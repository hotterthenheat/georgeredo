"""The contract-level lifecycle archive (deliverable 2): for every contract of a same-day chain with |delta| in
[0.05, 0.95] and every 5-minute entry instant from 09:35 to 15:45, what an entry there could have done.

Columns (prices per share; P&L per contract in dollars after $0.70 a side is in the analysis, not here):
  identity      root, session, expiration, strike, right, m (entry instant: minutes after 09:30)
  entry         bid0, ask0, mid0, rel_spread0, bid_size0, ask_size0, spot0, iv0, delta0, gamma0, theta0 (per day), vega0
                (per vol point), t_years
  executable    liq{15,30,60}: the bid at m+15/30/60; liq_cut: the bid at 15:50; best_bid / t_best: the highest bid in
                (m, 15:50] and its minute offset; worst_bid / t_worst: the lowest; best_bid{15,30,60}: the highest bid
                within the horizon
  theoretical   best_mid / t_best_mid: the highest mid in (m, 16:00] (hindsight, not a fill)
  expiry        settle: intrinsic at the 16:00 underlying value
  underlying    spot{15,30,60}, spot_cut, spot_max, spot_min over (m, 15:50]
An entry is executable at the ask; every exit column is a bid, so (bid - ask) x 100 is the executable round trip.
Hindsight columns (best_*, t_best*) are retrospective: no rule could know them at the entry."""
from __future__ import annotations
import datetime as dt, json, os, sys, time
import numpy as np
import polars as pl
from numba import njit
from . import paths, chainmat as cm, aux as ax, bs

GRID = np.arange(5, 376, 5)          # 09:35 .. 15:45
CUT = 380
H = (15, 30, 60)

@njit(cache=True)
def _forward(bid, ask, spot, ms, cut, last):
    C = bid.shape[0]; G = ms.size
    out = np.full((C, G, 20), np.nan)
    for c in range(C):
        for gi in range(G):
            m = ms[gi]
            b0 = bid[c, m]; a0 = ask[c, m]
            if not (b0 == b0 and a0 == a0 and a0 > 0 and a0 >= b0): continue
            bb = -1.0; tb = -1; wb = 1e18; tw = -1; bm = -1.0; tbm = -1
            hb = np.array([-1.0, -1.0, -1.0])
            smax = -1e18; smin = 1e18
            for k in range(m + 1, last + 1):
                b = bid[c, k]; a = ask[c, k]
                ok = b == b and a == a and a > 0 and a >= b
                if ok:
                    mid = 0.5 * (a + b)
                    if mid > bm: bm = mid; tbm = k - m
                    if k <= cut:
                        if b > bb: bb = b; tb = k - m
                        if b < wb: wb = b; tw = k - m
                        for h in range(3):
                            if k - m <= (15, 30, 60)[h] and b > hb[h]: hb[h] = b
                if k <= cut:
                    s = spot[k]
                    if s > smax: smax = s
                    if s < smin: smin = s
            o = out[c, gi]
            for h in range(3):
                k = m + (15, 30, 60)[h]
                if k <= last and bid[c, k] == bid[c, k]: o[h] = bid[c, k]
                if k <= last: o[10 + h] = spot[k]
                o[16 + h] = hb[h] if hb[h] >= 0 else np.nan
            if bid[c, cut] == bid[c, cut]: o[3] = bid[c, cut]
            o[4] = bb if tb >= 0 else np.nan; o[5] = tb if tb >= 0 else np.nan
            o[6] = wb if tw >= 0 else np.nan; o[7] = tw if tw >= 0 else np.nan
            o[8] = bm if tbm >= 0 else np.nan; o[9] = tbm if tbm >= 0 else np.nan
            o[13] = spot[cut]; o[14] = smax; o[15] = smin
            o[19] = 1.0
    return out

FWD = ['liq15', 'liq30', 'liq60', 'liq_cut', 'best_bid', 't_best', 'worst_bid', 't_worst', 'best_mid', 't_best_mid',
       'spot15', 'spot30', 'spot60', 'spot_cut', 'spot_max', 'spot_min', 'best_bid15', 'best_bid30', 'best_bid60', 'ok']

def session_rows(cd) -> pl.DataFrame | None:
    if cd.n_min < 391: return None                       # half days stay out of the archive (their grid ends at 13:00)
    tg = ax.t_years_grid(cd)
    ms = GRID.astype(np.int64)
    F = _forward(cd.bid, cd.ask, cd.spot, ms, CUT, cd.n_min - 1)
    C = cd.strike.size; G = ms.size
    sgn = np.where(cd.is_call, 1.0, -1.0)
    rows = {k: [] for k in ['ci', 'm', 'bid0', 'ask0', 'bsz0', 'asz0', 'spot0', 'iv0', 'delta0', 't_years']}
    fw = []
    for gi, m in enumerate(ms):
        b = cd.bid[:, m]; a = cd.ask[:, m]
        ok = np.isfinite(b) & np.isfinite(a) & (a > 0) & (a >= b)
        mid = np.where(ok, (a + b) / 2, np.nan)
        S = np.full(C, cd.spot[m]); t = np.full(C, tg[m])
        iv = bs.implied_vol(mid, S, cd.strike, t, sgn)
        d = bs.delta(S, cd.strike, t, np.where(np.isnan(iv), 0.3, iv), sgn)
        keep = ok & np.isfinite(iv) & (np.abs(d) >= 0.05) & (np.abs(d) <= 0.95)
        idx = np.where(keep)[0]
        if idx.size == 0: continue
        rows['ci'].append(idx); rows['m'].append(np.full(idx.size, m)); rows['bid0'].append(b[idx]); rows['ask0'].append(a[idx])
        rows['bsz0'].append(cd.bid_size[idx, m]); rows['asz0'].append(cd.ask_size[idx, m]); rows['spot0'].append(S[idx])
        rows['iv0'].append(iv[idx]); rows['delta0'].append(d[idx]); rows['t_years'].append(t[idx])
        fw.append(F[idx, gi, :])
    if not fw: return None
    R = {k: np.concatenate(v) for k, v in rows.items()}
    FW = np.vstack(fw)
    ci = R.pop('ci')
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.dirname(paths.HERE))
    from engine import greeks as g
    S0 = R['spot0']; K = cd.strike[ci]; iv0 = R['iv0']; tt = R['t_years']; sg = sgn[ci]
    gam = g.gamma(S0, K, tt, iv0); veg = g.vega_point(S0, K, tt, iv0); the = bs.theta_day(S0, K.astype(np.float64), tt, iv0, sg)
    settle = np.where(cd.is_call[ci], np.maximum(cd.spot[-1] - K, 0), np.maximum(K - cd.spot[-1], 0))
    df = pl.DataFrame({'root': [cd.root] * ci.size, 'session': [cd.session] * ci.size, 'strike': K.astype(np.float32),
                       'right': np.where(cd.is_call[ci], 'C', 'P'), 'm': R['m'].astype(np.int16),
                       'bid0': R['bid0'].astype(np.float32), 'ask0': R['ask0'].astype(np.float32),
                       'bid_size0': R['bsz0'].astype(np.int32), 'ask_size0': R['asz0'].astype(np.int32),
                       'spot0': S0.astype(np.float32), 'iv0': iv0.astype(np.float32), 'delta0': R['delta0'].astype(np.float32),
                       'gamma0': gam.astype(np.float32), 'theta0': the.astype(np.float32), 'vega0': veg.astype(np.float32),
                       't_years': tt.astype(np.float32), 'settle': settle.astype(np.float32)})
    df = df.with_columns(((pl.col('ask0') + pl.col('bid0')) / 2).alias('mid0'),
                         ((pl.col('ask0') - pl.col('bid0')) / ((pl.col('ask0') + pl.col('bid0')) / 2)).alias('rel_spread0'))
    for j, name in enumerate(FWD[:-1]):
        df = df.with_columns(pl.Series(name, FW[:, j].astype(np.float32)))
    return df

def build(root: str, log=print, sessions=None):
    out = f'{paths.WORK}/archive/{root}'; os.makedirs(out, exist_ok=True)
    ss = sessions or cm.sessions_0dte(root)
    jobs = f'{out}/jobs.jsonl'
    done = set()
    if os.path.exists(jobs):
        for l in open(jobs):
            r = json.loads(l)
            if r.get('status') == 'ok': done.add(r['month'])
    months = sorted({(d.year, d.month) for d in ss})
    for (y, mo) in months:
        key = f'{y}-{mo:02d}'
        if key in done: continue
        t0 = time.time(); parts = []
        for d in [d for d in ss if d.year == y and d.month == mo]:
            cd = cm.load_0dte(root, d)
            if cd is None: continue
            r = session_rows(cd)
            if r is not None: parts.append(r)
        if parts:
            df = pl.concat(parts)
            tmp = f'{out}/{key}.parquet.tmp'; df.write_parquet(tmp, compression='zstd'); os.replace(tmp, f'{out}/{key}.parquet')
            rec = {'month': key, 'status': 'ok', 'rows': df.height, 'sessions': len(parts), 'bytes': os.path.getsize(f'{out}/{key}.parquet'), 'secs': round(time.time() - t0, 1)}
        else:
            rec = {'month': key, 'status': 'empty'}
        open(jobs, 'a').write(json.dumps(rec) + '\n')
        log(f'{root} {key}: {rec}')
