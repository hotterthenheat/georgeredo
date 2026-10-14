# Compass full-history research protocol (pre-registered 2026-10-14)

This is the evaluation protocol the engine in `research/compass/engine/` implements. It is fixed before any experiment is run; changes are recorded as dated amendments at the end, never by editing the rules above them. Every number the engine reports is produced by this protocol; a run that deviates from it is labelled exploratory in the registry and cannot be used for promotion.

## 1. Objective

Find the Compass configuration — signal rules, contract selection, exits, expiration-specific and setup-specific settings, ranking — with the strongest reproducible, after-cost, out-of-sample evidence for **long single-leg options** (calls and puts) on the U.S. optionable universe, and state plainly if none meets the gate. Defined-risk multi-leg structures are evaluated separately only if the owner places them in scope. Short premium stays outside this protocol (registry `H15`).

## 2. Data and history (the coverage matrix is `02_coverage_matrix.md`)

| Input | Source | Used from | Role |
|---|---|---|---|
| Underlying daily bars, every symbol | ThetaData `stock_history_eod` (`data_lake/thetadata/stock_eod/`) | first year available (pinned by the probe) → 2026-10-13 | universe tiers, regimes, year tables |
| Underlying 1-minute bars | ThetaData `stock_history_ohlc` 1m | 2012-06 (single names), tape floors per symbol as pinned | signals, VWAP, relative volume, structure |
| Index 1-minute values (SPX, VIX, RUT) | ThetaData `index_history_price` 1m | 2017-01 | regime variables, SPXW signals |
| Option contracts listed on a date | ThetaData `option_list_contracts` / expirations per root | 2012-06 | point-in-time chain, no survivorship |
| Option NBBO at decision and exit minutes | ThetaData `option_history_quote` 1m (and 1s where a fill audit needs it) | floor pinned by the probe (2012–2014) | fills, spread filter, delta via implied vol |
| Option volume (intraday cumulative) and OI | ThetaData `option_history_ohlc` 1m, `option_history_open_interest` | 2012-06 | liquidity filters |
| Implied volatility, Greeks | computed by the engine from NBBO mid with the same Black-Scholes conventions as `3abida/src/core/greeks.ts` (r from ThetaData's rate series when available, else a stated constant; dividends as stated) | wherever quotes exist | delta band, expected move |
| Earnings dates | Unusual Whales `earnings` table (`data_lake/unusualwhales/earnings`) | ~2025-10 → 2026-10 only | Earnings/Events family — short window, reported as such |
| Flow, dealer exposure, dark pool | Unusual Whales (floors: 2023-11-13 / 2025-04-01) | their actual windows | optional features, evaluated against a matched baseline over the same dates only |
| Session calendar, early closes, FOMC dates | engine `calendar.py` (NYSE holidays, 13:00 closes), FOMC list committed in `engine/data/events.csv` | 2012 → | time rules, event flags |

No value observable only after the decision minute is an input to that decision (brief §4.3). Bars are used only once closed; the 1-minute bar ending at t is the latest usable at t+1.

## 3. Universe, point in time

1. **Candidate roots** = ThetaData's option-root list (15,817, delisted included), each with its listed expirations (`universe/expirations.jsonl`). A root is *optionable on date d* if it has at least one listed expiration within 400 days after d and its stock (or index) has a bar on d.
2. **Tiers per calendar year Y**, computed from year Y−1 only: rank the optionable roots by median daily dollar volume of the underlying over Y−1 (daily bars). Tier A = top 100; Tier B = ranks 101–500; Tier C = 501–1,000; Index/ETF group = SPY, QQQ, IWM, DIA and the index roots SPXW, RUTW (NDX is not entitled). Symbol changes are followed through the root list; a root that disappears mid-year stays in the tier until its last bar.
3. **Coverage order**: Index/ETF + Tier A for every year first; Tier B second; Tier C as time allows. Every table states which tiers it covers. A ticker with no qualifying setup is listed as "no setup", distinct from "unprofitable" and from "no data".

## 4. Setup families and the baseline configuration (the owner's specification)

Common inputs on every family: RSI 14 and EMA 5/9/20/50/200 on 1m, 5m, 15m, 30m, 1h and daily bars (EMA seeded at the first close, RSI Wilder with a null seed window — the app's conventions); session VWAP on typical price; relative volume = cumulative session volume at the decision minute ÷ the median cumulative volume at the same minute over the prior 20 sessions; market structure = swing highs/lows on the 5-minute bars (a swing = a 3-bar pivot); higher-high/higher-low (bull) or lower-high/lower-low (bear) over the last two swings.

**Baseline signal (all directional families):** 1-minute lead (RSI 14 crosses 55 upward for calls / 45 downward for puts, with close above/below EMA 9), 5-minute confirmation (close above/below EMA 20 and VWAP), 15-minute alignment (EMA 20 above/below EMA 50 and price on the same side of EMA 20), relative volume ≥ 1.0, structure in the signal's direction. Decision at the close of the 1-minute bar; fill at the first NBBO after it.

| Family | Entry trigger on top of the baseline | Expiration category | Hold limit | Exits (baseline) |
|---|---|---|---|---|
| Quick Scalps | baseline only; index products (SPY, QQQ, IWM, SPXW, RUTW) | 0DTE, Weekly | ≤ 60 min, never past 15:50 | invalidation: 5-min close through the signal swing low/high or VWAP loss; premium stop −25 %; target: underlying reaches the next EMA (20/50 on 15m) or premium +25 % (half) / +50 % (rest); time exit |
| Trend Plays | pullback to EMA 9 or 20 on 15m inside a trend (EMA 20 > 50 > 200 on 15m for calls, reversed for puts), then baseline resume | Weekly, Swing | ≤ 5 sessions | invalidation: 15-min close through EMA 50; premium stop −30 %; target: prior swing high/low or EMA 200 on 15m; time exit |
| Breakouts | 5-min close beyond the prior-day high/low or a 20-bar range with relative volume ≥ 1.5 | Weekly, Swing | ≤ 3 sessions | invalidation: 5-min close back inside the range; premium stop −30 %; target: range height projected; time exit |
| Bounces | touch of a qualified level (prior-day high/low, 20-day high/low, VWAP ± 2σ) with displacement z ≤ −2 (calls) / ≥ +2 (puts) and a reversal 5-min bar, then baseline | Weekly, Swing | ≤ 3 sessions | partner ruling: target = level + α·ATR (α = 1.5), invalidation = level − β·ATR (β = 0.5), session-close-through rule |
| Earnings & Events | implied move from the ATM straddle (chain at 15:30 the session before) below the median absolute realized earnings move of the prior 8 reports; direction from the baseline on the day before | Weekly | through the event session | exit at the first session close after the event; premium stop −40 % |
| Cheap Options | Edge = E_P[exit value] − ask − costs > 0 with f_P from regime-matched historical simulation (prior 2 years, same vol bucket and trend state); direction from the baseline | Weekly, Swing, Position | ≤ 10 sessions | invalidation and target as Trend Plays |
| Top Setups / All Setups | the ranking (§9) over the families above | all | — | — |

**Contract selection (baseline):** the expiration in the family's category with the most open interest; among its strikes, delta 0.30–0.60 (computed from the NBBO mid at the decision minute), open interest > 250 (as of the prior settlement), cumulative intraday volume > 100 at the decision minute, bid-ask spread < 12 % of the mid, ask ≥ $0.05; pick the strike with delta nearest 0.45; if none qualifies, the signal is recorded as "no eligible contract".

**Expiration categories** (brief): 0DTE = expires on the decision date (last trading day; AM-settled handled per `3abida/src/data/expiryClass.ts`); Weekly 1–7; Swing 8–30; Position 31–90; Long-Dated 91–364; LEAPS ≥ 365 calendar days to expiration, on actual listed expirations.

**EMA 15:** not an indicator (see `01_implementation_audit.md` §8); "15" refers to the 15-minute timeframe.

## 5. Execution and costs

- Entry at the ask, exit at the bid, from the first NBBO at or after the decision minute's close (1-minute quotes; 1-second quotes for fill audits of selected lanes). Commission and fees $0.70 per contract per side (base). Multiplier 100.
- Orders of 1 contract; an order larger than the displayed ask/bid size is a no-fill at that minute and retries next minute (brief §9); the base run uses 1 lot.
- Unexecutable states: missing bid (0), crossed quote, ask ≤ $0.05 at entry → no trade (recorded); exit on a dead quote waits for the next valid quote, and an expiring contract settles at intrinsic (cash-settled index) or at the 16:00 close with the after-hours exercise caveat stated (ETFs/stocks).
- Adverse scenarios reported beside the base: (a) quote 1 second later; (b) +1 tick on entry and −1 tick on exit; (c) half-spread doubled; (d) 2 lots with displayed-size check. A lane whose base lower bound is positive but (b) is negative is "fragile".
- Measured per-root half-spreads (registry `C1`) are reported against every run so that a lane's edge can be compared with its round-trip cost.

## 6. Chronological walk-forward

1. Folds are calendar years. For test year Y (from the first year with at least two full prior years of option quotes in the family's category, through 2026), the training window is every session before Y minus a 5-session embargo; the test window is Y. Parameters are chosen on the training window only, by the pre-specified objective (§9), from the pre-registered grid (§8); the chosen configuration is written to the registry **before** the test window is simulated.
2. Out-of-sample results are the concatenation of the test years; year-by-year tables are mandatory.
3. 2025-06 → 2026-10 is **not** a clean holdout for anything involving 0DTE index products (prior studies used it); it is labelled "previously analysed" in every table.
4. A forward paper phase (≥ 150 trades and ≥ 3 months for long-option lanes; `GATE-v2`'s 150 sessions / 7 months for carry lanes) precedes any claim of prospective validation.
5. No random shuffling of time-series observations as the primary validation; purged, embargoed folds only.

## 7. Baselines and statistics

- **Random-entry baseline:** for each strategy trade, a random trade on the same ticker and date at a uniformly random minute within ±45 minutes of the signal, same expiration category, same delta band and contract rule, same exit rule set, same costs; 5 draws with seeds 11, 12, 13, 14, 15 from a committed list of ticker-days; reported as the pooled mean and the spread across draws. A timing claim requires strategy − baseline > one round-trip cost with a day-clustered lower bound above zero.
- **Confidence intervals:** 95 % bootstrap, 5,000 draws, seed 7, clustered by trading day; where several trades share a contract and minute, a second clustering by contract-minute is reported.
- **Multiplicity:** for every grid, a recentred day-bootstrap reality check (count of positive lower bounds vs the null distribution) and a Romano–Wolf step-down at 5 %; a configuration is "selected" only if it survives the step-down on the training window.
- **Minimum evidence:** ≥ 150 out-of-sample trades over ≥ 3 months per reported cell; smaller cells are shown with their n and marked underpowered.
- **Reported per cell:** signals, eligible contracts, trades, rejected/unfilled orders, gross and net P&L, net expectancy per trade and per contract, win rate, average and median winners and losers, profit factor, maximum drawdown, worst 5 trades and worst 5 days, mean and 95th-percentile adverse excursion, exposure, Sharpe and Sortino where ≥ 150 trades, turnover and cost share, by ticker group, year, DTE category, setup, timeframe, regime (VIX tercile, trend state, event/non-event), by fold, and under each adverse scenario.

## 8. Pre-registered parameter grid (one factor at a time against the baseline, then the surviving combinations)

| Parameter | Values |
|---|---|
| RSI period | 7, 9, 14, 21 |
| Fast EMA | 3, 5, 8, 9, 13 |
| Intermediate EMA | 20, 21, 34 |
| Slow EMA | 50, 100, 200 |
| Relative volume threshold | none, 1.0, 1.25, 1.5, 2.0 |
| Minimum open interest | 50, 100, 250, 500, 1,000 |
| Minimum intraday volume | 25, 50, 100, 250, 500 |
| Maximum relative spread | 5 %, 8 %, 10 %, 12 %, 15 % |
| Delta band | 0.20–0.40, 0.30–0.50, 0.30–0.60, 0.40–0.60 |
| Confirmation | 1m/5m, 1m/5m/15m, 1m/5m/15m + daily trend |
| Entry trigger | RSI cross, VWAP reclaim/rejection, breakout, retest, EMA cross |
| Exits | invalidation only; premium stop −20/−30/−40 %; ATR-scaled stop; targets 25/50/100 %; partial exits; time exits 30/60/120 min and 1/3/5 sessions |
| Contract selection | delta nearest 0.45 vs highest OI vs tightest spread vs highest expected profit/MAE |

Ablations: each baseline filter removed one at a time (relative volume, structure, 15-minute alignment, OI, volume, spread, delta band) with the effect on trade count and net expectancy recorded. The grid is run on training windows only; the test year sees one configuration per family.

## 9. Ranking objective and its definition

**Primary (the owner's):** expected net profit ÷ expected worst drawdown, per contract, at the decision minute, where expected net profit = mean net P&L of the family's training trades in the same (expiration category, delta band, liquidity class, regime) cell, and expected worst drawdown = mean of those trades' maximum adverse excursion (entry ask − lowest bid before exit) in the same cell; both in dollars per contract over the trade's hold. Cells with fewer than 100 training trades report "unavailable" rather than a number. **Comparators:** rank by expected net profit alone; by the lower 95 % bound; by the partner spec's utility (EV − ES95). The ranking that gives the highest out-of-sample net expectancy for the top-ranked decile, across folds, is recommended; ties go to the simplest.

## 10. Gates (registry `GATE-v2`, brief §11)

A configuration is recommended only when, out of sample across the folds: net expectancy after costs is positive with a day-clustered 95 % lower bound above zero; ≥ 150 trades over ≥ 3 months; evidence beyond the development sample; a credible advantage over the matched random baseline for any timing claim; the base result survives adverse scenario (b) and the worst historical stress days in the sample; and the run reproduces from versioned code and the hashed data manifests. If no configuration passes, the report says so and gives the best defensible result with its gaps.

## 11. Outputs and versioning

`research/compass/results/vN/<family>/<fold>/…` with `config.json`, `trades.parquet`, `summary.json`, `baselines/`, `scenarios/`; every run appends to `registry.jsonl` (id, family, config hash, data manifest hash, windows, result, verdict). Raw provider responses are cached immutably under the data lake with SHA-256 manifests; normalized tables are derived in separate folders.

## Amendments

- **A1 (2026-10-14, after S06).** The underlying-level promotion hurdle (stated in `05_results.md` §S04 as "a day-clustered lower bound of at least +3 bp over 30–60 minutes against the matched random control") is restated with two parts: (a) the *absolute* signed forward return's day-clustered lower bound at 30 or 60 minutes ≥ +3 bp, **and** (b) the paired lower bound against the matched random control > 0. Reason: a counter-trend trigger beats a control matched on its own direction and date merely because the control inherits the day's adverse drift (S06 bounce rows: +7 to +11 bp vs random with an absolute return of zero). A long option pays its cost on the absolute move. The amendment removes a false positive; it cannot create one.
- **A2 (2026-10-14, pre-registered before running).** S07, a daily-resolution screen on the full-universe stock EOD lake (`data_lake/thetadata/stock_eod`, 2023 → 2026, every optionable root) for the Weekly / Swing / Position expiration categories. Universe per calendar year: roots whose prior-calendar-year median daily dollar volume ≥ $50 M (point in time). Triggers at the daily close, both directions: gap continuation (open gap ≥ 2 × 20-day ATR, close beyond the open), 20-day breakout (close through the prior 20-day high/low), 5-day reversal (5-day return ≤ −2σ of the 60-day daily returns, close above the prior close), trend pullback (close > EMA 50 > EMA 200, a touch of EMA 20 within 3 days, close back above EMA 20; mirrored), event shock (relative volume ≥ 3 and |daily return| ≥ 2σ: a proxy for earnings/news days in the absence of a calendar), each raw and with relative volume ≥ 1.5. Horizons 1, 5, 10 and 21 sessions, entered at the next session's open (no look-ahead); benchmark = the same-date mean forward return of the universe in the trigger's direction; CIs clustered by event date. Hurdle, in underlying terms for a single-name swing option (half-spread 3.5–4.1 % of premium measured in `registry.jsonl` C1, premium ≈ 3–5 % of spot for 2–4 week at-the-money): absolute lower bound ≥ +30 bp at 5, 10 or 21 sessions **and** benchmark-adjusted lower bound > 0. Nothing in S07 is an option result; it selects which daily triggers earn an option test with chains.

