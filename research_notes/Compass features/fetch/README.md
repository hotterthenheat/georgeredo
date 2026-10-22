# Compass features — the data fetch

`fetch_features.py` fetches exactly the frozen scope (`features_scope.md` in the coordinator's scratchpad): the UW feature
routes for the index names and the ThetaData base-trade gaps. It computes no feature, return or P&L.

`SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`

## Restart after a container restart (one line)

```
cd "/home/user/georgeredo/research_notes/Compass features/fetch" && (setsid nohup ./run_uw.sh >/dev/null 2>&1 </dev/null &) && (setsid nohup ./run_theta.sh >/dev/null 2>&1 </dev/null &)
```

Both are fully resumable: a UW item is done when `<date>.parquet`, `.empty`, `.oow` (out of UW's window) or `.refused`
exists; a Theta file is done when it is in the stored root. Errors leave no marker, so a restart asks them again. Writes
are `.part` then renamed, so a kill never leaves half a file. The Theta process waits out 00:00–01:45 New York by itself.

Progress: `python3 -I fetch_features.py status` or `$SP/features_data/STATUS.json` (a `uw` and a `theta` section,
rewritten every 50 items). Logs: `$SP/features_data/uw_log.ndjson` (every call: route, ticker, date, page, status,
bytes, ms, rows — no token), `uw_stdout.log`, `theta_stdout.log`, `theta_manifest.ndjson` (every Theta file: request
seconds, rows, bytes, checks, problems, where it was placed).

Keys: `run_*.sh` load `$SP/secrets/research.env` inside the process; the token goes in a header only; every text kept
passes `red()` and the launcher's sed (`td1_prod_…` → `[key]`). Python runs with `-I`.

## UW (`python3 -I fetch_features.py uw`)

Index names SPY, QQQ, IWM, SPX; span 2023-11-21 → 2026-10-21 (731 sessions; the calendar is the SPXW same-day chain files'
dates). Stored compact: `$SP/features_data/uw/<route>/<ticker>/<date>.parquet` (zstd; numbers typed, times UTC; only the
fields listed in `SPECS`). Order (dataset by dataset, oldest date first, the names inside a date):

| route | call | names | notes |
|---|---|---|---|
| spot_exposures | `/stock/{T}/spot-exposures?date=D` | 4 | from 2023-12-08 (UW's start); the per-minute whole-book GEX/charm/vanna, `_oi/_vol/_dir` |
| greek_exposure_strike | `/stock/{T}/greek-exposure/strike?date=D` | 4 | D's end state; the feature for D reads D−1's file |
| gex_levels | `/stock/{T}/gex-levels?date=D` | 4 | a row with every level null is stored `.empty` (SPY/SPX before 2024-05-13) |
| net_prem_ticks | `/stock/{T}/net-prem-ticks?date=D` | 4 | |
| flow_alerts | `/option-trades/flow-alerts?ticker_symbol=T&min_premium=25000&limit=200&newer_than&older_than` | SPY QQQ IWM SPX **SPXW** | SPX's alerts are filed under two roots (smoke: SPX 55 + SPXW ≥200 on 2026-10-20); walked back on `created_at` over New York's day; **cap 40 pages (8,000 alerts) a ticker-day** (`.meta.json` says when hit) |
| market_tide | `/market/market-tide?date=D` | market | default answer (5-minute rows), as the cached days were asked |
| nope | `/stock/{T}/nope?date=D` | SPY QQQ IWM | SPX answered empty on 2026-10-21 when SPY was served: not asked. Start bisected on SPY with ≤ 6 calls (`uw/nope/_start.json`); dates before it are inferred empty, not asked |
| oi_chain | `/stock/{T}/option-contracts?date=D&exclude_zero_oi_chains=true&limit=500&page=n` | 4 | `date` is honoured (smoke: 2024-06-03 returned 2024 contracts); option_symbol, open_interest, prev_oi, last_tape_time; the OI dated D is D−1's close (published the morning of D) — every session is fetched, so D and D−1 are both there; **cap 30 pages a ticker-day, SPX 60** |
| darkpool | `/darkpool/{T}?date=D&min_premium=1000000&limit=500&newer_than&older_than` | SPY QQQ IWM | the $1M floor is honoured (smoke); SPX has no prints; **cap 20 pages (10,000 prints) a ticker-day** |

Rate: 1 in flight 09:00–17:00 New York on weekdays, 2 otherwise, never more than 3, ≥ 1.2 s between starts; a 429 pauses
every worker (30 s doubling to 15 min); 429/5xx/network retried 6 times. A 403 "historic" is out of UW's rolling window
(`.oow`); other 4xx are `.refused`, and three in a row for one route and name skip the rest of that pair. An empty answer
on or after the route's served start is logged as a `gap`.

Reused from disk instead of asked (`uw/_reused.json`): bt/cache gex-levels (SPY/SPX 2023-11-21→2026-10-09, QQQ/IWM
2025-05-22→), net-prem-ticks (SPY/QQQ/IWM 342 days), spot-exposures (SPY 61 days), market-tide (342 days); the recorder's
2026-10-21 pass (net-prem-ticks, flow alerts — split SPX/SPXW —, dark pool filtered to ≥ $1M, the chain's OI); the
inventory's probe answers. A fresh call equalled the cached answer on the two dates checked (spot-exposures SPY
2026-08-05, gex-levels SPY 2024-08-02). Not reused: bt/cache dark-pool pages (unfiltered, completeness per day unknown —
asked again with the floor, one or two pages a day).

## ThetaData (`python3 -I fetch_features.py theta`)

The `thetadata` SDK exactly as `Compass phase 3/forward_2026-10-12_2026-10-21/sdk_fetch.py` (it is imported: its
`client()` single login, `fetch_raw`/`shape`/`one()` for the stored layout, venue nqb for stock bars). Never asked
between 00:00 and 01:45 New York. Order:

1. Smoke: IWM 2026-10-12 minute bars, schema against the stored IWM 2026-10-09 (stops on a mismatch).
2. IWM bars and same-day full chains 2026-10-12→21 → staged in `$SP/features_data/theta_staging`, validated
   (`paper_backtest.validate_frame` against the stored norms), merged by `paper_backtest.merge_parquet` (refuses any
   overlap).
3. The 11 singles' minute bars 2026-10-12→21 → `theta/fetch_cache/underlying/<S>/<D>.parquet`.
4. The 11 singles' expiry-day chains for their listed expiries 2026-10-12→21 → `fetch_cache/chains_exp/<S>/<D>__<D>.parquet`
   (NaN kept for no quote, as the stored files).
5. EOD (`option_history_eod`, every expiry, a Mon–Fri week a request, named by the week's first and last session) →
   `fetch_cache/eod_all/<S>/<w0>__<w1>.parquet` in its 14-column schema: SPY/QQQ/IWM 2026-10-12→21; the singles
   2022-11-01→2026-10-21 (AAPL from 2025-09-08: earlier weeks are on disk).
6. SPXW EOD with `max_dte=60`: one week measured first; fetched (into `eod_all/SPXW`) only if 207 weeks project
   < ~2 h and < 0.5 GB, else skipped with the reason in STATUS `notes.spxw_eod_measure`.

Every file: fetch → shape → stage → verify (schema equal to the stored files, every minute / every session of the week,
no duplicate key, norms of the 20 files before) → placed only where no file exists (never overwritten). SDK concurrency:
the first EOD jobs run 4 at 1 in flight, then 4 at 2, then 4 at 4; a level is kept only with no error and ≥ 20% less
wall time a job (STATUS `notes.sdk_concurrency_test`). Not fetched (as the forward fetch): IWM's band chains and
per-contract bars (`data/chain`, `data/ohlc`).

Disk guard: both processes stop cleanly (state in STATUS.json) when free space falls under 1.5 GB.
