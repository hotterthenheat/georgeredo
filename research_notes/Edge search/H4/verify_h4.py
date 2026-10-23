#!/usr/bin/env python3
"""
verify_h4.py — a plain-loop re-derivation of H4 trades from the raw files, independent of run_h4.py's code path.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B verify_h4.py

Samples (random.Random(20261024)) 20 traded test-span sessions and 10 traded exploration sessions a name from out/h4_sessions.csv
and, for each, rebuilds from the raw files with plain Python loops (polars only to read a Parquet file into Python lists; no
pyarrow here): the session list from QQQ's file names, the previous session, the official closes (ThetaData EOD rows walked one by
one and matched on the New York date of `created` for a session before 2025-10-13; Unusual Whales' daily rows with market_time 'r'
walked one by one for a session from 2025-10-13), the 09:59 close and the 15:30 open (each bar file walked row by row), side, gross,
costs, borrow and net at 1x and 2x. Compares with the CSV (|difference| < 1e-9). Also checks every session of the CSV: a session
excluded carries no P&L, and a session traded has side != 0. Writes out/h4_verify.json.
"""
import csv
import datetime as dt
import glob
import json
import math
import random
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
BARS = SP / 'theta' / 'data' / 'underlying'
NY = ZoneInfo('America/New_York')
EOD_FILES = ([str(REPO / 'research_notes' / 'Compass H1' / 'data' / 'stock_eod_2012_2018.parquet')]
             + sorted(glob.glob(str(SP / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet')))
             + sorted(glob.glob(str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet'))))
UW_FILES = sorted(glob.glob(str(REPO / 'data_lake' / 'unusualwhales' / 'ohlc__1d.part0*.parquet'))) + sorted(glob.glob(str(REPO / 'data' / 'official_closes' / 'uw_ohlc_1d_*.parquet')))


def theta_rows():
    d = {}
    for f in EOD_FILES:
        t = pl.read_parquet(f, columns=['symbol', 'created', 'close']).to_dict(as_series=False)
        for s, c, v in zip(t['symbol'], t['created'], t['close']):
            if s not in ('SPY', 'QQQ'):
                continue
            if c.tzinfo is None:
                c = c.replace(tzinfo=dt.timezone.utc)
            d.setdefault((s, c.astimezone(NY).date().isoformat()), set()).add(float(v))
    return d


def uw_rows():
    d = {}
    for f in UW_FILES:
        t = pl.read_parquet(f, columns=['ticker', 'date', 'close', 'market_time']).to_dict(as_series=False)
        for s, day, v, mt in zip(t['ticker'], t['date'], t['close'], t['market_time']):
            if s in ('SPY', 'QQQ') and mt == 'r':
                d.setdefault((s, str(day)[:10]), set()).add(float(v))
    return d


TH, UW = theta_rows(), uw_rows()


def official(name, day):
    found = (TH if day < '2025-10-13' else UW).get((name, day), set())
    return next(iter(found)) if len(found) == 1 else None


def bar(name, day, hh, mm, field):
    p = BARS / name / f'{day}.parquet'
    if not p.exists():
        return None
    t = pl.read_parquet(p, columns=['timestamp', field]).to_dict(as_series=False)
    for ts, v in zip(t['timestamp'], t[field]):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt.timezone.utc)
        ts = ts.astimezone(NY)
        if ts.hour == hh and ts.minute == mm:
            return None if v is None or not math.isfinite(float(v)) else float(v)
    return None


def main():
    sessions = sorted(Path(f).name[:10] for f in glob.glob(str(BARS / 'QQQ' / '*.parquet')))
    prev = {}
    for i in range(1, len(sessions)):
        prev[sessions[i]] = sessions[i - 1]
    rows = list(csv.DictReader(open(HERE / 'out' / 'h4_sessions.csv', encoding='utf-8')))
    excl_pnl, flag_bad = 0, 0
    for r in rows:
        if r['excluded'] and r['net_1x'] not in ('', None):
            excl_pnl += 1
        if not r['excluded'] and r['side'] == '':
            flag_bad += 1
    rng = random.Random(20261024)
    sample = []
    for nm in ('SPY', 'QQQ'):
        for span, k in (('test', 20), ('exploration', 10)):
            pool = [r for r in rows if r['name'] == nm and r['span'] == span and not r['excluded'] and r['side'] not in ('', '0')]
            sample += rng.sample(pool, k)
    diffs, fields, detail = 0, 0, []
    for r in sample:
        nm, d = r['name'], r['day']
        pd_ = prev[d]
        cprev, c = official(nm, pd_), official(nm, d)
        p10, e = bar(nm, d, 9, 59, 'close'), bar(nm, d, 15, 30, 'open')
        if p10 - cprev >= 0.00005:
            side = 1
        elif cprev - p10 >= 0.00005:
            side = -1
        else:
            side = 0
        gross = side * 100 * (c - e)
        borrow = 0.003 * 100 * e * (30 / 1440) / 360 if side == -1 else 0.0
        mine = {'prev': pd_, 'Cprev': cprev, 'C': c, 'P10': p10, 'E': e, 'side': side, 'gross': gross, 'borrow': borrow,
                'net_1x': gross - 1.50 - borrow, 'net_2x': gross - 3.00 - borrow}
        for key, v in mine.items():
            fields += 1
            theirs = r[key]
            if isinstance(v, str):
                ok = v == theirs
            else:
                ok = abs(float(theirs) - v) < 1e-9
            if not ok:
                diffs += 1
                detail.append({'name': nm, 'day': d, 'field': key, 'csv': theirs, 'plain': v})
    out = {'checked': len(sample), 'by': '20 test + 10 exploration a name, seed 20261024', 'fields': fields, 'differences': diffs,
           'detail': detail, 'excluded_with_pnl': excl_pnl, 'flag_mismatch': flag_bad}
    (HERE / 'out' / 'h4_verify.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'detail'}), detail[:5])


if __name__ == '__main__':
    main()
