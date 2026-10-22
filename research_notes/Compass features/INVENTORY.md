# Compass features — Step 0: data inventory (2026-10-22)

This is an inventory only. No feature result, return or P&L was computed, and nothing was pre-registered. Nothing was fetched from ThetaData. Unusual Whales (UW) got 28 single GET calls, one in flight at least 2.2 s apart (listed in §2). Their raw answers are in the scratch folder `$SP/feature_inventory/` (`calls.jsonl` plus one JSON file a call), where `SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`.

**Spans used below**
- **Base span**: 2022-11-11 → 2026-10-21, 988 sessions. This is the first SPY/QQQ daily-expiry session through the last complete session. The calendar is the SPXW 0DTE files' dates; the SPY bar folder also holds empty holiday files and was not used.
- **UW span**: 2023-11-21 → 2026-10-21, 731 sessions. UW's window floor today, read off its own 403 (call 01).

**Universe proposed** (single stocks ranked by option contracts a day over the only five sessions with every root on disk, the flat files of 2026-10-06…12)
- **Index/ETF**: SPY, QQQ, IWM, SPXW (SPX), XSP, NDXP (NDX), RUTW (RUT), DIA.
- **Single stocks, 30, in three liquidity tiers**:
  - T1, ≥ 0.9 M contracts a day: NVDA, TSLA, AAPL, MU, SPCX, INTC, AMZN.
  - T2, 0.4–0.9 M: META, PLTR, AMD, MSFT, GOOGL, MSTR.
  - T3, 0.16–0.4 M: AVGO, SOFI, ORCL, GME, IREN, NFLX, CRWV, HOOD, NBIS, ASTS, MRVL, SMCI, MARA, WULF, SNDK, SKHY, WMT.
- **Optional ETF add-on, 10** (high option volume, not index products): TLT, EWZ, IBIT, HYG, SLV, SOXL, TQQQ, XLF, GLD, SMH.
- Recency bias in this ranking is blocker B9.

---

## 1. On disk

`$SP` = the scratch root above. "Repo" = `/home/user/georgeredo`. Sizes are bytes on disk.

### 1a. ThetaData, by dataset

| Dataset | Granularity | Tickers | Span (sessions) | Size | Where |
|---|---|---|---|---|---|
| **0DTE full chains**, NBBO bid/ask/size/mid, every strike, same-day expiry | 1-min | SPY, QQQ | 2022-11-11 → 2026-10-21 (988 each, complete) | 614 / 589 MB | `$SP/theta/data_full/chains/` |
| | | SPXW | 2022-05-13 → 2026-10-21 (1,114, complete) | 908 MB | same |
| | | IWM | 2024-04-19 → 2026-10-09 (621) | 204 MB | same |
| 0DTE near-money band chains, plus per-contract OHLCV/VWAP | 1-min | SPY, QQQ, SPXW, IWM | as above, ending 2026-10-09 | 145+120, 127+108, 258+272, 39+31 MB | `$SP/theta/data/chain`, `data/ohlc` |
| The forward fetch through the SDK (merged into the above) and the reference day | 1-min | SPY, QQQ, SPXW; SPY/QQQ bars; SPX/VIX | 2026-10-12 → 21; 2026-10-09 | 18.7 MB; 2.3 MB | repo `data/theta_forward`, `data/theta_reference` |
| **Single-name expiry-day (0DTE) full chains**, NBBO | 1-min | AAPL, AMZN, AVGO, GOOGL, MSFT, NVDA, TSLA | 2017-06-02 → 2026-10-09 (552–559 each: every Friday expiry, plus Mon/Wed/Fri in 2026) | 110–336 MB each | `$SP/theta/fetch_cache/chains_exp/` |
| | | AMD, INTC, MU | 2017-06-02 → 2026-10-09 (513–516) | 74–134 MB | same |
| | | META | 2021-07-16 → 2026-10-09 (302) | 123 MB | same |
| | | FB | 2017-06-02 → 2022-06-03 (262) | 53 MB | same |
| | | SPXW (early) | 2017-06-30 → 2022-04-29 (56, sample) | 48 MB | same |
| **Weekly 1–7 DTE full chains** (nearest Friday), NBBO | 1-min | SPY | 2017-06-01 → 2026-10-09, 468 sessions: a **stratified sample**, not consecutive | 365 MB | `$SP/theta/fetch_cache/chains_exp/SPY` |
| | | QQQ, IWM | 2017-06-01 → 2026-10-07, 294 each, sample | 205 / 134 MB | same |
| Weekly per-contract OHLCV | 1-min | SPY / QQQ / IWM | 471 / 294 / 294 sessions, same sample | 76 / 44 / 21 MB | `fetch_cache/ohlc_exp` |
| **Option EOD, every expiry**: OHLC, volume, count, closing NBBO | daily, weekly files | SPY, QQQ, IWM | 2012-06-01 → 2026-10-05 (750 weeks) | 381 / 249 / 172 MB | `fetch_cache/eod_all` (the same rows regrouped in `$SP/lifecycle/eod_by_exp`, 0.8 GB) |
| | | AAPL | 2015-03-02 → 2025-09-02 (437 weeks) | 66 MB | same |
| | | FB | 2017-06 → 2022-06 | 35 MB | same |
| Option EOD, monthly cycles | daily | SPY, QQQ | 2012-06-15 → 2026-09-18 (168 cycles each) | 7.5 MB | `fetch_cache/eod_monthly` |
| Option EOD, earnings windows (one expiry per event) | daily | 520 roots | 2024-01-02 → 2026-09-01 (1,312 windows) | 44 MB | `fetch_cache/eod_exp` |
| **Open interest** | daily | SPY (weeklies only) | 2017-06-01 → 2023-06-26 (1,525 days) | 4.9 MB | `fetch_cache/oi` |
| Option EOD, every root (flat files) | daily | about 6,290 roots, 2.05 M contracts a day | 2026-10-06 → 2026-10-12 (5 sessions) | 145 MB | repo `data_lake/thetadata/flat/option_eod` |
| Open interest, every contract (flat files) | daily | every root | 2026-10-06 → 12 | 52 MB | `.../flat/option_oi` |
| **Underlying bars** OHLCV | 1-min | SPY, QQQ | 2012-06-01 → 2026-10-21 (**usable from 2017**; 2012–16 prices are NaN) | 33 / 41 MB | `$SP/theta/data/underlying` |
| | | IWM | 2012-06-01 → 2026-10-09 | 31 MB | same |
| | | 41 names: AAPL ADBE AMD AMZN AVGO COIN COST GOOG GOOGL HYG INTC IVV JPM LLY LQD META MSFT MSTR MU NFLX NVDA SMCI SMH SOXL TLT TQQQ TSLA TSM UNH V VOO XLF XOM… | 2017-06-01 → 2026-10-09. Ends early: BAC → 2021-06, CRM → 2025-05, DIA → 2025-06-30, GLD/PLTR → 2025-02-28, QCOM → 2022-07, SQQQ → 2022-04, FB → 2022-06 | 980 MB | `fetch_cache/underlying` |
| **Index level** | 1-min | SPX, VIX | 2017-06-01 → 2026-10-21 (2,361 / 2,394) | 8 / 7 MB | `$SP/theta/data/index` |
| Stock EOD, every symbol | daily | about 14,000 a year | 2019 ($SP only), 2020 → 2026-10-13 | 509 MB repo, plus 58 MB | `data_lake/thetadata/stock_eod`, `$SP/lake` |
| Stock EOD (v3) | daily | 12 names | 2017-01-03 → 2026-10-09 | 1.1 MB | `fetch_cache/v3_eod` |
| Expirations ever listed | list | 15,817 roots | 2012 → | 1 MB | repo `data_lake/universe/expirations.jsonl.gz` |

**Not stored anywhere**
- ThetaData IV or greeks, at any granularity.
- 1-min chains for 8–60 DTE.
- Consecutive 1-min chains for 1–7 DTE (only a sample is stored).
- Daily open interest after 2023-06, and before then for anything but SPY weeklies.
- Any option data for XSP, NDXP, RUTW, DIA.
- RUT or NDX index levels.

### 1b. Unusual Whales, by dataset

| Dataset (route) | Granularity | Tickers | Span | Size | Where |
|---|---|---|---|---|---|
| Daily bars (`ohlc/1d`), info, max-pain snapshot | daily | 9,610 / 15,676 | 2025-10-13 → 2026-10-13 | 92 MB | repo `data_lake/unusualwhales` |
| Earnings (`earnings`): report date, pre/post time, EPS, estimate | event | 5,805 | 1996-01-31 → 2026-12-17 (scheduled) | 3 MB | same |
| Ticker GEX/DEX/charm/vanna series (`greek-exposure`) | daily | 6,014 | 2025-10-15 → 2026-10-13 | 63 MB | same |
| IV rank (1 y), realized vol, variance risk premium | daily | about 6,000 | about 2025-10 → 2026-10-13 | 45 MB | same |
| **GEX levels** (`gex-levels`: walls, flip, magnet; source "vol") | daily, one row a date | SPY, SPX | 766 dates 2023-11-13 → 2026-10-09; **non-null from 2024-05-13** | 0.5 MB | `$SP/bt/cache` |
| | | QQQ, IWM | 348 dates 2025-05-22 → 2026-10-09 | | same |
| Per-minute GEX series (`spot-exposures`) | 1-min | SPY | 61 dates 2025-06-02 → 2026-10-09 | 2.5 MB | same |
| Net premium ticks (`net-prem-ticks`) | 1-min | SPY, QQQ, IWM | 342 dates 2025-06-02 → 2026-10-09 | 24 MB | same |
| Market tide | 5-min | market | 343 dates 2025-06-02 → 2026-10-09 | 0.6 MB | same |
| Interpolated IV | daily | SPY, QQQ, IWM | 348 dates 2025-05-22 → 2026-10-09 | 0.3 MB | same |
| Stock bars (`ohlc/1m`) | 1-min | SPY, QQQ, IWM | 348 dates 2025-05-22 → 2026-10-09 | 21 MB | same |
| Dark pool prints (paged) | print | SPY, QQQ, IWM | 93 dates 2025-06-30 → 2026-10-08 (pages; completeness per day not checked) | 87 MB | same |
| Flow per strike, intraday | 1-min, top strikes | SPY, QQQ, IWM | 42 dates 2025-07-07 → 2026-10-08 | 36 MB | same |
| Contract minutes (`option-contract/{id}/intraday`: side volume and premium, iv_high/low) | 1-min | QQQ 5,276, SPY 4,832, IWM 3,462, SPXW 256 contract-days, a few others | 2025-06-02 → 2026-10-13 | 185 MB | same |
| **Dated chains** (`option-contracts?date&expiry`: OI, prev OI, IV, greeks, closing NBBO, side/sweep/floor volume) | EOD, one expiry a file | 2,493 tickers | 711 dates 2023-11-15 → 2026-10-01, **sparse** (monthly-cycle dates: SPY 34 sessions, NVDA 69) | 830 MB | `$SP/uw_chains` |
| The recorder's EOD pass: flow alerts ≥ $25K, dark pool, net-prem-ticks, 1-min bars, OI by strike, full chain | as listed | 24 names (SPX, SPY, QQQ, IWM and 20 single names/ETFs) | **one session, 2026-10-21** | 20 MB | repo `data_recorder/` |
| | spot-exposures/strike (smoke) | SPY, SPX | 2026-10-21 (captured 20:36Z) | <1 MB | `data_recorder/smoke` |

### 1c. Events and closes

| Dataset | Span | Where |
|---|---|---|
| Macro releases: FOMC decisions 48, FOMC minutes 41, CPI 71, NFP 71 (231 in all, 191 released and 40 scheduled) | 2022-01-05 → 2027-12-10 | repo `data/macro_events_2022_2027.json` |
| UW earnings calendar | 1996 → 2026-12 | §1b |
| Official SPX close (Cboe history) | 1975-01-02 → 2026-10-21 | repo `data/official_closes/cboe_SPX_History_2026-10-22.csv` |
| UW daily bars SPY/QQQ (official close) | 2026-10-08 → 21 | `data/official_closes/uw_ohlc_1d_2026-10-22.parquet` |
| SPY/QQQ post-market 1-min | 2026-10-12 → 21 | `data/postmarket_1m` |

### 1d. Everything else under `$SP`

Research outputs, documents and logs, not market data:

| Folder | Size | Contents |
|---|---|---|
| `lifecycle` | 2.0 GB | derived contract archive (SPY/QQQ/SPXW/IWM, 293 MB), run grids, `eod_by_exp` (above) |
| `evidence` | 219 M | provider docs, UW OpenAPI catalog (`provider_docs/uw_paths_catalog.txt`) |
| `archive_ignored_2026-10-16` | 264 M | pickled/npz grids |
| `audit_validation` | 151 M | — |
| `hwr_grid*` | 155 M | SPXW trade grids |
| `uw_probe` | 103 M | one 105 MB tape fragment `part.bin` and small probes |
| `pdfs`, `papers`, `dl`, `l*_dl`, `pdf`, `earnings_pdfs`, `exec_pdfs` | ≈ 190 M | papers |
| `rea-src` | 57 M | — |
| `inventory` | 42 M | flat-file samples |
| `browser` | 32 M | — |
| `universe` | 18 M | — |
| `cboe*` | 7 M | — |
| `numerix`, `sqm`, `tl`, `spx`, `eod`, small scripts and logs | < 10 M each | — |

### 1e. Per ticker: what is on disk at 1 minute versus end of day

| Ticker | 0DTE 1-min chains | 1–7 DTE 1-min | 8–60 DTE 1-min | All-expiry EOD (closing NBBO) | Daily OI | Underlying 1-min | UW history on disk |
|---|---|---|---|---|---|---|---|
| SPY | 2022-11-11 → 2026-10-21, complete | sample 468 | none | 2012-06 → 2026-10-05, + 10-06…12 | weeklies 2017-06 → 2023-06 | 2017 → 2026-10-21 | GEX levels 2023-11 →, minute series 61 d, NPT/IV/bars 2025-05/06 → 2026-10-09 |
| QQQ | 2022-11-11 → 2026-10-21, complete | sample 294 | none | 2012-06 → 2026-10-05 | none | 2017 → 2026-10-21 | GEX levels 2025-05 →, NPT/IV/bars 2025-05/06 → |
| SPXW / SPX | 2022-05-13 → 2026-10-21, complete | none | none | flat 5 days | none | SPX index 2017-06 → 2026-10-21 | GEX levels 2023-11 → |
| IWM | 2024-04-19 → 2026-10-09 | sample 294 | none | 2012-06 → 2026-10-05 | none | 2017 → 2026-10-09 | as QQQ |
| XSP, NDXP, RUTW | none | none | none | flat 5 days | none | XSP uses SPX; **NDX refused before 2026-05-08**; RUT none | none |
| DIA | none (Fridays only) | none | none | flat 5 days | none | 2017-06 → 2025-06-30 | none |
| AAPL, AMZN, AVGO, GOOGL, MSFT, NVDA, TSLA, AMD, INTC, MU, META | expiry days 2017-06 (META 2021-07) → 2026-10-09 | none | none | AAPL 2015-03 → 2025-09; others only earnings windows and flat 5 days | none | 2017-06 → 2026-10-09 | UW dated chains, sparse; recorder 2026-10-21 |
| MSTR, NFLX, SMCI | none | none | none | earnings windows, flat 5 days | none | 2017-06 → 2026-10-09 | sparse dated chains |
| PLTR | none | none | none | as above | none | 2017-06 → 2025-02-28 | sparse; recorder 1 day |
| SPCX, SOFI, ORCL, GME, IREN, CRWV, HOOD, NBIS, ASTS, MRVL, MARA, WULF, SNDK, SKHY, WMT | none | none | none | earnings windows (where present), flat 5 days | none | **none** | sparse dated chains; recorder 1 day for SOFI, ORCL, GME |

Two caveats on this table:
- **Single-stock "0DTE" exists only on expiry days**: Fridays, plus Monday and Wednesday for the megacaps since 2026 (123–125 expirations a year).
- **Expiries listed per session, mean over the base span**:

| Group | 1–7 DTE | 8–30 DTE | 31–60 DTE |
|---|---|---|---|
| SPY/QQQ/SPXW/XSP | 4.8 | 15.8 | 20 |
| Single stocks | 1.0–1.4 | 3.4–4.7 | 4.4–5.9 |
| DIA | 1.1 | 3.5 | 4.6 |

---

## 2. Unusual Whales routes: served span and point-in-time status

**Lookback floor**: call 01 asked `greek-exposure?date=2000-01-03` and got 403 `historic_data_access_missing`: "The earliest date currently available to this token is **2023-11-21** … API Basic and API Advanced subscriptions include up to 2 years of historical data". The floor moves forward one trading day per trading day. On 2026-10-15 it was 2023-11-15 (3abida `docs/data-feed.md`, "The series job").

**Header**: every answer carried `x-uw-req-per-minute-remaining: 1000000`. The 160k-a-day figure is the recorder README's, not checked here.

**What "point-in-time" means below**:
- **PIT**: the row is stamped at its own minute or event, and a past date returns those rows.
- **End state**: a past date returns that session's final (after-close) values only. There is no earlier minute.

Calls ran 2026-10-22 03:44–03:46 UTC (container clock), one at a time.

| # | Route and parameters asked | HTTP | Served span (evidence) | Rows per answer, time stamp | Point-in-time? |
|---|---|---|---|---|---|
| 01 | `GET /api/stock/SPY/greek-exposure?date=2000-01-03` | 403 | Window floor 2023-11-21. The ticker series itself returns 2025-10-15 → regardless of `date` (repo `DATA_PROVIDER_AUDIT.md` §6 @7dfea57; the lake). | daily rows | End state, daily |
| 02 | `/stock/SPY/greek-exposure/strike?date=2023-11-21` | 200 | **From the floor** (268 strikes) | `date` only, no time | **End state** of D ("follows the day and ends at its close": 3abida data-feed.md "The point-in-time store") |
| 03 | `/stock/SPY/greek-exposure/expiry?date=2023-11-21` | 200 | From the floor (31 expiries) | `date` only | End state |
| 04 | `/stock/SPY/greek-exposure/strike-expiry?date=2023-11-21&expiry=2023-12-15` | 200 | From the floor (247 rows; `expiry` required) | `date` only | End state |
| 05 | `/stock/SPY/spot-exposures?date=2023-12-08` (per-minute GEX/vanna/charm, `_oi`/`_vol`/`_dir`) | 200 | **2023-12-08 →**: 506 rows, 08:00–21:00Z. Empty from the floor to 2023-12-07 for SPY/QQQ/SPX/IWM (3abida). `_dir` is 0 until about mid-2024. | one row a minute, `time` and `start_time` | PIT rows, a minute each. Whether UW revises them later was not tested here (no live-recorded series on this machine). |
| 06 | `/stock/SPY/spot-exposures/strike?date=2023-11-21&limit=500` | 200 | **Empty at the floor** (0 rows). Served "back to at least 2024-09-04" (3abida, 2026-10-13). Start not pinned. | — | — |
| 25 | the same route, `date=2026-10-21` (comparison) | 200 | 491 strikes | every row `time` 20:15Z (16:15 ET) | **End state only.** Equal to the recorder's smoke capture of 2026-10-21 20:36Z field for field (0 of 16,694 differ), so it is not recomputed a day later. A past minute's book by strike **cannot be asked**. |
| 07 | `/stock/SPY/spot-exposures/expiry-strike?date=2025-01-16&limit=50` | 200 | **2025-01-16 →** (UW's own doc: "Data is available since 2025-01-16"; this call returned rows that day) | one `time`, 20:28:30Z | End state |
| 08 | `/stock/QQQ/gex-levels?date=2024-05-13` | 200 | QQQ served 2024-05-13 (disk had QQQ only from 2025-05-22). SPY/SPX on disk: dates from 2023-11-13 but **null until 2024-05-13**. | one row a date, `time` 17:29–21:55Z (disk, 766 SPY dates) | **End state**, `source: vol` (directionalized volume, not OI). UW's walls/flip as of an intraday minute are not served. |
| 09 | `/option-trades/flow-alerts?ticker_symbol=SPY&newer_than=2023-11-21T14:30Z&older_than=…21:00Z&limit=50` | 200 | **From the floor** (50 rows, `created_at` 18:58–20:59Z, paged by `older_than`) | `created_at`, `start_time`, `has_sweep`, `has_floor`… | PIT (each alert stamped at creation) |
| 10 | `/option-trades?ticker_symbol=SPY&…2026-10-20` | 400 | **Latest trading day only** (`historical_data_not_supported`) | — | — |
| 11 | `/option-trades/full-tape/2023-11-21` | 403 | "**During an API trial, Full Tape is limited to the past 30 calendar days.**" | — | (prints would be PIT) |
| 12 | `/stock/SPY/flow-per-strike-intraday?date=2023-11-21` | 200 | **Empty at the floor.** On disk 2025-07-07 → (42 dates). Top 8 strikes only (3abida samples). Start not pinned. | 1-min | PIT minutes |
| 13 | `/stock/SPY/net-prem-ticks?date=2023-11-21` | 200 | **From the floor** (405 rows) | `tape_time` a minute | PIT |
| 26 | the same route, `date=2026-10-21` (comparison) | 200 | 510 rows | | Equal to the recorder's capture of 2026-10-21 21:24Z (0 of 5,610 fields differ) |
| 14 | `/stock/SPY/nope?date=2023-11-21` | 200 | **Empty at the floor** | — | — |
| 28 | the same route, `date=2026-10-21` | 200 | Served (390 rows, 13:30–19:59Z). **Start not pinned.** | `timestamp` a minute | PIT minutes (assumed; not compared) |
| 15 | `/market/market-tide?date=2023-11-21` | 200 | **From the floor** (81 rows, 5-min, 09:30–16:10 ET) | `timestamp` | PIT |
| 16 | `/darkpool/SPY?date=2023-11-21&limit=50` | 200 | **From the floor** (newest first; paged by `older_than`) | `executed_at` a print | PIT (prints). No index (SPX has none). |
| 17 | `/stock/SPY/options-pulse?date=2023-11-21` | 200 | **Empty at the floor** (`latest: null, intraday: []`) | — | — |
| 27 | the same route, `date=2026-10-21` | 200 | Served: intraday series in 10-min `hr_min` buckets with running `sntm_score`. **Start not pinned.** | `hr_min` | PIT buckets (assumed) |
| 18 | `/stock/SPY/option-contracts?date=2023-11-21&expiry=2023-12-15&limit=500` | 200 | **From the floor** (494 contracts with OI, prev OI, IV, greeks, closing NBBO, side/sweep volume). `date` is undocumented but honoured. | `last_tape_time` only | **End state** of D: vols at D's close; OI is the count published the morning of D, i.e. positions at D−1's close (3abida data-feed.md) |
| 19 | `/option-contract/SPY250417C00560000/intraday?date=2025-04-01` | 200 | **2025-04-01 →** (341 rows; empty ≤ 2025-03-03, `DATA_PROVIDER_AUDIT.md` §6) | `start_time` a minute | PIT minutes |
| 20 | `/stock/SPY/oi-per-strike?date=2023-11-21` | 200 | **Empty at the floor.** Recorded live 2026-10-21. Start not pinned. | `date` = publication day | Daily (count at D−1's close) |
| 21 | `/stock/SPY/interpolated-iv?date=2023-11-21` | 200 | **From the floor** (9 tenors) | `date` | End state, daily |
| 22 | `/stock/SPY/ohlc/1m?date=2022-09-28&limit=5` | 200 | Served **before** the window: stock bars are not held to it (2022-09-28 → per DATA_PROVIDER_AUDIT) | `start_time` | PIT. Indices 422. |
| 23 | `/earnings/afterhours?date=2023-11-21` | 200 | From the floor (13 reports); the lake holds 1996 → | event | Calendar |
| 24 | `/market/economic-calendar` (no parameters) | 200 | **Current week only** (18 rows, 2026-10-19 → 23). No history; the macro JSON covers 2022–2027. | — | — |
| — | `/stock/{t}/flow-recent` | not called | No date parameter: **current only** | — | — |

**What "Pulse" maps to.**
- UW has one Pulse family, the **Nasdaq Options Pulse** sentiment: `/api/stock/{t}/options-pulse`, `/api/options-pulse/total`, `/api/options-pulse/sectors`, `/api/options-pulse/top`.
- It serves recent dates, but answered empty at the floor.
- The terminal's own "Pulse" (3abida) is the house desk of panels, not a UW route.

Call count: 28 calls, all under the ~30 budget. Routes 06/25, 13/26, 14/28 and 17/27 got two calls each:
- 25 and 26 are the same-minute comparisons with the recorder that the brief asked for.
- 27 and 28 checked whether NOPE and Pulse are served at all after both answered empty at the floor.

---

## 3. Missing data: requests, size, time

### How the figures were measured

**ThetaData, through the `thetadata` SDK (gRPC) from this container**: one login per run, which signs the owner's PC terminal out (authorized). Times are measured from the forward fetch: `research_notes/Compass phase 3/forward_2026-10-12_2026-10-21/sdk_fetch.py`, `data/theta_forward/_manifest/*.json`. That fetch ran one request in flight: 56 files in 3 min 25 s.

| SDK request | Median s / request (max) | Median MB / file |
|---|---|---|
| `option_history_quote` 1-min, one expiry and one day: SPY | 5.0 (7.4) | 0.67 |
| … QQQ | 5.7 (11.2) | 0.66 |
| … SPXW | 9.95 (18.9) | 0.91 |
| `stock_history_ohlc` 1-min, a day | 1.0 (2.2) | 0.012 |
| `index_history_price` 1-min, a day | 0.1 | 0.003 |

Assumptions for requests not measured on the SDK path:
- **0DTE chains of other roots**: 10 s per MB of the root's measured file size (single names from the stored files: 0.14–0.60 MB, median 0.245 MB; IWM 0.33 MB). XSP is taken as SPY, NDXP as SPXW, RUTW as QQQ.
- **All-expiry EOD**: one week a request, about 15 s at 1 in flight. Derived from the Tier D pull of 2026-10-15 (750 QQQ weeks in 54 min at 4 workers, 17 s a request a worker; single names about 14 s). MB a week is measured: SPY 0.51, QQQ 0.33, IWM 0.23, AAPL 0.15. Others are assumed.
- **Open interest**: about 10 s a request (the vendor throttles this route to about 0.1 a second; measured in the S03 pull, `01_data_inventory.md` @7dfea57). Size from the flat OI file: 5.2 B a contract.
- **`at_time/quote` for one minute**: unmeasured. The vendor's p99 is 12.2 s (`x-concurrent-limit-ttl-ms` in the v3 spec on disk).
- **The "@4" column** divides by four and assumes the SDK scales across four workers as the Tier D pull did. The account allows 8.

**UW**: one call in flight, at least 2.2 s apart, counted as **2.5 s a call** (answers took 0.16–0.52 s). Bytes are the measured JSON answer sizes. Per-strike routes for other names are scaled by their strike count. Paging is from the recorder's 2026-10-21 row counts per name (flow alerts 200 a page, dark pool 500, chain 500); names it does not record use their tier's median. All runs are over the UW span minus what §1b holds.

### 3a. Needed for the base trades (ThetaData)

| Dataset | What is missing | Requests | Size | Hours @1 (SDK) | Hours @4 |
|---|---|---|---|---|---|
| **0DTE 1-min full chains**, index/ETF | IWM 233 days (2022-11-11 → 2024-04-18 expiry days, plus 2026-10-12 → 21); XSP 988; NDXP 959; RUTW 861; DIA 215 (Fridays) | 3,256 | 2.2 GB | 5.7 | 1.4 |
| **0DTE 1-min full chains**, 30 single stocks (expiry days only) | 11 stored names: 4–7 days each (2026-10-12 → 21). 19 others: every expiry day in the span (14–208 each) | 3,156 | 0.8 GB | 2.2 | 0.5 |
| ↳ optional ETF add-on (10) | every expiry day (174–483 each) | 2,961 | 0.7 GB | 2.0 | 0.5 |
| **Underlying 1-min bars**, one day a request | RUT 988 (index); IWM 8; DIA 330. NDX: not obtainable (B6). | 1,326 | 7 MB | 0.1 | — |
| | singles: 8 days for 13 names; PLTR 413; 15 names the whole span (988 each) | 15,345 | 0.18 GB | 4.3 | 1.1 |
| | ETF add-on | 3,425 | 0.04 GB | 1.0 | 0.2 |
| **1–60 DTE at a fixed minute, option A: all-expiry EOD** (closing NBBO, a week a request; measured route) | SPY/QQQ/IWM 2026-10-13 → 21 (2 weeks each); SPXW, XSP, NDXP, RUTW, DIA all 207 weeks | 1,041 | 0.43 GB | 4.3 | 1.1 |
| | 30 singles (AAPL 59 weeks, others 207) | 6,062 | 1.2 GB | 25.3 | 6.3 |
| | ETF add-on | 2,070 | 0.41 GB | 8.6 | 2.2 |
| **1–60 DTE at a fixed minute, option B: `option/at_time/quote`** (`expiration=*`, `max_dte=60`, `strike_range`, `time_of_day` e.g. 10:00, a month a request — unmeasured; multi-day with `*` untested) | 8 index roots × 48 months | 384 | ≈ 0.1 GB | ≈ 1.3 (p99) | ≈ 0.3 |
| | 30 singles × 48 months | 1,440 | ≈ 0.4 GB | ≈ 4.8 (p99) | ≈ 1.2 |

**Which 1–60 DTE route is cheaper.**
- A single-minute snapshot through `at_time/quote` is about 4–5× fewer requests than the weekly EOD. It is also the decision minute itself, where EOD gives the close.
- But it is unmeasured. One test request should settle it before choosing.
- EOD is the measured fallback: about 4 h @1 for the index roots and 25 h for 30 singles.
- Either is far cheaper than 1-min chains for 1–60 DTE (§3c).
- UW's dated chain is an EOD-only alternative from 2023-11-21: about 70 k calls for the index roots.

### 3b. Needed for the features

**ThetaData**

| Dataset | What is missing | Requests | Size | Hours @1 | Hours @4 |
|---|---|---|---|---|---|
| **Daily open interest**, `expiration=*`, a root-day a request, throttled (~10 s) | index roots 8 × 988 | 7,904 | 0.4 GB | 22 | 5.5 (if the throttle allows) |
| | 30 singles × 988 | 29,640 | 0.45 GB | 82 | 21 |
| | ETF add-on | 9,880 | 0.15 GB | 27 | 7 |
| IV and greeks | solved from the NBBO mid with the parity-implied rate (the engine's method); no fetch | 0 | — | — | — |

**UW, the core feature set** (731 sessions, or the route's own start, minus disk)

| Route | Start | Index/ETF 8: calls | GB | Singles 30: calls | GB | ETF add-on: calls | GB |
|---|---|---|---|---|---|---|---|
| `spot-exposures` (per-minute whole-book GEX) | 2023-12-08 | 5,691 | 1.5 | 21,570 | 5.7 | 7,190 | 1.9 |
| `greek-exposure/strike` (EOD book) | 2023-11-21 | 5,848 | 0.3 | 21,930 | 0.5 | 7,310 | 0.1 |
| `spot-exposures/strike` (EOD book) | ≥ 2024-09-04 (unpinned) | 4,280 | 1.6 | 16,050 | 2.7 | 5,350 | 0.7 |
| `gex-levels` (UW's walls/flip, EOD) | 2023-11-21 (non-null 2024-05-13) | 3,706 | 0 | 21,930 | 0 | 7,310 | 0 |
| `flow-alerts` (sweeps, floor, multileg flags; ≥ $25K) | 2023-11-21 | 45,322 | 8.3 | 41,667 | 7.6 | 7,310 | 1.3 |
| `net-prem-ticks` | 2023-11-21 | 4,822 | 0.9 | 21,930 | 4.0 | 7,310 | 1.3 |
| `nope` | unpinned (≤ 731 days) | 5,848 | 0.6 | 21,930 | 2.3 | 7,310 | 0.8 |
| `darkpool`, filtered to large prints (`min_premium` ≈ $1M: ~1 page a day, assumed) | 2023-11-21 | ≈ 2,900 | ≈ 0.6 | 21,930 | ≈ 1.1 | 7,310 | ≈ 0.4 |
| `options-pulse` ("Pulse") | unpinned | 5,848 | 0.03 | 21,930 | 0.1 | 7,310 | 0.04 |
| `interpolated-iv` | 2023-11-21 | 4,804 | 0 | 21,930 | 0 | 7,310 | 0 |
| `market-tide` + `options-pulse/total` (market-wide) | 2023-11-21 | 1,120 total | 0.01 | — | — | — | — |
| **Total core** | | **≈ 89 k** (≈ 62 h) | ≈ 14 | **≈ 233 k** (≈ 162 h) | ≈ 24 | ≈ 71 k (≈ 49 h) | ≈ 7 |

**Totals**
- Core without the ETF add-on: **≈ 323 k calls ≈ 224 h ≈ 9.3 days of continuous 1-in-flight fetching**, about 38 GB of raw JSON.
- If the fetch keeps clear of the owner's live recorder hours (≈ 16 h a day): about 14 days.
- At 2.5 s a call a day holds at most 34,560 calls, under the 160k daily figure; the per-minute header showed 1,000,000 remaining.

### 3c. Nice to have

| Dataset | Requests | Size | Time |
|---|---|---|---|
| Theta 1-min chains for every expiry ≤ 60 DTE, `strike_range=20` (intraday exits on multi-day holds): 7 index roots × 988 days | 6,916 | ≈ 48 GB | ≈ 134 h @1 / 34 h @4 |
| … 30 singles × 988 days | 29,640 | ≈ 59 GB | ≈ 165 h @1 / 41 h @4 |
| Theta vendor greeks EOD (`expiration=*`, day by day; p99 6.6 s) | 1 per root-day (≈ 37 k) | — | ≈ 70 h @1 |
| UW `spot-exposures/expiry-strike` (2025-01-16 →, ~10 pages a day for SPY) | ≈ 89 k | ≈ 37 GB | ≈ 61 h |
| UW `greek-exposure/expiry` | ≈ 35 k | 0.3 GB | ≈ 24 h |
| UW `flow-per-strike-intraday` (top 8 strikes) | ≈ 35 k | 5 GB | ≈ 24 h |
| UW full dark-pool tape (unfiltered; NVDA/META/MU ~27 pages a day) | ≈ 299 k | ≈ 63 GB | ≈ 208 h |
| UW dated chain (`option-contracts?date`, `max_dte=60`, paged) | ≈ 180 k | ≈ 53 GB | ≈ 125 h |
| UW contract minutes for the traded contracts only (2025-04-01 →, one call a contract-day; e.g. 8 contracts a session × 8 roots × ≈ 390 sessions) | ≈ 25 k | ≈ 3 GB | ≈ 17 h |
| UW full tape (prints; 0.7–1.9 GB a day) | 1 a day | ≈ 1 TB over the window | **not available on this token** (B1) |

**PC-terminal footnote** (no longer the plan): through the Theta Terminal on the owner's PC the same requests run at most 4 in flight (minute bars a month a call; the terminal's own recorder holds one slot). The "@4" column is the comparable figure there. The 3abida downloader (`npm run theta:history`) and the UW series job may already hold some of these rows in the PC's `.feed-cache/` (B12).

---

## 4. Blockers and what each blocks

| # | Blocker | What it blocks |
|---|---|---|
| B1 | **The UW token is an API trial**: full-tape answered "During an API trial, Full Tape is limited to the past 30 calendar days" (call 11). The owner's terminal token streamed archives from 2024-01-03 (3abida data-feed.md), so this research token is not that plan. | Per-print flow history (sweeps from prints, trade-level side, premium by contract-minute before 2025-04) beyond 30 days. `flow-alerts` (has_sweep, from 2023-11-21) and contract minutes (2025-04-01 →) are the partial substitutes. Whether trial limits apply elsewhere is unknown. |
| B2 | **No historical GEX by strike, walls or flip at a past minute** on UW: `spot-exposures/strike`, `greek-exposure/strike` and `gex-levels` for date D return D's end state only (calls 02, 07, 08, 25). The only intraday UW GEX history is the whole-book per-minute series (no strikes) from 2023-12-08. | "Walls and flip as UW published them" at a 0DTE entry minute. Using D's values at D's intraday entries is look-ahead; D−1's are usable. Per-strike GEX at the minute must be modelled (Theta OI × greeks, or the terminal's trail model). |
| B3 | Start dates not pinned: `nope`, `options-pulse`, `flow-per-strike-intraday`, `oi-per-strike` (empty at 2023-11-21, served recently), `spot-exposures/strike` (empty at the floor; ≥ 2024-09-04). | The span of the NOPE and Pulse features, and of their hold-out. About 3 calls a route by bisection (≈ 15 calls) would pin them. Not done: one call a route was the rule. |
| B4 | **UW's window rolls**: 730 trading days, floor 2023-11-21 today. | Each trading day before the fetch loses one session of UW history at the old end. |
| B5 | **gex-levels** is volume-sourced ("source: vol"), and SPY/SPX rows are null before 2024-05-13. | UW-published walls before 2024-05-13, and an OI-based UW wall. |
| B6 | **NDX index level refused on Theta before 2026-05-08** (add-on). | NDXP underlying price. NDXP base trades need the parity-implied level off its own chain (flagged) or must drop out. |
| B7 | **Theta OI is throttled** (~0.1 req/s). | Daily OI across the universe: 22–131 h at 1 in flight. UW's dated chain gives OI only from 2023-11-21. |
| B8 | Theta interest-rate history is not entitled before 2024. | Nothing if r is read off parity (the engine's method). |
| B9 | **The universe ranking is five sessions (2026-10-06 → 12)**, the only all-root files. 9 of the 30 single names listed options or turned liquid after 2022-11: SPCX (weekly only in 2026), CRWV 2025-04, NBIS 2024-11, SNDK 2025-03, SKHY 2026-07, IREN, WULF, ASTS, HOOD. | A point-in-time liquidity tiering and the 20%-of-tickers hold-out. A per-year ranking needs each candidate root's EOD volume (the EOD pull in §3a gives it for the candidates only). A ranking across all ~6,000 roots was not estimated. |
| B10 | **Single-stock 0DTE exists only on expiry days**: Fridays; Mon/Wed/Fri for the megacaps since 2026. | The "every 30 min" 0DTE base trades on singles: about 52–125 sessions a year a name, not daily. |
| B11 | Theta vendor greeks start between 2016 and 2017. | Nothing if IV and greeks are solved from the NBBO. |
| B12 | **The owner's PC holds data this machine cannot see**: 3abida `.feed-cache` (UW per-minute series back to 2023-12-08 for the recorder's names, live books, books60, chain reads) and any `theta:history` rows. | A copy could replace part of §3b, and is the only live-recorded intraday per-strike book there is. Its contents are unknown from here. |
| B13 | UW quota: only the per-minute header (1,000,000) was seen. The 160k a day is the recorder README's figure. The owner's recorder and terminal share the token, about 1.1–1.9 k calls a day plus the terminal's. | Schedule: at 1 in flight the core UW set is about 9–14 days of wall time. |

Nothing was fetched beyond the 28 UW probe calls. Nothing was committed.
