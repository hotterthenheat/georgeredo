# Lifecycle research — 10. Failed hypotheses (deliverable 8)

Every rule tested that did not show a positive, robust, executable expectancy, with the numbers that sank it.

**Conventions**
- Dollars per unit after fees.
- 95 % day-clustered intervals.
- Development + validation unless the hold-out is named.

**"Failed" means one of three things:**
- the expectancy's interval lies below zero;
- the effect is indistinguishable from a control;
- it did not survive validation, walk-forward or the hold-out.

A hypothesis whose interval spans zero on a small sample is listed as **inconclusive**, not failed.

## A. Same-day setups (Tier I: SPY, QQQ, SPXW, IWM 0DTE, 2022-05 → 2025-09)

| # | Hypothesis | Result | Evidence |
|---|---|---|---|
| A1 | Any of the 12 setups, bought as a Steady call or put, has a positive expectancy | **Failed.** 0 of 24 setup × Steady cells have a lower bound above zero at any stage-1 exit. Closest: QS Steady call held to expiry, +66.5 [−0.4, +140.0] on 3,136 trades, the same QS-calls-to-expiry pattern as A3. MSS Steady call to expiry has a higher point estimate (+119.4) on 172 trades, interval [−65.9, +332.9]. | `results/tier1/stage1_cells.csv` |
| A2 | …as a Big Payoff call or put (0.10–0.35 Δ) | **Failed.** 0 of 24 cells have a lower bound above zero. Held to 15:50 the cells return −57 % to +12 % of premium. | same |
| A3 | …as a debit spread | **Failed for 23 of 24 cells.** The exception is QS → debit call spread held to expiry: +50.3 [+10.6, +93.7] on 2,749 trades; development +51.7 [+1.6], validation +46.7 [−26.4, +114.3], walk-forward +16.9 [−19.6, +51.0]. It was not a finalist and is tested once on the hold-out under amendment L-A3 (`07_validation.md` §4.2). | same |
| A4 | Bullish setups sold as credit put spreads or cash-secured puts beat the setups' own long structures | **True but not an edge.** Put selling is the only positive family, but random minutes earn it too (A15, `04_entry_research.md` §1). | `07_validation.md` §4 |
| A5 | Liquidity sweep (LS), market-structure shift (MSS) and fair-value gap (FVG), the ICT concepts, mark profitable entries | **Failed.** Negative in every long structure; MSS fires on 118 days in 3.4 years. | `04_entry_research.md` §4 |
| A6 | Waiting for confirmation (E2) improves entries | **Failed.** Its gain per signal equals skipping the same share of signals at random; like for like it loses $14–60 a trade to entering at the signal. | `04_entry_research.md` §2 |
| A7 | A chase guard (skip if the structure ran > X in favour) improves entries | **Failed.** Same as A6: indistinguishable from random skipping. | same |
| A8 | Limit entries inside the spread improve fills | **Failed.** Adversely selected: they fill on the trades going wrong and miss the winners. Per signal, −12 to −19 a trade for Steady options. | same |
| A9 | Entering 1–3 minutes late costs nothing | **Failed (small).** −1.0 to −1.4 a trade for Steady calls. | same |
| A10 | Time-of-day, VIX or spread filters make a long structure profitable | **Failed.** No level of any filter gives a lower bound above zero. VIX ≥ 20 is worse for every long structure (Steady puts −44.65 [−68.4, −24.0]). | `04_entry_research.md` §3 |
| A11 | A higher forecast of realised volatility than implied (HAR, VOLC) makes the 10:00 straddle profitable | **Failed.** VOLC straddle to 15:50: −32.8 [−102.3, +30.7]; against all days +48.6 [−25.6, +116.5], not significant; walk-forward −35.8 [−42.7, −27.7]. | `results/vol/` |
| A12 | Implied above forecast (VOLR) makes selling puts better | **Failed.** VOLR credit put spreads are *worse* than all days: −17.5 [−38.0, 0.0] to expiry; walk-forward −23.8 [−36.4, −13.4]. | same |
| A13 | Fed-day afternoon straddles (EVF) | **Inconclusive.** 85 trades on 27 days, intervals ±$400. | same |
| A14 | A same-day straddle bought at 10:00 or 13:30 on any day | **Failed.** 10:00 to 15:50: −81.5 [−140.6, −18.8]; 13:30: −86.7 [−115.7, −57.1]. | same |
| A15 | The setups' timing beats a random minute | **See `04_entry_research.md` §1.** The original control could not answer it (look-ahead, amendment L-A2). | — |

## B. Management (Tier I)

| # | Hypothesis | Result | Evidence |
|---|---|---|---|
| B1 | Some management policy makes a long-premium structure profitable | **Failed.** Among 116 policies × 6 long structures, none has a lower bound above zero. Best: Steady call held to expiry +17.65 [−32.4, +81.2]. | `05_management_research.md` §1 |
| B2 | Adding to a winner after confirmation (M6) raises expectancy | **Failed.** The added contracts lose on their own: −8.83 (one add) and −16.77 (two adds) a trade on Steady calls; −60.27 on Steady puts. | `05_management_research.md` §3 |
| B3 | Doubling down (M7) on a drawdown raises expectancy | **Failed.** Added lots −5.09 (calls at −25 %), −27.48 (puts at −40 %), −17.75 even with the thesis intact. | same |
| B4 | Scaling in by thirds (M8) is a better entry | **Failed.** The later thirds lose more than the first: −8.19 against −5.14 on Steady calls. | same |
| B5 | Partial profits plus a runner (M3) beat a plain exit | **Failed.** The partial and the runner are positive by construction; the stops and cutoffs on the rest cost more. Example: +52.33 + 43.17 − 107.45 = −11.95. | `05_management_research.md` §4 |
| B6 | Trailing stops (M4) capture the hindsight opportunity | **Failed.** Same median effect as a plain time exit; no trail beats one by more than the noise. | `05_management_research.md` §2 |
| B7 | A thesis exit (a close beyond the setup's invalidation, M5) is setup-specific information | **Failed.** It helps random entries with the same invalidation distance as much. | same |
| B8 | Warnings (RSI back through 50, IV down, spread widening, adverse move) predict losses for calls | **Failed.** Every call interval spans zero. For puts they help significantly but leave −11.58 a trade, an effect of the period's drift. | `05_management_research.md` §5 |
| B9 | Taking profits on credit spreads and short puts raises expectancy | **Failed.** Take 25 %: −12.79 a CPS trade against +7.13 held to expiry; 91–93 % win rates that lose money. | `05_management_research.md` §6 |
| B10 | Selling at 15:50 is as good as holding to expiry | **Failed.** Holding to expiry beat the 15:50 sale by $10–34 a trade on calls, debit spreads and short puts. That is the cost of the last spread and the last minutes; for ETFs it carries the overnight gap. | `05_management_research.md` §1 |
| B11 | Re-entering after a loss, reversing, or closing on an opposite signal (M10, M11) | See `08_portfolio.md` §3. | — |

## C. Validation (Tier I)

| # | Hypothesis | Result | Evidence |
|---|---|---|---|
| C1 | A development winner stays a winner | **Failed for every long-premium cell.** 5 development winners, 0 in validation (e.g. breakout Steady calls with adds +33 lower bound → −156 a trade). | `07_validation.md` §2 |
| C2 | Walk-forward selection finds a positive policy set | **Failed in aggregate:** −2.92 [−7.54, +1.09] over 198,109 trades. Survivors are all put sales. | `07_validation.md` §3 |
| C3 | A hold-out finalist is promotable | **Failed.** 0 of 6. R1 (Holm) and the original R2 failed for all; MSS → CPS lost −76.44 a trade. | `07_validation.md` §4 |
| C4 | Dealer gamma's sign (UW, prior session) separates good days for long premium (H-FLO-1, H-FLO-2, hold-out only) | **Passed as pre-registered; not an edge.** Pooled differences +19.7 and +188.6 a trade (Holm pass), but within each root +1.7 and +8.8 points of premium, not significant. Long premium still loses on negative-gamma days. | `07_validation.md` §5 |

## D. Portfolios (Tier I)

| # | Hypothesis | Result | Evidence |
|---|---|---|---|
| D1 | A portfolio of Steady trades on QS signals at $1,000 a trade is viable | **Failed.** −$38,668 on $100,000 in 3.4 years, max drawdown −43 %. | `08_portfolio.md` |
| D2 | Pooling every setup diversifies the losses away | **Failed.** Pooled Steady trades ruined the account: equity $410. | same |
| D3 | The best finalist (QS → cash-secured put) is worth trading | **Failed on capital use.** +0.8 % a year; the collateral limits it to one or two positions. | same |

## E. Method failures found and corrected (kept here because they changed conclusions)

| # | What was wrong | Effect | Correction |
|---|---|---|---|
| E1 | The random-minute control (RND) took the setup's direction at minutes before the event | Momentum setups looked worse than random by $30–110 a trade; reversal setups better. Stage-1 "vs RND" and R2 were biased. | Amendment L-A2: RND-after and FLIP controls; the bias measured directly (`results/tier1/rnd_lookahead_split.csv`) |
| E2 | Entry-rule "taken" comparisons were pooled across structures | Mislabelled columns | Per structure, like for like (`04_entry_research.md` §2) |
| E3 | The first M10/M11 portfolio configurations could not trigger their rules | P2r, P3r and P3c equal their bases | Pooled setups at one contract on an uncapped account (`08_portfolio.md` §3) |
| E4 | The daily tier's expiration picker chose expirations not yet listed on the entry day | Position, Long-Dated and LEAPS entries silently dropped (SPY all-days: 149, 83 and 15 of 560 Mondays) | Picks restricted to expirations quoted that day (`lc/daily.py` `listed_ranges`); daily tier rerun |
| E5 | 2012–2016 SPY/QQQ/IWM 1-minute bars are empty at the vendor; 264 SPY minute files had text prices | Underlying closes | Parity closes with measured error; files re-fetched as numbers (`01_data_inventory.md`) |
