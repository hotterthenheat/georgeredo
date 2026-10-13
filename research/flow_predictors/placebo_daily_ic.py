"""Placebo: within-day Spearman IC between a trailing-15-minute return and forward 15/30/60-minute returns on simulated iid random walks
with the same panel shape (339 days x 390 minutes, t in 15..360). Shows the mechanical negative bias of within-day ICs."""
import numpy as np
from scipy.stats import spearmanr
rng = np.random.default_rng(0); out = {15: [], 30: [], 60: []}
for d in range(339):
    r = rng.standard_normal(390) * 3e-4; p = np.cumsum(r)
    t = np.arange(15, 361); back = p[t] - p[t - 15]
    for h in out:
        ok = t + h < 390; fwd = p[t[ok] + h] - p[t[ok]]; out[h].append(spearmanr(back[ok], fwd).correlation)
for h in out:
    a = np.array(out[h]); print(f'placebo daily IC (trailing15 vs fwd{h}): mean {a.mean():.4f}  t {a.mean() / (a.std(ddof=1) / np.sqrt(len(a))):.1f}')
