"""
power_h5_h6.py — reproduces the N of PREREG_H5.md and PREREG_H6.md (committed in e114e30) from the committed inputs they
name; writes power_h5_h6.json beside it. It reads no H5 or H6 trade: H5's inputs are SPXW_REPORT.md's published gap
intervals (commit 6bb230e, section 9, transcribed below and checked against the report's text), H6's are S17's committed
per-cycle rows (cycles.parquet at 5e7e1bd, read with `git show`).

    python3 -I "research_notes/Edge search/H5_H6/power_h5_h6.py"
"""
from __future__ import annotations

import io
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

Z = 1.959964 + 0.841621                     # two-sided 5 % and 80 % power
REPORT = REPO / 'research_notes' / 'Compass phase 3' / 'spxw_prereg' / 'SPXW_REPORT.md'
# SPXW_REPORT.md section 9, "The gaps, on the sessions all three share", SPY rows: gap in (ext − real) bps [block-20 CI], n
H5_GAPS = {
    ('development', '15:30'): (1.82, 1.40, 2.28, 530, '| development | 15:30 | SPY | 530 | 0.986 | 0.866 | +0.120 | [+0.093, +0.155] | +1.82 | [+1.40, +2.28] |'),
    ('development', '15:58'): (3.01, 2.38, 3.71, 530, '| development | 15:58 | SPY | 530 | 1.339 | 0.733 | +0.606 | [+0.505, +0.728] | +3.01 | [+2.38, +3.71] |'),
    ('selection', '15:30'): (1.97, 1.25, 2.72, 441, '| selection | 15:30 | SPY | 441 | 1.050 | 0.917 | +0.133 | [+0.081, +0.192] | +1.97 | [+1.25, +2.72] |'),
    ('selection', '15:58'): (4.09, 3.20, 5.13, 441, '| selection | 15:58 | SPY | 441 | 1.592 | 0.791 | +0.801 | [+0.634, +1.007] | +4.09 | [+3.20, +5.13] |'),
}
H5_DELTA_BPS = 1.0                           # the ASSUMED effect after costs (PREREG_H5.md section 6, item 3)
H5_SPY_REF = 775.0                           # bps → dollars only
H5_FEES = 40 * 0.68748 + 2 * 1.27748 + 2 * (1.27748 + 1.18748) / 2
H5_SPREAD_BPS = 2 * (0.325 + 0.325)          # 2 (w_SPY + w_SPXW), each 0.2–0.45 bps, central 0.325
S17_COMMIT, S17_PATH = '5e7e1bd', 'research/compass/results/v1/s17_put_write/cycles.parquet'
H6_HOLD_DAYS, H6_EXIT_COST = 21.0, 3.0


def n_of(sigma: float, delta: float, floor: int) -> int:
    return max(floor, math.ceil((Z * sigma / delta) ** 2))


def h5() -> dict:
    text = REPORT.read_text()
    sd = {}
    for k, (m, lo, hi, n, line) in H5_GAPS.items():
        if line not in text:
            raise SystemExit(f'SPXW_REPORT.md no longer carries the row transcribed for {k}')
        sd[k] = (hi - lo) / (2 * 1.959964) * math.sqrt(n)
    per = {}
    for p in ('development', 'selection'):
        a, b = sd[(p, '15:30')], sd[(p, '15:58')]
        per[p] = {'sd_1530': a, 'sd_1558': b, 'sigma_rho0': math.hypot(a, b), 'sigma_rho05': math.sqrt(a * a + b * b - a * b),
                  'mapped_mid_bps': H5_GAPS[(p, '15:30')][0] - H5_GAPS[(p, '15:58')][0]}
    sigma = max(per[p]['sigma_rho0'] for p in per)
    costs = H5_SPREAD_BPS + H5_FEES / (1000 * H5_SPY_REF) * 1e4
    for p in per:
        per[p]['mapped_after_costs_bps'] = per[p]['mapped_mid_bps'] - costs
        per[p]['mapped_after_costs_usd'] = per[p]['mapped_after_costs_bps'] * 1e-4 * 1000 * H5_SPY_REF
    grid = {f'{d}': {f'{s:.2f}': n_of(s, d, 60) for s in (8.0, per['development']['sigma_rho0'], 11.2, sigma, 16.0)} for d in (0.5, 1.0, 2.0)}
    best = (H5_GAPS[('development', '15:30')][0] + H5_GAPS[('selection', '15:30')][0]) / 2 - costs
    return {'sigma_bps': sigma, 'delta_bps_assumed': H5_DELTA_BPS, 'N': n_of(sigma, H5_DELTA_BPS, 60), 'periods': per, 'costs_bps': costs,
            'fees_usd': H5_FEES, 'grid': grid, 'best_case_bps': best, 'best_case_N': n_of(sigma, best, 60)}


def h6() -> dict:
    raw = subprocess.run(['git', '-C', str(REPO), 'show', f'{S17_COMMIT}:{S17_PATH}'], capture_output=True, check=True).stdout
    d = pl.read_parquet(io.BytesIO(raw)).filter((pl.col('structure') == 'put_spread_30_15') & (pl.col('adverse') == 0.0))
    hold = float(d.select((pl.col('exit') - pl.col('entry')).dt.total_days().mean()).item())
    j = (d.filter(pl.col('root') == 'SPY').select('entry', pl.col('ret').alias('s'))
         .join(d.filter(pl.col('root') == 'QQQ').select('entry', pl.col('ret').alias('q')), on='entry').sort('entry'))
    m = ((j['s'] + j['q']) / 2).to_numpy()
    n = m.size
    mu, sd = float(m.mean()), float(m.std(ddof=1))
    se3 = float(m[AL.block_draws(n, 3)].mean(1).std()) * math.sqrt(n)
    sig_m = max(sd, se3)
    cap = float(d.filter(pl.col('year') >= 2025)['capital'].mean())
    f = H6_HOLD_DAYS / hold
    delta = f * mu - H6_EXIT_COST / cap
    sigma = math.sqrt(f) * sig_m
    N = n_of(sigma, delta, 12)
    return {'cycles_common': n, 'mean_ret': mu, 'sd_ret': sd, 'block3_se_sqrt_n': se3, 'corr_spy_qqq': float(np.corrcoef(j['s'], j['q'])[0, 1]),
            'hold_days_s17': hold, 'f': f, 'capital_2025_2026': cap, 'delta_ret': delta, 'sigma_ret': sigma, 'N_months': N, 'N_spreads': 2 * N,
            'years': N / 12, 'delta_usd': delta * cap, 'sigma_usd': sigma * cap,
            'sensitivity': {f'{x}': n_of(sigma, delta * x, 12) for x in (0.5, 0.75, 1.0, 1.5)}, 'unscaled_N': n_of(sig_m, mu, 12)}


def main() -> int:
    out = {'H5': h5(), 'H6': h6()}
    (HERE / 'power_h5_h6.json').write_text(json.dumps(out, indent=1))
    print(f'H5 N = {out["H5"]["N"]} sessions (sigma {out["H5"]["sigma_bps"]:.3f} bps, delta {H5_DELTA_BPS} bp assumed)')
    print(f'H6 N = {out["H6"]["N_months"]} months ({out["H6"]["N_spreads"]} spreads, {out["H6"]["years"]:.1f} years)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
