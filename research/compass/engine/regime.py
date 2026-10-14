"""Regime and event variables for result tables (04_protocol.md §7): event flags (FOMC decision days, CPI and NFP release
days — lists compiled from federalreserve.gov and bls.gov for 2017-02 → 2026-10 in research/thetadata/vol_filters/),
month-end sessions, VIX terciles (ThetaData VIX minute cache, the 09:31 print of the session, terciles over the trailing
252 sessions — point-in-time), and the daily trend state (EMA 20 vs EMA 50 of the symbol's daily closes, previous session).
Sessions before 2017-02 carry no event flags (lists not yet extended) and are reported as 'unknown'."""
from __future__ import annotations
import datetime as dt
import glob, os
import numpy as np
import polars as pl
from . import calendar as cal, indicators as ind

HERE = os.path.dirname(os.path.abspath(__file__))
VOL_FILTERS = os.path.join(HERE, '..', '..', 'thetadata', 'vol_filters')

def event_days() -> dict[dt.date, set[str]]:
    out: dict[dt.date, set[str]] = {}
    for f, col in ((os.path.join(VOL_FILTERS, 'fomc_dates.csv'), 'event'), (os.path.join(VOL_FILTERS, 'events.csv'), 'event')):
        if not os.path.exists(f): continue
        df = pl.read_csv(f)
        for d, e in zip(df['date'].to_list(), df[col].to_list()):
            out.setdefault(dt.date.fromisoformat(str(d)[:10]), set()).add(str(e).upper())
    return out

def is_month_end(d: dt.date) -> bool:
    return cal.next_session(d).month != d.month

def vix_open_series(index_root: str, start: dt.date, end: dt.date) -> pl.DataFrame:
    """Session -> VIX at the 09:31 print (first non-null at/after 09:31)."""
    rows = []
    for f in sorted(glob.glob(os.path.join(index_root, 'VIX', '*.parquet'))):
        d = dt.date.fromisoformat(os.path.basename(f)[:10])
        if d < start or d > end: continue
        df = pl.read_parquet(f).filter(pl.col('price').is_not_null())
        if df.height == 0: continue
        df = df.filter(pl.col('timestamp').dt.replace_time_zone(None) >= dt.datetime.combine(d, dt.time(9, 31)))
        if df.height: rows.append({'session': d, 'vix_open': float(df['price'][0])})
    return pl.DataFrame(rows)

def vix_terciles(vix: pl.DataFrame, lookback: int = 252) -> pl.DataFrame:
    """Point-in-time tercile of today's VIX open within the prior `lookback` sessions' opens (1 = low, 3 = high)."""
    v = vix.sort('session'); x = v['vix_open'].to_numpy(); n = x.size
    terc = np.full(n, 0, dtype=int)
    for i in range(lookback, n):
        ref = x[i - lookback:i]; lo, hi = np.percentile(ref, [100 / 3, 200 / 3])
        terc[i] = 1 if x[i] <= lo else (3 if x[i] > hi else 2)
    return v.with_columns(pl.Series('vix_tercile', terc))

def daily_trend(daily: pl.DataFrame, fast: int = 20, slow: int = 50) -> pl.DataFrame:
    """Per session: +1 if EMA(fast) > EMA(slow) of the PREVIOUS sessions' closes, -1 if below, 0 while warming up."""
    d = daily.sort('session'); c = d['close'].to_numpy()
    ef = ind.ema(c, fast); es = ind.ema(c, slow)
    st = np.where(np.arange(c.size) < slow, 0, np.where(ef > es, 1, -1))
    st = np.concatenate(([0], st[:-1]))  # previous session's state applies to today
    return d.select(['session']).with_columns(pl.Series('trend_state', st))

def annotate(trades: pl.DataFrame, index_root: str | None = None, daily_by_symbol: dict[str, pl.DataFrame] | None = None) -> pl.DataFrame:
    ev = event_days()
    s = trades['session'].to_list()
    def flag(d):
        if d < dt.date(2017, 2, 1): return 'unknown'
        e = ev.get(d, set())
        return 'FOMC' if 'FOMC' in e else ('CPI' if 'CPI' in e else ('NFP' if 'NFP' in e else 'none'))
    out = trades.with_columns([pl.Series('event', [flag(d) for d in s]), pl.Series('month_end', [is_month_end(d) for d in s]), pl.Series('weekday', [d.weekday() for d in s])])
    if index_root:
        vx = vix_open_series(index_root, min(s), max(s))
        if vx.height: out = out.join(vix_terciles(vix_open_series(index_root, dt.date(2017, 1, 1), max(s))).select(['session', 'vix_open', 'vix_tercile']), on='session', how='left')
    if daily_by_symbol:
        parts = [daily_trend(df).with_columns(pl.lit(sym).alias('symbol')) for sym, df in daily_by_symbol.items()]
        out = out.join(pl.concat(parts), on=['symbol', 'session'], how='left')
    return out
