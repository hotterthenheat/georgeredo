# Compass Phase 2, Hypothesis A: the low-moc_mag closing pin (short defined-risk 0DTE premium at 15:00 / 15:30)

**Verdict: NO EDGE.** The pre-registered cell (SPXW short call spread, 15:30, held, on low-moc_mag sessions) made
+$26 a spread on 2022-2024 and lost −$33 a spread on 2025-2026 (n 177, CI [−84, +13], profit factor 0.63, both years
negative). Not one of the 1,458 SPXW cells read out of sample has a bootstrap CI clear of zero under any cut, and the
signal's lift (Q1-2 minus Q3-5) is −0.16 % of max risk on average across the SPXW grid OOS, positive in 46 % of cells,
clear of zero in none. moc_mag still ranks the size of the closing move out of sample (ρ +0.18 to +0.23 at every
checkpoint, both names; +0.25 at 15:45 on SPXW) — it just does not turn the sale of that move's optionality into money after the spread and
$0.65 a leg. SPY's unconditional short premium held to the close is positive OOS at $3-15 a spread on credits of
$0.08-0.32, and the signal adds nothing there (Q3-5 beats Q1-2). No rule follows.

Status: the pre-registration below was written 2026-10-21 BEFORE the 2025-2026 cells were read (`python3 s3_report.py
fit` first, the pick into this file, then `python3 s3_report.py oos`). Scripts and outputs: `hyp_a_closing_pin/`
(common.py, s1_features.py, s2_spreads.py, s3_report.py, s4_verify.py, s5_settle_check.py, s6_tables.py; outputs in
`out/`, logs `out/s*_log.txt`, every table `out/tables_oos.txt`). No vendor API was called; no key appears in any file.
Scope as asked: SPXW and SPY (QQQ and IWM were not run).

## 1. Definitions, exactly

**Data.** RAW `data_full/chains/{SPXW,SPY}/<date>.parquet` (every same-day contract's 1-minute NBBO), `data/underlying/
SPY`, `data/index/SPX` (one print a minute). A bar stamped t closes at t+1; a chain row stamped t is the quote at t.
Half days dropped (no 15:00 or 15:58 close). SPXW 1,106 session files 2022-05-13 → 2026-10-09 (1,102 full sessions with
a settlement); SPY 980 files 2022-11-11 → 2026-10-09 (962 full). Fit = 2022-2024, OOS = 2025-01 → 2026-10-09.

**moc_mag** (`s1_features.py`): the audit's normalization, imported unchanged from `clock_session/t5b_moc_test.py`
(`normalize()`: per name, input and checkpoint minute, the mean and sd of the input at that same minute over the 20
sessions strictly before, at least 15, z clipped to ±4, σ(z) = 1/(1+e^−z), moc_mag = [σ(z_vol) + σ(z_range) +
σ(z_|move|) + σ(z_|sweep|)] / 4). The inputs are built by a copy of t5a's `run()` with the window made a parameter:
- **15:00 checkpoint (t = 900): inputs over 14:30 → 15:00** — the audit's "since 15:00" window is empty at 15:00, so the
  half hour before stands in: volume of the bars 870..899 (SPY's for SPXW), range (high − low of those bars over the
  14:29 close; SPX: max − min of the prints 870..900 over the 14:30 print), the move from the 14:29 close (SPX: the
  14:30 print) to the 14:59 close (SPX: the 15:00 print), the sweep-premium imbalance from the per-contract OHLC bars
  870..899 sided against the chain mid at each bar's end (rows 871..900), exactly t5a's rule.
- **15:30 checkpoint (t = 930): the audit's own, inputs over 15:00 → 15:30**; **15:45 (t = 945): the audit's own,
  15:00 → 15:45.** The 930 and 945 rows were checked equal to the audit's `out/t5_features.parquet` on every input:
  4,154 of 4,154 rows, 0 differences.
- Scored sessions: SPXW 647 fit / 444 OOS, SPY 515 / 441 (the first 20 of a name have no score).
- **Quintile cuts from the fit period per name and checkpoint** (`out/moc_quintile_cuts.csv`): the 40 % cut is 0.4392
  (SPXW 900), 0.4341 (SPXW 930), 0.4379 (SPXW 945), 0.4330 / 0.4347 / 0.4353 (SPY 900 / 930 / 945). **Q1-2 = moc_mag below the fit 40 %
  cut; Q3-5 = at or above; 'all' = every scored session.** OOS, 40-44 % of sessions fall in Q1-2 on the fit cuts.
- The magnitude signal holds at every checkpoint (`out/moc_predictive_by_checkpoint.csv`, Spearman of moc_mag with
  |move from the checkpoint to the close|): SPXW 900 +0.241 fit / +0.229 OOS, 930 +0.194 / +0.177, 945 +0.193 /
  +0.251; SPY 900 +0.217 / +0.230, 930 +0.200 / +0.199, 945 +0.199 / +0.233; every p < 2e-4.

**Spreads** (`s2_spreads.py`, every full session, entries 15:00, 15:30 and 15:45):
- Spot S: SPX's print stamped t; SPY's bar stamped t−1 (it closes at t). IV and delta: Black-Scholes, r = q = 0, from
  the contract's NBBO mid at t; a contract with mid − intrinsic ≤ 0.01 has no IV (the same-day skip rule) and is never a
  short strike. (With r = q = 0 the delta does not depend on the year-fraction convention.)
- Short strikes, OTM only: **d10/d15/d20/d25** = the nearest-the-money OTM strike whose |delta| ≤ 0.10/0.15/0.20/0.25;
  **m1.00 / m1.25** = the first strike strictly outside S ± 1.00 × M / 1.25 × M, M = the ATM straddle's mid (call mid
  + put mid at the strike nearest S) at t. Wings: SPXW 5, 10, 25 points; SPY 1, 2, 5. (SPXW strikes are 5 points
  apart, so d15 and d20 often land on one strike.)
- Fills: the short leg at its bid, the long leg at its ask, both the row stamped t; credit = bid_short − ask_long,
  a vertical needs **credit ≥ $0.05** (per vertical; an iron condor needs both). **$0.65 a leg to open.**
- Management, each its own variant, one lot a vertical: **hold** to settlement (the vertical is worth intrinsic(short)
  − intrinsic(long), no closing fee); **tp50**: from t+1 to 15:59 the first minute the cost to close (ask_short −
  bid_long) ≤ 0.5 × credit, buy the short back at its ask (+$0.65) and sell the long at its bid (+$0.65) when that bid
  is above 0, else keep the long to settlement; **stop2x**: the first minute the cost to close ≥ 2 × credit, closed the
  same way. An iron condor is the call and the put vertical of the same rule and wing, each managed on its own; its
  max risk = width × 100 − total credit × 100.
- **Settlement.** SPXW: the last SPX print at or before 16:00 — a PROXY; the official settlement (the exchange's
  closing value from the constituents' closing auctions) is not on disk. SPY: the 16:00 bar's close, cash-settled at
  intrinsic — **assumed; no assignment or exercise fee is charged on either product** (a settled leg pays no fee,
  SPY's by the brief's instruction, SPXW's by the same assumption).
- **The proxy checked** (`s5_settle_check.py`, `out/settle_check.csv`, 1,097 sessions): the 16:00 SPX print against
  SPY's 16:00 close × (SPX / SPY at 15:59): mean +0.04 pts, median 0.00, sd 1.01, p5 −1.28, p95 +1.38; |difference|
  > 1 pt on 18.0 % of sessions, > 2 on 3.0 %, > 5 on 0.2 %; the largest 15.6 pts on 2026-06-26 (a Russell
  reconstitution close: the 15:59 → 16:00 print moved −26.6 pts). Fit sd 0.87, OOS 1.19. The 15:59 → 16:00 print move
  itself has sd 3.2 pts, |move| > 5 pts on 9.8 % of sessions — the last minute is where a short strike 7-15 points
  away gets hit. The audit's anomaly is real in the sense that the last minute is fat-tailed; the print is not visibly
  off from SPY's level except on index-rebalance closes.
- Rows: 524,598 (SPXW) + 189,171 (SPY) in `out/spread_rows_{SPXW,SPY}.parquet` — rebuildable by `s2_spreads.py` in
  about 4.5 minutes. `out/moc_*.parquet` rebuildable by `s1_features.py` in about 3 minutes. The cell tables
  (`out/cells_fit.csv`, `cells_oos.csv`, `cells_diff_*.csv`) by `s3_report.py` (4 and 9 minutes, 2,000-draw session
  bootstraps). Every run single-threaded under `nice -n 10`, well under 1.5 GB.
- **Verification** (`s4_verify.py`, `out/verify_50.csv`): 50 random spread rows (33 SPXW / 17 SPY; 24 call, 14 put,
  12 IC; 16 hold, 18 tp50, 16 stop2x; all three entries) re-derived from the raw chain files with separate plain-loop
  code (quotes read row by row into a dict, IV by scipy brentq, delta by scipy norm, the rules, the scan and the
  settlement written again): **50 identical, 0 differences** in short strike, long strike, credit, exit minute or P&L.

## 2. The pre-registered pick (fit = 2022-2024, read on 2026-10-21 before any 2025-2026 cell)

Selection rule (written into s3_report.py before the fit cells were read): universe SPXW and SPY, entries 15:00 and
15:30 (15:45 a check only), every structure, strike rule, wing and management, cut = moc_mag Q1-Q2 (the hypothesis is
the signal's). Eligible: N >= 150; the fit session-bootstrap 95% CI of the mean % of max risk excludes zero from above;
mean without the best 5 sessions > 0; every fit calendar year with >= 30 trades has a profit factor > 1; the fit
difference Q1-2 minus Q3-5 in % of max risk > 0. Pick: among the eligible, the highest lower bound of the fit CI of the
mean % of max risk; one a name, SPXW primary.

Result of the rule (`out/eligible_fit.csv`, `out/pick.json`): 14 cells eligible, every one SPXW, every one at 15:30,
every one a 25-point wing; no SPY cell is eligible (no SPY cell at 15:00 or 15:30 has a fit CI clear of zero with a
positive signal lift and every year's profit factor above 1).

**THE PICK: SPXW, short call spread, short strike = the first strike above spot + 1.00 x the remaining ATM straddle,
25-point wing, sold at 15:30, held to settlement, only on sessions whose moc_mag at 15:30 is below the fit-period 40%
cut (0.4341 for SPXW at 15:30).**
Fit (2022-05 -> 2024-12, n 252 sessions, fees in): mean +$26.3 a spread [+11.5, +39.9], +1.10% of max risk [+0.49,
+1.66]; win rate 91.7%; average win +$55.9, average loss -$298.9; full losses 0 of 252; p5 -$197, p1 -$603, worst -$687
(2023-03-08); profit factor 2.06; max drawdown $908; longest losing streak 1; without the best 5 sessions +$23.4; by
year 2022 +$53.2 (n 55, PF 3.61), 2023 +$11.3 (n 95, PF 1.45), 2024 +$25.8 (n 102, PF 1.96); total +$6,630. The same
spread sold on every session (cut 'all', n 640): +$6.2 [-15.7, +24.0]; on Q3-5 sessions (n 388): -$6.9 [-40.0, +22.6].
The signal lift Q1-2 minus Q3-5: +1.34% of max risk, CI [-0.03, +2.87] - NOT clear of zero on fit, which is already a
warning the rule did not weigh (the rule asked for a positive difference, not a significant one).

What the fit table says beyond the pick: across the 951 fit cells with both cuts, Q1-2 beats Q3-5 in 77% of cells but
the difference's CI is clear of zero in 18%; the mean cell is negative in % of max risk on SPXW at every entry for both
cuts (Q1-2 -0.2 to -1.0%, Q3-5 -1.4 to -2.1%) - the signal mostly removes the worst sessions from a losing baseline
rather than turning it positive. Every eligible cell is a 25-point wing: the widest wing has the largest max risk, so
the same dollars read as the smallest %, and the 25-point long leg is nearly free - the "edge" of these cells is the
naked short strike's premium with the tail cut at 25 points, which one closing move of 25+ points takes back.

## 3. Out of sample (2025-01-02 → 2026-10-09), read once

### 3.1 The pick, by cut (`out/cells_oos.csv`; SPXW · CALL · m1.00 · wing 25 · 15:30 · hold)

| period | cut | N | mean $ | 95 % CI | mean % of max risk [CI] | win | avg win | avg loss | full loss | p5 / p1 / worst (date) | PF | max DD | streak | wo best 5 | total | total w/o worst | by year |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fit | **Q1-2** | 252 | **+26.3** | [+11.5, +39.9] | +1.10 [+0.49, +1.66] | 91.7 % | +55.9 | −298.9 | 0.0 % | −197 / −603 / −687 (2023-03-08) | 2.06 | 908 | 1 | +23.4 | +6,630 | +7,318 | 22 +53.2 (55) · 23 +11.3 (95) · 24 +25.8 (102) |
| fit | Q3-5 | 388 | −6.9 | [−40.0, +22.6] | −0.24 [−1.60, +0.98] | 90.2 % | +79.7 | −805.3 | 0.3 % | −653 / −1,647 / −2,361 (2024-05-31) | 0.91 | 9,516 | 2 | −10.3 | −2,693 | −332 | 22 +22.1 · 23 +2.9 · 24 −34.7 |
| fit | all | 640 | +6.2 | [−15.7, +24.0] | +0.29 [−0.62, +1.03] | 90.8 % | +70.2 | −625.0 | 0.2 % | −449 / −1,347 / −2,361 | 1.11 | 9,187 | 2 | +4.2 | +3,937 | +6,298 | 22 +34.0 · 23 +6.1 · 24 −9.9 |
| **OOS** | **Q1-2 (the pick)** | **177** | **−33.0** | **[−83.8, +12.6]** | **−1.39 [−3.53, +0.52]** | 88.1 % | +62.9 | −708.8 | 0.6 % | −648 / −1,705 / −2,311 (2025-04-30) | **0.63** | 8,053 | 3 | **−38.6** | **−5,846** | −3,535 | **25 −37.1 (94, PF 0.62) · 26 −28.4 (83, PF 0.64)** |
| OOS | Q3-5 | 263 | +11.8 | [−29.7, +48.9] | +0.52 [−1.25, +2.10] | 86.7 % | +101.5 | −592.0 | 0.8 % | −550 / −1,616 / −2,301 (2025-04-16) | 1.15 | 6,067 | 3 | +6.1 | +3,110 | +5,411 | 25 −3.5 (153) · 26 +33.1 (110) |
| OOS | all | 440 | −6.2 | [−39.0, +23.1] | −0.25 [−1.62, +1.00] | 87.3 % | +85.9 | −637.9 | 0.7 % | −615 / −1,725 / −2,311 | 0.92 | 8,100 | 4 | −9.8 | −2,736 | −425 | 25 −16.3 (247) · 26 +6.7 (193) |

Credit mean $0.57 fit / $0.68 OOS on a max risk of ~$2,430; the short strike stood 9.2 pts (fit) / 10.7 pts (OOS) above
spot on average. The settlement ended above the short strike on 23 of 252 fit sessions (9 %) and 25 of 177 OOS (14 %);
above the long strike once (OOS).

**The signal lift, paired (`out/cells_diff_oos.csv`):** Q1-2 − Q3-5 = +$33.3 [−0.0, +70.4] (+1.34 % [−0.03, +2.87])
on fit; **−$44.9 [−112.5, +16.9] (−1.91 % [−4.74, +0.70]) OOS.** Q1-2 − all: +0.81 % fit, −1.14 % OOS. The sign of the
lift reversed; neither period's lift is clear of zero.

**What a single tail day does.** Fit: the worst session (−$687) is 10 % of the +$6,630 total. OOS: the worst session,
2025-04-30 (short 5535 call, settle 5564.5, credit $1.90, −$2,311), is 40 % of the −$5,846 loss; without the worst
three sessions (−$2,311, −$1,745, −$1,692) the OOS total is −$97 — still not positive. 177 sessions of +$63 wins are
undone by 21 losses averaging −$709; with a $68 credit and losses of that size the structure breaks even when the
settlement passes the short strike on about 8.5 % of sessions, and it ran at 14 % OOS (on fit the losses were half the
size, −$299, so the 9 % hit rate cleared a ~16 % breakeven — the fit result was smaller losses, not fewer).

**Sensitivity to the settlement proxy** (the proxy's sd against SPY's implied level is 1 pt): OOS mean −$20.7 with
the settle 1 pt lower, −$46.6 1 pt higher, −$9.7 / −$61.4 at ∓2; settled at the SPY-implied 16:00 level instead:
−$27.4 (n 177). Every variant negative. (Fit: +35.1 / +15.2 at ∓1; +26.4 on the SPY-implied level.)

**Equity (1 lot, OOS):** +34 (2025-01-03), −1,676 (04-14), −2,618 (06-09), −4,177 (09-22), −3,416 (12-05), −4,968
(2026-04-01), −6,428 (05-28), −6,507 (08-12), −5,846 (10-09). It never recovered the April 2025 drawdown.

### 3.2 The 14 fit-eligible cells (all SPXW · 15:30 · wing 25 · Q1-2), fit beside OOS

| side | rule | mgmt | fit N | fit $ | fit % [lo] | fit lift % | OOS N | OOS $ [CI] | OOS % [CI] | OOS win | OOS PF | OOS wo5 | OOS worst (date) | OOS total / w/o worst | OOS by year | OOS lift % [CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CALL | m1.00 | hold (**pick**) | 252 | +26.3 | 1.10 [0.49] | +1.34 | 177 | −33.0 [−83.8, +12.6] | −1.39 [−3.53, +0.52] | 88 % | 0.63 | −38.6 | −2,311 (2025-04-30) | −5,846 / −3,535 | 25 −37.1 · 26 −28.4 | −1.91 [−4.74, +0.70] |
| IC | d20 | hold | 251 | +36.4 | 1.58 [0.38] | +2.57 | 177 | −36.8 [−100.1, +20.6] | −1.64 [−4.44, +0.85] | 79 % | 0.72 | −45.7 | −2,348 (2026-09-30) | −6,516 / −4,169 | 25 −45.5 · 26 −27.0 | −2.29 [−6.08, +1.39] |
| CALL | d20 | hold | 252 | +22.4 | 0.93 [0.34] | +1.14 | 177 | −34.2 [−84.6, +11.1] | −1.45 [−3.55, +0.44] | 89 % | 0.60 | −39.5 | −2,311 (2025-04-30) | −6,052 / −3,741 | 25 −39.4 · 26 −28.3 | −1.95 [−4.67, +0.59] |
| IC | m1.00 | hold | 251 | +37.6 | 1.64 [0.33] | +2.74 | 177 | −29.6 [−94.3, +29.1] | −1.32 [−4.13, +1.26] | 77 % | 0.78 | −39.7 | −2,348 (2026-09-30) | −5,245 / −2,898 | 25 −44.4 · 26 −12.9 | −2.15 [−6.01, +1.77] |
| IC | d20 | stop2x | 251 | +16.6 | 0.71 [0.25] | +0.79 | 177 | −4.4 [−17.7, +9.3] | −0.19 [−0.75, +0.40] | 43 % | 0.86 | −10.9 | −401 (2025-05-06) | −777 / −376 | 25 −12.1 · 26 +4.3 | −0.11 [−1.16, +0.90] |
| CALL | m1.00 (wing 10) | hold | 253 | +16.6 | 1.83 [0.24] | +2.51 | 178 | −22.6 [−56.3, +8.4] | −2.48 [−6.13, +0.84] | 88 % | 0.66 | −26.3 | −961 (2026-01-29) | −4,023 / −3,062 | 25 −24.5 · 26 −20.4 | −2.69 [−7.42, +1.89] |
| IC | m1.00 | stop2x | 251 | +16.8 | 0.72 [0.21] | +0.88 | 177 | −1.3 [−14.7, +13.5] | −0.06 [−0.64, +0.58] | 45 % | 0.96 | −8.8 | −286 (2025-12-08) | −236 / +50 | 25 −10.8 · 26 +9.4 | −0.06 [−1.15, +1.05] |
| CALL | d10 | hold | 243 | +11.6 | 0.47 [0.19] | +1.05 | 173 | −16.6 [−48.9, +9.2] | −0.67 [−1.98, +0.37] | 95 % | 0.57 | −19.1 | −1,398 (2025-04-30) | −2,878 / −1,480 | 25 −16.3 · 26 −17.0 | −1.09 [−2.65, +0.35] |
| IC | d10 | hold | 242 | +19.9 | 0.82 [0.19] | +2.20 | 173 | −20.7 [−64.2, +19.2] | −0.86 [−2.65, +0.79] | 92 % | 0.68 | −24.8 | −2,190 (2026-09-30) | −3,585 / −1,395 | 25 −13.5 · 26 −28.8 | −1.21 [−3.51, +1.03] |
| PUT | d25 | stop2x | 253 | +13.7 | 0.58 [0.10] | +0.87 | 179 | +4.3 [−16.5, +24.4] | +0.19 [−0.70, +1.04] | 60 % | 1.08 | −1.7 | −763 (2025-05-06) | +761 / +1,524 | 25 −2.7 · 26 +12.2 | −0.48 [−1.76, +0.83] |
| CALL | m1.25 | hold | 252 | +15.9 | 0.65 [0.09] | +1.22 | 177 | −24.5 [−71.7, +14.6] | −1.01 [−2.97, +0.60] | 92 % | 0.62 | −28.5 | −2,328 (2025-04-30) | −4,335 / −2,007 | 25 −22.9 · 26 −26.3 | −1.44 [−3.76, +0.77] |
| PUT | d20 | stop2x | 253 | +10.1 | 0.42 [0.06] | +0.75 | 179 | +3.3 [−10.3, +16.8] | +0.15 [−0.42, +0.70] | 58 % | 1.09 | −1.0 | −377 (2025-03-17) | +598 / +975 | 25 −0.8 · 26 +8.0 | −0.12 [−1.06, +0.77] |
| CALL | d15 | hold | 251 | +13.2 | 0.54 [0.02] | +1.14 | 177 | −28.3 [−74.7, +10.6] | −1.17 [−3.11, +0.43] | 92 % | 0.56 | −32.0 | −2,328 (2025-04-30) | −5,000 / −2,672 | 25 −26.7 · 26 −30.0 | −1.65 [−3.92, +0.40] |
| IC | d15 | hold | 250 | +20.3 | 0.85 [0.00] | +2.32 | 177 | −30.0 [−86.8, +20.6] | −1.30 [−3.70, +0.83] | 85 % | 0.70 | −36.5 | −2,215 (2025-04-30) | −5,305 / −3,091 | 25 −27.0 · 26 −33.4 | −1.94 [−5.17, +0.99] |

Every held cell is negative OOS in both years; the two put-side stop2x cells are +$3-4 with CIs through zero and a
negative "without best 5"; every OOS lift is negative. 2025-04-30 is the worst session of eight of the fourteen.

### 3.3 The pick's structure at every entry and management, OOS (SPXW · CALL · m1.00 · wing 25)

| entry | mgmt | Q1-2 N / $ [CI] / % | Q3-5 N / $ | all N / $ [CI] |
|---|---|---|---|---|
| 15:00 | hold | 175 / +9.0 [−39.3, +45.9] / +0.32 (PF 1.15, wo5 +3.5, worst −2,281) | 265 / −7.3 | 440 / −0.8 [−42.5, +36.8] |
| 15:00 | tp50 | 175 / −17.5 [−65.0, +18.2] | 265 / −34.3 | 440 / −27.6 [−66.0, +6.8] |
| 15:00 | stop2x | 175 / −5.2 [−23.1, +12.6] | 265 / −3.6 | 440 / −4.3 [−23.9, +11.4] |
| 15:30 | hold | **177 / −33.0 [−83.8, +12.6] / −1.39** | 263 / +11.8 | 440 / −6.2 [−39.0, +23.1] |
| 15:30 | tp50 | 177 / −44.8 [−94.5, −0.4] / −1.88 (PF 0.44) | 263 / +7.5 | 440 / −13.6 [−42.1, +11.5] |
| 15:30 | stop2x | 177 / −5.1 [−18.7, +8.4] | 263 / −8.0 | 440 / −6.8 [−18.9, +5.5] |
| 15:45 | hold | 172 / −2.4 [−39.3, +27.4] / −0.12 | 265 / −22.8 | 437 / −14.8 [−44.9, +11.6] |
| 15:45 | tp50 | 172 / −10.4 [−45.1, +16.2] | 265 / −29.0 | 437 / −21.7 [−49.4, +2.1] |
| 15:45 | stop2x | 172 / −2.8 [−16.1, +10.3] | 265 / +0.5 | 437 / −0.8 [−12.9, +10.6] |

The 15:00 held cell is the only positive Q1-2 reading of the structure OOS (+$9, CI [−39, +46], a wo5 of +$3.5 and a
−$2,281 worst day); the 50 % buy-back makes every cell worse (it pays the spread twice and gives up the wins' tail
while keeping the losses); the 2× stop cuts the losses to −$300 to −$900 and the mean to −$1 to −$8.

### 3.4 The grid read whole, OOS (`out/cells_oos.csv`, 5,805 cell-periods; `out/tables_oos.txt`)

SPXW, 1,458 OOS cells (3 sides × 6 rules × 3 wings × 3 entries × 3 managements × 3 cuts): **0 with a CI clear of zero
under any cut.** Share of cells with a positive mean % of max risk / mean cell %: Q1-2 held 24 % / −1.40 %, Q1-2 stop2x
6 % / −1.36 %, Q1-2 tp50 9 % / −2.46 %; Q3-5 held 28 % / −0.96 %; all held 14 % / −1.14 %. By entry (Q1-2, every
management): 15:00 29 % positive / −0.89 %; 15:30 7 % / −2.09 %; 15:45 3 % / −2.24 %. The signal lift Q1-2 − Q3-5
across the 486 SPXW cells: mean −0.16 % of max risk, positive in 46 %, CI clear of zero in 0 %, below zero in 1 % — at
15:00 the lift is +1.10 % and positive in 80 % of cells (CI clear in 1 %), at 15:30 −1.12 % (26 % positive), at 15:45
−0.46 % (31 %). The fit's 15:30 lift (+1.69 %, 94 % of cells positive, 38 % clear) did not carry.

SPY, 1,452 OOS cells: held to the close, 92-96 % of cells are positive under every cut and about half have a CI clear
of zero — **but the means are $3-15 a spread on credits of $0.08-0.32** (mean cell +$4.6, the largest +$15.7; the
15:30 m1.00 / wing-5 call spread, sold every session: +$5.2 [+2.0, +8.0], n 310, credit $0.13, PF 2.0), the
dollars are pennies against a $100-500 max risk, and **the signal adds nothing: Q3-5 beats Q1-2** (the same call
spread Q1-2 +$3.0 [−1.9, +6.7] against Q3-5 +$6.5 [+2.2, +10.4]; the SPY iron condor m1.00 / 5: Q1-2 +$6.5, Q3-5
+$15.4, all +$12.2 [+6.6, +17.4]); the lift across SPY held cells is +0.11 % of max risk, positive in 53 %, clear of
zero in 3 %. The best SPY cells by lower CI have N of 1-50 (deep-OTM 1-point condors that clear the $0.05 floor on a
handful of sessions) and are not cells. SPY's stop2x is negative in 64-75 % of cells (the stop fires on the 1-point
spread's own width); tp50 is a coin flip. SPY was not eligible on fit under the pre-registered rule; its OOS reading
is a read, not a pick, and what it reads is "unconditional short premium held to the SPY close has made a few dollars
a spread in 2025-26 with no help from moc_mag" — a different hypothesis (unconditional, SPY, hold), read once, not
tested.

### 3.5 Stress tests, summarised
- Session bootstrap: every SPXW OOS cell's CI contains zero; the pick's is [−$84, +$13].
- Without the best 5 sessions: the pick −$38.6 OOS; every held eligible cell −$19 to −$46; the put stop2x cells −$1 to
  −$2.
- By year: the pick −$37.1 (2025, n 94, PF 0.62) and −$28.4 (2026, n 83, PF 0.64); no eligible held cell is positive
  in either OOS year.
- Tail day: the pick's worst OOS session is 40 % of its loss; without the worst three it is −$97.
- Settlement proxy ±1-2 pts and the SPY-implied level: the pick stays negative (−$10 to −$61; −$27 on SPY's level).
- Management: the 2× stop takes the pick to −$5 [−19, +8] (PF 0.88); the 50 % buy-back to −$45 [−94, −0.4].
- The signal lift: sign reversed from fit (+1.34 %) to OOS (−1.91 %), neither clear of zero.

## 4. Verdict and what would change it

**No edge.** Selling the close's optionality on SPXW when moc_mag is low — as a credit spread or an iron condor at
10-25 delta or outside the straddle, 5-25-point wings, at 15:00, 15:30 or 15:45, held, stopped or bought back — does
not pay after the NBBO spread and $0.65 a leg on 2025-2026, and the fit-period result (the pick +$26 a spread, CI
clear) was a 2022-2024 artefact that a stricter pre-registration (a lift CI clear of zero, which the pick's +1.34 %
[−0.03, +2.87] was not) would have flagged. The magnitude signal itself survives (ρ +0.18 to +0.24 with |move|, both
names, both periods, every checkpoint) — it ranks how far the close moves, but the market prices that: the low-moc_mag
sessions' credits are smaller ($0.57-0.68 against $0.81-1.04 on Q3-5 for the pick) by about as much as their
settlement risk is lower, and what is left is the spread and the fees. The one structural fact the grid shows is that
SPXW's last minute is fat-tailed (sd 3.2 pts, > 5 pts on 10 % of sessions, −26.6 pts on 2026-06-26) and a short strike
7-15 points from spot at 15:30 ends in the money on 9-14 % of sessions against a credit of ~$65 — a ratio no
magnitude signal at ρ 0.2 can carry.

**No rule is justified.** Nothing from this hypothesis goes into the engine. moc_mag stays what the audit said it is:
a display-only "expect a move" gauge.

**What would be needed to re-open it (not a recommendation to):** (a) the official SPXW settlement series — the proxy
moves the pick's OOS mean by ±$13 a point and the structure's whole margin is smaller than that, though every variant
tried stays negative; (b) mid-price or better fills — the result is read at the NBBO, and a short-premium seller who
works the mid would recover part of the $0.10-0.20 a leg the spread costs, which on a $0.60 credit is a third of the
premium — this is the one assumption that could flip the arithmetic, and it is an execution claim, not a signal
claim, so it needs fill data, not another backtest; (c) the closing-cross imbalance feed the audit named as the
missing fifth input, which would make moc_mag a different score; (d) for SPY, a separate unconditional hypothesis
(short 0DTE premium held to the close, no signal) with its own pre-registration — the OOS read here (+$3-15 a spread,
CIs clear on half the cells, 2025-26 only) is suggestive and tiny, and this file did not test it.
