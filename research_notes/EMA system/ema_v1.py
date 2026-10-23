"""
ema_v1.py — the engine of RULEBOOK_v1.md: RULEBOOK_v0's engine (ema_system.py, imported unchanged) with the four v1
changes — the 14:00 flat for every exit and no entries from 13:30 (X3), the 3% spread veto (BV1b), the S&P as one stream
on SPY's bars priced in the cheaper of SPY / SPXW (VN1) — and the V-chop gate. Files only; deterministic; seeded.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

import ema_system as E

S = E.S
NBAR = E.NBAR
FIRST_M = 15            # 09:45
LAST_M = 239            # 13:29 — no entries at or after 13:30 (§1.1; the rulebook printed "m = 15..299", an arithmetic slip: 13:30 is m = 240)
FLAT_M = 270            # 14:00 (§1.1)
CAP = 0.03              # §1.2
CHOP_M = 60             # 10:30 (§3)
STREAMS = ('SP', 'QQQ', 'IWM')          # the S&P stream reads SPY's bars
BARS_OF = {'SP': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM'}
LABEL = {'SP': 'S&P', 'QQQ': 'QQQ', 'IWM': 'IWM'}


# ---- the contract (§1.2, §1.4): v0's picker with the 3% cap ---------------------------------------------------------------------

@lru_cache(maxsize=None)
def pick(name: str, d: str, m: int, side: int, spot: float, cap: float = CAP):
    ch = S.chain(name, d)
    if ch is None:
        return None, 'no chain file'
    K, bid, ask = ch
    r = 0 if side > 0 else 1
    b, a = bid[m, :, r], ask[m, :, r]
    oi = S.oi_day(name, d)
    if oi is None:
        return None, 'no open interest file'
    vol = S.prev_volume(name, d)
    if vol is None:
        return None, 'no previous-session volume file'
    q = np.isfinite(a) & np.isfinite(b) & (a > b) & (b > 0)
    mid = np.where(q, (a + b) / 2.0, np.nan)
    spr = np.where(q, (a - b) / np.where(q, mid, 1.0), np.inf)
    T = (NBAR - m) / 525600.0
    dl = S.bs_delta(mid, spot, K, T, np.full(K.shape, side > 0))
    root = 'SPXW' if name == 'SPXW' else name
    o = np.array([oi.get(S.occ(root, d, r, k), 0) for k in K], float)
    v = np.array([vol.get((float(k), r), 0) for k in K], float)
    f1 = q
    f2 = f1 & (spr <= cap + 1e-12)
    f3 = f2 & np.isfinite(dl) & (dl >= 0.30 - 1e-12) & (dl <= 0.60 + 1e-12)
    f4 = f3 & (o >= 250)
    f5 = f4 & (v >= 100)
    for f, why in ((f1, 'no standing quote'), (f2, f'spread > {100 * cap:.0f}%'), (f3, 'no delta 0.30-0.60'),
                   (f4, 'OI < 250'), (f5, 'prev volume < 100')):
        if not f.any():
            return None, why
    cand = np.where(f5)[0]
    i = min(cand, key=lambda k: (round(abs(dl[k] - 0.45), 12), spr[k], K[k]))
    return dict(K=float(K[i]), i=int(i), r=r, ask=float(a[i]), bid=float(b[i]), spread=float(spr[i]), delta=float(dl[i]),
                oi=int(o[i]), pvol=int(v[i])), 'ok'


@lru_cache(maxsize=64)
def spx_close(d: str):
    b = E.index_bars(d)
    return None if b is None else b[3]


def cost_share(venue: str, c: dict) -> float:
    mid = (c['ask'] + c['bid']) / 2.0
    return ((c['ask'] - mid) + E.fee(venue, c['ask']) / 100.0) / mid


def choose(stream: str, d: str, m: int, side: int, spot: float):
    """→ (venue, contract, info) or (None, None, reason); the S&P stream takes the lower cost share, ties SPY (§1.3)"""
    if stream != 'SP':
        c, why = pick(stream, d, m, side, spot)
        return (stream, c, {}) if c is not None else (None, None, why)
    cs, ws = pick('SPY', d, m, side, spot)
    sx = spx_close(d)
    if sx is None or not np.isfinite(sx[m - 1]):
        cx, wx = None, 'no SPX print'
    else:
        cx, wx = pick('SPXW', d, m, side, float(sx[m - 1]))
    info = dict(cs_spy=cost_share('SPY', cs) if cs else np.nan, cs_spxw=cost_share('SPXW', cx) if cx else np.nan,
                spx=float(sx[m - 1]) if (sx is not None and np.isfinite(sx[m - 1])) else np.nan)
    if cs is None and cx is None:
        return None, None, f'SPY: {ws} / SPXW: {wx}'
    if cx is None:
        return 'SPY', cs, info
    if cs is None:
        return 'SPXW', cx, info
    if info['cs_spxw'] < info['cs_spy'] - 1e-12:
        return 'SPXW', cx, info
    return 'SPY', cs, info


# ---- one trade (§1.1, §1.3; v0 §5 otherwise) ----------------------------------------------------------------------------------

def simulate(X: E.Series, stream: str, d: str, m: int, side: int, exit_v: str, flat: int = FLAT_M):
    assert m < flat, (m, flat)                    # an entry is always before the 14:00 flat
    i = X.di(d)
    s = m - 1
    W = range(s - 4, s + 1)
    entry_u = float(X.C[i, s])
    level = float(min(X.L[i, t] for t in W)) if side > 0 else float(max(X.H[i, t] for t in W))
    R = abs(entry_u - level)
    if not R > 0:
        return None, 'zero R'
    venue, c, info = choose(stream, d, m, side, entry_u)
    if c is None:
        return None, info
    K, bid, ask = S.chain(venue, d)
    qty = 10 if exit_v == 'X4' else 1
    lots = {'t1': 2, 't2': 3, 'run': 5} if exit_v == 'X4' else None
    legs = []
    open_q = qty
    hit1 = hit2 = False
    e = None
    for t in range(s + 1, flat):                   # bar t completes at minute t + 1 <= flat
        ct = X.C[i, t]
        if not np.isfinite(ct):
            continue
        mv = (ct - entry_u) * side
        ex = t + 1
        if (side > 0 and ct < level) or (side < 0 and ct > level):
            legs.append((open_q, ex, 'stop'))
            open_q = 0
        else:
            x3 = False
            if t % 5 == 4:
                j = t // 5
                c5, e9 = X.c5[i, j], X.ema5[9][i, j]
                x3 = (c5 < e9) if side > 0 else (c5 > e9)
            if exit_v == 'X1' and mv >= R - 1e-12:
                legs.append((open_q, ex, '+1R')); open_q = 0
            elif exit_v == 'X2' and mv >= 2 * R - 1e-12:
                legs.append((open_q, ex, '+2R')); open_q = 0
            elif exit_v == 'X3' and x3:
                legs.append((open_q, ex, 'runner')); open_q = 0
            elif exit_v == 'X4':
                if not hit1 and mv >= R - 1e-12:
                    legs.append((lots['t1'], ex, '+1R')); open_q -= lots['t1']; hit1 = True
                if not hit2 and mv >= 2 * R - 1e-12:
                    legs.append((lots['t2'], ex, '+2R')); open_q -= lots['t2']; hit2 = True
                if x3 and open_q > 0:
                    legs.append((open_q, ex, 'runner')); open_q = 0
        if open_q == 0:
            e = ex
            break
    if open_q > 0:
        legs.append((open_q, flat, '14:00'))
        e = flat
    ii, r = c['i'], c['r']
    out_legs = [(q, ex, S.exit_quote(bid, ex, ii, r), why) for q, ex, why in legs]
    gross = sum(q * (px - c['ask']) * 100 for q, ex, px, why in out_legs)
    fees = qty * E.fee(venue, c['ask']) + sum(q * E.fee(venue, px) for q, ex, px, why in out_legs)
    path = [S.exit_quote(bid, mm, ii, r) for mm in range(m + 1, e + 1)]
    ex_u = sum(q * X.C[i, ex - 1] for q, ex, px, why in out_legs) / qty
    reason = 'stop' if any(w == 'stop' for *_, w in out_legs) else out_legs[-1][3]
    # half-spreads paid (CALCULATED): (ask − mid) at entry, (mid − bid) on each exit row (missing quote → 0)
    hs = qty * (c['ask'] - c['bid']) / 2 * 100
    for q, ex, px, _ in out_legs:
        a_, b_ = ask[ex, ii, r], bid[ex, ii, r]
        if np.isfinite(a_) and np.isfinite(b_) and a_ > b_:
            hs += q * (a_ - b_) / 2 * 100
    return dict(stream=LABEL[stream], venue=venue, day=d, exit=exit_v, m=m, entry=S.mtxt(m), side=side, K=c['K'],
                right='C' if side > 0 else 'P', ask=c['ask'], bid_in=c['bid'], spread=c['spread'], delta=c['delta'],
                oi=c['oi'], pvol=c['pvol'], cs_spy=info.get('cs_spy', np.nan), cs_spxw=info.get('cs_spxw', np.nan),
                spx=info.get('spx', np.nan), qty=qty, level=level, R=R, entry_u=entry_u, exit_u=float(ex_u), exit_m=e,
                hold=e - m, reason=reason, legs=out_legs, gross=gross, fees=fees, net=gross - fees, halfspread=hs,
                cost=qty * c['ask'] * 100, mfe=(max(path) / c['ask'] - 1) if path else 0.0,
                mae=(min(path) / c['ask'] - 1) if path else 0.0), 'ok'


# ---- V-chop (§3) --------------------------------------------------------------------------------------------------------------

def fhr(X: E.Series, i: int):
    o = X.O[i, 0]
    h, l_ = X.H[i, :60], X.L[i, :60]
    if not np.isfinite(o) or not np.isfinite(h).any():
        return np.nan, np.nan, np.nan
    hi, lo = float(np.nanmax(h)), float(np.nanmin(l_))
    return (hi - lo) / o, hi, lo


def chop_day(X: E.Series, i: int) -> bool:
    r, hi, lo = fhr(X, i)
    if not np.isfinite(r):
        return False
    ref = [fhr(X, j)[0] for j in range(max(0, i - 60), i)]
    ref = [v for v in ref if np.isfinite(v)]
    if len(ref) < 40:
        return False
    p33 = float(np.percentile(ref, 33))
    p = X.C[i, 59]
    if not np.isfinite(p):
        return False
    return bool(r < p33 and lo + 0.25 * (hi - lo) <= p <= lo + 0.75 * (hi - lo))


def chop_gate(X: E.Series, i: int, m: int) -> bool:
    """True = entry at m blocked by V-chop (uses bars <= 10:29 of day i and earlier sessions only)"""
    return m >= CHOP_M and chop_day(X, i)


# ---- a session under the risk rules (v0 §6, v1 §1.1) ------------------------------------------------------------------------

def run_day(X: E.Series, stream: str, d: str, cfg: str, exit_v: str, sig: str = 'full', chop: bool = False):
    fn = E.SIGNALS[sig]
    i = X.di(d)
    trades, skips = [], {}
    nxt, n = FIRST_M, 0
    for m in range(FIRST_M, LAST_M + 1):
        if m < nxt or n >= 5:
            continue
        if chop and chop_gate(X, i, m):
            break
        side = fn(X, i, m, cfg)
        if not side:
            continue
        tr, why = simulate(X, stream, d, m, side, exit_v)
        if tr is None:
            skips[why] = skips.get(why, 0) + 1
            continue
        tr['cfg'] = cfg
        trades.append(tr)
        n += 1
        nxt = tr['exit_m'] + (5 if tr['reason'] == 'stop' else 1)
    return trades, skips


_SER = {}


def series(stream_or_name: str, week: tuple) -> E.Series:
    """bars of a stream (S&P → SPY) or a v0 name (SPXW → SPX prints), with the 60-day warm-up before the week"""
    nm = BARS_OF.get(stream_or_name, stream_or_name)
    k = (nm, week)
    if k not in _SER:
        _SER[k] = E.Series(nm, days=list(week))
    return _SER[k]


def run_week(week: tuple, cfg: str, exit_v: str, sig: str = 'full', chop: bool = False):
    T, K = [], {}
    for st in STREAMS:
        X = series(st, week)
        for d in week:
            t, k = run_day(X, st, d, cfg, exit_v, sig, chop)
            T += t
            for a, b in k.items():
                K[(LABEL[st], a)] = K.get((LABEL[st], a), 0) + b
    return T, K


def run_v0_week(week: tuple, cfg: str, exit_v: str):
    """RULEBOOK_v0 as written (ema_system's own run_day, simulate and pick, unchanged) on one week"""
    T = []
    for nm in E.NAMES:
        X = series(nm, week)
        for d in week:
            t, _ = E.run_day(X, d, cfg, exit_v, 'full')
            T += t
    return T


# ---- the random baseline (§5) -------------------------------------------------------------------------------------------------

_RT = {}


def random_trade(week: tuple, stream: str, d: str, m: int, side: int, exit_v: str):
    k = (stream, d, m, side, exit_v)
    if k not in _RT:
        tr, _ = simulate(series(stream, week), stream, d, m, side, exit_v)
        _RT[k] = None if tr is None else (tr['net'], tr['cost'])
    return _RT[k]


def random_baseline(weeks: list[tuple], heads: list[list[dict]], exit_v: str, trials: int = 500, seed: int = 2026102312):
    """heads[w] = the headline trades of week w for this config × exit. → per week and pooled: totals, per-trade means"""
    rng = np.random.default_rng(seed)
    spec = []
    for wk, H in zip(weeks, heads):
        mins = np.array([t['m'] for t in H])
        putp = float(np.mean([t['side'] < 0 for t in H])) if H else 0.0
        cnt = {st: sum(1 for t in H if t['stream'] == LABEL[st]) for st in STREAMS}
        spec.append((wk, mins, putp, cnt))
    tot = np.zeros((trials, len(weeks)))
    nn = np.zeros((trials, len(weeks)))
    fails = 0
    for tr in range(trials):
        for w, (wk, mins, putp, cnt) in enumerate(spec):
            for st in STREAMS:
                for _k in range(cnt[st]):
                    for _try in range(50):
                        d = wk[int(rng.integers(len(wk)))]
                        m = int(mins[int(rng.integers(mins.size))])
                        sd = -1 if rng.random() < putp else 1
                        r = random_trade(wk, st, d, m, sd, exit_v)
                        if r is not None:
                            tot[tr, w] += r[0]
                            nn[tr, w] += 1
                            break
                    else:
                        fails += 1
    return dict(tot=tot, n=nn, fails=fails)
