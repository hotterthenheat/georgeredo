"""The notes' big tables, emitted as markdown from out/*.csv (no hand transcription). python3 -I notes_tables.py -> out/notes_tables.md"""
import os, numpy as np, polars as pl
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
def rd(n): return pl.read_csv(os.path.join(OUT, n), infer_schema_length=None)
def f(x, d=2, s=False):
    if x is None or (isinstance(x, float) and np.isnan(x)): return '—'
    return f'{x:+.{d}f}' if s else f'{x:.{d}f}'
L = []
def table(h, rows): L.append('| ' + ' | '.join(h) + ' |'); L.append('|' + '---|' * len(h)); [L.append('| ' + ' | '.join(map(str, r)) + ' |') for r in rows]; L.append('')
Cf = rd('fit_lift_cells.csv'); Co = rd('oos_lift_cells.csv'); key = ['structure', 'rule', 'width', 'management', 'signal']
J = Cf.join(Co, on=key, how='full', suffix='_o', coalesce=True).filter(pl.col('management') == 'hold').sort('lift_ci_lo_pct_risk', descending=True)
L.append('### Every hold cell: the lift, fit (ranked by its lower bound) and OOS'); L.append('')
rows = []
for r in J.iter_rows(named=True):
    ok = (r['lift_ci_lo_pct_risk_o'] or 0) > 0 and (r['lift_ci_lo_o'] or 0) > 0
    rows.append([r['signal'], r['structure'], r['rule'], f"{r['width']:.0f}", r['N'], r['sessions'], f(r['mean_pct_risk']), f(r['tod_mean_pct_risk']), f"{f(r['lift_pct_risk'], 2, True)} [{f(r['lift_ci_lo_pct_risk'], 2, True)}, {f(r['lift_ci_hi_pct_risk'], 2, True)}]", f"{f(r['lift_usd'], 2, True)} [{f(r['lift_ci_lo'], 2, True)}, {f(r['lift_ci_hi'], 2, True)}]", f(r['lift_wo_best5'], 2, True),
                 r['N_o'], r['sessions_o'], f(r['mean_pct_risk_o']), f(r['tod_mean_pct_risk_o']), f"{f(r['lift_pct_risk_o'], 2, True)} [{f(r['lift_ci_lo_pct_risk_o'], 2, True)}, {f(r['lift_ci_hi_pct_risk_o'], 2, True)}]{'*' if ok else ''}", f"{f(r['lift_usd_o'], 2, True)} [{f(r['lift_ci_lo_o'], 2, True)}, {f(r['lift_ci_hi_o'], 2, True)}]", f(r['lift_wo_best5_o'], 2, True), f"{f(r['lift_2025'], 1, True)} / {f(r['lift_2026'], 1, True)}"])
table(['signal', 'structure', 'rule', 'w', 'fit N', 'sess.', 'cell %risk', 'tod %risk', 'lift %risk [95% CI]', 'lift $ [CI]', 'wo5 $', 'OOS N', 'sess.', 'cell %risk', 'tod %risk', 'lift %risk [CI] (* clear)', 'lift $ [CI]', 'wo5 $', '2025 / 2026 $'], rows)
# managed, top 5 each by fit, with OOS
for mg in ('stop2x', 'tp50'):
    S = Cf.join(Co, on=key, how='full', suffix='_o', coalesce=True).filter(pl.col('management') == mg).sort('lift_ci_lo_pct_risk', descending=True).head(6)
    L.append(f'### {mg}: the six best fit lower bounds, with the cell\'s own mean (the managed cells are negative unconditionally)'); L.append('')
    rows = [[r['signal'], r['structure'], r['rule'], f"{r['width']:.0f}", r['N'], f(r['mean_pct_risk']), f(r['tod_mean_pct_risk']), f"{f(r['lift_pct_risk'], 2, True)} [{f(r['lift_ci_lo_pct_risk'], 2, True)}, {f(r['lift_ci_hi_pct_risk'], 2, True)}]", f(r['lift_wo_best5'], 2, True), r['N_o'], f(r['mean_pct_risk_o']), f(r['tod_mean_pct_risk_o']), f"{f(r['lift_pct_risk_o'], 2, True)} [{f(r['lift_ci_lo_pct_risk_o'], 2, True)}, {f(r['lift_ci_hi_pct_risk_o'], 2, True)}]", f(r['lift_wo_best5_o'], 2, True)] for r in S.iter_rows(named=True)]
    table(['signal', 'structure', 'rule', 'w', 'fit N', 'cell %risk', 'tod %risk', 'lift %risk [CI]', 'wo5 $', 'OOS N', 'cell %risk', 'tod %risk', 'lift %risk [CI]', 'wo5 $'], rows)
# unconditional by scan: every 2-wide cell + condor d25 w1, compact, fit/OOS
Uf = rd('fit_uncond_byscan.csv').filter(pl.col('management') == 'hold'); Uo = rd('oos_uncond_byscan.csv').filter(pl.col('management') == 'hold')
scans = sorted(Uf['m_scan'].unique().to_list()); names = [Uf.filter(pl.col('m_scan') == s)['scan'][0] for s in scans]
L.append('### Unconditional benchmark by scan minute, hold, every cell: mean % of max risk, fit / OOS (* = the session-bootstrap 95% CI of the mean $ above zero)'); L.append('')
rows = []
for (st, ru, w), g in Uf.group_by('structure', 'rule', 'width', maintain_order=True):
    r = [f'{st} {ru} w{w:.0f}']
    for s in scans:
        a = g.filter(pl.col('m_scan') == s).row(0, named=True); bq = Uo.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w) & (pl.col('m_scan') == s)); b = bq.row(0, named=True) if bq.height else None
        r.append(f"{f(a['mean_pct_risk'], 1, True)}{'*' if a['significant'] else ''} / {f(b['mean_pct_risk'], 1, True) + ('*' if b['significant'] else '') if b else '—'}")
    rows.append(r)
table(['cell'] + names, sorted(rows))
L.append('### Unconditional by scan, hold: N (fit / OOS) and the count of significant cells of 30'); L.append('')
rows = []
for s, nm in zip(scans, names):
    a = Uf.filter(pl.col('m_scan') == s); b = Uo.filter(pl.col('m_scan') == s)
    rows.append([nm, f"{int(a['N'].sum())} / {int(b['N'].sum())}", int(a['significant'].sum()), int(b['significant'].sum()), f"{int((a['mean_usd'] > 0).sum())} / {int((b['mean_usd'] > 0).sum())}"])
table(['scan', 'structures fit / OOS', 'fit significant', 'OOS significant', 'cells with mean > 0, fit / OOS'], rows)
open(os.path.join(OUT, 'notes_tables.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
