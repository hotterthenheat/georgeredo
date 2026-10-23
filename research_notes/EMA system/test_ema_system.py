"""
test_ema_system.py — small unit tests of the RULEBOOK_v0 engine: indicators on toy series, no look-ahead (changing bars
after a decision never changes it), the swing confirmation delay, the fees. Run: python3 test_ema_system.py
"""
from __future__ import annotations

import math

import numpy as np

import ema_system as E

NB = E.NBAR


def toy_series(closes_by_day: list[np.ndarray], vols=None, name='SPY', hl=0.0):
    days = [f'D{k}' for k in range(len(closes_by_day))]
    ov = {}
    for k, c in enumerate(closes_by_day):
        v = np.full(NB, 100.0) if vols is None else vols[k]
        ov[days[k]] = (c.copy(), c + hl, c - hl, c.copy(), v)
    return E.Series(name, days=days, warm=[], override=ov)


def test_ema():
    x = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
    e = E.ema_seq(x, 3)                                   # alpha 0.5
    want = [1.0, 1.5, 2.25, 2.25, 3.625]
    assert np.allclose(e, want), e


def test_rsi():
    up = np.arange(30, dtype=float)
    assert E.rsi_wilder(up)[-1] == 100.0
    alt = np.array([10.0 + (k % 2) for k in range(40)])
    assert abs(E.rsi_wilder(alt)[14] - 50.0) < 1e-9
    rng = np.random.default_rng(1)
    x = 100 + np.cumsum(rng.normal(0, 1, 60))
    # independent Wilder: simple means of the first 14 changes, then (prev*13 + x)/14
    d = np.diff(x)
    g, l_ = np.maximum(d, 0), np.maximum(-d, 0)
    ag, al = g[:14].mean(), l_[:14].mean()
    vals = [100 - 100 / (1 + ag / al)]
    for k in range(14, d.size):
        ag = (ag * 13 + g[k]) / 14
        al = (al * 13 + l_[k]) / 14
        vals.append(100 - 100 / (1 + ag / al))
    r = E.rsi_wilder(x)
    assert np.all(np.isnan(r[:14])) and np.allclose(r[14:], vals)


def test_vwap_roc_buckets():
    c0 = np.linspace(100, 101, NB)
    c1 = np.linspace(101, 99, NB)
    v = [np.arange(1, NB + 1, dtype=float), np.full(NB, 10.0)]
    X = toy_series([c0, c1], vols=v, hl=0.5)
    tp = c1                                                # (H + L + C)/3 = C when H, L = C ± 0.5
    assert np.allclose(X.vwap[1], np.cumsum(tp * 10) / np.cumsum(np.full(NB, 10.0)))
    assert math.isclose(X.roc5(1, 2), c1[2] / c0[NB - 3] - 1)                    # ROC steps back across the session
    assert math.isclose(X.c5[1, 0], c1[4]) and math.isclose(X.c15[1, 1], c1[29])
    assert X.last5(1, 15) == (1, 2) and X.last5(1, 4) == (0, 77) and X.last15(1, 15) == (1, 0)
    # SPX: time-weighted VWAP, no RVOL
    Y = toy_series([c0, c1], name='SPXW')
    assert np.allclose(Y.vwap[1], np.cumsum(c1) / np.arange(1, NB + 1)) and np.isnan(Y.rvol).all()


def test_rvol():
    vols = [np.full(NB, 100.0) for _ in range(11)]
    vols[10] = np.full(NB, 150.0)
    X = toy_series([np.full(NB, 100.0)] * 11, vols=vols)
    assert np.allclose(X.rvol[10], 1.5) and np.isnan(X.rvol[3]).all()            # 3 prior sessions < 5 → undefined


def test_swing_delay():
    c = 100 + 0.001 * np.arange(NB)                        # strictly rising: no swing anywhere
    for t, v in ((10, 103.0), (30, 105.0), (15, 99.0), (25, 99.5)):   # highs at 10, 30; lows at 15, 25
        c[t] = v
    X = toy_series([c])
    # the high at 30 (105) is unknown at s = 31 (one high known → no structure) and known at s = 32 (rising)
    s31 = X.structure(0, 31)
    s32 = X.structure(0, 32)
    assert s31 == 0 and s32 == 1, (s31, s32)


def test_no_lookahead():
    rng = np.random.default_rng(7)
    checked = 0
    for nm in E.NAMES:
        base = E.series(nm)
        for d in E.DAYS:
            i = base.di(d)
            s0 = int(rng.integers(40, 340))
            ov = {}
            for k, dd in enumerate(base.days):
                b = [base.O[k].copy(), base.H[k].copy(), base.L[k].copy(), base.C[k].copy(), base.V[k].copy()]
                if k > i or (k == i):
                    lo = s0 + 1 if k == i else 0
                    noise = rng.normal(0, 5, NB - lo)
                    for a in b[:4]:
                        a[lo:] = a[lo:] + noise
                    b[1][lo:] += 1; b[2][lo:] -= 1
                    if nm != 'SPXW':
                        b[4][lo:] = b[4][lo:] * rng.uniform(0.1, 5, NB - lo)
                ov[dd] = tuple(b)
            Y = E.Series(nm, days=E.DAYS, warm=base.days[:len(base.days) - len(E.DAYS)], override=ov)
            for m in range(E.FIRST_M, s0 + 2):                   # decisions at m use bars <= m - 1 <= s0
                for cfg in 'AB':
                    for sig in ('full', 'cross', 'align'):
                        assert E.SIGNALS[sig](base, i, m, cfg) == E.SIGNALS[sig](Y, i, m, cfg), (nm, d, m, cfg, sig)
                        checked += 1
                assert base.structure(i, m - 1) == Y.structure(i, m - 1)
    return checked


def test_fees():
    assert E.fee('SPY', 0.5) == 0.68748 and E.fee('IWM', 9) == 0.68748
    assert E.fee('SPXW', 0.99) == 1.18748 and E.fee('SPXW', 1.0) == 1.27748
    # a round trip: buy SPXW at 0.95, sell at 1.40 → gross 45, fees 1.18748 + 1.27748
    assert math.isclose(45 - (E.fee('SPXW', 0.95) + E.fee('SPXW', 1.40)), 45 - 2.46496)


if __name__ == '__main__':
    test_ema(); test_rsi(); test_vwap_roc_buckets(); test_rvol(); test_swing_delay(); test_fees()
    n = test_no_lookahead()
    print(f'all tests pass (no-lookahead: {n} decisions unchanged under perturbed future bars)')
