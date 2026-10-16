"""Step 5a check: random trades of every product and kind, their entry-minute features re-derived from the raw files with
plain Python loops (no shared code with features.py). Any difference stops the script.
  python3 -I step5/verify.py [N per product and kind]
"""
import os, random, statistics, sys
import polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
random.seed(20261016)

def minute(ts): return ts.hour * 60 + ts.minute - 570

def last_at(pairs, t):
    """the value of the last (minute, value) at or before t"""
    v = None
    for m, x in pairs:
        if m <= t: v = x
        else: break
    return v

def same(a, b, tol=1e-9):
    if a is None or b is None: return a is None and b is None
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))

bad, n = 0, 0
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    F = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet'))
    for tag in sorted(F['tag'].unique().to_list()):
        S = F.filter(pl.col('tag') == tag)
        for _ in range(N):
            r = S.row(random.randrange(S.height), named=True); n += 1
            d, m, close_m = r['session'], r['entry_minute'], r['close_minute']
            chain = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).to_dicts()
            q = sorted([(minute(x['timestamp']), x) for x in chain if x['bid'] is not None and x['ask'] is not None and x['ask'] >= x['bid'] >= 0 and x['ask'] > 0
                        and 1 <= minute(x['timestamp']) <= close_m], key=lambda p: p[0])
            mine = [(t, x) for t, x in q if x['strike'] == r['strike'] and x['right'] == r['right']]
            before = [(t, x['ask']) for t, x in mine if t < m]
            o = dict(open_ask=mine[0][1]['ask'], hi_before=max(a for _, a in before) if before else None)
            lo = min(a for _, a in before) if before else None
            o['low_minute'] = max(t for t, a in before if a == lo) if before else None
            at = [x for t, x in mine if t == m][0]
            o['bid_size'], o['ask_size'] = at['bid_size'], at['ask_size']
            for L in (1, 5, 15): o[f'ask_{L}'] = last_at([(t, x['ask']) for t, x in mine], m - L)
            # the underlying's price each minute 1..close_m, carried forward
            if root == 'SPXW':
                sp = [(minute(x['timestamp']), x['price']) for x in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).to_dicts() if x['price'] is not None]
            else:
                sp = [(minute(x['timestamp']) + 1, x['close']) for x in pl.read_parquet(os.path.join(RAW, 'data', 'underlying', root, f'{d}.parquet')).to_dicts() if x['close'] is not None]
            sp = sorted(p for p in sp if p[0] <= close_m)
            px = {t: last_at(sp, t) for t in range(1, close_m + 1)}
            o['px'] = px[m]
            for L in (1, 5, 15, 30): o[f'px_{L}'] = px.get(m - L)
            seen = [px[t] for t in range(1, m + 1) if px[t] is not None]
            o['hi_so_far'], o['lo_so_far'] = max(seen), min(seen)
            seen5 = [px[t] for t in range(1, m - 4) if px[t] is not None]
            o['hi_5'], o['lo_5'] = (max(seen5), min(seen5)) if seen5 else (None, None)
            r1 = [px[t] / px[t - 1] - 1 for t in range(max(2, m - 14), m + 1) if px[t] is not None and px[t - 1] is not None]
            o['rv15'] = statistics.stdev(r1) if len(r1) >= 10 else None
            vx = sorted((minute(x['timestamp']), x['price']) for x in pl.read_parquet(os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')).to_dicts()
                        if x['price'] is not None and minute(x['timestamp']) >= 1)
            vg = {t: last_at(vx, t) for t in range(1, close_m + 1)}
            o['vix'], o['vix_15'] = vg[m], vg.get(m - 15)
            o['vix_open'] = next(vg[t] for t in range(1, close_m + 1) if vg[t] is not None)
            # the at-the-money straddle at a minute: the strike nearest the price with a call and a put quoted
            bym = {}
            for tt, x in q: bym.setdefault(tt, []).append(x)
            def straddle(t):
                if px[t] is None: return None
                calls = {x['strike']: (x['bid'] + x['ask']) / 2 for x in bym.get(t, []) if x['right'] == 'CALL'}
                puts = {x['strike']: (x['bid'] + x['ask']) / 2 for x in bym.get(t, []) if x['right'] == 'PUT'}
                ks = sorted(set(calls) & set(puts), key=lambda k: (abs(k - px[t]), k))
                return calls[ks[0]] + puts[ks[0]] if ks else None
            o['straddle'] = straddle(m)
            o['straddle_open'] = next((s for s in (straddle(t) for t in sorted(bym)) if s is not None), None)
            for k, v in o.items():
                if not same(r[k], v, 1e-6 if k == 'rv15' else 1e-9): bad += 1; print('DIFF', root, tag, d, r['strike'], r['right'], m, k, r[k], v)
print(f'{n} trades\' entry-minute features re-derived from the raw files, {bad} differences')
if bad: raise SystemExit(1)
