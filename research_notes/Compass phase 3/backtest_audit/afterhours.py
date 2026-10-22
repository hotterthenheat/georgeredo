#!/usr/bin/env python3
"""
afterhours.py — the after-hours exercise risk the hold-to-expiry P&L leaves out, priced on the files on disk.

    cd "research_notes/Compass phase 3/backtest_audit"
    PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I afterhours.py \
        [--root ../../../data_recorder/paper_backtest] [--fee-ex 0.0] [--scratch <dir holding bt/cache, spx/ …>]

→ AFTERHOURS.md, out/afterhours_coverage.csv, out/afterhours_trades.csv, out/afterhours_summary.csv,
  out/afterhours_close_check.csv, out/afterhours_20250409.json.

Scope (the owner's spec): every hold-to-expiry trade of fly5 iron (SPY, QQQ; 15:00, 15:30) and condor_d20 (SPY,
13:00–15:00) on the sessions 2025-10-13 → 2026-10-21, period ii's overlap (→ 2026-10-09) and period iii
(2026-10-12 →) kept apart. Cases, every net stock position marked at the next session's 09:30 bar open:
  (0) intrinsic at the official close (the audit's re-settled P&L);
  (a) exercise by exception on the official close — every leg ≥ $0.01 in the money is exercised or assigned;
  (b) our longs by exception on the official close, each SHORT assigned iff ≥ $0.01 in the money at the decision price;
  (c) longs and shorts both decided at the decision price.
Decision price = the close of the last UW post-market 1-minute bar (market_time 'po') ending at or before 17:30
New York on the session's date. Never the daily 'po' row's close (20:00).

It reads files only: no vendor call, no write outside this folder's AFTERHOURS.md and out/afterhours_*. The replay rows,
scripts/ and tests/ are read, never written; the 15:58 quotes come from out/quotes_1558_cache.parquet (read only — the
parquet root is NOT handed to run_audit.build_trades, so it cannot rewrite that cache). Every bootstrap is seeded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_lib as A  # noqa: E402
import run_audit as RA  # noqa: E402

f, ci = A.f, A.ci
NY = ZoneInfo('America/New_York')
SCOPE_START, SCOPE_END = '2025-10-13', '2026-10-21'
PERIODS = [('ii', "period ii, its overlap with the post-market bars", SCOPE_START, A.HIST_END),
           ('iii', 'period iii, untouched forward', A.FORWARD_START, SCOPE_END)]
CANDS = [('fly5', 'iron', 'fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30)'),
         ('condor_d20', 'condor', 'condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00)')]
SEED = 20261016                 # the owner's seed for the block bootstrap (audit_lib.block_draws adds 7919 × block)
BLOCK = 20
CUTOFF = (17, 30)
COVER_MIN = 0.5                 # under half a period's sessions with a decision price: the rule is not applied there
CASES = ('0', 'a', 'b', 'c')
DIFFS = (('a-0', 'a', '0'), ('b-a', 'b', 'a'), ('c-b', 'c', 'b'))
UW_DIRS = ('bt/cache', 'audit_fresh_cache', 'bt/probe', 'evidence/provider_tests')
UW_RX = re.compile(r'stock_(SPY|QQQ)_ohlc_1m_date[-_](\d{4}-\d\d-\d\d)')
CLOSE_GAP = 0.25
PM_CACHE = A.REPO / 'data' / 'postmarket_1m'


# ---- small pieces ------------------------------------------------------------------------------------------------------------------------

def itm(px: float, k: float, r: str) -> bool:
    """≥ $0.01 in the money (OCC's exercise-by-exception threshold); prices in cents or UW's four decimals"""
    return A.intrinsic(px, k, r) >= 0.01 - 1e-9


def next_session(d: str) -> str:
    """the next NYSE session (half days included: they open at 09:30)"""
    x = dt.date.fromisoformat(d)
    while True:
        x += dt.timedelta(days=1)
        if x.weekday() < 5 and x.isoformat() not in A.NYSE_HOLIDAYS:
            return x.isoformat()


def ny(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(NY)


def money(x, d=0):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    return f'{x:+,.{d}f}'


def pct(x, d=1):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{100 * x:.{d}f}%'


def md_table(head, rows):
    return ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]


# ---- the post-market minute bars ----------------------------------------------------------------------------------------------------------

def uw_minute_files(scratch: Path | None, recorder: Path) -> dict:
    """{(name, day): [(source label, rows, fetched_at NY or None)]} from every UW 1-minute answer found on disk"""
    out: dict = defaultdict(list)
    for p in sorted(PM_CACHE.glob('*/*.json.gz')):        # fetched for this study (fetch_postmarket_1m.py), kept as answered
        out[(p.parent.name, p.name[:10])].append((f'data/postmarket_1m/{p.parent.name}/{p.name}', json.loads(gzip.open(p).read())['data'], None))
    if scratch is not None:
        for sub in UW_DIRS:
            d = scratch / sub
            if not d.is_dir():
                continue
            for p in sorted(d.iterdir()):
                m = UW_RX.search(p.name)
                if not m or p.suffix == '.headers':
                    continue
                raw = gzip.open(p).read() if p.suffix == '.gz' else p.read_bytes()
                try:
                    rows = json.loads(raw)['data']
                except (ValueError, KeyError, TypeError):
                    continue
                out[(m[1], m[2])].append((f'{sub}/{p.name}', rows, None))
    for nm in ('SPY', 'QQQ'):
        d = recorder / nm
        for p in sorted(d.glob('*.parquet')) if d.is_dir() else []:
            t = pl.read_parquet(p)
            fetched = max(ny(x) for x in t['_fetched_at'].to_list()) if '_fetched_at' in t.columns and t.height else None
            out[(nm, p.stem)].append((f'data_recorder/ohlc_1m/{nm}/{p.name}', t.select('start_time', 'end_time', 'open', 'high', 'low', 'close',
                                                                                      'market_time').to_dicts(), fetched))
    return out


def decision_of(day: str, rows: list, fetched) -> dict:
    """the last 'po' bar of `day` (New York) ending at or before 17:30, and whether the file proves it was taken after
    17:30 (a bar of the day ending after 17:30, or its fetch time) — a file taken earlier cannot name the last bar"""
    cut = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(*CUTOFF), NY)
    po, after = [], False
    for r in rows:
        s, e = ny(r['start_time']), ny(r['end_time'])
        if s.date().isoformat() != day:
            continue                                 # UW files a winter session by its UTC date: the evening before rides along
        if e > cut:
            after = True
        if r['market_time'] == 'po' and e <= cut:
            po.append((e, float(r['close'])))
    complete = after or (fetched is not None and fetched >= cut)
    if not po:
        return {'px': None, 'end': None, 'complete': complete, 'note': 'no post-market bar ending at or before 17:30 in the file'}
    e, c = max(po)
    if not complete:
        tail = f'file taken {fetched.strftime("%H:%M")} New York' if fetched else 'no bar after 17:30 in the file'
        return {'px': None, 'end': e.strftime('%H:%M'), 'seen': c, 'complete': False,
                'note': f'{tail}: the last bar to 17:30 is not known (last seen {e.strftime("%H:%M")} at {c})'}
    return {'px': c, 'end': e.strftime('%H:%M'), 'complete': True, 'note': ''}


def uw_daily(market_time: str, symbols=('SPY', 'QQQ')) -> dict:
    fs = sorted((A.REPO / 'data_lake' / 'unusualwhales').glob('ohlc__1d.part0*.parquet')) + sorted((A.REPO / 'data' / 'official_closes').glob('uw_ohlc_1d_*.parquet'))
    out = {}
    for p in fs:
        t = pl.scan_parquet(p).filter(pl.col('ticker').is_in(list(symbols)) & (pl.col('market_time') == market_time)).select('ticker', 'date', 'open', 'high', 'low', 'close').collect()
        for r in t.to_dicts():
            out[(r['ticker'], r['date'])] = {k: float(r[k]) for k in ('open', 'high', 'low', 'close')}
    return out


def bar_at(path: Path, h: int, m: int, field: str):
    if not path.exists():
        return None
    t = pl.read_parquet(path).filter((pl.col('timestamp').dt.hour() == h) & (pl.col('timestamp').dt.minute() == m))
    if t.height == 0:
        return None
    v = t[field][0]
    return float(v) if v is not None and math.isfinite(float(v)) else None


# ---- the cases ---------------------------------------------------------------------------------------------------------------------------

def case_pnl(legs, entry: float, C: float, D, O, case: str, fee_ex: float):
    """→ (P&L $, contracts exercised or assigned, net shares) or None when the case needs a price that is missing.
    An exercised or assigned leg is replaced by stock at its strike marked at the next open O: + (O − K) a long call,
    + (K − O) a long put, the negatives for a short; a leg not exercised expires worthless. Fees as the replay
    ($0.65 × 4 at the open) plus `fee_ex` a contract exercised or assigned."""
    base = A.CONTRACTS * A.FEE
    if case == '0':
        return (entry + A.payoff(legs, C)) * 100 - base, 0, 0
    const, coef, nex = 0.0, 0, 0
    for r, k, side, q in legs:
        px = C if (case == 'a' or (case == 'b' and side == 'long')) else D
        if px is None:
            return None
        if not itm(px, k, r):
            continue
        s = (1 if side == 'long' else -1) * q
        const += s * (-k if r == 'C' else k)
        coef += s * (1 if r == 'C' else -1)
        nex += q
    if coef != 0 and O is None:
        return None
    return (entry + const + coef * (O or 0.0)) * 100 - base - fee_ex * nex, nex, coef * 100


# ---- statistics --------------------------------------------------------------------------------------------------------------------------

def weights(n: int):
    if n < 3 * BLOCK:                           # audit_lib's rule: no block-20 interval under 60 sessions
        return None
    return A.weights_from(A.block_draws(n, BLOCK, A.BOOT_N, seed=SEED), n)


def stat(S: np.ndarray, N: np.ndarray, W) -> dict:
    n, nt = S.size, N.sum()
    o = {'sessions': int(n), 'trades': int(nt), 'mean_trade': float(S.sum() / nt) if nt else float('nan'),
         'mean_session': float(S.mean()) if n else float('nan'), 'total': float(S.sum())}
    if W is None or nt == 0:
        o['ci_trade'] = o['ci_session'] = (float('nan'), float('nan'))
    else:
        o['ci_trade'] = A.pct_ci((W @ S) / np.maximum(W @ N, 1))
        o['ci_session'] = A.pct_ci((W @ S) / n)
    return o


def tails(x: np.ndarray) -> dict:
    if x.size == 0:
        return {'p5': float('nan'), 'p1': float('nan'), 'worst': float('nan')}
    return {'p5': float(np.percentile(x, 5)), 'p1': float(np.percentile(x, 1)), 'worst': float(x.min())}


# ---- the close check -------------------------------------------------------------------------------------------------------------------------

def spx_closes(scratch: Path | None) -> tuple[dict, dict]:
    cb, fr = {}, {}
    if scratch is None:
        return cb, fr
    p = scratch / 'spx' / 'cboe_spx.csv'
    if p.exists():
        for line in p.read_text().splitlines()[1:]:
            a, b = line.split(',')
            mm, dd, yy = a.split('/')
            cb[f'{yy}-{mm}-{dd}'] = float(b)
    p = scratch / 'spx' / 'fred_sp500.csv'
    if p.exists():
        for line in p.read_text().splitlines()[1:]:
            a, b = line.split(',')
            if b.strip() and b.strip() != '.':
                fr[a] = float(b)
    return cb, fr


def second_sources(nm: str, d: str, c59: float, pr: Path, scratch: Path | None, eod: dict, spx: tuple, eod_days: list) -> dict:
    """values of the official close implied by other files on disk (labelled by how independent they are)"""
    o: dict = {}
    u = pr / 'data' / 'underlying' / nm / f'{d}.parquet'
    o['theta_1m_1600_bar'] = bar_at(u, 16, 0, 'close')
    fc = (scratch / 'theta' / 'fetch_cache' / 'underlying') if scratch is not None else None
    if nm == 'SPY':
        cb, fr = spx
        s16 = bar_at(pr / 'data' / 'index' / 'SPX' / f'{d}.parquet', 16, 0, 'price')
        s59 = bar_at(pr / 'data' / 'index' / 'SPX' / f'{d}.parquet', 15, 59, 'price')
        sp = s16 if s16 is not None else s59
        o['spx_cboe'], o['spx_fred'], o['spx_print_1600'] = cb.get(d), fr.get(d), sp
        o['spx_anchored'] = c59 * cb[d] / sp if sp and cb.get(d) else None
        for sib in ('IVV', 'VOO'):
            e = eod.get((sib, d))
            s = bar_at(fc / sib / f'{d}.parquet', 15, 59, 'close') if fc else None
            o[f'{sib.lower()}_anchored'] = c59 * e / s if e and s else None
    else:
        for sib, lev in (('TQQQ', 3.0), ('SQQQ', -3.0)):
            e = eod.get((sib, d))
            s = bar_at(fc / sib / f'{d}.parquet', 15, 59, 'close') if fc else None
            o[f'{sib.lower()}_anchored'] = c59 * (1 + (e / s - 1) / lev) if e and s else None
        # QQQM has no minute file: its EOD close × the median QQQ/QQQM EOD ratio of the five sessions either side
        i = eod_days.index(d) if d in eod_days else None
        q = eod.get(('QQQM', d))
        if i is not None and q:
            near = [x for x in eod_days[max(0, i - 5):i] + eod_days[i + 1:i + 6] if eod.get(('QQQ', x)) and eod.get(('QQQM', x))]
            o['qqqm_ratio'] = q * float(np.median([eod[('QQQ', x)] / eod[('QQQM', x)] for x in near])) if near else None
    return o


# ---- main ------------------------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--root', default=str(A.REPO / 'data_recorder' / 'paper_backtest'))
    p.add_argument('--parquet-root', default=os.environ.get('PAPER_PARQUET_ROOT'))
    p.add_argument('--scratch', help='the folder holding bt/cache, audit_fresh_cache, spx/, theta/ (default: the parquet root\'s parent)')
    p.add_argument('--recorder', default=str(A.REPO / 'data_recorder' / 'ohlc_1m'))
    p.add_argument('--fee-ex', type=float, default=0.0, help='$ a contract exercised or assigned (default 0)')
    a = p.parse_args(argv)
    if not a.parquet_root:
        sys.exit('PAPER_PARQUET_ROOT (or --parquet-root) is required: the next-session opens are its 1-minute underlying files')
    root, pr = Path(a.root).resolve(), Path(a.parquet_root)
    scratch = Path(a.scratch) if a.scratch else pr.parent
    out = A.OUT
    out.mkdir(parents=True, exist_ok=True)

    days_all = RA.replayed_days(root)
    off, off_src, _ = RA.official_closes()
    po_daily = uw_daily('po')
    r_daily = uw_daily('r')

    # 1. coverage, name-session by name-session -----------------------------------------------------------------------------------------
    uwm = uw_minute_files(scratch, Path(a.recorder))
    scope_days = [d for d in days_all if SCOPE_START <= d <= SCOPE_END]
    cov, COV = [], {}
    dup_disagree = 0
    overlap = [0, 0]
    for d in scope_days:
        per = next(pc for pc, _, lo, hi in PERIODS if lo <= d <= hi)
        nd = next_session(d)
        for nm in ('SPY', 'QQQ'):
            srcs = uwm.get((nm, d), [])
            decs = [(lab, decision_of(d, rows, fe)) for lab, rows, fe in srcs]
            good = [(lab, x) for lab, x in decs if x['px'] is not None]
            if len({x['px'] for _, x in good}) > 1:
                dup_disagree += 1
            if len(srcs) > 1:                              # bars two files both hold must agree
                bars = [{(r['start_time'], r['market_time']): r['close'] for r in rows} for _, rows, _ in srcs]
                for b2 in bars[1:]:
                    common = set(bars[0]) & set(b2)
                    overlap[0] += len(common)
                    overlap[1] += sum(float(bars[0][k]) != float(b2[k]) for k in common)
            lab, dec = good[0] if good else ((decs[0][0], decs[0][1]) if decs else (None, {'px': None, 'end': None, 'note': 'no UW 1-minute answer for this session on disk'}))
            O = bar_at(pr / 'data' / 'underlying' / nm / f'{nd}.parquet', 9, 30, 'open')
            pod = po_daily.get((nm, d))
            row = {'name': nm, 'day': d, 'period': per, 'official': off.get((nm, d)), 'official_src': off_src.get((nm, d)),
                   'uw_r_close': r_daily.get((nm, d), {}).get('close'),
                   'decision_px': dec['px'], 'decision_bar_end': dec.get('end'), 'decision_src': lab, 'decision_note': dec['note'],
                   'decision_files': len(srcs), 'po_daily_low': pod['low'] if pod else None, 'po_daily_high': pod['high'] if pod else None,
                   'po_daily_close_20h': pod['close'] if pod else None,
                   'decision_in_po_range': (pod['low'] - 1e-9 <= dec['px'] <= pod['high'] + 1e-9) if (pod and dec['px'] is not None) else None,
                   'next_session': nd, 'next_open_0930': O,
                   'next_open_note': '' if O is not None else f'no 09:30 bar for {nd} on disk ({nm}/{nd}.parquet)'}
            cov.append(row)
            COV[(nm, d)] = row
    pl.DataFrame(cov, infer_schema_length=None).write_csv(out / 'afterhours_coverage.csv')

    # 2. the trades ------------------------------------------------------------------------------------------------------------------------
    df = A.load_rows(root, keys=('fly5', 'condor_d20'), start=SCOPE_START, end=SCOPE_END)
    tr, _oc = RA.build_trades(df, None, out)          # parquet root withheld: the 15:58 cache is read, never rewritten
    want = {(k, s) for k, s, _ in CANDS}
    T = [t for t in tr if t.get('settled') and (t['key'], t['structure']) in want and t['day'] in set(scope_days)]
    check0 = 0
    for t in T:
        c = COV[(t['name'], t['day'])]
        t['ah_period'] = c['period']
        entry = t['price_nbbo'] if t['package'] == 'credit' else -t['price_nbbo']
        C = t['official']
        for cs in CASES:
            r = case_pnl(t['legs'], entry, C, c['decision_px'], c['next_open_0930'], cs, a.fee_ex)
            t[f'pnl_{cs}'], t[f'ex_{cs}'], t[f'sh_{cs}'] = r if r is not None else (None, None, None)
        check0 += abs(t['pnl_0'] - t['pnl_nbbo']) > 1e-6
        pod = po_daily.get((t['name'], t['day']))
        if pod:
            lo, hi = min(pod['low'], C), max(pod['high'], C)
            t['po_range_flag'] = any(lo <= k <= hi and itm(lo, k, r) != itm(hi, k, r) for r, k, side, q in t['legs'] if side == 'short')
        else:
            t['po_range_flag'] = None
        D = c['decision_px']
        t['short_flip_at_D'] = (any(itm(C, k, r) != itm(D, k, r) for r, k, side, q in t['legs'] if side == 'short') if D is not None else None)
    rows = [{'candidate': t['key'], 'structure': t['structure'], 'name': t['name'], 'day': t['day'], 'minute': t['minute'], 'period': t['ah_period'],
             'legs': json.dumps(t['legs']), 'package': t['package'], 'price_nbbo': t['price_nbbo'], 'official': t['official'],
             'decision_px': COV[(t['name'], t['day'])]['decision_px'], 'next_open_0930': COV[(t['name'], t['day'])]['next_open_0930'],
             **{f'pnl_{cs}': t[f'pnl_{cs}'] for cs in CASES}, **{f'contracts_exercised_{cs}': t[f'ex_{cs}'] for cs in 'abc'},
             **{f'net_shares_{cs}': t[f'sh_{cs}'] for cs in 'abc'}, 'pnl_1558': t.get('pnl_1558'), 'pnl_replay_official': t['pnl_nbbo'],
             'po_range_flag_upper_bound': t['po_range_flag'], 'short_itm_differs_close_vs_decision': t['short_flip_at_D']} for t in T]
    pl.DataFrame(rows, infer_schema_length=None).sort('candidate', 'day', 'name', 'minute').write_csv(out / 'afterhours_trades.csv')

    # 3. per candidate, per period --------------------------------------------------------------------------------------------------------
    res, summ = [], []
    for key, struct, label in CANDS:
        names = A.NAMES[key]
        for pc, plabel, lo, hi in PERIODS:
            P = [d for d in scope_days if lo <= d <= hi]
            no_open = [d for d in P if any(COV[(nm, d)]['next_open_0930'] is None for nm in names)]
            Ua = [d for d in P if d not in no_open]
            no_dec = [d for d in P if any(COV[(nm, d)]['decision_px'] is None for nm in names)]
            Ub = [d for d in Ua if d not in no_dec]
            X = [t for t in T if t['key'] == key and t['structure'] == struct and lo <= t['day'] <= hi]
            r = {'key': key, 'structure': struct, 'label': label, 'period': pc, 'plabel': plabel, 'from': lo, 'to': hi,
                 'sessions': len(P), 'no_open': no_open, 'no_dec': no_dec, 'Ua': len(Ua), 'Ub': len(Ub),
                 'coverage_b': len(Ub) / len(P) if P else 0.0, 'trades_all': len(X)}
            for uname, U, cases in (('A', Ua, ('0', 'a')), ('B', Ub, CASES)):
                ix = {d: i for i, d in enumerate(U)}
                xs = [t for t in X if t['day'] in ix]
                assert all(t[f'pnl_{cs}'] is not None for t in xs for cs in cases), 'a case left without a price inside its universe'
                n = len(U)
                W = weights(n)
                N = np.zeros(n)
                for t in xs:
                    N[ix[t['day']]] += 1
                ser = {}
                for cs in cases:
                    S = np.zeros(n)
                    for t in xs:
                        S[ix[t['day']]] += t[f'pnl_{cs}']
                    ser[cs] = S
                    st = stat(S, N, W)
                    st['affected'] = float(np.mean([abs(t[f'pnl_{cs}'] - t['pnl_0']) > 0.005 for t in xs])) if xs and cs != '0' else float('nan')
                    r[f'{uname}_{cs}'] = st
                    summ.append({'candidate': key, 'structure': struct, 'period': pc, 'universe': uname, 'series': cs, **{k: (json.dumps(v) if isinstance(v, tuple) else v) for k, v in st.items()}})
                for dname, x1, x0 in DIFFS:
                    if x1 not in cases:
                        continue
                    S = ser[x1] - ser[x0]
                    st = stat(S, N, W)
                    per_trade = np.array([t[f'pnl_{x1}'] - t[f'pnl_{x0}'] for t in xs])
                    st.update({'affected': float(np.mean(np.abs(per_trade) > 0.005)) if xs else float('nan'), 'affected_n': int((np.abs(per_trade) > 0.005).sum()),
                               **{f'trade_{k}': v for k, v in tails(per_trade).items()}, **{f'session_{k}': v for k, v in tails(S[N > 0]).items()}})
                    r[f'{uname}_{dname}'] = st
                    summ.append({'candidate': key, 'structure': struct, 'period': pc, 'universe': uname, 'series': dname, **{k: (json.dumps(v) if isinstance(v, tuple) else v) for k, v in st.items()}})
                # the 15:58 exit on the same trades (those with a 15:58 value)
                S58, N58 = np.zeros(n), np.zeros(n)
                for t in xs:
                    if t.get('pnl_1558') is not None:
                        S58[ix[t['day']]] += t['pnl_1558']
                        N58[ix[t['day']]] += 1
                st = stat(S58, N58, W)
                st['missing'] = int(N.sum() - N58.sum())
                r[f'{uname}_1558'] = st
                summ.append({'candidate': key, 'structure': struct, 'period': pc, 'universe': uname, 'series': '1558', **{k: (json.dumps(v) if isinstance(v, tuple) else v) for k, v in st.items()}})
                fl = [t['po_range_flag'] for t in xs if t['po_range_flag'] is not None]
                r[f'{uname}_po_flag'] = (float(np.mean(fl)) if fl else float('nan'), len(fl))
                fz = [t['short_flip_at_D'] for t in xs if t['short_flip_at_D'] is not None]
                r[f'{uname}_flipD'] = (float(np.mean(fz)) if fz else float('nan'), len(fz))
            # the rule, fixed by the owner before any number was read: drop if mean(b) ≤ 0 or its block-20 interval holds 0.
            # Its measure, fixed here before the run: the mean $ a trade (Σ ÷ Σ, AUDIT.md's headline measure) and its
            # 20-session block-bootstrap interval; the session-mean version is printed beside it as a check.
            b = r['B_b']
            if r['coverage_b'] < COVER_MIN:
                r['verdict'] = 'NOT APPLIED'
                r['why'] = f'decision price on {len(Ub)} of {len(P)} sessions ({pct(r["coverage_b"])}), under half'
            elif not all(math.isfinite(v) for v in b['ci_trade']):
                # the rule is an OR: a mean ≤ 0 decides on its own; a positive mean needs the interval, which cannot be formed
                if b['mean_trade'] <= 0:
                    r['verdict'] = 'DROP'
                    r['why'] = (f'mean under (b) {money(b["mean_trade"], 2)} a trade ≤ 0 — the rule\'s first clause decides alone; the block-20 '
                                f'interval cannot be formed on {len(Ub)} sessions (needs {3 * BLOCK})')
                else:
                    r['verdict'] = 'UNDECIDED'
                    r['why'] = (f'mean under (b) {money(b["mean_trade"], 2)} a trade > 0, and the block-20 interval the second clause needs cannot be formed '
                                f'on {len(Ub)} sessions (needs {3 * BLOCK})')
            else:
                lo_, hi_ = b['ci_trade']
                drop = b['mean_trade'] <= 0 or (lo_ <= 0 <= hi_)
                r['verdict'] = 'DROP' if drop else 'KEEP'
                r['why'] = f'mean under (b) {money(b["mean_trade"], 2)} a trade, block-20 {ci(b["ci_trade"])}'
                ls, hs = b['ci_session']
                r['verdict_session'] = 'DROP' if (b['mean_session'] <= 0 or ls <= 0 <= hs) else 'KEEP'
            res.append(r)
    pl.DataFrame(summ, infer_schema_length=None).write_csv(out / 'afterhours_summary.csv')

    # 4. the close check: 2025-04-09 and every pre-2025-10-13 session with |official − 15:59| > $0.25 ------------------------------------
    eod_syms = ('SPY', 'QQQ', 'IVV', 'VOO', 'TQQQ', 'SQQQ', 'QQQM')
    e = A.theta_eod(eod_syms)
    eod = {(r['symbol'], r['day']): r['close_theta'] for r in e.to_dicts()}
    eod_days = sorted({d for (s, d) in eod if s == 'SPY'})
    spx = spx_closes(scratch)
    ss_csv = A.OUT / 'settlement_sessions.csv'
    ss = {(r['name'], r['day']): r['close_1559'] for r in pl.read_csv(ss_csv, infer_schema_length=None).to_dicts()} if ss_csv.exists() else {}
    pre_days = [d for d in days_all if d < SCOPE_START]
    close_rows, agree59, n59 = [], 0, 0
    for d in pre_days:
        for nm in ('SPY', 'QQQ'):
            c59 = bar_at(pr / 'data' / 'underlying' / nm / f'{d}.parquet', 15, 59, 'close')
            o = off.get((nm, d))
            if (nm, d) in ss and c59 is not None:
                n59 += 1
                agree59 += abs(ss[(nm, d)] - c59) < 1e-9
            if c59 is None or o is None or abs(o - c59) <= CLOSE_GAP:
                continue
            sec = second_sources(nm, d, c59, pr, scratch, eod, spx, eod_days)
            vals = [v for k, v in sec.items() if k.endswith(('_anchored', '_ratio')) and v is not None]
            med = float(np.median(vals)) if vals else None
            close_rows.append({'name': nm, 'day': d, 'official': o, 'official_src': off_src.get((nm, d)), 'uw_daily_close': r_daily.get((nm, d), {}).get('close'),
                               'close_1559': c59, 'official_minus_1559': o - c59, **sec, 'second_median': med,
                               'second_nearer': (None if med is None else ('official' if abs(med - o) < abs(med - c59) else '15:59 bar')),
                               'official_minus_second_median': (o - med) if med is not None else None})
    cdf = pl.DataFrame(close_rows, infer_schema_length=None).sort('name', 'day')
    cdf.write_csv(out / 'afterhours_close_check.csv')

    # 2025-04-09 in full
    D0 = '2025-04-09'
    near = [x for x in eod_days if x != D0 and abs((dt.date.fromisoformat(x) - dt.date.fromisoformat(D0)).days) <= 8]
    ratios = {x: eod[('SPY', x)] / spx[0][x] for x in near if spx[0].get(x) and eod.get(('SPY', x))}
    eodrow = pl.concat([pl.scan_parquet(p).filter(pl.col('symbol').is_in(['SPY', 'QQQ']) & (pl.col('created').dt.strftime('%Y-%m-%d') == D0)).collect()
                        for p in sorted((A.REPO / 'data_lake' / 'thetadata' / 'stock_eod').glob('year=2025/*.parquet'))])
    u0 = pl.read_parquet(pr / 'data' / 'underlying' / 'SPY' / f'{D0}.parquet')
    c59_0 = bar_at(pr / 'data' / 'underlying' / 'SPY' / f'{D0}.parquet', 15, 59, 'close')
    sec0 = second_sources('SPY', D0, c59_0, pr, scratch, eod, spx, eod_days)
    q59 = bar_at(pr / 'data' / 'underlying' / 'QQQ' / f'{D0}.parquet', 15, 59, 'close')
    j0 = {'day': D0, 'theta_eod': [{k: (str(v) if isinstance(v, dt.datetime) else v) for k, v in r.items()} for r in eodrow.to_dicts()],
          'spy_1m_last_bars': [{k: (str(v) if isinstance(v, dt.datetime) else v) for k, v in r.items()} for r in u0.tail(3).to_dicts()],
          'spy_1m_high_of_day': float(u0['high'].max()), 'spy_close_1559': c59_0, 'second_sources': sec0,
          'spy_spx_ratio_nearby': ratios, 'ratio_median': float(np.median(list(ratios.values()))) if ratios else None,
          'ratio_implied': float(np.median(list(ratios.values()))) * spx[0][D0] if ratios and spx[0].get(D0) else None,
          'qqq_official': off.get(('QQQ', D0)), 'qqq_close_1559': q59,
          'ivv_eod': eod.get(('IVV', D0)), 'voo_eod': eod.get(('VOO', D0)),
          'ivv_1559': bar_at(scratch / 'theta' / 'fetch_cache' / 'underlying' / 'IVV' / f'{D0}.parquet', 15, 59, 'close'),
          'voo_1559': bar_at(scratch / 'theta' / 'fetch_cache' / 'underlying' / 'VOO' / f'{D0}.parquet', 15, 59, 'close'),
          'uw_daily': r_daily.get(('SPY', D0)), 'uw_minute_files': len(uwm.get(('SPY', D0), []))}
    # what the day's trades moved on the re-settlement: official 548.62 against the second sources' median
    d0df = A.load_rows(root, start=D0, end=D0)
    t0, _ = RA.build_trades(d0df, None, out)
    alt = float(np.median([v for k, v in sec0.items() if k.endswith('_anchored') and v is not None]))
    j0['alt_close'] = alt
    stake = defaultdict(lambda: [0, 0.0, 0.0])
    for t in t0:
        if not t.get('settled') or t['name'] != 'SPY':
            continue
        s = stake[f"{t['key']} {t['structure']}"]
        s[0] += 1
        s[1] += t['pnl_nbbo']
        s[2] += t['pnl_nbbo'] + (A.payoff(t['legs'], alt) - A.payoff(t['legs'], t['official'])) * 100
    j0['stake'] = {k: {'trades': v[0], 'total_at_official': v[1], 'total_at_second_median': v[2]} for k, v in sorted(stake.items())}
    (out / 'afterhours_20250409.json').write_text(json.dumps(j0, indent=1, default=str), encoding='utf-8')

    write_md(a, res, cov, COV, T, scope_days, dup_disagree, check0, cdf, j0, agree59, n59, scratch, pr, overlap)
    print('afterhours written')
    return 0


# ---- the report ----------------------------------------------------------------------------------------------------------------------------

def write_md(a, res, cov, COV, T, scope_days, dup_disagree, check0, cdf, j0, agree59, n59, scratch, pr, overlap):
    L = []
    w = L.append
    npm = len(list(PM_CACHE.glob('*/*.json.gz')))
    w('# After-hours exercise risk of the hold-to-expiry trades, 2025-10-13 → 2026-10-21')
    w('')
    w('Written by `afterhours.py` in this folder. It reads the replay\'s rows (`data_recorder/paper_backtest`, read only), the official closes as '
      '`run_audit.official_closes()` builds them (Theta EOD, UW daily `r` rows incl. `data/official_closes/`), UW\'s 1-minute answers already on disk '
      f'(`{"`, `".join(UW_DIRS)}` under the scratch folder, and `data_recorder/ohlc_1m/`), UW\'s daily `po` rows, the next sessions\' 1-minute bars '
      '(`$PAPER_PARQUET_ROOT/data/underlying`) and the 15:58 quotes the audit cached (`out/quotes_1558_cache.parquet`). It calls no vendor. The '
      f'UW 1-minute answers missing from disk were fetched once, with the owner\'s leave, by `fetch_postmarket_1m.py` ({npm} name-sessions, one call at a '
      'time, kept as answered under `data/postmarket_1m/<T>/<D>.json.gz`); a re-run reads those files and makes no call. Exercise / assignment fee: ${a.fee_ex:.2f} a contract (`--fee-ex`). Bootstraps: moving blocks of {BLOCK} sessions, {A.BOOT_N:,} draws, '
      f'`audit_lib.block_draws(n, {BLOCK}, seed={SEED})`, the same draws for every series of a candidate-period (so differences are paired). '
      'Periods are never pooled.')
    w('')
    # summary
    w('## Summary')
    w('')
    ii = [r for r in res if r['period'] == 'ii']
    iii = [r for r in res if r['period'] == 'iii']
    nii = ii[0]['sessions'] if ii else 0
    def dcov(pc):
        cc = [c for c in cov if c['period'] == pc]
        return sum(c['decision_px'] is not None for c in cc), len(cc)
    w(f'- **Decision-price coverage** (name-sessions with the last post-market bar to 17:30): period ii\'s overlap {"/".join(map(str, dcov("ii")))} '
      f'(UW 1-minute answers already on disk, `bt/cache`), period iii {"/".join(map(str, dcov("iii")))} ({npm} fetched for this study into '
      '`data/postmarket_1m/`). The next session\'s 09:30 open is missing only for 2026-10-21 (2026-10-22 is not on disk), so that session is left out '
      'of every case table and period iii has 7 sessions with a next open — too few for a 20-session block interval (60 needed): there the rule '
      'is decided by its first clause alone where the mean under (b) is ≤ 0, and left undecided where it is positive. UW answered every name-session '
      'asked of it.')
    for r in res:
        A_, B_ = r.get('A_a-0'), r.get('B_b-a')
        bits = [f'**{r["label"]}, period {r["period"]}** ({r["Ua"]} sessions with a next open): (0) {money(r["A_0"]["mean_trade"], 2)} a trade, '
                f'(a) {money(r["A_a"]["mean_trade"], 2)}, a−0 {money(A_["mean_trade"], 2)} {ci(A_["ci_trade"])}']
        if r['Ub']:
            bits.append(f'(b) {money(r["B_b"]["mean_trade"], 2)} {ci(r["B_b"]["ci_trade"])}, (c) {money(r["B_c"]["mean_trade"], 2)}, b−a {money(B_["mean_trade"], 2)} {ci(B_["ci_trade"])}')
        bits.append(f'15:58 exit {money(r["A_1558"]["mean_trade"], 2)}')
        bits.append(f'rule: **{r["verdict"]}** ({r["why"]})')
        w('- ' + '; '.join(bits) + '.')
    v = j0
    w(f'- **SPY on 2025-04-09.** Theta EOD\'s 548.62 is not confirmed by any second source on disk: SPX\'s official close (Cboe and FRED, '
      f'{v["second_sources"]["spx_cboe"]:.2f}) anchored on SPY\'s 15:59 bar gives {v["second_sources"]["spx_anchored"]:.2f}, the SPY/SPX ratio of the sessions '
      f'around it {v["ratio_implied"]:.2f}, IVV and VOO anchored {v["second_sources"]["ivv_anchored"]:.2f} and {v["second_sources"]["voo_anchored"]:.2f}; '
      f'548.62 is also the EOD row\'s high of the day (section 5).' if v['ratio_implied'] and v['second_sources'].get('spx_anchored') else '- 2025-04-09: see section 5.')
    nn = cdf.height
    w(f'- **Pre-2025-10-13 sessions with |official − 15:59| > $0.25:** {nn} name-sessions, every one with its official source (Theta EOD) and the second '
      'sources on disk (section 6).')
    w('')
    w('The decision rule was fixed by the owner before any of these numbers were read: *"if a candidate\'s mean under (b) is ≤ 0 or its block-20 '
      'interval includes zero, drop it as a SPY/QQQ hold-to-expiry strategy."* Its measure was fixed in the code before the run (the mean $ a trade, Σ ÷ Σ, '
      'AUDIT.md\'s headline measure, with its 20-session block-bootstrap interval); it is applied mechanically below and not reinterpreted.')
    w('')

    # 1. coverage
    w('## 1. Post-market bars: what is on disk')
    w('')
    w('UW\'s daily bars (`ohlc__1d`, `data/official_closes/uw_ohlc_1d_*.parquet`) carry ONE post-market row a session (`market_time = po`: the open, '
      'high, low and close of 16:00–20:00). They cannot give "the last bar at or before 17:30" and are not used for it. Minute bars with `po` rows exist '
      'on disk only as UW 1-minute answers (`/api/stock/{T}/ohlc/1m?date=D`, `start_time`/`end_time` in UTC): the backtest fetch cache '
      '(`bt/cache`, 2025-05-22 → 2026-10-09), the audit\'s fresh cache, two probe folders, the recorder\'s `data_recorder/ohlc_1m/{SPY,QQQ}/` (2026-10-21 '
      'only, taken at 17:24 New York) and, for period iii, the answers fetched for this study (`data/postmarket_1m/`). Theta\'s '
      '1-minute underlying files stop at the 16:00 bar. A disk-wide search for other minute post-market files found none.')
    w('')
    w('Rules applied: a bar belongs to session D when its start is on D in New York (UW files a winter session by its UTC date, so the evening before '
      'rides along in the file — 19:00–20:00 EST rows dated D−1 — and is left out); the decision price is the close of the last `po` bar ENDING at or '
      'before 17:30 New York; a file must show it was taken after 17:30 (a bar of D ending after 17:30, or its fetch time) — otherwise the last bar to '
      '17:30 is not known and the session has no decision price.')
    w('')
    rows = []
    for pc, plabel, lo, hi in PERIODS:
        for nm in ('SPY', 'QQQ'):
            cc = [c for c in cov if c['period'] == pc and c['name'] == nm]
            n = len(cc)
            rows.append([f'{pc} ({lo} → {hi})', nm, n, f'{sum(c["po_daily_low"] is not None for c in cc)}',
                         f'{sum(c["decision_files"] > 0 for c in cc)}', f'{sum(c["decision_px"] is not None for c in cc)} ({pct(sum(c["decision_px"] is not None for c in cc) / n if n else float("nan"))})',
                         f'{sum(c["next_open_0930"] is not None for c in cc)}',
                         f'{sum(c["decision_in_po_range"] is True for c in cc)} / {sum(c["decision_in_po_range"] is not None for c in cc)}'])
    w('\n'.join(md_table(['period', 'name', 'sessions', 'UW daily `po` row', 'UW 1-minute answer on disk', 'decision price (last `po` bar ≤ 17:30)',
                          'next session\'s 09:30 open', 'decision price inside the daily `po` range'], rows)))
    w('')
    ends = Counter(c['decision_bar_end'] for c in cov if c['decision_px'] is not None)
    w(f'Where the decision bar ends: {", ".join(f"{k} {v}" for k, v in sorted(ends.items(), key=lambda x: (-x[1], x[0]))[:8])} '
      '(a bar ending before 17:30 is the last trade-bearing minute before the cut-off). Name-sessions with two UW files whose decision prices disagree: '
      f'{dup_disagree}; bars held by two files of one name-session: {overlap[0]}, closes differing: {overlap[1]} (SPY 2026-10-21, the bar 17:24–17:25: '
      'the recorder took it at 17:24:25, mid-minute, 772.9608 against the finished bar\'s 772.98; not the decision bar).')
    w('')
    miss = [c for c in cov if c['decision_px'] is None]
    w(f'**Every session without a decision price** ({len(miss)} name-sessions):')
    w('')
    if miss:
        w('\n'.join(md_table(['name', 'day', 'period', 'why'], [[c['name'], c['day'], c['period'], c['decision_note']] for c in miss])))
    else:
        w('none.')
    w('')
    nop = [c for c in cov if c['next_open_0930'] is None]
    w(f'**Sessions without a next-session 09:30 open** ({len(nop)} name-sessions; their trades are left out of every case table, (0) included, so every '
      'comparison is on the same trades): ' + ('; '.join(f'{c["name"]} {c["day"]} — {c["next_open_note"]}' for c in nop) if nop else 'none') + '.')
    w('')
    for r in res:
        if r['coverage_b'] < COVER_MIN:
            nms = A.NAMES[r['key']]
            calls = sum(1 for d in r['no_dec'] for nm in nms if COV[(nm, d)]['decision_px'] is None)
            w(f'- {r["label"]}, period {r["period"]}: decision price on {r["Ub"]} of {r["sessions"]} sessions — too thin; (b), (c) and the rule are not '
              f'computed for it. The source that fills it: UW `/api/stock/{{T}}/ohlc/1m?date=D`, one call a name-session ({calls} calls: '
              f'{", ".join(nm for nm in nms)} × {", ".join(r["no_dec"])}), on the UW plan\'s quota, $0 marginal.')
    w('')

    # 2. cases
    w('## 2. The cases')
    w('')
    w('Every trade keeps the replay\'s entry (each leg at its NBBO, $0.65 × 4 contracts at the open). C = the official close; D = the decision price; '
      'O = the next session\'s 09:30 bar open (Theta 1-minute, `$PAPER_PARQUET_ROOT/data/underlying/<name>/<next>.parquet`). "In the money" = by $0.01 or '
      'more. An exercised or assigned leg delivers 100 shares a contract at its strike, the net stock marked at O: + (O − K) a long call, + (K − O) a long '
      'put, the negatives for a short; a leg not exercised expires worthless.')
    w('')
    w('- **(0) current**: every leg at intrinsic on C (the audit\'s re-settled P&L; equal to it on '
      f'{len(T) - check0} of {len(T)} trades).')
    w('- **(a) exercise by exception on C**: every leg in the money at C exercised or assigned. a − 0 = net shares × (O − C): the overnight gap alone.')
    w('- **(b) counterparty adverse selection**: our longs by exception on C; each short assigned iff in the money at D (the holder decides after hours on '
      'what we do not see). b − a isolates it.')
    w('- **(c) both rational at D**: our longs exercised and the shorts assigned iff in the money at D.')
    w(f'- Fee: ${a.fee_ex:.2f} a contract exercised or assigned. Not modeled: the stock commission at the next open, borrow on short stock, margin interest.')
    w('')

    # 3. results
    w('## 3. P&L under the cases, by candidate and period')
    w('')
    w('Session sums (a session\'s trades added; zero on a session with no trade); mean $ a trade = Σ ÷ Σ; intervals are 20-session moving-block '
      f'percentile intervals (— where a period has fewer than {3 * BLOCK} sessions: the block intervals need more sessions). Universe A: sessions with a '
      'next open for every name the candidate trades; universe B: those that also have a decision price for every name.')
    w('')
    head = ['candidate', 'period', 'universe', 'sessions', 'trades', 'series', 'mean $ a trade', 'block-20 CI (trade)', 'mean $ a session',
            'block-20 CI (session)', 'trades differing from (0)', 'total $']
    rows = []
    for r in res:
        for U, ser in (('A', ('0', 'a', '1558')), ('B', ('0', 'a', 'b', 'c', '1558'))):
            if U == 'B' and r['Ub'] == 0:
                rows.append([r['label'], r['period'], 'B', 0, 0, '(b), (c)', 'no decision price', '—', '—', '—', '—', '—'])
                continue
            for s in ser:
                st = r[f'{U}_{s}']
                nm = {'0': '(0) intrinsic at C', 'a': '(a) exception on C', 'b': '(b) shorts at D', 'c': '(c) both at D',
                      '1558': f'15:58 exit, NBBO ({st["trades"]} with a value)'}[s]
                rows.append([r['label'], r['period'], U, st['sessions'], r[f'{U}_0']['trades'], nm, money(st['mean_trade'], 2), ci(st['ci_trade']),
                             money(st['mean_session'], 2), ci(st['ci_session']), pct(st.get('affected')) if s in 'abc' else '—', money(st['total'])])
    w('\n'.join(md_table(head, rows)))
    w('')
    w('**Paired differences** (per trade and per session; the tails are of the per-trade and per-session differences):')
    w('')
    head = ['candidate', 'period', 'universe', 'difference', 'mean $ a trade', 'block-20 CI (trade)', 'mean $ a session', 'block-20 CI (session)',
            'trades affected', 'per trade p5 / p1 / worst', 'per session p5 / p1 / worst']
    rows = []
    for r in res:
        for U, dd in (('A', ('a-0',)), ('B', ('a-0', 'b-a', 'c-b'))):
            for dn in dd:
                st = r.get(f'{U}_{dn}')
                if st is None or (U == 'B' and r['Ub'] == 0):
                    continue
                rows.append([r['label'], r['period'], U, dn.replace('-', ' − '), money(st['mean_trade'], 2), ci(st['ci_trade']), money(st['mean_session'], 2),
                             ci(st['ci_session']), f'{pct(st["affected"])} ({st["affected_n"]})',
                             f'{money(st["trade_p5"])} / {money(st["trade_p1"])} / {money(st["trade_worst"])}',
                             f'{money(st["session_p5"])} / {money(st["session_p1"])} / {money(st["session_worst"])}'])
    w('\n'.join(md_table(head, rows)))
    w('')
    w('**After-hours range (upper bound, labelled).** The share of trades whose UW daily `po` range (16:00–20:00 high and low, with C) took a short '
      'strike across the money — wider than the 17:30 window, so an upper bound on the trades whose assignment could turn after the close — beside the '
      'share whose short-leg in-the-money state actually differs between C and D:')
    w('')
    rows = []
    for r in res:
        fa, na = r['A_po_flag']
        fb, nb = r.get('B_flipD', (float('nan'), 0))
        rows.append([r['label'], r['period'], f'{pct(fa)} of {na}', f'{pct(fb)} of {nb}' if nb else '— (no decision price)'])
    w('\n'.join(md_table(['candidate', 'period', 'daily `po` range crosses a short strike (upper bound)', 'short leg ITM at C ≠ ITM at D'], rows)))
    w('')

    # 4. rule
    w('## 4. The decision rule, applied')
    w('')
    w('Fixed by the owner before the numbers were read: if a candidate\'s mean under (b) is ≤ 0 or its 20-session block-bootstrap interval includes zero, '
      'it is dropped as a SPY/QQQ hold-to-expiry strategy. Measure fixed in the code before the run: mean $ a trade (Σ ÷ Σ) and its block-20 interval '
      f'on universe B. A period with a decision price on fewer than {pct(COVER_MIN, 0)} of its sessions is not judged.')
    w('')
    w('Disclosure: where the block-20 interval cannot be formed (period iii, 7 sessions), the first version of this script marked the period "not '
      'applied". After the period-iii figures were on screen it was changed to apply the rule\'s two clauses as written — a mean ≤ 0 under (b) decides '
      'DROP on its own; a positive mean whose interval cannot be formed is UNDECIDED. Period ii\'s verdicts were not touched by the change. A reader who '
      'holds that no verdict should be read off 7 sessions should read period iii as not applied for both candidates.')
    w('')
    for r in res:
        line = f'- **{r["label"]} — period {r["period"]} ({r["from"]} → {r["to"]}): {r["verdict"]}.** {r["why"]}.'
        if 'verdict_session' in r:
            b = r['B_b']
            line += (f' Session-mean check: {money(b["mean_session"], 2)} {ci(b["ci_session"])} → {r["verdict_session"]}'
                     + (' (the same).' if r['verdict_session'] == r['verdict'] else ' (differs; the trade-mean verdict above stands, as fixed).'))
        w(line)
    w('')

    # 5. 2025-04-09
    v = j0
    s = v['second_sources']
    w('## 5. SPY on 2025-04-09: 548.62 against the second sources')
    w('')
    er = {r['symbol']: r for r in v['theta_eod']}
    spy = er.get('SPY', {})
    rows = [['Theta EOD (`stock_eod`, the official close the audit uses)', f'close {spy.get("close")}; open {spy.get("open")}, high {spy.get("high")}, low {spy.get("low")}; '
             f'last trade stamped {spy.get("last_trade")}; NBBO at the report {spy.get("bid")} / {spy.get("ask")}', 'the source under test'],
            ['Theta 1-minute SPY, 15:59 bar close', f'{v["spy_close_1559"]:.2f}', 'the replay\'s settle'],
            ['Theta 1-minute SPY, 16:00 bar', f'{s["theta_1m_1600_bar"]}', 'same vendor; one print']]
    lb = v['spy_1m_last_bars'][-1] if v['spy_1m_last_bars'] else {}
    rows[-1][1] = f'{lb.get("close")} ({lb.get("volume")} shares, {lb.get("count")} trade(s)); highest 1-minute high of the day {v["spy_1m_high_of_day"]:.2f}'
    rows += [['SPX official close, Cboe (`spx/cboe_spx.csv`) / FRED SP500', f'{s["spx_cboe"]:.2f} / {s["spx_fred"]:.2f}', 'independent of Theta'],
             ['SPX print stamped 16:00 (Theta index file)', f'{s["spx_print_1600"]:.2f}', ''],
             ['SPY implied: 15:59 bar × SPX official ÷ SPX 16:00 print', f'**{s["spx_anchored"]:.2f}**', 'SPX close independent'],
             ['SPY implied: SPY/SPX close ratio of the sessions within 8 days (median) × SPX official', f'**{v["ratio_implied"]:.2f}** (ratios {", ".join(f"{k} {x:.5f}" for k, x in v["spy_spx_ratio_nearby"].items())}; on D: 548.62 ÷ {s["spx_cboe"]:.2f} = {548.62 / s["spx_cboe"]:.5f})', 'SPX close independent'],
             ['SPY implied: 15:59 bar × IVV EOD ÷ IVV 15:59 bar', f'{s["ivv_anchored"]:.2f} (IVV EOD {v["ivv_eod"]}, 15:59 {v["ivv_1559"]})', 'same vendor\'s EOD, another fund'],
             ['SPY implied: 15:59 bar × VOO EOD ÷ VOO 15:59 bar', f'{s["voo_anchored"]:.2f} (VOO EOD {v["voo_eod"]}, 15:59 {v["voo_1559"]})', 'same vendor\'s EOD, another fund'],
             ['QQQ the same day: official − 15:59', f'{v["qqq_official"] - v["qqq_close_1559"]:+.2f} ({v["qqq_official"]} vs {v["qqq_close_1559"]})', 'the sibling index fund'],
             ['UW daily / UW 1-minute for the day', 'none on disk (UW daily starts 2025-10-13; the 1-minute cache 2025-05-22)', '']]
    w('\n'.join(md_table(['source', 'value', 'note'], rows)))
    w('')
    alts = [x for x in (s['spx_anchored'], v['ratio_implied'], s['ivv_anchored'], s['voo_anchored']) if x is not None]
    agree = all(abs(x - v['spy_close_1559']) < 1.0 for x in alts) and all(abs(x - 548.62) > 3.0 for x in alts)
    if agree:
        w(f'**Verdict: not confirmed.** Every second source places SPY\'s close within $1 of the 15:59 bar ({min(alts):.2f}–{max(alts):.2f}), '
          f'${548.62 - max(alts):.2f}–{548.62 - min(alts):.2f} below 548.62; 548.62 is also the Theta EOD row\'s high of the day, above every 1-minute high ({v["spy_1m_high_of_day"]:.2f}), so it reads as '
          'one late or out-of-sequence print taken as the last sale, not the closing auction (the row\'s own NBBO at its 17:16 report, an after-hours '
          'quote, stood near 546). None of the second sources is the primary listing\'s '
          'auction print itself, so this is a strong inconsistency, not a proof of the auction price; the audit\'s official-close re-settlement uses '
          '548.62 for this day.')
    else:
        w('**Verdict: the second sources do not agree among themselves**; see the table.')
    w('')
    w(f'What the day carries in the audit (SPY trades on 2025-04-09, re-settled at 548.62 against the second sources\' median of the anchored values, '
      f'{v["alt_close"]:.2f}):')
    w('')
    w('\n'.join(md_table(['candidate · structure', 'trades', 'total $ at 548.62', f'total $ at {v["alt_close"]:.2f}'],
                         [[k, x['trades'], money(x['total_at_official']), money(x['total_at_second_median'])] for k, x in v['stake'].items()])))
    w('')

    # 6. list
    w(f'## 6. Every pre-2025-10-13 name-session with |official − 15:59| > ${CLOSE_GAP:.2f}')
    w('')
    w(f'The 15:59 bar is read again from the Theta 1-minute files; it equals the audit\'s `settlement_sessions.csv` value on {agree59} of {n59} name-sessions '
      'held in both. UW\'s daily bars start 2025-10-13, so the official close before it has one source, Theta EOD; the second sources are values implied '
      'by other files: SPY — SPX\'s official close (Cboe) anchored on the 15:59 bars (independent of Theta), IVV and VOO EOD anchored on their 15:59 bars '
      '(Theta EOD, other funds); QQQ — TQQQ and SQQQ EOD anchored on their 15:59 bars (÷ ±3; SQQQ\'s minute files on disk are partial, so it is '
      '"—" where its file is missing), QQQM EOD × the median QQQ/QQQM ratio of the five sessions '
      'either side (Theta EOD, other funds); Theta\'s own 16:00 bar for both. "Nearer" says whether the median of the implied values is nearer the '
      'official close or the 15:59 bar.')
    w('')
    rows = []
    for r in cdf.to_dicts():
        if r['name'] == 'SPY':
            sec = f'SPX-anchored {f(r.get("spx_anchored"), "{:.2f}")}; IVV {f(r.get("ivv_anchored"), "{:.2f}")}; VOO {f(r.get("voo_anchored"), "{:.2f}")}'
        else:
            sec = f'TQQQ {f(r.get("tqqq_anchored"), "{:.2f}")}; SQQQ {f(r.get("sqqq_anchored"), "{:.2f}")}; QQQM ratio {f(r.get("qqqm_ratio"), "{:.2f}")}'
        rows.append([r['name'], r['day'], f'{r["official"]:.2f}', r['official_src'], f'{r["close_1559"]:.2f}', f'{r["official_minus_1559"]:+.2f}',
                     f(r.get('theta_1m_1600_bar'), '{:.2f}'), sec, f(r.get('second_median'), '{:.2f}'), r.get('second_nearer') or '—',
                     f(r.get('official_minus_second_median'), '{:+.2f}')])
    w('\n'.join(md_table(['name', 'day', 'official', 'source', '15:59 bar', 'official − 15:59', 'Theta 16:00 bar', 'second sources (implied close)',
                          'median of implied', 'nearer', 'official − median'], rows)))
    w('')
    nf = sum(1 for r in cdf.to_dicts() if r.get('second_nearer') == 'official')
    w(f'Of {cdf.height}: the implied values sit nearer the official close on {nf} and nearer the 15:59 bar on {cdf.height - nf}. Read with care: the '
      'fund-anchored values start from the 15:59 bar and add only the sibling\'s own move from 15:59 to its close, so they test whether SPY or QQQ '
      'moved into the close with its siblings; only the SPX-anchored value uses a close from outside Theta. Every row is in '
      '`out/afterhours_close_check.csv`.')
    w('')

    # 7. files
    w('## 7. Files and command')
    w('')
    w('```')
    w('cd "research_notes/Compass phase 3/backtest_audit"')
    w('PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I afterhours.py [--fee-ex 0.0] [--scratch <dir>]')
    w('# done once (2026-10-22), the 16 period-iii name-sessions; a name-session already in data/postmarket_1m/ is never asked again')
    w('set -a; . <research.env>; set +a; python3 -I fetch_postmarket_1m.py --from-coverage')
    w('```')
    w('')
    w('`--scratch` defaults to the parquet root\'s parent (the folder holding `bt/cache`, `audit_fresh_cache`, `bt/probe`, `evidence/provider_tests`, '
      '`spx/` and `theta/fetch_cache`). Outputs: `out/afterhours_coverage.csv` (every name-session: official close and source, UW daily `po` row, '
      'decision price, its bar, its file, why missing, the next open), `out/afterhours_trades.csv` (every trade under (0)/(a)/(b)/(c), contracts '
      'exercised, net shares, the 15:58 exit, the flags), `out/afterhours_summary.csv` (every statistic above), `out/afterhours_close_check.csv`, '
      '`out/afterhours_20250409.json`. Deterministic: files read in sorted order, seeded draws, no clock in the outputs. `afterhours.py` reads no secret '
      'and calls no vendor. `fetch_postmarket_1m.py` made the 16 UW calls once, one at a time with a 2 s pause (429 → back off), the token from the '
      'environment as a Bearer header, never printed or written; each answer is kept as its response body, gzipped with no timestamp. UW answered every '
      'name-session asked. The replay\'s rows, `scripts/`, `tests/` and the other audit files are only read.')
    w('')
    (A.HERE / 'AFTERHOURS.md').write_text('\n'.join(L), encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
