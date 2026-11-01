"""Historical DEVELOPMENT-only fixed-signal execution ablations. Never prospective alerts."""
from __future__ import annotations
import contextlib, copy, json
from pathlib import Path
from .config import digest, canonical
from .store import connect, migrate, register, event, collector_lock
from .service import protocol, ingest
from .finance import process, submit, ensure_wallets, tick
from .reports import audit, profitability

VARIANTS={'reference':{},'entry_confirmation':{'entry_mode':'confirmation'},'exit_momentum':{'exit_mode':'momentum'}}

def run(source,destination):
    dest=Path(destination).resolve()
    if dest.exists(): raise FileExistsError('Diretório de ablação já existe; não sobrescrito.')
    with contextlib.closing(connect(source,True)) as src:
        src.execute('BEGIN')  # Consistent SQLite snapshot, including under a live collector.
        reg,c,schedule=protocol(src)
        if c['policy']['entry_mode']!='immediate' or c['policy']['exit_mode']!='fixed':
            raise ValueError('Ablações fixas exigem referência immediate/fixed; não combinar mudanças.')
        start,end=schedule['development']
        observations=[dict(x) for x in src.execute('SELECT * FROM observations WHERE period=? AND received>=? AND received<? ORDER BY received,id',('development',start,end))]
        cycles=[x[0] for x in src.execute("SELECT at FROM events WHERE kind='cycle' AND at>=? AND at<? ORDER BY at,id",(start,end))]
        signals=[dict(x) for x in src.execute("SELECT d.*,o.mint FROM decisions d JOIN observations o ON o.id=d.obs WHERE d.period='development' AND d.model='A' AND d.selected=1 ORDER BY d.at,d.id")]
        identifier=digest({'protocol':reg['id'],'observations':observations,'signals':signals,'cycles':cycles})
    dest.mkdir(parents=True)
    results=[]
    for name,override in VARIANTS.items():
        path=dest/(name+'.sqlite'); conf=copy.deepcopy(c)
        conf['research']['data_category']='historical_development_fixed_signal_ablation'
        conf['research']['source_snapshot']=identifier
        conf['policy'].update(override)
        migrate(path)
        with collector_lock(path), contextlib.closing(connect(path)) as db,db:
            register(db,conf,reg['registered'])
            ensure_wallets(db,conf,'development',reg['registered'])
            cursor=0; mapping={}
            for at in cycles:
                batch=[]
                while cursor<len(observations) and observations[cursor]['received']<=at:
                    batch.append(observations[cursor]); cursor+=1
                for original in batch:
                    new=ingest(db,[original],schedule,at)
                    if new:
                        mapping[original['id']]=new[0]
                        process(db,conf,db.execute('SELECT * FROM observations WHERE id=?',(new[0],)).fetchone())
                for sig in signals:
                    if sig['at']!=at or sig['obs'] not in mapping: continue
                    oid=mapping[sig['obs']]
                    cur=db.execute('INSERT INTO decisions(protocol,obs,model,period,at,score,eligible,selected,rank,reasons,features) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (digest(conf),oid,'A','development',at,sig['score'],1,1,1,'["historical_fixed_signal"]',sig['features']))
                    db.execute('INSERT INTO alerts(decision,mint,model,period,at) VALUES(?,?,?,?,?)',(cur.lastrowid,sig['mint'],'A','development',at))
                    obs=db.execute('SELECT * FROM observations WHERE id=?',(oid,)).fetchone()
                    submit(db,conf,{'A':obs},'development',at)
                tick(db,conf,at,schedule)
                event(db,at,'cycle',{'category':'replay_ablation','name':name})
            report=profitability(db,'development',cycles[-1] if cycles else start)
            report['wallets']=[x for x in report['wallets'] if x['strategy']=='A']
            results.append({'name':name,'changed_policy_fields':override,'audit':audit(db),'report':report})
    result={'category':'historical_development_fixed_signal_ablation','source_snapshot':identifier,
            'variants':results,'held_constant':'Sinais A registrados, dados, capital, calendário, cenários e latência.',
            'limitations':'Não mede seleção nem descoberta. Capital pode substituir oportunidades de forma diferente. Não é validação futura nem escolha autorizada de vencedor.'}
    (dest/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    return result
