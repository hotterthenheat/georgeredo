"""Step 4b check: random trades of every kind re-derived from the raw quotes with plain Python loops (no shared code with
trail.py): the entry minute and price (for bounce, the first minute the rule was met; for orb, the first break of the
range), the best bid, and every trailing exit's minute, bid and peak. Any difference stops the script.
  python3 -I step4/verify.py [N per product and kind]
"""
import os, random, sys
import polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 25
random.seed(20261016)
TR = {'trail20': 0.2, 'trail30': 0.3, 'trail40': 0.4, 'trail50': 0.5}

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

def quotes(root, d, strike, right, close_m):
    raw = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).filter((pl.col('strike') == strike) & (pl.col('right') == right)).sort('timestamp').to_dicts()
    return [(minute(r['timestamp']), r['bid'], r['ask']) for r in raw
            if 1 <= minute(r['timestamp']) <= close_m and r['bid'] is not None and r['ask'] is not None and r['ask'] >= r['bid'] and r['bid'] >= 0]

def entry_of(tag, q, sp, close_m, right):
    qa = [x for x in q if x[2] > 0]
    if tag == 'fixed':
        return None   # the row's own minute is checked to be one of the nine and quoted
    if tag.startswith('bounce'):
        k = float(tag[6:]); low = None
        for m, b, a in qa:
            if low is not None and low > 0 and 6 <= m <= close_m - 15 and a >= k * low - 1e-9:
                return m
            low = a if low is None else min(low, a)
        return 'none'
    if tag == 'orb':
        rng = [p for m, p in sp if 1 <= m <= 30]
        hi, lo = max(rng), min(rng)
        for m, p in sp:
            if 30 < m <= close_m - 15 and ((right == 'CALL' and p > hi) or (right == 'PUT' and p < lo)):
                return m
        return 'none'

def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-9)

bad, n = 0, 0
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    T = pl.read_parquet(os.path.join(OUT, f'trades_{root}.parquet'))
    for tag in sorted(T['tag'].unique().to_list()):
        S = T.filter(pl.col('tag') == tag)
        for _ in range(N):
            r = S.row(random.randrange(S.height), named=True); n += 1
            close_m = close_of(r['session'])
            q = quotes(root, r['session'], r['strike'], r['right'], close_m)
            sp = spots(root, r['session'], close_m)
            m0 = entry_of(tag, q, sp, close_m, r['right'])
            if tag == 'fixed':
                if r['entry_minute'] not in (1, 30, 60, 90, 150, 210, 270, 330, 360): bad += 1; print('BAD FIXED MINUTE', root, r)
            elif m0 != r['entry_minute']:
                bad += 1; print('ENTRY DIFF', root, tag, r['session'], r['strike'], r['right'], r['entry_minute'], m0); continue
            at = [x for x in q if x[0] == r['entry_minute']]
            if len(at) != 1 or at[0][2] <= 0: bad += 1; print('NO QUOTE AT ENTRY', root, tag, r); continue
            _, eb, ea = at[0]
            o = dict(entry_bid=eb, entry_ask=ea)
            after = [x for x in q if x[0] > r['entry_minute']]
            o['quotes_after'] = len(after)
            if after:
                mb = max(b for _, b, _ in after)
                o['max_bid'] = mb; o['max_bid_minute'] = next(m for m, b, _ in after if b == mb)
            for name, t in TR.items():
                peak, hit = ea, None
                for m, b, _ in after:
                    peak = max(peak, b)
                    if b <= (1 - t) * peak + 1e-9:
                        hit = (m, b, peak); break
                o[name + '_minute'], o[name + '_bid'], o[name + '_peak'] = hit if hit else (None, None, None)
            for k, v in o.items():
                if not same(r[k], v): bad += 1; print('DIFF', root, tag, r['session'], r['strike'], r['right'], r['entry_minute'], k, r[k], v)
print(f'{n} trades (every kind, every product) re-derived from raw quotes, {bad} differences')
if bad: raise SystemExit(1)
