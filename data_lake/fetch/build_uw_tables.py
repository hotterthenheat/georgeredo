"""Turn the raw Unusual Whales per-ticker JSON (gzip) under $LAKE/uw/<endpoint>/ into one Parquet table per endpoint
(rows = the response's data records, plus a `ticker` column; dict-shaped responses become one row). Values are kept as
strings where the API returns strings. Output: $LAKE/uw_tables/<endpoint>.parquet and a summary JSON."""
import os, sys, gzip, json, glob
import polars as pl
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
LAKE = os.environ.get('LAKE', SP + '/lake'); OUT = LAKE + '/uw_tables'; os.makedirs(OUT, exist_ok=True)
summary = {}
for d in sorted(glob.glob(LAKE + '/uw/*')):
    ep = os.path.basename(d); rows = []; err = 0; empty = 0
    for f in sorted(glob.glob(d + '/*.json.gz')):
        t = os.path.basename(f)[:-8]
        try: j = json.loads(gzip.open(f).read())
        except Exception: err += 1; continue
        if isinstance(j, dict) and 'error' in j and len(j) == 1: err += 1; continue
        x = j.get('data') if isinstance(j, dict) and 'data' in j else j
        if isinstance(x, dict): x = [x]
        if not x: empty += 1; continue
        for r in x:
            if isinstance(r, dict):
                rec = {k: (json.dumps(v) if isinstance(v, (dict, list)) else (None if v is None else str(v))) for k, v in r.items()}
                rec['ticker'] = t; rows.append(rec)
    if not rows: summary[ep] = dict(rows=0, errors=err, empty=empty); continue
    df = pl.from_dicts(rows, infer_schema_length=None)
    p = f'{OUT}/{ep}.parquet'; df.write_parquet(p, compression='zstd')
    summary[ep] = dict(rows=df.height, tickers=df['ticker'].n_unique(), columns=df.columns, errors=err, empty=empty, mb=round(os.path.getsize(p) / 1e6, 1))
    print(ep, {k: v for k, v in summary[ep].items() if k != 'columns'}, flush=True)
json.dump(summary, open(OUT + '/_summary.json', 'w'), indent=1)
