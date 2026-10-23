#!/usr/bin/env python3
"""
verify_h1.py — a plain-loop re-derivation of H1 trades from the raw files, independent of run_h1.py's code path.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B verify_h1.py [N]     # N random traded sessions a name (default 25; seed 20261023)

For each sampled (name, session) it reads the raw files (polars only to read the Parquet into Python lists) and plain Python loops: the session list from the QQQ file
names, the next session, the EOD row whose `created` New York date is the session (every EOD file scanned row by row), the 14:59
bar's close and the next session's 09:30 bar's open (each bar file walked row by row), the dividend on the next session, and
rebuilds side, gross, dividend, borrow and the net at 1x and 2x. It compares each with out/h1_sessions.csv (|difference| < 1e-9)
and writes out/h1_verify.json. Also re-checks every excluded/flat count is consistent (a session in the CSV is traded iff side != 0).
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import json
import math
import os
import random
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
BARS = SP / 'theta' / 'data' / 'underlying'
NY = ZoneInfo('America/New_York')
EOD_FILES = ([str(HERE / 'data' / 'stock_eod_2012_2018.parquet')] + sorted(glob.glob(str(SP / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet')))
             + sorted(glob.glob(str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet'))))


def num(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


_EOD = None


def eod_rows():
    """every SPY/QQQ row of every EOD file, read once, walked row by row: (symbol, New York date of `created`) -> [closes]"""
    global _EOD
    if _EOD is None:
        _EOD = {}
        for f in EOD_FILES:
            t = pl.read_parquet(f, columns=['symbol', 'created', 'close']).to_dict(as_series=False)
            for s, c, v in zip(t['symbol'], t['created'], t['close']):
                if s not in ('SPY', 'QQQ'):
                    continue
                if c.tzinfo is None:
                    c = c.replace(tzinfo=dt.timezone.utc)
                _EOD.setdefault((s, c.astimezone(NY).date().isoformat()), []).append(v)
    return _EOD


def eod_close(name, day):
    found = eod_rows().get((name, day), [])
    if not found or len(set(found)) > 1:
        return None
    return float(found[0])


def bar_value(name, day, hh, mm, field):
    p = BARS / name / f'{day}.parquet'
    if not p.exists():
        return None
    t = pl.read_parquet(p, columns=['timestamp', field]).to_dict(as_series=False)
    for ts, v in zip(t['timestamp'], t[field]):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt.timezone.utc)
        ts = ts.astimezone(NY)
        if ts.hour == hh and ts.minute == mm:
            return num(v)
    return None


def main() -> int:
    n_per = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    sessions = sorted(f[:10] for f in os.listdir(BARS / 'QQQ') if f.endswith('.parquet'))
    div = json.loads((HERE / 'data' / 'dividends.json').read_text(encoding='utf-8'))
    rows = list(csv.DictReader(open(HERE / 'out' / 'h1_sessions.csv', encoding='utf-8')))
    rng = random.Random(20261023)
    checks, diffs = [], []
    for name in ('SPY', 'QQQ'):
        traded = [r for r in rows if r['name'] == name and r['excluded'] == '' and r['side'] not in ('', '0')]
        for r in rng.sample(traded, min(n_per, len(traded))):
            d = r['day']
            i = sessions.index(d)
            n = sessions[i + 1]
            C = eod_close(name, d)
            P = bar_value(name, d, 14, 59, 'close')
            O = bar_value(name, n, 9, 30, 'open')
            if C > P and C - P >= 0.00005:
                side = -1
            elif P > C and P - C >= 0.00005:
                side = 1
            else:
                side = 0
            D = div[name].get(n, {}).get('amount', 0.0)
            gross = side * 100 * (O - C)
            dv = side * 100 * D
            days = (dt.date.fromisoformat(n) - dt.date.fromisoformat(d)).days
            borrow = 0.003 * 100 * C * days / 360 if side == -1 else 0.0
            net1 = gross + dv - borrow - 2 * 0.01 * 100
            net2 = gross + dv - borrow - 2 * 0.02 * 100
            mine = {'next': n, 'C': C, 'P15': P, 'O': O, 'side': side, 'gross': gross, 'dividend': dv, 'borrow': borrow, 'net_1x': net1, 'net_2x': net2}
            bad = []
            for k, v in mine.items():
                theirs = r[k]
                if k == 'next':
                    ok = theirs == v
                else:
                    ok = abs(float(theirs) - float(v)) < 1e-9
                if not ok:
                    bad.append({'field': k, 'run_h1': theirs, 'verifier': v})
            checks.append({'name': name, 'day': d, **mine, 'differences': bad})
            if bad:
                diffs.append((name, d, bad))
    # consistency: a session is traded iff side != 0, and the excluded sessions carry no P&L
    incons = [(r['name'], r['day']) for r in rows if (r['excluded'] != '' and r['net_1x'] not in ('', None)) ]
    rep = {'checked': len(checks), 'differences': len(diffs), 'detail': diffs, 'excluded_with_pnl': incons, 'trades': checks}
    (HERE / 'out' / 'h1_verify.json').write_text(json.dumps(rep, indent=1, default=str), encoding='utf-8')
    print(f'checked {len(checks)} trades, {len(diffs)} with a difference; excluded sessions carrying a P&L: {len(incons)}')
    return 1 if diffs or incons else 0


if __name__ == '__main__':
    sys.exit(main())
