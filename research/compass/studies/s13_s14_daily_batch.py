"""Studies S13 (pre-earnings run-up) and S14 (cross-sectional momentum / reversal long legs) on the stock EOD lake with
the S07 universe, 2024 -> 2026 (amendment A5). Usage: python3 s13_s14_daily_batch.py"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import daily_screen as ds, calendar as cal
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
t0 = time.time()
df = ds.load_lake(f'{SP}/lake/stock_eod', [2023, 2024, 2025, 2026]); elig = ds.universe(df)
f = ds.features(df).with_columns(pl.col('date').dt.year().alias('year')).join(elig, on=['symbol', 'year'], how='semi').filter(pl.col('i') >= 200)
b = ds.benchmark(f, elig); f = f.join(b, on='date', how='left')
# extra forward returns from the next open: 3 and 5 sessions already (r1, r5, r10, r21)
f = f.with_columns([(pl.col('close') / pl.col('close').shift(252) - 1).over('symbol').alias('ret252'), (pl.col('close') / pl.col('close').shift(21) - 1).over('symbol').alias('ret21'),
                    (pl.col('close').shift(21) / pl.col('close').shift(252) - 1).over('symbol').alias('mom12_1'), (pl.col('close') / pl.col('close').shift(20) - 1).over('symbol').alias('ret20')])
log(f'eligible rows {f.height:,} ({time.time() - t0:.0f}s)')
rows = []
# ---- S13: pre-earnings run-up. Entry at the close N sessions before the event session (i.e. next-open convention shifted):
# we use the row N+1 sessions before the event session so that its "next open" is N sessions before, and exit at the close
# of the session before the event session -> horizon = N sessions. We approximate with the engine's r{h} where h = N:
# r_h = close[t+h]/open[t+1]-1 with t = event_index - h - 1 gives exit at close[event_index - 1] (the pre-event close).
e = pl.read_parquet(os.path.join(ROOT, 'data_lake', 'unusualwhales', 'earnings.parquet')).filter(pl.col('report_type') == 'quarterly')
e = e.with_columns(pl.col('report_date').str.to_date(strict=False).alias('rd')).filter(pl.col('rd').is_not_null() & pl.col('report_time').is_in(['premarket', 'postmarket'])).rename({'ticker': 'symbol'}).unique(['symbol', 'rd'])
dates = f.select(['symbol', 'date', 'next_date' if 'next_date' in f.columns else 'date']).rename({'date': 'rd'}) if False else f.select(['symbol', 'date']).rename({'date': 'rd'})
e = e.join(dates, on=['symbol', 'rd'], how='inner')
# event session index per symbol
idx = f.select(['symbol', 'date', 'i']).rename({'date': 'rd', 'i': 'i_rd'})
e = e.join(idx, on=['symbol', 'rd'], how='inner').with_columns(pl.when(pl.col('report_time') == 'premarket').then(pl.col('i_rd')).otherwise(pl.col('i_rd') + 1).alias('i_event'))
for N in (3, 5, 10):
    hcol = {3: 'r3', 5: 'r5', 10: 'r10'}[N]
    if hcol == 'r3':
        f = f.with_columns((pl.col('close').shift(-3).over('symbol') / pl.col('entry_open') - 1).alias('r3'), ((pl.col('close').shift(-3).over('symbol') / pl.col('entry_open') - 1)).alias('_tmp')).drop('_tmp')
        b3 = f.join(elig, on=['symbol', 'year'], how='semi').group_by('date').agg(pl.col('r3').mean().alias('b3')); f = f.join(b3, on='date', how='left') if 'b3' not in f.columns else f
    ent = e.with_columns((pl.col('i_event') - N - 1).alias('i')).join(f.select(['symbol', 'i', 'date', 'year', hcol, 'b' + hcol[1:]]), on=['symbol', 'i'], how='inner')
    ent = ent.filter(pl.col('date').dt.year() >= 2024)
    d = np.ones(ent.height, int)
    rec = ds.event_stats(ent, d, horizons=(N,), ret_prefix='r', bench_prefix='b')
    rec.update({'trigger': 'S13_pre_earnings_runup', 'filters': f'enter {N} sessions before, exit pre-event close', 'horizon': N})
    rows.append(rec); log(f"S13 N={N}: n {rec['n']} abs {rec[f'abs_{N}d_bp']:+.1f} [{rec[f'abs_{N}d_lo']:+.1f}, {rec[f'abs_{N}d_hi']:+.1f}] adj {rec[f'adj_{N}d_bp']:+.1f} [{rec[f'adj_{N}d_lo']:+.1f}, {rec[f'adj_{N}d_hi']:+.1f}] by year {rec['by_year_adj_10d']}")
# ---- S14: cross-sectional deciles at month ends, held 21 sessions (from the next open)
me = f.filter(pl.col('date').dt.year() >= 2024).with_columns(pl.col('date').dt.month().alias('m')).with_columns((pl.col('m') != pl.col('m').shift(-1).over('symbol')).alias('is_me'))
me = me.filter(pl.col('is_me') & pl.col('r21').is_not_null())
for name, col, top in (('S14_momentum_12_1_top_decile', 'mom12_1', True), ('S14_reversal_1m_bottom_decile', 'ret21', False), ('S14_continuation_20d_top_decile', 'ret20', True), ('S14_momentum_12_1_bottom_decile_as_puts', 'mom12_1', False)):
    g = me.filter(pl.col(col).is_not_null()).with_columns(pl.col(col).rank().over('date').alias('rk'), pl.len().over('date').alias('nd'))
    sel = g.filter((pl.col('rk') > 0.9 * pl.col('nd')) if top else (pl.col('rk') <= 0.1 * pl.col('nd')))
    d = np.ones(sel.height, int) if name != 'S14_momentum_12_1_bottom_decile_as_puts' else -np.ones(sel.height, int)
    rec = ds.event_stats(sel, d, horizons=(5, 10, 21)); rec.update({'trigger': name, 'filters': 'month-end rebalance, S07 universe'})
    rows.append(rec); log(f"{name}: n {rec['n']} abs21 {rec['abs_21d_bp']:+.1f} [{rec['abs_21d_lo']:+.1f}, {rec['abs_21d_hi']:+.1f}] adj21 {rec['adj_21d_bp']:+.1f} [{rec['adj_21d_lo']:+.1f}, {rec['adj_21d_hi']:+.1f}] by year(10d adj) {rec['by_year_adj_10d']}")
OUT = os.path.join(HERE, '..', 'results', 'v1', 's13_s14_daily_batch'); os.makedirs(OUT, exist_ok=True)
json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w'), indent=1, default=str)
L = ['# S13 / S14 — pre-earnings run-up; cross-sectional momentum and reversal long legs (2024 → 2026, S07 universe)', '', '| cell | n | days | abs (bp) [CI] at horizon | adjusted [CI] | hit 10d | by year (adj) |', '|---|---|---|---|---|---|---|']
for r in rows:
    hs = [h for h in (3, 5, 10, 21) if f'abs_{h}d_bp' in r]
    L.append(f"| {r['trigger']} ({r['filters']}) | {r['n']} | {r['days']} | " + '; '.join(f"{h}d {r[f'abs_{h}d_bp']:+.0f} [{r[f'abs_{h}d_lo']:+.0f}, {r[f'abs_{h}d_hi']:+.0f}]" for h in hs) + ' | ' + '; '.join(f"{h}d {r[f'adj_{h}d_bp']:+.0f} [{r[f'adj_{h}d_lo']:+.0f}, {r[f'adj_{h}d_hi']:+.0f}]" for h in hs) + f" | {r.get('hit_10d', float('nan')) * 100:.0f} % | {r['by_year_adj_10d']} |")
open(os.path.join(OUT, 'REPORT.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L)); log(f'S13/S14 DONE ({time.time() - t0:.0f}s)')
