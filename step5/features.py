"""Step 5a: what could be seen at the moment of each turn-up and range-break buy of step 4, for every such trade.

The trades are step 4's (step4/out/trades_<PRODUCT>.parquet), every way in but the fixed times: the first minute a
contract's ask reached 1.5, 2, 3 or 5 times its lowest ask so far (bounce1.5 … bounce5), and the first break of the
9:31-10:00 range (orb). 1,602,401 trades on SPY, QQQ, IWM and SPX. Each keeps step 4's columns (what happened after, for
scoring only) and gains what was known by the end of its entry minute m, from the same raw one-minute data and the
same clock as steps 1-4 (minute 0 = 9:30; an ETF bar stamped t closes at t+1; an SPX or VIX print is stamped when taken):

The contract (its own quotes up to m, every minute with a bid and an ask above zero):
- open_ask: its first ask of the day; hi_before / low_before: its highest and lowest ask before m; low_minute: the last
  minute before m its ask stood at that low; ask_1, ask_5, ask_15: its ask 1, 5 and 15 minutes before m (the last one
  at or before); bid_size, ask_size: the sizes quoted at m.
The underlying (its price each minute, carried forward):
- px_1, px_5, px_15, px_30: its price 1, 5, 15 and 30 minutes before m; hi_so_far, lo_so_far: its high and low from the
  open to m; hi_5, lo_5: the same 5 minutes before m; rv15: the standard deviation of its one-minute returns over the 15
  minutes to m.
VIX: vix (at m), vix_open (first print of the day), vix_15 (15 minutes before m).
The chain: straddle (the at-the-money call and put mids at m, the strike nearest the price with both quoted and asks above
zero, as in step 3) and straddle_open (the same at the first minute it can be read).
The session: spot_open, prior_close, gap and prior_range from step 3's session table.

Nothing after m is read for a feature. step5/verify.py re-derives a sample from the raw files with separate code.
  python3 -I step5/features.py                 # every product -> step5/out/features_<PRODUCT>.parquet
  python3 -I step5/features.py SPY 2024-06-03  # one session, printed
"""
import datetime as dt, os, sys
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW, UNDERLYING, spot_series   # noqa: E402

OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
LAGS = (1, 5, 15, 30)

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def grid(series, close_m, name):
    """one row a minute 1..close_m with the last value at or before it"""
    g = pl.DataFrame({'m': pl.int_range(1, close_m + 1, eager=True).cast(pl.Int32)})
    return g.join_asof(series.select(pl.col('m').cast(pl.Int32), pl.col('px').alias(name)).sort('m'), on='m', strategy='backward')

def session(root, d, T):
    """T: step 4's non-fixed trades of this session"""
    close_m = int(T['close_minute'][0])
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
    c = c.with_columns(minute_of('timestamp').alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    qa = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & two & (pl.col('ask') > 0)).select('strike', 'right', 'm', 'bid', 'ask', 'bid_size', 'ask_size').sort('strike', 'right', 'm')

    # the contract's own path up to each minute
    k = ['strike', 'right']
    qa = qa.with_columns(pl.col('ask').cum_min().over(k).alias('_cm'))
    qa = qa.with_columns(pl.when(pl.col('ask') <= pl.col('_cm')).then(pl.col('m')).otherwise(None).alias('_lm'))
    qa = qa.with_columns(
        pl.col('ask').first().over(k).alias('open_ask'),
        pl.col('ask').cum_max().shift(1).over(k).alias('hi_before'),
        pl.col('_cm').shift(1).over(k).alias('low_before_f'),
        pl.col('_lm').forward_fill().shift(1).over(k).alias('low_minute')).drop('_cm', '_lm')
    e = T.join(qa.select(k + ['m', 'open_ask', 'hi_before', 'low_before_f', 'low_minute', 'bid_size', 'ask_size']),
               left_on=k + ['entry_minute'], right_on=k + ['m'], how='left')
    lag_src = qa.select(k + ['m', 'ask'])
    for L in (1, 5, 15):
        e = e.with_columns((pl.col('entry_minute') - L).cast(pl.Int32).alias('_t')).sort('_t')
        e = e.join_asof(lag_src.rename({'m': '_t', 'ask': f'ask_{L}'}).sort('_t'), on='_t', by=k, strategy='backward').drop('_t')

    # the underlying, a row a minute
    sp = spot_series(UNDERLYING[root], d).filter(pl.col('m') <= close_m)
    g = grid(sp, close_m, 'px')
    g = g.with_columns(pl.col('px').cum_max().alias('hi_so_far'), pl.col('px').cum_min().alias('lo_so_far'),
                       (pl.col('px') / pl.col('px').shift(1) - 1).alias('_r1'))
    g = g.with_columns(*[pl.col('px').shift(L).alias(f'px_{L}') for L in LAGS],
                       pl.col('hi_so_far').shift(5).alias('hi_5'), pl.col('lo_so_far').shift(5).alias('lo_5'),
                       pl.col('_r1').rolling_std(15, min_samples=10).alias('rv15')).drop('_r1')
    # VIX
    v = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')).with_columns(minute_of('timestamp').alias('m')) \
        .filter(pl.col('price').is_not_null() & (pl.col('m') >= 1)).select('m', pl.col('price').alias('px'))
    vg = grid(v, close_m, 'vix').with_columns(pl.col('vix').drop_nulls().first().alias('vix_open'), pl.col('vix').shift(15).alias('vix_15'))
    # the at-the-money straddle each minute
    mid = qa.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    pairs = mid.filter(pl.col('right') == 'CALL').select('m', 'strike', pl.col('mid').alias('cm')).join(
        mid.filter(pl.col('right') == 'PUT').select('m', 'strike', pl.col('mid').alias('pm')), on=['m', 'strike'])
    pairs = pairs.join(g.select('m', 'px'), on='m').filter(pl.col('px').is_not_null()).with_columns((pl.col('strike') - pl.col('px')).abs().alias('dist'))
    atm = pairs.sort('m', 'dist', 'strike').group_by('m', maintain_order=True).first().select('m', (pl.col('cm') + pl.col('pm')).alias('straddle')).sort('m')
    st_open = float(atm['straddle'][0]) if atm.height else None
    mg = g.join(vg, on='m', how='left').join(atm, on='m', how='left').rename({'m': 'entry_minute'})
    e = e.join(mg, on='entry_minute', how='left').with_columns(pl.lit(st_open, pl.Float64).alias('straddle_open'),
                                                              pl.lit(float(sp['px'][0])).alias('spot_open'))
    return e.drop('low_before_f').sort('tag', 'entry_minute', 'right', 'strike'), e['low_before_f'], e['low_before']

def run_product(root):
    T = pl.read_parquet(os.path.join(ROOT, 'step4', 'out', f'trades_{root}.parquet')).filter(pl.col('tag') != 'fixed')
    parts = {d: x for (d,), x in T.group_by('session')}
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        out = pool.starmap(session, [(root, d, parts[d]) for d in sorted(parts)], chunksize=8)
    F = pl.concat([o[0] for o in out], how='vertical_relaxed')
    # the running low here and step 4's must agree on every trade
    a = pl.concat([o[1] for o in out]); b = pl.concat([o[2] for o in out])
    bad = int((((a - b).abs() > 1e-9).fill_null(False) | (a.is_null() != b.is_null())).sum())
    if bad: raise SystemExit(f'{root}: {bad} trades whose low before buying differs from step 4')
    day = pl.read_parquet(os.path.join(ROOT, 'step3', 'out', f'features_{root}.parquet'), columns=['session', 'prior_close', 'gap', 'prior_range']).unique('session')
    F = F.join(day, on='session', how='left').sort('session', 'tag', 'entry_minute', 'right', 'strike')
    if F.height != T.height: raise SystemExit(f'{root}: {F.height} rows out for {T.height} trades in')
    F.write_parquet(os.path.join(OUT, f'features_{root}.parquet'), compression='zstd', compression_level=19)
    print(root, 'sessions', len(parts), 'trades', F.height, 'low checks ok', flush=True)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(60); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(12)
        d = dt.date.fromisoformat(sys.argv[2])
        T = pl.read_parquet(os.path.join(ROOT, 'step4', 'out', f'trades_{sys.argv[1]}.parquet')).filter((pl.col('tag') != 'fixed') & (pl.col('session') == d))
        x, a, b = session(sys.argv[1], d, T)
        print(x.filter(pl.col('tag') == 'bounce3').sort((pl.col('spot_entry') - pl.col('strike')).abs()).head(6))
        print('low differences', int((((a - b).abs() > 1e-9).fill_null(False) | (a.is_null() != b.is_null())).sum()), 'of', len(a))
    else:
        for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): run_product(r)
