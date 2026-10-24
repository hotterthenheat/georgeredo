"""fetch_close.py — Compass Close's fetch (PREREG_COMPASS_CLOSE.md section 8, the owner's "do em all").

One ThetaData SDK login (the daily job's --source sdk path: thetadata 1.0.14, the key from THETADATA_KEY loaded
in-process from the scratchpad's secrets/research.env, never printed or logged), at most 3 requests in flight, one request
a session: option_history_quote('SPXW', expiration=D, date=D, interval='1m', strike='*', right='both',
start_time='15:45:00', end_time='16:00:00'). Kept: the strikes from 4 listed steps below the strike nearest the lowest
SPX print 15:45-16:00 to 4 above the one nearest the highest; plus <D>.meta.json with every listed strike, the roots,
expirations, row counts and stamps. Never between 00:00-01:45 or 19:40-20:30 New York (checked before every request).
Resumable; every empty or denied answer logged in _fetch_log.jsonl.

    python3 -I fetch_close.py expirations    # Theta's SPXW expiration list against sessions_new.csv
    python3 -I fetch_close.py one 2017-06-02 # a single session (smoke)
    python3 -I fetch_close.py all            # every session of sessions_new.csv not yet on disk
    python3 -I fetch_close.py verify         # every file: same-day SPXW, stamps 15:45..16:00, strikes around S
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

HERE = Path(__file__).resolve().parent
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
OUT = SP / 'theta' / 'data_full' / 'chains_close' / 'SPXW'
SPX = SP / 'theta' / 'data' / 'index' / 'SPX'
LOG = OUT / '_fetch_log.jsonl'
NY = ZoneInfo('America/New_York')
NWORK = 3
PAD = 4
COLS = ['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size']


def load_key() -> None:
    if os.environ.get('THETADATA_KEY'):
        return
    for line in (SP / 'secrets' / 'research.env').read_text().splitlines():
        line = line.strip()
        if line.startswith('THETADATA_KEY='):
            os.environ['THETADATA_KEY'] = line.split('=', 1)[1].strip().strip('"').strip("'")


def red(s) -> str:
    s = str(s)
    k = os.environ.get('THETADATA_KEY') or ''
    if len(k) >= 4:
        s = s.replace(k, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9_-]+', '[key]', s)


_lock = threading.Lock()


def log(**kw) -> None:
    kw['at'] = dt.datetime.now(NY).isoformat(timespec='seconds')
    line = red(json.dumps(kw, default=str))
    with _lock:
        OUT.mkdir(parents=True, exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')
        print(line, flush=True)


def allowed_now() -> bool:
    t = dt.datetime.now(NY).time()
    return not (dt.time(0, 0) <= t < dt.time(1, 45) or dt.time(19, 40) <= t < dt.time(20, 30))


_client = None


def client():
    global _client
    with _lock:
        if _client is None:
            load_key()
            logging.getLogger('thetadata').setLevel(logging.ERROR)
            from thetadata import ThetaClient
            if not os.environ.get('THETADATA_KEY'):
                raise SystemExit('THETADATA_KEY not found')
            _client = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
            print('login ok', flush=True)
    return _client


class Stop(Exception):
    pass


def ask(day: str):
    import grpc
    from thetadata.errors import NoDataFoundError
    D = dt.date.fromisoformat(day)
    delay, codes = 2.0, []
    for attempt in range(8):
        if not allowed_now():
            raise Stop('outside the allowed hours')
        try:
            df = client().option_history_quote(symbol='SPXW', expiration=D, date=D, interval='1m', strike='*',
                                               right='both', start_time='15:45:00', end_time='16:00:00')
            codes.append('OK')
            return df, codes
        except NoDataFoundError as e:
            codes.append('NOT_FOUND')
            log(day=day, status='empty', codes=codes, error=red(e)[:200])
            return None, codes
        except grpc.RpcError as e:
            code = e.code() if hasattr(e, 'code') else None
            det = red(getattr(e, 'details', lambda: '')())
            codes.append(str(code).replace('StatusCode.', ''))
            if code == grpc.StatusCode.UNAUTHENTICATED:
                log(day=day, status='denied', codes=codes, error=det[:200])
                raise Stop('UNAUTHENTICATED: another login took the key')
            if code == grpc.StatusCode.PERMISSION_DENIED:
                log(day=day, status='denied', codes=codes, error=det[:200])
                return None, codes
            if attempt < 7:
                time.sleep(delay); delay = min(60.0, delay * 2)
                continue
            log(day=day, status='failed', codes=codes, error=det[:200])
            return None, codes
        except Exception as e:  # noqa: BLE001
            codes.append(type(e).__name__)
            if attempt < 4:
                time.sleep(delay); delay = min(60.0, delay * 2)
                continue
            log(day=day, status='failed', codes=codes, error=red(e)[:200])
            return None, codes
    return None, codes


def spx_window(day: str) -> pl.DataFrame:
    x = pl.read_parquet(SPX / f'{day}.parquet')
    return x.filter(pl.col('timestamp').dt.strftime('%H:%M').is_between(pl.lit('15:45'), pl.lit('16:00')))


def one(day: str) -> str:
    target = OUT / f'{day}.parquet'
    meta_f = OUT / f'{day}.meta.json'
    if target.exists() and meta_f.exists():
        return 'have'
    t0 = time.time()
    df, codes = ask(day)
    if df is None:
        return 'no-data'
    raw_cols = df.columns
    syms = sorted(set(map(str, df['symbol'].unique().to_list()))) if 'symbol' in raw_cols else []
    exps = sorted(set(str(v)[:10].replace('-', '') for v in df['expiration'].unique().to_list())) if 'expiration' in raw_cols else []
    d = df.with_columns(pl.col('timestamp').dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
    fl = [c for c, t in zip(d.columns, d.dtypes) if t in (pl.Float64, pl.Float32)]
    d = d.with_columns([pl.col(c).fill_nan(None) for c in fl])
    d = d.select(COLS).with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32),
                                    pl.col('strike').cast(pl.Float64))
    hm = d['timestamp'].dt.strftime('%H:%M')
    d = d.filter(hm.is_between(pl.lit('15:45'), pl.lit('16:00')))
    calls = set(d.filter(pl.col('right').str.to_uppercase().str.starts_with('C'))['strike'].to_list())
    puts = set(d.filter(pl.col('right').str.to_uppercase().str.starts_with('P'))['strike'].to_list())
    listed = sorted(calls & puts)
    s = spx_window(day)
    problems = []
    if syms != ['SPXW']:
        problems.append(f'roots {syms}')
    if exps != [day.replace('-', '')]:
        problems.append(f'expirations {exps}')
    if not listed:
        problems.append('no listed strike')
    if s.height == 0:
        problems.append('no SPX prints 15:45-16:00')
    keep = []
    if listed and s.height:
        lo_s, hi_s = float(s['price'].min()), float(s['price'].max())
        near = lambda x: min(range(len(listed)), key=lambda i: (abs(listed[i] - x), listed[i]))  # noqa: E731
        i0, i1 = max(0, near(lo_s) - PAD), min(len(listed) - 1, near(hi_s) + PAD)
        keep = listed[i0:i1 + 1]
    out = d.filter(pl.col('strike').is_in(keep)).sort(['strike', 'right', 'timestamp'])
    stamps = sorted(set(out['timestamp'].dt.strftime('%H:%M').to_list()))
    meta = {'day': day, 'request': {'call': 'option_history_quote', 'symbol': 'SPXW', 'expiration': day, 'date': day,
                                    'interval': '1m', 'strike': '*', 'right': 'both', 'start_time': '15:45:00',
                                    'end_time': '16:00:00'},
            'via': 'thetadata SDK 1.0.14 (gRPC), one login', 'codes': codes, 'seconds': round(time.time() - t0, 1),
            'raw_rows': df.height, 'raw_columns': raw_cols, 'roots': syms, 'expirations': exps,
            'listed_strikes': listed, 'kept_strikes': keep, 'kept_rows': out.height, 'stamps': stamps,
            'problems': problems, 'fetched_at': dt.datetime.now(NY).isoformat(timespec='seconds')}
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f'.{day}.parquet.part'
    out.write_parquet(tmp, compression='zstd')
    tmp.rename(target)
    meta_f.write_text(json.dumps(meta, indent=1, default=str))
    log(day=day, status='ok' if not problems else 'problem', rows=df.height, kept=out.height, strikes=len(keep),
        listed=len(listed), seconds=meta['seconds'], problems=problems)
    return 'ok' if not problems else 'problem'


def sessions() -> list[str]:
    return pl.read_csv(HERE / 'sessions_new.csv')['session'].to_list()


def main(step: str, arg: str | None = None) -> int:
    if not allowed_now():
        print('outside the allowed hours (00:00-01:45, 19:40-20:30 New York)'); return 2
    if step == 'expirations':
        e = client().option_list_expirations('SPXW')
        col = [c for c in e.columns if 'exp' in c.lower()][0]
        have = set(str(v)[:10] for v in e[col].to_list())
        have = {h if '-' in h else f'{h[:4]}-{h[4:6]}-{h[6:8]}' for h in have}
        miss = [d for d in sessions() if d not in have]
        (OUT).mkdir(parents=True, exist_ok=True)
        (OUT / '_expirations_check.json').write_text(json.dumps({'listed': len(have), 'sessions': len(sessions()),
                                                                 'not_listed': miss}, indent=1))
        print('expirations', len(have), 'sessions not listed:', miss)
        return 0
    if step == 'one':
        print(one(arg)); return 0
    if step == 'run':                       # ONE login: the expiration list, one smoke session, then the rest
        main('expirations')
        days = [d for d in sessions() if not (OUT / f'{d}.parquet').exists()]
        if days:
            r = one(days[0])
            print('smoke', days[0], r, flush=True)
            if r not in ('ok', 'have'):
                return 4
        return main('all')
    if step == 'all':
        days = [d for d in sessions() if not (OUT / f'{d}.parquet').exists()]
        print(len(days), 'to fetch', flush=True)
        client()
        res = {}
        try:
            with ThreadPoolExecutor(NWORK) as ex:
                for d, r in zip(days, ex.map(one, days)):
                    res[d] = r
        except Stop as e:
            print('STOPPED:', red(e)); return 3
        from collections import Counter
        print(Counter(res.values())); return 0
    if step == 'verify':
        bad = []
        for d in sessions():
            f, m = OUT / f'{d}.parquet', OUT / f'{d}.meta.json'
            if not (f.exists() and m.exists()):
                bad.append((d, 'missing')); continue
            meta = json.loads(m.read_text())
            x = pl.read_parquet(f)
            s = spx_window(d)
            st = sorted(set(x['timestamp'].dt.strftime('%H:%M').to_list()))
            probs = list(meta['problems'])
            if meta['roots'] != ['SPXW'] or meta['expirations'] != [d.replace('-', '')]:
                probs.append('not same-day SPXW')
            if set(x['timestamp'].dt.strftime('%Y-%m-%d').unique().to_list()) != {d}:
                probs.append('rows of another date')
            if '15:55' not in st:
                probs.append('no 15:55 stamp')
            if s.height and x.height and not (x['strike'].min() <= s['price'].min() and x['strike'].max() >= s['price'].max()):
                probs.append('kept strikes do not bracket the prints')
            if probs:
                bad.append((d, probs))
        print('verified', len(sessions()), 'bad', len(bad))
        for b in bad:
            print(b)
        (OUT / '_verify.json').write_text(json.dumps({'sessions': len(sessions()), 'bad': bad}, indent=1, default=str))
        return 0 if not bad else 1
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
