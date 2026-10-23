"""
verify_plain_v1.py — a plain-loop re-derivation of sampled headline trades of the v1 PREVIEW (RULEBOOK_v1.md), copied from
verify_plain.py (v0's, unchanged) and adapted; it imports neither ema_system.py nor ema_v1.py: reads the raw parquet files
itself, computes every indicator with plain Python loops, re-checks that the rule held at the entry minute and at no earlier
allowed minute (09:45..13:29) where a contract would have passed, re-picks the contract in each venue with the 3% cap,
re-makes the S&P venue choice by cost share, walks the exit with the 14:00 flat and recomputes the P&L.
Writes out_v1/verify_summary.md. Target: 0 differences.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import os
import random
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
import json
WEEKS = {k: v['days'] for k, v in json.loads((Path(__file__).resolve().parent / 'out_v1' / 'weeks.json').read_text())['picks'].items() if v}
CAP, FLAT, LAST = 0.03, 270, 239
ALIGN = {'A': (5, 15, 20, 50), 'B': (9, 21, 50)}
PULL = {'A': 20, 'B': 21}
NB = 390


def minute(ts):
    return ts.hour * 60 + ts.minute - 570


def bars_of(name, d):
    if name == 'SPXW':
        p = SP / 'theta' / 'data' / 'index' / 'SPX' / f'{d}.parquet'
        out = [None] * NB
        for ts, px in pl.read_parquet(p).iter_rows():
            k = minute(ts)
            if 1 <= k <= NB and px is not None and px == px:
                out[k - 1] = (px, px, px, px, None)
        return out
    p = SP / 'theta' / 'data' / 'underlying' / name / f'{d}.parquet'
    out = [None] * NB
    for ts, o, h, l_, c, v in pl.read_parquet(p, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).iter_rows():
        k = minute(ts)
        if 0 <= k < NB and None not in (o, h, l_, c) and c == c:
            out[k] = (o, h, l_, c, float(v or 0))
    return out


def day_list(name, week):
    folder = SP / 'theta' / 'data' / ('index/SPX' if name == 'SPXW' else f'underlying/{name}')
    ds = sorted(f.stem for f in folder.glob('*.parquet'))
    before = [x for x in ds if x < week[0]]
    return before[-60:] + list(week)


class Plain:
    def __init__(self, name, upto, week):
        self.name = name
        self.days = [x for x in day_list(name, week) if x <= upto]
        self.b = {d: bars_of(name, d) for d in self.days}
        flat = [(d, s) for d in self.days for s in range(NB)]
        self.pos = {k: n for n, k in enumerate(flat)}
        closes = [self.b[d][s][3] if self.b[d][s] else None for d, s in flat]
        self.e1 = {n: self.ema(closes, n) for n in (5, 9, 15, 20, 21, 50)}
        self.rsi = self.wilder(closes)
        self.closes = closes
        b5, b15 = [], []
        for d in self.days:
            for size, acc in ((5, b5), (15, b15)):
                for j in range(NB // size):
                    last = None
                    for s in range(size * j, size * j + size):
                        if self.b[d][s]:
                            last = self.b[d][s][3]
                    acc.append(last)
        self.k5 = {(d, j): n for n, (d, j) in enumerate((d, j) for d in self.days for j in range(78))}
        self.k15 = {(d, j): n for n, (d, j) in enumerate((d, j) for d in self.days for j in range(26))}
        self.b5, self.b15 = b5, b15
        self.e5 = {n: self.ema(b5, n) for n in (5, 9, 15, 20, 21, 50)}
        self.e15 = {n: self.ema(b15, n) for n in (50,)}

    @staticmethod
    def ema(x, n):
        a, e, out = 2 / (n + 1), None, []
        for v in x:
            if v is not None:
                e = v if e is None else e + a * (v - e)
            out.append(e)
        return out

    @staticmethod
    def wilder(x, n=14):
        out, prev, g0, l0, ag, al = [], None, [], [], None, None
        for v in x:
            if v is None:
                out.append(out[-1] if out else None)
                continue
            if prev is not None:
                ch = v - prev
                if ag is None:
                    g0.append(max(ch, 0)); l0.append(max(-ch, 0))
                    if len(g0) == n:
                        ag, al = sum(g0) / n, sum(l0) / n
                else:
                    ag = (ag * (n - 1) + max(ch, 0)) / n
                    al = (al * (n - 1) + max(-ch, 0)) / n
            prev = v
            if ag is None:
                out.append(None)
            else:
                out.append(100.0 if al == 0 and ag > 0 else (50.0 if al == 0 else 100 - 100 / (1 + ag / al)))
        return out

    def vwap(self, d, s):
        num = den = 0.0
        for t in range(s + 1):
            r = self.b[d][t]
            if r is None:
                continue
            w = 1.0 if self.name == 'SPXW' else r[4]
            tp = r[3] if self.name == 'SPXW' else (r[1] + r[2] + r[3]) / 3
            num += tp * w; den += w
        return num / den if den > 0 else None

    def rvol(self, d, s):
        i = self.days.index(d)
        vs = [self.b[x][s][4] for x in self.days[max(0, i - 10):i] if self.b[x][s]]
        if len(vs) < 5 or sum(vs) == 0:
            return None
        return self.b[d][s][4] / (sum(vs) / len(vs))

    def signal(self, d, m, cfg):
        s = m - 1
        B = self.b[d]
        if any(B[t] is None for t in range(s - 4, s + 1)):
            return 0
        i = self.days.index(d)
        j15 = m // 15 - 1
        k15 = self.k15[(d, j15)] if j15 >= 0 else self.k15[(self.days[i - 1], 25)]
        c15, e15 = self.b15[k15], self.e15[50][k15]
        bias = 1 if c15 > e15 else (-1 if c15 < e15 else 0)
        j5 = m // 5 - 1
        k5 = self.k5[(d, j5)] if j5 >= 0 else self.k5[(self.days[i - 1], 77)]
        v = [self.e5[n][k5] for n in ALIGN[cfg]]
        up = all(v[q] > v[q + 1] for q in range(len(v) - 1))
        dn = all(v[q] < v[q + 1] for q in range(len(v) - 1))
        al = 1 if up else (-1 if dn else 0)
        if bias == 0 or al != bias:
            return 0
        P = lambda t: self.pos[(d, t)]  # noqa: E731
        pl_, e50 = self.e1[PULL[cfg]], self.e1[50]
        touch = bad = False
        for t in range(s - 4, s + 1):
            vw = self.vwap(d, t)
            if bias > 0:
                touch |= B[t][2] <= max(pl_[P(t)], vw)
                bad |= B[t][3] < e50[P(t)]
            else:
                touch |= B[t][1] >= min(pl_[P(t)], vw)
                bad |= B[t][3] > e50[P(t)]
        vw = self.vwap(d, s)
        c = B[s][3]
        c5ago = self.closes[P(s) - 5]
        roc = c / c5ago - 1
        rs = self.rsi[P(s)]
        if bias > 0:
            ok = c > B[s - 1][1] and c > vw and rs > 50 and roc > 0
        else:
            ok = c < B[s - 1][2] and c < vw and rs < 50 and roc < 0
        if self.name != 'SPXW':
            rv = self.rvol(d, s)
            ok = ok and rv is not None and rv >= 1.5
        return bias if (touch and not bad and ok) else 0


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs(Sx, K, T, v, call, r=0.045):
    d1 = (math.log(Sx / K) + (r + v * v / 2) * T) / (v * math.sqrt(T))
    d2 = d1 - v * math.sqrt(T)
    c = Sx * ncdf(d1) - K * math.exp(-r * T) * ncdf(d2)
    return (c if call else c - Sx + K * math.exp(-r * T)), (ncdf(d1) if call else ncdf(d1) - 1)


def delta_of(price, Sx, K, T, call):
    df = math.exp(-0.045 * T)
    lo_b = max(Sx - K * df, 0) if call else max(K * df - Sx, 0)
    up_b = Sx if call else K * df
    if not (price > lo_b + 1e-12 and price < up_b):
        return None
    a, b = 1e-4, 10.0
    for _ in range(80):
        mid = (a + b) / 2
        if bs(Sx, K, T, mid, call)[0] > price:
            b = mid
        else:
            a = mid
    return abs(bs(Sx, K, T, (a + b) / 2, call)[1])


_chains = {}


def chain_rows(name, d):
    if (name, d) not in _chains:
        x = pl.read_parquet(SP / 'theta' / 'data_full' / 'chains' / name / f'{d}.parquet',
                            columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
        rows, bym = {}, {}
        for ts, k, rt, b, a in x.iter_rows():
            rows[(minute(ts), float(k), rt)] = (b, a)
            bym.setdefault(minute(ts), []).append((float(k), rt, b, a))
        _chains[(name, d)] = (rows, bym)
    return _chains[(name, d)]


def oi_map(name, d):
    t = 'SPX' if name == 'SPXW' else name
    x = pl.read_parquet(SP / 'features_data' / 'uw' / 'oi_chain' / t / f'{d}.parquet', columns=['option_symbol', 'open_interest'])
    return {a: b for a, b in x.iter_rows() if b is not None}


_pv = {}


def pvol_map(name, d, prev):
    if (name, d) in _pv:
        return _pv[(name, d)]
    out = _pv[(name, d)] = {}
    for f in sorted((SP / 'theta' / 'fetch_cache' / 'eod_all' / name).glob('*.parquet')):
        a, b = f.stem.split('__')
        if a <= prev <= b:
            x = pl.read_parquet(f, columns=['date', 'expiration', 'strike', 'right', 'volume'])
            for dd, ex, k, rt, v in x.iter_rows():
                if dd.isoformat() == prev and ex.isoformat() == d:
                    out[(float(k), rt)] = int(v or 0)
    return out


_oi = {}


def plain_pick(name, d, m, side, spot, prev):
    rows = chain_rows(name, d)[1]
    rt = 'CALL' if side > 0 else 'PUT'
    if (name, d) not in _oi:
        _oi[(name, d)] = oi_map(name, d)
    oi, pv = _oi[(name, d)], pvol_map(name, d, prev)
    root = 'SPXW' if name == 'SPXW' else name
    T = (390 - m) / 525600
    best = None
    for k, r, b, a in rows.get(m, []):
        if r != rt or b is None or a is None or not (a > b > 0):
            continue
        mid = (a + b) / 2
        spr = (a - b) / mid
        if spr > CAP + 1e-12:
            continue
        dl = delta_of(mid, spot, k, T, side > 0)
        if dl is None or dl < 0.30 - 1e-12 or dl > 0.60 + 1e-12:
            continue
        sym = f'{root}{d[2:4]}{d[5:7]}{d[8:10]}{"C" if side > 0 else "P"}{int(round(k * 1000)):08d}'
        if oi.get(sym, 0) < 250 or pv.get((k, 'C' if side > 0 else 'P'), 0) < 100:
            continue
        key = (round(abs(dl - 0.45), 12), spr, k)
        if best is None or key < best[0]:
            best = (key, dict(K=k, ask=a, bid=b, delta=dl))
    return None if best is None else best[1]


def bid_at(name, d, m, K, side):
    rows = chain_rows(name, d)[0]
    rt = 'CALL' if side > 0 else 'PUT'
    for mm in range(m, max(-1, m - 11), -1):
        q = rows.get((mm, K, rt))
        if q and q[0] is not None and q[0] == q[0]:
            return max(0.0, q[0])
    return 0.0


def fee(name, p):
    return (1.18748 if p < 1 else 1.27748) if name == 'SPXW' else 0.68748


def walk(P, d, m, side, ex_v):
    B = P.b[d]
    s = m - 1
    e_u = B[s][3]
    lvl = min(B[t][2] for t in range(s - 4, s + 1)) if side > 0 else max(B[t][1] for t in range(s - 4, s + 1))
    R = abs(e_u - lvl)
    legs, open_q, h1, h2 = [], (10 if ex_v == 'X4' else 1), False, False
    for t in range(s + 1, FLAT):
        if B[t] is None:
            continue
        c = B[t][3]
        mv = (c - e_u) * side
        if (side > 0 and c < lvl) or (side < 0 and c > lvl):
            legs.append((open_q, t + 1, 'stop')); open_q = 0
        else:
            x3 = False
            if t % 5 == 4:
                k5 = P.k5[(d, t // 5)]
                x3 = (P.b5[k5] < P.e5[9][k5]) if side > 0 else (P.b5[k5] > P.e5[9][k5])
            if ex_v == 'X1' and mv >= R - 1e-12:
                legs.append((open_q, t + 1, '+1R')); open_q = 0
            elif ex_v == 'X2' and mv >= 2 * R - 1e-12:
                legs.append((open_q, t + 1, '+2R')); open_q = 0
            elif ex_v == 'X3' and x3:
                legs.append((open_q, t + 1, 'runner')); open_q = 0
            elif ex_v == 'X4':
                if not h1 and mv >= R - 1e-12:
                    legs.append((2, t + 1, '+1R')); open_q -= 2; h1 = True
                if not h2 and mv >= 2 * R - 1e-12:
                    legs.append((3, t + 1, '+2R')); open_q -= 3; h2 = True
                if x3 and open_q > 0:
                    legs.append((open_q, t + 1, 'runner')); open_q = 0
        if open_q == 0:
            break
    if open_q > 0:
        legs.append((open_q, FLAT, '14:00'))
    return R, legs


def prev_day(name, d):
    folder = SP / 'theta' / 'data' / 'underlying' / 'SPY'
    ds = sorted(f.stem for f in folder.glob('*.parquet'))
    return [x for x in ds if x < d][-1]


_spx = {}


def spx_print(d, m):
    """the SPX print stamped minute m (v0 §1: the close of bar m − 1)"""
    if d not in _spx:
        out = {}
        for ts, px in pl.read_parquet(SP / 'theta' / 'data' / 'index' / 'SPX' / f'{d}.parquet').iter_rows():
            if px is not None and px == px:
                out[minute(ts)] = px
        _spx[d] = out
    return _spx[d].get(m)


def venue_pick(stream, d, m, side, spot, prev):
    """→ (venue, contract) or (None, None): the S&P stream takes the lower ((ask − mid) + fee/100)/mid, ties SPY"""
    if stream != 'S&P':
        c = plain_pick(stream, d, m, side, spot, prev)
        return (stream, c) if c else (None, None)
    a = plain_pick('SPY', d, m, side, spot, prev)
    sx = spx_print(d, m)
    b = plain_pick('SPXW', d, m, side, sx, prev) if sx is not None else None
    if a is None and b is None:
        return None, None
    if b is None:
        return 'SPY', a
    if a is None:
        return 'SPXW', b

    def share(v, c):
        mid = (c['ask'] + c['bid']) / 2
        return ((c['ask'] - mid) + fee(v, c['ask']) / 100) / mid
    return ('SPXW', b) if share('SPXW', b) < share('SPY', a) - 1e-12 else ('SPY', a)


def main(seed=20261023):
    rows = list(csv.DictReader(open(HERE / 'out_v1' / 'trades_v1.csv')))
    for r in rows:
        r['m'] = int(r['m']); r['side'] = int(r['side']); r['exit_m'] = int(r['exit_m'])
    seqs = {}
    for r in rows:
        seqs.setdefault((r['cfg'], r['exit'], r['stream'], r['day']), []).append(r)
    rng = random.Random(seed)
    keyset = sorted({(r['cfg'], r['exit'], r['stream'], r['venue']) for r in rows})
    picks = []
    for k in keyset:                                     # one per (config, exit, stream, venue) where rows exist
        cand = [r for r in rows if (r['cfg'], r['exit'], r['stream'], r['venue']) == k]
        picks.append(rng.choice(cand))
    plain = {}
    diffs, lines = [], []
    bars = {'S&P': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM'}
    for r in picks:
        stx, d, cfg, ex_v = r['stream'], r['day'], r['cfg'], r['exit']
        nm = bars[stx]
        wk = WEEKS[r['week']]
        if (nm, d) not in plain:
            plain[(nm, d)] = Plain(nm, d, wk)
        P = plain[(nm, d)]
        seq = seqs[(cfg, ex_v, stx, d)]
        k = seq.index(r)
        start = 15 if k == 0 else seq[k - 1]['exit_m'] + (5 if seq[k - 1]['reason'] == 'stop' else 1)
        prev = prev_day(nm, d)
        why = []
        if r['m'] > LAST:
            why.append('entry after 13:29')
        for m in range(start, r['m']):
            sg = P.signal(d, m, cfg)
            if sg and venue_pick(stx, d, m, sg, P.b[d][m - 1][3], prev)[0] is not None:
                if walk(P, d, m, sg, ex_v)[0] > 0:
                    why.append(f'an earlier allowed entry at {m}')
                    break
        sg = P.signal(d, r['m'], cfg)
        if sg != r['side']:
            why.append(f'signal {sg} != {r["side"]}')
        v, c = venue_pick(stx, d, r['m'], r['side'], P.b[d][r['m'] - 1][3], prev)
        if c is None or v != r['venue'] or abs(c['K'] - float(r['K'])) > 1e-9 or abs(c['ask'] - float(r['ask'])) > 1e-9 \
                or abs(c['delta'] - float(r['delta'])) > 1e-6:
            why.append(f'contract {v} {c} != {r["venue"]} {r["K"]} {r["ask"]} {r["delta"]}')
        R, legs = walk(P, d, r['m'], r['side'], ex_v)
        if abs(R - float(r['R'])) > 1e-9:
            why.append(f'R {R} != {r["R"]}')
        qty = sum(q for q, *_ in legs)
        if c is not None:
            out = [(q, e, bid_at(v, d, e, c['K'], r['side']), w) for q, e, w in legs]
            gross = sum(q * (px - c['ask']) * 100 for q, e, px, w in out)
            fees = qty * fee(v, c['ask']) + sum(q * fee(v, px) for q, e, px, w in out)
            net = gross - fees
            e_last = max(e for q, e, *_ in out)
            reason = 'stop' if any(w == 'stop' for *_, w in out) else out[-1][3]
            if e_last != r['exit_m'] or reason != r['reason'] or abs(net - float(r['net'])) > 1e-6 or e_last > FLAT:
                why.append(f'exit {e_last} {reason} {net:.4f} != {r["exit_m"]} {r["reason"]} {float(r["net"]):.4f}')
        lines.append(f"| {cfg} · {ex_v} | {stx} | {r['venue']} | {d} | {r['entry']} | {'call' if r['side'] > 0 else 'put'} {r['K']} | "
                     f"{r['reason']} at minute {r['exit_m']} | {float(r['net']):+.2f} | {'0 differences' if not why else '; '.join(why)} |")
        diffs += why
    md = ['## 10. Integrity: a plain-loop re-derivation\n',
          f'`verify_plain_v1.py` (imports neither engine; raw parquet, plain Python loops, its own Black-Scholes bisection) '
          f're-derived {len(picks)} headline trades, one drawn (seed {seed}) per config × exit × stream × venue present: the rule '
          'at the entry minute, no earlier allowed minute (09:45–13:29) where the rule and a contract in either venue would have '
          'entered, both venues\' contracts under the 3% cap and the cost-share choice, R, every exit leg with the 14:00 flat, the '
          f'bids and the net. **Differences: {len(diffs)}.**\n',
          '| config · exit | stream | venue | session | entry | contract | exit | net $ | check |\n|---|---|---|---|---|---|---|---|---|'] + lines
    (HERE / 'out_v1' / 'verify_summary.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))
    return len(diffs)


if __name__ == '__main__':
    raise SystemExit(1 if main() else 0)
