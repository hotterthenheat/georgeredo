"""Independent check of extract.py and engine.py with plain Python loops, on a random sample of trades.
(1) Re-derives each sampled trade from the raw files: the entry minute and side (universe A's event), the nearest-OTM
strike, the entry ask, the settle and the highest bid after entry. (2) Replays four exit rules minute by minute in a
plain loop and compares with engine.simulate. Prints the number of differences (must be 0).
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I verify.py
"""
import os, sys, math, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from extract import RAW, UNDERLYING, mcol

def raw_session(root, d):
    u = UNDERLYING[root]
    chain = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).with_columns(mcol().alias('m'))
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet')).filter(pl.col('close').is_not_null())
    close_m = 210 if spy['timestamp'].max().hour < 15 else 390
    if u == 'SPX':
        spx = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).with_columns(mcol().alias('m')).filter(pl.col('price').is_not_null())
        spot = dict(zip(spx['m'].to_list(), spx['price'].to_list()))
        bars = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet')).with_columns(mcol().alias('m')).filter(pl.col('close').is_not_null())
        spyc = {m + 1: c for m, c in zip(bars['m'].to_list(), bars['close'].to_list())}
        rat = [spot[m] / spyc[m] for m in range(25, 35) if m in spot and m in spyc]; ratio = float(np.median(rat))
        bh = {m: h * ratio for m, h in zip(bars['m'].to_list(), bars['high'].to_list())}; bl = {m: l * ratio for m, l in zip(bars['m'].to_list(), bars['low'].to_list())}
        bc = {m: c * ratio for m, c in zip(bars['m'].to_list(), bars['close'].to_list())}
    else:
        bars = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet')).with_columns(mcol().alias('m')).filter(pl.col('close').is_not_null())
        bh = dict(zip(bars['m'].to_list(), bars['high'].to_list())); bl = dict(zip(bars['m'].to_list(), bars['low'].to_list())); bc = dict(zip(bars['m'].to_list(), bars['close'].to_list()))
        spot = {m + 1: c for m, c in bc.items()}
    return chain, close_m, spot, bh, bl, bc

def check_entry(t, chain, close_m, spot, bh, bl, bc):
    errs = []
    rh = max(bh[m] for m in range(0, 30) if m in bh); rl = min(bl[m] for m in range(0, 30) if m in bl)
    if t['universe'] == 'A':
        found = None
        for bm in range(30, 150):
            if bm not in bh: continue
            if t['side'] == 'PUT' and bh[bm] >= rh * (1 + 2e-4) and bc[bm] < rh: found = bm + 1; break
            if t['side'] == 'CALL' and bl[bm] <= rl * (1 - 2e-4) and bc[bm] > rl: found = bm + 1; break
        if found != t['entry_m']: errs.append(('entry_m', found, t['entry_m']))
        if abs((rh if t['side'] == 'PUT' else rl) - t['level']) > 1e-6: errs.append(('level',))
    em = t['entry_m']; s = spot[em]
    q = chain.filter((pl.col('m') == em) & (pl.col('right') == t['side']) & pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0) & (pl.col('ask') > 0))
    ks = [k for k in q['strike'].to_list() if (k < s if t['side'] == 'PUT' else k > s)]
    k = max(ks) if t['side'] == 'PUT' else min(ks)
    if abs(k - t['strike']) > 1e-9: errs.append(('strike', k, t['strike']))
    row = q.filter(pl.col('strike') == k).row(0, named=True)
    if abs(row['ask'] - t['entry_ask']) > 1e-9: errs.append(('entry_ask', row['ask'], t['entry_ask']))
    path = chain.filter((pl.col('strike') == k) & (pl.col('right') == t['side']) & (pl.col('m') > em) & (pl.col('m') <= close_m) & pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0) & (pl.col('ask') > 0))
    mb = path['bid'].max()
    sc = spot[max(m for m in spot if m <= close_m)]
    settle = max(sc - k, 0) if t['side'] == 'CALL' else max(k - sc, 0)
    if abs(settle - t['settle']) > 1e-6: errs.append(('settle', settle, t['settle']))
    return errs, dict(zip(path['m'].to_list(), path['bid'].to_list())), mb, (bh, bl)

def loop_exit(t, bids, bh, bl, rule, close_m):
    """plain-loop replay of a rule: returns (exit minute, exit price, reason)"""
    a = t['entry_ask']; e = t['entry_m']; hf = 388 if close_m == 390 else 208
    peak = -math.inf; lock = False; last_bid = None
    lvl = t['level'] if t['universe'] == 'A' else (t['spot_entry'] * (1 + 15e-4) if t['side'] == 'PUT' else t['spot_entry'] * (1 - 15e-4))
    buf = 2e-4 if t['universe'] == 'A' else 0.0
    tr = {'vix': (0.06 if t['vix'] < 15 else 0.08 if t['vix'] < 20 else 0.11 if t['vix'] < 30 else 0.14)}.get(rule.get('trail'), rule.get('trail'))
    for m in range(e + 1, close_m + 1):
        b = bids.get(m)
        # structural: bar stamped m-1 closed at m
        if rule.get('struct') and (m - 1) >= e and (m - 1) in bh:
            if (t['side'] == 'PUT' and bh[m - 1] >= lvl * (1 + buf)) or (t['side'] == 'CALL' and bl[m - 1] <= lvl * (1 - buf)):
                px = b if b is not None else last_bid
                return m, px, 'struct'
        if b is None: 
            if m == hf and rule.get('flat', True): return m, last_bid, 'flat'
            continue
        if rule.get('target') and b >= rule['target'] * a - 1e-9: return m, rule['target'] * a, 'target'
        if rule.get('prem') and b <= rule['prem'] * a + 1e-9: return m, b, 'prem_stop'
        if rule.get('be') is not None and lock and b <= a + 1e-9: return m, b, 'be_lock'
        if tr is not None and peak >= 1.06 * a - 1e-9 and b <= (1 - tr) * peak + 1e-9: return m, b, 'trail'
        if rule.get('time') and m == e + rule['time'] and max(peak, b) < 1.06 * a - 1e-9: return m, b, 'time'
        peak = max(peak, b)
        if rule.get('be') is not None and peak >= (1 + rule['be']) * a - 1e-9: lock = True
        if m == hf and rule.get('flat', True): return m, b, 'flat'
        last_bid = b
    return None, None, 'settle'

RULES = [('prem32', dict(prem=0.68), dict(prem_stop=0.68)),
         ('spec', dict(prem=0.68, struct=True, be=0.06, trail='vix', time=5, target=1.25), None),
         ('trail20', dict(prem=0.68, trail=0.20), dict(prem_stop=0.68, trail=0.20, trail_act=0.06)),
         ('be12_t50', dict(prem=0.68, be=0.12, target=1.5), dict(prem_stop=0.68, be_lock=0.12, targets=((1, 1.5),)))]

if __name__ == '__main__':
    rng = np.random.default_rng(3)
    P = E.load()
    pick = rng.choice(P.n, 80, replace=False)
    sims = {}
    for name, _, kw in RULES:
        if kw is None:
            kw = dict(prem_stop=0.68, be_lock=0.06, trail='vix', trail_act=0.06, time_stop=5, time_prog=0.06, targets=((1, 1.25),))
            # struct differs by universe: run per universe
            resA = E.simulate(P, struct_buffer=2.0, **kw); resB = E.simulate(P, struct_buffer=0.0, b_bps=15.0, **kw)
            sims[name] = (resA, resB)
        else:
            sims[name] = (E.simulate(P, **kw),) * 2
    n_err = 0; n_ok = 0
    for i in pick:
        t = P.df.row(int(i), named=True)
        chain, close_m, spot, bh, bl, bc = raw_session(t['product'], t['session'])
        errs, bids, mb, _ = check_entry(t, chain, close_m, spot, bh, bl, bc)
        emb = np.nanmax(P.Bw[i]) if np.any(~np.isnan(P.Bw[i])) else None
        if emb is None or abs(mb - emb) > 1e-6: errs.append(('max_bid', mb, emb))
        for name, lr, _ in RULES:
            res = sims[name][0 if t['universe'] == 'A' else 1]
            lm, lpx, lr_ = loop_exit(t, bids, bh, bl, lr, close_m)
            leg = res['legs'][0]; em = int(leg['exit_m'][i]); epx = float(leg['price'][i]); er = str(leg['reason'][i])
            if lr_ == 'settle' or lpx is None or lpx <= 0: lpx = t['settle']; lr_ = 'settle'
            same_fill = abs(epx - lpx) <= 1e-6 and (lr_ == 'settle' or lm == em)
            if not same_fill or (er != lr_ and not same_fill): errs.append((name, (lm, lpx, lr_), (em, epx, er)))
        if errs: n_err += 1; print(t['product'], t['session'], t['universe'], t['side'], errs)
        else: n_ok += 1
    print('trades checked', len(pick), 'ok', n_ok, 'with differences', n_err)
