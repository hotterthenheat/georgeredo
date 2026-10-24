"""fetch_final.py — Compass Final's fetch (PREREG_COMPASS_FINAL.md sections 2.4 and 10), after the prereg (4bc546f).

One ThetaData SDK login a run (the daily job's --source sdk path; the key loaded in-process from the scratchpad's
secrets/research.env, never printed or logged; td1_prod_ redacted in every line), at most 3 requests in flight, never
00:00-01:45 or 19:40-20:30 New York (checked before every request). Resumable; every empty, denied or failed answer is
logged in _fetch_log.jsonl and never filled in. Nothing here computes an outcome: the checks read roots, expirations,
stamps and row counts only.

Layout (the replay's, under $SP/compass_final/):
  data_full/chains/<ROOT>/<D>.parquet   timestamp (ms, America/New_York), strike, right (CALL/PUT), bid, ask, bid_size,
                                        ask_size, mid — the research dataset's normalisation (dataset/fetch.py at 7dfea57:
                                        NaN -> null, mid = (bid + ask) / 2, every strike kept, sorted strike/right/time);
                                        <D>.meta.json beside it (the request, roots, expirations, rows, stamps, problems)
  data/afterhours/<SYM>/<D>.parquet     1-minute bars 16:00-17:31 (the bar's timestamp, OHLC, volume, count, vwap)
  data/index/SPX/<D>.parquet            SPX 1-minute prints (timestamp, price) for the sessions not on disk

    python3 -I fetch_final.py expirations   # Theta's expiration lists against the prereg's session lists
    python3 -I fetch_final.py one SPY 2017-01-04
    python3 -I fetch_final.py all [chains|afterhours|spx]
    python3 -I fetch_final.py verify
"""
from __future__ import annotations

import csv
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
ROOT = SP / 'compass_final'
LOG = ROOT / '_fetch_log.jsonl'
NY = ZoneInfo('America/New_York')
NWORK = 3
CHAIN_COLS = ['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size', 'mid']
WINDOW = {'SPY': ('09:30:00', '16:00:00', None), 'QQQ': ('15:00:00', '16:00:00', None),
          'SPXW': ('13:00:00', '14:06:00', ('13:00', '13:01', '14:05', '14:06'))}   # SPXW: kept stamps (entry and the control's minute)


def sessions(root: str) -> list[str]:
    fam = {'SPY': ('fly5', 'condor_em1', 'condor_d20', 'touch_d25'), 'QQQ': ('fly5',), 'SPXW': ('h13_te', 'h15_s2')}[root]
    out = set()
    for f in fam:
        for r in csv.DictReader(open(HERE / f'sessions_{f}.csv')):
            if r['excluded_by'] == '' and r['root'] == root:
                out.add(r['session'])
    return sorted(out)


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
        ROOT.mkdir(parents=True, exist_ok=True)
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


def ask(what: str, fn):
    import grpc
    from thetadata.errors import NoDataFoundError
    delay, codes = 2.0, []
    for attempt in range(8):
        if not allowed_now():
            raise Stop('outside the allowed hours')
        try:
            df = fn(client())
            codes.append('OK')
            return df, codes
        except NoDataFoundError as e:
            codes.append('NOT_FOUND')
            log(what=what, status='empty', codes=codes, error=red(e)[:200])
            return None, codes
        except grpc.RpcError as e:
            code = e.code() if hasattr(e, 'code') else None
            det = red(getattr(e, 'details', lambda: '')())
            codes.append(str(code).replace('StatusCode.', ''))
            if code == grpc.StatusCode.UNAUTHENTICATED:
                log(what=what, status='denied', codes=codes, error=det[:200])
                raise Stop('UNAUTHENTICATED: another login took the key')
            if code == grpc.StatusCode.PERMISSION_DENIED:
                log(what=what, status='denied', codes=codes, error=det[:200])
                return None, codes
            if attempt < 7:
                time.sleep(delay); delay = min(60.0, delay * 2)
                continue
            log(what=what, status='failed', codes=codes, error=det[:200])
            return None, codes
        except Exception as e:  # noqa: BLE001
            codes.append(type(e).__name__)
            if attempt < 4:
                time.sleep(delay); delay = min(60.0, delay * 2)
                continue
            log(what=what, status='failed', codes=codes, error=red(e)[:200])
            return None, codes
    return None, codes


def norm_ts(df: pl.DataFrame, col: str = 'timestamp') -> pl.DataFrame:
    df = df.with_columns(pl.col(col).dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
    fl = [c for c, t in zip(df.columns, df.dtypes) if t in (pl.Float64, pl.Float32)]
    return df.with_columns([pl.col(c).fill_nan(None) for c in fl]) if fl else df


def write(df: pl.DataFrame, p: Path, meta: dict | None = None) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name('.' + p.name + '.part')
    df.write_parquet(tmp, compression='zstd')
    tmp.rename(p)
    if meta is not None:
        p.with_suffix('.meta.json').write_text(json.dumps(meta, indent=1, default=str))


def chain(root: str, day: str) -> str:
    target = ROOT / 'data_full' / 'chains' / root / f'{day}.parquet'
    if target.exists():
        return 'have'
    t0 = time.time()
    a, b, keep_stamps = WINDOW[root]
    D = dt.date.fromisoformat(day)
    df, codes = ask(f'chain {root} {day}', lambda c: c.option_history_quote(symbol=root, expiration=D, date=D, interval='1m', strike='*',
                                                                            right='both', start_time=a, end_time=b))
    if df is None:
        return 'no-data'
    raw_cols = df.columns
    syms = sorted(set(map(str, df['symbol'].unique().to_list()))) if 'symbol' in raw_cols else []
    exps = sorted(set(str(v)[:10] for v in df['expiration'].unique().to_list())) if 'expiration' in raw_cols else []
    out = df.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid')).select(CHAIN_COLS) \
            .with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32), pl.col('strike').cast(pl.Float64))
    out = norm_ts(out).sort(['strike', 'right', 'timestamp'])
    hm = out['timestamp'].dt.strftime('%H:%M')
    out = out.filter(hm.is_between(pl.lit(a[:5]), pl.lit(b[:5])))
    if keep_stamps:
        out = out.filter(out['timestamp'].dt.strftime('%H:%M').is_in(list(keep_stamps)))
    stamps = sorted(set(out['timestamp'].dt.strftime('%H:%M').to_list()))
    rights = sorted(set(out['right'].to_list()))
    problems = []
    if syms != [root]:
        problems.append(f'roots {syms}')
    if exps != [day]:
        problems.append(f'expirations {exps}')
    if rights != ['CALL', 'PUT']:
        problems.append(f'rights {rights}')
    if not out.height:
        problems.append('no rows')
    if any(not (a[:5] <= s <= b[:5]) for s in stamps):
        problems.append('stamps outside the window')
    meta = {'day': day, 'root': root, 'request': {'call': 'option_history_quote', 'symbol': root, 'expiration': day, 'date': day,
            'interval': '1m', 'strike': '*', 'right': 'both', 'start_time': a, 'end_time': b, 'kept_stamps': keep_stamps},
            'via': 'thetadata SDK (gRPC), one login', 'codes': codes, 'seconds': round(time.time() - t0, 1),
            'raw_rows': df.height, 'raw_columns': raw_cols, 'roots': syms, 'expirations': exps, 'rows': out.height,
            'strikes': out['strike'].n_unique(), 'stamps_first_last': [stamps[0], stamps[-1]] if stamps else None,
            'n_stamps': len(stamps), 'problems': problems, 'fetched_at': dt.datetime.now(NY).isoformat(timespec='seconds')}
    write(out, target, meta)
    log(what=f'chain {root} {day}', status='ok' if not problems else 'problem', rows=out.height, strikes=meta['strikes'],
        stamps=len(stamps), seconds=meta['seconds'], problems=problems)
    return 'ok' if not problems else 'problem'


def afterhours(sym: str, day: str) -> str:
    target = ROOT / 'data' / 'afterhours' / sym / f'{day}.parquet'
    if target.exists():
        return 'have'
    D = dt.date.fromisoformat(day)
    df, codes = ask(f'afterhours {sym} {day}', lambda c: c.stock_history_ohlc(sym, interval='1m', date=D, start_time='16:00:00', end_time='17:31:00'))
    if df is None:
        return 'no-data'
    out = norm_ts(df).sort('timestamp')
    days = sorted(set(out['timestamp'].dt.strftime('%Y-%m-%d').to_list()))
    problems = [] if days == [day] else [f'days {days}']
    n_close = int(out.filter(pl.col('close').is_not_null()).height)
    write(out, target, {'day': day, 'symbol': sym, 'request': 'stock_history_ohlc 1m 16:00:00-17:31:00', 'codes': codes,
                        'rows': out.height, 'bars_with_close': n_close, 'problems': problems})
    log(what=f'afterhours {sym} {day}', status='ok' if not problems else 'problem', rows=out.height, bars_with_close=n_close, problems=problems)
    return 'ok'


def spx(day: str) -> str:
    target = ROOT / 'data' / 'index' / 'SPX' / f'{day}.parquet'
    if target.exists() or (SP / 'theta' / 'data' / 'index' / 'SPX' / f'{day}.parquet').exists():
        return 'have'
    D = dt.date.fromisoformat(day)
    df, codes = ask(f'spx {day}', lambda c: c.index_history_price('SPX', date=D, interval='1m'))
    if df is None:
        return 'no-data'
    out = norm_ts(df.select('timestamp', 'price')).sort('timestamp')
    days = sorted(set(out['timestamp'].dt.strftime('%Y-%m-%d').to_list()))
    problems = [] if days == [day] else [f'days {days}']
    write(out, target, {'day': day, 'request': 'index_history_price SPX 1m', 'codes': codes, 'rows': out.height, 'problems': problems})
    log(what=f'spx {day}', status='ok' if not problems else 'problem', rows=out.height, problems=problems)
    return 'ok'


def jobs(which: str) -> list:
    out = []
    if which in ('all', 'spx'):
        out += [(spx, (d,)) for d in sessions('SPXW')]
    if which in ('all', 'chains'):
        for r in ('SPXW', 'QQQ', 'SPY'):
            out += [(chain, (r, d)) for d in sessions(r)]
    if which in ('all', 'afterhours'):
        for s in ('SPY', 'QQQ'):
            out += [(afterhours, (s, d)) for d in sessions(s)]
    return out


def run_all(which: str) -> None:
    J = jobs(which)
    log(what='run', status='start', which=which, jobs=len(J))
    res: dict = {}
    stop = threading.Event()

    def go(j):
        if stop.is_set():
            return 'skipped'
        fn, a = j
        try:
            return fn(*a)
        except Stop as e:
            stop.set()
            log(what=f'{fn.__name__} {a}', status='stopped', why=str(e))
            return 'stopped'
    with ThreadPoolExecutor(NWORK) as ex:
        for r in ex.map(go, J):
            res[r] = res.get(r, 0) + 1
    log(what='run', status='end', which=which, results=res)


def expirations() -> None:
    out = {}
    for root in ('SPY', 'QQQ', 'SPXW'):
        df, codes = ask(f'expirations {root}', lambda c: c.option_list_expirations(root))
        col = [c for c in df.columns if 'exp' in c.lower()][0] if df is not None else None
        listed = {str(v)[:10] for v in df[col].to_list()} if col else set()
        want = sessions(root)
        missing = [d for d in want if d not in listed]
        out[root] = {'sessions': len(want), 'listed_now': len(listed), 'not_listed_now': missing}
        log(what=f'expirations {root}', status='ok' if not missing else 'problem', sessions=len(want), not_listed=missing)
    (ROOT / 'expirations_check.json').write_text(json.dumps(out, indent=1))


def verify() -> None:
    rep = {}
    for root in ('SPY', 'QQQ', 'SPXW'):
        want = sessions(root)
        have, bad = 0, []
        for d in want:
            m = ROOT / 'data_full' / 'chains' / root / f'{d}.meta.json'
            if not m.exists():
                continue
            have += 1
            j = json.loads(m.read_text())
            if j['problems']:
                bad.append((d, j['problems']))
        rep[f'chains {root}'] = {'wanted': len(want), 'have': have, 'problems': bad}
    for s in ('SPY', 'QQQ'):
        want = sessions(s)
        have = [d for d in want if (ROOT / 'data' / 'afterhours' / s / f'{d}.parquet').exists()]
        rep[f'afterhours {s}'] = {'wanted': len(want), 'have': len(have)}
    print(json.dumps(rep, indent=1, default=str))
    (ROOT / 'verify.json').write_text(json.dumps(rep, indent=1, default=str))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'verify'
    if cmd == 'expirations':
        expirations()
    elif cmd == 'one':
        print({'SPY': chain, 'QQQ': chain, 'SPXW': chain}[sys.argv[2]](sys.argv[2], sys.argv[3]))
    elif cmd == 'all':
        run_all(sys.argv[2] if len(sys.argv) > 2 else 'all')
    elif cmd == 'verify':
        verify()
    elif cmd == 'run':                      # one login: the expiration check, then every job
        expirations()
        run_all('all')
        verify()
