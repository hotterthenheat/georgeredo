"""Daily setups for Tier D (lifecycle protocol §3 at daily resolution): decided at a session's close from split-adjusted
daily bars known by then; the position opens at that close's NBBO.

  D_TP   trend pullback: EMA 20 > 50 > 200 (or the reverse), the day's low reached EMA 20 within the last 3 sessions, and the
         close back beyond EMA 20; invalidation a close beyond EMA 50
  D_BO   breakout: a close beyond the prior 20-session high (low), the first in 5 sessions; invalidation a close back inside
  D_BOF  failed breakout: within 3 sessions of a D_BO, a close back inside -> the other way; invalidation the extreme since
  D_BN   bounce: 20-session z-score of the close <= -2 (>= +2) and a reversal day (close beyond the open); invalidation
         the day's extreme -/+ 0.5 ATR
  D_BNF  failed bounce: within 3 sessions of a D_BN, a close beyond its invalidation -> the original move's way
  D_ALLL / D_ALLS   every Monday (the first session of each week), long and short: the all-days directional control
  D_ALLV / D_ALLP   every Monday: straddle/strangle and credit-put/cash-secured-put controls
  D_VOLC / D_VOLR   Mondays where the 30-day ATM IV is below 0.8 x (above 1.25 x) the 20-session realized vol, or at or
         below the 20th (at or above the 80th) percentile of its prior 252 sessions
  D_FOMC the session before an FOMC statement day (index ETFs); D_ALLF the same weekday in non-FOMC weeks
  D_EARN the 5th session before an earnings report (single names); D_EARNC the subset whose straddle prices less than
         the median absolute move of that name's prior 8 reports (point in time)
Controls (RND) are drawn by the runner: random sessions with the same direction, 5 seeds."""
from __future__ import annotations
import datetime as dt, os
import numpy as np
import polars as pl
from . import daily as dy, paths, vol

def directional(root: str) -> pl.DataFrame:
    d = dy.daily_series(root).sort('session')
    s = d['session'].to_list(); n = d.height
    c = d['c_adj'].to_numpy(); o = d['o_adj'].to_numpy(); h = d['h_adj'].to_numpy(); l = d['l_adj'].to_numpy()
    e20 = d['ema20'].to_numpy(); e50 = d['ema50'].to_numpy(); e200 = d['ema200'].to_numpy(); atr = d['atr14'].to_numpy()
    hi20 = d['hi20'].to_numpy(); lo20 = d['lo20'].to_numpy(); z = d['z20'].to_numpy()
    adj = d['adj'].to_numpy()
    rows = []
    def add(i, setup, direction, inv):  # inv in unadjusted price units (the option's)
        rows.append((s[i], setup, int(direction), float(inv) * adj[i] if np.isfinite(inv) else np.nan, float(d['close'][i])))
    last_bo = {1: -99, -1: -99}
    bo_open = []      # (i, direction, level)
    bn_open = []      # (i, direction, inv)
    for i in range(200, n):
        # trend pullback
        if e20[i] > e50[i] > e200[i] and np.nanmin(l[max(0, i - 2):i + 1] - e20[max(0, i - 2):i + 1]) <= 0 and c[i] > e20[i]:
            add(i, 'D_TP', 1, e50[i])
        if e20[i] < e50[i] < e200[i] and np.nanmax(h[max(0, i - 2):i + 1] - e20[max(0, i - 2):i + 1]) >= 0 and c[i] < e20[i]:
            add(i, 'D_TP', -1, e50[i])
        # breakouts (first in 5 sessions per side)
        if np.isfinite(hi20[i]) and c[i] > hi20[i] and i - last_bo[1] > 5:
            add(i, 'D_BO', 1, hi20[i]); last_bo[1] = i; bo_open.append((i, 1, hi20[i], h[i]))
        if np.isfinite(lo20[i]) and c[i] < lo20[i] and i - last_bo[-1] > 5:
            add(i, 'D_BO', -1, lo20[i]); last_bo[-1] = i; bo_open.append((i, -1, lo20[i], l[i]))
        keep = []
        for (j, dj, lvl, ext) in bo_open:
            ext = max(ext, h[i]) if dj > 0 else min(ext, l[i])
            if i > j and ((dj > 0 and c[i] < lvl) or (dj < 0 and c[i] > lvl)):
                add(i, 'D_BOF', -dj, ext)
            elif i - j < 3: keep.append((j, dj, lvl, ext))
        bo_open = keep
        # bounces
        if np.isfinite(z[i]) and z[i] <= -2 and c[i] > o[i]:
            inv = l[i] - 0.5 * atr[i]; add(i, 'D_BN', 1, inv); bn_open.append((i, 1, inv))
        if np.isfinite(z[i]) and z[i] >= 2 and c[i] < o[i]:
            inv = h[i] + 0.5 * atr[i]; add(i, 'D_BN', -1, inv); bn_open.append((i, -1, inv))
        keep = []
        for (j, dj, inv) in bn_open:
            if i > j and ((dj > 0 and c[i] < inv) or (dj < 0 and c[i] > inv)):
                add(i, 'D_BNF', -dj, h[j] + 0.5 * atr[j] if dj > 0 else l[j] - 0.5 * atr[j])
            elif i - j < 3: keep.append((j, dj, inv))
        bn_open = keep
    # all-days controls: the first session of each week
    wk = pl.DataFrame({'session': s}).with_columns(pl.col('session').dt.strftime('%G-%V').alias('w')).group_by('w').agg(pl.col('session').min()).sort('session')
    idx = {x: i for i, x in enumerate(s)}
    for m in wk['session'].to_list():
        i = idx[m]
        if i < 200: continue
        add(i, 'D_ALLL', 1, np.nan); add(i, 'D_ALLS', -1, np.nan); add(i, 'D_ALLV', 0, np.nan); add(i, 'D_ALLP', 1, np.nan)
    out = pl.DataFrame(rows, schema={'session': pl.Date, 'setup': pl.Utf8, 'direction': pl.Int64, 'inv': pl.Float64, 'spot': pl.Float64}, orient='row')
    return out.with_columns(pl.lit(root).alias('root')).sort(['session', 'setup'])

def fomc(root: str) -> pl.DataFrame:
    d = dy.underlying_daily(root).sort('session'); s = d['session'].to_list(); idx = {x: i for i, x in enumerate(s)}
    days = vol.load_fomc()
    rows = []
    for f in sorted(days):
        if f not in idx or idx[f] == 0: continue
        i = idx[f] - 1
        rows.append((s[i], 'D_FOMC', 0, np.nan, float(d['close'][i])))
    fset = {s[idx[f] - 1] for f in days if f in idx and idx[f] > 0}
    wd = {x.weekday() for x in fset}
    for i, x in enumerate(s):
        if x.weekday() in wd and x not in fset and i > 200 and i % 5 == 0:
            rows.append((x, 'D_ALLF', 0, np.nan, float(d['close'][i])))
    return pl.DataFrame(rows, schema={'session': pl.Date, 'setup': pl.Utf8, 'direction': pl.Int64, 'inv': pl.Float64, 'spot': pl.Float64}, orient='row').with_columns(pl.lit(root).alias('root'))

def earnings(root: str) -> pl.DataFrame:
    """The 5th session before each report (UW calendar). Report timing (premarket/afterhours) decides the event session:
    a premarket report moves the report date's open, an after-hours one the next session's open."""
    f = os.path.join(os.path.dirname(os.path.dirname(paths.HERE)), '..', 'data_lake', 'unusualwhales', 'earnings.parquet')
    f = os.path.normpath(f)
    e = pl.read_parquet(f).filter(pl.col('ticker') == root)
    if e.height == 0: return pl.DataFrame()
    d = dy.underlying_daily(root).sort('session'); s = d['session'].to_list(); idx = {x: i for i, x in enumerate(s)}
    rows = []
    tcol = next((c for c in ('report_time', 'time', 'timing') if c in e.columns), None)
    for r in e.iter_rows(named=True):
        rd = r['report_date']; rd = dt.date.fromisoformat(rd[:10]) if isinstance(rd, str) else rd
        if rd not in idx: continue
        t = (r.get(tcol) or '').lower() if tcol else ''
        ev_i = idx[rd] if ('pre' in t or 'bmo' in t) else idx[rd] + 1     # the first session that trades on the news
        i = ev_i - 5
        if i < 1 or ev_i >= len(s): continue
        rows.append((s[i], 'D_EARN', 0, np.nan, float(d['close'][i]), s[ev_i]))
    return pl.DataFrame(rows, schema={'session': pl.Date, 'setup': pl.Utf8, 'direction': pl.Int64, 'inv': pl.Float64, 'spot': pl.Float64, 'event_session': pl.Date}, orient='row').with_columns(pl.lit(root).alias('root'))
