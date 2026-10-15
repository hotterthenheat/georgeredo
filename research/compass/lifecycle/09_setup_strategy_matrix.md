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
| V | validated | passed every promotion rule on the hold-out |
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

## 2. Daily lifecycles (daily tier: Weekly, Swing, Position, Long-Dated, LEAPS; development ≤ 2021, validation 2022–2023)

Counts: carry, not setup 32, failed 60, failed on the hold-out 19, inconclusive 54, insufficient 113, promising 2.

### Index ETFs (SPY, QQQ, IWM)

| setup | bucket | LC-S | LP-S | LC-B | LP-B | DCS | DPS | CPS | CSP | STR | STG |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Baseline: non-Fed weeks | L | · | · | · | · | · | · | · | · | C | ? |
| Baseline: non-Fed weeks | P | · | · | · | · | · | · | · | · | ? | ? |
| Baseline: non-Fed weeks | S | · | · | · | · | · | · | · | · | ? | ? |
| Baseline: non-Fed weeks | W | · | · | · | · | · | · | · | · | ? | ? |
| Baseline: non-Fed weeks | X | · | · | · | · | · | · | · | · | C | ? |
| Baseline: every Monday, long | L | C | · | C | · | C | · | ? | C | · | · |
| Baseline: every Monday, long | P | C | · | C | · | C | · | ? | C | · | · |
| Baseline: every Monday, long | S | C | · | C | · | C | · | ? | C | · | · |
| Baseline: every Monday, long | W | ? | · | C | · | ? | · | F | ? | · | · |
| Baseline: every Monday, long | X | C | · | C | · | C | · | F | C | · | · |
| Baseline: every Monday, put sale | L | · | · | · | · | · | · | ? | C | · | · |
| Baseline: every Monday, put sale | P | · | · | · | · | · | · | ? | C | · | · |
| Baseline: every Monday, put sale | S | · | · | · | · | · | · | ? | C | · | · |
| Baseline: every Monday, put sale | W | · | · | · | · | · | · | F | ? | · | · |
| Baseline: every Monday, put sale | X | · | · | · | · | · | · | F | C | · | · |
| Baseline: every Monday, short | L | · | F | · | F | · | F | · | · | · | · |
| Baseline: every Monday, short | P | · | F | · | F | · | F | · | · | · | · |
| Baseline: every Monday, short | S | · | F | · | F | · | F | · | · | · | · |
| Baseline: every Monday, short | W | · | F | · | F | · | F | · | · | · | · |
| Baseline: every Monday, short | X | · | F | · | F | · | F | · | · | · | · |
| Baseline: every Monday, straddle | L | · | · | · | · | · | · | · | · | ? | F |
| Baseline: every Monday, straddle | P | · | · | · | · | · | · | · | · | ? | ? |
| Baseline: every Monday, straddle | S | · | · | · | · | · | · | · | · | ? | ? |
| Baseline: every Monday, straddle | W | · | · | · | · | · | · | · | · | ? | ? |
| Baseline: every Monday, straddle | X | · | · | · | · | · | · | · | · | C | ? |
| Bounce (daily) | L | n | n | n | n | n | n | n | n | · | · |
| Bounce (daily) | P | n | n | n | n | n | n | n | n | · | · |
| Bounce (daily) | S | n | n | n | n | n | n | n | n | · | · |
| Bounce (daily) | W | n | n | n | n | n | n | n | n | · | · |
| Bounce (daily) | X | n | n | n | n | n | n | n | n | · | · |
| Failed bounce (daily) | L | n | n | n | n | n | n | n | n | · | · |
| Failed bounce (daily) | P | n | n | n | n | n | n | n | n | · | · |
| Failed bounce (daily) | S | n | n | n | n | n | n | n | n | · | · |
| Failed bounce (daily) | W | n | n | n | n | n | n | n | n | · | · |
| Failed bounce (daily) | X | n | n | n | n | n | n | n | n | · | · |
| Breakout (daily) | L | H | ? | P | ? | H | F | C | H | · | · |
| Breakout (daily) | P | C | ? | ? | ? | F | F | ? | C | · | · |
| Breakout (daily) | S | C | ? | ? | ? | C | F | ? | C | · | · |
| Breakout (daily) | W | ? | ? | F | F | ? | ? | ? | H | · | · |
| Breakout (daily) | X | H | F | H | F | H | F | F | H | · | · |
| Failed breakout (daily) | L | n | F | n | F | n | F | n | n | · | · |
| Failed breakout (daily) | P | n | F | n | F | n | F | n | n | · | · |
| Failed breakout (daily) | S | ? | ? | n | ? | n | F | n | P | · | · |
| Failed breakout (daily) | W | n | F | n | F | n | F | n | n | · | · |
| Failed breakout (daily) | X | n | F | n | F | n | F | n | n | · | · |
| Day before the Fed | L | · | · | · | · | · | · | · | · | n | n |
| Day before the Fed | P | · | · | · | · | · | · | · | · | n | n |
| Day before the Fed | S | · | · | · | · | · | · | · | · | n | n |
| Day before the Fed | W | · | · | · | · | · | · | · | · | n | n |
| Day before the Fed | X | · | · | · | · | · | · | · | · | n | n |
| Trend pullback (daily) | L | H | F | H | F | H | F | ? | H | · | · |
| Trend pullback (daily) | P | C | F | ? | F | H | F | F | ? | · | · |
| Trend pullback (daily) | S | H | F | ? | F | H | F | F | C | · | · |
| Trend pullback (daily) | W | ? | ? | ? | ? | ? | F | F | ? | · | · |
| Trend pullback (daily) | X | H | F | H | F | H | F | F | H | · | · |

### Cells that did not simply fail

| group | setup | bucket | structure | best policy | trades | expectancy [95 %] | walk-forward [95 %] | vs a random day [95 %] | hold-out | label |
|---|---|---|---|---|---|---|---|---|---|---|
| index_etf | Baseline: non-Fed weeks | L | STG | D1_t5 | 641 | -26.3 [-48.9, -2.8] | -41.1 [-150.3, +70.0] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | L | STR | D12_both_t50 | 642 | +245.1 [+115.8, +373.3] | +234.6 [+27.4, +419.0] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: non-Fed weeks | P | STG | D1_t5 | 645 | -12.0 [-35.5, +13.5] | -4.7 [-46.5, +40.8] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | P | STR | D1_t5 | 645 | -17.6 [-43.0, +10.0] | -69.1 [-168.3, +32.9] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | S | STG | D1_t5 | 640 | -7.3 [-33.1, +22.4] | -23.8 [-69.1, +26.0] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | S | STR | D1_t5 | 645 | -12.7 [-42.9, +21.0] | +0.1 [-55.5, +65.1] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | W | STG | D0_dte21 | 618 | -4.7 [-14.5, +6.9] | -8.0 [-25.0, +11.1] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | W | STR | D0_dte21 | 637 | -8.7 [-22.1, +5.9] | -16.7 [-39.4, +8.6] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | X | STG | D2_s50_t100 | 569 | +96.1 [-13.3, +214.1] | +87.5 [-86.1, +270.7] | — [—, —] | — | inconclusive |
| index_etf | Baseline: non-Fed weeks | X | STR | D2_s50_t50 | 614 | +350.3 [+171.6, +544.0] | +304.2 [-9.1, +598.2] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | L | CPS | D0_dte21 | 1,681 | +9.2 [+5.5, +12.4] | -3.9 [-14.0, +5.2] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, long | L | CSP | D0_dte21 | 1,682 | +489.9 [+436.7, +540.3] | +569.0 [+464.3, +661.3] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | L | DCS | D0_expiry | 1,668 | +234.1 [+178.5, +291.2] | +175.9 [+56.0, +295.7] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | L | LC-B | D7_dd40 | 1,670 | +230.6 [+151.9, +312.6] | +321.2 [+190.1, +459.9] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | L | LC-S | D7_dd40 | 1,682 | +589.3 [+441.0, +751.6] | +589.3 [+334.3, +843.2] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | P | CPS | D0_expiry | 1,678 | +5.1 [+0.0, +9.6] | -1.1 [-8.7, +7.1] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, long | P | CSP | D0_ltd1 | 1,682 | +154.6 [+88.6, +214.1] | +162.8 [+46.0, +264.6] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | P | DCS | D0_ltd1 | 1,672 | +55.8 [+20.5, +92.2] | +45.2 [-13.7, +101.8] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | P | LC-B | D7_dd40 | 1,678 | +38.3 [+13.0, +66.7] | +15.9 [-22.3, +55.4] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | P | LC-S | D0_ltd1 | 1,683 | +142.3 [+68.9, +221.4] | +163.3 [+42.5, +283.5] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | S | CPS | D0_expiry | 1,665 | +2.9 [-2.3, +7.7] | -1.8 [-10.5, +6.2] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, long | S | CSP | D0_expiry | 1,680 | +84.2 [+29.7, +131.7] | +45.8 [-44.5, +128.6] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | S | DCS | D0_expiry | 1,646 | +46.8 [+21.3, +73.8] | +61.3 [+13.6, +105.3] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | S | LC-B | D1_t10 | 1,667 | +13.9 [+1.6, +26.7] | +4.5 [-23.2, +31.3] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | S | LC-S | D0_expiry | 1,677 | +91.2 [+40.4, +146.0] | +109.6 [+16.9, +196.5] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | W | CSP | D13_tp50_s2 | 1,680 | +6.6 [-4.4, +17.5] | +1.6 [-20.3, +21.7] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, long | W | DCS | D0_expiry | 1,661 | +4.3 [-8.1, +16.9] | +5.7 [-16.9, +24.5] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, long | W | LC-B | D2_s50_t50_exp | 1,667 | +5.8 [+0.7, +12.2] | +6.5 [-6.2, +18.4] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | W | LC-S | D2_s50_t50_exp | 1,680 | +8.9 [-5.9, +26.1] | +11.5 [-34.8, +52.5] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, long | X | CSP | D0_dte21 | 1,666 | +823.8 [+756.2, +891.1] | +760.2 [+581.3, +919.8] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | X | DCS | D7_dd40 | 1,523 | +550.7 [+425.2, +667.1] | +506.4 [+346.1, +677.0] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | X | LC-B | D7_dd40 | 1,527 | +763.8 [+625.4, +903.6] | +1154.0 [+908.3, +1417.0] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, long | X | LC-S | D7_dd40 | 1,677 | +1729.2 [+1444.7, +2023.5] | +2391.5 [+1896.7, +2903.9] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, put sale | L | CPS | D0_dte21 | 1,681 | +9.2 [+5.5, +12.4] | -3.9 [-14.0, +5.2] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, put sale | L | CSP | D0_dte21 | 1,682 | +489.9 [+436.7, +540.3] | +569.0 [+464.3, +661.3] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, put sale | P | CPS | D0_expiry | 1,678 | +5.1 [+0.0, +9.6] | -1.1 [-8.7, +7.1] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, put sale | P | CSP | D0_ltd1 | 1,682 | +154.6 [+88.6, +214.1] | +162.8 [+46.0, +264.6] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, put sale | S | CPS | D0_expiry | 1,665 | +2.9 [-2.3, +7.7] | -1.8 [-10.5, +6.2] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, put sale | S | CSP | D0_expiry | 1,680 | +84.2 [+29.7, +131.7] | +45.8 [-44.5, +128.6] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, put sale | W | CSP | D13_tp50_s2 | 1,680 | +6.6 [-4.4, +17.5] | +1.6 [-20.3, +21.7] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, put sale | X | CSP | D0_dte21 | 1,666 | +823.8 [+756.2, +891.1] | +760.2 [+581.3, +919.8] | — [—, —] | — | carry, not setup |
| index_etf | Baseline: every Monday, straddle | L | STR | D1_t5 | 1,680 | -41.0 [-53.2, -29.4] | -107.9 [-259.4, +49.2] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | P | STG | D1_t5 | 1,674 | -15.5 [-26.9, -3.0] | -12.5 [-31.9, +8.7] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | P | STR | D1_t5 | 1,681 | -22.4 [-37.3, -7.7] | -20.8 [-47.6, +3.4] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | S | STG | D1_t5 | 1,658 | -15.7 [-28.4, -1.9] | -19.0 [-41.2, +4.3] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | S | STR | D1_t5 | 1,680 | -24.0 [-40.5, -7.8] | -25.9 [-53.8, +3.3] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | W | STG | D0_dte21 | 1,663 | -7.0 [-12.1, -1.5] | -9.0 [-17.8, +0.5] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | W | STR | D0_dte21 | 1,674 | -12.1 [-18.5, -5.1] | -10.4 [-40.1, +22.0] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | X | STG | D2_s50_t100 | 1,522 | +22.3 [-53.1, +106.1] | -92.8 [-198.6, +24.0] | — [—, —] | — | inconclusive |
| index_etf | Baseline: every Monday, straddle | X | STR | D0_expiry | 1,628 | +494.8 [+325.6, +670.2] | +266.8 [+79.2, +475.4] | — [—, —] | — | carry, not setup |
| index_etf | Bounce (daily) | L | CPS | D0_expiry | 34 | +28.3 [+4.4, +50.8] | — [—, —] | +24.1 [-2.6, +47.9] | — | insufficient |
| index_etf | Bounce (daily) | L | CSP | D0_dte21 | 34 | +602.6 [+463.7, +732.2] | — [—, —] | +195.5 [+8.2, +391.3] | — | insufficient |
| index_etf | Bounce (daily) | L | DCS | D0_expiry | 30 | +342.6 [+30.6, +640.1] | — [—, —] | +90.7 [-244.6, +411.5] | — | insufficient |
| index_etf | Bounce (daily) | L | DPS | D9_rsi_exit | 38 | -57.6 [-75.6, -39.5] | — [—, —] | -1.6 [-35.4, +30.8] | — | insufficient |
| index_etf | Bounce (daily) | L | LC-B | D7_dd40 | 30 | +1040.1 [+164.0, +1992.3] | — [—, —] | +729.2 [-151.2, +1679.0] | — | insufficient |
| index_etf | Bounce (daily) | L | LC-S | D0_expiry | 34 | +1064.2 [+241.0, +1827.1] | — [—, —] | +472.5 [-389.0, +1302.6] | — | insufficient |
| index_etf | Bounce (daily) | L | LP-B | D9_rsi_exit | 38 | -19.8 [-29.4, -9.4] | — [—, —] | +22.6 [+2.7, +42.9] | — | insufficient |
| index_etf | Bounce (daily) | L | LP-S | D9_rsi_exit | 38 | -66.0 [-99.8, -31.2] | — [—, —] | +17.0 [-49.8, +81.5] | — | insufficient |
| index_etf | Bounce (daily) | P | CPS | D0_ltd1 | 33 | +5.9 [-19.9, +26.2] | — [—, —] | +7.9 [-17.9, +32.5] | — | insufficient |
| index_etf | Bounce (daily) | P | CSP | D0_expiry | 34 | +313.4 [+174.2, +457.6] | — [—, —] | +158.0 [-27.5, +346.9] | — | insufficient |
| index_etf | Bounce (daily) | P | DCS | D9_rsi_exit | 34 | +1.1 [-29.4, +28.2] | — [—, —] | +12.1 [-27.1, +49.8] | — | insufficient |
| index_etf | Bounce (daily) | P | DPS | D9_rsi_exit | 38 | -28.8 [-42.4, -14.3] | — [—, —] | -0.3 [-33.7, +30.6] | — | insufficient |
| index_etf | Bounce (daily) | P | LC-B | D2_s35_t35 | 34 | +22.1 [-10.8, +55.7] | — [—, —] | +14.0 [-21.0, +50.1] | — | insufficient |
| index_etf | Bounce (daily) | P | LC-S | D9_rsi_exit | 34 | +28.8 [-36.5, +88.7] | — [—, —] | +19.6 [-65.2, +106.9] | — | insufficient |
| index_etf | Bounce (daily) | P | LP-B | D9_rsi_exit | 38 | -13.5 [-22.2, -3.7] | — [—, —] | +21.3 [-1.8, +44.3] | — | insufficient |
| index_etf | Bounce (daily) | P | LP-S | D9_rsi_exit | 38 | -39.9 [-67.4, -10.8] | — [—, —] | +18.5 [-50.1, +81.1] | — | insufficient |
| index_etf | Bounce (daily) | S | CPS | D13_tp50 | 31 | +5.5 [-8.3, +17.9] | — [—, —] | +8.2 [-7.5, +22.1] | — | insufficient |
| index_etf | Bounce (daily) | S | CSP | D13_tp50 | 34 | +160.8 [+80.3, +227.9] | — [—, —] | +128.7 [+27.1, +219.1] | — | insufficient |
| index_etf | Bounce (daily) | S | DCS | D9_rsi_exit | 33 | -2.7 [-36.2, +26.5] | — [—, —] | +10.2 [-25.3, +42.8] | — | insufficient |
| index_etf | Bounce (daily) | S | DPS | D9_rsi_exit | 37 | -28.5 [-41.9, -14.6] | — [—, —] | -11.7 [-36.9, +14.6] | — | insufficient |
| index_etf | Bounce (daily) | S | LC-B | D2_s35_t35 | 33 | +26.2 [-4.0, +58.4] | — [—, —] | +19.1 [-11.9, +52.3] | — | insufficient |
| index_etf | Bounce (daily) | S | LC-S | D9_rsi_exit | 34 | +25.9 [-37.0, +84.6] | — [—, —] | +29.3 [-43.0, +97.0] | — | insufficient |
| index_etf | Bounce (daily) | S | LP-B | D9_rsi_exit | 38 | -15.2 [-24.4, -5.5] | — [—, —] | -0.6 [-25.1, +21.8] | — | insufficient |
| index_etf | Bounce (daily) | S | LP-S | D9_rsi_exit | 38 | -41.5 [-68.8, -11.9] | — [—, —] | -20.4 [-80.8, +37.3] | — | insufficient |
| index_etf | Bounce (daily) | W | CPS | D0_expiry | 31 | +6.6 [-12.3, +19.0] | — [—, —] | +0.6 [-18.4, +17.2] | — | insufficient |
| index_etf | Bounce (daily) | W | CSP | D0_expiry | 32 | +114.7 [+35.9, +180.0] | — [—, —] | +109.7 [+22.5, +189.4] | — | insufficient |
| index_etf | Bounce (daily) | W | DCS | D0_dte21 | 31 | +11.3 [-23.4, +41.4] | — [—, —] | +19.1 [-16.5, +52.6] | — | insufficient |
| index_etf | Bounce (daily) | W | DPS | D0_dte21 | 37 | -23.7 [-37.4, -9.2] | — [—, —] | -9.3 [-28.3, +10.4] | — | insufficient |
| index_etf | Bounce (daily) | W | LC-B | D2_s50_t50_exp | 31 | +18.6 [-12.9, +48.3] | — [—, —] | +18.9 [-13.5, +50.9] | — | insufficient |
| index_etf | Bounce (daily) | W | LC-S | D2_s50_t50_exp | 34 | +50.2 [-32.9, +136.1] | — [—, —] | +36.4 [-47.0, +125.4] | — | insufficient |
| index_etf | Bounce (daily) | W | LP-B | D0_dte21 | 38 | -19.6 [-28.3, -11.2] | — [—, —] | -13.7 [-30.7, +1.8] | — | insufficient |
| index_etf | Bounce (daily) | W | LP-S | D0_dte21 | 38 | -43.1 [-69.0, -15.5] | — [—, —] | -29.5 [-70.7, +10.2] | — | insufficient |
| index_etf | Bounce (daily) | X | CPS | D0_expiry | 29 | -36.4 [-93.3, +11.8] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Bounce (daily) | X | CSP | D0_dte21 | 32 | +795.3 [+572.6, +1003.4] | — [—, —] | +20.0 [-260.1, +306.0] | — | insufficient |
| index_etf | Bounce (daily) | X | DCS | D2_s50_t50 | 25 | +122.5 [-71.6, +275.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Bounce (daily) | X | DPS | D1_t5 | 35 | -163.2 [-210.5, -119.6] | — [—, —] | +12.1 [-49.3, +69.5] | — | insufficient |
| index_etf | Bounce (daily) | X | LC-B | D3_p50at50_trail25 | 26 | +78.9 [-49.8, +196.5] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Bounce (daily) | X | LC-S | D0_expiry | 33 | +1514.4 [+297.8, +2854.5] | — [—, —] | +97.1 [-1232.6, +1446.7] | — | insufficient |
| index_etf | Bounce (daily) | X | LP-B | D1_t5 | 36 | -53.7 [-83.4, -23.5] | — [—, —] | +13.2 [-26.2, +51.9] | — | insufficient |
| index_etf | Bounce (daily) | X | LP-S | D9_rsi_exit | 38 | -195.1 [-256.5, -138.5] | — [—, —] | -2.5 [-84.1, +84.3] | — | insufficient |
| index_etf | Failed bounce (daily) | L | CPS | D0_expiry | 16 | +22.4 [+14.2, +32.0] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | CSP | D0_expiry | 16 | +631.9 [+505.8, +790.8] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | DCS | D0_expiry | 16 | +399.7 [-3.2, +827.1] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | DPS | D1_t5 | 4 | -150.8 [-361.8, -33.1] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | LC-B | D1_t5 | 16 | -8.5 [-42.4, +28.5] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | LC-S | D0_expiry | 16 | +679.5 [-90.0, +1557.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | LP-B | D1_t5 | 4 | -7.4 [-127.4, +143.6] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | L | LP-S | D1_t5 | 4 | -112.4 [-271.4, -10.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | CPS | D1_t5 | 16 | -8.5 [-14.2, -1.6] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | CSP | D13_tp50 | 16 | +139.6 [-11.6, +261.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | DCS | D1_t5 | 14 | +3.3 [-52.0, +75.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | DPS | D1_t5 | 4 | -102.0 [-257.8, -8.8] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | LC-B | D1_t5 | 14 | -15.3 [-48.5, +21.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | LC-S | D1_t5 | 16 | +10.4 [-85.0, +118.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | LP-B | D1_t5 | 4 | -42.1 [-100.4, -14.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | P | LP-S | D1_t5 | 4 | -125.6 [-245.4, -15.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | CPS | D0_dte21 | 16 | -6.0 [-14.5, +0.7] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | CSP | D13_tp50_dte21 | 16 | +44.9 [-18.7, +109.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | DCS | D1_t5 | 15 | -20.2 [-59.2, +22.6] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | DPS | D7_dd40 | 4 | +74.8 [-26.6, +256.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | LC-B | D2_s35_t35 | 16 | -9.7 [-42.6, +26.9] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | LC-S | D2_s35_t35 | 16 | -3.9 [-111.7, +118.7] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | LP-B | D7_dd40 | 4 | +89.8 [-2.8, +173.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | S | LP-S | D7_dd40 | 4 | +255.4 [+33.3, +512.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | CPS | D0_expiry | 16 | +2.6 [-27.0, +19.7] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | CSP | D0_expiry | 16 | +20.4 [-43.5, +66.3] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | DCS | D0_dte21 | 16 | -24.2 [-51.3, -3.9] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | DPS | D0_dte21 | 4 | -95.0 [-313.4, +25.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | LC-B | D0_dte21 | 16 | -16.5 [-24.8, -10.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | LC-S | D0_dte21 | 16 | -36.5 [-78.8, -7.1] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | LP-B | D0_dte21 | 4 | -80.0 [-250.7, -7.4] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | W | LP-S | D0_dte21 | 4 | -185.7 [-643.7, +50.6] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | CPS | D0_expiry | 16 | -9.7 [-54.7, +23.3] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | CSP | D1_t5 | 16 | -60.3 [-108.9, -15.3] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | DCS | D0_dte21 | 16 | +652.1 [+49.9, +1299.0] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | DPS | D1_t10 | 3 | +18.5 [-117.8, +221.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | LC-B | D0_dte21 | 16 | +1179.6 [+270.5, +2324.6] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | LC-S | D7_dd40 | 16 | +2615.3 [+714.7, +4791.1] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | LP-B | D1_t10 | 3 | +39.6 [-43.4, +199.6] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Failed bounce (daily) | X | LP-S | D1_t5 | 4 | -285.1 [-681.4, -55.7] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Breakout (daily) | L | CPS | D0_expiry | 450 | +10.2 [+3.2, +16.2] | +0.3 [-10.3, +9.7] | +4.4 [-3.2, +11.2] | — | carry, not setup |
| index_etf | Breakout (daily) | L | CSP | D0_dte21 | 451 | +447.8 [+360.1, +525.3] | +492.8 [+323.7, +629.7] | -55.4 [-143.9, +27.8] | finalist D0_dte21: hold-out +1076 [+821] on 85; not promoted (fails R2, R2b, R4) | failed on the hold-out |
| index_etf | Breakout (daily) | L | DCS | D0_expiry | 448 | +249.7 [+166.5, +333.9] | +300.6 [+159.6, +439.3] | +19.4 [-59.7, +106.7] | finalist D0_expiry: hold-out +815 [+405] on 85; not promoted (fails R2, R2b, R4) | failed on the hold-out |
| index_etf | Breakout (daily) | L | LC-B | D9_rsi_exit | 448 | +82.7 [+45.5, +128.6] | +45.3 [-47.5, +138.7] | +41.6 [+1.5, +87.9] | — | promising |
| index_etf | Breakout (daily) | L | LC-S | D0_ltd1 | 451 | +470.3 [+307.0, +641.6] | +609.3 [+311.2, +904.1] | -61.5 [-227.1, +109.3] | finalist D0_ltd1: hold-out +891 [+235] on 85; not promoted (fails R2, R2b, R4) | failed on the hold-out |
| index_etf | Breakout (daily) | L | LP-B | D1_t5 | 195 | -26.8 [-63.2, +18.2] | -20.7 [-104.7, +81.0] | -3.4 [-41.1, +42.0] | — | inconclusive |
| index_etf | Breakout (daily) | L | LP-S | D1_t5 | 198 | -74.6 [-157.4, +23.6] | -48.2 [-240.0, +162.6] | -14.6 [-100.0, +87.4] | — | inconclusive |
| index_etf | Breakout (daily) | P | CPS | D0_expiry | 449 | +6.6 [+0.5, +12.0] | -2.1 [-12.8, +7.3] | +5.8 [-0.6, +12.6] | — | inconclusive |
| index_etf | Breakout (daily) | P | CSP | D13_s2 | 451 | +113.0 [+62.3, +165.6] | +82.8 [-91.9, +228.1] | +7.0 [-47.7, +62.9] | — | carry, not setup |
| index_etf | Breakout (daily) | P | LC-B | D1_t20 | 449 | +20.6 [-0.0, +43.4] | +2.2 [-19.7, +23.6] | -0.5 [-22.6, +23.5] | — | inconclusive |
| index_etf | Breakout (daily) | P | LC-S | D2_s50_t50 | 451 | +70.7 [+31.3, +113.0] | +52.8 [-29.6, +136.1] | +36.2 [-6.4, +81.4] | — | carry, not setup |
| index_etf | Breakout (daily) | P | LP-B | D1_t5 | 195 | -17.8 [-55.7, +30.2] | -29.0 [-100.1, +44.9] | +3.3 [-34.5, +52.0] | — | inconclusive |
| index_etf | Breakout (daily) | P | LP-S | D1_t5 | 199 | -50.0 [-128.5, +46.1] | -20.8 [-202.3, +185.9] | -9.7 [-92.2, +89.8] | — | inconclusive |
| index_etf | Breakout (daily) | S | CPS | D0_expiry | 451 | +1.1 [-6.4, +8.1] | -10.7 [-26.4, +2.1] | -0.1 [-8.1, +7.4] | — | inconclusive |
| index_etf | Breakout (daily) | S | CSP | D13_s2 | 450 | +59.8 [+25.3, +94.3] | +34.8 [-86.8, +125.6] | +15.7 [-19.7, +55.0] | — | carry, not setup |
| index_etf | Breakout (daily) | S | DCS | D0_expiry | 444 | +34.5 [+1.4, +71.2] | +48.3 [-10.6, +101.3] | -6.2 [-42.0, +30.6] | — | carry, not setup |
| index_etf | Breakout (daily) | S | LC-B | D2_s50_t50 | 450 | +2.7 [-4.7, +11.6] | +2.8 [-14.0, +21.5] | +2.5 [-5.9, +12.1] | — | inconclusive |
| index_etf | Breakout (daily) | S | LC-S | D2_s50_t50_exp | 451 | +31.0 [+0.7, +62.1] | +16.9 [-35.4, +75.7] | +18.6 [-14.5, +53.0] | — | carry, not setup |
| index_etf | Breakout (daily) | S | LP-B | D2_s35_t35 | 195 | -11.8 [-34.6, +14.0] | -20.0 [-76.2, +37.7] | +2.9 [-20.3, +29.4] | — | inconclusive |
| index_etf | Breakout (daily) | S | LP-S | D5_thesis | 198 | -73.8 [-124.0, -15.1] | -90.1 [-209.9, +46.3] | -19.3 [-80.1, +47.3] | — | inconclusive |
| index_etf | Breakout (daily) | W | CPS | D0_expiry | 442 | +4.2 [-0.6, +8.8] | +2.7 [-5.2, +9.6] | +10.1 [+4.3, +16.2] | — | inconclusive |
| index_etf | Breakout (daily) | W | CSP | D0_ltd1 | 445 | +22.3 [+11.7, +32.5] | +30.6 [+2.0, +55.7] | +21.8 [+8.7, +34.2] | finalist D0_ltd1: hold-out +77 [+44] on 103; not promoted (fails R2) | failed on the hold-out |
| index_etf | Breakout (daily) | W | DCS | D2_s50_t50_exp | 423 | -6.3 [-13.6, +1.3] | -8.2 [-23.9, +6.3] | +3.6 [-4.6, +11.8] | — | inconclusive |
| index_etf | Breakout (daily) | W | DPS | D2_s50_t50_exp | 193 | -7.1 [-28.3, +14.5] | -30.5 [-64.6, +6.1] | +9.4 [-12.5, +32.2] | — | inconclusive |
| index_etf | Breakout (daily) | W | LC-S | D2_s50_t50_exp | 447 | -0.5 [-16.0, +15.6] | -7.4 [-33.5, +19.1] | +3.5 [-13.9, +21.1] | — | inconclusive |
| index_etf | Breakout (daily) | W | LP-S | D2_s50_t50_exp | 197 | +19.2 [-26.2, +72.0] | +33.1 [-57.1, +135.5] | +33.7 [-15.5, +88.3] | — | inconclusive |
| index_etf | Breakout (daily) | X | CSP | D0_dte21 | 447 | +834.6 [+731.9, +944.5] | +721.8 [+433.7, +971.3] | -10.3 [-118.9, +99.7] | finalist D0_dte21: hold-out +2079 [+1922] on 71; not promoted (fails R2, R4) | failed on the hold-out |
| index_etf | Breakout (daily) | X | DCS | D0_expiry | 418 | +474.7 [+359.7, +592.0] | +583.5 [+356.6, +801.3] | -10.4 [-130.2, +121.7] | finalist D0_expiry: hold-out +2559 [+2143] on 68; not promoted (fails R2, R2b, R4) | failed on the hold-out |
| index_etf | Breakout (daily) | X | LC-B | D7_dd40 | 419 | +725.7 [+551.6, +902.9] | +1069.7 [+748.5, +1397.4] | -114.3 [-290.2, +79.5] | finalist D7_dd40: hold-out +1678 [+418] on 68; not promoted (fails R2, R2b, R4) | failed on the hold-out |
| index_etf | Breakout (daily) | X | LC-S | D0_ltd1 | 450 | +1476.6 [+1165.2, +1817.1] | +2016.7 [+1447.0, +2569.4] | +56.1 [-257.9, +392.9] | finalist D0_ltd1: hold-out +3554 [+2578] on 72; not promoted (fails R2, R2b, R4) | failed on the hold-out |
| index_etf | Failed breakout (daily) | L | CPS | D0_dte21 | 99 | +23.1 [+13.4, +33.0] | — [—, —] | +14.4 [+4.0, +25.3] | — | insufficient |
| index_etf | Failed breakout (daily) | L | CSP | D0_dte21 | 99 | +598.3 [+467.2, +734.3] | — [—, —] | +100.8 [-48.3, +250.2] | — | insufficient |
| index_etf | Failed breakout (daily) | L | DCS | D0_expiry | 97 | +270.7 [+71.0, +470.6] | — [—, —] | +64.6 [-143.7, +263.9] | — | insufficient |
| index_etf | Failed breakout (daily) | L | LC-B | D7_dd40 | 97 | +447.5 [+100.1, +851.1] | — [—, —] | +149.8 [-224.2, +558.7] | — | insufficient |
| index_etf | Failed breakout (daily) | L | LC-S | D0_expiry | 99 | +640.6 [+212.9, +1063.4] | — [—, —] | +85.0 [-352.5, +518.8] | — | insufficient |
| index_etf | Failed breakout (daily) | P | CPS | D0_ltd1 | 99 | +13.1 [+3.6, +21.3] | — [—, —] | +18.9 [+6.2, +30.8] | — | insufficient |
| index_etf | Failed breakout (daily) | P | CSP | D13_tp50_dte21 | 99 | +209.5 [+173.2, +249.9] | — [—, —] | +119.8 [+63.2, +177.9] | — | insufficient |
| index_etf | Failed breakout (daily) | P | DCS | D7_dd40 | 99 | +153.0 [+58.4, +253.6] | — [—, —] | +145.9 [+47.7, +252.2] | — | insufficient |
| index_etf | Failed breakout (daily) | P | LC-B | D7_dd40 | 99 | +117.1 [+39.6, +199.6] | — [—, —] | +91.5 [+7.2, +173.9] | — | insufficient |
| index_etf | Failed breakout (daily) | P | LC-S | D7_dd40 | 99 | +319.7 [+133.0, +512.6] | — [—, —] | +264.4 [+70.3, +473.0] | — | insufficient |
| index_etf | Failed breakout (daily) | S | CPS | D13_tp50 | 99 | +10.8 [+6.9, +13.8] | — [—, —] | +14.1 [+7.5, +20.7] | — | insufficient |
| index_etf | Failed breakout (daily) | S | CSP | D0_ltd1 | 100 | +215.3 [+156.5, +277.1] | — [—, —] | +124.7 [+55.0, +195.2] | — | promising |
| index_etf | Failed breakout (daily) | S | DCS | D2_s35_t35 | 98 | +5.9 [-25.3, +36.3] | — [—, —] | +7.2 [-27.3, +40.0] | — | insufficient |
| index_etf | Failed breakout (daily) | S | LC-B | D2_s50_t50_exp | 98 | +15.2 [-5.7, +38.7] | — [—, —] | +10.2 [-13.6, +35.5] | — | insufficient |
| index_etf | Failed breakout (daily) | S | LC-S | D2_s50_t50 | 100 | +41.5 [-33.9, +114.9] | — [—, —] | +13.4 [-67.1, +92.1] | — | inconclusive |
| index_etf | Failed breakout (daily) | S | LP-B | D9_rsi_exit | 186 | -14.7 [-25.9, -0.4] | -16.3 [-43.2, +18.9] | +11.1 [-3.2, +25.8] | — | inconclusive |
| index_etf | Failed breakout (daily) | S | LP-S | D9_rsi_exit | 186 | -36.9 [-63.4, -5.9] | -46.3 [-110.3, +29.2] | +18.2 [-14.5, +51.8] | — | inconclusive |
| index_etf | Failed breakout (daily) | W | CPS | D13_s2 | 97 | -0.4 [-11.4, +10.0] | — [—, —] | +3.4 [-8.6, +15.0] | — | insufficient |
| index_etf | Failed breakout (daily) | W | CSP | D0_dte21 | 98 | +3.9 [-32.1, +34.5] | — [—, —] | -0.8 [-37.1, +32.0] | — | insufficient |
| index_etf | Failed breakout (daily) | W | DCS | D2_s50_t50_exp | 95 | +5.3 [-23.2, +34.8] | — [—, —] | +4.1 [-26.3, +33.2] | — | insufficient |
| index_etf | Failed breakout (daily) | W | LC-B | D2_s50_t50_exp | 95 | +22.0 [-1.4, +49.1] | — [—, —] | +16.4 [-9.9, +42.9] | — | insufficient |
| index_etf | Failed breakout (daily) | W | LC-S | D2_s50_t50_exp | 98 | +44.3 [-16.5, +110.7] | — [—, —] | +27.1 [-39.3, +92.9] | — | insufficient |
| index_etf | Failed breakout (daily) | X | CPS | D0_dte21 | 91 | +11.9 [-12.7, +32.0] | — [—, —] | +20.0 [-5.0, +42.0] | — | insufficient |
| index_etf | Failed breakout (daily) | X | CSP | D0_dte21 | 97 | +889.6 [+705.8, +1068.3] | — [—, —] | +60.7 [-143.7, +271.4] | — | insufficient |
| index_etf | Failed breakout (daily) | X | DCS | D0_expiry | 83 | +517.3 [+239.3, +766.4] | — [—, —] | +98.0 [-188.8, +390.4] | — | insufficient |
| index_etf | Failed breakout (daily) | X | LC-B | D0_expiry | 84 | +515.8 [+196.6, +858.9] | — [—, —] | -119.7 [-448.2, +253.2] | — | insufficient |
| index_etf | Failed breakout (daily) | X | LC-S | D0_expiry | 98 | +1284.0 [+728.0, +1871.2] | — [—, —] | -202.6 [-829.4, +457.7] | — | insufficient |
| index_etf | Day before the Fed | L | STG | D1_t5 | 72 | -29.5 [-96.4, +31.8] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | L | STR | D1_t5 | 72 | -51.2 [-139.6, +41.9] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | P | STG | D1_t5 | 72 | -2.3 [-70.5, +64.2] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | P | STR | D1_t5 | 72 | -12.5 [-104.4, +77.1] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | S | STG | D2_s35_t35 | 72 | +9.5 [-73.0, +87.1] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | S | STR | D1_t5 | 72 | -10.0 [-118.3, +100.0] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | W | STG | D0_dte21 | 72 | +2.2 [-44.5, +68.7] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | W | STR | D0_ltd1 | 72 | +75.2 [-65.7, +228.9] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | X | STG | D1_t5 | 66 | -143.9 [-215.8, -74.5] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Day before the Fed | X | STR | D1_t5 | 70 | -206.5 [-305.0, -100.9] | — [—, —] | — [—, —] | — | insufficient |
| index_etf | Trend pullback (daily) | L | CPS | D0_expiry | 1,072 | +6.6 [+2.0, +10.5] | -7.8 [-16.2, +0.5] | -0.9 [-5.9, +3.4] | — | inconclusive |
| index_etf | Trend pullback (daily) | L | CSP | D0_dte21 | 1,073 | +401.0 [+336.1, +460.2] | +377.2 [+185.8, +557.7] | -90.3 [-149.8, -34.0] | finalist D0_dte21: hold-out +975 [+842] on 335; not promoted (fails R2, R2b) | failed on the hold-out |
| index_etf | Trend pullback (daily) | L | DCS | D0_expiry | 1,071 | +252.6 [+199.8, +309.4] | +224.5 [+127.1, +320.6] | +17.5 [-35.9, +72.0] | finalist D0_expiry: hold-out +781 [+571] on 327; not promoted (fails R2, R2b) | failed on the hold-out |
| index_etf | Trend pullback (daily) | L | LC-B | D7_dd40 | 1,071 | +185.2 [+132.9, +239.1] | +233.9 [+133.3, +333.0] | -54.1 [-121.2, +11.9] | finalist D7_dd40: hold-out -52 [-205] on 327; not promoted (fails R1, R2, R2b, R3, R5) | failed on the hold-out |
| index_etf | Trend pullback (daily) | L | LC-S | D7_dd40 | 1,073 | +551.3 [+436.3, +661.2] | +636.0 [+413.5, +857.4] | -59.2 [-192.2, +66.9] | finalist D7_dd40: hold-out +1180 [+672] on 336; not promoted (fails R2, R2b) | failed on the hold-out |
| index_etf | Trend pullback (daily) | P | CSP | D13_s2 | 1,074 | +90.5 [+56.3, +122.6] | -26.0 [-151.2, +97.7] | -15.7 [-51.2, +17.4] | — | inconclusive |
| index_etf | Trend pullback (daily) | P | DCS | D0_ltd1 | 1,069 | +56.1 [+28.5, +83.0] | +66.0 [+12.1, +123.3] | -7.1 [-35.6, +19.6] | finalist D0_ltd1: hold-out -236 [-324] on 376; not promoted (fails R1, R2, R2b, R3, R5) | failed on the hold-out |
| index_etf | Trend pullback (daily) | P | LC-B | D0_expiry | 1,073 | +33.8 [+9.4, +59.2] | -1.5 [-25.3, +25.2] | -4.7 [-32.0, +21.5] | — | inconclusive |
| index_etf | Trend pullback (daily) | P | LC-S | D0_ltd1 | 1,074 | +128.9 [+73.7, +184.7] | +35.4 [-60.5, +134.2] | -28.2 [-85.5, +29.5] | — | carry, not setup |
| index_etf | Trend pullback (daily) | S | CSP | D1_t10 | 1,073 | +40.9 [+20.1, +58.6] | +28.2 [-19.2, +72.5] | +4.1 [-19.0, +26.1] | — | carry, not setup |
| index_etf | Trend pullback (daily) | S | DCS | D0_expiry | 1,066 | +37.8 [+15.2, +58.1] | +55.2 [+13.1, +98.5] | -9.2 [-32.4, +12.9] | finalist D0_expiry: hold-out -118 [-196] on 400; not promoted (fails R1, R2, R2b, R3, R5) | failed on the hold-out |
| index_etf | Trend pullback (daily) | S | LC-B | D1_t10 | 1,070 | +6.2 [-2.1, +14.4] | -2.0 [-25.7, +23.7] | -6.2 [-16.1, +3.3] | — | inconclusive |
| index_etf | Trend pullback (daily) | S | LC-S | D0_expiry | 1,071 | +68.6 [+27.4, +105.6] | +85.2 [+7.0, +163.1] | -29.0 [-73.3, +14.5] | finalist D0_expiry: hold-out -235 [-373] on 403; not promoted (fails R1, R2, R2b, R3, R5) | failed on the hold-out |
| index_etf | Trend pullback (daily) | W | CSP | D13_s2 | 1,049 | +6.0 [-3.7, +15.8] | +12.0 [-10.1, +32.3] | -0.3 [-11.6, +11.2] | — | inconclusive |
| index_etf | Trend pullback (daily) | W | DCS | D0_expiry | 996 | +2.8 [-7.8, +13.8] | +12.9 [-6.5, +33.2] | -2.4 [-13.7, +8.9] | — | inconclusive |
| index_etf | Trend pullback (daily) | W | LC-B | D0_expiry | 1,013 | +4.8 [-3.0, +13.6] | +7.9 [-6.5, +24.7] | +3.3 [-6.1, +13.1] | — | inconclusive |
| index_etf | Trend pullback (daily) | W | LC-S | D0_expiry | 1,059 | +14.4 [-4.4, +34.1] | +27.5 [-7.7, +63.9] | -0.0 [-20.0, +21.5] | — | inconclusive |
| index_etf | Trend pullback (daily) | W | LP-B | D0_dte21 | 194 | +2.4 [-18.5, +25.8] | -19.5 [-38.2, +0.9] | +8.4 [-12.6, +32.5] | — | inconclusive |
| index_etf | Trend pullback (daily) | W | LP-S | D0_dte21 | 194 | +8.5 [-46.7, +63.6] | -56.2 [-111.1, +2.0] | +22.5 [-32.9, +79.5] | — | inconclusive |
| index_etf | Trend pullback (daily) | X | CSP | D0_dte21 | 1,066 | +725.9 [+651.3, +792.8] | +734.5 [+574.0, +889.2] | -72.3 [-140.3, -8.8] | finalist D0_dte21: hold-out +1901 [+1818] on 257; not promoted (fails R2, R2b) | failed on the hold-out |
| index_etf | Trend pullback (daily) | X | DCS | D0_expiry | 968 | +321.9 [+245.8, +396.9] | +284.1 [+126.2, +445.7] | -127.9 [-208.9, -56.1] | finalist D0_expiry: hold-out +2144 [+1890] on 246; not promoted (fails R2, R2b) | failed on the hold-out |
| index_etf | Trend pullback (daily) | X | LC-B | D7_dd40 | 970 | +656.8 [+537.4, +776.0] | +1031.3 [+765.0, +1309.2] | -67.2 [-189.1, +60.1] | finalist D7_dd40: hold-out +501 [+103] on 247; not promoted (fails R2, R2b) | failed on the hold-out |
| index_etf | Trend pullback (daily) | X | LC-S | D0_ltd1 | 1,072 | +1110.0 [+908.3, +1285.3] | +1327.4 [+997.0, +1685.4] | -236.8 [-427.6, -48.5] | finalist D0_ltd1: hold-out +2638 [+2198] on 257; not promoted (fails R2, R2b) | failed on the hold-out |

