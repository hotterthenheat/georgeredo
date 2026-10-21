"""Hypothesis C: re-derive 50 random structures (25 debit verticals, 25 butterflies) from the raw chain files with plain
loops - the files are read row by row (polars iter_rows, no expressions), no shared helpers beyond file paths and constants - and count the differences against the stored tables.

A vertical is checked on: the two strikes chosen (deltas from a scalar bisection on the mid), the debit, the settlement
value, the hold-to-settlement P&L, the 15:58 flat P&L and the 50%-trail exit minute and P&L (out/spreads_trades.parquet).
A butterfly on: the ATM strike, the wings' quotes, the debit or credit, the payoff and the P&L (out/flies_<P>.parquet).
Tolerance: 1e-6 on prices, exact on strikes and minutes.
  nice -n 10 env POLARS_MAX_THREADS=1 python3 -I verify.py      (SEED=... for another draw)
"""
import os, sys, math, random, json
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, OUT, PRODUCTS, FEE, UNDERLYING, FLY_WINGS, STRIKE_STEP, MIN_DEBIT, DELTA_CELLS

SEED = int(os.environ.get('SEED', '20261021'))
random.seed(SEED)

def ncdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def bs(S, K, v, call):
    d1 = math.log(S / K) / v + v / 2; d2 = d1 - v
    c = S * ncdf(d1) - K * ncdf(d2)
    return c if call else c - S + K
def total_vol(S, K, mid, call):
    intr = max(S - K, 0) if call else max(K - S, 0)
    if mid - intr <= 0.01: return None
    if bs(S, K, 4.0, call) < mid: return None
    a, b = 1e-5, 4.0
    for _ in range(60):
        m = (a + b) / 2
        if bs(S, K, m, call) < mid: a = m
        else: b = m
    return (a + b) / 2
def delta(S, K, v, call):
    d1 = math.log(S / K) / v + v / 2
    return ncdf(d1) if call else ncdf(d1) - 1

def chain_rows(root, d):
    """list of (m, strike, right, bid, ask) with the audit's validity rule, plain python."""
    t = pl.read_parquet(f'{RAW}/data_full/chains/{root}/{d}.parquet').iter_rows(named=True)
    out = []
    for r in t:
        ts = r['timestamp']; m = ts.hour * 60 + ts.minute - 570
        b, a = r['bid'], r['ask']
        if b is None or a is None or a < b or b < 0 or a <= 0 or m < 0 or m > 390: continue
        out.append((m, float(r['strike']), r['right'], float(b), float(a)))
    return out

def spot_series(root, d):
    """spot[m]: ETF close of bar stamped m-1; SPX print at m. plain python."""
    u = UNDERLYING[root]; spot = [None] * 391
    if u == 'SPX':
        for r in pl.read_parquet(f'{RAW}/data/index/SPX/{d}.parquet').iter_rows(named=True):
            if r['price'] is None: continue
            m = r['timestamp'].hour * 60 + r['timestamp'].minute - 570
            if 0 <= m <= 390: spot[m] = float(r['price'])
    else:
        for r in pl.read_parquet(f'{RAW}/data/underlying/{u}/{d}.parquet').iter_rows(named=True):
            if r['close'] is None: continue
            m = r['timestamp'].hour * 60 + r['timestamp'].minute - 570
            if 0 <= m + 1 <= 390: spot[m + 1] = float(r['close'])
    return spot

def settle_spot(spot, close_m=390):
    if spot[close_m] is not None: return spot[close_m]
    return [s for s in spot if s is not None][-1]

def intr(S, K, right): return max(S - K, 0.0) if right == 'CALL' else max(K - S, 0.0)

def check_spread(row, tr):
    root, d, side, e, cell = row['product'], row['session'], row['side'], int(row['entry_m']), row['cell']
    rows = chain_rows(root, d); spot = spot_series(root, d); S = float(row['spot_entry'])
    tab = sorted([(k, b, a) for m, k, r, b, a in rows if m == e and r == side])
    call = side == 'CALL'
    dl = []
    for k, b, a in tab:
        v = total_vol(S, k, (a + b) / 2, call); dl.append(None if v is None else abs(delta(S, k, v, call)))
    diffs = []
    if cell in DELTA_CELLS:
        dL, dS = DELTA_CELLS[cell]
        cand = [(i, x) for i, x in enumerate(dl) if x is not None]
        iL = min(cand, key=lambda t: abs(t[1] - dL))[0]; iS = min(cand, key=lambda t: abs(t[1] - dS))[0]
    else:
        dist = [abs(k - S) for k, _, _ in tab]; best = min(dist); ties = [i for i, x in enumerate(dist) if abs(x - best) < 1e-9]
        iL = max(ties) if side == 'PUT' else min(ties); iS = iL - 1 if side == 'PUT' else iL + 1
    KL, KS = tab[iL][0], tab[iS][0]
    if KL != row['k_long']: diffs.append(f'k_long {KL} vs {row["k_long"]}')
    if KS != row['k_short']: diffs.append(f'k_short {KS} vs {row["k_short"]}')
    debit = tab[iL][2] - tab[iS][1]
    if abs(debit - row['debit']) > 1e-6: diffs.append(f'debit {debit} vs {row["debit"]}')
    sc = settle_spot(spot); settle = intr(sc, KL, side) - intr(sc, KS, side)
    if abs(settle - row['settle']) > 1e-6: diffs.append(f'settle {settle} vs {row["settle"]}')
    # mark path
    lb = {}; sa = {}
    for m, k, r, b, a in rows:
        if r != side: continue
        if k == KL: lb[m] = b
        if k == KS: sa[m] = a
    mark = {m: lb[m] - sa[m] for m in range(e + 1, 391) if m in lb and m in sa}
    hold = (settle - debit) * 100 - 2 * FEE
    # flat at 388: last mark at or before 388
    mm = [m for m in mark if m <= 388]
    px = mark[max(mm)] if mm else 0.0
    flat = (px - debit) * 100 - 4 * FEE if px > 0 else hold
    # trail 50%
    peak = -1e9; tm = None; tpx = None
    for m in range(e + 1, 389):
        if m not in mark: 
            if m == 388 and tm is None: tm, tpx = 388, px
            continue
        x = mark[m]; peak = max(peak, x)
        if peak > 0 and x <= 0.5 * peak + 1e-9: tm, tpx = m, x; break
        if m == 388: tm, tpx = 388, px
    if tm is None: tm, tpx = 388, px
    trail = (tpx - debit) * 100 - 4 * FEE if tpx > 0 else hold
    tm_eff = tm if tpx > 0 else 390
    for name, val in (('hold', hold), ('flat', flat), ('trail50', trail)):
        t = tr[name]
        if abs(t['pnl'] - val) > 1e-6: diffs.append(f'{name} pnl {val:.4f} vs {t["pnl"]:.4f} (reason {t["reason"]})')
    if tr['trail50']['exit_m'] != tm_eff and tr['trail50']['reason'] != 'flat' or (tr['trail50']['reason'] == 'trail' and tr['trail50']['exit_m'] != tm):
        diffs.append(f'trail exit_m {tm} vs {tr["trail50"]["exit_m"]} ({tr["trail50"]["reason"]})')
    return diffs

def check_fly(row):
    root, d, m, kind, W, K0 = row['product'], row['session'], int(row['m']), row['kind'], float(row['W']), float(row['K0'])
    rows = chain_rows(root, d); spot = spot_series(root, d); S = spot[m]
    cq = {k: (b, a) for mm, k, r, b, a in rows if mm == m and r == 'CALL'}; pq_ = {k: (b, a) for mm, k, r, b, a in rows if mm == m and r == 'PUT'}
    both = sorted(set(cq) & set(pq_)); k0 = min(both, key=lambda k: abs(k - S))
    diffs = []
    if k0 != K0: diffs.append(f'K0 {k0} vs {K0}')
    if abs(S - row['spot']) > 1e-6: diffs.append(f'spot {S} vs {row["spot"]}')
    if row['wing'] == 'wstraddle':
        step = STRIKE_STEP[root]; strad = (cq[k0][0] + cq[k0][1]) / 2 + (pq_[k0][0] + pq_[k0][1]) / 2
        w = max(step, round(strad / step) * step)
        if abs(w - W) > 1e-9: diffs.append(f'W {w} vs {W}')
    lo, hi = k0 - W, k0 + W; sc = settle_spot(spot)
    if kind == 'call':
        debit = cq[lo][1] + cq[hi][1] - 2 * cq[k0][0]; pay = intr(sc, lo, 'CALL') - 2 * intr(sc, k0, 'CALL') + intr(sc, hi, 'CALL'); pnl = (pay - debit) * 100 - 4 * FEE; risk = debit
    elif kind == 'put':
        debit = pq_[lo][1] + pq_[hi][1] - 2 * pq_[k0][0]; pay = intr(sc, lo, 'PUT') - 2 * intr(sc, k0, 'PUT') + intr(sc, hi, 'PUT'); pnl = (pay - debit) * 100 - 4 * FEE; risk = debit
    else:
        credit = cq[k0][0] + pq_[k0][0] - pq_[lo][1] - cq[hi][1]; pay = -intr(sc, k0, 'CALL') - intr(sc, k0, 'PUT') + intr(sc, lo, 'PUT') + intr(sc, hi, 'CALL'); pnl = (credit + pay) * 100 - 4 * FEE; risk = W - credit
        if abs(credit - row['credit']) > 1e-6: diffs.append(f'credit {credit} vs {row["credit"]}')
    if kind != 'iron' and abs(debit - row['debit']) > 1e-6: diffs.append(f'debit {debit} vs {row["debit"]}')
    if abs(risk - row['risk']) > 1e-6: diffs.append(f'risk {risk} vs {row["risk"]}')
    if abs(pay - row['payoff']) > 1e-6: diffs.append(f'payoff {pay} vs {row["payoff"]}')
    if abs(pnl - row['pnl']) > 1e-6: diffs.append(f'pnl {pnl} vs {row["pnl"]}')
    return diffs

def main():
    T = pl.read_parquet(os.path.join(OUT, 'spreads_trades.parquet'))
    S = pl.concat([pl.read_parquet(os.path.join(OUT, f'spreads_{p}.parquet')).filter(pl.col('ok')) for p in PRODUCTS], how='vertical_relaxed')
    F = pl.concat([pl.read_parquet(os.path.join(OUT, f'flies_{p}.parquet')) for p in PRODUCTS], how='vertical_relaxed')
    si = random.sample(range(S.height), 25); fi = random.sample(range(F.height), 25)
    n_diff = 0; report = []
    for i in si:
        row = S.row(i, named=True)
        t = T.filter((pl.col('product') == row['product']) & (pl.col('session') == row['session']) & (pl.col('universe') == row['universe']) & (pl.col('entry_m') == row['entry_m']) & (pl.col('cell') == row['cell']) & (pl.col('side') == row['side']))
        tr = {r['exit']: r for r in t.iter_rows(named=True)}
        d = check_spread(row, tr) if tr else ['no trade rows']
        n_diff += bool(d); report.append(dict(kind='spread', product=row['product'], session=row['session'], universe=row['universe'], cell=row['cell'], side=row['side'], entry_m=row['entry_m'], diffs=d))
        print('spread', row['product'], row['session'], row['universe'], row['side'], row['entry_m'], row['cell'], 'OK' if not d else d, flush=True)
    for i in fi:
        row = F.row(i, named=True); d = check_fly(row)
        n_diff += bool(d); report.append(dict(kind='fly', product=row['product'], session=row['session'], t=row['t'], fly=row['kind'], wing=row['wing'], diffs=d))
        print('fly', row['product'], row['session'], row['t'], row['kind'], row['wing'], 'OK' if not d else d, flush=True)
    print('structures checked 50, with differences:', n_diff)
    with open(os.path.join(OUT, 'verify.json'), 'w') as f: json.dump(dict(seed=SEED, checked=50, differing=n_diff, rows=report), f, indent=1)

if __name__ == '__main__':
    main()
