# H7 (pre-FOMC drift) and H8 (turn of the month), SPY and QQQ stock: the pre-registered tests, run once

PREREG_H7.md sha256 `f81606b5c0a0f0e21e9234b2fc5cc77c0c51fb3f1dcaaa79010b3dfdcb519742`; PREREG_H8.md sha256 `4ccbe9680168c398f7a39b334c580b2e7ced88152995632c4628e4152f719fea`; PREREG_H9.md sha256 `932ddac43caefbd7159f2f1844d8ef64c00e62cd940d8a3dcfe13cf4b812b7c1` (the three files as committed alone, `edca472`, before this run). The FOMC list `data/fomc_statements_2012_2026.json` sha256 `550fb00f314d70abfeb385573e8cce8a0df23719621d059f1f683ec14fb79901`. Written by `run_h7_h8.py`; every number below is in `out/h7_h8_summary.json`, every trade in `out/h7_trades.csv` and `out/h8_trades.csv`.

Rules. **H7**: buy 100 shares at the official close of the session before each scheduled FOMC statement released at 2:00 pm (2013-03-20 on), sell at the close of the 13:58 bar on the statement day; $0.01 a share in the auction + $0.005 at the exit ($1.50 a trade at 1×, $3.00 at 2×); a dividend whose ex-date is the statement day is paid. **H8**: buy 100 shares at the official close of the second-to-last session of each month, sell at the official close of the third session of the next month; $0.01 a share each way ($2.00 at 1×, $4.00 at 2×); dividends with ex-dates after entry through exit are paid. Official close: ThetaData EOD before 2025-10-13, Unusual Whales' daily bar from it. Interval: the 20-session moving-block bootstrap over every calendar session of the name's span (sessions with no trade contribute no trade), 2,000 draws, seed 20261023 (`audit_lib.block_draws`, rng seed + 7919 × 20), the same draws for 1× and 2×. Pass per name: mean at 1× > 0 and the 95 % interval clear of zero. Bonferroni: m = 13 (8 ledger rows with H7, H8, H9 + 5 pre-ledger failures), α = 0.05 ÷ (2 × 13) = 0.1923 %.

## H7 — pre-FOMC drift (close before the statement → 13:59 on the statement day)

| name | span | trades | mean $ a trade, 1× [95 % block-20] | verdict | mean $ a trade, 2× [95 % block-20] | at 2× | 1× at the Bonferroni level (m = 13) | EDGE | win rate 1× | median 1× | worst / best 1× | total 1× |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 2017-02-01 → 2026-09-16 | 77 | +70.43 [+14.64, +129.31] | **PASS** | +68.93 [+13.14, +127.81] | clear of zero | [-15.91, +164.24] | no | 55.8 % | +15.50 | -620 / +823 | +5,423 |
| QQQ | 2013-03-20 → 2026-09-16 | 108 | +69.59 [+23.10, +122.14] | **PASS** | +68.09 [+21.60, +120.64] | clear of zero | [+6.96, +155.95] | yes | 61.1 % | +17.50 | -542 / +1,161 | +7,516 |

**SPY: PASS.** **QQQ: PASS — and an EDGE at the Bonferroni level.**

Descriptive (no verdict):

| name | gross a trade | dividend a trade | costs 1× / 2× | night (close → 09:30 open) | day (09:30 open → 13:58 close) | flagged closes out: trades, mean 1× [95 %] |
|---|---|---|---|---|---|---|
| SPY | +71.93 | +0.00 | −1.50 / −3.00 | +74.36 | -2.43 | 77, +70.43 [+14.64, +129.31] |
| QQQ | +71.09 | +0.00 | −1.50 / −3.00 | +72.97 | -1.88 | 107, +70.16 [+23.10, +123.08] |

SPY: flagged trades removed in the sensitivity: none; trades with a dividend term: none.

QQQ: flagged trades removed in the sensitivity: 2018-08-01; trades with a dividend term: none.

Before and from Song's March 2016 break (descriptive):

| name | statements | trades | mean 1× [95 % block-20] | win rate |
|---|---|---|---|---|
| SPY | from 2016-03-16 | 77 | +70.43 [+14.64, +129.31] | 55.8 % |
| QQQ | to 2016-01-27 | 24 | -3.00 [-20.84, +14.56] | 50.0 % |
| QQQ | from 2016-03-16 | 84 | +90.33 [+31.40, +155.72] | 64.3 % |

Per calendar year (descriptive):

| year | SPY trades | SPY mean 1× | SPY mean 2× | SPY win | QQQ trades | QQQ mean 1× | QQQ mean 2× | QQQ win |
|---|---|---|---|---|---|---|---|---|
| 2013 | — | — | — | — | 7 | -9.93 | -11.43 | 43 % |
| 2014 | — | — | — | — | 8 | -3.44 | -4.94 | 50 % |
| 2015 | — | — | — | — | 8 | +12.57 | +11.07 | 62 % |
| 2016 | — | — | — | — | 8 | -20.75 | -22.25 | 62 % |
| 2017 | 8 | +0.50 | -1.00 | 38 % | 8 | -4.56 | -6.06 | 62 % |
| 2018 | 8 | +43.94 | +42.44 | 62 % | 8 | +38.19 | +36.69 | 75 % |
| 2019 | 8 | -4.65 | -6.15 | 50 % | 8 | +30.71 | +29.21 | 50 % |
| 2020 | 7 | +285.20 | +283.70 | 86 % | 7 | +273.00 | +271.50 | 86 % |
| 2021 | 8 | -100.59 | -102.09 | 12 % | 8 | -109.81 | -111.31 | 38 % |
| 2022 | 8 | +332.50 | +331.00 | 88 % | 8 | +399.29 | +397.79 | 88 % |
| 2023 | 8 | +30.82 | +29.32 | 62 % | 8 | +51.19 | +49.69 | 62 % |
| 2024 | 8 | +175.51 | +174.01 | 62 % | 8 | +229.09 | +227.59 | 62 % |
| 2025 | 8 | +45.25 | +43.75 | 62 % | 8 | +20.79 | +19.29 | 50 % |
| 2026 | 6 | -126.53 | -128.03 | 33 % | 6 | +88.00 | +86.50 | 67 % |

SPY listed 77, included 77; excluded: none.

QQQ listed 114, included 108; excluded: 2012-06-20 (statement not released at 2:00 pm (before 2013-03-20)); 2012-08-01 (statement not released at 2:00 pm (before 2013-03-20)); 2012-09-13 (statement not released at 2:00 pm (before 2013-03-20)); 2012-10-24 (statement not released at 2:00 pm (before 2013-03-20)); 2012-12-12 (statement not released at 2:00 pm (before 2013-03-20)); 2013-01-30 (statement not released at 2:00 pm (before 2013-03-20)).

## H8 — turn of the month (close of the second-to-last session → close of the third session of the next month)

| name | span | trades | mean $ a trade, 1× [95 % block-20] | verdict | mean $ a trade, 2× [95 % block-20] | at 2× | 1× at the Bonferroni level (m = 13) | EDGE | win rate 1× | median 1× | worst / best 1× | total 1× |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 2017-01-30 → 2026-09-29 | 117 | +134.00 [-8.68, +283.42] | **FAIL** | +132.00 [-10.68, +281.42] | not clear | [-110.59, +343.94] | no | 60.7 % | +154.00 | -2,464 / +2,808 | +15,677 |
| QQQ | 2012-06-28 → 2026-09-29 | 172 | +110.22 [+0.84, +218.26] | **PASS** | +108.22 [-1.16, +216.26] | not clear | [-50.32, +282.68] | no | 59.3 % | +80.50 | -2,370 / +3,373 | +18,958 |

**SPY: FAIL.** **QQQ: PASS.**

Descriptive (no verdict):

| name | gross a trade | dividend a trade | costs 1× / 2× | flagged closes out: trades, mean 1× [95 %] |
|---|---|---|---|---|
| SPY | +136.00 | +0.00 | −2.00 / −4.00 | 115, +149.60 [+8.51, +300.21] |
| QQQ | +112.22 | +0.00 | −2.00 / −4.00 | 171, +123.84 [+20.21, +230.65] |

SPY: flagged trades removed in the sensitivity: 2018-03-28, 2025-03-28; trades with a dividend term: none.

QQQ: flagged trades removed in the sensitivity: 2024-07-30; trades with a dividend term: none.

Per calendar year (descriptive):

| year | SPY trades | SPY mean 1× | SPY mean 2× | SPY win | QQQ trades | QQQ mean 1× | QQQ mean 2× | QQQ win |
|---|---|---|---|---|---|---|---|---|
| 2012 | — | — | — | — | 7 | +103.62 | +101.62 | 71 % |
| 2013 | — | — | — | — | 12 | +27.51 | +25.51 | 67 % |
| 2014 | — | — | — | — | 12 | -22.33 | -24.33 | 50 % |
| 2015 | — | — | — | — | 12 | -27.50 | -29.50 | 42 % |
| 2016 | — | — | — | — | 12 | +1.67 | -0.33 | 50 % |
| 2017 | 12 | +104.92 | +102.92 | 75 % | 12 | +71.83 | +69.83 | 67 % |
| 2018 | 12 | -59.58 | -61.58 | 58 % | 12 | +23.67 | +21.67 | 58 % |
| 2019 | 12 | +58.62 | +56.62 | 67 % | 12 | +73.50 | +71.50 | 67 % |
| 2020 | 12 | +417.33 | +415.33 | 75 % | 12 | +413.08 | +411.08 | 67 % |
| 2021 | 12 | +1.08 | -0.92 | 42 % | 12 | -121.75 | -123.75 | 50 % |
| 2022 | 12 | -69.50 | -71.50 | 50 % | 12 | -63.33 | -65.33 | 50 % |
| 2023 | 12 | +174.25 | +172.25 | 58 % | 12 | +150.50 | +148.50 | 58 % |
| 2024 | 12 | -61.58 | -63.58 | 58 % | 12 | +90.67 | +88.67 | 58 % |
| 2025 | 12 | +79.08 | +77.08 | 58 % | 12 | +164.25 | +162.25 | 67 % |
| 2026 | 9 | +882.44 | +880.44 | 67 % | 9 | +983.56 | +981.56 | 78 % |

SPY listed 117, included 117; excluded: none.

QQQ listed 172, included 172; excluded: none.

## Verification

`verify_h7_h8.py` re-derived 60 trades (15 H7 + 15 H8 trades a name, seed 20261025) from the raw files with plain loops and no code shared with the run: 0 differences in 510 fields; rows carrying a P&L while excluded: 0; statement dates on disk the run did not list: 0.

## Reading (descriptive; the verdicts are the tables above)

**H7.** Both names pass at 1× and at 2×: SPY +$70.43 a trade [+14.64, +129.31] on 77 statements, QQQ +$69.59 [+23.10, +122.14] on 108 — about 19 and 21 bp of the position a trade (`out/h7_h8_tails.json`). **QQQ also clears the Bonferroni level at m = 13** (lower end +$6.96; none of the 2,000 draws has a mean at or below zero) **and is an EDGE under QUEUE rule 5; SPY does not** (lower end −$15.91; 15 of 2,000 draws at or below zero). The tail at α = 0.19 % rests on about two draws, so the QQQ call is coarse. SPY and QQQ trade the same nights, so the two passes are not independent evidence. The whole gross is the night: the official close → the 09:30 open averages +$74.36 (SPY) and +$72.97 (QQQ), the 09:30 open → 13:58 −$2.43 and −$1.88 — the shape Song reports for 2016–2023 (only the overnight gap survives). QQQ's 24 statements before March 2016 average −$3.00 [−20.84, +14.56]; the 84 from it +$90.33. The years swing: 2020 and 2022 carry large positive means (+$285 / +$273 and +$333 / +$399 a trade), 2021 is negative in both names and SPY's six 2026 statements average −$126.53. The intervals cleared although the mean (19–21 bp) is below the a-priori minimum detectable effect (35–37 bp): the pre-FOMC trades varied less than the all-session figure assumed. Every FOMC-eve night is also an H9 night; the repository's earlier overnight reads (H1's long legs +$22–27 a trade; the atlas's +4.9 / +6.8 bp, 43 names) are smaller than H7's night piece, so as far as those reads go the pre-FOMC night carries more than the ordinary overnight drift (not a test). No financing is charged (PREREG §2); one night of bill interest is about 1–1.5 bp of the position at 2023–2026 rates and near zero in 2013–2021.

**What a pass does not yet mean (QUEUE rule 6).** H7 is not "an edge that works" until a FORWARD rule (this rule, its N, its pass line) is committed and met. The next scheduled statement is 2026-10-28, whose entry is the 2026-10-27 official close: a forward rule has to be committed before that close is read. At eight statements a year any useful forward N takes years.

**H8.** SPY fails (+$134.00 a trade [−8.68, +283.42], 117 turns). QQQ passes at 1× by the narrowest margin (+$110.22 [+0.84, +218.26], 172 turns) and is not clear of zero at 2× ([−1.16, +216.26]) nor at the Bonferroni level ([−50.32, +282.68]); 49 (QQQ) and 61 (SPY) of the 2,000 draws are at or below zero. The means are about 39 and 31 bp of the position a turn, below the a-priori minimum detectable effect (56–60 bp). The years swing in sign (QQQ negative in 2014, 2015, 2021 and 2022), and the nine 2026 turns (+$882.44 SPY, +$983.56 QQQ a trade) are about half of each total: without them QQQ's other 163 turns average about $62 a trade (arithmetic on the table, not a test). A long-only four-session hold also carries the market's ordinary drift, and the forgone bill interest (6–8 calendar days, 0–10 bp of the position over 2012–2026), which the rule does not charge, is larger than QQQ's 1× margin over zero. H8 is a fail for SPY and a marginal 1×-only pass for QQQ that is not an EDGE.

## Notes on the run (none changes a rule)

- `run_h7_h8.py` was run once for the result. It was re-run afterwards only to add the descriptive tail file (`out/h7_h8_tails.json`: draws at or below zero, means in bp) and to write the verification line and this reading into the report; every re-run left `out/h7_h8_summary.json`, `out/h7_trades.csv` and `out/h8_trades.csv` byte-identical to the first run (sha256 checked).

- Unusual Whales' daily closes equal ThetaData's EOD closes on all 252 sessions where both are on disk from 2025-06 (SPY and QQQ; checked after the run while reading the 2026 trades): the source switch at 2025-10-13 does not change a price.

- No vendor fetch was made for the run (the Fed's calendar pages were read before the prereg). Sessions after 2026-10-22 were not read.

