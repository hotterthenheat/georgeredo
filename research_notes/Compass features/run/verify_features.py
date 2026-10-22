"""
verify_features.py — an independent re-derivation, with plain loops, of base trades and feature decisions from the raw
files. It does not import any module of this study or audit_lib (polars only reads files into Python rows).

It reads the screen's trade table ($SP/features_work/<split>/trades_with_inputs.parquet), draws a seeded sample of base
trades (0DTE and EOD-entry) and rebuilds each: the standing quotes at the entry, K*, the forward, the implied move, x, the
strike-bucket pick (nearest the centre, ties the lower strike), the entry ask, the fixed exit (the 15:58 bid with the
10-minute fallback, the expiry-day chain, the EOD bid of the exit session, or intrinsic on the official SPX close), the
fees and the return. Then it rebuilds feature values and decisions on another seeded sample: V1 (spread), V2 (open
interest), V3 (volume), V4 (earnings window), V5 (macro window), D1 (net premium), D4 (tide), D6 (opening range), D7 (prior
day), SD1's G, ES3's x_RM (0DTE), X1 and X3's exits. Any difference is printed; the exit code is the number of differences.

  python3 -I verify_features.py [expl|hold]
"""
import csv
import datetime as dt
import json
import math
import os
import random
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
TH = SP / 'theta'
UWD = SP / 'features_data' / 'uw'
STG = SP / 'features_data' / 'theta_staging'
SEED = 20261024
TOL = 1e-6
CENTRES = {'ITM': -0.325, 'ATM': 0.0, 'OTM1': 0.325, 'OTM2': 0.75, 'OTM3': 1.25}
BUCKET_CENTRE = {'1-7': 4, '8-30': 19, '31-60': 45}
BUCKET_RANGE = {'1-7': (1, 7), '8-30': (8, 30), '31-60': (31, 60)}


def rows_of(path, columns=None):
    return pl.read_parquet(path, columns=columns).rows(named=True)


def minute(ts):
    return ts.hour * 60 + ts.minute - 570


def num(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def stands(b, a):
    return b is not None and a is not None and b > 0 and a > 0 and a >= b


def bucket(x):
    e = 1e-12
    if -0.5 - e <= x < -0.15 - e:
        return 'ITM'
    if -0.15 - e <= x <= 0.15 + e:
        return 'ATM'
    if 0.15 + e < x <= 0.5 + e:
        return 'OTM1'
    if 0.5 + e < x <= 1.0 + e:
        return 'OTM2'
    if 1.0 + e < x <= 1.5 + e:
        return 'OTM3'
    return None


def fee(name, px):
    if px <= 0:
        return 0.0
    if name == 'SPXW':
        return 1.18748 if px < 1.0 - 1e-9 else 1.27748
    return 0.65 + 0.01248 + 0.025


def ret(name, ask, px, fee_out):
    return ((px - ask) * 100 - fee(name, ask) - fee_out) / (ask * 100)


def chain_path(name, d):
    if name in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        p = TH / 'data_full' / 'chains' / name / f'{d}.parquet'
        if p.exists():
            return p
        for q in sorted((STG / '_staging').glob(f'*/data_full/chains/{name}/{d}.parquet')):
            return q
        return None
    root = 'FB' if (name == 'META' and d <= '2022-06-08') else name
    for base in (TH / 'fetch_cache' / 'chains_exp', STG / 'fetch_cache' / 'chains_exp'):
        p = base / root / f'{d}__{d}.parquet'
        if p.exists():
            return p
    return None


def load_chain(name, d):
    """{minute: {(right, strike): (bid, ask)}} with every row (standing or not)"""
    out = {}
    for r in rows_of(chain_path(name, d), ['timestamp', 'strike', 'right', 'bid', 'ask']):
        m = minute(r['timestamp'])
        out.setdefault(m, {})[('C' if r['right'].upper().startswith('C') else 'P', round(r['strike'], 4))] = (num(r['bid']), num(r['ask']))
    return out


def fwd(book):
    """book: {(right, strike): (bid, ask)} → (K*, F, IM)"""
    ks = sorted({k for (_, k) in book})
    best = None
    for k in ks:
        c, p = book.get(('C', k)), book.get(('P', k))
        if c is None or p is None or not stands(*c) or not stands(*p):
            continue
        cm, pm = (c[0] + c[1]) / 2, (p[0] + p[1]) / 2
        d = abs(cm - pm)
        if best is None or d < best[0] - 1e-15:
            best = (d, k, cm, pm)
    if best is None:
        return None
    _, k, cm, pm = best
    return k, k + cm - pm, cm + pm


def pick(book, right, F, IM, sb):
    best = None
    for (r, k), (b, a) in sorted(book.items(), key=lambda t: t[0][1]):
        if r != right or not stands(b, a):
            continue
        x = (k - F) / IM if right == 'C' else (F - k) / IM
        if bucket(x) != sb:
            continue
        d = abs(x - CENTRES[sb])
        if best is None or d < best[0] - 1e-12:
            best = (d, k, b, a, x)
    return best


def bars_path(u, d):
    if u in ('SPY', 'QQQ', 'IWM'):
        return TH / 'data' / 'underlying' / u / f'{d}.parquet'
    root = 'FB' if (u == 'META' and d <= '2022-06-08') else u
    p = TH / 'fetch_cache' / 'underlying' / root / f'{d}.parquet'
    return p if p.exists() else STG / 'fetch_cache' / 'underlying' / root / f'{d}.parquet'


def closes(u, d):
    """{bar minute: close}; SPXW: the SPX prints"""
    out = {}
    if u == 'SPXW':
        for r in rows_of(TH / 'data' / 'index' / 'SPX' / f'{d}.parquet'):
            if num(r['price']) is not None:
                out[minute(r['timestamp'])] = r['price']
        return out
    for r in rows_of(bars_path(u, d), ['timestamp', 'close']):
        if num(r['close']) is not None:
            out[minute(r['timestamp'])] = r['close']
    return out


def hilo(u, d):
    hi, lo = {}, {}
    if u == 'SPXW':
        c = closes(u, d)
        return c, c
    for r in rows_of(bars_path(u, d), ['timestamp', 'high', 'low', 'close']):
        if num(r['close']) is not None:
            hi[minute(r['timestamp'])] = r['high']
            lo[minute(r['timestamp'])] = r['low']
    return hi, lo


def price_at(u, d, m):
    c = closes(u, d)
    if u == 'SPXW':
        return c.get(389 if m >= 390 else m)
    return c.get(m - 1)


def exit_bid(path, X, m0):
    """{minute: (bid, ask)} → the bid at X if it stands, else the last standing within the 10 minutes before (after m0), else 0"""
    for j in range(X, max(X - 10, m0 + 1) - 1, -1):
        q = path.get(j)
        if q and stands(*q):
            return q[0]
    return 0.0


def spx_closes():
    out = {}
    with open(REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-22.csv') as fh:
        for r in csv.DictReader(fh):
            mm, dd, yy = r['DATE'].split('/')
            out[f'{yy}-{mm}-{dd}'] = float(r['SPX'])
    return out


# ---- the calendar, rebuilt plainly from SPY's EOD file dates (before 2022) and the weekday rule with the holiday list -------------

HOLI = set('''2022-01-17 2022-02-21 2022-04-15 2022-05-30 2022-06-20 2022-07-04 2022-09-05 2022-11-24 2022-12-26 2023-01-02 2023-01-16
2023-02-20 2023-04-07 2023-05-29 2023-06-19 2023-07-04 2023-09-04 2023-11-23 2023-12-25 2024-01-01 2024-01-15 2024-02-19 2024-03-29
2024-05-27 2024-06-19 2024-07-04 2024-09-02 2024-11-28 2024-12-25 2025-01-01 2025-01-09 2025-01-20 2025-02-17 2025-04-18 2025-05-26
2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25 2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03
2026-09-07'''.split())
HALF = set('''2012-07-03 2012-11-23 2012-12-24 2013-07-03 2013-11-29 2013-12-24 2014-07-03 2014-11-28 2014-12-24 2015-11-27 2015-12-24
2016-11-25 2017-07-03 2017-11-24 2018-07-03 2018-11-23 2018-12-24 2019-07-03 2019-11-29 2019-12-24 2020-11-27 2020-12-24 2021-11-26
2022-11-25 2023-07-03 2023-11-24 2024-07-03 2024-11-29 2024-12-24 2025-07-03 2025-11-28 2025-12-24'''.split())
_TD = []


def tdays():
    if not _TD:
        s = set()
        for f in sorted((TH / 'fetch_cache' / 'eod_all' / 'SPY').glob('*.parquet')):
            if f.stem.split('__')[0] < '2022-01-01':
                s |= {str(r['date']) for r in rows_of(f, ['date'])}
        d = dt.date(2022, 1, 1)
        while d <= dt.date(2026, 10, 21):
            if d.weekday() < 5 and d.isoformat() not in HOLI:
                s.add(d.isoformat())
            d += dt.timedelta(days=1)
        _TD.extend(sorted(x for x in s if '2012-06-01' <= x <= '2026-10-21'))
    return _TD


def full():
    return [d for d in tdays() if d not in HALF]


def prev_td(d):
    t = tdays()
    i = max(j for j in range(len(t)) if t[j] < d)
    return t[i]


# ---- base trades ----------------------------------------------------------------------------------------------------------------------

def derive_0dte(t, closes_spx):
    name, d, m = t['name'], t['day'], t['m']
    ch = load_chain(name, d)
    f = fwd(ch.get(m, {}))
    out = {}
    if f is None:
        return {'note': 'no ATM pair'}
    Ks, F, IM = f
    out.update(F=F, IM=IM)
    p = pick(ch[m], t['right'], F, IM, t['sb'])
    if p is None:
        return {'note': 'no contract'}
    _, k, b, a, x = p
    out.update(strike=k, ask=a, bid=b, x=x)
    path = {mm: ch[mm].get((t['right'], k)) for mm in ch if ch[mm].get((t['right'], k))}
    if name == 'SPXW':
        o = closes_spx[d]
        px = max(o - k, 0) if t['right'] == 'C' else max(k - o, 0)
        fo = 0.0
    else:
        px = exit_bid(path, 388, m)
        fo = fee(name, px)
    out['exit_px'] = px
    out['r'] = ret(name, a, px, fo)
    # X1
    S = price_at(name, d, m)
    c = closes(name, d)
    lvl = S + IM if t['right'] == 'C' else S - IM
    hit = None
    if name == 'SPXW':
        for pm in range(m + 1, 389):
            v = c.get(pm)
            if v is not None and ((t['right'] == 'C' and v >= lvl) or (t['right'] == 'P' and v <= lvl)):
                hit = pm
                break
    else:
        for bm in range(m, 388):
            v = c.get(bm)
            if v is not None and ((t['right'] == 'C' and v >= lvl) or (t['right'] == 'P' and v <= lvl)):
                hit = bm + 1
                break
    if hit is None:
        out['r_x1'] = out['r']
    else:
        p1 = exit_bid(path, hit, m)
        out['r_x1'] = ret(name, a, p1, fee(name, p1))
    if m < 270:
        p3 = exit_bid(path, 270, m)
        out['r_x3'] = ret(name, a, p3, fee(name, p3))
    out['S'] = S
    return out


def eod_rows(name, d):
    for f in sorted((TH / 'fetch_cache' / 'eod_all' / name).glob('*.parquet')):
        a, b = f.stem.split('__')
        if a <= d <= b:
            return [r for r in rows_of(f, ['date', 'expiration', 'strike', 'right', 'volume', 'bid', 'ask']) if str(r['date']) == d]
    return []


def ltd(e):
    t = set(tdays())
    x = dt.date.fromisoformat(e)
    while x.isoformat() not in t:
        x -= dt.timedelta(days=1)
    return x.isoformat()


def r4(v):
    return None if v is None else round(float(v), 4)


def derive_eod(t, closes_spx):
    name, d, eb = t['name'], t['day'], t['eb']
    rows = eod_rows(name, d)
    exps = sorted({str(r['expiration']) for r in rows})
    lo, hi = BUCKET_RANGE[eb]
    best = None
    for e in exps:
        le = ltd(e)
        dte = (dt.date.fromisoformat(le) - dt.date.fromisoformat(d)).days
        if lo <= dte <= hi:
            key = (abs(dte - BUCKET_CENTRE[eb]), le)
            if best is None or key < best[0]:
                best = (key, le, e)
    if best is None:
        return {'note': 'no expiry'}
    _, le, e = best
    book = {}
    for r in rows:
        if str(r['expiration']) == e:
            book[(r['right'], r4(r['strike']))] = (r4(r['bid']), r4(r['ask']))
    f = fwd(book)
    if f is None:
        return {'note': 'no pair'}
    Ks, F, IM = f
    p = pick(book, t['right'], F, IM, t['sb'])
    if p is None:
        return {'note': 'no contract'}
    _, k, b, a, x = p
    out = dict(expiry=le, F=F, IM=IM, strike=k, ask=a, bid=b, x=x)
    fs = full()
    i = fs.index(d)
    if eb == '1-7':
        ex = le
    elif eb == '8-30':
        ex = min(fs[i + 5], max(s for s in fs if s < le))
    else:
        ex = fs[i + 10]
    out['exit_day'] = ex
    if eb == '1-7':
        if name == 'SPXW':
            o = closes_spx[le]
            px, fo = (max(o - k, 0) if t['right'] == 'C' else max(k - o, 0)), 0.0
        else:
            ch = load_chain(name, le)
            path = {mm: ch[mm].get((t['right'], k)) for mm in ch if ch[mm].get((t['right'], k))}
            px = exit_bid(path, 388, 377)
            fo = fee(name, px)
    else:
        q = None
        for r in eod_rows(name, ex):
            if str(r['expiration']) == e and r['right'] == t['right'] and abs(r4(r['strike']) - k) < 1e-6:
                q = (r4(r['bid']), r4(r['ask']))
        px = q[0] if q and stands(*q) else 0.0
        fo = fee(name, px)
    out['exit_px'] = px
    out['r'] = ret(name, a, px, fo)
    return out


# ---- feature values ---------------------------------------------------------------------------------------------------------------------

def uw_rows(route, tk, d):
    p = UWD / route / tk / f'{d}.parquet'
    return rows_of(p) if p.exists() else []


def ny_minute(ts):
    from zoneinfo import ZoneInfo
    z = ts.astimezone(ZoneInfo('America/New_York'))
    return z.hour * 60 + z.minute + z.second / 60 + z.microsecond / 6e7 - 570, z.date().isoformat()


def feat(fid, t):
    name, d, m = t['name'], t['day'], t['m']
    utk = 'SPX' if name == 'SPXW' else name
    if fid == 'V1':
        mid = (t['bid'] + t['ask']) / 2
        return (t['ask'] - t['bid']) / mid > 0.10, t['spread'] > 0.10
    if fid == 'V2':
        e = t['listed']
        sym = f"{name}{e[2:4]}{e[5:7]}{e[8:10]}{t['right']}{int(round(t['strike'] * 1000)):08d}"
        oi = None
        for r in uw_rows('oi_chain', utk, d):
            if r['option_symbol'] == sym:
                oi = r['open_interest']
        return oi, t['oi']
    if fid == 'V3':
        if t['eb'] == '0DTE':
            p = prev_td(d)
            v = None
            for r in eod_rows(name, p):
                if str(r['expiration']) == d and r['right'] == t['right'] and abs(r4(r['strike']) - t['strike']) < 1e-6:
                    v = r['volume']
            return v, t['v3vol']
        v = None
        for r in eod_rows(name, d):
            if str(r['expiration']) == t['listed'] and r['right'] == t['right'] and abs(r4(r['strike']) - t['strike']) < 1e-6:
                v = r['volume']
        return v, t['v3vol']
    if fid in ('V4', 'V5'):
        lo, hi = f'{prev_td(d)} 16:00', f"{t['expiry']} 16:00"
        if fid == 'V5':
            ev = json.loads((REPO / 'data' / 'macro_events_2022_2027.json').read_text())
            ts = [e['date'] + (' 14:00' if e['event'] == 'FOMC_DECISION' else ' 08:30') for e in ev if e['event'] in ('FOMC_DECISION', 'CPI', 'NFP')]
            return any(lo < x < hi for x in ts), t['ev_macro']
        hit = False
        for r in rows_of(REPO / 'data_lake' / 'unusualwhales' / 'earnings.parquet', ['ticker', 'report_date', 'report_time']):
            if r['ticker'] != name or r['report_date'] is None:
                continue
            rt = r['report_time']
            reads = [r['report_date'] + ' 09:30'] if rt == 'premarket' else ([r['report_date'] + ' 16:00'] if rt == 'postmarket' else
                                                                              [r['report_date'] + ' 09:30', r['report_date'] + ' 16:00'])
            if any(lo < x < hi for x in reads):
                hit = True
        return hit, t['ev_earn']
    if fid == 'SD1':
        g = None
        best = None
        for r in uw_rows('spot_exposures', utk, d):
            mm, day = ny_minute(r['start_time'])
            if day == d and mm + 1 <= m + 1e-9 and r['gamma_per_one_percent_move_oi'] is not None:
                if best is None or r['start_time'] > best:
                    best, g = r['start_time'], r['gamma_per_one_percent_move_oi']
        return g, t['G']
    if fid == 'D1':
        s, any_ = 0.0, False
        for r in uw_rows('net_prem_ticks', utk, d):
            mm, day = ny_minute(r['tape_time'])
            if day == d and 0 <= mm <= m - 1 + 1e-9:
                s += (r['net_call_premium'] or 0) - (r['net_put_premium'] or 0)
                any_ = True
        return (s if any_ else None), t['d1']
    if fid == 'D4':
        best, v = None, None
        for r in uw_rows('market_tide', 'market', d):
            mm, day = ny_minute(r['timestamp'])
            if day == d and mm + 5 <= m + 1e-9 and r['net_call_premium'] is not None:
                if best is None or r['timestamp'] > best:
                    best, v = r['timestamp'], r['net_call_premium'] - r['net_put_premium']
        return v, t['d4']
    if fid == 'D6':
        hi, lo = hilo(name, d)
        orh = max(hi[k] for k in hi if 0 <= k < 30)
        orl = min(lo[k] for k in lo if 0 <= k < 30)
        S = price_at(name, d, m)
        v = 0 if m < 45 else (1 if S > orh else (-1 if S < orl else 0))
        return v, t['d6']
    if fid == 'D7':
        p = prev_td(d)
        hi, lo = hilo(name, p)
        ph = max(hi[k] for k in hi if 0 <= k < 390)
        pl_ = min(lo[k] for k in lo if 0 <= k < 390)
        S = price_at(name, d, m)
        return (1 if S > ph else (-1 if S < pl_ else 0)), t['d7']
    if fid == 'ES3':
        fs = [x for x in full() if x < d]
        rs = []
        cl = [closes(name, x).get(389) for x in fs[-21:]]
        for a, b in zip(cl[:-1], cl[1:]):
            rs.append(math.log(b / a))
        mu = sum(rs) / len(rs)
        sd = math.sqrt(sum((x - mu) ** 2 for x in rs) / (len(rs) - 1))
        S = price_at(name, d, m)
        rm = S * sd * math.sqrt((390 - m) / 390) * math.sqrt(2 / math.pi)
        return rm / t['IM'], t['xrm']
    raise KeyError(fid)


def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, str) or isinstance(b, str):
        return str(a) == str(b)
    return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(a)))


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else 'expl'
    T = pl.read_parquet(SP / 'features_work' / split / 'trades_with_inputs.parquet')
    rng = random.Random(SEED)
    spx = spx_closes()
    diffs, detail = 0, []
    z = T.filter(pl.col('eb') == '0DTE').to_dicts()
    e = T.filter((pl.col('eb') != '0DTE') & (pl.col('day') >= '2016-01-01')).to_dicts()
    base = rng.sample(z, 35) + rng.sample(e, 20)
    for t in base:
        v = derive_0dte(t, spx) if t['eb'] == '0DTE' else derive_eod(t, spx)
        bad = [(k, v.get(k), t.get(k)) for k in v if k in t and not same(v[k], t[k]) and k != 'note']
        if 'note' in v:
            bad.append(('note', v['note'], None))
        diffs += len(bad)
        detail.append(dict(kind='base', name=t['name'], day=t['day'], m=t['m'], eb=t['eb'], sb=t['sb'], right=t['right'], checked=sorted(v), diffs=bad))
    checks = [('V1', None), ('V3', '0DTE'), ('V3', 'EOD'), ('V4', None), ('V5', None), ('D6', None), ('D7', None), ('ES3', None)]
    if T['G'].is_not_null().any():
        checks += [('SD1', None), ('D1', None), ('D4', None), ('V2', None)]
    nfeat = 0
    for fid, kind in checks:
        if fid == 'V3':
            pool = T.filter(pl.col('v3vol').is_not_null() & ((pl.col('eb') == '0DTE') if kind == '0DTE' else (pl.col('eb') != '0DTE')))
        elif fid == 'V4':
            pool = T.filter(pl.col('ev_earn').is_not_null())
            pool = pl.concat([pool.filter(pl.col('ev_earn')).head(2000), pool.filter(~pl.col('ev_earn')).head(2000)])
        elif fid == 'V5':
            pool = T.filter(pl.col('ev_macro').is_not_null())
        elif fid in ('D6', 'ES3'):
            pool = T.filter((pl.col('eb') == '0DTE') & pl.col('xrm').is_not_null() & (pl.col('m') >= 45))
        elif fid == 'D7':
            pool = T.filter(pl.col('d7').is_not_null() & (pl.col('day') >= '2017-07-01'))
        elif fid == 'SD1':
            pool = T.filter(pl.col('G').is_not_null())
        elif fid == 'D1':
            pool = T.filter(pl.col('d1').is_not_null())
        elif fid == 'D4':
            pool = T.filter(pl.col('d4').is_not_null())
        elif fid == 'V2':
            pool = T.filter(pl.col('oi').is_not_null())
        else:
            pool = T
        if pool.height == 0:
            continue
        for t in rng.sample(pool.to_dicts(), min(3, pool.height)):
            a, b = feat(fid, t)
            ok = same(a, b)
            nfeat += 1
            diffs += 0 if ok else 1
            detail.append(dict(kind='feature', fid=fid, name=t['name'], day=t['day'], m=t['m'], eb=t['eb'], right=t['right'], sb=t['sb'],
                               derived=a, table=b, ok=ok))
    res = dict(split=split, base_trades=len(base), feature_decisions=nfeat, differences=diffs, detail=detail)
    (HERE.parent / 'out' / f'verify_{split}.json').write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ('split', 'base_trades', 'feature_decisions', 'differences')}))
    for x in detail:
        if (x['kind'] == 'base' and x['diffs']) or (x['kind'] == 'feature' and not x['ok']):
            print(x)
    sys.exit(min(diffs, 255))


if __name__ == '__main__':
    main()
