"""THE CONTAINER'S FETCH of 2026-10-12 → 2026-10-21 through the thetadata SDK (gRPC) — the same calls, the same SDK
(1.0.14) and the same frame shaping that built the stored dataset (scratchpad theta/ds/build.py `fetch_raw` / `process`;
its fetch.py twin ran with no strike band for data_full/chains), so the files' schema is the stored files' by
construction. Then the repo's own checks (scripts/paper_backtest.py validate_frame / verify_parquet / merge_parquet).

ONE LOGIN, ONE PROCESS, ONE REQUEST IN FLIGHT (the SDK client is not shared across threads here). The key is read from
THETADATA_KEY in the environment only and handed to the client; never printed, logged or written (every text kept is
passed through red()). Signing in here signs the owner's PC terminal out — run it only with the owner's go-ahead.

    set -a; . /tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/secrets/research.env; set +a
    python3 -I sdk_fetch.py smallest      # SPY bars 2026-10-12 into staging, schema against the stored 2026-10-09; and the
                                          # stored 2026-10-09 SPY bars fetched again into an overlap root, compared value for value
    python3 -I sdk_fetch.py all           # every file of the 8 sessions into staging (a file already staged and ok is kept)
    python3 -I sdk_fetch.py verify        # --verify-parquet on staging (norms from the stored root); exit 1 on any failure
    python3 -I sdk_fetch.py merge         # into the stored root ONLY if nothing overlaps (merge_parquet stops on any overlap)
    python3 -I sdk_fetch.py final         # --verify-parquet on the stored root 2026-10-05 → 2026-10-21 (the sessions before too)
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

REPO = Path('/home/user/georgeredo')
sys.path.insert(0, str(REPO / 'scripts'))
import polars as pl  # noqa: E402

import eod_recorder as R  # noqa: E402
import paper_backtest as B  # noqa: E402

SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
STORED = SP / 'theta'
HERE = Path(__file__).resolve().parent
STAGING = HERE / 'theta_forward_staging'
OVERLAP = HERE / 'theta_overlap_check'
START, END = '2026-10-12', '2026-10-21'
REF_DAY = '2026-10-09'
REQ_TIMEOUT = 420
CHAIN_COLS = ['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size', 'mid']


def red(s) -> str:
    s = str(s)
    k = os.environ.get('THETADATA_KEY') or ''
    if len(k) >= 4:
        s = s.replace(k, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9]+', '[key]', s)


def log(*a):
    print(dt.datetime.now().strftime('%H:%M:%S'), *[red(x) for x in a], flush=True)


_client = None


def client():
    """ONE login for the process (build.py login()); the key from the environment only"""
    global _client
    if _client is None:
        logging.getLogger('thetadata').setLevel(logging.ERROR)
        from thetadata import ThetaClient
        if not os.environ.get('THETADATA_KEY'):
            raise SystemExit('THETADATA_KEY is not in the environment (set -a; . secrets/research.env; set +a)')
        _client = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
        log('login ok')
    return _client


def fetch_raw(kind: str, sym: str, day: str):
    """build.py fetch_raw, verbatim in its calls: the same-day chain with every strike and both rights; the stock bars
    with the SDK's default venue (nqb — what the stored bars were asked with); the index prices"""
    c, D = client(), dt.date.fromisoformat(day)
    if kind == 'chain':
        return c.option_history_quote(symbol=sym, expiration=D, interval='1m', date=D, strike='*', right='both')
    if kind == 'under':
        return c.stock_history_ohlc(symbol=sym, interval='1m', date=D)
    return c.index_history_price(symbol=sym, interval='1m', date=D)


def norm_ts(df, col='timestamp'):
    """build.py norm_ts: Datetime(ms, America/New_York); float NaN → null for every float column"""
    df = df.with_columns(pl.col(col).dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
    fl = [c for c, t in zip(df.columns, df.dtypes) if t in (pl.Float64, pl.Float32)]
    return df.with_columns([pl.col(c).fill_nan(None) for c in fl]) if fl else df


def shape(kind: str, sym: str, day: str, df) -> tuple[pl.DataFrame, list]:
    """build.py process() with no strike band (data_full): the chain's mid, its eight columns, sizes Int32; bars and prices
    as the SDK answers, the day's rows only. Problems said, nothing filled in."""
    probs = []
    if kind == 'chain':
        if df.height and 'expiration' in df.columns and set(df['expiration'].cast(pl.Utf8).str.replace_all('-', '').unique().to_list()) != {day.replace('-', '')}:
            probs.append('expirations other than the day')
        if df.height and 'symbol' in df.columns and set(df['symbol'].unique().to_list()) != {sym}:
            probs.append(f'roots other than {sym}: {df["symbol"].unique().to_list()[:4]}')
        out = df.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
        out = out.select(CHAIN_COLS).with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32))
        out = norm_ts(out).sort(['strike', 'right', 'timestamp'])
    else:
        out = norm_ts(df.select(df.columns)).sort('timestamp')
        other = out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') != day).height
        if other:
            probs.append(f'{other} rows of another day dropped')
        out = out.filter(pl.col('timestamp').dt.strftime('%Y-%m-%d') == day)
    ref = pl.read_parquet(STORED / B.rel_of(kind, sym, REF_DAY))
    if out.schema != ref.schema:
        probs.append(f'schema differs from the stored {REF_DAY}: {dict(out.schema)} vs {dict(ref.schema)}')
    return out, probs


def one(root: Path, kind: str, sym: str, day: str, run: str, requests: list) -> str:
    """ask, shape, validate, stage, place under `root`; the day's manifest says what happened; returns the status"""
    import grpc
    from thetadata.errors import NoDataFoundError
    rel = B.rel_of(kind, sym, day)
    sess = B.session_of(day)
    t0, delay, codes = time.time(), 2.0, []
    req = {'call': {'chain': 'option_history_quote', 'under': 'stock_history_ohlc', 'index': 'index_history_price'}[kind], 'symbol': sym, 'date': day}
    entry = {'run': run, 'request': req, 'fetched_at': R.iso_z(dt.datetime.now(R.UTC)), 'via': 'thetadata SDK 1.0.14 (gRPC)'}
    if kind == 'under':
        entry['venue'] = 'nqb (the SDK default, as the stored bars)'
    df = None
    for attempt in range(8):
        try:
            df = fetch_raw(kind, sym, day)
            codes.append('OK')
            break
        except NoDataFoundError as e:
            codes.append('NOT_FOUND')
            req.update(statuses=codes, seconds=round(time.time() - t0, 1))
            entry.update(status='FAILED', error=f'no data (NOT_FOUND) for a day the calendar calls a session ({sess["kind"]}) — not an empty session: {red(e)[:160]}')
            break
        except grpc.RpcError as e:
            code = e.code() if hasattr(e, 'code') else None
            det = red(getattr(e, 'details', lambda: '')())
            codes.append(str(code).replace('StatusCode.', ''))
            if code == grpc.StatusCode.UNAUTHENTICATED or 'session' in det.lower():
                req.update(statuses=codes)
                entry.update(status='FAILED', error=f'UNAUTHENTICATED — another login took the key\'s session; stopping: {det[:160]}')
                B.write_manifest(root, day, {rel: entry}, session=sess['kind'])
                requests.append({'file': rel, **req, 'status': 'FAILED'})
                raise SystemExit(red(entry['error']))
            if code in (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED,
                        grpc.StatusCode.UNKNOWN, grpc.StatusCode.INTERNAL, grpc.StatusCode.ABORTED) and attempt < 7:
                time.sleep(delay); delay = min(30.0, delay * 2)
                continue
            entry.update(status='FAILED', error=f'{code}: {det[:200]}')
            break
        except Exception as e:  # noqa: BLE001
            codes.append(type(e).__name__)
            if attempt < 3:
                time.sleep(delay); delay = min(30.0, delay * 2)
                continue
            entry.update(status='FAILED', error=red(f'{type(e).__name__}: {e}')[:200])
            break
    req.update(statuses=codes, seconds=round(time.time() - t0, 1))
    if df is not None and entry.get('status') is None:
        req['raw_rows'] = df.height
        if df.height == 0:
            entry.update(status='FAILED', error='an answer with no rows for a calendar session — not an empty session')
        else:
            out, probs = shape(kind, sym, day, df)
            staged = root / B.STAGING_DIR / run / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            out.write_parquet(staged, compression='zstd')
            entry.update(staged=str(staged.relative_to(root)), sha256=B.sha256_of(staged), rows=out.height)
            if probs:
                entry.update(status='FAILED', problems=probs)
            else:
                st, ck, vp = B.validate_frame(kind, sym, day, out, B.norms_for((STORED, root), kind, sym, day), sess)
                entry.update(status=st, checks=ck, problems=vp)
                if st == 'ok':
                    how = B.place(staged, root / rel, False, run)
                    entry['placed'] = how
                    if how == 'exists':
                        entry.update(status='FAILED', error='a different file is already there: not placed')
                    else:
                        staged.unlink()
                        entry['staged'] = None
    B.write_manifest(root, day, {rel: entry}, session=sess['kind'])
    requests.append({'file': rel, **req, 'status': entry['status']})
    log(entry['status'], rel, f"rows={entry.get('rows')}", req['statuses'], f"{req['seconds']}s", '; '.join(entry.get('problems') or []) or entry.get('error') or '')
    return entry['status']


def save_requests(root: Path, requests: list) -> None:
    f = root / B.MANIFEST_DIR / 'requests.jsonl'
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, 'a', encoding='utf-8') as fh:
        for r in requests:
            fh.write(red(json.dumps(r, default=str)) + '\n')


def main(step: str) -> int:
    run = dt.datetime.now(R.UTC).strftime('%Y%m%dT%H%M%SZ')
    requests: list = []
    try:
        if step == 'smallest':
            st = one(STAGING, 'under', 'SPY', START, run, requests)
            f = STAGING / B.rel_of('under', 'SPY', START)
            if f.exists():
                new, ref = pl.read_parquet(f), pl.read_parquet(STORED / B.rel_of('under', 'SPY', REF_DAY))
                log('schema equal to the stored', REF_DAY, new.schema == ref.schema, dict(new.schema))
                log('rows', new.height, 'vs', ref.height, 'first', new['timestamp'][0], 'last', new['timestamp'][-1], 'tz', new.schema['timestamp'])
            st2 = one(OVERLAP, 'under', 'SPY', REF_DAY, run, requests)
            if (OVERLAP / B.rel_of('under', 'SPY', REF_DAY)).exists():
                c = B.compare_frames('under', pl.read_parquet(OVERLAP / B.rel_of('under', 'SPY', REF_DAY)), pl.read_parquet(STORED / B.rel_of('under', 'SPY', REF_DAY)))
                log('the stored', REF_DAY, 'SPY bars fetched again: equal =', c['equal'], json.dumps(c, default=str)[:400])
                return 0 if (st == 'ok' and st2 == 'ok' and c['equal']) else 1
            return 1
        if step == 'all':
            bad = 0
            for day in B.weekdays(START, END):
                if B.session_of(day)['kind'] != 'full':
                    log('skip', day, B.session_of(day)['kind'])
                    continue
                # the bars and prices first (build.py's order: the chains read the day's price for their band)
                for kind, sym in [('under', 'SPY'), ('under', 'QQQ'), ('index', 'SPX'), ('index', 'VIX'), ('chain', 'SPY'), ('chain', 'QQQ'), ('chain', 'SPXW')]:
                    rel = B.rel_of(kind, sym, day)
                    if (STAGING / rel).exists():
                        log('held', rel)
                        continue
                    bad += one(STAGING, kind, sym, day, run, requests) != 'ok'
            return 1 if bad else 0
        if step == 'verify':
            rep = B.verify_parquet(STAGING, START, END, prior=False, norm_roots=(STORED,), stream=sys.stdout)
            (STAGING / B.MANIFEST_DIR / f'verify_{START}_{END}.json').write_text(json.dumps(rep, indent=1, default=str), encoding='utf-8')
            return 0 if rep['ok'] else 1
        if step == 'merge':
            res = B.merge_parquet(STAGING, STORED, force=False)
            print(json.dumps({k: v for k, v in res.items()}, indent=1, default=str))
            return res['rc']
        if step == 'final':
            rep = B.verify_parquet(STORED, '2026-10-05', END, prior=True, stream=sys.stdout)
            return 0 if rep['ok'] else 1
        print(__doc__)
        return 2
    finally:
        if requests:
            save_requests(STAGING if step != 'smallest' else STAGING, requests)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ''))
