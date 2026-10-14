# S01 — Quick Scalps baseline (owner parameters) on SPY/QQQ/IWM same-day expirations, 2022-11-11 → 2026-10-09

Generated 2026-10-14 16:11 UTC from `results/v1/s01_quick_scalps_0dte_baseline` (engine 0.1.0). Family `quick_scalps`, symbols SPY, QQQ, IWM, 2022-11-11 → 2026-10-09. Fills: entry at the ask, exits at the bid, $0.70/contract/side, 1 contract; one open position per symbol: True.

## Signals and fills

| status | count |
|---|---|
| in_position | 3100 |
| filled | 2886 |
| no_chain_data | 428 |
| no_expiration_in_category | 360 |
| no_eligible_contract | 108 |

## Headline (all filled trades)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| all | 2886 | 614 | -4.19 | [-5.68, -2.81] | 34.3 % | 0.73 | -12,320 | -12,081 |

Median $ -12.40; average win 32.62 / loss -23.41; MAE mean 19.61 (p95 50.00); MFE mean 22.05; hold 18 min mean; commissions $1.40 per trade; gross-to-cost share 0.503; daily Sharpe (annualised) -3.74, Sortino -4.82; worst 5 trades [-157, -154, -122, -116, -115]; worst 5 days [-478, -465, -412, -334, -329].

## Matched random-entry baseline (5 seeds, same symbol/date/direction/contract rule/exits, random minute within ±45)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| baseline pooled | 14218 | — | -2.18 | [-3.23, -1.15] | 37.2 % | 0.84 | — | — |
| strategy | 2886 | 614 | -4.19 | [-5.68, -2.81] | 34.3 % | 0.73 | -12,320 | -12,081 |

Strategy − baseline, paired by signal: n = 2885, mean -2.03 [-3.18, -0.90] per contract against a mean round-trip cost (spread + fees) of 2.79.

### By year

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 2022 | 74 | 17 | -1.74 | [-11.04, 5.53] | 37.8 % | 0.87 | -425 | -129 |
| 2023 | 578 | 146 | -4.87 | [-6.88, -2.85] | 31.5 % | 0.63 | -2,904 | -2,816 |
| 2024 | 725 | 157 | -3.22 | [-5.75, -0.76] | 35.2 % | 0.77 | -2,732 | -2,331 |
| 2025 | 834 | 165 | -4.39 | [-7.25, -1.78] | 35.5 % | 0.73 | -3,708 | -3,664 |
| 2026 | 675 | 129 | -4.65 | [-8.52, -1.06] | 33.9 % | 0.74 | -3,613 | -3,141 |

### By symbol

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| IWM | 685 | 274 | -3.46 | [-4.82, -2.20] | 33.3 % | 0.66 | -2,450 | -2,372 |
| QQQ | 1075 | 421 | -3.80 | [-6.13, -1.33] | 35.0 % | 0.79 | -4,610 | -4,087 |
| SPY | 1126 | 444 | -4.99 | [-6.97, -3.07] | 34.3 % | 0.69 | -5,838 | -5,621 |

### By direction (+1 calls, −1 puts)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| -1 | 1532 | 323 | -5.89 | [-8.23, -3.67] | 32.3 % | 0.68 | -9,156 | -9,019 |
| 1 | 1354 | 360 | -2.26 | [-3.86, -0.65] | 36.6 % | 0.81 | -3,421 | -3,062 |

### By exit reason

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| invalidation | 31 | 26 | -11.34 | [-15.86, -6.49] | 9.7 % | 0.13 | -360 | -351 |
| stop | 1498 | 499 | -22.43 | [-23.66, -21.21] | 3.9 % | 0.00 | -33,557 | -33,598 |
| target_2 | 760 | 348 | 38.75 | [36.18, 41.40] | 100.0 % | — | 0 | 29,448 |
| time | 155 | 120 | 13.90 | [11.52, 16.31] | 87.1 % | 10.58 | -33 | 2,155 |
| vwap_loss | 442 | 223 | -22.02 | [-24.84, -19.53] | 7.5 % | 0.03 | -9,700 | -9,734 |

### By event day (FOMC/CPI/NFP; unknown before 2017-02)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| CPI | 160 | 33 | -4.58 | [-11.50, 1.80] | 36.2 % | 0.68 | -679 | -732 |
| FOMC | 34 | 12 | -4.14 | [-14.45, 6.60] | 35.3 % | 0.78 | -223 | -141 |
| NFP | 219 | 35 | -1.30 | [-8.05, 5.85] | 37.0 % | 0.92 | -1,009 | -285 |
| none | 2473 | 534 | -4.42 | [-5.91, -2.97] | 33.9 % | 0.71 | -11,200 | -10,923 |

### By VIX open tercile (point-in-time, prior 252 sessions; 0 = warming up)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 1 | 1164 | 277 | -2.18 | [-4.10, -0.31] | 35.2 % | 0.82 | -3,315 | -2,538 |
| 2 | 727 | 147 | -3.30 | [-5.88, -0.80] | 34.3 % | 0.78 | -2,529 | -2,396 |
| 3 | 995 | 190 | -7.18 | [-10.04, -4.42] | 33.3 % | 0.64 | -7,150 | -7,147 |

### Month-end sessions

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| False | 2766 | 586 | -4.06 | [-5.55, -2.68] | 34.6 % | 0.74 | -11,453 | -11,223 |
| True | 120 | 28 | -7.15 | [-12.99, -1.92] | 28.3 % | 0.57 | -944 | -858 |

### By weekday (0 = Monday)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 0 | 367 | 96 | -5.75 | [-9.86, -2.05] | 33.2 % | 0.63 | -2,373 | -2,110 |
| 1 | 503 | 112 | -1.04 | [-4.40, 2.17] | 37.8 % | 0.93 | -1,036 | -525 |
| 2 | 513 | 118 | -4.39 | [-7.67, -1.30] | 34.9 % | 0.71 | -2,307 | -2,254 |
| 3 | 712 | 143 | -3.50 | [-6.16, -0.99] | 36.9 % | 0.76 | -2,582 | -2,495 |
| 4 | 791 | 145 | -5.94 | [-8.93, -2.84] | 29.8 % | 0.65 | -4,989 | -4,697 |

### By entry hour bucket (0 = 09:30–10:29)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 0 | 372 | 204 | -2.77 | [-7.73, 2.12] | 35.5 % | 0.84 | -1,596 | -1,032 |
| 1 | 643 | 326 | -4.87 | [-7.89, -1.35] | 34.1 % | 0.71 | -3,664 | -3,129 |
| 2 | 560 | 306 | -4.97 | [-9.06, -1.19] | 38.2 % | 0.70 | -2,892 | -2,786 |
| 3 | 572 | 300 | -1.18 | [-4.19, 1.70] | 36.4 % | 0.91 | -1,088 | -676 |
| 4 | 553 | 263 | -7.02 | [-9.61, -4.37] | 28.4 % | 0.52 | -4,043 | -3,881 |
| 5 | 186 | 132 | -3.10 | [-7.00, 0.55] | 32.3 % | 0.73 | -675 | -577 |

