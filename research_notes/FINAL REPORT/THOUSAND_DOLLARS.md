# $1,000 in each strategy

**Repository:** georgeredo, branch `claude/lucid-heisenberg-bpyq7k`. **Built:** 2026-10-23 by `research_notes/FINAL REPORT/build/thousand.py`, from the trade lists of `FINAL_RESEARCH_REPORT.md` (14a30a7).

**What this is.** Every row of the final report's page-1 table (`FINAL_RESEARCH_REPORT.md`, commit 14a30a7), each
on the same strategy, instrument and period as listed there, started with **$1,000** and walked through its own trades in
date order. The trades are the report's own (its loaders in `build/`); nothing was re-tested, re-priced or fetched.

**Method A, "all in each day".** Each session, the whole balance is split equally across that session's trades. Each
slice earns that trade's return in the row's own unit (% of premium paid, % of max risk, % of the credit received, % of
the cash set aside, or % of notional, as the table uses). The balance compounds session by session. A trade can lose more
than 100% of its unit (a short straddle, or a credit loss bigger than the credit), and a session whose only trades are
long options that all expire worthless loses 100%; if a session takes the balance to zero or below, the row is **wiped
out** on that date and stops.

**Method B, "10% per trade".** Each trade uses 10% of the balance at the start of its session. When a session has more
than ten trades, each uses 100% ÷ the number of trades, so a day never uses more than the whole balance. It compounds the
same way. On a session with ten or more trades, B uses the whole balance too, so a row that always trades ten or more a
session ends the same under A and B.

**For both.** Fractional contracts are allowed. That is not realistic: $1,000 often cannot buy one real SPXW contract,
or post the margin on a short straddle or strangle, and short-premium rows would need far more than $1,000 in a real
account. Costs are already inside each trade's return, as the study ran it. There are no taxes, no margin interest and
no slippage beyond the study's own fills. A trade is booked on its entry session (the trade lists carry the entry date
only), so a trade held for days or weeks is treated as if its money came back the same day. "Worst point" is the lowest
balance under method A and its date ("start" if it never fell below $1,000).


**In plain words.** These are what each strategy did over its own study period, not a forecast of what it will do next. Most rows lose: 61 of 75 end below $1,000 under method A (29 of them wiped out) and 53 of 75 under method B. The big gains come from short-premium and spread rows (5 of the 14 that end above $1,000 under A, led by #20a), whose real-account margin or cash $1,000 could not post; the other 9 are 7 stock rows with small gains, the vendor's own Epoch 1 cards and a five-session preview.

## Page 1. Every row, sorted by the method A ending balance

| # | strategy | instrument | period | trades | ending $ (A) | ending $ (B) | worst point (A) | verdict from the report |
|------|------------------------------------------------------|------------------|---------------------------|------------|---------------------|---------------------|---------------------------|------------------------------------|
| 1 | #20a Phase 2 hyp B: boundary touch — SPY 2-wide 25-delta credit spread, held (the … | SPY | OOS 2025–26 | 2,600 | $4.18 × 10¹¹ | $470,760 | $171 (2025-03-03) | No edge |
| 2 | #1 GeorgeFi vendor cards (the vendor's own recorded P&L) — *vendor-recorded, not re-marked* | all names | Epoch 1 | 546 | $8,015 | $14,424 | $1,000 (start) | Not evidence |
| 3 | #7j-atm_put S17 Index put-writing: monthly ATM cash-secured put | all names | 2012-06→2026-10 | 334 | $2,725 | $1,239 | $999 (2012-10-19) | PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 … |
| 4 | #32 Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock) | QQQ | single test | 3,299 | $2,207 | $1,093 | $681 (2020-02-03) | FAIL |
| 5 | #7j-put_30d S17 Index put-writing: monthly 0.30-delta cash-secured put | all names | 2012-06→2026-10 | 334 | $2,019 | $1,162 | $1,000 (start) | PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 … |
| 6 | #32 Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock) | SPY | single test | 2,177 | $1,874 | $1,071 | $856 (2019-12-09) | FAIL |
| 7 | #37b Edge H8: turn of the month (SPY, QQQ stock) | QQQ | single test | 172 | $1,852 | $1,068 | $1,000 (start) | SPY FAIL; QQQ PASS at 1× only |
| 8 | #7j-put_15d S17 Index put-writing: monthly 0.15-delta cash-secured put | all names | 2012-06→2026-10 | 334 | $1,487 | $1,089 | $981 (2020-02-21) | PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 … |
| 9 | #37b Edge H8: turn of the month (SPY, QQQ stock) | SPY | single test | 117 | $1,407 | $1,037 | $975 (2018-04-27) | SPY FAIL; QQQ PASS at 1× only |
| 10 | #37a Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED | QQQ | single test | 108 | $1,250 | $1,023 | $978 (2016-04-26) | PASS both names |
| 11 | #37a Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED | SPY | single test | 77 | $1,156 | $1,015 | $999 (2017-09-19) | PASS both names |
| 12 | #41a EMA system v0: PREVIEW on 2026-10-12 → 16 (5 sessions) — *PREVIEW* | Config A X1 | preview 2026-10-12→16 | 57 | $1,077 | $1,109 | $642 (2026-10-12) | PREVIEW |
| 13 | #35 Edge H4: market intraday momentum (SPY, QQQ stock) | QQQ | test 2025-10-13→2026-10-22 | 257 | $1,035 | $1,003 | $972 (2026-04-07) | FAIL |
| 14 | #9a Lifecycle P1: Quick Scalps → cash-secured put sale (portfolio) | all names | hold-out 2025-10→2026-10 | 122 | $1,007 | $1,001 | $988 (2026-03-25) | Rejected |
| 15 | #35 Edge H4: market intraday momentum (SPY, QQQ stock) | SPY | test 2025-10-13→2026-10-22 | 257 | $988 | $999 | $962 (2026-03-09) | FAIL |
| 16 | #6b T-B: gamma-conditioned last-30-minute momentum in SPY shares (H10) | SPY | negative-gamma days 2024-05→2026-10 | 299 | $912 | $991 | $906 (2026-09-23) | FAIL |
| 17 | #40b Compass EMA ladder: "take profits are the nearest EMAs" PREVIEW (E1 ATM, E2 … — *PREVIEW* | E1 | preview 2025-02 (fresh) | 1,761 | $592 | $592 | $592 (2025-02-28) | PREVIEW |
| 18 | #41b EMA system v1: PREVIEW on three drawn weeks (up, flat, down) — *PREVIEW* | Config A X1 | three weeks pooled | 64 | $467 | $984 | $372 (2025-07-25) | PREVIEW |
| 19 | #4b GeorgeFi entries with the trail engine (reconstruction C, G2) | all names | ledger E2 | 516 | $334 | $831 | $88.51 (2026-05-06) | No robust entry timing |
| 20 | #40a Compass EMA ladder: PREVIEW 2025-03, 13 versions (rerun) — *PREVIEW* | V1 | preview 2025-03 | 2,781 | $136 | $136 | $136 (2025-03-31) | PREVIEW |
| 21 | #8a V1 T0: short every monthly ATM straddle across the optionable universe | all names | hold-out | 12,484 | $98.72 | $98.72 | $98.72 (2026-08-24) | Rejected |
| 22 | #2b George rebuild: the best of 144 variants (sweep / ict+gex / morning / … | all names | out-of-sample 2026-03→10 | 385 | $10.03 | $291 | $9.80 (2026-10-06) | Rejected |
| 23 | #1 GeorgeFi vendor cards (the vendor's own recorded P&L) — *vendor-recorded, not re-marked* | all names | Epoch 2 | 603 | $2.66 | $2,385 | $1.85 (2026-09-17) | Not evidence |
| 24 | #2 George rebuild: the GeorgeFi-like reference (sweep / ict+gex / all / none / … | all names | out-of-sample 2026-03→10 | 1,399 | $1.05 | $5.89 | $1.00 (2026-10-07) | Rejected |
| 25 | #7c S03 Quick Scalps with weekly expirations (1–7 days) | all names | 2017-06→2026-10 | 818 | $0.15 | $696 | $0.09 (2023-05-19) | Nothing promoted |
| 26 | #17 Step 6: the six pre-registered runner rules × three exits | B1a | check 2025→2026-10-09 | 6,350 | $0.09 | $0.15 | $0.09 (2026-10-09) | FAIL |
| 27 | #17 Step 6: the six pre-registered runner rules × three exits | A1a | check 2025→2026-10-09 | 1,035 | $0.08 | $0.79 | $0.08 (2026-10-01) | FAIL |
| 28 | #4 GeorgeFi's own trades re-priced at the NBBO (G1) | all roots | ledger E2 | 594 | $0.01 | $129 | $9.12 × 10⁻³ (2026-09-17) | Not supported after execution |
| 29 | #5 Deep research round 1: flow rule F1 on SPY (H2 family) | SPY | 2025-07→2026-10 | 638 | $1.09 × 10⁻³ | $99.85 | $1.06 × 10⁻³ (2026-10-08) | Rejected |
| 30 | #43 Compass ICT: sweep → displacement/MSS → FVG on SPXW 0DTE | v0 | exploration 2022-05→2026-10-09 | 142 | $7.82 × 10⁻⁴ | $762 | $2.31 × 10⁻⁴ (2025-05-05) | Exploration only |
| 31 | #15 Step 4: turn-up buy (1.5× the low) + 20% trailing stop, near the money | all names | check 2025–26 | 26,258 | $7.66 × 10⁻⁵ | $7.66 × 10⁻⁵ | $6.61 × 10⁻⁵ (2026-09-17) | A trailing stop beats holding but still loses. |
| 32 | #29e Picker, IMPROVED (picked on the cards): PDH sweep → put, 10:00–12:00, +25% or … | all names | whole span (verdict) | 516 | $1.65 × 10⁻⁸ | $46.64 | $1.33 × 10⁻⁸ (2026-09-22) | FAIL on every name |
| 33 | #7b S02 Quick Scalps: 41-variant grid, walk-forward OOS (lower-bound selection) | all names | walk-forward OOS 2024-01→2026-10 | 3,200 | $8.41 × 10⁻¹⁶ | $2.10 × 10⁻⁵ | $7.04 × 10⁻¹⁶ (2026-10-02) | Nothing promoted |
| 34 | #7d S09 Quick Scalps on SPXW 0DTE | SPXW | 2022-05→2026-10 | 1,229 | $4.12 × 10⁻¹⁷ | $5.05 | $4.12 × 10⁻¹⁷ (2026-10-08) | REJECTED |
| 35 | #8c V2b: long ATM straddle into the earnings report | single names | hold-out | 3,543 | $2.06 × 10⁻²² | $7.69 × 10⁻¹⁵ | $2.06 × 10⁻²² (2026-09-23) | Rejected |
| 36 | #29c Picker, S2: "5 minutes" as a hard exit | all names | whole span (verdict) | 2,943 | $1.11 × 10⁻²² | $1.80 × 10⁻³ | $9.50 × 10⁻²³ (2026-10-14) | Labelled |
| 37 | #7a S01 Quick Scalps (owner baseline) on index 0DTE | all names | 2022-11→2026-10 | 2,886 | $3.46 × 10⁻²³ | $1.29 × 10⁻⁴ | $2.26 × 10⁻²³ (2026-09-29) | REJECTED |
| 38 | #29d Picker, S3: SPXW rides to the official close when in the money at 15:58 | SPXW | whole span (verdict) | 908 | $1.67 × 10⁻²⁹ | $8.63 | $1.02 × 10⁻²⁹ (2026-10-15) | Labelled |
| 39 | #29a Picker (GeorgeFi rule), PRIMARY: opening-range fade, stop 0.68, target 1.25, … | all names | whole span (verdict) | 2,943 | $3.03 × 10⁻³⁶ | $3.23 × 10⁻⁶ | $1.81 × 10⁻³⁶ (2026-08-25) | FAIL on every name |
| 40 | #29b Picker, SECONDARY: the narrative's +6% breakeven lock and VIX trail | all names | whole span (verdict) | 2,943 | $3.40 × 10⁻³⁸ | $2.05 × 10⁻⁶ | $2.94 × 10⁻³⁸ (2026-10-15) | Labelled |
| 41 | #13 Step 2: buy near the money, sell at +100% or hold (within 0.5% of the price) | all names | check 2025–26 | 227,851 | $5.36 × 10⁻⁴² | $5.36 × 10⁻⁴² | $5.36 × 10⁻⁴² (2026-10-09) | Every group loses before and after fees; near the money 29% double, … |
| 42 | #7i S16b Prior-day fade with a weekly contract (time exit) | all names | 2017-06→2026-10 | 1,041 | $1.26 × 10⁻⁷³ | $0.09 | $1.03 × 10⁻⁷³ (2026-10-07) | Nothing promoted |
| 43 | #30c Compass features X3: sell a same-day long option at the 14:00 bid (PASSED) | 0DTE→60 DTE, 15 names | holdout (opened) | 233,454 | $7.05 × 10⁻¹³¹ | $7.05 × 10⁻¹³¹ | $4.11 × 10⁻¹³¹ (2026-10-13) | PASS |
| 44 | #30e Compass features BX3e: the 14:00 exit on the physically settled names only … | 0DTE→60 DTE, 15 names | holdout (opened) | 203,289 | $4.67 × 10⁻¹³¹ | $4.67 × 10⁻¹³¹ | $2.88 × 10⁻¹³¹ (2026-10-13) | PASS |
| 45 | #30b Compass features V1: veto a spread over 10% of mid (PASSED) | 0DTE→60 DTE, 15 names | holdout (opened) | 474,526 | $9.03 × 10⁻²²⁹ | $2.87 × 10⁻²²⁵ | $9.03 × 10⁻²²⁹ (2026-10-21) | PASS |
| 46 | #30a Compass features: the base trades (every feature is judged against them) | 0DTE→60 DTE, 15 names | holdout (opened) | 580,234 | $4.12 × 10⁻²⁷⁰ | $8.65 × 10⁻²⁷⁰ | $4.12 × 10⁻²⁷⁰ (2026-10-21) | Descriptive |
| 47 | #8b V2a: short ATM straddle across the earnings report | single names | hold-out | 3,682 | **wiped out** 2026-06-17 | $1.53 × 10⁻¹⁵ | $0 (2026-06-17) | Rejected |
| 48 | #27a After-hours exercise study: fly5 iron ±5, case (b) the post-market decision | all names | ii | 987 | **wiped out** 2025-10-30 | **wiped out** 2025-11-19 | $0 (2025-10-30) | DROP |
| 49 | #27b After-hours exercise study: condor_d20, case (b) | SPY | ii | 1,176 | **wiped out** 2025-10-27 | **wiped out** 2025-11-19 | $0 (2025-10-27) | DROP |
| 50 | #9b Lifecycle P2: Quick Scalps → credit put spread to expiry (portfolio) | all names | hold-out 2025-10→2026-10 | 196 | **wiped out** 2025-10-16 | $142 | $0 (2025-10-16) | Rejected |
| 51 | #21d Phase 2 hyp C: debit vertical 0.70/0.30, universe B, held (the vertical pick) | all names | OOS 2025–26 | 1,761 | **wiped out** 2025-08-20 | $20.34 | $0 (2025-08-20) | Loses less than the naked contract but still loses |
| 52 | #6a T-A: the 13:00 short ATM 0DTE straddle, SPY/QQQ/IWM, bought back 15:55 (H9) | all names | 2025-06→2026-10 | 1,017 | **wiped out** 2025-06-13 | $8.66 | $0 (2025-06-13) | FAIL |
| 53 | #6c T-C: the 13:00 SPXW short straddle bought back 15:55 (H11) | SPXW | 2025-06→2026-10 | 339 | **wiped out** 2025-06-13 | $2,498 | $0 (2025-06-13) | FAIL |
| 54 | #19 Phase 2 hyp A: the low-moc_mag closing pin (SPXW short call spread, 15:30, held) | SPXW | OOS 2025–26 | 177 | **wiped out** 2025-04-30 | $767 | $0 (2025-04-30) | NO EDGE |
| 55 | #25 Phase 3 hyp F: the 15:30 SPY/QQQ long call ±5 butterfly (cash account) | all names | OOS 2025–26 | 879 | **wiped out** 2025-03-04 | $15,335 | $0 (2025-03-04) | Passes all four, but the cell was named after C's OOS was printed |
| 56 | #26b Paper tracker: fly5 (SPY/QQQ ±5 butterflies at 15:00 and 15:30: iron, call, put) | all names | ii | 5,271 | **wiped out** 2025-03-04 | **wiped out** 2025-03-04 | $0 (2025-03-04) | Iron clear of zero in i and ii |
| 57 | #28a SPXW analogue A: iron fly ±5×ratio at 15:00 and 15:30 (fly5 iron) | SPXW | selection | 882 | **wiped out** 2025-03-04 | $431 | $0 (2025-03-04) | FAIL |
| 58 | #21c Phase 2 hyp C: 15:00 SPY/QQQ P3 call ±5 butterfly, held to settlement | all names | OOS 2025–26 | 878 | **wiped out** 2025-02-28 | $2,386 | $0 (2025-02-28) | Not confirmed |
| 59 | #26c Paper tracker: condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | SPY | ii | 2,090 | **wiped out** 2025-02-27 | $394,318 | $0 (2025-02-27) | Positive in ii |
| 60 | #28b SPXW analogue B: 20-delta iron condor, wings 2×ratio, 13:00–15:00 (condor_d20) | SPXW | selection | 2,157 | **wiped out** 2025-02-27 | $201 | $0 (2025-02-27) | FAIL |
| 61 | #8d V3a: single-name 0DTE short ATM straddle 10:00 → 15:50 | all names | hold-out | 1,622 | **wiped out** 2025-02-21 | **wiped out** 2025-02-21 | $0 (2025-02-21) | Rejected |
| 62 | #6d T-E: the 13:00 SPXW ATM straddle held to PM settlement, ex FOMC/CPI/NFP (H13) | SPXW | TEST | 388 | **wiped out** 2025-01-31 | $7,555 | $0 (2025-01-31) | FAIL |
| 63 | #20b Phase 2 hyp B: the midday SPY iron condor (em1, mid-VIX), the midday pick | SPY | OOS 2025–26 | 1,202 | **wiped out** 2025-01-31 | $4,522 | $0 (2025-01-31) | "Needs X" |
| 64 | #26a Paper tracker: condor_em1 (SPY 2-wide iron condor at ± the ATM straddle, … | SPY | ii | 2,068 | **wiped out** 2025-01-31 | $612 | $0 (2025-01-31) | Historical periods through zero |
| 65 | #6e H15 carry lane: the 14:05 SPXW short strangle at ±0.5 expected move, held to … | SPXW | TEST | 407 | **wiped out** 2025-01-07 | $3,173 | $0 (2025-01-07) | Open, NOT promotable |
| 66 | #21a Phase 2 hyp C: 15:00 SPY/QQQ P1 iron ±2 butterfly, held to settlement | all names | OOS 2025–26 | 878 | **wiped out** 2025-01-02 | $302 | $0 (2025-01-02) | Not confirmed |
| 67 | #21b Phase 2 hyp C: 15:00 SPY/QQQ P2 call ±2 butterfly, held to settlement | all names | OOS 2025–26 | 880 | **wiped out** 2025-01-02 | $43.56 | $0 (2025-01-02) | Not confirmed |
| 68 | #7e S10 Short premium: fade the Quick Scalps signal (single contract, 2× stop, to … | all names | 2022-11→2026-10 | 2,886 | **wiped out** 2022-11-30 | **wiped out** 2023-03-03 | $0 (2022-11-30) | Nothing promoted |
| 69 | #7g S12b 10:00 long option in the first-half-hour direction | all names | 2022-11→2026-10 | 2,499 | **wiped out** 2022-11-22 | $1.68 × 10⁻¹⁵ | $0 (2022-11-22) | Nothing promoted |
| 70 | #7h S15 VRP-conditioned 10:00 short ATM 0DTE straddle (unconditional row) | all names | 2022-11→2026-10 | 1,941 | **wiped out** 2022-11-22 | **wiped out** 2025-10-10 | $0 (2022-11-22) | Nothing promoted |
| 71 | #7f S12 Intraday momentum: first-half-hour direction → 10:00–15:00 long option | all names | 2022-11→2026-10 | 2,214 | **wiped out** 2022-11-18 | $1.67 × 10⁻¹⁹ | $0 (2022-11-18) | Nothing promoted |
| 72 | #31 Compass direction: post-earnings drift in 31–60 DTE options (rerun) | single names | exploration (holdout unopened) | 12,114 | **wiped out** 2020-02-18 | $9.93 × 10⁻¹⁰⁸ | $0 (2020-02-18) | FAIL |
| 73 | #34 Edge H3: earnings IV-crush short iron condor (single names) | single names | exploration (holdout unopened) | 2,209 | **wiped out** 2019-08-13 | $5.09 × 10⁻³¹ | $0 (2019-08-13) | FAIL |
| 74 | #30d Compass features BV1b: the V1 veto at 3% (PASSED, Phase B) | 0DTE→60 DTE, 15 names | holdout (opened) | 251,808 | **wiped out** 2018-03-16 | $8.79 × 10⁻¹⁷¹ | $0 (2018-03-16) | PASS |
| 75 | #8e V8: month-end 13:00 long straddle on unread chains | all names | 2017-06→2022 (unread chains) | 105 | **wiped out** 2017-10-31 | $242 | $0 (2017-10-31) | Rejected |
| — | #3 George engine audit: the phase 1 reproduction audit of #1–#2 | — | — | — | not available — the audit produced no trades of its own; its trade files are #2's, byte for byte (see #2). | not available | — | Reproduced |
| — | #9c Lifecycle Tier I, daily tier, L-A3, H-FLO (by configuration) | — | — | — | not available — committed as configuration-level cells (grid_by_setup.csv, cells.csv); the trade rows are in the scratchpad (lifecycle/archive, 281 MB) and were … | not available | — | 0 promoted |
| — | #10 ATM straddle samples and the independent short-premium prereg (branch … | — | — | — | not available — price samples only (no trade with an exit); the pre-registered study never ran. | not available | — | No result |
| — | #11 Price-action catalogue and atlas (43 names) | — | — | — | not available — descriptive tables, no trades. | not available | — | Descriptive; V6 tested its levels |
| — | #12 Step 1: every 0DTE contract broken down | — | — | — | not available — a contract inventory, no trades. | not available | — | Descriptive. |
| — | #14 Step 3: 108 exits × 9 conditions | — | — | — | not available — committed as per-rule summaries (exits.csv, exits_best.csv); the per-trade paths are committed but the exit grid was not re-run here. | not available | — | Nothing made money in a way that held up; a −50% stop shrank … |
| — | #16 Step 5: the runner model (model A/B) and its top 1% picks | — | — | — | not available — the picks are committed as daily sums (top1_daily.csv), not trades. | not available | — | Runners partly separable |
| — | #18 Compass engine audit (six module groups) | — | — | — | not available — the audit committed row-level paths and events (paths_*.parquet, events_*.parquet) and per-cell tables; its exit stacks were scored by cell, and no … | not available | — | No directional rule survives after fees. What holds |
| — | #22 Phase 2 hyp D: volatility breakout (straddles on the model's top decile) | — | — | — | not available — committed as cells by scan minute and decile (cells_*.csv, minutes_*.parquet); no trade list of the pre-registered cell. | not available | — | No edge |
| — | #24 Phase 3 hyp E: short-premium lift of the vol model's quiet deciles | — | — | — | not available — committed as by-scan cells and pooled tables; the candidate was set after the OOS read (see #26 condor_d20 for its trades). | not available | — | No edge established — not pre-registrable |
| — | #26d Paper tracker: fly_spxw (SPX ±5 / ±25 flies) | — | — | — | not available — a one-week sanity run outside the repository; no rows were kept. | not available | — | Run only as a one-week sanity run outside the repository; replaced … |
| — | #29f Picker: flow gate and grade check | — | — | — | not available — one session of flow (5 trades) and the vendor's own recorded returns (see #1, vendor-recorded). | not available | — | Flow gate |
| — | #30f Compass features VN1 (venue SPY vs SPXW) and BC3 (V1 + X3 + D6) | — | — | — | not available — VN1 pairs venues and BC3 needs the D6 direction feature; both are computed inside the study's screen code, and their per-trade arms are not on disk. | not available | — | PASS |
| — | #36 Edge H5 (SPY − SPXW late straddle) and H6 (monthly put spreads), forward only | — | — | — | not available — forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has … | not available | — | No verdict. |
| — | #38 Edge H9: overnight drift (forward only, withdrawn) | — | — | — | not available — forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has … | not available | — | No verdict. |
| — | #39 Compass scanner (score ≥ 80, SPY/QQQ/IWM 0DTE) | — | — | — | not available — signal-only: the gate failed before any option was priced, so trades, win rate, average win/loss, biggest win/loss, profit factor, drawdown, top-5 … | not available | — | FAIL at the gate |
| — | #42 George A+ entry + EMA targets | — | — | — | not available — the run was stopped before its prereg was committed; no file exists on disk or in history, so every metric is not available. | not available | — | Never run. |
| — | #44 Compass EMA: the owner's three EMA / ORB models | — | — | — | not available — the run was stopped before computing: a partial engine and a session list exist in the scratchpad (compass_ema_partial/), no signal, trade or P&L. | not available | — | Never computed. |
| — | #45 DR-GCE gates 1 and 2 (Mode 1 Gamma Vacuum Squeeze) | — | — | — | not available — signal-only: touch outcomes (signals.csv, gate2_pairs.csv), never traded to an exit; no P&L metric exists. | not available | — | Gate 1 PASS |
| — | #46 Trend-day test | — | — | — | not available — never run (the trend-day share is only described in step 6). | not available | — | Never registered, never run. |

**Counts.** Above $1,000 at the end: 14 of 75 rows under A, 22 under B. Wiped out: 29 under A, 6 under B. The 20 studies at the foot of the table have no trade list with usable per-trade returns.

## Every row in full

Return unit is the row's own. "Sessions" counts the sessions with at least one trade. Max drawdown is the largest fall from a running peak of the balance, in %.

| # | strategy | instrument | period | unit | start | end | sessions | trades | A: ending $ | A: total return | A: lowest (date) | A: max DD | B: ending $ | B: total return | B: lowest (date) | B: max DD |
|------|------------------------------------------|---------------|---------------------|---------------|---------------|---------------|------------|------------|------------------|------------------|------------------------|------------|------------------|------------------|------------------------|------------|
| 1 | #20a Phase 2 hyp B: boundary touch — SPY 2-wide 25-delta credit spread, held (the … | SPY | OOS 2025–26 | % of max risk | 2025-01-02 | 2026-10-09 | 432 | 2,600 | $4.18 × 10¹¹ | +4.18 × 10¹⁰% | $171 (2025-03-03) | 96.3% | $470,760 | +46,976.0% | $62.83 (2025-03-03) | 96.9% |
| 2 | #1 GeorgeFi vendor cards (the vendor's own recorded P&L) — *vendor-recorded, not re-marked* | all names | Epoch 1 | % of premium | 2026-01-20 | 2026-02-27 | 28 | 546 | $8,015 | +701.5% | $1,000 (start) | 38.2% | $14,424 | +1,342.4% | $1,000 (start) | 11.0% |
| 3 | #7j-atm_put S17 Index put-writing: monthly ATM cash-secured put | all names | 2012-06→2026-10 | % of cash set aside | 2012-06-15 | 2026-08-21 | 167 | 334 | $2,725 | +172.5% | $999 (2012-10-19) | 26.7% | $1,239 | +23.9% | $1,000 (start) | 5.3% |
| 4 | #32 Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock) | QQQ | single test | % of notional | 2012-06-01 | 2025-10-10 | 3,299 | 3,299 | $2,207 | +120.7% | $681 (2020-02-03) | 35.5% | $1,093 | +9.3% | $965 (2020-02-03) | 4.1% |
| 5 | #7j-put_30d S17 Index put-writing: monthly 0.30-delta cash-secured put | all names | 2012-06→2026-10 | % of cash set aside | 2012-06-15 | 2026-08-21 | 167 | 334 | $2,019 | +101.9% | $1,000 (start) | 25.6% | $1,162 | +16.2% | $1,000 (start) | 5.1% |
| 6 | #32 Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock) | SPY | single test | % of notional | 2017-01-03 | 2025-10-10 | 2,177 | 2,177 | $1,874 | +87.4% | $856 (2019-12-09) | 19.6% | $1,071 | +7.1% | $985 (2019-12-09) | 2.1% |
| 7 | #37b Edge H8: turn of the month (SPY, QQQ stock) | QQQ | single test | % of notional | 2012-06-28 | 2026-09-29 | 172 | 172 | $1,852 | +85.2% | $1,000 (start) | 11.6% | $1,068 | +6.8% | $1,000 (start) | 1.2% |
| 8 | #7j-put_15d S17 Index put-writing: monthly 0.15-delta cash-secured put | all names | 2012-06→2026-10 | % of cash set aside | 2012-06-15 | 2026-08-21 | 167 | 334 | $1,487 | +48.7% | $981 (2020-02-21) | 23.2% | $1,089 | +8.9% | $1,000 (start) | 4.6% |
| 9 | #37b Edge H8: turn of the month (SPY, QQQ stock) | SPY | single test | % of notional | 2017-01-30 | 2026-09-29 | 117 | 117 | $1,407 | +40.7% | $975 (2018-04-27) | 8.4% | $1,037 | +3.7% | $998 (2018-04-27) | 0.9% |
| 10 | #37a Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED | QQQ | single test | % of notional | 2013-03-19 | 2026-09-15 | 108 | 108 | $1,250 | +25.0% | $978 (2016-04-26) | 3.0% | $1,023 | +2.3% | $998 (2016-04-26) | 0.3% |
| 11 | #37a Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED | SPY | single test | % of notional | 2017-01-31 | 2026-09-15 | 77 | 77 | $1,156 | +15.6% | $999 (2017-09-19) | 2.7% | $1,015 | +1.5% | $1,000 (2017-01-31) | 0.3% |
| 12 | #41a EMA system v0: PREVIEW on 2026-10-12 → 16 (5 sessions) — *PREVIEW* | Config A X1 | preview 2026-10-12→16 | % of premium | 2026-10-12 | 2026-10-16 | 5 | 57 | $1,077 | +7.7% | $642 (2026-10-12) | 35.8% | $1,109 | +10.9% | $678 (2026-10-12) | 32.2% |
| 13 | #35 Edge H4: market intraday momentum (SPY, QQQ stock) | QQQ | test 2025-10-13→2026-10-22 | % of notional | 2025-10-13 | 2026-10-22 | 257 | 257 | $1,035 | +3.5% | $972 (2026-04-07) | 3.7% | $1,003 | +0.3% | $997 (2026-04-07) | 0.4% |
| 14 | #9a Lifecycle P1: Quick Scalps → cash-secured put sale (portfolio) | all names | hold-out 2025-10→2026-10 | % of max risk | 2025-10-01 | 2026-10-05 | 89 | 122 | $1,007 | +0.7% | $988 (2026-03-25) | 1.2% | $1,001 | +0.1% | $998 (2026-03-25) | 0.2% |
| 15 | #35 Edge H4: market intraday momentum (SPY, QQQ stock) | SPY | test 2025-10-13→2026-10-22 | % of notional | 2025-10-13 | 2026-10-22 | 257 | 257 | $988 | −1.2% | $962 (2026-03-09) | 4.5% | $999 | −0.1% | $996 (2026-03-09) | 0.5% |
| 16 | #6b T-B: gamma-conditioned last-30-minute momentum in SPY shares (H10) | SPY | negative-gamma days 2024-05→2026-10 | % of notional | 2024-05-14 | 2026-10-07 | 299 | 299 | $912 | −8.8% | $906 (2026-09-23) | 9.4% | $991 | −0.9% | $990 (2026-09-23) | 1.0% |
| 17 | #40b Compass EMA ladder: "take profits are the nearest EMAs" PREVIEW (E1 ATM, E2 … — *PREVIEW* | E1 | preview 2025-02 (fresh) | % of premium | 2025-02-03 | 2025-02-28 | 19 | 1,761 | $592 | −40.8% | $592 (2025-02-28) | 40.8% | $592 | −40.8% | $592 (2025-02-28) | 40.8% |
| 18 | #41b EMA system v1: PREVIEW on three drawn weeks (up, flat, down) — *PREVIEW* | Config A X1 | three weeks pooled | % of premium | 2025-07-21 | 2026-07-17 | 15 | 64 | $467 | −53.3% | $372 (2025-07-25) | 64.0% | $984 | −1.6% | $706 (2025-07-25) | 29.4% |
| 19 | #4b GeorgeFi entries with the trail engine (reconstruction C, G2) | all names | ledger E2 | % of premium | 2026-03-02 | 2026-10-13 | 131 | 516 | $334 | −66.6% | $88.51 (2026-05-06) | 91.1% | $831 | −16.9% | $472 (2026-05-06) | 52.8% |
| 20 | #40a Compass EMA ladder: PREVIEW 2025-03, 13 versions (rerun) — *PREVIEW* | V1 | preview 2025-03 | % of premium | 2025-03-03 | 2025-03-31 | 21 | 2,781 | $136 | −86.4% | $136 (2025-03-31) | 86.4% | $136 | −86.4% | $136 (2025-03-31) | 86.4% |
| 21 | #8a V1 T0: short every monthly ATM straddle across the optionable universe | all names | hold-out | % of premium | 2026-01-20 | 2026-08-24 | 8 | 12,484 | $98.72 | −90.1% | $98.72 (2026-08-24) | 90.1% | $98.72 | −90.1% | $98.72 (2026-08-24) | 90.1% |
| 22 | #2b George rebuild: the best of 144 variants (sweep / ict+gex / morning / … | all names | out-of-sample 2026-03→10 | % of premium | 2026-03-02 | 2026-10-09 | 116 | 385 | $10.03 | −99.0% | $9.80 (2026-10-06) | 99.1% | $291 | −70.9% | $288 (2026-10-06) | 73.9% |
| 23 | #1 GeorgeFi vendor cards (the vendor's own recorded P&L) — *vendor-recorded, not re-marked* | all names | Epoch 2 | % of premium | 2026-03-02 | 2026-10-13 | 132 | 603 | $2.66 | −99.7% | $1.85 (2026-09-17) | 99.9% | $2,385 | +138.5% | $763 (2026-05-14) | 52.0% |
| 24 | #2 George rebuild: the GeorgeFi-like reference (sweep / ict+gex / all / none / … | all names | out-of-sample 2026-03→10 | % of premium | 2026-03-02 | 2026-10-09 | 155 | 1,399 | $1.05 | −99.9% | $1.00 (2026-10-07) | 99.9% | $5.89 | −99.4% | $5.71 (2026-10-07) | 99.4% |
| 25 | #7c S03 Quick Scalps with weekly expirations (1–7 days) | all names | 2017-06→2026-10 | % of premium | 2017-06-29 | 2026-10-07 | 376 | 818 | $0.15 | −100.0% | $0.09 (2023-05-19) | 100.0% | $696 | −30.4% | $317 (2023-06-13) | 70.3% |
| 26 | #17 Step 6: the six pre-registered runner rules × three exits | B1a | check 2025→2026-10-09 | % of premium | 2025-01-02 | 2026-10-09 | 197 | 6,350 | $0.09 | −100.0% | $0.09 (2026-10-09) | 100.0% | $0.15 | −100.0% | $0.15 (2026-10-09) | 100.0% |
| 27 | #17 Step 6: the six pre-registered runner rules × three exits | A1a | check 2025→2026-10-09 | % of premium | 2025-01-02 | 2026-10-01 | 101 | 1,035 | $0.08 | −100.0% | $0.08 (2026-10-01) | 100.0% | $0.79 | −99.9% | $0.79 (2026-10-01) | 100.0% |
| 28 | #4 GeorgeFi's own trades re-priced at the NBBO (G1) | all roots | ledger E2 | % of premium | 2026-03-02 | 2026-10-13 | 132 | 594 | $0.01 | −100.0% | $9.12 × 10⁻³ (2026-09-17) | 100.0% | $129 | −87.1% | $111 (2026-10-12) | 90.0% |
| 29 | #5 Deep research round 1: flow rule F1 on SPY (H2 family) | SPY | 2025-07→2026-10 | % of premium | 2025-07-01 | 2026-10-09 | 319 | 638 | $1.09 × 10⁻³ | −100.0% | $1.06 × 10⁻³ (2026-10-08) | 100.0% | $99.85 | −90.0% | $99.39 (2026-10-08) | 90.1% |
| 30 | #43 Compass ICT: sweep → displacement/MSS → FVG on SPXW 0DTE | v0 | exploration 2022-05→2026-10-09 | % of premium | 2022-06-09 | 2026-10-05 | 116 | 142 | $7.82 × 10⁻⁴ | −100.0% | $2.31 × 10⁻⁴ (2025-05-05) | 100.0% | $762 | −23.8% | $469 (2025-05-05) | 53.1% |
| 31 | #15 Step 4: turn-up buy (1.5× the low) + 20% trailing stop, near the money | all names | check 2025–26 | % of premium | 2025-01-02 | 2026-10-09 | 444 | 26,258 | $7.66 × 10⁻⁵ | −100.0% | $6.61 × 10⁻⁵ (2026-09-17) | 100.0% | $7.66 × 10⁻⁵ | −100.0% | $6.61 × 10⁻⁵ (2026-09-17) | 100.0% |
| 32 | #29e Picker, IMPROVED (picked on the cards): PDH sweep → put, 10:00–12:00, +25% or … | all names | whole span (verdict) | % of premium | 2022-05-17 | 2026-10-20 | 276 | 516 | $1.65 × 10⁻⁸ | −100.0% | $1.33 × 10⁻⁸ (2026-09-22) | 100.0% | $46.64 | −95.3% | $44.45 (2026-09-22) | 95.7% |
| 33 | #7b S02 Quick Scalps: 41-variant grid, walk-forward OOS (lower-bound selection) | all names | walk-forward OOS 2024-01→2026-10 | % of premium | 2024-01-02 | 2026-10-08 | 488 | 3,200 | $8.41 × 10⁻¹⁶ | −100.0% | $7.04 × 10⁻¹⁶ (2026-10-02) | 100.0% | $2.10 × 10⁻⁵ | −100.0% | $2.10 × 10⁻⁵ (2026-10-08) | 100.0% |
| 34 | #7d S09 Quick Scalps on SPXW 0DTE | SPXW | 2022-05→2026-10 | % of premium | 2022-05-19 | 2026-10-08 | 481 | 1,229 | $4.12 × 10⁻¹⁷ | −100.0% | $4.12 × 10⁻¹⁷ (2026-10-08) | 100.0% | $5.05 | −99.5% | $4.29 (2026-09-17) | 99.6% |
| 35 | #8c V2b: long ATM straddle into the earnings report | single names | hold-out | % of premium | 2025-12-29 | 2026-09-23 | 164 | 3,543 | $2.06 × 10⁻²² | −100.0% | $2.06 × 10⁻²² (2026-09-23) | 100.0% | $7.69 × 10⁻¹⁵ | −100.0% | $7.69 × 10⁻¹⁵ (2026-09-23) | 100.0% |
| 36 | #29c Picker, S2: "5 minutes" as a hard exit | all names | whole span (verdict) | % of premium | 2022-05-13 | 2026-10-21 | 903 | 2,943 | $1.11 × 10⁻²² | −100.0% | $9.50 × 10⁻²³ (2026-10-14) | 100.0% | $1.80 × 10⁻³ | −100.0% | $1.70 × 10⁻³ (2026-10-14) | 100.0% |
| 37 | #7a S01 Quick Scalps (owner baseline) on index 0DTE | all names | 2022-11→2026-10 | % of premium | 2022-11-11 | 2026-10-08 | 614 | 2,886 | $3.46 × 10⁻²³ | −100.0% | $2.26 × 10⁻²³ (2026-09-29) | 100.0% | $1.29 × 10⁻⁴ | −100.0% | $1.29 × 10⁻⁴ (2026-10-08) | 100.0% |
| 38 | #29d Picker, S3: SPXW rides to the official close when in the money at 15:58 | SPXW | whole span (verdict) | % of premium | 2022-05-13 | 2026-10-21 | 770 | 908 | $1.67 × 10⁻²⁹ | −100.0% | $1.02 × 10⁻²⁹ (2026-10-15) | 100.0% | $8.63 | −99.1% | $8.09 (2026-09-22) | 99.2% |
| 39 | #29a Picker (GeorgeFi rule), PRIMARY: opening-range fade, stop 0.68, target 1.25, … | all names | whole span (verdict) | % of premium | 2022-05-13 | 2026-10-21 | 903 | 2,943 | $3.03 × 10⁻³⁶ | −100.0% | $1.81 × 10⁻³⁶ (2026-08-25) | 100.0% | $3.23 × 10⁻⁶ | −100.0% | $2.66 × 10⁻⁶ (2026-08-25) | 100.0% |
| 40 | #29b Picker, SECONDARY: the narrative's +6% breakeven lock and VIX trail | all names | whole span (verdict) | % of premium | 2022-05-13 | 2026-10-21 | 903 | 2,943 | $3.40 × 10⁻³⁸ | −100.0% | $2.94 × 10⁻³⁸ (2026-10-15) | 100.0% | $2.05 × 10⁻⁶ | −100.0% | $1.94 × 10⁻⁶ (2026-10-15) | 100.0% |
| 41 | #13 Step 2: buy near the money, sell at +100% or hold (within 0.5% of the price) | all names | check 2025–26 | % of premium | 2025-01-02 | 2026-10-09 | 444 | 227,851 | $5.36 × 10⁻⁴² | −100.0% | $5.36 × 10⁻⁴² (2026-10-09) | 100.0% | $5.36 × 10⁻⁴² | −100.0% | $5.36 × 10⁻⁴² (2026-10-09) | 100.0% |
| 42 | #7i S16b Prior-day fade with a weekly contract (time exit) | all names | 2017-06→2026-10 | % of premium | 2017-06-05 | 2026-10-09 | 699 | 1,041 | $1.26 × 10⁻⁷³ | −100.0% | $1.03 × 10⁻⁷³ (2026-10-07) | 100.0% | $0.09 | −100.0% | $0.09 (2026-02-18) | 100.0% |
| 43 | #30c Compass features X3: sell a same-day long option at the 14:00 bid (PASSED) | 0DTE→60 DTE, 15 names | holdout (opened) | % of premium | 2017-06-02 | 2026-10-21 | 1,290 | 233,454 | $7.05 × 10⁻¹³¹ | −100.0% | $4.11 × 10⁻¹³¹ (2026-10-13) | 100.0% | $7.05 × 10⁻¹³¹ | −100.0% | $4.11 × 10⁻¹³¹ (2026-10-13) | 100.0% |
| 44 | #30e Compass features BX3e: the 14:00 exit on the physically settled names only … | 0DTE→60 DTE, 15 names | holdout (opened) | % of premium | 2017-06-02 | 2026-10-21 | 1,257 | 203,289 | $4.67 × 10⁻¹³¹ | −100.0% | $2.88 × 10⁻¹³¹ (2026-10-13) | 100.0% | $4.67 × 10⁻¹³¹ | −100.0% | $2.88 × 10⁻¹³¹ (2026-10-13) | 100.0% |
| 45 | #30b Compass features V1: veto a spread over 10% of mid (PASSED) | 0DTE→60 DTE, 15 names | holdout (opened) | % of premium | 2012-06-01 | 2026-10-21 | 3,572 | 474,526 | $9.03 × 10⁻²²⁹ | −100.0% | $9.03 × 10⁻²²⁹ (2026-10-21) | 100.0% | $2.87 × 10⁻²²⁵ | −100.0% | $2.87 × 10⁻²²⁵ (2026-10-21) | 100.0% |
| 46 | #30a Compass features: the base trades (every feature is judged against them) | 0DTE→60 DTE, 15 names | holdout (opened) | % of premium | 2012-06-01 | 2026-10-21 | 3,577 | 580,234 | $4.12 × 10⁻²⁷⁰ | −100.0% | $4.12 × 10⁻²⁷⁰ (2026-10-21) | 100.0% | $8.65 × 10⁻²⁷⁰ | −100.0% | $8.65 × 10⁻²⁷⁰ (2026-10-21) | 100.0% |
| 47 | #8b V2a: short ATM straddle across the earnings report | single names | hold-out | % of premium | 2026-01-06 | 2026-09-30 | 165 | 3,682 | **wiped out** 2026-06-17 | −100% (wiped out) | $0 (2026-06-17) | 100.0% | $1.53 × 10⁻¹⁵ | −100.0% | $1.43 × 10⁻¹⁵ (2026-09-09) | 100.0% |
| 48 | #27a After-hours exercise study: fly5 iron ±5, case (b) the post-market decision | all names | ii | % of max risk | 2025-10-13 | 2026-10-09 | 248 | 987 | **wiped out** 2025-10-30 | −100% (wiped out) | $0 (2025-10-30) | 100.0% | **wiped out** 2025-11-19 | −100% (wiped out) | $0 (2025-11-19) | 100.0% |
| 49 | #27b After-hours exercise study: condor_d20, case (b) | SPY | ii | % of max risk | 2025-10-13 | 2026-10-09 | 247 | 1,176 | **wiped out** 2025-10-27 | −100% (wiped out) | $0 (2025-10-27) | 100.0% | **wiped out** 2025-11-19 | −100% (wiped out) | $0 (2025-11-19) | 100.0% |
| 50 | #9b Lifecycle P2: Quick Scalps → credit put spread to expiry (portfolio) | all names | hold-out 2025-10→2026-10 | % of max risk | 2025-10-01 | 2026-10-05 | 91 | 196 | **wiped out** 2025-10-16 | −100% (wiped out) | $0 (2025-10-16) | 100.0% | $142 | −85.8% | $114 (2026-03-23) | 91.4% |
| 51 | #21d Phase 2 hyp C: debit vertical 0.70/0.30, universe B, held (the vertical pick) | all names | OOS 2025–26 | % of premium | 2025-01-02 | 2026-10-09 | 441 | 1,761 | **wiped out** 2025-08-20 | −100% (wiped out) | $0 (2025-08-20) | 100.0% | $20.34 | −98.0% | $1.32 (2025-11-03) | 99.9% |
| 52 | #6a T-A: the 13:00 short ATM 0DTE straddle, SPY/QQQ/IWM, bought back 15:55 (H9) | all names | 2025-06→2026-10 | % of credit | 2025-06-02 | 2026-10-09 | 339 | 1,017 | **wiped out** 2025-06-13 | −100% (wiped out) | $0 (2025-06-13) | 100.0% | $8.66 | −99.1% | $1.72 (2026-06-17) | 99.9% |
| 53 | #6c T-C: the 13:00 SPXW short straddle bought back 15:55 (H11) | SPXW | 2025-06→2026-10 | % of credit | 2025-06-02 | 2026-10-09 | 339 | 339 | **wiped out** 2025-06-13 | −100% (wiped out) | $0 (2025-06-13) | 100.0% | $2,498 | +149.8% | $780 (2025-09-04) | 47.8% |
| 54 | #19 Phase 2 hyp A: the low-moc_mag closing pin (SPXW short call spread, 15:30, held) | SPXW | OOS 2025–26 | % of max risk | 2025-01-03 | 2026-10-09 | 177 | 177 | **wiped out** 2025-04-30 | −100% (wiped out) | $0 (2025-04-30) | 100.0% | $767 | −23.3% | $719 (2026-04-13) | 29.8% |
| 55 | #25 Phase 3 hyp F: the 15:30 SPY/QQQ long call ±5 butterfly (cash account) | all names | OOS 2025–26 | % of max risk | 2025-01-02 | 2026-10-09 | 441 | 879 | **wiped out** 2025-03-04 | −100% (wiped out) | $0 (2025-03-04) | 100.0% | $15,335 | +1,433.5% | $714 (2025-05-22) | 58.4% |
| 56 | #26b Paper tracker: fly5 (SPY/QQQ ±5 butterflies at 15:00 and 15:30: iron, call, put) | all names | ii | % of max risk | 2025-01-02 | 2026-10-09 | 441 | 5,271 | **wiped out** 2025-03-04 | −100% (wiped out) | $0 (2025-03-04) | 100.0% | **wiped out** 2025-03-04 | −100% (wiped out) | $0 (2025-03-04) | 100.0% |
| 57 | #28a SPXW analogue A: iron fly ±5×ratio at 15:00 and 15:30 (fly5 iron) | SPXW | selection | % of max risk | 2025-01-02 | 2026-10-09 | 441 | 882 | **wiped out** 2025-03-04 | −100% (wiped out) | $0 (2025-03-04) | 100.0% | $431 | −56.9% | $319 (2026-04-22) | 73.2% |
| 58 | #21c Phase 2 hyp C: 15:00 SPY/QQQ P3 call ±5 butterfly, held to settlement | all names | OOS 2025–26 | % of max risk | 2025-01-02 | 2026-10-09 | 441 | 878 | **wiped out** 2025-02-28 | −100% (wiped out) | $0 (2025-02-28) | 100.0% | $2,386 | +138.6% | $296 (2025-04-09) | 72.5% |
| 59 | #26c Paper tracker: condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | SPY | ii | % of max risk | 2025-01-02 | 2026-10-09 | 440 | 2,090 | **wiped out** 2025-02-27 | −100% (wiped out) | $0 (2025-02-27) | 100.0% | $394,318 | +39,331.8% | $407 (2025-03-04) | 86.4% |
| 60 | #28b SPXW analogue B: 20-delta iron condor, wings 2×ratio, 13:00–15:00 (condor_d20) | SPXW | selection | % of max risk | 2025-01-02 | 2026-10-09 | 441 | 2,157 | **wiped out** 2025-02-27 | −100% (wiped out) | $0 (2025-02-27) | 100.0% | $201 | −79.9% | $19.49 (2026-06-17) | 99.2% |
| 61 | #8d V3a: single-name 0DTE short ATM straddle 10:00 → 15:50 | all names | hold-out | % of premium | 2025-01-03 | 2026-10-09 | 161 | 1,622 | **wiped out** 2025-02-21 | −100% (wiped out) | $0 (2025-02-21) | 100.0% | **wiped out** 2025-02-21 | −100% (wiped out) | $0 (2025-02-21) | 100.0% |
| 62 | #6d T-E: the 13:00 SPXW ATM straddle held to PM settlement, ex FOMC/CPI/NFP (H13) | SPXW | TEST | % of credit | 2025-01-02 | 2026-10-09 | 388 | 388 | **wiped out** 2025-01-31 | −100% (wiped out) | $0 (2025-01-31) | 100.0% | $7,555 | +655.5% | $460 (2025-03-03) | 61.1% |
| 63 | #20b Phase 2 hyp B: the midday SPY iron condor (em1, mid-VIX), the midday pick | SPY | OOS 2025–26 | % of max risk | 2025-01-02 | 2026-10-08 | 280 | 1,202 | **wiped out** 2025-01-31 | −100% (wiped out) | $0 (2025-01-31) | 100.0% | $4,522 | +352.2% | $875 (2025-01-07) | 82.6% |
| 64 | #26a Paper tracker: condor_em1 (SPY 2-wide iron condor at ± the ATM straddle, … | SPY | ii | % of max risk | 2025-01-02 | 2026-10-09 | 439 | 2,068 | **wiped out** 2025-01-31 | −100% (wiped out) | $0 (2025-01-31) | 100.0% | $612 | −38.8% | $134 (2025-03-07) | 96.8% |
| 65 | #6e H15 carry lane: the 14:05 SPXW short strangle at ±0.5 expected move, held to … | SPXW | TEST | % of credit | 2025-01-02 | 2026-10-09 | 407 | 407 | **wiped out** 2025-01-07 | −100% (wiped out) | $0 (2025-01-07) | 100.0% | $3,173 | +217.3% | $162 (2026-06-11) | 97.9% |
| 66 | #21a Phase 2 hyp C: 15:00 SPY/QQQ P1 iron ±2 butterfly, held to settlement | all names | OOS 2025–26 | % of max risk | 2025-01-02 | 2026-10-09 | 440 | 878 | **wiped out** 2025-01-02 | −100% (wiped out) | $0 (2025-01-02) | 100.0% | $302 | −69.8% | $13.16 (2026-04-23) | 98.7% |
| 67 | #21b Phase 2 hyp C: 15:00 SPY/QQQ P2 call ±2 butterfly, held to settlement | all names | OOS 2025–26 | % of max risk | 2025-01-02 | 2026-10-09 | 441 | 880 | **wiped out** 2025-01-02 | −100% (wiped out) | $0 (2025-01-02) | 100.0% | $43.56 | −95.6% | $2.60 (2026-06-08) | 99.7% |
| 68 | #7e S10 Short premium: fade the Quick Scalps signal (single contract, 2× stop, to … | all names | 2022-11→2026-10 | % of credit | 2022-11-11 | 2026-10-08 | 614 | 2,886 | **wiped out** 2022-11-30 | −100% (wiped out) | $0 (2022-11-30) | 100.0% | **wiped out** 2023-03-03 | −100% (wiped out) | $0 (2023-03-03) | 100.0% |
| 69 | #7g S12b 10:00 long option in the first-half-hour direction | all names | 2022-11→2026-10 | % of premium | 2022-11-11 | 2026-10-09 | 971 | 2,499 | **wiped out** 2022-11-22 | −100% (wiped out) | $0 (2022-11-22) | 100.0% | $1.68 × 10⁻¹⁵ | −100.0% | $1.35 × 10⁻¹⁵ (2026-10-02) | 100.0% |
| 70 | #7h S15 VRP-conditioned 10:00 short ATM 0DTE straddle (unconditional row) | all names | 2022-11→2026-10 | % of credit | 2022-11-11 | 2026-10-09 | 971 | 1,941 | **wiped out** 2022-11-22 | −100% (wiped out) | $0 (2022-11-22) | 100.0% | **wiped out** 2025-10-10 | −100% (wiped out) | $0 (2025-10-10) | 100.0% |
| 71 | #7f S12 Intraday momentum: first-half-hour direction → 10:00–15:00 long option | all names | 2022-11→2026-10 | % of premium | 2022-11-11 | 2026-10-09 | 961 | 2,214 | **wiped out** 2022-11-18 | −100% (wiped out) | $0 (2022-11-18) | 100.0% | $1.67 × 10⁻¹⁹ | −100.0% | $1.45 × 10⁻¹⁹ (2026-10-06) | 100.0% |
| 72 | #31 Compass direction: post-earnings drift in 31–60 DTE options (rerun) | single names | exploration (holdout unopened) | % of premium | 2019-04-11 | 2026-09-10 | 893 | 12,114 | **wiped out** 2020-02-18 | −100% (wiped out) | $0 (2020-02-18) | 100.0% | $9.93 × 10⁻¹⁰⁸ | −100.0% | $9.93 × 10⁻¹⁰⁸ (2026-09-10) | 100.0% |
| 73 | #34 Edge H3: earnings IV-crush short iron condor (single names) | single names | exploration (holdout unopened) | % of max risk | 2019-04-09 | 2022-12-14 | 554 | 2,209 | **wiped out** 2019-08-13 | −100% (wiped out) | $0 (2019-08-13) | 100.0% | $5.09 × 10⁻³¹ | −100.0% | $5.08 × 10⁻³¹ (2022-12-08) | 100.0% |
| 74 | #30d Compass features BV1b: the V1 veto at 3% (PASSED, Phase B) | 0DTE→60 DTE, 15 names | holdout (opened) | % of premium | 2012-06-01 | 2026-10-21 | 3,437 | 251,808 | **wiped out** 2018-03-16 | −100% (wiped out) | $0 (2018-03-16) | 100.0% | $8.79 × 10⁻¹⁷¹ | −100.0% | $8.79 × 10⁻¹⁷¹ (2026-10-21) | 100.0% |
| 75 | #8e V8: month-end 13:00 long straddle on unread chains | all names | 2017-06→2022 (unread chains) | % of premium | 2017-06-30 | 2022-10-31 | 62 | 105 | **wiped out** 2017-10-31 | −100% (wiped out) | $0 (2017-10-31) | 100.0% | $242 | −75.8% | $162 (2022-02-28) | 86.1% |

## Balance curves

One chart a row, in the page-1 order: method A in blue, method B in red, the balance on a log scale, the dashed line at $1,000, an ✕ where a row is wiped out.

<div class="grid">

![](charts_1000/r01_s20a.png){width=24%}
![](charts_1000/r02_s1.png){width=24%}
![](charts_1000/r03_s7j-atm_put.png){width=24%}
![](charts_1000/r04_s32.png){width=24%}
![](charts_1000/r05_s7j-put_30d.png){width=24%}
![](charts_1000/r06_s32.png){width=24%}
![](charts_1000/r07_s37b.png){width=24%}
![](charts_1000/r08_s7j-put_15d.png){width=24%}
![](charts_1000/r09_s37b.png){width=24%}
![](charts_1000/r10_s37a.png){width=24%}
![](charts_1000/r11_s37a.png){width=24%}
![](charts_1000/r12_s41a.png){width=24%}
![](charts_1000/r13_s35.png){width=24%}
![](charts_1000/r14_s9a.png){width=24%}
![](charts_1000/r15_s35.png){width=24%}
![](charts_1000/r16_s6b.png){width=24%}
![](charts_1000/r17_s40b.png){width=24%}
![](charts_1000/r18_s41b.png){width=24%}
![](charts_1000/r19_s4b.png){width=24%}
![](charts_1000/r20_s40a.png){width=24%}
![](charts_1000/r21_s8a.png){width=24%}
![](charts_1000/r22_s2b.png){width=24%}
![](charts_1000/r23_s1.png){width=24%}
![](charts_1000/r24_s2.png){width=24%}
![](charts_1000/r25_s7c.png){width=24%}
![](charts_1000/r26_s17.png){width=24%}
![](charts_1000/r27_s17.png){width=24%}
![](charts_1000/r28_s4.png){width=24%}
![](charts_1000/r29_s5.png){width=24%}
![](charts_1000/r30_s43.png){width=24%}
![](charts_1000/r31_s15.png){width=24%}
![](charts_1000/r32_s29e.png){width=24%}
![](charts_1000/r33_s7b.png){width=24%}
![](charts_1000/r34_s7d.png){width=24%}
![](charts_1000/r35_s8c.png){width=24%}
![](charts_1000/r36_s29c.png){width=24%}
![](charts_1000/r37_s7a.png){width=24%}
![](charts_1000/r38_s29d.png){width=24%}
![](charts_1000/r39_s29a.png){width=24%}
![](charts_1000/r40_s29b.png){width=24%}
![](charts_1000/r41_s13.png){width=24%}
![](charts_1000/r42_s7i.png){width=24%}
![](charts_1000/r43_s30c.png){width=24%}
![](charts_1000/r44_s30e.png){width=24%}
![](charts_1000/r45_s30b.png){width=24%}
![](charts_1000/r46_s30a.png){width=24%}
![](charts_1000/r47_s8b.png){width=24%}
![](charts_1000/r48_s27a.png){width=24%}
![](charts_1000/r49_s27b.png){width=24%}
![](charts_1000/r50_s9b.png){width=24%}
![](charts_1000/r51_s21d.png){width=24%}
![](charts_1000/r52_s6a.png){width=24%}
![](charts_1000/r53_s6c.png){width=24%}
![](charts_1000/r54_s19.png){width=24%}
![](charts_1000/r55_s25.png){width=24%}
![](charts_1000/r56_s26b.png){width=24%}
![](charts_1000/r57_s28a.png){width=24%}
![](charts_1000/r58_s21c.png){width=24%}
![](charts_1000/r59_s26c.png){width=24%}
![](charts_1000/r60_s28b.png){width=24%}
![](charts_1000/r61_s8d.png){width=24%}
![](charts_1000/r62_s6d.png){width=24%}
![](charts_1000/r63_s20b.png){width=24%}
![](charts_1000/r64_s26a.png){width=24%}
![](charts_1000/r65_s6e.png){width=24%}
![](charts_1000/r66_s21a.png){width=24%}
![](charts_1000/r67_s21b.png){width=24%}
![](charts_1000/r68_s7e.png){width=24%}
![](charts_1000/r69_s7g.png){width=24%}
![](charts_1000/r70_s7h.png){width=24%}
![](charts_1000/r71_s7f.png){width=24%}
![](charts_1000/r72_s31.png){width=24%}
![](charts_1000/r73_s34.png){width=24%}
![](charts_1000/r74_s30d.png){width=24%}
![](charts_1000/r75_s8e.png){width=24%}

</div>
