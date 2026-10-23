#!/usr/bin/env python3
"""
verify_h7_h8.py — a plain-loop re-derivation of H7 and H8 trades from the raw files, independent of run_h7_h8.py's code path.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B verify_h7_h8.py

Samples (random.Random(20261025)) 15 included H7 trades and 15 included H8 trades a name (60 in all) from out/h7_trades.csv and
out/h8_trades.csv, and rebuilds each from the raw files with plain Python loops (polars only to read a Parquet file into Python
lists): the session list from QQQ's file names; the previous session (H7) or the month's second-to-last session and the next
month's third (H8) by walking the list; the official closes (ThetaData EOD rows walked one by one and matched on the New York date
of `created` before 2025-10-13; Unusual Whales' daily rows with market_time 'r' walked one by one from 2025-10-13); the 13:58 close
and the 09:30 open (each bar file walked row by row); the dividends from the JSON table; gross and net at 1x and 2x. Compares with
the CSVs (|difference| < 1e-9; dates as strings). Also checks: no excluded row carries a P&L, and every scheduled 2:00 pm statement
in the FOMC list whose previous session is in a name's span and on or before 2026-10-22 is a row of the H7 file.
Writes out/h7_h8_verify.json.
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
FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}


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
DIV = json.loads((REPO / 'research_notes' / 'Compass H1' / 'data' / 'dividends.json').read_text(encoding='utf-8'))


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


def div_on(name, day):
    v = DIV[name].get(day)
    return v['amount'] if v else 0.0


def compare(mine, r, label, detail):
    n = bad = 0
    for key, v in mine.items():
        n += 1
        theirs = r[key]
        if isinstance(v, str):
            ok = v == theirs
        elif v is None:
            ok = theirs in ('', None)
        else:
            ok = theirs not in ('', None) and abs(float(theirs) - v) < 1e-9
        if not ok:
            bad += 1
            detail.append({'test': label, 'row': r.get('A') or r.get('E'), 'name': r['name'], 'field': key, 'csv': theirs, 'plain': v})
    return n, bad


def main():
    sessions = sorted(Path(f).name[:10] for f in glob.glob(str(BARS / 'QQQ' / '*.parquet')))
    prev = {}
    for i in range(1, len(sessions)):
        prev[sessions[i]] = sessions[i - 1]
    h7 = list(csv.DictReader(open(HERE / 'out' / 'h7_trades.csv', encoding='utf-8')))
    h8 = list(csv.DictReader(open(HERE / 'out' / 'h8_trades.csv', encoding='utf-8')))
    excl_pnl = sum(1 for r in h7 + h8 if r['excluded'] and r['net_1x'] not in ('', None))
    fomc = json.load(open(HERE / 'data' / 'fomc_statements_2012_2026.json', encoding='utf-8'))
    listed = {(r['name'], r['A']) for r in h7}
    missing = []
    for e in fomc['scheduled']:
        a = e['date']
        if not a or a > '2026-10-22' or a not in prev:
            continue
        for nm in ('SPY', 'QQQ'):
            if prev[a] >= FIRST[nm] and (nm, a) not in listed:
                missing.append(f'{nm} {a}')
    rng = random.Random(20261025)
    detail, fields, diffs, checked = [], 0, 0, 0
    for nm in ('SPY', 'QQQ'):
        pool = [r for r in h7 if r['name'] == nm and not r['excluded']]
        for r in rng.sample(pool, 15):
            a = r['A']
            p = prev[a]
            cp = official(nm, p)
            x = bar(nm, a, 13, 58, 'close')
            o = bar(nm, a, 9, 30, 'open')
            gross = 100 * (x - cp)
            dv = 100 * div_on(nm, a)
            mine = {'prev': p, 'C_prev': cp, 'X': x, 'O930': o, 'gross': gross, 'dividend': dv,
                    'net_1x': gross + dv - 1.50, 'net_2x': gross + dv - 3.00}
            n, b = compare(mine, r, 'H7', detail)
            fields += n
            diffs += b
            checked += 1
    for nm in ('SPY', 'QQQ'):
        pool = [r for r in h8 if r['name'] == nm and not r['excluded']]
        for r in rng.sample(pool, 15):
            m = r['M']
            ins = [d for d in sessions if d[:7] == m]
            y, mo = int(m[:4]), int(m[5:7])
            nxt = f'{y + (mo == 12)}-{(mo % 12) + 1:02d}'
            nxt_s = [d for d in sessions if d[:7] == nxt]
            e, last, x = ins[len(ins) - 2], ins[len(ins) - 1], nxt_s[2]
            ce, cx = official(nm, e), official(nm, x)
            dv = 0.0
            for d in sessions:
                if e < d <= x:
                    dv += div_on(nm, d)
            gross = 100 * (cx - ce)
            mine = {'E': e, 'L': last, 'X': x, 'C_E': ce, 'C_X': cx, 'gross': gross, 'dividend': 100 * dv,
                    'net_1x': gross + 100 * dv - 2.00, 'net_2x': gross + 100 * dv - 4.00}
            n, b = compare(mine, r, 'H8', detail)
            fields += n
            diffs += b
            checked += 1
    out = {'checked': checked, 'by': '15 H7 + 15 H8 trades a name, seed 20261025', 'fields': fields, 'differences': diffs,
           'detail': detail, 'excluded_with_pnl': excl_pnl, 'missing_dates': len(missing), 'missing': missing}
    (HERE / 'out' / 'h7_h8_verify.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'detail'}), detail[:5])


if __name__ == '__main__':
    main()
