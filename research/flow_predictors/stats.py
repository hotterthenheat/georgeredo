"""Statistics: pooled Spearman IC with daily-block bootstrap CI, daily-IC t-stat, quintile spreads, hit rates.
Bootstrap resamples trading days with replacement (B reps) using per-day sufficient statistics of the globally ranked data
(ranks are not recomputed inside each replicate - the usual fast approximation)."""
import numpy as np
from scipy.stats import rankdata, spearmanr, norm

def _corr_from_S(S):
    n, sx, sy, sxx, syy, sxy = [S[..., i] for i in range(6)]
    num = n * sxy - sx * sy; den = np.sqrt(np.maximum(n * sxx - sx ** 2, 1e-12) * np.maximum(n * syy - sy ** 2, 1e-12))
    return num / den

def _day_index(days):
    u, inv = np.unique(np.asarray(days), return_inverse=True)
    return u, inv

def pooled_ic(x, y, days, B=2000, seed=0):
    """Pooled Spearman IC between x and y, daily-block bootstrap CI/SE, normal-approx two-sided p."""
    x = np.asarray(x, float); y = np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]; days = np.asarray(days)[m]
    if len(x) < 50: return dict(n=len(x), days=0, ic=np.nan, lo=np.nan, hi=np.nan, se=np.nan, p=np.nan)
    rx, ry = rankdata(x), rankdata(y); u, di = _day_index(days); D = len(u)
    S = np.zeros((D, 6))
    for k, v in enumerate([np.ones_like(rx), rx, ry, rx * rx, ry * ry, rx * ry]): np.add.at(S[:, k], di, v)
    ic = float(_corr_from_S(S.sum(0)))
    rng = np.random.default_rng(seed); W = rng.multinomial(D, np.full(D, 1.0 / D), size=B)
    ics = _corr_from_S(W @ S); se = float(ics.std(ddof=1)); lo, hi = np.percentile(ics, [2.5, 97.5])
    p = float(2 * (1 - norm.cdf(abs(ic) / se))) if se > 0 else np.nan
    return dict(n=int(len(x)), days=int(D), ic=ic, lo=float(lo), hi=float(hi), se=se, p=p)

def daily_ic(x, y, days, min_n=30):
    x = np.asarray(x, float); y = np.asarray(y, float); days = np.asarray(days)
    out = []
    for d in np.unique(days):
        m = (days == d) & np.isfinite(x) & np.isfinite(y)
        if m.sum() >= min_n:
            r = spearmanr(x[m], y[m]).correlation
            if np.isfinite(r): out.append(r)
    out = np.array(out)
    if len(out) < 5: return dict(dic_mean=np.nan, dic_t=np.nan, dic_days=len(out), dic_pos=np.nan)
    return dict(dic_mean=float(out.mean()), dic_t=float(out.mean() / (out.std(ddof=1) / np.sqrt(len(out)))), dic_days=int(len(out)), dic_pos=float((out > 0).mean()))

def quintiles(x, y, days, B=2000, seed=1, nq=5):
    """Mean forward return (bps) per quintile of x; Q_top - Q_bottom spread with daily-block bootstrap CI. y in log return units."""
    x = np.asarray(x, float); y = np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]; days = np.asarray(days)[m]
    if len(x) < 50: return dict(spread=np.nan, sp_lo=np.nan, sp_hi=np.nan, sp_p=np.nan, hr_top=np.nan, hr_bot=np.nan, sign_agree=np.nan, qmeans=[np.nan] * nq)
    edges = np.quantile(x, np.linspace(0, 1, nq + 1)[1:-1]); q = np.searchsorted(edges, x, side='right')
    u, di = _day_index(days); D = len(u)
    qm = [float(y[q == k].mean() * 1e4) if (q == k).any() else np.nan for k in range(nq)]
    S = np.zeros((D, 4))
    for k, (sel, col) in enumerate([(q == nq - 1, 0), (q == 0, 2)]):
        np.add.at(S[:, col], di[sel], 1); np.add.at(S[:, col + 1], di[sel], y[sel])
    rng = np.random.default_rng(seed); W = rng.multinomial(D, np.full(D, 1.0 / D), size=B); T = W @ S
    sp = (T[:, 1] / np.maximum(T[:, 0], 1) - T[:, 3] / np.maximum(T[:, 2], 1)) * 1e4
    spread = (qm[nq - 1] - qm[0]); se = float(sp.std(ddof=1)); lo, hi = np.percentile(sp, [2.5, 97.5])
    p = float(2 * (1 - norm.cdf(abs(spread) / se))) if se > 0 else np.nan
    top = y[q == nq - 1]; bot = y[q == 0]
    nz = (x != 0) & (y != 0)
    return dict(spread=float(spread), sp_lo=float(lo), sp_hi=float(hi), sp_p=p, hr_top=float((top > 0).mean()), hr_bot=float((bot < 0).mean()),
                sign_agree=float((np.sign(x[nz]) == np.sign(y[nz])).mean()) if nz.any() else np.nan, qmeans=qm)

def cell(x, y, days, B=2000, with_daily=True):
    r = pooled_ic(x, y, days, B=B)
    if with_daily: r.update(daily_ic(x, y, days))
    qq = quintiles(x, y, days, B=B); qm = qq.pop('qmeans'); r.update(qq)
    for k, v in enumerate(qm): r[f'q{k + 1}_bps'] = v
    return r

def mean_ci(v, days=None, B=2000, seed=2):
    """Mean of v with CI; if days given, daily-block bootstrap, else iid bootstrap."""
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if len(v) < 5: return dict(mean=np.nan, lo=np.nan, hi=np.nan, n=len(v))
    rng = np.random.default_rng(seed)
    if days is None:
        bs = rng.choice(v, size=(B, len(v)), replace=True).mean(1)
    else:
        days = np.asarray(days); u, di = _day_index(days); D = len(u)
        S = np.zeros((D, 2)); np.add.at(S[:, 0], di, 1); np.add.at(S[:, 1], di, v)
        W = rng.multinomial(D, np.full(D, 1.0 / D), size=B); T = W @ S; bs = T[:, 1] / np.maximum(T[:, 0], 1)
    lo, hi = np.percentile(bs, [2.5, 97.5]); se = bs.std(ddof=1)
    return dict(mean=float(v.mean()), lo=float(lo), hi=float(hi), n=int(len(v)), p=float(2 * (1 - norm.cdf(abs(v.mean()) / se))) if se > 0 else np.nan)
