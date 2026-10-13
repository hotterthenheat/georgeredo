# Provider re-audit — live calls on 2026-10-13

Scope: re-test, with live requests made today, the Unusual Whales (UW) and Massive/Polygon entitlements and historical depth that a full reconstruction of the GeorgeFi trade ledger (`evidence/public_api/trades_all.json.gz`, 489 trades, 2026-03-02 14:35Z → 2026-10-08 19:25Z; the three `trades_book_*.json.gz` books extend to 2026-10-13) needs, and compare with the committed `DATA_PROVIDER_AUDIT.md`.

Method. 101 UW calls (`https://api.unusualwhales.com/api/`, Bearer header) and 8 Massive calls (`https://api.massive.com`, `apiKey` query, 13 s apart, no fallback to `api.polygon.io` was needed). Credentials were read from the environment by the script and never written anywhere; every saved payload and this report were regex-scanned for the token/key. One sanitized JSON per call (path without credentials, params, status, elapsed ms, row count, first/last and min/max timestamp, first 300 chars of body or the parsed error object, selected response headers) is in `provider_checks/`, with the combined list in `provider_checks/_summary.json`. Only observed status codes and payload facts are reported; nothing below comes from memory.

Operational facts observed today: UW returned **429 `concurrent_limit_exceeded` ("You have exceeded 3 concurrent requests, the maximum allowed for your current plan", `current_limit: 3`)** on the very first 4-wide burst while every response still carried `x-uw-req-per-minute-remaining: 1000000`; all later batches ran at ≤ 3 in flight without a single 429. Massive produced no 429 at one request per 13 s.

Contract-id convention verified: UW ids are the ledger's `optionSymbol` without the `O:` prefix (`{root}{yymmdd}{C|P}{strike*1000:08d}`), exactly as `backtest/data.py::contract_id` builds them. The ledger's roots are SPY, QQQ, IWM, single names, and for indices **SPXW** (142 of 145 ^SPX trades), **NDXP** (all ^NDX) and **RUTW** (all ^RUT); three ^SPX trades use the AM-settled root **SPX** (`O:SPX260320P06585000`, `O:SPX260417C07055000` twice).

## 1. Every call

| # | provider | endpoint | params | status | rows | min ts | max ts | note |
|---|---|---|---|---|---|---|---|---|
| 1 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2021-06-01, limit=2500 | **200** | 0 |  |  | 200, empty |
| 2 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2021-11-01, limit=2500 | **200** | 0 |  |  | 200, empty |
| 3 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2022-01-03, limit=2500 | **200** | 0 |  |  | 200, empty |
| 4 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2022-06-01, limit=2500 | **200** | 0 |  |  | 200 with empty data: OHLC 1m floor lies between 2022-06-01 and 2022-09-28 |
| 5 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2022-09-28, limit=2500 | **200** | 814 | 2022-09-28T08:00:00Z | 2022-09-28T23:59:00Z | OK, 390 RTH rows |
| 6 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2023-06-01, limit=2500 | **200** | 678 | 2023-06-01T08:02:00Z | 2023-06-01T23:59:00Z | OK, before the 2023-11-13 plan floor: stock OHLC is not gated |
| 7 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2024-06-03, limit=2500 | **200** | 660 | 2024-06-03T08:00:00Z | 2024-06-03T23:59:00Z | OK (beyond Massive window) |
| 8 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2025-01-02, limit=2500 | **200** | 655 | 2025-01-02T09:00:00Z | 2025-01-03T00:59:00Z | OK |
| 9 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2025-06-02, limit=2500 | **200** | 721 | 2025-06-02T08:00:00Z | 2025-06-02T23:59:00Z | first attempt 429 concurrent_limit_exceeded (current_limit 3); retried at <=3 parallel |
| 10 | unusualwhales | `/api/stock/SPY/ohlc/1m` | date=2026-03-02, limit=2500 | **200** | 855 | 2026-03-02T09:00:00Z | 2026-03-03T00:59:00Z | ledger start day; 390 RTH rows + pre/post |
| 11 | unusualwhales | `/api/option-contract/SPY240603C00528000/historic` | limit=10 | **200** | 10 | 2024-05-20 | 2024-06-03 | daily rows exist (OHLC, volume, OI, NBBO, IV) -> contract known, intraday missing |
| 12 | unusualwhales | `/api/option-contract/SPY241014C00580000/historic` | limit=10 | **200** | 10 | 2024-10-01 | 2024-10-14 | daily rows exist |
| 13 | unusualwhales | `/api/option-contract/SPY250303C00585000/historic` | limit=3 | **200** | 3 | 2025-02-27 | 2025-03-03 |  |
| 14 | unusualwhales | `/api/option-contract/SPY250303C00590000/historic` | limit=3 | **200** | 3 | 2025-02-27 | 2025-03-03 |  |
| 15 | unusualwhales | `/api/option-contract/SPY250401C00560000/historic` | limit=3 | **200** | 3 | 2025-03-28 | 2025-04-01 |  |
| 16 | unusualwhales | `/api/option-contract/SPY250401C00565000/historic` | limit=3 | **200** | 3 | 2025-03-28 | 2025-04-01 |  |
| 17 | unusualwhales | `/api/option-contract/SPY250501C00565000/historic` | limit=3 | **200** | 3 | 2025-04-29 | 2025-05-01 |  |
| 18 | unusualwhales | `/api/option-contract/SPY250501C00570000/historic` | limit=3 | **200** | 3 | 2025-04-29 | 2025-05-01 |  |
| 19 | unusualwhales | `/api/option-contract/SPY250515C00588000/historic` | limit=3 | **200** | 3 | 2025-05-13 | 2025-05-15 |  |
| 20 | unusualwhales | `/api/option-contract/SPY250515C00590000/historic` | limit=3 | **200** | 3 | 2025-05-13 | 2025-05-15 |  |
| 21 | unusualwhales | `/api/option-contract/SPY250602C00590000/historic` | limit=10 | **200** | 10 | 2025-05-19 | 2025-06-02 | daily rows exist |
| 22 | unusualwhales | `/api/option-contract/IWM260302C00259000/intraday` | date=2026-03-02 | **200** | 130 | 2026-03-02T14:30:00Z | 2026-03-02T21:01:00Z | EARLIEST ledger trade (IWM 259C, entry 14:35Z); iv_high/iv_low + side premium present |
| 23 | unusualwhales | `/api/option-contract/META260819C00545000/intraday` | date=2026-08-19 | **200** | 232 | 2026-08-19T13:30:00Z | 2026-08-19T19:59:00Z | single-name example |
| 24 | unusualwhales | `/api/option-contract/NDX260515P29130000/intraday` | date=2026-05-15 | **422** |  |  |  | 422 does not exist (root NDX) |
| 25 | unusualwhales | `/api/option-contract/NDXP260515P29130000/intraday` | date=2026-05-15 | **200** | 116 | 2026-05-15T13:30:00Z | 2026-05-15T19:59:00Z | first ^NDX trade; root NDXP works |
| 26 | unusualwhales | `/api/option-contract/QQQ260303P00595000/intraday` | date=2026-03-03 | **200** | 398 | 2026-03-03T14:30:00Z | 2026-03-03T21:14:00Z | first QQQ trade |
| 27 | unusualwhales | `/api/option-contract/RUT261008C02785000/intraday` | date=2026-10-08 | **422** |  |  |  | 422 does not exist (root RUT) |
| 28 | unusualwhales | `/api/option-contract/RUTW261008C02785000/intraday` | date=2026-10-08 | **200** | 204 | 2026-10-08T13:30:00Z | 2026-10-08T19:59:00Z | LATEST ledger trade (^RUT 2785C, entry 19:25Z); root RUTW works |
| 29 | unusualwhales | `/api/option-contract/SPX260304C06815000/intraday` | date=2026-03-04 | **422** |  |  |  | 422 "SPX260304C06815000 does not exist": root SPX rejected for a weekly |
| 30 | unusualwhales | `/api/option-contract/SPX260320P06585000/intraday` | date=2026-03-20 | **200** | 0 |  |  | ledger O:SPX260320P06585000 (3rd-Friday, AM-settled root): 200 but EMPTY |
| 31 | unusualwhales | `/api/option-contract/SPXW260304C06815000/intraday` | date=2026-03-04 | **200** | 164 | 2026-03-04T14:30:00Z | 2026-03-04T20:59:00Z | first ^SPX trade; root SPXW works |
| 32 | unusualwhales | `/api/option-contract/SPXW260320P06585000/intraday` | date=2026-03-20 | **200** | 280 | 2026-03-20T13:30:00Z | 2026-03-20T19:57:00Z | PM-settled twin of the same strike/expiry: 280 bars |
| 33 | unusualwhales | `/api/option-contract/SPY230601C00418000/intraday` | date=2023-06-01 | **403** |  |  |  | 403 same |
| 34 | unusualwhales | `/api/option-contract/SPY230601C00420000/intraday` | date=2023-06-01 | **403** |  |  |  | 403 historic_data_access_missing: "earliest date currently available to this token is 2023-11-13 (730 trading days)" |
| 35 | unusualwhales | `/api/option-contract/SPY230601C00422000/intraday` | date=2023-06-01 | **403** |  |  |  | 403 same |
| 36 | unusualwhales | `/api/option-contract/SPY231113C00440000/intraday` | date=2023-11-13 | **200** | 0 |  |  | 200 EMPTY (plan floor date) |
| 37 | unusualwhales | `/api/option-contract/SPY231113C00445000/intraday` | date=2023-11-13 | **200** | 0 |  |  | 200 EMPTY |
| 38 | unusualwhales | `/api/option-contract/SPY240603C00525000/intraday` | date=2024-06-03 | **200** | 0 |  |  | 200 EMPTY |
| 39 | unusualwhales | `/api/option-contract/SPY240603C00528000/intraday` | date=2024-06-03 | **200** | 0 |  |  | 200 EMPTY (historic: volume 349,971, underlying_close 527.80) |
| 40 | unusualwhales | `/api/option-contract/SPY240603C00530000/intraday` | date=2024-06-03 | **200** | 0 |  |  | 200 EMPTY |
| 41 | unusualwhales | `/api/option-contract/SPY240801C00545000/intraday` | date=2024-08-01 | **200** | 0 |  |  | 200 EMPTY |
| 42 | unusualwhales | `/api/option-contract/SPY240801C00550000/intraday` | date=2024-08-01 | **200** | 0 |  |  | 200 EMPTY |
| 43 | unusualwhales | `/api/option-contract/SPY241014C00580000/intraday` | date=2024-10-14 | **200** | 0 |  |  | 200 EMPTY (historic: contract traded) |
| 44 | unusualwhales | `/api/option-contract/SPY241014C00585000/intraday` | date=2024-10-14 | **200** | 0 |  |  | 200 EMPTY |
| 45 | unusualwhales | `/api/option-contract/SPY250102C00585000/intraday` | date=2025-01-02 | **200** | 0 |  |  | 200 EMPTY |
| 46 | unusualwhales | `/api/option-contract/SPY250102C00590000/intraday` | date=2025-01-02 | **200** | 0 |  |  | 200 EMPTY |
| 47 | unusualwhales | `/api/option-contract/SPY250303C00585000/intraday` | date=2025-03-03 | **200** | 0 |  |  | 200 EMPTY although historic shows the contract traded that day |
| 48 | unusualwhales | `/api/option-contract/SPY250303C00590000/intraday` | date=2025-03-03 | **200** | 0 |  |  | 200 EMPTY (historic: volume 184,321 on 2025-03-03) |
| 49 | unusualwhales | `/api/option-contract/SPY250401C00560000/intraday` | date=2025-04-01 | **200** | 405 | 2025-04-01T13:30:00Z | 2025-04-01T20:14:00Z | OK: earliest date with contract bars found |
| 50 | unusualwhales | `/api/option-contract/SPY250401C00565000/intraday` | date=2025-04-01 | **200** | 367 | 2025-04-01T13:30:00Z | 2025-04-01T20:06:00Z | OK |
| 51 | unusualwhales | `/api/option-contract/SPY250501C00565000/intraday` | date=2025-05-01 | **200** | 401 | 2025-05-01T13:30:00Z | 2025-05-01T20:13:00Z | OK |
| 52 | unusualwhales | `/api/option-contract/SPY250501C00570000/intraday` | date=2025-05-01 | **200** | 385 | 2025-05-01T13:30:00Z | 2025-05-01T20:14:00Z | OK |
| 53 | unusualwhales | `/api/option-contract/SPY250515C00588000/intraday` | date=2025-05-15 | **200** | 404 | 2025-05-15T13:30:00Z | 2025-05-15T20:14:00Z | OK |
| 54 | unusualwhales | `/api/option-contract/SPY250515C00590000/intraday` | date=2025-05-15 | **200** | 405 | 2025-05-15T13:30:00Z | 2025-05-15T20:14:00Z | OK |
| 55 | unusualwhales | `/api/option-contract/SPY250602C00590000/intraday` | date=2025-06-02 | **200** | 405 | 2025-06-02T13:30:00Z | 2025-06-02T20:14:00Z | OK: 405 bars |
| 56 | unusualwhales | `/api/option-contract/SPY260302C00682000/intraday` | date=2026-03-02 | **200** | 356 | 2026-03-02T14:30:00Z | 2026-03-02T21:05:00Z | first SPY trade; 356 bars, vol 93,817 (Massive same contract: 354 bars, vol 87,626) |
| 57 | unusualwhales | `/api/stock/NDX/ohlc/1m` | date=2026-10-09, limit=5 | **422** |  |  |  | 422 cboe_index_access_missing |
| 58 | unusualwhales | `/api/stock/RUT/ohlc/1m` | date=2026-10-09, limit=5 | **422** |  |  |  | 422 cboe_index_access_missing |
| 59 | unusualwhales | `/api/stock/SPXW/ohlc/1m` | date=2026-10-09, limit=5 | **422** |  |  |  | 422 cboe_index_access_missing |
| 60 | unusualwhales | `/api/stock/SPX/ohlc/1m` | date=2026-10-09, limit=5 | **422** |  |  |  | 422 cboe_index_access_missing |
| 61 | unusualwhales | `/api/stock/SPX/gex-levels` | date=2026-10-09 | **200** | 1 | 2026-10-09T20:00:00Z | 2026-10-09T20:00:00Z | INDEX WORKS: flip 7795.46 / 7815 / 7805 / 7810 |
| 62 | unusualwhales | `/api/stock/SPY/gex-levels` | date=2024-06-03 | **200** | 1 | 2024-06-03T20:14:58Z | 2024-06-03T20:14:58Z | OK (2+ years back) |
| 63 | unusualwhales | `/api/stock/SPY/gex-levels` | date=2025-06-02 | **200** | 1 | 2025-06-02T20:14:58Z | 2025-06-02T20:14:58Z | flip 592.5 / 594 / 588 / 593 |
| 64 | unusualwhales | `/api/stock/SPY/gex-levels` | date=2026-03-02 | **200** | 1 | 2026-03-02T21:00:00Z | 2026-03-02T21:00:00Z | flip 686.8 / call wall 688 / put wall 686 / magnet 686, source vol |
| 65 | unusualwhales | `/api/stock/SPX/spot-exposures` | date=2026-10-09 | **200** | 521 | 2026-10-09T10:36:00Z | 2026-10-09T20:00:00Z | INDEX WORKS; rows carry price (7795 at 10:36Z) although index OHLC is blocked |
| 66 | unusualwhales | `/api/stock/SPY/spot-exposures` | date=2024-06-03 | **200** | 545 | 2024-06-03T10:30:00Z | 2024-06-03T20:00:00Z | OK: no 90-day limit |
| 67 | unusualwhales | `/api/stock/SPY/spot-exposures` | date=2025-06-02 | **200** | 493 | 2025-06-02T10:30:00Z | 2025-06-02T19:59:00Z | OK: no 90-day limit |
| 68 | unusualwhales | `/api/stock/SPY/spot-exposures` | date=2026-03-02 | **200** | 549 | 2026-03-02T11:30:00Z | 2026-03-02T21:00:00Z | 1-min gamma/vanna/charm per 1% (oi/vol/dir) + price |
| 69 | unusualwhales | `/api/stock/SPY/spot-exposures` | date=2026-10-09 | **200** | 527 | 2026-10-09T10:35:00Z | 2026-10-09T20:00:00Z | control |
| 70 | unusualwhales | `/api/darkpool/SPY` | date=2026-03-02, limit=500 | **200** | 500 | 2026-03-02T20:59:42Z | 2026-03-02T23:57:31Z | limit=500 hit; newest-first; NBBO fields present |
| 71 | unusualwhales | `/api/option-trades/flow-alerts` | ticker_symbol=SPY, limit=5 | **200** | 5 | 2026-10-13T18:56:00Z (ms) | 2026-10-13T18:56:07Z (ms) | latest alerts (2026-10-13) |
| 72 | unusualwhales | `/api/option-trades/flow-alerts` | ticker_symbol=SPY, limit=5, date=2026-03-02 | **200** | 5 | 2026-10-13T18:56:00Z (ms) | 2026-10-13T18:56:07Z (ms) | `date` IGNORED: returned 2026-10-13 alerts |
| 73 | unusualwhales | `/api/option-trades/flow-alerts` | ticker_symbol=SPY, limit=5, newer_than=2026-03-02T00:00:00Z, older_than=2026-03-03T00:00:00Z | **200** | 5 | 2026-03-02T21:11:57Z (ms) | 2026-03-02T21:14:51Z (ms) | `newer_than`/`older_than` honoured: 2026-03-02 alerts returned |
| 74 | unusualwhales | `/api/stock/SPX/flow-per-strike-intraday` | date=2026-10-09 | **200** | 1121 | 2026-10-09T13:30:02.126000Z | 2026-10-09T20:53:16.740000Z | INDEX WORKS |
| 75 | unusualwhales | `/api/stock/SPY/flow-per-strike-intraday` | date=2025-06-02 | **200** | 2157 | 2025-06-02T13:30:05.288000Z | 2025-06-02T20:14:59.573000Z | OK |
| 76 | unusualwhales | `/api/stock/SPY/flow-per-strike-intraday` | date=2026-03-02 | **200** | 2915 | 2026-03-02T14:30:52.212000Z | 2026-03-02T21:14:59.122000Z | per-strike per-minute call/put premium & volume by side |
| 77 | unusualwhales | `/api/stock/SPX/greek-exposure/strike` | date=2026-10-09 | **200** | 890 | 2026-10-09 | 2026-10-09 | INDEX WORKS (890 strikes) |
| 78 | unusualwhales | `/api/stock/SPY/greek-exposure/strike` | date=2025-06-02 | **200** | 336 | 2025-06-02 | 2025-06-02 | per-strike EOD works (call/put gex, delta, charm, vanna) |
| 79 | unusualwhales | `/api/stock/SPY/greek-exposure/strike` | date=2026-03-02 | **200** | 434 | 2026-03-02 | 2026-03-02 | OK |
| 80 | unusualwhales | `/api/stock/SPY/greek-exposure` | date=2025-06-02 | **200** | 0 |  |  | 200 but EMPTY: the daily series starts 2025-10-14 on this token |
| 81 | unusualwhales | `/api/stock/SPY/greek-exposure` | date=2026-03-02 | **200** | 95 | 2025-10-14 | 2026-03-02 | date acts as series end: 2025-10-14 -> 2026-03-02 |
| 82 | unusualwhales | `/api/stock/SPY/greek-exposure` | - | **200** | 251 | 2025-10-14 | 2026-10-13 | daily series 2025-10-14 -> 2026-10-13 (251 rows) |
| 83 | unusualwhales | `/api/stock/SPY/interpolated-iv` | date=2025-06-02 | **200** | 9 | 2025-06-02 | 2025-06-02 | 9 maturities; days=1 row = 0.146, pct 0.344 |
| 84 | unusualwhales | `/api/stock/SPY/interpolated-iv` | date=2026-03-02 | **200** | 9 | 2026-03-02 | 2026-03-02 | ledger start day OK |
| 85 | unusualwhales | `/api/market/market-tide` | date=2022-09-28 | **403** |  |  |  | 403 historic_data_access_missing (floor 2023-11-13) |
| 86 | unusualwhales | `/api/market/market-tide` | date=2024-06-03 | **200** | 82 | 2024-06-03T09:30:00-04:00 | 2024-06-03T16:35:00-04:00 | OK |
| 87 | unusualwhales | `/api/market/market-tide` | date=2026-03-02 | **200** | 81 | 2026-03-02T09:30:00-05:00 | 2026-03-02T16:10:00-05:00 | ledger start day OK (5-min rows, -05:00 offset) |
| 88 | unusualwhales | `/api/stock/SPX/net-prem-ticks` | date=2026-10-09 | **200** | 450 | 2026-10-09T13:30:00Z | 2026-10-09T20:59:00Z | INDEX WORKS |
| 89 | unusualwhales | `/api/stock/SPY/net-prem-ticks` | date=2022-09-28 | **403** |  |  |  | 403 historic_data_access_missing (floor 2023-11-13) |
| 90 | unusualwhales | `/api/stock/SPY/net-prem-ticks` | date=2023-11-13 | **200** | 406 | 2023-11-13T14:30:00Z | 2023-11-13T21:15:00Z | OK exactly at the floor date |
| 91 | unusualwhales | `/api/stock/SPY/net-prem-ticks` | date=2024-06-03 | **200** | 406 | 2024-06-03T13:30:00Z | 2024-06-03T20:15:00Z | OK |
| 92 | unusualwhales | `/api/stock/SPY/net-prem-ticks` | date=2025-06-02 | **200** | 405 | 2025-06-02T13:30:00Z | 2025-06-02T20:14:00Z | OK |
| 93 | unusualwhales | `/api/stock/SPY/net-prem-ticks` | date=2026-03-02 | **200** | 405 | 2026-03-02T14:30:00Z | 2026-03-02T21:14:00Z | ledger start day OK |
| 94 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2025-03-03, limit=3 | **200** | 3 |  |  | historical chain OK |
| 95 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2025-04-01, limit=3 | **200** | 3 |  |  | OK |
| 96 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2025-05-01, limit=3 | **200** | 3 |  |  | OK |
| 97 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2025-05-15, limit=3 | **200** | 3 |  |  | OK |
| 98 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2025-06-02, limit=5 | **200** | 5 |  |  | historical chain OK (SPY250602C00590000 first row) |
| 99 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2026-03-02, limit=100 | **200** | 100 |  |  | `date` honoured: 2026-03-02 expiry chain with that day volume/OI/greeks/NBBO (first row SPY260302C00687000, vol 472,654) |
| 100 | unusualwhales | `/api/stock/SPY/option-contracts` | date=2026-03-02, expiry=2026-03-02, limit=100 | **200** | 100 |  |  | same with expiry filter |
| 101 | unusualwhales | `/api/stock/SPY/option-contracts` | limit=5 | **200** | 5 |  |  | no date -> current chain (2026-10-13 expiry) |
| 102 | massive | `/v2/aggs/ticker/SPY/range/1/minute/2026-03-02/2026-03-02` | adjusted=true, sort=asc, limit=50000 | **200** | 935 | 2026-03-02T09:00:00Z | 2026-03-03T00:59:00Z | OK 935 bars 09:00Z-00:59Z incl. extended hours |
| 103 | massive | `/v2/aggs/ticker/SPY/range/1/minute/2024-06-03/2024-06-03` | adjusted=true, sort=asc, limit=50000 | **403** |  |  |  | 403 NOT_AUTHORIZED "Your plan doesn't include this data timeframe" |
| 104 | massive | `/v2/aggs/ticker/O:SPY260302C00682000/range/1/minute/2026-03-02/2026-03-02` | adjusted=true, sort=asc, limit=50000 | **200** | 354 | 2026-03-02T14:30:00Z | 2026-03-02T21:05:00Z | ledger contract OK (354 bars; UW 356) |
| 105 | massive | `/v2/aggs/ticker/I:SPX/range/1/minute/2026-03-02/2026-03-02` | sort=asc, limit=50000 | **403** |  |  |  | 403 NOT_AUTHORIZED "You are not entitled to this data" |
| 106 | massive | `/v3/trades/O:SPY260302C00682000` | timestamp=2026-03-02, limit=1 | **403** |  |  |  | 403 NOT_AUTHORIZED |
| 107 | massive | `/v3/quotes/O:SPY260302C00682000` | timestamp=2026-03-02, limit=1 | **403** |  |  |  | 403 NOT_AUTHORIZED |
| 108 | massive | `/v2/aggs/ticker/O:RUTW261008C02785000/range/1/minute/2026-10-08/2026-10-08` | adjusted=true, sort=asc, limit=50000 | **200** | 201 | 2026-10-08T13:30:00Z | 2026-10-08T19:59:00Z | latest ledger trade, index-option root RUTW OK (201 bars; UW 204) |
| 109 | massive | `/v2/aggs/ticker/O:NDXP260515P29130000/range/1/minute/2026-05-15/2026-05-15` | adjusted=true, sort=asc, limit=50000 | **200** | 117 | 2026-05-15T13:30:00Z | 2026-05-15T20:00:00Z | NDXP root OK (117 bars; UW 116) |

Row-count conventions: UW `ohlc/1m` rows include pre/post-market bars (`market_time` pr/r/po; RTH is always 390 rows); UW `intraday` rows are 1-minute contract bars (newest first; min/max are the earliest/latest `start_time`); UW `darkpool` was capped by `limit=500`; Massive rows are `results` with `t` = epoch ms (bar start). "200, 0 rows" means the API answered `{"data": []}`.

## 2. What changed vs `DATA_PROVIDER_AUDIT.md`

| topic | DATA_PROVIDER_AUDIT.md (2026-10-13, earlier) | observed today | evidence |
|---|---|---|---|
| Index 1-minute bars on UW | `stock/{t}/ohlc/1m` "works for `SPX` (index) as well as ETFs"; §2 substitutes UW `stock/SPX/ohlc/1m` for Massive's missing `I:SPX` | **422 `cboe_index_access_missing`** for SPX, NDX, RUT and SPXW on 2026-10-09 ("Prices for the CBOE index SPX require provisioned access and CBOE approval") — the substitution rule in §2 of the audit no longer holds | `uw03_ohlc_*` |
| Index bars on Massive | `I:SPX` 403 | unchanged: 403 NOT_AUTHORIZED | `m04` |
| UW throttling | "effectively unthrottled (1000000/min advertised)" | the per-minute header is unchanged but the plan enforces a **concurrency cap of 3 in-flight requests** (429 `concurrent_limit_exceeded`); a fetcher must run ≤ 3 workers | `uw01_ohlc_SPY_1m_2025-06-02` |
| UW history floor | not stated | **403 `historic_data_access_missing`: "The earliest date currently available to this token is 2023-11-13 (730 trading days)"** on `option-contract/…/intraday`, `net-prem-ticks`, `market/market-tide` for dates before it; `net-prem-ticks` works exactly at 2023-11-13 | `uw02_intraday_SPY2306*`, `uw05_net-prem-ticks_SPY_2022-09-28`, `uw05_market-tide_2022-09-28`, `uw05_net-prem-ticks_SPY_2023-11-13` |
| UW underlying 1-minute bars depth | "unknown depth (tested 2026-10-12)" | not gated by the 730-day rule: SPY 1m returns full sessions for 2026-03-02, 2025-06-02, 2025-01-02, 2024-06-03, 2023-06-01 and 2022-09-28 (814 rows); **200 with empty data for 2022-06-01, 2022-01-03, 2021-11-01, 2021-06-01** → floor between 2022-06-01 and 2022-09-28 | `uw01_*` |
| UW contract 1-minute bars depth | "historical dates work" | works for every 2025-04-01 → 2026-10-08 date tested; **200 with empty `data` for every date ≤ 2025-03-03** (2025-03-03, 2025-01-02, 2024-10-14, 2024-08-01, 2024-06-03, 2023-11-13) even though `option-contract/{id}/historic` returns daily rows proving those contracts traded (SPY240603C00528000: volume 349,971 on 2024-06-03; SPY250303C00590000: volume 184,321 on 2025-03-03) → effective 1-minute contract-bar floor between 2025-03-03 and 2025-04-01 | `uw02_intraday_SPY25*`, `uw02_intraday_SPY24*`, `uw02_historic_*` |
| Index option roots on UW | SPXW tested | **SPXW / NDXP / RUTW work; SPX / NDX / RUT roots → 422 "… does not exist"** for weeklies. For the 3rd-Friday ledger contract `SPX260320P06585000` the SPX root answers 200 with 0 rows while `SPXW260320P06585000` returns 280 bars | `uw02_intraday_SPX*`, `uw02_intraday_NDX*`, `uw02_intraday_RUT*` |
| Index option bars on Massive | SPXW verified | **RUTW and NDXP option aggregates also 200** (201 and 117 bars, within 1–3 bars of UW) | `m07`, `m08` |
| Massive stock bars window | 2024-10-14 ok, 2024-01-02 refused | 2026-03-02 ok (935 bars incl. extended hours); **2024-06-03 refused** ("Your plan doesn't include this data timeframe") | `m01`, `m02` |
| Massive trades / quotes | 403 | unchanged 403 on `v3/trades` and `v3/quotes` for a ledger contract | `m05`, `m06` |
| `gex-levels` | SPY 2026-10-12 only | works for SPY on 2026-03-02, 2025-06-02 and 2024-06-03 and **for the SPX index on 2026-10-09** (gamma_flip 7795.46, call wall 7815, put wall 7805, magnet 7810) despite the index-bar block | `uw04_gex-levels_*` |
| `spot-exposures` | SPY 2026-10-12 only | no 90-day limit (2025-06-02: 493 rows; 2024-06-03: 545 rows); **works for SPX** (521 rows on 2026-10-09) and every row carries a per-minute `price` field (SPX `price: 7795` at 10:36Z) | `uw04_spot-exposures_*` |
| `greek-exposure` (ticker-level daily series) | 200 for SPY/SPX/SPXW | with `date=2025-06-02` answers **200, empty**; without `date` returns a 251-row daily series 2025-10-14 → 2026-10-13; with `date=2026-03-02` returns 2025-10-14 → 2026-03-02 (`date` is the series end, start fixed at 2025-10-14). The per-strike variant `greek-exposure/strike?date=` does work for 2025-06-02 (336 strikes), 2026-03-02 (434) and SPX 2026-10-09 (890) | `uw05_greek-exposure*` |
| `flow-alerts` history | not stated | `date` is silently ignored (returns 2026-10-13 alerts); `newer_than`/`older_than` return the 2026-03-02 alerts | `uw05_flow-alerts_*` |
| `stock/{t}/option-contracts` by date | not tested | `date=` is honoured although undocumented: returns that day's chain with volume, OI, prev_oi, side volumes, NBBO bid/ask, IV and delta/gamma/theta/vega/rho (2026-03-02, 2025-06-02, 2025-05-15, 2025-05-01, 2025-04-01, 2025-03-03 all 200) | `uw06_*` |
| `net-prem-ticks`, `flow-per-strike-intraday` on SPX | ETF only | both work for SPX on 2026-10-09 (450 and 1,121 rows) | `uw05_*_SPX_2026-10-09` |
| Cross-provider bar counts | 85 contracts, 0.0 % median close diff | today: SPY260302C00682000 UW 356 / Massive 354 bars, RUTW261008C02785000 204 / 201, NDXP260515P29130000 116 / 117; the first UW bar and the first Massive bar of the SPY contract are both 14:30Z and the last 21:05Z | `uw02_*`, `m03`, `m07`, `m08` |

## 3. Coverage for the GeorgeFi ledger (2026-03-02 → 2026-10-13)

The whole ledger window sits inside every depth limit found today (UW contract bars from ≈2025-04-01, UW 730-trading-day floor 2023-11-13, Massive ≈2-year aggregates window, UW underlying bars from 2022-09-28). Coverage per input, for every trade day in the window:

**Retrievable for every trade day (evidence = status 200 with populated rows on the ledger's own contracts/dates):**

- Option contract 1-minute bars with IV range and ask/bid/mid side premium and volume: UW `option-contract/{{id}}/intraday?date=` — verified on the earliest trade (IWM260302C00259000, 2026-03-02, 130 bars), the latest trade (RUTW261008C02785000, 2026-10-08, 204 bars), SPY260302C00682000 (356), QQQ260303P00595000 (398), SPXW260304C06815000 (164), NDXP260515P29130000 (116), META260819C00545000 (232). Ids are `optionSymbol` minus `O:`. Massive `v2/aggs/ticker/O:…/range/1/minute` is a second copy for the same contracts (354 / 201 / 117 bars), rate-limited to 5/min and ≤ 8 calls were used today.
- Underlying 1-minute bars for ETFs and single names (SPY, QQQ, IWM, META, GLD, TSLA, …): UW `stock/{{t}}/ohlc/1m?date=` (855 rows on 2026-03-02, incl. pre/post) and Massive `v2/aggs/ticker/SPY/range/1/minute` (935 rows).
- Dealer-positioning inputs: `gex-levels?date=` (SPY 2026-03-02 ok; SPX 2026-10-09 ok), `spot-exposures?date=` per minute (SPY 2026-03-02: 549 rows; SPX 2026-10-09: 521 rows), `greek-exposure/strike?date=` EOD per strike (SPY 2026-03-02: 434 strikes; SPX 2026-10-09: 890). The ticker-level `greek-exposure` daily series covers 2025-10-14 → today, i.e. the whole ledger window, when called without `date` or with `date` ≥ 2025-10-14.
- Flow inputs: `flow-per-strike-intraday?date=` (SPY 2026-03-02: 2,915 rows; SPX 2026-10-09: 1,121), `net-prem-ticks?date=` (SPY 2026-03-02: 405 rows; SPX 2026-10-09: 450), `market/market-tide?date=` (2026-03-02: 81 five-minute rows), `darkpool/{{t}}?date=` (SPY 2026-03-02: ≥ 500 prints with NBBO), `option-trades/flow-alerts?newer_than=&older_than=` (2026-03-02 alerts returned; the `date` param must not be used).
- Volatility inputs: `interpolated-iv?date=` (SPY 2026-03-02 and 2025-06-02: 9 maturities each).
- Strike/contract resolution and EOD chain state: `stock/{{t}}/option-contracts?date=` returns the historical chain with volume, OI, NBBO and Greeks for the day (2026-03-02 verified).

**Not retrievable on these entitlements (evidence = non-200 or empty on the ledger's dates):**

- Index 1-minute price bars for ^SPX, ^NDX, ^RUT: UW `stock/SPX|NDX|RUT|SPXW/ohlc/1m` → 422 `cboe_index_access_missing` (2026-10-09; earlier scratchpad probes show the same body for 2026-03-04 and 2025-06-02); Massive `I:SPX` → 403. This affects 184 of 489 ledger trades (145 ^SPX, 16 ^NDX, 23 ^RUT). The only per-minute index level observed on either provider today is the `price` column of UW `stock/SPX/spot-exposures` (521 rows on 2026-10-09); otherwise ETF proxies (SPY/QQQ/IWM) are needed, with basis drift to document. [the proxy/`price` substitution is an inference; the 422/403 are observed]
- Tick-level trades and quotes / NBBO history: Massive `v3/trades` and `v3/quotes` → 403 for a ledger contract; UW tick history was not re-tested today (the committed audit records `option-trades` as latest-day only and `full-tape` as 1.5 GB/day). Spread at entry therefore still has to be estimated from `premium_ask_side`/`premium_bid_side` in the 1-minute bars or from the `nbbo_bid/nbbo_ask` EOD values in `option-contracts?date=`.
- 1-minute bars for the three AM-settled `O:SPX…` monthly contracts (2026-03-20 P6585, 2026-04-17 C7055 ×2): UW `SPX260320P06585000/intraday?date=2026-03-20` → 200 with 0 rows (the PM twin `SPXW260320P06585000` has 280 bars, but it is a different contract); the 2026-04-17 ids and Massive `O:SPX…` were not tested. These 3 trades need a documented special case. [whether GeorgeFi actually traded the AM or the PM contract is not observable from either API]

**Constraints to build the fetcher around:** UW ≤ 3 concurrent requests (429 otherwise), per-minute budget unaffected; Massive ≤ 5/min; any extension of the study before 2025-04-01 loses UW contract minute bars, before 2023-11-13 loses all UW historical option endpoints, before 2022-09-28 loses UW underlying minute bars, and before ≈ late-2024 loses Massive aggregates.
