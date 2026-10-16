"""Step 3a: every trade of step 2, followed to each profit target, each stop and each time exit, with what was known
when it was bought.

The trades are step 2's: every same-day contract on SPY, QQQ, IWM and SPX, bought at the ask at 9:31 am, 10:00, 10:30,
11:00, 12:00, 1:00 pm, 2:00, 3:00 or 3:30. They come from the same raw one-minute quotes, with the same clock, half days and
settlement (step1/breakdown.py, step2/double.py).

For each trade, minutes after the entry to the close:
- t125 … t1100: the first minute the bid reached 1.25, 1.5, 2, 2.5, 3, 4, 6 and 11 times the price paid (+25%, +50%,
  +100%, +150%, +200%, +300%, +500%, +1,000%). A resting order to sell at that price would have filled by then.
- s70, s50, s30: the first minute the bid fell to 70%, 50% and 30% of the price paid (-30%, -50%, -70%), with that
  minute's bid (s70_bid …): a stop sells at the bid.
- the bid at time exits: c30_bid and c10_bid, the last bid 30 and 10 minutes before the close; h30_bid, h60_bid and
  h120_bid, the last bid 30, 60 and 120 minutes after buying (none when that is past the close).
- max_bid; settle comes from spot_close as in step 1.

What was known when it was bought (features_<PRODUCT>.parquet, one row per session and entry time):
- spot_open, spot_entry, prior_close (the session before's close), gap = open / prior close - 1, move = entry / open - 1,
  range_so_far = (high - low since the open) / open, prior_range = the session before's (high - low) / open,
- vix_entry: VIX at the entry minute,
- straddle_entry: the at-the-money call and put mids added up at the entry minute (the strike nearest the price with both
  quoted, each with an ask above zero), and implied_move = straddle_entry / spot_entry: the move the options were pricing for the rest of the day.

  python3 -I step3/paths.py                 # every product -> step3/out/paths_<PRODUCT>.parquet, features_<PRODUCT>.parquet
  python3 -I step3/paths.py SPY 2024-06-03  # one session, printed
"""
import datetime as dt, os, sys
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW, UNDERLYING, spot_series   # noqa: E402  (the same clock and prices as steps 1 and 2)
from step2.double import ENTRIES                            # noqa: E402

OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
EPS = 1e-9
TARGETS = {'t125': 1.25, 't150': 1.5, 't200': 2.0, 't250': 2.5, 't300': 3.0, 't400': 4.0, 't600': 6.0, 't1100': 11.0}
STOPS = {'s70': 0.7, 's50': 0.5, 's30': 0.3}

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def session(root, d):
    u = UNDERLYING[root]
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(minute_of('timestamp').alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    half_day = spy['timestamp'].max().hour < 15
    close_m = 210 if half_day else 390
    sp = spot_series(u, d).filter(pl.col('m') <= close_m).with_columns(pl.col('m').cast(pl.Int32))
    q = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & two).select('strike', 'right', 'm', 'bid', 'ask')
    ents = [e for e in ENTRIES if e < close_m]

    # what was known at each entry minute
    ent = pl.DataFrame({'entry_minute': ents}, schema={'entry_minute': pl.Int32}).sort('entry_minute')
    ent = ent.join_asof(sp.sort('m'), left_on='entry_minute', right_on='m', strategy='backward').rename({'px': 'spot_entry'}).drop('m')
    so_far = [sp.filter(pl.col('m') <= e).select(pl.lit(e, pl.Int32).alias('entry_minute'), pl.col('px').max().alias('high_so_far'), pl.col('px').min().alias('low_so_far')) for e in ents]
    ent = ent.join(pl.concat(so_far), on='entry_minute')
    vix = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')).with_columns(minute_of('timestamp').alias('m')) \
        .filter(pl.col('price').is_not_null() & (pl.col('m') >= 1)).select(pl.col('m').cast(pl.Int32), pl.col('price').alias('vix_entry')).sort('m')
    ent = ent.join_asof(vix, left_on='entry_minute', right_on='m', strategy='backward').drop('m')
    # the at-the-money straddle: the strike nearest the price with both a call and a put quoted at that minute
    at = q.filter(pl.col('m').is_in(ents) & (pl.col('ask') > 0)).with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    pairs = at.filter(pl.col('right') == 'CALL').select('m', 'strike', pl.col('mid').alias('cm')).join(
        at.filter(pl.col('right') == 'PUT').select('m', 'strike', pl.col('mid').alias('pm')), on=['m', 'strike'])
    pairs = pairs.join(ent.select(pl.col('entry_minute').alias('m'), 'spot_entry'), on='m').with_columns((pl.col('strike') - pl.col('spot_entry')).abs().alias('dist'))
    atm = pairs.sort('m', 'dist', 'strike').group_by('m', maintain_order=True).first().select(
        pl.col('m').alias('entry_minute'), pl.col('strike').alias('atm_strike'), (pl.col('cm') + pl.col('pm')).alias('straddle_entry'))
    feats = ent.join(atm, on='entry_minute', how='left').with_columns(
        pl.lit(d).alias('session'), pl.lit(float(sp['px'][0])).alias('spot_open'), pl.lit(float(sp['px'][-1])).alias('spot_close'),
        pl.lit(half_day).alias('half_day'), pl.lit(close_m).alias('close_minute'))

    # every trade, followed to each exit
    e = q.filter((pl.col('ask') > 0) & pl.col('m').is_in(ents)).rename({'m': 'entry_minute', 'bid': 'entry_bid', 'ask': 'entry_ask'})
    k = ['strike', 'right', 'entry_minute']
    j = e.select(k + ['entry_ask']).join(q.select('strike', 'right', 'm', 'bid'), on=['strike', 'right']).filter(pl.col('m') > pl.col('entry_minute'))
    j = j.sort(k + ['m']).with_columns(
        (pl.col('m') <= close_m - 30).alias('c30'), (pl.col('m') <= close_m - 10).alias('c10'),
        (pl.col('m') <= pl.col('entry_minute') + 30).alias('h30'), (pl.col('m') <= pl.col('entry_minute') + 60).alias('h60'),
        (pl.col('m') <= pl.col('entry_minute') + 120).alias('h120'))
    aggs = [pl.len().alias('quotes_after'), pl.col('bid').max().alias('max_bid'), pl.col('bid').last().alias('last_bid')]
    aggs += [pl.col('m').filter(pl.col('bid') >= x * pl.col('entry_ask') - EPS).first().alias(n) for n, x in TARGETS.items()]
    for n, x in STOPS.items():
        down = pl.col('bid') <= x * pl.col('entry_ask') + EPS
        aggs += [pl.col('m').filter(down).first().alias(n), pl.col('bid').filter(down).first().alias(n + '_bid')]
    # a time exit only exists when that minute is after the entry and still before the close
    aggs += [pl.col('bid').filter(pl.col(w)).last().alias(w + '_bid') for w in ('c30', 'c10')]
    aggs += [pl.col('bid').filter(pl.col(w)).last().alias(w + '_bid') for w in ('h30', 'h60', 'h120')]
    a = j.group_by(k, maintain_order=True).agg(aggs)
    r = e.join(a, on=k, how='left').with_columns(pl.lit(d).alias('session'), pl.col('quotes_after').fill_null(0))
    # time exits that fall at or before the entry, or after the close, do not exist
    r = r.with_columns(
        *[pl.when(pl.col('entry_minute') < close_m - n).then(pl.col(f'c{n}_bid')).otherwise(None).alias(f'c{n}_bid') for n in (30, 10)],
        *[pl.when(pl.col('entry_minute') + n <= close_m).then(pl.col(f'h{n}_bid')).otherwise(None).alias(f'h{n}_bid') for n in (30, 60, 120)])
    cols = ['session', 'strike', 'right', 'entry_minute', 'entry_bid', 'entry_ask', 'quotes_after', 'max_bid', 'last_bid'] + list(TARGETS) + \
           [x for n in STOPS for x in (n, n + '_bid')] + ['c30_bid', 'c10_bid', 'h30_bid', 'h60_bid', 'h120_bid']
    return r.select(cols), feats

def run_product(root):
    days = sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        out = pool.starmap(session, [(root, dt.date.fromisoformat(d)) for d in days], chunksize=8)
    P = pl.concat([o[0] for o in out], how='vertical_relaxed').sort('session', 'entry_minute', 'right', 'strike')
    F = pl.concat([o[1] for o in out], how='vertical_relaxed').sort('session', 'entry_minute')
    # the session before: its close and its range (the first session has none)
    day = F.group_by('session').agg(pl.col('spot_open').first(), pl.col('spot_close').first(), pl.col('high_so_far').max().alias('h'), pl.col('low_so_far').min().alias('l')).sort('session')
    # high and low so far at the last entry are not the whole day; the day's own high and low come from step 1
    s1 = pl.read_parquet(os.path.join(ROOT, 'step1', 'out', f'contracts_{root}.parquet'), columns=['session', 'spot_high', 'spot_low']).unique('session')
    day = day.drop('h', 'l').join(s1, on='session').sort('session').with_columns(
        pl.col('spot_close').shift(1).alias('prior_close'), ((pl.col('spot_high') - pl.col('spot_low')) / pl.col('spot_open')).shift(1).alias('prior_range'))
    F = F.join(day.select('session', 'prior_close', 'prior_range'), on='session').with_columns(
        (pl.col('spot_open') / pl.col('prior_close') - 1).alias('gap'),
        (pl.col('spot_entry') / pl.col('spot_open') - 1).alias('move'),
        ((pl.col('high_so_far') - pl.col('low_so_far')) / pl.col('spot_open')).alias('range_so_far'),
        (pl.col('straddle_entry') / pl.col('spot_entry')).alias('implied_move'))
    P.write_parquet(os.path.join(OUT, f'paths_{root}.parquet'), compression='zstd', compression_level=19)
    F.write_parquet(os.path.join(OUT, f'features_{root}.parquet'), compression='zstd', compression_level=19)
    print(root, 'sessions', len(days), 'trades', P.height, flush=True)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(260)
        p, f = session(sys.argv[1], dt.date.fromisoformat(sys.argv[2]))
        print(f); print(p.filter(pl.col('entry_minute') == 30).sort((pl.col('entry_ask') - 1.5).abs()).head(6))
    else:
        for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): run_product(r)
