# Paper tracker — cumulative report

Two parts, never pooled: the HISTORICAL sections (development and selection periods — written once, never changed by an append) and the FORWARD sessions (period iii, from 2026-10-12: untouched by any rule, model or choice), which the daily job (`scripts/daily_forward.py`) appends session by session. A forward session is appended only whole: every file fetched and verified, every capture settled on the official close.

<!-- cumulative:historical:begin -->
## Paper tracker — replay 2022-11-11 → 2026-10-09 (official-close settlement)

`paper-backtest-2026-10-22.2` on `paper-tracker-2026-10-22.3` (rules-2026-10-21.1, rules-c3-2026-10-21.1). Written 2026-10-22 02:37 UTC.

**What this is.** `paper_tracker.py --backtest` replays the stored 1-minute NBBO Parquet (`/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta`) through the live tracker's own code (`Tracker.capture`, `close_quotes` at 15:58 and `settle`, unchanged; each minute's rows adapted into the UW chain the live `Chain` reads). Fills: shorts at the bid, longs at the ask; $0.65 a contract at the open, nothing at expiry; the 15:58 exit pays $0.65 a contract closed (a long with no bid abandoned). **Spot** at a minute = the close of the bar stamped one minute earlier. **The settlement is the official close** (the audit's correction, the default since `paper-backtest-2026-10-22.2`): UW's daily bar (`r` row), else Theta's EOD daily bar; a session with neither settles on the 15:59 bar, labelled `1559_bar` and flagged below — never silently. SPXW on the last SPX print at or before 16:00. The audit's other corrections are in every row and every table: the period (never pooled), session sums with block-bootstrap intervals, the 15:58 exit for every candidate with the $0.01 / $0.02 stress at the open AND the exit, the expiry flags (stock left, pins, the post-market cross) and the after-hours cases. Rows carry `source = backtest-parquet` and live under their own root.

**Sessions**: 1021 weekdays; 9 half day, 41 holiday, 971 replayed.
- Holidays skipped (41): 2022-11-24, 2022-12-26, 2023-01-02, 2023-01-16, 2023-02-20, 2023-04-07, 2023-05-29, 2023-06-19, 2023-07-04, 2023-09-04, 2023-11-23, 2023-12-25, 2024-01-01, 2024-01-15, 2024-02-19, 2024-03-29, 2024-05-27, 2024-06-19, 2024-07-04, 2024-09-02, 2024-11-28, 2024-12-25, 2025-01-01, 2025-01-09, 2025-01-20, 2025-02-17, 2025-04-18, 2025-05-26, 2025-06-19, 2025-07-04, 2025-09-01, 2025-11-27, 2025-12-25, 2026-01-01, 2026-01-19, 2026-02-16, 2026-04-03, 2026-05-25, 2026-06-19, 2026-07-03, 2026-09-07
- Half days skipped (9): 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24

## Settlement: the official close

The options settle (and are auto-exercised) on the primary listing's official closing price, not the 15:59 bar. Each name-session's settlement source:

| name | sessions settled | official close (source) | 15:59 bar fallback (flagged) | official − 15:59 bar: mean / max |abs| | sessions where they differ by > $0.05 |
|---|---|---|---|---|---|
| QQQ | 968 | 968 (theta_eod 722, uw_1d 246) | 0 | 0.055 / 0.98 | 359 |
| SPY | 971 | 971 (theta_eod 723, uw_1d 248) | 0 | 0.054 / 5.25 | 352 |

No session fell back to the 15:59 bar.

## Results by period — never pooled

Official close, every leg at its own NBBO, $0.65 a contract at the open, nothing at expiry, one lot. A session's P&L is the sum of its trades (zero on a session the candidate ran and took no trade); intervals are percentile bootstraps over SESSIONS — iid and moving blocks of 20 consecutive sessions (2,000 draws, seeded; a block interval needs 60 sessions). fly5's three structures are one trade seen three ways; read them as one bet.

### condor_em1

- **i** — 2022-11-11 → 2024-12-31: development: hyp_b fit (the pre-registration picked the VIX-mid cell; this all-VIX parent ranked 4th)
- **ii** — 2025-01-02 → 2026-10-09: selection read: hyp_b OOS, read once; the tracked all-VIX form was written after it

| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | i | 530 | 2358 | 525 / 530 | +3.47 | [-0.04, +6.68] | 2.16% | +15.46 | [-0.73, +31.74] | [-0.16, +29.96] | +8,193 | 80.2% | 2,849 |
| condor | ii | 441 | 2068 | 439 / 441 | +4.10 | [-0.51, +8.15] | 2.46% | +19.25 | [-2.26, +38.82] | [-2.40, +38.40] | +8,487 | 80.4% | 2,910 |

### fly5

- **i** — 2022-11-11 → 2024-12-31: development: hyp_c fit (C pre-registered 15:00 iron ±2, call ±2, call ±5 — not these cells)
- **ii** — 2025-01-02 → 2026-10-09: selection read: hyp_c OOS — the iron ±5 found post hoc on it; the 15:30 call ±5 named after it (hyp_f)

| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iron | i | 530 | 2095 | 530 / 530 | +16.59 | [+12.41, +23.06] | 4.74% | +65.58 | [+43.08, +87.28] | [+49.06, +91.11] | +34,755 | 69.3% | 2,399 |
| iron | ii | 441 | 1757 | 441 / 441 | +16.20 | [+10.26, +22.36] | 5.42% | +64.54 | [+34.13, +92.37] | [+40.67, +89.07] | +28,463 | 63.5% | 2,902 |
| call | i | 530 | 2095 | 530 / 530 | +9.60 | [+5.29, +16.25] | 2.96% | +37.95 | [+14.70, +59.95] | [+20.94, +64.30] | +20,116 | 65.4% | 3,137 |
| call | ii | 441 | 1757 | 441 / 441 | +7.13 | [+0.77, +13.53] | 2.93% | +28.41 | [-3.04, +56.35] | [+3.06, +53.91] | +12,531 | 59.5% | 5,115 |
| put | i | 530 | 2097 | 530 / 530 | +7.43 | [+3.01, +14.31] | 2.43% | +29.42 | [+6.08, +51.25] | [+11.92, +56.63] | +15,591 | 63.3% | 3,543 |
| put | ii | 441 | 1757 | 441 / 441 | +5.58 | [-1.04, +12.00] | 2.53% | +22.22 | [-9.01, +49.80] | [-4.15, +47.72] | +9,800 | 58.6% | 5,553 |

### condor_d20

- **i-a** — 2022-11-11 → 2024-06-30: model training: the frozen t2 model was fit on these sessions — its deciles here are IN-SAMPLE
- **i-b** — 2024-07-01 → 2024-12-31: decile cuts: the nine cuts are this half-year's score quantiles (still hyp_e's fit period)
- **ii** — 2025-01-02 → 2026-10-09: selection read: hyp_e OOS — out of the model's training, read before the candidate was set

| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | i-a | 405 | 1823 | 403 / 405 | +2.42 | [-0.77, +4.99] | 1.53% | +10.88 | [-8.26, +29.12] | [-3.59, +22.52] | +4,407 | 76.9% | 1,769 |
| condor | i-b | 125 | 572 | 125 / 125 | +8.71 | [+3.68, +15.89] | 5.25% | +39.86 | [+4.36, +73.08] | [+16.68, +74.80] | +4,983 | 83.9% | 1,618 |
| condor | ii | 441 | 2090 | 440 / 441 | +7.67 | [+3.87, +10.89] | 4.68% | +36.36 | [+18.25, +53.22] | [+18.42, +51.77] | +16,034 | 82.1% | 2,292 |

## Hold to expiry against the 15:58 exit

The same trades, $ a structure. The 15:58 exit (the tracker's `close_quotes`, every candidate): a long sold at its bid, a short bought back at its ask, $0.65 a contract closed, a long with no bid abandoned (no fee); the stressed columns move every contract $0.01 / $0.02 against us at the open AND at the exit. Holding to expiry leaves stock on most in-the-money trades (the flags below); the 15:58 exit is the one a cash account can take.

| candidate · structure | period | trades | hold NBBO | hold +$0.01 | hold +$0.02 | hold at mids | 15:58 trades | 15:58 NBBO | 15:58 +$0.01 open & close | 15:58 +$0.02 open & close | 15:58 at mids | 15:58 NBBO: block-20 CI (trade) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | i | 2358 | +3.47 | -0.53 | -4.53 | +5.48 | 2358 | -4.83 | -11.26 | -17.70 | -0.83 | [-7.68, -1.73] |
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | ii | 2068 | +4.10 | +0.10 | -3.90 | +6.16 | 2062 | -7.52 | -14.62 | -21.71 | -2.81 | [-11.78, -3.96] |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | i | 2095 | +16.59 | +12.59 | +8.59 | +19.04 | 2095 | -7.81 | -14.03 | -20.25 | -1.65 | [-10.83, -3.12] |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | ii | 1757 | +16.20 | +12.20 | +8.20 | +18.62 | 1752 | -13.77 | -20.72 | -27.67 | -6.53 | [-19.88, -8.59] |
| fly5 long call ±5 | i | 2095 | +9.60 | +5.60 | +1.60 | +19.42 | 2095 | -31.37 | -38.43 | -45.48 | -2.65 | [-35.54, -24.83] |
| fly5 long call ±5 | ii | 1757 | +7.13 | +3.13 | -0.87 | +18.78 | 1754 | -35.98 | -43.25 | -50.52 | -7.59 | [-44.00, -28.17] |
| fly5 long put ±5 | i | 2097 | +7.43 | +3.43 | -0.57 | +19.45 | 2097 | -36.63 | -43.79 | -50.95 | -1.81 | [-41.80, -28.66] |
| fly5 long put ±5 | ii | 1757 | +5.58 | +1.58 | -2.42 | +19.44 | 1752 | -39.19 | -46.87 | -54.55 | -6.15 | [-48.16, -31.23] |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | i-a | 1823 | +2.42 | -1.58 | -5.58 | +4.47 | 1823 | -5.66 | -12.13 | -18.61 | -1.61 | [-8.39, -3.27] |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | i-b | 572 | +8.71 | +4.71 | +0.71 | +10.76 | 572 | -6.62 | -13.32 | -20.01 | -2.22 | [-11.75, +0.54] |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | ii | 2090 | +7.67 | +3.67 | -0.33 | +9.77 | 2084 | -5.54 | -12.79 | -20.05 | -1.03 | [-8.96, -2.94] |

## Expiry flags (held to the official close)

SPY and QQQ options are American and physically settled: OCC exercises every option in the money by $0.01 or more at the official close unless told otherwise, so a structure held to the close can leave shares (`stock_left`: the net of the exercises and assignments, by sign) — a 100-share position per lot against a few hundred dollars of modeled risk. The pins: the official close within $0.25 / $0.50 of a short strike (the writer does not know at 16:00 whether he is assigned). The post-market cross: UW's post-market bar (16:00–20:00, read from disk now — the window to the exercise cut-off is shorter, so an upper bound) took a short strike across the money; known only where that bar is on disk.

| candidate · structure | period | trades | stock left (long / short) | mean / max stock left $ | pin ≤ $0.25 | pin ≤ $0.50 | post-market cross (of trades with the bar) | settled on the 15:59 bar (flagged) |
|---|---|---|---|---|---|---|---|---|
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | i | 2358 | 19.8% (8.9% / 10.8%) | $46,733 / $60,433 | 10.3% | 22.5% | — (no post-market bar on disk) | 0 |
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | ii | 2068 | 16.9% (8.3% / 8.6%) | $66,391 / $77,722 | 8.6% | 15.5% | 38.0% of 1183 | 0 |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | i | 2095 | 98.9% (47.1% / 51.9%) | $43,706 / $60,781 | 23.5% | 42.4% | — (no post-market bar on disk) | 0 |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | ii | 1757 | 97.8% (47.0% / 50.8%) | $63,509 / $77,909 | 16.8% | 32.2% | 56.6% of 987 | 0 |
| fly5 long call ±5 | i | 2095 | 99.3% (47.4% / 51.9%) | $43,718 / $60,781 | 23.5% | 42.4% | — (no post-market bar on disk) | 0 |
| fly5 long call ±5 | ii | 1757 | 98.2% (47.4% / 50.8%) | $63,532 / $77,909 | 16.8% | 32.2% | 56.4% of 987 | 0 |
| fly5 long put ±5 | i | 2097 | 99.3% (47.0% / 52.3%) | $43,722 / $60,781 | 23.6% | 42.4% | — (no post-market bar on disk) | 0 |
| fly5 long put ±5 | ii | 1757 | 98.2% (47.0% / 51.2%) | $63,532 / $77,909 | 16.8% | 32.2% | 55.9% of 987 | 0 |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | i-a | 1823 | 26.0% (11.1% / 14.9%) | $44,437 / $54,710 | 15.2% | 32.3% | — (no post-market bar on disk) | 0 |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | i-b | 572 | 16.6% (8.0% / 8.6%) | $57,238 / $60,766 | 12.9% | 24.8% | — (no post-market bar on disk) | 0 |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | ii | 2090 | 20.2% (9.5% / 10.7%) | $65,899 / $77,326 | 13.2% | 25.0% | 51.5% of 1176 | 0 |

## After the close: the four expiry cases (the after-hours study's hook)

`paper_audit.after_hours_pnl`, $ a structure, on the official-close trades: **0** hold at intrinsic (the settle P&L); **a** OCC's default at the official close (every leg in the money by ≥ $0.01 exercised or assigned), the net stock marked at the next session's 09:30 open; **b** our shorts assigned iff in the money at the decision price, our longs by default; **c** both sides at the decision price. The decision price is the close of the last UW post-market 1-minute bar ending at or before 17:30 New York (the after-hours study's rule, `paper_audit.decision_of`, read off the UW 1-minute answers on disk — data/postmarket_1m, which the daily job fills); every stock position marked at the next session's 09:30 bar open. No exercise or assignment fee (a parameter, default 0). a needs the next open (filled once the next session is on disk — the next daily run); b and c also need the decision price; without them they are —.

| candidate · structure | period | official trades | with the next open | case 0 | case a | with a decision price too | case 0 | case a | case b | case c |
|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | i | 2358 | 2358 | +3.47 | +4.34 | 0 | — | — | — | — |
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | ii | 2068 | 2068 | +4.10 | +7.96 | 1607 | +4.04 | +11.98 | +5.58 | +6.24 |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | i | 2095 | 2095 | +16.59 | +20.94 | 0 | — | — | — | — |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | ii | 1757 | 1757 | +16.20 | +44.93 | 1374 | +19.62 | +55.64 | +24.86 | +24.94 |
| fly5 long call ±5 | i | 2095 | 2095 | +9.60 | +14.08 | 0 | — | — | — | — |
| fly5 long call ±5 | ii | 1757 | 1757 | +7.13 | +36.19 | 1374 | +11.76 | +48.21 | +15.66 | +15.73 |
| fly5 long put ±5 | i | 2097 | 2097 | +7.43 | +11.84 | 0 | — | — | — | — |
| fly5 long put ±5 | ii | 1757 | 1757 | +5.58 | +33.98 | 1374 | +10.27 | +45.88 | +16.86 | +17.27 |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | i-a | 1823 | 1823 | +2.42 | +5.09 | 0 | — | — | — | — |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | i-b | 572 | 572 | +8.71 | +19.42 | 0 | — | — | — | — |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | ii | 2090 | 2090 | +7.67 | +7.57 | 1626 | +7.38 | +11.13 | +5.73 | +9.30 |

## Detail by candidate — every period together (reconciliation and detail, NOT a result: read the period tables above)

## condor_em1 — hyp_b: SPY 2-wide iron condor, shorts the first strike outside spot ± the ATM straddle

Minutes 11:30, 12:00, 12:30, 13:00, 13:30 New York; names SPY; rules `rules-2026-10-21.1`.

| structure | sessions | trades | tradable share | mean NBBO | 95% CI (session bootstrap) | median | mean mid | mean +1c | mean +2c | total NBBO | win | avg win | avg loss | worst trade | worst session | PF | mean w/o best 5 sessions | mean max risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | 964 | 4426 | 91.2% | +3.77 | [+0.74, +6.63] | +21.40 | +5.80 | -0.23 | -4.23 | +16,680 | 80.3% | +26.07 | -87.14 | -191.60 | 2023-08-04 (-902) | 1.22 | +3.45 | $170 |

$ a structure (one lot, 100 shares a point), fees in. CI = 2,000 session-bootstrap draws, seed 20261016.

By minute:

| structure | minute | sessions | trades | mean NBBO | 95% CI | mean mid | mean +2c | win | PF |
|---|---|---|---|---|---|---|---|---|---|
| condor | 11:30 | 928 | 928 | +3.58 | [-0.12, +7.06] | +5.60 | -4.42 | 78.3% | 1.19 |
| condor | 12:00 | 912 | 912 | +3.01 | [-0.66, +6.50] | +5.03 | -4.99 | 79.1% | 1.16 |
| condor | 12:30 | 898 | 898 | +2.10 | [-1.69, +5.59] | +4.12 | -5.90 | 79.5% | 1.11 |
| condor | 13:00 | 861 | 861 | +4.57 | [+0.92, +8.04] | +6.59 | -3.43 | 82.0% | 1.29 |
| condor | 13:30 | 827 | 827 | +5.79 | [+2.43, +8.87] | +7.87 | -2.21 | 83.0% | 1.42 |

By year (mean NBBO $ a structure, trades):

| structure | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| condor | +9.38 (159) | +0.16 (1080) | +5.84 (1119) | +5.65 (1129) | +2.25 (939) |

By month (mean NBBO $ a structure, trades):

| month | condor |
|---|---|
| 2022-11 | +1.72 (57) |
| 2022-12 | +13.66 (102) |
| 2023-01 | -9.83 (97) |
| 2023-02 | -1.52 (93) |
| 2023-03 | -0.81 (114) |
| 2023-04 | -3.28 (82) |
| 2023-05 | +11.65 (101) |
| 2023-06 | +11.72 (88) |
| 2023-07 | +1.19 (71) |
| 2023-08 | -4.94 (107) |
| 2023-09 | -4.64 (76) |
| 2023-10 | +6.15 (110) |
| 2023-11 | -3.51 (74) |
| 2023-12 | -3.00 (67) |
| 2024-01 | -13.38 (95) |
| 2024-02 | +13.03 (86) |
| 2024-03 | +12.53 (82) |
| 2024-04 | +7.83 (102) |
| 2024-05 | -4.59 (88) |
| 2024-06 | +2.80 (89) |
| 2024-07 | +7.67 (97) |
| 2024-08 | +1.90 (105) |
| 2024-09 | +8.10 (98) |
| 2024-10 | +13.55 (111) |
| 2024-11 | +19.20 (89) |
| 2024-12 | +0.78 (77) |
| 2025-01 | +1.94 (93) |
| 2025-02 | -11.57 (92) |
| 2025-03 | +15.83 (102) |
| 2025-04 | +6.41 (100) |
| 2025-05 | +14.27 (104) |
| 2025-06 | -0.82 (98) |
| 2025-07 | +7.38 (87) |
| 2025-08 | +17.36 (91) |
| 2025-09 | -2.76 (86) |
| 2025-10 | +4.36 (98) |
| 2025-11 | +0.89 (88) |
| 2025-12 | +12.38 (90) |
| 2026-01 | -12.21 (88) |
| 2026-02 | +22.84 (94) |
| 2026-03 | -9.36 (105) |
| 2026-04 | +5.04 (105) |
| 2026-05 | +9.63 (98) |
| 2026-06 | -21.01 (105) |
| 2026-07 | +4.12 (107) |
| 2026-08 | +10.26 (101) |
| 2026-09 | +5.18 (102) |
| 2026-10 | +21.99 (34) |

Untradable captures, by reason (the numbers in a reason replaced by #):

| structure | captures | untradable | reason | count |
|---|---|---|---|---|
| condor | 4855 | 429 | call spread credit # under # | 315 |
|  |  |  | put spread credit # under # | 34 |
|  |  |  | long call # not quoted (ask > #) | 28 |
|  |  |  | long put # not quoted (ask > #) | 24 |
|  |  |  | call spread credit # under #; put spread credit # under # | 21 |
|  |  |  | long call # not quoted (ask > #); short put # not quoted (bid > #) | 2 |

Fill facts (tradable entries): the package's quoted width (Σ qty × (ask − bid)), the NBBO-to-mid slip, and the share of entries where every leg quoted ≥ 1 contract on the side hit (the Parquet carries Theta's sizes; UW's live route carries none).

| structure | entries | quoted width $ (mean / median) | NBBO→mid slip $ (mean / median) | every leg ≥ 1 contract |
|---|---|---|---|---|
| condor | 4426 | 4.06 / 4.00 | 2.03 / 2.00 | 100.0% (of 4426) |

## fly5 — hyp_c: ±5 iron butterfly and the long call and put ±5 butterflies at the strike nearest spot

Minutes 15:00, 15:30 New York; names SPY, QQQ; rules `rules-2026-10-21.1`.

| structure | sessions | trades | tradable share | mean NBBO | 95% CI (session bootstrap) | median | mean mid | mean +1c | mean +2c | total NBBO | win | avg win | avg loss | worst trade | worst session | PF | mean w/o best 5 sessions | mean max risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iron | 971 | 3852 | 99.2% | +16.41 | [+11.88, +20.94] | +29.40 | +18.85 | +12.41 | +8.41 | +63,218 | 66.6% | +62.33 | -75.21 | -401.60 | 2024-05-31 (-1,392) | 1.65 | +15.32 | $384 |
| call | 971 | 3852 | 99.2% | +8.48 | [+3.83, +13.15] | +22.40 | +19.13 | +4.48 | +0.48 | +32,647 | 62.7% | +58.93 | -76.41 | -470.60 | 2024-05-31 (-1,448) | 1.30 | +7.36 | $392 |
| put | 971 | 3854 | 99.2% | +6.59 | [+2.03, +11.22] | +19.40 | +19.45 | +2.59 | -1.41 | +25,391 | 61.2% | +58.50 | -75.14 | -407.60 | 2024-05-31 (-1,432) | 1.23 | +5.46 | $394 |

$ a structure (one lot, 100 shares a point), fees in. CI = 2,000 session-bootstrap draws, seed 20261016.

By name:

| structure | name | sessions | trades | mean NBBO | 95% CI | mean mid | mean +2c | win | PF |
|---|---|---|---|---|---|---|---|---|---|
| iron | QQQ | 967 | 1926 | +17.15 | [+11.98, +22.04] | +19.77 | +9.15 | 66.4% | 1.65 |
| iron | SPY | 966 | 1926 | +15.67 | [+11.06, +20.04] | +17.92 | +7.67 | 66.8% | 1.65 |
| call | QQQ | 967 | 1926 | +7.66 | [+2.38, +12.63] | +19.96 | -0.34 | 62.5% | 1.25 |
| call | SPY | 966 | 1926 | +9.29 | [+4.55, +13.74] | +18.29 | +1.29 | 62.9% | 1.35 |
| put | QQQ | 968 | 1928 | +6.37 | [+0.98, +11.39] | +20.43 | -1.63 | 61.6% | 1.21 |
| put | SPY | 966 | 1926 | +6.81 | [+2.20, +11.28] | +18.46 | -1.19 | 60.7% | 1.25 |

By minute:

| structure | minute | sessions | trades | mean NBBO | 95% CI | mean mid | mean +2c | win | PF |
|---|---|---|---|---|---|---|---|---|---|
| iron | 15:00 | 971 | 1925 | +17.37 | [+11.70, +22.97] | +19.79 | +9.37 | 66.5% | 1.64 |
| iron | 15:30 | 970 | 1927 | +15.46 | [+10.57, +20.10] | +17.91 | +7.46 | 66.7% | 1.67 |
| call | 15:00 | 971 | 1925 | +8.59 | [+3.00, +14.29] | +19.99 | +0.59 | 62.7% | 1.28 |
| call | 15:30 | 970 | 1927 | +8.36 | [+3.45, +13.10] | +18.27 | +0.36 | 62.7% | 1.32 |
| put | 15:00 | 971 | 1926 | +5.97 | [+0.26, +11.66] | +20.34 | -2.03 | 60.6% | 1.19 |
| put | 15:30 | 970 | 1928 | +7.20 | [+2.23, +11.90] | +18.55 | -0.80 | 61.7% | 1.27 |

By year (mean NBBO $ a structure, trades):

| structure | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| iron | +16.58 (130) | +17.30 (990) | +15.87 (975) | +13.73 (986) | +19.36 (771) |
| call | +10.53 (130) | +12.15 (990) | +6.89 (975) | +3.98 (986) | +11.16 (771) |
| put | +9.95 (130) | +10.52 (990) | +3.98 (977) | +1.62 (986) | +10.64 (771) |

By month (mean NBBO $ a structure, trades):

| month | iron | call | put |
|---|---|---|---|
| 2022-11 | +2.38 (46) | -3.51 (46) | -5.58 (46) |
| 2022-12 | +24.35 (84) | +18.22 (84) | +18.45 (84) |
| 2023-01 | +11.49 (80) | +5.69 (80) | +4.74 (80) |
| 2023-02 | +32.93 (76) | +26.69 (76) | +26.47 (76) |
| 2023-03 | +6.63 (91) | -0.09 (91) | -1.19 (91) |
| 2023-04 | +23.16 (76) | +17.93 (76) | +16.65 (76) |
| 2023-05 | +20.08 (88) | +15.10 (88) | +13.64 (88) |
| 2023-06 | +16.23 (83) | +11.12 (83) | +9.36 (83) |
| 2023-07 | +21.03 (76) | +18.06 (76) | +17.77 (76) |
| 2023-08 | +19.50 (92) | +17.13 (92) | +15.72 (92) |
| 2023-09 | +11.90 (80) | +8.34 (80) | +7.33 (80) |
| 2023-10 | +23.30 (88) | +18.80 (88) | +18.02 (88) |
| 2023-11 | +11.65 (80) | +5.63 (80) | +3.41 (80) |
| 2023-12 | +11.25 (80) | +2.76 (80) | -4.45 (80) |
| 2024-01 | +6.10 (82) | -2.16 (82) | -6.94 (82) |
| 2024-02 | +12.75 (74) | +9.13 (74) | +5.29 (74) |
| 2024-03 | -1.82 (80) | -7.50 (80) | -11.25 (80) |
| 2024-04 | +23.89 (87) | +16.72 (87) | +15.65 (87) |
| 2024-05 | -4.17 (87) | -13.54 (87) | -15.83 (87) |
| 2024-06 | +21.21 (74) | +11.83 (74) | +12.62 (76) |
| 2024-07 | +21.51 (82) | +11.10 (82) | +9.91 (82) |
| 2024-08 | +45.05 (82) | +35.63 (82) | +34.06 (82) |
| 2024-09 | +29.30 (80) | +21.34 (80) | +17.45 (80) |
| 2024-10 | +29.05 (92) | +21.69 (92) | +17.95 (92) |
| 2024-11 | +22.95 (76) | +11.12 (76) | +3.83 (76) |
| 2024-12 | -16.80 (79) | -34.35 (79) | -37.01 (79) |
| 2025-01 | +14.73 (80) | -1.90 (80) | -5.52 (80) |
| 2025-02 | -0.73 (76) | -18.60 (76) | -23.19 (76) |
| 2025-03 | +15.11 (84) | +1.08 (84) | +2.07 (84) |
| 2025-04 | -1.95 (83) | -8.93 (83) | -10.05 (83) |
| 2025-05 | -8.89 (84) | -19.08 (84) | -20.92 (84) |
| 2025-06 | +39.42 (80) | +30.82 (80) | +26.75 (80) |
| 2025-07 | +26.75 (84) | +15.98 (84) | +13.02 (84) |
| 2025-08 | +37.59 (84) | +30.27 (84) | +28.90 (84) |
| 2025-09 | +9.10 (83) | +3.51 (83) | +0.79 (83) |
| 2025-10 | +7.88 (92) | -0.46 (92) | -2.71 (92) |
| 2025-11 | -2.63 (72) | -8.18 (72) | -12.81 (72) |
| 2025-12 | +26.23 (84) | +20.60 (84) | +19.84 (84) |
| 2026-01 | +10.15 (80) | +4.07 (80) | +4.00 (80) |
| 2026-02 | +27.87 (76) | +17.99 (76) | +21.74 (76) |
| 2026-03 | +19.42 (87) | +11.24 (87) | +9.08 (87) |
| 2026-04 | +6.69 (82) | -0.43 (82) | -4.87 (82) |
| 2026-05 | +10.91 (78) | +0.52 (78) | -0.27 (78) |
| 2026-06 | +25.85 (84) | +16.34 (84) | +16.08 (84) |
| 2026-07 | +27.33 (88) | +17.10 (88) | +16.58 (88) |
| 2026-08 | +27.61 (84) | +17.69 (84) | +17.82 (84) |
| 2026-09 | +18.36 (84) | +13.94 (84) | +14.41 (84) |
| 2026-10 | +16.69 (28) | +14.19 (28) | +12.19 (28) |

Untradable captures, by reason (the numbers in a reason replaced by #):

| structure | captures | untradable | reason | count |
|---|---|---|---|---|
| iron | 3884 | 32 | call # not quoted | 21 |
|  |  |  | put # not quoted | 9 |
|  |  |  | call # not quoted; put # not quoted | 2 |
| call | 3884 | 32 | call # not quoted | 32 |
| put | 3884 | 30 | put # not quoted | 30 |

Fill facts (tradable entries): the package's quoted width (Σ qty × (ask − bid)), the NBBO-to-mid slip, and the share of entries where every leg quoted ≥ 1 contract on the side hit (the Parquet carries Theta's sizes; UW's live route carries none).

| structure | entries | quoted width $ (mean / median) | NBBO→mid slip $ (mean / median) | every leg ≥ 1 contract |
|---|---|---|---|---|
| iron | 3852 | 4.87 / 5.00 | 2.44 / 2.50 | 100.0% (of 3852) |
| call | 3852 | 21.30 / 16.00 | 10.65 / 8.00 | 100.0% (of 3852) |
| put | 3854 | 25.72 / 19.00 | 12.86 / 9.50 | 100.0% (of 3854) |

The 15:58 close-out against the 16:00 settlement (the same trades; the exit pays $0.65 a contract closed, a long leg with no bid left to expire):

| structure | name | trades with a 15:58 value | mean 16:00 NBBO | mean 15:58 NBBO | 15:58 − 16:00 (95% CI) | mean 15:58 mid | win 16:00 | win 15:58 |
|---|---|---|---|---|---|---|---|---|
| iron | all | 3847 | +16.33 | -10.52 | -26.85 [-29.36, -24.46] | -3.87 | 66.6% | 56.2% |
| iron | SPY | 1923 | +15.59 | -8.09 | -23.67 [-26.11, -21.18] | -2.36 | 66.8% | 57.6% |
| iron | QQQ | 1924 | +17.07 | -12.96 | -30.03 [-32.77, -27.36] | -5.39 | 66.4% | 54.8% |
| call | all | 3849 | +8.43 | -33.47 | -41.90 [-44.50, -39.30] | -4.90 | 62.7% | 36.6% |
| call | SPY | 1923 | +9.20 | -28.00 | -37.20 [-39.87, -34.51] | -3.11 | 62.9% | 38.6% |
| call | QQQ | 1926 | +7.66 | -38.94 | -46.59 [-49.82, -43.42] | -6.68 | 62.5% | 34.6% |
| put | all | 3849 | +6.50 | -37.79 | -44.30 [-46.96, -41.66] | -3.79 | 61.1% | 33.6% |
| put | SPY | 1923 | +6.71 | -31.89 | -38.60 [-41.10, -35.89] | -2.26 | 60.7% | 35.1% |
| put | QQQ | 1926 | +6.29 | -43.69 | -49.98 [-53.33, -46.77] | -5.31 | 61.5% | 32.2% |

## condor_d20 — hyp_e: SPY 2-wide 20-delta iron condor, held, with the live t2 decile (D1 → condor, 13:00–15:00)

Minutes 13:00, 13:30, 14:00, 14:30, 15:00 New York; names SPY; rules `rules-c3-2026-10-21.1`.

| structure | sessions | trades | tradable share | mean NBBO | 95% CI (session bootstrap) | median | mean mid | mean +1c | mean +2c | total NBBO | win | avg win | avg loss | worst trade | worst session | PF | mean w/o best 5 sessions | mean max risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | 968 | 4485 | 92.4% | +5.67 | [+2.98, +8.17] | +21.40 | +7.74 | +1.67 | -2.33 | +25,424 | 80.2% | +26.51 | -78.63 | -191.60 | 2024-05-31 (-873) | 1.36 | +5.38 | $169 |

$ a structure (one lot, 100 shares a point), fees in. CI = 2,000 session-bootstrap draws, seed 20261016.

By minute:

| structure | minute | sessions | trades | mean NBBO | 95% CI | mean mid | mean +2c | win | PF |
|---|---|---|---|---|---|---|---|---|---|
| condor | 13:00 | 945 | 945 | +4.78 | [+1.11, +8.35] | +6.79 | -3.22 | 78.4% | 1.25 |
| condor | 13:30 | 938 | 938 | +5.39 | [+1.87, +8.69] | +7.45 | -2.61 | 78.8% | 1.32 |
| condor | 14:00 | 924 | 924 | +4.56 | [+1.15, +7.74] | +6.78 | -3.44 | 80.3% | 1.28 |
| condor | 14:30 | 880 | 880 | +8.00 | [+5.08, +10.97] | +10.02 | -0.00 | 82.3% | 1.64 |
| condor | 15:00 | 798 | 798 | +5.77 | [+2.63, +8.76] | +7.80 | -2.23 | 81.5% | 1.44 |

By year (mean NBBO $ a structure, trades):

| structure | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| condor | -2.26 (163) | +2.33 (1102) | +6.36 (1130) | +8.46 (1156) | +6.69 (934) |

By month (mean NBBO $ a structure, trades):

| month | condor |
|---|---|
| 2022-11 | -4.84 (58) |
| 2022-12 | -0.84 (105) |
| 2023-01 | -1.81 (99) |
| 2023-02 | +1.03 (92) |
| 2023-03 | +6.72 (111) |
| 2023-04 | +2.61 (84) |
| 2023-05 | +4.89 (103) |
| 2023-06 | +8.73 (87) |
| 2023-07 | +3.53 (70) |
| 2023-08 | -1.33 (104) |
| 2023-09 | -1.68 (92) |
| 2023-10 | +5.34 (109) |
| 2023-11 | +0.56 (79) |
| 2023-12 | -2.16 (72) |
| 2024-01 | -10.79 (93) |
| 2024-02 | +9.95 (83) |
| 2024-03 | +8.15 (85) |
| 2024-04 | +9.23 (103) |
| 2024-05 | -3.80 (102) |
| 2024-06 | +12.26 (92) |
| 2024-07 | +6.02 (100) |
| 2024-08 | +3.43 (104) |
| 2024-09 | +7.61 (94) |
| 2024-10 | +17.29 (110) |
| 2024-11 | +18.50 (88) |
| 2024-12 | -2.92 (76) |
| 2025-01 | +12.03 (94) |
| 2025-02 | -10.97 (93) |
| 2025-03 | +27.22 (102) |
| 2025-04 | +2.35 (101) |
| 2025-05 | +15.18 (104) |
| 2025-06 | +12.15 (97) |
| 2025-07 | +11.79 (99) |
| 2025-08 | +12.13 (95) |
| 2025-09 | -1.60 (93) |
| 2025-10 | +6.84 (103) |
| 2025-11 | +3.10 (86) |
| 2025-12 | +8.55 (89) |
| 2026-01 | -5.42 (84) |
| 2026-02 | +13.11 (95) |
| 2026-03 | -1.16 (105) |
| 2026-04 | +3.90 (105) |
| 2026-05 | +5.18 (100) |
| 2026-06 | -2.25 (104) |
| 2026-07 | +13.09 (105) |
| 2026-08 | +18.32 (100) |
| 2026-09 | +9.88 (103) |
| 2026-10 | +20.19 (33) |

Untradable captures, by reason (the numbers in a reason replaced by #):

| structure | captures | untradable | reason | count |
|---|---|---|---|---|
| condor | 4855 | 370 | call spread credit # under # | 176 |
|  |  |  | put spread credit # under # | 92 |
|  |  |  | call spread credit # under #; put spread credit # under # | 38 |
|  |  |  | long put # not quoted (ask > #) | 35 |
|  |  |  | long call # not quoted (ask > #) | 28 |
|  |  |  | long call # not quoted (ask > #); put spread credit # under # | 1 |

Fill facts (tradable entries): the package's quoted width (Σ qty × (ask − bid)), the NBBO-to-mid slip, and the share of entries where every leg quoted ≥ 1 contract on the side hit (the Parquet carries Theta's sizes; UW's live route carries none).

| structure | entries | quoted width $ (mean / median) | NBBO→mid slip $ (mean / median) | every leg ≥ 1 contract |
|---|---|---|---|---|
| condor | 4485 | 4.15 / 4.00 | 2.07 / 2.00 | 100.0% (of 4485) |

Candidate 3 by its live t2 decile (the frozen models; primary = the full model when all four VIX features are there):

| decile column | group | sessions | trades | mean NBBO | 95% CI | mean mid | win | PF |
|---|---|---|---|---|---|---|---|---|
| t2_decile_primary | D1 | 376 | 723 | +14.83 | [+10.13, +18.95] | +17.00 | 87.8% | 2.54 |
| t2_decile_primary | D2–D10 | 944 | 3762 | +3.91 | [+1.08, +6.59] | +5.96 | 78.7% | 1.23 |
| t2_decile_primary | all | 968 | 4485 | +5.67 | [+2.98, +8.17] | +7.74 | 80.2% | 1.36 |
| t2_decile_full | D1 | 376 | 723 | +14.83 | [+10.13, +18.95] | +17.00 | 87.8% | 2.54 |
| t2_decile_full | D2–D10 | 944 | 3762 | +3.91 | [+1.08, +6.59] | +5.96 | 78.7% | 1.23 |
| t2_decile_full | all | 968 | 4485 | +5.67 | [+2.98, +8.17] | +7.74 | 80.2% | 1.36 |
| t2_decile_novix | D1 | 321 | 570 | +14.25 | [+9.40, +18.91] | +16.34 | 86.7% | 2.48 |
| t2_decile_novix | D2–D10 | 946 | 3915 | +4.42 | [+1.78, +7.07] | +6.49 | 79.2% | 1.27 |
| t2_decile_novix | all | 968 | 4485 | +5.67 | [+2.98, +8.17] | +7.74 | 80.2% | 1.36 |

Primary model by row: t2_spy_full 4485.

The time-matched lift of D1 (Hypothesis E §8: Σ_s N_D1(s)·[mean(D1 at s) − mean(all at s)] / Σ N_D1(s); paired session bootstrap, 2,000 draws, seed 20261016):

| decile column | D1 trades | lift $ | 95% CI $ | lift % of max risk | 95% CI % |
|---|---|---|---|---|---|
| t2_decile_primary | 723 | +9.04 | [+5.32, +12.66] | +5.56% | [+3.19, +7.84] |
| t2_decile_full | 723 | +9.04 | [+5.32, +12.66] | +5.56% | [+3.19, +7.84] |
| t2_decile_novix | 570 | +8.56 | [+4.35, +12.82] | +5.17% | [+2.50, +7.87] |
<!-- cumulative:historical:end -->

<!-- cumulative:forward:begin -->
# Forward — period iii, 8 sessions, 2026-10-12 → 2026-10-21

Regenerated from the replay root `paper_backtest_official` by the append (`paper-backtest-2026-10-22.2`, 2026-10-22 02:38 UTC); a session listed here is never dropped. These sessions are untouched by any rule, model or choice — an execution and data-quality record until the thresholds (60 → 120 sessions for condor_em1, 150 for condor_d20's D1 re-test, 250 a name for fly5).

### Settlement: the official close

The options settle (and are auto-exercised) on the primary listing's official closing price, not the 15:59 bar. Each name-session's settlement source:

| name | sessions settled | official close (source) | 15:59 bar fallback (flagged) | official − 15:59 bar: mean / max |abs| | sessions where they differ by > $0.05 |
|---|---|---|---|---|---|
| QQQ | 8 | 8 (uw_1d 8) | 0 | 0.072 / 0.13 | 7 |
| SPY | 8 | 8 (uw_1d 8) | 0 | 0.029 / 0.06 | 1 |

No session fell back to the 15:59 bar.

### Results by period — never pooled

Official close, every leg at its own NBBO, $0.65 a contract at the open, nothing at expiry, one lot. A session's P&L is the sum of its trades (zero on a session the candidate ran and took no trade); intervals are percentile bootstraps over SESSIONS — iid and moving blocks of 20 consecutive sessions (2,000 draws, seeded; a block interval needs 60 sessions). fly5's three structures are one trade seen three ways; read them as one bet.

#### condor_em1

- **iii** — 2026-10-12 → on: untouched forward

| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | iii | 8 | 39 | 8 / 8 | +6.35 | — | 3.47% | +30.95 | [-117.63, +125.75] | — | +248 | 84.6% | 455 |

#### fly5

- **iii** — 2026-10-12 → on: untouched forward

| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iron | iii | 8 | 32 | 8 / 8 | +52.62 | — | 17.52% | +210.48 | [+63.03, +352.11] | — | +1,684 | 68.8% | 100 |
| call | iii | 8 | 32 | 8 / 8 | +49.68 | — | 16.47% | +198.73 | [+51.40, +337.10] | — | +1,590 | 68.8% | 112 |
| put | iii | 8 | 32 | 8 / 8 | +50.21 | — | 16.63% | +200.85 | [+53.64, +341.64] | — | +1,607 | 68.8% | 111 |

#### condor_d20

- **iii** — 2026-10-12 → on: untouched forward

| structure | period | sessions | trades | traded / run | mean $ a trade | block-20 CI (trade) | mean % of max risk | mean $ a session | session CI (iid) | session CI (block-20) | total $ | win | max drawdown $ (sessions) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | iii | 8 | 36 | 8 / 8 | +21.59 | — | 12.83% | +97.17 | [+67.85, +124.20] | — | +777 | 94.4% | 0 |

### Hold to expiry against the 15:58 exit

The same trades, $ a structure. The 15:58 exit (the tracker's `close_quotes`, every candidate): a long sold at its bid, a short bought back at its ask, $0.65 a contract closed, a long with no bid abandoned (no fee); the stressed columns move every contract $0.01 / $0.02 against us at the open AND at the exit. Holding to expiry leaves stock on most in-the-money trades (the flags below); the 15:58 exit is the one a cash account can take.

| candidate · structure | period | trades | hold NBBO | hold +$0.01 | hold +$0.02 | hold at mids | 15:58 trades | 15:58 NBBO | 15:58 +$0.01 open & close | 15:58 +$0.02 open & close | 15:58 at mids | 15:58 NBBO: block-20 CI (trade) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | iii | 39 | +6.35 | +2.35 | -1.65 | +8.35 | 39 | -6.28 | -13.76 | -21.25 | -2.47 | — |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | iii | 32 | +52.62 | +48.62 | +44.62 | +54.70 | 32 | +3.07 | -4.18 | -11.43 | +7.51 | — |
| fly5 long call ±5 | iii | 32 | +49.68 | +45.68 | +41.68 | +54.84 | 32 | -3.92 | -11.48 | -19.04 | +7.41 | — |
| fly5 long put ±5 | iii | 32 | +50.21 | +46.21 | +42.21 | +54.99 | 32 | -2.81 | -10.50 | -18.18 | +7.43 | — |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | iii | 36 | +21.59 | +17.59 | +13.59 | +23.59 | 36 | +1.16 | -6.59 | -14.34 | +5.05 | — |

### Expiry flags (held to the official close)

SPY and QQQ options are American and physically settled: OCC exercises every option in the money by $0.01 or more at the official close unless told otherwise, so a structure held to the close can leave shares (`stock_left`: the net of the exercises and assignments, by sign) — a 100-share position per lot against a few hundred dollars of modeled risk. The pins: the official close within $0.25 / $0.50 of a short strike (the writer does not know at 16:00 whether he is assigned). The post-market cross: UW's post-market bar (16:00–20:00, read from disk now — the window to the exercise cut-off is shorter, so an upper bound) took a short strike across the money; known only where that bar is on disk.

| candidate · structure | period | trades | stock left (long / short) | mean / max stock left $ | pin ≤ $0.25 | pin ≤ $0.50 | post-market cross (of trades with the bar) | settled on the 15:59 bar (flagged) |
|---|---|---|---|---|---|---|---|---|
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | iii | 39 | 20.5% (12.8% / 7.7%) | $76,959 / $77,801 | 12.8% | 15.4% | 48.7% of 39 | 0 |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | iii | 32 | 96.9% (28.1% / 68.8%) | $74,987 / $77,810 | 28.1% | 31.2% | 75.0% of 32 | 0 |
| fly5 long call ±5 | iii | 32 | 100.0% (31.2% / 68.8%) | $74,918 / $77,810 | 28.1% | 31.2% | 75.0% of 32 | 0 |
| fly5 long put ±5 | iii | 32 | 100.0% (28.1% / 71.9%) | $74,918 / $77,810 | 28.1% | 31.2% | 75.0% of 32 | 0 |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | iii | 36 | 11.1% (2.8% / 8.3%) | $77,276 / $77,801 | 13.9% | 30.6% | 50.0% of 36 | 0 |

### After the close: the four expiry cases (the after-hours study's hook)

`paper_audit.after_hours_pnl`, $ a structure, on the official-close trades: **0** hold at intrinsic (the settle P&L); **a** OCC's default at the official close (every leg in the money by ≥ $0.01 exercised or assigned), the net stock marked at the next session's 09:30 open; **b** our shorts assigned iff in the money at the decision price, our longs by default; **c** both sides at the decision price. The decision price is the close of the last UW post-market 1-minute bar ending at or before 17:30 New York (the after-hours study's rule, `paper_audit.decision_of`, read off the UW 1-minute answers on disk — data/postmarket_1m, which the daily job fills); every stock position marked at the next session's 09:30 bar open. No exercise or assignment fee (a parameter, default 0). a needs the next open (filled once the next session is on disk — the next daily run); b and c also need the decision price; without them they are —.

| candidate · structure | period | official trades | with the next open | case 0 | case a | with a decision price too | case 0 | case a | case b | case c |
|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | iii | 39 | 34 | +3.64 | +62.37 | 34 | +3.64 | +62.37 | +60.55 | +60.55 |
| fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | iii | 32 | 28 | +40.51 | +117.26 | 28 | +40.51 | +117.26 | -41.81 | -41.81 |
| fly5 long call ±5 | iii | 32 | 28 | +37.36 | +105.26 | 28 | +37.36 | +105.26 | -58.35 | -58.35 |
| fly5 long put ±5 | iii | 32 | 28 | +38.04 | +123.65 | 28 | +38.04 | +123.65 | -30.89 | -30.10 |
| condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | iii | 36 | 31 | +20.69 | +48.79 | 31 | +20.69 | +48.79 | +43.14 | +43.14 |

### Sessions

| session | candidate · structure | trades | session P&L held $ | at 15:58 $ | settlement | stock left (trades) | pin ≤ $0.50 (trades) | post-market cross |
|---|---|---|---|---|---|---|---|---|
| 2026-10-12 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 4 | +42.60 | +18.50 | SPY 778.1 (uw_1d) | 0 | 0 | 0 of 4 |
| 2026-10-12 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | -63.40 | -88.60 | QQQ 746.04 (uw_1d); SPY 778.1 (uw_1d) | 4 | 1 | 2 of 4 |
| 2026-10-12 | fly5 long call ±5 | 4 | -69.40 | -115.20 | QQQ 746.04 (uw_1d); SPY 778.1 (uw_1d) | 4 | 1 | 2 of 4 |
| 2026-10-12 | fly5 long put ±5 | 4 | -75.40 | -110.20 | QQQ 746.04 (uw_1d); SPY 778.1 (uw_1d) | 4 | 1 | 2 of 4 |
| 2026-10-12 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 2 | +20.80 | +7.60 | SPY 778.1 (uw_1d) | 0 | 0 | 0 of 2 |
| 2026-10-13 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | +92.00 | +20.95 | SPY 778.01 (uw_1d) | 3 | 3 | 3 of 5 |
| 2026-10-13 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | +93.60 | -14.85 | QQQ 743.57 (uw_1d); SPY 778.01 (uw_1d) | 4 | 2 | 3 of 4 |
| 2026-10-13 | fly5 long call ±5 | 4 | +85.60 | -31.50 | QQQ 743.57 (uw_1d); SPY 778.01 (uw_1d) | 4 | 2 | 3 of 4 |
| 2026-10-13 | fly5 long put ±5 | 4 | +82.60 | -48.15 | QQQ 743.57 (uw_1d); SPY 778.01 (uw_1d) | 4 | 2 | 3 of 4 |
| 2026-10-13 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 4 | +57.60 | +1.50 | SPY 778.01 (uw_1d) | 2 | 2 | 2 of 4 |
| 2026-10-14 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | +165.00 | +13.00 | SPY 769.6 (uw_1d) | 0 | 0 | 3 of 5 |
| 2026-10-14 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | +305.60 | +10.20 | QQQ 728.95 (uw_1d); SPY 769.6 (uw_1d) | 4 | 1 | 4 of 4 |
| 2026-10-14 | fly5 long call ±5 | 4 | +293.60 | -16.80 | QQQ 728.95 (uw_1d); SPY 769.6 (uw_1d) | 4 | 1 | 4 of 4 |
| 2026-10-14 | fly5 long put ±5 | 4 | +290.60 | -14.80 | QQQ 728.95 (uw_1d); SPY 769.6 (uw_1d) | 4 | 1 | 4 of 4 |
| 2026-10-14 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 5 | +150.00 | +4.00 | SPY 769.6 (uw_1d) | 0 | 3 | 1 of 5 |
| 2026-10-15 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | +138.00 | +8.00 | SPY 771.79 (uw_1d) | 0 | 2 | 2 of 5 |
| 2026-10-15 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | +141.60 | -134.50 | QQQ 728 (uw_1d); SPY 771.79 (uw_1d) | 3 | 2 | 4 of 4 |
| 2026-10-15 | fly5 long call ±5 | 4 | +131.60 | -165.15 | QQQ 728 (uw_1d); SPY 771.79 (uw_1d) | 4 | 2 | 4 of 4 |
| 2026-10-15 | fly5 long put ±5 | 4 | +133.60 | -148.15 | QQQ 728 (uw_1d); SPY 771.79 (uw_1d) | 4 | 2 | 4 of 4 |
| 2026-10-15 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 5 | +74.00 | -123.00 | SPY 771.79 (uw_1d) | 1 | 3 | 4 of 5 |
| 2026-10-16 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | -455.00 | -426.75 | SPY 763.25 (uw_1d) | 3 | 0 | 1 of 5 |
| 2026-10-16 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | +421.60 | +266.50 | QQQ 709.8 (uw_1d); SPY 763.25 (uw_1d) | 4 | 1 | 3 of 4 |
| 2026-10-16 | fly5 long call ±5 | 4 | +398.60 | +218.85 | QQQ 709.8 (uw_1d); SPY 763.25 (uw_1d) | 4 | 1 | 3 of 4 |
| 2026-10-16 | fly5 long put ±5 | 4 | +412.60 | +233.85 | QQQ 709.8 (uw_1d); SPY 763.25 (uw_1d) | 4 | 1 | 3 of 4 |
| 2026-10-16 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 5 | +102.00 | +48.95 | SPY 763.25 (uw_1d) | 1 | 0 | 1 of 5 |
| 2026-10-19 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | +12.00 | +31.25 | SPY 766.48 (uw_1d) | 2 | 1 | 2 of 5 |
| 2026-10-19 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | -100.40 | -21.90 | QQQ 718.36 (uw_1d); SPY 766.48 (uw_1d) | 4 | 0 | 2 of 4 |
| 2026-10-19 | fly5 long call ±5 | 4 | -112.40 | -44.20 | QQQ 718.36 (uw_1d); SPY 766.48 (uw_1d) | 4 | 0 | 2 of 4 |
| 2026-10-19 | fly5 long put ±5 | 4 | -111.40 | -50.50 | QQQ 718.36 (uw_1d); SPY 766.48 (uw_1d) | 4 | 0 | 2 of 4 |
| 2026-10-19 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 5 | +126.00 | +89.00 | SPY 766.48 (uw_1d) | 0 | 3 | 0 of 5 |
| 2026-10-20 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | +129.00 | +84.25 | SPY 769.05 (uw_1d) | 0 | 0 | 4 of 5 |
| 2026-10-20 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | +335.60 | +78.15 | QQQ 717.63 (uw_1d); SPY 769.05 (uw_1d) | 4 | 2 | 2 of 4 |
| 2026-10-20 | fly5 long call ±5 | 4 | +318.60 | +38.50 | QQQ 717.63 (uw_1d); SPY 769.05 (uw_1d) | 4 | 2 | 2 of 4 |
| 2026-10-20 | fly5 long put ±5 | 4 | +332.60 | +62.85 | QQQ 717.63 (uw_1d); SPY 769.05 (uw_1d) | 4 | 2 | 2 of 4 |
| 2026-10-20 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 5 | +111.00 | +39.60 | SPY 769.05 (uw_1d) | 0 | 0 | 5 of 5 |
| 2026-10-21 | condor_em1 condor (SPY 2-wide, straddle edge, 11:30–13:30) | 5 | +124.00 | +6.00 | SPY 773.09 (uw_1d) | 0 | 0 | 4 of 5 |
| 2026-10-21 | fly5 iron ±5 (SPY+QQQ, 15:00 / 15:30) | 4 | +549.60 | +3.20 | QQQ 725.2 (uw_1d); SPY 773.09 (uw_1d) | 4 | 1 | 4 of 4 |
| 2026-10-21 | fly5 long call ±5 | 4 | +543.60 | -9.80 | QQQ 725.2 (uw_1d); SPY 773.09 (uw_1d) | 4 | 1 | 4 of 4 |
| 2026-10-21 | fly5 long put ±5 | 4 | +541.60 | -14.80 | QQQ 725.2 (uw_1d); SPY 773.09 (uw_1d) | 4 | 1 | 4 of 4 |
| 2026-10-21 | condor_d20 condor (SPY 2-wide 20-delta, 13:00–15:00) | 5 | +136.00 | -26.00 | SPY 773.09 (uw_1d) | 0 | 0 | 5 of 5 |

<!-- cumulative:forward-sessions ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21"] -->
<!-- cumulative:forward:end -->
