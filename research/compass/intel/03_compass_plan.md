# Market-intelligence brief — 3. What Compass should use, what it should not, and what to build next

**Standard (the brief, §18):**
- Compass shows a finding only where it survived costs and out-of-sample validation.
- Where evidence is missing, Compass says so.
- No unrelated risks are collapsed into an unvalidated score.

## 1. Use, as validated information

| Finding | Evidence | How Compass can show it |
|---|---|---|
| **Index put-writing carries the volatility premium.** SPY and QQQ monthly ATM and 0.30-delta puts sold at the bid kept 34–41 % of premium net, 2012–2026, positive in every three-year block. Not alpha against the index (beta about 0.5), and March 2020 cost 16–21 months of profit. | `../05_results.md` S17 | A carry lane under Premium Selling, labelled as index exposure with its crash risk, never as a signal |
| **Selling options early destroys the short-premium carry.** Taking 25–50 % of the credit turned positive same-day put sales negative on every ticker. | `../lifecycle/12_per_ticker_playbook.md` §5; `../lifecycle/05_management_research.md` §6 | A management note on put sales |
| **Adding to positions loses on the added contracts**, on every ticker, in both periods. | lifecycle 05 §3, 12 §4 | A note against adds and double-downs |
| **Single-name options are expensive to trade.** The ATM monthly straddle's median bid/ask spread is 13 % of its mid. | `02_volatility_pricing.md` V1 | Show the round-trip cost beside every single-name contract |
| **Implied ÷ realized volatility ranks names correctly at the level of volatility, not profit.** The richest quintile saw 2.3 vol points less movement than implied, the cheapest none. | `02_volatility_pricing.md` T1 | A descriptive "options price more/less movement than recent realized" label, with the sentence that selling it did not pay after costs |
| **Earnings implied moves overstate the typical report.** The median report moved 0.59 of the straddle-implied move; 28 % moved more. Selling at the mid earned +6.9 % of premium on same-day settlements, but half the spread is larger. | `02_volatility_pricing.md` V2 | Beside a name's next report: the implied move, this ratio, and that both sides of the trade lost after costs |

## 2. Do not use as trade signals

| Item | Why |
|---|---|
| The 12 Compass entry setups, intraday or daily | As good as random entries after a clean control, on every product tested (lifecycle 04; S04, S06, S07) |
| Daily breakouts and trend pullbacks as long signals | Followed by underperformance across 1,100–1,500 names (S07) |
| Earnings-surprise direction | Underperforms the same-date universe (S08) |
| Flow aggregates, market tide, dark pool, per-strike bursts on index ETFs | Describe the move that just happened; no forward information (`../../../reports/Finding a 0DTE options edge.md`) |
| Selling single-name straddles, or sorting names by IV ÷ RV, term slope or skew to sell or buy them | Negative in development, validation and hold-out; the sort adds nothing (V1) |
| Selling earnings straddles across the report, or buying them into it | −26 % and −21 % of premium (development + validation), −34 % and −29 % (hold-out) (V2) |
| Profit targets, stops, trails, partials on same-day long options | No rule's interval excludes zero on any ticker (lifecycle 12 §3) |

## 3. Build next, in order of expected value

1. **Start the Unusual Whales full-tape archive now, on the always-on machine.**
   - The vendor's history is a rolling 730 trading days, and each trading day the oldest day is lost.
   - Keep per (name, day): signed premium, delta-weighted order imbalance, opening-proxy volume (size above open interest), call-put IV spread and skew.
   - This enables the one flow test with published support: single names, daily horizon, traded in shares.
2. **Extend V1 from 34 months to 14 years.**
   - Pull monthly cross-sections of option end-of-day quotes from ThetaData, about 26 hours, through the owner's own Theta Terminal on the always-on machine so it does not take the login.
   - This also gives the 14-year test of index and ETF put-writing beyond SPY and QQQ.
3. **Let the terminal's recorder keep accumulating the dealer book.** UW's dealer-exposure history starts 2025-10, so the gamma-regime filter (H-FLO, lifecycle 07 §5) can be retested on more years only as it accrues.
4. **Forward paper tests for the three leads** (lifecycle 11 §B and 06 §7):
   - the QS debit call spread;
   - the gamma-regime filter;
   - the failed-breakout put sale.

## 4. What the brief should change

- **"14 years of one-minute data on every contract" is the wrong target.**
  - It is 10–12 TB and years of API time on the current plans.
  - Where the tests ran on the data that exists, they did not find an edge: setups, flow and single-name volatility.
  - End-of-day chains for the whole universe plus one-minute data for the products traded intraday answer the same questions.
- **Stop adding entry-pattern variants.** Each new variant spends the multiple-testing budget the hold-outs need, and the chart-pattern family is exhausted.
- **Where an edge is most likely:**
  - premiums that are paid structurally (index put-writing);
  - information that is not in the price chart (single-name option flow from the tape).

  Both need the data pulls above.
