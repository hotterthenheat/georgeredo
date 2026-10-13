"""Vectorised re-implementation of backtest/exits.py (ladder/trail logic) + costs.py so a 576-configuration grid runs in minutes.
Semantics are copied from exits.simulate: stop/breakeven/guardian trail checked on bar low BEFORE updating the high-water mark,
T1 (half) and T2 (rest) on bar high, time stop on bar close when flat/losing, forced CLOSE at the first bar >= 15:55 (or last bar).
`verify()` checks leg-for-leg agreement with exits.simulate + costs.settle on random configs."""
import itertools, random, datetime
import numpy as np
from common import *
R_NONE, R_STOP, R_BE, R_TRAIL, R_T1, R_T2, R_TS, R_CLOSE = range(8)
RNAME = ['', 'STOP', 'BREAKEVEN', 'TRAIL', 'T1', 'T2', 'TIME_STOP', 'CLOSE']
CLOSE_MIN = 15 * 60 + 55

def build(trades, bar_cache):
    """trades: dicts with ticker, contract, date, entry_t (iso), entry_px. Returns padded matrices + per-trade vectors."""
    seqs = []; keep = []
    for k, tr in enumerate(trades):
        bars = bar_cache[(tr['contract'], tr['date'])]
        eidx = next((i for i, b in enumerate(bars) if b['t'].isoformat() == tr['entry_t']), None)
        if eidx is None: continue
        e_t = bars[eidx]['t']; seq = bars[eidx + 1:]
        checked = []; close_bar = None
        for b in seq:
            if hhmm(b['t']) >= CLOSE_MIN: close_bar = b; break
            checked.append(b)
        if close_bar is None: close_bar = checked[-1] if checked else None
        if close_bar is None: continue
        seqs.append((eidx, e_t, checked, close_bar, bars[eidx])); keep.append(k)
    N = len(seqs); L = max(len(s[2]) for s in seqs)
    RH = np.full((N, L), np.nan); RL = np.full((N, L), np.nan); RC = np.full((N, L), np.nan); HELD = np.full((N, L), np.nan); TMIN = np.full((N, L), np.nan)
    VALID = np.zeros((N, L), bool)
    entry_px = np.array([float(trades[k]['entry_px']) for k in keep]); entry_hi = np.array([s[4]['h'] for s in seqs])
    close_px = np.array([s[3]['c'] for s in seqs]); close_min = np.array([hhmm(s[3]['t']) for s in seqs], float)
    for n, (eidx, e_t, checked, cb, eb) in enumerate(seqs):
        m = len(checked)
        if m:
            h = np.array([b['h'] for b in checked]); l = np.array([b['l'] for b in checked]); c = np.array([b['c'] for b in checked])
            RH[n, :m] = h / entry_px[n] - 1; RL[n, :m] = l / entry_px[n] - 1; RC[n, :m] = c / entry_px[n] - 1
            HELD[n, :m] = [(b['t'] - e_t).total_seconds() / 60 for b in checked]; TMIN[n, :m] = [hhmm(b['t']) for b in checked]
            VALID[n, :m] = True
    hs = np.array([costs.HALF_SPREAD.get(trades[k]['ticker'], 0.05) for k in keep])
    return dict(RH=RH, RL=RL, RC=RC, HELD=HELD, TMIN=TMIN, VALID=VALID, entry_px=entry_px, entry_hi=entry_hi, close_px=close_px, close_min=close_min, hs=hs, keep=np.array(keep), N=N, L=L)

def run(M, stop, be_arm, guard_arm, guard_gb, partial, time_stop, t1=0.25, t2=0.45):
    """Returns dict with per-trade proceeds ratio, $ proceeds with $0.01-floor half-spread, first/last reason, exit minute-of-day."""
    N, L = M['N'], M['L']; RH, RL, RC, HELD, VALID = M['RH'], M['RL'], M['RC'], M['HELD'], M['VALID']
    ep = M['entry_px']; hs = M['hs']
    remaining = np.ones(N); hwm = np.zeros(N); half = np.zeros(N, bool); be = np.zeros(N, bool); done = np.zeros(N, bool)
    proceeds = np.zeros(N); proceeds_floor = np.zeros(N)  # ratio to entry; $ with floor half-spread
    first = np.zeros(N, int); last = np.zeros(N, int); exit_min = np.full(N, np.nan)
    def fill(mask, frac, ratio, reason, j):
        px = ratio * ep[mask]
        proceeds[mask] += frac[mask] * ratio if np.ndim(ratio) else frac[mask] * ratio
        proceeds_floor[mask] += frac[mask] * (px - np.maximum(hs[mask] * px, 0.01))
        last[mask] = reason; exit_min[mask] = M['TMIN'][mask, j]
    be_arm = np.inf if be_arm is None else be_arm
    for j in range(L):
        act = ~done & VALID[:, j]
        if not act.any(): break
        rh = RH[:, j]; rl = RL[:, j]; rc = RC[:, j]
        stop_lvl = np.full(N, stop)
        stop_lvl = np.where(be, np.maximum(stop_lvl, 0.0), stop_lvl)
        g = hwm >= guard_arm
        stop_lvl = np.where(g, np.maximum(stop_lvl, hwm * (1 - guard_gb)), stop_lvl)
        hit = act & (rl <= stop_lvl)
        if hit.any():
            reason = np.where(stop_lvl == stop, R_STOP, np.where(stop_lvl == 0.0, R_BE, R_TRAIL))
            px_ratio = 1 + stop_lvl
            proceeds[hit] += remaining[hit] * px_ratio[hit]
            pxh = px_ratio[hit] * ep[hit]; proceeds_floor[hit] += remaining[hit] * (pxh - np.maximum(hs[hit] * pxh, 0.01))
            last[hit] = reason[hit]; exit_min[hit] = M['TMIN'][hit, j]; done[hit] = True
        act2 = act & ~done
        if partial:
            t1hit = act2 & ~half & (rh >= t1)
            if t1hit.any():
                px1 = (1 + t1) * ep[t1hit]
                proceeds[t1hit] += 0.5 * remaining[t1hit] * (1 + t1); proceeds_floor[t1hit] += 0.5 * remaining[t1hit] * (px1 - np.maximum(hs[t1hit] * px1, 0.01))
                remaining[t1hit] *= 0.5; half[t1hit] = True; first[t1hit] = R_T1
            t2hit = act2 & half & (rh >= t2)
            if t2hit.any():
                px2 = (1 + t2) * ep[t2hit]
                proceeds[t2hit] += remaining[t2hit] * (1 + t2); proceeds_floor[t2hit] += remaining[t2hit] * (px2 - np.maximum(hs[t2hit] * px2, 0.01))
                last[t2hit] = R_T2; exit_min[t2hit] = M['TMIN'][t2hit, j]; done[t2hit] = True
            act2 = act & ~done
        hwm = np.where(act2, np.maximum(hwm, rh), hwm)
        be |= act2 & (hwm >= be_arm)
        if time_stop:
            ts = act2 & (HELD[:, j] >= time_stop) & (rc <= 0)
            if ts.any():
                pxt = (1 + rc[ts]) * ep[ts]
                proceeds[ts] += remaining[ts] * (1 + rc[ts]); proceeds_floor[ts] += remaining[ts] * (pxt - np.maximum(hs[ts] * pxt, 0.01))
                last[ts] = R_TS; exit_min[ts] = M['TMIN'][ts, j]; done[ts] = True
    nd = ~done
    cp = M['close_px'][nd]
    proceeds[nd] += remaining[nd] * cp / ep[nd]; proceeds_floor[nd] += remaining[nd] * (cp - np.maximum(hs[nd] * cp, 0.01))
    last[nd] = R_CLOSE; exit_min[nd] = M['close_min'][nd]
    return dict(proceeds=proceeds, proceeds_floor=proceeds_floor, first=first, last=last, exit_min=exit_min)

def settle(M, R):
    """$ per contract and return on premium for mid / spread / adverse (as costs.settle) and spread_floor (half-spread >= $0.01 per side)."""
    ep, hs, hi = M['entry_px'], M['hs'], M['entry_hi']; pr = R['proceeds']
    out = {}
    buy = ep; sell = pr * ep; out['usd_mid'] = (sell - buy) * 100; out['ret_mid'] = (sell - buy) / buy
    buy = np.maximum(ep * (1 + hs), 0.01); sell = pr * ep * (1 - hs); out['usd_spread'] = (sell - buy) * 100 - 2 * costs.FEES; out['ret_spread'] = (sell - buy) / buy
    buy = np.maximum(hi, 0.01); sell = pr * ep * (1 - 2 * hs); out['usd_adverse'] = (sell - buy) * 100 - 2 * costs.FEES; out['ret_adverse'] = (sell - buy) / buy
    buy = ep + np.maximum(hs * ep, 0.01); sell = R['proceeds_floor']; out['usd_spread_floor'] = (sell - buy) * 100 - 2 * costs.FEES; out['ret_spread_floor'] = (sell - buy) / buy
    return out

def reasons_str(R):
    return ['+'.join(x for x in (RNAME[a], RNAME[b]) if x) for a, b in zip(R['first'], R['last'])]

GRID = [dict(stop=s, be_arm=b, guard_arm=ga, guard_gb=gb, partial=p, time_stop=t)
        for s, b, (ga, gb), p, t in itertools.product((-0.15, -0.25, -0.40, -0.60), (None, 0.06, 0.15, 0.30),
                                                       [(ga, gb) for ga in (0.15, 0.30) for gb in (0.25, 0.35, 0.50)], (True, False), (0, 30, 60))]

def cfg_name(c):
    return f"stop{int(c['stop']*100)}|be{'none' if c['be_arm'] is None else int(c['be_arm']*100)}|guard{int(c['guard_gb']*100)}@{int(c['guard_arm']*100)}|partial{'on' if c['partial'] else 'off'}|ts{c['time_stop'] or 'none'}"

def verify(trades, bar_cache, n_cfg=25, n_tr=250, seed=1):
    rng = random.Random(seed); M = build(trades, bar_cache); bad = 0; tested = 0
    for c in rng.sample(GRID, n_cfg):
        R = run(M, **c); S = settle(M, R); rs = reasons_str(R)
        for n in rng.sample(range(M['N']), n_tr):
            tr = trades[M['keep'][n]]; bars = bar_cache[(tr['contract'], tr['date'])]
            eidx = next(i for i, b in enumerate(bars) if b['t'].isoformat() == tr['entry_t'])
            p = dict(stop=c['stop'], be_arm=(99.0 if c['be_arm'] is None else c['be_arm']), guard_arm=c['guard_arm'], guard_giveback=c['guard_gb'], time_stop_min=c['time_stop'])
            legs = exits.simulate(bars, eidx, float(tr['entry_px']), 'ladder' if c['partial'] else 'trail', p)
            ref = {m: costs.settle(tr['ticker'], bars[eidx], float(tr['entry_px']), legs, m)['dollars'] for m in ('mid', 'spread', 'adverse')}
            rr = '+'.join(l[3] for l in legs); tested += 1
            if any(abs(ref[m] - S['usd_' + m][n]) > 1e-6 for m in ref) or rr != rs[n]:
                bad += 1
                if bad <= 5: print('MISMATCH', cfg_name(c), tr['contract'], tr['entry_t'], ref, {m: S['usd_' + m][n] for m in ref}, rr, rs[n])
    print(f'verify: {tested} trade-configs, {bad} mismatches')
    return bad == 0
