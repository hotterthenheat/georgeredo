"""Black-Scholes with a continuous dividend yield, the same formulas as 3abida/src/core/greeks.ts (delta = e^{-qt} N(d1),
vega per 1 vol point), vectorised, plus an implied-volatility solver on the NBBO mid.

Carry defaults are STATED constants (r = 0.04, q = 0.0) until the rate series is wired in (ThetaData
interest_rate_history_eod); every result records the r and q it used.
"""
from __future__ import annotations
import numpy as np
from scipy.stats import norm

R_DEFAULT = 0.04
Q_DEFAULT = 0.0

def _d1d2(S, K, t, v, r, q):
    sqt = np.sqrt(t)
    d1 = (np.log(S / K) + (r - q + 0.5 * v * v) * t) / (v * sqt)
    return d1, d1 - v * sqt

def price(S, K, t, v, right, r=R_DEFAULT, q=Q_DEFAULT):
    """right: array-like of 1 for calls, -1 for puts (or 'C'/'P')."""
    S = np.asarray(S, float); K = np.asarray(K, float); t = np.maximum(np.asarray(t, float), 1e-4); v = np.maximum(np.asarray(v, float), 1e-4)
    sgn = _sign(right)
    d1, d2 = _d1d2(S, K, t, v, r, q)
    dfq = np.exp(-q * t); dfr = np.exp(-r * t)
    return sgn * (S * dfq * norm.cdf(sgn * d1) - K * dfr * norm.cdf(sgn * d2))

def delta(S, K, t, v, right, r=R_DEFAULT, q=Q_DEFAULT):
    S = np.asarray(S, float); K = np.asarray(K, float); t = np.maximum(np.asarray(t, float), 1e-4); v = np.maximum(np.asarray(v, float), 1e-4)
    sgn = _sign(right)
    d1, _ = _d1d2(S, K, t, v, r, q)
    dfq = np.exp(-q * t)
    return np.where(sgn > 0, dfq * norm.cdf(d1), dfq * (norm.cdf(d1) - 1.0))

def vega_point(S, K, t, v, r=R_DEFAULT, q=Q_DEFAULT):
    S = np.asarray(S, float); K = np.asarray(K, float); t = np.maximum(np.asarray(t, float), 1e-4); v = np.maximum(np.asarray(v, float), 1e-4)
    d1, _ = _d1d2(S, K, t, v, r, q)
    return S * np.exp(-q * t) * np.sqrt(t) * norm.pdf(d1) / 100.0

def gamma(S, K, t, v, r=R_DEFAULT, q=Q_DEFAULT):
    S = np.asarray(S, float); K = np.asarray(K, float); t = np.maximum(np.asarray(t, float), 1e-4); v = np.maximum(np.asarray(v, float), 1e-4)
    d1, _ = _d1d2(S, K, t, v, r, q)
    return np.exp(-q * t) * norm.pdf(d1) / (S * v * np.sqrt(t))

def theta_per_day(S, K, t, v, right, r=R_DEFAULT, q=Q_DEFAULT):
    """Calendar-day theta in price units (negative for long options), by central finite difference over one day."""
    t = np.asarray(t, float)
    h = 1.0 / 365.0
    return (price(S, K, np.maximum(t - h, 1e-4), v, right, r, q) - price(S, K, t + h, v, right, r, q)) / 2.0 * -1.0

def implied_vol(P, S, K, t, right, r=R_DEFAULT, q=Q_DEFAULT, lo=1e-3, hi=5.0, iters=60):
    """Vectorised bisection on the mid price P. NaN where P is below intrinsic/discounted bounds or above the price at hi."""
    P = np.asarray(P, float); S = np.asarray(S, float); K = np.asarray(K, float); t = np.maximum(np.asarray(t, float), 1e-4)
    sgn = _sign(right)
    shape = np.broadcast(P, S, K, t, sgn).shape
    P, S, K, t, sgn = (np.broadcast_to(x, shape).astype(float) for x in (P, S, K, t, sgn))
    a = np.full(shape, lo); b = np.full(shape, hi)
    pa = price(S, K, t, a, sgn, r, q); pb = price(S, K, t, b, sgn, r, q)
    ok = (P > pa) & (P < pb) & np.isfinite(P)
    for _ in range(iters):
        m = 0.5 * (a + b)
        pm = price(S, K, t, m, sgn, r, q)
        up = pm < P
        a = np.where(up, m, a); b = np.where(up, b, m)
    out = 0.5 * (a + b)
    return np.where(ok, out, np.nan)

def _sign(right):
    r = np.asarray(right)
    if r.dtype.kind in 'UOS':
        return np.where(np.char.upper(r.astype(str)).astype('U1') == 'C', 1.0, -1.0)
    return np.where(r > 0, 1.0, -1.0)
