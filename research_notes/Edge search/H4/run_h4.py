#!/usr/bin/env python3
"""
run_h4.py — H4, market intraday momentum (first half-hour → last half-hour), SPY and QQQ stock, as pre-registered in
PREREG_H4.md (read it first).

    cd "research_notes/Edge search/H4"
    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 python3 -I -B run_h4.py

Reads files only (no vendor call, no clock in the outputs): the stored 1-minute bars ($SP/theta/data/underlying/<name>/<day>.parquet),
ThetaData's stock EOD (the files run_h1.py reads) for sessions before 2025-10-13, Unusual Whales' daily bars (audit_lib.uw_daily)
from 2025-10-13, and H1's dividend table (descriptive only). Writes out/h4_sessions.csv, out/h4_summary.json and H4_REPORT.md.
Statistics: audit_lib.block_draws / weights_from / pct_ci (read from the backtest audit's folder, not edited).
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
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
DIV = H1 / 'data' / 'dividends.json'
OUT = HERE / 'out'

# ---- the pre-registered constants (PREREG_H4.md) ---------------------------------------------------------------------------------------
NAMES = ('SPY', 'QQQ')
FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}
SPLIT = '2025-10-13'                          # official close: ThetaData EOD before, Unusual Whales' daily bar from
TEST_LAST = '2026-10-22'
SPANS = {'exploration': lambda nm, d: FIRST[nm] <= d < SPLIT, 'test': lambda nm, d: SPLIT <= d <= TEST_LAST}
SHARES = 100
ENTRY_HALF_SPREAD = 0.005                     # $ a share at the 15:30 entry
AUCTION = 0.01                                # $ a share at the closing-auction exit
BORROW = 0.0030                               # a year, Actual/360, on the short's notional at E, for 30 minutes
HOLD_DAYS = 30.0 / 1440.0
TIE = 0.00005
BLOCK, BOOT_N, SEED = 20, 2000, 20261023
BONF = {'m3': 0.05 / 6, 'm8': 0.05 / 16}      # alpha = 0.05 / (2 names x m)
HALF_DAYS = frozenset('''
2012-07-03 2012-11-23 2012-12-24 2013-07-03 2013-11-29 2013-12-24 2014-07-03 2014-11-28 2014-12-24 2015-11-27 2015-12-24
2016-11-25 2017-07-03 2017-11-24 2018-07-03 2018-11-23 2018-12-24 2019-07-03 2019-11-29 2019-12-24 2020-11-27 2020-12-24
2021-11-26 2022-11-25 2023-07-03 2023-11-24 2024-07-03 2024-11-29 2024-12-24 2025-07-03 2025-11-28 2025-12-24
'''.split())


def calendar() -> list[str]:
    return sorted(Path(f).name[:10] for f in glob.glob(str(BARS / 'QQQ' / '*.parquet')))


def fin(v):
    return float(v) if v is not None and math.isfinite(float(v)) else None


def bars_of(name: str, day: str) -> dict:
    """the 09:59 close, the 15:30 open (and the 15:59 close, descriptive) of one session's file; None where unpriced or missing"""
    p = BARS / name / f'{day}.parquet'
    out = {'P10': None, 'E': None, 'C1559': None}
    if not p.exists():
        return out
    t = pl.read_parquet(p).with_columns(pl.col('timestamp').dt.strftime('%H:%M').alias('hm'))
    for key, hm, field in (('P10', '09:59', 'close'), ('E', '15:30', 'open'), ('C1559', '15:59', 'close')):
        x = t.filter(pl.col('hm') == hm)
        if x.height:
            out[key] = fin(x[field][0])
    return out


def theta_eod() -> dict:
    e = pl.concat([pl.scan_parquet(f).filter(pl.col('symbol').is_in(list(NAMES))).select('symbol', 'created', 'close').collect() for f in EOD_FILES],
                  how='diagonal_relaxed')
    e = e.with_columns(pl.col('created').dt.convert_time_zone('America/New_York').dt.strftime('%Y-%m-%d').alias('day'))
    out, dup = {}, set()
    for s, d, c in e.select('symbol', 'day', 'close').iter_rows():
        k = (s, d)
        if k in out and out[k] != c:
            dup.add(k)
        out[k] = c
    for k in dup:
        out[k] = None
    return out


def uw_closes() -> dict:
    u = A.uw_daily(NAMES)
    out, dup = {}, set()
    for s, d, c in u.select('symbol', 'day', 'close_uw').iter_rows():
        k = (s, str(d))
        if k in out and out[k] != c:
            dup.add(k)
        out[k] = c
    for k in dup:
        out[k] = None
    return out


def build() -> pl.DataFrame:
    cal = calendar()
    prev = {cal[i]: cal[i - 1] for i in range(1, len(cal))}
    TE, UW = theta_eod(), uw_closes()

    def official(nm, d):
        if d is None:
            return None, ''
        if d < SPLIT:
            return TE.get((nm, d)), 'theta_eod'
        return UW.get((nm, d)), 'uw_daily'

    div = json.loads(DIV.read_text(encoding='utf-8'))
    rows = []
    for nm in NAMES:
        exd = set(div[nm])
        for d in cal:
            span = next((k for k, f in SPANS.items() if f(nm, d)), None)
            if span is None:
                continue
            pd_ = prev.get(d)
            cprev, src_prev = official(nm, pd_)
            c, src = official(nm, d)
            b = bars_of(nm, d)
            r = {'name': nm, 'span': span, 'day': d, 'prev': pd_, 'Cprev': cprev, 'Cprev_src': src_prev, 'P10': b['P10'], 'E': b['E'],
                 'C': c, 'C_src': src, 'C1559': b['C1559'], 'ex_date_in_table': d in exd}
            why = []
            if d in HALF_DAYS:
                why.append('half day')
            if cprev is None:
                why.append(f'no official close on the previous session {pd_}')
            if b['P10'] is None:
                why.append('no priced 09:59 bar')
            if b['E'] is None:
                why.append('no priced 15:30 bar')
            if c is None:
                why.append('no official close')
            r['excluded'] = '; '.join(why)
            if not why:
                P, Cp, E, C = b['P10'], cprev, b['E'], c
                side = 1 if P - Cp >= TIE else (-1 if Cp - P >= TIE else 0)
                r['r1'] = P / Cp - 1
                r['side'] = side
                r['gross'] = side * SHARES * (C - E)
                r['borrow'] = (BORROW * SHARES * E * HOLD_DAYS / 360.0) if side == -1 else 0.0
                for k, mult in (('1x', 1.0), ('2x', 2.0)):
                    r[f'cost_{k}'] = mult * SHARES * (ENTRY_HALF_SPREAD + AUCTION) if side != 0 else 0.0
                    r[f'net_{k}'] = (r['gross'] - r[f'cost_{k}'] - r['borrow']) if side != 0 else 0.0
            rows.append(r)
    return pl.DataFrame(rows, infer_schema_length=None)


def stats(t: pl.DataFrame, col: str, W: np.ndarray, bonf: bool) -> dict:
    S = t[col].to_numpy().astype(float)
    N = (t['side'].to_numpy() != 0).astype(float)
    out = {'sessions': int(S.size), 'trades': int(N.sum()), 'mean_trade': float(S.sum() / N.sum()) if N.sum() else float('nan')}
    mt = (W @ S) / np.maximum(W @ N, 1)
    out['ci'] = A.pct_ci(mt)
    if bonf:
        for k, a in BONF.items():
            x = mt[np.isfinite(mt)]
            out[f'ci_{k}'] = (float(np.percentile(x, 100 * a / 2)), float(np.percentile(x, 100 * (1 - a / 2))))
    tr = S[N > 0]
    out['win_rate'] = float((tr > 0).mean()) if tr.size else float('nan')
    out['total'] = float(tr.sum())
    out['worst'] = float(tr.min()) if tr.size else float('nan')
    out['best'] = float(tr.max()) if tr.size else float('nan')
    return out


def overlap(t: pl.DataFrame) -> None:
    """descriptive, not pre-registered: how often sign(r1) agrees with the sign of the 09:30 open -> 09:59 close (the earlier reads' signal)"""
    o = {}
    inc = t.filter(pl.col('excluded') == '').sort('name', 'day')
    for nm, span, d, P10, side in inc.select('name', 'span', 'day', 'P10', 'side').iter_rows():
        x = pl.read_parquet(BARS / nm / f'{d}.parquet').filter(pl.col('timestamp').dt.strftime('%H:%M') == '09:30')
        o930 = fin(x['open'][0]) if x.height else None
        if o930 is None or side == 0 or abs(P10 - o930) < TIE:
            continue
        k = f'{nm} {span}'
        o.setdefault(k, {'n': 0, 'agree': 0})
        o[k]['n'] += 1
        o[k]['agree'] += int((P10 > o930) == (side == 1))
    (OUT / 'h4_signal_overlap.json').write_text(json.dumps(o, indent=1), encoding='utf-8')


def money(x, d=2):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:+,.{d}f}'


def main() -> int:
    OUT.mkdir(exist_ok=True)
    t = build()
    t.write_csv(OUT / 'h4_sessions.csv')
    summ = {'prereg_sha256': hashlib.sha256((HERE / 'PREREG_H4.md').read_bytes()).hexdigest(), 'names': {}}
    for nm in NAMES:
        summ['names'][nm] = {}
        for span in SPANS:
            u = t.filter((pl.col('name') == nm) & (pl.col('span') == span))
            inc = u.filter(pl.col('excluded') == '').sort('day')
            W = A.weights_from(A.block_draws(inc.height, BLOCK, B=BOOT_N, seed=SEED), inc.height)
            s = {'span': [inc['day'].min(), inc['day'].max()], 'calendar_sessions': u.height, 'included': inc.height,
                 'excluded': u.filter(pl.col('excluded') != '').select('day', 'excluded').to_dicts(),
                 'long': int((inc['side'] == 1).sum()), 'short': int((inc['side'] == -1).sum()), 'flat': int((inc['side'] == 0).sum())}
            for k in ('1x', '2x'):
                s[k] = stats(inc, f'net_{k}', W, bonf=(span == 'test'))
                s[k]['pass'] = bool(s[k]['mean_trade'] > 0 and s[k]['ci'][0] > 0)
            if span == 'test':
                s['edge_m3'] = bool(s['1x']['pass'] and s['1x']['ci_m3'][0] > 0)
                s['edge_m8'] = bool(s['1x']['pass'] and s['1x']['ci_m8'][0] > 0)
            tr = inc.filter(pl.col('side') != 0)
            s['by_side'] = {lab: {'trades': int(g.height), 'mean_1x': float(g['net_1x'].mean()) if g.height else float('nan'),
                                  'win_rate': float((g['net_1x'] > 0).mean()) if g.height else float('nan')}
                            for lab, g in (('long', tr.filter(pl.col('side') == 1)), ('short', tr.filter(pl.col('side') == -1)))}
            s['by_year'] = [{'year': y, 'trades': int(g.height), 'mean_1x': float(g['net_1x'].mean()), 'mean_2x': float(g['net_2x'].mean())}
                            for (y,), g in sorted(tr.with_columns(pl.col('day').str.slice(0, 4).alias('y')).group_by('y'), key=lambda x: x[0])]
            s['gross_mean'] = float(tr['gross'].mean())
            s['borrow_mean'] = float(tr['borrow'].mean())
            s['ex_date_trades'] = tr.filter(pl.col('ex_date_in_table')).select('day', 'side', 'r1', 'net_1x').to_dicts()
            summ['names'][nm][span] = s
    (OUT / 'h4_summary.json').write_text(json.dumps(summ, indent=1, default=str), encoding='utf-8')
    overlap(t)
    write_report(summ)
    for nm in NAMES:
        for span in SPANS:
            s = summ['names'][nm][span]
            print(nm, span, s['span'], 'trades', s['1x']['trades'], 'L/S/F', s['long'], s['short'], s['flat'], '1x', money(s['1x']['mean_trade']),
                  [round(x, 2) for x in s['1x']['ci']], 'PASS' if s['1x']['pass'] else 'not clear', '| 2x', money(s['2x']['mean_trade']),
                  [round(x, 2) for x in s['2x']['ci']])
    return 0


def write_report(summ: dict) -> None:
    L = []
    w = L.append
    w('# H4 — market intraday momentum (first half-hour → last half-hour), SPY and QQQ stock: the pre-registered test, run once')
    w('')
    w(f'PREREG_H4.md sha256 `{summ["prereg_sha256"]}` (the file as committed alone, `b14b640`, before this run). Written by `run_h4.py`; '
      'every number below is in `out/h4_summary.json` and every session in `out/h4_sessions.csv`.')
    w('')
    w('Rule: r1 = the 09:59 bar\'s close ÷ the previous session\'s official close − 1; long 100 shares at the 15:30 bar\'s open if r1 > 0, '
      'short if r1 < 0, flat if equal; exit at the official close (ThetaData EOD before 2025-10-13, Unusual Whales\' daily bar from it); '
      'half days out; $0.005 a share at entry and $0.01 in the auction ($1.50 a trade at 1×, $3.00 at 2×), borrow pro rata for 30 minutes.')
    w('')
    w('## Verdict — the test span, 2025-10-13 → 2026-10-22, each name on its own (pass: mean $ a trade after costs at 1× > 0 and the 20-session block-bootstrap 95 % interval clear of zero)')
    w('')
    w('| name | sessions in | trades | long / short / flat | mean $ a trade, 1× [95 % block-20] | verdict | mean $ a trade, 2× [95 % block-20] | at 2× | win rate 1× | total 1× | worst / best trade 1× |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for nm, ss in summ['names'].items():
        s = ss['test']
        a, b = s['1x'], s['2x']
        w(f'| {nm} | {s["included"]} | {a["trades"]} | {s["long"]} / {s["short"]} / {s["flat"]} | '
          f'{money(a["mean_trade"])} [{money(a["ci"][0])}, {money(a["ci"][1])}] | **{"PASS" if a["pass"] else "FAIL"}** | '
          f'{money(b["mean_trade"])} [{money(b["ci"][0])}, {money(b["ci"][1])}] | {"clear of zero" if b["pass"] else "not clear"} | '
          f'{100 * a["win_rate"]:.1f} % | {money(a["total"], 0)} | {money(a["worst"], 0)} / {money(a["best"], 0)} |')
    w('')
    for nm, ss in summ['names'].items():
        s = ss['test']
        w(f'**{nm}: {"PASS" if s["1x"]["pass"] else "FAIL"}.**')
    w('')
    w('**Bonferroni (PREREG §5, α = 0.05 ÷ (2 names × m), the same 2,000 draws; coarse tails).**')
    w('')
    w('| name | 1× interval at m = 3 (α 0.833 %) | EDGE at m = 3 | 1× interval at m = 8 (α 0.3125 %) | EDGE at m = 8 |')
    w('|---|---|---|---|---|')
    for nm, ss in summ['names'].items():
        a = ss['test']['1x']
        w(f'| {nm} | [{money(a["ci_m3"][0])}, {money(a["ci_m3"][1])}] | {"yes" if ss["test"]["edge_m3"] else "no"} | '
          f'[{money(a["ci_m8"][0])}, {money(a["ci_m8"][1])}] | {"yes" if ss["test"]["edge_m8"] else "no"} |')
    w('')
    vf = OUT / 'h4_verify.json'
    if vf.exists():
        v = json.loads(vf.read_text(encoding='utf-8'))
        w(f'**Verification.** `verify_h4.py` re-derived {v["checked"]} traded sessions ({v["by"]}) from the raw files with plain loops and no '
          f'shared code: {v["differences"]} differences in {v["fields"]} fields; sessions carrying a P&L while excluded: {v["excluded_with_pnl"]}; '
          f'sessions whose traded flag disagrees with side: {v["flag_mismatch"]}.')
        w('')
    w('## Test span, descriptive (no verdict)')
    w('')
    w('| name | gross price P&L a trade | costs a trade 1× / 2× | borrow a short | long trades: n, mean 1×, win | short trades: n, mean 1×, win |')
    w('|---|---|---|---|---|---|')
    for nm, ss in summ['names'].items():
        s = ss['test']
        lg, sh = s['by_side']['long'], s['by_side']['short']
        bs = s['borrow_mean'] * (s['1x']['trades'] / max(s['short'], 1))
        w(f'| {nm} | {money(s["gross_mean"])} | −1.50 / −3.00 | {money(-bs, 4)} | {lg["trades"]}, {money(lg["mean_1x"])}, {100 * lg["win_rate"]:.1f} % | '
          f'{sh["trades"]}, {money(sh["mean_1x"])}, {100 * sh["win_rate"]:.1f} % |')
    w('')
    w('Per calendar year of the test span:')
    w('')
    w('| year | ' + ' | '.join(f'{nm} trades | {nm} mean 1× | {nm} mean 2×' for nm in summ['names']) + ' |')
    w('|---|' + '---|' * (3 * len(summ['names'])))
    yrs = sorted({y['year'] for ss in summ['names'].values() for y in ss['test']['by_year']})
    for y in yrs:
        cells = []
        for nm, ss in summ['names'].items():
            r = next((x for x in ss['test']['by_year'] if x['year'] == y), None)
            cells += [str(r['trades']), money(r['mean_1x']), money(r['mean_2x'])] if r else ['—'] * 3
        w(f'| {y} | ' + ' | '.join(cells) + ' |')
    w('')
    for nm, ss in summ['names'].items():
        ex = ss['test']['ex_date_trades']
        w(f'{nm} traded test sessions on an ex-date in H1\'s dividend table (r1 carries the dividend drop{"; the table has no SPY ex-date after 2025-12-19" if nm == "SPY" else ""}): '
          + (', '.join(f'{r["day"]} ({"long" if r["side"] == 1 else "short"}, r1 {100 * r["r1"]:+.3f} %, net {money(r["net_1x"])})' for r in ex) if ex else 'none') + '.')
        w('')
    w('**Reading (descriptive, no verdict).** ' + ' '.join(
        f'{nm}: the gross price P&L is {money(ss["test"]["gross_mean"])} a trade before the $1.50 of costs, the long trades average '
        f'{money(ss["test"]["by_side"]["long"]["mean_1x"])} and the short trades {money(ss["test"]["by_side"]["short"]["mean_1x"])} at 1×, '
        f'and the interval spans {money(ss["test"]["1x"]["ci"][0])} to {money(ss["test"]["1x"]["ci"][1])}.' for nm, ss in summ['names'].items()) +
      ' Neither interval is clear of zero, so neither name passes. The intervals are about as wide as PREREG §6 expected '
      '(an a-priori standard error of $10–13 a trade); a true mean below roughly $30 a trade could not have been detected on 257 sessions, '
      'so the fail says little about an effect of the size the literature reports. On the exploration span (context only) neither name shows '
      'a positive mean either: SPY ' + money(summ['names']['SPY']['exploration']['1x']['mean_trade']) + ' and QQQ ' +
      money(summ['names']['QQQ']['exploration']['1x']['mean_trade']) + ' a trade at 1×, in line with the earlier open-signed reads (PREREG §7).')
    w('')
    ov = OUT / 'h4_signal_overlap.json'
    if ov.exists():
        o = json.loads(ov.read_text(encoding='utf-8'))
        w('**How close r1 is to the open-signed first half hour the earlier reads used (not pre-registered; descriptive, for PREREG §7).** '
          'Share of included sessions where sign(r1) equals the sign of the 09:30 bar\'s open → the 09:59 bar\'s close: ' +
          '; '.join(f'{k} {v["agree"]} of {v["n"]} ({100 * v["agree"] / v["n"]:.1f} %)' for k, v in o.items()) + '.')
        w('')
    w('## Exploration span (context only — PREREG §3: no choice was made from it and it carries no verdict)')
    w('')
    w('| name | span | sessions in | trades | long / short / flat | mean $ a trade, 1× [95 % block-20] | 2× [95 % block-20] | win rate 1× | worst / best 1× | long mean 1× | short mean 1× |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for nm, ss in summ['names'].items():
        s = ss['exploration']
        a, b = s['1x'], s['2x']
        w(f'| {nm} | {s["span"][0]} → {s["span"][1]} | {s["included"]:,} | {a["trades"]:,} | {s["long"]:,} / {s["short"]:,} / {s["flat"]} | '
          f'{money(a["mean_trade"])} [{money(a["ci"][0])}, {money(a["ci"][1])}] | {money(b["mean_trade"])} [{money(b["ci"][0])}, {money(b["ci"][1])}] | '
          f'{100 * a["win_rate"]:.1f} % | {money(a["worst"], 0)} / {money(a["best"], 0)} | {money(s["by_side"]["long"]["mean_1x"])} | {money(s["by_side"]["short"]["mean_1x"])} |')
    w('')
    w('Per year, exploration (descriptive):')
    w('')
    w('| year | ' + ' | '.join(f'{nm} trades | {nm} mean 1× | {nm} mean 2×' for nm in summ['names']) + ' |')
    w('|---|' + '---|' * (3 * len(summ['names'])))
    yrs = sorted({y['year'] for ss in summ['names'].values() for y in ss['exploration']['by_year']})
    for y in yrs:
        cells = []
        for nm, ss in summ['names'].items():
            r = next((x for x in ss['exploration']['by_year'] if x['year'] == y), None)
            cells += [str(r['trades']), money(r['mean_1x']), money(r['mean_2x'])] if r else ['—'] * 3
        w(f'| {y} | ' + ' | '.join(cells) + ' |')
    w('')
    w('## Sessions left out')
    w('')
    for nm, ss in summ['names'].items():
        for span in SPANS:
            s = ss[span]
            by = {}
            for r in s['excluded']:
                by.setdefault(r['excluded'], []).append(r['day'])
            w(f'**{nm}, {span}** — {len(s["excluded"])} of {s["calendar_sessions"]} calendar sessions:')
            w('')
            for why, ds in sorted(by.items(), key=lambda x: -len(x[1])):
                w(f'- {why}: {len(ds)} — ' + ', '.join(ds))
            w('')
    w('## Notes on the run (none changes the rule)')
    w('')
    w('- `run_h4.py` was run once for the result. It was re-run afterwards only to write the verification line, the reading, the signal '
      'overlap and these notes into this report; every re-run left `out/h4_summary.json` and `out/h4_sessions.csv` byte-identical to the '
      'first run (sha256 checked). The overlap figure is written to its own file, `out/h4_signal_overlap.json`, and is not a variant.')
    w('- PREREG §8 says the verifier uses no pyarrow; it reads each Parquet file into Python lists with polars and does everything else '
      'in plain loops (its own session list, previous session, official close by source and date, bar lookup by stamp, side, gross, costs, borrow).')
    w('- QQQ 2013-05-09 has no priced 15:30 bar in the stored file and is excluded by the rule (exploration; no other bar substituted). '
      'QQQ 2013-08-22 (the Nasdaq halt, reopened 15:25) has priced 09:59 and 15:30 bars and is included.')
    w('- No vendor fetch was made. Sessions from 2026-10-23 were not read. Since neither name passed, no FORWARD rule is committed (PREREG §4).')
    w('')
    (HERE / 'H4_REPORT.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
