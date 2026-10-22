#!/usr/bin/env python3
"""
paper_backtest.py — the historical replay of paper_tracker.py (`--backtest`), its report, the parity check against the
research's own trade tables (`python3 -I scripts/paper_backtest.py parity …`), and the Theta fetch that writes later
sessions into the same Parquet layout (`--fetch-theta`). It reads files only: no UW call, no Theta call in a replay.

THE REPLAY RUNS THE LIVE TRACKER ITSELF. A `ReplayClient` answers the UW routes the tracker asks — the same-day chain
(/option-contracts?expiry=D), the stock-state, ohlc/1m, ohlc/1d and SPX's book price — out of the stored Parquet at the
replay clock's minute, and `paper_tracker.Tracker` does everything else exactly as live: `capture` (the strike rules,
the fills, the tradable rule, candidate 3's features through vol_model and both frozen deciles), `close_quotes` at 15:58,
and `settle` (intrinsic on the official close, $0.65 a leg at the open, nothing at expiry, the mid and the $0.01 / $0.02
stresses, the 15:58 exit beside). There is no second strike or P&L implementation here.

THE ADAPTER (a minute m = 0 is 09:30 New York; a Parquet row stamped t is the quote at t; a bar stamped t closes at t+1):
  - the chain at minute m: every row of ROOT/data_full/chains/<ROOT>/<D>.parquet stamped m becomes a UW row — the
    option_symbol written as UW writes it (OCC: root, YYMMDD, C/P, the strike × 1000 in eight digits; SPY, QQQ and the
    SPXW root for SPX), nbbo_bid / nbbo_ask (null where Theta had no quote), nbbo_bid_size / nbbo_ask_size (the sizes UW's
    route lacks, so the fill facts can be read), the same-day expiry. 500 a page, as UW pages.
  - spot (stock-state `close`) at minute m: the close of the last bar that has closed by m — the bar stamped m − 1, the
    research's spot convention and the live one (stock-state's last trade); `prev_close` the session before's last
    regular close. SPX's price at a fly_spxw capture is the SPX print stamped m (the research's) — the live tracker's
    parity spot is logged beside it (`parity_strikes`).
  - ohlc/1m: the day's bars as UW stamps them (start_time the bar's open, `r` 09:30–15:59, `po` the 16:00 bar when it
    printed); on the replayed day only the bars closed by the clock's minute — nothing ahead of the clock is served.
  - the official close (ohlc/1d's `r` row): SINCE .2 THE OFFICIAL CLOSE by default (`--settle-on official`: UW's daily
    bar, then Theta's EOD — paper_audit.OfficialCloses; none on disk → the 15:59 bar, `settle_source = 1559_bar`, the
    session flagged), with UW's post-market `po` bar where on disk. `--settle-on 1559` keeps THE 15:59 BAR'S CLOSE — the
    research's convention (hyp_c common.py "the 16:00 close - the bar stamped 15:59"; hyp_b takes the last bar at or
    before 16:00 with a close, the same bar since Theta's 16:00 bar carries none), labelled `close_official_from` =
    OFFICIAL_FROM on every settle row, and its report exactly as before (the committed reports, byte for byte).
  - SPXW's settlement (fly_spxw, off unless listed): the last SPX print at or before 16:00 (`settle_source`
    'spx_last_print'), the research's SET proxy.
  - VIX: the day's prints out of ROOT/data/index/VIX through the tracker's Theta path (the print stamped m is the price
    at m; the session before's last print), so the full model is the primary decile whenever VIX is on disk.
  - the calendar: a weekday with no SPY underlying file inside the files' span is a holiday; a session whose SPY bars end
    before 15:00 is a half day and is skipped, as the reports skipped them.

STORAGE: rows go to a root of their own (default data_recorder/paper_backtest/, never the live paper root — refused if
the two meet), the live schema plus `source` = 'backtest-parquet' on every row; a replayed minute is a marker like a
live one, so a run resumes and a second run of the same days writes nothing. `_replay/days.json` keeps what each day
was (replayed, holiday, half day, which file was missing).

    python3 -I scripts/paper_tracker.py --backtest --start 2025-01-02 --end 2026-10-09 [--candidates condor_em1,fly5,condor_d20]
                                        [--parquet-root R] [--backtest-data DIR] [--out DIR]
    python3 -I scripts/paper_tracker.py --fetch-theta --start 2026-10-12 --end 2026-10-21 --parquet-root R [--only SPY-underlying,…]
                                        [--stock-venue nqb|utp_cta] [--compare-root REF] [--theta-in-flight 1-3] [--force]
    python3 -I scripts/paper_tracker.py --verify-parquet --start D1 --end D2 --parquet-root R [--only …] [--no-prior]
                                        [--compare-root REF] [--verify-json FILE]
    python3 -I scripts/paper_tracker.py --merge-parquet SRC --parquet-root DST [--force]
(the fetch's audit, its manifest and staging, and the owner's commands: docs/fetch-theta-audit.md)
    python3 -I scripts/paper_backtest.py parity --start 2022-11-11 --end 2026-10-09 [--backtest-data DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import logging
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eod_recorder as R  # noqa: E402
import paper_audit as P  # noqa: E402
import paper_tracker as T  # noqa: E402
import vol_model as V  # noqa: E402

REPLAY_VERSION = 'paper-backtest-2026-10-22.2'   # .2: the official close by default (--settle-on 1559 keeps the old convention), the audit's report
SOURCE = 'backtest-parquet'
DEFAULT_REPLAY_ROOT = R.REPO / 'data_recorder' / 'paper_backtest'                    # --settle-on 1559 (the committed reports)
DEFAULT_OFFICIAL_ROOT = R.REPO / 'data_recorder' / 'paper_backtest_official'         # --settle-on official (the default)
SETTLE_MODES = ('official', '1559')
DEFAULT_SETTLE = 'official'
OFFICIAL_FROM = 'replay: the 15:59 bar close (the research convention)'
SPX_SETTLE = 'spx_last_print'
SPX_SPOT_SOURCE = 'replay: the SPX print at the minute (the research convention)'
CHAIN_ROOT = {'SPY': 'SPY', 'QQQ': 'QQQ', 'SPX': 'SPXW'}
BOOT_SEED, BOOT_N = 20261016, 2000
MINUTE_OF = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:5]) - 570     # noqa: E731


def weekdays(a: str, b: str) -> list[str]:
    d, e, out = dt.date.fromisoformat(a), dt.date.fromisoformat(b), []
    while d <= e:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _j(ts: pl.Expr) -> pl.Expr:
    """the minute index of a New York timestamp: 0 = 09:30"""
    return (ts.dt.hour().cast(pl.Int32) * 60 + ts.dt.minute().cast(pl.Int32) - 570).alias('j')


# ---- the stored files ----------------------------------------------------------------------------------------------------------------

class ParquetSource:
    """ROOT/data_full/chains/<ROOT>/<D>.parquet, ROOT/data/underlying/<SYM>/<D>.parquet, ROOT/data/index/<SYM>/<D>.parquet;
    a few days kept in memory (a day is read once)"""

    def __init__(self, root: Path, keep: int = 6):
        self.root = Path(root)
        self.keep = keep
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._days: dict = {}

    def chain_file(self, root_sym: str, day: str) -> Path:
        return self.root / 'data_full' / 'chains' / root_sym / f'{day}.parquet'

    def under_file(self, sym: str, day: str) -> Path:
        return self.root / 'data' / 'underlying' / sym / f'{day}.parquet'

    def index_file(self, sym: str, day: str) -> Path:
        return self.root / 'data' / 'index' / sym / f'{day}.parquet'

    def file_for(self, kind: str, sym: str, day: str) -> Path:
        return {'chain': self.chain_file, 'under': self.under_file, 'index': self.index_file}[kind](sym, day)

    def days(self, sym: str = 'SPY') -> list[str]:
        if sym not in self._days:
            d = self.root / 'data' / 'underlying' / sym
            self._days[sym] = sorted(f.name[:10] for f in d.glob('*.parquet')) if d.is_dir() else []
        return self._days[sym]

    def refused(self, f: Path, day: str) -> bool:
        """a file its day's manifest calls FAILED / INCOMPLETE is read as absent (no manifest — the stored files — nothing is)"""
        if not (self.root / MANIFEST_DIR / f'{day}.json').exists():
            return False
        return f.relative_to(self.root).as_posix() in refusals(self.root, day)

    def _get(self, key, load):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        v = load()
        with self._lock:
            self._cache[key] = v
            while len(self._cache) > self.keep * 4:
                self._cache.popitem(last=False)
        return v

    def chain(self, root_sym: str, day: str) -> pl.DataFrame | None:
        f = self.chain_file(root_sym, day)

        def load():
            if not f.exists() or self.refused(f, day):
                return None
            c = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
            return c.with_columns(_j(pl.col('timestamp'))).drop('timestamp').sort('j', 'strike', 'right')
        return self._get(('chain', root_sym, day), load)

    def bars(self, sym: str, day: str) -> dict | None:
        """{'j': [...], 'o','h','l','c','v'} for the bars stamped 09:30 .. 16:00 with a close (j 0 .. 390)"""
        f = self.under_file(sym, day)

        def load():
            if not f.exists() or self.refused(f, day):
                return None
            b = pl.read_parquet(f, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).with_columns(_j(pl.col('timestamp')))
            b = b.filter(pl.col('close').is_not_null() & (pl.col('j') >= 0) & (pl.col('j') <= 390)).sort('j')
            return {'j': b['j'].to_list(), 'o': b['open'].to_list(), 'h': b['high'].to_list(), 'l': b['low'].to_list(),
                    'c': b['close'].to_list(), 'v': b['volume'].to_list()}
        return self._get(('bars', sym, day), load)

    def prints(self, sym: str, day: str) -> list | None:
        """[(j, price)] for the prints stamped 09:30 .. 16:00 with a price > 0"""
        f = self.index_file(sym, day)

        def load():
            if not f.exists() or self.refused(f, day):
                return None
            p = pl.read_parquet(f, columns=['timestamp', 'price']).with_columns(_j(pl.col('timestamp')))
            p = p.filter(pl.col('price').is_not_null() & (pl.col('price') > 0) & (pl.col('j') >= 0) & (pl.col('j') <= 390)).sort('j')
            return list(zip(p['j'].to_list(), p['price'].to_list()))
        return self._get(('prints', sym, day), load)

    def is_session(self, day: str) -> bool:
        """a session = SPY's file holds at least 30 bars with a close (the research's day table: read_bars / summary — a
        holiday's file, padded with empty bars, drops out)"""
        b = self.bars('SPY', day)
        return bool(b and len(b['j']) >= 30)

    def is_half(self, day: str) -> bool:
        """the research's rule: SPY's last bar with a close stamped before 15:00"""
        b = self.bars('SPY', day)
        return bool(b and b['j'] and b['j'][-1] < 330)

    def last_regular_close(self, sym: str, day: str) -> tuple[float | None, int | None]:
        """the close of the 15:59 bar (else the last bar before it with a close): the replay's official close"""
        b = self.bars(sym, day)
        if not b:
            return None, None
        for j, c in zip(reversed(b['j']), reversed(b['c'])):
            if j <= 389 and c is not None:
                return float(c), j
        return None, None

    def previous_day(self, sym: str, day: str) -> str | None:
        ds = self.days(sym)
        import bisect
        i = bisect.bisect_left(ds, day) - 1
        return ds[i] if i >= 0 else None


def occ(root: str, day: str, right: str, strike: float) -> str:
    """the OCC option_symbol as UW writes it: SPY261020C00773000, SPXW261020P05800000"""
    return f'{root}{day[2:4]}{day[5:7]}{day[8:10]}{"C" if right.upper().startswith("C") else "P"}{int(round(strike * 1000)):08d}'


def chain_rows(src: ParquetSource, name: str, day: str, m: int) -> list | None:
    """THE ADAPTER: the Parquet rows stamped m → UW /option-contracts rows (option_symbol, nbbo_bid, nbbo_ask, the sizes);
    None when the day's chain file is not on disk"""
    root = CHAIN_ROOT.get(name, name)
    c = src.chain(root, day)
    if c is None:
        return None
    s = c.filter(pl.col('j') == m)
    out = []
    for k, r, b, a, bs, as_ in zip(s['strike'], s['right'], s['bid'], s['ask'], s['bid_size'], s['ask_size']):
        out.append({'option_symbol': occ(root, day, r, k), 'nbbo_bid': b, 'nbbo_ask': a, 'nbbo_bid_size': bs, 'nbbo_ask_size': as_})
    return out


# ---- the replay client: the UW routes the tracker asks, answered from the files at the clock's minute ------------------------------

class ReplayClock(R.FakeClock):
    def set(self, when: dt.datetime) -> None:
        with self._lock:
            self._t = (when - self._start).total_seconds()


class ReplayClient:
    """Answers GET <UW path> as UW would at the clock's minute, from the stored Parquet; never touches the network. Index
    names answer stock-state / ohlc with 422, as UW Basic does. `settle_on`: 'official' (the default since .2) answers
    ohlc/1d with the official close out of `closes` (paper_audit.OfficialCloses — UW's daily bar, then Theta's EOD) and
    UW's post-market bar where on disk, nothing when no source holds the day (the tracker then settles on the 15:59 bar,
    labelled '1559_bar' and flagged); '1559' answers it with the 15:59 bar's close, the research's convention."""

    def __init__(self, src: ParquetSource, limiter, log, clock, settle_on: str = '1559', closes: P.OfficialCloses | None = None):
        if settle_on not in SETTLE_MODES:
            raise ValueError(f'settle_on is one of {SETTLE_MODES}')
        self.src, self.limiter, self.log, self.clock = src, limiter, log, clock
        self.settle_on = settle_on
        self.closes = closes if closes is not None else (P.OfficialCloses() if settle_on == 'official' else None)
        self.calls = 0
        self.requests: list = []

    def _now(self) -> tuple[str, int]:
        t = self.clock.utcnow().astimezone(R.NY)
        return t.strftime('%Y-%m-%d'), t.hour * 60 + t.minute - 570

    def get(self, path: str, params: dict | None = None) -> R.Answer:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        self.limiter.acquire()
        try:
            self.calls += 1
            self.requests.append((path, dict(params)))
            status, body, err = self._serve(path, params)
        finally:
            self.limiter.release()
        if status != 200:
            return R.Answer(status, [], 0, error=f'{status}: {err}')
        return R.Answer(200, R.rows_of(body), 0, body=body)

    def _bar_rows(self, name: str, day: str, upto_j: int | None) -> list:
        b = self.src.bars(name, day)
        if not b:
            return []
        rows = []
        for j, o, h, l, c, v in zip(b['j'], b['o'], b['h'], b['l'], b['c'], b['v']):
            if upto_j is not None and j > upto_j:
                continue
            t = R.ny_at(day, '09:30') + dt.timedelta(minutes=j)
            rows.append({'start_time': R.iso_z(t), 'end_time': R.iso_z(t + dt.timedelta(minutes=1)), 'market_time': 'r' if j <= 389 else 'po',
                         'open': o, 'high': h, 'low': l, 'close': c, 'volume': v, 'total_volume': v})
        rows.reverse()                                            # UW answers newest first
        return rows

    def _serve(self, path: str, params: dict):
        parts = path.split('/')
        name = parts[3] if len(parts) > 3 else ''
        today, m = self._now()
        if path.endswith('/option-contracts'):
            day = str(params.get('expiry') or today)
            if day != today:
                return 404, None, f'replay serves the same-day chain of the clock\'s day ({today}), not {day}'
            rows = chain_rows(self.src, name, day, m)
            if rows is None:
                return 404, None, f'no chain file {self.src.chain_file(CHAIN_ROOT.get(name, name), day)}'
            page, limit = int(params.get('page', 0)), int(params.get('limit', 500))
            return 200, {'data': rows[page * limit:(page + 1) * limit]}, None
        if path.endswith('/stock-state'):
            if name in ('SPX', 'VIX') or not self.src.under_file(name, today).exists():
                return 422, None, 'Stock state data is not available for index ticker' if name in ('SPX', 'VIX') else 'no underlying file'
            b = self.src.bars(name, today) or {'j': [], 'c': []}
            last = [(j, c) for j, c in zip(b['j'], b['c']) if j <= min(m - 1, 389)]
            if not last:
                return 200, {'data': {}}, None
            j, c = last[-1]
            pd_ = self.src.previous_day(name, today)
            prev = self.src.last_regular_close(name, pd_)[0] if pd_ else None
            if pd_ and self.settle_on == 'official':
                prev = self.closes.get(name, pd_)[0] or prev        # UW's prev_close is the official close
            tape = R.ny_at(today, '09:30') + dt.timedelta(minutes=j + 1)
            return 200, {'data': {'close': c, 'prev_close': prev, 'market_time': 'regular' if m <= 390 else 'postmarket',
                                  'tape_time': R.iso_z(tape)}}, None
        if path.endswith('/ohlc/1m'):
            if name in ('SPX', 'VIX'):
                return 422, None, 'cboe_index_access_missing'
            day = str(params.get('date') or today)
            if day > today:
                return 200, {'data': []}, None
            return 200, {'data': self._bar_rows(name, day, (m - 1) if day == today else None)}, None
        if path.endswith('/ohlc/1d'):
            day = str(params.get('date') or today)
            if day > today or (day == today and m < 390):
                return 200, {'data': []}, None
            if self.settle_on == 'official':
                rows = []
                px, src_ = self.closes.get(name, day)
                if px is not None:
                    rows.append({'date': day, 'market_time': 'r', 'close': px, 'source': src_})
                lo, hi, pm_src = self.closes.post_market(name, day)
                if lo is not None:
                    rows.append({'date': day, 'market_time': 'po', 'low': lo, 'high': hi, 'source': pm_src})
                return 200, {'data': rows}, None
            px, _ = self.src.last_regular_close(name, day)
            return 200, {'data': [] if px is None else [{'date': day, 'market_time': 'r', 'close': px}]}, None
        if path.endswith('/spot-exposures/strike'):
            pr = self.src.prints('SPX', today) or []
            pr = [(j, p) for j, p in pr if j <= min(m, 390)]
            if not pr:
                return 200, {'data': []}, None
            j, p = pr[-1]
            return 200, {'data': [{'ticker': 'SPX', 'price': p, 'time': R.iso_z(R.ny_at(today, '09:30') + dt.timedelta(minutes=j)), 'strike': None}]}, None
        return 404, None, f'the replay does not serve {path}'


class ParquetVix:
    """The tracker's Theta path (VIX minutes for a day) answered from ROOT/data/index/VIX"""

    def __init__(self, src: ParquetSource):
        self.src = src
        self.error = None
        self.calls = 0

    def prints(self, symbol: str, day: str):
        self.calls += 1
        p = self.src.prints(symbol, day)
        self.error = None if p else f'no {symbol} file for {day}'
        return p or None


class ReplayStore(R.Store):
    """The recorder's Store at the replay root, every row tagged source = 'backtest-parquet'; refuses the live root"""

    def __init__(self, root: Path, live_root: Path | None = None):
        root = Path(root).resolve()
        if live_root is not None:
            lr = Path(live_root).resolve()
            if root == lr or lr in root.parents or root in lr.parents:
                raise ValueError(f'the replay root {root} meets the live paper root {lr} — a replay never writes there')
        super().__init__(root)

    def append(self, ep, name, day, rows, stamps, tags=None):
        return super().append(ep, name, day, [dict(r, source=SOURCE) for r in rows], stamps, tags)


class MemoBarCache(T.BarCache):
    """The tracker's minute-bar cache with the days held in memory (a replay reads the same 20 sessions every capture)"""

    def __init__(self, root: Path):
        super().__init__(root, None)
        self._memo: dict = {}

    def get(self, name: str, day: str):
        k = (name, day)
        if k not in self._memo:
            self._memo[k] = super().get(name, day)
        return self._memo[k]

    def put(self, name: str, day: str, bars: dict, source: str) -> None:
        super().put(name, day, bars, source)
        self._memo[(name, day)] = bars


# ---- the calendar ------------------------------------------------------------------------------------------------------------------------

def install_calendar(src: ParquetSource, days: list[str]) -> tuple:
    """Weekdays inside the SPY files' span with no file are holidays; replayed days whose SPY bars end before 15:00 are
    half days. Patches the recorder's module calendar for this process (returned to undo)."""
    have = src.days('SPY')
    saved = (R.HOLIDAYS, R.HALF_DAYS)
    if have and days:
        hs = set(have)
        # From the recorder's calendar's first year (CAL_FROM) its calendar is the word: a weekday it calls a session is
        # never made a holiday because a file is missing or short — that would read a failed fetch as an empty session
        # (the replay then says the file is missing). Before it, the files are the calendar, as the research read them.
        known = lambda d: d >= CAL_FROM                                           # noqa: E731
        hol = {d for d in weekdays(have[0], have[-1]) if d not in hs and not known(d)}
        # near the replayed days (the model reads the 20 sessions before; VIX the one before) a file with under 30 bars
        # is no session either
        lo = (dt.date.fromisoformat(days[0]) - dt.timedelta(days=60)).isoformat()
        hol |= {d for d in weekdays(max(lo, have[0]), min(days[-1], have[-1])) if d in hs and not known(d) and not src.is_session(d)}
        half = {d for d in days if d in hs and d not in hol and src.is_half(d)}
        R.HOLIDAYS = frozenset(set(R.HOLIDAYS) | hol)
        R.HALF_DAYS = frozenset(set(R.HALF_DAYS) | half)
    return saved


def restore_calendar(saved: tuple) -> None:
    R.HOLIDAYS, R.HALF_DAYS = saved


def needs(cand: T.Candidate, name: str) -> list[tuple[str, str]]:
    """the files a candidate's name reads: (kind, symbol)"""
    out = [('chain', CHAIN_ROOT[name])]
    out.append(('index', 'SPX') if name == 'SPX' else ('under', name))
    return out


# ---- the replay ---------------------------------------------------------------------------------------------------------------------------

def make_tracker(src: ParquetSource, replay_root: Path, live_root: Path | None, keys: tuple, stream=None, settle_on: str = '1559',
                 closes: P.OfficialCloses | None = None):
    scrub = R.Scrub(None)
    store = ReplayStore(replay_root, live_root)
    log = R.make_logger(scrub, store.root / '_logs', stream=stream, name='paper_backtest')
    log.setLevel(logging.WARNING)
    clock = ReplayClock(dt.datetime(2000, 1, 1, tzinfo=R.UTC))
    limiter = R.RateLimiter(max_in_flight=1, per_minute=10 ** 9, daily_budget=10 ** 9, clock=clock)
    client = ReplayClient(src, limiter, log, clock, settle_on=settle_on, closes=closes)

    def spx_spot(day: str, minute: str):
        m = MINUTE_OF(minute)
        p = dict(src.prints('SPX', day) or [])
        return p.get(m), SPX_SPOT_SOURCE

    if settle_on == 'official':
        def official_from(name, day):
            return f'replay: official close ({client.closes.get(name, day)[1]})'
        extra = dict(official_from=official_from, fallback_source=P.FALLBACK_1559, later_state_official=False)
    else:
        extra = dict(official_from=OFFICIAL_FROM)
    tr = T.Tracker(client, store, limiter, log, clock, scrub, cands=T.active_candidates(keys=keys), theta=ParquetVix(src),
                   recorder_root=None, bar_wait_s=0, vix_uw=False, spx_spot=spx_spot, spx_settle_source=SPX_SETTLE, **extra)
    tr.bars = MemoBarCache(store.root)
    return tr, store, client, clock


def days_file(store_root: Path, start: str, end: str) -> Path:
    return Path(store_root) / '_replay' / f'days_{start}_{end}.json'


def read_days(store_root: Path) -> dict:
    """what each day was, merged over every run's file (a later run's word on a day wins)"""
    out: dict = {}
    d = Path(store_root) / '_replay'
    for f in sorted(d.glob('days_*.json'), key=lambda x: x.stat().st_mtime) if d.is_dir() else []:
        try:
            out.update(json.loads(f.read_text(encoding='utf-8')))
        except Exception:
            pass
    return out


def write_days(store_root: Path, start: str, end: str, info: dict) -> None:
    """one file a run (two runs over disjoint days may run at once)"""
    f = days_file(store_root, start, end)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + f'.tmp{os.getpid()}')
    tmp.write_text(json.dumps(dict(sorted(info.items())), indent=0), encoding='utf-8')
    os.replace(tmp, f)


MODE_FILE = 'settle_on.json'


def root_mode(store_root: Path) -> str | None:
    """the settlement convention a replay root was written with: its `_replay/settle_on.json`; a root written before
    .2 (rows, no file) is '1559'; an empty root None"""
    d = Path(store_root) / '_replay'
    f = d / MODE_FILE
    if f.exists():
        try:
            return json.loads(f.read_text(encoding='utf-8'))['settle_on']
        except Exception:  # noqa: BLE001
            return 'unreadable'
    return '1559' if d.is_dir() and any(d.glob('days_*.json')) else None


def claim_mode(store_root: Path, settle_on: str) -> None:
    """one convention a root: rows settled on the 15:59 bar and on the official close never share a root (their
    settle rows would collide in the dedupe — both are `settle_source = official` — and the markers would skip one)"""
    have = root_mode(store_root)
    if have is not None and have != settle_on:
        raise ValueError(f'the replay root {store_root} holds rows settled with --settle-on {have}; this run asks {settle_on} — '
                         f'use another --backtest-data (the defaults: {DEFAULT_OFFICIAL_ROOT.name} for official, {DEFAULT_REPLAY_ROOT.name} for 1559)')
    if have is None:
        f = Path(store_root) / '_replay' / MODE_FILE
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({'settle_on': settle_on, 'version': REPLAY_VERSION}), encoding='utf-8')


def replay(start: str, end: str, keys: tuple, parquet_root: Path, replay_root: Path, live_root: Path | None = None,
           progress=sys.stderr, settle_on: str = DEFAULT_SETTLE, closes: P.OfficialCloses | None = None) -> dict:
    """Every New York weekday in [start, end]: classify it, then run the tracker's events of the day at their minutes.
    `settle_on` 'official' (the default) settles SPY and QQQ on the official close (`closes`, paper_audit.OfficialCloses
    by default), a session with none on the 15:59 bar labelled '1559_bar' and flagged in `_replay/days_*.json`
    (`settle_fallback`); '1559' keeps the research's 15:59-bar convention (the committed reports)."""
    if settle_on not in SETTLE_MODES:
        raise ValueError(f'--settle-on is one of {SETTLE_MODES}')
    src = ParquetSource(parquet_root)
    days = weekdays(start, end)
    ReplayStore(replay_root, live_root)                     # refuses the live root before anything is written
    claim_mode(replay_root, settle_on)
    saved = install_calendar(src, days)
    t0 = time.time()
    info: dict = {}
    try:
        tr, store, client, clock = make_tracker(src, replay_root, live_root, keys, settle_on=settle_on, closes=closes)
        all_cands = tr.cands
        have = src.days('SPY')
        first, last = (have[0], have[-1]) if have else (None, None)
        n = 0
        for day in days:
            refused = refusals(src.root, day)
            spy = rel_of('under', 'SPY', day)
            if spy in refused:
                info[day] = {'status': 'refused', 'refused': {spy: refused[spy]}}
                continue
            if last is None or day > last:
                info[day] = {'status': 'not in files', 'note': f'after the stored files end ({last}) — fetch the chains first (--fetch-theta)'}
                continue
            if day < first:
                info[day] = {'status': 'not in files', 'note': f'before the stored files begin ({first})'}
                continue
            if not R.is_trading_day(day):
                info[day] = {'status': 'holiday'}
                continue
            if R.is_half_day(day):
                info[day] = {'status': 'half day'}
                continue
            # a day's manifest (a fetched session) refusing a file: FAILED / INCOMPLETE is never a session to read; nor is a
            # calendar session whose SPY file holds under 30 closes (a padded file) — that is not a holiday
            if day >= CAL_FROM and src.under_file('SPY', day).exists() and not src.is_session(day):
                info[day] = {'status': 'refused', 'refused': {spy: 'SPY\'s bars hold under 30 closes on a calendar session'}}
                continue
            missing, cands = [], []
            for c in all_cands:
                names = []
                for nm in c.names:
                    miss = [src.file_for(k, s, day).relative_to(src.root).as_posix() for k, s in needs(c, nm)
                            if not src.file_for(k, s, day).exists() or src.file_for(k, s, day).relative_to(src.root).as_posix() in refused]
                    if miss:
                        missing.append({'candidate': c.key, 'name': nm, 'files': miss})
                        bad = {m: refused[m] for m in miss if m in refused}
                        if bad:
                            missing[-1]['refused'] = bad
                    else:
                        names.append(nm)
                if names:
                    import dataclasses
                    cands.append(dataclasses.replace(c, names=tuple(names)))
            notes = []
            if any(c.key == 'condor_d20' for c in cands) and (not src.index_file('VIX', day).exists() or rel_of('index', 'VIX', day) in refused):
                notes.append('no VIX file: the no-VIX decile is the primary')
            if not cands:
                info[day] = {'status': 'missing files', 'missing': missing}
                continue
            tr.cands = tuple(cands)
            calls0 = client.calls
            for label, kind, when in T.events_for(day, tr.cands):
                clock.set(when)
                if kind == 'capture':
                    tr.capture(day, label, when)
                elif kind == 'close':
                    tr.close_quotes(day, when)
                else:
                    tr.settle(day, with_official=True)
            info[day] = {'status': 'replayed', 'candidates': [f'{c.key}:{"+".join(c.names)}' for c in cands], 'reads': client.calls - calls0}
            if settle_on == 'official':
                fb = sorted({f'{c.key} {nm}' for c in cands for nm in c.names
                             if (lambda d: d is not None and 'settle_source' in d.columns
                                 and d.filter(pl.col('settle_source') == P.FALLBACK_1559).height > 0)(store.read(c.key, nm, day))})
                if fb:
                    info[day]['settle_fallback'] = fb           # flagged: no official close on disk — settled on the 15:59 bar
                    notes.append('NO OFFICIAL CLOSE: ' + ', '.join(fb) + ' settled on the 15:59 bar (1559_bar)')
            if missing:
                info[day]['missing'] = missing
            if notes:
                info[day]['note'] = '; '.join(notes)
            n += 1
            if progress is not None and n % 25 == 0:
                print(f'replay {day}: {n} sessions in {time.time() - t0:.0f} s', file=progress, flush=True)
        tr.cands = all_cands
        write_days(store.root, start, end, info)
    finally:
        restore_calendar(saved)
    return {'days': len(days), 'replayed': sum(1 for v in info.values() if v['status'] == 'replayed'), 'seconds': round(time.time() - t0, 1),
            'root': str(Path(replay_root).resolve())}


# ---- reading the rows back ---------------------------------------------------------------------------------------------------------------

def read_rows(root: Path, keys: tuple, start: str, end: str) -> pl.DataFrame | None:
    frames = []
    for k in keys:
        cand = T.CANDIDATES[k]
        for nm in cand.names:
            d = Path(root) / k / nm
            for f in sorted(d.glob('*.parquet')) if d.is_dir() else []:
                if start <= f.stem <= end:
                    frames.append(pl.read_parquet(f))
    if not frames:
        return None
    df = pl.concat(frames, how='diagonal_relaxed')
    return df.filter(pl.col('source') == SOURCE) if 'source' in df.columns else df.head(0)


def fnum_col(df: pl.DataFrame, c: str) -> np.ndarray:
    if c not in df.columns:
        return np.full(df.height, np.nan)
    return df[c].cast(pl.Float64, strict=False).fill_null(float('nan')).to_numpy()


# ---- the statistics ---------------------------------------------------------------------------------------------------------------------

def session_boot(values: np.ndarray, days: np.ndarray, n: int = BOOT_N, seed: int = BOOT_SEED) -> tuple[float, float]:
    """95% interval of the mean by resampling sessions (a session's trades stay together)"""
    ok = np.isfinite(values)
    values, days = values[ok], days[ok]
    if values.size == 0:
        return float('nan'), float('nan')
    ud, inv = np.unique(days, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=ud.size)
    cnts = np.bincount(inv, minlength=ud.size).astype(float)
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, ud.size, (n, ud.size))
    means = sums[draw].sum(1) / np.maximum(cnts[draw].sum(1), 1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def cell(df: pl.DataFrame) -> dict:
    """The P&L block a group: settle rows (tradable, one per trade)"""
    days = df['_day'].to_numpy().astype(str)
    p = {k: fnum_col(df, f'pnl_{k}') for k in ('nbbo', 'mid', '1c', '2c')}
    risk = fnum_col(df, 'max_risk') * 100
    x = p['nbbo']
    n = int(np.isfinite(x).sum())
    out = {'trades': n, 'sessions': int(np.unique(days).size)}
    if n == 0:
        return out
    for k, v in p.items():
        out[f'mean_{k}'] = float(np.nanmean(v))
        out[f'median_{k}'] = float(np.nanmedian(v))
        out[f'total_{k}'] = float(np.nansum(v))
    win, loss = x > 0, x < 0
    ud, inv = np.unique(days, return_inverse=True)
    daysum = np.bincount(inv, weights=np.nan_to_num(x), minlength=ud.size)
    top5 = np.argsort(daysum)[-5:]
    keep = np.ones(ud.size, bool)
    keep[top5] = False
    gw, gl = x[win].sum(), -x[loss].sum()
    lo, hi = session_boot(x, days)
    mlo, mhi = session_boot(p['mid'], days)
    out.update({'win_rate': float(win.mean()), 'avg_win': float(x[win].mean()) if win.any() else float('nan'),
                'avg_loss': float(x[loss].mean()) if loss.any() else float('nan'), 'worst_trade': float(np.nanmin(x)),
                'worst_session': str(ud[np.argmin(daysum)]), 'worst_session_pnl': float(daysum.min()),
                'profit_factor': float(gw / gl) if gl > 0 else float('inf'), 'ci_lo_nbbo': lo, 'ci_hi_nbbo': hi,
                'ci_lo_mid': mlo, 'ci_hi_mid': mhi,
                'mean_wo_best5': float(x[keep[inv]].mean()) if keep[inv].any() else float('nan'),
                'mean_risk': float(np.nanmean(risk)), 'mean_pct_risk': float(np.nanmean(x / risk)) if np.isfinite(risk).any() else float('nan')})
    return out


def lift_d1(df: pl.DataFrame, col: str = 't2_decile_primary', minutes=('13:00', '13:30', '14:00', '14:30', '15:00')) -> dict:
    """Hypothesis E's time-matched lift: Σ_s N_D1(s)·[mean(D1 at s) − mean(all at s)] / Σ_s N_D1(s), $ and % of max risk,
    with a paired session bootstrap (2,000 draws, seed 20261016)"""
    if df.height == 0 or col not in df.columns:
        return {}
    days = df['_day'].to_numpy().astype(str)
    ud, inv = np.unique(days, return_inverse=True)
    mi = np.array([minutes.index(m) if m in minutes else -1 for m in df['minute'].to_list()])
    d1 = (df[col].cast(pl.Utf8) == '1').to_numpy()
    out = {}
    for unit, v in (('usd', fnum_col(df, 'pnl_nbbo')), ('pct', fnum_col(df, 'pnl_nbbo') / (fnum_col(df, 'max_risk') * 100))):
        ok = (mi >= 0) & np.isfinite(v)
        S = np.zeros((ud.size, len(minutes))); N = np.zeros_like(S); S1 = np.zeros_like(S); N1 = np.zeros_like(S)
        np.add.at(S, (inv[ok], mi[ok]), v[ok]); np.add.at(N, (inv[ok], mi[ok]), 1)
        k = ok & d1
        np.add.at(S1, (inv[k], mi[k]), v[k]); np.add.at(N1, (inv[k], mi[k]), 1)

        def lift(w):
            s, n, s1, n1 = w @ S, w @ N, w @ S1, w @ N1
            good = (n1 > 0) & (n > 0)
            if not good.any():
                return float('nan')
            return float((n1[good] * (s1[good] / n1[good] - s[good] / n[good])).sum() / n1[good].sum())
        point = lift(np.ones(ud.size))
        rng = np.random.default_rng(BOOT_SEED)
        draw = rng.integers(0, ud.size, (BOOT_N, ud.size))
        W = np.zeros((BOOT_N, ud.size))
        for b in range(BOOT_N):
            W[b] = np.bincount(draw[b], minlength=ud.size)
        bs = np.array([lift(W[b]) for b in range(BOOT_N)])
        bs = bs[np.isfinite(bs)]
        out[f'lift_{unit}'] = point
        out[f'lift_{unit}_lo'] = float(np.percentile(bs, 2.5)) if bs.size else float('nan')
        out[f'lift_{unit}_hi'] = float(np.percentile(bs, 97.5)) if bs.size else float('nan')
        out['n_d1'] = int((ok & d1).sum())
    return out


def leg_facts(caps: pl.DataFrame) -> dict:
    """The fill facts of tradable captures: the package's quoted width (Σ qty × (ask − bid) × 100), the NBBO-to-mid slip
    ($ a structure), and the share where every leg showed ≥ 1 contract on the side hit (a short's bid, a long's ask)"""
    if caps.height == 0:
        return {}
    width = np.zeros(caps.height)
    sized = np.ones(caps.height, bool)
    known = np.ones(caps.height, bool)
    for i in range(1, 5):
        if f'l{i}_symbol' not in caps.columns:
            continue
        has = caps[f'l{i}_symbol'].is_not_null().to_numpy()
        q = np.nan_to_num(fnum_col(caps, f'l{i}_qty'))
        b, a = fnum_col(caps, f'l{i}_bid'), fnum_col(caps, f'l{i}_ask')
        width += np.where(has, q * (a - b), 0.0)
        short = (caps[f'l{i}_side'] == 'short').fill_null(False).to_numpy()
        sz = np.where(short, fnum_col(caps, f'l{i}_bid_size'), fnum_col(caps, f'l{i}_ask_size'))
        known &= ~has | np.isfinite(sz)
        sized &= ~has | (np.nan_to_num(sz) >= 1)
    slip = np.abs(fnum_col(caps, 'price_nbbo') - fnum_col(caps, 'price_mid')) * 100
    return {'entries': caps.height, 'quoted_width_usd': float(np.mean(width) * 100), 'quoted_width_median_usd': float(np.median(width) * 100),
            'slip_usd': float(np.nanmean(slip)), 'slip_median_usd': float(np.nanmedian(slip)),
            'all_legs_sized_share': float(sized[known].mean()) if known.any() else float('nan'), 'sizes_known': int(known.sum())}


def reason_class(r: str | None) -> str:
    if not r:
        return ''
    return '; '.join(sorted({re.sub(r'-?\d+(\.\d+)?', '#', x.strip()) for x in r.split(';')}))


# ---- the report ----------------------------------------------------------------------------------------------------------------------------

def _f(x, fmt='{:+.2f}'):
    if isinstance(x, float) and x == float('inf'):
        return '∞ (no loss)'
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    return fmt.format(x)


def build_report(root: Path, keys: tuple, start: str, end: str, out_dir: Path, parquet_root: Path | None = None,
                 wall_seconds: float | None = None, stream=sys.stdout, settle_on: str | None = None,
                 closes: P.OfficialCloses | None = None, decision_prices: dict | None = None) -> dict:
    """The replay's report. `settle_on` (default: the root's own convention, else official): '1559' writes the report
    as it was before .2 (the committed reports, byte for byte); 'official' writes the audit's sections first — the
    settlement, every candidate by PERIOD (never pooled) on session sums with iid and 20-session block-bootstrap
    intervals, the 15:58 exit beside hold-to-expiry (the stress on the exit too), the expiry flags' shares, the
    after-hours cases — then the replay's detail tables (all periods together, for reconciliation), and a per-trade CSV
    (trades_<D1>_<D2>.csv) with every flag and the after-hours columns."""
    mode = settle_on or root_mode(root) or DEFAULT_SETTLE
    if mode == 'unreadable':
        mode = DEFAULT_SETTLE
    if mode == '1559':
        return _report(root, keys, start, end, out_dir, parquet_root, wall_seconds, stream)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    au = audit_sections(root, keys, start, end, parquet_root, closes, decision_prices)
    tp = out_dir / f'trades_{start}_{end}.csv'
    write_trades_csv(au['trades'], tp)
    res = _report(root, keys, start, end, out_dir, parquet_root, wall_seconds, stream, mode='official', extra=au)
    res['trades_csv'] = str(tp)
    res['audit'] = {k: v for k, v in au.items() if k not in ('md', 'csv', 'trades')}
    return res


def _report(root: Path, keys: tuple, start: str, end: str, out_dir: Path, parquet_root: Path | None = None,
            wall_seconds: float | None = None, stream=sys.stdout, mode: str = '1559', extra: dict | None = None) -> dict:
    """The replay's tables. mode '1559': the report before .2, unchanged (the reproduction of the committed reports);
    mode 'official': the same tables on the official-close settle rows (a '1559_bar' fallback counted, flagged), after
    `extra['md']` (the audit's sections) — and `extra['csv']` appended to the CSV"""
    root = Path(root)
    df = read_rows(root, keys, start, end)
    days_info = {d: v for d, v in read_days(root).items() if start <= d <= end}
    rows_csv: list = []
    md: list = []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f'{start}_{end}'
    st_counts: dict = {}
    for v in days_info.values():
        st_counts[v['status']] = st_counts.get(v['status'], 0) + 1
    official = mode == 'official'
    md.append(f'# Paper tracker — {"replay" if official else "historical replay"} {start} → {end}' + (' (official-close settlement)' if official else ''))
    md.append('')
    md.append(f'`{REPLAY_VERSION}` on `{T.VERSION}` ({T.RULES_VERSION}, {T.C3_RULES_VERSION}). Written {dt.datetime.now(R.UTC):%Y-%m-%d %H:%M} UTC'
              + (f'; this run took {wall_seconds:.0f} s (a minute already replayed into the root is skipped, so a resumed run is quick).' if wall_seconds else '.'))
    md.append('')
    if official:
        md.append('**What this is.** `paper_tracker.py --backtest` replays the stored 1-minute NBBO Parquet'
                  + (f' (`{parquet_root}`)' if parquet_root else '') + ' through the live tracker\'s own code (`Tracker.capture`, '
                  '`close_quotes` at 15:58 and `settle`, unchanged; each minute\'s rows adapted into the UW chain the live `Chain` '
                  'reads). Fills: shorts at the bid, longs at the ask; $0.65 a contract at the open, nothing at expiry; the 15:58 exit '
                  'pays $0.65 a contract closed (a long with no bid abandoned). **Spot** at a minute = the close of the bar stamped one '
                  'minute earlier. **The settlement is the official close** (the audit\'s correction, the default since '
                  f'`{REPLAY_VERSION}`): UW\'s daily bar (`r` row), else Theta\'s EOD daily bar; a session with neither settles on the '
                  '15:59 bar, labelled `1559_bar` and flagged below — never silently. SPXW on the last SPX print at or before 16:00. '
                  'The audit\'s other corrections are in every row and every table: the period (never pooled), session sums with '
                  'block-bootstrap intervals, the 15:58 exit for every candidate with the $0.01 / $0.02 stress at the open AND the exit, '
                  'the expiry flags (stock left, pins, the post-market cross) and the after-hours cases. Rows carry `source = '
                  'backtest-parquet` and live under their own root.')
    else:
        md.append('**What this is.** `paper_tracker.py --backtest` replays the stored 1-minute NBBO Parquet (the research\'s dataset'
                  + (f', `{parquet_root}`' if parquet_root else '') + ') through the live tracker\'s own code: each minute\'s rows are '
                  'adapted into the UW chain the live `Chain` reads, and `Tracker.capture`, `close_quotes` (15:58) and `settle` run '
                  'unchanged. Fills: shorts at the bid, longs at the ask; $0.65 a leg at the open, nothing at expiry; the 15:58 exit '
                  'pays $0.65 a contract closed. **Spot** at a minute = the close of the bar stamped one minute earlier. **The official '
                  'close** = the 15:59 bar\'s close for SPY and QQQ (the research\'s convention — the real closing print differs by '
                  'cents; the live tracker settles on UW\'s daily bar); SPXW on the last SPX print at or before 16:00. Rows carry '
                  '`source = backtest-parquet` and live under their own root, never the forward sample\'s.')
    md.append('')
    md.append(f'**Sessions**: {len(weekdays(start, end))} weekdays; ' + ', '.join(f'{v} {k}' for k, v in sorted(st_counts.items())) + '.')
    for kind in ('holiday', 'half day'):
        ds = sorted(d for d, v in days_info.items() if v['status'] == kind)
        if ds:
            md.append(f'- {kind.capitalize()}s skipped ({len(ds)}): {", ".join(ds)}')
    miss = sorted((d, v) for d, v in days_info.items() if v.get('missing'))
    if miss:
        md.append(f'- Days missing a file ({len(miss)}): ' + '; '.join(f'{d} ' + ', '.join(f'{m["candidate"]} {m["name"]}: {" ".join(m["files"])}' for m in v['missing']) for d, v in miss))
    ref = sorted(d for d, v in days_info.items() if v['status'] == 'refused' or any(m.get('refused') for m in v.get('missing', [])))
    if ref:
        md.append(f'- Refused by a fetch manifest ({len(ref)}): ' + '; '.join(f'{d} ' + json.dumps(days_info[d].get('refused') or [m['refused'] for m in days_info[d]['missing'] if m.get('refused')]) for d in ref))
    nif = sorted(d for d, v in days_info.items() if v['status'] == 'not in files')
    if nif:
        md.append(f'- Not in the stored files ({len(nif)}): {nif[0]} … {nif[-1]} — sessions after 2026-10-09 (the 12th onward) need '
                  'their chains fetched first (`--fetch-theta`, on the owner\'s machine), then a replay.')
    if parquet_root is not None:
        have = ParquetSource(parquet_root).days('SPY')
        if have and not official:
            nxt = next(d for d in weekdays(have[-1], (dt.date.fromisoformat(have[-1]) + dt.timedelta(days=7)).isoformat()) if d > have[-1])
            md.append(f'- The stored files end on {have[-1]}: sessions from {nxt} on (the 12th onward) are not in them and need their chains '
                      'fetched first — `paper_tracker.py --fetch-theta --start D1 --end D2 --parquet-root R` on the owner\'s machine '
                      '(the Theta Terminal running there), then `--backtest` over them.')
        elif have and end > have[-1]:
            md.append(f'- The stored files end on {have[-1]}: later sessions need their files fetched first (`scripts/daily_forward.py`, or '
                      '`paper_tracker.py --fetch-theta` on the owner\'s machine), then `--backtest` over them.')
    notes = sorted(d for d, v in days_info.items() if v.get('note') and v['status'] == 'replayed')
    if notes:
        md.append(f'- Replayed with a note ({len(notes)}): ' + '; '.join(f'{d} {days_info[d]["note"]}' for d in notes[:20]) + (' …' if len(notes) > 20 else ''))
    md.append('')
    if official and extra:
        md += extra['md']
        md.append('## Detail by candidate — every period together (reconciliation and detail, NOT a result: read the period tables above)')
        md.append('')
    if df is None or df.height == 0:
        md.append('No replay rows in this range.')
        (out_dir / f'backtest_{stamp}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
        pl.DataFrame({'section': []}).write_csv(out_dir / f'backtest_{stamp}.csv')
        return {'md': str(out_dir / f'backtest_{stamp}.md'), 'csv': str(out_dir / f'backtest_{stamp}.csv'), 'cells': []}
    caps = df.filter(pl.col('row_kind') == 'capture')
    sources = ['official', SPX_SETTLE] + ([P.FALLBACK_1559] if official else [])
    sett = df.filter((pl.col('row_kind') == 'settle') & pl.col('settle_source').is_in(sources) & (pl.col('tradable') == 'true'))
    sett = sett.with_columns(pl.col('_day').str.slice(0, 4).alias('year'), pl.col('_day').str.slice(0, 7).alias('month'))
    headline = []
    for k in keys:
        cand = T.CANDIDATES[k]
        md.append(f'## {k} — {cand.note}')
        md.append('')
        md.append(f'Minutes {", ".join(cand.minutes)} New York; names {", ".join(cand.names)}; rules `{cand.rules}`.')
        md.append('')
        md.append('| structure | sessions | trades | tradable share | mean NBBO | 95% CI (session bootstrap) | median | mean mid | mean +1c | mean +2c | total NBBO | win | avg win | avg loss | worst trade | worst session | PF | mean w/o best 5 sessions | mean max risk |')
        md.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for s in cand.structures:
            cs = caps.filter((pl.col('candidate') == k) & (pl.col('structure') == s))
            ss = sett.filter((pl.col('candidate') == k) & (pl.col('structure') == s))
            c = cell(ss)
            share = cs.filter(pl.col('tradable') == 'true').height / cs.height if cs.height else float('nan')
            r = {'section': 'cell', 'candidate': k, 'structure': s, 'cut': 'all', 'key': 'all', 'captures': cs.height, 'tradable_share': share, **c}
            rows_csv.append(r)
            headline.append(r)
            if c.get('trades'):
                md.append(f'| {s} | {c["sessions"]} | {c["trades"]} | {share:.1%} | {_f(c["mean_nbbo"])} | [{_f(c["ci_lo_nbbo"])}, {_f(c["ci_hi_nbbo"])}] | '
                          f'{_f(c["median_nbbo"])} | {_f(c["mean_mid"])} | {_f(c["mean_1c"])} | {_f(c["mean_2c"])} | {_f(c["total_nbbo"], "{:+,.0f}")} | '
                          f'{c["win_rate"]:.1%} | {_f(c["avg_win"])} | {_f(c["avg_loss"])} | {_f(c["worst_trade"])} | {c["worst_session"]} ({_f(c["worst_session_pnl"], "{:+,.0f}")}) | '
                          f'{_f(c["profit_factor"], "{:.2f}")} | {_f(c["mean_wo_best5"])} | ${c["mean_risk"]:.0f} |')
            else:
                md.append(f'| {s} | 0 | 0 | {share:.1%} | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |')
        md.append('')
        md.append('$ a structure (one lot, 100 shares a point), fees in. CI = 2,000 session-bootstrap draws, seed 20261016.')
        md.append('')
        # by name and by minute
        for cut, col in (('name', '_name'), ('minute', 'minute')):
            vals = sorted(set(sett.filter(pl.col('candidate') == k)[col].to_list()))
            if len(vals) <= 1 and cut == 'name':
                continue
            md.append(f'By {cut}:')
            md.append('')
            md.append(f'| structure | {cut} | sessions | trades | mean NBBO | 95% CI | mean mid | mean +2c | win | PF |')
            md.append('|---|---|---|---|---|---|---|---|---|---|')
            for s in cand.structures:
                for v in vals:
                    ss = sett.filter((pl.col('candidate') == k) & (pl.col('structure') == s) & (pl.col(col) == v))
                    cs = caps.filter((pl.col('candidate') == k) & (pl.col('structure') == s) & (pl.col(col) == v))
                    c = cell(ss)
                    share = cs.filter(pl.col('tradable') == 'true').height / cs.height if cs.height else float('nan')
                    rows_csv.append({'section': 'cell', 'candidate': k, 'structure': s, 'cut': cut, 'key': v, 'captures': cs.height, 'tradable_share': share, **c})
                    if c.get('trades'):
                        md.append(f'| {s} | {v} | {c["sessions"]} | {c["trades"]} | {_f(c["mean_nbbo"])} | [{_f(c["ci_lo_nbbo"])}, {_f(c["ci_hi_nbbo"])}] | '
                                  f'{_f(c["mean_mid"])} | {_f(c["mean_2c"])} | {c["win_rate"]:.1%} | {_f(c["profit_factor"], "{:.2f}")} |')
            md.append('')
        # by year and month
        years = sorted(set(sett.filter(pl.col('candidate') == k)['year'].to_list()))
        months = sorted(set(sett.filter(pl.col('candidate') == k)['month'].to_list()))
        md.append('By year (mean NBBO $ a structure, trades):')
        md.append('')
        md.append('| structure | ' + ' | '.join(years) + ' |')
        md.append('|---|' + '---|' * len(years))
        for s in cand.structures:
            cells = []
            for y in years:
                ss = sett.filter((pl.col('candidate') == k) & (pl.col('structure') == s) & (pl.col('year') == y))
                c = cell(ss)
                rows_csv.append({'section': 'cell', 'candidate': k, 'structure': s, 'cut': 'year', 'key': y, **c})
                cells.append(f'{_f(c.get("mean_nbbo"))} ({c.get("trades", 0)})')
            md.append(f'| {s} | ' + ' | '.join(cells) + ' |')
        md.append('')
        md.append('By month (mean NBBO $ a structure, trades):')
        md.append('')
        md.append('| month | ' + ' | '.join(cand.structures) + ' |')
        md.append('|---|' + '---|' * len(cand.structures))
        for mo in months:
            cells = []
            for s in cand.structures:
                ss = sett.filter((pl.col('candidate') == k) & (pl.col('structure') == s) & (pl.col('month') == mo))
                c = cell(ss)
                rows_csv.append({'section': 'cell', 'candidate': k, 'structure': s, 'cut': 'month', 'key': mo, **{x: c[x] for x in c if x in ('trades', 'sessions', 'mean_nbbo', 'mean_mid', 'total_nbbo', 'win_rate')}})
                cells.append(f'{_f(c.get("mean_nbbo"))} ({c.get("trades", 0)})')
            md.append(f'| {mo} | ' + ' | '.join(cells) + ' |')
        md.append('')
        # why untradable
        md.append('Untradable captures, by reason (the numbers in a reason replaced by #):')
        md.append('')
        md.append('| structure | captures | untradable | reason | count |')
        md.append('|---|---|---|---|---|')
        for s in cand.structures:
            cs = caps.filter((pl.col('candidate') == k) & (pl.col('structure') == s))
            un = cs.filter(pl.col('tradable') != 'true')
            if not un.height:
                md.append(f'| {s} | {cs.height} | 0 | — | — |')
                continue
            cnt: dict = {}
            for r_ in un['reason'].to_list():
                rc = reason_class(r_)
                cnt[rc] = cnt.get(rc, 0) + 1
            for i, (rc, n) in enumerate(sorted(cnt.items(), key=lambda x: -x[1])[:6]):
                md.append(f'| {s if i == 0 else ""} | {cs.height if i == 0 else ""} | {un.height if i == 0 else ""} | {rc} | {n} |')
                rows_csv.append({'section': 'untradable', 'candidate': k, 'structure': s, 'cut': 'reason', 'key': rc, 'trades': n})
        md.append('')
        # fill facts
        md.append('Fill facts (tradable entries): the package\'s quoted width (Σ qty × (ask − bid)), the NBBO-to-mid slip, and the '
                  'share of entries where every leg quoted ≥ 1 contract on the side hit (the Parquet carries Theta\'s sizes; UW\'s live route carries none).')
        md.append('')
        md.append('| structure | entries | quoted width $ (mean / median) | NBBO→mid slip $ (mean / median) | every leg ≥ 1 contract |')
        md.append('|---|---|---|---|---|')
        for s in cand.structures:
            cs = caps.filter((pl.col('candidate') == k) & (pl.col('structure') == s) & (pl.col('tradable') == 'true'))
            fx = leg_facts(cs)
            if fx:
                rows_csv.append({'section': 'fills', 'candidate': k, 'structure': s, 'cut': 'all', 'key': 'all', **fx})
                md.append(f'| {s} | {fx["entries"]} | {fx["quoted_width_usd"]:.2f} / {fx["quoted_width_median_usd"]:.2f} | {fx["slip_usd"]:.2f} / {fx["slip_median_usd"]:.2f} | '
                          f'{_f(fx["all_legs_sized_share"], "{:.1%}")} (of {fx["sizes_known"]}) |')
        md.append('')
        if k == 'condor_d20':
            ss = sett.filter((pl.col('candidate') == k) & (pl.col('structure') == 'condor'))
            md.append('Candidate 3 by its live t2 decile (the frozen models; primary = the full model when all four VIX features are there):')
            md.append('')
            md.append('| decile column | group | sessions | trades | mean NBBO | 95% CI | mean mid | win | PF |')
            md.append('|---|---|---|---|---|---|---|---|---|')
            for col in ('t2_decile_primary', 't2_decile_full', 't2_decile_novix'):
                if col not in ss.columns:
                    continue
                for g, flt in (('D1', pl.col(col) == '1'), ('D2–D10', pl.col(col).is_not_null() & (pl.col(col) != '1')), ('all', pl.lit(True))):
                    c = cell(ss.filter(flt))
                    rows_csv.append({'section': 'decile', 'candidate': k, 'structure': 'condor', 'cut': col, 'key': g, **c})
                    if c.get('trades'):
                        md.append(f'| {col} | {g} | {c["sessions"]} | {c["trades"]} | {_f(c["mean_nbbo"])} | [{_f(c["ci_lo_nbbo"])}, {_f(c["ci_hi_nbbo"])}] | '
                                  f'{_f(c["mean_mid"])} | {c["win_rate"]:.1%} | {_f(c["profit_factor"], "{:.2f}")} |')
                    else:
                        md.append(f'| {col} | {g} | 0 | 0 | — | — | — | — | — |')
            md.append('')
            prim = ss['t2_primary_model'].value_counts().sort('t2_primary_model').to_dicts() if 't2_primary_model' in ss.columns else []
            md.append('Primary model by row: ' + ', '.join(f'{d["t2_primary_model"]} {d["count"]}' for d in prim) + '.')
            md.append('')
            md.append('The time-matched lift of D1 (Hypothesis E §8: Σ_s N_D1(s)·[mean(D1 at s) − mean(all at s)] / Σ N_D1(s); paired '
                      'session bootstrap, 2,000 draws, seed 20261016):')
            md.append('')
            md.append('| decile column | D1 trades | lift $ | 95% CI $ | lift % of max risk | 95% CI % |')
            md.append('|---|---|---|---|---|---|')
            for col in ('t2_decile_primary', 't2_decile_full', 't2_decile_novix'):
                lf = lift_d1(ss, col)
                if lf:
                    rows_csv.append({'section': 'lift', 'candidate': k, 'structure': 'condor', 'cut': col, 'key': 'D1', **lf})
                    md.append(f'| {col} | {lf.get("n_d1", 0)} | {_f(lf["lift_usd"])} | [{_f(lf["lift_usd_lo"])}, {_f(lf["lift_usd_hi"])}] | '
                              f'{_f(lf["lift_pct"] * 100, "{:+.2f}%")} | [{_f(lf["lift_pct_lo"] * 100, "{:+.2f}")}, {_f(lf["lift_pct_hi"] * 100, "{:+.2f}")}] |')
            md.append('')
        if k == 'fly5':
            md.append('The 15:58 close-out against the 16:00 settlement (the same trades; the exit pays $0.65 a contract closed, a '
                      'long leg with no bid left to expire):')
            md.append('')
            md.append('| structure | name | trades with a 15:58 value | mean 16:00 NBBO | mean 15:58 NBBO | 15:58 − 16:00 (95% CI) | mean 15:58 mid | win 16:00 | win 15:58 |')
            md.append('|---|---|---|---|---|---|---|---|---|')
            for s in cand.structures:
                for nm in ['all'] + list(cand.names):
                    ss = sett.filter((pl.col('candidate') == k) & (pl.col('structure') == s))
                    if nm != 'all':
                        ss = ss.filter(pl.col('_name') == nm)
                    if 'pnl_1558_nbbo' not in ss.columns:
                        continue
                    ss = ss.filter(pl.col('pnl_1558_nbbo').is_not_null())
                    if not ss.height:
                        continue
                    a, b = fnum_col(ss, 'pnl_nbbo'), fnum_col(ss, 'pnl_1558_nbbo')
                    days = ss['_day'].to_numpy().astype(str)
                    lo, hi = session_boot(b - a, days)
                    r = {'section': '1558', 'candidate': k, 'structure': s, 'cut': 'name', 'key': nm, 'trades': ss.height, 'mean_1600_nbbo': float(a.mean()),
                         'mean_1558_nbbo': float(b.mean()), 'diff': float((b - a).mean()), 'diff_lo': lo, 'diff_hi': hi,
                         'mean_1558_mid': float(np.nanmean(fnum_col(ss, 'pnl_1558_mid'))), 'win_1600': float((a > 0).mean()), 'win_1558': float((b > 0).mean())}
                    rows_csv.append(r)
                    md.append(f'| {s} | {nm} | {r["trades"]} | {_f(r["mean_1600_nbbo"])} | {_f(r["mean_1558_nbbo"])} | {_f(r["diff"])} [{_f(lo)}, {_f(hi)}] | '
                              f'{_f(r["mean_1558_mid"])} | {r["win_1600"]:.1%} | {r["win_1558"]:.1%} |')
            md.append('')
    if official and extra:
        rows_csv += extra['csv']
    mdp, csvp = out_dir / f'backtest_{stamp}.md', out_dir / f'backtest_{stamp}.csv'
    mdp.write_text('\n'.join(md) + '\n', encoding='utf-8')
    tab = pl.DataFrame([{kk: (None if isinstance(vv, float) and not math.isfinite(vv) else vv) for kk, vv in r.items()} for r in rows_csv], infer_schema_length=None)
    tab.write_csv(csvp)
    if stream is not None:
        print(f'\nbacktest {start} → {end}: {st_counts.get("replayed", 0)} sessions replayed  ({mdp})', file=stream)
        for r in headline:
            if r.get('trades'):
                print(f'  {r["candidate"]:<10} {r["structure"]:<7} sessions {r["sessions"]:>4} trades {r["trades"]:>5} tradable {r["tradable_share"]:.0%}  '
                      f'mean $ NBBO {r["mean_nbbo"]:+7.2f} [{r["ci_lo_nbbo"]:+.2f}, {r["ci_hi_nbbo"]:+.2f}]  mid {r["mean_mid"]:+7.2f}  +1c {r["mean_1c"]:+7.2f}  '
                      f'+2c {r["mean_2c"]:+7.2f}  win {r["win_rate"]:.0%}  PF {r["profit_factor"]:.2f}  total {r["total_nbbo"]:+,.0f}', file=stream)
            else:
                print(f'  {r["candidate"]:<10} {r["structure"]:<7} no tradable trade ({r["captures"]} captures)', file=stream)
    return {'md': str(mdp), 'csv': str(csvp), 'cells': headline}


# ---- the audit's sections (the official-close report and the cumulative forward report) -----------------------------------------

STRUCT_LABEL = {('condor_em1', 'condor'): 'condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30)',
                ('fly5', 'iron'): 'fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30)', ('fly5', 'call'): 'fly5 long call ±5',
                ('fly5', 'put'): 'fly5 long put ±5', ('condor_d20', 'condor'): 'condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00)'}
SETTLE_RANK = {'official': 0, SPX_SETTLE: 0, P.FALLBACK_1559: 1}


def label_of(k: str, s: str) -> str:
    return STRUCT_LABEL.get((k, s), f'{k} {s}')


def next_session_open(src: ParquetSource | None, closes: P.OfficialCloses, name: str, day: str) -> tuple[float | None, str | None, str | None]:
    """The next session's 09:30 open: the open of its 09:30 bar in the stored Parquet, else UW's daily `r` open of the
    next calendar session. (price, the next session, source) — (None, …) until the next session's data is on disk"""
    if src is not None:
        import bisect
        ds = src.days(name)
        for nd in ds[bisect.bisect_right(ds, day):bisect.bisect_right(ds, day) + 6]:
            b = src.bars(name, nd)
            if not b or len(b['j']) < 30:
                continue                            # a holiday's padded file (Thanksgiving 2025-11-27 is one) is no session
            if b['j'][0] == 0 and b['o'][0] is not None:
                return float(b['o'][0]), nd, 'parquet: the 09:30 bar\'s open'
            break
    d = dt.date.fromisoformat(day)
    for _ in range(10):
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and R.is_trading_day(d.isoformat()):
            o = closes.open_r(name, d.isoformat())
            return (o, d.isoformat(), 'uw_1d r open') if o is not None else (None, d.isoformat(), None)
    return None, None, None


def trade_table(df: pl.DataFrame | None, closes: P.OfficialCloses | None = None, parquet_root: Path | None = None,
                decision_prices: dict | None = None, only_days: set | None = None) -> tuple[list, int]:
    """One dict a settled trade (a tradable capture and its settle row — the official close preferred over a 1559_bar
    fallback): the P&Ls held and at 15:58 (stressed too), the period, the expiry flags at the settlement price with the
    post-market range read from disk NOW (a later fetch carries the whole evening), and the after-hours cases with the
    next 09:30 open and the decision price where they exist. → (trades, tradable captures with no settle row)"""
    if df is None or df.height == 0:
        return [], 0
    closes = closes if closes is not None else P.OfficialCloses()
    src = ParquetSource(parquet_root) if parquet_root else None
    if decision_prices is None:                     # the study's rule on every UW 1-minute answer on disk
        decision_prices = P.decision_prices_on_disk(extra_dirs=uw_1m_dirs())
    k5 = ('candidate', '_name', '_day', 'minute', 'structure')
    caps = df.filter((pl.col('row_kind') == 'capture') & (pl.col('tradable') == 'true') & pl.col('l1_symbol').is_not_null())
    sett = df.filter((pl.col('row_kind') == 'settle') & pl.col('settle_source').is_in(list(SETTLE_RANK)))
    if only_days is not None:
        caps = caps.filter(pl.col('_day').is_in(sorted(only_days)))
        sett = sett.filter(pl.col('_day').is_in(sorted(only_days)))
    sett = sett.with_columns(pl.col('settle_source').replace_strict(SETTLE_RANK, default=9).alias('_rank'))
    sett = sett.sort(list(k5) + ['_rank']).unique(subset=list(k5), keep='first', maintain_order=True)
    S = {tuple(r[k] for k in k5): r for r in sett.to_dicts()}
    out, unsettled = [], 0
    nf = T.fnum
    for c in caps.sort(list(k5)).to_dicts():
        s = S.get(tuple(c[k] for k in k5))
        st = T.structure_from_row(c)
        if s is None or st is None or nf(s.get('settle_px')) is None:
            unsettled += 1
            continue
        k, name, day = c['candidate'], c['_name'], c['_day']
        px = nf(s['settle_px'])
        cash = k == 'fly_spxw'
        lo, hi, pm_src = (None, None, 'cash-settled: no delivery') if cash else closes.post_market(name, day)
        fl = P.flags(st, px, lo, hi, cash_settled=cash)
        nxt, nday, nsrc = (None, None, None) if cash else next_session_open(src, closes, name, day)
        dp = decision_prices.get((name, day))
        is_off = s['settle_source'] == 'official'
        ah = P.after_hours_pnl(st, st.entry_cash(), px, nxt, dp, cash_settled=cash) if (is_off or cash) else \
            {'pnl_ah0': None, 'pnl_ah_a': None, 'pnl_ah_b': None, 'pnl_ah_c': None}
        t = {'candidate': k, 'name': name, 'day': day, 'minute': c['minute'], 'structure': c['structure'],
             'period': P.period_of(k, day), 'settle_source': s['settle_source'], 'settle_from': s.get('close_official_from'),
             'settle_fallback': s['settle_source'] == P.FALLBACK_1559, 'settle_px': px, 'close_1559': nf(s.get('close_1m_r')),
             'price_nbbo': nf(c.get('price_nbbo')), 'max_risk': nf(c.get('max_risk')),
             'risk_usd': None if nf(c.get('max_risk')) is None else nf(c.get('max_risk')) * 100,
             **{f'pnl_{x}': nf(s.get(f'pnl_{x}')) for x in ('nbbo', 'mid', '1c', '2c')},
             **{f'pnl_1558_{x}': nf(s.get(f'pnl_1558_{x}')) for x in ('nbbo', 'mid', '1c', '2c')},
             'legs_closed_1558': nf(s.get('legs_closed')),
             'stock_left': fl['stock_left'], 'stock_left_side': fl['stock_left_side'],
             'stock_value': None if fl['stock_left'] is None else abs(fl['stock_left']) * px,
             'pin_dist': fl['pin_dist'], 'pin_025': fl['pin_025'], 'pin_050': fl['pin_050'],
             'pm_low': lo, 'pm_high': hi, 'pm_cross': fl['pm_cross'], 'pm_source': pm_src,
             'next_day': nday, 'next_open': nxt, 'next_open_source': nsrc, 'decision_price': dp, **ah,
             't2_decile_primary': c.get('t2_decile_primary')}
        out.append(t)
    return out, unsettled


TRADE_COLUMNS = ('candidate', 'name', 'day', 'minute', 'structure', 'period', 'settle_source', 'settle_from', 'settle_fallback', 'settle_px',
                 'close_1559', 'price_nbbo', 'max_risk', 'pnl_nbbo', 'pnl_mid', 'pnl_1c', 'pnl_2c', 'pnl_1558_nbbo', 'pnl_1558_mid',
                 'pnl_1558_1c', 'pnl_1558_2c', 'legs_closed_1558', 'stock_left', 'stock_left_side', 'stock_value', 'pin_dist', 'pin_025',
                 'pin_050', 'pm_low', 'pm_high', 'pm_cross', 'pm_source', 'next_day', 'next_open', 'next_open_source', 'decision_price',
                 'pnl_ah0', 'pnl_ah_a', 'pnl_ah_b', 'pnl_ah_c', 't2_decile_primary')


def write_trades_csv(trades: list, path: Path) -> None:
    rows = [{c: (None if isinstance(t.get(c), float) and not math.isfinite(t[c]) else t.get(c)) for c in TRADE_COLUMNS} for t in trades]
    schema = {c: (pl.Boolean if c in ('settle_fallback', 'pin_025', 'pin_050', 'pm_cross') else
                  pl.Int64 if c == 'stock_left' else
                  pl.Utf8 if c in ('candidate', 'name', 'day', 'minute', 'structure', 'period', 'settle_source', 'settle_from', 'stock_left_side',
                                   'pm_source', 'next_day', 'next_open_source', 't2_decile_primary') else pl.Float64) for c in TRADE_COLUMNS}
    pl.DataFrame(rows, schema=schema).write_csv(path)


def candidate_sessions(days_info: dict, key: str, only_days: set | None = None) -> list[str]:
    """the replayed sessions the candidate ran (zero where it took no trade), in calendar order"""
    out = []
    for d, v in sorted(days_info.items()):
        if v.get('status') != 'replayed' or (only_days is not None and d not in only_days):
            continue
        if any(str(x).split(':')[0] == key for x in v.get('candidates', [])):
            out.append(d)
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None and isinstance(x, (int, float)) and math.isfinite(x)]
    return (float(np.mean(xs)) if xs else float('nan')), len(xs)


def _share(xs):
    xs = [x for x in xs if x is not None]
    return (sum(1 for x in xs if x) / len(xs)) if xs else float('nan'), len(xs)


def _ci(t, fmt='{:+.2f}'):
    if not t or any((v is None or not math.isfinite(v)) for v in t):
        return '—'
    return f'[{fmt.format(t[0])}, {fmt.format(t[1])}]'


def _pct(x, d=1):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{100 * x:.{d}f}%'


def audit_sections(root: Path, keys: tuple, start: str, end: str, parquet_root: Path | None = None, closes: P.OfficialCloses | None = None,
                   decision_prices: dict | None = None, only_days: set | None = None, df: pl.DataFrame | None = None) -> dict:
    """The audit's corrections as report sections: {'md': lines, 'csv': rows, 'trades': per-trade dicts, 'unsettled': n,
    'fallback_sessions': [...]}. Every statistic is by candidate · structure · PERIOD (paper_audit.period_of), never
    pooled across periods; inference on SESSION sums (every session the candidate ran, zero where it took no trade) by
    the iid-session and 20-session moving-block bootstraps (paper_audit.session_stats — audit_lib's, 2,000 draws, seed
    20261022)."""
    closes = closes if closes is not None else P.OfficialCloses()
    df = read_rows(root, keys, start, end) if df is None else df
    days_info = {d: v for d, v in read_days(root).items() if start <= d <= end}
    trades, unsettled = trade_table(df, closes, parquet_root, decision_prices, only_days)
    md: list = []
    csv: list = []
    # -- the settlement
    md.append('## Settlement: the official close')
    md.append('')
    md.append('The options settle (and are auto-exercised) on the primary listing\'s official closing price, not the 15:59 bar. Each '
              'name-session\'s settlement source:')
    md.append('')
    md.append('| name | sessions settled | official close (source) | 15:59 bar fallback (flagged) | official − 15:59 bar: mean / max |abs| | sessions where they differ by > $0.05 |')
    md.append('|---|---|---|---|---|---|')
    sess_src: dict = {}
    for t in trades:
        sess_src.setdefault((t['name'], t['day']), (t['settle_source'], t['settle_from'], t['settle_px'], t['close_1559']))
    fallback = sorted({f'{d} {nm}' for (nm, d), v in sess_src.items() if v[0] == P.FALLBACK_1559})
    for nm in sorted({nm for nm, _ in sess_src}):
        vs = [v for (n_, _), v in sess_src.items() if n_ == nm]
        offs = [v for v in vs if v[0] == 'official']
        by = {}
        for v in offs:
            lab = (v[1] or '').replace('replay: official close (', '').rstrip(')') or 'official'
            by[lab] = by.get(lab, 0) + 1
        dd = np.array([v[2] - v[3] for v in offs if v[3] is not None])
        md.append(f'| {nm} | {len(vs)} | {len(offs)} ({", ".join(f"{k} {n}" for k, n in sorted(by.items()))}) | {sum(1 for v in vs if v[0] == P.FALLBACK_1559)} | '
                  + (f'{np.mean(np.abs(dd)):.3f} / {np.max(np.abs(dd)):.2f} | {int((np.abs(dd) > 0.05).sum())} |' if dd.size else '— | — |'))
        csv.append({'section': 'settlement', 'candidate': 'all', 'structure': 'all', 'cut': 'name', 'key': nm, 'sessions': len(vs),
                    'official': len(offs), 'fallback_1559': sum(1 for v in vs if v[0] == P.FALLBACK_1559),
                    'official_sources': json.dumps(by, sort_keys=True), 'mean_abs_off_minus_1559': float(np.mean(np.abs(dd))) if dd.size else None})
    md.append('')
    md.append(('**Flagged — settled on the 15:59 bar (`1559_bar`), no official close on disk:** ' + ', '.join(fallback)) if fallback
              else 'No session fell back to the 15:59 bar.')
    if unsettled:
        md.append(f'\nTradable captures with no settle row: {unsettled}.')
    md.append('')
    # -- by period
    md.append('## Results by period — never pooled')
    md.append('')
    md.append('Official close, every leg at its own NBBO, $0.65 a contract at the open, nothing at expiry, one lot. A session\'s P&L is the sum '
              'of its trades (zero on a session the candidate ran and took no trade); intervals are percentile bootstraps over SESSIONS — '
              'iid and moving blocks of 20 consecutive sessions (2,000 draws, seeded; a block interval needs 60 sessions). fly5\'s three '
              'structures are one trade seen three ways; read them as one bet.')
    md.append('')
    for k in keys:
        if k not in T.CANDIDATES:
            continue
        cand = T.CANDIDATES[k]
        sessions = candidate_sessions(days_info, k, only_days)
        pers = sorted({P.period_of(k, d) for d in sessions}, key=P.period_sort)
        if not pers:
            continue
        md.append(f'### {k}')
        md.append('')
        for code in pers:
            md.append(f'- **{code}** — {P.period_label(k, code)}')
        md.append('')
        md.append('| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |')
        md.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for s in cand.structures:
            for code in pers:
                days = [d for d in sessions if P.period_of(k, d) == code]
                xs = [t for t in trades if t['candidate'] == k and t['structure'] == s and t['period'] == code]
                Sv, Nv = P.session_series(days, [t['day'] for t in xs], [t['pnl_nbbo'] for t in xs])
                stt = P.session_stats(Sv, Nv)
                vals = [t['pnl_nbbo'] for t in xs if t['pnl_nbbo'] is not None]
                pct_ = [t['pnl_nbbo'] / t['risk_usd'] for t in xs if t['pnl_nbbo'] is not None and t['risk_usd']]
                row = {'section': 'period', 'candidate': k, 'structure': s, 'cut': 'period', 'key': code, 'sessions': stt['sessions'],
                       'trades': stt['trades'], 'sessions_traded': stt['sessions_traded'], 'mean_nbbo': stt.get('mean_trade'),
                       'mean_session': stt.get('mean_session'), 'total_nbbo': float(np.sum(vals)) if vals else 0.0,
                       'win_rate': float(np.mean(np.array(vals) > 0)) if vals else None, 'mean_pct_risk': float(np.mean(pct_)) if pct_ else None,
                       'max_drawdown': P.drawdown(Sv[Nv > 0]) if Nv.sum() else None}
                for b in (1, 5, 20):
                    for what in ('session', 'trade'):
                        lo_hi = stt.get(f'ci_{what}_b{b}', (float('nan'), float('nan')))
                        row[f'ci_{what}_b{b}_lo'], row[f'ci_{what}_b{b}_hi'] = lo_hi
                csv.append(row)
                if not stt['trades']:
                    md.append(f'| {s} | {code} | {stt["sessions"]} | 0 | 0 / {stt["sessions"]} | — | — | — | — | — | — | — | — | — |')
                    continue
                md.append(f'| {s} | {code} | {stt["sessions"]} | {stt["trades"]} | {stt["sessions_traded"]} / {stt["sessions"]} | {_f(stt["mean_trade"])} | '
                          f'{_ci(stt.get("ci_trade_b20"))} | {_pct(row["mean_pct_risk"], 2)} | {_f(stt["mean_session"])} | {_ci(stt.get("ci_session_b1"))} | '
                          f'{_ci(stt.get("ci_session_b20"))} | {_f(row["total_nbbo"], "{:+,.0f}")} | {_pct(row["win_rate"])} | {_f(row["max_drawdown"], "{:,.0f}")} |')
        md.append('')
    # -- the 15:58 exit beside hold-to-expiry
    md.append('## Hold to expiry against the 15:58 exit')
    md.append('')
    md.append('The same trades, $ a structure. The 15:58 exit (the tracker\'s `close_quotes`, every candidate): a long sold at its bid, a short '
              'bought back at its ask, $0.65 a contract closed, a long with no bid abandoned (no fee); the stressed columns move every contract '
              '$0.01 / $0.02 against us at the open AND at the exit. Holding to expiry leaves stock on most in-the-money trades (the flags below); '
              'the 15:58 exit is the one a cash account can take.')
    md.append('')
    md.append('| candidate · structure | period | trades | hold NBBO | hold +$0.01 | hold +$0.02 | hold at mids | 15:58 trades | 15:58 NBBO | 15:58 +$0.01 open & close | 15:58 +$0.02 open & close | 15:58 at mids | 15:58 NBBO: block-20 CI (trade) |')
    md.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k in keys:
        if k not in T.CANDIDATES:
            continue
        sessions = candidate_sessions(days_info, k, only_days)
        for s in T.CANDIDATES[k].structures:
            for code in sorted({P.period_of(k, d) for d in sessions}, key=P.period_sort):
                xs = [t for t in trades if t['candidate'] == k and t['structure'] == s and t['period'] == code]
                if not xs:
                    continue
                days = [d for d in sessions if P.period_of(k, d) == code]
                ex = [t for t in xs if t['pnl_1558_nbbo'] is not None]
                Se, Ne = P.session_series(days, [t['day'] for t in ex], [t['pnl_1558_nbbo'] for t in ex])
                se = P.session_stats(Se, Ne, blocks=(20,))
                m = {c: _mean([t[c] for t in xs])[0] for c in ('pnl_nbbo', 'pnl_1c', 'pnl_2c', 'pnl_mid')}
                e = {c: _mean([t[c] for t in xs]) for c in ('pnl_1558_nbbo', 'pnl_1558_1c', 'pnl_1558_2c', 'pnl_1558_mid')}
                row = {'section': 'exit1558', 'candidate': k, 'structure': s, 'cut': 'period', 'key': code, 'trades': len(xs),
                       'hold_nbbo': m['pnl_nbbo'], 'hold_1c': m['pnl_1c'], 'hold_2c': m['pnl_2c'], 'hold_mid': m['pnl_mid'],
                       'exit_trades': len(ex), 'exit_nbbo': e['pnl_1558_nbbo'][0], 'exit_1c': e['pnl_1558_1c'][0], 'exit_2c': e['pnl_1558_2c'][0],
                       'exit_mid': e['pnl_1558_mid'][0]}
                row['exit_ci_trade_b20_lo'], row['exit_ci_trade_b20_hi'] = se.get('ci_trade_b20', (float('nan'), float('nan')))
                csv.append(row)
                md.append(f'| {label_of(k, s)} | {code} | {len(xs)} | {_f(m["pnl_nbbo"])} | {_f(m["pnl_1c"])} | {_f(m["pnl_2c"])} | {_f(m["pnl_mid"])} | '
                          f'{len(ex)} | {_f(row["exit_nbbo"])} | {_f(row["exit_1c"])} | {_f(row["exit_2c"])} | {_f(row["exit_mid"])} | {_ci(se.get("ci_trade_b20"))} |')
    md.append('')
    # -- the flags
    md.append('## Expiry flags (held to the official close)')
    md.append('')
    md.append('SPY and QQQ options are American and physically settled: OCC exercises every option in the money by $0.01 or more at the '
              'official close unless told otherwise, so a structure held to the close can leave shares (`stock_left`: the net of the '
              'exercises and assignments, by sign) — a 100-share position per lot against a few hundred dollars of modeled risk. The pins: '
              'the official close within $0.25 / $0.50 of a short strike (the writer does not know at 16:00 whether he is assigned). The '
              'post-market cross: UW\'s post-market bar (16:00–20:00, read from disk now — the window to the exercise cut-off is shorter, '
              'so an upper bound) took a short strike across the money; known only where that bar is on disk.')
    md.append('')
    md.append('| candidate · structure | period | trades | stock left (long / short) | mean / max stock left $ | pin ≤ $0.25 | pin ≤ $0.50 | post-market cross (of trades with the bar) | settled on the 15:59 bar (flagged) |')
    md.append('|---|---|---|---|---|---|---|---|---|')
    for k in keys:
        if k not in T.CANDIDATES:
            continue
        sessions = candidate_sessions(days_info, k, only_days)
        for s in T.CANDIDATES[k].structures:
            for code in sorted({P.period_of(k, d) for d in sessions}, key=P.period_sort):
                xs = [t for t in trades if t['candidate'] == k and t['structure'] == s and t['period'] == code]
                if not xs:
                    continue
                n = len(xs)
                left = [t for t in xs if t['stock_left']]
                sl, _ = _share([bool(t['stock_left']) if t['stock_left'] is not None else None for t in xs])
                lg = sum(1 for t in xs if (t['stock_left'] or 0) > 0) / n
                sh = sum(1 for t in xs if (t['stock_left'] or 0) < 0) / n
                p25, _ = _share([t['pin_025'] for t in xs])
                p50, _ = _share([t['pin_050'] for t in xs])
                pmc, pmn = _share([t['pm_cross'] for t in xs])
                fb = sum(1 for t in xs if t['settle_fallback'])
                vals = [t['stock_value'] for t in left if t['stock_value'] is not None]
                row = {'section': 'flags', 'candidate': k, 'structure': s, 'cut': 'period', 'key': code, 'trades': n, 'stock_left_share': sl,
                       'stock_long_share': lg, 'stock_short_share': sh, 'stock_value_mean': float(np.mean(vals)) if vals else None,
                       'stock_value_max': float(np.max(vals)) if vals else None, 'pin_025_share': p25, 'pin_050_share': p50,
                       'pm_cross_share': pmc, 'pm_known': pmn, 'settle_fallback': fb}
                csv.append(row)
                md.append(f'| {label_of(k, s)} | {code} | {n} | {_pct(sl)} ({_pct(lg)} / {_pct(sh)}) | '
                          + (f'${np.mean(vals):,.0f} / ${np.max(vals):,.0f}' if vals else '—') + f' | {_pct(p25)} | {_pct(p50)} | '
                          + (f'{_pct(pmc)} of {pmn}' if pmn else '— (no post-market bar on disk)') + f' | {fb} |')
    md.append('')
    # -- after hours
    md.append('## After the close: the four expiry cases (the after-hours study\'s hook)')
    md.append('')
    md.append('`paper_audit.after_hours_pnl`, $ a structure, on the official-close trades: **0** hold at intrinsic (the settle P&L); **a** OCC\'s default '
              'at the official close (every leg in the money by ≥ $0.01 exercised or assigned), the net stock marked at the next session\'s '
              '09:30 open; **b** our shorts assigned iff in the money at the decision price, our longs by default; **c** both sides at the '
              'decision price. The decision price is the close of the last UW post-market 1-minute bar ending at or before 17:30 New York (the after-hours '
              'study\'s rule, `paper_audit.decision_of`, read off the UW 1-minute answers on disk — data/postmarket_1m, which the daily '
              'job fills); every stock position marked at the next session\'s 09:30 bar open. No exercise or assignment fee (a parameter, '
              'default 0). a needs the next open (filled once the next session is on disk — the next daily run); b and c also need '
              'the decision price; without them they are —.')
    md.append('')
    md.append('| candidate · structure | period | official trades | with the next open | case 0 | case a | with a decision price too | case 0 | case a | case b | case c |')
    md.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for k in keys:
        if k not in T.CANDIDATES:
            continue
        sessions = candidate_sessions(days_info, k, only_days)
        for s in T.CANDIDATES[k].structures:
            for code in sorted({P.period_of(k, d) for d in sessions}, key=P.period_sort):
                xs = [t for t in trades if t['candidate'] == k and t['structure'] == s and t['period'] == code and t['pnl_ah0'] is not None]
                if not xs:
                    continue
                wa = [t for t in xs if t['pnl_ah_a'] is not None]
                wb = [t for t in xs if t['pnl_ah_b'] is not None]
                row = {'section': 'afterhours', 'candidate': k, 'structure': s, 'cut': 'period', 'key': code, 'trades': len(xs), 'with_open': len(wa),
                       'case0_same': _mean([t['pnl_ah0'] for t in wa])[0], 'case_a': _mean([t['pnl_ah_a'] for t in wa])[0],
                       'with_decision': len(wb), 'case0_b': _mean([t['pnl_ah0'] for t in wb])[0], 'case_a_b': _mean([t['pnl_ah_a'] for t in wb])[0],
                       'case_b': _mean([t['pnl_ah_b'] for t in wb])[0], 'case_c': _mean([t['pnl_ah_c'] for t in wb])[0]}
                csv.append(row)
                md.append(f'| {label_of(k, s)} | {code} | {len(xs)} | {len(wa)} | {_f(row["case0_same"])} | {_f(row["case_a"])} | {len(wb)} | '
                          f'{_f(row["case0_b"])} | {_f(row["case_a_b"])} | {_f(row["case_b"])} | {_f(row["case_c"])} |')
    md.append('')
    return {'md': md, 'csv': csv, 'trades': trades, 'unsettled': unsettled, 'fallback_sessions': fallback}


# ---- the cumulative report: append the newest forward sessions, the history untouched ------------------------------------------

CUM_HIST_BEGIN, CUM_HIST_END = '<!-- cumulative:historical:begin -->', '<!-- cumulative:historical:end -->'
CUM_FWD_BEGIN, CUM_FWD_END = '<!-- cumulative:forward:begin -->', '<!-- cumulative:forward:end -->'
CUM_STATE = '<!-- cumulative:forward-sessions '


def complete_sessions(root: Path, keys: tuple, start: str, end: str) -> tuple[list, dict]:
    """The forward sessions whole enough to append: replayed with no file missing, every tradable capture settled on the
    official close (an SPXW proxy for fly_spxw) — a session with a 15:59-bar fallback, a missing file or an unsettled
    capture is PENDING (with why), never appended. → (complete days, {day: why})"""
    info = {d: v for d, v in read_days(root).items() if start <= d <= end}
    df = read_rows(root, keys, start, end)
    done, pend = [], {}
    for d, v in sorted(info.items()):
        if v.get('status') != 'replayed':
            if v.get('status') not in ('holiday', 'half day', 'weekend'):
                pend[d] = f'not replayed: {v.get("status")}'
            continue
        if v.get('missing'):
            pend[d] = 'a file missing: ' + '; '.join(f'{m["candidate"]} {m["name"]}' for m in v['missing'])
            continue
        if v.get('settle_fallback'):
            pend[d] = 'no official close yet (settled on the 15:59 bar): ' + ', '.join(v['settle_fallback'])
            continue
        ran = {str(x).split(':')[0] for x in v.get('candidates', [])}
        if not ran >= {k for k in keys if k in T.CANDIDATES and not T.CANDIDATES[k].optional}:
            pend[d] = f'not every candidate ran: {sorted(ran)}'
            continue
        x = df.filter(pl.col('_day') == d) if df is not None else None
        if x is None or x.height == 0:
            pend[d] = 'no rows'
            continue
        have = {(a, b) for a, b in x.filter(pl.col('row_kind') == 'capture').select('candidate', '_name').unique().iter_rows()}
        gone = [f'{k} {nm}' for k_nm in v.get('candidates', []) for k, names in [str(k_nm).split(':')] if k in keys
                for nm in names.split('+') if (k, nm) not in have]
        if gone:
            pend[d] = 'the day file says these ran but their rows are not in the root: ' + ', '.join(gone)
            continue
        caps = x.filter((pl.col('row_kind') == 'capture') & (pl.col('tradable') == 'true') & pl.col('l1_symbol').is_not_null())
        st = x.filter((pl.col('row_kind') == 'settle') & pl.col('settle_source').is_in(['official', SPX_SETTLE]))
        k5 = ['candidate', '_name', 'minute', 'structure']
        miss = caps.select(k5).join(st.select(k5).unique(), on=k5, how='anti').height
        if miss:
            pend[d] = f'{miss} tradable captures without an official settle row'
            continue
        done.append(d)
    return done, pend


def _cum_parse(text: str) -> tuple[int, int, list]:
    for m in (CUM_HIST_BEGIN, CUM_HIST_END, CUM_FWD_BEGIN, CUM_FWD_END):
        if text.count(m) != 1:
            raise ValueError(f'the cumulative report must hold {m} exactly once (found {text.count(m)})')
    a, b = text.index(CUM_FWD_BEGIN) + len(CUM_FWD_BEGIN), text.index(CUM_FWD_END)
    if not (text.index(CUM_HIST_END) < a):
        raise ValueError('the forward block must follow the historical block')
    block = text[a:b]
    listed: list = []
    if CUM_STATE in block:
        j = block.index(CUM_STATE) + len(CUM_STATE)
        listed = json.loads(block[j:block.index('-->', j)].strip())
    return a, b, listed


def init_cumulative(path: Path, historical: str | None = None, title: str = 'Paper tracker — cumulative report') -> None:
    """A new cumulative report: the historical block (`historical`: e.g. the official-close replay report of
    2022-11-11 → 2026-10-09, embedded verbatim) and an empty forward block"""
    path = Path(path)
    hist = (historical or '_The historical sections: none embedded. The official-close replay of the research\'s span goes here '
            '(`--historical-from` on the first append)._\n').rstrip('\n') + '\n'
    hist = hist.replace('\n# ', '\n## ') if hist.startswith('# ') else hist
    if hist.startswith('# '):
        hist = '#' + hist
    txt = (f'# {title}\n\nTwo parts, never pooled: the HISTORICAL sections (development and selection periods — written once, never changed '
           'by an append) and the FORWARD sessions (period iii, from 2026-10-12: untouched by any rule, model or choice), which the daily job '
           '(`scripts/daily_forward.py`) appends session by session. A forward session is appended only whole: every file fetched and '
           'verified, every capture settled on the official close.\n\n'
           f'{CUM_HIST_BEGIN}\n{hist}{CUM_HIST_END}\n\n{CUM_FWD_BEGIN}\n_No forward session yet._\n{CUM_FWD_END}\n')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(txt, encoding='utf-8')
    os.replace(tmp, path)


def forward_block(root: Path, keys: tuple, sessions: list, parquet_root: Path | None = None, closes: P.OfficialCloses | None = None,
                  decision_prices: dict | None = None) -> str:
    """The forward block: the audit's sections over `sessions` alone (period iii) and a ledger a session"""
    first, last = sessions[0], sessions[-1]
    au = audit_sections(root, keys, first, last, parquet_root, closes, decision_prices, only_days=set(sessions))
    md = [f'# Forward — period iii, {len(sessions)} session{"s" if len(sessions) != 1 else ""}, {first} → {last}', '',
          f'Regenerated from the replay root `{Path(root).name}` by the append (`{REPLAY_VERSION}`, {dt.datetime.now(R.UTC):%Y-%m-%d %H:%M} UTC); '
          'a session listed here is never dropped. These sessions are untouched by any rule, model or choice — an execution and data-quality '
          'record until the thresholds (60 → 120 sessions for condor_em1, 150 for condor_d20\'s D1 re-test, 250 a name for fly5).', '']
    md += [x.replace('## ', '### ', 1) if x.startswith('## ') else (x.replace('### ', '#### ', 1) if x.startswith('### ') else x) for x in au['md']]
    md.append('### Sessions')
    md.append('')
    md.append('| session | candidate · structure | trades | session P&L held $ | at 15:58 $ | settlement | stock left (trades) | pin ≤ $0.50 (trades) | post-market cross |')
    md.append('|---|---|---|---|---|---|---|---|---|')
    for d in sessions:
        for k in keys:
            if k not in T.CANDIDATES:
                continue
            for s in T.CANDIDATES[k].structures:
                xs = [t for t in au['trades'] if t['day'] == d and t['candidate'] == k and t['structure'] == s]
                if not xs:
                    continue
                srcs = sorted({f'{t["name"]} {t["settle_px"]:g} ({(t["settle_from"] or t["settle_source"]).replace("replay: official close (", "").rstrip(")")})' for t in xs})
                ex = [t['pnl_1558_nbbo'] for t in xs if t['pnl_1558_nbbo'] is not None]
                pmk = [t['pm_cross'] for t in xs if t['pm_cross'] is not None]
                md.append(f'| {d} | {label_of(k, s)} | {len(xs)} | {_f(float(sum(t["pnl_nbbo"] for t in xs)))} | '
                          + (_f(float(sum(ex))) + (f' ({len(ex)})' if len(ex) != len(xs) else '') if ex else '—') + f' | {"; ".join(srcs)} | '
                          f'{sum(1 for t in xs if t["stock_left"])} | {sum(1 for t in xs if t["pin_050"])} | '
                          + (f'{sum(pmk)} of {len(pmk)}' if pmk else '—') + ' |')
    md.append('')
    md.append(f'{CUM_STATE}{json.dumps(sessions)} -->')
    return '\n' + '\n'.join(md) + '\n'


def append_cumulative(root: Path, cumulative: Path, keys: tuple = T.DEFAULT_KEYS, parquet_root: Path | None = None,
                      closes: P.OfficialCloses | None = None, decision_prices: dict | None = None, through: str | None = None,
                      historical_from: Path | None = None) -> dict:
    """APPEND mode: the forward sessions of `root` (2026-10-12 on, through `through`) that are whole and not yet in
    `cumulative` are added; the forward block is regenerated over every listed session (so a session's after-hours
    columns fill once the next session is on disk); the historical block's bytes are never touched. A session listed
    before but no longer whole in the root stops it (nothing written). Nothing new: the file is not written at all.
    → {'added', 'pending', 'listed', 'written'}"""
    cumulative = Path(cumulative)
    if not cumulative.exists():
        init_cumulative(cumulative, Path(historical_from).read_text(encoding='utf-8') if historical_from else None)
    text = cumulative.read_text(encoding='utf-8')
    a, b, listed = _cum_parse(text)
    comp, pend = complete_sessions(root, keys, P.FORWARD_START, through or '9999-12-31')
    gone = sorted(set(listed) - set(comp))
    if gone:
        raise ValueError(f'sessions already in {cumulative.name} are not whole in the replay root {root}: {gone} — nothing written')
    new = sorted(set(comp) - set(listed))
    res = {'added': new, 'pending': pend, 'listed': sorted(listed), 'written': False}
    if not new:
        return res
    sessions = sorted(set(listed) | set(new))
    block = forward_block(root, keys, sessions, parquet_root, closes, decision_prices)
    out = text[:a] + block + text[b:]
    assert out[:a] == text[:a], 'the historical part changed'                  # never: the prefix is the old text's
    tmp = cumulative.with_name(cumulative.name + '.tmp')
    tmp.write_text(out, encoding='utf-8')
    os.replace(tmp, cumulative)
    res['written'] = True
    return res


# ---- the parity check against the research's own trade tables ----------------------------------------------------------------------

RN = R.REPO / 'research_notes'
HYP_B_TRADES = RN / 'Compass phase 2' / 'hyp_b_boundary_theta' / 'out' / 'trades_SPY.parquet'
HYP_E_SCORES = RN / 'Compass phase 3' / 'hyp_e_short_premium_lift' / 'out' / 'scores_SPY.parquet'
HYP_F_FLIES = [RN / 'Compass phase 3' / 'hyp_f_cash_butterfly' / 'out' / f'flies_{p}.parquet' for p in ('fit', 'oos')]
HYP_C_FLIES = [RN / 'Compass phase 2' / 'hyp_c_debit_flies' / 'out' / f'flies_{p}.parquet' for p in ('SPY', 'QQQ')]
SCAN_OF = {'11:30': 120, '12:00': 150, '12:30': 180, '13:00': 210, '13:30': 240, '14:00': 270, '14:30': 300, '15:00': 330, '15:30': 360}


def _leg_k(sym):
    p = T.parse_symbol(sym) if sym else None
    return p[3] if p else None


def _diffstats(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    d = np.abs(a - b)
    d = d[np.isfinite(d)]
    return (float(d.max()) if d.size else 0.0), int((d > 0.01 + 1e-9).sum())


def hyp_b_settle(src: ParquetSource, day: str) -> float | None:
    """hyp_b's SPY settlement (engine.py Session): the close of the last bar at or before 16:00 that has one — the bar
    stamped 16:00 when Theta printed one, else the 15:59 bar"""
    b = src.bars('SPY', day)
    if not b or not b['c']:
        return None
    return float(b['c'][-1])


def parity_condor(root: Path, key: str, rule: str, start: str, end: str, src: ParquetSource | None = None) -> tuple[dict, list, pl.DataFrame]:
    df = read_rows(root, (key,), start, end)
    caps = df.filter(pl.col('row_kind') == 'capture')
    sett = df.filter((pl.col('row_kind') == 'settle') & (pl.col('settle_source') == 'official'))
    rep = caps.select('_day', 'minute', 'tradable', 'reason', 'spot', 'l1_symbol', 'l3_symbol', 'price_nbbo', 'price_mid',
                      *[c for c in ('l1_bid', 'l2_ask', 'l3_bid', 'l4_ask') if c in caps.columns],
                      *[c for c in ('t2_decile_full', 't2_score_full', 't2_decile_novix', 't2_decile_primary') if c in caps.columns])
    # the live P&L code (Structure.pnl on the logged structure) at hyp_b's own settlement, beside the replay's
    alt = {}
    if src is not None:
        for c in caps.filter(pl.col('tradable') == 'true').to_dicts():
            st = T.structure_from_row(c)
            px = hyp_b_settle(src, c['_day'])
            if st is not None and px is not None:
                alt[(c['_day'], c['minute'])] = (st.pnl(px), px)
    rep = rep.with_columns(pl.struct('_day', 'minute').map_elements(lambda r: alt.get((r['_day'], r['minute']), (None, None))[0], return_dtype=pl.Float64).alias('pnl_at_hyp_b_settle'),
                           pl.struct('_day', 'minute').map_elements(lambda r: alt.get((r['_day'], r['minute']), (None, None))[1], return_dtype=pl.Float64).alias('hyp_b_settle'))
    rep = rep.join(sett.select('_day', 'minute', 'pnl_nbbo', 'settle_px'), on=['_day', 'minute'], how='left')
    rep = rep.with_columns(pl.col('minute').replace_strict(SCAN_OF, default=None).alias('m_scan'),
                           pl.col('l1_symbol').map_elements(_leg_k, return_dtype=pl.Float64).alias('r_kc'),
                           pl.col('l3_symbol').map_elements(_leg_k, return_dtype=pl.Float64).alias('r_kp'))
    X = pl.read_parquet(HYP_B_TRADES).filter((pl.col('test') == 'sched') & (pl.col('rule') == rule) & (pl.col('width') == 2.0)
                                              & pl.col('m_scan').is_in([SCAN_OF[m] for m in T.CANDIDATES[key].minutes])
                                              & (pl.col('session') >= start) & (pl.col('session') <= end))
    con = X.filter(pl.col('structure') == 'condor').select(pl.col('session').alias('_day'), 'm_scan', pl.col('credit').alias('x_credit'),
                                                           pl.col('pnl_hold').alias('x_pnl'), pl.col('settle').alias('x_settle'), pl.col('spot_e').alias('x_spot'))
    vc = X.filter(pl.col('structure') == 'call').select(pl.col('session').alias('_day'), 'm_scan', pl.col('short_k').alias('x_kc'))
    vp = X.filter(pl.col('structure') == 'put').select(pl.col('session').alias('_day'), 'm_scan', pl.col('short_k').alias('x_kp'))
    J = rep.join(con, on=['_day', 'm_scan'], how='full', coalesce=True).join(vc, on=['_day', 'm_scan'], how='left').join(vp, on=['_day', 'm_scan'], how='left')
    rt = (J['tradable'] == 'true').fill_null(False).to_numpy()
    xt = J['x_credit'].is_not_null().to_numpy()
    both = rt & xt
    B = J.filter(pl.Series(both))
    kdiff = B.filter(((pl.col('r_kc') - pl.col('x_kc')).abs() > 1e-6) | ((pl.col('r_kp') - pl.col('x_kp')).abs() > 1e-6))
    cmax, cn = _diffstats(fnum_col(B, 'price_nbbo'), B['x_credit'].to_numpy())
    pmax, pn = _diffstats(fnum_col(B, 'pnl_nbbo'), B['x_pnl'].to_numpy())
    smax, sn = _diffstats(fnum_col(B, 'settle_px'), B['x_settle'].to_numpy())
    amax, an = _diffstats(fnum_col(B, 'pnl_at_hyp_b_settle'), B['x_pnl'].to_numpy())
    hmax, hn = _diffstats(fnum_col(B, 'hyp_b_settle'), B['x_settle'].to_numpy())
    RO = J.filter(pl.Series(rt & ~xt))
    # a vertical whose credit is $0.05 exactly: the live rule keeps it (>= 0.05 within 1e-9), the research's float compare
    # (credit < MIN_CREDIT) dropped it when the subtraction landed a hair under (0.09 − 0.04 = 0.04999999999999999)
    fp = 0
    for r in RO.to_dicts():
        for b_, a_ in (('l1_bid', 'l2_ask'), ('l3_bid', 'l4_ask')):
            try:
                c_ = float(r[b_]) - float(r[a_])
            except (TypeError, ValueError):
                continue
            if abs(c_ - T.MIN_CREDIT) < 1e-9 and c_ < T.MIN_CREDIT:
                fp += 1
                break
    res = {'cell': f'{key} vs hyp_b {rule} 2-wide condor', 'replay_tradable': int(rt.sum()), 'research_trades': int(xt.sum()), 'matched': int(both.sum()),
           'replay_only': int((rt & ~xt).sum()), 'replay_only_fp_credit_005': fp, 'research_only': int((~rt & xt).sum()), 'strikes_differ': kdiff.height,
           'credit_max_diff': cmax, 'credit_over_1c': cn, 'pnl_max_diff': pmax, 'pnl_over_1c': pn, 'settle_max_diff': smax, 'settle_over_1c': sn,
           'settle_differs': int((np.abs(fnum_col(B, 'settle_px') - B['x_settle'].to_numpy()) > 1e-9).sum()),
           'pnl_at_hyp_b_settle_max_diff': amax, 'pnl_at_hyp_b_settle_over_1c': an, 'hyp_b_settle_max_diff': hmax}
    detail = []
    for r in RO.head(15).to_dicts():
        detail.append(f'replay-only {r["_day"]} {r["minute"]}: shorts {r["r_kc"]}/{r["r_kp"]} credit {r["price_nbbo"]} (call spread {r.get("l1_bid")}−{r.get("l2_ask")}, '
                      f'put spread {r.get("l3_bid")}−{r.get("l4_ask")}; research verticals: call {r["x_kc"]}, put {r["x_kp"]})')
    for r in J.filter(pl.Series(~rt & xt)).head(15).to_dicts():
        detail.append(f'research-only {r["_day"]} m{r["m_scan"]}: research credit {r["x_credit"]:.2f} shorts {r["x_kc"]}/{r["x_kp"]}; replay '
                      f'{"no capture" if r["tradable"] is None else "tradable=" + str(r["tradable"]) + " — " + str(r["reason"])}')
    for r in kdiff.head(10).to_dicts():
        detail.append(f'strikes differ {r["_day"]} {r["minute"]}: replay {r["r_kc"]}/{r["r_kp"]} research {r["x_kc"]}/{r["x_kp"]}')
    return res, detail, J


def parity_deciles(J: pl.DataFrame, start: str, end: str, src: ParquetSource | None = None) -> dict:
    S = pl.read_parquet(HYP_E_SCORES).with_columns(pl.col('session').cast(pl.Utf8).alias('_day'), pl.col('m').alias('m_scan'))
    S = S.select('_day', 'm_scan', 'full_gbm_score', 'full_gbm_dec_reg', 'full_gbm_dec', 'dec_kind')
    K = J.filter(pl.col('t2_decile_full').is_not_null()).join(S, on=['_day', 'm_scan'], how='inner')
    rd = K['t2_decile_full'].cast(pl.Int64).to_numpy()
    out = {'rows': K.height, 'agree_reg': int((rd == K['full_gbm_dec_reg'].to_numpy()).sum()),
           'agree_signal': int((rd == K['full_gbm_dec'].to_numpy()).sum()),
           'score_max_diff': float(np.nanmax(np.abs(fnum_col(K, 't2_score_full') - K['full_gbm_score'].to_numpy()))) if K.height else float('nan'),
           'oof_rows': int((K['dec_kind'] == 'oof').sum())}
    k2 = K.filter(pl.col('dec_kind') != 'oof')
    out['agree_signal_non_oof'] = int((k2['t2_decile_full'].cast(pl.Int64) == k2['full_gbm_dec']).sum())
    out['non_oof_rows'] = k2.height
    out['d1_replay'] = int((rd == 1).sum())
    out['d1_research_reg'] = int((K['full_gbm_dec_reg'] == 1).sum())
    out['d1_research_signal'] = int((K['full_gbm_dec'] == 1).sum())
    # where the score differs: the sessions after an exchange holiday whose VIX file is on disk — the research's
    # vix_prev_close read the last print of the previous VIX FILE (hyp_d lib.py vix_sessions lists VIX files), the live
    # tracker the session before's (the recorder calendar; a holiday is no session)
    bad = K.filter(pl.Series(np.abs(fnum_col(K, 't2_score_full') - K['full_gbm_score'].to_numpy()) > 1e-5))
    out['score_differs_rows'] = bad.height
    out['score_differs_sessions'] = sorted(set(bad['_day'].to_list()))
    if src is not None:
        after = 0
        for d in out['score_differs_sessions']:
            prev = (dt.date.fromisoformat(d) - dt.timedelta(days=1))
            while prev.weekday() >= 5:
                prev -= dt.timedelta(days=1)
            if not src.is_session(prev.isoformat()) and src.index_file('VIX', prev.isoformat()).exists():
                after += 1
        out['score_differs_after_holiday_with_vix_file'] = after
    ok = K.filter(~pl.col('_day').is_in(out['score_differs_sessions']))
    out['agree_reg_elsewhere'] = f"{int((ok['t2_decile_full'].cast(pl.Int64) == ok['full_gbm_dec_reg']).sum())} of {ok.height}"
    out['score_max_diff_elsewhere'] = float(np.nanmax(np.abs(fnum_col(ok, 't2_score_full') - ok['full_gbm_score'].to_numpy()))) if ok.height else float('nan')
    return out


def parity_fly5(root: Path, start: str, end: str) -> tuple[list, list]:
    df = read_rows(root, ('fly5',), start, end)
    caps = df.filter(pl.col('row_kind') == 'capture')
    sett = df.filter((pl.col('row_kind') == 'settle') & (pl.col('settle_source') == 'official'))
    rep = caps.select('_day', '_name', 'minute', 'structure', 'tradable', 'reason', 'k0', 'price_nbbo', 'spot')
    rep = rep.join(sett.select('_day', '_name', 'minute', 'structure', 'pnl_nbbo', 'settle_px'), on=['_day', '_name', 'minute', 'structure'], how='left')
    rep = rep.with_columns(pl.col('minute').str.replace(':', '').alias('t'))
    F = pl.concat([pl.read_parquet(f) for f in HYP_F_FLIES], how='diagonal_relaxed').filter((pl.col('session') >= start) & (pl.col('session') <= end))
    F = F.select(pl.col('session').alias('_day'), pl.col('product').alias('_name'), 't', pl.col('form').alias('structure'), pl.col('K0').alias('x_k0'),
                 pl.when(pl.col('form') == 'iron').then(pl.col('credit_nbbo')).otherwise(pl.col('debit_nbbo')).alias('x_price'),
                 pl.col('pnl_nbbo').alias('x_pnl'), pl.col('spot_close').alias('x_settle'), pl.col('spot').alias('x_spot'))
    C = pl.concat([pl.read_parquet(f) for f in HYP_C_FLIES], how='diagonal_relaxed').filter((pl.col('wing') == 'w5') & (pl.col('session') >= start) & (pl.col('session') <= end))
    C = C.select(pl.col('session').alias('_day'), pl.col('product').alias('_name'), 't', pl.col('kind').alias('structure'), pl.col('pnl').alias('c_pnl'))
    J = rep.join(F, on=['_day', '_name', 't', 'structure'], how='full', coalesce=True).join(C, on=['_day', '_name', 't', 'structure'], how='left')
    res, detail = [], []
    for nm in ('SPY', 'QQQ'):
        for s in ('iron', 'call', 'put'):
            Q = J.filter((pl.col('_name') == nm) & (pl.col('structure') == s))
            rt = (Q['tradable'] == 'true').fill_null(False).to_numpy()
            xt = Q['x_pnl'].is_not_null().to_numpy()
            B = Q.filter(pl.Series(rt & xt))
            pmax, pn = _diffstats(fnum_col(B, 'price_nbbo'), B['x_price'].to_numpy())
            lmax, ln = _diffstats(fnum_col(B, 'pnl_nbbo'), B['x_pnl'].to_numpy())
            cmax, cn = _diffstats(fnum_col(B, 'pnl_nbbo'), B['c_pnl'].to_numpy())
            res.append({'cell': f'fly5 {nm} {s} vs hyp_f ±5', 'replay_tradable': int(rt.sum()), 'research_trades': int(xt.sum()), 'matched': int((rt & xt).sum()),
                        'replay_only': int((rt & ~xt).sum()), 'research_only': int((~rt & xt).sum()),
                        'strikes_differ': int((np.abs(fnum_col(B, 'k0') - B['x_k0'].to_numpy()) > 1e-6).sum()), 'credit_max_diff': pmax, 'credit_over_1c': pn,
                        'pnl_max_diff': lmax, 'pnl_over_1c': ln, 'hyp_c_pnl_max_diff': cmax, 'hyp_c_pnl_over_1c': cn})
            for r in Q.filter(pl.Series(rt & ~xt)).head(5).to_dicts():
                detail.append(f'replay-only fly5 {nm} {s} {r["_day"]} {r["minute"]}: K0 {r["k0"]} price {r["price_nbbo"]}')
            for r in Q.filter(pl.Series(~rt & xt)).head(5).to_dicts():
                detail.append(f'research-only fly5 {nm} {s} {r["_day"]} {r["t"]}: research K0 {r["x_k0"]} price {r["x_price"]:.2f}; replay '
                              f'{"no capture" if r["tradable"] is None else "tradable=" + str(r["tradable"]) + " — " + str(r["reason"])}')
    return res, detail


def parity(root: Path, start: str, end: str, out_dir: Path, parquet_root: Path | None = None, stream=sys.stdout) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = ParquetSource(parquet_root) if parquet_root else None
    rows, detail = [], []
    r1, d1, _ = parity_condor(root, 'condor_em1', 'em1', start, end, src)
    rows.append(r1); detail += d1
    r3, d3, J3 = parity_condor(root, 'condor_d20', 'd20', start, end, src)
    rows.append(r3); detail += d3
    dec = parity_deciles(J3, start, end, src)
    r2, d2 = parity_fly5(root, start, end)
    rows += r2; detail += d2
    md = [f'# Replay parity {start} → {end}', '',
          '| cell | replay tradable | research trades | matched | replay only | research only | strikes differ | max price diff | price diffs > $0.01 | max P&L diff $ | P&L diffs > $0.01 |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        md.append(f'| {r["cell"]} | {r["replay_tradable"]} | {r["research_trades"]} | {r["matched"]} | {r["replay_only"]} | {r["research_only"]} | {r["strikes_differ"]} | '
                  f'{r["credit_max_diff"]:.4f} | {r["credit_over_1c"]} | {r["pnl_max_diff"]:.4f} | {r["pnl_over_1c"]} |')
    md += ['', 'Condors, the settlement and the $0.05 edge:', '']
    for r in rows[:2]:
        md.append(f'- {r["cell"]}: settlement differs on {r["settle_differs"]} of {r["matched"]} matched trades (max {r["settle_max_diff"]:.4f}); '
                  f'the replay\'s own logged structures re-figured by the live Structure.pnl at hyp_b\'s settlement (the 16:00 bar when it printed): '
                  f'max P&L difference {r["pnl_at_hyp_b_settle_max_diff"]:.4f}, {r["pnl_at_hyp_b_settle_over_1c"]} over $0.01; replay-only trades with a '
                  f'vertical at exactly $0.05: {r["replay_only_fp_credit_005"]} of {r["replay_only"]}')
    md += ['', f'condor_d20 deciles: {json.dumps(dec)}', '', 'Details (first of each kind):', ''] + [f'- {x}' for x in detail]
    (out_dir / f'parity_{start}_{end}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    pl.DataFrame(rows, infer_schema_length=None).write_csv(out_dir / f'parity_{start}_{end}.csv')
    if stream is not None:
        print('\n'.join(md), file=stream)
    return {'rows': rows, 'deciles': dec, 'detail': detail}


# ---- the Theta fetch (the owner's machine, against its running terminal) -------------------------------------------------------------
#
# THE AUDIT (docs/fetch-theta-audit.md). Every rule below is checked against the code that BUILT the stored dataset (the
# `thetadata` SDK 1.0.14 over gRPC — scratchpad theta/ds/build.py, its fetch.py twin with no strike band) and the
# Slayer Terminal's live v3 code (3abida server/feed.ts, scripts/theta-history, scripts/theta-probe/lib.ts):
#   - 127.0.0.1 alone (Theta's 476 WRONG_IP for "localhost"), no proxy, no key on a request — the terminal holds it;
#     nothing here starts, stops or signs into a terminal. Before any data call: GET /v3/terminal/mdds/status must answer
#     CONNECTED, else nothing is asked.
#   - format=ndjson on every data call; a line that is not JSON fails the answer (a cut stream), never skipped.
#   - v3 has no pagination ("There is no more next-page header / pagination"); a Next-Page header all the same fails.
#   - 472 NO_DATA for a day the calendar calls a session is a FAILURE, never an empty session. 476 / 478 (another
#     terminal took the key's session) / a refused connection stop the whole run. 429, 474, 571, 572, a timeout and a cut
#     stream are asked again (waits 5, 15, 45, 120 s, a quarter jitter); 471 / 473 / 570 and the rest fail at once.
#   - nothing is asked in Theta's own gap (00:00–01:45 New York: "data from the previous day isn't available"), nor for a
#     session not yet over.
#   - the files are staged under <root>/_staging/<run>/ and VALIDATED (validate_frame) before they are placed; a day's
#     manifest (<root>/_manifest/<D>.json) records every file's status, request, checks and hash; an existing file is
#     never overwritten without --force, and --force keeps the old one beside it (<file>.prev-<run>).

THETA_BASE = 'http://127.0.0.1:25503/v3'
THETA_MAX_IN_FLIGHT = 3
THETA_TIMEOUT_S = 900.0                 # the biggest stored SPXW day took 172 s through the SDK
# THE STOCK BARS' VENUE. The stored data/underlying files were asked through the thetadata SDK 1.0.14 with no venue,
# and that SDK's stock_history_ohlc sends venue='nqb' by default (client.py) — v3's own default is nqb too. The bars
# feed the replay's spot, its 15:59 settlement and candidate 3's relative volume against the 20 sessions before, so a
# fetched session must be asked on the venue the stored sessions were: nqb. `--stock-venue utp_cta` (the 3abida
# downloader's) is kept for the overlap check (docs/fetch-theta-audit.md, step 2) — never mix venues inside one root.
STOCK_VENUES = ('nqb', 'utp_cta')
STOCK_VENUE = 'nqb'
FETCH_CHAINS = ('SPY', 'QQQ', 'SPXW')
FETCH_UNDER = ('SPY', 'QQQ')
FETCH_INDEX = ('SPX', 'VIX')
THETA_STATUS = {200: 'OK', 404: 'NO_IMPL', 410: 'GONE', 429: 'OS_LIMIT', 470: 'GENERAL', 471: 'PERMISSION', 472: 'NO_DATA',
                473: 'INVALID_PARAMS', 474: 'DISCONNECTED', 475: 'TERMINAL_PARSE', 476: 'WRONG_IP', 477: 'NO_PAGE_FOUND',
                478: 'INVALID_SESSION_ID', 570: 'LARGE_REQUEST', 571: 'SERVER_STARTING', 572: 'UNCAUGHT_ERROR',
                0: 'TIMEOUT_OR_CUT', -1: 'NO_TERMINAL'}
RETRY_STATUSES = frozenset({0, 429, 474, 571, 572})
FATAL_STATUSES = frozenset({-1, 476, 478})
RETRY_WAITS = (5.0, 15.0, 45.0, 120.0)
THETA_GAP_END_MIN = 105                 # 01:45 New York
SESSION_DONE = '16:30'                  # a session's minutes are asked only once this has passed in New York
MANIFEST_DIR, STAGING_DIR = '_manifest', '_staging'
REQUIRED_FIELDS = {'chain': ('timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'),
                   'under': ('timestamp', 'open', 'high', 'low', 'close', 'volume', 'count', 'vwap'),
                   'index': ('timestamp', 'price')}
# the fewest strikes a same-day chain may hold when no stored session stands before it (the stored 2026 minimum:
# SPY 110, QQQ 146, SPXW 238; median 173, 190, 252)
STRIKE_FLOOR = {'SPY': 80, 'QQQ': 100, 'SPXW': 150}
NORM_SHARE = 0.5                        # strikes / rows under half the median of the 20 stored sessions before: INCOMPLETE
VOLUME_SHARE = 0.25                     # a day's bar volume under a quarter of that median (another venue?): INCOMPLETE
MAX_CROSSED = 0.005                     # crossed quotes (bid > ask) — stored: at most 2 rows a day in 136k
MAX_NOQUOTE = 0.02                      # rows with no quote after 09:30 — stored: none (SPY/QQQ's 09:30 row is unquoted)
MIN_GRID = 0.99                         # each minute holds at least 99% of the day's contracts — stored: 100%
MIN_CLOSES = 0.98                       # bars with a close among 09:30–15:59 — stored: 390 of 390
CAL_FROM = (min(R.HOLIDAYS)[:4] + '-01-01') if R.HOLIDAYS else '9999-01-01'


def _red(s) -> str:
    """the SDK key's shape taken out of any text kept (none is ever sent here; defensive)"""
    return re.sub(r'td1_prod_[A-Za-z0-9]+', '[key]', str(s))


class ThetaAnswer:
    __slots__ = ('url', 'status', 'rows', 'error', 'attempts', 'statuses', 'seconds', 'bytes', 'fatal')

    def __init__(self, url, status, rows=None, error=None, attempts=0, statuses=None, seconds=0.0, nbytes=0, fatal=False):
        self.url, self.status, self.rows, self.error = url, status, rows or [], error
        self.attempts, self.statuses, self.seconds, self.bytes, self.fatal = attempts, statuses or [], seconds, nbytes, fatal

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.error is None

    def record(self) -> dict:
        return {'url': self.url, 'http': self.status, 'name': THETA_STATUS.get(self.status, ''), 'attempts': self.attempts,
                'statuses': self.statuses, 'rows': len(self.rows), 'bytes': self.bytes, 'seconds': round(self.seconds, 2),
                'error': None if self.error is None else _red(self.error)[:300]}


def parse_ndjson(body: str) -> tuple[list, str | None]:
    """NDJSON → rows (a line a row; a {"response": [...]} or a list line flattened). A line that is not JSON is an
    error — the stream was cut — never skipped."""
    rows = []
    for n, line in enumerate(body.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            return rows, f'line {n + 1} is not JSON ({line[:60]!r}) — a cut stream'
        if isinstance(r, dict) and isinstance(r.get('response'), list):
            rows += [x for x in r['response'] if isinstance(x, dict)]
        elif isinstance(r, dict):
            rows.append(r)
        elif isinstance(r, list):
            rows += [x for x in r if isinstance(x, dict)]
    return rows, None


class ThetaFetch:
    """GETs against the Theta Terminal v3 on 127.0.0.1 (never "localhost" — Theta's 476; no proxy; the terminal holds
    the key, none is ever sent); format=ndjson on every data call; at most THETA_MAX_IN_FLIGHT at once; retries by
    status; a fatal status stops every call after it. Never starts, stops or signs into a terminal."""

    def __init__(self, base: str = THETA_BASE, timeout_s: float = THETA_TIMEOUT_S, opener=None, max_in_flight: int = THETA_MAX_IN_FLIGHT,
                 waits: tuple = RETRY_WAITS, sleep=time.sleep):
        u = urllib.parse.urlparse(base)
        if u.hostname != '127.0.0.1' or u.scheme != 'http':
            raise ValueError(f'the Theta Terminal is asked on http://127.0.0.1 alone (got {base!r}; "localhost" is refused by the terminal)')
        self.base = base.rstrip('/')
        self.timeout_s = timeout_s
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.sem = threading.BoundedSemaphore(max(1, min(int(max_in_flight), THETA_MAX_IN_FLIGHT)))
        self.waits, self.sleep = tuple(waits), sleep
        self.calls = 0
        self.stopped: str | None = None
        self.requests: list = []
        self._lock = threading.Lock()

    def url_for(self, path: str, params: dict | None = None) -> str:
        p = dict(params or {})
        if not path.startswith('/terminal/'):
            p['format'] = 'ndjson'
        return f'{self.base}{path}' + (f'?{urllib.parse.urlencode(p)}' if p else '')

    def _once(self, url: str) -> tuple[int, str | None, str | None, dict]:
        import http.client
        import socket
        with self.sem:
            with self._lock:
                self.calls += 1
            try:
                with self.opener.open(urllib.request.Request(url, headers={'Accept': 'application/x-ndjson'}), timeout=self.timeout_s) as res:
                    body = res.read().decode('utf-8', 'replace')
                    return res.status, body, None, {k.lower(): v for k, v in res.headers.items()}
            except urllib.error.HTTPError as e:
                txt = ''
                try:
                    txt = e.read().decode('utf-8', 'replace')[:200]
                except Exception:  # noqa: BLE001
                    pass
                return e.code, None, f'{e.code} {THETA_STATUS.get(e.code, "")}: {txt.strip()}', {}
            except urllib.error.URLError as e:
                if isinstance(e.reason, ConnectionRefusedError):
                    return -1, None, f'no terminal answers on {self.base} (connection refused)', {}
                if isinstance(e.reason, (socket.timeout, TimeoutError)):
                    return 0, None, f'timeout after {self.timeout_s:.0f} s', {}
                return 0, None, f'URLError: {str(e.reason)[:160]}', {}
            except ConnectionRefusedError:
                return -1, None, f'no terminal answers on {self.base} (connection refused)', {}
            except (socket.timeout, TimeoutError):
                return 0, None, f'timeout after {self.timeout_s:.0f} s', {}
            except (http.client.IncompleteRead, ConnectionResetError, http.client.RemoteDisconnected) as e:
                return 0, None, f'the stream was cut: {type(e).__name__}', {}
            except Exception as e:  # noqa: BLE001
                return 0, None, f'{type(e).__name__}: {str(e)[:160]}', {}

    def get(self, path: str, params: dict) -> ThetaAnswer:
        url = self.url_for(path, params)
        t0, statuses = time.time(), []
        if self.stopped:
            return ThetaAnswer(url, 'stopped', error=f'not asked: the run stopped ({self.stopped})', fatal=True)
        for attempt in range(len(self.waits) + 1):
            status, body, err, hdr = self._once(url)
            if status == 200:
                nxt = hdr.get('next-page')
                if nxt and nxt.strip().lower() not in ('null', 'none', ''):
                    err, status = f'the answer is paginated (Next-Page: {nxt[:80]}) — v3 should not page; not taken', 477
                else:
                    rows, perr = parse_ndjson(body or '')
                    if perr:
                        status, err = 0, perr
                    else:
                        statuses.append(200)
                        a = ThetaAnswer(url, 200, rows, None, attempt + 1, statuses, time.time() - t0, len(body or ''))
                        self._note(a)
                        return a
            statuses.append(status)
            if status in FATAL_STATUSES:
                with self._lock:
                    self.stopped = self.stopped or f'{status} {THETA_STATUS.get(status, "")}: {err}'
                a = ThetaAnswer(url, status, error=err, attempts=attempt + 1, statuses=statuses, seconds=time.time() - t0, fatal=True)
                self._note(a)
                return a
            if status in RETRY_STATUSES and attempt < len(self.waits):
                self.sleep(self.waits[attempt] * (1 + 0.25 * (hash((url, attempt)) % 100) / 100))
                continue
            a = ThetaAnswer(url, status, error=err, attempts=attempt + 1, statuses=statuses, seconds=time.time() - t0)
            self._note(a)
            return a
        raise AssertionError('unreachable')

    def _note(self, a: ThetaAnswer) -> None:
        with self._lock:
            self.requests.append(a.record())

    def terminal_status(self) -> tuple[bool, str]:
        """GET /v3/terminal/mdds/status (no format): the terminal's own word — CONNECTED, else nothing is asked"""
        status, body, err, _ = self._once(self.url_for('/terminal/mdds/status'))
        text = (body or err or '').strip()[:120]
        return status == 200 and text.upper() == 'CONNECTED', f'{status} {text}'

    def calendar(self, day: str) -> tuple[str | None, str | None]:
        """GET /v3/calendar/on_date: the day's type (open, full_close, early_close, weekend) or the error"""
        a = self.get('/calendar/on_date', {'date': day.replace('-', '')})
        if not a.ok:
            return None, a.error
        t = next((str(r.get('type')) for r in a.rows if r.get('type') is not None), None)
        return t, None if t else 'no type in the answer'


# ---- the calendar, the norms, the frames and their checks (shared by --fetch-theta, --merge-parquet and --verify-parquet) ----

def session_of(day: str) -> dict:
    """the recorder's calendar (eod_recorder HOLIDAYS / HALF_DAYS, carried from CAL_FROM): full, half, holiday, weekend —
    or 'unknown' before the calendar's first year (a weekday is then assumed a session, and a missing file is not
    called a failure)"""
    d = dt.date.fromisoformat(day)
    if d.weekday() >= 5:
        return {'kind': 'weekend', 'close_j': None}
    if day < CAL_FROM:
        return {'kind': 'unknown', 'close_j': 390}
    if not R.is_trading_day(day):
        return {'kind': 'holiday', 'close_j': None}
    if R.is_half_day(day):
        return {'kind': 'half', 'close_j': 210}
    return {'kind': 'full', 'close_j': 390}


THETA_CAL = {'full': 'open', 'half': 'early_close', 'holiday': 'full_close', 'weekend': 'weekend'}


def fetch_jobs(day: str, venue: str = STOCK_VENUE) -> list[dict]:
    d = day.replace('-', '')
    win = {'start_time': '09:30:00', 'end_time': '16:00:00'}
    jobs = [dict(kind='chain', sym=s, path='/option/history/quote', params=dict(symbol=s, expiration=d, date=d, interval='1m', **win)) for s in FETCH_CHAINS]
    jobs += [dict(kind='under', sym=s, path='/stock/history/ohlc', params=dict(symbol=s, start_date=d, end_date=d, interval='1m', venue=venue, **win)) for s in FETCH_UNDER]
    jobs += [dict(kind='index', sym=s, path='/index/history/price', params=dict(symbol=s, date=d, interval='1m', **win)) for s in FETCH_INDEX]
    return jobs


KIND_WORDS = {'chain': 'chain', 'chains': 'chain', 'underlying': 'under', 'under': 'under', 'bars': 'under', 'index': 'index'}


def parse_only(text: str | None) -> set | None:
    """--only SPY-underlying,SPXW-chain,VIX-index → {('under', 'SPY'), ...}; None = everything"""
    if not text:
        return None
    known = {(j['kind'], j['sym']) for j in fetch_jobs('2026-01-02')}
    out = set()
    for tok in (t.strip() for t in text.split(',') if t.strip()):
        sym, _, kind = tok.partition('-')
        k = (KIND_WORDS.get(kind.lower()), sym.upper())
        if k not in known:
            raise ValueError(f'--only {tok!r}: one of ' + ', '.join(sorted(f'{s}-{ {"chain": "chain", "under": "underlying", "index": "index"}[k]}' for k, s in known)))
        out.add(k)
    return out


def rel_of(kind: str, sym: str, day: str) -> str:
    return {'chain': f'data_full/chains/{sym}/{day}.parquet', 'under': f'data/underlying/{sym}/{day}.parquet',
            'index': f'data/index/{sym}/{day}.parquet'}[kind]


def _ts_ny(s: pl.Series) -> pl.Series:
    """Theta's "2026-10-13T09:30:00.000" (New York wall clock, no offset) → Datetime(ms, America/New_York); a stamp
    that does not parse is null (counted by the caller, never silently dropped)"""
    s = s.cast(pl.Utf8).str.slice(0, 19)
    return s.str.to_datetime('%Y-%m-%dT%H:%M:%S', strict=False).dt.replace_time_zone('America/New_York', ambiguous='earliest').dt.cast_time_unit('ms')


def _num(rows, k):
    out, bad = [], 0
    for r in rows:
        v = r.get(k)
        try:
            x = float(v)
            if math.isfinite(x):
                out.append(x)
                continue
        except (TypeError, ValueError):
            pass
        out.append(None)
        bad += v is not None
    return out, bad


def frame_of(kind: str, rows: list, day: str, root_sym: str | None = None) -> tuple[pl.DataFrame, list]:
    """Theta's rows → the dataset's layout and dtypes (the stored files' exact schema), with every row it could not
    take said in `problems` (a FAILED file): a field missing, a number or a stamp that does not parse, a right that is
    neither call nor put, a contract of another root or expiry. Nothing is filled in: no quote is null, never a mid or a
    trade. The chain's no-quote minute (Theta writes bid = ask = 0 with both sizes 0 — the SDK wrote NaN) is null, as
    the stored files hold it; the bars' no-trade minute (prices 0, volume 0) has null prices, its session VWAP kept; an
    index price of 0 (no print yet) is null."""
    problems = []
    need = REQUIRED_FIELDS[kind]
    if rows:
        miss = {k: sum(1 for r in rows if k not in r) for k in need}
        miss = {k: n for k, n in miss.items() if n}
        if miss:
            problems.append('fields missing: ' + ', '.join(f'{k} in {n} rows' for k, n in miss.items()))
    stamps = [str(r.get('timestamp', '')) for r in rows]
    if kind == 'chain':
        (bid, b1), (ask, b2), (bs, b3), (as_, b4), (k, b5) = (_num(rows, c) for c in ('bid', 'ask', 'bid_size', 'ask_size', 'strike'))
        if b1 + b2 + b3 + b4 + b5:
            problems.append(f'numbers that do not parse: {b1 + b2 + b3 + b4 + b5}')
        for i in range(len(rows)):
            if bid[i] == 0 and ask[i] == 0 and not bs[i] and not as_[i]:
                bid[i] = ask[i] = None
        right = []
        for r in rows:
            x = str(r.get('right', '')).strip().upper()
            right.append('CALL' if x in ('C', 'CALL') else 'PUT' if x in ('P', 'PUT') else None)
        if any(x is None for x in right):
            problems.append(f'rights neither call nor put: {sum(1 for x in right if x is None)} rows')
        exps = {str(r.get('expiration')).replace('-', '')[:8] for r in rows if r.get('expiration') is not None}
        if exps and exps != {day.replace('-', '')}:
            problems.append(f'expirations other than the day: {sorted(exps)[:4]}')
        syms = {str(r.get('symbol')).upper() for r in rows if r.get('symbol') is not None}
        if root_sym and syms and syms != {root_sym}:
            problems.append(f'roots other than {root_sym}: {sorted(syms)[:4]}')
        df = pl.DataFrame({'timestamp': stamps, 'strike': k, 'right': right, 'bid': bid, 'ask': ask,
                           'bid_size': [None if x is None else int(x) for x in bs], 'ask_size': [None if x is None else int(x) for x in as_]},
                          schema={'timestamp': pl.Utf8, 'strike': pl.Float64, 'right': pl.Utf8, 'bid': pl.Float64, 'ask': pl.Float64,
                                  'bid_size': pl.Int32, 'ask_size': pl.Int32})
        df = df.with_columns(_ts_ny(df['timestamp']).alias('timestamp'), ((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
        if df['bid_size'].null_count() or df['ask_size'].null_count():
            problems.append('sizes missing')
        keys = ['strike', 'right', 'timestamp']
    elif kind == 'under':
        cols = {}
        bad = 0
        for c in ('open', 'high', 'low', 'close', 'volume', 'count', 'vwap'):
            cols[c], b = _num(rows, c)
            bad += b
        if bad:
            problems.append(f'numbers that do not parse: {bad}')
        for i in range(len(rows)):
            if not cols['volume'][i] and not cols['close'][i]:
                for c in ('open', 'high', 'low', 'close'):
                    cols[c][i] = None
        df = pl.DataFrame({'timestamp': stamps, **{c: cols[c] for c in ('open', 'high', 'low', 'close')},
                           'volume': [None if x is None else int(x) for x in cols['volume']], 'count': [None if x is None else int(x) for x in cols['count']],
                           'vwap': cols['vwap']},
                          schema={'timestamp': pl.Utf8, 'open': pl.Float64, 'high': pl.Float64, 'low': pl.Float64, 'close': pl.Float64,
                                  'volume': pl.Int64, 'count': pl.Int64, 'vwap': pl.Float64})
        df = df.with_columns(_ts_ny(df['timestamp']).alias('timestamp'))
        keys = ['timestamp']
    else:
        p, bad = _num(rows, 'price')
        if bad:
            problems.append(f'numbers that do not parse: {bad}')
        df = pl.DataFrame({'timestamp': stamps, 'price': [None if (x is None or x <= 0) else x for x in p]}, schema={'timestamp': pl.Utf8, 'price': pl.Float64})
        df = df.with_columns(_ts_ny(df['timestamp']).alias('timestamp'))
        keys = ['timestamp']
    nts = df['timestamp'].null_count()
    if nts:
        problems.append(f'stamps that do not parse: {nts} rows (e.g. {next((s for s, ok in zip(stamps, df["timestamp"].is_null()) if ok), "")!r})')
    if kind == 'chain' and df['strike'].null_count():
        problems.append(f'rows without a strike: {df["strike"].null_count()}')
    other = df.filter(pl.col('timestamp').is_not_null() & (pl.col('timestamp').dt.strftime('%Y-%m-%d') != day)).height
    if other:
        problems.append(f'rows of another day: {other}')
    return df.sort(keys), problems


def read_layout(f: Path) -> pl.DataFrame:
    return pl.read_parquet(f)


_NORM_CACHE: dict = {}


def norms_for(roots: tuple, kind: str, sym: str, day: str, n: int = 20) -> dict:
    """the stored files' norm for a file: the median over up to `n` sessions before `day` found under `roots` (a chain:
    strikes, rows, the median strike; bars: the day's volume, the median close; an index: the median price)"""
    key = (tuple(str(r) for r in roots), kind, sym, day, n)
    if key in _NORM_CACHE:
        return _NORM_CACHE[key]
    files: dict = {}
    for r in roots:
        d = Path(r) / Path(rel_of(kind, sym, day)).parent
        if d.is_dir():
            for f in d.glob('*.parquet'):
                if f.name[:10] < day and f.name[:10] not in files and len(f.name) == 18:
                    files[f.name[:10]] = f
    vals: list = []
    for dd in sorted(files)[::-1]:
        if len(vals) >= n:
            break
        try:
            if kind == 'chain':
                c = pl.read_parquet(files[dd], columns=['strike'])
                vals.append((c['strike'].n_unique(), c.height, float(c['strike'].median())))
            elif kind == 'under':
                b = pl.read_parquet(files[dd], columns=['close', 'volume'])
                if b['close'].drop_nulls().len() >= 30:
                    vals.append((int(b['volume'].sum()), float(b['close'].drop_nulls().median())))
            else:
                p = pl.read_parquet(files[dd], columns=['price'])['price'].drop_nulls()
                if p.len() >= 30:
                    vals.append((float(p.median()),))
        except Exception:  # noqa: BLE001
            continue
    med = lambda i: float(np.median([v[i] for v in vals])) if vals else None  # noqa: E731
    out = {'sessions': len(vals)}
    if kind == 'chain':
        out.update(strikes=med(0), rows=med(1), strike_mid=med(2))
    elif kind == 'under':
        out.update(volume=med(0), price=med(1))
    else:
        out.update(price=med(0))
    _NORM_CACHE[key] = out
    return out


def validate_frame(kind: str, sym: str, day: str, df: pl.DataFrame, norm: dict | None = None, sess: dict | None = None) -> tuple[str, dict, list]:
    """A file against its session: 'ok' or 'INCOMPLETE' (data that is there but is not a whole session) with the checks
    measured and the problems found. The stored files' norms (2026-10-05→09 and the 80 sessions before): every one of
    the 391 minutes 09:30–16:00, every contract quoted every minute, no duplicate (timestamp, strike, right), at most a
    crossed quote or two, SPY/QQQ's 09:30 row unquoted; 391 bars, a close on every bar 09:30–15:59; 391 index prints."""
    sess = sess or session_of(day)
    norm = norm or {}
    probs: list = []
    close_j = sess.get('close_j') if sess.get('close_j') is not None else 390
    want = set(range(0, close_j + 1))
    if df.height == 0:
        return 'INCOMPLETE', {'rows': 0}, ['no rows']
    j = (df['timestamp'].dt.hour().cast(pl.Int32) * 60 + df['timestamp'].dt.minute().cast(pl.Int32) - 570)
    off_minute = int(((df['timestamp'].dt.second() != 0) | (df['timestamp'].dt.millisecond() != 0)).sum())
    days = set(df['timestamp'].dt.strftime('%Y-%m-%d').unique().to_list())
    ck: dict = {'rows': df.height}
    if days != {day}:
        probs.append(f'stamps on other days: {sorted(days - {day})[:3]}')
    if off_minute:
        probs.append(f'{off_minute} stamps not on a whole minute')
    have = set(j.unique().to_list())
    ck['minutes'] = len(have & want)
    ck['minutes_expected'] = len(want)
    missing = sorted(want - have)
    if missing:
        probs.append(f'{len(missing)} of {len(want)} minutes missing (first {", ".join(f"{9 + (m + 30) // 60:02d}:{(m + 30) % 60:02d}" for m in missing[:3])})')
    outside = sorted(x for x in have if x < 0 or x > 390)
    if outside:
        probs.append(f'{len(outside)} minutes outside 09:30–16:00')
    if kind == 'chain':
        d2 = df.with_columns(j.alias('j'))
        dups = d2.height - d2.select('j', 'strike', 'right').n_unique()
        ck['duplicates'] = dups
        if dups:
            probs.append(f'{dups} duplicate (timestamp, strike, right) rows')
        contracts = d2.select('strike', 'right').n_unique()
        strikes = d2['strike'].n_unique()
        ck['strikes'], ck['contracts'] = strikes, contracts
        one_sided = strikes * 2 - contracts
        ck['one_sided_strikes'] = one_sided
        if one_sided > 0.02 * strikes:
            probs.append(f'{one_sided} of {strikes} strikes quote one right only')
        per_min = d2.filter(pl.col('j').is_in(list(want))).group_by('j').len()
        low = per_min.filter(pl.col('len') < MIN_GRID * contracts).height
        ck['grid'] = round(df.height / max(1, contracts * len(have)), 4)
        if low:
            probs.append(f'{low} minutes hold under {MIN_GRID:.0%} of the {contracts} contracts')
        floor = STRIKE_FLOOR.get(sym, 50)
        if norm.get('strikes'):
            floor = max(floor * 0.5, NORM_SHARE * norm['strikes'])
            ck['strikes_norm'] = norm['strikes']
        if strikes < floor:
            probs.append(f'{strikes} strikes, under the norm\'s floor {floor:.0f}')
        if norm.get('rows') and df.height < NORM_SHARE * norm['rows']:
            probs.append(f'{df.height} rows, under half the norm {norm["rows"]:.0f}')
        mid_k = float(d2['strike'].median())
        ref = norm.get('strike_mid') or norm.get('ref')
        ck['strike_median'] = mid_k
        if ref and not (0.5 <= mid_k / ref <= 2.0):
            probs.append(f'the strikes\' median {mid_k:g} is not near the norm {ref:g} (strike units?)')
        elif not ref and mid_k > 50_000:
            probs.append(f'the strikes\' median {mid_k:g} reads as thousandths of a dollar (v2 units?)')
        b, a = d2['bid'], d2['ask']
        neg = int(((b < 0) | (a < 0) | (d2['bid_size'] < 0) | (d2['ask_size'] < 0)).fill_null(False).sum())
        crossed = int(((b > a) & (a > 0)).fill_null(False).sum())
        noq = int(d2.filter(pl.col('j') > 0)['bid'].null_count())
        zero_bid = int((b == 0).fill_null(False).sum())
        late = d2.filter(pl.col('j') > 0).height or 1
        ck.update(negative=neg, crossed=crossed, crossed_share=round(crossed / df.height, 6), no_quote_after_0930=noq,
                  no_quote_share=round(noq / late, 6), zero_bid_share=round(zero_bid / df.height, 4))
        if neg:
            probs.append(f'{neg} rows with a negative price or size')
        if crossed > MAX_CROSSED * df.height:
            probs.append(f'{crossed} crossed quotes ({crossed / df.height:.2%})')
        if noq > MAX_NOQUOTE * late:
            probs.append(f'{noq} rows after 09:30 with no quote ({noq / late:.2%})')
        if 'mid' in d2.columns:
            badmid = int(d2.select(((pl.col('mid') - (pl.col('bid') + pl.col('ask')) / 2).abs() > 1e-9).fill_null(False).sum()).item())
            if badmid:
                probs.append(f'{badmid} mids that are not (bid + ask) / 2')
    else:
        dups = df.height - j.n_unique()
        ck['duplicates'] = dups
        if dups:
            probs.append(f'{dups} duplicate timestamps')
        col = 'close' if kind == 'under' else 'price'
        jl = j.to_list()
        vals = df[col].to_list()
        reg = [v for jj, v in zip(jl, vals) if 0 <= jj < close_j]
        if kind == 'index' and sym == 'SPX':
            reg = [v for jj, v in zip(jl, vals) if 1 <= jj < close_j]      # SPX has no print at 09:30:00 (the stored files: null)
        got = sum(1 for v in reg if v is not None)
        ck['priced'] = got
        ck['priced_expected'] = (close_j - 1) if (kind == 'index' and sym == 'SPX') else close_j
        if got < MIN_CLOSES * ck['priced_expected']:
            probs.append(f'{got} of {ck["priced_expected"]} minutes priced (a holiday\'s padded file, or a gap)')
        if kind == 'under':
            last = dict(zip(jl, vals)).get(close_j - 1)
            if last is None:
                probs.append(f'no close on the {9 + (close_j - 1 + 30) // 60:02d}:{(close_j - 1 + 30) % 60:02d} bar (the replay\'s settlement)')
            bad = int(df.select(((pl.col('low') > pl.col('high')) | (pl.col('close') > pl.col('high') + 1e-9) | (pl.col('close') < pl.col('low') - 1e-9)
                                 | (pl.col('volume') < 0)).fill_null(False).sum()).item())
            if bad:
                probs.append(f'{bad} bars whose prices do not sit in their range')
            vol = int(df['volume'].sum())
            ck['volume'] = vol
            if norm.get('volume'):
                ck['volume_norm'] = norm['volume']
                if vol < VOLUME_SHARE * norm['volume']:
                    probs.append(f'the day\'s volume {vol:,} is under a quarter of the norm {norm["volume"]:,.0f} (another venue?)')
        if norm.get('price'):
            pm = df[col].drop_nulls()
            if pm.len() and not (0.5 <= float(pm.median()) / norm['price'] <= 2.0):
                probs.append(f'prices near {float(pm.median()):g}, not the norm {norm["price"]:g}')
        if (df[col].drop_nulls() <= 0).sum():
            probs.append('prices at or under zero')
    return ('ok' if not probs else 'INCOMPLETE'), ck, probs


# ---- the manifest and the placing of a file --------------------------------------------------------------------------------------

_MANIFEST_LOCK = threading.Lock()


def manifest_path(root: Path, day: str) -> Path:
    return Path(root) / MANIFEST_DIR / f'{day}.json'


def read_manifest(root: Path, day: str) -> dict | None:
    f = manifest_path(root, day)
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return {'day': day, 'files': {}, 'unreadable': True}


def write_manifest(root: Path, day: str, files: dict | None = None, **top) -> None:
    """merge `files` entries (a file's latest word wins; its attempts counted) and top-level facts into the day's manifest"""
    with _MANIFEST_LOCK:
        m = read_manifest(root, day) or {'day': day, 'files': {}}
        m.update(top)
        for rel, e in (files or {}).items():
            old = m['files'].get(rel) or {}
            e = dict(e)
            e['tries'] = int(old.get('tries', 0)) + 1
            m['files'][rel] = e
        f = manifest_path(root, day)
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + f'.tmp{os.getpid()}{threading.get_ident()}')
        tmp.write_text(json.dumps(m, indent=1, sort_keys=True, default=str), encoding='utf-8')
        os.replace(tmp, f)


def refusals(root: Path, day: str) -> dict:
    """the files a day's manifest says are not whole: {rel: 'STATUS: why'} (no manifest: nothing refused — the stored files)"""
    m = read_manifest(root, day)
    if not m:
        return {}
    if m.get('unreadable'):
        return {'_manifest': 'FAILED: the manifest does not read'}
    return {rel: f'{e.get("status")}: {"; ".join(e.get("problems") or []) or e.get("error") or ""}'.strip()
            for rel, e in m.get('files', {}).items() if e.get('status') not in ('ok', 'skipped')}


def sha256_of(f: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(f, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def place(staged: Path, target: Path, force: bool, run_id: str) -> str:
    """put a validated file in place: 'placed' (nothing there), 'identical' (the same bytes there: kept as it was),
    'exists' (another file there and no --force: NOT placed), 'replaced' (--force: the old kept beside as
    <name>.prev-<run>)"""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256_of(target) == sha256_of(staged):
            return 'identical'
        if not force:
            return 'exists'
        os.replace(target, target.with_name(f'{target.name}.prev-{run_id}'))
        shutil_copy(staged, target)
        return 'replaced'
    shutil_copy(staged, target)
    return 'placed'


def shutil_copy(src: Path, dst: Path) -> None:
    import shutil
    tmp = dst.with_name(dst.name + f'.tmp{os.getpid()}{threading.get_ident()}')
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def _run_id(now: dt.datetime) -> str:
    return now.astimezone(R.UTC).strftime('%Y%m%dT%H%M%SZ') + f'-{os.getpid()}'


# ---- --fetch-theta ---------------------------------------------------------------------------------------------------------------

def fetch_theta(start: str, end: str, parquet_root: Path, base: str | None = None, force: bool = False, stream=sys.stderr,
                fetcher: ThetaFetch | None = None, only: set | None = None, venue: str = STOCK_VENUE, norm_roots: tuple = (),
                now: dt.datetime | None = None, in_flight: int = THETA_MAX_IN_FLIGHT, check_calendar: bool = True) -> dict:
    """Each New York session in [start, end]: the same-day chains (SPY, QQQ, SPXW), SPY/QQQ minute bars and SPX/VIX
    prints, staged, validated, then placed into the layout; the day's manifest says what each file is. A session whose
    answer is an error, a 472 or short of the norm is FAILED / INCOMPLETE in the manifest — never an empty session —
    and is not placed. Returns what happened; `rc` 0 only when every file asked is whole."""
    root = Path(parquet_root)
    now = now or dt.datetime.now(R.UTC)
    if venue not in STOCK_VENUES:
        raise ValueError(f'--stock-venue is one of {STOCK_VENUES}')
    th = fetcher or ThetaFetch(base or os.environ.get('THETA_BASE') or THETA_BASE, max_in_flight=in_flight)
    run_id = _run_id(now)
    out = {'run': run_id, 'written': [], 'identical': [], 'skipped': [], 'failed': [], 'incomplete': [], 'exists': [], 'not_asked': [],
           'holidays': [], 'calendar': {}, 'venue': venue}
    ny = now.astimezone(R.NY)
    if ny.hour * 60 + ny.minute < THETA_GAP_END_MIN:
        out['aborted'] = 'inside Theta\'s own gap (00:00–01:45 New York: the previous day is not served) — run it after 01:45'
        return _finish(out, th)
    ok, word = th.terminal_status()
    out['terminal'] = word
    if not ok:
        out['aborted'] = f'the Theta Terminal on {th.base} is not CONNECTED ({word}) — nothing asked; start or sign it in on this machine first'
        return _finish(out, th)
    norm_roots = tuple(norm_roots) + (root,)
    todo = []
    for day in weekdays(start, end):
        sess = session_of(day)
        jobs = [j for j in fetch_jobs(day, venue) if only is None or (j['kind'], j['sym']) in only]
        if sess['kind'] == 'holiday':
            out['holidays'].append(day)
            write_manifest(root, day, session='holiday')
            continue
        if now < R.ny_at(day, SESSION_DONE):
            for j in jobs:
                out['not_asked'].append({'file': rel_of(j['kind'], j['sym'], day), 'error': f'the session is not over (asked after {SESSION_DONE} New York)'})
            continue
        tcal = None
        if check_calendar:
            tcal, cerr = th.calendar(day)
            out['calendar'][day] = {'recorder': sess['kind'], 'theta': tcal, 'error': cerr}
            if th.stopped:
                break
            if tcal is not None and sess['kind'] in THETA_CAL and tcal != THETA_CAL[sess['kind']]:
                why = f'the calendars disagree: the recorder says {sess["kind"]}, Theta says {tcal} — fix eod_recorder HOLIDAYS / HALF_DAYS first'
                ent = {rel_of(j['kind'], j['sym'], day): {'status': 'FAILED', 'error': why, 'run': run_id} for j in jobs}
                write_manifest(root, day, ent, session=sess['kind'], theta_calendar=tcal)
                out['failed'] += [{'file': r, 'error': why} for r in ent]
                continue
        write_manifest(root, day, session=sess['kind'], theta_calendar=tcal)
        for j in jobs:
            rel = rel_of(j['kind'], j['sym'], day)
            if (root / rel).exists() and not force:
                out['skipped'].append(rel)
                continue
            todo.append((day, sess, j, rel))
    lock = threading.Lock()

    def run(item):
        day, sess, j, rel = item
        ans = th.get(j['path'], j['params'])
        entry = {'run': run_id, 'request': ans.record(), 'fetched_at': R.iso_z(dt.datetime.now(R.UTC))}
        if j['kind'] == 'under':
            entry['venue'] = venue
        if not ans.ok:
            why = ans.error or f'{ans.status}'
            if ans.status == 472:
                why = f'472 NO_DATA for a day the calendar calls a session ({sess["kind"]}) — not an empty session'
            entry.update(status='FAILED', error=why)
            write_manifest(root, day, {rel: entry})
            with lock:
                (out['not_asked'] if ans.status == 'stopped' else out['failed']).append({'file': rel, 'error': why})
            return
        if not ans.rows:
            why = 'HTTP 200 with no rows for a calendar session — not an empty session'
            entry.update(status='FAILED', error=why)
            write_manifest(root, day, {rel: entry})
            with lock:
                out['failed'].append({'file': rel, 'error': why})
            return
        df, probs = frame_of(j['kind'], ans.rows, day, j['sym'] if j['kind'] == 'chain' else None)
        staged = root / STAGING_DIR / run_id / rel
        staged.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(staged, compression='zstd')
        entry['staged'] = str(staged.relative_to(root))
        entry['sha256'] = sha256_of(staged)
        if probs:
            entry.update(status='FAILED', problems=probs, rows=df.height)
            write_manifest(root, day, {rel: entry})
            with lock:
                out['failed'].append({'file': rel, 'error': '; '.join(probs)})
            return
        status, ck, vprobs = validate_frame(j['kind'], j['sym'], day, df, norms_for(norm_roots, j['kind'], j['sym'], day), sess)
        entry.update(status=status, checks=ck, problems=vprobs)
        if status != 'ok':
            write_manifest(root, day, {rel: entry})
            with lock:
                out['incomplete'].append({'file': rel, 'error': '; '.join(vprobs)})
            return
        how = place(staged, root / rel, force, run_id)
        entry['placed'] = how
        if how == 'exists':
            entry.update(status='FAILED', error='a different file is already there (no --force): not placed')
        else:
            staged.unlink()                                  # placed (or the same bytes already there): the staged copy goes;
            entry['staged'] = None                           # a FAILED / INCOMPLETE one stays for inspection
        write_manifest(root, day, {rel: entry})
        with lock:
            key = {'placed': 'written', 'replaced': 'written', 'identical': 'identical', 'exists': 'exists'}[how]
            out[key].append(rel)
        if stream is not None:
            print(f'fetch-theta: {rel} {df.height} rows {how}', file=stream, flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(int(in_flight), THETA_MAX_IN_FLIGHT))) as ex:
        list(ex.map(run, todo))
    if th.stopped:
        out['aborted'] = f'stopped: {th.stopped}'
    return _finish(out, th)


def _finish(out: dict, th: ThetaFetch) -> dict:
    out['calls'] = th.calls
    out['requests'] = th.requests
    out['rc'] = 0 if not (out.get('aborted') or out['failed'] or out['incomplete'] or out['exists'] or out['not_asked']) else 1
    return out


# ---- --merge-parquet: a validated layout into another, never over a file ---------------------------------------------------------

def layout_files(root: Path) -> list[tuple[str, str, str, str]]:
    """(kind, sym, day, rel) for every file of the layout under `root`"""
    root = Path(root)
    out = []
    for kind, sub in (('chain', 'data_full/chains'), ('under', 'data/underlying'), ('index', 'data/index')):
        d = root / sub
        if not d.is_dir():
            continue
        for sd in sorted(p for p in d.iterdir() if p.is_dir()):
            for f in sorted(sd.glob('*.parquet')):
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.parquet', f.name):
                    out.append((kind, sd.name, f.name[:10], f'{sub}/{sd.name}/{f.name}'))
    return out


def merge_parquet(src: Path, dst: Path, force: bool = False, stream=sys.stderr, now: dt.datetime | None = None) -> dict:
    """Copy every file of `src`'s layout into `dst` after checking it: its manifest says ok (when it has one), it
    validates against its session and `dst`'s norms, it has no duplicate key — and NOTHING is copied while any file
    fails or any target already exists (identical bytes count as an overlap too, listed apart), unless --force (a
    different target is then kept beside as <name>.prev-<run>; an identical one is left). `src` is never changed."""
    src, dst = Path(src), Path(dst)
    run_id = _run_id(now or dt.datetime.now(R.UTC))
    res = {'run': run_id, 'checked': 0, 'refused': [], 'overlap': [], 'identical': [], 'copied': [], 'rc': 0}
    plan = []
    for kind, sym, day, rel in layout_files(src):
        res['checked'] += 1
        rf = refusals(src, day)
        if rel in rf:
            res['refused'].append({'file': rel, 'why': f'its manifest: {rf[rel]}'})
            continue
        try:
            df = pl.read_parquet(src / rel)
        except Exception as e:  # noqa: BLE001
            res['refused'].append({'file': rel, 'why': f'does not read: {e}'})
            continue
        sess = session_of(day)
        if sess['kind'] in ('holiday', 'weekend'):
            res['refused'].append({'file': rel, 'why': f'{day} is a {sess["kind"]}'})
            continue
        st, ck, probs = validate_frame(kind, sym, day, df, norms_for((dst, src), kind, sym, day), sess)
        if st != 'ok':
            res['refused'].append({'file': rel, 'why': '; '.join(probs)})
            continue
        tgt = dst / rel
        if tgt.exists():
            (res['identical'] if sha256_of(tgt) == sha256_of(src / rel) else res['overlap']).append(rel)
        plan.append((kind, sym, day, rel, ck))
    if res['refused'] or ((res['overlap'] or res['identical']) and not force):
        res['rc'] = 1
        res['note'] = 'nothing copied: ' + ('files refused; ' if res['refused'] else '') + \
            ('targets already exist (listed) — --force replaces a different one, keeping it beside' if (res['overlap'] or res['identical']) else '')
        return res
    for kind, sym, day, rel, ck in plan:
        how = place(src / rel, dst / rel, force, run_id)
        if how in ('placed', 'replaced'):
            res['copied'].append(f'{rel} ({how})')
        e = ((read_manifest(src, day) or {}).get('files') or {}).get(rel) or {}
        write_manifest(dst, day, {rel: dict(e, status='ok', checks=ck, merged_from=str(src), merge_run=run_id, placed=how,
                                            sha256=sha256_of(dst / rel))}, session=session_of(day)['kind'])
        if stream is not None:
            print(f'merge-parquet: {rel} {how}', file=stream, flush=True)
    return res


# ---- --verify-parquet ------------------------------------------------------------------------------------------------------------

def compare_frames(kind: str, a: pl.DataFrame, b: pl.DataFrame) -> dict:
    """`a` (checked) against `b` (the reference) on the same key: schema, keys only in one, values that differ"""
    keys = ['timestamp', 'strike', 'right'] if kind == 'chain' else ['timestamp']
    out = {'schema_equal': a.schema == b.schema, 'rows': a.height, 'rows_ref': b.height}
    if not out['schema_equal']:
        out['schema'] = {'checked': {k: str(v) for k, v in a.schema.items()}, 'reference': {k: str(v) for k, v in b.schema.items()}}
    common = [c for c in b.columns if c in a.columns and c not in keys]
    out['only_checked'] = a.join(b, on=keys, how='anti').height
    out['only_reference'] = b.join(a, on=keys, how='anti').height
    m = a.join(b, on=keys, how='inner', suffix='_ref')
    diffs = {}
    for c in common:
        x, y = m[c], m[f'{c}_ref']
        if x.dtype.is_numeric() and y.dtype.is_numeric():
            d = ((x.cast(pl.Float64) - y.cast(pl.Float64)).abs() > 1e-9).fill_null(False) | (x.is_null() != y.is_null())
        else:
            d = (x.cast(pl.Utf8) != y.cast(pl.Utf8)).fill_null(False) | (x.is_null() != y.is_null())
        n = int(d.sum())
        if n:
            diffs[c] = n
    out['value_diffs'] = diffs
    out['matched'] = m.height
    worst = max([out['only_checked'], out['only_reference']] + list(diffs.values()) or [0])
    out['equal'] = out['schema_equal'] and worst == 0
    out['ok'] = out['schema_equal'] and worst <= 0.001 * max(1, b.height)
    return out


def verify_parquet(root: Path, start: str, end: str, only: set | None = None, prior: bool = True, compare_root: Path | None = None,
                   norm_roots: tuple = (), stream=sys.stdout) -> dict:
    """Per New York weekday in [start, end] and per file: expected (the recorder's calendar, half days marked), present,
    the manifest's word, complete (validate_frame against the norms of the sessions before it), duplicates; then the
    sessions before each day that the replay reads (SPY's bars the 20 sessions before — candidate 3 —, VIX and QQQ the
    session before); with `compare_root`, every file also found there compared value for value. `ok` False on any
    failure."""
    root = Path(root)
    roots = tuple(norm_roots) + (root,)
    rows, fails, warns = [], [], []
    for day in weekdays(start, end):
        sess = session_of(day)
        rf = refusals(root, day)
        for j in fetch_jobs(day):
            kind, sym = j['kind'], j['sym']
            if only is not None and (kind, sym) not in only:
                continue
            rel = rel_of(kind, sym, day)
            f = root / rel
            r = {'day': day, 'session': sess['kind'], 'file': rel, 'present': f.exists(), 'manifest': None, 'status': None, 'checks': {}, 'problems': []}
            m = ((read_manifest(root, day) or {}).get('files') or {}).get(rel)
            r['manifest'] = (m or {}).get('status')
            if rel in rf:
                r['problems'].append(f'the manifest: {rf[rel]}')
            if not f.exists():
                if sess['kind'] in ('full', 'half'):
                    r['problems'].append('missing for a session')
                elif sess['kind'] == 'unknown':
                    r['status'] = 'unknown'
                    warns.append(f'{rel}: missing; {day} is before the calendar ({CAL_FROM})')
                else:
                    r['status'] = sess['kind']
            else:
                try:
                    df = pl.read_parquet(f)
                except Exception as e:  # noqa: BLE001
                    df = None
                    r['problems'].append(f'does not read: {e}')
                if df is not None:
                    if sess['kind'] in ('holiday', 'weekend'):
                        col = {'chain': 'bid', 'under': 'close', 'index': 'price'}[kind]
                        n = df[col].drop_nulls().len() if col in df.columns else 0
                        r['status'] = f'{sess["kind"]} (a padded file, {n} values)' if n < 30 else sess['kind']
                        if n >= 30:
                            warns.append(f'{rel}: {n} values on a {sess["kind"]}')
                    else:
                        st, ck, probs = validate_frame(kind, sym, day, df, norms_for(roots, kind, sym, day), sess)
                        r['checks'] = ck
                        r['problems'] += probs
                        if compare_root is not None and (Path(compare_root) / rel).exists():
                            c = compare_frames(kind, df, pl.read_parquet(Path(compare_root) / rel))
                            r['compare'] = c
                            if not c['ok']:
                                r['problems'].append(f'differs from {compare_root}: schema_equal={c["schema_equal"]} only_checked={c["only_checked"]} '
                                                     f'only_reference={c["only_reference"]} value_diffs={c["value_diffs"]}')
                            elif not c['equal']:
                                warns.append(f'{rel}: not equal to {compare_root} (within 0.1%): only_checked={c["only_checked"]} '
                                             f'only_reference={c["only_reference"]} value_diffs={c["value_diffs"]}')
                            else:
                                r['status'] = 'ok (equal to the reference)'
            if r['status'] is None:
                r['status'] = 'FAIL' if r['problems'] else 'ok'
            if r['status'] == 'FAIL':
                fails.append(f'{rel}: ' + '; '.join(r['problems']))
            rows.append(r)
        # the sessions before that the replay reads
        if prior and sess['kind'] in ('full', 'half', 'unknown'):
            wants = []
            if only is None or ('under', 'SPY') in only:
                wants.append(('under', 'SPY', T.previous_sessions(day, T.PRIOR_SESSIONS)))
            if only is None or ('index', 'VIX') in only:
                wants.append(('index', 'VIX', T.previous_sessions(day, 1)))
            if only is None or ('under', 'QQQ') in only:
                wants.append(('under', 'QQQ', T.previous_sessions(day, 1)))
            for kind, sym, ds in wants:
                bad = []
                for d in ds:
                    f = root / rel_of(kind, sym, d)
                    if f.exists():
                        try:
                            col = 'close' if kind == 'under' else 'price'
                            ok_ = pl.read_parquet(f, columns=[col])[col].drop_nulls().len() >= 30
                        except Exception:  # noqa: BLE001
                            ok_ = False
                        rfd = refusals(root, d).get(rel_of(kind, sym, d))
                        if ok_ and not rfd:
                            continue
                        bad.append(f'{d} ({rfd or "under 30 values"})')
                    elif d < CAL_FROM:
                        warns.append(f'{rel_of(kind, sym, d)}: missing; {d} is before the calendar ({CAL_FROM}) — a holiday there is not known')
                    else:
                        bad.append(f'{d} (missing)')
                r = {'day': day, 'session': sess['kind'], 'file': f'prior {sym} {"bars" if kind == "under" else "prints"}: {len(ds)} sessions {ds[0]}…{ds[-1]}',
                     'present': len(ds) - len(bad), 'manifest': None, 'status': 'ok' if not bad else 'FAIL', 'checks': {}, 'problems': bad}
                if bad:
                    fails.append(f'{day} {r["file"]}: missing or short ' + ', '.join(bad[:5]))
                rows.append(r)
    rep = {'root': str(root), 'start': start, 'end': end, 'ok': not fails, 'fails': fails, 'warnings': warns, 'rows': rows}
    if stream is not None:
        print_verify(rep, stream)
    return rep


def print_verify(rep: dict, stream) -> None:
    print(f'verify-parquet {rep["root"]} {rep["start"]} → {rep["end"]}', file=stream)
    print('| day | session | file | present | manifest | rows | minutes | strikes | crossed | no quote >09:30 | zero bid | priced | dups | status |', file=stream)
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|', file=stream)
    for r in rep['rows']:
        c = r['checks']
        mins = f'{c["minutes"]}/{c["minutes_expected"]}' if 'minutes' in c else ''
        pr = f'{c["priced"]}/{c["priced_expected"]}' if 'priced' in c else ''
        print(f'| {r["day"]} | {r["session"]} | {r["file"]} | {r["present"]} | {r["manifest"] or ""} | {c.get("rows", "")} | {mins} | '
              f'{c.get("strikes", "")} | {c.get("crossed", "")} | {c.get("no_quote_after_0930", "")} | {c.get("zero_bid_share", "")} | {pr} | '
              f'{c.get("duplicates", "")} | {r["status"]}{(" — " + "; ".join(r["problems"])) if r["problems"] else ""} |', file=stream)
    for w in rep['warnings']:
        print(f'WARN {w}', file=stream)
    for f in rep['fails']:
        print(f'FAIL {f}', file=stream)
    print('verify-parquet: ' + ('PASS' if rep['ok'] else f'FAIL ({len(rep["fails"])})'), file=stream)


# ---- the command line (paper_tracker.py hands --backtest and --fetch-theta here) ---------------------------------------------------------

def parquet_root_of(args) -> Path:
    r = getattr(args, 'parquet_root', None) or os.environ.get('PAPER_PARQUET_ROOT')
    if not r:
        raise SystemExit('--parquet-root (or PAPER_PARQUET_ROOT) names the stored Parquet layout: <root>/data_full/chains/…, <root>/data/underlying/…, <root>/data/index/…')
    return Path(r)


def replay_root_of(args, settle_on: str) -> Path:
    r = getattr(args, 'backtest_data', None) or os.environ.get('PAPER_BACKTEST_DATA')
    return Path(r) if r else (DEFAULT_OFFICIAL_ROOT if settle_on == 'official' else DEFAULT_REPLAY_ROOT)


DEFAULT_CUMULATIVE = R.REPO / 'research_notes' / 'Compass phase 3' / 'forward_cumulative.md'


def uw_1m_dirs() -> tuple:
    """more folders of UW /ohlc/1m answers to read decision prices from (PAPER_UW_1M_DIRS, os.pathsep-separated —
    e.g. the backtest fetch cache the after-hours study read); data/postmarket_1m and data_recorder/ohlc_1m always"""
    return tuple(Path(x) for x in (os.environ.get('PAPER_UW_1M_DIRS') or '').split(os.pathsep) if x)


def read_decision_prices(path: str | None) -> dict | None:
    """decision prices from a CSV (name, day, price) → {(name, day): price}; no file → None: the report reads them off the
    UW 1-minute answers on disk (paper_audit.decision_prices_on_disk — the after-hours study's rule)"""
    if not path:
        return None
    d = pl.read_csv(path, infer_schema_length=None)
    return {(str(n), str(dd)[:10]): float(px) for n, dd, px in d.select('name', 'day', 'price').iter_rows() if px is not None}


def run_cli(args) -> int:
    settle_on = getattr(args, 'settle_on', None) or DEFAULT_SETTLE
    if getattr(args, 'append_report', False):
        pr = getattr(args, 'parquet_root', None) or os.environ.get('PAPER_PARQUET_ROOT')
        keys = tuple(k.strip() for k in (getattr(args, 'candidates', None) or ','.join(T.DEFAULT_KEYS)).split(',') if k.strip())
        try:
            res = append_cumulative(replay_root_of(args, 'official'), Path(getattr(args, 'cumulative', None) or DEFAULT_CUMULATIVE), keys,
                                    parquet_root=Path(pr) if pr else None, decision_prices=read_decision_prices(getattr(args, 'decision_prices', None)),
                                    through=getattr(args, 'through', None), historical_from=getattr(args, 'historical_from', None))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        print(json.dumps(res))
        return 0
    root = parquet_root_of(args)
    if getattr(args, 'merge_parquet', None):
        res = merge_parquet(Path(args.merge_parquet), root, force=args.force)
        print(json.dumps({k: (v if isinstance(v, (int, str)) else len(v)) for k, v in res.items()}))
        for k in ('refused', 'overlap', 'identical'):
            for x in res[k]:
                print(f'{k.upper()} {x if isinstance(x, str) else x["file"] + ": " + x["why"]}', file=sys.stderr)
        if res.get('note'):
            print(res['note'], file=sys.stderr)
        return res['rc']
    if not args.start or not args.end:
        print('--start and --end (YYYY-MM-DD) are needed', file=sys.stderr)
        return 2
    try:
        only = parse_only(getattr(args, 'only', None))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    extra = tuple(Path(x) for x in [getattr(args, 'compare_root', None)] if x)
    if getattr(args, 'verify_parquet', False):
        rep = verify_parquet(root, args.start, args.end, only=only, prior=not getattr(args, 'no_prior', False),
                             compare_root=extra[0] if extra else None, norm_roots=extra, stream=sys.stdout)
        if getattr(args, 'verify_json', None):
            Path(args.verify_json).write_text(json.dumps(rep, indent=1, default=str), encoding='utf-8')
        return 0 if rep['ok'] else 1
    if args.fetch_theta:
        try:
            res = fetch_theta(args.start, args.end, root, force=args.force, only=only, venue=getattr(args, 'stock_venue', None) or STOCK_VENUE,
                              norm_roots=extra, in_flight=getattr(args, 'theta_in_flight', None) or THETA_MAX_IN_FLIGHT)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        print(json.dumps({k: (v if isinstance(v, (int, str)) or k == 'calendar' else len(v)) for k, v in res.items() if k != 'requests'}))
        for k in ('failed', 'incomplete', 'exists', 'not_asked'):
            for x in res[k]:
                print(f'{k.upper()} {x if isinstance(x, str) else x["file"] + ": " + x["error"]}', file=sys.stderr)
        if res.get('aborted'):
            print(f'ABORTED {res["aborted"]}', file=sys.stderr)
        return res['rc']
    keys = tuple(k.strip() for k in (args.candidates or ','.join(T.DEFAULT_KEYS)).split(',') if k.strip())
    bad = [k for k in keys if k not in T.CANDIDATES]
    if bad:
        print(f'unknown candidate(s) {bad}: {", ".join(T.CANDIDATES)}', file=sys.stderr)
        return 2
    rroot = replay_root_of(args, settle_on)
    try:
        res = replay(args.start, args.end, keys, root, rroot, live_root=Path(args.data), settle_on=settle_on)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else rroot / 'reports'
    build_report(rroot, keys, args.start, args.end, out, parquet_root=root, wall_seconds=res['seconds'], settle_on=settle_on,
                 decision_prices=read_decision_prices(getattr(args, 'decision_prices', None)))
    print(json.dumps(res))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='paper_backtest.py — the replay parity check against the research\'s trade tables')
    p.add_argument('mode', choices=['parity', 'report'])
    p.add_argument('--start', required=True)
    p.add_argument('--end', required=True)
    p.add_argument('--backtest-data', default=os.environ.get('PAPER_BACKTEST_DATA') or str(DEFAULT_REPLAY_ROOT))
    p.add_argument('--candidates', default=','.join(T.DEFAULT_KEYS))
    p.add_argument('--out', default=None)
    p.add_argument('--parquet-root', default=os.environ.get('PAPER_PARQUET_ROOT'), help='parity: re-figure the condors at hyp_b\'s settlement')
    p.add_argument('--settle-on', choices=SETTLE_MODES, default=None, help='report: the convention (default: the root\'s own)')
    a = p.parse_args(argv)
    root = Path(a.backtest_data)
    out = Path(a.out) if a.out else root / 'reports'
    if a.mode == 'parity':
        parity(root, a.start, a.end, out, Path(a.parquet_root) if a.parquet_root else None)
    else:
        build_report(root, tuple(a.candidates.split(',')), a.start, a.end, out, parquet_root=Path(a.parquet_root) if a.parquet_root else None,
                     settle_on=a.settle_on)
    return 0


if __name__ == '__main__':
    sys.exit(main())
