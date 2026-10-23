# H7 against ordinary nights: the same clock window on every non-FOMC session (descriptive — no new verdict)

**No new verdict.** This file is descriptive. H7's verdict (`6c94bb8`, `H7_H8_REPORT.md`: SPY PASS, QQQ PASS and an EDGE at m = 13), its rule (`PREREG_H7.md`, `edca472`) and its forward rule (`FORWARD_RULE_H7.md`, `fcc1f4d`) are unchanged; nothing here is a test, a pass line or a rule change. The owner's question (2026-10-23): *is this a Fed effect, or ordinary overnight drift?*

Written by `h7_baseline.py`; every number below is in `out/h7_baseline.json`. H7's trades are read as committed (`out/h7_trades.csv`, sha256 `c1af017ae6932dbd6f66e4fcb9fd372eec3851090310770e824447e9c79e0e50`), and recomputed by this script from the raw files as a check (SPY 0 and QQQ 0 differences in net 1×). No vendor fetch; no session after 2026-10-22 read.

## The baseline, exactly

- **Sessions**: per name, every session D from H7's first to its last trade (SPY 2017-02-01 → 2026-09-16, QQQ 2013-03-20 → 2026-09-16 — the same years) that is **not a scheduled FOMC statement day** (the 127 dates of `data/fomc_statements_2012_2026.json`).
- **The same window, prices, costs and dividends as H7**: buy 100 at the official close of the session before D (ThetaData EOD before 2025-10-13, Unusual Whales' daily `r` bar from it), sell at the close of D's 1-minute bar stamped 13:58; $1.50 a trade (1×); a dividend whose ex-date is D paid from H1's table (`Compass H1/data/dividends.json`). Net = 100 (X − C_prev) + 100 DIV − $1.50.
- **Excluded, as H7 excludes**: no official close on the session before, no priced 13:58 bar, and half days — D or the session before is a half day (the file's last priced bar at or before 13:00; a half day has no priced 13:58 bar anyway, and a half day before D would start the hold at a 1:00 pm close). None of H7's sessions is a half day.
- **Excluded, the Fed outside the schedule**: every D whose window holds a day of an unscheduled meeting, conference call, notation vote or the cancelled 2020-03-17/18 meeting listed under `excluded` in the FOMC list — any such day e with session-before(D) ≤ e ≤ D (the meeting's day(s) and any statement date listed; release times are not in the list, so both the session of the event and the one after it are dropped).
- **Calendar mix — the choice**: all baseline sessions are kept, Mondays and post-holiday sessions included (their hold spans a non-trading day). H7's holds: SPY 0 of 77 H7 trades span a non-trading day, weekdays Wed 74, Thu 3; QQQ 0 of 108 H7 trades span a non-trading day, weekdays Wed 104, Thu 4. So the split by whether the hold spans a non-trading day is reported, and a Wednesday-only baseline beside it.
- **Interval**: the 20-session moving-block bootstrap over every calendar session of H7's span (SPY 2017-01-03, QQQ 2012-06-01 → 2026-10-22) — `audit_lib.block_draws(n, 20, B=2,000, seed=20261023)`, `weights_from`, `pct_ci`, the same draws as H7's test. In each draw both means are recomputed on the resampled sessions (H7's Σ W·S ÷ Σ W·N on its statement days, the baseline's on its sessions) and the excess is their difference; the 2.5 and 97.5 percentiles are the interval. H7's own interval in the tables is therefore its committed one.
- **Overnight / morning**: overnight = 100 (09:30 bar's open − C_prev) + the dividend; morning = 100 (13:58 close − 09:30 open); gross, so overnight + morning − $1.50 = net and the cost cancels in every excess. A session with no priced 09:30 open is left out of the split only.

## The comparison (per name; $ a trade of 100 shares, 1×)

| name | H7 trades | H7 mean [95 %] | baseline sessions | baseline mean [95 %] | **excess = H7 − baseline [95 %]** | draws ≤ 0 |
|---|---|---|---|---|---|---|
| SPY | 77 | +70.43 [+14.64, +129.31] | 2,282 | +22.15 [+4.09, +38.67] | **+48.29 [-12.51, +114.68]** | 127 of 2,000 |
| QQQ | 108 | +69.59 [+23.10, +122.14] | 3,204 | +14.88 [+2.34, +27.62] | **+54.71 [+5.12, +108.83]** | 29 of 2,000 |

The split (gross pieces; the excess of the two adds to the total excess):

| name | part | H7 mean | baseline mean [95 %] | excess [95 %] | draws ≤ 0 |
|---|---|---|---|---|---|
| SPY | overnight (close → 09:30 open) | +74.36 | +17.03 [+4.27, +29.21] | +57.33 [+16.50, +102.60] | 4 |
| SPY | morning (09:30 open → 13:58 close) | -2.43 | +6.62 [-4.03, +17.59] | -9.05 [-39.50, +22.58] | 1432 |
| QQQ | overnight (close → 09:30 open) | +72.97 | +12.57 [+3.93, +21.53] | +60.41 [+26.15, +99.84] | 0 |
| QQQ | morning (09:30 open → 13:58 close) | -1.88 | +3.81 [-4.95, +12.40] | -5.70 [-33.01, +19.99] | 1334 |

Calendar mix (H7 against a subset of the baseline; same draws):

| name | baseline subset | sessions | baseline mean [95 %] | excess [95 %] | draws ≤ 0 |
|---|---|---|---|---|---|
| SPY | hold spans no non-trading day | 1,792 | +20.38 [+1.60, +38.47] | +50.05 [-10.87, +115.78] | 115 |
| SPY | hold spans a weekend / holiday | 490 | +28.59 [-8.27, +62.79] | +41.85 [-29.15, +119.95] | 231 |
| SPY | Wednesdays only (H7's usual weekday) | 413 | +52.69 [+16.50, +90.89] | +17.74 [-51.40, +89.28] | 630 |
| QQQ | hold spans no non-trading day | 2,515 | +10.55 [-3.42, +24.88] | +59.04 [+8.72, +113.05] | 20 |
| QQQ | hold spans a weekend / holiday | 689 | +30.67 [+2.07, +61.21] | +38.92 [-18.42, +98.63] | 185 |
| QQQ | Wednesdays only (H7's usual weekday) | 579 | +31.20 [+0.40, +63.53] | +38.39 [-18.90, +99.74] | 191 |

Win share and size in bp of the position (net 1× ÷ 100 C_prev):

| name | H7 win rate | baseline share > 0 | H7 mean bp | baseline mean bp | H7 overnight bp | baseline overnight bp |
|---|---|---|---|---|---|---|
| SPY | 55.8 % | 55.4 % | +19.01 | +5.60 | +19.01 | +4.25 |
| QQQ | 61.1 % | 54.9 % | +21.05 | +5.47 | +23.78 | +4.44 |

## Per calendar year (descriptive)

| year | SPY H7 n | SPY H7 mean | SPY baseline n | SPY baseline mean | SPY baseline > 0 | QQQ H7 n | QQQ H7 mean | QQQ baseline n | QQQ baseline mean | QQQ baseline > 0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | — | — | — | — | — | 7 | -9.93 | 183 | +8.06 | 57 % |
| 2014 | — | — | — | — | — | 8 | -3.44 | 237 | +3.82 | 56 % |
| 2015 | — | — | — | — | — | 8 | +12.57 | 240 | +2.56 | 52 % |
| 2016 | — | — | — | — | — | 8 | -20.75 | 242 | -2.92 | 50 % |
| 2017 | 8 | +0.50 | 219 | +19.83 | 56 % | 8 | -4.56 | 239 | +12.65 | 59 % |
| 2018 | 8 | +43.94 | 237 | +2.42 | 56 % | 8 | +38.19 | 237 | +2.13 | 56 % |
| 2019 | 8 | -4.65 | 234 | +25.72 | 57 % | 8 | +30.71 | 234 | +16.61 | 58 % |
| 2020 | 7 | +285.20 | 228 | +23.05 | 60 % | 7 | +273.00 | 228 | +31.17 | 61 % |
| 2021 | 8 | -100.59 | 242 | +52.07 | 58 % | 8 | -109.81 | 242 | +28.63 | 55 % |
| 2022 | 8 | +332.50 | 241 | -56.83 | 44 % | 8 | +399.29 | 241 | -74.70 | 44 % |
| 2023 | 8 | +30.82 | 238 | +32.67 | 55 % | 8 | +51.19 | 238 | +52.14 | 56 % |
| 2024 | 8 | +175.51 | 238 | +41.99 | 57 % | 8 | +229.09 | 238 | +39.48 | 58 % |
| 2025 | 8 | +45.25 | 234 | +30.59 | 57 % | 8 | +20.79 | 234 | +35.57 | 56 % |
| 2026 | 6 | -126.53 | 171 | +61.48 | 53 % | 6 | +88.00 | 171 | +69.06 | 50 % |

## Exclusions and notes

- SPY: D or the session before is a half day: 40 (2017-07-03, 2017-07-05, 2017-11-24, 2017-11-27, 2018-07-03, 2018-07-05, 2018-11-23, 2018-11-26, 2018-12-24, 2018-12-26, 2019-07-03, 2019-07-05 …); unscheduled meeting / call / notation vote / cancelled meeting in the window (prev ≤ event day ≤ D): 20 (2019-10-04, 2019-10-07, 2019-10-11, 2019-10-14, 2020-03-02, 2020-03-03, 2020-03-04, 2020-03-16, 2020-03-17, 2020-03-18, 2020-03-19, 2020-03-20 …). Baseline sessions with a dividend term: 35. Baseline sessions spanning a non-trading day: 490.
- QQQ: D or the session before is a half day: 56 (2013-07-03, 2013-07-05, 2013-11-29, 2013-12-02, 2013-12-24, 2013-12-26, 2014-11-28, 2014-12-01, 2014-12-24, 2014-12-26, 2015-11-27, 2015-11-30 …); no priced 13:58 bar: 2 (2013-08-22, 2014-07-03); unscheduled meeting / call / notation vote / cancelled meeting in the window (prev ≤ event day ≤ D): 24 (2013-10-16, 2013-10-17, 2014-03-04, 2014-03-05, 2019-10-04, 2019-10-07, 2019-10-11, 2019-10-14, 2020-03-02, 2020-03-03, 2020-03-04, 2020-03-16 …). Baseline sessions with a dividend term: 53. Baseline sessions spanning a non-trading day: 689.
- The Fed's off-schedule days read from the list: 2013-10-16, 2014-03-04, 2019-10-04, 2019-10-11, 2020-03-02, 2020-03-03, 2020-03-15, 2020-03-17, 2020-03-18, 2020-03-19, 2020-03-23, 2020-03-31, 2020-08-27, 2025-08-22.
- H1's dividend table ends at SPY 2025-12-19 (QQQ 2026-09-21), as in H7. SPY's 2026 ex-dates (March, June, September; the third-Friday pattern) are not in it, so up to three SPY baseline sessions in 2026 carry the ex-date price drop with no dividend term — about 100 × $1.9 each over ~2,300 sessions, roughly −$0.25 on SPY's baseline mean (an estimate, not computed): it would lower SPY's excess by about that, far inside the interval.
- The session after a statement day is in the baseline (its window starts at the statement day's close). No financing is charged on either side (as H7). H7 and the baseline share the costs, so the excess is a difference in gross drift.

## The answer, plainly (descriptive — no new verdict)

**SPY.** H7 averaged +70.43 a trade; an ordinary non-FOMC session over the same window averaged +22.15 (+5.60 bp of the position; 55.4 % of them positive against H7's 55.8 %). The excess is +48.29 a trade, 95 % [-12.51, +114.68] — **the interval includes zero: H7's result is not distinguishable from ordinary close → 13:58 drift.** Overnight excess +57.33 [+16.50, +102.60] (clear of zero); morning excess -9.05 [-39.50, +22.58] (not clear of zero).

**QQQ.** H7 averaged +69.59 a trade; an ordinary non-FOMC session over the same window averaged +14.88 (+5.47 bp of the position; 54.9 % of them positive against H7's 61.1 %). The excess is +54.71 a trade, 95 % [+5.12, +108.83] — **the interval excludes zero: the FOMC nights earned more than ordinary nights in the same window.** Overnight excess +60.41 [+26.15, +99.84] (clear of zero); morning excess -5.70 [-33.01, +19.99] (not clear of zero).

**What the numbers say together.** The ordinary drift over this window is positive and small: SPY +22.15 a session (+5.60 bp), about 31 % of H7's mean; QQQ +14.88 a session (+5.47 bp), about 21 % of H7's mean. In both names the excess is the night — the close → 09:30 piece of H7 is larger than an ordinary night's and that difference is clear of zero in both — while the 09:30 → 13:58 morning on statement days is no better than an ordinary morning (its excess is negative in both and not clear of zero), the morning giving back part of the night. The total excess is clear of zero for QQQ and not for SPY (SPY's span is 77 statements from 2017; QQQ's 108 from 2013). Against the Wednesday-only baseline — H7's own weekday, whose ordinary drift is larger in this sample — the excess is SPY +17.74 [-51.40, +89.28]; QQQ +38.39 [-18.90, +99.74], neither clear of zero. By year (table above) H7 is above the baseline in SPY 5 of 10 years; QQQ 7 of 14 years, and the excess is concentrated in a few years (2020, 2022 and 2024 above all). SPY and QQQ trade the same nights, so the two names are not independent evidence.

**Plainly:** the FOMC-eve nights earned more than ordinary nights over the same clock window — clearly in QQQ, and in the overnight piece of both names — but SPY's total excess and both names' excess over ordinary Wednesdays are not distinguishable from zero; ordinary close → 13:58 drift is about +22.15 / +14.88 a session (SPY / QQQ), 31 % / 21 % of H7's average, and not its distinctive part, the night's excess. This is a description; H7's verdict (`6c94bb8`) and the forward rule (`fcc1f4d`) are unchanged, and nothing here is a new test or a pass line.

