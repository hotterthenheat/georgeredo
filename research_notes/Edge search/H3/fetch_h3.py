#!/usr/bin/env python3
"""
fetch_h3.py — the option EOD fetch of PREREG_H3.md §6 (commit 001a136). Computes no return and prints no price.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B fetch_h3.py expl      # the exploration events, in their seeded order, until the cut
    PYTHONDONTWRITEBYTECODE=1 python3 -I -B fetch_h3.py hold      # refused unless out/screen_expl.json says the screen passed
    PYTHONDONTWRITEBYTECODE=1 python3 -I -B fetch_h3.py status

Pass A, per event formed up to the option stage (window, full P and R, bar at P, the floor — inputs only):
  1. P's option EOD, every expiry (store/<SYM>/<P>__ALL.parquet; a P file already in the PEAD store is read, not fetched)
  2. only when the entry is formed from (1): R's option EOD of the one chosen expiry (store/<SYM>/<R>__<EXP>.parquet)
Pass B, after every event: per (name, month of P) of a formed entry, the two tier sessions, every expiry (PEAD store first).
A request answered with no rows leaves <file>.empty. Every answer is staged (.part), verified, then renamed into the store,
never over a file already there. The key is read from the secrets file inside this process and never printed or written.
Exit code 2: a ThetaData quiet window (19:35-20:30 or 23:50-01:45 New York) began; the wrapper restarts the run after it.
Resumable: an event is done when its line is in store/_events_<set>.ndjson; a tier key when in store/_tiers_<set>.ndjson.
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
import h3common as H  # noqa: E402

D = H.D
NY = ZoneInfo('America/New_York')
SECRETS = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/secrets/research.env')
BUDGET = {'expl': (8.0 * 3600, 1.5e9), 'hold': (8.0 * 3600, 1.5e9)}
MIN_FREE = 1.5e9
STAGE = H.STORE / '_staging'
LOG = H.STORE / '_requests.ndjson'


class QuietWindow(Exception):
    pass


def red(s) -> str:
    s = str(s)
    v = os.environ.get('THETADATA_KEY') or ''
    if len(v) >= 4:
        s = s.replace(v, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9_\-]+', '[key]', s)


def log(*a):
    print(dt.datetime.now(NY).strftime('%m-%d %H:%M:%S'), *[red(x) for x in a], flush=True)


def quiet_now() -> bool:
    n = dt.datetime.now(NY)
    m = n.hour * 60 + n.minute
    return (19 * 60 + 35 <= m < 20 * 60 + 30) or m >= 23 * 60 + 50 or m < 1 * 60 + 45


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
        if quiet_now():
            raise QuietWindow()
        logging.getLogger('thetadata').setLevel(logging.ERROR)
        from thetadata import ThetaClient
        load_key()
        _client = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
        log('login ok')
    return _client


class Fetch:
    def __init__(self, split: str):
        self.split = split
        self.secs = 0.0
        self.bytes = 0
        self.req = 0

    def over(self) -> str | None:
        lim_s, lim_b = BUDGET[self.split]
        if self.secs >= lim_s:
            return f'fetch time {self.secs / 3600:.2f} h reached the {lim_s / 3600:.1f} h cut'
        if self.bytes >= lim_b:
            return f'stored {self.bytes / 1e9:.3f} GB reached the {lim_b / 1e9:.1f} GB cut'
        if shutil.disk_usage(str(H.STORE)).free < MIN_FREE:
            return 'free disk under 1.5 GB'
        return None

    def call(self, **kw):
        import grpc
        from thetadata.errors import NoDataFoundError
        delay = 2.0
        for attempt in range(8):
            if quiet_now():
                raise QuietWindow()
            c = client()
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
            return ['no rows']
        if set(x['date'].cast(pl.String).unique().to_list()) != {day}:
            probs.append('dates other than the one asked')
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

    def get(self, sym: str, day: str, expiry: str | None, peadok: bool = True) -> str:
        """→ 'stored', 'pead', 'empty' or 'failed'; never refetches, never writes over a file"""
        what = 'ALL' if expiry is None else expiry
        p = H.path(sym, day, what)
        e = p.with_name(p.name + '.empty')
        if p.exists():
            return 'stored'
        if e.exists():
            return 'empty'
        if (STAGE / sym / p.name).exists():
            return 'failed'
        if expiry is None and peadok and (H.PEAD_STORE / sym / p.name).exists():
            return 'pead'
        d = dt.date.fromisoformat(day)
        t0 = time.time()
        df = self.call(start_date=d, end_date=d, symbol=sym, expiration='*' if expiry is None else dt.date.fromisoformat(expiry))
        self.req += 1
        rec = dict(split=self.split, sym=sym, day=day, what=what, secs=round(time.time() - t0, 2),
                   raw_rows=None if df is None else df.height)
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


def save_budget(F: Fetch, split: str, **extra):
    H.jdump(dict(secs=F.secs, bytes=F.bytes, requests=F.req, **extra), H.STORE / f'_budget_{split}.json')


def run(split: str) -> int:
    if split == 'hold':
        sc = H.OUT / 'screen_expl.json'
        if not sc.exists() or not json.loads(sc.read_text()).get('screen_pass'):
            raise SystemExit('the holdout is fetched only after the exploration screen passed (out/screen_expl.json)')
    H.STORE.mkdir(parents=True, exist_ok=True)
    evs = H.event_lists()['holdout' if split == 'hold' else 'exploration']
    done_path = H.STORE / f'_events_{split}.ndjson'
    done = {}
    if done_path.exists():
        for line in done_path.read_text().splitlines():
            r = json.loads(line)
            done[(r['ticker'], r['report_date'])] = r
    F = Fetch(split)
    bp = H.STORE / f'_budget_{split}.json'
    if bp.exists():
        b0 = json.loads(bp.read_text())
        if b0.get('stop'):
            log(split, 'already stopped:', b0['stop'])
            return 0
    # the budget spent so far is the request log's own sum for this split (a killed run loses none of it); a line written
    # before the log carried its split (the first 25 requests, all exploration) counts as exploration
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            r = json.loads(line)
            if r.get('split', 'expl') == split:
                F.secs += r['secs']
                F.bytes += r.get('bytes', 0)
                F.req += 1
    # the window filter is calendar only; bars only for the names with an event in the window
    cand = []
    for ev in evs:
        d = H.ev_dates(ev['report_date'], ev['report_time'])
        cand.append((ev, d))
    names = sorted({ev['ticker'] for ev, d in cand if d['status'] == 'ok'})
    log(split, len(evs), 'events in the list,', sum(d['status'] == 'ok' for _, d in cand), 'in the window,', len(names), 'names; loading bars')
    bars = {s: D.Bars(df) for s, df in D.load_bars(names).items()}
    log('bars for', len(bars), 'names')
    stop = None
    n_ev = 0
    try:
        with open(done_path, 'a') as out:
            for ev, d in cand:
                key = (ev['ticker'], ev['report_date'])
                if key in done:
                    continue
                stop = F.over()
                if stop:
                    break
                sym = ev['ticker']
                rec = dict(ticker=sym, report_date=ev['report_date'], report_time=ev['report_time'], R=d.get('R'), P=d.get('P'))
                if d['status'] != 'ok':
                    rec['stage'] = d['status']
                elif sym not in bars or bars[sym].c(d['P']) is None:
                    rec['stage'] = 'no bar for P'
                else:
                    okl, med, nd = H.liquid_before(bars[sym], d['P'])
                    rec['liq'] = med
                    if not okl:
                        rec['stage'] = 'under the $50 M floor' if med is not None else 'under 50 of 60 days of bars'
                    else:
                        s1 = F.get(sym, d['P'], None)
                        rec['p_file'] = s1
                        if s1 not in ('stored', 'pead'):
                            rec['stage'] = f'entry chain {s1}'
                        else:
                            xp = H.read(H.find_all(sym, d['P']))
                            exp = H.choose_expiry(d['P'], d['R'], xp['expiration'].unique().to_list())
                            rec['expiry'] = exp
                            if exp is None:
                                rec['stage'] = 'no expiry after R within 14 days'
                            else:
                                e = H.entry(xp.filter(pl.col('expiration') == exp), bars[sym].c(d['P']))
                                if e['status'] != 'formed':
                                    rec['stage'] = e['status']
                                else:
                                    s2 = F.get(sym, d['R'], exp)
                                    rec['r_file'] = s2
                                    rec['stage'] = 'exit file failed verification' if s2 == 'failed' else 'formed'
                out.write(json.dumps(rec) + '\n')
                out.flush()
                done[key] = rec
                n_ev += 1
                if n_ev % 100 == 0:
                    save_budget(F, split)
                    log(split, 'events', n_ev, 'requests', F.req, f'fetch {F.secs / 3600:.2f} h', f'{F.bytes / 1e6:.0f} MB',
                        f'free {shutil.disk_usage(str(H.STORE)).free / 1e9:.2f} GB')
        if stop is None:
            log(split, 'pass A complete; pass B (tiers)')
            tdone_path = H.STORE / f'_tiers_{split}.ndjson'
            tdone = set()
            if tdone_path.exists():
                tdone = {tuple(json.loads(x)['key']) for x in tdone_path.read_text().splitlines()}
            want = []
            for r in done.values():
                if r.get('stage') == 'formed':
                    k = (r['ticker'], r['P'][:7])
                    if k not in want:
                        want.append(k)
            with open(tdone_path, 'a') as tout:
                for k in want:
                    if k in tdone:
                        continue
                    stop = F.over()
                    if stop:
                        break
                    td = D.tier_days(k[1] + '-15')
                    st = [F.get(k[0], t, None) for t in td] if td else []
                    tout.write(json.dumps(dict(key=list(k), days=list(td) if td else None, files=st)) + '\n')
                    tout.flush()
                    tdone.add(k)
            if stop:
                stop = 'pass B (tiers): ' + stop
    except QuietWindow:
        save_budget(F, split)
        log(split, 'quiet window: exiting; events this run', n_ev, 'requests', F.req, f'fetch {F.secs / 3600:.2f} h')
        return 2
    finished = stop is None
    save_budget(F, split, stop=stop, finished=finished)
    log(split, 'stopped:', stop or 'every event and tier walked', '| events this run', n_ev, '| requests', F.req,
        f'| fetch {F.secs / 3600:.2f} h | {F.bytes / 1e6:.0f} MB')
    return 0


if __name__ == '__main__':
    if sys.argv[1] == 'status':
        for s in ('expl', 'hold'):
            p = H.STORE / f'_budget_{s}.json'
            print(s, p.read_text() if p.exists() else '-')
    else:
        sys.exit(run(sys.argv[1]))
