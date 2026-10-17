"""Step 5c check: random trades with volume, their volume measurements re-derived from the raw one-minute bars and quotes
with plain Python loops (no shared code with volume.py). Any difference stops the script.
  python3 -I step5/verify_volume.py [N per product] [PRODUCTS]
"""
import math, os, random, sys
import polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
ROOTS = sys.argv[2].split(',') if len(sys.argv) > 2 else ['SPY', 'QQQ', 'IWM', 'SPXW']
random.seed(20261016)

def minute(ts): return ts.hour * 60 + ts.minute - 570
def ratio(a, b): return a / b if b else None
def clean(x): return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else x

bad, n = 0, 0
for root in ROOTS:
    f = os.path.join(OUT, f'volume_features_{root}.parquet')
    if not os.path.exists(f): continue
    V = pl.read_parquet(f).filter(pl.col('has_vol') == 1)
    F = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet'), columns=['session', 'tag', 'strike', 'right', 'entry_minute', 'close_minute'])
    V = V.join(F, on=['session', 'tag', 'strike', 'right', 'entry_minute'])
    for _ in range(N):
        r = V.row(random.randrange(V.height), named=True); n += 1
        d, m, close_m, k, side = r['session'], r['entry_minute'], r['close_minute'], r['strike'], r['right']
        bars = [x for x in pl.read_parquet(os.path.join(RAW, 'data', 'ohlc', root, f'{d}.parquet')).to_dicts() if 0 <= minute(x['timestamp']) < close_m]
        quotes = {}
        for x in pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).filter((pl.col('strike') == k) & (pl.col('right') == side)).to_dicts():
            if x['bid'] is not None and x['ask'] is not None and x['ask'] >= x['bid'] >= 0:
                quotes[minute(x['timestamp'])] = (x['bid'] + x['ask']) / 2
        mine = {minute(x['timestamp']): x for x in bars if x['strike'] == k and x['right'] == side}
        def vsum(lo, hi, who='me', field='volume'):
            if who == 'me': return sum(x[field] or 0 for j, x in mine.items() if lo <= j <= hi)
            return sum(x['volume'] or 0 for x in bars if lo <= minute(x['timestamp']) <= hi and (who == 'both' or x['right'] == who))
        o = dict(vol_day=vsum(0, m - 1), vol_1=vsum(m - 1, m - 1), vol_5=vsum(m - 5, m - 1), vol_15=vsum(m - 15, m - 1), trades_5=vsum(m - 5, m - 1, field='count'))
        buy = judged = 0
        for j in range(m - 5, m):
            x = mine.get(j)
            if x is None or not x['volume'] or j not in quotes or j + 1 not in quotes: continue
            mid = (quotes[j] + quotes[j + 1]) / 2
            judged += x['volume']
            if x['close'] is not None and x['close'] > mid + 1e-9: buy += x['volume']
        o['buy_share5'] = ratio(buy, judged)
        sv5, svd, bv5, bvd = vsum(m - 5, m - 1, side), vsum(0, m - 1, side), vsum(m - 5, m - 1, 'both'), vsum(0, m - 1, 'both')
        o.update(burst5=ratio(o['vol_5'], o['vol_day'] / m * 5), size_5=ratio(o['vol_5'], o['trades_5']), side_share5=ratio(sv5, bv5),
                 side_share_day=ratio(svd, bvd), side_burst5=ratio(sv5, svd / m * 5), share_of_side5=ratio(o['vol_5'], sv5))
        for key, v in o.items():
            a, b = clean(r[key]), clean(v)
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9 * max(1.0, abs(b))):
                bad += 1; print('DIFF', root, d, k, side, m, key, r[key], v)
print(f'{n} trades\' volume measurements re-derived from the raw bars and quotes, {bad} differences')
if bad: raise SystemExit(1)
