# Paper tracker candidates — corrected cumulative report through 2026-10-21

Written 2026-10-22 00:40 UTC by `run_audit.py` (this folder). The method and every check behind these tables are in `AUDIT.md`. Corrections against `backtest_replay/backtest_2022-11-11_2026-10-09.md`: settled on the official close (not the 15:59 bar); session-sum statistics with session and moving-block bootstrap intervals (never trade-level); the periods apart — (i) development / training, (ii) the span the candidate was selected on, (iii) the untouched forward sessions from 2026-10-12. **The periods are never pooled into one figure.** NBBO legs, $0.65 a contract at the open, held to the official close, one lot.

## (i) Development / training — historical, not evidence for the candidate

| candidate · structure | period | sessions | trades | sessions traded / run | mean $ a trade | mean % of max risk | mean max risk | mean $ a session | session CI (iid sessions) | block-5 CI | block-20 CI | mean $ a trade, block-20 CI | session P&L acf lag 1..5 | effective N (acf / block-20) | total $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | 2022-11-11 → 2024-12-31 | 2358 | 525 / 530 | +3.47 | 2.16% | $173 | +15.46 | [-0.73, +31.74] | [-2.26, +31.58] | [-0.16, +29.96] | [-0.04, +6.68] | +0.04 -0.01 -0.09 -0.08 +0.01 | 730 / 606 | +8,193 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | 2022-11-11 → 2024-12-31 | 2095 | 530 / 530 | +16.59 | 4.74% | $399 | +65.58 | [+43.08, +87.28] | [+42.54, +89.37] | [+49.06, +91.11] | [+12.41, +23.06] | +0.01 -0.03 +0.01 -0.01 -0.02 | 580 / 629 | +34,755 |
| fly5 long call ±5 | i | 2022-11-11 → 2024-12-31 | 2095 | 530 / 530 | +9.60 | 2.96% | $406 | +37.95 | [+14.70, +59.95] | [+14.27, +61.80] | [+20.94, +64.30] | [+5.29, +16.25] | +0.02 -0.02 +0.01 -0.01 -0.02 | 549 / 596 | +20,116 |
| fly5 long put ±5 | i | 2022-11-11 → 2024-12-31 | 2097 | 530 / 530 | +7.43 | 2.43% | $408 | +29.42 | [+6.08, +51.25] | [+5.36, +53.67] | [+11.92, +56.63] | [+3.01, +14.31] | +0.01 -0.01 +0.01 +0.01 -0.01 | 515 / 542 | +15,591 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | 2022-11-11 → 2024-06-30 | 1823 | 403 / 405 | +2.42 | 1.53% | $171 | +10.88 | [-8.26, +29.12] | [-6.13, +27.35] | [-3.59, +22.52] | [-0.77, +4.99] | -0.03 -0.05 -0.08 -0.10 +0.06 | 658 / 857 | +4,407 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | 2024-07-01 → 2024-12-31 | 572 | 125 / 125 | +8.71 | 5.25% | $169 | +39.86 | [+4.36, +73.08] | [+2.07, +73.25] | [+16.68, +74.80] | [+3.68, +15.89] | +0.17 -0.10 -0.15 -0.12 -0.13 | 323 / 186 | +4,983 |

condor_d20's i-a are the frozen model's own training sessions (its deciles in-sample); i-b the half-year its cuts were set on.

| candidate · structure | period | mean $ a trade | mean % of max risk | win (trades) | profit factor | max drawdown $ (one lot, sessions) | worst session | longest losing streak (sessions) | full-loss share (≤ −95 % of max risk) | p1 session $ | p5 session $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | +3.47 | 2.16% | 80.2% | 1.22 | 2,849 | 2023-08-04 (-902) | 4 | 3.7% | -820 | -411 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | +16.59 | 4.74% | 69.3% | 1.78 | 2,399 | 2024-05-31 (-1,392) | 6 | 0.9% | -1,004 | -382 |
| fly5 long call ±5 | i | +9.60 | 2.96% | 65.4% | 1.40 | 3,137 | 2024-05-31 (-1,448) | 7 | 0.9% | -1,037 | -446 |
| fly5 long put ±5 | i | +7.43 | 2.43% | 63.3% | 1.30 | 3,543 | 2024-05-31 (-1,432) | 7 | 0.9% | -1,043 | -410 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | +2.42 | 1.53% | 76.9% | 1.14 | 1,769 | 2024-05-31 (-873) | 4 | 3.7% | -750 | -404 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | +8.71 | 5.25% | 83.9% | 1.62 | 1,618 | 2024-08-30 (-810) | 3 | 5.1% | -785 | -483 |

| candidate · structure | period | NBBO legs (as modeled) | +$0.01 a contract at the open | +$0.02 a contract at the open | every leg at its mid | package NBBO width $ (mean / median) | NBBO→mid slip $ | each $0.01 of package improvement | break-even: worse fill a contract | 15:58 exit, NBBO | 15:58 exit, +$0.01 open and close | 15:58 exit, +$0.02 open and close | 15:58 exit at mids | +1c: session-mean block-20 CI | +2c: session-mean block-20 CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | +3.47 | -0.53 | -4.53 | +5.48 | 4.01 / 4.00 | 2.01 | +1.00 | +0.87¢ | -4.83 | -11.26 | -17.70 | -0.83 | [-17.83, +12.05] | [-35.60, -5.82] |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | +16.59 | +12.59 | +8.59 | +19.04 | 4.89 / 5.00 | 2.45 | +1.00 | +4.15¢ | -7.81 | -14.03 | -20.25 | -1.65 | [+33.24, +75.26] | [+17.40, +59.59] |
| fly5 long call ±5 | i | +9.60 | +5.60 | +1.60 | +19.42 | 19.64 / 15.00 | 9.82 | +1.00 | +2.40¢ | -31.37 | -38.43 | -45.48 | -2.65 | [+5.10, +48.43] | [-10.73, +32.64] |
| fly5 long put ±5 | i | +7.43 | +3.43 | -0.57 | +19.45 | 24.04 / 18.00 | 12.02 | +1.00 | +1.86¢ | -36.63 | -43.79 | -50.95 | -1.81 | [-3.93, +40.72] | [-19.71, +24.81] |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | +2.42 | -1.58 | -5.58 | +4.47 | 4.10 / 4.00 | 2.05 | +1.00 | +0.60¢ | -5.66 | -12.13 | -18.61 | -1.61 | [-21.54, +4.39] | [-39.44, -13.60] |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | +8.71 | +4.71 | +0.71 | +10.76 | 4.09 / 4.00 | 2.05 | +1.00 | +2.18¢ | -6.62 | -13.32 | -20.01 | -2.22 | [-1.49, +56.03] | [-19.07, +37.07] |

## (ii) Selection read — historical, the span each candidate was chosen on (not an out-of-sample confirmation)

| candidate · structure | period | sessions | trades | sessions traded / run | mean $ a trade | mean % of max risk | mean max risk | mean $ a session | session CI (iid sessions) | block-5 CI | block-20 CI | mean $ a trade, block-20 CI | session P&L acf lag 1..5 | effective N (acf / block-20) | total $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | 2025-01-02 → 2026-10-09 | 2068 | 439 / 441 | +4.10 | 2.46% | $167 | +19.25 | [-2.26, +38.82] | [-3.06, +38.70] | [-2.40, +38.40] | [-0.51, +8.15] | -0.02 -0.01 -0.01 +0.07 -0.03 | 440 / 464 | +8,487 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | 2025-01-02 → 2026-10-09 | 1757 | 441 / 441 | +16.20 | 5.42% | $366 | +64.54 | [+34.13, +92.37] | [+37.19, +92.60] | [+40.67, +89.07] | [+10.26, +22.36] | -0.02 -0.05 +0.01 -0.05 -0.06 | 663 / 663 | +28,463 |
| fly5 long call ±5 | ii | 2025-01-02 → 2026-10-09 | 1757 | 441 / 441 | +7.13 | 2.93% | $375 | +28.41 | [-3.04, +56.35] | [+0.40, +56.54] | [+3.06, +53.91] | [+0.77, +13.53] | -0.01 -0.05 +0.01 -0.05 -0.06 | 639 / 622 | +12,531 |
| fly5 long put ±5 | ii | 2025-01-02 → 2026-10-09 | 1757 | 441 / 441 | +5.58 | 2.53% | $377 | +22.22 | [-9.01, +49.80] | [-5.47, +50.67] | [-4.15, +47.72] | [-1.04, +12.00] | -0.02 -0.05 +0.02 -0.04 -0.06 | 630 / 607 | +9,800 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | 2025-01-02 → 2026-10-09 | 2090 | 440 / 441 | +7.67 | 4.68% | $168 | +36.36 | [+18.25, +53.22] | [+17.68, +53.66] | [+18.42, +51.77] | [+3.87, +10.89] | +0.02 -0.01 +0.02 +0.04 -0.08 | 453 / 466 | +16,034 |

| candidate · structure | period | mean $ a trade | mean % of max risk | win (trades) | profit factor | max drawdown $ (one lot, sessions) | worst session | longest losing streak (sessions) | full-loss share (≤ −95 % of max risk) | p1 session $ | p5 session $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | +4.10 | 2.46% | 80.4% | 1.22 | 2,910 | 2025-01-31 (-888) | 4 | 7.0% | -791 | -522 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | +16.20 | 5.42% | 63.5% | 1.55 | 2,902 | 2025-03-04 (-1,133) | 4 | 2.1% | -887 | -567 |
| fly5 long call ±5 | ii | +7.13 | 2.93% | 59.5% | 1.21 | 5,115 | 2025-03-04 (-1,168) | 4 | 2.1% | -901 | -613 |
| fly5 long put ±5 | ii | +5.58 | 2.53% | 58.6% | 1.16 | 5,553 | 2025-03-04 (-1,240) | 5 | 2.1% | -908 | -610 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | +7.67 | 4.68% | 82.1% | 1.51 | 2,292 | 2026-09-30 (-843) | 4 | 4.7% | -760 | -390 |

| candidate · structure | period | NBBO legs (as modeled) | +$0.01 a contract at the open | +$0.02 a contract at the open | every leg at its mid | package NBBO width $ (mean / median) | NBBO→mid slip $ | each $0.01 of package improvement | break-even: worse fill a contract | 15:58 exit, NBBO | 15:58 exit, +$0.01 open and close | 15:58 exit, +$0.02 open and close | 15:58 exit at mids | +1c: session-mean block-20 CI | +2c: session-mean block-20 CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | +4.10 | +0.10 | -3.90 | +6.16 | 4.12 / 4.00 | 2.06 | +1.00 | +1.03¢ | -7.52 | -14.62 | -21.71 | -2.81 | [-21.15, +19.61] | [-40.00, +0.69] |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | +16.20 | +12.20 | +8.20 | +18.62 | 4.85 / 4.00 | 2.42 | +1.00 | +4.05¢ | -13.77 | -20.72 | -27.67 | -6.53 | [+24.81, +73.13] | [+8.96, +57.19] |
| fly5 long call ±5 | ii | +7.13 | +3.13 | -0.87 | +18.78 | 23.29 / 17.00 | 11.65 | +1.00 | +1.78¢ | -35.98 | -43.25 | -50.52 | -7.59 | [-12.84, +37.95] | [-28.80, +21.99] |
| fly5 long put ±5 | ii | +5.58 | +1.58 | -2.42 | +19.44 | 27.72 / 20.00 | 13.86 | +1.00 | +1.39¢ | -39.19 | -46.87 | -54.55 | -6.15 | [-20.11, +31.84] | [-36.06, +15.95] |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | +7.67 | +3.67 | -0.33 | +9.77 | 4.20 / 4.00 | 2.10 | +1.00 | +1.92¢ | -5.54 | -12.79 | -20.05 | -1.03 | [-0.61, +32.71] | [-19.42, +13.79] |

condor_d20, D1 against the unconditional condor (official close), by period:

| period | sessions kept | n | D1 trades / sessions | D1 mean $ | all trades mean $ (same minutes) | D2–D10 mean $ | time-matched lift $ | iid-session CI | block-20 CI | lift % of risk | block-20 CI (pp) | session-matched lift $ | sessions with D1 and non-D1 | iid-session CI | block-20 CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| i-a | all sessions | 405 | 459 / 226 | +12.05 | +2.42 | -0.83 | +9.16 | [+4.72, +13.65] | [+4.73, +13.86] | 5.27% | [+2.61, +8.19] | +6.22 | 205 | [+1.10, +11.64] | [+2.18, +11.47] |
| i-a | without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP) | 345 | 383 / 196 | +11.66 | +1.75 | -1.53 | +9.00 | [+4.34, +13.83] | [+4.77, +13.78] | 5.07% | [+2.56, +7.95] | +4.89 | 177 | [+0.65, +9.80] | [+1.27, +9.00] |
| i-a | without FOMC decision days only | 392 | 425 / 213 | +13.08 | +3.02 | -0.19 | +9.20 | [+5.06, +13.68] | [+4.87, +14.08] | 5.21% | [+2.61, +8.20] | +4.39 | 192 | [+0.37, +8.92] | [+1.05, +8.34] |
| i-a | scheduled-event sessions only | 60 | 76 / 30 | +14.06 | +6.03 | +3.10 | +7.88 | [-6.09, +20.90] | [-6.66, +22.62] | 4.75% | [-4.60, +13.27] | +12.54 | 28 | [-5.18, +32.91] | [-7.96, +33.73] |
| i-b | all sessions | 125 | 68 / 34 | +14.47 | +8.71 | +7.93 | +5.88 | [-15.91, +22.78] | [-3.49, +26.24] | 4.51% | [-1.68, +17.84] | -0.01 | 33 | [-13.85, +9.63] | [-7.32, +12.27] |
| i-b | without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP) | 106 | 50 / 28 | +15.84 | +9.36 | +8.62 | +6.80 | [-16.78, +21.84] | [-2.07, +23.04] | 5.00% | [-0.35, +15.13] | -3.19 | 27 | [-22.40, +9.58] | [-10.50, +15.54] |
| i-b | without FOMC decision days only | 121 | 54 / 30 | +16.70 | +9.16 | +8.34 | +7.60 | [-12.62, +22.30] | [+1.04, +23.43] | 5.40% | [+1.29, +15.15] | -2.05 | 29 | [-18.52, +10.25] | [-10.52, +14.39] |
| i-b | scheduled-event sessions only | 19 | 18 / 6 | +10.68 | +4.96 | +3.40 | +5.84 | [-52.34, +48.25] | — | 4.41% | — | +8.64 | 6 | [-0.45, +15.06] | — |
| ii | all sessions | 441 | 196 / 116 | +21.45 | +7.67 | +6.25 | +13.75 | [+7.32, +19.22] | [+5.82, +21.86] | 8.94% | [+3.89, +14.08] | +3.23 | 114 | [-2.73, +9.14] | [-4.18, +11.77] |
| ii | without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP) | 373 | 141 / 90 | +16.42 | +6.72 | +5.87 | +9.80 | [+1.66, +16.87] | [+2.15, +18.73] | 5.98% | [+1.11, +11.58] | +0.55 | 89 | [-6.82, +7.65] | [-8.18, +9.81] |
| ii | without FOMC decision days only | 427 | 161 / 103 | +16.79 | +7.38 | +6.56 | +9.40 | [+2.14, +15.74] | [+1.26, +17.78] | 5.86% | [+0.91, +11.06] | +1.58 | 102 | [-5.16, +7.82] | [-6.43, +11.10] |
| ii | scheduled-event sessions only | 68 | 55 / 26 | +34.35 | +12.83 | +8.47 | +20.88 | [+11.93, +29.49] | [+10.05, +37.52] | 14.55% | [+7.23, +25.76] | +10.53 | 25 | [+2.63, +21.33] | [-0.81, +35.95] |

## (iii) Untouched forward — 2026-10-12 → 2026-10-21

**Pending the fetch.** None of these sessions is in the stored Parquet yet; they are fetched on the owner's machine (`paper_tracker.py --fetch-theta --start 2026-10-12 --end 2026-10-21 --parquet-root R`), replayed (`--backtest` over the same days into the replay root), and this report is regenerated by the one command in `AUDIT.md` §9. Nothing below is pooled with (i) or (ii).

| sessions | count | dates |
|---|---|---|
| expected (NYSE full sessions) | 8 | 2026-10-12, 2026-10-13, 2026-10-14, 2026-10-15, 2026-10-16, 2026-10-19, 2026-10-20, 2026-10-21 |
| fetched (SPY and QQQ chains and bars on disk) | 0 | — |
| missing (not fetched) | 8 | 2026-10-12, 2026-10-13, 2026-10-14, 2026-10-15, 2026-10-16, 2026-10-19, 2026-10-20, 2026-10-21 |
| fetched without a VIX file (no-VIX decile primary) | 0 | — |
| replayed | 0 | — |
| excluded by the replay (holiday, half day, missing files) | 0 | — |

| candidate | complete sessions (every minute captured) | settled sessions | valid trades (tradable, settled) | invalid (untradable captures) | unmatched (a capture without its settle, or the reverse) | sessions settled without an official close on disk |
|---|---|---|---|---|---|---|
| condor_em1 | 0 | 0 | 0 | 0 | 0 | — |
| fly5 | 0 | 0 | 0 | 0 | 0 | — |
| condor_d20 | 0 | 0 | 0 | 0 | 0 | — |

Forward P&L, risk and D1 tables: pending the fetch (they will hold the same columns as (i) and (ii), for the forward sessions alone).

