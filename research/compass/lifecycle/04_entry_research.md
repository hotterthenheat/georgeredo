# Lifecycle research — 4. Entries (deliverable 3)

**Scope**
- Tier I, same-day index options: SPY, QQQ, SPXW, IWM.
- Development and validation sessions only (2022-05 → 2025-09).
- 12 setups, each entered in every structure its direction allows (`02_protocol.md` §3–§4).

**Units**
- Dollars per unit after fees.
- 95 % intervals bootstrapped over trading days, with the four roots on one date counted as one cluster.

**Raw cells**
- `results/tier1/stage1_cells.csv`: setup × structure × policy, with the original control.
- `results/tier1/controls_*.csv`: the corrected controls, §1.
- `results/tier1/entry_rules_vs_E0.csv` and `entry_filters.csv`.

## 1. Setups against random entries

**Three comparisons, each paired by trading day, development + validation**
- **RND-after:** the setup's trade against the same structure entered at a random later minute of the same session, in the same direction (5 seeds).
- **FLIP:** the setup's trade against the mirrored structure at the same minute: Steady call against Steady put, Big Payoff call against put, debit call spread against debit put spread.
- **Drift-neutral versions of both:** 2022–2025 rose. A call beats a put at any minute, and an earlier call rides more of the session's rise, so each comparison is flattered for bullish signals and penalised for bearish ones. Pooling a setup's bullish and bearish trades cancels most of that. These are the comparisons that answer "does the setup know something?".

**Files:** `results/tier1/controls_summary.csv` (every setup × structure × stage-1 policy, the three controls side by side); `controls_after_drift_neutral.csv` and `controls_flip_drift_neutral.csv` (by structure family).

### 1.0 Results

**Drift-neutral, 30-minute exit** (dollars a trade, setup minus control [95 %]):

| Setup | Steady vs a later minute | Steady vs the other side | Debit spread vs a later minute | Debit spread vs the other side |
|---|---|---|---|---|
| QS (Quick Scalps) | −7.0 [−19.4, +4.2] | −0.8 [−24.2, +21.5] | −4.3 [−10.4, +1.4] | −0.9 [−12.7, +10.5] |
| TP (trend pullback) | +5.0 [−16.8, +27.7] | −18.0 [−74.7, +34.0] | +4.1 [−7.6, +15.3] | −8.2 [−36.9, +18.5] |
| BO (breakout) | −22.2 [−54.4, +5.3] | −34.4 [−104.7, +30.0] | −9.7 [−25.3, +3.2] | −16.8 [−50.0, +15.2] |
| BOF (failed breakout) | −5.4 [−36.6, +26.9] | −2.3 [−64.8, +59.2] | −3.6 [−19.2, +11.9] | −0.9 [−32.9, +31.3] |
| LS (liquidity sweep) | −10.6 [−25.6, +4.7] | −19.9 [−49.9, +9.3] | −4.3 [−11.5, +3.1] | −8.3 [−23.0, +6.0] |
| MSS (structure shift) | +5.2 [−41.9, +53.2] | −10.3 [−90.2, +69.6] | +1.0 [−21.2, +24.1] | −6.7 [−45.4, +31.5] |
| FVG (fair-value gap) | −6.9 [−20.0, +7.1] | −2.4 [−27.9, +22.6] | −3.8 [−10.1, +2.6] | −3.1 [−15.4, +9.3] |
| TPp (pullback, trigger only) | −2.3 [−12.4, +6.7] | +12.1 [−7.9, +29.4] | −0.9 [−6.2, +3.8] | +6.4 [−3.5, +16.0] |
| BOp (5m breakout, trigger only) | −4.8 [−14.4, +4.8] | +13.0 [−9.1, +33.1] | −3.8 [−8.8, +0.9] | +4.6 [−6.2, +14.5] |
| BOr (breakout retest) | −5.2 [−15.5, +4.4] | +3.4 [−17.7, +23.7] | −2.9 [−8.0, +2.1] | +0.7 [−9.6, +10.9] |
| BNp (bounce, trigger only) | +7.6 [−3.0, +17.6] | −17.7 [−46.0, +7.2] | +4.7 [−0.5, +9.6] | −4.7 [−17.1, +6.8] |
| VWR (VWAP reclaim) | +2.1 [−1.4, +5.6] | +1.4 [−2.7, +5.5] | **+1.5 [+0.2, +2.9]** | +0.5 [−1.7, +2.6] |
| **All setups pooled** | −0.6 [−3.9, +2.4] | −1.5 [−8.2, +4.4] | −0.1 [−1.6, +1.2] | −0.6 [−3.7, +2.2] |

**Held to expiry**, the drift-neutral cells whose interval excludes zero:
- worse than a later minute: BO Steady −62.3 [−127.9, −5.3]; BO Big Payoff −30.4 [−60.7, −4.7]; MSS debit spread −46.4 [−88.7, −4.7];
- better than the other side: BOp debit spread +53.7 [+5.5, +102.6]; BOr debit spread +57.8 [+9.1, +106.5];
- worse than the other side: TP Big Payoff −76.0 [−160.6, −3.5].

**Reading**
- Across the four drift-neutral comparisons there are 156 tests: 13 setups × 3 structure families × 2 exits × 2 controls.
- 3 intervals lie above zero and 4 below; about 8 would by chance at 5 %.
- **Pooled over every setup, the setups' trades are within $1.50 of a random later minute and of the opposite side at the same minute, both ways.**
- **No setup shows timing or directional information that survives a control without look-ahead.**
- The positive cells are isolated (one structure family, one exit), not a pattern across a setup's structures and exits.

**Per structure, without drift neutrality** (`controls_summary.csv`), at the 30-minute exit:
- 8 of 104 cells beat RND-after; 5 of them are TP's bullish structures (Steady call +32.5 [+8.1, +58.1], debit call spread +19.9, cash-secured put +21.6, credit put spread +8.5, Big Payoff call +11.0);
- the same TP signals' bearish structures are 7–18 worse than their controls (intervals spanning zero);
- TP's drift-neutral totals are within noise (table above). Its bullish advantage is the session's rise riding with an earlier entry, not the signal.

**What happened to the original comparison:**
- under RND, 39 of 104 cells at the 30-minute exit were significantly worse than random and 9 better;
- under the clean controls, without drift neutrality, the counts are 3 and 8;
- with drift neutrality, they are as chance predicts.

### 1.1 The original control was biased, and by how much

The protocol's random-minute control (RND) had two properties:
- it drew a minute anywhere in the session's entry window;
- it took the direction the setup had chosen at its own minute.

A control drawn before the event therefore enters in a direction that was only decided after the move that produced the event (amendment L-A2). Splitting the original controls by whether they fell before or after their event shows the size of that look-ahead. Steady options, 30-minute exit, dollars per trade (`results/tier1/rnd_lookahead_split.csv`):

| Setup | Structure | The setup | Controls before the event | Controls at or after it |
|---|---|---|---|---|
| Breakout (5m, trigger only, BOp) | Steady put | −24.0 | **+111.8** | −11.3 |
| Breakout (5m, trigger only, BOp) | Steady call | −1.3 | **+78.7** | −6.7 |
| Quick Scalps (QS) | Steady call | 0.0 | **+61.9** | −6.3 |
| Quick Scalps (QS) | Steady put | −28.3 | **+81.7** | −13.5 |
| Bounce (trigger only, BNp) | Steady call | −10.1 | **−89.4** | −19.0 |
| Failed breakout (BOF) | Steady put | −43.2 | **−103.2** | −25.7 |
| Trend pullback (trigger only, TPp) | Steady call | −11.6 | −13.3 | −14.7 |

**What the bias did:**
- A control placed before a momentum event bought the move that later triggered the event.
- A control placed before a reversal event bought into the move that was about to reverse.
- So the original comparison made every momentum setup look worse than random and every reversal setup look better.
- Setups whose trigger is not a recent move in the traded direction (TPp, VWR) are hardly affected.

**What it invalidates:**
- every stage-1 "vs RND" figure;
- the protocol's promotion rule R2, on development, validation and the hold-out;
- the "setups were worse than random minutes" statements in `05_management_research.md` §6.

**Three controls are reported side by side:**
- the original control, for the record;
- **RND-after:** a random later minute, same session, same direction;
- **FLIP:** the same minute, the opposite direction.

## 2. Entry rules: how to get in once a setup fires

**The rules** (`02_protocol.md` §5 and amendment L-A1). Each is applied to the same events as entering at the signal (E0) and paired by day:
- **E1L1, E1L3:** enter 1 or 3 minutes late (latency).
- **E1L3g:** enter 3 minutes late, but skip the trade if the structure's mark has moved more than the chase guard in the trade's favour.
- **E2:** wait for a 1-minute close beyond the signal bar in the trade's direction (confirmation), then choose the structure at that minute.
- **E2g:** E2 with the chase guard.
- **E3:** a limit order at mark − ¼ spread, good for 10 minutes.
- **E3atr:** a limit at mark − |delta| × 0.25 × ATR(5m), good for 10 minutes.

**Three questions are asked of each rule, and they have different answers:**

| Question | Comparison |
|---|---|
| A. Does the rule raise the dollars made per setup signal? | the rule against E0 on every event, a skipped trade counted as $0 |
| B. Is a trade the rule takes better than a trade at the signal on average? | the rule's expectancy per trade taken against E0's per trade |
| C. On the events the rule trades, does its timing beat E0's? | the rule's taken trades against E0 on those same events, like for like |

**A benchmark for A: skipping at random.**
- On a structure whose expectancy is negative, any rule that trades less makes A positive.
- Skipping the same share of signals at random improves A by (share skipped) × |E0's expectancy|.
- A rule adds information only if it beats that benchmark.

### 2.1 Results at the 30-minute exit (M1_t30)

| Rule | Structure | Taken | E0 per trade | Rule per trade taken (B) | A: rule − E0 per signal [95 %] | Skipping at random | C: rule − E0, same events [95 %] |
|---|---|---|---|---|---|---|---|
| E1L1 | Steady call | 100 % | −9.91 | −10.94 | −1.02 [−2.0, −0.1] | 0 | — |
| E1L3 | Steady call | 100 % | −9.91 | −11.33 | −1.41 [−2.8, −0.1] | 0 | — |
| E1L3 | Steady put | 100 % | −20.14 | −20.90 | −0.76 [−2.8, +1.5] | 0 | — |
| E1L3g | Steady call | 78 % | −9.91 | −9.89 | +2.20 [−0.6, +4.9] | +2.18 | +25.28 [+23.4, +27.4] |
| E1L3g | Steady put | 77 % | −20.14 | −20.29 | +4.46 [+0.8, +8.5] | +4.57 | +31.39 [+29.1, +33.8] |
| E2 | Steady call | 73 % | −9.91 | −11.55 | +1.51 [−1.4, +4.5] | +2.70 | −47.46 [−50.6, −44.4] |
| E2 | Steady put | 69 % | −20.14 | −22.30 | +4.74 [+0.6, +9.1] | +6.24 | −60.50 [−64.3, −56.8] |
| E2g | Steady call | 43 % | −9.91 | −12.43 | +4.59 [+0.2, +9.0] | +5.67 | −14.14 [−16.6, −11.4] |
| E2g | Steady put | 39 % | −20.14 | −20.06 | +12.39 [+6.6, +18.4] | +12.37 | −15.62 [−18.7, −12.6] |
| E2g | Debit call spread | 37 % | −14.39 | −15.07 | +8.88 [+6.6, +11.3] | +9.12 | −7.55 [−8.9, −6.1] |
| E3 | Steady call | 78 % | −9.91 | −37.21 | **−18.94 [−22.0, −16.4]** | +2.22 | +6.34 [+5.3, +7.4] |
| E3 | Steady put | 80 % | −20.14 | −49.42 | **−19.50 [−22.7, −16.3]** | +3.99 | +6.67 [+5.2, +8.3] |
| E3atr | Steady call | 59 % | −9.91 | −37.52 | **−12.30 [−15.8, −9.2]** | +4.04 | +32.08 [+30.3, +34.1] |
| E3atr | Cash-secured put | 49 % | −1.46 | −19.89 | **−8.37 [−10.0, −6.8]** | −0.74 | +21.14 [+19.6, +22.8] |

Full table, every structure and the three stage-1 exits: `results/tier1/tables/entry_rules_vs_E0.md`.

### 2.2 What the entry rules show

**Latency costs a little.**
- One to three minutes late cost Steady calls $1.0–1.4 a trade (intervals just below zero).
- Every other structure's latency effect lies within ±$1.

**Confirmation (E2) and the chase guard (E2g, E1L3g) do not select better trades.**
- Their gain per signal (A) equals what skipping the same share of signals at random would give, within a dollar or two.
- Per trade taken (B), they are no better than entering at the signal and usually slightly worse.
- Like for like (C), confirmation loses $14–60 a trade. The events that confirm are the ones that moved in the trade's favour, and E0 already owned that move.
- The chase guard's large positive C is the mirror image: it keeps the events that moved against the trade, where entering later is cheaper.
- None of these is a forecast. They are the price of the minutes between the signal and the entry.

**Limit entries are adversely selected.**
- E3 and E3atr fill at better prices; their C is $3–34 a trade in their favour.
- But they fill mainly when price moves against the trade, and they miss the trades that run away.
- Per trade taken (B), the trades they get are $20–40 worse than E0's.
- Per signal (A), Steady calls lose $12–19 more than entering at the ask at the signal.

**No entry rule turns any long-premium structure's expectancy positive.** The best per-trade result was E2g on the Steady call under the 35 % stop / 50 % target exit (M2): −4.72 a trade.

**Under the other exits the pattern is the same.** At M0_cutoff and M2_s35_t50, E2g and E1L3g track the random-skip benchmark, and E3 is worse than E0 for every long structure. The one exception: E2g on the Steady call under M2 takes trades at −4.72 against E0's −10.34 a trade, a gain per signal of +8.31 [+3.1, +13.4] against +5.91 for random skipping. That margin is inside the uncertainty of the benchmark and still leaves a losing trade.

## 3. Filters: when to take a signal

Each filter level is the same setups' trades restricted to that level, at the 30-minute exit (`results/tier1/tables/entry_filters.md`).

| Filter | Steady call | Steady put | Debit call spread | Cash-secured put |
|---|---|---|---|---|
| Entry 09:45–11:00 | −12.02 [−23.5, +0.5] | −18.56 [−32.9, −4.6] | −15.37 [−20.7, −9.7] | −4.36 [−12.6, +2.8] |
| Entry 11:00–14:00 | −9.11 [−16.8, −1.6] | −19.52 [−30.3, −9.3] | −13.86 [−17.9, −10.0] | −2.29 [−6.7, +1.8] |
| Entry 14:00–15:00 | −8.13 [−24.8, +8.8] | −25.27 [−50.3, −2.6] | −13.81 [−23.6, −4.0] | +7.25 [−5.3, +18.5] |
| VIX < 15 | −9.03 [−16.7, −1.0] | −10.49 [−18.8, −1.8] | −11.70 [−15.8, −7.6] | −2.26 [−8.4, +3.2] |
| VIX 15–20 | −5.64 [−14.4, +3.1] | −11.35 [−23.1, 0.0] | −11.00 [−15.5, −6.7] | −2.89 [−8.8, +2.5] |
| VIX ≥ 20 | −19.59 [−38.1, 0.0] | **−44.65 [−68.4, −24.0]** | −24.17 [−33.5, −15.3] | +2.40 [−8.5, +12.2] |
| Structure spread ≤ 5 % | −10.05 [−16.3, −3.6] | −20.19 [−28.8, −11.9] | −14.60 [−17.9, −11.2] | −1.34 [−5.7, +2.7] |
| Structure spread 5–10 % | +14.19 [−7.7, +37.3] (728 trades) | −19.50 [−46.2, +5.8] | −12.73 [−17.1, −8.2] | −1.24 [−7.3, +4.9] |

- **No filter level gives any structure a positive expectancy whose interval clears zero.**
- **High volatility is worse for long premium, not better.** With VIX at 20 or more, every long structure loses more, most of all Steady puts. The extra premium paid when volatility is high is not repaid by the larger moves within 30 minutes.
- **Time of day matters less than the exit.** Under a 30-minute exit the three windows are within noise of each other. Under hold-to-15:50 (M0), late entries lose most, as the archive showed (`03_lifecycle_archive.md`).
- **Spread:** the 5–10 % bin of Steady calls is positive but rests on 728 trades and an interval across zero. Steady contracts that wide are rare: deep in-the-money contracts in fast markets.

## 4. ICT concepts, tested as hypotheses

Liquidity sweeps (LS), market-structure shifts (MSS) and fair-value gaps (FVG) are mechanical definitions in `lc/events.py`. The thresholds were fixed before any result (`02_protocol.md` §3).

| Setup | Events | Steady call, 30 min | Steady put, 30 min | Best structure and exit |
|---|---|---|---|---|
| LS (sweep of the prior swing, close back inside) | 1,396 | −8.6 | −35.6 | CSP held to expiry; see `09_setup_strategy_matrix.md` |
| MSS (break of the last swing after a sweep) | 172 | −13.3 | −21.0 | none positive |
| FVG (entry on the return to a 3-bar gap) | 3,550 | −16.1 | −21.7 | none positive |

- All three lose money in every long-premium structure.
- MSS fires too rarely to estimate anything (118 days in 3.4 years).
- Against the clean controls (§1.0) none differs from a random minute: LS −10.6 [−25.6, +4.7], MSS +5.2 [−41.9, +53.2], FVG −6.9 [−20.0, +7.1] for Steady options, drift-neutral, 30-minute exit.

## 5. Entry conclusions

1. **Timing an entry cannot rescue a structure whose expectancy is negative.** Latency, confirmation, chase guards and limits move the result by a few dollars a trade, and each improvement in dollars per signal is explained by trading less.
2. **Limit orders for same-day options lose to marketable orders** on these setups. The fills they get are the trades going wrong.
3. **The filters that matter are the ones that remove trades:**
   - VIX ≥ 20 for long premium;
   - spreads above 10 % of the structure's cost.

   None makes a structure profitable.
4. **None of the 12 setups carries timing or direction information** that survives a control without look-ahead, once the period's drift is netted out (§1.0). The setups do not select better entries than a random minute in the same session.
