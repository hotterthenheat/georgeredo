"""One-sided bootstrap p-values, Holm, and per-root descriptive splits for H-FLO-1/2, read from the runs holdout_flo.py
wrote (no simulation is repeated; the same Boot seed and B as the opened test)."""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import policies as pol, analyze as an, paths
names = [n for n, _, _ in pol.stage1()]
rows = []
for root in an.ROOTS:
    for st, pname, test in (('flo1', 'M1_t30', 'H-FLO-1'), ('flo2', 'M0_cutoff', 'H-FLO-2')):
        d = f'{paths.WORK}/runs/{st}/{root}'
        o = pl.read_parquet(f'{d}/outcomes.parquet').join(pl.read_parquet(f'{d}/positions.parquet'), on='pos_id')
        o = o.filter((pl.col('policy') == names.index(pname)) & (pl.col('filled') > 0))
        rows.append(o.select([pl.lit(root).alias('root'), pl.lit(test).alias('test'), 'session', 'pnl', 'cost0', 'structure']))
H = pl.concat(rows)
ge = pl.concat([pl.read_parquet(f) for f in sorted(glob.glob(os.path.normpath(os.path.join(paths.HERE, '..', '..', '..', 'data_lake', 'unusualwhales', 'greek-exposure.part0*.parquet'))))])
ge = ge.select([pl.col('ticker'), pl.col('date').str.to_date().alias('d'), (pl.col('call_gamma').cast(pl.Float64) + pl.col('put_gamma').cast(pl.Float64)).alias('g')])
out = {}
for test in ('H-FLO-1', 'H-FLO-2'):
    parts = []
    for root in an.ROOTS:
        g = ge.filter(pl.col('ticker') == ('SPX' if root == 'SPXW' else root)).sort('d')
        gd = dict(zip(g['d'].to_list(), g['g'].to_list()))
        x = H.filter((pl.col('test') == test) & (pl.col('root') == root))
        prior = {s: gd[max(k for k in gd if k < s)] for s in x['session'].unique().to_list() if any(k < s for k in gd)}
        parts.append(x.with_columns(pl.col('session').replace_strict(prior, default=None, return_dtype=pl.Float64).alias('g')))
    x = pl.concat(parts).filter(pl.col('g').is_not_null()).with_columns(pl.when(pl.col('g') < 0).then(pl.lit('neg')).otherwise(pl.lit('pos')).alias('regime'))
    d = x.group_by(['regime', 'session']).agg(pl.len().alias('n'), pl.col('pnl').sum())
    boot = an.Boot(d['session'].to_list(), B=5000)
    def arm(r):
        g = d.filter(pl.col('regime') == r)
        N = np.zeros(len(boot.days)); P = np.zeros(len(boot.days))
        for s, n, p in zip(g['session'].to_list(), g['n'].to_list(), g['pnl'].to_list()): N[boot.ix[s]] += n; P[boot.ix[s]] += p
        return (boot.W @ P) / (boot.W @ N)
    diff = arm('neg') - arm('pos')
    by_root = x.group_by(['root', 'regime']).agg(pl.len().alias('n'), pl.col('pnl').mean().alias('exp'), pl.col('session').n_unique().alias('days')).sort(['root', 'regime'])
    by_struct = x.group_by(['structure', 'regime']).agg(pl.len().alias('n'), pl.col('pnl').mean().alias('exp')).sort(['structure', 'regime'])
    out[test] = {'p_one_sided': float(np.mean(diff <= 0)), 'by_root': by_root.to_dicts(), 'by_structure': by_struct.to_dicts()}
ps = sorted((out[t]['p_one_sided'], t) for t in out)
for i, (p, t) in enumerate(ps):
    out[t]['holm_threshold'] = 0.05 / (len(ps) - i)
    out[t]['holm_pass'] = bool(all(pp <= 0.05 / (len(ps) - j) for j, (pp, _) in enumerate(ps[:i + 1])))
json.dump(out, open(f'{paths.RESULTS}/tier1/holdout_flo_stats.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))

# post hoc (written after the pooled result was seen): the roots differ in dollar scale and in how often each regime
# occurs (SPXW mostly positive-gamma, IWM almost always negative), so the pooled difference mixes regime and root.
# Within-root differences in return on premium (pnl / premium), each with its own day bootstrap, and their equal-weight mean.
post = {}
for test in ('H-FLO-1', 'H-FLO-2'):
    parts = []
    for root in an.ROOTS:
        g = ge.filter(pl.col('ticker') == ('SPX' if root == 'SPXW' else root)).sort('d')
        gd = dict(zip(g['d'].to_list(), g['g'].to_list()))
        x = H.filter((pl.col('test') == test) & (pl.col('root') == root))
        prior = {s: gd[max(k for k in gd if k < s)] for s in x['session'].unique().to_list() if any(k < s for k in gd)}
        parts.append(x.with_columns(pl.col('session').replace_strict(prior, default=None, return_dtype=pl.Float64).alias('g')))
    x = pl.concat(parts).filter(pl.col('g').is_not_null()).with_columns(pl.when(pl.col('g') < 0).then(pl.lit('neg')).otherwise(pl.lit('pos')).alias('regime'),
                                                                        pl.col('cost0').abs().alias('prem'))
    boot = an.Boot(x['session'].to_list(), B=5000, seed=11)
    diffs = []; res = {}
    for root in an.ROOTS:
        xr = x.filter(pl.col('root') == root)
        def arm(r):
            gg = xr.filter(pl.col('regime') == r).group_by('session').agg(pl.col('pnl').sum(), pl.col('prem').sum())
            P = np.zeros(len(boot.days)); C = np.zeros(len(boot.days))
            for s, p, c in zip(gg['session'].to_list(), gg['pnl'].to_list(), gg['prem'].to_list()): P[boot.ix[s]] += p; C[boot.ix[s]] += c
            return P.sum() / C.sum(), (boot.W @ P) / (boot.W @ C)
        (ea, ba), (eb, bb) = arm('neg'), arm('pos')
        dd = ba - bb; diffs.append(dd)
        res[root] = {'rop_neg': ea, 'rop_pos': eb, 'diff': ea - eb, 'lo': float(np.nanquantile(dd, 0.025)), 'hi': float(np.nanquantile(dd, 0.975)),
                     'days_pos': int(xr.filter(pl.col('regime') == 'pos')['session'].n_unique())}
    m = np.nanmean(np.vstack(diffs), axis=0)
    res['equal_weight_mean'] = {'diff': float(np.mean([res[r]['diff'] for r in an.ROOTS])), 'lo': float(np.nanquantile(m, 0.025)), 'hi': float(np.nanquantile(m, 0.975)),
                                'p_one_sided': float(np.mean(m <= 0))}
    post[test] = res
json.dump(post, open(f'{paths.RESULTS}/tier1/holdout_flo_within_root_posthoc.json', 'w'), indent=1, default=str)
print(json.dumps(post, indent=1, default=str))
