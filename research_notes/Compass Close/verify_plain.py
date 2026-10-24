"""verify_plain.py — Compass Close integrity, part 1 (PREREG section 7): 60 sessions (50 of the gate sample, 10 previously
read; seed 20261024) re-derived from the raw files with plain loops — pyarrow to read the parquet rows into Python lists,
csv for Cboe's file, no polars and nothing from close_lib or gate.py — then compared with gate.py's outputs
(out/gate_sessions.csv, out/prev_sessions.csv): K, both 15:55 quotes (each leg's bid and ask against the rows the gate read, and through STR_ask and STR_mid), SET and P&L; and for a
session with no trade, that gate.py has no trade either.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
NEW = SP / 'theta' / 'data_full' / 'chains_close' / 'SPXW'
PREV = SP / 'theta' / 'data_full' / 'chains' / 'SPXW'
SPXD = SP / 'theta' / 'data' / 'index' / 'SPX'
CBOE = HERE.parents[1] / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-23.csv'


def hhmm(ts) -> str:
    return '%02d:%02d' % (ts.hour, ts.minute)


def plain(day: str, span: str) -> dict:
    t = pq.read_table((NEW if span == 'new' else PREV) / f'{day}.parquet',
                      columns=['timestamp', 'strike', 'right', 'bid', 'ask']).to_pylist()
    quotes = {}
    calls, puts = set(), set()
    for r in t:
        h = hhmm(r['timestamp'])
        if h < '15:45' or h > '16:00':
            continue
        side = r['right'][0].upper()
        (calls if side == 'C' else puts).add(r['strike'])
        quotes[(r['strike'], side, h)] = (round(r['bid'], 4) if r['bid'] is not None else None,
                                          round(r['ask'], 4) if r['ask'] is not None else None)
    if span == 'new':
        listed = [float(k) for k in json.loads((NEW / f'{day}.meta.json').read_text())['listed_strikes']]
    else:
        listed = sorted(calls & puts)
    s = None
    for r in pq.read_table(SPXD / f'{day}.parquet').to_pylist():
        if hhmm(r['timestamp']) == '15:55':
            s = r['price']
    best = None
    for k in listed:                                   # nearest, a tie to the lower strike
        d = abs(k - s)
        if best is None or d < best[0] or (d == best[0] and k < best[1]):
            best = (d, k)
    K = best[1]
    SET = None
    with open(CBOE) as fh:
        for row in csv.DictReader(fh):
            m, dd, y = row['DATE'].split('/')
            if f'{y}-{m}-{dd}' == day:
                SET = float(row['SPX'])
    c = quotes.get((K, 'C', '15:55'))
    p = quotes.get((K, 'P', '15:55'))
    ok = True
    for q in (c, p):
        if q is None or q[0] is None or q[1] is None:
            ok = False
            continue
        b, a = q
        if not (b > 0) or not (a > b) or (a - b) > 0.5 * (a + b) / 2:
            ok = False
    out = {'day': day, 'K': K, 'S': s, 'SET': SET, 'trade': ok, 'C': c, 'P': p}
    if ok:
        str_ask = c[1] + p[1]
        entry = 100 * str_ask + 2 * 1.28
        payout = 100 * abs(SET - K) - 2 * 1.28
        out.update(str_ask=str_ask, str_mid=(c[0] + c[1]) / 2 + (p[0] + p[1]) / 2, pnl=payout - entry)
    return out


def main() -> int:
    gate = {r['day']: r for r in csv.DictReader(open(HERE / 'out' / 'gate_sessions.csv'))}
    prev = {r['day']: r for r in csv.DictReader(open(HERE / 'out' / 'prev_sessions.csv'))}
    gdays = [r['session'] for r in csv.DictReader(open(HERE / 'sessions_new.csv')) if r['sample'] == 'gate']
    pdays = sorted(prev)                       # traded previously-read sessions
    rng = random.Random(20261024)
    pick = [(d, 'new') for d in sorted(rng.sample(gdays, 50))] + [(d, 'prev') for d in sorted(rng.sample(pdays, 10))]
    diffs, n_trade, n_none, fields = [], 0, 0, 0
    sys.path.insert(0, str(HERE))
    import close_lib as L                      # the reference only: the per-leg quotes and K the gate read
    for day, span in pick:
        p = plain(day, span)
        ref = (gate if span == 'new' else prev).get(day)
        e = L.session_row(day, span)['15:55']
        for k, a, b in (('K', p['K'], e['K']), ('C', p['C'], e['C']), ('P', p['P'], e['P'])):
            fields += 1 if k == 'K' else 2
            if (tuple(a) if isinstance(a, (list, tuple)) else a) != (tuple(b) if isinstance(b, (list, tuple)) else b):
                diffs.append((day, k, a, b))
        if not p['trade']:
            n_none += 1
            fields += 1
            if ref is not None:
                diffs.append((day, 'plain says no trade, gate.py traded'))
            continue
        n_trade += 1
        if ref is None:
            diffs.append((day, 'plain traded, gate.py has no trade')); continue
        for k in ('K', 'str_ask', 'str_mid', 'SET', 'pnl'):
            fields += 1
            a, b = float(p[k]), float(ref[k if k != 'pnl' else 'pnl_usd'])
            if abs(a - b) > 1e-6:
                diffs.append((day, k, a, b))
    res = {'sessions': len(pick), 'traded': n_trade, 'no_trade': n_none, 'fields_compared': fields, 'differences': diffs}
    (HERE / 'out' / 'verify_plain.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0 if not diffs else 1


if __name__ == '__main__':
    sys.exit(main())
