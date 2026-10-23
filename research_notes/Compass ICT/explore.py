"""
explore.py — the EXPLORATION of PREREG_COMPASS_ICT.md (9d6c37e) as amended (Amendment 1, 9dbc0bf): v0, V1-V4 and the four
ablations on SPXW 0DTE 2022-05-13 -> 2026-10-09 minus the 28 held-out months, full sessions; the 9 forward sessions
2026-10-12 .. 10-22 apart. Reuses ict.py unchanged; only the HTF history's start is set per session (the preview's
convention: from the first session after the latest held-out month, never reading one). guard.py raises on any held-out
file. Neither holdout is read. Writes the trade and session tables (scratchpad and out/).

    python explore.py            # run (4 processes) and write the tables
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
import multiprocessing as mp
from pathlib import Path

os.environ.setdefault('POLARS_MAX_THREADS', '1')
import guard  # noqa: E402,F401  (must wrap polars before any read)
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

import ict  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

OUT = HERE / 'out'
BIG = ict.SP / 'compass_ict_explore'
SPAN = ('2022-05-13', '2026-10-09')
FORWARD = ('2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-19', '2026-10-20', '2026-10-21',
           '2026-10-22')
B_SESSIONS = 269                      # Amendment 1: full SPXW sessions in the 28 months, from file names only
STAGE = {'no HTF bias': 0, 'no sweep': 1, 'sweep without close-back': 2, 'no displacement + MSS': 3, 'no FVG': 4,
         'entry outside killzone': 5, 'no entry in window': 5, 'trade open': 6, 'session limit': 6, 'picker': 7}


def spxw_dates() -> list[str]:
    return sorted(p.stem for p in (ict.TH / 'data_full' / 'chains' / 'SPXW').glob('*.parquet'))


def sessions():
    """(run, dropped): exploration sessions run, and those not run with the reason"""
    run, dropped = [], []
    for d in spxw_dates():
        if not (SPAN[0] <= d <= SPAN[1]) or guard.held_out(d):
            continue
        if d in AL.NYSE_HALF_DAYS:
            dropped.append((d, 'half day'))
            continue
        p = ict.prev_day(d)
        if guard.held_out(p):
            dropped.append((d, f'prior session {p} held out'))
            continue
        run.append(d)
    return run, dropped


@lru_cache(maxsize=None)
def htf_start(d: str) -> str:
    """the first session of the contiguous readable run of SPX days ending the day before d"""
    s = ict.spx_days()
    i = s.index(d) - 1
    start = None
    while i >= 0 and not guard.held_out(s[i]):
        start = s[i]
        i -= 1
    return start or d


_orig_bias = ict.htf_bias


@lru_cache(maxsize=None)
def bias(d: str) -> int:
    ict.HTF_FROM = htf_start(d)
    return _orig_bias(d)


ict.htf_bias = bias                    # Day() looks htf_bias up in ict's namespace at call time


def flat(tr: dict, row: str) -> dict:
    s = tr['setup']
    z = s['zone']
    return dict(row=row, day=tr['day'], t=tr['t'], m=tr['m'], side=tr['side'], ext=tr['ext'], entry_u=tr['entry_u'],
                tp1=tr['tp1'], tp2=tr['tp2'], K=tr['K'], ask=tr['ask'], delta=tr['delta'], spread=tr['spread'],
                exit_m=tr['exit_m'], reason=tr['reason'], gross=tr['gross'], fees=tr['fees'], net=tr['net'], pct=tr['pct'],
                bp=tr['bp'], im=tr['im'], kz=tr['kz'], sweep_s=s['sweep'], disp_j=s['j'],
                zone_lo=None if z is None else z[0], zone_hi=None if z is None else z[1],
                legs=';'.join(f'{n}@{ex}:{px:.4f}:{w}' for n, ex, px, w in tr['legs']))


def one_day(d: str):
    T, S = [], []
    try:
        for row, P in ict.VARIANTS.items():
            tr, why, *_ = ict.run_day(d, P)
            T += [flat(t, row) for t in tr]
            stage = None
            if not tr:
                stage = max(why, key=lambda a: STAGE.get(a.split(':')[0], 9)) if why else 'no sweep'
            S.append(dict(row=row, day=d, n=len(tr), pct=float(sum(t['pct'] for t in tr)), net=float(sum(t['net'] for t in tr)),
                          stage=stage, why=json.dumps(why, sort_keys=True), bias=ict.htf_bias(d), htf_from=htf_start(d)))
    finally:
        ict.chain.cache_clear()
    return T, S


def run_all(days, procs=4):
    with mp.get_context('spawn').Pool(procs) as pool:   # spawn: never fork after polars' threads start
        res = pool.map(one_day, days, chunksize=4)
    T = [t for a, _ in res for t in a]
    S = [s for _, b in res for s in b]
    return pl.DataFrame(T, infer_schema_length=None), pl.DataFrame(S, infer_schema_length=None)


def main():
    print(guard.selftest())
    OUT.mkdir(exist_ok=True)
    BIG.mkdir(parents=True, exist_ok=True)
    run, dropped = sessions()
    print(f'exploration sessions run {len(run)} ({run[0]} .. {run[-1]}); not run {len(dropped)}')
    (OUT / 'explore_sessions.json').write_text(json.dumps(dict(run=run, dropped=dropped, forward=FORWARD), indent=0))
    for tag, days in (('explore', run), ('forward', list(FORWARD))):
        T, S = run_all(days)
        T.write_parquet(BIG / f'{tag}_trades.parquet')
        S.write_parquet(BIG / f'{tag}_sessions.parquet')
        T.write_csv(OUT / f'{tag}_trades.csv')
        print(tag, 'trades', T.height, 'session rows', S.height)


if __name__ == '__main__':
    main()
