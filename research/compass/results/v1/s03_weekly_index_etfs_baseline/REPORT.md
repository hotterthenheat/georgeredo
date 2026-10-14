# S03 — owner baseline (Quick Scalps rule) on weekly expirations, SPY/QQQ/IWM 2017-06 → 2026-10 (stratified sessions)

Generated 2026-10-14 18:59 UTC from `results/v1/s03_weekly_index_etfs_baseline` (engine 0.1.0). Family `weekly_index`, symbols SPY, QQQ, IWM, 2017-06-01 → 2026-10-09. Fills: entry at the ask, exits at the bid, $0.70/contract/side, 1 contract; one open position per symbol: True.

## Signals and fills

| status | count |
|---|---|
| no_chain_data | 14884 |
| in_position | 2185 |
| filled | 818 |
| no_expiration_in_category | 21 |

## Headline (all filled trades)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| all | 818 | 376 | 1.27 | [-3.69, 6.25] | 37.7 % | 1.06 | -1,214 | 1,038 |

Median $ -9.40; average win 59.33 / loss -33.79; MAE mean 28.36 (p95 80.00); MFE mean 43.97; hold 117 min mean; commissions $1.40 per trade; gross-to-cost share 0.524; daily Sharpe (annualised) 0.41, Sortino 0.79; worst 5 trades [-227, -194, -168, -147, -147]; worst 5 days [-381, -329, -290, -228, -218].

## Matched random-entry baseline (5 seeds, same symbol/date/direction/contract rule/exits, random minute within ±45)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| baseline pooled | 4089 | — | 1.25 | [-3.05, 5.71] | 36.7 % | 1.07 | — | — |
| strategy | 818 | 376 | 1.27 | [-3.69, 6.25] | 37.7 % | 1.06 | -1,214 | 1,038 |

Strategy − baseline, paired by signal: n = 818, mean 0.02 [-2.11, 2.15] per contract against a mean round-trip cost (spread + fees) of 4.31.

### By year

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 2017 | 66 | 22 | -3.34 | [-5.70, -0.45] | 25.8 % | 0.64 | -273 | -220 |
| 2018 | 126 | 39 | 2.29 | [-7.34, 12.18] | 42.1 % | 1.16 | -472 | 289 |
| 2019 | 77 | 40 | -7.00 | [-14.41, 1.27] | 28.6 % | 0.59 | -622 | -539 |
| 2020 | 105 | 51 | 2.32 | [-15.70, 24.49] | 38.1 % | 1.09 | -605 | 244 |
| 2021 | 107 | 50 | -4.58 | [-14.33, 7.02] | 34.6 % | 0.80 | -933 | -490 |
| 2022 | 82 | 42 | -2.81 | [-19.12, 15.18] | 31.7 % | 0.91 | -911 | -230 |
| 2023 | 87 | 38 | 1.80 | [-7.17, 11.37] | 41.4 % | 1.09 | -245 | 157 |
| 2024 | 61 | 36 | 7.87 | [-5.36, 21.50] | 42.6 % | 1.49 | -363 | 480 |
| 2025 | 63 | 31 | 26.05 | [-4.21, 57.59] | 54.0 % | 2.07 | -376 | 1,641 |
| 2026 | 44 | 27 | -6.66 | [-22.96, 13.22] | 38.6 % | 0.80 | -392 | -293 |

### By symbol

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| IWM | 239 | 141 | 2.09 | [-3.13, 7.51] | 40.6 % | 1.15 | -631 | 500 |
| QQQ | 217 | 135 | -2.13 | [-12.52, 8.44] | 36.9 % | 0.92 | -1,953 | -463 |
| SPY | 362 | 221 | 2.76 | [-4.07, 10.26] | 36.2 % | 1.12 | -1,057 | 1,001 |

### By direction (+1 calls, −1 puts)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| -1 | 447 | 197 | 3.05 | [-4.67, 10.92] | 37.8 % | 1.13 | -1,377 | 1,365 |
| 1 | 371 | 201 | -0.88 | [-6.25, 4.75] | 37.5 % | 0.95 | -920 | -326 |

### By exit reason

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| data_end | 144 | 120 | 22.02 | [13.76, 30.74] | 67.4 % | 3.95 | -184 | 3,171 |
| invalidation | 44 | 36 | -40.03 | [-52.00, -29.39] | 2.3 % | 0.00 | -1,711 | -1,761 |
| stop | 70 | 58 | -47.87 | [-56.02, -40.89] | 0.0 % | 0.00 | -3,331 | -3,351 |
| target_2 | 143 | 97 | 79.53 | [69.98, 90.16] | 100.0 % | — | 0 | 11,373 |
| time | 3 | 3 | 6.60 | [-7.40, 24.60] | 66.7 % | 3.68 | 0 | 20 |
| vwap_loss | 414 | 242 | -20.32 | [-24.90, -15.63] | 15.7 % | 0.24 | -8,386 | -8,414 |

### By event day (FOMC/CPI/NFP; unknown before 2017-02)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| CPI | 49 | 22 | 5.88 | [-13.15, 26.19] | 51.0 % | 1.27 | -202 | 288 |
| FOMC | 18 | 13 | 12.49 | [-16.08, 47.33] | 44.4 % | 1.79 | -166 | 225 |
| NFP | 42 | 21 | -3.30 | [-20.95, 17.24] | 33.3 % | 0.84 | -602 | -139 |
| none | 709 | 320 | 0.94 | [-4.15, 6.58] | 36.8 % | 1.04 | -1,468 | 664 |


### Month-end sessions

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| False | 790 | 362 | 1.54 | [-3.52, 6.82] | 38.0 % | 1.07 | -1,051 | 1,219 |
| True | 28 | 14 | -6.45 | [-19.97, 7.95] | 28.6 % | 0.59 | -344 | -181 |

### By weekday (0 = Monday)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 0 | 132 | 64 | -8.96 | [-18.13, 0.69] | 31.1 % | 0.63 | -1,350 | -1,183 |
| 1 | 134 | 68 | -2.43 | [-15.92, 12.41] | 33.6 % | 0.90 | -1,200 | -326 |
| 2 | 166 | 80 | 11.35 | [0.90, 21.88] | 44.6 % | 1.70 | -263 | 1,885 |
| 3 | 220 | 86 | -6.65 | [-13.10, -0.14] | 38.2 % | 0.70 | -1,783 | -1,463 |
| 4 | 166 | 78 | 12.80 | [-0.13, 26.46] | 38.6 % | 1.66 | -369 | 2,126 |

### By entry hour bucket (0 = 09:30–10:29)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 0 | 127 | 106 | 6.12 | [-2.99, 15.77] | 34.6 % | 1.38 | -455 | 777 |
| 1 | 196 | 154 | -4.83 | [-12.15, 2.84] | 31.1 % | 0.78 | -1,307 | -947 |
| 2 | 147 | 114 | -0.57 | [-11.48, 11.36] | 40.1 % | 0.97 | -1,303 | -84 |
| 3 | 131 | 104 | 15.31 | [1.98, 31.33] | 45.8 % | 1.85 | -326 | 2,005 |
| 4 | 109 | 97 | 8.40 | [-3.59, 20.49] | 50.5 % | 1.45 | -408 | 915 |
| 5 | 105 | 89 | -16.07 | [-27.73, -3.72] | 26.7 % | 0.46 | -1,778 | -1,687 |
| 6 | 3 | 3 | 19.43 | [-45.40, 134.10] | 33.3 % | 1.77 | -45 | 58 |

