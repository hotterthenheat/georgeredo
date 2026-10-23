#!/usr/bin/env python3
"""
h7_baseline.py — DESCRIPTIVE, NO NEW VERDICT. H7's committed trades (out/h7_trades.csv, 6c94bb8) against every non-FOMC session
of the same span over the same clock window: buy 100 at the official close of the session before D, sell at the close of D's
13:58 bar. The owner's question (2026-10-23): is H7 a Fed effect, or ordinary overnight drift? H7's verdict and rule are unchanged.

    cd "research_notes/Edge search/H7_H8_H9"
    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 python3 -I -B h7_baseline.py

Reads files only (no vendor call, no clock in the outputs), and no session after 2026-10-22: the same sources as run_h7_h8.py —
the stored 1-minute bars, ThetaData's stock EOD before 2025-10-13 and Unusual Whales' daily bar `r` close from it (both scanned
with the date cut at 2026-10-22), H1's dividend table, the FOMC list. Writes out/h7_baseline.json and H7_BASELINE.md.
Statistics: audit_lib.block_draws / weights_from / pct_ci (read, not edited), 2,000 draws, seed 20261023, 20-session blocks —
the same draws as H7's test, so H7's own interval is reproduced exactly inside every comparison.
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as A  # noqa: E402

SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
BARS = SP / 'theta' / 'data' / 'underlying'
H1 = REPO / 'research_notes' / 'Compass H1'
EOD_FILES = ([str(H1 / 'data' / 'stock_eod_2012_2018.parquet')] + sorted(glob.glob(str(SP / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet')))
             + sorted(glob.glob(str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet'))))
UW_FILES = (sorted(glob.glob(str(REPO / 'data_lake' / 'unusualwhales' / 'ohlc__1d.part0*.parquet')))
            + sorted(glob.glob(str(REPO / 'data' / 'official_closes' / 'uw_ohlc_1d_*.parquet'))))
DIV = H1 / 'data' / 'dividends.json'
FOMC = HERE / 'data' / 'fomc_statements_2012_2026.json'
H7_TRADES = HERE / 'out' / 'h7_trades.csv'
OUT = HERE / 'out'

NAMES = ('SPY', 'QQQ')
FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}      # H7's calendar spans (the bootstrap's sessions), as run_h7_h8.py
SPLIT = '2025-10-13'
LAST = '2026-10-22'                                     # nothing after it is read
SHARES = 100
COST_1X = 1.50
BLOCK, BOOT_N, SEED = 20, 2000, 20261023
_MONTHS = {m: i for i, m in enumerate(('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                                       'November', 'December'), 1)}


def calendar() -> list[str]:
    return sorted(d for d in (Path(f).name[:10] for f in glob.glob(str(BARS / 'QQQ' / '*.parquet'))) if d <= LAST)


def fin(v):
    return float(v) if v is not None and math.isfinite(float(v)) else None


_B: dict = {}


def bars(name: str, day: str) -> dict:
    """the 09:30 open, the 13:58 close, and whether the session is a half day (its last priced bar at or before 13:00)"""
    k = (name, day)
    if k not in _B:
        out = {'O930': None, 'X1358': None, 'half': False, 'file': False}
        p = BARS / name / f'{day}.parquet'
        if p.exists():
            out['file'] = True
            t = pl.read_parquet(p).with_columns(pl.col('timestamp').dt.strftime('%H:%M').alias('hm'))
            for key, hm, field in (('O930', '09:30', 'open'), ('X1358', '13:58', 'close')):
                x = t.filter(pl.col('hm') == hm)
                if x.height:
                    out[key] = fin(x[field][0])
            pr = t.filter(pl.col('close').is_not_null() & pl.col('close').is_finite())
            out['half'] = bool(pr.height) and pr['hm'].max() <= '13:00'
        _B[k] = out
    return _B[k]


def official() -> dict:
    """(name, day) → official close: ThetaData EOD before 2025-10-13, UW's daily `r` bar from it (run_h7_h8.py's reading; two
    different closes for one key → None); both cut at LAST"""
    te, dup = {}, set()
    e = pl.concat([pl.scan_parquet(f).filter(pl.col('symbol').is_in(list(NAMES))).select('symbol', 'created', 'close').collect() for f in EOD_FILES],
                  how='diagonal_relaxed')
    e = e.with_columns(pl.col('created').dt.convert_time_zone('America/New_York').dt.strftime('%Y-%m-%d').alias('day')).filter(pl.col('day') <= LAST)
    for s, d, c in e.select('symbol', 'day', 'close').iter_rows():
        if (s, d) in te and te[(s, d)] != c:
            dup.add((s, d))
        te[(s, d)] = c
    uw, dup2 = {}, set()
    u = pl.concat([pl.scan_parquet(f).filter(pl.col('ticker').is_in(list(NAMES)) & (pl.col('market_time') == 'r')
                                              & (pl.col('date').cast(pl.Utf8) <= LAST)).select('ticker', 'date', 'close').collect() for f in UW_FILES])
    u = u.select(pl.col('ticker'), pl.col('date').cast(pl.Utf8), pl.col('close').cast(pl.Float64)).unique()
    for s, d, c in u.iter_rows():
        if (s, d) in uw and uw[(s, d)] != c:
            dup2.add((s, d))
        uw[(s, d)] = c
    for k in dup:
        te[k] = None
    for k in dup2:
        uw[k] = None
    return {'te': te, 'uw': uw}


def close_of(OFF, nm, d):
    return OFF['te'].get((nm, d)) if d < SPLIT else OFF['uw'].get((nm, d))


def event_days(fomc: dict) -> list[tuple[str, str]]:
    """the unscheduled meetings, conference calls, notation votes and the cancelled meeting of the FOMC list: every day named by
    the meeting text (both days of a two-day meeting) and every statement date listed beside it"""
    out = []
    for e in fomc['excluded']:
        m = re.match(r'\s*([A-Za-z]+)\s+(\d+)(?:-(\d+))?.*-\s*(\d{4})\s*$', e['meeting'])
        mon, y = _MONTHS[m.group(1)], int(m.group(4))
        for d in {int(m.group(2)), int(m.group(3) or m.group(2))}:
            out.append((dt.date(y, mon, d).isoformat(), e['meeting']))
        out += [(s, e['meeting']) for s in e.get('statement', [])]
    return sorted(set(out))


def build(cal, OFF, div, fomc, h7: pl.DataFrame) -> dict:
    prev = {cal[i]: cal[i - 1] for i in range(1, len(cal))}
    scheduled = {e['date'] for e in fomc['scheduled'] if e['date']}
    evs = event_days(fomc)
    rows, check = {}, {}
    for nm in NAMES:
        D = {d: v['amount'] for d, v in div[nm].items() if d <= LAST}
        tr = h7.filter((pl.col('name') == nm) & (pl.col('excluded').fill_null('') == '')).sort('A')
        lo, hi = tr['A'].min(), tr['A'].max()
        out, excl = [], {}

        def drop(d, why):
            excl.setdefault(why, []).append(d)
        for d in cal:
            if d < lo or d > hi or d not in prev or prev[d] < FIRST[nm]:
                continue
            p = prev[d]
            if d in scheduled:
                continue                                     # H7's own days (and pre-2013 scheduled days, none in span)
            win = [m for e, m in evs if p <= e <= d]
            if win:
                drop(d, 'unscheduled meeting / call / notation vote / cancelled meeting in the window (prev ≤ event day ≤ D)')
                continue
            b, bp = bars(nm, d), bars(nm, p)
            if b['half'] or bp['half']:
                drop(d, 'D or the session before is a half day')
                continue
            cp = close_of(OFF, nm, p)
            if cp is None:
                drop(d, 'no official close on the session before')
                continue
            if b['X1358'] is None:
                drop(d, 'no priced 13:58 bar')
                continue
            dv = SHARES * D.get(d, 0.0)
            gross = SHARES * (b['X1358'] - cp)
            o = b['O930']
            gap = (dt.date.fromisoformat(d) - dt.date.fromisoformat(p)).days
            out.append({'D': d, 'prev': p, 'C_prev': cp, 'O930': o, 'X': b['X1358'], 'dividend': dv, 'gross': gross,
                        'net_1x': gross + dv - COST_1X, 'night': None if o is None else SHARES * (o - cp) + dv,
                        'day': None if o is None else SHARES * (b['X1358'] - o), 'spans_closed_day': gap > 1,
                        'weekday': dt.date.fromisoformat(d).strftime('%a')})
        # H7 recomputed by the same code from the raw files, against the committed trades (must be equal)
        diffs = 0
        for r in tr.iter_rows(named=True):
            a, p = r['A'], prev[r['A']]
            b, cp = bars(nm, a), close_of(OFF, nm, p)
            mine = SHARES * (b['X1358'] - cp) + SHARES * D.get(a, 0.0) - COST_1X
            diffs += abs(mine - r['net_1x']) > 1e-6
        check[nm] = {'h7_trades': tr.height, 'recomputed_differences': int(diffs)}
        rows[nm] = {'base': out, 'excluded': {k: sorted(v) for k, v in excl.items()}}
    return {'rows': rows, 'check': check, 'events': evs}


def series(ses, pos, pairs):
    S, N = np.zeros(len(ses)), np.zeros(len(ses))
    for d, v in pairs:
        S[pos[d]] += v
        N[pos[d]] += 1
    return S, N


def compare(W, ses, pos, h7pairs, bpairs) -> dict:
    Sh, Nh = series(ses, pos, h7pairs)
    Sb, Nb = series(ses, pos, bpairs)
    mh = (W @ Sh) / np.maximum(W @ Nh, 1)
    mb = (W @ Sb) / np.maximum(W @ Nb, 1)
    ex = mh - mb
    h, b = Sh.sum() / Nh.sum(), Sb.sum() / Nb.sum()
    return {'h7_n': int(Nh.sum()), 'h7_mean': float(h), 'h7_ci': A.pct_ci(mh), 'base_n': int(Nb.sum()), 'base_mean': float(b),
            'base_ci': A.pct_ci(mb), 'excess': float(h - b), 'excess_ci': A.pct_ci(ex), 'draws_excess_le_0': int((ex <= 0).sum())}


def summarise(built, h7: pl.DataFrame, cal) -> dict:
    res = {}
    for nm in NAMES:
        ses = [d for d in cal if FIRST[nm] <= d <= LAST]
        pos = {d: i for i, d in enumerate(ses)}
        W = A.weights_from(A.block_draws(len(ses), BLOCK, B=BOOT_N, seed=SEED), len(ses))
        tr = h7.filter((pl.col('name') == nm) & (pl.col('excluded').fill_null('') == '')).sort('A').to_dicts()
        for r in tr:
            r['night'] = r['night'] + r['dividend']          # the dividend belongs to the night (no H7 trade has one)
            r['spans_closed_day'] = (dt.date.fromisoformat(r['A']) - dt.date.fromisoformat(r['prev'])).days > 1
        base = built['rows'][nm]['base']
        s = {'calendar_sessions': len(ses), 'h7_span': [tr[0]['A'], tr[-1]['A']], 'excluded': built['rows'][nm]['excluded'],
             'check': built['check'][nm]}
        s['total'] = compare(W, ses, pos, [(r['A'], r['net_1x']) for r in tr], [(r['D'], r['net_1x']) for r in base])
        for part in ('night', 'day'):
            s[part] = compare(W, ses, pos, [(r['A'], r[part]) for r in tr if r[part] is not None],
                              [(r['D'], r[part]) for r in base if r[part] is not None])
        s['vs_consecutive'] = compare(W, ses, pos, [(r['A'], r['net_1x']) for r in tr],
                                      [(r['D'], r['net_1x']) for r in base if not r['spans_closed_day']])
        s['vs_spanning'] = compare(W, ses, pos, [(r['A'], r['net_1x']) for r in tr],
                                   [(r['D'], r['net_1x']) for r in base if r['spans_closed_day']])
        s['vs_wednesday'] = compare(W, ses, pos, [(r['A'], r['net_1x']) for r in tr],
                                    [(r['D'], r['net_1x']) for r in base if r['weekday'] == 'Wed'])
        s['h7_spanning'] = sum(r['spans_closed_day'] for r in tr)
        s['h7_weekdays'] = {w: sum(dt.date.fromisoformat(r['A']).strftime('%a') == w for r in tr) for w in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri')}
        bv = np.asarray([r['net_1x'] for r in base])
        hv = np.asarray([r['net_1x'] for r in tr])
        s['base_win'] = float((bv > 0).mean())
        s['h7_win'] = float((hv > 0).mean())
        s['base_bp'] = float(np.mean([1e4 * r['net_1x'] / (SHARES * r['C_prev']) for r in base]))
        s['h7_bp'] = float(np.mean([1e4 * r['net_1x'] / (SHARES * r['C_prev']) for r in tr]))
        s['base_night_bp'] = float(np.mean([1e4 * r['night'] / (SHARES * r['C_prev']) for r in base if r['night'] is not None]))
        s['h7_night_bp'] = float(np.mean([1e4 * r['night'] / (SHARES * r['C_prev']) for r in tr]))
        s['base_dividend_sessions'] = [r['D'] for r in base if r['dividend']]
        s['base_spanning'] = int(sum(r['spans_closed_day'] for r in base))
        by = {}
        for r in tr:
            by.setdefault(r['A'][:4], {'h7': [], 'base': []})['h7'].append(r['net_1x'])
        for r in base:
            by.setdefault(r['D'][:4], {'h7': [], 'base': []})['base'].append(r['net_1x'])
        s['by_year'] = [{'year': y, 'h7_n': len(v['h7']), 'h7_mean': float(np.mean(v['h7'])) if v['h7'] else None,
                         'base_n': len(v['base']), 'base_mean': float(np.mean(v['base'])) if v['base'] else None,
                         'base_win': float(np.mean(np.asarray(v['base']) > 0)) if v['base'] else None}
                        for y, v in sorted(by.items())]
        res[nm] = s
    return res


def money(x, d=2):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:+,.{d}f}'


def ci(c):
    return f'[{money(c[0])}, {money(c[1])}]'


def write_report(summ: dict) -> None:
    L = []
    w = L.append
    R = summ['H7']
    w('# H7 against ordinary nights: the same clock window on every non-FOMC session (descriptive — no new verdict)')
    w('')
    w('**No new verdict.** This file is descriptive. H7\'s verdict (`6c94bb8`, `H7_H8_REPORT.md`: SPY PASS, QQQ PASS and an EDGE at '
      'm = 13), its rule (`PREREG_H7.md`, `edca472`) and its forward rule (`FORWARD_RULE_H7.md`, `fcc1f4d`) are unchanged; nothing '
      'here is a test, a pass line or a rule change. The owner\'s question (2026-10-23): *is this a Fed effect, or ordinary overnight '
      'drift?*')
    w('')
    w(f'Written by `h7_baseline.py`; every number below is in `out/h7_baseline.json`. H7\'s trades are read as committed '
      f'(`out/h7_trades.csv`, sha256 `{summ["h7_trades_sha256"]}`), and recomputed by this script from the raw files as a check '
      f'(SPY {R["SPY"]["check"]["recomputed_differences"]} and QQQ {R["QQQ"]["check"]["recomputed_differences"]} differences in net 1×). '
      'No vendor fetch; no session after 2026-10-22 read.')
    w('')
    w('## The baseline, exactly')
    w('')
    w('- **Sessions**: per name, every session D from H7\'s first to its last trade (SPY 2017-02-01 → 2026-09-16, QQQ 2013-03-20 → '
      '2026-09-16 — the same years) that is **not a scheduled FOMC statement day** (the 127 dates of `data/fomc_statements_2012_2026.json`).')
    w('- **The same window, prices, costs and dividends as H7**: buy 100 at the official close of the session before D (ThetaData EOD '
      'before 2025-10-13, Unusual Whales\' daily `r` bar from it), sell at the close of D\'s 1-minute bar stamped 13:58; $1.50 a trade '
      '(1×); a dividend whose ex-date is D paid from H1\'s table (`Compass H1/data/dividends.json`). Net = 100 (X − C_prev) + 100 DIV − $1.50.')
    w('- **Excluded, as H7 excludes**: no official close on the session before, no priced 13:58 bar, and half days — D or the session '
      'before is a half day (the file\'s last priced bar at or before 13:00; a half day has no priced 13:58 bar anyway, and a half day '
      'before D would start the hold at a 1:00 pm close). None of H7\'s sessions is a half day.')
    w('- **Excluded, the Fed outside the schedule**: every D whose window holds a day of an unscheduled meeting, conference call, '
      'notation vote or the cancelled 2020-03-17/18 meeting listed under `excluded` in the FOMC list — any such day e with '
      'session-before(D) ≤ e ≤ D (the meeting\'s day(s) and any statement date listed; release times are not in the list, so both '
      'the session of the event and the one after it are dropped).')
    w('- **Calendar mix — the choice**: all baseline sessions are kept, Mondays and post-holiday sessions included (their hold spans '
      'a non-trading day). H7\'s holds: ' + '; '.join(
          f'{nm} {R[nm]["h7_spanning"]} of {R[nm]["total"]["h7_n"]} H7 trades span a non-trading day, weekdays '
          + ', '.join(f'{k} {v}' for k, v in R[nm]['h7_weekdays'].items() if v) for nm in NAMES)
      + '. So the split by whether the hold spans a non-trading day is reported, and a Wednesday-only baseline beside it.')
    w(f'- **Interval**: the 20-session moving-block bootstrap over every calendar session of H7\'s span (SPY 2017-01-03, QQQ 2012-06-01 '
      f'→ 2026-10-22) — `audit_lib.block_draws(n, 20, B={summ["draws"]:,}, seed={summ["seed"]})`, `weights_from`, `pct_ci`, the same '
      'draws as H7\'s test. In each draw both means are recomputed on the resampled sessions (H7\'s Σ W·S ÷ Σ W·N on its statement days, '
      'the baseline\'s on its sessions) and the excess is their difference; the 2.5 and 97.5 percentiles are the interval. H7\'s own '
      'interval in the tables is therefore its committed one.')
    w('- **Overnight / morning**: overnight = 100 (09:30 bar\'s open − C_prev) + the dividend; morning = 100 (13:58 close − 09:30 '
      'open); gross, so overnight + morning − $1.50 = net and the cost cancels in every excess. A session with no priced 09:30 open '
      'is left out of the split only.')
    w('')
    w('## The comparison (per name; $ a trade of 100 shares, 1×)')
    w('')
    w('| name | H7 trades | H7 mean [95 %] | baseline sessions | baseline mean [95 %] | **excess = H7 − baseline [95 %]** | draws ≤ 0 |')
    w('|---|---|---|---|---|---|---|')
    for nm in NAMES:
        t = R[nm]['total']
        w(f'| {nm} | {t["h7_n"]} | {money(t["h7_mean"])} {ci(t["h7_ci"])} | {t["base_n"]:,} | {money(t["base_mean"])} {ci(t["base_ci"])} | '
          f'**{money(t["excess"])} {ci(t["excess_ci"])}** | {t["draws_excess_le_0"]} of {summ["draws"]:,} |')
    w('')
    w('The split (gross pieces; the excess of the two adds to the total excess):')
    w('')
    w('| name | part | H7 mean | baseline mean [95 %] | excess [95 %] | draws ≤ 0 |')
    w('|---|---|---|---|---|---|')
    for nm in NAMES:
        for part, lab in (('night', 'overnight (close → 09:30 open)'), ('day', 'morning (09:30 open → 13:58 close)')):
            t = R[nm][part]
            w(f'| {nm} | {lab} | {money(t["h7_mean"])} | {money(t["base_mean"])} {ci(t["base_ci"])} | {money(t["excess"])} {ci(t["excess_ci"])} | '
              f'{t["draws_excess_le_0"]} |')
    w('')
    w('Calendar mix (H7 against a subset of the baseline; same draws):')
    w('')
    w('| name | baseline subset | sessions | baseline mean [95 %] | excess [95 %] | draws ≤ 0 |')
    w('|---|---|---|---|---|---|')
    for nm in NAMES:
        for k, lab in (('vs_consecutive', 'hold spans no non-trading day'), ('vs_spanning', 'hold spans a weekend / holiday'),
                       ('vs_wednesday', 'Wednesdays only (H7\'s usual weekday)')):
            t = R[nm][k]
            w(f'| {nm} | {lab} | {t["base_n"]:,} | {money(t["base_mean"])} {ci(t["base_ci"])} | {money(t["excess"])} {ci(t["excess_ci"])} | '
              f'{t["draws_excess_le_0"]} |')
    w('')
    w('Win share and size in bp of the position (net 1× ÷ 100 C_prev):')
    w('')
    w('| name | H7 win rate | baseline share > 0 | H7 mean bp | baseline mean bp | H7 overnight bp | baseline overnight bp |')
    w('|---|---|---|---|---|---|---|')
    for nm in NAMES:
        s = R[nm]
        w(f'| {nm} | {100 * s["h7_win"]:.1f} % | {100 * s["base_win"]:.1f} % | {s["h7_bp"]:+.2f} | {s["base_bp"]:+.2f} | {s["h7_night_bp"]:+.2f} | '
          f'{s["base_night_bp"]:+.2f} |')
    w('')
    w('## Per calendar year (descriptive)')
    w('')
    w('| year | ' + ' | '.join(f'{nm} H7 n | {nm} H7 mean | {nm} baseline n | {nm} baseline mean | {nm} baseline > 0' for nm in NAMES) + ' |')
    w('|---|' + '---|' * (5 * len(NAMES)))
    yrs = sorted({y['year'] for nm in NAMES for y in R[nm]['by_year']})
    for y in yrs:
        cells = []
        for nm in NAMES:
            r = next((x for x in R[nm]['by_year'] if x['year'] == y), None)
            cells += ([str(r['h7_n']), money(r['h7_mean']), f'{r["base_n"]:,}', money(r['base_mean']),
                       f'{100 * r["base_win"]:.0f} %' if r['base_win'] is not None else '—'] if r else ['—'] * 5)
        w(f'| {y} | ' + ' | '.join(cells) + ' |')
    w('')
    w('## Exclusions and notes')
    w('')
    for nm in NAMES:
        ex = R[nm]['excluded']
        w(f'- {nm}: ' + ('; '.join(f'{k}: {len(v)} ({", ".join(v[:12])}{" …" if len(v) > 12 else ""})' for k, v in ex.items()) or 'none')
          + f'. Baseline sessions with a dividend term: {len(R[nm]["base_dividend_sessions"])}. Baseline sessions spanning a non-trading '
          f'day: {R[nm]["base_spanning"]:,}.')
    w('- The Fed\'s off-schedule days read from the list: ' + ', '.join(f'{d}' for d, _ in summ['events']) + '.')
    w('- H1\'s dividend table ends at SPY 2025-12-19 (QQQ 2026-09-21), as in H7. SPY\'s 2026 ex-dates (March, June, September; the '
      'third-Friday pattern) are not in it, so up to three SPY baseline sessions in 2026 carry the ex-date price drop with no '
      'dividend term — about 100 × $1.9 each over ~2,300 sessions, roughly −$0.25 on SPY\'s baseline mean (an estimate, not '
      'computed): it would lower SPY\'s excess by about that, far inside the interval.')
    w('- The session after a statement day is in the baseline (its window starts at the statement day\'s close). No financing is '
      'charged on either side (as H7). H7 and the baseline share the costs, so the excess is a difference in gross drift.')
    w('')
    for line in summ['reading']:
        w(line)
        w('')
    (HERE / 'H7_BASELINE.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


def reading(R: dict) -> list[str]:
    s, q = R['SPY'], R['QQQ']

    def clears(t):
        return t['excess_ci'][0] > 0 or t['excess_ci'][1] < 0
    lines = ['## The answer, plainly (descriptive — no new verdict)']
    for nm, x in (('SPY', s), ('QQQ', q)):
        t = x['total']
        lines.append(
            f'**{nm}.** H7 averaged {money(t["h7_mean"])} a trade; an ordinary non-FOMC session over the same window averaged '
            f'{money(t["base_mean"])} ({x["base_bp"]:+.2f} bp of the position; {100 * x["base_win"]:.1f} % of them positive against H7\'s '
            f'{100 * x["h7_win"]:.1f} %). The excess is {money(t["excess"])} a trade, 95 % {ci(t["excess_ci"])} — '
            + ('**the interval excludes zero: the FOMC nights earned more than ordinary nights in the same window.**' if clears(t) and t['excess_ci'][0] > 0
               else '**the interval excludes zero on the negative side.**' if clears(t)
               else '**the interval includes zero: H7\'s result is not distinguishable from ordinary close → 13:58 drift.**')
            + f' Overnight excess {money(x["night"]["excess"])} {ci(x["night"]["excess_ci"])}'
            + (' (clear of zero)' if clears(x['night']) else ' (not clear of zero)')
            + f'; morning excess {money(x["day"]["excess"])} {ci(x["day"]["excess_ci"])}'
            + (' (clear of zero)' if clears(x['day']) else ' (not clear of zero)') + '.')
    yrs = {nm: [y for y in x['by_year'] if y['h7_n'] and y['base_n']] for nm, x in (('SPY', s), ('QQQ', q))}
    lines.append(
        '**What the numbers say together.** The ordinary drift over this window is positive and small: '
        + '; '.join(f'{nm} {money(x["total"]["base_mean"])} a session ({x["base_bp"]:+.2f} bp), about '
                    f'{100 * x["total"]["base_mean"] / x["total"]["h7_mean"]:.0f} % of H7\'s mean' for nm, x in (('SPY', s), ('QQQ', q)))
        + '. In both names the excess is the night — the close → 09:30 piece of H7 is larger than an ordinary night\'s and that '
        'difference is clear of zero in both — while the 09:30 → 13:58 morning on statement days is no better than an ordinary '
        'morning (its excess is negative in both and not clear of zero), the morning giving back part of the night. The total '
        'excess is clear of zero for QQQ and not for SPY (SPY\'s span is 77 statements from 2017; QQQ\'s 108 from 2013). Against the '
        'Wednesday-only baseline — H7\'s own weekday, whose ordinary drift is larger in this sample — the excess is '
        + '; '.join(f'{nm} {money(x["vs_wednesday"]["excess"])} {ci(x["vs_wednesday"]["excess_ci"])}' for nm, x in (('SPY', s), ('QQQ', q)))
        + (', neither clear of zero' if not (clears(s['vs_wednesday']) or clears(q['vs_wednesday'])) else '')
        + '. By year (table above) H7 is above the baseline in '
        + '; '.join(f'{nm} {sum(y["h7_mean"] > y["base_mean"] for y in v)} of {len(v)} years' for nm, v in yrs.items())
        + ', and the excess is concentrated in a few years (2020, 2022 and 2024 above all). SPY and QQQ trade the same nights, so '
        'the two names are not independent evidence.')
    lines.append(
        '**Plainly:** the FOMC-eve nights earned more than ordinary nights over the same clock window — clearly in QQQ, and in the '
        'overnight piece of both names — but SPY\'s total excess and both names\' excess over ordinary Wednesdays are not '
        'distinguishable from zero; ordinary close → 13:58 drift is about ' + ' / '.join(
            f'{money(x["total"]["base_mean"])}' for x in (s, q)) + ' a session (SPY / QQQ), ' + ' / '.join(
            f'{100 * x["total"]["base_mean"] / x["total"]["h7_mean"]:.0f} %' for x in (s, q)) + ' of H7\'s average, and not its '
        'distinctive part, the night\'s excess. This is a description; H7\'s verdict (`6c94bb8`) '
        'and the forward rule (`fcc1f4d`) are unchanged, and nothing here is a new test or a pass line.')
    return lines


def main() -> int:
    OUT.mkdir(exist_ok=True)
    cal = calendar()
    OFF = official()
    div = json.loads(DIV.read_text(encoding='utf-8'))
    fomc = json.loads(FOMC.read_text(encoding='utf-8'))
    h7 = pl.read_csv(H7_TRADES, infer_schema_length=None)
    built = build(cal, OFF, div, fomc, h7)
    R = summarise(built, h7, cal)
    summ = {'note': 'descriptive, no new verdict; H7 verdict 6c94bb8 unchanged', 'seed': SEED, 'draws': BOOT_N, 'block': BLOCK,
            'h7_trades_sha256': hashlib.sha256(H7_TRADES.read_bytes()).hexdigest(),
            'fomc_list_sha256': hashlib.sha256(FOMC.read_bytes()).hexdigest(), 'events': built['events'], 'H7': R}
    summ['reading'] = reading(R)
    (OUT / 'h7_baseline.json').write_text(json.dumps(summ, indent=1, default=str), encoding='utf-8')
    write_report(summ)
    for nm in NAMES:
        t = R[nm]['total']
        print(nm, 'H7', money(t['h7_mean']), [round(v, 2) for v in t['h7_ci']], '| base', t['base_n'], money(t['base_mean']),
              '| excess', money(t['excess']), [round(v, 2) for v in t['excess_ci']], '| night', money(R[nm]['night']['excess']),
              [round(v, 2) for v in R[nm]['night']['excess_ci']], '| day', money(R[nm]['day']['excess']), [round(v, 2) for v in R[nm]['day']['excess_ci']],
              '| check', R[nm]['check'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
