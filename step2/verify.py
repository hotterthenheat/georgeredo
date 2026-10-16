"""Step 2b check: re-derive random (contract, entry time) rows of step2/out/entries_*.parquet from the raw quotes with
plain Python loops (no shared code with double.py's calculation) and compare every figure. Any difference stops the script.
  python3 -I step2/verify.py [N]
"""
import bisect, os, random, sys
import polars as pl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step2.double import load   # noqa: E402  (reads the stored table; every figure is checked against the raw quotes below)

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
random.seed(20261016)

def minute(ts): return ts.hour * 60 + ts.minute - 570

def close_of(d):
    rows = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet')).to_dicts()
    return 210 if max(r['timestamp'] for r in rows if r['close'] is not None).hour < 15 else 390

def spots(root, d, close_m):
    if root == 'SPXW':
        rows = [(minute(r['timestamp']), r['price']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).to_dicts() if r['price'] is not None]
    else:   # a bar stamped t closes at t + 1 minute
        rows = [(minute(r['timestamp']) + 1, r['close']) for r in pl.read_parquet(os.path.join(RAW, 'data', 'underlying', root, f'{d}.parquet')).to_dicts() if r['close'] is not None]
    return sorted(x for x in rows if x[0] <= close_m)

def derive(root, d, strike, right, e):
    close_m = close_of(d)
    raw = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).filter((pl.col('strike') == strike) & (pl.col('right') == right)).sort('timestamp').to_dicts()
    q = [(minute(r['timestamp']), r['bid'], r['ask']) for r in raw
         if 1 <= minute(r['timestamp']) <= close_m and r['bid'] is not None and r['ask'] is not None and r['ask'] >= r['bid'] and r['bid'] >= 0]
    at = [x for x in q if x[0] == e]
    assert len(at) == 1 and at[0][2] > 0, (root, d, strike, right, e)
    _, eb, ea = at[0]
    sp = spots(root, d, close_m)
    ms = [m for m, _ in sp]
    spot_e = sp[bisect.bisect_right(ms, e) - 1][1]
    s1 = sp[-1][1]
    settle = max(s1 - strike, 0.0) if right == 'CALL' else max(strike - s1, 0.0)
    after = [x for x in q if x[0] > e]
    out = dict(entry_bid=eb, entry_ask=ea, spot_entry=spot_e, spot_close=s1, settle=settle, quotes_after=len(after),
               otm_entry_pct=((strike - spot_e) if right == 'CALL' else (spot_e - strike)) / spot_e * 100, hold=settle - ea)
    dbl = next((m for m, b, _ in after if b >= 2 * ea - 1e-9), None)
    half = next(((m, b) for m, b, _ in after if b <= 0.5 * ea + 1e-9), None)
    if after:
        mb = max(b for _, b, _ in after)
        out.update(max_bid=mb, max_bid_minute=next(m for m, b, _ in after if b == mb), max_multiple=mb / ea, last_bid=after[-1][1])
    out['double_minute'] = dbl
    out['half_minute'] = half[0] if half else None
    out['tp100'] = ea if dbl is not None else settle - ea
    if half and (dbl is None or half[0] < dbl): out['tp100_sl50'] = half[1] - ea
    elif dbl is not None: out['tp100_sl50'] = ea
    else: out['tp100_sl50'] = settle - ea
    return out

bad, n = 0, 0
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    T = load(root)
    hit = T.filter(pl.col('double_minute').is_not_null())
    half = T.filter(pl.col('half_day'))
    k = N // 4
    picks = [T.row(random.randrange(T.height), named=True) for _ in range(k - 20)] + \
            [hit.row(random.randrange(hit.height), named=True) for _ in range(10)] + [half.row(random.randrange(half.height), named=True) for _ in range(10)]
    for r in picks:
        x = derive(root, r['session'], r['strike'], r['right'], r['entry_minute']); n += 1
        for key, v in x.items():
            a = r[key]
            same = (a is None and v is None) or (a is not None and v is not None and abs(float(a) - float(v)) <= 1e-9)
            if not same:
                bad += 1; print('DIFF', root, r['session'], r['strike'], r['right'], r['entry_minute'], key, a, v)
print(f'{n} entries re-derived from raw quotes, {bad} differences')
if bad: raise SystemExit(1)
