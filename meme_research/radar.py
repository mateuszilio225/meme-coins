from __future__ import annotations
import json, math, statistics
from .config import D, digest

MODELS=('A','B','C')
BASELINES=('random','volume','momentum','buyer','first','matched')
STRATEGIES=MODELS+BASELINES+('main','main_random','cash')

def features(db,obs,p):
    rows=db.execute('SELECT * FROM observations WHERE mint=? AND pair=? AND source=? AND period=? AND received<=? AND received>=? ORDER BY received,id',
        (obs['mint'],obs['pair'],obs['source'],obs['period'],obs['received'],obs['received']-p['history_seconds'])).fetchall()
    history=[]
    for row in rows:
        if not history or row['received']-history[-1]['received']>=p['min_spacing_seconds']:
            history.append(row)
    if history and history[-1]['id']!=obs['id']:
        if len(history)>1 and obs['received']-history[-2]['received']>=p['min_spacing_seconds']: history[-1]=obs
        else: return {'ready':False,'reasons':['spacing']}
    reasons=[]
    if len(history)<p['min_observations']: reasons.append('history')
    if any(b['received']-a['received']>p['max_gap_seconds'] for a,b in zip(history,history[1:])): reasons.append('gap')
    if any(x['price'] is None for x in history): reasons.append('price_history')
    if obs['price'] is None: reasons.append('price')
    if obs['liquidity'] is None or D(obs['liquidity'])<D(p['min_liquidity_usd']): reasons.append('liquidity')
    if obs['pair_created'] is None or not 0 <= obs['received']-obs['pair_created']<=p['max_pair_age_minutes']*60: reasons.append('pair_age')
    unchanged=obs['received']
    for row in reversed(rows):
        if row['fingerprint']!=obs['fingerprint']: break
        unchanged=row['received']
    if obs['received']-unchanged>p['max_unchanged_seconds']: reasons.append('unchanged')
    if p['require_provider_timestamp'] and obs['provider_ts'] is None: reasons.append('provider_timestamp_unknown')
    if obs['provider_ts'] is not None and (obs['provider_ts']>obs['received'] or obs['received']-obs['provider_ts']>p['max_snapshot_age_seconds']): reasons.append('provider_stale')
    f={'ready':not reasons,'reasons':reasons,'count':len(history),'provider_timestamp_known':obs['provider_ts'] is not None,
       'security':'unknown','quote':'unknown','volume':float(obs['volume']) if obs['volume'] is not None else None,
       'liquidity':float(obs['liquidity']) if obs['liquidity'] is not None else None,
       'pair_age_minutes':(obs['received']-obs['pair_created'])/60 if obs['pair_created'] is not None else None}
    fact=db.execute('SELECT * FROM facts WHERE mint=? AND received<=? ORDER BY received DESC,id DESC LIMIT 1',(obs['mint'],obs['received'])).fetchone()
    if fact: f['security']=fact['state']
    if not history or any(x['price'] is None for x in history): return f
    prices=[float(x['price']) for x in history]
    speeds=[(b/a-1)/((y['received']-x['received'])/60) for a,b,x,y in zip(prices,prices[1:],history,history[1:])]
    logs=[math.log(b/a)/((y['received']-x['received'])/60) for a,b,x,y in zip(prices,prices[1:],history,history[1:])]
    f.update(ret=prices[-1]/prices[0]-1,velocity=speeds[-1] if speeds else None,
             acceleration=(speeds[-1]-speeds[-2])/((history[-1]['received']-history[-3]['received'])/120) if len(speeds)>1 else None,
             positive_fraction=sum(x>0 for x in speeds)/len(speeds) if speeds else None,
             volatility=statistics.pstdev(logs) if logs else None,
             drawdown=1-prices[-1]/max(prices), new_high=len(prices)>1 and prices[-1]>max(prices[:-1]))
    current=obs['buys']+obs['sells'] if obs['buys'] is not None and obs['sells'] is not None else 0
    f['buy_fraction']=obs['buys']/current if current else None
    previous=history[-2] if len(history)>1 else None
    total=(previous['buys']+previous['sells']) if previous and previous['buys'] is not None and previous['sells'] is not None else 0
    f['buy_change']=f['buy_fraction']-previous['buys']/total if total and f['buy_fraction'] is not None else None
    prior=[x for x in history[:-1] if 300<=obs['received']-x['received']<=480 and x['volume'] is not None and D(x['volume'])>0]
    f['volume_nonoverlap']=float(D(obs['volume'])/D(prior[-1]['volume'])) if prior and obs['volume'] is not None else None
    liquid=[D(x['liquidity']) for x in history if x['liquidity'] is not None]
    f['liquidity_retention']=float(D(obs['liquidity'])/max(liquid)) if liquid and max(liquid)>0 and obs['liquidity'] is not None else None
    f['tx_count']=current
    return f

def scores(f):
    def val(k,predicate): return f.get(k) is not None and predicate(f[k])
    components_a={
        'early_return':20 if val('ret',lambda x:.02<=x<=.35) else 0,
        'velocity':15 if val('velocity',lambda x:x>0) else 0,
        'acceleration':15 if val('acceleration',lambda x:x>0) else 0,
        'buy_fraction':15 if val('buy_fraction',lambda x:x>=.6) else 0,
        'drawdown':10 if val('drawdown',lambda x:x<=.05) else 0,
        'volume':10 if val('volume',lambda x:x>=1000) else 0,
        'volume_nonoverlap':15 if val('volume_nonoverlap',lambda x:x>=1.2) else 0}
    components_b={
        'positive_fraction':20 if val('positive_fraction',lambda x:x>=.75) else 0,
        'new_high':15 if f.get('new_high',False) else 0,
        'buy_fraction':10 if val('buy_fraction',lambda x:x>=.6) else 0,
        'buy_change':10 if val('buy_change',lambda x:x>=-.05) else 0,
        'velocity':10 if val('velocity',lambda x:x>0) else 0,
        'volume_nonoverlap':20 if val('volume_nonoverlap',lambda x:x>=.8) else 0,
        'acceleration':15 if val('acceleration',lambda x:x>=-.02) else 0}
    f['score_components']={'A':components_a,'B':components_b,'C':components_a}
    a=sum(components_a.values()); b=sum(components_b.values())
    risk=[]
    for k,bad in [('liquidity_retention',lambda x:x<.8),('buy_fraction',lambda x:x<.5),
                  ('drawdown',lambda x:x>=.15),('volatility',lambda x:x>.25),('ret',lambda x:x>1)]:
        if f.get(k) is None: risk.append(k+'_unknown')
        elif bad(f[k]): risk.append(k)
    if f.get('security') in ('known_risk','unsupported_program'): risk.append('known_token_risk_or_unsupported_program')
    return {'A':a,'B':b,'C':a},risk

def select(db,candidates,c,protocol,at,period):
    """Persist every model decision; deterministic contemporaneous ranking."""
    p=c['policy']; seed=c['research']['seed']; prepared=[]
    for obs in candidates:
        f=features(db,obs,p); sc,risk=scores(f)
        prepared.append((obs,f,sc,risk))
    selected={}; assignments={}
    for model in MODELS+BASELINES:
        eligible=[]
        for obs,f,sc,risk in prepared:
            reasons=list(f['reasons'])
            score=sc.get(model,0)
            if model in MODELS:
                if score<p['score_threshold']: reasons.append('score')
                if model=='B' and f['count']<5: reasons.append('continuation_history')
                if model=='C': reasons+=risk
            if db.execute('SELECT 1 FROM alerts WHERE mint=? AND model=? AND period=?',(obs['mint'],model,period)).fetchone(): reasons.append('already_alerted')
            assignments[(obs['id'],model)]=[score,reasons]
            if not reasons: eligible.append((obs,f,score))
        def key(item):
            o,f,s=item
            tie=digest([seed,model,o['mint'],o['pair']])
            if model in MODELS: return (-s,tie)
            if model in ('random','matched'): return (tie,)
            if model=='first': return (o['received'],tie)
            metric={'volume':'volume','momentum':'ret','buyer':'buy_fraction'}[model]
            return (-(f.get(metric) if f.get(metric) is not None else -1e100),tie)
        eligible.sort(key=key)
        if model=='matched':
            ref=selected.get('C')
            if ref:
                target=next(f for o,f,_ in eligible if o['id']==ref['id']) if any(o['id']==ref['id'] for o,f,_ in eligible) else features(db,ref,p)
                eligible=[x for x in eligible if x[0]['mint']!=ref['mint'] and x[1].get('liquidity') and target.get('liquidity') and
                          abs(math.log(x[1]['liquidity']/target['liquidity']))<=.7 and abs(x[1]['pair_age_minutes']-target['pair_age_minutes'])<=15]
            else: eligible=[]
        ranks={o['id']:i+1 for i,(o,_,_) in enumerate(eligible)}
        winner=eligible[0][0] if eligible else None
        for obs,f,sc,risk in prepared:
            score,reasons=assignments[(obs['id'],model)]
            if model=='matched' and not winner: reasons=reasons+['matched_control_unavailable']
            pick=winner is not None and winner['id']==obs['id']
            cur=db.execute('INSERT OR IGNORE INTO decisions(protocol,obs,model,period,at,score,eligible,selected,rank,reasons,features) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (protocol,obs['id'],model,period,at,score,int(not reasons),int(pick),ranks.get(obs['id']),json.dumps(reasons or ([] if pick else ['ranking'])),json.dumps(f)))
            if pick and cur.rowcount:
                db.execute('INSERT OR IGNORE INTO alerts(decision,mint,model,period,at) VALUES(?,?,?,?,?)',(cur.lastrowid,obs['mint'],model,period,at))
        if winner: selected[model]=winner
    # Fixed unique portfolio policy: C takes precedence, then A; never choose ex post winner.
    if 'C' in selected: selected['main']=selected['C']
    elif 'A' in selected: selected['main']=selected['A']
    if 'random' in selected: selected['main_random']=selected['random']
    return selected
