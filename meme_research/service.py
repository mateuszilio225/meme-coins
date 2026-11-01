from __future__ import annotations
import json, time
from .config import canonical, digest, period_at, D
from .data import Sources, DataUnavailable
from .store import event
from .radar import select
from .finance import process, submit, ensure_wallets, tick

COLUMNS=('mint','pair','source','requested','received','provider_ts','price','liquidity','volume','buys','sells','pair_created','fingerprint','quality','raw','period')

def protocol(db,c=None):
    row=db.execute('SELECT * FROM protocols').fetchone()
    if not row: raise ValueError('Execute init antes de run.')
    frozen=json.loads(row['config'])
    if c is not None and digest(c)!=row['id']: raise ValueError('Configuração diverge do protocolo congelado. Não altere um experimento ativo; use outro banco.')
    return row,frozen,json.loads(row['schedule'])

def ingest(db,items,schedule,now):
    ids=[]
    for data in sorted(items,key=lambda x:(x['received'],x['mint'],x['pair'])):
        o=dict(data)
        if not 0<=o['requested']<=o['received']<=now: raise ValueError('Observation future/inverted time')
        if o['provider_ts'] is not None and o['provider_ts']>o['received']: raise ValueError('future provider timestamp')
        # Store all observations, but a mint belongs to its first-seen period forever.
        db.execute('INSERT OR IGNORE INTO tokens(mint,discovered) VALUES(?,?)',(o['mint'],o['received']))
        token=db.execute('SELECT * FROM tokens WHERE mint=?',(o['mint'],)).fetchone()
        if token['first_seen'] is None:
            period=period_at(schedule,o['received'])
            db.execute('UPDATE tokens SET first_seen=?,period=? WHERE mint=?',(o['received'],period,o['mint']))
        else: period=token['period']
        o['period']=period
        for key in ('price','liquidity','volume'):
            if o[key] is not None and (not D(o[key]).is_finite() or D(o[key])<0 or (key=='price' and D(o[key])==0)): raise ValueError('invalid normalized '+key)
        cur=db.execute(f"INSERT OR IGNORE INTO observations({','.join(COLUMNS)}) VALUES({','.join('?' for _ in COLUMNS)})",[o[k] for k in COLUMNS])
        if cur.rowcount: ids.append(cur.lastrowid)
    return ids

def cycle(db,c,items,at):
    reg,_,schedule=protocol(db,c)
    current=period_at(schedule,at)
    ids=ingest(db,items,schedule,at)
    for oid in ids:
        obs=db.execute('SELECT * FROM observations WHERE id=?',(oid,)).fetchone()
        if at-obs['received']<=c['policy']['max_snapshot_age_seconds'] and obs['period'] in schedule and at<schedule[obs['period']][1]:
            process(db,c,obs)
        else:
            event(db,at,'stale_batch_no_fill',{'obs':oid})
    if current!='embargo':
        ensure_wallets(db,c,current,at)
        # Representative pool per mint is chosen by currently reported liquidity, not future return.
        representatives={}
        for oid in ids:
            obs=db.execute('SELECT * FROM observations WHERE id=?',(oid,)).fetchone()
            if obs['period']!=current or at-obs['received']>c['policy']['max_snapshot_age_seconds']: continue
            old=representatives.get(obs['mint'])
            if old is None or (D(obs['liquidity'] or 0),obs['pair'])>(D(old['liquidity'] or 0),old['pair']): representatives[obs['mint']]=obs
        selected=select(db,list(representatives.values()),c,reg['id'],at,current)
        submit(db,c,selected,current,at)
    tick(db,c,at,schedule)
    event(db,at,'cycle',{'observations':len(ids),'period':current})
    return len(ids)

def collect_once(db,c,sources=None):
    sources=sources or Sources(db); now=time.time(); items=[]
    try: sources.discover()
    except DataUnavailable as exc: event(db,now,'source_unavailable',{'provider':'dex_profiles','reason':str(exc)})
    # Open orders/positions first, then oldest last_poll; bounded serial concurrency.
    tokens=db.execute("""SELECT t.*,
        CASE WHEN EXISTS(SELECT 1 FROM positions p WHERE p.mint=t.mint AND p.state!='closed')
        OR EXISTS(SELECT 1 FROM orders o WHERE o.mint=t.mint AND o.state='pending') THEN 0 ELSE 1 END AS priority
        FROM tokens t WHERE t.last_poll<=? ORDER BY priority,t.last_poll,t.discovered,t.mint LIMIT ?""",
        (now-30,c['research']['max_tokens_per_cycle'])).fetchall()
    for token in tokens:
        try: items+=sources.pairs(token['mint'])
        except DataUnavailable as exc: event(db,time.time(),'source_unavailable',{'provider':'dex_pairs','mint':token['mint'],'reason':str(exc)})
        db.execute('UPDATE tokens SET last_poll=? WHERE mint=?',(time.time(),token['mint']))
    if c['research']['quotes_enabled'] and tokens:
        # Exactly one round trip per cycle. Provider limiter persists all actual attempts.
        budget=D(c['research']['capital_brl'])/D(c['research']['fx_brl_per_usd'])*D(c['policy']['position_fraction'])
        try: sources.round_trip(tokens[0]['mint'],budget)
        except DataUnavailable as exc: event(db,time.time(),'quote_unavailable',{'reason':str(exc)})
    at=time.time()
    count=cycle(db,c,items,at)
    # New facts are consumed only by future observations, never the previous decision.
    if c['research']['rpc_enabled'] and tokens:
        try: sources.facts([x['mint'] for x in tokens[:10]])
        except DataUnavailable as exc: event(db,time.time(),'rpc_unavailable',{'reason':str(exc)})
    return count
