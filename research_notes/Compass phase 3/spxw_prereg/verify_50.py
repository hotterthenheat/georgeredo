#!/usr/bin/env python3
"""
verify_50.py — 50 SPXW structures (25 iron flies, 25 condors; seed 20261022) re-derived from the raw Parquet by separate
plain-loop code: no import of paper_tracker, paper_backtest, audit_lib or run_spxw. Spot (the SPX print stamped m), the
ratio (÷ the SPY bar stamped m − 1), K0, the wings, the 20-delta shorts (its own Black-Scholes bisection), every leg's
bid and ask, the tradable rule, the legs' credit, the package credit, the opening fees and the package P&L on the official
close (read with the csv module), and the 15:58 package exit. → out/verify_50.json

    PAPER_PARQUET_ROOT=<the stored Parquet> python3 -I verify_50.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
from pathlib import Path

import polars as pl   # the file reader only; every rule below is plain Python loops

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path(os.environ['PAPER_PARQUET_ROOT'])


def minute_rows(path: Path, hh: int, mm: int, cols):
    t = pl.read_parquet(path, columns=cols).to_dicts()
    return [r for r in t if r['timestamp'].hour == hh and r['timestamp'].minute == mm]


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def absdelta(S, K, price, call):
    lo, hi = 1e-5, 5.0
    tgt = price if call else price + S - K
    for _ in range(60):
        v = (lo + hi) / 2
        d1 = (math.log(S / K) + v * v / 2) / v
        if S * ncdf(d1) - K * ncdf(d1 - v) > tgt:
            hi = v
        else:
            lo = v
    v = (lo + hi) / 2
    d1 = (math.log(S / K) + v * v / 2) / v
    return ncdf(d1) if call else 1 - ncdf(d1)


def fee(p):
    return 0.65 + (0.36 if p < 1 else 0.45) + 0.14 + 0.01248 + 0.025


def derive(day, minute, kind, close):
    hh, mm = int(minute[:2]), int(minute[3:])
    sp = minute_rows(ROOT / 'data/index/SPX' / f'{day}.parquet', hh, mm, ['timestamp', 'price'])
    S = sp[0]['price'] if sp and sp[0]['price'] else None
    m1 = hh * 60 + mm - 1
    sy = [r for r in pl.read_parquet(ROOT / 'data/underlying/SPY' / f'{day}.parquet', columns=['timestamp', 'close']).to_dicts()
          if r['timestamp'].hour * 60 + r['timestamp'].minute == m1]
    Y = sy[0]['close'] if sy else None
    rows = minute_rows(ROOT / 'data_full/chains/SPXW' / f'{day}.parquet', hh, mm, ['timestamp', 'strike', 'right', 'bid', 'ask'])
    calls, puts, listed = {}, {}, set()
    for r in rows:
        listed.add(r['strike'])
        b, a = r['bid'], r['ask']
        if b is None or a is None or a < b or b < 0:
            continue
        (calls if r['right'].upper().startswith('C') else puts)[r['strike']] = (b, a)
    out = {'spot': S, 'ratio': S / Y if (S and Y) else None}
    if S is None or Y is None:
        return out
    ratio = S / Y
    listed = sorted(listed)

    def near(t, c):
        best = None
        for k in listed:
            key = (abs(k - t), -abs(k - c))
            if best is None or key < best[0]:
                best = (key, k)
        return best[1]
    legs, ok = [], True
    if kind == 'iron_fly':
        both = [k for k in sorted(set(calls) & set(puts)) if calls[k][1] > 0 and puts[k][1] > 0]
        k0 = None
        for k in both:
            if k0 is None or abs(k - S) < abs(k0 - S):
                k0 = k
        hi, lo = near(k0 + 5 * ratio, k0), near(k0 - 5 * ratio, k0)
        out.update({'k0': k0, 'k_hi': hi, 'k_lo': lo})
        if lo not in puts or hi not in calls or calls[k0][0] <= 0 or puts[k0][0] <= 0:
            ok = False
        if lo in puts and hi in calls:
            legs = [('C', k0, -1, calls[k0]), ('P', k0, -1, puts[k0]), ('P', lo, 1, puts[lo]), ('C', hi, 1, calls[hi])]
        width = max(hi - k0, k0 - lo)
    else:
        short = {}
        for side, book in (('C', calls), ('P', puts)):
            best = None
            for k, (b, a) in book.items():
                mid = (b + a) / 2
                if side == 'C' and not (k > S and mid > 0 and a > 0 and mid < S):
                    continue
                if side == 'P' and not (k < S and mid > 0 and a > 0 and mid < k):
                    continue
                d = absdelta(S, k, mid, side == 'C')
                key = (abs(d - 0.20), -k if side == 'C' else k)
                if best is None or key < best[0]:
                    best = (key, k)
            short[side] = best[1] if best else None
        kc, kp = short['C'], short['P']
        lc, lp = near(kc + 2 * ratio, kc), near(kp - 2 * ratio, kp)
        out.update({'k_sc': kc, 'k_sp': kp, 'k_lc': lc, 'k_lp': lp})
        for side, ks, kl, book in (('C', kc, lc, calls), ('P', kp, lp, puts)):
            qs, ql = book.get(ks), book.get(kl)
            if qs is None or qs[0] <= 0 or ql is None or ql[1] <= 0 or qs[0] - ql[1] < 0.05 * ratio - 1e-9:
                ok = False
            if qs is not None and ql is not None:
                legs += [(side, ks, -1, qs), (side, kl, 1, ql)]
        width = max(lc - kc, kp - lp)
    if len(legs) != 4:
        ok = False
    credit = sum((q[0] if s < 0 else -q[1]) for _, _, s, q in legs) if len(legs) == 4 else None
    if kind == 'iron_fly' and ok and width - credit < 0.05 * ratio - 1e-9:
        ok = False
    out.update({'tradable': ok, 'width': width, 'credit_legs': credit})
    if not ok:
        return out
    pk = math.floor(credit / 0.05 + 1e-6) * 0.05
    f_open = sum(fee(q[0] if s < 0 else q[1]) for _, _, s, q in legs)
    pay = 0.0
    for r, k, s, _ in legs:
        intr = max(close - k, 0) if r == 'C' else max(k - close, 0)
        pay += s * intr
    out.update({'credit_pkg': pk, 'fees_open': f_open, 'pnl_pkg_off': (pk + pay) * 100 - f_open})
    ex = minute_rows(ROOT / 'data_full/chains/SPXW' / f'{day}.parquet', 15, 58, ['timestamp', 'strike', 'right', 'bid', 'ask'])
    q58 = {}
    for r in ex:
        b, a = r['bid'], r['ask']
        if b is None or a is None or a < b or b < 0:
            continue
        q58[('C' if r['right'].upper().startswith('C') else 'P', r['strike'])] = (b, a)
    if all((r, k) in q58 for r, k, _, _ in legs):
        raw = sum((q58[(r, k)][1] if s < 0 else -q58[(r, k)][0]) for r, k, s, _ in legs)
        fc = sum(fee(q58[(r, k)][1] if s < 0 else q58[(r, k)][0]) for r, k, s, _ in legs)
        pc = math.ceil(raw / 0.05 - 1e-6) * 0.05
        out['x_pkg'] = (pk - pc) * 100 - f_open - fc
    return out


def main():
    tr = pl.read_parquet(HERE / 'out' / 'trades.parquet').filter(pl.col('spot').is_not_null() & pl.col('ratio').is_not_null())
    closes = {}
    with open(REPO / 'data/official_closes/cboe_SPX_History_2026-10-22.csv') as fh:
        for r in csv.DictReader(fh):
            m, d, y = r['DATE'].split('/')
            closes[f'{y}-{m}-{d}'] = float(r['SPX'])
    rng = random.Random(20261022)
    picks = []
    for an in ('iron_fly', 'condor_d20'):
        rows = tr.filter(pl.col('analogue') == an).to_dicts()
        picks += rng.sample(rows, 25)
    keys = ('spot', 'ratio', 'k0', 'k_hi', 'k_lo', 'k_sc', 'k_sp', 'k_lc', 'k_lp', 'tradable', 'width', 'credit_legs', 'credit_pkg', 'fees_open',
            'pnl_pkg_off', 'x_pkg')
    diffs, detail = {k: 0 for k in keys}, []
    for t in picks:
        v = derive(t['day'], t['minute'], t['analogue'], closes[t['day']])
        bad = []
        for k in keys:
            if k not in v:
                continue
            a, b = v[k], t.get(k)
            same = (a == b) if not isinstance(a, float) or b is None or a is None else abs(a - b) < 1e-6
            if not same:
                diffs[k] += 1
                bad.append((k, a, b))
        detail.append({'day': t['day'], 'minute': t['minute'], 'analogue': t['analogue'], 'tradable': t['tradable'], 'diffs': bad})
    res = {'n': len(picks), 'tradable': sum(1 for t in picks if t['tradable']), 'differences': diffs, 'any': sum(1 for d in detail if d['diffs']),
           'detail': detail}
    (HERE / 'out' / 'verify_50.json').write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ('n', 'tradable', 'differences', 'any')}))


if __name__ == '__main__':
    main()
