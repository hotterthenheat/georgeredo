# SPXW short premium on complete chains with official settlement: re-run of T-E and the pre-registered grid, plus tail stress and margin

Scope and provenance. This note answers the developer review of the round-2 report (`reports/High win rate 0DTE lanes.md`), adopted as [COMPASS_RESEARCH_PLAN.md §10](file:///home/user/georgeredo/COMPASS_RESEARCH_PLAN.md). The review named three weaknesses of the round-2 SPXW study ([empirical_spxw_grid_and_te.md](file:///home/user/georgeredo/research_notes/High%20win%20rate%200DTE%20lanes/empirical_spxw_grid_and_te.md)): (1) option chains were stored only within ±2 % of the 09:31 SPX price, so large-move days were skipped; (2) hold-to-settlement used the SPX print stamped 16:00 instead of the official close; (3) sizing used the worst TRAIN day, which 2025-04-09 exceeded. Every number below was computed in this re-run from local data (no ThetaData login). Code, protocol and results are in [research/thetadata/hwr_grid/spxw_v2/](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/README.md); generated tables are in [RESULTS.md](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/RESULTS.md). The round-2 folder `../spxw/` was not modified. "v1" means round 2 and "v2" means this re-run.

Design. The pre-registration ([../spxw/PREREGISTRATION.md](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw/PREREGISTRATION.md)) is used unchanged: same T-E rule, window and holdout; the same 2,736 distinct grid configurations; TRAIN 2022-05-13 → 2024-12-31 and TEST 2025-01-02 → 2026-10-09; the same S1/S2 selection rules; the same seeds (7, 8, 11–15) and committed random-entry minutes; the same fills (sell at the NBBO bid, buy at the ask) and fees ($1.00 per contract per side). Only two inputs change. (a) Quotes come from the complete same-day chain (every listed strike). (b) Every settlement value is the Cboe SPX close from [settlement_reconciliation.csv](file:///home/user/georgeredo/research/thetadata/settlement_audit/settlement_reconciliation.csv). The protocol, an amendment, and the TRAIN-selection hash were each written before the statistics they govern; times and hashes are in [protocol_sha256.txt](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/protocol_sha256.txt):
- protocol at 01:43 UTC;
- Amendment 1 at 02:20 UTC;
- TRAIN selection hashed at 02:27 UTC, before any TEST session was simulated;
- Amendment 1 resolved at 03:11 UTC, with the TRAIN selection re-hashed at 03:11 UTC.

**Amendment 1 (resolved).** At first the complete-chain fetch did not deliver 2024-06-21, and that session ran from the v1 band file. The complete file arrived at 03:03 UTC. The fallback trade and skip files were then deleted and the whole pipeline re-run. **No TEST-period figure changed** and the S1/S2 selections are unchanged. TRAIN, T-E-window-baseline and whole-sample figures moved slightly. Changed numbers below show the earlier fallback value as "was …". Every changed cell, before → after, is in [resolution_changes.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/resolution_changes.csv.gz) (`resolution_diff.py`), summarised in [RESULTS.md §0](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/RESULTS.md).

Conventions: P&L in $ per 1-lot (one contract per leg, ×100); 95 % intervals are day-clustered percentile bootstraps (5,000 draws, seed 7); "LB" is the lower bound of that interval.

## Q1. Data integrity: does the complete chain contain every strike the grid needs?

### Takeaway
Yes, on every TEST session. Coverage is now complete for all 1,097 regular sessions (was 1,096 before 2024-06-21 arrived). At every fixed entry and every committed random-entry minute, no needed short or wing strike lies beyond the listed range. The complete files agree row for row with the band files where the two overlap, except on 2024-06-21: that day's delivered complete file is itself partial. A handful of cases are still missing. They come from quote gaps on two sessions, 2022-06-02 and 2024-06-21, plus two no-credit wing cases; they do not come from storage. The complete chain supplies 531 naked and 1,739 winged fixed-entry trades whose strikes the v1 band could not hold (was 528 / 1,734), including every April 2025 day.

### Cited Findings
- **Sessions.** Complete chains exist for all 1,097 regular sessions 2022-05-13 → 2026-10-09 (was 1,096, with 2024-06-21 run from the band file). Settlement is the Cboe close on all 1,097 — [integrity_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_summary.json), [run_status.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/run_status.json)
- **Consistency and size.** Of the 37,315,085 v1 band-file rows, 37,307,656 are present in the complete files with identical bid and ask. The other 7,429 all belong to 2024-06-21 and are absent from that day's delivered complete file: 6 band strikes are missing entirely there, and other strikes lack one side (before the file arrived, the check was 37,315,085 of 37,315,085). That file has 333 strikes, 127 of them with only a call or only a put. The complete files hold 194,604,219 rows, with a median of 207 strikes per session (range 90–644; was 194,416,539 and 34–644). The SHA-256 of every file is listed — [integrity_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_summary.json), [integrity_sessions.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_sessions.csv.gz)
- **Needed legs.** The check covers 4,388 fixed-entry cases and 5,485 random-minute cases per k, with k ∈ {0, 0.5, 1.0, 1.5}:
  - "Needed strike beyond the listed range": 0 for every leg (short call, short put, call wing, put wing), every k, fixed and random.
  - Listed strike without a usable quote at the entry minute: 0–5 per leg and k.
  - The ATM strike round(S/5)×5 was not listed twice (14:05 on 2025-05-12 and 2026-04-09; the nearest listed strike was used).

  Source: [integrity_by_k.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_by_k.csv), [diagnostics.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/diagnostics.csv)
- **Still missing (fixed entries and committed random minutes).** 34 entry × k cases could not be built (was 44):
  - 2022-06-02: 15 cases, `no_quote`. The complete file has 5,802 null bids that morning.
  - 2024-06-21: 17 cases, `no_quote` (was 27 from the band file, in which 9 of 34 strikes carried only one side).
  - 2024-08-05: two winged cases at 10:00 (k = 1.0 and 1.5) with `no_credit`.

  The list is in [integrity_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_summary.json).
- **Every minute 10:00–14:30 × 8 structure cells.** 2,376,562 cases are buildable (was 2,376,148). The rest: 1,719 `no_quote` (was 2,133), of which 948 fall on 2022-06-02, 755 on 2024-06-21 (was 1,169), 8 on 2025-07-30 and 8 on 2025-04-09; 8 `zero_bid`; 7 `no_credit` — [integrity_minutes_nonok.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_minutes_nonok.csv), [integrity_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_summary.json)
- **What the band hid.** Fixed-entry trades that the v1 band could not hold but the complete chain prices: 531 naked and 1,739 winged (was 528 / 1,734). For the k = 0.5 strangle at 14:05 these are 30 dates; at 13:00 they include 2025-04-02, 04-04, 04-07, 04-08, 04-09, 04-10, 04-11, 04-21 and 04-24 — [integrity_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_summary.json)
- **Coverage now.** TEST: 441/441 sessions for the straddle and the k = 0.5 and k = 1.0 strangles at 13:00 and 14:05. TRAIN: 656/656 for the straddle at both times and for the strangles at 14:05; 654/656 for the k = 0.5 strangle at 13:00 (`no_quote` on 2022-06-02 and 2024-06-21). Before the file arrived, 655/656 for the strangles. [coverage.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/coverage.csv)
- **Exit rows and settlement.** Exit rows were forward-filled for 0 trades. Settlement source "not Cboe close": 0 sessions. Cboe close minus 16:00 print: up to 18.32 points in TEST and 3.85 points in TRAIN — [diagnostics.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/diagnostics.csv)

- **2024-06-21 trades on the delivered complete file.**
  - The 14:05 k = 0.5 strangle (round-2 S2) now trades, at +$328.
  - The re-selected S2 also trades: the same strikes, 5475/5445, at +$328.
  - The 13:00 straddle is unchanged at +$1,480.
  - The file's gaps still move the strikes. At 14:05 the rounded ATM strike 5460 had no usable call/put pair, and the k = 0.5 short strikes lie 8.37 and 7.63 points beyond their targets.

  Source: [stress_trades.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/stress_trades.csv.gz), [integrity_legs.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_legs.csv.gz), [diagnostics.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/diagnostics.csv)

### Inferences
- The storage band was the only reason large-move days were skipped. With complete chains the residual gaps are vendor quote gaps on two TRAIN sessions; none falls in TEST. The §10 data-integrity item ("full-chain coverage on every test date") is therefore met for TEST.

### Gaps
- 2024-06-21's delivered complete file is itself partial. A further re-request, or a union with the band file (identical where both have a row), would be needed for a fully complete day. Neither was done; the protocol uses the complete file as delivered.
- The quote gaps on 2022-06-02 were not investigated with the vendor.

## Q2. T-C and T-E on complete data with the official close

### Takeaway
The T-C reproduction is now exact on all 339 sessions. **T-E still FAILS**, with essentially the same numbers as v1. The holdout's v1 "confirmation" disappears: it had come from two sessions where the band forced the wrong ATM strike, and from the 16:00 print.

### Cited Findings
- **T-C reproduction.** All checked fields equal on 339/339 sessions: strike, credit, 15:55 P&L and settlement P&L under T-C's own settlement source. v1 matched 337/339. Sell bid / buy back at the 15:55 ask: +$72.43 [−75.80, +214.25] (published +$72.43 [−75.8, 214.2]). Hold to the official close: +$156.23 [+4.95, +304.45] (published +$156.8 [+5.76, +305.0]); the only difference is 2026-06-09, where T-C used the 16:00 print — [tc_reproduction.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/tc_reproduction.csv), [te_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/te_summary.json)
- **T-E window (2022-05-13 → 2025-05-29), Cboe close.** n = 663, **+$26.94 [−136.73, +170.75]**, win rate 61.4 %, PF 1.048, max drawdown −$38,494. Worst days: 2025-04-09 −$34,022, 2024-04-04 −$9,211, 2022-11-30 −$9,063. Verdict **FAIL**. v1: +$26.37 [−138.17, +169.77] — [te_results.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/te_results.csv), [cmp_te.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_te.csv)
- **T-E window sensitivities and baseline.**
  - 16:00-print settlement: +$27.06 [−134.89, +171.05].
  - One tick worse per leg: +$16.94.
  - 15:55 buy-back: −$11.71.
  - Lane minus random entry: −$24.42 [−91.79, +40.67] (was −$24.03 [−91.47, +41.50]), against a round trip of $20.02. The lane itself is unchanged.

  Source: [te_results.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/te_results.csv)
- **Holdout (2025-06-02 → 2026-10-09).** n = 299, **+$138.97 [−19.69, +288.50]**, verdict "does not confirm". v1 gave +$152.93 [+1.91, +294.08], "confirms". In v2 the 16:00 print gives +$141.99 [−16.44, +287.36], so the chain change costs $10.94 and the settlement change $3.02. Lane minus random: −$23.41 [−158.08, +106.06] — [cmp_te.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_te.csv), [te_results.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/te_results.csv)
- **T-E.4 tail rule (6.33 % stress, 8 % budget).** The 2025-04-09 loss of $34,022 equals 11.75 % of that day's tail capital. The day's 13:00 → settlement move was 8.49 % — [te_summary.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/te_summary.json)

### Inferences
- H13 stays rejected. Complete chains and the official close change the T-E window by less than $1 per straddle. On the T-E rule, v1 and v2 differ mainly in the holdout. There the band had replaced the 13:00 ATM strike on 2025-11-20 and 2026-06-09 with the nearest stored strike, which flattered the result.

### Gaps
- None specific to T-E beyond those in Q5. The tail rule written before the run was again too small.

## Q3. Grid: selection on complete TRAIN data, TEST results, and how many lower bounds chance would produce

### Takeaway
Re-selection on complete TRAIN data keeps S1 but changes S2: it becomes a k = 1.0 strangle with a 2× stop, and that S2 fails on TEST. The round-2 S2 definition (14:05 ±0.5·EM strangle, held to the Cboe close, skipping FOMC and month-end) keeps a positive TEST LB on complete data, including the ten days the band had skipped. It also survives a Bonferroni correction for the two TRAIN selections. Across the grid, however, the number of positive TEST lower bounds (61) is within what chance produces. Within TEST, the positive result is concentrated in 2025.

### Cited Findings
- **Selections.** The TRAIN selection was written before any TEST session was simulated; 2,736 configurations were eligible, 1,455 of them with TRAIN win rate ≥ 70 % — [selection_train.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/selection_train.json), [protocol_sha256.txt](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/protocol_sha256.txt), [cmp_selection.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_selection.csv), [gate.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/gate.csv)

  | Rule | TRAIN mean [95 % CI], win rate | TEST mean [95 % CI], win rate | Other TEST figures |
  |---|---|---|---|
  | S1 `N0.0\|14:05\|tp0\|st1\|E2\|F3` (unchanged) | +$164.59 [+92.72, +236.58], 62.4 % (was +$165.25 [+93.38, +237.01]) | +$122.78 [−2.99, +246.45], 58.7 % | v1 TEST +$99.13 [−33.97, +225.95] |
  | Re-selected S2 `N1.0\|14:05\|tp0\|st2\|E2\|F3` | +$94.99 [+58.50, +130.72], 74.9 %, n = 606 (was +$94.61 [+58.68, +130.08], n = 605) | +$52.54 [−22.24, +122.49], 73.2 % | Bonferroni(2) bound −$33.59 |
  | **Round-2 S2 definition** `N0.5\|14:05\|tp0\|st0\|E2\|F3` | +$123.98 [+49.62, +192.92], 72.1 %, n = 606 (was +$123.64 [+51.13, +194.44], n = 605; v1 +$124.52 [+51.97, +193.75]) | **n = 407, +$151.17 [+42.15, +251.73], 70.8 %** | PF 1.49, max drawdown −$13,022, worst day −$7,131 (2026-03-09); coverage 100 %; one-tick-worse mean +$141.17; round trip $13.20; **Bonferroni(2) bound +$26.23**. v1 TEST: n = 397, +$162.00 [+63.16, +258.44] |
  | T-E's rule as a grid cell (13:00, F4) | — | +$85.56 [−171.50, +291.52] | — |
- **v1 → v2 decomposition for the round-2 S2 on TEST.**
  - v1: +$162.00 (n = 397).
  - Complete chain, 16:00 print: +$158.66 (n = 407).
  - Complete chain, Cboe close: +$151.17.
  - On the 397 shared days the 16:00-print P&L is identical to v1; the Cboe close lowers it to +$156.30.
  - The 10 added days sum to −$525. In date order: 2025-04-04 −3,744; 04-07 +4,448; 04-08 −2,825; 04-09 +2,778; 04-11 +3,088; 04-21 −2,452; 04-24 +1,358; 2025-10-10 −3,051; 2025-11-20 +2,428; 2026-02-03 −2,553.

  Source: [cmp_decomposition.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_decomposition.csv)
- **Robustness of the round-2 S2 on TEST.**
  - By year: 2025 (n = 228) +$228.60 [+81.09, +373.09]; 2026 (n = 179) +$52.54 [−102.00, +201.29].
  - Without the 5 best days the LB is +$5.22; without the 10 best it is −$15.63. The 10 best days carry 43.3 % of the TEST total.
  - Without April 2025: +$126.16 [+26.41, +221.67].

  Source: [cmp_robustness.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_robustness.csv)
- **Neighbouring S2-family configurations on TEST** (v2, with v1 for comparison where shown):
  - k = 0.5 at 14:05, E2, no TP or stop, by filter: F0 +$124.46 [+9.88]; F1 +$115.32 [+2.72]; F4 +$111.22 [−1.28].
  - Same rule exiting under E1 (F3): +$132.85 [+33.24].
  - Adding a 2× stop: +$103.33 [−1.96].
  - k = 1.0 with no stop (F3): +$112.47 [+30.72].
  - The 13:00 k = 0.5 F3 strangle, the v1 band-check example: +$181.71 [−45.50], against v1 +$260.19 [+135.54].

  Source: [grid_configs.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/grid_configs.csv.gz), [v1 grid_configs.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw/results/grid_configs.csv.gz)
- **TRAIN top 10 on TEST.** 2 of 10 keep LB > 0 (v1: 6 of 10) — [selected_test.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/selected_test.csv)
- **Chance count (seed 8, 5,000 draws).** TEST: 61 configurations with LB > 0, against 39.8 expected under the global null (95th percentile 196, 99th 394), P = 0.187. v1 had 135 against 50.6 (95th percentile 232). TRAIN: 227 against 54.3 (95th percentile 265; was 225 against 54.0, 95th percentile 262).
- **Reality check and Romano–Wolf.** With a fixed s.e., TEST max t is 5.22, p = 0.000, with 11 Romano–Wolf rejections: the 10:00 k = 1.5 TP-25 % family and 14:05 k = 1.5 F3. The round-2 S2 is not among them. With within-draw studentisation, p = 0.235 and there are 0 rejections.

  Source for these two items: [cmp_multiplicity.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_multiplicity.csv), [multiplicity.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/multiplicity.json)
- **Descriptive grid counts.** 20 configurations have LB > 0 in both TRAIN and TEST. 42 have TEST LB > 0 with TEST win rate ≥ 70 %, all naked (k = 1.5: 21; 1.0: 12; 0.5: 8; 0: 1). One winged configuration has TEST LB > 0 — [test_wr70_lbpos.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/test_wr70_lbpos.csv), [grid_configs.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/grid_configs.csv.gz)

### Inferences
- **The selection is unstable.** On band-truncated TRAIN data the rule picked k = 0.5. On complete TRAIN data it picks k = 1.0 with a stop, and the new pick fails on TEST. The round-2 S2 is a fixed, previously published definition that holds up on corrected data. It is not what an honest re-selection would choose today. Its TEST evidence is therefore one pre-specified rule evaluated on a period whose band-version result was already published; it is not a fresh holdout.
- **Complete data mostly removed false positives.** The TEST LB > 0 count fell from 135 to 61, and the 13:00 strangles that had looked strong now include 2025-04-09 and lose their bounds. The 14:05 k ≤ 0.5 family, held to settlement and skipping FOMC (plus month-end), stays positive.
- **The S2 result is a 2025 result.** 2026 alone is indistinguishable from zero. The LB needs the five best days, most of them post-crash April 2025 sessions that the band had hidden.

### Gaps
- The study has no fresh out-of-sample period. All 2022-05 → 2026-10 data has now been used.
- 2026 alone (n = 179) cannot separate the lane from zero.

## Q4. Random-entry comparison on matched days: what changed and why

### Takeaway
In v1 the round-2 S2 trailed random entry by $92.82. In v2 it leads by $22.60. Both numbers were artefacts of which days were compared. On the days both studies traded, random entry still beat the 14:05 lane by about $90. The v2 lead comes from the ten band-skipped days, and almost entirely from one of them, 2025-04-09: every random entry that day fell before a 2.6 % one-minute jump, while the 14:05 entry came after it. Without that day the lane trails random entry by $64.37. Nothing here shows timing skill, which is consistent with classifying the lane as carry.

### Cited Findings
- **v1, TEST.**
  - Lane on its 397 matched days: +$162.00.
  - Random per-date mean on the same days: +$254.82, so lane − random = −$92.82.
  - Pooled random: +$165.10 over 2,005 draw-trades. These include 25 draw-trades on days the lane had skipped, which averaged −$6,432.84 (2025-04-09 −33,127; 04-08 −17,502; 2025-11-20 −16,029; 2025-10-10 −10,554).

  Source: [cmp_random_explain.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_random_explain.csv)
- **v2, TEST.**
  - All 407 days are matched, each with 5 draws, so pooled equals matched.
  - Lane +$151.17 against random +$128.57: **lane − random +$22.60 [−147.61, +261.12]**.
  - Per-draw means: +$110.95, +$23.44, +$261.68, +$87.51, +$159.26.
  - Per-draw maximum drawdowns: −$32,372 to −$50,147.

  Source: [selected_random_baseline.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/selected_random_baseline.csv)
- **Where the difference comes from.**
  - On the same 397 v1-matched days, v2 random averages +$246.60 and the lane +$156.30.
  - On the 10 added days the lane averages −$52.50 and random −$4,557.44.
  - Most influential day: 2025-04-09, lane − random = +$35,332.
  - Lane − random without that day: **−$64.37 [−168.56, +45.84]**; without the 3 most influential days: −$103.36 [−196.26, −7.40].

  Source: [cmp_random_explain.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_random_explain.csv)
- **2025-04-09 minute path.** SPX was 5,013.84 at 13:19 and 5,143.92 at 13:20, a one-minute move of +2.59 %; it was 5,380.10 at 14:05; the Cboe close was 5,456.90. The five committed random minutes were 10:15, 10:22, 10:27, 10:32 and 12:39 — [spx_2025-04-09_path.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/spx_2025-04-09_path.csv)
- **TRAIN and other rules.**
  - Round-2 S2, TRAIN: lane − random +$25.66 [−37.98, +88.73]; without the most influential day +$15.60 (was +$26.40 [−36.85, +90.00] and +$16.32).
  - T-E rule in the grid: TRAIN −$55.26 [−114.75, +5.08] (was −$54.81 [−114.45, +5.37]); TEST +$17.58 [−107.16, +138.49].
  - Re-selected S2: TEST −$11.93 [−103.79, +95.36].

  Source: [cmp_random_explain.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_random_explain.csv), [selected_random_baseline.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/selected_random_baseline.csv)

### Inferences
- **The v1 figure was biased by the band.** v1's matched comparison dropped the band-skipped lane days. The random entries' worst days were mostly on those same days, so they also dropped out of the matched set but stayed in the pooled figure. That is why v1's pooled (+$165.10) and matched (+$254.82) random means disagreed by $90.
- **The v2 lead is one event's timing.** It rests on whether the entry fell before or after the 2025-04-09 announcement jump. That is not a repeatable property of 14:05, so the random-entry item should be read as "not distinguishable from random". This is the outcome §10 anticipates for a carry lane.

### Gaps
- Five random draws per day give a noisy baseline on single extreme days. A larger number of draws would narrow it, but would not change the conclusion.

## Q5. Tail stress, worst historical moves, margin, capital per lot and drawdowns

### Takeaway
For a naked 0DTE SPXW strangle or straddle, the settlement loss under a large move is close to the move times the notional: about −9.7 % of notional per lot for a 10 % move and −14.7 % for a 15 % move. The 2017–2026 minute record contains no 14:05→close move beyond 5.3 %. Its largest 13:00→close move is 8.49 % (2025-04-09). Reg-T margin is about 15 % of notional and approximate portfolio margin about 7.8 %. Capital sized so that a ±10 % (±15 %) shock costs ≤ 25 % is a median $261,570 ($396,198) per lot in TEST. At that capital the round-2 S2's TEST mean returns 13.4 % (8.9 %) a year, with low bootstrap drawdown probabilities. Those probabilities come from history, which contains no shock of the size the capital is built for.

### Cited Findings
- **Shock P&L for the round-2 S2** (TEST, n = 407; median and worst over trades, $ per lot; % is the median share of notional) — [stress_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/stress_summary.csv)

  | SPX move from entry | Median | Worst | Median % of notional |
  |---|---|---|---|
  | −15 % | −98,941 | −116,107 | −14.77 % |
  | −10 % | −65,226 | −76,976 | −9.77 % |
  | −8.42 % | −54,742 | — | — |
  | −5 % | −31,916 | — | — |
  | +5 % | −31,858 | — | — |
  | +8.42 % | −54,750 | — | — |
  | +10 % | −65,377 | −77,354 | — |
  | +15 % | −98,881 | −116,501 | — |

  At the last trade (2026-10-09, SPX 7,808.34): −10 % → −$76,976; −15 % → −$116,018.
- **Other rules under the same shocks.** The re-selected S2 and the T-E rule are within 1 % of these figures: T-E rule −10 % median −$65,182 and −15 % median −$98,766. Actual worst days: round-2 S2 −$7,146 in TRAIN (2024-04-04) and −$7,131 in TEST (2026-03-09); re-selected S2 −$4,999 (2025-04-08); T-E rule −$9,211 in TRAIN and −$34,022 in TEST (2025-04-09) — [stress_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/stress_summary.csv)
- **Worst SPX moves, 2017-06-01 → 2026-10-09** (2,333 regular sessions; official close; 16:00 print in brackets) — [worst_moves.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/worst_moves.csv), [stress_meta.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/stress_meta.json)
  - 13:00 → close: up +8.490 % on 2025-04-09 (5,029.87 → 5,456.90) [+8.419 %]; next +6.322 % on 2020-03-13. Down −4.482 % on 2020-03-12 [−4.511 %]; next −3.962 % on 2020-03-16.
  - 14:05 → close: up +5.284 % on 2020-03-13 [+5.296 %]; next +4.240 % on 2020-03-10. Down −3.302 % on 2020-03-20 [−3.370 %]; next −3.134 % on 2022-11-02.
- **Margin per lot, TEST medians** — [margin_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/margin_summary.csv), rule text in [README.md](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/README.md)
  - **Reg-T, round-2 S2:** $100,608, 15.0 % of notional (range $76,469–$117,279). At the last trade: $116,734.
  - The rule text used is Cboe Rule 10.3(c)(5) as quoted in SEC Release 34-97019, 88 FR 14416: "100% of the current market value of the option plus 15% … of the amount equal to the index value multiplied by the index multiplier minus the amount, if any, by which the option is out-of-the-money … minimum … plus 10% of the index value … for a call or 10% of the exercise price … for a put". For straddles and strangles, Cboe's strategy-based margin page gives "short put or short call requirement, whichever is greater, plus the option proceeds of the other side".
  - The simplified formula requested (10 % of the index for both minimums) gives the same median.
  - **Approximate portfolio margin** (largest expiration-value loss over −8 % … +6 %): $51,928, 7.8 % of notional. The worst point was the −8 % end for every trade. At the last trade: $61,358.
  - The T-E rule gives Reg-T $102,752 and portfolio margin $51,788.
- **Capital per lot** (±shock loss ≤ 25 % of capital) and annualized return — [margin_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/margin_summary.csv), [capital_returns.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/capital_returns.csv)
  - **Round-2 S2, TEST medians:** $261,570 (10 % rule) and $396,198 (15 % rule). At the last trade: $308,578 and $464,744. Reg-T is a median 0.38 and 0.25 of that capital.
  - **Annualized return** = TEST mean $151.17 × 232.6 trades a year ÷ median capital: **13.44 % (10 % rule) and 8.87 % (15 % rule)**. The per-trade return-ratio version gives 15.27 % and 9.93 %; the full 2022–2026 sample gives 14.96 % and 9.85 % (was 14.93 % and 9.83 %).
  - Re-selected S2: 4.70 % and 3.10 %. T-E rule: 7.25 % and 4.79 %.
  - The worst TEST day of the round-2 S2 cost 2.75 % (10 % rule) and 1.81 % (15 % rule) of capital. The T-E rule's 2025-04-09 cost 20.42 % and 12.73 %.
- **Drawdowns at that sizing** (circular block bootstrap of the complete-data daily series 2022-05-13 → 2026-10-09, block 20 sessions, 3,000 paths, seed 7, one-year horizon of 252 sessions) — [drawdown_bootstrap.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/drawdown_bootstrap.csv)
  - **Round-2 S2, 15 % rule:** median maximum drawdown −3.06 % (5th percentile −5.12 %); P(drawdown > 10 %) = 0.000; P(end below start) = 0.0083; longest spell under water median 55 sessions (95th percentile 144).
  - **Round-2 S2, 10 % rule:** median −4.63 % (5th percentile −7.71 %); P(> 10 %) = 0.0083; P(end below start) = 0.0087; spell median 56 (95th percentile 145).
  - **Historical path:** maximum drawdown −5.58 % (10 % rule) and −3.69 % (15 % rule); longest under water 154 sessions.
  - Blocks of 5 and 60 sessions give the same picture: one-year P(> 10 %) ≤ 0.034 at the 10 % rule and ≤ 0.004 at the 15 % rule.
  - **T-E rule, 10 % rule:** P(drawdown > 10 %) = 0.490, P(> 20 %) = 0.222, P(end below start) = 0.353; historical maximum drawdown −22.36 %, longest under water 589 sessions.
- **G.8 sizing, as pre-registered** (8 % of the worst TRAIN loss), round-2 S2: TRAIN worst loss $7,146 → $89,325 per lot. That capital is below Reg-T, and TEST's worst day ($7,131) did not exceed the TRAIN worst. The T-E rule's TEST worst ($34,022) is 3.7× its TRAIN worst ($9,211) — [sizing_test_lbpos.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/sizing_test_lbpos.csv), [stress_summary.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/stress_summary.csv)

### Inferences
- **What the stress-based capital implies.** It is about 2.6× Reg-T at the 10 % rule and 3.9× at the 15 % rule. At the 15 % rule, one −15 % settlement shock (25 % of capital) costs about 2.8 years of the TEST-mean income. The 13.4 % and 8.9 % returns are therefore the price of surviving shocks larger than any in the 2017–2026 record. A 13:00 entry has already met an 8.5 % one-afternoon move; a 14:05 entry has met 5.3 %.
- **What the bootstrap cannot show.** The drawdown probabilities resample only observed days. They describe the ordinary-day risk at that sizing, not the shock the capital was sized for. Worst-day sizing (G.8, $89k) is not tail survival: it sits below Reg-T, and at TEST index levels a 10 % move would cost about 73 % of it ($65,226 of $89,325).

### Gaps
- Portfolio margin is an expiration-value approximation, not a TIMS run. Brokers' 0DTE house requirements and intraday margin calls are not modelled.
- The shocks assume no executable exit before settlement (gap). Stops in the re-selected S2 are ignored in the stress figures.
- Only one 13:00-or-later move above 6.4 % exists in the record, so the frequency of 10–15 % afternoon moves cannot be estimated from data.

## Q6. Gate verdict under COMPASS §10 (carry lane)

### Takeaway
**Nothing is promotable yet. Forward validation has not started.** Of the three rules, only the round-2 S2 definition (14:05 ±0.5·EM short strangle, held to the Cboe close, skipping FOMC and month-end) meets every gate item that can be computed from history. The re-selected S2 and T-E's rule fail the statistical-validity item. The round-2 S2 is a reasonable candidate for T-G forward paper trading as a carry lane, sized by the stress capital above. Its historical evidence carries three caveats: selection instability, dependence on 2025, and a TEST period that is not unseen.

### Cited Findings (item by item; [carry_gate.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/carry_gate.csv))
- **Data integrity.** TEST: 0 of 441 sessions are missing a needed strike or quote at 14:05 (k = 0.5), and complete chains exist for every TEST session. The same holds at 14:05 (k = 1.0) and 13:00 (k = 0) → **met on TEST**. Whole sample: 1,097/1,097 complete chains (was 1,096/1,097 with 2024-06-21 on the band fallback); 2024-06-21's delivered file is partial (Q1). Every file is hashed — [carry_gate.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/carry_gate.csv), [integrity_sessions.csv.gz](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/integrity_sessions.csv.gz)
- **Execution realism.** Bid/ask fills at the entry-minute NBBO, $1 per contract per side, settlement at the Cboe close on all sessions, and a one-tick-worse sensitivity (round-2 S2 TEST mean +$141.17). Size and queue are not modelled → **met as modelled**, not yet verified live — [gate.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/gate.csv), [diagnostics.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/diagnostics.csv)
- **Statistical validity (complete data, out of sample, multiplicity).**
  - Round-2 S2: TEST LB +$42.15, Bonferroni(2) bound +$26.23, n = 407, 21.2 months → **met as specified**. Caveats from Q3: 2026 alone is not significant; the LB depends on the best 5 days; TEST was seen in v1; and the grid-wide TEST count of 61 is within chance.
  - Re-selected S2: LB −$22.24 → **not met**.
  - T-E rule: LB −$171.50 in the grid TEST; −$136.73 in the T-E window → **not met**.

  Source: [gate.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/gate.csv), [cmp_robustness.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_robustness.csv), [multiplicity.json](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/multiplicity.json)
- **Tail survival.** All stated stresses were computed: the worst historical moves, 2025-04-09's 8.42–8.49 %, and ±10 % and ±15 %. Reg-T (median $100,608) and approximate portfolio margin ($51,928) are stated. Capital per lot is $261,570 / $396,198 (TEST median) with the ±10 % / ±15 % shock held at 25 %. Return on that capital is 13.4 % / 8.9 % a year; one-year P(drawdown > 10 %) is 0.008 / 0.000 → **met at the stated budget** for the round-2 S2. For the T-E rule at the same capital: P(drawdown > 10 %) 0.490 and P(end below start) 0.353 — [capital_returns.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/capital_returns.csv), [drawdown_bootstrap.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/drawdown_bootstrap.csv)
- **Forward validation.** **Not yet**: 0 of at least 150 sessions and 0 of at least 7 months — [COMPASS_RESEARCH_PLAN.md §10](file:///home/user/georgeredo/COMPASS_RESEARCH_PLAN.md)
- **Classification.** **Carry.** The random-entry item does not apply. Q4 shows no timing skill: lane − random without 2025-04-09 is −$64.37 — [cmp_random_explain.csv](file:///home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2/results/cmp_random_explain.csv)

### Inferences
- **Register.** H13 (T-E) remains closed. The re-selected S2 should not replace the round-2 definition. H15 can proceed to T-G forward paper trading as defined, with these settings:
  - capital at the stress budget, not the G.8 worst-day budget;
  - the Cboe close as the settlement reference;
  - logging of the random-time baseline for information only.
- **Expectations for forward trading.** The historical case for H15 is a positive 2025 plus a 2026 that is indistinguishable from zero. Forward trading should be judged on its own interval. It should not be read as a continuation of 2025.

### Gaps
- The forward gate is the binding item and cannot be shortened.
- Live NBBO fills, broker 0DTE margin and settlement-day operations (exercise-settlement value publication) remain unverified.
