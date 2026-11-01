from __future__ import annotations
import copy, hashlib, json, math, tomllib
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = lambda v: Decimal(str(v))

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def load(path=None):
    p = Path(path).resolve() if path else ROOT / 'config.toml'
    with p.open('rb') as f:
        c = tomllib.load(f)
    validate(c)
    return c, p

def db_path(c, config_path):
    p = Path(c['research']['database'])
    return p if p.is_absolute() else config_path.parent / p

def validate(c):
    r, p, cal = c['research'], c['policy'], c['calendar']
    for group,keys in ((r,('synthetic','rpc_enabled','quotes_enabled','monthly_costs_confirmed')),(p,('require_provider_timestamp','portfolio_require_quote'))):
        for k in keys:
            if type(group[k]) is not bool: raise ValueError(k)
    if D(r['capital_brl']) != 400:
        raise ValueError('Este protocolo exige capital fictício total de R$400 por carteira.')
    for k in ('fx_brl_per_usd', 'monthly_infrastructure_brl', 'monthly_data_brl'):
        if not D(r[k]).is_finite() or D(r[k]) < 0:
            raise ValueError(k)
    for k in ('position_fraction', 'exposure_fraction', 'reserve_fraction', 'partial_fraction',
              'stop_fraction', 'trailing_fraction', 'max_capacity_fraction', 'liquidity_exit_retention'):
        if not 0 < D(p[k]) < 1: raise ValueError(k)
    if D(p['exposure_fraction']) + D(p['reserve_fraction']) > 1: raise ValueError('exposure/reserve')
    if D(p['position_fraction']) > D(p['exposure_fraction']): raise ValueError('position/exposure')
    for k in ('max_break_even', 'min_notional_usd', 'min_liquidity_usd'):
        if not D(p[k]).is_finite() or D(p[k]) <= 0: raise ValueError(k)
    if D(p['take_profit_multiple']) <= 1: raise ValueError('take_profit_multiple')
    for group, keys in ((p, ('max_positions','max_pair_age_minutes','min_observations','min_spacing_seconds',
                           'history_seconds','max_gap_seconds','max_snapshot_age_seconds', 'max_unchanged_seconds',
                           'entry_timeout_seconds','exit_timeout_seconds','max_holding_seconds')),
                        (r, ('cycle_seconds','max_tokens_per_cycle','max_visual_alerts')),
                        (cal, ('development_days','embargo_days','validation_days','test_days','min_closed_mints','min_days','bootstrap_repetitions'))):
        for k in keys:
            if type(group[k]) is not int or group[k] <= 0: raise ValueError(k)
    if p['min_observations'] < 3 or not 0 <= p['score_threshold'] <= 100: raise ValueError('radar')
    if p['entry_mode'] not in ('immediate','confirmation','consolidation','recovery'): raise ValueError('entry_mode')
    if p['exit_mode'] not in ('fixed','volatility','momentum'): raise ValueError('exit_mode')
    for name, s in c['scenarios'].items():
        for k in ('fee_bps','spread_bps','slippage_bps','network_usd','priority_usd','liquidity_multiplier','impact_multiplier'):
            if not D(s[k]).is_finite() or D(s[k]) < 0: raise ValueError(f'{name}.{k}')
        if D(s['liquidity_multiplier']) <= 0: raise ValueError('liquidity_multiplier')
        if D(s['fee_bps']) >= 10000 or D(s['slippage_bps'])+D(s['spread_bps'])/2 >= 10000: raise ValueError('cost range')
        if type(s['latency_seconds']) is not int or s['latency_seconds'] < 1: raise ValueError('latency')
        if type(s['failure_every_n']) is not int or s['failure_every_n'] < 0: raise ValueError('failure_every_n')
    if set(c['scenarios']) != {'optimistic','base','adverse'}: raise ValueError('scenarios')

def calendar(c, start):
    day = 86400
    v = start + (c['calendar']['development_days'] + c['calendar']['embargo_days']) * day
    t = v + (c['calendar']['validation_days'] + c['calendar']['embargo_days']) * day
    return {'development': [start, start+c['calendar']['development_days']*day],
            'validation': [v, v+c['calendar']['validation_days']*day],
            'test': [t, t+c['calendar']['test_days']*day]}

def period_at(schedule, ts):
    return next((name for name, (a,b) in schedule.items() if a <= ts < b), 'embargo')

def toml_text(c):
    """Serialize this project's scalar/nested configuration without extra dependencies."""
    lines=[]
    def section(mapping,path):
        if path: lines.append('['+'.'.join(path)+']')
        for key,value in mapping.items():
            if isinstance(value,dict): continue
            if isinstance(value,bool): text='true' if value else 'false'
            elif isinstance(value,(int,float)): text=str(value)
            elif isinstance(value,str): text=json.dumps(value,ensure_ascii=False)
            else: raise ValueError('unsupported TOML value')
            lines.append(key+' = '+text)
        lines.append('')
        for key,value in mapping.items():
            if isinstance(value,dict): section(value,path+[key])
    section(c,[])
    return '\n'.join(lines)
