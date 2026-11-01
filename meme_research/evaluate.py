from __future__ import annotations
import collections, datetime as dt, json, math, random, statistics, time
from .config import D, canonical
from .service import protocol
from .reports import guard, profitability

DAY=86400

def block_interval(values,repetitions=30000,alpha=.05/9,seed=3501,block=3):
    """Circular moving-day blocks. No claim that three days remove all dependence."""
    if len(values)<20: return {'state':'insufficient_days','interval':None}
    if repetitions*alpha/2<50: return {'state':'insufficient_tail_resolution','interval':None}
    rng=random.Random(seed); n=len(values); estimates=[]
    for _ in range(repetitions):
        sample=[]
        while len(sample)<n:
            start=rng.randrange(n)
            sample.extend(values[(start+j)%n] for j in range(block))
        estimates.append(sum(sample[:n])/n)
    estimates.sort()
    return {'state':'computed_descriptive','interval':[estimates[int(repetitions*alpha/2)],estimates[min(repetitions-1,int(repetitions*(1-alpha/2)))]],
            'alpha':alpha,'repetitions':repetitions,'days':n,'block_days':block,
            'note':'Família primária fixa: 3 modelos x 3 cenários = 9 comparações. Dependência de regime pode persistir.'}

def daily_pnl(db,wid,start,end):
    n=math.ceil((end-start)/DAY); values=[0.0]*n
    # All ledger deltas except initial; cash-flow alone double-counts entry timing, so use
    # closed and partial realized PnL, only interpretable when no unresolved positions.
    for p in db.execute("SELECT * FROM positions WHERE wallet=? AND state='closed'",(wid,)):
        i=int((p['closed_at']-start)//DAY)
        if 0<=i<n: values[i]+=float(p['pnl'])
    for row in db.execute("SELECT at,delta FROM ledger WHERE wallet=? AND kind='onchain_failure'",(wid,)):
        i=int((row['at']-start)//DAY)
        if 0<=i<n: values[i]+=float(row['delta'])
    return values

def evaluate(db,period,at=None,save=True):
    at=time.time() if at is None else at
    guard(db,period,at)
    reg,c,schedule=protocol(db); start,end=schedule[period]
    if at<end: raise ValueError('Avaliação final exige período encerrado. Use relatórios descritivos no desenvolvimento.')
    times=[r[0] for r in db.execute('SELECT DISTINCT received FROM observations WHERE period=? AND received>=? AND received<? ORDER BY received',(period,start,end))]
    covered=sum(min(b-a,c['policy']['max_gap_seconds']) for a,b in zip(times,times[1:]))
    coverage=covered/(end-start)
    summary=profitability(db,period,at); wallets={w['wallet']:w for w in summary['wallets']}
    comparisons=[]
    for scenario in c['scenarios']:
        baseline=f'{period}:random:{scenario}'
        for model in ('A','B','C'):
            wid=f'{period}:{model}:{scenario}'; report=wallets.get(wid)
            if not report or baseline not in wallets: continue
            left=daily_pnl(db,wid,start,end); right=daily_pnl(db,baseline,start,end)
            delta=[a-b for a,b in zip(left,right)]
            closed_mints=db.execute("SELECT count(DISTINCT mint) FROM positions WHERE wallet=? AND state='closed'",(wid,)).fetchone()[0]
            observed_days=len({int((x-start)//DAY) for x in times})
            blockers=[]
            if reg['synthetic']: blockers.append('synthetic_not_economic_evidence')
            if period=='development': blockers.append('development_not_confirmation')
            if closed_mints<c['calendar']['min_closed_mints']: blockers.append('insufficient_distinct_closed_mints')
            if observed_days<c['calendar']['min_days']: blockers.append('insufficient_observed_days')
            if coverage<.8: blockers.append('insufficient_temporal_coverage')
            if report['open_or_inconclusive'] or wallets[baseline]['open_or_inconclusive']: blockers.append('unresolved_positions')
            if report['orders'].get('pending',0) or wallets[baseline]['orders'].get('pending',0): blockers.append('pending_orders')
            if not c['research']['monthly_costs_confirmed']: blockers.append('recurring_costs_unconfirmed')
            # All market fills remain hypothetical even with quotes; never label an executable edge.
            blockers.append('execution_costs_and_fills_unverified')
            ci=block_interval(delta,c['calendar']['bootstrap_repetitions'],seed=c['research']['seed'])
            if ci['interval'] is None: blockers.append(ci['state'])
            sensitivity=[block_interval(delta,c['calendar']['bootstrap_repetitions'],seed=c['research']['seed'],block=b) for b in (1,7)] if len(delta)>=20 else []
            comparisons.append({'model':model,'scenario':scenario,'baseline':'random','paired_daily_mean_difference_usd':statistics.mean(delta) if delta else None,
                                'uncertainty':ci,'block_sensitivity':sensitivity,'blockers':blockers,
                                'without_top3_closed_pnl_usd':report['closed_pnl_without_top3_usd'],
                                'conclusion':'insufficient_evidence'})
    result={'period':period,'protocol':reg['id'],'synthetic':bool(reg['synthetic']),'coverage':coverage,
            'metric':'net_portfolio_brl_with_recurring_costs','primary_family':9,'comparisons':comparisons,
            'conclusion':'Evidência insuficiente para vantagem líquida sustentável/executável; não promover automaticamente.',
            'stopping_rule':'Avaliar uma vez ao fim fixo da validação e uma vez ao fim fixo do teste; repetições ficam registradas.',
            'benchmark_SOL':'unavailable: série comparável não integrada'}
    if save:
        db.execute('INSERT INTO evaluations(at,period,protocol,result) VALUES(?,?,?,?)',(at,period,reg['id'],canonical(result)))
    return result
