"""
verify_plain.py — DR-GCE's independent re-derivation (GATE_PREREG.md section 8). Plain Python loops over the raw files
(math only, no numpy in the logic): every bar of each chosen session is rescanned for both modes, the trades rebuilt
(contract, G_max, touch / stop) and compared with dr_gce's out/signals.csv. Shares no function with dr_gce.py.

  python3 verify_plain.py [N_SESSIONS]
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard as G  # noqa: E402

SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
RATE, YEAR_MIN, TRMIN = 0.045, 525600.0, 252 * 390


def N(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def n(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def minute(ts):
    return ts.hour * 60 + ts.minute - 570


def load(d):
    S = [None] * 390
    for ts, p in pl.read_parquet(SP / f'theta/data/index/SPX/{d}.parquet').iter_rows():
        m = minute(ts)
        if 1 <= m <= 390 and p is not None and p == p:
            S[m - 1] = float(p)
    bars = {}
    for row in pl.read_parquet(SP / f'theta/data/underlying/SPY/{d}.parquet').iter_rows(named=True):
        m = minute(row['timestamp'])
        if 0 <= m < 390:
            bars[m] = row
    Q = {}
    for ts, k, r, b, a in pl.read_parquet(SP / f'theta/data_full/chains/SPXW/{d}.parquet',
                                          columns=['timestamp', 'strike', 'right', 'bid', 'ask']).iter_rows():
        m = minute(ts)
        if 0 <= m <= 390:
            Q[(m, float(k), 0 if r == 'CALL' else 1)] = (b, a)
    strikes = sorted({k for (_, k, _) in Q})
    oi = {}
    for sym, v in pl.read_parquet(SP / f'features_data/uw/oi_chain/SPX/{d}.parquet',
                                  columns=['option_symbol', 'open_interest']).iter_rows():
        oi[sym] = v or 0
    return S, bars, Q, strikes, oi


def occ(d, r, k):
    return f'SPXW{d[2:4]}{d[5:7]}{d[8:10]}{"C" if r == 0 else "P"}{int(round(k * 1000)):08d}'


def price(F, K, T, v, call):
    sv = v * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * v * v * T) / sv
    d2 = d1 - sv
    df = math.exp(-RATE * T)
    c = df * (F * N(d1) - K * N(d2))
    return c if call else c - df * (F - K)


def implied(p, F, K, T, call):
    df = math.exp(-RATE * T)
    lo_b = df * max((F - K) if call else (K - F), 0)
    up_b = df * (F if call else K)
    if not (p > lo_b + 1e-12 and p < up_b and T > 0):
        return None
    a, b = 1e-4, 10.0
    for _ in range(60):
        m = 0.5 * (a + b)
        if price(F, K, T, m, call) > p:
            b = m
        else:
            a = m
    return 0.5 * (a + b)


def standing(q):
    if q is None:
        return False
    b, a = q
    return b is not None and a is not None and b == b and a == a and a >= b and b > 0


def forward(Q, strikes, m):
    best = None
    for k in strikes:
        c, p = Q.get((m, k, 0)), Q.get((m, k, 1))
        if standing(c) and standing(p):
            cm, pm = (c[0] + c[1]) / 2, (p[0] + p[1]) / 2
            if best is None or abs(cm - pm) < best[0]:
                best = (abs(cm - pm), k, k + cm - pm, cm + pm)
    if best is None or not best[3] > 0:
        return None
    return best[1], best[2]


def book(d, Q, strikes, oi, m, St):
    fw = forward(Q, strikes, m)
    if fw is None:
        return None
    Ks, F = fw
    T = (390 - m) / YEAR_MIN
    cons = []                                           # (K, sign, oi, iv)
    ivs = {}
    for k in strikes:
        for r in (0, 1):
            q = Q.get((m, k, r))
            if abs(k - St) <= 0.025 * St + 1e-9 and standing(q):
                iv = implied((q[0] + q[1]) / 2, F, k, T, r == 0)
                ivs[(k, r)] = iv
                o = oi.get(occ(d, r, k), 0)
                if iv is not None and o > 0:
                    cons.append((k, 1.0 if r == 0 else -1.0, o, iv))
    xs = [ivs.get((Ks, 0)), ivs.get((Ks, 1))]
    xs = [x for x in xs if x is not None]
    satm = sum(xs) / len(xs) if xs else None

    def gex(x, only=None):
        Fx = x * F / St
        tot = 0.0
        for k, sg, o, iv in cons:
            if only is not None and k != only:
                continue
            sv = iv * math.sqrt(T)
            d1 = (math.log(Fx / k) + 0.5 * iv * iv * T) / sv
            g = math.exp(-RATE * T) * n(d1) / (Fx * sv) * (Fx / x) ** 2
            tot += sg * o * 100 * g * x * x * 0.01
        return tot

    gk = {}
    for k, sg, o, iv in cons:
        gk[k] = gk.get(k, 0.0)
    for k in list(gk):
        gk[k] = gex(St, only=k)
    tot0 = sum(gk.values())
    lo, hi = math.ceil(0.975 * St), math.floor(1.025 * St)
    grid = [float(x) for x in range(lo, hi + 1)]
    gv = [gex(x) for x in grid]
    zs = []
    for i in range(len(grid) - 1):
        if gv[i] == 0:
            zs.append(grid[i])
        elif gv[i] * gv[i + 1] < 0:
            zs.append(grid[i] + abs(gv[i]) / (abs(gv[i]) + abs(gv[i + 1])))
    if zs:
        Z = min(zs, key=lambda z: abs(z - St))
        reg = -1 if St < Z else (1 if St > Z else 0)
    else:
        reg = -1 if tot0 < 0 else (1 if tot0 > 0 else 0)
    pos = {k: v for k, v in gk.items() if v > 0}
    neg = {k: v for k, v in gk.items() if v < 0}
    CW = max(pos, key=pos.get) if pos else None
    PW = min(neg, key=neg.get) if neg else None
    up = {k: v for k, v in pos.items() if k > St}
    dn = {k: v for k, v in neg.items() if k < St}
    CWa = max(up, key=up.get) if up else None
    PWb = min(dn, key=dn.get) if dn else None
    near = [k for k, v in gk.items() if abs(k - St) <= 0.01 * St + 1e-9 and v != 0]
    Mg = max(near, key=lambda k: (abs(gk[k]), -abs(k - St), -k)) if near else None
    return dict(F=F, satm=satm, reg=reg, CW=CW, PW=PW, CWa=CWa, PWb=PWb, Mg=Mg)


def med(xs):
    xs = sorted(xs)
    k = len(xs)
    return xs[k // 2] if k % 2 else 0.5 * (xs[k // 2 - 1] + xs[k // 2])


class Sess:
    def __init__(self, d, prev):
        self.d = d
        self.S, self.bars, self.Q, self.K, self.oi = load(d)
        self.rp = []
        if prev is not None and not G.held_out(prev):
            Sp = load(prev)[0]
            r = []
            for j in range(1, 390):
                a, b = Sp[j - 1], Sp[j]
                r.append(math.log(b / a) if (a is not None and b is not None) else None)
            self.rp = r[-60:]
        self.cache = {}
        num = den = 0.0
        self.vw = []
        for t in range(390):
            b = self.bars.get(t)
            if b and None not in (b['high'], b['low'], b['close'], b['volume']):
                num += (b['high'] + b['low'] + b['close']) / 3 * b['volume']
                den += b['volume']
            c = b['close'] if b else None
            self.vw.append(num / den * self.S[t] / c if (den > 0 and c and self.S[t] is not None) else None)

    def ret(self, j):
        a, b = self.S[j - 1], self.S[j]
        return math.log(b / a) if (a is not None and b is not None) else None

    def sigma(self, t):
        today = [self.ret(j) for j in range(1, t + 1)]
        w = (self.rp + today)[-60:] if len(today) < 60 else today[-60:]
        if len(w) < 60:
            return None
        w = [x for x in w if x is not None]
        if len(w) < 50:
            return None
        m = med(w)
        v = 1.4826 * med([abs(x - m) for x in w])
        return v if v > 0 else None

    def zvel(self, t):
        s = self.sigma(t)
        if t < 3 or s is None or self.S[t] is None or self.S[t - 3] is None:
            return None
        return math.log(self.S[t] / self.S[t - 3]) / (math.sqrt(3) * s)

    def bk(self, t):
        if t not in self.cache:
            self.cache[t] = book(self.d, self.Q, self.K, self.oi, t + 1, self.S[t]) if self.S[t] is not None else None
        return self.cache[t]

    def vr(self, t, b):
        s = self.sigma(t)
        if b is None or s is None or b['satm'] is None:
            return None
        return b['satm'] * math.sqrt(TRMIN / YEAR_MIN) / (s * math.sqrt(TRMIN))


def m1(X, t):
    if not ((15 <= t <= 135) or (240 <= t <= 345)):
        return 0
    z = X.zvel(t)
    if z is None or abs(z) < 2.60 - 1e-12:
        return 0
    St, vw = X.S[t], X.vw[t]
    if St is None or vw is None:
        return 0
    side = 1 if (z >= 2.6 and St > vw) else (-1 if (z <= -2.6 and St < vw) else 0)
    if not side:
        return 0
    vs = [X.bars[j]['volume'] for j in range(max(0, t - 30), t) if j in X.bars and X.bars[j]['volume'] is not None]
    if t < 15 or len(vs) < 15 or t not in X.bars or X.bars[t]['volume'] is None:
        return 0
    if X.bars[t]['volume'] < 1.8 * med(vs) - 1e-9:
        return 0
    b = X.bk(t)
    if b is None or b['reg'] != -1:
        return 0
    v = X.vr(t, b)
    if v is None or v > 1.18 + 1e-12:
        return 0
    w = b['CWa'] if side > 0 else b['PWb']
    dist = abs(w - St) if w is not None else 0.025 * St
    if dist < 4.5 * math.sqrt(5) * X.sigma(t) * St - 1e-9:
        return 0
    return side


def m2(X, t):
    if t < 1:
        return 0
    u = t - 1
    if not (30 <= u <= 315):
        return 0
    s, St, vw = X.sigma(u), X.S[u], X.vw[u]
    if s is None or St is None or vw is None or St == vw:
        return 0
    if abs(St - vw) / (s * St * math.sqrt(u + 1)) < 2.80 - 1e-12:
        return 0
    b = X.bk(u)
    if b is None or b['reg'] != 1:
        return 0
    if not any(w is not None and abs(St - w) <= 0.0015 * St + 1e-9 for w in (b['CW'], b['PW'])):
        return 0
    v = X.vr(u, b)
    if v is None or v > 1.18 + 1e-12:
        return 0
    side = -1 if St > vw else 1
    pb, cb = X.bars.get(u), X.bars.get(t)
    if not pb or not cb or None in (pb['open'], pb['close'], cb['close']):
        return 0
    if not (min(pb['open'], pb['close']) < cb['close'] < max(pb['open'], pb['close'])):
        return 0
    z = X.zvel(t)
    if z is None or not z * side > 0:
        return 0
    return side


def trade(X, mode, s, bb, side):
    m = s + 1
    sig, St = X.sigma(s), X.S[s]
    if sig is None or St is None:
        return None
    b = X.bk(bb)
    if b is None:
        return None
    fw = forward(X.Q, X.K, m)
    if fw is None:
        return None
    F = fw[1]
    T = (390 - m) / YEAR_MIN
    r = 0 if side > 0 else 1
    best = None
    dS = 3 * sig * St
    for k in X.K:
        q = X.Q.get((m, k, r))
        if not standing(q):
            continue
        bid, ask = q
        iv = implied((bid + ask) / 2, F, k, T, side > 0)
        if iv is None:
            continue
        sv = iv * math.sqrt(T)
        d1 = (math.log(F / k) + 0.5 * iv * iv * T) / sv
        df = math.exp(-RATE * T)
        dl = df * (N(d1) if side > 0 else N(d1) - 1) * F / St
        gm = df * n(d1) / (F * sv) * (F / St) ** 2
        if not (0.40 - 1e-12 <= abs(dl) <= 0.54 + 1e-12) or (ask - bid) / ask > 0.035 + 1e-12:
            continue
        T5 = max(T - 5 / YEAR_MIN, 0)
        v5 = price(F, k, T5, iv, side > 0) if T5 > 0 else max((F - k) if side > 0 else (k - F), 0)
        th = abs(price(F, k, T, iv, side > 0) - v5)
        ck = (abs(dl) * dS + 0.5 * gm * dS * dS) / (th + (ask - bid))
        key = (round(ck, 12), -abs(k - F), -k)
        if best is None or key > best[0]:
            best = (key, k, bid, ask, dl, gm)
    if best is None:
        return None
    _, k, bid, ask, dl, gm = best
    Sb = X.S[bb]
    w = (b['CWa'] if side > 0 else b['PWb']) if mode == 1 else (b['CW'] if side > 0 else b['PW'])
    c = [x for x in (b['Mg'], w) if x is not None and (x - Sb) * side > 0]
    mv = min(abs(x - Sb) for x in c) if c else 0.025 * Sb
    gmax = (abs(dl) * mv + 0.5 * gm * mv * mv) / ask
    stop = 0.76 if gmax >= 0.85 else 0.82
    res, last = (0, 'none'), min(m + 4, 390)
    for j in range(m + 1, min(m + 4, 390) + 1):
        q = X.Q.get((j, k, r))
        bj = q[0] if q else None
        if bj is None or bj != bj:
            continue
        if bj <= stop * ask + 1e-9:
            res, last = (0, 'stop'), j
            break
        if bj >= 1.18 * ask - 1e-9:
            res, last = (1, 'touch'), j
            break
    return dict(mode=mode, sbar=s, side=side, K=k, ask=ask, touch=res[0], how=res[1], last=last, stop=stop)


def scan(d, prev):
    X = Sess(d, prev)
    out = []
    for mode, fn in ((1, m1), (2, m2)):
        free = -1
        for t in range(385):
            side = fn(X, t)
            if not side or t + 1 <= free:
                continue
            tr = trade(X, mode, t, t if mode == 1 else t - 1, side)
            if tr is None:
                continue
            out.append(tr)
            free = tr['last']
    return out


def main():
    import dr_gce as D                                       # the calendar and the engine's rows, for the comparison only
    rows = list(csv.DictReader(open(HERE / 'out' / 'signals.csv')))
    by = {}
    for r in rows:
        by.setdefault(r['d'], []).append(r)
    days = sorted(by)
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    step = max(1, len(days) // want)
    pick = days[::step][:want]
    # add sessions until >= 20 signals are covered
    i = 0
    while sum(len(by[d]) for d in pick) < 20 and i < len(days):
        if days[i] not in pick:
            pick.append(days[i])
        i += 1
    quiet = [d for d in D.sessions() if d not in by][::60][:6]       # sessions the engine found nothing on
    diffs, nsig = [], 0
    for d in sorted(pick + quiet):
        mine = scan(d, D.prev_tday(d))
        eng = sorted(by.get(d, []), key=lambda r: (int(r['mode']), int(r['sbar'])))
        mine = sorted(mine, key=lambda r: (r['mode'], r['sbar']))
        nsig += len(eng)
        if len(mine) != len(eng):
            diffs.append((d, 'count', len(mine), len(eng)))
            continue
        for a, b in zip(mine, eng):
            for f in ('mode', 'sbar', 'side', 'touch', 'last'):
                if int(a[f]) != int(b[f]):
                    diffs.append((d, f, a[f], b[f]))
            for f in ('K', 'ask', 'stop'):
                if abs(float(a[f]) - float(b[f])) > 1e-9:
                    diffs.append((d, f, a[f], b[f]))
            if a['how'] != b['how']:
                diffs.append((d, 'how', a['how'], b['how']))
    print(f'verify_plain: {len(pick)} sessions with signals + {len(quiet)} without rescanned bar by bar, {nsig} signals re-derived, {len(diffs)} differences')
    for x in diffs[:20]:
        print('  ', x)


if __name__ == '__main__':
    main()
