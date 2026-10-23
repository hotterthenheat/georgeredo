"""Step 6c, Part 2: what was visible before the move, as lift against trades bought at the same time at the same
moneyness (PREREG section 4).

For every buy-minute feature (data.FEATURES), its buckets (categories, or quintiles cut on Pick and used unchanged on
Check; a blank is its own bucket) and every class-window pair (R40, R100, R500 in H60 and H1530):
  lift = runners in the bucket / sum over the bucket's trades of the base rate of their cell (buy time x moneyness bin),
the base rate taken in the same period. Interval: moving-block bootstrap over calendar dates (blocks of 5, 2,000 draws,
audit_lib.block_draws), 2.5-97.5 percentiles of the ratio.
A bucket raised (lowered) the odds in Pick: >= 300 Pick trades on >= 30 dates, lift >= 1.25 (<= 0.80) and the interval
above (below) 1. It held in Check: Check lift on the same side of 1, Check interval excluding 1.

Writes step6/out/lift.csv (every bucket and pair), lift_held.csv (the Pick passes with their Check read), buckets.json
(the cut points), and $WORK/membership.parquet (each trade's bucket per feature, for trade.py).
  python3 -I step6/lift.py
"""
import json, os, sys
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'research_notes', 'Compass phase 3', 'backtest_audit'))
from step6.data import load, OUT, WORK, FEATURES, PAIRS, PRIMARY   # noqa: E402
import audit_lib                                                      # noqa: E402

MIN_N, MIN_DATES, UP, DOWN, BLOCK, B = 300, 30, 1.25, 0.80, 5, 2000

def bucketize(T):
    """feature -> (labels per trade, cut description). Cut points from Pick alone."""
    pick = T.filter(pl.col('period') == 'pick')
    lab, cuts = {}, {}
    for f in FEATURES:
        col = T[f]
        if col.dtype == pl.Utf8 or col.drop_nulls().n_unique() <= 6:
            v = col.cast(pl.Utf8).fill_null('not available')
            if col.dtype in (pl.Float64, pl.Float32):
                v = pl.Series(f, [('not available' if (x is None or x != x) else (str(int(x)) if float(x).is_integer() else str(x))) for x in col.to_list()])
            lab[f] = v.to_numpy(); cuts[f] = 'categories'
            continue
        x = col.cast(pl.Float64).to_numpy(); px_ = pick[f].cast(pl.Float64).to_numpy()
        px_ = px_[np.isfinite(px_)]
        qs = np.unique(np.quantile(px_, [0.2, 0.4, 0.6, 0.8]))
        edges = np.concatenate([[-np.inf], qs, [np.inf]])
        k = np.searchsorted(qs, x, side='right')
        names = [f'q{i + 1} [{edges[i]:.4g}, {edges[i + 1]:.4g})' for i in range(len(edges) - 1)]
        out = np.array([names[i] if np.isfinite(v) else 'not available' for i, v in zip(np.minimum(k, len(names) - 1), x)], dtype=object)
        lab[f] = out; cuts[f] = [float(c) for c in qs]
    return lab, cuts

def base_expected(T, cls):
    """each trade's base rate: the share of `cls` in its cell, in its own period"""
    b = T.group_by('period', 'cell').agg(pl.col(cls).cast(pl.Float64).mean().alias('_b'))
    return T.select('period', 'cell').join(b, on=['period', 'cell'], how='left')['_b'].to_numpy()

def lift_table(T, lab):
    rows = []
    for per in ('pick', 'check'):
        P = T.filter(pl.col('period') == per)
        sel = (T['period'] == per).to_numpy()
        dates = np.array(sorted(set(P['date'].to_list())))
        di = np.searchsorted(dates, P['date'].to_numpy())
        nd = dates.size
        W = audit_lib.weights_from(audit_lib.block_draws(nd, BLOCK, B), nd)          # B x dates
        ys = {f'{c}_{w}': P[f'{c}_{w}'].cast(pl.Float64).to_numpy() for c, w in PAIRS}
        es = {k: base_expected(P, k) for k in ys}
        for f in FEATURES:
            L = lab[f][sel]
            for bkt in sorted(set(L)):
                m = L == bkt
                n = int(m.sum()); nds = int(np.unique(di[m]).size)
                r = {'period': per, 'feature': f, 'bucket': bkt, 'trades': n, 'dates': nds}
                for k in ys:
                    O = np.bincount(di[m], weights=ys[k][m], minlength=nd); E = np.bincount(di[m], weights=es[k][m], minlength=nd)
                    lift = O.sum() / E.sum() if E.sum() > 0 else np.nan
                    with np.errstate(divide='ignore', invalid='ignore'):
                        bl = (W @ O) / (W @ E)
                    lo, hi = audit_lib.pct_ci(bl)
                    r.update({f'{k}_obs': int(O.sum()), f'{k}_exp': float(E.sum()), f'{k}_rate': float(O.sum() / n) if n else np.nan,
                              f'{k}_lift': float(lift), f'{k}_lo': lo, f'{k}_hi': hi})
                rows.append(r)
    return pl.DataFrame(rows)

def main():
    T = load()
    lab, cuts = bucketize(T)
    json.dump(cuts, open(os.path.join(OUT, 'buckets.json'), 'w'), indent=1)
    M = T.select('product', 'session', 'strike', 'right', 'entry_minute').with_columns([pl.Series(f, lab[f].astype(str)) for f in FEATURES])
    M.write_parquet(os.path.join(WORK, 'membership.parquet'))
    L = lift_table(T, lab)
    L.write_csv(os.path.join(OUT, 'lift.csv'))
    # the Pick passes, read on Check
    pk = L.filter(pl.col('period') == 'pick'); ck = L.filter(pl.col('period') == 'check')
    held = []
    ntests = 0
    for c, w in PAIRS:
        k = f'{c}_{w}'
        for r in pk.iter_rows(named=True):
            if r['bucket'] == 'not available': pass
            ntests += 1
            up = r[f'{k}_lift'] >= UP and r[f'{k}_lo'] > 1
            dn = r[f'{k}_lift'] <= DOWN and r[f'{k}_hi'] < 1
            if not (r['trades'] >= MIN_N and r['dates'] >= MIN_DATES and (up or dn)): continue
            x = ck.filter((pl.col('feature') == r['feature']) & (pl.col('bucket') == r['bucket']))
            xr = x.row(0, named=True) if x.height else None
            hold = False
            if xr is not None and xr['trades'] > 0:
                hold = (xr[f'{k}_lo'] > 1) if up else (xr[f'{k}_hi'] < 1)
            held.append({'pair': k, 'primary': (c, w) in PRIMARY, 'feature': r['feature'], 'bucket': r['bucket'], 'direction': 'raised' if up else 'lowered',
                         'pick_trades': r['trades'], 'pick_rate': r[f'{k}_rate'], 'pick_lift': r[f'{k}_lift'], 'pick_lo': r[f'{k}_lo'], 'pick_hi': r[f'{k}_hi'],
                         'check_trades': xr['trades'] if xr else 0, 'check_rate': xr[f'{k}_rate'] if xr else None,
                         'check_lift': xr[f'{k}_lift'] if xr else None, 'check_lo': xr[f'{k}_lo'] if xr else None, 'check_hi': xr[f'{k}_hi'] if xr else None,
                         'held': hold})
    H = pl.DataFrame(held).sort('pair', 'held', 'pick_lift', descending=[False, True, True])
    H.write_csv(os.path.join(OUT, 'lift_held.csv'))
    # disclosed beside the pre-registered test, not part of it: buckets whose interval excludes 1 on the same side in BOTH
    # periods, whatever the size of the lift (the pre-registered bar is 1.25 / 0.80)
    J = pk.join(ck, on=['feature', 'bucket'], suffix='_c')
    cons = []
    for c, w in PAIRS:
        k = f'{c}_{w}'
        X = J.filter((pl.col('trades') >= MIN_N) & (pl.col('dates') >= MIN_DATES) & (pl.col('bucket') != 'not available')
                     & (((pl.col(f'{k}_lo') > 1) & (pl.col(f'{k}_lo_c') > 1)) | ((pl.col(f'{k}_hi') < 1) & (pl.col(f'{k}_hi_c') < 1))))
        for r in X.iter_rows(named=True):
            cons.append({'pair': k, 'feature': r['feature'], 'bucket': r['bucket'], 'direction': 'raised' if r[f'{k}_lo'] > 1 else 'lowered',
                         'pick_trades': r['trades'], 'pick_rate': r[f'{k}_rate'], 'pick_lift': r[f'{k}_lift'], 'pick_lo': r[f'{k}_lo'], 'pick_hi': r[f'{k}_hi'],
                         'check_trades': r['trades_c'], 'check_rate': r[f'{k}_rate_c'], 'check_lift': r[f'{k}_lift_c'], 'check_lo': r[f'{k}_lo_c'], 'check_hi': r[f'{k}_hi_c']})
    pl.DataFrame(cons).sort('pair', 'direction', 'pick_lift', descending=[False, False, True]).write_csv(os.path.join(OUT, 'lift_consistent.csv'))
    print('disclosed (not pre-registered): buckets clear of 1 on the same side in both periods:', len(cons))
    print('tests (feature buckets x 6 pairs on Pick):', ntests, '| Pick passes:', H.height, '| held in Check:', int(H['held'].sum()))
    print(H.group_by('pair', 'direction').agg(pl.len().alias('pick_pass'), pl.col('held').sum().alias('held')).sort('pair', 'direction'))

if __name__ == '__main__':
    main()
