"""
forward_features.py — the forward test of the six Compass features models (FORWARD_RULE.md): V1, X3, VN1 (PREREG_FEATURES.md,
a2e14e4) and BV1b, BX3e, BC3 (PREREG_FEATURES_B.md, b6737c7), on the forward set — 0DTE base trades on SPY, QQQ and SPXW —
for every complete forward session from 2026-10-22.

Nothing here defines a trade, a feature, a threshold, a cost or an exit. The base trades are built by the study's own
build_0dte.build_day (prereg 2.3–2.6) and the models' arms by screen.py (f_V1, f_X3, f_VN1) and phase_b.py (variants:
BV1b, BX3e, BC3) — imported from ../run, their sha256 checked against FORWARD_RULE.md before anything runs. The only
adapting is where those files read: fcommon's data root is pointed at the daily job's Parquet layout (the same layout:
data_full/chains/<SYM>/<D>.parquet, data/underlying/<SYM>/<D>.parquet, data/index/SPX/<D>.parquet), its last day moved to
the forward session, the daily table (opening range, RV20, prior range) built by daily.build on the 60 trading days
ending at the session, and the official SPX close read from every Cboe SPX history file in data/official_closes/ (the
study's file and the job's later copies) — never a 15:59 print.

Per session and model one row in forward_sessions.csv: S_with, N_with, S_without, N_without (prereg 2.6 / stats.py), the
session's own per-trade difference (for reading). Idempotent: a session already in the file is never recomputed or
written again; a session with any input missing fails loudly (FeatureDataError) and writes nothing. The verdict
(FORWARD_RULE.md section 5): none before N counted sessions; at N, on the first N sessions, Δ > 0 with the 20-session
block-bootstrap 95% interval's lower end > 0 ⇒ CONFIRMED, else NOT CONFIRMED.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
RUN = FOLDER / 'run'
REPO = HERE.parents[2]
sys.path.insert(0, str(RUN))
import fcommon as C  # noqa: E402
import daily as D  # noqa: E402
import build_0dte as B0  # noqa: E402
import stats as ST  # noqa: E402
import screen as SC  # noqa: E402
import phase_b as PB  # noqa: E402
sys.path.insert(0, str(REPO / 'scripts'))
import fees_robinhood as FR  # noqa: E402  (the default cost model from 2026-10-24, docs/FEES_ROBINHOOD.md — beside, never in, the test)

AL = C.AL
VERSION = 'compass-features-forward-2026-10-22.1'
FORWARD_START = '2026-10-22'
FORWARD_NAMES = ('SPY', 'QQQ', 'SPXW')
MODELS = ('V1', 'X3', 'VN1', 'BV1b', 'BX3e', 'BC3')
# FORWARD_RULE.md section 4 (composition A; power_n.json)
N_RULE = {'V1': 23960, 'X3': 369, 'VN1': 587, 'BV1b': 481, 'BX3e': 265, 'BC3': 341}
BLOCK = 20
NO_CI_UNDER = 60
DAILY_WINDOW = 60
CSV_PATH = HERE / 'forward_sessions.csv'
REPORT_PATH = HERE / 'FORWARD_REPORT.md'
RH_CSV_PATH = HERE / 'forward_sessions_robinhood.csv'   # the same sessions and arms at Robinhood's fees: descriptive only
CSV_COLS = ('day', 'model', 'S_with', 'N_with', 'S_without', 'N_without', 'mean_with', 'mean_without', 'd_session', 'version', 'written_at')
CBOE_URL = 'https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv'

# FORWARD_RULE.md section 1: the code the forward test runs, by sha256 (as committed in 2a49049, unchanged through e5dd8c6)
FROZEN = {
    'run/fcommon.py': '05af0be735bd2f6c82551913ca1de2df3cdc9d01cc49fa8b2e31601973b9e882',
    'run/build_0dte.py': 'e152b1bec413f03a78ff9b6116ae45b5a92585d558f28f60b196f135d25fbc47',
    'run/daily.py': 'd2cb253936b9928f3efe9b3e87d71fdb67ad0d360feb99a84d207b11f2ec6505',
    'run/screen.py': 'e6cf7ef0e6e3e144c38aaf608ebb4afad8e9f50808a04550ef164b9dde0376b4',
    'run/stats.py': '4ad310430a2d27e88d2bbf4b491e433124bf1447d00fcbdaf179129558e97ea6',
    'run/phase_b.py': '313efc2e7630f6820d54e108435adec1402b176cb34b903307a1baae33470fef',
    'run/b_exits.py': '74556c8cb056179410d226bed6374c3dd0fa67e061675ca9b07915094badb665',
    'run/tiers.py': 'c6cad0c62353f42de3c029aaa1a45af26b5f125131b74dfa5c44aed1794818cd',
    '../Compass phase 3/backtest_audit/audit_lib.py': '3fcbb80b54a31ae3baa0ed94cdd269be5040f2761351bac129866b88b7935936',
}


class FeatureDataError(Exception):
    def __init__(self, day: str, step: str, why: str):
        super().__init__(f'{day} {step}: {why}')
        self.day, self.step, self.why = day, step, why


def check_frozen() -> None:
    bad = []
    for rel, want in FROZEN.items():
        p = (FOLDER / rel).resolve()
        got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'missing'
        if got != want:
            bad.append(f'{rel}: {got[:12]} (frozen {want[:12]})')
    if bad:
        raise RuntimeError('the frozen code changed — the forward test refuses to run: ' + '; '.join(bad))


# ---- the official SPX close (Cboe's history, as the study read it) ---------------------------------------------------------------------

def cboe_files(official_dir: Path) -> list[Path]:
    """every Cboe SPX history file kept, oldest copy first (a later copy's figure wins for a date both hold)"""
    return sorted(Path(official_dir).glob('cboe_SPX_History_*.csv'))


def parse_cboe(text: str) -> dict[str, float]:
    out = {}
    rd = csv.DictReader(io.StringIO(text))
    if rd.fieldnames is None or [f.strip() for f in rd.fieldnames[:2]] != ['DATE', 'SPX']:
        raise ValueError(f'not Cboe\'s SPX history: header {rd.fieldnames}')
    for r in rd:
        mm, dd, yy = r['DATE'].strip().split('/')
        v = float(r['SPX'])
        if not (v > 0):
            raise ValueError(f'a non-positive SPX close on {r["DATE"]}')
        out[f'{yy}-{mm}-{dd}'] = v
    return out


def official_spx_from(official_dir: Path) -> dict[str, float]:
    out = {}
    for f in cboe_files(official_dir):
        out.update(parse_cboe(f.read_text()))
    return out


def ensure_spx_close(day: str, official_dir: Path, fetch_text=None, today: str | None = None, log=None) -> tuple[float | None, int]:
    """the official SPX close of `day`: on disk → no call; else Cboe's history asked ONCE (fetch_text(url) → str) and kept
    as cboe_SPX_History_<today>.csv only if it parses and holds the day. → (close or None, calls)"""
    have = official_spx_from(official_dir).get(day)
    if have is not None or fetch_text is None:
        return have, 0
    text = fetch_text(CBOE_URL)
    got = parse_cboe(text)
    if day not in got:
        if log:
            log.info('Cboe\'s SPX history has no close for %s yet (its last row: %s)', day, max(got) if got else '—')
        return None, 1
    today = today or dt.date.today().isoformat()
    dest = Path(official_dir) / f'cboe_SPX_History_{today}.csv'
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix('.part')
    tmp.write_text(text)
    tmp.replace(dest)
    if log:
        log.info('official SPX close %s: %.2f (Cboe\'s history kept as %s)', day, got[day], dest.name)
    return got[day], 1


def default_fetch_text(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'compass-features-forward/1'})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 — a fixed https URL
        return r.read().decode('utf-8')


# ---- pointing the study's readers at a layout ------------------------------------------------------------------------------------------

def configure(layout: Path, work: Path, official_dir: Path, day: str) -> None:
    """fcommon's data root → the layout; its last day → `day`; the daily table rebuilt on the 60 trading days to `day`"""
    C.set_split('hold')                      # 'hold' opens every ticker; the forward set is outside both splits
    C.THETA = Path(layout)
    C.STAGING = Path(work) / '_no_staging'
    C.WORK = Path(work)
    C.LAST_DAY = day
    spx = official_spx_from(official_dir)
    C.official_spx = lambda: spx             # the same lookup build_0dte makes, on every Cboe file kept
    for f in (C.spy_eod_dates, C.trading_days, C.sessions, C.calendar_disagreements, C.session_index, C.tday_index, C.chain_days, C.bars):
        f.cache_clear()
    D._cache.clear()
    td = C.trading_days()
    if day not in td:
        raise FeatureDataError(day, 'calendar', 'not a trading day')
    i = td.index(day)
    window = td[max(0, i - DAILY_WINDOW + 1): i + 1]
    keep = C.trading_days
    try:
        C.trading_days = lambda: window       # daily.build walks C.trading_days(); restored before anything else reads it
        for u in FORWARD_NAMES:
            df = D.build(u)
            C.write_parquet(df, D.path(u))
    finally:
        C.trading_days = keep
    D._cache.clear()


def build_session(day: str, layout: Path, work: Path, official_dir: Path) -> pl.DataFrame:
    """the forward set's base trades of one full session, exactly as build_0dte forms them; any input missing → FeatureDataError"""
    if day in C.HALF_DAYS or day in AL.NYSE_HALF_DAYS:
        raise FeatureDataError(day, 'calendar', 'a half day: no base trade is entered (prereg 2.1)')
    for rel in [f'data_full/chains/{n}/{day}.parquet' for n in FORWARD_NAMES] + [f'data/underlying/{u}/{day}.parquet' for u in ('SPY', 'QQQ')] \
            + [f'data/index/SPX/{day}.parquet']:
        if not (Path(layout) / rel).exists():
            raise FeatureDataError(day, 'inputs', f'{rel} is not in the layout')
    configure(layout, work, official_dir, day)
    if C.official_spx().get(day) is None:
        raise FeatureDataError(day, 'official-spx-close', 'no official SPX close on disk (Cboe\'s history): SPXW cannot settle')
    rows = []
    for name in FORWARD_NAMES:
        rr, cnt, _notes = B0.build_day((name, day, 'hold'))
        if cnt.get('day: no chain') or cnt.get('day: no official SPX close (SPXW not formed)'):
            raise FeatureDataError(day, 'base-trades', f'{name}: {dict(cnt)}')
        if not rr:
            raise FeatureDataError(day, 'base-trades', f'{name}: no base trade formed on a full session ({dict(cnt)})')
        if name != 'SPXW' and C.bars(name, day) is None:
            raise FeatureDataError(day, 'inputs', f'{name}: no bars')
        rows += rr
    T = B0.frame(rows)
    T = T.with_columns(pl.col('m').cast(pl.Int64), pl.col('d6').cast(pl.Int64), pl.col('d7').cast(pl.Int64),
                       pl.when(pl.col('name') == 'SPXW').then(pl.lit('cash')).otherwise(pl.lit('physical')).alias('settle'),
                       pl.lit('-').alias('tier'))       # tiers are descriptive only and not computed forward
    return T.with_row_index('tid')


def model_arms(T: pl.DataFrame) -> dict:
    V = {vid: fn for vid, _f, _d, fn in PB.variants(T)}
    return {'V1': SC.f_V1(T), 'X3': SC.f_X3(T), 'VN1': SC.f_VN1(T), 'BV1b': V['BV1b'](), 'BX3e': V['BX3e'](), 'BC3': V['BC3']()}


def session_rows(day: str, T: pl.DataFrame) -> list[dict]:
    at = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    out = []
    for mid, (w, wo) in model_arms(T).items():
        Sw, Nw = ST.per_session(w, [day])
        So, No = ST.per_session(wo, [day])
        mw = float(Sw[0] / Nw[0]) if Nw[0] else None
        mo = float(So[0] / No[0]) if No[0] else None
        out.append(dict(day=day, model=mid, S_with=float(Sw[0]), N_with=int(Nw[0]), S_without=float(So[0]), N_without=int(No[0]),
                        mean_with=mw, mean_without=mo, d_session=(mw - mo) if (mw is not None and mo is not None) else None,
                        version=VERSION, written_at=at))
    return out


def rh_repriced(T: pl.DataFrame) -> pl.DataFrame:
    """the same base trades with r and r_x3 at Robinhood's fees: the study's fee (fcommon.fee on the buy at the ask and the
    sale at exit_px; SPXW settled 0DTE pays no exit fee; a $0 price pays none) added back, Robinhood's charged. The rows,
    and so every model's arms, are unchanged — only the returns move. The 14:00 bid is read back from r_x3."""
    def old(name, px):
        return pl.when(px > 0).then(pl.when(name == 'SPXW').then(pl.when(px < 1.0 - 1e-9).then(C.FEE_SPXW_LO).otherwise(C.FEE_SPXW_HI))
                                    .otherwise(C.FEE_ETF)).otherwise(0.0)
    nm, ask = pl.col('name'), pl.col('ask')
    settled = (nm == 'SPXW') & (pl.col('eb') == '0DTE')
    f_in = old(nm, ask)
    buy = FR.option_fee_expr(nm, ask, 1.0, 'buy')
    fee_old = f_in + pl.when(settled).then(0.0).otherwise(old(nm, pl.col('exit_px')))
    fee_rh = buy + pl.when(settled | (pl.col('exit_px') <= 0)).then(0.0).otherwise(FR.option_fee_expr(nm, pl.col('exit_px'), 1.0, 'sell'))
    base = pl.col('r_x3') * ask + ask + f_in / 100
    lo, hi, etf = base + C.FEE_SPXW_LO / 100, base + C.FEE_SPXW_HI / 100, base + C.FEE_ETF / 100
    px3 = pl.when(base.abs() < 1e-7).then(0.0).otherwise(pl.when(nm == 'SPXW').then(pl.when(lo < 1.0 - 1e-9).then(lo).otherwise(hi)).otherwise(etf))
    old3 = f_in + old(nm, px3)
    rh3 = buy + pl.when(px3 > 0).then(FR.option_fee_expr(nm, px3, 1.0, 'sell')).otherwise(0.0)
    return T.with_columns(((pl.col('r') * ask * 100 + fee_old - fee_rh) / (ask * 100)).alias('r'),
                          pl.when(pl.col('r_x3').is_null()).then(None).otherwise((pl.col('r_x3') * ask * 100 + old3 - rh3) / (ask * 100)).alias('r_x3'))


def rh_session_rows(day: str, T: pl.DataFrame) -> list[dict]:
    rows = session_rows(day, rh_repriced(T))
    for x in rows:
        x['version'] = f'{VERSION} + {FR.VERSION}'
    return rows


# ---- the cumulative file ----------------------------------------------------------------------------------------------------------------

def read_csv(path: Path = CSV_PATH) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ('S_with', 'S_without'):
            r[k] = float(r[k])
        for k in ('N_with', 'N_without'):
            r[k] = int(r[k])
    return rows


def days_in(path: Path = CSV_PATH) -> set[str]:
    rows = read_csv(path)
    by = {}
    for r in rows:
        by.setdefault(r['day'], set()).add(r['model'])
    bad = {d: sorted(m) for d, m in by.items() if m != set(MODELS)}
    if bad:
        raise RuntimeError(f'{path}: a session without all six models: {bad}')
    dup = len(rows) - len({(r['day'], r['model']) for r in rows})
    if dup:
        raise RuntimeError(f'{path}: {dup} duplicated (day, model) rows')
    return set(by)


def append_rows(rows: list[dict], path: Path = CSV_PATH) -> list[str]:
    """append whole sessions not already in the file; → the days added (none twice, ever)"""
    have = days_in(path)
    new = [r for r in rows if r['day'] not in have]
    days = sorted({r['day'] for r in new})
    for d in days:
        if {r['model'] for r in new if r['day'] == d} != set(MODELS):
            raise RuntimeError(f'{d}: refusing to append a session without all six models')
    if not new:
        return []
    exists = Path(path).exists()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        if not exists:
            w.writeheader()
        for r in sorted(new, key=lambda x: (x['day'], MODELS.index(x['model']))):
            w.writerow({k: ('' if r.get(k) is None else (repr(r[k]) if isinstance(r[k], float) else r[k])) for k in CSV_COLS})
    return days


# ---- the verdict (FORWARD_RULE.md section 5) -------------------------------------------------------------------------------------------

def evaluate(rows: list[dict], model: str, n_rule: int | None = None) -> dict:
    n_rule = N_RULE[model] if n_rule is None else n_rule
    rs = sorted((r for r in rows if r['model'] == model), key=lambda r: r['day'])
    n = len(rs)
    use = rs[:n_rule] if n >= n_rule else rs
    out = dict(model=model, N=n_rule, counted=n, verdict='no verdict', delta=None, ci=None, mean_with=None, mean_without=None)
    if not use:
        return out
    Sw = np.array([r['S_with'] for r in use], float)
    Nw = np.array([r['N_with'] for r in use], float)
    So = np.array([r['S_without'] for r in use], float)
    No = np.array([r['N_without'] for r in use], float)
    if Nw.sum() > 0 and No.sum() > 0:
        mw, mo = Sw.sum() / Nw.sum(), So.sum() / No.sum()
        out.update(mean_with=float(mw), mean_without=float(mo), delta=float(mw - mo))
        if len(use) >= NO_CI_UNDER:
            out['ci'] = AL.pct_ci(ST._boot(Sw, Nw, So, No, BLOCK))
    if n >= n_rule:
        ok = out['delta'] is not None and out['delta'] > 0 and out['ci'] is not None and math.isfinite(out['ci'][0]) and out['ci'][0] > 0
        out['verdict'] = 'CONFIRMED' if ok else 'NOT CONFIRMED'
        out['through'] = use[-1]['day']
    return out


def pp(x):
    return '—' if x is None else f'{100 * x:+.2f}'


def write_report(path: Path = REPORT_PATH, csv_path: Path = CSV_PATH) -> str:
    rows = read_csv(csv_path)
    days = sorted({r['day'] for r in rows})
    L = ['# Compass features: the forward test', '',
         f'The rule: `FORWARD_RULE.md` (committed alone before any forward datum existed). Written by `forward_features.py` '
         f'({VERSION}) from `forward_sessions.csv`. Forward set: 0DTE base trades on SPY, QQQ and SPXW, full sessions from '
         f'{FORWARD_START}. Points of the debit per trade after fees; Δ = per-trade mean with − without, pooled over sessions; '
         f'interval: 20-session moving-block bootstrap (audit_lib, 2,000 draws, seed {AL.SEED}), none under {NO_CI_UNDER} sessions.', '',
         f'Sessions counted: **{len(days)}** ({days[0] + " → " + days[-1] if days else "none yet"}).', '',
         '| model | counted / N | mean with | mean without | Δ | 95% | verdict |', '|---|---|---|---|---|---|---|']
    for m in MODELS:
        e = evaluate(rows, m)
        ci = '—' if not e['ci'] else f'[{pp(e["ci"][0])}, {pp(e["ci"][1])}]'
        lab = e['verdict'] if e['verdict'] != 'no verdict' else 'no verdict (interim figures only)'
        L.append(f'| {m} | {e["counted"]:,} / {e["N"]:,} | {pp(e["mean_with"])} | {pp(e["mean_without"])} | {pp(e["delta"])} | {ci} | **{lab}** |')
    L += ['', 'No verdict is read before a model reaches its N; interim figures are logged for the record only, with no early '
          'stop. At N the verdict uses exactly the first N counted sessions and is never revised. V1\'s N (23,960 sessions) is '
          'out of reach on this forward set (FORWARD_RULE.md section 4). The six models are read separately, without a '
          'multiple-test correction.', '']
    rh = read_csv(RH_CSV_PATH if Path(csv_path) == CSV_PATH else Path(csv_path).with_name(RH_CSV_PATH.name))
    rdays = sorted({x['day'] for x in rh})
    L += ['## At Robinhood fees (descriptive)', '',
          f'The same sessions, trades and arms, each trade re-priced at Robinhood\'s fees (the research\'s default cost model '
          f'from 2026-10-24, `docs/FEES_ROBINHOOD.md`, `{FR.VERSION}`). The study\'s modelled fee ($0.68748 a contract a side; '
          'SPXW $1.18748 / $1.27748) is added back and Robinhood\'s charged: $0.0403 a contract to buy, and $0.0603 to sell a '
          'one-lot ETF option; SPXW $1.0403 / $1.1303 a side. **The pass rule and each model\'s N stay on the pre-registered '
          'fees (FORWARD_RULE.md, frozen)**, and the verdict column above is the only verdict. This table is descriptive.', '',
          f'Sessions re-priced: **{len(rdays)}** ({rdays[0] + " → " + rdays[-1] if rdays else "none yet"}).', '',
          '| model | sessions | mean with, Robinhood (pre-registered) | mean without, Robinhood (pre-registered) | Δ, Robinhood (pre-registered) |',
          '|---|---|---|---|---|']
    for m in MODELS:
        a, b = evaluate(rows, m), evaluate(rh, m)
        L.append(f'| {m} | {b["counted"]:,} | {pp(b["mean_with"])} ({pp(a["mean_with"])}) | {pp(b["mean_without"])} ({pp(a["mean_without"])}) | '
                 f'{pp(b["delta"])} ({pp(a["delta"])}) |')
    L.append('')
    txt = '\n'.join(L)
    tmp = Path(path).with_suffix('.part')
    tmp.write_text(txt)
    tmp.replace(path)
    return txt


# ---- one run ---------------------------------------------------------------------------------------------------------------------------

def run(days: list[str], layout: Path, work: Path, official_dir: Path, csv_path: Path = CSV_PATH, report_path: Path = REPORT_PATH,
        fetch_text=None, log=None, today: str | None = None) -> dict:
    """every given forward session not yet in the file, oldest first; stops at the first one that fails (nothing written for
    it or after it). → {'added', 'failure', 'calls'}"""
    check_frozen()
    have = days_in(csv_path)
    todo = sorted(d for d in set(days) if d >= FORWARD_START and d not in have)
    res = dict(added=[], failure=None, calls=0, pending=todo)
    for d in todo:
        try:
            _, calls = ensure_spx_close(d, official_dir, fetch_text, today=today, log=log)
            res['calls'] += calls
            T = build_session(d, layout, work, official_dir)
            res['added'] += append_rows(session_rows(d, T), csv_path)
            append_rows(rh_session_rows(d, T), Path(csv_path).with_name(RH_CSV_PATH.name))
            if log:
                log.info('compass features %s: %d base trades, six models appended', d, T.height)
        except FeatureDataError as e:
            res['failure'] = f'{e.day} {e.step}: {e.why}'
            break
    res['rh_backfilled'] = backfill_rh(layout, work, official_dir, csv_path, log)
    write_report(report_path, csv_path)
    return res


def backfill_rh(layout: Path, work: Path, official_dir: Path, csv_path: Path = CSV_PATH, log=None) -> list[str]:
    """the Robinhood re-pricing for sessions already counted before it existed: their base trades rebuilt from the layout on
    disk (nothing fetched; the counted file is never touched); a session that cannot be rebuilt is said and skipped"""
    rh_path = Path(csv_path).with_name(RH_CSV_PATH.name)
    done = []
    for d in sorted(days_in(csv_path) - days_in(rh_path)):
        try:
            T = build_session(d, layout, work, official_dir)
            done += append_rows(rh_session_rows(d, T), rh_path)
        except FeatureDataError as e:
            if log:
                log.warning('compass features Robinhood re-pricing %s skipped: %s', d, e)
    return done
