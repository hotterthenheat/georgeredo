"""Test 8 (Weekly/Swing/LEAPS premium stops): with no multi-day option paths on disk, the Black-Scholes drag of a
-20% / -17% / -25% premium stop on a long ATM option at 7, 14, 30, 90 DTE: how much the stop decays into the stop on
its own (theta), the 1-vega move in IV that would do it, and the underlying move (against the position) that triggers
it after 0, 1 and 3 trading days, at IVs of 15%, 20% and 30%. No fitting; pure arithmetic. Writes out/t8_bs_drag.csv.
  python3 -I bs_drag.py
"""
import os, math, numpy as np, polars as pl
from math import log, sqrt, exp
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
def N(x): return 0.5 * (1 + math.erf(x / sqrt(2)))
def bs(S, K, T, r, iv, call=True):
    if T <= 0: return max(S - K, 0) if call else max(K - S, 0)
    d1 = (log(S / K) + (r + iv * iv / 2) * T) / (iv * sqrt(T)); d2 = d1 - iv * sqrt(T)
    return S * N(d1) - K * exp(-r * T) * N(d2) if call else K * exp(-r * T) * N(-d2) - S * N(-d1)
def solve_move(S, K, T0, T1, r, iv, stop_frac, call=True):
    """underlying move (fraction, against a long call = down) at which the option, after T0-T1 of decay, is worth stop_frac of its entry"""
    p0 = bs(S, K, T0, r, iv, call); target = stop_frac * p0
    lo, hi = 0.0, 0.5
    f = lambda x: bs(S * (1 - x) if call else S * (1 + x), K, T1, r, iv, call) - target
    if f(0) <= 0: return 0.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) > 0: lo = mid
        else: hi = mid
    return (lo + hi) / 2
rows = []
S = 100.0; r = 0.04
for dte in (7, 14, 30, 90, 365):
    for iv in (0.15, 0.20, 0.30):
        T0 = dte / 365
        p0 = bs(S, S, T0, r, iv)
        vega = (bs(S, S, T0, r, iv + 0.01) - p0)
        for days in (0, 1, 3):
            T1 = max(dte - days * 365 / 252, 0.01) / 365
            p1 = bs(S, S, T1, r, iv)
            theta_pct = p1 / p0 - 1
            row = dict(dte=dte, iv=iv, atm_premium_pct_of_spot=p0 / S, vega_1pt_pct_of_premium=vega / p0, days_held=days, decay_alone_pct=theta_pct)
            for stop in (0.83, 0.80, 0.75):
                row[f'move_to_stop_{round((1-stop)*100)}pct'] = solve_move(S, S, T0, T1, r, iv, stop)
                row[f'iv_drop_to_stop_{round((1-stop)*100)}pct'] = (1 - stop + theta_pct) / (vega / p0) if days == 0 else np.nan
            daily_sigma = iv / sqrt(252)
            row['daily_1sigma_move'] = daily_sigma
            row['move_to_stop_20pct_in_sigmas'] = row['move_to_stop_20pct'] / (daily_sigma * sqrt(max(days, 1)))
            rows.append(row)
df = pl.DataFrame(rows); df = df.with_columns([pl.col(c).round(5) for c, t in df.schema.items() if t == pl.Float64])
df.write_csv(os.path.join(OUT, 't8_bs_drag.csv'))
pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(100)
print(df.filter(pl.col('iv') == 0.20).select('dte', 'iv', 'atm_premium_pct_of_spot', 'days_held', 'decay_alone_pct', 'move_to_stop_20pct', 'move_to_stop_17pct', 'move_to_stop_25pct', 'daily_1sigma_move', 'move_to_stop_20pct_in_sigmas', 'iv_drop_to_stop_20pct'))
