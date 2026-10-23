"""
select_weeks_v1.py — RULEBOOK_v1.md §4, run as written: lists the eligible Monday–Friday weeks (file presence only), reads
SPY's weekly return (the only market figure read), and draws the up / flat / down weeks with seed 2026102310.
Writes out_v1/weeks.json and prints the counts. Files only.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass scanner'))
import scanner_lib as S  # noqa: E402

OUT = HERE / 'out_v1'
OUT.mkdir(exist_ok=True)
SEED = 2026102310
A, B = '2024-05-01', '2026-10-09'
EXCL = {'2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16'}
T = S.THETA


def has_eod(name: str, d: str) -> bool:
    return any(a <= d <= b for a, b, _ in S.eod_files(name))


def day_inputs_ok(d: str) -> str | None:
    for nm in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        if not (T / 'data_full' / 'chains' / nm / f'{d}.parquet').exists():
            return f'chain {nm}'
    for nm in ('SPY', 'QQQ', 'IWM'):
        if not (T / 'data' / 'underlying' / nm / f'{d}.parquet').exists():
            return f'bars {nm}'
    if not (T / 'data' / 'index' / 'SPX' / f'{d}.parquet').exists():
        return 'SPX prints'
    for nm in ('SPY', 'QQQ', 'IWM', 'SPX'):
        if not (S.OI_DIR / nm / f'{d}.parquet').exists():
            return f'UW chain {nm}'
    p = S.prev_tday(d)
    for nm in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        if p is None or not has_eod(nm, p):
            return f'EOD {nm}'
    return None


def hist_ok(d: str) -> str | None:
    td = S.trading_days()
    i = td.index(d)
    for x in td[i - 60:i]:
        for nm in ('SPY', 'QQQ', 'IWM'):
            if not (T / 'data' / 'underlying' / nm / f'{x}.parquet').exists():
                return f'history bars {nm}'
        if not (T / 'data' / 'index' / 'SPX' / f'{x}.parquet').exists():
            return 'history SPX prints'
    return None


def spy_close(d: str) -> float:
    c = S.day_bars('SPY', d)[3]
    return float(c[np.isfinite(c)][-1])


def main():
    tset = S.tday_set()
    mon = dt.date.fromisoformat(A)
    mon -= dt.timedelta(days=mon.weekday())
    drops, elig = {}, []
    while mon.isoformat() <= B:
        days = [(mon + dt.timedelta(days=k)).isoformat() for k in range(5)]
        why = None
        if days[0] < A or days[4] > B:
            why = 'outside the span'
        elif not all(x in tset for x in days):
            why = 'not five trading days'
        elif any(x in S.HALF_DAYS for x in days):
            why = 'a half day'
        elif any(S.held_month(x) for x in days):
            why = 'held-out month'
        elif any(x in EXCL for x in days):
            why = '2026-10-12..16'
        else:
            for x in days:
                why = day_inputs_ok(x)
                if why:
                    break
            if why is None:
                why = hist_ok(days[0])
        if why is None:
            prev = S.prev_tday(days[0])
            if S.day_bars('SPY', days[4]) is None or prev is None or S.day_bars('SPY', prev) is None:
                why = 'weekly return undefined'
        if why:
            drops[why] = drops.get(why, 0) + 1
        else:
            elig.append(dict(days=days, prev=S.prev_tday(days[0])))
        mon += dt.timedelta(days=7)
    for w in elig:
        w['ret'] = spy_close(w['days'][4]) / spy_close(w['prev']) - 1
    elig.sort(key=lambda w: w['days'][0])
    rng = np.random.default_rng(SEED)
    cats = {'up': [w for w in elig if w['ret'] > 0.015], 'flat': [w for w in elig if abs(w['ret']) < 0.003],
            'down': [w for w in elig if w['ret'] < -0.015]}
    pick = {}
    for k in ('up', 'flat', 'down'):
        L = cats[k]
        if not L:
            pick[k] = None
            continue
        pick[k] = L[int(rng.integers(len(L)))]
    out = dict(seed=SEED, eligible=len(elig), drops=drops, counts={k: len(v) for k, v in cats.items()},
               eligible_weeks=[(w['days'][0], round(w['ret'], 6)) for w in elig],
               picks={k: (None if v is None else dict(days=v['days'], prev=v['prev'], ret=v['ret'])) for k, v in pick.items()})
    (OUT / 'weeks.json').write_text(json.dumps(out, indent=1))
    print('eligible', len(elig), 'drops', drops, 'counts', out['counts'])
    for k, v in pick.items():
        print(k, None if v is None else (v['days'][0], v['days'][4], f"{100 * v['ret']:+.2f}%"))


if __name__ == '__main__':
    main()
