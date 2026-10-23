"""
test_ema_v1.py — unit tests of the RULEBOOK_v1 engine (ema_v1.py): the 3% veto at its edge, the venue choice (cost share,
ties to SPY), the 14:00 flat and the 13:30 entry cut, the V-chop definition on a toy series, and no look-ahead — every
v1 decision (the full, crossover and alignment signals and the V-chop gate) unchanged when every bar after the decision's
last bar is truncated (set missing), on the three test weeks. Run: python3 test_ema_v1.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import ema_system as E
import ema_v1 as V

NB = E.NBAR
S = E.S
HERE = Path(__file__).resolve().parent


def toy(closes_by_day, name='SPY', hl=0.5, opens=None, highs=None, lows=None):
    days = [f'D{k:03d}' for k in range(len(closes_by_day))]
    ov = {}
    for k, c in enumerate(closes_by_day):
        o = c.copy() if opens is None else opens[k]
        h = c + hl if highs is None else highs[k]
        l_ = c - hl if lows is None else lows[k]
        ov[days[k]] = (o, h, l_, c.copy(), np.full(NB, 100.0))
    return E.Series(name, days=days, warm=[], override=ov), days


class Patch:
    def __init__(self, **kw):
        self.kw, self.old = kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            mod, attr = k.split('__')
            m = {'S': S, 'V': V}[mod]
            self.old[k] = getattr(m, attr)
            setattr(m, attr, v)

    def __exit__(self, *a):
        for k, v in self.old.items():
            mod, attr = k.split('__')
            setattr({'S': S, 'V': V}[mod], attr, v)


def test_veto():
    K = np.array([100.0])
    for half, ok in ((0.015, True), (0.0155, False)):           # spread exactly 3% kept, 3.1% vetoed
        bid = np.full((391, 1, 2), np.nan); ask = np.full((391, 1, 2), np.nan)
        bid[200, 0, 0], ask[200, 0, 0] = 1.0 - half, 1.0 + half
        with Patch(S__chain=lambda n, d: (K, bid, ask), S__oi_day=lambda n, d: {S.occ(n, d, 0, 100.0): 1000},
                   S__prev_volume=lambda n, d: {(100.0, 0): 1000}):
            c, why = V.pick.__wrapped__('SPY', '2025-01-03', 200, 1, 100.0)
        assert (c is not None) == ok, (half, c, why)
        if not ok:
            assert why == 'spread > 3%', why


def test_venue():
    spy = dict(ask=1.02, bid=1.00)
    spx = dict(ask=10.10, bid=10.00)
    cs1 = ((1.02 - 1.01) + 0.68748 / 100) / 1.01
    cs2 = ((10.10 - 10.05) + 1.27748 / 100) / 10.05
    assert math.isclose(V.cost_share('SPY', spy), cs1) and math.isclose(V.cost_share('SPXW', spx), cs2)
    assert V.cost_share('SPXW', dict(ask=0.99, bid=0.97)) == ((0.99 - 0.98) + 1.18748 / 100) / 0.98
    sx = np.full(NB, 5000.0)

    def fake(cs_spy, cs_spx):
        def p(name, d, m, side, spot, cap=V.CAP):
            if name == 'SPY':
                return (None, 'spread > 3%') if cs_spy is None else (dict(ask=1 + cs_spy, bid=1 - cs_spy), 'ok')
            return (None, 'OI < 250') if cs_spx is None else (dict(ask=1 + cs_spx, bid=1 - cs_spx), 'ok')
        return p
    # with fees ignored by giving both the same premium scale, the cheaper half-spread wins; a tie goes to SPY
    with Patch(V__spx_close=lambda d: sx, V__cost_share=lambda v, c: c['ask'] - 1):
        for a, b, want in ((0.01, 0.02, 'SPY'), (0.02, 0.01, 'SPXW'), (0.01, 0.01, 'SPY'), (None, 0.01, 'SPXW'),
                           (0.01, None, 'SPY')):
            with Patch(V__pick=fake(a, b)):
                v, c, info = V.choose('SP', 'D', 100, 1, 500.0)
            assert v == want, (a, b, v)
        with Patch(V__pick=fake(None, None)):
            v, c, info = V.choose('SP', 'D', 100, 1, 500.0)
        assert v is None and info == 'SPY: spread > 3% / SPXW: OI < 250', info
    # no SPX print at m → SPXW is not a candidate
    sx2 = sx.copy(); sx2[99] = np.nan
    with Patch(V__spx_close=lambda d: sx2, V__pick=fake(0.02, 0.01), V__cost_share=lambda v, c: c['ask'] - 1):
        assert V.choose('SP', 'D', 100, 1, 500.0)[0] == 'SPY'


def test_flat_and_cut():
    c = np.full(NB, 100.0)
    X, days = toy([c, c.copy()], hl=0.5)
    bid = np.full((391, 1, 2), np.nan); ask = np.full((391, 1, 2), np.nan)
    bid[:, 0, 0] = np.arange(391) / 100.0; ask[:, 0, 0] = bid[:, 0, 0] + 0.01
    con = dict(K=100.0, i=0, r=0, ask=1.0, bid=0.99, spread=0.01, delta=0.45, oi=1000, pvol=1000)
    with Patch(V__choose=lambda st, d, m, side, spot: ('SPY', con, {}), S__chain=lambda n, d: (np.array([100.0]), bid, ask)):
        for x in ('X1', 'X2', 'X3', 'X4'):
            # closes never move (no stop: low 99.5 is the level, closes stay 100; no target); X3 runner: 5m close == EMA9
            tr, _ = V.simulate(X, 'SP', days[1], 100, 1, x)
            assert tr['exit_m'] == 270 and tr['reason'] == '14:00', (x, tr['exit_m'], tr['reason'])
            assert all(px == 2.70 for q, ex, px, w in tr['legs']), tr['legs']
        # a signal every minute from 13:26 → entries at 13:26..13:29 only
        with Patch(V__simulate=lambda X_, st, d, m, side, ex: (dict(m=m, exit_m=m, reason='+1R'), 'ok')):
            old = E.SIGNALS['full']
            E.SIGNALS['full'] = lambda X_, i, m, cfg: 1 if m >= 236 else 0
            try:
                T, _ = V.run_day(X, 'SP', days[1], 'A', 'X1')
            finally:
                E.SIGNALS['full'] = old
        ms = [t['m'] for t in T]
        assert ms == [236, 237, 238, 239], ms                      # signals every minute from 13:26: none from 13:30


def test_chop():
    rng = np.random.default_rng(3)
    closes, opens, highs, lows = [], [], [], []
    for k in range(61):
        c = np.full(NB, 100.0)
        rg = 1.0 + rng.uniform(0, 1) if k < 60 else 0.5             # 60 reference days with ranges 1–2, today 0.5
        h = np.full(NB, 100.0); l_ = np.full(NB, 100.0)
        h[10], l_[20] = 100 + rg / 2, 100 - rg / 2
        closes.append(c); opens.append(c.copy()); highs.append(h); lows.append(l_)
    X, days = toy(closes, opens=opens, highs=highs, lows=lows)
    assert V.chop_day(X, 60)                                          # narrow, 10:30 price (100) mid-range
    assert not V.chop_gate(X, 60, 59) and V.chop_gate(X, 60, 60)
    closes[60] = closes[60].copy(); closes[60][59] = 100.12          # 10:30 price inside the middle half 99.875–100.125
    X, _ = toy(closes, opens=opens, highs=highs, lows=lows)
    assert V.chop_day(X, 60)
    closes[60][59] = 100.13
    X, _ = toy(closes, opens=opens, highs=highs, lows=lows)
    assert not V.chop_day(X, 60)                                      # 100.13 > 99.75 + 0.75 × 0.5 = 100.125
    highs[60] = highs[60].copy(); highs[60][10] = 103.0               # wide first hour → not chop
    closes[60][59] = 100.0
    X, _ = toy(closes, opens=opens, highs=highs, lows=lows)
    assert not V.chop_day(X, 60)


def test_no_lookahead():
    weeks = [tuple(v['days']) for v in json.loads((HERE / 'out_v1' / 'weeks.json').read_text())['picks'].values() if v]
    rng = np.random.default_rng(11)
    checked = 0
    for wk in weeks:
        for st in V.STREAMS:
            base = V.series(st, wk)
            for d in wk:
                i = base.di(d)
                s0 = int(rng.integers(30, 300))
                ov = {}
                for k, dd in enumerate(base.days):
                    b = [base.O[k].copy(), base.H[k].copy(), base.L[k].copy(), base.C[k].copy(), base.V[k].copy()]
                    if k >= i:
                        lo = s0 + 1 if k == i else 0
                        for a in b:
                            a[lo:] = np.nan
                    ov[dd] = tuple(b)
                nwarm = len(base.days) - len(wk)
                Y = E.Series(base.name, days=list(wk), warm=base.days[:nwarm], override=ov)
                for m in range(V.FIRST_M, min(s0 + 1, V.LAST_M) + 1):          # decisions at m read bars <= m - 1 <= s0
                    for cfg in 'AB':
                        for sig in ('full', 'cross', 'align'):
                            assert E.SIGNALS[sig](base, i, m, cfg) == E.SIGNALS[sig](Y, i, m, cfg), (st, d, m, cfg, sig)
                            checked += 1
                    assert V.chop_gate(base, i, m) == V.chop_gate(Y, i, m), (st, d, m)
                    checked += 1
    return checked


if __name__ == '__main__':
    test_veto(); test_venue(); test_flat_and_cut(); test_chop()
    n = test_no_lookahead()
    msg = f'all tests pass (no-lookahead: {n} v1 decisions unchanged with every later bar truncated)'
    (HERE / 'out_v1' / 'tests.txt').write_text(msg + '\n')
    print(msg)
