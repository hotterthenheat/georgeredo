"""verify_targets.py — plain-loop re-derivation of sampled trades of the "nearest EMA" rule (RULE_EMA_TARGETS.md).

No numpy, no ema_lib / scanner_lib code: the raw Parquet rows are read with polars into Python lists and everything after
that is plain loops (the mid chart, the carried mid, the EMAs on 1/5/15/30-minute candles, the break, the ATM strike, the
target, the cost check, the E1 veto or the E2 best-R/R pick with its own Black-Scholes and bisection, the exit, the bid
fallback, the fees). Each sampled trade's whole name-session is replayed from 09:45 so the position state is re-derived too.
PREVIEW — one month each, no verdict.
"""
import json
import math
import os
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
HELD = set('''2017-06 2017-09 2017-10 2018-01 2019-07 2019-08 2020-06 2020-08 2020-11 2020-12 2021-01 2021-03 2021-05 2021-11
2022-04 2022-12 2023-05 2023-11 2024-05 2024-06 2024-07 2024-08 2024-11 2025-08 2025-11 2026-03 2026-04 2026-08'''.split())
FEE, RATE, NAN = 0.68748, 0.045, float('nan')


def fin(x):
    return x is not None and x == x


def minute(ts):
    return ts.hour * 60 + ts.minute - 570


def load(name, d):
    assert d[:7] not in HELD
    bars = pl.read_parquet(SP / 'theta' / 'data' / 'underlying' / name / f'{d}.parquet',
                           columns=['timestamp', 'open', 'high', 'low', 'close']).rows()
    close = {}
    for ts, o, h, l, c in bars:
        k = minute(ts)
        if 0 <= k < 390 and fin(c) and o is not None and h is not None and l is not None:
            close[k] = c
    spot = [NAN] * 391
    last = NAN
    for m in range(1, 391):
        if (m - 1) in close:
            last = close[m - 1]
        spot[m] = last
    rows = pl.read_parquet(SP / 'theta' / 'data_full' / 'chains' / name / f'{d}.parquet',
                           columns=['timestamp', 'strike', 'right', 'bid', 'ask']).rows()
    q = {}
    strikes = set()
    for ts, k, rt, b, a in rows:
        m = minute(ts)
        if 0 <= m <= 390:
            strikes.add(k)
            q[(m, float(k), 0 if rt == 'CALL' else 1)] = (NAN if b is None else float(b), NAN if a is None else float(a))
    return spot, q, sorted(float(k) for k in strikes)


class Chart:
    """one contract's carried-mid chart and its EMA 9 on each timeframe"""
    def __init__(self, q, k, r):
        self.mid = [NAN] * 391
        self.cm = [NAN] * 391
        last = NAN
        for m in range(391):
            b, a = q.get((m, k, r), (NAN, NAN))
            if fin(b) and fin(a) and b > 0 and a >= b:
                self.mid[m] = 0.5 * (b + a)
                last = self.mid[m]
            self.cm[m] = last
        al = 2.0 / 10
        self.ema, self.brk, self.below = {}, {}, {}
        for tf in (1, 5, 15, 30):
            e = NAN
            val = [NAN] * 391
            prev_above, have_prev = False, False
            br = [False] * 391
            bl = [False] * 391
            for m in range(391):
                if m >= tf and m % tf == 0 and m < 390 and fin(self.cm[m]):
                    c = self.cm[m]
                    e = c if not fin(e) else al * c + (1 - al) * e
                    ab = c > e
                    br[m] = ab and have_prev and not prev_above
                    bl[m] = c < e
                    prev_above, have_prev = ab, True
                val[m] = e
            self.ema[tf], self.brk[tf], self.below[tf] = val, br, bl


def ncdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def bs(S, K, T, v, call):
    sv = v * math.sqrt(T)
    d1 = (math.log(S / K) + (RATE + 0.5 * v * v) * T) / sv
    d2 = d1 - sv
    df = math.exp(-RATE * T)
    c = S * ncdf(d1) - K * df * ncdf(d2)
    return c if call else c - S + K * df


def ivd(price, S, K, T, call):
    df = math.exp(-RATE * T)
    lo_b = max(S - K * df, 0) if call else max(K * df - S, 0)
    up_b = S if call else K * df
    if not (fin(price) and price > lo_b + 1e-12 and price < up_b and T > 0):
        return NAN, NAN
    a, b = 1e-4, 10.0
    for _ in range(80):
        mm = 0.5 * (a + b)
        if bs(S, K, T, mm, call) > price:
            b = mm
        else:
            a = mm
    v = 0.5 * (a + b)
    d1 = (math.log(S / K) + (RATE + 0.5 * v * v) * T) / (v * math.sqrt(T))
    return v, abs(ncdf(d1) if call else ncdf(d1) - 1.0)


def day(name, d, ver):
    spot, q, K = load(name, d)
    charts = {}

    def ch(k, r):
        if (k, r) not in charts:
            charts[(k, r)] = Chart(q, k, r)
        return charts[(k, r)]

    def bid_at(x, k, r, field):
        for mm in range(x, max(-1, x - 11), -1):
            if field == 'bid':
                v = q.get((mm, k, r), (NAN, NAN))[0]
            else:
                v = ch(k, r).mid[mm]
            if fin(v):
                return max(0.0, v)
        return 0.0

    out = []
    m = 15
    while m <= 360:
        s = spot[m]
        if not fin(s):
            m += 1
            continue
        k = min(K, key=lambda z: (abs(z - s), z))
        qual = []
        for r in (0, 1):
            c = ch(k, r)
            if not c.brk[1][m]:
                continue
            ab = [c.ema[tf][m] for tf in (5, 15, 30) if fin(c.ema[tf][m]) and c.ema[tf][m] > c.cm[m]]
            if ab:
                qual.append((r, min(ab)))
        if len(qual) != 1:
            m += 1
            continue
        r, T = qual[0]
        b0, a0 = q.get((m, k, r), (NAN, NAN))
        if not (fin(b0) and fin(a0) and a0 > b0 > 0) or not (T - 0.5 * (a0 + b0) >= a0 - b0):
            m += 1
            continue
        tau = (390 - m) / 525600.0
        if ver == 'E1':
            if (a0 - b0) / (0.5 * (a0 + b0)) > 0.03 + 1e-12:
                m += 1
                continue
            kx = k
            de = ivd(0.5 * (a0 + b0), s, k, tau, r == 0)[1]
        else:
            M = ch(k, 0).cm[m] + ch(k, 1).cm[m]
            if not fin(M):
                m += 1
                continue
            best = None
            for kk in K:
                b, a = q.get((m, kk, r), (NAN, NAN))
                if not (fin(b) and fin(a) and a > b and b > 0):
                    continue
                mid = 0.5 * (a + b)
                sp = (a - b) / mid
                if sp > 0.03 + 1e-12:
                    continue
                iv, dl = ivd(mid, s, kk, tau, r == 0)
                if not (fin(dl) and 0.15 <= dl <= 0.50):
                    continue
                rr = (bs(s + M if r == 0 else s - M, kk, tau, iv, r == 0) - a) / a
                key = (-rr, sp, abs(kk - s), kk)
                if best is None or key < best[0]:
                    best = (key, kk, dl)
            if best is None:
                m += 1
                continue
            kx, de = best[1], best[2]
        a_in = q[(m, kx, r)][1]
        x, why = 388, '15:58'
        c = ch(k, r)
        for cc in range(m + 1, 389):
            if c.cm[cc] >= T:
                x, why = cc, 'target'
                break
            if c.below[1][cc]:
                x, why = cc, 'stop'
                break
        bo = bid_at(x, kx, r, 'bid')
        usd = (bo - a_in) * 100 - FEE - (FEE if bo > 0 else 0.0)
        out.append(dict(m=m, side='C' if r == 0 else 'P', k_sig=k, k_ex=kx, T=T, delta=de, ask=a_in, x=x, why=why,
                        bid_out=bo, usd=usd))
        m = x + 1
    return out


def same(a, b, tol=1e-6):
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    if not fin(a) and not fin(b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


if __name__ == '__main__':
    total = diffs = days_same = 0
    for mo in ('2025-02', '2025-03'):
        J = json.load(open(HERE / 'out' / f'targets_{mo}.json'))
        picks = []
        for ver in ('E1', 'E2'):
            T = J[ver]['trades']
            for why, n in (('target', 3), ('stop', 2)):
                g = [t for t in T if t['why'] == why]
                picks += [g[round(j * (len(g) - 1) / (n - 1))] for j in range(n)]
        for t in picks:
            full = day(t['name'], t['date'], t['ver'])
            eng = [(u['m'], u['x'], u['why']) for u in J[t['ver']]['trades'] if u['name'] == t['name'] and u['date'] == t['date']]
            days_same += [(u['m'], u['x'], u['why']) for u in full] == eng
            got = [u for u in full if u['m'] == t['m']]
            bad = ['no trade at m'] if len(got) != 1 else [f for f in ('side', 'k_sig', 'k_ex', 'T', 'delta', 'ask', 'x', 'why',
                                                                       'bid_out', 'usd') if not same(t[f], got[0][f])]
            total += 1
            diffs += bool(bad)
            print(mo, t['ver'], t['name'], t['date'], f"m={t['m']}", t['side'], t['why'], f"x={t['x']}",
                  f"usd={t['usd']:+.4f}", 'OK' if not bad else f'DIFF {bad}')
    print(f'{total} trades re-derived, {diffs} with differences; the whole name-session trade list (entry, exit, reason) '
          f'equal on {days_same} of {total} replayed sessions')
