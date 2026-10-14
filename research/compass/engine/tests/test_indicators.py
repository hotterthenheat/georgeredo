import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import indicators as ind

def test_ema_seeded_at_first_close():
    c = np.array([10.0, 11.0, 12.0, 13.0])
    e = ind.ema(c, 3)
    k = 0.5
    exp = [10.0]
    for x in c[1:]: exp.append(x * k + exp[-1] * (1 - k))
    assert np.allclose(e, exp)
    assert e[0] == 10.0 and e.size == 4

def test_rsi_wilder_seed_and_extremes():
    up = np.arange(1, 30, dtype=float)
    r = ind.rsi(up, 14)
    assert np.isnan(r[:14]).all() and r[14] == 100.0 and r[-1] == 100.0
    down = up[::-1].copy()
    r = ind.rsi(down, 14)
    assert r[14] == 0.0
    flat = np.full(30, 5.0)
    assert ind.rsi(flat, 14)[14] == 50.0
    # hand-computed 3-period example
    c = np.array([44.0, 44.5, 44.2, 44.9, 45.1])
    r = ind.rsi(c, 3)
    g = (0.5 + 0 + 0.7) / 3; l = (0 + 0.3 + 0) / 3
    assert np.isclose(r[3], 100 - 100 / (1 + g / l))
    g2 = (g * 2 + 0.2) / 3; l2 = (l * 2 + 0) / 3
    assert np.isclose(r[4], 100 - 100 / (1 + g2 / l2))

def test_session_vwap_resets_per_session():
    h = np.array([10, 12, 20, 22.0]); l = np.array([9, 11, 19, 21.0]); c = np.array([9.5, 11.5, 19.5, 21.5]); v = np.array([100, 100, 100, 300.0])
    s = np.array([1, 1, 2, 2])
    out = ind.session_vwap(h, l, c, v, s)
    t = (h + l + c) / 3
    assert np.isclose(out[0], t[0]) and np.isclose(out[1], (t[0] * 100 + t[1] * 100) / 200)
    assert np.isclose(out[2], t[2]) and np.isclose(out[3], (t[2] * 100 + t[3] * 300) / 400)
    out0 = ind.session_vwap(h, l, c, np.zeros(4), s)
    assert np.allclose(out0, c)

def test_relative_volume_same_minute_median():
    # 3 sessions of 4 minutes; the 4th session's cumulative volume compared with the median of the prior 3 at each minute
    vol = np.array([1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 6, 6, 6, 6], dtype=float)
    sid = np.repeat([1, 2, 3, 4], 4); minute = np.tile(np.arange(4), 4)
    cum = ind.cumulative_session_volume(vol, sid)
    rv = ind.relative_volume(cum, minute, sid, lookback=3)
    assert np.isnan(rv[:12]).all()
    # session 4 cum = 6,12,18,24; medians of prior sessions' cum at each minute = 2,4,6,8
    assert np.allclose(rv[12:], [3.0, 3.0, 3.0, 3.0])

def test_structure_state_no_lookahead():
    # highs/lows rising: a swing high at i is confirmed at i+right
    high = np.array([1, 2, 3, 2, 1, 2, 4, 3, 2, 3, 5, 4, 3, 4, 6, 5, 4], dtype=float)
    low = high - 1.0
    st = ind.structure_state(high, low, left=2, right=2)
    sh, sl = ind.pivots(high, low, 2, 2)
    assert list(sh) == [2, 6, 10, 14]
    # before the second swing pair is confirmed the state is 0; after it, +1 (higher highs and higher lows)
    assert st[:8].max() == 0
    assert st[-1] == 1
    # a bar cannot know a pivot before right bars have passed
    first_known = int(sh[1] + 2)
    assert st[first_known - 1] == 0

def test_atr_wilder():
    h = np.array([10, 11, 12, 11, 13.0]); l = np.array([9, 10, 11, 10, 12.0]); c = np.array([9.5, 10.5, 11.5, 10.5, 12.5])
    a = ind.atr(h, l, c, 2)
    assert np.isnan(a[:2]).all()
    tr1 = max(11 - 10, abs(11 - 9.5), abs(10 - 9.5)); tr2 = max(12 - 11, abs(12 - 10.5), abs(11 - 10.5))
    assert np.isclose(a[2], (tr1 + tr2) / 2)
