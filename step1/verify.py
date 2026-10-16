"""Step 1b check: re-derive random contracts from the raw quotes with plain Python loops (no shared code with
breakdown.py) and compare every figure with the table. Any difference stops the script.
  python3 -I step1/verify.py [N]
"""
import datetime as dt, os, random, sys
import polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
random.seed(20261016)

def minute(ts): return ts.hour * 60 + ts.minute - 570

def close_of(d):
    rows = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet')).to_dicts()
    last = max(r['timestamp'] for r in rows if r['close'] is not None)
    return 210 if last.hour < 15 else 390

def spot_at(root, d, close_m):
    if root == 'SPXW':
        rows = [(minute(r['timestamp']), r['price']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).to_dicts() if r['price'] is not None]
    else:   # a bar stamped t closes at t + 1 minute
        rows = [(minute(r['timestamp']) + 1, r['close']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'underlying', root, f'{d}.parquet')).to_dicts() if r['close'] is not None]
    rows = [x for x in rows if x[0] <= close_m]
    return rows[0][1], rows[-1][1]

def derive(root, d, strike, right):
    close_m = close_of(d)
    raw = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).filter((pl.col('strike') == strike) & (pl.col('right') == right)).sort('timestamp').to_dicts()
    q = [(minute(r['timestamp']), r['bid'], r['ask']) for r in raw
         if 1 <= minute(r['timestamp']) <= close_m and r['bid'] is not None and r['ask'] is not None and r['ask'] >= r['bid'] and r['bid'] >= 0]
    s0, s1 = spot_at(root, d, close_m)
    settle = max(s1 - strike, 0.0) if right == 'CALL' else max(strike - s1, 0.0)
    mids = [(b + a) / 2 for _, b, a in q]
    hi = max(mids); lo = min(mids)
    best_long = settle - min(a for _, _, a in q)
    best_short = max(b for _, b, _ in q) - settle
    for i in range(len(q)):
        for j in range(i + 1, len(q)):
            best_long = max(best_long, q[j][1] - q[i][2])
            best_short = max(best_short, q[i][1] - q[j][2])
    return dict(quoted_minutes=len(q), open_minute=q[0][0], open_bid=q[0][1], open_ask=q[0][2], close_bid=q[-1][1], close_ask=q[-1][2],
                high=hi, high_minute=q[mids.index(hi)][0], low=lo, low_minute=q[mids.index(lo)][0],
                best_bid=max(b for _, b, _ in q), best_ask=min(a for _, _, a in q), spot_open=s0, spot_close=s1, settle=settle,
                buy_open_hold=settle - q[0][2], sell_open_hold=q[0][1] - settle, best_long=best_long, best_short=best_short)

bad, n = 0, 0
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    T = pl.read_parquet(os.path.join(OUT, f'contracts_{root}.parquet'))
    # half-day sessions get extra weight so the 13:00 close is checked too
    half = T.filter(pl.col('half_day'))
    picks = [T.row(random.randrange(T.height), named=True) for _ in range(N // 4 - 10)] + [half.row(random.randrange(half.height), named=True) for _ in range(10)]
    for r in picks:
        x = derive(root, r['session'], r['strike'], r['right']); n += 1
        for k, v in x.items():
            if abs(float(r[k]) - float(v)) > 1e-9:
                bad += 1; print('DIFF', root, r['session'], r['strike'], r['right'], k, r[k], v)
print(f'{n} contracts re-derived from raw quotes, {bad} differences')
if bad: raise SystemExit(1)
