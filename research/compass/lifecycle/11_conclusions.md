# Lifecycle research — 11. Conclusions (deliverable 10)

**The brief's standard:** "If a setup, option strategy, or management rule does not demonstrate positive and robust net expectancy, report that conclusion directly."

**Direct answer: no setup, option strategy or management rule tested here demonstrated a positive, robust, executable net expectancy.**
- Nothing passed the pre-registered promotion rules on the hold-out.
- The few things that make money do so by carry or market drift that a random entry earns too, not because of the setups.

The ranked conclusions follow, strongest evidence first. Every number is per unit after fees, with 95 % day-clustered intervals; the documents named hold the tables.

## A. What the evidence settles

1. **Same-day long premium (Steady and Big Payoff calls and puts, debit spreads) loses money on these setups, whatever the management** (`05_management_research.md` §1).
   - 116 pre-registered policies on 39,000–43,000 trades per structure: none has a lower bound above zero.
   - The best is a Steady call held to expiry: +17.65 [−32.4, +81.2].
   - Walk-forward over all cells: −2.92 [−7.54, +1.09] (`07_validation.md` §3).
   - Every development winner reversed in validation.
2. **The 12 setups carry no timing or direction information that survives a clean control** (`04_entry_research.md` §1.0).
   - Against a random later minute and against the opposite side at the same minute, with the period's drift netted out, the setups are within $1.50 a trade of random, pooled.
   - 3 positive and 4 negative intervals in 156 tests: what chance produces.
   - This includes the ICT concepts (liquidity sweeps, structure shifts, fair-value gaps).
3. **Adding to positions loses money on the added contracts, every time.** Confirmation adds, double-downs and scale-ins all lose: −1.7 to −60 a trade on the added lots (`05_management_research.md` §3).
4. **Partial profits and runners do not beat plain exits.** Their profitable pieces are profitable by construction, and the losing remainder outweighs them (`05_management_research.md` §4).
5. **Entry timing rules do not select better trades** (`04_entry_research.md` §2).
   - Confirmation and chase guards improve dollars per signal only by trading less: exactly what skipping the same share of signals at random does.
   - Limit orders are adversely selected and lose $12–19 a trade more than marketable orders on Steady options.
6. **Re-entry and reverse rules make a losing signal set lose more per trade** (`08_portfolio.md` §3):
   - reverse: −$17.63 a trade;
   - close on an opposite signal: −$18.14;
   - base: −$14.52.
7. **Profit-taking on short premium hurts** (`05_management_research.md` §6).
   - Taking 25 % of a credit spread's credit turns +7.13 (held to expiry) into −12.79, with a 91–93 % win rate.
   - A high win rate is not evidence of an edge.
8. **What makes money is put-selling carry, and a random entry earns it too** (`07_validation.md` §4–4.1).
   - Cash-secured puts and put spreads on bullish signals were the only finalists.
   - On the hold-out, selling the same put at a random later minute earned within noise of the setups' trades: +4.7 to +21.0 a trade for the cash-secured puts, intervals spanning zero.
   - As portfolios:
     - one cash-secured put at a time earned about 1 % a year on $100,000 (+$987 on the hold-out);
     - the $1,000-risk put-spread portfolio earned 4.8 % a year in development and lost 9.6 % on the hold-out (`08_portfolio.md`).

## B. What the evidence suggests but does not establish

1. **Dealer-gamma sign as a regime** (`07_validation.md` §5).
   - Long premium lost less on days after negative net gamma: pre-registered, run once, Holm-significant pooled.
   - Within each root it is +1.7 points of premium [−0.5, +3.8]: not significant, and long premium still lost money.
   - Worth keeping as a filter to study on more years. It is not an edge.
2. **The QS debit call spread held to expiry** (`07_validation.md` §4.2).
   - Positive in development, validation and the hold-out: +51.7, +46.7, +64.4.
   - It beat a random later minute on the hold-out.
   - But it failed its pre-registered absolute test (p 0.064), and drift-neutral it is no better than random entries.
   - Most likely a bullish spread held through a rising market.
   - It is a hypothesis for sessions after 2026-10-09, with its rule frozen as of this report.

## C. What was not tested, and why

- **Calendars, diagonals, iron condors and iron flies:** out of scope (the brief's "later" structures).
- **Unusual-options-activity setups:** they need per-chain trade or volume history the vendor serves only per request (about 4,000 requests for the 0DTE chains); not pulled (`02_protocol.md` §9).
- **Dark-pool and flow setups inside these lifecycles:** Unusual Whales serves flow, dark-pool prints and the full option tape only for its last 730 trading days (rolling; 2023-11-15 on 2026-10-15), so not across this study's periods. The separate index-ETF study on 339 of those sessions found no intraday edge in net premium, market tide, dark pool or per-strike bursts (`reports/Finding a 0DTE options edge.md`, `research/flow_predictors/`).
- **Dealer positioning before 2025-10-15:** UW's daily greek exposure begins then, so H-FLO could only be tested on one year.
- **Single names at any resolution:** only FB was pulled. The 40-name option EOD pull (about 19 hours) could not run in a session whose container is reclaimed when idle; it is resumable (`scripts/pull_tier_d.py`).
- **Bounce setups on index ETFs before 2017 and on FB:** those closes come from put-call parity (the vendor has no stock bars there), so there is no daily open, and the bounce rules need one.
- **Tick-level fills:** fills use the 1-minute NBBO (Tier I) and the closing NBBO (daily tier); queue position and partial fills are not modelled.

## D. Method corrections that changed conclusions (`10_failed_hypotheses.md` §E)

1. **The random-minute control had a look-ahead** (amendment L-A2).
   - Every original "setups are worse or better than random" statement was an artifact of it.
   - The clean controls show the setups are as good as random.
2. **The daily tier's expiration picker chose expirations not yet listed.** It was fixed before any daily-tier result was used.
3. **The first M10/M11 portfolio configurations could not fire their rules,** and the first rule comparisons ran into ruin and cap effects. Corrected to one contract on an uncapped account.
4. **One hold-out portfolio run used the wrong account size** by a configuration error. It is kept, labelled and superseded.

## E. The daily tier (Weekly, Swing, Position, Long-Dated, LEAPS; single names; earnings)

**Index ETFs, complete** (`06_daily_tier.md` §3–§7):

1. **Any long-dated bullish structure bought on any Monday made money in 2013–2026.**
   - A Steady call in the LEAPS bucket made +$1,326 a contract held to expiry.
   - Any bearish one lost.
   - This is the bar, and it is the market's drift, not a setup.
2. **No daily setup beat buying the same structure on a random day in the same direction on the hold-out.**
   - The 19 walk-forward finalists made +$500–3,500 a trade in 2024–2026.
   - R2 failed for all 19, and the shorter-dated trend-pullback finalists lost money outright.
3. **Bearish daily setups lost heavily against their baselines,** most of all trend-pullback shorts (LEAPS Steady puts −1,052 [−1,417, −654] against shorting every Monday).
4. **Daily management follows the trend's sign:** hold and add on the trend side, cut after 5 sessions against it. No rule helped both sides.
5. **The day before the Fed carries no straddle edge either way** through the announcement (5-session hold).
6. **One daily cell is a hypothesis for a fresh hold-out:** failed-breakout put sales in the Swing bucket. It cleared both baselines in development + validation on about 100 trades, but was not a walk-forward finalist.

**Single names, earnings and cash-secured-put assignment: untested on a credible sample.**
- Only FB (2017-06 → 2022-06) was pulled before the session's container was reclaimed while idle.
- On FB the setups were as good as random, and the pre-earnings straddles had 2–20 trades a cell, under the 30-trade floor (`06_daily_tier.md` §8).
- The remaining 40 names need about 19 hours of pulling on an always-on machine.

## F. What this means for Compass

- **No setup should be shown as a trade signal on the strength of this research.**
  - The setups do not select better entries than a random minute.
  - No management rule makes their long-premium trades profitable.
- **Two descriptive uses are supported:**
  - Put-selling carry and the market's drift exist, and a structure that harvests them (cash-secured puts, put spreads held to expiry, long calls held long-dated in a rising market) will show a positive history whether or not a setup fired.
  - A dealer-gamma regime label describes days on which long premium lost less.
- **Any future claim of an edge needs, at minimum:**
  - a fresh hold-out (sessions after 2026-10-09);
  - a control without look-ahead, with the period's drift netted out;
  - a comparison against simply holding the same structure on all days.
