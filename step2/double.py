"""Step 2a: can a same-day (0DTE) contract be doubled? Every contract on SPY, QQQ, IWM and SPX, bought at fixed times
of the session, followed minute by minute to the close.

One row per contract per entry time. Read from the same raw one-minute NBBO and underlying prices as step 1, with the
same clock, half days and settlement (step1/breakdown.py). Prices are per share; x100 for one contract.

The entry
- Bought at the ask at one of ENTRIES (9:31 am, 10:00, 10:30, 11:00, 12:00, 1:00 pm, 2:00, 3:00, 3:30), when the
  contract has a two-sided quote at that minute with an ask above zero. An entry at or after the close (1:00 pm on a
  half day) is not taken.
- otm_entry_pct: the strike's distance from the underlying at the entry minute, in %, out of the money positive for
  calls and puts alike.

What happened after it (minutes after the entry, to the close)
- max_bid / max_bid_minute: the highest bid; max_multiple = max_bid / entry_ask.
- double_minute: the first minute the bid reached twice the entry ask (+100%). A limit order to sell at twice the
  entry price would have filled by then: the bid cannot rise to a resting offer's price without trading with it.
- half_minute / half_bid: the first minute the bid fell to half the entry ask or lower (-50%), and that bid.
- settle: worth at the close (intrinsic against the underlying's close), as in step 1.

The three ways out, all per share, before fees
- hold:       settle - entry_ask
- tp100:      +entry_ask if the bid reached twice the entry ask (sold at exactly twice), else settle - entry_ask
- tp100_sl50: +entry_ask if the bid reached twice the entry ask before it fell to half; else, if it fell to half, sold
              at that minute's bid (half_bid - entry_ask); else settle - entry_ask.
Nothing here picks contracts: every contract quoted at the entry minute is in. The summaries group them.

Stored per product (step2/out/entries_<PRODUCT>.parquet): the quotes and minutes (STORED). The distance, multiple,
settle and the three results are recomputed on reading (derived, load), so the files stay small.

  python3 -I step2/double.py                 # every product -> step2/out/entries_<PRODUCT>.parquet
  python3 -I step2/double.py SPY 2024-06-03  # one session, printed
"""
import datetime as dt, os, sys
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW, UNDERLYING, spot_series   # noqa: E402  (the same clock and prices as step 1)

OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
ENTRIES = [1, 30, 60, 90, 150, 210, 270, 330, 360]   # 9:31, 10:00, 10:30, 11:00, 12:00, 1:00 pm, 2:00, 3:00, 3:30
EPS = 1e-9

def session(root, d):
    u = UNDERLYING[root]
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - 570).alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    half_day = spy['timestamp'].max().hour < 15
    close_m = 210 if half_day else 390
    sp = spot_series(u, d).filter(pl.col('m') <= close_m)
    spot_close = float(sp['px'][-1])
    q = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & two).select('strike', 'right', 'm', 'bid', 'ask')
    # the underlying at each entry minute: its last price at or before that minute
    ent = pl.DataFrame({'entry_minute': [e for e in ENTRIES if e < close_m]}, schema={'entry_minute': pl.Int32})
    ent = ent.sort('entry_minute').join_asof(sp.with_columns(pl.col('m').cast(pl.Int32)).sort('m'), left_on='entry_minute', right_on='m', strategy='backward')
    ent = ent.select('entry_minute', pl.col('px').alias('spot_entry'))
    e = q.filter(pl.col('ask') > 0).join(ent, left_on='m', right_on='entry_minute').rename({'m': 'entry_minute', 'bid': 'entry_bid', 'ask': 'entry_ask'})
    k = ['strike', 'right', 'entry_minute']
    # every later quote of the same contract
    j = e.select(k + ['entry_ask']).join(q.select('strike', 'right', 'm', 'bid'), on=['strike', 'right']).filter(pl.col('m') > pl.col('entry_minute'))
    j = j.sort(k + ['m'])
    up = pl.col('bid') >= 2 * pl.col('entry_ask') - EPS
    down = pl.col('bid') <= 0.5 * pl.col('entry_ask') + EPS
    a = j.group_by(k, maintain_order=True).agg(
        pl.len().alias('quotes_after'),
        pl.col('bid').max().alias('max_bid'), pl.col('m').get(pl.col('bid').arg_max()).alias('max_bid_minute'),
        pl.col('m').filter(up).first().alias('double_minute'),
        pl.col('m').filter(down).first().alias('half_minute'), pl.col('bid').filter(down).first().alias('half_bid'),
        pl.col('bid').last().alias('last_bid'),
    )
    r = e.join(a, on=k, how='left').with_columns(
        pl.lit(d).alias('session'), pl.lit(half_day).alias('half_day'), pl.lit(close_m).alias('close_minute'),
        pl.lit(spot_close).alias('spot_close'), pl.col('quotes_after').fill_null(0))
    return r.select(STORED)

# what is written: the quotes and minutes. Everything else is arithmetic on them (derived, below)
STORED = ['session', 'strike', 'right', 'entry_minute', 'entry_bid', 'entry_ask', 'spot_entry', 'quotes_after', 'max_bid', 'max_bid_minute',
          'double_minute', 'half_minute', 'half_bid', 'last_bid', 'spot_close', 'half_day', 'close_minute']

def derived(r, root):
    """the figures computed from the stored ones: distance, multiple, settle and the three ways out"""
    r = r.with_columns(
        pl.lit('SPX' if root == 'SPXW' else root).alias('product'),
        pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - pl.col('spot_close')).clip(0)).alias('settle'),
        (pl.when(pl.col('right') == 'CALL').then(pl.col('strike') - pl.col('spot_entry')).otherwise(pl.col('spot_entry') - pl.col('strike')) / pl.col('spot_entry') * 100).alias('otm_entry_pct'),
        (pl.col('max_bid') / pl.col('entry_ask')).alias('max_multiple'),
    )
    hit = pl.col('double_minute').is_not_null()
    stopped_first = pl.col('half_minute').is_not_null() & (~hit | (pl.col('half_minute') < pl.col('double_minute')))
    return r.with_columns(
        (pl.col('settle') - pl.col('entry_ask')).alias('hold'),
        pl.when(hit).then(pl.col('entry_ask')).otherwise(pl.col('settle') - pl.col('entry_ask')).alias('tp100'),
        pl.when(stopped_first).then(pl.col('half_bid') - pl.col('entry_ask'))
          .when(hit).then(pl.col('entry_ask')).otherwise(pl.col('settle') - pl.col('entry_ask')).alias('tp100_sl50'),
        pl.when(stopped_first).then(pl.lit('half')).when(hit).then(pl.lit('double')).otherwise(pl.lit('close')).alias('tp100_sl50_exit'),
    )

def load(root):
    """one product's table with every figure: python3 -I -c 'from step2.double import load; load("SPY")' from the repository"""
    return derived(pl.read_parquet(os.path.join(OUT, f'entries_{root}.parquet')), root)

def run_product(root):
    days = sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        frames = pool.starmap(session, [(root, dt.date.fromisoformat(d)) for d in days], chunksize=8)
    T = pl.concat(frames, how='vertical_relaxed').sort('session', 'entry_minute', 'right', 'strike')
    T.write_parquet(os.path.join(OUT, f'entries_{root}.parquet'), compression='zstd', compression_level=19)
    print(root, 'sessions', len(days), 'entries', T.height, flush=True)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(250)
        x = derived(session(sys.argv[1], dt.date.fromisoformat(sys.argv[2])), sys.argv[1])
        print(x.filter(pl.col('otm_entry_pct').abs() < 0.3))
    else:
        for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): run_product(r)
