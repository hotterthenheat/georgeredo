"""
daily.py — one row a trading day per underlying, read from the stored 1-minute bars (SPX: its prints): the 15:59 close,
the regular high and low (bars stamped 09:30–15:59), and the opening-range high and low (bars 09:30–09:59). Cached in
$SP/features_work/daily/<U>.parquet. RV20 (prereg ES2/ES3) and the prior-day structure (D7) are read off this table.

  python3 -I daily.py SPY IWM SPXW AAPL ...
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402


def build(u: str) -> pl.DataFrame:
    rows = []
    for d in C.trading_days():
        if u in C.SINGLES and d < '2017-06-01':
            continue
        b = C.bars(u, d)
        if b is None:
            continue
        h, l, c = b
        reg_h, reg_l = h[0:390], l[0:390]
        rows.append(dict(day=d, close1559=float(c[389]) if np.isfinite(c[389]) else None,
                         high=float(np.nanmax(reg_h)) if np.isfinite(reg_h).any() else None,
                         low=float(np.nanmin(reg_l)) if np.isfinite(reg_l).any() else None,
                         or_high=float(np.nanmax(h[0:30])) if np.isfinite(h[0:30]).any() else None,
                         or_low=float(np.nanmin(l[0:30])) if np.isfinite(l[0:30]).any() else None,
                         n_bars=int(np.isfinite(c[0:390]).sum())))
        C.bars.cache_clear() if len(rows) % 500 == 0 else None
    return pl.DataFrame(rows, schema={'day': pl.String, 'close1559': pl.Float64, 'high': pl.Float64, 'low': pl.Float64,
                                      'or_high': pl.Float64, 'or_low': pl.Float64, 'n_bars': pl.Int64})


def path(u: str) -> Path:
    return C.WORK / 'daily' / f'{u}.parquet'


_cache: dict[str, dict] = {}


def table(u: str) -> dict:
    """day → row dict, plus the RV20 series over full sessions"""
    C.guard_ticker(u)
    if u in _cache:
        return _cache[u]
    p = path(u)
    if not p.exists():
        C.write_parquet(build(u), p)
    df = pl.read_parquet(p)
    rows = {r['day']: r for r in df.iter_rows(named=True)}
    full = [d for d in C.sessions() if d in rows and rows[d]['close1559'] is not None]
    lr = {}
    for a, b in zip(full[:-1], full[1:]):
        lr[b] = math.log(rows[b]['close1559'] / rows[a]['close1559'])
    _cache[u] = dict(rows=rows, full=full, logret=lr)
    return _cache[u]


def rv20_through(u: str, d: str) -> float:
    """the standard deviation (ddof 1) of the last 20 daily log returns of the 15:59 close, over full sessions, through d
    (d itself included when it is a full session with a 15:59 close). NaN without 20 returns."""
    t = table(u)
    full = t['full']
    import bisect
    i = bisect.bisect_right(full, d)          # sessions ≤ d
    if i < 21:
        return float('nan')
    days = full[i - 20:i]
    # the 20 returns must be consecutive full sessions in the bars (no session missing between them)
    si = C.session_index()
    if any(x not in si for x in days):
        return float('nan')
    if si[days[-1]] - si[full[i - 21]] != 20:
        return float('nan')
    r = [t['logret'].get(x) for x in days]
    if any(v is None for v in r):
        return float('nan')
    return float(np.std(r, ddof=1))


def prior_hl(u: str, d: str):
    """the prior trading day's regular high and low (bars 09:30–15:59)"""
    p = C.prev_tday(d)
    r = table(u)['rows'].get(p) if p else None
    if not r or r['high'] is None:
        return float('nan'), float('nan')
    return float(r['high']), float(r['low'])


if __name__ == '__main__':
    C.set_split('hold' if '--hold' in sys.argv else 'expl')
    for u in [a for a in sys.argv[1:] if not a.startswith('--')]:
        df = build(u)
        C.write_parquet(df, path(u))
        print(u, df.height, df['day'].min(), df['day'].max(), int(df['close1559'].is_null().sum()), flush=True)
