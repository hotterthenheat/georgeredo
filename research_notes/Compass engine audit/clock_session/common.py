"""Shared helpers for the Compass clock/session audit (modules 1 and 10).

Conventions (from the owner's brief and the prior steps):
- minute of day t = hour*60 + minute, New York. Minute m = 0 is 09:30 (t = 570).
- an underlying 1-minute bar stamped t closes at t+1. A chain NBBO row stamped t is the quote at t.
- half days close at m = 210 (t = 780): the vendor fills bars after 13:00 with null closes.
- a contract is bought at the ask and sold at the bid; $0.65 a contract each way; no fee when it expires worthless.
- fit = 2022-2024, out-of-sample = 2025-2026, context = 2012-2021.
"""
import os, glob, numpy as np, polars as pl

RAW = "/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta"
UW = "/home/user/georgeredo/data_lake/unusualwhales"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
FEE = 0.65
NBARS = 391

def tod(col="timestamp"):
    return pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)

def sessions(kind, sym):
    """kind: 'underlying' | 'index' | 'chains' | 'ohlc'."""
    base = {"underlying": f"{RAW}/data/underlying/{sym}", "index": f"{RAW}/data/index/{sym}",
            "chains": f"{RAW}/data_full/chains/{sym}", "ohlc": f"{RAW}/data/ohlc/{sym}"}[kind]
    return sorted(os.path.basename(p)[:10] for p in glob.glob(f"{base}/*.parquet"))

def period(date):
    y = int(date[:4])
    return "ctx" if y < 2022 else ("fit" if y <= 2024 else "oos")

def load_bars(sym, date):
    """Return dict of numpy arrays (t, open, high, low, close, volume) over the 391 minutes 09:30..16:00,
    or None if the session is missing. For SPX (index prints) open=high=low=close=price, volume=0."""
    if sym == "SPX":
        p = f"{RAW}/data/index/SPX/{date}.parquet"
        if not os.path.exists(p): return None
        df = pl.read_parquet(p).with_columns(tod().alias("t")).sort("t")
        t = df["t"].to_numpy(); px = df["price"].to_numpy().astype(float)
        full = np.full(NBARS, np.nan); idx = t - 570; ok = (idx >= 0) & (idx < NBARS)
        full[idx[ok]] = px[ok]
        return {"t": np.arange(570, 961), "open": full, "high": full, "low": full, "close": full, "volume": np.zeros(NBARS)}
    p = f"{RAW}/data/underlying/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    df = pl.read_parquet(p, columns=["timestamp", "open", "high", "low", "close", "volume"]).with_columns(tod().alias("t")).sort("t")
    out = {"t": np.arange(570, 961)}
    idx = df["t"].to_numpy() - 570; ok = (idx >= 0) & (idx < NBARS)
    for c in ["open", "high", "low", "close", "volume"]:
        full = np.full(NBARS, np.nan); full[idx[ok]] = df[c].to_numpy().astype(float)[ok]; out[c] = full
    return out

def is_half_day(bars):
    """True when the session closed at 13:00: no close printed at 15:00 (ETF files) or no price (index)."""
    c = bars["close"]
    return np.isnan(c[900 - 570]) or np.isnan(c[958 - 570])

def quotes(sym, date, strikes, right, t_lo=570, t_hi=960):
    """NBBO rows for the given strikes/right, between t_lo and t_hi inclusive. sym: SPY|QQQ|IWM|SPXW."""
    p = f"{RAW}/data_full/chains/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    return (pl.scan_parquet(p).with_columns(tod().alias("t"))
            .filter(pl.col("right") == right).filter(pl.col("strike").is_in(list(strikes)))
            .filter((pl.col("t") >= t_lo) & (pl.col("t") <= t_hi))
            .select("t", "strike", "bid", "ask").collect())

def chain_strikes(sym, date):
    p = f"{RAW}/data_full/chains/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    return np.sort(pl.scan_parquet(p).select("strike").unique().collect()["strike"].to_numpy())

def nearest_otm(strikes, spot, right):
    """Nearest strictly out-of-the-money strike; None if none."""
    if right == "CALL":
        s = strikes[strikes > spot]; return float(s.min()) if s.size else None
    s = strikes[strikes < spot]; return float(s.max()) if s.size else None

def trade_path(bid, ask, t_entry, t_exit, trail=None):
    """bid/ask: arrays indexed by t-570 for one contract. Buy at the ask at t_entry, sell at the bid at
    t_exit or when a trailing stop (share of the highest bid since entry) is hit. Returns (entry_ask, exit_bid,
    exit_t, pnl_dollars_per_contract). pnl includes $0.65 each way; none on the sale when it expires worthless
    (exit bid 0 at the close)."""
    i0, i1 = t_entry - 570, t_exit - 570
    a0 = ask[i0]
    if not np.isfinite(a0) or a0 <= 0: return None
    exit_t, exit_b = t_exit, bid[i1]
    if trail is not None:
        peak = -np.inf
        for i in range(i0 + 1, i1 + 1):
            b = bid[i]
            if not np.isfinite(b): continue
            peak = max(peak, b)
            if peak > 0 and b <= peak * (1 - trail):
                exit_t, exit_b = i + 570, b; break
    if not np.isfinite(exit_b): exit_b = 0.0
    fee = FEE + (FEE if exit_b > 0 else 0.0)
    return a0, exit_b, exit_t, (exit_b - a0) * 100 - fee

def boot_ci(values, days, n=2000, seed=7):
    """95% bootstrap interval of the mean, resampling days (sessions) with replacement."""
    values = np.asarray(values, float); days = np.asarray(days)
    if values.size == 0: return (np.nan, np.nan)
    ud, inv = np.unique(days, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=ud.size); cnts = np.bincount(inv, minlength=ud.size)
    rng = np.random.default_rng(seed); means = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, ud.size, ud.size)
        means[k] = sums[pick].sum() / max(cnts[pick].sum(), 1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))

def stress(values, days):
    """mean, 95% day-bootstrap interval, mean without the best 5 days, and by year."""
    values = np.asarray(values, float); days = np.asarray(days)
    if values.size == 0: return {"n": 0}
    lo, hi = boot_ci(values, days)
    ud, inv = np.unique(days, return_inverse=True)
    daysum = np.bincount(inv, weights=values, minlength=ud.size)
    best5 = set(np.argsort(daysum)[-5:])
    keep = np.array([i not in best5 for i in inv])
    years = {}
    for y in sorted(set(d[:4] for d in ud)):
        m = np.array([d.startswith(y) for d in days]); years[y] = (int(m.sum()), float(values[m].mean()))
    return {"n": int(values.size), "days": int(ud.size), "mean": float(values.mean()), "ci_lo": lo, "ci_hi": hi,
            "wo_best5": float(values[keep].mean()) if keep.any() else np.nan,
            "win_rate": float((values > 0).mean()), "days_up": int((daysum > 0).sum()), "by_year": years}

def fmt_stress(s):
    if not s or s.get("n", 0) == 0: return "n=0"
    by = " ".join(f"{y}:{v[1]:+.2f}({v[0]})" for y, v in s["by_year"].items())
    return (f"n={s['n']} days={s['days']} mean={s['mean']:+.2f} ci=[{s['ci_lo']:+.2f},{s['ci_hi']:+.2f}] "
            f"wo_best5={s['wo_best5']:+.2f} win={s['win_rate']:.3f} days_up={s['days_up']} | {by}")
