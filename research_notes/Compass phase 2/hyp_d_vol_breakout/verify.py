"""Re-derive 50 random trades of the per-minute table from the raw chain and bar files with separate plain-loop code
(dicts and scalar math, no numpy vectorisation, no import of lib / sweeplib beyond the paths and constants), and count
the differences: the structure's legs, the debit, the exit minute, the net dollars (to $0.01), plus the straddle/spot
and the t2 target at the minute. Reads the table only to choose the sample.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I verify.py [N] [seed]
"""
import datetime as dt, math, os, sys
import polars as pl

RAW = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta'
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
FEE = 0.65; LAST = 388; CLOSE = 390
BAR = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPY'}
STRUCTS = ['str', 'sg10', 'sg15', 'sg20', 'dir', 'oddir']; EXITS = ['h30', 'h60', 'trail', 'settle', 'ri', 'e0955', 'e1030']

def minute(ts): return ts.hour * 60 + ts.minute - 570

def read_chain(root, d):
    q = {}
    for r in pl.read_parquet(f'{RAW}/data_full/chains/{root}/{d}.parquet').iter_rows(named=True):
        m = minute(r['timestamp']); b = r['bid']; a = r['ask']
        if m < 1 or m > CLOSE or b is None or a is None or a < b or b < 0 or a <= 0: continue
        q[(0 if r['right'] == 'CALL' else 1, float(r['strike']), m)] = (round(b, 4), round(a, 4))
    strikes = sorted({k[1] for k in q})
    return q, strikes

def read_bars(u, d):
    o = {}; c = {}; h = {}; l = {}
    for r in pl.read_parquet(f'{RAW}/data/underlying/{u}/{d}.parquet').iter_rows(named=True):
        m = minute(r['timestamp']) + 1
        if r['close'] is None or m < 1 or m > CLOSE: continue
        o[m] = r['open']; c[m] = r['close']; h[m] = r['high']; l[m] = r['low']
    return o, h, l, c

def read_prints(name, d):
    p = {}
    for r in pl.read_parquet(f'{RAW}/data/index/{name}/{d}.parquet').iter_rows(named=True):
        m = minute(r['timestamp'])
        if r['price'] is not None and 0 <= m <= CLOSE: p[m] = r['price']
    out = {}; last = None
    for m in range(0, CLOSE + 1):
        if m in p: last = p[m]
        if last is not None: out[m] = last
    return out

def ncdf(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
def bs_rel(v, k, is_put):
    d1 = -math.log(k) / v + 0.5 * v; d2 = d1 - v
    return k * ncdf(-d2) - ncdf(-d1) if is_put else ncdf(d1) - k * ncdf(d2)
def total_vol(mid, S, K, is_put):
    k = K / S; intr = max(k - 1.0, 0.0) if is_put else max(1.0 - k, 0.0); target = mid / S
    if not target > intr + 1e-9: return None
    lo, hi = 1e-5, 3.0
    for _ in range(80):
        v = 0.5 * (lo + hi)
        if bs_rel(v, k, is_put) < target: lo = v
        else: hi = v
    return 0.5 * (lo + hi)
def delta(v, S, K, is_put):
    d1 = -math.log(K / S) / v + 0.5 * v
    return ncdf(d1) - 1.0 if is_put else ncdf(d1)

def clean(q, right, K, m):
    x = q.get((right, K, m))
    return x is not None and x[1] > 0 and x[0] > 0 and x[0] <= x[1]

def legs_of(struct, q, strikes, m, S, spot, o, c, right_hint=None):
    if struct == 'str':
        j = min(range(len(strikes)), key=lambda i: abs(strikes[i] - S))
        for jj in sorted(range(max(0, j - 2), min(len(strikes), j + 3)), key=lambda i: abs(strikes[i] - S)):
            if (0, strikes[jj], m) in q and (1, strikes[jj], m) in q: return [(0, strikes[jj]), (1, strikes[jj])]
        return None
    if struct.startswith('sg'):
        d = int(struct[2:]) / 100.0; legs = []
        for right in (0, 1):
            best = None
            for K in strikes:
                if not clean(q, right, K, m): continue
                if (right == 0 and K < S) or (right == 1 and K > S) or abs(K - S) > 0.03 * S: continue
                b, a = q[(right, K, m)]; v = total_vol(0.5 * (a + b), S, K, right == 1)
                if v is None: continue
                g = abs(abs(delta(v, S, K, right == 1)) - d)
                if best is None or g < best[0]: best = (g, K)
            if best is None or best[0] > 0.05: return None
            legs.append((right, best[1]))
        return legs
    if struct in ('dir', 'oddir'):
        if struct == 'dir':
            p = spot.get(m - 5) if m - 5 >= 1 else None
            if p is None or p <= 0: return None
            mv = S / p - 1.0
        else:
            if m != 5: return None
            mv = c[5] - o[1]
        if mv == 0: return None
        right = 0 if mv > 0 else 1
        cand = [K for K in strikes if clean(q, right, K, m) and ((K >= S) if right == 0 else (K <= S))]
        if not cand: return None
        return [(right, min(cand, key=lambda K: abs(K - S)))]

def intrinsic(Sc, K, right): return max(Sc - K, 0.0) if right == 0 else max(K - Sc, 0.0)

def trade(legs, q, m, Sc, spot, straddle_rel, exit_name):
    n = len(legs); a0 = []; b0 = []
    for r, K in legs:
        x = q.get((r, K, m))
        if x is None or x[1] <= 0 or x[0] <= 0 or x[0] > x[1]: return None
        b0.append(x[0]); a0.append(x[1])
    debit = sum(a0); m0 = sum(0.5 * (a + b) for a, b in zip(a0, b0))
    settle_val = sum(intrinsic(Sc, K, r) for r, K in legs)
    settle = (CLOSE, (settle_val - debit) * 100.0 - n * FEE)
    def sell(t):
        val = 0.0; fee = n * FEE
        for r, K in legs:
            b = None
            for u in range(t, m, -1):
                x = q.get((r, K, u))
                if x is not None: b = x[0]; break
            if b is None or b <= 0: val += intrinsic(Sc, K, r)
            else: val += b; fee += FEE
        return (t, (val - debit) * 100.0 - fee)
    if exit_name in ('h30', 'h60', 'e0955', 'e1030'):
        t = {'h30': m + 30, 'h60': m + 60, 'e0955': 25, 'e1030': 60}[exit_name]
        return sell(min(t, LAST)) if min(t, LAST) >= m + 1 else settle, debit
    if exit_name == 'settle': return settle, debit
    if exit_name == 'trail':
        peak = m0
        for t in range(m + 1, LAST + 1):
            xs = [q.get((r, K, t)) for r, K in legs]
            if any(x is None for x in xs): continue
            mark = sum(0.5 * (x[0] + x[1]) for x in xs); peak = max(peak, mark)
            if peak > 0 and mark <= 0.5 * peak: return sell(t), debit
        return settle, debit
    if exit_name == 'ri':
        if straddle_rel is None: return settle, debit
        for t in range(m + 1, LAST + 1):
            p = spot.get(t)
            if p is None: continue
            if abs(p / spot[m] - 1.0) >= straddle_rel * math.sqrt((t - m) / (CLOSE - m)): return sell(t), debit
        return settle, debit

if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    import random; rng = random.Random(seed)
    picks = []
    for p in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        T = pl.read_parquet(os.path.join(OUT, f'minutes_{p}.parquet'))
        cols = [(s, e) for s in STRUCTS for e in EXITS if f'{s}_{e}_net' in T.columns]
        want = N // 4 + (1 if p == 'SPY' and N % 4 else 0) + (1 if p == 'QQQ' and N % 4 > 1 else 0)
        tries = 0
        while len([x for x in picks if x['product'] == p]) < want and tries < 5000:
            tries += 1
            s, e = rng.choice(cols); i = rng.randrange(T.height); row = T.row(i, named=True)
            if row[f'{s}_{e}_net'] is None: continue
            picks.append(dict(product=p, session=row['session'], m=row['m'], struct=s, exit=e, K=row[f'{s}_K'], debit=row[f'{s}_debit'], exit_m=row[f'{s}_{e}_m'], net=row[f'{s}_{e}_net'], straddle_rel=row['straddle_rel'], t2=row['t2']))
    diffs = 0; cache = {}
    for k, pk in enumerate(picks):
        key = (pk['product'], pk['session'])
        if key not in cache:
            q, strikes = read_chain(pk['product'], pk['session']); o, h, l, c = read_bars(BAR[pk['product']], pk['session'])
            spot = read_prints('SPX', pk['session']) if pk['product'] == 'SPXW' else dict(c)
            Sc = spot[CLOSE] if CLOSE in spot else spot[max(spot)]
            cache[key] = (q, strikes, o, c, spot, Sc)
        q, strikes, o, c, spot, Sc = cache[key]
        m = pk['m']; S = spot[m]
        # straddle/spot and t2 at the minute
        st_legs = legs_of('str', q, strikes, m, S, spot, o, c)
        srel = None
        if st_legs:
            srel = sum(0.5 * (q[(r, K, m)][0] + q[(r, K, m)][1]) for r, K in st_legs) / S
        imp30 = srel * math.sqrt(30.0 / (CLOSE - m)) if srel else None
        mv30 = abs(spot[m + 30] / S - 1.0) if (m + 30) in spot else None
        t2 = (1 if mv30 > imp30 else 0) if (mv30 is not None and imp30 is not None) else None
        legs = legs_of(pk['struct'], q, strikes, m, S, spot, o, c)
        res = trade(legs, q, m, Sc, spot, srel, pk['exit']) if legs else None
        ok = res is not None
        msgs = []
        if not ok: msgs.append('no trade here')
        else:
            (xm, net), debit = res
            Kstr = ','.join(f'{K:g}' for _, K in legs)
            if Kstr != pk['K']: msgs.append(f'legs {Kstr} vs {pk["K"]}')
            if abs(debit - pk['debit']) > 1e-6: msgs.append(f'debit {debit} vs {pk["debit"]}')
            if xm != pk['exit_m']: msgs.append(f'exit_m {xm} vs {pk["exit_m"]}')
            if abs(net - pk['net']) > 0.01: msgs.append(f'net {net:.2f} vs {pk["net"]:.2f}')
            if srel is not None and pk['straddle_rel'] is not None and abs(srel - pk['straddle_rel']) > 1e-9: msgs.append(f'straddle_rel {srel} vs {pk["straddle_rel"]}')
            if t2 != pk['t2']: msgs.append(f't2 {t2} vs {pk["t2"]}')
        if msgs: diffs += 1
        print(f'{k + 1:2d} {pk["product"]:4} {pk["session"]} m={m:3d} {pk["struct"]:5} {pk["exit"]:6} K={pk["K"]:<12} debit={pk["debit"]:.2f} exit_m={pk["exit_m"]} net={pk["net"]:+8.2f} t2={pk["t2"]} ->', 'OK' if not msgs else 'DIFF ' + '; '.join(msgs), flush=True)
    print(f'\n{len(picks)} trades re-derived with plain-loop code, {diffs} with a difference')
