# ThetaData 0DTE research dataset — manifest

Generated 2026-10-14T03:10:33 from `/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta/data` (outside the repo). One row per file in `manifest.csv.gz` (columns: data_type, symbol, date, rows, strikes, min_strike, max_strike, ref_price, ref_time, ref_status, band_lo, band_hi, raw_rows, raw_strikes, in_calendar, bytes, sha256). Loader: `load.py`; build/verify commands: `README.md`.

## Scope

| Symbol | First daily-expiry date (every weekday session has an expiration, from `option_list_expirations`) | Chain sessions to 2026-10-09 |
|---|---|---|
| SPY | 2022-11-11 | 980 |
| QQQ | 2022-11-11 | 980 |
| SPXW | 2022-05-13 | 1106 |
| IWM | 2024-04-19 | 621 |

Chains/OHLC: same-day expiration, both rights, 1-minute, strikes within ±2.0 % of the 09:31 underlying print (ETFs: open of the 09:31 bar; SPXW: SPX index value at 09:31:00), 09:30–16:00 ET. Underlying (SPY, QQQ, IWM 1-minute OHLC) and index (SPX, VIX 1-minute price) cover every NYSE session 2017-06-01 → 2026-10-09 (SPX, VIX and SPY converted from the index_tests cache pulled 2026-10-13 with the same client; QQQ and IWM fetched here).

## Files per data type and symbol

| Data type | Symbol | Expected sessions | Files | No-data (API) | Missing (not fetched) | Empty files | Fallback ref | Strikes/file min–max | Rows | MB |
|---|---|---|---|---|---|---|---|---|---|---|
| chains | SPY | 980 | 980 | 0 | 0 | 0 | 0 | 12–36 | 17,335,767 | 145.1 |
| chains | QQQ | 980 | 980 | 0 | 0 | 0 | 0 | 9–35 | 15,310,387 | 126.7 |
| chains | SPXW | 1106 | 1106 | 0 | 0 | 0 | 0 | 27–63 | 37,631,795 | 258.3 |
| chains | IWM | 621 | 621 | 0 | 0 | 0 | 0 | 5–15 | 4,735,010 | 38.7 |
| ohlc | SPY | 980 | 91 | 0 | 889 | 0 | 0 | 12–19 | 1,143,284 | 9.3 |
| ohlc | QQQ | 980 | 0 | 0 | 980 | 0 | 0 | None–None | 0 | 0.0 |
| ohlc | SPXW | 1106 | 0 | 0 | 1106 | 0 | 0 | None–None | 0 | 0.0 |
| ohlc | IWM | 621 | 0 | 0 | 621 | 0 | 0 | None–None | 0 | 0.0 |
| underlying | SPY | 2353 | 2442 | 0 | 0 | 0 | 0 | None–None | 954,822 | 27.2 |
| underlying | QQQ | 2353 | 2353 | 0 | 0 | 0 | 0 | None–None | 920,023 | 27.3 |
| underlying | IWM | 2353 | 2353 | 0 | 0 | 0 | 0 | None–None | 920,023 | 25.6 |
| index | SPX | 2353 | 2353 | 0 | 0 | 0 | 0 | None–None | 920,023 | 7.9 |
| index | VIX | 2353 | 2386 | 0 | 0 | 0 | 0 | None–None | 932,926 | 6.9 |

**Total: 15,665 files, 80,804,060 rows, 0.67 GB.**

## Sessions without data

- chains/SPY: complete
- chains/QQQ: complete
- chains/SPXW: complete
- chains/IWM: complete
- ohlc/SPY: not fetched (889): 2023-03-27, 2023-03-28, 2023-03-29, 2023-03-30, 2023-03-31, 2023-04-03, 2023-04-04, 2023-04-05, 2023-04-06, 2023-04-10, 2023-04-11, 2023-04-12, 2023-04-13, 2023-04-14, 2023-04-17, 2023-04-18, 2023-04-19, 2023-04-20, 2023-04-21, 2023-04-24, 2023-04-25, 2023-04-26, 2023-04-27, 2023-04-28, 2023-05-01, 2023-05-02, 2023-05-03, 2023-05-04, 2023-05-05, 2023-05-08, 2023-05-09, 2023-05-10, 2023-05-11, 2023-05-12, 2023-05-15, 2023-05-16, 2023-05-17, 2023-05-18, 2023-05-19, 2023-05-22 …
- ohlc/QQQ: not fetched (980): 2022-11-11, 2022-11-14, 2022-11-15, 2022-11-16, 2022-11-17, 2022-11-18, 2022-11-21, 2022-11-22, 2022-11-23, 2022-11-25, 2022-11-28, 2022-11-29, 2022-11-30, 2022-12-01, 2022-12-02, 2022-12-05, 2022-12-06, 2022-12-07, 2022-12-08, 2022-12-09, 2022-12-12, 2022-12-13, 2022-12-14, 2022-12-15, 2022-12-16, 2022-12-19, 2022-12-20, 2022-12-21, 2022-12-22, 2022-12-23, 2022-12-27, 2022-12-28, 2022-12-29, 2022-12-30, 2023-01-03, 2023-01-04, 2023-01-05, 2023-01-06, 2023-01-09, 2023-01-10 …
- ohlc/SPXW: not fetched (1106): 2022-05-13, 2022-05-16, 2022-05-17, 2022-05-18, 2022-05-19, 2022-05-20, 2022-05-23, 2022-05-24, 2022-05-25, 2022-05-26, 2022-05-27, 2022-05-31, 2022-06-01, 2022-06-02, 2022-06-03, 2022-06-06, 2022-06-07, 2022-06-08, 2022-06-09, 2022-06-10, 2022-06-13, 2022-06-14, 2022-06-15, 2022-06-16, 2022-06-17, 2022-06-21, 2022-06-22, 2022-06-23, 2022-06-24, 2022-06-27, 2022-06-28, 2022-06-29, 2022-06-30, 2022-07-01, 2022-07-05, 2022-07-06, 2022-07-07, 2022-07-08, 2022-07-11, 2022-07-12 …
- ohlc/IWM: not fetched (621): 2024-04-19, 2024-04-22, 2024-04-23, 2024-04-24, 2024-04-25, 2024-04-26, 2024-04-29, 2024-04-30, 2024-05-01, 2024-05-02, 2024-05-03, 2024-05-06, 2024-05-07, 2024-05-08, 2024-05-09, 2024-05-10, 2024-05-13, 2024-05-14, 2024-05-15, 2024-05-16, 2024-05-17, 2024-05-20, 2024-05-21, 2024-05-22, 2024-05-23, 2024-05-24, 2024-05-28, 2024-05-29, 2024-05-30, 2024-05-31, 2024-06-03, 2024-06-04, 2024-06-05, 2024-06-06, 2024-06-07, 2024-06-10, 2024-06-11, 2024-06-12, 2024-06-13, 2024-06-14 …
- underlying/SPY: complete
- underlying/QQQ: complete
- underlying/IWM: complete
- index/SPX: complete
- index/VIX: complete

## Build run

progress.json: done=1400 pending=3628 elapsed=2843 s, login generations=1, final=False; per job class ok/nodata/err/unauth: chain/SPXW: 737/0/0/0, chain/IWM: 621/0/0/0, ohlc/SPY: 42/0/0/0

## Verification (verify.py)

Fresh 1-second NBBO pulls on 2026-10-14T03:09:24 for 5 random session files; at every minute boundary present in both series the 1-minute row must equal the 1-second row (bid, ask, bid_size, ask_size).

| Symbol | Date | Strike | Right | 1-min rows | 1-sec rows | Minutes compared | Mismatches | Result |
|---|---|---|---|---|---|---|---|---|
| QQQ | 2024-04-02 | 440.0 | CALL | 391 | 23401 | 391 | 0 | PASS |
| SPY | 2025-05-01 | 560.0 | CALL | 391 | 23401 | 391 | 0 | PASS |
| QQQ | 2025-05-30 | 515.0 | CALL | 391 | 23401 | 391 | 0 | PASS |
| SPXW | 2025-03-10 | 5690.0 | PUT | 391 | 23401 | 391 | 0 | PASS |
| SPY | 2023-08-28 | 442.0 | CALL | 391 | 23401 | 391 | 0 | PASS |

- 1-second rows at hh:mm:00 are compared with the stored 1-minute rows (same contract, same session); the 09:30:00 placeholder row is included when both series carry it.
