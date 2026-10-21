"""Shared helpers for Compass Phase 2, Hypothesis A (the low-moc_mag closing pin).

Conventions (the owner's brief, the audit's):
- minute of day t = hour*60 + minute, New York; 09:30 = 570, 16:00 = 960.
- an underlying 1-minute bar stamped t closes at t+1; a chain NBBO row stamped t is the quote at t.
- half days are dropped (no close printed at 15:00 or 15:58).
- a short leg is sold at the bid, a long leg bought at the ask; $0.65 a leg each way; a leg that expires worthless pays
  no closing fee; a leg settled in the money pays no closing fee either (cash settlement at intrinsic; no assignment or
  exercise fee is charged for SPXW or SPY - stated in the notes).
- fit = 2022-2024, out-of-sample = 2025-2026.
Nothing here calls a vendor.
"""
import os, glob, math, numpy as np, polars as pl

RAW = "/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta"
AUDIT = "/home/user/georgeredo/research_notes/Compass engine audit/clock_session"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
FEE = 0.65
NBARS = 391
T0 = 900            # first minute kept in memory from a chain file
NT = 961 - T0       # minutes 900..960 inclusive

def tod(col="timestamp"):
    return pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)

def sessions(kind, sym):
    base = {"underlying": f"{RAW}/data/underlying/{sym}", "index": f"{RAW}/data/index/{sym}",
            "chains": f"{RAW}/data_full/chains/{sym}", "ohlc": f"{RAW}/data/ohlc/{sym}"}[kind]
    return sorted(os.path.basename(p)[:10] for p in glob.glob(f"{base}/*.parquet"))

def period(date):
    y = int(date[:4]); return "fit" if y <= 2024 else "oos"

def load_bars(sym, date):
    """Dict of arrays over the 391 minutes 09:30..16:00 (index = t - 570). SPX: price only (open=high=low=close)."""
    if sym == "SPX":
        p = f"{RAW}/data/index/SPX/{date}.parquet"
        if not os.path.exists(p): return None
        df = pl.read_parquet(p).with_columns(tod().alias("t")).sort("t")
        t = df["t"].to_numpy(); px = df["price"].to_numpy().astype(float)
        full = np.full(NBARS, np.nan); idx = t - 570; ok = (idx >= 0) & (idx < NBARS); full[idx[ok]] = px[ok]
        return {"open": full, "high": full, "low": full, "close": full, "volume": np.zeros(NBARS)}
    p = f"{RAW}/data/underlying/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    df = pl.read_parquet(p, columns=["timestamp", "open", "high", "low", "close", "volume"]).with_columns(tod().alias("t")).sort("t")
    out = {}
    idx = df["t"].to_numpy() - 570; ok = (idx >= 0) & (idx < NBARS)
    for c in ["open", "high", "low", "close", "volume"]:
        full = np.full(NBARS, np.nan); full[idx[ok]] = df[c].to_numpy().astype(float)[ok]; out[c] = full
    return out

def is_half_day(bars):
    c = bars["close"]; return np.isnan(c[900 - 570]) or np.isnan(c[958 - 570])

def settlement(sym, bars):
    """SPXW: the last SPX print at or before 16:00 (a proxy for the official settlement). SPY: the 16:00 bar's close when
    printed, else the 15:59 bar's close."""
    c = bars["close"]
    if sym == "SPXW":
        for i in range(960 - 570, 950 - 570, -1):
            if np.isfinite(c[i]): return float(c[i])
        return None
    return float(c[960 - 570]) if np.isfinite(c[960 - 570]) else float(c[959 - 570])

def spot_at(sym, bars, t):
    """The underlying at minute t: SPX's print stamped t; an ETF's bar stamped t-1 (it closes at t)."""
    c = bars["close"]
    v = c[t - 570] if sym == "SPXW" else c[t - 1 - 570]
    return float(v) if np.isfinite(v) else None

class Chain:
    """One session's chain from 15:00: bid/ask arrays per (strike, right) over minutes 900..960 (index t-900).
    Prices rounded to 4 decimals on load (the audit's float32 lesson)."""
    def __init__(self, sym, date):
        p = f"{RAW}/data_full/chains/{sym}/{date}.parquet"
        df = (pl.scan_parquet(p).with_columns(tod().alias("t")).filter(pl.col("t") >= T0)
              .select("t", "strike", "right", "bid", "ask").collect())
        self.strikes = np.sort(df["strike"].unique().to_numpy())
        self.bid = {}; self.ask = {}
        for (k, r), g in df.group_by(["strike", "right"]):
            b = np.full(NT, np.nan); a = np.full(NT, np.nan)
            idx = g["t"].to_numpy() - T0
            b[idx] = np.round(g["bid"].to_numpy().astype(float), 4); a[idx] = np.round(g["ask"].to_numpy().astype(float), 4)
            self.bid[(float(k), r)] = b; self.ask[(float(k), r)] = a
    def quote(self, K, right, t):
        b = self.bid.get((float(K), right)); a = self.ask.get((float(K), right))
        if b is None: return (np.nan, np.nan)
        return (b[t - T0], a[t - T0])

# ---- Black-Scholes with r = q = 0 (the delta is invariant to the year-fraction convention when r = q = 0) ----
SQRT2 = math.sqrt(2.0)
def _ncdf(x): return 0.5 * (1.0 + math.erf(x / SQRT2))

def bs_price(S, K, sig, T, right):
    if sig <= 0 or T <= 0: return max(S - K, 0.0) if right == "CALL" else max(K - S, 0.0)
    v = sig * math.sqrt(T); d1 = math.log(S / K) / v + 0.5 * v; d2 = d1 - v
    return S * _ncdf(d1) - K * _ncdf(d2) if right == "CALL" else K * _ncdf(-d2) - S * _ncdf(-d1)

def implied_vol(price, S, K, T, right, lo=1e-4, hi=20.0):
    """Bisection on sigma; None when price - intrinsic <= 0.01 (the same-day skip rule) or no root."""
    intr = max(S - K, 0.0) if right == "CALL" else max(K - S, 0.0)
    if price - intr <= 0.01: return None
    if bs_price(S, K, hi, T, right) < price: return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, mid, T, right) > price: hi = mid
        else: lo = mid
    return 0.5 * (lo + hi)

def bs_delta(S, K, sig, T, right):
    v = sig * math.sqrt(T); d1 = math.log(S / K) / v + 0.5 * v
    return _ncdf(d1) if right == "CALL" else _ncdf(d1) - 1.0

def years_to_close(t):
    return (960 - t) / (365.0 * 1440.0)

def boot_ci(values, days, n=2000, seed=7):
    values = np.asarray(values, float); days = np.asarray(days)
    if values.size == 0: return (np.nan, np.nan)
    ud, inv = np.unique(days, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=ud.size); cnts = np.bincount(inv, minlength=ud.size)
    rng = np.random.default_rng(seed); means = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, ud.size, ud.size); means[k] = sums[pick].sum() / max(cnts[pick].sum(), 1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))
