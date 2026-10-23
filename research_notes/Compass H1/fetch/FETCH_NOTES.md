# H1 stage 1 — the fetch (2026-10-22, 20:31–20:32 New York)

One process, one ThetaData login (thetadata SDK 1.0.14, gRPC), one request in flight, started at 20:31 New York (after the
owner's daily job's 19:40–20:30 window), 72 s from login to exit; the session closed with the process. The key was read from the
environment inside the process only and never printed, logged or written (every logged text passes `red()`; the logs were
scanned for `td1_prod_` before commit). Script: `fetch_h1.py`; log: `fetch_log.jsonl`, `run_fetch.out`; summary:
`fetch_summary.json`. No outcome was computed or printed.

**What was on disk before** (listed first, as the spec asks):
- 1-minute bars `$SP/theta/data/underlying/{SPY,QQQ}/<day>.parquet` (391 rows 09:30–16:00): QQQ priced on every session from
  2012-06-01 (3,360 sessions to 2025-10-10, no holiday files); SPY: a file on every session from 2012-06-01, but the 1,154 files
  2012-06-01 → 2016-12-30 have every price NaN; priced from 2017-01-03 (SPY also has all-NaN files on holidays from 2017, not
  sessions).
- ThetaData stock EOD: `$SP/lake/stock_eod/year=2019` (2019) and `data_lake/thetadata/stock_eod/year=2020…2026` (to 2026-10-13);
  SPY and QQQ 1,956 rows each 2019-01-02 → 2026-10-13, no duplicates, `created` date = `last_trade` date on every row.

**Requests (15 in all, 142,147 bytes written to `$SP/lake/stock_eod_h1/`, plus the 81,028-byte combined
`../data/stock_eod_2012_2018.parquet`, sha256 `80e4cedba55c1226b3ecd8e32655ba35a9489aa10c35a88422f8b70880a39cf5`):**

| request | answer |
|---|---|
| `stock_history_eod(SPY, Jan 1 – Dec 31)` for 2012, 2013, 2014, 2015, 2016 (5 calls; `data_lake/fetch/bulk_fetch.py` phase B's call) | NOT_FOUND every year — ThetaData serves no SPY stock EOD before 2017 |
| `stock_history_eod(QQQ, …)` 2012–2016 (5 calls) | 146 rows (2012-06-01 →), 252, 252, 252, 252 |
| `stock_history_eod(SPY, …)`, `(QQQ, …)` 2017, 2018 (4 calls) | 251 and 251 rows each |
| ONE probe: `stock_history_ohlc(SPY, interval='1m', date=2016-06-01)` (venue nqb, `sdk_fetch.py`'s call) | 391 rows, the stored file's schema, **every price NaN** (0 priced bars) |

**The SPY bar fetch was not run** (the probe came back NaN, as the stored files): SPY starts 2017-01-03 — both its 1-minute bars
and its EOD close. Nothing was staged, nothing merged, no stored file touched (no `.orig` written).

**Coverage after the fetch** (sessions = QQQ's file dates, 2025-10-10 the last signal session): SPY 2,206 sessions 2017-01-03 →
2025-10-10 and QQQ 3,360 sessions 2012-06-01 → 2025-10-10, each with an EOD row on every session, no EOD row on a non-session,
no duplicate EOD rows (the 2012–2018 rows too).

**Dividends** (not ThetaData; fetched the same evening for the P&L's dividend term): Nasdaq's dividend history for QQQ
(`api.nasdaq.com`; it serves none for SPY) and the dividend events of Yahoo's chart answer for both names (only the events kept;
the price arrays discarded unread), 9.7 KB and 2.8 KB, in `../data/dividends_raw/`; merged into `../data/dividends.json`.
QQQ: the two sources agree to $0.0005 on the 54 dates both carry; Yahoo lacks 2020-09-21 (Nasdaq has it), Nasdaq lacks
2012-09-21 and 2012-12-21 (Yahoo's used).
