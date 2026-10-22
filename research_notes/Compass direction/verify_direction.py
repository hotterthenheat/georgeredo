#!/usr/bin/env python3
"""
verify_direction.py — a plain-loop re-derivation of trades from the raw files, against what build_direction.py built.

    python3 -I verify_direction.py expl [n]     # n trades (default 40) drawn with seed 20261027 from out/…/expl_trades
    python3 -I verify_direction.py hold [n]

It shares nothing with the builder but the list of trading days and the raw files: every step is a Python loop over raw rows —
the reaction session, the earnings-day return from the stock EOD rows, the 31–60 expiry nearest 45, K*, F, IM, x, the
bucket's contract, the closing ask, the closing bid 10 full sessions later, the fees and the return.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcommon as C  # noqa: E402   (only: the trading-day list, the half days, paths)

FEE = 0.68748
CENTRES = {'ITM': -0.325, 'ATM': 0.0, 'OTM1': 0.325, 'OTM2': 0.75, 'OTM3': 1.25}


def in_b(x, b):
    e = 1e-12
    return {'ITM': -0.5 - e <= x < -0.15 - e, 'ATM': -0.15 - e <= x <= 0.15 + e, 'OTM1': 0.15 + e < x <= 0.5 + e,
            'OTM2': 0.5 + e < x <= 1.0 + e, 'OTM3': 1.0 + e < x <= 1.5 + e}[b]


def stock_rows(sym):
    """day → close, from the raw stock EOD parts (the last-trade date; a row whose report date equals it first)"""
    got = {}
    files = sorted(glob.glob(C.BAR_GLOBS[0])) + sorted(glob.glob(C.BAR_GLOBS[1]))
    for f in files:
        t = pl.scan_parquet(f).filter(pl.col('symbol') == sym).select('created', 'last_trade', 'close').collect()
        for cr, lt, c in t.iter_rows():
            if c is None or c <= 0:
                continue
            d = lt.strftime('%Y-%m-%d')
            same = cr.strftime('%Y-%m-%d') == d
            if d not in got or (same and not got[d][1]):
                got[d] = (float(c), same)
    return {d: v[0] for d, v in got.items()}


def raw_chain(name, day, disk):
    """list of (expiration, strike, right, bid, ask) of the raw file holding that day"""
    rows = []
    if disk:
        root = 'FB' if (name in ('META', 'FB') and day <= '2022-06-08') else name
        for f in sorted((C.THETA / 'fetch_cache' / 'eod_all' / root).glob('*.parquet')):
            a, b = f.stem.split('__')
            if a <= day <= b:
                t = pl.read_parquet(f, columns=['date', 'expiration', 'strike', 'right', 'bid', 'ask']).to_dicts()
                seen = set()
                for r in t:
                    if r['date'].isoformat() != day:
                        continue
                    k = (r['expiration'].isoformat(), round(r['strike'], 4), r['right'])
                    if k in seen:
                        continue
                    seen.add(k)
                    rows.append((k[0], k[1], k[2], round(float(r['bid']), 4), round(float(r['ask']), 4)))
                return rows
        return rows
    for f in sorted((C.STORE / name).glob(f'{day}__*.parquet')):
        for r in pl.read_parquet(f).to_dicts():
            rows.append((r['expiration'].isoformat(), round(r['strike'], 4), r['right'], round(float(r['bid']), 4), round(float(r['ask']), 4)))
    return list(dict.fromkeys(rows))


def derive(t: dict, closes: dict) -> dict:
    td = list(C.trading_days())
    tds = set(td)
    full = [d for d in td if d not in C.HALF_DAYS]
    rd, rt = t['report_date'], t['report_time']
    if rt == 'premarket':
        R = rd if rd in tds else min(d for d in td if d > rd)
    else:
        R = min(d for d in td if d > rd)
    P = max(d for d in td if d < R)
    E1 = min(d for d in td if d > R)
    after = [d for d in full if d > E1]
    X = after[9]
    g = closes[R] / closes[P] - 1
    pick = 'C' if g > 0 else 'P'
    disk = t['disk']
    ch = raw_chain(t['ticker'], E1, disk)
    # the expiry: last trading day 31–60 calendar days after E1, nearest 45, ties the earlier
    best = None
    for e in sorted({r[0] for r in ch}):
        le = e if e in tds else max(d for d in td if d < e)
        dte = (dt.date.fromisoformat(le) - dt.date.fromisoformat(E1)).days
        if 31 <= dte <= 60:
            k = (abs(dte - 45), le)
            if best is None or k < best[0]:
                best = (k, e)
    exp = best[1]
    calls, puts = {}, {}
    for e, k, rgt, b, a in ch:
        if e == exp:
            (calls if rgt == 'C' else puts)[k] = (b, a)
    stand = lambda q: q is not None and q[0] > 0 and q[1] > 0 and q[1] >= q[0]
    Ks, dmin = None, None
    for k in sorted(set(calls) | set(puts)):
        c, p = calls.get(k), puts.get(k)
        if stand(c) and stand(p):
            d = abs((c[0] + c[1]) / 2 - (p[0] + p[1]) / 2)
            if dmin is None or d < dmin:
                Ks, dmin = k, d
    cm = (calls[Ks][0] + calls[Ks][1]) / 2
    pm = (puts[Ks][0] + puts[Ks][1]) / 2
    F, IM = Ks + cm - pm, cm + pm
    side = calls if t['right'] == 'C' else puts
    pickk, pd = None, None
    for k in sorted(side):
        q = side[k]
        if not stand(q):
            continue
        x = (k - F) / IM if t['right'] == 'C' else (F - k) / IM
        if in_b(x, t['sb']):
            d = abs(x - CENTRES[t['sb']])
            if pd is None or d < pd - 1e-12:
                pickk, pd = k, d
    ask = side[pickk][1]
    xb = None
    for e, k, rgt, b, a in raw_chain(t['ticker'], X, disk):
        if e == exp and k == pickk and rgt == t['right']:
            xb = b if (b > 0 and a > 0 and a >= b) else 0.0
    fee_out = FEE if xb > 0 else 0.0
    r = ((xb - ask) * 100 - FEE - fee_out) / (ask * 100)
    return dict(R=R, P=P, day=E1, exit_day=X, pick=pick, expiry=exp, strike=pickk, F=F, IM=IM, ask=ask, exit_px=xb, r=r)


def main(split: str, n: int):
    df = pl.read_parquet(C.WORK / f'{split}_trades.parquet')
    idx = np.random.default_rng(20261027).choice(df.height, size=min(n, df.height), replace=False)
    sample = [df.row(int(i), named=True) for i in sorted(idx)]
    # make sure on-disk and fetched trades are both in the sample when both exist
    cache = {}
    diffs, rows = [], []
    for t in sample:
        sym = ('FB' if (t['ticker'] == 'META' and t['P'] <= '2022-06-08') else t['ticker']) if t['disk'] else t['ticker']
        if sym not in cache:
            cache[sym] = stock_rows(sym)
        v = derive(t, cache[sym])
        bad = []
        for k in ('R', 'P', 'day', 'exit_day', 'pick', 'expiry'):
            if v[k] != t[k]:
                bad.append((k, v[k], t[k]))
        for k in ('strike', 'F', 'IM', 'ask', 'exit_px', 'r'):
            if abs(v[k] - t[k]) > 1e-9 * max(1.0, abs(t[k])):
                bad.append((k, v[k], t[k]))
        rows.append(dict(ticker=t['ticker'], report_date=t['report_date'], right=t['right'], sb=t['sb'], disk=t['disk'], ok=not bad))
        if bad:
            diffs.append(dict(ticker=t['ticker'], report_date=t['report_date'], right=t['right'], sb=t['sb'], diffs=bad))
    res = dict(split=split, checked=len(sample), fields=['R', 'P', 'E1', 'exit', 'pick', 'expiry', 'strike', 'F', 'IM', 'ask',
                                                          'exit bid', 'r'],
               disk_trades=sum(r['disk'] for r in rows), fetched_trades=sum(not r['disk'] for r in rows),
               differences=len(diffs), detail=diffs, trades=rows)
    C.jdump(res, C.OUT / f'verify_{split}.json')
    print(split, 'checked', len(sample), 'differences', len(diffs))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40)
