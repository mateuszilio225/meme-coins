from __future__ import annotations
import contextlib, copy, io, json, os, sqlite3, tempfile, time, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch
from meme_research.config import load, D, canonical, digest, validate, calendar
from meme_research.store import migrate, connect, register, collector_lock, backup
from meme_research.demo import sample, START, create
from meme_research.service import cycle, ingest, protocol
from meme_research.finance import costs, break_even, ensure_wallets, submit, process, reserved, tick
from meme_research.data import HTTP, Sources, DataUnavailable, normalize
from meme_research.reports import audit, guard, outcome, profitability, forensics, economic_table
from meme_research.radar import features, scores
from meme_research.evaluate import block_interval, evaluate
from meme_research.cli import main, active

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'with spaces'/'research.sqlite'
        self.c=copy.deepcopy(load()[0]); self.c['research'].update(fx_brl_per_usd='5',fx_source='fixture',fx_available_at=START-1,synthetic=True)
        migrate(self.path); self.db=connect(self.path); self.addCleanup(self.db.close)
        with self.db: register(self.db,self.c,START)
        self.schedule=calendar(self.c,START)
    def ingest(self,o):
        ids=ingest(self.db,[o],self.schedule,o['received'])
        return self.db.execute('SELECT * FROM observations WHERE id=?',(ids[0],)).fetchone() if ids else None
    def history(self,mint='M',pair='P',price=1,liq=100000):
        for i in range(3):
            o=self.ingest(sample(mint,pair,START+2+i*60,price*(1+i*.03),liq))
        return o
    def order(self,obs,strategy='A'):
        ensure_wallets(self.db,self.c,'development',obs['received'])
        submit(self.db,self.c,{strategy:obs},'development',obs['received'])
        return f'development:{strategy}:base'
    def fill(self):
        o=self.history(); wid=self.order(o)
        nxt=self.ingest(sample('M','P',START+182,1.07))
        process(self.db,self.c,nxt)
        return wid,self.db.execute('SELECT * FROM positions WHERE wallet=?',(wid,)).fetchone()

class Configuration(Base):
    def test_version_consistent(self):
        import tomllib, meme_research
        p=Path(__file__).resolve().parents[1]/'pyproject.toml'
        self.assertEqual(tomllib.loads(p.read_text())['project']['version'],meme_research.__version__)
    def test_capital_total_fixed(self):
        self.c['research']['capital_brl']='401'
        self.assertRaises(ValueError,validate,self.c)
    def test_nan_rejected(self):
        self.c['scenarios']['base']['fee_bps']='NaN'
        self.assertRaises(ValueError,validate,self.c)
    def test_negative_fee_rejected(self):
        self.c['scenarios']['base']['network_usd']='-1'
        self.assertRaises(ValueError,validate,self.c)
    def test_bad_fraction(self):
        self.c['policy']['position_fraction']='.9'
        self.assertRaises(ValueError,validate,self.c)
    def test_fx_future_rejected(self):
        c=copy.deepcopy(self.c); c['research']['fx_available_at']=START+1
        new=Path(self.tmp.name)/'other.sqlite'; migrate(new)
        with contextlib.closing(connect(new)) as db: self.assertRaises(ValueError,register,db,c,START)
    def test_no_configuration_drift(self):
        self.c['policy']['score_threshold']=20
        self.assertRaises(ValueError,protocol,self.db,self.c)
    def test_calendar_embargo(self):
        from meme_research.config import period_at
        self.assertEqual(period_at(self.schedule,START+7.5*86400),'embargo')
    def test_active_ptax_binding(self):
        c=copy.deepcopy(self.c)
        c['research'].update(fx_brl_per_usd='0',fx_source='',fx_available_at=0)
        self.assertEqual(active(self.db,c),self.c)

class Persistence(Base):
    def test_idempotent_migration(self):
        self.db.commit(); migrate(self.path)
        self.assertEqual(self.db.execute('SELECT count(*) FROM protocols').fetchone()[0],1)
    def test_immutable_protocol(self):
        self.assertRaises(sqlite3.IntegrityError,self.db.execute,'DELETE FROM protocols')
    def test_immutable_evidence(self):
        self.history()
        self.assertRaises(sqlite3.IntegrityError,self.db.execute,"UPDATE observations SET price='100'")
    def test_duplicate_observation(self):
        o=sample('M','P',START+2)
        self.assertIsNotNone(self.ingest(o)); self.assertIsNone(self.ingest(o))
    def test_foreign_key(self):
        self.assertRaises(sqlite3.IntegrityError,self.db.execute,"INSERT INTO ledger(wallet,at,delta,kind) VALUES('absent',0,'1','x')")
    def test_readonly_no_write(self):
        self.db.commit()
        with contextlib.closing(connect(self.path,True)) as db:
            self.assertRaises(sqlite3.OperationalError,db.execute,'DELETE FROM tokens')
    def test_missing_read_does_not_create(self):
        p=Path(self.tmp.name)/'absent.sqlite'
        self.assertRaises(FileNotFoundError,connect,p,True); self.assertFalse(p.exists())
    def test_lock_exclusive(self):
        with collector_lock(self.path):
            with self.assertRaises(RuntimeError):
                with collector_lock(self.path): pass
        with collector_lock(self.path): pass
    def test_backup_and_no_overwrite(self):
        self.history(); self.db.commit(); dest=Path(self.tmp.name)/'backup.sqlite'
        backup(self.path,dest)
        self.assertRaises(FileExistsError,backup,self.path,dest)
        with contextlib.closing(connect(dest,True)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0],3)
    def test_reject_unknown_database(self):
        path=Path(self.tmp.name)/'foreign.sqlite'
        with sqlite3.connect(path) as db: db.execute('CREATE TABLE old(data TEXT)')
        self.assertRaises(ValueError,migrate,path)
    def test_transaction_rollback(self):
        self.db.commit()
        try:
            with self.db:
                self.history(); raise RuntimeError('fixture')
        except RuntimeError: pass
        self.assertEqual(self.db.execute('SELECT count(*) FROM observations').fetchone()[0],0)
    def test_restart_preserves_pending(self):
        o=self.history(); self.order(o); self.db.commit()
        with contextlib.closing(connect(self.path)) as db:
            self.assertGreater(db.execute("SELECT count(*) FROM orders WHERE state='pending'").fetchone()[0],0)
    def test_failed_migration_rolls_back(self):
        import meme_research.store as store
        path=Path(self.tmp.name)/'broken.sqlite'
        with patch.object(store,'SCHEMA','CREATE TABLE partial(x); INVALID SQL;'):
            self.assertRaises(sqlite3.Error,migrate,path)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='partial'").fetchone())

class Temporal(Base):
    def test_future_observation(self):
        o=sample('M','P',START+5)
        self.assertRaises(ValueError,ingest,self.db,[o],self.schedule,START+4)
    def test_future_provider(self):
        o=sample('M','P',START+5); o['provider_ts']=START+6
        self.assertRaises(ValueError,self.ingest,o)
    def test_pair_isolation(self):
        self.history(); o=self.ingest(sample('M','OTHER',START+182,100))
        self.assertFalse(features(self.db,o,self.c['policy'])['ready'])
    def test_source_isolation(self):
        self.history(); o=self.ingest(sample('M','P',START+182,100,source='other'))
        self.assertFalse(features(self.db,o,self.c['policy'])['ready'])
    def test_late_fact_does_not_approve(self):
        o=self.history()
        before=features(self.db,o,self.c['policy'])
        self.db.execute('INSERT INTO facts(mint,received,state,raw) VALUES(?,?,?,?)',('M',o['received']+1,'known_risk','{}'))
        self.assertEqual(features(self.db,o,self.c['policy']),before)
    def test_gap_rejected(self):
        self.history(); o=self.ingest(sample('M','P',START+500))
        self.assertIn('gap',features(self.db,o,self.c['policy'])['reasons'])
    def test_missing_liquidity_not_zero(self):
        o=self.ingest(sample('M','P',START+2,liquidity=None))
        self.assertIsNone(o['liquidity']); self.assertIn('missing',o['quality'])
    def test_zero_liquidity_distinct(self):
        o=self.ingest(sample('M','P',START+2,liquidity=0))
        self.assertEqual(D(o['liquidity']),0); self.assertIn('zero',o['quality'])
    def test_missing_price_no_zero_fill(self):
        o=self.ingest(sample('M','P',START+2,price=None))
        self.assertIsNone(o['price']); self.assertFalse(features(self.db,o,self.c['policy'])['ready'])
    def test_provider_timestamp_unknown(self):
        o=self.history(); self.c['policy']['require_provider_timestamp']=True
        self.assertIn('provider_timestamp_unknown',features(self.db,o,self.c['policy'])['reasons'])
    def test_rolling_windows_not_new_flow(self):
        o=self.history()
        self.assertIsNone(features(self.db,o,self.c['policy'])['volume_nonoverlap'])
    def test_future_history_does_not_change_features(self):
        o=self.history(); before=features(self.db,o,self.c['policy'])
        self.ingest(sample('M','P',START+182,100))
        self.assertEqual(before,features(self.db,o,self.c['policy']))
    def test_token_split_frozen(self):
        self.history(); o=self.ingest(sample('M','P',self.schedule['validation'][0]+1))
        self.assertEqual(o['period'],'development')
    def test_holdout_hidden(self):
        self.assertRaises(ValueError,guard,self.db,'test',START+1)
    def test_holdout_unlock_at_end(self):
        guard(self.db,'test',self.schedule['test'][1])
    def test_horizon_crossing_no_fabrication(self):
        o=self.ingest(sample('M','P',self.schedule['development'][1]-10))
        self.assertEqual(outcome(self.db,o,300)['state'],'crosses_period')
    def test_partial_horizon_incomplete(self):
        o=self.history()
        self.assertEqual(outcome(self.db,o,300)['state'],'incomplete')
    def test_scores_not_probabilities(self):
        o=self.history(); sc,r=scores(features(self.db,o,self.c['policy']))
        self.assertTrue(all(0<=v<=100 for v in sc.values()))

class Finance(Base):
    def test_pending_reserves_cash(self):
        o=self.history(); wid=self.order(o)
        self.assertEqual(reserved(self.db,wid),D('8'))
        self.assertEqual(D(self.db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0]),D('80'))
    def test_duplicate_mint_exposure(self):
        o=self.history(); wid=self.order(o); submit(self.db,self.c,{'A':o},'development',o['received'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM orders WHERE wallet=?',(wid,)).fetchone()[0],1)
    def test_shared_capital_limit(self):
        ensure_wallets(self.db,self.c,'development',START)
        for i in range(7):
            o=self.history(f'M{i}',f'P{i}')
            submit(self.db,self.c,{'A':o},'development',o['received'])
        self.assertEqual(reserved(self.db,'development:A:base'),D('24'))
    def test_no_signal_snapshot_fill(self):
        o=self.history(); wid=self.order(o); process(self.db,self.c,o)
        self.assertIsNone(self.db.execute('SELECT * FROM positions WHERE wallet=?',(wid,)).fetchone())
    def test_request_before_eligibility_no_fill(self):
        o=self.history(); wid=self.order(o)
        n=sample('M','P',o['received']+2,1.07); n['requested']=o['received']-1
        process(self.db,self.c,self.ingest(n))
        self.assertIsNone(self.db.execute('SELECT * FROM positions WHERE wallet=?',(wid,)).fetchone())
    def test_buy_total_budget_no_double_cost(self):
        wid,p=self.fill()
        self.assertEqual(D(self.db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0]),D('72'))
        f=self.db.execute("SELECT * FROM fills WHERE wallet=? AND side='buy'",(wid,)).fetchone()
        self.assertAlmostEqual(D(f['quantity'])*D(f['price'])+D(f['fee'])+D(f['network']),D(8),places=23)
        self.assertTrue(audit(self.db)['ok'])
    def test_stop_fill_after_jump_not_threshold(self):
        wid,p=self.fill()
        trigger=self.ingest(sample('M','P',START+242,.3)); process(self.db,self.c,trigger)
        self.assertEqual(self.db.execute('SELECT state FROM positions WHERE id=?',(p['id'],)).fetchone()[0],'exit_pending')
        nxt=self.ingest(sample('M','P',START+302,.2)); process(self.db,self.c,nxt)
        sell=self.db.execute("SELECT * FROM fills WHERE wallet=? AND side='sell'",(wid,)).fetchone()
        self.assertLess(D(sell['price']),D('.2')); self.assertTrue(audit(self.db)['ok'])
    def test_inconclusive_capital_not_freed(self):
        wid,p=self.fill()
        trigger=self.ingest(sample('M','P',START+242,.1,0)); process(self.db,self.c,trigger)
        tick(self.db,self.c,START+1000,self.schedule)
        pos=self.db.execute('SELECT * FROM positions WHERE id=?',(p['id'],)).fetchone()
        self.assertEqual(pos['state'],'inconclusive'); self.assertGreater(D(pos['quantity']),0)
        self.assertEqual(D(self.db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0]),D(72))
    def test_entry_expiry_releases_only_reservation(self):
        o=self.history(); wid=self.order(o)
        tick(self.db,self.c,START+1000,self.schedule)
        self.assertEqual(reserved(self.db,wid),0)
    def test_main_abstains_without_quote(self):
        o=self.history(); wid=self.order(o,'main')
        self.assertEqual(self.db.execute('SELECT count(*) FROM orders WHERE wallet=?',(wid,)).fetchone()[0],0)
    def test_break_even_round_trip_math(self):
        for name,s in self.c['scenarios'].items():
            for b in (D(2),D(4),D(8),D(16)):
                r=break_even(b,100000,s); cc=costs(s,b,100000)
                buy=(1+cc['half_spread']+cc['slippage']+cc['impact'])
                q=(b-cc['network'])/(1+cc['fee'])/buy
                sellmid=1+r; exitc=costs(s,q*sellmid,100000)
                proceeds=q*sellmid*(1-exitc['half_spread']-exitc['slippage']-exitc['impact'])*(1-exitc['fee'])-exitc['network']
                self.assertAlmostEqual(proceeds,b,places=22)
    def test_tiny_budget_impossible(self):
        self.assertIsNone(break_even('.001',10000,self.c['scenarios']['base']))
    def test_cost_size_sensitivity(self):
        s=self.c['scenarios']['base']
        self.assertGreater(break_even(1,100000,s),break_even(8,100000,s))
    def test_adverse_more_expensive(self):
        self.assertGreater(break_even(8,100000,self.c['scenarios']['adverse']),break_even(8,100000,self.c['scenarios']['base']))
    def test_query_failure_has_no_network_fee(self):
        wid,p=self.fill(); cash=self.db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0]
        from meme_research.store import event
        event(self.db,START+200,'quote_unavailable',{'reason':'transport'})
        self.assertEqual(self.db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0],cash)
    def test_deterministic_onchain_failure_charges_once(self):
        self.c['scenarios']['base']['failure_every_n']=1
        o=self.history(); wid=self.order(o)
        nxt=self.ingest(sample('M','P',START+182,1.07)); process(self.db,self.c,nxt)
        self.assertEqual(D(self.db.execute('SELECT cash FROM wallets WHERE id=?',(wid,)).fetchone()[0]),D('79.98'))
        self.assertIsNone(self.db.execute('SELECT * FROM positions WHERE wallet=?',(wid,)).fetchone())
    def test_partial_and_trailing_reconcile(self):
        wid,p=self.fill()
        for i,price in enumerate((3,3.1,2,1.9)):
            o=self.ingest(sample('M','P',START+242+i*60,price)); process(self.db,self.c,o)
        pos=self.db.execute('SELECT * FROM positions WHERE id=?',(p['id'],)).fetchone()
        self.assertEqual(pos['state'],'closed'); self.assertTrue(audit(self.db)['ok'])
        f=forensics(self.db,'development')['cases']
        case=next(x for x in f if x['position']['id']==p['id'])
        self.assertAlmostEqual(D(case['evidence']['gross_reference_closed_usd'])-D(case['evidence']['execution_costs_usd']),D(pos['pnl']),places=22)
    def test_no_fill_for_other_pair(self):
        o=self.history(); wid=self.order(o)
        nxt=self.ingest(sample('M','OTHER',START+182,100)); process(self.db,self.c,nxt)
        self.assertIsNone(self.db.execute('SELECT * FROM positions WHERE wallet=?',(wid,)).fetchone())
    def test_infrastructure_once_global(self):
        self.c['research']['monthly_infrastructure_brl']='30'
        # New frozen experiment for this cost assumption, rather than rewriting protocol.
        from meme_research.reports import wallet_report
        ensure_wallets(self.db,self.c,'development',START)
        w=self.db.execute("SELECT * FROM wallets WHERE id='development:A:base'").fetchone()
        r=wallet_report(self.db,w,self.c,self.schedule,START+86400)
        self.assertEqual(D(r['infrastructure_brl_once']),D(1))
        self.assertEqual(D(r['net_brl_if_fully_closed']),D(-1))
    def test_no_expectancy_with_unresolved(self):
        wid,p=self.fill()
        report=profitability(self.db,'development',START+183)
        self.assertIsNone(next(w for w in report['wallets'] if w['wallet']==wid)['expectancy_usd'])

class HTTPTests(Base):
    def test_429_persisted_deferred_without_retry(self):
        class Opener:
            def __init__(self): self.calls=0
            def open(self,*a,**k):
                self.calls+=1
                raise urllib.error.HTTPError('https://example.test',429,'quota',{'Retry-After':'120'},None)
        opener=Opener(); h=HTTP(self.db,clock=lambda:START,opener=opener)
        self.assertRaises(DataUnavailable,h.get,'dex_pairs','https://example.test/a')
        self.assertRaises(DataUnavailable,h.get,'dex_pairs','https://example.test/b')
        self.assertEqual(opener.calls,1)
        self.assertGreaterEqual(self.db.execute("SELECT next_at FROM api_state WHERE provider='dex_pairs'").fetchone()[0],START+120)
    def test_cache_original_timestamp(self):
        data={'a':1}; key=digest(['dex_pairs','https://example.test',None])
        self.db.execute('INSERT INTO cache VALUES(?,?,?,?,?)',(key,START-20,START+10,canonical(data),'ok'))
        h=HTTP(self.db,clock=lambda:START)
        value,at,origin=h.get('dex_pairs','https://example.test')
        self.assertEqual(at,START-20); self.assertEqual(origin,'cache')
    def test_missing_quote_key_no_call(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertRaises(DataUnavailable,Sources(self.db).quote,'a','b',100)
        self.assertEqual(self.db.execute('SELECT count(*) FROM api_calls').fetchone()[0],0)
    def test_incompatible_quote_rejected(self):
        class Fake:
            clock=lambda s:START
            def get(self,*a,**kw): return {'inputMint':'WRONG','outputMint':'b','inAmount':'100','outAmount':'20','routePlan':[{}]},START,'network'
        with patch.dict(os.environ,{'JUPITER_API_KEY':'SECRET_FIXTURE'}):
            self.assertRaises(DataUnavailable,Sources(self.db,Fake()).quote,'a','b',100)
        quote=self.db.execute('SELECT * FROM quotes').fetchone()
        self.assertEqual(quote['state'],'incompatible'); self.assertNotIn('SECRET_FIXTURE',quote['raw'])
    def test_unexpected_transaction_not_retained(self):
        class Fake:
            clock=lambda s:START
            def get(self,*a,**kw): return {'transaction':'SENSITIVE','inputMint':'a'},START,'network'
        with patch.dict(os.environ,{'JUPITER_API_KEY':'x'}):
            self.assertRaises(DataUnavailable,Sources(self.db,Fake()).quote,'a','b',100)
        self.assertNotIn('SENSITIVE',self.db.execute('SELECT raw FROM quotes').fetchone()[0])
    def test_invalid_mint_no_query(self):
        self.assertRaises(DataUnavailable,Sources(self.db).pairs,'../invalid')
    def test_nan_raw_invalid(self):
        raw={'chainId':'solana','pairAddress':'p','baseToken':{'address':'m'},'priceUsd':'NaN'}
        self.assertIsNone(normalize(raw,1,2)['price'])

class Scientific(Base):
    def test_too_few_days_no_bootstrap_claim(self):
        self.assertEqual(block_interval([1]*5)['state'],'insufficient_days')
    def test_tail_resolution_rejected(self):
        self.assertEqual(block_interval([1]*20,100)['state'],'insufficient_tail_resolution')
    def test_block_reproducible(self):
        a=block_interval([1,-1]*10,2000,alpha=.1,seed=2)
        self.assertEqual(a,block_interval([1,-1]*10,2000,alpha=.1,seed=2))
    def test_early_evaluation_rejected(self):
        self.assertRaises(ValueError,evaluate,self.db,'development',START+100)
    def test_synthetic_no_economic_claim(self):
        self.history(); ensure_wallets(self.db,self.c,'development',START)
        report=evaluate(self.db,'development',self.schedule['development'][1]+1)
        self.assertTrue(all(x['conclusion']=='insufficient_evidence' for x in report['comparisons']))
    def test_demo_audited_and_no_overwrite(self):
        dest=Path(self.tmp.name)/'demo.sqlite'; result=create(dest,self.c)
        self.assertTrue(result['audit']['ok']); self.assertTrue(result['demo_only'])
        self.assertRaises(FileExistsError,create,dest,self.c)
        with contextlib.closing(connect(dest,True)) as db:
            self.assertGreater(db.execute("SELECT count(*) FROM positions WHERE state='inconclusive'").fetchone()[0],0)
            self.assertGreater(db.execute("SELECT count(*) FROM positions WHERE state='closed' AND CAST(pnl AS REAL)<0").fetchone()[0],0)
            self.assertGreater(db.execute("SELECT count(*) FROM positions WHERE state='closed' AND CAST(pnl AS REAL)>0").fetchone()[0],0)
    def test_cli_version(self):
        with self.assertRaises(SystemExit) as e,contextlib.redirect_stdout(io.StringIO()): main(['--version'])
        self.assertEqual(e.exception.code,0)
    def test_report_does_not_mutate(self):
        self.history(); self.db.commit()
        before=self.path.read_bytes()
        with contextlib.closing(connect(self.path,True)) as db:
            audit(db); profitability(db,'development',START+200)
        self.assertEqual(self.path.read_bytes(),before)

if __name__=='__main__': unittest.main()

class AdditionalSafety(Base):
    def test_ablation_preserves_source_and_varies_one_field(self):
        from meme_research.ablation import run
        dest=Path(self.tmp.name)/'demo.sqlite'; create(dest,self.c)
        before=dest.read_bytes()
        result=run(dest,Path(self.tmp.name)/'ablations')
        self.assertEqual(dest.read_bytes(),before)
        self.assertEqual(len(result['variants']),3)
        self.assertTrue(all(v['audit']['ok'] for v in result['variants']))
        self.assertEqual(result['variants'][1]['changed_policy_fields'],{'entry_mode':'confirmation'})
    def test_generated_demo_config_reportable(self):
        result=create(Path(self.tmp.name)/'demo.sqlite',self.c)
        c,path=load(result['config_path'])
        self.assertTrue(c['research']['synthetic'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--config',str(path),'audit']),0)
    def test_oversized_numeric_rejected(self):
        from meme_research.data import number
        self.assertIsNone(number('1e999999'))
    def test_bad_nested_payload_rejected(self):
        self.assertIsNone(normalize({'chainId':'solana','baseToken':'bad'},1,2))
    def test_bool_config_validated(self):
        self.c['research']['quotes_enabled']='false'
        self.assertRaises(ValueError,validate,self.c)
    def test_same_size_quote_mismatch_abstains(self):
        from meme_research.finance import quote_evidence
        self.assertFalse(quote_evidence(self.db,'M',D(8),START))
    def test_score_high_can_lose_in_demo(self):
        result=create(Path(self.tmp.name)/'demo.sqlite',self.c)
        with contextlib.closing(connect(result['database_path'],True)) as db:
            n=db.execute("SELECT count(*) FROM positions p JOIN decisions d ON d.obs=p.signal WHERE d.score>=60 AND p.state='closed' AND CAST(p.pnl AS REAL)<0").fetchone()[0]
            self.assertGreater(n,0)

class BoundaryTests(Base):
    def test_horizon_complete_no_future_max(self):
        a=self.ingest(sample('M','P',START+2,1))
        for sec in (60,120,180,240,300): self.ingest(sample('M','P',START+2+sec,1.1))
        self.ingest(sample('M','P',START+362,10))
        o=outcome(self.db,a,300)
        self.assertEqual(o['state'],'complete'); self.assertFalse(o['hit']['1'])
    def test_risk_score_components_reconstruct_total(self):
        o=self.history(); f=features(self.db,o,self.c['policy']); sc,_=scores(f)
        for model in ('A','B','C'): self.assertEqual(sum(f['score_components'][model].values()),sc[model])
    def test_strict_quote_size_and_reverse(self):
        from meme_research.finance import quote_evidence
        usdc='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        fields='mint,requested,received,input_mint,output_mint,amount,out_amount,state,raw'
        self.db.execute(f'INSERT INTO quotes({fields}) VALUES(?,?,?,?,?,?,?,?,?)',('M',START-2,START-1,usdc,'M','8000000','12345','ok','{}'))
        self.db.execute(f'INSERT INTO quotes({fields}) VALUES(?,?,?,?,?,?,?,?,?)',('M',START-1,START,'M',usdc,'12345','7900000','ok','{}'))
        self.assertTrue(quote_evidence(self.db,'M',D(8),START))
        self.assertFalse(quote_evidence(self.db,'M',D(7),START))
        self.assertFalse(quote_evidence(self.db,'M',D(8),START+60))
    def test_c_unsupported_program_rejected(self):
        o=self.history(); f=features(self.db,o,self.c['policy']); f['security']='unsupported_program'
        self.assertIn('known_token_risk_or_unsupported_program',scores(f)[1])
    def test_score_report_on_demo(self):
        from meme_research.reports import score_diagnostics
        out=create(Path(self.tmp.name)/'score-demo.sqlite',self.c)
        with contextlib.closing(connect(out['database_path'],True)) as db:
            result=score_diagnostics(db,'development')
            self.assertEqual(len(result['models']),3)
    def test_stale_batch_not_filled(self):
        o=self.history(); wid=self.order(o); self.db.commit()
        n=sample('M','P',START+182,1.08)
        with self.db: cycle(self.db,self.c,[n],START+400)
        self.assertEqual(self.db.execute('SELECT count(*) FROM positions WHERE wallet=?',(wid,)).fetchone()[0],0)
    def test_same_future_price_other_pool_no_outcome(self):
        a=self.ingest(sample('M','P',START+2,1))
        for sec in (60,120,180,240,300): self.ingest(sample('M','OTHER',START+2+sec,10))
        self.assertFalse(outcome(self.db,a,300)['hit']['1'])
    def test_collector_cycle_restart_no_alert_duplication(self):
        items=[sample('X','Y',START+2+i*60,1+i*.03) for i in range(3)]
        for o in items:
            with self.db: cycle(self.db,self.c,[o],o['received'])
        n=self.db.execute('SELECT count(*) FROM alerts').fetchone()[0]
        with self.db: cycle(self.db,self.c,[items[-1]],items[-1]['received'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM alerts').fetchone()[0],n)

class MalformedAPITests(Base):
    def test_rpc_list_rejected(self):
        class Fake:
            def get(self,*a,**k): return [],START,'network'
        self.assertRaises(DataUnavailable,Sources(self.db,Fake()).facts,['M'])
    def test_quote_list_rejected(self):
        class Fake:
            clock=lambda s:START
            def get(self,*a,**k): return [],START,'network'
        with patch.dict(os.environ,{'JUPITER_API_KEY':'x'}):
            self.assertRaises(DataUnavailable,Sources(self.db,Fake()).quote,'a','b',1)
