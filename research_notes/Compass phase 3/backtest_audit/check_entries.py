#!/usr/bin/env python3
"""
check_entries.py — re-derives a seeded random sample of the replay's TRADES from the raw files with separate,
plain-loop code (no import of paper_tracker or paper_backtest): the spot at the entry minute (the close of the last
1-minute bar stamped before it), the chain at the entry minute (the rows stamped at it), the strike rule (condor_em1:
the first quoted strike beyond spot ± the ATM straddle mid; condor_d20: the OTM strike whose Black-Scholes |delta|
from its own mid, r = q = 0, is nearest 0.20, a tie to the farther strike; fly5: K0 the strike nearest spot with both
sides quoted, a tie to the lower), the four contracts' bid and ask, the expiry (the OCC symbol's date = the session
= the chain file's date), the package price at the NBBO and the mid, and the max risk. Counts every difference.

    python3 -I check_entries.py --root data_recorder/paper_backtest --parquet-root R [--n 100] [--seed 20261022]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_lib as A  # noqa: E402

ROOT_OF = {'SPY': 'SPY', 'QQQ': 'QQQ'}


def minute_index(ts) -> int:
    return ts.hour * 60 + ts.minute - 570


def chain_at(parquet_root: Path, name: str, day: str, m: int) -> dict:
    """{(right 'C'|'P', strike): (bid, ask)} for the rows stamped m, read row by row"""
    f = Path(parquet_root) / 'data_full' / 'chains' / ROOT_OF[name] / f'{day}.parquet'
    d = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    out = {}
    for ts, k, r, b, a in d.iter_rows():
        if ts.strftime('%Y-%m-%d') != day or minute_index(ts) != m:
            continue
        out[('C' if r.upper().startswith('C') else 'P', round(float(k), 3))] = (b, a)
    return out


def spot_at(parquet_root: Path, name: str, day: str, m: int) -> float | None:
    f = Path(parquet_root) / 'data' / 'underlying' / name / f'{day}.parquet'
    d = pl.read_parquet(f, columns=['timestamp', 'close'])
    best_j, best = -10 ** 9, None
    for ts, c in d.iter_rows():
        j = minute_index(ts)
        if c is not None and 0 <= j <= m - 1 and j > best_j:
            best_j, best = j, c
    return best


def valid(q) -> bool:
    return q is not None and q[0] is not None and q[1] is not None and q[1] >= q[0] and q[0] >= 0


def ncdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def abs_delta(S: float, K: float, price: float, call: bool) -> float:
    lo, hi = 1e-6, 5.0
    for _ in range(100):
        v = (lo + hi) / 2
        d1 = (math.log(S / K) + v * v / 2) / v
        d2 = d1 - v
        model = S * ncdf(d1) - K * ncdf(d2) if call else K * ncdf(-d2) - S * ncdf(-d1)
        if model > price:
            hi = v
        else:
            lo = v
    v = (lo + hi) / 2
    d1 = (math.log(S / K) + v * v / 2) / v
    return ncdf(d1) if call else 1 - ncdf(d1)


def derive(key: str, structure: str, ch: dict, S: float) -> tuple[list, str]:
    calls = {k: q for (r, k), q in ch.items() if r == 'C' and valid(q)}
    puts = {k: q for (r, k), q in ch.items() if r == 'P' and valid(q)}
    strikes = sorted(set(calls) | set(puts))
    both = [k for k in strikes if k in calls and k in puts and calls[k][1] > 0 and puts[k][1] > 0]
    if not both:
        return [], 'no strike with both sides'
    k0 = None
    for k in both:
        if k0 is None or abs(k - S) < abs(k0 - S) or (abs(k - S) == abs(k0 - S) and k < k0):
            k0 = k
    if key == 'fly5':
        if structure == 'iron':
            return [('C', k0, 'short', 1), ('P', k0, 'short', 1), ('P', k0 - 5, 'long', 1), ('C', k0 + 5, 'long', 1)], ''
        r = 'C' if structure == 'call' else 'P'
        return [(r, k0 - 5, 'long', 1), (r, k0, 'short', 2), (r, k0 + 5, 'long', 1)], ''
    if key == 'condor_em1':
        M = (calls[k0][0] + calls[k0][1]) / 2 + (puts[k0][0] + puts[k0][1]) / 2
        kc = next((k for k in strikes if k >= S + M - 1e-9), None)
        kp = next((k for k in reversed(strikes) if k <= S - M + 1e-9), None)
    else:
        def pick(book, call):
            best = None
            for k, (b, a) in book.items():
                mid = (b + a) / 2
                if call and not (k > S and mid > 0 and a > 0 and mid < S):
                    continue
                if not call and not (k < S and mid > 0 and a > 0 and mid < k):
                    continue
                g = abs(abs_delta(S, k, mid, call) - 0.20)
                farther = (k > best[1]) if (best and call) else ((k < best[1]) if best else True)
                if best is None or g < best[0] - 1e-12 or (abs(g - best[0]) <= 1e-12 and farther):
                    best = (g, k)
            return None if best is None else best[1]
        kc, kp = pick(calls, True), pick(puts, False)
    if kc is None or kp is None:
        return [], 'no short strike'
    return [('C', kc, 'short', 1), ('C', kc + 2, 'long', 1), ('P', kp, 'short', 1), ('P', kp - 2, 'long', 1)], ''


def check(root: Path, parquet_root: Path, n: int = 100, seed: int = A.SEED) -> dict:
    df = A.load_rows(root, start=A.HIST_START, end=A.HIST_END)
    caps = df.filter((pl.col('row_kind') == 'capture') & (pl.col('tradable') == 'true')).sort('candidate', '_name', '_day', 'minute', 'structure')
    rows = caps.to_dicts()
    rng = random.Random(seed)
    by = {k: [r for r in rows if r['candidate'] == k] for k in A.KEYS}
    take = {'condor_em1': n // 3, 'condor_d20': n // 3}
    take['fly5'] = n - take['condor_em1'] - take['condor_d20']
    sample = [r for k in A.KEYS for r in rng.sample(by[k], take[k])]
    res = {'n': len(sample), 'seed': seed, 'by_candidate': take, 'diffs': {}, 'details': []}
    cnt = {x: 0 for x in ('spot', 'strikes', 'expiry', 'leg_quotes', 'price_nbbo', 'price_mid', 'max_risk', 'any')}
    cache: dict = {}
    for r in sample:
        day, nm, mi = r['_day'], r['_name'], r['minute']
        m = int(mi[:2]) * 60 + int(mi[3:]) - 570
        if (nm, day, m) not in cache:
            cache[(nm, day, m)] = (chain_at(parquet_root, nm, day, m), spot_at(parquet_root, nm, day, m))
        ch, S = cache[(nm, day, m)]
        logged = A.legs_of(r)
        exp_ok = all(r[f'l{i}_symbol'][-15:-9] == day[2:4] + day[5:7] + day[8:10] for i in range(1, 5) if r.get(f'l{i}_symbol'))
        legs, why = derive(r['candidate'], r['structure'], ch, S)
        d = []
        if S is None or abs(S - float(r['spot'])) > 1e-6:
            d.append('spot')
        if sorted(legs) != sorted(logged):
            d.append('strikes')
        if not exp_ok:
            d.append('expiry')
        qd, cash, mid, ok = False, 0.0, 0.0, True
        for i, (rt, k, side, q) in enumerate(logged, 1):
            qq = ch.get((rt, k))
            if not valid(qq):
                ok = False
                qd = True
                continue
            if abs(qq[0] - float(r[f'l{i}_bid'])) > 1e-9 or abs(qq[1] - float(r[f'l{i}_ask'])) > 1e-9:
                qd = True
            cash += q * (qq[0] if side == 'short' else -qq[1])
            mid += q * (1 if side == 'short' else -1) * (qq[0] + qq[1]) / 2
        if qd:
            d.append('leg_quotes')
        credit = r['package'] == 'credit'
        px, pmid = (cash, mid) if credit else (-cash, -mid)
        wing = float(r['wing'])
        risk = (wing - px) if credit else px
        if ok and abs(px - float(r['price_nbbo'])) > 1e-6:
            d.append('price_nbbo')
        if ok and abs(pmid - float(r['price_mid'])) > 1e-6:
            d.append('price_mid')
        if ok and abs(risk - float(r['max_risk'])) > 1e-6:
            d.append('max_risk')
        for x in d:
            cnt[x] += 1
        if d:
            cnt['any'] += 1
        res['details'].append({'candidate': r['candidate'], 'name': nm, 'day': day, 'minute': mi, 'structure': r['structure'],
                               'logged': logged, 'derived': legs, 'why': why, 'spot_logged': r['spot'], 'spot_raw': S,
                               'price_logged': r['price_nbbo'], 'price_raw': round(px, 6), 'differences': d})
    res['diffs'] = cnt
    return res


def main(argv=None) -> int:
    import os
    p = argparse.ArgumentParser()
    p.add_argument('--root', default=str(A.REPO / 'data_recorder' / 'paper_backtest'))
    p.add_argument('--parquet-root', default=os.environ.get('PAPER_PARQUET_ROOT'))
    p.add_argument('--n', type=int, default=100)
    p.add_argument('--seed', type=int, default=A.SEED)
    p.add_argument('--out', default=str(A.OUT))
    a = p.parse_args(argv)
    res = check(Path(a.root), Path(a.parquet_root), a.n, a.seed)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / 'entries.json').write_text(json.dumps(res, indent=1, default=str), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'details'}, indent=1))
    for x in res['details']:
        if x['differences']:
            print(x)
    return 0


if __name__ == '__main__':
    sys.exit(main())
