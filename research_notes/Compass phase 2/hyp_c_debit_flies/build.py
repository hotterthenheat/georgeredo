"""Hypothesis C, step 1: build the structures from the raw chains, one read per session.

(a) DEBIT VERTICALS at every universe A and B entry the audit stored (exits_sizing/out/paths_<P>.parquet, the same rows
    engine.load() keeps: quotes_after >= 5; half days dropped here). At the entry minute e, every same-side contract with a
    valid quote and mid - intrinsic > 0.01 gets a BSM delta (r = q = 0) on its mid; cells:
      d60_40: long the strike whose |delta| is nearest 0.60, short the one nearest 0.40 (0.70/0.30, 0.55/0.45 likewise);
      atm_otm1: long the strike nearest spot (a tie -> the in-the-money one), short the next strike out of the money.
    The long must be strictly more in the money than the short, the long's ask > 0, the short's bid > 0, else no structure.
    Each leg's bid/ask path from e to the close is stored once per (session, side, strike) in out/legs_<P>.parquet; the
    structures (entry, strikes, debit, settle) in out/spreads_<P>.parquet. Both are rebuildable from the raw files.
(b) BUTTERFLIES at 15:00 (m = 330) and 15:30 (m = 360): ATM strike K0 = the strike nearest spot that has a call and a put
    quoted; wings W in FLY_WINGS[P] and W = the ATM straddle's mid rounded to the strike grid (min one step); long call fly
    (buy K0-W, sell 2 K0, buy K0+W), long put fly, iron fly (sell the K0 straddle, buy the K0-W put and the K0+W call), all
    at the NBBO, held to settlement; out/flies_<P>.parquet.

  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build.py [PRODUCT ...]     (LIMIT=n for a test)
"""
import os, sys, time, json
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ENTRY_COLS = ['product', 'session', 'universe', 'side', 'strike', 'entry_m', 'level', 'spot_entry', 'entry_ask', 'entry_bid', 'close_m', 'half_day', 'spot_close', 'settle', 'quotes_after', 'vix']

def entries_for(root):
    df = pl.read_parquet(os.path.join(AUDIT_EXITS, 'out', f'paths_{root}.parquet'), columns=ENTRY_COLS)
    return df.filter(pl.col('quotes_after') >= 5).sort('session', 'universe', 'entry_m')

def slice_minute(c, m):
    return c.filter(pl.col('m') == m)

def side_table(q, side, S):
    """strikes of one side at one minute with bid/ask/mid, |delta| from the mid (NaN where unreadable), sorted by strike."""
    t = q.filter(pl.col('right') == side).sort('strike')
    if t.height == 0: return None
    K = t['strike'].to_numpy(); bid = t['bid'].to_numpy(); ask = t['ask'].to_numpy(); mid = (bid + ask) / 2
    v = total_vol_from_mid(np.full(K.shape, S), K, mid, np.full(K.shape, side == 'CALL'))
    dl = np.abs(bs_delta(np.full(K.shape, S), K, np.where(np.isnan(v), 1e-3, v), np.full(K.shape, side == 'CALL')))
    dl = np.where(np.isnan(v), np.nan, dl)
    return dict(K=K, bid=bid, ask=ask, mid=mid, delta=dl, v=v)

def pick_delta(tab, side, d_long, d_short):
    ok = ~np.isnan(tab['delta'])
    if ok.sum() < 2: return None
    K = tab['K']; dl = tab['delta']
    iL = np.where(ok)[0][np.argmin(np.abs(dl[ok] - d_long))]; iS = np.where(ok)[0][np.argmin(np.abs(dl[ok] - d_short))]
    more_itm = (K[iL] > K[iS]) if side == 'PUT' else (K[iL] < K[iS])
    if not more_itm: return None
    return iL, iS

def pick_atm(tab, side, S):
    K = tab['K']
    dist = np.abs(K - S); i0 = int(np.argmin(dist))
    ties = np.where(np.abs(dist - dist[i0]) < 1e-9)[0]
    if len(ties) > 1: i0 = int(ties.max()) if side == 'PUT' else int(ties.min())     # the in-the-money one
    iS = i0 - 1 if side == 'PUT' else i0 + 1
    if iS < 0 or iS >= len(K): return None
    return i0, iS

def leg_paths(c, side, K):
    p = c.filter((pl.col('strike') == K) & (pl.col('right') == side)).sort('m')
    return to_arr(p, 'm', 'bid'), to_arr(p, 'm', 'ask')

def build_session(root, d, ents, legs_store, fr, c):
    rows = []
    for r in ents.iter_rows(named=True):
        e = int(r['entry_m']); side = r['side']; S = float(r['spot_entry'])
        q = slice_minute(c, e)
        tab = side_table(q, side, S)
        if tab is None: continue
        cells = {}
        for name, (dL, dS) in DELTA_CELLS.items(): cells[name] = pick_delta(tab, side, dL, dS)
        cells['atm_otm1'] = pick_atm(tab, side, S)
        for name, pk in cells.items():
            if pk is None:
                rows.append(dict(product=root, session=d, universe=r['universe'], side=side, entry_m=e, cell=name, ok=False)); continue
            iL, iS = pk
            KL, KS = float(tab['K'][iL]), float(tab['K'][iS])
            askL, bidL, bidS, askS = float(tab['ask'][iL]), float(tab['bid'][iL]), float(tab['bid'][iS]), float(tab['ask'][iS])
            if askL <= 0 or bidS <= 0:
                rows.append(dict(product=root, session=d, universe=r['universe'], side=side, entry_m=e, cell=name, ok=False)); continue
            debit = askL - bidS
            if debit <= 0:
                rows.append(dict(product=root, session=d, universe=r['universe'], side=side, entry_m=e, cell=name, ok=False)); continue
            for K in (KL, KS):
                key = (side, K)
                if key not in legs_store:
                    b, a = leg_paths(c, side, K); legs_store[key] = (b, a)
            sc = fr['spot_close']
            settle = intrinsic(sc, KL, side) - intrinsic(sc, KS, side)
            rows.append(dict(product=root, session=d, universe=r['universe'], side=side, entry_m=e, cell=name, ok=True,
                             k_long=KL, k_short=KS, width=abs(KL - KS), ask_long=askL, bid_long=bidL, bid_short=bidS, ask_short=askS,
                             delta_long=float(tab['delta'][iL]), delta_short=float(tab['delta'][iS]), vol_long=float(tab['v'][iL]), vol_short=float(tab['v'][iS]),
                             debit=debit, settle=settle, spot_entry=S, spot_close=sc, close_m=fr['close_m'], level=r['level'],
                             naked_strike=r['strike'], naked_ask=r['entry_ask'], naked_settle=r['settle'],
                             n_side_quoted=int(len(tab['K'])), n_side_delta=int((~np.isnan(tab['delta'])).sum())))
    return rows

def build_flies(root, d, fr, c):
    rows = []
    step = STRIKE_STEP[root]
    for tag, m in FLY_TIMES.items():
        S = fr['spot'][m]
        if np.isnan(S) or m >= fr['close_m']: continue
        q = slice_minute(c, m)
        calls = q.filter(pl.col('right') == 'CALL').sort('strike'); puts = q.filter(pl.col('right') == 'PUT').sort('strike')
        if calls.height == 0 or puts.height == 0: continue
        cq = {float(k): (b, a) for k, b, a in zip(calls['strike'], calls['bid'], calls['ask'])}
        pq = {float(k): (b, a) for k, b, a in zip(puts['strike'], puts['bid'], puts['ask'])}
        both = np.array(sorted(set(cq) & set(pq)))
        if both.size == 0: continue
        K0 = float(both[np.argmin(np.abs(both - S))])
        strad = (cq[K0][0] + cq[K0][1]) / 2 + (pq[K0][0] + pq[K0][1]) / 2
        w_str = max(step, round(strad / step) * step)
        wings = [(f'w{w:g}', w) for w in FLY_WINGS[root]] + [('wstraddle', w_str)]
        sc = fr['spot_close']
        for wname, W in wings:
            lo, hi = K0 - W, K0 + W
            for kind in ('call', 'put', 'iron'):
                if kind == 'call':
                    if lo not in cq or hi not in cq: continue
                    debit = cq[lo][1] + cq[hi][1] - 2 * cq[K0][0]; credit = np.nan
                    if cq[K0][0] <= 0: continue
                    pay = intrinsic(sc, lo, 'CALL') - 2 * intrinsic(sc, K0, 'CALL') + intrinsic(sc, hi, 'CALL')
                    risk = debit; legs = 4
                elif kind == 'put':
                    if lo not in pq or hi not in pq: continue
                    debit = pq[lo][1] + pq[hi][1] - 2 * pq[K0][0]; credit = np.nan
                    if pq[K0][0] <= 0: continue
                    pay = intrinsic(sc, lo, 'PUT') - 2 * intrinsic(sc, K0, 'PUT') + intrinsic(sc, hi, 'PUT')
                    risk = debit; legs = 4
                else:
                    if lo not in pq or hi not in cq: continue
                    if cq[K0][0] <= 0 or pq[K0][0] <= 0: continue
                    credit = cq[K0][0] + pq[K0][0] - pq[lo][1] - cq[hi][1]; debit = np.nan
                    pay = -intrinsic(sc, K0, 'CALL') - intrinsic(sc, K0, 'PUT') + intrinsic(sc, lo, 'PUT') + intrinsic(sc, hi, 'CALL')
                    risk = W - credit; legs = 4
                if not np.isfinite(risk) or risk < MIN_DEBIT: continue
                pnl = (pay - debit) * 100 - legs * FEE if kind != 'iron' else (credit + pay) * 100 - legs * FEE
                rows.append(dict(product=root, session=d, t=tag, m=m, kind=kind, wing=wname, W=W, K0=K0, spot=S, straddle=strad, debit=debit, credit=credit,
                                 risk=risk, payoff=pay, pnl=pnl, pct=pnl / (risk * 100), spot_close=sc, close_m=fr['close_m'],
                                 max_gain=(W - debit) * 100 - legs * FEE if kind != 'iron' else credit * 100 - legs * FEE))
    return rows

def run(root):
    ents = entries_for(root)
    days = sorted(f[:-8] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    if os.environ.get('LIMIT'): days = days[:int(os.environ['LIMIT'])]
    by_day = {k[0]: g for k, g in ents.group_by(['session'])}
    t0 = time.time(); srows = []; frows = []; lrows = []; nhalf = 0; nmiss = 0
    for i, d in enumerate(days):
        try:
            fr = session_frame(root, d)
        except FileNotFoundError:
            nmiss += 1; continue
        if fr is None: nmiss += 1; continue
        if fr['half']: nhalf += 1; continue
        c = read_chain(root, d)
        if c.height == 0: nmiss += 1; continue
        legs = {}
        if d in by_day: srows += build_session(root, d, by_day[d], legs, fr, c)
        frows += build_flies(root, d, fr, c)
        for (side, K), (b, a) in legs.items():
            lrows.append(dict(product=root, session=d, side=side, strike=K, bid=b.astype(np.float32).tolist(), ask=a.astype(np.float32).tolist()))
        if i % 100 == 0: print(root, i, len(days), len(srows), len(frows), f'{time.time()-t0:.0f}s', flush=True)
    pl.DataFrame(srows, infer_schema_length=None).write_parquet(os.path.join(OUT, f'spreads_{root}.parquet'), compression='zstd')
    pl.DataFrame(frows, infer_schema_length=None).write_parquet(os.path.join(OUT, f'flies_{root}.parquet'), compression='zstd')
    pl.DataFrame(lrows, infer_schema_length=None).write_parquet(os.path.join(OUT, f'legs_{root}.parquet'), compression='zstd')
    sd = pl.DataFrame(srows, infer_schema_length=None)
    info = dict(product=root, sessions=len(days), half_days_dropped=nhalf, missing=nmiss, entries=ents.height, structures=int(sd.filter(pl.col('ok')).height) if sd.height else 0,
                no_structure=int(sd.filter(~pl.col('ok')).height) if sd.height else 0, flies=len(frows), legs=len(lrows), seconds=round(time.time() - t0))
    print(json.dumps(info), flush=True)
    with open(os.path.join(LOGS, f'build_{root}.json'), 'w') as f: json.dump(info, f)

if __name__ == '__main__':
    for root in (sys.argv[1:] or PRODUCTS): run(root)
