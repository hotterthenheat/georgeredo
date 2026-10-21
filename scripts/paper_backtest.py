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
  - the official close (ohlc/1d's `r` row): THE 15:59 BAR'S CLOSE — the research's convention (hyp_c common.py "the
    16:00 close - the bar stamped 15:59"; hyp_b takes the last bar at or before 16:00 with a close, the same bar since
    Theta's 16:00 bar carries none). Labelled `close_official_from` = OFFICIAL_FROM on every settle row.
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
    python3 -I scripts/paper_tracker.py --fetch-theta --start 2026-10-12 --end 2026-10-16 --parquet-root R
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
import paper_tracker as T  # noqa: E402
import vol_model as V  # noqa: E402

REPLAY_VERSION = 'paper-backtest-2026-10-21.1'
SOURCE = 'backtest-parquet'
DEFAULT_REPLAY_ROOT = R.REPO / 'data_recorder' / 'paper_backtest'
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
            if not f.exists():
                return None
            c = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
            return c.with_columns(_j(pl.col('timestamp'))).drop('timestamp').sort('j', 'strike', 'right')
        return self._get(('chain', root_sym, day), load)

    def bars(self, sym: str, day: str) -> dict | None:
        """{'j': [...], 'o','h','l','c','v'} for the bars stamped 09:30 .. 16:00 with a close (j 0 .. 390)"""
        f = self.under_file(sym, day)

        def load():
            if not f.exists():
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
            if not f.exists():
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
    names answer stock-state / ohlc with 422, as UW Basic does."""

    def __init__(self, src: ParquetSource, limiter, log, clock):
        self.src, self.limiter, self.log, self.clock = src, limiter, log, clock
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
        hol = {d for d in weekdays(have[0], have[-1]) if d not in hs}
        # near the replayed days (the model reads the 20 sessions before; VIX the one before) a file with under 30 bars
        # is no session either
        lo = (dt.date.fromisoformat(days[0]) - dt.timedelta(days=60)).isoformat()
        hol |= {d for d in weekdays(max(lo, have[0]), min(days[-1], have[-1])) if d in hs and not src.is_session(d)}
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

def make_tracker(src: ParquetSource, replay_root: Path, live_root: Path | None, keys: tuple, stream=None):
    scrub = R.Scrub(None)
    store = ReplayStore(replay_root, live_root)
    log = R.make_logger(scrub, store.root / '_logs', stream=stream, name='paper_backtest')
    log.setLevel(logging.WARNING)
    clock = ReplayClock(dt.datetime(2000, 1, 1, tzinfo=R.UTC))
    limiter = R.RateLimiter(max_in_flight=1, per_minute=10 ** 9, daily_budget=10 ** 9, clock=clock)
    client = ReplayClient(src, limiter, log, clock)

    def spx_spot(day: str, minute: str):
        m = MINUTE_OF(minute)
        p = dict(src.prints('SPX', day) or [])
        return p.get(m), SPX_SPOT_SOURCE

    tr = T.Tracker(client, store, limiter, log, clock, scrub, cands=T.active_candidates(keys=keys), theta=ParquetVix(src),
                   recorder_root=None, bar_wait_s=0, vix_uw=False, spx_spot=spx_spot, spx_settle_source=SPX_SETTLE,
                   official_from=OFFICIAL_FROM)
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


def replay(start: str, end: str, keys: tuple, parquet_root: Path, replay_root: Path, live_root: Path | None = None,
           progress=sys.stderr) -> dict:
    """Every New York weekday in [start, end]: classify it, then run the tracker's events of the day at their minutes"""
    src = ParquetSource(parquet_root)
    days = weekdays(start, end)
    saved = install_calendar(src, days)
    t0 = time.time()
    info: dict = {}
    try:
        tr, store, client, clock = make_tracker(src, replay_root, live_root, keys)
        all_cands = tr.cands
        have = src.days('SPY')
        first, last = (have[0], have[-1]) if have else (None, None)
        n = 0
        for day in days:
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
            missing, cands = [], []
            for c in all_cands:
                names = []
                for nm in c.names:
                    miss = [str(src.file_for(k, s, day).relative_to(src.root)) for k, s in needs(c, nm) if not src.file_for(k, s, day).exists()]
                    if miss:
                        missing.append({'candidate': c.key, 'name': nm, 'files': miss})
                    else:
                        names.append(nm)
                if names:
                    import dataclasses
                    cands.append(dataclasses.replace(c, names=tuple(names)))
            notes = []
            if any(c.key == 'condor_d20' for c in cands) and not src.index_file('VIX', day).exists():
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
                 wall_seconds: float | None = None, stream=sys.stdout) -> dict:
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
    md.append(f'# Paper tracker — historical replay {start} → {end}')
    md.append('')
    md.append(f'`{REPLAY_VERSION}` on `{T.VERSION}` ({T.RULES_VERSION}, {T.C3_RULES_VERSION}). Written {dt.datetime.now(R.UTC):%Y-%m-%d %H:%M} UTC'
              + (f'; this run took {wall_seconds:.0f} s (a minute already replayed into the root is skipped, so a resumed run is quick).' if wall_seconds else '.'))
    md.append('')
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
    nif = sorted(d for d, v in days_info.items() if v['status'] == 'not in files')
    if nif:
        md.append(f'- Not in the stored files ({len(nif)}): {nif[0]} … {nif[-1]} — sessions after 2026-10-09 (the 12th onward) need '
                  'their chains fetched first (`--fetch-theta`, on the owner\'s machine), then a replay.')
    if parquet_root is not None:
        have = ParquetSource(parquet_root).days('SPY')
        if have:
            nxt = next(d for d in weekdays(have[-1], (dt.date.fromisoformat(have[-1]) + dt.timedelta(days=7)).isoformat()) if d > have[-1])
            md.append(f'- The stored files end on {have[-1]}: sessions from {nxt} on (the 12th onward) are not in them and need their chains '
                      'fetched first — `paper_tracker.py --fetch-theta --start D1 --end D2 --parquet-root R` on the owner\'s machine '
                      '(the Theta Terminal running there), then `--backtest` over them.')
    notes = sorted(d for d, v in days_info.items() if v.get('note') and v['status'] == 'replayed')
    if notes:
        md.append(f'- Replayed with a note ({len(notes)}): ' + '; '.join(f'{d} {days_info[d]["note"]}' for d in notes[:20]) + (' …' if len(notes) > 20 else ''))
    md.append('')
    if df is None or df.height == 0:
        md.append('No replay rows in this range.')
        (out_dir / f'backtest_{stamp}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
        pl.DataFrame({'section': []}).write_csv(out_dir / f'backtest_{stamp}.csv')
        return {'md': str(out_dir / f'backtest_{stamp}.md'), 'csv': str(out_dir / f'backtest_{stamp}.csv'), 'cells': []}
    caps = df.filter(pl.col('row_kind') == 'capture')
    sett = df.filter((pl.col('row_kind') == 'settle') & pl.col('settle_source').is_in(['official', SPX_SETTLE]) & (pl.col('tradable') == 'true'))
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

THETA_BASE = 'http://127.0.0.1:25503/v3'
THETA_MAX_IN_FLIGHT = 3
STOCK_VENUE = 'utp_cta'                 # the consolidated tape, as the 3abida downloader asks for it
FETCH_CHAINS = ('SPY', 'QQQ', 'SPXW')
FETCH_UNDER = ('SPY', 'QQQ')
FETCH_INDEX = ('SPX', 'VIX')


class ThetaFetch:
    """GETs against the Theta Terminal v3 on 127.0.0.1 (never "localhost" — Theta's 476; no proxy; the terminal holds
    the key, none is ever sent); format=ndjson on every call; at most THETA_MAX_IN_FLIGHT at once. Never starts, stops
    or signs into a terminal."""

    def __init__(self, base: str = THETA_BASE, timeout_s: float = 300.0, opener=None, max_in_flight: int = THETA_MAX_IN_FLIGHT):
        u = urllib.parse.urlparse(base)
        if u.hostname != '127.0.0.1':
            raise ValueError(f'the Theta Terminal is asked on 127.0.0.1 alone (got {u.hostname!r}; "localhost" is refused by the terminal)')
        self.base = base.rstrip('/')
        self.timeout_s = timeout_s
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.sem = threading.BoundedSemaphore(max(1, min(int(max_in_flight), THETA_MAX_IN_FLIGHT)))
        self.calls = 0

    def get(self, path: str, params: dict) -> tuple[int, list, str | None]:
        q = urllib.parse.urlencode(dict(params, format='ndjson'))
        url = f'{self.base}{path}?{q}'
        with self.sem:
            self.calls += 1
            try:
                with self.opener.open(urllib.request.Request(url, headers={'Accept': 'application/x-ndjson'}), timeout=self.timeout_s) as res:
                    body = res.read().decode('utf-8', 'replace')
                    status = res.status
            except urllib.error.HTTPError as e:
                txt = e.read().decode('utf-8', 'replace')[:200] if hasattr(e, 'read') else ''
                return e.code, [], ('no data' if e.code == 472 else f'{e.code}: {txt}')
            except Exception as e:  # noqa: BLE001
                return 0, [], f'{type(e).__name__}: {str(e)[:160]}'
        rows = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if isinstance(r, dict) and isinstance(r.get('response'), list):
                rows += [x for x in r['response'] if isinstance(x, dict)]
            elif isinstance(r, dict):
                rows.append(r)
            elif isinstance(r, list):
                rows += [x for x in r if isinstance(x, dict)]
        return status, rows, None


def _ny_ts(col: pl.Series) -> pl.Series:
    """Theta's "2026-10-13T09:30:00.000" (New York wall clock, no offset) → Datetime(ms, America/New_York)"""
    s = col.cast(pl.Utf8).str.slice(0, 19)
    return s.str.to_datetime('%Y-%m-%dT%H:%M:%S', strict=False).dt.replace_time_zone('America/New_York', ambiguous='earliest').dt.cast_time_unit('ms')


def _num(rows, k):
    out = []
    for r in rows:
        v = r.get(k)
        try:
            x = float(v)
            out.append(x if math.isfinite(x) else None)
        except (TypeError, ValueError):
            out.append(None)
    return out


def chain_frame(rows: list) -> pl.DataFrame:
    """quote rows → the dataset's chain layout: timestamp, strike, right CALL/PUT, bid, ask, bid_size, ask_size, mid. A
    minute with no quote on either side (bid = ask = 0, both sizes 0) is null, as the dataset holds it."""
    bid, ask, bs, as_ = _num(rows, 'bid'), _num(rows, 'ask'), _num(rows, 'bid_size'), _num(rows, 'ask_size')
    for i in range(len(rows)):
        if (bid[i] or 0) == 0 and (ask[i] or 0) == 0 and (bs[i] or 0) == 0 and (as_[i] or 0) == 0:
            bid[i] = ask[i] = None
    right = [('CALL' if str(r.get('right', '')).upper().startswith('C') else 'PUT') for r in rows]
    df = pl.DataFrame({'timestamp': [str(r.get('timestamp', '')) for r in rows], 'strike': _num(rows, 'strike'), 'right': right,
                       'bid': bid, 'ask': ask, 'bid_size': [int(x or 0) for x in bs], 'ask_size': [int(x or 0) for x in as_]},
                      schema={'timestamp': pl.Utf8, 'strike': pl.Float64, 'right': pl.Utf8, 'bid': pl.Float64, 'ask': pl.Float64,
                              'bid_size': pl.Int32, 'ask_size': pl.Int32})
    df = df.with_columns(_ny_ts(df['timestamp']).alias('timestamp'), ((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    return df.filter(pl.col('timestamp').is_not_null() & pl.col('strike').is_not_null()).sort('strike', 'right', 'timestamp')


def bars_frame(rows: list) -> pl.DataFrame:
    """stock ohlc rows → timestamp, open, high, low, close, volume, count, vwap (a minute with no trade: prices null)"""
    o, h, l, c = _num(rows, 'open'), _num(rows, 'high'), _num(rows, 'low'), _num(rows, 'close')
    v, n, w = _num(rows, 'volume'), _num(rows, 'count'), _num(rows, 'vwap')
    for i in range(len(rows)):
        if (v[i] or 0) == 0 and (c[i] or 0) == 0:
            o[i] = h[i] = l[i] = c[i] = None
    df = pl.DataFrame({'timestamp': [str(r.get('timestamp', '')) for r in rows], 'open': o, 'high': h, 'low': l, 'close': c,
                       'volume': [int(x or 0) for x in v], 'count': [int(x or 0) for x in n], 'vwap': w},
                      schema={'timestamp': pl.Utf8, 'open': pl.Float64, 'high': pl.Float64, 'low': pl.Float64, 'close': pl.Float64,
                              'volume': pl.Int64, 'count': pl.Int64, 'vwap': pl.Float64})
    return df.with_columns(_ny_ts(df['timestamp']).alias('timestamp')).filter(pl.col('timestamp').is_not_null()).sort('timestamp')


def prints_frame(rows: list) -> pl.DataFrame:
    """index price rows → timestamp, price (0 = no print → null)"""
    p = [None if (x or 0) <= 0 else x for x in _num(rows, 'price')]
    df = pl.DataFrame({'timestamp': [str(r.get('timestamp', '')) for r in rows], 'price': p}, schema={'timestamp': pl.Utf8, 'price': pl.Float64})
    return df.with_columns(_ny_ts(df['timestamp']).alias('timestamp')).filter(pl.col('timestamp').is_not_null()).sort('timestamp')


def fetch_jobs(day: str) -> list[dict]:
    d = day.replace('-', '')
    win = {'start_time': '09:30:00', 'end_time': '16:00:00'}
    jobs = [dict(kind='chain', sym=s, path='/option/history/quote', params=dict(symbol=s, expiration=d, date=d, interval='1m', **win)) for s in FETCH_CHAINS]
    jobs += [dict(kind='under', sym=s, path='/stock/history/ohlc', params=dict(symbol=s, start_date=d, end_date=d, interval='1m', venue=STOCK_VENUE, **win)) for s in FETCH_UNDER]
    jobs += [dict(kind='index', sym=s, path='/index/history/price', params=dict(symbol=s, date=d, interval='1m', **win)) for s in FETCH_INDEX]
    return jobs


def fetch_theta(start: str, end: str, parquet_root: Path, base: str | None = None, force: bool = False, stream=sys.stderr,
                fetcher: ThetaFetch | None = None) -> dict:
    """Write each weekday's same-day chains (SPY, QQQ, SPXW), SPY/QQQ minute bars and SPX/VIX prints into the layout"""
    src = ParquetSource(parquet_root)
    th = fetcher or ThetaFetch(base or os.environ.get('THETA_BASE') or THETA_BASE)
    out = {'written': [], 'skipped': [], 'empty': [], 'failed': []}
    lock = threading.Lock()
    todo = []
    for day in weekdays(start, end):
        if day in R.HOLIDAYS:
            out['skipped'].append(f'{day} holiday')
            continue
        for j in fetch_jobs(day):
            f = src.file_for(j['kind'], j['sym'], day)
            if f.exists() and not force:
                out['skipped'].append(str(f.relative_to(src.root)))
                continue
            todo.append((day, j, f))

    def run(item):
        day, j, f = item
        status, rows, err = th.get(j['path'], j['params'])
        if err and status != 472:
            with lock:
                out['failed'].append({'file': str(f.relative_to(src.root)), 'error': err})
            return
        if not rows:
            with lock:
                out['empty'].append(str(f.relative_to(src.root)))
            return
        frame = {'chain': chain_frame, 'under': bars_frame, 'index': prints_frame}[j['kind']](rows)
        if j['kind'] in ('under', 'index'):
            frame = frame.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') == day)
        if not frame.height:
            with lock:
                out['empty'].append(str(f.relative_to(src.root)))
            return
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + '.tmp')
        frame.write_parquet(tmp, compression='zstd')
        os.replace(tmp, f)
        with lock:
            out['written'].append(str(f.relative_to(src.root)))
        if stream is not None:
            print(f'fetch-theta: {f.relative_to(src.root)} {frame.height} rows', file=stream, flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=THETA_MAX_IN_FLIGHT) as ex:
        list(ex.map(run, todo))
    out['calls'] = th.calls
    return out


# ---- the command line (paper_tracker.py hands --backtest and --fetch-theta here) ---------------------------------------------------------

def parquet_root_of(args) -> Path:
    r = getattr(args, 'parquet_root', None) or os.environ.get('PAPER_PARQUET_ROOT')
    if not r:
        raise SystemExit('--parquet-root (or PAPER_PARQUET_ROOT) names the stored Parquet layout: <root>/data_full/chains/…, <root>/data/underlying/…, <root>/data/index/…')
    return Path(r)


def run_cli(args) -> int:
    if not args.start or not args.end:
        print('--start and --end (YYYY-MM-DD) are needed', file=sys.stderr)
        return 2
    root = parquet_root_of(args)
    if args.fetch_theta:
        res = fetch_theta(args.start, args.end, root, force=args.force)
        print(json.dumps({k: (v if k == 'calls' else len(v)) for k, v in res.items()}))
        for x in res['failed']:
            print(f'FAILED {x["file"]}: {x["error"]}', file=sys.stderr)
        return 1 if res['failed'] else 0
    keys = tuple(k.strip() for k in (args.candidates or ','.join(T.DEFAULT_KEYS)).split(',') if k.strip())
    bad = [k for k in keys if k not in T.CANDIDATES]
    if bad:
        print(f'unknown candidate(s) {bad}: {", ".join(T.CANDIDATES)}', file=sys.stderr)
        return 2
    rroot = Path(args.backtest_data)
    try:
        res = replay(args.start, args.end, keys, root, rroot, live_root=Path(args.data))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else rroot / 'reports'
    build_report(rroot, keys, args.start, args.end, out, parquet_root=root, wall_seconds=res['seconds'])
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
    a = p.parse_args(argv)
    root = Path(a.backtest_data)
    out = Path(a.out) if a.out else root / 'reports'
    if a.mode == 'parity':
        parity(root, a.start, a.end, out, Path(a.parquet_root) if a.parquet_root else None)
    else:
        build_report(root, tuple(a.candidates.split(',')), a.start, a.end, out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
