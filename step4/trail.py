"""Step 4a: sell near the high, and buy on the turn. Every same-day contract on SPY, QQQ, IWM and SPX, three ways in and
a trailing stop out.

Ways in (all bought at the ask, at a minute when the contract has a bid and an ask above zero):
- fixed: step 2's 10.5 million trades, bought at 9:31 am, 10:00, 10:30, 11:00, 12:00, 1:00 pm, 2:00, 3:00 or 3:30.
- bounce (k = 1.5, 2, 3, 5): the first minute from 9:36 am to 15 minutes before the close that the contract's ask is at
  least k times the lowest ask it has shown so far that day (before that minute). One trade a contract and k.
- orb: the opening range is the underlying's high and low from 9:31 to 10:00. The first minute after 10:00 (to 15 minutes
  before the close) that the underlying is above the range buys every call; the first minute below it buys every put.

Ways out, from the minute after buying to the close:
- trail20 … trail50: sell at the bid the first minute the bid has fallen 20%, 30%, 40% or 50% from the peak, the peak
  being the highest bid since buying, or the price paid if that is higher (so the trail is also the first stop).
- hold: worth at the close (intrinsic against the underlying's close), as in step 1.
- max_bid: the highest bid after buying, the exact top that only hindsight knows.

Clock, half days and settlement are step 1's (step1/breakdown.py). Prices per share; x100 for one contract.
  python3 -I step4/trail.py                 # every product -> step4/out/trades_<PRODUCT>.parquet
  python3 -I step4/trail.py SPY 2024-06-03  # one session, printed
"""
import datetime as dt, os, sys
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW, UNDERLYING, spot_series   # noqa: E402
from step2.double import ENTRIES                            # noqa: E402

OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
EPS = 1e-9
TRAILS = {'trail20': 0.2, 'trail30': 0.3, 'trail40': 0.4, 'trail50': 0.5}
KS = [1.5, 2.0, 3.0, 5.0]
FIRST_EVENT, LAST_GAP, OR_END = 6, 15, 30   # bounce from 9:36; no event entry in the last 15 minutes; range to 10:00

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def exits(e, q, close_m):
    """e: entries (strike, right, entry_minute, entry_ask, key columns); q: quotes. Trailing exits, best bid, last bid."""
    k = ['strike', 'right', 'entry_minute', 'tag']
    j = e.select(k + ['entry_ask']).join(q.select('strike', 'right', 'm', 'bid'), on=['strike', 'right']).filter(pl.col('m') > pl.col('entry_minute'))
    j = j.sort(k + ['m']).with_columns(pl.max_horizontal(pl.col('bid').cum_max().over(k), pl.col('entry_ask')).alias('peak'))
    aggs = [pl.len().alias('quotes_after'), pl.col('bid').max().alias('max_bid'), pl.col('m').get(pl.col('bid').arg_max()).alias('max_bid_minute')]
    for n, t in TRAILS.items():
        hit = pl.col('bid') <= (1 - t) * pl.col('peak') + EPS
        aggs += [pl.col('m').filter(hit).first().alias(n + '_minute'), pl.col('bid').filter(hit).first().alias(n + '_bid'),
                 pl.col('peak').filter(hit).first().alias(n + '_peak')]
    a = j.group_by(k, maintain_order=True).agg(aggs)
    return e.join(a, on=k, how='left').with_columns(pl.col('quotes_after').fill_null(0))

def session(root, d):
    u = UNDERLYING[root]
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(minute_of('timestamp').alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    half_day = spy['timestamp'].max().hour < 15
    close_m = 210 if half_day else 390
    sp = spot_series(u, d).filter(pl.col('m') <= close_m).with_columns(pl.col('m').cast(pl.Int32)).sort('m')
    spot_close = float(sp['px'][-1])
    q = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & two).select('strike', 'right', 'm', 'bid', 'ask').sort('strike', 'right', 'm')
    qa = q.filter(pl.col('ask') > 0)
    frames = []

    # fixed: step 2's entries
    ents = [x for x in ENTRIES if x < close_m]
    f = qa.filter(pl.col('m').is_in(ents)).rename({'m': 'entry_minute', 'bid': 'entry_bid', 'ask': 'entry_ask'}).with_columns(pl.lit('fixed').alias('tag'))
    frames.append(f)

    # bounce: the ask reaches k times the lowest ask before that minute
    b = qa.with_columns(pl.col('ask').cum_min().over('strike', 'right').shift(1).over('strike', 'right').alias('low_before'))
    b = b.filter((pl.col('m') >= FIRST_EVENT) & (pl.col('m') <= close_m - LAST_GAP) & pl.col('low_before').is_not_null() & (pl.col('low_before') > 0))
    for kk in KS:
        x = b.filter(pl.col('ask') >= kk * pl.col('low_before') - EPS).group_by('strike', 'right', maintain_order=True).first()
        frames.append(x.rename({'m': 'entry_minute', 'bid': 'entry_bid', 'ask': 'entry_ask'}).with_columns(pl.lit(f'bounce{kk:g}').alias('tag')))

    # orb: the first break of the 9:31-10:00 range by the underlying
    rng = sp.filter((pl.col('m') >= 1) & (pl.col('m') <= OR_END))
    if rng.height:
        hi, lo = float(rng['px'].max()), float(rng['px'].min())
        later = sp.filter((pl.col('m') > OR_END) & (pl.col('m') <= close_m - LAST_GAP))
        for right, cond in (('CALL', pl.col('px') > hi), ('PUT', pl.col('px') < lo)):
            hit = later.filter(cond)
            if hit.height:
                t = int(hit['m'][0])
                x = qa.filter((pl.col('m') == t) & (pl.col('right') == right))
                frames.append(x.rename({'m': 'entry_minute', 'bid': 'entry_bid', 'ask': 'entry_ask'}).with_columns(pl.lit('orb').alias('tag')))
    e = pl.concat([fr.select('strike', 'right', 'entry_minute', 'entry_bid', 'entry_ask', 'tag') for fr in frames])
    e = e.with_columns(pl.col('entry_minute').cast(pl.Int32))
    # the underlying when bought (its last price at or before that minute), and the contract's low before buying
    e = e.sort('entry_minute').join_asof(sp.rename({'m': 'sm', 'px': 'spot_entry'}), left_on='entry_minute', right_on='sm', strategy='backward').drop('sm')
    lows = b.select('strike', 'right', 'm', 'low_before')
    e = e.join(lows, left_on=['strike', 'right', 'entry_minute'], right_on=['strike', 'right', 'm'], how='left')
    r = exits(e, q, close_m).with_columns(pl.lit(d).alias('session'), pl.lit(spot_close).alias('spot_close'), pl.lit(close_m).alias('close_minute'),
                                          pl.lit(half_day).alias('half_day'))
    cols = ['session', 'tag', 'strike', 'right', 'entry_minute', 'entry_bid', 'entry_ask', 'low_before', 'spot_entry', 'quotes_after', 'max_bid', 'max_bid_minute'] + \
           [f'{n}_{s}' for n in TRAILS for s in ('minute', 'bid', 'peak')] + ['spot_close', 'close_minute', 'half_day']
    return r.select(cols)

def run_product(root):
    days = sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        frames = pool.starmap(session, [(root, dt.date.fromisoformat(d)) for d in days], chunksize=8)
    T = pl.concat(frames, how='vertical_relaxed').sort('session', 'tag', 'entry_minute', 'right', 'strike')
    T.write_parquet(os.path.join(OUT, f'trades_{root}.parquet'), compression='zstd', compression_level=19)
    print(root, 'sessions', len(days), 'trades', T.height, T.group_by('tag').len().sort('tag').rows(), flush=True)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(30)
        x = session(sys.argv[1], dt.date.fromisoformat(sys.argv[2]))
        print(x.group_by('tag').len().sort('tag'))
        print(x.filter(pl.col('tag').is_in(['bounce3', 'orb'])).sort((pl.col('spot_entry') - pl.col('strike')).abs()).head(8))
    else:
        for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): run_product(r)
