"""Step 1b: every same-day (0DTE) option contract on SPY, QQQ, IWM and SPX (root SPXW), broken down one by one.

One row per contract per session, from the raw one-minute NBBO (bid and ask) and the underlying's one-minute prices
(RAW, outside the repository). Prices are per share; multiply by 100 for one contract. Nothing here is modelled: every
figure is a quote, a price, or arithmetic on them.

Definitions
- Minutes count from 09:30 (minute 0) to 16:00 (minute 390). The session closes at 16:00, or 13:00 on a half day
  (found from SPY's bars, which stop at 13:00 on a half day). Quotes are read from 09:31 (the 09:30
  stamp is the pre-open book) to the close; a minute counts when the bid and the ask are both there and ask >= bid.
- open_*: the first quoted minute. close_*: the last quoted minute at or before the session's close.
- mid = (bid + ask) / 2. high/low are of the mid; best_bid is the highest bid (the most a holder could sell for) and
  best_ask the lowest ask (the least a buyer could pay), each with its time.
- spot_*: the underlying at each minute (SPY/QQQ/IWM: the close of the one-minute bar ending then; SPX: the index print). settle: the contract's value
  at the close, max(spot_close - strike, 0) for a call and max(strike - spot_close, 0) for a put.
- buy_open_hold: bought at the opening ask, held to the close (settle - open_ask). sell_open_hold: sold at the opening
  bid, held to the close (open_bid - settle). run_up / draw_down: the best and worst bid after the open, against the
  opening ask.
- best_long: in hindsight, the most a buyer could have made: buy at an ask, sell at a later bid or hold to the close.
  best_short: sell at a bid, buy back at a later ask or let it expire at the close. Both with their times.
No fees are taken off; the bid/ask is in every figure that buys or sells.

  python3 -I step1/breakdown.py            # every product -> step1/out/contracts_<PRODUCT>.parquet
  python3 -I step1/breakdown.py SPY 2024-06-03   # one session, printed
"""
import datetime as dt, os, sys
import numpy as np, polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'); os.makedirs(OUT, exist_ok=True)
UNDERLYING = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
TZ = 'America/New_York'

def spot_series(u, d):
    """minute (0 = 09:30) -> underlying price, for the minutes that have one"""
    if u == 'SPX':
        p = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).rename({'price': 'px'})
    else:
        p = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet'), columns=['timestamp', 'close']).rename({'close': 'px'})
    p = p.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - 570).alias('m'))
    # an ETF's one-minute bar stamped 15:59 closes at 16:00: its close is the price one minute after the stamp.
    # An SPX print is stamped at the instant it was taken.
    if u != 'SPX': p = p.with_columns((pl.col('m') + 1).alias('m'))
    return p.filter(pl.col('px').is_not_null()).select('m', 'px').sort('m')

def session(root, d):
    u = UNDERLYING[root]
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - 570).alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    # a half day (close 13:00): SPY's regular-session bars stop at 13:00 (on a full day the last is stamped 15:59). The
    # vendor repeats the last option quote, frozen, from 13:15 to 16:00 and SPX keeps printing, so neither tells.
    # The vendor's 13:00 ETF bar (the closing auction's prints) and SPX's prints after 13:00 are not read.
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    half_day = spy['timestamp'].max().hour < 15
    close_m = 210 if half_day else 390
    sp = spot_series(u, d).filter(pl.col('m') <= close_m)
    spot = dict(spot_open=float(sp['px'][0]), spot_open_minute=int(sp['m'][0]), spot_close=float(sp['px'][-1]), spot_close_minute=int(sp['m'][-1]),
                close_minute=close_m, half_day=half_day, spot_high=float(sp['px'].max()), spot_low=float(sp['px'].min()))
    # quotes from 09:31 (the 09:30 stamp is the pre-open book) to the close
    q = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & two)
    q = q.sort('strike', 'right', 'm').with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    k = ['strike', 'right']
    # hindsight: the cheapest ask before each minute, the richest bid before each minute (within the contract)
    q = q.with_columns(pl.col('ask').cum_min().over(k).shift(1).over(k).alias('prev_min_ask'),
                       pl.col('bid').cum_max().over(k).shift(1).over(k).alias('prev_max_bid'))
    q = q.with_columns((pl.col('bid') - pl.col('prev_min_ask')).alias('long_gain'), (pl.col('prev_max_bid') - pl.col('ask')).alias('short_gain'))
    first = lambda col: pl.col(col).first()
    g = q.group_by(k, maintain_order=True).agg(
        pl.len().alias('quoted_minutes'),
        first('m').alias('open_minute'), first('bid').alias('open_bid'), first('ask').alias('open_ask'), first('mid').alias('open_mid'),
        pl.col('m').last().alias('close_quote_minute'), pl.col('bid').last().alias('close_bid'), pl.col('ask').last().alias('close_ask'), pl.col('mid').last().alias('close_mid'),
        pl.col('mid').max().alias('high'), pl.col('m').get(pl.col('mid').arg_max()).alias('high_minute'),
        pl.col('mid').min().alias('low'), pl.col('m').get(pl.col('mid').arg_min()).alias('low_minute'),
        pl.col('bid').max().alias('best_bid'), pl.col('m').get(pl.col('bid').arg_max()).alias('best_bid_minute'),
        pl.col('ask').min().alias('best_ask'), pl.col('m').get(pl.col('ask').arg_min()).alias('best_ask_minute'),
        pl.col('bid').slice(1).max().alias('max_bid_after_open'), pl.col('bid').slice(1).min().alias('min_bid_after_open'),
        ((pl.col('ask') - pl.col('bid')) / ((pl.col('ask') + pl.col('bid')) / 2)).filter(pl.col('ask') + pl.col('bid') > 0).median().alias('spread_median'),
        (pl.col('ask') - pl.col('bid')).median().alias('spread_median_usd'),
        (pl.col('bid') == 0).sum().alias('zero_bid_minutes'),
        pl.col('long_gain').max().alias('best_long_quotes'), pl.col('m').get(pl.col('long_gain').arg_max()).alias('best_long_exit_minute'),
        pl.col('short_gain').max().alias('best_short_quotes'), pl.col('m').get(pl.col('short_gain').arg_max()).alias('best_short_exit_minute'),
    )
    S = spot['spot_close']
    g = g.with_columns(
        pl.lit(root).alias('product'), pl.lit(d).alias('session'),
        pl.when(pl.col('right') == 'CALL').then((S - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - S).clip(0)).alias('settle'),
        *[pl.lit(v).alias(n) for n, v in spot.items()],
    )
    g = g.with_columns(
        (pl.col('settle') > 0).alias('expired_itm'),
        ((pl.col('strike') - pl.col('spot_open')) / pl.col('spot_open')).alias('strike_vs_open'),
        pl.when(pl.col('right') == 'CALL').then(pl.col('strike') > pl.col('spot_open')).otherwise(pl.col('strike') < pl.col('spot_open')).alias('otm_at_open'),
        (pl.col('settle') - pl.col('open_ask')).alias('buy_open_hold'),
        (pl.col('open_bid') - pl.col('settle')).alias('sell_open_hold'),
        (pl.col('max_bid_after_open') - pl.col('open_ask')).alias('run_up'),
        (pl.col('min_bid_after_open') - pl.col('open_ask')).alias('draw_down'),
        # holding to the close is also an exit (long) and letting it expire is also a buy-back (short)
        pl.max_horizontal('best_long_quotes', pl.col('settle') - pl.col('best_ask')).alias('best_long'),
        pl.max_horizontal('best_short_quotes', pl.col('best_bid') - pl.col('settle')).alias('best_short'),
    )
    g = g.with_columns(pl.when(pl.col('best_long') == pl.col('best_long_quotes')).then(pl.lit('quote')).otherwise(pl.lit('close')).alias('best_long_exit'),
                       pl.when(pl.col('best_short') == pl.col('best_short_quotes')).then(pl.lit('quote')).otherwise(pl.lit('close')).alias('best_short_exit'))
    return g.drop('best_long_quotes', 'best_short_quotes')

def run_product(root):
    days = sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        frames = pool.starmap(session, [(root, dt.date.fromisoformat(d)) for d in days], chunksize=8)
    T = pl.concat(frames, how='vertical_relaxed')
    cols = ['product', 'session', 'strike', 'right'] + [c for c in T.columns if c not in ('product', 'session', 'strike', 'right')]
    T = T.select(cols).sort('session', 'right', 'strike')
    T.write_parquet(os.path.join(OUT, f'contracts_{root}.parquet'), compression='zstd', compression_level=10)
    print(root, 'sessions', len(days), 'contracts', T.height, flush=True)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250)
        print(session(sys.argv[1], dt.date.fromisoformat(sys.argv[2])).filter(pl.col('strike').is_between(525, 532)))
    else:
        for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): run_product(r)
