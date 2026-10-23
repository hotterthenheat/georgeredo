#!/usr/bin/env python3
"""
power_h4.py — the a-priori power figure in PREREG_H4.md section 6, computed before the prereg was committed.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B power_h4.py

Reads only the exploration span (signal sessions before 2025-10-13). It computes, per name, the root-mean-square of the
last-half-hour return x = C / E − 1 (E = the 15:30 bar's open, C = the official close: ThetaData EOD as in run_h1.py). The RMS
is sqrt(mean(x²)): it does not depend on any sign, so it is the same for the long, the short and the H4 position, and no mean
of x — nor of any signed quantity — is computed or printed. sqrt(mean(x²)) ≥ the de-meaned sd, so the MDE below is conservative.
MDE ($ a trade, 100 shares, 80 % power, two-sided 5 %) = (1.96 + 0.84) × RMS × P / sqrt(n), with P = the name's official close
on 2025-10-10 (the last exploration session) and n = 257 (the test span's 259 sessions less its two half days).
"""
import glob
import math
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
BARS = SP / 'theta' / 'data' / 'underlying'
H1 = REPO / 'research_notes' / 'Compass H1'
EOD_FILES = ([str(H1 / 'data' / 'stock_eod_2012_2018.parquet')] + sorted(glob.glob(str(SP / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet')))
             + sorted(glob.glob(str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet'))))
FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}
LAST = '2025-10-10'
N_TEST = 257

e = pl.concat([pl.scan_parquet(f).filter(pl.col('symbol').is_in(['SPY', 'QQQ'])).select('symbol', 'created', 'close').collect() for f in EOD_FILES], how='diagonal_relaxed')
e = e.with_columns(pl.col('created').dt.convert_time_zone('America/New_York').dt.strftime('%Y-%m-%d').alias('day'))
E = {}
for s, d, c in e.select('symbol', 'day', 'close').iter_rows():
    E.setdefault((s, d), set()).add(c)
for nm in ('SPY', 'QQQ'):
    xs = {'all': [], 'last3y': []}
    for f in sorted(glob.glob(str(BARS / nm / '*.parquet'))):
        d = Path(f).name[:10]
        if not (FIRST[nm] <= d <= LAST):
            continue
        c = E.get((nm, d))
        if not c or len(c) > 1:
            continue
        t = pl.read_parquet(f).filter(pl.col('timestamp').dt.strftime('%H:%M') == '15:30')
        if t.height == 0 or t['open'][0] is None or not math.isfinite(t['open'][0]):
            continue
        x = next(iter(c)) / t['open'][0] - 1
        xs['all'].append(x)
        if d >= '2022-10-11':
            xs['last3y'].append(x)
    P = next(iter(E[(nm, LAST)]))
    for k, v in xs.items():
        rms = math.sqrt(sum(a * a for a in v) / len(v))
        print(f'{nm} {k:7s} n {len(v):5d}  RMS {rms * 1e4:6.1f} bp  = ${rms * P * 100:6.2f} a 100-share trade at P {P:.2f}; '
              f'SE over {N_TEST} trades ${rms * P * 100 / math.sqrt(N_TEST):5.2f}; MDE (80 %, 5 % two-sided) ${2.80 * rms * P * 100 / math.sqrt(N_TEST):5.2f}')
