# Final research report

**Repository:** georgeredo, branch `claude/lucid-heisenberg-bpyq7k`. **Built:** 2026-10-23 by
`research_notes/FINAL REPORT/build/` (`build.py`, then `render.py` for the PDF); **re-scored 2026-10-24 at Robinhood's fees**.

**Fees: Robinhood is primary.** From 2026-10-24 the research's default cost model is Robinhood's options fee schedule
(`docs/FEES_ROBINHOOD.md`, read 2026-10-24). In short: $0 commission; ETF options about $0.04 a contract to buy and $0.06
to sell (a 1-lot); SPXW $1.04 a contract a side under $1.00 of premium and $1.13 at $1.00 and up (non-Gold); nothing at
expiry or settlement. The studies charged $0.65 a contract each way, or $0.68748 with pass-throughs, or $0.70 for the
older Compass studies; SPXW was $1.18748 / $1.27748.

Every trade is re-priced on its own fills: buys at the ask and sales at the bid, exactly as the study filled them. The
study's modelled fee is added back and Robinhood's is charged. Every figure is printed at Robinhood's fees first, with the
study's own beside it on page 1 and in each section's fee table.

Where a trade file lacks a leg's price, side or exit, Robinhood's fee is inferred from the rule. Those rows are marked ‡
and labelled "Robinhood fees inferred from the rule" in their section. Vendor-recorded rows (§) carry no fee in either
column.

Every verdict stays exactly as pre-registered, on the study's own fees. The column "would the verdict differ at Robinhood
fees?" only runs the frozen pass rule on the Robinhood-fee returns. It is descriptive, not a new verdict.
**Inventory of every study:** `INVENTORY.md`, the file beside this one.

This report is read-only with respect to the research. It adds no test, variant or fetch, opens no holdout and
changes no rule. Every metric is recomputed from a study's committed trade-level output, or from the scratchpad copy
that INVENTORY.md names, with one exception: two studies (#31 and #40) were rerun deterministically from their
committed scripts at their own commits, on the same stored inputs. Step 6's rule membership (#17) is recomputed by its committed
`step6/trade.py` `choose()`, on the scratchpad population it was built from. Where a figure cannot be produced, the report
writes "not available — <why>". GeorgeFi's own recorded card returns appear only in sections marked
**vendor-recorded, not re-marked** (#1, and the grade check in #29f).

**Units.** Return per trade is given as:

- % of premium paid, for long options;
- % of max risk, for spreads and butterflies;
- % of the credit received, for naked short straddles and strangles;
- % of cash set aside, for cash-secured puts;
- % of notional, for stock trades. Their "$" column is $ per 100 shares, because every stock trade here is 100 shares.

$ per trade is one lot, after every fee the study charged.

## Page 1. Every strategy, sorted by mean trade at Robinhood fees

One row per strategy, on the period that carries its verdict, sorted by mean trade at Robinhood fees (% in
each row's own unit), with the mean at the study's own fees beside it. The table pools all names when a study judged them together, and shows one row per name or variant when it did
not. The interval is the 20-session moving-block bootstrap of the mean % a trade (`audit_lib.session_stats`, 2,000
draws). It is "n/a" when the period has fewer than 60 sessions. "Biggest win/loss" are $ for one trade, with its entry
date. The verdict is the study's own, as pre-registered. The last column is descriptive. It runs the study's frozen pass
rule on the Robinhood-fee returns: through the study's own code where the trade list allows (the Compass features' Δ, the
direction screen); otherwise through the rule's computable part, with the report's block-20 interval, and it says so. ‡ marks
a row whose Robinhood fees are partly inferred from the rule. § marks a vendor-recorded row.

**Robinhood against the study's fees, on page 1.** 75 rows. The five largest changes in the mean trade:

- #40a Compass EMA ladder: PREVIEW 2025-03, 13 versions (rerun) (V1, preview 2025-03): −9.20 → **−4.89** % of premium (−2.76 → −1.48 $ a trade).
- #7f S12 Intraday momentum: first-half-hour direction → 10:00–15:00 long option (all names, 2022-11→2026-10): −15.07 → **−11.94** % of premium (−4.36 → −3.06 $ a trade).
- #21a Phase 2 hyp C: 15:00 SPY/QQQ P1 iron ±2 butterfly, held to settlement (all names, OOS 2025–26): +4.49 → **+7.46** % of max risk (+3.41 → +5.81 $ a trade).
- #21b Phase 2 hyp C: 15:00 SPY/QQQ P2 call ±2 butterfly, held to settlement (all names, OOS 2025–26): +2.09 → **+5.02** % of max risk (+1.34 → +3.75 $ a trade).
- #30e Compass features BX3e: the 14:00 exit on the physically settled names only … (0DTE→60 DTE, 15 names, holdout (opened)): −11.03 → **−8.12** % of premium (−14.09 → −12.83 $ a trade).

Rows whose mean trade changes sign: **2**: #4b all names ledger E2 (−0.13 → +1.50); #7c all names 2017-06→2026-10 (−0.08 → +0.83).

Rows where the frozen pass rule, run on Robinhood-fee returns, would read differently: **2**: #21a all names; #21c all names. This is descriptive; every verdict stays as pre-registered.

| # | strategy | name | period | trades | mean trade at Robinhood fees | mean trade at the study's fees | win % Robinhood / study | biggest win | biggest loss | 20-session block 95% (mean %, Robinhood) | verdict (as pre-registered, at the study's fees) | would the verdict differ at Robinhood fees? (descriptive) |
|---------|------------------------------------------|---------------|------------------------|------------|---------------------------|---------------------------|------------------|---------------------|---------------------|------------------------|------------------------------|------------------------------------------------------------------|
| 6e | H15 carry lane: the 14:05 SPXW short strangle at ±0.5 expected move, held to … | SPXW | TEST | 407 | **+17.98 % credit** / +150.91 ‡ | +18.02 / +151.17 | 70.8 / 70.8 | +4,578 (2025-04-10) | −7,131 (2026-03-09) | [+3.49, +29.85] | Open, NOT promotable | Its computable part (mean > 0, interval clear of zero): No — passes at both (Robinhood: mean +17.98%, lower end +3.49); the reselection and the forward T-G are not in the trade list |
| 1 | GeorgeFi vendor cards (the vendor's own recorded P&L) | all names | Epoch 1 | 546 | **+14.82 % prem** / +79.21 § | +14.82 / +79.21 | 78.8 / 78.8 | +4,020 (2026-02-06) | −1,375 (2026-02-18) | n/a (< 60 sessions) | Not evidence | — (no pass rule: descriptive) |
| 41a | EMA system v0: PREVIEW on 2026-10-12 → 16 (5 sessions) | Config A X1 | preview 2026-10-12→16 | 57 | **+11.68 % prem** / +43.87 | +10.67 / +43.03 | 61.4 / 61.4 | +718 (2026-10-14) | −772 (2026-10-15) | n/a (< 60 sessions) | PREVIEW | — (no pass rule: a preview) |
| 6d | T-E: the 13:00 SPXW ATM straddle held to PM settlement, ex FOMC/CPI/NFP (H13) | SPXW | TEST | 388 | **+8.74 % credit** / +85.30 ‡ | +8.75 / +85.56 | 67.0 / 67.0 | +4,100 (2025-03-06) | −34,022 (2025-04-09) | [+1.85, +14.75] | FAIL | No — fails at both (Robinhood: mean +85.30, lower end −115.97) |
| 21a | Phase 2 hyp C: 15:00 SPY/QQQ P1 iron ±2 butterfly, held to settlement | all names | OOS 2025–26 | 878 | **+7.46 % risk** / +5.81 | +4.49 / +3.41 | 53.3 / 52.3 | +156 (2026-01-28) | −130 (2026-01-07) | [+0.15, +15.30] | Not confirmed | **Yes** — fails at the study's fees, passes at Robinhood's (all four parts; Robinhood: mean +7.46%, lower end +0.15, without the best five +3,788 $, years 2025 +5.17, 2026 +6.62) |
| 27a | After-hours exercise study: fly5 iron ±5, case (b) the post-market decision | all names | ii | 987 | **+6.72 % risk** / +24.19 | +6.25 / +22.52 | 55.8 / 55.7 | +2,199 (2026-06-22) | −2,193 (2026-04-07) | [−5.36, +15.74] | DROP | Keep-or-drop rule: No — dropped at both (Robinhood: mean +24.19, lower end −17.22) |
| 26c | Paper tracker: condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | SPY | ii | 2,090 | **+6.11 % risk** / +10.07 | +4.68 / +7.67 | 82.8 / 82.1 | +63 (2025-04-10) | −187 (2026-04-13) | [+3.87, +8.01] | Positive in ii | — (verdict at the forward N only; the historical rows are descriptive) |
| 6c | T-C: the 13:00 SPXW short straddle bought back 15:55 (H11) | SPXW | 2025-06→2026-10 | 339 | **+5.07 % credit** / +71.91 ‡ | +5.11 / +72.43 | 63.4 / 63.4 | +3,370 (2025-09-17) | −8,500 (2026-06-11) | [−0.09, +8.97] | FAIL | No — fails at both (Robinhood: mean +71.91, lower end −56.51) |
| 21b | Phase 2 hyp C: 15:00 SPY/QQQ P2 call ±2 butterfly, held to settlement | all names | OOS 2025–26 | 880 | **+5.02 % risk** / +3.75 | +2.09 / +1.34 | 52.3 / 51.2 | +154 (2026-01-28) | −131 (2026-01-07) | [−2.27, +12.91] | Not confirmed | No — fails at both (all four parts; Robinhood: mean +5.02%, lower end −2.27, without the best five +2,002 $, years 2025 +2.90, 2026 +4.83) |
| 20b | Phase 2 hyp B: the midday SPY iron condor (em1, mid-VIX), the midday pick | SPY | OOS 2025–26 | 1,202 | **+4.67 % risk** / +7.95 | +3.25 / +5.55 | 81.9 / 81.6 | +59 (2026-04-29) | −176 (2026-07-24) | [+1.62, +7.46] | "Needs X" | Its computable part (mean > 0, interval clear of zero): No — passes at both (Robinhood: mean +4.67%, lower end +1.62); the rule picks the cell on fit; read here on OOS |
| 20a | Phase 2 hyp B: boundary touch — SPY 2-wide 25-delta credit spread, held (the … | SPY | OOS 2025–26 | 2,600 | **+4.59 % risk** / +8.04 | +3.91 / +6.84 | 88.2 / 88.1 | +46 (2025-11-14) | −190 (2026-04-13) | [+2.24, +6.37] | No edge | Its computable part (mean > 0, interval clear of zero): No — passes at both (Robinhood: mean +4.59%, lower end +2.24); the rule picks the cell on fit; read here on OOS |
| 25 | Phase 3 hyp F: the 15:30 SPY/QQQ long call ±5 butterfly (cash account) | all names | OOS 2025–26 | 879 | **+4.50 % risk** / +12.31 | +3.85 / +9.89 | 63.0 / 62.2 | +262 (2026-04-29) | −332 (2025-03-04) | [+2.14, +6.84] | Passes all four, but the cell was named after C's OOS was printed | No — passes at both (all four parts; Robinhood: mean +4.50%, lower end +2.14, at $0.01 a leg +3.43%, without the best five +8,588 $, names QQQ +9.11, SPY +15.50) |
| 26b | Paper tracker: fly5 (SPY/QQQ ±5 butterflies at 15:00 and 15:30: iron, call, put) | all names | ii | 5,271 | **+4.29 % risk** / +12.05 | +3.62 / +9.64 | 61.4 / 60.5 | +283 (2026-04-29) | −468 (2026-05-12) | [+2.45, +6.13] | Iron clear of zero in i and ii | — (verdict at the forward N only; the historical rows are descriptive) |
| 26a | Paper tracker: condor_em1 (SPY 2-wide iron condor at ± the ATM straddle, … | SPY | ii | 2,068 | **+3.90 % risk** / +6.50 | +2.46 / +4.10 | 80.7 / 80.4 | +66 (2026-07-29) | −185 (2025-04-09) | [+0.90, +6.46] | Historical periods through zero | — (verdict at the forward N only; the historical rows are descriptive) |
| 27b | After-hours exercise study: condor_d20, case (b) | SPY | ii | 1,176 | **+3.70 % risk** / +6.07 | +2.37 / +3.84 | 83.3 / 83.3 | +868 (2026-09-16) | −1,796 (2026-04-07) | [−11.28, +15.87] | DROP | Keep-or-drop rule: No — dropped at both (Robinhood: mean +6.07, lower end −17.97) |
| 41b | EMA system v1: PREVIEW on three drawn weeks (up, flat, down) | Config A X1 | three weeks pooled | 64 | **+3.29 % prem** / +3.91 | +2.23 / +2.98 | 54.7 / 54.7 | +1,358 (2026-02-03) | −872 (2026-02-03) | [−13.43, +29.47] | PREVIEW | — (no pass rule: a preview) |
| 1 | GeorgeFi vendor cards (the vendor's own recorded P&L) | all names | Epoch 2 | 603 | **+3.13 % prem** / −6.23 § | +3.13 / −6.23 | 48.1 / 48.1 | +3,313 (2026-07-13) | −3,400 (2026-07-13) | [−0.74, +9.76] | Not evidence | — (no pass rule: descriptive) |
| 21c | Phase 2 hyp C: 15:00 SPY/QQQ P3 call ±5 butterfly, held to settlement | all names | OOS 2025–26 | 878 | **+2.84 % risk** / +6.94 | +2.15 / +4.52 | 59.2 / 58.5 | +277 (2026-04-29) | −468 (2026-05-12) | [+0.10, +5.46] | Not confirmed | **Yes** — fails at the study's fees, passes at Robinhood's (all four parts; Robinhood: mean +2.84%, lower end +0.10, without the best five +3,769 $, years 2025 +4.46, 2026 +10.13) |
| 6a | T-A: the 13:00 short ATM 0DTE straddle, SPY/QQQ/IWM, bought back 15:55 (H9) | all names | 2025-06→2026-10 | 1,017 | **+2.44 % credit** / +5.17 | +0.62 / +2.57 | 63.1 / 62.2 | +346 (2026-06-12) | −1,184 (2026-06-11) | [−2.53, +6.28] | FAIL | No — fails at both (Robinhood: mean +5.17, lower end −6.16) |
| 21d | Phase 2 hyp C: debit vertical 0.70/0.30, universe B, held (the vertical pick) | all names | OOS 2025–26 | 1,761 | **+2.09 % prem** / +5.61 ‡ | +1.25 / +4.95 | 52.0 / 51.6 | +6,048 (2025-04-11) | −7,092 (2025-04-10) | [−2.01, +5.45] | Loses less than the naked contract but still loses | — (no pass rule: the pre-registered expectation was a negative OOS) |
| 28b | SPXW analogue B: 20-delta iron condor, wings 2×ratio, 13:00–15:00 (condor_d20) | SPXW | selection | 2,157 | **+1.53 % risk** / +25.28 | +1.49 / +24.69 | 76.8 / 76.8 | +605 (2026-07-29) | −1,849 (2026-04-13) | [−1.08, +3.50] | FAIL | No — fails at both (three parts; Robinhood: selection mean +25.28 $, lower end −18.27, at +$0.05 +20.28) |
| 4b | GeorgeFi entries with the trail engine (reconstruction C, G2) | all names | ledger E2 | 516 | **+1.50 % prem** / +2.46 | −0.13 / +2.27 | 40.1 / 39.0 | +1,752 (2026-07-06) | −778 (2026-03-16) | [−2.81, +3.24] | No robust entry timing | — (no pass rule: descriptive) |
| 7c | S03 Quick Scalps with weekly expirations (1–7 days) | all names | 2017-06→2026-10 | 818 | **+0.83 % prem** / +2.57 | −0.08 / +1.27 | 37.9 / 37.7 | +464 (2020-05-15) | −226 (2020-03-10) | [−0.91, +2.53] | Nothing promoted | No — fails at both (Robinhood: mean +2.57, lower end −1.49) |
| 7j-atm_put | S17 Index put-writing: monthly ATM cash-secured put | all names | 2012-06→2026-10 | 334 | **+0.66 % capital** / +200.60 | +0.65 / +199.27 | 81.4 / 81.4 | +2,118 (2026-07-17) | −9,870 (2020-02-21) | [+0.17, +1.08] | PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 … | No — passes at both (A7, per cell; Robinhood: mean +200.60 $, lower end +42.50) |
| 7j-put_30d | S17 Index put-writing: monthly 0.30-delta cash-secured put | all names | 2012-06→2026-10 | 334 | **+0.46 % capital** / +142.99 | +0.46 / +141.65 | 85.6 / 85.6 | +1,428 (2026-05-15) | −9,370 (2020-02-21) | [+0.03, +0.79] | PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 … | No — passes at both (A7, per cell; Robinhood: mean +142.99 $, lower end +16.36) |
| 37b | Edge H8: turn of the month (SPY, QQQ stock) | QQQ | single test | 172 | **+0.397 % notional** / +111.66 | +0.387 / +110.22 | 59.3 / 59.3 | +3,373 (2026-07-30) | −2,369 (2026-01-29) | [+0.016, +0.705] | SPY FAIL; QQQ PASS at 1× only | No — fails at both (each name read alone, at 1× (2× not re-read); Robinhood: mean +111.66 $, lower end −9.31) |
| 37b | Edge H8: turn of the month (SPY, QQQ stock) | SPY | single test | 117 | **+0.315 % notional** / +135.10 | +0.311 / +134.00 | 60.7 / 60.7 | +2,808 (2026-07-30) | −2,463 (2024-07-30) | [−0.049, +0.646] | SPY FAIL; QQQ PASS at 1× only | No — fails at both (each name read alone, at 1× (2× not re-read); Robinhood: mean +135.10 $, lower end −19.75) |
| 7j-put_15d | S17 Index put-writing: monthly 0.15-delta cash-secured put | all names | 2012-06→2026-10 | 334 | **+0.27 % capital** / +83.86 | +0.26 / +82.52 | 94.0 / 94.0 | +720 (2026-05-15) | −8,445 (2020-02-21) | [−0.09, +0.48] | PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 … | No — fails at both (A7, per cell; Robinhood: mean +83.86 $, lower end −14.32) |
| 37a | Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED | QQQ | single test | 108 | **+0.214 % notional** / +70.01 | +0.210 / +69.59 | 61.1 / 61.1 | +1,162 (2024-07-30) | −543 (2026-07-28) | [+0.053, +0.358] | PASS both names | No — passes at both (each name read alone, at 1× (Bonferroni and 2× not re-read); Robinhood: mean +70.01 $, lower end +18.16) |
| 37a | Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED | SPY | single test | 77 | **+0.191 % notional** / +70.54 | +0.190 / +70.43 | 55.8 / 55.8 | +823 (2024-07-30) | −620 (2021-01-26) | [+0.060, +0.355] | PASS both names | No — passes at both (each name read alone, at 1× (Bonferroni and 2× not re-read); Robinhood: mean +70.54 $, lower end +11.25) |
| 32 | Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock) | QQQ | single test | 3,299 | **+0.038 % notional** / +10.92 | +0.027 / +9.42 | 51.6 / 50.5 | +2,402 (2024-08-02) | −1,448 (2025-04-07) | [+0.005, +0.074] | FAIL | No — fails at both (both names must pass; at Robinhood's fees QQQ passes (changed) (mean +10.92, lower end +1.33); SPY fails (mean +12.26, lower end −3.39)) |
| 32 | Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock) | SPY | single test | 2,177 | **+0.035 % notional** / +12.26 | +0.032 / +11.09 | 51.2 / 50.8 | +3,028 (2020-03-13) | −1,749 (2025-04-07) | [−0.009, +0.088] | FAIL | No — fails at both (both names must pass; at Robinhood's fees QQQ passes (changed) (mean +10.92, lower end +1.33); SPY fails (mean +12.26, lower end −3.39)) |
| 35 | Edge H4: market intraday momentum (SPY, QQQ stock) | QQQ | test 2025-10-13→2026-10-22 | 257 | **+0.013 % notional** / +9.92 | +0.014 / +10.32 | 49.8 / 49.8 | +902 (2026-07-29) | −378 (2025-11-20) | [−0.017, +0.048] | FAIL | No — fails at both (each name read alone; Robinhood: mean +9.92 $, lower end −9.77) |
| 9a | Lifecycle P1: Quick Scalps → cash-secured put sale (portfolio) | all names | hold-out 2025-10→2026-10 | 122 | **+0.01 % risk** / +9.39 ‡ | +0.01 / +8.09 | 63.1 / 63.1 | +137 (2026-08-03) | −197 (2025-10-14) | [−0.02, +0.04] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean +0.01%, lower end −0.02); R1–R6 (Holm, the random-day control) need more than this list |
| 35 | Edge H4: market intraday momentum (SPY, QQQ stock) | SPY | test 2025-10-13→2026-10-22 | 257 | **−0.005 % notional** / −3.45 | −0.004 / −2.95 | 45.5 / 45.5 | +573 (2026-07-29) | −373 (2026-09-30) | [−0.029, +0.019] | FAIL | No — fails at both (each name read alone; Robinhood: mean −3.45 $, lower end −20.01) |
| 6b | T-B: gamma-conditioned last-30-minute momentum in SPY shares (H10) | SPY | negative-gamma days 2024-05→2026-10 | 299 | **−0.029 % notional** / −18.38 ‡ | −0.031 / −19.59 | 46.5 / 46.2 | +523 (2025-04-04) | −698 (2025-03-04) | [−0.054, −0.001] | FAIL | No — fails at both (Robinhood: mean −0.03%, lower end −0.05) |
| 28a | SPXW analogue A: iron fly ±5×ratio at 15:00 and 15:30 (fly5 iron) | SPXW | selection | 882 | **−0.40 % risk** / −19.23 | −0.41 / −19.82 | 58.8 / 58.8 | +2,569 (2026-09-16) | −3,549 (2026-03-09) | [−2.27, +1.43] | FAIL | No — fails at both (three parts; Robinhood: selection mean −19.23 $, lower end −86.71, at +$0.05 −24.23) |
| 43 | Compass ICT: sweep → displacement/MSS → FVG on SPXW 0DTE | v0 | exploration 2022-05→2026-10-09 | 142 | **−0.73 % prem** / +48.84 | −0.76 / +48.26 | 37.3 / 37.3 | +9,735 (2026-07-27) | −3,284 (2025-05-05) | [−7.74, +7.57] | Exploration only | — (no pass rule: exploration only; no holdout read) |
| 40b | Compass EMA ladder: "take profits are the nearest EMAs" PREVIEW (E1 ATM, E2 … | E1 | preview 2025-02 (fresh) | 1,761 | **−1.25 % prem** / −1.22 | −2.75 / −2.49 | 31.8 / 30.8 | +177 (2025-02-03) | −85 (2025-02-07) | n/a (< 60 sessions) | PREVIEW | — (no pass rule: a preview) |
| 15 | Step 4: turn-up buy (1.5× the low) + 20% trailing stop, near the money | all names | check 2025–26 | 26,258 | **−1.37 % prem** / −2.06 | −2.02 / −2.26 | 29.5 / 29.0 | +21,608 (2025-04-07) | −39,942 (2025-04-09) | [−2.96, +0.56] | A trailing stop beats holding but still loses. | — (no pass rule: no pass rule pre-registered) |
| 19 | Phase 2 hyp A: the low-moc_mag closing pin (SPXW short call spread, 15:30, held) | SPXW | OOS 2025–26 | 177 | **−1.43 % risk** / −33.83 | −1.39 / −33.03 | 87.6 / 87.6 | +173 (2025-04-14) | −2,312 (2025-04-30) | [−3.57, +0.26] | NO EDGE | No — fails at both (Robinhood: mean −33.83, lower end −85.45) |
| 7e | S10 Short premium: fade the Quick Scalps signal (single contract, 2× stop, to … | all names | 2022-11→2026-10 | 2,886 | **−1.68 % credit** / +1.82 | −3.63 / +0.52 | 55.5 / 55.4 | +457 (2025-04-09) | −425 (2026-06-09) | [−7.80, +4.77] | Nothing promoted | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −1.68%, lower end −7.80); the matched-random comparison is not recomputed |
| 2b | George rebuild: the best of 144 variants (sweep / ict+gex / morning / … | all names | out-of-sample 2026-03→10 | 385 | **−1.87 % prem** / −0.48 | −3.04 / −1.78 | 40.3 / 40.3 | +123 (2026-06-25) | −102 (2026-06-29) | [−3.37, −0.33] | Rejected | — (no pass rule: no pass rule pre-registered) |
| 4 | GeorgeFi's own trades re-priced at the NBBO (G1) | all roots | ledger E2 | 594 | **−2.02 % prem** / −41.59 | −2.54 / −42.07 | 45.8 / 45.1 | +3,018 (2026-09-21) | −3,476 (2026-07-13) | [−5.93, +2.73] | Not supported after execution | — (no pass rule: an execution check) |
| 7g | S12b 10:00 long option in the first-half-hour direction | all names | 2022-11→2026-10 | 2,499 | **−2.27 % prem** / −3.58 | −3.60 / −4.87 | 33.6 / 33.4 | +2,479 (2025-04-09) | −412 (2026-06-25) | [−8.13, +4.26] | Nothing promoted | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −2.27%, lower end −8.13); its two-part rule A1 also reads the underlying |
| 2 | George rebuild: the GeorgeFi-like reference (sweep / ict+gex / all / none / … | all names | out-of-sample 2026-03→10 | 1,399 | **−2.33 % prem** / −1.69 | −3.84 / −2.99 | 37.3 / 37.2 | +143 (2026-06-26) | −127 (2026-06-25) | [−3.41, −1.58] | Rejected | — (no pass rule: no pass rule pre-registered) |
| 5 | Deep research round 1: flow rule F1 on SPY (H2 family) | SPY | 2025-07→2026-10 | 638 | **−2.48 % prem** / −2.82 | −3.45 / −4.12 | 35.9 / 35.9 | +177 (2025-12-18) | −82 (2026-07-29) | [−3.55, −1.17] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −2.48%, lower end −3.55); its 62-cell multiple-testing correction needs the other cells |
| 7a | S01 Quick Scalps (owner baseline) on index 0DTE | all names | 2022-11→2026-10 | 2,886 | **−3.01 % prem** / −2.89 | −4.92 / −4.19 | 35.9 / 34.3 | +347 (2026-06-09) | −156 (2025-04-07) | [−4.41, −1.79] | REJECTED | No — fails at both (Robinhood: mean −2.89, lower end −4.49) |
| 29c | Picker, S2: "5 minutes" as a hard exit | all names | whole span (verdict) | 2,943 | **−3.03 % prem** / −12.07 | −4.18 / −13.04 | 40.1 / 38.3 | +908 (2025-04-09) | −992 (2026-02-05) | [−4.12, −2.02] | Labelled | — (no pass rule: a sensitivity) |
| 7b | S02 Quick Scalps: 41-variant grid, walk-forward OOS (lower-bound selection) | all names | walk-forward OOS 2024-01→2026-10 | 3,200 | **−3.09 % prem** / −2.51 | −5.31 / −3.81 | 36.4 / 34.8 | +347 (2026-06-09) | −162 (2025-04-07) | [−4.63, −1.82] | Nothing promoted | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −3.09%, lower end −4.63); the matched-random comparison is not recomputed |
| 9b | Lifecycle P2: Quick Scalps → credit put spread to expiry (portfolio) | all names | hold-out 2025-10→2026-10 | 196 | **−3.13 % risk** / −30.07 ‡ | −3.65 / −34.72 | 87.8 / 87.8 | +1,951 (2025-10-14) | −5,189 (2026-01-16) | [−15.66, +4.66] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −3.13%, lower end −15.66); R1–R6 (Holm, the random-day control) need more than this list |
| 7d | S09 Quick Scalps on SPXW 0DTE | SPXW | 2022-05→2026-10 | 1,229 | **−3.93 % prem** / −47.04 | −3.81 / −46.18 | 33.8 / 33.8 | +1,483 (2025-04-09) | −1,002 (2026-03-09) | [−5.60, −2.27] | REJECTED | No — fails at both (Robinhood: mean −47.04, lower end −63.75) |
| 17 | Step 6: the six pre-registered runner rules × three exits | B1a | check 2025→2026-10-09 | 6,350 | **−3.96 % prem** / −89.19 | −3.97 / −89.48 | 41.6 / 41.6 | +1,958 (2026-06-17) | −2,891 (2025-07-30) | [−4.78, −3.40] | FAIL | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −3.96%, lower end −4.78); the 97.5th percentile of 500 cell-matched random draws is not recomputed |
| 29e | Picker, IMPROVED (picked on the cards): PDH sweep → put, 10:00–12:00, +25% or … | all names | whole span (verdict) | 516 | **−4.37 % prem** / −17.87 | −5.52 / −18.73 | 39.5 / 38.8 | +478 (2024-08-07) | −1,172 (2026-02-20) | [−7.23, −1.84] | FAIL on every name | — (no pass rule: labelled, read only) |
| 7h | S15 VRP-conditioned 10:00 short ATM 0DTE straddle (unconditional row) | all names | 2022-11→2026-10 | 1,941 | **−4.50 % credit** / −12.86 | −5.47 / −15.46 | 58.2 / 58.0 | +663 (2024-08-05) | −3,321 (2025-04-09) | [−8.99, −0.44] | Nothing promoted | — (no pass rule: the rule reads the conditioned cells; this row is the unconditional one) |
| 40a | Compass EMA ladder: PREVIEW 2025-03, 13 versions (rerun) | V1 | preview 2025-03 | 2,781 | **−4.89 % prem** / −1.48 | −9.20 / −2.76 | 18.6 / 15.5 | +149 (2025-03-28) | −30 (2025-03-05) | n/a (< 60 sessions) | PREVIEW | — (no pass rule: a preview) |
| 29a | Picker (GeorgeFi rule), PRIMARY: opening-range fade, stop 0.68, target 1.25, … | all names | whole span (verdict) | 2,943 | **−4.89 % prem** / −21.65 | −6.05 / −22.62 | 36.8 / 35.9 | +1,388 (2025-04-09) | −2,952 (2025-04-07) | [−6.21, −3.68] | FAIL on every name | No — fails at both (every name must pass; at Robinhood's fees IWM fails (mean −6.54, lower end −9.08); QQQ fails (mean −3.99, lower end −5.98); SPXW fails (mean −4.93, lower end −6.70); SPY fails (mean −4.87, lower end −6.71)) |
| 29d | Picker, S3: SPXW rides to the official close when in the money at 15:58 | SPXW | whole span (verdict) | 908 | **−4.93 % prem** / −59.13 | −4.96 / −59.43 | 37.0 / 37.0 | +1,388 (2025-04-09) | −2,952 (2025-04-07) | [−6.70, −3.46] | Labelled | — (no pass rule: a sensitivity) |
| 29b | Picker, SECONDARY: the narrative's +6% breakeven lock and VIX trail | all names | whole span (verdict) | 2,943 | **−5.04 % prem** / −20.30 | −6.20 / −21.27 | 41.9 / 39.8 | +1,388 (2025-04-09) | −1,182 (2025-04-23) | [−6.20, −3.90] | Labelled | — (no pass rule: no verdict of its own) |
| 7i | S16b Prior-day fade with a weekly contract (time exit) | all names | 2017-06→2026-10 | 1,041 | **−5.93 % prem** / −8.61 | −6.78 / −9.91 | 38.0 / 37.8 | +1,276 (2022-10-13) | −444 (2026-06-12) | [−10.19, −2.31] | Nothing promoted | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −5.93%, lower end −10.19); its two-part rule A1 also reads the underlying |
| 30d | Compass features BV1b: the V1 veto at 3% (PASSED, Phase B) | 0DTE→60 DTE, 15 names | holdout (opened) | 251,808 | **−5.93 % prem** / −25.68 | −6.73 / −26.77 | 32.0 / 31.9 | +45,478 (2026-03-30) | −26,112 (2026-03-30) | [−8.57, −3.08] | PASS | No — passes at both (the study's own stats.delta on the holdout; Δ +4.30 → +3.46 points, Robinhood interval [+1.82, +4.95]) |
| 17 | Step 6: the six pre-registered runner rules × three exits | A1a | check 2025→2026-10-09 | 1,035 | **−6.72 % prem** / −23.79 | −7.54 / −24.69 | 36.6 / 36.6 | +4,162 (2025-04-09) | −3,532 (2025-04-04) | [−14.64, +0.78] | FAIL | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −6.72%, lower end −14.64); the 97.5th percentile of 500 cell-matched random draws is not recomputed |
| 30c | Compass features X3: sell a same-day long option at the 14:00 bid (PASSED) | 0DTE→60 DTE, 15 names | holdout (opened) | 233,454 | **−6.97 % prem** / −10.58 | −9.51 / −11.72 | 29.6 / 29.0 | +19,168 (2025-11-20) | −4,252 (2025-11-21) | [−11.22, −4.91] | PASS | No — passes at both (the study's own stats.delta on the holdout; Δ +7.78 → +8.21 points, Robinhood interval [+4.53, +11.38]) |
| 30b | Compass features V1: veto a spread over 10% of mid (PASSED) | 0DTE→60 DTE, 15 names | holdout (opened) | 474,526 | **−7.14 % prem** / −26.08 | −8.43 / −27.16 | 29.7 / 29.5 | +45,478 (2026-03-30) | −29,000 (2026-10-19) | [−9.97, −3.99] | PASS | No — passes at both (the study's own stats.delta on the holdout; Δ +2.61 → +2.25 points, Robinhood interval [+1.41, +3.07]) |
| 30e | Compass features BX3e: the 14:00 exit on the physically settled names only … | 0DTE→60 DTE, 15 names | holdout (opened) | 203,289 | **−8.12 % prem** / −12.83 | −11.03 / −14.09 | 29.1 / 28.4 | +7,780 (2026-07-02) | −3,457 (2021-12-17) | [−12.22, −6.21] | PASS | No — passes at both (the study's own stats.delta on the holdout; Δ +7.67 → +8.15 points, Robinhood interval [+4.68, +11.18]) |
| 8d | V3a: single-name 0DTE short ATM straddle 10:00 → 15:50 | all names | hold-out | 1,622 | **−8.50 % prem** / −22.24 | −9.47 / −24.84 | 57.2 / 56.4 | +2,455 (2026-06-12) | −7,237 (2026-07-02) | [−18.41, −1.91] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −8.50%, lower end −18.41); rule A10 is not restated in the trade list |
| 8e | V8: month-end 13:00 long straddle on unread chains | all names | 2017-06→2022 (unread chains) | 105 | **−8.71 % prem** / −85.91 | −9.14 / −86.06 | 39.0 / 39.0 | +3,221 (2022-03-31) | −3,553 (2020-02-28) | [−23.53, +11.40] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −8.71%, lower end −23.53); rule A15 is not restated in the trade list |
| 30a | Compass features: the base trades (every feature is judged against them) | 0DTE→60 DTE, 15 names | holdout (opened) | 580,234 | **−9.39 % prem** / −30.17 | −11.03 / −31.26 | 28.3 / 28.2 | +45,478 (2026-03-30) | −32,491 (2026-10-19) | [−12.26, −6.22] | Descriptive | — (no pass rule: the reference set) |
| 7f | S12 Intraday momentum: first-half-hour direction → 10:00–15:00 long option | all names | 2022-11→2026-10 | 2,214 | **−11.94 % prem** / −3.06 | −15.07 / −4.36 | 31.1 / 30.4 | +1,189 (2026-07-29) | −221 (2025-04-08) | [−17.27, −6.14] | Nothing promoted | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −11.94%, lower end −17.27); its two-part rule A1 also reads the underlying |
| 13 | Step 2: buy near the money, sell at +100% or hold (within 0.5% of the price) | all names | check 2025–26 | 227,851 | **−17.61 % prem** / −54.14 | −18.66 / −54.46 | 40.2 / 40.1 | +9,038 (2025-04-09) | −18,091 (2025-11-28) | [−19.37, −16.02] | Every group loses before and after fees; near the money 29% double, … | — (no pass rule: a population study) |
| 31 | Compass direction: post-earnings drift in 31–60 DTE options (rerun) | single names | exploration (holdout unopened) | 12,114 | **−23.52 % prem** / −107.74 | −24.29 / −108.97 | 26.2 / 26.1 | +18,029 (2023-10-30) | −13,865 (2026-06-26) | [−27.45, −19.03] | FAIL | No — fails at both (the study's own analyse(); Δ −0.90 → −0.90 pp, Robinhood interval [−3.54, +1.71]) |
| 8a | V1 T0: short every monthly ATM straddle across the optionable universe | all names | hold-out | 12,484 | **−24.13 % prem** / −241.82 | −24.41 / −243.08 | 44.5 / 44.4 | +30,841 (2026-07-20) | −65,572 (2026-01-20) | [−31.78, −16.70] | Rejected | — (no pass rule: A8 reads T0's sign and the sorts' long-short, not this list alone) |
| 34 | Edge H3: earnings IV-crush short iron condor (single names) | single names | exploration (holdout unopened) | 2,209 | **−27.65 % risk** / −156.97 ‡ | −30.24 / −161.54 | 31.6 / 30.3 | +1,565 (2022-04-26) | −6,536 (2022-07-26) | [−29.75, −25.26] | FAIL | No — fails at both (Robinhood: mean −156.97, lower end −176.19) |
| 8c | V2b: long ATM straddle into the earnings report | single names | hold-out | 3,543 | **−30.57 % prem** / −339.77 | −31.05 / −342.34 | 10.2 / 10.1 | +19,714 (2026-05-21) | −11,371 (2026-02-10) | [−34.38, −25.36] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −30.57%, lower end −34.38); rule A9 is not restated in the trade list |
| 8b | V2a: short ATM straddle across the earnings report | single names | hold-out | 3,682 | **−35.40 % prem** / −378.11 | −35.95 / −380.58 | 26.2 / 25.6 | +5,019 (2026-08-05) | −22,300 (2026-05-04) | [−38.38, −29.66] | Rejected | Its computable part (mean > 0, interval clear of zero): No — fails at both (Robinhood: mean −35.40%, lower end −38.38); rule A9 is not restated in the trade list |

**Studies with no trade-level result** (each has its own short section below):

| # | study | why no metrics | verdict |
|------|------------------------------------------|------------------------------------------------------------------------------------------|------------------------------|
| 3 | George engine audit: the phase 1 reproduction audit of #1–#2 | the audit produced no trades of its own; its trade files are #2's, byte for byte (see #2). | Reproduced |
| 9c | Lifecycle Tier I, daily tier, L-A3, H-FLO (by configuration) | committed as configuration-level cells (grid_by_setup.csv, cells.csv); the trade rows are in the scratchpad (lifecycle/archive, 281 MB) and were not re-run for  | 0 promoted |
| 10 | ATM straddle samples and the independent short-premium prereg (branch compass-research-2026-10-14) | price samples only (no trade with an exit); the pre-registered study never ran. | No result |
| 11 | Price-action catalogue and atlas (43 names) | descriptive tables, no trades. | Descriptive; V6 tested its levels |
| 12 | Step 1: every 0DTE contract broken down | a contract inventory, no trades. | Descriptive. |
| 14 | Step 3: 108 exits × 9 conditions | committed as per-rule summaries (exits.csv, exits_best.csv); the per-trade paths are committed but the exit grid was not re-run here. | Nothing made money in a way that held up; a −50% stop shrank … |
| 16 | Step 5: the runner model (model A/B) and its top 1% picks | the picks are committed as daily sums (top1_daily.csv), not trades. | Runners partly separable |
| 18 | Compass engine audit (six module groups) | the audit committed row-level paths and events (paths_\*.parquet, events_\*.parquet) and per-cell tables; its exit stacks were scored by cell, and no single trade | No directional rule survives after fees. What holds |
| 22 | Phase 2 hyp D: volatility breakout (straddles on the model's top decile) | committed as cells by scan minute and decile (cells_\*.csv, minutes_\*.parquet); no trade list of the pre-registered cell. | No edge |
| 24 | Phase 3 hyp E: short-premium lift of the vol model's quiet deciles | committed as by-scan cells and pooled tables; the candidate was set after the OOS read (see #26 condor_d20 for its trades). | No edge established — not pre-registrable |
| 26d | Paper tracker: fly_spxw (SPX ±5 / ±25 flies) | a one-week sanity run outside the repository; no rows were kept. | Run only as a one-week sanity run outside the repository; replaced … |
| 29f | Picker: flow gate and grade check | one session of flow (5 trades) and the vendor's own recorded returns (see #1, vendor-recorded). | Flow gate |
| 30f | Compass features VN1 (venue SPY vs SPXW) and BC3 (V1 + X3 + D6) | VN1 pairs venues and BC3 needs the D6 direction feature; both are computed inside the study's screen code, and their per-trade arms are not on disk. | PASS |
| 36 | Edge H5 (SPY − SPXW late straddle) and H6 (monthly put spreads), forward only | forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has been counted | No verdict. |
| 38 | Edge H9: overnight drift (forward only, withdrawn) | forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has been counted | No verdict. |
| 39 | Compass scanner (score ≥ 80, SPY/QQQ/IWM 0DTE) | signal-only: the gate failed before any option was priced, so trades, win rate, average win/loss, biggest win/loss, profit factor, drawdown, top-5 share and by- | FAIL at the gate |
| 42 | George A+ entry + EMA targets | the run was stopped before its prereg was committed; no file exists on disk or in history, so every metric is not available. | Never run. |
| 44 | Compass EMA: the owner's three EMA / ORB models | the run was stopped before computing: a partial engine and a session list exist in the scratchpad (compass_ema_partial/), no signal, trade or P&L. | Never computed. |
| 45 | DR-GCE gates 1 and 2 (Mode 1 Gamma Vacuum Squeeze) | signal-only: touch outcomes (signals.csv, gate2_pairs.csv), never traded to an exit; no P&L metric exists. | Gate 1 PASS |
| 46 | Trend-day test | never run (the trend-day share is only described in step 6). | Never registered, never run. |

## The rules that passed, with their numbers

Seven rules passed a pre-registered holdout or single test. None of them makes a losing base set profitable, except H7,
which is a stock trade.

| rule | what it does | the test | result (Δ = with − without, points of the debit a trade; H7 = $ a trade) | forward N (committed) |
|---|---|---|---|---|
| **V1** spread veto | skip a base trade whose (ask − bid) ÷ mid > 10% at entry | Compass features Phase A holdout (a2e14e4, 2a49049) | Δ **+2.61 [+1.76, +3.46]**; −8.43% with vs −11.03% without | 23,960 sessions (out of reach) |
| **X3** 14:00 exit | sell a 0DTE long entered before 14:00 at the 14:00 bid | same | Δ **+7.78 [+4.14, +10.95]**; −9.51% vs −17.29% | 369 sessions |
| **VN1** venue | keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid | same (failed on the first, duplicated, read) | Δ **+1.18 [+0.50, +2.20]** | 587 |
| **BV1b** | V1 at 3% | Phase B holdout (b6737c7, e5dd8c6), not virgin | Δ **+4.30 [+2.66, +5.85]**; −6.73% vs −11.03% | 481 |
| **BX3e** | X3 on the physically settled names only | same | Δ **+7.67 [+4.23, +10.69]**; −11.03% vs −18.71% | 265 |
| **BC3** | V1 veto + X3 exit + D6 direction, against all base trades | same | Δ **+6.77 [+4.82, +8.19]**; −4.26% vs −11.03% | 341 |
| **H7** pre-FOMC drift | 100 shares from the close before a 2:00 pm FOMC statement to the 13:58 bar | single test (edca472, 6c94bb8) | SPY **+$70.43 [+14.64, +129.31]**, QQQ **+$69.59 [+23.10, +122.14]**; QQQ clears Bonferroni at m = 13 | 366 SPY / 483 QQQ trades (fcc1f4d) |

These rules are frozen as written:

- Compass's decision layer uses V1, X3 and VN1 exactly as frozen (`FORWARD_RULE.md` b101ae1, `PREREG_PICKER.md` §4
  fees).
- The daily forward job counts every rule here against its N. No verdict is read before a rule reaches its N.

Also positive on a single historical read, but not passed:

- S17's index put-writing passes its carry-lane rule (#7j). It is a carry with alpha 0, not an edge.
- H8 passes for QQQ at 1× only.
- Phase 3 hyp F (#25) passes its four-part rule on the OOS that chose it.


**The same rules at Robinhood fees (descriptive; the pre-registered results above stand).** The Compass features' Δ is re-run by the study's own `stats.delta` on the holdout with each trade re-priced; H7 is its single-test row.

| rule | Δ or mean at the study's fees | at Robinhood fees | 95% interval at Robinhood fees | the frozen pass rule at Robinhood fees |
|---|---|---|---|---|
| V1 | Δ +2.61 | Δ **+2.25** | [+1.41, +3.07] | passes |
| X3 | Δ +7.78 | Δ **+8.21** | [+4.53, +11.38] | passes |
| BV1b | Δ +4.30 | Δ **+3.46** | [+1.82, +4.95] | passes |
| BX3e | Δ +7.67 | Δ **+8.15** | [+4.68, +11.18] | passes |
| VN1, BC3 | not re-run: their per-trade arms are not on disk (and VN1's choice itself prices the fee) | | | |
| H7 QQQ | +69.59 $ | **+70.01 $** | [+18.16, +115.30] | passes (report interval, 1×) |
| H7 SPY | +70.43 $ | **+70.54 $** | [+11.25, +131.20] | passes (report interval, 1×) |

## The holdout ledger (the report's copy)

This is a copy of `research_notes/HOLDOUT_LEDGER.md` (9af93fc) with three rows added after it. The committed ledger is unchanged: nothing in it is wrong, it only predates DR-GCE.

**Holdout A** = index direction data 2017-06-01 → 2022-05-12. **Holdout B** = the 28 drawn months.

| study (commit) | data and span | rules read | A | B |
|---|---|---|---|---|
| S04 (`b037899`) | SPY/QQQ/IWM bars 2017-06-01 → 2026-10-09 | Quick Scalps signal, forward returns (+ ablations, not counted) | 1 | 1 |
| S06 (`4aba507`) | same | 7 triggers × 4 filter sets | 28 | 28 |
| S12 (`be991de`) | bars 2017-06 → 2026-10-09 | first-half-hour momentum, 3 windows | 3 | 3 |
| S12b (`be991de`) | 0DTE 2022-11-11 → 2026-10-09 | 2 option expressions | 0 | 2 |
| S16a | bars 2017-06 → 2026-10-09 | 108 cells ÷ 3 names | 36 | 36 |
| S03, S16b (`3c8d6cb`) | weekly chains, sample 2017-06 → 2026-10-09 | Quick Scalps weekly; prior-day fade 2 cells × 2 exits | 5 | 5 |
| H10 (registry) | SPY bars 2017 → 2026-10-09 | last-30-minute momentum | 1 | 1 |
| H17 (registry) | SPX 2017 → 2026 | 4 day filters | 4 | 4 |
| S17 | SPY/QQQ monthly chains 2012-06 → 2026-10 | 5 structures | 5 | 5 |
| Lifecycle daily tier (`50de62a`) | SPY/QQQ/IWM option EOD 2012-06 → 2026-10 | ≥ 19 walk-forward finalists | ≥ 19 | ≥ 19 |
| V6 / atlas (`0d706b6`, `1660366`) | 43 names incl. SPY/QQQ/IWM bars 2017-06 → 2026-10 | PDH/PDL, round numbers | 2 | 2 |
| V8 (registry) | SPXW 2017-06 → 2022-04, SPY 2017-06 → 2022-10 month-ends | month-end 13:00 straddle | 1 | 1 |
| Compass H1 (`4a02144`) | SPY 2017-01 → 2025-10-10, QQQ 2012-06 → | overnight reversal | 1 | 1 |
| Edge H4 (`dfa575d`) | SPY/QQQ 2012/2017 → 2026-10-22 (exploration context + test) | intraday momentum | 1 | 1 |
| Edge H7, H8 (`6c94bb8`) | SPY 2017 → 2026-09, QQQ 2012/2013 → | pre-FOMC drift; turn of month | 2 | 2 |
| Compass features (`a2e14e4`, `2a49049`, `e5dd8c6`) | ETFs 2012-06 →; SPXW/SPY/QQQ 0DTE 2022 → 2026-10-21; its own 43-month holdout read (twice) | 23 features screened | 23 | 23 |
| Compass scanner signal check (`142fcf4`, `9e3888e`) | SPY/QQQ/IWM bars, Pick 2017-07-05 → 2022-11-18 (its non-held-out months; the 28 never opened) | the scanner score (RSI/VWAP/RVOL/structure family) | 1 | 0 |
| S01, S02 (`5e90201`, `6bf5934`) | SPY/QQQ/IWM 0DTE 2022-11-11 → 2026-10-09 | Quick Scalps + 41 variants | 0 | 42 |
| S09, S10 (`7167541`, `3c8d6cb`) | SPXW 0DTE 2022-05 →; SPY/QQQ/IWM | QS on SPXW; QS fade (≥ 2 cells) | 0 | ≥ 3 |
| S15 (registry) | SPY/QQQ 0DTE 2022-11-11 → 2026-10-09 | 10:00 straddle, 3 conditions | 0 | 3 |
| H9, H11, H13, H15, H16 (registry) | SPY/QQQ/SPXW 0DTE 2022-05 / 2025-06 → 2026-10 | straddles/strangles; grids of 1,890 + 2,736 configs | 0 | ≥ 4,630 |
| Steps 1–5 (`2185eb9` → `491a0c7`) | every 0DTE contract 2022-05-13 → 2026-10-09 | buy/sell-and-hold, times, exits, turn-ups, volume (≥ 1 a step) | 0 | ≥ 5 |
| Lifecycle Tier I (`425c7f4`) | 0DTE SPY/QQQ/IWM/SPXW 2022-05 → 2026-10-09 | 12 setups × 8 structures × 116 policies | 0 | 11,136 |
| V5, V7 (registry) | same-day chains 2022-05/11 → | calibration; event afternoons | 0 | 2 |
| Engine audit, phase 2 (4), phase 3 (E, F), backtest audit, SPXW analogues (`2820bb4`) | 0DTE 2022 → 2026-10-09 | ≥ 1 each | 0 | ≥ 9 |
| Picker (`c502122`, `1e10053`) | SPY/QQQ/IWM/SPXW 0DTE 2022 → 2026-10-21 | opening-range fade + improved | 0 | 2 |
| EMA system v1 preview | bars of 60 sessions before each week (2025-11, 2026-04 bars as warm-up only, no outcome) | — | 0 | 0 |
| Compass EMA ladder (previews 2025-02/03) | not held out; holdout not read | — | 0 | 0 |
| Step 6 (`30babaa`, `44b5547`) | 0DTE 2022-05-13 → 2026-10-09, the 28 months never opened | 18 rules | 0 | 0 |
| Compass ICT (`9d6c37e`, `0943030`) | exploration only; holdouts never opened | — | 0 | 0 |
| Compass EMA (this study, prereg) | not yet read | — | 0 | 0 |
| Compass Close (`research_notes/Compass Close/PREREG_COMPASS_CLOSE.md`, row added with the prereg, before any fetch or computation) | SPXW same-day PM chains 15:45–16:00, SPX prints, Cboe SPX closes: 470 new sessions 2017-06-02 → 2022-05-12 (gate = odd months 236, P&L = even months 234; 15 of B's 28 months inside); previously read 2022-05-13 → 2026-10-09 reported, not judged | 1 judged rule (15:55 ATM straddle to settlement) + 8 reported entry/exit books (call, put, move side, narrower leg, 15:50, 15:58, 15:56 ask, one-strike-OTM strangle); fee and event-day lines not counted | 9 | 9 |
| Compass EMA (`9af93fc`) | prereg only; the run was stopped before computing | — | 0 | 0 |
| DR-GCE gates 1, 2 (`01d5c8e`, `041baba`, `b20eb9c`; `294d4f2`, `00eb3d5`) | SPXW 0DTE exploration 2023-12-01 → 2026-10-09, the 28 months never opened (guard selftest 5/5) | Mode 1 / Mode 2 touch gate; direction vs volatility | 0 | 0 |
| This final report (2026-10-23) | reads only spans already read; reruns #31 (exploration X only) and #40 (2025-02/03 only) | — | 0 | 0 |

**Running count with Compass Close's row (2026-10-24): holdout A ≥ 142 rules (≥ 133 before it); holdout B ≥ 15,975 rules (≥ 15,966 before it); Compass EMA's prereg has read nothing.**

**What has read each holdout, and what remains unopened**

| holdout | read by | unopened for |
|---|---|---|
| A (2017-06 → 2022-05-12) | ≥ 133 rules (S04, S06, S12, S16a, S03/S16b, H10, H17, S17, the daily tier, V6, V8, Compass H1, H4, H7/H8, Compass features, the scanner's signal check) | every rule from the scanner on: Compass ICT (#43), Compass EMA (#44), the EMA ladder (#40), DR-GCE (#45), step 6 (#17) |
| B (28 months) | ≥ 15,966 rules, before the holdout was defined (steps 1–5, S01/S02, S09/S10, S15, the short-premium grids, Tier I, V5/V7, the engine audit, phases 2–3, the picker) | the rules defined after it: #17, #39, #40, #43, #44, #45 ("unopened for this rule only") |
| Compass features' own (43 months + AVGO, MU, QQQ) | opened: Phase A twice (the first on duplicated rows), Phase B once | — |
| Compass direction: 1,600 names 2019-01 → 2022-12 | — | **unopened** (the screen failed) |
| Edge H3: 1,600 names | — | **unopened** (not fetched) |
| The scanner's held-out tickers AMD, AVGO | — | **unopened** |
| Lifecycle hold-out 2025-10-01 → 2026-10-09 | opened once per group (Tier I, L-A3, H-FLO, the daily tier, P1/P2) | — |
| V1–V8 hold-outs | each opened once | — |
| ThetaData lanes TEST (2025 → 2026-10) | read (T-A, T-B, T-C, T-E, H15) | — |
| Phase 2/3 OOS 2025-01 → 2026-10-09 | read once each; this is the tracker's and the SPXW test's "selection" period | — |
| Forward from 2026-10-12 | the paper tracker (9 sessions to 10-22) | features (0 sessions counted), H5 (none), H6 (from 2026-11-02), H7 (from 2026-10-28) |


## The data inventory

All market data is stored files. Nothing was fetched for this report.

| data | span | where |
|---|---|---|
| Same-day option chains, 1-minute NBBO (every contract) | SPY 989 sessions 2022-11-11 → 2026-10-22; QQQ 989, same span; IWM 629, 2024-04-19 → 2026-10-21; SPXW 1,115, 2022-05-13 → 2026-10-22 | scratchpad `theta/data_full/chains/` (forward sessions 2026-10-12 → 21 also committed in `data/theta_forward/`) |
| Underlying 1-minute bars | SPY 3,687 sessions 2012-06-01 → 2026-10-22; QQQ 3,619; IWM 3,618 | scratchpad `theta/data/underlying/` |
| SPX prints and VIX, 1-minute | SPX 2,362 sessions, VIX 2,395, 2017-06-01 → 2026-10-22 | scratchpad `theta/data/index/` |
| Official closes | Cboe's SPX history 1975 → 2026-10-21; UW daily bars | `data/official_closes/` |
| Option EOD and open interest, every contract | the account's bulk files 2026-10-06 → 12; index-ETF option EOD 2012-06 → 2026-10 | `data_lake/thetadata/flat/`, scratchpad `lifecycle/eod_by_exp` |
| Stock daily bars, every symbol | 2012-06 → 2026-10-13 (26,855 symbols listed) | `data_lake/thetadata/stock_eod/` |
| Unusual Whales per-ticker histories | daily bars, greek exposure, IV rank, realised volatility, VRP, earnings; about one year to 2026-10-13 | `data_lake/unusualwhales/` |
| Unusual Whales recorder (flow, dark pool, net-prem ticks, minute bars, OI by strike) | from 2026-10-21 | `data_recorder/` (git-ignored) |
| Post-market 1-minute bars (UW) | 16 name-sessions fetched once for the after-hours study, plus the backtest cache 2025-05 → 2026-10 | `data/postmarket_1m/`, scratchpad `bt/cache` |
| Macro calendar (FOMC, CPI, payrolls) | 2022 → 2027 | `data/macro_events_2022_2027.csv` |
| GeorgeFi evidence (cards, books, API captures) | 2026-01-20 → 2026-10-13 | `evidence/` at 7dfea57 |
| Trade-level outputs used here and not committed (kept in the scratchpad) | tracker `data_recorder/paper_backtest_official` (316 MB); step 6 population `step6/` (39 MB); features `features_work/{expl,hold}`; direction rerun `dir/work/expl_trades.parquet`; EMA ladder rerun `ema_ladder_out/` | as listed |


## Forward tracking

**The daily job.** `scripts/daily_forward.py` runs after each close, in this order, stopping at the first failure:

1. fetch the session's seven files: the Theta Terminal on the owner's machine, or one SDK login inside the owner's
   window;
2. verify them;
3. merge them;
4. read the official close: UW's daily bar, or Cboe for SPX;
5. read the post-market decision price;
6. replay the session through the live paper tracker (condor_em1, fly5, condor_d20), settled on the official close;
7. append it to `research_notes/Compass phase 3/forward_cumulative.md`;
8. run the Compass features forward test (V1, X3, VN1, BV1b, BX3e, BC3 under `FORWARD_RULE.md` b101ae1);
9. run the edge-search forward tests (H5, H6 and H7).

A session is appended only whole. No verdict is read before a model reaches its committed N. Interim figures are
logged without early stopping.

**Where it stands (2026-10-23).**

- **The paper tracker's period iii:** 9 sessions, 2026-10-12 → 22. Results in that window:
  - condor_em1: 44 trades, +$9.99 a trade.
  - fly5 iron: 36 trades, +$52.93.
  - condor_d20: 41 trades, +$23.38.

  This is an execution and data-quality record. The thresholds are 60 → 120 sessions for condor_em1, 150 for
  condor_d20's D1 re-test, and 250 a name for the flies.
- **The Compass features:** 0 forward sessions counted (from 2026-10-22).
- **H5:** forward from 2026-10-23.
- **H6:** from 2026-11-02.

**H7 live.** The pre-FOMC drift is wired into step 8 of the job (712b0ad). It trades 100 SPY / 100 QQQ from the official
close before each scheduled 2:00 pm statement to the 13:58 bar's close. It runs on the official closes and minute
bars the job already keeps, with the macro calendar and H7's dividend table. The first forward trade is the statement
of 2026-10-28. N is 366 trades for SPY and 483 for QQQ (`FORWARD_RULE_H7.md` fcc1f4d), about 46 and 60 years. The
verdict is read at N only.

**The H9 removal.** H9 (overnight drift) was registered forward-only (edca472) and wired in 712b0ad. The owner withdrew
it on 2026-10-23, and it was removed from the job (c68f389) before any H9 forward row was written. The registered rule
is unchanged.


## Method (every section)

- **Fills.** As each study ran them: ask in, bid out, at the 1-minute NBBO unless the section says otherwise. Older
  studies (#2, #4b, #5) used Unusual Whales bars with a modelled spread. Each section states its fee schedule.
- **Fees (from 2026-10-24).** Every trade is re-priced at Robinhood's fees: `pnl_rh = pnl + the study's fee − Robinhood's
  fee`, on the study's own fills (`scripts/fees_robinhood.py`, `docs/FEES_ROBINHOOD.md`).
  - The study's fee is taken from its own fee column when the file has one, and otherwise from its code's formula.
  - Robinhood's fee is figured from each leg's contracts, side and price.
  - A contract held to expiry or settlement pays no exit fee. Where a study charged a sale on a contract held in the money
    to the close (steps 2 and 4), Robinhood's fee is $0.
  - Where only the structure's total price is kept, a leg's price is taken as its share of that total. It is used only for
    the SEC fee's cent and SPXW's $1.00 tier. A row that needed any other guess is labelled "inferred".
  - Stock trades: the studies' $0.01 a share on an auction fill is their fee allowance, so it is replaced. Their $0.005 a
    share on a bar fill is half the spread, so it stays.
- **Win and loss.** A win is a trade whose P&L after fees is above zero. A breakeven counts as a loss.
- **Session span.** The calendar is every stored SPY minute-file session in the period's span. A session with no trade
  counts as zero.
- **Interval.** The interval is `audit_lib.session_stats` with blocks of 20 sessions (2,000 draws, its own seed), for the
  mean $ and the mean % a trade. A period under 60 sessions gets no interval. Some studies used other intervals, such
  as iid session or trade bootstraps, so the numbers here can differ from a study's own; the verdict is always the
  study's.
- **Drawdown.** Max drawdown is taken on the cumulative $ of session sums. The longest drawdown is the longest run of
  sessions spent below a previous peak.
- **Top-5 share.** This is the five best sessions' share of a positive total. Where the total is ≤ 0, the five best
  sessions' $ and the total without them are printed instead.
- **Random baselines.** Each is quoted from the study that computed it. For S10, S12, S12b and S16b, the mean of the study's own matched-control rows (seeds 11–15) is taken from the same trade file. None was re-simulated.
- **By year.** All periods together, grouped by entry year.
- **Charts.** Cumulative $ per name and pooled, with each period shaded and labelled.


# Part A. Studies before the fresh start (75c29c9), read from 7dfea57

## #1 GeorgeFi vendor cards (the vendor's own recorded P&L)

**Folder:** `evidence/public_api/, research/georgefi_full_history/normalized/ (@7dfea57)`. **Commits:** — / errata 5ed66df / cf555c9. **Dates:** 2026-10-13.

**Hypothesis.** GeorgeFi's published 0DTE and swing calls carry a positive return.

**Rule.** The vendor's own cards: ticker, contract, entry and exit premium, size and P&L as GeorgeFi recorded them (books v2.0.0-ict, trade_now_v1, singles_today_v1, spx_plan_v1).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** The vendor's recorded fills; no fee or spread applied by us.

**Data.** 1,149 closed cards, 2026-01-20 → 2026-10-13 (Epoch 1 2026-01-20 → 02-27; Epoch 2 from 2026-03-02).

**Periods and holdouts.** Epoch 1 / Epoch 2, descriptive. No holdout.

**Pass rule (as pre-registered).** None (descriptive). The grade check of the picker test (#29) reads the same cards.

**Verdict.** Not evidence: re-priced at the NBBO (#4) Epoch 1 falls from +$43,248 recorded to +$12,039 executable and Epoch 2 from −$3,757 to −$24,988 (G1).

> **Vendor-recorded, not re-marked.** Every figure below is the vendor's own recorded card P&L, as published; none was re-priced on market quotes.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| v2.0.0-ict 0DTE | Epoch 1 | 373 | 25 / 29 | 82.6 | +25.5, +161.46 | −23.6, −195.44 | +14.5, +39.00 | **+16.92**, +99.27 | n/a (< 60 sessions); n/a (< 60 sessions) |
| v2.0.0-ict SWING | Epoch 1 | 173 | 10 / 11 | 70.5 | +16.1, +95.18 | −3.6, −105.67 | +10.7, +29.00 | **+10.29**, +35.97 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | Epoch 1 | 546 | 28 / 29 | 78.8 | +22.8, +142.65 | −14.8, −155.97 | +13.0, +36.00 | **+14.82**, +79.21 | n/a (< 60 sessions); n/a (< 60 sessions) |
| singles_today_v1 0DTE | Epoch 2 | 29 | 6 / 7 | 20.7 | +43.3, +46.33 | −45.8, −61.30 | −50.0, −24.00 | **−27.35**, −39.03 | n/a (< 60 sessions); n/a (< 60 sessions) |
| singles_today_v1 SWING | Epoch 2 | 19 | 4 / 7 | 57.9 | +20.3, +40.18 | −16.2, −19.13 | +8.2, +4.00 | **+4.94**, +15.21 | n/a (< 60 sessions); n/a (< 60 sessions) |
| spx_plan_v1 0DTE | Epoch 2 | 11 | 7 / 7 | 54.5 | +97.4, +902.50 | −79.0, −480.00 | +54.1, +200.00 | **+17.23**, +274.09 | n/a (< 60 sessions); n/a (< 60 sessions) |
| trade_now_v1 0DTE | Epoch 2 | 55 | 35 / 69 | 25.5 | +90.5, +1,247.32 | −35.0, −667.44 | −13.9, −130.00 | **−3.06**, −180.05 | [−32.03, +25.54]; [−540.38, +201.06] |
| v2.0.0-ict 0DTE | Epoch 2 | 429 | 113 / 159 | 51.0 | +28.5, +129.99 | −19.3, −120.22 | +0.9, +3.00 | **+5.13**, +7.51 | [−0.81, +12.76]; [−17.29, +30.78] |
| v2.0.0-ict SWING | Epoch 2 | 60 | 28 / 121 | 56.7 | +25.9, +94.03 | −19.9, −94.02 | +6.1, +22.00 | **+6.06**, +12.54 | [−8.91, +14.87]; [−57.80, +24.30] |
| all names | Epoch 2 | 603 | 132 / 162 | 48.1 | +32.6, +190.56 | −24.2, −188.56 | +0.0, +0.00 | **+3.13**, −6.23 | [−0.74, +9.76]; [−62.87, +13.75] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| v2.0.0-ict 0DTE | Epoch 1 | +4,020.00, +1,057.9%, 2026-02-06, O:SPX260206C06930000 | −1,375.00, −78.6%, 2026-02-18, O:SPXW260218P06860000 | 3.91 | 310 | 1 | 60% |
| v2.0.0-ict SWING | Epoch 1 | +910.00, +59.6%, 2026-01-29, O:USAR260130P00023000 | −810.00, −21.4%, 2026-01-21, O:COIN260123P00230000 | 2.15 | 579 | 3 | 109% |
| all names | Epoch 1 | +4,020.00, +1,057.9%, 2026-02-06, O:SPX260206C06930000 | −1,375.00, −78.6%, 2026-02-18, O:SPXW260218P06860000 | 3.39 | 310 | 1 | 62% |
| singles_today_v1 0DTE | Epoch 2 | +104.00, +50.5%, 2026-10-07, O:MU261007C01085000 | −216.00, −63.5%, 2026-10-09, O:MU261009P01005000 | 0.20 | 1,132 | 7 | total ≤ 0 (best 5 days −671; without them −461) |
| singles_today_v1 SWING | Epoch 2 | +144.00, +38.9%, 2026-10-08, O:GOOGL261009P00347500 | −70.00, −53.8%, 2026-10-08, O:TQQQ261009C00084000 | 2.89 | 0 | 0 | 100% |
| spx_plan_v1 0DTE | Epoch 2 | +1,750.00, +140.0%, 2026-10-09, O:SPXW261009C07800000 | −935.00, −94.4%, 2026-10-06, O:SPXW261006P07815000 | 2.26 | 2,140 | 5 | 162% |
| trade_now_v1 0DTE | Epoch 2 | +3,312.50, +160.6%, 2026-07-13, O:SPXW260713P07505000 | −3,400.00, −60.7%, 2026-07-13, O:SPXW260713C07570000 | 0.64 | 15,740 | 67 | total ≤ 0 (best 5 days +8,318; without them −18,220) |
| v2.0.0-ict 0DTE | Epoch 2 | +2,055.00, +24.9%, 2026-03-04, O:SPXW260304C06815000 | −2,015.00, −24.7%, 2026-03-05, O:SPXW260305P06840000 | 1.13 | 4,066 | 63 | 227% |
| v2.0.0-ict SWING | Epoch 2 | +501.00, +68.1%, 2026-03-04, O:IWM260313P00261000 | −475.00, −19.2%, 2026-03-17, O:COIN260320C00210000 | 1.31 | 1,445 | 112 | 320% |
| all names | Epoch 2 | +3,312.50, +160.6%, 2026-07-13, O:SPXW260713P07505000 | −3,400.00, −60.7%, 2026-07-13, O:SPXW260713C07570000 | 0.94 | 14,299 | 101 | total ≤ 0 (best 5 days +13,434; without them −17,191) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $0.00 a trade) and Robinhood's charged instead (mean $0.00). The study's fees are given beside them below. Re-pricing: vendor-recorded: no fee in either column (1,149 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| v2.0.0-ict 0DTE | Epoch 1 | 373 | **+16.92**, +99.27 | +16.92, +99.27 | 82.6 / 82.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| v2.0.0-ict SWING | Epoch 1 | 173 | **+10.29**, +35.97 | +10.29, +35.97 | 70.5 / 70.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | Epoch 1 | 546 | **+14.82**, +79.21 | +14.82, +79.21 | 78.8 / 78.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| singles_today_v1 0DTE | Epoch 2 | 29 | **−27.35**, −39.03 | −27.35, −39.03 | 20.7 / 20.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| singles_today_v1 SWING | Epoch 2 | 19 | **+4.94**, +15.21 | +4.94, +15.21 | 57.9 / 57.9 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| spx_plan_v1 0DTE | Epoch 2 | 11 | **+17.23**, +274.09 | +17.23, +274.09 | 54.5 / 54.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| trade_now_v1 0DTE | Epoch 2 | 55 | **−3.06**, −180.05 | −3.06, −180.05 | 25.5 / 25.5 | [−32.03, +25.54] / [−32.03, +25.54] |
| v2.0.0-ict 0DTE | Epoch 2 | 429 | **+5.13**, +7.51 | +5.13, +7.51 | 51.0 / 51.0 | [−0.81, +12.76] / [−0.81, +12.76] |
| v2.0.0-ict SWING | Epoch 2 | 60 | **+6.06**, +12.54 | +6.06, +12.54 | 56.7 / 56.7 | [−8.91, +14.87] / [−8.91, +14.87] |
| all names | Epoch 2 | 603 | **+3.13**, −6.23 | +3.13, −6.23 | 48.1 / 48.1 | [−0.74, +9.76] / [−0.74, +9.76] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- Epoch 1: ICT: Take profit at MAJOR liquidity pool 6.8%; TIER A +10% (1/5) 4.8%; EOD AUTO-CLOSE (3:58 PM) 4.6%; ICT TIER 1 PROFIT +11% (PARTIAL) 3.7%; ICT TIER 1 PROFIT +12% (PARTIAL) 3.3%; ICT TIER 1 PROFIT +13% (PARTIAL) 2.9%; TIER A +10% (1/4) 2.9%; TIER A +10% (2/8) 2.6%
- Epoch 2: ICT: Take profit at MAJOR liquidity pool 5.6%; SINGLES_TODAY_TRAIL 4.3%; STOP LOSS (-12%) 4.1%; GEX EXIT: Accelerator reversed against B 3.8%; SINGLES_TODAY_STOP 2.3%; STOP LOSS (0%) 2.0%; GEX REGIME SHIFT: NEG→POS while losing ( 1.8%; SWING PROFIT_TARGET PARTIAL EXIT (25%):  1.8%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2026 | singles_today_v1 0DTE | 29 | 20.7 | −27.35 | −39.03 | −1,132 |
| 2026 | singles_today_v1 SWING | 19 | 57.9 | +4.94 | +15.21 | +289 |
| 2026 | spx_plan_v1 0DTE | 11 | 54.5 | +17.23 | +274.09 | +3,015 |
| 2026 | trade_now_v1 0DTE | 55 | 25.5 | −3.06 | −180.05 | −9,902 |
| 2026 | v2.0.0-ict 0DTE | 802 | 65.7 | +10.62 | +50.18 | +40,247 |
| 2026 | v2.0.0-ict SWING | 233 | 67.0 | +9.20 | +29.93 | +6,975 |
| 2026 | all names | 1,149 | 62.7 | +8.68 | +34.37 | +39,492 |

![](charts/s1.png)

**Amendments, deviations and integrity checks.** pnl_reported is used as recorded; 24 cards carry a data_error flag and are kept, as the vendor kept them.

**What it showed.** The vendor's record is positive in Epoch 1 and near zero in Epoch 2; the same rows re-priced at the market's quotes are a loss in Epoch 2 (#4).

## #2 George rebuild: the GeorgeFi-like reference (sweep / ict+gex / all / none / ladder)

**Folder:** `backtest/, BACKTEST_RESULTS.md (@7dfea57)`. **Commits:** — / — / 8f5b067. **Dates:** 2026-10-13.

**Hypothesis.** A level-sweep reversal into the nearest-strike 0DTE contract, managed by GeorgeFi's ladder, makes money after costs.

**Rule.** Levels PDH/PDL, PWH/PWL, PMH/PML, ORH/ORL and the prior-day call/put walls; a sweep within the last 3 bars closed back inside by max(0.25 ATR14, 0.02%) → buy the nearest-strike 0DTE call (low swept) or put (high swept) at the next bar's VWAP; ladder exit: stop −25%, T1 +25% half, T2 +45%, breakeven lock at +6%, trail at 65% of the high-water mark from +15%, 30-minute time stop, flat 15:55.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** The "spread" model: a half-spread of 1% (SPY, QQQ) or 2% (IWM) of premium each side plus $0.70 a contract each side; one contract. (Unusual Whales 1-minute bars, no NBBO.)

**Data.** SPY, QQQ, IWM 0DTE, 345 sessions 2025-06-02 → 2026-10-09 (SPX excluded: no index bars on the plan).

**Periods and holdouts.** In-sample < 2026-03-02, out-of-sample 2026-03-02 → 2026-10-09 (read). No holdout.

**Pass rule (as pre-registered).** None pre-registered (an exploratory grid of 144 variants).

**Verdict.** Rejected: 0 of 144 variants positive after costs (registry H1).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | in-sample 2025-06→2026-02 | 504 | 175 / 192 | 35.5 | +14.0, +8.71 | −16.1, −9.98 | −4.2, −2.30 | **−5.41**, −3.34 | [−7.13, −4.32]; [−4.70, −2.49] |
| QQQ | in-sample 2025-06→2026-02 | 526 | 165 / 192 | 35.0 | +15.5, +20.22 | −11.6, −15.06 | −2.1, −2.14 | **−2.11**, −2.72 | [−3.48, −1.45]; [−4.68, −1.43] |
| SPY | in-sample 2025-06→2026-02 | 550 | 172 / 192 | 37.6 | +14.9, +17.69 | −11.3, −13.33 | −2.1, −1.91 | **−1.44**, −1.65 | [−2.87, −0.20]; [−3.55, −0.06] |
| all names | in-sample 2025-06→2026-02 | 1,580 | 184 / 192 | 36.1 | +14.8, +15.69 | −13.0, −12.84 | −2.1, −2.10 | **−2.93**, −2.55 | [−3.86, −2.52]; [−3.66, −1.86] |
| IWM | out-of-sample 2026-03→10 | 483 | 143 / 160 | 42.0 | +13.3, +9.99 | −14.6, −9.91 | −4.1, −1.86 | **−2.89**, −1.55 | [−4.91, −1.54]; [−3.19, −0.58] |
| QQQ | out-of-sample 2026-03→10 | 461 | 142 / 160 | 36.9 | +14.5, +26.57 | −10.5, −17.33 | −2.1, −2.70 | **−1.29**, −1.14 | [−3.21, +0.23]; [−3.38, +1.18] |
| SPY | out-of-sample 2026-03→10 | 455 | 144 / 160 | 32.7 | +15.0, +21.32 | −11.4, −13.96 | −2.1, −2.40 | **−2.78**, −2.41 | [−3.73, −1.87]; [−3.44, −1.29] |
| all names | out-of-sample 2026-03→10 | 1,399 | 155 / 160 | 37.3 | +14.2, +18.62 | −12.1, −13.79 | −2.1, −2.38 | **−2.33**, −1.69 | [−3.41, −1.58]; [−2.53, −1.01] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | in-sample 2025-06→2026-02 | +29.27, +30.2%, 2026-01-14, IWM260114C00260000 | −61.66, −28.5%, 2025-09-17, IWM250917P00240000 | 0.48 | 1,735 | 188 | total ≤ 0 (best 5 days +198; without them −1,882) |
| QQQ | in-sample 2025-06→2026-02 | +102.07, +32.6%, 2025-11-20, QQQ251120P00600000 | −103.09, −26.8%, 2025-11-20, QQQ251120C00593000 | 0.72 | 1,658 | 177 | total ≤ 0 (best 5 days +460; without them −1,890) |
| SPY | in-sample 2025-06→2026-02 | +90.97, +32.6%, 2025-10-17, SPY251017C00658000 | −83.29, −26.8%, 2025-11-20, SPY251120C00660000 | 0.80 | 1,071 | 180 | total ≤ 0 (best 5 days +367; without them −1,275) |
| all names | in-sample 2025-06→2026-02 | +102.07, +32.6%, 2025-11-20, QQQ251120P00600000 | −103.09, −26.8%, 2025-11-20, QQQ251120C00593000 | 0.69 | 4,188 | 185 | total ≤ 0 (best 5 days +582; without them −4,604) |
| IWM | out-of-sample 2026-03→10 | +51.09, +30.2%, 2026-03-11, IWM260311C00251000 | −43.42, −28.6%, 2026-06-11, IWM260611P00289000 | 0.73 | 949 | 141 | total ≤ 0 (best 5 days +248; without them −994) |
| QQQ | out-of-sample 2026-03→10 | +142.56, +32.6%, 2026-06-26, QQQ260626C00705000 | −126.63, −26.8%, 2026-06-25, QQQ260625C00711000 | 0.90 | 675 | 137 | total ≤ 0 (best 5 days +699; without them −1,226) |
| SPY | out-of-sample 2026-03→10 | +105.99, +32.6%, 2026-06-25, SPY260625C00730000 | −79.81, −26.8%, 2026-04-02, SPY260402P00655000 | 0.74 | 1,135 | 160 | total ≤ 0 (best 5 days +326; without them −1,422) |
| all names | out-of-sample 2026-03→10 | +142.56, +32.6%, 2026-06-26, QQQ260626C00705000 | −126.63, −26.8%, 2026-06-25, QQQ260625C00711000 | 0.80 | 2,499 | 159 | total ≤ 0 (best 5 days +701; without them −3,071) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (2,979 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | in-sample 2025-06→2026-02 | 504 | **−5.41**, −3.34 | −8.06, −4.64 | 35.5 / 35.1 | [−7.13, −4.32] / [−9.87, −6.89] |
| QQQ | in-sample 2025-06→2026-02 | 526 | **−2.11**, −2.72 | −3.32, −4.02 | 35.0 / 35.0 | [−3.48, −1.45] / [−4.73, −2.65] |
| SPY | in-sample 2025-06→2026-02 | 550 | **−1.44**, −1.65 | −2.79, −2.95 | 37.6 / 37.6 | [−2.87, −0.20] / [−4.25, −1.51] |
| all names | in-sample 2025-06→2026-02 | 1,580 | **−2.93**, −2.55 | −4.65, −3.84 | 36.1 / 35.9 | [−3.86, −2.52] / [−5.64, −4.20] |
| IWM | out-of-sample 2026-03→10 | 483 | **−2.89**, −1.55 | −5.30, −2.84 | 42.0 / 41.6 | [−4.91, −1.54] / [−7.54, −3.82] |
| QQQ | out-of-sample 2026-03→10 | 461 | **−1.29**, −1.14 | −2.21, −2.44 | 36.9 / 36.9 | [−3.21, +0.23] / [−4.23, −0.59] |
| SPY | out-of-sample 2026-03→10 | 455 | **−2.78**, −2.41 | −3.94, −3.71 | 32.7 / 32.7 | [−3.73, −1.87] / [−4.92, −3.04] |
| all names | out-of-sample 2026-03→10 | 1,399 | **−2.33**, −1.69 | −3.84, −2.99 | 37.3 / 37.2 | [−3.41, −1.58] / [−5.02, −3.01] |

**Random baseline** (as the study computed it, at its own fees): random-time entries, same contract choice and ladder (9,896 trades): −$3.20 a trade [−3.70, −2.70] under the spread model; the reference is −$3.44 [−4.23, −2.70]. No percentile was computed.

**Exit reasons (share of trades):**

- in-sample 2025-06→2026-02: BREAKEVEN 36.8%; STOP 26.1%; TRAIL 22.0%; T1+TRAIL 9.9%; T1+T2 4.2%; TIME_STOP 0.9%
- out-of-sample 2026-03→10: BREAKEVEN 38.5%; STOP 23.7%; TRAIL 23.6%; T1+TRAIL 10.4%; T1+T2 3.4%; TIME_STOP 0.6%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | IWM | 399 | 34.3 | −5.98 | −3.69 | −1,470 |
| 2026 | IWM | 588 | 41.7 | −2.96 | −1.63 | −960 |
| 2025 | QQQ | 425 | 35.5 | −2.15 | −2.32 | −986 |
| 2026 | QQQ | 562 | 36.1 | −1.40 | −1.73 | −971 |
| 2025 | SPY | 444 | 38.3 | −0.91 | −0.92 | −411 |
| 2026 | SPY | 561 | 33.2 | −2.95 | −2.84 | −1,594 |
| 2025 | all names | 1,268 | 36.1 | −2.92 | −2.26 | −2,867 |
| 2026 | all names | 1,711 | 37.1 | −2.44 | −2.06 | −3,524 |

![](charts/s2.png)

**Amendments, deviations and integrity checks.** Reproduced byte for byte by the phase 1 audit (#3): trades.csv sha256 0e8c41c819e74eb0… on both runs.

**What it showed.** The reference variant loses $3.44 a trade, no better than random entry times with the same exits.

## #2b George rebuild: the best of 144 variants (sweep / ict+gex / morning / posgamma_fade / trail)

**Folder:** `backtest/ (@7dfea57)`. **Commits:** — / — / 8f5b067. **Dates:** 2026-10-13.

**Hypothesis.** The best-ranked of the 144 variants (selected in sample) holds out of sample.

**Rule.** As #2 but 10:00–12:00 only, sweep reversals only when spot is above the prior-day gamma flip, and the trail engine (no profit targets).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As #2 (spread model).

**Data.** As #2.

**Periods and holdouts.** As #2.

**Pass rule (as pre-registered).** None pre-registered.

**Verdict.** Rejected: −$2.41 a trade [−4.10, −0.47]; out of sample −$1.8 [−4.5, +0.9].

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | in-sample 2025-06→2026-02 | 134 | 91 / 187 | 29.9 | +14.8, +9.73 | −14.0, −9.82 | −4.1, −2.76 | **−5.40**, −3.99 | [−7.91, −3.08]; [−5.60, −2.45] |
| QQQ | in-sample 2025-06→2026-02 | 161 | 98 / 189 | 32.3 | +17.5, +27.01 | −11.3, −14.72 | −2.1, −2.34 | **−2.02**, −1.24 | [−5.84, +0.76]; [−5.87, +3.40] |
| SPY | in-sample 2025-06→2026-02 | 154 | 96 / 186 | 36.4 | +18.0, +25.10 | −11.4, −14.39 | −2.1, −2.16 | **−0.74**, −0.03 | [−2.96, +1.88]; [−3.60, +4.91] |
| all names | in-sample 2025-06→2026-02 | 449 | 145 / 191 | 33.0 | +17.0, +21.62 | −12.2, −13.08 | −2.1, −2.30 | **−2.59**, −1.64 | [−4.38, −1.28]; [−3.93, +0.49] |
| IWM | out-of-sample 2026-03→10 | 131 | 79 / 160 | 39.7 | +12.0, +10.55 | −15.6, −12.94 | −4.1, −2.62 | **−4.64**, −3.61 | [−6.97, −2.75]; [−5.32, −2.17] |
| QQQ | out-of-sample 2026-03→10 | 122 | 76 / 157 | 45.9 | +13.1, +29.78 | −9.5, −17.21 | −2.0, −2.77 | **+0.88**, +4.36 | [−1.20, +3.67]; [+0.16, +10.19] |
| SPY | out-of-sample 2026-03→10 | 132 | 76 / 160 | 35.6 | +14.9, +22.59 | −10.8, −15.36 | −2.1, −2.64 | **−1.66**, −1.85 | [−4.04, +0.28]; [−5.66, +1.05] |
| all names | out-of-sample 2026-03→10 | 385 | 116 / 160 | 40.3 | +13.3, +21.15 | −12.1, −15.06 | −2.1, −2.68 | **−1.87**, −0.48 | [−3.37, −0.33]; [−2.32, +1.51] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | in-sample 2025-06→2026-02 | +38.51, +55.0%, 2026-01-02, IWM260102P00248000 | −34.58, −28.6%, 2025-11-21, IWM251121P00231000 | 0.42 | 537 | 187 | total ≤ 0 (best 5 days +124; without them −658) |
| QQQ | in-sample 2025-06→2026-02 | +265.83, +84.9%, 2025-11-20, QQQ251120P00600000 | −87.57, −26.8%, 2025-11-21, QQQ251121C00588000 | 0.88 | 499 | 182 | total ≤ 0 (best 5 days +661; without them −861) |
| SPY | in-sample 2025-06→2026-02 | +200.88, +72.0%, 2025-10-17, SPY251017C00658000 | −81.96, −26.8%, 2025-11-21, SPY251121C00655000 | 1.00 | 247 | 84 | total ≤ 0 (best 5 days +481; without them −485) |
| all names | in-sample 2025-06→2026-02 | +265.83, +84.9%, 2025-11-20, QQQ251120P00600000 | −87.57, −26.8%, 2025-11-21, QQQ251121C00588000 | 0.81 | 938 | 181 | total ≤ 0 (best 5 days +804; without them −1,542) |
| IWM | out-of-sample 2026-03→10 | +47.29, +34.5%, 2026-03-25, IWM260325C00250000 | −42.28, −28.6%, 2026-06-25, IWM260625P00300000 | 0.54 | 521 | 140 | total ≤ 0 (best 5 days +146; without them −620) |
| QQQ | out-of-sample 2026-03→10 | +123.00, +30.1%, 2026-06-25, QQQ260625C00711000 | −102.02, −26.8%, 2026-06-29, QQQ260629C00712000 | 1.47 | 171 | 33 | 105% |
| SPY | out-of-sample 2026-03→10 | +78.04, +43.6%, 2026-04-06, SPY260406P00658000 | −79.81, −26.8%, 2026-04-02, SPY260402P00655000 | 0.81 | 393 | 99 | total ≤ 0 (best 5 days +255; without them −499) |
| all names | out-of-sample 2026-03→10 | +123.00, +30.1%, 2026-06-25, QQQ260625C00711000 | −102.02, −26.8%, 2026-06-29, QQQ260629C00712000 | 0.95 | 520 | 87 | total ≤ 0 (best 5 days +631; without them −816) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (834 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | in-sample 2025-06→2026-02 | 134 | **−5.40**, −3.99 | −7.51, −5.29 | 29.9 / 29.9 | [−7.91, −3.08] / [−10.05, −5.20] |
| QQQ | in-sample 2025-06→2026-02 | 161 | **−2.02**, −1.24 | −3.11, −2.54 | 32.3 / 32.3 | [−5.84, +0.76] / [−7.01, −0.26] |
| SPY | in-sample 2025-06→2026-02 | 154 | **−0.74**, −0.03 | −1.91, −1.33 | 36.4 / 36.4 | [−2.96, +1.88] / [−4.22, +0.67] |
| all names | in-sample 2025-06→2026-02 | 449 | **−2.59**, −1.64 | −4.01, −2.94 | 33.0 / 33.0 | [−4.38, −1.28] / [−5.87, −2.66] |
| IWM | out-of-sample 2026-03→10 | 131 | **−4.64**, −3.61 | −6.41, −4.91 | 39.7 / 39.7 | [−6.97, −2.75] / [−8.92, −4.38] |
| QQQ | out-of-sample 2026-03→10 | 122 | **+0.88**, +4.36 | +0.17, +3.06 | 45.9 / 45.9 | [−1.20, +3.67] / [−1.94, +2.98] |
| SPY | out-of-sample 2026-03→10 | 132 | **−1.66**, −1.85 | −2.65, −3.15 | 35.6 / 35.6 | [−4.04, +0.28] / [−5.03, −0.65] |
| all names | out-of-sample 2026-03→10 | 385 | **−1.87**, −0.48 | −3.04, −1.78 | 40.3 / 40.3 | [−3.37, −0.33] / [−4.57, −1.42] |

**Random baseline** (as the study computed it, at its own fees): random-time baseline −$3.20 a trade (as #2); the best variant beats it by about $0.8, inside its interval.

**Exit reasons (share of trades):**

- in-sample 2025-06→2026-02: BREAKEVEN 40.5%; TRAIL 33.0%; STOP 25.4%; TIME_STOP 1.1%
- out-of-sample 2026-03→10: TRAIL 40.3%; BREAKEVEN 36.9%; STOP 22.3%; TIME_STOP 0.5%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | IWM | 98 | 30.6 | −6.17 | −4.54 | −445 |
| 2026 | IWM | 167 | 37.1 | −4.35 | −3.37 | −563 |
| 2025 | QQQ | 136 | 30.9 | −1.73 | −0.56 | −76 |
| 2026 | QQQ | 147 | 44.9 | +0.13 | +2.77 | +408 |
| 2025 | SPY | 124 | 37.1 | −0.18 | +1.33 | +165 |
| 2026 | SPY | 162 | 35.2 | −1.91 | −2.55 | −414 |
| 2025 | all names | 358 | 33.0 | −2.41 | −0.99 | −355 |
| 2026 | all names | 476 | 38.9 | −2.14 | −1.19 | −569 |

![](charts/s2b.png)

**Amendments, deviations and integrity checks.** Selected as the best of 144 on the full sample (a selection effect the numbers include).

**What it showed.** Even the best of 144 variants loses after costs.

## #3 George engine audit: the phase 1 reproduction audit of #1–#2

**Folder:** `audit/phase1/ (@7dfea57)`. **Commits:** — / — / 5ed66df (+ e95177c deterministic T5 rerun). **Dates:** 2026-10-13.

**Hypothesis.** The rebuild (#2) and the GeorgeFi validation tests T1–T7 reproduce from their artifacts.

**Rule.** Rerun of backtest/run.py and the validation scripts; byte comparison of outputs.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** As #2.

**Periods and holdouts.** —

**Pass rule (as pre-registered).** Reproduction (no trading rule).

**Verdict.** Reproduced: the regenerated trades and baseline files are byte-identical once decompressed.

**Metrics.** not available — the audit produced no trades of its own; its trade files are #2's, byte for byte (see #2).

**Amendments, deviations and integrity checks.** Fixes the audit motivated were added, never overwritten (trading-days path, signals.json, deterministic T5 iteration).

**What it showed.** The rebuild is deterministic and reproducible; no new strategy was tested.

## #4 GeorgeFi's own trades re-priced at the NBBO (G1)

**Folder:** `research/georgefi_full_history/results/F_nbbo_\*.csv (@7dfea57)`. **Commits:** — / — / c27ff28. **Dates:** 2026-10-13.

**Hypothesis.** The vendor's recorded trades were executable at the prices it recorded.

**Rule.** Each card's own entry and exit second, filled at ThetaData's NBBO (ask in, bid out), the card's own size.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** NBBO at the reported second; no fee added.

**Data.** 1,220 cards with both sides quoted, 2026-01-20 → 2026-10-13, every root the vendor traded.

**Periods and holdouts.** ledger Epoch 1, ledger Epoch 2, paper book. Descriptive.

**Pass rule (as pre-registered).** None (an execution check).

**Verdict.** Not supported after execution: Epoch 1 +$22.2 a trade [day CI −11.2, +66.2], Epoch 2 −$42.1 [−78.8, −9.6], paper −$73.9 (registry G1); 58% of Epoch 1 rows filled better than the market.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| all roots | ledger E1 | 492 | 27 / 29 | 64.8 | +15.7, +119.56 | −22.4, −142.93 | +7.0, +22.40 | **+2.27**, +27.26 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all roots | ledger E2 | 594 | 132 / 162 | 45.8 | +26.5, +154.61 | −26.1, −207.32 | −2.2, −6.25 | **−2.02**, −41.59 | [−5.93, +2.73]; [−122.29, −7.59] |
| all roots | paper book | 84 | 38 / 61 | 36.9 | +35.9, +131.73 | −32.0, −196.34 | −26.6, −79.43 | **−6.94**, −75.27 | [−13.24, −0.81]; [−97.75, −56.42] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| all roots | ledger E1 | +1,981.92, +38.1%, 2026-02-20, SPXW PUT y3bxx2s50sc0nh8 | −1,677.02, −89.4%, 2026-02-18, SPXW PUT 2k5f36h32m9rqf7 | 1.54 | 4,914 | 12 | 109% |
| all roots | ledger E2 | +3,017.74, +391.9%, 2026-09-21, SPXW CALL dni7it4jw9zjisg | −3,476.17, −62.1%, 2026-07-13, SPXW CALL vkmuy6n1j94hoee | 0.63 | 31,395 | 159 | total ≤ 0 (best 5 days +10,361; without them −35,063) |
| all roots | paper book | +597.74, +89.2%, 2026-10-01, SPXW PUT 4oduouxg1tp6xd2 | −464.52, −36.3%, 2026-08-06, SPXW PUT qoxj9ry0ux3n0cz | 0.39 | 6,770 | 61 | total ≤ 0 (best 5 days +1,521; without them −7,843) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $3.63 a trade) and Robinhood's charged instead (mean $2.31). The study's fees are given beside them below. Re-pricing: exact (1,170 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| all roots | ledger E1 | 492 | **+2.27**, +27.26 | +1.55, +24.46 | 64.8 / 64.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all roots | ledger E2 | 594 | **−2.02**, −41.59 | −2.54, −42.07 | 45.8 / 45.1 | [−5.93, +2.73] / [−6.22, +2.54] |
| all roots | paper book | 84 | **−6.94**, −75.27 | −6.58, −73.92 | 36.9 / 36.9 | [−13.24, −0.81] / [−12.81, −0.49] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- ledger E1: vendor exit time, filled at the NBBO 100.0%
- ledger E2: vendor exit time, filled at the NBBO 100.0%
- paper book: vendor exit time, filled at the NBBO 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2026 | all roots | 1,170 | 53.2 | −0.57 | −15.05 | −17,614 |

![](charts/s4.png)

**Amendments, deviations and integrity checks.** Cards with a side unquoted, and the stock rows, are left out (as F_nbbo_trades.csv flags them).

**What it showed.** At the market's own quotes the vendor's live epoch loses $42 a trade.

## #4b GeorgeFi entries with the trail engine (reconstruction C, G2)

**Folder:** `research/georgefi_full_history/results/C_trades.csv (@7dfea57)`. **Commits:** — / — / 5ed66df. **Dates:** 2026-10-13.

**Hypothesis.** GeorgeFi's entry minutes carry timing information when managed by a fixed trail engine.

**Rule.** The vendor's entry minute, the reconstructed contract, entry at the bar VWAP, the paper-lane trail engine.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Spread model of #2 (half-spread + $0.70 a side).

**Data.** 972 reconstructed trades, 2026-01 → 2026-10.

**Periods and holdouts.** ledger Epoch 1 / Epoch 2 / paper.

**Pass rule (as pre-registered).** None (descriptive).

**Verdict.** No robust entry timing: Epoch 1 +$5.8 a contract [−5.7, +16.3], Epoch 2 +$2.3 [−10.5, +14.9]; MFE percentile against time-matched random minutes 53 and 48 (G2).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| AAPL | ledger E1 | 1 | 1 / 1 | 100.0 | +18.8, +4.00 | —, — | +18.8, +4.00 | **+18.81**, +4.00 | n/a (< 60 sessions); n/a (< 60 sessions) |
| COIN | ledger E1 | 5 | 2 / 6 | 40.0 | +27.0, +12.99 | −21.7, −38.47 | −12.6, −13.00 | **−2.18**, −17.88 | n/a (< 60 sessions); n/a (< 60 sessions) |
| CRCL | ledger E1 | 12 | 1 / 1 | 0.0 | —, — | −27.2, −46.27 | −27.2, −46.27 | **−27.18**, −46.27 | n/a (< 60 sessions); n/a (< 60 sessions) |
| CRM | ledger E1 | 1 | 1 / 1 | 100.0 | +69.0, +54.79 | —, — | +69.0, +54.79 | **+69.05**, +54.79 | n/a (< 60 sessions); n/a (< 60 sessions) |
| CRML | ledger E1 | 14 | 1 / 1 | 85.7 | +26.0, +2.89 | −21.3, −8.47 | +26.7, +2.92 | **+19.22**, +1.27 | n/a (< 60 sessions); n/a (< 60 sessions) |
| CVNA | ledger E1 | 1 | 1 / 1 | 0.0 | —, — | −27.1, −199.24 | −27.1, −199.24 | **−27.06**, −199.24 | n/a (< 60 sessions); n/a (< 60 sessions) |
| GOOGL | ledger E1 | 3 | 1 / 1 | 0.0 | —, — | −25.1, −19.46 | −26.3, −20.34 | **−25.13**, −19.46 | n/a (< 60 sessions); n/a (< 60 sessions) |
| HOOD | ledger E1 | 3 | 1 / 1 | 66.7 | +17.1, +9.94 | −25.3, −38.22 | +13.7, +7.97 | **+2.95**, −6.11 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IWM | ledger E1 | 65 | 15 / 28 | 67.7 | +27.2, +56.65 | −7.5, −13.78 | +7.8, +14.67 | **+16.02**, +33.90 | n/a (< 60 sessions); n/a (< 60 sessions) |
| NVDA | ledger E1 | 14 | 2 / 3 | 57.1 | +30.6, +26.57 | −2.7, −3.74 | +30.2, +26.24 | **+16.32**, +13.58 | n/a (< 60 sessions); n/a (< 60 sessions) |
| OKLO | ledger E1 | 1 | 1 / 1 | 0.0 | —, — | −24.3, −44.15 | −24.3, −44.15 | **−24.33**, −44.15 | n/a (< 60 sessions); n/a (< 60 sessions) |
| QQQ | ledger E1 | 63 | 11 / 29 | 46.0 | +11.7, +20.87 | −6.5, −16.66 | −0.6, −1.29 | **+1.87**, +0.62 | n/a (< 60 sessions); n/a (< 60 sessions) |
| RDDT | ledger E1 | 2 | 1 / 1 | 50.0 | +60.0, +90.25 | −25.1, −34.23 | +17.5, +28.01 | **+17.46**, +28.01 | n/a (< 60 sessions); n/a (< 60 sessions) |
| RKLB | ledger E1 | 28 | 2 / 6 | 64.3 | +24.3, +20.12 | −3.2, −5.62 | +7.1, +9.62 | **+14.46**, +10.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| RUTW | ledger E1 | 8 | 1 / 1 | 87.5 | +8.2, +21.72 | −3.2, −8.53 | +8.2, +20.89 | **+6.79**, +17.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SLV | ledger E1 | 3 | 1 / 1 | 0.0 | —, — | −3.2, −5.66 | −3.2, −5.66 | **−3.19**, −5.66 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPXW | ledger E1 | 59 | 11 / 25 | 54.2 | +10.7, +142.36 | −20.5, −150.77 | +5.7, +5.62 | **−3.57**, +8.22 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY | ledger E1 | 89 | 16 / 24 | 48.3 | +13.9, +33.04 | −7.3, −21.51 | −0.3, −0.68 | **+2.94**, +4.85 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | ledger E1 | 372 | 25 / 29 | 53.8 | +18.8, +50.15 | −11.3, −41.17 | +4.5, +2.92 | **+4.91**, +7.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| AAPL | ledger E2 | 2 | 2 / 8 | 50.0 | +14.5, +10.84 | −2.9, −3.74 | +5.8, +3.55 | **+5.82**, +3.55 | n/a (< 60 sessions); n/a (< 60 sessions) |
| AMD | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −26.0, −34.41 | −26.0, −34.41 | **−25.96**, −34.41 | n/a (< 60 sessions); n/a (< 60 sessions) |
| AMZN | ledger E2 | 6 | 5 / 42 | 16.7 | +22.0, +13.75 | −6.8, −8.26 | −2.1, −3.60 | **−1.96**, −4.59 | n/a (< 60 sessions); n/a (< 60 sessions) |
| AVGO | ledger E2 | 5 | 5 / 152 | 40.0 | +9.7, +17.95 | −16.0, −12.03 | −1.0, −0.90 | **−5.70**, −0.04 | [−9.07, +7.77]; [−5.92, +23.51] |
| BAC | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −11.8, −1.92 | −11.8, −1.92 | **−11.81**, −1.92 | n/a (< 60 sessions); n/a (< 60 sessions) |
| COIN | ledger E2 | 1 | 1 / 1 | 100.0 | +8.4, +22.90 | —, — | +8.4, +22.90 | **+8.39**, +22.90 | n/a (< 60 sessions); n/a (< 60 sessions) |
| GLD | ledger E2 | 17 | 12 / 150 | 52.9 | +137.9, +33.76 | −10.1, −20.59 | +0.6, +0.34 | **+68.24**, +8.19 | [+0.00, +61.34]; [+0.00, +38.22] |
| GOOGL | ledger E2 | 10 | 8 / 142 | 30.0 | +11.6, +10.83 | −8.9, −11.33 | −1.7, −3.15 | **−2.75**, −4.69 | [−5.01, +10.11]; [−9.41, +10.23] |
| HOOD | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −20.6, −7.33 | −20.6, −7.33 | **−20.59**, −7.33 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IBIT | ledger E2 | 2 | 2 / 6 | 0.0 | —, — | −3.8, −2.11 | −3.8, −2.11 | **−3.83**, −2.11 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IWM | ledger E2 | 19 | 10 / 68 | 36.8 | +14.1, +31.50 | −12.6, −28.07 | −1.9, −2.58 | **−2.76**, −6.13 | [−6.46, +17.44]; [−13.95, +30.20] |
| META | ledger E2 | 17 | 6 / 39 | 35.3 | +7.3, +15.81 | −9.5, −22.69 | −3.6, −15.82 | **−3.59**, −9.10 | n/a (< 60 sessions); n/a (< 60 sessions) |
| MSFT | ledger E2 | 1 | 1 / 1 | 100.0 | +9.8, +38.68 | —, — | +9.8, +38.68 | **+9.84**, +38.68 | n/a (< 60 sessions); n/a (< 60 sessions) |
| MU | ledger E2 | 4 | 2 / 3 | 50.0 | +17.8, +32.27 | −14.4, −21.65 | +4.0, +12.60 | **+1.66**, +5.31 | n/a (< 60 sessions); n/a (< 60 sessions) |
| NDXP | ledger E2 | 16 | 14 / 44 | 56.2 | +48.8, +444.39 | −24.3, −231.98 | +15.7, +97.07 | **+16.86**, +148.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| QQQ | ledger E2 | 103 | 56 / 158 | 42.7 | +14.6, +26.25 | −12.4, −23.33 | −0.7, −1.42 | **−0.89**, −2.15 | [−4.59, +4.08]; [−9.10, +7.45] |
| RUTW | ledger E2 | 23 | 17 / 77 | 56.5 | +25.2, +156.97 | −15.1, −91.73 | +9.1, +53.40 | **+7.66**, +48.84 | [−1.21, +14.07]; [+5.82, +67.78] |
| SLV | ledger E2 | 3 | 3 / 29 | 100.0 | +14.9, +5.38 | —, — | +14.4, +5.03 | **+14.88**, +5.38 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SMCI | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −24.0, −16.17 | −24.0, −16.17 | **−24.05**, −16.17 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SMH | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −2.2, −3.18 | −2.2, −3.18 | **−2.15**, −3.18 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPXW | ledger E2 | 206 | 90 / 160 | 38.3 | +19.4, +128.84 | −15.0, −90.17 | −3.1, −16.18 | **−1.80**, −6.18 | [−6.28, +2.53]; [−26.24, +7.53] |
| SPY | ledger E2 | 65 | 31 / 158 | 30.8 | +11.0, +21.89 | −9.2, −23.19 | −1.4, −3.06 | **−2.98**, −9.32 | [−4.45, −1.04]; [−12.14, −2.43] |
| TSLA | ledger E2 | 8 | 6 / 126 | 62.5 | +8.3, +8.99 | −2.7, −8.01 | +7.4, +3.99 | **+4.19**, +2.61 | [−2.97, +4.16]; [−9.47, +5.02] |
| UBER | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −18.4, −5.05 | −18.4, −5.05 | **−18.40**, −5.05 | n/a (< 60 sessions); n/a (< 60 sessions) |
| UCO | ledger E2 | 1 | 1 / 1 | 0.0 | —, — | −26.2, −19.20 | −26.2, −19.20 | **−26.17**, −19.20 | n/a (< 60 sessions); n/a (< 60 sessions) |
| USO | ledger E2 | 1 | 1 / 1 | 100.0 | +28.4, +40.60 | —, — | +28.4, +40.60 | **+28.43**, +40.60 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | ledger E2 | 516 | 131 / 162 | 40.1 | +23.2, +90.58 | −13.0, −56.58 | −1.5, −3.47 | **+1.50**, +2.46 | [−2.81, +3.24]; [−9.27, +19.34] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| AAPL | ledger E1 | +4.00, +18.8%, 2026-02-06, AAPL PUT 955xs5861je0sz7 | +4.00, +18.8%, 2026-02-06, AAPL PUT 955xs5861je0sz7 | ∞ | 0 | 0 | 100% |
| COIN | ledger E1 | +19.57, +40.7%, 2026-01-23, COIN PUT j55nf3xhhgeu4hi | −74.94, −25.7%, 2026-01-30, COIN PUT 09x52w4963s144b | 0.23 | 89 | 6 | total ≤ 0 (best 5 days −89; without them +0) |
| CRCL | ledger E1 | −46.27, −27.2%, 2026-01-30, CRCL PUT 0g311hmh7608g99 | −46.27, −27.2%, 2026-01-30, CRCL PUT 0g311hmh7608g99 | 0.00 | 555 | 1 | total ≤ 0 (best 5 days −555; without them +0) |
| CRM | ledger E1 | +54.79, +69.0%, 2026-01-30, CRM PUT 78506oa5o61r701 | +54.79, +69.0%, 2026-01-30, CRM PUT 78506oa5o61r701 | ∞ | 0 | 0 | 100% |
| CRML | ledger E1 | +2.92, +26.7%, 2026-01-30, CRML PUT 163cd9t5w354tz2 | −9.79, −24.7%, 2026-01-30, CRML PUT r2r64k78k862056 | 2.05 | 0 | 0 | 100% |
| CVNA | ledger E1 | −199.24, −27.1%, 2026-01-30, CVNA PUT 3gris210t7m2b5w | −199.24, −27.1%, 2026-01-30, CVNA PUT 3gris210t7m2b5w | 0.00 | 199 | 1 | total ≤ 0 (best 5 days −199; without them +0) |
| GOOGL | ledger E1 | −17.70, −22.9%, 2026-01-30, GOOGL PUT 3afgh5f7vn4ui47 | −20.34, −26.3%, 2026-01-30, GOOGL PUT 95s51zbt917v348 | 0.00 | 58 | 1 | total ≤ 0 (best 5 days −58; without them +0) |
| HOOD | ledger E1 | +11.92, +20.5%, 2026-01-30, HOOD PUT 5oox1vaao67k69q | −38.22, −25.3%, 2026-01-30, HOOD PUT 774ne079d7stl33 | 0.52 | 18 | 1 | total ≤ 0 (best 5 days −18; without them +0) |
| IWM | ledger E1 | +371.94, +164.1%, 2026-02-12, IWM PUT 9wo3d839ljqsl5l | −76.13, −26.6%, 2026-02-13, IWM PUT 960e22lsdv24ai6 | 8.61 | 164 | 11 | 105% |
| NVDA | ledger E1 | +27.56, +31.7%, 2026-02-06, NVDA CALL u87y983118239z4 | −4.18, −3.0%, 2026-02-04, NVDA PUT 1848jkd063c3950 | 9.47 | 22 | 2 | 100% |
| OKLO | ledger E1 | −44.15, −24.3%, 2026-01-30, OKLO PUT 9xy7jas7kw9524i | −44.15, −24.3%, 2026-01-30, OKLO PUT 9xy7jas7kw9524i | 0.00 | 44 | 1 | total ≤ 0 (best 5 days −44; without them +0) |
| QQQ | ledger E1 | +47.56, +21.4%, 2026-02-20, QQQ CALL x3tcpw8hmqi8w86 | −119.17, −25.9%, 2026-02-18, QQQ CALL 402z467697wj3ie | 1.07 | 366 | 22 | 1238% |
| RDDT | ledger E1 | +90.25, +60.0%, 2026-01-30, RDDT PUT 5725tnis6i49604 | −34.23, −25.1%, 2026-01-30, RDDT PUT 485pwz3e339pbdj | 2.64 | 0 | 0 | 100% |
| RKLB | ledger E1 | +33.88, +38.5%, 2026-01-30, RKLB PUT 0gi7xw49q6uthdz | −5.62, −3.2%, 2026-01-30, RKLB PUT 02rl903c51x3m7l | 6.44 | 0 | 0 | 100% |
| RUTW | ledger E1 | +26.77, +8.2%, 2026-01-27, RUTW CALL 1891h5gtbs11ue7 | −8.53, −3.2%, 2026-01-27, RUTW CALL 592b74h07fy9i2j | 17.82 | 0 | 0 | 100% |
| SLV | ledger E1 | −5.66, −3.2%, 2026-02-06, SLV PUT ar9594rv59q1lpa | −5.66, −3.2%, 2026-02-06, SLV PUT ar9594rv59q1lpa | 0.00 | 17 | 1 | total ≤ 0 (best 5 days −17; without them +0) |
| SPXW | ledger E1 | +639.34, +21.7%, 2026-02-17, SPXW PUT 0vsr61tk6e355f0 | −855.63, −27.3%, 2026-02-19, SPXW PUT u3a2f8rxkb60t4x | 1.12 | 811 | 7 | 396% |
| SPY | ledger E1 | +162.30, +65.4%, 2026-02-24, SPY CALL 894j813el751a5q | −124.06, −17.0%, 2026-02-10, SPY CALL 9zf937w5328f71i | 1.44 | 361 | 13 | 212% |
| all names | ledger E1 | +639.34, +21.7%, 2026-02-17, SPXW PUT 0vsr61tk6e355f0 | −855.63, −27.3%, 2026-02-19, SPXW PUT u3a2f8rxkb60t4x | 1.42 | 765 | 7 | 127% |
| AAPL | ledger E2 | +10.84, +14.5%, 2026-03-18, AAPL PUT yco9879mvrod1qa | −3.74, −2.9%, 2026-03-27, AAPL PUT lf35l8q98xq5m4i | 2.90 | 4 | 1 | 100% |
| AMD | ledger E2 | −34.41, −26.0%, 2026-10-09, AMD PUT i3b03ewpkryh99v | −34.41, −26.0%, 2026-10-09, AMD PUT i3b03ewpkryh99v | 0.00 | 34 | 1 | total ≤ 0 (best 5 days −34; without them +0) |
| AMZN | ledger E2 | +13.75, +22.0%, 2026-09-23, AMZN PUT t5exm42pv39sbea | −27.28, −25.5%, 2026-08-17, AMZN PUT 9jcbom24ks2h5nl | 0.33 | 35 | 42 | total ≤ 0 (best 5 days −28; without them −0) |
| AVGO | ledger E2 | +23.51, +7.8%, 2026-03-13, AVGO PUT rvd99u8867d6qku | −26.43, −25.4%, 2026-10-12, AVGO PUT ekylizkrfb48uzw | 0.99 | 35 | 2 | total ≤ 0 (best 5 days −0; without them +0) |
| BAC | ledger E2 | −1.92, −11.8%, 2026-10-09, BAC CALL x0z4k4fwb8gos4x | −1.92, −11.8%, 2026-10-09, BAC CALL x0z4k4fwb8gos4x | 0.00 | 2 | 1 | total ≤ 0 (best 5 days −2; without them +0) |
| COIN | ledger E2 | +22.90, +8.4%, 2026-10-09, COIN CALL 9oyzh2v0xe3d9bs | +22.90, +8.4%, 2026-10-09, COIN CALL 9oyzh2v0xe3d9bs | ∞ | 0 | 0 | 100% |
| GLD | ledger E2 | +142.92, +93.7%, 2026-09-14, GLD CALL kw39iz49kt101o8 | −74.71, −26.5%, 2026-03-18, GLD CALL 4hc062it0yxcvu4 | 1.85 | 75 | 128 | 198% |
| GOOGL | ledger E2 | +25.80, +22.9%, 2026-08-21, GOOGL CALL xk0nrxpvlxtv0rk | −41.71, −27.1%, 2026-03-27, GOOGL PUT i83o4578nx3v13m | 0.41 | 47 | 142 | total ≤ 0 (best 5 days +14; without them −61) |
| HOOD | ledger E2 | −7.33, −20.6%, 2026-10-09, HOOD CALL 5dewoq9m3lm21bz | −7.33, −20.6%, 2026-10-09, HOOD CALL 5dewoq9m3lm21bz | 0.00 | 7 | 1 | total ≤ 0 (best 5 days −7; without them +0) |
| IBIT | ledger E2 | −1.06, −1.1%, 2026-10-05, IBIT PUT mz572iaej6prqxd | −3.16, −6.5%, 2026-10-12, IBIT PUT ens8uikr9j4xd0u | 0.00 | 4 | 6 | total ≤ 0 (best 5 days −4; without them +0) |
| IWM | ledger E2 | +82.22, +27.4%, 2026-03-19, IWM CALL 1794163he39p5c3 | −77.73, −27.0%, 2026-03-09, IWM CALL 9417g6bc21he872 | 0.65 | 213 | 67 | total ≤ 0 (best 5 days +129; without them −245) |
| META | ledger E2 | +20.17, +10.9%, 2026-09-04, META CALL kmr87mdhotjnbzb | −65.76, −26.9%, 2026-09-16, META CALL u8myue00egjv6ch | 0.38 | 157 | 39 | total ≤ 0 (best 5 days +2; without them −157) |
| MSFT | ledger E2 | +38.68, +9.8%, 2026-03-27, MSFT PUT 8o6nv14p53b063h | +38.68, +9.8%, 2026-03-27, MSFT PUT 8o6nv14p53b063h | ∞ | 0 | 0 | 100% |
| MU | ledger E2 | +32.72, +24.7%, 2026-10-07, MU CALL m88pqldq0ixb2wd | −36.69, −26.1%, 2026-10-09, MU PUT cmzm0ywaiod9jxm | 1.49 | 37 | 1 | 100% |
| NDXP | ledger E2 | +1,752.21, +122.3%, 2026-07-06, NDXP PUT fugmhxmitbyc9jl | −590.99, −27.3%, 2026-06-12, NDXP PUT 744n57ni3vvbc5v | 2.46 | 790 | 23 | 142% |
| QQQ | ledger E2 | +151.46, +105.1%, 2026-05-11, QQQ PUT n65jjs8fech846i | −99.61, −26.1%, 2026-07-10, QQQ CALL g8rhxc7ftrxf8ox | 0.84 | 655 | 154 | total ≤ 0 (best 5 days +558; without them −779) |
| RUTW | ledger E2 | +355.71, +39.1%, 2026-07-13, RUTW PUT hh5gls5egcdlfbb | −301.17, −27.2%, 2026-07-28, RUTW PUT kekqioeqylgb4kl | 2.22 | 301 | 14 | 115% |
| SLV | ledger E2 | +11.01, +30.1%, 2026-09-11, SLV CALL m2eeuqdcs6jl3xr | +0.10, +0.2%, 2026-10-07, SLV CALL 2ti9rbrixeb0oze | ∞ | 0 | 0 | 100% |
| SMCI | ledger E2 | −16.17, −24.0%, 2026-10-09, SMCI PUT u0lsesrgx6ikwsj | −16.17, −24.0%, 2026-10-09, SMCI PUT u0lsesrgx6ikwsj | 0.00 | 16 | 1 | total ≤ 0 (best 5 days −16; without them +0) |
| SMH | ledger E2 | −3.18, −2.2%, 2026-10-12, SMH PUT c4i07emq4fnytre | −3.18, −2.2%, 2026-10-12, SMH PUT c4i07emq4fnytre | 0.00 | 3 | 1 | total ≤ 0 (best 5 days −3; without them +0) |
| SPXW | ledger E2 | +823.27, +56.3%, 2026-09-29, SPXW CALL 4cwxg2xbhvss79h | −777.97, −27.2%, 2026-03-16, SPXW CALL r98xgo27bdx4g5f | 0.89 | 3,530 | 159 | total ≤ 0 (best 5 days +3,270; without them −4,544) |
| SPY | ledger E2 | +40.40, +21.2%, 2026-08-18, SPY PUT kgrcrt2va87cvcl | −156.86, −26.3%, 2026-03-27, SPY PUT 5zy0jk44ra6yh18 | 0.42 | 606 | 158 | total ≤ 0 (best 5 days +128; without them −734) |
| TSLA | ledger E2 | +17.84, +6.7%, 2026-09-04, TSLA PUT mpxpmm8qv0ehcv0 | −13.51, −3.3%, 2026-08-21, TSLA CALL v71km1xj03uovgs | 1.87 | 24 | 122 | 165% |
| UBER | ledger E2 | −5.05, −18.4%, 2026-10-09, UBER CALL lk1w0emiuxfqtk7 | −5.05, −18.4%, 2026-10-09, UBER CALL lk1w0emiuxfqtk7 | 0.00 | 5 | 1 | total ≤ 0 (best 5 days −5; without them +0) |
| UCO | ledger E2 | −19.20, −26.2%, 2026-03-20, UCO CALL 0c63wm0dox7wy65 | −19.20, −26.2%, 2026-03-20, UCO CALL 0c63wm0dox7wy65 | 0.00 | 19 | 1 | total ≤ 0 (best 5 days −19; without them +0) |
| USO | ledger E2 | +40.60, +28.4%, 2026-03-20, USO CALL 4ug6m04x120lnp8 | +40.60, +28.4%, 2026-03-20, USO CALL 4ug6m04x120lnp8 | ∞ | 0 | 0 | 100% |
| all names | ledger E2 | +1,752.21, +122.3%, 2026-07-06, NDXP PUT fugmhxmitbyc9jl | −777.97, −27.2%, 2026-03-16, SPXW CALL r98xgo27bdx4g5f | 1.07 | 3,638 | 87 | 391% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $3.62 a trade) and Robinhood's charged instead (mean $2.63). The study's fees are given beside them below. Re-pricing: exact (888 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| AAPL | ledger E1 | 1 | **+18.81**, +4.00 | +6.49, +1.38 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| COIN | ledger E1 | 5 | **−2.18**, −17.88 | −12.50, −25.75 | 40.0 / 40.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| CRCL | ledger E1 | 12 | **−27.18**, −46.27 | −27.94, −47.57 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| CRM | ledger E1 | 1 | **+69.05**, +54.79 | +62.43, +49.54 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| CRML | ledger E1 | 14 | **+19.22**, +1.27 | +5.65, −0.59 | 85.7 / 78.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| CVNA | ledger E1 | 1 | **−27.06**, −199.24 | −27.94, −205.75 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| GOOGL | ledger E1 | 3 | **−25.13**, −19.46 | −27.94, −21.64 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| HOOD | ledger E1 | 3 | **+2.95**, −6.11 | −1.67, −9.61 | 66.7 / 66.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IWM | ledger E1 | 65 | **+16.02**, +33.90 | +13.74, +30.74 | 67.7 / 64.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| NVDA | ledger E1 | 14 | **+16.32**, +13.58 | +14.71, +11.90 | 57.1 / 57.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| OKLO | ledger E1 | 1 | **−24.33**, −44.15 | −27.94, −50.70 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| QQQ | ledger E1 | 63 | **+1.87**, +0.62 | −0.60, −4.21 | 46.0 / 30.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| RDDT | ledger E1 | 2 | **+17.46**, +28.01 | +13.84, +22.76 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| RKLB | ledger E1 | 28 | **+14.46**, +10.93 | +11.45, +9.16 | 64.3 / 64.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| RUTW | ledger E1 | 8 | **+6.79**, +17.93 | +6.86, +18.09 | 87.5 / 87.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SLV | ledger E1 | 3 | **−3.19**, −5.66 | −3.92, −6.96 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPXW | ledger E1 | 59 | **−3.57**, +8.22 | −0.02, +12.25 | 54.2 / 55.9 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY | ledger E1 | 89 | **+2.94**, +4.85 | +1.29, +1.41 | 48.3 / 42.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | ledger E1 | 372 | **+4.91**, +7.93 | +3.15, +5.83 | 53.8 / 49.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| AAPL | ledger E2 | 2 | **+5.82**, +3.55 | +0.91, −0.38 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| AMD | ledger E2 | 1 | **−25.96**, −34.41 | −27.94, −37.02 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| AMZN | ledger E2 | 6 | **−1.96**, −4.59 | −4.65, −7.65 | 16.7 / 16.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| AVGO | ledger E2 | 5 | **−5.70**, −0.04 | −9.00, −3.44 | 40.0 / 40.0 | [−9.07, +7.77] / [−12.65, +5.61] |
| BAC | ledger E2 | 1 | **−11.81**, −1.92 | −27.94, −4.54 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| COIN | ledger E2 | 1 | **+8.39**, +22.90 | +7.91, +21.60 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| GLD | ledger E2 | 17 | **+68.24**, +8.19 | +7.49, +5.49 | 52.9 / 47.1 | [+0.00, +61.34] / [+0.00, +32.98] |
| GOOGL | ledger E2 | 10 | **−2.75**, −4.69 | −5.62, −7.44 | 30.0 / 20.0 | [−5.01, +10.11] / [−8.57, +8.89] |
| HOOD | ledger E2 | 1 | **−20.59**, −7.33 | −27.94, −9.95 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IBIT | ledger E2 | 2 | **−3.83**, −2.11 | −7.92, −4.73 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IWM | ledger E2 | 19 | **−2.76**, −6.13 | −4.12, −8.60 | 36.8 / 36.8 | [−6.46, +17.44] / [−8.20, +13.22] |
| META | ledger E2 | 17 | **−3.59**, −9.10 | −4.40, −10.79 | 35.3 / 35.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| MSFT | ledger E2 | 1 | **+9.84**, +38.68 | +9.51, +37.38 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| MU | ledger E2 | 4 | **+1.66**, +5.31 | +0.31, +3.02 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| NDXP | ledger E2 | 16 | **+16.86**, +148.48 | +17.18, +149.80 | 56.2 / 56.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| QQQ | ledger E2 | 103 | **−0.89**, −2.15 | −2.11, −4.31 | 42.7 / 36.9 | [−4.59, +4.08] / [−5.66, +2.78] |
| RUTW | ledger E2 | 23 | **+7.66**, +48.84 | +7.67, +48.88 | 56.5 / 56.5 | [−1.21, +14.07] / [−1.20, +14.07] |
| SLV | ledger E2 | 3 | **+14.88**, +5.38 | +8.70, +2.76 | 100.0 / 66.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SMCI | ledger E2 | 1 | **−24.05**, −16.17 | −27.94, −18.78 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SMH | ledger E2 | 1 | **−2.15**, −3.18 | −3.92, −5.80 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPXW | ledger E2 | 206 | **−1.80**, −6.18 | +1.03, −3.72 | 38.3 / 40.3 | [−6.28, +2.53] / [−1.75, +4.20] |
| SPY | ledger E2 | 65 | **−2.98**, −9.32 | −4.05, −11.57 | 30.8 / 29.2 | [−4.45, −1.04] / [−5.86, −1.98] |
| TSLA | ledger E2 | 8 | **+4.19**, +2.61 | +2.11, +0.00 | 62.5 / 62.5 | [−2.97, +4.16] / [−3.92, +1.72] |
| UBER | ledger E2 | 1 | **−18.40**, −5.05 | −27.94, −7.67 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| UCO | ledger E2 | 1 | **−26.17**, −19.20 | −27.94, −20.49 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| USO | ledger E2 | 1 | **+28.43**, +40.60 | +27.52, +39.30 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | ledger E2 | 516 | **+1.50**, +2.46 | −0.13, +2.27 | 40.1 / 39.0 | [−2.81, +3.24] / [−2.08, +3.55] |

**Random baseline** (as the study computed it, at its own fees): time-matched random minutes, trail engine: MFE percentile 53 [47.5, 59.2] (Epoch 1) and 48 (Epoch 2).

**Exit reasons (share of trades):**

- ledger E1: TRAIL 48.7%; BREAKEVEN 32.3%; STOP 16.4%; TIME_STOP 1.6%; CLOSE 1.1%
- ledger E2: TRAIL 39.0%; BREAKEVEN 37.0%; STOP 23.4%; TIME_STOP 0.6%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2026 | AAPL | 3 | 66.7 | +10.15 | +3.70 | +11 |
| 2026 | AMD | 1 | 0.0 | −25.96 | −34.41 | −34 |
| 2026 | AMZN | 6 | 16.7 | −1.96 | −4.59 | −28 |
| 2026 | AVGO | 5 | 40.0 | −5.70 | −0.04 | −0 |
| 2026 | BAC | 1 | 0.0 | −11.81 | −1.92 | −2 |
| 2026 | COIN | 6 | 50.0 | −0.42 | −11.08 | −67 |
| 2026 | CRCL | 12 | 0.0 | −27.18 | −46.27 | −555 |
| 2026 | CRM | 1 | 100.0 | +69.05 | +54.79 | +55 |
| 2026 | CRML | 14 | 85.7 | +19.22 | +1.27 | +18 |
| 2026 | CVNA | 1 | 0.0 | −27.06 | −199.24 | −199 |
| 2026 | GLD | 17 | 52.9 | +68.24 | +8.19 | +139 |
| 2026 | GOOGL | 13 | 23.1 | −7.91 | −8.09 | −105 |
| 2026 | HOOD | 4 | 50.0 | −2.93 | −6.42 | −26 |
| 2026 | IBIT | 2 | 0.0 | −3.83 | −2.11 | −4 |
| 2026 | IWM | 84 | 60.7 | +11.77 | +24.84 | +2,087 |
| 2026 | META | 17 | 35.3 | −3.59 | −9.10 | −155 |
| 2026 | MSFT | 1 | 100.0 | +9.84 | +38.68 | +39 |
| 2026 | MU | 4 | 50.0 | +1.66 | +5.31 | +21 |
| 2026 | NDXP | 16 | 56.2 | +16.86 | +148.48 | +2,376 |
| 2026 | NVDA | 14 | 57.1 | +16.32 | +13.58 | +190 |
| 2026 | OKLO | 1 | 0.0 | −24.33 | −44.15 | −44 |
| 2026 | QQQ | 166 | 44.0 | +0.16 | −1.10 | −183 |
| 2026 | RDDT | 2 | 50.0 | +17.46 | +28.01 | +56 |
| 2026 | RKLB | 28 | 64.3 | +14.46 | +10.93 | +306 |
| 2026 | RUTW | 31 | 64.5 | +7.44 | +40.87 | +1,267 |
| 2026 | SLV | 6 | 50.0 | +5.85 | −0.14 | −1 |
| 2026 | SMCI | 1 | 0.0 | −24.05 | −16.17 | −16 |
| 2026 | SMH | 1 | 0.0 | −2.15 | −3.18 | −3 |
| 2026 | SPXW | 265 | 41.9 | −2.19 | −2.98 | −789 |
| 2026 | SPY | 154 | 40.9 | +0.44 | −1.13 | −174 |
| 2026 | TSLA | 8 | 62.5 | +4.19 | +2.61 | +21 |
| 2026 | UBER | 1 | 0.0 | −18.40 | −5.05 | −5 |
| 2026 | UCO | 1 | 0.0 | −26.17 | −19.20 | −19 |
| 2026 | USO | 1 | 100.0 | +28.43 | +40.60 | +41 |
| 2026 | all names | 888 | 45.8 | +2.93 | +4.75 | +4,216 |

![](charts/s4b.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** The entries are as good as random minutes once the exit is fixed.

## #5 Deep research round 1: flow rule F1 on SPY (H2 family)

**Folder:** `research/flow_predictors/ (@7dfea57); report "Finding a 0DTE options edge"`. **Commits:** — / — / 96a2c09…fb4205f, 5208c8f. **Dates:** 2026-10-13.

**Hypothesis.** Options-flow imbalances (net premium, net delta, market tide, dark pool) lead the underlying.

**Rule.** F1: the flow predictor's signal minute on SPY → buy the 0DTE contract in its direction, trail engine (as #4b).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Spread model of #2 (1% half-spread + $0.70 a side), entry at the VWAP of the first option bar after the signal.

**Data.** SPY, Unusual Whales flow and bars 2025-07-01 → 2026-10-09; F1 = 15-minute net premium against its trailing-20-session 20th/80th percentiles, every 5 minutes 09:45–15:00, at most 2 a day.

**Periods and holdouts.** One span (descriptive test 5).

**Pass rule (as pre-registered).** Multiple-testing correction across 62 cells (exploratory).

**Verdict.** Rejected: 0 of 62 cells survive correction; forward ICs ≤ 0.02 (registry H2). The other round-1 notes (GEX regime and exit grid of 576 configurations, short-vol session T1–T5) kept results by configuration only; their verdicts: H4 rejected, H6 rejected, H7 0 of 576 exit configurations positive (White p = 1), H8 every option expression negative.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | 2025-07→2026-10 | 638 | 319 / 331 | 35.9 | +14.8, +23.24 | −12.2, −17.41 | −2.1, −2.60 | **−2.48**, −2.82 | [−3.55, −1.17]; [−4.47, −0.72] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | 2025-07→2026-10 | +177.21, +85.2%, 2025-12-18, SPY251218C00676000 | −82.49, −26.8%, 2026-07-29, SPY260729C00736000 | 0.75 | 1,805 | 331 | total ≤ 0 (best 5 days +647; without them −2,445) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (638 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | 2025-07→2026-10 | 638 | **−2.48**, −2.82 | −3.45, −4.12 | 35.9 / 35.9 | [−3.55, −1.17] / [−4.53, −2.12] |

**Random baseline** (as the study computed it, at its own fees): random minutes matched per day, random side, same exits and costs (574 trades): −$3.34 a trade, −2.26% (the rule −$4.12, −2.38%).

**Exit reasons (share of trades):**

- 2025-07→2026-10: BREAKEVEN 37.8%; TRAIL 35.9%; STOP 26.0%; TIME_STOP 0.3%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | SPY | 250 | 36.4 | −2.93 | −2.45 | −614 |
| 2026 | SPY | 388 | 35.6 | −2.18 | −3.05 | −1,185 |

![](charts/s5.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** The one flow rule with a trade list loses after costs.

## #6a T-A: the 13:00 short ATM 0DTE straddle, SPY/QQQ/IWM, bought back 15:55 (H9)

**Folder:** `research/thetadata/straddle_nbbo/ (@7dfea57)`. **Commits:** — / gate v2 924aee9 / ebde6ae. **Dates:** 2026-10-13.

**Hypothesis.** Selling the 13:00 at-the-money straddle harvests intraday variance premium after measured costs.

**Rule.** Sell the same-day ATM straddle at the 13:00 bids, buy it back at the 15:55 asks.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Measured ThetaData NBBO both ways (the round trip $12.93 a SPY/QQQ straddle); return as % of the credit received.

**Data.** SPY, QQQ, IWM 0DTE, 339 sessions each, 2025-06-02 → 2026-10-09.

**Periods and holdouts.** One span; no holdout ("previously analysed").

**Pass rule (as pre-registered).** Gate v2: a positive lower bound at measured NBBO (T-A).

**Verdict.** FAIL: +$8.60 a straddle [−6.07, +22.45] SPY/QQQ (n 678); IWM −$9.50 [−18.69, −0.44].

**Metrics at Robinhood fees** (return = % of the credit received; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2025-06→2026-10 | 339 | 339 / 352 | 58.4 | +40.1, +43.53 | −71.3, −77.72 | +17.3, +14.80 | **−6.22**, −6.90 | [−13.67, −1.11]; [−17.06, +0.58] |
| QQQ | 2025-06→2026-10 | 339 | 339 / 352 | 65.8 | +39.5, +90.29 | −54.2, −133.74 | +20.7, +47.80 | **+7.41**, +13.63 | [+2.39, +12.20]; [−0.70, +26.27] |
| SPY | 2025-06→2026-10 | 339 | 339 / 352 | 65.2 | +40.0, +77.36 | −57.3, −119.68 | +20.8, +38.80 | **+6.12**, +8.77 | [+1.16, +10.27]; [−4.18, +19.47] |
| all names | 2025-06→2026-10 | 1,017 | 339 / 352 | 63.1 | +39.8, +71.42 | −61.6, −108.25 | +20.0, +27.80 | **+2.44**, +5.17 | [−2.53, +6.28]; [−6.16, +14.35] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2025-06→2026-10 | +330.80, +81.5%, 2026-07-29, IWM 13:00 short straddle 289 | −403.20, −238.6%, 2026-06-11, IWM 13:00 short straddle 285 | 0.79 | 3,358 | 346 | total ≤ 0 (best 5 days +1,038; without them −3,378) |
| QQQ | 2025-06→2026-10 | +345.80, +77.2%, 2026-06-12, QQQ 13:00 short straddle 722 | −1,184.20, −224.7%, 2026-06-11, QQQ 13:00 short straddle 700 | 1.30 | 2,434 | 125 | 34% |
| SPY | 2025-06→2026-10 | +321.80, +67.3%, 2025-09-17, SPY 13:00 short straddle 658 | −764.20, −196.5%, 2026-06-11, SPY 13:00 short straddle 727 | 1.21 | 2,233 | 148 | 42% |
| all names | 2025-06→2026-10 | +345.80, +77.2%, 2026-06-12, QQQ 13:00 short straddle 722 | −1,184.20, −224.7%, 2026-06-11, QQQ 13:00 short straddle 700 | 1.13 | 6,185 | 148 | 68% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.80 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (1,017 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2025-06→2026-10 | 339 | **−6.22**, −6.90 | −8.94, −9.50 | 58.4 / 57.2 | [−13.67, −1.11] / [−16.30, −3.87] |
| QQQ | 2025-06→2026-10 | 339 | **+7.41**, +13.63 | +6.15, +11.03 | 65.8 / 65.2 | [+2.39, +12.20] / [+1.12, +10.94] |
| SPY | 2025-06→2026-10 | 339 | **+6.12**, +8.77 | +4.64, +6.17 | 65.2 / 64.3 | [+1.16, +10.27] / [−0.30, +8.72] |
| all names | 2025-06→2026-10 | 1,017 | **+2.44**, +5.17 | +0.62, +2.57 | 63.1 / 62.2 | [−2.53, +6.28] / [−4.33, +4.41] |

**Random baseline** (as the study computed it, at its own fees): random entry times: +$13.10 [−2.42, +29.14] against a $12.93 round trip (registry H9).

**Exit reasons (share of trades):**

- 2025-06→2026-10: bought back 15:55 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | IWM | 145 | 57.9 | −7.29 | −6.93 | −1,005 |
| 2026 | IWM | 194 | 58.8 | −5.41 | −6.88 | −1,335 |
| 2025 | QQQ | 145 | 69.7 | +12.48 | +24.67 | +3,577 |
| 2026 | QQQ | 194 | 62.9 | +3.62 | +5.38 | +1,044 |
| 2025 | SPY | 145 | 68.3 | +11.10 | +20.50 | +2,972 |
| 2026 | SPY | 194 | 62.9 | +2.40 | +0.00 | +1 |
| 2025 | all names | 435 | 65.3 | +5.43 | +12.74 | +5,543 |
| 2026 | all names | 582 | 61.5 | +0.20 | −0.50 | −290 |

![](charts/s6a.png)

**Amendments, deviations and integrity checks.** The modelled-spread result (+$8.36) was optimistic by about $5 a straddle.

**What it showed.** The 13:00 short straddle is positive on SPY/QQQ with an interval through zero and negative on IWM.

## #6b T-B: gamma-conditioned last-30-minute momentum in SPY shares (H10)

**Folder:** `research/thetadata/index_tests/tb_momentum/ (@7dfea57)`. **Commits:** — / — / b209f7b. **Dates:** 2026-10-13.

**Hypothesis.** On negative-gamma days the last 30 minutes continue the session's move.

**Rule.** On days with dealer gamma below the flip (prior-day UW levels): 100 SPY in the direction of the open→15:30 move, 15:30 → official close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Net of the study's cost per day (0.4 bp).

**Data.** SPY, 299 negative-gamma days 2024-05-14 → 2026-10-07.

**Periods and holdouts.** One span.

**Pass rule (as pre-registered).** T-B: positive mean with a positive lower bound.

**Verdict.** FAIL (wrong sign): −3.07 bp a day [−5.73, −0.52], Sharpe −2.15.

**Metrics at Robinhood fees** (return = % of notional ($ = per 100 sh); win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | negative-gamma days 2024-05→2026-10 | 299 | 299 / 620 | 46.5 | +0.128, +77.62 | −0.165, −101.78 | −0.012, −7.22 | **−0.029**, −18.38 | [−0.054, −0.001]; [−32.83, −2.86] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | negative-gamma days 2024-05→2026-10 | +523.44, +1.0%, 2025-04-04, 100 SPY short 15:30→close | −698.04, −1.2%, 2025-03-04, 100 SPY long 15:30→close | 0.66 | 5,964 | 620 | total ≤ 0 (best 5 days +2,021; without them −7,517) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.55 a trade) and Robinhood's charged instead (mean $1.34). The study's fees are given beside them below. Re-pricing: Robinhood fees inferred from the rule: the study's 0.2 bp a side is a generic cost, taken as fees and replaced (299 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | negative-gamma days 2024-05→2026-10 | 299 | **−0.029**, −18.38 | −0.031, −19.59 | 46.5 / 46.2 | [−0.054, −0.001] / [−0.056, −0.003] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- negative-gamma days 2024-05→2026-10: official close 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | SPY | 77 | 50.6 | −0.03 | −18.29 | −1,408 |
| 2025 | SPY | 125 | 44.0 | −0.02 | −15.41 | −1,926 |
| 2026 | SPY | 97 | 46.4 | −0.03 | −22.28 | −2,162 |

![](charts/s6b.png)

**Amendments, deviations and integrity checks.** The two gamma proxies agree on the regime 52% of days.

**What it showed.** The effect has the wrong sign.

## #6c T-C: the 13:00 SPXW short straddle bought back 15:55 (H11)

**Folder:** `research/thetadata/index_tests/tc_spxw_straddle/ (@7dfea57)`. **Commits:** — / — / b209f7b. **Dates:** 2026-10-13.

**Hypothesis.** As T-A on SPXW (cash-settled).

**Rule.** Sell the SPXW ATM straddle at 13:00 (bids), buy back at 15:55 (asks).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Measured NBBO; return as % of the credit.

**Data.** SPXW 0DTE, 339 sessions 2025-06-02 → 2026-10-09.

**Periods and holdouts.** One span.

**Pass rule (as pre-registered).** T-C: positive lower bound.

**Verdict.** FAIL: +$72.4 a day [−75.8, +214.2], max drawdown −$21,180, worst day −$8,499.

**Metrics at Robinhood fees** (return = % of the credit received; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | 2025-06→2026-10 | 339 | 339 / 352 | 63.4 | +46.5, +832.04 | −66.7, −1,246.05 | +26.2, +395.48 | **+5.07**, +71.91 | [−0.09, +8.97]; [−56.51, +173.38] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | 2025-06→2026-10 | +3,370.48, +71.7%, 2025-09-17, SPXW 13:00 short straddle 6590.0 | −8,499.52, −230.3%, 2026-06-11, SPXW 13:00 short straddle 7275.0 | 1.16 | 21,186 | 91 | 54% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $4.00 a trade) and Robinhood's charged instead (mean $4.52). The study's fees are given beside them below. Re-pricing: Robinhood fees inferred from the rule: the 15:55 buy-back legs' price tier (only the straddle's debit is kept) (339 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | 2025-06→2026-10 | 339 | **+5.07**, +71.91 | +5.11, +72.43 | 63.4 / 63.4 | [−0.09, +8.97] / [−0.06, +9.01] |

**Random baseline** (as the study computed it, at its own fees): random entry: +$40.6 [−73.4, +164.2] against a $68.9 cost.

**Exit reasons (share of trades):**

- 2025-06→2026-10: bought back 15:55 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | SPXW | 145 | 63.4 | +7.60 | +153.24 | +22,219 |
| 2026 | SPXW | 194 | 63.4 | +3.19 | +11.12 | +2,158 |

![](charts/s6c.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Positive mean, interval through zero, large tail days.

## #6d T-E: the 13:00 SPXW ATM straddle held to PM settlement, ex FOMC/CPI/NFP (H13)

**Folder:** `research/thetadata/hwr_grid/spxw_v2/ (@7dfea57)`. **Commits:** protocol sha256 in protocol_sha256.txt / — / 01ee3f3, 5f253c6 (full chains). **Dates:** 2026-10-14.

**Hypothesis.** Holding the short straddle to cash settlement adds the last hour's decay.

**Rule.** Sell the SPXW ATM straddle at 13:00, hold to the PM settlement (Cboe close), skip FOMC/CPI/NFP days.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Measured NBBO in; settlement value out.

**Data.** SPXW 0DTE 2022-05-13 → 2026-10-09 on complete chains.

**Periods and holdouts.** TRAIN 2022-05→2024 / TEST 2025→2026-10 (TEST read).

**Pass rule (as pre-registered).** T-E gate on TEST.

**Verdict.** FAIL: +$26.94 a day [−136.73, +170.75]; 2025-04-09 alone −$33,667 a lot; trails random entry in both windows.

**Metrics at Robinhood fees** (return = % of the credit received; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | TRAIN | 575 | 575 / 683 | 60.2 | +54.3, +881.09 | −81.0, −1,229.08 | +22.1, +353.74 | **+0.40**, +40.69 | [−6.13, +6.47]; [−56.80, +135.66] |
| SPXW | TEST | 388 | 388 / 457 | 67.0 | +52.8, +997.58 | −80.7, −1,767.78 | +28.0, +486.74 | **+8.74**, +85.30 | [+1.85, +14.75]; [−115.97, +252.47] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | TRAIN | +2,926.74, +96.3%, 2022-05-13, SPXW 13:00 4025P/4025C | −9,211.26, −860.9%, 2024-04-04, SPXW 13:00 5250P/5250C | 1.08 | 22,502 | 526 | 58% |
| SPXW | TEST | +4,099.74, +96.5%, 2025-03-06, SPXW 13:00 5740P/5740C | −34,022.26, −392.4%, 2025-04-09, SPXW 13:00 5030P/5030C | 1.15 | 38,495 | 175 | 53% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.00 a trade) and Robinhood's charged instead (mean $2.26). The study's fees are given beside them below. Re-pricing: Robinhood fees inferred from the rule: each leg's price tier (only the credit is kept; $1.00 and up unless the credit is under $1.00) (963 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | TRAIN | 575 | **+0.40**, +40.69 | +0.42, +40.95 | 60.2 / 60.2 | [−6.13, +6.47] / [−6.12, +6.49] |
| SPXW | TEST | 388 | **+8.74**, +85.30 | +8.75, +85.56 | 67.0 / 67.0 | [+1.85, +14.75] / [+1.86, +14.77] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- TRAIN: settle 100.0%
- TEST: settle 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 140 | 61.4 | +4.58 | +102.76 | +14,387 |
| 2023 | SPXW | 217 | 58.5 | −1.50 | +1.62 | +352 |
| 2024 | SPXW | 218 | 61.0 | −0.40 | +39.72 | +8,659 |
| 2025 | SPXW | 218 | 69.3 | +10.31 | +97.72 | +21,302 |
| 2026 | SPXW | 170 | 64.1 | +6.72 | +69.37 | +11,793 |

![](charts/s6d.png)

**Amendments, deviations and integrity checks.** Re-run on complete chains (5f253c6, 8fb5bad): no TEST figure changed.

**What it showed.** One day can erase years; no edge.

## #6e H15 carry lane: the 14:05 SPXW short strangle at ±0.5 expected move, held to settlement

**Folder:** `research/thetadata/hwr_grid/spxw_v2/ (@7dfea57); report "High win rate 0DTE lanes"`. **Commits:** protocol_sha256.txt / — / 01ee3f3, 97e685a, 6691368. **Dates:** 2026-10-14.

**Hypothesis.** A 70%+ win-rate short strangle with a positive cost-realistic lower bound exists.

**Rule.** 14:05 sell the SPXW strangle at ±0.5 × the 14:05 expected move, held to cash settlement, skip FOMC and month-end (selection S2 on TRAIN).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Measured NBBO in; settlement out.

**Data.** SPXW 0DTE 2022-05-13 → 2026-10-09.

**Periods and holdouts.** TRAIN (selection) / TEST (read). The deciding test T-G (forward paper ≥ 150 sessions) was never started.

**Pass rule (as pre-registered).** Positive TEST lower bound after the two selections; then T-G forward.

**Verdict.** Open, NOT promotable: TEST +$151.17 a lot [+42.15, +251.73], win 70.8%; the pre-registered reselection on complete TRAIN picks a different S2 that fails (+$52.54 [−22.24, +122.49]); ±10% shock ≈ −$65k a lot.

**Metrics at Robinhood fees** (return = % of the credit received; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | TRAIN | 606 | 606 / 682 | 72.1 | +83.8, +528.16 | −166.7, −922.10 | +97.3, +347.74 | **+13.98**, +123.71 | [+1.57, +24.80]; [+60.00, +188.18] |
| SPXW | TEST | 407 | 407 / 457 | 70.8 | +86.4, +646.09 | −147.7, −1,047.53 | +95.8, +352.74 | **+17.98**, +150.91 | [+3.49, +29.85]; [+33.90, +263.67] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | TRAIN | +1,827.74, +99.9%, 2024-08-05, SPXW 14:05 5175P/5215C | −7,146.26, −1,125.4%, 2024-04-04, SPXW 14:05 5225P/5240C | 1.48 | 10,109 | 91 | 10% |
| SPXW | TEST | +4,577.74, +100.0%, 2025-04-10, SPXW 14:05 5245P/5335C | −7,131.26, −735.2%, 2026-03-09, SPXW 14:05 6690P/6715C | 1.49 | 13,025 | 157 | 28% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.00 a trade) and Robinhood's charged instead (mean $2.26). The study's fees are given beside them below. Re-pricing: Robinhood fees inferred from the rule: each leg's price tier (only the credit is kept; $1.00 and up unless the credit is under $1.00) (1,013 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | TRAIN | 606 | **+13.98**, +123.71 | +14.03, +123.98 | 72.1 / 72.1 | [+1.57, +24.80] / [+1.62, +24.85] |
| SPXW | TEST | 407 | **+17.98**, +150.91 | +18.02, +151.17 | 70.8 / 70.8 | [+3.49, +29.85] / [+3.54, +29.89] |

**Random baseline** (as the study computed it, at its own fees): matched random: +$22.60 [−147.61, +261.12].

**Exit reasons (share of trades):**

- TRAIN: settle 100.0%
- TEST: settle 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 146 | 73.3 | +20.70 | +217.14 | +31,703 |
| 2023 | SPXW | 228 | 67.1 | +5.37 | +38.58 | +8,797 |
| 2024 | SPXW | 232 | 76.3 | +18.20 | +148.58 | +34,472 |
| 2025 | SPXW | 228 | 71.9 | +22.48 | +228.34 | +52,062 |
| 2026 | SPXW | 179 | 69.3 | +12.24 | +52.28 | +9,357 |

![](charts/s6e.png)

**Amendments, deviations and integrity checks.** All historical data has been used for selection; no further historical re-selection allowed (registry).

**What it showed.** Positive on TEST, but the reselection fails and the tail risk is unbounded.

## #7a S01 Quick Scalps (owner baseline) on index 0DTE

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** protocol 113cad7 / — / 5e90201. **Dates:** 2026-10-14.

**Hypothesis.** The owner's Quick Scalps signal (RSI14 cross 55/45 + EMA9 lead, 5m EMA20 + VWAP confirm, 15m EMA alignment) predicts 0DTE moves.

**Rule.** Signal → buy the 0DTE contract in a delta band at the ask; exits: stop, two targets, VWAP loss, invalidation, time.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM 0DTE 2022-11-11 → 2026-10-08.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** Positive net expectancy with a positive lower bound (protocol).

**Verdict.** REJECTED: −$4.19 a contract [−5.68, −2.81].

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2022-11→2026-10 | 685 | 274 / 638 | 35.0 | +37.4, +20.71 | −26.2, −14.50 | −25.2, −9.10 | **−3.89**, −2.16 | [−6.28, −1.52]; [−3.61, −0.83] |
| QQQ | 2022-11→2026-10 | 1,075 | 421 / 1,009 | 36.8 | +36.1, +39.24 | −25.6, −26.85 | −22.2, −14.10 | **−2.85**, −2.50 | [−4.78, −1.21]; [−4.52, −0.66] |
| SPY | 2022-11→2026-10 | 1,126 | 444 / 1,009 | 35.5 | +36.1, +32.76 | −24.0, −23.77 | −17.9, −12.10 | **−2.63**, −3.69 | [−4.52, −0.90]; [−6.03, −1.75] |
| all names | 2022-11→2026-10 | 2,886 | 614 / 1,009 | 35.9 | +36.4, +32.44 | −25.1, −22.67 | −21.6, −11.10 | **−3.01**, −2.89 | [−4.41, −1.79]; [−4.49, −1.58] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2022-11→2026-10 | +72.40, +51.0%, 2026-06-12, IWM 2026-06-12 292.0CALL | −59.10, −29.6%, 2025-04-07, IWM 2025-04-07 178.0PUT | 0.77 | 1,610 | 571 | total ≤ 0 (best 5 days +396; without them −1,879) |
| QQQ | 2022-11→2026-10 | +346.89, +112.3%, 2026-06-09, QQQ 2026-06-09 692.0PUT | −156.10, −34.2%, 2025-04-07, QQQ 2025-04-07 417.0PUT | 0.85 | 3,381 | 1,007 | total ≤ 0 (best 5 days +1,405; without them −4,095) |
| SPY | 2022-11→2026-10 | +145.90, +51.7%, 2025-03-11, SPY 2025-03-11 557.0PUT | −114.10, −24.8%, 2025-04-09, SPY 2025-04-09 495.0PUT | 0.76 | 4,510 | 966 | total ≤ 0 (best 5 days +785; without them −4,943) |
| all names | 2022-11→2026-10 | +346.89, +112.3%, 2026-06-09, QQQ 2026-06-09 692.0PUT | −156.10, −34.2%, 2025-04-07, QQQ 2025-04-07 417.0PUT | 0.80 | 8,689 | 991 | total ≤ 0 (best 5 days +1,575; without them −9,906) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (2,886 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2022-11→2026-10 | 685 | **−3.89**, −2.16 | −6.74, −3.46 | 35.0 / 33.3 | [−6.28, −1.52] / [−9.19, −4.39] |
| QQQ | 2022-11→2026-10 | 1,075 | **−2.85**, −2.50 | −4.38, −3.80 | 36.8 / 35.0 | [−4.78, −1.21] / [−6.34, −2.71] |
| SPY | 2022-11→2026-10 | 1,126 | **−2.63**, −3.69 | −4.32, −4.99 | 35.5 / 34.3 | [−4.52, −0.90] / [−6.19, −2.60] |
| all names | 2022-11→2026-10 | 2,886 | **−3.01**, −2.89 | −4.92, −4.19 | 35.9 / 34.3 | [−4.41, −1.79] / [−6.31, −3.69] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2022-11→2026-10: stop 51.9%; target_2 26.3%; vwap_loss 15.3%; time 5.4%; invalidation 1.1%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 157 | 36.9 | −2.73 | −0.47 | −73 |
| 2025 | IWM | 311 | 35.7 | −2.94 | −2.08 | −647 |
| 2026 | IWM | 217 | 32.7 | −6.08 | −3.51 | −762 |
| 2022 | QQQ | 34 | 35.3 | −4.44 | −3.66 | −124 |
| 2023 | QQQ | 293 | 33.4 | −5.58 | −3.91 | −1,146 |
| 2024 | QQQ | 287 | 38.0 | −2.42 | −2.20 | −631 |
| 2025 | QQQ | 241 | 39.0 | −1.29 | −2.50 | −602 |
| 2026 | QQQ | 220 | 37.7 | −1.21 | −0.85 | −187 |
| 2022 | SPY | 40 | 45.0 | +3.25 | +2.29 | +91 |
| 2023 | SPY | 285 | 32.6 | −4.51 | −3.22 | −919 |
| 2024 | SPY | 281 | 35.9 | −1.98 | −2.44 | −685 |
| 2025 | SPY | 282 | 37.2 | −2.44 | −4.72 | −1,331 |
| 2026 | SPY | 238 | 34.9 | −2.39 | −5.52 | −1,315 |
| 2022 | all names | 74 | 40.5 | −0.28 | −0.45 | −33 |
| 2023 | all names | 578 | 33.0 | −5.05 | −3.57 | −2,065 |
| 2024 | all names | 725 | 37.0 | −2.32 | −1.92 | −1,389 |
| 2025 | all names | 834 | 37.2 | −2.29 | −3.09 | −2,580 |
| 2026 | all names | 675 | 35.1 | −3.20 | −3.35 | −2,264 |

![](charts/s7a.png)

**Amendments, deviations and integrity checks.** Status ≠ filled rows (no chain, in position, no expiry) are not trades.

**What it showed.** The baseline loses $4 a contract after costs.

## #7b S02 Quick Scalps: 41-variant grid, walk-forward OOS (lower-bound selection)

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** 113cad7 / — / 6bf5934. **Dates:** 2026-10-14.

**Hypothesis.** A single-factor variant of the baseline holds out of sample.

**Rule.** Each year, the variant with the best lower bound on the years before is traded the next year (walk-forward).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM 0DTE, OOS 2024-01 → 2026-10.

**Periods and holdouts.** Walk-forward OOS years 2024–2026.

**Pass rule (as pre-registered).** Positive OOS lower bound, better than matched random.

**Verdict.** Nothing promoted: OOS −$3.81 [−5.23, −2.35]; no variant positive or better than random.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | walk-forward OOS 2024-01→2026-10 | 935 | 314 / 638 | 34.5 | +35.9, +18.92 | −26.1, −13.42 | −25.3, −7.10 | **−4.67**, −2.25 | [−6.71, −2.72]; [−3.43, −1.16] |
| QQQ | walk-forward OOS 2024-01→2026-10 | 1,117 | 352 / 715 | 38.0 | +35.7, +39.64 | −25.4, −26.27 | −21.3, −10.10 | **−2.22**, −1.25 | [−4.12, −0.57]; [−3.55, +1.03] |
| SPY | walk-forward OOS 2024-01→2026-10 | 1,148 | 373 / 715 | 36.4 | +35.6, +31.63 | −24.5, −24.30 | −18.2, −10.10 | **−2.65**, −3.93 | [−4.92, −0.91]; [−6.75, −1.69] |
| all names | walk-forward OOS 2024-01→2026-10 | 3,200 | 488 / 715 | 36.4 | +35.7, +31.02 | −25.3, −21.70 | −22.0, −9.10 | **−3.09**, −2.51 | [−4.63, −1.82]; [−4.16, −1.16] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | walk-forward OOS 2024-01→2026-10 | +109.90, +199.8%, 2025-02-07, IWM 227.5PUT no_15m | −119.10, −70.5%, 2025-09-17, IWM 239.0PUT no_15m | 0.74 | 2,158 | 571 | total ≤ 0 (best 5 days +561; without them −2,661) |
| QQQ | walk-forward OOS 2024-01→2026-10 | +346.89, +112.3%, 2026-06-09, QQQ 692.0PUT no_15m | −156.10, −34.2%, 2025-04-07, QQQ 417.0PUT no_15m | 0.92 | 1,615 | 668 | total ≤ 0 (best 5 days +1,714; without them −3,116) |
| SPY | walk-forward OOS 2024-01→2026-10 | +173.39, +40.3%, 2025-04-10, SPY 516.0PUT no_15m | −162.11, −23.5%, 2025-04-07, SPY 496.0PUT no_15m | 0.75 | 4,899 | 692 | total ≤ 0 (best 5 days +956; without them −5,472) |
| all names | walk-forward OOS 2024-01→2026-10 | +346.89, +112.3%, 2026-06-09, QQQ 692.0PUT no_15m | −162.11, −23.5%, 2025-04-07, SPY 496.0PUT no_15m | 0.82 | 8,361 | 668 | total ≤ 0 (best 5 days +2,083; without them −10,101) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (3,200 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | walk-forward OOS 2024-01→2026-10 | 935 | **−4.67**, −2.25 | −7.85, −3.55 | 34.5 / 32.2 | [−6.71, −2.72] / [−10.10, −5.79] |
| QQQ | walk-forward OOS 2024-01→2026-10 | 1,117 | **−2.22**, −1.25 | −3.97, −2.55 | 38.0 / 36.6 | [−4.12, −0.57] / [−5.94, −2.21] |
| SPY | walk-forward OOS 2024-01→2026-10 | 1,148 | **−2.65**, −3.93 | −4.55, −5.23 | 36.4 / 35.1 | [−4.92, −0.91] / [−6.76, −2.77] |
| all names | walk-forward OOS 2024-01→2026-10 | 3,200 | **−3.09**, −2.51 | −5.31, −3.81 | 36.4 / 34.8 | [−4.63, −1.82] / [−6.87, −3.98] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- walk-forward OOS 2024-01→2026-10: stop 52.8%; target_2 24.4%; vwap_loss 14.3%; ema_target 4.2%; time 3.6%; invalidation 0.8%; settlement 0.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 150 | 32.7 | −5.10 | −0.79 | −118 |
| 2025 | IWM | 475 | 36.4 | −3.21 | −1.68 | −796 |
| 2026 | IWM | 310 | 32.6 | −6.70 | −3.83 | −1,186 |
| 2024 | QQQ | 317 | 34.7 | −3.70 | −1.73 | −548 |
| 2025 | QQQ | 429 | 42.2 | −0.46 | +0.49 | +211 |
| 2026 | QQQ | 371 | 35.8 | −2.98 | −2.87 | −1,064 |
| 2024 | SPY | 300 | 33.0 | −3.66 | −2.06 | −618 |
| 2025 | SPY | 475 | 39.6 | −2.20 | −4.32 | −2,050 |
| 2026 | SPY | 373 | 35.1 | −2.40 | −4.96 | −1,849 |
| 2024 | all names | 767 | 33.6 | −3.96 | −1.67 | −1,284 |
| 2025 | all names | 1,379 | 39.3 | −2.01 | −1.91 | −2,635 |
| 2026 | all names | 1,054 | 34.6 | −3.87 | −3.89 | −4,099 |

![](charts/s7b.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Variant selection does not rescue the signal.

## #7c S03 Quick Scalps with weekly expirations (1–7 days)

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** 113cad7 / — / 3c8d6cb. **Dates:** 2026-10-14.

**Hypothesis.** The signal works on weekly contracts.

**Rule.** Quick Scalps signal → nearest Friday contract, OI > 250.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM weekly chains, sampled sessions 2017-06 → 2026-10.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** As S01.

**Verdict.** Nothing promoted: +$1.27 a contract [−3.69, +6.25] (= random).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2017-06→2026-10 | 239 | 141 / 2,394 | 41.4 | +27.7, +40.24 | −14.1, −22.66 | −3.9, −6.10 | **+3.21**, +3.39 | [−0.34, +6.81]; [−1.55, +9.44] |
| QQQ | 2017-06→2026-10 | 217 | 135 / 2,386 | 36.9 | +23.7, +65.41 | −15.5, −39.52 | −6.6, −13.10 | **−1.07**, −0.83 | [−4.07, +2.56]; [−10.65, +10.52] |
| SPY | 2017-06→2026-10 | 362 | 221 / 2,393 | 36.2 | +29.2, +72.20 | −15.9, −34.57 | −5.9, −8.10 | **+0.39**, +4.06 | [−2.01, +2.90]; [−1.87, +11.12] |
| all names | 2017-06→2026-10 | 818 | 376 / 2,399 | 37.9 | +27.3, +60.24 | −15.3, −32.62 | −5.7, −8.10 | **+0.83**, +2.57 | [−0.91, +2.53]; [−1.49, +6.93] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2017-06→2026-10 | +168.89, +39.5%, 2025-04-08, IWM 2025-04-11 176.0PUT | −99.10, −21.8%, 2020-06-12, IWM 2020-06-19 134.5PUT | 1.26 | 497 | 1,422 | 92% |
| QQQ | 2017-06→2026-10 | +416.87, +39.9%, 2025-04-08, QQQ 2025-04-11 423.0PUT | −167.10, −33.6%, 2026-02-05, QQQ 2026-02-06 594.0PUT | 0.97 | 1,797 | 1,942 | total ≤ 0 (best 5 days +1,661; without them −1,842) |
| SPY | 2017-06→2026-10 | +464.39, +120.3%, 2020-05-15, SPY 2020-05-22 286.0CALL | −226.11, −31.8%, 2020-03-10, SPY 2020-03-13 273.0PUT | 1.18 | 854 | 739 | 121% |
| all names | 2017-06→2026-10 | +464.39, +120.3%, 2020-05-15, SPY 2020-05-22 286.0CALL | −226.11, −31.8%, 2020-03-10, SPY 2020-03-13 273.0PUT | 1.13 | 902 | 726 | 118% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (818 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2017-06→2026-10 | 239 | **+3.21**, +3.39 | +2.14, +2.09 | 41.4 / 40.6 | [−0.34, +6.81] / [−1.42, +5.76] |
| QQQ | 2017-06→2026-10 | 217 | **−1.07**, −0.83 | −1.82, −2.13 | 36.9 / 36.9 | [−4.07, +2.56] / [−4.84, +1.90] |
| SPY | 2017-06→2026-10 | 362 | **+0.39**, +4.06 | −0.50, +2.76 | 36.2 / 36.2 | [−2.01, +2.90] / [−2.94, +2.05] |
| all names | 2017-06→2026-10 | 818 | **+0.83**, +2.57 | −0.08, +1.27 | 37.9 / 37.7 | [−0.91, +2.53] / [−1.87, +1.70] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2017-06→2026-10: vwap_loss 50.6%; data_end 17.6%; target_2 17.5%; stop 8.6%; invalidation 5.4%; time 0.4%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2017 | IWM | 20 | 35.0 | −2.01 | −3.43 | −69 |
| 2018 | IWM | 30 | 53.3 | +8.83 | +9.48 | +284 |
| 2019 | IWM | 15 | 46.7 | +2.74 | +3.87 | +58 |
| 2020 | IWM | 34 | 35.3 | +2.62 | −0.79 | −27 |
| 2021 | IWM | 29 | 37.9 | +2.60 | +1.88 | +55 |
| 2022 | IWM | 20 | 20.0 | −3.05 | −10.88 | −218 |
| 2023 | IWM | 31 | 35.5 | −1.72 | −4.86 | −151 |
| 2024 | IWM | 17 | 41.2 | +3.23 | +6.99 | +119 |
| 2025 | IWM | 24 | 66.7 | +16.71 | +33.11 | +795 |
| 2026 | IWM | 19 | 42.1 | −0.22 | −1.89 | −36 |
| 2017 | QQQ | 14 | 14.3 | −6.61 | −3.99 | −56 |
| 2018 | QQQ | 21 | 76.2 | +15.13 | +27.45 | +576 |
| 2019 | QQQ | 16 | 37.5 | −8.39 | −8.19 | −131 |
| 2020 | QQQ | 32 | 37.5 | −4.01 | −16.56 | −530 |
| 2021 | QQQ | 27 | 18.5 | −11.97 | −22.19 | −599 |
| 2022 | QQQ | 26 | 30.8 | −0.82 | −9.93 | −258 |
| 2023 | QQQ | 26 | 34.6 | −0.72 | −5.87 | −153 |
| 2024 | QQQ | 23 | 30.4 | +2.49 | +2.81 | +65 |
| 2025 | QQQ | 22 | 54.5 | +8.04 | +54.33 | +1,195 |
| 2026 | QQQ | 10 | 30.0 | −6.52 | −29.05 | −291 |
| 2017 | SPY | 32 | 25.0 | −3.41 | −0.32 | −10 |
| 2018 | SPY | 75 | 29.3 | −2.69 | −5.44 | −408 |
| 2019 | SPY | 46 | 21.7 | −7.32 | −7.95 | −366 |
| 2020 | SPY | 39 | 41.0 | +5.90 | +24.03 | +937 |
| 2021 | SPY | 51 | 41.2 | −0.11 | +3.79 | +193 |
| 2022 | SPY | 36 | 38.9 | +3.19 | +9.77 | +352 |
| 2023 | SPY | 30 | 53.3 | +8.63 | +19.10 | +573 |
| 2024 | SPY | 21 | 57.1 | +8.43 | +17.90 | +376 |
| 2025 | SPY | 17 | 35.3 | −2.76 | −15.69 | −267 |
| 2026 | SPY | 15 | 40.0 | +4.01 | +6.03 | +90 |
| 2017 | all names | 66 | 25.8 | −3.67 | −2.04 | −135 |
| 2018 | all names | 126 | 42.9 | +3.02 | +3.59 | +453 |
| 2019 | all names | 77 | 29.9 | −5.58 | −5.70 | −439 |
| 2020 | all names | 105 | 38.1 | +1.82 | +3.62 | +380 |
| 2021 | all names | 107 | 34.6 | −2.37 | −3.28 | −351 |
| 2022 | all names | 82 | 31.7 | +0.40 | −1.51 | −124 |
| 2023 | all names | 87 | 41.4 | +2.15 | +3.10 | +270 |
| 2024 | all names | 61 | 42.6 | +4.74 | +9.17 | +559 |
| 2025 | all names | 63 | 54.0 | +8.43 | +27.35 | +1,723 |
| 2026 | all names | 44 | 38.6 | −0.21 | −5.36 | −236 |

![](charts/s7c.png)

**Amendments, deviations and integrity checks.** A cut-short pull is a uniform sample by strata (d706328).

**What it showed.** Indistinguishable from zero.

## #7d S09 Quick Scalps on SPXW 0DTE

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** 113cad7 / — / 7167541. **Dates:** 2026-10-14.

**Hypothesis.** The baseline on SPXW.

**Rule.** As S01, signals on SPX values with SPY volume.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO; SPXW per its fees

**Data.** SPXW 0DTE 2022-05-19 → 2026-10-08, 1,229 fills on 481 days.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** As S01.

**Verdict.** REJECTED: −$46.18 a contract [−63.19, −30.02], −$24 against matched random.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | 2022-05→2026-10 | 1,229 | 481 / 1,135 | 33.8 | +37.6, +316.91 | −25.1, −232.60 | −22.2, −142.26 | **−3.93**, −47.04 | [−5.60, −2.27]; [−63.75, −31.69] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | 2022-05→2026-10 | +1,482.74, +41.0%, 2025-04-09, SPXW 2025-04-09 5380.0CALL | −1,002.26, −40.6%, 2026-03-09, SPXW 2026-03-09 6640.0PUT | 0.69 | 58,726 | 1,135 | total ≤ 0 (best 5 days +8,061; without them −65,879) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $2.26). The study's fees are given beside them below. Re-pricing: exact (1,229 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | 2022-05→2026-10 | 1,229 | **−3.93**, −47.04 | −3.81, −46.18 | 33.8 / 33.8 | [−5.60, −2.27] / [−5.48, −2.15] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2022-05→2026-10: stop 52.7%; target_2 26.2%; vwap_loss 15.3%; time 3.3%; invalidation 2.4%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 159 | 27.7 | −7.55 | −92.48 | −14,704 |
| 2023 | SPXW | 300 | 34.3 | −3.60 | −30.08 | −9,023 |
| 2024 | SPXW | 279 | 37.6 | −1.33 | −16.66 | −4,648 |
| 2025 | SPXW | 266 | 33.8 | −5.45 | −59.79 | −15,904 |
| 2026 | SPXW | 225 | 32.4 | −3.24 | −60.17 | −13,539 |

![](charts/s7d.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Loses on SPXW too.

## #7e S10 Short premium: fade the Quick Scalps signal (single contract, 2× stop, to 15:50)

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A4 912b415 / rerun 1ecdfd5 / cf124a0, 3c8d6cb. **Dates:** 2026-10-14.

**Hypothesis.** Selling the contract the signal would buy earns its premium.

**Rule.** Sell the signal's contract at the bid, buy back at 15:50 or at a 2× credit stop (the best cell).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM 0DTE 2022-11 → 2026-10.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** Positive lower bound and better than random.

**Verdict.** Nothing promoted: breakeven at best (+$0.52 a contract).

**Metrics at Robinhood fees** (return = % of the credit received; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2022-11→2026-10 | 685 | 274 / 638 | 51.7 | +82.7, +49.31 | −102.2, −52.69 | +17.1, +8.90 | **−6.67**, +0.02 | [−17.08, +3.47]; [−5.57, +5.31] |
| QQQ | 2022-11→2026-10 | 1,075 | 421 / 1,009 | 56.3 | +73.9, +81.09 | −97.0, −102.74 | +26.2, +20.90 | **−0.84**, +0.72 | [−8.80, +8.60]; [−9.93, +12.06] |
| SPY | 2022-11→2026-10 | 1,126 | 444 / 1,009 | 57.1 | +74.7, +75.78 | −98.2, −91.64 | +34.6, +22.90 | **+0.55**, +3.97 | [−6.55, +7.56]; [−3.28, +11.71] |
| all names | 2022-11→2026-10 | 2,886 | 614 / 1,009 | 55.5 | +76.1, +71.94 | −98.8, −85.66 | +30.1, +18.90 | **−1.68**, +1.82 | [−7.80, +4.77]; [−4.24, +8.50] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2022-11→2026-10 | +186.90, +99.4%, 2025-04-09, IWM short 173.0PUT | −194.10, −106.6%, 2025-09-17, IWM short 241.0CALL | 1.00 | 2,829 | 362 | 7604% |
| QQQ | 2022-11→2026-10 | +419.90, +92.9%, 2025-04-07, QQQ short 417.0PUT | −425.10, −138.5%, 2026-06-09, QQQ short 692.0PUT | 1.02 | 7,141 | 244 | 515% |
| SPY | 2022-11→2026-10 | +456.90, +99.5%, 2025-04-09, SPY short 495.0PUT | −413.10, −101.0%, 2025-04-11, SPY short 527.0CALL | 1.10 | 3,022 | 358 | 78% |
| all names | 2022-11→2026-10 | +456.90, +99.5%, 2025-04-09, SPY short 495.0PUT | −425.10, −138.5%, 2026-06-09, QQQ short 692.0PUT | 1.05 | 8,737 | 358 | 135% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (2,886 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2022-11→2026-10 | 685 | **−6.67**, +0.02 | −9.63, −1.27 | 51.7 / 51.4 | [−17.08, +3.47] / [−20.09, +0.58] |
| QQQ | 2022-11→2026-10 | 1,075 | **−0.84**, +0.72 | −2.40, −0.58 | 56.3 / 56.3 | [−8.80, +8.60] / [−10.34, +7.08] |
| SPY | 2022-11→2026-10 | 1,126 | **+0.55**, +3.97 | −1.17, +2.67 | 57.1 / 57.1 | [−6.55, +7.56] / [−8.30, +5.93] |
| all names | 2022-11→2026-10 | 2,886 | **−1.68**, +1.82 | −3.63, +0.52 | 55.5 / 55.4 | [−7.80, +4.77] / [−9.79, +2.83] |

**Random baseline** (as the study computed it, at its own fees): the study's matched random controls (5 seeds, same symbols, sessions and exits, 14,218 trades): mean −5.71 dollars and −10.27% a trade (no percentile was computed).

**Exit reasons (share of trades):**

- 2022-11→2026-10: session_cutoff 61.9%; stop 38.1%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 157 | 56.1 | −0.78 | +1.38 | +217 |
| 2025 | IWM | 311 | 46.9 | −14.49 | −3.18 | −988 |
| 2026 | IWM | 217 | 55.3 | +0.28 | +3.63 | +788 |
| 2022 | QQQ | 34 | 67.6 | +23.21 | +20.99 | +714 |
| 2023 | QQQ | 293 | 53.9 | −0.91 | +0.49 | +144 |
| 2024 | QQQ | 287 | 59.6 | −0.15 | +4.20 | +1,205 |
| 2025 | QQQ | 241 | 59.3 | +3.89 | +9.16 | +2,209 |
| 2026 | QQQ | 220 | 50.0 | −10.54 | −15.91 | −3,501 |
| 2022 | SPY | 40 | 50.0 | −8.08 | −9.88 | −395 |
| 2023 | SPY | 285 | 58.9 | +6.11 | +6.91 | +1,968 |
| 2024 | SPY | 281 | 57.7 | −4.92 | +2.18 | +613 |
| 2025 | SPY | 282 | 58.2 | +2.96 | +7.35 | +2,073 |
| 2026 | SPY | 238 | 54.2 | −1.07 | +0.87 | +208 |
| 2022 | all names | 74 | 58.1 | +6.30 | +4.30 | +319 |
| 2023 | all names | 578 | 56.4 | +2.55 | +3.65 | +2,112 |
| 2024 | all names | 725 | 58.1 | −2.13 | +2.81 | +2,035 |
| 2025 | all names | 834 | 54.3 | −3.28 | +3.95 | +3,293 |
| 2026 | all names | 675 | 53.2 | −3.72 | −3.71 | −2,505 |

![](charts/s7e.png)

**Amendments, deviations and integrity checks.** The vertical rows were superseded after the protective-leg fix; the single-contract rows (shown) are unchanged.

**What it showed.** The fade is about breakeven.

## #7f S12 Intraday momentum: first-half-hour direction → 10:00–15:00 long option

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A5 fe93f87 / — / 2430c9b. **Dates:** 2026-10-14.

**Hypothesis.** The first half hour's direction continues (Gao et al.).

**Rule.** Buy the 0DTE contract in the first-half-hour direction at 10:00, exit 15:00.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM 2022-11 → 2026-10 (options).

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** Two-part promotion rule (A1).

**Verdict.** Nothing promoted (QQQ-only underlying effect, not batch-robust; option cell negative).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2022-11→2026-10 | 388 | 388 / 638 | 28.9 | +116.9, +42.41 | −69.3, −22.27 | −58.6, −13.60 | **−15.58**, −3.60 | [−26.74, −4.07]; [−7.74, +0.90] |
| QQQ | 2022-11→2026-10 | 920 | 920 / 1,010 | 31.3 | +96.5, +67.15 | −61.8, −35.44 | −42.3, −19.10 | **−12.22**, −3.32 | [−18.81, −6.00]; [−8.32, +1.98] |
| SPY | 2022-11→2026-10 | 906 | 906 / 1,010 | 31.8 | +98.5, +63.60 | −60.7, −33.41 | −40.0, −17.10 | **−10.10**, −2.57 | [−15.74, −2.87]; [−6.60, +2.60] |
| all names | 2022-11→2026-10 | 2,214 | 961 / 1,010 | 31.1 | +100.7, +61.64 | −62.7, −32.24 | −44.0, −17.10 | **−11.94**, −3.06 | [−17.27, −6.14]; [−6.83, +1.36] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2022-11→2026-10 | +371.90, +743.8%, 2026-07-29, IWM 293.0PUT | −108.10, −99.2%, 2024-09-18, IWM 222.0CALL | 0.77 | 1,852 | 465 | total ≤ 0 (best 5 days +1,190; without them −2,586) |
| QQQ | 2022-11→2026-10 | +1,188.88, +861.5%, 2026-07-29, QQQ 678.0PUT | −176.10, −77.9%, 2025-04-07, QQQ 424.0CALL | 0.86 | 5,106 | 1,008 | total ≤ 0 (best 5 days +3,418; without them −6,477) |
| SPY | 2022-11→2026-10 | +972.88, +299.3%, 2025-04-09, SPY 532.0CALL | −221.10, −97.4%, 2025-04-08, SPY 502.0CALL | 0.89 | 3,997 | 1,010 | total ≤ 0 (best 5 days +3,046; without them −5,377) |
| all names | 2022-11→2026-10 | +1,188.88, +861.5%, 2026-07-29, QQQ 678.0PUT | −221.10, −97.4%, 2025-04-08, SPY 502.0CALL | 0.86 | 10,128 | 1,010 | total ≤ 0 (best 5 days +7,114; without them −13,899) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (2,214 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2022-11→2026-10 | 388 | **−15.58**, −3.60 | −20.62, −4.90 | 28.9 / 28.1 | [−26.74, −4.07] / [−31.88, −9.17] |
| QQQ | 2022-11→2026-10 | 920 | **−12.22**, −3.32 | −14.88, −4.62 | 31.3 / 30.9 | [−18.81, −6.00] / [−21.50, −8.59] |
| SPY | 2022-11→2026-10 | 906 | **−10.10**, −2.57 | −12.89, −3.87 | 31.8 / 30.8 | [−15.74, −2.87] / [−18.58, −5.60] |
| all names | 2022-11→2026-10 | 2,214 | **−11.94**, −3.06 | −15.07, −4.36 | 31.1 / 30.4 | [−17.27, −6.14] / [−20.45, −9.22] |

**Random baseline** (as the study computed it, at its own fees): the study's matched random controls (5 seeds, same symbols, sessions and exits, 10,984 trades): mean −5.53 dollars and −14.32% a trade (no percentile was computed).

**Exit reasons (share of trades):**

- 2022-11→2026-10: session_cutoff 98.5%; settlement 1.5%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 98 | 31.6 | −8.90 | −0.11 | −11 |
| 2025 | IWM | 166 | 27.7 | −21.21 | −5.60 | −930 |
| 2026 | IWM | 124 | 28.2 | −13.31 | −3.67 | −455 |
| 2022 | QQQ | 31 | 16.1 | −23.64 | −14.29 | −443 |
| 2023 | QQQ | 225 | 31.1 | −22.55 | −9.79 | −2,204 |
| 2024 | QQQ | 236 | 28.4 | −16.18 | −7.05 | −1,664 |
| 2025 | QQQ | 239 | 33.1 | −7.83 | −0.00 | −1 |
| 2026 | QQQ | 189 | 35.4 | +1.33 | +6.63 | +1,253 |
| 2022 | SPY | 33 | 9.1 | −58.40 | −33.49 | −1,105 |
| 2023 | SPY | 217 | 27.6 | −13.59 | −6.22 | −1,351 |
| 2024 | SPY | 233 | 32.2 | −10.10 | −4.62 | −1,076 |
| 2025 | SPY | 236 | 32.6 | −8.48 | +0.79 | +186 |
| 2026 | SPY | 187 | 39.0 | +0.42 | +5.43 | +1,016 |
| 2022 | all names | 64 | 12.5 | −41.56 | −24.19 | −1,548 |
| 2023 | all names | 442 | 29.4 | −18.15 | −8.04 | −3,554 |
| 2024 | all names | 567 | 30.5 | −12.42 | −4.85 | −2,751 |
| 2025 | all names | 641 | 31.5 | −11.54 | −1.16 | −744 |
| 2026 | all names | 500 | 35.0 | −2.64 | +3.63 | +1,814 |

![](charts/s7f.png)

**Amendments, deviations and integrity checks.** seed 0 = the signal; 11–15 random.

**What it showed.** The option expression loses.

## #7g S12b 10:00 long option in the first-half-hour direction

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A5.1 b9b9206 / — / be991de. **Dates:** 2026-10-14.

**Hypothesis.** As S12 with the baseline rule's contract.

**Rule.** Buy the baseline-rule 0DTE contract at 10:00 in the first-half-hour direction; exit 15:00.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM 2022-11 → 2026-10.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** As S12.

**Verdict.** Nothing promoted: −$4.87 a contract [−14.18, +4.87].

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2022-11→2026-10 | 564 | 564 / 639 | 32.8 | +145.0, +111.15 | −81.1, −59.47 | −73.8, −40.10 | **−6.92**, −3.51 | [−17.17, +6.37]; [−12.57, +7.74] |
| QQQ | 2022-11→2026-10 | 964 | 964 / 1,010 | 33.0 | +148.6, +207.30 | −76.1, −108.99 | −60.9, −70.60 | **−2.01**, −4.66 | [−8.95, +4.98]; [−14.84, +5.37] |
| SPY | 2022-11→2026-10 | 971 | 971 / 1,010 | 34.6 | +144.1, +169.16 | −76.0, −93.39 | −59.6, −57.10 | **+0.18**, −2.54 | [−6.40, +7.45]; [−11.49, +9.04] |
| all names | 2022-11→2026-10 | 2,499 | 971 / 1,010 | 33.6 | +146.0, +170.82 | −77.2, −91.72 | −63.1, −54.10 | **−2.27**, −3.58 | [−8.13, +4.26]; [−11.65, +5.47] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2022-11→2026-10 | +859.88, +398.1%, 2025-04-09, IWM 176.0CALL | −180.09, −100.1%, 2025-04-23, IWM 194.0CALL | 0.91 | 3,136 | 249 | total ≤ 0 (best 5 days +3,049; without them −5,027) |
| QQQ | 2022-11→2026-10 | +2,478.84, +482.3%, 2025-04-09, QQQ 423.0CALL | −412.10, −99.5%, 2026-06-25, QQQ 704.0PUT | 0.94 | 6,199 | 980 | total ≤ 0 (best 5 days +6,404; without them −10,894) |
| SPY | 2022-11→2026-10 | +2,331.85, +411.3%, 2025-04-09, SPY 502.0CALL | −376.09, −100.0%, 2025-04-08, SPY 524.0CALL | 0.96 | 4,288 | 620 | total ≤ 0 (best 5 days +5,599; without them −8,068) |
| all names | 2022-11→2026-10 | +2,478.84, +482.3%, 2025-04-09, QQQ 423.0CALL | −412.10, −99.5%, 2026-06-25, QQQ 704.0PUT | 0.94 | 11,917 | 605 | total ≤ 0 (best 5 days +13,086; without them −22,022) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (2,499 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2022-11→2026-10 | 564 | **−6.92**, −3.51 | −8.94, −4.81 | 32.8 / 32.8 | [−17.17, +6.37] / [−19.12, +4.50] |
| QQQ | 2022-11→2026-10 | 964 | **−2.01**, −4.66 | −3.05, −5.96 | 33.0 / 32.7 | [−8.95, +4.98] / [−9.98, +4.00] |
| SPY | 2022-11→2026-10 | 971 | **+0.18**, −2.54 | −1.04, −3.84 | 34.6 / 34.4 | [−6.40, +7.45] / [−7.66, +6.24] |
| all names | 2022-11→2026-10 | 2,499 | **−2.27**, −3.58 | −3.60, −4.87 | 33.6 / 33.4 | [−8.13, +4.26] / [−9.45, +2.93] |

**Random baseline** (as the study computed it, at its own fees): the study's matched random controls (5 seeds, same symbols, sessions and exits, 12,446 trades): mean −11.99 dollars and −9.75% a trade (no percentile was computed).

**Exit reasons (share of trades):**

- 2022-11→2026-10: time 95.5%; settlement 4.5%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 144 | 29.9 | −15.19 | −9.30 | −1,339 |
| 2025 | IWM | 227 | 35.2 | +2.83 | +7.08 | +1,607 |
| 2026 | IWM | 193 | 32.1 | −12.22 | −11.63 | −2,245 |
| 2022 | QQQ | 31 | 45.2 | +16.56 | +23.03 | +714 |
| 2023 | QQQ | 247 | 30.8 | −8.73 | −9.31 | −2,299 |
| 2024 | QQQ | 248 | 32.7 | +3.88 | +1.17 | +290 |
| 2025 | QQQ | 246 | 33.7 | −2.72 | −2.96 | −727 |
| 2026 | QQQ | 192 | 33.3 | −3.05 | −12.85 | −2,467 |
| 2022 | SPY | 33 | 30.3 | −4.33 | −18.40 | −607 |
| 2023 | SPY | 248 | 33.5 | −5.80 | −4.91 | −1,218 |
| 2024 | SPY | 249 | 35.3 | +1.08 | −3.47 | −863 |
| 2025 | SPY | 247 | 37.7 | +6.98 | +12.87 | +3,178 |
| 2026 | SPY | 194 | 32.0 | −1.19 | −15.25 | −2,959 |
| 2022 | all names | 64 | 37.5 | +5.79 | +1.67 | +107 |
| 2023 | all names | 495 | 32.1 | −7.26 | −7.10 | −3,517 |
| 2024 | all names | 641 | 33.1 | −1.50 | −2.98 | −1,913 |
| 2025 | all names | 720 | 35.6 | +2.35 | +5.64 | +4,058 |
| 2026 | all names | 579 | 32.5 | −5.48 | −13.25 | −7,671 |

![](charts/s7g.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Negative.

## #7h S15 VRP-conditioned 10:00 short ATM 0DTE straddle (unconditional row)

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A5 6dfba60 / — / 6ed12b6. **Dates:** 2026-10-14.

**Hypothesis.** Rich implied vs trailing realised volatility marks sellable straddles.

**Rule.** Sell the 10:00 ATM straddle at the bids, buy back at 15:50 at the asks.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ 0DTE, 970/971 sessions 2022-11 → 2026-10.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** A conditioned cell with a positive lower bound.

**Verdict.** Nothing promoted: unconditional −$15.46 a straddle [−32.68, +0.29]; rich implied forecasts large moves.

**Metrics at Robinhood fees** (return = % of the credit received; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | 2022-11→2026-10 | 971 | 971 / 1,010 | 58.4 | +44.8, +146.03 | −73.9, −235.27 | +14.9, +43.80 | **−4.60**, −12.62 | [−9.49, −0.07]; [−32.26, +3.85] |
| SPY | 2022-11→2026-10 | 970 | 970 / 1,010 | 58.0 | +44.0, +123.56 | −71.4, −202.13 | +14.9, +38.80 | **−4.40**, −13.10 | [−8.87, −0.60]; [−31.42, +0.76] |
| all names | 2022-11→2026-10 | 1,941 | 971 / 1,010 | 58.2 | +44.4, +134.83 | −72.6, −218.64 | +14.9, +41.80 | **−4.50**, −12.86 | [−8.99, −0.44]; [−31.36, +1.76] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | 2022-11→2026-10 | +662.80, +76.0%, 2024-08-05, QQQ 10:00 short straddle 433.0 | −3,321.22, −278.9%, 2025-04-09, QQQ 10:00 short straddle 421.0 | 0.87 | 17,201 | 1,003 | total ≤ 0 (best 5 days +2,665; without them −14,915) |
| SPY | 2022-11→2026-10 | +660.80, +76.5%, 2024-08-05, SPY 10:00 short straddle 515.0 | −3,097.22, −230.6%, 2025-04-09, SPY 10:00 short straddle 500.0 | 0.85 | 14,929 | 999 | total ≤ 0 (best 5 days +2,528; without them −15,233) |
| all names | 2022-11→2026-10 | +662.80, +76.0%, 2024-08-05, QQQ 10:00 short straddle 433.0 | −3,321.22, −278.9%, 2025-04-09, QQQ 10:00 short straddle 421.0 | 0.86 | 31,025 | 1,003 | total ≤ 0 (best 5 days +5,081; without them −30,037) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.80 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (1,941 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | 2022-11→2026-10 | 971 | **−4.60**, −12.62 | −5.49, −15.22 | 58.4 / 58.1 | [−9.49, −0.07] / [−10.37, −0.97] |
| SPY | 2022-11→2026-10 | 970 | **−4.40**, −13.10 | −5.44, −15.70 | 58.0 / 57.9 | [−8.87, −0.60] / [−9.91, −1.65] |
| all names | 2022-11→2026-10 | 1,941 | **−4.50**, −12.86 | −5.47, −15.46 | 58.2 / 58.0 | [−8.99, −0.44] / [−9.93, −1.42] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2022-11→2026-10: bought back 15:50 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | QQQ | 33 | 45.5 | −14.07 | −37.63 | −1,242 |
| 2023 | QQQ | 248 | 52.0 | −10.88 | −21.56 | −5,346 |
| 2024 | QQQ | 249 | 63.5 | +1.61 | +6.15 | +1,531 |
| 2025 | QQQ | 247 | 59.1 | −6.33 | −29.53 | −7,293 |
| 2026 | QQQ | 194 | 61.3 | −0.73 | +0.51 | +99 |
| 2022 | SPY | 33 | 51.5 | −5.42 | −13.26 | −438 |
| 2023 | SPY | 248 | 57.3 | −5.28 | −7.76 | −1,924 |
| 2024 | SPY | 248 | 63.7 | −0.01 | +0.38 | +94 |
| 2025 | SPY | 247 | 55.1 | −6.93 | −30.65 | −7,570 |
| 2026 | SPY | 194 | 56.7 | −5.48 | −14.78 | −2,868 |
| 2022 | all names | 66 | 48.5 | −9.74 | −25.44 | −1,679 |
| 2023 | all names | 496 | 54.6 | −8.08 | −14.66 | −7,270 |
| 2024 | all names | 497 | 63.6 | +0.80 | +3.27 | +1,625 |
| 2025 | all names | 494 | 57.1 | −6.63 | −30.09 | −14,863 |
| 2026 | all names | 388 | 59.0 | −3.11 | −7.14 | −2,769 |

![](charts/s7h.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** The 10:00 short straddle loses.

## #7i S16b Prior-day fade with a weekly contract (time exit)

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A5 fe93f87 / — / 5cabc13, 3c8d6cb. **Dates:** 2026-10-14.

**Hypothesis.** The prior session's close-to-close move reverses.

**Rule.** Buy the weekly contract against the prior move at the 09:31 close; time exit.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO

**Data.** SPY/QQQ/IWM weekly chains 2017-06 → 2026-10.

**Periods and holdouts.** Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).

**Pass rule (as pre-registered).** As S12.

**Verdict.** Nothing promoted: −$9.91 a contract [−19.31, −0.26].

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | 2017-06→2026-10 | 287 | 287 / 2,411 | 36.9 | +48.1, +77.16 | −41.2, −64.72 | −16.8, −22.10 | **−8.24**, −12.32 | [−13.81, −2.14]; [−21.52, −2.43] |
| QQQ | 2017-06→2026-10 | 290 | 290 / 2,411 | 38.6 | +46.5, +134.39 | −40.9, −104.20 | −13.6, −27.60 | **−7.16**, −12.06 | [−12.80, −1.26]; [−29.31, +6.13] |
| SPY | 2017-06→2026-10 | 464 | 464 / 2,419 | 38.4 | +58.1, +132.32 | −42.2, −89.11 | −14.6, −23.10 | **−3.74**, −4.17 | [−10.96, +2.56]; [−19.85, +10.79] |
| all names | 2017-06→2026-10 | 1,041 | 699 / 2,419 | 38.0 | +52.1, +118.14 | −41.6, −86.43 | −14.9, −24.10 | **−5.93**, −8.61 | [−10.19, −2.31]; [−17.65, +0.82] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | 2017-06→2026-10 | +376.89, +221.7%, 2026-05-20, IWM 275.0CALL | −277.10, −72.5%, 2025-04-08, IWM 186.0CALL | 0.70 | 3,902 | 1,453 | total ≤ 0 (best 5 days +1,240; without them −4,775) |
| QQQ | 2017-06→2026-10 | +1,175.86, +123.8%, 2025-04-08, QQQ 435.0PUT | −444.10, −65.9%, 2026-06-12, QQQ 713.0PUT | 0.81 | 3,518 | 2,362 | total ≤ 0 (best 5 days +2,972; without them −6,469) |
| SPY | 2017-06→2026-10 | +1,275.87, +405.0%, 2022-10-13, SPY 350.0CALL | −415.10, −89.7%, 2022-05-04, SPY 415.0PUT | 0.92 | 4,102 | 1,484 | total ≤ 0 (best 5 days +4,195; without them −6,129) |
| all names | 2017-06→2026-10 | +1,275.87, +405.0%, 2022-10-13, SPY 350.0CALL | −444.10, −65.9%, 2026-06-12, QQQ 713.0PUT | 0.84 | 9,949 | 2,388 | total ≤ 0 (best 5 days +4,600; without them −13,565) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (1,041 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | 2017-06→2026-10 | 287 | **−8.24**, −12.32 | −9.21, −13.62 | 36.9 / 36.6 | [−13.81, −2.14] / [−14.76, −3.11] |
| QQQ | 2017-06→2026-10 | 290 | **−7.16**, −12.06 | −7.85, −13.36 | 38.6 / 38.3 | [−12.80, −1.26] / [−13.53, −1.97] |
| SPY | 2017-06→2026-10 | 464 | **−3.74**, −4.17 | −4.60, −5.46 | 38.4 / 38.1 | [−10.96, +2.56] / [−11.77, +1.69] |
| all names | 2017-06→2026-10 | 1,041 | **−5.93**, −8.61 | −6.78, −9.91 | 38.0 / 37.8 | [−10.19, −2.31] / [−11.05, −3.10] |

**Random baseline** (as the study computed it, at its own fees): the study's matched random controls (5 seeds, same symbols, sessions and exits, 5,218 trades): mean −9.80 dollars and −4.48% a trade (no percentile was computed).

**Exit reasons (share of trades):**

- 2017-06→2026-10: data_end 88.1%; time 11.9%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2017 | IWM | 16 | 18.8 | −27.60 | −16.66 | −267 |
| 2018 | IWM | 30 | 50.0 | +9.17 | +7.30 | +219 |
| 2019 | IWM | 32 | 37.5 | −2.93 | −0.54 | −17 |
| 2020 | IWM | 28 | 42.9 | −1.08 | +0.04 | +1 |
| 2021 | IWM | 31 | 38.7 | −14.71 | −22.94 | −711 |
| 2022 | IWM | 32 | 50.0 | −0.39 | +6.56 | +210 |
| 2023 | IWM | 31 | 38.7 | −1.68 | −6.07 | −188 |
| 2024 | IWM | 31 | 29.0 | −15.08 | −25.33 | −785 |
| 2025 | IWM | 32 | 21.9 | −30.49 | −52.63 | −1,684 |
| 2026 | IWM | 24 | 33.3 | −4.60 | −13.02 | −312 |
| 2017 | QQQ | 17 | 23.5 | −19.87 | −8.04 | −137 |
| 2018 | QQQ | 31 | 32.3 | −17.10 | −20.42 | −633 |
| 2019 | QQQ | 31 | 32.3 | −7.11 | −5.58 | −173 |
| 2020 | QQQ | 30 | 46.7 | +1.84 | −11.83 | −355 |
| 2021 | QQQ | 31 | 38.7 | −8.57 | −16.88 | −523 |
| 2022 | QQQ | 32 | 43.8 | −1.23 | +1.15 | +37 |
| 2023 | QQQ | 31 | 38.7 | −1.89 | +1.51 | +47 |
| 2024 | QQQ | 31 | 38.7 | −7.38 | −24.20 | −750 |
| 2025 | QQQ | 32 | 40.6 | −10.12 | −12.01 | −384 |
| 2026 | QQQ | 24 | 45.8 | −5.25 | −26.02 | −625 |
| 2017 | SPY | 58 | 44.8 | +2.02 | +0.59 | +34 |
| 2018 | SPY | 62 | 33.9 | −20.01 | −25.44 | −1,577 |
| 2019 | SPY | 64 | 34.4 | +6.00 | +10.41 | +667 |
| 2020 | SPY | 60 | 45.0 | +1.73 | +17.46 | +1,048 |
| 2021 | SPY | 64 | 29.7 | −10.06 | −12.65 | −809 |
| 2022 | SPY | 37 | 40.5 | −3.28 | −19.86 | −735 |
| 2023 | SPY | 32 | 34.4 | −14.53 | −40.44 | −1,294 |
| 2024 | SPY | 31 | 35.5 | −8.14 | −23.36 | −724 |
| 2025 | SPY | 31 | 48.4 | +9.03 | +34.12 | +1,058 |
| 2026 | SPY | 25 | 44.0 | +4.15 | +16.02 | +400 |
| 2017 | all names | 91 | 36.3 | −7.27 | −4.06 | −369 |
| 2018 | all names | 123 | 37.4 | −12.16 | −16.19 | −1,991 |
| 2019 | all names | 127 | 34.6 | +0.55 | +3.75 | +476 |
| 2020 | all names | 118 | 44.9 | +1.09 | +5.88 | +694 |
| 2021 | all names | 126 | 34.1 | −10.84 | −16.22 | −2,044 |
| 2022 | all names | 101 | 44.6 | −1.71 | −4.84 | −488 |
| 2023 | all names | 94 | 37.2 | −6.13 | −15.27 | −1,435 |
| 2024 | all names | 93 | 34.4 | −10.20 | −24.29 | −2,259 |
| 2025 | all names | 95 | 36.8 | −10.73 | −10.64 | −1,011 |
| 2026 | all names | 73 | 41.1 | −1.82 | −7.35 | −537 |

![](charts/s7i.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Negative.

## #7j-atm_put S17 Index put-writing: monthly ATM cash-secured put

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A7 c81522a / wording 9ea4adf / 5e7e1bd. **Dates:** 2026-10-15.

**Hypothesis.** Index put-writing earns the variance risk premium (Cboe PUT).

**Rule.** Sell the standard monthly ATM put at the bid at expiry roll, hold to expiration, cash-secured.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Bid in; settlement out; $0.70 a contract.

**Data.** SPY and QQQ standard monthlies 2012-06 → 2026-10.

**Periods and holdouts.** One span (2012–2026); no holdout.

**Pass rule (as pre-registered).** A7 carry-lane rule (positive mean with a positive lower bound per cell).

**Verdict.** PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 against the index, crash risk stated (a carry lane, not an edge).

**Metrics at Robinhood fees** (return = % of the cash set aside; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | 2012-06→2026-10 | 167 | 167 / 3,633 | 80.2 | +1.9, +496.48 | −4.0, −1,003.19 | +1.6, +216.94 | **+0.72**, +200.14 | [+0.21, +1.16]; [+57.42, +322.89] |
| SPY | 2012-06→2026-10 | 167 | 166 / 3,633 | 82.6 | +1.5, +527.73 | −3.9, −1,353.39 | +1.2, +330.94 | **+0.59**, +201.07 | [+0.08, +1.01]; [+20.70, +347.85] |
| all names | 2012-06→2026-10 | 334 | 167 / 3,633 | 81.4 | +1.7, +512.34 | −4.0, −1,166.99 | +1.4, +267.94 | **+0.66**, +200.60 | [+0.17, +1.08]; [+42.50, +333.89] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | 2012-06→2026-10 | +2,117.90, +3.0%, 2026-07-17, QQQ 2026-08-21 695.0 | −5,456.06, −23.7%, 2020-02-21, QQQ 2020-03-20 230.0 | 2.01 | 7,613 | 581 | 24% |
| SPY | 2012-06→2026-10 | +1,693.91, +2.3%, 2026-05-15, SPY 2026-07-17 735.0 | −9,870.07, −29.6%, 2020-02-21, SPY 2020-03-20 333.0 | 1.86 | 9,870 | 586 | 22% |
| all names | 2012-06→2026-10 | +2,117.90, +3.0%, 2026-07-17, QQQ 2026-08-21 695.0 | −9,870.07, −29.6%, 2020-02-21, SPY 2020-03-20 333.0 | 1.93 | 15,326 | 581 | 23% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.07). The study's fees are given beside them below. Re-pricing: exact (334 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | 2012-06→2026-10 | 167 | **+0.72**, +200.14 | +0.72, +198.81 | 80.2 / 80.2 | [+0.21, +1.16] / [+0.20, +1.16] |
| SPY | 2012-06→2026-10 | 167 | **+0.59**, +201.07 | +0.59, +199.73 | 82.6 / 82.6 | [+0.08, +1.01] / [+0.07, +1.01] |
| all names | 2012-06→2026-10 | 334 | **+0.66**, +200.60 | +0.65, +199.27 | 81.4 / 81.4 | [+0.17, +1.08] / [+0.16, +1.07] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2012-06→2026-10: held to expiration 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | QQQ | 7 | 71.4 | +0.33 | +16.44 | +115 |
| 2013 | QQQ | 12 | 91.7 | +0.89 | +65.65 | +788 |
| 2014 | QQQ | 12 | 75.0 | +0.45 | +37.06 | +445 |
| 2015 | QQQ | 12 | 66.7 | −0.14 | −23.69 | −284 |
| 2016 | QQQ | 12 | 91.7 | +1.41 | +153.48 | +1,842 |
| 2017 | QQQ | 12 | 91.7 | +1.06 | +147.61 | +1,771 |
| 2018 | QQQ | 12 | 66.7 | −0.20 | −43.56 | −523 |
| 2019 | QQQ | 11 | 90.9 | +1.58 | +292.21 | +3,214 |
| 2020 | QQQ | 12 | 83.3 | +0.72 | +184.26 | +2,211 |
| 2021 | QQQ | 12 | 66.7 | +0.33 | +76.59 | +919 |
| 2022 | QQQ | 11 | 54.5 | −0.51 | −240.35 | −2,644 |
| 2023 | QQQ | 12 | 83.3 | +1.32 | +424.18 | +5,090 |
| 2024 | QQQ | 12 | 91.7 | +1.31 | +617.35 | +7,408 |
| 2025 | QQQ | 11 | 90.9 | +1.09 | +611.29 | +6,724 |
| 2026 | QQQ | 7 | 85.7 | +1.33 | +906.63 | +6,346 |
| 2012 | SPY | 7 | 71.4 | +0.75 | +100.37 | +703 |
| 2013 | SPY | 12 | 83.3 | +0.71 | +115.86 | +1,390 |
| 2014 | SPY | 12 | 83.3 | +0.53 | +96.36 | +1,156 |
| 2015 | SPY | 12 | 83.3 | +0.30 | +57.48 | +690 |
| 2016 | SPY | 12 | 91.7 | +1.25 | +254.36 | +3,052 |
| 2017 | SPY | 12 | 91.7 | +0.71 | +172.48 | +2,070 |
| 2018 | SPY | 12 | 66.7 | −0.53 | −158.98 | −1,908 |
| 2019 | SPY | 11 | 90.9 | +1.18 | +340.03 | +3,740 |
| 2020 | SPY | 12 | 83.3 | +0.02 | −76.32 | −916 |
| 2021 | SPY | 12 | 83.3 | +1.18 | +475.68 | +5,708 |
| 2022 | SPY | 11 | 63.6 | −0.32 | −182.12 | −2,003 |
| 2023 | SPY | 12 | 75.0 | +0.48 | +190.18 | +2,282 |
| 2024 | SPY | 12 | 91.7 | +1.05 | +579.10 | +6,949 |
| 2025 | SPY | 11 | 90.9 | +0.95 | +601.20 | +6,613 |
| 2026 | SPY | 7 | 85.7 | +0.80 | +578.78 | +4,051 |
| 2012 | all names | 14 | 71.4 | +0.54 | +58.40 | +818 |
| 2013 | all names | 24 | 87.5 | +0.80 | +90.75 | +2,178 |
| 2014 | all names | 24 | 79.2 | +0.49 | +66.71 | +1,601 |
| 2015 | all names | 24 | 75.0 | +0.08 | +16.90 | +406 |
| 2016 | all names | 24 | 91.7 | +1.33 | +203.92 | +4,894 |
| 2017 | all names | 24 | 91.7 | +0.88 | +160.04 | +3,841 |
| 2018 | all names | 24 | 66.7 | −0.37 | −101.27 | −2,430 |
| 2019 | all names | 22 | 90.9 | +1.38 | +316.12 | +6,955 |
| 2020 | all names | 24 | 83.3 | +0.37 | +53.97 | +1,295 |
| 2021 | all names | 24 | 75.0 | +0.75 | +276.14 | +6,627 |
| 2022 | all names | 22 | 59.1 | −0.42 | −211.24 | −4,647 |
| 2023 | all names | 24 | 79.2 | +0.90 | +307.18 | +7,372 |
| 2024 | all names | 24 | 91.7 | +1.18 | +598.22 | +14,357 |
| 2025 | all names | 22 | 90.9 | +1.02 | +606.24 | +13,337 |
| 2026 | all names | 14 | 85.7 | +1.07 | +742.70 | +10,398 |

![](charts/s7j-atm_put.png)

**Amendments, deviations and integrity checks.** Covered calls not significantly negative (9ea4adf).

**What it showed.** Put-writing earned its premium like the index it is short; a carry, not an edge.

## #7j-put_30d S17 Index put-writing: monthly 0.30-delta cash-secured put

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A7 c81522a / wording 9ea4adf / 5e7e1bd. **Dates:** 2026-10-15.

**Hypothesis.** Index put-writing earns the variance risk premium (Cboe PUT).

**Rule.** Sell the standard monthly 0.30-delta put at the bid at expiry roll, hold to expiration, cash-secured.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Bid in; settlement out; $0.70 a contract.

**Data.** SPY and QQQ standard monthlies 2012-06 → 2026-10.

**Periods and holdouts.** One span (2012–2026); no holdout.

**Pass rule (as pre-registered).** A7 carry-lane rule (positive mean with a positive lower bound per cell).

**Verdict.** PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 against the index, crash risk stated (a carry lane, not an edge).

**Metrics at Robinhood fees** (return = % of the cash set aside; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | 2012-06→2026-10 | 167 | 167 / 3,633 | 85.6 | +1.2, +318.38 | −3.7, −833.96 | +1.0, +156.94 | **+0.52**, +152.78 | [+0.12, +0.86]; [+44.84, +240.05] |
| SPY | 2012-06→2026-10 | 167 | 166 / 3,633 | 85.6 | +1.0, +338.50 | −3.3, −1,090.06 | +0.8, +223.94 | **+0.40**, +133.20 | [−0.07, +0.73]; [−21.54, +242.25] |
| all names | 2012-06→2026-10 | 334 | 167 / 3,633 | 85.6 | +1.1, +328.44 | −3.5, −962.01 | +0.9, +186.94 | **+0.46**, +142.99 | [+0.03, +0.79]; [+16.36, +239.59] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | 2012-06→2026-10 | +1,427.92, +2.1%, 2026-05-15, QQQ 2026-07-17 675.0 | −5,030.06, −22.5%, 2020-02-21, QQQ 2020-03-20 224.0 | 2.27 | 5,030 | 368 | 21% |
| SPY | 2012-06→2026-10 | +1,116.92, +1.6%, 2026-05-15, SPY 2026-07-17 715.0 | −9,370.06, −28.7%, 2020-02-21, SPY 2020-03-20 326.0 | 1.85 | 9,370 | 408 | 20% |
| all names | 2012-06→2026-10 | +1,427.92, +2.1%, 2026-05-15, QQQ 2026-07-17 675.0 | −9,370.06, −28.7%, 2020-02-21, SPY 2020-03-20 326.0 | 2.03 | 14,400 | 343 | 21% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.06). The study's fees are given beside them below. Re-pricing: exact (334 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | 2012-06→2026-10 | 167 | **+0.52**, +152.78 | +0.51, +151.44 | 85.6 / 85.6 | [+0.12, +0.86] / [+0.11, +0.86] |
| SPY | 2012-06→2026-10 | 167 | **+0.40**, +133.20 | +0.40, +131.86 | 85.6 / 85.6 | [−0.07, +0.73] / [−0.08, +0.72] |
| all names | 2012-06→2026-10 | 334 | **+0.46**, +142.99 | +0.46, +141.65 | 85.6 / 85.6 | [+0.03, +0.79] / [+0.02, +0.79] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2012-06→2026-10: held to expiration 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | QQQ | 7 | 71.4 | +0.11 | +2.87 | +20 |
| 2013 | QQQ | 12 | 91.7 | +0.52 | +37.81 | +454 |
| 2014 | QQQ | 12 | 75.0 | +0.33 | +26.81 | +322 |
| 2015 | QQQ | 12 | 75.0 | −0.20 | −27.69 | −332 |
| 2016 | QQQ | 12 | 91.7 | +0.99 | +105.69 | +1,268 |
| 2017 | QQQ | 12 | 100.0 | +0.78 | +107.86 | +1,294 |
| 2018 | QQQ | 12 | 75.0 | −0.06 | −15.31 | −184 |
| 2019 | QQQ | 11 | 100.0 | +1.11 | +199.94 | +2,199 |
| 2020 | QQQ | 12 | 83.3 | −0.09 | −14.57 | −175 |
| 2021 | QQQ | 12 | 75.0 | +0.58 | +176.10 | +2,113 |
| 2022 | QQQ | 11 | 81.8 | +0.18 | −11.70 | −129 |
| 2023 | QQQ | 12 | 83.3 | +0.87 | +275.69 | +3,308 |
| 2024 | QQQ | 12 | 91.7 | +0.88 | +402.18 | +4,826 |
| 2025 | QQQ | 11 | 90.9 | +0.75 | +420.93 | +4,630 |
| 2026 | QQQ | 7 | 100.0 | +1.32 | +842.50 | +5,897 |
| 2012 | SPY | 7 | 85.7 | +0.66 | +88.80 | +622 |
| 2013 | SPY | 12 | 83.3 | +0.49 | +78.69 | +944 |
| 2014 | SPY | 12 | 91.7 | +0.39 | +70.69 | +848 |
| 2015 | SPY | 12 | 83.3 | +0.23 | +42.94 | +515 |
| 2016 | SPY | 12 | 91.7 | +0.88 | +176.73 | +2,121 |
| 2017 | SPY | 12 | 91.7 | +0.55 | +132.02 | +1,584 |
| 2018 | SPY | 12 | 66.7 | −0.45 | −129.56 | −1,555 |
| 2019 | SPY | 11 | 90.9 | +0.81 | +229.12 | +2,520 |
| 2020 | SPY | 12 | 91.7 | −0.71 | −292.32 | −3,508 |
| 2021 | SPY | 12 | 91.7 | +0.99 | +401.44 | +4,817 |
| 2022 | SPY | 11 | 72.7 | +0.09 | −3.98 | −44 |
| 2023 | SPY | 12 | 75.0 | +0.36 | +140.69 | +1,688 |
| 2024 | SPY | 12 | 91.7 | +0.70 | +374.52 | +4,494 |
| 2025 | SPY | 11 | 90.9 | +0.63 | +393.57 | +4,329 |
| 2026 | SPY | 7 | 85.7 | +0.58 | +409.50 | +2,866 |
| 2012 | all names | 14 | 78.6 | +0.38 | +45.83 | +642 |
| 2013 | all names | 24 | 87.5 | +0.50 | +58.25 | +1,398 |
| 2014 | all names | 24 | 83.3 | +0.36 | +48.75 | +1,170 |
| 2015 | all names | 24 | 79.2 | +0.01 | +7.63 | +183 |
| 2016 | all names | 24 | 91.7 | +0.93 | +141.21 | +3,389 |
| 2017 | all names | 24 | 95.8 | +0.67 | +119.94 | +2,879 |
| 2018 | all names | 24 | 70.8 | −0.26 | −72.44 | −1,738 |
| 2019 | all names | 22 | 95.5 | +0.96 | +214.53 | +4,720 |
| 2020 | all names | 24 | 87.5 | −0.40 | −153.44 | −3,683 |
| 2021 | all names | 24 | 83.3 | +0.79 | +288.77 | +6,930 |
| 2022 | all names | 22 | 77.3 | +0.13 | −7.84 | −173 |
| 2023 | all names | 24 | 79.2 | +0.62 | +208.19 | +4,997 |
| 2024 | all names | 24 | 91.7 | +0.79 | +388.35 | +9,320 |
| 2025 | all names | 22 | 90.9 | +0.69 | +407.25 | +8,959 |
| 2026 | all names | 14 | 92.9 | +0.95 | +626.00 | +8,764 |

![](charts/s7j-put_30d.png)

**Amendments, deviations and integrity checks.** Covered calls not significantly negative (9ea4adf).

**What it showed.** Put-writing earned its premium like the index it is short; a carry, not an edge.

## #7j-put_15d S17 Index put-writing: monthly 0.15-delta cash-secured put

**Folder:** `research/compass/studies/, results/v1/ (@7dfea57)`. **Commits:** A7 c81522a / wording 9ea4adf / 5e7e1bd. **Dates:** 2026-10-15.

**Hypothesis.** Index put-writing earns the variance risk premium (Cboe PUT).

**Rule.** Sell the standard monthly 0.15-delta put at the bid at expiry roll, hold to expiration, cash-secured.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Bid in; settlement out; $0.70 a contract.

**Data.** SPY and QQQ standard monthlies 2012-06 → 2026-10.

**Periods and holdouts.** One span (2012–2026); no holdout.

**Pass rule (as pre-registered).** A7 carry-lane rule (positive mean with a positive lower bound per cell).

**Verdict.** PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 against the index, crash risk stated (a carry lane, not an edge).

**Metrics at Robinhood fees** (return = % of the cash set aside; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | 2012-06→2026-10 | 167 | 167 / 3,633 | 93.4 | +0.6, +151.92 | −3.9, −780.51 | +0.5, +86.94 | **+0.31**, +90.50 | [−0.01, +0.52]; [+20.03, +138.63] |
| SPY | 2012-06→2026-10 | 167 | 166 / 3,633 | 94.6 | +0.5, +160.77 | −4.6, −1,389.73 | +0.4, +114.94 | **+0.22**, +77.21 | [−0.18, +0.45]; [−47.55, +149.04] |
| all names | 2012-06→2026-10 | 334 | 167 / 3,633 | 94.0 | +0.5, +156.37 | −4.2, −1,054.66 | +0.5, +107.44 | **+0.27**, +83.86 | [−0.09, +0.48]; [−14.32, +142.48] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | 2012-06→2026-10 | +719.93, +1.1%, 2026-05-15, QQQ 2026-07-17 635.0 | −4,190.06, −19.6%, 2020-02-21, QQQ 2020-03-20 214.0 | 2.76 | 4,190 | 388 | 17% |
| SPY | 2012-06→2026-10 | +528.93, +0.8%, 2026-05-15, SPY 2026-07-17 675.0 | −8,445.06, −26.8%, 2020-02-21, SPY 2020-03-20 315.0 | 2.03 | 8,520 | 1,336 | 17% |
| all names | 2012-06→2026-10 | +719.93, +1.1%, 2026-05-15, QQQ 2026-07-17 635.0 | −8,445.06, −26.8%, 2020-02-21, SPY 2020-03-20 315.0 | 2.33 | 12,635 | 776 | 17% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.06). The study's fees are given beside them below. Re-pricing: exact (334 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | 2012-06→2026-10 | 167 | **+0.31**, +90.50 | +0.30, +89.16 | 93.4 / 93.4 | [−0.01, +0.52] / [−0.01, +0.51] |
| SPY | 2012-06→2026-10 | 167 | **+0.22**, +77.21 | +0.22, +75.87 | 94.6 / 94.6 | [−0.18, +0.45] / [−0.19, +0.45] |
| all names | 2012-06→2026-10 | 334 | **+0.27**, +83.86 | +0.26, +82.52 | 94.0 / 94.0 | [−0.09, +0.48] / [−0.10, +0.47] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2012-06→2026-10: held to expiration 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | QQQ | 7 | 85.7 | +0.18 | +9.23 | +65 |
| 2013 | QQQ | 12 | 91.7 | +0.32 | +22.65 | +272 |
| 2014 | QQQ | 12 | 91.7 | +0.18 | +14.27 | +171 |
| 2015 | QQQ | 12 | 83.3 | −0.05 | −8.19 | −98 |
| 2016 | QQQ | 12 | 100.0 | +0.52 | +53.77 | +645 |
| 2017 | QQQ | 12 | 100.0 | +0.38 | +51.44 | +617 |
| 2018 | QQQ | 12 | 83.3 | +0.18 | +27.77 | +333 |
| 2019 | QQQ | 11 | 100.0 | +0.54 | +94.67 | +1,041 |
| 2020 | QQQ | 12 | 91.7 | −0.68 | −143.14 | −1,718 |
| 2021 | QQQ | 12 | 100.0 | +0.72 | +232.52 | +2,790 |
| 2022 | QQQ | 11 | 81.8 | +0.14 | +13.76 | +151 |
| 2023 | QQQ | 12 | 100.0 | +0.58 | +184.11 | +2,209 |
| 2024 | QQQ | 12 | 100.0 | +0.52 | +229.77 | +2,757 |
| 2025 | QQQ | 11 | 90.9 | +0.46 | +243.03 | +2,673 |
| 2026 | QQQ | 7 | 100.0 | +0.76 | +457.65 | +3,204 |
| 2012 | SPY | 7 | 100.0 | +0.46 | +60.51 | +424 |
| 2013 | SPY | 12 | 100.0 | +0.36 | +56.52 | +678 |
| 2014 | SPY | 12 | 91.7 | +0.21 | +36.61 | +439 |
| 2015 | SPY | 12 | 91.7 | +0.24 | +43.27 | +519 |
| 2016 | SPY | 12 | 100.0 | +0.45 | +88.52 | +1,062 |
| 2017 | SPY | 12 | 100.0 | +0.31 | +72.69 | +872 |
| 2018 | SPY | 12 | 83.3 | −0.23 | −64.23 | −771 |
| 2019 | SPY | 11 | 100.0 | +0.45 | +124.67 | +1,371 |
| 2020 | SPY | 12 | 91.7 | −1.37 | −471.06 | −5,653 |
| 2021 | SPY | 12 | 100.0 | +0.60 | +235.77 | +2,829 |
| 2022 | SPY | 11 | 81.8 | +0.37 | +124.39 | +1,368 |
| 2023 | SPY | 12 | 91.7 | +0.40 | +158.36 | +1,900 |
| 2024 | SPY | 12 | 100.0 | +0.39 | +200.44 | +2,405 |
| 2025 | SPY | 11 | 90.9 | +0.44 | +260.30 | +2,863 |
| 2026 | SPY | 7 | 100.0 | +0.56 | +369.22 | +2,585 |
| 2012 | all names | 14 | 92.9 | +0.32 | +34.87 | +488 |
| 2013 | all names | 24 | 95.8 | +0.34 | +39.59 | +950 |
| 2014 | all names | 24 | 91.7 | +0.20 | +25.44 | +611 |
| 2015 | all names | 24 | 87.5 | +0.10 | +17.54 | +421 |
| 2016 | all names | 24 | 100.0 | +0.49 | +71.15 | +1,708 |
| 2017 | all names | 24 | 100.0 | +0.35 | +62.06 | +1,490 |
| 2018 | all names | 24 | 83.3 | −0.03 | −18.23 | −437 |
| 2019 | all names | 22 | 100.0 | +0.50 | +109.67 | +2,413 |
| 2020 | all names | 24 | 91.7 | −1.02 | −307.10 | −7,370 |
| 2021 | all names | 24 | 100.0 | +0.66 | +234.15 | +5,620 |
| 2022 | all names | 22 | 81.8 | +0.25 | +69.08 | +1,520 |
| 2023 | all names | 24 | 95.8 | +0.49 | +171.23 | +4,110 |
| 2024 | all names | 24 | 100.0 | +0.45 | +215.11 | +5,163 |
| 2025 | all names | 22 | 90.9 | +0.45 | +251.67 | +5,537 |
| 2026 | all names | 14 | 100.0 | +0.66 | +413.44 | +5,788 |

![](charts/s7j-put_15d.png)

**Amendments, deviations and integrity checks.** Covered calls not significantly negative (9ea4adf).

**What it showed.** Put-writing earned its premium like the index it is short; a carry, not an edge.

## #8a V1 T0: short every monthly ATM straddle across the optionable universe

**Folder:** `research/compass/intel/, studies/v*.py, results/v1/ (@7dfea57)`. **Commits:** A8 29f20e3 (A8.1–A8.4) / — / aff15d9, df4fe32. **Dates:** 2026-10-15.

**Hypothesis.** Single-name monthly straddles are overpriced (volatility risk premium).

**Rule.** Sell the ATM straddle of every optionable name at the cycle's entry, hold to expiration (adverse fill: one tick worse).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side; mid ± one tick ("adv").

**Data.** The optionable universe 2023-11 → 2026-08, 44,447 name-cycles.

**Periods and holdouts.** development / validation / hold-out (each hold-out opened once).

**Pass rule (as pre-registered).** A8: negative T0 with sorts (T1 IV/RV, T2 term slope, T3 skew) adding a positive long-short.

**Verdict.** Rejected: T0 −13.2% of premium dev+val [−22.4, −5.0], −23.6% hold-out; T1–T3 add nothing.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| ADR | development | 731 | 14 / 283 | 51.2 | +46.9, +305.51 | −77.4, −436.05 | +1.3, +5.88 | **−13.81**, −56.64 | [−29.13, −3.90]; [−173.85, +26.14] |
| Common Stock | development | 12,281 | 14 / 283 | 54.7 | +47.5, +505.78 | −73.6, −747.20 | +8.5, +36.88 | **−7.38**, −62.30 | [−8.83, +0.77]; [−109.35, +10.32] |
| ETF | development | 2,642 | 14 / 283 | 50.8 | +44.8, +257.19 | −61.0, −253.09 | +1.2, +3.88 | **−7.25**, +6.11 | [−18.04, +8.70]; [−59.66, +84.56] |
| Structured Product | development | 12 | 12 / 283 | 75.0 | +51.1, +156.21 | −42.9, −108.45 | +35.2, +95.88 | **+27.60**, +90.05 | [−6.44, +50.40]; [−13.76, +129.89] |
| Unit | development | 51 | 14 / 283 | 58.8 | +42.2, +39.65 | −94.1, −93.64 | +15.2, +11.88 | **−13.93**, −15.24 | [−31.13, +23.27]; [−25.28, +24.29] |
| stock | development | 14 | 14 / 283 | 57.1 | +55.2, +105.38 | −48.5, −77.29 | +19.0, +26.88 | **+10.77**, +27.09 | [−17.45, +41.25]; [−26.68, +82.50] |
| all names | development | 15,731 | 14 / 283 | 53.9 | +47.0, +455.19 | −71.5, −640.64 | +7.1, +24.88 | **−7.63**, −50.20 | [−9.73, +0.78]; [−90.34, +12.98] |
| ADR | validation | 761 | 12 / 239 | 50.6 | +44.0, +355.98 | −86.0, −584.97 | +1.1, +4.82 | **−20.23**, −108.93 | [−32.01, −4.74]; [−189.57, +31.75] |
| Common Stock | validation | 12,557 | 12 / 239 | 48.6 | +45.8, +573.82 | −82.4, −939.57 | −2.7, −12.12 | **−20.11**, −204.27 | [−35.39, −5.24]; [−393.76, −25.91] |
| ETF | validation | 2,832 | 12 / 239 | 45.8 | +43.3, +287.12 | −79.0, −499.64 | −7.5, −20.12 | **−22.94**, −139.04 | [−51.85, −0.88]; [−393.80, +28.71] |
| Other | validation | 2 | 2 / 21 | 0.0 | —, — | −100.7, −335.62 | −100.7, −335.62 | **−100.69**, −335.62 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Structured Product | validation | 12 | 12 / 239 | 58.3 | +44.1, +241.74 | −121.4, −746.72 | +21.3, +107.38 | **−24.86**, −170.12 | [−139.67, +22.36]; [−756.56, +127.70] |
| Unit | validation | 45 | 12 / 239 | 57.8 | +51.3, +74.30 | −75.4, −90.28 | +26.0, +27.88 | **−2.21**, +4.81 | [−41.90, +38.57]; [−48.07, +54.95] |
| stock | validation | 23 | 12 / 239 | 34.8 | +45.0, +151.38 | −103.5, −375.79 | −33.8, −120.12 | **−51.82**, −192.42 | [−104.30, −6.97]; [−282.32, −12.45] |
| all names | validation | 16,232 | 12 / 239 | 48.2 | +45.3, +513.15 | −82.0, −840.26 | −3.5, −14.12 | **−20.61**, −187.82 | [−37.72, −4.97]; [−373.25, −17.85] |
| ADR | hold-out | 588 | 8 / 155 | 46.3 | +41.1, +557.43 | −81.7, −791.98 | −10.0, −33.12 | **−24.91**, −167.77 | [−46.04, −11.98]; [−503.04, +7.84] |
| Common Stock | hold-out | 9,500 | 8 / 155 | 46.2 | +43.9, +771.40 | −78.3, −1,107.72 | −7.9, −44.12 | **−21.89**, −240.16 | [−26.52, −13.80]; [−377.47, −37.68] |
| ETF | hold-out | 2,296 | 8 / 155 | 37.2 | +40.4, +375.41 | −77.6, −662.56 | −24.2, −77.62 | **−33.69**, −276.03 | [−53.03, −22.38]; [−495.65, −182.98] |
| Other | hold-out | 11 | 7 / 155 | 45.5 | +40.8, +348.67 | −44.1, −418.63 | −9.9, −169.14 | **−5.51**, −69.86 | [−53.68, +36.47]; [−459.63, +389.86] |
| Structured Product | hold-out | 8 | 8 / 155 | 62.5 | +45.2, +167.88 | −24.8, −108.79 | +16.6, +42.88 | **+18.93**, +64.13 | [−18.51, +45.31]; [−89.42, +132.74] |
| Unit | hold-out | 34 | 8 / 155 | 44.1 | +39.0, +61.01 | −80.1, −104.49 | −10.4, −18.12 | **−27.57**, −31.47 | [−53.97, +8.22]; [−68.41, +11.82] |
| stock | hold-out | 47 | 8 / 155 | 42.6 | +58.5, +660.32 | −63.0, −621.76 | −3.8, −40.13 | **−11.31**, −76.19 | [−51.78, +4.77]; [−610.34, +117.37] |
| all names | hold-out | 12,484 | 8 / 155 | 44.5 | +43.2, +696.78 | −78.2, −995.02 | −10.9, −49.12 | **−24.13**, −241.82 | [−31.78, −16.70]; [−367.78, −68.92] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| ADR | development | +4,425.75, +66.1%, 2024-07-22, ASML 2024-08-16 940.0 straddle | −11,414.21, −224.7%, 2024-01-22, ASML 2024-02-16 765.0 straddle | 0.73 | 57,178 | 283 | total ≤ 0 (best 5 days +31,201; without them −72,607) |
| Common Stock | development | +19,754.81, +36.9%, 2024-03-18, MSTR 2024-04-19 1500.0 straddle | −95,326.37, −739.7%, 2024-02-20, MSTR 2024-03-15 705.0 straddle | 0.82 | 836,734 | 283 | total ≤ 0 (best 5 days +268,994; without them −1,034,062) |
| ETF | development | +2,699.76, +41.9%, 2024-11-18, MSTX 2024-12-20 115.0 straddle | −5,420.16, −209.3%, 2024-05-20, NVDX 2024-06-21 105.0 straddle | 1.05 | 116,495 | 282 | 765% |
| Structured Product | development | +490.88, +91.0%, 2024-12-23, VXX 2025-01-17 44.0 straddle | −181.12, −96.3%, 2024-04-22, VXX 2024-05-17 14.5 straddle | 4.32 | 181 | 109 | 104% |
| Unit | development | +117.88, +73.7%, 2024-08-19, WES 2024-09-20 39.0 straddle | −443.12, −190.6%, 2023-11-20, NEP 2023-12-15 23.5 straddle | 0.60 | 876 | 193 | total ≤ 0 (best 5 days +691; without them −1,469) |
| stock | development | +191.88, +89.2%, 2024-10-21, SPLG 2024-11-15 69.0 straddle | −154.12, −83.3%, 2024-04-22, SPLG 2024-05-17 59.0 straddle | 1.82 | 398 | 237 | 189% |
| all names | development | +19,754.81, +36.9%, 2024-03-18, MSTR 2024-04-19 1500.0 straddle | −95,326.37, −739.7%, 2024-02-20, MSTR 2024-03-15 705.0 straddle | 0.83 | 918,409 | 283 | total ≤ 0 (best 5 days +345,303; without them −1,134,960) |
| ADR | validation | +4,876.78, +87.2%, 2025-05-19, ASML 2025-06-20 750.0 straddle | −23,247.25, −315.6%, 2025-12-22, ASML 2026-01-16 1055.0 straddle | 0.62 | 98,216 | 195 | total ≤ 0 (best 5 days +26,071; without them −108,969) |
| Common Stock | validation | +21,042.30, +68.0%, 2025-05-19, BKNG 2025-06-20 5380.0 straddle | −45,597.98, −100.8%, 2025-04-21, BKNG 2025-05-16 4440.0 straddle | 0.58 | 2,565,025 | 239 | total ≤ 0 (best 5 days +64,256; without them −2,629,282) |
| ETF | validation | +4,382.79, +87.3%, 2025-08-18, ETHU 2025-09-19 155.0 straddle | −8,801.19, −210.3%, 2025-04-21, VGT 2025-05-16 490.0 straddle | 0.49 | 416,912 | 239 | total ≤ 0 (best 5 days +123,089; without them −516,862) |
| Other | validation | −198.12, −67.2%, 2025-06-23, RDW 2025-07-18 15.0 straddle | −473.12, −134.2%, 2025-07-21, RDW 2025-08-15 17.0 straddle | 0.00 | 671 | 21 | total ≤ 0 (best 5 days −671; without them +0) |
| Structured Product | validation | +533.88, +70.9%, 2025-05-19, VXX 2025-06-20 52.5 straddle | −2,173.12, −453.7%, 2025-03-24, VXX 2025-04-17 45.5 straddle | 0.45 | 3,230 | 195 | total ≤ 0 (best 5 days +1,477; without them −3,519) |
| Unit | validation | +202.88, +93.3%, 2025-07-21, MPLX 2025-08-15 50.0 straddle | −260.12, −125.4%, 2025-03-24, MPLX 2025-04-17 55.0 straddle | 1.13 | 934 | 105 | 609% |
| stock | validation | +411.88, +56.8%, 2025-07-21, HIMZ 2025-08-15 19.0 straddle | −1,175.12, −162.1%, 2025-12-22, Q 2026-01-16 80.0 straddle | 0.21 | 4,578 | 215 | total ≤ 0 (best 5 days +717; without them −5,143) |
| all names | validation | +21,042.30, +68.0%, 2025-05-19, BKNG 2025-06-20 5380.0 straddle | −45,597.98, −100.8%, 2025-04-21, BKNG 2025-05-16 4440.0 straddle | 0.57 | 3,048,619 | 239 | total ≤ 0 (best 5 days +121,340; without them −3,169,960) |
| ADR | hold-out | +21,363.40, +87.6%, 2026-07-20, ASML 2026-08-21 1740.0 straddle | −29,898.44, −178.8%, 2026-05-18, ASML 2026-06-18 1470.0 straddle | 0.61 | 124,610 | 155 | total ≤ 0 (best 5 days +22,101; without them −120,748) |
| Common Stock | hold-out | +30,840.83, +58.9%, 2026-07-20, SNDK 2026-08-21 1390.0 straddle | −65,571.76, −189.2%, 2026-01-20, BKNG 2026-02-20 5050.0 straddle | 0.60 | 2,530,009 | 155 | total ≤ 0 (best 5 days −790,140; without them −1,491,384) |
| ETF | hold-out | +7,362.74, +95.7%, 2026-07-20, SMH 2026-08-21 560.0 straddle | −47,328.44, −266.6%, 2026-05-18, MUU 2026-06-18 445.0 straddle | 0.34 | 644,350 | 131 | total ≤ 0 (best 5 days −166,531; without them −467,244) |
| Other | hold-out | +744.86, +43.1%, 2026-05-18, FCFS 2026-06-18 220.0 straddle | −1,184.14, −67.5%, 2026-04-20, FCFS 2026-05-15 200.0 straddle | 0.69 | 1,579 | 111 | total ≤ 0 (best 5 days +1,088; without them −1,857) |
| Structured Product | hold-out | +352.88, +60.8%, 2026-01-20, VXX 2026-02-20 29.5 straddle | −215.12, −43.3%, 2026-02-23, VXX 2026-03-20 29.5 straddle | 2.57 | 215 | 85 | 164% |
| Unit | hold-out | +194.88, +74.2%, 2026-04-20, MPLX 2026-05-15 55.0 straddle | −296.12, −240.7%, 2026-01-20, EPD 2026-02-20 32.5 straddle | 0.46 | 1,423 | 155 | total ≤ 0 (best 5 days +329; without them −1,400) |
| stock | hold-out | +2,137.84, +74.9%, 2026-07-20, Q 2026-08-21 135.0 straddle | −1,752.13, −174.3%, 2026-06-22, SOLS 2026-07-17 85.0 straddle | 0.79 | 9,304 | 155 | total ≤ 0 (best 5 days +6,741; without them −10,323) |
| all names | hold-out | +30,840.83, +58.9%, 2026-07-20, SNDK 2026-08-21 1390.0 straddle | −65,571.76, −189.2%, 2026-01-20, BKNG 2026-02-20 5050.0 straddle | 0.56 | 3,279,363 | 155 | total ≤ 0 (best 5 days −1,248,558; without them −1,770,295) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.13). The study's fees are given beside them below. Re-pricing: exact (44,447 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| ADR | development | 731 | **−13.81**, −56.64 | −14.31, −57.92 | 51.2 / 50.8 | [−29.13, −3.90] / [−29.64, −4.41] |
| Common Stock | development | 12,281 | **−7.38**, −62.30 | −7.69, −63.56 | 54.7 / 54.6 | [−8.83, +0.77] / [−9.11, +0.46] |
| ETF | development | 2,642 | **−7.25**, +6.11 | −7.86, +4.83 | 50.8 / 50.5 | [−18.04, +8.70] / [−18.67, +8.12] |
| Structured Product | development | 12 | **+27.60**, +90.05 | +27.04, +88.77 | 75.0 / 75.0 | [−6.44, +50.40] / [−7.09, +49.70] |
| Unit | development | 51 | **−13.93**, −15.24 | −15.55, −16.52 | 58.8 / 58.8 | [−31.13, +23.27] / [−32.77, +21.79] |
| stock | development | 14 | **+10.77**, +27.09 | +10.02, +25.81 | 57.1 / 57.1 | [−17.45, +41.25] / [−18.20, +40.54] |
| all names | development | 15,731 | **−7.63**, −50.20 | −8.01, −51.47 | 53.9 / 53.7 | [−9.73, +0.78] / [−10.10, +0.41] |
| ADR | validation | 761 | **−20.23**, −108.93 | −20.69, −110.21 | 50.6 / 50.2 | [−32.01, −4.74] / [−32.48, −5.20] |
| Common Stock | validation | 12,557 | **−20.11**, −204.27 | −20.38, −205.54 | 48.6 / 48.5 | [−35.39, −5.24] / [−35.64, −5.51] |
| ETF | validation | 2,832 | **−22.94**, −139.04 | −23.43, −140.32 | 45.8 / 45.4 | [−51.85, −0.88] / [−52.31, −1.38] |
| Other | validation | 2 | **−100.69**, −335.62 | −101.09, −336.90 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Structured Product | validation | 12 | **−24.86**, −170.12 | −25.09, −171.40 | 58.3 / 58.3 | [−139.67, +22.36] / [−139.90, +22.16] |
| Unit | validation | 45 | **−2.21**, +4.81 | −3.33, +3.53 | 57.8 / 57.8 | [−41.90, +38.57] / [−43.01, +37.34] |
| stock | validation | 23 | **−51.82**, −192.42 | −52.24, −193.70 | 34.8 / 34.8 | [−104.30, −6.97] / [−104.78, −7.46] |
| all names | validation | 16,232 | **−20.61**, −187.82 | −20.93, −189.08 | 48.2 / 48.0 | [−37.72, −4.97] / [−38.05, −5.29] |
| ADR | hold-out | 588 | **−24.91**, −167.77 | −25.31, −169.03 | 46.3 / 46.3 | [−46.04, −11.98] / [−46.43, −12.36] |
| Common Stock | hold-out | 9,500 | **−21.89**, −240.16 | −22.12, −241.42 | 46.2 / 46.0 | [−26.52, −13.80] / [−26.76, −14.02] |
| ETF | hold-out | 2,296 | **−33.69**, −276.03 | −34.11, −277.31 | 37.2 / 37.1 | [−53.03, −22.38] / [−53.44, −22.80] |
| Other | hold-out | 11 | **−5.51**, −69.86 | −5.76, −71.13 | 45.5 / 45.5 | [−53.68, +36.47] / [−53.95, +36.37] |
| Structured Product | hold-out | 8 | **+18.93**, +64.13 | +18.57, +62.85 | 62.5 / 62.5 | [−18.51, +45.31] / [−18.81, +44.93] |
| Unit | hold-out | 34 | **−27.57**, −31.47 | −28.55, −32.75 | 44.1 / 44.1 | [−53.97, +8.22] / [−55.00, +7.31] |
| stock | hold-out | 47 | **−11.31**, −76.19 | −11.47, −77.46 | 42.6 / 42.6 | [−51.78, +4.77] / [−51.92, +4.60] |
| all names | hold-out | 12,484 | **−24.13**, −241.82 | −24.41, −243.08 | 44.5 / 44.4 | [−31.78, −16.70] / [−32.05, −16.96] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development: held to expiration 100.0%
- validation: held to expiration 100.0%
- hold-out: held to expiration 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2023 | ADR | 106 | 47.2 | −13.65 | −67.88 | −7,195 |
| 2024 | ADR | 625 | 51.8 | −13.84 | −54.74 | −34,211 |
| 2025 | ADR | 761 | 50.6 | −20.23 | −108.93 | −82,898 |
| 2026 | ADR | 588 | 46.3 | −24.91 | −167.77 | −98,647 |
| 2023 | Common Stock | 1,681 | 52.1 | −22.75 | −133.90 | −225,093 |
| 2024 | Common Stock | 10,600 | 55.1 | −4.94 | −50.94 | −539,975 |
| 2025 | Common Stock | 12,557 | 48.6 | −20.11 | −204.27 | −2,565,025 |
| 2026 | Common Stock | 9,500 | 46.2 | −21.89 | −240.16 | −2,281,524 |
| 2023 | ETF | 404 | 39.9 | −32.49 | −91.40 | −36,924 |
| 2024 | ETF | 2,238 | 52.8 | −2.70 | +23.71 | +53,059 |
| 2025 | ETF | 2,832 | 45.8 | −22.94 | −139.04 | −393,774 |
| 2026 | ETF | 2,296 | 37.2 | −33.69 | −276.03 | −633,775 |
| 2025 | Other | 2 | 0.0 | −100.69 | −335.62 | −671 |
| 2026 | Other | 11 | 45.5 | −5.51 | −69.86 | −768 |
| 2023 | Structured Product | 2 | 50.0 | +16.90 | +35.38 | +71 |
| 2024 | Structured Product | 10 | 80.0 | +29.74 | +100.98 | +1,010 |
| 2025 | Structured Product | 12 | 58.3 | −24.86 | −170.12 | −2,041 |
| 2026 | Structured Product | 8 | 62.5 | +18.93 | +64.13 | +513 |
| 2023 | Unit | 7 | 71.4 | +3.99 | −43.69 | −306 |
| 2024 | Unit | 44 | 56.8 | −16.78 | −10.71 | −471 |
| 2025 | Unit | 45 | 57.8 | −2.21 | +4.81 | +217 |
| 2026 | Unit | 34 | 44.1 | −27.57 | −31.47 | −1,070 |
| 2023 | stock | 2 | 50.0 | −23.70 | −32.12 | −64 |
| 2024 | stock | 12 | 58.3 | +16.51 | +36.96 | +444 |
| 2025 | stock | 23 | 34.8 | −51.82 | −192.42 | −4,426 |
| 2026 | stock | 47 | 42.6 | −11.31 | −76.19 | −3,581 |
| 2023 | all names | 2,202 | 49.6 | −23.98 | −122.39 | −269,511 |
| 2024 | all names | 13,529 | 54.6 | −4.97 | −38.45 | −520,145 |
| 2025 | all names | 16,232 | 48.2 | −20.61 | −187.82 | −3,048,619 |
| 2026 | all names | 12,484 | 44.5 | −24.13 | −241.82 | −3,018,853 |

![](charts/s8a.png)

**Amendments, deviations and integrity checks.** Corporate actions detected from the options market (A8.1–A8.3c).

**What it showed.** Selling every straddle lost; the spread takes the premium.

## #8b V2a: short ATM straddle across the earnings report

**Folder:** `research/compass/intel/, studies/v*.py, results/v1/ (@7dfea57)`. **Commits:** A9 47c2c2f / — / 4ed84d4, 152f786. **Dates:** 2026-10-15.

**Hypothesis.** Earnings straddles are overpriced.

**Rule.** Sell the ATM straddle at the close before the report, buy back after it (adverse fill).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side; adverse tick.

**Data.** 1,578 names, reports 2023-11 → 2026-09.

**Periods and holdouts.** development / validation / hold-out (each hold-out opened once).

**Pass rule (as pre-registered).** A9.

**Verdict.** Rejected: −26.1% dev+val [−28.5, −23.3], −34.2% hold-out.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| single names | development | 3,558 | 234 / 276 | 40.2 | +27.6, +301.83 | −60.3, −622.70 | −12.5, −52.20 | **−25.03**, −251.38 | [−27.70, −21.41]; [−288.01, −214.25] |
| single names | validation | 4,244 | 218 / 246 | 33.0 | +26.3, +355.73 | −56.3, −553.12 | −17.6, −86.20 | **−29.02**, −252.89 | [−33.20, −23.79]; [−315.21, −192.68] |
| single names | hold-out | 3,682 | 165 / 191 | 26.2 | +23.6, +339.98 | −56.3, −632.44 | −24.0, −146.71 | **−35.40**, −378.11 | [−38.38, −29.66]; [−411.00, −332.44] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| single names | development | +5,621.52, +31.6%, 2024-05-02, BKNG 2024-05-03 3475.0 | −23,114.48, −129.2%, 2024-02-22, BKNG 2024-02-23 3900.0 | 0.33 | 898,664 | 266 | total ≤ 0 (best 5 days +22,380; without them −916,788) |
| single names | validation | +26,833.24, +84.4%, 2025-02-20, BKNG 2025-02-21 5020.0 | −18,091.28, −406.1%, 2025-09-09, SNPS 2025-09-12 605.0 | 0.32 | 1,074,808 | 244 | total ≤ 0 (best 5 days +43,663; without them −1,116,914) |
| single names | hold-out | +5,019.46, +30.4%, 2026-08-05, SNDK 2026-08-07 1350.0 | −22,300.32, −330.6%, 2026-05-04, STRL 2026-05-15 530.0 | 0.19 | 1,399,007 | 191 | total ≤ 0 (best 5 days +19,525; without them −1,411,739) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.67 a trade) and Robinhood's charged instead (mean $0.21). The study's fees are given beside them below. Re-pricing: exact (11,484 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| single names | development | 3,558 | **−25.03**, −251.38 | −25.67, −253.83 | 40.2 / 39.2 | [−27.70, −21.41] / [−28.33, −22.08] |
| single names | validation | 4,244 | **−29.02**, −252.89 | −29.62, −255.34 | 33.0 / 32.5 | [−33.20, −23.79] / [−33.80, −24.38] |
| single names | hold-out | 3,682 | **−35.40**, −378.11 | −35.95, −380.58 | 26.2 / 25.6 | [−38.38, −29.66] / [−38.94, −30.24] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development: closed after the report 100.0%
- validation: closed after the report 100.0%
- hold-out: closed after the report 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2023 | single names | 71 | 47.9 | −19.84 | −99.28 | −7,049 |
| 2024 | single names | 3,487 | 40.0 | −25.13 | −254.48 | −887,359 |
| 2025 | single names | 4,244 | 33.0 | −29.02 | −252.89 | −1,073,251 |
| 2026 | single names | 3,682 | 26.2 | −35.40 | −378.11 | −1,392,215 |

![](charts/s8b.png)

**Amendments, deviations and integrity checks.** Friday-only expiry probe checked on all names (95c90f9: no change).

**What it showed.** Selling earnings straddles lost a quarter of the premium.

## #8c V2b: long ATM straddle into the earnings report

**Folder:** `research/compass/intel/, studies/v*.py, results/v1/ (@7dfea57)`. **Commits:** A9 47c2c2f / — / 152f786. **Dates:** 2026-10-15.

**Hypothesis.** Buying into the report captures the run-up in implied volatility.

**Rule.** Buy the ATM straddle five sessions before the report, sell at the report.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As V2a.

**Data.** As V2a.

**Periods and holdouts.** development / validation / hold-out (each hold-out opened once).

**Pass rule (as pre-registered).** A9.

**Verdict.** Rejected: −20.9% / −29.3%.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| single names | development | 3,485 | 234 / 277 | 21.2 | +18.0, +204.81 | −22.5, −231.86 | −13.2, −74.20 | **−13.91**, −139.26 | [−15.90, −11.09]; [−165.27, −101.68] |
| single names | validation | 4,100 | 217 / 246 | 9.2 | +20.2, +272.46 | −34.2, −369.07 | −26.4, −194.20 | **−29.18**, −309.92 | [−33.00, −24.91]; [−356.97, −263.79] |
| single names | hold-out | 3,543 | 164 / 191 | 10.2 | +24.0, +483.68 | −36.8, −433.77 | −28.6, −232.20 | **−30.57**, −339.77 | [−34.38, −25.36]; [−393.53, −267.97] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| single names | development | +8,234.62, +93.4%, 2024-10-30, TPL 2024-11-15 1150.0 | −11,695.66, −50.7%, 2024-04-22, MSTR 2024-05-03 1320.0 | 0.24 | 485,792 | 277 | total ≤ 0 (best 5 days +22,585; without them −507,907) |
| single names | validation | +10,494.60, +99.1%, 2025-02-18, AXON 2025-03-21 710.0 | −10,930.90, −32.1%, 2025-07-22, BKNG 2025-08-01 5775.0 | 0.07 | 1,270,690 | 246 | total ≤ 0 (best 5 days +3,917; without them −1,274,607) |
| single names | hold-out | +19,714.24, +71.8%, 2026-05-21, AZO 2026-06-18 3450.0 | −11,370.84, −36.5%, 2026-02-10, BKNG 2026-02-20 4300.0 | 0.13 | 1,203,797 | 191 | total ≤ 0 (best 5 days +27,607; without them −1,231,404) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.80 a trade) and Robinhood's charged instead (mean $0.22). The study's fees are given beside them below. Re-pricing: exact (11,128 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| single names | development | 3,485 | **−13.91**, −139.26 | −14.51, −141.84 | 21.2 / 20.3 | [−15.90, −11.09] / [−16.48, −11.70] |
| single names | validation | 4,100 | **−29.18**, −309.92 | −29.71, −312.50 | 9.2 / 9.0 | [−33.00, −24.91] / [−33.51, −25.43] |
| single names | hold-out | 3,543 | **−30.57**, −339.77 | −31.05, −342.34 | 10.2 / 10.1 | [−34.38, −25.36] / [−34.85, −25.85] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development: closed at the report 100.0%
- validation: closed at the report 100.0%
- hold-out: closed at the report 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2023 | single names | 76 | 17.1 | −9.07 | −95.74 | −7,277 |
| 2024 | single names | 3,417 | 21.2 | −14.06 | −140.45 | −479,930 |
| 2025 | single names | 4,101 | 9.2 | −29.19 | −310.06 | −1,271,575 |
| 2026 | single names | 3,534 | 10.2 | −30.55 | −339.85 | −1,201,028 |

![](charts/s8c.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Both sides of the earnings straddle lose.

## #8d V3a: single-name 0DTE short ATM straddle 10:00 → 15:50

**Folder:** `research/compass/intel/, studies/v*.py, results/v1/ (@7dfea57)`. **Commits:** A10–A10.4 9c476c5, 048d33a / — / e4e4cea. **Dates:** 2026-10-16.

**Hypothesis.** Single-name same-day premium is overpriced.

**Rule.** Sell the ATM straddle at 10:00, buy back 15:50 (adverse).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side; adverse tick.

**Data.** 11 Mon/Wed/Fri names 2017-06 → 2026-10.

**Periods and holdouts.** development / validation / hold-out (each hold-out opened once).

**Pass rule (as pre-registered).** A10.

**Verdict.** Rejected: −19.8% dev+val [−25.5, −14.7], −7.4% hold-out.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| AAPL | development | 283 | 283 / 1,446 | 49.8 | +45.7, +84.21 | −81.0, −152.69 | −0.2, −0.20 | **−17.87**, −34.66 | [−26.74, −4.24]; [−56.36, −11.16] |
| AMD | development | 284 | 284 / 1,446 | 50.4 | +38.6, +44.78 | −78.3, −75.02 | +1.8, +0.80 | **−19.44**, −14.70 | [−28.06, −9.69]; [−26.95, −3.56] |
| AMZN | development | 283 | 283 / 1,446 | 51.6 | +40.5, +802.01 | −81.0, −1,484.71 | +4.1, +23.78 | **−18.33**, −304.99 | [−26.52, −7.14]; [−520.81, −95.64] |
| AVGO | development | 284 | 284 / 1,446 | 31.7 | +33.2, +129.67 | −97.1, −370.79 | −37.7, −126.20 | **−55.78**, −212.20 | [−66.69, −42.24]; [−262.59, −158.95] |
| GOOGL | development | 283 | 283 / 1,446 | 41.7 | +36.9, +473.30 | −89.1, −1,069.53 | −14.7, −104.20 | **−36.58**, −426.23 | [−46.05, −23.83]; [−583.44, −271.48] |
| INTC | development | 283 | 283 / 1,446 | 41.0 | +35.8, +19.76 | −86.9, −42.88 | −12.3, −6.20 | **−36.59**, −17.20 | [−48.71, −24.04]; [−23.72, −10.92] |
| META | development | 284 | 284 / 1,446 | 52.5 | +43.2, +108.30 | −70.4, −167.28 | +5.0, +12.80 | **−10.81**, −22.69 | [−17.22, −1.13]; [−42.29, −0.45] |
| MSFT | development | 284 | 284 / 1,446 | 45.1 | +38.2, +67.15 | −92.7, −141.54 | −10.5, −10.70 | **−33.74**, −47.48 | [−43.70, −22.16]; [−67.09, −29.27] |
| MU | development | 284 | 284 / 1,446 | 51.1 | +38.8, +32.45 | −81.5, −66.99 | +4.3, +2.80 | **−20.08**, −16.22 | [−29.24, −8.91]; [−24.51, −7.51] |
| NVDA | development | 283 | 283 / 1,446 | 55.8 | +41.0, +168.40 | −71.8, −329.11 | +11.1, +36.80 | **−8.78**, −51.35 | [−16.83, −0.31]; [−93.86, −7.94] |
| TSLA | development | 282 | 282 / 1,446 | 57.1 | +47.1, +482.48 | −84.7, −858.84 | +17.1, +99.80 | **−9.48**, −93.05 | [−18.33, −0.81]; [−215.17, +22.77] |
| all names | development | 3,117 | 284 / 1,446 | 48.0 | +40.4, +226.69 | −84.0, −425.57 | −3.8, −5.20 | **−24.33**, −112.72 | [−28.82, −17.16]; [−148.99, −72.62] |
| AAPL | validation | 102 | 102 / 512 | 60.8 | +49.3, +76.86 | −63.3, −104.25 | +23.2, +39.30 | **+5.16**, +5.84 | [−0.92, +21.03]; [−3.78, +31.69] |
| AMD | validation | 102 | 102 / 512 | 58.8 | +46.8, +99.75 | −80.3, −166.80 | +20.9, +32.80 | **−5.52**, −10.01 | [−15.28, +11.32]; [−38.48, +23.38] |
| AMZN | validation | 102 | 102 / 512 | 52.9 | +45.3, +76.87 | −68.6, −107.16 | +5.9, +10.30 | **−8.31**, −9.73 | [−16.57, +7.97]; [−22.77, +16.20] |
| AVGO | validation | 101 | 101 / 512 | 48.5 | +36.5, +319.04 | −89.4, −815.52 | −1.1, −11.22 | **−28.33**, −265.09 | [−45.56, −9.94]; [−446.57, −96.17] |
| GOOGL | validation | 102 | 102 / 512 | 53.9 | +42.0, +55.09 | −88.1, −110.48 | +8.7, +11.30 | **−17.99**, −21.20 | [−31.46, −1.42]; [−35.16, +0.48] |
| INTC | validation | 102 | 102 / 512 | 62.7 | +36.3, +17.13 | −91.6, −40.10 | +16.2, +6.30 | **−11.37**, −4.19 | [−20.89, +3.78]; [−9.40, +2.60] |
| META | validation | 102 | 102 / 512 | 56.9 | +49.2, +225.42 | −97.7, −386.70 | +18.0, +62.80 | **−14.17**, −38.63 | [−32.49, +1.89]; [−119.61, +33.39] |
| MSFT | validation | 102 | 102 / 512 | 50.0 | +39.5, +118.88 | −71.8, −197.42 | +1.1, +2.80 | **−16.14**, −39.27 | [−31.11, −2.06]; [−76.64, −0.82] |
| MU | validation | 102 | 102 / 512 | 54.9 | +38.3, +46.16 | −68.0, −81.46 | +9.4, +10.30 | **−9.65**, −11.40 | [−16.99, +4.15]; [−22.10, +5.98] |
| NVDA | validation | 101 | 101 / 512 | 54.5 | +47.4, +239.69 | −90.3, −647.64 | +4.1, +13.80 | **−15.30**, −164.44 | [−30.21, +7.22]; [−364.49, −5.92] |
| TSLA | validation | 102 | 102 / 512 | 54.9 | +51.7, +219.24 | −71.3, −262.64 | +14.3, +41.80 | **−3.76**, +1.93 | [−14.69, +13.33]; [−44.26, +68.41] |
| all names | validation | 1,120 | 102 / 512 | 55.4 | +43.9, +132.00 | −80.0, −276.29 | +10.3, +12.30 | **−11.38**, −50.27 | [−17.28, −0.43]; [−88.36, −9.27] |
| AAPL | hold-out | 161 | 161 / 456 | 54.0 | +44.8, +109.86 | −80.5, −191.23 | +6.5, +14.80 | **−12.79**, −28.53 | [−29.37, −0.27]; [−66.61, +2.54] |
| AMD | hold-out | 116 | 116 / 456 | 60.3 | +44.9, +255.78 | −70.1, −323.03 | +20.6, +78.80 | **−0.73**, +26.25 | [−14.94, +8.72]; [−39.74, +75.10] |
| AMZN | hold-out | 161 | 161 / 456 | 60.9 | +40.7, +101.80 | −74.7, −182.01 | +17.3, +36.80 | **−4.44**, −9.26 | [−17.22, +6.96]; [−37.65, +17.31] |
| AVGO | hold-out | 159 | 159 / 456 | 53.5 | +37.6, +186.18 | −57.0, −318.46 | +7.5, +34.80 | **−6.44**, −48.69 | [−15.07, +2.08]; [−103.74, +0.86] |
| GOOGL | hold-out | 159 | 159 / 456 | 52.2 | +45.7, +144.28 | −73.7, −219.04 | +5.3, +13.80 | **−11.39**, −29.38 | [−25.56, −1.45]; [−72.75, +2.67] |
| INTC | hold-out | 116 | 116 / 456 | 54.3 | +37.7, +57.70 | −75.4, −97.03 | +5.5, +4.80 | **−13.97**, −12.99 | [−31.20, −1.03]; [−35.43, +4.57] |
| META | hold-out | 159 | 159 / 456 | 55.3 | +37.4, +293.02 | −71.4, −499.71 | +3.7, +28.80 | **−11.19**, −60.96 | [−25.81, −3.35]; [−159.79, −8.66] |
| MSFT | hold-out | 159 | 159 / 456 | 52.2 | +44.3, +174.96 | −79.3, −288.00 | +7.3, +27.80 | **−14.77**, −46.33 | [−34.37, −2.24]; [−121.96, +3.72] |
| MU | hold-out | 115 | 115 / 456 | 62.6 | +40.0, +515.28 | −94.5, −791.52 | +11.9, +57.80 | **−10.27**, +26.65 | [−27.84, +6.42]; [−151.18, +235.33] |
| NVDA | hold-out | 158 | 158 / 456 | 65.8 | +44.3, +106.99 | −86.9, −196.65 | +22.8, +54.80 | **−0.56**, +3.22 | [−15.00, +12.08]; [−29.62, +32.92] |
| TSLA | hold-out | 159 | 159 / 456 | 59.7 | +47.5, +292.67 | −87.3, −522.37 | +21.9, +117.80 | **−6.77**, −35.40 | [−20.47, +5.64]; [−115.37, +43.42] |
| all names | hold-out | 1,622 | 161 / 456 | 57.2 | +42.4, +199.58 | −76.6, −318.86 | +10.9, +32.80 | **−8.50**, −22.24 | [−18.41, −1.91]; [−62.38, +8.26] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| AAPL | development | +438.80, +59.9%, 2020-08-28, AAPL 10:00 short straddle 505.0 | −1,147.20, −146.1%, 2020-03-20, AAPL 10:00 short straddle 250.0 | 0.55 | 9,952 | 1,446 | total ≤ 0 (best 5 days +1,622; without them −11,431) |
| AMD | development | +223.80, +74.1%, 2022-05-06, AMD 10:00 short straddle 95.0 | −838.20, −262.3%, 2022-02-11, AMD 10:00 short straddle 123.0 | 0.61 | 4,832 | 1,446 | total ≤ 0 (best 5 days +1,030; without them −5,205) |
| AMZN | development | +3,219.66, +46.9%, 2020-09-04, AMZN 10:00 short straddle 3275.0 | −7,893.22, −413.3%, 2021-10-15, AMZN 10:00 short straddle 3310.0 | 0.58 | 90,721 | 1,446 | total ≤ 0 (best 5 days +13,718; without them −100,029) |
| AVGO | development | +412.80, +55.4%, 2022-06-10, AVGO 10:00 short straddle 545.0 | −1,891.20, −244.0%, 2022-08-26, AVGO 10:00 short straddle 547.5 | 0.16 | 60,878 | 1,446 | total ≤ 0 (best 5 days +1,855; without them −62,119) |
| GOOGL | development | +2,033.74, +68.0%, 2022-07-15, GOOGL 10:00 short straddle 2225.0 | −6,481.22, −498.6%, 2021-09-10, GOOGL 10:00 short straddle 2890.0 | 0.32 | 122,179 | 1,446 | total ≤ 0 (best 5 days +8,920; without them −129,543) |
| INTC | development | +94.80, +62.2%, 2020-07-24, INTC 10:00 short straddle 50.0 | −382.20, −534.5%, 2018-03-29, INTC 10:00 short straddle 50.0 | 0.32 | 4,868 | 1,446 | total ≤ 0 (best 5 days +338; without them −5,206) |
| META | development | +324.80, +64.5%, 2021-12-03, META 10:00 short straddle 305.0 | −891.20, −221.4%, 2020-06-26, META 10:00 short straddle 227.5 | 0.71 | 6,962 | 1,446 | total ≤ 0 (best 5 days +1,533; without them −7,978) |
| MSFT | development | +267.80, +50.3%, 2022-01-21, MSFT 10:00 short straddle 300.0 | −844.20, −226.6%, 2022-08-26, MSFT 10:00 short straddle 280.0 | 0.39 | 13,546 | 1,446 | total ≤ 0 (best 5 days +1,200; without them −14,685) |
| MU | development | +120.80, +65.7%, 2022-01-21, MU 10:00 short straddle 82.5 | −341.20, −300.6%, 2020-06-12, MU 10:00 short straddle 50.0 | 0.51 | 4,732 | 1,446 | total ≤ 0 (best 5 days +445; without them −5,051) |
| NVDA | development | +662.80, +76.2%, 2020-05-22, NVDA 10:00 short straddle 360.0 | −2,157.20, −243.8%, 2020-11-06, NVDA 10:00 short straddle 557.5 | 0.65 | 14,965 | 1,441 | total ≤ 0 (best 5 days +2,830; without them −17,362) |
| TSLA | development | +2,874.70, +50.6%, 2020-08-21, TSLA 10:00 short straddle 2060.0 | −12,862.24, −442.8%, 2020-07-10, TSLA 10:00 short straddle 1385.0 | 0.75 | 27,343 | 1,441 | total ≤ 0 (best 5 days +10,858; without them −37,099) |
| all names | development | +3,219.66, +46.9%, 2020-09-04, AMZN 10:00 short straddle 3275.0 | −12,862.24, −442.8%, 2020-07-10, TSLA 10:00 short straddle 1385.0 | 0.49 | 353,850 | 1,446 | total ≤ 0 (best 5 days +27,310; without them −378,672) |
| AAPL | validation | +198.80, +55.5%, 2024-08-02, AAPL 10:00 short straddle 222.5 | −451.20, −213.3%, 2024-12-20, AAPL 10:00 short straddle 247.5 | 1.14 | 591 | 105 | 131% |
| AMD | validation | +260.80, +80.7%, 2024-01-26, AMD 10:00 short straddle 177.5 | −873.20, −328.9%, 2024-01-19, AMD 10:00 short straddle 162.5 | 0.85 | 1,679 | 453 | total ≤ 0 (best 5 days +1,186; without them −2,207) |
| AMZN | validation | +201.80, +75.3%, 2023-10-27, AMZN 10:00 short straddle 128.0 | −337.20, −242.6%, 2024-02-09, AMZN 10:00 short straddle 170.0 | 0.81 | 1,252 | 512 | total ≤ 0 (best 5 days +815; without them −1,808) |
| AVGO | validation | +1,858.76, +67.1%, 2024-06-21, AVGO 10:00 short straddle 1680.0 | −4,831.22, −406.0%, 2023-05-26, AVGO 10:00 short straddle 755.0 | 0.37 | 27,246 | 512 | total ≤ 0 (best 5 days +5,488; without them −32,262) |
| GOOGL | validation | +129.80, +78.4%, 2024-12-27, GOOGL 10:00 short straddle 192.5 | −505.20, −204.9%, 2024-12-20, GOOGL 10:00 short straddle 185.0 | 0.58 | 2,292 | 512 | total ≤ 0 (best 5 days +604; without them −2,767) |
| INTC | validation | +54.80, +52.4%, 2024-08-02, INTC 10:00 short straddle 21.0 | −175.20, −216.3%, 2024-03-08, INTC 10:00 short straddle 46.0 | 0.72 | 520 | 512 | total ≤ 0 (best 5 days +206; without them −634) |
| META | validation | +966.78, +85.0%, 2024-02-02, META 10:00 short straddle 475.0 | −1,493.20, −323.2%, 2024-07-05, META 10:00 short straddle 522.5 | 0.77 | 4,914 | 512 | total ≤ 0 (best 5 days +3,136; without them −7,077) |
| MSFT | validation | +336.80, +67.1%, 2024-08-02, MSFT 10:00 short straddle 407.5 | −771.20, −357.0%, 2023-04-06, MSFT 10:00 short straddle 282.5 | 0.60 | 4,775 | 512 | total ≤ 0 (best 5 days +1,278; without them −5,284) |
| MU | validation | +135.80, +68.8%, 2024-04-05, MU 10:00 short straddle 123.0 | −356.20, −137.3%, 2024-08-02, MU 10:00 short straddle 96.0 | 0.69 | 1,260 | 512 | total ≤ 0 (best 5 days +563; without them −1,726) |
| NVDA | validation | +1,068.78, +77.2%, 2024-05-03, NVDA 10:00 short straddle 887.5 | −6,702.22, −541.6%, 2024-04-19, NVDA 10:00 short straddle 840.0 | 0.44 | 17,826 | 378 | total ≤ 0 (best 5 days +4,328; without them −20,937) |
| TSLA | validation | +573.80, +69.1%, 2024-11-15, TSLA 10:00 short straddle 317.5 | −1,069.20, −290.5%, 2023-01-27, TSLA 10:00 short straddle 165.0 | 1.02 | 2,458 | 343 | 1194% |
| all names | validation | +1,858.76, +67.1%, 2024-06-21, AVGO 10:00 short straddle 1680.0 | −6,702.22, −541.6%, 2024-04-19, NVDA 10:00 short straddle 840.0 | 0.59 | 59,100 | 512 | total ≤ 0 (best 5 days +9,405; without them −65,708) |
| AAPL | hold-out | +336.80, +61.2%, 2026-09-09, AAPL 10:00 short straddle 317.5 | −733.20, −417.8%, 2025-10-10, AAPL 10:00 short straddle 255.0 | 0.68 | 6,414 | 443 | total ≤ 0 (best 5 days +1,181; without them −5,774) |
| AMD | hold-out | +845.78, +58.7%, 2026-06-12, AMD 10:00 short straddle 510.0 | −2,432.22, −199.4%, 2026-07-02, AMD 10:00 short straddle 545.0 | 1.20 | 3,520 | 252 | 118% |
| AMZN | hold-out | +303.80, +73.0%, 2026-08-03, AMZN 10:00 short straddle 285.0 | −913.20, −493.6%, 2025-10-10, AMZN 10:00 short straddle 227.5 | 0.87 | 3,747 | 293 | total ≤ 0 (best 5 days +1,386; without them −2,876) |
| AVGO | hold-out | +438.80, +58.1%, 2026-05-15, AVGO 10:00 short straddle 425.0 | −3,666.24, −137.1%, 2026-09-02, AVGO 10:00 short straddle 375.0 | 0.67 | 7,809 | 447 | total ≤ 0 (best 5 days +2,057; without them −9,798) |
| GOOGL | hold-out | +397.80, +81.2%, 2026-02-06, GOOGL 10:00 short straddle 322.5 | −1,528.20, −384.9%, 2026-08-05, GOOGL 10:00 short straddle 380.0 | 0.72 | 5,992 | 275 | total ≤ 0 (best 5 days +1,622; without them −6,294) |
| INTC | hold-out | +238.80, +72.4%, 2026-04-24, INTC 10:00 short straddle 82.0 | −895.20, −259.1%, 2026-07-02, INTC 10:00 short straddle 130.0 | 0.71 | 2,143 | 456 | total ≤ 0 (best 5 days +980; without them −2,487) |
| META | hold-out | +1,095.78, +76.9%, 2025-04-11, META 10:00 short straddle 542.5 | −2,417.22, −222.8%, 2026-09-21, META 10:00 short straddle 712.5 | 0.73 | 13,402 | 438 | total ≤ 0 (best 5 days +3,825; without them −13,518) |
| MSFT | hold-out | +412.80, +63.8%, 2026-07-31, MSFT 10:00 short straddle 462.5 | −952.20, −269.4%, 2026-06-17, MSFT 10:00 short straddle 390.0 | 0.66 | 10,826 | 438 | total ≤ 0 (best 5 days +1,788; without them −9,155) |
| MU | hold-out | +2,454.74, +71.8%, 2026-06-12, MU 10:00 short straddle 985.0 | −7,237.26, −236.9%, 2026-07-02, MU 10:00 short straddle 1060.0 | 1.09 | 9,813 | 361 | 288% |
| NVDA | hold-out | +271.80, +83.9%, 2026-06-08, NVDA 10:00 short straddle 207.5 | −803.20, −378.9%, 2025-10-10, NVDA 10:00 short straddle 195.0 | 1.05 | 2,421 | 145 | 250% |
| TSLA | hold-out | +798.78, +77.4%, 2025-11-21, TSLA 10:00 short straddle 395.0 | −1,992.20, −427.1%, 2026-04-15, TSLA 10:00 short straddle 370.0 | 0.83 | 9,938 | 456 | total ≤ 0 (best 5 days +3,470; without them −9,098) |
| all names | hold-out | +2,454.74, +71.8%, 2026-06-12, MU 10:00 short straddle 985.0 | −7,237.26, −236.9%, 2026-07-02, MU 10:00 short straddle 1060.0 | 0.84 | 57,068 | 443 | total ≤ 0 (best 5 days +18,242; without them −54,316) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.80 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (5,859 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| AAPL | development | 283 | **−17.87**, −34.66 | −19.52, −37.26 | 49.8 / 49.1 | [−26.74, −4.24] / [−28.35, −5.92] |
| AMD | development | 284 | **−19.44**, −14.70 | −24.12, −17.30 | 50.4 / 48.2 | [−28.06, −9.69] / [−32.87, −14.20] |
| AMZN | development | 283 | **−18.33**, −304.99 | −18.63, −307.55 | 51.6 / 51.6 | [−26.52, −7.14] / [−26.79, −7.45] |
| AVGO | development | 284 | **−55.78**, −212.20 | −56.57, −214.80 | 31.7 / 31.0 | [−66.69, −42.24] / [−67.43, −43.02] |
| GOOGL | development | 283 | **−36.58**, −426.23 | −36.98, −428.81 | 41.7 / 41.7 | [−46.05, −23.83] / [−46.44, −24.19] |
| INTC | development | 283 | **−36.59**, −17.20 | −42.26, −19.80 | 41.0 / 39.9 | [−48.71, −24.04] / [−54.48, −29.44] |
| META | development | 284 | **−10.81**, −22.69 | −12.07, −25.29 | 52.5 / 52.1 | [−17.22, −1.13] / [−18.45, −2.33] |
| MSFT | development | 284 | **−33.74**, −47.48 | −36.16, −50.08 | 45.1 / 43.7 | [−43.70, −22.16] / [−46.26, −24.48] |
| MU | development | 284 | **−20.08**, −16.22 | −23.59, −18.82 | 51.1 / 50.7 | [−29.24, −8.91] / [−32.65, −12.50] |
| NVDA | development | 283 | **−8.78**, −51.35 | −9.58, −53.95 | 55.8 / 55.8 | [−16.83, −0.31] / [−17.63, −1.10] |
| TSLA | development | 282 | **−9.48**, −93.05 | −9.89, −95.64 | 57.1 / 57.1 | [−18.33, −0.81] / [−18.72, −1.20] |
| all names | development | 3,117 | **−24.33**, −112.72 | −26.32, −115.32 | 48.0 / 47.4 | [−28.82, −17.16] / [−30.82, −19.20] |
| AAPL | validation | 102 | **+5.16**, +5.84 | +3.45, +3.24 | 60.8 / 60.8 | [−0.92, +21.03] / [−2.56, +19.29] |
| AMD | validation | 102 | **−5.52**, −10.01 | −6.93, −12.60 | 58.8 / 57.8 | [−15.28, +11.32] / [−16.69, +10.03] |
| AMZN | validation | 102 | **−8.31**, −9.73 | −10.03, −12.33 | 52.9 / 52.9 | [−16.57, +7.97] / [−18.30, +6.15] |
| AVGO | validation | 101 | **−28.33**, −265.09 | −28.79, −267.68 | 48.5 / 47.5 | [−45.56, −9.94] / [−46.02, −10.45] |
| GOOGL | validation | 102 | **−17.99**, −21.20 | −20.12, −23.80 | 53.9 / 52.9 | [−31.46, −1.42] / [−33.58, −3.41] |
| INTC | validation | 102 | **−11.37**, −4.19 | −17.56, −6.79 | 62.7 / 59.8 | [−20.89, +3.78] / [−27.04, −2.17] |
| META | validation | 102 | **−14.17**, −38.63 | −14.87, −41.23 | 56.9 / 56.9 | [−32.49, +1.89] / [−33.14, +1.23] |
| MSFT | validation | 102 | **−16.14**, −39.27 | −17.09, −41.87 | 50.0 / 50.0 | [−31.11, −2.06] / [−32.02, −2.96] |
| MU | validation | 102 | **−9.65**, −11.40 | −12.21, −14.00 | 54.9 / 54.9 | [−16.99, +4.15] / [−19.70, +1.67] |
| NVDA | validation | 101 | **−15.30**, −164.44 | −16.01, −167.04 | 54.5 / 54.5 | [−30.21, +7.22] / [−30.76, +6.52] |
| TSLA | validation | 102 | **−3.76**, +1.93 | −4.47, −0.67 | 54.9 / 54.9 | [−14.69, +13.33] / [−15.41, +12.65] |
| all names | validation | 1,120 | **−11.38**, −50.27 | −13.13, −52.87 | 55.4 / 54.8 | [−17.28, −0.43] / [−19.02, −2.17] |
| AAPL | hold-out | 161 | **−12.79**, −28.53 | −13.89, −31.13 | 54.0 / 53.4 | [−29.37, −0.27] / [−30.49, −1.41] |
| AMD | hold-out | 116 | **−0.73**, +26.25 | −1.50, +23.66 | 60.3 / 60.3 | [−14.94, +8.72] / [−15.86, +8.01] |
| AMZN | hold-out | 161 | **−4.44**, −9.26 | −5.53, −11.86 | 60.9 / 60.9 | [−17.22, +6.96] / [−18.28, +5.86] |
| AVGO | hold-out | 159 | **−6.44**, −48.69 | −7.00, −51.28 | 53.5 / 53.5 | [−15.07, +2.08] / [−15.63, +1.50] |
| GOOGL | hold-out | 159 | **−11.39**, −29.38 | −12.32, −31.98 | 52.2 / 51.6 | [−25.56, −1.45] / [−26.47, −2.39] |
| INTC | hold-out | 116 | **−13.97**, −12.99 | −17.28, −15.59 | 54.3 / 51.7 | [−31.20, −1.03] / [−34.85, −4.09] |
| META | hold-out | 159 | **−11.19**, −60.96 | −11.56, −63.56 | 55.3 / 55.3 | [−25.81, −3.35] / [−26.18, −3.73] |
| MSFT | hold-out | 159 | **−14.77**, −46.33 | −15.47, −48.93 | 52.2 / 50.9 | [−34.37, −2.24] / [−35.07, −2.94] |
| MU | hold-out | 115 | **−10.27**, +26.65 | −10.96, +24.07 | 62.6 / 60.0 | [−27.84, +6.42] / [−28.77, +5.92] |
| NVDA | hold-out | 158 | **−0.56**, +3.22 | −1.71, +0.62 | 65.8 / 63.3 | [−15.00, +12.08] / [−16.12, +10.93] |
| TSLA | hold-out | 159 | **−6.77**, −35.40 | −7.21, −37.99 | 59.7 / 59.7 | [−20.47, +5.64] / [−20.89, +5.22] |
| all names | hold-out | 1,622 | **−8.50**, −22.24 | −9.47, −24.84 | 57.2 / 56.4 | [−18.41, −1.91] / [−19.41, −2.80] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development: bought back 15:50 100.0%
- validation: bought back 15:50 100.0%
- hold-out: bought back 15:50 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2017 | AAPL | 30 | 53.3 | −38.65 | −27.40 | −822 |
| 2018 | AAPL | 51 | 47.1 | −25.99 | −37.99 | −1,937 |
| 2019 | AAPL | 51 | 58.8 | −5.75 | −13.22 | −674 |
| 2020 | AAPL | 49 | 42.9 | −18.00 | −84.67 | −4,149 |
| 2021 | AAPL | 51 | 51.0 | −13.29 | −11.57 | −590 |
| 2022 | AAPL | 51 | 47.1 | −14.08 | −32.08 | −1,636 |
| 2023 | AAPL | 51 | 58.8 | +6.16 | +9.96 | +508 |
| 2024 | AAPL | 51 | 62.7 | +4.16 | +1.72 | +88 |
| 2025 | AAPL | 50 | 50.0 | −23.90 | −52.76 | −2,638 |
| 2026 | AAPL | 111 | 55.9 | −7.78 | −17.62 | −1,955 |
| 2017 | AMD | 30 | 50.0 | −30.95 | −7.77 | −233 |
| 2018 | AMD | 51 | 45.1 | −40.00 | −17.87 | −911 |
| 2019 | AMD | 51 | 45.1 | −15.26 | −6.89 | −351 |
| 2020 | AMD | 50 | 48.0 | −21.31 | −26.08 | −1,304 |
| 2021 | AMD | 51 | 51.0 | −15.00 | −18.75 | −956 |
| 2022 | AMD | 51 | 62.7 | +1.11 | −8.22 | −419 |
| 2023 | AMD | 51 | 56.9 | −9.40 | −7.75 | −395 |
| 2024 | AMD | 51 | 60.8 | −1.64 | −12.26 | −625 |
| 2025 | AMD | 50 | 54.0 | −13.31 | −19.66 | −983 |
| 2026 | AMD | 66 | 65.2 | +8.80 | +61.03 | +4,028 |
| 2017 | AMZN | 30 | 46.7 | −49.74 | −322.50 | −9,675 |
| 2018 | AMZN | 51 | 52.9 | −21.37 | −380.11 | −19,386 |
| 2019 | AMZN | 51 | 64.7 | −1.96 | −30.20 | −1,540 |
| 2020 | AMZN | 50 | 44.0 | −19.52 | −443.86 | −22,193 |
| 2021 | AMZN | 51 | 51.0 | −22.41 | −438.78 | −22,378 |
| 2022 | AMZN | 50 | 48.0 | −7.71 | −222.80 | −11,140 |
| 2023 | AMZN | 51 | 52.9 | −8.15 | −6.67 | −340 |
| 2024 | AMZN | 51 | 52.9 | −8.47 | −12.79 | −652 |
| 2025 | AMZN | 50 | 70.0 | −3.78 | −0.70 | −35 |
| 2026 | AMZN | 111 | 56.8 | −4.74 | −13.11 | −1,455 |
| 2017 | AVGO | 30 | 33.3 | −91.66 | −203.83 | −6,115 |
| 2018 | AVGO | 51 | 33.3 | −32.53 | −88.30 | −4,503 |
| 2019 | AVGO | 51 | 51.0 | −17.84 | −37.79 | −1,927 |
| 2020 | AVGO | 50 | 20.0 | −68.55 | −266.56 | −13,328 |
| 2021 | AVGO | 51 | 15.7 | −99.57 | −400.65 | −20,433 |
| 2022 | AVGO | 51 | 37.3 | −39.53 | −273.67 | −13,957 |
| 2023 | AVGO | 51 | 43.1 | −40.88 | −348.99 | −17,799 |
| 2024 | AVGO | 50 | 54.0 | −15.53 | −179.52 | −8,976 |
| 2025 | AVGO | 50 | 56.0 | −7.23 | −35.74 | −1,787 |
| 2026 | AVGO | 109 | 52.3 | −6.07 | −54.62 | −5,954 |
| 2017 | GOOGL | 30 | 33.3 | −61.32 | −289.07 | −8,672 |
| 2018 | GOOGL | 51 | 33.3 | −46.95 | −462.19 | −23,572 |
| 2019 | GOOGL | 51 | 51.0 | −15.02 | −82.68 | −4,216 |
| 2020 | GOOGL | 50 | 42.0 | −34.67 | −425.80 | −21,290 |
| 2021 | GOOGL | 51 | 43.1 | −45.53 | −739.78 | −37,729 |
| 2022 | GOOGL | 50 | 44.0 | −25.94 | −502.89 | −25,145 |
| 2023 | GOOGL | 51 | 56.9 | −17.54 | −13.28 | −677 |
| 2024 | GOOGL | 51 | 51.0 | −18.44 | −29.12 | −1,485 |
| 2025 | GOOGL | 50 | 60.0 | −12.72 | −11.36 | −568 |
| 2026 | GOOGL | 109 | 48.6 | −10.79 | −37.65 | −4,104 |
| 2017 | INTC | 29 | 24.1 | −62.75 | −15.96 | −463 |
| 2018 | INTC | 51 | 29.4 | −81.58 | −40.28 | −2,054 |
| 2019 | INTC | 51 | 54.9 | −9.42 | −3.73 | −190 |
| 2020 | INTC | 50 | 42.0 | −34.85 | −19.80 | −990 |
| 2021 | INTC | 51 | 45.1 | −31.44 | −19.24 | −981 |
| 2022 | INTC | 51 | 43.1 | −10.72 | −3.71 | −189 |
| 2023 | INTC | 51 | 56.9 | −15.05 | −5.99 | −305 |
| 2024 | INTC | 51 | 68.6 | −7.68 | −2.40 | −122 |
| 2025 | INTC | 50 | 48.0 | −30.93 | −16.36 | −818 |
| 2026 | INTC | 66 | 59.1 | −1.13 | −10.44 | −689 |
| 2017 | META | 30 | 43.3 | −31.80 | −29.70 | −891 |
| 2018 | META | 51 | 41.2 | −20.15 | −38.53 | −1,965 |
| 2019 | META | 51 | 66.7 | +6.85 | +13.09 | +668 |
| 2020 | META | 50 | 50.0 | −22.11 | −60.86 | −3,043 |
| 2021 | META | 51 | 56.9 | −1.40 | −4.79 | −244 |
| 2022 | META | 51 | 52.9 | −5.12 | −19.01 | −969 |
| 2023 | META | 51 | 49.0 | −26.54 | −82.20 | −4,192 |
| 2024 | META | 51 | 64.7 | −1.79 | +4.94 | +252 |
| 2025 | META | 50 | 38.0 | −15.32 | −78.88 | −3,944 |
| 2026 | META | 109 | 63.3 | −9.30 | −52.74 | −5,749 |
| 2017 | MSFT | 30 | 43.3 | −80.99 | −31.10 | −933 |
| 2018 | MSFT | 51 | 43.1 | −56.62 | −46.63 | −2,378 |
| 2019 | MSFT | 51 | 51.0 | −10.56 | −10.63 | −542 |
| 2020 | MSFT | 50 | 40.0 | −26.77 | −49.10 | −2,455 |
| 2021 | MSFT | 51 | 45.1 | −19.05 | −50.06 | −2,553 |
| 2022 | MSFT | 51 | 47.1 | −27.74 | −90.65 | −4,623 |
| 2023 | MSFT | 51 | 49.0 | −24.22 | −58.93 | −3,005 |
| 2024 | MSFT | 51 | 51.0 | −8.07 | −19.61 | −1,000 |
| 2025 | MSFT | 50 | 42.0 | −17.86 | −56.32 | −2,816 |
| 2026 | MSFT | 109 | 56.9 | −13.35 | −41.75 | −4,551 |
| 2017 | MU | 30 | 40.0 | −55.95 | −23.77 | −713 |
| 2018 | MU | 51 | 47.1 | −16.14 | −11.83 | −603 |
| 2019 | MU | 51 | 51.0 | −6.40 | −3.30 | −168 |
| 2020 | MU | 50 | 54.0 | −40.51 | −34.58 | −1,729 |
| 2021 | MU | 51 | 56.9 | −13.95 | −21.61 | −1,102 |
| 2022 | MU | 51 | 52.9 | −2.73 | −5.69 | −290 |
| 2023 | MU | 51 | 54.9 | −8.19 | −7.06 | −360 |
| 2024 | MU | 51 | 54.9 | −11.11 | −15.73 | −802 |
| 2025 | MU | 50 | 50.0 | −30.11 | −49.04 | −2,452 |
| 2026 | MU | 65 | 72.3 | +5.00 | +84.88 | +5,517 |
| 2017 | NVDA | 30 | 50.0 | −24.55 | −70.90 | −2,127 |
| 2018 | NVDA | 51 | 56.9 | −7.20 | −16.83 | −858 |
| 2019 | NVDA | 51 | 68.6 | +7.19 | +17.76 | +906 |
| 2020 | NVDA | 50 | 36.0 | −36.47 | −247.80 | −12,390 |
| 2021 | NVDA | 50 | 68.0 | +8.05 | +30.50 | +1,525 |
| 2022 | NVDA | 51 | 52.9 | −6.43 | −31.12 | −1,587 |
| 2023 | NVDA | 51 | 54.9 | −17.06 | −79.63 | −4,061 |
| 2024 | NVDA | 50 | 54.0 | −13.50 | −250.95 | −12,547 |
| 2025 | NVDA | 50 | 72.0 | +0.31 | +9.04 | +452 |
| 2026 | NVDA | 108 | 63.0 | −0.97 | +0.52 | +56 |
| 2017 | TSLA | 30 | 63.3 | −26.55 | −86.40 | −2,592 |
| 2018 | TSLA | 51 | 54.9 | −8.34 | −59.04 | −3,011 |
| 2019 | TSLA | 51 | 58.8 | −7.48 | −45.12 | −2,301 |
| 2020 | TSLA | 49 | 61.2 | −1.05 | −127.33 | −6,239 |
| 2021 | TSLA | 51 | 54.9 | −5.11 | −44.42 | −2,265 |
| 2022 | TSLA | 50 | 52.0 | −15.14 | −196.64 | −9,832 |
| 2023 | TSLA | 51 | 54.9 | −6.79 | −4.14 | −211 |
| 2024 | TSLA | 51 | 54.9 | −0.74 | +7.99 | +408 |
| 2025 | TSLA | 50 | 66.0 | −3.97 | −2.58 | −129 |
| 2026 | TSLA | 109 | 56.9 | −8.05 | −50.45 | −5,499 |
| 2017 | all names | 329 | 43.8 | −50.41 | −101.02 | −33,236 |
| 2018 | all names | 561 | 44.0 | −32.44 | −109.05 | −61,180 |
| 2019 | all names | 561 | 56.5 | −6.88 | −18.43 | −10,338 |
| 2020 | all names | 548 | 43.6 | −29.51 | −162.61 | −89,111 |
| 2021 | all names | 560 | 48.9 | −23.57 | −156.62 | −87,708 |
| 2022 | all names | 558 | 49.1 | −13.99 | −125.07 | −69,789 |
| 2023 | all names | 561 | 53.5 | −15.24 | −54.97 | −30,839 |
| 2024 | all names | 559 | 57.2 | −7.50 | −45.55 | −25,464 |
| 2025 | all names | 550 | 55.1 | −14.44 | −28.58 | −15,719 |
| 2026 | all names | 1,072 | 58.3 | −5.45 | −18.99 | −20,355 |

![](charts/s8d.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Negative.

## #8e V8: month-end 13:00 long straddle on unread chains

**Folder:** `research/compass/intel/, studies/v*.py, results/v1/ (@7dfea57)`. **Commits:** A15 8bc3baf / — / e4e4cea. **Dates:** 2026-10-16.

**Hypothesis.** Month-end afternoons move more than priced (from V7).

**Rule.** Buy the ATM straddle at 13:00 on the month's last session, hold to settlement.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Ask in (adverse); settlement out.

**Data.** SPXW 2017-06 → 2022-04, SPY 2017-06 → 2022-10 (chains no study had read).

**Periods and holdouts.** One unread span.

**Pass rule (as pre-registered).** A15.

**Verdict.** Rejected: SPXW −6.6% [−24.5, +12.6], SPY −8.4% [−27.2, +11.3].

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | 2017-06→2022 (unread chains) | 56 | 56 / 1,251 | 41.1 | +61.9, +810.44 | −57.6, −808.56 | −24.7, −289.26 | **−8.51**, −143.62 | [−26.73, +11.41]; [−475.31, +118.60] |
| SPY | 2017-06→2022 (unread chains) | 49 | 49 / 1,382 | 36.7 | +65.6, +109.64 | −52.2, −95.19 | −29.7, −39.08 | **−8.94**, −19.95 | [−23.93, +13.10]; [−52.12, +20.74] |
| all names | 2017-06→2022 (unread chains) | 105 | 62 / 1,382 | 39.0 | +63.5, +502.77 | −55.0, −463.02 | −28.7, −54.58 | **−8.71**, −85.91 | [−23.53, +11.40]; [−258.98, +99.54] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | 2017-06→2022 (unread chains) | +3,220.74, +154.1%, 2022-03-31, SPXW 13:00 long straddle 4585.0 | −3,553.26, −78.9%, 2020-02-28, SPXW 13:00 long straddle 2945.0 | 0.70 | 15,944 | 971 | total ≤ 0 (best 5 days +11,961; without them −20,003) |
| SPY | 2017-06→2022 (unread chains) | +303.92, +133.9%, 2022-03-31, SPY 13:00 long straddle 457.0 | −377.08, −78.2%, 2020-02-28, SPY 13:00 long straddle 295.0 | 0.67 | 1,823 | 1,190 | total ≤ 0 (best 5 days +1,337; without them −2,314) |
| all names | 2017-06→2022 (unread chains) | +3,220.74, +154.1%, 2022-03-31, SPXW 13:00 long straddle 4585.0 | −3,553.26, −78.9%, 2020-02-28, SPXW 13:00 long straddle 2945.0 | 0.70 | 17,754 | 1,102 | total ≤ 0 (best 5 days +13,098; without them −22,118) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $1.24). The study's fees are given beside them below. Re-pricing: exact (105 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | 2017-06→2022 (unread chains) | 56 | **−8.51**, −143.62 | −8.42, −142.76 | 41.1 / 41.1 | [−26.73, +11.41] / [−26.64, +11.50] |
| SPY | 2017-06→2022 (unread chains) | 49 | **−8.94**, −19.95 | −9.96, −21.27 | 36.7 / 36.7 | [−23.93, +13.10] / [−24.94, +12.12] |
| all names | 2017-06→2022 (unread chains) | 105 | **−8.71**, −85.91 | −9.14, −86.06 | 39.0 / 39.0 | [−23.53, +11.40] / [−23.88, +10.99] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- 2017-06→2022 (unread chains): held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2017 | SPXW | 7 | 42.9 | −25.25 | −95.83 | −671 |
| 2018 | SPXW | 11 | 45.5 | +10.50 | +44.19 | +486 |
| 2019 | SPXW | 10 | 30.0 | −23.62 | −236.76 | −2,368 |
| 2020 | SPXW | 12 | 41.7 | −3.04 | −368.01 | −4,416 |
| 2021 | SPXW | 12 | 33.3 | −31.32 | −541.34 | −6,496 |
| 2022 | SPXW | 4 | 75.0 | +58.32 | +1,355.49 | +5,422 |
| 2017 | SPY | 3 | 33.3 | −2.40 | −0.08 | −0 |
| 2018 | SPY | 9 | 33.3 | +15.59 | +6.70 | +60 |
| 2019 | SPY | 6 | 16.7 | −51.70 | −48.58 | −291 |
| 2020 | SPY | 11 | 45.5 | +0.47 | −43.63 | −480 |
| 2021 | SPY | 10 | 30.0 | −41.59 | −63.48 | −635 |
| 2022 | SPY | 10 | 50.0 | +14.98 | +36.87 | +369 |
| 2017 | all names | 10 | 40.0 | −18.40 | −67.11 | −671 |
| 2018 | all names | 20 | 40.0 | +12.79 | +27.32 | +546 |
| 2019 | all names | 16 | 25.0 | −34.15 | −166.19 | −2,659 |
| 2020 | all names | 23 | 43.5 | −1.36 | −212.87 | −4,896 |
| 2021 | all names | 22 | 31.8 | −35.99 | −324.13 | −7,131 |
| 2022 | all names | 14 | 57.1 | +27.37 | +413.62 | +5,791 |

![](charts/s8e.png)

**Amendments, deviations and integrity checks.** Read once on unread chains.

**What it showed.** The month-end effect V7 suggested did not appear on unread data.

## #9a Lifecycle P1: Quick Scalps → cash-secured put sale (portfolio)

**Folder:** `research/compass/lifecycle/ (@7dfea57)`. **Commits:** protocol 1f99d75 / L-A4 8bd322a / 425c7f4, b9d04b5. **Dates:** 2026-10-15.

**Hypothesis.** The Tier I finalists, run as a portfolio, earn after costs.

**Rule.** QS signal → sell a cash-secured put (s20 policy), one unit, the lifecycle position engine.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side, NBBO.

**Data.** SPY/QQQ/IWM 0DTE 2022-11 → 2026-10.

**Periods and holdouts.** development + validation / hold-out 2025-10-01 → 2026-10-09 (opened once).

**Pass rule (as pre-registered).** R1–R6 promotion rules (Holm; R2 random-day control).

**Verdict.** Rejected: hold-out +$987 (about 1% a year, collateral-bound).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | development + validation | 88 | 78 / 318 | 56.8 | +0.1, +26.45 | −0.2, −37.34 | +0.0, +10.40 | **−0.01**, −1.09 | [−0.05, +0.03]; [−9.52, +6.92] |
| QQQ | development + validation | 165 | 157 / 738 | 61.8 | +0.1, +45.84 | −0.1, −58.91 | +0.1, +27.90 | **+0.01**, +5.84 | [−0.00, +0.03]; [−2.44, +13.34] |
| SPY | development + validation | 155 | 148 / 742 | 62.6 | +0.1, +46.81 | −0.1, −59.34 | +0.1, +27.90 | **+0.01**, +7.09 | [−0.00, +0.03]; [−1.56, +14.65] |
| all names | development + validation | 408 | 269 / 742 | 61.0 | +0.1, +42.32 | −0.1, −53.91 | +0.1, +22.40 | **+0.01**, +4.82 | [−0.00, +0.02]; [−0.06, +9.09] |
| IWM | hold-out 2025-10→2026-10 | 51 | 48 / 259 | 49.0 | +0.1, +33.06 | −0.2, −41.87 | −0.0, −13.10 | **−0.02**, −5.14 | [−0.06, +0.02]; [−15.48, +5.30] |
| QQQ | hold-out 2025-10→2026-10 | 32 | 32 / 252 | 81.2 | +0.1, +71.86 | −0.2, −98.10 | +0.1, +59.90 | **+0.06**, +39.99 | [+0.03, +0.10]; [+17.30, +69.30] |
| SPY | hold-out 2025-10→2026-10 | 39 | 35 / 240 | 66.7 | +0.1, +51.78 | −0.1, −93.72 | +0.1, +34.90 | **+0.00**, +3.28 | [−0.04, +0.04]; [−24.04, +27.80] |
| all names | hold-out 2025-10→2026-10 | 122 | 89 / 262 | 63.1 | +0.1, +52.48 | −0.2, −64.35 | +0.1, +30.40 | **+0.01**, +9.39 | [−0.02, +0.04]; [−5.59, +23.17] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | development + validation | +98.90, +0.4%, 2025-09-17, IWM CSP m85 | −84.10, −0.4%, 2024-07-17, IWM CSP m16 | 0.93 | 464 | 240 | total ≤ 0 (best 5 days +286; without them −383) |
| QQQ | development + validation | +171.90, +0.4%, 2025-04-11, QQQ CSP m181 | −167.10, −0.4%, 2025-04-23, QQQ CSP m54 | 1.26 | 513 | 195 | 61% |
| SPY | development + validation | +243.90, +0.5%, 2025-04-11, SPY CSP m75 | −197.10, −0.4%, 2025-04-10, SPY CSP m309 | 1.32 | 440 | 218 | 62% |
| all names | development + validation | +243.90, +0.5%, 2025-04-11, SPY CSP m75 | −197.10, −0.4%, 2025-04-10, SPY CSP m309 | 1.23 | 923 | 195 | 52% |
| IWM | hold-out 2025-10→2026-10 | +91.90, +0.3%, 2026-06-12, IWM CSP m21 | −114.10, −0.5%, 2025-10-29, IWM CSP m139 | 0.76 | 301 | 248 | total ≤ 0 (best 5 days +273; without them −536) |
| QQQ | hold-out 2025-10→2026-10 | +136.90, +0.2%, 2026-08-03, QQQ CSP m15 | −166.10, −0.3%, 2025-10-29, QQQ CSP m44 | 3.17 | 210 | 129 | 47% |
| SPY | hold-out 2025-10→2026-10 | +91.90, +0.1%, 2026-04-01, SPY CSP m38 | −197.10, −0.3%, 2025-10-14, SPY CSP m283 | 1.11 | 507 | 147 | 327% |
| all names | hold-out 2025-10→2026-10 | +136.90, +0.2%, 2026-08-03, QQQ CSP m15 | −197.10, −0.3%, 2025-10-14, SPY CSP m283 | 1.40 | 763 | 82 | 62% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.40 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: Robinhood fees inferred from the rule: the legs' prices and the expiry exercise fee are not in the trade file (530 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | development + validation | 88 | **−0.01**, −1.09 | −0.01, −2.39 | 56.8 / 56.8 | [−0.05, +0.03] / [−0.05, +0.02] |
| QQQ | development + validation | 165 | **+0.01**, +5.84 | +0.01, +4.54 | 61.8 / 61.8 | [−0.00, +0.03] / [−0.01, +0.03] |
| SPY | development + validation | 155 | **+0.01**, +7.09 | +0.01, +5.79 | 62.6 / 62.6 | [−0.00, +0.03] / [−0.00, +0.03] |
| all names | development + validation | 408 | **+0.01**, +4.82 | +0.01, +3.52 | 61.0 / 61.0 | [−0.00, +0.02] / [−0.01, +0.02] |
| IWM | hold-out 2025-10→2026-10 | 51 | **−0.02**, −5.14 | −0.02, −6.44 | 49.0 / 49.0 | [−0.06, +0.02] / [−0.06, +0.02] |
| QQQ | hold-out 2025-10→2026-10 | 32 | **+0.06**, +39.99 | +0.06, +38.69 | 81.2 / 81.2 | [+0.03, +0.10] / [+0.02, +0.10] |
| SPY | hold-out 2025-10→2026-10 | 39 | **+0.00**, +3.28 | +0.00, +1.98 | 66.7 / 66.7 | [−0.04, +0.04] / [−0.04, +0.04] |
| all names | hold-out 2025-10→2026-10 | 122 | **+0.01**, +9.39 | +0.01, +8.09 | 63.1 / 63.1 | [−0.02, +0.04] / [−0.02, +0.03] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development + validation: policy 100.0%
- hold-out 2025-10→2026-10: policy 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 36 | 58.3 | −0.00 | −0.10 | −4 |
| 2025 | IWM | 66 | 54.5 | −0.01 | −2.67 | −176 |
| 2026 | IWM | 37 | 48.6 | −0.02 | −4.83 | −179 |
| 2022 | QQQ | 6 | 83.3 | +0.08 | +20.23 | +121 |
| 2023 | QQQ | 76 | 57.9 | +0.01 | +2.49 | +189 |
| 2024 | QQQ | 48 | 62.5 | +0.02 | +8.25 | +396 |
| 2025 | QQQ | 40 | 65.0 | +0.01 | +4.02 | +161 |
| 2026 | QQQ | 27 | 85.2 | +0.07 | +50.97 | +1,376 |
| 2022 | SPY | 7 | 85.7 | +0.08 | +32.61 | +228 |
| 2023 | SPY | 59 | 55.9 | +0.01 | +3.39 | +200 |
| 2024 | SPY | 54 | 68.5 | +0.02 | +12.50 | +675 |
| 2025 | SPY | 47 | 61.7 | −0.00 | −1.44 | −68 |
| 2026 | SPY | 27 | 66.7 | +0.01 | +7.08 | +191 |
| 2022 | all names | 13 | 84.6 | +0.08 | +26.90 | +350 |
| 2023 | all names | 135 | 57.0 | +0.01 | +2.88 | +389 |
| 2024 | all names | 138 | 63.8 | +0.02 | +7.74 | +1,068 |
| 2025 | all names | 153 | 59.5 | −0.00 | −0.54 | −83 |
| 2026 | all names | 91 | 64.8 | +0.02 | +15.26 | +1,389 |

![](charts/s9a.png)

**Amendments, deviations and integrity checks.** A superseded hold-out file is kept separately.

**What it showed.** The put sale earns cents on the cash it ties up.

## #9b Lifecycle P2: Quick Scalps → credit put spread to expiry (portfolio)

**Folder:** `research/compass/lifecycle/ (@7dfea57)`. **Commits:** 1f99d75 / L-A4 / d8a7ebb. **Dates:** 2026-10-15.

**Hypothesis.** As P1 with a defined-risk spread.

**Rule.** QS signal → credit put spread held to expiry.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As P1.

**Data.** SPY/QQQ/IWM/SPXW 0DTE.

**Periods and holdouts.** As P1.

**Pass rule (as pre-registered).** As P1.

**Verdict.** Rejected: hold-out −$6,805.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | development + validation | 80 | 80 / 335 | 93.8 | +12.9, +112.46 | −67.6, −614.64 | +8.1, +74.56 | **+7.83**, +67.01 | [+5.39, +13.17]; [+45.16, +114.00] |
| QQQ | development + validation | 173 | 173 / 738 | 89.6 | +14.0, +124.25 | −108.0, −959.24 | +9.8, +89.56 | **+1.26**, +11.51 | [−6.04, +7.97]; [−54.56, +71.24] |
| SPXW | development + validation | 182 | 182 / 844 | 85.2 | +12.0, +106.03 | −79.8, −703.62 | +11.5, +102.74 | **−1.66**, −14.09 | [−7.34, +3.03]; [−64.09, +27.31] |
| SPY | development + validation | 169 | 169 / 742 | 92.3 | +13.5, +120.52 | −98.2, −830.68 | +9.2, +84.56 | **+4.91**, +47.35 | [−1.92, +11.38]; [−12.08, +103.91] |
| all names | development + validation | 604 | 299 / 844 | 89.6 | +13.1, +116.32 | −90.7, −795.81 | +9.8, +89.56 | **+2.27**, +21.18 | [−2.26, +5.99]; [−18.54, +53.64] |
| IWM | hold-out 2025-10→2026-10 | 53 | 53 / 259 | 79.2 | +7.7, +66.86 | −87.2, −795.58 | +6.3, +54.56 | **−11.97**, −112.14 | [−23.36, −3.21]; [−216.18, −31.72] |
| QQQ | hold-out 2025-10→2026-10 | 48 | 48 / 252 | 95.8 | +16.8, +147.16 | −100.8, −889.94 | +10.4, +89.56 | **+11.89**, +103.95 | [−1.34, +21.64]; [−16.34, +191.82] |
| SPXW | hold-out 2025-10→2026-10 | 47 | 47 / 261 | 89.4 | +11.1, +98.93 | −99.8, −882.92 | +10.9, +97.74 | **−0.73**, −5.52 | [−11.24, +8.66]; [−98.70, +77.67] |
| SPY | hold-out 2025-10→2026-10 | 48 | 48 / 261 | 87.5 | +16.2, +149.39 | −199.0, −1,825.69 | +9.8, +89.56 | **−10.73**, −97.50 | [−45.02, +8.20]; [−415.90, +78.51] |
| all names | hold-out 2025-10→2026-10 | 196 | 91 / 262 | 87.8 | +13.0, +116.32 | −118.9, −1,079.17 | +9.2, +84.56 | **−3.13**, −30.07 | [−15.66, +4.66]; [−146.03, +40.69] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | development + validation | +1,571.06, +179.5%, 2024-07-25, IWM CPS m163 | −887.44, −100.8%, 2024-07-24, IWM CPS m140 | 2.74 | 887 | 44 | 62% |
| QQQ | development + validation | +1,766.06, +187.9%, 2024-03-06, QQQ CPS m226 | −2,153.94, −238.0%, 2023-02-03, QQQ CPS m105 | 1.12 | 5,931 | 590 | 279% |
| SPXW | development + validation | +157.74, +18.8%, 2024-07-31, SPXW CPS m76 | −943.66, −100.4%, 2024-07-12, SPXW CPS m311 | 0.87 | 5,356 | 416 | total ≤ 0 (best 5 days +754; without them −3,318) |
| SPY | development + validation | +2,461.06, +284.5%, 2025-06-05, SPY CPS m85 | −1,503.94, −168.0%, 2023-02-03, SPY CPS m92 | 1.74 | 4,686 | 304 | 65% |
| all names | development + validation | +2,461.06, +284.5%, 2025-06-05, SPY CPS m85 | −2,153.94, −238.0%, 2023-02-03, QQQ CPS m105 | 1.26 | 9,144 | 496 | 68% |
| IWM | hold-out 2025-10→2026-10 | +114.56, +12.9%, 2026-03-31, IWM CPS m225 | −2,353.94, −255.9%, 2026-01-16, IWM CPS m187 | 0.32 | 6,493 | 241 | total ≤ 0 (best 5 days +548; without them −6,491) |
| QQQ | hold-out 2025-10→2026-10 | +1,781.06, +196.8%, 2026-02-10, QQQ CPS m61 | −902.44, −100.8%, 2026-08-28, QQQ CPS m123 | 3.80 | 902 | 56 | 66% |
| SPXW | hold-out 2025-10→2026-10 | +137.74, +16.0%, 2026-08-27, SPXW CPS m21 | −898.66, −100.4%, 2025-10-14, SPXW CPS m283 | 0.94 | 1,835 | 203 | total ≤ 0 (best 5 days +634; without them −893) |
| SPY | hold-out 2025-10→2026-10 | +1,951.06, +204.3%, 2025-10-14, SPY CPS m283 | −5,188.94, −558.0%, 2026-01-16, SPY CPS m316 | 0.57 | 8,609 | 250 | total ≤ 0 (best 5 days +3,081; without them −7,761) |
| all names | hold-out 2025-10→2026-10 | +1,951.06, +204.3%, 2025-10-14, SPY CPS m283 | −5,188.94, −558.0%, 2026-01-16, SPY CPS m316 | 0.77 | 11,888 | 251 | total ≤ 0 (best 5 days +5,214; without them −11,107) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $5.39 a trade) and Robinhood's charged instead (mean $0.97). The study's fees are given beside them below. Re-pricing: Robinhood fees inferred from the rule: the legs' prices and the expiry exercise fee are not in the trade file (800 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | development + validation | 80 | **+7.83**, +67.01 | +7.11, +60.54 | 93.8 / 93.8 | [+5.39, +13.17] / [+4.68, +12.45] |
| QQQ | development + validation | 173 | **+1.26**, +11.51 | +0.52, +4.89 | 89.6 / 89.6 | [−6.04, +7.97] / [−6.78, +7.22] |
| SPXW | development + validation | 182 | **−1.66**, −14.09 | −1.56, −13.21 | 85.2 / 85.2 | [−7.34, +3.03] / [−7.24, +3.13] |
| SPY | development + validation | 169 | **+4.91**, +47.35 | +4.17, +40.71 | 92.3 / 92.3 | [−1.92, +11.38] / [−2.65, +10.65] |
| all names | development + validation | 604 | **+2.27**, +21.18 | +1.79, +16.83 | 89.6 / 89.6 | [−2.26, +5.99] / [−2.76, +5.49] |
| IWM | hold-out 2025-10→2026-10 | 53 | **−11.97**, −112.14 | −12.68, −118.47 | 79.2 / 79.2 | [−23.36, −3.21] / [−24.08, −3.92] |
| QQQ | hold-out 2025-10→2026-10 | 48 | **+11.89**, +103.95 | +11.17, +97.67 | 95.8 / 95.8 | [−1.34, +21.64] / [−2.07, +20.92] |
| SPXW | hold-out 2025-10→2026-10 | 47 | **−0.73**, −5.52 | −0.64, −4.66 | 89.4 / 89.4 | [−11.24, +8.66] / [−11.14, +8.75] |
| SPY | hold-out 2025-10→2026-10 | 48 | **−10.73**, −97.50 | −11.45, −104.05 | 87.5 / 87.5 | [−45.02, +8.20] / [−45.74, +7.48] |
| all names | hold-out 2025-10→2026-10 | 196 | **−3.13**, −30.07 | −3.65, −34.72 | 87.8 / 87.8 | [−15.66, +4.66] / [−16.19, +4.15] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development + validation: policy 100.0%
- hold-out 2025-10→2026-10: policy 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 31 | 96.8 | +12.09 | +99.03 | +3,070 |
| 2025 | IWM | 62 | 90.3 | +2.54 | +21.84 | +1,354 |
| 2026 | IWM | 40 | 77.5 | −13.50 | −125.16 | −5,006 |
| 2022 | QQQ | 6 | 100.0 | +11.33 | +101.70 | +610 |
| 2023 | QQQ | 68 | 85.3 | −6.27 | −58.75 | −3,995 |
| 2024 | QQQ | 53 | 88.7 | +5.89 | +57.16 | +3,030 |
| 2025 | QQQ | 56 | 94.6 | +6.39 | +56.61 | +3,170 |
| 2026 | QQQ | 38 | 97.4 | +12.58 | +109.64 | +4,166 |
| 2022 | SPXW | 28 | 85.7 | −2.86 | −24.25 | −679 |
| 2023 | SPXW | 51 | 86.3 | +2.29 | +20.11 | +1,026 |
| 2024 | SPXW | 56 | 80.4 | −6.60 | −58.25 | −3,262 |
| 2025 | SPXW | 57 | 87.7 | −1.37 | −10.86 | −619 |
| 2026 | SPXW | 37 | 91.9 | +2.01 | +19.21 | +711 |
| 2022 | SPY | 7 | 100.0 | +14.56 | +119.16 | +834 |
| 2023 | SPY | 54 | 92.6 | +3.66 | +33.88 | +1,829 |
| 2024 | SPY | 61 | 86.9 | −2.38 | −10.61 | −647 |
| 2025 | SPY | 58 | 94.8 | +12.99 | +117.73 | +6,828 |
| 2026 | SPY | 37 | 89.2 | −16.06 | −149.25 | −5,522 |
| 2022 | all names | 41 | 90.2 | +2.19 | +18.67 | +765 |
| 2023 | all names | 173 | 87.9 | −0.65 | −6.59 | −1,140 |
| 2024 | all names | 201 | 87.1 | +0.85 | +10.90 | +2,191 |
| 2025 | all names | 233 | 91.8 | +5.11 | +46.07 | +10,734 |
| 2026 | all names | 152 | 88.8 | −3.82 | −37.18 | −5,652 |

![](charts/s9b.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Loses on the hold-out.

## #9c Lifecycle Tier I, daily tier, L-A3, H-FLO (by configuration)

**Folder:** `research/compass/lifecycle/ (@7dfea57)`. **Commits:** 1f99d75 / L-A2, L-A3 889691a, L-A4 8bd322a, L-A4.1 f815d27 / 425c7f4, f6d5a98, d8a7ebb, 66bc5c9, 50de62a. **Dates:** 2026-10-15.

**Hypothesis.** Some of 12 setups × 8 structures × 116 management policies (Tier I) or daily setups (Tier D) survive a hold-out.

**Rule.** Grids; finalists chosen on development + validation.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.70 a contract each side, NBBO.

**Data.** 0DTE SPY/QQQ/IWM/SPXW; index-ETF option EOD 2012-06 → 2026-10.

**Periods and holdouts.** hold-out 2025-10-01 → 2026-10-09, opened once per group.

**Pass rule (as pre-registered).** R1–R6.

**Verdict.** 0 promoted: Tier I no long-premium policy with a positive lower bound, finalists all put sales; L-A3 debit call spread +$64.37 [−18.16, +138.67] p 0.064 (fail); daily tier 19 finalists, all fail R2 (random day); H-FLO a regime descriptor, not an edge.

**Metrics.** not available — committed as configuration-level cells (grid_by_setup.csv, cells.csv); the trade rows are in the scratchpad (lifecycle/archive, 281 MB) and were not re-run for this report.

**Amendments, deviations and integrity checks.** Random-minute look-ahead corrected (L-A2) before the hold-out.

**What it showed.** No configuration survived the hold-out.

## #10 ATM straddle samples and the independent short-premium prereg (branch compass-research-2026-10-14)

**Folder:** `research/compass_2026_10_14/ on origin/compass-research-2026-10-14`. **Commits:** short_premium PREREG 2f97a0c / — / BLOCKED. **Dates:** 2026-10-14 → 15.

**Hypothesis.** (Measurement) what short-dated ATM straddles cost on 10 names.

**Rule.** —

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** 8–19 sessions a name.

**Periods and holdouts.** —

**Pass rule (as pre-registered).** —

**Verdict.** No result: the short-premium study was blocked (ThetaData session invalidated off-box).

**Metrics.** not available — price samples only (no trade with an exit); the pre-registered study never ran.

**Amendments, deviations and integrity checks.** —

**What it showed.** Medians of ATM straddle prices; no strategy.

## #11 Price-action catalogue and atlas (43 names)

**Folder:** `research/compass/intel/04, 06, 07 (@7dfea57)`. **Commits:** — / — / 048d33a, 0d706b6, 98fa5f0. **Dates:** 2026-10-15.

**Hypothesis.** (Descriptive) how price action behaves around levels.

**Rule.** —

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** 43 names 2017–2026 bars.

**Periods and holdouts.** —

**Pass rule (as pre-registered).** —

**Verdict.** Descriptive; V6 tested its levels (rejected).

**Metrics.** not available — descriptive tables, no trades.

**Amendments, deviations and integrity checks.** —

**What it showed.** No strategy.

# Part B. Studies after the fresh start

## #12 Step 1: every 0DTE contract broken down

**Folder:** `step1/`. **Commits:** — / — / 2185eb9. **Dates:** 2026-10-16.

**Hypothesis.** (Descriptive) the anatomy of 1,176,935 same-day contracts over 3,687 sessions.

**Rule.** —

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** SPY, QQQ, IWM, SPX 0DTE.

**Periods and holdouts.** —

**Pass rule (as pre-registered).** —

**Verdict.** Descriptive.

**Metrics.** not available — a contract inventory, no trades.

**Amendments, deviations and integrity checks.** Checked against the raw quotes (verify.py).

**What it showed.** No strategy.

## #13 Step 2: buy near the money, sell at +100% or hold (within 0.5% of the price)

**Folder:** `step2/`. **Commits:** — / — / b15b56b. **Dates:** 2026-10-16.

**Hypothesis.** A same-day contract that can double pays for those that do not.

**Rule.** Buy every contract within 0.5% of the underlying at the ask at 9:31, 10:00, 10:30, 11:00, 12:00, 1:00, 2:00, 3:00, 3:30; sell the first minute the bid reaches 2× the price paid (at exactly 2×), else hold to the close (worth intrinsic).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract on the buy and on the sale; none when it expires worthless.

**Data.** SPY, QQQ, IWM, SPX 0DTE 2022-05-13 → 2026-10-09 (the near-the-money slice of 10,547,433 trades).

**Periods and holdouts.** pick 2022–24 / check 2025–26 (no holdout; holdout B months read).

**Pass rule (as pre-registered).** None pre-registered (a population study).

**Verdict.** Every group loses before and after fees; near the money 29% double, below the share needed to break even.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | pick 2022–24 | 6,960 | 177 / 182 | 38.0 | +84.1, +54.63 | −84.6, −49.19 | −62.8, −13.04 | **−20.47**, −9.75 | [−24.27, −17.67]; [−11.94, −8.14] |
| QQQ | pick 2022–24 | 39,574 | 536 / 553 | 38.6 | +83.2, +95.68 | −84.8, −86.19 | −59.7, −23.04 | **−19.94**, −15.94 | [−21.42, −18.71]; [−19.08, −13.54] |
| SPXW | pick 2022–24 | 109,721 | 662 / 683 | 41.3 | +83.1, +914.13 | −85.4, −810.56 | −46.6, −121.13 | **−15.83**, −98.21 | [−17.16, −14.68]; [−117.17, −79.16] |
| SPY | pick 2022–24 | 46,425 | 536 / 553 | 39.2 | +80.8, +88.58 | −84.0, −77.77 | −53.2, −16.04 | **−19.43**, −12.61 | [−20.88, −18.21]; [−14.81, −10.73] |
| all names | pick 2022–24 | 202,680 | 662 / 683 | 40.2 | +82.6, +548.24 | −85.0, −467.67 | −51.3, −31.04 | **−17.62**, −59.50 | [−18.93, −16.54]; [−72.29, −47.82] |
| IWM | check 2025–26 | 20,177 | 444 / 457 | 40.2 | +84.5, +62.36 | −85.8, −54.97 | −55.3, −12.04 | **−17.28**, −7.79 | [−19.60, −15.65]; [−9.42, −6.58] |
| QQQ | check 2025–26 | 48,342 | 444 / 457 | 39.3 | +82.8, +141.26 | −84.6, −124.45 | −56.0, −27.04 | **−18.87**, −20.11 | [−20.90, −17.12]; [−23.03, −17.99] |
| SPXW | check 2025–26 | 106,236 | 444 / 457 | 41.1 | +81.3, +1,167.90 | −84.3, −982.35 | −42.5, −106.13 | **−16.20**, −98.09 | [−18.05, −14.46]; [−123.60, −77.87] |
| SPY | check 2025–26 | 53,096 | 444 / 457 | 39.0 | +80.3, +121.01 | −83.2, −101.77 | −50.9, −17.04 | **−19.40**, −14.81 | [−21.33, −17.68]; [−17.73, −12.68] |
| all names | check 2025–26 | 227,851 | 444 / 457 | 40.2 | +81.7, +619.80 | −84.3, −506.49 | −48.3, −30.04 | **−17.61**, −54.14 | [−19.37, −16.02]; [−67.43, −43.81] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | pick 2022–24 | +376.89, +100.0%, 2024-08-05, IWM 197.0C m1 | −336.04, −100.0%, 2024-07-24, IWM 220.0C m30 | 0.68 | 68,223 | 180 | total ≤ 0 (best 5 days +2,838; without them −70,686) |
| QQQ | pick 2022–24 | +761.87, +100.0%, 2024-08-05, QQQ 423.0C m1 | −700.04, −100.0%, 2024-08-05, QQQ 426.0P m1 | 0.70 | 631,261 | 551 | total ≤ 0 (best 5 days +21,148; without them −651,979) |
| SPXW | pick 2022–24 | +7,667.74, +100.0%, 2024-08-05, SPXW 5095.0C m1 | −6,891.13, −100.0%, 2024-08-05, SPXW 5145.0P m1 | 0.79 | 10,776,052 | 683 | total ≤ 0 (best 5 days +720,720; without them −11,496,772) |
| SPY | pick 2022–24 | +709.88, +100.0%, 2024-08-05, SPY 509.0C m1 | −678.04, −100.0%, 2024-08-05, SPY 513.0P m1 | 0.73 | 585,645 | 553 | total ≤ 0 (best 5 days +27,423; without them −613,067) |
| all names | pick 2022–24 | +7,667.74, +100.0%, 2024-08-05, SPXW 5095.0C m1 | −6,891.13, −100.0%, 2024-08-05, SPXW 5145.0P m1 | 0.79 | 12,060,375 | 683 | total ≤ 0 (best 5 days +757,864; without them −12,818,240) |
| IWM | check 2025–26 | +344.89, +100.0%, 2025-04-07, IWM 173.0C m1 | −340.04, −100.0%, 2025-04-07, IWM 179.0P m60 | 0.76 | 157,234 | 457 | total ≤ 0 (best 5 days +6,839; without them −163,930) |
| QQQ | check 2025–26 | +787.87, +100.0%, 2025-04-09, QQQ 415.0C m1 | −792.04, −100.0%, 2025-04-09, QQQ 418.0P m1 | 0.73 | 972,278 | 457 | total ≤ 0 (best 5 days +53,908; without them −1,026,186) |
| SPXW | check 2025–26 | +9,037.74, +100.0%, 2025-04-09, SPXW 4940.0C m1 | −18,091.13, −100.0%, 2025-11-28, SPXW 6845.0P m1 | 0.83 | 10,437,628 | 457 | total ≤ 0 (best 5 days +910,540; without them −11,331,229) |
| SPY | check 2025–26 | +931.87, +100.0%, 2025-04-09, SPY 492.0C m1 | −880.04, −100.0%, 2025-04-09, SPY 496.0P m1 | 0.76 | 786,680 | 457 | total ≤ 0 (best 5 days +46,040; without them −832,367) |
| all names | check 2025–26 | +9,037.74, +100.0%, 2025-04-09, SPXW 4940.0C m1 | −18,091.13, −100.0%, 2025-11-28, SPXW 6845.0P m1 | 0.82 | 12,352,616 | 457 | total ≤ 0 (best 5 days +1,010,478; without them −13,346,862) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.02 a trade) and Robinhood's charged instead (mean $0.76). The study's fees are given beside them below. Re-pricing: exact (430,531 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | pick 2022–24 | 6,960 | **−20.47**, −9.75 | −24.05, −10.71 | 38.0 / 37.5 | [−24.27, −17.67] / [−28.15, −21.15] |
| QQQ | pick 2022–24 | 39,574 | **−19.94**, −15.94 | −21.90, −16.90 | 38.6 / 38.5 | [−21.42, −18.71] / [−23.39, −20.69] |
| SPXW | pick 2022–24 | 109,721 | **−15.83**, −98.21 | −15.61, −97.77 | 41.3 / 41.3 | [−17.16, −14.68] / [−16.94, −14.47] |
| SPY | pick 2022–24 | 46,425 | **−19.43**, −12.61 | −21.94, −13.58 | 39.2 / 39.0 | [−20.88, −18.21] / [−23.48, −20.59] |
| all names | pick 2022–24 | 202,680 | **−17.62**, −59.50 | −18.58, −59.71 | 40.2 / 40.1 | [−18.93, −16.54] / [−19.90, −17.44] |
| IWM | check 2025–26 | 20,177 | **−17.28**, −7.79 | −20.51, −8.74 | 40.2 / 40.0 | [−19.60, −15.65] / [−22.95, −18.65] |
| QQQ | check 2025–26 | 48,342 | **−18.87**, −20.11 | −20.52, −21.07 | 39.3 / 39.2 | [−20.90, −17.12] / [−22.70, −18.63] |
| SPXW | check 2025–26 | 106,236 | **−16.20**, −98.09 | −15.96, −97.67 | 41.1 / 41.1 | [−18.05, −14.46] / [−17.79, −14.25] |
| SPY | check 2025–26 | 53,096 | **−19.40**, −14.81 | −21.68, −15.78 | 39.0 / 38.9 | [−21.33, −17.68] / [−23.83, −19.76] |
| all names | check 2025–26 | 227,851 | **−17.61**, −54.14 | −18.66, −54.46 | 40.2 / 40.1 | [−19.37, −16.02] / [−20.55, −16.99] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- pick 2022–24: held to the close 70.8%; +100% target 29.2%
- check 2025–26: held to the close 71.1%; +100% target 28.9%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 6,960 | 38.0 | −20.47 | −9.75 | −67,848 |
| 2025 | IWM | 10,251 | 40.2 | −17.59 | −7.93 | −81,303 |
| 2026 | IWM | 9,926 | 40.2 | −16.95 | −7.64 | −75,789 |
| 2022 | QQQ | 1,720 | 36.8 | −21.99 | −18.60 | −31,989 |
| 2023 | QQQ | 15,750 | 39.3 | −19.06 | −13.07 | −205,813 |
| 2024 | QQQ | 22,104 | 38.3 | −20.41 | −17.78 | −393,029 |
| 2025 | QQQ | 24,779 | 38.4 | −20.50 | −20.25 | −501,665 |
| 2026 | QQQ | 23,563 | 40.2 | −17.15 | −19.97 | −470,613 |
| 2022 | SPXW | 22,444 | 40.9 | −15.65 | −153.67 | −3,448,980 |
| 2023 | SPXW | 38,347 | 41.6 | −15.60 | −77.07 | −2,955,493 |
| 2024 | SPXW | 48,930 | 41.2 | −16.10 | −89.34 | −4,371,579 |
| 2025 | SPXW | 55,548 | 41.2 | −16.17 | −102.24 | −5,679,112 |
| 2026 | SPXW | 50,688 | 41.1 | −16.23 | −93.54 | −4,741,576 |
| 2022 | SPY | 2,386 | 38.0 | −20.32 | −17.85 | −42,597 |
| 2023 | SPY | 19,406 | 39.7 | −18.76 | −10.60 | −205,722 |
| 2024 | SPY | 24,633 | 38.8 | −19.87 | −13.69 | −337,326 |
| 2025 | SPY | 27,804 | 39.1 | −19.49 | −15.35 | −426,889 |
| 2026 | SPY | 25,292 | 39.0 | −19.30 | −14.21 | −359,438 |
| 2022 | all names | 26,550 | 40.4 | −16.48 | −132.71 | −3,523,566 |
| 2023 | all names | 73,503 | 40.6 | −17.18 | −45.81 | −3,367,027 |
| 2024 | all names | 102,627 | 39.8 | −18.23 | −50.37 | −5,169,782 |
| 2025 | all names | 118,382 | 40.0 | −17.98 | −56.50 | −6,688,968 |
| 2026 | all names | 109,469 | 40.3 | −17.20 | −51.59 | −5,647,417 |

![](charts/s13.png)

**Amendments, deviations and integrity checks.** Formulas: step2/summarize.py (tp100, fees), the committed loader step2.double.load.

**What it showed.** Near-the-money 0DTE buys lose 16–22% of premium a trade.

## #14 Step 3: 108 exits × 9 conditions

**Folder:** `step3/`. **Commits:** — / — / 09885b6. **Dates:** 2026-10-16.

**Hypothesis.** A target, stop or time exit, or a condition known at the buy, makes step 2's trades pay.

**Rule.** 108 exits × 9 entry conditions on step 2's trades.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract each way.

**Data.** As step 2.

**Periods and holdouts.** discovery 2022–24 / check 2025–26.

**Pass rule (as pre-registered).** None pre-registered.

**Verdict.** Nothing made money in a way that held up; a −50% stop shrank losses; targets raised the win rate and lowered the average.

**Metrics.** not available — committed as per-rule summaries (exits.csv, exits_best.csv); the per-trade paths are committed but the exit grid was not re-run here.

**Amendments, deviations and integrity checks.** —

**What it showed.** No exit rule rescues the buys.

## #15 Step 4: turn-up buy (1.5× the low) + 20% trailing stop, near the money

**Folder:** `step4/`. **Commits:** — / — / 6c0e60b. **Dates:** 2026-10-16.

**Hypothesis.** Buying the turn up off the low and selling near the high with a trailing stop finds an edge.

**Rule.** The first minute (9:36 → 15 minutes before the close) a contract's ask reaches 1.5× its low so far → buy at the ask; sell at the bid once it falls 20% from the highest bid since buying, else hold to the close. Strikes within 0.5% of the price.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract each way (none when worthless).

**Data.** SPY, QQQ, IWM, SPX 0DTE 2022–2026 (this slice of 12,149,834 trades).

**Periods and holdouts.** pick 2022–24 / check 2025–26.

**Pass rule (as pre-registered).** None pre-registered; 126 rules positive in both periods, the 11 biggest failed the stress test.

**Verdict.** A trailing stop beats holding but still loses.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | pick 2022–24 | 807 | 177 / 182 | 24.5 | +37.0, +28.50 | −20.4, −17.31 | −18.0, −10.10 | **−6.33**, −6.07 | [−9.52, −3.39]; [−9.07, −3.39] |
| QQQ | pick 2022–24 | 4,603 | 536 / 553 | 28.1 | +39.6, +52.59 | −18.8, −25.65 | −15.3, −14.10 | **−2.39**, −3.69 | [−3.63, −0.43]; [−5.49, −0.73] |
| SPXW | pick 2022–24 | 12,787 | 662 / 683 | 26.8 | +36.7, +472.57 | −19.5, −244.41 | −16.7, −117.26 | **−4.44**, −52.48 | [−5.58, −3.06]; [−69.56, −31.31] |
| SPY | pick 2022–24 | 5,388 | 536 / 553 | 27.5 | +36.6, +46.54 | −18.8, −22.43 | −15.7, −10.10 | **−3.58**, −3.46 | [−4.81, −1.85]; [−5.05, −0.84] |
| all names | pick 2022–24 | 23,585 | 662 / 683 | 27.1 | +37.2, +275.24 | −19.2, −143.79 | −16.3, −25.10 | **−3.91**, −30.17 | [−4.90, −2.70]; [−41.22, −17.54] |
| IWM | check 2025–26 | 2,347 | 444 / 457 | 26.0 | +41.0, +37.89 | −19.9, −18.58 | −16.8, −10.10 | **−4.05**, −3.88 | [−6.62, −0.91]; [−6.61, −0.87] |
| QQQ | check 2025–26 | 5,595 | 444 / 457 | 28.9 | +41.4, +86.76 | −18.9, −38.41 | −14.9, −20.10 | **−1.42**, −2.21 | [−3.82, +0.97]; [−6.43, +2.76] |
| SPXW | check 2025–26 | 12,238 | 444 / 457 | 30.0 | +40.9, +721.76 | −19.0, −312.11 | −14.7, −122.26 | **−1.07**, −2.40 | [−2.69, +1.07]; [−43.29, +51.45] |
| SPY | check 2025–26 | 6,078 | 444 / 457 | 30.4 | +39.4, +70.71 | −18.5, −31.69 | −14.0, −11.10 | **−0.87**, −0.52 | [−2.54, +1.14]; [−4.16, +3.71] |
| all names | check 2025–26 | 26,258 | 444 / 457 | 29.5 | +40.7, +379.64 | −18.9, −161.74 | −14.8, −23.10 | **−1.37**, −2.06 | [−2.96, +0.56]; [−22.49, +24.58] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | pick 2022–24 | +196.90, +161.4%, 2024-07-11, IWM 207.0C m14 | −240.10, −73.9%, 2024-09-03, IWM 217.0C m30 | 0.54 | 5,042 | 179 | total ≤ 0 (best 5 days +1,063; without them −5,960) |
| QQQ | pick 2022–24 | +604.96, +360.1%, 2023-08-29, QQQ 367.0C m13 | −270.10, −52.5%, 2023-03-22, QQQ 313.0P m270 | 0.80 | 16,971 | 553 | total ≤ 0 (best 5 days +7,189; without them −24,160) |
| SPXW | pick 2022–24 | +7,302.87, +268.5%, 2024-05-31, SPXW 5180.0C m211 | −4,492.26, −81.8%, 2023-09-21, SPXW 4350.0C m6 | 0.71 | 673,616 | 673 | total ≤ 0 (best 5 days +145,866; without them −816,949) |
| SPY | pick 2022–24 | +796.88, +249.0%, 2024-08-01, SPY 555.0P m36 | −330.10, −68.1%, 2024-09-18, SPY 565.0P m270 | 0.79 | 18,648 | 553 | total ≤ 0 (best 5 days +6,787; without them −25,435) |
| all names | pick 2022–24 | +7,302.87, +268.5%, 2024-05-31, SPXW 5180.0C m211 | −4,492.26, −81.8%, 2023-09-21, SPXW 4350.0C m6 | 0.71 | 714,131 | 673 | total ≤ 0 (best 5 days +154,196; without them −865,795) |
| IWM | check 2025–26 | +640.96, +754.1%, 2025-02-21, IWM 225.0P m6 | −245.10, −66.1%, 2025-08-01, IWM 212.5C m30 | 0.72 | 10,434 | 418 | total ≤ 0 (best 5 days +3,653; without them −12,759) |
| QQQ | check 2025–26 | +1,033.96, +984.7%, 2026-09-21, QQQ 730.0C m8 | −274.09, −100.0%, 2025-07-30, QQQ 570.0P m104 | 0.92 | 26,331 | 323 | total ≤ 0 (best 5 days +21,516; without them −33,895) |
| SPXW | check 2025–26 | +21,607.74, +266.1%, 2025-04-07, SPXW 4875.0C m19 | −39,942.26, −80.0%, 2025-04-09, SPXW 5340.0P m238 | 0.99 | 466,377 | 390 | total ≤ 0 (best 5 days +421,711; without them −451,093) |
| SPY | check 2025–26 | +1,876.85, +247.0%, 2025-04-07, SPY 490.0C m23 | −2,362.10, −85.9%, 2025-04-09, SPY 521.0P m231 | 0.98 | 25,145 | 390 | total ≤ 0 (best 5 days +20,869; without them −24,052) |
| all names | check 2025–26 | +21,607.74, +266.1%, 2025-04-07, SPXW 4875.0C m19 | −39,942.26, −80.0%, 2025-04-09, SPXW 5340.0P m238 | 0.98 | 521,558 | 390 | total ≤ 0 (best 5 days +459,576; without them −513,627) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.30 a trade) and Robinhood's charged instead (mean $1.18). The study's fees are given beside them below. Re-pricing: exact (49,843 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | pick 2022–24 | 807 | **−6.33**, −6.07 | −8.30, −7.27 | 24.5 / 23.3 | [−9.52, −3.39] / [−11.58, −5.37] |
| QQQ | pick 2022–24 | 4,603 | **−2.39**, −3.69 | −3.66, −4.89 | 28.1 / 27.4 | [−3.63, −0.43] / [−4.88, −1.77] |
| SPXW | pick 2022–24 | 12,787 | **−4.44**, −52.48 | −4.29, −51.53 | 26.8 / 26.8 | [−5.58, −3.06] / [−5.43, −2.91] |
| SPY | pick 2022–24 | 5,388 | **−3.58**, −3.46 | −5.57, −4.66 | 27.5 / 26.2 | [−4.81, −1.85] / [−6.91, −3.68] |
| all names | pick 2022–24 | 23,585 | **−3.91**, −30.17 | −4.59, −30.20 | 27.1 / 26.6 | [−4.90, −2.70] / [−5.59, −3.37] |
| IWM | check 2025–26 | 2,347 | **−4.05**, −3.88 | −5.82, −5.08 | 26.0 / 24.8 | [−6.62, −0.91] / [−8.42, −2.59] |
| QQQ | check 2025–26 | 5,595 | **−1.42**, −2.21 | −2.38, −3.41 | 28.9 / 28.3 | [−3.82, +0.97] / [−4.82, +0.08] |
| SPXW | check 2025–26 | 12,238 | **−1.07**, −2.40 | −0.94, −1.45 | 30.0 / 30.0 | [−2.69, +1.07] / [−2.55, +1.19] |
| SPY | check 2025–26 | 6,078 | **−0.87**, −0.52 | −2.41, −1.72 | 30.4 / 29.3 | [−2.54, +1.14] / [−4.16, −0.30] |
| all names | check 2025–26 | 26,258 | **−1.37**, −2.06 | −2.02, −2.26 | 29.5 / 29.0 | [−2.96, +0.56] / [−3.63, −0.05] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- pick 2022–24: 20% trailing stop 99.5%; held to the close 0.5%
- check 2025–26: 20% trailing stop 99.4%; held to the close 0.6%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 807 | 24.5 | −6.33 | −6.07 | −4,897 |
| 2025 | IWM | 1,182 | 24.5 | −6.01 | −6.99 | −8,258 |
| 2026 | IWM | 1,165 | 27.6 | −2.07 | −0.73 | −848 |
| 2022 | QQQ | 202 | 19.8 | −6.67 | −10.70 | −2,162 |
| 2023 | QQQ | 1,842 | 28.5 | −2.28 | −3.25 | −5,993 |
| 2024 | QQQ | 2,559 | 28.4 | −2.14 | −3.45 | −8,816 |
| 2025 | QQQ | 2,874 | 27.7 | −2.52 | −3.10 | −8,896 |
| 2026 | QQQ | 2,721 | 30.2 | −0.27 | −1.28 | −3,483 |
| 2022 | SPXW | 2,622 | 25.2 | −5.38 | −91.83 | −240,767 |
| 2023 | SPXW | 4,479 | 25.9 | −5.14 | −52.32 | −234,351 |
| 2024 | SPXW | 5,686 | 28.2 | −3.45 | −34.46 | −195,964 |
| 2025 | SPXW | 6,428 | 29.9 | −1.07 | +3.97 | +25,507 |
| 2026 | SPXW | 5,810 | 30.0 | −1.07 | −9.45 | −54,889 |
| 2022 | SPY | 300 | 22.7 | −5.94 | −9.47 | −2,840 |
| 2023 | SPY | 2,240 | 26.7 | −4.57 | −4.19 | −9,376 |
| 2024 | SPY | 2,848 | 28.6 | −2.56 | −2.26 | −6,432 |
| 2025 | SPY | 3,194 | 30.4 | −1.10 | −0.51 | −1,626 |
| 2026 | SPY | 2,884 | 30.5 | −0.61 | −0.54 | −1,556 |
| 2022 | all names | 3,124 | 24.6 | −5.52 | −78.67 | −245,770 |
| 2023 | all names | 8,561 | 26.7 | −4.38 | −29.17 | −249,720 |
| 2024 | all names | 11,900 | 28.1 | −3.15 | −18.16 | −216,109 |
| 2025 | all names | 13,678 | 29.1 | −1.81 | +0.49 | +6,727 |
| 2026 | all names | 12,580 | 29.9 | −0.88 | −4.83 | −60,777 |

![](charts/s15.png)

**Amendments, deviations and integrity checks.** Formulas copied from step4/summarize.py prep().

**What it showed.** The near-the-money turn-up buy with a 20% trail loses 1–8% of premium a trade.

## #16 Step 5: the runner model (model A/B) and its top 1% picks

**Folder:** `step5/`. **Commits:** — / — / ae3c63d, 1227394, f9f2746, 491a0c7. **Dates:** 2026-10-16 → 17.

**Hypothesis.** What was visible at the turn tells runners from duds well enough to trade.

**Rule.** Gradient-boosted model A (P(bid ≥ 3× paid)) and B; trade the top 1% / 0.5% / 0.1%, three exits.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract each way.

**Data.** 1,602,401 turn-up and range-break buys; trained 2022–24, scored once on 2025–26.

**Periods and holdouts.** train 2022–24 / scored 2025–26.

**Pass rule (as pre-registered).** None pre-registered.

**Verdict.** Runners partly separable (top 1% reach 3× 26% vs 6%) but do not pay; every pick total made money almost all on 2025-11-20, and without its best 5 days it lost $620,114.

**Metrics.** not available — the picks are committed as daily sums (top1_daily.csv), not trades.

**Amendments, deviations and integrity checks.** Scored once.

**What it showed.** The model ranks runners but its picks do not pay without a handful of days.

## #17 Step 6: the six pre-registered runner rules × three exits

**Folder:** `step6/`. **Commits:** 30babaa / — / 44b5547. **Dates:** 2026-10-23.

**Hypothesis.** A condition visible at the buy raises the odds of a +40% (family A) or +500% (family B) run enough to trade.

**Rule.** The top 3 rules of each family by Pick lift (one or two Part 2 buckets, ≥ 300 Pick trades on ≥ 60 dates), each buying every near-the-money population trade that meets it; exits (a) +40% / −30% / 60 minutes or 3:30, (b) 50% trail armed at +40%, out 3:30, (c) half at +40%, trail the rest 50%, out 3:30.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract each way (SPY/QQQ/IWM), SPXW per schedule; no sale fee at a $0 bid.

**Data.** 240,493 near-the-money 0DTE buys 2022-05 → 2026-10-09 (the 28 held-out months never read).

**Periods and holdouts.** pick 2022-05→2024 / check 2025→2026-10-09; the 28 holdout-B months UNOPENED.

**Pass rule (as pre-registered).** Check: average r > 0, its 20-session block lower end > 0, and above the 97.5th percentile of 500 cell-matched random draws.

**Verdict.** FAIL: 0 of 18 pass; all lose on Check (−3.3% to −21.9% a trade); 14 of 18 below the 20th random percentile.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| A1a | pick 2022-05→2024 | 665 | 80 / 681 | 49.9 | +36.4, +235.02 | −32.7, −297.48 | −0.0, −0.10 | **+1.78**, −31.63 | [−5.55, +10.85]; [−84.59, +65.12] |
| A1b | pick 2022-05→2024 | 665 | 80 / 681 | 32.0 | +79.9, +608.96 | −49.9, −418.89 | −22.6, −40.10 | **−8.32**, −89.67 | [−24.75, +16.03]; [−197.94, +180.18] |
| A1c | pick 2022-05→2024 | 665 | 80 / 681 | 66.9 | +66.1, +503.74 | −156.0, −1,350.48 | +15.3, +35.48 | **−7.38**, −109.68 | [−33.39, +30.57]; [−282.38, +320.89] |
| A2a | pick 2022-05→2024 | 1,081 | 186 / 678 | 43.1 | +38.4, +324.15 | −33.7, −270.27 | −30.6, −19.10 | **−2.60**, −14.02 | [−10.00, +1.96]; [−93.03, +32.48] |
| A2b | pick 2022-05→2024 | 1,081 | 186 / 678 | 33.3 | +139.4, +938.60 | −50.2, −420.27 | −21.8, −45.10 | **+12.97**, +32.27 | [−7.98, +40.79]; [−123.81, +239.18] |
| A2c | pick 2022-05→2024 | 1,081 | 186 / 678 | 64.8 | +100.1, +706.13 | −148.1, −1,215.00 | +14.4, +40.00 | **+12.62**, +29.03 | [−13.99, +44.01]; [−186.99, +294.84] |
| A3a | pick 2022-05→2024 | 1,239 | 127 / 683 | 47.4 | +38.3, +323.94 | −33.1, −287.55 | −14.7, −14.10 | **+0.74**, +2.16 | [−6.33, +7.31]; [−80.72, +74.27] |
| A3b | pick 2022-05→2024 | 1,239 | 127 / 683 | 29.1 | +95.0, +884.01 | −45.2, −357.95 | −20.4, −50.10 | **−4.46**, +2.91 | [−26.01, +2.77]; [−269.93, +76.52] |
| A3c | pick 2022-05→2024 | 1,239 | 127 / 683 | 66.3 | +69.8, +650.54 | −145.1, −1,132.38 | +16.4, +38.40 | **−2.68**, +49.04 | [−35.01, +13.09]; [−383.88, +201.66] |
| B1a | pick 2022-05→2024 | 2,426 | 121 / 443 | 42.3 | +31.5, +631.01 | −29.8, −598.26 | −18.6, −382.26 | **−3.87**, −77.87 | [−5.30, −2.88]; [−104.62, −55.49] |
| B1b | pick 2022-05→2024 | 2,426 | 121 / 443 | 34.5 | +106.5, +2,149.80 | −52.9, −1,062.29 | −21.6, −412.26 | **+2.03**, +44.59 | [−10.50, +14.05]; [−210.37, +298.18] |
| B1c | pick 2022-05→2024 | 2,426 | 121 / 443 | 58.4 | +93.3, +1,886.36 | −142.2, −2,855.75 | +13.8, +253.48 | **−4.66**, −85.93 | [−16.86, +8.36]; [−327.73, +192.82] |
| B2a | pick 2022-05→2024 | 2,483 | 137 / 621 | 38.6 | +30.0, +579.64 | −27.6, −533.57 | −15.5, −312.26 | **−5.33**, −103.62 | [−6.43, −4.58]; [−126.68, −88.57] |
| B2b | pick 2022-05→2024 | 2,483 | 137 / 621 | 34.8 | +95.3, +1,817.59 | −55.5, −1,073.71 | −23.8, −432.26 | **−2.97**, −66.47 | [−11.43, +6.46]; [−246.90, +130.43] |
| B2c | pick 2022-05→2024 | 2,483 | 137 / 621 | 55.8 | +90.1, +1,733.67 | −142.5, −2,744.13 | +10.8, +207.48 | **−12.65**, −244.64 | [−21.37, −3.57]; [−429.23, −53.76] |
| B3a | pick 2022-05→2024 | 752 | 60 / 85 | 43.9 | +36.3, +320.14 | −32.3, −203.18 | −30.3, −22.10 | **−2.20**, +26.47 | [−10.14, −1.77]; [−74.91, +34.62] |
| B3b | pick 2022-05→2024 | 752 | 60 / 85 | 32.6 | +104.2, +928.10 | −50.3, −338.87 | −21.9, −48.60 | **+0.06**, +73.91 | [−27.16, +6.00]; [−229.79, +153.45] |
| B3c | pick 2022-05→2024 | 752 | 60 / 85 | 56.0 | +91.8, +801.36 | −133.0, −858.15 | +12.9, +26.50 | **−7.11**, +70.91 | [−47.60, −0.43]; [−400.77, +171.45] |
| A1a | check 2025→2026-10-09 | 1,035 | 101 / 451 | 36.6 | +38.1, +430.92 | −32.6, −286.49 | −30.9, −32.10 | **−6.72**, −23.79 | [−14.64, +0.78]; [−158.27, +105.75] |
| A1b | check 2025→2026-10-09 | 1,035 | 101 / 451 | 27.4 | +83.5, +329.73 | −60.2, −662.52 | −29.4, −72.10 | **−20.74**, −390.25 | [−41.61, +1.31]; [−621.10, −124.77] |
| A1c | check 2025→2026-10-09 | 1,035 | 101 / 451 | 54.0 | +71.1, +416.03 | −163.2, −1,635.74 | +8.7, +8.80 | **−36.67**, −527.59 | [−78.56, +0.61]; [−822.26, −207.25] |
| A2a | check 2025→2026-10-09 | 1,502 | 155 / 456 | 32.4 | +36.8, +377.42 | −33.0, −318.01 | −31.1, −39.60 | **−10.43**, −92.99 | [−14.25, −6.42]; [−187.40, +2.57] |
| A2b | check 2025→2026-10-09 | 1,502 | 155 / 456 | 36.0 | +81.5, +878.55 | −63.4, −597.62 | −23.9, −45.10 | **−11.19**, −65.92 | [−29.74, +11.07]; [−317.65, +162.85] |
| A2c | check 2025→2026-10-09 | 1,502 | 155 / 456 | 55.9 | +84.3, +927.09 | −165.7, −1,585.56 | +12.5, +21.70 | **−25.90**, −180.35 | [−58.12, +11.34]; [−619.37, +241.04] |
| A3a | check 2025→2026-10-09 | 2,435 | 146 / 451 | 37.1 | +37.8, +365.85 | −33.3, −304.89 | −30.9, −34.10 | **−6.90**, −56.15 | [−11.17, −2.58]; [−116.06, +1.64] |
| A3b | check 2025→2026-10-09 | 2,435 | 146 / 451 | 29.0 | +75.2, +511.39 | −60.5, −623.93 | −27.5, −59.10 | **−21.21**, −295.22 | [−31.60, −6.77]; [−507.83, −4.66] |
| A3c | check 2025→2026-10-09 | 2,435 | 146 / 451 | 54.5 | +70.4, +543.60 | −166.6, −1,690.55 | +10.1, +13.40 | **−37.46**, −473.01 | [−55.26, −14.39]; [−823.39, −4.40] |
| B1a | check 2025→2026-10-09 | 6,350 | 197 / 457 | 41.6 | +31.8, +686.04 | −29.5, −642.27 | −17.7, −432.26 | **−3.96**, −89.19 | [−4.78, −3.40]; [−107.28, −75.90] |
| B1b | check 2025→2026-10-09 | 6,350 | 197 / 457 | 35.0 | +93.5, +2,028.67 | −55.6, −1,238.59 | −22.1, −442.26 | **−3.33**, −93.77 | [−8.44, +2.82]; [−197.96, +34.83] |
| B1c | check 2025→2026-10-09 | 6,350 | 197 / 457 | 59.0 | +85.8, +1,874.77 | −150.5, −3,356.40 | +14.0, +293.48 | **−11.00**, −268.77 | [−16.67, −5.04]; [−397.73, −126.84] |
| B2a | check 2025→2026-10-09 | 5,406 | 136 / 446 | 39.7 | +31.7, +703.98 | −29.2, −655.49 | −19.9, −452.26 | **−5.05**, −116.08 | [−6.43, −4.01]; [−152.33, −88.09] |
| B2b | check 2025→2026-10-09 | 5,406 | 136 / 446 | 35.4 | +93.0, +2,087.91 | −57.7, −1,324.10 | −22.0, −462.26 | **−4.28**, −114.81 | [−9.47, +3.42]; [−237.38, +59.95] |
| B2c | check 2025→2026-10-09 | 5,406 | 136 / 446 | 57.3 | +88.7, +2,007.76 | −152.2, −3,497.85 | +13.2, +277.48 | **−14.04**, −340.73 | [−21.01, −5.68]; [−527.97, −136.71] |
| B3a | check 2025→2026-10-09 | 5,454 | 321 / 457 | 37.5 | +36.7, +376.44 | −31.4, −325.41 | −30.5, −40.10 | **−5.86**, −62.38 | [−7.25, −4.50]; [−119.96, −21.06] |
| B3b | check 2025→2026-10-09 | 5,454 | 321 / 457 | 31.6 | +95.2, +1,028.90 | −54.5, −557.24 | −25.1, −64.10 | **−7.17**, −55.57 | [−11.78, −2.80]; [−130.11, +14.09] |
| B3c | check 2025→2026-10-09 | 5,454 | 321 / 457 | 53.7 | +87.1, +955.61 | −141.7, −1,427.58 | +9.7, +19.50 | **−18.89**, −148.59 | [−26.18, −12.17]; [−285.84, −41.36] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| A1a | pick 2022-05→2024 | +1,237.74, +39.9%, 2022-09-01, SPX 3955.0P m60 | −1,412.26, −31.6%, 2022-05-19, SPX 3935.0P m90 | 0.79 | 36,376 | 681 | total ≤ 0 (best 5 days +31,082; without them −52,115) |
| A1b | pick 2022-05→2024 | +6,137.74, +204.6%, 2022-10-20, SPX 3755.0P m90 | −3,402.26, −94.2%, 2022-05-17, SPX 4075.0P m90 | 0.69 | 82,581 | 681 | total ≤ 0 (best 5 days +92,021; without them −151,650) |
| A1c | pick 2022-05→2024 | +7,519.48, +200.0%, 2022-07-05, SPX 3725.0C m60 | −6,804.52, −188.5%, 2022-05-17, SPX 4075.0P m90 | 0.75 | 115,672 | 681 | total ≤ 0 (best 5 days +125,595; without them −198,535) |
| A2a | pick 2022-05→2024 | +1,689.74, +39.9%, 2022-06-13, SPX 3750.0C m150 | −1,322.26, −36.8%, 2022-05-19, SPX 3935.0P m210 | 0.91 | 65,254 | 660 | total ≤ 0 (best 5 days +53,888; without them −69,049) |
| A2b | pick 2022-05→2024 | +7,777.74, +437.0%, 2024-09-11, SPX 5445.0C m150 | −3,622.26, −86.0%, 2022-05-24, SPX 3930.0P m60 | 1.12 | 86,433 | 596 | 468% |
| A2c | pick 2022-05→2024 | +8,487.48, +476.8%, 2024-09-11, SPX 5445.0C m150 | −7,244.52, −172.1%, 2022-05-24, SPX 3930.0P m60 | 1.07 | 112,670 | 543 | 621% |
| A3a | pick 2022-05→2024 | +1,813.74, +40.0%, 2022-05-18, SPX 4050.0P m60 | −1,562.26, −40.7%, 2022-10-21, SPX 3710.0P m90 | 1.01 | 59,262 | 587 | 1962% |
| A3b | pick 2022-05→2024 | +8,687.74, +191.4%, 2022-05-18, SPX 4050.0P m60 | −3,837.17, −99.9%, 2022-10-21, SPX 3710.0P m90 | 1.01 | 170,610 | 679 | 6266% |
| A3c | pick 2022-05→2024 | +10,501.48, +231.3%, 2022-05-18, SPX 4050.0P m60 | −7,674.34, −199.9%, 2022-10-21, SPX 3710.0P m90 | 1.13 | 187,074 | 633 | 482% |
| B1a | pick 2022-05→2024 | +1,625.74, +39.9%, 2024-12-31, SPX 5955.0P m60 | −2,557.17, −99.5%, 2023-09-21, SPX 4355.0C m1 | 0.77 | 189,080 | 442 | total ≤ 0 (best 5 days +11,243; without them −200,162) |
| B1b | pick 2022-05→2024 | +12,317.74, +443.1%, 2024-12-18, SPX 6090.0P m90 | −3,431.13, −100.0%, 2024-04-15, SPX 5135.0C m1 | 1.06 | 233,154 | 324 | 521% |
| B1c | pick 2022-05→2024 | +13,427.48, +483.0%, 2024-12-18, SPX 6090.0P m90 | −6,862.26, −200.1%, 2024-04-15, SPX 5135.0C m1 | 0.93 | 391,350 | 443 | total ≤ 0 (best 5 days +559,855; without them −768,330) |
| B2a | pick 2022-05→2024 | +1,533.74, +39.9%, 2024-10-04, SPX 5775.0P m1 | −1,382.26, −37.8%, 2022-08-10, SPX 4165.0C m1 | 0.68 | 259,220 | 618 | total ≤ 0 (best 5 days +9,032; without them −266,317) |
| B2b | pick 2022-05→2024 | +12,317.74, +443.1%, 2024-12-18, SPX 6090.0P m90 | −3,322.26, −94.1%, 2024-10-31, SPX 5740.0C m1 | 0.90 | 456,313 | 621 | total ≤ 0 (best 5 days +395,764; without them −560,812) |
| B2c | pick 2022-05→2024 | +13,427.48, +483.0%, 2024-12-18, SPX 6090.0P m90 | −6,644.52, −188.2%, 2024-10-31, SPX 5740.0C m1 | 0.80 | 889,284 | 621 | total ≤ 0 (best 5 days +390,675; without them −998,112) |
| B3a | pick 2022-05→2024 | +1,281.74, +39.9%, 2024-09-06, SPX 5410.0C m90 | −1,112.26, −35.2%, 2024-09-06, SPX 5435.0C m60 | 1.23 | 18,770 | 61 | 197% |
| B3b | pick 2022-05→2024 | +11,797.74, +655.4%, 2024-12-18, SPX 6075.0P m150 | −2,932.26, −92.8%, 2024-09-06, SPX 5435.0C m60 | 1.32 | 83,638 | 79 | 265% |
| B3c | pick 2022-05→2024 | +12,515.48, +695.3%, 2024-12-18, SPX 6075.0P m150 | −5,864.52, −185.6%, 2024-09-06, SPX 5435.0C m60 | 1.19 | 137,832 | 79 | 337% |
| A1a | check 2025→2026-10-09 | +4,161.74, +40.0%, 2025-04-09, SPX 5085.0P m60 | −3,532.26, −37.5%, 2025-04-04, SPX 5255.0P m90 | 0.87 | 74,759 | 368 | total ≤ 0 (best 5 days +140,582; without them −165,205) |
| A1b | check 2025→2026-10-09 | +3,477.74, +37.0%, 2025-04-04, SPX 5255.0P m90 | −13,347.17, −100.0%, 2025-04-09, SPX 5125.0P m60 | 0.19 | 404,331 | 446 | total ≤ 0 (best 5 days +40,801; without them −444,708) |
| A1c | check 2025→2026-10-09 | +7,239.48, +76.9%, 2025-04-04, SPX 5255.0P m90 | −26,694.34, −200.0%, 2025-04-09, SPX 5125.0P m60 | 0.30 | 590,220 | 384 | total ≤ 0 (best 5 days +136,512; without them −682,564) |
| A2a | check 2025→2026-10-09 | +2,647.74, +23.2%, 2025-04-11, SPX 5155.0C m90 | −4,132.26, −31.1%, 2025-04-07, SPX 4900.0C m150 | 0.57 | 155,224 | 408 | total ≤ 0 (best 5 days +96,325; without them −235,994) |
| A2b | check 2025→2026-10-09 | +9,607.74, +84.2%, 2025-04-11, SPX 5155.0C m90 | −6,502.26, −88.7%, 2025-04-08, SPX 5025.0C m270 | 0.83 | 388,282 | 409 | total ≤ 0 (best 5 days +308,386; without them −407,402) |
| A2c | check 2025→2026-10-09 | +14,169.48, +124.2%, 2025-04-11, SPX 5155.0C m90 | −13,004.52, −177.4%, 2025-04-08, SPX 5025.0C m270 | 0.74 | 695,495 | 408 | total ≤ 0 (best 5 days +431,141; without them −702,028) |
| A3a | check 2025→2026-10-09 | +4,161.74, +40.0%, 2025-04-09, SPX 5085.0P m60 | −3,532.26, −37.5%, 2025-04-04, SPX 5255.0P m90 | 0.71 | 217,405 | 383 | total ≤ 0 (best 5 days +177,528; without them −314,258) |
| A3b | check 2025→2026-10-09 | +5,297.74, +118.5%, 2025-10-10, SPX 6680.0P m150 | −13,347.17, −100.0%, 2025-04-09, SPX 5125.0P m60 | 0.33 | 754,262 | 451 | total ≤ 0 (best 5 days +152,747; without them −871,616) |
| A3c | check 2025→2026-10-09 | +7,239.48, +76.9%, 2025-04-04, SPX 5255.0P m90 | −26,694.34, −200.0%, 2025-04-09, SPX 5125.0P m60 | 0.39 | 1,198,123 | 451 | total ≤ 0 (best 5 days +252,347; without them −1,404,122) |
| B1a | check 2025→2026-10-09 | +1,957.74, +40.0%, 2026-06-17, SPX 7570.0P m60 | −2,891.13, −100.0%, 2025-07-30, SPX 6360.0C m60 | 0.76 | 569,189 | 449 | total ≤ 0 (best 5 days +22,718; without them −589,061) |
| B1b | check 2025→2026-10-09 | +16,707.74, +843.8%, 2025-10-10, SPX 6770.0P m30 | −5,517.26, −98.2%, 2026-09-16, SPX 7560.0C m1 | 0.88 | 697,999 | 401 | total ≤ 0 (best 5 days +624,115; without them −1,219,527) |
| B1c | check 2025→2026-10-09 | +17,497.48, +883.7%, 2025-10-10, SPX 6770.0P m30 | −11,034.52, −196.3%, 2026-09-16, SPX 7560.0C m1 | 0.80 | 1,789,686 | 434 | total ≤ 0 (best 5 days +576,212; without them −2,282,931) |
| B2a | check 2025→2026-10-09 | +2,301.74, +40.0%, 2026-02-20, SPX 6790.0C m1 | −2,891.13, −100.0%, 2025-07-30, SPX 6360.0C m60 | 0.71 | 627,925 | 446 | total ≤ 0 (best 5 days +22,686; without them −650,206) |
| B2b | check 2025→2026-10-09 | +16,707.74, +843.8%, 2025-10-10, SPX 6770.0P m30 | −5,762.26, −97.0%, 2026-02-20, SPX 6890.0P m1 | 0.87 | 915,097 | 251 | total ≤ 0 (best 5 days +550,915; without them −1,171,573) |
| B2c | check 2025→2026-10-09 | +17,497.48, +883.7%, 2025-10-10, SPX 6770.0P m30 | −11,524.52, −194.0%, 2026-02-20, SPX 6890.0P m1 | 0.77 | 1,932,579 | 251 | total ≤ 0 (best 5 days +521,569; without them −2,363,566) |
| B3a | check 2025→2026-10-09 | +2,985.74, +40.0%, 2025-04-07, SPX 4925.0C m210 | −4,022.26, −33.5%, 2025-04-07, SPX 4820.0C m1 | 0.69 | 343,898 | 456 | total ≤ 0 (best 5 days +72,225; without them −412,431) |
| B3b | check 2025→2026-10-09 | +23,857.74, +381.1%, 2025-04-08, SPX 5295.0P m60 | −7,837.17, −99.2%, 2025-04-04, SPX 5215.0C m1 | 0.85 | 482,980 | 390 | total ≤ 0 (best 5 days +678,847; without them −981,925) |
| B3c | check 2025→2026-10-09 | +26,359.48, +421.1%, 2025-04-08, SPX 5295.0P m60 | −15,674.34, −198.4%, 2025-04-04, SPX 5215.0C m1 | 0.78 | 969,168 | 412 | total ≤ 0 (best 5 days +852,845; without them −1,663,254) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.92 a trade) and Robinhood's charged instead (mean $2.22). The study's fees are given beside them below. Re-pricing: exact (92,484 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| A1a | pick 2022-05→2024 | 665 | **+1.78**, −31.63 | +1.07, −32.35 | 49.9 / 49.8 | [−5.55, +10.85] / [−6.21, +10.10] |
| A1b | pick 2022-05→2024 | 665 | **−8.32**, −89.67 | −9.02, −90.37 | 32.0 / 31.9 | [−24.75, +16.03] / [−25.54, +15.35] |
| A1c | pick 2022-05→2024 | 665 | **−7.38**, −109.68 | −8.77, −111.10 | 66.9 / 66.2 | [−33.39, +30.57] / [−34.77, +29.18] |
| A2a | pick 2022-05→2024 | 1,081 | **−2.60**, −14.02 | −3.29, −14.71 | 43.1 / 43.1 | [−10.00, +1.96] / [−10.74, +1.18] |
| A2b | pick 2022-05→2024 | 1,081 | **+12.97**, +32.27 | +12.30, +31.60 | 33.3 / 32.7 | [−7.98, +40.79] / [−8.79, +40.13] |
| A2c | pick 2022-05→2024 | 1,081 | **+12.62**, +29.03 | +11.28, +27.68 | 64.8 / 64.0 | [−13.99, +44.01] / [−15.39, +42.35] |
| A3a | pick 2022-05→2024 | 1,239 | **+0.74**, +2.16 | +0.07, +1.42 | 47.4 / 47.4 | [−6.33, +7.31] / [−7.06, +6.68] |
| A3b | pick 2022-05→2024 | 1,239 | **−4.46**, +2.91 | −5.11, +2.19 | 29.1 / 28.6 | [−26.01, +2.77] / [−26.65, +2.15] |
| A3c | pick 2022-05→2024 | 1,239 | **−2.68**, +49.04 | −3.97, +47.59 | 66.3 / 66.0 | [−35.01, +13.09] / [−36.20, +11.73] |
| B1a | pick 2022-05→2024 | 2,426 | **−3.87**, −77.87 | −3.88, −78.17 | 42.3 / 42.3 | [−5.30, −2.88] / [−5.32, −2.90] |
| B1b | pick 2022-05→2024 | 2,426 | **+2.03**, +44.59 | +2.01, +44.30 | 34.5 / 34.5 | [−10.50, +14.05] / [−10.52, +14.04] |
| B1c | pick 2022-05→2024 | 2,426 | **−4.66**, −85.93 | −4.69, −86.51 | 58.4 / 58.4 | [−16.86, +8.36] / [−16.90, +8.33] |
| B2a | pick 2022-05→2024 | 2,483 | **−5.33**, −103.62 | −5.35, −103.91 | 38.6 / 38.6 | [−6.43, −4.58] / [−6.45, −4.60] |
| B2b | pick 2022-05→2024 | 2,483 | **−2.97**, −66.47 | −2.99, −66.76 | 34.8 / 34.8 | [−11.43, +6.46] / [−11.44, +6.44] |
| B2c | pick 2022-05→2024 | 2,483 | **−12.65**, −244.64 | −12.68, −245.22 | 55.8 / 55.8 | [−21.37, −3.57] / [−21.40, −3.60] |
| B3a | pick 2022-05→2024 | 752 | **−2.20**, +26.47 | −2.80, +25.68 | 43.9 / 43.8 | [−10.14, −1.77] / [−10.87, −2.38] |
| B3b | pick 2022-05→2024 | 752 | **+0.06**, +73.91 | −0.53, +73.13 | 32.6 / 32.3 | [−27.16, +6.00] / [−27.90, +5.39] |
| B3c | pick 2022-05→2024 | 752 | **−7.11**, +70.91 | −8.30, +69.36 | 56.0 / 55.9 | [−47.60, −0.43] / [−49.01, −1.58] |
| A1a | check 2025→2026-10-09 | 1,035 | **−6.72**, −23.79 | −7.54, −24.69 | 36.6 / 36.6 | [−14.64, +0.78] / [−15.50, −0.10] |
| A1b | check 2025→2026-10-09 | 1,035 | **−20.74**, −390.25 | −21.53, −391.13 | 27.4 / 27.1 | [−41.61, +1.31] / [−42.34, +0.40] |
| A1c | check 2025→2026-10-09 | 1,035 | **−36.67**, −527.59 | −38.24, −529.36 | 54.0 / 53.4 | [−78.56, +0.61] / [−80.04, −0.96] |
| A2a | check 2025→2026-10-09 | 1,502 | **−10.43**, −92.99 | −11.17, −93.85 | 32.4 / 32.2 | [−14.25, −6.42] / [−15.01, −7.26] |
| A2b | check 2025→2026-10-09 | 1,502 | **−11.19**, −65.92 | −11.89, −66.75 | 36.0 / 35.8 | [−29.74, +11.07] / [−30.37, +10.29] |
| A2c | check 2025→2026-10-09 | 1,502 | **−25.90**, −180.35 | −27.31, −182.01 | 55.9 / 55.3 | [−58.12, +11.34] / [−59.32, +9.59] |
| A3a | check 2025→2026-10-09 | 2,435 | **−6.90**, −56.15 | −7.62, −57.06 | 37.1 / 37.1 | [−11.17, −2.58] / [−11.88, −3.35] |
| A3b | check 2025→2026-10-09 | 2,435 | **−21.21**, −295.22 | −21.90, −296.11 | 29.0 / 28.7 | [−31.60, −6.77] / [−32.27, −7.52] |
| A3c | check 2025→2026-10-09 | 2,435 | **−37.46**, −473.01 | −38.83, −474.77 | 54.5 / 54.0 | [−55.26, −14.39] / [−56.61, −15.99] |
| B1a | check 2025→2026-10-09 | 6,350 | **−3.96**, −89.19 | −3.97, −89.48 | 41.6 / 41.6 | [−4.78, −3.40] / [−4.79, −3.41] |
| B1b | check 2025→2026-10-09 | 6,350 | **−3.33**, −93.77 | −3.34, −94.06 | 35.0 / 35.0 | [−8.44, +2.82] / [−8.46, +2.81] |
| B1c | check 2025→2026-10-09 | 6,350 | **−11.00**, −268.77 | −11.03, −269.36 | 59.0 / 59.0 | [−16.67, −5.04] / [−16.70, −5.06] |
| B2a | check 2025→2026-10-09 | 5,406 | **−5.05**, −116.08 | −5.07, −116.37 | 39.7 / 39.7 | [−6.43, −4.01] / [−6.44, −4.02] |
| B2b | check 2025→2026-10-09 | 5,406 | **−4.28**, −114.81 | −4.29, −115.10 | 35.4 / 35.4 | [−9.47, +3.42] / [−9.49, +3.40] |
| B2c | check 2025→2026-10-09 | 5,406 | **−14.04**, −340.73 | −14.07, −341.32 | 57.3 / 57.3 | [−21.01, −5.68] / [−21.04, −5.71] |
| B3a | check 2025→2026-10-09 | 5,454 | **−5.86**, −62.38 | −6.35, −63.19 | 37.5 / 37.4 | [−7.25, −4.50] / [−7.74, −5.02] |
| B3b | check 2025→2026-10-09 | 5,454 | **−7.17**, −55.57 | −7.66, −56.38 | 31.6 / 31.5 | [−11.78, −2.80] / [−12.26, −3.30] |
| B3c | check 2025→2026-10-09 | 5,454 | **−18.89**, −148.59 | −19.87, −150.21 | 53.7 / 53.6 | [−26.18, −12.17] / [−27.20, −13.13] |

**Random baseline** (as the study computed it, at its own fees): 500 cell-matched random draws per rule and exit (step6/out/results.csv): the rule's percentile is printed there; on Check 14 of 18 rule × exit cells sit below the 20th.

**Exit reasons (share of trades):**

- pick 2022-05→2024: half at +40%, trail the rest 50%, out at 3:30 33.3%; time 20.4%; stop 15.9%; trail 11.9%; target 10.9%; time_armed 7.6%
- check 2025→2026-10-09: half at +40%, trail the rest 50%, out at 3:30 33.3%; time 21.0%; stop 17.5%; trail 10.7%; target 10.0%; time_armed 7.6%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | A1a | 218 | 40.4 | −1.06 | −90.49 | −19,727 |
| 2023 | A1a | 249 | 59.4 | +7.33 | +5.46 | +1,359 |
| 2024 | A1a | 198 | 48.5 | −2.05 | −13.46 | −2,665 |
| 2025 | A1a | 615 | 44.1 | −1.07 | +32.65 | +20,082 |
| 2026 | A1a | 420 | 25.7 | −14.99 | −106.44 | −44,704 |
| 2022 | A1b | 218 | 22.5 | −9.04 | −137.71 | −30,020 |
| 2023 | A1b | 249 | 43.8 | +6.75 | −8.77 | −2,183 |
| 2024 | A1b | 198 | 27.8 | −26.49 | −138.51 | −27,425 |
| 2025 | A1b | 615 | 33.7 | −3.02 | −353.37 | −217,325 |
| 2026 | A1b | 420 | 18.3 | −46.69 | −444.24 | −186,581 |
| 2022 | A1c | 218 | 61.9 | −10.30 | −183.45 | −39,991 |
| 2023 | A1c | 249 | 75.5 | +17.04 | −4.26 | −1,060 |
| 2024 | A1c | 198 | 61.6 | −34.88 | −161.05 | −31,889 |
| 2025 | A1c | 615 | 64.9 | −3.33 | −363.00 | −223,243 |
| 2026 | A1c | 420 | 38.1 | −85.48 | −768.59 | −322,809 |
| 2022 | A2a | 341 | 37.5 | −6.84 | −59.24 | −20,201 |
| 2023 | A2a | 403 | 46.9 | −0.68 | −9.28 | −3,740 |
| 2024 | A2a | 337 | 44.2 | −0.61 | +26.06 | +8,781 |
| 2025 | A2a | 1,058 | 31.1 | −11.14 | −122.47 | −129,574 |
| 2026 | A2a | 444 | 35.4 | −8.74 | −22.73 | −10,094 |
| 2022 | A2b | 341 | 27.3 | −5.78 | −71.82 | −24,492 |
| 2023 | A2b | 403 | 33.3 | +18.53 | +48.86 | +19,691 |
| 2024 | A2b | 337 | 39.5 | +25.30 | +117.76 | +39,686 |
| 2025 | A2b | 1,058 | 35.7 | −8.12 | −68.40 | −72,363 |
| 2026 | A2b | 444 | 36.7 | −18.50 | −60.03 | −26,653 |
| 2022 | A2c | 341 | 62.8 | −5.91 | −36.06 | −12,296 |
| 2023 | A2c | 403 | 70.0 | +23.79 | +57.73 | +23,265 |
| 2024 | A2c | 337 | 60.5 | +18.00 | +60.56 | +20,408 |
| 2025 | A2c | 1,058 | 57.1 | −22.02 | −212.45 | −224,768 |
| 2026 | A2c | 444 | 53.2 | −35.16 | −103.87 | −46,118 |
| 2022 | A3a | 493 | 48.5 | +2.75 | +48.91 | +24,112 |
| 2023 | A3a | 440 | 48.2 | +0.72 | −23.36 | −10,276 |
| 2024 | A3a | 306 | 44.4 | −2.47 | −36.48 | −11,164 |
| 2025 | A3a | 1,516 | 36.7 | −7.38 | −73.51 | −111,435 |
| 2026 | A3a | 919 | 37.8 | −6.10 | −27.52 | −25,294 |
| 2022 | A3b | 493 | 27.2 | −1.70 | +56.95 | +28,076 |
| 2023 | A3b | 440 | 30.2 | −2.25 | −3.95 | −1,737 |
| 2024 | A3b | 306 | 30.4 | −12.08 | −74.28 | −22,731 |
| 2025 | A3b | 1,516 | 27.9 | −22.64 | −401.46 | −608,621 |
| 2026 | A3b | 919 | 30.7 | −18.85 | −119.97 | −110,248 |
| 2022 | A3c | 493 | 65.9 | −0.02 | +89.54 | +44,143 |
| 2023 | A3c | 440 | 74.5 | +8.16 | +115.29 | +50,728 |
| 2024 | A3c | 306 | 54.9 | −22.56 | −111.48 | −34,112 |
| 2025 | A3c | 1,516 | 52.4 | −40.91 | −640.99 | −971,742 |
| 2026 | A3c | 919 | 58.0 | −31.75 | −195.90 | −180,033 |
| 2023 | B1a | 911 | 43.4 | −3.69 | −71.84 | −65,442 |
| 2024 | B1a | 1,515 | 41.7 | −3.97 | −81.50 | −123,477 |
| 2025 | B1a | 3,411 | 42.0 | −3.87 | −85.14 | −290,404 |
| 2026 | B1a | 2,939 | 41.3 | −4.06 | −93.89 | −275,938 |
| 2023 | B1b | 911 | 36.2 | −3.34 | −78.31 | −71,343 |
| 2024 | B1b | 1,515 | 33.4 | +5.26 | +118.50 | +179,525 |
| 2025 | B1b | 3,411 | 36.1 | −1.44 | −50.85 | −173,447 |
| 2026 | B1b | 2,939 | 33.9 | −5.51 | −143.57 | −421,965 |
| 2023 | B1c | 911 | 59.9 | −8.59 | −171.21 | −155,975 |
| 2024 | B1c | 1,515 | 57.5 | −2.29 | −34.65 | −52,500 |
| 2025 | B1c | 3,411 | 60.1 | −7.57 | −175.77 | −599,566 |
| 2026 | B1c | 2,939 | 57.8 | −14.98 | −376.71 | −1,107,153 |
| 2022 | B2a | 247 | 39.7 | −5.50 | −117.31 | −28,974 |
| 2023 | B2a | 775 | 37.5 | −5.42 | −104.41 | −80,916 |
| 2024 | B2a | 1,461 | 39.0 | −5.25 | −100.89 | −147,395 |
| 2025 | B2a | 2,755 | 40.3 | −4.72 | −102.86 | −283,385 |
| 2026 | B2a | 2,651 | 39.0 | −5.41 | −129.81 | −344,135 |
| 2022 | B2b | 247 | 33.2 | −17.66 | −395.41 | −97,667 |
| 2023 | B2b | 775 | 34.1 | −10.26 | −223.55 | −173,248 |
| 2024 | B2b | 1,461 | 35.5 | +3.38 | +72.46 | +105,867 |
| 2025 | B2b | 2,755 | 36.9 | +1.06 | +22.17 | +61,092 |
| 2026 | B2b | 2,651 | 33.9 | −9.82 | −257.17 | −681,750 |
| 2022 | B2c | 247 | 50.2 | −33.33 | −708.26 | −174,939 |
| 2023 | B2c | 775 | 54.7 | −20.22 | −396.09 | −306,968 |
| 2024 | B2c | 1,461 | 57.4 | −5.14 | −85.92 | −125,530 |
| 2025 | B2c | 2,755 | 58.3 | −7.49 | −151.34 | −416,933 |
| 2026 | B2c | 2,651 | 56.4 | −20.84 | −537.56 | −1,425,064 |
| 2024 | B3a | 752 | 43.9 | −2.20 | +26.47 | +19,903 |
| 2025 | B3a | 3,157 | 36.8 | −6.42 | −86.42 | −272,818 |
| 2026 | B3a | 2,297 | 38.4 | −5.10 | −29.34 | −67,388 |
| 2024 | B3b | 752 | 32.6 | +0.06 | +73.91 | +55,578 |
| 2025 | B3b | 3,157 | 31.5 | −6.89 | −60.70 | −191,615 |
| 2026 | B3b | 2,297 | 31.8 | −7.56 | −48.53 | −111,463 |
| 2024 | B3c | 752 | 56.0 | −7.11 | +70.91 | +53,325 |
| 2025 | B3c | 3,157 | 52.7 | −19.32 | −180.17 | −568,806 |
| 2026 | B3c | 2,297 | 55.0 | −18.30 | −105.18 | −241,604 |
| 2022 | all names | 3,897 | 43.9 | −6.21 | −90.32 | −351,977 |
| 2023 | all names | 8,334 | 47.7 | −1.75 | −93.33 | −777,846 |
| 2024 | all names | 13,707 | 44.4 | −2.06 | −6.99 | −95,814 |
| 2025 | all names | 37,536 | 43.2 | −8.88 | −140.53 | −5,274,871 |
| 2026 | all names | 29,010 | 42.3 | −13.12 | −194.04 | −5,628,994 |

![](charts/s17.png)

**Amendments, deviations and integrity checks.** The rules are chosen by the committed step6/trade.py choose() on the scratchpad population (39 MB, not committed); verify.py 0 differences in 480 figures; lookahead.py 0 differences in 104,748 values.

**What it showed.** No rule chosen on Pick made money on Check.

## #18 Compass engine audit (six module groups)

**Folder:** `research_notes/Compass engine audit/, reports/Compass engine audit.md`. **Commits:** — / — / 9cf8110, 59e1a1a, d724ae4, 18cf86a, b84fa3c, 09799af; report 138ff0e. **Dates:** 2026-10-21.

**Hypothesis.** The owner's 16-module Compass specification picks direction and opens trades that pay after costs.

**Rule.** Each module tested under its own definition (exits and sizing, expected move/ATR/flow, clock and power hour, greeks and books, horizons, sweep and grade).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Ask in, bid out, $0.65 each way.

**Data.** 0DTE SPY/QQQ/IWM/SPXW 980/980/621/1,106 sessions; daily bars for horizons.

**Periods and holdouts.** fit 2022–24 / check 2025–26.

**Pass rule (as pre-registered).** Picked on 2022–24, read on 2025–26, friction-adjusted.

**Verdict.** No directional rule survives after fees. What holds: the 15:58 flat, the −32% backstop, a breakeven lock at +0% with a target on, a trailed remainder, the r,q pricer from parity, Method A flips with three books, net/gross confidence, the MOC magnitude as a volatility gauge, an ATR > 1.5 block on counter-trend fades.

**Metrics.** not available — the audit committed row-level paths and events (paths_\*.parquet, events_\*.parquet) and per-cell tables; its exit stacks were scored by cell, and no single trade list per rule exists to recompute (spec stack A −4.3% / B −4.5% of debit a trade, exits_sizing.md line 14).

**Amendments, deviations and integrity checks.** Six blockers stated (no OPRA tape, no strike-level OI history before 2026-10, …).

**What it showed.** Frictions, not edges.

## #19 Phase 2 hyp A: the low-moc_mag closing pin (SPXW short call spread, 15:30, held)

**Folder:** `research_notes/Compass phase 2/hyp_a_closing_pin`. **Commits:** prereg in-doc before the OOS read / — / 5deb793. **Dates:** 2026-10-21.

**Hypothesis.** On quiet closes (low moc_mag) the 15:30 short credit spread pins and pays.

**Rule.** SPXW short call spread, short strike at 1.00 × the move rule, 25 wide, 15:30 at the NBBO, held to settlement, on low-moc_mag sessions (the pre-registered cell).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry; bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPXW 2022-05-13 → 2026-10-09.

**Periods and holdouts.** fit 2022–24 / OOS 2025–26 (read once).

**Pass rule (as pre-registered).** The pick fixed on fit; read OOS for a positive mean with an interval clear of zero.

**Verdict.** NO EDGE: fit +$26 a spread, OOS −$33 [−84, +13].

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | fit 2022–24 | 252 | 252 / 656 | 91.7 | +2.3, +55.08 | −12.2, −299.66 | +1.9, +45.42 | **+1.07**, +25.52 | [+0.42, +1.63]; [+9.66, +38.99] |
| SPXW | OOS 2025–26 | 177 | 177 / 456 | 87.6 | +2.6, +62.08 | −29.6, −709.56 | +2.0, +47.92 | **−1.43**, −33.83 | [−3.57, +0.26]; [−85.45, +6.92] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | fit 2022–24 | +197.83, +8.6%, 2022-09-16, SPXW 15:30 3880.0/3905.0C | −688.08, −28.1%, 2023-03-08, SPXW 15:30 3985.0/4010.0C | 2.02 | 919 | 99 | 13% |
| SPXW | OOS 2025–26 | +172.83, +7.4%, 2025-04-14, SPXW 15:30 5450.0/5475.0C | −2,312.17, −100.1%, 2025-04-30, SPXW 15:30 5535.0/5560.0C | 0.62 | 8,138 | 426 | total ≤ 0 (best 5 days +789; without them −6,778) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.30 a trade) and Robinhood's charged instead (mean $2.10). The study's fees are given beside them below. Re-pricing: exact (429 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | fit 2022–24 | 252 | **+1.07**, +25.52 | +1.10, +26.31 | 91.7 / 91.7 | [+0.42, +1.63] / [+0.45, +1.66] |
| SPXW | OOS 2025–26 | 177 | **−1.43**, −33.83 | −1.39, −33.03 | 87.6 / 87.6 | [−3.57, +0.26] / [−3.53, +0.30] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 55 | 92.7 | +2.19 | +52.38 | +2,881 |
| 2023 | SPXW | 95 | 90.5 | +0.43 | +10.56 | +1,003 |
| 2024 | SPXW | 102 | 92.2 | +1.05 | +24.96 | +2,546 |
| 2025 | SPXW | 94 | 88.3 | −1.62 | −37.93 | −3,565 |
| 2026 | SPXW | 83 | 86.7 | −1.20 | −29.19 | −2,423 |

![](charts/s19.png)

**Amendments, deviations and integrity checks.** Cells and the pick written before the OOS run (s3_report.py fit, then oos).

**What it showed.** The pin made money on fit and lost out of sample.

## #20a Phase 2 hyp B: boundary touch — SPY 2-wide 25-delta credit spread, held (the touch pick)

**Folder:** `research_notes/Compass phase 2/hyp_b_boundary_theta`. **Commits:** out/prereg.txt before the OOS read / — / 2c241f4. **Dates:** 2026-10-21.

**Hypothesis.** When price touches the straddle boundary, the far side's credit spread decays faster.

**Rule.** At a touch: sell the 2-wide spread on the touched side, short strike at 25 delta, held to settlement.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry; bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPY 2022-11 → 2026-10.

**Periods and holdouts.** fit 2022–24 / OOS 2025–26.

**Pass rule (as pre-registered).** The highest fit lower bound (N ≥ 300, ≥ 150 sessions, positive without the best 5); its lower bound was negative ("least bad").

**Verdict.** No edge: the touch adds nothing over the unconditional sell at the same minute (the increment flips sign between periods).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | fit 2022–24 | 2,890 | 512 / 553 | 83.7 | +11.3, +19.81 | −47.3, −83.52 | +9.4, +16.90 | **+1.74**, +3.01 | [−0.14, +3.51]; [−0.35, +6.15] |
| SPY | OOS 2025–26 | 2,600 | 432 / 457 | 88.2 | +12.6, +21.86 | −54.9, −95.16 | +11.1, +19.90 | **+4.59**, +8.04 | [+2.24, +6.37]; [+3.91, +11.15] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | fit 2022–24 | +44.90, +29.0%, 2024-08-28, SPY 554.0/552.0 down | −194.10, −100.1%, 2024-05-31, SPY 525.0/527.0 up | 1.22 | 3,489 | 165 | 16% |
| SPY | OOS 2025–26 | +45.90, +29.8%, 2025-11-14, SPY 673.0/675.0 up | −190.10, −99.5%, 2026-04-13, SPY 684.0/686.0 up | 1.72 | 4,370 | 59 | 8% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.30 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (5,490 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | fit 2022–24 | 2,890 | **+1.74**, +3.01 | +1.07, +1.81 | 83.7 / 83.5 | [−0.14, +3.51] / [−0.80, +2.84] |
| SPY | OOS 2025–26 | 2,600 | **+4.59**, +8.04 | +3.91, +6.84 | 88.2 / 88.1 | [+2.24, +6.37] / [+1.56, +5.68] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPY | 188 | 80.9 | +1.43 | +2.26 | +425 |
| 2023 | SPY | 1,366 | 82.8 | +1.38 | +2.35 | +3,205 |
| 2024 | SPY | 1,336 | 85.1 | +2.15 | +3.79 | +5,068 |
| 2025 | SPY | 1,457 | 87.7 | +4.36 | +7.60 | +11,067 |
| 2026 | SPY | 1,143 | 88.8 | +4.89 | +8.60 | +9,836 |

![](charts/s20a.png)

**Amendments, deviations and integrity checks.** Deduplicated as analyze.py (one touch a session, side, e, mult, rule, width).

**What it showed.** Positive in both periods but no better than selling unconditionally.

## #20b Phase 2 hyp B: the midday SPY iron condor (em1, mid-VIX), the midday pick

**Folder:** `research_notes/Compass phase 2/hyp_b_boundary_theta`. **Commits:** out/prereg.txt / — / 2c241f4. **Dates:** 2026-10-21.

**Hypothesis.** Midday iron condors on SPY are unconditional short premium that pays.

**Rule.** 11:30–13:30 every half hour: SPY 2-wide iron condor, shorts at the first listed strikes outside spot ± the ATM straddle, held to settlement, VIX in the fit's middle tercile.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry; bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPY 2022-11 → 2026-10.

**Periods and holdouts.** fit 2022–24 / OOS 2025–26.

**Pass rule (as pre-registered).** As 20a.

**Verdict.** "Needs X" (a forward paper run): +4.6% of risk fit, +3.3% OOS (CI $0.03–$10.69). Became the tracker's condor_em1 (all-VIX parent, #26).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | fit 2022–24 | 748 | 178 / 510 | 80.7 | +17.0, +28.34 | −40.0, −68.04 | +14.2, +24.30 | **+6.02**, +9.78 | [+2.67, +9.18]; [+4.23, +15.06] |
| SPY | OOS 2025–26 | 1,202 | 280 / 456 | 81.9 | +16.8, +28.18 | −50.4, −83.87 | +14.2, +24.80 | **+4.67**, +7.95 | [+1.62, +7.46]; [+2.98, +12.41] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | fit 2022–24 | +64.80, +48.0%, 2024-09-18, None | −173.20, −100.1%, 2024-09-11, None | 1.75 | 1,387 | 57 | 18% |
| SPY | OOS 2025–26 | +58.80, +41.7%, 2026-04-29, None | −176.20, −100.1%, 2026-07-24, None | 1.53 | 1,696 | 92 | 13% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (1,950 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | fit 2022–24 | 748 | **+6.02**, +9.78 | +4.61, +7.39 | 80.7 / 80.5 | [+2.67, +9.18] / [+1.27, +7.77] |
| SPY | OOS 2025–26 | 1,202 | **+4.67**, +7.95 | +3.25, +5.55 | 81.9 / 81.6 | [+1.62, +7.46] / [+0.21, +6.04] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2023 | SPY | 388 | 74.7 | +2.43 | +3.99 | +1,550 |
| 2024 | SPY | 360 | 87.2 | +9.88 | +16.02 | +5,769 |
| 2025 | SPY | 631 | 83.5 | +6.05 | +10.06 | +6,350 |
| 2026 | SPY | 571 | 80.2 | +3.13 | +5.62 | +3,210 |

![](charts/s20b.png)

**Amendments, deviations and integrity checks.** The VIX terciles recomputed from the fit d15 condors exactly as analyze.py.

**What it showed.** Small positive in both periods; $5 a condor on a four-leg structure.

## #21a Phase 2 hyp C: 15:00 SPY/QQQ P1 iron ±2 butterfly, held to settlement

**Folder:** `research_notes/Compass phase 2/hyp_c_debit_flies`. **Commits:** preregistration.md before the OOS run / — / faea67c. **Dates:** 2026-10-21.

**Hypothesis.** Late-day ATM butterflies on quiet closes pin.

**Rule.** 15:00, SPY and QQQ, P1 iron ±2 at the 4-leg NBBO, held to settlement, unconditional.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry (four legs); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPY and QQQ 2022-11 → 2026-10.

**Periods and holdouts.** fit 2022–24 / OOS 2025–26.

**Pass rule (as pre-registered).** Edge only if the OOS mean is positive with its interval clear of zero AND positive without the best five sessions AND both OOS years positive.

**Verdict.** Not confirmed: the picks fell to +2 to +4.5% of risk OOS with intervals through zero and die under $0.01 a leg; the un-picked iron ±5 read +5.0/+6.0% (→ the tracker's fly5).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | fit 2022–24 | 521 | 521 / 553 | 64.5 | +54.4, +50.94 | −51.8, −49.88 | +23.4, +25.80 | **+16.71**, +15.14 | [+11.64, +23.15]; [+10.82, +20.41] |
| SPY | fit 2022–24 | 525 | 525 / 553 | 63.4 | +50.9, +49.19 | −51.8, −51.01 | +18.3, +21.80 | **+13.33**, +12.54 | [+8.43, +18.36]; [+8.36, +16.78] |
| all names | fit 2022–24 | 1,046 | 529 / 553 | 64.0 | +52.7, +50.07 | −51.8, −50.46 | +21.5, +23.80 | **+15.01**, +13.84 | [+10.61, +20.36]; [+10.06, +18.07] |
| QQQ | OOS 2025–26 | 440 | 440 / 457 | 51.4 | +75.9, +57.13 | −69.3, −52.57 | +2.3, +2.55 | **+5.29**, +3.78 | [−2.50, +13.57]; [−2.32, +10.23] |
| SPY | OOS 2025–26 | 438 | 438 / 457 | 55.3 | +65.6, +53.87 | −59.4, −48.97 | +10.7, +11.05 | **+9.65**, +7.85 | [+2.22, +18.07]; [+1.83, +15.04] |
| all names | OOS 2025–26 | 878 | 440 / 457 | 53.3 | +70.6, +55.45 | −64.6, −50.85 | +6.8, +6.80 | **+7.46**, +5.81 | [+0.15, +15.30]; [+0.44, +12.00] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | fit 2022–24 | +138.80, +261.9%, 2024-02-01, QQQ 1500 iron K0 422.0 ±2.0 | −142.20, −100.1%, 2023-07-07, QQQ 1500 iron K0 369.0 ±2.0 | 1.85 | 592 | 65 | 8% |
| SPY | fit 2022–24 | +132.80, +201.2%, 2024-12-31, SPY 1500 iron K0 586.0 ±2.0 | −144.20, −100.1%, 2024-03-26, SPY 1500 iron K0 521.0 ±2.0 | 1.67 | 381 | 52 | 10% |
| all names | fit 2022–24 | +138.80, +261.9%, 2024-02-01, QQQ 1500 iron K0 422.0 ±2.0 | −144.20, −100.1%, 2024-03-26, SPY 1500 iron K0 521.0 ±2.0 | 1.76 | 829 | 34 | 8% |
| QQQ | OOS 2025–26 | +155.80, +380.0%, 2026-01-28, QQQ 1500 iron K0 633.0 ±2.0 | −118.20, −100.2%, 2026-09-14, QQQ 1500 iron K0 712.0 ±2.0 | 1.15 | 923 | 142 | 42% |
| SPY | OOS 2025–26 | +149.30, +364.1%, 2026-09-16, SPY 1500 iron K0 754.0 ±2.0 | −130.20, −100.2%, 2026-01-07, SPY 1500 iron K0 692.0 ±2.0 | 1.36 | 725 | 85 | 20% |
| all names | OOS 2025–26 | +155.80, +380.0%, 2026-01-28, QQQ 1500 iron K0 633.0 ±2.0 | −130.20, −100.2%, 2026-01-07, SPY 1500 iron K0 692.0 ±2.0 | 1.24 | 1,552 | 131 | 26% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (1,924 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | fit 2022–24 | 521 | **+16.71**, +15.14 | +14.26, +12.74 | 64.5 / 63.1 | [+11.64, +23.15] / [+9.21, +20.69] |
| SPY | fit 2022–24 | 525 | **+13.33**, +12.54 | +10.95, +10.14 | 63.4 / 62.1 | [+8.43, +18.36] / [+6.16, +15.93] |
| all names | fit 2022–24 | 1,046 | **+15.01**, +13.84 | +12.60, +11.44 | 64.0 / 62.6 | [+10.61, +20.36] / [+8.22, +17.89] |
| QQQ | OOS 2025–26 | 440 | **+5.29**, +3.78 | +2.16, +1.38 | 51.4 / 50.0 | [−2.50, +13.57] / [−5.77, +10.53] |
| SPY | OOS 2025–26 | 438 | **+9.65**, +7.85 | +6.84, +5.45 | 55.3 / 54.6 | [+2.22, +18.07] / [−0.71, +15.31] |
| all names | OOS 2025–26 | 878 | **+7.46**, +5.81 | +4.49, +3.41 | 53.3 / 52.3 | [+0.15, +15.30] / [−2.96, +12.33] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | QQQ | 33 | 75.8 | +21.33 | +16.12 | +532 |
| 2023 | QQQ | 247 | 65.2 | +16.18 | +15.55 | +3,842 |
| 2024 | QQQ | 241 | 62.2 | +16.62 | +14.59 | +3,515 |
| 2025 | QQQ | 246 | 54.1 | +4.09 | +5.47 | +1,345 |
| 2026 | QQQ | 194 | 47.9 | +6.80 | +1.64 | +318 |
| 2022 | SPY | 32 | 65.6 | +33.20 | +24.89 | +797 |
| 2023 | SPY | 246 | 65.4 | +12.72 | +13.36 | +3,287 |
| 2024 | SPY | 247 | 61.1 | +11.35 | +10.13 | +2,501 |
| 2025 | SPY | 244 | 53.7 | +4.74 | +4.87 | +1,189 |
| 2026 | SPY | 194 | 57.2 | +15.84 | +11.60 | +2,250 |
| 2022 | all names | 65 | 70.8 | +27.18 | +20.44 | +1,328 |
| 2023 | all names | 493 | 65.3 | +14.46 | +14.46 | +7,128 |
| 2024 | all names | 488 | 61.7 | +13.96 | +12.33 | +6,017 |
| 2025 | all names | 490 | 53.9 | +4.41 | +5.17 | +2,534 |
| 2026 | all names | 388 | 52.6 | +11.32 | +6.62 | +2,568 |

![](charts/s21a.png)

**Amendments, deviations and integrity checks.** Fill stress ($0.01 a leg) read on both periods as a robustness check.

**What it showed.** Positive on fit, shrunk to noise out of sample.

## #21b Phase 2 hyp C: 15:00 SPY/QQQ P2 call ±2 butterfly, held to settlement

**Folder:** `research_notes/Compass phase 2/hyp_c_debit_flies`. **Commits:** preregistration.md before the OOS run / — / faea67c. **Dates:** 2026-10-21.

**Hypothesis.** Late-day ATM butterflies on quiet closes pin.

**Rule.** 15:00, SPY and QQQ, P2 call ±2 at the 4-leg NBBO, held to settlement, unconditional.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry (four legs); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPY and QQQ 2022-11 → 2026-10.

**Periods and holdouts.** fit 2022–24 / OOS 2025–26.

**Pass rule (as pre-registered).** Edge only if the OOS mean is positive with its interval clear of zero AND positive without the best five sessions AND both OOS years positive.

**Verdict.** Not confirmed: the picks fell to +2 to +4.5% of risk OOS with intervals through zero and die under $0.01 a leg; the un-picked iron ±5 read +5.0/+6.0% (→ the tracker's fly5).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | fit 2022–24 | 522 | 522 / 553 | 62.3 | +51.6, +49.62 | −50.2, −50.30 | +20.0, +22.82 | **+13.21**, +11.91 | [+8.31, +19.56]; [+7.53, +17.25] |
| SPY | fit 2022–24 | 525 | 525 / 553 | 61.5 | +48.4, +47.92 | −50.4, −51.29 | +16.7, +18.82 | **+10.40**, +9.74 | [+5.72, +15.41]; [+5.43, +14.06] |
| all names | fit 2022–24 | 1,047 | 530 / 553 | 61.9 | +50.0, +48.77 | −50.3, −50.80 | +18.4, +20.82 | **+11.80**, +10.83 | [+7.47, +17.08]; [+6.96, +15.13] |
| QQQ | OOS 2025–26 | 441 | 441 / 457 | 49.9 | +73.0, +56.05 | −68.4, −53.62 | −0.2, −0.18 | **+2.15**, +1.09 | [−5.56, +10.35]; [−5.02, +7.63] |
| SPY | OOS 2025–26 | 439 | 439 / 457 | 54.7 | +63.7, +53.10 | −59.4, −49.86 | +8.6, +8.82 | **+7.90**, +6.43 | [+0.28, +16.44]; [+0.32, +13.68] |
| all names | OOS 2025–26 | 880 | 441 / 457 | 52.3 | +68.2, +54.51 | −64.1, −51.84 | +4.4, +4.82 | **+5.02**, +3.75 | [−2.27, +12.91]; [−1.67, +9.95] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | fit 2022–24 | +137.82, +255.2%, 2024-02-01, QQQ 1500 call K0 422.0 ±2.0 | −146.18, −100.1%, 2023-07-07, QQQ 1500 call K0 369.0 ±2.0 | 1.63 | 696 | 92 | 10% |
| SPY | fit 2022–24 | +131.82, +376.6%, 2024-08-28, SPY 1500 call K0 558.0 ±2.0 | −149.18, −100.1%, 2024-03-26, SPY 1500 call K0 521.0 ±2.0 | 1.49 | 495 | 62 | 12% |
| all names | fit 2022–24 | +137.82, +255.2%, 2024-02-01, QQQ 1500 call K0 422.0 ±2.0 | −149.18, −100.1%, 2024-03-26, SPY 1500 call K0 521.0 ±2.0 | 1.56 | 877 | 44 | 11% |
| QQQ | OOS 2025–26 | +153.82, +357.7%, 2026-01-28, QQQ 1500 call K0 633.0 ±2.0 | −130.18, −100.1%, 2025-11-05, QQQ 1500 call K0 626.0 ±2.0 | 1.04 | 1,152 | 197 | 144% |
| SPY | OOS 2025–26 | +149.32, +364.2%, 2026-09-16, SPY 1500 call K0 754.0 ±2.0 | −131.18, −100.1%, 2026-01-07, SPY 1500 call K0 692.0 ±2.0 | 1.28 | 823 | 120 | 25% |
| all names | OOS 2025–26 | +153.82, +357.7%, 2026-01-28, QQQ 1500 call K0 633.0 ±2.0 | −131.18, −100.1%, 2026-01-07, SPY 1500 call K0 692.0 ±2.0 | 1.15 | 1,781 | 141 | 39% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.18). The study's fees are given beside them below. Re-pricing: exact (1,927 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | fit 2022–24 | 522 | **+13.21**, +11.91 | +10.81, +9.49 | 62.3 / 61.5 | [+8.31, +19.56] / [+5.90, +17.14] |
| SPY | fit 2022–24 | 525 | **+10.40**, +9.74 | +8.07, +7.33 | 61.5 / 59.6 | [+5.72, +15.41] / [+3.41, +13.02] |
| all names | fit 2022–24 | 1,047 | **+11.80**, +10.83 | +9.44, +8.41 | 61.9 / 60.6 | [+7.47, +17.08] / [+5.18, +14.71] |
| QQQ | OOS 2025–26 | 441 | **+2.15**, +1.09 | −0.92, −1.33 | 49.9 / 48.3 | [−5.56, +10.35] / [−8.71, +7.43] |
| SPY | OOS 2025–26 | 439 | **+7.90**, +6.43 | +5.11, +4.01 | 54.7 / 54.2 | [+0.28, +16.44] / [−2.63, +13.75] |
| all names | OOS 2025–26 | 880 | **+5.02**, +3.75 | +2.09, +1.34 | 52.3 / 51.2 | [−2.27, +12.91] / [−5.35, +10.06] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | QQQ | 33 | 72.7 | +17.18 | +11.71 | +387 |
| 2023 | QQQ | 247 | 62.8 | +12.66 | +12.16 | +3,004 |
| 2024 | QQQ | 242 | 60.3 | +13.22 | +11.69 | +2,828 |
| 2025 | QQQ | 247 | 52.2 | +0.89 | +2.73 | +675 |
| 2026 | QQQ | 194 | 46.9 | +3.75 | −0.99 | −193 |
| 2022 | SPY | 32 | 65.6 | +29.27 | +21.79 | +697 |
| 2023 | SPY | 246 | 63.4 | +10.24 | +10.86 | +2,671 |
| 2024 | SPY | 247 | 59.1 | +8.11 | +7.07 | +1,747 |
| 2025 | SPY | 245 | 52.7 | +2.49 | +3.08 | +754 |
| 2026 | SPY | 194 | 57.2 | +14.73 | +10.66 | +2,068 |
| 2022 | all names | 65 | 69.2 | +23.14 | +16.67 | +1,084 |
| 2023 | all names | 493 | 63.1 | +11.45 | +11.51 | +5,675 |
| 2024 | all names | 489 | 59.7 | +10.64 | +9.36 | +4,575 |
| 2025 | all names | 492 | 52.4 | +1.69 | +2.90 | +1,428 |
| 2026 | all names | 388 | 52.1 | +9.24 | +4.83 | +1,876 |

![](charts/s21b.png)

**Amendments, deviations and integrity checks.** Fill stress ($0.01 a leg) read on both periods as a robustness check.

**What it showed.** Positive on fit, shrunk to noise out of sample.

## #21c Phase 2 hyp C: 15:00 SPY/QQQ P3 call ±5 butterfly, held to settlement

**Folder:** `research_notes/Compass phase 2/hyp_c_debit_flies`. **Commits:** preregistration.md before the OOS run / — / faea67c. **Dates:** 2026-10-21.

**Hypothesis.** Late-day ATM butterflies on quiet closes pin.

**Rule.** 15:00, SPY and QQQ, P3 call ±5 at the 4-leg NBBO, held to settlement, unconditional.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry (four legs); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPY and QQQ 2022-11 → 2026-10.

**Periods and holdouts.** fit 2022–24 / OOS 2025–26.

**Pass rule (as pre-registered).** Edge only if the OOS mean is positive with its interval clear of zero AND positive without the best five sessions AND both OOS years positive.

**Verdict.** Not confirmed: the picks fell to +2 to +4.5% of risk OOS with intervals through zero and die under $0.01 a leg; the un-picked iron ±5 read +5.0/+6.0% (→ the tracker's fly5).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | fit 2022–24 | 523 | 523 / 553 | 67.7 | +16.3, +58.86 | −20.1, −75.05 | +7.5, +30.82 | **+4.53**, +15.59 | [+2.84, +6.89]; [+10.26, +22.80] |
| SPY | fit 2022–24 | 524 | 524 / 553 | 66.2 | +15.1, +55.82 | −19.4, −74.67 | +5.9, +24.82 | **+3.43**, +11.74 | [+1.76, +5.46]; [+5.76, +18.73] |
| all names | fit 2022–24 | 1,047 | 530 / 553 | 67.0 | +15.7, +57.36 | −19.7, −74.85 | +7.0, +27.82 | **+3.98**, +13.67 | [+2.47, +6.05]; [+8.57, +20.25] |
| QQQ | OOS 2025–26 | 438 | 438 / 457 | 56.2 | +25.4, +77.79 | −28.9, −97.59 | +5.1, +19.82 | **+1.60**, +0.91 | [−1.59, +4.74]; [−9.97, +11.22] |
| SPY | OOS 2025–26 | 440 | 440 / 457 | 62.3 | +21.8, +71.33 | −25.2, −83.42 | +7.3, +25.82 | **+4.08**, +12.95 | [+1.51, +6.61]; [+4.72, +21.89] |
| all names | OOS 2025–26 | 878 | 441 / 457 | 59.2 | +23.5, +74.39 | −27.2, −91.02 | +5.6, +21.82 | **+2.84**, +6.94 | [+0.10, +5.46]; [−2.06, +16.24] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | fit 2022–24 | +288.81, +207.8%, 2024-08-28, QQQ 1500 call K0 472.0 ±5.0 | −367.18, −100.0%, 2024-05-31, QQQ 1500 call K0 446.0 ±5.0 | 1.64 | 738 | 64 | 14% |
| SPY | fit 2022–24 | +270.82, +138.2%, 2024-08-28, SPY 1500 call K0 558.0 ±5.0 | −405.18, −100.0%, 2024-05-31, SPY 1500 call K0 521.0 ±5.0 | 1.47 | 851 | 113 | 17% |
| all names | fit 2022–24 | +288.81, +207.8%, 2024-08-28, QQQ 1500 call K0 472.0 ±5.0 | −405.18, −100.0%, 2024-05-31, SPY 1500 call K0 521.0 ±5.0 | 1.55 | 1,296 | 39 | 14% |
| QQQ | OOS 2025–26 | +276.81, +170.9%, 2026-04-29, QQQ 1500 call K0 661.0 ±5.0 | −468.18, −100.0%, 2026-05-12, QQQ 1500 call K0 702.0 ±5.0 | 1.02 | 2,030 | 214 | 318% |
| SPY | OOS 2025–26 | +267.32, +119.9%, 2026-09-16, SPY 1500 call K0 754.0 ±5.0 | −342.18, −100.1%, 2026-03-09, SPY 1500 call K0 670.0 ±5.0 | 1.41 | 1,171 | 81 | 20% |
| all names | OOS 2025–26 | +276.81, +170.9%, 2026-04-29, QQQ 1500 call K0 661.0 ±5.0 | −468.18, −100.0%, 2026-05-12, QQQ 1500 call K0 702.0 ±5.0 | 1.19 | 3,102 | 128 | 38% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.18). The study's fees are given beside them below. Re-pricing: exact (1,925 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | fit 2022–24 | 523 | **+4.53**, +15.59 | +3.91, +13.17 | 67.7 / 66.3 | [+2.84, +6.89] / [+2.23, +6.26] |
| SPY | fit 2022–24 | 524 | **+3.43**, +11.74 | +2.81, +9.32 | 66.2 / 64.9 | [+1.76, +5.46] / [+1.17, +4.83] |
| all names | fit 2022–24 | 1,047 | **+3.98**, +13.67 | +3.36, +11.25 | 67.0 / 65.6 | [+2.47, +6.05] / [+1.85, +5.44] |
| QQQ | OOS 2025–26 | 438 | **+1.60**, +0.91 | +0.90, −1.51 | 56.2 / 55.5 | [−1.59, +4.74] / [−2.31, +4.05] |
| SPY | OOS 2025–26 | 440 | **+4.08**, +12.95 | +3.40, +10.53 | 62.3 / 61.6 | [+1.51, +6.61] / [+0.80, +5.95] |
| all names | OOS 2025–26 | 878 | **+2.84**, +6.94 | +2.15, +4.52 | 59.2 / 58.5 | [+0.10, +5.46] / [−0.59, +4.78] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | QQQ | 32 | 75.0 | +5.41 | +13.08 | +419 |
| 2023 | QQQ | 247 | 66.0 | +4.43 | +17.19 | +4,246 |
| 2024 | QQQ | 244 | 68.4 | +4.52 | +14.31 | +3,491 |
| 2025 | QQQ | 246 | 56.9 | +0.95 | −0.14 | −34 |
| 2026 | QQQ | 192 | 55.2 | +2.42 | +2.26 | +434 |
| 2022 | SPY | 33 | 72.7 | +7.77 | +22.26 | +735 |
| 2023 | SPY | 247 | 67.6 | +3.54 | +13.88 | +3,429 |
| 2024 | SPY | 244 | 63.9 | +2.73 | +8.15 | +1,990 |
| 2025 | SPY | 247 | 60.3 | +2.78 | +9.04 | +2,232 |
| 2026 | SPY | 193 | 64.8 | +5.74 | +17.95 | +3,465 |
| 2022 | all names | 65 | 73.8 | +6.61 | +17.74 | +1,153 |
| 2023 | all names | 494 | 66.8 | +3.99 | +15.54 | +7,675 |
| 2024 | all names | 488 | 66.2 | +3.62 | +11.23 | +5,480 |
| 2025 | all names | 493 | 58.6 | +1.87 | +4.46 | +2,198 |
| 2026 | all names | 385 | 60.0 | +4.08 | +10.13 | +3,898 |

![](charts/s21c.png)

**Amendments, deviations and integrity checks.** Fill stress ($0.01 a leg) read on both periods as a robustness check.

**What it showed.** Positive on fit, shrunk to noise out of sample.

## #21d Phase 2 hyp C: debit vertical 0.70/0.30, universe B, held (the vertical pick)

**Folder:** `research_notes/Compass phase 2/hyp_c_debit_flies`. **Commits:** preregistration.md / — / faea67c. **Dates:** 2026-10-21.

**Hypothesis.** A debit vertical keeps the directional premium at lower cost.

**Rule.** The audit's universe B entries, 0.70Δ/0.30Δ debit vertical, held to settlement.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry; bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)

**Data.** SPY, QQQ, IWM, SPXW 2022–2026.

**Periods and holdouts.** fit / OOS.

**Pass rule (as pre-registered).** Pre-registered expectation: negative OOS.

**Verdict.** Loses less than the naked contract but still loses (−6.7% of debit fit).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | fit 2022–24 | 173 | 173 / 182 | 54.9 | +60.6, +44.65 | −69.8, −49.86 | +10.0, +10.90 | **+1.83**, +2.04 | [−10.09, +9.51]; [−7.68, +8.86] |
| QQQ | fit 2022–24 | 530 | 530 / 553 | 50.2 | +70.2, +93.93 | −69.9, −89.38 | +1.1, +1.90 | **+0.42**, +2.62 | [−6.74, +8.85]; [−8.28, +15.78] |
| SPXW | fit 2022–24 | 656 | 656 / 683 | 45.4 | +74.7, +883.66 | −77.7, −953.83 | −14.5, −156.76 | **−8.47**, −119.12 | [−13.29, −1.93]; [−183.46, −32.45] |
| SPY | fit 2022–24 | 530 | 530 / 553 | 44.0 | +69.7, +81.90 | −75.6, −90.73 | −20.9, −24.10 | **−11.74**, −14.84 | [−17.85, −4.31]; [−22.97, −4.02] |
| all names | fit 2022–24 | 1,889 | 656 / 683 | 47.2 | +70.5, +349.37 | −74.4, −397.10 | −9.3, −14.10 | **−5.95**, −44.61 | [−9.17, −2.36]; [−66.16, −15.55] |
| IWM | OOS 2025–26 | 439 | 439 / 457 | 50.6 | +67.0, +60.94 | −73.1, −61.82 | +0.9, +0.90 | **−2.25**, +0.26 | [−9.15, +4.45]; [−7.00, +7.58] |
| QQQ | OOS 2025–26 | 441 | 441 / 457 | 51.9 | +71.6, +135.52 | −70.9, −133.29 | +9.4, +14.90 | **+3.07**, +6.30 | [−4.60, +9.89]; [−9.53, +21.99] |
| SPXW | OOS 2025–26 | 441 | 441 / 457 | 51.7 | +71.7, +1,074.83 | −78.1, −1,140.55 | +5.4, +69.74 | **−0.63**, +4.82 | [−9.01, +7.72]; [−103.56, +117.40] |
| SPY | OOS 2025–26 | 440 | 440 / 457 | 53.6 | +73.9, +115.70 | −67.8, −110.02 | +12.6, +18.90 | **+8.17**, +11.05 | [+0.57, +15.59]; [−2.69, +24.29] |
| all names | OOS 2025–26 | 1,761 | 441 / 457 | 52.0 | +71.1, +346.37 | −72.5, −362.95 | +6.7, +10.90 | **+2.09**, +5.61 | [−2.01, +5.45]; [−21.65, +33.23] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | fit 2022–24 | +137.90, +93.2%, 2024-08-08, IWM CALL 0.70/0.30 m56 | −212.10, −100.0%, 2024-06-12, IWM CALL 0.70/0.30 m146 | 1.09 | 660 | 77 | 168% |
| QQQ | fit 2022–24 | +370.90, +95.8%, 2022-12-14, QQQ PUT 0.70/0.30 m54 | −321.10, −100.0%, 2024-11-20, QQQ PUT 0.70/0.30 m66 | 1.06 | 2,897 | 229 | 110% |
| SPXW | fit 2022–24 | +4,407.74, +107.8%, 2022-09-21, SPXW PUT 0.70/0.30 m59 | −4,492.26, −100.1%, 2022-12-14, SPXW CALL 0.70/0.30 m90 | 0.77 | 80,420 | 678 | total ≤ 0 (best 5 days +14,715; without them −92,857) |
| SPY | fit 2022–24 | +338.90, +93.9%, 2023-03-22, SPY PUT 0.70/0.30 m96 | −454.10, −100.0%, 2022-12-14, SPY CALL 0.70/0.30 m160 | 0.71 | 8,263 | 553 | total ≤ 0 (best 5 days +1,317; without them −9,182) |
| all names | fit 2022–24 | +4,407.74, +107.8%, 2022-09-21, SPXW PUT 0.70/0.30 m59 | −4,492.26, −100.1%, 2022-12-14, SPXW CALL 0.70/0.30 m90 | 0.79 | 86,543 | 678 | total ≤ 0 (best 5 days +13,891; without them −98,156) |
| IWM | OOS 2025–26 | +218.90, +120.9%, 2026-09-16, IWM PUT 0.70/0.30 m108 | −394.10, −94.3%, 2025-06-23, IWM PUT 0.70/0.30 m30 | 1.01 | 1,967 | 351 | 930% |
| QQQ | OOS 2025–26 | +594.90, +117.8%, 2026-06-10, QQQ PUT 0.70/0.30 m62 | −619.10, −67.0%, 2025-04-07, QQQ PUT 0.70/0.30 m66 | 1.10 | 2,749 | 185 | 92% |
| SPXW | OOS 2025–26 | +6,047.74, +87.0%, 2025-04-11, SPXW CALL 0.70/0.30 m99 | −7,092.26, −100.0%, 2025-04-10, SPXW PUT 0.70/0.30 m176 | 1.01 | 34,735 | 286 | 1149% |
| SPY | OOS 2025–26 | +690.90, +85.4%, 2025-04-11, SPY CALL 0.70/0.30 m52 | −558.10, −100.0%, 2025-04-08, SPY CALL 0.70/0.30 m197 | 1.22 | 2,148 | 225 | 51% |
| all names | OOS 2025–26 | +6,047.74, +87.0%, 2025-04-11, SPXW CALL 0.70/0.30 m99 | −7,092.26, −100.0%, 2025-04-10, SPXW PUT 0.70/0.30 m176 | 1.03 | 32,160 | 261 | 268% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.30 a trade) and Robinhood's charged instead (mean $0.75). The study's fees are given beside them below. Re-pricing: exact (2,553 trades); Robinhood fees inferred from the rule: SPXW legs' price tier ($1.00 and up) (1,097 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | fit 2022–24 | 173 | **+1.83**, +2.04 | −0.05, +0.84 | 54.9 / 54.9 | [−10.09, +9.51] / [−12.07, +7.72] |
| QQQ | fit 2022–24 | 530 | **+0.42**, +2.62 | −0.66, +1.42 | 50.2 / 50.2 | [−6.74, +8.85] / [−7.85, +7.82] |
| SPXW | fit 2022–24 | 656 | **−8.47**, −119.12 | −8.38, −118.16 | 45.4 / 45.4 | [−13.29, −1.93] / [−13.19, −1.84] |
| SPY | fit 2022–24 | 530 | **−11.74**, −14.84 | −12.94, −16.04 | 44.0 / 44.0 | [−17.85, −4.31] / [−19.06, −5.52] |
| all names | fit 2022–24 | 1,889 | **−5.95**, −44.61 | −6.73, −45.06 | 47.2 / 47.2 | [−9.17, −2.36] / [−9.96, −3.11] |
| IWM | OOS 2025–26 | 439 | **−2.25**, +0.26 | −3.93, −0.94 | 50.6 / 49.7 | [−9.15, +4.45] / [−10.90, +2.84] |
| QQQ | OOS 2025–26 | 441 | **+3.07**, +6.30 | +2.26, +5.10 | 51.9 / 51.5 | [−4.60, +9.89] / [−5.49, +9.09] |
| SPXW | OOS 2025–26 | 441 | **−0.63**, +4.82 | −0.55, +5.78 | 51.7 / 51.7 | [−9.01, +7.72] / [−8.93, +7.80] |
| SPY | OOS 2025–26 | 440 | **+8.17**, +11.05 | +7.22, +9.85 | 53.6 / 53.6 | [+0.57, +15.59] / [−0.41, +14.64] |
| all names | OOS 2025–26 | 1,761 | **+2.09**, +5.61 | +1.25, +4.95 | 52.0 / 51.6 | [−2.01, +5.45] / [−2.84, +4.65] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022–24: settle 100.0%
- OOS 2025–26: settle 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 173 | 54.9 | +1.83 | +2.04 | +353 |
| 2025 | IWM | 245 | 48.6 | −6.41 | −0.55 | −134 |
| 2026 | IWM | 194 | 53.1 | +3.00 | +1.28 | +247 |
| 2022 | QQQ | 33 | 42.4 | −1.42 | −3.18 | −105 |
| 2023 | QQQ | 248 | 51.6 | +1.55 | +6.07 | +1,507 |
| 2024 | QQQ | 249 | 49.8 | −0.46 | −0.05 | −13 |
| 2025 | QQQ | 247 | 51.4 | +0.09 | +2.10 | +520 |
| 2026 | QQQ | 194 | 52.6 | +6.87 | +11.64 | +2,257 |
| 2022 | SPXW | 159 | 47.2 | −6.24 | −111.25 | −17,688 |
| 2023 | SPXW | 248 | 46.0 | −8.93 | −119.26 | −29,577 |
| 2024 | SPXW | 249 | 43.8 | −9.45 | −124.00 | −30,877 |
| 2025 | SPXW | 247 | 49.8 | −2.50 | −39.58 | −9,776 |
| 2026 | SPXW | 194 | 54.1 | +1.76 | +61.34 | +11,900 |
| 2022 | SPY | 33 | 30.3 | −30.24 | −64.56 | −2,130 |
| 2023 | SPY | 248 | 42.7 | −13.29 | −13.19 | −3,272 |
| 2024 | SPY | 249 | 47.0 | −7.74 | −9.89 | −2,463 |
| 2025 | SPY | 246 | 51.6 | +3.63 | +5.73 | +1,410 |
| 2026 | SPY | 194 | 56.2 | +13.94 | +17.79 | +3,452 |
| 2022 | all names | 225 | 44.0 | −9.05 | −88.55 | −19,924 |
| 2023 | all names | 744 | 46.8 | −6.89 | −42.13 | −31,342 |
| 2024 | all names | 920 | 48.4 | −4.43 | −35.87 | −32,999 |
| 2025 | all names | 985 | 50.4 | −1.29 | −8.10 | −7,981 |
| 2026 | all names | 776 | 54.0 | +6.39 | +23.01 | +17,857 |

![](charts/s21d.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** Verticals lose less than calls and puts, and still lose.

## #22 Phase 2 hyp D: volatility breakout (straddles on the model's top decile)

**Folder:** `research_notes/Compass phase 2/hyp_d_vol_breakout`. **Commits:** out/preregistered.md / — / da02507. **Dates:** 2026-10-21.

**Hypothesis.** The volatility model's top decile marks straddles worth buying.

**Rule.** Buy straddles/strangles on the top-decile scan minutes.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry

**Data.** SPY/QQQ/IWM/SPXW 2022–2026.

**Periods and holdouts.** fit / cut / OOS (read once).

**Pass rule (as pre-registered).** Best-on-fit cell positive OOS.

**Verdict.** No edge: the best-on-fit cell flipped from +4.6% to −7.0%; the model forecasts volatility (AUC 0.71–0.73) but the straddle is already priced richer.

**Metrics.** not available — committed as cells by scan minute and decile (cells_\*.csv, minutes_\*.parquet); no trade list of the pre-registered cell.

**Amendments, deviations and integrity checks.** —

**What it showed.** Forecasting volatility is not trading it.

## #24 Phase 3 hyp E: short-premium lift of the vol model's quiet deciles

**Folder:** `research_notes/Compass phase 3/hyp_e_short_premium_lift`. **Commits:** out/preregistered.md / — / 02d0dcd. **Dates:** 2026-10-21.

**Hypothesis.** Quiet deciles lift the SPY short-premium spread over selling unconditionally.

**Rule.** Sell the SPY spread on the bottom deciles vs unconditionally, same minute.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a contract (leg) to open, nothing at expiry

**Data.** SPY 2022-11 → 2026-10.

**Periods and holdouts.** fit / OOS.

**Pass rule (as pre-registered).** A pre-registrable lift on fit.

**Verdict.** No edge established — not pre-registrable (no fit cell clear of zero); the D1 condor read later became condor_d20 (#26).

**Metrics.** not available — committed as by-scan cells and pooled tables; the candidate was set after the OOS read (see #26 condor_d20 for its trades).

**Amendments, deviations and integrity checks.** —

**What it showed.** No lift on fit.

## #25 Phase 3 hyp F: the 15:30 SPY/QQQ long call ±5 butterfly (cash account)

**Folder:** `research_notes/Compass phase 3/hyp_f_cash_butterfly`. **Commits:** out/preregistered.md (20:44:54 UTC) / — / f2883c0; report b7ffa46. **Dates:** 2026-10-21.

**Hypothesis.** The cash-account call fly at 15:30 keeps hyp C's OOS edge under realistic complex-order fills.

**Rule.** 15:30, SPY and QQQ, long call butterfly ±5 around the ATM strike at the 4-leg NBBO package, held to settlement.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.65 a leg, four legs to open, none at expiry; package at the NBBO (k = 0).

**Data.** SPY, QQQ 2022-11-11 → 2026-10-09.

**Periods and holdouts.** fit 2022-11 → 2024 / OOS 2025 → 2026-10-09 (the same OOS C read).

**Pass rule (as pre-registered).** Four parts: OOS mean > 0 with its interval clear of zero at k = 0; also under $0.01 a leg worse; positive without the best five sessions; both names positive.

**Verdict.** Passes all four, but the cell was named after C's OOS was printed: a conditionally justified rule, to be confirmed forward (≈ 450 sessions); dies at $0.02 a leg.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | fit 2022-11→2024 | 526 | 526 / 553 | 66.3 | +13.7, +50.50 | −16.5, −67.55 | +5.7, +24.82 | **+3.52**, +10.78 | [+1.96, +6.01]; [+5.58, +19.00] |
| SPY | fit 2022-11→2024 | 522 | 522 / 553 | 65.5 | +11.7, +45.76 | −16.1, −65.07 | +4.9, +20.82 | **+2.15**, +7.54 | [+0.69, +4.13]; [+1.88, +14.88] |
| all names | fit 2022-11→2024 | 1,048 | 529 / 553 | 65.9 | +12.7, +48.15 | −16.3, −66.30 | +5.1, +21.82 | **+2.84**, +9.17 | [+1.40, +4.94]; [+4.22, +16.39] |
| QQQ | OOS 2025–26 | 439 | 439 / 457 | 61.3 | +21.3, +67.68 | −23.1, −83.58 | +5.4, +20.82 | **+4.14**, +9.11 | [+1.31, +6.99]; [+0.01, +17.59] |
| SPY | OOS 2025–26 | 440 | 440 / 457 | 64.8 | +17.6, +60.78 | −18.6, −67.76 | +6.4, +26.82 | **+4.86**, +15.50 | [+2.74, +7.06]; [+8.63, +22.33] |
| all names | OOS 2025–26 | 879 | 441 / 457 | 63.0 | +19.4, +64.13 | −20.9, −76.03 | +5.7, +24.32 | **+4.50**, +12.31 | [+2.14, +6.84]; [+4.78, +19.17] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | fit 2022-11→2024 | +289.81, +210.0%, 2024-08-28, QQQ 1530 call fly K0 472.0 ±5 | −405.18, −100.0%, 2024-12-18, QQQ 1530 call fly K0 522.0 ±5 | 1.47 | 1,263 | 48 | 19% |
| SPY | fit 2022-11→2024 | +228.82, +112.2%, 2024-08-28, SPY 1530 call fly K0 559.0 ±5 | −420.18, −100.0%, 2024-05-31, SPY 1530 call fly K0 522.0 ±5 | 1.34 | 1,281 | 106 | 23% |
| all names | fit 2022-11→2024 | +289.81, +210.0%, 2024-08-28, QQQ 1530 call fly K0 472.0 ±5 | −420.18, −100.0%, 2024-05-31, SPY 1530 call fly K0 522.0 ±5 | 1.41 | 1,999 | 88 | 19% |
| QQQ | OOS 2025–26 | +261.82, +147.9%, 2026-04-29, QQQ 1530 call fly K0 661.0 ±5 | −332.18, −100.1%, 2025-03-04, QQQ 1530 call fly K0 502.0 ±5 | 1.28 | 1,434 | 153 | 31% |
| SPY | OOS 2025–26 | +237.82, +104.8%, 2025-11-19, SPY 1530 call fly K0 663.0 ±5 | −290.18, −73.8%, 2025-05-22, SPY 1530 call fly K0 587.0 ±5 | 1.65 | 1,080 | 67 | 16% |
| all names | OOS 2025–26 | +261.82, +147.9%, 2026-04-29, QQQ 1530 call fly K0 661.0 ±5 | −332.18, −100.1%, 2025-03-04, QQQ 1530 call fly K0 502.0 ±5 | 1.44 | 2,393 | 80 | 21% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.18). The study's fees are given beside them below. Re-pricing: exact (1,927 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | fit 2022-11→2024 | 526 | **+3.52**, +10.78 | +2.93, +8.36 | 66.3 / 65.2 | [+1.96, +6.01] / [+1.37, +5.42] |
| SPY | fit 2022-11→2024 | 522 | **+2.15**, +7.54 | +1.56, +5.12 | 65.5 / 63.8 | [+0.69, +4.13] / [+0.11, +3.53] |
| all names | fit 2022-11→2024 | 1,048 | **+2.84**, +9.17 | +2.25, +6.75 | 65.9 / 64.5 | [+1.40, +4.94] / [+0.83, +4.35] |
| QQQ | OOS 2025–26 | 439 | **+4.14**, +9.11 | +3.48, +6.69 | 61.3 / 60.1 | [+1.31, +6.99] / [+0.65, +6.32] |
| SPY | OOS 2025–26 | 440 | **+4.86**, +15.50 | +4.22, +13.08 | 64.8 / 64.3 | [+2.74, +7.06] / [+2.11, +6.41] |
| all names | OOS 2025–26 | 879 | **+4.50**, +12.31 | +3.85, +9.89 | 63.0 / 62.2 | [+2.14, +6.84] / [+1.49, +6.20] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- fit 2022-11→2024: held to settlement 100.0%
- OOS 2025–26: held to settlement 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | QQQ | 33 | 60.6 | +0.19 | −0.83 | −27 |
| 2023 | QQQ | 248 | 68.1 | +3.69 | +13.62 | +3,378 |
| 2024 | QQQ | 245 | 65.3 | +3.79 | +9.47 | +2,320 |
| 2025 | QQQ | 247 | 59.9 | +3.49 | +6.41 | +1,584 |
| 2026 | QQQ | 192 | 63.0 | +4.97 | +12.57 | +2,414 |
| 2022 | SPY | 32 | 71.9 | +5.26 | +18.77 | +601 |
| 2023 | SPY | 248 | 67.7 | +2.90 | +11.07 | +2,744 |
| 2024 | SPY | 242 | 62.4 | +0.96 | +2.44 | +591 |
| 2025 | SPY | 246 | 63.4 | +3.60 | +10.78 | +2,651 |
| 2026 | SPY | 194 | 66.5 | +6.45 | +21.49 | +4,169 |
| 2022 | all names | 65 | 66.2 | +2.69 | +8.82 | +573 |
| 2023 | all names | 496 | 67.9 | +3.30 | +12.34 | +6,122 |
| 2024 | all names | 487 | 63.9 | +2.39 | +5.98 | +2,911 |
| 2025 | all names | 493 | 61.7 | +3.55 | +8.59 | +4,235 |
| 2026 | all names | 386 | 64.8 | +5.71 | +17.05 | +6,583 |

![](charts/s25.png)

**Amendments, deviations and integrity checks.** The selection is not independent of the OOS it was read on (stated in the report).

**What it showed.** +3.85% of risk a fly OOS, carried by the same data that chose it.

## #26a Paper tracker: condor_em1 (SPY 2-wide iron condor at ± the ATM straddle, 11:30–13:30)

**Folder:** `scripts/paper_tracker.py; research_notes/Compass phase 3/backtest_replay, backtest_audit, forward_*`. **Commits:** defaults ba117a7, 6826b98 / official-close settlement a4ebe90, 99a3d4e, 16eb3c0 / replay 94af538, 30bb73e; audit 1ca1f0e; forward d7115b6, 2a7bd3b. **Dates:** 2026-10-21 → 22.

**Hypothesis.** The midday SPY condor of hyp B (#20b), all-VIX form, pays forward.

**Rule.** 11:30, 12:00, 12:30, 13:00, 13:30: SPY 2-wide iron condor, shorts the first listed strikes outside spot ± the ATM straddle, held to the official close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Shorts at the bid, longs at the ask; $0.65 a contract (leg) to open, nothing at expiry.

**Data.** The replay of every stored session through the live tracker's code, settled on the official close (data_recorder/paper_backtest_official, git-ignored, every trade).

**Periods and holdouts.** i development 2022-11-11 → 2024-12-31 / ii selection 2025-01-02 → 2026-10-09 (read) / iii forward 2026-10-12 → (untouched). No historical period is untouched for any candidate (AUDIT.md §5).

**Pass rule (as pre-registered).** Confirmation: 60 → 120 forward sessions (the candidate's threshold).

**Verdict.** Historical periods through zero (i +3.47 [−0.04, +6.68], ii +4.10 [−0.51, +8.15]); the 15:58 close-out turns it negative; forward pending.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | i | 2,358 | 525 / 553 | 80.5 | +15.6, +26.27 | −46.0, −78.29 | +12.2, +21.80 | **+3.56**, +5.87 | [+1.48, +5.58]; [+2.36, +9.29] |
| SPY | ii | 2,068 | 439 / 457 | 80.7 | +18.8, +30.76 | −58.5, −94.98 | +14.8, +25.80 | **+3.90**, +6.50 | [+0.90, +6.46]; [+1.71, +10.55] |
| SPY | iii | 44 | 9 / 9 | 86.4 | +16.9, +28.33 | −53.6, −88.53 | +14.5, +25.30 | **+7.25**, +12.39 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | i | +68.80, +52.5%, 2022-12-14, SPY 12:30 −C411/−C413/−P396/−P394 | −189.20, −100.1%, 2023-07-07, SPY 13:30 −C444/−C446/−P441/−P439 | 1.38 | 2,344 | 98 | 10% |
| SPY | ii | +65.80, +49.1%, 2026-07-29, SPY 13:00 −C741/−C743/−P729/−P727 | −185.20, −100.1%, 2025-04-09, SPY 13:30 −C536/−C538/−P512/−P510 | 1.35 | 2,737 | 67 | 11% |
| SPY | iii | +46.80, +30.6%, 2026-10-22, SPY 11:30 −C767/−C769/−P760/−P758 | −168.20, −100.1%, 2026-10-16, SPY 11:30 −C772/−C774/−P766/−P764 | 2.03 | 443 | 4 | 148% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (4,470 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | i | 2,358 | **+3.56**, +5.87 | +2.16, +3.47 | 80.5 / 80.2 | [+1.48, +5.58] / [+0.08, +4.18] |
| SPY | ii | 2,068 | **+3.90**, +6.50 | +2.46, +4.10 | 80.7 / 80.4 | [+0.90, +6.46] / [−0.54, +5.02] |
| SPY | iii | 44 | **+7.25**, +12.39 | +5.84, +9.99 | 86.4 / 86.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- i: held to settlement (official close) 100.0%
- ii: held to settlement (official close) 100.0%
- iii: held to settlement (official close) 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPY | 159 | 82.4 | +6.98 | +11.78 | +1,873 |
| 2023 | SPY | 1,080 | 78.2 | +1.59 | +2.56 | +2,761 |
| 2024 | SPY | 1,119 | 82.4 | +4.98 | +8.24 | +9,216 |
| 2025 | SPY | 1,129 | 81.8 | +4.97 | +8.05 | +9,086 |
| 2026 | SPY | 983 | 79.8 | +2.82 | +4.99 | +4,907 |

![](charts/s26a.png)

**Amendments, deviations and integrity checks.** Deterministic (a cold replay equals the committed CSV byte for byte); 100 trades re-derived, 0 differences; re-settled on the official close (12,338 of 20,469 trades changed).

**What it showed.** A few dollars a condor in both historical periods, inside the noise.

## #26b Paper tracker: fly5 (SPY/QQQ ±5 butterflies at 15:00 and 15:30: iron, call, put)

**Folder:** `scripts/paper_tracker.py; research_notes/Compass phase 3/backtest_replay, backtest_audit, forward_*`. **Commits:** defaults ba117a7, 6826b98 / official-close settlement a4ebe90, 99a3d4e, 16eb3c0 / replay 94af538, 30bb73e; audit 1ca1f0e; forward d7115b6, 2a7bd3b. **Dates:** 2026-10-21 → 22.

**Hypothesis.** The late-day ±5 fly of hyp C/F pays forward.

**Rule.** 15:00 and 15:30: SPY and QQQ ±5 iron, call and put butterflies (one trade seen three ways), held to the official close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Shorts at the bid, longs at the ask; $0.65 a contract (leg) to open, nothing at expiry.

**Data.** The replay of every stored session through the live tracker's code, settled on the official close (data_recorder/paper_backtest_official, git-ignored, every trade).

**Periods and holdouts.** i development 2022-11-11 → 2024-12-31 / ii selection 2025-01-02 → 2026-10-09 (read) / iii forward 2026-10-12 → (untouched). No historical period is untouched for any candidate (AUDIT.md §5).

**Pass rule (as pre-registered).** Confirmation: 250 forward sessions a name.

**Verdict.** Iron clear of zero in i and ii (+16.59, +16.20 a trade) but chosen on ii; hold-to-expiry leaves 100 shares a fly; the after-hours rule (#27) DROPS the iron as a SPY/QQQ hold-to-expiry strategy.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ call | i | 1,049 | 528 / 553 | 67.8 | +15.0, +54.56 | −18.1, −70.70 | +6.6, +27.82 | **+4.29**, +14.20 | [+2.86, +6.62]; [+9.41, +21.45] |
| QQQ iron | i | 1,049 | 528 / 553 | 70.4 | +16.2, +58.48 | −18.2, −68.71 | +8.2, +33.80 | **+6.01**, +20.78 | [+4.42, +8.44]; [+16.04, +27.95] |
| QQQ put | i | 1,051 | 529 / 553 | 66.9 | +14.8, +54.17 | −17.7, −68.90 | +6.6, +26.82 | **+4.06**, +13.42 | [+2.63, +6.39]; [+8.84, +20.65] |
| SPY call | i | 1,046 | 525 / 553 | 65.2 | +13.6, +51.58 | −17.3, −68.37 | +5.5, +22.82 | **+2.84**, +9.84 | [+1.44, +4.70]; [+4.49, +16.39] |
| SPY iron | i | 1,046 | 525 / 553 | 70.1 | +14.5, +54.41 | −18.3, −69.95 | +7.5, +30.80 | **+4.68**, +17.20 | [+3.38, +6.49]; [+12.45, +23.13] |
| SPY put | i | 1,046 | 525 / 553 | 61.7 | +13.5, +50.90 | −16.4, −65.52 | +4.4, +17.82 | **+2.00**, +6.27 | [+0.43, +3.98]; [+0.20, +13.46] |
| all names | i | 6,287 | 530 / 553 | 67.0 | +14.6, +54.11 | −17.6, −68.58 | +6.4, +26.80 | **+3.98**, +13.62 | [+2.65, +6.02]; [+9.09, +20.10] |
| QQQ call | ii | 877 | 439 / 457 | 58.0 | +23.6, +73.52 | −25.8, −89.43 | +4.9, +20.82 | **+2.88**, +5.14 | [+0.52, +5.22]; [−3.06, +13.07] |
| QQQ iron | ii | 877 | 439 / 457 | 63.7 | +25.3, +77.91 | −26.8, −87.08 | +8.4, +33.80 | **+6.41**, +18.09 | [+4.18, +8.62]; [+10.35, +25.33] |
| QQQ put | ii | 877 | 439 / 457 | 57.2 | +23.3, +72.48 | −25.7, −89.48 | +4.3, +17.82 | **+2.36**, +3.23 | [−0.03, +4.65]; [−5.04, +10.84] |
| SPY call | ii | 880 | 441 / 457 | 62.5 | +20.0, +67.05 | −21.8, −74.57 | +6.5, +26.82 | **+4.31**, +13.94 | [+2.58, +6.09]; [+8.02, +20.31] |
| SPY iron | ii | 880 | 441 / 457 | 65.0 | +20.8, +69.13 | −22.2, −73.79 | +7.8, +30.80 | **+5.78**, +19.11 | [+4.08, +7.55]; [+13.03, +25.40] |
| SPY put | ii | 880 | 441 / 457 | 62.0 | +19.9, +66.54 | −21.9, −75.18 | +6.2, +24.82 | **+4.02**, +12.75 | [+2.30, +5.86]; [+6.59, +19.20] |
| all names | ii | 5,271 | 441 / 457 | 61.4 | +22.1, +71.07 | −24.1, −81.95 | +6.2, +24.82 | **+4.29**, +12.05 | [+2.45, +6.13]; [+5.53, +18.35] |
| QQQ call | iii | 18 | 9 / 9 | 77.8 | +36.8, +110.68 | −19.9, −74.68 | +27.9, +82.32 | **+24.16**, +69.49 | n/a (< 60 sessions); n/a (< 60 sessions) |
| QQQ iron | iii | 18 | 9 / 9 | 77.8 | +38.7, +115.16 | −18.4, −67.20 | +29.9, +89.30 | **+26.03**, +74.63 | n/a (< 60 sessions); n/a (< 60 sessions) |
| QQQ put | iii | 18 | 9 / 9 | 77.8 | +36.9, +110.82 | −19.1, −70.68 | +28.4, +80.82 | **+24.49**, +70.49 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY call | iii | 18 | 9 / 9 | 61.1 | +22.6, +81.91 | −9.2, −37.47 | +14.5, +49.32 | **+10.27**, +35.49 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY iron | iii | 18 | 9 / 9 | 61.1 | +22.9, +82.44 | −9.0, −36.92 | +14.5, +54.30 | **+10.47**, +36.02 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY put | iii | 18 | 9 / 9 | 61.1 | +22.7, +82.09 | −9.1, −37.18 | +14.4, +53.82 | **+10.36**, +35.71 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | iii | 108 | 9 / 9 | 69.4 | +31.0, +98.99 | −12.7, −49.43 | +18.2, +67.30 | **+17.63**, +53.64 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ call | i | +296.81, +215.1%, 2024-08-28, QQQ 15:30 −C467/−C472/−C477 | −405.18, −100.0%, 2024-12-18, QQQ 15:30 −C517/−C522/−C527 | 1.62 | 1,830 | 36 | 14% |
| QQQ iron | i | +298.80, +219.7%, 2024-08-28, QQQ 15:00 −C472/−P472/−P467/−C477 | −349.20, −100.1%, 2024-07-25, QQQ 15:30 −C464/−P464/−P459/−C469 | 2.02 | 1,370 | 31 | 10% |
| QQQ put | i | +295.81, +212.8%, 2024-08-28, QQQ 15:00 −P467/−P472/−P477 | −372.18, −100.0%, 2024-07-25, QQQ 15:30 −P459/−P464/−P469 | 1.59 | 1,633 | 37 | 15% |
| SPY call | i | +273.82, +139.7%, 2024-08-28, SPY 15:00 −C553/−C558/−C563 | −420.18, −100.0%, 2024-05-31, SPY 15:30 −C517/−C522/−C527 | 1.41 | 1,480 | 106 | 18% |
| SPY iron | i | +275.80, +142.2%, 2024-08-28, SPY 15:00 −C558/−P558/−P553/−C563 | −399.20, −100.1%, 2024-05-31, SPY 15:30 −C522/−P522/−P517/−C527 | 1.82 | 1,046 | 30 | 10% |
| SPY put | i | +273.82, +139.7%, 2024-08-28, SPY 15:00 −P553/−P558/−P563 | −405.18, −100.0%, 2024-05-31, SPY 15:00 −P516/−P521/−P526 | 1.25 | 3,410 | 207 | 27% |
| all names | i | +298.80, +219.7%, 2024-08-28, QQQ 15:00 −C472/−P472/−P467/−C477 | −420.18, −100.0%, 2024-05-31, SPY 15:30 −C517/−C522/−C527 | 1.60 | 8,141 | 44 | 13% |
| QQQ call | ii | +280.82, +173.3%, 2026-04-29, QQQ 15:00 −C656/−C661/−C666 | −468.18, −100.0%, 2026-05-12, QQQ 15:00 −C697/−C702/−C707 | 1.14 | 3,185 | 130 | 51% |
| QQQ iron | ii | +282.80, +176.7%, 2026-04-29, QQQ 15:00 −C661/−P661/−P656/−C666 | −347.20, −100.1%, 2026-03-09, QQQ 15:00 −C600/−P600/−P595/−C605 | 1.57 | 1,714 | 50 | 15% |
| QQQ put | ii | +280.81, +173.3%, 2026-04-29, QQQ 15:00 −P656/−P661/−P666 | −363.18, −100.0%, 2026-03-09, QQQ 15:00 −P595/−P600/−P605 | 1.08 | 3,215 | 180 | 82% |
| SPY call | ii | +271.82, +121.9%, 2026-09-16, SPY 15:00 −C749/−C754/−C759 | −342.18, −100.1%, 2026-03-09, SPY 15:00 −C665/−C670/−C675 | 1.50 | 1,480 | 57 | 15% |
| SPY iron | ii | +271.80, +121.9%, 2026-09-16, SPY 15:00 −C754/−P754/−P749/−C759 | −341.20, −100.1%, 2026-03-09, SPY 15:00 −C670/−P670/−P665/−C675 | 1.74 | 1,248 | 34 | 11% |
| SPY put | ii | +270.82, +120.9%, 2026-09-16, SPY 15:00 −P749/−P754/−P759 | −346.18, −100.1%, 2026-03-09, SPY 15:00 −P665/−P670/−P675 | 1.45 | 1,569 | 63 | 17% |
| all names | ii | +282.80, +176.7%, 2026-04-29, QQQ 15:00 −C661/−P661/−P656/−C666 | −468.18, −100.0%, 2026-05-12, QQQ 15:00 −C697/−C702/−C707 | 1.38 | 10,116 | 86 | 19% |
| QQQ call | iii | +177.82, +73.5%, 2026-10-21, QQQ 15:30 −C721/−C726/−C731 | −151.18, −43.1%, 2026-10-15, QQQ 15:00 −C720/−C725/−C730 | 5.19 | 38 | 1 | 98% |
| QQQ iron | iii | +181.80, +76.4%, 2026-10-21, QQQ 15:30 −C726/−P726/−P721/−C731 | −141.20, −41.4%, 2026-10-15, QQQ 15:00 −C725/−P725/−P720/−C730 | 6.00 | 27 | 1 | 95% |
| QQQ put | iii | +178.82, +74.2%, 2026-10-21, QQQ 15:30 −P721/−P726/−P731 | −145.18, −42.1%, 2026-10-15, QQQ 15:00 −P720/−P725/−P730 | 5.49 | 37 | 1 | 98% |
| SPY call | iii | +158.82, +47.8%, 2026-10-21, SPY 15:30 −C768/−C773/−C778 | −69.18, −16.6%, 2026-10-19, SPY 15:30 −C763/−C768/−C773 | 3.44 | 116 | 2 | 121% |
| SPY iron | iii | +158.80, +47.8%, 2026-10-21, SPY 15:30 −C773/−P773/−P768/−C778 | −71.20, −17.0%, 2026-10-19, SPY 15:30 −C768/−P768/−P763/−C773 | 3.51 | 119 | 2 | 121% |
| SPY put | iii | +156.82, +47.0%, 2026-10-21, SPY 15:30 −P768/−P773/−P778 | −72.18, −17.2%, 2026-10-19, SPY 15:30 −P763/−P768/−P773 | 3.47 | 120 | 2 | 121% |
| all names | iii | +181.80, +76.4%, 2026-10-21, QQQ 15:30 −C726/−P726/−P721/−C731 | −151.18, −43.1%, 2026-10-15, QQQ 15:00 −C720/−C725/−C730 | 4.55 | 295 | 1 | 96% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.19). The study's fees are given beside them below. Re-pricing: exact (11,666 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ call | i | 1,049 | **+4.29**, +14.20 | +3.69, +11.78 | 67.8 / 66.7 | [+2.86, +6.62] / [+2.25, +6.00] |
| QQQ iron | i | 1,049 | **+6.01**, +20.78 | +5.39, +18.38 | 70.4 / 69.5 | [+4.42, +8.44] / [+3.81, +7.82] |
| QQQ put | i | 1,051 | **+4.06**, +13.42 | +3.45, +11.00 | 66.9 / 65.8 | [+2.63, +6.39] / [+2.03, +5.76] |
| SPY call | i | 1,046 | **+2.84**, +9.84 | +2.24, +7.42 | 65.2 / 64.1 | [+1.44, +4.70] / [+0.85, +4.08] |
| SPY iron | i | 1,046 | **+4.68**, +17.20 | +4.08, +14.80 | 70.1 / 69.0 | [+3.38, +6.49] / [+2.77, +5.88] |
| SPY put | i | 1,046 | **+2.00**, +6.27 | +1.41, +3.85 | 61.7 / 60.7 | [+0.43, +3.98] / [−0.16, +3.37] |
| all names | i | 6,287 | **+3.98**, +13.62 | +3.38, +11.21 | 67.0 / 66.0 | [+2.65, +6.02] / [+2.05, +5.40] |
| QQQ call | ii | 877 | **+2.88**, +5.14 | +2.20, +2.72 | 58.0 / 57.5 | [+0.52, +5.22] / [−0.17, +4.54] |
| QQQ iron | ii | 877 | **+6.41**, +18.09 | +5.71, +15.69 | 63.7 / 62.7 | [+4.18, +8.62] / [+3.47, +7.94] |
| QQQ put | ii | 877 | **+2.36**, +3.23 | +1.68, +0.81 | 57.2 / 56.4 | [−0.03, +4.65] / [−0.72, +3.99] |
| SPY call | ii | 880 | **+4.31**, +13.94 | +3.65, +11.52 | 62.5 / 61.6 | [+2.58, +6.09] / [+1.91, +5.44] |
| SPY iron | ii | 880 | **+5.78**, +19.11 | +5.12, +16.71 | 65.0 / 64.2 | [+4.08, +7.55] / [+3.41, +6.91] |
| SPY put | ii | 880 | **+4.02**, +12.75 | +3.37, +10.33 | 62.0 / 60.8 | [+2.30, +5.86] / [+1.63, +5.21] |
| all names | ii | 5,271 | **+4.29**, +12.05 | +3.62, +9.64 | 61.4 / 60.5 | [+2.45, +6.13] / [+1.77, +5.47] |
| QQQ call | iii | 18 | **+24.16**, +69.49 | +23.42, +67.07 | 77.8 / 77.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| QQQ iron | iii | 18 | **+26.03**, +74.63 | +25.29, +72.23 | 77.8 / 77.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| QQQ put | iii | 18 | **+24.49**, +70.49 | +23.75, +68.07 | 77.8 / 77.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY call | iii | 18 | **+10.27**, +35.49 | +9.63, +33.07 | 61.1 / 61.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY iron | iii | 18 | **+10.47**, +36.02 | +9.83, +33.62 | 61.1 / 61.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY put | iii | 18 | **+10.36**, +35.71 | +9.72, +33.29 | 61.1 / 61.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | iii | 108 | **+17.63**, +53.64 | +16.94, +51.22 | 69.4 / 69.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- i: held to settlement (official close) 100.0%
- ii: held to settlement (official close) 100.0%
- iii: held to settlement (official close) 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | QQQ call | 65 | 67.7 | +2.76 | +6.17 | +401 |
| 2023 | QQQ call | 495 | 68.7 | +4.34 | +16.49 | +8,162 |
| 2024 | QQQ call | 489 | 66.9 | +4.46 | +12.95 | +6,332 |
| 2025 | QQQ call | 493 | 57.6 | +2.24 | +3.37 | +1,663 |
| 2026 | QQQ call | 402 | 59.5 | +4.62 | +10.19 | +4,098 |
| 2022 | QQQ iron | 65 | 72.3 | +4.59 | +13.69 | +890 |
| 2023 | QQQ iron | 495 | 70.5 | +5.57 | +21.23 | +10,507 |
| 2024 | QQQ iron | 489 | 69.9 | +6.64 | +21.26 | +10,397 |
| 2025 | QQQ iron | 493 | 64.9 | +6.15 | +17.93 | +8,842 |
| 2026 | QQQ iron | 402 | 62.9 | +7.61 | +20.80 | +8,363 |
| 2022 | QQQ put | 65 | 69.2 | +2.60 | +5.50 | +357 |
| 2023 | QQQ put | 495 | 68.1 | +4.10 | +15.53 | +7,689 |
| 2024 | QQQ put | 491 | 65.4 | +4.20 | +12.34 | +6,060 |
| 2025 | QQQ put | 493 | 55.4 | +1.43 | +0.36 | +180 |
| 2026 | QQQ put | 402 | 60.4 | +4.49 | +9.75 | +3,920 |
| 2022 | SPY call | 65 | 69.2 | +6.33 | +19.73 | +1,282 |
| 2023 | SPY call | 495 | 67.9 | +3.26 | +12.65 | +6,262 |
| 2024 | SPY call | 486 | 61.9 | +1.94 | +5.64 | +2,743 |
| 2025 | SPY call | 493 | 61.1 | +2.89 | +9.42 | +4,646 |
| 2026 | SPY call | 405 | 64.2 | +6.30 | +20.40 | +8,264 |
| 2022 | SPY iron | 65 | 72.3 | +7.71 | +24.26 | +1,577 |
| 2023 | SPY iron | 495 | 71.9 | +4.65 | +18.17 | +8,993 |
| 2024 | SPY iron | 486 | 67.9 | +4.31 | +15.26 | +7,416 |
| 2025 | SPY iron | 493 | 62.5 | +4.32 | +14.32 | +7,060 |
| 2026 | SPY iron | 405 | 67.9 | +7.77 | +25.69 | +10,405 |
| 2022 | SPY put | 65 | 70.8 | +6.22 | +19.23 | +1,250 |
| 2023 | SPY put | 495 | 65.1 | +2.73 | +10.33 | +5,115 |
| 2024 | SPY put | 486 | 57.0 | +0.70 | +0.39 | +191 |
| 2025 | SPY put | 493 | 60.0 | +2.48 | +7.72 | +3,805 |
| 2026 | SPY put | 405 | 64.4 | +6.18 | +19.89 | +8,057 |
| 2022 | all names | 390 | 70.3 | +5.04 | +14.76 | +5,758 |
| 2023 | all names | 2,970 | 68.7 | +4.11 | +15.73 | +46,730 |
| 2024 | all names | 2,927 | 64.8 | +3.71 | +11.32 | +33,139 |
| 2025 | all names | 2,958 | 60.2 | +3.25 | +8.86 | +26,194 |
| 2026 | all names | 2,421 | 63.2 | +6.17 | +17.81 | +43,106 |

![](charts/s26b.png)

**Amendments, deviations and integrity checks.** As 26a.

**What it showed.** Positive historically, but on the period that chose it, and not operationally clean.

## #26c Paper tracker: condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00)

**Folder:** `scripts/paper_tracker.py; research_notes/Compass phase 3/backtest_replay, backtest_audit, forward_*`. **Commits:** defaults ba117a7, 6826b98 / official-close settlement a4ebe90, 99a3d4e, 16eb3c0 / replay 94af538, 30bb73e; audit 1ca1f0e; forward d7115b6, 2a7bd3b; candidate 3 99a3d4e. **Dates:** 2026-10-21 → 22.

**Hypothesis.** The 20-delta SPY condor (from hyp E's D1 read) pays forward.

**Rule.** 13:00, 13:30, 14:00, 14:30, 15:00: SPY 2-wide iron condor at 20 delta, held to the official close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Shorts at the bid, longs at the ask; $0.65 a contract (leg) to open, nothing at expiry.

**Data.** The replay of every stored session through the live tracker's code, settled on the official close (data_recorder/paper_backtest_official, git-ignored, every trade).

**Periods and holdouts.** i-a model training 2022-11 → 2024-06 (in-sample) / i-b decile cuts 2024-07 → 12 / ii selection 2025 → 2026-10-09 / iii forward.

**Pass rule (as pre-registered).** Confirmation: 150 forward sessions for the D1 re-test.

**Verdict.** Positive in ii (+7.67 [+3.87, +10.89]) but set after ii was read; the after-hours rule DROPS it as a hold-to-expiry strategy.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | i-a | 1,823 | 403 / 422 | 77.4 | +16.2, +27.08 | −42.4, −71.43 | +12.9, +22.80 | **+2.94**, +4.82 | [+1.04, +4.52]; [+1.61, +7.40] |
| SPY | i-b | 572 | 125 / 131 | 83.9 | +17.9, +29.46 | −51.9, −84.65 | +14.5, +24.80 | **+6.68**, +11.11 | [+3.50, +10.97]; [+5.84, +18.09] |
| SPY | ii | 2,090 | 440 / 457 | 82.8 | +18.2, +29.85 | −52.1, −84.97 | +14.8, +25.80 | **+6.11**, +10.07 | [+3.87, +8.01]; [+6.37, +13.18] |
| SPY | iii | 41 | 9 / 9 | 95.1 | +17.6, +29.34 | −26.2, −43.70 | +17.5, +29.80 | **+15.43**, +25.77 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | i-a | +71.80, +56.1%, 2022-12-14, SPY 13:30 −C411/−C413/−P397/−P395 | −189.20, −100.1%, 2023-07-07, SPY 13:30 −C444/−C446/−P441/−P439 | 1.30 | 1,349 | 68 | 15% |
| SPY | i-b | +65.80, +49.1%, 2024-09-18, SPY 13:00 −C569/−C571/−P557/−P555 | −183.20, −100.1%, 2024-07-12, SPY 15:00 −C564/−C566/−P562/−P560 | 1.82 | 1,517 | 20 | 21% |
| SPY | ii | +62.80, +45.8%, 2025-04-10, SPY 13:30 −C530/−C532/−P509/−P507 | −187.20, −100.1%, 2026-04-13, SPY 14:00 −C684/−C686/−P680/−P678 | 1.69 | 2,139 | 34 | 7% |
| SPY | iii | +43.80, +28.1%, 2026-10-22, SPY 13:00 −C767/−C769/−P761/−P759 | −45.20, −27.2%, 2026-10-15, SPY 14:30 −C771/−C773/−P768/−P766 | 13.09 | 0 | 0 | 72% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.20). The study's fees are given beside them below. Re-pricing: exact (4,526 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | i-a | 1,823 | **+2.94**, +4.82 | +1.53, +2.42 | 77.4 / 76.9 | [+1.04, +4.52] / [−0.37, +3.11] |
| SPY | i-b | 572 | **+6.68**, +11.11 | +5.25, +8.71 | 83.9 / 83.9 | [+3.50, +10.97] / [+2.06, +9.54] |
| SPY | ii | 2,090 | **+6.11**, +10.07 | +4.68, +7.67 | 82.8 / 82.1 | [+3.87, +8.01] / [+2.43, +6.59] |
| SPY | iii | 41 | **+15.43**, +25.77 | +14.02, +23.38 | 95.1 / 95.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- i-a: held to settlement (official close) 100.0%
- i-b: held to settlement (official close) 100.0%
- ii: held to settlement (official close) 100.0%
- iii: held to settlement (official close) 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPY | 163 | 77.9 | +0.37 | +0.14 | +22 |
| 2023 | SPY | 1,102 | 76.7 | +2.84 | +4.73 | +5,212 |
| 2024 | SPY | 1,130 | 81.3 | +5.30 | +8.76 | +9,901 |
| 2025 | SPY | 1,156 | 82.7 | +6.70 | +10.86 | +12,557 |
| 2026 | SPY | 975 | 83.4 | +5.81 | +9.79 | +9,547 |

![](charts/s26c.png)

**Amendments, deviations and integrity checks.** As 26a.

**What it showed.** Positive on the period it was chosen on.

## #26d Paper tracker: fly_spxw (SPX ±5 / ±25 flies)

**Folder:** `scripts/paper_tracker.py; research_notes/Compass phase 3/backtest_replay, backtest_audit, forward_*`. **Commits:** scripts/paper_backtest.py (off unless listed). **Dates:** 2026-10-21.

**Hypothesis.** The SPXW analogue of fly5.

**Rule.** 15:00 and 15:30 SPXW ±5 and ±25 flies.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC)

**Data.** One week, 2026-10-05 → 09.

**Periods and holdouts.** —

**Pass rule (as pre-registered).** —

**Verdict.** Run only as a one-week sanity run outside the repository; replaced by the pre-registered SPXW test (#28).

**Metrics.** not available — a one-week sanity run outside the repository; no rows were kept.

**Amendments, deviations and integrity checks.** —

**What it showed.** No result.

## #27a After-hours exercise study: fly5 iron ±5, case (b) the post-market decision

**Folder:** `research_notes/Compass phase 3/backtest_audit/AFTERHOURS.md`. **Commits:** owner's rule fixed before the read / — / 633fbff. **Dates:** 2026-10-22.

**Hypothesis.** The SPY/QQQ hold-to-expiry candidates survive after-hours exercise.

**Rule.** fly5 iron held to expiry; case (b): the counterparty exercises on the 17:30 post-market price, the position re-marked at the next 09:30 open.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As #26 plus the exercise/assignment fee.

**Data.** SPY/QQQ, period ii (2025-10-13 → 2026-10-09 overlap) and iii (2026-10-12 → 21).

**Periods and holdouts.** ii / iii (7 sessions with a next open).

**Pass rule (as pre-registered).** "If a candidate's mean under (b) is ≤ 0 or its block-20 interval includes zero, drop it as a SPY/QQQ hold-to-expiry strategy."

**Verdict.** DROP: (b) +22.52 a trade [−20.07, +52.89] in ii.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | ii | 492 | 246 / 258 | 55.7 | +119.6, +393.62 | −131.8, −428.94 | +16.4, +61.30 | **+8.20**, +29.15 | [−7.17, +18.66]; [−21.23, +63.21] |
| SPY | ii | 495 | 248 / 258 | 56.0 | +72.4, +258.78 | −80.1, −285.08 | +9.2, +37.36 | **+5.26**, +19.26 | [−6.09, +14.29]; [−18.43, +50.48] |
| all names | ii | 987 | 248 / 258 | 55.8 | +95.9, +325.83 | −106.0, −357.01 | +11.1, +43.36 | **+6.72**, +24.19 | [−5.36, +15.74]; [−17.22, +53.53] |
| QQQ | iii | 14 | 7 / 7 | 42.9 | +142.6, +506.30 | −156.5, −511.84 | −51.5, −168.96 | **−28.36**, −75.49 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY | iii | 14 | 7 / 7 | 42.9 | +56.5, +226.86 | −49.2, −177.93 | −27.7, −107.20 | **−3.94**, −4.45 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | iii | 28 | 7 / 7 | 42.9 | +99.5, +366.58 | −102.9, −344.88 | −27.7, −107.20 | **−16.15**, −39.97 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | ii | +2,198.80, +672.4%, 2026-06-22, QQQ 15:00 [["C", 736.0, "short", 1], ["P", 736.0, "short", 1], ["P", 731.0, "long", 1], ["C", 741.0, "long", 1]] | −2,193.20, −681.1%, 2026-04-07, QQQ 15:30 [["C", 585.0, "short", 1], ["P", 585.0, "short", 1], ["P", 580.0, "long", 1], ["C", 590.0, "long", 1]] | 1.15 | 10,269 | 68 | 88% |
| SPY | ii | +1,155.80, +318.4%, 2026-06-22, SPY 15:00 [["C", 744.0, "short", 1], ["P", 744.0, "short", 1], ["P", 739.0, "long", 1], ["C", 749.0, "long", 1]] | −1,759.20, −549.8%, 2026-04-07, SPY 15:30 [["C", 657.0, "short", 1], ["P", 657.0, "short", 1], ["P", 652.0, "long", 1], ["C", 662.0, "long", 1]] | 1.15 | 7,172 | 88 | 83% |
| all names | ii | +2,198.80, +672.4%, 2026-06-22, QQQ 15:00 [["C", 736.0, "short", 1], ["P", 736.0, "short", 1], ["P", 731.0, "long", 1], ["C", 741.0, "long", 1]] | −2,193.20, −681.1%, 2026-04-07, QQQ 15:30 [["C", 585.0, "short", 1], ["P", 585.0, "short", 1], ["P", 580.0, "long", 1], ["C", 590.0, "long", 1]] | 1.15 | 15,447 | 73 | 83% |
| QQQ | iii | +1,067.29, +365.5%, 2026-10-16, QQQ 15:30 [["C", 711.0, "short", 1], ["P", 711.0, "short", 1], ["P", 706.0, "long", 1], ["C", 716.0, "long", 1]] | −874.71, −266.7%, 2026-10-14, QQQ 15:30 [["C", 729.0, "short", 1], ["P", 729.0, "short", 1], ["P", 724.0, "long", 1], ["C", 734.0, "long", 1]] | 0.74 | 2,203 | 5 | total ≤ 0 (best 5 days +1,170; without them −2,227) |
| SPY | iii | +375.80, +87.0%, 2026-10-13, SPY 15:00 [["C", 778.0, "short", 1], ["P", 778.0, "short", 1], ["P", 773.0, "long", 1], ["C", 783.0, "long", 1]] | −340.20, −107.3%, 2026-10-16, SPY 15:00 [["C", 762.0, "short", 1], ["P", 762.0, "short", 1], ["P", 757.0, "long", 1], ["C", 767.0, "long", 1]] | 0.96 | 1,171 | 3 | total ≤ 0 (best 5 days +863; without them −925) |
| all names | iii | +1,067.29, +365.5%, 2026-10-16, QQQ 15:30 [["C", 711.0, "short", 1], ["P", 711.0, "short", 1], ["P", 706.0, "long", 1], ["C", 716.0, "long", 1]] | −874.71, −266.7%, 2026-10-14, QQQ 15:30 [["C", 729.0, "short", 1], ["P", 729.0, "short", 1], ["P", 724.0, "long", 1], ["C", 734.0, "long", 1]] | 0.80 | 3,063 | 5 | total ≤ 0 (best 5 days +1,259; without them −2,378) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.92). The study's fees are given beside them below. Re-pricing: exact (1,015 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | ii | 492 | **+8.20**, +29.15 | +7.69, +27.42 | 55.7 / 55.5 | [−7.17, +18.66] / [−7.67, +18.13] |
| SPY | ii | 495 | **+5.26**, +19.26 | +4.82, +17.65 | 56.0 / 56.0 | [−6.09, +14.29] / [−6.54, +13.87] |
| all names | ii | 987 | **+6.72**, +24.19 | +6.25, +22.52 | 55.8 / 55.7 | [−5.36, +15.74] / [−5.84, +15.27] |
| QQQ | iii | 14 | **−28.36**, −75.49 | −28.86, −77.24 | 42.9 / 42.9 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY | iii | 14 | **−3.94**, −4.45 | −4.44, −6.39 | 42.9 / 42.9 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | iii | 28 | **−16.15**, −39.97 | −16.65, −41.81 | 42.9 / 42.9 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- ii: held; after-hours decision (b) on the 17:30 price 100.0%
- iii: held; after-hours decision (b) on the 17:30 price 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | QQQ | 108 | 57.4 | +11.35 | +57.33 | +6,191 |
| 2026 | QQQ | 398 | 54.8 | +6.05 | +17.83 | +7,095 |
| 2025 | SPY | 108 | 59.3 | +5.69 | +33.24 | +3,590 |
| 2026 | SPY | 401 | 54.6 | +4.82 | +14.67 | +5,882 |
| 2025 | all names | 216 | 58.3 | +8.52 | +45.28 | +9,781 |
| 2026 | all names | 799 | 54.7 | +5.43 | +16.24 | +12,977 |

![](charts/s27a.png)

**Amendments, deviations and integrity checks.** 16 name-sessions of UW 1-minute post-market bars fetched once with the owner's leave; SPY 2025-04-09 official close flagged.

**What it showed.** Counting after-hours exercise, the iron fly's mean is inside the noise.

## #27b After-hours exercise study: condor_d20, case (b)

**Folder:** `research_notes/Compass phase 3/backtest_audit/AFTERHOURS.md`. **Commits:** — / — / 633fbff. **Dates:** 2026-10-22.

**Hypothesis.** As 27a.

**Rule.** condor_d20 held to expiry, case (b).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As 27a.

**Data.** As 27a.

**Periods and holdouts.** ii / iii.

**Pass rule (as pre-registered).** As 27a.

**Verdict.** DROP: (b) +3.84 [−19.94, +22.74] in ii; iii undecided (7 sessions).

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPY | ii | 1,176 | 247 / 258 | 83.3 | +38.3, +62.32 | −169.4, −275.19 | +16.2, +27.80 | **+3.70**, +6.07 | [−11.28, +15.87]; [−17.97, +25.12] |
| SPY | iii | 36 | 8 / 8 | 94.4 | +31.6, +54.28 | −84.0, −143.70 | +17.5, +29.80 | **+25.14**, +43.28 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPY | ii | +868.20, +598.8%, 2026-09-16, SPY 14:00 [["C", 765.0, "short", 1], ["C", 767.0, "long", 1], ["P", 755.0, "short", 1], ["P", 753.0, "long", 1]] | −1,796.20, −1,144.1%, 2026-04-07, SPY 14:30 [["C", 658.0, "short", 1], ["C", 660.0, "long", 1], ["P", 654.0, "short", 1], ["P", 652.0, "long", 1]] | 1.13 | 11,417 | 130 | 156% |
| SPY | iii | +354.19, +212.1%, 2026-10-16, SPY 13:00 [["C", 769.0, "short", 1], ["C", 771.0, "long", 1], ["P", 764.0, "short", 1], ["P", 762.0, "long", 1]] | −190.20, −114.6%, 2026-10-15, SPY 14:30 [["C", 771.0, "short", 1], ["C", 773.0, "long", 1], ["P", 768.0, "short", 1], ["P", 766.0, "long", 1]] | 6.42 | 59 | 1 | 105% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.60 a trade) and Robinhood's charged instead (mean $0.38). The study's fees are given beside them below. Re-pricing: exact (1,212 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPY | ii | 1,176 | **+3.70**, +6.07 | +2.37, +3.84 | 83.3 / 83.3 | [−11.28, +15.87] / [−12.63, +14.57] |
| SPY | iii | 36 | **+25.14**, +43.28 | +23.77, +40.93 | 94.4 / 94.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- ii: held; after-hours decision (b) on the 17:30 price 100.0%
- iii: held; after-hours decision (b) on the 17:30 price 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | SPY | 242 | 84.3 | +2.92 | +5.92 | +1,432 |
| 2026 | SPY | 970 | 83.5 | +4.68 | +7.48 | +7,258 |

![](charts/s27b.png)

**Amendments, deviations and integrity checks.** As 27a.

**What it showed.** Inside the noise once exercise is counted.

## #28a SPXW analogue A: iron fly ±5×ratio at 15:00 and 15:30 (fly5 iron)

**Folder:** `research_notes/Compass phase 3/spxw_prereg`. **Commits:** 2820bb4 / — / 6bb230e. **Dates:** 2026-10-22.

**Hypothesis.** The ETF fly5 iron result transfers to cash-settled SPXW.

**Rule.** SPXW iron fly, wings ±5 × the SPX/SPY ratio, 15:00 and 15:30, package fill at the NBBO rounded against us to $0.05, held to cash settlement on the official SPX close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); about $4.93 to open a four-leg structure.

**Data.** SPXW 1,105 full sessions 2022-05-13 → 2026-10-21.

**Periods and holdouts.** development 2022-05 → 2024 / selection 2025 → 2026-10-09 / forward 8 sessions.

**Pass rule (as pre-registered).** (1) selection mean > 0 and block-20 lower bound > 0; (2) selection mean > 0 at +$0.05 package stress; (3) development mean > 0.

**Verdict.** FAIL: selection −$39.64 a session [−173.06, +87.48].

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | development | 1,312 | 656 / 683 | 62.6 | +12.7, +488.32 | −18.3, −708.36 | +4.6, +195.16 | **+1.08**, +40.48 | [−0.12, +2.36]; [−3.76, +88.63] |
| SPXW | selection | 882 | 441 / 457 | 58.8 | +15.0, +535.02 | −22.4, −811.67 | +3.5, +150.16 | **−0.40**, −19.23 | [−2.27, +1.43]; [−86.71, +46.19] |
| SPXW | forward | 16 | 8 / 8 | 62.5 | +10.9, +433.56 | −7.7, −324.67 | +1.4, +54.66 | **+3.92**, +149.22 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | development | +2,463.48, +123.2%, 2022-12-14, None | −4,034.34, −100.1%, 2024-05-31, None | 1.15 | 29,822 | 272 | 28% |
| SPXW | selection | +2,569.48, +114.5%, 2026-09-16, None | −3,549.34, −100.1%, 2026-03-09, None | 0.94 | 39,040 | 422 | total ≤ 0 (best 5 days +15,024; without them −31,986) |
| SPXW | forward | +921.66, +25.4%, 2026-10-16, None | −746.34, −17.3%, 2026-10-19, None | 2.23 | 813 | 2 | 141% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $4.93 a trade) and Robinhood's charged instead (mean $4.35). The study's fees are given beside them below. Re-pricing: exact (2,210 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | development | 1,312 | **+1.08**, +40.48 | +1.07, +39.89 | 62.6 / 62.6 | [−0.12, +2.36] / [−0.13, +2.35] |
| SPXW | selection | 882 | **−0.40**, −19.23 | −0.41, −19.82 | 58.8 / 58.8 | [−2.27, +1.43] / [−2.28, +1.41] |
| SPXW | forward | 16 | **+3.92**, +149.22 | +3.91, +148.63 | 62.5 / 62.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development: held to cash settlement (official SPX close) 100.0%
- selection: held to cash settlement (official SPX close) 100.0%
- forward: held to cash settlement (official SPX close) 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 318 | 63.5 | +3.79 | +133.85 | +42,565 |
| 2023 | SPXW | 496 | 64.5 | +1.29 | +54.21 | +26,888 |
| 2024 | SPXW | 498 | 60.0 | −0.85 | −32.82 | −16,344 |
| 2025 | SPXW | 494 | 58.9 | −0.88 | −38.33 | −18,934 |
| 2026 | SPXW | 404 | 58.9 | +0.36 | +10.79 | +4,360 |

![](charts/s28a.png)

**Amendments, deviations and integrity checks.** The package rule cost nothing: the summed leg NBBO is always a multiple of $0.05.

**What it showed.** SPXW did not reproduce the ETF fly.

## #28b SPXW analogue B: 20-delta iron condor, wings 2×ratio, 13:00–15:00 (condor_d20)

**Folder:** `research_notes/Compass phase 3/spxw_prereg`. **Commits:** 2820bb4 / — / 6bb230e. **Dates:** 2026-10-22.

**Hypothesis.** As 28a for condor_d20.

**Rule.** SPXW 20-delta iron condor, wings 2 × ratio, five entries 13:00–15:00, package fill, held to cash settlement.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC)

**Data.** As 28a.

**Periods and holdouts.** As 28a.

**Pass rule (as pre-registered).** As 28a.

**Verdict.** FAIL: selection +$120.76 a session [−95.03, +286.78] — positive but the interval crosses zero.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | development | 3,193 | 656 / 683 | 74.4 | +16.9, +281.25 | −47.0, −784.69 | +13.1, +230.66 | **+0.52**, +7.84 | [−1.29, +2.21]; [−21.92, +35.82] |
| SPXW | selection | 2,157 | 441 / 457 | 76.8 | +17.5, +289.67 | −51.4, −848.63 | +13.4, +235.66 | **+1.53**, +25.28 | [−1.08, +3.50]; [−18.27, +58.23] |
| SPXW | forward | 38 | 8 / 8 | 89.5 | +15.4, +262.42 | −15.0, −260.32 | +14.4, +250.66 | **+12.23**, +207.39 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | development | +705.48, +54.7%, 2022-12-14, SPXW 13:00 3945.0/3965.0P 4105.0/4125.0C | −1,879.16, −100.2%, 2023-12-20, SPXW 13:30 4745.0/4765.0P 4785.0/4805.0C | 1.04 | 55,785 | 560 | 51% |
| SPXW | selection | +605.48, +43.6%, 2026-07-29, SPXW 13:00 7290.0/7310.0P 7430.0/7450.0C | −1,849.34, −100.2%, 2026-04-13, SPXW 14:30 6815.0/6835.0P 6860.0/6880.0C | 1.13 | 34,778 | 171 | 24% |
| SPXW | forward | +435.48, +27.9%, 2026-10-16, SPXW 13:30 7620.0/7640.0P 7695.0/7715.0C | −645.34, −37.2%, 2026-10-15, SPXW 14:30 7685.0/7705.0P 7735.0/7755.0C | 8.57 | 0 | 0 | 80% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $4.95 a trade) and Robinhood's charged instead (mean $4.36). The study's fees are given beside them below. Re-pricing: exact (5,388 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | development | 3,193 | **+0.52**, +7.84 | +0.49, +7.25 | 74.4 / 74.4 | [−1.29, +2.21] / [−1.33, +2.18] |
| SPXW | selection | 2,157 | **+1.53**, +25.28 | +1.49, +24.69 | 76.8 / 76.8 | [−1.08, +3.50] / [−1.12, +3.46] |
| SPXW | forward | 38 | **+12.23**, +207.39 | +12.19, +206.80 | 89.5 / 89.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- development: held to cash settlement (official SPX close) 100.0%
- selection: held to cash settlement (official SPX close) 100.0%
- forward: held to cash settlement (official SPX close) 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 794 | 73.8 | +1.34 | +20.24 | +16,067 |
| 2023 | SPXW | 1,190 | 73.4 | −0.23 | −3.36 | −3,994 |
| 2024 | SPXW | 1,209 | 75.6 | +0.73 | +10.72 | +12,955 |
| 2025 | SPXW | 1,203 | 77.1 | +1.83 | +28.80 | +34,645 |
| 2026 | SPXW | 992 | 76.9 | +1.57 | +27.98 | +27,761 |

![](charts/s28b.png)

**Amendments, deviations and integrity checks.** As 28a; the ETF−SPXW late-day extrinsic gap measured beside it.

**What it showed.** Positive in both periods, inside the noise.

## #29a Picker (GeorgeFi rule), PRIMARY: opening-range fade, stop 0.68, target 1.25, 5-minute stop, flat 15:58

**Folder:** `research_notes/Compass phase 3/picker_prereg`. **Commits:** c502122 / — / 1e10053. **Dates:** 2026-10-22.

**Hypothesis.** The opening-range sweep fade the GeorgeFi cards describe makes money as written.

**Rule.** Opening range = the 09:30–09:59 bars; 10:00–11:59: the first bar with high ≥ ORH × (1 + 2 bp) and close < ORH → PUT (the low side → CALL); buy the nearest OTM 0DTE contract at the ask one bar later; exits: stop at 0.68 × ask, target 1.25 × ask (resting), out at 5 minutes unless +6% reached, flat 15:58.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData); a target at its resting limit

**Data.** SPY, QQQ (846 sessions), IWM (484), SPXW (972), 2022 → 2026-10-21, the 134 GeorgeFi card dates excluded.

**Periods and holdouts.** The whole tested span (verdict) and the never-read line 2026-10-14 → 21 (no verdict). The 2022–2026 NBBO had been read by the engine audit for the same universe (disclosed).

**Pass rule (as pre-registered).** "Pass: mean > 0 with the interval clear of zero on each name, judged only on the span with the excluded dates removed" (PRIMARY only; mean % of premium, 20-session block interval; every name must pass).

**Verdict.** FAIL on every name: SPY −6.28% [−8.18, −4.41], QQQ −5.21%, IWM −9.47%, SPXW −4.96%.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | whole span (card dates out) | 438 | 394 / 634 | 36.1 | +23.8, +13.92 | −23.7, −13.18 | −10.6, −5.10 | **−6.54**, −3.41 | [−9.08, −4.31]; [−5.25, −1.95] |
| QQQ | whole span (card dates out) | 814 | 698 / 1,005 | 37.3 | +22.8, +28.93 | −20.2, −26.03 | −7.3, −7.60 | **−4.12**, −5.50 | [−5.86, −2.43]; [−8.41, −2.71] |
| SPXW | whole span (card dates out) | 902 | 765 / 1,135 | 36.9 | +21.9, +269.51 | −20.7, −252.86 | −7.9, −82.26 | **−5.00**, −60.01 | [−6.67, −3.48]; [−84.67, −36.93] |
| SPY | whole span (card dates out) | 771 | 660 / 1,005 | 36.2 | +22.0, +24.93 | −20.2, −22.79 | −7.7, −6.10 | **−4.97**, −5.52 | [−6.71, −3.28]; [−8.49, −2.91] |
| all names | whole span (card dates out) | 2,925 | 898 / 1,135 | 36.7 | +22.4, +100.28 | −20.9, −92.95 | −7.8, −9.10 | **−4.98**, −22.00 | [−6.17, −3.69]; [−30.20, −14.23] |
| QQQ | never-read 2026-10-14→21 | 6 | 5 / 6 | 66.7 | +25.1, +50.40 | −10.0, −19.10 | +25.0, +45.90 | **+13.42**, +27.23 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPXW | never-read 2026-10-14→21 | 6 | 5 / 6 | 50.0 | +24.9, +291.07 | −12.5, −145.59 | +10.1, +87.74 | **+6.24**, +72.74 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 6 | 5 / 6 | 50.0 | +25.4, +26.57 | −11.5, −13.10 | +10.0, +5.90 | **+6.98**, +6.73 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 18 | 5 / 6 | 55.6 | +25.2, +115.45 | −11.5, −64.29 | +24.8, +24.40 | **+8.88**, +35.57 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IWM | whole span (verdict) | 438 | 394 / 634 | 36.1 | +23.8, +13.92 | −23.7, −13.18 | −10.6, −5.10 | **−6.54**, −3.41 | [−9.08, −4.31]; [−5.25, −1.95] |
| QQQ | whole span (verdict) | 820 | 703 / 1,018 | 37.6 | +22.8, +29.20 | −20.1, −26.00 | −7.1, −7.10 | **−3.99**, −5.27 | [−5.98, −2.44]; [−8.47, −2.91] |
| SPXW | whole span (verdict) | 908 | 770 / 1,148 | 37.0 | +21.9, +269.70 | −20.7, −252.30 | −7.8, −77.26 | **−4.93**, −59.13 | [−6.70, −3.46]; [−85.43, −36.69] |
| SPY | whole span (verdict) | 777 | 665 / 1,018 | 36.3 | +22.0, +24.95 | −20.2, −22.73 | −7.7, −6.10 | **−4.87**, −5.42 | [−6.71, −3.20]; [−8.52, −2.98] |
| all names | whole span (verdict) | 2,943 | 903 / 1,148 | 36.8 | +22.5, +100.42 | −20.8, −92.83 | −7.8, −9.10 | **−4.89**, −21.65 | [−6.21, −3.68]; [−30.26, −13.55] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | whole span (card dates out) | +60.90, +25.1%, 2025-04-09, IWM 2025-04-09 176.0P | −119.10, −57.8%, 2025-04-07, IWM 2025-04-07 176.0P | 0.60 | 1,533 | 624 | total ≤ 0 (best 5 days +292; without them −1,784) |
| QQQ | whole span (card dates out) | +141.89, +25.1%, 2025-04-09, QQQ 2025-04-09 423.0P | −299.10, −51.1%, 2025-04-07, QQQ 2025-04-07 416.0P | 0.66 | 4,558 | 990 | total ≤ 0 (best 5 days +691; without them −5,172) |
| SPXW | whole span (card dates out) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −2,952.26, −45.6%, 2025-04-07, SPXW 2025-04-07 4970.0P | 0.62 | 54,455 | 1,135 | total ≤ 0 (best 5 days +6,120; without them −60,249) |
| SPY | whole span (card dates out) | +128.89, +25.1%, 2025-04-09, SPY 2025-04-09 495.0C | −294.10, −45.2%, 2025-04-07, SPY 2025-04-07 495.0P | 0.62 | 4,290 | 1,005 | total ≤ 0 (best 5 days +572; without them −4,828) |
| all names | whole span (card dates out) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −2,952.26, −45.6%, 2025-04-07, SPXW 2025-04-07 4970.0P | 0.63 | 64,706 | 1,135 | total ≤ 0 (best 5 days +7,330; without them −71,688) |
| QQQ | never-read 2026-10-14→21 | +54.90, +25.1%, 2026-10-15, QQQ 2026-10-15 720.0P | −34.10, −17.9%, 2026-10-19, QQQ 2026-10-19 720.0P | 5.28 | 38 | 2 | 100% |
| SPXW | never-read 2026-10-14→21 | +347.74, +25.0%, 2026-10-19, SPXW 2026-10-19 7690.0C | −222.26, −17.8%, 2026-10-14, SPXW 2026-10-14 7760.0C | 2.00 | 295 | 3 | 100% |
| SPY | never-read 2026-10-14→21 | +30.90, +24.9%, 2026-10-21, SPY 2026-10-21 770.0C | −17.10, −17.8%, 2026-10-14, SPY 2026-10-14 774.0C | 2.03 | 25 | 3 | 100% |
| all names | never-read 2026-10-14→21 | +347.74, +25.0%, 2026-10-19, SPXW 2026-10-19 7690.0C | −222.26, −17.8%, 2026-10-14, SPXW 2026-10-14 7760.0C | 2.24 | 218 | 2 | 100% |
| IWM | whole span (verdict) | +60.90, +25.1%, 2025-04-09, IWM 2025-04-09 176.0P | −119.10, −57.8%, 2025-04-07, IWM 2025-04-07 176.0P | 0.60 | 1,533 | 624 | total ≤ 0 (best 5 days +292; without them −1,784) |
| QQQ | whole span (verdict) | +141.89, +25.1%, 2025-04-09, QQQ 2025-04-09 423.0P | −299.10, −51.1%, 2025-04-07, QQQ 2025-04-07 416.0P | 0.68 | 4,558 | 1,003 | total ≤ 0 (best 5 days +691; without them −5,009) |
| SPXW | whole span (verdict) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −2,952.26, −45.6%, 2025-04-07, SPXW 2025-04-07 4970.0P | 0.63 | 54,455 | 1,148 | total ≤ 0 (best 5 days +6,120; without them −59,812) |
| SPY | whole span (verdict) | +128.89, +25.1%, 2025-04-09, SPY 2025-04-09 495.0C | −294.10, −45.2%, 2025-04-07, SPY 2025-04-07 495.0P | 0.63 | 4,290 | 1,018 | total ≤ 0 (best 5 days +572; without them −4,787) |
| all names | whole span (verdict) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −2,952.26, −45.6%, 2025-04-07, SPXW 2025-04-07 4970.0P | 0.63 | 64,706 | 1,148 | total ≤ 0 (best 5 days +7,330; without them −71,048) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.74 a trade) and Robinhood's charged instead (mean $0.77). The study's fees are given beside them below. Re-pricing: exact (2,943 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | whole span (card dates out) | 438 | **−6.54**, −3.41 | −9.47, −4.68 | 36.1 / 34.9 | [−9.08, −4.31] / [−12.02, −7.26] |
| QQQ | whole span (card dates out) | 814 | **−4.12**, −5.50 | −5.34, −6.78 | 37.3 / 36.4 | [−5.86, −2.43] / [−7.05, −3.69] |
| SPXW | whole span (card dates out) | 902 | **−5.00**, −60.01 | −5.03, −60.30 | 36.9 / 36.9 | [−6.67, −3.48] / [−6.69, −3.51] |
| SPY | whole span (card dates out) | 771 | **−4.97**, −5.52 | −6.37, −6.79 | 36.2 / 34.4 | [−6.71, −3.28] / [−8.12, −4.67] |
| all names | whole span (card dates out) | 2,925 | **−4.98**, −22.00 | −6.14, −22.97 | 36.7 / 35.8 | [−6.17, −3.69] / [−7.36, −4.81] |
| QQQ | never-read 2026-10-14→21 | 6 | **+13.42**, +27.23 | +12.77, +25.96 | 66.7 / 66.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPXW | never-read 2026-10-14→21 | 6 | **+6.24**, +72.74 | +6.21, +72.44 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 6 | **+6.98**, +6.73 | +5.82, +5.46 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 18 | **+8.88**, +35.57 | +8.27, +34.62 | 55.6 / 55.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IWM | whole span (verdict) | 438 | **−6.54**, −3.41 | −9.47, −4.68 | 36.1 / 34.9 | [−9.08, −4.31] / [−12.02, −7.26] |
| QQQ | whole span (verdict) | 820 | **−3.99**, −5.27 | −5.21, −6.54 | 37.6 / 36.6 | [−5.98, −2.44] / [−7.13, −3.67] |
| SPXW | whole span (verdict) | 908 | **−4.93**, −59.13 | −4.96, −59.43 | 37.0 / 37.0 | [−6.70, −3.46] / [−6.73, −3.49] |
| SPY | whole span (verdict) | 777 | **−4.87**, −5.42 | −6.28, −6.70 | 36.3 / 34.5 | [−6.71, −3.20] / [−8.12, −4.61] |
| all names | whole span (verdict) | 2,943 | **−4.89**, −21.65 | −6.05, −22.62 | 36.8 / 35.9 | [−6.21, −3.68] / [−7.41, −4.82] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- whole span (card dates out): time5 47.2%; target 32.1%; stop 20.7%
- never-read 2026-10-14→21: target 55.6%; time5 44.4%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 152 | 30.9 | −8.85 | −4.73 | −719 |
| 2025 | IWM | 232 | 38.8 | −5.08 | −2.29 | −531 |
| 2026 | IWM | 54 | 38.9 | −6.33 | −4.47 | −241 |
| 2022 | QQQ | 30 | 36.7 | −2.88 | −1.93 | −58 |
| 2023 | QQQ | 248 | 39.5 | −2.10 | −1.50 | −371 |
| 2024 | QQQ | 244 | 34.8 | −5.34 | −7.19 | −1,756 |
| 2025 | QQQ | 233 | 39.1 | −3.80 | −6.37 | −1,483 |
| 2026 | QQQ | 65 | 35.4 | −7.39 | −9.99 | −650 |
| 2022 | SPXW | 164 | 40.9 | −3.26 | −41.41 | −6,791 |
| 2023 | SPXW | 240 | 41.7 | −3.14 | −25.47 | −6,113 |
| 2024 | SPXW | 228 | 28.5 | −7.29 | −75.33 | −17,175 |
| 2025 | SPXW | 213 | 36.2 | −5.61 | −88.18 | −18,782 |
| 2026 | SPXW | 63 | 42.9 | −5.23 | −76.71 | −4,832 |
| 2022 | SPY | 33 | 30.3 | −9.79 | −10.31 | −340 |
| 2023 | SPY | 240 | 42.5 | −2.30 | −1.08 | −259 |
| 2024 | SPY | 228 | 28.1 | −7.19 | −6.86 | −1,564 |
| 2025 | SPY | 213 | 36.6 | −4.88 | −7.78 | −1,657 |
| 2026 | SPY | 63 | 44.4 | −3.70 | −6.26 | −394 |
| 2022 | all names | 227 | 38.8 | −4.15 | −31.67 | −7,189 |
| 2023 | all names | 728 | 41.2 | −2.51 | −9.26 | −6,743 |
| 2024 | all names | 852 | 30.6 | −6.98 | −24.90 | −21,214 |
| 2025 | all names | 891 | 37.7 | −4.82 | −25.20 | −22,454 |
| 2026 | all names | 245 | 40.4 | −5.65 | −24.97 | −6,118 |

![](charts/s29a.png)

**Amendments, deviations and integrity checks.** verify_picker.py re-derives trades from the raw files; the flow gate had one session of data (0 trades gated).

**What it showed.** The fade loses 5–9% of premium a trade on every name.

## #29b Picker, SECONDARY: the narrative's +6% breakeven lock and VIX trail

**Folder:** `research_notes/Compass phase 3/picker_prereg`. **Commits:** c502122 / — / 1e10053. **Dates:** 2026-10-22.

**Hypothesis.** The vendor's narrative exits rescue the rule.

**Rule.** Opening range = the 09:30–09:59 bars; 10:00–11:59: the first bar with high ≥ ORH × (1 + 2 bp) and close < ORH → PUT (the low side → CALL); buy the nearest OTM 0DTE contract at the ask one bar later; exits: stop, target, breakeven lock at +6%, VIX-scaled trail, flat 15:58.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData); a target at its resting limit

**Data.** SPY, QQQ (846 sessions), IWM (484), SPXW (972), 2022 → 2026-10-21, the 134 GeorgeFi card dates excluded.

**Periods and holdouts.** The whole tested span (verdict) and the never-read line 2026-10-14 → 21 (no verdict). The 2022–2026 NBBO had been read by the engine audit for the same universe (disclosed).

**Pass rule (as pre-registered).** No verdict of its own (labelled).

**Verdict.** Labelled: SPY −6.29%, QQQ −5.44%, IWM −9.91%, SPXW −5.01%.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | whole span (card dates out) | 438 | 394 / 634 | 38.1 | +18.5, +10.62 | −22.7, −11.83 | −3.9, −2.10 | **−6.98**, −3.27 | [−9.29, −4.90]; [−4.67, −2.02] |
| QQQ | whole span (card dates out) | 814 | 698 / 1,005 | 44.3 | +17.2, +21.82 | −21.6, −26.43 | −0.9, −1.10 | **−4.37**, −5.03 | [−5.68, −2.80]; [−7.18, −2.60] |
| SPXW | whole span (card dates out) | 902 | 765 / 1,135 | 41.4 | +16.6, +210.90 | −20.1, −242.81 | −1.6, −12.26 | **−4.95**, −55.19 | [−6.42, −3.35]; [−72.29, −35.44] |
| SPY | whole span (card dates out) | 771 | 660 / 1,005 | 41.8 | +16.6, +19.26 | −20.2, −22.35 | −1.7, −1.10 | **−4.85**, −4.97 | [−6.60, −3.28]; [−6.93, −3.16] |
| all names | whole span (card dates out) | 2,925 | 898 / 1,135 | 41.8 | +17.0, +77.29 | −20.9, −90.28 | −1.7, −2.10 | **−5.07**, −20.22 | [−6.13, −3.84]; [−25.53, −13.49] |
| QQQ | never-read 2026-10-14→21 | 6 | 5 / 6 | 83.3 | +25.1, +50.30 | −32.5, −62.10 | +25.1, +48.40 | **+15.52**, +31.57 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPXW | never-read 2026-10-14→21 | 6 | 5 / 6 | 33.3 | +25.0, +312.74 | −26.9, −334.76 | −17.7, −187.26 | **−9.57**, −118.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 6 | 5 / 6 | 33.3 | +25.2, +29.90 | −27.3, −34.35 | −18.2, −17.10 | **−9.79**, −12.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 18 | 5 / 6 | 50.0 | +25.1, +104.09 | −27.7, −170.95 | +10.8, +12.90 | **−1.28**, −33.43 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IWM | whole span (verdict) | 438 | 394 / 634 | 38.1 | +18.5, +10.62 | −22.7, −11.83 | −3.9, −2.10 | **−6.98**, −3.27 | [−9.29, −4.90]; [−4.67, −2.02] |
| QQQ | whole span (verdict) | 820 | 703 / 1,018 | 44.6 | +17.3, +22.21 | −21.6, −26.50 | −0.9, −1.10 | **−4.22**, −4.76 | [−5.88, −2.87]; [−7.35, −2.80] |
| SPXW | whole span (verdict) | 908 | 770 / 1,148 | 41.3 | +16.6, +211.45 | −20.2, −243.50 | −1.6, −17.26 | **−4.98**, −55.61 | [−6.55, −3.44]; [−73.51, −36.97] |
| SPY | whole span (verdict) | 777 | 665 / 1,018 | 41.7 | +16.7, +19.33 | −20.3, −22.46 | −1.7, −1.10 | **−4.89**, −5.04 | [−6.62, −3.34]; [−7.10, −3.27] |
| all names | whole span (verdict) | 2,943 | 903 / 1,148 | 41.9 | +17.1, +77.48 | −21.0, −90.71 | −1.7, −2.10 | **−5.04**, −20.30 | [−6.20, −3.90]; [−25.95, −13.96] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | whole span (card dates out) | +60.90, +25.1%, 2025-04-09, IWM 2025-04-09 176.0P | −59.10, −39.1%, 2024-08-05, IWM 2024-08-05 199.0P | 0.55 | 1,453 | 632 | total ≤ 0 (best 5 days +225; without them −1,658) |
| QQQ | whole span (card dates out) | +141.89, +25.1%, 2025-04-09, QQQ 2025-04-09 423.0P | −139.10, −34.6%, 2025-04-08, QQQ 2025-04-08 440.0P | 0.66 | 4,142 | 1,001 | total ≤ 0 (best 5 days +616; without them −4,709) |
| SPXW | whole span (card dates out) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −1,182.26, −34.4%, 2025-04-23, SPXW 2025-04-23 5445.0P | 0.61 | 49,779 | 1,135 | total ≤ 0 (best 5 days +5,592; without them −55,371) |
| SPY | whole span (card dates out) | +128.89, +25.1%, 2025-04-09, SPY 2025-04-09 495.0C | −109.10, −34.7%, 2025-04-23, SPY 2025-04-23 542.0P | 0.62 | 4,064 | 913 | total ≤ 0 (best 5 days +531; without them −4,366) |
| all names | whole span (card dates out) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −1,182.26, −34.4%, 2025-04-23, SPXW 2025-04-23 5445.0P | 0.62 | 59,140 | 1,135 | total ≤ 0 (best 5 days +6,267; without them −65,407) |
| QQQ | never-read 2026-10-14→21 | +54.90, +25.1%, 2026-10-15, QQQ 2026-10-15 720.0P | −62.10, −32.5%, 2026-10-19, QQQ 2026-10-19 720.0P | 4.05 | 12 | 2 | 100% |
| SPXW | never-read 2026-10-14→21 | +347.74, +25.0%, 2026-10-19, SPXW 2026-10-19 7690.0C | −562.26, −36.0%, 2026-10-15, SPXW 2026-10-15 7695.0P | 0.47 | 997 | 6 | total ≤ 0 (best 5 days −714; without them +0) |
| SPY | never-read 2026-10-14→21 | +30.90, +24.9%, 2026-10-21, SPY 2026-10-21 770.0C | −57.10, −34.4%, 2026-10-15, SPY 2026-10-15 767.0P | 0.44 | 91 | 6 | total ≤ 0 (best 5 days −78; without them +0) |
| all names | never-read 2026-10-14→21 | +347.74, +25.0%, 2026-10-19, SPXW 2026-10-19 7690.0C | −562.26, −36.0%, 2026-10-15, SPXW 2026-10-15 7695.0P | 0.61 | 951 | 6 | total ≤ 0 (best 5 days −602; without them +0) |
| IWM | whole span (verdict) | +60.90, +25.1%, 2025-04-09, IWM 2025-04-09 176.0P | −59.10, −39.1%, 2024-08-05, IWM 2024-08-05 199.0P | 0.55 | 1,453 | 632 | total ≤ 0 (best 5 days +225; without them −1,658) |
| QQQ | whole span (verdict) | +141.89, +25.1%, 2025-04-09, QQQ 2025-04-09 423.0P | −139.10, −34.6%, 2025-04-08, QQQ 2025-04-08 440.0P | 0.68 | 4,142 | 1,014 | total ≤ 0 (best 5 days +616; without them −4,520) |
| SPXW | whole span (verdict) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −1,182.26, −34.4%, 2025-04-23, SPXW 2025-04-23 5445.0P | 0.61 | 50,776 | 1,148 | total ≤ 0 (best 5 days +5,592; without them −56,085) |
| SPY | whole span (verdict) | +128.89, +25.1%, 2025-04-09, SPY 2025-04-09 495.0C | −109.10, −34.7%, 2025-04-23, SPY 2025-04-23 542.0P | 0.62 | 4,155 | 926 | total ≤ 0 (best 5 days +531; without them −4,444) |
| all names | whole span (verdict) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −1,182.26, −34.4%, 2025-04-23, SPXW 2025-04-23 5445.0P | 0.62 | 60,091 | 1,148 | total ≤ 0 (best 5 days +6,267; without them −66,009) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.74 a trade) and Robinhood's charged instead (mean $0.77). The study's fees are given beside them below. Re-pricing: exact (2,943 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | whole span (card dates out) | 438 | **−6.98**, −3.27 | −9.91, −4.55 | 38.1 / 33.8 | [−9.29, −4.90] / [−12.27, −7.73] |
| QQQ | whole span (card dates out) | 814 | **−4.37**, −5.03 | −5.59, −6.30 | 44.3 / 42.3 | [−5.68, −2.80] / [−6.92, −4.02] |
| SPXW | whole span (card dates out) | 902 | **−4.95**, −55.19 | −4.98, −55.48 | 41.4 / 41.4 | [−6.42, −3.35] / [−6.45, −3.38] |
| SPY | whole span (card dates out) | 771 | **−4.85**, −4.97 | −6.25, −6.25 | 41.8 / 38.4 | [−6.60, −3.28] / [−8.05, −4.65] |
| all names | whole span (card dates out) | 2,925 | **−5.07**, −20.22 | −6.22, −21.19 | 41.8 / 39.7 | [−6.13, −3.84] / [−7.32, −4.97] |
| QQQ | never-read 2026-10-14→21 | 6 | **+15.52**, +31.57 | +14.87, +30.29 | 83.3 / 83.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPXW | never-read 2026-10-14→21 | 6 | **−9.57**, −118.93 | −9.60, −119.22 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 6 | **−9.79**, −12.93 | −10.95, −14.21 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 18 | **−1.28**, −33.43 | −1.89, −34.38 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IWM | whole span (verdict) | 438 | **−6.98**, −3.27 | −9.91, −4.55 | 38.1 / 33.8 | [−9.29, −4.90] / [−12.27, −7.73] |
| QQQ | whole span (verdict) | 820 | **−4.22**, −4.76 | −5.44, −6.03 | 44.6 / 42.6 | [−5.88, −2.87] / [−7.06, −4.10] |
| SPXW | whole span (verdict) | 908 | **−4.98**, −55.61 | −5.01, −55.90 | 41.3 / 41.3 | [−6.55, −3.44] / [−6.58, −3.47] |
| SPY | whole span (verdict) | 777 | **−4.89**, −5.04 | −6.29, −6.31 | 41.7 / 38.4 | [−6.62, −3.34] / [−8.04, −4.75] |
| all names | whole span (verdict) | 2,943 | **−5.04**, −20.30 | −6.20, −21.27 | 41.9 / 39.8 | [−6.20, −3.90] / [−7.38, −5.02] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- whole span (card dates out): stop 30.8%; lock 27.4%; target 25.0%; trail 16.9%
- never-read 2026-10-14→21: target 50.0%; stop 38.9%; lock 11.1%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 152 | 35.5 | −7.99 | −4.01 | −609 |
| 2025 | IWM | 232 | 37.9 | −6.81 | −2.91 | −674 |
| 2026 | IWM | 54 | 46.3 | −4.91 | −2.77 | −149 |
| 2022 | QQQ | 30 | 40.0 | −3.25 | −1.43 | −43 |
| 2023 | QQQ | 248 | 48.8 | −3.31 | −2.68 | −664 |
| 2024 | QQQ | 244 | 41.8 | −6.02 | −7.03 | −1,716 |
| 2025 | QQQ | 233 | 45.9 | −2.90 | −3.65 | −851 |
| 2026 | QQQ | 65 | 36.9 | −6.19 | −9.69 | −630 |
| 2022 | SPXW | 164 | 36.6 | −3.36 | −44.70 | −7,331 |
| 2023 | SPXW | 240 | 46.2 | −3.50 | −27.01 | −6,483 |
| 2024 | SPXW | 228 | 41.2 | −6.27 | −76.38 | −17,415 |
| 2025 | SPXW | 213 | 41.3 | −5.50 | −64.33 | −13,702 |
| 2026 | SPXW | 63 | 34.9 | −8.39 | −88.29 | −5,562 |
| 2022 | SPY | 33 | 36.4 | −1.51 | −1.13 | −37 |
| 2023 | SPY | 240 | 44.6 | −3.28 | −1.88 | −452 |
| 2024 | SPY | 228 | 41.7 | −5.84 | −6.62 | −1,510 |
| 2025 | SPY | 213 | 42.3 | −5.23 | −6.44 | −1,371 |
| 2026 | SPY | 63 | 31.7 | −8.15 | −8.59 | −541 |
| 2022 | all names | 227 | 37.0 | −3.08 | −32.65 | −7,411 |
| 2023 | all names | 728 | 46.6 | −3.36 | −10.44 | −7,599 |
| 2024 | all names | 852 | 40.5 | −6.39 | −24.94 | −21,250 |
| 2025 | all names | 891 | 41.9 | −5.09 | −18.63 | −16,599 |
| 2026 | all names | 245 | 37.1 | −6.98 | −28.09 | −6,883 |

![](charts/s29b.png)

**Amendments, deviations and integrity checks.** As 29a.

**What it showed.** The narrative exits change nothing.

## #29c Picker, S2: "5 minutes" as a hard exit

**Folder:** `research_notes/Compass phase 3/picker_prereg`. **Commits:** c502122 / — / 1e10053. **Dates:** 2026-10-22.

**Hypothesis.** Reading the 5-minute rule as a hard exit helps.

**Rule.** Opening range = the 09:30–09:59 bars; 10:00–11:59: the first bar with high ≥ ORH × (1 + 2 bp) and close < ORH → PUT (the low side → CALL); buy the nearest OTM 0DTE contract at the ask one bar later; exit at 5 minutes, or the stop/target first.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData); a target at its resting limit

**Data.** SPY, QQQ (846 sessions), IWM (484), SPXW (972), 2022 → 2026-10-21, the 134 GeorgeFi card dates excluded.

**Periods and holdouts.** The whole tested span (verdict) and the never-read line 2026-10-14 → 21 (no verdict). The 2022–2026 NBBO had been read by the engine audit for the same universe (disclosed).

**Pass rule (as pre-registered).** Sensitivity, no verdict.

**Verdict.** Labelled: SPY −4.20%, QQQ −3.64%, IWM −7.42%, SPXW −3.10%.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | whole span (card dates out) | 438 | 394 / 634 | 39.3 | +16.3, +9.27 | −17.9, −9.57 | −5.6, −2.10 | **−4.49**, −2.17 | [−6.50, −2.52]; [−3.66, −0.83] |
| QQQ | whole span (card dates out) | 814 | 698 / 1,005 | 40.7 | +15.1, +19.23 | −14.6, −18.54 | −3.6, −4.10 | **−2.54**, −3.18 | [−3.72, −1.21]; [−5.00, −1.09] |
| SPXW | whole span (card dates out) | 902 | 765 / 1,135 | 40.4 | +13.6, +172.88 | −14.4, −172.45 | −3.9, −42.26 | **−3.08**, −33.09 | [−4.30, −1.84]; [−47.58, −17.29] |
| SPY | whole span (card dates out) | 771 | 660 / 1,005 | 39.4 | +14.0, +16.08 | −13.8, −15.10 | −4.0, −3.10 | **−2.81**, −2.81 | [−4.17, −1.52]; [−4.37, −1.17] |
| all names | whole span (card dates out) | 2,925 | 898 / 1,135 | 40.0 | +14.5, +64.71 | −14.8, −63.47 | −4.1, −4.10 | **−3.07**, −12.16 | [−4.02, −2.06]; [−16.90, −6.70] |
| QQQ | never-read 2026-10-14→21 | 6 | 5 / 6 | 66.7 | +25.1, +50.40 | −10.0, −19.10 | +25.0, +45.90 | **+13.42**, +27.23 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPXW | never-read 2026-10-14→21 | 6 | 5 / 6 | 33.3 | +15.0, +177.74 | −10.2, −117.26 | −3.9, −52.26 | **−1.76**, −18.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 6 | 5 / 6 | 33.3 | +14.8, +17.90 | −9.6, −10.60 | −4.5, −5.60 | **−1.47**, −1.10 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 18 | 5 / 6 | 44.4 | +20.0, +74.11 | −9.9, −54.96 | −2.6, −3.60 | **+3.40**, +2.40 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IWM | whole span (verdict) | 438 | 394 / 634 | 39.3 | +16.3, +9.27 | −17.9, −9.57 | −5.6, −2.10 | **−4.49**, −2.17 | [−6.50, −2.52]; [−3.66, −0.83] |
| QQQ | whole span (verdict) | 820 | 703 / 1,018 | 40.9 | +15.2, +19.61 | −14.6, −18.55 | −3.5, −4.10 | **−2.42**, −2.96 | [−3.76, −1.27]; [−5.12, −1.14] |
| SPXW | whole span (verdict) | 908 | 770 / 1,148 | 40.3 | +13.7, +172.90 | −14.4, −172.04 | −3.9, −42.26 | **−3.07**, −33.00 | [−4.43, −1.78]; [−48.54, −16.94] |
| SPY | whole span (verdict) | 777 | 665 / 1,018 | 39.4 | +14.0, +16.09 | −13.7, −15.07 | −4.0, −3.10 | **−2.80**, −2.80 | [−4.16, −1.48]; [−4.41, −1.16] |
| all names | whole span (verdict) | 2,943 | 903 / 1,148 | 40.1 | +14.6, +64.78 | −14.8, −63.42 | −4.0, −4.10 | **−3.03**, −12.07 | [−4.12, −2.02]; [−17.44, −6.50] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | whole span (card dates out) | +33.90, +14.0%, 2025-04-09, IWM 2025-04-09 176.0P | −47.10, −39.6%, 2026-02-13, IWM 2026-02-13 261.0P | 0.63 | 967 | 629 | total ≤ 0 (best 5 days +186; without them −1,136) |
| QQQ | whole span (card dates out) | +83.90, +25.2%, 2025-03-11, QQQ 2025-03-11 472.0C | −100.10, −39.4%, 2026-02-20, QQQ 2026-02-20 604.0P | 0.71 | 2,590 | 1,005 | total ≤ 0 (best 5 days +523; without them −3,113) |
| SPXW | whole span (card dates out) | +907.74, +16.4%, 2025-04-09, SPXW 2025-04-09 4960.0C | −992.26, −34.1%, 2026-02-05, SPXW 2026-02-05 6810.0C | 0.68 | 30,354 | 1,038 | total ≤ 0 (best 5 days +4,440; without them −34,289) |
| SPY | whole span (card dates out) | +88.89, +17.3%, 2025-04-09, SPY 2025-04-09 495.0C | −97.10, −32.5%, 2026-02-05, SPY 2026-02-05 679.0C | 0.69 | 2,417 | 914 | total ≤ 0 (best 5 days +411; without them −2,577) |
| all names | whole span (card dates out) | +907.74, +16.4%, 2025-04-09, SPXW 2025-04-09 4960.0C | −992.26, −34.1%, 2026-02-05, SPXW 2026-02-05 6810.0C | 0.68 | 36,007 | 1,038 | total ≤ 0 (best 5 days +4,952; without them −40,507) |
| QQQ | never-read 2026-10-14→21 | +54.90, +25.1%, 2026-10-15, QQQ 2026-10-15 720.0P | −34.10, −17.9%, 2026-10-19, QQQ 2026-10-19 720.0P | 5.28 | 38 | 2 | 100% |
| SPXW | never-read 2026-10-14→21 | +247.74, +22.3%, 2026-10-21, SPXW 2026-10-21 7725.0C | −222.26, −17.8%, 2026-10-14, SPXW 2026-10-14 7760.0C | 0.76 | 327 | 6 | total ≤ 0 (best 5 days −114; without them +0) |
| SPY | never-read 2026-10-14→21 | +25.90, +20.9%, 2026-10-21, SPY 2026-10-21 770.0C | −17.10, −17.8%, 2026-10-14, SPY 2026-10-14 774.0C | 0.84 | 28 | 6 | total ≤ 0 (best 5 days −7; without them +0) |
| all names | never-read 2026-10-14→21 | +247.74, +22.3%, 2026-10-21, SPXW 2026-10-21 7725.0C | −222.26, −17.8%, 2026-10-14, SPXW 2026-10-14 7760.0C | 1.08 | 218 | 5 | 100% |
| IWM | whole span (verdict) | +33.90, +14.0%, 2025-04-09, IWM 2025-04-09 176.0P | −47.10, −39.6%, 2026-02-13, IWM 2026-02-13 261.0P | 0.63 | 967 | 629 | total ≤ 0 (best 5 days +186; without them −1,136) |
| QQQ | whole span (verdict) | +83.90, +25.2%, 2025-03-11, QQQ 2025-03-11 472.0C | −100.10, −39.4%, 2026-02-20, QQQ 2026-02-20 604.0P | 0.73 | 2,590 | 1,018 | total ≤ 0 (best 5 days +523; without them −2,950) |
| SPXW | whole span (verdict) | +907.74, +16.4%, 2025-04-09, SPXW 2025-04-09 4960.0C | −992.26, −34.1%, 2026-02-05, SPXW 2026-02-05 6810.0C | 0.68 | 30,575 | 1,051 | total ≤ 0 (best 5 days +4,440; without them −34,402) |
| SPY | whole span (verdict) | +88.89, +17.3%, 2025-04-09, SPY 2025-04-09 495.0C | −97.10, −32.5%, 2026-02-05, SPY 2026-02-05 679.0C | 0.69 | 2,434 | 927 | total ≤ 0 (best 5 days +411; without them −2,583) |
| all names | whole span (verdict) | +907.74, +16.4%, 2025-04-09, SPXW 2025-04-09 4960.0C | −992.26, −34.1%, 2026-02-05, SPXW 2026-02-05 6810.0C | 0.68 | 36,172 | 1,051 | total ≤ 0 (best 5 days +4,952; without them −40,464) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.74 a trade) and Robinhood's charged instead (mean $0.77). The study's fees are given beside them below. Re-pricing: exact (2,943 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | whole span (card dates out) | 438 | **−4.49**, −2.17 | −7.42, −3.44 | 39.3 / 35.8 | [−6.50, −2.52] / [−9.45, −5.42] |
| QQQ | whole span (card dates out) | 814 | **−2.54**, −3.18 | −3.76, −4.46 | 40.7 / 38.9 | [−3.72, −1.21] / [−4.96, −2.44] |
| SPXW | whole span (card dates out) | 902 | **−3.08**, −33.09 | −3.11, −33.39 | 40.4 / 40.4 | [−4.30, −1.84] / [−4.33, −1.87] |
| SPY | whole span (card dates out) | 771 | **−2.81**, −2.81 | −4.21, −4.08 | 39.4 / 36.4 | [−4.17, −1.52] / [−5.64, −2.91] |
| all names | whole span (card dates out) | 2,925 | **−3.07**, −12.16 | −4.23, −13.13 | 40.0 / 38.3 | [−4.02, −2.06] / [−5.22, −3.18] |
| QQQ | never-read 2026-10-14→21 | 6 | **+13.42**, +27.23 | +12.77, +25.96 | 66.7 / 66.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPXW | never-read 2026-10-14→21 | 6 | **−1.76**, −18.93 | −1.78, −19.22 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 6 | **−1.47**, −1.10 | −2.63, −2.38 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 18 | **+3.40**, +2.40 | +2.79, +1.45 | 44.4 / 44.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IWM | whole span (verdict) | 438 | **−4.49**, −2.17 | −7.42, −3.44 | 39.3 / 35.8 | [−6.50, −2.52] / [−9.45, −5.42] |
| QQQ | whole span (verdict) | 820 | **−2.42**, −2.96 | −3.64, −4.23 | 40.9 / 39.1 | [−3.76, −1.27] / [−4.99, −2.47] |
| SPXW | whole span (verdict) | 908 | **−3.07**, −33.00 | −3.10, −33.29 | 40.3 / 40.3 | [−4.43, −1.78] / [−4.46, −1.80] |
| SPY | whole span (verdict) | 777 | **−2.80**, −2.80 | −4.20, −4.07 | 39.4 / 36.4 | [−4.16, −1.48] / [−5.61, −2.85] |
| all names | whole span (verdict) | 2,943 | **−3.03**, −12.07 | −4.18, −13.04 | 40.1 / 38.3 | [−4.12, −2.02] / [−5.32, −3.14] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- whole span (card dates out): time5 80.8%; target 13.2%; stop 6.0%
- never-read 2026-10-14→21: time5 77.8%; target 22.2%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 152 | 32.2 | −6.92 | −3.95 | −600 |
| 2025 | IWM | 232 | 44.0 | −2.52 | −0.60 | −140 |
| 2026 | IWM | 54 | 38.9 | −6.13 | −3.88 | −209 |
| 2022 | QQQ | 30 | 36.7 | −0.96 | −0.13 | −4 |
| 2023 | QQQ | 248 | 43.5 | −1.14 | −0.83 | −205 |
| 2024 | QQQ | 244 | 38.5 | −3.67 | −4.65 | −1,135 |
| 2025 | QQQ | 233 | 43.3 | −1.52 | −1.46 | −339 |
| 2026 | QQQ | 65 | 32.3 | −6.52 | −11.44 | −744 |
| 2022 | SPXW | 164 | 45.7 | −1.47 | −19.88 | −3,261 |
| 2023 | SPXW | 240 | 42.9 | −2.70 | −15.51 | −3,723 |
| 2024 | SPXW | 228 | 34.2 | −3.87 | −46.08 | −10,505 |
| 2025 | SPXW | 213 | 39.0 | −3.43 | −40.99 | −8,732 |
| 2026 | SPXW | 63 | 42.9 | −4.60 | −59.40 | −3,742 |
| 2022 | SPY | 33 | 42.4 | −4.09 | −4.49 | −148 |
| 2023 | SPY | 240 | 44.2 | −1.80 | −0.52 | −124 |
| 2024 | SPY | 228 | 34.2 | −3.26 | −3.60 | −820 |
| 2025 | SPY | 213 | 38.5 | −2.84 | −3.55 | −755 |
| 2026 | SPY | 63 | 41.3 | −4.09 | −5.15 | −324 |
| 2022 | all names | 227 | 44.1 | −1.79 | −15.04 | −3,413 |
| 2023 | all names | 728 | 43.5 | −1.87 | −5.57 | −4,052 |
| 2024 | all names | 852 | 35.1 | −4.19 | −15.33 | −13,060 |
| 2025 | all names | 891 | 41.3 | −2.55 | −11.19 | −9,967 |
| 2026 | all names | 245 | 38.8 | −5.32 | −20.49 | −5,020 |

![](charts/s29c.png)

**Amendments, deviations and integrity checks.** As 29a.

**What it showed.** Shorter holds lose less, still lose.

## #29d Picker, S3: SPXW rides to the official close when in the money at 15:58

**Folder:** `research_notes/Compass phase 3/picker_prereg`. **Commits:** c502122 / — / 1e10053. **Dates:** 2026-10-22.

**Hypothesis.** SPXW's cash settlement adds value.

**Rule.** Opening range = the 09:30–09:59 bars; 10:00–11:59: the first bar with high ≥ ORH × (1 + 2 bp) and close < ORH → PUT (the low side → CALL); buy the nearest OTM 0DTE contract at the ask one bar later; SPXW only; ITM at 15:58 → settle.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData); a target at its resting limit

**Data.** SPY, QQQ (846 sessions), IWM (484), SPXW (972), 2022 → 2026-10-21, the 134 GeorgeFi card dates excluded.

**Periods and holdouts.** The whole tested span (verdict) and the never-read line 2026-10-14 → 21 (no verdict). The 2022–2026 NBBO had been read by the engine audit for the same universe (disclosed).

**Pass rule (as pre-registered).** Sensitivity, no verdict.

**Verdict.** Labelled: identical to PRIMARY (no trade was open at 15:58).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| SPXW | whole span (card dates out) | 902 | 765 / 1,135 | 36.9 | +21.9, +269.51 | −20.7, −252.86 | −7.9, −82.26 | **−5.00**, −60.01 | [−6.67, −3.48]; [−84.67, −36.93] |
| SPXW | never-read 2026-10-14→21 | 6 | 5 / 6 | 50.0 | +24.9, +291.07 | −12.5, −145.59 | +10.1, +87.74 | **+6.24**, +72.74 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPXW | whole span (verdict) | 908 | 770 / 1,148 | 37.0 | +21.9, +269.70 | −20.7, −252.30 | −7.8, −77.26 | **−4.93**, −59.13 | [−6.70, −3.46]; [−85.43, −36.69] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| SPXW | whole span (card dates out) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −2,952.26, −45.6%, 2025-04-07, SPXW 2025-04-07 4970.0P | 0.62 | 54,455 | 1,135 | total ≤ 0 (best 5 days +6,120; without them −60,249) |
| SPXW | never-read 2026-10-14→21 | +347.74, +25.0%, 2026-10-19, SPXW 2026-10-19 7690.0C | −222.26, −17.8%, 2026-10-14, SPXW 2026-10-14 7760.0C | 2.00 | 295 | 3 | 100% |
| SPXW | whole span (verdict) | +1,387.74, +25.1%, 2025-04-09, SPXW 2025-04-09 4960.0C | −2,952.26, −45.6%, 2025-04-07, SPXW 2025-04-07 4970.0P | 0.63 | 54,455 | 1,148 | total ≤ 0 (best 5 days +6,120; without them −59,812) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.55 a trade) and Robinhood's charged instead (mean $2.26). The study's fees are given beside them below. Re-pricing: exact (908 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| SPXW | whole span (card dates out) | 902 | **−5.00**, −60.01 | −5.03, −60.30 | 36.9 / 36.9 | [−6.67, −3.48] / [−6.69, −3.51] |
| SPXW | never-read 2026-10-14→21 | 6 | **+6.24**, +72.74 | +6.21, +72.44 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPXW | whole span (verdict) | 908 | **−4.93**, −59.13 | −4.96, −59.43 | 37.0 / 37.0 | [−6.70, −3.46] / [−6.73, −3.49] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- whole span (card dates out): time5 48.9%; target 31.5%; stop 19.6%
- never-read 2026-10-14→21: time5 50.0%; target 50.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | SPXW | 164 | 40.9 | −3.26 | −41.41 | −6,791 |
| 2023 | SPXW | 240 | 41.7 | −3.14 | −25.47 | −6,113 |
| 2024 | SPXW | 228 | 28.5 | −7.29 | −75.33 | −17,175 |
| 2025 | SPXW | 213 | 36.2 | −5.61 | −88.18 | −18,782 |
| 2026 | SPXW | 63 | 42.9 | −5.23 | −76.71 | −4,832 |

![](charts/s29d.png)

**Amendments, deviations and integrity checks.** As 29a.

**What it showed.** No trade reached 15:58.

## #29e Picker, IMPROVED (picked on the cards): PDH sweep → put, 10:00–12:00, +25% or 5 minutes

**Folder:** `research_notes/Compass phase 3/picker_prereg`. **Commits:** c502122 / — / 1e10053. **Dates:** 2026-10-22.

**Hypothesis.** The owner's "improved" parameters, traced to the cards, work.

**Rule.** SPXW/SPY/IWM: prior-day-high sweep → put, 10:00–12:00, sell at +25% or at 5 minutes.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData); a target at its resting limit

**Data.** SPY, QQQ (846 sessions), IWM (484), SPXW (972), 2022 → 2026-10-21, the 134 GeorgeFi card dates excluded.

**Periods and holdouts.** The whole tested span (verdict) and the never-read line 2026-10-14 → 21 (no verdict). The 2022–2026 NBBO had been read by the engine audit for the same universe (disclosed).

**Pass rule (as pre-registered).** Labelled, never pooled; the owner's rule shown for reading only.

**Verdict.** FAIL on every name (read only): SPXW −3.81% [−6.76, −0.95], SPY −4.77%, IWM −10.38%.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| IWM | whole span (card dates out) | 106 | 106 / 615 | 35.8 | +16.1, +9.00 | −20.6, −11.22 | −8.3, −4.10 | **−7.45**, −3.97 | [−11.56, −3.37]; [−7.45, −0.87] |
| SPXW | whole span (card dates out) | 217 | 217 / 1,105 | 40.1 | +16.9, +196.93 | −17.9, −197.72 | −6.2, −62.26 | **−3.92**, −39.50 | [−6.82, −1.00]; [−77.20, −2.81] |
| SPY | whole span (card dates out) | 191 | 191 / 977 | 40.3 | +17.4, +18.54 | −17.6, −17.83 | −6.6, −5.10 | **−3.48**, −3.17 | [−6.09, +0.27]; [−6.48, +1.24] |
| all names | whole span (card dates out) | 514 | 275 / 1,125 | 39.3 | +17.0, +93.58 | −18.4, −91.34 | −7.0, −7.10 | **−4.48**, −18.67 | [−7.09, −1.91]; [−36.18, −2.07] |
| SPXW | never-read 2026-10-14→21 | 1 | 1 / 1 | 100.0 | +25.2, +337.74 | —, — | +25.2, +337.74 | **+25.20**, +337.74 | n/a (< 60 sessions); n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 1 | 1 / 1 | 100.0 | +24.9, +35.90 | —, — | +24.9, +35.90 | **+24.93**, +35.90 | n/a (< 60 sessions); n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 2 | 1 / 1 | 100.0 | +25.1, +186.82 | —, — | +25.1, +186.82 | **+25.07**, +186.82 | n/a (< 60 sessions); n/a (< 60 sessions) |
| IWM | whole span (verdict) | 106 | 106 / 615 | 35.8 | +16.1, +9.00 | −20.6, −11.22 | −8.3, −4.10 | **−7.45**, −3.97 | [−11.56, −3.37]; [−7.45, −0.87] |
| SPXW | whole span (verdict) | 218 | 218 / 1,145 | 40.4 | +17.0, +198.53 | −17.9, −197.72 | −6.2, −62.26 | **−3.78**, −37.77 | [−6.90, −1.07]; [−80.50, −2.94] |
| SPY | whole span (verdict) | 192 | 192 / 1,017 | 40.6 | +17.5, +18.76 | −17.6, −17.83 | −6.6, −5.10 | **−3.33**, −2.97 | [−6.21, +0.07]; [−6.54, +1.13] |
| all names | whole span (verdict) | 516 | 276 / 1,145 | 39.5 | +17.0, +94.49 | −18.4, −91.34 | −6.9, −7.10 | **−4.37**, −17.87 | [−7.23, −1.84]; [−37.83, −1.65] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| IWM | whole span (card dates out) | +28.90, +24.9%, 2024-07-17, IWM 2024-07-17 224.0P | −129.10, −60.3%, 2025-04-07, IWM 2025-04-07 182.0P | 0.45 | 516 | 512 | total ≤ 0 (best 5 days +117; without them −538) |
| SPXW | whole span (card dates out) | +477.74, +25.0%, 2024-08-07, SPXW 2024-08-07 5310.0P | −1,172.26, −49.7%, 2026-02-20, SPXW 2026-02-20 6870.0P | 0.67 | 9,095 | 1,084 | total ≤ 0 (best 5 days +2,259; without them −10,829) |
| SPY | whole span (card dates out) | +50.90, +22.5%, 2025-11-20, SPY 2025-11-20 667.0P | −108.10, −48.9%, 2026-02-20, SPY 2026-02-20 685.0P | 0.70 | 642 | 977 | total ≤ 0 (best 5 days +224; without them −830) |
| all names | whole span (card dates out) | +477.74, +25.0%, 2024-08-07, SPXW 2024-08-07 5310.0P | −1,172.26, −49.7%, 2026-02-20, SPXW 2026-02-20 6870.0P | 0.66 | 10,121 | 1,104 | total ≤ 0 (best 5 days +2,494; without them −12,090) |
| SPXW | never-read 2026-10-14→21 | +337.74, +25.2%, 2026-10-20, SPXW 2026-10-20 7715.0P | +337.74, +25.2%, 2026-10-20, SPXW 2026-10-20 7715.0P | ∞ | 0 | 0 | 100% |
| SPY | never-read 2026-10-14→21 | +35.90, +24.9%, 2026-10-20, SPY 2026-10-20 769.0P | +35.90, +24.9%, 2026-10-20, SPY 2026-10-20 769.0P | ∞ | 0 | 0 | 100% |
| all names | never-read 2026-10-14→21 | +337.74, +25.2%, 2026-10-20, SPXW 2026-10-20 7715.0P | +35.90, +24.9%, 2026-10-20, SPY 2026-10-20 769.0P | ∞ | 0 | 0 | 100% |
| IWM | whole span (verdict) | +28.90, +24.9%, 2024-07-17, IWM 2024-07-17 224.0P | −129.10, −60.3%, 2025-04-07, IWM 2025-04-07 182.0P | 0.45 | 516 | 512 | total ≤ 0 (best 5 days +117; without them −538) |
| SPXW | whole span (verdict) | +477.74, +25.0%, 2024-08-07, SPXW 2024-08-07 5310.0P | −1,172.26, −49.7%, 2026-02-20, SPXW 2026-02-20 6870.0P | 0.68 | 9,095 | 1,124 | total ≤ 0 (best 5 days +2,259; without them −10,492) |
| SPY | whole span (verdict) | +50.90, +22.5%, 2025-11-20, SPY 2025-11-20 667.0P | −108.10, −48.9%, 2026-02-20, SPY 2026-02-20 685.0P | 0.72 | 642 | 1,017 | total ≤ 0 (best 5 days +224; without them −794) |
| all names | whole span (verdict) | +477.74, +25.0%, 2024-08-07, SPXW 2024-08-07 5310.0P | −1,172.26, −49.7%, 2026-02-20, SPXW 2026-02-20 6870.0P | 0.68 | 10,121 | 1,124 | total ≤ 0 (best 5 days +2,494; without them −11,717) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.87 a trade) and Robinhood's charged instead (mean $1.01). The study's fees are given beside them below. Re-pricing: exact (516 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| IWM | whole span (card dates out) | 106 | **−7.45**, −3.97 | −10.38, −5.24 | 35.8 / 34.9 | [−11.56, −3.37] / [−14.45, −6.32] |
| SPXW | whole span (card dates out) | 217 | **−3.92**, −39.50 | −3.95, −39.79 | 40.1 / 40.1 | [−6.82, −1.00] / [−6.85, −1.03] |
| SPY | whole span (card dates out) | 191 | **−3.48**, −3.17 | −4.92, −4.44 | 40.3 / 38.7 | [−6.09, +0.27] / [−7.55, −1.17] |
| all names | whole span (card dates out) | 514 | **−4.48**, −18.67 | −5.64, −19.53 | 39.3 / 38.5 | [−7.09, −1.91] / [−8.26, −3.06] |
| SPXW | never-read 2026-10-14→21 | 1 | **+25.20**, +337.74 | +25.18, +337.44 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| SPY | never-read 2026-10-14→21 | 1 | **+24.93**, +35.90 | +24.05, +34.62 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| all names | never-read 2026-10-14→21 | 2 | **+25.07**, +186.82 | +24.61, +186.03 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| IWM | whole span (verdict) | 106 | **−7.45**, −3.97 | −10.38, −5.24 | 35.8 / 34.9 | [−11.56, −3.37] / [−14.45, −6.32] |
| SPXW | whole span (verdict) | 218 | **−3.78**, −37.77 | −3.81, −38.06 | 40.4 / 40.4 | [−6.90, −1.07] / [−6.93, −1.10] |
| SPY | whole span (verdict) | 192 | **−3.33**, −2.97 | −4.77, −4.24 | 40.6 / 39.1 | [−6.21, +0.07] / [−7.69, −1.37] |
| all names | whole span (verdict) | 516 | **−4.37**, −17.87 | −5.52, −18.73 | 39.5 / 38.8 | [−7.23, −1.84] / [−8.38, −2.95] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- whole span (card dates out): time5 81.9%; target 18.1%
- never-read 2026-10-14→21: target 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2024 | IWM | 37 | 45.9 | −2.88 | −0.24 | −9 |
| 2025 | IWM | 52 | 34.6 | −9.24 | −5.89 | −306 |
| 2026 | IWM | 17 | 17.6 | −11.89 | −6.22 | −106 |
| 2022 | SPXW | 33 | 42.4 | −5.28 | −74.99 | −2,475 |
| 2023 | SPXW | 61 | 37.7 | −5.03 | −43.57 | −2,658 |
| 2024 | SPXW | 50 | 38.0 | −1.08 | +9.34 | +467 |
| 2025 | SPXW | 57 | 47.4 | −2.03 | −11.03 | −629 |
| 2026 | SPXW | 17 | 29.4 | −10.22 | −172.85 | −2,938 |
| 2022 | SPY | 7 | 28.6 | −14.54 | −15.39 | −108 |
| 2023 | SPY | 61 | 37.7 | −4.59 | −3.46 | −211 |
| 2024 | SPY | 50 | 42.0 | −0.41 | +1.14 | +57 |
| 2025 | SPY | 57 | 47.4 | −1.23 | −0.61 | −35 |
| 2026 | SPY | 17 | 29.4 | −9.88 | −16.04 | −273 |
| 2022 | all names | 40 | 40.0 | −6.90 | −64.56 | −2,582 |
| 2023 | all names | 122 | 37.7 | −4.81 | −23.52 | −2,869 |
| 2024 | all names | 137 | 41.6 | −1.32 | +3.76 | +515 |
| 2025 | all names | 166 | 43.4 | −4.01 | −5.84 | −970 |
| 2026 | all names | 51 | 25.5 | −10.67 | −65.04 | −3,317 |

![](charts/s29e.png)

**Amendments, deviations and integrity checks.** Parameters picked from the cards, whose dates are excluded.

**What it showed.** Negative on every name.

## #29f Picker: flow gate and grade check

**Folder:** `research_notes/Compass phase 3/picker_prereg`. **Commits:** c502122 / — / 1e10053. **Dates:** 2026-10-22.

**Hypothesis.** UW sweep flow on the trade's side, and the vendor's grades, separate winners.

**Rule.** Gate: trade-side UW sweep ask-premium over the 5 minutes before entry > the other side. Grade: A+/A/B+ on the vendor cards.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** Flow: one session (2026-10-21). Grades: the D1 ledger (489 cards).

**Periods and holdouts.** —

**Pass rule (as pre-registered).** Descriptive only.

**Verdict.** Flow gate: 0 of 5 trades gated (one session). Grades (vendor-recorded, not re-marked): A+ +8.09% [+1.81, +19.44], A +3.12%, B+ −3.23%; A+ − A +4.97 [−3.79, +15.09].

**Metrics.** not available — one session of flow (5 trades) and the vendor's own recorded returns (see #1, vendor-recorded).

**Amendments, deviations and integrity checks.** —

**What it showed.** No usable gate; the grades rank the vendor's own record.

## #30a Compass features: the base trades (every feature is judged against them)

**Folder:** `research_notes/Compass features/`. **Commits:** inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e. **Dates:** 2026-10-22.

**Hypothesis.** (The reference set.)

**Rule.** Every base trade, fixed exit: 0DTE sold at the 15:58 bid (SPXW held to settlement), multi-day at a fixed horizon.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData) (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)

**Data.** The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).

**Periods and holdouts.** exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).

**Pass rule (as pre-registered).** —

**Verdict.** Descriptive: −13.35% a trade (exploration), −11.03% (holdout).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 651,232 | 2,596 / 3,671 | 27.0 | +168.5, +741.48 | −78.4, −330.47 | −73.4, −56.10 | **−11.66**, −40.85 | [−14.67, −8.76]; [−57.10, −24.10] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 580,234 | 3,577 / 3,686 | 28.3 | +159.0, +669.32 | −75.9, −306.57 | −66.0, −47.10 | **−9.39**, −30.17 | [−12.26, −6.22]; [−43.06, −9.06] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | +73,267.74, +453.4%, 2025-03-25, SPXW 31-60 5900.0P | −27,252.26, −77.6%, 2025-04-08, SPXW 31-60 5175.0P | 0.83 | 26,826,744 | 3,671 | total ≤ 0 (best 5 days +4,030,356; without them −30,633,237) |
| 0DTE→60 DTE, 15 names | holdout (opened) | +45,477.74, +143.5%, 2026-03-30, SPXW 31-60 6220.0C | −32,491.13, −100.0%, 2026-10-19, SPXW 1-7 7740.0P | 0.86 | 17,504,031 | 3,686 | total ≤ 0 (best 5 days +2,437,620; without them −19,941,651) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.29 a trade) and Robinhood's charged instead (mean $0.24). The study's fees are given beside them below. Re-pricing: exact (1,231,466 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 651,232 | **−11.66**, −40.85 | −13.35, −41.86 | 27.0 / 26.9 | [−14.67, −8.76] / [−16.39, −10.41] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 580,234 | **−9.39**, −30.17 | −11.03, −31.26 | 28.3 / 28.2 | [−12.26, −6.22] / [−13.95, −7.83] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration: fixed exit 100.0%
- holdout (opened): fixed exit 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | 0DTE→60 DTE, 15 names | 7,483 | 33.4 | −14.57 | −19.13 | −143,128 |
| 2013 | 0DTE→60 DTE, 15 names | 13,829 | 33.8 | −8.36 | −12.16 | −168,121 |
| 2014 | 0DTE→60 DTE, 15 names | 14,053 | 35.3 | −7.14 | −10.83 | −152,153 |
| 2015 | 0DTE→60 DTE, 15 names | 14,318 | 32.3 | −8.75 | −15.94 | −228,164 |
| 2016 | 0DTE→60 DTE, 15 names | 14,750 | 32.3 | −8.71 | −17.81 | −262,733 |
| 2017 | 0DTE→60 DTE, 15 names | 26,450 | 26.4 | −11.80 | −15.92 | −421,047 |
| 2018 | 0DTE→60 DTE, 15 names | 45,006 | 27.0 | −15.94 | −17.01 | −765,774 |
| 2019 | 0DTE→60 DTE, 15 names | 41,854 | 25.6 | −23.61 | −28.81 | −1,206,001 |
| 2020 | 0DTE→60 DTE, 15 names | 52,798 | 26.3 | −14.46 | −39.88 | −2,105,827 |
| 2021 | 0DTE→60 DTE, 15 names | 50,593 | 24.5 | −24.22 | −58.86 | −2,977,693 |
| 2022 | 0DTE→60 DTE, 15 names | 90,557 | 27.2 | −12.55 | −53.30 | −4,826,972 |
| 2023 | 0DTE→60 DTE, 15 names | 194,773 | 28.3 | −8.15 | −31.31 | −6,098,522 |
| 2024 | 0DTE→60 DTE, 15 names | 210,416 | 27.9 | −6.83 | −15.66 | −3,294,940 |
| 2025 | 0DTE→60 DTE, 15 names | 223,997 | 27.7 | −9.02 | −36.18 | −8,103,173 |
| 2026 | 0DTE→60 DTE, 15 names | 230,589 | 26.9 | −9.86 | −57.91 | −13,352,664 |

![](charts/s30a.png)

**Amendments, deviations and integrity checks.** The holdout join duplicated rows on the first read (777,571 rows for 580,274 trades); fixed with no feature, threshold or rule changed.

**What it showed.** The base trades lose 11–13% of the debit a trade.

## #30b Compass features V1: veto a spread over 10% of mid (PASSED)

**Folder:** `research_notes/Compass features/`. **Commits:** inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e. **Dates:** 2026-10-22.

**Hypothesis.** Skipping wide spreads makes a losing set lose less.

**Rule.** The base trades with (ask − bid) ÷ mid ≤ 10% at the entry quote.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData) (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)

**Data.** The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).

**Periods and holdouts.** exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).

**Pass rule (as pre-registered).** Holdout Δ (with − without, % of debit) > 0 with its 20-session block 95% interval clear of zero.

**Verdict.** PASS: holdout Δ +2.61 [+1.76, +3.46] (−8.43 with vs −11.03 without).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 538,468 | 2,594 / 3,671 | 28.1 | +163.5, +774.06 | −77.5, −355.59 | −69.2, −61.04 | **−9.72**, −37.88 | [−12.93, −6.46]; [−56.55, −18.77] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 474,526 | 3,572 / 3,686 | 29.7 | +153.4, +673.84 | −74.9, −321.38 | −61.4, −49.04 | **−7.14**, −26.08 | [−9.97, −3.99]; [−39.67, −4.48] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | +73,267.74, +453.4%, 2025-03-25, SPXW 31-60 5900.0P | −27,252.26, −77.6%, 2025-04-08, SPXW 31-60 5175.0P | 0.85 | 20,616,811 | 3,671 | total ≤ 0 (best 5 days +4,132,210; without them −24,528,078) |
| 0DTE→60 DTE, 15 names | holdout (opened) | +45,477.74, +143.5%, 2026-03-30, SPXW 31-60 6220.0C | −29,000.04, −100.0%, 2026-10-19, MU 1-7 1000.0C | 0.88 | 12,374,254 | 3,686 | total ≤ 0 (best 5 days +2,369,409; without them −14,743,663) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.31 a trade) and Robinhood's charged instead (mean $0.27). The study's fees are given beside them below. Re-pricing: exact (1,012,994 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 538,468 | **−9.72**, −37.88 | −10.89, −38.87 | 28.1 / 28.0 | [−12.93, −6.46] / [−14.09, −7.65] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 474,526 | **−7.14**, −26.08 | −8.43, −27.16 | 29.7 / 29.5 | [−9.97, −3.99] / [−11.25, −5.25] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration: fixed exit 100.0%
- holdout (opened): fixed exit 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | 0DTE→60 DTE, 15 names | 6,826 | 33.4 | −15.13 | −20.70 | −141,305 |
| 2013 | 0DTE→60 DTE, 15 names | 12,329 | 33.9 | −9.51 | −13.44 | −165,709 |
| 2014 | 0DTE→60 DTE, 15 names | 12,822 | 36.1 | −6.59 | −11.18 | −143,386 |
| 2015 | 0DTE→60 DTE, 15 names | 13,158 | 33.2 | −6.84 | −15.85 | −208,518 |
| 2016 | 0DTE→60 DTE, 15 names | 14,153 | 32.4 | −9.19 | −18.67 | −264,175 |
| 2017 | 0DTE→60 DTE, 15 names | 15,517 | 30.3 | −11.23 | −19.48 | −302,248 |
| 2018 | 0DTE→60 DTE, 15 names | 23,379 | 32.6 | −6.95 | −8.56 | −200,046 |
| 2019 | 0DTE→60 DTE, 15 names | 25,570 | 31.3 | −14.22 | −25.13 | −642,470 |
| 2020 | 0DTE→60 DTE, 15 names | 32,249 | 29.9 | −7.61 | −31.64 | −1,020,510 |
| 2021 | 0DTE→60 DTE, 15 names | 35,164 | 27.0 | −21.52 | −60.05 | −2,111,715 |
| 2022 | 0DTE→60 DTE, 15 names | 76,404 | 28.1 | −11.42 | −51.57 | −3,940,490 |
| 2023 | 0DTE→60 DTE, 15 names | 169,119 | 29.2 | −6.98 | −28.25 | −4,778,061 |
| 2024 | 0DTE→60 DTE, 15 names | 179,301 | 28.7 | −5.20 | −9.23 | −1,654,092 |
| 2025 | 0DTE→60 DTE, 15 names | 201,814 | 28.1 | −7.93 | −31.15 | −6,286,096 |
| 2026 | 0DTE→60 DTE, 15 names | 195,189 | 27.5 | −9.28 | −55.90 | −10,911,300 |

![](charts/s30b.png)

**Amendments, deviations and integrity checks.** As 30a.

**What it showed.** A cost filter: the with-set still loses 8.4% a trade.

## #30c Compass features X3: sell a same-day long option at the 14:00 bid (PASSED)

**Folder:** `research_notes/Compass features/`. **Commits:** inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e. **Dates:** 2026-10-22.

**Hypothesis.** Selling 0DTE longs at 14:00 beats holding to 15:58/settlement.

**Rule.** 0DTE base trades entered before 14:00, sold at the 14:00 bid.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData) (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)

**Data.** The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).

**Periods and holdouts.** exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).

**Pass rule (as pre-registered).** As 30b.

**Verdict.** PASS: holdout Δ +7.78 [+4.14, +10.95] (−9.51 with vs −17.29 without).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 291,090 | 964 / 2,388 | 28.9 | +109.1, +374.81 | −60.5, −184.85 | −42.6, −25.10 | **−11.48**, −23.17 | [−13.72, −9.24]; [−32.52, −11.51] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 233,454 | 1,290 / 2,428 | 29.6 | +121.7, +266.96 | −61.2, −127.43 | −42.2, −21.10 | **−6.97**, −10.58 | [−11.22, −4.91]; [−18.52, −4.17] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | +36,117.74, +538.3%, 2025-04-09, SPXW 0DTE 4940.0C | −9,452.26, −96.9%, 2025-04-09, SPXW 0DTE 5040.0P | 0.82 | 6,745,277 | 2,388 | total ≤ 0 (best 5 days +1,951,222; without them −8,695,714) |
| 0DTE→60 DTE, 15 names | holdout (opened) | +19,167.74, +891.5%, 2025-11-20, SPXW 0DTE 6780.0P | −4,252.26, −93.3%, 2025-11-21, SPXW 0DTE 6580.0P | 0.88 | 2,806,725 | 2,418 | total ≤ 0 (best 5 days +1,179,475; without them −3,649,568) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.58 a trade) and Robinhood's charged instead (mean $0.49). The study's fees are given beside them below. Re-pricing: exact (524,544 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 291,090 | **−11.48**, −23.17 | −13.88, −24.21 | 28.9 / 28.3 | [−13.72, −9.24] / [−16.20, −11.58] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 233,454 | **−6.97**, −10.58 | −9.51, −11.72 | 29.6 / 29.0 | [−11.22, −4.91] / [−13.87, −7.42] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration: sold at the 14:00 bid 100.0%
- holdout (opened): sold at the 14:00 bid 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2017 | 0DTE→60 DTE, 15 names | 9,741 | 21.3 | −6.70 | −9.41 | −91,695 |
| 2018 | 0DTE→60 DTE, 15 names | 23,860 | 25.2 | −19.64 | −27.75 | −662,143 |
| 2019 | 0DTE→60 DTE, 15 names | 21,472 | 23.8 | −19.62 | −25.50 | −547,548 |
| 2020 | 0DTE→60 DTE, 15 names | 29,501 | 27.2 | −13.55 | −37.94 | −1,119,259 |
| 2021 | 0DTE→60 DTE, 15 names | 27,934 | 26.5 | −15.96 | −43.34 | −1,210,556 |
| 2022 | 0DTE→60 DTE, 15 names | 47,279 | 30.3 | −9.69 | −32.09 | −1,517,213 |
| 2023 | 0DTE→60 DTE, 15 names | 72,946 | 31.4 | −6.40 | −14.26 | −1,040,264 |
| 2024 | 0DTE→60 DTE, 15 names | 84,765 | 29.9 | −8.98 | −12.43 | −1,053,383 |
| 2025 | 0DTE→60 DTE, 15 names | 93,284 | 31.3 | −4.32 | +5.61 | +523,027 |
| 2026 | 0DTE→60 DTE, 15 names | 113,762 | 28.9 | −9.47 | −21.94 | −2,495,551 |

![](charts/s30c.png)

**Amendments, deviations and integrity checks.** As 30a.

**What it showed.** Selling at 14:00 halves the loss; the with-set still loses 9.5% a trade.

## #30d Compass features BV1b: the V1 veto at 3% (PASSED, Phase B)

**Folder:** `research_notes/Compass features/`. **Commits:** inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e. **Dates:** 2026-10-22.

**Hypothesis.** A stricter spread veto.

**Rule.** The base trades with spread ≤ 3% of mid.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData) (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)

**Data.** The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).

**Periods and holdouts.** exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).

**Pass rule (as pre-registered).** As 30b (Phase B, read once).

**Verdict.** PASS: holdout Δ +4.30 [+2.66, +5.85] (−6.73 with vs −11.03) — the holdout was not virgin for it.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 265,416 | 2,576 / 3,671 | 30.9 | +140.3, +922.74 | −73.4, −478.52 | −55.0, −81.10 | **−7.31**, −45.05 | [−10.79, −3.54]; [−74.18, −13.33] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 251,808 | 3,437 / 3,686 | 32.0 | +135.1, +690.58 | −72.3, −362.73 | −52.4, −64.10 | **−5.93**, −25.68 | [−8.57, −3.08]; [−39.04, −8.60] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | +73,267.74, +453.4%, 2025-03-25, SPXW 31-60 5900.0P | −27,252.26, −77.6%, 2025-04-08, SPXW 31-60 5175.0P | 0.86 | 12,142,678 | 3,671 | total ≤ 0 (best 5 days +3,638,743; without them −15,595,427) |
| 0DTE→60 DTE, 15 names | holdout (opened) | +45,477.74, +143.5%, 2026-03-30, SPXW 31-60 6220.0C | −26,112.26, −90.4%, 2026-03-30, SPXW 31-60 6510.0P | 0.90 | 6,467,637 | 3,686 | total ≤ 0 (best 5 days +1,736,209; without them −8,203,846) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.33 a trade) and Robinhood's charged instead (mean $0.32). The study's fees are given beside them below. Re-pricing: exact (517,224 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 265,416 | **−7.31**, −45.05 | −7.95, −46.00 | 30.9 / 30.8 | [−10.79, −3.54] / [−11.44, −4.19] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 251,808 | **−5.93**, −25.68 | −6.73, −26.77 | 32.0 / 31.9 | [−8.57, −3.08] / [−9.38, −3.86] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration: fixed exit 100.0%
- holdout (opened): fixed exit 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | 0DTE→60 DTE, 15 names | 3,539 | 34.8 | −14.38 | −27.47 | −97,221 |
| 2013 | 0DTE→60 DTE, 15 names | 5,476 | 35.5 | −9.22 | −15.17 | −83,074 |
| 2014 | 0DTE→60 DTE, 15 names | 5,572 | 37.3 | −5.08 | −10.09 | −56,242 |
| 2015 | 0DTE→60 DTE, 15 names | 4,958 | 35.4 | −4.12 | −15.29 | −75,801 |
| 2016 | 0DTE→60 DTE, 15 names | 8,797 | 33.3 | −10.26 | −21.22 | −186,698 |
| 2017 | 0DTE→60 DTE, 15 names | 5,822 | 31.5 | −13.12 | −25.73 | −149,817 |
| 2018 | 0DTE→60 DTE, 15 names | 8,205 | 38.2 | +4.31 | +9.81 | +80,509 |
| 2019 | 0DTE→60 DTE, 15 names | 11,814 | 36.3 | −9.23 | −24.84 | −293,426 |
| 2020 | 0DTE→60 DTE, 15 names | 12,459 | 35.3 | +2.21 | −8.66 | −107,908 |
| 2021 | 0DTE→60 DTE, 15 names | 14,837 | 31.8 | −14.67 | −64.48 | −956,640 |
| 2022 | 0DTE→60 DTE, 15 names | 36,317 | 32.2 | −6.88 | −53.37 | −1,938,310 |
| 2023 | 0DTE→60 DTE, 15 names | 85,208 | 32.4 | −6.14 | −33.26 | −2,834,113 |
| 2024 | 0DTE→60 DTE, 15 names | 93,592 | 31.4 | −4.08 | −7.83 | −732,520 |
| 2025 | 0DTE→60 DTE, 15 names | 120,615 | 30.2 | −6.40 | −33.05 | −3,985,784 |
| 2026 | 0DTE→60 DTE, 15 names | 100,013 | 29.3 | −9.26 | −70.06 | −7,007,275 |

![](charts/s30d.png)

**Amendments, deviations and integrity checks.** 33 variants tried for 3 candidates.

**What it showed.** Still −6.7% a trade.

## #30e Compass features BX3e: the 14:00 exit on the physically settled names only (PASSED, Phase B)

**Folder:** `research_notes/Compass features/`. **Commits:** inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e. **Dates:** 2026-10-22.

**Hypothesis.** X3 without SPXW.

**Rule.** X3 on SPY/QQQ/singles (physical settlement).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData) (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)

**Data.** The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).

**Periods and holdouts.** exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).

**Pass rule (as pre-registered).** As 30d.

**Verdict.** PASS: holdout Δ +7.67 [+4.23, +10.69] (−11.03 with vs −18.71).

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 225,023 | 897 / 2,388 | 28.0 | +110.3, +202.19 | −60.9, −107.45 | −44.3, −19.10 | **−12.88**, −20.65 | [−15.20, −10.62]; [−27.07, −15.33] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 203,289 | 1,257 / 2,428 | 29.1 | +121.7, +149.87 | −61.4, −79.55 | −43.3, −19.10 | **−8.12**, −12.83 | [−12.22, −6.21]; [−18.15, −9.08] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | +10,634.57, +181.8%, 2022-02-04, AMZN 0DTE 3045.0C | −6,108.10, −97.0%, 2020-09-04, AMZN 0DTE 3150.0P | 0.73 | 4,646,111 | 2,388 | total ≤ 0 (best 5 days +870,133; without them −5,516,244) |
| 0DTE→60 DTE, 15 names | holdout (opened) | +7,779.71, +421.7%, 2026-07-02, MU 0DTE 1055.0P | −3,457.10, −99.3%, 2021-12-17, AMZN 0DTE 3330.0P | 0.77 | 2,772,055 | 2,418 | total ≤ 0 (best 5 days +485,048; without them −3,093,089) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.36 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (428,312 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| 0DTE→60 DTE, 15 names | exploration | 225,023 | **−12.88**, −20.65 | −15.96, −21.91 | 28.0 / 27.3 | [−15.20, −10.62] / [−18.40, −13.67] |
| 0DTE→60 DTE, 15 names | holdout (opened) | 203,289 | **−8.12**, −12.83 | −11.03, −14.09 | 29.1 / 28.4 | [−12.22, −6.21] / [−15.23, −9.12] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration: sold at the 14:00 bid 100.0%
- holdout (opened): sold at the 14:00 bid 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2017 | 0DTE→60 DTE, 15 names | 9,741 | 21.3 | −6.70 | −9.41 | −91,695 |
| 2018 | 0DTE→60 DTE, 15 names | 23,860 | 25.2 | −19.64 | −27.75 | −662,143 |
| 2019 | 0DTE→60 DTE, 15 names | 21,472 | 23.8 | −19.62 | −25.50 | −547,548 |
| 2020 | 0DTE→60 DTE, 15 names | 29,501 | 27.2 | −13.55 | −37.94 | −1,119,259 |
| 2021 | 0DTE→60 DTE, 15 names | 27,934 | 26.5 | −15.96 | −43.34 | −1,210,556 |
| 2022 | 0DTE→60 DTE, 15 names | 33,013 | 28.8 | −12.57 | −31.38 | −1,035,845 |
| 2023 | 0DTE→60 DTE, 15 names | 51,821 | 30.8 | −6.42 | −4.53 | −234,964 |
| 2024 | 0DTE→60 DTE, 15 names | 63,319 | 29.1 | −10.42 | −8.25 | −522,496 |
| 2025 | 0DTE→60 DTE, 15 names | 71,666 | 30.9 | −5.03 | −2.24 | −160,403 |
| 2026 | 0DTE→60 DTE, 15 names | 95,985 | 28.6 | −10.21 | −17.39 | −1,669,244 |

![](charts/s30e.png)

**Amendments, deviations and integrity checks.** As 30d.

**What it showed.** Still −11% a trade.

## #30f Compass features VN1 (venue SPY vs SPXW) and BC3 (V1 + X3 + D6)

**Folder:** `research_notes/Compass features/`. **Commits:** inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e. **Dates:** 2026-10-22.

**Hypothesis.** The cheaper venue, and the stacked model, lose less.

**Rule.** VN1: keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid. BC3: V1 veto + X3 exit + D6 direction.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData) (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)

**Data.** The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).

**Periods and holdouts.** exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).

**Pass rule (as pre-registered).** As 30b.

**Verdict.** PASS: VN1 holdout Δ +1.18 [+0.50, +2.20] (failed on the duplicated table); BC3 +6.77 [+4.82, +8.19] (−4.26 with vs −11.03).

**Metrics.** not available — VN1 pairs venues and BC3 needs the D6 direction feature; both are computed inside the study's screen code, and their per-trade arms are not on disk.

**Amendments, deviations and integrity checks.** VN1 failed on the first (duplicated) holdout read and passes on the corrected one.

**What it showed.** Cost and timing filters; no direction feature passed.

## #31 Compass direction: post-earnings drift in 31–60 DTE options (rerun)

**Folder:** `research_notes/Compass direction/`. **Commits:** 38b11bf / ledger code 043d723 / 94fb69d. **Dates:** 2026-10-22.

**Hypothesis.** After a report, options on the side of the earnings-day move drift in its direction (PEAD).

**Rule.** At the close after the report: the 31–60 DTE expiry nearest 45 days; buy five strike buckets on the picked side (the sign of the report-day return) at the closing ask; sell at the closing bid 10 full sessions later ($0 if no bid).

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry; the closing NBBO (EOD).

**Data.** Exploration set X: 1,601 names, 3,129 events (12,114 picked-side trades) 2019-04 → 2026-09.

**Periods and holdouts.** Exploration screen only; the 1,600 holdout names (2019-01 → 2022-12) UNOPENED.

**Pass rule (as pre-registered).** Screen: Δ (picked − both sides) > 0 with its block-20 interval clear of zero; then the holdout once.

**Verdict.** FAIL: Δ −0.90 pp [−3.53, +1.71]; the holdout is not fetched and not read.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| single names | exploration (holdout unopened) | 12,114 | 893 / 1,920 | 26.2 | +79.9, +471.35 | −60.2, −312.80 | −46.4, −85.10 | **−23.52**, −107.74 | [−27.45, −19.03]; [−135.54, −77.96] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| single names | exploration (holdout unopened) | +18,029.34, +195.5%, 2023-10-30, CMG 2023-12-15 1880.0C | −13,865.21, −72.0%, 2026-06-26, MU 2026-08-07 1040.0C | 0.53 | 1,312,036 | 1,840 | total ≤ 0 (best 5 days +160,683; without them −1,465,799) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.34 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (12,114 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| single names | exploration (holdout unopened) | 12,114 | **−23.52**, −107.74 | −24.29, −108.97 | 26.2 / 26.1 | [−27.45, −19.03] / [−28.19, −19.82] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration (holdout unopened): closing bid 10 sessions later 94.5%; no bid at exit ($0) 5.5%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2019 | single names | 702 | 29.8 | −9.07 | −40.75 | −28,604 |
| 2020 | single names | 1,187 | 19.5 | −27.14 | −168.04 | −199,461 |
| 2021 | single names | 1,485 | 28.7 | −19.96 | −60.81 | −90,303 |
| 2022 | single names | 1,549 | 28.3 | −18.58 | −125.40 | −194,237 |
| 2023 | single names | 1,520 | 25.2 | −24.32 | −54.94 | −83,511 |
| 2024 | single names | 1,604 | 28.3 | −23.90 | −106.55 | −170,913 |
| 2025 | single names | 2,170 | 27.1 | −23.81 | −112.42 | −243,953 |
| 2026 | single names | 1,897 | 23.0 | −32.14 | −155.05 | −294,133 |

![](charts/s31.png)

**Amendments, deviations and integrity checks.** Rerun for this report at 94fb69d from the stored files: screen.json equal to the committed one to the last float digit (summation order); the trade table expl_trades.parquet rewritten in the scratchpad.

**What it showed.** The picked side loses 24% of the debit a trade, no better than the other side.

## #32 Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock)

**Folder:** `research_notes/Compass H1/`. **Commits:** 38aca66 / — / 4a02144. **Dates:** 2026-10-23.

**Hypothesis.** The 15:00 → close move reverses overnight.

**Rule.** Short 100 shares at the official close if the close > the 15:00 price, long if below; exit at the next 09:30 open.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.01 a share each way ($2.00 a trade at 1×); 2× shown in the study.

**Data.** SPY 2017-01-03 → 2025-10-10, QQQ 2012-06-01 → 2025-10-10.

**Periods and holdouts.** Single test; no holdout.

**Pass rule (as pre-registered).** In each name: mean $ a trade after costs > 0 and the 20-session block interval clear of zero (both names).

**Verdict.** FAIL: SPY +$11.09 [−4.42, +28.72], QQQ +$9.42 [−0.06, +18.61].

**Metrics at Robinhood fees** (return = % of notional ($ = per 100 sh); win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | single test | 3,299 | 3,299 / 3,420 | 51.6 | +0.534, +132.20 | −0.491, −118.32 | +0.020, +2.67 | **+0.038**, +10.92 | [+0.005, +0.074]; [+1.33, +20.38] |
| SPY | single test | 2,177 | 2,177 / 2,266 | 51.2 | +0.479, +181.19 | −0.431, −165.10 | +0.014, +5.37 | **+0.035**, +12.26 | [−0.009, +0.088]; [−3.39, +28.97] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | single test | +2,401.93, +5.4%, 2024-08-02, 100 QQQ short | −1,448.25, −3.4%, 2025-04-07, 100 QQQ short | 1.19 | 8,286 | 585 | 28% |
| SPY | single test | +3,028.28, +11.2%, 2020-03-13, 100 SPY short | −1,749.48, −3.5%, 2025-04-07, 100 SPY short | 1.15 | 10,312 | 410 | 42% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.00 a trade) and Robinhood's charged instead (mean $0.63). The study's fees are given beside them below. Re-pricing: exact (5,476 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | single test | 3,299 | **+0.038**, +10.92 | +0.027, +9.42 | 51.6 / 50.5 | [+0.005, +0.074] / [−0.006, +0.064] |
| SPY | single test | 2,177 | **+0.035**, +12.26 | +0.032, +11.09 | 51.2 / 50.8 | [−0.009, +0.088] / [−0.013, +0.084] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- single test: next 09:30 open 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | QQQ | 142 | 54.2 | +0.00 | +0.06 | +9 |
| 2013 | QQQ | 247 | 57.1 | +0.06 | +4.85 | +1,197 |
| 2014 | QQQ | 244 | 50.8 | −0.02 | −1.40 | −341 |
| 2015 | QQQ | 246 | 50.4 | +0.00 | +0.00 | +1 |
| 2016 | QQQ | 248 | 47.6 | +0.03 | +3.18 | +788 |
| 2017 | QQQ | 248 | 52.8 | +0.02 | +2.62 | +649 |
| 2018 | QQQ | 247 | 46.2 | −0.04 | −6.77 | −1,673 |
| 2019 | QQQ | 248 | 44.4 | −0.07 | −12.60 | −3,125 |
| 2020 | QQQ | 247 | 54.7 | +0.19 | +39.47 | +9,749 |
| 2021 | QQQ | 247 | 55.9 | +0.06 | +18.36 | +4,535 |
| 2022 | QQQ | 249 | 53.4 | +0.13 | +37.97 | +9,454 |
| 2023 | QQQ | 246 | 52.4 | +0.04 | +12.36 | +3,041 |
| 2024 | QQQ | 248 | 54.0 | +0.10 | +42.75 | +10,601 |
| 2025 | QQQ | 192 | 49.0 | +0.00 | +6.01 | +1,154 |
| 2017 | SPY | 245 | 53.9 | +0.03 | +7.74 | +1,897 |
| 2018 | SPY | 246 | 47.6 | −0.03 | −7.42 | −1,824 |
| 2019 | SPY | 248 | 43.1 | −0.05 | −13.72 | −3,402 |
| 2020 | SPY | 251 | 57.4 | +0.21 | +61.86 | +15,526 |
| 2021 | SPY | 251 | 54.2 | +0.02 | +9.21 | +2,311 |
| 2022 | SPY | 247 | 54.3 | +0.08 | +32.83 | +8,109 |
| 2023 | SPY | 247 | 49.0 | +0.02 | +7.11 | +1,756 |
| 2024 | SPY | 249 | 52.6 | +0.05 | +23.44 | +5,836 |
| 2025 | SPY | 193 | 48.2 | −0.04 | −18.23 | −3,518 |
| 2012 | all names | 142 | 54.2 | +0.00 | +0.06 | +9 |
| 2013 | all names | 247 | 57.1 | +0.06 | +4.85 | +1,197 |
| 2014 | all names | 244 | 50.8 | −0.02 | −1.40 | −341 |
| 2015 | all names | 246 | 50.4 | +0.00 | +0.00 | +1 |
| 2016 | all names | 248 | 47.6 | +0.03 | +3.18 | +788 |
| 2017 | all names | 493 | 53.3 | +0.02 | +5.17 | +2,547 |
| 2018 | all names | 493 | 46.9 | −0.03 | −7.09 | −3,498 |
| 2019 | all names | 496 | 43.8 | −0.06 | −13.16 | −6,527 |
| 2020 | all names | 498 | 56.0 | +0.20 | +50.75 | +25,275 |
| 2021 | all names | 498 | 55.0 | +0.04 | +13.75 | +6,846 |
| 2022 | all names | 496 | 53.8 | +0.11 | +35.41 | +17,564 |
| 2023 | all names | 493 | 50.7 | +0.03 | +9.73 | +4,797 |
| 2024 | all names | 497 | 53.3 | +0.07 | +33.07 | +16,437 |
| 2025 | all names | 385 | 48.6 | −0.02 | −6.14 | −2,364 |

![](charts/s32.png)

**Amendments, deviations and integrity checks.** verify_h1.py: 50 random trades re-derived, 0 differences.

**What it showed.** The longs carry the overnight drift; the shorts lose.

## #34 Edge H3: earnings IV-crush short iron condor (single names)

**Folder:** `research_notes/Edge search/H3`. **Commits:** 001a136 / — / 34c8fd8. **Dates:** 2026-10-23.

**Hypothesis.** Implied volatility collapses across the report enough to pay a short condor.

**Rule.** Shorts at K0 ± 0.5 implied move, longs ± 1.5, first expiry after R within 14 days, sold at the closing quote before the report, bought back at the reaction session's close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Bid/ask both ways, $0.68748 a contract each way.

**Data.** Exploration: 1,601 X names, 2,209 condors 2019-04 → 2022-12.

**Periods and holdouts.** Exploration screen; holdout (1,600 H names) not fetched, UNOPENED.

**Pass rule (as pre-registered).** Screen: mean > 0 with the block interval clear of zero.

**Verdict.** FAIL: −$161.54 a condor [−180.68, −142.46] (−30.2% of max risk); at the mid −$20.

**Metrics at Robinhood fees** (return = % of max risk; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| single names | exploration (holdout unopened) | 2,209 | 554 / 957 | 31.6 | +22.3, +117.80 | −50.7, −283.90 | −20.0, −40.34 | **−27.65**, −156.97 | [−29.75, −25.26]; [−176.19, −138.32] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| single names | exploration (holdout unopened) | +1,564.55, +19.3%, 2022-04-26, CMG 2022-04-29 1270.0/1385.0P 1495.0/1605.0C | −6,535.53, −111.1%, 2022-07-26, CMG 2022-07-29 1180.0/1270.0P 1365.0/1455.0C | 0.19 | 346,757 | 956 | total ≤ 0 (best 5 days +5,046; without them −351,794) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $4.93 a trade) and Robinhood's charged instead (mean $0.36). The study's fees are given beside them below. Re-pricing: exact (2,208 trades); Robinhood fees inferred from the rule: no exit quotes kept: four legs closed at $1.00 assumed (1 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| single names | exploration (holdout unopened) | 2,209 | **−27.65**, −156.97 | −30.24, −161.54 | 31.6 / 30.3 | [−29.75, −25.26] / [−32.38, −27.80] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration (holdout unopened): quotes 100.0%; split-sized move: booked at max loss 0.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2019 | single names | 403 | 36.5 | −24.96 | −94.66 | −38,148 |
| 2020 | single names | 504 | 27.0 | −29.62 | −161.93 | −81,614 |
| 2021 | single names | 649 | 31.3 | −30.20 | −187.39 | −121,616 |
| 2022 | single names | 653 | 32.5 | −25.24 | −161.36 | −105,369 |

![](charts/s34.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** The spread and fees take the crush.

## #35 Edge H4: market intraday momentum (SPY, QQQ stock)

**Folder:** `research_notes/Edge search/H4`. **Commits:** b14b640 / — / dfa575d. **Dates:** 2026-10-23.

**Hypothesis.** The first half hour's return predicts the last half hour (Gao, Han, Li & Zhou 2018).

**Rule.** r1 = the 09:59 bar close ÷ the previous official close − 1; long 100 at the 15:30 bar open if r1 > 0, short if < 0; exit at the official close.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.005 a share entry + $0.01 auction ($1.50 a trade).

**Data.** Test 2025-10-13 → 2026-10-22 (257 sessions a name); exploration (context) SPY 2017 → 2025-10-10, QQQ 2012 → .

**Periods and holdouts.** test (the verdict) / exploration (context only, spent by S12 and others).

**Pass rule (as pre-registered).** Each name: mean > 0 with the block-20 interval clear of zero.

**Verdict.** FAIL: SPY −$2.95 [−19.01, +15.37], QQQ +$10.32 [−8.56, +35.77].

**Metrics at Robinhood fees** (return = % of notional ($ = per 100 sh); win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | exploration (context) | 3,319 | 3,319 / 3,419 | 49.4 | +0.193, +44.97 | −0.194, −47.99 | −0.004, −0.66 | **−0.003**, −2.03 | [−0.013, +0.010]; [−4.65, +1.07] |
| SPY | exploration (context) | 2,184 | 2,184 / 2,265 | 49.0 | +0.192, +72.15 | −0.190, −72.04 | −0.003, −0.99 | **−0.003**, −1.33 | [−0.018, +0.014]; [−6.76, +4.60] |
| QQQ | test 2025-10-13→2026-10-22 | 257 | 257 / 267 | 49.8 | +0.180, +119.61 | −0.152, −98.91 | −0.001, −0.77 | **+0.013**, +9.92 | [−0.017, +0.048]; [−9.77, +34.85] |
| SPY | test 2025-10-13→2026-10-22 | 257 | 257 / 267 | 45.5 | +0.125, +88.87 | −0.114, −80.60 | −0.013, −9.11 | **−0.005**, −3.45 | [−0.029, +0.019]; [−20.01, +14.24] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | exploration (context) | +780.08, +4.2%, 2020-03-13, 100 QQQ long | −751.87, −4.4%, 2020-03-18, 100 QQQ short | 0.92 | 12,257 | 1,401 | total ≤ 0 (best 5 days +3,464; without them −10,205) |
| SPY | exploration (context) | +1,249.46, +4.8%, 2020-03-13, 100 SPY long | −744.13, −2.6%, 2020-02-28, 100 SPY short | 0.96 | 9,189 | 1,417 | total ≤ 0 (best 5 days +4,114; without them −7,020) |
| QQQ | test 2025-10-13→2026-10-22 | +902.08, +1.3%, 2026-07-29, 100 QQQ short | −377.73, −0.6%, 2025-11-20, 100 QQQ long | 1.20 | 2,304 | 142 | 96% |
| SPY | test 2025-10-13→2026-10-22 | +572.95, +0.8%, 2026-07-29, 100 SPY short | −373.10, −0.5%, 2026-09-30, 100 SPY long | 0.92 | 3,175 | 240 | total ≤ 0 (best 5 days +1,735; without them −2,621) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.00 a trade) and Robinhood's charged instead (mean $0.70). The study's fees are given beside them below. Re-pricing: exact (6,017 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | exploration (context) | 3,319 | **−0.003**, −2.03 | −0.007, −2.53 | 49.4 / 48.1 | [−0.013, +0.010] / [−0.017, +0.005] |
| SPY | exploration (context) | 2,184 | **−0.003**, −1.33 | −0.003, −1.51 | 49.0 / 48.9 | [−0.018, +0.014] / [−0.018, +0.013] |
| QQQ | test 2025-10-13→2026-10-22 | 257 | **+0.013**, +9.92 | +0.014, +10.32 | 49.8 / 49.8 | [−0.017, +0.048] / [−0.016, +0.048] |
| SPY | test 2025-10-13→2026-10-22 | 257 | **−0.005**, −3.45 | −0.004, −2.95 | 45.5 / 45.5 | [−0.029, +0.019] / [−0.028, +0.020] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration (context): official close 100.0%
- test 2025-10-13→2026-10-22: official close 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | QQQ | 142 | 51.4 | −0.00 | −0.01 | −1 |
| 2013 | QQQ | 245 | 49.0 | +0.01 | +0.42 | +102 |
| 2014 | QQQ | 245 | 49.8 | +0.01 | +0.46 | +112 |
| 2015 | QQQ | 250 | 46.8 | −0.00 | −0.11 | −28 |
| 2016 | QQQ | 251 | 52.2 | −0.01 | −1.15 | −288 |
| 2017 | QQQ | 249 | 47.4 | −0.01 | −0.86 | −214 |
| 2018 | QQQ | 248 | 56.5 | +0.03 | +4.60 | +1,140 |
| 2019 | QQQ | 249 | 50.2 | −0.01 | −1.47 | −366 |
| 2020 | QQQ | 251 | 52.6 | +0.06 | +9.25 | +2,321 |
| 2021 | QQQ | 250 | 44.4 | −0.04 | −12.96 | −3,240 |
| 2022 | QQQ | 250 | 47.6 | −0.04 | −12.50 | −3,125 |
| 2023 | QQQ | 248 | 48.0 | −0.02 | −6.55 | −1,626 |
| 2024 | QQQ | 248 | 48.0 | −0.01 | −2.60 | −645 |
| 2025 | QQQ | 247 | 47.8 | −0.01 | −5.41 | −1,337 |
| 2026 | QQQ | 203 | 51.7 | +0.02 | +14.79 | +3,003 |
| 2017 | SPY | 246 | 45.1 | −0.01 | −2.24 | −550 |
| 2018 | SPY | 248 | 50.8 | −0.01 | −1.80 | −447 |
| 2019 | SPY | 248 | 51.2 | −0.01 | −1.69 | −420 |
| 2020 | SPY | 251 | 46.6 | +0.03 | +5.35 | +1,344 |
| 2021 | SPY | 251 | 43.4 | −0.03 | −14.02 | −3,519 |
| 2022 | SPY | 250 | 50.0 | −0.02 | −7.48 | −1,870 |
| 2023 | SPY | 248 | 51.2 | +0.02 | +7.07 | +1,754 |
| 2024 | SPY | 249 | 49.4 | −0.00 | −2.75 | −684 |
| 2025 | SPY | 247 | 52.2 | +0.00 | +2.51 | +621 |
| 2026 | SPY | 203 | 46.3 | −0.00 | −0.11 | −21 |
| 2012 | all names | 142 | 51.4 | −0.00 | −0.01 | −1 |
| 2013 | all names | 245 | 49.0 | +0.01 | +0.42 | +102 |
| 2014 | all names | 245 | 49.8 | +0.01 | +0.46 | +112 |
| 2015 | all names | 250 | 46.8 | −0.00 | −0.11 | −28 |
| 2016 | all names | 251 | 52.2 | −0.01 | −1.15 | −288 |
| 2017 | all names | 495 | 46.3 | −0.01 | −1.54 | −764 |
| 2018 | all names | 496 | 53.6 | +0.01 | +1.40 | +693 |
| 2019 | all names | 497 | 50.7 | −0.01 | −1.58 | −786 |
| 2020 | all names | 502 | 49.6 | +0.04 | +7.30 | +3,665 |
| 2021 | all names | 501 | 43.9 | −0.03 | −13.49 | −6,759 |
| 2022 | all names | 500 | 48.8 | −0.03 | −9.99 | −4,995 |
| 2023 | all names | 496 | 49.6 | +0.00 | +0.26 | +129 |
| 2024 | all names | 497 | 48.7 | −0.01 | −2.67 | −1,328 |
| 2025 | all names | 494 | 50.0 | −0.00 | −1.45 | −716 |
| 2026 | all names | 406 | 49.0 | +0.01 | +7.34 | +2,981 |

![](charts/s35.png)

**Amendments, deviations and integrity checks.** A-priori MDE $28–37 a trade: weak evidence either way.

**What it showed.** No momentum after costs.

## #37a Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED

**Folder:** `research_notes/Edge search/H7_H8_H9`. **Commits:** edca472 / forward rule fcc1f4d / 6c94bb8; wired 712b0ad; baseline 827bd5e. **Dates:** 2026-10-23.

**Hypothesis.** Stocks drift up in the 24 hours before a scheduled FOMC statement (Lucca & Moench 2015).

**Rule.** Buy 100 at the official close of the session before each scheduled 2:00 pm statement (2013-03-20 on); sell at the 13:58 bar's close on the statement day.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.01 a share auction entry + $0.005 exit ($1.50 a trade).

**Data.** SPY 77 statements 2017-02 → 2026-09; QQQ 108 2013-03 → 2026-09.

**Periods and holdouts.** Single test (no study had read the signed pre-FOMC return); forward from 2026-10-28 (N 366 SPY / 483 QQQ).

**Pass rule (as pre-registered).** Each name: mean > 0 with the block-20 interval (calendar sessions, 2,000 draws, seed 20261023) clear of zero at 1× and 2×; Bonferroni m = 13 for an EDGE.

**Verdict.** PASS both names: SPY +$70.43 [+14.64, +129.31], QQQ +$69.59 [+23.10, +122.14]; QQQ clears Bonferroni (EDGE under rule 5); not "works" before its forward N.

**Metrics at Robinhood fees** (return = % of notional ($ = per 100 sh); win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | single test | 108 | 108 / 3,462 | 61.1 | +0.649, +195.59 | −0.469, −127.34 | +0.115, +18.20 | **+0.214**, +70.01 | [+0.053, +0.358]; [+18.16, +115.30] |
| SPY | single test | 77 | 77 / 2,487 | 55.8 | +0.563, +224.77 | −0.280, −124.53 | +0.062, +15.94 | **+0.191**, +70.54 | [+0.060, +0.355]; [+11.25, +131.20] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | single test | +1,161.51, +2.5%, 2024-07-30, 100 QQQ long, FOMC 2024-07-31 | −542.91, −0.8%, 2026-07-28, 100 QQQ long, FOMC 2026-07-29 | 2.41 | 1,001 | 1,370 | 56% |
| SPY | single test | +822.94, +1.5%, 2024-07-30, 100 SPY long, FOMC 2024-07-31 | −620.30, −1.6%, 2021-01-26, 100 SPY long, FOMC 2021-01-27 | 2.28 | 1,068 | 295 | 66% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.00 a trade) and Robinhood's charged instead (mean $0.71). The study's fees are given beside them below. Re-pricing: exact (185 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | single test | 108 | **+0.214**, +70.01 | +0.210, +69.59 | 61.1 / 61.1 | [+0.053, +0.358] / [+0.049, +0.355] |
| SPY | single test | 77 | **+0.191**, +70.54 | +0.190, +70.43 | 55.8 / 55.8 | [+0.060, +0.355] / [+0.059, +0.355] |

**Random baseline** (as the study computed it, at its own fees): descriptive baseline against every non-FOMC session over the same clock window (H7_BASELINE.md, 827bd5e), no new verdict.

**Exit reasons (share of trades):**

- single test: 13:58 bar close on the statement day 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2013 | QQQ | 7 | 42.9 | −0.10 | −9.11 | −64 |
| 2014 | QQQ | 8 | 50.0 | −0.04 | −2.65 | −21 |
| 2015 | QQQ | 8 | 62.5 | +0.13 | +13.32 | +107 |
| 2016 | QQQ | 8 | 62.5 | −0.19 | −20.01 | −160 |
| 2017 | QQQ | 8 | 62.5 | −0.02 | −3.88 | −31 |
| 2018 | QQQ | 8 | 75.0 | +0.23 | +38.81 | +310 |
| 2019 | QQQ | 8 | 50.0 | +0.19 | +31.29 | +250 |
| 2020 | QQQ | 7 | 85.7 | +1.12 | +273.44 | +1,914 |
| 2021 | QQQ | 8 | 37.5 | −0.34 | −109.57 | −877 |
| 2022 | QQQ | 8 | 87.5 | +1.28 | +399.64 | +3,197 |
| 2023 | QQQ | 8 | 62.5 | +0.16 | +51.44 | +412 |
| 2024 | QQQ | 8 | 62.5 | +0.46 | +229.10 | +1,833 |
| 2025 | QQQ | 8 | 50.0 | +0.04 | +20.63 | +165 |
| 2026 | QQQ | 6 | 66.7 | +0.11 | +87.60 | +526 |
| 2017 | SPY | 8 | 37.5 | +0.00 | +0.97 | +8 |
| 2018 | SPY | 8 | 62.5 | +0.17 | +44.34 | +355 |
| 2019 | SPY | 8 | 50.0 | −0.01 | −4.28 | −34 |
| 2020 | SPY | 7 | 85.7 | +0.91 | +285.49 | +1,998 |
| 2021 | SPY | 8 | 12.5 | −0.26 | −100.50 | −804 |
| 2022 | SPY | 8 | 87.5 | +0.82 | +332.64 | +2,661 |
| 2023 | SPY | 8 | 62.5 | +0.07 | +30.91 | +247 |
| 2024 | SPY | 8 | 62.5 | +0.30 | +175.36 | +1,403 |
| 2025 | SPY | 8 | 62.5 | +0.08 | +44.94 | +360 |
| 2026 | SPY | 6 | 33.3 | −0.18 | −127.04 | −762 |
| 2013 | all names | 7 | 42.9 | −0.10 | −9.11 | −64 |
| 2014 | all names | 8 | 50.0 | −0.04 | −2.65 | −21 |
| 2015 | all names | 8 | 62.5 | +0.13 | +13.32 | +107 |
| 2016 | all names | 8 | 62.5 | −0.19 | −20.01 | −160 |
| 2017 | all names | 16 | 50.0 | −0.01 | −1.46 | −23 |
| 2018 | all names | 16 | 68.8 | +0.20 | +41.58 | +665 |
| 2019 | all names | 16 | 50.0 | +0.09 | +13.51 | +216 |
| 2020 | all names | 14 | 85.7 | +1.01 | +279.46 | +3,912 |
| 2021 | all names | 16 | 25.0 | −0.30 | −105.03 | −1,681 |
| 2022 | all names | 16 | 87.5 | +1.05 | +366.14 | +5,858 |
| 2023 | all names | 16 | 62.5 | +0.11 | +41.18 | +659 |
| 2024 | all names | 16 | 62.5 | +0.38 | +202.23 | +3,236 |
| 2025 | all names | 16 | 56.2 | +0.06 | +32.79 | +525 |
| 2026 | all names | 12 | 50.0 | −0.03 | −19.72 | −237 |

![](charts/s37a.png)

**Amendments, deviations and integrity checks.** The gross is the night (close → 09:30 ≈ +$73–74); QQQ before March 2016 −$3.00.

**What it showed.** About +$70 a trade (0.2% of notional) in both names, carried overnight.

## #37b Edge H8: turn of the month (SPY, QQQ stock)

**Folder:** `research_notes/Edge search/H7_H8_H9`. **Commits:** edca472 / — / 6c94bb8. **Dates:** 2026-10-23.

**Hypothesis.** Returns concentrate from the last trading day to the third of the new month.

**Rule.** Buy 100 at the official close of the second-to-last session of each month, sell at the official close of the third session of the next.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.01 a share each way ($2.00 a trade).

**Data.** SPY 117 turns 2017-01 → 2026-09; QQQ 172 2012-06 → 2026-09.

**Periods and holdouts.** Single test.

**Pass rule (as pre-registered).** As H7.

**Verdict.** SPY FAIL; QQQ PASS at 1× only (+$110.22 [+0.84, +218.26]) — not an EDGE.

**Metrics at Robinhood fees** (return = % of notional ($ = per 100 sh); win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| QQQ | single test | 172 | 172 / 3,651 | 59.3 | +1.854, +505.33 | −1.727, −461.97 | +0.419, +82.00 | **+0.397**, +111.66 | [+0.016, +0.705]; [−9.31, +213.25] |
| SPY | single test | 117 | 117 / 2,498 | 60.7 | +1.482, +608.65 | −1.488, −595.82 | +0.417, +155.21 | **+0.315**, +135.10 | [−0.049, +0.646]; [−19.75, +265.54] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| QQQ | single test | +3,373.50, +4.9%, 2026-07-30, 100 QQQ long, turn 2026-07 | −2,369.27, −3.8%, 2026-01-29, 100 QQQ long, turn 2026-01 | 1.59 | 4,227 | 865 | 63% |
| SPY | single test | +2,808.39, +3.8%, 2026-07-30, 100 SPY long, turn 2026-07 | −2,463.09, −4.5%, 2024-07-30, 100 SPY long, turn 2024-07 | 1.58 | 4,623 | 498 | 66% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $2.00 a trade) and Robinhood's charged instead (mean $0.70). The study's fees are given beside them below. Re-pricing: exact (289 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| QQQ | single test | 172 | **+0.397**, +111.66 | +0.387, +110.22 | 59.3 / 59.3 | [+0.016, +0.705] / [+0.006, +0.694] |
| SPY | single test | 117 | **+0.315**, +135.10 | +0.311, +134.00 | 60.7 / 60.7 | [−0.049, +0.646] / [−0.052, +0.642] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- single test: official close, 3rd session 100.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2012 | QQQ | 7 | 71.4 | +1.65 | +105.45 | +738 |
| 2013 | QQQ | 12 | 66.7 | +0.44 | +29.33 | +352 |
| 2014 | QQQ | 12 | 50.0 | −0.17 | −20.55 | −247 |
| 2015 | QQQ | 12 | 41.7 | −0.17 | −25.75 | −309 |
| 2016 | QQQ | 12 | 50.0 | +0.05 | +3.41 | +41 |
| 2017 | QQQ | 12 | 66.7 | +0.50 | +73.51 | +882 |
| 2018 | QQQ | 12 | 58.3 | +0.19 | +25.29 | +303 |
| 2019 | QQQ | 12 | 66.7 | +0.46 | +75.09 | +901 |
| 2020 | QQQ | 12 | 66.7 | +1.68 | +414.53 | +4,974 |
| 2021 | QQQ | 12 | 50.0 | −0.24 | −120.50 | −1,446 |
| 2022 | QQQ | 12 | 50.0 | −0.19 | −61.99 | −744 |
| 2023 | QQQ | 12 | 58.3 | +0.61 | +151.75 | +1,821 |
| 2024 | QQQ | 12 | 58.3 | +0.17 | +91.68 | +1,100 |
| 2025 | QQQ | 12 | 66.7 | +0.27 | +165.08 | +1,981 |
| 2026 | QQQ | 9 | 77.8 | +1.50 | +984.12 | +8,857 |
| 2017 | SPY | 12 | 75.0 | +0.42 | +106.38 | +1,277 |
| 2018 | SPY | 12 | 58.3 | −0.17 | −58.17 | −698 |
| 2019 | SPY | 12 | 66.7 | +0.25 | +59.99 | +720 |
| 2020 | SPY | 12 | 75.0 | +1.25 | +418.64 | +5,024 |
| 2021 | SPY | 12 | 41.7 | +0.06 | +2.17 | +26 |
| 2022 | SPY | 12 | 50.0 | −0.14 | −68.36 | −820 |
| 2023 | SPY | 12 | 58.3 | +0.48 | +175.34 | +2,104 |
| 2024 | SPY | 12 | 58.3 | −0.11 | −60.73 | −729 |
| 2025 | SPY | 12 | 58.3 | +0.11 | +79.77 | +957 |
| 2026 | SPY | 9 | 66.7 | +1.25 | +882.91 | +7,946 |
| 2012 | all names | 7 | 71.4 | +1.65 | +105.45 | +738 |
| 2013 | all names | 12 | 66.7 | +0.44 | +29.33 | +352 |
| 2014 | all names | 12 | 50.0 | −0.17 | −20.55 | −247 |
| 2015 | all names | 12 | 41.7 | −0.17 | −25.75 | −309 |
| 2016 | all names | 12 | 50.0 | +0.05 | +3.41 | +41 |
| 2017 | all names | 24 | 70.8 | +0.46 | +89.95 | +2,159 |
| 2018 | all names | 24 | 58.3 | +0.01 | −16.44 | −395 |
| 2019 | all names | 24 | 66.7 | +0.35 | +67.54 | +1,621 |
| 2020 | all names | 24 | 70.8 | +1.47 | +416.58 | +9,998 |
| 2021 | all names | 24 | 45.8 | −0.09 | −59.17 | −1,420 |
| 2022 | all names | 24 | 50.0 | −0.16 | −65.18 | −1,564 |
| 2023 | all names | 24 | 58.3 | +0.55 | +163.54 | +3,925 |
| 2024 | all names | 24 | 58.3 | +0.03 | +15.47 | +371 |
| 2025 | all names | 24 | 62.5 | +0.19 | +122.43 | +2,938 |
| 2026 | all names | 18 | 72.2 | +1.37 | +933.52 | +16,803 |

![](charts/s37b.png)

**Amendments, deviations and integrity checks.** The nine 2026 turns are about half of each total.

**What it showed.** Positive means, intervals at or through zero.

## #36 Edge H5 (SPY − SPXW late straddle) and H6 (monthly put spreads), forward only

**Folder:** `research_notes/Edge search/`. **Commits:** e114e30 / — / wired 23c0cc3. **Dates:** 2026-10-23.

**Hypothesis.** (See the prereg.)

**Rule.** (See the prereg.)

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** Forward only.

**Periods and holdouts.** Forward; no historical read.

**Pass rule (as pre-registered).** At N forward trades only.

**Verdict.** No verdict.

**Metrics.** not available — forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has been counted. H5: no forward session read yet (N = 1,326 sessions); H6: entries from 2026-11-02 (N = 449 months). Their historical reads are spent (the SPXW report, S17).

**Amendments, deviations and integrity checks.** —

**What it showed.** Nothing to report yet.

## #38 Edge H9: overnight drift (forward only, withdrawn)

**Folder:** `research_notes/Edge search/`. **Commits:** edca472 / — / wired 712b0ad, removed c68f389. **Dates:** 2026-10-23.

**Hypothesis.** (See the prereg.)

**Rule.** (See the prereg.)

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** Forward only.

**Periods and holdouts.** Forward; no historical read.

**Pass rule (as pre-registered).** At N forward trades only.

**Verdict.** No verdict.

**Metrics.** not available — forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has been counted. Withdrawn by the owner 2026-10-23 (c68f389) before any forward row was written; the registered rule edca472 is unchanged.

**Amendments, deviations and integrity checks.** —

**What it showed.** Nothing to report yet.

## #39 Compass scanner (score ≥ 80, SPY/QQQ/IWM 0DTE)

**Folder:** `research_notes/Compass scanner/`. **Commits:** 142fcf4 / — / 9e3888e. **Dates:** 2026-10-23.

**Hypothesis.** The owner's scanner score (RSI/VWAP/RVOL/structure) gives a forward move worth an option trade.

**Rule.** Signal check first: the underlying's forward return after a signal vs non-signal minutes; only then the option P&L.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** SPY/QQQ/IWM bars, Pick 2017-07-05 → 2022-11-18 and the option layer's Pick.

**Periods and holdouts.** Pick / Check; the 28 holdout months and AMD/AVGO UNOPENED.

**Pass rule (as pre-registered).** At 15 or 30 minutes: excess > 0 with its block-20 interval clear of zero and a positive signal mean.

**Verdict.** FAIL at the gate: 15 min −0.30 bp [−0.56, −0.07] (wrong side); 30 min −0.19 bp [−0.57, +0.21]. The study stopped.

**Metrics.** not available — signal-only: the gate failed before any option was priced, so trades, win rate, average win/loss, biggest win/loss, profit factor, drawdown, top-5 share and by-year are not available; no exit or option P&L was ever read.

**Amendments, deviations and integrity checks.** No held-out month read for an outcome.

**What it showed.** The scanner's signals do not move the underlying their way.

## #40a Compass EMA ladder: PREVIEW 2025-03, 13 versions (rerun)

**Folder:** `research_notes/Compass EMA ladder/`. **Commits:** 0dd8c5d / — / cb79c23. **Dates:** 2026-10-23.

**Hypothesis.** The owner's EMA ladder entries on 0DTE options make money.

**Rule.** EMA 9 / ladder L1 (V1, the preview's base) and V2–V13 (one change each); the best-R/R execution contract; exits per PREREG_EMA_LADDER §3.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 a contract each way; ask in, bid out; bid 0 → $0, no exit fee.

**Data.** SPY, QQQ, IWM 0DTE, 21 sessions 2025-03-03 → 31 (inside Pick, not held out).

**Periods and holdouts.** PREVIEW, no verdict; the full study was never run; the 28-month holdout UNOPENED for this rule.

**Pass rule (as pre-registered).** None for a preview (the study's rule waits for the full run).

**Verdict.** PREVIEW: every version loses.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| V1 | preview 2025-03 | 2,781 | 21 / 21 | 18.6 | +34.9, +12.50 | −14.0, −4.68 | −10.7, −3.10 | **−4.89**, −1.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V10 | preview 2025-03 | 1,996 | 21 / 21 | 19.9 | +31.0, +11.89 | −12.4, −4.74 | −9.7, −3.10 | **−3.79**, −1.43 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V11 | preview 2025-03 | 2,765 | 21 / 21 | 18.7 | +35.1, +12.54 | −13.8, −4.71 | −10.5, −3.10 | **−4.67**, −1.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V12 | preview 2025-03 | 2,350 | 21 / 21 | 20.7 | +31.3, +15.34 | −12.2, −6.01 | −9.1, −4.10 | **−3.21**, −1.59 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V13 | preview 2025-03 | 2,794 | 21 / 21 | 23.8 | +23.0, +31.86 | −10.1, −12.08 | −6.6, −7.10 | **−2.23**, −1.64 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V2 | preview 2025-03 | 768 | 21 / 21 | 13.9 | +83.4, +30.95 | −28.2, −10.04 | −23.5, −7.10 | **−12.66**, −4.33 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V3 | preview 2025-03 | 253 | 21 / 21 | 11.5 | +156.1, +57.24 | −43.3, −17.44 | −40.3, −13.10 | **−20.41**, −8.88 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V4 | preview 2025-03 | 2,214 | 21 / 21 | 14.1 | +61.7, +22.11 | −15.1, −5.08 | −12.4, −4.10 | **−4.22**, −1.24 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V5 | preview 2025-03 | 511 | 21 / 21 | 11.4 | +132.7, +43.61 | −30.7, −11.33 | −28.0, −9.10 | **−12.12**, −5.09 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V6 | preview 2025-03 | 192 | 21 / 21 | 8.9 | +223.3, +90.66 | −46.9, −19.72 | −44.8, −16.10 | **−22.97**, −9.95 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V7 | preview 2025-03 | 2,749 | 21 / 21 | 18.6 | +34.9, +12.56 | −13.9, −4.69 | −10.7, −3.10 | **−4.86**, −1.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V8 | preview 2025-03 | 2,101 | 21 / 21 | 17.8 | +42.0, +15.45 | −14.1, −4.68 | −11.1, −3.10 | **−4.16**, −1.11 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V9 | preview 2025-03 | 2,076 | 21 / 21 | 17.8 | +42.1, +15.56 | −14.1, −4.69 | −11.1, −3.10 | **−4.09**, −1.09 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| V1 | preview 2025-03 | +148.90, +330.9%, 2025-03-28, QQQ 473P m34 | −30.10, −38.6%, 2025-03-05, QQQ 486P m24 | 0.61 | 4,124 | 21 | total ≤ 0 (best 5 days −132; without them −3,992) |
| V10 | preview 2025-03 | +148.90, +330.9%, 2025-03-28, QQQ 473P m34 | −30.10, −38.6%, 2025-03-05, QQQ 486P m24 | 0.62 | 2,864 | 21 | total ≤ 0 (best 5 days +243; without them −3,106) |
| V11 | preview 2025-03 | +148.90, +330.9%, 2025-03-28, QQQ 473P m34 | −30.10, −38.6%, 2025-03-05, QQQ 486P m24 | 0.61 | 4,094 | 21 | total ≤ 0 (best 5 days −130; without them −3,965) |
| V12 | preview 2025-03 | +148.90, +330.9%, 2025-03-28, QQQ 473P m34 | −40.10, −55.7%, 2025-03-07, QQQ 489P m346 | 0.67 | 3,746 | 21 | total ≤ 0 (best 5 days +65; without them −3,812) |
| V13 | preview 2025-03 | +358.89, +212.4%, 2025-03-03, QQQ 509P m195 | −97.10, −29.2%, 2025-03-05, QQQ 495P m24 | 0.82 | 4,731 | 21 | total ≤ 0 (best 5 days +1,476; without them −6,058) |
| V2 | preview 2025-03 | +248.90, +607.1%, 2025-03-17, QQQ 482C m229 | −46.10, −59.9%, 2025-03-11, QQQ 483C m18 | 0.50 | 3,322 | 21 | total ≤ 0 (best 5 days +328; without them −3,651) |
| V3 | preview 2025-03 | +306.90, +682.0%, 2025-03-28, QQQ 473P m30 | −145.10, −61.0%, 2025-03-03, QQQ 506P m30 | 0.43 | 2,769 | 21 | total ≤ 0 (best 5 days +902; without them −3,147) |
| V4 | preview 2025-03 | +495.89, +1,549.7%, 2025-03-03, QQQ 501P m317 | −34.10, −51.7%, 2025-03-07, QQQ 479P m209 | 0.72 | 3,754 | 19 | total ≤ 0 (best 5 days +1,022; without them −3,758) |
| V5 | preview 2025-03 | +288.90, +656.6%, 2025-03-28, QQQ 473P m35 | −45.10, −64.4%, 2025-03-11, QQQ 463P m90 | 0.49 | 3,302 | 19 | total ≤ 0 (best 5 days +968; without them −3,570) |
| V6 | preview 2025-03 | +307.90, +699.8%, 2025-03-28, QQQ 473P m35 | −145.10, −61.0%, 2025-03-03, QQQ 506P m30 | 0.45 | 2,887 | 21 | total ≤ 0 (best 5 days +1,039; without them −2,949) |
| V7 | preview 2025-03 | +148.90, +330.9%, 2025-03-28, QQQ 473P m34 | −30.10, −38.6%, 2025-03-05, QQQ 486P m24 | 0.61 | 4,068 | 21 | total ≤ 0 (best 5 days −132; without them −3,935) |
| V8 | preview 2025-03 | +377.90, +944.7%, 2025-03-03, QQQ 502P m316 | −27.10, −51.1%, 2025-03-19, QQQ 471P m269 | 0.71 | 3,090 | 20 | total ≤ 0 (best 5 days +899; without them −3,221) |
| V9 | preview 2025-03 | +377.90, +944.7%, 2025-03-03, QQQ 502P m316 | −27.10, −51.1%, 2025-03-19, QQQ 471P m269 | 0.72 | 3,037 | 20 | total ≤ 0 (best 5 days +899; without them −3,168) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.37 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (23,550 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| V1 | preview 2025-03 | 2,781 | **−4.89**, −1.48 | −9.20, −2.76 | 18.6 / 15.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V10 | preview 2025-03 | 1,996 | **−3.79**, −1.43 | −7.62, −2.71 | 19.9 / 17.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V11 | preview 2025-03 | 2,765 | **−4.67**, −1.48 | −8.88, −2.76 | 18.7 / 15.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V12 | preview 2025-03 | 2,350 | **−3.21**, −1.59 | −5.91, −2.87 | 20.7 / 18.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V13 | preview 2025-03 | 2,794 | **−2.23**, −1.64 | −3.61, −2.91 | 23.8 / 22.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V2 | preview 2025-03 | 768 | **−12.66**, −4.33 | −16.78, −5.60 | 13.9 / 13.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V3 | preview 2025-03 | 253 | **−20.41**, −8.88 | −24.32, −10.15 | 11.5 / 10.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V4 | preview 2025-03 | 2,214 | **−4.22**, −1.24 | −8.50, −2.51 | 14.1 / 12.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V5 | preview 2025-03 | 511 | **−12.12**, −5.09 | −16.15, −6.37 | 11.4 / 11.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V6 | preview 2025-03 | 192 | **−22.97**, −9.95 | −26.68, −11.22 | 8.9 / 8.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V7 | preview 2025-03 | 2,749 | **−4.86**, −1.48 | −9.15, −2.75 | 18.6 / 15.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V8 | preview 2025-03 | 2,101 | **−4.16**, −1.11 | −8.50, −2.38 | 17.8 / 14.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V9 | preview 2025-03 | 2,076 | **−4.09**, −1.09 | −8.40, −2.37 | 17.8 / 14.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- preview 2025-03: signal 99.6%; 15:58 0.2%; 14:00 0.2%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | V1 | 2,781 | 18.6 | −4.89 | −1.48 | −4,124 |
| 2025 | V10 | 1,996 | 19.9 | −3.79 | −1.43 | −2,864 |
| 2025 | V11 | 2,765 | 18.7 | −4.67 | −1.48 | −4,094 |
| 2025 | V12 | 2,350 | 20.7 | −3.21 | −1.59 | −3,746 |
| 2025 | V13 | 2,794 | 23.8 | −2.23 | −1.64 | −4,582 |
| 2025 | V2 | 768 | 13.9 | −12.66 | −4.33 | −3,322 |
| 2025 | V3 | 253 | 11.5 | −20.41 | −8.88 | −2,245 |
| 2025 | V4 | 2,214 | 14.1 | −4.22 | −1.24 | −2,736 |
| 2025 | V5 | 511 | 11.4 | −12.12 | −5.09 | −2,602 |
| 2025 | V6 | 192 | 8.9 | −22.97 | −9.95 | −1,910 |
| 2025 | V7 | 2,749 | 18.6 | −4.86 | −1.48 | −4,068 |
| 2025 | V8 | 2,101 | 17.8 | −4.16 | −1.11 | −2,322 |
| 2025 | V9 | 2,076 | 17.8 | −4.09 | −1.09 | −2,269 |
| 2025 | all names | 23,550 | 18.5 | −4.81 | −1.74 | −40,885 |

![](charts/s40a.png)

**Amendments, deviations and integrity checks.** Rerun for this report at cb79c23/e9d13c0 from the stored files: preview_2025-03.json byte-identical to the original run (sha256 81edab0c934effe5…).

**What it showed.** All 13 versions lose 3.6–26.7% of premium a trade in the month.

## #40b Compass EMA ladder: "take profits are the nearest EMAs" PREVIEW (E1 ATM, E2 best-R/R)

**Folder:** `research_notes/Compass EMA ladder/`. **Commits:** rule aad56cf / — / e9d13c0. **Dates:** 2026-10-23.

**Hypothesis.** Targets at the nearest EMAs rescue the entries.

**Rule.** E1: the ATM contract (3% spread veto); E2: the best-R/R contract (3% cap); targets at the nearest EMAs, exits on the ATM chart.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As 40a.

**Data.** 2025-02 (19 sessions, fresh) and 2025-03 (21, seen before).

**Periods and holdouts.** PREVIEW, no verdict.

**Pass rule (as pre-registered).** None.

**Verdict.** PREVIEW: both versions lose in both months.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| E1 | preview 2025-02 (fresh) | 1,761 | 19 / 20 | 31.8 | +16.0, +16.99 | −9.3, −9.71 | −5.5, −4.10 | **−1.25**, −1.22 | n/a (< 60 sessions); n/a (< 60 sessions) |
| E2 | preview 2025-02 (fresh) | 1,544 | 19 / 20 | 29.7 | +19.7, +9.11 | −11.6, −5.36 | −7.6, −3.10 | **−2.34**, −1.07 | n/a (< 60 sessions); n/a (< 60 sessions) |
| E1 | preview 2025-03 (seen before) | 2,179 | 21 / 21 | 33.2 | +16.2, +23.00 | −9.8, −13.06 | −5.6, −6.10 | **−1.14**, −1.08 | n/a (< 60 sessions); n/a (< 60 sessions) |
| E2 | preview 2025-03 (seen before) | 2,044 | 21 / 21 | 31.3 | +20.1, +9.86 | −12.1, −5.96 | −7.8, −4.10 | **−2.06**, −1.01 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| E1 | preview 2025-02 (fresh) | +176.90, +83.1%, 2025-02-03, SPY 592C m52 | −85.10, −60.4%, 2025-02-07, QQQ 527.5C m77 | 0.82 | 2,149 | 20 | total ≤ 0 (best 5 days +571; without them −2,720) |
| E2 | preview 2025-02 (fresh) | +80.90, +120.7%, 2025-02-25, SPY 596P m359 | −30.10, −61.4%, 2025-02-07, QQQ 530C m77 | 0.72 | 1,649 | 20 | total ≤ 0 (best 5 days +103; without them −1,752) |
| E1 | preview 2025-03 (seen before) | +140.90, +134.2%, 2025-03-19, QQQ 484P m348 | −63.10, −21.5%, 2025-03-11, QQQ 473P m120 | 0.88 | 2,888 | 16 | total ≤ 0 (best 5 days +947; without them −3,305) |
| E2 | preview 2025-03 (seen before) | +109.90, +144.6%, 2025-03-05, QQQ 502P m346 | −23.10, −30.4%, 2025-03-13, QQQ 466P m42 | 0.75 | 2,068 | 21 | total ≤ 0 (best 5 days +61; without them −2,129) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $1.37 a trade) and Robinhood's charged instead (mean $0.10). The study's fees are given beside them below. Re-pricing: exact (7,528 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| E1 | preview 2025-02 (fresh) | 1,761 | **−1.25**, −1.22 | −2.75, −2.49 | 31.8 / 30.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| E2 | preview 2025-02 (fresh) | 1,544 | **−2.34**, −1.07 | −5.21, −2.34 | 29.7 / 27.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| E1 | preview 2025-03 (seen before) | 2,179 | **−1.14**, −1.08 | −2.28, −2.36 | 33.2 / 32.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| E2 | preview 2025-03 (seen before) | 2,044 | **−2.06**, −1.01 | −4.76, −2.29 | 31.3 / 29.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- preview 2025-02 (fresh): stop 72.4%; target 27.6%
- preview 2025-03 (seen before): stop 70.3%; target 29.7%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | E1 | 3,940 | 32.6 | −1.19 | −1.14 | −4,506 |
| 2025 | E2 | 3,588 | 30.6 | −2.18 | −1.04 | −3,717 |
| 2025 | all names | 7,528 | 31.6 | −1.66 | −1.09 | −8,223 |

![](charts/s40b.png)

**Amendments, deviations and integrity checks.** Rerun byte-identical (targets_2025-02.json 6de804ea3ddfa9d5…, targets_2025-03.json 2b005e352e86e126…).

**What it showed.** E1 −2.3 to −2.8% and E2 −4.8 to −5.2% of premium a trade.

## #41a EMA system v0: PREVIEW on 2026-10-12 → 16 (5 sessions)

**Folder:** `research_notes/EMA system/`. **Commits:** af32405 / — / 8765f71. **Dates:** 2026-10-23.

**Hypothesis.** The owner's EMA options system as specified (v0 defaults pinned).

**Rule.** RULEBOOK_v0.md: Config A/B entries, exits X1 (+1R), X2 (+2R), X3 (runner), X4; SPXW (SPX prints), SPY, QQQ, IWM.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** $0.68748 SPY/QQQ/IWM; SPXW $1.18748/$1.27748; ask in, bid out.

**Data.** 5 full sessions 2026-10-12 → 16 (a falling week: SPY −1.96%).

**Periods and holdouts.** PREVIEW, no verdict.

**Pass rule (as pre-registered).** None.

**Verdict.** PREVIEW: every row net positive in a falling week, 86% of trades puts.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| Config A X1 | preview 2026-10-12→16 | 57 | 5 / 5 | 61.4 | +42.2, +135.86 | −36.9, −102.47 | +26.5, +33.89 | **+11.68**, +43.87 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X2 | preview 2026-10-12→16 | 53 | 5 / 5 | 49.1 | +76.2, +233.00 | −40.8, −102.23 | −13.2, −10.10 | **+16.56**, +62.22 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X3 | preview 2026-10-12→16 | 48 | 5 / 5 | 29.2 | +136.9, +561.09 | −33.8, −100.48 | −22.8, −27.70 | **+15.96**, +92.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X4 | preview 2026-10-12→16 | 48 | 5 / 5 | 33.3 | +90.3, +3,192.34 | −31.9, −911.52 | −20.4, −221.49 | **+8.86**, +456.43 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X1 | preview 2026-10-12→16 | 55 | 5 / 5 | 63.6 | +39.6, +126.18 | −37.9, −105.20 | +26.8, +33.89 | **+11.39**, +42.04 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X2 | preview 2026-10-12→16 | 49 | 5 / 5 | 46.9 | +71.3, +209.81 | −41.4, −101.50 | −16.9, −11.12 | **+11.51**, +44.62 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X3 | preview 2026-10-12→16 | 46 | 5 / 5 | 28.3 | +125.6, +597.50 | −34.3, −100.00 | −23.6, −29.17 | **+10.90**, +97.12 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X4 | preview 2026-10-12→16 | 46 | 5 / 5 | 32.6 | +82.5, +3,362.13 | −32.7, −906.58 | −21.8, −236.46 | **+4.82**, +485.39 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| Config A X1 | preview 2026-10-12→16 | +717.74, +69.7%, 2026-10-14, SPXW 7770.0P 09:53 | −772.26, −51.1%, 2026-10-15, SPXW 7665.0P 09:55 | 2.11 | 618 | 2 | 100% |
| Config A X2 | preview 2026-10-12→16 | +1,427.74, +138.6%, 2026-10-14, SPXW 7770.0P 09:53 | −527.26, −65.1%, 2026-10-16, SPXW 7640.0P 14:37 | 2.19 | 724 | 2 | 100% |
| Config A X3 | preview 2026-10-12→16 | +3,277.74, +337.9%, 2026-10-16, SPXW 7715.0P 11:42 | −527.26, −65.1%, 2026-10-16, SPXW 7640.0P 14:37 | 2.30 | 605 | 2 | 100% |
| Config A X4 | preview 2026-10-12→16 | +21,707.39, +210.8%, 2026-10-14, SPXW 7770.0P 09:53 | −3,602.61, −44.5%, 2026-10-16, SPXW 7640.0P 14:37 | 1.75 | 5,442 | 2 | 100% |
| Config B X1 | preview 2026-10-12→16 | +717.74, +69.7%, 2026-10-14, SPXW 7770.0P 09:53 | −772.26, −51.1%, 2026-10-15, SPXW 7665.0P 09:55 | 2.10 | 618 | 2 | 100% |
| Config B X2 | preview 2026-10-12→16 | +1,427.74, +138.6%, 2026-10-14, SPXW 7770.0P 09:53 | −527.26, −65.1%, 2026-10-16, SPXW 7640.0P 14:37 | 1.83 | 602 | 2 | 100% |
| Config B X3 | preview 2026-10-12→16 | +3,277.74, +337.9%, 2026-10-16, SPXW 7715.0P 11:42 | −527.26, −65.1%, 2026-10-16, SPXW 7640.0P 14:37 | 2.35 | 572 | 2 | 100% |
| Config B X4 | preview 2026-10-12→16 | +21,707.39, +210.8%, 2026-10-14, SPXW 7770.0P 09:53 | −3,602.61, −44.5%, 2026-10-16, SPXW 7640.0P 14:37 | 1.79 | 5,442 | 2 | 100% |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $5.65 a trade) and Robinhood's charged instead (mean $2.92). The study's fees are given beside them below. Re-pricing: exact (402 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| Config A X1 | preview 2026-10-12→16 | 57 | **+11.68**, +43.87 | +10.67, +43.03 | 61.4 / 61.4 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X2 | preview 2026-10-12→16 | 53 | **+16.56**, +62.22 | +15.56, +61.38 | 49.1 / 49.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X3 | preview 2026-10-12→16 | 48 | **+15.96**, +92.48 | +14.82, +91.60 | 29.2 / 29.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X4 | preview 2026-10-12→16 | 48 | **+8.86**, +456.43 | +7.71, +447.58 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X1 | preview 2026-10-12→16 | 55 | **+11.39**, +42.04 | +10.41, +41.19 | 63.6 / 63.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X2 | preview 2026-10-12→16 | 49 | **+11.51**, +44.62 | +10.54, +43.78 | 46.9 / 46.9 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X3 | preview 2026-10-12→16 | 46 | **+10.90**, +97.12 | +9.80, +96.23 | 28.3 / 28.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X4 | preview 2026-10-12→16 | 46 | **+4.82**, +485.39 | +3.72, +476.48 | 32.6 / 32.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- preview 2026-10-12→16: stop 45.0%; runner 24.9%; +1R 17.4%; +2R 12.2%; flat 0.5%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2026 | Config A X1 | 57 | 61.4 | +11.68 | +43.87 | +2,501 |
| 2026 | Config A X2 | 53 | 49.1 | +16.56 | +62.22 | +3,298 |
| 2026 | Config A X3 | 48 | 29.2 | +15.96 | +92.48 | +4,439 |
| 2026 | Config A X4 | 48 | 33.3 | +8.86 | +456.43 | +21,909 |
| 2026 | Config B X1 | 55 | 63.6 | +11.39 | +42.04 | +2,312 |
| 2026 | Config B X2 | 49 | 46.9 | +11.51 | +44.62 | +2,187 |
| 2026 | Config B X3 | 46 | 28.3 | +10.90 | +97.12 | +4,467 |
| 2026 | Config B X4 | 46 | 32.6 | +4.82 | +485.39 | +22,328 |
| 2026 | all names | 402 | 44.0 | +11.56 | +157.81 | +63,440 |

![](charts/s41a.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** One falling week, mostly puts.

## #41b EMA system v1: PREVIEW on three drawn weeks (up, flat, down)

**Folder:** `research_notes/EMA system/`. **Commits:** f171654 / — / f512d21. **Dates:** 2026-10-23.

**Hypothesis.** v0 with four changes (the three passed rules V1, X3, VN1 and a fix).

**Rule.** RULEBOOK_v1.md.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** As 41a.

**Data.** Weeks drawn by seed 2026102310: up 2025-07-21, flat 2026-02-02, down 2026-07-13.

**Periods and holdouts.** PREVIEW, no verdict; no day in a held-out month.

**Pass rule (as pre-registered).** None.

**Verdict.** PREVIEW: about zero pooled; the sign follows the week.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| Config A X1 | preview week: up | 20 | 5 / 5 | 45.0 | +18.9, +28.03 | −42.1, −69.72 | −26.0, −17.12 | **−14.67**, −25.73 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X2 | preview week: up | 20 | 5 / 5 | 20.0 | +52.1, +158.81 | −45.6, −73.60 | −34.6, −22.21 | **−26.04**, −27.12 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X3 | preview week: up | 21 | 5 / 5 | 9.5 | +25.6, +10.89 | −28.5, −57.92 | −28.7, −20.13 | **−23.34**, −51.37 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X4 | preview week: up | 21 | 5 / 5 | 14.3 | +21.3, +92.09 | −28.0, −586.46 | −27.9, −201.23 | **−20.93**, −489.52 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X1 | preview week: up | 18 | 5 / 5 | 50.0 | +18.9, +28.03 | −42.2, −78.63 | −9.2, −5.11 | **−11.65**, −25.30 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X2 | preview week: up | 18 | 5 / 5 | 22.2 | +52.1, +158.81 | −46.1, −79.88 | −34.6, −22.21 | **−24.28**, −26.84 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X3 | preview week: up | 19 | 5 / 5 | 10.5 | +25.6, +10.89 | −28.0, −61.95 | −28.7, −17.14 | **−22.31**, −54.28 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X4 | preview week: up | 19 | 5 / 5 | 15.8 | +21.3, +92.09 | −27.3, −630.20 | −27.9, −171.27 | **−19.65**, −516.16 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X1 | preview week: flat | 32 | 5 / 5 | 68.8 | +44.7, +218.82 | −39.8, −206.96 | +28.9, +34.83 | **+18.29**, +85.77 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X2 | preview week: flat | 27 | 5 / 5 | 55.6 | +74.3, +368.70 | −35.5, −244.81 | +51.7, +47.81 | **+25.50**, +96.03 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X3 | preview week: flat | 24 | 5 / 5 | 45.8 | +88.1, +487.11 | −30.4, −162.95 | −14.0, −10.65 | **+23.94**, +134.99 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X4 | preview week: flat | 24 | 5 / 5 | 50.0 | +65.4, +3,380.28 | −28.8, −1,525.87 | −2.4, −47.30 | **+18.29**, +927.21 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X1 | preview week: flat | 32 | 5 / 5 | 68.8 | +44.7, +218.82 | −39.8, −206.96 | +28.9, +34.83 | **+18.29**, +85.77 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X2 | preview week: flat | 27 | 5 / 5 | 55.6 | +74.3, +368.70 | −35.5, −244.81 | +51.7, +47.81 | **+25.50**, +96.03 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X3 | preview week: flat | 24 | 5 / 5 | 45.8 | +88.1, +487.11 | −30.4, −162.95 | −14.0, −10.65 | **+23.94**, +134.99 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X4 | preview week: flat | 24 | 5 / 5 | 50.0 | +65.4, +3,380.28 | −28.8, −1,525.87 | −2.4, −47.30 | **+18.29**, +927.21 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X1 | preview week: down | 12 | 5 / 5 | 33.3 | +63.9, +202.11 | −42.2, −348.48 | −29.4, −93.68 | **−6.80**, −164.95 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X2 | preview week: down | 12 | 5 / 5 | 16.7 | +80.3, +531.35 | −48.0, −294.91 | −47.3, −138.21 | **−26.64**, −157.20 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X3 | preview week: down | 13 | 5 / 5 | 23.1 | +19.4, +61.47 | −32.3, −245.24 | −28.5, −82.20 | **−20.34**, −174.46 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X4 | preview week: down | 13 | 5 / 5 | 30.8 | +35.4, +1,469.19 | −35.8, −2,724.57 | −28.5, −821.88 | **−13.90**, −1,434.19 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X1 | preview week: down | 12 | 5 / 5 | 33.3 | +63.9, +202.11 | −42.2, −348.48 | −29.4, −93.68 | **−6.80**, −164.95 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X2 | preview week: down | 12 | 5 / 5 | 16.7 | +80.3, +531.35 | −48.0, −294.91 | −47.3, −138.21 | **−26.64**, −157.20 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X3 | preview week: down | 13 | 5 / 5 | 23.1 | +19.4, +61.47 | −32.3, −245.24 | −28.5, −82.20 | **−20.34**, −174.46 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config B X4 | preview week: down | 13 | 5 / 5 | 30.8 | +35.4, +1,469.19 | −35.8, −2,724.57 | −28.5, −821.88 | **−13.90**, −1,434.19 | n/a (< 60 sessions); n/a (< 60 sessions) |
| Config A X1 | three weeks pooled | 64 | 15 / 257 | 54.7 | +40.3, +167.85 | −41.3, −193.94 | +10.2, +10.81 | **+3.29**, +3.91 | [−13.43, +29.47]; [−70.94, +165.39] |
| Config A X2 | three weeks pooled | 59 | 15 / 257 | 35.6 | +70.7, +344.21 | −43.1, −185.90 | −27.8, −22.20 | **−2.58**, +2.78 | [−20.60, +34.39]; [−59.32, +240.66] |
| Config A X3 | three weeks pooled | 58 | 15 / 257 | 27.6 | +67.4, +347.78 | −30.0, −135.03 | −26.4, −17.18 | **−3.11**, −1.84 | [−21.35, +41.96]; [−96.00, +244.91] |
| Config A X4 | three weeks pooled | 58 | 15 / 257 | 32.8 | +52.1, +2,458.76 | −30.0, −1,368.92 | −22.3, −161.32 | **−3.13**, −115.02 | [−18.53, +30.59]; [−542.27, +1,595.76] |
| Config B X1 | three weeks pooled | 62 | 15 / 257 | 56.5 | +40.3, +167.85 | −41.3, −206.12 | +12.7, +12.35 | **+4.74**, +5.00 | [−11.65, +29.47]; [−70.94, +165.39] |
| Config B X2 | three weeks pooled | 57 | 15 / 257 | 36.8 | +70.7, +344.21 | −43.1, −194.59 | −26.0, −22.20 | **−1.20**, +3.92 | [−20.60, +34.39]; [−59.32, +240.66] |
| Config B X3 | three weeks pooled | 56 | 15 / 257 | 28.6 | +67.4, +347.78 | −29.8, −140.60 | −24.5, −16.15 | **−2.03**, −1.06 | [−20.52, +41.96]; [−96.00, +244.91] |
| Config B X4 | three weeks pooled | 56 | 15 / 257 | 33.9 | +52.1, +2,458.76 | −29.9, −1,430.13 | −20.9, −146.13 | **−2.05**, −110.69 | [−17.89, +30.59]; [−562.97, +1,595.76] |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| Config A X1 | preview week: up | +97.74, +19.2%, 2025-07-23, SPXW 6340.0C 12:43 | −322.26, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.33 | 541 | 4 | total ≤ 0 (best 5 days −515; without them −0) |
| Config A X2 | preview week: up | +387.74, +76.0%, 2025-07-23, SPXW 6340.0C 12:43 | −322.26, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.54 | 806 | 5 | total ≤ 0 (best 5 days −542; without them −0) |
| Config A X3 | preview week: up | +18.96, +46.2%, 2025-07-25, QQQ 567.0C 12:09 | −322.26, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.02 | 1,079 | 5 | total ≤ 0 (best 5 days −1,079; without them +0) |
| Config A X4 | preview week: up | +221.16, +53.9%, 2025-07-25, QQQ 567.0C 12:09 | −3,222.61, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.03 | 10,280 | 5 | total ≤ 0 (best 5 days −10,280; without them +0) |
| Config B X1 | preview week: up | +97.74, +19.2%, 2025-07-23, SPXW 6340.0C 12:43 | −322.26, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.36 | 520 | 4 | total ≤ 0 (best 5 days −455; without them +0) |
| Config B X2 | preview week: up | +387.74, +76.0%, 2025-07-23, SPXW 6340.0C 12:43 | −322.26, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.57 | 768 | 5 | total ≤ 0 (best 5 days −483; without them −0) |
| Config B X3 | preview week: up | +18.96, +46.2%, 2025-07-25, QQQ 567.0C 12:09 | −322.26, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.02 | 1,031 | 5 | total ≤ 0 (best 5 days −1,031; without them +0) |
| Config B X4 | preview week: up | +221.16, +53.9%, 2025-07-25, QQQ 567.0C 12:09 | −3,222.61, −35.4%, 2025-07-22, SPXW 6285.0P 10:13 | 0.03 | 9,807 | 5 | total ≤ 0 (best 5 days −9,807; without them +0) |
| Config A X1 | preview week: flat | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −872.26, −66.1%, 2026-02-03, SPXW 6925.0P 10:25 | 2.33 | 555 | 2 | 100% |
| Config A X2 | preview week: flat | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −1,052.26, −47.6%, 2026-02-05, SPXW 6785.0P 10:46 | 1.88 | 1,198 | 2 | 100% |
| Config A X3 | preview week: flat | +4,288.87, +376.2%, 2026-02-03, SPXW 6925.0P 11:51 | −782.26, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 2.53 | 906 | 3 | 100% |
| Config A X4 | preview week: flat | +28,233.05, +247.7%, 2026-02-03, SPXW 6925.0P 11:51 | −7,822.61, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 2.22 | 4,590 | 3 | 100% |
| Config B X1 | preview week: flat | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −872.26, −66.1%, 2026-02-03, SPXW 6925.0P 10:25 | 2.33 | 555 | 2 | 100% |
| Config B X2 | preview week: flat | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −1,052.26, −47.6%, 2026-02-05, SPXW 6785.0P 10:46 | 1.88 | 1,198 | 2 | 100% |
| Config B X3 | preview week: flat | +4,288.87, +376.2%, 2026-02-03, SPXW 6925.0P 11:51 | −782.26, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 2.53 | 906 | 3 | 100% |
| Config B X4 | preview week: flat | +28,233.05, +247.7%, 2026-02-03, SPXW 6925.0P 11:51 | −7,822.61, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 2.22 | 4,590 | 3 | 100% |
| Config A X1 | preview week: down | +627.74, +91.0%, 2026-07-13, SPXW 7530.0P 12:17 | −632.26, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.29 | 2,607 | 4 | total ≤ 0 (best 5 days −1,979; without them +0) |
| Config A X2 | preview week: down | +1,047.74, +151.8%, 2026-07-13, SPXW 7530.0P 12:17 | −632.26, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.36 | 2,934 | 4 | total ≤ 0 (best 5 days −1,886; without them −0) |
| Config A X3 | preview week: down | +137.74, +20.0%, 2026-07-13, SPXW 7530.0P 12:17 | −632.26, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.08 | 2,406 | 4 | total ≤ 0 (best 5 days −2,268; without them +0) |
| Config A X4 | preview week: down | +5,087.39, +73.7%, 2026-07-13, SPXW 7530.0P 12:17 | −6,322.61, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.24 | 23,732 | 4 | total ≤ 0 (best 5 days −18,644; without them −0) |
| Config B X1 | preview week: down | +627.74, +91.0%, 2026-07-13, SPXW 7530.0P 12:17 | −632.26, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.29 | 2,607 | 4 | total ≤ 0 (best 5 days −1,979; without them +0) |
| Config B X2 | preview week: down | +1,047.74, +151.8%, 2026-07-13, SPXW 7530.0P 12:17 | −632.26, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.36 | 2,934 | 4 | total ≤ 0 (best 5 days −1,886; without them −0) |
| Config B X3 | preview week: down | +137.74, +20.0%, 2026-07-13, SPXW 7530.0P 12:17 | −632.26, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.08 | 2,406 | 4 | total ≤ 0 (best 5 days −2,268; without them +0) |
| Config B X4 | preview week: down | +5,087.39, +73.7%, 2026-07-13, SPXW 7530.0P 12:17 | −6,322.61, −35.9%, 2026-07-17, SPXW 7430.0P 09:45 | 0.24 | 23,732 | 4 | total ≤ 0 (best 5 days −18,644; without them −0) |
| Config A X1 | three weeks pooled | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −872.26, −66.1%, 2026-02-03, SPXW 6925.0P 10:25 | 1.04 | 2,607 | 136 | 1601% |
| Config A X2 | three weeks pooled | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −1,052.26, −47.6%, 2026-02-05, SPXW 6785.0P 10:46 | 1.02 | 2,934 | 137 | 3122% |
| Config A X3 | three weeks pooled | +4,288.87, +376.2%, 2026-02-03, SPXW 6925.0P 11:51 | −782.26, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 0.98 | 3,173 | 138 | total ≤ 0 (best 5 days +4,205; without them −4,312) |
| Config A X4 | three weeks pooled | +28,233.05, +247.7%, 2026-02-03, SPXW 6925.0P 11:51 | −7,822.61, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 0.88 | 23,732 | 138 | total ≤ 0 (best 5 days +31,995; without them −38,666) |
| Config B X1 | three weeks pooled | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −872.26, −66.1%, 2026-02-03, SPXW 6925.0P 10:25 | 1.06 | 2,607 | 136 | 1302% |
| Config B X2 | three weeks pooled | +1,357.74, +119.1%, 2026-02-03, SPXW 6925.0P 11:51 | −1,052.26, −47.6%, 2026-02-05, SPXW 6785.0P 10:46 | 1.03 | 2,934 | 137 | 2303% |
| Config B X3 | three weeks pooled | +4,288.87, +376.2%, 2026-02-03, SPXW 6925.0P 11:51 | −782.26, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 0.99 | 3,173 | 138 | total ≤ 0 (best 5 days +4,213; without them −4,273) |
| Config B X4 | three weeks pooled | +28,233.05, +247.7%, 2026-02-03, SPXW 6925.0P 11:51 | −7,822.61, −59.3%, 2026-02-03, SPXW 6925.0P 10:25 | 0.88 | 23,732 | 138 | total ≤ 0 (best 5 days +32,257; without them −38,455) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $5.62 a trade) and Robinhood's charged instead (mean $2.65). The study's fees are given beside them below. Re-pricing: exact (470 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| Config A X1 | preview week: up | 20 | **−14.67**, −25.73 | −16.37, −26.72 | 45.0 / 45.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X2 | preview week: up | 20 | **−26.04**, −27.12 | −27.76, −28.17 | 20.0 / 20.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X3 | preview week: up | 21 | **−23.34**, −51.37 | −25.11, −52.37 | 9.5 / 9.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X4 | preview week: up | 21 | **−20.93**, −489.52 | −22.71, −499.61 | 14.3 / 9.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X1 | preview week: up | 18 | **−11.65**, −25.30 | −13.33, −26.26 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X2 | preview week: up | 18 | **−24.28**, −26.84 | −25.99, −27.87 | 22.2 / 22.2 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X3 | preview week: up | 19 | **−22.31**, −54.28 | −24.09, −55.26 | 10.5 / 10.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X4 | preview week: up | 19 | **−19.65**, −516.16 | −21.43, −526.01 | 15.8 / 10.5 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X1 | preview week: flat | 32 | **+18.29**, +85.77 | +17.52, +84.77 | 68.8 / 68.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X2 | preview week: flat | 27 | **+25.50**, +96.03 | +24.68, +94.99 | 55.6 / 55.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X3 | preview week: flat | 24 | **+23.94**, +134.99 | +23.21, +133.99 | 45.8 / 45.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X4 | preview week: flat | 24 | **+18.29**, +927.21 | +17.55, +917.31 | 50.0 / 45.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X1 | preview week: flat | 32 | **+18.29**, +85.77 | +17.52, +84.77 | 68.8 / 68.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X2 | preview week: flat | 27 | **+25.50**, +96.03 | +24.68, +94.99 | 55.6 / 55.6 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X3 | preview week: flat | 24 | **+23.94**, +134.99 | +23.21, +133.99 | 45.8 / 45.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X4 | preview week: flat | 24 | **+18.29**, +927.21 | +17.55, +917.31 | 50.0 / 45.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X1 | preview week: down | 12 | **−6.80**, −164.95 | −7.58, −165.65 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X2 | preview week: down | 12 | **−26.64**, −157.20 | −27.42, −157.90 | 16.7 / 16.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X3 | preview week: down | 13 | **−20.34**, −174.46 | −21.10, −175.16 | 23.1 / 23.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X4 | preview week: down | 13 | **−13.90**, −1,434.19 | −14.66, −1,441.33 | 30.8 / 30.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X1 | preview week: down | 12 | **−6.80**, −164.95 | −7.58, −165.65 | 33.3 / 33.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X2 | preview week: down | 12 | **−26.64**, −157.20 | −27.42, −157.90 | 16.7 / 16.7 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X3 | preview week: down | 13 | **−20.34**, −174.46 | −21.10, −175.16 | 23.1 / 23.1 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config B X4 | preview week: down | 13 | **−13.90**, −1,434.19 | −14.66, −1,441.33 | 30.8 / 30.8 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| Config A X1 | three weeks pooled | 64 | **+3.29**, +3.91 | +2.23, +2.98 | 54.7 / 54.7 | [−13.43, +29.47] / [−14.91, +28.63] |
| Config A X2 | three weeks pooled | 59 | **−2.58**, +2.78 | −3.69, +1.80 | 35.6 / 35.6 | [−20.60, +34.39] / [−21.32, +33.47] |
| Config A X3 | three weeks pooled | 58 | **−3.11**, −1.84 | −4.22, −2.78 | 27.6 / 27.6 | [−21.35, +41.96] / [−23.21, +41.16] |
| Config A X4 | three weeks pooled | 58 | **−3.13**, −115.02 | −4.24, −124.37 | 32.8 / 29.3 | [−18.53, +30.59] / [−20.19, +29.83] |
| Config B X1 | three weeks pooled | 62 | **+4.74**, +5.00 | +3.71, +4.07 | 56.5 / 56.5 | [−11.65, +29.47] / [−13.33, +28.63] |
| Config B X2 | three weeks pooled | 57 | **−1.20**, +3.92 | −2.29, +2.95 | 36.8 / 36.8 | [−20.60, +34.39] / [−21.32, +33.47] |
| Config B X3 | three weeks pooled | 56 | **−2.03**, −1.06 | −3.12, −1.99 | 28.6 / 28.6 | [−20.52, +41.96] / [−22.39, +41.16] |
| Config B X4 | three weeks pooled | 56 | **−2.05**, −110.69 | −3.15, −119.93 | 33.9 / 30.4 | [−17.89, +30.59] / [−19.76, +29.83] |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- preview week: up: stop 46.2%; runner 34.6%; +1R 11.5%; +2R 5.1%; 14:00 2.6%
- preview week: flat: runner 31.8%; stop 25.2%; +1R 19.6%; +2R 12.1%; 14:00 11.2%
- preview week: down: stop 56.0%; runner 32.0%; +1R 6.0%; 14:00 4.0%; +2R 2.0%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2025 | Config A X1 | 20 | 45.0 | −14.67 | −25.73 | −515 |
| 2026 | Config A X1 | 44 | 59.1 | +11.45 | +17.39 | +765 |
| 2025 | Config A X2 | 20 | 20.0 | −26.04 | −27.12 | −542 |
| 2026 | Config A X2 | 39 | 43.6 | +9.46 | +18.11 | +706 |
| 2025 | Config A X3 | 21 | 9.5 | −23.34 | −51.37 | −1,079 |
| 2026 | Config A X3 | 37 | 37.8 | +8.38 | +26.27 | +972 |
| 2025 | Config A X4 | 21 | 14.3 | −20.93 | −489.52 | −10,280 |
| 2026 | Config A X4 | 37 | 43.2 | +6.98 | +97.53 | +3,609 |
| 2025 | Config B X1 | 18 | 50.0 | −11.65 | −25.30 | −455 |
| 2026 | Config B X1 | 44 | 59.1 | +11.45 | +17.39 | +765 |
| 2025 | Config B X2 | 18 | 22.2 | −24.28 | −26.84 | −483 |
| 2026 | Config B X2 | 39 | 43.6 | +9.46 | +18.11 | +706 |
| 2025 | Config B X3 | 19 | 10.5 | −22.31 | −54.28 | −1,031 |
| 2026 | Config B X3 | 37 | 37.8 | +8.38 | +26.27 | +972 |
| 2025 | Config B X4 | 19 | 15.8 | −19.65 | −516.16 | −9,807 |
| 2026 | Config B X4 | 37 | 43.2 | +6.98 | +97.53 | +3,609 |
| 2025 | all names | 156 | 23.1 | −20.43 | −155.08 | −24,192 |
| 2026 | all names | 314 | 46.5 | +9.18 | +38.55 | +12,104 |

![](charts/s41b.png)

**Amendments, deviations and integrity checks.** —

**What it showed.** The sign follows the week.

## #42 George A+ entry + EMA targets

**Folder:** `(research_notes/George A+ EMA targets/ was planned)`. **Commits:** none. **Dates:** 2026-10-23.

**Hypothesis.** The GeorgeFi "A+" entry with EMA price-target exits.

**Rule.** —

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** —

**Periods and holdouts.** —

**Pass rule (as pre-registered).** —

**Verdict.** Never run.

**Metrics.** not available — the run was stopped before its prereg was committed; no file exists on disk or in history, so every metric is not available.

**Amendments, deviations and integrity checks.** —

**What it showed.** No result.

## #43 Compass ICT: sweep → displacement/MSS → FVG on SPXW 0DTE

**Folder:** `research_notes/Compass ICT/`. **Commits:** 9d6c37e / Amendment 1 9dbc0bf / preview 315fe8e; exploration 0943030. **Dates:** 2026-10-23.

**Hypothesis.** The owner's ICT rule (v0) and its variants trade SPXW 0DTE at a profit.

**Rule.** HTF bias, a sweep of a level in a killzone, displacement/MSS, entry in the FVG; 2 contracts; TP1 half, TP2, stop; V1 OTE, V2 out 14:00, V3 range gate, V4 5-min; four ablations.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC); ask in, bid out.

**Data.** SPXW 0DTE, 818 full sessions 2022-05-16 → 2026-10-09 (the 28 held-out months out); preview 2026-10-09 → 22.

**Periods and holdouts.** exploration / preview (10 sessions). Holdout A and holdout B UNOPENED; finalists named, never read.

**Pass rule (as pre-registered).** Finalists: v0 plus at most 2 candidates with exploration mean % > 0 and underlying return > 0; holdout B pass: options mean % > 0, interval clear of zero, ≥ 80 trades.

**Verdict.** Exploration only: v0 −0.8% [−7.7, +7.2], +$48 a trade; no holdout read.

**Metrics at Robinhood fees** (return = % of premium; win = P&L > 0 after fees; breakeven is a loss; the interval is audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):

| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |
|------------------|------------------------------|---------------|---------------------|------------|------------------------|------------------------|------------------------|------------------------|------------------------------------------------|
| A no FVG | exploration 2022-05→2026-10-09 | 202 | 158 / 1,123 | 33.2 | +66.1, +1,840.25 | −29.6, −694.87 | −4.9, −109.52 | **+2.12**, +145.99 | [−6.81, +12.27]; [−150.34, +476.87] |
| A no HTF bias | exploration 2022-05→2026-10-09 | 357 | 281 / 1,135 | 37.3 | +37.0, +893.82 | −26.3, −627.90 | −4.6, −104.52 | **−2.74**, −60.98 | [−7.84, +2.11]; [−203.54, +88.43] |
| A no killzones | exploration 2022-05→2026-10-09 | 245 | 175 / 1,126 | 33.1 | +43.7, +1,040.36 | −22.7, −518.74 | −4.2, −94.52 | **−0.74**, −3.29 | [−6.27, +6.15]; [−147.76, +185.82] |
| A no sweep | exploration 2022-05→2026-10-09 | 1,266 | 698 / 1,128 | 41.3 | +30.8, +864.70 | −28.7, −753.63 | −2.7, −54.52 | **−4.11**, −85.08 | [−6.21, −1.64]; [−140.68, −24.20] |
| V1 OTE | exploration 2022-05→2026-10-09 | 94 | 79 / 1,117 | 33.0 | +36.7, +833.54 | −22.6, −525.71 | −12.0, −214.52 | **−3.04**, −77.45 | [−11.14, +6.40]; [−264.40, +154.92] |
| V2 out 14:00 | exploration 2022-05→2026-10-09 | 142 | 116 / 1,117 | 39.4 | +34.0, +896.55 | −21.2, −446.47 | −3.5, −64.52 | **+0.58**, +83.17 | [−6.39, +8.93]; [−101.94, +310.88] |
| V3 range gate | exploration 2022-05→2026-10-09 | 84 | 71 / 1,105 | 36.9 | +26.4, +713.87 | −24.9, −498.63 | −5.4, −84.52 | **−5.95**, −51.16 | [−14.25, +2.73]; [−259.00, +237.27] |
| V4 5-min | exploration 2022-05→2026-10-09 | 37 | 37 / 1,077 | 27.0 | +77.6, +1,528.98 | −41.1, −988.03 | −5.1, −84.52 | **−8.99**, −307.76 | [−24.94, +18.00]; [−673.32, +279.37] |
| v0 | exploration 2022-05→2026-10-09 | 142 | 116 / 1,117 | 37.3 | +35.5, +955.29 | −22.3, −490.95 | −3.9, −74.52 | **−0.73**, +48.84 | [−7.74, +7.57]; [−153.60, +292.78] |
| A no FVG | preview 2026-10-09→22 | 2 | 2 / 6 | 50.0 | +15.1, +175.48 | −37.8, −1,004.52 | −11.3, −414.52 | **−11.32**, −414.52 | n/a (< 60 sessions); n/a (< 60 sessions) |
| A no HTF bias | preview 2026-10-09→22 | 4 | 3 / 3 | 25.0 | +98.7, +3,455.48 | −32.1, −924.52 | −25.5, −574.52 | **+0.59**, +170.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| A no killzones | preview 2026-10-09→22 | 4 | 3 / 6 | 0.0 | —, — | −50.0, −721.98 | −47.2, −824.52 | **−49.96**, −721.98 | n/a (< 60 sessions); n/a (< 60 sessions) |
| A no sweep | preview 2026-10-09→22 | 17 | 9 / 9 | 35.3 | +68.9, +1,563.81 | −41.9, −1,029.07 | −8.8, −204.52 | **−2.84**, −113.93 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V1 OTE | preview 2026-10-09→22 | 1 | 1 / 1 | 0.0 | —, — | −10.0, −264.52 | −10.0, −264.52 | **−10.02**, −264.52 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V2 out 14:00 | preview 2026-10-09→22 | 1 | 1 / 1 | 0.0 | —, — | −40.6, −884.52 | −40.6, −884.52 | **−40.57**, −884.52 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V3 range gate | preview 2026-10-09→22 | 1 | 1 / 1 | 100.0 | +6.7, +175.48 | —, — | +6.7, +175.48 | **+6.70**, +175.48 | n/a (< 60 sessions); n/a (< 60 sessions) |
| V4 5-min | preview 2026-10-09→22 | 1 | 1 / 1 | 0.0 | —, — | −13.1, −104.52 | −13.1, −104.52 | **−13.07**, −104.52 | n/a (< 60 sessions); n/a (< 60 sessions) |
| v0 | preview 2026-10-09→22 | 1 | 1 / 1 | 0.0 | —, — | −40.6, −884.52 | −40.6, −884.52 | **−40.57**, −884.52 | n/a (< 60 sessions); n/a (< 60 sessions) |

| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days' share of profit |
|------------------|------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|------------|---------------|---------------|------------------------------------|
| A no FVG | exploration 2022-05→2026-10-09 | +21,545.48, +282.7%, 2025-04-08, SPXW 5220.0- ×2 m84 | −4,074.52, −91.8%, 2026-02-20, SPXW 6860.0- ×2 m47 | 1.31 | 22,163 | 337 | 193% |
| A no HTF bias | exploration 2022-05→2026-10-09 | +9,735.48, +333.4%, 2026-07-27, SPXW 7465.0- ×2 m16 | −10,804.52, −69.9%, 2025-04-07, SPXW 5075.01 ×2 m53 | 0.85 | 45,284 | 1,011 | total ≤ 0 (best 5 days +35,068; without them −56,839) |
| A no killzones | exploration 2022-05→2026-10-09 | +9,735.48, +333.4%, 2026-07-27, SPXW 7465.0- ×2 m16 | −3,284.34, −97.7%, 2025-05-05, SPXW 5655.01 ×2 m33 | 0.99 | 16,881 | 518 | total ≤ 0 (best 5 days +30,157; without them −30,962) |
| A no sweep | exploration 2022-05→2026-10-09 | +24,995.48, +262.6%, 2025-04-04, SPXW 5245.0- ×2 m6 | −13,624.52, −92.2%, 2025-04-07, SPXW 4895.0- ×2 m3 | 0.81 | 120,952 | 1,083 | total ≤ 0 (best 5 days +58,768; without them −166,476) |
| V1 OTE | exploration 2022-05→2026-10-09 | +4,615.48, +219.8%, 2023-08-10, SPXW 4510.0- ×2 m86 | −2,124.52, −37.7%, 2026-06-12, SPXW 7405.0- ×2 m37 | 0.78 | 7,416 | 1,117 | total ≤ 0 (best 5 days +16,423; without them −23,703) |
| V2 out 14:00 | exploration 2022-05→2026-10-09 | +9,735.48, +333.4%, 2026-07-27, SPXW 7465.0- ×2 m16 | −3,044.52, −51.4%, 2026-06-12, SPXW 7395.0- ×2 m31 | 1.31 | 7,047 | 584 | 212% |
| V3 range gate | exploration 2022-05→2026-10-09 | +7,705.48, +157.9%, 2022-10-14, SPXW 3675.0- ×2 m30 | −3,044.52, −51.4%, 2026-06-12, SPXW 7395.0- ×2 m31 | 0.84 | 7,261 | 1,008 | total ≤ 0 (best 5 days +16,393; without them −20,690) |
| V4 5-min | exploration 2022-05→2026-10-09 | +4,025.48, +156.0%, 2026-06-04, SPXW 7550.01 ×2 m61 | −3,764.52, −64.2%, 2026-06-12, SPXW 7380.0- ×2 m27 | 0.57 | 13,988 | 1,077 | total ≤ 0 (best 5 days +13,137; without them −24,524) |
| v0 | exploration 2022-05→2026-10-09 | +9,735.48, +333.4%, 2026-07-27, SPXW 7465.0- ×2 m16 | −3,284.34, −97.7%, 2025-05-05, SPXW 5655.01 ×2 m33 | 1.16 | 10,583 | 878 | 393% |
| A no FVG | preview 2026-10-09→22 | +175.48, +15.1%, 2026-10-21, SPXW 7745.0- ×2 m330 | −1,004.52, −37.8%, 2026-10-14, SPXW 7785.01 ×2 m18 | 0.17 | 1,005 | 6 | total ≤ 0 (best 5 days −829; without them +0) |
| A no HTF bias | preview 2026-10-09→22 | +3,455.48, +98.7%, 2026-10-15, SPXW 7695.01 ×2 m35 | −1,624.52, −45.4%, 2026-10-15, SPXW 7695.01 ×2 m13 | 1.25 | 885 | 1 | 100% |
| A no killzones | preview 2026-10-09→22 | −294.52, −11.0%, 2026-10-20, SPXW 7720.0- ×2 m106 | −944.34, −94.4%, 2026-10-21, SPXW 7745.0- ×2 m347 | 0.00 | 2,888 | 6 | total ≤ 0 (best 5 days −2,888; without them +0) |
| A no sweep | preview 2026-10-09→22 | +6,545.48, +320.9%, 2026-10-16, SPXW 7740.0- ×2 m86 | −2,224.52, −74.6%, 2026-10-21, SPXW 7720.0- ×2 m38 | 0.83 | 5,612 | 4 | total ≤ 0 (best 5 days +5,139; without them −7,076) |
| V1 OTE | preview 2026-10-09→22 | −264.52, −10.0%, 2026-10-14, SPXW 7775.01 ×2 m23 | −264.52, −10.0%, 2026-10-14, SPXW 7775.01 ×2 m23 | 0.00 | 265 | 1 | total ≤ 0 (best 5 days −265; without them +0) |
| V2 out 14:00 | preview 2026-10-09→22 | −884.52, −40.6%, 2026-10-14, SPXW 7790.01 ×2 m20 | −884.52, −40.6%, 2026-10-14, SPXW 7790.01 ×2 m20 | 0.00 | 885 | 1 | total ≤ 0 (best 5 days −885; without them +0) |
| V3 range gate | preview 2026-10-09→22 | +175.48, +6.7%, 2026-10-14, SPXW 7760.01 ×2 m30 | +175.48, +6.7%, 2026-10-14, SPXW 7760.01 ×2 m30 | ∞ | 0 | 0 | 100% |
| V4 5-min | preview 2026-10-09→22 | −104.52, −13.1%, 2026-10-13, SPXW 7805.01 ×2 m286 | −104.52, −13.1%, 2026-10-13, SPXW 7805.01 ×2 m286 | 0.00 | 105 | 1 | total ≤ 0 (best 5 days −105; without them +0) |
| v0 | preview 2026-10-09→22 | −884.52, −40.6%, 2026-10-14, SPXW 7790.01 ×2 m20 | −884.52, −40.6%, 2026-10-14, SPXW 7790.01 ×2 m20 | 0.00 | 885 | 1 | total ≤ 0 (best 5 days −885; without them +0) |

**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back (mean $5.09 a trade) and Robinhood's charged instead (mean $4.50). The study's fees are given beside them below. Re-pricing: exact (2,601 trades).

| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study's fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |
|------------------|------------------------------|------------|------------------------------|------------------------------|------------------------|------------------------------------------------------|
| A no FVG | exploration 2022-05→2026-10-09 | 202 | **+2.12**, +145.99 | +2.10, +145.40 | 33.2 / 33.2 | [−6.81, +12.27] / [−6.84, +12.24] |
| A no HTF bias | exploration 2022-05→2026-10-09 | 357 | **−2.74**, −60.98 | −2.77, −61.57 | 37.3 / 37.3 | [−7.84, +2.11] / [−7.87, +2.08] |
| A no killzones | exploration 2022-05→2026-10-09 | 245 | **−0.74**, −3.29 | −0.77, −3.87 | 33.1 / 33.1 | [−6.27, +6.15] / [−6.30, +6.13] |
| A no sweep | exploration 2022-05→2026-10-09 | 1,266 | **−4.11**, −85.08 | −4.14, −85.66 | 41.3 / 41.3 | [−6.21, −1.64] / [−6.24, −1.67] |
| V1 OTE | exploration 2022-05→2026-10-09 | 94 | **−3.04**, −77.45 | −3.07, −78.04 | 33.0 / 33.0 | [−11.14, +6.40] / [−11.17, +6.37] |
| V2 out 14:00 | exploration 2022-05→2026-10-09 | 142 | **+0.58**, +83.17 | +0.55, +82.59 | 39.4 / 39.4 | [−6.39, +8.93] / [−6.41, +8.90] |
| V3 range gate | exploration 2022-05→2026-10-09 | 84 | **−5.95**, −51.16 | −5.98, −51.74 | 36.9 / 36.9 | [−14.25, +2.73] / [−14.28, +2.70] |
| V4 5-min | exploration 2022-05→2026-10-09 | 37 | **−8.99**, −307.76 | −9.02, −308.33 | 27.0 / 27.0 | [−24.94, +18.00] / [−24.97, +17.97] |
| v0 | exploration 2022-05→2026-10-09 | 142 | **−0.73**, +48.84 | −0.76, +48.26 | 37.3 / 37.3 | [−7.74, +7.57] / [−7.77, +7.54] |
| A no FVG | preview 2026-10-09→22 | 2 | **−11.32**, −414.52 | −11.35, −415.11 | 50.0 / 50.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| A no HTF bias | preview 2026-10-09→22 | 4 | **+0.59**, +170.48 | +0.57, +169.89 | 25.0 / 25.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| A no killzones | preview 2026-10-09→22 | 4 | **−49.96**, −721.98 | −50.00, −722.56 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| A no sweep | preview 2026-10-09→22 | 17 | **−2.84**, −113.93 | −2.86, −114.52 | 35.3 / 35.3 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V1 OTE | preview 2026-10-09→22 | 1 | **−10.02**, −264.52 | −10.04, −265.11 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V2 out 14:00 | preview 2026-10-09→22 | 1 | **−40.57**, −884.52 | −40.60, −885.11 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V3 range gate | preview 2026-10-09→22 | 1 | **+6.70**, +175.48 | +6.68, +174.89 | 100.0 / 100.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| V4 5-min | preview 2026-10-09→22 | 1 | **−13.07**, −104.52 | −13.14, −105.11 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |
| v0 | preview 2026-10-09→22 | 1 | **−40.57**, −884.52 | −40.60, −885.11 | 0.0 / 0.0 | n/a (< 60 sessions) / n/a (< 60 sessions) |

**Random baseline** (as the study computed it, at its own fees): not available — no random baseline was computed by this study

**Exit reasons (share of trades):**

- exploration 2022-05→2026-10-09: TP1+stop@entry 45.9%; stop 29.9%; TP1+TP2 7.3%; TP1 6.5%; TP1+flat 15:58 5.2%; flat 15:58 3.3%; TP2 1.5%; TP1+14:00 0.4%
- preview 2026-10-09→22: stop 56.2%; TP1+stop@entry 21.9%; TP1 12.5%; TP1+flat 15:58 3.1%; TP2 3.1%; TP1+TP2 3.1%

**By year** at Robinhood fees (all periods together, labelled by entry year):

| year | name | trades | win % | mean % | mean $ | total $ |
|---|---|---|---|---|---|---|
| 2022 | A no FVG | 40 | 25.0 | −4.75 | +70.29 | +2,811 |
| 2023 | A no FVG | 61 | 39.3 | −2.07 | +7.29 | +444 |
| 2024 | A no FVG | 29 | 37.9 | +22.81 | +384.79 | +11,159 |
| 2025 | A no FVG | 43 | 34.9 | +3.42 | +484.32 | +20,826 |
| 2026 | A no FVG | 31 | 25.8 | −2.75 | −212.26 | −6,580 |
| 2022 | A no HTF bias | 68 | 39.7 | −1.72 | +22.06 | +1,500 |
| 2023 | A no HTF bias | 102 | 37.3 | −4.05 | −92.65 | −9,451 |
| 2024 | A no HTF bias | 51 | 31.4 | −6.61 | −80.89 | −4,125 |
| 2025 | A no HTF bias | 90 | 36.7 | −4.22 | −203.41 | −18,307 |
| 2026 | A no HTF bias | 50 | 40.0 | +5.41 | +185.88 | +9,294 |
| 2022 | A no killzones | 52 | 36.5 | −3.93 | +35.62 | +1,852 |
| 2023 | A no killzones | 70 | 31.4 | −0.26 | +46.91 | +3,284 |
| 2024 | A no killzones | 35 | 25.7 | −2.16 | +12.06 | +422 |
| 2025 | A no killzones | 60 | 36.7 | −2.25 | −137.27 | −8,236 |
| 2026 | A no killzones | 32 | 28.1 | +1.62 | −31.70 | −1,014 |
| 2022 | A no sweep | 233 | 43.8 | −3.09 | −42.51 | −9,904 |
| 2023 | A no sweep | 307 | 41.4 | −4.37 | −92.89 | −28,518 |
| 2024 | A no sweep | 201 | 40.3 | −5.21 | −69.49 | −13,967 |
| 2025 | A no sweep | 338 | 40.5 | −2.11 | −26.64 | −9,004 |
| 2026 | A no sweep | 204 | 40.2 | −7.00 | −236.53 | −48,251 |
| 2022 | V1 OTE | 17 | 35.3 | −12.61 | −310.11 | −5,272 |
| 2023 | V1 OTE | 26 | 38.5 | +1.94 | +94.13 | +2,447 |
| 2024 | V1 OTE | 10 | 30.0 | −4.99 | −61.52 | −615 |
| 2025 | V1 OTE | 25 | 32.0 | +2.50 | +30.48 | +762 |
| 2026 | V1 OTE | 17 | 23.5 | −8.46 | −286.29 | −4,867 |
| 2022 | V2 out 14:00 | 30 | 43.3 | −6.74 | +19.22 | +577 |
| 2023 | V2 out 14:00 | 40 | 32.5 | −1.79 | +8.73 | +349 |
| 2024 | V2 out 14:00 | 20 | 35.0 | −4.63 | +34.49 | +690 |
| 2025 | V2 out 14:00 | 35 | 48.6 | +4.12 | +107.48 | +3,762 |
| 2026 | V2 out 14:00 | 18 | 33.3 | +14.69 | +308.26 | +5,549 |
| 2022 | V3 range gate | 18 | 44.4 | −9.70 | +91.16 | +1,641 |
| 2023 | V3 range gate | 20 | 25.0 | −9.37 | −152.02 | −3,040 |
| 2024 | V3 range gate | 11 | 36.4 | −15.00 | −145.41 | −1,600 |
| 2025 | V3 range gate | 27 | 44.4 | +1.30 | +25.48 | +688 |
| 2026 | V3 range gate | 9 | 33.3 | −0.15 | −201.19 | −1,811 |
| 2022 | V4 5-min | 8 | 12.5 | −42.21 | −999.22 | −7,994 |
| 2023 | V4 5-min | 11 | 18.2 | −25.16 | −390.65 | −4,297 |
| 2024 | V4 5-min | 6 | 50.0 | +24.16 | +477.98 | +2,868 |
| 2025 | V4 5-min | 5 | 40.0 | +46.49 | +619.48 | +3,097 |
| 2026 | V4 5-min | 8 | 25.0 | −13.59 | −645.75 | −5,166 |
| 2022 | v0 | 30 | 40.0 | −7.46 | +31.39 | +942 |
| 2023 | v0 | 40 | 30.0 | −3.79 | −42.77 | −1,711 |
| 2024 | v0 | 20 | 35.0 | −5.26 | +16.49 | +330 |
| 2025 | v0 | 35 | 45.7 | +0.75 | −5.66 | −198 |
| 2026 | v0 | 18 | 33.3 | +17.22 | +371.59 | +6,689 |
| 2022 | all names | 496 | 39.9 | −4.81 | −27.92 | −13,847 |
| 2023 | all names | 677 | 37.4 | −3.74 | −59.81 | −40,493 |
| 2024 | all names | 383 | 36.8 | −2.78 | −12.63 | −4,839 |
| 2025 | all names | 658 | 39.8 | −0.88 | −10.05 | −6,610 |
| 2026 | all names | 387 | 36.2 | −2.25 | −119.27 | −46,158 |

![](charts/s43.png)

**Amendments, deviations and integrity checks.** Amendment 1 (ablations become candidates) committed before any exploration result.

**What it showed.** v0 is about zero, and 398% of its profit comes from its five best days.

## #44 Compass EMA: the owner's three EMA / ORB models

**Folder:** `research_notes/Compass EMA/`. **Commits:** 9af93fc (prereg + HOLDOUT_LEDGER) / — / none. **Dates:** 2026-10-23.

**Hypothesis.** (See the prereg.)

**Rule.** PREREG_COMPASS_EMA.md v0.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** SPXW (primary), QQQ (secondary).

**Periods and holdouts.** Holdouts A and B UNOPENED.

**Pass rule (as pre-registered).** (See the prereg.)

**Verdict.** Never computed.

**Metrics.** not available — the run was stopped before computing: a partial engine and a session list exist in the scratchpad (compass_ema_partial/), no signal, trade or P&L.

**Amendments, deviations and integrity checks.** —

**What it showed.** No result.

## #45 DR-GCE gates 1 and 2 (Mode 1 Gamma Vacuum Squeeze)

**Folder:** `research_notes/DR-GCE/`. **Commits:** 01d5c8e, 294d4f2 / A1 041baba / b20eb9c, 00eb3d5. **Dates:** 2026-10-23.

**Hypothesis.** Mode 1 signals touch +18% within 4 minutes far more often than random (gate 1), and in their own direction (gate 2).

**Rule.** Signal rows on SPXW 0DTE; the contract under the gate's rules; a touch = +18% within 4 minutes before the stop.

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** Real NBBO.

**Data.** 504 exploration sessions 2023-12-01 → 2026-10-09; 98 Mode 1 signals.

**Periods and holdouts.** Exploration; the 28 held-out months UNOPENED.

**Pass rule (as pre-registered).** Gate 1: touch-rate lower bound above the random baseline's 97.5%; gate 2: signal − opposite side touch difference clear of zero.

**Verdict.** Gate 1 PASS (narrow: 32.7% [23.3, 40.2] vs 16.0% [9.2, 22.4]); gate 2 FAIL (the lift is volatility, not direction). No backtest was written.

**Metrics.** not available — signal-only: touch outcomes (signals.csv, gate2_pairs.csv), never traded to an exit; no P&L metric exists.

**Amendments, deviations and integrity checks.** Guard selftest 5 of 5.

**What it showed.** The lift is volatility after the impulse, not direction.

## #46 Trend-day test

**Folder:** `—`. **Commits:** none. **Dates:** —.

**Hypothesis.** —

**Rule.** —

**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** —

**Data.** —

**Periods and holdouts.** —

**Pass rule (as pre-registered).** —

**Verdict.** Never registered, never run.

**Metrics.** not available — never run (the trend-day share is only described in step 6).

**Amendments, deviations and integrity checks.** —

**What it showed.** No result.
