"""H-FLO-1 and H-FLO-2 (protocol amendment L-A1), run once on the hold-out (2025-10-15 .. 2026-10-09, where UW's dealer
greek-exposure exists):
  H-FLO-1  Steady longs (LC-S, LP-S), every directional setup pooled, M1_t30: expectancy on negative-gamma days minus
           positive-gamma days.
  H-FLO-2  the 10:00 long straddle (ALL10V, STR, M0_cutoff): the same difference.
The gamma sign for session D is the sign of UW's call_gamma + put_gamma on the root (SPX's for SPXW) dated the session
before D. Day-clustered 95 % intervals; Holm across the two."""
import os, sys, json, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import runner, policies as pol, analyze as an, paths, chainmat as cm

OUT = f'{paths.RESULTS}/tier1'
LOCK = f'{OUT}/holdout_flo_opened.json'
if os.path.exists(LOCK) and '--again' not in sys.argv: sys.exit(f'already run: {open(LOCK).read()}')
DIRS = ('QS', 'TP', 'BO', 'BOF', 'BN', 'BNF', 'LS', 'MSS', 'FVG', 'TPp', 'BOp', 'BOr', 'BNp', 'VWR')
s1 = pol.stage1(); names = [n for n, _, _ in s1]
rows = []
for root in an.ROOTS:
    ss = [d for d in cm.sessions_0dte(root) if d >= dt.date(2025, 10, 15)]
    runner.run_root(root, 'flo1', s1, sessions=ss, mode='rows', include_holdout=True, setups=DIRS, structures=('LC-S', 'LP-S'), with_controls=False, log=lambda m: None)
    runner.run_root(root, 'flo2', s1, sessions=ss, mode='rows', include_holdout=True, setups=('ALL10V',), structures=('STR',), with_controls=False,
                    events_file=f'{paths.WORK}/events_vol/{root}.parquet', log=lambda m: None)
    for st, pname, test in (('flo1', 'M1_t30', 'H-FLO-1'), ('flo2', 'M0_cutoff', 'H-FLO-2')):
        d = f'{paths.WORK}/runs/{st}/{root}'
        o = pl.read_parquet(f'{d}/outcomes.parquet').join(pl.read_parquet(f'{d}/positions.parquet'), on='pos_id')
        o = o.filter((pl.col('policy') == names.index(pname)) & (pl.col('filled') > 0)).with_columns(pl.lit(root).alias('root'), pl.lit(test).alias('test'))
        rows.append(o.select(['root', 'test', 'session', 'pnl', 'cost0']))
H = pl.concat(rows)
ge = pl.concat([pl.read_parquet(f) for f in sorted(glob.glob(os.path.normpath(os.path.join(paths.HERE, '..', '..', '..', 'data_lake', 'unusualwhales', 'greek-exposure.part0*.parquet'))))])
ge = ge.select([pl.col('ticker'), pl.col('date').str.to_date().alias('d'), (pl.col('call_gamma').cast(pl.Float64) + pl.col('put_gamma').cast(pl.Float64)).alias('g')])
res = {}
for test in ('H-FLO-1', 'H-FLO-2'):
    x = H.filter(pl.col('test') == test)
    parts = []
    for root in an.ROOTS:
        tk = 'SPX' if root == 'SPXW' else root
        g = ge.filter(pl.col('ticker') == tk).sort('d')
        sess = sorted(x.filter(pl.col('root') == root)['session'].unique().to_list())
        gd = dict(zip(g['d'].to_list(), g['g'].to_list()))
        prior = {}
        for s in sess:
            prev = [d for d in gd if d < s]
            if prev: prior[s] = gd[max(prev)]
        xr = x.filter(pl.col('root') == root).with_columns(pl.col('session').replace_strict(prior, default=None, return_dtype=pl.Float64).alias('g'))
        parts.append(xr)
    x = pl.concat(parts).filter(pl.col('g').is_not_null()).with_columns(pl.when(pl.col('g') < 0).then(pl.lit('neg')).otherwise(pl.lit('pos')).alias('regime'))
    d = x.group_by(['regime', 'session']).agg(pl.len().alias('n'), pl.col('pnl').sum())
    boot = an.Boot(d['session'].to_list(), B=5000)
    pr = an.paired(d.with_columns(pl.lit('all').alias('k')), ['k'], {'regime': 'neg'}, {'regime': 'pos'}, boot)
    r = pr.row(0, named=True)
    res[test] = {'exp_neg': r['exp_a'], 'exp_pos': r['exp_b'], 'diff': r['diff'], 'diff_lo': r['diff_lo'], 'diff_hi': r['diff_hi'],
                 'n_neg': r['n_a'], 'n_pos': r['n_b'], 'days_neg': int(x.filter(pl.col('regime') == 'neg')['session'].n_unique()),
                 'days_pos': int(x.filter(pl.col('regime') == 'pos')['session'].n_unique())}
json.dump(res, open(f'{OUT}/holdout_flo.json', 'w'), indent=1, default=str)
json.dump({'opened_utc': dt.datetime.now(dt.timezone.utc).isoformat()}, open(LOCK, 'w'))
print(json.dumps(res, indent=1, default=str))
