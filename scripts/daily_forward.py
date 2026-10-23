#!/usr/bin/env python3
"""
daily_forward.py — the daily post-close job (2026-10-22, the owner: "a daily post-close job: fetch → verify → merge →
replay → append to the cumulative report. One ThetaData login per run, scheduled so it doesn't collide with my terminal
session"). For every forward session not yet in the cumulative report (2026-10-12 on, oldest first, at most --max-days a
run), in this order, stopping at the first failure:

  1. fetch     the session's seven files (SPY/QQQ/SPXW same-day chains, SPY/QQQ minute bars, SPX/VIX prints) into a
               staging folder of its own (<parquet-root>/_daily_staging/<D>/) — skipped when the day is already in the
               layout. TWO SOURCES, one a run:
                 --source terminal (DEFAULT): the Theta Terminal already running on the owner's PC, through the existing
                   --fetch-theta REST path (paper_backtest.fetch_theta: 127.0.0.1:25503, at most 3 in flight). NO LOGIN
                   AT ALL — the terminal holds the key — so nothing collides with the owner's session.
                 --source sdk: the container path (the `thetadata` SDK calls of research_notes/…/sdk_fetch.py) — ONE login
                   a run. It signs the owner's terminal out, so it runs only inside THETA_SDK_WINDOW=HH:MM-HH:MM (New York,
                   set by the owner; refused when unset or outside it) and never between 00:00 and 01:45 New York (Theta's
                   own gap: the previous day is not served).
  2. verify    --verify-parquet on the staged day (every minute, contract, NBBO and the stored norms) — a failure stops
               the run before anything is merged.
  3. merge     --merge-parquet into the layout (nothing copied while a file fails or a target exists); then --verify-
               parquet on the layout with the sessions before the replay reads.
  4. the official close: UW's daily bar (`/api/stock/{T}/ohlc/1d`, ONE call a name — SPY, QQQ — UW_API_TOKEN from the
               environment, never logged) kept as fetched in data/official_closes/, unless the day's official close is
               already on disk (UW's daily bar or Theta's EOD). None published yet: the day fails (it is never settled on
               the 15:59 bar and appended).
  4b. the decision price (the after-hours study's: the last UW post-market 1-minute bar ending at or before 17:30
               New York): read off data/postmarket_1m; a name without one is asked ONCE (/ohlc/1m?date=D) after 17:30 and
               kept there as answered. Without it only cases b and c of the after-hours columns stay null.
  5. replay    the session through the live tracker (paper_backtest.replay, --settle-on official) into the replay root;
               the session must come out whole: replayed, no file missing, every tradable capture settled on the official
               close.
  6. append    the whole sessions to the cumulative report (paper_backtest.append_cumulative): the historical sections
               untouched, the forward block regenerated — so yesterday's after-hours columns (they need the next 09:30
               open) fill on today's run.
  7. compass features (on by default from the command line; --no-features skips it): the forward test of the six
               Compass features models (research_notes/Compass features/FORWARD_RULE.md: V1, X3, VN1, BV1b, BX3e, BC3) on
               every whole forward session from 2026-10-22 not yet in forward/forward_sessions.csv — the 0DTE base trades on
               SPY, QQQ and SPXW built by the study's own frozen code (forward/forward_features.py, sha256 checked) from the
               same layout, SPXW settled on the official SPX close (Cboe's SPX history, data/official_closes/
               cboe_SPX_History_*.csv; asked ONCE a run when the day is not on disk, --no-cboe asks nothing). A session
               missing anything fails loudly (`DAILY-FORWARD FAIL <day> features-<step>`, exit 1, nothing written for it);
               the paper tracker's append above is not held back by it. forward/FORWARD_REPORT.md is rewritten each run:
               sessions counted against each model's N, "no verdict" until N.
  8. edge H5 / H6 / H7 (on by default from the command line; --no-edge skips it): the forward-only tests of the edge-search
               queue's H5 and H6 (research_notes/Edge search/H5_H6/PREREG_H5.md, PREREG_H6.md, e114e30; the code
               edge_forward.py there) on every complete forward session. H5 (from 2026-10-23): 10 SPY same-day ATM straddles
               sold at the 15:30 bids against 1 SPXW straddle bought at the asks, all four legs closed at 15:58 — read from
               the layout this job already holds, nothing fetched. H6 (each month's first full session from November 2026):
               SPY and QQQ 0.30/0.15-delta put spreads 30–45 days out, closed on the first full session 21 days before
               expiry — on END-OF-DAY option quotes, which steps 1–7 do not fetch: step 8 asks the run's own --source for
               them (the terminal's /option/history/eod, or the SDK's option_history_eod; every expiration on an entry
               session, the one expiration on an exit session — at most four calls a month), kept as answered under
               <parquet-root>/edge_forward/eod/ and never asked twice. A session missing anything fails loudly
               (`DAILY-FORWARD FAIL <day> edge-<step>`, exit 1, nothing written for it); the steps before are not held
               back by it. forward/EDGE_FORWARD_REPORT.md is rewritten each run: counted against N, "no verdict" until N.
               Step 8 also runs H7 (research_notes/Edge search/H7_H8_H9/forward_h7_h9.py): the pre-FOMC drift
               (FORWARD_RULE_H7.md, fcc1f4d: 100 SPY / QQQ from the official close before each scheduled 2:00 pm FOMC
               statement from 2026-10-28 to the 13:58 bar's close; N 366 / 483 trades) — on the official closes and
               1-minute bars this job keeps (nothing fetched for it), the FOMC calendar in data/macro_events_2022_2027.json
               and H7's hand-kept dividend table H7_H8_H9/data/dividends_h7.json (the ex-dates that fall on statement
               dates; a statement past its complete_through fails loudly). Its report: H7_H8_H9/forward/
               H7_FORWARD_REPORT.md, "no verdict" until N. (H9, the overnight drift, was withdrawn from this job by the
               owner on 2026-10-23, with its half-day collection and its dividend table; no H9 forward row was written.)

A NEW MACHINE: the sessions the cumulative report already lists but this replay root does not hold (the owner's PC
with the committed report) go through the same steps first — fetched if the layout lacks them, replayed — so the
forward block can be regenerated; they are not appended twice.

IDEMPOTENT: a day already in the layout is not fetched; a day whose official close is on disk asks UW nothing; a replayed
minute is skipped by its marker; a session already in the cumulative report is not pending. A run with nothing pending
says so and exits 0. ON ANY FAILURE: one line `DAILY-FORWARD FAIL <day> <step>: <why>`, nothing appended for that day
(or after it), exit 1. A refusal (the SDK window, Theta's gap, a missing setting): `DAILY-FORWARD REFUSED …`, exit 2.

THE SCHEDULE: 17:45 New York on trading days (after the official close is published and after the 17:30 decision
price), holidays and half days skipped by the recorder's calendar (eod_recorder HOLIDAYS / HALF_DAYS): scripts/
daily_forward.cmd (Windows Task Scheduler) or scripts/daily_forward.service + .timer (systemd). README: scripts/
eod_recorder.README.md "The daily forward job".

    python3 -I scripts/daily_forward.py [--source terminal|sdk] [--parquet-root R] [--backtest-data DIR] [--cumulative FILE]
                                        [--historical-from REPORT] [--day D] [--max-days N] [--no-uw] [--status]
                                        [--no-features] [--no-cboe] [--no-edge]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import polars as pl  # noqa: E402

import eod_recorder as R  # noqa: E402
import paper_audit as P  # noqa: E402
import paper_backtest as B  # noqa: E402
import paper_tracker as T  # noqa: E402

JOB_VERSION = 'daily-forward-2026-10-23.5'
READY_AFTER = '17:30'               # a session is pending once its official close is out and the 17:30 decision price has passed
SCHEDULE_NY = '17:45'
THETA_GAP_END_MIN = 105             # 00:00–01:45 New York: Theta serves no previous day; the SDK never logs in then
SDK_WINDOW_ENV = 'THETA_SDK_WINDOW'
SDK_KEY_ENVS = ('THETADATA_KEY', 'THETADATA_API_KEY')
DEFAULT_MAX_DAYS = 10
CLOSE_NAMES = ('SPY', 'QQQ')
OFFICIAL_DIR = R.REPO / 'data' / 'official_closes'
STAGING_DIR = '_daily_staging'
SDK_ORDER = (('under', 'SPY'), ('under', 'QQQ'), ('index', 'SPX'), ('index', 'VIX'), ('chain', 'SPY'), ('chain', 'QQQ'), ('chain', 'SPXW'))
CHAIN_COLS = ['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size', 'mid']


class JobError(Exception):
    def __init__(self, step: str, day: str | None, why: str):
        super().__init__(f'{day or "-"} {step}: {why}')
        self.step, self.day, self.why = step, day, why


class Refused(Exception):
    pass


def red(s) -> str:
    """the Theta key's value and shape out of any text kept (never sent to a log in the first place; defensive)"""
    s = str(s)
    for k in SDK_KEY_ENVS:
        v = os.environ.get(k) or ''
        if len(v) >= 4:
            s = s.replace(v, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9]+', '[key]', s)


# ---- the clock rules -----------------------------------------------------------------------------------------------------------------

def parse_window(text: str | None) -> tuple[int, int]:
    """'HH:MM-HH:MM' (New York) → (start, end) minutes of the day; a window may run past midnight ('22:00-00:30')"""
    m = re.fullmatch(r'\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*', text or '')
    if not m:
        raise Refused(f'{SDK_WINDOW_ENV} is not set to HH:MM-HH:MM New York (got {text!r}) — the SDK signs the owner\'s terminal out, '
                      'so it runs only inside a window the owner sets')
    a, b = int(m[1]) * 60 + int(m[2]), int(m[3]) * 60 + int(m[4])
    if not (0 <= a < 1440 and 0 <= b <= 1440) or a == b:
        raise Refused(f'{SDK_WINDOW_ENV}={text!r} is not a window')
    return a, b


def in_window(ny: dt.datetime, win: tuple[int, int]) -> bool:
    m = ny.hour * 60 + ny.minute
    a, b = win
    return a <= m < b if a < b else (m >= a or m < b)


def in_theta_gap(ny: dt.datetime) -> bool:
    return ny.hour * 60 + ny.minute < THETA_GAP_END_MIN


# ---- what is pending ---------------------------------------------------------------------------------------------------------------

def listed_sessions(cumulative: Path) -> list[str]:
    if not Path(cumulative).exists():
        return []
    return B._cum_parse(Path(cumulative).read_text(encoding='utf-8'))[2]


def pending_sessions(listed: list, now: dt.datetime, max_days: int = DEFAULT_MAX_DAYS, start: str = P.FORWARD_START,
                     only: str | None = None) -> list[str]:
    """forward sessions (the recorder's calendar: holidays and half days skipped) whose 17:30 has passed and that the
    cumulative report does not hold yet — oldest first, at most `max_days`"""
    if only:
        return [only] if only not in listed and T.is_tracked_day(only) and now >= R.ny_at(only, READY_AFTER) else []
    out, d = [], dt.date.fromisoformat(start)
    today = dt.date.fromisoformat(R.ny_day_of(now))
    while d <= today and len(out) < max_days:
        day = d.isoformat()
        if T.is_tracked_day(day) and now >= R.ny_at(day, READY_AFTER) and day not in listed:
            out.append(day)
        d += dt.timedelta(days=1)
    return out


def day_in_layout(root: Path, day: str) -> bool:
    """every file of the day in the layout, none refused by the day's manifest"""
    rf = B.refusals(root, day)
    return all((Path(root) / B.rel_of(j['kind'], j['sym'], day)).exists() and B.rel_of(j['kind'], j['sym'], day) not in rf
               for j in B.fetch_jobs(day))


# ---- the SDK path (the container's: research_notes/Compass phase 3/forward_2026-10-12_2026-10-21/sdk_fetch.py's calls) ----

class SdkSource:
    """The thetadata SDK, ONE login a run (the client is made on the first file asked and kept); the key from the
    environment only, never printed or logged. `factory()` → a client with option_history_quote / stock_history_ohlc /
    index_history_price (the tests hand in a fake)."""

    def __init__(self, factory=None, log: logging.Logger | None = None, retries: int = 3, sleep=time.sleep):
        self.factory = factory or default_sdk_factory
        self.log = log or logging.getLogger('daily_forward')
        self.retries, self.sleep = retries, sleep
        self._client = None
        self.logins = 0

    def client(self):
        if self._client is None:
            self._client = self.factory()
            self.logins += 1
            self.log.info('thetadata SDK: signed in (one login for this run)')
        return self._client

    def raw(self, kind: str, sym: str, day: str):
        c, D = self.client(), dt.date.fromisoformat(day)
        if kind == 'chain':
            return c.option_history_quote(symbol=sym, expiration=D, interval='1m', date=D, strike='*', right='both')
        if kind == 'under':
            return c.stock_history_ohlc(symbol=sym, interval='1m', date=D)
        return c.index_history_price(symbol=sym, interval='1m', date=D)

    def eod(self, sym: str, day: str, expiration: str | None) -> list[dict]:
        """step 8's end-of-day option quotes of `sym` on `day` — every expiration (None) or one — through the same login
        (fetch_h3's call: option_history_eod, start_date = end_date = day). → the rows; EdgeFetchError when none come"""
        EF = edge_module()
        D = dt.date.fromisoformat(day)
        exp = '*' if expiration is None else dt.date.fromisoformat(expiration)
        err = None
        for attempt in range(self.retries):
            try:
                df = self.client().option_history_eod(start_date=D, end_date=D, symbol=sym, expiration=exp)
                if df is None or getattr(df, 'height', 0) == 0:
                    raise EF.EdgeFetchError('the SDK answered no rows')
                return df.to_dicts()
            except EF.EdgeFetchError:
                raise
            except Exception as e:  # noqa: BLE001 — never with the key in it
                name = type(e).__name__
                err = red(f'{name}: {e}')[:200]
                if name == 'NoDataFoundError' or 'UNAUTHENTICATED' in str(e).upper():
                    break
                if attempt + 1 < self.retries:
                    self.sleep(2.0 * (attempt + 1))
        raise EF.EdgeFetchError(err or 'no answer')

    def fetch(self, day: str, staging: Path, norm_roots: tuple = ()) -> dict:
        """the seven files of `day` into `staging` (its layout and manifest), each shaped as the stored dataset was
        (sdk_fetch.shape), validated before it is placed. → {'rc', 'written', 'failed'}"""
        run = dt.datetime.now(R.UTC).strftime('%Y%m%dT%H%M%SZ')
        out = {'rc': 0, 'written': [], 'failed': [], 'logins': 0}
        sess = B.session_of(day)
        for kind, sym in SDK_ORDER:
            rel = B.rel_of(kind, sym, day)
            if (Path(staging) / rel).exists():
                continue
            entry = {'run': run, 'via': 'thetadata SDK (gRPC), daily_forward', 'request': {'kind': kind, 'symbol': sym, 'date': day}}
            df, err = None, None
            for attempt in range(self.retries):
                try:
                    df = self.raw(kind, sym, day)
                    break
                except Exception as e:  # noqa: BLE001 — a fake's or the SDK's error alike; never with the key in it
                    name = type(e).__name__
                    err = red(f'{name}: {e}')[:200]
                    if name == 'NoDataFoundError' or 'UNAUTHENTICATED' in str(e).upper():
                        break
                    if attempt + 1 < self.retries:
                        self.sleep(2.0 * (attempt + 1))
            if df is None or getattr(df, 'height', 0) == 0:
                why = err or 'an answer with no rows for a calendar session — not an empty session'
                entry.update(status='FAILED', error=why)
                B.write_manifest(staging, day, {rel: entry}, session=sess['kind'])
                out['failed'].append({'file': rel, 'error': why})
                continue
            shaped, probs = sdk_shape(kind, sym, day, df, norm_roots)
            f = Path(staging) / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            st, ck, vp = B.validate_frame(kind, sym, day, shaped, B.norms_for(tuple(norm_roots) + (Path(staging),), kind, sym, day), sess) if not probs else ('FAILED', {}, probs)
            entry.update(status=st, checks=ck, problems=vp, rows=shaped.height)
            if st == 'ok':
                tmp = f.with_name(f.name + '.tmp')
                shaped.write_parquet(tmp, compression='zstd')
                os.replace(tmp, f)
                entry['sha256'] = B.sha256_of(f)
                out['written'].append(rel)
            else:
                out['failed'].append({'file': rel, 'error': '; '.join(vp)})
            B.write_manifest(staging, day, {rel: entry}, session=sess['kind'])
        out['rc'] = 1 if out['failed'] else 0
        out['logins'] = self.logins
        return out


def default_sdk_factory():
    key = next((os.environ[k] for k in SDK_KEY_ENVS if os.environ.get(k)), None)
    if not key:
        raise JobError('fetch', None, f'the SDK needs the key in the environment ({" or ".join(SDK_KEY_ENVS)}) — never in a file in the repo')
    logging.getLogger('thetadata').setLevel(logging.ERROR)
    from thetadata import ThetaClient          # imported only on the container path
    return ThetaClient(api_key=key, dataframe_type='polars')


def sdk_shape(kind: str, sym: str, day: str, df, norm_roots: tuple = ()) -> tuple[pl.DataFrame, list]:
    """sdk_fetch.shape: the chain's mid and its eight columns (sizes Int32), the bars and prices as the SDK answers, the
    day's rows only, timestamps Datetime(ms, America/New_York), NaN → null; the schema checked against a stored file of
    the same kind when one is on disk. Problems said, nothing filled in."""
    probs = []

    def norm_ts(x):
        x = x.with_columns(pl.col('timestamp').dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
        fl = [c for c, t in zip(x.columns, x.dtypes) if t in (pl.Float64, pl.Float32)]
        return x.with_columns([pl.col(c).fill_nan(None) for c in fl]) if fl else x
    if kind == 'chain':
        if df.height and 'expiration' in df.columns and set(df['expiration'].cast(pl.Utf8).str.replace_all('-', '').str.slice(0, 8).unique().to_list()) != {day.replace('-', '')}:
            probs.append('expirations other than the day')
        if df.height and 'symbol' in df.columns and set(df['symbol'].unique().to_list()) != {sym}:
            probs.append(f'roots other than {sym}')
        out = df.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
        out = out.select(CHAIN_COLS).with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32))
        out = norm_ts(out).sort(['strike', 'right', 'timestamp'])
    else:
        out = norm_ts(df.select(df.columns)).sort('timestamp')
        other = out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') != day).height
        if other:
            probs.append(f'{other} rows of another day')
        out = out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') == day)
    for r in norm_roots:
        d = Path(r) / Path(B.rel_of(kind, sym, day)).parent
        ref = sorted(f for f in d.glob('*.parquet') if len(f.name) == 18 and f.name[:10] < day) if d.is_dir() else []
        if ref:
            sch = pl.read_parquet_schema(ref[-1])
            if dict(out.schema) != dict(sch):
                probs.append(f'schema differs from the stored {ref[-1].name}: {dict(out.schema)} vs {dict(sch)}')
            break
    return out, probs


# ---- the official close: UW's daily bar, one call a name -------------------------------------------------------------------------

def ensure_official(day: str, closes: P.OfficialCloses, official_dir: Path, uw_client, log: logging.Logger,
                    names=CLOSE_NAMES) -> tuple[P.OfficialCloses, list, int]:
    """The day's official close for every name: on disk already (UW's daily bar, Theta's EOD) → no call; else one UW
    call a name (/ohlc/1d?date=D — its answer carries the days before too, so yesterday's post-market bar is complete in
    it), kept as fetched under `official_dir`. → (closes reloaded, names still missing, calls)"""
    def reload(c):
        return P.OfficialCloses(names=c.names, uw_dirs=tuple(c.uw_dirs) + ((Path(official_dir),) if Path(official_dir) not in c.uw_dirs else ()),
                                uw_lake_glob=c.uw_lake_glob, theta_glob=c.theta_glob, live_root=c.live_root)
    need = [nm for nm in names if closes.get(nm, day)[0] is None]
    if need:                                    # the disk again first: an earlier run may have kept the day since
        closes = reload(closes)
        need = [nm for nm in names if closes.get(nm, day)[0] is None]
    calls = 0
    if need and uw_client is not None:
        rows = []
        at = R.iso_z(dt.datetime.now(R.UTC))
        for nm in need:
            ans = uw_client.get(f'/api/stock/{nm}/ohlc/1d', {'date': day, 'limit': 6})
            calls += 1
            if not ans.ok:
                log.error('official close %s %s: %s', nm, day, ans.error)
                continue
            for r in ans.rows:
                rows.append({'ticker': nm, **{k: R.stringify(r.get(k)) for k in ('close', 'date', 'high', 'low', 'market_time', 'open', 'total_volume', 'volume')},
                             '_fetched_at': at, '_asked_date': day})
        if rows:
            official_dir = Path(official_dir)
            official_dir.mkdir(parents=True, exist_ok=True)
            f = official_dir / f'uw_ohlc_1d_{day}_fetched{at.replace(":", "").replace("-", "")}.parquet'
            pl.DataFrame(rows, schema={c: pl.Utf8 for c in rows[0]}).write_parquet(f)
            log.info('official close %s: %d rows of UW\'s daily bar kept in %s', day, len(rows), f.name)
        closes = reload(closes)
    missing = [nm for nm in names if closes.get(nm, day)[0] is None]
    return closes, missing, calls


def ensure_decision(day: str, uw_client, postmarket_dir: Path, log: logging.Logger, now: dt.datetime,
                    names=CLOSE_NAMES) -> tuple[list, int]:
    """The after-hours study's decision price (the last UW post-market 1-minute bar ending at or before 17:30): read
    off the UW 1-minute answers on disk; a name without one (and no answer kept for it) is asked ONCE (/ohlc/1m?date=D&limit=2000, as the study's
    fetch_postmarket_1m.py asks) once 17:30 New York has passed, the answer kept as answered under
    data/postmarket_1m/<T>/<D>.json.gz. A name still without one is only said: cases b and c stay null for it, the
    session is appended all the same (the hold, the 15:58 exit and case a do not need it). → (names without, calls)"""
    import gzip
    have = P.decision_prices_on_disk(names, postmarket_dir, B.uw_1m_dirs())
    calls = 0
    for nm in [n for n in names if (n, day) not in have]:
        if uw_client is None or now < R.ny_at(day, '17:31') or (Path(postmarket_dir) / nm / f'{day}.json.gz').exists():
            continue                            # an answer kept is never asked again (taken after 17:30, it is the evening's)
        ans = uw_client.get(f'/api/stock/{nm}/ohlc/1m', {'date': day, 'limit': 2000})
        calls += 1
        if not ans.ok or not isinstance(ans.body, dict):
            log.warning('decision price %s %s: %s', nm, day, ans.error)
            continue
        f = Path(postmarket_dir) / nm / f'{day}.json.gz'
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + '.tmp')
        with gzip.GzipFile(tmp, 'wb', mtime=0) as g:
            g.write(json.dumps(ans.body, separators=(',', ':')).encode('utf-8'))
        os.replace(tmp, f)
    have = P.decision_prices_on_disk(names, postmarket_dir, B.uw_1m_dirs())
    missing = [n for n in names if (n, day) not in have]
    if missing:
        log.warning('decision price %s: none for %s — cases b and c stay null there', day, ', '.join(missing))
    return missing, calls


# ---- the job ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Job:
    parquet_root: Path
    replay_root: Path = B.DEFAULT_OFFICIAL_ROOT
    cumulative: Path = B.DEFAULT_CUMULATIVE
    source: str = 'terminal'
    keys: tuple = T.DEFAULT_KEYS
    official_dir: Path = OFFICIAL_DIR
    staging: Path | None = None
    max_days: int = DEFAULT_MAX_DAYS
    day: str | None = None
    start: str = P.FORWARD_START
    prior_check: bool = True
    use_uw: bool = True
    postmarket_dir: Path = P.POSTMARKET_DIR
    historical_from: Path | None = None
    decision_prices: dict | None = None
    features: bool = False                  # step 7 (the command line turns it on unless --no-features)
    features_csv: Path | None = None        # default: research_notes/Compass features/forward/forward_sessions.csv
    features_report: Path | None = None     # default: …/forward/FORWARD_REPORT.md
    features_work: Path | None = None       # default: <replay root>/_compass_features
    use_cboe: bool = True
    edge: bool = False                      # step 8 (the command line turns it on unless --no-edge)
    edge_folder: Path | None = None         # default: research_notes/Edge search/H5_H6/forward
    h7_folder: Path | None = None           # default: research_notes/Edge search/H7_H8_H9/forward
    edge_store: Path | None = None          # default: <parquet root>/edge_forward/eod

    def __post_init__(self):
        self.parquet_root, self.replay_root, self.cumulative = Path(self.parquet_root), Path(self.replay_root), Path(self.cumulative)
        self.staging = Path(self.staging) if self.staging else self.parquet_root / STAGING_DIR


def make_log(root: Path | None, stream=sys.stderr, scrub: R.Scrub | None = None) -> logging.Logger:
    scrub = scrub or R.Scrub(os.environ.get('UW_API_TOKEN'))
    log = logging.getLogger('daily_forward')
    log.setLevel(logging.INFO)
    log.propagate = False
    for h in list(log.handlers):
        log.removeHandler(h)

    class F(R.ScrubFormatter):
        def format(self, record):
            return red(super().format(record))
    if stream is not None:
        h = logging.StreamHandler(stream)
        h.setFormatter(F(scrub))
        log.addHandler(h)
    if root is not None:
        d = Path(root) / '_logs'
        d.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(d / f'daily_forward-{dt.datetime.now(R.UTC):%Y-%m-%d}.log', encoding='utf-8')
        fh.setFormatter(F(scrub))
        log.addHandler(fh)
    return log


def features_module():
    """research_notes/Compass features/forward/forward_features.py (imported only when step 7 runs)"""
    d = str(R.REPO / 'research_notes' / 'Compass features' / 'forward')
    if d not in sys.path:
        sys.path.insert(0, d)
    import forward_features as FF  # noqa: E402
    return FF


def run_features(job: Job, log: logging.Logger, spx_fetch=None) -> dict:
    """step 7: every whole forward session (the replay root's complete sessions, in the layout) not yet in the features file"""
    FF = features_module()
    comp = B.complete_sessions(job.replay_root, job.keys, FF.FORWARD_START, '9999-12-31')[0]
    days = [d for d in comp if (job.day is None or d == job.day) and day_in_layout(job.parquet_root, d)]
    work = job.features_work or (job.replay_root / '_compass_features')
    fetch = spx_fetch if spx_fetch is not None else (FF.default_fetch_text if job.use_cboe else None)
    return FF.run(days, job.parquet_root, work, job.official_dir, csv_path=job.features_csv or FF.CSV_PATH,
                  report_path=job.features_report or FF.REPORT_PATH, fetch_text=fetch, log=log,
                  today=dt.datetime.now(R.UTC).astimezone(R.NY).date().isoformat())


def features_step(job: Job, res: dict, log: logging.Logger, spx_fetch=None) -> None:
    """step 7 into the run's result: a failure is one DAILY-FORWARD FAIL line and rc 1, never a half-written session"""
    try:
        fr = run_features(job, log, spx_fetch)
        res['features_added'], res['features_failure'], res['cboe_calls'] = fr['added'], fr['failure'], fr['calls']
        if fr['failure']:
            day_, _, why_ = fr['failure'].partition(' ')
            step_, _, why_ = why_.partition(': ')
            log.error('DAILY-FORWARD FAIL %s features-%s: %s', day_, step_, red(why_)[:400])
            res.update(rc=1, failure=res['failure'] or f'features {red(fr["failure"])}'[:400])
        else:
            log.info('compass features: %s', ' '.join(fr['added']) or 'nothing new')
    except Exception as e:  # noqa: BLE001
        log.error('DAILY-FORWARD FAIL - features: %s', red(f'{type(e).__name__}: {e}')[:400])
        res.update(rc=1, failure=res['failure'] or f'features: {red(type(e).__name__)}')


def edge_module():
    """research_notes/Edge search/H5_H6/edge_forward.py (imported only when step 8 runs)"""
    d = str(R.REPO / 'research_notes' / 'Edge search' / 'H5_H6')
    if d not in sys.path:
        sys.path.insert(0, d)
    import edge_forward as EF  # noqa: E402
    return EF


def terminal_eod(theta_fetcher=None):
    """step 8's end-of-day fetch through the Theta Terminal (the run's --source terminal): GET /option/history/eod with
    symbol, expiration (* = every one) and start_date = end_date = the day, format=ndjson, 127.0.0.1 only, no key —
    the fetcher made on the first call and the terminal's own status asked first"""
    EF = edge_module()
    box = {}

    def fetch(sym: str, day: str, expiration: str | None) -> list[dict]:
        if 'th' not in box:
            th = theta_fetcher or B.ThetaFetch(os.environ.get('THETA_BASE') or B.THETA_BASE)
            ok, word = th.terminal_status()
            if not ok:
                raise EF.EdgeFetchError(f'the Theta Terminal on {th.base} is not CONNECTED ({word}) — nothing asked')
            box['th'] = th
        d8 = day.replace('-', '')
        ans = box['th'].get('/option/history/eod', {'symbol': sym, 'expiration': '*' if expiration is None else expiration.replace('-', ''),
                                                    'start_date': d8, 'end_date': d8})
        if not ans.ok:
            raise EF.EdgeFetchError(red(f'{ans.status}: {ans.error}')[:300])
        if not ans.rows:
            raise EF.EdgeFetchError('HTTP 200 with no rows')
        return ans.rows
    return fetch


def run_edge(job: Job, log: logging.Logger, closes: P.OfficialCloses | None = None, theta_fetcher=None, sdk: SdkSource | None = None,
             edge_fetch=None) -> dict:
    """step 8: every whole forward session (the replay root's complete sessions) through edge_forward.run"""
    EF = edge_module()
    comp = B.complete_sessions(job.replay_root, job.keys, EF.H5_START, '9999-12-31')[0]
    closes = closes if closes is not None else P.OfficialCloses(uw_dirs=(job.official_dir,))
    if edge_fetch is None:
        if job.source == 'sdk':
            sdk = sdk or SdkSource(log=log)
            edge_fetch = sdk.eod
        else:
            edge_fetch = terminal_eod(theta_fetcher)
    return EF.run(comp, job.parquet_root, lambda nm, d: closes.get(nm, d)[0], eod_fetch=edge_fetch,
                  store=job.edge_store or (job.parquet_root / EF.EOD_STORE), folder=job.edge_folder, log=log)


def h7_module():
    """research_notes/Edge search/H7_H8_H9/forward_h7_h9.py (imported only when step 8 runs)"""
    d = str(R.REPO / 'research_notes' / 'Edge search' / 'H7_H8_H9')
    if d not in sys.path:
        sys.path.insert(0, d)
    import forward_h7_h9 as FH  # noqa: E402
    return FH


def run_h7(job: Job, log: logging.Logger, closes: P.OfficialCloses | None = None) -> dict:
    """step 8's H7: every complete forward session from 2026-10-23 through forward_h7_h9.run, on the closes and bars the job
    already keeps (it fetches nothing). → forward_h7_h9.run's result"""
    FH = h7_module()
    comp = B.complete_sessions(job.replay_root, job.keys, FH.SERIES_START, '9999-12-31')[0]
    closes = closes if closes is not None else P.OfficialCloses(uw_dirs=(job.official_dir,))
    return FH.run(comp, job.parquet_root, closes.get, folder=job.h7_folder, log=log)


def edge_step(job: Job, res: dict, log: logging.Logger, closes=None, theta_fetcher=None, sdk=None, edge_fetch=None) -> None:
    """step 8 into the run's result: each failure is one DAILY-FORWARD FAIL line and rc 1, never a half-written row"""
    try:
        hr = run_h7(job, log, closes)
        res['edge_h7_added'] = hr['h7_added']
        for f in hr['failures']:
            day_, _, why_ = f.partition(' ')
            step_, _, why_ = why_.partition(': ')
            log.error('DAILY-FORWARD FAIL %s edge-%s: %s', day_, step_, red(why_)[:400])
        if hr['failures']:
            res.update(rc=1, failure=res['failure'] or f'edge {red(hr["failures"][0])}'[:400])
        else:
            log.info('edge H7: %s', ' '.join(hr['h7_added']) or 'nothing new')
    except Exception as e:  # noqa: BLE001
        log.error('DAILY-FORWARD FAIL - edge-h7: %s', red(f'{type(e).__name__}: {e}')[:400])
        res.update(rc=1, failure=res['failure'] or f'edge-h7: {red(type(e).__name__)}')
    try:
        er = run_edge(job, log, closes, theta_fetcher, sdk, edge_fetch)
        res['edge_added'] = {k: er[k] for k in ('h5_added', 'h6_entries', 'h6_trades')}
        res['edge_calls'] = er['calls']
        for f in er['failures']:
            day_, _, why_ = f.partition(' ')
            step_, _, why_ = why_.partition(': ')
            log.error('DAILY-FORWARD FAIL %s edge-%s: %s', day_, step_, red(why_)[:400])
        if er['failures']:
            res.update(rc=1, failure=res['failure'] or f'edge {red(er["failures"][0])}'[:400])
        else:
            log.info('edge H5/H6: H5 %s; H6 entries %s, closed %s; %d end-of-day calls', ' '.join(er['h5_added']) or 'nothing new',
                     ' '.join(er['h6_entries']) or 'none', ' '.join(er['h6_trades']) or 'none', er['calls'])
    except Exception as e:  # noqa: BLE001
        log.error('DAILY-FORWARD FAIL - edge: %s', red(f'{type(e).__name__}: {e}')[:400])
        res.update(rc=1, failure=res['failure'] or f'edge: {red(type(e).__name__)}')


def run_job(job: Job, now: dt.datetime | None = None, log: logging.Logger | None = None, theta_fetcher=None, sdk: SdkSource | None = None,
            uw_client=None, closes: P.OfficialCloses | None = None, window: str | None = None, spx_fetch=None, edge_fetch=None) -> dict:
    """One run. → {'rc': 0 ok or nothing to do | 1 a failure | 2 refused, 'pending', 'completed', 'appended', 'failure',
    'uw_calls', 'logins', 'fetched'}"""
    now = now or dt.datetime.now(R.UTC)
    ny = now.astimezone(R.NY)
    log = log or make_log(job.replay_root)
    res = {'rc': 0, 'pending': [], 'completed': [], 'appended': [], 'failure': None, 'uw_calls': 0, 'logins': 0, 'fetched': [],
           'source': job.source, 'version': JOB_VERSION}
    try:
        if job.source not in ('terminal', 'sdk'):
            raise Refused(f'--source is terminal or sdk (got {job.source!r})')
        if in_theta_gap(ny):
            raise Refused(f'{ny:%H:%M} New York is inside Theta\'s gap (00:00–01:45): nothing is fetched and the SDK never signs in then')
        if job.source == 'sdk':
            win = parse_window(window if window is not None else os.environ.get(SDK_WINDOW_ENV))
            if not in_window(ny, win):
                raise Refused(f'{ny:%H:%M} New York is outside {SDK_WINDOW_ENV} '
                              f'({win[0] // 60:02d}:{win[0] % 60:02d}-{win[1] // 60:02d}:{win[1] % 60:02d}) — the SDK login signs the '
                              'owner\'s terminal out, so it runs only inside the window the owner set')
    except Refused as e:
        log.error('DAILY-FORWARD REFUSED: %s', e)
        res.update(rc=2, failure=str(e))
        return res
    listed = listed_sessions(job.cumulative)
    pend = pending_sessions(listed, now, job.max_days, start=job.start, only=job.day)
    # the sessions the cumulative report already lists must be whole in THIS replay root too (the forward block is
    # regenerated from it): on a new machine — the owner's PC with the committed report — they are rebuilt first
    whole = set(B.complete_sessions(job.replay_root, job.keys, P.FORWARD_START, '9999-12-31')[0]) if listed else set()
    rebuild = [d for d in listed if d not in whole and (job.day is None or d == job.day)]
    res['pending'], res['rebuild'] = pend, rebuild
    pend = sorted(set(pend) | set(rebuild))
    if not pend:
        log.info('DAILY-FORWARD OK: nothing pending (%d forward sessions in %s; the next is due after %s New York on a trading day)',
                 len(listed), job.cumulative.name, READY_AFTER)
        if job.features:                     # a session the tracker finished earlier may still wait for step 7
            features_step(job, res, log, spx_fetch)
        if job.edge:                         # … and for step 8 (an H6 exit falls weeks after its entry)
            edge_step(job, res, log, closes, theta_fetcher, sdk, edge_fetch)
        return res
    log.info('daily forward %s (%s): pending %s%s', JOB_VERSION, job.source, ' '.join(res['pending']) or '—',
             f"; listed but not in this replay root, rebuilt first: {' '.join(rebuild)}" if rebuild else '')
    closes = closes if closes is not None else P.OfficialCloses(uw_dirs=(job.official_dir,))
    if job.source == 'sdk' and sdk is None:
        sdk = SdkSource(log=log)
    for day in pend:
        step = 'fetch'
        try:
            if not day_in_layout(job.parquet_root, day):
                stage = job.staging / day
                if job.source == 'terminal':
                    fr = B.fetch_theta(day, day, stage, fetcher=theta_fetcher, norm_roots=(job.parquet_root,), now=now, stream=None)
                    why = fr.get('aborted') or '; '.join(f'{x["file"]}: {x["error"]}' for x in fr['failed'] + fr['incomplete'] + fr['exists'] + fr['not_asked'])
                else:
                    fr = sdk.fetch(day, stage, norm_roots=(job.parquet_root,))
                    why = '; '.join(f'{x["file"]}: {x["error"]}' for x in fr['failed'])
                if fr['rc'] != 0:
                    raise JobError(step, day, red(why)[:400] or 'the fetch did not come back whole')
                res['fetched'].append(day)
                step = 'verify-parquet'
                rep = B.verify_parquet(stage, day, day, prior=False, norm_roots=(job.parquet_root,), stream=None)
                if not rep['ok']:
                    raise JobError(step, day, '; '.join(rep['fails'])[:400])
                step = 'merge-parquet'
                mr = B.merge_parquet(stage, job.parquet_root, stream=None)
                if mr['rc'] != 0:
                    raise JobError(step, day, (mr.get('note') or '') + ' ' + json.dumps({k: mr[k] for k in ('refused', 'overlap', 'identical')}, default=str)[:300])
                shutil.rmtree(stage, ignore_errors=True)
                log.info('%s: fetched (%s), verified and merged — %d files', day, job.source, len(mr['copied']))
            else:
                log.info('%s: already in the layout — not fetched', day)
            step = 'verify-layout'
            rep = B.verify_parquet(job.parquet_root, day, day, prior=job.prior_check, stream=None)
            if not rep['ok']:
                raise JobError(step, day, '; '.join(rep['fails'])[:400])
            step = 'official-close'
            closes, missing, calls = ensure_official(day, closes, job.official_dir, uw_client if job.use_uw else None, log)
            res['uw_calls'] += calls
            if missing:
                raise JobError(step, day, f'no official close for {", ".join(missing)} yet (UW\'s daily bar'
                               + (' asked' if job.use_uw and uw_client is not None else ' not asked: no token / --no-uw') + ', no Theta EOD on disk) — '
                               'the session is never settled on the 15:59 bar and appended; the next run asks again')
            step = 'decision-price'
            _, calls = ensure_decision(day, uw_client if job.use_uw else None, job.postmarket_dir, log, now)
            res['uw_calls'] += calls
            step = 'replay'
            rr = B.replay(day, day, job.keys, job.parquet_root, job.replay_root, settle_on='official', closes=closes, progress=None)
            st = B.read_days(job.replay_root).get(day, {})
            if st.get('status') != 'replayed':
                raise JobError(step, day, f'the replay says {st.get("status")}: {json.dumps(st)[:300]}')
            step = 'complete'
            comp, pend_why = B.complete_sessions(job.replay_root, job.keys, day, day)
            if day not in comp:
                raise JobError(step, day, pend_why.get(day, 'not whole'))
            res['completed'].append(day)
            log.info('%s: replayed whole (%s s)', day, rr['seconds'])
        except JobError as e:
            log.error('DAILY-FORWARD FAIL %s %s: %s', e.day or day, e.step, red(e.why))
            res.update(rc=1, failure=f'{e.day or day} {e.step}: {red(e.why)}')
            break
        except Exception as e:  # noqa: BLE001 — anything else is a failure of this day's step, said, never half-appended
            log.error('DAILY-FORWARD FAIL %s %s: %s', day, step, red(f'{type(e).__name__}: {e}')[:400])
            res.update(rc=1, failure=f'{day} {step}: {red(type(e).__name__)}')
            break
    res['logins'] = sdk.logins if sdk is not None else 0
    if res['completed']:
        try:
            ar = B.append_cumulative(job.replay_root, job.cumulative, job.keys, parquet_root=job.parquet_root, closes=closes,
                                     decision_prices=job.decision_prices if job.decision_prices is not None else
                                     P.decision_prices_on_disk(postmarket_dir=job.postmarket_dir, extra_dirs=B.uw_1m_dirs()),
                                     through=res['completed'][-1], historical_from=job.historical_from)
            res['appended'] = ar['added']
            log.info('appended to %s: %s', job.cumulative, ' '.join(ar['added']) or 'nothing new')
        except Exception as e:  # noqa: BLE001
            log.error('DAILY-FORWARD FAIL %s append: %s', res['completed'][-1], red(f'{type(e).__name__}: {e}')[:400])
            res.update(rc=1, failure=f'append: {red(e)}'[:400])
    if job.features:
        features_step(job, res, log, spx_fetch)
    if job.edge:
        edge_step(job, res, log, closes, theta_fetcher, sdk, edge_fetch)
    if res['rc'] == 0:
        log.info('DAILY-FORWARD OK: %d session(s) completed, %d appended (%s), %d UW calls, %d Theta logins', len(res['completed']),
                 len(res['appended']), ' '.join(res['appended']) or '—', res['uw_calls'], res['logins'])
    return res


def status(job: Job, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(R.UTC)
    listed = listed_sessions(job.cumulative)
    return {'cumulative': str(job.cumulative), 'listed': listed, 'pending': pending_sessions(listed, now, 50),
            'replay_root': str(job.replay_root), 'replay_mode': B.root_mode(job.replay_root), 'parquet_root': str(job.parquet_root)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--source', choices=('terminal', 'sdk'), default=os.environ.get('DAILY_FORWARD_SOURCE') or 'terminal',
                   help='terminal (default: the Theta Terminal already running on this machine — no login) or sdk (one login; only inside THETA_SDK_WINDOW)')
    p.add_argument('--parquet-root', default=os.environ.get('PAPER_PARQUET_ROOT'), help='the stored Parquet layout (PAPER_PARQUET_ROOT)')
    p.add_argument('--backtest-data', default=os.environ.get('PAPER_FORWARD_DATA') or str(B.DEFAULT_OFFICIAL_ROOT),
                   help='the replay root (official-close settlement; default data_recorder/paper_backtest_official)')
    p.add_argument('--cumulative', default=os.environ.get('PAPER_CUMULATIVE') or str(B.DEFAULT_CUMULATIVE), help='the cumulative report')
    p.add_argument('--historical-from', help='a report embedded as the historical sections when the cumulative report is new')
    p.add_argument('--official-dir', default=str(OFFICIAL_DIR), help='where UW\'s daily bars are kept as fetched')
    p.add_argument('--candidates', default=','.join(T.DEFAULT_KEYS))
    p.add_argument('--day', help='one session (default: every pending one, oldest first)')
    p.add_argument('--max-days', type=int, default=DEFAULT_MAX_DAYS)
    p.add_argument('--no-uw', action='store_true', help='ask UW nothing: the official close must be on disk already')
    p.add_argument('--no-prior-check', action='store_true', help='skip the sessions-before check of --verify-parquet on the layout')
    p.add_argument('--decision-prices', help='the after-hours study\'s CSV name,day,price')
    p.add_argument('--status', action='store_true', help='what the cumulative report holds and what is pending; asks nothing')
    p.add_argument('--no-features', action='store_true', help='skip step 7 (the Compass features forward test)')
    p.add_argument('--no-cboe', action='store_true', help='step 7 asks Cboe nothing: the official SPX close must be on disk already')
    p.add_argument('--no-edge', action='store_true', help='skip step 8 (the edge-search H5, H6 and H7 forward tests)')
    a = p.parse_args(argv)
    if not a.parquet_root:
        print('--parquet-root (or PAPER_PARQUET_ROOT) names the stored Parquet layout', file=sys.stderr)
        return 2
    job = Job(Path(a.parquet_root), Path(a.backtest_data), Path(a.cumulative), a.source,
              tuple(k.strip() for k in a.candidates.split(',') if k.strip()), Path(a.official_dir), max_days=a.max_days, day=a.day,
              prior_check=not a.no_prior_check, use_uw=not a.no_uw, historical_from=Path(a.historical_from) if a.historical_from else None,
              decision_prices=B.read_decision_prices(a.decision_prices), features=not a.no_features, use_cboe=not a.no_cboe,
              edge=not a.no_edge)
    if a.status:
        print(json.dumps(status(job), indent=1))
        return 0
    token = os.environ.get('UW_API_TOKEN')
    log = make_log(job.replay_root, scrub=R.Scrub(token))
    uw = None
    if job.use_uw and token:
        clock = R.Clock()
        uw = R.UwClient(token, R.RateLimiter(max_in_flight=1, per_minute=30, daily_budget=10, clock=clock), log, clock, R.Scrub(token))
    elif job.use_uw:
        log.warning('UW_API_TOKEN is not set: the official close must already be on disk (UW\'s daily bar or Theta\'s EOD)')
    res = run_job(job, log=log, uw_client=uw)
    print(json.dumps({k: v for k, v in res.items()}, default=str))
    return res['rc']


if __name__ == '__main__':
    sys.exit(main())
