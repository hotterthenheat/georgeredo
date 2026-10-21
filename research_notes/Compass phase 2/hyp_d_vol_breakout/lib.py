"""Compass Phase 2, Hypothesis D: the top-decile volatility breakout (0DTE straddles / strangles / directional breakouts
bought only when a fitted volatility model's forecast is in its top decile), plus the opening drive as a special case.

Conventions (the audit's, kept exactly):
- minute m = 0 is 09:30 New York; an underlying 1-minute bar stamped t closes at t+1, so c[m] is the close of the bar
  stamped m-1 and is the price known at m; a chain NBBO row stamped m is the quote at m; an SPX / VIX print stamped m is
  the price at m. Half days are dropped. SPXW's spot is SPX's print; its bar features (ranges, volume, opening-drive
  direction) come from SPY's bars (SPX has one print a minute) - a stated proxy, as in the audit.
- every leg is bought at the ask and sold at the bid; $0.65 a leg each way; a leg held to settlement pays no closing
  fee - it expires worthless or settles at intrinsic (ETFs at the 16:00 close, i.e. the 15:59 bar's close; SPXW at the
  last SPX print at or before 16:00, a proxy for the official settlement, stated).
- fit = sessions before 2024-07-01; cut = 2024-07-01 -> 2024-12-31 (decile cuts set here); oos = 2025-01-01 -> 2026-10-09,
  read once.
Feature and pricing code is reused from the audit's sweeplib (read_bars, read_prints, chain_arrays, total_vol,
bs_delta, load_day_table, stress); nothing in that folder is edited. Nothing here calls a vendor.
"""
import datetime as dt, math, os, sys
import numpy as np, polars as pl

AUDIT_SWEEP = '/home/user/georgeredo/research_notes/Compass engine audit/sweep_trigger'
sys.path.insert(0, AUDIT_SWEEP)
import sweeplib as S                       # noqa: E402  (the audit's shared code, read-only)

RAW = S.RAW
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
LOGS = os.path.join(HERE, 'logs'); os.makedirs(LOGS, exist_ok=True)
FEE = 0.65
PRODUCTS = ('SPY', 'QQQ', 'IWM', 'SPXW')
BAR_SOURCE = S.BAR_SOURCE                   # SPXW -> SPY bars
FIT_END = dt.date(2024, 7, 1); CUT_END = dt.date(2025, 1, 1)
SCAN = list(range(5, 356, 5))               # 09:35 .. 15:25 every 5 minutes (71 scan minutes)
LAST_SELL = 388                             # 15:58, the last minute a leg is sold in
CLOSE_M = 390
STRUCTS = ('str', 'sg10', 'sg15', 'sg20', 'dir')      # ATM straddle, 10/15/20-delta strangles, directional nearest OTM
OD_STRUCT = 'oddir'                                   # the opening drive's directional leg (m = 5 only)
EXITS = ('h30', 'h60', 'trail', 'settle', 'ri')       # hold 30, hold 60, 50% trail on the mark, settlement, realized >= implied
OD_EXITS = ('e0955', 'e1030')                         # the opening drive's time exits (m = 5 only)
TRAIL = 0.5
DELTA_TOL = 0.05                                      # a strangle leg must sit within +-0.05 of its target |delta|
FEATURES = ['m', 'ret1', 'ret5', 'ret15', 'ret30', 'aret1', 'aret5', 'aret15', 'aret30', 'rng1', 'rng5', 'rng15', 'rng30',
            'range_pos', 'or_pos', 'day_move_atr', 'day_range_atr', 'rv_session', 'vix', 'vix_chg_open', 'vix_chg30', 'vix_chg_prev',
            'straddle_rel', 'implied30', 'rel_vol']
BASE_FEATURES = ['m', 'straddle_rel']                 # the baseline that knows only time of day and the straddle
TARGETS = ('t1', 't2', 't3')

def period_of(session):
    if session < FIT_END: return 'fit'
    if session < CUT_END: return 'cut'
    return 'oos'

def with_period(df):
    return df.with_columns(pl.when(pl.col('session') < FIT_END).then(pl.lit('fit')).when(pl.col('session') < CUT_END).then(pl.lit('cut')).otherwise(pl.lit('oos')).alias('period'),
                           pl.col('session').dt.year().alias('year'))

# ----------------------------------------------------------------------------------------------- sessions
def sessions_of(root): return S.sessions_of(root)

def vix_sessions():
    return sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(os.path.join(RAW, 'data', 'index', 'VIX')) if f.endswith('.parquet'))

def vix_prev_close(d, vs):
    """the last VIX print of the session before d (None if none on disk)"""
    i = np.searchsorted(vs, d)
    if i == 0: return None
    a = S.read_prints('VIX', vs[i - 1])
    v = a[~np.isnan(a)]
    return float(v[-1]) if len(v) else None

def load_days(root):
    T = S.load_day_table(BAR_SOURCE[root])
    days = {r['session']: r for r in T.select('session', 'prev_close', 'atr14').to_dicts()}
    volmat = np.array(T['volume'].to_list(), dtype=float)
    volidx = {s: i for i, s in enumerate(T['session'].to_list())}
    return days, volmat, volidx

# ----------------------------------------------------------------------------------------------- pricing helpers
def intrinsic(S_close, K, right): return max(S_close - K, 0.0) if right == 0 else max(K - S_close, 0.0)

def atm_strike(strikes, mids, m, Sm):
    """the strike nearest spot among the five nearest with both sides quoted at m; -1 if none (the audit's rule)"""
    if len(strikes) == 0 or np.isnan(Sm): return -1
    j = int(np.argmin(np.abs(strikes - Sm)))
    for jj in sorted(range(max(0, j - 2), min(len(strikes), j + 3)), key=lambda q: abs(strikes[q] - Sm)):
        if not np.isnan(mids[0, jj, m]) and not np.isnan(mids[1, jj, m]): return jj
    return -1

def clean_at(bid, ask, right, m):
    b = bid[right, :, m]; a = ask[right, :, m]
    return (a > 0) & (b > 0) & (b <= a)

def strangle_legs(strikes, bid, ask, m, Sm, d):
    """the OTM call and put whose BSM |delta| (mid implied vol, r = q = 0) is nearest d, each within DELTA_TOL; legs
    among strikes within 3% of spot. Returns [(0, jc), (1, jp)] or None; and the two deltas."""
    legs = []; deltas = []
    for right in (0, 1):
        cl = clean_at(bid, ask, right, m)
        otm = (strikes >= Sm) if right == 0 else (strikes <= Sm)
        near = np.abs(strikes - Sm) <= 0.03 * Sm
        cand = np.where(cl & otm & near)[0]
        if len(cand) == 0: return None, None
        mid = 0.5 * (bid[right, cand, m] + ask[right, cand, m])
        v = S.total_vol(mid, Sm, strikes[cand], right == 1)
        dl = np.abs(S.bs_delta(v, Sm, strikes[cand], right == 1))
        ok = ~np.isnan(dl)
        if not ok.any(): return None, None
        gap = np.where(ok, np.abs(dl - d), np.inf); k = int(np.argmin(gap))
        if gap[k] > DELTA_TOL: return None, None
        legs.append((right, int(cand[k]))); deltas.append(float(dl[k]))
    return legs, deltas

def nearest_otm(strikes, bid, ask, m, Sm, right):
    cl = clean_at(bid, ask, right, m)
    otm = (strikes >= Sm) if right == 0 else (strikes <= Sm)
    cand = np.where(cl & otm)[0]
    if len(cand) == 0: return None
    return int(cand[np.argmin(np.abs(strikes[cand] - Sm))])

# ----------------------------------------------------------------------------------------------- exits
def run_exits(legs, strikes, bid, ask, m, S_close, spot, straddle_rel, time_exits, last=LAST_SELL):
    """legs: list of (right, strike index). Buy every leg at its ask at m (hygiene: ask > 0, bid > 0, bid <= ask on every
    leg, else None). Exits on the path m+1..last:
      time exits (name -> minute, capped at `last`): every leg sold at its bid at that minute;
      'trail': the structure's mark (sum of the legs' mids, the entry minute's mark included) falls to 50% of its running
               peak -> sold at the bids that minute; else settlement;
      'settle': held to settlement - each leg at its intrinsic on S_close, no closing fee;
      'ri': the underlying's |move since entry| first reaches the straddle-implied move for the time elapsed,
            straddle_rel * sqrt((t - m) / (390 - m)) -> sold at the bids; else settlement.
    A leg whose bid at a sale minute is missing takes its last quoted bid since entry; a leg with a zero bid there is held
    to settlement (no closing fee). Returns dict exit -> (exit_m, value, net_usd, ret_pct) and the debit."""
    n = len(legs)
    a0 = np.array([ask[r, j, m] for r, j in legs]); b0 = np.array([bid[r, j, m] for r, j in legs])
    if np.any(np.isnan(a0)) or np.any(a0 <= 0) or np.any(np.isnan(b0)) or np.any(b0 <= 0) or np.any(b0 > a0): return None, np.nan
    debit = float(a0.sum())
    t = np.arange(m + 1, last + 1)
    bidp = np.stack([bid[r, j, m + 1:last + 1] for r, j in legs]); askp = np.stack([ask[r, j, m + 1:last + 1] for r, j in legs])
    midp = 0.5 * (bidp + askp)
    mark = np.where(np.isnan(midp).any(axis=0), np.nan, midp.sum(axis=0))
    m0 = float((0.5 * (a0 + b0)).sum())
    settle_val = float(sum(intrinsic(S_close, strikes[j], r) for r, j in legs))
    settle = (CLOSE_M, settle_val, (settle_val - debit) * 100.0 - n * FEE)
    # last quoted bid at or before each path index, per leg
    lastbid = np.empty_like(bidp)
    for i in range(n):
        row = bidp[i]; idx = np.where(~np.isnan(row), np.arange(len(row)), -1); np.maximum.accumulate(idx, out=idx)
        lastbid[i] = np.where(idx >= 0, row[np.maximum(idx, 0)], np.nan)
    def sell(k):
        val = 0.0; fee = 0.0
        for i, (r, j) in enumerate(legs):
            b = lastbid[i, k]
            if np.isnan(b) or b <= 0: val += intrinsic(S_close, strikes[j], r)      # held to settlement
            else: val += b; fee += FEE
        return (int(t[k]), float(val), (val - debit) * 100.0 - n * FEE - fee)
    out = {}
    for name, tm in time_exits.items():
        k = min(tm, last) - (m + 1)
        out[name] = sell(k) if k >= 0 else settle
    valid = ~np.isnan(mark)
    peak = np.maximum.accumulate(np.where(valid, mark, -np.inf)); peak = np.maximum(peak, m0)
    hit = valid & (mark <= TRAIL * peak) & (peak > 0)
    out['trail'] = sell(int(np.argmax(hit))) if hit.any() else settle
    out['settle'] = settle
    sp = spot[m + 1:last + 1]; realized = np.abs(sp / spot[m] - 1.0)
    thr = straddle_rel * np.sqrt((t - m) / (CLOSE_M - m)) if straddle_rel == straddle_rel else np.full(len(t), np.inf)
    hit2 = ~np.isnan(realized) & (realized >= thr)
    out['ri'] = sell(int(np.argmax(hit2))) if hit2.any() else settle
    return {k: (xm, v, net, net / (debit * 100.0) * 100.0) for k, (xm, v, net) in out.items()}, debit

# ----------------------------------------------------------------------------------------------- the session
def session_rows(root, d, days, volmat, volidx, vix_prev):
    """one row a scan minute: features known at m, the three targets, and every structure's trades"""
    u = BAR_SOURCE[root]
    arr, close_m, half = S.read_bars(u, d)
    if arr is None or half: return None
    o, h, l, c, v = arr['open'], arr['high'], arr['low'], arr['close'], arr['volume']
    if np.isnan(c[1:CLOSE_M + 1]).sum() > 5: return None
    spot = S.read_prints('SPX', d) if root == 'SPXW' else S.ffill(c)
    vix = S.read_prints('VIX', d)
    row = days.get(d)
    if row is None: return None
    S_close = float(spot[CLOSE_M]) if not np.isnan(spot[CLOSE_M]) else float(spot[~np.isnan(spot)][-1])
    strikes, bid, ask = S.chain_arrays(root, d, CLOSE_M)
    if len(strikes) == 0: return None
    bid = np.round(bid, 4); ask = np.round(ask, 4)
    mids = 0.5 * (bid + ask)
    i = volidx.get(d); vol_ref = volmat[max(0, i - 20):i] if i is not None and i >= 10 else None
    orh, orl = (np.nanmax(h[1:31]), np.nanmin(l[1:31]))
    runhi = np.fmax.accumulate(np.nan_to_num(h, nan=-np.inf)); runlo = np.fmin.accumulate(np.nan_to_num(l, nan=np.inf))
    lr = np.diff(np.log(c[1:CLOSE_M + 1])); lr = np.concatenate([[np.nan, np.nan], lr])   # lr[m] = log return of bar closing at m (m >= 2)
    vix_first = vix[1] if not np.isnan(vix[1]) else vix[0]
    atr = row['atr14'] if row['atr14'] and row['atr14'] > 0 else np.nan
    rows = []
    for m in SCAN:
        Sm = float(spot[m])
        if np.isnan(Sm): continue
        rec = dict(product=root, session=d, m=m, spot=Sm, settle_spot=S_close)
        for k, name in ((1, '1'), (5, '5'), (15, '15'), (30, '30')):
            p = spot[m - k] if m - k >= 1 else np.nan
            r = (Sm / p - 1.0) * 1e4 if p == p and p > 0 else np.nan
            rec['ret' + name] = r; rec['aret' + name] = abs(r) if r == r else np.nan
            lo = max(1, m - k + 1)
            rec['rng' + name] = (np.nanmax(h[lo:m + 1]) - np.nanmin(l[lo:m + 1])) / c[m] * 1e4
        rec['range_pos'] = (c[m] - runlo[m]) / (runhi[m] - runlo[m]) if runhi[m] > runlo[m] else np.nan
        rec['or_pos'] = (c[m] - orl) / (orh - orl) if (m > 30 and orh > orl) else np.nan
        rec['day_move_atr'] = (c[m] - row['prev_close']) / atr
        rec['day_range_atr'] = (runhi[m] - runlo[m]) / atr
        rec['rv_session'] = float(np.sqrt(np.nanmean(lr[2:m + 1] ** 2)) * 1e4) if m >= 3 else np.nan
        rec['vix'] = vix[m]; rec['vix_chg_open'] = vix[m] - vix_first; rec['vix_chg30'] = vix[m] - vix[max(m - 30, 1)]
        rec['vix_chg_prev'] = vix[m] - vix_prev if vix_prev is not None else np.nan
        if vol_ref is not None:
            cur = np.nansum(v[m - 4:m + 1]); ref = np.nanmedian(vol_ref[:, m - 4:m + 1].sum(axis=1))
            rec['rel_vol'] = cur / ref if ref > 0 else np.nan
        else: rec['rel_vol'] = np.nan
        j = atm_strike(strikes, mids, m, Sm)
        st = mids[0, j, m] + mids[1, j, m] if j >= 0 else np.nan
        rec['atm_K'] = strikes[j] if j >= 0 else np.nan
        rec['straddle'] = st; rec['straddle_rel'] = st / Sm if st == st else np.nan
        rec['implied30'] = rec['straddle_rel'] * math.sqrt(30.0 / (CLOSE_M - m)) if st == st else np.nan
        # targets (read forward; never used as a feature)
        mv30 = abs(spot[m + 30] / Sm - 1.0) if m + 30 <= CLOSE_M and not np.isnan(spot[m + 30]) else np.nan
        mvc = abs(S_close / Sm - 1.0)
        rec['mv30_bps'] = mv30 * 1e4 if mv30 == mv30 else np.nan; rec['mvclose_bps'] = mvc * 1e4
        rec['t1'] = int(mv30 >= 10e-4) if mv30 == mv30 else None
        rec['t2'] = int(mv30 > rec['implied30']) if (mv30 == mv30 and rec['implied30'] == rec['implied30']) else None
        rec['t3'] = int(mvc > rec['straddle_rel']) if rec['straddle_rel'] == rec['straddle_rel'] else None
        # trades
        time_exits = {'h30': m + 30, 'h60': m + 60}
        if m == 5: time_exits.update({'e0955': 25, 'e1030': 60})
        structs = {}
        if j >= 0: structs['str'] = [(0, j), (1, j)]
        for d_, nm in ((0.10, 'sg10'), (0.15, 'sg15'), (0.20, 'sg20')):
            legs, dls = strangle_legs(strikes, bid, ask, m, Sm, d_)
            if legs is not None: structs[nm] = legs; rec[nm + '_dc'] = dls[0]; rec[nm + '_dp'] = dls[1]
        r5 = rec['ret5']
        if r5 == r5 and r5 != 0:
            right = 0 if r5 > 0 else 1; jj = nearest_otm(strikes, bid, ask, m, Sm, right)
            if jj is not None: structs['dir'] = [(right, jj)]; rec['dir_right'] = right
        if m == 5:
            mv = c[5] - o[1]
            if mv == mv and mv != 0:
                right = 0 if mv > 0 else 1; jj = nearest_otm(strikes, bid, ask, m, Sm, right)
                if jj is not None: structs[OD_STRUCT] = [(right, jj)]; rec['oddir_right'] = right
        for nm, legs in structs.items():
            res, debit = run_exits(legs, strikes, bid, ask, m, S_close, spot, rec['straddle_rel'], time_exits)
            if res is None: continue
            rec[nm + '_debit'] = debit; rec[nm + '_K'] = ','.join(f'{strikes[q]:g}' for _, q in legs)
            for ex, (xm, val, net, ret) in res.items():
                rec[f'{nm}_{ex}_m'] = xm; rec[f'{nm}_{ex}_net'] = net; rec[f'{nm}_{ex}_ret'] = ret
        rows.append(rec)
    return rows

# ----------------------------------------------------------------------------------------------- reporting
def cell_stats(net, ret, sessions, reps=1000, seed=7):
    """the brief's per-cell report: N, mean $, mean % of debit, win rate, average win / loss, p5 / p1 / worst, the best 5
    sessions' share of the total, profit factor, session-bootstrap 95% CI of the mean $, mean $ without the best 5 sessions"""
    net = np.asarray(net, float); ret = np.asarray(ret, float); sessions = np.asarray(sessions)
    ok = ~np.isnan(net); net = net[ok]; ret = ret[ok]; sessions = sessions[ok]
    if len(net) == 0: return dict(n=0)
    ud, inv = np.unique(sessions, return_inverse=True)
    sums = np.bincount(inv, weights=net, minlength=ud.size); cnt = np.bincount(inv, minlength=ud.size)
    rng = np.random.default_rng(seed); means = np.empty(reps)
    for k in range(reps):
        pick = rng.integers(0, ud.size, ud.size); means[k] = sums[pick].sum() / max(cnt[pick].sum(), 1)
    order = np.argsort(-sums); keep = np.ones(ud.size, bool); keep[order[:5]] = False
    wins = net[net > 0]; losses = net[net < 0]
    tot = sums.sum()
    return dict(n=int(len(net)), sessions=int(ud.size), mean_usd=float(net.mean()), mean_pct=float(ret.mean()), win=float((net > 0).mean()),
                avg_win=float(wins.mean()) if len(wins) else np.nan, avg_loss=float(losses.mean()) if len(losses) else np.nan,
                p5=float(np.percentile(net, 5)), p1=float(np.percentile(net, 1)), worst=float(net.min()),
                best5_share=float(sums[order[:5]].sum() / tot) if tot > 0 else np.nan,
                profit_factor=float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else np.nan,
                ci_lo=float(np.percentile(means, 2.5)), ci_hi=float(np.percentile(means, 97.5)),
                wo_best5=float(sums[keep].sum() / max(cnt[keep].sum(), 1)), sessions_up=int((sums > 0).sum()), total_usd=float(tot))
