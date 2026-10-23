#!/usr/bin/env python3
"""
verify_h3.py — a plain-loop re-derivation of H3 trades from the raw files, independent of h3common's entry/exit code
(PREREG_H3.md §9). Draws N trades from out/trades_<set>.csv (seed 20261028) and, for each, recomputes from the stored parquet
rows with ordinary Python loops: R and P from the report's date and time on the trading-day list, close(P) and close(R) from the
raw stock EOD rows, the expiry, K0, IM, F, the four strikes, the entry quotes, the credit, the exit prices (with the fallback
rule), the fees and the $ — and counts fields that differ.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B verify_h3.py expl 50
"""
from __future__ import annotations

import bisect
import csv
import datetime as dt
import glob
import json
import random
import sys
from pathlib import Path

import polars as pl   # used only to read the parquet files into plain Python rows

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3common as H  # noqa: E402   (paths, the trading-day list and the fee only)

D = H.D
FEE = 0.65 + 0.01248 + 0.025


def rows_of(path):
    t = pl.read_parquet(path).to_dicts()
    out = []
    for r in t:
        out.append(dict(date=str(r['date']), expiration=str(r['expiration']), strike=round(float(r['strike']), 4),
                        right=str(r['right']), bid=round(float(r['bid'] or 0), 4), ask=round(float(r['ask'] or 0), 4)))
    return out


def closes(sym):
    """day → close, from the raw stock EOD rows: a row counts for the day of its last trade; one with created on that day wins"""
    best = {}
    for f in sorted({f for g in D.BAR_GLOBS for f in glob.glob(g)}):
        t = pl.read_parquet(f, columns=['symbol', 'created', 'last_trade', 'close']).filter(pl.col('symbol') == sym).to_dicts()
        for r in t:
            if r['close'] is None or not r['close'] > 0:
                continue
            day = r['last_trade'].strftime('%Y-%m-%d')
            same = r['created'].strftime('%Y-%m-%d') == day
            if day not in best or (same and not best[day][1]):
                best[day] = (float(r['close']), same)
    return {d: v[0] for d, v in best.items()}


def last_td(e, tds):
    if e in tds:
        return e
    i = bisect.bisect_left(tds, e)
    return tds[i - 1]


def near(ks, tgt, up):
    best, bd = None, None
    for k in ks:
        d = abs(k - tgt)
        if bd is None or d < bd - 1e-9 or (abs(d - bd) <= 1e-9 and ((up and k > best) or (not up and k < best))):
            best, bd = k, d
    return best


def derive(t, tds):
    sym = t['ticker']
    if t['report_time'] == 'premarket':
        R = t['report_date'] if t['report_date'] in tds else tds[bisect.bisect_right(tds, t['report_date'])]
    else:
        R = tds[bisect.bisect_right(tds, t['report_date'])]
    P = tds[bisect.bisect_left(tds, R) - 1]
    cl = closes(sym)
    cP, cR = cl.get(P), cl.get(R)
    pfile = H.find_all(sym, P)
    rows = rows_of(pfile)
    exps = sorted({r['expiration'] for r in rows})
    exp = None
    for e in exps:
        if last_td(e, tds) > R and (dt.date.fromisoformat(e) - dt.date.fromisoformat(P)).days <= 14:
            exp = e
            break
    q = {}
    for r in rows:
        if r['expiration'] == exp:
            q[(r['right'], r['strike'])] = (r['bid'], r['ask'])
    calls = sorted(k for (rt, k) in q if rt == 'C')
    puts = sorted(k for (rt, k) in q if rt == 'P')
    both = [k for k in calls if ('P', k) in q]
    K0 = near(both, cP, False)
    cb, ca = q[('C', K0)]
    pb, pa = q[('P', K0)]
    IM = (cb + ca) / 2 + (pb + pa) / 2
    F = K0 + (cb + ca) / 2 - (pb + pa) / 2
    Kcs, Kcl = near(calls, K0 + 0.5 * IM, True), near(calls, K0 + 1.5 * IM, True)
    Kps, Kpl = near(puts, K0 - 0.5 * IM, False), near(puts, K0 - 1.5 * IM, False)
    legs = dict(cs=('C', Kcs, 's'), ps=('P', Kps, 's'), cl=('C', Kcl, 'l'), pl=('P', Kpl, 'l'))
    ent = {n: q[(rt, k)] for n, (rt, k, _) in legs.items()}
    credit = ent['cs'][0] + ent['ps'][0] - ent['cl'][1] - ent['pl'][1]
    W = max(Kcl - Kcs, Kps - Kpl)
    out = dict(R=R, P=P, closeP=cP, closeR=cR, expiry=exp, K0=K0, IM=IM, F=F, Kcs=Kcs, Kcl=Kcl, Kps=Kps, Kpl=Kpl,
               cs_bid=ent['cs'][0], ps_bid=ent['ps'][0], cl_ask=ent['cl'][1], pl_ask=ent['pl'][1], credit=credit, W=W)
    maxloss = -100 * (W - credit) - 8 * FEE
    split = False
    if cR is not None:
        ratio = cR / cP
        for s in (1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 1 / 20, 1 / 50, 2, 3, 4, 5, 10, 20, 50):
            if abs(ratio / s - 1) <= 0.10:
                split = True
    if split:
        out['pnl'] = maxloss
        return out
    rpath = H.path(sym, R, exp)
    qr = {}
    if rpath.exists():
        for r in rows_of(rpath):
            qr[(r['right'], r['strike'])] = (r['bid'], r['ask'])
    fees = 4 * FEE
    px = {}
    for n, (rt, k, side) in legs.items():
        b, a = qr.get((rt, k), (None, None))
        sp = ent[n][1] - ent[n][0]
        intr = None if cR is None else (max(cR - k, 0) if rt == 'C' else max(k - cR, 0))
        if side == 's':
            if a is not None and a > 0 and a >= b:
                p = a
            elif intr is None:
                out['pnl'] = maxloss
                return out
            else:
                p = intr + sp
        else:
            if b is not None and b > 0 and a >= b:
                p = b
            elif b is not None and b == 0 and a > 0:
                p = 0.0
            elif intr is None:
                out['pnl'] = maxloss
                return out
            else:
                p = max(intr - sp, 0)
        if p > 0:
            fees += FEE
        px['x_' + n] = p
    out.update(px)
    out['pnl'] = 100 * (credit - (px['x_cs'] + px['x_ps'] - px['x_cl'] - px['x_pl'])) - fees
    return out


def main(split, n):
    trs = list(csv.DictReader(open(H.OUT / f'trades_{split}.csv')))
    random.seed(20261028)
    pick = random.sample(trs, min(n, len(trs)))
    tds = list(D.trading_days())
    diffs, checked, fields = [], 0, 0
    for t in pick:
        d = derive(t, tds)
        checked += 1
        for k, v in d.items():
            w = t[k]
            fields += 1
            if isinstance(v, str):
                ok = v == w
            elif v is None:
                ok = w in ('', 'None')
            else:
                ok = w not in ('', 'None') and abs(float(w) - v) <= 1e-6 * max(1, abs(v))
            if not ok:
                diffs.append(dict(ticker=t['ticker'], R=t['R'], field=k, table=w, loop=v))
    res = dict(split=split, checked=checked, fields=fields, differences=len(diffs), detail=diffs[:20],
               seed=20261028, how_counts={h: sum(1 for t in pick if t['how'] == h) for h in sorted({t['how'] for t in pick})})
    H.jdump(res, H.OUT / f'verify_{split}.json')
    print(json.dumps(dict(checked=checked, fields=fields, differences=len(diffs))))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 50)
