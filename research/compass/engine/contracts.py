"""Point-in-time contract selection on a chain snapshot at the decision minute (research/compass/04_protocol.md §4).

A chain snapshot is a polars frame with one row per (strike, right) carrying bid, ask, bid_size, ask_size at the decision
minute (the last NBBO at that minute boundary), optionally open_interest (as of the prior settlement) and cum_volume
(intraday volume up to the decision minute). Implied vol and delta are computed from the mid with engine.greeks.
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import polars as pl
from . import calendar as cal, greeks as g

SELECT = dict(delta_lo=0.30, delta_hi=0.60, delta_target=0.45, min_oi=250, min_volume=100, max_spread_pct=0.12, min_ask=0.05,
              r=g.R_DEFAULT, q=g.Q_DEFAULT, pick='delta_nearest')

def years_to_expiry(decision_ts: dt.datetime, last_trading_day: dt.date) -> float:
    """Calendar time from the decision instant to the close of the contract's last trading day, in years (365.25 days) —
    the practitioner and the app's convention (core/greeks.ts prices on calendar years). Floored at one minute."""
    close = dt.datetime.combine(last_trading_day, cal.close_time(last_trading_day))
    return max((close - decision_ts).total_seconds(), 60.0) / (365.25 * 86400.0)

def pick_expiration(expirations: list[dt.date], decision_date: dt.date, category: str, root: str, oi_by_exp: dict | None = None) -> dt.date | None:
    """The listed expiration in the category; ties broken by the most open interest when given, else the nearest."""
    cands = []
    for e in expirations:
        ltd = cal.last_trading_day(e, cal.is_spx_am_settled(root, e))
        if cal.expiry_category(decision_date, ltd) == category: cands.append(e)
    if not cands: return None
    if oi_by_exp: return max(cands, key=lambda e: (oi_by_exp.get(e, 0), -(e - decision_date).days))
    return min(cands)

def annotate(chain: pl.DataFrame, spot: float, t_years: float, params: dict | None = None) -> pl.DataFrame:
    p = {**SELECT, **(params or {})}
    K = chain['strike'].to_numpy().astype(float); bid = chain['bid'].to_numpy().astype(float); ask = chain['ask'].to_numpy().astype(float)
    right = chain['right'].to_numpy().astype(str)
    mid = (bid + ask) / 2.0
    with np.errstate(invalid='ignore', divide='ignore'):
        spread_pct = np.where(mid > 0, (ask - bid) / mid, np.nan)
    iv = g.implied_vol(mid, spot, K, max(t_years, 1e-4), right, p['r'], p['q'])
    delta = np.abs(g.delta(spot, K, max(t_years, 1e-4), np.where(np.isnan(iv), 0.3, iv), right, p['r'], p['q']))
    delta = np.where(np.isnan(iv), np.nan, delta)
    return chain.with_columns([pl.Series('mid', mid), pl.Series('spread_pct', spread_pct), pl.Series('iv', iv), pl.Series('delta_abs', delta)])

def select(chain: pl.DataFrame, spot: float, t_years: float, direction: int, params: dict | None = None) -> tuple[dict | None, dict]:
    """Returns (chosen row as dict or None, diagnostics with rejection counts)."""
    p = {**SELECT, **(params or {})}
    want = 'C' if direction > 0 else 'P'
    c = annotate(chain, spot, t_years, p)
    rt = c['right'].cast(pl.Utf8).str.to_uppercase().str.slice(0, 1)
    c = c.with_columns(rt.alias('_r')).filter(pl.col('_r') == want)
    diag = {'n_side': c.height}
    ok = pl.lit(True)
    checks = {
        'bid_zero': pl.col('bid') > 0,
        'ask_min': pl.col('ask') >= p['min_ask'],
        'crossed': pl.col('ask') >= pl.col('bid'),
        'spread': pl.col('spread_pct') < p['max_spread_pct'],
        'delta_band': (pl.col('delta_abs') >= p['delta_lo']) & (pl.col('delta_abs') <= p['delta_hi']),
    }
    if 'open_interest' in c.columns and p['min_oi'] is not None: checks['oi'] = pl.col('open_interest') > p['min_oi']
    if 'cum_volume' in c.columns and p['min_volume'] is not None: checks['volume'] = pl.col('cum_volume') > p['min_volume']
    for name, expr in checks.items():
        diag[f'reject_{name}'] = int(c.filter(ok & ~expr.fill_null(False)).height)
        ok = ok & expr.fill_null(False)
    cand = c.filter(ok)
    diag['n_eligible'] = cand.height
    if cand.height == 0: return None, diag
    if p['pick'] == 'delta_nearest':
        cand = cand.with_columns((pl.col('delta_abs') - p['delta_target']).abs().alias('_d')).sort(['_d', 'spread_pct'])
    elif p['pick'] == 'highest_oi' and 'open_interest' in cand.columns:
        cand = cand.sort('open_interest', descending=True)
    elif p['pick'] == 'tightest_spread':
        cand = cand.sort(['spread_pct', 'strike'])
    row = cand.row(0, named=True)
    row.pop('_d', None); row.pop('_r', None)
    return row, diag
