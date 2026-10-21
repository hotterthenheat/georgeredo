"""Re-derive a random sample of events from the raw files with separate, plain-loop code and compare:
the sweep conditions (the excursion bar beyond the level, the bar before inside, the return bar's close inside),
the entry ask and bid of the nearest-OTM pick straight from the chain parquet, the trailing-stop exit minute and price,
the hold exit, the net dollars with fees, and the forward return. Prints the number of differences.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I verify.py [n_per_product]
"""
import datetime as dt, os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S

def raw_quotes(root, d, K, right):
    c = pl.read_parquet(os.path.join(S.RAW, 'data_full', 'chains', root, f'{d}.parquet'))
    c = c.filter((pl.col('strike') == K) & (pl.col('right') == ('PUT' if right == 1 else 'CALL')))
    q = {}
    for t, b, a in zip(c['timestamp'].to_list(), c['bid'].to_list(), c['ask'].to_list()):
        m = t.hour * 60 + t.minute - 570
        if b is None or a is None or a < b or b < 0 or a <= 0: continue
        q[m] = (b, a)
    return q

def check(root, row):
    d = row['session']; u = S.BAR_SOURCE[root]
    p = pl.read_parquet(os.path.join(S.RAW, 'data', 'underlying', u, f'{d}.parquet')).filter(pl.col('close').is_not_null())
    bars = {}
    for t, o, h, l, c in zip(p['timestamp'].to_list(), p['open'].to_list(), p['high'].to_list(), p['low'].to_list(), p['close'].to_list()):
        bars[t.hour * 60 + t.minute - 570 + 1] = (o, h, l, c)
    close_m = 390
    diffs = []
    e, r, L, side, X, m_in = row['e'], row['r'], row['L'], row['side'], row['X'], row['entry_m']
    if row['level'] != 'DISP' and row['k'] != '5m':
        thr = L * (1 + X / 1e4) if side == 'hi' else L * (1 - X / 1e4)
        if side == 'hi':
            if not (bars[e][1] >= thr and bars[e - 1][3] < L and bars[r][3] < L): diffs.append('sweep condition')
            if row['level'] != 'SH' and not bars[e - 1][1] < thr: diffs.append('bar before beyond the line')
        else:
            if not (bars[e][2] <= thr and bars[e - 1][3] > L and bars[r][3] > L): diffs.append('sweep condition')
        if row['confirm'] == 1:
            ok = bars[r + 1][3] < bars[r][3] if side == 'hi' else bars[r + 1][3] > bars[r][3]
            if not ok or m_in != r + 1: diffs.append('confirm bar')
    # the pick and its exits
    if row['fo_ask'] is not None and not np.isnan(row['fo_ask']):
        right = 1 if side == 'hi' else 0; K = row['fo_K']
        q = raw_quotes(root, d, K, right)
        b0, a0 = q[m_in]
        if abs(a0 - row['fo_ask']) > 1e-9 or abs(b0 - row['fo_bid']) > 1e-9: diffs.append('entry quote')
        spot = row['spot']
        if (right == 0 and K < spot) or (right == 1 and K > spot): diffs.append('pick not OTM')
        # trailing stop: first minute after entry with bid <= 0.5 * highest bid so far (entry bid included)
        peak = b0; ex = None
        for t in range(m_in + 1, S.LAST_SELL + 1):
            if t not in q: continue
            bt = q[t][0]; peak = max(peak, bt)
            if peak > 0 and bt <= 0.5 * peak: ex = (t, bt); break
        if ex is None:
            last = [t for t in range(m_in + 1, S.LAST_SELL + 1) if t in q]
            if last and q[last[-1]][0] > 0: ex = (last[-1], q[last[-1]][0])
            else:
                sp = S.read_prints('SPX', d)[close_m] if root == 'SPXW' else bars[close_m][3]
                ex = (S.LAST_SELL, max(sp - K, 0) if right == 0 else max(K - sp, 0))
        net = (ex[1] - a0) * 100 - (2 * S.FEE if ex[1] > 0 or ex[0] != S.LAST_SELL else S.FEE)
        if ex[1] == 0 and ex[0] == S.LAST_SELL: net = (ex[1] - a0) * 100 - S.FEE
        if ex[0] != row['fo_trail_m'] or abs(ex[1] - row['fo_trail_px']) > 1e-9: diffs.append(f'trail exit {ex} vs {(row["fo_trail_m"], row["fo_trail_px"])}')
        elif abs(net - row['fo_trail_net']) > 1e-6: diffs.append(f'trail net {net} vs {row["fo_trail_net"]}')
    # forward return from the entry minute
    s = -1 if side == 'hi' else 1
    t = min(m_in + 30, close_m); f30 = s * (bars[t][3] - bars[m_in][3]) / bars[m_in][3] * 1e4
    if abs(f30 - row['fwd_30']) > 1e-6: diffs.append(f'fwd_30 {f30} vs {row["fwd_30"]}')
    return diffs

if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    rng = np.random.default_rng(3); total = 0; bad = 0
    for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        E = pl.read_parquet(os.path.join(S.OUT, f'events_{root}.parquet'))
        idx = rng.choice(E.height, size=min(n, E.height), replace=False)
        for i in idx:
            row = E.row(int(i), named=True); d = check(root, row); total += 1
            if d: bad += 1; print(root, row['session'], row['level'], row['side'], row['X'], row['k'], row['confirm'], row['entry_m'], d)
    print('checked', total, 'differences', bad)
