# Market-intelligence brief — 1. Audit, coverage and gaps (2026-10-15)

**The brief:** "Slayer Terminal — Complete Options Intelligence, Market Research, Fair Value, and Trade Optimization Engine" (21 sections).

**What this file does:**
- maps every section of the brief to the work that answers it;
- records what was verified today;
- lists the data the brief names that we do not have, and what each gap rules out.

The detailed inventory is `../lifecycle/01_data_inventory.md` and `../../../DATA_PROVIDER_AUDIT.md`; this file does not repeat them.

## 1. The brief against the work

| § | Asked | Status | Where |
|---|---|---|---|
| 1 | Audit data, codebase, coverage | Done; updated today (§2 below) | `../lifecycle/01_data_inventory.md`, `../02_coverage_matrix.md`, this file |
| 2 | Behaviour profile per ticker | Partly: same-day and daily profiles for SPY, QQQ, IWM, SPX; daily triggers on 1,100–1,500 names; intraday triggers on 34 names | `../lifecycle/12_per_ticker_playbook.md`, `../05_results.md` S07, S06 |
| 3 | Relationships, leaders and laggards | Not run in this pass (§4) | — |
| 4 | Fair value: options and underlyings | Options: V1 and V2 measure whether implied volatility is above what followed, net of the bid/ask. Underlyings: no fundamentals history (§3) | `02_volatility_pricing.md` |
| 5 | Every expiration and strike | Full same-day chains on index products, every expiration of SPY/QQQ/IWM from 2012, single-name monthlies (V1) and report-week expirations (V2). Not every strike of every single-name expiration for 14 years (§5) | lifecycle 04–12, `02_volatility_pricing.md` |
| 6 | Volatility intelligence | V1 (implied against realized, term slope, skew), V2 (earnings run-up and crush), S15 (same-day), S17 (index put-writing) | `02_volatility_pricing.md`, `../05_results.md` |
| 7 | Flow, positioning, dealer effects | Index-ETF flow on 339 sessions, dealer gamma on one year. Single-name flow from the full tape not run (§4) | `../../../reports/Finding a 0DTE options edge.md`, `../lifecycle/07_validation.md` §5 |
| 8 | False breakouts, traps, suspicious moves | Breakouts underperform at daily resolution across the universe; intraday triggers fire after the move. Manipulation cannot be established: no order book, no participant codes (§3) | `../05_results.md` S06, S07; lifecycle 04 |
| 9 | New patterns, regimes | V1 and V2 are this pass's new families. Open-ended machine-learning search not run: it spends the multiple-testing budget the hold-outs need | `02_volatility_pricing.md` |
| 10–13 | Lifecycle, entries, sizing, adds, stops, exits | Done | lifecycle 04, 05, 08, 12 |
| 14 | Contract selection | Steady, Big Payoff, spreads and put sales by expiry bucket and ticker | lifecycle 05, 06, 09, 12 |
| 15 | Market context | Dealer-gamma regime, Fed days, regime cuts. Breadth not built | lifecycle 06, 07 |
| 16 | Backtesting framework | Point-in-time, NBBO fills, walk-forward, Holm, hold-outs opened once | `../engine/`, `../lifecycle/lc/` |
| 17 | Evidence labels | Used throughout | every report |
| 18 | Compass integration | `03_compass_plan.md` | |
| 19 | Infrastructure | §5 below | |
| 20 | Deliverables | Index in `README.md` | |

## 2. Verified today

- **Unusual Whales historical chains carry the official closing quote.** On 2026-10-09 their `nbbo_bid`/`nbbo_ask` equal ThetaData's closing NBBO on 638 of 638 contracts (AAPL, CRWD, SOFI, XOM, PLTR, the 2026-11-20 expiration).
- **Unusual Whales history is a rolling 730 trading days.** The earliest date is 2023-11-15 today; it was 2023-11-13 two days ago. Every trading day, the oldest day is lost for good.
- **The full option tape** is a daily zip of every option print, with the NBBO at the print, side tags, IV, Greeks and open interest. 2023-11-16 is 692 MB zipped; downloads run at about 19 MB/s.
- **The chain endpoint** takes 0.3–0.6 s per (ticker, date, expiration) and sustains 9–10 requests a second at the plan's three concurrent requests.
- **The listed-expirations endpoint returns nothing for past dates** (CRWD, 2024-02-26).
  - **Correction (2026-10-15, later the same day):** this note then said past expirations "are found by requesting candidate Fridays". That assumed single names expire only on Fridays, and they do not.
  - ThetaData's list of every expiration a name has had (`option_list_expirations`, `../studies/expiry_calendar_theta.py`) shows Monday and Wednesday expirations on:
    - AAPL, AMZN, AVGO, GOOGL, META, MSFT, NVDA and TSLA since 2026-02-02;
    - AMD, INTC and MU since 2026-07-13.
  - Several ETFs list other weekdays as well; SPY, QQQ and IWM list every weekday.
  - Unusual Whales' chains agree on 3,616 of 3,618 sampled name-dates (`../studies/expiry_calendar.py`, `../results/expiry_calendar/`).
  - Past expirations are now read from ThetaData's list, never from a weekday rule.
- **ThetaData allows one login per key.** Using it in market hours signs out the owner's terminal, so this pass used Unusual Whales only.
- **Unusual Whales' sector and issue type are a current snapshot**, not point in time.

## 3. Data the brief names that we do not have

| Missing | What it rules out |
|---|---|
| Order book depth for options and stocks | Spoofing, layering and order-book imbalance; any manipulation finding beyond price, volume and quotes |
| Participant and open/close codes | Who traded and whether a print opened or closed a position. Size above open interest is at best an inferred proxy |
| Point-in-time sector, industry and index membership | Sector-relative analysis uses today's sectors (a small look-ahead) |
| Fundamentals, guidance and analyst history | Fundamental fair value of the underlying |
| Corporate-action and dividend feeds | Splits are detected from price ratios (A8.1); early exercise around dividends is ignored |
| Halts and limit-up/limit-down events | Not verified as available |
| Futures, currencies, and rates before 2024 | Cross-asset context; a stated rate is used in the pricing models |
| NDX index data | Separate Nasdaq add-on, not entitled |
| Stock 1-minute bars before 2017 | ThetaData returns rows with NaN prices for 2012–2016 |
| Bulk history files | ThetaData's flat files start 2026-10-06 on this account |

## 4. Not run in this pass, and why

- **Relationships and lead-lag across the universe (§3 of the brief).** Daily data for every symbol is on disk (2023 →), so it can be built. The published evidence puts any daily lead-lag between liquid names inside trading costs, so it would serve Compass as context ("is the sector confirming?"), not as an edge. It ranks below V1 and V2.
- **Single-name flow from the full tape (Pan & Poteshman, Hu 2014).** This is the one flow test with published support, and it is single names, not index products. It needs about 700 GB streamed, roughly 10 hours, which only an always-on machine can finish. Because the window rolls, it should start soon.
- **Open-ended pattern search.** Every extra search shrinks what the hold-outs can confirm. V1 and V2 were chosen because they have prior published support and a direct options expression.

## 5. What the full scope would cost

- **The whole U.S. option tape at 1-minute NBBO, 2012–2026:** about 10–12 TB and more than 200 million requests, which is years of wall time at the plan's concurrency (`../lifecycle/01_data_inventory.md` §3). Not feasible on the current plans.
- **Option end-of-day for every root, every session, 2012–2026, from ThetaData:**
  - about 21 million root-sessions at the measured 1.85 a second, about 130 days.
  - A monthly cross-section (about 1,000 roots × 170 month-ends) is about 26 hours. It would extend V1 from 34 months to 14 years.
  - It should run through the owner's own Theta Terminal on the always-on machine, so it does not take the login away from it.
- **The Unusual Whales full tape for its 730 days:** about 700 GB downloaded once and streamed, keeping daily per-name summaries of about 1 GB.
