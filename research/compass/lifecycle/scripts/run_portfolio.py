"""Portfolio simulations (deliverable 7) on the Tier I events: concurrent signals across roots in time order, one open
position per root, capital and risk caps, displayed-size limits, and the M10 (re-entry) and M11 (reverse) rules.
Each configuration is run on development + validation and, separately, on the hold-out (the hold-out was opened for the
finalists on 2026-10-15; these portfolios use only finalist cells or their random-minute equivalents and fixed rules)."""
import os, sys, json, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import sequencer as sq, policies as pol, paths, runner

OUT = f'{paths.RESULTS}/portfolio'; os.makedirs(OUT, exist_ok=True)
G = {n: p for n, _, p in pol.grid()}
def events(roots, setups):
    ev = pl.concat([pl.read_parquet(f'{paths.WORK}/events/{r}.parquet') for r in roots], how='diagonal_relaxed')
    return ev.filter(pl.col('setup').is_in(setups))
POOL = ('QS', 'TP', 'BO', 'BN', 'BOF', 'BNF', 'LS', 'MSS', 'FVG')
CONFIGS = {
    # the best hold-out finalist (QS -> cash-secured put, stop at 2x credit), cash-secured on SPY/QQQ/IWM (SPXW's collateral
    # is several times the account), one contract a trade, collateral capped at the account
    'P1_QS_CSP_s20': dict(roots=('SPY', 'QQQ', 'IWM'), setups=('QS',), sf=lambda s, d: 'CSP' if d > 0 else None, pol='M13_tpnone_s20',
                          sizing='fixed_units', fixed_units=1, max_total_risk=1.0, max_bucket_risk=1.0),
    # credit put spreads on QS, $1,000 of maximum loss a trade, 10 % of the account at risk at most
    'P2_QS_CPS_expiry': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=('QS',), sf=lambda s, d: 'CPS' if d > 0 else None, pol='M0_expiry',
                             sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10),
    'P2r_skip_after_loss': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=('QS',), sf=lambda s, d: 'CPS' if d > 0 else None, pol='M0_expiry',
                                sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reentry='skip'),
    # long Steady calls and puts on QS, 30-minute exit, $1,000 of premium a trade
    'P3_QS_Steady_t30': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=('QS',), sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30',
                             sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10),
    'P3r_reverse': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=('QS',), sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30',
                        sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reverse='reverse'),
    'P3c_close_on_opposite': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=('QS',), sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30',
                                  sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reverse='close'),
    # M10 / M11 need a pool in which opposite signals and closed losses occur inside a session: QS alone signals both ways on
    # one root in 37 of 1,639 root-sessions, and a spread held to expiry never closes before the session ends, so P2r, P3r and
    # P3c could not differ from their bases. The engine's and the pattern setups pooled (no trigger-only duplicates):
    'P4_pool_Steady_t30': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10),
    'P4r_reverse': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reverse='reverse'),
    'P4c_close_on_opposite': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reverse='close'),
    'P4s_skip_after_loss': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reentry='skip'),
    'P4k_cool15_after_loss': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_risk', risk_per_trade=1000.0, max_total_risk=0.10, max_bucket_risk=0.10, reentry='cool15'),
    # P4 at $1,000 a trade is ruined within the sample (equity $410), after which the caps decide every trade; the rule
    # comparisons are made at one contract a trade on an account no cap can bind ($100 M), so each variant differs from
    # P5 only by its rule (compare dollars, not CAGR)
    'P5_pool_Steady_t30_1lot': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_units', fixed_units=1, max_total_risk=1.0, max_bucket_risk=1.0, equity0=1e8),
    'P5r_reverse': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_units', fixed_units=1, max_total_risk=1.0, max_bucket_risk=1.0, equity0=1e8, reverse='reverse'),
    'P5c_close_on_opposite': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_units', fixed_units=1, max_total_risk=1.0, max_bucket_risk=1.0, equity0=1e8, reverse='close'),
    'P5s_skip_after_loss': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_units', fixed_units=1, max_total_risk=1.0, max_bucket_risk=1.0, equity0=1e8, reentry='skip'),
    'P5k_cool15_after_loss': dict(roots=('SPY', 'QQQ', 'IWM', 'SPXW'), setups=POOL, sf=lambda s, d: 'LC-S' if d > 0 else 'LP-S', pol='M1_t30', sizing='fixed_units', fixed_units=1, max_total_risk=1.0, max_bucket_risk=1.0, equity0=1e8, reentry='cool15'),
}
which = sys.argv[1].split(',') if len(sys.argv) > 1 else list(CONFIGS)
period = sys.argv[2] if len(sys.argv) > 2 else 'devval'
summ = {}
for name in which:
    c = CONFIGS[name]; t0 = time.time()
    ev = events(c['roots'], c['setups'])
    ev = ev.filter(pl.col('session') < runner.HOLDOUT_START) if period == 'devval' else ev.filter(pl.col('session') >= runner.HOLDOUT_START)
    kw = {k: v for k, v in c.items() if k not in ('roots', 'setups', 'sf', 'pol')}
    tr, days = sq.simulate(ev, c['sf'], G[c['pol']], **kw)
    tr.write_parquet(f'{OUT}/{name}_{period}_trades.parquet'); days.write_csv(f'{OUT}/{name}_{period}_days.csv')
    f = tr.filter(pl.col('status') == 'filled') if tr.height else tr
    eq = days['equity'].to_numpy(); pnl = days['pnl'].to_numpy()
    yrs = max(len(eq) / 252, 1e-9)
    summ[name] = {'period': period, 'sessions': days.height, 'trades': f.height, 'skipped_risk_cap': int(tr.filter(pl.col('status') == 'risk_cap').height) if tr.height else 0,
                  'skipped_size': int(tr.filter(pl.col('status') == 'size').height) if tr.height else 0,
                  'total_pnl': float(pnl.sum()), 'end_equity': float(eq[-1]) if len(eq) else None, 'cagr': float((eq[-1] / kw.get('equity0', 100000)) ** (1 / yrs) - 1) if len(eq) else None,
                  'max_drawdown': float(days['drawdown'].min()) if days.height else None,
                  'daily_sharpe': float(np.mean(pnl) / np.std(pnl) * np.sqrt(252)) if np.std(pnl) > 0 else None,
                  'win_rate': float((f['pnl'] > 0).mean()) if f.height else None, 'avg_trade': float(f['pnl'].mean()) if f.height else None,
                  'worst_trade': float(f['pnl'].min()) if f.height else None, 'worst_day': float(pnl.min()) if len(pnl) else None,
                  'avg_units': float(f['units'].mean()) if f.height else None, 'seconds': round(time.time() - t0)}
    print(name, period, json.dumps(summ[name]), flush=True)
    prev = json.load(open(f'{OUT}/summary.json')) if os.path.exists(f'{OUT}/summary.json') else {}
    prev[f'{name}|{period}'] = summ[name]
    json.dump(prev, open(f'{OUT}/summary.json', 'w'), indent=1)
