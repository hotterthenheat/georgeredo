"""Re-derive 50 random spreads from the RAW chain files with plain loops (no numpy arrays, no polars expressions beyond
reading the file into rows) and count the fields that differ from engine.py's rows. Writes out/verify.txt.
    python3 -I verify.py
Every element of a trade is rebuilt here from scratch: the strike rule (a scalar bisection for the delta rules), the entry
NBBO, the credit, the minute-by-minute cost to close, the take-profit and stop minutes, the settlement price and the four
P&Ls. Tolerance 1e-6 on dollars; the delta-rule strike must match exactly.
"""
import datetime as dt, math, os, random
import polars as pl
RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
UNDERLYING = {'SPXW': 'SPX', 'SPY': 'SPY'}
FEE = 0.65; DELTA_OF = {'d10': 0.10, 'd15': 0.15, 'd20': 0.20, 'd25': 0.25}

def N(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def call_price(S, K, v):
    d1 = (math.log(S / K) + 0.5 * v * v) / v
    return S * N(d1) - K * N(d1 - v)

def delta_from_mid(S, K, mid, is_call):
    target = mid if is_call else mid + S - K
    lo, hi = 1e-5, 5.0
    for _ in range(60):
        m = (lo + hi) / 2
        if call_price(S, K, m) > target: hi = m
        else: lo = m
    v = (lo + hi) / 2; d1 = (math.log(S / K) + 0.5 * v * v) / v
    return N(d1) if is_call else 1 - N(d1)

def load_chain(root, d):
    """quotes[(right, strike, minute)] = (bid, ask) for two-sided rows at minutes 1..390"""
    f = os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')
    q = {}
    for ts, k, r, b, a in pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).iter_rows():
        m = ts.hour * 60 + ts.minute - 570
        if b is None or a is None or a < b or b < 0 or m < 1 or m > 390: continue
        q[(r, float(k), m)] = (b, a)
    strikes = sorted({k for (_, k, _) in q})
    return q, strikes

def spot_and_settle(root, d):
    if root == 'SPXW':
        rows = [(ts.hour * 60 + ts.minute - 570, p) for ts, p in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).iter_rows() if p is not None]
        rows = [(m, p) for m, p in rows if 0 <= m <= 390]
        return {m: p for m, p in rows}, rows[-1][1]
    rows = [(ts.hour * 60 + ts.minute - 570, c) for ts, c in pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).iter_rows() if c is not None]
    rows = [(j, c) for j, c in rows if 0 <= j <= 390]
    return {j + 1: c for j, c in rows if j < 390}, rows[-1][1]

def leg(q, right, K, m):
    return q.get((right, K, m))

def rebuild(root, row, q, strikes, px, settle):
    side = row['structure']; right = 'CALL' if side == 'call' else 'PUT'; e = row['e']; S = px[e]; w = row['width']
    # ---- the short strike by the row's rule
    rule = row['rule']
    if rule in DELTA_OF:
        best = None
        for K in strikes:
            if (side == 'call' and K <= S) or (side == 'put' and K >= S): continue
            lq = leg(q, right, K, e)
            if lq is None: continue
            b, a = lq; mid = (b + a) / 2
            if mid <= 0 or a <= 0: continue
            if side == 'call' and mid >= S: continue
            if side == 'put' and mid >= K: continue
            dl = delta_from_mid(S, K, mid, side == 'call')
            key = (abs(dl - DELTA_OF[rule]), -K if side == 'call' else K)
            if best is None or key < best[0]: best = (key, K)
        Ks = best[1] if best else None
    else:
        if row['test'] == 'touch':
            ref = row['px_t']
            if rule == 'half': ref = ref + (0.5 * row['straddle_e'] if side == 'call' else -0.5 * row['straddle_e'])
        else:
            mult = {'em1': 1.0, 'em1p': 1.2533141, 'half': 0.5}[rule]
            ref = S + (mult * row['straddle_e'] if side == 'call' else -mult * row['straddle_e'])
        if side == 'call': cands = [K for K in strikes if K >= ref - 1e-9]; Ks = min(cands) if cands else None
        else: cands = [K for K in strikes if K <= ref + 1e-9]; Ks = max(cands) if cands else None
    if Ks is None: return None
    Kl = Ks + w if side == 'call' else Ks - w
    sq, lq = leg(q, right, Ks, e), leg(q, right, Kl, e)
    if sq is None or lq is None or sq[0] <= 0 or lq[1] <= 0: return None
    credit = sq[0] - lq[1]
    if credit < 0.05: return None
    tp_m = stop_m = None
    for m in range(e + 1, 390):
        a_s, b_l = leg(q, right, Ks, m), leg(q, right, Kl, m)
        if a_s is None or b_l is None: continue
        cost = a_s[1] - b_l[0]
        if tp_m is None and cost <= 0.5 * credit: tp_m = m
        if stop_m is None and cost >= 2.0 * credit: stop_m = m
        if tp_m and stop_m: break
    intr = lambda K: max(0.0, settle - K) if side == 'call' else max(0.0, K - settle)
    sv = intr(Ks) - intr(Kl)
    hold = (credit - sv) * 100 - 2 * FEE
    def at(m):
        a_s, b_l = leg(q, right, Ks, m), leg(q, right, Kl, m)
        return (credit - (a_s[1] - b_l[0])) * 100 - 4 * FEE
    both = min([x for x in (tp_m, stop_m) if x]) if (tp_m or stop_m) else None
    return dict(short_k=Ks, long_k=Kl, credit=credit, tp_m=tp_m, stop_m=stop_m, pnl_hold=hold, pnl_tp=at(tp_m) if tp_m else hold,
                pnl_stop=at(stop_m) if stop_m else hold, pnl_both=at(both) if both else hold, settle=settle)

random.seed(7)
lines = []; n_diff = 0; n_checked = 0; fields = ['short_k', 'long_k', 'credit', 'tp_m', 'stop_m', 'pnl_hold', 'pnl_tp', 'pnl_stop', 'pnl_both', 'settle']
for root in ('SPXW', 'SPY'):
    X = pl.read_parquet(os.path.join(OUT, f'trades_{root}.parquet')).filter(pl.col('structure') != 'condor')
    idx = random.sample(range(X.height), 25)
    sample = X[idx].sort('session')
    cache = {}
    for row in sample.iter_rows(named=True):
        d = row['session']
        if d not in cache: cache[d] = (*load_chain(root, d), *spot_and_settle(root, d))
        q, strikes, px, settle = cache[d]
        r = rebuild(root, row, q, strikes, px, settle)
        n_checked += 1
        if r is None:
            n_diff += 1; lines.append(f'{root} {d} e={row["e"]} {row["rule"]} w={row["width"]}: engine has a trade, the rebuild found none'); continue
        diffs = []
        for f in fields:
            a, b = row[f], r[f]
            if a is None and b is None: continue
            if a is None or b is None or (isinstance(a, float) and abs(a - b) > 1e-6) or (not isinstance(a, float) and a != b): diffs.append(f'{f}: engine {a} rebuild {b}')
        if diffs: n_diff += 1
        lines.append(f'{root} {d} {row["test"]} {row["structure"]} e={row["e"]} rule={row["rule"]} w={row["width"]} K={row["short_k"]}/{row["long_k"]} credit={row["credit"]:.2f} '
                     f'hold={row["pnl_hold"]:.2f} tp={row["pnl_tp"]:.2f} stop={row["pnl_stop"]:.2f} both={row["pnl_both"]:.2f} -> ' + ('OK' if not diffs else 'DIFF ' + '; '.join(diffs)))
head = f'{n_checked} spreads re-derived with plain loops from the raw chain files; {n_diff} differ from engine.py (fields: {", ".join(fields)})'
with open(os.path.join(OUT, 'verify.txt'), 'w') as fh:
    fh.write(head + '\n' + '\n'.join(lines) + '\n')
print(head)
