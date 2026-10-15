"""Black-Scholes with continuous yield and the bisection IV solver of engine/greeks.py, compiled (numba, math.erf), for
the per-minute chain snapshots. Same conventions: t floored at 1e-4 years, vol floored at 1e-4, bisection on [1e-3, 5]
for 60 iterations, NaN when the mid is outside (price at lo, price at hi). tests/test_bs.py checks it against
engine.greeks to 1e-9."""
from __future__ import annotations
import math
import numpy as np
from numba import njit

R_DEFAULT = 0.04
Q_DEFAULT = 0.0

@njit(cache=True)
def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

@njit(cache=True)
def _price1(S, K, t, v, sgn, r, q):
    t = max(t, 1e-4); v = max(v, 1e-4)
    sqt = math.sqrt(t)
    d1 = (math.log(S / K) + (r - q + 0.5 * v * v) * t) / (v * sqt)
    d2 = d1 - v * sqt
    return sgn * (S * math.exp(-q * t) * _ncdf(sgn * d1) - K * math.exp(-r * t) * _ncdf(sgn * d2))

@njit(cache=True)
def implied_vol(P, S, K, t, sgn, r=R_DEFAULT, q=Q_DEFAULT):
    n = P.size
    out = np.full(n, np.nan)
    for i in range(n):
        p = P[i]
        if not (p == p): continue
        tt = max(t[i], 1e-4)
        lo = 1e-3; hi = 5.0
        pa = _price1(S[i], K[i], tt, lo, sgn[i], r, q); pb = _price1(S[i], K[i], tt, hi, sgn[i], r, q)
        if not (p > pa and p < pb): continue
        a = lo; b = hi
        for _ in range(60):
            m = 0.5 * (a + b)
            if _price1(S[i], K[i], tt, m, sgn[i], r, q) < p: a = m
            else: b = m
        out[i] = 0.5 * (a + b)
    return out

@njit(cache=True)
def delta(S, K, t, v, sgn, r=R_DEFAULT, q=Q_DEFAULT):
    n = K.size
    out = np.empty(n)
    for i in range(n):
        tt = max(t[i], 1e-4); vv = max(v[i], 1e-4)
        d1 = (math.log(S[i] / K[i]) + (r - q + 0.5 * vv * vv) * tt) / (vv * math.sqrt(tt))
        e = math.exp(-q * tt)
        out[i] = e * _ncdf(d1) if sgn[i] > 0 else e * (_ncdf(d1) - 1.0)
    return out

@njit(cache=True)
def theta_day(S, K, t, v, sgn, r=R_DEFAULT, q=Q_DEFAULT):
    """Analytic Black-Scholes theta (the instantaneous rate of value change with calendar time), per calendar day;
    negative for a long option. On a same-day contract it is a rate, not a forecast of a whole day's decay."""
    n = K.size
    out = np.empty(n)
    for i in range(n):
        tt = max(t[i], 1e-4); vv = max(v[i], 1e-4); sq = math.sqrt(tt)
        d1 = (math.log(S[i] / K[i]) + (r - q + 0.5 * vv * vv) * tt) / (vv * sq); d2 = d1 - vv * sq
        pdf = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
        a = -S[i] * math.exp(-q * tt) * pdf * vv / (2.0 * sq)
        if sgn[i] > 0:
            th = a - r * K[i] * math.exp(-r * tt) * _ncdf(d2) + q * S[i] * math.exp(-q * tt) * _ncdf(d1)
        else:
            th = a + r * K[i] * math.exp(-r * tt) * _ncdf(-d2) - q * S[i] * math.exp(-q * tt) * _ncdf(-d1)
        out[i] = th / 365.0
    return out
