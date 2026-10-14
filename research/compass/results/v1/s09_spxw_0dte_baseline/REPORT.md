# S09 — owner baseline (Quick Scalps) on SPXW same-day expirations, SPX signal with SPY volume proxy, 2022-05-13 → 2026-10-09

Generated 2026-10-14 16:55 UTC from `results/v1/s09_spxw_0dte_baseline` (engine 0.1.0). Family `quick_scalps`, symbols SPXW, 2022-05-13 → 2026-10-09. Fills: entry at the ask, exits at the bid, $0.70/contract/side, 1 contract; one open position per symbol: True.

## Signals and fills

| status | count |
|---|---|
| filled | 1229 |
| in_position | 1094 |
| no_eligible_contract | 1 |

## Headline (all filled trades)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| all | 1229 | 481 | -46.18 | [-63.19, -30.02] | 33.8 % | 0.70 | -57,412 | -56,761 |

Median $ -141.40; average win 317.77 / loss -231.74; MAE mean 199.24 (p95 470.00); MFE mean 203.61; hold 17 min mean; commissions $1.40 per trade; gross-to-cost share 0.031; daily Sharpe (annualised) -4.03, Sortino -6.28; worst 5 trades [-1001, -971, -971, -891, -851]; worst 5 days [-2247, -1863, -1593, -1264, -1233].

## Matched random-entry baseline (5 seeds, same symbol/date/direction/contract rule/exits, random minute within ±45)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| baseline pooled | 6139 | — | -22.15 | [-32.52, -11.03] | 37.6 % | 0.83 | — | — |
| strategy | 1229 | 481 | -46.18 | [-63.19, -30.02] | 33.8 % | 0.70 | -57,412 | -56,761 |

Strategy − baseline, paired by signal: n = 1229, mean -24.09 [-39.45, -9.28] per contract against a mean round-trip cost (spread + fees) of 18.79.

### By year

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 2022 | 159 | 72 | -91.62 | [-142.47, -43.90] | 27.7 % | 0.52 | -14,740 | -14,568 |
| 2023 | 300 | 107 | -29.22 | [-54.87, -4.62] | 34.3 % | 0.76 | -9,611 | -8,765 |
| 2024 | 279 | 106 | -15.80 | [-42.50, 9.95] | 37.6 % | 0.87 | -7,715 | -4,408 |
| 2025 | 266 | 109 | -58.93 | [-104.15, -18.39] | 33.8 % | 0.67 | -15,702 | -15,675 |
| 2026 | 225 | 87 | -59.31 | [-104.65, -12.63] | 32.4 % | 0.67 | -16,985 | -13,345 |

### By symbol

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| SPXW | 1229 | 481 | -46.18 | [-63.10, -30.02] | 33.8 % | 0.70 | -57,412 | -56,761 |

### By direction (+1 calls, −1 puts)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| -1 | 656 | 261 | -68.28 | [-94.68, -42.13] | 33.4 % | 0.63 | -45,626 | -44,793 |
| 1 | 573 | 228 | -20.89 | [-40.39, -1.64] | 34.2 % | 0.82 | -12,644 | -11,967 |

### By exit reason

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| invalidation | 30 | 24 | -81.07 | [-117.80, -51.10] | 16.7 % | 0.06 | -2,231 | -2,432 |
| stop | 648 | 366 | -222.06 | [-237.39, -207.54] | 6.8 % | 0.01 | -143,516 | -143,897 |
| target_2 | 322 | 212 | 385.76 | [360.52, 413.87] | 100.0 % | — | 0 | 124,214 |
| time | 41 | 39 | 108.23 | [72.09, 148.73] | 78.0 % | 6.98 | -244 | 4,438 |
| vwap_loss | 188 | 127 | -207.89 | [-236.09, -181.55] | 6.4 % | 0.03 | -38,522 | -39,083 |

### By event day (FOMC/CPI/NFP; unknown before 2017-02)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| CPI | 74 | 32 | -48.87 | [-111.32, 13.78] | 31.1 % | 0.65 | -2,958 | -3,616 |
| FOMC | 11 | 5 | -126.40 | [-229.73, -37.65] | 18.2 % | 0.38 | -1,296 | -1,390 |
| NFP | 73 | 30 | -113.32 | [-221.11, -21.00] | 28.8 % | 0.42 | -8,916 | -8,272 |
| none | 1071 | 414 | -40.60 | [-58.34, -22.55] | 34.5 % | 0.73 | -45,077 | -43,482 |

### By VIX open tercile (point-in-time, prior 252 sessions; 0 = warming up)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 1 | 494 | 183 | -17.32 | [-40.26, 6.46] | 36.4 % | 0.85 | -10,029 | -8,557 |
| 2 | 315 | 125 | -56.10 | [-89.17, -24.67] | 31.4 % | 0.64 | -19,248 | -17,671 |
| 3 | 420 | 173 | -72.70 | [-103.49, -40.38] | 32.4 % | 0.64 | -30,259 | -30,533 |

### Month-end sessions

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| False | 1169 | 455 | -44.17 | [-62.20, -27.03] | 34.0 % | 0.71 | -52,283 | -51,632 |
| True | 60 | 26 | -85.48 | [-150.95, -20.01] | 28.3 % | 0.51 | -5,038 | -5,129 |

### By weekday (0 = Monday)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 0 | 144 | 62 | -47.51 | [-97.40, 5.59] | 33.3 % | 0.68 | -8,123 | -6,842 |
| 1 | 219 | 89 | -41.73 | [-84.07, -1.02] | 35.2 % | 0.72 | -10,120 | -9,139 |
| 2 | 206 | 82 | -39.57 | [-78.17, -3.00] | 33.5 % | 0.72 | -8,135 | -8,151 |
| 3 | 305 | 122 | -18.66 | [-50.99, 10.55] | 38.4 % | 0.87 | -6,237 | -5,692 |
| 4 | 355 | 126 | -75.88 | [-112.20, -42.06] | 29.3 % | 0.57 | -27,224 | -26,937 |

### By entry hour bucket (0 = 09:30–10:29)

| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |
|---|---|---|---|---|---|---|---|---|
| 0 | 142 | 105 | -62.67 | [-117.90, -5.41] | 28.2 % | 0.67 | -9,185 | -8,899 |
| 1 | 258 | 191 | -89.67 | [-125.76, -52.51] | 28.3 % | 0.50 | -24,218 | -23,134 |
| 2 | 236 | 181 | -70.65 | [-113.19, -26.76] | 33.5 % | 0.60 | -16,291 | -16,673 |
| 3 | 226 | 180 | 4.15 | [-34.26, 42.11] | 42.0 % | 1.03 | -5,102 | 939 |
| 4 | 279 | 188 | -25.56 | [-56.40, 5.22] | 34.8 % | 0.79 | -7,882 | -7,131 |
| 5 | 88 | 80 | -21.17 | [-70.95, 30.48] | 35.2 % | 0.81 | -4,151 | -1,863 |

