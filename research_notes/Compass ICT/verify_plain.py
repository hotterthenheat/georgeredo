"""
verify_plain.py — re-derives v0 (and the no-bias and no-killzone ablations, which share its sweep path) on the ten preview
sessions with plain Python loops and lists, written apart from ict.py (only the file reading is shared in kind: polars to
lists). Compares every candidate setup and every trade figure; prints the differences (0 required).
"""
from __future__ import annotations

import math
import os
import statistics
from pathlib import Path

import polars as pl

import ict

SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
TH = SP / 'theta'
NAN = float('nan')


def mins(ts):
    return [t.hour * 60 + t.minute - 570 for t in ts]


def read_spx(d):
    x = pl.read_parquet(TH / 'data' / 'index' / 'SPX' / f'{d}.parquet').to_dict(as_series=False)
    a = [NAN] * 391
    for m, p in zip(mins(x['timestamp']), x['price']):
        if 0 <= m <= 390 and p is not None:
            a[m] = p
    return a


def read_spy(d):
    x = pl.read_parquet(TH / 'data' / 'underlying' / 'SPY' / f'{d}.parquet').to_dict(as_series=False)
    o, h, l_, c = ([NAN] * 390 for _ in range(4))
    for i, m in enumerate(mins(x['timestamp'])):
        if 0 <= m < 390:
            o[m], h[m], l_[m], c[m] = x['open'][i], x['high'][i], x['low'][i], x['close'][i]
    return o, h, l_, c


def read_chain(d):
    x = pl.read_parquet(TH / 'data_full' / 'chains' / 'SPXW' / f'{d}.parquet').to_dict(as_series=False)
    q = {}
    for ts, k, r, b, a in zip(x['timestamp'], x['strike'], x['right'], x['bid'], x['ask']):
        m = ts.hour * 60 + ts.minute - 570
        q[(m, k, 0 if r == 'CALL' else 1)] = (b, a)
    return q, sorted(set(x['strike']))


def fin(v):
    return v is not None and v == v


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def b76(F, K, T, v, call):
    sv = v * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sv * sv) / sv
    c = F * ncdf(d1) - K * ncdf(d1 - sv)
    return c if call else c - (F - K)


def delta(price, F, K, T, call):
    intr = max(F - K, 0) if call else max(K - F, 0)
    if not (price > intr + 1e-12 and price < (F if call else K)):
        return None
    lo, hi = 1e-4, 8.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if b76(F, K, T, mid, call) > price:
            hi = mid
        else:
            lo = mid
    v = 0.5 * (lo + hi)
    d1 = (math.log(F / K) + 0.5 * v * v * T) / (v * math.sqrt(T))
    return abs(ncdf(d1) if call else ncdf(d1) - 1)


def forward(q, Ks, m):
    best = None
    for k in Ks:
        cb, ca = q.get((m, k, 0), (None, None))
        pb, pa = q.get((m, k, 1), (None, None))
        if not all(fin(v) for v in (cb, ca, pb, pa)):
            continue
        if cb > 0 and ca > 0 and ca >= cb and pb > 0 and pa > 0 and pa >= pb:
            cm, pm = (cb + ca) / 2, (pb + pa) / 2
            if best is None or abs(cm - pm) < best[0]:
                best = (abs(cm - pm), k, k + cm - pm, cm + pm)
    return best


def run(d, use_bias=True, kz_all=False):
    days = sorted(p.stem for p in (TH / 'data' / 'index' / 'SPX').glob('*.parquet'))
    p = days[days.index(d) - 1]
    spx, spxp = read_spx(d), read_spx(p)
    o, h, l_, c = read_spy(d)
    po, ph, pl_, pc = read_spy(p)
    R, Rp = spx[1] / c[0], spxp[1] / pc[0]
    PDH, PDL = max(v for v in ph if fin(v)) * R, min(v for v in pl_ if fin(v)) * R
    # the bias
    hd = [x for x in days if '2026-09-01' <= x < d]
    DH, DL, DC = [], [], []
    for x in hd:
        a = [v for v in read_spx(x)[1:] if fin(v)]
        DH.append(max(a)); DL.append(min(a)); DC.append(read_spx(x)[390])
    bias = 0
    for k in range(len(hd)):
        sh = [j for j in range(2, len(hd)) if j + 2 <= k and DH[j] >= max(DH[j - 2], DH[j - 1], DH[j + 1], DH[j + 2])]
        sl = [j for j in range(2, len(hd)) if j + 2 <= k and DL[j] <= min(DL[j - 2], DL[j - 1], DL[j + 1], DL[j + 2])]
        up = len(sh) > 0 and DC[k] > DH[sh[-1]]
        dn = len(sl) > 0 and DC[k] < DL[sl[-1]]
        if up and not dn:
            bias = 1
        if dn and not up:
            bias = -1
    O = [v * Rp for v in po] + [v * R for v in o]
    H = [v * Rp for v in ph] + [v * R for v in h]
    L = [v * Rp for v in pl_] + [v * R for v in l_]
    C = [v * Rp for v in pc] + [v * R for v in c]
    P, n = 390, 780

    def swing(x, kind):
        if x < 2 or x + 2 >= n or not all(fin(H[i]) for i in range(x - 2, x + 3)):
            return False
        if kind == 'h':
            return all(H[x] >= H[i] for i in range(x - 2, x + 3))
        return all(L[x] <= L[i] for i in range(x - 2, x + 3))

    def last_swing(kind, last, below=None, above=None):
        x = last - 2
        while x > 1:
            v = H[x] if kind == 'h' else L[x]
            if swing(x, kind) and (below is None or v < below) and (above is None or v > above):
                return v
            x -= 1
        return None

    def kz(t):
        if kz_all:
            return 5 <= t + 1 <= 360
        return t < 90 or 270 <= t < 330

    setups = []
    if use_bias and bias == 0:
        return setups, [], bias
    for lvl, side in ((PDH, -1), (PDL, 1)):
        if use_bias and side != bias:
            continue
        s = P
        while s < n:
            if not fin(C[s]):
                s += 1
                continue
            hit = H[s] >= lvl * 1.0002 if side < 0 else L[s] <= lvl * 0.9998
            if not hit:
                s += 1
                continue
            k = None
            for kk in range(s, min(s + 6, n)):
                if fin(C[kk]) and ((C[kk] < lvl) if side < 0 else (C[kk] > lvl)):
                    k = kk
                    break
            if k is None:
                s += 1
                continue
            seg = [H[i] if side < 0 else L[i] for i in range(s, k + 1) if fin(H[i])]
            ext = max(seg) if side < 0 else min(seg)
            jj = None
            for j in range(k, min(k + 16, n - 1)):
                if not (fin(O[j]) and fin(C[j])) or (C[j] - O[j]) * side <= 0:
                    continue
                bodies = [abs(C[i] - O[i]) for i in range(max(0, j - 20), j) if fin(C[i]) and fin(O[i])]
                if not bodies or abs(C[j] - O[j]) < 1.5 * statistics.median(bodies) - 1e-12:
                    continue
                sw = last_swing('l' if side < 0 else 'h', j)
                if sw is not None and ((C[j] < sw) if side < 0 else (C[j] > sw)):
                    jj = j
                    break
            if jj is not None:
                j = jj
                if side < 0 and L[j - 1] > H[j + 1]:
                    zone = (H[j + 1], L[j - 1])
                elif side > 0 and H[j - 1] < L[j + 1]:
                    zone = (H[j - 1], L[j + 1])
                else:
                    zone = None
                if zone is not None:
                    t0 = j - P + 2
                    for t in range(t0, min(t0 + 30, 390)):
                        if fin(c[t]) and ((H[P + t] >= zone[0]) if side < 0 else (L[P + t] <= zone[1])) and kz(t):
                            setups.append((t, side, ext, j - P, zone))
                            break
            s = k + 1
    setups.sort(key=lambda a: (a[0], a[3]))
    q, Ks = read_chain(d)
    trades, last = [], -1
    for t, side, ext, j, zone in setups:
        if t + 1 <= last or len(trades) >= 2:
            continue
        m = t + 1
        fw = forward(q, Ks, m)
        if fw is None:
            continue
        F, r = fw[2], 0 if side > 0 else 1
        cands = []
        for k in Ks:
            b, a = q.get((m, k, r), (None, None))
            if not (fin(b) and fin(a) and a > b and b > 0):
                continue
            mid = (a + b) / 2
            spr = (a - b) / mid
            dl = delta(mid, F, k, (390 - m) / 525600.0, side > 0)
            if spr <= 0.10 + 1e-12 and dl is not None and 0.45 - 1e-12 <= dl <= 0.60 + 1e-12:
                cands.append((round(abs(dl - 0.5), 12), spr, k, a, b))
        if not cands:
            continue
        _, spr, K, ask, bid = min(cands)
        eu = C[P + t]
        tp1 = last_swing('l' if side < 0 else 'h', P + (t + 1) - 1, below=eu if side < 0 else None, above=eu if side > 0 else None)
        tp2 = PDL if side < 0 else PDH
        if (side < 0 and eu <= tp2) or (side > 0 and eu >= tp2):
            tp2 = None
        stop, qty, legs, done1 = ext, 2, [], False
        for u in range(t + 1, 388):
            if not fin(c[u]):
                continue
            Hu, Lu, Cu = H[P + u], L[P + u], C[P + u]
            if tp1 is not None and not done1 and ((Lu <= tp1) if side < 0 else (Hu >= tp1)):
                nn = qty if tp2 is None else 1
                legs.append((nn, u + 1)); qty -= nn; done1 = True; stop = eu
            if qty and tp2 is not None and ((Lu <= tp2) if side < 0 else (Hu >= tp2)):
                legs.append((qty, u + 1)); qty = 0
            if qty and ((Cu > stop) if side < 0 else (Cu < stop)):
                legs.append((qty, u + 1)); qty = 0
            if not qty:
                break
        if qty:
            legs.append((qty, 388))
        net = 0.0
        fees = 2 * (1.18748 if ask < 1 else 1.27748)
        ex_m = 0
        for nn, e in legs:
            px = 0.0
            for mm in range(e, max(-1, e - 11), -1):
                b2 = q.get((mm, K, r), (None, None))[0]
                if fin(b2):
                    px = max(0.0, b2)
                    break
            net += nn * (px - ask) * 100
            fees += nn * ((1.18748 if px < 1 else 1.27748) if px > 0 else 0)
            ex_m = max(ex_m, e)
        trades.append((d, t, side, round(ext, 6), K, ask, ex_m, round(net - fees, 6)))
        last = ex_m
    return setups, trades, bias


def main():
    diffs, nset, ntr, nnt = 0, 0, 0, 0
    for name, kw in (('v0', {}), ('A no HTF bias', {'use_bias': False}), ('A no killzones', {'kz_all': True})):
        for d in ict.DAYS:
            S, T, _ = run(d, **kw)
            tr, why, S2, D, B = ict.run_day(d, ict.VARIANTS[name])
            a = [(s[0], s[1], round(s[2], 6), s[3], tuple(round(z, 6) for z in s[4])) for s in S]
            b = [(s['t'], s['side'], round(s['ext'], 6), s['j'], tuple(round(z, 6) for z in s['zone'])) for s in S2]
            ta = T
            tb = [(t['day'], t['t'], t['side'], round(t['ext'], 6), t['K'], t['ask'], t['exit_m'], round(t['net'], 6)) for t in tr]
            if a != b:
                diffs += 1
                print('SETUP DIFF', name, d, a, b)
            if ta != tb:
                diffs += 1
                print('TRADE DIFF', name, d, ta, tb)
            nset += len(a)
            ntr += len(ta)
            nnt += (name == 'v0' and not ta)
    print(f'compared {nset} setups and {ntr} trades (v0 no-trade sessions {nnt}); differences: {diffs}')


if __name__ == '__main__':
    main()
