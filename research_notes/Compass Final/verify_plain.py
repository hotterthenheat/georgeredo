"""verify_plain.py — Compass Final integrity, part 1 (PREREG section 11): 70 trades (10 a test, seed 20261024) re-derived from
the raw files with separate plain-loop code: pyarrow reads rows into Python lists; no polars, no numpy, nothing imported
from the run scripts, the tracker, the engines or the fee module. Every field below must equal the run's (1e-6).

  T1 fly5 iron, T2 condor_em1, T3 condor_d20: spot (the last bar with a close stamped before the entry minute), the strikes
     by the frozen rule (K0 nearest spot among strikes with both sides quoted and asks > 0, a tie the lower; em1's first
     quoted strike beyond spot +/- the straddle mid; d20's OTM |delta| nearest 0.20 by a scalar 60-step bisection, a tie the
     farther OTM), the four fills, max risk, C (Theta EOD), D (the last post-market bar stamped 16:00..17:29 with a close),
     O (the next session's 09:30 open), the case (b) P&L at Robinhood's fees.
  T4 the touch pick: the scan's spot and straddle, the touch minute (first minute after the scan with spot >= spot + M or
     <= spot - M), the 25-delta short strike at the touch, the spread's fills, C, D, O, the case (b) P&L.
  T5, T6: the SPX print at the entry minute, the ATM strike and EM, the strikes, the bids, the Cboe close, the P&L.
  T7: C, the 14:59 close, O, the side, the dividend and borrow, the net at Robinhood's fees.

    python3 -I verify_plain.py      -> out/verify_plain.json
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import json
import math
import os
import random
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
ROOT = SP + '/compass_final'
TOL = 1e-6


# ---- readers -------------------------------------------------------------------------------------------------------------------------

def rows(path: str, cols: list[str]) -> list[dict]:
    t = pq.read_table(path, columns=cols)
    data = {c: t.column(c).to_pylist() for c in cols}
    return [dict(zip(cols, v)) for v in zip(*[data[c] for c in cols])]


def hm(ts) -> str:
    if ts.tzinfo is not None:
        import zoneinfo
        ts = ts.astimezone(zoneinfo.ZoneInfo('America/New_York'))
    return f'{ts.hour:02d}:{ts.minute:02d}'


def minute_add(h: str, k: int) -> str:
    m = int(h[:2]) * 60 + int(h[3:]) + k
    return f'{m // 60:02d}:{m % 60:02d}'


def chain_at(root: str, day: str, h: str) -> tuple[dict, dict]:
    """{strike: (bid, ask)} calls and puts with a standing quote (both sides, ask >= bid, bid >= 0) in the row stamped h"""
    calls, puts = {}, {}
    for r in rows(f'{ROOT}/data_full/chains/{root}/{day}.parquet', ['timestamp', 'strike', 'right', 'bid', 'ask']):
        if hm(r['timestamp']) != h:
            continue
        b, a = r['bid'], r['ask']
        if b is None or a is None or (isinstance(b, float) and b != b) or (isinstance(a, float) and a != a) or a < b or b < 0:
            continue
        (calls if r['right'] == 'CALL' else puts)[float(r['strike'])] = (float(b), float(a))
    return calls, puts


def bars(sym: str, day: str) -> list[tuple[str, float, float]]:
    p = f'{SP}/theta/data/underlying/{sym}/{day}.parquet'
    if not os.path.exists(p):
        return []
    out = []
    for r in rows(p, ['timestamp', 'open', 'close']):
        c, o = r['close'], r['open']
        out.append((hm(r['timestamp']), None if o is None or o != o else float(o), None if c is None else float(c)))   # a NaN close stays NaN, as the replay's is_not_null keeps it
    return out


def spot_before(sym: str, day: str, h: str) -> float | None:
    last = None
    for t, o, c in bars(sym, day):
        if t < h and c is not None:
            last = c
    return None if last is None or last != last else last


def decision(sym: str, day: str) -> float | None:
    p = f'{ROOT}/data/afterhours/{sym}/{day}.parquet'
    if not os.path.exists(p):
        return None
    last = None
    for r in rows(p, ['timestamp', 'close']):
        t, c = hm(r['timestamp']), r['close']
        if '16:00' <= t <= '17:29' and c is not None and c == c:
            last = float(c)
    return last


_cal = None


def next_session(day: str) -> str | None:
    global _cal
    if _cal is None:
        _cal = []
        for f in sorted(glob.glob(f'{SP}/theta/data/underlying/QQQ/*.parquet')):
            n = sum(1 for r in rows(f, ['close']) if r['close'] is not None and r['close'] == r['close'])
            if n >= 30:
                _cal.append(os.path.basename(f)[:10])
    for d in _cal:
        if d > day:
            return d
    return None


def open_0930(sym: str, day: str) -> float | None:
    for t, o, c in bars(sym, day):
        if t == '09:30':
            return o
    return None


_eod = None


def official(sym: str, day: str) -> float | None:
    global _eod
    if _eod is None:
        _eod = {}
        files = ([str(REPO / 'research_notes/Compass H1/data/stock_eod_2012_2018.parquet')] + sorted(glob.glob(f'{SP}/lake/stock_eod/year=2019/*.parquet'))
                 + sorted(glob.glob(str(REPO / 'data_lake/thetadata/stock_eod/year=*/*.parquet'))))
        import zoneinfo
        ny = zoneinfo.ZoneInfo('America/New_York')
        for f in files:
            for r in rows(f, ['symbol', 'created', 'close']):
                if r['symbol'] in ('SPY', 'QQQ') and r['close'] is not None:
                    k = (r['symbol'], r['created'].astimezone(ny).strftime('%Y-%m-%d'))
                    _eod.setdefault(k, float(r['close']))
    return _eod.get((sym, day))


# ---- arithmetic -------------------------------------------------------------------------------------------------------------------------

def ceil_cent(x: float) -> float:
    return math.ceil(x * 100 - 1e-9) / 100 if x > 0 else 0.0


def fee_etf(price: float, qty: float, side: str) -> float:
    f = qty * (0.04 + 0.0003)
    if side == 'sell':
        f += ceil_cent(min(0.00329 * qty, 9.79)) + ceil_cent(20.60e-6 * price * 100 * qty)
    return f


def fee_spxw(price: float) -> float:
    return 0.04 + 0.0003 + 0.50 + (0.50 if price < 1.0 - 1e-9 else 0.59)


def fee_stock(price: float, sh: float, side: str) -> float:
    f = 0.000003 * sh
    if side == 'sell':
        f += ceil_cent(min(0.000195 * sh, 9.79)) + ceil_cent(20.60e-6 * price * sh)
    return f


def ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def abs_delta(S: float, K: float, price: float, call: bool) -> float:
    lo, hi = 1e-5, 5.0
    target = price if call else price + S - K
    for _ in range(60):
        v = (lo + hi) / 2
        d1 = (math.log(S / K) + v * v / 2) / v
        if S * ncdf(d1) - K * ncdf(d1 - v) > target:
            hi = v
        else:
            lo = v
    v = (lo + hi) / 2
    d1 = (math.log(S / K) + v * v / 2) / v
    return ncdf(d1) if call else 1 - ncdf(d1)


def nearest_delta(book: dict, S: float, call: bool, target: float) -> float | None:
    best = None
    for k, (b, a) in book.items():
        mid = (b + a) / 2
        if call and not (k > S and mid > 0 and a > 0 and mid < S):
            continue
        if not call and not (k < S and mid > 0 and a > 0 and mid < k):
            continue
        key = (abs(abs_delta(S, k, mid, call) - target), -k if call else k)
        if best is None or key < best[0]:
            best = (key, k)
    return best[1] if best else None


def case_b(legs: list, entry: float, C: float, D: float, O: float) -> tuple[float, int]:
    """(points a unit incl. the entry, net shares); longs exercised on C, shorts assigned on D, stock marked at O"""
    pts, sh = entry, 0
    for r, k, side, q in legs:
        px = C if side == 'long' else D
        itm = (px - k if r == 'C' else k - px) >= 0.01 - 1e-9
        if not itm:
            continue
        s = q if side == 'long' else -q
        pts += s * ((O - k) if r == 'C' else (k - O))
        sh += s * (1 if r == 'C' else -1) * 100
    return pts, sh


def straddle_k(calls: dict, puts: dict, spot: float):
    ks = [k for k in calls if k in puts and calls[k][1] > 0 and puts[k][1] > 0]
    if not ks:
        return None
    return min(ks, key=lambda k: (abs(k - spot), k))


# ---- the tests ---------------------------------------------------------------------------------------------------------------------------

def check(diffs: list, tag: str, mine, theirs) -> int:
    if mine is None and theirs is None:
        return 1
    if mine is None or theirs is None or abs(float(mine) - float(theirs)) > TOL:
        diffs.append({'trade': tag, 'mine': mine, 'run': theirs})
    return 1


def settle_b(name, day, legs, entry, open_fee, diffs, tag, row) -> int:
    n = 0
    C, D = official(name, day), decision(name, day)
    nx = next_session(day)
    O = open_0930(name, nx)
    n += check(diffs, tag + ' C', C, row['official'])
    n += check(diffs, tag + ' D', D, row['decision_px'])
    n += check(diffs, tag + ' O', O, row['next_open_0930'])
    pts, sh = case_b(legs, entry, C, D, O)
    stock = fee_stock(O, abs(sh), 'sell' if sh > 0 else 'buy') if sh else 0.0
    n += check(diffs, tag + ' pnl_b (Robinhood)', pts * 100 - open_fee - stock, row['pnl_b'])
    return n


def t123(diffs: list, rng: random.Random) -> dict:
    T = rows(str(HERE / 'out' / 't123_trades.parquet'), ['candidate', 'structure', 'name', 'date', 'entry', 'legs', 'price_nbbo', 'max_risk',
                                                            'official', 'decision_px', 'next_open_0930', 'pnl_b'])
    n = 0
    for cand in ('fly5', 'condor_em1', 'condor_d20'):
        pool = [r for r in T if r['candidate'] == cand and (cand != 'fly5' or r['structure'] == 'iron') and r['pnl_b'] is not None]
        for r in rng.sample(pool, min(10, len(pool))):
            nm, day, h = r['name'], r['date'], r['entry']
            tag = f"{cand} {nm} {day} {h}"
            calls, puts = chain_at(nm, day, h)
            spot = spot_before(nm, day, h)
            if cand == 'fly5':
                k0 = straddle_k(calls, puts, spot)
                legs = [('C', k0, 'short', 1), ('P', k0, 'short', 1), ('P', k0 - 5, 'long', 1), ('C', k0 + 5, 'long', 1)]
                credit = calls[k0][0] + puts[k0][0] - puts[k0 - 5][1] - calls[k0 + 5][1]
                risk = 5 - credit
            else:
                if cand == 'condor_em1':
                    k0 = straddle_k(calls, puts, spot)
                    M = sum(calls[k0]) / 2 + sum(puts[k0]) / 2
                    strikes = sorted(set(calls) | set(puts))
                    kc = next(k for k in strikes if k >= spot + M - 1e-9)
                    kp = next(k for k in reversed(strikes) if k <= spot - M + 1e-9)
                else:
                    kc = nearest_delta(calls, spot, True, 0.20)
                    kp = nearest_delta(puts, spot, False, 0.20)
                legs = [('C', kc, 'short', 1), ('C', kc + 2, 'long', 1), ('P', kp, 'short', 1), ('P', kp - 2, 'long', 1)]
                credit = calls[kc][0] - calls[kc + 2][1] + puts[kp][0] - puts[kp - 2][1]
                risk = 2 - credit
            run_legs = sorted((a, round(b, 3), c, d) for a, b, c, d in json.loads(r['legs']))
            if sorted((a, round(b, 3), c, d) for a, b, c, d in legs) != run_legs:
                diffs.append({'trade': tag + ' legs', 'mine': legs, 'run': run_legs})
            n += 1
            n += check(diffs, tag + ' price', credit, r['price_nbbo'])
            n += check(diffs, tag + ' max risk', risk, r['max_risk'])
            fee = 0.0
            for rt, k, side, q in legs:
                bk = calls if rt == 'C' else puts
                fee += fee_etf(bk[k][0], q, 'sell') if side == 'short' else fee_etf(bk[k][1], q, 'buy')
            n += settle_b(nm, day, legs, credit, fee, diffs, tag, r)
    return {'fields': n}


def t4(diffs: list, rng: random.Random) -> dict:
    T = rows(str(HERE / 'out' / 't4_trades.parquet'), ['date', 'entry', 'structure', 'legs', 'credit', 'm_scan', 'official', 'decision_px',
                                                          'next_open_0930', 'pnl_b'])
    pool = [r for r in T if r['pnl_b'] is not None]
    n = 0
    for r in rng.sample(pool, min(10, len(pool))):
        day, h, side = r['date'], r['entry'], r['structure']
        tag = f"touch {day} {h} {side}"
        bl = bars('SPY', day)
        px = {}
        for t, o, c in bl:
            m = int(t[:2]) * 60 + int(t[3:]) - 570 + 1
            if c is not None and 0 <= m <= 390 and m - 1 < 390:
                px[m] = c
        s = int(r['m_scan'])
        sh = f'{(s + 570) // 60:02d}:{(s + 570) % 60:02d}'
        calls, puts = chain_at('SPY', day, sh)
        k0 = min((k for k in calls if k in puts and calls[k][1] > 0 and puts[k][1] > 0), key=lambda k: (abs(k - px[s]), k))
        M = sum(calls[k0]) / 2 + sum(puts[k0]) / 2
        up = side == 'call'
        t = next(m for m in sorted(px) if m > s and ((px[m] >= px[s] + M) if up else (px[m] <= px[s] - M)))
        n += check(diffs, tag + ' touch minute', t, int(h[:2]) * 60 + int(h[3:]) - 570)
        S = px[t]
        ca, pu = chain_at('SPY', day, h)
        book = ca if up else pu
        ks = nearest_delta(book, S, up, 0.25)
        kl = ks + 2 if up else ks - 2
        credit = book[ks][0] - book[kl][1]
        R = 'C' if up else 'P'
        legs = [(R, ks, 'short', 1), (R, kl, 'long', 1)]
        run_legs = sorted((a, round(b, 3), c, d) for a, b, c, d in json.loads(r['legs']))
        if sorted((a, round(b, 3), c, d) for a, b, c, d in legs) != run_legs:
            diffs.append({'trade': tag + ' legs', 'mine': legs, 'run': run_legs})
        n += 1
        n += check(diffs, tag + ' credit', credit, r['credit'])
        fee = fee_etf(book[ks][0], 1, 'sell') + fee_etf(book[kl][1], 1, 'buy')
        n += settle_b('SPY', day, legs, credit, fee, diffs, tag, r)
    return {'fields': n}


def t56(diffs: list, rng: random.Random) -> dict:
    T = rows(str(HERE / 'out' / 't56_trades.parquet'), ['test', 'date', 'entry', 'kc', 'kp', 'credit', 'settle', 'pnl', 'spot', 'em'])
    cb = {}
    for r in csv.DictReader(open(REPO / 'data/official_closes/cboe_SPX_History_2026-10-23.csv')):
        m, d, y = r['DATE'].split('/')
        cb[f'{y}-{m}-{d}'] = float(r['SPX'])
    n = 0
    for test, k in (('h13_te', 0.0), ('h15_s2', 0.5)):
        pool = [r for r in T if r['test'] == test]
        for r in rng.sample(pool, min(10, len(pool))):
            day, h = r['date'], r['entry']
            tag = f'{test} {day}'
            spot = None
            for p in (f'{SP}/theta/data/index/SPX/{day}.parquet', f'{ROOT}/data/index/SPX/{day}.parquet'):
                if os.path.exists(p):
                    for x in rows(p, ['timestamp', 'price']):
                        if hm(x['timestamp']) == h and x['price']:
                            spot = float(x['price'])
                    break
            allk = sorted({float(x['strike']) for x in rows(f'{ROOT}/data_full/chains/SPXW/{day}.parquet', ['strike'])})
            calls, puts = {}, {}
            for x in rows(f'{ROOT}/data_full/chains/SPXW/{day}.parquet', ['timestamp', 'strike', 'right', 'bid', 'ask']):
                if hm(x['timestamp']) != h:
                    continue
                b, a = x['bid'], x['ask']
                if b is None or a is None or b != b or a != a or not (a > 0) or a < b:
                    continue
                (calls if x['right'] == 'CALL' else puts)[float(x['strike'])] = (float(b), float(a))
            both = [kk for kk in allk if kk in calls and kk in puts]
            k0 = round(spot / 5) * 5
            if k0 not in both:
                k0 = min(both, key=lambda kk: (abs(kk - spot), kk))
            em = sum(calls[k0]) / 2 + sum(puts[k0]) / 2
            if k == 0:
                kc = kp = k0
            else:
                kc = min(kk for kk in allk if kk >= spot + k * em - 1e-9)
                kp = max(kk for kk in allk if kk <= spot - k * em + 1e-9)
            credit = round(calls[kc][0] + puts[kp][0], 4)
            S = cb[day]
            pay = max(S - kc, 0) + max(kp - S, 0)
            pnl = (credit - pay) * 100 - fee_spxw(calls[kc][0]) - fee_spxw(puts[kp][0])
            n += check(diffs, tag + ' spot', spot, r['spot']) + check(diffs, tag + ' em', em, r['em'])
            n += check(diffs, tag + ' kc', kc, r['kc']) + check(diffs, tag + ' kp', kp, r['kp'])
            n += check(diffs, tag + ' credit', credit, r['credit']) + check(diffs, tag + ' Cboe close', S, r['settle'])
            n += check(diffs, tag + ' pnl (Robinhood)', pnl, r['pnl'])
    return {'fields': n}


def t7(diffs: list, rng: random.Random) -> dict:
    T = rows(str(HERE / 'out' / 't7_trades.parquet'), ['date', 'side', 'C', 'P15', 'O', 'next', 'dividend', 'borrow', 'pnl'])
    div = json.loads((REPO / 'research_notes/Compass H1/data/dividends.json').read_text())['QQQ']
    n = 0
    for r in rng.sample(T, min(10, len(T))):
        day = r['date']
        tag = f'h1 QQQ {day}'
        C = official('QQQ', day)
        P = next((c for t, o, c in bars('QQQ', day) if t == '14:59' and c == c), None)
        nx = next_session(day)
        O = open_0930('QQQ', nx)
        side = -1 if C - P >= 0.00005 else (1 if P - C >= 0.00005 else 0)
        dv = side * 100 * (div[nx]['amount'] if nx in div else 0.0)
        days = (dt.date.fromisoformat(nx) - dt.date.fromisoformat(day)).days
        borrow = 0.003 * 100 * C * days / 360 if side == -1 else 0.0
        fee = (fee_stock(C, 100, 'buy') + fee_stock(O, 100, 'sell')) if side == 1 else (fee_stock(C, 100, 'sell') + fee_stock(O, 100, 'buy'))
        net = side * 100 * (O - C) + dv - borrow - fee
        for nm, a, b in (('C', C, r['C']), ('P15', P, r['P15']), ('O', O, r['O']), ('side', side, r['side']), ('dividend', dv, r['dividend']),
                         ('borrow', borrow, r['borrow']), ('pnl (Robinhood)', net, r['pnl'])):
            n += check(diffs, f'{tag} {nm}', a, b)
    return {'fields': n}


def main() -> None:
    rng = random.Random(20261024)
    diffs: list = []
    res = {'T1-T3': t123(diffs, rng), 'T4': t4(diffs, rng), 'T5-T6': t56(diffs, rng), 'T7': t7(diffs, rng)}
    res['trades'] = 70
    res['fields_compared'] = sum(v['fields'] for v in res.values() if isinstance(v, dict))
    res['differences'] = len(diffs)
    res['difference_rows'] = diffs[:50]
    (HERE / 'out' / 'verify_plain.json').write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != 'difference_rows'}, indent=1), diffs[:5])


if __name__ == '__main__':
    main()
