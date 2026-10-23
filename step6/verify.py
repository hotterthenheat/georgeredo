"""Step 6 check 1: trades re-derived from the raw files with separate code (plain Python loops over the rows; nothing
shared with build.py but the file locations). 30 random trades and 10 random +500% (H1530) trades, seed 20261023.

For each: the entry quote, the straddle at the buy and the moneyness x (population membership), the spread, the peak bid
and its minute in H60 and H1530, the underlying at the buy and at the H1530 peak, and the three exits' net $ (fees in).
Any difference stops the script.
  python3 -I step6/verify.py [N]
"""
import datetime as dt, os, random, sys
import polars as pl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step1.breakdown import RAW   # noqa: E402  (only the raw files' location is shared)
WORK = os.environ.get('WORK', os.path.join(os.path.dirname(RAW), 'step6'))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
random.seed(20261023)

def minute(ts): return ts.hour * 60 + ts.minute - 570

def last_at(pairs, t):
    v = None
    for m, x in pairs:
        if m <= t: v = x
        else: break
    return v

def same(a, b, tol=1e-9):
    if a is None or b is None: return a is None and b is None
    if a != a or b != b: return a != a and b != b
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))

def fee(root, p):
    if root != 'SPXW': return 0.65
    return 1.18748 if p < 1.0 else 1.27748

def check(r):
    root, d, K, right, e = r['root'], r['session'], r['strike'], r['right'], r['entry_minute']
    rows = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).to_dicts()
    q = {}
    allq = {}
    for x in rows:
        if x['bid'] is None or x['ask'] is None or not (x['ask'] >= x['bid'] >= 0): continue
        m = minute(x['timestamp'])
        if m < 1 or m > 390: continue
        allq.setdefault(m, []).append(x)
        if x['strike'] == K and x['right'] == right: q[m] = (x['bid'], x['ask'])
    o = {}
    o['entry_bid'], o['entry_ask'] = q[e]
    # the underlying, each minute 1..390, carried forward
    if root == 'SPXW':
        sp = sorted((minute(x['timestamp']), x['price']) for x in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).to_dicts() if x['price'] is not None)
    else:
        sp = sorted((minute(x['timestamp']) + 1, x['close']) for x in pl.read_parquet(os.path.join(RAW, 'data', 'underlying', root, f'{d}.parquet')).to_dicts() if x['close'] is not None)
    sp = [p for p in sp if p[0] <= 390]
    px = {t: last_at(sp, t) for t in range(0, 391)}
    o['px'] = px[e]
    # the at-the-money straddle at the buy: the strike nearest the price with both sides quoted, asks above zero
    calls = {x['strike']: (x['bid'] + x['ask']) / 2 for x in allq[e] if x['right'] == 'CALL' and x['ask'] > 0}
    puts = {x['strike']: (x['bid'] + x['ask']) / 2 for x in allq[e] if x['right'] == 'PUT' and x['ask'] > 0}
    k0 = sorted(set(calls) & set(puts), key=lambda k: (abs(k - px[e]), k))[0]
    strad = calls[k0] + puts[k0]
    sgn = 1 if right == 'CALL' else -1
    o['x'] = sgn * (K - px[e]) / strad
    bid0, ask0 = o['entry_bid'], o['entry_ask']
    if not (abs(o['x']) <= 1 and (ask0 - bid0) / ((ask0 + bid0) / 2) <= 0.10): raise SystemExit(f'not in the population: {r}')
    # peaks
    for w, hi in ((60, min(e + 60, 360)), (1530, 360)):
        best, bm = None, -1
        for m in range(e + 1, hi + 1):
            if m in q and (best is None or q[m][0] > best): best, bm = q[m][0], m
        o[f'peak_{w}'] = best; o[f'peak_min_{w}'] = bm
    o['spot_peak_1530'] = px[o['peak_min_1530']] if o['peak_min_1530'] >= 0 else None
    def last_bid(upto):
        v = None
        for m in range(e, upto + 1):
            if m in q: v = q[m][0]
        return v
    # (a)
    xp = None
    for m in range(e + 1, min(e + 60, 360) + 1):
        if m not in q: continue
        b = q[m][0]
        if b >= 1.4 * ask0 - 1e-9: xp = 1.4 * ask0; break
        if b <= 0.7 * ask0 + 1e-9: xp = b; break
    if xp is None: xp = last_bid(min(e + 60, 360))
    o['net_a'] = (xp - ask0) * 100 - fee(root, ask0) - (fee(root, xp) if xp > 0 else 0)
    # (b) and (c)
    armed, top, xb = False, None, None
    for m in range(e + 1, 361):
        if m not in q: continue
        b = q[m][0]
        top = b if top is None else max(top, b)
        if armed and b <= 0.5 * top + 1e-9: xb = b; break
        if not armed and b >= 1.4 * ask0 - 1e-9: armed = True
    if xb is None: xb = last_bid(360)
    o['net_b'] = (xb - ask0) * 100 - fee(root, ask0) - (fee(root, xb) if xb > 0 else 0)
    x1 = 1.4 * ask0 if armed else last_bid(360)
    o['net_c'] = o['net_b'] + (x1 - ask0) * 100 - fee(root, ask0) - (fee(root, x1) if x1 > 0 else 0)
    return o

def main():
    T = pl.concat([pl.read_parquet(os.path.join(WORK, f'trades_{x}.parquet')) for x in ('SPY', 'QQQ', 'IWM', 'SPXW')], how='vertical_relaxed')
    sample = [T.row(random.randrange(T.height), named=True) for _ in range(N)]
    R5 = T.filter(pl.col('peak_1530') >= 6 * pl.col('entry_ask') - 1e-9)
    sample += [R5.row(random.randrange(R5.height), named=True) for _ in range(10)]
    bad = 0
    for r in sample:
        o = check(r)
        for k, v in o.items():
            mine = r[k] if k != 'px' else r['px']
            if not same(mine, v, 1e-9): bad += 1; print('DIFF', r['root'], r['session'], r['strike'], r['right'], r['entry_minute'], k, mine, v)
    print(f'{len(sample)} trades ({N} random, 10 that reached +500% by 3:30) re-derived from the raw files: {bad} differences in {len(sample) * len(o)} figures')
    if bad: raise SystemExit(1)

if __name__ == '__main__':
    main()
