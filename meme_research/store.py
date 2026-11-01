from __future__ import annotations
import contextlib, os, sqlite3, time
from pathlib import Path
from .config import canonical, digest, D, calendar
from . import __version__

SCHEMA = '''
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS protocols(id TEXT PRIMARY KEY, registered REAL NOT NULL, config TEXT NOT NULL, schedule TEXT NOT NULL, synthetic INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS tokens(mint TEXT PRIMARY KEY, discovered REAL NOT NULL, first_seen REAL, period TEXT, last_poll REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, mint TEXT NOT NULL, pair TEXT NOT NULL, source TEXT NOT NULL, requested REAL NOT NULL, received REAL NOT NULL, provider_ts REAL, price TEXT, liquidity TEXT, volume TEXT, buys INTEGER, sells INTEGER, pair_created REAL, fingerprint TEXT NOT NULL, quality TEXT NOT NULL, raw TEXT NOT NULL, period TEXT NOT NULL, UNIQUE(mint,pair,source,requested,fingerprint));
CREATE INDEX IF NOT EXISTS obs_history ON observations(mint,pair,source,received);
CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, protocol TEXT NOT NULL REFERENCES protocols(id), obs INTEGER NOT NULL REFERENCES observations(id), model TEXT NOT NULL, period TEXT NOT NULL, at REAL NOT NULL, score REAL NOT NULL, eligible INTEGER NOT NULL, selected INTEGER NOT NULL, rank INTEGER, reasons TEXT NOT NULL, features TEXT NOT NULL, UNIQUE(protocol,obs,model));
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, decision INTEGER NOT NULL REFERENCES decisions(id), mint TEXT NOT NULL, model TEXT NOT NULL, period TEXT NOT NULL, at REAL NOT NULL, UNIQUE(mint,model,period));
CREATE TABLE IF NOT EXISTS wallets(id TEXT PRIMARY KEY, strategy TEXT NOT NULL, scenario TEXT NOT NULL, period TEXT NOT NULL, initial TEXT NOT NULL, cash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, wallet TEXT NOT NULL REFERENCES wallets(id), mint TEXT NOT NULL, pair TEXT NOT NULL, source TEXT NOT NULL, signal INTEGER NOT NULL REFERENCES observations(id), created REAL NOT NULL, eligible REAL NOT NULL, expires REAL NOT NULL, budget TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL, position INTEGER);
CREATE TABLE IF NOT EXISTS positions(id INTEGER PRIMARY KEY, wallet TEXT NOT NULL REFERENCES wallets(id), mint TEXT NOT NULL, pair TEXT NOT NULL, source TEXT NOT NULL, signal INTEGER NOT NULL REFERENCES observations(id), entry_obs INTEGER NOT NULL REFERENCES observations(id), entry_at REAL NOT NULL, quantity TEXT NOT NULL, initial_quantity TEXT NOT NULL, cost TEXT NOT NULL, remaining_cost TEXT NOT NULL, entry_price TEXT NOT NULL, peak TEXT NOT NULL, partial INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL, exit_requested REAL, exit_reason TEXT, closed_at REAL, pnl TEXT NOT NULL DEFAULT '0');
CREATE TABLE IF NOT EXISTS fills(id INTEGER PRIMARY KEY, wallet TEXT NOT NULL REFERENCES wallets(id), position INTEGER NOT NULL REFERENCES positions(id), obs INTEGER NOT NULL REFERENCES observations(id), at REAL NOT NULL, side TEXT NOT NULL, quantity TEXT NOT NULL, price TEXT NOT NULL, mid TEXT NOT NULL, fee TEXT NOT NULL, network TEXT NOT NULL, embedded TEXT NOT NULL, cash_delta TEXT NOT NULL, reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY, wallet TEXT NOT NULL REFERENCES wallets(id), at REAL NOT NULL, delta TEXT NOT NULL, kind TEXT NOT NULL, ref INTEGER);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, at REAL NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS equity(id INTEGER PRIMARY KEY, wallet TEXT NOT NULL REFERENCES wallets(id), at REAL NOT NULL, cash TEXT NOT NULL, marked TEXT, stress TEXT NOT NULL, exposure TEXT NOT NULL, unresolved INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS api_state(provider TEXT PRIMARY KEY, next_at REAL NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0, window_start REAL NOT NULL DEFAULT 0, calls INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS api_calls(id INTEGER PRIMARY KEY, provider TEXT NOT NULL, endpoint TEXT NOT NULL, requested REAL NOT NULL, received REAL NOT NULL, state TEXT NOT NULL, status INTEGER);
CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, at REAL NOT NULL, expires REAL NOT NULL, data TEXT, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quotes(id INTEGER PRIMARY KEY, mint TEXT NOT NULL, requested REAL NOT NULL, received REAL NOT NULL, input_mint TEXT NOT NULL, output_mint TEXT NOT NULL, amount TEXT NOT NULL, out_amount TEXT, state TEXT NOT NULL, raw TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY, mint TEXT NOT NULL, received REAL NOT NULL, state TEXT NOT NULL, raw TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY, at REAL NOT NULL, period TEXT NOT NULL, protocol TEXT NOT NULL, result TEXT NOT NULL);
'''
IMMUTABLE = ('protocols','observations','decisions','alerts','fills','ledger','events','api_calls','quotes','facts','equity','evaluations')

def connect(path, readonly=False):
    p=Path(path).resolve()
    if readonly and not p.is_file(): raise FileNotFoundError(f'Banco inexistente: {p}. Execute init explicitamente.')
    db=sqlite3.connect(p.as_uri()+'?mode=ro' if readonly else str(p), uri=readonly, timeout=10)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    if readonly: db.execute('PRAGMA query_only=ON')
    else: db.execute('PRAGMA journal_mode=WAL')
    return db

def backup(path, destination):
    dest=Path(destination)
    # Exclusive creation prevents accidental backup overwrite.
    with dest.open('xb'): pass
    try:
        with contextlib.closing(connect(path, True)) as src, contextlib.closing(sqlite3.connect(dest)) as dst:
            src.backup(dst)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

def migrate(path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    existed=p.exists()
    with contextlib.closing(connect(p)) as db:
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version > 1: raise ValueError('Schema mais recente que o programa')
        if version == 1: return
        tables=db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if tables: raise ValueError('Banco externo/desconhecido: não migrado ou substituído')
        if existed: backup(p, str(p)+f'.pre-v1-{time.time_ns()}.bak')
        triggers=''
        for table in IMMUTABLE:
            for op in ('UPDATE','DELETE'):
                triggers+=f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{op} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,'immutable evidence'); END;\n"
        try: db.executescript('BEGIN IMMEDIATE;\n'+SCHEMA+triggers+'PRAGMA user_version=1; COMMIT;')
        except BaseException:
            db.rollback(); raise

@contextlib.contextmanager
def collector_lock(path):
    p=Path(str(path)+'.lock'); p.parent.mkdir(parents=True,exist_ok=True)
    f=p.open('a+b')
    try:
        if os.name=='nt':
            import msvcrt
            if p.stat().st_size==0: f.write(b'0'); f.flush()
            f.seek(0); msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        f.close(); raise RuntimeError('Outro processo usa este banco') from None
    try: yield
    finally:
        if os.name=='nt':
            f.seek(0); msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
        f.close()

def event(db, at, kind, detail):
    db.execute('INSERT INTO events(at,kind,detail) VALUES(?,?,?)',(at,kind,canonical(detail)))

def register(db,c,at):
    r=c['research']
    if D(r['fx_brl_per_usd']) <= 0 or not r['fx_source'] or not 0 < r['fx_available_at'] <= at:
        raise ValueError('Informe FX positivo, fonte e instante de disponibilidade anterior ao init; use fx para consultar PTAX.')
    if db.execute('SELECT 1 FROM protocols').fetchone(): raise ValueError('Protocolo já registrado; use outro banco para novas regras, preserve o anterior.')
    h=digest(c)
    db.execute('INSERT INTO protocols VALUES(?,?,?,?,?)',(h,at,canonical(c),canonical(calendar(c,at)),int(r['synthetic'])))
    event(db,at,'registered',{'protocol':h,'version':__version__,'metric':'net_portfolio_brl','max_primary_hypotheses':3})
    return h
