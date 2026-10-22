# Compass features: the pre-registered study, run as written

**Pre-registration: `PREREG_FEATURES.md`, commit `a2e14e4`, sha256 `840f7671b1f997c9610a3cda9bec0407fb341755eb8b88a3defa5d314cfc62cd`** (committed alone before any result was computed). Code: `run/` in this folder (`fcommon.py` the shared definitions; `daily.py`, `build_0dte.py`, `build_eod.py`, `tiers.py`, `uw_features.py` the inputs and base trades; `gex_check.py`; `screen.py` the comparisons; `x2.py`; `verify_features.py` the plain-loop re-derivation; this file by `write_report.py`). Files read only; no vendor call by the study. Returns are per trade after fees, as a share of the debit (prereg 2.6), shown in percentage points; Δ = mean with − mean without; intervals are the 20-session moving-block bootstrap (audit_lib, 2,000 draws, seed 20261022), percentile 95%, none under 60 sessions.

## Summary

- **The GEX check (section 7): Δ_GEX = -0.0604 implied moves [-0.1327, +0.0354] on 1,470 name-sessions → the GEX features are DROPPED UNTESTED (SD1, SD2, X2).**
- **Screened: 23** (the conservative count of section 6, the GEX features included whether tested or not); computed on the exploration set: 20; **passed the exploration screen: 3** (V1, VN1, X3); **passed the holdout: 3** (V1, VN1, X3).
- V1 on the holdout: Δ +2.61 [+1.76, +3.46], 474,526 / 580,234 trades, 3,586 sessions → **PASS**.
- VN1 on the holdout: Δ +1.18 [+0.50, +2.20], 35,217 / 70,434 trades, 936 sessions → **PASS**.
- X3 on the holdout: Δ +7.78 [+4.14, +10.95], 233,454 / 233,454 trades, 2,340 sessions → **PASS**.
- What the passes mean: each one makes a losing base set lose less; none makes it profitable. On the holdout, mean per trade with → without: V1 -8.43 → -11.03; VN1 -8.87 → -10.04; X3 -9.51 → -17.29. The three that pass are costs and timing (skip wide spreads, take the cheaper venue, sell a same-day long option at 14:00 instead of holding it to 15:58 or settlement); no direction, strike-placement or expiry-choice feature passed the screen, and the GEX family did not pass its gate.
- **Disclosure: the holdout was read twice.** The first read ran on a table in which a join had duplicated base trades (777,571 rows for 580,274 trades; section 6); after the fix (no feature, threshold or rule changed) it was run once more and that second read carries the verdicts above. The first read, for the record: V1 Δ +1.77 [+1.62, +3.44] → pass; VN1 Δ -5.77 [-5.86, +2.60] → fail; X3 Δ +17.77 [+4.16, +18.51] → pass. VN1 failed on the duplicated table and passes on the corrected one; weigh it accordingly.
- Expected false passes at the screen under the null: 23 × 0.025 = 0.58; both stages ≈ 0.014 (section 6).

## 1. The base set (descriptive; no verdict)

Exploration sessions 2012-06-01 → 2026-09-30 (2,695 in the span, held-out months out). Mean return per trade after fees with its block-20 interval:

| slice | sessions traded | trades | mean per trade | 20-session block 95% |
|---|---|---|---|---|
| all | 2,596 | 651,232 | -13.35 | [-16.29, -10.36] |
| eb=0DTE | 964 | 376,177 | -19.15 | [-23.06, -15.35] |
| eb=1-7 | 655 | 66,031 | -5.22 | [-13.66, +3.71] |
| eb=8-30 | 2,487 | 108,548 | -5.61 | [-8.32, -2.59] |
| eb=31-60 | 2,300 | 100,476 | -5.35 | [-8.48, -1.86] |
| tier=1 | 2,562 | 284,976 | -10.92 | [-14.48, -6.69] |
| tier=2 | 2,015 | 124,323 | -12.05 | [-15.99, -8.56] |
| tier=3 | 1,059 | 73,603 | -8.62 | [-13.55, -2.97] |
| tier=U | 550 | 168,330 | -20.50 | [-25.99, -14.62] |
| settle=physical | 2,592 | 544,644 | -14.58 | [-17.42, -11.70] |
| settle=cash | 761 | 106,588 | -7.05 | [-12.59, -1.17] |
| name=AAPL | 885 | 29,842 | -12.36 | [-19.87, -4.32] |
| name=AMD | 882 | 36,991 | -16.15 | [-23.64, -10.06] |
| name=AMZN | 885 | 47,527 | -18.38 | [-23.43, -12.40] |
| name=GOOGL | 885 | 44,574 | -19.02 | [-24.26, -13.60] |
| name=INTC | 885 | 31,765 | -14.98 | [-23.51, -6.70] |
| name=IWM | 2,561 | 77,925 | -12.79 | [-16.26, -8.25] |
| name=META | 885 | 40,101 | -16.00 | [-22.06, -11.04] |
| name=MSFT | 885 | 34,126 | -17.23 | [-23.36, -10.58] |
| name=NVDA | 885 | 39,698 | -14.18 | [-20.87, -7.02] |
| name=SPXW | 761 | 106,588 | -7.05 | [-12.59, -1.17] |
| name=SPY | 2,583 | 114,064 | -9.41 | [-12.98, -5.16] |
| name=TSLA | 885 | 48,031 | -19.07 | [-24.90, -12.42] |

Trades formed and not formed, by name (exploration split):

| kind | name | formed | not formed (reason: count) | sold at $0 in the money |
|---|---|---|---|---|
| 0dte | AAPL | 14,522 | contract: no standing quote in the bucket: 38,418; entry: no standing ATM pair: 10 | 0 |
| 0dte | AMD | 19,689 | contract: no standing quote in the bucket: 28,821; entry: no standing ATM pair: 102 | 0 |
| 0dte | AMZN | 31,108 | contract: no standing quote in the bucket: 21,912; entry: no standing ATM pair: 2 | 0 |
| 0dte | GOOGL | 28,275 | contract: no standing quote in the bucket: 24,535; entry: no standing ATM pair: 10 | 0 |
| 0dte | INTC | 15,343 | contract: no standing quote in the bucket: 33,107; entry: no standing ATM pair: 108 | 0 |
| 0dte | IWM | 26,415 | contract: no standing quote in the bucket: 31,695 | 0 |
| 0dte | META | 22,233 | contract: no standing quote in the bucket: 30,627; entry: no standing ATM pair: 5 | 17 |
| 0dte | MSFT | 16,720 | contract: no standing quote in the bucket: 36,060; entry: no standing ATM pair: 13 | 9 |
| 0dte | NVDA | 22,186 | contract: no standing quote in the bucket: 30,444; entry: no standing ATM pair: 2 | 4 |
| 0dte | SPXW | 89,048 | contract: no standing quote in the bucket: 9,882 | 0 |
| 0dte | SPY | 60,478 | contract: no standing quote in the bucket: 27,532 | 0 |
| 0dte | TSLA | 30,160 | contract: no standing quote in the bucket: 22,730; entry: no standing ATM pair: 2 | 0 |
| eod | AAPL | 15,320 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 2,039; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 437; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 563 | 0 |
| eod | AMD | 17,302 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 4; 1-7: no standing quote in the bucket: 500; 31-60: expires on a half day: 10; 31-60: no EOD row for the contract at the exit session: 40; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 123; 8-30: expires on a half day: 10; 8-30: no EOD row for the contract at the exit session: 40; 8-30: no standing quote in the bucket: 62 | 0 |
| eod | AMZN | 16,419 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 1,443; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 133; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 224 | 0 |
| eod | GOOGL | 16,299 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 1,448; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 226; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 266 | 0 |
| eod | INTC | 16,422 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 4; 1-7: no standing quote in the bucket: 1,439; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 210; 8-30: expires on a half day: 10; 8-30: no standing ATM pair: 2; 8-30: no standing quote in the bucket: 184 | 0 |
| eod | IWM | 51,510 | 1-7: expires on a half day: 46; 1-7: no expiry-day chain on disk: 19,529; 1-7: no listed expiry in the bucket: 11; 1-7: no standing quote in the bucket: 1,898; 31-60: expires on a half day: 57; 31-60: no listed expiry in the bucket: 18; 31-60: no standing quote in the bucket: 120; 8-30: expires on a half day: 50; 8-30: no listed expiry in the bucket: 13; 8-30: no standing quote in the bucket: 217 | 0 |
| eod | META | 17,868 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 240; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 50; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 7 | 0 |
| eod | MSFT | 17,406 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 707; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 14; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 44 | 0 |
| eod | NVDA | 17,512 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 564; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 70; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 38 | 5 |
| eod | SPXW | 17,540 | 1-7: expires on a half day: 2; 1-7: no standing ATM pair: 1; 31-60: expires on a half day: 12; 31-60: no EOD row for the contract at the exit session: 115; 31-60: no listed expiry in the bucket: 8; 31-60: no standing ATM pair: 2; 31-60: no standing quote in the bucket: 12; 8-30: expires on a half day: 5; 8-30: no EOD row for the contract at the exit session: 113; 8-30: no standing quote in the bucket: 1 | 0 |
| eod | SPY | 53,586 | 1-7: expires on a half day: 38; 1-7: no expiry-day chain on disk: 18,185; 1-7: no listed expiry in the bucket: 4; 1-7: no standing quote in the bucket: 1,183; 31-60: expires on a half day: 57; 31-60: no listed expiry in the bucket: 18; 31-60: no standing ATM pair: 4; 31-60: no standing quote in the bucket: 108; 8-30: expires on a half day: 33; 8-30: no listed expiry in the bucket: 13; 8-30: no standing quote in the bucket: 506 | 0 |
| eod | TSLA | 17,871 | 1-7: expires on a half day: 10; 1-7: no listed expiry in the bucket: 3; 1-7: no standing quote in the bucket: 264; 31-60: expires on a half day: 10; 31-60: no listed expiry in the bucket: 8; 31-60: no standing quote in the bucket: 11; 8-30: expires on a half day: 10; 8-30: no standing quote in the bucket: 10 | 0 |

## 2. The GEX check (prereg section 7)

Name-sessions: 1,470 (negative GEX 898, positive 572); left out: IWM: GEX exactly 0 1; SPXW: GEX exactly 0 3; SPXW: no 09:45 GEX row 1; SPY: GEX exactly 0 3; SPY: no 09:45 GEX row 1. Realized move = |official close − P| ÷ IM.

| rows | name-sessions neg / pos | mean neg | mean pos | Δ_GEX | 20-session block 95% | sessions | n_eff (block) | n_eff (acf) |
|---|---|---|---|---|---|---|---|---|
| **pooled (the gate)** | 898 / 572 | 0.9085 | 0.9690 | -0.0604 | [-0.1327, +0.0354] | 516 | 617 | 374 |
| name SPY | 336 / 176 | 0.8842 | 0.9779 | -0.0938 | [-0.2092, +0.0528] | 516 | 627 | 176 |
| name IWM | 383 / 63 | 0.8910 | 0.9691 | -0.0781 | [-0.2638, +0.1353] | 516 | 485 | 63 |
| name SPXW | 179 / 333 | 0.9918 | 0.9642 | +0.0276 | [-0.1050, +0.1913] | 516 | 485 | 333 |
| tier 1 | 841 / 468 | 0.8924 | 0.9567 | -0.0643 | [-0.1401, +0.0352] | 516 | 625 | 340 |
| tier U | 57 / 104 | 1.1464 | 1.0241 | +0.1223 | [-0.1191, +0.5356] | 516 | 392 | 104 |

**Gate: FAILED — SD1, SD2 and X2 are dropped untested (prereg section 7).** The per-name and per-tier rows do not change the gate.

## 3. The features, in the prereg's order

| id | family | span | sessions | trades with / without | exploration Δ [95%] | n_eff (block) | holdout Δ [95%] | verdict |
|---|---|---|---|---|---|---|---|---|
| V1 | veto | 2012-06-01 → 2026-09-30 | 2,695 | 538,468 / 651,232 | +2.46 [+1.64, +3.41] | 1,775 | +2.61 [+1.76, +3.46] (n_eff 3,373) | **PASS** |
| V2 | veto | 2023-11-21 → 2026-09-30 | 527 | 139,912 / 174,213 | -0.59 [-2.28, +0.96] | 694 | — | FAIL (screen) |
| V3 | veto | 2012-06-01 → 2026-09-30 | 2,695 | 429,615 / 520,282 | -0.52 [-1.14, +0.09] | 3,285 | — | FAIL (screen) |
| V4 | veto | 2017-07-07 → 2026-09-30 | 1,762 | 315,087 / 352,655 | -1.82 [-2.75, -1.04] | 463 | — | FAIL (screen) |
| V5 | veto | 2022-01-03 → 2026-09-30 | 829 | 268,104 / 486,126 | -3.10 [-6.13, -0.32] | 791 | — | FAIL (screen) |
| V6 | veto | 2013-06-07 → 2026-09-22 | 2,480 | 424,349 / 449,028 | -0.40 [-1.36, +0.33] | 2,360 | — | FAIL (screen) |
| VN1 | venue | 2022-11-01 → 2026-09-30 | 685 | 74,405 / 148,810 | +1.69 [+0.99, +2.26] | 651 | +1.18 [+0.50, +2.20] (n_eff 607) | **PASS** |
| ES1 | expiry | 2012-06-01 → 2026-09-23 | 2,690 | 104,061 / 267,995 | -1.41 [-3.76, +0.13] | 1,275 | — | FAIL (screen) |
| ES2 | expiry | 2017-03-01 → 2026-09-23 | 1,823 | 88,127 / 240,455 | -0.67 [-2.71, +1.42] | 985 | — | FAIL (screen) |
| ES3 | strike | 2017-03-01 → 2026-09-30 | 1,828 | 135,338 / 620,755 | -6.35 [-8.31, -4.69] | 1,987 | — | FAIL (screen) |
| ES4 | strike | 2012-06-01 → 2026-09-30 | 2,695 | 196,298 / 651,228 | -5.73 [-6.99, -4.54] | 2,288 | — | FAIL (screen) |
| SD1 | strike | — → — | — | — / — | dropped by the GEX check (untested) | — | — | dropped by the GEX check |
| SD2 | strike | — → — | — | — / — | dropped by the GEX check (untested) | — | — | dropped by the GEX check |
| X1 | exit | 2017-01-03 → 2026-09-30 | 1,848 | 621,255 / 621,255 | -1.06 [-3.18, +0.97] | 2,285 | — | FAIL (screen) |
| X2 | exit | — → — | — | — / — | dropped by the GEX check (untested) | — | — | dropped by the GEX check |
| X3 | exit | 2017-07-07 → 2026-09-30 | 1,762 | 291,090 / 291,090 | +5.75 [+1.83, +9.44] | 2,189 | +7.78 [+4.14, +10.95] (n_eff 3,405) | **PASS** |
| D1 | direction | 2023-11-21 → 2026-09-30 | 527 | 88,564 / 177,245 | -0.40 [-4.29, +2.73] | 765 | — | FAIL (screen) |
| D2 | direction | 2023-11-21 → 2026-09-30 | 527 | 68,085 / 136,216 | +0.52 [-3.47, +4.25] | 498 | — | FAIL (screen) |
| D3 | direction | 2024-09-03 → 2026-09-30 | 374 | 38,672 / 77,399 | -4.35 [-9.43, -0.27] | 563 | — | FAIL (screen) |
| D4 | direction | 2023-11-21 → 2026-09-30 | 527 | 88,606 / 177,245 | -3.34 [-10.11, +4.18] | 526 | — | FAIL (screen) |
| D5 | direction | 2023-11-21 → 2026-09-30 | 527 | 51,044 / 102,020 | +2.93 [-3.56, +9.12] | 383 | — | FAIL (screen) |
| D6 | direction | 2017-07-07 → 2026-09-30 | 1,762 | 98,952 / 197,857 | +1.13 [-4.82, +8.08] | 1,709 | — | FAIL (screen) |
| D7 | direction | 2017-01-04 → 2026-09-30 | 1,847 | 165,197 / 330,543 | -1.47 [-5.39, +3.10] | 1,975 | — | FAIL (screen) |

Per feature: the decision, the source, the arms, and the rows per tier, settlement type and expiry bucket (descriptive).

### V1 — spread: veto when (ask − bid) ÷ mid at the entry quote > 10%

Family: veto. Source: ThetaData chain / EOD.
Span 2012-06-01 → 2026-09-30, 2,695 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 538,468 trades on 2,594 sessions, mean -10.89; without: 651,232 trades on 2,596 sessions, mean -13.35. **Δ +2.46 [+1.64, +3.41]**, n_eff 1,775 (block ratio) / 2,062 (acf). Screen: **PASS → holdout**.

Holdout (once): 474,526 / 580,234 trades, 3,586 sessions (2012-06-01 → 2026-10-21), Δ +2.61 [+1.76, +3.46], n_eff 3,373 / 2,578 → **PASS**.
- holdout part, held-out tickers, all months (descriptive): Δ +3.61 [+2.51, +4.81], 225,757 / 287,011 trades.
- holdout part, exploration tickers, held-out months (descriptive): Δ +1.57 [+0.42, +2.62], 248,769 / 293,223 trades.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 273,430 / 284,976 | -10.53 | -10.92 | +0.39 | [+0.12, +0.65] |
| tier 2 | 104,006 / 124,323 | -10.75 | -12.05 | +1.30 | [+0.17, +2.29] |
| tier 3 | 53,369 / 73,603 | -4.74 | -8.62 | +3.87 | [+2.35, +5.36] |
| tier U | 107,663 / 168,330 | -15.00 | -20.50 | +5.50 | [+2.69, +8.44] |
| settlement physical | 434,045 / 544,644 | -11.86 | -14.58 | +2.73 | [+1.80, +3.76] |
| settlement cash | 104,423 / 106,588 | -6.87 | -7.05 | +0.17 | [-0.18, +0.50] |
| bucket 0DTE | 297,027 / 376,177 | -16.24 | -19.15 | +2.91 | [+1.52, +4.47] |
| bucket 1-7 | 58,472 / 66,031 | -3.76 | -5.22 | +1.47 | [+0.27, +2.73] |
| bucket 8-30 | 97,214 / 108,548 | -4.89 | -5.61 | +0.72 | [+0.20, +1.16] |
| bucket 31-60 | 85,755 / 100,476 | -4.03 | -5.35 | +1.32 | [+0.71, +1.84] |
| holdout tier 1 | 272,862 / 282,901 | -9.70 | -10.02 | +0.32 | [+0.06, +0.50] |
| holdout tier 2 | 86,928 / 104,010 | -4.49 | -5.29 | +0.80 | [-0.34, +1.67] |
| holdout tier 3 | 84,102 / 128,110 | -3.95 | -9.66 | +5.71 | [+3.98, +7.47] |
| holdout tier U | 30,634 / 65,213 | -20.52 | -27.31 | +6.79 | [+1.79, +11.60] |
| holdout settlement physical | 425,047 / 529,788 | -8.27 | -11.17 | +2.90 | [+2.00, +3.81] |
| holdout settlement cash | 49,479 / 50,446 | -9.79 | -9.60 | -0.19 | [-0.61, +0.15] |

### V2 — open interest: veto when the contract's OI published the morning of the entry session < 500

Family: veto. Source: UW option-contracts?date=D.
Span 2023-11-21 → 2026-09-30, 527 sessions; names IWM, SPXW, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 139,912 trades on 527 sessions, mean -11.56; without: 174,213 trades on 527 sessions, mean -10.97. **Δ -0.59 [-2.28, +0.96]**, n_eff 694 (block ratio) / 695 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 123,098 / 151,288 | -13.80 | -13.09 | -0.71 | [-2.16, +0.55] |
| tier U | 16,814 / 22,925 | +4.84 | +3.00 | +1.83 | [-5.29, +8.62] |
| settlement physical | 87,462 / 100,740 | -14.36 | -13.90 | -0.46 | [-1.55, +0.61] |
| settlement cash | 52,450 / 73,473 | -6.89 | -6.95 | +0.06 | [-3.40, +3.03] |
| bucket 0DTE | 119,364 / 135,818 | -11.87 | -11.70 | -0.17 | [-2.14, +1.52] |
| bucket 1-7 | 9,521 / 13,978 | -18.14 | -14.80 | -3.35 | [-6.76, +0.64] |
| bucket 8-30 | 7,376 / 13,542 | -3.37 | -6.13 | +2.77 | [+0.06, +5.65] |
| bucket 31-60 | 3,651 / 10,875 | -0.79 | -2.93 | +2.14 | [-2.10, +4.88] |

### V3 — volume: veto when the contract's volume on the last completed session < 100

Family: veto. Source: ThetaData option EOD volume.
Span 2012-06-01 → 2026-09-30, 2,695 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 429,615 trades on 2,582 sessions, mean -10.52; without: 520,282 trades on 2,583 sessions, mean -10.00. **Δ -0.52 [-1.14, +0.09]**, n_eff 3,285 (block ratio) / 2,154 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 247,174 / 283,255 | -11.42 | -10.88 | -0.54 | [-1.18, -0.02] |
| tier 2 | 94,716 / 124,280 | -13.40 | -12.03 | -1.36 | [-2.39, -0.49] |
| tier 3 | 54,443 / 73,587 | -9.16 | -8.60 | -0.56 | [-2.09, +0.96] |
| tier U | 33,282 / 39,160 | +2.12 | +0.17 | +1.95 | [+0.04, +3.71] |
| settlement physical | 349,341 / 425,703 | -11.48 | -10.77 | -0.71 | [-1.28, -0.13] |
| settlement cash | 80,274 / 94,579 | -6.34 | -6.52 | +0.17 | [-1.31, +1.38] |
| bucket 0DTE | 237,104 / 245,227 | -15.12 | -15.13 | +0.01 | [-0.50, +0.45] |
| bucket 1-7 | 65,061 / 66,031 | -5.30 | -5.22 | -0.08 | [-0.30, +0.13] |
| bucket 8-30 | 78,169 / 108,548 | -5.09 | -5.61 | +0.52 | [-0.18, +1.14] |
| bucket 31-60 | 49,281 / 100,476 | -3.88 | -5.35 | +1.47 | [-0.41, +3.15] |

### V4 — earnings: veto when a release falls between the last close before entry and the expiry's 16:00

Family: veto. Source: UW earnings calendar.
Span 2017-07-07 → 2026-09-30, 1,762 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, META, MSFT, NVDA, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 315,087 trades on 886 sessions, mean -18.47; without: 352,655 trades on 886 sessions, mean -16.65. **Δ -1.82 [-2.75, -1.04]**, n_eff 463 (block ratio) / 307 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 53,853 / 64,972 | -10.47 | -8.72 | -1.75 | [-3.49, -0.25] |
| tier 2 | 85,337 / 97,878 | -15.31 | -13.32 | -2.00 | [-3.76, -0.76] |
| tier 3 | 50,902 / 64,490 | -11.38 | -9.70 | -1.68 | [-5.03, +0.99] |
| tier U | 124,995 / 125,315 | -26.96 | -26.95 | -0.01 | [-0.07, +0.04] |
| settlement physical | 315,087 / 352,655 | -18.47 | -16.65 | -1.82 | [-2.75, -1.04] |
| bucket 0DTE | 200,236 / 200,236 | -26.26 | -26.26 | +0.00 | [+0.00, +0.00] |
| bucket 1-7 | 45,835 / 49,087 | -2.64 | -1.45 | -1.19 | [-3.13, +0.43] |
| bucket 8-30 | 41,156 / 53,929 | -5.59 | -4.77 | -0.82 | [-2.63, +0.89] |
| bucket 31-60 | 27,860 / 49,403 | -7.54 | -5.78 | -1.76 | [-5.32, +1.63] |

### V5 — macro: the same window for an FOMC decision, CPI or NFP

Family: veto. Source: data/macro_events_2022_2027.json.
Span 2022-01-03 → 2026-09-30, 829 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 268,104 trades on 680 sessions, mean -14.21; without: 486,126 trades on 825 sessions, mean -11.11. **Δ -3.10 [-6.13, -0.32]**, n_eff 791 (block ratio) / 786 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 155,998 / 252,225 | -14.15 | -11.67 | -2.48 | [-5.89, +0.70] |
| tier 2 | 41,189 / 101,204 | -20.68 | -12.95 | -7.73 | [-13.83, -4.14] |
| tier 3 | 22,035 / 64,490 | -20.73 | -9.70 | -11.02 | [-16.59, -5.50] |
| tier U | 48,882 / 68,207 | -5.99 | -7.60 | +1.60 | [-6.31, +7.78] |
| settlement physical | 186,221 / 379,538 | -17.33 | -12.25 | -5.08 | [-8.41, -2.27] |
| settlement cash | 81,883 / 106,588 | -7.12 | -7.05 | -0.07 | [-3.72, +2.91] |
| bucket 0DTE | 231,530 / 276,890 | -14.52 | -15.48 | +0.96 | [-2.49, +3.52] |
| bucket 1-7 | 34,942 / 66,031 | -12.02 | -5.22 | -6.80 | [-14.48, +0.50] |
| bucket 8-30 | 1,632 / 74,894 | -17.28 | -5.32 | -11.95 | [-19.91, -4.13] |
| bucket 31-60 | 0 / 68,311 | — | — | — | — |

### V6 — IV rank: veto when IV rank ≥ 0.80

Family: veto. Source: ThetaData option EOD.
Span 2013-06-07 → 2026-09-22, 2,480 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 424,349 trades on 2,336 sessions, mean -10.90; without: 449,028 trades on 2,379 sessions, mean -10.50. **Δ -0.40 [-1.36, +0.33]**, n_eff 2,360 (block ratio) / 2,093 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 249,685 / 258,076 | -12.20 | -11.41 | -0.79 | [-2.62, +0.23] |
| tier 2 | 96,894 / 106,578 | -11.68 | -11.73 | +0.05 | [-1.32, +1.45] |
| tier 3 | 54,308 / 60,562 | -9.05 | -9.24 | +0.19 | [-1.31, +1.67] |
| tier U | 23,462 / 23,812 | +1.84 | +1.59 | +0.25 | [-0.10, +0.92] |
| settlement physical | 350,647 / 374,206 | -11.50 | -11.14 | -0.35 | [-1.13, +0.32] |
| settlement cash | 73,702 / 74,822 | -8.06 | -7.30 | -0.76 | [-3.06, +0.44] |
| bucket 0DTE | 204,701 / 215,712 | -16.94 | -16.39 | -0.55 | [-2.85, +0.85] |
| bucket 1-7 | 50,907 / 54,663 | -7.49 | -6.76 | -0.73 | [-2.21, +0.63] |
| bucket 8-30 | 87,782 / 92,937 | -4.82 | -4.64 | -0.18 | [-0.62, +0.23] |
| bucket 31-60 | 80,959 / 85,716 | -4.37 | -4.43 | +0.06 | [-0.69, +0.71] |

### VN1 — entry cost share: keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid

Family: venue. Source: ThetaData chains / EOD.
Span 2022-11-01 → 2026-09-30, 685 sessions; names SPXW, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 74,405 trades on 685 sessions, mean -7.98; without: 148,810 trades on 685 sessions, mean -9.66. **Δ +1.69 [+0.99, +2.26]**, n_eff 651 (block ratio) / 651 (acf). Screen: **PASS → holdout**.

Holdout (once): 35,217 / 70,434 trades, 936 sessions (2023-01-18 → 2026-10-21), Δ +1.18 [+0.50, +2.20], n_eff 607 / 274 → **PASS**.
- holdout part, exploration tickers, held-out months (descriptive): Δ +1.18 [+0.50, +2.20], 35,217 / 70,434 trades.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 58,932 / 124,276 | -11.28 | -11.89 | +0.61 | [-1.43, +2.16] |
| tier U | 15,473 / 24,534 | +4.59 | +1.60 | +2.98 | [-1.69, +7.85] |
| settlement physical | 26,164 / 74,405 | -10.10 | -11.71 | +1.61 | [-2.38, +5.67] |
| settlement cash | 48,241 / 74,405 | -6.83 | -7.62 | +0.79 | [-1.80, +3.21] |
| bucket 0DTE | 57,013 / 114,026 | -7.64 | -9.62 | +1.97 | [+1.04, +2.73] |
| bucket 1-7 | 6,265 / 12,530 | -14.65 | -14.57 | -0.09 | [-0.74, +0.59] |
| bucket 8-30 | 5,876 / 11,752 | -6.84 | -8.25 | +1.41 | [+1.07, +1.77] |
| bucket 31-60 | 5,251 / 10,502 | -4.94 | -5.93 | +0.99 | [+0.71, +1.29] |
| holdout tier 1 | 35,132 / 69,808 | -8.87 | -10.00 | +1.12 | [+0.42, +2.13] |
| holdout tier U | 85 / 626 | -6.95 | -15.19 | +8.25 | [-17.35, +45.47] |
| holdout settlement physical | 12,699 / 35,217 | -4.05 | -11.72 | +7.66 | [+2.73, +13.13] |
| holdout settlement cash | 22,518 / 35,217 | -11.58 | -8.37 | -3.21 | [-6.66, +0.21] |

### ES1 — term structure: keep the multi-day expiry bucket with the lowest at-the-money IV

Family: expiry. Source: ThetaData EOD.
Span 2012-06-01 → 2026-09-23, 2,690 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 1-7, 31-60, 8-30. With: 104,061 trades on 2,330 sessions, mean -6.83; without: 267,995 trades on 2,330 sessions, mean -5.41. **Δ -1.41 [-3.76, +0.13]**, n_eff 1,275 (block ratio) / 1,009 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 46,402 / 118,038 | -8.08 | -5.77 | -2.31 | [-4.77, -0.44] |
| tier 2 | 32,846 / 83,622 | -7.36 | -6.37 | -0.99 | [-4.63, +1.22] |
| tier 3 | 20,441 / 54,781 | -1.92 | -3.33 | +1.41 | [-1.08, +3.89] |
| tier U | 4,372 / 11,554 | -12.45 | -4.70 | -7.76 | [-15.22, +2.27] |
| settlement physical | 98,028 / 250,775 | -6.29 | -5.09 | -1.20 | [-3.40, +0.28] |
| settlement cash | 6,033 / 17,220 | -15.46 | -10.00 | -5.46 | [-11.79, -0.06] |
| bucket 1-7 | 23,163 / 63,346 | -13.83 | -5.19 | -8.64 | [-20.20, -1.35] |
| bucket 8-30 | 47,729 / 105,153 | -4.98 | -5.56 | +0.58 | [-1.46, +2.44] |
| bucket 31-60 | 33,169 / 99,496 | -4.59 | -5.39 | +0.80 | [-1.81, +3.52] |

### ES2 — implied vs realized: keep the expiry bucket with the lowest IM ÷ RM

Family: expiry. Source: ThetaData EOD and bars.
Span 2017-03-01 → 2026-09-23, 1,823 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 1-7, 31-60, 8-30. With: 88,127 trades on 1,632 sessions, mean -5.52; without: 240,455 trades on 1,632 sessions, mean -4.85. **Δ -0.67 [-2.71, +1.42]**, n_eff 985 (block ratio) / 769 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 39,240 / 104,339 | -7.07 | -5.24 | -1.83 | [-4.56, +0.54] |
| tier 2 | 26,598 / 72,769 | -5.13 | -5.82 | +0.69 | [-1.63, +4.19] |
| tier 3 | 18,375 / 52,629 | -2.37 | -2.99 | +0.62 | [-3.45, +4.36] |
| tier U | 3,914 / 10,718 | -7.42 | -3.55 | -3.86 | [-11.26, +8.10] |
| settlement physical | 82,093 / 223,235 | -4.93 | -4.45 | -0.48 | [-2.48, +1.61] |
| settlement cash | 6,034 / 17,220 | -13.50 | -10.00 | -3.50 | [-8.94, +1.67] |
| bucket 1-7 | 36,871 / 63,346 | -7.59 | -5.19 | -2.40 | [-7.93, +4.27] |
| bucket 8-30 | 28,122 / 91,479 | -2.78 | -4.95 | +2.17 | [-1.25, +5.42] |
| bucket 31-60 | 23,134 / 85,630 | -5.54 | -4.49 | -1.05 | [-5.29, +2.96] |

### ES3 — distance: keep the strike bucket containing x_RM = RM ÷ IM

Family: strike. Source: ThetaData chains / EOD and bars.
Span 2017-03-01 → 2026-09-30, 1,828 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 135,338 trades on 1,790 sessions, mean -19.84; without: 620,755 trades on 1,790 sessions, mean -13.48. **Δ -6.35 [-8.31, -4.69]**, n_eff 1,987 (block ratio) / 1,720 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 58,760 / 270,143 | -16.72 | -11.00 | -5.72 | [-8.25, -2.81] |
| tier 2 | 24,245 / 112,476 | -17.53 | -12.36 | -5.17 | [-8.34, -2.87] |
| tier 3 | 15,138 / 71,381 | -10.05 | -8.51 | -1.54 | [-5.17, +2.57] |
| tier U | 37,195 / 166,755 | -30.25 | -20.38 | -9.87 | [-12.86, -6.93] |
| settlement physical | 112,939 / 514,167 | -21.98 | -14.82 | -7.16 | [-8.92, -5.70] |
| settlement cash | 22,399 / 106,588 | -9.02 | -7.05 | -1.97 | [-6.76, +2.75] |
| bucket 0DTE | 85,270 / 375,438 | -27.95 | -19.09 | -8.86 | [-11.51, -6.52] |
| bucket 1-7 | 13,942 / 66,031 | -7.65 | -5.22 | -2.43 | [-6.14, +2.04] |
| bucket 8-30 | 18,845 / 93,276 | -5.76 | -5.05 | -0.71 | [-2.43, +1.26] |
| bucket 31-60 | 17,281 / 86,010 | -4.96 | -4.49 | -0.47 | [-2.24, +1.51] |

### ES4 — delta: keep the strike bucket whose contract's |delta| is nearest 0.30

Family: strike. Source: ThetaData chains / EOD.
Span 2012-06-01 → 2026-09-30, 2,695 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 196,298 trades on 2,596 sessions, mean -19.08; without: 651,228 trades on 2,596 sessions, mean -13.35. **Δ -5.73 [-6.99, -4.54]**, n_eff 2,288 (block ratio) / 2,437 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 77,045 / 284,976 | -13.93 | -10.92 | -3.01 | [-4.10, -1.67] |
| tier 2 | 37,050 / 124,323 | -17.04 | -12.05 | -4.99 | [-7.41, -2.78] |
| tier 3 | 22,208 / 73,601 | -13.99 | -8.62 | -5.37 | [-8.44, -1.95] |
| tier U | 59,995 / 168,328 | -28.85 | -20.50 | -8.35 | [-10.34, -6.45] |
| settlement physical | 173,000 / 544,640 | -20.54 | -14.58 | -5.96 | [-7.34, -4.69] |
| settlement cash | 23,298 / 106,588 | -8.24 | -7.05 | -1.19 | [-2.45, +0.06] |
| bucket 0DTE | 138,944 / 376,174 | -24.64 | -19.15 | -5.49 | [-6.99, -4.09] |
| bucket 1-7 | 14,900 / 66,031 | -5.99 | -5.22 | -0.77 | [-2.59, +1.12] |
| bucket 8-30 | 22,119 / 108,547 | -5.73 | -5.62 | -0.11 | [-0.75, +0.58] |
| bucket 31-60 | 20,335 / 100,476 | -5.26 | -5.35 | +0.09 | [-0.63, +0.85] |

### SD1 — UW GEX regime: G > 0 keep ATM, G < 0 keep OTM2

Family: strike. Source: UW spot-exposures.
**dropped by the GEX check (untested).**

### SD2 — UW flip: price above the prior session's flip keep ATM, below keep OTM2

Family: strike. Source: UW gex-levels (D−1).
**dropped by the GEX check (untested).**

### X1 — the implied move as the target

Family: exit. Source: ThetaData chains / EOD, bars.
Span 2017-01-03 → 2026-09-30, 1,848 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 621,255 trades on 1,805 sessions, mean -14.56; without: 621,255 trades on 1,805 sessions, mean -13.50. **Δ -1.06 [-3.18, +0.97]**, n_eff 2,285 (block ratio) / 2,336 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 270,393 / 270,393 | -11.91 | -11.02 | -0.89 | [-4.01, +1.93] |
| tier 2 | 112,726 / 112,726 | -11.21 | -12.41 | +1.20 | [-0.76, +3.37] |
| tier 3 | 71,381 / 71,381 | -8.77 | -8.51 | -0.26 | [-3.12, +2.16] |
| tier U | 166,755 / 166,755 | -23.60 | -20.38 | -3.21 | [-7.11, +0.60] |
| settlement physical | 514,667 / 514,667 | -15.05 | -14.83 | -0.21 | [-2.04, +1.49] |
| settlement cash | 106,588 / 106,588 | -12.20 | -7.05 | -5.16 | [-9.75, -0.53] |
| bucket 0DTE | 375,438 / 375,438 | -20.43 | -19.09 | -1.34 | [-4.74, +1.81] |
| bucket 1-7 | 66,031 / 66,031 | -6.71 | -5.22 | -1.49 | [-5.38, +2.08] |
| bucket 8-30 | 93,576 / 93,576 | -5.54 | -5.13 | -0.41 | [-1.48, +0.60] |
| bucket 31-60 | 86,210 / 86,210 | -4.76 | -4.56 | -0.20 | [-1.66, +0.96] |

### X2 — UW's walls (prior session) as targets

Family: exit. Source: UW greek-exposure/strike (D−1).
**dropped by the GEX check (untested).**

### X3 — 0DTE entries before 14:00 sold at the 14:00 bid

Family: exit. Source: ThetaData chains.
Span 2017-07-07 → 2026-09-30, 1,762 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE. With: 291,090 trades on 964 sessions, mean -13.88; without: 291,090 trades on 964 sessions, mean -19.63. **Δ +5.75 [+1.83, +9.44]**, n_eff 2,189 (block ratio) / 1,276 (acf). Screen: **PASS → holdout**.

Holdout (once): 233,454 / 233,454 trades, 2,340 sessions (2017-06-02 → 2026-10-21), Δ +7.78 [+4.14, +10.95], n_eff 3,405 / 1,781 → **PASS**.
- holdout part, held-out tickers, all months (descriptive): Δ +7.91 [+4.72, +10.97], 120,269 / 120,269 trades.
- holdout part, exploration tickers, held-out months (descriptive): Δ +7.65 [+1.25, +12.38], 113,185 / 113,185 trades.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 126,469 / 126,469 | -10.06 | -15.32 | +5.25 | [-0.36, +10.87] |
| tier 2 | 30,317 / 30,317 | -17.64 | -28.18 | +10.53 | [+5.30, +17.19] |
| tier 3 | 14,308 / 14,308 | -20.24 | -25.80 | +5.57 | [-2.62, +12.77] |
| tier U | 119,996 / 119,996 | -16.19 | -21.28 | +5.09 | [-0.52, +9.98] |
| settlement physical | 225,023 / 225,023 | -15.96 | -23.45 | +7.49 | [+3.88, +10.94] |
| settlement cash | 66,067 / 66,067 | -6.78 | -6.61 | -0.17 | [-6.83, +6.09] |
| bucket 0DTE | 291,090 / 291,090 | -13.88 | -19.63 | +5.75 | [+1.83, +9.44] |
| holdout tier 1 | 136,283 / 136,283 | -4.02 | -11.73 | +7.72 | [+2.69, +11.60] |
| holdout tier 2 | 20,201 / 20,201 | -14.97 | -16.29 | +1.32 | [-10.19, +10.29] |
| holdout tier 3 | 27,478 / 27,478 | -18.95 | -31.72 | +12.77 | [+7.29, +18.03] |
| holdout tier U | 49,492 / 49,492 | -17.16 | -24.99 | +7.84 | [+3.40, +13.36] |
| holdout settlement physical | 203,289 / 203,289 | -11.03 | -18.71 | +7.67 | [+4.23, +10.69] |
| holdout settlement cash | 30,165 / 30,165 | +0.77 | -7.76 | +8.53 | [-0.52, +15.30] |

### D1 — net premium since 09:30

Family: direction. Source: UW net-prem-ticks.
Span 2023-11-21 → 2026-09-30, 527 sessions; names IWM, SPXW, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 88,564 trades on 527 sessions, mean -11.37; without: 177,245 trades on 527 sessions, mean -10.97. **Δ -0.40 [-4.29, +2.73]**, n_eff 765 (block ratio) / 660 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 76,864 / 153,845 | -13.19 | -13.05 | -0.14 | [-4.42, +2.80] |
| tier U | 11,700 / 23,400 | +0.57 | +2.69 | -2.12 | [-17.02, +12.17] |
| settlement physical | 50,980 / 102,095 | -13.34 | -13.84 | +0.50 | [-5.24, +5.46] |
| settlement cash | 37,584 / 75,150 | -8.70 | -7.07 | -1.63 | [-8.79, +4.39] |
| bucket 0DTE | 68,018 / 136,161 | -13.98 | -11.80 | -2.18 | [-7.00, +1.58] |
| bucket 1-7 | 7,044 / 14,084 | -4.44 | -15.14 | +10.69 | [+3.07, +19.73] |
| bucket 8-30 | 7,131 / 14,266 | -3.22 | -6.26 | +3.05 | [-1.97, +8.46] |
| bucket 31-60 | 6,371 / 12,734 | -0.34 | -2.80 | +2.46 | [-3.39, +7.06] |

### D2 — sweep alerts: calls (ask − bid premium) − puts

Family: direction. Source: UW flow-alerts.
Span 2023-11-21 → 2026-09-30, 527 sessions; names IWM, SPXW, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 68,085 trades on 527 sessions, mean -13.65; without: 136,216 trades on 527 sessions, mean -14.17. **Δ +0.52 [-3.47, +4.25]**, n_eff 498 (block ratio) / 471 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 63,907 / 127,859 | -12.68 | -13.93 | +1.24 | [-2.54, +4.72] |
| tier U | 4,178 / 8,357 | -28.48 | -17.93 | -10.55 | [-27.71, +9.55] |
| settlement physical | 50,001 / 100,034 | -13.84 | -13.83 | -0.00 | [-4.32, +3.98] |
| settlement cash | 18,084 / 36,182 | -13.15 | -15.12 | +1.97 | [-7.07, +12.04] |
| bucket 0DTE | 50,703 / 101,453 | -16.06 | -15.94 | -0.13 | [-4.87, +4.34] |
| bucket 1-7 | 5,912 / 11,826 | -12.12 | -15.88 | +3.76 | [-2.71, +10.96] |
| bucket 8-30 | 6,055 / 12,109 | -4.75 | -6.73 | +1.98 | [-3.65, +7.30] |
| bucket 31-60 | 5,415 / 10,828 | -2.73 | -4.14 | +1.40 | [-4.39, +7.84] |

### D3 — NOPE of the last complete minute

Family: direction. Source: UW nope.
Span 2024-09-03 → 2026-09-30, 374 sessions; names IWM, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 38,672 trades on 374 sessions, mean -20.34; without: 77,399 trades on 374 sessions, mean -15.99. **Δ -4.35 [-9.43, -0.27]**, n_eff 563 (block ratio) / 558 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 38,672 / 77,399 | -20.34 | -15.99 | -4.35 | [-9.43, -0.27] |
| settlement physical | 38,672 / 77,399 | -20.34 | -15.99 | -4.35 | [-9.43, -0.27] |
| bucket 0DTE | 28,812 / 57,672 | -20.66 | -16.87 | -3.79 | [-10.10, +2.20] |
| bucket 1-7 | 3,509 / 7,020 | -31.76 | -21.08 | -10.68 | [-25.00, -2.44] |
| bucket 8-30 | 3,385 / 6,771 | -15.26 | -10.90 | -4.37 | [-10.75, -0.31] |
| bucket 31-60 | 2,966 / 5,936 | -9.58 | -7.23 | -2.34 | [-6.44, +2.28] |

### D4 — market tide: net call − net put premium

Family: direction. Source: UW market-tide.
Span 2023-11-21 → 2026-09-30, 527 sessions; names IWM, SPXW, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 88,606 trades on 527 sessions, mean -14.31; without: 177,245 trades on 527 sessions, mean -10.97. **Δ -3.34 [-10.11, +4.18]**, n_eff 526 (block ratio) / 522 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 76,905 / 153,845 | -15.76 | -13.05 | -2.71 | [-9.57, +4.75] |
| tier U | 11,701 / 23,400 | -4.83 | +2.69 | -7.51 | [-23.35, +9.23] |
| settlement physical | 51,026 / 102,095 | -15.03 | -13.84 | -1.19 | [-7.59, +5.49] |
| settlement cash | 37,580 / 75,150 | -13.34 | -7.07 | -6.27 | [-14.14, +2.79] |
| bucket 0DTE | 68,070 / 136,161 | -15.02 | -11.80 | -3.22 | [-11.76, +6.69] |
| bucket 1-7 | 7,042 / 14,084 | -20.71 | -15.14 | -5.57 | [-15.95, +3.87] |
| bucket 8-30 | 7,133 / 14,266 | -9.88 | -6.26 | -3.62 | [-10.37, +2.75] |
| bucket 31-60 | 6,361 / 12,734 | -4.70 | -2.80 | -1.90 | [-8.17, +2.82] |

### D5 — dark pool: Σ premium × sign(price − NBBO mid), prints ≥ $1M

Family: direction. Source: UW darkpool.
Span 2023-11-21 → 2026-09-30, 527 sessions; names IWM, SPY; buckets 0DTE, 1-7, 31-60, 8-30. With: 51,044 trades on 527 sessions, mean -10.88; without: 102,020 trades on 527 sessions, mean -13.80. **Δ +2.93 [-3.56, +9.12]**, n_eff 383 (block ratio) / 399 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 51,044 / 102,020 | -10.88 | -13.80 | +2.93 | [-3.56, +9.12] |
| settlement physical | 51,044 / 102,020 | -10.88 | -13.80 | +2.93 | [-3.56, +9.12] |
| bucket 0DTE | 37,332 / 74,619 | -12.98 | -15.79 | +2.81 | [-5.35, +11.07] |
| bucket 1-7 | 4,595 / 9,184 | -10.33 | -16.94 | +6.61 | [-3.45, +16.97] |
| bucket 8-30 | 4,815 / 9,629 | -4.18 | -5.58 | +1.40 | [-4.20, +6.46] |
| bucket 31-60 | 4,302 / 8,588 | -0.68 | -2.36 | +1.68 | [-3.28, +6.31] |

### D6 — opening range: above ORH → call, below ORL → put (0DTE from 10:15)

Family: direction. Source: ThetaData bars / SPX prints.
Span 2017-07-07 → 2026-09-30, 1,762 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE. With: 98,952 trades on 959 sessions, mean -18.53; without: 197,857 trades on 959 sessions, mean -19.67. **Δ +1.13 [-4.82, +8.08]**, n_eff 1,709 (block ratio) / 975 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 47,606 / 95,226 | -17.65 | -15.08 | -2.58 | [-11.08, +7.08] |
| tier 2 | 8,212 / 16,401 | -35.96 | -24.20 | -11.76 | [-22.02, +1.32] |
| tier 3 | 4,095 / 8,212 | -40.15 | -28.90 | -11.25 | [-26.17, +3.51] |
| tier U | 39,039 / 78,018 | -13.68 | -23.35 | +9.67 | [+1.17, +17.55] |
| settlement physical | 69,769 / 139,475 | -22.72 | -25.03 | +2.31 | [-3.32, +9.13] |
| settlement cash | 29,183 / 58,382 | -8.53 | -6.86 | -1.67 | [-10.64, +7.83] |
| bucket 0DTE | 98,952 / 197,857 | -18.53 | -19.67 | +1.13 | [-4.82, +8.08] |

### D7 — prior-day structure: above the prior high → call, below the prior low → put

Family: direction. Source: ThetaData bars / SPX prints.
Span 2017-01-04 → 2026-09-30, 1,847 sessions; names AAPL, AMD, AMZN, GOOGL, INTC, IWM, META, MSFT, NVDA, SPXW, SPY, TSLA; buckets 0DTE, 1-7, 31-60, 8-30. With: 165,197 trades on 1,548 sessions, mean -15.07; without: 330,543 trades on 1,548 sessions, mean -13.60. **Δ -1.47 [-5.39, +3.10]**, n_eff 1,975 (block ratio) / 1,563 (acf). Screen: **FAIL**.

| slice | trades with / without | mean with | mean without | Δ | 95% |
|---|---|---|---|---|---|
| tier 1 | 74,201 / 148,452 | -15.94 | -11.64 | -4.30 | [-10.14, +2.13] |
| tier 2 | 30,283 / 60,650 | -14.27 | -11.94 | -2.33 | [-7.38, +3.08] |
| tier 3 | 19,270 / 38,575 | -8.77 | -10.39 | +1.62 | [-4.32, +7.77] |
| tier U | 41,443 / 82,866 | -17.04 | -19.82 | +2.78 | [-5.32, +10.46] |
| settlement physical | 135,015 / 270,161 | -16.16 | -15.33 | -0.83 | [-4.32, +3.08] |
| settlement cash | 30,182 / 60,382 | -10.20 | -5.85 | -4.36 | [-14.11, +6.28] |
| bucket 0DTE | 96,243 / 192,478 | -21.59 | -19.34 | -2.25 | [-8.52, +4.62] |
| bucket 1-7 | 18,529 / 37,090 | -7.55 | -6.30 | -1.25 | [-8.90, +6.50] |
| bucket 8-30 | 26,273 / 52,569 | -6.21 | -5.85 | -0.36 | [-3.37, +3.14] |
| bucket 31-60 | 24,152 / 48,406 | -4.50 | -4.77 | +0.27 | [-3.88, +4.71] |

## 4. Counts

- Screened: 23. Dropped by the GEX check: 3. Not tested for want of data: 0. Computed on the exploration set: 20. Passed the screen: 3. Passed the holdout: 3.

## 5. Verification

- `verify_features.py expl` (plain loops, imports nothing of this study or audit_lib): 55 base trades and 36 feature values and decisions re-derived from the raw files; **0 differences**.
- `verify_features.py hold` (plain loops, imports nothing of this study or audit_lib): 55 base trades and 36 feature values and decisions re-derived from the raw files; **0 differences**.

## 6. Deviations, known departures and readings of the prereg

**Deviations (forced by the data or made after a number was read)**

- UW pages capped by the fetch (a ticker-day whose answer reached the page cap; the rows past the cap are not on disk, so a contract or alert there is undefined): none in this split.
- Single-name expiry-day chains 2026-10-12 → 21 that failed the fetch's verification and stayed in its staging folder (43 files at the last pass). The complaint "N mids that are not (bid + ask) / 2" is the verifier's handling of NaN: polars orders NaN above every number, so each row WITHOUT a quote (NaN bid, ask and mid — the stored files' convention) counts as a bad mid. A staged file is read only when that is its one complaint, N equals its rows with a NaN mid, every quoted row's mid is exactly (bid + ask) / 2 and no bid is negative or above its ask (fcommon.staged_sound); then bid and ask are read from staging. Any other complaint (one-sided strikes, under half the usual rows, INTC 2026-10-19 with 1 strike) and the session is treated as not on disk (no 0DTE trade, no 1–7 exit there). Read from staging in this split: 34 file(s) (AAPL 2026-10-12, AAPL 2026-10-14, AAPL 2026-10-16, AMD 2026-10-12, AMD 2026-10-14, AMD 2026-10-16, AMZN 2026-10-12, AMZN 2026-10-14, AMZN 2026-10-16, AVGO 2026-10-12, AVGO 2026-10-14, AVGO 2026-10-16, GOOGL 2026-10-12, GOOGL 2026-10-14, GOOGL 2026-10-16, INTC 2026-10-12, INTC 2026-10-14, INTC 2026-10-16, META 2026-10-12, META 2026-10-14, META 2026-10-16, META 2026-10-21, MSFT 2026-10-12, MSFT 2026-10-14, MSFT 2026-10-16, MU 2026-10-12, MU 2026-10-14, MU 2026-10-16, NVDA 2026-10-12, NVDA 2026-10-14, NVDA 2026-10-16, TSLA 2026-10-12, TSLA 2026-10-14, TSLA 2026-10-16). All are in 2026-10, a held-out month: only the holdout reads them.
- Option EOD weeks that failed the fetch's verification and stayed in staging are treated as not on disk: AMD 2024-02-20__2024-02-23 (expirations before the date), SPXW 2022-11-21__2022-11-25 (dates ['2022-11-21', '2022-11-22', '2022-11-23', '2022-11-24', '2022-11-25'] != the week's sessions ['2022-11-21', '2022-11-22', '2022-11-23', '2022-11-25']), SPXW 2023-07-03__2023-07-07 (dates ['2023-07-03', '2023-07-04', '2023-07-05', '2023-07-06', '2023-07-07'] != the week's sessions ['2023-07-03', '2023-07-05', '2023-07-06', '2023-07-07']), SPXW 2023-11-20__2023-11-24 (dates ['2023-11-20', '2023-11-21', '2023-11-22', '2023-11-23', '2023-11-24'] != the week's sessions ['2023-11-20', '2023-11-21', '2023-11-22', '2023-11-24']), SPXW 2024-06-17__2024-06-21 (dates ['2024-06-17', '2024-06-18', '2024-06-19', '2024-06-20', '2024-06-21'] != the week's sessions ['2024-06-17', '2024-06-18', '2024-06-20', '2024-06-21']), SPXW 2024-07-01__2024-07-05 (dates ['2024-07-01', '2024-07-02', '2024-07-03', '2024-07-04', '2024-07-05'] != the week's sessions ['2024-07-01', '2024-07-02', '2024-07-03', '2024-07-05']), SPXW 2024-11-25__2024-11-29 (dates ['2024-11-25', '2024-11-26', '2024-11-27', '2024-11-28', '2024-11-29'] != the week's sessions ['2024-11-25', '2024-11-26', '2024-11-27', '2024-11-29']), SPXW 2025-01-06__2025-01-10 (dates ['2025-01-06', '2025-01-07', '2025-01-08', '2025-01-09', '2025-01-10'] != the week's sessions ['2025-01-06', '2025-01-07', '2025-01-08', '2025-01-10']), SPXW 2025-06-16__2025-06-20 (dates ['2025-06-16', '2025-06-17', '2025-06-18', '2025-06-19', '2025-06-20'] != the week's sessions ['2025-06-16', '2025-06-17', '2025-06-18', '2025-06-20']), SPXW 2025-11-24__2025-11-28 (dates ['2025-11-24', '2025-11-25', '2025-11-26', '2025-11-27', '2025-11-28'] != the week's sessions ['2025-11-24', '2025-11-25', '2025-11-26', '2025-11-28']), SPXW 2026-02-09__2026-02-13 (expirations before the date). The SPXW weeks are mostly holiday weeks (the vendor answered rows dated on the exchange holiday, which the fetch's session check refused); they are not read. Each such week leaves its sessions without EOD for that name: no multi-day entry or EOD exit there (a trade whose exit falls there is not formed, counted), and the tier and IV-rank windows lose them (Tier U where a tier window is short; IV rank needs 200 of 252).
- UW answers logged by the fetch as empty on or after a route's served start ("gaps"; the value is undefined there): flow_alerts 650, nope 3; gex-levels rows with every level null (stored .empty; SPY/SPX before 2024-05-13, as INVENTORY B5): 132 ticker-days.
- A bug found on the FIRST holdout read and fixed before the read that carries the verdicts: two option-EOD inputs were not unique — SPY's 2015-03-30 and 03-31 sat in two weekly files (both read, so those sessions' multi-day trades were doubled), and the next-session volumes for V3 were keyed by the last trading day rather than the listed expiry, so on a day with two expiries sharing a last trading day (2025-01-09, the market closure; 2026-10-21) the join doubled 0DTE trades. Every such day is in a held-out month, so the exploration screen was unaffected (its trade count is unchanged and no exploration row was duplicated); the holdout table had 777,571 rows for 580,274 base trades. Fixed: a trading day is read once (the first weekly file), EOD rows are unique per (date, expiration, strike, right), V3 joins on the listed expiry, and screen.py refuses a join that duplicates a base trade. The holdout was then run once more on the corrected table (out/holdout.json); the first, duplicated read is kept as out/holdout_run1_duplicated_rows.json and reported beside it. No feature, threshold or rule changed between the two reads.
- IWM's 2026-10-21 same-day chain failed the fetch's first verification (one-sided strikes) and was merged on its second pass; it is read like any other file, a strike without a standing quote untradable by the prereg's rules (holdout month).
- SPXW option EOD: the fetch measured one week (23.9 s, 1.040483 MB; projected 1.37 h, 0.215 GB) and stored it with max_dte = 60, so SPXW is in the 1–60 DTE buckets, V3 and V6 apply to SPXW and the VN1 pairs include 1–60 DTE. Because only expiries to 60 days were fetched, SPXW's tier volume is the day's volume over those expiries only (not every expiry).
- UW `nope` start: {"fetch_from": "2024-08-30", "last_empty_seen": "2024-08-29", "first_served_seen": "2024-09-16", "bisect_calls": [["2025-05-08", ".parquet"], ["2024-08-14", ".empty"], ["2024-12-23", ".parquet"], ["2024-10-17", ".parquet"], ["2024-09-16", ".parquet"], ["2024-08-29", ".empty"]], "note": "SPY bisected; every date from fetch_from is asked for every name; dates before it are inferred empty, not asked"}; D3 is undefined before it.
- The calendar: the 2022 → rule against SPY's EOD file dates disagrees on 0 dates.

**Known departures the prereg lists (section 8)**

- The 0DTE grid keeps both named endpoints (09:45 and 15:30; the last step is 15 minutes) — prereg 2.3.
- V4 and V5 use the realized release dates (prereg 3.2 note), including the shutdown-moved CPI and NFP of October–December 2025.
- V2 reads the open_interest of the chain dated D (the count published the morning of D); the last session of the span has the chain only if the fetch stored it.
- D3 (NOPE) from its served start; D5 (dark pool) with the fetch's $1M premium floor (so 23 features are screened).

**Readings of the prereg where its text left a choice (made before any result was read)**

- Expiries dated on a Saturday (the monthlies before 2015) or a non-trading day are read at their last trading day for the calendar DTE, T and the exits.
- The EOD entry is stamped 16:00 for T (so T = calendar days ÷ 365) and for every point-in-time rule; its underlying price is the 15:59 bar (SPXW: the SPX print stamped 15:59).
- Sessions in "the 5th / 10th session after", "the session before the expiry day", RV20 and the tier and IV-rank windows are full sessions (half days out, as prereg 2.1 defines sessions); the prior session of D7 is the previous trading day.
- RV20 needs 21 15:59 closes on consecutive full sessions; for a 0DTE entry it ends at the session before (point in time).
- The single names' option EOD is read from 2022-11-01 for every EOD-based input (base trades, tiers, V3, V6), as the scope and section 2.7 set ("the singles before 2022-12" are Tier U), although older AAPL and FB weekly files are on disk.
- META before the 2022-06-09 renaming is FB in the stored chains (to 2022-06-03) and bars (to 2022-06-08); the META folder's ten overlapping expiry days are not read twice.
- The intraday no-bid fallback looks back at most 10 minutes and never before the entry minute.
- An expiry-day chain that is on disk but lacks the contract forms no 1–7 trade (counted).
- ES1/ES2 are defined at an entry when at least two of the three multi-day buckets have a value; the "without" arm is the trades of those buckets. ES4 chooses among the strike buckets whose contract has a solved IV; a tie in |delta| − 0.30 keeps the contract nearer the money (smaller |x|).
- VN1: two venues tie when their cost shares differ by ≤ 1e-12 (both kept).
- V4/V5 window: (16:00 of the trading day before the entry session, the expiry's 16:00), both ends open; an EOD entry on D is stamped 16:00 on D, so D−1's 16:00 is its last close before; a post-market report counts at 16:00 of its date.
- V2: UW's dated chain was fetched with exclude_zero_oi_chains = true, so a contract with no row (zero open interest included) is undefined, as the prereg says of a contract not found.
- D2 for SPXW sums the SPX- and SPXW-filed alerts; D5 counts every served print (cancelled ones included).
- The single names' 0DTE V3 and V6 exist only where their 2022-11 → EOD files do.

