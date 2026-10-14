"""ThetaData fetching with on-disk caching, in the layouts the CacheStore reads (research/compass/04_protocol.md §2, §11).

One live login per key: the fetcher refuses to start while the all-symbol stock EOD job (bulk_fetch.py) is running, and
every worker thread shares one client (re-login on UNAUTHENTICATED). Raw vendor frames are normalised to the dataset's
column conventions (timestamp America/New_York ms; right CALL/PUT; strike float) and written once per (root, session,
expiration); existing files are never rewritten; a `.nodata` marker records a session the vendor has nothing for. Key from
THETADATA_KEY only; exceptions are redacted before logging.

Layout under CACHE:
  underlying/{symbol}/{date}.parquet                timestamp, open, high, low, close, volume, count, vwap   (1-minute, 09:30-16:00)
  chains_exp/{root}/{date}__{expiration}.parquet     timestamp, strike, right, bid, ask, bid_size, ask_size, mid (1-minute NBBO, every strike)
  ohlc_exp/{root}/{date}__{expiration}.parquet       timestamp, strike, right, open, high, low, close, volume, count, vwap
  oi/{root}/{date}__{expiration}.parquet             strike, right, open_interest (as reported for that date)
"""
from __future__ import annotations
import datetime as dt
import os, re, subprocess, threading, time, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl

CHAIN_COLS = ['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size', 'mid']
OHLC_COLS = ['timestamp', 'strike', 'right', 'open', 'high', 'low', 'close', 'volume', 'count', 'vwap']
STOCK_COLS = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'count', 'vwap']

def _red(s: str) -> str:
    s = re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
    k = os.environ.get('THETADATA_KEY')
    return s.replace(k, 'REDACTED') if k else s

def bulk_job_running() -> bool:
    try:
        out = subprocess.run(['ps', '-eo', 'args'], capture_output=True, text=True).stdout
        return any(line.startswith('python3 -I bulk_fetch.py') or 'bulk_fetch.py' in line and 'python3' in line for line in out.splitlines())
    except Exception:
        return False

def norm_ts(df: pl.DataFrame, col: str = 'timestamp') -> pl.DataFrame:
    if df.schema[col] == pl.Utf8:
        df = df.with_columns(pl.col(col).str.to_datetime(strict=False))
    tz = getattr(df.schema[col], 'time_zone', None)
    if tz is None: df = df.with_columns(pl.col(col).dt.replace_time_zone('America/New_York'))
    else: df = df.with_columns(pl.col(col).dt.convert_time_zone('America/New_York'))
    return df.with_columns(pl.col(col).dt.cast_time_unit('ms'))

class ThetaFetcher:
    def __init__(self, cache: str, nw: int = 8, log=print, allow_with_bulk_job: bool = False):
        if bulk_job_running() and not allow_with_bulk_job:
            raise RuntimeError('bulk_fetch.py is running: one live ThetaData login per key — pause it first')
        self.cache = cache; self.nw = nw; self.log = log
        self._lock = threading.Lock(); self._client = None; self._gen = 0
        self.stats = {'ok': 0, 'nodata': 0, 'error': 0, 'skipped': 0}

    def client(self, seen: int | None = None):
        from thetadata import ThetaClient
        with self._lock:
            if self._client is None or (seen is not None and seen == self._gen):
                self._client = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars'); self._gen += 1
                self.log(f'theta login gen {self._gen}')
            return self._client, self._gen

    def call(self, fn: str, **kw):
        import grpc
        from thetadata.errors import NoDataFoundError
        for attempt in range(6):
            c, g = self.client()
            try: return getattr(c, fn)(**kw), None
            except NoDataFoundError: return None, 'nodata'
            except grpc.RpcError as e:
                code = e.code()
                if code == grpc.StatusCode.UNAUTHENTICATED: self.client(g); continue
                if code in (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.INTERNAL, grpc.StatusCode.UNKNOWN): time.sleep(2 + 3 * attempt); continue
                return None, f'{code} {_red(e.details())[:160]}'
            except Exception as e: return None, f'{type(e).__name__} {_red(e)[:160]}'
        return None, 'retries exhausted'

    # ---- paths ----
    def _p(self, kind: str, root: str, session: dt.date, expiration: dt.date | None = None) -> str:
        name = f'{session}__{expiration}.parquet' if expiration else f'{session}.parquet'
        return os.path.join(self.cache, kind, root, name)

    @staticmethod
    def _write(df: pl.DataFrame, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'; df.write_parquet(tmp, compression='zstd'); os.replace(tmp, path)

    @staticmethod
    def _mark(path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True); open(path[:-8] + '.nodata', 'w').close()

    @staticmethod
    def _done(path: str) -> bool:
        return os.path.exists(path) or os.path.exists(path[:-8] + '.nodata')

    # ---- one-item fetches (each writes its file) ----
    def chain_quotes(self, root: str, session: dt.date, expiration: dt.date) -> str:
        p = self._p('chains_exp', root, session, expiration)
        if self._done(p): self.stats['skipped'] += 1; return p
        df, err = self.call('option_history_quote', symbol=root, expiration=expiration, interval='1m', date=session, strike='*', right='both')
        return self._finish(df, err, p, CHAIN_COLS, mid=True)

    def chain_ohlc(self, root: str, session: dt.date, expiration: dt.date) -> str:
        p = self._p('ohlc_exp', root, session, expiration)
        if self._done(p): self.stats['skipped'] += 1; return p
        df, err = self.call('option_history_ohlc', symbol=root, expiration=expiration, interval='1m', date=session, strike='*', right='both')
        return self._finish(df, err, p, OHLC_COLS)

    def open_interest(self, root: str, session: dt.date, expiration: dt.date) -> str:
        p = self._p('oi', root, session, expiration)
        if self._done(p): self.stats['skipped'] += 1; return p
        df, err = self.call('option_history_open_interest', symbol=root, expiration=expiration, date=session, strike='*', right='both')
        if df is not None and df.height:
            df = df.select(['strike', 'right', 'open_interest']).with_columns(pl.col('strike').cast(pl.Float64), pl.col('open_interest').cast(pl.Int64))
        return self._finish(df, err, p, None)

    def stock_minutes(self, symbol: str, start: dt.date, end: dt.date) -> list[str]:
        """Month-sized requests, split into per-session files; sessions already on disk are skipped."""
        from .. import calendar as cal
        out = []
        a = start
        while a <= end:
            b = min(end, (a.replace(day=1) + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1))
            sessions = cal.sessions(a, b)
            if all(self._done(self._p('underlying', symbol, d)) for d in sessions): a = b + dt.timedelta(days=1); self.stats['skipped'] += 1; continue
            df, err = self.call('stock_history_ohlc', symbol=symbol, interval='1m', start_date=a, end_date=b)
            if df is None or not df.height:
                for d in sessions: self._mark(self._p('underlying', symbol, d))
                self.stats['nodata' if err == 'nodata' else 'error'] += 1; self.log(f'stock_minutes {symbol} {a}..{b}: {err}')
            else:
                df = norm_ts(df.select([c for c in STOCK_COLS if c in df.columns]))
                for (day,), part in df.group_by([pl.col('timestamp').dt.date()], maintain_order=True):
                    if not cal.is_session(day): continue
                    p = self._p('underlying', symbol, day)
                    if not self._done(p): self._write(part.sort('timestamp'), p); out.append(p)
                for d in sessions:
                    p = self._p('underlying', symbol, d)
                    if not self._done(p): self._mark(p)
                self.stats['ok'] += 1
            a = b + dt.timedelta(days=1)
        return out

    def _finish(self, df, err, path, cols, mid=False) -> str:
        if df is None or not df.height:
            self._mark(path); self.stats['nodata' if err in (None, 'nodata') else 'error'] += 1
            if err not in (None, 'nodata'): self.log(f'{path}: {err}')
            return path
        if cols:
            if mid: df = df.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
            df = df.select([c for c in cols if c in df.columns])
            df = norm_ts(df).with_columns(pl.col('strike').cast(pl.Float64))
            if 'bid_size' in df.columns: df = df.with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32))
            df = df.sort(['strike', 'right', 'timestamp'])
        self._write(df, path); self.stats['ok'] += 1
        return path

    # ---- batches ----
    def run_jobs(self, jobs: list[tuple], label: str = 'jobs') -> dict:
        """jobs: (method_name, args...) tuples run on the thread pool; progress every 200."""
        t0 = time.time(); n = 0
        with ThreadPoolExecutor(self.nw) as ex:
            futs = [ex.submit(getattr(self, j[0]), *j[1:]) for j in jobs]
            for f in as_completed(futs):
                n += 1
                try: f.result()
                except Exception as e: self.stats['error'] += 1; self.log(f'job error {_red(e)[:160]}')
                if n % 200 == 0: self.log(f'{label}: {n}/{len(jobs)} {self.stats} {time.time() - t0:.0f}s')
        self.log(f'{label}: done {len(jobs)} {self.stats} {time.time() - t0:.0f}s')
        return dict(self.stats)
