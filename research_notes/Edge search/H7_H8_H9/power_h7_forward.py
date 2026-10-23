#!/usr/bin/env python3
"""
power_h7_forward.py — the N of FORWARD_RULE_H7.md (committed with it, before any forward session of H7 is read).

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B "research_notes/Edge search/H7_H8_H9/power_h7_forward.py"

Reads one committed file: out/h7_trades.csv (the pre-registered test's trades, commit 6c94bb8; sha256 checked below). Nothing
after 2026-10-22 is read. Per name (SPY, QQQ):
  - each included trade's net $ at 1x as a share of its position, in bp: net_1x / (100 x C_prev) x 1e4 (scale-free, so N does
    not depend on the price level of the years ahead);
  - sigma = the sample standard deviation of those bp (ddof 1);
  - mu = the ASSUMED forward effect = HALF the test's mean bp (the winner's-curse shrink; FORWARD_RULE_H7.md section 3 says why
    this and not the published figures, which are printed beside it);
  - N0 = ceil(((z_.975 + z_.80) x sigma / mu)^2), trades;
  - the simulated power of the rule's own verdict at N (FORWARD_RULE_H7.md section 4): 2,000 outer draws, each N trades drawn iid
    from the name's test trades re-centred to mu (seed 20261023 + N), placed on a forward session calendar that starts on
    2026-10-23 with the first statement on its 4th session (2026-10-28) and the test's own gaps between statements (weekdays,
    cycled); each draw judged by the 20-session moving-block bootstrap over those sessions (audit_lib.block_draws(n, 20, B=2000,
    seed=20261023), a draw with no trade counting as 0) — PASS when the mean > 0 and the 2.5th percentile > 0. If the power at N0 is
    under 0.80, N is raised in steps of 5 % (at least 5 trades) until it is not. N is never set below N0.
Writes power_h7_forward.json beside it and prints the N.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

TRADES = HERE / 'out' / 'h7_trades.csv'
NAMES = ('SPY', 'QQQ')
Z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(0.80)
SHRINK = 0.5
BLOCK, BOOT_N, SEED = 20, 2000, 20261023
OUTER = 2000
FIRST_POS = int(np.busday_count(np.datetime64('2026-10-23'), np.datetime64('2026-10-28')))     # 3: the 4th session
TARGET = 0.80
CLOSE_2026_10_22 = {'SPY': 763.96, 'QQQ': 704.47}      # PREREG_H7.md section 5: bp -> $ for the reader only
# for the reader only (FORWARD_RULE_H7.md section 3): the published close-to-release figures on the S&P 500 index, gross
# (as PREREG_H7.md section 1 summarises them); 'mu_bp_net' takes 0.2 bp off for the $1.50 of costs at today's prices
PUBLISHED_BP = {'Song 2016-2023 (overnight gap +0.19 % and open-to-release -0.03 %)': 16.0,
                'Hu, Pan, Wang & Zhu 2012-2018 (close to release - 5 min)': 3.96,
                'Lucca & Moench 1994-2011 (24 h before)': 49.0}


def n0(sigma: float, mu: float) -> int:
    return int(math.ceil((Z * sigma / mu) ** 2))


def positions(gaps: np.ndarray, n: int) -> np.ndarray:
    pos = [FIRST_POS]
    for i in range(1, n):
        pos.append(pos[-1] + int(gaps[(i - 1) % gaps.size]))
    return np.asarray(pos, int)


def power(x_bp: np.ndarray, mu: float, gaps: np.ndarray, n: int) -> float:
    xc = x_bp - x_bp.mean() + mu
    pos = positions(gaps, n)
    n_ses = int(pos[-1]) + 1
    idx = AL.block_draws(n_ses, BLOCK, B=BOOT_N, seed=SEED)
    Wt = np.empty((BOOT_N, n))
    for b in range(BOOT_N):
        Wt[b] = np.bincount(idx[b], minlength=n_ses)[pos]
    del idx
    cnt = np.maximum(Wt.sum(1), 1.0)
    rng = np.random.default_rng(SEED + n)
    X = rng.choice(xc, size=(OUTER, n), replace=True)
    means = (Wt @ X.T) / cnt[:, None]                    # inner draws x outer draws
    lo = np.percentile(means, 2.5, axis=0)
    ok = (X.mean(1) > 0) & (lo > 0)
    return float(ok.mean())


def main() -> int:
    raw = TRADES.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    t = pl.read_csv(TRADES).filter(pl.col('net_1x').is_not_null())
    out = {'trades_file': str(TRADES.relative_to(REPO)), 'trades_sha256': sha, 'z_sum': Z, 'shrink': SHRINK, 'block': BLOCK,
           'boot_n': BOOT_N, 'seed': SEED, 'outer': OUTER, 'first_position': FIRST_POS, 'names': {}}
    for nm in NAMES:
        u = t.filter(pl.col('name') == nm).sort('A')
        x = (u['net_1x'] / (100.0 * u['C_prev']) * 1e4).to_numpy()
        a = np.array(u['A'].to_list(), dtype='datetime64[D]')
        gaps = np.busday_count(a[:-1], a[1:])
        mean, sd = float(x.mean()), float(x.std(ddof=1))
        mu = SHRINK * mean
        N0 = n0(sd, mu)
        N, p = N0, power(x, mu, gaps, N0)
        steps = [(N0, p)]
        while p < TARGET:
            N = max(N + 5, int(math.ceil(N * 1.05)))
            p = power(x, mu, gaps, N)
            steps.append((N, p))
        o = {'trades': int(x.size), 'span': [str(a[0]), str(a[-1])], 'mean_bp': mean, 'sd_bp': sd, 'mean_usd': float(u['net_1x'].mean()),
             'sd_usd': float(u['net_1x'].std()), 'lag1_corr': float(np.corrcoef(x[:-1], x[1:])[0, 1]),
             'gap_weekdays': {'min': int(gaps.min()), 'max': int(gaps.max()), 'mean': float(gaps.mean())},
             'mu_bp': mu, 'N0': N0, 'power_steps': steps, 'N': N, 'power_at_N': p, 'years_at_8_a_year': N / 8.0,
             'forward_sessions_at_N': int(positions(gaps, N)[-1]) + 1,
             'mu_usd_at_2026_10_22_close': mu * 1e-4 * 100 * CLOSE_2026_10_22[nm],
             'for_reading': {f'{k}': {'mu_bp_net': v - 0.2, 'N_formula': n0(sd, v - 0.2)} for k, v in PUBLISHED_BP.items()} |
                            {'the test mean, unshrunk': {'mu_bp_net': mean, 'N_formula': n0(sd, mean)}}}
        out['names'][nm] = o
        print(f'{nm}: {x.size} test trades, mean {mean:.2f} bp, sd {sd:.2f} bp; mu = {mu:.2f} bp; N0 {N0} (power {steps[0][1]:.3f}); '
              f'N {N} trades (power {p:.3f}), {N / 8:.1f} years at 8 a year')
    (HERE / 'power_h7_forward.json').write_text(json.dumps(out, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
