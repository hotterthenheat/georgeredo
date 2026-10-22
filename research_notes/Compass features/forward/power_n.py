"""
power_n.py — N for the forward pass rule (FORWARD_RULE.md). Reads ONLY the holdout table Phase A already built and both
holdout reads already used ($SP/features_work/hold/trades_with_inputs.parquet, the table behind out/holdout.json and
out/phase_b_holdout.json); computes no new feature, threshold or comparison: each model is the committed function
(screen.py f_V1 / f_X3 / f_VN1, phase_b.py variants BV1b / BX3e / BC3) on the holdout's base trades RESTRICTED to the
forward set (0DTE, SPY + QQQ + SPXW), and the statistic is stats.py's (per-trade mean with − per-trade mean without, sums
over sessions; the 20-session moving-block bootstrap of audit_lib, 2,000 draws, seed 20261022).

Per model and per composition (A: the holdout sessions whose month is held out, from 2022-11-11, where all three names
are holdout — the forward composition; B: every holdout session of the restricted span, mostly QQQ alone):
  δ        the statistic on the series (the holdout effect for planning);
  σ_LR     per session: max of (i) the block-20 bootstrap SE of δ × √n and (ii) the linearised session contribution z_s
           (z_s = (Sw − m_w Nw)/N̄w − (So − m_o No)/N̄o, so δ̂ − δ ≈ mean z) by 20-session block means: √(20 · var(block means));
  N0       ⌈((1.96 + 0.8416) σ_LR / δ)²⌉, floor 60 (stats.py prints no interval under 60 sessions);
  power    the share of 2,000 outer draws (moving blocks of 20 from the series, cut to N; seed 20261023) whose own block-20
           interval (audit_lib.block_draws(N, 20), the rule's fixed seed) has a lower end > 0 and Δ > 0;
  N        N0 raised in steps of 5% (at least 5 sessions) until power ≥ 0.80.
The model's N is the larger of compositions A and B.

    POLARS_MAX_THREADS=1 python3 -I power_n.py  → power_n.json beside this file
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'run'))
import fcommon as C  # noqa: E402
import stats as ST  # noqa: E402
import screen as SC  # noqa: E402
import phase_b as PB  # noqa: E402

AL = C.AL
FORWARD_NAMES = ('SPY', 'QQQ', 'SPXW')
Z = 1.96 + 0.8416212335729143
FLOOR = 60
BLOCK = 20
OUTER_SEED = 20261023
OUTER_B = 2000
TARGET = 0.80
MODELS = ('V1', 'X3', 'VN1', 'BV1b', 'BX3e', 'BC3')


def arms_of(T: pl.DataFrame) -> dict:
    V = {vid: fn for vid, _f, _d, fn in PB.variants(T)}
    return {'V1': lambda: SC.f_V1(T), 'X3': lambda: SC.f_X3(T), 'VN1': lambda: SC.f_VN1(T),
            'BV1b': V['BV1b'], 'BX3e': V['BX3e'], 'BC3': V['BC3']}


def series(w, wo, sess):
    Sw, Nw = ST.per_session(w, sess)
    So, No = ST.per_session(wo, sess)
    return Sw, Nw, So, No


def stat(Sw, Nw, So, No):
    return Sw.sum() / Nw.sum() - So.sum() / No.sum()


def sigma_lr(Sw, Nw, So, No):
    n = Sw.size
    d20 = ST._boot(Sw, Nw, So, No, BLOCK)
    se = float(np.nanstd(d20[np.isfinite(d20)]))
    s_boot = se * math.sqrt(n)
    mw, mo = Sw.sum() / Nw.sum(), So.sum() / No.sum()
    z = (Sw - mw * Nw) / Nw.mean() - (So - mo * No) / No.mean()
    k = n // BLOCK
    bm = z[: k * BLOCK].reshape(k, BLOCK).mean(axis=1)
    s_blk = float(math.sqrt(BLOCK * bm.var(ddof=1))) if k >= 2 else float('nan')
    return max(s_boot, s_blk), s_boot, s_blk, se


def power(Sw, Nw, So, No, N):
    """outer: moving blocks of 20 from the holdout series cut to N; inner: the rule's own interval"""
    n = Sw.size
    rng = np.random.default_rng(OUTER_SEED + N)
    k = int(math.ceil(N / BLOCK))
    starts = rng.integers(0, n - BLOCK + 1, (OUTER_B, k))
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(OUTER_B, k * BLOCK)[:, :N]
    Wi = AL.weights_from(AL.block_draws(N, BLOCK), N)                 # 2000 × N, the rule's fixed draw
    A = [x[idx] for x in (Sw, Nw, So, No)]                              # each OUTER_B × N
    with np.errstate(divide='ignore', invalid='ignore'):
        point = A[0].sum(1) / A[1].sum(1) - A[2].sum(1) / A[3].sum(1)
        inner = (Wi @ A[0].T) / (Wi @ A[1].T) - (Wi @ A[2].T) / (Wi @ A[3].T)   # 2000 inner × OUTER_B
    lo = np.array([AL.pct_ci(inner[:, j])[0] for j in range(OUTER_B)])
    ok = np.isfinite(point) & np.isfinite(lo) & (point > 0) & (lo > 0)
    return float(ok.mean())


def plan(Sw, Nw, So, No):
    n = Sw.size
    d = float(stat(Sw, Nw, So, No))
    s, s_boot, s_blk, se = sigma_lr(Sw, Nw, So, No)
    out = dict(sessions=n, sessions_traded=int((No > 0).sum()), trades_with=int(Nw.sum()), trades_without=int(No.sum()),
               mean_with=float(Sw.sum() / Nw.sum()), mean_without=float(So.sum() / No.sum()), delta=d,
               se_boot20=se, sigma_lr=s, sigma_lr_boot=s_boot, sigma_lr_blockmeans=s_blk)
    if not d > 0:
        out.update(N0=None, N=None, note='δ ≤ 0 on this composition: no finite N')
        return out
    N0 = max(FLOOR, int(math.ceil((Z * s / d) ** 2)))
    out['N0_formula'] = int(math.ceil((Z * s / d) ** 2))
    out['N0'] = N0
    N, tried = N0, []
    while True:
        p = power(Sw, Nw, So, No, N)
        tried.append([N, p])
        print(f'    N {N}: power {p:.3f}', flush=True)
        if p >= TARGET or N > 20000:
            break
        N = N + max(5, int(math.ceil(0.05 * N)))
    out.update(power_at_N0=tried[0][1], N=N, power_at_N=tried[-1][1], tried=tried)
    return out


def main():
    C.set_split('hold')
    T = pl.read_parquet(C.WORK / 'hold' / 'trades_with_inputs.parquet')
    assert T['tid'].n_unique() == T.height
    T = T.filter((pl.col('eb') == '0DTE') & pl.col('name').is_in(list(FORWARD_NAMES)))
    sess_all = SC.split_sessions('hold')
    A = arms_of(T)
    first3 = max(T.filter(pl.col('name') == nm)['day'].min() for nm in FORWARD_NAMES)
    res = dict(source='features_work/hold/trades_with_inputs.parquet (Phase A corrected holdout table)', forward_names=FORWARD_NAMES,
               bucket='0DTE', z=Z, floor=FLOOR, block=BLOCK, boot_seed=AL.SEED, boot_n=AL.BOOT_N, outer_seed=OUTER_SEED,
               outer_draws=OUTER_B, target_power=TARGET, first_all_three=first3, models={})
    for mid in MODELS:
        w, wo = A[mid]()
        a, b = wo['day'].min(), wo['day'].max()
        sessB = [d for d in sess_all if a <= d <= b]
        sessA = [d for d in sessB if C.held_month(d) and d >= first3]
        r = dict(span=[a, b])
        for lab, sess in (('A_forward_composition', sessA), ('B_all_restricted', sessB)):
            if not w.height or not wo.height:
                continue
            wa, woa = w.filter(pl.col('day').is_in(sess)), wo.filter(pl.col('day').is_in(sess))
            print(mid, lab, len(sess), flush=True)
            r[lab] = plan(*series(wa, woa, sess))
        Ns = [r[k]['N'] for k in ('A_forward_composition', 'B_all_restricted') if k in r and r[k].get('N')]
        r['N'] = max(Ns) if Ns else None
        res['models'][mid] = r
        print(mid, 'N =', r['N'], flush=True)
    (HERE / 'power_n.json').write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
