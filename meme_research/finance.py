from __future__ import annotations
import json
from decimal import Decimal, localcontext
from .config import D
from .store import event
from .radar import STRATEGIES, features

ZERO=D(0)

def costs(s,notional,liquidity):
    effective=D(liquidity)*D(s['liquidity_multiplier'])
    if effective<=0: raise ValueError('liquidity')
    return {'fee':D(s['fee_bps'])/10000, 'half_spread':D(s['spread_bps'])/20000,
            'slippage':D(s['slippage_bps'])/10000,
            'impact':2*D(notional)/effective*D(s['impact_multiplier']),
            'network':D(s['network_usd'])+D(s['priority_usd'])}

def break_even(budget,liquidity,s):
    """Exact first break-even root under this model, one buy+one full sell.
    Exit impact depends on exit gross reference value; fees not double charged.
    """
    b=D(budget); c=costs(s,b,liquidity)
    if b<=c['network']: return None
    h=c['half_spread']+c['slippage']; k=2*D(s['impact_multiplier'])/(D(liquidity)*D(s['liquidity_multiplier']))
    base=(b-c['network'])/(1+c['fee'])/(1+h+c['impact'])
    target=(b+c['network'])/(1-c['fee'])
    discriminant=(1-h)**2-4*k*target
    if discriminant<0: return None
    with localcontext() as ctx:
        ctx.prec=40
        x=2*target/(1-h+discriminant.sqrt())
        return x/base-1

def ensure_wallets(db,c,period,at):
    initial=D(c['research']['capital_brl'])/D(c['research']['fx_brl_per_usd'])
    for strategy in STRATEGIES:
        for scenario in c['scenarios']:
            wid=f'{period}:{strategy}:{scenario}'
            cur=db.execute('INSERT OR IGNORE INTO wallets VALUES(?,?,?,?,?,?)',(wid,strategy,scenario,period,str(initial),str(initial)))
            if cur.rowcount: db.execute('INSERT INTO ledger(wallet,at,delta,kind) VALUES(?,?,?,?)',(wid,at,str(initial),'initial'))

def reserved(db,wid):
    return sum((D(x[0]) for x in db.execute("SELECT budget FROM orders WHERE wallet=? AND state='pending'",(wid,))),ZERO)

def committed(db,wid):
    return sum((D(x[0]) for x in db.execute("SELECT remaining_cost FROM positions WHERE wallet=? AND state!='closed'",(wid,))),ZERO)

def reject(db,at,wid,obs,reason):
    event(db,at,'abstain',{'wallet':wid,'obs':obs['id'],'mint':obs['mint'],'reason':reason})

def quote_evidence(db,mint,budget,now):
    usdc='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    buy=db.execute("SELECT * FROM quotes WHERE input_mint=? AND output_mint=? AND amount=? AND state='ok' AND received<=? AND requested>=? ORDER BY id DESC LIMIT 1",
        (usdc,mint,str(int(budget*1000000)),now,now-30)).fetchone()
    if not buy: return False
    sell=db.execute("SELECT * FROM quotes WHERE input_mint=? AND output_mint=? AND amount=? AND state='ok' AND requested>=? AND received<=? ORDER BY id DESC LIMIT 1",
        (mint,usdc,buy['out_amount'],buy['received'],now)).fetchone()
    return bool(sell and int(sell['out_amount'])>0)

def submit(db,c,selected,period,at):
    p=c['policy']
    for strategy,obs in selected.items():
        for name,s in c['scenarios'].items():
            wid=f'{period}:{strategy}:{name}'; w=db.execute('SELECT * FROM wallets WHERE id=?',(wid,)).fetchone()
            initial=D(w['initial']); budget=initial*D(p['position_fraction'])
            pending=db.execute("SELECT count(*) FROM orders WHERE wallet=? AND state='pending'",(wid,)).fetchone()[0]
            opened=db.execute("SELECT count(*) FROM positions WHERE wallet=? AND state!='closed'",(wid,)).fetchone()[0]
            reason=None
            if db.execute("SELECT 1 FROM orders WHERE wallet=? AND mint=? AND state='pending'",(wid,obs['mint'])).fetchone() or db.execute("SELECT 1 FROM positions WHERE wallet=? AND mint=? AND state!='closed'",(wid,obs['mint'])).fetchone(): reason='duplicate_exposure'
            elif pending+opened>=p['max_positions']: reason='position_limit'
            elif committed(db,wid)+reserved(db,wid)+budget>initial*D(p['exposure_fraction']): reason='exposure_limit'
            elif D(w['cash'])-reserved(db,wid)-budget<initial*D(p['reserve_fraction']): reason='cash_reserve'
            elif budget<D(p['min_notional_usd']): reason='minimum_notional'
            elif obs['liquidity'] is None or budget>D(obs['liquidity'])*D(s['liquidity_multiplier'])*D(p['max_capacity_fraction']): reason='capacity'
            else:
                be=break_even(budget,obs['liquidity'],s)
                if be is None or be>D(p['max_break_even']): reason='break_even'
            if strategy in ('main','main_random') and p['portfolio_require_quote'] and not quote_evidence(db,obs['mint'],budget,at): reason='exact_size_round_trip_quote_missing'
            if reason: reject(db,at,wid,obs,reason); continue
            db.execute('INSERT INTO orders(wallet,mint,pair,source,signal,created,eligible,expires,budget,state,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (wid,obs['mint'],obs['pair'],obs['source'],obs['id'],at,at+s['latency_seconds'],at+p['entry_timeout_seconds'],str(budget),'pending',p['entry_mode']))

def ledger(db,wid,at,delta,kind,ref):
    cash=D(db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0])+delta
    if cash < 0: raise ArithmeticError('negative cash')
    db.execute('UPDATE wallets SET cash=? WHERE id=?',(str(cash),wid))
    db.execute('INSERT INTO ledger(wallet,at,delta,kind,ref) VALUES(?,?,?,?,?)',(wid,at,str(delta),kind,ref))

def can_fill(obs,eligible,created,p):
    return obs['requested']>=eligible and obs['requested']>created and obs['received']-obs['requested']<=p['max_snapshot_age_seconds']

def attempt_failure(db,w,s,at,ref):
    n=s['failure_every_n']
    attempts=db.execute("SELECT count(*) FROM ledger WHERE wallet=? AND kind IN ('buy','sell','onchain_failure')",(w['id'],)).fetchone()[0]+1
    if n and attempts%n==0:
        fee=D(s['network_usd'])+D(s['priority_usd'])
        cash=D(db.execute('SELECT cash FROM wallets WHERE id=?',(w['id'],)).fetchone()[0])
        if cash<fee:
            event(db,at,'failure_fee_unaffordable',{'wallet':w['id']}); return True
        ledger(db,w['id'],at,-fee,'onchain_failure',ref)
        event(db,at,'hypothetical_onchain_failure',{'wallet':w['id'],'ref':ref,'fee':str(fee),'deterministic_every_n':n})
        return True
    return False

def process(db,c,obs):
    p=c['policy']; at=obs['received']; mid=D(obs['price']) if obs['price'] is not None else None
    for order in db.execute("SELECT * FROM orders WHERE mint=? AND pair=? AND source=? AND state='pending'",(obs['mint'],obs['pair'],obs['source'])).fetchall():
        w=db.execute('SELECT * FROM wallets WHERE id=?',(order['wallet'],)).fetchone(); s=c['scenarios'][w['scenario']]
        if w['period']!=obs['period']: continue
        if at>order['expires']:
            db.execute("UPDATE orders SET state='expired',reason='entry_timeout' WHERE id=?",(order['id'],)); continue
        if not can_fill(obs,order['eligible'],order['created'],p): continue
        if mid is None or obs['liquidity'] is None or D(obs['liquidity'])<D(p['min_liquidity_usd']): continue
        budget=D(order['budget']); sig=db.execute('SELECT * FROM observations WHERE id=?',(order['signal'],)).fetchone()
        f=features(db,obs,p)
        if not f['ready']: continue
        if w['strategy']=='C':
            from .radar import scores
            if scores(f)[1]: continue
        mode=p['entry_mode']
        if mode=='confirmation' and not (mid>=D(sig['price'])*D('1.01') and (f.get('velocity') or 0)>0): continue
        if mode in ('consolidation','recovery'):
            history=db.execute('SELECT price FROM observations WHERE mint=? AND pair=? AND source=? AND received>=? AND received<=? AND price IS NOT NULL ORDER BY received,id',
                (obs['mint'],obs['pair'],obs['source'],order['created'],at)).fetchall()
            prices=[D(x[0]) for x in history]
            if mode=='consolidation' and (len(prices)<3 or max(prices[-3:])/min(prices[-3:])-1>D('.03')): continue
            if mode=='recovery' and (not any(b<a for a,b in zip(prices,prices[1:])) or (f.get('velocity') or 0)<=0): continue
        if budget>D(obs['liquidity'])*D(s['liquidity_multiplier'])*D(p['max_capacity_fraction']): continue
        be=break_even(budget,obs['liquidity'],s)
        if be is None or be>D(p['max_break_even']): continue
        if w['strategy'] in ('main','main_random') and p['portfolio_require_quote'] and not quote_evidence(db,obs['mint'],budget,at): continue
        if attempt_failure(db,w,s,at,order['id']):
            db.execute("UPDATE orders SET state='failed',reason='hypothetical_onchain_failure' WHERE id=?",(order['id'],)); continue
        cc=costs(s,budget,obs['liquidity']); fill=mid*(1+cc['half_spread']+cc['slippage']+cc['impact'])
        gross=(budget-cc['network'])/(1+cc['fee'])
        if gross<=0: continue
        quantity=gross/fill; fee=gross*cc['fee']; embedded=quantity*(fill-mid)
        cur=db.execute('INSERT INTO positions(wallet,mint,pair,source,signal,entry_obs,entry_at,quantity,initial_quantity,cost,remaining_cost,entry_price,peak,state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (w['id'],obs['mint'],obs['pair'],obs['source'],order['signal'],obs['id'],at,str(quantity),str(quantity),str(budget),str(budget),str(fill),str(mid),'open'))
        pid=cur.lastrowid
        fillcur=db.execute('INSERT INTO fills(wallet,position,obs,at,side,quantity,price,mid,fee,network,embedded,cash_delta,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (w['id'],pid,obs['id'],at,'buy',str(quantity),str(fill),str(mid),str(fee),str(cc['network']),str(embedded),str(-budget),'entry'))
        ledger(db,w['id'],at,-budget,'buy',fillcur.lastrowid)
        db.execute("UPDATE orders SET state='filled',position=? WHERE id=?",(pid,order['id']))
    for pos in db.execute("SELECT * FROM positions WHERE mint=? AND pair=? AND source=? AND state IN ('open','exit_pending')",(obs['mint'],obs['pair'],obs['source'])).fetchall():
        w=db.execute('SELECT * FROM wallets WHERE id=?',(pos['wallet'],)).fetchone(); s=c['scenarios'][w['scenario']]
        if obs['period']!=w['period'] or at<=pos['entry_at']: continue
        peak=max(D(pos['peak']),mid) if mid else D(pos['peak'])
        db.execute('UPDATE positions SET peak=? WHERE id=?',(str(peak),pos['id']))
        if pos['state']=='open':
            reason=None; entry=D(pos['entry_price'])
            stop=D(p['stop_fraction'])
            if p['exit_mode']=='volatility':
                sig=db.execute('SELECT * FROM observations WHERE id=?',(pos['signal'],)).fetchone()
                vol=features(db,sig,p).get('volatility')
                if vol is not None: stop=max(D('.15'),min(D('.40'),3*D(vol)))
            if mid and mid<=entry*(1-stop): reason='stop'
            elif pos['partial'] and mid and mid<=peak*(1-D(p['trailing_fraction'])): reason='trailing'
            elif not pos['partial'] and mid and mid>=entry*D(p['take_profit_multiple']): reason='partial'
            elif at-pos['entry_at']>=p['max_holding_seconds']: reason='time'
            entryobs=db.execute('SELECT * FROM observations WHERE id=?',(pos['entry_obs'],)).fetchone()
            if obs['liquidity'] is not None and entryobs['liquidity'] and D(obs['liquidity'])<=D(entryobs['liquidity'])*D(p['liquidity_exit_retention']): reason='liquidity'
            if mid is None: reason='price_missing'
            if p['exit_mode']=='momentum':
                f=features(db,obs,p)
                if f.get('velocity') is not None and f['velocity']<0 and f.get('buy_fraction') is not None and f['buy_fraction']<.5: reason='momentum'
            if reason:
                db.execute("UPDATE positions SET state='exit_pending',exit_requested=?,exit_reason=? WHERE id=?",(at,reason,pos['id']))
            continue  # Exit always requires a later request, even when triggered by this observation.
        if at-pos['exit_requested']>p['exit_timeout_seconds']:
            db.execute("UPDATE positions SET state='inconclusive' WHERE id=?",(pos['id'],)); continue
        if not can_fill(obs,pos['exit_requested']+s['latency_seconds'],pos['exit_requested'],p): continue
        if mid is None or obs['liquidity'] is None or D(obs['liquidity'])<=0: continue
        amount=D(pos['quantity'])*(D(p['partial_fraction']) if pos['exit_reason']=='partial' else 1)
        notional=amount*mid
        if notional>D(obs['liquidity'])*D(s['liquidity_multiplier'])*D(p['max_capacity_fraction']): continue
        cc=costs(s,notional,obs['liquidity']); fill=mid*(1-cc['half_spread']-cc['slippage']-cc['impact'])
        if fill<=0: continue
        gross=amount*fill; fee=gross*cc['fee']; proceeds=gross-fee-cc['network']
        if proceeds<0: continue  # No invented negative-output sale.
        if attempt_failure(db,w,s,at,pos['id']): continue
        allocated=D(pos['remaining_cost'])*amount/D(pos['quantity']); pnl=D(pos['pnl'])+proceeds-allocated
        remains=D(pos['quantity'])-amount
        cur=db.execute('INSERT INTO fills(wallet,position,obs,at,side,quantity,price,mid,fee,network,embedded,cash_delta,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (w['id'],pos['id'],obs['id'],at,'sell',str(amount),str(fill),str(mid),str(fee),str(cc['network']),str(amount*(mid-fill)),str(proceeds),pos['exit_reason']))
        ledger(db,w['id'],at,proceeds,'sell',cur.lastrowid)
        db.execute('UPDATE positions SET quantity=?,remaining_cost=?,pnl=?,state=?,partial=?,closed_at=?,exit_requested=NULL WHERE id=?',
            (str(remains),str(D(pos['remaining_cost'])-allocated),str(pnl),'closed' if remains==0 else 'open',1 if remains else pos['partial'],at if remains==0 else None,pos['id']))

def tick(db,c,at,schedule):
    # Timeouts advance without fresh price; never free the capital of an unsold position.
    db.execute("UPDATE orders SET state='expired',reason='entry_timeout' WHERE state='pending' AND expires<?",(at,))
    for pos in db.execute("SELECT p.*,w.period FROM positions p JOIN wallets w ON w.id=p.wallet WHERE p.state IN ('open','exit_pending')").fetchall():
        end=schedule[pos['period']][1]
        if at>=end or (pos['state']=='exit_pending' and at-pos['exit_requested']>c['policy']['exit_timeout_seconds']):
            db.execute("UPDATE positions SET state='inconclusive' WHERE id=?",(pos['id'],))
        elif pos['state']=='open' and at-pos['entry_at']>=c['policy']['max_holding_seconds']:
            db.execute("UPDATE positions SET state='exit_pending',exit_requested=?,exit_reason='time' WHERE id=?",(at,pos['id']))
    for w in db.execute('SELECT * FROM wallets').fetchall():
        if at>schedule[w['period']][1] and db.execute('SELECT 1 FROM equity WHERE wallet=? AND at>=? LIMIT 1',(w['id'],schedule[w['period']][1])).fetchone():
            continue
        positions=db.execute("SELECT * FROM positions WHERE wallet=? AND state!='closed'",(w['id'],)).fetchall()
        value=ZERO; unknown=False
        for pos in positions:
            obs=db.execute('SELECT * FROM observations WHERE mint=? AND pair=? AND source=? AND period=? AND received<=? ORDER BY received DESC,id DESC LIMIT 1',
                (pos['mint'],pos['pair'],pos['source'],w['period'],at)).fetchone()
            if not obs or obs['price'] is None or at-obs['received']>c['policy']['max_snapshot_age_seconds']: unknown=True
            else: value+=D(pos['quantity'])*D(obs['price'])
        cash=D(w['cash']); exposure=committed(db,w['id'])+reserved(db,w['id'])
        db.execute('INSERT INTO equity(wallet,at,cash,marked,stress,exposure,unresolved) VALUES(?,?,?,?,?,?,?)',
            (w['id'],at,str(cash),None if unknown else str(cash+value),str(cash),str(exposure),len(positions)))
