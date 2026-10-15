"""Per-session decision series on the chain's minute grid: what a policy may read at the instant 09:30 + m.

Every series comes from the underlying's 1-minute feature frame (engine.signals.features, computed over the root's whole
history once, so the indicators carry their warm-up across sessions). The value at instant m is the feature of the bar
that CLOSED at m (the bar stamped m - 1), so nothing after the instant is read.

  rsi     RSI(14) on 1-minute closes
  ema5    EMA(20) on completed 5-minute bars
  atr5    ATR(14) on completed 5-minute bars
  vwap    the session VWAP
  ativ    the at-the-money implied vol of the session's chain (mean of the call and put mid IVs at the strike nearest spot)
"""
from __future__ import annotations
import datetime as dt, os, sys
import numpy as np
import polars as pl
from . import paths
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import bars, indicators as ind, signals, greeks as g, store as st, calendar as cal  # noqa: E402

def make_store():
    return st.IndexProxyStore(paths.UNDERLYING, paths.CHAINS_0DTE, paths.INDEX)

def feature_frame(store, root: str, start: dt.date, end: dt.date, params: dict | None = None) -> pl.DataFrame:
    """The engine's feature frame plus ATR(14) on 5-minute bars, aligned by close time."""
    sym = root
    warm = cal.prev_session(start, 40)
    df1 = store.bars(sym, warm, end)
    p = {**signals.BASELINE, **(params or {})}
    feat = signals.features(df1, p)
    d5 = bars.resample(df1, 5)
    a = bars.with_session_arrays(d5)
    atr5 = ind.atr(a['high'], a['low'], a['close'], 14)
    t5 = d5.select(['close_ts']).with_columns(pl.Series('atr_5m', atr5))
    feat = bars.align_closed(feat, t5, ['atr_5m'], '')
    return feat

def session_series(feat_day: pl.DataFrame, session: dt.date, n_min: int) -> dict[str, np.ndarray]:
    """feat_day: the feature rows of one session. Index each series by the instant its bar closed."""
    open_ = np.datetime64(dt.datetime.combine(session, dt.time(9, 30)), 'm')
    ct = feat_day['close_ts'].dt.replace_time_zone(None).cast(pl.Datetime('ms')).to_numpy().astype('datetime64[m]')
    m = (ct - open_).astype(int)
    ok = (m >= 0) & (m < n_min)
    out = {}
    for name, col in [('rsi', 'rsi'), ('ema5', 'ema_mid_5m'), ('atr5', 'atr_5m'), ('vwap', 'vwap'), ('atr1', 'atr')]:
        a = np.full(n_min, np.nan)
        if col in feat_day.columns:
            a[m[ok]] = feat_day[col].to_numpy().astype(float)[ok]
            for i in range(1, n_min):                     # carry the last closed value between closes (5m series)
                if np.isnan(a[i]): a[i] = a[i - 1]
        out[name] = a
    return out

def atm_iv(cd, r=g.R_DEFAULT, q=g.Q_DEFAULT) -> np.ndarray:
    """ATM IV per minute: the strike nearest spot, call and put mids, mean of the two solved IVs."""
    n = cd.n_min
    close = dt.datetime.combine(cd.expiration, cal.close_time(cd.expiration))
    open_ = dt.datetime.combine(cd.session, dt.time(9, 30))
    tt = np.array([max((close - (open_ + dt.timedelta(minutes=m))).total_seconds(), 60.0) / (365.25 * 86400.0) for m in range(n)])
    K = np.unique(cd.strike)
    out = np.full(n, np.nan)
    calls = {k: i for i, k in enumerate(cd.strike) if cd.is_call[i]}
    puts = {k: i for i, k in enumerate(cd.strike) if not cd.is_call[i]}
    ks = np.array(sorted(set(calls) & set(puts)))
    if ks.size == 0: return out
    S = cd.spot
    idx = np.abs(ks[None, :] - S[:, None]).argmin(axis=1)
    kk = ks[idx]
    ci = np.array([calls[k] for k in kk]); pi = np.array([puts[k] for k in kk])
    mm = np.arange(n)
    cm = (cd.bid[ci, mm] + cd.ask[ci, mm]) / 2; pm = (cd.bid[pi, mm] + cd.ask[pi, mm]) / 2
    ivc = g.implied_vol(cm, S, kk, tt, np.ones(n), r, q); ivp = g.implied_vol(pm, S, kk, tt, -np.ones(n), r, q)
    out = np.nanmean(np.vstack([ivc, ivp]), axis=0)
    return out

def t_years_grid(cd) -> np.ndarray:
    close = dt.datetime.combine(cd.expiration, cal.close_time(cd.expiration))
    open_ = dt.datetime.combine(cd.session, dt.time(9, 30))
    return np.array([max((close - (open_ + dt.timedelta(minutes=m))).total_seconds(), 60.0) / (365.25 * 86400.0) for m in range(cd.n_min)])
