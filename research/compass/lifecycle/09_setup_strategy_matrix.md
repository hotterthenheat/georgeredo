# Lifecycle research — 9. Setup × strategy matrix (deliverable 5)

Every setup × structure cell tested, classified by `scripts/build_matrix.py` from the result files and rendered by
`scripts/matrix_md.py`. Nothing here is typed by hand. A cell's label is the first that applies:

| Code | Label | Rule |
|---|---|---|
| n | insufficient | fewer than 100 trades or 60 sessions |
| F | failed | every policy's interval below zero, or the walk-forward interval below zero |
| H | failed on the hold-out | tested once on the hold-out and not promoted (`07_validation.md` §4) |
| C | carry, not setup | some policy's lower bound > 0 and walk-forward > 0, but no better than its clean control |
| P | promising | as C, and better than its clean control; still not validated without a hold-out |
| ? | inconclusive | intervals span zero |
| · | not applicable | the structure does not follow the setup's direction, or was not run |

**Structures**
- LC-S / LP-S: Steady call / put.
- LC-B / LP-B: Big Payoff call / put.
- DCS / DPS: debit call / put spread.
- CPS: credit put spread.
- CSP: cash-secured put.
- STR / STG: long straddle / strangle.

**How a cell is scored**
- Its best policy is the stage-1 policy with the highest lower bound on development + validation.
- The walk-forward column picks a policy each quarter (Tier I) or year (daily tier) on earlier data alone.

## 1. Same-day options (Tier I: SPY, QQQ, IWM, SPXW 0DTE, 2022-05 → 2025-09; hold-out 2025-10 → 2026-10)

Counts: failed 37, failed on the hold-out 7, inconclusive 47, insufficient 5.

| setup | LC-S | LP-S | LC-B | LP-B | DCS | DPS | CPS | CSP |
|---|---|---|---|---|---|---|---|---|
| Bounce, trigger only | F | F | F | F | F | F | F | ? |
| Breakout | n | F | n | F | n | F | n | n |
| Failed breakout | F | ? | ? | ? | ? | ? | ? | ? |
| 5m breakout, trigger only | ? | ? | F | F | ? | F | ? | H |
| Breakout retest, trigger only | ? | ? | ? | F | ? | F | ? | H |
| Fair-value gap (ICT) | ? | ? | F | F | ? | F | F | ? |
| Liquidity sweep (ICT) | ? | ? | F | F | ? | F | F | ? |
| Market-structure shift (ICT) | ? | ? | ? | ? | ? | ? | H | ? |
| Quick Scalps | ? | F | ? | F | H | F | H | H |
| Trend pullback | ? | ? | ? | ? | ? | F | ? | ? |
| Trend pullback, trigger only | F | ? | F | ? | F | ? | ? | H |
| VWAP reclaim | F | F | F | F | F | F | ? | ? |

### Cells that did not simply fail

| setup | structure | best policy | trades | expectancy [95 %] | walk-forward [95 %] | vs a later minute [95 %] | hold-out | label |
|---|---|---|---|---|---|---|---|---|
| Bounce, trigger only | CSP | M5_thesis1m | 6,203 | -7.8 [-16.1, -1.1] | -9.5 [-23.9, +1.3] | -0.8 [-12.4, +12.0] | — | inconclusive |
| Breakout | CPS | M0_expiry | 320 | +31.5 [+18.0, +41.8] | +29.7 [-3.9, +52.3] | -0.9 [-6.5, +4.0] | — | insufficient |
| Breakout | CSP | M0_expiry | 320 | +143.0 [+62.4, +213.2] | +157.1 [-31.8, +310.1] | +17.6 [-27.0, +47.3] | — | insufficient |
| Breakout | DCS | M5_thesis1m | 305 | -17.8 [-23.8, -12.5] | -59.9 [-147.2, +1.2] | -8.5 [-51.1, +36.1] | — | insufficient |
| Breakout | LC-B | M5_thesis1m | 330 | -7.6 [-12.1, -4.1] | -27.0 [-69.8, -3.2] | +10.3 [-23.0, +42.6] | — | insufficient |
| Breakout | LC-S | M5_thesis1m | 331 | -15.9 [-27.0, -6.0] | -45.6 [-306.2, +147.3] | -6.5 [-85.7, +78.2] | — | insufficient |
| Failed breakout | CPS | M1_t60 | 321 | -4.2 [-13.4, +4.2] | -14.2 [-33.9, +3.3] | +3.6 [-6.3, +13.3] | — | inconclusive |
| Failed breakout | CSP | M1_t60 | 323 | +21.7 [-18.0, +57.8] | +15.9 [-71.6, +89.7] | +14.1 [-28.5, +56.3] | — | inconclusive |
| Failed breakout | DCS | M1_t30 | 319 | -7.3 [-30.1, +14.8] | -23.5 [-82.3, +32.8] | +0.5 [-20.4, +22.0] | — | inconclusive |
| Failed breakout | DPS | M1_t30 | 294 | -30.0 [-53.3, -6.4] | -14.8 [-27.3, +1.3] | -8.1 [-30.5, +14.6] | — | inconclusive |
| Failed breakout | LC-B | M2_s35_t50 | 330 | -5.3 [-16.9, +7.0] | -11.5 [-23.2, +2.3] | -4.1 [-15.4, +7.9] | — | inconclusive |
| Failed breakout | LP-B | M2_s35_t50 | 315 | -9.1 [-23.9, +6.4] | -9.0 [-23.7, +7.0] | +0.7 [-13.8, +14.8] | — | inconclusive |
| Failed breakout | LP-S | M2_s35_t50 | 313 | -30.5 [-77.6, +26.7] | -9.9 [-32.6, +19.5] | -1.9 [-48.2, +47.1] | — | inconclusive |
| 5m breakout, trigger only | CPS | M0_expiry | 4,148 | +7.7 [-2.9, +17.6] | +0.9 [-12.1, +11.9] | -3.1 [-8.0, +1.7] | — | inconclusive |
| 5m breakout, trigger only | CSP | M1_t60 | 4,161 | +15.1 [+4.6, +24.2] | +28.8 [+13.8, +42.3] | +0.7 [-9.6, +11.6] | finalist M13_tpnone_s15: hold-out +26.30 [+3.78]; not promoted (R1 Holm; R2 against a later minute) | failed on the hold-out |
| 5m breakout, trigger only | DCS | M0_expiry | 3,855 | +18.4 [-13.4, +53.6] | -1.4 [-42.1, +38.9] | +9.8 [-3.7, +23.4] | — | inconclusive |
| 5m breakout, trigger only | LC-S | M1_t30 | 4,269 | -1.3 [-12.8, +8.9] | -11.2 [-32.8, +8.7] | +2.5 [-8.5, +13.3] | — | inconclusive |
| 5m breakout, trigger only | LP-S | M1_t30 | 2,873 | -24.0 [-46.5, -4.3] | -12.8 [-27.9, +0.9] | -15.6 [-34.3, +1.6] | — | inconclusive |
| Breakout retest, trigger only | CPS | M0_expiry | 3,532 | +6.7 [-3.9, +16.9] | +2.6 [-6.9, +11.3] | -3.0 [-7.6, +1.6] | — | inconclusive |
| Breakout retest, trigger only | CSP | M13_tp50_s2 | 3,557 | +7.0 [-5.1, +18.1] | +26.2 [+9.9, +41.1] | -6.0 [-15.0, +2.9] | finalist M13_tpnone_s15: hold-out +24.67 [+2.79]; not promoted (R1 Holm; R2 against a later minute) | failed on the hold-out |
| Breakout retest, trigger only | DCS | M0_expiry | 3,249 | +18.3 [-14.0, +52.3] | -2.7 [-40.0, +32.7] | +10.1 [-3.7, +23.5] | — | inconclusive |
| Breakout retest, trigger only | LC-B | M2_s35_t50 | 3,642 | -7.1 [-10.6, -3.7] | -2.6 [-6.1, +1.1] | +0.3 [-2.9, +3.6] | — | inconclusive |
| Breakout retest, trigger only | LC-S | M1_t30 | 3,654 | -9.3 [-19.8, +1.2] | -2.5 [-25.1, +21.0] | -0.5 [-11.7, +10.6] | — | inconclusive |
| Breakout retest, trigger only | LP-S | M1_t30 | 2,340 | -18.3 [-38.6, +1.7] | -9.0 [-24.8, +6.5] | -12.6 [-30.7, +5.4] | — | inconclusive |
| Fair-value gap (ICT) | CSP | M1_t60 | 2,219 | +12.2 [-8.5, +30.9] | +21.5 [-2.1, +46.7] | +9.1 [-13.5, +31.3] | — | inconclusive |
| Fair-value gap (ICT) | DCS | M0_expiry | 2,131 | +26.2 [-17.2, +67.5] | +17.4 [-28.8, +66.3] | +10.0 [-13.3, +31.5] | — | inconclusive |
| Fair-value gap (ICT) | LC-S | M1_t30 | 2,252 | -16.1 [-38.0, +5.3] | -12.5 [-28.8, +3.0] | -9.5 [-32.2, +11.6] | — | inconclusive |
| Fair-value gap (ICT) | LP-S | M2_s35_t50 | 3,538 | -15.5 [-32.3, +0.7] | -3.9 [-18.0, +13.7] | +1.7 [-13.5, +16.8] | — | inconclusive |
| Liquidity sweep (ICT) | CSP | M13_tp50_s2 | 1,375 | +12.6 [-4.6, +29.4] | +2.7 [-33.1, +36.4] | +5.4 [-10.9, +20.7] | — | inconclusive |
| Liquidity sweep (ICT) | DCS | M2_s35_t50 | 1,340 | -5.5 [-18.6, +9.4] | -17.1 [-34.9, +1.4] | +4.1 [-8.9, +17.6] | — | inconclusive |
| Liquidity sweep (ICT) | LC-S | M2_s35_t50 | 1,396 | +2.6 [-23.3, +29.9] | -13.0 [-30.7, +4.2] | +5.3 [-18.6, +29.1] | — | inconclusive |
| Liquidity sweep (ICT) | LP-S | M1_t30 | 1,286 | -35.6 [-59.2, -12.3] | -20.6 [-42.5, +0.4] | -9.4 [-29.6, +13.0] | — | inconclusive |
| Market-structure shift (ICT) | CPS | M0_expiry | 170 | +21.7 [-4.6, +43.5] | +7.1 [+0.2, +13.2] | +1.6 [-12.2, +11.4] | finalist M13_tp25_snone: hold-out -76.44 [-166.45]; not promoted (R1 Holm; R2 against a later minute) | failed on the hold-out |
| Market-structure shift (ICT) | CSP | M0_expiry | 169 | +91.9 [-4.2, +176.2] | +36.7 [-6.3, +71.1] | +17.0 [-23.2, +49.3] | — | inconclusive |
| Market-structure shift (ICT) | DCS | M1_t30 | 167 | -18.9 [-43.3, +8.5] | +9.3 [-35.0, +49.6] | -7.7 [-35.8, +21.7] | — | inconclusive |
| Market-structure shift (ICT) | DPS | M1_t30 | 160 | -18.1 [-46.8, +13.3] | — [—, —] | +9.4 [-22.6, +43.2] | — | inconclusive |
| Market-structure shift (ICT) | LC-B | M0_expiry | 172 | +86.3 [-0.5, +187.3] | +5.4 [-19.9, +25.1] | +16.3 [-48.5, +83.1] | — | inconclusive |
| Market-structure shift (ICT) | LC-S | M0_expiry | 172 | +119.4 [-65.9, +332.9] | +23.1 [-59.7, +86.0] | -42.3 [-144.9, +59.5] | — | inconclusive |
| Market-structure shift (ICT) | LP-B | M2_s35_t50 | 165 | -13.2 [-30.2, +5.9] | — [—, —] | +1.2 [-16.1, +19.4] | — | inconclusive |
| Market-structure shift (ICT) | LP-S | M1_t30 | 165 | -21.0 [-81.5, +46.1] | — [—, —] | +18.9 [-48.9, +89.8] | — | inconclusive |
| Quick Scalps | CPS | M0_expiry | 3,046 | +17.6 [+6.0, +26.9] | +14.7 [+4.7, +23.7] | -5.3 [-11.7, +0.1] | finalist M0_expiry: hold-out +5.96 [-19.86]; not promoted (R1 Holm; R2 against a later minute) | failed on the hold-out |
| Quick Scalps | CSP | M0_expiry | 3,039 | +72.5 [+26.7, +110.4] | +49.8 [+10.9, +84.8] | -15.9 [-46.8, +8.7] | finalist M13_tpnone_s20: hold-out +51.73 [+5.42]; not promoted (R1 Holm; R2 against a later minute) | failed on the hold-out |
| Quick Scalps | DCS | M0_expiry | 2,749 | +50.3 [+10.6, +93.7] | +16.9 [-19.6, +51.0] | +20.5 [+0.8, +40.9] | L-A3 M0_expiry: hold-out +64.37 [-18.16], p 0.064; beats a later minute +45.57 [+5.29]; not a candidate (H-DCS-1 failed) | failed on the hold-out |
| Quick Scalps | LC-B | M1_t30 | 3,130 | -2.9 [-8.3, +2.2] | -0.9 [-10.0, +8.1] | +1.0 [-3.5, +5.6] | — | inconclusive |
| Quick Scalps | LC-S | M0_expiry | 3,136 | +66.5 [-0.4, +140.0] | -19.6 [-66.0, +27.6] | +46.9 [+12.4, +83.0] | — | inconclusive |
| Trend pullback | CPS | M1_t30 | 594 | -1.9 [-6.1, +2.3] | +0.2 [-5.9, +5.1] | +8.5 [+2.4, +14.8] | — | inconclusive |
| Trend pullback | CSP | M1_t30 | 607 | +13.2 [-2.7, +28.9] | -11.1 [-79.1, +24.2] | +21.6 [+4.0, +38.9] | — | inconclusive |
| Trend pullback | DCS | M1_t30 | 526 | +1.9 [-13.9, +19.2] | -5.4 [-17.3, +5.3] | +19.9 [+6.3, +33.7] | — | inconclusive |
| Trend pullback | LC-B | M2_s35_t50 | 612 | -0.3 [-8.6, +9.2] | -4.5 [-11.1, +2.3] | +6.0 [-0.6, +12.7] | — | inconclusive |
| Trend pullback | LC-S | M1_t30 | 617 | +15.3 [-14.0, +48.2] | +14.7 [-6.8, +33.2] | +32.5 [+8.1, +58.1] | — | inconclusive |
| Trend pullback | LP-B | M2_s35_t50 | 758 | -15.1 [-26.5, -4.9] | -4.7 [-9.9, +0.3] | -2.7 [-12.7, +7.2] | — | inconclusive |
| Trend pullback | LP-S | M2_s35_t50 | 756 | -32.2 [-74.8, +6.4] | -7.8 [-31.1, +17.6] | -2.2 [-35.1, +30.0] | — | inconclusive |
| Trend pullback, trigger only | CPS | M0_expiry | 4,155 | +10.3 [-0.6, +20.0] | +8.6 [-4.9, +21.5] | -3.5 [-9.1, +1.6] | — | inconclusive |
| Trend pullback, trigger only | CSP | M0_expiry | 4,184 | +54.2 [+24.0, +81.0] | +51.4 [+10.8, +85.8] | +1.7 [-14.0, +16.0] | finalist M0_expiry: hold-out +51.95 [-6.95]; not promoted (R1 Holm; R2 against a later minute) | failed on the hold-out |
| Trend pullback, trigger only | DPS | M1_t30 | 2,023 | -13.9 [-25.7, -4.3] | -9.1 [-20.0, +1.8] | +1.4 [-10.1, +12.8] | — | inconclusive |
| Trend pullback, trigger only | LP-B | M2_s35_t50 | 2,167 | -4.4 [-11.3, +1.7] | -2.4 [-11.9, +7.0] | +3.9 [-1.5, +9.2] | — | inconclusive |
| Trend pullback, trigger only | LP-S | M1_t30 | 2,148 | -5.1 [-29.2, +17.1] | +2.1 [-19.4, +22.3] | +1.6 [-22.5, +25.6] | — | inconclusive |
| VWAP reclaim | CPS | M0_expiry | 15,329 | +6.8 [-3.3, +16.5] | +7.1 [-5.7, +18.5] | -1.0 [-5.7, +3.6] | — | inconclusive |
| VWAP reclaim | CSP | M0_expiry | 15,431 | +41.4 [-2.9, +79.2] | +26.3 [-19.4, +62.3] | +3.9 [-12.8, +19.4] | — | inconclusive |

### Volatility and Fed-day setups (Tier I)

| setup | CPS | CSP | STR | STG |
|---|---|---|---|---|
| ALL10P | ? | C | · | · |
| ALL10V | · | · | F | ? |
| ALL1330 | · | · | F | F |
| EVF | · | · | n | n |
| VOLC | · | · | F | F |
| VOLR | F | ? | · | · |

| setup | structure | best policy | trades | expectancy [95 %] | walk-forward [95 %] | vs a random day [95 %] | label |
|---|---|---|---|---|---|---|---|
| ALL10P | CPS | M0_expiry | 2,585 | -3.1 [-13.0, +7.0] | -9.3 [-20.2, +0.3] | — [—, —] | inconclusive |
| ALL10P | CSP | M13_tpnone_s20 | 2,601 | +21.9 [+2.2, +41.9] | +18.5 [-8.0, +43.4] | — [—, —] | carry, not setup |
| ALL10V | STG | M1_t15 | 2,576 | -17.6 [-24.8, -8.1] | -13.8 [-24.5, +0.4] | — [—, —] | inconclusive |
| EVF | STG | M1_t15 | 85 | -1.7 [-12.1, +11.8] | — [—, —] | +14.3 [+3.0, +27.9] | insufficient |
| EVF | STR | M1_t15 | 85 | -4.9 [-17.5, +10.4] | — [—, —] | +14.8 [+1.0, +30.7] | insufficient |
| VOLR | CSP | M13_tp75_s15 | 647 | -3.3 [-39.5, +33.6] | -19.9 [-100.1, +56.8] | -10.4 [-38.3, +17.4] | inconclusive |

## 2. Daily lifecycles

_Running: filled when the daily tier finishes (`06_daily_tier.md`)._
