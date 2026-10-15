"""Tier D pull (lifecycle 01_data_inventory.md §3): option EOD — OHLC, volume, trade count and the closing NBBO — for EVERY
expiration of a root, one file per root per calendar week (one request of up to five sessions), plus the underlying's
1-minute bars where the cache lacks them (the daily bars and the next-open prices come from those).

Resumable and idempotent: a week already written (or marked .nodata) is skipped; files are written atomically; every
request is logged to jobs.jsonl with its status, rows and seconds; one login (the fetcher's guard); key from
THETADATA_KEY only. Columns kept: date, expiration, strike, right, open, high, low, close, volume, count, bid, ask,
bid_size, ask_size (float32 prices, int32 sizes).

  python3 -I -m lc.pull_tier_d ROOTS START END [--nw 4]
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import polars as pl
from . import paths
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import calendar as cal  # noqa: E402
from engine.data.theta_fetch import ThetaFetcher, _red  # noqa: E402

OUT = f'{paths.FETCH_CACHE}/eod_all'
KEEP = ['date', 'expiration', 'strike', 'right', 'open', 'high', 'low', 'close', 'volume', 'count', 'bid', 'ask', 'bid_size', 'ask_size']

def weeks(start: dt.date, end: dt.date) -> list[tuple[dt.date, dt.date]]:
    a = start - dt.timedelta(days=start.weekday())
    out = []
    while a <= end:
        b = a + dt.timedelta(days=4)
        s = [d for d in cal.sessions(max(a, start), min(b, end))]
        if s: out.append((s[0], s[-1]))
        a += dt.timedelta(days=7)
    return out

def normalise(df: pl.DataFrame) -> pl.DataFrame:
    cols = df.columns
    if 'date' not in cols:
        tcol = 'created' if 'created' in cols else ('timestamp' if 'timestamp' in cols else None)
        if tcol is None: raise ValueError(f'no date column in {cols}')
        df = df.with_columns(pl.col(tcol).cast(pl.Utf8).str.slice(0, 10).str.to_date().alias('date'))
    df = df.with_columns([pl.col('expiration').cast(pl.Utf8).str.slice(0, 10).str.to_date().alias('expiration'),
                          pl.col('right').cast(pl.Utf8).str.to_uppercase().str.slice(0, 1).alias('right'),
                          pl.col('strike').cast(pl.Float64)])
    out = df.select([c for c in KEEP if c in df.columns])
    f32 = [c for c in ('open', 'high', 'low', 'close', 'bid', 'ask') if c in out.columns]
    i32 = [c for c in ('volume', 'count', 'bid_size', 'ask_size') if c in out.columns]
    return out.with_columns([pl.col(c).cast(pl.Float32) for c in f32] + [pl.col(c).cast(pl.Int64) for c in i32])

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('roots'); ap.add_argument('start'); ap.add_argument('end'); ap.add_argument('--nw', type=int, default=4)
    ap.add_argument('--no-minutes', action='store_true')
    a = ap.parse_args(argv)
    roots = a.roots.split(','); start = dt.date.fromisoformat(a.start); end = dt.date.fromisoformat(a.end)
    os.makedirs(OUT, exist_ok=True)
    lock = threading.Lock(); logf = open(f'{OUT}/jobs.jsonl', 'a')
    def log(msg): print(time.strftime('%H:%M:%S'), _red(msg), flush=True)
    fx = ThetaFetcher(paths.FETCH_CACHE, nw=a.nw, log=log)
    def job(root, w0, w1):
        p = f'{OUT}/{root}/{w0}__{w1}.parquet'
        if os.path.exists(p) or os.path.exists(p[:-8] + '.nodata'): return 'skip', 0
        t0 = time.time()
        df, err = fx.call('option_history_eod', symbol=root, expiration='*', start_date=w0, end_date=w1, strike='*', right='both')
        rec = {'root': root, 'w0': str(w0), 'w1': str(w1), 'secs': round(time.time() - t0, 2)}
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if df is None or df.height == 0:
            if err == 'nodata': open(p[:-8] + '.nodata', 'w').close()
            rec.update(status=err or 'empty', rows=0)
        else:
            try:
                d = normalise(df); tmp = p + '.tmp'; d.write_parquet(tmp, compression='zstd', compression_level=9); os.replace(tmp, p)
                rec.update(status='ok', rows=d.height, bytes=os.path.getsize(p))
            except Exception as e:
                rec.update(status=f'write_error {type(e).__name__} {_red(e)[:120]}', rows=0)
        with lock: logf.write(json.dumps(rec) + '\n'); logf.flush()
        return rec['status'], rec.get('rows', 0)
    for root in roots:
        if not a.no_minutes and root in ('SPY', 'QQQ', 'IWM'):
            # the 1-minute bars before the cached 2017-06 start (daily bars and next opens for the early years)
            und_dir = paths.UNDERLYING
            fx2 = ThetaFetcher(os.path.dirname(und_dir), nw=1, log=log)   # writes underlying/{root}/{date}.parquet under theta/data
            fx2._client = None
            fx2.stock_minutes(root, max(start, dt.date(2012, 6, 1)), min(end, dt.date(2017, 5, 31)))
        ws = weeks(start, end)
        t0 = time.time(); n = 0; rows = 0; stat = {}
        with ThreadPoolExecutor(a.nw) as ex:
            futs = [ex.submit(job, root, w0, w1) for (w0, w1) in ws]
            for f in as_completed(futs):
                s, r = f.result(); n += 1; rows += r; stat[s] = stat.get(s, 0) + 1
                if n % 50 == 0: log(f'{root}: {n}/{len(ws)} weeks {stat} rows {rows} {time.time() - t0:.0f}s')
        log(f'{root}: done {n} weeks {stat} rows {rows} in {time.time() - t0:.0f}s')
    log(f'fetch stats {fx.stats}')

if __name__ == '__main__':
    main()
