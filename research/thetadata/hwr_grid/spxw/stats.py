"""Statistics shared by te.py and analyze.py (PREREGISTRATION.md T-E.5, G.7, G.8)."""
import numpy as np

B = 5000; SEED = 7


def cluster_boot_loop(x, cl, n=B, seed=SEED):
    """Verbatim logic of index_tests/tc_spxw_straddle/analyze_tc.py cluster_boot (date-clustered percentile bootstrap)."""
    x = np.asarray(x, float); cl = np.asarray(cl); ids = np.unique(cl); groups = [x[cl == i] for i in ids]
    rng = np.random.default_rng(seed); out = np.empty(n)
    for b in range(n):
        pick = rng.integers(0, len(ids), len(ids)); out[b] = np.mean(np.concatenate([groups[i] for i in pick]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


class Boot:
    """Vectorised version for one observation per day (x in date order): identical draws to cluster_boot_loop
    (verified in te.py).  Index matrices are cached per n (one at a time, configurations are processed sorted by n)."""

    def __init__(self, n_draws=B, seed=SEED):
        self.B = n_draws; self.seed = seed; self._n = None; self._idx = None

    def idx(self, n):
        if n != self._n:
            self._idx = np.random.default_rng(self.seed).integers(0, n, (self.B, n)); self._n = n
        return self._idx

    def ci(self, x):
        x = np.asarray(x, float); n = len(x)
        if n < 2: return np.nan, np.nan, np.nan
        m = x[self.idx(n)].mean(axis=1)
        return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), float(m.std(ddof=1))


def max_dd(x):
    """Maximum drawdown ($) of the cumulative 1-lot P&L, starting from 0."""
    cum = np.cumsum(np.asarray(x, float)); peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    return float((cum - peak).min()) if len(cum) else 0.0


def basic(x):
    x = np.asarray(x, float); gp = x[x > 0].sum(); gl = -x[x < 0].sum()
    return dict(n=len(x), total=float(x.sum()), mean=float(x.mean()) if len(x) else np.nan, sd=float(x.std(ddof=1)) if len(x) > 1 else np.nan,
                median=float(np.median(x)) if len(x) else np.nan, win_rate=float((x > 0).mean()) if len(x) else np.nan,
                pf=float(gp / gl) if gl > 0 else np.inf, max_dd=max_dd(x))


def kelly_capital(x):
    """Full-Kelly capital per lot C* = argmax mean log(1 + x/C); None if mean <= 0."""
    from scipy.optimize import brentq
    x = np.asarray(x, float)
    if len(x) == 0 or x.mean() <= 0: return None
    lo = -x.min() * (1 + 1e-9) + 1e-6 if x.min() < 0 else 1e-6
    g = lambda C: np.mean(x / (C + x))
    hi = max(lo * 2, 1.0)
    while g(hi) < 0: hi *= 2
    return float(brentq(g, lo, hi, xtol=1.0))


def path_stats(x, cap, n_paths=3000, seed=SEED):
    """Compounding equity W_t = prod(1 + x_s / cap): actual max drawdown and day-resampled path distribution."""
    x = np.asarray(x, float)
    def dd_end(r):
        w = np.cumprod(1 + r / cap, axis=-1); w = np.concatenate([np.ones(w.shape[:-1] + (1,)), w], axis=-1)
        if (w <= 0).any(): w = np.where(np.minimum.accumulate(w > 0, axis=-1), w, 0.0)
        peak = np.maximum.accumulate(w, axis=-1); dd = (w / peak - 1).min(axis=-1)
        return dd, w[..., -1]
    a_dd, a_end = dd_end(x)
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(x), (n_paths, len(x)))
    dd, end = dd_end(x[idx])
    return dict(capital=round(cap, 0), actual_maxdd=round(float(a_dd), 4), actual_end=round(float(a_end), 4),
                boot_median_dd=round(float(np.median(dd)), 4), p_dd_gt20=round(float((dd < -0.2).mean()), 4),
                p_dd_gt30=round(float((dd < -0.3).mean()), 4), p_dd_gt50=round(float((dd < -0.5).mean()), 4),
                p_end_below_start=round(float((end < 1).mean()), 4), boot_median_end=round(float(np.median(end)), 4))
