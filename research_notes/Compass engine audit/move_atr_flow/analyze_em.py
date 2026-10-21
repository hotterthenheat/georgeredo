"""Module 7: the expected move (questions 1 and 2). Reads out/scans_<P>.parquet and out/touches_<P>.parquet.
Writes out/em_exceed.csv, out/em_contain.csv, out/em_fade.csv, out/em_fade_stress.csv, out/king_reach.csv
  python3 -I analyze_em.py [SPY,QQQ,IWM,SPXW]
"""
import os, sys, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
PRODUCTS = sys.argv[1].split(',') if len(sys.argv) > 1 else [p for p in ('SPY', 'QQQ', 'IWM', 'SPXW') if os.path.exists(os.path.join(OUT, f'scans_{p}.parquet'))]
SQRT_HALF_PI = 1.2533141
PERIODS = {'pick 2022-2024': ('2022-01-01', '2024-12-31'), 'read 2025-2026': ('2025-01-01', '2026-12-31')}
LABEL = {5: '09:35', 30: '10:00', 60: '10:30', 90: '11:00', 120: '11:30', 150: '12:00', 180: '12:30', 210: '13:00', 240: '13:30', 270: '14:00', 300: '14:30', 330: '15:00', 360: '15:30', 380: '15:50'}

def period_col():
    return pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('pick 2022-2024')).otherwise(pl.lit('read 2025-2026')).alias('period')

def boot_days(df, col, n=2000, seed=0):
    """95% range of the mean of `col` from a bootstrap that resamples sessions (days) with replacement"""
    g = df.group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('k'))
    s = g['s'].to_numpy(); k = g['k'].to_numpy(); D = len(s)
    if D < 10: return (np.nan, np.nan)
    rng = np.random.default_rng(seed); idx = rng.integers(0, D, (n, D))
    means = s[idx].sum(1) / k[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

def stress(df, col):
    """mean of col, its day-bootstrap range, without the best 5 days, and by year"""
    o = dict(trades=df.height, days=df['session'].n_unique(), mean=float(df[col].mean()))
    o['ci_lo'], o['ci_hi'] = boot_days(df, col)
    g = df.group_by('session').agg(pl.col(col).sum().alias('s')).sort('s', descending=True)
    best5 = set(g['session'][:5].to_list()); rest = df.filter(~pl.col('session').is_in(best5))
    o['wo_best5'] = float(rest[col].mean()) if rest.height else np.nan
    o['best5_share_of_total'] = float(g['s'][:5].sum() / df[col].sum()) if df[col].sum() > 0 else np.nan
    for y in ('2022', '2023', '2024', '2025', '2026'):
        yy = df.filter(pl.col('session').str.starts_with(y)); o[f'mean_{y}'] = float(yy[col].mean()) if yy.height else np.nan
    return o

ex_rows, ct_rows, fd_rows, st_rows, kg_rows = [], [], [], [], []
for P in PRODUCTS:
    S = pl.read_parquet(os.path.join(OUT, f'scans_{P}.parquet')).with_columns(period_col())
    S = S.filter(pl.col('straddle') > 0)
    S = S.with_columns((pl.col('rem_high') - pl.col('spot')).alias('up_ext'), (pl.col('spot') - pl.col('rem_low')).alias('dn_ext'),
                       ((pl.col('close') - pl.col('spot')).abs() / pl.col('straddle')).alias('close_mult'))
    for (period, s), g in S.group_by('period', 'm_scan'):
        for mult in (1.0, SQRT_HALF_PI):
            M = mult * g['straddle']
            up = (g['up_ext'] >= M); dn = (g['dn_ext'] >= M)
            o = dict(product=P, period=period, scan=LABEL[s], m_scan=s, mult=round(mult, 4), sessions=g.height,
                     exceed_either=float((up | dn).mean()), exceed_up=float(up.mean()), exceed_down=float(dn.mean()),
                     close_outside=float((g['close_mult'] > mult).mean()))
            if g['rem_high_bar'].null_count() < g.height:
                ub = (g['rem_high_bar'] - g['spot']) >= M; db = (g['spot'] - g['rem_low_bar']) >= M
                o['exceed_either_barHL'] = float((ub | db).mean())
            ex_rows.append(o)
        cm = g['close_mult'].to_numpy()
        ct_rows.append(dict(product=P, period=period, scan=LABEL[s], m_scan=s, sessions=g.height,
                            q683_close_over_straddle=float(np.quantile(cm, 0.683)), q50=float(np.quantile(cm, 0.5)), q95=float(np.quantile(cm, 0.95)),
                            sd_close_over_straddle=float(np.sqrt(np.mean(cm ** 2))), mean_abs_close_over_straddle=float(cm.mean()),
                            share_within_1x=float((cm <= 1).mean()), share_within_1p2533x=float((cm <= SQRT_HALF_PI).mean())))
    # ---- touches and the fade trade
    T = pl.read_parquet(os.path.join(OUT, f'touches_{P}.parquet')).with_columns(period_col())
    sgn = pl.when(pl.col('side') == 'up').then(1.0).otherwise(-1.0)
    T = T.with_columns((sgn * (pl.col('px_t') - pl.col('px_15')) / pl.col('px_t') * 1e4).alias('fade15_bps'),
                       (sgn * (pl.col('px_t') - pl.col('px_30')) / pl.col('px_t') * 1e4).alias('fade30_bps'),
                       (sgn * (pl.col('px_t') - pl.col('px_60')) / pl.col('px_t') * 1e4).alias('fade60_bps'),
                       (sgn * (pl.col('px_t') - pl.col('close')) / pl.col('px_t') * 1e4).alias('fade_close_bps'),
                       (sgn * (pl.col('close') - pl.col('px_t')) < 0).alias('close_back_inside'),
                       (pl.col('t') - pl.col('m_scan')).alias('mins_to_touch'), (390 - pl.col('t')).alias('mins_left'))
    T = T.with_columns(pl.col('mult').round(4))
    for keys, label in ((['period', 'mult', 'm_scan'], 'by scan'), (['period', 'mult'], 'all scans'), (['period', 'mult', 'side'], 'by side')):
        for k, g in T.group_by(keys):
            kd = dict(zip(keys, k)); tr = g.filter(pl.col('entry_ask').is_not_null())
            o = dict(product=P, cut=label, **kd, scan=LABEL.get(kd.get('m_scan'), 'all'), touches=g.height, sessions=g['session'].n_unique(),
                     p_close_back_inside=float(g['close_back_inside'].mean()), fade15_bps=float(g['fade15_bps'].mean()), fade30_bps=float(g['fade30_bps'].mean()),
                     fade60_bps=float(g['fade60_bps'].mean()), fade_close_bps=float(g['fade_close_bps'].mean()), median_mins_left=float(g['mins_left'].median()),
                     trades=tr.height, entry_ask_median=float(tr['entry_ask'].median()) if tr.height else np.nan,
                     ret_trail=float(tr['ret_trail'].mean()) if tr.height else np.nan, pnl_trail_usd=float(tr['pnl_trail'].mean()) if tr.height else np.nan,
                     win_trail=float((tr['pnl_trail'] > 0).mean()) if tr.height else np.nan, stopped=float(tr['stopped'].mean()) if tr.height else np.nan,
                     ret_hold=float(tr['ret_hold'].mean()) if tr.height else np.nan, pnl_hold_usd=float(tr['pnl_hold'].mean()) if tr.height else np.nan)
            fd_rows.append(o)
    for (period, mult), g in T.filter(pl.col('entry_ask').is_not_null()).group_by('period', 'mult'):
        for col in ('pnl_trail', 'ret_trail', 'pnl_hold'):
            o = dict(product=P, period=period, mult=mult, measure=col); o.update(stress(g, col)); st_rows.append(o)
    # ---- the king proxy's reachability
    K = S.filter(pl.col('king').is_not_null() & (pl.col('king') != pl.col('spot')))
    K = K.with_columns(((pl.col('king') - pl.col('spot')) / pl.col('straddle')).alias('dist_em'))
    K = K.with_columns(pl.col('dist_em').abs().alias('ad'), (pl.col('king') > pl.col('spot')).alias('above'))
    K = K.with_columns(pl.when(pl.col('above')).then(pl.col('up_ext') >= pl.col('king') - pl.col('spot')).otherwise(pl.col('dn_ext') >= pl.col('spot') - pl.col('king')).alias('king_reached'),
                       pl.when(pl.col('above')).then(pl.col('dn_ext') >= pl.col('king') - pl.col('spot')).otherwise(pl.col('up_ext') >= pl.col('spot') - pl.col('king')).alias('mirror_reached'))
    cuts = [(0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 99)]
    for (period,), g in K.group_by('period'):
        # the marginal reach of a level at distance d (same side distribution): for each row, P over all sessions at that scan that the
        # same-side extension (in straddle units) >= this row's distance
        g = g.with_columns((pl.col('up_ext') / pl.col('straddle')).alias('u'), (pl.col('dn_ext') / pl.col('straddle')).alias('v'))
        for lo, hi in cuts:
            b = g.filter((pl.col('ad') >= lo) & (pl.col('ad') < hi))
            if b.height == 0: continue
            marg = []
            for s, bb in b.group_by('m_scan'):
                gs = g.filter(pl.col('m_scan') == s[0]); u = gs['u'].to_numpy(); v = gs['v'].to_numpy()
                for ad, ab in zip(bb['ad'].to_numpy(), bb['above'].to_numpy()):
                    marg.append(float(((u if ab else v) >= ad).mean()))
            kg_rows.append(dict(product=P, period=period, dist_lo=lo, dist_hi=hi, n=b.height, sessions=b['session'].n_unique(),
                                king_reached=float(b['king_reached'].mean()), mirror_reached=float(b['mirror_reached'].mean()), any_level_same_dist=float(np.mean(marg)),
                                king_above_share=float(b['above'].mean()), median_dist=float(b['ad'].median())))
        # the rule itself: |dist| <= 1 vs 1-2
        for lab, lo, hi in (('|d|<=1', 0, 1.0 + 1e-9), ('1<|d|<=2', 1.0 + 1e-9, 2.0 + 1e-9), ('|d|>2', 2.0 + 1e-9, 99)):
            b = g.filter((pl.col('ad') >= lo) & (pl.col('ad') < hi))
            kg_rows.append(dict(product=P, period=period, dist_lo=lab, dist_hi='', n=b.height, sessions=b['session'].n_unique(),
                                king_reached=float(b['king_reached'].mean()) if b.height else np.nan, mirror_reached=float(b['mirror_reached'].mean()) if b.height else np.nan,
                                any_level_same_dist=np.nan, king_above_share=float(b['above'].mean()) if b.height else np.nan, median_dist=float(b['ad'].median()) if b.height else np.nan))
    print(P, 'done', flush=True)

r = lambda rows: pl.DataFrame(rows, infer_schema_length=None)
r(ex_rows).sort('product', 'period', 'm_scan', 'mult').write_csv(os.path.join(OUT, 'em_exceed.csv'))
r(ct_rows).sort('product', 'period', 'm_scan').write_csv(os.path.join(OUT, 'em_contain.csv'))
r(fd_rows).sort('product', 'cut', 'period', 'mult').write_csv(os.path.join(OUT, 'em_fade.csv'))
r(st_rows).sort('product', 'period', 'mult', 'measure').write_csv(os.path.join(OUT, 'em_fade_stress.csv'))
r(kg_rows).write_csv(os.path.join(OUT, 'king_reach.csv'))
pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(200)
print(r(ct_rows).select('product', 'period', 'scan', 'sessions', 'q683_close_over_straddle', 'sd_close_over_straddle', 'share_within_1x', 'share_within_1p2533x'))
print(r(ex_rows).select('product', 'period', 'scan', 'mult', 'sessions', 'exceed_either', 'exceed_up', 'exceed_down', 'close_outside'))
F = r(fd_rows)
print(F.filter(pl.col('cut') == 'all scans').select('product', 'period', 'mult', 'touches', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'trades', 'entry_ask_median', 'ret_trail', 'pnl_trail_usd', 'win_trail', 'ret_hold'))
print(F.filter(pl.col('cut') == 'by scan').select('product', 'period', 'mult', 'scan', 'touches', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'median_mins_left', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail').sort('product', 'period', 'mult', 'scan'))
print(r(st_rows))
print(r(kg_rows))
