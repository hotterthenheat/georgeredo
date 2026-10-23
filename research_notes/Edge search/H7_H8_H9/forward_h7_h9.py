"""
forward_h7_h9.py — the forward runner of the edge-search queue's H7 (the pre-FOMC drift; FORWARD_RULE_H7.md, committed alone in
fcc1f4d, the rule of PREREG_H7.md, edca472), run by step 8 of scripts/daily_forward.py beside H5 and H6 (../H5_H6/edge_forward.py).
Nothing here reads a session before 2026-10-23. (The file keeps its name; H9, the overnight drift of PREREG_H9.md, was withdrawn
from the forward job by the owner on 2026-10-23 before any forward datum was read — its row builder, its half-day collection and
its dividend table were removed with it; PREREG_H9.md, edca472, is unchanged.)

H7 (SPY, QQQ; every scheduled 2:00 pm FOMC statement from 2026-10-28): buy 100 at the official close of the session before the
statement date A, sell at the close of A's 1-minute bar stamped 13:58; net = 100 (X − C_prev) + 100 DIV(ex-date A) − $1.50 (2×
$3.00). A file in the layout with no priced 13:58 bar → the meeting is excluded and listed (no trade); a statement whose
calendar time is not 14:00, or on a day that is not a full session → excluded and listed. N: SPY 366 trades, QQQ 483.

Inputs, all from the daily job: the official close = Unusual Whales' daily bar `r` close (paper_audit.OfficialCloses sources
'uw_1d' / 'uw_1d_live_tracker'; any other source is refused, never substituted); the 1-minute bars = the layout's
data/underlying/<name>/<D>.parquet (ThetaData stock_history_ohlc 1m; a file its manifest refuses is absent); the FOMC calendar =
data/macro_events_2022_2027.json FOMC_DECISION rows from 2026-10-28, cross-checked against the meetings of
data/fomc_statements_2012_2026.json; the sessions = scripts/eod_recorder.py HOLIDAYS (half days are sessions); dividends =
data/dividends_h7.json — H7's own table: only an ex-date that is a statement date A can pay H7 a dividend, so it lists the
ex-dates that fall on scheduled statement dates, with a complete_through per name (FORWARD_RULE_H7.md section 2's terms). A
statement past the calendar's last year, the holidays' last year or the dividend table's complete_through fails loudly and
waits; a dividend is never taken as 0 for want of a row. The job collects no half day: should the session before a statement
ever be a half day, its official close is not on disk and the trade fails loudly (none through 2027).

The job hands `days` = its complete forward sessions; `last` = the newest of them. A row whose inputs are all at or before `last`
must be computable, else the run says why (`<day> <step>: <why>`) and that name's series stops there (rows are counted in
calendar order: the count is the final prefix); a row that needs a later session waits silently. Idempotent and append-only
(one row a key; a key twice or a foreign header refuses the file). Verdict: none before N; at N, on the first N only, mean > 0
with the 20-session block bootstrap's 95 % lower end > 0 (seed 20261023) ⇒ CONFIRMED, else NOT CONFIRMED — written once to
verdicts.json, never revised. A checkpoint every 8 trades, labelled "no verdict". The dividend table is extended by hand, in a
commit that names the declaration read (the note in the file says how).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for _p in (REPO / 'scripts', REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit', REPO / 'research_notes' / 'Edge search' / 'H5_H6'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import audit_lib as AL  # noqa: E402
import eod_recorder as R  # noqa: E402
import edge_forward as EF  # noqa: E402  (append_rows, read_rows, EdgeDataError — the H5/H6 runner's file rules)
import paper_backtest as B  # noqa: E402

VERSION = 'edge-forward-h7-2026-10-23.2'                # .2: H9 withdrawn (no H7 figure changes)
RULE_COMMITS = {'H7': 'fcc1f4d'}                         # FORWARD_RULE_H7.md (its rule PREREG_H7.md, edca472)
EdgeDataError = EF.EdgeDataError

# ---- the rules -----------------------------------------------------------------------------------------------------------------------
NAMES = ('SPY', 'QQQ')
SERIES_START = '2026-10-23'               # the forward series (H7's calendar sessions)
H7_START = '2026-10-28'                   # the first forward statement (entry: the 2026-10-27 close)
H7_EXIT_J = B.MINUTE_OF('13:58')          # 268
SHARES = 100
H7_COST = {'1x': 1.50, '2x': 3.00}        # 100 × ($0.01 auction + $0.005 exit); 2×
N_RULE = {('H7', 'SPY'): 366, ('H7', 'QQQ'): 483}
BLOCK, BOOT_N, SEED = 20, 2000, 20261023
H7_CHECKPOINT, H7_CI_FROM = 8, 16         # a checkpoint every 8 trades; its interval from the 16th trade
OFFICIAL_SOURCES = ('uw_1d', 'uw_1d_live_tracker')

MACRO = REPO / 'data' / 'macro_events_2022_2027.json'
FOMC_JSON = HERE / 'data' / 'fomc_statements_2012_2026.json'
DIVS = HERE / 'data' / 'dividends_h7.json'
FWD = HERE / 'forward'
H7_COLS = ('name', 'A', 'prev', 'status', 'excluded', 'C_prev', 'C_prev_src', 'O930', 'X', 'div', 'gross', 'dividend', 'night', 'day',
           'cost_1x', 'net_1x', 'cost_2x', 'net_2x', 'version', 'written_at')


def default_paths(folder: Path | None = None) -> dict:
    f = Path(folder) if folder else FWD
    return {'h7': f / 'h7_trades.csv', 'report': f / 'H7_FORWARD_REPORT.md', 'verdicts': f / 'verdicts.json'}


# ---- the session calendar --------------------------------------------------------------------------------------------------------------

def holidays_last_year() -> int:
    return max(int(d[:4]) for d in R.HOLIDAYS)


def _covered(day: str, step: str) -> None:
    if int(day[:4]) > holidays_last_year():
        raise EdgeDataError(day, step, f'past the session calendar (scripts/eod_recorder.py HOLIDAYS ends with {holidays_last_year()}): '
                                       'extend HOLIDAYS / HALF_DAYS first')


def is_session(day: str) -> bool:
    return R.is_trading_day(day)


def next_session(day: str) -> str:
    d = dt.date.fromisoformat(day)
    for _ in range(15):
        d += dt.timedelta(days=1)
        _covered(d.isoformat(), 'calendar')
        if is_session(d.isoformat()):
            return d.isoformat()
    raise EdgeDataError(day, 'calendar', 'no session in the next two weeks')


def prev_session(day: str) -> str:
    d = dt.date.fromisoformat(day)
    for _ in range(15):
        d -= dt.timedelta(days=1)
        if is_session(d.isoformat()):
            return d.isoformat()
    raise EdgeDataError(day, 'calendar', 'no session in the two weeks before')


def sessions(a: str, b: str) -> list[str]:
    out, d = [], dt.date.fromisoformat(a)
    while d.isoformat() <= b:
        _covered(d.isoformat(), 'calendar')
        if is_session(d.isoformat()):
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


# ---- the FOMC calendar -----------------------------------------------------------------------------------------------------------------

_MONTHS = {m: i for i, m in enumerate(('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                                       'November', 'December'), 1)}


def meeting_end(text: str) -> str | None:
    """'October 27-28 - 2026', 'June 8-9* - 2027', 'April 30-May 1 - 2024' → the statement date (the meeting's last day)"""
    m = re.match(r'\s*([A-Za-z]+)\s+(\d+)\*?\s*-\s*(?:([A-Za-z]+)\s+)?(\d+)\*?\s*-\s*(\d{4})', text)
    if not m:
        return None
    mon = _MONTHS.get(m.group(3) or m.group(1))
    return None if mon is None else dt.date(int(m.group(5)), mon, int(m.group(4))).isoformat()


def fomc_calendar(macro: Path = MACRO, committed: Path = FOMC_JSON) -> tuple[list[dict], str]:
    """the forward statements [{'date', 'time_et', 'source'}] from H7_START, and the last day the calendar covers (31 December of
    its last year). Cross-checked: inside the years both files cover, the macro calendar's dates are the committed list's
    meetings exactly — a disagreement is a loud failure, never a pick"""
    rows = json.loads(Path(macro).read_text(encoding='utf-8'))
    dec = [r for r in rows if r.get('event') == 'FOMC_DECISION']
    if not dec:
        raise EdgeDataError(H7_START, 'h7-calendar', f'{Path(macro).name} has no FOMC_DECISION row')
    last_year = max(int(r['date'][:4]) for r in dec)
    fwd = sorted(({'date': r['date'], 'time_et': r.get('time_et'), 'source': r.get('source')} for r in dec if r['date'] >= H7_START),
                 key=lambda r: r['date'])
    js = json.loads(Path(committed).read_text(encoding='utf-8'))
    theirs = set()
    for e in js.get('scheduled', []):
        d = e.get('date') or meeting_end(e.get('meeting') or '')
        if d is None:
            raise EdgeDataError(H7_START, 'h7-calendar', f'{Path(committed).name}: a meeting with no readable date: {e.get("meeting")!r}')
        theirs.add(d)
    hi = max(theirs)
    hi_year = int(hi[:4])
    mine = {r['date'] for r in fwd if int(r['date'][:4]) <= hi_year}
    theirs_fwd = {d for d in theirs if d >= H7_START}
    if mine != theirs_fwd:
        raise EdgeDataError(H7_START, 'h7-calendar', f'the two FOMC calendars disagree from {H7_START}: only in {Path(macro).name} '
                                                     f'{sorted(mine - theirs_fwd)}, only in {Path(committed).name} {sorted(theirs_fwd - mine)}')
    return fwd, f'{last_year}-12-31'


# ---- dividends -------------------------------------------------------------------------------------------------------------------------

def load_divs(path: Path = DIVS) -> dict:
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    for nm in NAMES:
        if nm not in d or 'complete_through' not in d[nm] or 'ex' not in d[nm]:
            raise EdgeDataError(SERIES_START, 'dividends', f'{Path(path).name}: no complete_through / ex for {nm}')
    return d


def dividend(divs: dict, name: str, ex_date: str, step: str) -> float:
    """the cash dividend per share whose ex-date is `ex_date` (a statement date A); 0 only when the table is complete through that
    date and lists none"""
    t = divs[name]
    if ex_date > t['complete_through']:
        raise EdgeDataError(ex_date, step, f'{name}: the dividend table is complete only through {t["complete_through"]} — an ex-date may be '
                                           f'missing; read the fund\'s declaration and extend data/dividends_h7.json')
    row = t['ex'].get(ex_date)
    if row is None:
        return 0.0
    if row.get('amount') is None:
        raise EdgeDataError(ex_date, step, f'{name}: ex-date {ex_date} is listed with no amount yet — add the declared amount')
    return float(row['amount'])


# ---- the inputs ------------------------------------------------------------------------------------------------------------------------

class Inputs:
    def __init__(self, layout: Path, official):
        self.src = B.ParquetSource(Path(layout), keep=4)
        self.official = official

    def close(self, name: str, day: str, step: str) -> tuple[float, str]:
        v = self.official(name, day)
        c, s = (v if isinstance(v, tuple) else (v, 'uw_1d'))
        if c is None:
            raise EdgeDataError(day, step, f'no official close for {name} on disk (UW\'s daily bar)')
        if s not in OFFICIAL_SOURCES:
            raise EdgeDataError(day, step, f'{name}\'s official close on disk is from {s}, not UW\'s daily bar (the rule\'s source) — '
                                           'nothing is substituted; fetch UW\'s daily bar for the day')
        return float(c), s

    def has_file(self, name: str, day: str) -> bool:
        f = self.src.under_file(name, day)
        return f.exists() and not self.src.refused(f, day)

    def bar(self, name: str, day: str, j: int, field: str) -> float | None:
        b = self.src.bars(name, day) or {'j': []}
        if j not in b['j']:
            return None
        v = b[field][b['j'].index(j)]
        return float(v) if v is not None and math.isfinite(float(v)) and float(v) > 0 else None


def now_z() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---- H7 --------------------------------------------------------------------------------------------------------------------------------

def h7_row(name: str, st: dict, inp: Inputs, divs: dict) -> dict:
    a = st['date']
    p = prev_session(a)
    row = {c: None for c in H7_COLS}
    row.update(name=name, A=a, prev=p, version=VERSION, written_at=now_z())
    why = []
    if (st.get('time_et') or '') != '14:00':
        why.append(f'statement time {st.get("time_et")!r}, not 2:00 pm')
    if not is_session(a) or R.is_half_day(a):
        why.append('the statement date is not a full session')
    if why:
        row.update(status='excluded', excluded='; '.join(why))
        return row
    c, s = inp.close(name, p, 'h7-official-close')
    if not inp.has_file(name, a):
        raise EdgeDataError(a, 'h7-bars', f'{name} 1-minute bars of {a} are not in the layout')
    x = inp.bar(name, a, H7_EXIT_J, 'c')
    o = inp.bar(name, a, 0, 'o')
    row.update(C_prev=c, C_prev_src=s, O930=o, X=x)
    if x is None:
        row.update(status='excluded', excluded='no priced 13:58 bar')
        return row
    dv = dividend(divs, name, a, 'h7-dividend')
    gross = SHARES * (x - c)
    row.update(status='trade', excluded='', div=dv, gross=gross, dividend=SHARES * dv,
               night=None if o is None else SHARES * (o - c), day=None if o is None else SHARES * (x - o))
    for k, cost in H7_COST.items():
        row[f'cost_{k}'] = cost
        row[f'net_{k}'] = gross + SHARES * dv - cost
    return row


def run_h7(inp: Inputs, last: str, divs: dict, paths: dict, log=None, calendar=None) -> tuple[list, list]:
    added, fails = [], []
    try:
        cal, cal_end = calendar or fomc_calendar()
    except EdgeDataError as e:
        return [], [f'{e.day} {e.step}: {e.why}']
    if last > cal_end:
        fails.append(f'{last} h7-calendar: the FOMC calendar ends {cal_end}: add the Fed\'s scheduled meetings for the next year to '
                     f'{MACRO.name} (scheduled only, with the source) — no statement is judged past it')
    have = {(r['name'], r['A']) for r in EF.read_rows(paths['h7'])}
    for nm in NAMES:
        for st in cal:
            if st['date'] > min(last, cal_end):
                break
            if (nm, st['date']) in have:
                continue
            try:
                row = h7_row(nm, st, inp, divs)
            except EdgeDataError as e:
                fails.append(f'{e.day} {e.step}: {e.why}')
                break
            added += [f'{k[0]}/{k[1]}' for k in EF.append_rows(paths['h7'], H7_COLS, [row], ('name', 'A'))]
            if log:
                log.info('edge H7 %s %s: %s', nm, st['date'], f'{row["net_1x"]:+.2f} after costs' if row['status'] == 'trade' else
                         f'excluded ({row["excluded"]})')
    return added, fails


# ---- the statistic, the verdicts, the report -------------------------------------------------------------------------------------------

def interval(S: np.ndarray, N: np.ndarray) -> list:
    n = S.size
    idx = AL.block_draws(n, BLOCK, B=BOOT_N, seed=SEED)
    m = S[idx].sum(1) / np.maximum(N[idx].sum(1), 1)          # a draw with no trade counts as 0, as in the test
    return list(AL.pct_ci(m))


def h7_series(rows: list[dict], name: str, upto: int | None = None, col: str = 'net_1x') -> tuple[np.ndarray, np.ndarray, list]:
    """every session from SERIES_START through the last counted trade's A (or the `upto`-th trade's); S and N on A"""
    tr = sorted((r for r in rows if r['name'] == name and r['status'] == 'trade'), key=lambda r: r['A'])
    if upto is not None:
        tr = tr[:upto]
    if not tr:
        return np.zeros(0), np.zeros(0), []
    ses = sessions(SERIES_START, tr[-1]['A'])
    pos = {d: i for i, d in enumerate(ses)}
    S, N = np.zeros(len(ses)), np.zeros(len(ses))
    for r in tr:
        S[pos[r['A']]] += float(r[col])
        N[pos[r['A']]] += 1
    return S, N, tr


def evaluate(test: str, name: str, rows: list[dict]) -> dict:
    """H7's count, mean and interval for one name; the verdict only at N (`test` is 'H7', the key of N_RULE and verdicts.json)"""
    n_rule = N_RULE[(test, name)]
    counted = len([r for r in rows if r['name'] == name and r['status'] == 'trade'])
    S, N, tr = h7_series(rows, name, upto=n_rule)
    S2, _, _ = h7_series(rows, name, upto=n_rule, col='net_2x')
    through = tr[-1]['A'] if tr else None
    ci_ok = len(tr) >= H7_CI_FROM
    out = {'test': test, 'name': name, 'N': n_rule, 'counted': counted, 'trades': int(N.sum()), 'mean_1x': None, 'mean_2x': None,
           'ci': None, 'verdict': 'no verdict', 'through': through}
    if N.sum() > 0:
        out['mean_1x'], out['mean_2x'] = float(S.sum() / N.sum()), float(S2.sum() / N.sum())
        if ci_ok or counted >= n_rule:                       # at N the verdict's interval, whatever the checkpoint floor
            out['ci'] = interval(S, N)
    if counted >= n_rule:
        ok = out['mean_1x'] is not None and out['mean_1x'] > 0 and out['ci'] is not None and math.isfinite(out['ci'][0]) and out['ci'][0] > 0
        out['verdict'] = 'CONFIRMED' if ok else 'NOT CONFIRMED'
    return out


def record_verdict(path: Path, ev: dict) -> dict:
    """written once: a verdict already there is returned unchanged, never revised"""
    key = f'{ev["test"]} {ev["name"]}'
    have = json.loads(Path(path).read_text()) if Path(path).exists() else {}
    if key in have:
        return {**have[key], 'counted': ev['counted']}
    if ev['verdict'] == 'no verdict':
        return ev
    have[key] = {**ev, 'written_at': now_z(), 'version': VERSION, 'rule': RULE_COMMITS[ev['test']]}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix('.part')
    tmp.write_text(json.dumps(have, indent=1))
    tmp.replace(path)
    return have[key]


def checkpoints(rows: list[dict], name: str) -> list[dict]:
    """H7's descriptive checkpoints at 8, 16, 24 … counted trades (never past N) — no verdict"""
    tr = sorted((r for r in rows if r['name'] == name and r['status'] == 'trade'), key=lambda r: r['A'])
    out = []
    for k in range(H7_CHECKPOINT, min(len(tr), N_RULE[('H7', name)]) + 1, H7_CHECKPOINT):
        S, N, t = h7_series(rows, name, upto=k)
        S2, _, _ = h7_series(rows, name, upto=k, col='net_2x')
        v = np.asarray([float(r['net_1x']) for r in t])
        out.append({'k': k, 'through': t[-1]['A'], 'mean_1x': float(S.sum() / N.sum()), 'mean_2x': float(S2.sum() / N.sum()),
                    'win': float((v > 0).mean()), 'total': float(v.sum()), 'worst': float(v.min()), 'best': float(v.max()),
                    'ci': interval(S, N) if k >= H7_CI_FROM else None})
    return out


def money(x):
    return '—' if x is None else f'{x:+,.2f}'


def ci_txt(c):
    return '—' if not c else f'[{money(c[0])}, {money(c[1])}]'


def write_report(paths: dict) -> str:
    h7 = EF.read_rows(paths['h7'])
    evs = {}
    for nm in NAMES:
        e = evaluate('H7', nm, h7)
        if e['verdict'] != 'no verdict':
            e = record_verdict(paths['verdicts'], e)
        evs[nm] = e

    def lab(e):
        return f'**{e["verdict"]}**' if e['verdict'] != 'no verdict' else 'no verdict'
    L = ['# Edge search H7: the forward test', '',
         f'Rule: `FORWARD_RULE_H7.md` (`{RULE_COMMITS["H7"]}`; its rule `PREREG_H7.md`, `edca472`). Written by `forward_h7_h9.py` '
         f'({VERSION}) from the append-only file in this folder. Dollars a trade after costs (1×; 2× beside). **No verdict before N**; '
         'at N the verdict uses exactly the first N and is written once (`verdicts.json`). SPY and QQQ are read separately. (H9 was '
         'withdrawn from the forward job by the owner on 2026-10-23, before any forward datum was read.)', '',
         '| test | name | counted / N | mean $ a trade 1× | 2× | 95 % block-20 interval | verdict |', '|---|---|---|---|---|---|---|']
    for nm, e in evs.items():
        L.append(f'| H7 | {nm} | {e["counted"]:,} / {e["N"]:,} | {money(e["mean_1x"])} | {money(e["mean_2x"])} | {ci_txt(e["ci"])} | {lab(e)} |')
    L += ['', '## H7 checkpoints (every 8 trades; descriptive)', '']
    for nm in NAMES:
        cps = checkpoints(h7, nm)
        if not cps:
            L.append(f'{nm}: no checkpoint yet (the first at 8 trades).')
        for c in cps:
            L.append(f'- {nm} after {c["k"]} trades (through {c["through"]}): mean {money(c["mean_1x"])} (2× {money(c["mean_2x"])}), '
                     f'{100 * c["win"]:.0f} % of trades > 0, total {money(c["total"])}, worst {money(c["worst"])}, best {money(c["best"])}'
                     + (f', interval {ci_txt(c["ci"])}' if c['ci'] else '') + ' — **checkpoint — no verdict**')
    exc = [r for r in h7 if r['status'] == 'excluded']
    L += ['', 'H7 meetings excluded (no trade): ' + ('; '.join(f'{r["name"]} {r["A"]} ({r["excluded"]})' for r in exc) or 'none') + '.', '']
    txt = '\n'.join(L)
    p = Path(paths['report'])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.part')
    tmp.write_text(txt)
    tmp.replace(p)
    return txt


# ---- one run ---------------------------------------------------------------------------------------------------------------------------

def run(days: list[str], layout: Path, official, folder: Path | None = None, divs_path: Path = DIVS, log=None, calendar=None) -> dict:
    """`days` = the job's complete forward sessions; `official(name, day)` → (close, source) or None. → {'h7_added', 'failures'}"""
    paths = default_paths(folder)
    res = {'h7_added': [], 'failures': []}
    days = sorted(d for d in set(days) if d >= SERIES_START)
    last = days[-1] if days else None
    if last is not None:
        try:
            divs = load_divs(divs_path)
        except EdgeDataError as e:
            res['failures'].append(f'{e.day} {e.step}: {e.why}')
            divs = None
        if divs is not None:
            res['h7_added'], res['failures'] = run_h7(Inputs(layout, official), last, divs, paths, log, calendar)
    write_report(paths)
    return res
