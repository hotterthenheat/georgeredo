"""
stats.py — the comparison statistic of prereg section 6, on top of audit_lib (imported, never rewritten): per session s in
calendar order S_s = Σ r and N_s = number of trades of an arm entered in s; an arm's mean per trade = Σ S ÷ Σ N; Δ = mean(with)
− mean(without); the 20-session moving-block bootstrap (audit_lib.block_draws(n, 20), weights_from, 2,000 draws, the SAME
draw for both arms), the 95% percentile interval (pct_ci), none under 60 sessions; effective N by the block-1 / block-20
variance ratio and by the autocorrelation of the per-session difference series.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import polars as pl

import fcommon as C

AL = C.AL


@lru_cache(maxsize=32)
def W(n: int, block: int) -> np.ndarray:
    return AL.weights_from(AL.block_draws(n, block), n)


def per_session(df: pl.DataFrame, sessions: list[str], col: str = 'r') -> tuple[np.ndarray, np.ndarray]:
    idx = {d: i for i, d in enumerate(sessions)}
    n = len(sessions)
    S, N = np.zeros(n), np.zeros(n)
    if df.height:
        g = df.group_by('day').agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
        for d, s, k in g.iter_rows():
            i = idx.get(d)
            if i is None:
                raise RuntimeError(f'a trade entered on {d}, outside the session list')
            S[i] += s
            N[i] += k
    return S, N


def _boot(Sw, Nw, So, No, block):
    n = Sw.size
    Wb = W(n, block)
    with np.errstate(divide='ignore', invalid='ignore'):
        a = (Wb @ Sw) / (Wb @ Nw)
        b = (Wb @ So) / (Wb @ No)
    return a - b


def acf_neff(x: np.ndarray) -> float:
    n = x.size
    if n < 3:
        return float('nan')
    out = AL.session_stats(x, np.ones(n), blocks=())
    return out.get('n_eff_acf', float('nan'))


def delta(with_df: pl.DataFrame, without_df: pl.DataFrame, sessions: list[str], col: str = 'r', full: bool = True) -> dict:
    """Δ, its block-20 interval and effective N; with full=True also each arm's session_stats (blocks 1, 5, 20)"""
    n = len(sessions)
    Sw, Nw = per_session(with_df, sessions, col)
    So, No = per_session(without_df, sessions, col)
    out = dict(sessions=n, first=sessions[0] if n else None, last=sessions[-1] if n else None,
               trades_with=int(Nw.sum()), trades_without=int(No.sum()),
               sessions_with=int((Nw > 0).sum()), sessions_without=int((No > 0).sum()))
    if Nw.sum() == 0 or No.sum() == 0:
        out.update(mean_with=None, mean_without=None, delta=None, ci=(float('nan'), float('nan')))
        return out
    mw, mo = Sw.sum() / Nw.sum(), So.sum() / No.sum()
    out.update(mean_with=float(mw), mean_without=float(mo), delta=float(mw - mo))
    if n < 60:
        out.update(ci=(float('nan'), float('nan')), n_eff_block20=float('nan'), n_eff_acf=float('nan'), note='under 60 sessions: no interval')
        return out
    d20 = _boot(Sw, Nw, So, No, 20)
    out['ci'] = AL.pct_ci(d20)
    if full:
        d1 = _boot(Sw, Nw, So, No, 1)
        v1, v20 = np.nanvar(d1[np.isfinite(d1)]), np.nanvar(d20[np.isfinite(d20)])
        out['n_eff_block20'] = float(n * v1 / v20) if v20 > 0 else float('nan')
        ok = No > 0
        diff = Sw[ok] - (Nw[ok] / No[ok]) * So[ok]
        out['n_eff_acf'] = acf_neff(diff)
        out['arm_with'] = clean(AL.session_stats(Sw, Nw))
        out['arm_without'] = clean(AL.session_stats(So, No))
    return out


def clean(d: dict) -> dict:
    o = {}
    for k, v in d.items():
        if isinstance(v, tuple):
            o[k] = [None if not math.isfinite(x) else x for x in v]
        elif isinstance(v, float) and not math.isfinite(v):
            o[k] = None
        else:
            o[k] = v
    return o


def passes(res: dict) -> bool:
    c = res.get('ci')
    return bool(res.get('delta') is not None and res['delta'] > 0 and c and c[0] is not None and math.isfinite(c[0]) and c[0] > 0)
