"""All-ticker daily data from ThetaData (PRO), within what the account allows and the container can hold.
Phase A: bulk daily files for every allowed date (stocks EOD, every option contract's EOD, option open interest, indices EOD).
Phase B: stock daily bars for every symbol in thetadata_stocks.txt, one request per symbol-year (365-day request limit).
Phase C: index daily values for every symbol in thetadata_indices.txt, same scheme.
Phase D: option daily bars (every expiration and strike) for every root in thetadata_option_roots.txt, same scheme.
Phase E: option open interest for every root, same scheme. D and E need LAKE on large storage (tens of GB).
ONE login; worker threads share it; resumable (existing outputs skipped). Key from THETADATA_KEY only; exceptions redacted.
Usage: set -a; . "$SP/secrets/research.env"; set +a; python3 -I bulk_fetch.py [A] [B] [C] [D] [E]"""
import os, re, sys, time, json, threading, logging, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl, grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
LAKE = os.environ.get('LAKE', SP + '/lake'); os.makedirs(LAKE + '/logs', exist_ok=True)
NW = int(os.environ.get('NW', '6'))
FLAT_DATES = os.environ.get('FLAT_DATES', '2026-10-06,2026-10-07,2026-10-08,2026-10-09,2026-10-12,2026-10-13').split(',')
YEARS = [int(y) for y in os.environ.get('YEARS', '2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012').split(',')]
YEAR_END = dt.date(2026, 10, 13)
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
def log(*a): print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *[red(x) for x in a], flush=True)
lock = threading.Lock(); state = dict(client=None, gen=0)
def client(gen_seen=None):
    with lock:
        if state['client'] is None or (gen_seen is not None and gen_seen == state['gen']):
            state['client'] = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars'); state['gen'] += 1; log('login gen', state['gen'])
        return state['client'], state['gen']
def call(fn_name, **kw):
    for attempt in range(6):
        c, g = client()
        try: return getattr(c, fn_name)(**kw)
        except NoDataFoundError: return None
        except grpc.RpcError as e:
            code = e.code() if hasattr(e, 'code') else None
            if code == grpc.StatusCode.UNAUTHENTICATED: client(g); continue
            if code in (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.INTERNAL, grpc.StatusCode.UNKNOWN): time.sleep(2 + 3 * attempt); continue
            if code in (grpc.StatusCode.PERMISSION_DENIED, grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.NOT_FOUND): return ('denied', red(str(e.details()))[:160])
            raise
    return ('failed', 'retries exhausted')
def write(df, p):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'; df.write_parquet(tmp, compression='zstd'); os.replace(tmp, p)
def phase_a():
    kinds = [('stock_eod', 'stock_flat_file_eod'), ('option_eod', 'option_flat_file_eod'), ('option_oi', 'option_flat_file_open_interest'), ('index_eod', 'index_flat_file_eod')]
    for d in FLAT_DATES:
        for k, fn in kinds:
            p = f'{LAKE}/flat/{k}/{d}.parquet'
            if os.path.exists(p): continue
            t0 = time.time(); df = call(fn, date=dt.date.fromisoformat(d))
            if isinstance(df, tuple) or df is None: log('A', k, d, 'no data', df); continue
            write(df, p); log('A', k, d, df.height, 'rows', round(time.time() - t0, 1), 's', round(os.path.getsize(p) / 1e6, 1), 'MB')
def per_symbol_year(tag, kind, listfile, fn, part, **extra):
    """One request per symbol per calendar year (365-day limit); `part` symbols per Parquet file; resumable.
    Symbols whose request was denied or failed are listed in {LAKE}/{kind}/failed.jsonl for a retry pass."""
    syms = [s for s in open(HERE + '/' + listfile).read().split() if s]
    for y in YEARS:
        a, b = dt.date(y, 1, 1), min(dt.date(y, 12, 31), YEAR_END)
        for i in range(0, len(syms), part):
            p = f'{LAKE}/{kind}/year={y}/part-{i // part:03d}.parquet'
            if os.path.exists(p): continue
            batch = syms[i:i + part]; t0 = time.time(); frames = []; nd = 0; bad = []
            with ThreadPoolExecutor(NW) as ex:
                futs = {ex.submit(call, fn, symbol=s, start_date=a, end_date=b, **extra): s for s in batch}
                for f in as_completed(futs):
                    s = futs[f]
                    try: df = f.result()
                    except Exception as e: bad.append((s, type(e).__name__ + ' ' + red(e)[:120])); continue
                    if df is None: nd += 1; continue
                    if isinstance(df, tuple): bad.append((s, ' '.join(df))); continue
                    if df.height: frames.append(df.with_columns(pl.lit(s).alias('symbol')))
            out = pl.concat(frames, how='diagonal_relaxed') if frames else pl.DataFrame({'symbol': []})
            write(out, p)
            if bad:
                with open(f'{LAKE}/{kind}/failed.jsonl', 'a') as fh:
                    for s, why in bad: fh.write(json.dumps({'year': y, 'part': i // part, 'symbol': s, 'error': why}) + '\n')
            log(tag, y, f'part {i // part:03d}', 'symbols with data', len(frames), 'nodata', nd, 'denied/err', len(bad), 'rows', out.height, round(time.time() - t0, 1), 's')
def phase_b(): per_symbol_year('B', 'stock_eod', 'thetadata_stocks.txt', 'stock_history_eod', 500)
def phase_c(): per_symbol_year('C', 'index_eod', 'thetadata_indices.txt', 'index_history_eod', 500)
def phase_d(): per_symbol_year('D', 'option_eod', 'thetadata_option_roots.txt', 'option_history_eod', int(os.environ.get('OPT_PART', '100')), expiration='*')
def phase_e(): per_symbol_year('E', 'option_oi', 'thetadata_option_roots.txt', 'option_history_open_interest', int(os.environ.get('OPT_PART', '100')), expiration='*')
if __name__ == '__main__':
    ph = sys.argv[1:] or ['A', 'B']
    for k, f in [('A', phase_a), ('B', phase_b), ('C', phase_c), ('D', phase_d), ('E', phase_e)]:
        if k in ph: f()
    log('DONE')
