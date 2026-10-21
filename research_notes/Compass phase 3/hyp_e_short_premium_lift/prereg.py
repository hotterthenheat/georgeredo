"""Write out/preregistered.md from the FIT pass alone (out/fit_lift_cells.csv, out/fit_uncond_byscan.csv, out/fit_uncond_pooled.csv),
with a timestamp, before analyze.py oos is run. The rule is mechanical and fixed here:
  the pick = the HOLD cell (structure x rule x width x signal in {D1-2, D1}) with the highest fit lower 95% bound of the
  paired-bootstrap LIFT in % of max risk, requiring N >= 300 signal structures, >= 150 sessions, the lift positive without
  the best 5 sessions (by their contribution to the lift) and the signal cell's own mean positive without its best 5.
  If no qualifying cell's lift CI (in % of risk AND in $) excludes zero, the test is NOT pre-registrable: say so.
  python3 -I prereg.py
"""
import datetime as dt, os
import polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
C = pl.read_csv(os.path.join(OUT, 'fit_lift_cells.csv'))
U = pl.read_csv(os.path.join(OUT, 'fit_uncond_byscan.csv')); P = pl.read_csv(os.path.join(OUT, 'fit_uncond_pooled.csv'))
H = C.filter(pl.col('management') == 'hold')
Q = H.filter((pl.col('N') >= 300) & (pl.col('sessions') >= 150) & (pl.col('lift_wo_best5') > 0) & (pl.col('wo_best5') > 0)).sort('lift_ci_lo_pct_risk', descending=True)
now = dt.datetime.now(dt.timezone.utc)
L = [f'# Hypothesis E, pre-registration - written {now.isoformat(timespec="seconds")} (UTC) by prereg.py from the fit pass (2022-11-11 -> 2024-12-31) alone; no 2025-2026 trade row has been collected by any script in this folder (analyze.py filters the period at load; verify.py was run with `fit`).', '']
L.append('## Rule (fixed before the OOS read)')
L.append('- Cells: SPY 0DTE call vertical / put vertical / iron condor, short strike d10 / d15 / d20 / d25 / em1, widths 1 and 2, sold at the 12 scan minutes 10:00 .. 15:30, HOLD to settlement; signal = the t2 GBM decile at the scan minute (D1-2 or D1); the lift = the signal\'s mean net against the time-of-day-matched unconditional mean (all sessions at the same scan minute), weighted by the signal\'s scan mix; paired session bootstrap, 2,000 draws, seed 20261016.')
L.append('- The pick = the hold cell with the highest fit LOWER 95% bound of the lift in % of max risk, with N >= 300 structures, >= 150 sessions, lift > 0 without the best 5 sessions, and the cell\'s own mean > 0 without its best 5 sessions.')
L.append('- Pre-registrable only if that cell\'s fit lift CI excludes zero in % of risk and in $. OOS "edge" = the pick\'s OOS lift CI (in % of risk and in $) above zero AND its OOS lift > 0 without the best 5 sessions AND the signal cell\'s own OOS mean CI above zero AND the lift > 0 in each OOS year (2025, 2026). The OOS pass (analyze.py oos) is run once.')
L.append('- The unconditional benchmark is read OOS regardless (the owner asked for it); its strongest fit cells are listed below so that no scan time or rule is chosen on the OOS read.')
L.append('')
L.append('## Qualifying hold cells, ranked (fit; lift in % of max risk with its CI, then $)')
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_float_precision(3)
L.append('```'); L.append(str(Q.select('signal', 'structure', 'rule', 'width', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'tod_mean_pct_risk', 'lift_pct_risk', 'lift_ci_lo_pct_risk', 'lift_ci_hi_pct_risk', 'lift_usd', 'lift_ci_lo', 'lift_ci_hi', 'lift_wo_best5', 'lift_vs_rest_usd', 'lift_vs_rest_ci_lo', 'wo_best5').head(40))); L.append('```')
L.append('')
if Q.height == 0:
    L.append('## Pick: NONE QUALIFIES (no hold cell meets N >= 300, sessions >= 150 and both without-best-5 conditions).')
    pre = False
else:
    top = Q.row(0, named=True)
    pre = (top['lift_ci_lo_pct_risk'] > 0) and (top['lift_ci_lo'] > 0)
    L.append(f"## Pick (the highest lower bound): signal {top['signal']}, {top['structure']} {top['rule']} width {top['width']:.0f}, hold")
    L.append(f"- Fit: N {top['N']}, sessions {top['sessions']}, mean ${top['mean_usd']:.2f} = {top['mean_pct_risk']:.2f}% of max risk; time-matched unconditional {top['tod_mean_pct_risk']:.2f}%; lift {top['lift_pct_risk']:+.2f}% of risk, 95% CI [{top['lift_ci_lo_pct_risk']:+.2f}, {top['lift_ci_hi_pct_risk']:+.2f}]; lift ${top['lift_usd']:+.2f} [{top['lift_ci_lo']:+.2f}, {top['lift_ci_hi']:+.2f}]; lift without the best 5 sessions ${top['lift_wo_best5']:+.2f}; vs the rest (D3-D10) ${top['lift_vs_rest_usd']:+.2f} [{top['lift_vs_rest_ci_lo']:+.2f}, {top['lift_vs_rest_ci_hi']:+.2f}]; the cell\'s own mean without its best 5 ${top['wo_best5']:+.2f}; win {top['win_rate']:.3f}; full-loss share {top['full_loss_share']:.3f}.")
    L.append(f"- Lift by year (fit): " + ', '.join(f"{y} {top[f'lift_{y}']:+.2f} (n {top[f'lift_n_{y}']})" for y in (2022, 2023, 2024) if f'lift_{y}' in top))
    L.append(f"- **{'PRE-REGISTRABLE: the fit lift CI excludes zero in % of risk and in $.' if pre else 'NOT PRE-REGISTRABLE: the fit lift CI does not exclude zero (in % of risk and in $). The OOS lift is read for the record only, labelled not pre-registrable.'}**")
    n_excl = Q.filter((pl.col('lift_ci_lo_pct_risk') > 0) & (pl.col('lift_ci_lo') > 0)).height
    L.append(f"- Qualifying hold cells whose fit lift CI excludes zero (both yardsticks): {n_excl} of {Q.height}; of every hold cell (no size filter): {H.filter((pl.col('lift_ci_lo_pct_risk') > 0) & (pl.col('lift_ci_lo') > 0)).height} of {H.height}; hold cells with a NEGATIVE lift upper bound: {H.filter(pl.col('lift_ci_hi_pct_risk') < 0).height}.")
M = C.filter(pl.col('management') != 'hold').filter((pl.col('N') >= 300) & (pl.col('sessions') >= 150)).sort('lift_ci_lo_pct_risk', descending=True)
if M.height:
    t = M.row(0, named=True)
    L.append(f"- For the record, the best managed cell (secondary, not the pick): {t['management']} {t['signal']} {t['structure']} {t['rule']} w{t['width']:.0f}: lift {t['lift_pct_risk']:+.2f}% [{t['lift_ci_lo_pct_risk']:+.2f}, {t['lift_ci_hi_pct_risk']:+.2f}], N {t['N']}.")
L.append('')
L.append('## The unconditional benchmark in fit (for the OOS read; nothing chosen OOS)')
Ph = P.filter(pl.col('management') == 'hold').sort('ci_lo_pct_risk', descending=True)
L.append('Pooled over the 12 scans, hold, the ten highest lower bounds (% of max risk; CI in $):')
L.append('```'); L.append(str(Ph.select('structure', 'rule', 'width', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'ci_lo', 'ci_hi', 'ci_lo_pct_risk', 'win_rate', 'full_loss_share', 'wo_best5', 'friction_share_of_gross', 'significant').head(10))); L.append('```')
Uh = U.filter(pl.col('management') == 'hold')
L.append(f"Significant unconditional hold cells by scan (CI of the mean $ above zero), of {Uh.filter(pl.col('m_scan') == 30).height} a scan:")
for s in sorted(Uh['m_scan'].unique().to_list()):
    us = Uh.filter(pl.col('m_scan') == s).sort('ci_lo_pct_risk', descending=True); top = us.row(0, named=True)
    L.append(f"- {top['scan']}: {int(us['significant'].sum())} significant; strongest {top['structure']} {top['rule']} w{top['width']:.0f}: {top['mean_pct_risk']:+.2f}% of risk, ${top['mean_usd']:+.2f} [{top['ci_lo']:+.2f}, {top['ci_hi']:+.2f}], N {top['N']}")
L.append('')
L.append('Expectation written now: the unconditional short-premium harvest on SPY 2-wide reads positive in fit at most scans; the signal\'s lift is the question. If the lift is not pre-registrable, the expectation for the OOS lift is "inside the noise".')
txt = '\n'.join(L) + '\n'
with open(os.path.join(OUT, 'preregistered.md'), 'w') as fh: fh.write(txt)
print(txt)
