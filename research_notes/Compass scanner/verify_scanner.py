"""
verify_scanner.py — prereg section 11: re-derive Compass scanner minutes from the raw Parquet files with separate
plain-loop code (no numpy, nothing imported from scanner_lib), and compare with the study's outputs.

python verify_scanner.py signal pick   -> out/verify_signal_pick.json
    a seeded sample of >= 30 signal minutes and >= 20 non-signal minutes of the signal check's Pick arrays: the window,
    RSI_1m, RSI_5m, VWAP, RVOL, swings, trend, BOS, MSS, direction, stretch, score, and the signed forward returns.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
THETA = SP / 'theta'
WORK = SP / 'scanner_work'
NAMES = ('SPY', 'QQQ', 'IWM')
HORIZONS = (5, 15, 30, 60)


def read_bars(name, day):
    p = THETA / 'data' / 'underlying' / name / f'{day}.parquet'
    if not p.exists():
        return []
    rows = pl.read_parquet(p).to_dicts()
    out = []
    for r in rows:
        ts = r['timestamp']
        stamp = ts.hour * 60 + ts.minute - 570
        if stamp < 0 or stamp > 389:
            continue
        vals = [r['open'], r['high'], r['low'], r['close']]
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in vals):
            continue
        out.append({'stamp': stamp, 'o': float(r['open']), 'h': float(r['high']), 'l': float(r['low']),
                    'c': float(r['close']), 'v': float(r['volume'] or 0)})
    out.sort(key=lambda b: b['stamp'])
    return out


def trading_days():
    return set(json.loads((WORK / 'spy_eod_dates.json').read_text()))


HOLIDAYS_2022 = set('''2022-01-17 2022-02-21 2022-04-15 2022-05-30 2022-06-20 2022-07-04 2022-09-05 2022-11-24 2022-12-26
2023-01-02 2023-01-16 2023-02-20 2023-04-07 2023-05-29 2023-06-19 2023-07-04 2023-09-04 2023-11-23 2023-12-25
2024-01-01 2024-01-15 2024-02-19 2024-03-29 2024-05-27 2024-06-19 2024-07-04 2024-09-02 2024-11-28 2024-12-25
2025-01-01 2025-01-09 2025-01-20 2025-02-17 2025-04-18 2025-05-26 2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25
2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03 2026-09-07'''.split())


def is_tday(day, eod):
    if day < '2022-01-01':
        return day in eod
    d = dt.date.fromisoformat(day)
    return d.weekday() < 5 and day not in HOLIDAYS_2022


def rsi(closes):
    if len(closes) < 15:
        return 50.0
    ch = [closes[i] - closes[i - 1] for i in range(len(closes) - 14, len(closes))]
    g = sum(max(x, 0.0) for x in ch) / 14.0
    l = sum(max(-x, 0.0) for x in ch) / 14.0
    if g == 0 and l == 0:
        return 50.0
    if l == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + g / l)


def minute_state(name, day, m, eod):
    """the scanner at minute m (bars through the one stamped m - 1), plain loops"""
    D = dt.date.fromisoformat(day)
    prior_days = []
    for j in (2, 1):
        x = (D - dt.timedelta(days=j)).isoformat()
        if is_tday(x, eod):
            prior_days.append(x)
    seq = []
    fives = []
    for x in prior_days:
        bs = read_bars(name, x)
        seq.extend(bs)
        buckets = {}
        for b in bs:
            buckets[b['stamp'] // 5] = b['c']            # the last present bar of the bucket wins (sorted by stamp)
        fives.extend(buckets[k] for k in sorted(buckets))
    today = read_bars(name, day)
    if not any(b['stamp'] == m - 1 for b in today):
        return None
    tb = [b for b in today if b['stamp'] <= m - 1]
    seq.extend(tb)
    if len(seq) < 30:
        return None
    buckets = {}
    for b in tb:
        if b['stamp'] // 5 * 5 + 4 <= m - 1:
            buckets[b['stamp'] // 5] = b['c']
    fives.extend(buckets[k] for k in sorted(buckets))
    pv = sum((b['h'] + b['l'] + b['c']) / 3.0 * b['v'] for b in tb)
    vv = sum(b['v'] for b in tb)
    if vv <= 0:
        return None
    vwap = pv / vv
    closes = [b['c'] for b in seq]
    c = closes[-1]
    r1 = rsi(closes)
    r5 = rsi(fives)
    n = len(seq)
    if n < 2:
        rvol = 1.0
    else:
        prev = [b['v'] for b in seq[max(0, n - 21):n - 1]]
        mv = sum(prev) / len(prev)
        rvol = seq[-1]['v'] / mv if mv > 0 else 1.0
    volx = n >= 2 and seq[-1]['v'] > seq[-2]['v']
    sh, sl = [], []
    for i in range(2, n - 2):
        if seq[i]['h'] >= max(seq[j]['h'] for j in range(i - 2, i + 3)):
            sh.append(seq[i]['h'])
        if seq[i]['l'] <= min(seq[j]['l'] for j in range(i - 2, i + 3)):
            sl.append(seq[i]['l'])
    h2 = sh[-1] if sh else None
    h1 = sh[-2] if len(sh) >= 2 else None
    l2 = sl[-1] if sl else None
    l1 = sl[-2] if len(sl) >= 2 else None
    HH = h1 is not None and h2 > h1
    LH = h1 is not None and h2 < h1
    HL = l1 is not None and l2 > l1
    LL = l1 is not None and l2 < l1
    up, down = HH and HL, LH and LL
    bos = (h2 is not None and c > h2) or (l2 is not None and c < l2)
    mss = (up and l2 is not None and c < l2) or (down and h2 is not None and c > h2)
    bull = c >= vwap and r1 >= 50
    aligned = (bull and up) or ((not bull) and down)
    pts = 0.0
    pts += 15 if ((r1 > 55) if bull else (r1 < 45)) else 0
    pts += 15 if ((r5 > 52) if bull else (r5 < 48)) else 0
    pts += 15 if ((c > vwap) if bull else (c < vwap)) else 0
    pts += 15 if rvol >= 1.5 else (8 if rvol >= 1.2 else 0)
    pts += 10 if volx else 0
    pts += 15 if aligned else 0
    pts += 10 if bos else 0
    pts += 5 if mss else 0
    st1 = abs(c - vwap) / vwap > 0.018
    st2 = (bull and r1 >= 82) or ((not bull) and r1 <= 18)
    st3 = True
    for b in seq[-3:]:
        rng = b['h'] - b['l']
        ratio = abs(b['c'] - b['o']) / rng if rng > 0 else 0.0
        if not ratio > 0.75:
            st3 = False
    if n < 3:
        st3 = False
    sw = l2 if bull else h2
    st4 = sw is not None and abs(c - sw) / c > 0.025
    score = 0.0 if (st1 or st2 or st3 or st4) else min(100.0, pts)
    fwd = {}
    for h in HORIZONS:
        f = [b for b in today if b['stamp'] == m - 1 + h]
        if m - 1 + h <= 389 and f:
            fwd[h] = (1 if bull else -1) * (f[0]['c'] / c - 1.0) * 1e4
        else:
            fwd[h] = None
    return dict(score=score, bull=bull, rsi1=r1, rsi5=r5, vwap=vwap, rvol=rvol, fwd=fwd)


def verify_signal(split):
    import numpy as np
    z = np.load(WORK / f'signal_{split}.npz')
    days = [str(x) for x in z['days']]
    valid, score, bull, bp = z['valid'], z['score'], z['bull'], z['bp']
    rng = random.Random(20261023)
    sig = [(i, n, j) for i, n, j in zip(*np.where(valid & (score >= 80)))]
    non = [(i, n, j) for i, n, j in zip(*np.where(valid & (score < 80)))]
    pick = rng.sample(sig, 40) + rng.sample(non, 30)
    eod = trading_days()
    rows, diffs = [], 0
    for i, n, j in pick:
        day, name, m = days[i], NAMES[n], int(j) + 1
        r = minute_state(name, day, m, eod)
        mine = dict(score=float(score[i, n, j]), bull=bool(bull[i, n, j]), fwd={h: (None if not np.isfinite(bp[i, n, j, k]) else float(bp[i, n, j, k])) for k, h in enumerate(HORIZONS)})
        bad = []
        if r is None:
            bad.append('plain loop: minute not evaluated')
        else:
            if abs(r['score'] - mine['score']) > 1e-9:
                bad.append(f"score {r['score']} vs {mine['score']}")
            if r['bull'] != mine['bull']:
                bad.append('direction')
            for h in HORIZONS:
                a, b = r['fwd'][h], mine['fwd'][h]
                if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-6):
                    bad.append(f'fwd{h} {a} vs {b}')
        diffs += bool(bad)
        rows.append(dict(name=name, day=day, minute=f'{(570 + m) // 60:02d}:{(570 + m) % 60:02d}', study=mine,
                         plain=None if r is None else {k: r[k] for k in ('score', 'bull', 'rsi1', 'rsi5', 'vwap', 'rvol', 'fwd')},
                         differences=bad))
    out = dict(split=split, checked=len(rows), signal_minutes=40, non_signal_minutes=30, rows_with_differences=diffs, rows=rows)
    (HERE / 'out' / f'verify_signal_{split}.json').write_text(json.dumps(out, indent=1, default=str))
    print('verified', len(rows), 'minutes;', diffs, 'with differences')


if __name__ == '__main__':
    if sys.argv[1] == 'signal':
        verify_signal(sys.argv[2])
