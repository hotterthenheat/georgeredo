#!/usr/bin/env python3
"""Compass features study: the data fetch (frozen scope: scratchpad features_scope.md). One resumable fetcher, two processes.

    set -a; . $SP/secrets/research.env; set +a
    python3 -I fetch_features.py uw-smoke     # one live call per new parameter combination, the reuse import, then stops
    python3 -I fetch_features.py uw           # the UW fetch (reuse import first; resumes from what is on disk)
    python3 -I fetch_features.py theta        # the ThetaData fetch (waits out 00:00-01:45 New York; one SDK login)
    python3 -I fetch_features.py status       # prints STATUS.json

Everything is resumable: a UW item (route, ticker, date) is done when <date>.parquet, .empty, .oow or .refused exists under
$SP/features_data/uw/<route>/<ticker>/; a Theta item when its file is in the stored root ($SP/theta). Errors are not marked,
so a restart asks them again. No key is ever printed, logged or written (red() scrubs every text kept).
"""
from __future__ import annotations

import datetime as dt
import fcntl
import gzip
import json
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
OUT = SP / 'features_data'
UWROOT = OUT / 'uw'
STATUS = OUT / 'STATUS.json'
UWLOG = OUT / 'uw_log.ndjson'
STORED = SP / 'theta'
NY, UTC = ZoneInfo('America/New_York'), dt.timezone.utc
REPO = Path('/home/user/georgeredo')
MIN_FREE = 1.5e9
UW_BASE = 'https://api.unusualwhales.com'

UW_START, UW_END = '2023-11-21', '2026-10-21'
INDEX = ['SPY', 'QQQ', 'IWM', 'SPX']
SINGLES = ['AAPL', 'AMZN', 'AVGO', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'INTC', 'MU', 'META']

# hard caps a ticker-day (stated in the README)
FLOW_PAGES, FLOW_LIMIT = 40, 200          # 8,000 alerts >= $25K a ticker-day
DP_PAGES, DP_LIMIT, DP_FLOOR = 20, 500, 1_000_000
OI_LIMIT = 500
OI_PAGES = {'SPX': 60, 'SPY': 30, 'QQQ': 30, 'IWM': 30}


def red(s) -> str:
    s = str(s)
    for k in ('UW_API_TOKEN', 'THETADATA_KEY'):
        v = os.environ.get(k) or ''
        if len(v) >= 4:
            s = s.replace(v, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9_\-]+', '[key]', s)


def log(*a):
    print(dt.datetime.now(NY).strftime('%m-%d %H:%M:%S'), *[red(x) for x in a], flush=True)


def free_bytes() -> int:
    return shutil.disk_usage(str(SP)).free


def write_status(section: str, payload: dict) -> None:
    """STATUS.json holds one section per process; merged under a lock, replaced whole"""
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / '.status.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            cur = json.loads(STATUS.read_text()) if STATUS.exists() else {}
        except Exception:  # noqa: BLE001
            cur = {}
        cur[section] = payload
        cur['updated_ny'] = dt.datetime.now(NY).isoformat(timespec='seconds')
        tmp = STATUS.with_name('STATUS.json.part')
        tmp.write_text(red(json.dumps(cur, indent=1, default=str)))
        os.replace(tmp, STATUS)


def sessions(a: str, b: str) -> list[str]:
    """the calendar: the SPXW same-day chain files' dates (every session since 2022-05, half days included)"""
    d = STORED / 'data_full/chains/SPXW'
    return sorted(f.name[:10] for f in d.glob('*.parquet') if a <= f.name[:10] <= b and len(f.name) == 18)


def ny_midnight_utc(day: str) -> dt.datetime:
    return dt.datetime.fromisoformat(day).replace(tzinfo=NY).astimezone(UTC)


def iso_z(t: dt.datetime) -> str:
    return t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---- compact typing -------------------------------------------------------------------------------------------------------------

def _f(v):
    if v is None or v == '':
        return None
    try:
        x = float(v)
        return x if x == x and abs(x) != float('inf') else None
    except (TypeError, ValueError):
        return None


def _i(v):
    x = _f(v)
    return None if x is None else int(round(x))


def _t(v):
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return dt.datetime.fromtimestamp(v / 1000 if v > 1e11 else v, UTC)
    try:
        t = dt.datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        return (t if t.tzinfo else t.replace(tzinfo=UTC)).astimezone(UTC)
    except ValueError:
        return None


def _d(v):
    try:
        return dt.date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _b(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).lower() in ('true', '1', 't')


CONV = {'f': (_f, pl.Float64), 'i': (_i, pl.Int64), 's': (lambda v: None if v is None else str(v), pl.Utf8),
        'b': (_b, pl.Boolean), 't': (_t, pl.Datetime('us', 'UTC')), 'd': (_d, pl.Date),
        'j': (lambda v: None if v is None else json.dumps(v), pl.Utf8)}

GREEKS = [f'{g}_per_one_percent_move_{k}' for g in ('gamma', 'charm', 'vanna') for k in ('oi', 'vol', 'dir')]
SPECS = {
    'spot_exposures': dict(time='t', start_time='t', price='f', **{g: 'f' for g in GREEKS}),
    'greek_exposure_strike': dict(date='d', strike='f', call_gex='f', put_gex='f', call_delta='f', put_delta='f',
                                  call_charm='f', put_charm='f', call_vanna='f', put_vanna='f'),
    'gex_levels': dict(date='d', time='t', call_wall='f', put_wall='f', gamma_flip='f', gamma_magnet='f', nearby_flips='j',
                       source='s'),
    'net_prem_ticks': dict(date='d', tape_time='t', call_volume='i', put_volume='i', call_volume_ask_side='i',
                           call_volume_bid_side='i', put_volume_ask_side='i', put_volume_bid_side='i', net_call_premium='f',
                           net_put_premium='f', net_call_volume='i', net_put_volume='i', net_delta='f'),
    'flow_alerts': dict(id='s', created_at='t', start_time='t', end_time='t', ticker='s', option_chain='s', type='s',
                        strike='f', expiry='d', expiry_count='i', alert_rule='s', total_premium='f', total_ask_side_prem='f',
                        total_bid_side_prem='f', total_size='i', trade_count='i', volume='i', open_interest='i',
                        volume_oi_ratio='f', price='f', bid='f', ask='f', underlying_price='f', iv_start='f', iv_end='f',
                        has_sweep='b', has_floor='b', has_multileg='b', has_singleleg='b', all_opening_trades='b'),
    'market_tide': dict(timestamp='t', date='d', net_call_premium='f', net_put_premium='f', net_volume='i'),
    'nope': dict(timestamp='t', call_vol='i', put_vol='i', stock_vol='i', call_delta='f', put_delta='f', nope='f',
                 nope_fill='f', call_fill_delta='f', put_fill_delta='f'),
    'darkpool': dict(tracking_id='i', executed_at='t', trf_executed_at='t', price='f', size='i', premium='f', volume='i',
                     nbbo_bid='f', nbbo_ask='f', market_center='s', canceled='b', sale_cond_codes='s',
                     ext_hour_sold_codes='s', trade_code='s', trade_settlement='s'),
    'oi_chain': dict(option_symbol='s', open_interest='i', prev_oi='i', last_tape_time='t'),
}


def compact(route: str, rows: list[dict]) -> pl.DataFrame:
    spec = SPECS[route]
    cols = {}
    for k, ty in spec.items():
        fn, dtype = CONV[ty]
        cols[k] = pl.Series(k, [fn(r.get(k)) for r in rows], dtype=dtype)
    return pl.DataFrame(cols)


# ---- the UW item store ----------------------------------------------------------------------------------------------------------

MARKS = ('.parquet', '.empty', '.oow', '.refused')


def item_path(route: str, ticker: str, day: str) -> Path:
    return UWROOT / route / ticker / day


def item_done(route: str, ticker: str, day: str) -> str | None:
    base = item_path(route, ticker, day)
    for m in MARKS:
        if base.with_name(base.name + m).exists():
            return m
    return None


def atomic_write_bytes(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + '.part')
    tmp.write_bytes(data)
    os.replace(tmp, target)


def store_rows(route: str, ticker: str, day: str, rows: list[dict], meta: dict) -> int:
    base = item_path(route, ticker, day)
    if not rows:
        atomic_write_bytes(base.with_name(day + '.empty'), json.dumps(meta, default=str).encode())
        return 0
    df = compact(route, rows)
    target = base.with_name(day + '.parquet')
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + '.part')
    df.write_parquet(tmp, compression='zstd')
    os.replace(tmp, target)
    if meta.get('capped') or meta.get('note'):
        atomic_write_bytes(base.with_name(day + '.meta.json'), json.dumps(meta, default=str).encode())
    return target.stat().st_size


def mark(route: str, ticker: str, day: str, kind: str, meta: dict) -> None:
    atomic_write_bytes(item_path(route, ticker, day).with_name(day + kind), red(json.dumps(meta, default=str)).encode())


# ---- the UW client and limiter ----------------------------------------------------------------------------------------------------

class Limiter:
    """1 in flight 09:00-17:00 New York on weekdays (the owner's recorder shares the token), 2 otherwise, never more than
    3; at least 1.2 s between starts; a 429 pauses every worker (30 s doubling to 15 min, reset on success)"""

    def __init__(self):
        self.cv = threading.Condition()
        self.inflight = 0
        self.last = 0.0
        self.pause_until = 0.0
        self.backoff = 30.0

    @staticmethod
    def allowed() -> int:
        n = dt.datetime.now(NY)
        return 1 if (n.weekday() < 5 and 9 <= n.hour < 17) else 2

    def acquire(self):
        with self.cv:
            while True:
                now = time.time()
                if now < self.pause_until:
                    self.cv.wait(self.pause_until - now)
                    continue
                if self.inflight >= min(self.allowed(), 3):
                    self.cv.wait(1.0)
                    continue
                gap = self.last + 1.2 - now
                if gap > 0:
                    self.cv.wait(gap)
                    continue
                self.inflight += 1
                self.last = now
                return

    def release(self, hit429: bool = False):
        with self.cv:
            self.inflight -= 1
            if hit429:
                self.pause_until = max(self.pause_until, time.time() + self.backoff)
                self.backoff = min(900.0, self.backoff * 2)
            else:
                self.backoff = 30.0
            self.cv.notify_all()


LIM = Limiter()
_loglock = threading.Lock()


def uwlog(rec: dict) -> None:
    with _loglock:
        with open(UWLOG, 'a') as fh:
            fh.write(red(json.dumps(rec, default=str)) + '\n')


class UWError(Exception):
    def __init__(self, status, msg):
        super().__init__(f'{status}: {msg}')
        self.status, self.msg = status, msg


def uw_get(path: str, params: dict, route: str, ticker: str, day: str, page: int = 0):
    """one GET through the limiter, retried on 429 / 5xx / network (6 tries); returns (status, json). 4xx other than 429
    raise UWError (403 out-of-window is told apart by the caller)"""
    url = UW_BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    tok = os.environ.get('UW_API_TOKEN')
    if not tok:
        raise SystemExit('UW_API_TOKEN is not in the environment')
    for attempt in range(6):
        LIM.acquire()
        t0, status, body, nbytes, hit = time.time(), None, None, 0, False
        try:
            req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tok, 'Accept': 'application/json',
                                                       'User-Agent': 'compass-features-research'})
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
                status, nbytes = r.status, len(raw)
                body = json.loads(raw)
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                raw = e.read()
                nbytes = len(raw)
                body = json.loads(raw)
            except Exception:  # noqa: BLE001
                body = {'error': 'unreadable body'}
            hit = status == 429
        except Exception as e:  # noqa: BLE001
            status, body = 0, {'error': f'{type(e).__name__}: {e}'}
        finally:
            LIM.release(hit)
        ms = int((time.time() - t0) * 1000)
        nrows = len(body.get('data')) if isinstance(body, dict) and isinstance(body.get('data'), list) else None
        uwlog({'t': dt.datetime.now(UTC).isoformat(timespec='seconds'), 'route': route, 'ticker': ticker, 'date': day,
               'page': page, 'status': status, 'bytes': nbytes, 'ms': ms, 'rows': nrows,
               'path': path, 'params': {k: v for k, v in params.items()}})
        if status == 200:
            return status, body
        if status == 429 or status == 0 or (status and status >= 500):
            time.sleep(min(60, 2 ** attempt))
            continue
        raise UWError(status, red(json.dumps(body)[:300]))
    raise UWError(status or 0, 'retries exhausted: ' + red(json.dumps(body)[:200]))


# ---- the UW datasets ------------------------------------------------------------------------------------------------------------

def rows_of(body) -> list:
    d = body.get('data') if isinstance(body, dict) else body
    if d is None:
        return []
    if isinstance(d, dict):     # gex-levels: one row a date; a row with every level null is an empty answer
        return [d] if any(v not in (None, '', []) for k, v in d.items() if k not in ('date', 'source', 'time', 'ticker')) else []
    return list(d)


def fetch_simple(route: str, path: str, ticker: str, day: str, extra: dict | None = None):
    st, body = uw_get(path, dict(date=day, **(extra or {})), route, ticker, day)
    return rows_of(body), {'calls': 1}


def fetch_flow(route, ticker, day):
    start = ny_midnight_utc(day)
    end = ny_midnight_utc((dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat())
    cursor, seen, out, meta = end, set(), [], {'pages': 0}
    for page in range(FLOW_PAGES):
        _, body = uw_get('/api/option-trades/flow-alerts', dict(ticker_symbol=ticker, min_premium=25000, limit=FLOW_LIMIT,
                                                               newer_than=iso_z(start), older_than=iso_z(cursor)),
                         route, ticker, day, page)
        rows = rows_of(body)
        meta['pages'] += 1
        new = 0
        for r in rows:
            t = _t(r.get('created_at'))
            if t is not None and start <= t < end and r.get('id') not in seen:
                seen.add(r.get('id'))
                out.append(r)
                new += 1
        if len(rows) < FLOW_LIMIT:
            return out, meta
        oldest = min((_t(r.get('created_at')) for r in rows if _t(r.get('created_at'))), default=None)
        if oldest is None or oldest < start or new == 0:
            meta['note'] = 'stopped: no progress' if new == 0 else None
            return out, meta
        nxt = oldest.replace(microsecond=0) + dt.timedelta(seconds=1)   # inclusive of the boundary second; deduped by id
        cursor = nxt if nxt < cursor else oldest.replace(microsecond=0)
    meta['capped'] = f'{FLOW_PAGES} pages'
    return out, meta


def fetch_darkpool(route, ticker, day):
    start = ny_midnight_utc(day)
    end = ny_midnight_utc((dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat())
    cursor, seen, out, meta = end, set(), [], {'pages': 0, 'min_premium': DP_FLOOR}
    for page in range(DP_PAGES):
        _, body = uw_get(f'/api/darkpool/{ticker}', dict(date=day, min_premium=DP_FLOOR, limit=DP_LIMIT,
                                                          newer_than=iso_z(start), older_than=iso_z(cursor)),
                         route, ticker, day, page)
        rows = rows_of(body)
        meta['pages'] += 1
        new = 0
        for r in rows:
            t = _t(r.get('executed_at'))
            k = (r.get('tracking_id'), r.get('executed_at'), r.get('price'), r.get('size'))
            if t is not None and start <= t < end and k not in seen:
                seen.add(k)
                out.append(r)
                new += 1
        if len(rows) < DP_LIMIT:
            return out, meta
        oldest = min((_t(r.get('executed_at')) for r in rows if _t(r.get('executed_at'))), default=None)
        if oldest is None or oldest < start or new == 0:
            return out, meta
        nxt = oldest + dt.timedelta(seconds=1)
        cursor = nxt if nxt < cursor else oldest
    meta['capped'] = f'{DP_PAGES} pages'
    return out, meta


def fetch_oi(route, ticker, day):
    out, meta = [], {'pages': 0}
    for page in range(OI_PAGES.get(ticker, 30)):
        _, body = uw_get(f'/api/stock/{ticker}/option-contracts', dict(date=day, exclude_zero_oi_chains='true',
                                                                       limit=OI_LIMIT, page=page), route, ticker, day, page)
        rows = rows_of(body)
        meta['pages'] += 1
        out.extend(rows)
        if len(rows) < OI_LIMIT:
            return out, meta
    meta['capped'] = f'{OI_PAGES.get(ticker, 30)} pages'
    return out, meta


# route -> (fetch, tickers, first date the vendor serves (an empty on or after it is a gap))
def DATASETS():
    S = lambda r, p: (lambda route, t, d: fetch_simple(route, p.format(t=t), t, d))  # noqa: E731
    return [
        ('spot_exposures', S('spot_exposures', '/api/stock/{t}/spot-exposures'), INDEX, '2023-12-08'),
        ('greek_exposure_strike', S('greek_exposure_strike', '/api/stock/{t}/greek-exposure/strike'), INDEX, UW_START),
        ('gex_levels', S('gex_levels', '/api/stock/{t}/gex-levels'), INDEX, '2024-05-13'),
        ('net_prem_ticks', S('net_prem_ticks', '/api/stock/{t}/net-prem-ticks'), INDEX, UW_START),
        ('flow_alerts', fetch_flow, INDEX + ['SPXW'], UW_START),   # SPX's alerts are filed under SPX and SPXW
        ('market_tide', lambda route, t, d: fetch_simple(route, '/api/market/market-tide', 'market', d), ['market'], UW_START),
        ('nope', S('nope', '/api/stock/{t}/nope'), ['SPY', 'QQQ', 'IWM'], None),   # start bisected; SPX empty when SPY served (smoke)
        ('oi_chain', fetch_oi, INDEX, UW_START),
        ('darkpool', fetch_darkpool, ['SPY', 'QQQ', 'IWM'], UW_START),
    ]


def is_oow(e: UWError) -> bool:
    return e.status == 403 and 'historic' in (e.msg or '').lower()


# ---- reuse of what is on disk ---------------------------------------------------------------------------------------------------

def reuse_import() -> dict:
    """bt/cache (gex-levels, net-prem-ticks, spot-exposures, market-tide answered with date only), the recorder's
    2026-10-21 pass, and the inventory's probe answers -> the compact store. Idempotent: an item done is not touched."""
    cal = set(sessions(UW_START, UW_END))
    done = {'bt_cache': {}, 'recorder_2026-10-21': {}, 'probe': {}}
    rx = re.compile(r'^[0-9a-f]+_(?:stock_(SPY|QQQ|IWM|SPX)_(gex-levels|net-prem-ticks|spot-exposures)|market_(market-tide))'
                    r'_date-(\d{4}-\d{2}-\d{2})\.json\.gz$')
    rmap = {'gex-levels': 'gex_levels', 'net-prem-ticks': 'net_prem_ticks', 'spot-exposures': 'spot_exposures',
            'market-tide': 'market_tide'}
    for f in sorted((SP / 'bt/cache').iterdir()):
        m = rx.match(f.name)
        if not m:
            continue
        tk, r1, r2, day = m.groups()
        route, tk = rmap[r1 or r2], tk or 'market'
        if day not in cal or item_done(route, tk, day):
            continue
        try:
            with gzip.open(f, 'rt') as fh:
                body = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(body, dict) or 'error' in body:
            continue
        store_rows(route, tk, day, rows_of(body), {'reused': str(f.name)})
        done['bt_cache'][route] = done['bt_cache'].get(route, 0) + 1
        uwlog({'t': dt.datetime.now(UTC).isoformat(timespec='seconds'), 'route': route, 'ticker': tk, 'date': day,
               'status': 'reused', 'src': 'bt/cache'})
    rec = REPO / 'data_recorder'
    for sub, route, flt in [('net_prem_ticks', 'net_prem_ticks', None), ('flow_alerts', 'flow_alerts', None),
                            ('darkpool', 'darkpool', DP_FLOOR), ('chain', 'oi_chain', None)]:
        for tk in INDEX:
            f = rec / sub / tk / '2026-10-21.parquet'
            if not f.exists() or item_done(route, tk, '2026-10-21'):
                continue
            rows = pl.read_parquet(f).to_dicts()
            if flt:
                rows = [r for r in rows if (_f(r.get('premium')) or 0) >= flt]
            if route == 'flow_alerts' and tk == 'SPX':      # the recorder filed both roots under SPX; the fetch keeps them apart
                if not item_done(route, 'SPXW', '2026-10-21'):
                    store_rows(route, 'SPXW', '2026-10-21', [r for r in rows if r.get('ticker') == 'SPXW'], {'reused': str(f)})
                rows = [r for r in rows if r.get('ticker') != 'SPXW']
            store_rows(route, tk, '2026-10-21', rows, {'reused': str(f)})
            done['recorder_2026-10-21'][route] = done['recorder_2026-10-21'].get(route, 0) + 1
            uwlog({'t': dt.datetime.now(UTC).isoformat(timespec='seconds'), 'route': route, 'ticker': tk, 'date': '2026-10-21',
                   'status': 'reused', 'src': 'data_recorder'})
    probes = [('02_greek_exposure_strike', 'greek_exposure_strike', 'SPY', '2023-11-21'),
              ('05_spot_exposures_series', 'spot_exposures', 'SPY', '2023-12-08'),
              ('08_gex_levels_QQQ', 'gex_levels', 'QQQ', '2024-05-13'),
              ('13_net_prem_ticks', 'net_prem_ticks', 'SPY', '2023-11-21'),
              ('14_nope', 'nope', 'SPY', '2023-11-21'),
              ('15_market_tide', 'market_tide', 'market', '2023-11-21'),
              ('28_nope_recent', 'nope', 'SPY', '2026-10-21')]
    for name, route, tk, day in probes:
        f = SP / 'feature_inventory' / f'{name}.json'
        if not f.exists() or item_done(route, tk, day):
            continue
        d = json.loads(f.read_text())
        if d.get('status') != 200:
            continue
        body = d['body'] if not isinstance(d['body'], str) else json.loads(d['body'])
        store_rows(route, tk, day, rows_of(body), {'reused': f'feature_inventory/{name}.json'})
        done['probe'][route] = done['probe'].get(route, 0) + 1
        uwlog({'t': dt.datetime.now(UTC).isoformat(timespec='seconds'), 'route': route, 'ticker': tk, 'date': day,
               'status': 'reused', 'src': 'feature_inventory'})
    # what has been reused overall (counted off the markers, so a restart reports the same)
    tot = {}
    for f in (OUT / 'uw_log.ndjson',):
        if f.exists():
            for line in f.open():
                if '"reused"' in line:
                    r = json.loads(line)
                    k = f"{r['route']}<-{r.get('src')}"
                    tot[k] = tot.get(k, 0) + 1
    (UWROOT / '_reused.json').parent.mkdir(parents=True, exist_ok=True)
    (UWROOT / '_reused.json').write_text(json.dumps({'this_run': done, 'all_runs': tot}, indent=1))
    return done


# ---- NOPE's start, bisected (<= 6 calls, each kept as an item) ----------------------------------------------------------------

def nope_start(cal: list[str]) -> str:
    f = UWROOT / 'nope' / '_start.json'
    if f.exists():
        return json.loads(f.read_text())['fetch_from']
    lo, hi = 0, len(cal) - 1            # lo empty (probe 14), hi served (probe 28)
    calls = []
    for _ in range(6):
        if hi - lo <= 1:
            break
        mid = (lo + hi) // 2
        day = cal[mid]
        m = item_done('nope', 'SPY', day)
        if m is None:
            try:
                rows, _ = fetch_simple('nope', '/api/stock/SPY/nope', 'SPY', day)
                store_rows('nope', 'SPY', day, rows, {'bisect': True})
                m = '.parquet' if rows else '.empty'
            except UWError as e:
                m = '.oow' if is_oow(e) else '.refused'
                mark('nope', 'SPY', day, m, {'error': str(e)})
            calls.append((day, m))
        if m == '.parquet':
            hi = mid
        else:
            lo = mid
    out = {'fetch_from': cal[lo + 1], 'last_empty_seen': cal[lo], 'first_served_seen': cal[hi], 'bisect_calls': calls,
           'note': 'SPY bisected; every date from fetch_from is asked for every name; dates before it are inferred empty, not asked'}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1))
    log('nope start', out)
    return out['fetch_from']


# ---- the UW run -----------------------------------------------------------------------------------------------------------------

class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.d = {}
        self.items = 0
        self.last_error = None
        self.t0 = time.time()

    def ds(self, route):
        return self.d.setdefault(route, dict(total=0, done_before=0, done=0, empty=0, gaps=0, oow=0, refused=0, errors=0,
                                             capped=0, bytes=0, calls=0, secs=0.0, skipped=0))


def uw_run(smoke: bool = False) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cal = sessions(UW_START, UW_END)
    log('calendar', len(cal), 'sessions', cal[0], '->', cal[-1], 'free', f'{free_bytes() / 1e9:.2f} GB')
    log('reuse', reuse_import())
    if smoke:
        return uw_smoke(cal)
    st = Stats()
    plan = []
    for route, fn, tickers, served_from in DATASETS():
        dsx = st.ds(route)
        days = cal
        if route == 'spot_exposures':
            days = [d for d in cal if d >= '2023-12-08']
        for d in days:
            for t in tickers:
                dsx['total'] += 1
                if item_done(route, t, d):
                    dsx['done_before'] += 1
                else:
                    plan.append((route, fn, t, d, served_from))
    log('plan', {r: (v['total'], v['done_before']) for r, v in st.d.items()}, 'items to ask', len(plan))
    refused_streak: dict = {}
    nope_from = None
    idx = [0]
    stop = {'why': None}
    qlock = threading.Lock()

    def next_item():
        with qlock:
            while idx[0] < len(plan):
                it = plan[idx[0]]
                idx[0] += 1
                return it
            return None

    def status(final=False):
        with st.lock:
            per = {}
            rate_left = []
            for r, v in st.d.items():
                n = v['done'] + v['empty'] + v['oow'] + v['refused'] + v['skipped']
                left = v['total'] - v['done_before'] - n - v['errors']
                sp = v['secs'] / max(1, n) if n else None
                per[r] = dict(v, finished=v['done_before'] + n, remaining=max(0, left),
                              secs_per_item=round(sp, 2) if sp else None, secs=round(v['secs']))
                rate_left.append((r, left, sp))
            # ETA: datasets run in order; an untouched dataset is estimated at the slowest measured simple rate
            known = [sp for _, _, sp in rate_left if sp]
            dflt = (sorted(known)[len(known) // 2] if known else 2.0)
            eta, acc = {}, 0.0
            for r, left, sp in rate_left:      # secs_per_item is a worker's; the limiter runs allowed() at once
                acc += max(0, left) * (sp or dflt) / Limiter.allowed()
                eta[r] = (dt.datetime.now(NY) + dt.timedelta(seconds=acc)).isoformat(timespec='minutes')
            payload = dict(pid=os.getpid(), state='finished' if final else ('stopped: ' + stop['why'] if stop['why'] else 'running'),
                           started=dt.datetime.fromtimestamp(st.t0, NY).isoformat(timespec='seconds'), items_this_run=st.items,
                           in_flight_rule='1 in 09:00-17:00 NY weekdays, else 2; >=1.2 s between starts',
                           datasets=per, eta_finish_by_dataset=eta, free_disk_gb=round(free_bytes() / 1e9, 2),
                           last_error=st.last_error, nope_from=nope_from)
        write_status('uw', payload)

    def worker():
        nonlocal nope_from
        while not stop['why']:
            it = next_item()
            if it is None:
                return
            route, fn, t, d, served_from = it
            if free_bytes() < MIN_FREE:
                stop['why'] = f'free disk under {MIN_FREE / 1e9} GB'
                return
            dsx = st.ds(route)
            if route == 'nope':
                with qlock:
                    if nope_from is None:
                        nope_from = nope_start(cal)
                if d < nope_from:
                    with st.lock:
                        dsx['skipped'] += 1
                    continue
                served_from = nope_from
            if item_done(route, t, d):
                with st.lock:
                    dsx['skipped'] += 1
                continue
            if refused_streak.get((route, t), 0) >= 3:
                with st.lock:
                    dsx['skipped'] += 1
                continue
            t0 = time.time()
            try:
                rows, meta = fn(route, t, d)
                nb = store_rows(route, t, d, rows, dict(meta, asked_at=dt.datetime.now(UTC).isoformat(timespec='seconds')))
                with st.lock:
                    if rows:
                        dsx['done'] += 1
                        dsx['bytes'] += nb
                    else:
                        dsx['empty'] += 1
                        if served_from and d >= served_from:
                            dsx['gaps'] += 1
                            uwlog({'route': route, 'ticker': t, 'date': d, 'status': 'gap', 'note': 'empty inside the served span'})
                    dsx['capped'] += 1 if meta.get('capped') else 0
                    dsx['calls'] += meta.get('pages', meta.get('calls', 1))
                refused_streak[(route, t)] = 0
            except UWError as e:
                with st.lock:
                    if is_oow(e):
                        mark(route, t, d, '.oow', {'error': str(e)})
                        dsx['oow'] += 1
                    elif e.status in (400, 403, 404, 422):
                        mark(route, t, d, '.refused', {'error': str(e)})
                        dsx['refused'] += 1
                        refused_streak[(route, t)] = refused_streak.get((route, t), 0) + 1
                    else:
                        dsx['errors'] += 1
                    st.last_error = f'{route} {t} {d}: {e}'
            except Exception as e:  # noqa: BLE001
                with st.lock:
                    dsx['errors'] += 1
                    st.last_error = red(f'{route} {t} {d}: {type(e).__name__}: {e}')
            with st.lock:
                dsx['secs'] += time.time() - t0
                st.items += 1
                n = st.items
            if n % 50 == 0:
                status()
                log('progress', n, route, t, d)

    status()
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    status(final=not stop['why'])
    log('uw done' if not stop['why'] else 'uw STOPPED: ' + stop['why'])
    return 0 if not stop['why'] else 2


def uw_smoke(cal) -> int:
    """the new parameter combinations, one live call each (the inventory's probes already proved the routes)"""
    res = {}

    def one(name, path, params, route='smoke', tk='-', day='-'):
        try:
            _, body = uw_get(path, params, route, tk, day)
            rows = rows_of(body)
            res[name] = {'rows': len(rows), 'first': rows[0] if rows else None, 'last': rows[-1] if rows else None}
        except UWError as e:
            res[name] = {'error': str(e)}
        return res[name]

    r = one('spx_spot_exposures', '/api/stock/SPX/spot-exposures', {'date': '2024-06-03'})
    r = one('spx_greek_strike', '/api/stock/SPX/greek-exposure/strike', {'date': '2024-06-03'})
    r = one('flow_alerts_SPX_p0', '/api/option-trades/flow-alerts',
            dict(ticker_symbol='SPX', min_premium=25000, limit=200, newer_than='2024-06-03T04:00:00Z', older_than='2024-06-04T04:00:00Z'))
    r = one('darkpool_min_premium', '/api/darkpool/SPY', dict(date='2024-06-03', min_premium=DP_FLOOR, limit=500,
                                                             newer_than='2024-06-03T04:00:00Z', older_than='2024-06-04T04:00:00Z'))
    if 'error' not in r:
        allp = [_f(x.get('premium')) for x in ([r['first'], r['last']] if r['first'] else [])]
        r['premium_floor_honoured_first_last'] = allp
    r = one('oi_chain_dated_p0', '/api/stock/SPY/option-contracts', dict(date='2024-06-03', exclude_zero_oi_chains='true', limit=500, page=0))
    r = one('nope_SPX', '/api/stock/SPX/nope', {'date': '2026-10-21'})
    # reused answers compared with a fresh one
    for route, path, tk, day in [('spot_exposures', '/api/stock/SPY/spot-exposures', 'SPY', '2026-08-05'),
                                 ('gex_levels', '/api/stock/SPY/gex-levels', 'SPY', '2024-08-02')]:
        f = item_path(route, tk, day).with_name(day + '.parquet')
        _, body = uw_get(path, {'date': day}, 'smoke', tk, day)
        new = compact(route, rows_of(body))
        old = pl.read_parquet(f) if f.exists() else None
        res[f'reuse_check_{route}'] = {'cached_rows': None if old is None else old.height, 'fresh_rows': new.height,
                                       'equal': (old is not None and old.equals(new))}
    print(red(json.dumps(res, indent=1, default=str)[:12000]))
    (OUT / 'uw_smoke.json').write_text(red(json.dumps(res, indent=1, default=str)))
    return 0


# ================================================================================================================================
# ThetaData (SDK)
# ================================================================================================================================

FWD = REPO / 'research_notes/Compass phase 3/forward_2026-10-12_2026-10-21'
TSTG = OUT / 'theta_staging'                 # the staging root (the stored layout below it)
TMAN = OUT / 'theta_manifest.ndjson'
NEW_DAYS = ('2026-10-12', '2026-10-21')
EOD_COLS = {'date': pl.Date, 'expiration': pl.Date, 'strike': pl.Float64, 'right': pl.Utf8, 'open': pl.Float32,
            'high': pl.Float32, 'low': pl.Float32, 'close': pl.Float32, 'volume': pl.Int64, 'count': pl.Int64,
            'bid': pl.Float32, 'ask': pl.Float32, 'bid_size': pl.Int64, 'ask_size': pl.Int64}
FC = STORED / 'fetch_cache'


def tman(rec: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    rec = dict(rec, t=dt.datetime.now(UTC).isoformat(timespec='seconds'))
    with open(TMAN, 'a') as fh:
        fh.write(red(json.dumps(rec, default=str)) + '\n')


def theta_gap_wait():
    """never ask Theta between 00:00 and 01:45 New York"""
    while True:
        n = dt.datetime.now(NY)
        if n.hour == 0 or (n.hour == 1 and n.minute < 45):
            until = n.replace(hour=1, minute=45, second=30, microsecond=0)
            log('inside Theta\'s 00:00-01:45 gap; sleeping until', until.strftime('%H:%M:%S'))
            write_status('theta', {'pid': os.getpid(), 'state': f'waiting for 01:45 New York (until {until.isoformat()})'})
            time.sleep(max(5, (until - n).total_seconds()))
            continue
        return


def weeks(a: str, b: str) -> list[tuple[str, str, list]]:
    """Mon-Fri weeks of the calendar's sessions in [a, b], named by their first and last session (the stored naming)"""
    out, cur = [], {}
    for d in sessions(a, b):
        key = dt.date.fromisoformat(d).isocalendar()[:2]
        cur.setdefault(key, []).append(d)
    for k in sorted(cur):
        ds = cur[k]
        out.append((ds[0], ds[-1], ds))
    return out


def covered(root_dir: Path) -> set:
    """the dates an eod_all folder's files already span (by their names)"""
    s = set()
    if root_dir.is_dir():
        for f in root_dir.glob('*__*.parquet'):
            a, b = f.name[:10], f.name[12:22]
            s.update(d for d in sessions(a, b))
    return s


class Theta:
    def __init__(self):
        sys.path.insert(0, str(REPO / 'scripts'))
        sys.path.insert(0, str(FWD))
        import sdk_fetch as F  # noqa: E402  (its calls, shaping, one() and its single login)
        import paper_backtest as B  # noqa: E402
        self.F, self.B = F, B
        self.lock = threading.Lock()
        self.stats = {}
        self.last_error = None
        self.t0 = time.time()
        self.workers = 1
        self.notes = {}

    def ds(self, k):
        return self.stats.setdefault(k, dict(total=0, done_before=0, done=0, empty=0, errors=0, bytes=0, secs=0.0))

    def status(self, state='running', eta=None):
        with self.lock:
            per = {}
            for k, v in self.stats.items():
                n = v['done'] + v['empty'] + v['errors']
                left = v['total'] - v['done_before'] - n
                per[k] = dict(v, secs=round(v['secs']), remaining=max(0, left),
                              secs_per_item=round(v['secs'] / n, 2) if n else None)
            payload = dict(pid=os.getpid(), state=state, workers=self.workers, datasets=per, notes=self.notes,
                           free_disk_gb=round(free_bytes() / 1e9, 2), last_error=self.last_error, eta=eta,
                           started=dt.datetime.fromtimestamp(self.t0, NY).isoformat(timespec='seconds'))
        write_status('theta', payload)

    def client(self):
        return self.F.client()

    def call(self, fn, *a, **kw):
        """one SDK request with sdk_fetch's retry rules; NoDataFound -> None"""
        import grpc
        from thetadata.errors import NoDataFoundError
        delay = 2.0
        for attempt in range(8):
            theta_gap_wait()
            try:
                return fn(*a, **kw)
            except NoDataFoundError:
                return None
            except grpc.RpcError as e:
                code = e.code() if hasattr(e, 'code') else None
                det = red(getattr(e, 'details', lambda: '')())
                if code == grpc.StatusCode.UNAUTHENTICATED:
                    raise SystemExit(red(f'UNAUTHENTICATED — another login took the key\'s session; stopping: {det[:160]}'))
                if attempt < 7:
                    time.sleep(delay)
                    delay = min(30.0, delay * 2)
                    continue
                raise RuntimeError(red(f'{code}: {det[:200]}'))
            except Exception as e:  # noqa: BLE001
                if attempt < 3:
                    time.sleep(delay)
                    delay = min(30.0, delay * 2)
                    continue
                raise RuntimeError(red(f'{type(e).__name__}: {e}')[:240])

    # ---- shaping --------------------------------------------------------------------------------------------------------------
    def shape_chain_exp(self, df, sym, day):
        """sdk_fetch.shape's chain, but NaN kept as NaN: the stored fetch_cache/chains_exp files hold NaN for no quote"""
        out = df.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
        out = out.select(self.F.CHAIN_COLS).with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32))
        out = out.with_columns(pl.col('timestamp').dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
        return out.sort(['strike', 'right', 'timestamp'])

    def shape_under(self, df, day):
        out = self.F.norm_ts(df.select(df.columns)).sort('timestamp')
        return out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') == day)

    def shape_eod(self, df):
        """the SDK's EOD frame -> fetch_cache/eod_all's 14 columns and dtypes; NaN prices -> 0 (the stored convention:
        close 0 where nothing traded), counted"""
        cols = df.columns
        if 'date' in cols:
            dcol = pl.col('date').cast(pl.Date) if df.schema['date'] != pl.Utf8 else pl.col('date').str.slice(0, 10).str.to_date()
        else:
            src = next(c for c in ('created', 'last_trade', 'timestamp') if c in cols)
            dcol = pl.col(src).dt.convert_time_zone('America/New_York').dt.date() if isinstance(df.schema[src], pl.Datetime) else pl.col(src).cast(pl.Utf8).str.slice(0, 10).str.to_date()
        ecol = pl.col('expiration').cast(pl.Date) if df.schema['expiration'] != pl.Utf8 else pl.col('expiration').str.replace_all('-', '').str.to_date('%Y%m%d')
        rcol = pl.col('right').cast(pl.Utf8).str.slice(0, 1).str.to_uppercase()
        sel = [dcol.alias('date'), ecol.alias('expiration'), pl.col('strike').cast(pl.Float64), rcol.alias('right')]
        nan = 0
        for c in ('open', 'high', 'low', 'close', 'bid', 'ask'):
            nan += int(df[c].cast(pl.Float64).is_nan().sum() + df[c].null_count())
            sel.append(pl.col(c).cast(pl.Float64).fill_nan(0.0).fill_null(0.0).cast(pl.Float32))
        for c in ('volume', 'count', 'bid_size', 'ask_size'):
            sel.append(pl.col(c).cast(pl.Float64).fill_nan(0).fill_null(0).cast(pl.Int64))
        out = df.select(sel)
        return out, nan

    # ---- checks -------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def norm_files(folder: Path, before: str, n=20, pattern='*.parquet'):
        fs = sorted(f for f in folder.glob(pattern) if f.name[:10] < before)
        return fs[-n:]

    def check_chain_exp(self, out, sym, day):
        import numpy as np
        fs = self.norm_files(FC / 'chains_exp' / sym, day)
        vals = []
        for f in fs:
            c = pl.read_parquet(f, columns=['strike'])
            vals.append((c['strike'].n_unique(), c.height, float(c['strike'].median())))
        norm = {'strikes': float(np.median([v[0] for v in vals])), 'rows': float(np.median([v[1] for v in vals])),
                'strike_mid': float(np.median([v[2] for v in vals]))} if vals else {}
        st, ck, probs = self.B.validate_frame('chain', sym, day, out, norm, self.B.session_of(day))
        late = out.filter(pl.col('timestamp').dt.hour() * 60 + pl.col('timestamp').dt.minute() > 570)
        nanq = int(late['bid'].is_nan().sum())
        ck['nan_after_0930'] = nanq
        if nanq > 0.02 * max(1, late.height):
            probs.append(f'{nanq} rows after 09:30 with no quote (NaN)')
        ref = pl.read_parquet(fs[-1]) if fs else None
        if ref is not None and ref.schema != out.schema:
            probs.append(f'schema differs from the stored {fs[-1].name}')
        return (not probs), ck, probs

    def check_under(self, out, folder: Path, sym, day):
        import numpy as np
        fs = self.norm_files(folder, day)
        vals = []
        for f in fs:
            b = pl.read_parquet(f, columns=['close', 'volume'])
            if b['close'].drop_nulls().len() >= 30:
                vals.append((int(b['volume'].sum()), float(b['close'].drop_nulls().median())))
        norm = {'volume': float(np.median([v[0] for v in vals])), 'price': float(np.median([v[1] for v in vals]))} if vals else {}
        st, ck, probs = self.B.validate_frame('under', sym, day, out, norm, self.B.session_of(day))
        ref = pl.read_parquet(fs[-1]) if fs else None
        if ref is not None and ref.schema != out.schema:
            probs.append(f'schema differs from the stored {fs[-1].name}: {dict(out.schema)}')
        return (not probs), ck, probs

    def check_eod(self, out, folder: Path, w0, w1, days):
        probs, ck = [], {'rows': out.height}
        want = {dt.date.fromisoformat(d) for d in days}
        got = set(out['date'].unique().to_list())
        if got != want:
            probs.append(f'dates {sorted(str(x) for x in got)[:6]} != the week\'s sessions {sorted(days)}')
        dups = out.height - out.select('date', 'expiration', 'strike', 'right').n_unique()
        ck['duplicates'] = dups
        if dups:
            probs.append(f'{dups} duplicate (date, expiration, strike, right)')
        if set(out['right'].unique().to_list()) - {'C', 'P'}:
            probs.append('rights other than C/P')
        if out.filter(pl.col('expiration') < pl.col('date')).height:
            probs.append('expirations before the date')
        if out.select((pl.col('bid') < 0) | (pl.col('ask') < 0) | (pl.col('close') < 0)).to_series().sum():
            probs.append('negative prices')
        if dict(out.schema) != EOD_COLS:
            probs.append(f'schema differs from eod_all: {dict(out.schema)}')
        prev = self.norm_files(folder, w0, n=8, pattern='*__*.parquet')
        if prev:
            import numpy as np
            per_day = [pl.read_parquet(f, columns=['date']).height / max(1, pl.read_parquet(f, columns=['date'])['date'].n_unique()) for f in prev]
            nm = float(np.median(per_day))
            ck['rows_per_day'], ck['norm_rows_per_day'] = round(out.height / max(1, len(days))), round(nm)
            if out.height / max(1, len(days)) < 0.5 * nm:
                probs.append(f'rows a day {out.height / max(1, len(days)):.0f} under half the norm {nm:.0f}')
        return (not probs), ck, probs

    def place_new(self, staged: Path, target: Path) -> str:
        """merge without overwriting: placed, identical, or refused (a different file there)"""
        if target.exists():
            return 'identical' if self.B.sha256_of(target) == self.B.sha256_of(staged) else 'exists'
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + '.part')
        shutil.copyfile(staged, tmp)
        os.replace(tmp, target)
        return 'placed'

    # ---- one job ---------------------------------------------------------------------------------------------------------------
    def job(self, key, kind, sym, a, b=None, days=None, max_dte=None):
        """fetch -> shape -> stage -> verify -> place (never over a stored file). Returns 'done' / 'empty' / 'error'."""
        if free_bytes() < MIN_FREE:
            raise SystemExit(f'free disk under {MIN_FREE / 1e9} GB')
        dsx = self.ds(key)
        c = self.client()
        t0 = time.time()
        if kind == 'chain_exp':
            rel = f'fetch_cache/chains_exp/{sym}/{a}__{a}.parquet'
            D = dt.date.fromisoformat(a)
            df = self.call(c.option_history_quote, symbol=sym, expiration=D, interval='1m', date=D, strike='*', right='both')
        elif kind == 'under_fc':
            rel = f'fetch_cache/underlying/{sym}/{a}.parquet'
            df = self.call(c.stock_history_ohlc, symbol=sym, interval='1m', date=dt.date.fromisoformat(a))
        else:   # eod week
            rel = f'fetch_cache/eod_all/{sym}/{a}__{b}.parquet'
            kw = dict(start_date=dt.date.fromisoformat(a), end_date=dt.date.fromisoformat(b), symbol=sym, expiration='*')
            if max_dte:
                kw['max_dte'] = max_dte
            df = self.call(c.option_history_eod, **kw)
        secs = time.time() - t0
        rec = {'dataset': key, 'file': rel, 'request_secs': round(secs, 2), 'raw_rows': None if df is None else df.height}
        if df is None or df.height == 0:
            rec['status'] = 'empty'
            tman(rec)
            with self.lock:
                dsx['empty'] += 1
                dsx['secs'] += secs
            return 'empty'
        try:
            if kind == 'chain_exp':
                out = self.shape_chain_exp(df, sym, a)
                ok, ck, probs = self.check_chain_exp(out, sym, a)
            elif kind == 'under_fc':
                out = self.shape_under(df, a)
                ok, ck, probs = self.check_under(out, FC / 'underlying' / sym, sym, a)
            else:
                out, nan = self.shape_eod(df)
                ok, ck, probs = self.check_eod(out, FC / 'eod_all' / sym, a, b, days)
                ck['nan_or_null_prices_to_0'] = nan
                if max_dte:
                    ck['max_dte'] = max_dte
            staged = TSTG / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            tmp = staged.with_name(staged.name + '.part')
            out.write_parquet(tmp, compression='zstd')
            os.replace(tmp, staged)
            rec.update(rows=out.height, bytes=staged.stat().st_size, checks=ck, problems=probs)
            if ok:
                how = self.place_new(staged, STORED / rel)
                rec['placed'] = how
                if how in ('placed', 'identical'):
                    staged.unlink()
                    rec['status'] = 'ok'
                else:
                    rec['status'] = 'FAILED: a different stored file is there (not overwritten)'
            else:
                rec['status'] = 'FAILED verify (kept in staging)'
        except Exception as e:  # noqa: BLE001
            rec['status'] = red(f'FAILED shape: {type(e).__name__}: {e}')[:300]
            rec['raw_schema'] = {k: str(v) for k, v in df.schema.items()}
        tman(rec)
        with self.lock:
            dsx['secs'] += secs
            if rec['status'] == 'ok':
                dsx['done'] += 1
                dsx['bytes'] += rec.get('bytes', 0)
                return 'done'
            dsx['errors'] += 1
            self.last_error = f"{rel}: {rec['status']} {'; '.join(rec.get('problems') or [])}"[:400]
        log(rec['status'], rel, rec.get('problems'))
        return 'error'


def theta_run() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    theta_gap_wait()
    T = Theta()
    F, B = T.F, T.B
    run = dt.datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    T.client()                                   # ONE login for the run
    new_days = [d for d in sessions(*NEW_DAYS)]
    requests: list = []

    # 1. the smallest live test: IWM 2026-10-12 bars, schema against the stored IWM bars
    st = 'ok' if (STORED / B.rel_of('under', 'IWM', new_days[0])).exists() else F.one(TSTG, 'under', 'IWM', new_days[0], run, requests)
    f = TSTG / B.rel_of('under', 'IWM', new_days[0])
    if f.exists():
        new, ref = pl.read_parquet(f), pl.read_parquet(STORED / B.rel_of('under', 'IWM', '2026-10-09'))
        T.notes['smoke_iwm_bars'] = dict(status=st, schema_equal=new.schema == ref.schema, rows=new.height, ref_rows=ref.height,
                                         first=str(new['timestamp'][0]), last=str(new['timestamp'][-1]))
        log('smoke IWM 2026-10-12 bars', T.notes['smoke_iwm_bars'])
        if new.schema != ref.schema or st != 'ok':
            T.status('stopped: the smoke test failed (schema or validation)')
            return 1
    else:
        T.notes['smoke_iwm_bars'] = {'status': st, 'note': 'already merged' if st == 'ok' else 'not staged'}
        if st != 'ok':
            T.status('stopped: the smoke test failed')
            return 1

    # 2. IWM bars + same-day chains 2026-10-12 -> 21 into the stored layout (sdk_fetch.one: stage, validate; then merge)
    for kind in ('under', 'chain'):
        key = f'iwm_{kind}'
        dsx = T.ds(key)
        for d in new_days:
            dsx['total'] += 1
            if (STORED / B.rel_of(kind, 'IWM', d)).exists():
                dsx['done_before'] += 1
                continue
            if (TSTG / B.rel_of(kind, 'IWM', d)).exists():
                dsx['done'] += 1
                continue
            t0 = time.time()
            theta_gap_wait()
            s = F.one(TSTG, kind, 'IWM', d, run, requests)
            dsx['secs'] += time.time() - t0
            dsx['done' if s == 'ok' else 'errors'] += 1
            if s != 'ok':
                T.last_error = f'IWM {kind} {d}: {s}'
        T.status()
    F.save_requests(TSTG, requests)
    staged = B.layout_files(TSTG)
    if staged:
        res = B.merge_parquet(TSTG, STORED, force=False, stream=None)
        T.notes['iwm_merge'] = {k: (v if k != 'copied' else len(v)) for k, v in res.items()}
        log('IWM merge', T.notes['iwm_merge'])
        if res['rc'] == 0:
            for _, _, _, rel in staged:
                (TSTG / rel).unlink()
    T.status()

    # 3. singles' minute bars to 2026-10-21 (fetch_cache/underlying)
    jobs = []
    dsx = T.ds('singles_under')
    for s in SINGLES:
        for d in new_days:
            dsx['total'] += 1
            if (FC / 'underlying' / s / f'{d}.parquet').exists():
                dsx['done_before'] += 1
            else:
                jobs.append(('singles_under', 'under_fc', s, d))
    # 4. singles' expiry-day chains to 2026-10-21 (fetch_cache/chains_exp): the listed expiries that are sessions
    dsx = T.ds('singles_chains')
    for s in SINGLES:
        exps = T.call(T.client().option_list_expirations, symbol=s)
        col = exps.columns[-1] if exps is not None else None
        lst = sorted(str(x)[:10].replace('/', '-') for x in exps[col].to_list()) if exps is not None else []
        lst = [x if '-' in x else f'{x[:4]}-{x[4:6]}-{x[6:8]}' for x in lst]
        for d in [x for x in lst if x in new_days]:
            dsx['total'] += 1
            if (FC / 'chains_exp' / s / f'{d}__{d}.parquet').exists():
                dsx['done_before'] += 1
            else:
                jobs.append(('singles_chains', 'chain_exp', s, d))
        T.notes.setdefault('singles_expiries_2026-10-12_21', {})[s] = [x for x in lst if x in new_days]
    for key, kind, s, d in jobs:
        T.job(key, kind, s, d)
    T.status()

    # 5. EOD weeks: SPY/QQQ/IWM 2026-10-12 -> 21; the 11 singles 2022-11-01 -> 2026-10-21 (every expiry, as eod_all)
    eod_jobs = []
    for key, names, a in [('eod_index', ['SPY', 'QQQ', 'IWM'], '2026-10-06'), ('eod_singles', SINGLES, '2022-11-01')]:
        dsx = T.ds(key)
        for s in names:
            cov = covered(FC / 'eod_all' / s)
            for w0, w1, days in weeks(a, '2026-10-21'):
                dsx['total'] += 1
                if all(d in cov for d in days):
                    dsx['done_before'] += 1
                elif any(d in cov for d in days):
                    rest = [d for d in days if d not in cov]
                    eod_jobs.append((key, s, rest[0], rest[-1], rest, None))
                else:
                    eod_jobs.append((key, s, w0, w1, days, None))
    # newest first inside each name is not needed; index weeks first
    eod_jobs.sort(key=lambda j: (j[0] != 'eod_index', j[1], j[2]))

    # 6. SPXW EOD (1-60 DTE): one measured request decides (< ~2 h and < 0.5 GB projected -> fetched, last)
    spx_weeks = weeks('2022-11-01', '2026-10-21')
    dsx = T.ds('eod_spxw')
    cov = covered(FC / 'eod_all' / 'SPXW')
    todo_spx = [(w0, w1, days) for w0, w1, days in spx_weeks if not all(d in cov for d in days)]
    dsx['done_before'] = len(spx_weeks) - len(todo_spx)
    if todo_spx:
        w0, w1, days = todo_spx[-1]
        t0 = time.time()
        r = T.job('eod_spxw', 'eod', 'SPXW', w0, w1, days, max_dte=60)
        secs = time.time() - t0
        f = FC / 'eod_all' / 'SPXW' / f'{w0}__{w1}.parquet'
        mb = f.stat().st_size / 1e6 if f.exists() else None
        proj_h = secs * len(todo_spx) / 3600
        proj_gb = (mb or 0) * len(todo_spx) / 1e3
        decide = r == 'done' and proj_h < 2.0 and proj_gb < 0.5
        T.notes['spxw_eod_measure'] = dict(week=f'{w0}__{w1}', result=r, secs=round(secs, 1), mb=mb, weeks=len(todo_spx),
                                           projected_hours_at_1=round(proj_h, 2), projected_gb=round(proj_gb, 3),
                                           include=decide, rule='include if < ~2 h and < 0.5 GB at 1 in flight')
        log('SPXW EOD measure', T.notes['spxw_eod_measure'])
        dsx['total'] = len(spx_weeks)
        if decide:
            for w0, w1, days in todo_spx[:-1]:
                eod_jobs.append(('eod_spxw', 'SPXW', w0, w1, days, 60))
        else:
            dsx['total'] = dsx['done_before'] + (1 if r == 'done' else 0)
            T.notes['spxw_eod_skipped'] = 'over budget at the measured rate (see spxw_eod_measure)' if r == 'done' else f'measure failed: {r}'
    for key, *_ in eod_jobs:
        T.ds(key)['total'] += 0
    T.status()

    # concurrency: measured on the first EOD jobs (1, then 2, then 4 in flight); kept only if no error and faster
    from concurrent.futures import ThreadPoolExecutor
    q = list(eod_jobs)
    def run_batch(batch, n):
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=n) as ex:
            res = list(ex.map(lambda j: T.job(j[0], 'eod', j[1], j[2], j[3], j[4], max_dte=j[5]), batch))
        return time.time() - t0, res
    chosen, meas = 1, {}
    for n in (1, 2, 4):
        batch, q = q[:4], q[4:]
        if not batch:
            break
        wall, res = run_batch(batch, n)
        meas[n] = dict(jobs=len(batch), wall=round(wall, 1), per_job=round(wall / len(batch), 1), results=res)
        log('concurrency test', n, meas[n])
        if n == 1 and res and all(r == 'error' for r in res):
            T.notes['eod_stopped'] = 'the first EOD requests all failed to shape or verify (see theta_manifest.ndjson raw_schema) — EOD not run'
            T.status(state='stopped: ' + T.notes['eod_stopped'])
            return 1
        if 'error' in res:
            break
        if n == 1 or meas[n]['per_job'] < 0.8 * meas[chosen]['per_job']:
            chosen = n
    T.workers = chosen
    T.notes['sdk_concurrency_test'] = dict(measured=meas, chosen=chosen)
    T.status()
    done_n = [0]
    def eta():
        left = len(q) - done_n[0]
        per = [v for k, v in T.stats.items() if k.startswith('eod') and (v['done'] + v['errors'])]
        sp = sum(v['secs'] for v in per) / max(1, sum(v['done'] + v['errors'] for v in per))
        return (dt.datetime.now(NY) + dt.timedelta(seconds=left * sp / max(1, chosen))).isoformat(timespec='minutes')
    def run_one(j):
        r = T.job(j[0], 'eod', j[1], j[2], j[3], j[4], max_dte=j[5])
        with T.lock:
            done_n[0] += 1
            n = done_n[0]
        if n % 50 == 0:
            T.status(eta=eta())
            log('eod progress', n, 'of', len(q))
        return r
    with ThreadPoolExecutor(max_workers=chosen) as ex:
        list(ex.map(run_one, q))
    T.status(state='finished', eta=None)
    log('theta done')
    return 0


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else ''
    try:
        if cmd == 'uw':
            return uw_run()
        if cmd == 'uw-smoke':
            return uw_run(smoke=True)
        if cmd == 'theta':
            return theta_run()
        if cmd == 'status':
            print(STATUS.read_text() if STATUS.exists() else 'no STATUS.json yet')
            return 0
    except SystemExit as e:
        sec = 'theta' if cmd == 'theta' else 'uw'
        try:
            cur = json.loads(STATUS.read_text()).get(sec, {}) if STATUS.exists() else {}
        except Exception:  # noqa: BLE001
            cur = {}
        cur['state'] = red(f'stopped: {e}')
        write_status(sec, cur)
        log('STOPPED', e)
        return 2
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
