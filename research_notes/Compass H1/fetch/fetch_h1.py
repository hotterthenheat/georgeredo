"""H1 stage 1 — the fetch (no outcome computed or printed). ONE login, ONE process, ONE request in flight.

    set -a; . $SP/secrets/research.env; set +a      # THETADATA_KEY, read by this process only
    python3 -I fetch_h1.py fetch     # (a) SPY, QQQ stock EOD 2012..2018, one request a name-year (data_lake/fetch/bulk_fetch.py
                                     #     phase B's call: stock_history_eod(symbol, start_date=Jan 1, end_date=Dec 31));
                                     # (b) ONE probe: SPY 1-minute bars on 2016-06-01 (sdk_fetch.py's call: stock_history_ohlc(
                                     #     symbol, interval='1m', date=D), the SDK's default venue nqb, as the stored bars);
                                     #     prices back → every SPY session 2012-06-01..2016-12-30 whose stored file is all-NaN,
                                     #     into the staging folder; NaN again → no bar fetch (SPY starts 2017-01-03)
    python3 -I fetch_h1.py verify    # no login: every staged file checked (391 rows 09:30..16:00, prices present, schema)
    python3 -I fetch_h1.py merge     # no login: a verified staged file replaces ONLY a stored file that is all-NaN; the
                                     # original is kept beside it as <day>.parquet.orig

The key is never printed, logged or written: every text kept passes through red(). Guard: no ThetaData session is opened or
held between 19:40 and 20:30 New York (the owner's daily job logs in at 19:47) or between 00:00 and 01:45 New York; the run
stops at 30 minutes or 50 MB fetched, whichever first. Writes: $SP/lake/stock_eod_h1/, $SP/theta/h1_staging/, this
folder's fetch_log.jsonl and fetch_summary.json, ../data/stock_eod_2012_2018.parquet. It computes no H1 quantity.
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
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

NY = ZoneInfo('America/New_York')
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
STORED = SP / 'theta' / 'data' / 'underlying'
STAGING = SP / 'theta' / 'h1_staging' / 'data' / 'underlying'
EOD_OUT = SP / 'lake' / 'stock_eod_h1'
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / 'data'
LOG = HERE / 'fetch_log.jsonl'
SUMMARY = HERE / 'fetch_summary.json'
PROBE_DAY = '2016-06-01'
BAR_FROM, BAR_TO = '2012-06-01', '2016-12-30'
EOD_YEARS = range(2012, 2019)
BUDGET_S, BUDGET_BYTES = 30 * 60, 50 * 1024 * 1024
T0 = time.time()


def red(s) -> str:
    s = str(s)
    k = os.environ.get('THETADATA_KEY') or ''
    if len(k) >= 4:
        s = s.replace(k, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9_\-]+', '[key]', s)


def log(**rec):
    rec = {'t': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), **rec}
    line = red(json.dumps(rec, default=str))
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')
    print(line, flush=True)


def forbidden_now() -> str | None:
    n = dt.datetime.now(NY)
    m = n.hour * 60 + n.minute
    if 19 * 60 + 40 <= m < 20 * 60 + 30:
        return f'{n:%H:%M} New York is inside 19:40-20:30 (the owner\'s daily job)'
    if m < 60 + 45:
        return f'{n:%H:%M} New York is inside 00:00-01:45'
    return None


_client = None


def client():
    global _client
    if _client is None:
        why = forbidden_now()
        if why:
            raise SystemExit(why)
        logging.getLogger('thetadata').setLevel(logging.ERROR)
        from thetadata import ThetaClient
        if not os.environ.get('THETADATA_KEY'):
            raise SystemExit('THETADATA_KEY is not in the environment')
        _client = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
        log(event='login ok')
    return _client


def call(fn: str, **kw):
    """→ (frame | None, status). One request at a time; retries on transient codes; stops on UNAUTHENTICATED."""
    import grpc
    from thetadata.errors import NoDataFoundError
    delay, codes = 2.0, []
    for attempt in range(6):
        why = forbidden_now()
        if why:
            raise SystemExit(why)
        try:
            return getattr(client(), fn)(**kw), codes + ['OK']
        except NoDataFoundError:
            return None, codes + ['NOT_FOUND']
        except grpc.RpcError as e:
            code = e.code() if hasattr(e, 'code') else None
            det = red(getattr(e, 'details', lambda: '')())
            codes.append(str(code).replace('StatusCode.', ''))
            if code == grpc.StatusCode.UNAUTHENTICATED:
                log(event='stop', why='UNAUTHENTICATED: another login took the session', detail=det[:160])
                raise SystemExit('UNAUTHENTICATED')
            if code in (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED,
                        grpc.StatusCode.UNKNOWN, grpc.StatusCode.INTERNAL, grpc.StatusCode.ABORTED) and attempt < 5:
                time.sleep(delay)
                delay = min(30.0, delay * 2)
                continue
            return None, codes + [f'ERR {det[:120]}']
        except Exception as e:  # noqa: BLE001
            codes.append(type(e).__name__)
            if attempt < 3:
                time.sleep(delay)
                delay *= 2
                continue
            return None, codes + [red(e)[:160]]
    return None, codes + ['retries exhausted']


def norm_ts(df, col='timestamp'):
    """sdk_fetch.py norm_ts: Datetime(ms, America/New_York); float NaN → null"""
    df = df.with_columns(pl.col(col).dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
    fl = [c for c, t in zip(df.columns, df.dtypes) if t in (pl.Float64, pl.Float32)]
    return df.with_columns([pl.col(c).fill_nan(None) for c in fl]) if fl else df


def shape_bars(df, day):
    """sdk_fetch.py shape('under'): the SDK's frame, the day's rows only"""
    out = norm_ts(df.select(df.columns)).sort('timestamp')
    other = out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') != day).height
    return out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') == day), other


def priced(t: pl.DataFrame) -> int:
    return t['close'].fill_nan(None).drop_nulls().len()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def trading_days() -> list[str]:
    """the calendar for the bar fetch: the dates QQQ's stored 1-minute files exist (QQQ has a file on every session and on
    no holiday 2012-06 →), inside BAR_FROM..BAR_TO"""
    return sorted(Path(f).name[:10] for f in glob.glob(str(STORED / 'QQQ' / '*.parquet')) if BAR_FROM <= Path(f).name[:10] <= BAR_TO)


def all_nan(p: Path) -> bool:
    return p.exists() and priced(pl.read_parquet(p, columns=['close'])) == 0


def step_fetch() -> int:
    summ = {'requests': 0, 'bytes_written': 0, 'eod': {}, 'probe': None, 'bars': {}}
    # (a) stock EOD
    frames = []
    for y in EOD_YEARS:
        for s in ('SPY', 'QQQ'):
            t0 = time.time()
            df, st = call('stock_history_eod', symbol=s, start_date=dt.date(y, 1, 1), end_date=dt.date(y, 12, 31))
            summ['requests'] += 1
            rows = 0 if df is None else df.height
            if df is not None and df.height:
                df = df.with_columns(pl.lit(s).alias('symbol'))
                p = EOD_OUT / f'year={y}' / f'{s}.parquet'
                p.parent.mkdir(parents=True, exist_ok=True)
                df.write_parquet(p, compression='zstd')
                summ['bytes_written'] += p.stat().st_size
                frames.append(df)
                first, last = df['created'].min(), df['created'].max()
            else:
                first = last = None
            summ['eod'][f'{s} {y}'] = {'rows': rows, 'status': st, 'first': str(first), 'last': str(last)}
            log(event='eod', symbol=s, year=y, rows=rows, status=st, first=first, last=last, s=round(time.time() - t0, 1))
    if frames:
        e = pl.concat(frames, how='diagonal_relaxed').sort('symbol', 'created')
        DATA.mkdir(parents=True, exist_ok=True)
        e.write_parquet(DATA / 'stock_eod_2012_2018.parquet', compression='zstd', statistics=False)
        summ['eod_file'] = {'path': 'data/stock_eod_2012_2018.parquet', 'rows': e.height, 'sha256': sha(DATA / 'stock_eod_2012_2018.parquet')}
    # (b) the probe
    t0 = time.time()
    df, st = call('stock_history_ohlc', symbol='SPY', interval='1m', date=dt.date.fromisoformat(PROBE_DAY))
    summ['requests'] += 1
    if df is None:
        summ['probe'] = {'day': PROBE_DAY, 'status': st, 'rows': 0, 'priced': 0}
    else:
        out, other = shape_bars(df, PROBE_DAY)
        summ['probe'] = {'day': PROBE_DAY, 'status': st, 'rows': out.height, 'priced': priced(out), 'other_day_rows': other,
                         'schema_equal_stored': out.schema == pl.read_parquet(STORED / 'QQQ' / f'{PROBE_DAY}.parquet').schema}
        if summ['probe']['priced'] > 0:
            p = STAGING / 'SPY' / f'{PROBE_DAY}.parquet'
            p.parent.mkdir(parents=True, exist_ok=True)
            out.write_parquet(p, compression='zstd')
            summ['bytes_written'] += p.stat().st_size
    log(event='probe', s=round(time.time() - t0, 1), **summ['probe'])
    if not summ['probe']['priced']:
        summ['bars'] = {'fetched': False, 'why': 'the probe came back with no price: SPY starts 2017-01-03'}
        SUMMARY.write_text(red(json.dumps(summ, indent=1, default=str)), encoding='utf-8')
        return 0
    # the bar fetch
    days = [d for d in trading_days() if all_nan(STORED / 'SPY' / f'{d}.parquet')]
    n_ok = n_fail = 0
    stopped = None
    for d in days:
        p = STAGING / 'SPY' / f'{d}.parquet'
        if p.exists():
            n_ok += 1
            continue
        if time.time() - T0 > BUDGET_S:
            stopped = 'time budget (30 min)'
            break
        if summ['bytes_written'] > BUDGET_BYTES:
            stopped = 'size budget (50 MB)'
            break
        t0 = time.time()
        df, st = call('stock_history_ohlc', symbol='SPY', interval='1m', date=dt.date.fromisoformat(d))
        summ['requests'] += 1
        if df is None or df.height == 0:
            n_fail += 1
            log(event='bars', day=d, status=st, rows=0)
            continue
        out, other = shape_bars(df, d)
        p.parent.mkdir(parents=True, exist_ok=True)
        out.write_parquet(p, compression='zstd')
        summ['bytes_written'] += p.stat().st_size
        n_ok += 1
        if n_ok % 50 == 0 or other or out.height != 391:
            log(event='bars', day=d, status=st, rows=out.height, priced=priced(out), other_day_rows=other, s=round(time.time() - t0, 2),
                done=n_ok, of=len(days), mb=round(summ['bytes_written'] / 1e6, 2), elapsed_s=round(time.time() - T0))
    summ['bars'] = {'fetched': True, 'target_days': len(days), 'staged': n_ok, 'failed': n_fail, 'stopped': stopped,
                    'range': [days[0], days[-1]] if days else None}
    summ['elapsed_s'] = round(time.time() - T0)
    SUMMARY.write_text(red(json.dumps(summ, indent=1, default=str)), encoding='utf-8')
    log(event='done', **{k: v for k, v in summ.items() if k in ('requests', 'bytes_written', 'bars', 'elapsed_s')})
    return 0


def check_file(p: Path, day: str, ref_schema) -> list[str]:
    t = pl.read_parquet(p)
    probs = []
    if t.schema != ref_schema:
        probs.append(f'schema {dict(t.schema)}')
    if t.height != 391:
        probs.append(f'{t.height} rows')
    ts = t['timestamp'].dt.strftime('%H:%M').to_list()
    if ts and (ts[0] != '09:30' or ts[-1] != '16:00'):
        probs.append(f'stamps {ts[0]}..{ts[-1]}')
    if set(t['timestamp'].dt.strftime('%Y-%m-%d').unique().to_list()) != {day}:
        probs.append('rows of another day')
    rth = t.filter(pl.col('timestamp').dt.strftime('%H:%M') < '16:00')
    n = priced(rth)
    if n < 300:                          # a session with fewer than 300 of 390 regular minutes priced is not "prices present"
        probs.append(f'only {n} of {rth.height} regular minutes priced')
    for c in ('open', 'high', 'low', 'close'):
        v = t[c].fill_nan(None).drop_nulls()
        if v.len() and (v.min() <= 0):
            probs.append(f'{c} <= 0')
    return probs


def step_verify() -> int:
    files = sorted(glob.glob(str(STAGING / 'SPY' / '*.parquet')))
    ref = pl.read_parquet(STORED / 'QQQ' / f'{PROBE_DAY}.parquet').schema
    bad, half = {}, []
    for f in files:
        d = Path(f).name[:10]
        pr = check_file(Path(f), d, ref)
        if pr:
            bad[d] = pr
    rep = {'staged': len(files), 'ok': len(files) - len(bad), 'problems': bad}
    (HERE / 'verify_staging.json').write_text(json.dumps(rep, indent=1), encoding='utf-8')
    print(json.dumps({'staged': rep['staged'], 'ok': rep['ok'], 'n_problems': len(bad), 'first_problems': dict(list(bad.items())[:12])}, indent=1))
    return 0


def step_merge() -> int:
    rep = json.loads((HERE / 'verify_staging.json').read_text(encoding='utf-8'))
    merged, kept, skipped = [], [], []
    for f in sorted(glob.glob(str(STAGING / 'SPY' / '*.parquet'))):
        d = Path(f).name[:10]
        tgt = STORED / 'SPY' / f'{d}.parquet'
        if d in rep['problems']:
            skipped.append((d, 'failed verify: ' + '; '.join(rep['problems'][d])))
            continue
        if not tgt.exists():
            skipped.append((d, 'no stored file to replace'))
            continue
        if not all_nan(tgt):
            kept.append(d)                      # never overwrite good data
            continue
        orig = tgt.with_name(tgt.name + '.orig')
        if orig.exists():
            skipped.append((d, '.orig already present'))
            continue
        shutil.copy2(tgt, orig)
        shutil.copy2(f, tgt)
        merged.append({'day': d, 'sha256_new': sha(tgt), 'sha256_orig': sha(orig)})
    out = {'merged': len(merged), 'kept_good_stored': kept, 'skipped': skipped, 'files': merged}
    (HERE / 'merge_log.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps({'merged': len(merged), 'kept_good_stored': len(kept), 'skipped': skipped[:20]}, indent=1))
    return 0


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else ''
    sys.exit({'fetch': step_fetch, 'verify': step_verify, 'merge': step_merge}.get(step, lambda: print(__doc__) or 2)())
