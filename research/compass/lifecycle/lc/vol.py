"""Volatility and event setups on the 0DTE chains (lifecycle protocol §3: VOLC, VOLR, EVF and their all-days controls).

Per session at 10:00 (m = 30):
  iv10      the ATM implied vol of the same-day chain (lc.aux.atm_iv)
  ivar10    the implied variance to the close: iv10^2 x calendar years to 16:00
  rv_fc     a HAR forecast of the 10:00-16:00 realized variance (sum of squared 1-minute log returns), fitted by OLS on
            log variances over sessions strictly before the day (expanding, at least 60 sessions, refit every 20), from:
            the prior session's full-day RV, its 5- and 22-session means, and today's 09:30-10:00 RV — all known at 10:00
  ratio     sqrt(rv_fc / ivar10): above 1.25 the option is cheap against the forecast (IV < 0.8 x forecast vol)
  iv_pct    iv10's percentile among the prior 60 sessions' iv10
VOLC: ratio >= 1.25 or iv_pct <= 0.20; VOLR: ratio <= 0.80 or iv_pct >= 0.80. ALL10V / ALL10P: every session at 10:00 (the
controls the flagged days are compared with). EVF: FOMC statement days at 13:30 (m = 240); ALL1330: every other session
at 13:30."""
from __future__ import annotations
import datetime as dt, os
import numpy as np
import polars as pl
from . import paths, chainmat as cm, aux as ax

def _rv(spot: np.ndarray, a: int, b: int) -> float:
    x = spot[a:b + 1]
    x = x[np.isfinite(x) & (x > 0)]
    if x.size < 3: return np.nan
    r = np.diff(np.log(x))
    return float(np.sum(r * r))

def session_table(root: str) -> pl.DataFrame:
    rows = []
    for s in cm.sessions_0dte(root):
        cd = cm.load_0dte(root, s)
        if cd is None: continue
        if cd.n_min < 391: continue                       # half days: no 10:00-16:00 window comparable to the rest
        iv = ax.atm_iv(cd)
        tg = ax.t_years_grid(cd)
        rows.append({'session': s, 'iv10': float(iv[30]), 't10': float(tg[30]), 'rv_day': _rv(cd.spot, 0, cd.n_min - 1),
                     'rv_am': _rv(cd.spot, 0, 30), 'rv_pm': _rv(cd.spot, 30, cd.n_min - 1), 'spot10': float(cd.spot[30]),
                     'spot1330': float(cd.spot[240]), 'n_min': cd.n_min})
    df = pl.DataFrame(rows).sort('session')
    return df.with_columns((pl.col('iv10') ** 2 * pl.col('t10')).alias('ivar10'))

def har_forecast(df: pl.DataFrame, min_train: int = 60, refit: int = 20) -> np.ndarray:
    rv_day = df['rv_day'].to_numpy(); rv_am = df['rv_am'].to_numpy(); y = df['rv_pm'].to_numpy()
    n = df.height
    lag1 = np.r_[np.nan, rv_day[:-1]]
    m5 = pl.Series(lag1).rolling_mean(5).to_numpy(); m22 = pl.Series(lag1).rolling_mean(22).to_numpy()
    X = np.column_stack([np.ones(n), np.log(lag1), np.log(m5), np.log(m22), np.log(rv_am)])
    ly = np.log(y)
    out = np.full(n, np.nan); beta = None; s2 = 0.0; last_fit = -10**9
    for d in range(n):
        if d - last_fit >= refit or beta is None:
            tr = np.arange(d)
            ok = tr[np.all(np.isfinite(X[tr]), axis=1) & np.isfinite(ly[tr])]
            if ok.size >= min_train:
                beta, *_ = np.linalg.lstsq(X[ok], ly[ok], rcond=None)
                res = ly[ok] - X[ok] @ beta; s2 = float(np.var(res)); last_fit = d
        if beta is not None and np.all(np.isfinite(X[d])):
            out[d] = float(np.exp(X[d] @ beta + 0.5 * s2))
    return out

def events(root: str, fomc: set[dt.date]) -> pl.DataFrame:
    df = session_table(root)
    fc = har_forecast(df)
    iv = df['iv10'].to_numpy()
    pct = np.full(df.height, np.nan)
    for i in range(df.height):
        past = iv[max(0, i - 60):i]; past = past[np.isfinite(past)]
        if past.size >= 40 and np.isfinite(iv[i]): pct[i] = float((past < iv[i]).mean())
    df = df.with_columns(pl.Series('rv_fc', fc), pl.Series('iv_pct', pct))
    df = df.with_columns((pl.col('rv_fc') / pl.col('ivar10')).sqrt().alias('ratio'))
    rows = []
    for r in df.iter_rows(named=True):
        s = r['session']
        base = {'session': s, 'inv': None, 'target': None}
        rows.append({**base, 'm': 30, 'direction': 0, 'setup': 'ALL10V', 'spot': r['spot10']})
        rows.append({**base, 'm': 30, 'direction': 1, 'setup': 'ALL10P', 'spot': r['spot10']})
        ok = np.isfinite(r['ratio'] if r['ratio'] is not None else np.nan)
        cheap = (ok and r['ratio'] >= 1.25) or (r['iv_pct'] is not None and np.isfinite(r['iv_pct']) and r['iv_pct'] <= 0.20)
        rich = (ok and r['ratio'] <= 0.80) or (r['iv_pct'] is not None and np.isfinite(r['iv_pct']) and r['iv_pct'] >= 0.80)
        if cheap: rows.append({**base, 'm': 30, 'direction': 0, 'setup': 'VOLC', 'spot': r['spot10']})
        if rich: rows.append({**base, 'm': 30, 'direction': 1, 'setup': 'VOLR', 'spot': r['spot10']})
        rows.append({**base, 'm': 240, 'direction': 0, 'setup': 'EVF' if s in fomc else 'ALL1330', 'spot': r['spot1330']})
    ev = pl.DataFrame(rows, schema={'session': pl.Date, 'm': pl.Int64, 'direction': pl.Int64, 'setup': pl.Utf8, 'inv': pl.Float64, 'target': pl.Float64, 'spot': pl.Float64}, orient='row')
    return ev.with_columns(pl.lit(root).alias('root')), df

def load_fomc() -> set[dt.date]:
    f = os.path.join(paths.HERE, 'data', 'fomc_dates.csv')
    return {dt.date.fromisoformat(l.split(',')[0]) for l in open(f) if l[:2] == '20'}
