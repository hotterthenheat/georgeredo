"""Step 3b check. Two parts; any difference stops the script.
1. Random trades re-derived from the raw quotes with plain Python loops (no shared code with paths.py): every target and
   stop minute, every stop's bid, every time exit's bid, the best and last bid, and the entry minute's features
   (price, high and low so far, VIX, the at-the-money straddle).
2. The whole table against step 2's: the +100% minute, the -50% minute and its bid, and the best bid must be the same
   for every trade.
  python3 -I step3/verify.py [N]
"""
import bisect, os, random, sys
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step2.double import load as load2   # noqa: E402  (step 2's stored table, for the cross-check)

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(HERE, 'out')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
random.seed(20261016)
TG = {'t125': 1.25, 't150': 1.5, 't200': 2.0, 't250': 2.5, 't300': 3.0, 't400': 4.0, 't600': 6.0, 't1100': 11.0}
ST = {'s70': 0.7, 's50': 0.5, 's30': 0.3}

def minute(ts): return ts.hour * 60 + ts.minute - 570

def close_of(d):
    rows = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet')).to_dicts()
    return 210 if max(r['timestamp'] for r in rows if r['close'] is not None).hour < 15 else 390

def spots(root, d, close_m):
    if root == 'SPXW':
        rows = [(minute(r['timestamp']), r['price']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).to_dicts() if r['price'] is not None]
    else:
        rows = [(minute(r['timestamp']) + 1, r['close']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'underlying', root, f'{d}.parquet')).to_dicts() if r['close'] is not None]
    return sorted(x for x in rows if x[0] <= close_m)

def quotes(root, d, close_m):
    out = {}
    for r in pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).to_dicts():
        m = minute(r['timestamp'])
        if 1 <= m <= close_m and r['bid'] is not None and r['ask'] is not None and r['ask'] >= r['bid'] and r['bid'] >= 0:
            out.setdefault((r['strike'], r['right']), []).append((m, r['bid'], r['ask']))
    for v in out.values(): v.sort()
    return out

def derive(root, d, strike, right, e, Q, close_m):
    q = Q[(strike, right)]
    (_, eb, ea), = [x for x in q if x[0] == e]
    after = [x for x in q if x[0] > e]
    o = dict(entry_bid=eb, entry_ask=ea, quotes_after=len(after))
    if after:
        o['max_bid'] = max(b for _, b, _ in after); o['last_bid'] = after[-1][1]
    for n, k in TG.items(): o[n] = next((m for m, b, _ in after if b >= k * ea - 1e-9), None)
    for n, k in ST.items():
        hit = next(((m, b) for m, b, _ in after if b <= k * ea + 1e-9), None)
        o[n] = hit[0] if hit else None; o[n + '_bid'] = hit[1] if hit else None
    def bid_by(x):
        xs = [b for m, b, _ in after if m <= x]
        return xs[-1] if xs else None
    o['c30_bid'] = bid_by(close_m - 30) if e < close_m - 30 else None
    o['c10_bid'] = bid_by(close_m - 10) if e < close_m - 10 else None
    for h in (30, 60, 120): o[f'h{h}_bid'] = bid_by(e + h) if e + h <= close_m else None
    return o

def features(root, d, e, Q, close_m):
    sp = spots(root, d, close_m); ms = [m for m, _ in sp]
    upto = [p for m, p in sp if m <= e]
    s = sp[bisect.bisect_right(ms, e) - 1][1]
    vix = [(minute(r['timestamp']), r['price']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')).to_dicts()
           if r['price'] is not None and minute(r['timestamp']) >= 1]
    v = [p for m, p in sorted(vix) if m <= e]
    best = None
    for (k, rt), q in Q.items():
        if rt != 'CALL' or (k, 'PUT') not in Q: continue
        c = [x for x in q if x[0] == e and x[2] > 0]; p = [x for x in Q[(k, 'PUT')] if x[0] == e and x[2] > 0]
        if c and p:
            key = (abs(k - s), k)
            if best is None or key < best[0]: best = (key, k, (c[0][1] + c[0][2]) / 2 + (p[0][1] + p[0][2]) / 2)
    return dict(spot_entry=s, high_so_far=max(upto), low_so_far=min(upto), vix_entry=v[-1] if v else None,
                atm_strike=best[1] if best else None, straddle_entry=best[2] if best else None)

def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-9)

bad, n, nf = 0, 0, 0
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    P = pl.read_parquet(os.path.join(OUT, f'paths_{root}.parquet'))
    F = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet'))
    # 2. the whole table against step 2's
    S2 = load2(root).select('session', 'strike', 'right', 'entry_minute', 'double_minute', 'half_minute', 'half_bid', 'max_bid')
    J = P.join(S2, on=['session', 'strike', 'right', 'entry_minute'], how='full', coalesce=True)
    diff = J.filter(pl.col('t200').ne_missing(pl.col('double_minute')) | pl.col('s50').ne_missing(pl.col('half_minute'))
                    | pl.col('s50_bid').ne_missing(pl.col('half_bid')) | pl.col('max_bid').ne_missing(pl.col('max_bid_right')))
    if J.height != P.height or J.height != S2.height or diff.height:
        bad += 1; print('STEP 2 MISMATCH', root, J.height, P.height, S2.height, diff.height)
    else:
        print(root, P.height, 'trades: +100% minute, -50% minute and bid, best bid all equal to step 2')
    # 1. random trades from the raw quotes
    picks = [P.row(random.randrange(P.height), named=True) for _ in range(N // 4)]
    for r in picks:
        close_m = close_of(r['session'])
        Q = quotes(root, r['session'], close_m)
        x = derive(root, r['session'], r['strike'], r['right'], r['entry_minute'], Q, close_m); n += 1
        for k, v in x.items():
            if not same(r[k], v): bad += 1; print('DIFF', root, r['session'], r['strike'], r['right'], r['entry_minute'], k, r[k], v)
        if nf < 40 * 4 and random.random() < 0.3:
            f = F.filter((pl.col('session') == r['session']) & (pl.col('entry_minute') == r['entry_minute'])).row(0, named=True)
            for k, v in features(root, r['session'], r['entry_minute'], Q, close_m).items():
                if not same(f[k], v): bad += 1; print('FEATURE DIFF', root, r['session'], r['entry_minute'], k, f[k], v)
            nf += 1
print(f'{n} trades and {nf} entry-minute features re-derived from raw quotes, {bad} differences')
if bad: raise SystemExit(1)
