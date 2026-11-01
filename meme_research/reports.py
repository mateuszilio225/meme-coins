from __future__ import annotations
import collections, datetime as dt, json, math, random, statistics, time
from .config import D
from .service import protocol
from .finance import break_even

HORIZONS=(300,900,1800,3600,14400,86400)

def guard(db,period,now=None):
    _,_,schedule=protocol(db)
    if period not in schedule: raise ValueError('period')
    if period in ('validation','test') and (time.time() if now is None else now)<schedule[period][1]:
        raise ValueError('Período reservado: resultados ocultos até o fim pré-registrado; não ajuste regras com o holdout.')

def rows(db,table,period,limit=100):
    guard(db,period)
    if table not in ('alerts','decisions','positions','orders'): raise ValueError(table)
    if table in ('positions','orders'):
        return [dict(r) for r in db.execute(f'SELECT t.* FROM {table} t JOIN wallets w ON w.id=t.wallet WHERE w.period=? ORDER BY t.id DESC LIMIT ?',(period,limit))]
    return [dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE period=? ORDER BY id DESC LIMIT ?',(period,limit))]

def health(db,path):
    from . import __version__
    import sys
    last=db.execute("SELECT at,detail FROM events WHERE kind='cycle' ORDER BY id DESC LIMIT 1").fetchone()
    error=db.execute("SELECT at,kind,detail FROM events WHERE kind IN ('source_unavailable','quote_unavailable','rpc_unavailable') ORDER BY id DESC LIMIT 1").fetchone()
    _,c,_=protocol(db)
    return {'version':__version__,'python':sys.version,'interpreter':sys.executable,'project':str(__import__('pathlib').Path(__file__).resolve().parent.parent),
            'database':str(path.resolve()),'synthetic':c['research']['synthetic'],
            'modules':{'radar':True,'paper':True,'quotes':c['research']['quotes_enabled'],'rpc':c['research']['rpc_enabled']},
            'last_cycle':dict(last) if last else None,'data_age_seconds':time.time()-last['at'] if last else None,
            'last_error':dict(error) if error else None,
            'note':'Sem ciclos: inicie run. Zero sinais: veja moonshot-quality e decisões; zero operações pode ser abstenção correta.'}

def quality(db,period):
    guard(db,period)
    _,_,schedule=protocol(db)
    start,end=schedule[period]
    obs=db.execute('SELECT * FROM observations WHERE period=? AND received>=? AND received<? ORDER BY mint,pair,source,received',(period,start,end)).fetchall()
    counts=collections.Counter(); gaps=[]; previous={}; price_ts=0
    for o in obs:
        for k in ('price','liquidity','volume'):
            counts[k+('_missing' if o[k] is None else '_zero' if D(o[k])==0 else '_present')]+=1
        price_ts+=o['provider_ts'] is not None
        key=(o['mint'],o['pair'],o['source'])
        if key in previous:
            delta=o['received']-previous[key]['received']; gaps.append(delta)
            if o['fingerprint']==previous[key]['fingerprint']: counts['repeated_fingerprint']+=1
        previous[key]=o
    reasons=collections.Counter()
    for r in db.execute('SELECT reasons FROM decisions WHERE period=?',(period,)):
        reasons.update(json.loads(r[0]))
    api=[dict(r) for r in db.execute('SELECT provider,state,count(*) AS count FROM api_calls GROUP BY provider,state')]
    return {'synthetic':bool(protocol(db)[0]['synthetic']),'period':period,'observations':len(obs),'fields':dict(counts),
            'provider_timestamps':price_ts,'largest_gap_seconds':max(gaps) if gaps else None,
            'decision_reasons':dict(reasons),'api_lifetime_counts':api,
            'coverage_note':'Universo parcial de perfis; ausência de dados não comprova perda total ou fraude.'}

def outcome(db,anchor,horizon,tolerance=180):
    end=anchor['received']+horizon
    _,_,schedule=protocol(db)
    if end>schedule[anchor['period']][1]: return {'state':'crosses_period','return':None,'hit':{str(x):False for x in (1,2,5)}}
    history=db.execute('SELECT * FROM observations WHERE mint=? AND pair=? AND source=? AND period=? AND received>=? AND received<=? ORDER BY received,id',
        (anchor['mint'],anchor['pair'],anchor['source'],anchor['period'],anchor['received'],min(end+tolerance,schedule[anchor['period']][1]-0.000001))).fetchall()
    hits={str(x):False for x in (1,2,5)}
    if not anchor['price']: return {'state':'missing_anchor','return':None,'hit':hits}
    prices=[r for r in history if r['price'] is not None]
    for r in prices:
        if r['received']<=end:
            ret=float(D(r['price'])/D(anchor['price'])-1)
            for x in (1,2,5): hits[str(x)] |= ret>=x
    terminal=min((r for r in prices if abs(r['received']-end)<=tolerance),key=lambda r:abs(r['received']-end),default=None)
    selected=[r for r in history if r['received']<=end]
    # No nearest-neighbour replacement of missing prices; gaps assessed on valid observations too.
    valid_times=[anchor['received']]+[r['received'] for r in prices if r['received']<=end]+[end]
    gap=max((b-a for a,b in zip(valid_times,valid_times[1:])),default=horizon)
    complete=bool(terminal and gap<=180 and not any(r['price'] is None for r in selected))
    return {'state':'complete' if complete else 'incomplete','return':float(D(terminal['price'])/D(anchor['price'])-1) if terminal else None,
            'hit':hits,'gap_seconds':gap,'terminal_at':terminal['received'] if terminal else None,
            'note':'Retorno observado; sem garantia de execução.'}

def observational(db,period,model='A'):
    guard(db,period)
    anchors=db.execute('SELECT o.*,d.score FROM alerts a JOIN decisions d ON d.id=a.decision JOIN observations o ON o.id=d.obs WHERE a.period=? AND a.model=? ORDER BY a.at',(period,model)).fetchall()
    results=[]
    for h in HORIZONS:
        outcomes=[outcome(db,a,h) for a in anchors]
        complete=[o for o in outcomes if o['state']=='complete']
        hits=sum(o['hit']['1'] for o in complete); incomplete=len(outcomes)-len(complete)
        results.append({'horizon_seconds':h,'alerts':len(anchors),'complete':len(complete),'incomplete':incomplete,
                        'precision_100_complete':hits/len(complete) if complete else None,
                        'precision_100_bounds':[hits/len(outcomes),(hits+incomplete)/len(outcomes)] if outcomes else None})
    bins=[]
    for lo in range(0,100,20):
        group=[(a,outcome(db,a,1800)) for a in anchors if lo<=a['score']<(lo+20 if lo<80 else 101)]
        complete=[o for _,o in group if o['state']=='complete']
        bins.append({'score_range':[lo,min(100,lo+20)],'n':len(group),'complete':len(complete),
                     'mean_return_30m':statistics.mean(o['return'] for o in complete) if complete else None})
    return {'model':model,'anchor':'persisted_alert','horizons':results,'score_bins':bins,
            'calibration':'Não treinada; score não é probabilidade. Sem amostra suficiente não inferir relação.',
            'recall_note':'Use missed para o universo observado; alertas com referências distintas não definem recall comum.'}

def missed(db,period,horizon=1800):
    guard(db,period)
    # First observation co-measured for all models, not hindsight-selected entry.
    anchors=db.execute('SELECT o.* FROM observations o JOIN (SELECT mint,min(id) id FROM observations WHERE period=? GROUP BY mint) first ON first.id=o.id',(period,)).fetchall()
    result=[]; complete_n=0; targets=0; detected=collections.Counter()
    for a in anchors:
        o=outcome(db,a,horizon)
        complete_n+=o['state']=='complete'
        if not any(o['hit'].values()): continue
        targets+=o['state']=='complete'
        decisions=[dict(r) for r in db.execute('SELECT model,at,score,eligible,selected,reasons,features FROM decisions WHERE obs IN (SELECT id FROM observations WHERE mint=? AND pair=? AND source=? AND period=? AND received<=?) ORDER BY at,id',
                      (a['mint'],a['pair'],a['source'],period,a['received']+horizon))]
        early={m:False for m in ('A','B','C')}
        hit_at=db.execute('SELECT received FROM observations WHERE mint=? AND pair=? AND source=? AND period=? AND received>=? AND received<=? AND CAST(price AS REAL)>=? ORDER BY received LIMIT 1',
            (a['mint'],a['pair'],a['source'],period,a['received'],a['received']+horizon,float(D(a['price'])*2))).fetchone()
        for d in decisions:
            if d['model'] in early and d['selected'] and hit_at and d['at']<hit_at[0]: early[d['model']]=True
        if o['state']=='complete': detected.update(m for m,v in early.items() if v)
        result.append({'mint':a['mint'],'pair':a['pair'],'first_observation':a['received'],'outcome':o,'selected_before_100':early,
                       'decisions':decisions,'before_discovery':'unknown: sem fonte histórica independente',
                       'execution':'Alta observada não verifica compra/venda; consultar orders/fills/quotes.'})
    return {'anchor':'first_observation_same_pair','universe':len(anchors),'complete':complete_n,'complete_100_targets':targets,
            'recall_observed_100':{m:detected[m]/targets if targets else None for m in ('A','B','C')},'cases':result,
            'limitation':'Recall antes do alvo é métrica descritiva de detecção, não recall de entrada lucrativa ou de todo o mercado.'}

def max_drawdown(values,initial):
    peak=initial; maximum=D(0)
    for x in values:
        peak=max(peak,x)
        if peak>0: maximum=max(maximum,(peak-x)/peak)
    return maximum

def wallet_report(db,w,c,schedule,at):
    positions=db.execute('SELECT * FROM positions WHERE wallet=?',(w['id'],)).fetchall()
    closed=[p for p in positions if p['state']=='closed']; unresolved=[p for p in positions if p['state']!='closed']
    pnls=[D(p['pnl']) for p in closed]; wins=[p for p in pnls if p>0]; losses=[p for p in pnls if p<0]
    fills=db.execute('SELECT * FROM fills WHERE wallet=?',(w['id'],)).fetchall()
    initial=D(w['initial']); fx=D(c['research']['fx_brl_per_usd']); cash=D(w['cash'])
    start,end=schedule[w['period']]; elapsed=max(0,min(at,end)-start)
    infrastructure=D(0) if w['strategy']=='cash' else (D(c['research']['monthly_infrastructure_brl'])+D(c['research']['monthly_data_brl']))*D(elapsed)/D(30*86400)
    eq=db.execute('SELECT * FROM equity WHERE wallet=? ORDER BY at,id',(w['id'],)).fetchall()
    last=eq[-1] if eq else None
    marked=D(last['marked']) if last and last['marked'] is not None else None
    sorted_pnls=sorted(pnls,reverse=True)
    orders=collections.Counter(r[0] for r in db.execute('SELECT state FROM orders WHERE wallet=?',(w['id'],)))
    costs={k:str(sum((D(f[k]) for f in fills),D(0))) for k in ('fee','network','embedded')}
    failure=sum((-D(r[0]) for r in db.execute("SELECT delta FROM ledger WHERE wallet=? AND kind='onchain_failure'",(w['id'],))),D(0))
    total_realized=sum(pnls,D(0))+sum((D(p['pnl']) for p in unresolved),D(0))-failure
    grouped={name:collections.defaultdict(lambda:D(0)) for name in ('mint','utc_day','utc_hour','entry_liquidity_band')}
    for pos in closed:
        entry=db.execute('SELECT liquidity FROM observations WHERE id=?',(pos['entry_obs'],)).fetchone()
        liquidity=D(entry['liquidity']) if entry and entry['liquidity'] is not None else None
        keys={'mint':pos['mint'],'utc_day':dt.datetime.fromtimestamp(pos['closed_at'],dt.timezone.utc).strftime('%Y-%m-%d'),
              'utc_hour':dt.datetime.fromtimestamp(pos['closed_at'],dt.timezone.utc).strftime('%H'),
              'entry_liquidity_band':'unknown' if liquidity is None else '<25k' if liquidity<25000 else '25k-100k' if liquidity<100000 else '>=100k'}
        for name,key in keys.items(): grouped[name][key]+=D(pos['pnl'])
    pnl_total=sum(pnls,D(0))
    removal={name:[{'removed':key,'closed_pnl_remaining_usd':str(pnl_total-value)} for key,value in sorted(groups.items())] for name,groups in grouped.items()}
    streak=0; max_streak=0
    for pos in sorted(closed,key=lambda x:x['closed_at']):
        streak=streak+1 if D(pos['pnl'])<0 else 0
        max_streak=max(streak,max_streak)
    return {'wallet':w['id'],'strategy':w['strategy'],'scenario':w['scenario'],'period':w['period'],
            'execution_class':'exact_size_quote_required_conditional' if w['strategy'] in ('main','main_random') and c['policy']['portfolio_require_quote'] else 'conditional_unverified',
            'capital_initial_usd':str(initial),'capital_brl':'400','cash_usd':str(cash),'reserved_usd':str(__import__('meme_research.finance',fromlist=['reserved']).reserved(db,w['id'])),
            'closed':len(closed),'open_or_inconclusive':len(unresolved),'inconclusive':sum(p['state']=='inconclusive' for p in unresolved),
            'closed_pnl_usd':str(sum(pnls,D(0))),'partial_realized_usd':str(sum((D(p['pnl']) for p in unresolved),D(0))),
            'onchain_failure_stress_cost_usd':str(failure),'realized_total_usd':str(total_realized),
            'marked_equity_usd_before_exit_costs':str(marked) if marked is not None else None,
            'marked_age_seconds':at-last['at'] if last else None,
            'zero_recovery_equity_usd':str(cash),'zero_recovery_net_brl':str((cash-initial)*fx-infrastructure),
            'net_brl_if_fully_closed':str((cash-initial)*fx-infrastructure) if not unresolved else None,
            'infrastructure_brl_once':str(infrastructure),'cost_assumptions_confirmed':c['research']['monthly_costs_confirmed'],
            'initial_fx_equivalence_only':True,'costs_usd':costs,'orders':dict(orders),
            'win_rate_closed':len(wins)/len(pnls) if pnls else None,
            'mean_win_usd':str(sum(wins,D(0))/len(wins)) if wins else None,
            'mean_loss_usd':str(sum(losses,D(0))/len(losses)) if losses else None,
            'profit_factor_closed':str(sum(wins,D(0))/-sum(losses,D(0))) if losses else None,
            'expectancy_usd':str(total_realized/sum(orders.values())) if orders and not unresolved and not orders.get('pending',0) else None,
            'expectancy_denominator':'Todas as ordens: preenchidas, frustradas e expiradas; sem inferência enquanto houver posições ou ordens pendentes.',
            'expectancy_note':'Indefinida com posições abertas/inconclusivas; inclui falhas no resultado global.',
            'drawdown_marked_observed':str(max_drawdown([D(x['marked']) for x in eq if x['marked'] is not None],initial)),
            'drawdown_missing_marks':sum(x['marked'] is None for x in eq),
            'drawdown_zero_recovery_stress':str(max_drawdown([D(x['stress']) for x in eq],initial)),
            'exposure_cost_basis_usd':last['exposure'] if last else '0',
            'mean_holding_seconds_closed':statistics.mean(p['closed_at']-p['entry_at'] for p in closed) if closed else None,
            'closed_pnl_leave_group_out':removal,'maximum_closed_loss_streak':max_streak,
            'closed_pnl_without_best_usd':str(sum(pnls,D(0))-sum(sorted_pnls[:1],D(0))),
            'closed_pnl_without_top3_usd':str(sum(pnls,D(0))-sum(sorted_pnls[:3],D(0))),
            'conclusion':'Evidência insuficiente. Resultado sintético/condicional ou amostra ainda não validada.'}

def profitability(db,period,at=None):
    guard(db,period,at)
    reg,c,schedule=protocol(db); at=time.time() if at is None else at
    return {'synthetic':bool(reg['synthetic']),'data_category':c['research'].get('data_category','synthetic' if reg['synthetic'] else 'real_observations_conditional_fills'),'period':period,'protocol':reg['id'],'currency_note':'USD contábil; BRL ao FX inicial, não FX corrente.',
            'capital_note':'Carteiras independentes são contrafactuais, nunca somar seus resultados. main é um portfólio único de R$400 por cenário.',
            'wallets':[wallet_report(db,w,c,schedule,at) for w in db.execute('SELECT * FROM wallets WHERE period=? ORDER BY id',(period,))]}

def forensics(db,period):
    guard(db,period); result=[]
    _,_,schedule=protocol(db)
    for pos in db.execute('SELECT p.* FROM positions p JOIN wallets w ON p.wallet=w.id WHERE w.period=?',(period,)):
        fills=[dict(r) for r in db.execute('SELECT * FROM fills WHERE position=? ORDER BY at,id',(pos['id'],))]
        signal=db.execute('SELECT * FROM observations WHERE id=?',(pos['signal'],)).fetchone()
        entry=db.execute('SELECT * FROM observations WHERE id=?',(pos['entry_obs'],)).fetchone()
        history=db.execute('SELECT * FROM observations WHERE mint=? AND pair=? AND source=? AND period=? AND received>=? AND received<=? ORDER BY received,id',
            (pos['mint'],pos['pair'],pos['source'],period,signal['received'],min(pos['closed_at'] or time.time(),schedule[period][1]-0.000001))).fetchall()
        buy=next(f for f in fills if f['side']=='buy'); sells=[f for f in fills if f['side']=='sell']
        reference=sum((D(f['quantity'])*(D(f['mid'])-D(buy['mid'])) for f in sells),D(0))
        totalcost=sum((D(f['fee'])+D(f['network'])+D(f['embedded']) for f in fills),D(0))
        evidence={'signal_to_entry_price_change':str(D(entry['price'])/D(signal['price'])-1) if entry['price'] and signal['price'] else None,
                  'signal_to_entry_seconds':pos['entry_at']-signal['received'],
                  'liquidity_signal':signal['liquidity'],'liquidity_entry':entry['liquidity'],
                  'prices_observed':[{'at':r['received'],'price':r['price'],'liquidity':r['liquidity']} for r in history],
                  'gross_reference_closed_usd':str(reference) if pos['state']=='closed' else None,
                  'execution_costs_usd':str(totalcost),'pnl_usd':pos['pnl'],'exit_reason':pos['exit_reason'],
                  'features_at_signal':[dict(x) for x in db.execute('SELECT model,score,features,reasons FROM decisions WHERE obs=?',(pos['signal'],))]}
        result.append({'position':dict(pos),'fills':fills,'evidence':evidence,
                       'causality':'unknown. Custos têm decomposição contábil; seleção, descoberta e regras de saída exigem contrafactuais pareados, não atribuição automática.',
                       'discovery':dict(db.execute('SELECT * FROM tokens WHERE mint=?',(pos['mint'],)).fetchone())})
    return {'period':period,'cases':result}

def audit(db):
    failures=[]
    for w in db.execute('SELECT * FROM wallets'):
        balance=sum((D(x[0]) for x in db.execute('SELECT delta FROM ledger WHERE wallet=?',(w['id'],))),D(0))
        if balance!=D(w['cash']) or balance<0: failures.append(w['id']+':cash')
        for p in db.execute('SELECT * FROM positions WHERE wallet=?',(w['id'],)):
            fills=db.execute('SELECT side,quantity FROM fills WHERE position=?',(p['id'],)).fetchall()
            qty=sum((D(x['quantity'])*(1 if x['side']=='buy' else -1) for x in fills),D(0))
            if abs(qty-D(p['quantity']))>D('1e-22'): failures.append(str(p['id'])+':quantity')
    for reg in db.execute('SELECT * FROM protocols'):
        from .config import digest
        if digest(json.loads(reg['config']))!=reg['id']: failures.append('protocol hash')
    integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    foreign=[list(x) for x in db.execute('PRAGMA foreign_key_check')]
    return {'integrity':integrity,'foreign_keys':foreign,'reconciliation_failures':failures,'ok':integrity=='ok' and not foreign and not failures}

def economic_table(c):
    fx=D(c['research']['fx_brl_per_usd'])
    if fx<=0: raise ValueError('Informe câmbio identificado antes do cálculo econômico.')
    result=[]
    for brl in (10,20,30,40,80):
        for name,s in c['scenarios'].items():
            for liquidity in (10000,25000,100000):
                b=D(brl)/fx; be=break_even(b,liquidity,s)
                result.append({'position_brl':brl,'position_usd':str(b),'liquidity_usd':liquidity,'scenario':name,
                               'required_price_increase_fraction':str(be) if be is not None else None,
                               'passes_cost_gate':be is not None and be<=D(c['policy']['max_break_even']),
                               'assumptions':'Uma compra + venda integral; parcial adiciona fills/custos. Sem probabilidade de lucro.'})
    return {'fx':str(fx),'source':c['research']['fx_source'],'table':result,
            'monthly_cost_sensitivity_brl':[{'cost':x,'fraction_of_capital':str(D(x)/400)} for x in (0,20,50,100)],
            'note':'Sem retorno esperado verificado não se pode afirmar viabilidade. Maior frequência não implica maior lucro.'}

def spearman(pairs):
    if len(pairs)<20: return None
    def ranks(values):
        order=sorted(range(len(values)),key=values.__getitem__); output=[0.0]*len(values); i=0
        while i<len(order):
            j=i+1
            while j<len(order) and values[order[j]]==values[order[i]]: j+=1
            for k in range(i,j): output[order[k]]=(i+j-1)/2
            i=j
        return output
    a=ranks([x for x,y in pairs]); b=ranks([y for x,y in pairs]); ma=statistics.mean(a); mb=statistics.mean(b)
    den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/den if den else None

def score_diagnostics(db,period):
    guard(db,period); results=[]
    for model in ('A','B','C'):
        # First ready screen per mint/model; distinct from the alert cohort.
        decisions=db.execute('''SELECT d.*,o.mint FROM decisions d JOIN observations o ON o.id=d.obs
            JOIN (SELECT min(d2.id) id FROM decisions d2 JOIN observations o2 ON o2.id=d2.obs
                  WHERE d2.period=? AND d2.model=? AND json_extract(d2.features,'$.ready')=1 GROUP BY o2.mint) x ON d.id=x.id''',(period,model)).fetchall()
        pairs=[]; bins=collections.defaultdict(list); components=collections.defaultdict(lambda:{'lost_selections':0,'observed_winners_lost':0,'complete':0})
        for d in decisions:
            anchor=db.execute('SELECT * FROM observations WHERE id=?',(d['obs'],)).fetchone(); out=outcome(db,anchor,1800)
            if out['state']!='complete': continue
            pairs.append((d['score'],out['return'])); bins[int(min(99,d['score'])//20)*20].append(out['return'])
            f=json.loads(d['features']); score_parts=f.get('score_components',{}).get(model,{})
            for key,value in score_parts.items():
                item=components[key]; item['complete']+=1
                _,cfg,_=protocol(db); threshold=cfg['policy']['score_threshold']
                removed=d['score']>=threshold and d['score']-value<threshold
                item['lost_selections']+=removed; item['observed_winners_lost']+=removed and out['hit']['1']
        pnls=[(d['score'],float(p[0])) for d in decisions for p in db.execute("SELECT pnl FROM positions WHERE signal=? AND wallet=? AND state='closed'",(d['obs'],f'{period}:{model}:base'))]
        results.append({'model':model,'anchor':'first_ready_screen','complete_30m':len(pairs),'spearman_score_return':spearman(pairs),
                        'spearman_score_closed_base_pnl':spearman(pnls),'closed_pnl_sample':len(pnls),
                        'bins':[{'range':[lo,lo+20],'n':len(values),'mean_return':statistics.mean(values),'extreme_loss_below_50pct':sum(v<=-.5 for v in values)} for lo,values in sorted(bins.items())],
                        'component_removal_screen_sensitivity':dict(components),
                        'limitation':'Remoção do componente só mede cruzamento de limiar na triagem; não simula novo ranking, fills ou causalidade. PnL exclui inconclusivas nesta correlação descritiva; veja relatório global.'})
    return {'models':results,'calibration':'Não treinada; correlação nula/ausente não autoriza converter score em probabilidade.'}
