# Post-hoc diagnostics of the hold-to-expiry (E2) result

Not pre-registered and not used for any selection; computed after the TEST results were seen.  CIs: day-clustered, 5,000 draws, seed 7.

## A. Settlement price (SPY)

| period | days | mean (EOD close − 15:59-bar close) $ | median abs $ | p95 abs $ | max abs $ | median abs after-hours move to 17:15 mid $ | p95 abs | days with abs move > $0.50 | > $1.00 |
|---|---|---|---|---|---|---|---|---|---|
| TRAIN | 530 | +0.0120 | 0.030 | 0.080 | 0.38 | 0.275 | 1.030 | 112 | 29 |
| TEST | 441 | +0.0345 | 0.050 | 0.170 | 5.25 | 0.375 | 2.160 | 159 | 68 |

## B. E2 sensitivity (SPY): re-valuing expired legs

Columns: (1) as run, legs valued at the 15:59-bar close; (2) at the EOD close; (3) auto-exercise only (legs ITM at the EOD close are exercised, the delivered shares are closed at the 17:15 quote mid); (4) rational after-hours exercise (every leg is worth its intrinsic value at the 17:15 mid: holders exercise iff in the money after hours, shares closed there); (5) pessimistic: short legs owe max(intrinsic at the close, at the 17:15 mid).

| config | period | n | (1) as run | (2) EOD close | (3) auto-exercise, shares closed 17:15 | (4) rational after-hours exercise | (5) pessimistic |
|---|---|---|---|---|---|---|---|
| S0|14:05|tp0|st1|E2|F3 | TRAIN | 485 | +25.81 [+18.04, +33.62] | +25.49 [+17.66, +33.32] | +25.75 [+16.61, +35.13] | +19.98 [+11.65, +28.37] | +6.39 [-1.45, +14.18] |
| S0.5|14:05|tp0|st2|E2|F3 | TRAIN | 480 | +18.56 [+13.27, +23.98] | +18.42 [+13.14, +23.80] | +18.39 [+12.36, +24.66] | +13.59 [+7.52, +19.62] | +10.23 [+4.22, +16.29] |
| S0|14:05|tp0|st2|E2|F3 | TRAIN | 485 | +26.25 [+17.60, +34.82] | +25.88 [+17.19, +34.45] | +26.93 [+17.14, +36.95] | +21.16 [+12.07, +30.18] | +5.75 [-3.07, +14.42] |
| S0|14:05|tp0|st0|E2|F0 | TRAIN | 525 | +19.03 [+6.88, +30.13] | +18.71 [+6.61, +29.82] | +19.80 [+6.96, +31.79] | +14.26 [+1.92, +25.74] | -2.20 [-14.25, +9.02] |
| S1|14:05|tp0|st0|E2|F0 | TRAIN | 514 | +5.81 [-2.76, +12.75] | +5.77 [-2.78, +12.74] | +6.32 [-2.13, +13.40] | +3.57 [-5.03, +10.79] | +0.61 [-8.32, +8.07] |
| S0|14:05|tp0|st1|E2|F3 | TEST | 400 | +34.82 [+23.36, +46.84] | +34.13 [+22.69, +46.29] | +41.07 [+25.19, +57.58] | +23.59 [+10.26, +36.37] | +2.58 [-10.03, +15.13] |
| S0.5|14:05|tp0|st2|E2|F3 | TEST | 397 | +20.69 [+12.34, +28.99] | +19.93 [+11.57, +28.15] | +24.81 [+15.69, +33.80] | +11.32 [+1.45, +20.49] | +4.43 [-5.68, +13.69] |
| S0|14:05|tp0|st2|E2|F3 | TEST | 400 | +37.83 [+25.70, +50.09] | +37.22 [+24.98, +49.58] | +44.60 [+28.25, +62.45] | +25.61 [+11.01, +39.36] | +2.17 [-11.94, +15.95] |
| S0|14:05|tp0|st0|E2|F0 | TEST | 434 | +36.21 [+23.42, +48.85] | +35.56 [+22.74, +48.30] | +43.16 [+26.82, +61.13] | +24.54 [+10.28, +38.57] | -0.97 [-15.25, +12.99] |
| S1|14:05|tp0|st0|E2|F0 | TEST | 426 | +18.50 [+11.32, +24.99] | +17.99 [+10.80, +24.50] | +18.74 [+10.38, +26.53] | +14.06 [+6.09, +21.43] | +9.02 [+0.47, +16.83] |

## C. The last five minutes: ATM straddle quoted at 15:55 vs realized |S(16:00) − K|  ($ per straddle)

| ticker | period | days | mean mid $ | mean ask-sum $ | mean realized $ | mid − realized | ask − realized |
|---|---|---|---|---|---|---|---|
| SPY | TRAIN | 524 | 68.43 | 70.58 | 45.26 | +23.17 [+19.73, +26.73] | +25.32 [+21.87, +28.86] |
| SPY, realized at the 17:15 after-hours mid | TRAIN | 524 | 68.43 | 70.58 | 58.72 | +9.71 [+5.19, +14.34] | +11.85 [+7.31, +16.51] |
| SPY | TEST | 431 | 89.06 | 92.31 | 52.61 | +36.45 [+30.91, +42.30] | +39.70 [+34.13, +45.55] |
| SPY, realized at the 17:15 after-hours mid | TEST | 431 | 89.06 | 92.31 | 82.76 | +6.30 [-3.51, +14.69] | +9.55 [-0.20, +17.95] |
| QQQ | TRAIN | 499 | 70.93 | 73.81 | 40.78 | +30.15 [+25.59, +34.90] | +33.03 [+28.43, +37.86] |
| QQQ | TEST | 418 | 103.52 | 107.08 | 56.30 | +47.23 [+40.19, +54.76] | +50.79 [+43.71, +58.37] |
| IWM | TRAIN | 161 | 39.02 | 43.06 | 28.24 | +10.78 [+7.70, +13.81] | +14.81 [+11.75, +17.88] |
| IWM | TEST | 402 | 43.47 | 49.76 | 31.65 | +11.82 [+9.64, +14.03] | +18.11 [+15.94, +20.35] |

## D. Why E2 beats E1: straddle entered at 14:05, no TP, no stop, no filter ($ per straddle, mean [95 % CI])

E2 − E1 = Σ over legs E1 bought back at 15:55 of (ask − mid) + (mid − intrinsic at the 15:54-bar close) + (intrinsic at 15:55 − intrinsic at 16:00) + fee.

| ticker | period | n | E2 − E1 | half-spread | extrinsic at 15:55 | 15:55→16:00 intrinsic change | fees |
|---|---|---|---|---|---|---|---|
| SPY | TRAIN | 525 | +12.43 [+7.82, +16.83] | +3.75 [+3.50, +4.03] | +19.34 [+17.10, +21.72] | -11.75 [-16.05, -7.65] | 1.09 |
| SPY | TEST | 434 | +30.60 [+24.59, +36.66] | +7.27 [+6.60, +7.97] | +28.57 [+25.10, +32.38] | -6.40 [-11.82, -1.09] | 1.17 |
| QQQ | TRAIN | 507 | +16.95 [+12.03, +22.00] | +5.46 [+4.78, +6.26] | +22.94 [+19.58, +26.59] | -12.51 [-16.65, -8.60] | 1.06 |
| QQQ | TEST | 425 | +35.42 [+28.35, +42.56] | +10.04 [+8.91, +11.41] | +34.16 [+29.09, +39.81] | -9.94 [-15.91, -4.24] | 1.16 |
| IWM | TRAIN | 162 | +13.19 [+9.46, +16.67] | +4.65 [+4.37, +4.95] | +7.26 [+5.66, +8.98] | +0.35 [-3.12, +3.68] | 0.92 |
| IWM | TEST | 416 | +17.69 [+15.18, +20.20] | +10.05 [+9.30, +10.83] | +8.12 [+6.85, +9.44] | -1.42 [-3.75, +0.81] | 0.95 |
