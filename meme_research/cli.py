from __future__ import annotations
import argparse, contextlib, copy, json, os, sys, tempfile, time
from pathlib import Path
from .config import ROOT, load, db_path, digest
from .data import Sources, DataUnavailable
from .store import connect, migrate, register, collector_lock, backup
from .service import protocol, collect_once
from . import reports

COMMANDS=('init','run','watch','health','audit','moonshot','moonshot-alerts','moonshot-trades',
          'moonshot-profitability','moonshot-forensics','moonshot-missed','moonshot-quality','moonshot-compare','moonshot-scores',
          'evaluate','demo','fx','economics','backup','ablate')

def output(value): print(json.dumps(value,indent=2,ensure_ascii=False,default=str,allow_nan=False))

def active(db,c):
    reg,frozen,_=protocol(db)
    candidate=copy.deepcopy(c)
    # init --ptax explicitly freezes an observed FX binding. Config's zero means use it.
    if candidate['research']['fx_brl_per_usd']=='0' and not candidate['research']['fx_source']:
        for k in ('fx_brl_per_usd','fx_source','fx_available_at'): candidate['research'][k]=frozen['research'][k]
    protocol(db,candidate)
    return candidate

def main(argv=None):
    parser=argparse.ArgumentParser(description='Moonshot Profit Research — somente dados e simulação; nunca envia transações.')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--version',action='version',version=__import__('meme_research').__version__)
    sub=parser.add_subparsers(dest='command',required=True)
    for cmd in COMMANDS:
        p=sub.add_parser(cmd)
        if cmd=='run':
            p.add_argument('--once',action='store_true'); p.add_argument('--cycles',type=int,default=0)
        elif cmd=='init': p.add_argument('--ptax',action='store_true')
        elif cmd in ('demo','backup','ablate'): p.add_argument('--output',type=Path,required=True)
        elif cmd=='watch': p.add_argument('--follow',action='store_true')
        if cmd.startswith('moonshot') or cmd in ('evaluate','watch'):
            p.add_argument('--period',choices=('development','validation','test'),default='development')
    args=parser.parse_args(argv)
    try:
        c,config_path=load(args.config); path=db_path(c,config_path)
        if args.command=='demo':
            from .demo import create
            output(create(args.output,c)); return 0
        if args.command=='fx':
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'fx.sqlite'; migrate(p)
                with contextlib.closing(connect(p)) as db,db: output(Sources(db).fx())
            return 0
        if args.command=='init':
            if c['research']['synthetic']: raise ValueError('Use demo para dados sintéticos separados.')
            with collector_lock(path):
                migrate(path)
                with contextlib.closing(connect(path)) as db,db:
                    if args.ptax:
                        fx=Sources(db).fx()
                        for k in ('fx_brl_per_usd','fx_source','fx_available_at'): c['research'][k]=fx[k]
                    h=register(db,c,time.time())
                    output({'registered':h,'database':str(path),'fx':c['research']['fx_source'],'note':'Regras congeladas. Nenhuma ordem criada. Capital fictício.'})
            return 0
        if args.command=='economics':
            if path.exists():
                with contextlib.closing(connect(path,True)) as db: _,c,_=protocol(db)
            output(reports.economic_table(c)); return 0
        if args.command=='ablate':
            from .ablation import run
            output(run(path,args.output)); return 0
        if args.command=='backup':
            with collector_lock(path): backup(path,args.output)
            output({'backup':str(args.output.resolve())}); return 0
        if args.command=='run':
            if args.cycles<0: raise ValueError('--cycles')
            if not path.is_file(): raise FileNotFoundError('Execute init --ptax antes de run. Banco não criado automaticamente.')
            with collector_lock(path), contextlib.closing(connect(path)) as db:
                c=active(db,c)
                if c['research']['synthetic']: raise ValueError('Banco sintético não aceita coleta real.')
                n=0
                while True:
                    with db: count=collect_once(db,c)
                    n+=1; output({'cycle':n,'observations':count,'database':str(path),'mode':'research_only'})
                    if args.once or (args.cycles and n>=args.cycles): break
                    time.sleep(c['research']['cycle_seconds'])
            return 0
        if args.command=='evaluate':
            from .evaluate import evaluate
            with collector_lock(path), contextlib.closing(connect(path)) as db,db: output(evaluate(db,args.period))
            return 0
        with contextlib.closing(connect(path,True)) as db:
            while True:
                cmd=args.command
                if cmd=='health': result=reports.health(db,path)
                elif cmd=='audit':
                    result=reports.audit(db); output(result); return 0 if result['ok'] else 1
                elif cmd in ('watch','moonshot-alerts'):
                    result=reports.rows(db,'alerts',args.period)
                    if cmd=='watch':
                        _,cfg,_=protocol(db)
                        result=result[:cfg['research']['max_visual_alerts']]
                elif cmd=='moonshot': result=reports.rows(db,'decisions',args.period)
                elif cmd=='moonshot-trades': result={'orders':reports.rows(db,'orders',args.period),'positions':reports.rows(db,'positions',args.period)}
                elif cmd in ('moonshot-profitability','moonshot-compare'): result=reports.profitability(db,args.period)
                elif cmd=='moonshot-forensics': result=reports.forensics(db,args.period)
                elif cmd=='moonshot-missed': result=reports.missed(db,args.period)
                elif cmd=='moonshot-quality': result=reports.quality(db,args.period)
                elif cmd=='moonshot-scores': result={'scores':reports.score_diagnostics(db,args.period),'alerts':reports.observational(db,args.period)}
                else: raise ValueError(cmd)
                _,frozen,_=protocol(db)
                output({'synthetic':frozen['research']['synthetic'],'data_mode':frozen['research'].get('data_category','synthetic' if frozen['research']['synthetic'] else 'real_observations_conditional_fills'),'result':result})
                if cmd!='watch' or not args.follow: break
                time.sleep(10)
        return 0
    except KeyboardInterrupt:
        print('Interrompido; transações incompletas revertidas. Histórico preservado.',file=sys.stderr); return 130
    except (ValueError,OSError,RuntimeError,DataUnavailable, __import__('sqlite3').Error) as exc:
        # No raw HTTP request/response/headers or environment variables in errors.
        if isinstance(exc,DataUnavailable): message='Fonte indisponível: '+str(exc)
        elif isinstance(exc,OSError): message='Falha de arquivo/rede: '+type(exc).__name__
        else: message=str(exc)
        print(message,file=sys.stderr); return 1
