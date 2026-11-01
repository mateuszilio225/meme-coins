from __future__ import annotations
import contextlib, copy, json, time
from pathlib import Path
from .config import load, canonical, digest, toml_text
from .data import normalize
from .store import migrate, connect, register, collector_lock
from .service import cycle
from .reports import audit, profitability

START=1700000000.0

def sample(mint,pair,at,price=1,liquidity=100000,buys=80,sells=20,volume=2000,source='synthetic'):
    raw={'chainId':'solana','pairAddress':pair,'dexId':'synthetic','baseToken':{'address':mint,'symbol':mint},
         'priceUsd':str(price) if price is not None else None,'liquidity':{'usd':liquidity} if liquidity is not None else {},
         'volume':{'m5':volume},'txns':{'m5':{'buys':buys,'sells':sells}},'pairCreatedAt':int((START-60)*1000),
         'demo_snapshot_at':at}
    obs=normalize(raw,at-1,at); obs['source']=source
    return obs

def create(destination,base_config=None):
    dest=Path(destination).resolve()
    config_dest=dest.with_suffix('.toml')
    if config_dest.exists(): raise FileExistsError('Configuração da demo já existe; não sobrescrita.')
    if dest.exists(): raise FileExistsError('Demo não sobrescreve arquivo existente; escolha outro --output.')
    c=copy.deepcopy(base_config or load()[0]); c['research'].update(synthetic=True,fx_brl_per_usd='5',fx_source='SYNTHETIC fixed 5 BRL/USD',fx_available_at=START-1,database=str(dest))
    migrate(dest)
    with collector_lock(dest), contextlib.closing(connect(dest)) as db:
        with db:
            register(db,c,START)
            # Each trajectory is explicitly synthetic. Includes pump/crash, late high score,
            # missing liquidity, an unsellable open position, and low/negative momentum.
            for step in range(85):
                at=START+step*60+2
                items=[]
                for index in range(7):
                    if index==0: price=1+step*.025 if step<12 else 1.3*max(.2,1-(step-12)*.018)
                    elif index==1: price=1+step*.05 if step<10 else .08
                    elif index==2: price=1+step*.012 if step<9 else .4
                    elif index==3: price=1+step*.025
                    elif index==4: price=1+step*.02 if step<8 else None
                    elif index==5: price=1+step*.005 if step<6 else 1.03+max(0,step-6)*.06
                    else: price=max(.05,1-step*.012)
                    liquidity=None if index==3 else (0 if index==4 and step>=8 else 100000)
                    items.append(sample(f'SYNTHETIC_{index}',f'POOL_{index}',at,price,liquidity,volume=2000+step*80))
                cycle(db,c,items,at)
            result={'demo_only':True,'audit':audit(db),'report':profitability(db,'development',at)}
    config_dest.write_text(toml_text(c),encoding='utf-8')
    result['config_path']=str(config_dest)
    result['database_path']=str(dest)
    return result
