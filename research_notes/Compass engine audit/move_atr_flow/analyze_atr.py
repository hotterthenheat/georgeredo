"""Module 8: ATR exhaustion on the 0DTE fades. Reads out/touches_<P>.parquet, out/sweeps_<P>.parquet, out/daily_<SYM>.parquet
and the UW greek-exposure daily table. Writes out/atr_touch.csv, out/atr_sweep.csv, out/atr_gamma.csv
move_atr at the event = (px_event - prior close) / atr14 known at the prior close (the ATR series lagged one session).
ext = move_atr signed into the event's direction (+ for an up touch/sweep, - for a down one): a counter-trend fade sells
into an extension of `ext` ATRs. Buckets of ext: <0.5, 0.5-1, 1-1.5, 1.5-2, >2 (and ext < 0: the event is against the
day's move). The gamma regime is the sign of UW's call_gamma + put_gamma for the PRIOR session (its book at that close),
2025-10-15 -> 2026-10-13 only, positive = dampening per UW's documentation.
"""
import os, sys, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); LAKE = '/home/user/georgeredo/data_lake/unusualwhales'
PRODUCTS = sys.argv[1].split(',') if len(sys.argv) > 1 else [p for p in ('SPY', 'QQQ', 'IWM', 'SPXW') if os.path.exists(os.path.join(OUT, f'touches_{p}.parquet'))]
DAILY = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
UWT = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
BUCKETS = [('<0 (against the day)', -99, 0), ('0-0.5', 0, 0.5), ('0.5-1', 0.5, 1.0), ('1-1.5', 1.0, 1.5), ('1.5-2', 1.5, 2.0), ('>2', 2.0, 99)]
period_col = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('pick 2022-2024')).otherwise(pl.lit('read 2025-2026')).alias('period')

def daily(sym):
    d = pl.read_parquet(os.path.join(OUT, f'daily_{sym}.parquet')).select('date', 'prior_close', pl.col('atr14').shift(1).alias('atr_prev'))
    return d.rename({'date': 'session'})

gex = pl.concat([pl.read_parquet(os.path.join(LAKE, f'greek-exposure.part0{i}.parquet')) for i in (1, 2)])
gex = gex.with_columns((pl.col('call_gamma').cast(pl.Float64) + pl.col('put_gamma').cast(pl.Float64)).alias('net')).select('ticker', 'date', 'net').sort('ticker', 'date')
gex = gex.with_columns(pl.col('net').shift(1).over('ticker').alias('net_prior'), pl.col('date').shift(1).over('ticker').alias('prior_date'))

def summar(g, label, kd):
    tr = g.filter(pl.col('entry_ask').is_not_null())
    return dict(**kd, bucket=label, events=g.height, sessions=g['session'].n_unique(), p_close_back_inside=float(g['close_back_inside'].mean()),
                fade30_bps=float(g['fade30_bps'].mean()), fade_close_bps=float(g['fade_close_bps'].mean()), trades=tr.height,
                ret_trail=float(tr['ret_trail'].mean()) if tr.height else np.nan, pnl_trail_usd=float(tr['pnl_trail'].mean()) if tr.height else np.nan,
                win_trail=float((tr['pnl_trail'] > 0).mean()) if tr.height else np.nan, pnl_hold_usd=float(tr['pnl_hold'].mean()) if tr.height else np.nan,
                ret_hold=float(tr['ret_hold'].mean()) if tr.height else np.nan)

rows_t, rows_s, rows_g = [], [], []
for P in PRODUCTS:
    D = daily(DAILY[P])
    T = pl.read_parquet(os.path.join(OUT, f'touches_{P}.parquet')).filter(pl.col('mult') == 1.0).join(D, on='session', how='inner').with_columns(period_col)
    sgn = pl.when(pl.col('side') == 'up').then(1.0).otherwise(-1.0)
    T = T.with_columns(((pl.col('px_t') - pl.col('prior_close')) / pl.col('atr_prev')).alias('move_atr'))
    T = T.with_columns((sgn * pl.col('move_atr')).alias('ext'), (sgn * (pl.col('px_t') - pl.col('px_30')) / pl.col('px_t') * 1e4).alias('fade30_bps'),
                       (sgn * (pl.col('px_t') - pl.col('close')) / pl.col('px_t') * 1e4).alias('fade_close_bps'), (sgn * (pl.col('close') - pl.col('px_t')) < 0).alias('close_back_inside'))
    # one touch a scan each; a late-day scan's touch at the same minute as an earlier scan's is the same event: keep one row a (session, side, t)
    T1 = T.sort('session', 'side', 't', 'm_scan').unique(subset=['session', 'side', 't'], keep='first')
    for (period,), g in T1.group_by('period'):
        for lab, lo, hi in BUCKETS:
            b = g.filter((pl.col('ext') >= lo) & (pl.col('ext') < hi))
            if b.height: rows_t.append(summar(b, lab, dict(product=P, period=period, event='touch +/-1.0 straddle (one row a touch minute)')))
        rows_t.append(summar(g, 'all', dict(product=P, period=period, event='touch +/-1.0 straddle (one row a touch minute)')))
        for lab, lo, hi in (('|ext|<=1.5', -99, 1.5), ('ext>1.5', 1.5, 99)):
            b = g.filter((pl.col('ext') >= lo) & (pl.col('ext') < hi))
            if b.height: rows_t.append(summar(b, lab, dict(product=P, period=period, event='touch +/-1.0 straddle (one row a touch minute)')))
    # sweeps (ETFs only)
    fs = os.path.join(OUT, f'sweeps_{P}.parquet')
    if os.path.exists(fs):
        S = pl.read_parquet(fs).join(D, on='session', how='inner').with_columns(period_col)
        sgn = pl.when(pl.col('side') == 'up').then(1.0).otherwise(-1.0)
        S = S.with_columns(((pl.col('px_t') - pl.col('prior_close')) / pl.col('atr_prev')).alias('move_atr'))
        S = S.with_columns((sgn * pl.col('move_atr')).alias('ext'), (sgn * (pl.col('px_t') - pl.col('px_30')) / pl.col('px_t') * 1e4).alias('fade30_bps'),
                           (sgn * (pl.col('px_t') - pl.col('close_px')) / pl.col('px_t') * 1e4).alias('fade_close_bps'), (sgn * (pl.col('close_px') - pl.col('px_t')) < 0).alias('close_back_inside'),
                           pl.col('fade_entry_ask').alias('entry_ask'), pl.col('fade_ret_trail').alias('ret_trail'), pl.col('fade_pnl_trail').alias('pnl_trail'),
                           pl.col('fade_pnl_hold').alias('pnl_hold'), pl.col('fade_ret_hold').alias('ret_hold'))
        for (period,), g in S.group_by('period'):
            for lab, lo, hi in BUCKETS + [('|ext|<=1.5', -99, 1.5), ('ext>1.5', 1.5, 99)]:
                b = g.filter((pl.col('ext') >= lo) & (pl.col('ext') < hi))
                if b.height: rows_s.append(summar(b, lab, dict(product=P, period=period, event='sweep of the session high/low (2 bps, closes back inside)')))
            rows_s.append(summar(g, 'all', dict(product=P, period=period, event='sweep of the session high/low (2 bps, closes back inside)')))
        # gamma regime (UW, prior session's net), the read period only
        gx = gex.filter(pl.col('ticker') == UWT[P]).select(pl.col('date').alias('session'), 'net_prior')
        for name, X in (('touch', T1), ('sweep', S)):
            G = X.join(gx, on='session', how='inner').filter(pl.col('net_prior').is_not_null())
            G = G.with_columns(pl.when(pl.col('net_prior') > 0).then(pl.lit('positive')).otherwise(pl.lit('negative')).alias('regime'))
            for (regime,), g in G.group_by('regime'):
                for lab, lo, hi in (('ext<=1.5', -99, 1.5), ('ext>1.5', 1.5, 99), ('ext>1', 1.0, 99), ('all', -99, 99)):
                    b = g.filter((pl.col('ext') >= lo) & (pl.col('ext') < hi))
                    if b.height: rows_g.append(summar(b, lab, dict(product=P, event=name, regime=regime, period='2025-10-16 to 2026-10-09 (UW gamma available)')))
    else:
        gx = gex.filter(pl.col('ticker') == UWT[P]).select(pl.col('date').alias('session'), 'net_prior')
        G = T1.join(gx, on='session', how='inner').filter(pl.col('net_prior').is_not_null()).with_columns(pl.when(pl.col('net_prior') > 0).then(pl.lit('positive')).otherwise(pl.lit('negative')).alias('regime'))
        for (regime,), g in G.group_by('regime'):
            for lab, lo, hi in (('ext<=1.5', -99, 1.5), ('ext>1.5', 1.5, 99), ('ext>1', 1.0, 99), ('all', -99, 99)):
                b = g.filter((pl.col('ext') >= lo) & (pl.col('ext') < hi))
                if b.height: rows_g.append(summar(b, lab, dict(product=P, event='touch', regime=regime, period='2025-10-16 to 2026-10-09 (UW gamma available)')))
    print(P, 'done', flush=True)

pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(300)
A = pl.DataFrame(rows_t, infer_schema_length=None); A.write_csv(os.path.join(OUT, 'atr_touch.csv')); print(A)
if rows_s: B = pl.DataFrame(rows_s, infer_schema_length=None); B.write_csv(os.path.join(OUT, 'atr_sweep.csv')); print(B)
if rows_g: C = pl.DataFrame(rows_g, infer_schema_length=None); C.write_csv(os.path.join(OUT, 'atr_gamma.csv')); print(C)
