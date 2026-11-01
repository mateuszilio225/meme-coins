from __future__ import annotations
import base64, datetime as dt, email.utils, hashlib, json, math, os, random, re, time
import urllib.error, urllib.parse, urllib.request
from decimal import Decimal
from .config import canonical, digest, D
from .store import event

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

class DataUnavailable(Exception): pass

class HTTP:
    """Serial HTTP; TLS/proxy defaults preserved. No signing or send-transaction methods."""
    LIMITS={'dex_profiles':(60,2), 'dex_pairs':(60,12), 'rpc':(3600,30), 'quote':(60,6), 'fx':(60,2)}
    def __init__(self, db, clock=time.time, opener=None):
        self.db, self.clock=db,clock
        self.opener=opener or urllib.request.build_opener(NoRedirect())

    def get(self, provider, url, ttl=30, payload=None, headers=None):
        now=self.clock(); key=digest([provider,url,payload])
        cached=self.db.execute('SELECT * FROM cache WHERE key=?',(key,)).fetchone()
        if cached and cached['expires']>now:
            if cached['state']!='ok': raise DataUnavailable('cached_failure')
            return json.loads(cached['data']), cached['at'], 'cache'
        state=self.db.execute('SELECT * FROM api_state WHERE provider=?',(provider,)).fetchone()
        window,limit=self.LIMITS[provider]
        failures=state['failures'] if state else 0
        start=state['window_start'] if state and now-state['window_start']<window else now
        calls=state['calls'] if state and start==state['window_start'] else 0
        next_at=state['next_at'] if state else 0
        if now<next_at or calls>=limit:
            self.db.execute('INSERT INTO api_calls(provider,endpoint,requested,received,state) VALUES(?,?,?,?,?)',
                            (provider,urllib.parse.urlsplit(url).path,now,now,'deferred'))
            raise DataUnavailable('deferred')
        self.db.execute('INSERT OR REPLACE INTO api_state VALUES(?,?,?,?,?)',(provider,now+1,failures,start,calls+1))
        hdr={'Accept':'application/json','User-Agent':'MoonshotResearch/0.1.0'}
        hdr.update(headers or {})
        body=canonical(payload).encode() if payload is not None else None
        if body: hdr['Content-Type']='application/json'
        req=urllib.request.Request(url,data=body,headers=hdr,method='POST' if body else 'GET')
        status=None; error='transport'; data=None; retry=0
        try:
            with self.opener.open(req,timeout=10) as response:
                status=response.status
                if status!=200: raise DataUnavailable('http')
                content=response.headers.get('Content-Type','')
                if 'json' not in content: raise DataUnavailable('content_type')
                raw=response.read(2_000_001)
                if len(raw)>2_000_000: raise DataUnavailable('too_large')
                data=json.loads(raw,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                if not isinstance(data,(list,dict)): raise DataUnavailable('schema')
                error='ok'
        except urllib.error.HTTPError as exc:
            status=exc.code; error='http_'+str(status)
            val=exc.headers.get('Retry-After','')
            try: retry=max(0,float(val))
            except ValueError:
                try: retry=max(0,email.utils.parsedate_to_datetime(val).timestamp()-now)
                except (ValueError,TypeError,OverflowError): pass
        except (OSError,ValueError,DataUnavailable): pass
        received=self.clock()
        self.db.execute('INSERT INTO api_calls(provider,endpoint,requested,received,state,status) VALUES(?,?,?,?,?,?)',
                        (provider,urllib.parse.urlsplit(url).path,now,received,error,status))
        if error!='ok':
            failures+=1
            delay=max(retry,min(3600,2**min(failures,10))+random.uniform(0,2),300 if failures>=3 else 0)
            self.db.execute('UPDATE api_state SET next_at=?,failures=? WHERE provider=?',(received+delay,failures,provider))
            self.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)',(key,received,received+min(delay,60),None,error))
            raise DataUnavailable(error)
        self.db.execute('UPDATE api_state SET failures=0 WHERE provider=?',(provider,))
        self.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)',(key,received,received+ttl,canonical(data),'ok'))
        return data,received,'network'

def number(value, positive=False):
    if isinstance(value,bool) or value is None: return None
    try:
        d=D(value)
        return str(d) if d.is_finite() and abs(d)<=D('1e30') and (d>0 if positive else d>=0) else None
    except Exception: return None

def integer(value):
    n=number(value)
    return int(D(n)) if n is not None and D(n)==D(n).to_integral_value() else None

def normalize(pair, requested, received):
    if not isinstance(pair,dict) or pair.get('chainId')!='solana': return None
    for key in ('baseToken','liquidity','volume','txns'):
        if pair.get(key) is not None and not isinstance(pair[key],dict): return None
    if isinstance(pair.get('txns'),dict) and pair['txns'].get('m5') is not None and not isinstance(pair['txns']['m5'],dict): return None
    mint=(pair.get('baseToken') or {}).get('address'); address=pair.get('pairAddress')
    if not isinstance(mint,str) or not isinstance(address,str) or not mint or not address: return None
    price=number(pair.get('priceUsd'),True)
    liq=number((pair.get('liquidity') or {}).get('usd'))
    volume=number((pair.get('volume') or {}).get('m5'))
    tx=(pair.get('txns') or {}).get('m5') or {}
    created=number(pair.get('pairCreatedAt'))
    created=float(D(created)/1000) if created is not None else None
    quality={'price':'valid' if price else 'missing_or_invalid',
             'liquidity':'missing' if 'usd' not in (pair.get('liquidity') or {}) else ('invalid' if liq is None else ('zero' if D(liq)==0 else 'valid')),
             'provider_timestamp':'unavailable','token_age':'unknown','dex':pair.get('dexId'),
             'symbol':(pair.get('baseToken') or {}).get('symbol')}
    return {'mint':mint,'pair':address,'source':'dexscreener','requested':requested,'received':received,
            'provider_ts':None,'price':price,'liquidity':liq,'volume':volume,'buys':integer(tx.get('buys')),
            'sells':integer(tx.get('sells')),'pair_created':created,'fingerprint':digest(pair),
            'quality':canonical(quality),'raw':canonical(pair)}

class Sources:
    def __init__(self, db, http=None): self.db=db; self.http=http or HTTP(db)

    def discover(self):
        data,received,origin=self.http.get('dex_profiles','https://api.dexscreener.com/token-profiles/latest/v1',ttl=300)
        if not isinstance(data,list): raise DataUnavailable('profiles_schema')
        for item in data:
            if isinstance(item,dict) and item.get('chainId')=='solana' and isinstance(item.get('tokenAddress'),str):
                self.db.execute('INSERT OR IGNORE INTO tokens(mint,discovered) VALUES(?,?)',(item['tokenAddress'],received))
        return origin

    def pairs(self,mint):
        if not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}',mint): raise DataUnavailable('mint_format')
        requested=self.http.clock()
        data,received,origin=self.http.get('dex_pairs','https://api.dexscreener.com/token-pairs/v1/solana/'+mint,ttl=25)
        if origin=='cache': return []  # Never turn a cache read into a new observation.
        if not isinstance(data,list): raise DataUnavailable('pairs_schema')
        result=[]
        for pair in data:
            obs=normalize(pair,requested,received)
            if obs and obs['mint']==mint: result.append(obs)
        return result

    def facts(self,mints):
        if not mints: return
        # Only read-only RPC method; no token-holder or circulating-supply claims.
        data,received,_=self.http.get('rpc','https://api.mainnet-beta.solana.com',ttl=3600,
            payload={'jsonrpc':'2.0','id':1,'method':'getMultipleAccounts','params':[mints[:10],{'encoding':'jsonParsed'}]})
        if not isinstance(data,dict) or not isinstance(data.get('result'),dict): raise DataUnavailable('rpc_schema')
        values=data['result'].get('value')
        if not isinstance(values,list) or len(values)!=len(mints[:10]): raise DataUnavailable('rpc_schema')
        for mint,value in zip(mints[:10],values):
            state='unknown'; fact={}
            try:
                parsed=value['data']['parsed']
                info=parsed['info']
                if parsed['type']=='mint':
                    fact={k:info.get(k,'missing') for k in ('mintAuthority','freezeAuthority','decimals','supply')}
                    fact['owner_program']=value.get('owner')
                    fact['extensions']=info.get('extensions','unknown')
                    state='known_risk' if any(fact[k] not in (None,'missing') for k in ('mintAuthority','freezeAuthority')) else 'partial_unknown'
                    if value.get('owner')!='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': state='unsupported_program'
            except (KeyError,TypeError): pass
            self.db.execute('INSERT INTO facts(mint,received,state,raw) VALUES(?,?,?,?)',(mint,received,state,canonical(fact)))

    def quote(self,input_mint,output_mint,amount):
        if not str(amount).isdigit() or int(amount)<=0: raise ValueError('atomic amount')
        key=os.environ.get('JUPITER_API_KEY')
        if not key: raise DataUnavailable('quote_key_missing')
        requested=self.http.clock()
        query=urllib.parse.urlencode({'inputMint':input_mint,'outputMint':output_mint,'amount':str(amount),'slippageBps':100,'swapMode':'ExactIn'})
        # Quote-only legacy endpoint. No order construction/execute/swap request exists.
        data,received,_=self.http.get('quote','https://api.jup.ag/swap/v1/quote?'+query,ttl=0,headers={'x-api-key':key})
        if not isinstance(data,dict): raise DataUnavailable('quote_schema')
        state='ok'
        if any(k in data for k in ('transaction','swapTransaction','signedTransaction')): state='unexpected_transaction'
        elif data.get('inputMint')!=input_mint or data.get('outputMint')!=output_mint or str(data.get('inAmount'))!=str(amount): state='incompatible'
        elif not str(data.get('outAmount','')).isdigit() or int(data['outAmount'])<=0 or not data.get('routePlan'): state='no_route'
        # Whitelist retained quote evidence: never persist service headers or arbitrary fields.
        safe={k:data.get(k) for k in ('inputMint','outputMint','inAmount','outAmount','otherAmountThreshold','priceImpactPct','routePlan','contextSlot','timeTaken')}
        self.db.execute('INSERT INTO quotes(mint,requested,received,input_mint,output_mint,amount,out_amount,state,raw) VALUES(?,?,?,?,?,?,?,?,?)',
                        (output_mint,requested,received,input_mint,output_mint,str(amount),str(data.get('outAmount','')),state,canonical(safe)))
        if state!='ok': raise DataUnavailable(state)
        return safe,requested,received

    def round_trip(self,mint,budget_usd):
        usdc='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        # USDC six decimals; USD equivalence is explicitly conditional on peg.
        amount=int(D(budget_usd)*1_000_000)
        buy,_,_=self.quote(usdc,mint,amount)
        return self.quote(mint,usdc,buy['outAmount'])

    def fx(self):
        now=dt.datetime.now(dt.timezone.utc); start=(now-dt.timedelta(days=10)).strftime('%m-%d-%Y'); end=now.strftime('%m-%d-%Y')
        url="https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@a,dataFinalCotacao=@b)?"
        url+=urllib.parse.urlencode({'@a':"'"+start+"'",'@b':"'"+end+"'",'$format':'json','$orderby':'dataHoraCotacao desc','$top':1})
        data,received,_=self.http.get('fx',url,ttl=3600)
        values=data.get('value') if isinstance(data,dict) else None
        if not values: raise DataUnavailable('fx_empty')
        value=values[0]; rate=number(value.get('cotacaoVenda'),True)
        if not rate: raise DataUnavailable('fx_schema')
        return {'fx_brl_per_usd':rate,'fx_source':'BCB PTAX cotacaoVenda '+str(value.get('dataHoraCotacao')),
                'fx_available_at':received,'note':'disponível localmente no recebimento; não é preço intradiário executável'}
