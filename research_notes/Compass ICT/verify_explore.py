"""
verify_explore.py — integrity (prereg section 5's checks, at the exploration's scale): re-derives v0 on exploration
sessions from the raw files with plain Python loops and lists, written apart from ict.py / explore.py (its own readers,
held-out test, HTF history, daily swings, sweeps, displacement + MSS, FVG, entry, picker with Black-76 on math.erf,
exits, fees, the underlying's return). Compares, per setup: the sweep bar, the sweep's extreme, the displacement bar,
the FVG zone, the entry minute; per trade: the strike, the ask, every exit leg (size, minute, bid, reason), net, bp;
per no-trade session: no trade, the HTF bias and the furthest stage reached. 0 differences required.

    python verify_explore.py        # every v0 trade session + 40 seeded no-trade sessions
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics
import multiprocessing as mp
from pathlib import Path

os.environ.setdefault('POLARS_MAX_THREADS', '1')
import guard  # noqa: E402  (the held-out guard wraps every read below too)
import polars as pl  # noqa: E402

SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
TH = SP / 'theta'
HERE = Path(__file__).resolve().parent
NAN = float('nan')
HELD = ('2017-06 2017-09 2017-10 2018-01 2019-07 2019-08 2020-06 2020-08 2020-11 2020-12 2021-01 2021-03 2021-05 2021-11 '
        '2022-04 2022-12 2023-05 2023-11 2024-05 2024-06 2024-07 2024-08 2024-11 2025-08 2025-11 2026-03 2026-04 2026-08').split()


def held(d):
    return d < '2022-05-13' or d[:7] in HELD


def fin(v):
    return v is not None and v == v


def mins(ts):
    return [t.hour * 60 + t.minute - 570 for t in ts]


_spx = {}


def read_spx(d):
    if d not in _spx:
        x = pl.read_parquet(TH / 'data' / 'index' / 'SPX' / f'{d}.parquet').to_dict(as_series=False)
        a = [NAN] * 391
        for m, p in zip(mins(x['timestamp']), x['price']):
            if 0 <= m <= 390 and p is not None:
                a[m] = p
        _spx[d] = a
    return _spx[d]


def read_spy(d):
    x = pl.read_parquet(TH / 'data' / 'underlying' / 'SPY' / f'{d}.parquet').to_dict(as_series=False)
    o, h, l_, c = ([NAN] * 390 for _ in range(4))
    for i, m in enumerate(mins(x['timestamp'])):
        if 0 <= m < 390:
            for arr, col in ((o, 'open'), (h, 'high'), (l_, 'low'), (c, 'close')):
                v = x[col][i]
                arr[m] = NAN if v is None else v
    return o, h, l_, c


def read_chain(d):
    x = pl.read_parquet(TH / 'data_full' / 'chains' / 'SPXW' / f'{d}.parquet').to_dict(as_series=False)
    q = {}
    for ts, k, r, b, a in zip(x['timestamp'], x['strike'], x['right'], x['bid'], x['ask']):
        m = ts.hour * 60 + ts.minute - 570
        q[(m, k, 0 if r == 'CALL' else 1)] = (b, a)
    return q, sorted(set(x['strike']))


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def b76(F, K, T, v, call):
    sv = v * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sv * sv) / sv
    c = F * ncdf(d1) - K * ncdf(d1 - sv)
    return c if call else c - (F - K)


def delta(price, F, K, T, call):
    intr = max(F - K, 0) if call else max(K - F, 0)
    if not (price > intr + 1e-12 and price < (F if call else K) and T > 0):
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


def fee(px):
    return 0.0 if not px > 0 else (1.18748 if px < 1 else 1.27748)


def bias_of(d, days):
    """HTF bias: daily SPX bars from prints over the readable run of days just before d"""
    i = days.index(d) - 1
    hd = []
    while i >= 0 and not held(days[i]):
        hd.insert(0, days[i])
        i -= 1
    DH, DL, DC = [], [], []
    for x in hd:
        a = [v for v in read_spx(x)[1:] if fin(v)]
        DH.append(max(a))
        DL.append(min(a))
        DC.append(read_spx(x)[390])
    bias = 0
    for k in range(len(hd)):
        sh = [j for j in range(2, len(hd) - 2) if j + 2 <= k and DH[j] >= max(DH[j - 2], DH[j - 1], DH[j + 1], DH[j + 2])]
        sl = [j for j in range(2, len(hd) - 2) if j + 2 <= k and DL[j] <= min(DL[j - 2], DL[j - 1], DL[j + 1], DL[j + 2])]
        up = len(sh) > 0 and DC[k] > DH[sh[-1]]
        dn = len(sl) > 0 and DC[k] < DL[sl[-1]]
        if up and not dn:
            bias = 1
        if dn and not up:
            bias = -1
    return bias


def run(d):
    days = sorted(p.stem for p in (TH / 'data' / 'index' / 'SPX').glob('*.parquet'))
    p = days[days.index(d) - 1]
    assert not held(d) and not held(p)
    spx, spxp = read_spx(d), read_spx(p)
    o, h, l_, c = read_spy(d)
    po, ph, pl_, pc = read_spy(p)
    R, Rp = spx[1] / c[0], spxp[1] / pc[0]
    PDH, PDL = max(v for v in ph if fin(v)) * R, min(v for v in pl_ if fin(v)) * R
    bias = bias_of(d, days)
    O = [v * Rp for v in po] + [v * R for v in o]
    H = [v * Rp for v in ph] + [v * R for v in h]
    L = [v * Rp for v in pl_] + [v * R for v in l_]
    C = [v * Rp for v in pc] + [v * R for v in c]
    P, n = 390, 780
    stage = []

    def swing(x, kind):
        if x < 2 or x + 2 >= n or not all(fin(H[i]) for i in range(x - 2, x + 3)):
            return False
        return all(H[x] >= H[i] for i in range(x - 2, x + 3)) if kind == 'h' else all(L[x] <= L[i] for i in range(x - 2, x + 3))

    def last_swing(kind, last, below=None, above=None):
        x = last - 2
        while x > 1:
            v = H[x] if kind == 'h' else L[x]
            if swing(x, kind) and (below is None or v < below) and (above is None or v > above):
                return v
            x -= 1
        return None

    setups = []
    if bias == 0:
        return dict(bias=0, setups=[], trades=[], stage='no HTF bias')
    lvl, side = (PDH, -1) if bias < 0 else (PDL, 1)
    s = P
    while s < n:
        if not fin(C[s]) or not (H[s] >= lvl * 1.0002 if side < 0 else L[s] <= lvl * 0.9998):
            s += 1
            continue
        stage.append(2)
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
        if jj is None:
            stage.append(3)
        else:
            j = jj
            if side < 0 and L[j - 1] > H[j + 1]:
                zone = (H[j + 1], L[j - 1])
            elif side > 0 and H[j - 1] < L[j + 1]:
                zone = (H[j - 1], L[j + 1])
            else:
                zone = None
            if zone is None:
                stage.append(4)
            else:
                t0, got = j - P + 2, None
                for t in range(t0, min(t0 + 30, 390)):
                    if fin(c[t]) and ((H[P + t] >= zone[0]) if side < 0 else (L[P + t] <= zone[1])) and (t < 90 or 270 <= t < 330):
                        got = t
                        break
                if got is None:
                    stage.append(5)
                else:
                    setups.append(dict(t=got, side=side, ext=ext, s=s - P, j=j - P, zone=zone))
        s = k + 1
    setups.sort(key=lambda a: (a['t'], a['j']))
    q, Ks = read_chain(d)
    trades, last = [], -1
    for st in setups:
        t, side, ext = st['t'], st['side'], st['ext']
        if t + 1 <= last or len(trades) >= 2:
            stage.append(6)
            continue
        m = t + 1
        fw = forward(q, Ks, m)
        r = 0 if side > 0 else 1
        cands = []
        if fw is not None:
            F = fw[2]
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
            stage.append(7)
            continue
        _, spr, K, ask, bid = min(cands)
        eu = C[P + t]
        tp1 = last_swing('l' if side < 0 else 'h', P + m - 1, below=eu if side < 0 else None, above=eu if side > 0 else None)
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
                legs.append([nn, u + 1, 'TP1'])
                qty -= nn
                done1 = True
                stop = eu
            if qty and tp2 is not None and ((Lu <= tp2) if side < 0 else (Hu >= tp2)):
                legs.append([qty, u + 1, 'TP2'])
                qty = 0
            if qty and ((Cu > stop) if side < 0 else (Cu < stop)):
                legs.append([qty, u + 1, 'stop' if stop == ext else 'stop@entry'])
                qty = 0
            if not qty:
                break
        if qty:
            legs.append([qty, 388, 'flat 15:58'])
        net, fees, ex_m, spx_out = 0.0, 2 * fee(ask), 0, 0.0
        for leg in legs:
            nn, e, _w = leg
            px = 0.0
            for mm in range(e, max(-1, e - 11), -1):
                b2 = q.get((mm, K, r), (None, None))[0]
                if fin(b2):
                    px = max(0.0, b2)
                    break
            leg.append(px)
            net += nn * (px - ask) * 100
            fees += nn * fee(px)
            ex_m = max(ex_m, e)
            spx_out += nn * spx[e]
        bp = side * (spx_out / 2 - spx[m]) / spx[m] * 1e4
        trades.append(dict(t=t, K=K, ask=ask, legs=legs, exit_m=ex_m, net=net - fees, bp=bp))
        last = ex_m
    names = {2: 'sweep without close-back', 3: 'no displacement + MSS', 4: 'no FVG', 5: 'no entry in window', 6: 'trade open',
             7: 'picker'}
    st = 'no sweep' if not stage else names[max(stage)]
    return dict(bias=bias, setups=setups, trades=trades, stage=None if trades else st)


def R6(x):
    return None if x is None else round(float(x), 6)


def compare(d, E):
    """E: the engine's rows for v0 on day d -> list of difference strings"""
    plain = run(d)
    eng = E[d]
    diffs = []
    if plain['bias'] != eng['bias']:
        diffs.append(f'{d} bias {plain["bias"]} vs {eng["bias"]}')
    a = [(s['t'], s['side'], R6(s['ext']), s['s'], s['j'], R6(s['zone'][0]), R6(s['zone'][1])) for s in plain['setups']]
    b = [(s['t'], s['side'], R6(s['ext']), s['sweep'], s['j'], R6(s['zone'][0]), R6(s['zone'][1])) for s in eng['setups']]
    if a != b:
        diffs.append(f'{d} setups {a} vs {b}')
    ta = [(t['t'], t['K'], R6(t['ask']), tuple((n, e, w, R6(px)) for n, e, w, px in t['legs']), t['exit_m'], R6(t['net']), R6(t['bp']))
          for t in plain['trades']]
    tb = [(t['t'], t['K'], R6(t['ask']), tuple((n, e, w, R6(px)) for n, e, px, w in t['legs']), t['exit_m'], R6(t['net']), R6(t['bp']))
          for t in eng['trades']]
    if ta != tb:
        diffs.append(f'{d} trades {ta} vs {tb}')
    if not eng['trades'] and plain['stage'] != eng['stage']:
        diffs.append(f'{d} no-trade stage {plain["stage"]} vs {eng["stage"]}')
    return diffs, len(a), len(ta), (0 if eng['trades'] else 1)


def engine_rows(days):
    import explore as X
    out = {}
    for d in days:
        tr, why, S, D, B = X.ict.run_day(d, X.ict.VARIANTS['v0'])
        stage = None
        if not tr:
            stage = max(why, key=lambda a: X.STAGE.get(a.split(':')[0], 9)) if why else 'no sweep'
            stage = 'picker' if stage.startswith('picker') else stage
        out[d] = dict(bias=X.ict.htf_bias(d), setups=S, trades=tr, stage=stage)
        X.ict.chain.cache_clear()
    return out


def check_day(d):
    E = engine_rows([d])
    return d, compare(d, E)


def main():
    sess = json.loads((HERE / 'out' / 'explore_sessions.json').read_text())
    T = pl.read_csv(HERE / 'out' / 'explore_trades.csv').filter(pl.col('row') == 'v0')
    traded = sorted(set(T['day'].to_list()))
    rest = [d for d in sess['run'] if d not in set(traded)]
    rnd = random.Random(20261023)
    no_trade = sorted(rnd.sample(rest, 40))
    days = traded + no_trade
    with mp.get_context('spawn').Pool(4) as pool:
        res = pool.map(check_day, days, chunksize=2)
    nd = ns = nt = nn = 0
    lines = []
    for d, (diffs, a, b, c) in res:
        nd += len(diffs)
        ns += a
        nt += b
        nn += c if d in no_trade else 0
        lines += diffs
    msg = (f'v0 re-derived by plain loops on {len(days)} sessions ({len(traded)} with a v0 trade, {len(no_trade)} seeded no-trade '
           f'sessions): {ns} setups (sweep bar, extreme, displacement bar, FVG zone, entry minute), {nt} trades (strike, ask, '
           f'every exit leg: size, minute, reason, bid; net; underlying bp), {nn} no-trade sessions (bias, furthest stage); '
           f'differences: {nd}')
    print('\n'.join(lines + [msg]))
    (HERE / 'out' / 'verify_explore.txt').write_text('\n'.join(lines + [msg]) + '\n')


if __name__ == '__main__':
    main()
