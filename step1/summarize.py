"""Step 1c: summaries of the per-contract breakdown (step1/out/contracts_*.parquet), for the page and the repository.
Descriptive only: what each kind of same-day contract did, 2022-2026. Nothing is tested and nothing is a trade rule.
Writes step1/out/: by_distance.csv, timing.csv, recent_chains.csv, products.csv.
  python3 -I step1/summarize.py
"""
import os
import polars as pl

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

def clock(col):
    """minute of the session (0 = 9:30 am) as New York clock time, e.g. 9:43 am"""
    t = pl.col(col).cast(pl.Int32) + 570
    h, m = t // 60, t % 60
    h12 = pl.when(h > 12).then(h - 12).otherwise(h)
    return pl.format('{}:{} {}', h12.cast(pl.Utf8), m.cast(pl.Utf8).str.zfill(2), pl.when(h >= 12).then(pl.lit('pm')).otherwise(pl.lit('am')))
T = pl.concat([pl.read_parquet(os.path.join(OUT, f'contracts_{p}.parquet')) for p in ('SPY', 'QQQ', 'IWM', 'SPXW')], how='vertical_relaxed')
T = T.with_columns(pl.when(pl.col('product') == 'SPXW').then(pl.lit('SPX')).otherwise(pl.col('product')).alias('product'))
# distance from the money at the open, in % of the underlying, signed so that out of the money is positive for both rights
T = T.with_columns(pl.when(pl.col('right') == 'CALL').then(pl.col('strike_vs_open')).otherwise(-pl.col('strike_vs_open')).mul(100).alias('otm_pct'))
EDGES = [(-1e9, -1.0, 'ITM more than 1%'), (-1.0, -0.5, 'ITM 0.5–1%'), (-0.5, 0.0, 'ITM 0–0.5%'), (0.0, 0.25, 'OTM 0–0.25%'), (0.25, 0.5, 'OTM 0.25–0.5%'),
         (0.5, 1.0, 'OTM 0.5–1%'), (1.0, 2.0, 'OTM 1–2%'), (2.0, 1e9, 'OTM more than 2%')]
b = pl.lit(None, pl.Utf8); o = pl.lit(None, pl.Int32)
for i, (lo, hi, lab) in enumerate(EDGES):
    f = (pl.col('otm_pct') > lo) & (pl.col('otm_pct') <= hi)
    b = pl.when(f).then(pl.lit(lab)).otherwise(b); o = pl.when(f).then(pl.lit(i)).otherwise(o)
T = T.with_columns(b.alias('distance'), o.alias('distance_order'))

# 1. by product, right and distance: what a contract of that kind did, per contract (x100), no fees
D = T.filter(pl.col('open_ask') > 0).group_by('product', 'right', 'distance', 'distance_order').agg(
    pl.len().alias('contracts'),
    pl.col('expired_itm').mean().alias('expired_itm'),
    (pl.col('open_ask') * 100).median().alias('open_ask_usd_median'),
    (pl.col('spread_median')).median().alias('spread_pct_median'),
    (pl.col('buy_open_hold') > 0).mean().alias('buy_hold_win_rate'),
    (pl.col('buy_open_hold') * 100).mean().alias('buy_hold_avg_usd'),
    (pl.col('buy_open_hold') * 100).max().alias('buy_hold_best_usd'),
    (pl.col('buy_open_hold') * 100).min().alias('buy_hold_worst_usd'),
    # selling needs a bid: a contract quoted $0 bid at the open could not be sold, so the selling figures use only
    # contracts with a bid at the open
    (pl.col('open_bid') > 0).sum().alias('sellable_contracts'),
    (pl.col('sell_open_hold') > 0).filter(pl.col('open_bid') > 0).mean().alias('sell_hold_win_rate'),
    (pl.col('sell_open_hold') * 100).filter(pl.col('open_bid') > 0).mean().alias('sell_hold_avg_usd'),
    (pl.col('sell_open_hold') * 100).filter(pl.col('open_bid') > 0).max().alias('sell_hold_best_usd'),
    (pl.col('sell_open_hold') * 100).filter(pl.col('open_bid') > 0).min().alias('sell_hold_worst_usd'),
    (pl.col('run_up') > 0).mean().alias('ever_above_entry'),
    (pl.col('best_long') * 100).median().alias('best_long_usd_median'),
    (pl.col('best_short') * 100).median().alias('best_short_usd_median'),
    pl.col('high_minute').median().alias('high_minute_median'),
).sort('product', 'right', 'distance_order')
D = D.with_columns(pl.concat_str([pl.col('product'), pl.col('right'), pl.col('distance')], separator=' | ').alias('id'), clock('high_minute_median').alias('high_time_median'))
D.write_csv(os.path.join(OUT, 'by_distance.csv'))

# 2. when contracts near the money make their high and their low (half-hour of the session), full days only
N = T.filter(~pl.col('half_day') & (pl.col('otm_pct').abs() <= 0.5))
rows = []
for col, lab in (('high_minute', 'High'), ('low_minute', 'Low')):
    x = N.with_columns(((pl.col(col) - 1) // 30).clip(0, 12).alias('slot')).group_by('product', 'right', 'slot').agg(pl.len().alias('n'))
    x = x.with_columns((pl.col('n') / pl.col('n').sum().over('product', 'right')).alias('share'), pl.lit(lab).alias('what'))
    rows.append(x)
M = pl.concat(rows).with_columns((pl.col('slot') * 30).alias('slot_minute'))
M = M.with_columns(clock('slot_minute').alias('from')).drop('slot_minute')
M = M.with_columns(pl.concat_str([pl.col('product'), pl.col('right'), pl.col('what'), pl.col('slot').cast(pl.Utf8)], separator=' | ').alias('id')).sort('product', 'right', 'what', 'slot')
M.write_csv(os.path.join(OUT, 'timing.csv'))

# 3. the chain contract by contract for the last 20 sessions of each product, strikes within 2% of the open
last = T.group_by('product').agg(pl.col('session').unique().sort().tail(20).alias('s')).explode('s')
R = T.join(last, left_on=['product', 'session'], right_on=['product', 's']).filter(pl.col('otm_pct').abs() <= 2.0)
R = R.select('product', 'session', 'strike', 'right', 'otm_pct', 'spot_open', 'spot_close', 'open_bid', 'open_ask', 'high', 'high_minute', 'low', 'low_minute',
             'close_bid', 'close_ask', 'settle', 'expired_itm', 'buy_open_hold', 'sell_open_hold', 'best_long', 'best_long_exit_minute', 'best_short',
             'spread_median').with_columns(pl.col('session').cast(pl.Utf8))
R = R.with_columns(pl.concat_str([pl.col('product'), pl.col('session'), pl.col('right'), pl.col('strike').cast(pl.Utf8)], separator=' | ').alias('id'),
                   clock('high_minute').alias('high_time'), clock('low_minute').alias('low_time'), clock('best_long_exit_minute').alias('best_long_exit_time'),
                   pl.when(pl.col('expired_itm')).then(pl.lit('In the money')).otherwise(pl.lit('Worthless')).alias('finished'))
for c in ('otm_pct', 'spread_median'): R = R.with_columns(pl.col(c).round(4))
R.sort('product', 'session', 'right', 'strike').write_csv(os.path.join(OUT, 'recent_chains.csv'))

# 4. products
P = T.group_by('product').agg(pl.col('session').min().alias('first'), pl.col('session').max().alias('last'), pl.col('session').n_unique().alias('sessions'),
                              pl.len().alias('contracts'), pl.col('half_day').filter(pl.col('half_day')).len().alias('half_day_contracts')).sort('product')
P.write_csv(os.path.join(OUT, 'products.csv'))
pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_rows(70)
print(P); print(D.filter(pl.col('product') == 'SPY').select('right', 'distance', 'contracts', 'expired_itm', 'open_ask_usd_median', 'buy_hold_win_rate', 'buy_hold_avg_usd', 'sell_hold_win_rate', 'sell_hold_avg_usd', 'sell_hold_worst_usd', 'high_minute_median'))
print('recent chain rows', R.height, os.path.getsize(os.path.join(OUT, 'recent_chains.csv')))
