# Compass Phase 2, Hypothesis D: the top-decile volatility breakout

Buying 0DTE straddles, strangles and directional breakouts only when a fitted volatility model's forecast of realized
expansion is in its top decile, plus the opening drive (09:30–09:55) as a special case. Every number below comes from a
script in `hyp_d_vol_breakout/` and its `out/` folder; nothing was fetched; nothing outside that folder was edited.

**Verdict: no edge.** The model does forecast volatility (AUC 0.71–0.73 out of sample for "|30-minute move| ≥ 10 bps"),
but almost all of it is the straddle's own information plus the time of day — a baseline that knows only those two
scores 0.712 — and for the trade-relevant target (the realized 30-minute move exceeds the straddle-implied one) the full
model's top decile realizes it 53.7 % of the time against 53.9 % for the baseline's top decile. The straddle at those
minutes is already priced 2–13 % richer (median) than at the same minute on other sessions. Every long-premium cell is
negative or inside the noise out of sample; the cells that read best lose less than buying at every minute (−1.2 % to
−1.7 % of debit against −4.4 % for the ATM straddle held 30 minutes) but no paired lift's 95 % interval clears zero and
every one is negative without its best five sessions. The pre-registered best-on-fit cell flipped from +4.6 % to −7.0 %
of debit. The opening drive is not tradable with long premium either way. No rule is justified.

## 1. Data, conventions and what was built

- Data (on disk, nothing fetched): ThetaData 1-minute NBBO of every same-day contract — SPXW 1,106 sessions from
  2022-05-13, SPY and QQQ 980 from 2022-11-11, IWM 621 from 2024-04-19, all to 2026-10-09; 1-minute underlying bars
  (SPY, QQQ, IWM); SPX and VIX prints. Half days dropped. **Every second session was taken** (the four cores were shared
  with other researchers at load 6, and a full single-process pass would have run about 65 minutes): SPY 486 sessions
  kept of 490 taken, QQQ 486, IWM 308, SPXW 549 — 1,829 sessions, 129,859 scan minutes (fit 49,487, cut 17,679, OOS
  62,693). The sample is systematic (every other file in date order), not chosen.
- Minute m = 0 is 09:30 New York; a bar stamped t closes at t+1 (c[m] is the price known at m); a chain row stamped m is
  the quote at m; an SPX/VIX print stamped m is the price at m. SPXW's spot is SPX's print; its bar features (ranges,
  relative volume, the opening-drive direction) come from SPY's bars — a stated proxy, as in the audit.
- Fills: every leg bought at the ask and sold at the bid; $0.65 a leg each way; a leg held to settlement pays no closing
  fee — it expires worthless or settles at intrinsic (ETFs at the 16:00 close, i.e. the 15:59 bar's close; SPXW at the
  last SPX print at or before 16:00, a proxy for the official settlement — stated). Quote hygiene at entry on every
  leg: ask > 0, bid > 0, bid ≤ ask; a structure with no eligible leg is no trade. A leg whose bid is missing at a sale
  minute takes its last quoted bid since entry; a leg with a zero bid there is held to settlement.
- Split: fit = sessions before 2024-07-01 (model fitted here; honest fit-period scores are out-of-fold over 5 contiguous
  session blocks); cut = 2024-07-01 → 2024-12-31 (the decile cuts are set here); OOS = 2025-01-01 → 2026-10-09, read
  once, after the picks were written to `out/preregistered.md` (section 4).
- Scripts: `lib.py` (conventions, features, legs, exits, the cell report; reuses the audit's `sweeplib` read-only for
  bars, prints, the dense chain, the IV/delta solver and the day table), `build.py` (the per-scan-minute table,
  `out/minutes_<ROOT>.parquet` — rebuildable, 48 MB, the only parquet intermediates besides `scores.parquet`),
  `model.py`, `cells.py`, `verify.py`; logs in `logs/`.
- Verification: 50 random (product, session, minute, structure, exit) trades re-derived from the raw chain and bar
  files with separate plain-loop code (dicts, scalar Black-Scholes with `math.erf`, its own bisection, its own exits):
  legs, debit, exit minute, net dollars (to $0.01), straddle/spot and the t2 target — **0 differences of 50**
  (`logs/verify.log`).

## 2. Definitions: scan minutes, features, targets, structures, exits

- Scan minutes: 09:35 to 15:25 every 5 minutes (71 a session).
- Features known at the minute (the audit's list, plus two stated additions): minute of day `m`; signed and absolute
  returns over 1/5/15/30 minutes (bps, from spot); bar ranges over 1/5/15/30 minutes (bps of the close); position in
  the session's range so far and in the opening range (from 10:01); the day's move and the day's range so far in ATR14
  units (the audit's day table); realized volatility so far (root mean square of 1-minute log returns since the open,
  bps/min — addition); VIX, VIX minus its first print of the day, minus 30 minutes ago, minus the prior session's last
  print; the ATM straddle (the strike nearest spot with both sides quoted, call mid + put mid) as a share of spot; the
  move it implies for 30 minutes, `implied30 = straddle/spot × sqrt(30 / minutes_left)` (one stated approximation);
  relative volume (the last 5 bars against the median of the same 5 minutes over the 20 sessions before); the day's
  range in ATR units (addition). Product is a categorical. Nothing after the minute is read for a feature.
- Targets: **t1** |30-minute move| ≥ 10 bps; **t2** the realized |30-minute move| > implied30 (the trade-relevant one);
  **t3** the realized move to the close > straddle/spot. Base rates (fit / cut / OOS): t1 0.524 / 0.525 / 0.510; t2
  0.326 / 0.364 / 0.362; t3 0.369 / 0.318 / 0.328 — the straddle over-prices the move about two times in three.
- Models (fixed, never tuned): LightGBM binary, 15 leaves, learning rate 0.05, 400 rounds, min leaf 200, 80 % row and
  column sampling, L2 1.0, one thread; a logistic regression on standardized features (NaN → fit median, product
  one-hot). Baseline: the same LightGBM on `m`, `straddle/spot` and product only. Decile cuts: the nine inner quantiles
  of the final model's score on the cut slice, applied to 2025–2026; D10 by those cuts holds 9.7 % of OOS minutes.
- Structures at a scan minute: `str` ATM straddle (both legs at the ask); `sg10/15/20` strangles — the OTM call and put
  whose BSM |delta| (mid implied vol, r = q = 0, strikes within 3 % of spot) is nearest 0.10 / 0.15 / 0.20, each within
  ±0.05 else no trade; `dir` the side of the last 5-minute move, nearest OTM, one leg; at 09:35 also `oddir`, the side
  of the 09:30 open → 09:35 close move (the bar source's).
- Exits: `h30` / `h60` every leg sold at its bid 30 / 60 minutes on (never past 15:58); `trail` the structure's mark
  (sum of the legs' mids, the entry minute's mark included) falls to 50 % of its running peak → sold at the bids, else
  settlement; `settle` held to settlement; `ri` — stated before the OOS read — the underlying's |move since entry| first
  reaches `straddle/spot × sqrt(elapsed / remaining)` → sold at the bids, else settlement. At 09:35 also `e0955` and
  `e1030` (sold at 09:55 / 10:30).
- Selections: D10 first-of-session (one trade a session at the first D10 scan minute), D10 every minute, D1 every
  minute, all minutes. The time-of-day-matched paired lift of a selected trade = its result minus the mean of the same
  structure and exit at the same product and minute over every other session of the period; its CI is a session
  bootstrap (1,000 draws). Dollar means pool SPXW (10× the ETFs' notional) with the ETFs; **% of debit is the
  cross-product yardstick** and stands beside every dollar figure.

## 3. The forecast: AUC per target per period, and the lift over the straddle-and-clock baseline

`out/model_auc.csv`, `out/lift.csv`, `out/decile_rates.csv`, `logs/model.log`.

| target | model | AUC fit (in-sample) | AUC fit (out-of-fold) | AUC cut 2024H2 | AUC OOS 2025–26 |
|---|---|---|---|---|---|
| t1 ≥ 10 bps | full GBM | 0.799 | 0.673 | 0.682 | **0.713** |
| | full logistic | 0.689 | 0.684 | 0.697 | **0.734** |
| | baseline (m, straddle, product) | 0.692 | 0.653 | 0.698 | **0.712** |
| t2 realized > implied | full GBM | 0.810 | 0.613 | 0.588 | **0.609** |
| | full logistic | 0.633 | 0.621 | 0.640 | **0.647** |
| | baseline | 0.640 | 0.575 | 0.601 | **0.594** |
| t3 to-close > straddle | full GBM | 0.934 | 0.518 | 0.514 | **0.496** |
| | full logistic | 0.562 | 0.469 | 0.580 | 0.493 |
| | baseline | 0.620 | 0.495 | 0.535 | 0.508 |

The audit's 0.68 / 0.71 is reproduced for t1 (0.673 out-of-fold, 0.713 OOS) and it is a volatility forecast; but the
baseline that knows only the clock and the straddle is at 0.712, so the features add 0.001 (GBM) to 0.022 (logistic) of
AUC. The target that would pay a straddle buyer, t2, is far harder (0.61–0.65) and the baseline is 0.59; t3 is a coin
flip for every model (the GBM's 0.934 in-sample is pure memorization).

The top decile's realized rate (full GBM D10 by the registered cuts) against the baseline's D10 and the time-of-day
matched rate:

| target | period | base rate | D10 full | D10 logistic | D10 baseline | tod-matched | lift full − baseline | lift full − tod | mv30 at D10 full / baseline / all (bps) |
|---|---|---|---|---|---|---|---|---|---|
| t1 | fit (OOF) | 0.524 | 0.761 | 0.774 | 0.721 | 0.580 | +0.040 | +0.181 | 28.7 / 26.2 / 15.0 |
| t1 | cut | 0.525 | 0.774 | 0.803 | 0.792 | 0.616 | −0.019 | +0.157 | 30.5 / 32.3 / 15.6 |
| t1 | **OOS** | 0.510 | **0.804** | 0.803 | **0.777** | 0.591 | **+0.028** | +0.214 | 37.9 / 32.5 / 16.1 |
| t2 | fit (OOF) | 0.326 | 0.494 | 0.511 | 0.461 | 0.405 | +0.033 | +0.089 | 22.1 / 19.5 / 15.0 |
| t2 | cut | 0.364 | 0.484 | 0.584 | 0.559 | 0.474 | −0.075 | +0.010 | 22.1 / 26.7 / 15.6 |
| t2 | **OOS** | 0.362 | **0.537** | 0.556 | **0.539** | 0.477 | **−0.002** | +0.060 | 25.3 / 25.2 / 16.1 |
| t3 | OOS | 0.328 | 0.327 | 0.335 | 0.344 | 0.325 | −0.017 | +0.002 | 12.0 / 16.6 / 16.1 |

The full model's D10 and the baseline's D10 overlap 42 % (t2) to 53 % (t1) of their rows; the full-model rows the
baseline does not pick realize t2 at 0.496 OOS, the baseline rows the full model does not pick 0.497 — the same. The
D10 is the open: 32 % of t2's OOS D10 minutes are 09:30–09:59, 25 % 10:00–10:29, 14 % 10:30–10:59 (71 % in the first
ninety minutes); 45 % of sessions are D10 at 09:35 itself. Top features by gain (t1 GBM): realized vol so far,
implied30, VIX, VIX vs prior close, VIX since the open; logistic coefficients (t2): straddle/spot −0.41, m −0.35,
30-minute range +0.18, realized vol +0.16 — the forecast says "the morning is volatile and this session's morning has
been volatile", which the straddle also says.

**Was the straddle at D10 minutes already priced richer?** Yes (`out/straddle_rich_oos_t2_gbm.csv`; straddle/spot
divided by the median straddle/spot at the same product, minute and period over every session): at OOS D10 minutes the
median ratio is SPY 1.13, SPXW 1.07, QQQ 1.04, IWM 1.02 (mean 1.18–1.45; 53–62 % of D10 minutes above the same-minute
median) against 0.99–1.00 (49–50 %) at the other minutes. The realized 30-minute move at D10 is 20–29 bps against 13–18
bps elsewhere, and the straddle has moved up with it.

## 4. Pre-registered picks (`out/preregistered.md`, written after the fit+cut read, before any 2025–2026 row was read)

- Signal: the t2 GBM's top decile by the registered cuts. The t2 logistic and the t1 / t3 models' D10 are robustness
  reads only.
- Primary cells (from the hypothesis, not from the fit numbers): ATM straddle and 15-delta strangle at the FIRST D10
  minute of the session, exits hold-30 and 50 % trail. Fit+cut reads (pooled, % of debit; `out/cells_fit+cut_t2_gbm.csv`):
  straddle h30 −2.7 % [−$48, −$14], trail −4.9 % (−$3, CI [−$90, +$87], −$58 without the best 5 sessions); strangle h30
  −9.9 % [−$28, −$6], trail −9.7 % (CI through zero). Expectation written down: negative out of sample.
- Best-on-fit cell (what a tuner would have picked, registered so its fate is on record): 20-delta strangle, every D10
  minute, 50 % trail: +4.6 % of debit, +$21.7 [−$29, +$81], −$31 without the best 5 sessions, the best 5 sessions = 238 %
  of the total. Expectation: fails.
- Opening drive pick: 09:35, the side of the 09:30–09:35 move, nearest OTM, 50 % trail, D10-only: +12.2 % of debit on
  fit+cut, +$53 [−$26, +$145], −$23 without the best 5. Unconditional +0.1 %. Expectation: noise.
- Decision rule for "edge", fixed then: OOS mean % of debit > 0 with the session-bootstrap 95 % CI of the mean $ clear of
  zero, AND the mean without the best 5 sessions > 0, AND the paired time-of-day-matched lift's CI clear of zero.

## 5. Out of sample, 2025-01-02 → 2026-10-09 (441 sessions, every 2nd; t2 GBM D10 by the registered cuts)

Pooled over the four products (`out/cells_oos_t2_gbm.csv`; $ a structure, fees in; % of debit; CI = session bootstrap
of the mean $; wo5 = mean $ without the best 5 sessions; b5 = the best 5 sessions' share of the total when it is
positive; PF = profit factor).

| structure | exit | selection | N | sessions | debit | mean $ | % of debit | 95 % CI ($) | wo5 | win | avg win / loss | p5 / p1 / worst | b5 | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| straddle | h30 | **D10 first** | 737 | 420 | — | −16.0 | **−1.7 %** | [−38.6, +7.6] | −31.7 | 0.32 | +163 / −102 | −385 / −778 / −2,043 | — | 0.77 |
| straddle | h30 | D10 every | 6,102 | 420 | | +1.8 | −1.2 % | [−16.7, +21.2] | −15.7 | 0.31 | +210 / −90 | −323 / −613 / −3,153 | 896 % | 1.03 |
| straddle | h30 | D1 every | 5,918 | 331 | | −17.5 | −6.2 % | [−23.4, −10.5] | −21.9 | 0.24 | | | — | 0.49 |
| straddle | h30 | all minutes | 62,676 | 441 | | −15.3 | **−4.4 %** | [−20.1, −9.8] | −19.3 | 0.25 | +154 / −71 | −273 / −483 / −3,153 | — | 0.71 |
| straddle | h60 | D10 first | 737 | 420 | | −22.7 | −1.3 % | [−60.3, +17.9] | −48.8 | 0.34 | | | — | 0.80 |
| straddle | h60 | D10 every | 6,102 | 420 | | +15.1 | −0.3 % | [−25.5, +60.6] | −22.1 | 0.33 | +370 / −157 | −553 / −943 / −4,593 | 241 % | 1.14 |
| straddle | h60 | all minutes | 62,676 | 441 | | −15.9 | −5.3 % | [−27.8, −1.8] | −26.6 | 0.27 | | | — | 0.82 |
| straddle | trail | **D10 first** | 737 | 420 | | +27.6 | **−0.5 %** | [−74.7, +146.9] | −70.2 | 0.32 | +892 / −382 | −1,425 / −2,316 / −5,183 | 350 % | 1.11 |
| straddle | trail | D10 every | 6,102 | 420 | | −26.9 | −4.9 % | [−118, +66] | −95.5 | 0.30 | | | — | 0.89 |
| straddle | trail | all minutes | 62,676 | 441 | | −34.8 | −11.1 % | [−86, +35] | −84.6 | 0.28 | | | — | 0.83 |
| straddle | settle | D10 first | 737 | 420 | | +29.1 | −3.4 % | [−109, +182] | −92.6 | 0.39 | +878 / −516 | −1,847 / −3,080 / −10,563 | 412 % | 1.09 |
| straddle | settle | all minutes | 62,676 | 441 | | −50.7 | −15.2 % | [−119, +35] | −114 | 0.33 | | | — | 0.80 |
| straddle | ri | D10 first | 737 | 420 | | −19.3 | −2.5 % | [−23.2, −15.5] | −21.0 | 0.15 | | | — | 0.15 |
| 15Δ strangle | h30 | **D10 first** | 711 | 401 | | −9.9 | **−5.8 %** | [−21.6, +2.3] | −19.1 | 0.29 | +89 / −51 | −198 / −387 / −488 | — | 0.73 |
| 15Δ strangle | h30 | D10 every | 5,661 | 417 | | +1.1 | −4.0 % | [−11.6, +16.6] | −12.6 | 0.26 | | | 1,149 % | 1.03 |
| 15Δ strangle | h30 | all minutes | 53,258 | 441 | | −10.1 | −12.1 % | [−13.7, −5.7] | −13.7 | 0.20 | | | — | 0.70 |
| 15Δ strangle | h60 | D10 every | 5,661 | 417 | | +14.1 | +1.0 % | [−13.4, +48.8] | −14.4 | 0.26 | +270 / −78 | −283 / −488 / −1,353 | 196 % | 1.25 |
| 15Δ strangle | trail | **D10 first** | 711 | 401 | | −13.5 | **−5.7 %** | [−47.0, +23.9] | −46.6 | 0.20 | | | — | 0.82 |
| 15Δ strangle | trail | D10 every | 5,661 | 417 | | −5.6 | −9.5 % | [−35.8, +32.9] | −40.0 | 0.17 | | | — | 0.92 |
| 15Δ strangle | settle | D10 every | 5,661 | 417 | | −53.6 | −29.3 % | [−103, −3.4] | −94.2 | 0.17 | | | — | 0.66 |
| 20Δ strangle | trail | **D10 every (best-on-fit)** | 5,151 | 406 | | −10.3 | **−7.0 %** | [−56.5, +45.4] | −58.5 | 0.18 | +506 / −122 | −463 / −773 / −2,113 | — | 0.90 |
| 20Δ strangle | h60 | D10 every | 5,151 | 406 | | +17.9 | +1.6 % | [−18.6, +57.3] | −16.7 | 0.29 | | | 188 % | 1.23 |
| 20Δ strangle | h30 | D10 first | 660 | 352 | | −12.1 | −5.0 % | [−28.0, +7.1] | −24.1 | 0.29 | | | — | 0.75 |
| 10Δ strangle | h30 | D10 first | 730 | 417 | | −10.1 | −11.9 % | [−17.8, −1.2] | −16.1 | 0.25 | | | — | 0.61 |
| 10Δ strangle | h60 | D10 every | 6,000 | 420 | | +8.9 | −4.3 % | [−11.9, +32.2] | −13.2 | 0.22 | | | 240 % | 1.22 |
| directional | h30 | D10 every | 5,677 | 413 | | −2.6 | −2.5 % | [−18.3, +12.5] | −14.4 | 0.38 | | | — | 0.97 |
| directional | h30 | D10 first | 335 | 204 | | −13.9 | −9.9 % | [−66, +40] | −48.3 | 0.37 | | | — | 0.89 |
| directional | settle | D10 first | 335 | 204 | | +135.9 | −9.0 % | [−107, +459] | −99.3 | 0.30 | +1,539 / −470 | −1,767 / −2,684 / −6,171 | 170 % | 1.41 |
| directional | trail | all minutes | 61,387 | 441 | | −17.0 | −10.2 % | [−29.2, −2.3] | −28.2 | 0.20 | | | — | 0.83 |

Every cell of the full grid (5 structures × 5 exits × 4 selections, pooled and by product) is in the CSV; the pattern
above holds throughout: the D10 cells lose less than the all-minute and D1 cells, the dollar means that read positive
(the straddle's trail and settle at the first D10 minute, the strangles' hold-60 at every D10 minute) have intervals
through zero, are negative without their best five sessions, and the best five sessions are 190–1,150 % of the total.
The `ri` rule (sell once realized ≥ implied) is the worst exit everywhere (−2.5 to −15 %, intervals below zero): the
event it waits for is reached on 15–21 % of trades and the rest decay to settlement.

**By year** (`out/cells_by_year_oos_t2_gbm.csv`): straddle h30 D10-first 2025 −2.4 % (n 411), 2026 −0.9 % (326);
straddle trail D10-first 2025 −1.3 %, 2026 +0.5 %; 15Δ h30 D10-first 2025 −7.6 %, 2026 −3.6 %; 20Δ trail D10-every
(best-on-fit) 2025 −17.1 %, 2026 +3.0 %. The all-minute cells are −3 to −22 % in both years.

**By product, the primary cells** (D10 first, % of debit; CI in $): straddle h30 — SPY +0.2 % [−12.5, +10.1] (n 147),
QQQ −0.4 % [−15.4, +9.3] (198), IWM −5.0 % [−13.7, −4.8] (210), SPXW −1.0 % [−126, +30] (182); straddle trail — SPY
+2.7 % [−33, +83], SPXW +2.4 % (+$114 [−235, +520], −$21 without the best 5), QQQ −2.1 %, IWM −3.7 %; 15Δ h30 — SPY
−1.6 %, QQQ −2.9 %, IWM −14.2 % [−7.8, −2.6], SPXW −3.4 %. No product cell clears zero on the positive side.

**The paired, time-of-day-matched lift of D10 over all minutes** (`out/paired_lift_oos_t2_gbm.csv`, pooled; $ a
structure, CI session bootstrap; "wo5" the lift without the best 5 sessions):

| structure | exit | selection | N | lift $ | 95 % CI | lift % of debit | wo5 |
|---|---|---|---|---|---|---|---|
| straddle | h30 | D10 every | 6,102 | +16.6 | [−2.3, +36.2] | +2.1 | −1.3 |
| straddle | h30 | D10 first | 737 | −4.0 | [−26.5, +20.0] | +1.1 | −19.7 |
| straddle | h60 | D10 every | 6,102 | +30.0 | [−10.9, +75.9] | +3.3 | −7.6 |
| straddle | trail | D10 first | 737 | +24.2 | [−78.9, +144.8] | +4.3 | −73.9 |
| straddle | settle | D10 first | 737 | +49.0 | [−89.8, +202.4] | +4.8 | −73.2 |
| 15Δ strangle | h30 | D10 every | 5,661 | +12.1 | [−0.8, +27.7] | +7.0 | −1.7 |
| 15Δ strangle | h60 | D10 every | 5,661 | +23.3 | [−4.3, +57.6] | +12.1 | −5.3 |
| 15Δ strangle | trail | D10 every | 5,661 | +7.5 | [−22.9, +45.4] | +5.4 | −27.1 |
| 20Δ strangle | h30 | D10 every | 5,151 | +13.4 | [−2.3, +30.5] | +5.1 | −2.9 |
| 20Δ strangle | trail | D10 every | 5,151 | +2.6 | [−44.4, +57.9] | +3.7 | −45.9 |
| directional | h30 | D10 every | 5,677 | +3.1 | [−12.8, +18.4] | +2.2 | −8.8 |

The lift is positive in dollars for the short holds and its intervals touch zero from below in three cells (straddle
h30, 15Δ and 20Δ h30, every D10 minute) — and in every one of them it is negative without the best five sessions. A
D10 minute is a better minute to own gamma than its neighbours on other days, by about the amount the straddle has
already risen; it is not a profitable minute.

**The opening drive at 09:35** (`out/opening_drive_oos_t2_gbm.csv`; "D10" = the 09:35 minute is in the t2 D10, 397 of
877 sessions):

| structure | exit | selection | N | mean $ | % of debit | 95 % CI ($) | wo5 | win | 2025 / 2026 (% of debit) |
|---|---|---|---|---|---|---|---|---|---|
| side of the 09:30–09:35 move | 09:55 | unconditional | 877 | −25.6 | −3.6 % | [−53.2, +0.7] | −38.6 | 0.42 | −2.8 / −4.6 |
| | 09:55 | D10 at 09:35 | 397 | −13.6 | −3.0 % | [−45.8, +19.7] | −32.7 | 0.45 | −3.6 / −2.3 |
| | 10:30 | unconditional | 877 | −30.0 | −2.1 % | [−73.0, +12.7] | −57.8 | 0.40 | −4.9 / +1.6 |
| | 10:30 | D10 at 09:35 | 397 | −12.7 | +0.6 % | [−64.8, +43.8] | −50.9 | 0.41 | −5.3 / +6.7 |
| | trail | unconditional | 877 | −48.0 | −6.1 % | [−105, +9.7] | −98.3 | 0.23 | −8.5 / −3.0 |
| | trail | D10 at 09:35 (the pick) | 397 | −40.6 | **−6.9 %** | [−96.8, +28.9] | −97.8 | 0.23 | −10.2 / −3.5 |
| ATM straddle | 09:55 | unconditional | 881 | −21.6 | −3.2 % | [−35.3, −9.1] | −30.0 | 0.28 | −3.2 / −3.2 |
| | 09:55 | D10 at 09:35 | 402 | −13.7 | −3.5 % | [−32.8, +7.9] | −30.6 | 0.29 | −3.2 / −3.7 |
| | 10:30 | D10 at 09:35 | 402 | +2.4 | −0.9 % | [−39.0, +50.2] | −36.5 | 0.35 | −2.8 / +1.0 |
| | trail | unconditional | 881 | +2.6 | −4.6 % | [−105, +154] | −110 | 0.29 | −5.8 / −3.0 |
| | trail | D10 at 09:35 | 402 | +54.5 | +3.0 % | [−82.8, +206.6] | −82.8 | 0.33 | +3.6 / +2.3 |

The opening-drive pick (+12.2 % on fit+cut) read −6.9 % out of sample. The straddle's trail at a D10 09:35 reads +3.0 %
of debit (+$54) but its interval is [−$83, +$207] and it is −$83 without the best five sessions (SPXW +8.8 % / −$337
without its best five; SPY +4.3 % [−51, +98]); the 10:30 time exit, the honest version of "trade the drive", is −0.9 %.
The drive trends more than a random walk (the audit) and a same-day option still cannot be bought into it: its first
five minutes do not predict its remainder, and the 09:35 straddle is the day's most expensive.

**Robustness reads** (`out/cells_oos_t2_lr.csv`, `cells_oos_t1_gbm.csv`, `cells_oos_t3_gbm.csv`): with the t2 logistic's
D10 the straddle trail D10-first is −1.4 % of debit (+$58 [−69, +215], −$72 without the best 5) and the best-on-fit
20Δ trail D10-every +2.7 % ($11.5 [−56, +97], −$63 wo5); with the t1 GBM's D10 (the audit's target) the straddle trail
D10-every is +0.1 % of debit (+$157 [−175, +670], −$140 wo5), 15Δ hold-60 −1.1 %, 20Δ hold-60 −0.5 %, the opening-drive
pick −10.0 % [−153, −14]; with the t3 GBM's D10 (a model with no skill) every straddle and strangle cell is −3 to −23 %.
No paired lift in any robustness read has an interval clear of zero.

## 6. Stress tests, in one place

- Session bootstrap: no D10 cell's 95 % interval of the mean $ lies above zero, pooled or by product, under any model.
- Without the best five sessions: every D10 cell with a positive dollar mean turns negative (straddle trail D10-first
  +$28 → −$70; settle +$29 → −$93; 15Δ h60 D10-every +$14 → −$14; 20Δ h60 +$18 → −$17), and the best five sessions are
  188–1,149 % of each positive total.
- By year: no cell positive in both 2025 and 2026 among the pre-registered ones (the straddle trail D10-first is −1.3 /
  +0.5 %; the best-on-fit −17.1 / +3.0 %).
- Paired, time-of-day matched: positive in dollars for the short holds, every interval through zero, every one negative
  without its best five sessions.
- The pre-registered best-on-fit cell: +4.6 % → −7.0 % of debit. The pre-registered opening-drive cell: +12.2 % → −6.9 %.
- The straddle at D10 minutes was priced richer (median ratio 1.02–1.13 against 0.99–1.00); the D10's realized move is
  larger (20–29 bps against 13–18) but so is what was paid for it.
- The p1 / worst of the D10 straddle cells (−$778 / −$2,043 on hold-30; −$3,080 / −$10,563 on settle, pooled with SPXW)
  are the ordinary tails of long gamma; no exit changes the mean.

## 7. Verdict and what would change it

**No edge.** A volatility forecast from these features exists and reproduces the audit's AUC, but (a) a baseline of the
clock and the straddle has the same AUC for the audit's target, (b) for the target that pays a straddle buyer the full
model's top decile realizes exactly the baseline's rate (0.537 vs 0.539), (c) the straddle at those minutes is already
dearer by about the forecast, and (d) no long-premium cell — straddle, 10/15/20-delta strangle, directional breakout,
with five exits, at the first or every D10 minute, or at the opening drive — passes the pre-registered rule; the
best-on-fit cell and the opening-drive pick both flipped sign. The D10 cells lose less than buying at any minute
(−1 to −2 % against −4 to −12 % of debit for the straddle; the strangles −4 to −6 % against −12 to −21 %), which is the
one thing the forecast buys: a less bad minute, not a good one.

**Needs X**: an input the straddle does not already price — a scheduled-event calendar (FOMC, CPI, payrolls: the D10
minutes cluster on such mornings), the flow and dark-pool tape, or per-minute strike books — none of which is on disk
for this period (the audit's blockers). A short-premium reading of the same model (selling the straddle at D1 minutes,
where t2 realizes 0.18–0.24 against 0.36) is the direction the data points to and was not tested here (outside this
hypothesis; the owner's go-ahead needed, as the audit's conclusion says).

**Rule**: none for the engine. If the terminal shows an "expected move" gauge, it may show implied30 and the model's
decile as a display field with the statement that neither sets a trade; the realized-vs-implied base rate (the straddle
over-prices the next 30 minutes about 64 % of the time) is the one number worth printing.

## 8. Files

- `hyp_d_vol_breakout/lib.py`, `build.py`, `model.py`, `cells.py`, `verify.py`; `logs/build.log`, `model.log`,
  `cells_*.log`, `oos_summary.txt`, `verify.log`.
- `out/minutes_{SPY,QQQ,IWM,SPXW}.parquet` (rebuildable by `build.py`, every 2nd session, 48 MB), `out/scores.parquet`
  (rebuildable by `model.py`), `out/model_auc.csv`, `decile_rates.csv`, `lift.csv`, `feature_importance.csv`,
  `out/preregistered.md`, and per read `cells_<periods>_<target>_<model>.csv`, `cells_by_year_…`, `paired_lift_…`,
  `straddle_rich_…`, `opening_drive_…` for fit+cut (t2 gbm, t2 lr) and oos (t2 gbm, t2 lr, t1 gbm, t3 gbm).
- Commands, from the folder, each `nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I …`:
  `STEP=2 WORKERS=1 build.py <ROOT>` (5–6 minutes a product), `model.py` (80 s), `cells.py fit,cut t2 gbm`,
  `cells.py oos t2 gbm` (and `t2 lr`, `t1 gbm`, `t3 gbm`; ~1 minute each), `verify.py 50 11`.
