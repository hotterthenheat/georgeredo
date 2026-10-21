"""Shared code for the Compass sweep-trigger audit (modules 2 and 9).

Conventions (steps 1-5 of this repository): minute m = 0 is 09:30; an ETF one-minute bar stamped t closes at t+1, so
"bar m" is the bar that closes at minute m (stamped m-1) and its close is the price at m; an option quote stamped m is
the NBBO at minute m; an SPX or VIX print stamped m is the price at m. A half day (SPY's bars stop at 13:00) is dropped.
Fees: $0.65 a contract each way; none when a contract expires worthless (sold at the close with a zero bid).

Nothing after the entry minute is read for a feature or a trigger; only the exits read forward.
"""
import datetime as dt, math, os
import numpy as np, polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
UNDERLYING = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
# SPXW's events and levels are detected on SPY's one-minute bars (SPX has one print a minute, no bar high/low); its
# spot, strikes and deltas are SPX's own prints. Stated as a proxy in the notes.
BAR_SOURCE = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPY'}
FEE = 0.65
ENTRY_LO, ENTRY_HI, LAST_SELL = 5, 388, 388           # 09:35 .. 15:58, sell at 15:58
X_GRID = (0, 2, 5, 10, 20)                            # bps beyond the level
K_GRID = ('1', '3', '5', '5m')                         # bars allowed for the close back inside
LEVELS = ('OR', 'PD', 'PW', 'SH')
COOLDOWN = 30                                         # minutes between episodes of one (level, side, X)
SH_AGE = 10                                           # a session high/low must have stood this many bars to hold liquidity
GEOM_WAIT = 30                                        # bars allowed for an OTE / order-block retrace to fill
TRAIL = 0.5; TGT = 1.25; STOP = 0.68                  # exits: 50% trailing stop; +25% target / -32% stop

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

# ----------------------------------------------------------------------------------------------- underlying
def read_bars(u, d):
    """o,h,l,c,v arrays indexed by the minute the bar CLOSES (1..390); index 0 is NaN. close_m, half_day."""
    p = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet'))
    p = p.with_columns((minute_of('timestamp') + 1).alias('m')).filter(pl.col('close').is_not_null() & (pl.col('m') >= 1) & (pl.col('m') <= 390))
    if p.height < 30: return None, None, None
    half = p['timestamp'].max().hour < 15
    close_m = 210 if half else 390
    arr = {}
    for k in ('open', 'high', 'low', 'close', 'volume'):
        a = np.full(391, np.nan); a[p['m'].to_numpy()] = p[k].to_numpy().astype(float); arr[k] = a
    return arr, close_m, half

def read_prints(name, d):
    """SPX or VIX: price at minute m (stamped m), carried forward; index 0..390"""
    p = pl.read_parquet(os.path.join(RAW, 'data', 'index', name, f'{d}.parquet')).with_columns(minute_of('timestamp').alias('m'))
    p = p.filter(pl.col('price').is_not_null() & (pl.col('m') >= 0) & (pl.col('m') <= 390))
    a = np.full(391, np.nan); a[p['m'].to_numpy()] = p['price'].to_numpy()
    return ffill(a)

def ffill(a):
    a = a.copy(); idx = np.where(~np.isnan(a), np.arange(len(a)), 0); np.maximum.accumulate(idx, out=idx); return a[idx]

def sessions_of(root):
    return sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))

# ----------------------------------------------------------------------------------------------- the day table
def day_table_path(u): return os.path.join(OUT, f'days_{u}.parquet')

def build_day_table(u):
    """one row a session from the one-minute bars (2012 on): open, high, low, close, close_m, the volume by minute"""
    days = sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data', 'underlying', u)) if f.endswith('.parquet'))
    rows = []
    for d in days:
        arr, close_m, half = read_bars(u, d)
        if arr is None: continue
        sl = slice(1, close_m + 1)
        h, l, c, o, v = arr['high'][sl], arr['low'][sl], arr['close'][sl], arr['open'][sl], arr['volume'][sl]
        if np.all(np.isnan(c)): continue
        vol = np.nan_to_num(arr['volume'][:391], nan=0.0)
        rows.append(dict(session=dt.date.fromisoformat(d), close_m=close_m, half=half, open=float(o[~np.isnan(o)][0]),
                         high=float(np.nanmax(h)), low=float(np.nanmin(l)), close=float(c[~np.isnan(c)][-1]), volume=vol.tolist()))
    T = pl.DataFrame(rows).sort('session')
    T = T.with_columns(pl.col('close').shift(1).alias('prev_close'), pl.col('high').shift(1).alias('pdh'), pl.col('low').shift(1).alias('pdl'),
                       pl.col('session').dt.year().alias('iso_year'), pl.col('session').dt.week().alias('iso_week'))
    # true range and a 14-session ATR (sessions before this one)
    tr = pl.max_horizontal(pl.col('high') - pl.col('low'), (pl.col('high') - pl.col('prev_close')).abs(), (pl.col('low') - pl.col('prev_close')).abs())
    T = T.with_columns(tr.alias('tr')).with_columns(pl.col('tr').shift(1).rolling_mean(14, min_samples=10).alias('atr14'))
    # prior ISO week's high and low
    wk = T.group_by('iso_year', 'iso_week').agg(pl.col('high').max().alias('wh'), pl.col('low').min().alias('wl'), pl.col('session').min().alias('wstart')).sort('wstart')
    wk = wk.with_columns(pl.col('wh').shift(1).alias('pwh'), pl.col('wl').shift(1).alias('pwl')).select('iso_year', 'iso_week', 'pwh', 'pwl')
    T = T.join(wk, on=['iso_year', 'iso_week'], how='left').sort('session')
    T.write_parquet(day_table_path(u))
    return T

def load_day_table(u):
    return pl.read_parquet(day_table_path(u))

# ----------------------------------------------------------------------------------------------- the chain
def chain_arrays(root, d, close_m):
    """bid[right, strike, m], ask[...] dense (NaN where no two-sided quote), strikes sorted; right 0 = CALL, 1 = PUT"""
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(minute_of('timestamp').alias('m'))
    c = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & pl.col('bid').is_not_null() & pl.col('ask').is_not_null()
                 & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0) & (pl.col('ask') > 0))
    strikes = np.sort(c['strike'].unique().to_numpy())
    si = np.searchsorted(strikes, c['strike'].to_numpy()); ri = (c['right'].to_numpy() == 'PUT').astype(int); mi = c['m'].to_numpy()
    bid = np.full((2, len(strikes), 391), np.nan); ask = np.full((2, len(strikes), 391), np.nan)
    bid[ri, si, mi] = c['bid'].to_numpy(); ask[ri, si, mi] = c['ask'].to_numpy()
    return strikes, bid, ask

SQ2 = math.sqrt(2.0)
try:
    from scipy.special import erf as _erf
except Exception:                      # pragma: no cover
    _erf = None
def ncdf(x): return 0.5 * (1.0 + (_erf(x / SQ2) if _erf is not None else _erf_py(x / SQ2)))
def _erf_py(x):
    # vectorised erf (Abramowitz-Stegun 7.1.26, |error| < 1.5e-7)
    s = np.sign(x); x = np.abs(x); t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return s * y

def total_vol(mid, S, K, is_put):
    """Black-Scholes with r = 0 (same day): solve v = sigma*sqrt(T) from the mid by bisection. NaN where no time value."""
    k = K / S; lk = np.log(k)
    intrinsic = np.where(is_put, np.maximum(k - 1.0, 0.0), np.maximum(1.0 - k, 0.0))
    target = mid / S
    lo = np.full_like(target, 1e-5); hi = np.full_like(target, 3.0)
    ok = target > intrinsic + 1e-9
    for _ in range(36):
        v = 0.5 * (lo + hi); d1 = -lk / v + 0.5 * v; d2 = d1 - v
        px = np.where(is_put, k * ncdf(-d2) - ncdf(-d1), ncdf(d1) - k * ncdf(d2))
        up = px < target; lo = np.where(up, v, lo); hi = np.where(up, hi, v)
    v = 0.5 * (lo + hi)
    return np.where(ok, v, np.nan)

def bs_delta(v, S, K, is_put):
    d1 = -np.log(K / S) / v + 0.5 * v
    return np.where(is_put, ncdf(d1) - 1.0, ncdf(d1))

# ----------------------------------------------------------------------------------------------- picks and exits
def pick_contracts(strikes, bid, ask, m, S, right, want_delta=True):
    """right 0 call / 1 put at minute m. Returns dict with the nearest OTM pick ('otm') and the 0.30-0.45 |delta| pick ('dlt'),
    each (strike index or -1). Quote hygiene at entry: ask > 0, bid > 0, bid <= ask (a candidate failing it is skipped)."""
    b = bid[right, :, m]; a = ask[right, :, m]
    clean = (a > 0) & (b > 0) & (b <= a)
    otm = (strikes >= S) if right == 0 else (strikes <= S)
    cand = np.where(clean & otm)[0]
    res = {'otm': -1, 'dlt': -1, 'otm_delta': np.nan, 'dlt_delta': np.nan, 'otm_iv': np.nan, 'dlt_iv': np.nan}
    if len(cand) == 0: return res
    dist = np.abs(strikes[cand] - S)
    res['otm'] = int(cand[np.argmin(dist)])
    near = cand[dist <= 0.03 * S]
    if want_delta and len(near):
        mid = 0.5 * (a[near] + b[near]); v = total_vol(mid, S, strikes[near], right == 1); dl = bs_delta(v, S, strikes[near], right == 1)
        ad = np.abs(dl)
        ok = (ad >= 0.30) & (ad <= 0.45)
        j = int(cand.tolist().index(res['otm'])); jo = np.where(near == res['otm'])[0]
        if len(jo): res['otm_delta'] = float(dl[jo[0]]); res['otm_iv'] = float(v[jo[0]])
        if ok.any():
            sel = np.where(ok)[0]; best = sel[np.argmin(np.abs(ad[sel] - 0.375))]
            res['dlt'] = int(near[best]); res['dlt_delta'] = float(dl[best]); res['dlt_iv'] = float(v[best])
    return res

def settle_of(S_close, K, right): return max(S_close - K, 0.0) if right == 0 else max(K - S_close, 0.0)

def exits(bid_row, m0, a0, S_close, K, right, last=LAST_SELL):
    """buy at ask a0 at minute m0; three ways out on the bid path m0+1..last. Returns per exit (exit_m, exit_px, net_usd, ret_pct).
    Hold: sell at the bid at `last` (the last quoted bid at or before it); a zero bid there is held to expiry (settle, no sell fee)."""
    path = bid_row[m0 + 1:last + 1]
    t = np.arange(m0 + 1, last + 1)
    valid = ~np.isnan(path)
    out = {}
    def fin(mx, px, expired=False):
        fee = FEE if expired else 2 * FEE
        net = (px - a0) * 100.0 - fee
        return (int(mx), float(px), float(net), float(net / (a0 * 100.0) * 100.0))
    # hold to 15:58
    if valid.any():
        li = np.where(valid)[0][-1]; hold_px, hold_m = path[li], t[li]
    else:
        hold_px, hold_m = 0.0, last
    if hold_px <= 0:
        out['hold'] = fin(last, settle_of(S_close, K, right), expired=True)
    else:
        out['hold'] = fin(hold_m, hold_px)
    # trailing stop 50% from the highest bid since buying (the entry minute's bid included)
    b0 = bid_row[m0]; b0 = 0.0 if np.isnan(b0) else b0
    p = np.where(valid, path, -np.inf); peak = np.maximum.accumulate(np.maximum(p, b0))
    hit = valid & (path <= TRAIL * peak) & (peak > 0)
    out['trail'] = fin(t[np.argmax(hit)], path[np.argmax(hit)]) if hit.any() else out['hold']
    # +25% target / -32% stop, else hold
    hit2 = valid & ((path >= TGT * a0) | (path <= STOP * a0))
    out['tgt'] = fin(t[np.argmax(hit2)], path[np.argmax(hit2)]) if hit2.any() else out['hold']
    return out

# ----------------------------------------------------------------------------------------------- sweeps
def episodes_static(h, l, c, L, side, X, first_m, close_m):
    """excursions beyond a fixed level L on 1-minute bars. side 'hi': high >= L(1+X) with the bar before closing below L.
    Returns list of (e, extreme) with a COOLDOWN between episode starts."""
    thr = L * (1 + X / 1e4) if side == 'hi' else L * (1 - X / 1e4)
    eps = []; last_e = -10**6
    for e in range(max(first_m, 2), close_m + 1):
        if e - last_e < COOLDOWN: continue
        if side == 'hi':
            if h[e] >= thr and c[e - 1] < L and h[e - 1] < thr: eps.append(e); last_e = e
        else:
            if l[e] <= thr and c[e - 1] > L and l[e - 1] > thr: eps.append(e); last_e = e
    return eps

def episodes_session_extreme(h, l, c, side, X, first_m, close_m):
    """the session high (low) so far, set at least SH_AGE bars ago, swept by this bar. Returns list of (e, L)."""
    eps = []; last_e = -10**6
    run = np.maximum.accumulate(np.nan_to_num(h[:close_m + 1], nan=-np.inf)) if side == 'hi' else np.minimum.accumulate(np.nan_to_num(l[:close_m + 1], nan=np.inf))
    for e in range(max(first_m, SH_AGE + 2), close_m + 1):
        if e - last_e < COOLDOWN: continue
        L = run[e - 1]
        if not np.isfinite(L): continue
        stale = run[e - SH_AGE] == L            # the extreme has not moved for SH_AGE bars
        if not stale: continue
        thr = L * (1 + X / 1e4) if side == 'hi' else L * (1 - X / 1e4)
        if side == 'hi':
            if h[e] >= thr and c[e - 1] < L: eps.append((e, L)); last_e = e
        else:
            if l[e] <= thr and c[e - 1] > L: eps.append((e, L)); last_e = e
    return eps

def return_bar(c, e, L, side, k, close_m):
    """first bar r in [e, e+k-1] closing back inside L; None if none"""
    for r in range(e, min(e + k, close_m + 1)):
        if (side == 'hi' and c[r] < L) or (side == 'lo' and c[r] > L): return r
    return None

def five_min_episodes(h, l, c, level_fn, side, X, first_M, close_m):
    """5-minute bars (stamps 5j..5j+4 close at M = 5j+5): the bar's extreme beyond L(1+-X), its close back inside L, the
    5-minute bar before closing inside. level_fn(M) gives the level as of the bar's start (static or the running extreme).
    Returns list of (M, L, extreme)."""
    out = []; last = -10**6
    for M in range(((first_M + 4) // 5) * 5, close_m + 1, 5):
        if M - last < COOLDOWN or M < 10: continue
        L = level_fn(M)
        if L is None or not np.isfinite(L): continue
        hh = np.nanmax(h[M - 4:M + 1]); ll = np.nanmin(l[M - 4:M + 1]); cl = c[M]; pc = c[M - 5]
        if np.isnan(cl) or np.isnan(pc): continue
        if side == 'hi':
            if hh >= L * (1 + X / 1e4) and cl < L and pc < L: out.append((M, L, hh)); last = M
        else:
            if ll <= L * (1 - X / 1e4) and cl > L and pc > L: out.append((M, L, ll)); last = M
    return out

# ----------------------------------------------------------------------------------------------- geometry (module 9)
def fvg_present(h, l, r, side):
    """a three-candle gap in the fade direction with its window ending at r-1 or r (known at r):
    bearish (side 'hi'): low[t-2] > high[t]; bullish (side 'lo'): high[t-2] < low[t]."""
    for t in (r - 1, r):
        if t - 2 < 1: continue
        if side == 'hi' and l[t - 2] > h[t]: return 1
        if side == 'lo' and h[t - 2] < l[t]: return 1
    return 0

def order_block(o, h, l, c, r, side):
    """the last opposite-colour candle in [r-5, r-1] before the displacement bar r (the close back inside).
    Zone = its body; a doji (body under a tick) takes its full range; a zero range is no block. Returns (zlo, zhi) or None."""
    for t in range(r - 1, max(r - 6, 0), -1):
        up = c[t] > o[t]
        if (side == 'hi' and up) or (side == 'lo' and not up):
            body = abs(c[t] - o[t])
            if body >= 0.01: return (min(o[t], c[t]), max(o[t], c[t]))
            if h[t] - l[t] >= 0.01: return (l[t], h[t])
            return None
    return None

def ote_fill(h, l, c, r, H, side, close_m, wait=GEOM_WAIT):
    """optimal-trade-entry retrace: after the return bar r the impulse runs from the sweep extreme H to the running
    extreme of the displacement; a fill is the first bar whose range reaches the 0.62-0.705 zone of that leg measured
    back toward H, the bar before having set the leg. Doji guard: the leg must be >= 1 bp of price (else undefined);
    a bar trading through H voids the setup. Returns the fill minute or None."""
    for t in range(r + 1, min(r + wait, close_m, ENTRY_HI) + 1):
        if side == 'hi':
            leg_lo = np.nanmin(l[r:t]); leg = H - leg_lo
            if leg < 1e-4 * H: continue
            z_lo = leg_lo + 0.62 * leg
            if h[t] > H: return None
            if h[t] >= z_lo: return t
        else:
            leg_hi = np.nanmax(h[r:t]); leg = leg_hi - H
            if leg < 1e-4 * H: continue
            z_hi = leg_hi - 0.62 * leg
            if l[t] < H: return None
            if l[t] <= z_hi: return t
    return None

def ob_fill(h, l, r, zone, H, side, close_m, wait=GEOM_WAIT):
    """first bar after r whose range returns into the order block; voided by a bar through the sweep extreme H"""
    if zone is None: return None
    zlo, zhi = zone
    for t in range(r + 1, min(r + wait, close_m, ENTRY_HI) + 1):
        if side == 'hi':
            if h[t] > H: return None
            if h[t] >= zlo: return t
        else:
            if l[t] < H: return None
            if l[t] <= zhi: return t
    return None

def displacement_bars(o, h, l, c, close_m):
    """1-minute bars whose range >= 2x the mean range of the 14 bars before, closing in their direction
    (|close-open| >= half the range). Returns list of (m, dir) with dir +1 up / -1 down."""
    rng = h - l; out = []
    for m in range(16, close_m + 1):
        w = rng[m - 14:m]
        if np.isnan(w).any() or np.isnan(rng[m]): continue
        avg = w.mean()
        if avg <= 0 or rng[m] < 2 * avg: continue
        body = c[m] - o[m]
        if abs(body) < 0.5 * rng[m]: continue
        out.append((m, 1 if body > 0 else -1))
    return out

# ----------------------------------------------------------------------------------------------- stress helpers
def stress(df, col, day_col='session', reps=1000, seed=7):
    """mean, N, days, 95% bootstrap range of the mean resampling days, mean without the best 5 days, total $"""
    if df.height == 0: return dict(n=0)
    x = df.select(day_col, col).drop_nulls()
    byday = x.group_by(day_col).agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
    s = byday['s'].to_numpy(); n = byday['n'].to_numpy()
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(reps):
        i = rng.integers(0, len(s), len(s)); means.append(s[i].sum() / n[i].sum())
    lo, hi = np.percentile(means, [2.5, 97.5])
    order = np.argsort(-s); keep = order[5:]
    wo5 = s[keep].sum() / max(n[keep].sum(), 1)
    return dict(n=int(n.sum()), days=int(len(s)), mean=float(s.sum() / n.sum()), lo95=float(lo), hi95=float(hi), wo_best5=float(wo5),
                best5_share=float(s[order[:5]].sum() / s.sum()) if s.sum() > 0 else float('nan'), days_up=int((s > 0).sum()))
