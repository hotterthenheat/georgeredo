"""Robustness reads on the HOLD cells, fit and OOS: (a) the t2 LOGISTIC model's deciles in place of the GBM's; (b) the lift
with FOMC decision days removed - the decision-day list below is TYPED FROM MEMORY (2022-11 -> 2026-10, the second day of
each meeting), NOT a file on disk and unverified; it is a descriptive stress read only. Reuses analyze.py's loader, Boot
and stats. python3 -I robust.py -> out/robust_lr_<mode>.csv, out/robust_fomc_<mode>.csv, out/robust.txt"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
OUT = A.OUT; L = []
FOMC = ['2022-11-02', '2022-12-14', '2023-02-01', '2023-03-22', '2023-05-03', '2023-06-14', '2023-07-26', '2023-09-20', '2023-11-01', '2023-12-13',
        '2024-01-31', '2024-03-20', '2024-05-01', '2024-06-12', '2024-07-31', '2024-09-18', '2024-11-07', '2024-12-18',
        '2025-01-29', '2025-03-19', '2025-05-07', '2025-06-18', '2025-07-30', '2025-09-17', '2025-10-29', '2025-12-10',
        '2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17', '2026-07-29', '2026-09-16']

def lifts(X, boot, deccol, years, tag):
    rows = []
    for (st, ru, w), g in X.group_by('structure', 'rule', 'width'):
        col = 'pnl_hold'; scored = g.filter(pl.col(deccol).is_not_null())
        Sa, Na = boot.mat(g, col); pr_all = g.with_columns((pl.col(col) / pl.col('max_risk') * 100).alias('pr')); Pa, _ = boot.mat(pr_all, 'pr')
        tod = np.where(Na.sum(0) > 0, Sa.sum(0) / np.maximum(Na.sum(0), 1), np.nan); tod_pr = np.where(Na.sum(0) > 0, Pa.sum(0) / np.maximum(Na.sum(0), 1), np.nan)
        for sig, (dlo, dhi) in A.SIGNALS.items():
            sg = scored.filter((pl.col(deccol) >= dlo) & (pl.col(deccol) <= dhi))
            if sg.height == 0: continue
            Ss, Ns = boot.mat(sg, col); sgp = sg.with_columns((pl.col(col) / pl.col('max_risk') * 100).alias('pr')); Ps, _ = boot.mat(sgp, 'pr')
            ns = Ns.sum(0); w_ = ns / ns.sum(); ms = np.where(ns > 0, Ss.sum(0) / np.maximum(ns, 1), np.nan)
            lo, hi = boot.ci_lift(Ss, Ns, Sa, Na); plo, phi = boot.ci_lift(Ps, Ns, Pa, Na)
            contrib = (Ss - Ns * tod[None, :]).sum(1); order = np.argsort(-contrib); keep = np.ones(boot.D, bool); keep[order[:5]] = False
            rows.append(dict(read=tag, structure=st, rule=ru, width=w, signal=sig, N=sg.height, sessions=sg['session'].n_unique(), mean_pct_risk=float((sg[col] / sg['max_risk']).mean() * 100), tod_mean_pct_risk=float(np.nansum(w_ * tod_pr)),
                             lift_usd=float(np.nansum(w_ * (ms - tod))), lift_ci_lo=lo, lift_ci_hi=hi, lift_pct_risk=float(np.nansum(w_ * (np.where(ns > 0, Ps.sum(0) / np.maximum(ns, 1), np.nan) - tod_pr))), lift_ci_lo_pct_risk=plo, lift_ci_hi_pct_risk=phi,
                             lift_wo_best5=float(contrib[keep].sum() / max(Ns[keep].sum(), 1)), full_loss_sig=float((sg[col] <= -0.95 * sg['max_risk']).mean()), full_loss_all=float((g[col] <= -0.95 * g['max_risk']).mean())))
    return pl.DataFrame(rows).sort('lift_ci_lo_pct_risk', descending=True)

for mode in ('fit', 'oos'):
    X = A.load(mode); years = sorted(X['year'].unique().to_list()); boot = A.Boot(sorted(X['session'].unique().to_list()))
    R = lifts(X, boot, 'dec_lr', years, 'lr'); R.write_csv(os.path.join(OUT, f'robust_lr_{mode}.csv'))
    L.append(f'== {mode}: t2 LOGISTIC deciles, hold cells: {R.height}; lift CI above zero (both yardsticks): {R.filter((pl.col("lift_ci_lo_pct_risk") > 0) & (pl.col("lift_ci_lo") > 0)).height}; below: {R.filter(pl.col("lift_ci_hi_pct_risk") < 0).height}; point > 0: {R.filter(pl.col("lift_usd") > 0).height}; wo5 > 0: {R.filter(pl.col("lift_wo_best5") > 0).height}')
    for st, ru, w, sg in (('put', 'd15', 2.0, 'D1-2'), ('condor', 'd20', 2.0, 'D1'), ('condor', 'd25', 1.0, 'D1'), ('condor', 'em1', 2.0, 'D1-2')):
        r = R.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w) & (pl.col('signal') == sg)).row(0, named=True)
        L.append(f"   LR {sg} {st} {ru} w{w:.0f}: N {r['N']}, cell {r['mean_pct_risk']:.2f}% vs tod {r['tod_mean_pct_risk']:.2f}%, lift {r['lift_pct_risk']:+.2f}% [{r['lift_ci_lo_pct_risk']:+.2f}, {r['lift_ci_hi_pct_risk']:+.2f}], ${r['lift_usd']:+.2f} [{r['lift_ci_lo']:+.2f}, {r['lift_ci_hi']:+.2f}], wo5 ${r['lift_wo_best5']:+.2f}")
    top = R.row(0, named=True); L.append(f"   LR best lower bound: {top['signal']} {top['structure']} {top['rule']} w{top['width']:.0f}: lift {top['lift_pct_risk']:+.2f}% [{top['lift_ci_lo_pct_risk']:+.2f}, {top['lift_ci_hi_pct_risk']:+.2f}], N {top['N']}")
    # FOMC decision days removed (typed from memory; unverified)
    inf = X.filter(pl.col('session').is_in(FOMC)); Xf = X.filter(~pl.col('session').is_in(FOMC)); bootf = A.Boot(sorted(Xf['session'].unique().to_list()))
    L.append(f'== {mode}: FOMC decision days in the period (typed list, unverified): {inf["session"].n_unique()} sessions, {inf.height} rows removed of {X.height}')
    for st, ru, w in (('put', 'd15', 2.0), ('condor', 'd20', 2.0), ('condor', 'd25', 2.0), ('condor', 'em1', 2.0)):
        g = X.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w)); gi = g.filter(pl.col('session').is_in(FOMC)); go = g.filter(~pl.col('session').is_in(FOMC))
        L.append(f"   unconditional {st} {ru} w{w:.0f} hold: on decision days {(gi['pnl_hold'] / gi['max_risk']).mean() * 100:+.2f}% of risk (N {gi.height}, full-loss {(gi['pnl_hold'] <= -0.95 * gi['max_risk']).mean():.2f}) vs the other days {(go['pnl_hold'] / go['max_risk']).mean() * 100:+.2f}% (N {go.height}, full-loss {(go['pnl_hold'] <= -0.95 * go['max_risk']).mean():.3f}); D1-2 rows on decision days: {gi.filter(pl.col('dec') <= 2).height}, their mean {((gi.filter(pl.col('dec') <= 2)['pnl_hold'] / gi.filter(pl.col('dec') <= 2)['max_risk']).mean() * 100 if gi.filter(pl.col('dec') <= 2).height else float('nan')):+.2f}%")
    Rf = lifts(Xf, bootf, 'dec', years, 'no_fomc'); Rf.write_csv(os.path.join(OUT, f'robust_fomc_{mode}.csv'))
    L.append(f'   GBM deciles, decision days removed, hold cells: lift CI above zero: {Rf.filter((pl.col("lift_ci_lo_pct_risk") > 0) & (pl.col("lift_ci_lo") > 0)).height} of {Rf.height}; below: {Rf.filter(pl.col("lift_ci_hi_pct_risk") < 0).height}; wo5 > 0: {Rf.filter(pl.col("lift_wo_best5") > 0).height}')
    for st, ru, w, sg in (('put', 'd15', 2.0, 'D1-2'), ('condor', 'd20', 2.0, 'D1'), ('condor', 'd25', 1.0, 'D1'), ('condor', 'em1', 2.0, 'D1-2'), ('condor', 'd25', 2.0, 'D1-2')):
        r = Rf.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w) & (pl.col('signal') == sg)).row(0, named=True)
        L.append(f"   no-FOMC {sg} {st} {ru} w{w:.0f}: N {r['N']}, cell {r['mean_pct_risk']:.2f}% vs tod {r['tod_mean_pct_risk']:.2f}%, lift {r['lift_pct_risk']:+.2f}% [{r['lift_ci_lo_pct_risk']:+.2f}, {r['lift_ci_hi_pct_risk']:+.2f}], ${r['lift_usd']:+.2f} [{r['lift_ci_lo']:+.2f}, {r['lift_ci_hi']:+.2f}], wo5 ${r['lift_wo_best5']:+.2f}; full-loss sig {r['full_loss_sig']:.3f} vs all {r['full_loss_all']:.3f}")
txt = '\n'.join(L); open(os.path.join(OUT, 'robust.txt'), 'w').write(txt + '\n'); print(txt)
