# H1 — overnight reversal of the late-day move (SPY, QQQ stock): the pre-registered test, run once

PREREG_H1.md sha256 `30209e95a926bef54d4b51e5abf4c75b1912c20c1e26bf5f52929b4f66e0b2af` (the file as committed alone before this run). Written by `run_h1.py`; every number below is in `out/h1_summary.json` and every session in `out/h1_sessions.csv`.

## Verdict (at 1x costs; the pass rule: mean $ a trade after costs > 0 and the 20-session block-bootstrap interval clear of zero, in each name)

| name | span (signal sessions) | sessions in | trades | long / short / flat | mean $ a trade, 1x [95% block-20] | verdict 1x | mean $ a trade, 2x [95% block-20] | at 2x | win rate 1x | total 1x | worst trade 1x |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 2017-01-03 → 2025-10-10 | 2,188 | 2,177 | 1,086 / 1,091 / 11 | +11.09 [-4.42, +28.72] | **FAIL** | +9.09 [-6.42, +26.72] | not clear | 50.8% | +24,135 | -1,750 |
| QQQ | 2012-06-01 → 2025-10-10 | 3,329 | 3,299 | 1,586 / 1,713 / 30 | +9.42 [-0.06, +18.61] | **FAIL** | +7.42 [-2.06, +16.61] | not clear | 50.5% | +31,083 | -1,449 |

**H1 FAILS** its pre-registered rule (it needs both names).

**Reading (descriptive, no verdict).** The mean is positive in both names at 1x and 2x, but neither 20-session block interval is clear of zero, so neither name passes and H1 fails as registered. SPY: the long trades (close below the 15:00 price) average +26.55 and the short trades -4.30 a trade at 1x. QQQ: the long trades (close below the 15:00 price) average +22.49 and the short trades -2.67 a trade at 1x. The positive mean comes from the long side, which carries the market's overnight drift as well as any reversal; the short side, which should profit from a reversal of an up-move into the close, loses after costs. The per-year means swing in sign.

**Verification.** `verify_h1.py` re-derived 50 random trades (25 a name, seed 20261023) from the raw files with plain loops: 0 differences; excluded sessions carrying a P&L: 0.

## Sensitivity (pre-specified): the flagged sessions out

Flagged = the after-hours study's list (`afterhours_close_check.csv`) plus every session in the span where |EOD close − 15:59 bar close| > $0.25.

| name | flagged sessions | trades left | mean $ a trade 1x [block-20] | 2x [block-20] | rule at 1x |
|---|---|---|---|---|---|
| SPY | 24 | 2,153 | +8.89 [-4.44, +21.84] | +6.89 [-6.44, +19.84] | not clear |
| QQQ | 37 | 3,262 | +8.48 [-0.71, +17.41] | +6.48 [-2.71, +15.41] | not clear |

SPY flagged: 2018-02-28 (EOD 271.6500, 15:59 271.3300), 2018-03-29 (EOD 263.1500, 15:59 263.4900), 2018-04-04 (EOD 263.5600, 15:59 263.8300), 2019-12-11 (EOD 313.4393, 15:59 314.4100), 2020-01-23 (EOD 330.5204, 15:59 331.7400), 2020-03-09 (EOD 276.3200, 15:59 274.4000), 2020-03-13 (EOD 271.4754, 15:59 270.9300), 2020-03-16 (EOD 239.8500, 15:59 239.4100), 2020-03-17 (EOD 252.8000, 15:59 254.1900), 2020-03-18 (EOD 235.7300, 15:59 241.0100), 2020-03-23 (EOD 222.9619, 15:59 222.5100), 2020-03-24 (EOD 243.1500, 15:59 243.5900), 2020-03-26 (EOD 262.0841, 15:59 261.3900), 2021-11-30 (EOD 455.5600, 15:59 455.8400), 2022-06-16 (EOD 366.6500, 15:59 366.9300), 2023-12-20 (EOD 468.2600, 15:59 467.9700), 2024-06-21 (EOD 544.5100, 15:59 544.1300), 2024-07-31 (EOD 550.8100, 15:59 550.4400), 2024-09-30 (EOD 573.7600, 15:59 574.0200), 2024-12-20 (EOD 591.1500, 15:59 590.8700), 2025-04-03 (EOD 536.7000, 15:59 537.6400), 2025-04-08 (EOD 496.4800, 15:59 496.7400), 2025-04-09 (EOD 548.6200, 15:59 543.3700), 2025-04-22 (EOD 527.2500, 15:59 526.9400).

QQQ flagged: 2018-07-31 (EOD 176.4500, 15:59 176.1600), 2018-10-29 (EOD 163.2300, 15:59 163.7200), 2020-02-28 (EOD 205.8000, 15:59 206.6700), 2020-03-13 (EOD 192.3400, 15:59 193.9600), 2020-03-16 (EOD 169.3000, 15:59 169.5700), 2020-03-26 (EOD 191.9000, 15:59 192.1600), 2020-03-27 (EOD 185.3000, 15:59 184.9400), 2020-04-30 (EOD 218.9100, 15:59 219.1700), 2020-05-29 (EOD 233.3600, 15:59 232.8800), 2020-06-30 (EOD 247.6000, 15:59 247.2800), 2020-09-30 (EOD 277.8400, 15:59 278.1000), 2020-10-30 (EOD 269.3800, 15:59 269.7100), 2020-11-30 (EOD 299.6200, 15:59 299.3600), 2021-01-27 (EOD 319.4300, 15:59 319.7500), 2021-03-19 (EOD 313.1400, 15:59 313.4200), 2021-04-28 (EOD 339.0000, 15:59 338.7400), 2021-12-31 (EOD 397.8500, 15:59 397.5600), 2022-01-24 (EOD 353.3000, 15:59 353.5800), 2022-01-26 (EOD 344.5700, 15:59 344.9800), 2022-02-28 (EOD 346.8000, 15:59 347.1500), 2022-03-31 (EOD 362.5400, 15:59 362.0000), 2022-04-18 (EOD 338.6900, 15:59 338.9600), 2022-05-05 (EOD 313.0000, 15:59 313.3900), 2022-06-24 (EOD 294.6100, 15:59 294.9900), 2023-05-31 (EOD 347.9900, 15:59 347.6600), 2023-07-19 (EOD 385.6500, 15:59 385.3900), 2023-10-18 (EOD 363.3700, 15:59 363.0900), 2023-12-15 (EOD 405.3400, 15:59 404.9400), 2024-05-31 (EOD 450.7100, 15:59 451.6900), 2024-08-05 (EOD 435.3700, 15:59 435.7500), 2025-03-03 (EOD 497.0500, 15:59 497.3200), 2025-03-10 (EOD 472.7300, 15:59 473.3000), 2025-03-21 (EOD 480.8400, 15:59 481.1200), 2025-04-04 (EOD 422.6700, 15:59 423.2012), 2025-04-07 (EOD 423.6900, 15:59 423.9500), 2025-04-09 (EOD 466.0000, 15:59 465.1400), 2025-05-01 (EOD 481.6800, 15:59 481.1900).

## The pieces of the mean (descriptive)

| name | gross price P&L a trade | dividend a trade | borrow a trade | costs a trade 1x / 2x | trades over an ex-date | long trades, mean 1x | short trades, mean 1x |
|---|---|---|---|---|---|---|---|
| SPY | +13.35 | -0.03 | -0.24 | −2.00 / −4.00 | 35 | 1,086: +26.55 | 1,091: -4.30 |
| QQQ | +11.63 | -0.06 | -0.14 | −2.00 / −4.00 | 56 | 1,586: +22.49 | 1,713: -2.67 |

## Per year (descriptive only)

| year | SPY trades | SPY mean 1x | SPY mean 2x | QQQ trades | QQQ mean 1x | QQQ mean 2x |
|---|---|---|---|---|---|---|
| 2012 | — | — | — | 142 | -1.78 | -3.78 |
| 2013 | — | — | — | 247 | +3.03 | +1.03 |
| 2014 | — | — | — | 244 | -3.18 | -5.18 |
| 2015 | — | — | — | 246 | -1.75 | -3.75 |
| 2016 | — | — | — | 248 | +1.43 | -0.57 |
| 2017 | 245 | +6.27 | +4.27 | 248 | +0.93 | -1.07 |
| 2018 | 246 | -8.82 | -10.82 | 247 | -8.40 | -10.40 |
| 2019 | 248 | -15.09 | -17.09 | 248 | -14.19 | -16.19 |
| 2020 | 251 | +60.54 | +58.54 | 247 | +38.01 | +36.01 |
| 2021 | 251 | +8.11 | +6.11 | 247 | +17.11 | +15.11 |
| 2022 | 247 | +31.70 | +29.70 | 249 | +36.64 | +34.64 |
| 2023 | 247 | +6.02 | +4.02 | 246 | +11.10 | +9.10 |
| 2024 | 249 | +22.58 | +20.58 | 248 | +41.73 | +39.73 |
| 2025 | 193 | -18.96 | -20.96 | 192 | +5.13 | +3.13 |

## Sessions left out

**SPY** — 18 of 2206 calendar sessions in 2017-01-03 → 2025-10-10:

- half day; no priced 14:59 bar: 18 — 2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23, 2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03

**QQQ** — 31 of 3360 calendar sessions in 2012-06-01 → 2025-10-10:

- half day; no priced 14:59 bar: 30 — 2012-07-03, 2012-11-23, 2012-12-24, 2013-07-03, 2013-11-29, 2013-12-24, 2014-07-03, 2014-11-28, 2014-12-24, 2015-11-27, 2015-12-24, 2016-11-25, 2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23, 2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03
- no priced 14:59 bar: 1 — 2013-08-22

## Notes on the run (deviations from the prereg's wording, none in the rule)

- `run_h1.py` was run once for the result. It was re-run afterwards only to write this report's reading, verification line and these notes and to round the flagged closes to four decimals; every re-run left `out/h1_summary.json` and `out/h1_sessions.csv` byte-identical to the first run (sha256 checked).
- The prereg says the verifier reads the files "with pyarrow"; the container has no pyarrow, so `verify_h1.py` reads each Parquet file into Python lists with polars and does everything else in plain loops (its own session list, next session, EOD lookup by the `created` date, bar lookup by stamp, side, dividend, borrow, costs); it shares no code with `run_h1.py`.
- Stage 1 (`fetch/FETCH_NOTES.md`): 15 ThetaData requests, 142 KB; SPY EOD 2012–2016 NOT_FOUND and the SPY 2016 bar probe NaN, so SPY starts 2017-01-03 as the prereg states; no stored file was changed.

