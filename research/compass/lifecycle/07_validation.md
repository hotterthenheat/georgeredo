# Lifecycle research — 7. Out-of-sample validation (deliverable 6)

**Scope:** Tier I, same-day index options (SPY, QQQ, SPXW, IWM). The daily tier's validation is in `06_daily_tier.md`.

## 1. The design, fixed before any result (`02_protocol.md` §6)

**Splits**

| Part | Sessions | Use |
|---|---|---|
| Development | 2022-05 → 2024-12 | choosing policies and cells |
| Validation | 2025-01 → 2025-09 | checking what development chose |
| Hold-out | 2025-10-01 → 2026-10-09 | opened once, for the finalists only |

**Walk-forward:**
- quarterly over development and validation;
- a policy is chosen per setup × structure cell on every earlier quarter (by the lower bound of its expectancy, at least 150 trades);
- a 5-session embargo;
- scored on the next quarter.

**Finalists.** A cell becomes a finalist when its walk-forward out-of-sample expectancy is above zero with a lower bound above zero, and its frozen policy is not significantly worse than holding to the 15:50 cutoff.

**Promotion rules, all six needed, scored on the hold-out:**
- **R1** expectancy > 0 with a one-sided bootstrap p below its Holm threshold across the finalists;
- **R2** beats the random-minute control (paired lower bound > 0);
- **R3** profit factor > 1;
- **R4** at least 100 trades on 60 sessions;
- **R5** still positive at +$0.01 a side slippage and with 1-minute latency;
- **R6** the same family's policies are positive on the cell in development (a plateau, not a spike).

**Multiple testing**
- 7,392 configurations were evaluated on development and validation: 12 setups × 8 structures × up to 116 policies, real and control.
- Every interval is a day-clustered bootstrap.
- Walk-forward selection uses only earlier data.
- The hold-out was touched by the six finalists and by the two pre-registered dealer-gamma tests only.

## 2. Development's choices, checked on validation

Each cell's best development policy (by lower bound), run on validation (`results/tier1/dev_choice_then_val.csv`).

| | Cells | Lower bound > 0 in development | …and still > 0 in validation |
|---|---|---|---|
| Long premium (calls, puts, debit spreads) | 66 | 5 | **0** |
| Short puts (CPS, CSP) | 22 | 11 | 4 (QS CSP, BOp CSP, TPp CSP, QS CPS) |

**The long-premium cells that looked best in development reversed in validation:**
- Breakout Steady calls with adds: +33 lower bound in development → −156 a trade in validation.
- Breakout Big Payoff calls: → −51 a trade.
- Breakout debit call spreads: → −66 a trade.
- QS Steady calls with an adverse-move exit: → −16 a trade.

The average validation expectancy over all 88 development choices was −3.90 a trade.

## 3. Walk-forward out of sample

7 quarters (2023-Q3 → 2025-Q3) of policies chosen on earlier quarters alone (`results/tier1/walkforward_oos.csv`).

- **All cells pooled: −2.92 a trade [−7.54, +1.09], 198,109 trades on 438 sessions.**
- 6 of 93 cells had a lower bound above zero:

| Setup | Structure | Trades | Out-of-sample expectancy [lower bound] | Frozen policy for the hold-out |
|---|---|---|---|---|
| BOp (5m breakout, trigger only) | Cash-secured put | 2,602 | +28.79 [+13.77] | stop at 1.5 × credit |
| QS (Quick Scalps) | Cash-secured put | 1,939 | +49.79 [+10.91] | stop at 2 × credit |
| TPp (trend pullback, trigger only) | Cash-secured put | 2,765 | +51.38 [+10.84] | hold to expiry |
| BOr (breakout retest, trigger only) | Cash-secured put | 2,272 | +26.16 [+9.93] | stop at 1.5 × credit |
| QS | Credit put spread | 1,949 | +14.74 [+4.73] | hold to expiry |
| MSS (market-structure shift) | Credit put spread | 15 | +7.13 [+0.20] | take 25 % of the credit |

**Every survivor sells puts. No long-premium cell survived walk-forward.**

**Policies chosen most often** (587 cell-quarters):
- W1 RSI exit (120);
- 20 % stop / 20 % target (104);
- 15-minute exit (76);
- hold to expiry (65).

The choice moved from quarter to quarter: no cell kept one policy throughout.

## 4. The hold-out, opened once for the six finalists (2026-10-15 03:20 UTC)

| Finalist | Hold-out trades / sessions | Expectancy [95 %] | One-sided p | Win rate | Worst trade | +$0.01 slippage | +1 min latency |
|---|---|---|---|---|---|---|---|
| BOp → CSP, stop 1.5× | 1,538 / 160 | +26.30 [+3.78, +45.42] | 0.0086 | 53 % | −1,991 | +24.20 | +27.72 |
| QS → CSP, stop 2× | 1,007 / 91 | +51.73 [+5.42, +88.84] | 0.0115 | 73 % | −2,311 | +50.20 | +51.60 |
| BOr → CSP, stop 1.5× | 1,336 / 154 | +24.67 [+2.79, +43.84] | 0.0125 | 55 % | −2,101 | +22.42 | +27.82 |
| TPp → CSP, to expiry | 1,280 / 146 | +51.95 [−6.95, +98.64] | 0.0416 | 88 % | −6,421 | +50.95 | +51.95 |
| QS → CPS, to expiry | 1,000 / 91 | +5.96 [−19.86, +24.51] | 0.2883 | 91 % | −1,042 | +3.96 | +5.96 |
| MSS → CPS, take 25 % | 67 / 40 | −76.44 [−166.45, +3.72] | 0.964 | 84 % | −1,393 | −83.13 | −76.76 |

**Verdicts** (`results/tier1/holdout_verdicts.csv`):
- **Nothing was promoted.**
- **R1 failed for all six.** The smallest p (0.0086, BOp → CSP) missed its Holm threshold (0.05 / 6 = 0.0083), and Holm stops at the first failure.
- **R2 failed for all six.** Under the original control their edges were −18 to −46 a trade. That control had a look-ahead (amendment L-A2, `04_entry_research.md` §1.1). §4.1 re-scores R2 against a clean control, after the fact. Because R1 already failed, the re-score cannot change the verdict.
- **R3–R6:** R3, R4, R5 and R6 passed for the first five; MSS → CPS failed all four.

**What the finalists are**
- They are cash-secured puts and put spreads on SPY, QQQ, IWM and SPXW in a market that rose through most of 2022–2026.
- A cash-secured put sets aside the strike × 100: $40,000–$70,000 for one contract on SPY or QQQ.
- So +$26–52 a trade is about 0.05–0.1 % of the capital per trade, with single losses up to $6,400.

### 4.1 R2 against the clean control (post hoc)

<!-- R2POST: filled from results/tier1/holdout_r2_after.csv once ctrl_after_holdout finishes -->

## 5. Flow & Positioning: the dealer-gamma regime (H-FLO-1, H-FLO-2)

**What was tested**
- UW's daily dealer greek-exposure covers 2025-10-15 → 2026-10-13: exactly the hold-out, so no development was possible.
- Both tests were fixed in amendment L-A1 and run once (2026-10-15 03:56 UTC).
- The regime for session D is the sign of the previous session's call_gamma + put_gamma on the root (SPX's for SPXW).

| Test | Negative-gamma days | Positive-gamma days | Difference [95 %] | One-sided p | Holm |
|---|---|---|---|---|---|
| H-FLO-1 Steady calls and puts, all directional setups, 30-minute exit | −6.54 a trade (18,005 trades) | −26.24 (11,229) | +19.71 [+6.66, +32.01] | 0.0022 | pass (≤ 0.025) |
| H-FLO-2 the 10:00 long straddle, held to 15:50 | −4.62 (609) | −193.20 (361) | +188.58 [+16.91, +370.90] | 0.0158 | pass (≤ 0.05) |

**Both pre-registered hypotheses pass:** long premium lost less on days after a negative net-gamma reading.

**What the pooled numbers mix (found after the result, from `results/tier1/holdout_flo_stats.json`)**
- The roots differ about tenfold in dollars per unit, and the regime is not spread evenly across them.
- SPX was negative on 65 of 247 days; IWM on 229 of 247.
- The positive-gamma side is therefore weighted toward SPXW's large losses. Part of the pooled difference is root mix, not regime.

**Within each root, in return on premium** (post hoc, `results/tier1/holdout_flo_within_root_posthoc.json`):

| Test | SPY | QQQ | IWM (18 positive days) | SPXW | Equal-weight mean [95 %], one-sided p |
|---|---|---|---|---|---|
| H-FLO-1 | +4.1 pp [+1.4, +6.8] | +1.9 pp [−1.1, +4.8] | −1.0 pp [−5.6, +4.2] | +1.8 pp [−1.8, +5.1] | +1.7 pp [−0.5, +3.8], 0.055 |
| H-FLO-2 | +0.6 pp [−16.7, +18.5] | +4.4 pp [−10.9, +20.2] | +11.9 pp [−27.6, +44.0] | +18.2 pp [−3.6, +43.3] | +8.8 pp [−6.2, +23.8], 0.127 |

**Reading:**
- The direction holds in seven of eight root × test cells, and SPY's Steady trades are significant on their own.
- Once root mix is removed, the regime effect is a few points of premium and not significant at the 5 % level.
- **On every root and in either regime, the trades still lost money**, with one exception: the SPXW straddle on negative-gamma days, +6.5 % of premium on 65 days, an interval across zero.
- **Dealer-gamma sign is a regime descriptor worth keeping as a filter to study. It is not an edge.** One year is one sample of regimes.

## 6. What validation says

1. **No configuration is validated.** No setup, structure and management rule passed the promotion rules on the hold-out.
2. **What survives out of sample is put-selling carry.** The variance-risk premium of same-day index puts in a rising market. It is not a property of the setups' timing. The clean-control comparison (§4.1 and `04_entry_research.md` §1) says how much, if anything, the setups add.
3. **Long same-day premium has no out-of-sample edge in any cell:**
   - every development winner reversed in validation;
   - the walk-forward pool is negative.
4. **A fresh hold-out exists from 2026-10-12 onward** (sessions not yet in this archive). Any configuration that is to be promoted later must pass there, with its rules frozen as of this report.
