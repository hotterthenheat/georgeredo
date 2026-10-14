# Reconciliation of the four prior reports with the Compass research (2026-10-14)

The owner's brief names four documents as the existing evidence: `RESULTS_NBBO.md`, `RESULTS.md`, `COMPASS_RESEARCH_PLAN.md` and `High win rate 0DTE lanes.md`. This note records what each one established, with its exact date window and fill model, what is carried into the Compass experiment registry (`registry.jsonl`), and what the full-history research must do differently. Nothing in the four documents is edited; they keep their original date ranges and conclusions.

Resolved paths:

| Brief's name | Repository path | Generated |
|---|---|---|
| `RESULTS_NBBO.md` | `research/georgefi_full_history/results/RESULTS_NBBO.md` | 2026-10-13 |
| `RESULTS.md` (the 0DTE straddle study) | `research/thetadata/straddle_nbbo/RESULTS.md` | 2026-10-13 |
| `COMPASS_RESEARCH_PLAN.md` | repository root, §1–§11 | 2026-10-13/14 |
| `High win rate 0DTE lanes.md` | `reports/High win rate 0DTE lanes.md` (+ 2026-10-14 update) | 2026-10-14 |

The other `RESULTS.md` files (`research/georgefi_full_history/results/RESULTS.md`, the four `hwr_grid/*/RESULTS.md`, the two `index_tests/*/RESULTS.md`) are the sources the four documents cite; they are preserved and referenced from the registry by path.

## 1. `RESULTS_NBBO.md` — execution quality, kept as its own investigation

**What it is.** GeorgeFi's 1,149 ledger trades and 84 paper trades (2026-01-20 → 2026-10-13) repriced at the ThetaData 1-second NBBO prevailing at the reported second: buy at the ask, sell at the bid, $0.70 per contract per side; 99 % coverage.

**What it established.** (a) The reported fills are systematically better than the market offered: 58 % of Epoch 1 rows were filled better than the NBBO on at least one side, and 27 % of the 382 same-contract-same-minute repeats were priced below the minute's lowest bid. (b) Executable P&L: Epoch 1 $39,297 → $12,039 (+$22/trade, day-clustered CI [−11, 66]); Epoch 2 −$3,294 → −$24,988 (−$42/trade [−79, −10]); paper −$3,632 → −$6,209. (c) Measured half-spreads at the fill time: SPY/QQQ 0.5 % of mid, SPXW 0.9 %, IWM 0.7–1.0 %, RUTW 4.5 %, NDXP 7.5 %, single names 3.5–4.1 %.

**Carried into Compass.** The methodology (fill classification against the NBBO at the decision second, the 1-second-later variant, day- and trade-clustered bootstrap) is the template for every Compass fill audit; the per-root half-spread table is the engine's default cost model and the adverse scenarios are built from its upper quartiles. The P&L numbers are **not** evidence about any Compass strategy (registry `RULE-separation`, `G1`, `G2`, `C1`).

**Owner's decision 2026-10-14.** GeorgeFi reverse-engineering stops. The report, its raw exports (`research/georgefi_full_history/raw/`, SHA-256 indexed) and its code are preserved unchanged.

## 2. `RESULTS.md` — the 0DTE short-straddle study (June 2025 → October 2026)

**What it is.** 5,084 fixed-time and 1,017 random-time ATM 0DTE straddles on SPY/QQQ/IWM over 339 sessions 2025-06-02 → 2026-10-09, sold at the bid and bought back at the ask at 15:55 from ThetaData 1-minute NBBO, $0.70 × 4 sides, day-clustered 95 % CIs.

**What it established.** The pre-registered 13:00 SPY+QQQ lane earns +$8.60 per straddle [−6.07, +22.45] (n = 678), +$5.92 ex FOMC/CPI/NFP, +$4.55 with a 2× stop; IWM −$9.50 [−18.69, −0.44]; every other entry time is negative; the modelled cost rule under-charged the exit by about $5 per straddle because buying back near-worthless legs costs 3.3 % of the credit (median). Random-time baseline: the lane beats it by $13.10 [−2.42, +29.14] against a $12.93 round trip. **T-A FAIL** (registry `H9`).

**Brief §3.2 asks** to reproduce this baseline and run the experiment over all historical periods where contract data exist, without carrying the 13:00 entry, the expiration or the stop rules into the final configuration. Status: the full-period version was already run in round 2 and on complete chains (SPY/QQQ daily expiries exist only from 2022-11-11, SPXW from 2022-05-13, IWM from 2024-04-19 — the 0DTE product did not exist earlier, so "all available history" for same-day expiries is 2022 →). Results are in `High win rate 0DTE lanes.md` and plan §9–§11 (registry `H13`, `H15`, `H16`). The reproduction of the 2025-06 → 2026-10 baseline to the cent (669/678 and 337/339 rows) is recorded in that report. **Short premium is outside Compass's long-option recommendation universe unless the owner places it in scope** (brief §3.4); the registry keeps `H15` as a labelled carry candidate for forward paper trading only.

## 3. `COMPASS_RESEARCH_PLAN.md` — the hypothesis register and the gates

**Carried over verbatim into `registry.jsonl`:** H1–H15 with their verdicts and deciding numbers; the original gate (`GATE-v1`) and the six-gate revision from the developer review (`GATE-v2`, in force); the separation rule; the adopted execution rule `H14`; the default carry-lane filter (`H17`); the data limitations (`DATA-1..3`).

**Closed and not to be reopened without a new, specific hypothesis:** H1 (level-sweep 0DTE entries), H2 (flow-following entries), H3 (per-strike bursts), H4 (gamma regime as direction filter), H6 (wall/magnet fades), H7 (exit engineering as alpha), H8 (session plays in options), H9/H11/H13 (short straddle variants), H10 (gamma-conditioned momentum), H12 (GeorgeFi inputs; closed by owner).

**Where the brief justifies a controlled retest.** Every closed hypothesis above was tested on short windows (UW option history from 2023-11, UW contract bars from 2025-04, the 0DTE chains from 2022-05/11). The brief's §2 and §5 require the full history to be used where the inputs exist. That reopens **only** the hypotheses whose inputs reach further back, and only as pre-registered retests with the same baselines:

| Registry id | Input needed | Earliest availability | Retest scope on the full history |
|---|---|---|---|
| H8 (session effects) and the brief's session-of-day analysis | underlying 1-minute bars | ThetaData stock 1-minute from 2012-06 (SPY/IWM/GME quotes from 2017-01; AAPL/MSFT from 2012-06); options NBBO 1-minute from 2012–2014 | Underlying effects 2012 →; option expressions wherever option quotes exist |
| H10 (last-30-minute momentum, unconditional part) | SPY 1-minute bars + SPX index | SPX 1-minute from 2017-01 | 2017 → in shares; the gamma-conditioned part cannot extend (UW gex from 2024-05) |
| H7 exit rules as drawdown shaping (not alpha) | option NBBO | 2012–2014 → | Re-measured inside the Compass engine on long-option trades across all years |
| H5 gamma as a volatility gauge | UW gex (2024-05 →) or our own exposure from ThetaData OI + Greeks (2012 →) | depends on the computed-exposure path | Computed-exposure version is a new hypothesis (`H18`, to be registered when the inputs are built) |

H2/H3/H4/H6 depend on Unusual Whales flow and positioning fields with a 2023-11 or 2025-04 floor; the full history cannot extend them, so they stay closed, and any new flow feature is evaluated on its actual window against a matched baseline over the same dates (brief §4.4).

**The gates.** `GATE-v2` maps onto the brief's §11 promotion criteria one-for-one (positive net expectancy under defensible execution; positive lower 95 % bound out of sample; adequate count and chronological coverage; evidence beyond the development sample; a credible advantage over the matched baseline for timing claims; robustness to adverse execution and stress; reproducible from versioned code and documented data). The brief adds the 150-trade / 3-month starting gate for out-of-sample evaluation (§11) and the forward paper phase before calling anything prospectively validated (§10); both are already in `GATE-v2`.

## 4. `High win rate 0DTE lanes.md` — why win rate is not an objective

**What it established** (registry `H16`, `H17`, `H15`): across 1,890 ETF and 2,736 SPXW configurations with TRAIN to 2024-12-31 and TEST 2025-01 → 2026-10, the median configuration wins 71–73 % and loses money; take-profits, wider strikes and wings buy win rate with expectancy; stops shape drawdown without raising the mean out of sample; the one surviving lane is a carry trade whose timing adds nothing, concentrated in 2025, needing ≈ $400k per lot to survive a 15 % shock.

**Brief §3.4 asks** that the ±2 % strike-band restriction not survive, that far-OTM strikes and extreme-move days be included, and that short premium stay out of the main recommendation universe. Status: the band was removed on 2026-10-14 (full chains, `data_full`, registry `DATA-1`), the report's update section carries the complete-data numbers, and the registry files H15 as a carry candidate separate from Compass's long-option families.

**Carried into Compass.** (1) The ranking objective must be after-cost expectancy against drawdown; win rate is reported, never optimised. (2) Exit rules are evaluated as risk shaping. (3) Day filters: FOMC and month-end are the only skips with evidence, and that evidence is for short premium; for long-option lanes the event-day treatment is an open test. (4) Multiplicity accounting (recentred day bootstrap, Romano–Wolf) is mandatory for every grid.

## 5. What the full-history research adds that the four reports could not

1. **Instruments and families.** The four reports test short premium on four index products and GeorgeFi's long-option record on about 40 roots. The brief's families (scalps, trend, breakouts, bounces, earnings/events, cheap options) are long-option strategies on the optionable universe; none has been tested in this repository. Everything in `research/compass/` from here on is new evidence.
2. **History.** Underlying 1-minute bars from 2012-06, option NBBO from 2012–2014, option EOD/OI from 2012-06, index 1-minute from 2017-01 (boundaries in `02_coverage_matrix.md`), against the reports' 2022–2026 windows.
3. **Point-in-time universe.** Reconstructed from ThetaData's option-root list (15,817 roots including delisted) and each root's listed expirations, never from today's tickers.
4. **Walk-forward across years**, not a single TRAIN/TEST split, with year-by-year and regime tables.

Everything above is recorded so that a later result contradicting an earlier conclusion is checked against the earlier window, instruments, fill model and method before either is revised.
