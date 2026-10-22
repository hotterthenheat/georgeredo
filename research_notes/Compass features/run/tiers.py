"""
tiers.py — the liquidity tiers (prereg 2.7), point in time, monthly: for each name and calendar month, on the 20 full
sessions before the month's first session, from the option EOD files: spread = the median of (ask − bid) ÷ mid at the
closing quote over every contract with a standing quote, 1–60 DTE, |x| ≤ 0.5 (pooled over the 20 sessions); volume = the
median over the 20 sessions of the day's total option volume. Tier 1: volume ≥ 900,000 and spread ≤ 5%; Tier 3: volume
< 400,000 or spread > 10%; Tier 2 otherwise; Tier U when the 20 sessions are not all on disk.

Reads build_eod's pass-1 inputs ($SP/features_work/eod/<name>/days.parquet, spreads.pkl). Writes
$SP/features_work/tiers/<name>.parquet.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402


def build(name: str) -> pl.DataFrame:
    C.guard_ticker(name)
    od = C.WORK / 'eod' / name
    rows = []
    vol, spreads = {}, {}
    if (od / 'days.parquet').exists():
        vol = {r['day']: r['total_vol'] for r in pl.read_parquet(od / 'days.parquet').iter_rows(named=True)}
        with open(od / 'spreads.pkl', 'rb') as fh:
            spreads = pickle.load(fh)
    s = C.sessions()
    import bisect
    for mo in C.MONTHS:
        i = bisect.bisect_left(s, mo + '-01')
        win = s[max(0, i - 20):i]
        if len(win) < 20 or any(d not in vol for d in win):
            rows.append(dict(name=name, month=mo, tier='U', volume=None, spread=None, sessions=sum(d in vol for d in win)))
            continue
        v = float(np.median([vol[d] for d in win]))
        sp = np.concatenate([spreads.get(d, np.array([], np.float32)) for d in win])
        sp = sp[np.isfinite(sp)]
        spr = float(np.median(sp)) if sp.size else float('nan')
        if not np.isfinite(spr):
            t = 'U'
        elif v >= 900_000 and spr <= 0.05:
            t = '1'
        elif v < 400_000 or spr > 0.10:
            t = '3'
        else:
            t = '2'
        rows.append(dict(name=name, month=mo, tier=t, volume=v, spread=spr, sessions=20))
    return pl.DataFrame(rows, schema={'name': pl.String, 'month': pl.String, 'tier': pl.String, 'volume': pl.Float64,
                                      'spread': pl.Float64, 'sessions': pl.Int64})


def table(names) -> dict[tuple[str, str], str]:
    out = {}
    for nm in names:
        p = C.WORK / 'tiers' / f'{nm}.parquet'
        C.write_parquet(build(nm), p)          # always rebuilt from the EOD inputs on disk (cheap)
        for r in pl.read_parquet(p).iter_rows(named=True):
            out[(nm, r['month'])] = r['tier']
    return out


if __name__ == '__main__':
    C.set_split('hold' if '--hold' in sys.argv else 'expl')
    for nm in [a for a in sys.argv[1:] if not a.startswith('--')]:
        df = build(nm)
        C.write_parquet(df, C.WORK / 'tiers' / f'{nm}.parquet')
        print(nm, df.group_by('tier').len().sort('tier').rows())
