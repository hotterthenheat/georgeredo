"""Line the fit and OOS reads up side by side from out/*.csv into out/tables.md (markdown tables for the notes). python3 -I report.py"""
import os, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
def rd(n): return pl.read_csv(os.path.join(OUT, n), infer_schema_length=None)
def f(x, d=2, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)): return '—'
    return f'{x:+.{d}f}' if sign else f'{x:.{d}f}'
L = []
def table(hdr, rows):
    L.append('| ' + ' | '.join(hdr) + ' |'); L.append('|' + '---|' * len(hdr))
    for r in rows: L.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    L.append('')
# ---- 1. model
A = rd('model_auc.csv'); Ao = rd('model_auc_oos.csv'); H = rd('hypd_spy_auc.csv'); D = rd('decile_rates.csv'); Do = rd('decile_rates_oos.csv')
L.append('## Model AUC (t2), this refit (SPY alone, 971 sessions) against Hypothesis D (four products pooled, every 2nd session; read on its SPY rows)'); L.append('')
rows = []
for key, nm in (('full_gbm', 'full GBM'), ('full_lr', 'full logistic'), ('base_gbm', 'baseline (m, straddle)')):
    a = A.filter(pl.col('model') == key).row(0, named=True); o = Ao.filter(pl.col('model') == key).row(0, named=True)
    h = H.filter((pl.col('model') == f'hypd_pooled_{key}_on_SPY') & pl.col('n_fit').is_not_null()).row(0, named=True); ho = Ao.filter(pl.col('model') == f'hypd_pooled_{key}_on_SPY').row(0, named=True)
    rows.append([nm, f(a['auc_fit_insample'], 3), f(a['auc_fit_oof'], 3), f(a['auc_cut'], 3), f(o['auc'], 3), f(h['auc_fit_oof'], 3), f(h['auc_cut'], 3), f(ho['auc'], 3)])
table(['model', 'fit in-sample', 'fit OOF', 'cut 2024H2', 'OOS 2025-26', 'Hyp D on SPY: fit OOF', 'cut', 'OOS'], rows)
L.append('## t2 realized rate by decile (full GBM; fit = out-of-fold deciles, cut and OOS = the registered cuts)'); L.append('')
rows = []
for d in range(1, 11):
    r = [d]
    for per, T in (('fit_oof', D), ('cut', D), ('oos', Do)):
        x = T.filter((pl.col('model') == 'full_gbm') & (pl.col('period') == per) & (pl.col('decile') == d)).row(0, named=True); r += [x['n'], f(x['share'], 3), f(x['rate'], 3), f(x['mv30_mean'], 1)]
    rows.append(r)
table(['decile', 'fit n', 'share', 't2 rate', 'mv30 bps', 'cut n', 'share', 'rate', 'mv30', 'OOS n', 'share', 'rate', 'mv30'], rows)
# ---- 2. the pick and the lift cells
Cf = rd('fit_lift_cells.csv'); Co = rd('oos_lift_cells.csv')
key = ['structure', 'rule', 'width', 'management', 'signal']
J = Cf.join(Co, on=key, how='full', suffix='_oos', coalesce=True)
def lrow(r):
    return [r['signal'], r['structure'], r['rule'], f"{r['width']:.0f}", r['management'],
            r['N'], f(r['mean_pct_risk']), f(r['tod_mean_pct_risk']), f"{f(r['lift_pct_risk'], 2, True)} [{f(r['lift_ci_lo_pct_risk'], 2, True)}, {f(r['lift_ci_hi_pct_risk'], 2, True)}]", f"{f(r['lift_usd'], 2, True)} [{f(r['lift_ci_lo'], 2, True)}, {f(r['lift_ci_hi'], 2, True)}]", f(r['lift_wo_best5'], 2, True), f"{f(r['lift_vs_rest_usd'], 2, True)} [{f(r['lift_vs_rest_ci_lo'], 2, True)}, {f(r['lift_vs_rest_ci_hi'], 2, True)}]",
            r['N_oos'], f(r['mean_pct_risk_oos']), f(r['tod_mean_pct_risk_oos']), f"{f(r['lift_pct_risk_oos'], 2, True)} [{f(r['lift_ci_lo_pct_risk_oos'], 2, True)}, {f(r['lift_ci_hi_pct_risk_oos'], 2, True)}]", f"{f(r['lift_usd_oos'], 2, True)} [{f(r['lift_ci_lo_oos'], 2, True)}, {f(r['lift_ci_hi_oos'], 2, True)}]", f(r['lift_wo_best5_oos'], 2, True), f"{f(r['lift_vs_rest_usd_oos'], 2, True)} [{f(r['lift_vs_rest_ci_lo_oos'], 2, True)}, {f(r['lift_vs_rest_ci_hi_oos'], 2, True)}]",
            f"{f(r['lift_2025'], 2, True)} / {f(r['lift_2026'], 2, True)}"]
hdr = ['signal', 'structure', 'rule', 'w', 'mgmt', 'fit N', 'fit mean %risk', 'fit tod %risk', 'fit lift %risk [CI]', 'fit lift $ [CI]', 'fit lift wo5 $', 'fit lift vs rest $ [CI]', 'OOS N', 'OOS mean %risk', 'OOS tod %risk', 'OOS lift %risk [CI]', 'OOS lift $ [CI]', 'OOS lift wo5 $', 'OOS lift vs rest $ [CI]', 'OOS lift $ 2025 / 2026']
for mg in ('hold', 'stop2x', 'tp50'):
    S = J.filter(pl.col('management') == mg).sort('lift_ci_lo_pct_risk', descending=True)
    L.append(f'## Lift cells, {mg}, every cell, ranked by the FIT lower bound of the lift in % of max risk'); L.append('')
    table(hdr, [lrow(r) for r in S.iter_rows(named=True)])
# counts
for per, C in (('fit', Cf), ('oos', Co)):
    Hh = C.filter(pl.col('management') == 'hold')
    L.append(f"{per}: hold cells {Hh.height}; lift CI (both yardsticks) above zero: {Hh.filter((pl.col('lift_ci_lo_pct_risk') > 0) & (pl.col('lift_ci_lo') > 0)).height}; below zero: {Hh.filter((pl.col('lift_ci_hi_pct_risk') < 0) & (pl.col('lift_ci_hi') < 0)).height}; lift point estimate > 0: {Hh.filter(pl.col('lift_usd') > 0).height}; lift wo best 5 > 0: {Hh.filter(pl.col('lift_wo_best5') > 0).height}; lift vs rest CI above zero: {Hh.filter(pl.col('lift_vs_rest_ci_lo') > 0).height}")
    for mg in ('stop2x', 'tp50'):
        M = C.filter(pl.col('management') == mg)
        L.append(f"{per}: {mg} cells {M.height}; lift CI above zero: {M.filter((pl.col('lift_ci_lo_pct_risk') > 0) & (pl.col('lift_ci_lo') > 0)).height}; of those with the signal cell's own mean > 0: {M.filter((pl.col('lift_ci_lo_pct_risk') > 0) & (pl.col('lift_ci_lo') > 0) & (pl.col('mean_usd') > 0)).height}")
L.append('')
# ---- 3. the pick's full report, fit and OOS
def full(r):
    return [r['N'], r['sessions'], f(r['mean_usd']), f(r['mean_pct_risk']), f"[{f(r['ci_lo'])}, {f(r['ci_hi'])}]", f(r['median_credit']), f(r['win_rate'], 3), f"{f(r['avg_win'])} / {f(r['avg_loss'])}", f(r['full_loss_share'], 3), f"{f(r['p5'])} / {f(r['p1'])} / {f(r['worst'])}", f"{r['worst_session']} {f(r['worst_session_usd'])}", f(r['total_usd'], 0), f(r['profit_factor']), f"{f(r['max_drawdown'], 0)} / {r['longest_losing_streak']}", f(r['wo_best5']), f(r.get('best5_share_of_total'), 2),
            ', '.join(f"{y} {f(r.get(f'mean_{y}'))} (n {r.get(f'n_{y}')})" for y in (2022, 2023, 2024, 2025, 2026) if r.get(f'n_{y}')), f(r.get('friction_share_of_gross'), 2), f"{f(r.get('credit_fill'))} -> {f(r.get('credit_mid'))}", f(r.get('spread_cost_usd')), f(r.get('fees_usd')), f(r.get('gross_mid_nofee_usd'))]
fhdr = ['period', 'cell', 'N', 'sessions', 'mean $', '% risk', 'CI $', 'median credit', 'win', 'avg win / loss', 'full-loss', 'p5 / p1 / worst', 'worst session', 'total $', 'PF', 'max DD / streak', 'wo best 5 $', 'best-5 share', 'by year $', 'friction share of gross', 'credit fill -> mid', 'spread $', 'fees $', 'gross at mid $']
L.append('## Full report: the pre-registered (not pre-registrable) pick and its neighbours, the signal cells, fit and OOS'); L.append('')
rows = []
picks = [('put', 'd15', 2.0, 'hold', 'D1-2'), ('put', 'd15', 2.0, 'hold', 'D1'), ('put', 'em1', 2.0, 'hold', 'D1-2'), ('put', 'd25', 2.0, 'hold', 'D1-2'), ('condor', 'd25', 2.0, 'hold', 'D1-2'), ('condor', 'em1', 2.0, 'hold', 'D1-2'), ('put', 'd15', 1.0, 'stop2x', 'D1-2'), ('put', 'd25', 1.0, 'stop2x', 'D1')]
for st, ru, w, mg, sg in picks:
    for per, C in (('fit', Cf), ('oos', Co)):
        q = C.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w) & (pl.col('management') == mg) & (pl.col('signal') == sg))
        if q.height: rows.append([per, f'{sg} {st} {ru} w{w:.0f} {mg}'] + full(q.row(0, named=True)))
table(fhdr, rows)
# ---- 4. the unconditional benchmark pooled, fit vs OOS
Pf = rd('fit_uncond_pooled.csv'); Po = rd('oos_uncond_pooled.csv')
L.append('## Unconditional benchmark, pooled over the 12 scans, hold: fit and OOS (ranked by the fit lower bound in % of risk)'); L.append('')
JP = Pf.filter(pl.col('management') == 'hold').join(Po.filter(pl.col('management') == 'hold'), on=['structure', 'rule', 'width'], suffix='_oos').sort('ci_lo_pct_risk', descending=True)
rows = []
for r in JP.iter_rows(named=True):
    rows.append([r['structure'], r['rule'], f"{r['width']:.0f}", r['N'], f(r['mean_usd']), f(r['mean_pct_risk']), f"[{f(r['ci_lo'])}, {f(r['ci_hi'])}]", '*' if r['significant'] else '', f(r['win_rate'], 2), f(r['full_loss_share'], 3), f(r['wo_best5']), f(r['profit_factor']), f(r['friction_share_of_gross'], 2),
                 r['N_oos'], f(r['mean_usd_oos']), f(r['mean_pct_risk_oos']), f"[{f(r['ci_lo_oos'])}, {f(r['ci_hi_oos'])}]", '*' if r['significant_oos'] else '', f(r['win_rate_oos'], 2), f(r['full_loss_share_oos'], 3), f(r['wo_best5_oos']), f(r['profit_factor_oos']), f"{f(r['max_drawdown_oos'], 0)} / {r['longest_losing_streak_oos']}", f(r['friction_share_of_gross_oos'], 2)])
table(['structure', 'rule', 'w', 'fit N', 'mean $', '% risk', 'CI $', 'sig', 'win', 'full-loss', 'wo5 $', 'PF', 'friction', 'OOS N', 'mean $', '% risk', 'CI $', 'sig', 'win', 'full-loss', 'wo5 $', 'PF', 'max DD / streak', 'friction'], rows)
# ---- 5. by scan: the significance count and the strongest, fit and OOS; plus the fit-strongest cells read OOS
Uf = rd('fit_uncond_byscan.csv').filter(pl.col('management') == 'hold'); Uo = rd('oos_uncond_byscan.csv').filter(pl.col('management') == 'hold')
L.append('## Unconditional benchmark by scan minute, hold: significant cells (CI of the mean $ above zero) of 30, the strongest fit cell, and that same cell OOS'); L.append('')
rows = []
for s in sorted(Uf['m_scan'].unique().to_list()):
    a = Uf.filter(pl.col('m_scan') == s).sort('ci_lo_pct_risk', descending=True); t = a.row(0, named=True)
    b = Uo.filter(pl.col('m_scan') == s); o = b.filter((pl.col('structure') == t['structure']) & (pl.col('rule') == t['rule']) & (pl.col('width') == t['width'])).row(0, named=True)
    bo = b.sort('ci_lo_pct_risk', descending=True).row(0, named=True)
    rows.append([t['scan'], int(a['significant'].sum()), f"{t['structure']} {t['rule']} w{t['width']:.0f}", t['N'], f(t['mean_pct_risk']), f"{f(t['mean_usd'])} [{f(t['ci_lo'])}, {f(t['ci_hi'])}]", int(b['significant'].sum()), o['N'], f(o['mean_pct_risk']), f"{f(o['mean_usd'])} [{f(o['ci_lo'])}, {f(o['ci_hi'])}]", '*' if o['significant'] else '', f"{bo['structure']} {bo['rule']} w{bo['width']:.0f}: {f(bo['mean_pct_risk'])}% [{f(bo['ci_lo'])}, {f(bo['ci_hi'])}]"])
table(['scan', 'fit: significant of 30', 'fit strongest', 'N', '% risk', 'mean $ [CI]', 'OOS: significant of 30', 'that cell OOS N', '% risk', 'mean $ [CI]', 'sig', 'OOS strongest (for the record, not chosen)'], rows)
L.append('## Unconditional by scan, hold, the headline structures: mean % of max risk at each scan, fit / OOS (* = CI of the mean $ above zero)'); L.append('')
heads = [('condor', 'd25', 2.0), ('condor', 'em1', 2.0), ('condor', 'd20', 2.0), ('condor', 'd25', 1.0), ('put', 'd25', 2.0), ('put', 'd15', 2.0), ('call', 'd25', 2.0), ('call', 'em1', 2.0)]
scans = sorted(Uf['m_scan'].unique().to_list())
rows = []
for st, ru, w in heads:
    r = [f'{st} {ru} w{w:.0f}']
    for s in scans:
        a = Uf.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w) & (pl.col('m_scan') == s)).row(0, named=True); b = Uo.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w) & (pl.col('m_scan') == s)).row(0, named=True)
        r.append(f"{f(a['mean_pct_risk'], 1, True)}{'*' if a['significant'] else ''} / {f(b['mean_pct_risk'], 1, True)}{'*' if b['significant'] else ''}")
    rows.append(r)
table(['cell'] + [Uf.filter(pl.col('m_scan') == s)['scan'][0] for s in scans], rows)
# ---- 6. the pick's lift by scan, fit and OOS
Bf = rd('fit_lift_byscan.csv'); Bo = rd('oos_lift_byscan.csv')
L.append('## The pick (D1-2, put d15 w2, hold): lift by scan minute, fit and OOS ($ a spread; CI paired session bootstrap)'); L.append('')
rows = []
for s in scans:
    sc = Uf.filter(pl.col('m_scan') == s)['scan'][0]
    a = Bf.filter((pl.col('structure') == 'put') & (pl.col('rule') == 'd15') & (pl.col('width') == 2.0) & (pl.col('management') == 'hold') & (pl.col('signal') == 'D1-2') & (pl.col('scan') == sc))
    b = Bo.filter((pl.col('structure') == 'put') & (pl.col('rule') == 'd15') & (pl.col('width') == 2.0) & (pl.col('management') == 'hold') & (pl.col('signal') == 'D1-2') & (pl.col('scan') == sc))
    a = a.row(0, named=True) if a.height else None; b = b.row(0, named=True) if b.height else None
    rows.append([sc] + ([a['N'], f(a['mean_pct_risk']), f(a['tod_mean_pct_risk']), f"{f(a['lift_usd'], 2, True)} [{f(a['lift_ci_lo'], 2, True)}, {f(a['lift_ci_hi'], 2, True)}]"] if a else ['—'] * 4) + ([b['N'], f(b['mean_pct_risk']), f(b['tod_mean_pct_risk']), f"{f(b['lift_usd'], 2, True)} [{f(b['lift_ci_lo'], 2, True)}, {f(b['lift_ci_hi'], 2, True)}]"] if b else ['—'] * 4))
table(['scan', 'fit N', 'signal % risk', 'tod % risk', 'lift $ [CI]', 'OOS N', 'signal % risk', 'tod % risk', 'lift $ [CI]'], rows)
# where the D1-2 minutes fall
L.append('D1-2 share of the signal rows by scan (the pick, hold): fit ' + ', '.join(f"{r['scan']} {r['N']}" for r in Bf.filter((pl.col('structure') == 'put') & (pl.col('rule') == 'd15') & (pl.col('width') == 2.0) & (pl.col('management') == 'hold') & (pl.col('signal') == 'D1-2')).sort('scan').iter_rows(named=True)) + '; OOS ' + ', '.join(f"{r['scan']} {r['N']}" for r in Bo.filter((pl.col('structure') == 'put') & (pl.col('rule') == 'd15') & (pl.col('width') == 2.0) & (pl.col('management') == 'hold') & (pl.col('signal') == 'D1-2')).sort('scan').iter_rows(named=True)))
L.append('')
# ---- 7. management, pooled unconditional, fit and OOS
L.append('## Management, pooled unconditional, mean % of max risk: hold / stop2x / tp50, fit and OOS'); L.append('')
rows = []
for (st, ru, w), g in Pf.group_by('structure', 'rule', 'width', maintain_order=True):
    o = Po.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w))
    def mm(T, mg): q = T.filter(pl.col('management') == mg); return f(q['mean_pct_risk'][0]) if q.height else '—'
    rows.append([f'{st} {ru} w{w:.0f}', mm(g, 'hold'), mm(g, 'stop2x'), mm(g, 'tp50'), mm(o, 'hold'), mm(o, 'stop2x'), mm(o, 'tp50')])
table(['cell', 'fit hold', 'stop2x', 'tp50', 'OOS hold', 'stop2x', 'tp50'], sorted(rows))
open(os.path.join(OUT, 'tables.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
