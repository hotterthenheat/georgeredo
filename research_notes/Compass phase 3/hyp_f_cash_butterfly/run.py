"""Hypothesis F, step 2: the cells. time (15:00, 15:30) x name (SPY, QQQ, SPY+QQQ) x form (long call fly, long put
fly, iron fly) x k (0, 0.25, 0.5) x stress ($0.00, $0.01, $0.02 a leg worse), per period.

Per cell: N, mean $ a fly, mean % of max risk, session-bootstrap 95% CI (C's boot_ci: 2,000 draws resampling
sessions, seed 7), win rate, average win / loss, p5 / p1 / worst, worst session, profit factor, max drawdown and the
longest losing streak of the 1-lot chronological sequence, mean without the best five sessions, by year; the gross
(mid-to-mid, no fees) result and friction as a share of it; the break-even fill improvement k* where the mean crosses
zero (the mean is linear in k: mean_k = mean_0 + k * mean(slip) * 100, so k* = -mean_0 / (100 * mean(slip)); a
negative k* says the cell survives fills WORSE than the NBBO, and the equivalent $ a leg is printed beside it); the
quoted sizes on the legs at the entry minute (the side hit: ask size on a long leg, bid size on a short) and the share
of entries where every leg quotes >= 1 contract (and >= the lots it needs, 2 on the short K0 of a call / put fly);
and moc_mag Q12 vs Q345 (C's out/moc_mag.parquet, read only: the audit's t = 930 score at 15:30, C's 14:30 -> 15:00
re-computation at 15:00, fit-quintile cuts) at k = 0.

  PERIOD=fit  reads out/flies_fit.parquet only (the pre-registration pass) -> out/cells_fit.csv etc.
  PERIOD=all  reads both                                                   -> out/cells.csv, out/magdiff.csv, out/fills.csv, out/kstar.csv
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_f import *

PERIOD = os.environ.get('PERIOD', 'fit')
PCT_FLOOR = MIN_DEBIT

def load():
    files = ['fit'] if PERIOD == 'fit' else ['fit', 'oos']
    F = pl.concat([pl.read_parquet(os.path.join(OUT, f'flies_{p}.parquet')) for p in files], how='vertical_relaxed')
    M = pl.read_parquet(os.path.join(C_OUT, 'moc_mag.parquet')).with_columns(pl.when(pl.col('t') == 900).then(pl.lit('1500')).otherwise(pl.lit('1530')).alias('tt'))
    M = M.select(pl.col('sym').alias('product'), pl.col('date').alias('session'), pl.col('tt').alias('t'), 'moc_mag', 'quintile')
    F = F.join(M, on=['product', 'session', 't'], how='left').with_columns(pl.when(pl.col('session') < SPLIT).then(pl.lit('fit')).otherwise(pl.lit('oos')).alias('period'))
    F = F.with_columns(pl.when(pl.col('quintile').is_null() | (pl.col('quintile') < 1)).then(pl.lit('none')).when(pl.col('quintile') <= 2).then(pl.lit('Q12')).otherwise(pl.lit('Q345')).alias('mag'))
    return F

def priced(g, k, stress):
    """pnl $, pct of max risk, risk $ a share, number of rows whose risk hit the $0.05 floor, for one (k, stress)."""
    form = g['form'][0]; pay = g['payoff'].to_numpy(); slip = g['slip'].to_numpy()
    if form == 'iron':
        credit = g['credit_nbbo'].to_numpy() + k * (g['credit_mid'].to_numpy() - g['credit_nbbo'].to_numpy()) - 4 * stress
        pnl = (credit + pay) * 100 - 4 * FEE; risk = W - credit
    else:
        debit = g['debit_nbbo'].to_numpy() - k * slip + 4 * stress
        pnl = (pay - debit) * 100 - 4 * FEE; risk = debit
    floored = int((risk < PCT_FLOOR).sum())
    pct = pnl / (np.maximum(risk, PCT_FLOOR) * 100)
    return pnl, pct, risk, floored

def boot_diff(a, da, b, db, n=2000, seed=11):
    rng = np.random.default_rng(seed)
    def prep(v, d):
        ud, inv = np.unique(d, return_inverse=True)
        return np.bincount(inv, weights=v, minlength=ud.size), np.bincount(inv, minlength=ud.size)
    sa, ca = prep(a, da); sb, cb = prep(b, db); out = np.empty(n)
    for i in range(n):
        ia = rng.integers(0, sa.size, sa.size); ib = rng.integers(0, sb.size, sb.size)
        out[i] = sa[ia].sum() / max(ca[ia].sum(), 1) - sb[ib].sum() / max(cb[ib].sum(), 1)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))

def main():
    F = load()
    periods = ['fit'] if PERIOD == 'fit' else ['fit', 'oos']
    rows = []; drows = []; frows = []; krows = []
    for t in ['1500', '1530']:
        for prod in ['SPY+QQQ', 'SPY', 'QQQ']:
            for form in FORMS:
                for per in periods:
                    g = F.filter((pl.col('t') == t) & (pl.col('form') == form) & (pl.col('period') == per))
                    if prod != 'SPY+QQQ': g = g.filter(pl.col('product') == prod)
                    if g.height == 0: continue
                    days = g['session'].to_numpy(); pay = g['payoff'].to_numpy(); slip = g['slip'].to_numpy()
                    gross = (pay - (g['debit_mid'].to_numpy() if form != 'iron' else -g['credit_mid'].to_numpy())) * 100
                    pnl0 = g['pnl_nbbo'].to_numpy()
                    # fills / sizes
                    frows.append(dict(t=t, product=prod, form=form, period=per, n=g.height,
                                      min_size_med=float(np.median(g['min_size'].to_numpy())), min_size_p10=float(np.percentile(g['min_size'].to_numpy(), 10)),
                                      share_all_legs_ge1=float((g['min_size'] >= 1).mean()), share_all_legs_ge_lots=float((g['min_size_per_lot'] >= 1).mean()),
                                      share_all_legs_ge10=float((g['min_size'] >= 10).mean()),
                                      slip_mean_usd=float(slip.mean() * 100), slip_med_usd=float(np.median(slip) * 100),
                                      nbbo_risk_mean=float(g['risk_nbbo'].mean()), mid_risk_mean=float((g['risk_nbbo'] - g['slip']).mean()) if form != 'iron' else float((W - g['credit_mid']).mean()),
                                      gross_mean_usd=float(gross.mean()), friction_mean_usd=float((gross - pnl0).mean()),
                                      friction_share_of_gross=float((gross - pnl0).mean() / gross.mean()) if gross.mean() != 0 else np.nan,
                                      fees_usd=4 * FEE))
                    # k* (break-even improvement) on the NBBO mean
                    m0 = float(pnl0.mean()); ms = float(slip.mean() * 100)
                    kstar = -m0 / ms if ms != 0 else np.nan
                    krows.append(dict(t=t, product=prod, form=form, period=per, n=g.height, mean_nbbo_usd=m0, mean_slip_usd=ms, kstar=kstar,
                                      breakeven_usd_per_leg=m0 / 400.0, mean_at_k025=m0 + 0.25 * ms, mean_at_k05=m0 + 0.5 * ms, mean_mid=m0 + ms))
                    for k in KS:
                        for stress in STRESSES:
                            pnl, pct, risk, floored = priced(g, k, stress)
                            s = cell_stats(pnl, pct, days)
                            s.update(t=t, product=prod, form=form, period=per, k=k, stress=stress, mean_risk=float(risk.mean()), n_floored=floored,
                                     mean_usd_over_mean_risk=float(pnl.mean() / (risk.mean() * 100)), gross_mean_usd=float(gross.mean()),
                                     friction_share_of_gross=float((gross - pnl).mean() / gross.mean()) if gross.mean() != 0 else np.nan,
                                     share_scored=float((g['mag'] != 'none').mean()))
                            # by name inside a pooled cell
                            if prod == 'SPY+QQQ':
                                for nm in PRODUCTS:
                                    mk = (g['product'] == nm).to_numpy()
                                    s[f'{nm}_mean_pct'] = float(pct[mk].mean()) if mk.any() else np.nan
                                    s[f'{nm}_mean_usd'] = float(pnl[mk].mean()) if mk.any() else np.nan
                            rows.append(s)
                            if k == 0.0 and stress == 0.0:
                                a = (g['mag'] == 'Q12').to_numpy(); b = (g['mag'] == 'Q345').to_numpy()
                                if a.any() and b.any():
                                    lo, hi = boot_diff(pct[a], days[a], pct[b], days[b])
                                    drows.append(dict(t=t, product=prod, form=form, period=per, n_Q12=int(a.sum()), n_Q345=int(b.sum()),
                                                      Q12_pct=float(pct[a].mean()), Q345_pct=float(pct[b].mean()), diff_pct=float(pct[a].mean() - pct[b].mean()), diff_lo=lo, diff_hi=hi,
                                                      Q12_usd=float(pnl[a].mean()), Q345_usd=float(pnl[b].mean()), Q12_win=float((pnl[a] > 0).mean()), Q345_win=float((pnl[b] > 0).mean())))
    tag = '_fit' if PERIOD == 'fit' else ''
    C = pl.DataFrame(rows, infer_schema_length=None); C.write_csv(os.path.join(OUT, f'cells{tag}.csv'))
    pl.DataFrame(drows, infer_schema_length=None).write_csv(os.path.join(OUT, f'magdiff{tag}.csv'))
    pl.DataFrame(frows, infer_schema_length=None).write_csv(os.path.join(OUT, f'fills{tag}.csv'))
    pl.DataFrame(krows, infer_schema_length=None).write_csv(os.path.join(OUT, f'kstar{tag}.csv'))
    for r in C.iter_rows(named=True):
        print(f"{r['t']} {r['product']:7} {r['form']:4} {r['period']:3} k={r['k']:.2f} s={r['stress']:.2f} risk={r['mean_risk']:.2f} floored={r['n_floored']} | {fmt(r)}")
    print('---- fills ----')
    for r in frows: print(r)
    print('---- k* ----')
    for r in krows: print(r)
    print('---- Q12 minus Q345 at k = 0 ----')
    for r in drows:
        print(f"{r['t']} {r['product']:7} {r['form']:4} {r['period']:3} nQ12={r['n_Q12']} nQ345={r['n_Q345']} Q12={r['Q12_pct']*100:+5.1f}% Q345={r['Q345_pct']*100:+5.1f}% diff={r['diff_pct']*100:+5.1f} [{r['diff_lo']*100:+5.1f},{r['diff_hi']*100:+5.1f}] win {r['Q12_win']:.2f}/{r['Q345_win']:.2f}")

if __name__ == '__main__':
    main()
