"""Data access for the engine. CacheStore reads the Parquet caches already on disk (underlying minute bars, full-strike
0DTE chains, index minutes, the universe's expirations). A fetching store (ThetaData gRPC with on-disk caching) is added
in data/theta_fetch.py; both expose the same methods so a run never knows which one served it.

Chain frames: one row per (timestamp, strike, right) with bid, ask, bid_size, ask_size; `timestamp` naive New York time
at the minute boundary (the last NBBO at that boundary). Rows with null bid/ask are kept so a dead quote is visible.
"""
from __future__ import annotations
import datetime as dt
import glob, json, os
import polars as pl
from . import bars, calendar as cal

class CacheStore:
    def __init__(self, underlying_root: str, chains_root: str, index_root: str | None = None, expirations_file: str | None = None):
        self.und = underlying_root; self.chains = chains_root; self.idx = index_root
        self._exp: dict[str, list[dt.date]] = {}
        if expirations_file and os.path.exists(expirations_file):
            for line in open(expirations_file):
                try: r = json.loads(line)
                except Exception: continue
                if r.get('expirations'): self._exp[r['root']] = [dt.date.fromisoformat(x) for x in r['expirations']]

    def bars(self, symbol: str, start: dt.date, end: dt.date) -> pl.DataFrame:
        return bars.load_minutes(symbol, self.und, start, end)

    def has_bars(self, symbol: str) -> bool:
        return os.path.isdir(os.path.join(self.und, symbol))

    def index_minutes(self, symbol: str, start: dt.date, end: dt.date) -> pl.DataFrame:
        files = sorted(glob.glob(os.path.join(self.idx or '', symbol, '*.parquet')))
        frames = []
        for f in files:
            d = dt.date.fromisoformat(os.path.basename(f)[:10])
            if d < start or d > end: continue
            frames.append(pl.read_parquet(f).with_columns(pl.lit(d).alias('session')))
        return pl.concat(frames) if frames else pl.DataFrame()

    def expirations(self, root: str) -> list[dt.date]:
        if root in self._exp: return self._exp[root]
        # fall back to the 0DTE cache: every cached session is a listed same-day expiration
        files = sorted(glob.glob(os.path.join(self.chains, root, '*.parquet')))
        return [dt.date.fromisoformat(os.path.basename(f)[:10]) for f in files]

    def chain_minutes(self, root: str, session: dt.date, expiration: dt.date) -> pl.DataFrame | None:
        """Only same-day expirations are in the 0DTE cache; anything else returns None (a fetching store fills it)."""
        if expiration != session: return None
        f = os.path.join(self.chains, root, f'{session}.parquet')
        if not os.path.exists(f): return None
        df = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
        return df.with_columns(pl.col('timestamp').dt.replace_time_zone(None))

    def chain_sessions(self, root: str) -> list[dt.date]:
        return [dt.date.fromisoformat(os.path.basename(f)[:10]) for f in sorted(glob.glob(os.path.join(self.chains, root, '*.parquet')))]

    def open_interest(self, root: str, session: dt.date, expiration: dt.date) -> pl.DataFrame | None:
        return None

    def chain_ohlc(self, root: str, session: dt.date, expiration: dt.date) -> pl.DataFrame | None:
        return None


class FetchStore(CacheStore):
    """CacheStore plus the fetcher's caches (chains_exp/ohlc_exp/oi/underlying under `fetch_cache`), fetching on a miss when
    a ThetaFetcher is attached; without one, misses return None (recorded as no_chain_data by the runner)."""
    def __init__(self, underlying_root: str, chains_root: str, index_root: str | None, expirations_file: str | None, fetch_cache: str, fetcher=None):
        super().__init__(underlying_root, chains_root, index_root, expirations_file)
        self.fc = fetch_cache; self.fetcher = fetcher

    def _read(self, kind: str, root: str, session: dt.date, expiration: dt.date, method: str | None):
        p = os.path.join(self.fc, kind, root, f'{session}__{expiration}.parquet')
        if not os.path.exists(p) and not os.path.exists(p[:-8] + '.nodata') and self.fetcher is not None and method:
            getattr(self.fetcher, method)(root, session, expiration)
        if not os.path.exists(p): return None
        return pl.read_parquet(p)

    def bars(self, symbol: str, start: dt.date, end: dt.date) -> pl.DataFrame:
        a = super().bars(symbol, start, end)
        if a.height: return a
        if self.fetcher is not None and not os.path.isdir(os.path.join(self.fc, 'underlying', symbol)): self.fetcher.stock_minutes(symbol, start, end)
        return bars.load_minutes(symbol, os.path.join(self.fc, 'underlying'), start, end)

    def chain_minutes(self, root: str, session: dt.date, expiration: dt.date) -> pl.DataFrame | None:
        c = super().chain_minutes(root, session, expiration)
        if c is not None: return c
        df = self._read('chains_exp', root, session, expiration, 'chain_quotes')
        if df is None: return None
        return df.select(['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size']).with_columns(pl.col('timestamp').dt.replace_time_zone(None))

    def open_interest(self, root: str, session: dt.date, expiration: dt.date) -> pl.DataFrame | None:
        return self._read('oi', root, session, expiration, 'open_interest')

    def chain_ohlc(self, root: str, session: dt.date, expiration: dt.date) -> pl.DataFrame | None:
        df = self._read('ohlc_exp', root, session, expiration, 'chain_ohlc')
        if df is None: return None
        return df.with_columns(pl.col('timestamp').dt.replace_time_zone(None))
