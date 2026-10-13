"""Q2 extra: partial IC of gamma_oi vs |r30| controlling for trailing |r_prev30|; between-day vs within-day decomposition."""
import csv
from common import *
rows = list(csv.DictReader(open(OUT + '/q2_minute_obs.csv')))
def col(k): return np.array([float(r[k]) if r[k] not in ('', 'nan') else np.nan for r in rows])
g = col('gamma_oi'); a30 = col('abs_r30'); pv = np.abs(col('r_prev30')); d = np.array([r['date'] for r in rows])
ok = ~np.isnan(g) & ~np.isnan(a30) & ~np.isnan(pv)
def rk(x): return np.argsort(np.argsort(x)).astype(float)
def partial(g, a, p):
    rg, ra, rp = rk(g), rk(a), rk(p)
    def resid(y, x): X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; return y - X @ b
    return float(np.corrcoef(resid(rg, rp), resid(ra, rp))[0, 1])
lo, hi = boot_stat_ci(partial, [g[ok], a30[ok], pv[ok]], d[ok], 300)
days = sorted(set(d)); mg = np.array([np.nanmean(g[d == x]) for x in days]); rv = np.array([np.nanmean(a30[d == x]) for x in days]); sh = np.array([np.mean(g[(d == x) & ~np.isnan(g)] > 0) for x in days])
wg = np.concatenate([rk(g[(d == x) & ok]) / max(((d == x) & ok).sum(), 1) for x in days]); wa = np.concatenate([rk(a30[(d == x) & ok]) / max(((d == x) & ok).sum(), 1) for x in days])
out = dict(n=int(ok.sum()), ic_gamma_oi_abs_r30=spearman(g[ok], a30[ok]), ic_absprev30_abs_r30=spearman(pv[ok], a30[ok]), partial_ic=partial(g[ok], a30[ok], pv[ok]), partial_ic_lo=lo, partial_ic_hi=hi,
           n_days=len(days), day_level_spearman_mean_gamma_vs_mean_abs_r30=spearman(mg, rv), day_level_spearman_share_pos_vs_mean_abs_r30=spearman(sh, rv), days_mean_gamma_pos=int((mg > 0).sum()), within_day_ic=float(np.corrcoef(wg, wa)[0, 1]))
write_csv(OUT + '/q2_extra.csv', [out]); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()})
