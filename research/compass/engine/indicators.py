"""Indicators with the Slayer Terminal conventions (3abida/src/data/indicators.ts), on numpy arrays.

- ema: seeded at the first close (not SMA-seeded), k = 2/(period+1); warm-up = period bars before a value is 'settled'.
- rsi: Wilder; NaN through index `period`-1, the first value ON the bar that completes the seed window; 100 when no
  losses, 0 when no gains, 50 when neither.
- session VWAP on typical price (H+L+C)/3, cumulative within a session, close when the session has no volume yet.
- atr: Wilder, NaN through the seed window.
- relative volume: cumulative session volume at minute m divided by the median cumulative volume at the same minute over
  the prior N sessions (same-minute matching; the brief's 'comparable times of day').
- swings/structure: 3-bar pivots; HH/HL (bull), LH/LL (bear) from the last two swing highs and lows.
All functions are pure and vectorised; NaN marks 'not computable yet', never zero.
"""
from __future__ import annotations
import numpy as np

def ema(close: np.ndarray, period: int) -> np.ndarray:
    close = np.asarray(close, dtype=float)
    out = np.empty_like(close)
    if close.size == 0: return out
    k = 2.0 / (period + 1)
    e = close[0]
    for i, c in enumerate(close):
        e = c * k + e * (1 - k)
        out[i] = e
    return out

def ema_warmup(period: int) -> int:
    return period

def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    close = np.asarray(close, dtype=float)
    n = close.size
    out = np.full(n, np.nan)
    if period < 1 or n <= period: return out
    ch = np.diff(close)
    g = np.maximum(ch[:period], 0).sum() / period
    l = np.maximum(-ch[:period], 0).sum() / period
    def val(g, l):
        if l == 0: return 50.0 if g == 0 else 100.0
        return 100.0 - 100.0 / (1.0 + g / l)
    out[period] = val(g, l)
    for i in range(period + 1, n):
        c = ch[i - 1]
        g = (g * (period - 1) + max(c, 0.0)) / period
        l = (l * (period - 1) + max(-c, 0.0)) / period
        out[i] = val(g, l)
    return out

def session_starts(session_id: np.ndarray) -> np.ndarray:
    """Indices where a new session begins, given a per-bar session identifier (date ordinal or string)."""
    session_id = np.asarray(session_id)
    if session_id.size == 0: return np.zeros(0, dtype=int)
    starts = np.flatnonzero(np.concatenate(([True], session_id[1:] != session_id[:-1])))
    return starts

def session_vwap(high, low, close, volume, session_id) -> np.ndarray:
    high = np.asarray(high, float); low = np.asarray(low, float); close = np.asarray(close, float); volume = np.asarray(volume, float)
    typ = (high + low + close) / 3.0
    out = np.empty_like(close)
    starts = set(session_starts(session_id).tolist())
    pv = 0.0; v = 0.0
    for i in range(close.size):
        if i in starts: pv = 0.0; v = 0.0
        pv += typ[i] * volume[i]; v += volume[i]
        out[i] = pv / v if v > 0 else close[i]
    return out

def session_vwap_sigma(high, low, close, volume, session_id) -> np.ndarray:
    high = np.asarray(high, float); low = np.asarray(low, float); close = np.asarray(close, float); volume = np.asarray(volume, float)
    typ = (high + low + close) / 3.0
    out = np.full(close.size, np.nan)
    starts = set(session_starts(session_id).tolist())
    v = 0.0; pv = 0.0; p2v = 0.0
    for i in range(close.size):
        if i in starts: v = pv = p2v = 0.0
        v += volume[i]; pv += typ[i] * volume[i]; p2v += typ[i] * typ[i] * volume[i]
        if v > 0:
            m = pv / v
            out[i] = np.sqrt(max(0.0, p2v / v - m * m))
    return out

def atr(high, low, close, period: int = 14) -> np.ndarray:
    high = np.asarray(high, float); low = np.asarray(low, float); close = np.asarray(close, float)
    n = close.size
    out = np.full(n, np.nan)
    if period < 1 or n <= period: return out
    tr = np.empty(n); tr[0] = high[0] - low[0]
    tr[1:] = np.maximum.reduce([high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])])
    a = tr[1:period + 1].mean()
    out[period] = a
    for i in range(period + 1, n):
        a = (a * (period - 1) + tr[i]) / period
        out[i] = a
    return out

def cumulative_session_volume(volume, session_id) -> np.ndarray:
    volume = np.asarray(volume, float)
    out = np.empty_like(volume)
    starts = set(session_starts(session_id).tolist())
    c = 0.0
    for i in range(volume.size):
        if i in starts: c = 0.0
        c += volume[i]; out[i] = c
    return out

def relative_volume(cum_volume: np.ndarray, minute_of_session: np.ndarray, session_id: np.ndarray, lookback: int = 20) -> np.ndarray:
    """cum_volume[i] / median over the prior `lookback` sessions of cum_volume at the same minute_of_session.
    NaN until `lookback` prior sessions exist. Sessions are compared by minute index (0 = first bar of the session), so a
    half day's minutes compare with the same clock minutes on full days."""
    cum_volume = np.asarray(cum_volume, float); minute_of_session = np.asarray(minute_of_session, int); session_id = np.asarray(session_id)
    n = cum_volume.size
    out = np.full(n, np.nan)
    starts = session_starts(session_id).tolist() + [n]
    nsess = len(starts) - 1
    # per-session arrays indexed by minute
    maxm = int(minute_of_session.max()) + 1 if n else 0
    table = np.full((nsess, maxm), np.nan)
    for s in range(nsess):
        a, b = starts[s], starts[s + 1]
        table[s, minute_of_session[a:b]] = cum_volume[a:b]
    for s in range(lookback, nsess):
        a, b = starts[s], starts[s + 1]
        ref = np.nanmedian(table[s - lookback:s], axis=0)
        m = minute_of_session[a:b]
        denom = ref[m]
        with np.errstate(invalid='ignore', divide='ignore'):
            out[a:b] = np.where(denom > 0, cum_volume[a:b] / denom, np.nan)
    return out

def pivots(high: np.ndarray, low: np.ndarray, left: int = 3, right: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Swing highs/lows: bar i is a swing high if high[i] is the strict maximum of high[i-left:i+right+1]; the swing is
    KNOWN only at bar i+right (returned as confirm index). Returns (swing_high_idx, swing_low_idx) arrays of bar indices."""
    high = np.asarray(high, float); low = np.asarray(low, float)
    n = high.size
    sh, sl = [], []
    for i in range(left, n - right):
        w = slice(i - left, i + right + 1)
        if high[i] == high[w].max() and (high[w] == high[i]).sum() == 1: sh.append(i)
        if low[i] == low[w].min() and (low[w] == low[i]).sum() == 1: sl.append(i)
    return np.array(sh, dtype=int), np.array(sl, dtype=int)

def structure_state(high: np.ndarray, low: np.ndarray, left: int = 3, right: int = 3) -> np.ndarray:
    """Per bar: +1 when the last two CONFIRMED swing highs and lows make higher highs and higher lows, -1 for lower highs
    and lower lows, 0 otherwise/unknown. A swing is confirmed `right` bars after its pivot, so no look-ahead."""
    high = np.asarray(high, float); low = np.asarray(low, float)
    n = high.size
    sh, sl = pivots(high, low, left, right)
    out = np.zeros(n, dtype=int)
    hi_list: list[float] = []; lo_list: list[float] = []
    hi_i = 0; lo_i = 0
    for i in range(n):
        while hi_i < sh.size and sh[hi_i] + right <= i: hi_list.append(high[sh[hi_i]]); hi_i += 1
        while lo_i < sl.size and sl[lo_i] + right <= i: lo_list.append(low[sl[lo_i]]); lo_i += 1
        if len(hi_list) >= 2 and len(lo_list) >= 2:
            if hi_list[-1] > hi_list[-2] and lo_list[-1] > lo_list[-2]: out[i] = 1
            elif hi_list[-1] < hi_list[-2] and lo_list[-1] < lo_list[-2]: out[i] = -1
    return out

def last_swing_levels(high: np.ndarray, low: np.ndarray, left: int = 3, right: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Per bar: the most recent confirmed swing high and swing low (NaN before one exists)."""
    high = np.asarray(high, float); low = np.asarray(low, float)
    n = high.size
    sh, sl = pivots(high, low, left, right)
    oh = np.full(n, np.nan); ol = np.full(n, np.nan)
    hi_i = lo_i = 0; ch = np.nan; cl = np.nan
    for i in range(n):
        while hi_i < sh.size and sh[hi_i] + right <= i: ch = high[sh[hi_i]]; hi_i += 1
        while lo_i < sl.size and sl[lo_i] + right <= i: cl = low[sl[lo_i]]; lo_i += 1
        oh[i] = ch; ol[i] = cl
    return oh, ol
