# ThetaData 0DTE research dataset

Minute-level option chains for the same-day expiration of **SPY, QQQ, IWM and SPXW**, near the money, with the underlying and
index minute series, pulled from ThetaData (PRO key) with the official `thetadata` Python client 1.0.14 (gRPC; no Theta Terminal).
The data lives **outside the repo** (`$THETA_DS_ROOT`, default `<scratchpad>/theta/data`); this directory holds the committed
manifest (`MANIFEST.md`, `manifest.csv.gz`: one row per file with rows, strikes, min/max strike, sha256, bytes), the loader
(`load.py`), the build/verify scripts and the expiration lists the date ranges were derived from.

## Coverage

| Symbol | First daily-expiry date | Rule |
|---|---|---|
| SPY | 2022-11-11 | first session after which every NYSE weekday session to 2026-10-09 is in `option_list_expirations('SPY')` |
| QQQ | 2022-11-11 | idem |
| SPXW | 2022-05-13 | idem (`SPXW` root; the plain `SPX` root does not return weeklies) |
| IWM | 2024-04-19 | idem |

(`first_daily.py` over `expirations/expirations_*.csv`, pulled 2026-10-13.  Sessions = weekdays minus NYSE full closes in
`calendar_2017_2026.csv`; early-close days are sessions and hold data to the early close.)  Underlying and index series:
every session 2017-06-01 → 2026-10-09.

## Layout (Parquet, zstd, polars-written; one file per symbol-session)

| Path | Columns | Notes |
|---|---|---|
| `chains/{SPY,QQQ,IWM,SPXW}/{date}.parquet` | timestamp, strike, right, bid, ask, bid_size, ask_size, mid | 1-minute NBBO 09:30–16:00 of the same-day expiry, both rights, strikes in the band; the 09:30:00 row is a null placeholder |
| `ohlc/{symbol}/{date}.parquet` | timestamp, strike, right, open, high, low, close, volume, count, vwap | 1-minute option OHLC for the same strikes; only minutes with trades |
| `underlying/{SPY,QQQ,IWM}/{date}.parquet` | timestamp, open, high, low, close, volume, count, vwap | 1-minute stock bars 09:30–16:00 |
| `index/{SPX,VIX}/{date}.parquet` | timestamp, price | index value at each minute boundary; 09:30:00 is null |

A `{date}.nodata` marker means the API answered "no data" for that session (listed in `MANIFEST.md`).

**Strike band**: `ref·0.98 ≤ strike ≤ ref·1.02`, `ref` = the 09:31 underlying print: ETFs → `open` of the stock bar stamped
09:31:00; SPXW → SPX index `price` stamped 09:31:00; first non-null at/after 09:31 if that is null (`ref_status=fallback`
in the manifest, with `ref_time`).  The whole chain (`strike='*'`) is fetched in one request per symbol-session per data type and
filtered locally; `raw_rows`/`raw_strikes` in the manifest record the full-chain size.

**Conventions**: `timestamp` is polars `Datetime('ms', 'America/New_York')` (parquet stores it with the timezone).  Quote
rows hold the last NBBO at the minute boundary; OHLC bars are stamped at their opening minute.  Missing numbers are null
(the client's NaN placeholders are converted).  `right` is `CALL`/`PUT`; `mid = (bid+ask)/2` (null if either side is null).
Reading needs polars only (`load.py` converts to pandas without pyarrow via `to_dict`).

## Loader

```python
import sys; sys.path.insert(0, 'research/thetadata/dataset'); import load as L
L.chain('SPY', '2024-06-03')                 # polars frame; L.chain(..., as_pandas=True) for pandas
L.ohlc('SPXW', '2024-06-03'); L.underlying('QQQ', '2019-03-01'); L.index('VIX', '2021-01-04')
L.ref_price('SPXW', '2024-06-03')            # (5296.37, '09:31:00', 'ok'); L.band(ref) -> (lo, hi)
L.sessions('chains', 'IWM'); L.nodata_sessions('chains', 'IWM'); L.trading_sessions('2022-11-11', '2026-10-09')
L.scan('chains', 'SPY', '2024-01-01', '2024-12-31').collect()    # lazy concat with a `date` column
L.manifest()                                 # manifest.csv.gz as a frame
```

## Exact build commands (run from this directory; key only from the env file, never printed)

```bash
SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad
cd /home/user/georgeredo/research/thetadata/dataset
# full build (resumable: existing files / .nodata markers are skipped). ONE login; 6 worker processes reuse the session token.
set -a; . "$SP/secrets/research.env"; set +a; THETA_DS_MAX_SECS=10800 setsid nohup python3 -I fetch.py underlying chains ohlc > "$SP/theta/ds/logs/build.log" 2>&1 < /dev/null &
# progress: $THETA_DS_ROOT/progress.json (every 100 jobs) and _jobs.jsonl (one line per job)
# spot-check against fresh 1-second pulls (only when no other fetch process holds the key):
set -a; . "$SP/secrets/research.env"; set +a; python3 -I verify.py 5 7
# manifest (no network):
python3 -I manifest.py
```

Phases: `underlying` converts the index_tests cache (SPX, VIX, SPY monthly CSVs pulled 2026-10-13 with the same client) and
fetches QQQ/IWM monthly stock bars; `chains` then `ohlc` run SPY → QQQ → SPXW → IWM.  `THETA_DS_MAX_SECS` stops feeding new
jobs after that many seconds (in-flight jobs finish; partial output is complete per file).  `THETA_DS_NWORK` (default 6, PRO
allows 8 concurrent requests), `THETA_DS_LIMIT` (debug: sessions per symbol).

Session handling: the parent authenticates once (`ThetaClient(api_key=…)`); workers build clients with
`ThetaClient(existing_authorized_client=…)` from the shared session id (no further logins).  A gRPC `UNAUTHENTICATED` /
"Invalid session ID" (another study logged in with the key) makes the parent re-login once and re-queue the job; `login_gen` in
`progress.json` counts logins.  `RESOURCE_EXHAUSTED`/`UNAVAILABLE`/`DEADLINE_EXCEEDED` are retried with backoff (2…30 s, ≤ 8 tries);
each request carries a 420 s deadline.  Exception text is redacted (`td1_prod_…` → `REDACTED`).

## Provenance of the first-daily dates
`expirations/expirations_{SPY,QQQ,IWM,SPXW}.csv` are the raw `option_list_expirations` responses (2026-10-13);
`first_daily.py` walks the NYSE sessions backwards from 2026-10-09 and reports the first session after the last one without an
expiration (2025-01-09, the Carter day of mourning, is listed as an expiration but was not a session).
