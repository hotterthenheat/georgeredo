"""One session's option chain as dense arrays, and the underlying path on the same minute grid.

Grid: minute m = minutes after 09:30 New York, 0 … 390 (0 … 210 on a 13:00 close). A chain row stamped T is the NBBO at
the instant T, so bid[c, m] is the quote at 09:30 + m. The underlying's price at the instant 09:30 + m is the close of
the 1-minute bar stamped 09:30 + m - 1 (a bar stamped t closes at t + 1); at m = 0 it is the first bar's open. An index
(SPX) row stamped T is its value at T. The settlement value of a same-day contract is the price at the close instant.

Missing quotes stay NaN: a fill reads only a two-sided quote at its minute (or the next, per the protocol), a mark may
carry the last two-sided quote forward (`marks`)."""
from __future__ import annotations
import datetime as dt, os
from dataclasses import dataclass, field
import numpy as np
import polars as pl
from . import paths
import sys
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import calendar as cal  # noqa: E402

@dataclass
class ChainDay:
    root: str
    session: dt.date
    expiration: dt.date
    n_min: int                      # minutes on the grid (391 or 211)
    strike: np.ndarray              # [C]
    is_call: np.ndarray             # [C] bool
    bid: np.ndarray                 # [C, M] float64, NaN missing
    ask: np.ndarray
    bid_size: np.ndarray            # [C, M] int32
    ask_size: np.ndarray
    spot: np.ndarray                # [M] underlying at the instant 09:30 + m
    spot_hi: np.ndarray             # [M] high of the bar ending at m (NaN at 0)
    spot_lo: np.ndarray
    meta: dict = field(default_factory=dict)

    def contract(self, strike: float, call: bool) -> int:
        idx = np.where((np.abs(self.strike - strike) < 1e-6) & (self.is_call == call))[0]
        return int(idx[0]) if idx.size else -1

    def two_sided(self) -> np.ndarray:
        return np.isfinite(self.bid) & np.isfinite(self.ask) & (self.ask > 0) & (self.ask >= self.bid)

    def marks(self) -> np.ndarray:
        """Mid with the last two-sided quote carried forward along the session (NaN before the first)."""
        mid = np.where(self.two_sided(), (self.bid + self.ask) / 2.0, np.nan)
        out = mid.copy()
        for m in range(1, out.shape[1]):
            nan = np.isnan(out[:, m]); out[nan, m] = out[nan, m - 1]
        return out

def _grid_index(ts: pl.Series, session: dt.date) -> np.ndarray:
    open_ = dt.datetime.combine(session, dt.time(9, 30))
    t = ts.dt.replace_time_zone(None).cast(pl.Datetime('ms')).to_numpy().astype('datetime64[m]')
    return (t - np.datetime64(open_, 'm')).astype(int)

def underlying_path(root: str, session: dt.date, n_min: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sym = {'SPXW': 'SPX'}.get(root, root)
    if sym in ('SPX', 'VIX'):
        f = f'{paths.INDEX}/{sym}/{session}.parquet'
        df = pl.read_parquet(f)
        m = _grid_index(df['timestamp'], session); p = df['price'].to_numpy().astype(float)
        spot = np.full(n_min, np.nan); ok = (m >= 0) & (m < n_min); spot[m[ok]] = p[ok]
        if np.isnan(spot[0]): spot[0] = spot[1] if n_min > 1 else np.nan
        hi = np.full(n_min, np.nan); lo = np.full(n_min, np.nan)
        hi[1:] = np.fmax(spot[1:], spot[:-1]); lo[1:] = np.fmin(spot[1:], spot[:-1])
        return _ffill(spot), hi, lo
    f = f'{paths.UNDERLYING}/{sym}/{session}.parquet'
    df = pl.read_parquet(f)
    m = _grid_index(df['timestamp'], session)
    o = df['open'].to_numpy().astype(float); c = df['close'].to_numpy().astype(float)
    h = df['high'].to_numpy().astype(float); l = df['low'].to_numpy().astype(float)
    spot = np.full(n_min, np.nan); hi = np.full(n_min, np.nan); lo = np.full(n_min, np.nan)
    for i in range(m.size):
        k = m[i] + 1                      # the bar stamped m closes at the instant m + 1
        if 1 <= k < n_min and np.isfinite(c[i]): spot[k] = c[i]; hi[k] = h[i]; lo[k] = l[i]
        if m[i] == 0 and np.isfinite(o[i]): spot[0] = o[i]
    return _ffill(spot), hi, lo

def _ffill(a: np.ndarray) -> np.ndarray:
    out = a.copy()
    for i in range(1, out.size):
        if np.isnan(out[i]): out[i] = out[i - 1]
    return out

def load_0dte(root: str, session: dt.date) -> ChainDay | None:
    f = f'{paths.CHAINS_0DTE}/{root}/{session}.parquet'
    if not os.path.exists(f): return None
    n_min = 211 if cal.is_early_close(session) else 391
    df = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
    df = df.with_columns(pl.col('right').cast(pl.Utf8).str.to_uppercase().str.slice(0, 1).alias('right'))
    keys = df.select(['strike', 'right']).unique().sort(['right', 'strike'])
    keys = keys.with_row_index('cid')
    df = df.join(keys, on=['strike', 'right'], how='left')
    m = _grid_index(df['timestamp'], session)
    ok = (m >= 0) & (m < n_min)
    cid = df['cid'].to_numpy()[ok]; mm = m[ok]
    C = keys.height
    bid = np.full((C, n_min), np.nan); ask = np.full((C, n_min), np.nan)
    bsz = np.zeros((C, n_min), np.int32); asz = np.zeros((C, n_min), np.int32)
    b = df['bid'].to_numpy()[ok].astype(float); a = df['ask'].to_numpy()[ok].astype(float)
    bid[cid, mm] = b; ask[cid, mm] = a
    bsz[cid, mm] = df['bid_size'].fill_null(0).to_numpy()[ok]; asz[cid, mm] = df['ask_size'].fill_null(0).to_numpy()[ok]
    spot, hi, lo = underlying_path(root, session, n_min)
    return ChainDay(root=root, session=session, expiration=session, n_min=n_min,
                    strike=keys['strike'].to_numpy().astype(float), is_call=(keys['right'].to_numpy() == 'C'),
                    bid=bid, ask=ask, bid_size=bsz, ask_size=asz, spot=spot, spot_hi=hi, spot_lo=lo,
                    meta={'source': f, 'am_settled': False})

def sessions_0dte(root: str) -> list[dt.date]:
    d = f'{paths.CHAINS_0DTE}/{root}'
    return sorted(dt.date.fromisoformat(x[:10]) for x in os.listdir(d) if x.endswith('.parquet'))
