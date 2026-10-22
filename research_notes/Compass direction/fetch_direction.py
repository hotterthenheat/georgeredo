#!/usr/bin/env python3
"""
fetch_direction.py — the option EOD fetch of PREREG_DIRECTION.md §7 (commit 38b11bf). Computes no return and prints no price.

    python3 -I fetch_direction.py expl          # the exploration set's events, in their seeded order, until the cut
    python3 -I fetch_direction.py hold          # the holdout's — refused unless out/screen.json says the screen passed
    python3 -I fetch_direction.py status

Per event that is formed up to the option stage (calendar, window, bars of P and R, the $50 M floor — inputs only):
  1. E1's option EOD, every expiry (store/<SYM>/<E1>__ALL.parquet)
  2. the exit session's option EOD of the one expiry chosen from (1) by its listed dates (store/<SYM>/<X>__<EXP>.parquet)
  3. per (name, month of E1): the 10th and 20th of the 20 full sessions before the month, every expiry (…__ALL.parquet)
A request answered with no rows leaves <file>.empty. Every answer is staged (.part), verified, then renamed into the store,
never over a file already there. The key is read from the secrets file inside this process and never printed or written.
Resumable: an event is done when its line is in store/_events_<set>.ndjson.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcommon as C  # noqa: E402

NY = ZoneInfo('America/New_York')
SECRETS = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/secrets/research.env')
BUDGET = {'expl': (3.0 * 3600, 0.6e9), 'hold': (4.0 * 3600, 1.0e9)}
MIN_FREE = 1.5e9
STAGE = C.STORE / '_staging'
LOG = C.STORE / '_requests.ndjson'


def red(s) -> str:
    s = str(s)
    v = os.environ.get('THETADATA_KEY') or ''
    if len(v) >= 4:
        s = s.replace(v, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9_\-]+', '[key]', s)


def log(*a):
    print(dt.datetime.now(NY).strftime('%m-%d %H:%M:%S'), *[red(x) for x in a], flush=True)


def load_key():
    for line in SECRETS.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            k = k.strip().removeprefix('export ').strip()
            if k == 'THETADATA_KEY':
                os.environ[k] = v.strip().strip('"').strip("'")
    if not os.environ.get('THETADATA_KEY'):
        raise SystemExit('no THETADATA_KEY in the secrets file')


_client = None


def client():
    global _client
    if _client is None:
        logging.getLogger('thetadata').setLevel(logging.ERROR)
        from thetadata import ThetaClient
        load_key()
        _client = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
        log('login ok')
    return _client


def gap_wait():
    while True:
        n = dt.datetime.now(NY)
        if n.hour == 0 or (n.hour == 1 and n.minute < 45):
            time.sleep(60)
            continue
        return


class Fetch:
    def __init__(self, split: str):
        self.split = split
        self.secs = 0.0
        self.bytes = 0
        self.req = 0
        self.t0 = time.time()

    def over(self) -> str | None:
        lim_s, lim_b = BUDGET[self.split]
        if self.secs >= lim_s:
            return f'fetch time {self.secs / 3600:.2f} h reached the {lim_s / 3600:.1f} h cut'
        if self.bytes >= lim_b:
            return f'stored {self.bytes / 1e9:.3f} GB reached the {lim_b / 1e9:.1f} GB cut'
        if shutil.disk_usage(str(C.STORE)).free < MIN_FREE:
            return 'free disk under 1.5 GB'
        return None

    def call(self, **kw):
        import grpc
        from thetadata.errors import NoDataFoundError
        c = client()
        delay = 2.0
        for attempt in range(8):
            gap_wait()
            t0 = time.time()
            try:
                df = c.option_history_eod(**kw)
                self.secs += time.time() - t0
                return df
            except NoDataFoundError:
                self.secs += time.time() - t0
                return None
            except grpc.RpcError as e:
                self.secs += time.time() - t0
                code = e.code() if hasattr(e, 'code') else None
                if code == grpc.StatusCode.UNAUTHENTICATED:
                    raise SystemExit('UNAUTHENTICATED — another login took the session; stopping')
                log('rpc error', code, 'retry', attempt)
            except Exception as e:  # noqa: BLE001
                self.secs += time.time() - t0
                log('error', type(e).__name__, red(str(e))[:200], 'retry', attempt)
            time.sleep(delay)
            delay = min(delay * 2, 120)
        raise RuntimeError('request failed 8 times')

    @staticmethod
    def shape(df: pl.DataFrame) -> pl.DataFrame:
        cols = df.columns
        if 'date' in cols:
            dcol = pl.col('date').cast(pl.Date) if df.schema['date'] != pl.Utf8 else pl.col('date').str.slice(0, 10).str.to_date()
        else:
            src = next(c for c in ('created', 'last_trade', 'timestamp') if c in cols)
            dcol = (pl.col(src).dt.convert_time_zone('America/New_York').dt.date() if isinstance(df.schema[src], pl.Datetime)
                    else pl.col(src).cast(pl.Utf8).str.slice(0, 10).str.to_date())
        ecol = (pl.col('expiration').cast(pl.Date) if df.schema['expiration'] != pl.Utf8
                else pl.col('expiration').str.replace_all('-', '').str.to_date('%Y%m%d'))
        rcol = pl.col('right').cast(pl.Utf8).str.slice(0, 1).str.to_uppercase()
        return df.select(dcol.alias('date'), ecol.alias('expiration'), pl.col('strike').cast(pl.Float64), rcol.alias('right'),
                         pl.col('bid').cast(pl.Float64).fill_nan(0.0).fill_null(0.0),
                         pl.col('ask').cast(pl.Float64).fill_nan(0.0).fill_null(0.0),
                         pl.col('volume').cast(pl.Float64).fill_nan(0).fill_null(0).cast(pl.Int64))

    @staticmethod
    def verify(x: pl.DataFrame, day: str, expiry: str | None) -> list[str]:
        probs = []
        if x.height == 0:
            probs.append('no rows')
            return probs
        if set(x['date'].cast(pl.String).unique().to_list()) != {day}:
            probs.append(f"dates {sorted(x['date'].cast(pl.String).unique().to_list())[:3]} not only {day}")
        if expiry is not None and set(x['expiration'].cast(pl.String).unique().to_list()) != {expiry}:
            probs.append('an expiration other than the one asked')
        if x.filter(pl.col('expiration').cast(pl.String) < day).height:
            probs.append('expirations before the date')
        if not set(x['right'].unique().to_list()) <= {'C', 'P'}:
            probs.append('a right other than C/P')
        if x.height != x.select('date', 'expiration', 'strike', 'right').n_unique():
            probs.append('duplicate (date, expiration, strike, right)')
        if x.filter((pl.col('bid') < 0) | (pl.col('ask') < 0) | (pl.col('strike') <= 0)).height:
            probs.append('a negative price or a non-positive strike')
        return probs

    def get(self, sym: str, day: str, expiry: str | None) -> str:
        """→ 'stored', 'empty' or 'failed'; never refetches"""
        what = 'ALL' if expiry is None else expiry
        p = C.store_path(sym, day, what)
        e = p.with_name(p.name + '.empty')
        if p.exists():
            return 'stored'
        if e.exists():
            return 'empty'
        d = dt.date.fromisoformat(day)
        t0 = time.time()
        df = self.call(start_date=d, end_date=d, symbol=sym, expiration='*' if expiry is None else dt.date.fromisoformat(expiry))
        self.req += 1
        rec = dict(sym=sym, day=day, what=what, secs=round(time.time() - t0, 2), raw_rows=None if df is None else df.height)
        p.parent.mkdir(parents=True, exist_ok=True)
        if df is None or df.height == 0:
            e.write_text('')
            rec['status'] = 'empty'
            self.logrec(rec)
            return 'empty'
        x = self.shape(df)
        probs = self.verify(x, day, expiry)
        if probs:
            q = STAGE / sym / p.name
            q.parent.mkdir(parents=True, exist_ok=True)
            x.write_parquet(q, compression='zstd')
            rec.update(status='failed', problems=probs)
            self.logrec(rec)
            return 'failed'
        tmp = STAGE / sym / (p.name + '.part')
        tmp.parent.mkdir(parents=True, exist_ok=True)
        x.write_parquet(tmp, compression='zstd')
        if p.exists():
            tmp.unlink()
            return 'stored'
        os.replace(tmp, p)
        b = p.stat().st_size
        self.bytes += b
        rec.update(status='stored', rows=x.height, bytes=b)
        self.logrec(rec)
        return 'stored'

    @staticmethod
    def logrec(rec):
        with open(LOG, 'a') as fh:
            fh.write(json.dumps(rec) + '\n')


def stored_bytes() -> int:
    return sum(f.stat().st_size for f in C.STORE.rglob('*.parquet') if '_staging' not in f.parts)


def run(split: str):
    if split == 'hold':
        sc = C.OUT / 'screen.json'
        if not sc.exists() or not json.loads(sc.read_text()).get('screen_pass'):
            raise SystemExit('the holdout is fetched only after the exploration screen passed (out/screen.json)')
    C.STORE.mkdir(parents=True, exist_ok=True)
    evs = C.event_lists()['holdout' if split == 'hold' else 'exploration']
    done_path = C.STORE / f'_events_{split}.ndjson'
    done = set()
    if done_path.exists():
        for line in done_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r['ticker'], r['report_date']))
    names = sorted({e['ticker'] for e in evs})
    log(split, len(evs), 'events,', len(names), 'names; loading bars')
    bars = {s: C.Bars(df) for s, df in C.load_bars(names).items()}
    log('bars for', len(bars), 'names')
    F = Fetch(split)
    # the budget counts what earlier runs of this split already spent
    if (C.STORE / f'_budget_{split}.json').exists():
        b0 = json.loads((C.STORE / f'_budget_{split}.json').read_text())
        F.secs, F.bytes = b0['secs'], b0['bytes']
    lo, hi = (C.HOLD_FROM, '2022-12-30') if split == 'hold' else (C.EXPL_FROM, C.EXPL_LAST)
    tiers_done = set()
    n_ev = 0
    stop = None
    with open(done_path, 'a') as out:
        for ev in evs:
            key = (ev['ticker'], ev['report_date'])
            if key in done:
                continue
            stop = F.over()
            if stop:
                break
            sym = ev['ticker']
            d = C.event_dates(ev['report_date'], ev['report_time'])
            rec = dict(ticker=sym, report_date=ev['report_date'], report_time=ev['report_time'], **{k: d.get(k) for k in ('R', 'P', 'E1', 'X')})
            if d['status'] != 'ok':
                rec['stage'] = d['status']
            elif d['X'] is None or d['E1'] < lo or d['X'] > hi:
                rec['stage'] = 'outside the set window'
            elif sym not in bars or bars[sym].c(d['P']) is None or bars[sym].c(d['R']) is None:
                rec['stage'] = 'no bar for P or R'
            else:
                okl, med, nd = bars[sym].liquid(d['P'])
                rec['liq'] = med
                if not okl:
                    rec['stage'] = 'under the $50 M floor' if med is not None else 'under 50 of 60 days of bars'
                else:
                    s1 = F.get(sym, d['E1'], None)
                    if s1 != 'stored':
                        rec['stage'] = f'entry chain {s1}'
                    else:
                        x = pl.read_parquet(C.store_path(sym, d['E1'], 'ALL'), columns=['expiration'])
                        exp = C.choose_expiry(d['E1'], [e.isoformat() for e in x['expiration'].unique().to_list()])
                        rec['expiry'] = exp
                        if exp is None:
                            rec['stage'] = 'no listed 31-60 expiry'
                        else:
                            s2 = F.get(sym, d['X'], exp)
                            rec['exit_file'] = s2
                            td = C.tier_days(d['E1'])
                            tk = (sym, d['E1'][:7])
                            if td and tk not in tiers_done:
                                rec['tier_files'] = [F.get(sym, t, None) for t in td]
                                tiers_done.add(tk)
                            rec['stage'] = 'fetched'
            out.write(json.dumps(rec) + '\n')
            out.flush()
            n_ev += 1
            if n_ev % 50 == 0:
                C.jdump(dict(secs=F.secs, bytes=F.bytes, requests=F.req), C.STORE / f'_budget_{split}.json')
                log(split, 'events', n_ev, 'requests', F.req, f'fetch {F.secs / 3600:.2f} h', f'{F.bytes / 1e6:.0f} MB',
                    f'free {shutil.disk_usage(str(C.STORE)).free / 1e9:.2f} GB')
    C.jdump(dict(secs=F.secs, bytes=F.bytes, requests=F.req, stop=stop, finished=stop is None), C.STORE / f'_budget_{split}.json')
    log(split, 'stopped:', stop or 'every event walked', '| events this run', n_ev, '| requests', F.req,
        f'| fetch {F.secs / 3600:.2f} h | {F.bytes / 1e6:.0f} MB')


if __name__ == '__main__':
    if sys.argv[1] == 'status':
        for s in ('expl', 'hold'):
            p = C.STORE / f'_budget_{s}.json'
            print(s, p.read_text() if p.exists() else '-')
    else:
        run(sys.argv[1])
