"""
verify_picker.py — an independent re-derivation of the picker's trades from the raw minute files, with plain loops.

It does not import run_picker.py or audit_lib. It reads out/trades_primary.csv and out/trades_improved.csv, draws a seeded
sample (40 primary, 10 improved), and for each rebuilds from the raw Parquet (read with pyarrow into Python lists): the
opening range or the prior-day high, the ratio for SPXW, the FIRST qualifying trigger bar of that side (so no earlier bar
qualified), the spot and the nearest OTM strike, the entry ask, every exit minute and price under the frozen rule, the
fees and the P&L. It also re-scans 20 random (name, session, side) cells where the run found no trade and checks that none
qualifies. Any difference is printed; the exit code is the number of differences.

  python3 -I verify_picker.py
"""
import csv
import math
import os
import random
import sys
from pathlib import Path

import polars as pl


def rows_of(path, columns=None):
    """the file's rows as plain Python dicts (polars only reads; every rule below is a plain loop)"""
    return pl.read_parquet(path, columns=columns).rows(named=True)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = Path(os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta'))
SEED = 20261023


def minute_of(ts):
    return ts.hour * 60 + ts.minute - 570


def load_bars(sym, day):
    t = rows_of(RAW / 'data' / 'underlying' / sym / f'{day}.parquet', ['timestamp', 'high', 'low', 'close'])
    hi, lo, cl = {}, {}, {}
    for r in t:
        if r['close'] is None:
            continue
        m = minute_of(r['timestamp'])
        hi[m] = round(r['high'], 4); lo[m] = round(r['low'], 4); cl[m] = round(r['close'], 4)
    return hi, lo, cl


def load_prints(sym, day):
    out = {}
    for r in rows_of(RAW / 'data' / 'index' / sym / f'{day}.parquet'):
        if r['price'] is not None:
            out[minute_of(r['timestamp'])] = round(r['price'], 4)
    return out


def load_chain(name, day):
    out = {}
    for r in rows_of(RAW / 'data_full' / 'chains' / name / f'{day}.parquet', ['timestamp', 'strike', 'right', 'bid', 'ask']):
        b, a = r['bid'], r['ask']
        if b is None or a is None or not (a >= b and b >= 0 and a > 0):
            continue
        m = minute_of(r['timestamp'])
        if 1 <= m <= 390:
            out[(m, r['right'], r['strike'])] = (round(b, 4), round(a, 4))
    return out


def official_close(day):
    with open(REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-22.csv') as f:
        for r in csv.DictReader(f):
            mm, dd, yy = r['DATE'].split('/')
            if f'{yy}-{mm}-{dd}' == day:
                return float(r['SPX'])
    return None


def day_view(name, day):
    """bars for the sweep (SPXW: SPY × ratio), spot by quote minute"""
    if name == 'SPXW':
        hi, lo, cl = load_bars('SPY', day)
        spx = load_prints('SPX', day)
        vals = []
        for m in range(21, 31):
            if m in spx and (m - 1) in cl and cl[m - 1] > 0:
                vals.append(spx[m] / cl[m - 1])
        vals.sort()
        if not vals:
            return None
        n = len(vals)
        ratio = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        H = {m: v * ratio for m, v in hi.items()}; L = {m: v * ratio for m, v in lo.items()}; Cc = {m: v * ratio for m, v in cl.items()}
        spot = dict(spx)
        return H, L, Cc, spot, ratio
    hi, lo, cl = load_bars(name, day)
    spot = {m + 1: v for m, v in cl.items()}
    return hi, lo, cl, spot, None


def first_trigger(H, L, Cc, side, level, buf=2.0):
    for bm in range(30, 150):
        if bm not in H or bm not in Cc:
            continue
        if side == 'PUT' and H[bm] >= level * (1 + buf / 1e4) and Cc[bm] < level:
            return bm
        if side == 'CALL' and L[bm] <= level * (1 - buf / 1e4) and Cc[bm] > level:
            return bm
    return None


def tickv(name, px):
    if name == 'SPXW':
        return 0.05 if px < 3.0 - 1e-9 else 0.10
    return 0.01


def fee1(name, px):
    if px <= 0:
        return 0.0
    if name == 'SPXW':
        return 0.65 + (0.36 if px < 1.0 - 1e-9 else 0.45) + 0.14 + 0.01248 + 0.025
    return 0.65 + 0.01248 + 0.025


def exit_of(kind, name, e, ask0, bids):
    raw = 1.25 * ask0
    tk = tickv(name, raw)
    T = round(math.ceil(round(raw / tk, 9)) * tk, 4)
    hi_seen = None
    for m in range(e + 1, 389):
        b = bids.get(m)
        if b is not None:
            hi_seen = b if hi_seen is None else max(hi_seen, b)
            if b >= T - 1e-9:
                return m, T, 'target'
            if kind == 'primary' and b <= 0.68 * ask0 + 1e-9:
                return m, b, 'stop'
        if m == e + 5:
            last = 0.0
            for j in range(m, e, -1):
                if j in bids:
                    last = bids[j]; break
            if kind == 'improved':
                return m, last, 'time5'
            if hi_seen is None or hi_seen < 1.06 * ask0 - 1e-9:
                return m, last, 'time5'
        if m == 388:
            last = 0.0
            for j in range(m, e, -1):
                if j in bids:
                    last = bids[j]; break
            return m, last, 'flat'
    return None


def rebuild(run, name, day, side):
    v = day_view(name, day)
    if v is None:
        return None
    H, L, Cc, spot, ratio = v
    if run == 'primary':
        hs = [H[m] for m in range(0, 30) if m in H]; ls = [L[m] for m in range(0, 30) if m in L]
        level = max(hs) if side == 'PUT' else min(ls)
    else:
        days = sorted(f[:-8] for f in os.listdir(RAW / 'data' / 'underlying' / ('SPY' if name == 'SPXW' else name)))
        prev = days[days.index(day) - 1]
        ph, _, _ = load_bars('SPY' if name == 'SPXW' else name, prev)
        level = max(ph[m] for m in ph if 0 <= m < 390) * (ratio if name == 'SPXW' else 1.0)
    bm = first_trigger(H, L, Cc, side, level)
    if bm is None:
        return dict(trigger_bar=None)
    e = bm + 1
    s = spot.get(e)
    ch = load_chain(name, day)
    cands = [k for (m, r, k) in ch if m == e and r == side and ((k < s) if side == 'PUT' else (k > s))]
    if not cands:
        return dict(trigger_bar=bm, strike=None)
    k = max(cands) if side == 'PUT' else min(cands)
    ask0 = ch[(e, side, k)][1]
    bids = {m: ba[0] for (m, r, kk), ba in ch.items() if r == side and kk == k}
    m, px, reason = exit_of(run, name, e, ask0, bids)
    if px <= 0:
        if name == 'SPXW':
            oc = official_close(day)
            px = max(oc - k, 0.0) if side == 'CALL' else max(k - oc, 0.0)
        else:
            px = 0.0
        fo = 0.0
    else:
        fo = fee1(name, px)
    pnl = (px - ask0) * 100 - fee1(name, ask0) - fo
    return dict(level=round(level, 4), trigger_bar=bm, entry_m=e, strike=k, entry_ask=ask0, exit_m=m, exit_px=round(px, 4),
                reason=reason, pnl=round(pnl, 4))


def main():
    rnd = random.Random(SEED)
    diffs = 0
    checked = 0
    for run, n in (('primary', 40), ('improved', 10)):
        rows = list(csv.DictReader(open(HERE / 'out' / f'trades_{run}.csv')))
        for t in rnd.sample(rows, min(n, len(rows))):
            got = rebuild(run, t['name'], t['session'], t['side'])
            checked += 1
            for key, tol in (('level', 1e-3), ('trigger_bar', 0), ('entry_m', 0), ('strike', 1e-9), ('entry_ask', 1e-9), ('exit_m', 0),
                             ('exit_px', 1e-6), ('reason', None), ('pnl', 1e-4)):
                a, b = t[key], got.get(key) if got else None
                if tol is None:
                    ok = a == b
                else:
                    try:
                        ok = abs(float(a) - float(b)) <= tol
                    except (TypeError, ValueError):
                        ok = False
                if not ok:
                    diffs += 1
                    print('DIFF', run, t['name'], t['session'], t['side'], key, 'run:', a, 'verify:', b)
            print('checked', run, t['name'], t['session'], t['side'], t['reason'], t['pnl'], flush=True)
    # cells with no trade: none should qualify
    rows = list(csv.DictReader(open(HERE / 'out' / 'trades_primary.csv')))
    have = {(r['name'], r['session'], r['side']) for r in rows}
    sess = {}
    for r in rows:
        sess.setdefault(r['name'], set()).add(r['session'])
    pool = sorted({(nm, d, sd) for nm, ds in sess.items() for d in ds for sd in ('PUT', 'CALL')} - have)
    for nm, d, sd in rnd.sample(pool, min(20, len(pool))):
        got = rebuild('primary', nm, d, sd)
        checked += 1
        if got and got.get('trigger_bar') is not None and got.get('strike') is not None:
            diffs += 1
            print('DIFF no-trade cell has a trade:', nm, d, sd, got)
        else:
            print('ok no trade', nm, d, sd)
    print(f'checked {checked}, differences {diffs}')
    (HERE / 'out' / 'verify.txt').write_text(f'{checked} re-derivations from the raw files (40 primary trades, 10 improved trades, '
                                             f'20 primary no-trade cells; seed {SEED}), {diffs} differences')
    sys.exit(min(diffs, 100))


if __name__ == '__main__':
    main()
