#!/usr/bin/env python3
"""
run_h1.py — H1, the overnight reversal of the late-day move, as pre-registered in PREREG_H1.md (read it first).

    cd "research_notes/Compass H1"
    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 python3 -I -B run_h1.py

Reads files only (no vendor call, no clock in the outputs): the stored 1-minute bars ($SP/theta/data/underlying/<name>/<day>.parquet),
ThetaData's stock EOD (data/stock_eod_2012_2018.parquet, $SP/lake/stock_eod/year=2019, data_lake/thetadata/stock_eod/year=2020..),
data/dividends.json, and the after-hours study's out/afterhours_close_check.csv. Writes out/h1_sessions.csv, out/h1_summary.json
and H1_REPORT.md in this folder. Statistics: audit_lib.block_draws / pct_ci (read from the backtest audit's folder, not edited).
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as A  # noqa: E402

SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
BARS = SP / 'theta' / 'data' / 'underlying'
EOD_FILES = ([str(HERE / 'data' / 'stock_eod_2012_2018.parquet')] + sorted(glob.glob(str(SP / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet')))
             + sorted(glob.glob(str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet'))))
FLAG_CSV = REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit' / 'out' / 'afterhours_close_check.csv'
OUT = HERE / 'out'

# ---- the pre-registered constants (PREREG_H1.md) ---------------------------------------------------------------------------------------
NAMES = ('SPY', 'QQQ')
FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}   # first signal session a name (SPY: ThetaData serves no SPY stock data before 2017)
LAST = '2025-10-10'                          # the last signal session; its exit is the 2025-10-13 09:30 open
SHARES = 100
COST = 0.01                                  # $ a share each way (auction fill: commission, fees, slippage); 2x = 0.02
BORROW = 0.0030                              # a year, on the short's notional at C, per calendar day held (Actual/360)
TIE = 0.00005                                # |C - P15| below this is "equal": flat
FLAG_GAP = 0.25                              # |C - 15:59 bar close| above this flags the session (sensitivity only)
BLOCK, BOOT_N, SEED = 20, 2000, 20261022
HALF_DAYS = frozenset('''
2012-07-03 2012-11-23 2012-12-24 2013-07-03 2013-11-29 2013-12-24 2014-07-03 2014-11-28 2014-12-24 2015-11-27 2015-12-24
2016-11-25 2017-07-03 2017-11-24 2018-07-03 2018-11-23 2018-12-24 2019-07-03 2019-11-29 2019-12-24 2020-11-27 2020-12-24
2021-11-26 2022-11-25 2023-07-03 2023-11-24 2024-07-03 2024-11-29 2024-12-24 2025-07-03
'''.split())


def calendar() -> list[str]:
    """the sessions: the dates QQQ's stored 1-minute files exist (one on every session, none on a holiday)"""
    return sorted(Path(f).name[:10] for f in glob.glob(str(BARS / 'QQQ' / '*.parquet')))


def bar(name: str, day: str, hm: str, field: str):
    p = BARS / name / f'{day}.parquet'
    if not p.exists():
        return None
    t = pl.read_parquet(p).filter(pl.col('timestamp').dt.strftime('%H:%M') == hm)
    if t.height == 0:
        return None
    v = t[field][0]
    return float(v) if v is not None and math.isfinite(float(v)) else None


def eod() -> dict:
    e = pl.concat([pl.scan_parquet(f).filter(pl.col('symbol').is_in(list(NAMES))).select('symbol', 'created', 'close').collect() for f in EOD_FILES],
                  how='diagonal_relaxed')
    e = e.with_columns(pl.col('created').dt.convert_time_zone('America/New_York').dt.strftime('%Y-%m-%d').alias('day'))
    out, dup = {}, set()
    for s, d, c in e.select('symbol', 'day', 'close').iter_rows():
        k = (s, d)
        if k in out and out[k] != c:
            dup.add(k)
        out[k] = c
    for k in dup:                                   # two different closes for one session: no official close
        out[k] = None
    return out


def caldays(a: str, b: str) -> int:
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def build() -> pl.DataFrame:
    cal = calendar()
    nxt = {cal[i]: cal[i + 1] for i in range(len(cal) - 1)}
    E = eod()
    div = json.loads((HERE / 'data' / 'dividends.json').read_text(encoding='utf-8'))
    rows = []
    for nm in NAMES:
        D = {d: v['amount'] for d, v in div[nm].items()}
        for d in cal:
            if not (FIRST[nm] <= d <= LAST):
                continue
            n = nxt.get(d)
            r = {'name': nm, 'day': d, 'next': n, 'C': E.get((nm, d)), 'P15': bar(nm, d, '14:59', 'close'),
                 'O': bar(nm, n, '09:30', 'open') if n else None, 'C1559': bar(nm, d, '15:59', 'close'), 'div_next': D.get(n, 0.0) if n else 0.0}
            why = []
            if d in HALF_DAYS:
                why.append('half day')
            if r['C'] is None:
                why.append('no official close (ThetaData EOD)')
            if r['P15'] is None:
                why.append('no priced 14:59 bar')
            if r['O'] is None:
                why.append(f'no priced 09:30 bar on the next session {n}')
            r['excluded'] = '; '.join(why)
            if not why:
                C, P, O = r['C'], r['P15'], r['O']
                side = -1 if C - P >= TIE else (1 if P - C >= TIE else 0)
                r['side'] = side
                r['gross'] = side * SHARES * (O - C)
                r['dividend'] = side * SHARES * r['div_next']
                r['borrow'] = (BORROW * SHARES * C * caldays(d, n) / 360.0) if side == -1 else 0.0
                for k, c in (('1x', COST), ('2x', 2 * COST)):
                    r[f'cost_{k}'] = 2 * c * SHARES if side != 0 else 0.0
                    r[f'net_{k}'] = r['gross'] + r['dividend'] - r['borrow'] - r[f'cost_{k}'] if side != 0 else 0.0
            r['flag_gap'] = (r['C'] is not None and r['C1559'] is not None and abs(r['C'] - r['C1559']) > FLAG_GAP)
            rows.append(r)
    t = pl.DataFrame(rows, infer_schema_length=None)
    csv_flags = {(r['name'], r['day']) for r in pl.read_csv(FLAG_CSV, infer_schema_length=None).select('name', 'day').to_dicts()}
    t = t.with_columns(pl.struct('name', 'day').map_elements(lambda s: (s['name'], s['day']) in csv_flags, return_dtype=pl.Boolean).alias('flag_csv'))
    return t.with_columns((pl.col('flag_gap') | pl.col('flag_csv')).alias('flagged'))


def stats(t: pl.DataFrame, col: str, idx: np.ndarray | None = None) -> dict:
    """t: the included sessions of one name in calendar order. S = the session's net $ (0 when flat), N = 1 when it traded"""
    S = t[col].to_numpy().astype(float)
    N = (t['side'].to_numpy() != 0).astype(float)
    n = S.size
    out = {'sessions': int(n), 'trades': int(N.sum()), 'mean_trade': float(S.sum() / N.sum()) if N.sum() else float('nan')}
    if idx is None:
        idx = A.block_draws(n, BLOCK, B=BOOT_N, seed=SEED)
    W = A.weights_from(idx, n)
    mt = (W @ S) / np.maximum(W @ N, 1)
    out['ci'] = A.pct_ci(mt)
    tr = S[N > 0]
    out['win_rate'] = float((tr > 0).mean()) if tr.size else float('nan')
    out['total'] = float(tr.sum())
    out['worst'] = float(tr.min()) if tr.size else float('nan')
    out['best'] = float(tr.max()) if tr.size else float('nan')
    return out


def money(x, d=2):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:+,.{d}f}'


def main() -> int:
    OUT.mkdir(exist_ok=True)
    t = build()
    t.write_csv(OUT / 'h1_sessions.csv')
    pre = HERE / 'PREREG_H1.md'
    prehash = hashlib.sha256(pre.read_bytes()).hexdigest()
    summ = {'prereg_sha256': prehash, 'names': {}}
    for nm in NAMES:
        u = t.filter(pl.col('name') == nm)
        inc = u.filter(pl.col('excluded') == '').sort('day')
        idx = A.block_draws(inc.height, BLOCK, B=BOOT_N, seed=SEED)
        s = {'span': [inc['day'].min(), inc['day'].max()], 'calendar_sessions': u.height, 'included': inc.height,
             'excluded': u.filter(pl.col('excluded') != '').select('day', 'excluded').to_dicts(),
             'long': int((inc['side'] == 1).sum()), 'short': int((inc['side'] == -1).sum()), 'flat': int((inc['side'] == 0).sum()),
             'dividend_trades': int(((inc['side'] != 0) & (inc['dividend'] != 0)).sum())}
        for k in ('1x', '2x'):
            s[k] = stats(inc, f'net_{k}', idx)
            s[k]['pass'] = bool(s[k]['mean_trade'] > 0 and s[k]['ci'][0] > 0)
        f = inc.filter(~pl.col('flagged'))
        fidx = A.block_draws(f.height, BLOCK, B=BOOT_N, seed=SEED)
        s['flagged_out'] = {'flagged_sessions': inc.filter(pl.col('flagged')).select('day', 'C', 'C1559').to_dicts()}
        for k in ('1x', '2x'):
            s['flagged_out'][k] = stats(f, f'net_{k}', fidx)
            s['flagged_out'][k]['pass'] = bool(s['flagged_out'][k]['mean_trade'] > 0 and s['flagged_out'][k]['ci'][0] > 0)
        tr = inc.filter(pl.col('side') != 0)
        s['by_side'] = {lab: {'trades': int(g.height), 'mean_1x': float(g['net_1x'].mean())}
                        for lab, g in (('long', tr.filter(pl.col('side') == 1)), ('short', tr.filter(pl.col('side') == -1)))}
        s['by_year'] = [{'year': y, 'trades': int(g.height), 'mean_1x': float(g['net_1x'].mean()), 'mean_2x': float(g['net_2x'].mean())}
                        for (y,), g in sorted(tr.with_columns(pl.col('day').str.slice(0, 4).alias('y')).group_by('y'), key=lambda x: x[0])]
        s['gross_mean'] = float(tr['gross'].mean())
        s['dividend_mean'] = float(tr['dividend'].mean())
        s['borrow_mean'] = float(tr['borrow'].mean())
        summ['names'][nm] = s
    (OUT / 'h1_summary.json').write_text(json.dumps(summ, indent=1, default=str), encoding='utf-8')
    write_report(summ)
    for nm, s in summ['names'].items():
        print(nm, s['span'], 'trades', s['1x']['trades'], '1x', money(s['1x']['mean_trade']), s['1x']['ci'], 'PASS' if s['1x']['pass'] else 'FAIL',
              '| 2x', money(s['2x']['mean_trade']), s['2x']['ci'])
    return 0


def write_report(summ: dict) -> None:
    L = []
    w = L.append
    w('# H1 — overnight reversal of the late-day move (SPY, QQQ stock): the pre-registered test, run once')
    w('')
    w(f'PREREG_H1.md sha256 `{summ["prereg_sha256"]}` (the file as committed alone before this run). Written by `run_h1.py`; '
      'every number below is in `out/h1_summary.json` and every session in `out/h1_sessions.csv`.')
    w('')
    w('## Verdict (at 1x costs; the pass rule: mean $ a trade after costs > 0 and the 20-session block-bootstrap interval clear of zero, in each name)')
    w('')
    w('| name | span (signal sessions) | sessions in | trades | long / short / flat | mean $ a trade, 1x [95% block-20] | verdict 1x | mean $ a trade, 2x [95% block-20] | at 2x | win rate 1x | total 1x | worst trade 1x |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for nm, s in summ['names'].items():
        a, b = s['1x'], s['2x']
        w(f'| {nm} | {s["span"][0]} → {s["span"][1]} | {s["included"]:,} | {a["trades"]:,} | {s["long"]:,} / {s["short"]:,} / {s["flat"]:,} | '
          f'{money(a["mean_trade"])} [{money(a["ci"][0])}, {money(a["ci"][1])}] | **{"PASS" if a["pass"] else "FAIL"}** | '
          f'{money(b["mean_trade"])} [{money(b["ci"][0])}, {money(b["ci"][1])}] | {"clear of zero" if b["pass"] else "not clear"} | '
          f'{100 * a["win_rate"]:.1f}% | {money(a["total"], 0)} | {money(a["worst"], 0)} |')
    w('')
    both = all(s['1x']['pass'] for s in summ['names'].values())
    w(f'**H1 {"PASSES" if both else "FAILS"}** its pre-registered rule ({"both names pass" if both else "it needs both names"}).')
    w('')
    w('**Reading (descriptive, no verdict).** The mean is positive in both names at 1x and 2x, but neither 20-session block interval '
      'is clear of zero, so neither name passes and H1 fails as registered. ' + ' '.join(
          f'{nm}: the long trades (close below the 15:00 price) average {money(s["by_side"]["long"]["mean_1x"])} and the short trades '
          f'{money(s["by_side"]["short"]["mean_1x"])} a trade at 1x.' for nm, s in summ['names'].items()) +
      ' The positive mean comes from the long side, which carries the market\'s overnight drift as well as any reversal; the short '
      'side, which should profit from a reversal of an up-move into the close, loses after costs. The per-year means swing in sign.')
    w('')
    vf = OUT / 'h1_verify.json'
    if vf.exists():
        v = json.loads(vf.read_text(encoding='utf-8'))
        w(f'**Verification.** `verify_h1.py` re-derived {v["checked"]} random trades (25 a name, seed 20261023) from the raw files with plain '
          f'loops: {v["differences"]} differences; excluded sessions carrying a P&L: {len(v["excluded_with_pnl"])}.')
        w('')
    w('## Sensitivity (pre-specified): the flagged sessions out')
    w('')
    w('Flagged = the after-hours study\'s list (`afterhours_close_check.csv`) plus every session in the span where |EOD close − 15:59 bar close| > $0.25.')
    w('')
    w('| name | flagged sessions | trades left | mean $ a trade 1x [block-20] | 2x [block-20] | rule at 1x |')
    w('|---|---|---|---|---|---|')
    for nm, s in summ['names'].items():
        f = s['flagged_out']
        w(f'| {nm} | {len(f["flagged_sessions"])} | {f["1x"]["trades"]:,} | {money(f["1x"]["mean_trade"])} [{money(f["1x"]["ci"][0])}, {money(f["1x"]["ci"][1])}] | '
          f'{money(f["2x"]["mean_trade"])} [{money(f["2x"]["ci"][0])}, {money(f["2x"]["ci"][1])}] | {"clear" if f["1x"]["pass"] else "not clear"} |')
    w('')
    for nm, s in summ['names'].items():
        fl = s['flagged_out']['flagged_sessions']
        w(f'{nm} flagged: ' + (', '.join(f'{r["day"]} (EOD {r["C"]:.4f}, 15:59 {r["C1559"]:.4f})' for r in fl) if fl else 'none') + '.')
        w('')
    w('## The pieces of the mean (descriptive)')
    w('')
    w('| name | gross price P&L a trade | dividend a trade | borrow a trade | costs a trade 1x / 2x | trades over an ex-date | long trades, mean 1x | short trades, mean 1x |')
    w('|---|---|---|---|---|---|---|---|')
    for nm, s in summ['names'].items():
        w(f'| {nm} | {money(s["gross_mean"])} | {money(s["dividend_mean"])} | {money(-s["borrow_mean"])} | −2.00 / −4.00 | {s["dividend_trades"]} | '
          f'{s["by_side"]["long"]["trades"]:,}: {money(s["by_side"]["long"]["mean_1x"])} | {s["by_side"]["short"]["trades"]:,}: {money(s["by_side"]["short"]["mean_1x"])} |')
    w('')
    w('## Per year (descriptive only)')
    w('')
    years = sorted({y['year'] for s in summ['names'].values() for y in s['by_year']})
    w('| year | ' + ' | '.join(f'{nm} trades | {nm} mean 1x | {nm} mean 2x' for nm in summ['names']) + ' |')
    w('|---|' + '---|' * (3 * len(summ['names'])))
    for y in years:
        cells = []
        for nm, s in summ['names'].items():
            r = next((x for x in s['by_year'] if x['year'] == y), None)
            cells += [str(r['trades']), money(r['mean_1x']), money(r['mean_2x'])] if r else ['—', '—', '—']
        w(f'| {y} | ' + ' | '.join(cells) + ' |')
    w('')
    w('## Sessions left out')
    w('')
    for nm, s in summ['names'].items():
        ex = s['excluded']
        by = {}
        for r in ex:
            by.setdefault(r['excluded'], []).append(r['day'])
        w(f'**{nm}** — {len(ex)} of {s["calendar_sessions"]} calendar sessions in {FIRST[nm]} → {LAST}:')
        w('')
        for why, ds in sorted(by.items(), key=lambda x: -len(x[1])):
            lst = ', '.join(ds) if len(ds) <= 40 else f'{ds[0]} … {ds[-1]} ({len(ds)} sessions)'
            w(f'- {why}: {len(ds)} — {lst}')
        w('')
    w('## Notes on the run (deviations from the prereg\'s wording, none in the rule)')
    w('')
    w('- `run_h1.py` was run once for the result. It was re-run afterwards only to write this report\'s reading, verification line '
      'and these notes and to round the flagged closes to four decimals; every re-run left `out/h1_summary.json` and '
      '`out/h1_sessions.csv` byte-identical to the first run (sha256 checked).')
    w('- The prereg says the verifier reads the files "with pyarrow"; the container has no pyarrow, so `verify_h1.py` reads each '
      'Parquet file into Python lists with polars and does everything else in plain loops (its own session list, next session, EOD '
      'lookup by the `created` date, bar lookup by stamp, side, dividend, borrow, costs); it shares no code with `run_h1.py`.')
    w('- Stage 1 (`fetch/FETCH_NOTES.md`): 15 ThetaData requests, 142 KB; SPY EOD 2012–2016 NOT_FOUND and the SPY 2016 bar probe '
      'NaN, so SPY starts 2017-01-03 as the prereg states; no stored file was changed.')
    w('')
    (HERE / 'H1_REPORT.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
