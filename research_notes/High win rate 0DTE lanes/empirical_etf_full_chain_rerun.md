# Empirical: the SPY / QQQ / IWM 0DTE short-premium grid re-run on complete option chains (answer to the developer review)

Scope and method. The developer review of the round-2 report found that the original grid ([empirical_etf_short_premium_grid.md](file:///home/user/georgeredo/research_notes/High%20win%20rate%200DTE%20lanes/empirical_etf_short_premium_grid.md), code in `research/thetadata/hwr_grid/etf/`) priced only strikes within ±2 % of the 09:31 print, skipped every entry whose strikes or spot fell outside that band (amendment A1), and so dropped extreme-move days from the lane while the random-entry baseline could still trade some of them. This note re-runs exactly the pre-registered grid on the full same-day chains (every listed strike; `data_full`). The rules are unchanged: 2,016 configurations per scope, TRAIN 2022-11-11 → 2024-12-31 (IWM from 2024-04-19), TEST 2025-01-02 → 2026-10-09, NBBO bid/ask fills, $0.70 per contract per side, the same exits, seeds and statistics. The protocol file is a byte-identical copy (sha256 ddc4e053…). Code, outputs and run record: `/home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/` ([README.md](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/README.md), [RESULTS.md](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)). No ThetaData login was used. All $ are per 1-lot (one contract per leg). CIs are 95 % day-clustered bootstrap intervals (5,000 draws, seed 7). The TEST window had already been seen on band data, so it is out of sample for the selection rule but it is not a fresh holdout.

## Key question 1: Do the full chains contain every strike the grid needs on every session, including extreme-move days? How many previously skipped entries can now be traded?

### Takeaway
Yes. Strike-band truncation is gone. At every pre-registered entry and every random-baseline minute, in both periods, no needed strike is missing and spot is never outside the listed range. Amendment A1 therefore never fires. 125 entry slots still fail, all because no usable quote existed at that exact minute: 107 in TRAIN (95 of them on 2024-06-21) and 18 in TEST. On 2024-06-21 both data pulls are incomplete. Of the fixed-entry slots the band run skipped, 8,731 of 9,247 now trade. The other 516 are skipped under pre-registered market rules (a zero bid or no net credit), except 7 with no quote.

### Cited Findings
- Files (all hashed with sha256 in `data_manifest.csv`): SPY 980 sessions, QQQ 980, IWM 621, with 0 `.nodata`. Listed strikes per session, median (min): SPY 139 (40), QQQ 131 (38), IWM 79 (30). The listed strikes span the session's whole 09:30–16:00 price range on 980 / 980 / 621 sessions. The original band spanned it on 938 / 881 / 520 — [RESULTS.md §1](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md), [integrity.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/integrity.json), [data_manifest.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/data_manifest.csv)
- Consistency between the two pulls: every band quote row is reproduced exactly by the full pull on every session except 2024-06-21. That day the full pull lacks 2,346 of 12,121 SPY band rows, 3,910 of 10,557 QQQ rows and 1,564 of 3,128 IWM rows (SPY strike 553 is missing entirely). Overall, 17,333,421 of 17,335,767 SPY band rows are identical in the full pull, along with 15,306,477 of 15,310,387 QQQ rows and 4,733,446 of 4,735,010 IWM rows — [RESULTS.md §1](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md), [data_manifest.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/data_manifest.csv)
- Per-entry check (the trade loop's own skip rules applied at every minute from 10:00 to 14:30). Strike-beyond-range (`out_of_band`) and spot-outside-range (A1) slots are 0 at every pre-registered entry and every drawn random minute, for all tickers and both periods. Outside the drawn minutes there are 6 such slots (QQQ TEST) and 2 (IWM TEST) out of 836,577 slots each. TEST fixed-entry slots (entry × structure-k, 12,348 per ticker):
  - SPY: 12,332 eligible; 2 no_quote, 13 zero_bid, 1 no_credit.
  - QQQ: 12,319 eligible; 29 zero_bid.
  - IWM: 11,300 eligible; 1,015 zero_bid (mostly condor wings), 33 no_credit.
  Sources: [integrity_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/integrity_summary.csv), [RESULTS.md §1](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Slots still missing a needed quote, out of all fixed and random-baseline slots: **125, all `no_quote`**. By session:
  - TRAIN 2024-06-21: SPY 30, QQQ 34, IWM 31.
  - QQQ TRAIN: 2023-10-19 (4), 2023-10-25 (2), 2024-02-06 (6).
  - SPY TEST (7): 2025-04-07 r12, 2025-11-13 11:00 S1/I1, 2026-05-29 r15, 2026-06-11 r13.
  - IWM TEST (11): 2025-07-30 r13, 2025-10-22 r15.
  The full list is in [integrity_missing.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/integrity_missing.csv).
- Recovered entries. Band-skipped fixed-entry slots now traded: 8,731 of 9,247; random-entry slots: 10,750 of 11,380. For TEST alone: fixed 4,818 of 5,105 and random 5,863 of 6,238. By ticker (TEST, fixed): SPY 694 of 694, QQQ 1,768 of 1,778, IWM 2,356 of 2,633 — [RESULTS.md §1](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md), [integrity_recovered.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/integrity_recovered.csv)
- Amendment A1 (spot outside the stored range). The original run skipped these fixed-entry slots; most are now traded:

  | Ticker | TRAIN skipped (sessions) | TRAIN now traded | TEST skipped (sessions) | TEST now traded |
  |---|---|---|---|---|
  | SPY | 56 (6) | 56 | 98 (9) | 98 |
  | QQQ | 294 (26) | 293 | 259 (24) | 259 |
  | IWM | 168 (13) | 154 | 399 (33) | 375 |

  The IWM remainder is zero-bid or no-credit skips — [integrity.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/integrity.json), [RESULTS.md §1](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Reach of the listed strikes beyond spot at the pre-registered entries, in units of the entry-time expected move: the minimum is 4.94 EM (QQQ TRAIN, below spot). The widest structure needs 2.5 EM. 0 fixed-entry slots reach less than 2.5 EM — [integrity_reach.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/integrity_reach.csv)
- Code validation. Pointed at the original band data, the copied engine reproduces all six original per-trade and skip files exactly (e.g. SPY TEST 577,080 rows). It also reproduces the four scopes' TRAIN selections and the selected-TEST rows (max |difference| 0). On the full data, trades common to both runs have identical P&L (max |Δ| $0.0000 for every selection) — [validation_band_reproduction.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/validation_band_reproduction.json), [selected_test.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selected_test.csv)

### Inferences
- The data-integrity gate (§10: full-chain coverage on every test date, data hashed) is met for TEST at every entry the selected configurations use. What remains are minute-level quote gaps (18 TEST slots, none at a 14:05 entry), not truncation.
- 2024-06-21 is a vendor irregularity: a June quad-witching expiry, with rows missing in both pulls. It touches TRAIN only (one session of 530) and should be re-pulled before that day is relied on.

### Gaps
- There is no independent second vendor; the check is internal consistency between two ThetaData pulls plus the per-entry rules.
- Quote size and queue position are not modelled (1-lot at the displayed NBBO).

## Key question 2: What do the TRAIN selections do in TEST on complete data? Does the grid still beat chance and the max-statistic test?

### Takeaway
The selections hardly change on complete TRAIN data. Every scope's S1 is still the 14:05 ATM straddle with a 1× stop, held to expiry (E2), skipping FOMC and month-end days (F3). Only SPY S2 and QQQ S2 change. On complete TEST data each lane now trades all 407 eligible days. The extreme days (2025-04-04, 2025-04-08) enter as some of the largest losses, but over 7–24 added trades they net roughly zero, so the TEST means move by only $0.09–$2.04 (the largest change is QQQ S2-orig, −$2.04). Every pre-registered selection except IWM S1 keeps a Bonferroni-adjusted lower bound above zero.

Grid-wide, complete data cuts the number of configurations with TEST LB > 0 by about a third (SPY+QQQ 293 → 193). The cut falls on the 10:00, 11:00 and 13:00 entries and on E1. The count is still above the chance 95th percentile, and the reality check still rejects; nearly all rejections are E2 straddles/strangles.

### Cited Findings
- Selections on complete TRAIN data (original band selection → full-chain selection):
  - SPY S1, QQQ S1, IWM S1, SPY+QQQ S1: `S0|14:05|tp0|st1|E2|F3`, unchanged.
  - SPY S2: `S0.5|14:05|tp0|st2|E2|F3` → `S0|14:05|tp50|st2|E2|F3` (straddle, 50 % take-profit, 2× stop).
  - QQQ S2: `S0|14:05|tp0|st2|E2|F3` → `S0|14:05|tp0|st1|E2|F3` (= S1).
  - IWM S2, SPY+QQQ S2: `S0|14:05|tp0|st2|E2|F3`, unchanged.
  The final selection file has sha256 b3d83a32…, written before the TEST stage — [selection_train.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selection_train.json), [RESULTS.md §2](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md), [README.md](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/README.md)
- TEST on band data (original run) → TEST on complete data, as n / win / mean [CI], with the Bonferroni-8 lower bound:

  | Scope | Selection | Band data | Complete data | Bonferroni-8 LB |
  |---|---|---|---|---|
  | SPY | S1 = S1-orig | 400 / +$34.82 [+23.09, +46.26] | 407 / 68.1 % / **+$34.33 [+21.02, +47.24]** | +$15.41 |
  | SPY | S2 (new) | — | 407 / 70.3 % / **+$32.09 [+19.93, +43.76]** | +$15.35 |
  | SPY | S2-orig | 397 / +$20.69 [+12.19, +29.03] | 407 / 75.9 % / +$21.29 [+11.05, +31.28] | +$7.07 |
  | QQQ | S1 | 391 / +$28.55 [+14.89, +41.98] | 407 / 64.9 % / +$28.10 [+14.03, +41.97] | +$9.33 |
  | QQQ | S2-orig | 391 / +$35.05 | 407 / 67.8 % / +$33.01 [+18.05, +47.32] | +$12.29 |
  | IWM | S1 | 383 / +$8.69 [+2.71, +14.50] | 407 / 61.7 % / +$8.78 [+2.52, +14.95] | **−$0.66** |
  | IWM | S2 | 383 / +$12.20 [+6.28, +17.74] | 407 / 63.9 % / +$12.40 [+6.36, +18.35] | +$3.38 |
  | SPY+QQQ | S1 | 791 / +$31.72 | 814 / 66.5 % / +$31.22 [+18.07, +44.25] | +$13.25 |
  | SPY+QQQ | S2 | 791 / +$36.45 | 814 / 68.6 % / +$35.75 [+22.31, +49.03] | +$17.19 |

  Source: [selected_test.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selected_test.csv), [RESULTS.md §2](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Trades added by the full chains (count, net $, worst):
  - SPY S1: 7, +$47.80, worst 2025-04-08 −$801.
  - QQQ S1: 16, +$273.71, worst 2025-04-08 −$652.
  - QQQ S2-orig: 16, −$267.29, worst −$776.
  - IWM S2: 24, +$375.00.
  - SPY+QQQ S1: 23, +$321.51.
  The worst TEST days on complete data are now SPY S1 2025-04-08 −$801 and 2025-04-04 −$447, and SPY+QQQ S1 2025-04-08 −$1,453 — [selected_test.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selected_test.csv), [RESULTS.md §2](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- By year (complete data): SPY S1 2025 +$43.05 [+23.73, +62.18], 2026 +$23.23 [+5.86, +40.20]; QQQ S1 2026 +$14.23 [−7.56, +35.19]; IWM S2 2026 +$6.62 [−2.96, +16.38] — [selected_by_year.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selected_by_year.csv)
- Full grid in TEST (1,890 distinct configurations per scope). Count of TEST LB > 0, band → complete, against the chance mean / 95th percentile on complete data:

  | Scope | LB > 0, band → complete | Chance mean / p95 (complete) |
  |---|---|---|
  | SPY | 240 → 161 | 26.5 / 134 |
  | QQQ | 314 → 240 | 29.5 / 143 |
  | IWM | 63 → 55 | 23.0 / 105 |
  | SPY+QQQ | 293 → 193 | 27.5 / 144 |

  The IWM count is not distinguishable from chance. White reality check, best studentised t: SPY+QQQ 5.893 (`S1.5|14:05|tp0|st0|E2|F3`), SPY 6.388, QQQ 5.467, IWM 5.295, all p < 0.0002. Romano–Wolf rejections: SPY+QQQ 81 (79 E2, 2 E1), SPY 78 (74 E2), QQQ 76 (all E2), IWM 20 (all E2). The only E1 rejections are strangles k = 1–1.5 at 14:05 with no TP and no stop — [grid_test_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/grid_test_summary.json), [RESULTS.md §4](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Where the LB > 0 configurations were lost (SPY+QQQ, band → complete):
  - By entry: 10:00 58 → 26, 11:00 29 → 6, 13:00 119 → 73, 14:05 87 → 88.
  - By exit: E1 57 → 15, E2 236 → 178.
  - Grid medians: TEST win 72.9 % → 73.3 %, mean −$1.39 → −$1.47.
  Computed from [grid.csv.gz (complete)](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/grid.csv.gz) and [grid.csv.gz (band)](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf/results/grid.csv.gz)
- Post-hoc E1 selections (the realistic 15:55 buy-back; not pre-registered): SPY+QQQ `S0.5|14:05|tp0|st2|E1|F3` TEST +$6.38 [−2.77, +15.05]; SPY +$7.62 [−1.05, +16.13]; QQQ +$5.50 [−2.31, +13.28]. For IWM the rule now picks `S0.5|11:00|tp0|st0|E1|F1`, which earns −$4.30 [−16.18, +5.42] and loses −$1,488 on 2025-04-09 — [selected_test.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selected_test.csv)

### Inferences
- The band mostly flattered the earlier entries (10:00–13:00) and the E1 exits. The extreme days it dropped were days when the market had already broken out before a late entry, or had high expected moves. The TRAIN-selected 14:05 family was barely exposed to those days, which is why its TEST numbers hardly move.
- The positive, multiple-testing-robust result is still "sell the ATM straddle in the afternoon and hold it through the 16:00 close" (E2). With the realistic exit (E1), no TRAIN-selected configuration has a positive TEST lower bound.

### Gaps
- There is one TRAIN/TEST split. IWM TRAIN covers only 161 trades. TEST (2025–2026) is the same favourable regime already noted in the original study.

## Key question 3: With no day skipped, do the selections beat random entry on matched days?

### Takeaway
The one-sidedness is gone: lane and baseline now trade the same (ticker, date) pairs, with 0 baseline-only trades for every selection. On matched days no selection's paired difference has a CI that excludes zero.

As written (point estimate above one round trip), only SPY S1 (+$8.23 vs $3.28) and the new SPY S2 (+$11.15 vs $3.49) clear it. SPY S2 also has TEST win ≥ 70 % (70.3 %), so it is the first configuration in this study to meet the original four-item gate and the 70 % objective together. IWM S2's original pass (+$3.38 vs $3.18) disappears (+$1.89 vs $3.27). The pooled S1 (+$3.48 vs $3.77) and S2 (+$1.19 vs $3.10) fail.

### Cited Findings
- Paired lane − baseline on matched days, mean [CI], against the round trip:

  | Scope | Selection | Matched pairs | Paired diff | Round trip |
  |---|---|---|---|---|
  | SPY | S1 | 407 | +$8.23 [−6.65, +23.97] | $3.28 |
  | SPY | S2 (new) | 407 | +$11.15 [−3.31, +27.48] | $3.49 |
  | SPY | S2-orig | 407 | −$1.84 [−13.57, +11.47] | $2.98 |
  | QQQ | S1 | 407 | −$1.27 [−16.77, +15.76] | $4.26 |
  | QQQ | S2-orig | 407 | −$5.03 [−20.81, +12.53] | $3.39 |
  | IWM | S1 | 407 | +$1.42 [−4.89, +8.06] | $4.09 |
  | IWM | S2 | 407 | +$1.89 [−4.76, +8.90] | $3.27 |
  | SPY+QQQ | S1 | 814 | +$3.48 [−10.65, +18.83] | $3.77 |
  | SPY+QQQ | S2 | 814 | +$1.19 [−13.43, +17.67] | $3.10 |

  Baseline-only trades: 0 for every selection — [selected_test.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/selected_test.csv), [RESULTS.md §3](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- In the original band run, SPY S1's baseline traded 19 days that the lane could not trade; those trades averaged −$458.56. IWM S2's baseline traded 61 such days, averaging −$152.62 — [empirical_etf_short_premium_grid.md](file:///home/user/georgeredo/research_notes/High%20win%20rate%200DTE%20lanes/empirical_etf_short_premium_grid.md)
- Random-entry baselines are positive on their own. For example, the SPY S1 seeds earn +$23.52 to +$28.62, with lower bounds from +$4.85 to +$9.62 — [baselines.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/baselines.csv)
- Original four-item gate on complete data: PASS for SPY S1 (= S1-orig) and SPY S2 (new). FAIL for SPY S2-orig, every QQQ, IWM and SPY+QQQ selection, and every post-hoc E1 selection — [RESULTS.md §3](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)

### Inferences
- The premium is generic: an entry anywhere from 10:00 to 14:30 with the same rules earns most of it. The 14:05 timing's edge over random entry is within noise even for SPY. That is consistent with treating this family as carry, not signal.

### Gaps
- The random baseline uses 5 seeds of one minute per day. A full-window average (every minute from 10:00 to 14:30) would tighten the baseline but was not pre-registered.

## Key question 4: How realistic is hold-to-expiry for physically settled ETF options, and what does a tail shock cost?

### Takeaway
E2 is optimistic for the ETFs. Re-valuing SPY's expired legs against the after-hours price, SPY S1 drops from +$34.33 to +$23.03 if holders exercise rationally after hours, and to +$1.01 [−12.68, +14.66] under the pessimistic valuation. The new SPY S2 falls to +$1.58 [−12.61, +15.01] under the pessimistic valuation.

The selected straddles are naked. A ±8.42 % move from entry to settlement costs about $5,470 per SPY lot (median trade), against a median credit of $148. A ±15 % move costs about $9,880, and up to −$11,608 for the worst trade. Keeping that inside an 8 % budget needs about $124k of capital per SPY lot (QQQ $111k, IWM $45k). Historically the worst 14:05→close moves since 2017 are smaller (SPY −3.63 % / +5.09 %, QQQ −4.37 % / +5.46 %, IWM −4.54 % / +4.12 %). Earlier entries have seen +10.2 % (SPY), +11.9 % (QQQ) and +10.5 % (IWM), all on 2025-04-09.

### Cited Findings
- SPY settlement re-valuation, TEST, complete data. Inputs are `../etf/results/diag_settlement_spy.csv`, used unchanged.

  | Configuration | 16:00 as run | EOD close | Rational after-hours exercise | Pessimistic |
  |---|---|---|---|---|
  | `S0|14:05|tp0|st1|E2|F3` (SPY S1, n = 407) | +$34.33 [+21.37, +47.10] | +$32.29 | +$23.03 [+8.73, +37.27] | +$1.01 [−12.68, +14.66] |
  | `S0|14:05|tp50|st2|E2|F3` (SPY S2) | +$32.09 | — | +$21.30 [+7.38, +34.99] | +$1.58 [−12.61, +15.01] |
  | `S0.5|14:05|tp0|st2|E2|F3` (S2-orig) | — | — | — | +$3.95 [−7.28, +14.78] |
  | `S0|14:05|tp0|st2|E2|F3` (SPY leg of SPY+QQQ S2) | — | — | — | +$1.57 [−13.11, +15.74] |

  QQQ and IWM cannot be re-valued: no after-hours inputs exist for them — [settlement_spy.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/settlement_spy.csv), [RESULTS.md §6](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Historical entry→close moves, 2,333 full sessions per ticker, 2017-06-01 → 2026-10-09:
  - SPY: 13:00 +8.41 % (2025-04-09); any minute from 10:00 to 14:30, −6.90 % (2020-03-12) / +10.17 % (2025-04-09); 14:05 −3.63 % (2020-03-20) / +5.09 % (2020-03-13).
  - QQQ: any minute −8.15 % / +11.85 %; 14:05 −4.37 % / +5.46 %.
  - IWM: any minute −7.08 % / +10.47 %; 14:05 −4.54 % (2024-12-18) / +4.12 %.

  Sources: [stress_hist_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/stress_hist_summary.csv), [stress_hist_moves.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/stress_hist_moves.csv)
- Unprotected settlement P&L per lot over the selection's TEST trades (median trade / worst trade). No stop fill is assumed: gaps, halts and after-hours moves cannot be stopped.

  | Selection | Median credit | ±5 % | ±8.42 % | ±10 % | ±15 % |
  |---|---|---|---|---|---|
  | SPY S1 | $148 | −$3,181 to −$3,182 / −$3,814 | −$5,470 to −$5,477 / −$6,475 | −$6,518 to −$6,533 / −$7,708 | −$9,877 to −$9,878 / −$11,608 |
  | QQQ S1 | $176 | — | — | — | −$8,834 to −$8,838 / −$11,337 |
  | IWM S2 | $77 | — | — | — | −$3,602 to −$3,612 / −$4,543 |

  At the worst historical 14:05 moves: SPY −$2,268 (down) and −$3,242 (up), median trade.

  Capital per lot so that the ±15 % loss stays within an 8 % budget (median trade): SPY $123,589, QQQ $110,783, IWM $45,440, SPY+QQQ $116,438.

  Formula margin estimates per lot, not broker-verified:
  - SPY: Reg-T $13,555 at the 20 % rate, $10,219 at the 15 % rate; PM-style −8 % / +6 % scenario $5,186.
  - IWM: Reg-T $5,012 / $3,782.

  Stop at its trigger level (optimistic): SPY S1 −$151.

  Sources: [stress_selected.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/stress_selected.csv), [RESULTS.md §7](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Realized SPY S1 results on the April 2025 days, which are now priced:
  - 04-04: −$447 (held to expiry)
  - 04-07: +$477
  - 04-08: −$801 (stopped out)
  - 04-09: +$261 (the 14:05 entry came after the 13:18 jump)
  - 04-10: +$629

  On the same days, QQQ S1 had 04-08 −$652, and SPY+QQQ S1 had 04-08 −$1,453 and 04-04 −$864 — [stress_extreme_days.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/stress_extreme_days.csv)

### Inferences
- Most of the SPY E2 edge depends on how after-hours exercise is valued. Without a modelled exercise and assignment process, E2 cannot pass execution realism for the ETFs.
- The 1× and 2× stops are what kept realized single-day losses in the hundreds of dollars on 2025-04-04 and 2025-04-08. The capital needed per lot is set by the unstoppable scenario, not by the realized history.

### Gaps
- Margin figures are formula estimates (Reg-T naked-option rule at 20 % and 15 %, and a PM-style scenario at expiry intrinsic), not broker or OCC TIMS numbers.
- After-hours inputs exist only for SPY.

## Key question 5: Gate verdicts under COMPASS §10

### Takeaway
No selection passes, either as a carry lane or as a signal lane. For the pre-registered selections, item by item:

| Gate item | Result |
|---|---|
| Data integrity | ✓ for all 16 selection rows |
| Execution realism | ✗ for all (every selection is E2) |
| Statistical validity on complete data | ✓, except IWM S1 (= S1-orig; Bonferroni-8 lower bound −$0.66) |
| Tail survival | ✗: losses are now stated, but no sizing rule or broker margin has been adopted |
| Forward validation | ✗: 0 of the required 150 sessions and 7 months |
| Classification | carry |
| Beats random entry (signal version only) | Point estimate above cost only for SPY S1 and SPY S2; no paired CI excludes zero |

The post-hoc E1 versions fix execution realism but fail statistical validity (TEST lower bound below 0).

### Cited Findings
- Gate table and item detail per selection — [gates.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/results/gates.csv), [RESULTS.md §8](file:///home/user/georgeredo/research/thetadata/hwr_grid/etf_v2/RESULTS.md)
- Gate definitions — [COMPASS_RESEARCH_PLAN.md §10](file:///home/user/georgeredo/COMPASS_RESEARCH_PLAN.md)

### Inferences
- The review's two data findings are now fixed: the strike band and the one-sided random comparison. Fixing them does not change the original conclusion. The defensible statement is a generic afternoon short-straddle carry on SPY/QQQ. Its measured edge sits within the unpriced after-hours exercise risk, and it needs a large capital base per lot. The next evidence has to come from an exercise/assignment model with after-hours data for QQQ and IWM, and from forward paper trading with live NBBO logging. More historical re-selection will not supply it.

### Gaps
- §10 asks for official settlement values. Physically settled ETF options have none, so the execution-realism item for E2 cannot be passed on this data by construction. Any ETF carry lane would have to be defined with E1 or with an explicit assignment process.
