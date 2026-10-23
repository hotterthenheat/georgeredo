"""Step 6 check 2: no look-ahead. For sampled sessions, build.py's whole per-session build is run again once per buy time,
with every raw file the build reads cut at that buy minute: chain quotes and SPX / VIX prints stamped after it removed,
ETF bars that had not closed by it removed (a bar stamped t closes at t+1), UW spot-exposure rows stamped after it
removed. The gamma flip comes from the session before's file (read whole: it was written after that session's close).
Every buy-minute feature (step 5's raw columns, the derived 39 + 9 context features of data.FEATURES, and the inputs
behind them) must come out identical to the full build's. Outcomes are not compared (they need what comes after).
  python3 -I step6/lookahead.py [sessions per product]
"""
import datetime as dt, os, random, sys
import numpy as np, polars as pl
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import step6.build as bld                       # noqa: E402
from step6.data import step5_derived, FEATURES  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
random.seed(20261023)
RAWCOLS = ['open_ask', 'hi_before', 'low_minute', 'bid_size', 'ask_size', 'ask_1', 'ask_5', 'ask_15', 'px', 'hi_so_far', 'lo_so_far', 'px_1', 'px_5',
           'px_15', 'px_30', 'hi_5', 'lo_5', 'rv15', 'vix', 'vix_open', 'vix_15', 'straddle', 'straddle_open', 'spot_open', 'low_before', 'fwd_entry',
           'iv_entry', 'vwap', 'vwap_side', 'vwap_im', 'or30_im', 'or_state', 'uw_gamma', 'uw_regime', 'flip_prior', 'flip_im', 'event', 'hi_e', 'lo_e']
_read = pl.read_parquet
CUT = {'reads': 0, 'dropped': 0}
CONTROL = ['day_hi', 'day_lo', 'day_close', 'peak_1530', 'mult_1530']   # after-the-fact: these must differ

def cut_read(path, *a, **k):
    df = _read(path, *a, **k)
    p = str(path); c = CUT.get('at')
    if c is None: return df
    if '/data_full/chains/' in p or '/data/index/' in p:
        x = df.filter(pl.col('timestamp') <= c)
    elif '/data/underlying/' in p:
        x = df.filter(pl.col('timestamp') <= c - dt.timedelta(minutes=1))
    elif '/spot_exposures/' in p:
        x = df.filter(pl.col('time') <= c.astimezone(dt.timezone.utc))
    else:
        return df
    CUT['reads'] += 1; CUT['dropped'] += df.height - x.height
    return x

def same(a, b):
    if a is None or b is None or (isinstance(a, float) and a != a) or (isinstance(b, float) and b != b):
        na = a is None or (isinstance(a, float) and a != a); nb = b is None or (isinstance(b, float) and b != b)
        return na == nb
    if isinstance(a, str) or isinstance(b, str): return a == b
    return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)))

def main():
    pl.read_parquet = cut_read
    cal = sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(os.path.join(bld.RAW, 'data', 'underlying', 'SPY')) if f.endswith('.parquet'))
    cprev = {b: a for a, b in zip(cal[:-1], cal[1:])}
    bad = checked = values = ctrl = 0
    for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        CUT['at'] = None
        E, _ = bld.population(root)
        full = _read(os.path.join(bld.WORK, f'trades_{root}.parquet'))
        days = sorted(set(E['session'].to_list()))
        # half the sessions from the UW-covered span, so the UW features are tested too
        uw = [d for d in days if d >= dt.date(2023, 12, 8)]
        pick = random.sample(uw, N // 2) + random.sample(days, N - N // 2)
        for d in pick:
            T = E.filter(pl.col('session') == d)
            for e in sorted(set(T['entry_minute'].to_list())):
                Te = T.filter(pl.col('entry_minute') == e)
                CUT['at'] = (dt.datetime.combine(d, dt.time(9, 30)) + dt.timedelta(minutes=int(e))).replace(tzinfo=ZoneInfo('America/New_York'))
                cutx = bld.session(root, d, Te, cprev.get(d))
                CUT['at'] = None
                ref = full.filter((pl.col('session') == d) & (pl.col('entry_minute') == e))
                a = step5_derived(cutx.with_columns((pl.col('gap') * 100).abs().alias('gap_abs'))).sort('right', 'strike')
                b = step5_derived(ref.with_columns((pl.col('gap') * 100).abs().alias('gap_abs'))).sort('right', 'strike')
                if a.height != b.height: bad += 1; print('ROWS', root, d, e, a.height, b.height); continue
                for col in RAWCOLS + FEATURES:
                    for x, y in zip(a[col].to_list(), b[col].to_list()):
                        values += 1
                        if not same(x, y): bad += 1; print('DIFF', root, d, e, col, x, y)
                for col in CONTROL:
                    ctrl += sum(not same(x, y) for x, y in zip(a[col].to_list(), b[col].to_list()))
                checked += a.height
    print(f'no look-ahead: {checked} trades on {4 * N} sessions rebuilt with every raw file cut at the buy minute; '
          f'{values} feature values compared, {bad} differences. The cut was real: {CUT["reads"]} raw reads cut, {CUT["dropped"]:,} rows removed; '
          f'the after-the-fact control columns {CONTROL} differed in {ctrl} of {checked * len(CONTROL)} values')
    if bad or ctrl == 0 or CUT['dropped'] == 0: raise SystemExit(1)

if __name__ == '__main__':
    main()
