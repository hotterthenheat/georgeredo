"""Hypothesis F, step 1: build the +-5 ATM butterflies at 15:00 and 15:30 on SPY and QQQ from the raw chains, one read
per session, with every leg's NBBO, mid and quoted size, so the fill model can be applied afterwards.

C's structure rule, unchanged: at minute m (330 = 15:00, 360 = 15:30), K0 = the strike nearest spot (spot = the close
of the ETF bar stamped m-1) among the strikes with BOTH a call and a put validly quoted at m (C's read_chain validity:
bid and ask present, ask >= bid, bid >= 0, ask > 0); wings K0 +- 5. Long call fly: buy K0-5, sell 2 K0, buy K0+5, all
calls; long put fly the same in puts; iron fly: sell the K0 call and put, buy the K0-5 put and the K0+5 call. Every
leg quoted at m, the short legs' bids > 0, NBBO max risk >= $0.05. Held to settlement on the 16:00 close.

  PERIOD=fit  builds the 2022-2024 sessions -> out/flies_fit.parquet;  PERIOD=oos the 2025-2026 sessions -> out/flies_oos.parquet.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build.py
Both parquets are rebuildable from RAW in about two minutes a product.
"""
import os, sys, time, json
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_f import *

PERIOD = os.environ.get('PERIOD', 'fit')
assert PERIOD in ('fit', 'oos')

def quotes(q, side):
    t = q.filter(pl.col('right') == side)
    return {float(k): (float(b), float(a), int(bs), int(as_)) for k, b, a, bs, as_ in zip(t['strike'], t['bid'], t['ask'], t['bid_size'], t['ask_size'])}

def leg(d, K, side, lots, long):
    """one leg's record: strike, side, bid, ask, mid, sizes; 'size' is the size on the side we hit (ask for a long, bid for a short)."""
    b, a, bs, as_ = d[K]
    return dict(K=K, side=side, long=long, lots=lots, bid=b, ask=a, mid=(a + b) / 2, bid_size=bs, ask_size=as_, size=(as_ if long else bs))

def build_session(root, d, fr, c):
    rows = []
    for tag, m in FLY_TIMES.items():
        S = fr['spot'][m]
        if np.isnan(S) or m >= fr['close_m']: continue
        q = c.filter(pl.col('m') == m)
        cq = quotes(q, 'CALL'); pq = quotes(q, 'PUT')
        both = np.array(sorted(set(cq) & set(pq)))
        if both.size == 0: continue
        K0 = float(both[np.argmin(np.abs(both - S))])
        lo, hi = K0 - W, K0 + W
        sc = fr['spot_close']
        for form in FORMS:
            if form == 'call':
                if lo not in cq or hi not in cq or cq[K0][0] <= 0: continue
                legs = [leg(cq, lo, 'CALL', 1, True), leg(cq, K0, 'CALL', 2, False), leg(cq, hi, 'CALL', 1, True)]
                pay = intrinsic(sc, lo, 'CALL') - 2 * intrinsic(sc, K0, 'CALL') + intrinsic(sc, hi, 'CALL')
            elif form == 'put':
                if lo not in pq or hi not in pq or pq[K0][0] <= 0: continue
                legs = [leg(pq, lo, 'PUT', 1, True), leg(pq, K0, 'PUT', 2, False), leg(pq, hi, 'PUT', 1, True)]
                pay = intrinsic(sc, lo, 'PUT') - 2 * intrinsic(sc, K0, 'PUT') + intrinsic(sc, hi, 'PUT')
            else:
                if lo not in pq or hi not in cq or cq[K0][0] <= 0 or pq[K0][0] <= 0: continue
                legs = [leg(pq, lo, 'PUT', 1, True), leg(cq, K0, 'CALL', 1, False), leg(pq, K0, 'PUT', 1, False), leg(cq, hi, 'CALL', 1, True)]
                pay = -intrinsic(sc, K0, 'CALL') - intrinsic(sc, K0, 'PUT') + intrinsic(sc, lo, 'PUT') + intrinsic(sc, hi, 'CALL')
            # net package: + for what we pay (debit), computed as sum over legs of lots * (ask if long else -bid)
            nbbo = sum(l['lots'] * (l['ask'] if l['long'] else -l['bid']) for l in legs)
            mid = sum(l['lots'] * (l['mid'] if l['long'] else -l['mid']) for l in legs)
            if form == 'iron':
                credit_nbbo, credit_mid = -nbbo, -mid
                risk = W - credit_nbbo
                debit_nbbo = debit_mid = np.nan
            else:
                debit_nbbo, debit_mid = nbbo, mid
                risk = debit_nbbo
                credit_nbbo = credit_mid = np.nan
            if not np.isfinite(risk) or risk < MIN_DEBIT: continue
            rec = dict(product=root, session=d, t=tag, m=m, form=form, W=W, K0=K0, spot=S, spot_close=sc, close_m=fr['close_m'],
                       debit_nbbo=debit_nbbo, debit_mid=debit_mid, credit_nbbo=credit_nbbo, credit_mid=credit_mid, risk_nbbo=risk, payoff=pay,
                       slip=nbbo - mid,   # $ a share of package debit above the mid (what k = 1 would recover)
                       pnl_nbbo=((pay - debit_nbbo) * 100 - 4 * FEE) if form != 'iron' else ((credit_nbbo + pay) * 100 - 4 * FEE),
                       min_size=min(l['size'] for l in legs), min_size_per_lot=min(l['size'] / l['lots'] for l in legs),
                       n_legs=len(legs))
            for i, l in enumerate(legs):
                for k2 in ('K', 'side', 'long', 'lots', 'bid', 'ask', 'bid_size', 'ask_size'):
                    rec[f'l{i}_{k2}'] = l[k2]
            rows.append(rec)
    return rows

def run(root):
    days = sorted(f[:-8] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    days = [d for d in days if (d < SPLIT) == (PERIOD == 'fit') and d <= OOS_END]
    if os.environ.get('LIMIT'): days = days[:int(os.environ['LIMIT'])]
    t0 = time.time(); rows = []; nhalf = 0; nmiss = 0
    for i, d in enumerate(days):
        try:
            fr = session_frame(root, d)
        except FileNotFoundError:
            nmiss += 1; continue
        if fr is None: nmiss += 1; continue
        if fr['half']: nhalf += 1; continue
        c = read_chain(root, d)
        if c.height == 0: nmiss += 1; continue
        rows += build_session(root, d, fr, c)
        if i % 100 == 0: print(root, PERIOD, i, len(days), len(rows), f'{time.time()-t0:.0f}s', flush=True)
    info = dict(product=root, period=PERIOD, sessions_listed=len(days), half_days_dropped=nhalf, missing=nmiss, flies=len(rows),
                first=days[0] if days else None, last=days[-1] if days else None, seconds=round(time.time() - t0))
    print(json.dumps(info), flush=True)
    return rows, info

if __name__ == '__main__':
    allrows = []; infos = []
    for root in PRODUCTS:
        r, i = run(root); allrows += r; infos.append(i)
    pl.DataFrame(allrows, infer_schema_length=None).write_parquet(os.path.join(OUT, f'flies_{PERIOD}.parquet'), compression='zstd')
    with open(os.path.join(LOGS, f'build_{PERIOD}.json'), 'w') as f: json.dump(infos, f, indent=1)
