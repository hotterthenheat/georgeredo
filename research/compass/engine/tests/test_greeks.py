import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import greeks as g

def test_price_put_call_parity_and_known_value():
    S, K, t, v, r, q = 100.0, 100.0, 0.5, 0.2, 0.04, 0.0
    c = g.price(S, K, t, v, 'C', r, q); p = g.price(S, K, t, v, 'P', r, q)
    assert np.isclose(c - p, S * np.exp(-q * t) - K * np.exp(-r * t), atol=1e-10)
    # textbook: S=100,K=100,t=0.5,v=0.2,r=0.04 -> call ~ 6.64
    assert abs(c - 6.64) < 0.02

def test_delta_conventions_match_app():
    S, K, t, v, r, q = 100.0, 100.0, 0.5, 0.2, 0.04, 0.02
    from scipy.stats import norm
    d1 = (np.log(S / K) + (r - q + 0.5 * v * v) * t) / (v * np.sqrt(t))
    assert np.isclose(g.delta(S, K, t, v, 'C', r, q), np.exp(-q * t) * norm.cdf(d1))
    assert np.isclose(g.delta(S, K, t, v, 'P', r, q), np.exp(-q * t) * (norm.cdf(d1) - 1))
    # vega per vol POINT (divided by 100)
    assert np.isclose(g.vega_point(S, K, t, v, r, q) * 100, S * np.exp(-q * t) * np.sqrt(t) * norm.pdf(d1))

def test_implied_vol_roundtrip_and_bounds():
    S = np.array([100.0, 100.0, 50.0]); K = np.array([105.0, 95.0, 55.0]); t = np.array([0.1, 0.1, 0.02]); v = np.array([0.25, 0.4, 0.6])
    right = np.array(['C', 'P', 'C'])
    P = g.price(S, K, t, v, right)
    iv = g.implied_vol(P, S, K, t, right)
    assert np.allclose(iv, v, atol=1e-6)
    # below intrinsic -> NaN
    assert np.isnan(g.implied_vol(0.01, 100.0, 90.0, 0.1, 'C'))
