"""Hypothesis C, step 3: the late-day ATM butterflies held to settlement, cut by moc_mag.

Cells: product (and ALL) x entry (15:00, 15:30) x kind (long call fly, long put fly, iron fly) x wing (the product's three
fixed widths and the ATM straddle's width) x moc_mag group (all, Q12 = fit quintiles 1-2, Q345 = fit quintiles 3-5).
A structure needs its three strikes quoted at the entry minute, the short legs' bids > 0 and max risk >= $0.05.
% figures are of max risk (the debit; W - credit for the iron). The signal's contribution is the difference of the
Q12 and Q345 group means on the same cell, with a 95% interval from a session bootstrap drawn in each group (the two
groups are disjoint sessions, so this is a between-session contrast, not a within-session pair).
  PERIOD=fit  prints the fit tables only (the pre-registration pass);  PERIOD=all prints fit and OOS.
Writes out/flies_summary.csv, out/flies_magdiff.csv.
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

PERIOD = os.environ.get('PERIOD', 'fit')

def load():
    F = pl.concat([pl.read_parquet(os.path.join(OUT, f'flies_{p}.parquet')) for p in PRODUCTS], how='vertical_relaxed')
    M = pl.read_parquet(os.path.join(OUT, 'moc_mag.parquet')).with_columns(pl.when(pl.col('t') == 900).then(pl.lit('1500')).otherwise(pl.lit('1530')).alias('tt'))
    M = M.select(pl.col('sym').alias('product'), pl.col('date').alias('session'), pl.col('tt').alias('t'), 'moc_mag', 'quintile')
    F = F.join(M, on=['product', 'session', 't'], how='left').with_columns(pl.when(pl.col('session') < SPLIT).then(pl.lit('fit')).otherwise(pl.lit('oos')).alias('period'))
    F = F.with_columns(pl.when(pl.col('quintile').is_null() | (pl.col('quintile') < 1)).then(pl.lit('none')).when(pl.col('quintile') <= 2).then(pl.lit('Q12')).otherwise(pl.lit('Q345')).alias('mag'))
    return F

def boot_diff(a, da, b, db, n=2000, seed=11):
    """bootstrap of mean(a) - mean(b), sessions resampled within each group."""
    rng = np.random.default_rng(seed)
    def prep(v, d):
        ud, inv = np.unique(d, return_inverse=True)
        return np.bincount(inv, weights=v, minlength=ud.size), np.bincount(inv, minlength=ud.size)
    sa, ca = prep(a, da); sb, cb = prep(b, db); out = np.empty(n)
    for k in range(n):
        ia = rng.integers(0, sa.size, sa.size); ib = rng.integers(0, sb.size, sb.size)
        out[k] = sa[ia].sum() / max(ca[ia].sum(), 1) - sb[ib].sum() / max(cb[ib].sum(), 1)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))

def main():
    F = load()
    periods = ['fit'] if PERIOD == 'fit' else ['fit', 'oos']
    rows = []; drows = []
    wings_all = ['w5', 'w10', 'w25', 'w1', 'w2', 'w0.5', 'wstraddle']
    for prod in PRODUCTS + ['ALL']:
        for t in ['1500', '1530']:
            for kind in ['call', 'put', 'iron']:
                for wing in wings_all:
                    for per in periods:
                        d = F.filter((pl.col('t') == t) & (pl.col('kind') == kind) & (pl.col('wing') == wing) & (pl.col('period') == per))
                        if prod != 'ALL': d = d.filter(pl.col('product') == prod)
                        if d.height == 0: continue
                        for mag in ['all', 'Q12', 'Q345']:
                            g = d if mag == 'all' else d.filter(pl.col('mag') == mag)
                            if g.height == 0: continue
                            s = cell_stats(g['pnl'].to_numpy(), g['pct'].to_numpy(), g['session'].to_numpy())
                            s.update(product=prod, t=t, kind=kind, wing=wing, mag=mag, period=per, mean_risk=float(g['risk'].mean()), mean_W=float(g['W'].mean()),
                                     mean_max_gain=float(g['max_gain'].mean()), share_scored=float((g['mag'] != 'none').mean()))
                            rows.append(s)
                        a = d.filter(pl.col('mag') == 'Q12'); b = d.filter(pl.col('mag') == 'Q345')
                        if a.height and b.height:
                            du = float(a['pnl'].mean() - b['pnl'].mean()); dp = float(a['pct'].mean() - b['pct'].mean())
                            lo, hi = boot_diff(a['pnl'].to_numpy(), a['session'].to_numpy(), b['pnl'].to_numpy(), b['session'].to_numpy())
                            plo, phi = boot_diff(a['pct'].to_numpy(), a['session'].to_numpy(), b['pct'].to_numpy(), b['session'].to_numpy())
                            drows.append(dict(product=prod, t=t, kind=kind, wing=wing, period=per, n_Q12=a.height, n_Q345=b.height, Q12_usd=float(a['pnl'].mean()), Q345_usd=float(b['pnl'].mean()),
                                              diff_usd=du, diff_usd_lo=lo, diff_usd_hi=hi, Q12_pct=float(a['pct'].mean()), Q345_pct=float(b['pct'].mean()), diff_pct=dp, diff_pct_lo=plo, diff_pct_hi=phi,
                                              Q12_win=float((a['pnl'] > 0).mean()), Q345_win=float((b['pnl'] > 0).mean())))
    summ = pl.DataFrame(rows, infer_schema_length=None); diff = pl.DataFrame(drows, infer_schema_length=None)
    tag = '' if PERIOD == 'fit' else '_all'
    summ.write_csv(os.path.join(OUT, f'flies_summary{tag}.csv')); diff.write_csv(os.path.join(OUT, f'flies_magdiff{tag}.csv'))
    for r in summ.iter_rows(named=True):
        print(f"{r['product']:4} {r['t']} {r['kind']:4} {r['wing']:9} {r['mag']:4} {r['period']:3} risk={r['mean_risk']:.2f} W={r['mean_W']:.1f} maxG=${r['mean_max_gain']:.0f} | {fmt(r)}")
    print('---- Q12 minus Q345 (low magnitude minus high), same cell ----')
    for r in diff.iter_rows(named=True):
        print(f"{r['product']:4} {r['t']} {r['kind']:4} {r['wing']:9} {r['period']:3} nQ12={r['n_Q12']:4d} nQ345={r['n_Q345']:4d} Q12=${r['Q12_usd']:+6.1f}({r['Q12_pct']*100:+5.1f}%) Q345=${r['Q345_usd']:+6.1f}({r['Q345_pct']*100:+5.1f}%) "
              f"diff=${r['diff_usd']:+6.1f} [{r['diff_usd_lo']:+6.1f},{r['diff_usd_hi']:+6.1f}] diff%={r['diff_pct']*100:+5.1f} [{r['diff_pct_lo']*100:+5.1f},{r['diff_pct_hi']*100:+5.1f}] win {r['Q12_win']:.2f}/{r['Q345_win']:.2f}")

if __name__ == '__main__':
    main()
