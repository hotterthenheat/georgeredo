# H4 — market intraday momentum (first half-hour → last half-hour), SPY and QQQ stock: the pre-registered test, run once

PREREG_H4.md sha256 `714a09a6517ba68f8165686585c978f02e7cd37f7fdea6b75752a40a8087b0fe` (the file as committed alone, `b14b640`, before this run). Written by `run_h4.py`; every number below is in `out/h4_summary.json` and every session in `out/h4_sessions.csv`.

Rule: r1 = the 09:59 bar's close ÷ the previous session's official close − 1; long 100 shares at the 15:30 bar's open if r1 > 0, short if r1 < 0, flat if equal; exit at the official close (ThetaData EOD before 2025-10-13, Unusual Whales' daily bar from it); half days out; $0.005 a share at entry and $0.01 in the auction ($1.50 a trade at 1×, $3.00 at 2×), borrow pro rata for 30 minutes.

## Verdict — the test span, 2025-10-13 → 2026-10-22, each name on its own (pass: mean $ a trade after costs at 1× > 0 and the 20-session block-bootstrap 95 % interval clear of zero)

| name | sessions in | trades | long / short / flat | mean $ a trade, 1× [95 % block-20] | verdict | mean $ a trade, 2× [95 % block-20] | at 2× | win rate 1× | total 1× | worst / best trade 1× |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 257 | 257 | 142 / 115 / 0 | -2.95 [-19.01, +15.37] | **FAIL** | -4.45 [-20.51, +13.87] | not clear | 45.5 % | -757 | -373 / +573 |
| QQQ | 257 | 257 | 138 / 119 / 0 | +10.32 [-8.56, +35.77] | **FAIL** | +8.82 [-10.06, +34.27] | not clear | 49.8 % | +2,651 | -378 / +902 |

**SPY: FAIL.**
**QQQ: FAIL.**

**Bonferroni (PREREG §5, α = 0.05 ÷ (2 names × m), the same 2,000 draws; coarse tails).**

| name | 1× interval at m = 3 (α 0.833 %) | EDGE at m = 3 | 1× interval at m = 8 (α 0.3125 %) | EDGE at m = 8 |
|---|---|---|---|---|
| SPY | [-24.56, +21.45] | no | [-25.89, +23.54] | no |
| QQQ | [-15.38, +44.27] | no | [-19.36, +50.14] | no |

**Verification.** `verify_h4.py` re-derived 60 traded sessions (20 test + 10 exploration a name, seed 20261024) from the raw files with plain loops and no shared code: 0 differences in 600 fields; sessions carrying a P&L while excluded: 0; sessions whose traded flag disagrees with side: 0.

## Test span, descriptive (no verdict)

| name | gross price P&L a trade | costs a trade 1× / 2× | borrow a short | long trades: n, mean 1×, win | short trades: n, mean 1×, win |
|---|---|---|---|---|---|
| SPY | -1.44 | −1.50 / −3.00 | -0.0124 | 142, -7.65, 42.3 % | 115, +2.86, 49.6 % |
| QQQ | +11.82 | −1.50 / −3.00 | -0.0115 | 138, +9.85, 50.0 % | 119, +10.86, 49.6 % |

Per calendar year of the test span:

| year | SPY trades | SPY mean 1× | SPY mean 2× | QQQ trades | QQQ mean 1× | QQQ mean 2× |
|---|---|---|---|---|---|---|
| 2025 | 54 | -15.59 | -17.09 | 54 | -8.08 | -9.58 |
| 2026 | 203 | +0.42 | -1.08 | 203 | +15.21 | +13.71 |

SPY traded test sessions on an ex-date in H1's dividend table (r1 carries the dividend drop; the table has no SPY ex-date after 2025-12-19): 2025-12-19 (long, r1 +0.495 %, net +8.50).

QQQ traded test sessions on an ex-date in H1's dividend table (r1 carries the dividend drop): 2025-12-22 (long, r1 +0.572 %, net +7.50), 2026-03-23 (long, r1 +1.876 %, net -199.00), 2026-06-22 (long, r1 +0.550 %, net +244.50), 2026-09-21 (long, r1 +1.541 %, net -30.50).

**Reading (descriptive, no verdict).** SPY: the gross price P&L is -1.44 a trade before the $1.50 of costs, the long trades average -7.65 and the short trades +2.86 at 1×, and the interval spans -19.01 to +15.37. QQQ: the gross price P&L is +11.82 a trade before the $1.50 of costs, the long trades average +9.85 and the short trades +10.86 at 1×, and the interval spans -8.56 to +35.77. Neither interval is clear of zero, so neither name passes. The intervals are about as wide as PREREG §6 expected (an a-priori standard error of $10–13 a trade); a true mean below roughly $30 a trade could not have been detected on 257 sessions, so the fail says little about an effect of the size the literature reports. On the exploration span (context only) neither name shows a positive mean either: SPY -1.51 and QQQ -2.53 a trade at 1×, in line with the earlier open-signed reads (PREREG §7).

**How close r1 is to the open-signed first half hour the earlier reads used (not pre-registered; descriptive, for PREREG §7).** Share of included sessions where sign(r1) equals the sign of the 09:30 bar's open → the 09:59 bar's close: QQQ exploration 2254 of 3301 (68.3 %); QQQ test 167 of 255 (65.5 %); SPY exploration 1383 of 2175 (63.6 %); SPY test 172 of 257 (66.9 %).

## Exploration span (context only — PREREG §3: no choice was made from it and it carries no verdict)

| name | span | sessions in | trades | long / short / flat | mean $ a trade, 1× [95 % block-20] | 2× [95 % block-20] | win rate 1× | worst / best 1× | long mean 1× | short mean 1× |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 2017-01-04 → 2025-10-10 | 2,187 | 2,184 | 1,216 / 968 / 3 | -1.51 [-6.62, +4.34] | -3.01 [-8.12, +2.84] | 48.9 % | -745 / +1,249 | -2.96 | +0.32 |
| QQQ | 2012-06-04 → 2025-10-10 | 3,328 | 3,319 | 1,838 / 1,481 / 9 | -2.53 [-5.18, +0.67] | -4.03 [-6.68, -0.83] | 48.1 % | -753 / +780 | -2.53 | -2.54 |

Per year, exploration (descriptive):

| year | SPY trades | SPY mean 1× | SPY mean 2× | QQQ trades | QQQ mean 1× | QQQ mean 2× |
|---|---|---|---|---|---|---|
| 2012 | — | — | — | 142 | -0.84 | -2.34 |
| 2013 | — | — | — | 245 | -0.40 | -1.90 |
| 2014 | — | — | — | 245 | -0.32 | -1.82 |
| 2015 | — | — | — | 250 | -0.86 | -2.36 |
| 2016 | — | — | — | 251 | -1.89 | -3.39 |
| 2017 | 246 | -2.71 | -4.21 | 249 | -1.55 | -3.05 |
| 2018 | 248 | -2.21 | -3.71 | 248 | +3.97 | +2.47 |
| 2019 | 248 | -2.07 | -3.57 | 249 | -2.06 | -3.56 |
| 2020 | 251 | +5.04 | +3.54 | 251 | +8.79 | +7.29 |
| 2021 | 251 | -14.11 | -15.61 | 250 | -13.21 | -14.71 |
| 2022 | 250 | -7.61 | -9.11 | 250 | -12.83 | -14.33 |
| 2023 | 248 | +6.98 | +5.48 | 248 | -6.82 | -8.32 |
| 2024 | 249 | -2.61 | -4.11 | 248 | -2.62 | -4.12 |
| 2025 | 193 | +7.96 | +6.46 | 193 | -4.47 | -5.97 |

## Sessions left out

**SPY, exploration** — 19 of 2206 calendar sessions:

- half day; no priced 15:30 bar: 18 — 2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23, 2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03
- no official close on the previous session 2016-12-30: 1 — 2017-01-03

**SPY, test** — 2 of 259 calendar sessions:

- half day; no priced 15:30 bar: 2 — 2025-11-28, 2025-12-24

**QQQ, exploration** — 32 of 3360 calendar sessions:

- half day; no priced 15:30 bar: 30 — 2012-07-03, 2012-11-23, 2012-12-24, 2013-07-03, 2013-11-29, 2013-12-24, 2014-07-03, 2014-11-28, 2014-12-24, 2015-11-27, 2015-12-24, 2016-11-25, 2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23, 2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03
- no official close on the previous session None: 1 — 2012-06-01
- no priced 15:30 bar: 1 — 2013-05-09

**QQQ, test** — 2 of 259 calendar sessions:

- half day; no priced 15:30 bar: 2 — 2025-11-28, 2025-12-24

## Notes on the run (none changes the rule)

- `run_h4.py` was run once for the result. It was re-run afterwards only to write the verification line, the reading, the signal overlap and these notes into this report; every re-run left `out/h4_summary.json` and `out/h4_sessions.csv` byte-identical to the first run (sha256 checked). The overlap figure is written to its own file, `out/h4_signal_overlap.json`, and is not a variant.
- PREREG §8 says the verifier uses no pyarrow; it reads each Parquet file into Python lists with polars and does everything else in plain loops (its own session list, previous session, official close by source and date, bar lookup by stamp, side, gross, costs, borrow).
- QQQ 2013-05-09 has no priced 15:30 bar in the stored file and is excluded by the rule (exploration; no other bar substituted). QQQ 2013-08-22 (the Nasdaq halt, reopened 15:25) has priced 09:59 and 15:30 bars and is included.
- No vendor fetch was made. Sessions from 2026-10-23 were not read. Since neither name passed, no FORWARD rule is committed (PREREG §4).

