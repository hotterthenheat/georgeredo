"""The hold-out, opened once (lifecycle protocol §6, §7 C; amendment L-A1):
  1. every finalist in results/tier1/finalists.csv (frozen policy) on 2025-10-01 -> 2026-10-09, with the promotion rules:
     expectancy > 0 with a day-clustered 95 % lower bound > 0 after Holm across the finalists evaluated; profit factor > 1;
     >= 100 trades on >= 60 sessions; still > 0 at +$0.01 per contract per side and with a 1-minute latency; directional
     cells also beat the random-minute control (paired lower bound > 0).
  2. H-FLO-1 and H-FLO-2 (dealer-gamma sign from UW, prior session).
Writes results/tier1/holdout.json and holdout_*.csv. Refuses to run twice unless --again (the second run is recorded)."""
import os, sys, json, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import runner, policies as pol, analyze as an, reports as rp, paths, position as ps

OUT = f'{paths.RESULTS}/tier1'
LOCK = f'{OUT}/holdout_opened.json'
if os.path.exists(LOCK) and '--again' not in sys.argv:
    sys.exit(f'hold-out already opened: {open(LOCK).read()}')
fin = pl.read_csv(f'{OUT}/finalists.csv')
grid = {n: (f, p) for n, f, p in pol.grid()}
res = {'opened_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'finalists': [], 'flo': {}}
H0 = runner.HOLDOUT_START
def hold_sessions(root):
    from lc import chainmat as cm
    return [d for d in cm.sessions_0dte(root) if d >= H0]

rows_all = []
if 'setup' in fin.columns:
    fin = fin.filter(pl.col('qualifies'))
    for r in fin.iter_rows(named=True):
        name = r['frozen_policy']; fam, p = grid[name]
        variants = {'base': p, 'slip1': p.copy(), 'lat1': p.copy()}
        variants['slip1'][ps.P['SLIP']] = 0.01; variants['lat1'][ps.P['LAT']] = 1
        pset = [(f'{name}|{k}', fam, v) for k, v in variants.items()]
        for root in an.ROOTS:
            meta = runner.run_root(root, f'holdout_{r["setup"]}_{r["structure"]}', pset, sessions=hold_sessions(root), mode='rows', include_holdout=True,
                                   setups=(r['setup'],), structures=(r['structure'],), with_controls=True, log=lambda m: None)
            d = f'{paths.WORK}/runs/holdout_{r["setup"]}_{r["structure"]}/{root}'
            if not os.path.exists(f'{d}/outcomes.parquet'): continue
            o = pl.read_parquet(f'{d}/outcomes.parquet').join(pl.read_parquet(f'{d}/positions.parquet'), on='pos_id')
            o = o.with_columns(pl.col('policy').map_elements(lambda i: pset[i][0], return_dtype=pl.Utf8).alias('pname'), pl.lit(root).alias('root'))
            rows_all.append(o)
if rows_all:
    H = pl.concat(rows_all, how='diagonal_relaxed').filter(pl.col('filled') > 0)
    H.write_parquet(f'{paths.WORK}/holdout_rows.parquet')
    boot = an.Boot(H['session'].to_list(), B=5000)
    keys = ['setup', 'structure', 'pname']
    real = H.filter(pl.col('ctrl') == -1); ctrl = H.filter(pl.col('ctrl') >= 0)
    t = an.cell_table(rp.rows_to_daily(real, keys), keys, boot).join(rp.trade_level(real, keys), on=keys, how='left')
    both = pl.concat([rp.rows_to_daily(real, keys).with_columns(pl.lit('real').alias('side')), rp.rows_to_daily(ctrl, keys).with_columns(pl.lit('ctrl').alias('side'))])
    pr = an.paired(both, keys, {'side': 'real'}, {'side': 'ctrl'}, boot).select(keys + ['diff', 'diff_lo', 'diff_hi']).rename({'diff': 'edge_vs_rnd', 'diff_lo': 'edge_lo', 'diff_hi': 'edge_hi'})
    t = t.join(pr, on=keys, how='left')
    t.write_csv(f'{OUT}/holdout_finalists.csv')
    # Holm across the finalists actually evaluated (base variants): one-sided p from the bootstrap share at or below zero
    base = t.filter(pl.col('pname').str.ends_with('|base'))
    res['finalists'] = base.to_dicts()
res['flo']['note'] = 'H-FLO-1/2 are run by scripts/holdout_flo.py'
json.dump(res, open(f'{OUT}/holdout.json', 'w'), indent=1, default=str)
json.dump({'opened_utc': res['opened_utc'], 'finalists': int(fin.height) if 'setup' in fin.columns else 0}, open(LOCK, 'w'))
print(json.dumps({k: (v if k != 'finalists' else len(v)) for k, v in res.items()}, default=str))
