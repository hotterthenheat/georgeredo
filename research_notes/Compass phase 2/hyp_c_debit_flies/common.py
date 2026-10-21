"""Compass Phase 2, Hypothesis C: shared helpers (paths, pricing, settlement, stats).

Conventions (the audit's, unchanged): minute m = 0 is 09:30; a bar stamped t closes at t+1; a chain row stamped t is the
quote at t; spot at quote minute m = close of the bar stamped m-1 (ETF) or the SPX print at m (SPXW); half days dropped.
Fills: a long leg is bought at the ask and sold at the bid, a short leg sold at the bid and bought back at the ask; $0.65 a
leg each way; a leg expiring worthless pays no closing fee; a leg expiring in the money settles at intrinsic with no fee
(SPXW: cash on the last SPX print at or before 16:00 as a proxy for the official SET; SPY/QQQ/IWM: the 16:00 close -
the bar stamped 15:59 - with no assignment or exercise fee assumed).
Deltas: Black-Scholes on the mid's implied vol with r = q = 0; with r = q = 0 the delta depends on sigma*sqrt(T) alone,
so the total vol v is solved directly from the mid (bisection) and no day-count convention enters. A contract with
mid - intrinsic <= 0.01 is skipped (no vol can be read off it).
Split: fit = 2022-2024, OOS = 2025-2026.
"""
import os, sys, numpy as np, polars as pl
from math import erf, sqrt, log

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out'); LOGS = os.path.join(HERE, 'logs')
AUDIT = '/home/user/georgeredo/research_notes/Compass engine audit'
AUDIT_EXITS = os.path.join(AUDIT, 'exits_sizing'); AUDIT_CLOCK = os.path.join(AUDIT, 'clock_session')
FEE = 0.65
NMIN = 391
SPLIT = '2025-01-01'
PRODUCTS = ['SPXW', 'SPY', 'QQQ', 'IWM']
UNDERLYING = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
DELTA_CELLS = {'d60_40': (0.60, 0.40), 'd70_30': (0.70, 0.30), 'd55_45': (0.55, 0.45)}   # + 'atm_otm1'
FLY_WINGS = {'SPXW': [5.0, 10.0, 25.0], 'SPY': [1.0, 2.0, 5.0], 'QQQ': [1.0, 2.0, 5.0], 'IWM': [0.5, 1.0, 2.0]}
STRIKE_STEP = {'SPXW': 5.0, 'SPY': 1.0, 'QQQ': 1.0, 'IWM': 1.0}   # the grid the straddle-width wing is rounded to (IWM's 0.5 strikes exist on few sessions, so its straddle wing rounds to $1)
FLY_TIMES = {'1500': 330, '1530': 360}
MIN_DEBIT = 0.05

def period_of(date):
    return 'fit' if date < SPLIT else 'oos'

def mcol(col='timestamp'):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

# ---------- Black-Scholes with r = q = 0, in total vol v = sigma*sqrt(T) ----------
SQ2 = sqrt(2.0)
def _ncdf(x):
    return 0.5 * (1.0 + np.vectorize(erf)(x / SQ2)) if np.ndim(x) else 0.5 * (1.0 + erf(x / SQ2))

try:
    from scipy.special import ndtr as ncdf
except Exception:   # pragma: no cover
    ncdf = _ncdf

def bs_price(S, K, v, is_call):
    """r = q = 0. v = sigma*sqrt(T) > 0. Vectorised."""
    S = np.asarray(S, float); K = np.asarray(K, float); v = np.asarray(v, float)
    d1 = np.log(S / K) / v + v / 2; d2 = d1 - v
    c = S * ncdf(d1) - K * ncdf(d2)
    return np.where(is_call, c, c - S + K)

def total_vol_from_mid(S, K, mid, is_call, lo=1e-5, hi=4.0, it=60):
    """bisection for v in [lo, hi] such that bs_price(S,K,v) = mid; NaN where mid <= intrinsic + 0.01 or outside the bracket."""
    S = np.asarray(S, float); K = np.asarray(K, float); mid = np.asarray(mid, float); is_call = np.asarray(is_call, bool)
    intr = np.where(is_call, np.maximum(S - K, 0), np.maximum(K - S, 0))
    ok = (mid - intr > 0.01) & (S > 0) & (K > 0)
    a = np.full(mid.shape, lo); b = np.full(mid.shape, hi)
    for _ in range(it):
        m = 0.5 * (a + b); p = bs_price(S, K, m, is_call)
        up = p < mid
        a = np.where(up, m, a); b = np.where(up, b, m)
    v = 0.5 * (a + b)
    # outside the bracket: price at hi still below mid (mid above the cap) -> NaN
    ok &= bs_price(S, K, np.full(mid.shape, hi), is_call) >= mid
    return np.where(ok, v, np.nan)

def bs_delta(S, K, v, is_call):
    d1 = np.log(np.asarray(S, float) / np.asarray(K, float)) / v + v / 2
    return np.where(is_call, ncdf(d1), ncdf(d1) - 1.0)

# ---------- chains and bars ----------
def read_chain(root, d):
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet')).with_columns(mcol().alias('m'))
    ok = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0) & (pl.col('ask') > 0)
    return c.filter(ok & (pl.col('m') >= 0) & (pl.col('m') <= 390))

def to_arr(df, key, val, n=NMIN):
    a = np.full(n, np.nan); k = df[key].to_numpy(); v = df[val].to_numpy().astype(float)
    ok = (k >= 0) & (k < n); a[k[ok]] = v[ok]; return a

def session_frame(root, d):
    """spot[m] for quote minutes (ETF: close of bar m-1; SPX: print at m), bar high/low/close by bar stamp, close_m, half."""
    u = UNDERLYING[root]
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    if spy.height == 0: return None
    half = spy['timestamp'].max().hour < 15
    close_m = 210 if half else 390
    if u == 'SPX':
        sp = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).with_columns(mcol().alias('m')).filter(pl.col('price').is_not_null())
        if sp.height < 100: return None
        spot = to_arr(sp, 'm', 'price')
        bh = bl = bc = None
    else:
        b = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet'), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).with_columns(mcol().alias('m')).filter(pl.col('close').is_not_null())
        if b.height < 100: return None
        bh = to_arr(b, 'm', 'high'); bl = to_arr(b, 'm', 'low'); bc = to_arr(b, 'm', 'close')
        spot = np.full(NMIN, np.nan); spot[1:] = bc[:-1]
    if np.all(np.isnan(spot)): return None
    sc = spot[close_m] if not np.isnan(spot[close_m]) else spot[~np.isnan(spot)][-1]
    return dict(spot=spot, bh=bh, bl=bl, bc=bc, close_m=close_m, half=half, spot_close=float(sc))

def intrinsic(S, K, right):
    return max(S - K, 0.0) if right == 'CALL' else max(K - S, 0.0)

# ---------- stats ----------
def boot_ci(values, days, n=2000, seed=7):
    values = np.asarray(values, float); days = np.asarray(days)
    if values.size == 0: return (np.nan, np.nan)
    ud, inv = np.unique(days, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=ud.size); cnts = np.bincount(inv, minlength=ud.size)
    rng = np.random.default_rng(seed); means = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, ud.size, ud.size)
        means[k] = sums[pick].sum() / max(cnts[pick].sum(), 1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))

def cell_stats(pnl, pct, days, order=None):
    """pnl $ per structure, pct = pnl / max risk; days = session strings; order = chronological sort key (default days)."""
    pnl = np.asarray(pnl, float); pct = np.asarray(pct, float); days = np.asarray(days)
    n = pnl.size
    if n == 0: return dict(n=0)
    o = np.argsort(days if order is None else order, kind='stable'); p = pnl[o]; d = days[o]
    win = p > 0; loss = p < 0
    eq = np.cumsum(p); dd = eq - np.maximum.accumulate(np.maximum(eq, 0)); mdd = float(dd.min())
    streak = cur = 0
    for x in p:
        cur = cur + 1 if x <= 0 else 0; streak = max(streak, cur)
    ud, inv = np.unique(d, return_inverse=True); daysum = np.bincount(inv, weights=p, minlength=ud.size)
    top5 = np.argsort(daysum)[-5:]; keep = np.ones(ud.size, bool); keep[top5] = False
    wo5 = float(p[keep[inv]].mean()) if keep.any() else np.nan
    pct_o = pct[o]; wo5_pct = float(pct_o[keep[inv]].mean()) if keep.any() else np.nan
    lo, hi = boot_ci(pct, days)
    lo_usd, hi_usd = boot_ci(pnl, days)
    years = {}
    for y in sorted(set(x[:4] for x in ud)):
        mk = np.char.startswith(d.astype(str), y); years[y] = (int(mk.sum()), float(p[mk].mean()), float(pct_o[mk].mean()))
    gw = p[win].sum(); gl = -p[loss].sum()
    return dict(n=int(n), sessions=int(ud.size), mean_usd=float(p.mean()), mean_pct=float(pct.mean()), ci_lo_pct=lo, ci_hi_pct=hi,
                ci_lo_usd=lo_usd, ci_hi_usd=hi_usd, win_rate=float(win.mean()),
                avg_win_usd=float(p[win].mean()) if win.any() else np.nan, avg_loss_usd=float(p[loss].mean()) if loss.any() else np.nan,
                avg_win_pct=float(pct_o[win].mean()) if win.any() else np.nan, avg_loss_pct=float(pct_o[loss].mean()) if loss.any() else np.nan,
                p5_usd=float(np.percentile(p, 5)), p1_usd=float(np.percentile(p, 1)), worst_usd=float(p.min()),
                worst_session=str(ud[np.argmin(daysum)]), worst_session_usd=float(daysum.min()),
                profit_factor=float(gw / gl) if gl > 0 else np.inf, max_dd_usd=mdd, longest_losing=int(streak),
                wo_best5_usd=wo5, wo_best5_pct=wo5_pct, days_up=int((daysum > 0).sum()),
                by_year=' '.join(f'{y}:{v[1]:+.1f}$({v[2]*100:+.1f}%,n{v[0]})' for y, v in years.items()))

def fmt(s):
    if not s or s.get('n', 0) == 0: return 'n=0'
    return (f"n={s['n']:5d} sess={s['sessions']:4d} mean=${s['mean_usd']:+7.2f} ({s['mean_pct']*100:+6.2f}% of risk) ci%=[{s['ci_lo_pct']*100:+6.2f},{s['ci_hi_pct']*100:+6.2f}] "
            f"win={s['win_rate']:.3f} avgW=${s['avg_win_usd']:+6.1f} avgL=${s['avg_loss_usd']:+6.1f} p5=${s['p5_usd']:+6.1f} p1=${s['p1_usd']:+6.1f} worst=${s['worst_usd']:+6.1f} "
            f"worstSess={s['worst_session']}(${s['worst_session_usd']:+.0f}) PF={s['profit_factor']:.2f} MDD=${s['max_dd_usd']:+.0f} streak={s['longest_losing']} "
            f"wo5=${s['wo_best5_usd']:+.2f}({s['wo_best5_pct']*100:+.2f}%) daysUp={s['days_up']} | {s['by_year']}")
