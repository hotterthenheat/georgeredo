import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lc import bs
from engine import greeks as g

def test_matches_engine_greeks():
    rng = np.random.default_rng(3)
    n = 4000
    S = rng.uniform(50, 600, n); K = S * rng.uniform(0.8, 1.2, n); t = rng.uniform(1e-5, 1.5, n); v = rng.uniform(0.05, 1.5, n)
    sgn = np.where(rng.random(n) < 0.5, 1.0, -1.0)
    P = g.price(S, K, t, v, sgn) * rng.uniform(0.9, 1.1, n)
    P = np.where(P >= 0.005, P, np.nan)          # below half a cent is no quote; the tails of erf and scipy's cdf part there
    a = g.implied_vol(P, S, K, t, sgn); b = bs.implied_vol(P, S, K, t, sgn)
    both = np.isfinite(a) & np.isfinite(b)
    assert (np.isfinite(a) == np.isfinite(b)).mean() > 0.999
    assert np.max(np.abs(a[both] - b[both])) < 1e-9
    da = g.delta(S, K, t, v, sgn); db = bs.delta(S, K, t, v, sgn)
    assert np.max(np.abs(da - db)) < 1e-12

def test_theta_matches_finite_difference():
    S = np.array([100.0, 100.0, 450.0]); K = np.array([100.0, 95.0, 460.0]); t = np.array([0.1, 0.5, 0.02]); v = np.array([0.2, 0.3, 0.15]); sgn = np.array([1.0, -1.0, 1.0])
    h = 1e-6
    fd = (g.price(S, K, t - h, v, sgn) - g.price(S, K, t, v, sgn)) / h / 365.0     # value change as calendar time passes
    an = bs.theta_day(S, K, t, v, sgn)
    assert np.max(np.abs(fd - an)) < 1e-4 and (an[[0, 2]] < 0).all()
