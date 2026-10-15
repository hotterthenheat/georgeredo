# Lifecycle research — 5. Position management (deliverable 4)

**Scope**
- Tier I, same-day index options: SPY, QQQ, SPXW, IWM.
- Development and validation sessions only (2022-05 → 2025-09); the hold-out is reported in `07_validation.md`.
- 113,428 setup events from 12 setups, each entered in every structure its direction allows. Each position is managed by every applicable policy of the pre-registered grid (116 policies, families M0–M13, `02_protocol.md` §5).
- The same positions entered at random minutes of the same sessions (5 seeds) are run through the same grid. That shows whether a policy helps because of the setup or would help any entry.

**Units**
- All figures are dollars per unit after fees ($0.70 a contract a side): one contract per leg, or one SPX-sized contract for SPXW.
- Intervals are 95 %, bootstrapped over trading days, with SPY, QQQ, SPX and IWM on the same date counted as one cluster.
- "vs hold" is the paired difference from holding the same positions to the 15:50 cutoff (M0).

Full per-policy tables: `results/tier1/tables/grid_<structure>_real.md` and `_rnd.md`. Raw cells: `results/tier1/grid_by_structure.csv` and `grid_by_setup.csv`.

## 1. The baseline: hold to 15:50, and the best policy for each structure

| Structure | Trades | Hold to 15:50: win, expectancy | Best policy | Its expectancy [95 %] | vs hold [95 %] | Return on premium |
|---|---|---|---|---|---|---|
| Steady call (LC-S) | 42,709 | 37 %, −15.43 | hold to expiry | +17.65 [−32.4, +81.2] | +33.1 [+15.0, +52.2] | +4 % |
| Big Payoff call (LC-B) | 42,593 | 18 %, −9.40 | hold to expiry | +0.74 [−28.4, +43.1] | +10.1 [+2.5, +19.3] | +1 % |
| Debit call spread (DCS) | 38,989 | 40 %, −28.00 | hold to expiry | +5.60 [−16.5, +30.3] | +33.6 [+22.6, +46.2] | +2 % |
| Steady put (LP-S) | 39,000 | 29 %, −81.84 | exit when RSI(14) crosses back through 50 | −11.58 [−17.0, −5.2] | +70.3 [+24.5, +112.8] | −2 % |
| Big Payoff put (LP-B) | 39,225 | 14 %, −33.56 | exit when RSI(14) crosses back through 50 | −6.76 [−9.9, −2.5] | +26.8 [+3.1, +47.0] | −5 % |
| Debit put spread (DPS) | 36,783 | 32 %, −61.64 | exit when RSI(14) crosses back through 50 | −17.61 [−19.7, −15.6] | +44.0 [+25.3, +63.8] | −6 % |
| Credit put spread (CPS) | 41,339 | 81 %, −9.63 | hold to expiry | +7.13 [−0.4, +14.6] | +16.8 [+12.1, +21.1] | +14 % |
| Cash-secured put (CSP) | 41,588 | 80 %, +11.99 | hold to expiry | +38.14 [+2.9, +70.2] | +26.1 [+12.9, +39.9] | +19 % of credit; ~0.1 % of the cash set aside |

**No long-premium structure has a policy with a positive expectancy whose lower bound clears zero.** Calls, puts and debit spreads all fail, among 116 policies run on 39–43 thousand trades each. The only structure with policies whose lower bound clears zero is the cash-secured put, and section 6 shows that is the put-selling carry rather than the setups.

## 2. What each management family did (median across a family's policies, vs hold to 15:50)

| Family | Steady call: setups / random minutes | Steady put: setups / random minutes | Debit call spread: setups / random minutes | Reading |
|---|---|---|---|---|
| M0 hold to expiry instead of 15:50 | +33.1 / +34.7 | +1.2 / +6.7 | +33.6 / +34.0 | Selling at the 15:50 bid gives up the last spread and the last minutes of an in-the-money contract's value. Expiry avoids both but carries exercise into shares and the overnight gap (ETFs) — see §5. |
| M1 time exit (15–120 min) | +5.1 / −4.1 | +57.3 / +25.1 | +13.6 / +9.2 | Short holds lose less than long ones; for puts in 2022–25's rising market, much less. |
| M2 stop / target | +5.0 / −6.7 | +48.9 / +17.4 | +12.3 / +8.5 | As M1: limits the time a losing side is held. |
| M3 partials and a runner | +3.5 / −6.2 | +60.2 / +22.7 | +11.8 / +6.3 | Same effect as M1/M2; no partial schedule beats a plain time or stop exit by a margin outside the noise. |
| M4 trailing only | +3.1 / −6.8 | +57.6 / +23.5 | +9.2 / +5.3 | Same. |
| M5 thesis (a close beyond the setup's invalidation) | +0.5 / +6.3 | +33.3 / +20.0 | +6.1 / +5.4 | Helps little. A random entry's invalidation is placed the same distance away, and it helps as much there. |
| M6 add on confirmation | −4.2 / −4.8 | −12.9 / −14.7 | −11.9 / −13.9 | **Hurts.** The added contracts lose on their own (below). |
| M7 double down | −6.1 / −0.7 | −8.7 / +1.5 | −8.4 / −9.1 | **Hurts.** The added contracts lose. |
| M8 scale in by thirds | +5.2 / −2.9 | +33.9 / +10.6 | +10.0 / +6.4 | Less capital in the trade early, so less lost. Not a better entry: the later thirds lose more than the first. |
| M9 reduce or exit on a warning | +1.7 / −4.5 | +33.4 / +13.4 | +6.5 / +3.5 | For puts, every warning helps significantly (below). For calls, none differs from holding. |

**The pattern is the same on random entries as on setup entries.** Exits that shorten a losing hold help both, and adding to positions hurts both. The value of management here is risk truncation on entries whose expectancy is negative; it does not come from the setups.

## 3. Adding, doubling down, scaling in: the added contracts measured on their own

Each lot is accounted separately; an exit is allocated to the lots pro rata.

| Policy | Structure | Original lot | Added lots | Total |
|---|---|---|---|---|
| Add 1 unit after +1 ATR(5m) in favour (M6_k1_max1) | Steady call | −15.43 | **−8.83** | −24.26 |
| Add up to 2 units (M6_k1_max2) | Steady call | −15.43 | **−16.77** | −32.21 |
| Add 1 unit, with stop 35 % / target 50 % | Steady call | −7.88 | **−1.68** | −9.56 |
| Add 1 unit after +1 ATR(5m) | Steady put | −81.84 | **−60.27** | −142.11 |
| Double down at −25 % | Steady call | −15.43 | **−5.09** | −20.53 |
| Double down at −40 % | Steady put | −81.84 | **−27.48** | −109.32 |
| Double down at −40 %, only if the thesis stands | Steady put | −46.73 | **−17.75** | −64.49 |
| Scale in by thirds | Steady call | −5.14 (first third) | **−8.19** (later thirds) | −13.33 |
| Scale in by thirds | Steady put | −27.28 | **−44.03** | −71.31 |

**Every form of adding loses money on the added contracts.**
- **Adding after confirmation** buys a dearer option after the move it was waiting for.
- **Doubling down** buys more of a position whose thesis is failing.
- **Neither improved the chance of finishing ahead.** A lower average entry price did not raise the probability of a profitable exit; it raised the size of the loss.

## 4. Partials and runners: where the profit and the loss come from

For the partial-and-runner policies, the exits tagged "partial" and "runner" are profitable by construction: they fire only on a gain. The losses sit in the stop and cutoff exits.

| Policy | Structure | Partial 1 | Runner | Everything else (stop, cutoff) | Total |
|---|---|---|---|---|---|
| Sell 50 % at +50 %, runner trails 20 % | Steady call | +52.33 | +43.17 | −107.45 | −11.95 |
| Sell 25 % at +20 %, runner trails 20 % | Steady call | +16.91 | +43.98 | −74.78 | −13.89 |
| Sell 50 % at +50 %, runner trails 20 % | Steady put | +53.12 | +49.09 | −128.51 | −26.30 |

**Report the whole decomposition, not the partial or the runner alone.** Either alone looks like an edge; the total is negative.

## 5. Warnings (M9): acted on, against holding

| Warning | Steady call, exit: vs hold [95 %] | Steady put, exit: vs hold [95 %] | Steady put, reduce half: vs hold [95 %] |
|---|---|---|---|
| W1 RSI(14) back through 50 | +5.2 [−56.5, +49.2] | **+70.3 [+24.5, +112.8]** | +35.1 [+12.2, +56.4] |
| W2 ATM IV down ≥ 10 % since entry | +1.4 [−50.6, +34.4] | +31.6 [+10.9, +52.2] | +15.8 [+5.4, +26.1] |
| W3 structure spread ≥ 2 × entry | −1.3 [−59.6, +38.7] | +50.0 [+9.0, +90.2] | +25.0 [+4.5, +45.1] |
| W4 adverse move ≥ 1 ATR(5m) | +4.1 [−38.5, +34.8] | +44.0 [+14.3, +71.8] | +22.0 [+7.2, +35.9] |

- **For puts, every warning was observable before the exit and improved the result significantly, all on the same trades.** It still did not make the trades profitable: the best put policy is −11.58 a trade.
- **For calls, no warning distinguished deterioration from noise.** Every interval spans zero.
- **The asymmetry is the period's drift.** A put held through 2022–2025 is held against the trend, so anything that shortens the hold helps. It is not evidence that the warnings predict losses in general.

## 6. Short premium (CPS, CSP): taking profits and stops

| Policy | CPS: setups / random minutes | CSP: setups / random minutes |
|---|---|---|
| Hold to 15:50 | −9.63 / −7.12 | +11.99 / +19.75 |
| Hold to expiry | +7.13 / +8.21 | +38.14 / +42.88 |
| Take 50 % of the credit, stop at 2 × | −8.13 / −7.34 | +4.75 / +7.61 |
| Stop at 2 × credit only | −5.24 / −4.31 | +21.71 / +24.65 |
| Take 25 % of the credit, no stop | −12.79 / −10.04 | −8.31 / −1.19 |

**Profit-taking hurts both structures.**
- It caps the many small wins and leaves the rare large losses in place.
- The win rates make it look attractive: 91–93 % for take-25 %.

**Holding to expiry was best, and the setups were worse than random minutes on every row.** The positive CSP numbers are the variance-risk premium of same-day index puts in a rising market. They are not a property of when a setup fires. The cash set aside is the strike × 100, about $40–60 k for one SPY contract, so a $38 expectancy is roughly 0.1 % of the capital per trade.

## 7. Expiry mechanics

Holding a physically settled ETF option to expiry is modelled as exercise or assignment at the 16:00 close, with the shares sold at the next session's open. Fees are charged on both. The overnight gap is therefore in the result. SPXW settles in cash at the 16:00 value.

The hold-to-expiry advantage over a 15:50 sale is the spread and residual value given up in the last ten minutes. It comes with requirements a trader must meet:
- the buying power for 100 shares a contract;
- carrying the overnight gap.

## 8. What is not here yet

- **M10 (re-entry after a loss) and M11 (reverse on an opposite signal)** change which trades are taken, so they are measured in the portfolio sequencer (`08_portfolio.md`), not here.
- **The daily-resolution management results** (Swing, Position and Long-Dated buckets, single names) are in `06_daily_tier.md` as their runs finish.
