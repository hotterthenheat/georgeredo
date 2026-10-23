#!/usr/bin/env python3
"""
run_h7_h8.py — H7 (the pre-FOMC drift) and H8 (the turn of the month), SPY and QQQ stock, as pre-registered in PREREG_H7.md and
PREREG_H8.md (committed alone in edca472; read them first).

    cd "research_notes/Edge search/H7_H8_H9"
    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 python3 -I -B run_h7_h8.py

Reads files only (no vendor call, no clock in the outputs): the stored 1-minute bars ($SP/theta/data/underlying/<name>/<day>.parquet),
ThetaData's stock EOD (run_h1.py's files) before 2025-10-13, Unusual Whales' daily bars (audit_lib.uw_daily) from 2025-10-13, H1's
dividend table, the after-hours close check, and data/fomc_statements_2012_2026.json. Writes out/h7_trades.csv, out/h8_trades.csv,
out/h7_h8_summary.json and H7_H8_REPORT.md. Statistics: audit_lib.block_draws / weights_from / pct_ci (read, not edited).
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import sys
from collections import defaultdict
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
FLAG_CSV = REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit' / 'out' / 'afterhours_close_check.csv'
FOMC = HERE / 'data' / 'fomc_statements_2012_2026.json'
OUT = HERE / 'out'

# ---- the pre-registered constants ------------------------------------------------------------------------------------------------------
NAMES = ('SPY', 'QQQ')
FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}
SPLIT = '2025-10-13'                     # official close: ThetaData EOD before, Unusual Whales' daily bar from
LAST = '2026-10-22'
FIRST_2PM = '2013-03-20'                 # the first scheduled statement released at 2:00 pm
SONG_BREAK = '2016-03-16'
SHARES = 100
H7_COST = {'1x': 0.015, '2x': 0.030}     # $ a share round trip: $0.01 auction entry + $0.005 exit half-spread; 2x
H8_COST = {'1x': 0.02, '2x': 0.04}       # $0.01 each way; 2x
FLAG_GAP = 0.25
BLOCK, BOOT_N, SEED = 20, 2000, 20261023
M_LEDGER = 13
ALPHA_BONF = 0.05 / (2 * M_LEDGER)
READING: list[str] = [                   # the report's closing notes, written after the first run (they change no number)
    '## Reading (descriptive; the verdicts are the tables above)',
    '**H7.** Both names pass at 1× and at 2×: SPY +$70.43 a trade [+14.64, +129.31] on 77 statements, QQQ +$69.59 [+23.10, +122.14] '
    'on 108 — about 19 and 21 bp of the position a trade (`out/h7_h8_tails.json`). **QQQ also clears the Bonferroni level at m = 13** '
    '(lower end +$6.96; none of the 2,000 draws has a mean at or below zero) **and is an EDGE under QUEUE rule 5; SPY does not** '
    '(lower end −$15.91; 15 of 2,000 draws at or below zero). The tail at α = 0.19 % rests on about two draws, so the QQQ call is '
    'coarse. SPY and QQQ trade the same nights, so the two passes are not independent evidence. The whole gross is the night: the '
    'official close → the 09:30 open averages +$74.36 (SPY) and +$72.97 (QQQ), the 09:30 open → 13:58 −$2.43 and −$1.88 — the shape '
    'Song reports for 2016–2023 (only the overnight gap survives). QQQ\'s 24 statements before March 2016 average −$3.00 [−20.84, +14.56]; '
    'the 84 from it +$90.33. The years swing: 2020 and 2022 carry large positive means (+$285 / +$273 and +$333 / +$399 a trade), 2021 '
    'is negative in both names and SPY\'s six 2026 statements average −$126.53. The intervals cleared although the mean (19–21 bp) is '
    'below the a-priori minimum detectable effect (35–37 bp): the pre-FOMC trades varied less than the all-session figure assumed. '
    'Every FOMC-eve night is also an H9 night; the repository\'s earlier overnight reads (H1\'s long legs +$22–27 a trade; the atlas\'s '
    '+4.9 / +6.8 bp, 43 names) are smaller than H7\'s night piece, so as far as those reads go the pre-FOMC night carries more than the '
    'ordinary overnight drift (not a test). No financing is charged (PREREG §2); one night of bill interest is about 1–1.5 bp of the '
    'position at 2023–2026 rates and near zero in 2013–2021.',
    '**What a pass does not yet mean (QUEUE rule 6).** H7 is not "an edge that works" until a FORWARD rule (this rule, its N, its pass '
    'line) is committed and met. The next scheduled statement is 2026-10-28, whose entry is the 2026-10-27 official close: a forward '
    'rule has to be committed before that close is read. At eight statements a year any useful forward N takes years.',
    '**H8.** SPY fails (+$134.00 a trade [−8.68, +283.42], 117 turns). QQQ passes at 1× by the narrowest margin (+$110.22 [+0.84, '
    '+218.26], 172 turns) and is not clear of zero at 2× ([−1.16, +216.26]) nor at the Bonferroni level ([−50.32, +282.68]); 49 '
    '(QQQ) and 61 (SPY) of the 2,000 draws are at or below zero. The means are about 39 and 31 bp of the position a turn, below the '
    'a-priori minimum detectable effect (56–60 bp). The years swing in sign (QQQ negative in 2014, 2015, 2021 and 2022), and the nine '
    '2026 turns (+$882.44 SPY, +$983.56 QQQ a trade) are about half of each total: without them QQQ\'s other 163 turns average about '
    '$62 a trade (arithmetic on the table, not a test). A long-only four-session hold also carries the market\'s ordinary drift, and the '
    'forgone bill interest (6–8 calendar days, 0–10 bp of the position over 2012–2026), which the rule does not charge, is larger than '
    'QQQ\'s 1× margin over zero. H8 is a fail for SPY and a marginal 1×-only pass for QQQ that is not an EDGE.',
    '## Notes on the run (none changes a rule)',
    '- `run_h7_h8.py` was run once for the result. It was re-run afterwards only to add the descriptive tail file '
    '(`out/h7_h8_tails.json`: draws at or below zero, means in bp) and to write the verification line and this reading into the report; '
    'every re-run left `out/h7_h8_summary.json`, `out/h7_trades.csv` and `out/h8_trades.csv` byte-identical to the first run (sha256 '
    'checked).',
    '- Unusual Whales\' daily closes equal ThetaData\'s EOD closes on all 252 sessions where both are on disk from 2025-06 (SPY and QQQ; '
    'checked after the run while reading the 2026 trades): the source switch at 2025-10-13 does not change a price.',
    '- No vendor fetch was made for the run (the Fed\'s calendar pages were read before the prereg). Sessions after 2026-10-22 were not read.',
]


def calendar() -> list[str]:
    return sorted(Path(f).name[:10] for f in glob.glob(str(BARS / 'QQQ' / '*.parquet')))


def fin(v):
    return float(v) if v is not None and math.isfinite(float(v)) else None


_BARS = {}


def bars(name: str, day: str) -> dict:
    """the 09:30 open, the 13:58 close and the 15:59 close of one session's file (None where unpriced or missing)"""
    k = (name, day)
    if k in _BARS:
        return _BARS[k]
    out = {'O930': None, 'X1358': None, 'C1559': None}
    p = BARS / name / f'{day}.parquet'
    if p.exists():
        t = pl.read_parquet(p).with_columns(pl.col('timestamp').dt.strftime('%H:%M').alias('hm'))
        for key, hm, field in (('O930', '09:30', 'open'), ('X1358', '13:58', 'close'), ('C1559', '15:59', 'close')):
            x = t.filter(pl.col('hm') == hm)
            if x.height:
                out[key] = fin(x[field][0])
    _BARS[k] = out
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


class Official:
    def __init__(self):
        self.TE, self.UW = theta_eod(), uw_closes()

    def __call__(self, nm, d):
        if d is None:
            return None, ''
        return (self.TE.get((nm, d)), 'theta_eod') if d < SPLIT else (self.UW.get((nm, d)), 'uw_daily')


def flag_set() -> set:
    return {(r['name'], r['day']) for r in pl.read_csv(FLAG_CSV, infer_schema_length=None).select('name', 'day').to_dicts()}


def flagged(nm, d, close, FL) -> bool:
    if (nm, d) in FL:
        return True
    c1559 = bars(nm, d)['C1559']
    return close is not None and c1559 is not None and abs(close - c1559) > FLAG_GAP


def build_h7(cal, OFF, div, FL) -> pl.DataFrame:
    prev = {cal[i]: cal[i - 1] for i in range(1, len(cal))}
    fomc = json.loads(FOMC.read_text(encoding='utf-8'))
    dates = sorted(e['date'] for e in fomc['scheduled'] if e['date'])
    rows = []
    for nm in NAMES:
        D = {d: v['amount'] for d, v in div[nm].items()}
        for a in dates:
            if a > LAST or a not in prev or prev[a] < FIRST[nm]:
                continue
            p = prev[a]
            cp, src = OFF(nm, p)
            b = bars(nm, a)
            r = {'name': nm, 'A': a, 'prev': p, 'C_prev': cp, 'C_prev_src': src, 'O930': b['O930'], 'X': b['X1358'], 'div': D.get(a, 0.0)}
            why = []
            if a < FIRST_2PM:
                why.append('statement not released at 2:00 pm (before 2013-03-20)')
            if cp is None:
                why.append(f'no official close on the previous session {p}')
            if b['X1358'] is None:
                why.append('no priced 13:58 bar')
            r['excluded'] = '; '.join(why)
            if not why:
                r['gross'] = SHARES * (b['X1358'] - cp)
                r['dividend'] = SHARES * r['div']
                r['night'] = SHARES * (b['O930'] - cp) if b['O930'] is not None else None
                r['day'] = SHARES * (b['X1358'] - b['O930']) if b['O930'] is not None else None
                for k, c in H7_COST.items():
                    r[f'cost_{k}'] = SHARES * c
                    r[f'net_{k}'] = r['gross'] + r['dividend'] - r[f'cost_{k}']
                r['flagged'] = flagged(nm, p, cp, FL)
            rows.append(r)
    return pl.DataFrame(rows, infer_schema_length=None)


def build_h8(cal, OFF, div, FL) -> pl.DataFrame:
    bym = defaultdict(list)
    for d in cal:
        bym[d[:7]].append(d)
    months = sorted(bym)
    rows = []
    for nm in NAMES:
        D = {d: v['amount'] for d, v in div[nm].items()}
        for i, m in enumerate(months[:-1]):
            s, nx = bym[m], bym[months[i + 1]]
            if len(s) < 2 or len(nx) < 3:
                continue
            e, last, x = s[-2], s[-1], nx[2]
            if e < FIRST[nm] or x > LAST:
                continue
            ce, se = OFF(nm, e)
            cx, sx = OFF(nm, x)
            held = [d for d in cal if e < d <= x]
            dv = sum(D.get(d, 0.0) for d in held)
            r = {'name': nm, 'M': m, 'E': e, 'L': last, 'X': x, 'C_E': ce, 'C_E_src': se, 'C_X': cx, 'C_X_src': sx, 'div': dv,
                 'div_dates': ' '.join(d for d in held if d in D)}
            why = []
            if ce is None:
                why.append(f'no official close on the entry session {e}')
            if cx is None:
                why.append(f'no official close on the exit session {x}')
            r['excluded'] = '; '.join(why)
            if not why:
                r['gross'] = SHARES * (cx - ce)
                r['dividend'] = SHARES * dv
                for k, c in H8_COST.items():
                    r[f'cost_{k}'] = SHARES * c
                    r[f'net_{k}'] = r['gross'] + r['dividend'] - r[f'cost_{k}']
                r['flagged'] = flagged(nm, e, ce, FL) or flagged(nm, x, cx, FL)
            rows.append(r)
    return pl.DataFrame(rows, infer_schema_length=None)


def series(cal, nm, trades: pl.DataFrame, key: str, col: str):
    """every calendar session of the name's span; S = the trade's net on its key session, N = 1 there"""
    ses = [d for d in cal if FIRST[nm] <= d <= LAST]
    pos = {d: i for i, d in enumerate(ses)}
    S, N = np.zeros(len(ses)), np.zeros(len(ses))
    for d, v in trades.select(key, col).iter_rows():
        S[pos[d]] += v
        N[pos[d]] += 1
    return S, N


def stats(S, N, W, tr: np.ndarray) -> dict:
    mt = (W @ S) / np.maximum(W @ N, 1)
    out = {'trades': int(N.sum()), 'mean_trade': float(S.sum() / N.sum()) if N.sum() else float('nan'), 'ci': A.pct_ci(mt)}
    x = mt[np.isfinite(mt)]
    out['ci_bonf'] = (float(np.percentile(x, 100 * ALPHA_BONF / 2)), float(np.percentile(x, 100 * (1 - ALPHA_BONF / 2))))
    out['win_rate'] = float((tr > 0).mean()) if tr.size else float('nan')
    out['total'] = float(tr.sum())
    out['worst'] = float(tr.min()) if tr.size else float('nan')
    out['best'] = float(tr.max()) if tr.size else float('nan')
    out['median'] = float(np.median(tr)) if tr.size else float('nan')
    return out


def summarise(cal, t: pl.DataFrame, key: str, hyp: str) -> dict:
    res = {}
    for nm in NAMES:
        u = t.filter(pl.col('name') == nm)
        inc = u.filter(pl.col('excluded') == '').sort(key)
        n_ses = len([d for d in cal if FIRST[nm] <= d <= LAST])
        W = A.weights_from(A.block_draws(n_ses, BLOCK, B=BOOT_N, seed=SEED), n_ses)
        s = {'span': [inc[key].min(), inc[key].max()], 'calendar_sessions': n_ses, 'listed': u.height, 'included': inc.height,
             'excluded': u.filter(pl.col('excluded') != '').select(key, 'excluded').to_dicts()}
        for k in ('1x', '2x'):
            S, N = series(cal, nm, inc, key, f'net_{k}')
            s[k] = stats(S, N, W, inc[f'net_{k}'].to_numpy())
            s[k]['pass'] = bool(s[k]['mean_trade'] > 0 and s[k]['ci'][0] > 0)
        s['edge_m13'] = bool(s['1x']['pass'] and s['1x']['ci_bonf'][0] > 0)
        s['gross_mean'] = float(inc['gross'].mean())
        s['dividend_mean'] = float(inc['dividend'].mean())
        s['dividend_trades'] = inc.filter(pl.col('dividend') != 0).select(key, 'dividend').to_dicts()
        s['by_year'] = [{'year': y, 'trades': int(g.height), 'mean_1x': float(g['net_1x'].mean()), 'mean_2x': float(g['net_2x'].mean()),
                         'win_rate': float((g['net_1x'] > 0).mean())}
                        for (y,), g in sorted(inc.with_columns(pl.col(key).str.slice(0, 4).alias('y')).group_by('y'), key=lambda x: x[0])]
        fo = inc.filter(~pl.col('flagged'))
        S, N = series(cal, nm, fo, key, 'net_1x')
        s['flagged_out'] = {'flagged': inc.filter(pl.col('flagged')).select(key).to_series().to_list(), '1x': stats(S, N, W, fo['net_1x'].to_numpy())}
        if hyp == 'H7':
            s['night_mean'] = float(inc['night'].mean())
            s['day_mean'] = float(inc['day'].mean())
            sub = {}
            for lab, f in (('to 2016-01-27', pl.col('A') < SONG_BREAK), ('from 2016-03-16', pl.col('A') >= SONG_BREAK)):
                g = inc.filter(f)
                if g.height:
                    S, N = series(cal, nm, g, key, 'net_1x')
                    sub[lab] = stats(S, N, W, g['net_1x'].to_numpy())
            s['sub_spans'] = sub
        res[nm] = s
    return res


def tails(cal, h7: pl.DataFrame, h8: pl.DataFrame) -> dict:
    """descriptive, not pre-registered (its own file; no verdict): how many of the same 2,000 draws have a 1x mean at or below
    zero, and each rule's mean net in bp of the position (net / (100 x entry close))"""
    out = {}
    for h, t, key, ent in (('H7', h7, 'A', 'C_prev'), ('H8', h8, 'E', 'C_E')):
        for nm in NAMES:
            inc = t.filter((pl.col('name') == nm) & (pl.col('excluded') == '')).sort(key)
            n_ses = len([d for d in cal if FIRST[nm] <= d <= LAST])
            W = A.weights_from(A.block_draws(n_ses, BLOCK, B=BOOT_N, seed=SEED), n_ses)
            S, N = series(cal, nm, inc, key, 'net_1x')
            mt = (W @ S) / np.maximum(W @ N, 1)
            bp = (1e4 * inc['net_1x'] / (SHARES * inc[ent])).to_numpy()
            out[f'{h} {nm}'] = {'draws_le_0': int((mt <= 0).sum()), 'draws': int(mt.size), 'mean_bp_1x': float(bp.mean()),
                                'median_bp_1x': float(np.median(bp)), 'plain_mean_1x': float(inc['net_1x'].sum() / inc.height)}
    (OUT / 'h7_h8_tails.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    return out


def money(x, d=2):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:+,.{d}f}'


def main() -> int:
    OUT.mkdir(exist_ok=True)
    cal = calendar()
    OFF = Official()
    div = json.loads(DIV.read_text(encoding='utf-8'))
    FL = flag_set()
    h7 = build_h7(cal, OFF, div, FL)
    h8 = build_h8(cal, OFF, div, FL)
    h7.write_csv(OUT / 'h7_trades.csv')
    h8.write_csv(OUT / 'h8_trades.csv')
    summ = {'prereg_sha256': {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ('PREREG_H7.md', 'PREREG_H8.md', 'PREREG_H9.md')},
            'fomc_list_sha256': hashlib.sha256(FOMC.read_bytes()).hexdigest(), 'seed': SEED, 'draws': BOOT_N, 'block': BLOCK,
            'm_ledger': M_LEDGER, 'alpha_bonf': ALPHA_BONF,
            'H7': summarise(cal, h7, 'A', 'H7'), 'H8': summarise(cal, h8, 'E', 'H8')}
    (OUT / 'h7_h8_summary.json').write_text(json.dumps(summ, indent=1, default=str), encoding='utf-8')
    tails(cal, h7, h8)
    write_report(summ)
    for h in ('H7', 'H8'):
        for nm in NAMES:
            s = summ[h][nm]
            print(h, nm, s['span'], 'trades', s['1x']['trades'], '1x', money(s['1x']['mean_trade']), [round(v, 2) for v in s['1x']['ci']],
                  'PASS' if s['1x']['pass'] else 'FAIL', '| 2x', money(s['2x']['mean_trade']), [round(v, 2) for v in s['2x']['ci']],
                  '| bonf', [round(v, 2) for v in s['1x']['ci_bonf']])
    return 0


def write_report(summ: dict) -> None:
    L = []
    w = L.append
    ph = summ['prereg_sha256']
    w('# H7 (pre-FOMC drift) and H8 (turn of the month), SPY and QQQ stock: the pre-registered tests, run once')
    w('')
    w(f'PREREG_H7.md sha256 `{ph["PREREG_H7.md"]}`; PREREG_H8.md sha256 `{ph["PREREG_H8.md"]}`; PREREG_H9.md sha256 `{ph["PREREG_H9.md"]}` '
      '(the three files as committed alone, `edca472`, before this run). The FOMC list `data/fomc_statements_2012_2026.json` sha256 '
      f'`{summ["fomc_list_sha256"]}`. Written by `run_h7_h8.py`; every number below is in `out/h7_h8_summary.json`, every trade in '
      '`out/h7_trades.csv` and `out/h8_trades.csv`.')
    w('')
    w('Rules. **H7**: buy 100 shares at the official close of the session before each scheduled FOMC statement released at 2:00 pm '
      '(2013-03-20 on), sell at the close of the 13:58 bar on the statement day; $0.01 a share in the auction + $0.005 at the exit '
      '($1.50 a trade at 1×, $3.00 at 2×); a dividend whose ex-date is the statement day is paid. **H8**: buy 100 shares at the official '
      'close of the second-to-last session of each month, sell at the official close of the third session of the next month; $0.01 '
      'a share each way ($2.00 at 1×, $4.00 at 2×); dividends with ex-dates after entry through exit are paid. Official close: ThetaData '
      'EOD before 2025-10-13, Unusual Whales\' daily bar from it. Interval: the 20-session moving-block bootstrap over every calendar '
      f'session of the name\'s span (sessions with no trade contribute no trade), {summ["draws"]:,} draws, seed {summ["seed"]} '
      '(`audit_lib.block_draws`, rng seed + 7919 × 20), the same draws for 1× and 2×. Pass per name: mean at 1× > 0 and the 95 % '
      f'interval clear of zero. Bonferroni: m = {summ["m_ledger"]} (8 ledger rows with H7, H8, H9 + 5 pre-ledger failures), '
      f'α = 0.05 ÷ (2 × {summ["m_ledger"]}) = {100 * summ["alpha_bonf"]:.4f} %.')
    w('')
    for h, title, key in (('H7', 'H7 — pre-FOMC drift (close before the statement → 13:59 on the statement day)', 'A'),
                          ('H8', 'H8 — turn of the month (close of the second-to-last session → close of the third session of the next month)', 'E')):
        w(f'## {title}')
        w('')
        w('| name | span | trades | mean $ a trade, 1× [95 % block-20] | verdict | mean $ a trade, 2× [95 % block-20] | at 2× | '
          f'1× at the Bonferroni level (m = {summ["m_ledger"]}) | EDGE | win rate 1× | median 1× | worst / best 1× | total 1× |')
        w('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for nm, s in summ[h].items():
            a, b = s['1x'], s['2x']
            w(f'| {nm} | {s["span"][0]} → {s["span"][1]} | {a["trades"]} | {money(a["mean_trade"])} [{money(a["ci"][0])}, {money(a["ci"][1])}] | '
              f'**{"PASS" if a["pass"] else "FAIL"}** | {money(b["mean_trade"])} [{money(b["ci"][0])}, {money(b["ci"][1])}] | '
              f'{"clear of zero" if b["pass"] else "not clear"} | [{money(a["ci_bonf"][0])}, {money(a["ci_bonf"][1])}] | {"yes" if s["edge_m13"] else "no"} | '
              f'{100 * a["win_rate"]:.1f} % | {money(a["median"])} | {money(a["worst"], 0)} / {money(a["best"], 0)} | {money(a["total"], 0)} |')
        w('')
        w(' '.join(f'**{nm}: {"PASS" if s["1x"]["pass"] else "FAIL"}{" — and an EDGE at the Bonferroni level" if s["edge_m13"] else ""}.**'
                   for nm, s in summ[h].items()))
        w('')
        w('Descriptive (no verdict):')
        w('')
        cols = '| name | gross a trade | dividend a trade | costs 1× / 2× |' + (' night (close → 09:30 open) | day (09:30 open → 13:58 close) |' if h == 'H7' else '') + \
            ' flagged closes out: trades, mean 1× [95 %] |'
        w(cols)
        w('|---|---|---|---|' + ('---|---|' if h == 'H7' else '') + '---|')
        for nm, s in summ[h].items():
            c = '−1.50 / −3.00' if h == 'H7' else '−2.00 / −4.00'
            fo = s['flagged_out']['1x']
            extra = f' {money(s["night_mean"])} | {money(s["day_mean"])} |' if h == 'H7' else ''
            w(f'| {nm} | {money(s["gross_mean"])} | {money(s["dividend_mean"])} | {c} |{extra} {fo["trades"]}, {money(fo["mean_trade"])} '
              f'[{money(fo["ci"][0])}, {money(fo["ci"][1])}] |')
        w('')
        for nm, s in summ[h].items():
            fl = s['flagged_out']['flagged']
            dv = s['dividend_trades']
            w(f'{nm}: flagged trades removed in the sensitivity: {", ".join(fl) if fl else "none"}; trades with a dividend term: '
              + (', '.join(f'{r[key]} ({money(r["dividend"])})' for r in dv) if dv else 'none') + '.')
            w('')
        if h == 'H7':
            w('Before and from Song\'s March 2016 break (descriptive):')
            w('')
            w('| name | statements | trades | mean 1× [95 % block-20] | win rate |')
            w('|---|---|---|---|---|')
            for nm, s in summ[h].items():
                for lab, x in s['sub_spans'].items():
                    w(f'| {nm} | {lab} | {x["trades"]} | {money(x["mean_trade"])} [{money(x["ci"][0])}, {money(x["ci"][1])}] | {100 * x["win_rate"]:.1f} % |')
            w('')
        w('Per calendar year (descriptive):')
        w('')
        w('| year | ' + ' | '.join(f'{nm} trades | {nm} mean 1× | {nm} mean 2× | {nm} win' for nm in summ[h]) + ' |')
        w('|---|' + '---|' * (4 * len(summ[h])))
        yrs = sorted({y['year'] for s in summ[h].values() for y in s['by_year']})
        for y in yrs:
            cells = []
            for nm, s in summ[h].items():
                r = next((x for x in s['by_year'] if x['year'] == y), None)
                cells += [str(r['trades']), money(r['mean_1x']), money(r['mean_2x']), f'{100 * r["win_rate"]:.0f} %'] if r else ['—'] * 4
            w(f'| {y} | ' + ' | '.join(cells) + ' |')
        w('')
        for nm, s in summ[h].items():
            ex = s['excluded']
            w(f'{nm} listed {s["listed"]}, included {s["included"]}; excluded: ' +
              ('; '.join(f'{r[key]} ({r["excluded"]})' for r in ex) if ex else 'none') + '.')
            w('')
    vf = OUT / 'h7_h8_verify.json'
    if vf.exists():
        v = json.loads(vf.read_text(encoding='utf-8'))
        w('## Verification')
        w('')
        w(f'`verify_h7_h8.py` re-derived {v["checked"]} trades ({v["by"]}) from the raw files with plain loops and no code shared with the run: '
          f'{v["differences"]} differences in {v["fields"]} fields; rows carrying a P&L while excluded: {v["excluded_with_pnl"]}; '
          f'statement dates on disk the run did not list: {v["missing_dates"]}.')
        w('')
    for line in READING:
        w(line)
        w('')
    (HERE / 'H7_H8_REPORT.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
