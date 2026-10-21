"""Module 8: daily bars, ATR(14) and the swing-entry test.

Daily bars are built from the 1-minute underlying files (RAW/data/underlying/<SYM>, 2012-06 -> 2026-10): open = the
09:30 bar's open, high/low over the regular session's bars, close = the last bar stamped at or before 16:00 (the closing
auction print when the 16:00 bar is there; 13:00 on a half day). atr_14 is Wilder's (a 14-day RMA of the true range).
sma20/sma50 of the close; range_pos_day = (close - low) / (high - low); range_pos_20 = the close's place in the
20-day high/low. Forward returns 5/10/20 sessions from the close.

Swing events (known at the close):
  chase_day : range_pos_day > 0.95 and close > sma20                 ("chasing range_position > 0.95")
  chase_20  : range_pos_20 > 0.95 (a close in the top 5% of the 20-day range)
  pullback  : sma20 > sma50, close <= sma20 and the prior close > sma20 (the first touch of the 20-day mean from above)
  near_mean : sma20 > sma50 and |close / sma20 - 1| <= 0.5%
  all       : every day
Also the UW one-year daily cross-section (data_lake/unusualwhales/ohlc__1d, regular-session rows), the same events, forward
returns market-adjusted (minus the equal-weight mean of all names that day), t-stats from per-date means.
Writes out/daily_<SYM>.parquet, out/swing_etf.csv, out/swing_uw.csv
"""
import os, sys, numpy as np, polars as pl
RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
LAKE = '/home/user/georgeredo/data_lake/unusualwhales'

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def wilder(tr, n=14):
    """Wilder's ATR: the first value the mean of the first n finite true ranges, then (13 x prior + TR) / 14; it restarts
    the same way after a gap (a NaN true range)."""
    atr = np.full(len(tr), np.nan); run = []
    for i in range(len(tr)):
        if not np.isfinite(tr[i]): run = []; continue
        if i > 0 and np.isfinite(atr[i - 1]): atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
        else:
            run.append(tr[i])
            if len(run) == n: atr[i] = float(np.mean(run)); run = []
    return atr

def build(sym):
    rows = []
    folder = os.path.join(RAW, 'data', 'underlying', sym)
    for f in sorted(os.listdir(folder)):
        b = pl.read_parquet(os.path.join(folder, f), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).with_columns(minute_of('timestamp').alias('m'))
        b = b.filter(pl.col('close').is_not_null() & pl.col('close').is_not_nan() & pl.col('high').is_not_nan() & pl.col('low').is_not_nan() & pl.col('open').is_not_nan() & (pl.col('m') >= 0) & (pl.col('m') <= 390))
        if b.height < 100: continue   # the vendor's files before 2017-06 hold no prices (every field NaN): skipped
        rows.append(dict(date=f[:-8], open=float(b['open'][0]), high=float(b['high'].max()), low=float(b['low'].min()), close=float(b['close'][-1]),
                         volume=int(b['volume'].sum()), bars=b.height, half_day=bool(b['m'].max() < 300)))
    d = pl.DataFrame(rows).sort('date')
    d = d.with_columns(pl.col('close').shift(1).alias('prior_close'))
    d = d.with_columns(pl.max_horizontal(pl.col('high') - pl.col('low'), (pl.col('high') - pl.col('prior_close')).abs(), (pl.col('low') - pl.col('prior_close')).abs()).alias('tr'))
    d = d.with_columns(pl.Series('atr14', wilder(d['tr'].to_numpy())))
    d = d.with_columns(pl.col('close').rolling_mean(20).alias('sma20'), pl.col('close').rolling_mean(50).alias('sma50'),
                       pl.col('high').rolling_max(20).alias('hi20'), pl.col('low').rolling_min(20).alias('lo20'),
                       ((pl.col('close') - pl.col('low')) / (pl.col('high') - pl.col('low'))).alias('range_pos_day'),
                       (pl.col('open') / pl.col('prior_close') - 1).alias('gap'), (pl.col('close') / pl.col('prior_close') - 1).alias('ret1'))
    d = d.with_columns(((pl.col('close') - pl.col('lo20')) / (pl.col('hi20') - pl.col('lo20'))).alias('range_pos_20'),
                       *[(pl.col('close').shift(-k) / pl.col('close') - 1).alias(f'fwd{k}') for k in (5, 10, 20)])
    d.write_parquet(os.path.join(OUT, f'daily_{sym}.parquet'))
    print(sym, d.height, d['date'][0], d['date'][-1], 'half days', int(d['half_day'].sum()), flush=True)
    return d

def events(d):
    return d.with_columns(
        ((pl.col('range_pos_day') > 0.95) & (pl.col('close') > pl.col('sma20'))).alias('chase_day'),
        (pl.col('range_pos_20') > 0.95).alias('chase_20'),
        ((pl.col('sma20') > pl.col('sma50')) & (pl.col('close') <= pl.col('sma20')) & (pl.col('prior_close') > pl.col('sma20'))).alias('pullback'),
        ((pl.col('sma20') > pl.col('sma50')) & ((pl.col('close') / pl.col('sma20') - 1).abs() <= 0.005)).alias('near_mean'),
        pl.lit(True).alias('all'))

EV = ['chase_day', 'chase_20', 'pullback', 'near_mean', 'all']

def block_boot(x, block=20, n=2000, seed=0):
    """a 95% range of the mean from a moving-block bootstrap on a daily series (overlapping forward windows)"""
    x = np.asarray(x, float); x = x[~np.isnan(x)]; L = len(x)
    if L < block * 2: return (np.nan, np.nan)
    rng = np.random.default_rng(seed); nb = int(np.ceil(L / block)); means = np.empty(n)
    for i in range(n):
        st = rng.integers(0, L - block + 1, nb); idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:L]; means[i] = x[idx].mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))

def stats(x, label):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) == 0: return dict(n=0)
    lo, hi = block_boot(x)
    srt = np.sort(x)[::-1]; wo5 = srt[5:].mean() if len(x) > 5 else np.nan
    return dict(n=len(x), mean_bps=1e4 * x.mean(), median_bps=1e4 * np.median(x), hit=float((x > 0).mean()), ci_lo_bps=1e4 * lo, ci_hi_bps=1e4 * hi, wo_best5_bps=1e4 * wo5)

def swing_etf():
    rows = []
    for sym in ('SPY', 'QQQ', 'IWM'):
        d = events(pl.read_parquet(os.path.join(OUT, f'daily_{sym}.parquet')))
        for period, lo, hi in (('2012-2024', '2012-01-01', '2024-12-31'), ('2025-2026', '2025-01-01', '2026-12-31'), ('2022-2024', '2022-01-01', '2024-12-31')):
            p = d.filter((pl.col('date') >= lo) & (pl.col('date') <= hi))
            for ev in EV:
                e = p.filter(pl.col(ev))
                for k in (5, 10, 20):
                    o = dict(sym=sym, period=period, event=ev, horizon=k); o.update(stats(e[f'fwd{k}'].to_numpy(), ev)); rows.append(o)
    pl.DataFrame(rows).write_csv(os.path.join(OUT, 'swing_etf.csv'))
    return pl.DataFrame(rows)

def swing_uw():
    parts = [pl.scan_parquet(os.path.join(LAKE, f'ohlc__1d.part0{i}.parquet')).filter(pl.col('market_time') == 'r') for i in (1, 2, 3)]
    o = pl.concat(parts).select('ticker', 'date', pl.col('open').cast(pl.Float64), pl.col('high').cast(pl.Float64), pl.col('low').cast(pl.Float64),
                                pl.col('close').cast(pl.Float64), pl.col('volume').cast(pl.Float64)).collect()
    info = pl.read_parquet(os.path.join(LAKE, 'info.parquet'))
    opt = info.filter(pl.col('has_options').cast(pl.Utf8).str.to_lowercase() == 'true')['ticker'].unique() if 'has_options' in info.columns else None
    o = o.sort('ticker', 'date')
    o = o.with_columns(pl.col('close').shift(1).over('ticker').alias('prior_close'), pl.len().over('ticker').alias('n'), pl.col('volume').rolling_mean(20).over('ticker').alias('adv20'))
    o = o.filter((pl.col('n') >= 200) & (pl.col('high') > pl.col('low')))
    if opt is not None: o = o.filter(pl.col('ticker').is_in(opt))
    o = o.with_columns(pl.col('close').rolling_mean(20).over('ticker').alias('sma20'), pl.col('close').rolling_mean(50).over('ticker').alias('sma50'),
                       pl.col('high').rolling_max(20).over('ticker').alias('hi20'), pl.col('low').rolling_min(20).over('ticker').alias('lo20'),
                       ((pl.col('close') - pl.col('low')) / (pl.col('high') - pl.col('low'))).alias('range_pos_day'))
    o = o.with_columns(((pl.col('close') - pl.col('lo20')) / (pl.col('hi20') - pl.col('lo20'))).alias('range_pos_20'),
                       *[(pl.col('close').shift(-k).over('ticker') / pl.col('close') - 1).alias(f'fwd{k}') for k in (5, 10, 20)])
    o = o.filter((pl.col('close') >= 5) & (pl.col('adv20') >= 300_000) & pl.col('sma50').is_not_null())
    # market-adjust: minus the equal-weight mean across names that day
    for k in (5, 10, 20):
        o = o.with_columns((pl.col(f'fwd{k}') - pl.col(f'fwd{k}').mean().over('date')).alias(f'adj{k}'))
    o = events(o)
    rows = []
    for ev in EV:
        e = o.filter(pl.col(ev))
        for k in (5, 10, 20):
            x = e.filter(pl.col(f'adj{k}').is_not_null())
            per_date = x.group_by('date').agg(pl.col(f'adj{k}').mean().alias('m'), pl.len().alias('k'))
            m = per_date['m'].to_numpy(); t = m.mean() / (m.std(ddof=1) / np.sqrt(len(m))) if len(m) > 2 else np.nan
            rows.append(dict(event=ev, horizon=k, n_obs=x.height, n_dates=per_date.height, n_tickers=x['ticker'].n_unique(), mean_adj_bps=1e4 * x[f'adj{k}'].mean(),
                             mean_raw_bps=1e4 * x[f'fwd{k}'].mean(), hit_adj=float((x[f'adj{k}'] > 0).mean()), t_by_date=t, first=x['date'].min(), last=x['date'].max()))
    R = pl.DataFrame(rows); R.write_csv(os.path.join(OUT, 'swing_uw.csv')); return R

if __name__ == '__main__':
    pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_rows(100)
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('build', 'all'):
        for s in ('SPY', 'QQQ', 'IWM'): build(s)
    if what in ('etf', 'all'): print(swing_etf())
    if what in ('uw', 'all'): print(swing_uw())

def build_spx():
    """SPX daily bars from the index prints (RAW/data/index/SPX, 2017-06 -> 2026-10): open = the first print, high/low
    over the prints 09:30-16:00, close = the last print at or before 16:00. Same ATR as the ETFs."""
    rows = []
    folder = os.path.join(RAW, 'data', 'index', 'SPX')
    for f in sorted(os.listdir(folder)):
        p = pl.read_parquet(os.path.join(folder, f)).with_columns(minute_of('timestamp').alias('m')).filter(pl.col('price').is_not_null() & pl.col('price').is_not_nan() & (pl.col('m') >= 0) & (pl.col('m') <= 390))
        if p.height < 100: continue
        rows.append(dict(date=f[:-8], open=float(p['price'][0]), high=float(p['price'].max()), low=float(p['price'].min()), close=float(p['price'][-1]), volume=0, bars=p.height, half_day=bool(p['m'].max() < 300)))
    d = pl.DataFrame(rows).sort('date').with_columns(pl.col('close').shift(1).alias('prior_close'))
    d = d.with_columns(pl.max_horizontal(pl.col('high') - pl.col('low'), (pl.col('high') - pl.col('prior_close')).abs(), (pl.col('low') - pl.col('prior_close')).abs()).alias('tr'))
    d = d.with_columns(pl.Series('atr14', wilder(d['tr'].to_numpy())))
    d.write_parquet(os.path.join(OUT, 'daily_SPX.parquet')); print('SPX', d.height, d['date'][0], d['date'][-1], flush=True)

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'spx':
    build_spx()
