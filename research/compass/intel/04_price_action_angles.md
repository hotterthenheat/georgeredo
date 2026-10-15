# Market-intelligence brief — 4. Price action from every angle: the evidence, what was tested here, what is open (2026-10-15)

**Purpose.** The owner asked for price action "from every single possible angle" so that options can be traded better. This file lists every angle on the underlying's behaviour (stocks, ETFs, SPX; one-minute and daily). For each angle it gives:
- what an options trader would use it for;
- what the published evidence says;
- what this repository has already tested, with its numbers;
- whether our data can test it;
- how much it matters for options.

It then orders the open angles with test designs, and lists the descriptive statistics a desk should see without spending any hypothesis budget.

**The rule this file applies.** An angle helps an options trader only if it predicts something the option has not already priced, by more than the bid/ask spread of the structure that expresses it.
- **Size:** a forecast of the move must beat the implied move (the straddle).
- **Path:** a realized probability (finish beyond a strike, touch a level) must differ from the probability the chain prices.
- **Direction:** the expected move must exceed the spread plus the time decay over the hold. The repository's hurdle for a 0.45-delta same-day SPY contract is an absolute day-clustered lower bound of at least +3 bp at 30 or 60 minutes (`../05_results.md` S04, amendment A1); for a single-name swing option it is +30 bp (A2).

Nothing here is called an edge unless it survived costs and out-of-sample evidence. On that standard, one study in this repository has passed a pre-registered gate (four cells), and only as a carry lane: S17 index put-writing (not alpha; beta about 0.5).

**Measured costs that every angle must clear** (registry `C1`, `02_volatility_pricing.md`):
- median half-spread at the fill: SPY/QQQ 0.5 % of mid, IWM 0.7–1.0 %, SPXW 0.9 %, single names 3.5–4.1 %;
- SPY/QQQ same-day ATM straddle round trip: $12.93 measured (against $8.30 modelled);
- single-name monthly ATM straddle: median spread 13 % of its mid.

**How to read the evidence.**
- **(paper)**: a number from the paper itself (its abstract or text).
- **[sec]**: a paper's number taken from a secondary summary I could reach; not checked against the full text.
- **[repo]**: a number already quoted in this repository's notes (`../../../reports/`, `../../../research_notes/`).
- Sentences without these marks are my summary of the paper's finding.
- The full references are in §6.

**Evidence labels.** OBSERVED (bars, quotes, prints), CALCULATED (statistics computed from observed data), MODELED (forecasts, risk-neutral densities, theoretical benchmarks).

**What was read.**
- `../05_results.md` (S01–S17, V1, V2) and `../04_protocol.md` (amendments A1–A10).
- `../registry.jsonl` (G1–G3, C1, H1–H17, L-*, DATA-1..3).
- `../lifecycle/` 01, 04, 06, 07, 10, 11, 12.
- `01_audit_and_gaps.md`, `02_volatility_pricing.md`, `03_compass_plan.md`, `05_expirations_and_corrections.md` (written today in parallel).
- `../../../reports/Finding a 0DTE options edge.md` and `../../../reports/High win rate 0DTE lanes.md`.
- `../../../research/short_vol_session/summary.md` and `../../../research_notes/High win rate 0DTE lanes/empirical_vol_filters_spx.md`.
- `../10_external_research.md` and the L6 note in `../../../research_notes/Retail options edge sweep/`.

No market-data API was called for this file.

**Abbreviations used in the "data" column** (from `../lifecycle/01_data_inventory.md`):

| Code | Dataset | Window |
|---|---|---|
| M1-ETF | SPY, QQQ, IWM one-minute bars | 2017-06-01 → 2026-10-09 (the vendor's 2012–2016 bars are empty) |
| M1-A | 40 Tier A single names and ETFs, one-minute bars | 2017-06-01 → 2026-10-09 (S06-TierA read 34 of them) |
| M1-IDX | SPX and VIX one-minute index prints | 2017-06-01 → 2026-10-09; no intrabar range, so high/low = max/min of the prints. RUT from 2018-12 |
| D-ALL | Stock end-of-day bars, every symbol | 2023 → 2026; earlier years arriving |
| Q0 | Same-day (0DTE) option one-minute NBBO, every strike | SPY and QQQ 2022-11-11 →; SPXW 2022-05-13 →; IWM 2024-04-19 → 2026-10-09 |
| QW | Weekly options (the nearest Friday) one-minute NBBO | a stratified sample: SPY 468, QQQ 294, IWM 294 sessions, 2017 → 2026; not consecutive |
| EOD-ETF | Option end-of-day (closing NBBO), every expiration, SPY/QQQ/IWM | 2012-06 → 2026-10 (Tier D) |
| UW-C | Unusual Whales closing chains, any optionable name | 2023-11 → (a rolling 730 trading days) |
| UW-T | Unusual Whales full option tape | available from the vendor, not pulled (about 700 GB) |
| UW-G | Unusual Whales daily dealer greek exposure | 2025-10-15 → 2026-10-13 |
| UW-E | Unusual Whales earnings calendar | 1996 → |
| EV | FOMC, CPI and NFP dates | 2017 → (`../../thetadata/vol_filters/events.csv`) |

**Not on disk:** futures, FX, rates before 2024, order books, VIX9D/VIX3M, NDX, stock one-minute bars before 2017.

**Pulls must wait.** Any ThetaData pull runs through the owner's Theta Terminal, one login per key (registry DATA-3), outside market hours, and only once the process that holds the login now has released it.

---

## 1. Short reading of the matrix

There are **62 angles** in §2, grouped as the owner listed them. How each stands here:

| Status | Angles | What it found |
|---|---|---|
| Tested | 28 | 24 came out null, rejected, or the wrong sign after costs: setups, triggers, momentum, reversal, gaps, levels, VWAP, flow, the gamma direction filter, the VIX filter, single-name volatility pricing (V1) and earnings straddles (V2). Of the other four: the index variance risk premium passed a pre-registered gate as a carry lane (S5: S17; the 14:05 SPXW strangle, H15, is an open carry lane awaiting its forward test); the settlement path gave execution rules (P7: H14 adopted); the pre-earnings run-up is a candidate at the underlying level only (D10: S13); and the bull-market drift is context, not a rule (R2). |
| Partly | 17 | Mostly **size** angles: the afternoon range is forecastable (OOS R² 0.44), but no forecast was ever compared with the live implied move except in a crude form (A11, S15). Also **calendar size** effects: FOMC afternoons move 2.08× as far, month-end 1.33×; whether the 0DTE straddle prices these is unmeasured. |
| Descriptive only | 1 | Where the day's high and low form. |
| Not tested | 16 | Two **path** angles of high priority (touch probabilities; the overnight variance price), two size inputs (range-based estimators, semivariance), and low-value direction, calendar, level and lead–lag effects. |

**What follows from it.**
- The published record agrees with the repository. Directional price-action rules either decayed after publication (pre-FOMC drift, the weekend effect, technical rules after 1987) or do not survive costs.
- Volatility is forecastable from its own past, but options already price most of that. The open questions are whether **intraday** information, **event and time-of-day structure**, and **path probabilities** are priced as well as the level of volatility is.

---

## 2. The matrix

Notes on the columns:
- "Tested here?" starts with **Tested**, **Partly**, **Descriptive only** or **Not tested**.
- Intervals are 95 %, day-clustered unless stated.
- "dev+val" = development + validation. "VF" = the SPX volatility-filter study (`../../thetadata/vol_filters/`, fit 2017-06 → 2022-12, test 2023-01 → 2026-10). "PB" = `../lifecycle/12_per_ticker_playbook.md`. "SVS" = `../../short_vol_session/`, SPY/QQQ/IWM 2025-06-02 → 2026-10-09.

### 2.1 Size / volatility

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| S1 | Volatility clustering; daily HAR-RV forecast of realized vol | Price a straddle or strangle against a forecast; strike distance; size | HAR-RV is a simple cascade model that reproduces long memory and forecasts well [Corsi09]; realized-vol models beat daily GARCH [ABDL03]; implied vol still carries information beyond past realized vol [CP98], [BCN11] | **Partly** — A11 VOLC, a long straddle when 10:00 0DTE IV ≤ 0.8 × a HAR forecast, SPY/QQQ/IWM/SPXW 2022-05 → 2025-09: −32.8 [−102.3, +30.7], walk-forward −35.8 [−42.7, −27.7]: failed. A12 VOLR (rich → put sales) −17.5 [−38.0, 0.0]: failed. S15 (implied vs trailing 20-day realized, SPY+QQQ 2022-11 → 2026-10): "rich" days −$41.10 [−86.33, −2.39], the wrong sign | Yes: M1-ETF, M1-A, M1-IDX; Q0; EOD-ETF | **High** — size is the forecastable part of price action; tested here only with a daily HAR and a trailing-realized rule, never with intraday information against the live implied move (§4 O1) |
| S2 | Intraday information (morning realized variance, first-hour range, overnight gap, VIX) → rest-of-day size | 0DTE strike distance and entry time; skip or size | Intraday volatility = daily × time-of-day × intraday components; pooled forecasts beat per-stock ones [ES12] | **Partly** — VF: afternoon range OOS R² 0.442 [0.354, 0.521] against a constant and 0.336 [0.255, 0.414] against the trailing 20-day mean; afternoon absolute move only 0.109 [0.051, 0.177]. The elasticity of the afternoon to the morning range fell from 0.823 [0.741, 0.890] (2017–22) to 0.539 [0.414, 0.640] (2023–26). No option-implied data was in that cache | Yes: M1-IDX, M1-ETF; Q0 for the implied side | **High** — the forecast exists; whether it beats the 13:00 implied move does not (O1) |
| S3 | Range-based estimators (Parkinson, Garman–Klass, Rogers–Satchell, Yang–Zhang) | Better realized-vol inputs from daily OHLC where minute bars are missing (single names, pre-2017) | Large efficiency gains over close-to-close [Park80], [GK80]; drift-independent [RS91]; Yang–Zhang adds opening jumps, is drift-independent, and has the minimum variance in its class (paper) [YZ00] | **Not tested** — the repo uses sums of one-minute squared returns, and V1 used close-to-close RV21 | Yes: D-ALL (2023 →), M1-A | Medium — an input, not a signal; it sharpens single-name IV/RV labels |
| S4 | Signed semivariance and the leverage asymmetry | Forecasts after down days; put-skew calibration | Variance from past negative returns predicts future vol more than variance from positive returns; negative jumps raise later vol, positive lower it [PS15]; a 2025 paper attributes part of this to drift bias in the estimators [sec] | **Not tested** | Yes: M1-ETF, M1-A, M1-IDX | Medium — add as a predictor inside O1, not as a separate test |
| S5 | Index variance risk premium (implied above realized) | Carry: sell index puts or straddles | The variance risk premium on indexes is negative and large [CW09]; delta-hedged index options lose on average [BK03]; it predicts equity returns [BTZ09] | **Tested** — S17, SPY/QQQ monthly 2012-06 → 2026-10: QQQ ATM put +$199 per contract a month [+58, +326], SPY ATM put +$200 [+17, +347]. It passed A7 as a carry lane, but it is not alpha (beta ≈ 0.5) and not robust to a 10-cell Bonferroni; March 2020 cost 16–21 months. 0DTE: S15 unconditional −$15.46 [−32.68, +0.29]; H15 14:05 SPXW strangle TEST +$151.17 [+42.15, +251.73], open, awaiting its forward test | Yes: EOD-ETF, Q0 | **High** — the one premium that survived costs here; conditioning it on a size forecast is open (O6) |
| S6 | Single-name variance premium; IV/RV, term-slope and skew sorts | Which names' options are rich | Long high (HV − IV) / short low earns significantly in the cross-section [GS09]; later work questions it after costs [sec] | **Tested, rejected** — V1 (44,447 name-cycles, 2023-11 → 2026-09): shorting every ATM straddle −13.2 % [−22.4, −5.0] dev+val, −23.6 % hold-out. The richest IV/RV quintile realized 2.34 vol points under implied, but quintile 5 minus shorting everything was +2.7 % [−2.5, +8.6] dev+val and −0.03 % hold-out. Term slope and skew: no edge | UW-C | Low — the ranking is real; the 13 % spread takes it |
| S7 | Trading a volatility forecast against implied (the historical record) | Whether forecasts ever paid after costs | GARCH-based S&P 500 straddle trading in 1986–91 earned more than a $0.25-per-straddle cost (abstract) [NEK94]; S&P 100 implied vol is predictable, but a daily trading strategy earned nothing after costs [HW92] | **Partly** — A11 and S15, as in S1 | Yes | Part of S1 — a mixed record, mostly pre-2000 |
| S8 | The earnings move against its implied move | Earnings straddles and iron flies | Earnings-announcement risk is priced in options [DJKS19]; high expected-announcement-volatility straddles underperform low by 11 % [repo: `../10_external_research.md` E2] | **Tested, rejected** — V2 (11,802 reports, 2023-11 → 2026-09): the median report moved 0.59 of the implied move. Selling across the report −26.1 % [−28.5, −23.3] dev+val, −34.2 % hold-out; buying into it −20.9 % and −29.3 %. At the mid, sellers earned +6.9 % on same-day settlements; at the bid, −4.5 % | UW-C, UW-E | Low — rejected; only the top-liquidity decile (S18, queued) is a cost question left |
| S9 | Scheduled macro events (FOMC, CPI, NFP) and the size of the move | Event-day straddles; skip or size short premium | Announcement days earned 11.4 bp against 1.1 bp, 1958–2009 (paper; returns, not variance) [SW13]; 0DTE implied event vol rises into the 14:00 statement and collapses after it [repo: `../../../reports/High win rate 0DTE lanes.md`] | **Partly** — H17/VF (SPX 2017–2026): FOMC afternoons move 2.08× [1.56, 2.68] as far as event-free ones; CPI/NFP 0.94–0.96×. A13 EVF (Fed-day afternoon straddles): inconclusive, 85 trades on 27 days, intervals ± $400. D_FOMC daily straddles through the statement: no difference (Swing +3 [−107, +118]) | Yes: Q0 (about 30–35 FOMC days), M1-IDX, EV | Medium — the 2.08× is measured; whether the 13:00 FOMC straddle prices it is not (O4); n is small |
| S10 | Month-end, holiday-adjacent and weekday variance | Skip or size short premium | No peer-reviewed variance study reviewed here (turn-of-month evidence is about returns, C3) | **Partly** — VF: month-end afternoons 1.33× [1.06, 1.65]; holiday-adjacent 0.82× [0.66, 1.02]; Monday 0.89× [0.74, 1.05]; Wednesdays without FOMC 1.07× [0.91, 1.29]. Skipping FOMC + month-end was positive in 9 of 10 years (found post hoc) | Yes: M1-IDX, Q0 | Medium — month-end is inside O4 |
| S11 | Volatility-level regime (VIX level or percentile; volatility-managed exposure) | Skip, size, choose a structure | Scaling exposure by inverse past variance raised Sharpe ratios [MM17]; in real time, volatility-managed versions of many equity strategies do not systematically beat the unmanaged ones [CODWY20] | **Tested** — lifecycle: VIX ≥ 20 was worse for every long structure (Steady puts −44.65 [−68.4, −24.0]). VF: skipping when the 13:00 VIX is above its 60-day 80th percentile lowered the mean by −0.020 [−0.035, −0.005]; the credit already prices it | Yes | Low as a filter (it is priced); keep it for sizing in index terms |
| S12 | Dealer gamma and the size of moves | Expect a wider or narrower day; strike distance; long vs short premium | One SD of gamma imbalance lowers the absolute daily index return by more than 20 bp (about 20 % of an SD) and intraday autocorrelation by 1.5–2 pp [BB21, repo]. Option market makers' rebalancing affects volatility and the odds of large moves [NPPW21]. 0DTE gamma does not carry volatility forward [DEV]. Vendor GEX vs next-day RV: −0.36 raw, −0.03 (p 0.18) after VIX and ATM IV [FlashAlpha, practitioner, repo] | **Partly** — H5 (60 SPY sessions): net OI gamma IC −0.211 [−0.300, −0.125] against the absolute 30-minute move, partial −0.171; a tool, not a lane. H-FLO (2025-10 → 2026-10): long premium lost less after negative gamma, but within each root only +1.7 pp [−0.5, +3.8]. VF: prior-day gamma sign IC +0.101 [+0.002, +0.175] with the afternoon absolute move | Partly: UW-G (one year); a house naive-sign estimate needs an open-interest pull (throttled) | Medium — it must add to the implied move, not to realized alone (O5) |
| S13 | Jumps and tail frequency | Short-premium sizing; wing choice | Nonparametric jump detection and jump dynamics [LeeM08] | **Partly** — descriptive tails only: V1 (13 % of single-name straddles lost more than the whole premium), S17 (March 2020), H13 (2025-04-09 −$33,667 a lot) | Yes: M1-* | Medium — an atlas item (A12) and a sizing input |
| S14 | Volume → volatility | Forecast size from early relative volume | The absolute price change and volume are positively related [Karpoff87] | **Partly** — relative volume was tested only as a direction filter (S01, S02, S04: nothing); VF did not include volume | Yes: M1-* volume | Medium — a predictor inside O1 |

### 2.2 Path / timing

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| P1 | The intraday volatility U-shape against the 0DTE decay schedule | When in the day to sell or buy same-day premium | U-shaped intraday patterns in activity and returns [WMO85], [Harris86]; intraday periodicity must be modelled to read volatility dynamics [AB97] | **Partly** — SVS T1: a short ATM straddle has a positive mid-price edge at every entry time, best at 13:00 (+$16.69 [5.36, 27.71] at mid, +$8.36 [−3.15, 19.52] after the spread). H15: a random minute 10:00–14:30 earned as much as 14:05 (+$165 pooled vs +$162) | Yes: Q0, M1-* | Medium — timing added nothing measured so far; the implied-vs-realized curve by time is an atlas item (A10) |
| P2 | Time of day of the day's high and low | After the morning, how likely a new extreme is; strike placement | For a driftless random walk the time of the maximum follows the arcsine law, so extremes near the open and close are most likely [Aldous]. S&P 500 futures high/low times are consistent with a random walk with time-varying trading speed [MLL00]. FTSE 100 futures extremes cluster at the open and close [Acar] | **Descriptive only** — PB §1 (2022-11 → 2025-09): SPY sets its high in 09:30–10:00 23 % of days, its low 27 %; the first 30 minutes hold the high or the low 51 % (QQQ 62 %, IWM 67 %); the high is set after 15:00 30 %, the low 20 % | Yes: M1-ETF, M1-A, M1-IDX | Medium — informs strikes; compare it with the arcsine null in clock time and in variance time (A4) |
| P3 | Touch probabilities of ±k levels against the reflection principle | Stops; short-strike distance; "close if touched" rules | For driftless Brownian motion, P(touch) = 2 × P(finish beyond) [Shreve]; practitioners use "touch ≈ 2 × delta" [repo]. No peer-reviewed intraday calibration was found in this pass | **Not tested** as such (PB §5: SPY cash-secured put "take 50 % or close if the strike is touched" +0.4 / +0.3 a contract) | Yes: M1-* (against a trailing σ); Q0 (against the implied σ) | **High** — a direct input to short-premium strike and stop choice, cheap to measure (A5, O2) |
| P4 | Calibration of the 0DTE chain's probabilities across strikes; implied-move breach rates | Which strikes are rich; strangle, condor or vertical choice | 193 SPY Wednesdays: the 10:00 straddle over-forecast the close-to-close move by about 13 % (median realized/implied 0.589 vs 0.674 if fair), 1σ breaches 26 % [FlashAlpha, practitioner, repo]. Vilkov's SPXW panel 2016–2026, after his cost-scaling correction: no structure keeps a positive net Sharpe (straddle/strangle −0.97, condor/fly −2.67) [repo] | **Partly** — on P&L, not calibration. ETF grid, 13:00, SPY+QQQ: strangle at 1 expected move TRAIN +$2.48 [−6.73, +9.93], TEST +$11.50 [+1.75, +20.05]; iron condors never had a positive lower bound. H9 13:00 straddle +$8.60 [−6.07, 22.45]. S15 as in S5 | Yes: Q0 (every strike) | **High** — the cleanest "beat the price" measure, partly mapped by the grids (O2) |
| P5 | Trend day vs range day (efficiency, variance ratio, autocorrelation) | Long or short gamma for the day; hedging frequency | The variance-ratio test [LM88]; gamma lowers intraday autocorrelation by 1.5–2 pp [BB21, repo]; [GHLZ18] | **Partly** — the 1-minute reversal rate is 50.2–50.8 % in every gamma regime [repo]. VF: the morning's efficiency has an IC of −0.002 [−0.043, +0.039] with the afternoon absolute move. PB: days close 53–61 % of the way up their range | Yes: M1-* | Medium-low — no ex-ante predictor found; atlas (A8) |
| P6 | The option's own path after entry (hindsight high and low) and exit rules | Targets, stops, trails | Stop rules raise expected return only when returns are serially correlated [KL14] | **Tested** — PB §2: 47–55 % of same-day options reach +50 % at some minute, but 60–75 % of Steady options and 85–92 % of Big Payoff options also reach −50 %. Of 81 exit rules per ticker and structure, none has a lower bound above zero. H7: 0 of 576 exit configurations positive | — | Low (closed) — exits shape risk, not expectancy |
| P7 | The last minutes and settlement | Hold to expiry or close at 15:50; after-hours exercise | — (mechanics) | **Tested** — lifecycle B10: holding to expiry beat selling at 15:50 by $10–34 a trade. H16: on SPY/QQQ most of the hold-to-expiry gain is after-hours exercise risk (+$30.60 against the 16:00 close, +$6.30 against the 17:15 quote). H14: leave legs quoted at $0.05 or less to expire | — | Medium — an execution rule, already adopted |

### 2.3 Levels

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| L1 | Prior-day high/low and 20-day extremes (breakouts, retests) | Directional entries; short strikes beyond levels | Trading-range breaks earned money on the DJIA 1897–1986 before costs [BLL92]; the best of those rules earned 8.63 % a year, insignificantly, in 1987–1996 before costs [STW99, sec] | **Tested** — S06 (SPY/QQQ/IWM 2017–2026): 5-minute breakouts fire after +25 to +38 bp; 30 minutes later the absolute move is ≈ 0, and they trail random minutes by −8.7 / −10.8 / −12.5 bp at 60 minutes. S07 (1,100–1,500 names, 2024–26): a 20-day breakout is followed by −81 bp [−133, −33] at 21 sessions. Lifecycle breakouts ≈ random | — | Low for direction (closed); how often levels hold for strike placement is O7 |
| L2 | Opening-range breakout | 0DTE direction | A 5-minute ORB on QQQ, 2016–2023, reported 33 % annual alpha net of commissions, with no spread or slippage; an independent replication found zero net [ZA23, sec]. Crude-oil futures ORB [HLL13] (results not read) | **Tested** — report: a 1-minute close beyond the 15-minute range happens on 1,016 of 1,017 ticker-days; it continues 50–54 % of the time at +30 and +60 minutes; −0.5 bp [−7.0, +5.8] to the close; back inside within 30 minutes 78 % of the time. ORB option −$5.15 [−7.11, −3.24] | Yes: M1-* 2017 → | Low |
| L3 | VWAP and VWAP bands | Entries, stops | No peer-reviewed price-action evidence found in this pass; VWAP is an execution benchmark | **Tested** — S06 VWAP reclaim at 30 minutes: +0.0 / +0.2 / +0.1 bp. Lifecycle VWR debit spread +1.5 [+0.2, +2.9] against a later minute: one of 3 positive intervals in 156 tests. S06 bounces at VWAP ± 2σ: absolute ≈ 0 | — | Low |
| L4 | Round numbers | Short strikes and stops at or beyond round numbers | FX take-profit orders cluster at round numbers (reversals there) and stop-losses just beyond them (acceleration through) [Osler03]. Published FX support/resistance levels from six firms predicted intraday trend interruptions, 1996–98, for at least five business days (paper) [Osler00]. Buy/sell imbalances one cent either side of whole dollars in more than 100 million US stock trades [BHJ12]. Price barriers in the DJIA [DK93] | **Not tested** | Yes: M1-* (SPY whole and $5 levels, SPX 25/50/100 points) | Medium-low — a path question: do they hold more than matched random levels? (O7) |
| L5 | Strikes as levels: walls, gamma magnet, index pinning | Pin plays; short strikes at walls | S&P 500 futures are pinned to the ATM strike when serial options expire; at least $115M of notional shifted per expiration (working paper) [GJ12, sec]. SPY 2016–2025: no pinning, and about 16 % wider ranges on high ATM-open-interest days [Harbourfront summary of a working paper, repo] | **Tested** — H6: walls and the magnet are indistinguishable from distance-matched random levels. Days closing within 0.25 % of a touched magnet: 34.5 % vs 34.6 % for random levels; the put wall anti-pins (−6.3 pp [−12.2, −1.2]). H1: 0 of 144 level-sweep variants | — | Low (index) |
| L6 | Single-name monthly-expiration pinning at high open-interest strikes | Short ATM premium into expiry on optionable names | Closes of optionable stocks cluster at strikes on expiration dates; returns shifted by at least 16.5 bp per expiration (paper) [NPP05] | **Not tested** | Partly: UW-C (open interest) 2023-11 → with M1-A | Low-medium — 16.5 bp is far below single-name option spreads (about 11 % median near-ATM half-spread at the close, `../10_external_research.md` X4); descriptive (A11) |
| L7 | Chart patterns; ICT sweeps, structure shifts, fair-value gaps; bounces | Entries | Several patterns carry incremental information, 1962–1996 [LMW00]; on the DJIA 1897–2011, after false-discovery control, low costs remove the value even in sample [BS12] | **Tested** — lifecycle A5: sweeps, structure shifts and fair-value gaps lose in every long structure and are within noise of clean controls. S06 bounces: absolute ≈ 0 | — | Low |
| L8 | Nearness to the 52-week high | Swing direction | Nearness to the 52-week high predicts returns [GH04] | **Not tested** | Yes: D-ALL | Low — direction, months |

### 2.4 Gaps / overnight

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| G1 | Overnight vs intraday returns (direction) | Hold calls overnight or intraday | QQQQ 1999–2006: close-to-open risk premium about +23.7 %, open-to-close about −23.3 % (abstract) [KC11]; the same split in stocks, indexes, futures and ETFs, 1993–2006 [CCG08]; momentum earns overnight, other strategies intraday [LPS19]; E-mini 2004–2018: four hours around the European open carry the whole average return, Sharpe 1.6 (abstract) [BM23] | **Not tested** as such (S16a tested gap signals) | Yes: M1-ETF, M1-A, D-ALL | Low — direction, shares-sized |
| G2 | Overnight share of variance, and the night/day option return | Sell or buy premium overnight on next-day expirations | Open-to-close variance is more than 6× the weekend's close-to-open variance; per hour it is 13–100× (paper) [FR86]. Delta-hedged S&P 500 index options lose about −0.7 % a day: roughly −1 % close-to-open and +0.3 % open-to-close (abstract) [MN20, repo] | **Not tested** | Yes, with one gap: D's closing quote of the next-day expiration (EOD-ETF closing NBBO, or a 15:50 pull); D+1 morning quotes are in Q0 2022-11 → | **High** — a size-and-time mispricing with peer-reviewed support, never measured here on daily expirations (O3) |
| G3 | Weekend and holiday variance in weeklies | Open multi-session longs on Monday rather than Friday | Delta-hedged puts −0.82 % per nontrading period vs +0.03 % per trading day (t −11.93), 1996–2014 [JS18, repo] | **Tested** (small) — L6: 32 SPY weekend pairs 2017–2022, ATM straddle −1.17 % [−4.34, +2.40] over the weekend vs +0.40 % [−2.22, +3.30] on weekday nights. Friday weeklies price the weekend at about 0.2–0.9 trading-day equivalents: mostly priced | Partly: QW is not consecutive | Low — a free convention, not a lane |
| G4 | Gap continuation vs gap fill | Gap-fill fades, gap-and-go | DJI, S&P 500 and Nasdaq 1928–2018: gap days tend to move in the gap's direction, and gaps do not tend to fill (abstract) [PSGW20] | **Tested** — S16a (SPY/QQQ/IWM 2017–2026, 108 cells): continuation and fade ≈ 0. Report T5: gaps above 0.3 % filled by the close 38 % of the time, above 1 % 20 %, at or below 0.3 % 83 %. Gap-fill option at 09:35 −$3.78 [−7.12, −0.29]. S07 gap continuation: not significant | — | Low (closed) |
| G5 | Gap size → the day's range | Size of the opening straddle | — | **Tested** — VF: the absolute gap has an IC of +0.332 with the afternoon range, but its OOS R² against the trailing 20-day mean is −0.180 [−0.286, −0.073] | — | Low on its own — keep it as a predictor inside O1 |
| G6 | Prior-day move reversal | Weekly-option fades | See D8 | **Tested** — S16a QQQ, absolute gap ≥ 0.5 % days: +17.8 bp [+4.7, +30.2] (6 cells with positive lower bounds against 2.7 expected by chance). S16b weekly-option expression +$1.83 [−16.40, +21.02], equal to a random direction on all days | — | Low (closed) |

### 2.5 Calendar / session

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| C1 | Pre-FOMC drift | Calls before the statement | +49 bp in the 24 hours before scheduled FOMC decisions, 1994–2011 (paper) [LM15]; it essentially vanished after 2015, sample to 2019 [KWG21] | **Not tested** (direction); only D_FOMC straddles (S9) | Yes: M1-IDX 2017 → (mostly after 2015), EV | Low — decayed, and directional |
| C2 | Returns on macro announcement days | — | 11.4 bp vs 1.1 bp, 1958–2009 (paper) [SW13]; 10.68 vs 0.93 bp in 1961–2023 per a 2025 survey [sec] | **Not tested** | Yes: M1-IDX, EV | Low — direction, about 10 bp |
| C3 | Turn of the month | — | High returns at the turn of the month [Ariel87], [LS88]; it persisted in 1987–2005 and appears in 31 of 35 countries (abstract) [MX08] | **Not tested** for returns (month-end variance: S10) | Yes | Low |
| C4 | Day of week / weekend effect | — | Negative weekend returns [French80]; the weekend effect weakened or disappeared after publication [Schwert03] | **Partly** — VF weekday ratios (Monday 0.89×); weekday skip rules hurt out of sample (Friday −0.0272, Tuesday −0.0216, Monday −0.0153); SVS weekday cuts not significant | Yes | Low |
| C5 | Pre-holiday sessions | — | High returns before holidays [Ariel90] | **Partly** — VF: holiday-adjacent afternoons 0.82× [0.66, 1.02]; skipping them −0.0130 [−0.0183, −0.0074] | Yes | Low |
| C6 | Options-expiration week and day | — | S&P 100 stocks earn more in options-expiration weeks (abstract) [SS13]; see [NPP05] | **Partly** — VF: monthly-opex afternoons 0.94× [0.73, 1.20], quarterly 1.04× [0.62, 1.60]; skipping opex −0.0066 | Yes (index); single names via UW-C | Low |
| C7 | Intraday return seasonality (half-hours; the same half-hour on later days) | Time-of-day direction | A stock's return in a half-hour predicts its return in the same half-hour on later days, for at least 40 trading days (abstract) [HKS10] | **Partly** — report T4 (SPY/QQQ/IWM 2025-06 → 2026-10): no half-hour has an absolute t of 2 or more; the same-half-hour persistence was not tested | Yes: M1-* | Low — bp-sized, directional |

### 2.6 Direction / trend / reversal

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| D1 | Technical trading rules (moving averages, trading-range breaks) | Direction for longer-dated options | [BLL92] and [STW99] as in L1. DJIA 1897–2011: low costs offset the rules' performance even in sample, and the best rules could not be picked ex ante [BS12]. Survey: in the 2004 version, 58 of 92 modern studies were positive, mostly before the early 1990s [PI07] | **Tested** — S04, S06, S07. Lifecycle daily trend and breakout setups: 19 finalists, and 0 of 19 beat random days in the same direction (R2) | — | Low (closed) |
| D2 | Intraday entry triggers (RSI, EMA, VWAP reclaim, breakouts, retests, pullbacks, bounces) | Compass setups | — | **Tested** — S04: the baseline rule −1.3 bp [−2.4, −0.2] at 30 minutes (SPY). S06: about 450,000 index events, no trigger with an absolute lower bound of +3 bp. S06-TierA: 0 of 808 cells. S01 −$4.19 [−5.68, −2.81]; S09 −$46.18; S02: 41 variants, none | — | Low (closed) |
| D3 | First half-hour → last half-hour (market intraday momentum) | 15:30 0DTE direction | SPY 1993–2013, stronger on volatile and news days (paper) [GHLZ18]; R² about 2 % in the 1999–2012 working-paper sample [sec]; significant in and out of sample in most of 16 developed markets [LSU22, sec] | **Tested** — S12 (2017–2026): 15:30 → 16:00 is within ±2 bp with intervals spanning zero on all three ETFs. Report T4: correlation −0.036, signs agree 46.7 % of days | — | Low (absent here) |
| D4 | End-of-day momentum with negative dealer gamma; leveraged-ETF rebalancing | 15:30 direction on short-gamma days | 60+ futures 1974–2020: the last 30 minutes load on the rest of the day, β 6.63 (t 4.78) on negative-gamma days vs 0.82 (t 1.03) on positive [BDLM21, repo]. Leveraged-ETF rebalancing raised end-of-day volatility in 2006–2011 (abstract) [Shum16] | **Tested** — H10: on SPY negative-gamma days, −3.07 bp/day [−5.73, −0.52], the wrong sign (299 days, 2024-05 → 2026-10) | Partly: gamma only from 2024-05 | Low |
| D5 | First half-hour → rest of the day | 10:00 direction | As D3 | **Tested** — S12: QQQ 10:00 → 15:00 +4.3 bp [+0.8, +7.8], and +9.0 [+2.8, +15.3] when the first 30 minutes moved 0.3 % or more; SPY and IWM not significant; the Bonferroni lower bound is −2.5 bp. S12b: long −$4.87 [−14.18, +4.87]; short vertical −$2.56 [−4.72, −0.33] | — | Low |
| D6 | Noise-band intraday momentum (trade out of the open's noise area) | Direction, traded in shares | SPY 2007–2024, net Sharpe 1.33 in shares (working paper) [ZAB24, repo] | **Not tested** | Yes: M1-ETF | Low for options — test in shares if at all (O8) |
| D7 | Time-series momentum (1–12 months) | Long-dated direction | 58 futures 1985–2009: each contract's past 12-month return predicts its next month (paper) [MOP12]; asset by asset the evidence is weak [HLWZ20]; volatility scaling drives much of it [KTW16] | **Partly** — lifecycle daily trend setups ≈ random days; S07 trend pullback −69 bp [−113, −24] at 21 sessions | Yes: EOD-ETF, D-ALL | Low |
| D8 | Short-term reversal (1 day – 1 month) | Swing fades | Monthly reversal [Jeg90]; reversals sit in illiquid stocks, and the profits are smaller than likely costs (abstract) [ACG06]; reversal returns track the return to liquidity provision [Nagel12] | **Tested** — S07 5-day reversal +53 bp [−16, +121]. S14 1-month reversal, long leg: +398 bp [+59, +737] absolute, +247 [−38, +598] against the universe. G6 | — | Low |
| D9 | Cross-sectional momentum (12-1) | — | Buying past winners and selling past losers earned money 1965–89 [JT93] | **Tested** — S14: indistinguishable from the universe; shorting the bottom decile −576 bp [−1,120, −140] | Yes: D-ALL (20–34 rebalances; more years arriving) | Low |
| D10 | Earnings drift and pre-earnings run-up | Calls into or after reports | Post-earnings-announcement drift [BT89] (not re-checked here) | **Tested** — S08 "sell the beat": the surprise direction, adjusted, −31 bp [−59, −2] at 21 sessions. S13: the 10 sessions before a report +97 bp [+62, +133] absolute, +20 [+4, +36] adjusted, carried by a tail (−7 bp without the top 1 %) and by Q2 reports. S11 option expression pending (n ≤ 20) | Yes (S11 pull) | Low-medium |

### 2.7 Volume / flow–price

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| V1 | High-volume return premium | Swing direction | Unusually high (low) volume over a day or week is followed by higher (lower) returns over the next month (abstract) [GKM01] | **Not tested** (S07's event shock, relative volume ≥ 3: not significant) | Yes: D-ALL | Low |
| V2 | Volume and serial correlation; relative-volume filters | Confirming a move | Price changes on high volume reverse less [CGW93]; [Karpoff87] | **Tested** — relative volume as a filter in S01/S02 (off, 1.25, 1.5, 2.0): nothing positive; S04: removing it changes nothing | — | Low |
| V3 | Options flow, net premium, market tide, dark pool as price predictors | Entries | Opening customer buys predict single stocks (about 40 bp a day) but not index options [PP, repo] | **Tested** — H2: 0 of 62 cells; ICs −0.011 to +0.020, against 0.51–0.67 with the trailing 15 minutes. H3: burst contracts −6 to −8 % | — | Low (index); single-name flow from the tape (`03_compass_plan.md` §3) is open but is not price action |

### 2.8 Cross-asset / lead–lag

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| X1 | Futures lead the cash index | A faster index signal | S&P 500 futures lead the cash index by about 5 minutes, sometimes 10 or more (abstract) [SW90]; E-mini futures dominate index price discovery [Hasb03] | **Not tested** | No: no futures on disk | Low — minutes-scale and arbitraged; SPY/SPX options already follow the futures |
| X2 | Large caps lead small caps; industry leaders lead followers | IWM or laggard options after a leader moves | Large-stock returns lead small-stock returns [LM90]; high-volume stocks lead [CS00]; industry leaders lead [Hou07] | **Not tested** | Yes: M1-ETF, M1-A, D-ALL | Low — published sizes are inside costs (`01_audit_and_gaps.md` §4) |
| X3 | VIX moves → index realized | Skip or size | — | **Tested** — VF: the VIX change from the open to 13:00 has an IC of +0.026 [−0.014, +0.061] with the afternoon absolute move; skip rules were negative | — | Low |
| X4 | Rates, FX and commodities → equities | Macro context | (not reviewed in this pass) | **Not tested** | No: no futures, FX or rates before 2024 | Low |

### 2.9 Regime

| # | Angle | What an options trader would use it for | Published evidence (one line + key) | Tested here? | Testable with our data? | Priority for options |
|---|---|---|---|---|---|---|
| R1 | Dealer gamma regime as a direction filter | Momentum days vs mean-reversion days | [BDLM21] (D4); [BB21] | **Tested** — H4: the afternoon-on-morning slope differs by +0.03 [−0.12, +0.19] between regimes, and its sign flips from in-sample to out-of-sample. Two gamma proxies agree on the regime 52 % of days (H10); intraday and prior-day signs agree 54 % [repo] | — | Low for direction; as a size variable see S12 |
| R2 | Trend regime (the bull market's drift) | Bullish vs bearish structures | (market drift; no paper needed) | **Tested** — lifecycle: any long-dated bullish structure bought every Monday in 2013–2023 made money (LEAPS Steady call +$1,326 [+1,112, +1,542]); daily management rules "work" only by following the trend's sign | — | Medium as context — every result must be netted of drift |
| R3 | VIX term-structure slope | Straddle timing | The slope predicts straddle returns (Johnson 2017) [repo]; refuted at retail costs by three skeptic checks (`../10_external_research.md` L1) | **Partly** — refuted on the literature; no P&L test | No: VIX9D/VIX3M not on disk | Low |

(S10, S11 and S12 cover the volatility-level and gamma-size regimes.)

---

## 3. What the published record adds, in one paragraph per family (my summary)

- **Size is forecastable and mostly priced.** Realized volatility clusters, and HAR-type models built from realized measures forecast it well [Corsi09], [ABDL03]. But implied volatility already contains that information and more [CP98], [BCN11]. Trading a forecast against implied paid in one early sample [NEK94] and not after costs in another [HW92]. Here, the daily-HAR and trailing-realized versions failed (A11, S15). Untested here: **intraday** information (morning realized variance, which the SPX study shows adds OOS R² 0.151 [0.054, 0.254] over a trailing average for the afternoon range), and the **event, time-of-day and overnight structure** of variance.
- **Path is the least studied.** The time of the extremes follows a random-walk benchmark once trading speed varies through the day [MLL00]. Touch and finish probabilities follow the reflection principle under a diffusion. No peer-reviewed study found in this pass calibrates 0DTE chain probabilities against realized touch and finish frequencies; practitioner evidence says straddles over-forecast the move [FlashAlpha].
- **Levels work in FX order books and in microstructure** (round numbers: [Osler03], [BHJ12]). Option-strike pinning was real in older samples [NPP05], [GJ12] and is reported absent in SPY since 2016 [repo]. Every level tested here as a trigger fired after the move.
- **Calendar and direction anomalies decay after publication** ([Schwert03], [KWG21], [STW99], [BS12]). What survives tends to be bp-sized and traded in shares or futures, not options.

---

## 4. Open angles worth testing, in order

Ordered by expected value for options: size and path first. Direction is largely tested and empty here.

**Every design follows the repository's protocol** (`../04_protocol.md` §5–§7):
- fills at the NBBO, ask in and bid out, every leg;
- $0.70 per contract per side per leg;
- a +1-tick-every-leg adverse scenario;
- day-clustered bootstrap intervals (5,000 draws, seed 7);
- matched controls;
- pre-registration as a dated amendment before any outcome is read;
- the hold-out opened once.

**The windows for the same-day index products** (the same for every design below unless stated):
- **development:** SPXW 2022-05-13 → 2024-12-31, SPY and QQQ 2022-11-11 → 2024-12-31, IWM 2024-04-19 → 2024-12-31;
- **validation:** 2025-01-02 → 2025-09-30;
- **2025-10-01 → 2026-10-09:** already opened for other hypotheses (the lifecycle hold-out, H-FLO, L-A3 and the H15 test). It is reported, labelled "previously analysed", and is never the deciding data;
- **deciding hold-out:** forward sessions from 2026-10-12, at least 150 sessions (GATE-v2 asks 150 sessions and 7 months for a carry lane).

**Underlying-only model fits** use 2017-06-01 → 2022-04-29, which predates every cached 0DTE chain. They are frozen before the chains are read.

### O1. Does intraday information forecast the rest-of-day move better than the 0DTE straddle prices it?

| Item | Design |
|---|---|
| Universe | SPY, QQQ, IWM and SPXW same-day expirations (Q0); underlying one-minute bars (M1-ETF; M1-IDX for SPX, VIX). |
| Decision times | 10:00 and 13:00, and no others. |
| Implied move (OBSERVED quotes → CALCULATED) | I_t = (call mid + put mid at the strike nearest S_t, both legs two-sided) ÷ S_t. |
| Forecast (MODELED) | F_t = the model's forecast of the absolute move from t to the close, from an OLS on logs fitted in the 2017-06 → 2022-04 window and frozen. Predictors, all known at t: realized variance 09:30 → t divided by the time-of-day share of that window [ES12]; prior-day realized variance and 5- and 22-day means (HAR, [Corsi09]); the absolute overnight gap; VIX at t; the negative-return share of realized variance so far [PS15]; cumulative volume at t against its 20-day median at the same minute; flags for FOMC day, month-end and CPI/NFP day. |
| Test 1 (no P&L) | Encompassing regression: log(absolute move to the close / S_t + 1 bp) on log I_t and log F_t, pooled across roots, errors clustered by date. **H1: the coefficient on log F_t > 0** (one-sided), one test per decision time. Reported alongside, with no test: the QLIKE and MSE loss of F against I [Patton11]; the slope on log I_t; the elasticity of I_t to the morning range against the realized elasticity (the gap VF could not close). |
| Test 2 (option), only if Test 1 passes at that time | z_t = log(F_t / I_t), with quintile cut-points fixed on development. Top quintile: buy the ATM straddle at the ask, sell at 15:50 at the bid. Bottom quintile: sell it at the bid and buy it back at 15:50 at the ask, leaving legs at $0.05 or less to expire (H14); SPXW short also held to settlement. |
| Comparison with the option's price | The straddle **is** the price. Each cell is compared, paired by day, with: (a) the same structure at the same time on every day; (b) the same number of days drawn at random (5 seeds); (c) S15's trailing-realized rule. **Promotion:** the development + validation lower bound is above zero for the cell, and for the cell minus the unconditional structure; the validation sign is the same; the hold-out mean has the same sign; and it survives +1 tick on every leg. |
| Costs | Measured NBBO; C1's measured $12.93 SPY/QQQ straddle round trip is the reference. |
| Tests | 2 (Test 1) + 4 (2 times × long/short) = **6**. |
| Prior | Negative for Test 2: A11, S15, and VF's finding that VIX skips lower the mean because the credit already prices the volatility level. Test 1 is cheap and decides whether Test 2 is run at all. |

### O2. Are the 0DTE chain's probabilities calibrated (finish and touch), by distance and time of day?

| Item | Design |
|---|---|
| Universe and times | As O1; 10:00 and 13:00. |
| Chain probabilities (MODELED from OBSERVED quotes) | The risk-neutral probability of finishing above K, from adjacent call mids: q(K) ≈ (C(K₋) − C(K₊)) / (K₊ − K₋). Puts are checked by parity. Only strikes whose legs have a relative spread of 20 % or less are used. Distance d = ln(K/S_t) / (σ_imp √τ), bucketed at ±0.25, 0.5, 0.75, 1.0, 1.5 and 2.0. |
| Realized (CALCULATED) | Finish = 1{S_close > K}. Touch = 1{the highest price from t to 16:00 ≥ K}; mirrored for strikes below. |
| Benchmark (MODELED) | Reflection principle: touch ≈ 2 × the finish probability for out-of-the-money strikes (table in A5). |
| Test 1 | Berkowitz likelihood-ratio test of the probability integral transform of the realized close under the chain's distribution [Berk01], one per decision time. **H1: the chain is miscalibrated.** Reported with no test: the calibration curve (realized − q by bucket, with intervals) and the touch-to-finish ratio against 2. |
| Test 2 (option) | One band per side, fixed now from the literature rather than from the curve: the 1-implied-move wings, near 0.16 delta. At 13:00, sell a one-strike-wide credit vertical at that distance (calls side; puts side); hold to settlement (SPXW) or to the 16:00 intrinsic (ETFs, with H16's after-hours caveat). **H1: the mean after costs > 0.** Controls: the same vertical at a random minute 10:00–14:30 (H15 showed timing can be the control), and at 0.5 implied moves. |
| Costs | Measured NBBO, both legs; adverse tick. |
| Tests | 2 + 2 = **4**. |
| Prior | Mixed. The ETF grid's 1-expected-move strangle was positive in TEST (+$11.50 [+1.75, +20.05]) but not in TRAIN, and TEST overlaps the "previously analysed" window, so the forward hold-out decides. |

### O3. Is overnight variance on next-day expirations priced differently from daytime variance?

| Item | Design |
|---|---|
| Universe | SPY and QQQ (daily expirations; the Q0 cache starts 2022-11-11), IWM (from 2024-04-19), SPXW (from 2022-05-13). |
| Data | The quote at D 15:50 for the next session's expiration: a one-expiration pull of one-minute NBBO, 15:45–16:00, for about 3,700 root-sessions (980 + 980 + 621 + 1,106). The fallback is the EOD-ETF closing NBBO, flagged because ETF options trade until 16:15 and that quote is not simultaneous with the 16:00 underlying close. The same contract at D+1 09:35 is already in Q0. |
| Trades | **Night:** sell the ATM straddle of the D+1 expiration at D 15:50 at the bid; buy it back at D+1 09:35 at the ask. **Day:** sell the same strike at 09:35 at the bid; buy it back at 15:50 at the ask. Both unhedged and delta-hedged with shares at the two marks (shares cost about 0.15 bp). |
| Statistics | P&L as a share of the entry mid; night minus day, paired by date. CALCULATED, no test: the implied overnight variance (the D 15:50 straddle's variance minus the D+1 09:35 straddle's) against the realized squared overnight return. |
| Cells and tests | (1) weekday nights, short night straddle, mean > 0; (2) night minus day > 0; (3) nights before an 08:30 CPI/NFP release (the event-eve premium, `../10_external_research.md` E5). Weekend and holiday nights are reported only (G3 found them mostly priced). **3 tests.** |
| Prior | Supportive: [MN20], about −1 % close-to-open for delta-hedged index options; [FR86] variance concentrated in trading hours. Against: closing spreads widen (Goyenko–Zhang, in the repo's L6 note), and L6 found the weekend mostly priced in weeklies. |

### O4. Event afternoons: does the 13:00 straddle price the measured multiple?

| Item | Design |
|---|---|
| Universe | SPXW, SPY, QQQ same-day expirations; EV. |
| Statistic | R_imp = I_13:00 on the event day ÷ the median I_13:00 over the prior 20 event-free sessions. R_real = the event-free multiple measured on SPX 2017–2026: 2.08× [1.56, 2.68] for FOMC, 1.33× [1.06, 1.65] for month-end (H17). |
| Tests | **H1: R_imp < R_real** (the event afternoon is under-priced), one-sided, one for FOMC and one for month-end: **2 tests**. With about 30–35 FOMC days in Q0 the power is low, and the minimum detectable gap is reported. |
| Option expression | Not pre-registered until at least 60 events (forward accrual), because A13 had ± $400 intervals on 27 days. |

### O5. Does dealer gamma explain realized relative to implied, not realized alone?

| Item | Design |
|---|---|
| Data | The prior session's naive-sign gamma: UW-G 2025-10-15 → 2026-10-13, which H-FLO already used, so that window is "previously analysed". For a development window, a house estimate (open interest × Black–Scholes gamma, both signs, as the terminal models it) needs an open-interest pull for the near expirations 2022-11 → 2025-09; that endpoint is throttled to about 0.1 requests a second. |
| Test | Add the sign and the absolute size of gamma to O1's Test 1 regression. **H1: negative gamma raises realized relative to implied**, at 10:00 and 13:00: **2 tests**. |
| Option expression | Only if it passes: H-FLO-2's long straddle on negative-gamma days, compared with the unconditional straddle rather than with positive-gamma days. |
| Prior | The FlashAlpha control (−0.03 once VIX and ATM IV are included) suggests it is priced. |

### O6. Conditional index put-writing: does a size forecast improve S17?

| Item | Design |
|---|---|
| Data | SPY and QQQ monthlies (EOD-ETF), 2017-06 → 2026-10: about 112 cycles each. Before 2017 the closes come from parity and there are no minute bars. |
| Signal | G = 30-day ATM IV − the HAR forecast of the next month's realized variance (as volatility). Sell S17's ATM put only when G is above its trailing 36-month median. |
| Comparison | The same month's unconditional S17 trade, paired. **H1: conditional minus unconditional > 0. 1 test.** |
| Prior and power | Weak. VF's VIX-skip and lifecycle results say skipping on the volatility level costs premium. About 56 cycles in each arm; the minimum detectable difference is stated before the run. |

### O7. Do levels hold more often than matched random levels? (path, for short-strike placement)

| Item | Design |
|---|---|
| Universe | M1-ETF, M1-IDX, M1-A, 2017-06 → 2026-10. |
| Levels | (a) the prior day's high and low; (b) round numbers (SPY whole and $5 levels; SPX 25, 50 and 100 points; single names' whole dollars). For each real level, five pseudo-levels at the same distance from the 10:00 price: H6's design. |
| Statistic (CALCULATED) | P(close beyond the level, given it was touched), real minus pseudo. **H1: real levels hold more** (lower close-beyond rate): **2 tests**, one per level family. Reported alongside: P(touch) and the move through the level after a touch. |
| Windows | Development 2017-06 → 2021-12, validation 2022-01 → 2024-12, hold-out 2025-01 → 2026-10 (underlying only). Caveat: S06's bounces read these sessions for direction, not for hold rates. |
| Option expression | Only if it passes: a short 0DTE vertical with its short strike one strike beyond the level at the first touch, against the same vertical at the matched pseudo-level, on the forward hold-out. |
| Prior | Osler (FX) and BHJ12 (microstructure) are supportive; H6 (GEX walls ≈ random levels) is not. |

### O8. Outside the options family: noise-band intraday momentum in SPY shares

[ZAB24] reports a net Sharpe of 1.33 in shares. It is directional and earns bp-sized moves, so it belongs to an underlying lane, not to options (`../../../reports/Finding a 0DTE options edge.md`, "move every directional idea to the underlying").
- 1 test.
- Its own family and α.
- Costs at 0.2 bp a side.
- Development 2017–2021, validation 2022–2024, hold-out 2025–2026.

### The multiple-testing budget

**The list implies 20 confirmatory tests** in the options family: O1 6, O2 4, O3 3, O4 2, O5 2, O6 1, O7 2. O8 is 1 test in a separate family.

**Recommended family-wise control (5 %):** a weighted Bonferroni split of α across the angles, with a fixed sequence inside each angle.
- **The weights encode the order above:**

  | Angle | α |
  |---|---|
  | O1 | 0.015 |
  | O2 | 0.010 |
  | O3 | 0.010 |
  | O4 | 0.005 |
  | O5 | 0.005 |
  | O6 | 0.0025 |
  | O7 | 0.0025 |
  | Total | 0.05 |

- **Inside an angle:** the calibration or encompassing test (the gate) is tested first at the angle's full α. Its option cells are tested, Holm at the same α, only if the gate rejects.
- **Why it holds:** the split is a union bound across angles and fixed-sequence-plus-Holm within each, so the family's FWER stays at 5 % however the gates fall.
- **It costs no power** compared with a flat Bonferroni over 20 (0.0025 each), for the high-priority angles.
- **Grids keep the protocol's Romano–Wolf step-down** (§7).
- **The A5 batch rule still applies:** the same sign in every year of the window.

**Two rules protect the budget:**
1. **No statistic from the atlas (§5) may choose a test** run on the same sessions. A pattern the atlas suggests is tested on the forward hold-out only.
2. **No new entry-pattern variants.** S01–S16, S06-TierA and lifecycle 04 spent that family (`03_compass_plan.md` §4).

---

## 5. Descriptive atlas (no hypothesis budget spent)

Statistics a desk should see before choosing strikes, expirations and times. Each is CALCULATED from OBSERVED bars and quotes; null benchmarks are MODELED. None is a trade signal.

**Show each:**
- per name;
- by time of day where it applies;
- for 2017–2022 and 2023–2026 side by side, so a reader sees whether it held;
- with its sample size.

**What already exists:**
- PB §1–§6 (SPY/QQQ/IWM/SPX, 2022-11 → 2025-09);
- VF (SPX 2017–2026, afternoons);
- SVS T4/T5 (2025-06 → 2026-10);
- `../studies/pa_atlas.py`, being written in parallel today (file dated 2026-10-15 22:15). Per its docstring it covers every root with cached one-minute bars (the 40 Tier A roots, SPY, QQQ, IWM), 2017-06 → 2026-10. Its outputs were not read for this note. It computes:
  - the remaining move from each half hour;
  - touch odds from 10:00 against a trailing 20-day σ;
  - path and opening-range shares;
  - prior-day levels and VWAP crosses;
  - gap fill by size;
  - calendar ranges;
  - descriptive correlations;
  - HAR OOS R² on the log range;
  - a 5-minute activity profile.

| # | Statistic (CALCULATED unless marked) | Why a desk needs it | Data | Exists? |
|---|---|---|---|---|
| A1 | Daily range: median, 25th and 90th percentiles, by year and VIX tercile | Strike distance for multi-hour structures; stress size | M1-* | PB §1 (4 roots); pa_atlas (43 roots, in progress) |
| A2 | Remaining move and remaining range from t to the close, quantiles, for every half hour; on Q0 roots also in units of the implied move at t | How far a position can still run; whether a strike is in reach | M1-*, Q0 | pa_atlas in %; **in implied-move units: not built** |
| A3 | Time-of-day volatility profile: each 5-minute block's share of the day's variance; the first-30 and last-30 shares; FOMC, CPI and NFP days separately | Variance-time for theta comparisons; the null for A4 | M1-* | pa_atlas (absolute-move share, all days); PB half-hour detail; **event-day profiles: not built** |
| A4 | When the high and the low form: P(the high falls in block b), P(the low falls in b); P(the day's high is already in by t, given price is inside the range at t). Null (MODELED): the arcsine law in clock time and in variance time, P(the maximum falls in the first fraction f) = (2/π)·arcsin(√f) | Whether to place short strikes beyond the morning's extremes after 10:30 | M1-* | PB §1; pa_atlas (first/last 30). **The conditional "already in" probability and the null comparison: not built.** For scale, in clock time the null gives 17.9 % for the first 30 of 390 minutes and 25.7 % for the last 60 (MODELED, this note); SPY's observed high/low in the first 30 minutes (23 % / 27 %) sit above the clock-time null, and after 15:00 (30 % / 20 %) they straddle it, as an upward drift would. The fair comparison is the variance-time null, which needs A3's measured first-30 share |
| A5 | Touch and finish probabilities for ±k: k in units of a trailing σ (underlying) and of the straddle-implied move (Q0), by entry time; the touch-to-finish ratio; P(back inside at the close, given touched) | Strike distance and stop rules for short premium | M1-*, Q0 | pa_atlas (trailing σ, 10:00 only). **In implied units by time: not built.** Reflection benchmarks below |
| A6 | Overnight gaps: size in σ units, fill rate and time to fill by size bucket, close beyond the open in the gap's direction | Opening straddle and strike choice | M1-*, D-ALL | SVS T5 (2025-06 → 2026-10); pa_atlas 2017 → |
| A7 | Overnight vs intraday variance share, weeknights vs weekends and holidays; FR86's per-hour ratio per name | O3's denominator; overnight risk of physically settled ETF options held to expiry | M1-*, D-ALL | **Not built** (pa_atlas reports mean overnight and intraday returns, not variance) |
| A8 | Trend days vs range days: close location in the range, efficiency (absolute close − open) ÷ range, 30-minute vs 1-minute variance ratio | Long or short gamma frequency; how often a short straddle faces a one-way day | M1-* | PB §1 (close location); pa_atlas (close location ≥ 0.9 or ≤ 0.1); **variance ratio: not built** |
| A9 | Calendar and event profiles: range, morning, afternoon and absolute move on FOMC, CPI, NFP, opex, quarter-end, month-end, first session, holiday-adjacent days, each weekday | Event-day sizing; skip lists | M1-*, EV | VF (SPX afternoons); pa_atlas (full-day range, 10:00 → close) |
| A10 | Implied vs realized by time of day (Q0): median realized ÷ implied for the move from t to the close; breach rates of ±0.5, 1 and 1.5 implied moves; the same on event days | Which hour's premium is richest; the calibration behind O1 and O2 | Q0 | **Not built** for 0DTE (V2 has the earnings version: 0.59 of implied) |
| A11 | Level touch and hold rates: prior-day high, low and close; opening-range extremes; VWAP ± kσ; round numbers; high open-interest strikes on single-name monthly expirations, each with a distance-matched random-level baseline | Strike placement beyond levels without over-trusting them | M1-*, UW-C | pa_atlas (prior-day levels, no random baseline); H6 (GEX levels with baseline); **round numbers and OI strikes: not built** |
| A12 | Jumps and tails: days with an absolute move above 3× the trailing σ; the largest 1- and 5-minute moves; jump counts (Lee–Mykland statistic) | Short-premium sizing and wing width | M1-* | **Not built** |
| A13 | Cost by time of day and moneyness: median relative spread at 09:30, 12:00 and 15:00 for Steady, Big Payoff and put-sale strikes | The hurdle every angle must clear | Q0, QW | PB §6; C1; `../10_external_research.md` C2 |
| A14 | Realized vs implied per name, monthly (IV ÷ RV21 history, forward realized minus implied) | Labelling a name "options price more or less movement than recent realized" without a trade claim | UW-C | V1 quintiles (pooled); per name: not built |
| A15 | How a weekly prices the weekend: Friday's implied variance per remaining session against Monday's | Monday-not-Friday convention (G3) | QW, EOD-ETF | L6 local check (SPY 2017–2022 sample) |
| A16 | Co-movement: intraday correlation and beta of each name to SPY, by regime | "The same bet twice" (PB §8) | M1-* | **Not built** |

**Reflection-principle benchmarks for A5** (MODELED, this note): driftless Brownian motion, constant volatility, no jumps. The straddle-implied move M equals √(2/π) σ√τ ≈ 0.798 σ√τ, so 1 M ≈ 0.80σ and 2 M ≈ 1.60σ.

| Level | Finish beyond one side | Touch one side | Touch either side | Finish outside ±level |
|---|---|---|---|---|
| ±0.5σ | 30.9 % | 61.7 % | 99.1 % | 61.7 % |
| ±1 M (0.80σ) | 21.2 % | 42.5 % | 81.7 % | 42.5 % |
| ±1σ | 15.9 % | 31.7 % | 62.9 % | 31.7 % |
| ±1.5 M (1.20σ) | 11.6 % | 23.1 % | 46.2 % | 23.1 % |
| ±2 M (1.60σ) | 5.5 % | 11.0 % | 22.1 % | 11.0 % |
| ±2σ | 2.3 % | 4.6 % | 9.1 % | 4.6 % |

Observed rates below these mean intraday mean reversion or overpriced wings. Rates above them mean jumps or trending days. Either way, A5 and A10 measure it before any money is at risk.

---

## 6. References

Keys as used above. DOIs were checked against Crossref on 2026-10-15; "[sec]" marks numbers taken from summaries rather than the paper.

**Volatility, forecasting, variance premium**
- [ABDL03] Andersen, Bollerslev, Diebold, Labys (2003), "Modeling and Forecasting Realized Volatility", *Econometrica* 71(2), 579–625. https://doi.org/10.1111/1468-0262.00418
- [AB97] Andersen, Bollerslev (1997), "Intraday periodicity and volatility persistence in financial markets", *Journal of Empirical Finance* 4(2–3), 115–158. https://doi.org/10.1016/S0927-5398(97)00004-2
- [AB98] Andersen, Bollerslev (1998), "Answering the Skeptics: Yes, Standard Volatility Models Do Provide Accurate Forecasts", *International Economic Review* 39(4), 885–905. https://doi.org/10.2307/2527343
- [BCN11] Busch, Christensen, Nielsen (2011), "The role of implied volatility in forecasting future realized volatility and jumps in foreign exchange, stock, and bond markets", *Journal of Econometrics* 160(1), 48–57. https://doi.org/10.1016/j.jeconom.2010.03.014
- [BK03] Bakshi, Kapadia (2003), "Delta-Hedged Gains and the Negative Market Volatility Risk Premium", *Review of Financial Studies* 16(2), 527–566. https://doi.org/10.1093/rfs/hhg002
- [BTZ09] Bollerslev, Tauchen, Zhou (2009), "Expected Stock Returns and Variance Risk Premia", *Review of Financial Studies* 22(11), 4463–4492. https://doi.org/10.1093/rfs/hhp008
- [CODWY20] Cederburg, O'Doherty, Wang, Yan (2020), "On the performance of volatility-managed portfolios", *Journal of Financial Economics* 138(1), 95–117. https://doi.org/10.1016/j.jfineco.2020.04.015
- [Corsi09] Corsi (2009), "A Simple Approximate Long-Memory Model of Realized Volatility", *Journal of Financial Econometrics* 7(2), 174–196. https://doi.org/10.1093/jfinec/nbp001
- [CP98] Christensen, Prabhala (1998), "The relation between implied and realized volatility", *Journal of Financial Economics* 50(2), 125–150. https://doi.org/10.1016/S0304-405X(98)00034-8
- [CW09] Carr, Wu (2009), "Variance Risk Premiums", *Review of Financial Studies* 22(3), 1311–1341. https://doi.org/10.1093/rfs/hhn038
- [DJKS19] Dubinsky, Johannes, Kaeck, Seeger (2019), "Option Pricing of Earnings Announcement Risks", *Review of Financial Studies* 32(2), 646–687. https://doi.org/10.1093/rfs/hhy060
- [ES12] Engle, Sokalska (2012), "Forecasting intraday volatility in the US equity market. Multiplicative component GARCH", *Journal of Financial Econometrics* 10(1), 54–83. https://ideas.repec.org/a/oup/jfinec/v10yi1p54-83.html
- [GK80] Garman, Klass (1980), "On the Estimation of Security Price Volatilities from Historical Data", *Journal of Business* 53(1), 67–78. https://doi.org/10.1086/296072
- [GS09] Goyal, Saretto (2009), "Cross-section of option returns and volatility", *Journal of Financial Economics* 94(2), 310–326. https://doi.org/10.1016/j.jfineco.2009.01.001
- [HW92] Harvey, Whaley (1992), "Market volatility prediction and the efficiency of the S&P 100 index option market", *Journal of Financial Economics* 31(1), 43–73. https://doi.org/10.1016/0304-405X(92)90011-L
- [LeeM08] Lee, Mykland (2008), "Jumps in Financial Markets: A New Nonparametric Test and Jump Dynamics", *Review of Financial Studies* 21(6), 2535–2563. https://doi.org/10.1093/rfs/hhm056
- [MM17] Moreira, Muir (2017), "Volatility-Managed Portfolios", *Journal of Finance* 72(4), 1611–1644. https://doi.org/10.1111/jofi.12513
- [NEK94] Noh, Engle, Kane (1994), "Forecasting Volatility and Option Prices of the S&P 500 Index", *Journal of Derivatives* 2(1), 17–30; working paper NBER w4520. https://www.nber.org/papers/w4520
- [Park80] Parkinson (1980), "The Extreme Value Method for Estimating the Variance of the Rate of Return", *Journal of Business* 53(1), 61–65. https://doi.org/10.1086/296071
- [Patton11] Patton (2011), "Volatility forecast comparison using imperfect volatility proxies", *Journal of Econometrics* 160(1), 246–256. https://doi.org/10.1016/j.jeconom.2010.03.034
- [PS15] Patton, Sheppard (2015), "Good Volatility, Bad Volatility: Signed Jumps and the Persistence of Volatility", *Review of Economics and Statistics* 97(3), 683–697. https://doi.org/10.1162/REST_a_00503
- [RS91] Rogers, Satchell (1991), "Estimating Variance From High, Low and Closing Prices", *Annals of Applied Probability* 1(4), 504–512. https://doi.org/10.1214/aoap/1177005835
- [YZ00] Yang, Zhang (2000), "Drift-Independent Volatility Estimation Based on High, Low, Open, and Close Prices", *Journal of Business* 73(3), 477–492. https://doi.org/10.1086/209650

**Intraday patterns, overnight, path**
- [Acar] Acar, Toffel, "Timing the highs and lows of the day" (practitioner study for LIFFE, FTSE 100 futures 1992-07 → 1995-09; undated; copy hosted on a forum). https://www.financnik.cz/forum/uploads/monthly_2010_11/acar-emmanuel-timing-the-highs-and-lows-of-the-day.pdf
- [Aldous] Aldous, "Arc sine laws and stock prices" (expository note). https://www.stat.berkeley.edu/~aldous/Real-World/arc-sine.html
- [BDLM21] Baltussen, Da, Lammers, Martens (2021), "Hedging demand and market intraday momentum", *Journal of Financial Economics* 142(1), 377–403. https://doi.org/10.1016/j.jfineco.2021.04.029 (working paper: https://www3.nd.edu/~zda/intramom.pdf)
- [BM23] Bondarenko, Muravyev (2023), "Market Return Around the Clock: A Puzzle", *Journal of Financial and Quantitative Analysis* 58(3), 939–967. https://ideas.repec.org/a/cup/jfinqa/v58y2023i3p939-967_1.html
- [CCG08] Cliff, Cooper, Gulen (2008), "Return Differences between Trading and Non-Trading Hours: Like Night and Day", working paper. https://doi.org/10.2139/ssrn.1004081
- [FR86] French, Roll (1986), "Stock return variances: The arrival of information and the reaction of traders", *Journal of Financial Economics* 17(1), 5–26. https://doi.org/10.1016/0304-405X(86)90004-8
- [GHLZ18] Gao, Han, Li, Zhou (2018), "Market intraday momentum", *Journal of Financial Economics* 129(2), 394–414. https://doi.org/10.1016/j.jfineco.2018.05.009 (R² from the CXO summary of the working paper [sec]: https://www.cxoadvisory.com/?p=25481)
- [Harris86] Harris (1986), "A transaction data study of weekly and intradaily patterns in stock returns", *Journal of Financial Economics* 16(1), 99–117. https://doi.org/10.1016/0304-405X(86)90044-9
- [HKS10] Heston, Korajczyk, Sadka (2010), "Intraday Patterns in the Cross-section of Stock Returns", *Journal of Finance* 65(4), 1369–1407. https://doi.org/10.1111/j.1540-6261.2010.01573.x
- [JS18] Jones, Shemesh (2018), "Option Mispricing around Nontrading Periods", *Journal of Finance* 73(2), 861–900. https://doi.org/10.1111/jofi.12603
- [KC11] Kelly, Clark (2011), "Returns in trading versus non-trading hours: The difference is day and night", *Journal of Asset Management* 12(2), 132–145. https://doi.org/10.1057/jam.2011.2
- [KL14] Kaminski, Lo (2014), "When do stop-loss rules stop losses?", *Journal of Financial Markets* 18, 234–254. https://doi.org/10.1016/j.finmar.2013.07.001
- [LM88] Lo, MacKinlay (1988), "Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test", *Review of Financial Studies* 1(1), 41–66. https://doi.org/10.1093/rfs/1.1.41
- [LPS19] Lou, Polk, Skouras (2019), "A tug of war: Overnight versus intraday expected returns", *Journal of Financial Economics* 134(1), 192–213. https://doi.org/10.1016/j.jfineco.2019.03.011 (open copy: https://personal.lse.ac.uk/polk/research/TugOfWar.pdf)
- [LSU22] Li, Sakkas, Urquhart, "Intraday Time Series Momentum: Global Evidence and Links to Market Characteristics" (SSRN version; the published version was not checked). https://doi.org/10.2139/ssrn.3460965
- [MLL00] Mok, Lam, Li (2000), "Using Daily High/Low Time to Test for Intraday Random Walk in Two Index Futures Markets", *Review of Quantitative Finance and Accounting* 14(4), 381–397. https://doi.org/10.1023/A:1008323926951
- [MN20] Muravyev, Ni (2020), "Why do option returns change sign from day to night?", *Journal of Financial Economics* 136(1), 219–238. https://doi.org/10.1016/j.jfineco.2018.12.006
- [Shreve] Shreve (2004), *Stochastic Calculus for Finance II: Continuous-Time Models*, Springer, §3.7 (the reflection principle); summary at https://en.wikipedia.org/wiki/Reflection_principle_(Wiener_process)
- [Shum16] Shum, Hejazi, Haryanto, Rodier (2016), "Intraday Share Price Volatility and Leveraged ETF Rebalancing", *Review of Finance* 20(6), 2379–2409. https://doi.org/10.1093/rof/rfv061
- [WMO85] Wood, McInish, Ord (1985), "An Investigation of Transactions Data for NYSE Stocks", *Journal of Finance* 40(3), 723–739. https://doi.org/10.1111/j.1540-6261.1985.tb04996.x
- [ZA23] Zarattini, Aziz (2023), "Can Day Trading Really Be Profitable?", SSRN 4416622. https://papers.ssrn.com/abstract=4416622 (replication note [sec]: https://www.mql5.com/en/blogs/post/776235)
- [ZAB24] Zarattini, Aziz, Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", Swiss Finance Institute working paper 24-97. https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy
- [HLL13] Holmberg, Lönnbark, Lundström (2013), "Assessing the profitability of intraday opening range breakout strategies", *Finance Research Letters* 10(1), 27–33. https://doi.org/10.1016/j.frl.2012.09.001
- [PSGW20] Plastun, Sibande, Gupta, Wohar (2020), "Price gap anomaly in the US stock market: The whole story", *North American Journal of Economics and Finance* 52, 101177. https://doi.org/10.1016/j.najef.2020.101177

**Technical analysis and levels**
- [BHJ12] Bhattacharya, Holden, Jacobsen (2012), "Penny Wise, Dollar Foolish: Buy–Sell Imbalances On and Around Round Numbers", *Management Science* 58(2), 413–431. https://doi.org/10.1287/mnsc.1110.1364
- [BLL92] Brock, Lakonishok, LeBaron (1992), "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance* 47(5), 1731–1764. https://doi.org/10.1111/j.1540-6261.1992.tb04681.x
- [BS12] Bajgrowicz, Scaillet (2012), "Technical trading revisited: False discoveries, persistence tests, and transaction costs", *Journal of Financial Economics* 106(3), 473–491. https://doi.org/10.1016/j.jfineco.2012.06.001
- [DK93] Donaldson, Kim (1993), "Price Barriers in the Dow Jones Industrial Average", *Journal of Financial and Quantitative Analysis* 28(3), 313–330. https://doi.org/10.2307/2331416
- [GH04] George, Hwang (2004), "The 52-Week High and Momentum Investing", *Journal of Finance* 59(5), 2145–2176. https://doi.org/10.1111/j.1540-6261.2004.00695.x
- [LMW00] Lo, Mamaysky, Wang (2000), "Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation", *Journal of Finance* 55(4), 1705–1765; NBER w7613. https://www.nber.org/papers/w7613
- [Osler00] Osler (2000), "Support for Resistance: Technical Analysis and Intraday Exchange Rates", FRBNY *Economic Policy Review* 6(2), 53–68. https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf
- [Osler03] Osler (2003), "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *Journal of Finance* 58(5), 1791–1819. https://doi.org/10.1111/1540-6261.00588
- [PI07] Park, Irwin (2007), "What Do We Know About the Profitability of Technical Analysis?", *Journal of Economic Surveys* 21(4), 786–826. https://doi.org/10.1111/j.1467-6419.2007.00519.x (2004 report with the 58-of-92 count: https://ageconsearch.umn.edu/record/37487/files/AgMAS04_04.pdf)
- [STW99] Sullivan, Timmermann, White (1999), "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance* 54(5), 1647–1691. https://doi.org/10.1111/0022-1082.00163 (1987–1996 figure via secondary summaries [sec])

**Options, dealers, pinning**
- [BB21] Barbon, Buraschi (2021), "Gamma Fragility", working paper. http://www.abarbon.com/assets/Barbon_Buraschi_2021_Gamma_Fragility.pdf
- [DEV] Dim, Eraker, Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation" (abstract via an Oxford seminar page). https://www.maths.ox.ac.uk/node/67396
- [GJ12] Golez, Jackwerth (2012), "Pinning in the S&P 500 futures", *Journal of Financial Economics* 106(3), 566–585. https://doi.org/10.1016/j.jfineco.2012.06.010
- [NPP05] Ni, Pearson, Poteshman (2005), "Stock price clustering on option expiration dates", *Journal of Financial Economics* 78(1), 49–87. https://doi.org/10.1016/j.jfineco.2004.08.005
- [NPPW21] Ni, Pearson, Poteshman, White (2021), "Does Option Trading Have a Pervasive Impact on Underlying Stock Prices?", *Review of Financial Studies* 34(4), 1952–1986. https://ideas.repec.org/a/oup/rfinst/v34y2021i4p1952-1986..html
- [PP] Pan, Poteshman (2006), "The Information in Option Volume for Future Stock Prices", *Review of Financial Studies*; NBER w10925. https://nber.org/system/files/working_papers/w10925/w10925.pdf
- [FlashAlpha] FlashAlpha (practitioner): "GEX, DEX, VEX, CHEX: 8-year backtest" https://flashalpha.com/articles/gex-dex-vex-chex-8-year-backtest-spy-vix-control ; "Are 0DTE straddles overpriced? 193 SPY sessions" https://flashalpha.com/articles/are-0dte-straddles-overpriced-193-spy-sessions-data-study
- [Vilkov] Vilkov, 0DTE trading-rules repository and its cost-scaling correction (KNOWN-ISSUES). https://raw.githubusercontent.com/vilkovgr/0dte-strategies/main/KNOWN-ISSUES.md
- [Elms/Harbourfront] "From pinning to amplification" (summary of a working paper on SPY 2016–2025). https://harbourfrontquant.substack.com/p/from-pinning-to-amplification-evidence

**Calendar, cross-section, volume, lead–lag**
- [Ariel87] Ariel (1987), "A monthly effect in stock returns", *Journal of Financial Economics* 18(1), 161–174. https://doi.org/10.1016/0304-405X(87)90066-3
- [Ariel90] Ariel (1990), "High Stock Returns before Holidays: Existence and Evidence on Possible Causes", *Journal of Finance* 45(5), 1611–1626. https://doi.org/10.1111/j.1540-6261.1990.tb03731.x
- [ACG06] Avramov, Chordia, Goyal (2006), "Liquidity and Autocorrelations in Individual Stock Returns", *Journal of Finance* 61(5), 2365–2394. https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html
- [BT89] Bernard, Thomas (1989), "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?", *Journal of Accounting Research* 27, 1–36. https://doi.org/10.2307/2491062
- [CGW93] Campbell, Grossman, Wang (1993), "Trading Volume and Serial Correlation in Stock Returns", *Quarterly Journal of Economics* 108(4), 905–939. https://doi.org/10.2307/2118454
- [CS00] Chordia, Swaminathan (2000), "Trading Volume and Cross-Autocorrelations in Stock Returns", *Journal of Finance* 55(2), 913–935. https://doi.org/10.1111/0022-1082.00231
- [French80] French (1980), "Stock returns and the weekend effect", *Journal of Financial Economics* 8(1), 55–69. https://doi.org/10.1016/0304-405X(80)90021-5
- [GKM01] Gervais, Kaniel, Mingelgrin (2001), "The High-Volume Return Premium", *Journal of Finance* 56(3), 877–919. https://doi.org/10.1111/0022-1082.00349
- [Hasb03] Hasbrouck (2003), "Intraday Price Formation in U.S. Equity Index Markets", *Journal of Finance* 58(6), 2375–2400. https://doi.org/10.1046/j.1540-6261.2003.00609.x
- [HLWZ20] Huang, Li, Wang, Zhou (2020), "Time series momentum: Is it there?", *Journal of Financial Economics* 135(3), 774–794. https://doi.org/10.1016/j.jfineco.2019.08.004
- [Hou07] Hou (2007), "Industry Information Diffusion and the Lead-lag Effect in Stock Returns", *Review of Financial Studies* 20(4), 1113–1138. https://doi.org/10.1093/revfin/hhm003
- [Jeg90] Jegadeesh (1990), "Evidence of Predictable Behavior of Security Returns", *Journal of Finance* 45(3), 881–898. https://doi.org/10.1111/j.1540-6261.1990.tb05110.x
- [JT93] Jegadeesh, Titman (1993), "Returns to Buying Winners and Selling Losers", *Journal of Finance* 48(1), 65–91. https://doi.org/10.1111/j.1540-6261.1993.tb04702.x
- [Karpoff87] Karpoff (1987), "The Relation Between Price Changes and Trading Volume: A Survey", *Journal of Financial and Quantitative Analysis* 22(1), 109–126. https://doi.org/10.2307/2330874
- [KTW16] Kim, Tse, Wald (2016), "Time series momentum and volatility scaling", *Journal of Financial Markets* 30, 103–124. https://doi.org/10.1016/j.finmar.2016.05.003
- [KWG21] Kurov, Wolfe, Gilbert (2021), "The disappearing pre-FOMC announcement drift", *Finance Research Letters* 40, 101781. https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html
- [LM15] Lucca, Moench (2015), "The Pre-FOMC Announcement Drift", *Journal of Finance* 70(1), 329–371. https://doi.org/10.1111/jofi.12196
- [LM90] Lo, MacKinlay (1990), "When Are Contrarian Profits Due to Stock Market Overreaction?", *Review of Financial Studies* 3(2), 175–205; NBER w2977. https://www.nber.org/papers/w2977
- [LS88] Lakonishok, Smidt (1988), "Are Seasonal Anomalies Real? A Ninety-Year Perspective", *Review of Financial Studies* 1(4), 403–425. https://doi.org/10.1093/rfs/1.4.403
- [MOP12] Moskowitz, Ooi, Pedersen (2012), "Time series momentum", *Journal of Financial Economics* 104(2), 228–250. https://doi.org/10.1016/j.jfineco.2011.11.003
- [MX08] McConnell, Xu (2008), "Equity Returns at the Turn of the Month", *Financial Analysts Journal* 64(2), 49–64. https://doi.org/10.2469/faj.v64.n2.11
- [Nagel12] Nagel (2012), "Evaporating Liquidity", *Review of Financial Studies* 25(7), 2005–2039. https://doi.org/10.1093/rfs/hhs066
- [Schwert03] Schwert (2003), "Anomalies and Market Efficiency", *Handbook of the Economics of Finance* 1, ch. 15, 939–974; NBER w9277. https://www.nber.org/papers/w9277
- [SS13] Stivers, Sun (2013), "Returns and option activity over the option-expiration week for S&P 100 stocks", *Journal of Banking & Finance* 37(11), 4226–4240. https://doi.org/10.1016/j.jbankfin.2013.07.030
- [SW13] Savor, Wilson (2013), "How Much Do Investors Care About Macroeconomic Risk? Evidence from Scheduled Economic Announcements", *Journal of Financial and Quantitative Analysis* 48(2), 343–375. https://ideas.repec.org/a/cup/jfinqa/v48y2013i02p343-375_00.html
- [SW90] Stoll, Whaley (1990), "The Dynamics of Stock Index and Stock Index Futures Returns", *Journal of Financial and Quantitative Analysis* 25(4), 441–468. https://doi.org/10.2307/2331010

**Method**
- [Berk01] Berkowitz (2001), "Testing Density Forecasts, With Applications to Risk Management", *Journal of Business & Economic Statistics* 19(4), 465–474. https://doi.org/10.1198/07350010152596718
