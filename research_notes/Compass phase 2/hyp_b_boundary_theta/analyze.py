"""Hypothesis B cells. Reads out/trades_<P>.parquet (engine.py). Two modes:
    python3 -I analyze.py fit    -> out/fit_touch_cells.csv, out/fit_touch_byscan.csv, out/fit_midday_cells.csv, out/prereg.txt
                                    (2022-2024 ONLY; the pre-registered pick is chosen here, mechanically, before any OOS row is read)
    python3 -I analyze.py all    -> out/touch_cells.csv, out/touch_byscan.csv, out/midday_cells.csv, out/summary.txt (both periods)
Periods: fit = sessions <= 2024-12-31, oos = sessions >= 2025-01-01. Fees, fills and management are engine.py's.
A touch cell is ONE ROW A TOUCH MINUTE (session, side, t, mult, rule, width): the audit lists a touch once a scan, and a later
scan's touch at the same minute is the same event and the same trade (analyze_atr.py's de-duplication); the by-scan table
keeps the scan-level rows. Metrics per cell (the `management` column says which exit): N, sessions, mean $ a spread, mean
% of max risk (max risk = width x 100 - credit x 100), win rate, average win/loss, share of full-loss outcomes (pnl <= -95%
of max risk), p5/p1/worst, worst session (its summed $), profit factor, max drawdown and longest losing streak of the 1-lot
sequence (trades in session, entry-minute order), session-bootstrap 95% CI of the mean $, mean $ without the best 5 sessions,
their share of the total, the worst session's effect on the total, and the mean $ by year.
PRE-REGISTERED PICK (fixed before the OOS read): among touch cells with mult 1.0, filter in {all, |move_atr| <= 1.5}, every
product x width x rule x management, the cell with the highest fit-period lower 95% CI bound of mean $ per $100 of max risk,
requiring N >= 300 trades, >= 150 sessions and a positive mean without the best 5 sessions. The midday pick is the same rule
over product x width x structure x rule x management x filter in {all, |move_atr| <= 1.5, each VIX tercile}, scans pooled.
"""
import os, sys, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
MODE = sys.argv[1] if len(sys.argv) > 1 else 'fit'
PRODUCTS = [p for p in ('SPXW', 'SPY') if os.path.exists(os.path.join(OUT, f'trades_{p}.parquet'))]
MGMT = {'hold': 'pnl_hold', 'tp50': 'pnl_tp', 'stop2x': 'pnl_stop', 'tp50+stop2x': 'pnl_both'}
MID_SCANS = [120, 150, 180, 210, 240]
LABEL = {5: '09:35', 30: '10:00', 60: '10:30', 90: '11:00', 120: '11:30', 150: '12:00', 180: '12:30', 210: '13:00', 240: '13:30', 270: '14:00', 300: '14:30', 330: '15:00', 360: '15:30', 380: '15:50'}
period_col = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('fit 2022-2024')).otherwise(pl.lit('oos 2025-2026')).alias('period')
pre = 'fit_' if MODE == 'fit' else ''

def boot(df, col, n=2000, seed=0):
    g = df.group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('k'))
    s = g['s'].to_numpy(); k = g['k'].to_numpy(); D = len(s)
    if D < 10: return (np.nan, np.nan)
    rng = np.random.default_rng(seed); idx = rng.integers(0, D, (n, D))
    means = s[idx].sum(1) / k[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

def stats(df, col):
    df = df.filter(pl.col(col).is_not_null()).sort('session', 'e')
    o = dict(N=df.height, sessions=df['session'].n_unique())
    if df.height == 0: return o
    p = df[col].to_numpy(); risk = df['max_risk'].to_numpy()
    o['mean_usd'] = float(p.mean()); o['mean_pct_risk'] = float((p / risk).mean() * 100)
    o['median_credit'] = float(df['credit'].median()); o['mean_max_risk'] = float(risk.mean())
    w = p > 0; o['win_rate'] = float(w.mean()); o['avg_win'] = float(p[w].mean()) if w.any() else np.nan; o['avg_loss'] = float(p[~w].mean()) if (~w).any() else np.nan
    o['full_loss_share'] = float((p <= -0.95 * risk).mean())
    o['p5'] = float(np.percentile(p, 5)); o['p1'] = float(np.percentile(p, 1)); o['worst'] = float(p.min())
    g = df.group_by('session').agg(pl.col(col).sum().alias('s')).sort('s')
    o['worst_session'] = g['session'][0]; o['worst_session_usd'] = float(g['s'][0])
    tot = float(p.sum()); o['total_usd'] = tot; o['total_wo_worst_session'] = tot - float(g['s'][0])
    gw = p[w].sum(); gl = -p[~w].sum(); o['profit_factor'] = float(gw / gl) if gl > 0 else np.inf
    cum = np.cumsum(p); o['max_drawdown'] = float((np.maximum.accumulate(cum) - cum).max())
    streak = best = 0
    for x in p:
        streak = streak + 1 if x <= 0 else 0; best = max(best, streak)
    o['longest_losing_streak'] = best
    o['ci_lo'], o['ci_hi'] = boot(df, col)
    o['ci_lo_pct_risk'] = o['ci_lo'] / o['mean_max_risk'] * 100 if o['mean_max_risk'] else np.nan
    best5 = set(g['session'][-5:].to_list()); rest = df.filter(~pl.col('session').is_in(best5))
    o['wo_best5'] = float(rest[col].mean()) if rest.height else np.nan
    o['best5_share_of_total'] = float(g['s'][-5:].sum() / tot) if tot > 0 else np.nan
    for y in ('2022', '2023', '2024', '2025', '2026'):
        yy = df.filter(pl.col('session').str.starts_with(y)); o[f'mean_{y}'] = float(yy[col].mean()) if yy.height else np.nan
    return o

def load(P):
    X = pl.read_parquet(os.path.join(OUT, f'trades_{P}.parquet')).with_columns(period_col)
    if MODE == 'fit': X = X.filter(pl.col('period') == 'fit 2022-2024')
    return X

rows_t, rows_s, rows_m = [], [], []
for P in PRODUCTS:
    X = load(P)
    T = X.filter(pl.col('test') == 'touch')
    T1 = T.sort('session', 'touch_side', 'e', 'mult', 'rule', 'width', 'm_scan').unique(subset=['session', 'touch_side', 'e', 'mult', 'rule', 'width'], keep='first')
    S = X.filter(pl.col('test') == 'sched')
    FILTERS = {'all': pl.lit(True), '|move_atr|<=1.5': pl.col('move_atr').abs() <= 1.5, '|move_atr|>1.5': pl.col('move_atr').abs() > 1.5,
               'before 14:00': pl.col('e') < 270, 'after 14:00': pl.col('e') >= 270, 'up touch (call spread)': pl.col('touch_side') == 'up', 'down touch (put spread)': pl.col('touch_side') == 'down',
               '|move_atr|<=1.5 & before 14:00': (pl.col('move_atr').abs() <= 1.5) & (pl.col('e') < 270)}
    for (period, mult, width, rule), g in T1.group_by('period', 'mult', 'width', 'rule'):
        mult = round(float(mult), 4)
        for fname, fexp in FILTERS.items():
            if mult != 1.0 and fname != 'all': continue
            gg = g.filter(fexp)
            for mg, col in MGMT.items():
                rows_t.append(dict(product=P, period=period, test='touch', mult=mult, width=width, rule=rule, filter=fname, management=mg, **stats(gg, col)))
    # ---- by scan: the touch cell against the unconditional sell at the same scan (every session), and the same-session paired difference
    for (period, width, rule, s), g in T.filter(pl.col('mult') == 1.0).group_by('period', 'width', 'rule', 'm_scan'):
        for mg, col in MGMT.items():
            o = dict(product=P, period=period, scan=LABEL[s], m_scan=s, width=width, rule=rule, management=mg)
            st = stats(g, col); o.update({f'touch_{k}': v for k, v in st.items() if k in ('N', 'sessions', 'mean_usd', 'mean_pct_risk', 'win_rate', 'ci_lo', 'ci_hi')})
            brule = 'em1' if rule == 'at' else rule     # the band's own edge is the scan-time analogue of 'at the touch price'
            b = S.filter((pl.col('period') == period) & (pl.col('m_scan') == s) & (pl.col('width') == width) & (pl.col('rule') == brule) & (pl.col('structure') != 'condor'))
            sb = stats(b, col); o.update({f'base_{k}': v for k, v in sb.items() if k in ('N', 'sessions', 'mean_usd', 'mean_pct_risk', 'win_rate', 'ci_lo', 'ci_hi')}); o['base_rule'] = brule
            # paired: the touch trade minus the same session's scan-time sell of the same side, rule and width
            side_of = pl.when(pl.col('touch_side') == 'up').then(pl.lit('call')).otherwise(pl.lit('put')).alias('structure')
            pr = g.with_columns(side_of).select('session', 'structure', pl.col(col).alias('pt'), pl.col('e')).join(b.select('session', 'structure', pl.col(col).alias('pb'), 'max_risk'), on=['session', 'structure'], how='inner')
            pr = pr.with_columns((pl.col('pt') - pl.col('pb')).alias('d'))
            o['paired_N'] = pr.height; o['paired_diff_usd'] = float(pr['d'].mean()) if pr.height else np.nan
            o['paired_ci_lo'], o['paired_ci_hi'] = boot(pr, 'd') if pr.height else (np.nan, np.nan)
            rows_s.append(o)
    # ---- midday: iron condors and one-sided spreads sold 11:30-13:30
    M = S.filter(pl.col('m_scan').is_in(MID_SCANS))
    fitv = pl.read_parquet(os.path.join(OUT, f'trades_{P}.parquet')).filter((pl.col('session') <= '2024-12-31') & (pl.col('test') == 'sched') & pl.col('m_scan').is_in(MID_SCANS) & (pl.col('structure') == 'condor') & (pl.col('rule') == 'd15') & (pl.col('width') == M['width'].min()))
    vq = fitv['vix_e'].drop_nulls().to_numpy(); v1, v2 = (float(np.percentile(vq, 100 / 3)), float(np.percentile(vq, 200 / 3))) if len(vq) else (np.nan, np.nan)
    MF = {'all': pl.lit(True), '|move_atr|<=1.5': pl.col('move_atr').abs() <= 1.5, f'VIX low (<{v1:.1f})': pl.col('vix_e') < v1,
          f'VIX mid ({v1:.1f}-{v2:.1f})': (pl.col('vix_e') >= v1) & (pl.col('vix_e') < v2), f'VIX high (>={v2:.1f})': pl.col('vix_e') >= v2}
    for (period, width, structure, rule), g in M.group_by('period', 'width', 'structure', 'rule'):
        for fname, fexp in MF.items():
            gg = g.filter(fexp)
            for mg, col in MGMT.items():
                rows_m.append(dict(product=P, period=period, test='midday pooled 11:30-13:30', scan='pooled', width=width, structure=structure, rule=rule, filter=fname, management=mg, vix_cuts_fit=f'{v1:.2f}/{v2:.2f}', **stats(gg, col)))
        for s in MID_SCANS:
            gs = g.filter(pl.col('m_scan') == s)
            for mg, col in MGMT.items():
                rows_m.append(dict(product=P, period=period, test='midday by scan', scan=LABEL[s], width=width, structure=structure, rule=rule, filter='all', management=mg, vix_cuts_fit=f'{v1:.2f}/{v2:.2f}', **stats(gs, col)))

TC = pl.DataFrame(rows_t, infer_schema_length=None).sort('product', 'period', 'mult', 'width', 'rule', 'filter', 'management')
BS = pl.DataFrame(rows_s, infer_schema_length=None).sort('product', 'period', 'width', 'rule', 'm_scan', 'management')
MC = pl.DataFrame(rows_m, infer_schema_length=None).sort('product', 'period', 'test', 'width', 'structure', 'rule', 'filter', 'scan', 'management')
TC.write_csv(os.path.join(OUT, f'{pre}touch_cells.csv')); BS.write_csv(os.path.join(OUT, f'{pre}touch_byscan.csv')); MC.write_csv(os.path.join(OUT, f'{pre}midday_cells.csv'))

def pick(df, extra_keys):
    f = df.filter((pl.col('period') == 'fit 2022-2024') & (pl.col('N') >= 300) & (pl.col('sessions') >= 150) & (pl.col('wo_best5') > 0))
    if 'mult' in f.columns: f = f.filter(pl.col('mult') == 1.0)
    f = f.filter(pl.col('filter').is_in(['all', '|move_atr|<=1.5']) | pl.col('filter').str.starts_with('VIX'))
    if 'scan' in f.columns: f = f.filter(pl.col('scan') == 'pooled')
    return f.sort('ci_lo_pct_risk', descending=True).select(['product', 'width'] + extra_keys + ['filter', 'management', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'ci_lo_pct_risk', 'win_rate', 'wo_best5', 'full_loss_share'])

if MODE == 'fit':
    with open(os.path.join(OUT, 'prereg.txt'), 'w') as fh:
        fh.write('PRE-REGISTERED PICK, chosen on 2022-2024 only (the OOS rows were not read by this run: MODE=fit filters them out at load).\n')
        fh.write('Rule: highest fit-period lower 95% CI bound of mean $ per $100 of max risk; N >= 300, sessions >= 150, mean without the best 5 sessions > 0.\n\n')
        pt = pick(TC, ['rule']); fh.write('TOUCH (mult 1.0), candidates ranked:\n' + (pt.head(15).to_pandas().to_string() if False else str(pt.head(15))) + '\n\n')
        fh.write(f'TOUCH PICK: {pt.row(0, named=True) if pt.height else "NO CELL QUALIFIES"}\n\n')
        pm = pick(MC, ['structure', 'rule']); fh.write('MIDDAY (pooled), candidates ranked:\n' + str(pm.head(15)) + '\n\n')
        fh.write(f'MIDDAY PICK: {pm.row(0, named=True) if pm.height else "NO CELL QUALIFIES"}\n')
    print(open(os.path.join(OUT, 'prereg.txt')).read())
else:
    with open(os.path.join(OUT, 'summary.txt'), 'w') as fh:
        pl.Config.set_tbl_rows(400); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260)
        for P in PRODUCTS:
            fh.write(f'==== {P} touch cells (one row a touch minute), mean $ and % of max risk, fit / oos\n')
            t = TC.filter(pl.col('product') == P).select('period', 'mult', 'width', 'rule', 'filter', 'management', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'ci_lo', 'ci_hi', 'win_rate', 'full_loss_share', 'wo_best5', 'profit_factor', 'max_drawdown')
            fh.write(str(t) + '\n')
            fh.write(f'==== {P} midday cells\n')
            m = MC.filter((pl.col('product') == P) & (pl.col('scan') == 'pooled')).select('period', 'width', 'structure', 'rule', 'filter', 'management', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'ci_lo', 'ci_hi', 'win_rate', 'full_loss_share', 'wo_best5', 'profit_factor', 'max_drawdown')
            fh.write(str(m) + '\n')
    print('written', OUT)
