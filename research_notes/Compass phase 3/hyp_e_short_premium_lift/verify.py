"""Re-derive random scheduled structures of this test's cells from the RAW chain and bar files with separate plain-loop code
(dicts keyed by (right, strike, minute), a scalar Black-Scholes bisection through math.erf, its own strike rules, its own
minute-by-minute cost to close), and compare with Hypothesis B's trade rows; and re-derive the scan minute's straddle,
implied30, the 30-minute move and the t2 target against this folder's minutes table. Prints the count of differences.
  python3 -I verify.py fit 50 11      # period (fit: sessions <= 2024-12-31 only; oos: after), count, seed
"""
import datetime as dt, math, os, random, sys
import polars as pl
RAW = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta'
TRADES = '/home/user/georgeredo/research_notes/Compass phase 2/hyp_b_boundary_theta/out/trades_SPY.parquet'
SCANS_AUDIT = '/home/user/georgeredo/research_notes/Compass engine audit/move_atr_flow/out/scans_SPY.parquet'
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
SCANS = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360]; RULES = ['d10', 'd15', 'd20', 'd25', 'em1']
DELTA = {'d10': 0.10, 'd15': 0.15, 'd20': 0.20, 'd25': 0.25}
FEE = 0.65; TOL = 0.0051

def N(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
def call_px(S, K, v):
    d1 = (math.log(S / K) + 0.5 * v * v) / v; return S * N(d1) - K * N(d1 - v)
def delta_of(S, K, price, is_call):
    target = price if is_call else price + S - K
    lo, hi = 1e-5, 5.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if call_px(S, K, mid) > target: hi = mid
        else: lo = mid
    v = 0.5 * (lo + hi); d1 = (math.log(S / K) + 0.5 * v * v) / v
    return N(d1) if is_call else 1.0 - N(d1)

def load_session(d):
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', 'SPY', f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    Q = {}; strikes = set()
    for ts, k, r, b, a in zip(c['timestamp'].to_list(), c['strike'].to_list(), c['right'].to_list(), c['bid'].to_list(), c['ask'].to_list()):
        m = ts.hour * 60 + ts.minute - 570
        if b is None or a is None or a < b or b < 0 or m < 1 or m > 390: continue
        Q[(r, float(k), m)] = (float(b), float(a)); strikes.add(float(k))
    strikes = sorted(strikes)
    u = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close'])
    bars = {}
    for ts, cl in zip(u['timestamp'].to_list(), u['close'].to_list()):
        j = ts.hour * 60 + ts.minute - 570
        if cl is None or j < 0 or j > 390: continue
        bars[j] = float(cl)
    settle = bars[max(bars)]                                   # the close of the last bar stamped <= 16:00
    px = {j + 1: v for j, v in bars.items() if j < 390}        # the spot at m is the close of the bar stamped m-1
    return Q, strikes, px, settle

def first_beyond(strikes, level, side):
    if side == 'call':
        for k in strikes:
            if k >= level - 1e-9: return k
        return None
    out = None
    for k in strikes:
        if k <= level + 1e-9: out = k
    return out

def straddle_engine(Q, strikes, m, S):
    """the engine's straddle_at: the strike nearest S with both sides quoted and both asks > 0; ties -> the lower strike"""
    best = None
    for k in strikes:
        c = Q.get(('CALL', k, m)); p = Q.get(('PUT', k, m))
        if c is None or p is None or c[1] <= 0 or p[1] <= 0: continue
        key = (abs(k - S), k)
        if best is None or key < best[0]: best = (key, (c[0] + c[1]) / 2 + (p[0] + p[1]) / 2)
    return None if best is None else best[1]

def nearest_delta(Q, strikes, m, S, side, target):
    r = 'CALL' if side == 'call' else 'PUT'; cands = []
    for k in strikes:
        q = Q.get((r, k, m))
        if q is None: continue
        mid = (q[0] + q[1]) / 2
        otm = k > S if side == 'call' else k < S
        if not otm or mid <= 0 or q[1] <= 0: continue
        if side == 'call' and not mid < S: continue
        if side == 'put' and not mid < k: continue
        cands.append((abs(delta_of(S, k, mid, side == 'call') - target), -k if side == 'call' else k, k))   # the engine's tie order
    if not cands: return None
    return sorted(cands)[0][2]

def vertical(Q, strikes, px, settle, side, Ks, width, e):
    r = 'CALL' if side == 'call' else 'PUT'; Kl = Ks + width if side == 'call' else Ks - width
    if Kl not in strikes: return None
    qs = Q.get((r, Ks, e)); ql = Q.get((r, Kl, e))
    if qs is None or ql is None or qs[0] <= 0 or ql[1] <= 0: return None
    credit = qs[0] - ql[1]
    if credit < 0.05: return None
    def intr(K): return max(0.0, settle - K) if side == 'call' else max(0.0, K - settle)
    sv = intr(Ks) - intr(Kl)
    cost = {}
    for m in range(e + 1, 390):
        a = Q.get((r, Ks, m)); b = Q.get((r, Kl, m))
        cost[m] = (a[1] - b[0]) if (a is not None and b is not None) else None
    return dict(Ks=Ks, Kl=Kl, credit=credit, sv=sv, cost=cost)

def manage(credit, cost, sv, e, legs):
    hold = (credit - sv) * 100 - FEE * legs
    tp = st = None
    for m in range(e + 1, 390):
        c = cost[m]
        if c is None: continue
        if tp is None and c <= 0.5 * credit: tp = m
        if st is None and c >= 2.0 * credit: st = m
    def at(m): return (credit - cost[m]) * 100 - 2 * FEE * legs
    return dict(pnl_hold=hold, pnl_tp=at(tp) if tp else hold, pnl_stop=at(st) if st else hold, tp_m=tp, stop_m=st)

if __name__ == '__main__':
    mode = sys.argv[1]; n = int(sys.argv[2]); seed = int(sys.argv[3])
    X = pl.scan_parquet(TRADES).filter((pl.col('test') == 'sched') & pl.col('m_scan').is_in(SCANS) & pl.col('rule').is_in(RULES) & pl.col('structure').is_in(['call', 'put', 'condor']))
    X = (X.filter(pl.col('session') <= '2024-12-31') if mode == 'fit' else X.filter(pl.col('session') > '2024-12-31')).collect()
    Sc = pl.read_parquet(SCANS_AUDIT).select('session', 'm_scan', 'spot', 'straddle')
    Mn = pl.read_parquet(os.path.join(OUT, 'minutes_SPY_all.parquet'), columns=['session', 'm', 'spot', 'straddle', 'straddle_rel', 'implied30', 'mv30_bps', 't2']).with_columns(pl.col('session').cast(pl.Utf8))
    random.seed(seed); picks = sorted(random.sample(range(X.height), n))
    diffs = 0; fdiffs = 0; lines = []; cache = {}
    for i in picks:
        row = X.row(i, named=True); d = row['session']; e = int(row['m_scan']); side = row['structure']; rule = row['rule']; w = float(row['width'])
        if d not in cache: cache = {d: load_session(d)}
        Q, strikes, px, settle = cache[d]; S = px[e]
        sc = Sc.filter((pl.col('session') == d) & (pl.col('m_scan') == e)).row(0, named=True)
        strad_audit = sc['straddle']; strad_mine = straddle_engine(Q, strikes, e, S)
        def leg(sd):
            sg = 1 if sd == 'call' else -1
            if rule in DELTA: Ks = nearest_delta(Q, strikes, e, S, sd, DELTA[rule])
            else: Ks = first_beyond(strikes, S + sg * strad_audit, sd)
            return vertical(Q, strikes, px, settle, sd, Ks, w, e) if Ks is not None else None
        bad = []
        if side == 'condor':
            cv, pv = leg('call'), leg('put')
            if cv is None or pv is None: bad.append('no condor rebuilt'); credit = sv = None; res = {}
            else:
                credit = cv['credit'] + pv['credit']; sv = cv['sv'] + pv['sv']
                cost = {m: (cv['cost'][m] + pv['cost'][m]) if (cv['cost'][m] is not None and pv['cost'][m] is not None) else None for m in cv['cost']}
                res = manage(credit, cost, sv, e, 4)
        else:
            v = leg(side)
            if v is None: bad.append('no vertical rebuilt'); credit = sv = None; res = {}
            else:
                credit = v['credit']; sv = v['sv']; res = manage(credit, v['cost'], sv, e, 2)
                if abs(v['Ks'] - row['short_k']) > 1e-9: bad.append(f"short_k {v['Ks']} vs {row['short_k']}")
                if abs(v['Kl'] - row['long_k']) > 1e-9: bad.append(f"long_k {v['Kl']} vs {row['long_k']}")
        if credit is not None:
            for a, b, nm in ((credit, row['credit'], 'credit'), (sv, row['settle_val'], 'settle_val'), (settle, row['settle'], 'settle'), (S, row['spot_e'], 'spot')):
                if abs(a - b) > TOL: bad.append(f'{nm} {a:.4f} vs {b:.4f}')
            for nm in ('pnl_hold', 'pnl_tp', 'pnl_stop'):
                if abs(res[nm] - row[nm]) > TOL: bad.append(f'{nm} {res[nm]:.2f} vs {row[nm]:.2f}')
            for nm in ('tp_m', 'stop_m'):
                if res[nm] != row[nm]: bad.append(f'{nm} {res[nm]} vs {row[nm]}')
        if strad_mine is None or abs(strad_mine - strad_audit) > TOL: bad.append(f'straddle(engine rule) {strad_mine} vs audit scans {strad_audit}')
        if abs(S - sc['spot']) > TOL: bad.append(f"spot {S} vs audit scans {sc['spot']}")
        # the feature side: the minutes table's straddle (Hypothesis D's five-nearest rule), implied30, mv30, t2
        mrow = Mn.filter((pl.col('session') == d) & (pl.col('m') == e))
        if mrow.height == 0: bad.append('no minutes row')
        else:
            mr = mrow.row(0, named=True)
            # Hypothesis D's atm_strike: the strike nearest spot among the five nearest, both mids present (two-sided, ask > 0)
            def mid_ok(r, k): 
                q = Q.get((r, k, e)); return q is not None and q[1] > 0
            order = sorted(range(len(strikes)), key=lambda q: abs(strikes[q] - S)); j0 = order[0]
            window = sorted(range(max(0, j0 - 2), min(len(strikes), j0 + 3)), key=lambda q: abs(strikes[q] - S))
            st = None
            for q in window:
                k = strikes[q]
                if mid_ok('CALL', k) and mid_ok('PUT', k):
                    cq, pq = Q[('CALL', k, e)], Q[('PUT', k, e)]; st = round((cq[0] + cq[1]) / 2, 4) + round((pq[0] + pq[1]) / 2, 4); break
            spot30 = px.get(e + 30) if e + 30 < 390 else settle if e + 30 == 390 and False else None
            # Hypothesis D's spot[390] is the close of the bar stamped 389 (read_bars indexes bars by the minute they close)
            spot30 = px.get(e + 30)
            mv30 = abs(spot30 / S - 1.0) if spot30 else None
            if st is None or mr['straddle'] is None or abs(st - mr['straddle']) > TOL: bad.append(f"feature straddle {st} vs {mr['straddle']}")
            elif abs(st / S - mr['straddle_rel']) > 1e-6: bad.append('straddle_rel')
            else:
                imp = st / S * math.sqrt(30.0 / (390 - e))
                if abs(imp - mr['implied30']) > 1e-7: bad.append(f"implied30 {imp} vs {mr['implied30']}")
                if mv30 is None or abs(mv30 * 1e4 - mr['mv30_bps']) > 1e-4: bad.append(f"mv30 {mv30} vs {mr['mv30_bps']}")
                elif int(mv30 > imp) != mr['t2']: bad.append(f"t2 {int(mv30 > imp)} vs {mr['t2']}")
        if any(b.startswith(('feature', 'straddle_rel', 'implied30', 'mv30', 't2', 'no minutes')) for b in bad): fdiffs += 1
        if any(not b.startswith(('feature', 'straddle_rel', 'implied30', 'mv30', 't2', 'no minutes')) for b in bad): diffs += 1
        lines.append(f"{d} {e} {side:6s} {rule:4s} w{w:.0f} credit {row['credit']:.2f} hold {row['pnl_hold']:+.2f} tp {row['pnl_tp']:+.2f} stop {row['pnl_stop']:+.2f} -> {'OK' if not bad else '; '.join(bad)}")
    hdr = f'{mode}: {n} random structures (seed {seed}) re-derived from the raw files: {diffs} trade differences (short_k, long_k, credit, settle, settle_val, spot, tp_m, stop_m, pnl_hold, pnl_tp, pnl_stop; tolerance ${TOL}), {fdiffs} feature differences (straddle, straddle_rel, implied30, mv30, t2)'
    print(hdr); print('\n'.join(lines))
    with open(os.path.join(OUT, f'verify_{mode}.txt'), 'w') as fh: fh.write(hdr + '\n' + '\n'.join(lines) + '\n')
