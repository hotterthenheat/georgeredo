# Lifecycle research — 2. Protocol (pre-registered 2026-10-15, before any lifecycle result was computed)

This protocol fixes, before results are seen:
- the splits;
- the setups, structures, entry rules and management policies;
- the metrics;
- the rules that promote a candidate.

Every change after the first result is an amendment (L-A1, L-A2, …) at the foot of this file. Each amendment is dated and gives its reason, and no amendment is retroactive.

Prior work it builds on: `../04_protocol.md`, studies S01–S17 in `../05_results.md`. None of those directional configurations passed. This program tests whether **entry timing, structure choice or position management** change that, and measures what each management action contributes.

## 1. Data and splits

### Tier I: intraday, 1-minute NBBO, complete 0DTE chains

| Root | Sessions |
|---|---|
| SPY | 2022-11-11 → 2026-10-09 |
| QQQ | 2022-11-11 → 2026-10-09 |
| SPXW | 2022-05-13 → 2026-10-09; signals on SPX with SPY volume |
| IWM | 2024-04-19 → 2026-10-09 |

The weekly sample (S03 sessions) is a secondary check for the Weekly bucket.

### Chronological splits (no random splits)

| Split | Sessions | Use |
|---|---|---|
| Development | ≤ 2024-12-31 | rules, grids, model choice |
| Validation | 2025-01-02 → 2025-09-30 | selection between finalists, sensitivity |
| **Hold-out** | **2025-10-01 → 2026-10-09** | untouched; evaluated once per frozen configuration version, finalists only |

**Walk-forward** inside development and validation:
- expanding window, refit each calendar quarter from 2024-Q1;
- a five-session embargo between fit and test;
- the selection rule is the one in §6.

Its stitched out-of-sample series (2024-01 → 2025-09) is reported for every family, so selection bias is visible before the hold-out is opened.

### Tier D: daily lifecycles (option EOD, closing NBBO)

- SPY, QQQ, IWM from 2012-06 and 40 Tier A names from 2017-06.
- Splits by calendar year: development ≤ 2021, validation 2022–2023, hold-out 2024-01 → 2026-10.
- Walk-forward is yearly.

## 2. Execution model (same for every policy)

**Timing**
- A decision is made at the close of a 1-minute bar stamped t, the instant t+1.
- A market order fills at the NBBO stamped t+1+L. L, the latency, is 0 by default; 1 and 3 minutes are sensitivity runs.

**Prices**
- Buy at the ask, sell at the bid.
- A multi-leg order fills every leg in the same minute at its own bid or ask. No package mid is assumed.

**Limit orders**
- A limit fills only when the NBBO **trades through** it: a buy limit L fills at L in a minute whose ask ≤ L − $0.01; a sell limit fills when the bid ≥ L + $0.01.
- "Fill on touch" (ask ≤ L) is a sensitivity run, never the headline.
- An unfilled limit is cancelled at its expiry and recorded as a missed entry.

**Size and fees**
- Size: an order fills at most the displayed size of each leg at the fill minute. The rest is a partial fill that waits one more minute and is then cancelled. Research runs use 1 unit, so this binds only in the portfolio simulation.
- Fees: $0.70 per contract per side, on exercise and assignment too.
- Slippage sensitivity: +$0.01 and +$0.02 per contract per side beyond the NBBO.

**Missing data**
- No quote at the fill minute → the next minute with a two-sided quote, at most 2 minutes later, else no fill.
- Marks between fills use the mid of the last two-sided quote. A stale quote older than 5 minutes is never used for a fill.

**Expiry**
- Cash-settled (SPXW, PM): intrinsic value at the 16:00 index value.
- Physically settled ETF and stock options: in-the-money by ≥ $0.01 at the 16:00 underlying close is exercised or assigned at intrinsic, plus the share position for a cash-secured put.
- Assigned shares are sold at the next session's 09:31 bar open unless a policy holds them.
- After-hours moves after 16:00 are not modelled (stated limit).

**Carry**
- r = 0.04 (stated), q = 0, for IV and Greeks solved from the mid.
- A parity-implied rate is a sensitivity run.

## 3. Setups (intraday definitions; index products only for Quick Scalps)

Every setup emits events (session, minute, direction, invalidation level, optional target). Definitions reuse `../engine/signals.py` and `screen.py` where they exist.

| Code | Category | Event |
|---|---|---|
| QS | Quick Scalps | the S01 baseline rule (RSI 14 cross 55/45 beyond EMA 9, 5m confirmation, 15m alignment, relative volume ≥ 1, structure), 09:45–14:50 |
| TP | Trend Plays | `family_events('trend_plays')` |
| BO | Breakouts | `family_events('breakouts')` |
| BOF | Breakouts (failed) | a 5m close beyond the prior session's high/low or the 20-bar range, then a 5m close back inside within 3 bars → the opposite direction; invalidation the extreme of the failed break |
| BN | Bounces | `family_events('bounces')` |
| BNF | Bounces (failed reversal) | a BN event whose 5m close crosses its invalidation level within 6 bars → the original move's direction |
| LS | ICT liquidity sweep | the 1m high (low) takes out the prior session's high (low) or the 09:30–10:00 range by ≥ 0.03 %, then a 5m close back inside within 3 bars → back-inside direction; invalidation the sweep extreme |
| MSS | ICT market-structure shift | within 30 minutes after an LS, a 5m close beyond the most recent confirmed 5m swing (3/3) in the LS direction |
| FVG | ICT fair-value-gap retracement | a displacement 5m bar (range ≥ 1.5 × ATR(14) on 5m) leaving a three-bar gap; entry when a 1m bar trades back into the gap within 60 minutes; invalidation a 1m close beyond the gap's far side |
| VOLC | Volatility, cheap | 10:00 ATM 0DTE IV at or below the 20th percentile of its prior 60 sessions **or** below 0.8 × a HAR forecast of the rest-of-day realized vol (fit on past days only) → long straddle or strangle |
| VOLR | Volatility, rich | the mirror (≥ 80th percentile, or > 1.25 × the forecast) → the premium-collecting structures in §4 only |
| EVF | Events, Fed | FOMC statement days; 13:30 entry, structures in §4; non-FOMC days at 13:30 as the control. Dates from the Federal Reserve's published calendar, kept in `data/fomc_dates.csv` with the source URL |
| CHP | Cheap Options | any directional event above whose chosen Big Payoff contract has mid-IV < 0.8 × the HAR forecast |
| FLO | Flow & Positioning | daily dealer-gamma sign from UW (2025-10-15 → 2026-10-13, on disk) as a regime filter on the events above. Unusual activity needs the option tape and is untested until pulled (§9). Dark pool is untested. |
| TPp, BOp, BOr, BNp, VWR | trigger-only variants | the S06 screen's triggers without the baseline RSI gate (`../engine/screen.py`): trend pullback, 5m breakout, breakout retest, bounce, VWAP reclaim. Invalidation is the last confirmed 5m swing against the trade. Added before any result because the gated families are rare (BN gave 0 events on SPY in 2024-H1). |
| RND | control | random minutes matched by session, direction and entry window (5 seeds), the same structures and policies |

**Top Setups** is a ranking over the union of events:
- the score is a setup × structure cell's walk-forward expectancy estimate from data before the event;
- an opportunity is the (root, session, direction, 15-minute bucket) key, deduplicated across categories, with the categories kept as tags;
- the test is ranked-top-k against all eligible.

**All Setups** is the deduplicated union.

## 4. Structures (chosen at the fill minute from the snapshot; IV and delta from the mid)

| Code | Legs |
|---|---|
| LC-S / LP-S | Steady: |Δ| ≥ 0.50, nearest 0.55 |
| LC-B / LP-B | Big Payoff: |Δ| 0.10–0.35, nearest 0.20 |
| DCS / DPS | debit spread: long |Δ| nearest 0.50, short |Δ| nearest 0.25, same expiration, short strike further OTM |
| CPS | credit put spread: short put |Δ| nearest 0.20 (0.15–0.30), long put the next listed strike at least $1 (index ETFs) or 5 points (SPXW) lower |
| CSP | cash-secured put: short put |Δ| nearest 0.30; collateral strike × 100; assignment per §2 |
| STR | long straddle: call and put at the strike nearest spot |
| STG | long strangle: call and put |Δ| nearest 0.25 |

A structure is skipped when any leg has no two-sided quote, a long leg's ask < $0.05, or a leg's relative spread > 20 %. Skips are counted as a reason.

Allowed setup × structure pairs:
- directional setups → LC/LP-S, LC/LP-B, DCS/DPS;
- bullish directional setups also → CPS and CSP, since a structure follows its setup's direction (the Compass rule);
- VOLC and EVF → STR, STG;
- VOLR → CPS, CSP only (no short straddles or strangles: undefined risk, out of scope).

## 5. Entry rules and management policies

**Entry rules**

| Rule | Behaviour |
|---|---|
| E0 | market at the signal |
| E1 | latency 1 / 3 minutes |
| E2 | wait for the next 5m close in the direction, cancel after 15 minutes |
| E3 | pullback limit at mid − ¼ spread or at the mid implied by a 0.25 × ATR retrace (delta-mapped), good for 10 minutes |
| E4 | chase guard: skip if the fill ask > 1.10 × the signal-time mid |
| E5 | spread guard: skip if the structure's relative spread > 10 % |
| E6 | entry window: 09:45–11:00, 11:00–14:00, 14:00–15:30 |
| E7 | regime: VIX tercile at entry (prior-session VIX), IV percentile, the open-to-now move |

**Management families**

| Family | Parameters |
|---|---|
| M0 do nothing | hold to the 15:50 cutoff or to expiry |
| M1 time exit | 15, 30, 60, 120 minutes |
| M2 stop / target | stop −20 / −35 / −50 % / none × target +20 / +50 / +100 % / none |
| M3 partials and runner | sell 25 % or 50 % at +20 % or +50 %, a second 25 % at +50 % or +100 %; the runner trails 20 % or 35 % from its peak, or exits on a 5m close beyond EMA 20 against it, or at time |
| M4 trail only | arm at +20 % or +50 %, give back 15 / 25 / 40 % of the peak |
| M5 thesis | a 1m or 5m close beyond the setup's invalidation level → exit, or reduce 50 % |
| M6 add on confirmation | +1 unit when the underlying moves k = 1 or 2 ATR(14, 5m) in favour while the position is green; at most 1 or 2 adds. ATR(5m) rather than ATR(1m): one 1-minute ATR on SPY is a few cents, which is noise. Fixed before any result was computed. |
| M7 double down | add units equal to those held when the value is −25 % or −40 % and the thesis stands; at most 1 |
| M8 scale in | ⅓ at the signal, ⅓ at +5 minutes if not invalidated, ⅓ on the next 5m close in the direction, against 100 % at once |
| M9 reduce on warning | W1 RSI(14, 1m) back through 50; W2 ATM IV down ≥ 10 % relative since entry; W3 structure spread ≥ 2 × the entry spread; W4 adverse excursion ≥ 1 ATR(5m). Action: reduce 50 % or exit. Each warning is scored against holding. |
| M10 re-entry | after a losing exit, the next qualifying event in the session is taken / skipped / taken after a 15-minute cool-down |
| M11 reverse | an opposite event while a position is open: close and reverse / close only / ignore |
| M12 straddle and strangle legs | close both at +25 / +50 % of debit; close the losing leg when the underlying has moved ±k × the expected move (k = 0.5, 1) and trail the winner 25 %; time exit |
| M13 short premium | take profit at 25 / 50 / 75 % of credit; stop at 1.5 × / 2 × / 3 × credit or when the short strike is touched; hold to expiry |

**Accounting**
- Units added later are separate lots. Exits are allocated to lots pro rata, so the P&L of the original lot, each add and each double-down is reported separately.
- Exits are tagged by reason, which gives each partial's and the runner's contribution.

## 6. Selection, promotion and multiple testing

**Objective inside development:** the day-clustered bootstrap lower bound (95 %) of net expectancy per trade, with at least 150 trades in the fit window. Ties go to fewer parameters.

**Walk-forward:** every family re-selects its parameters each quarter by the objective. The stitched out-of-sample result is the family's development evidence.

**Finalists:** at most **10** configurations go to the hold-out, chosen on validation (walk-forward OOS plus the validation split). Each must be:
- positive with a positive lower bound on the walk-forward OOS series;
- not worse than M0 on the same events by a paired test.

**Promotion** (hold-out, each of):
1. net expectancy per trade > 0 with a day-clustered 95 % lower bound > 0, Holm-adjusted across the finalists actually evaluated;
2. directional setups: paired lower bound against RND with the same structure and policy > 0;
3. profit factor > 1.0;
4. ≥ 100 trades on ≥ 60 sessions;
5. still positive at +$0.01 per contract per side and with L = 1 minute;
6. a parameter plateau: on development, the median of the configuration's grid neighbours is > 0.

A configuration that fails is reported in the failed-hypothesis report with its numbers, never dropped.

**The count of every configuration evaluated** is kept in `registry.jsonl` and in each report's header.

## 7. Three results, never combined

- **A, hindsight.** For every eligible entry (archive grid and actual events):
  - the best bid reachable after an ask entry (and the mid-to-mid equivalent);
  - MAE;
  - the times to MFE and MAE;
  - the share of the hindsight MFE a rule captured.

  Labelled retrospective in every table.
- **B, executable simulation.** The rule on development + validation with §2 execution, every cost and constraint.
- **C, validated.** Walk-forward OOS (2024-01 → 2025-09) and the hold-out, reported separately. Live or paper results, if any appear later, are a fourth table.

## 8. Metrics (every table, where the data allows)

- **Counts:** trades and independent days.
- **Returns:**
  - win rate, average winner and loser;
  - average and median $ and % return;
  - gross and net expectancy;
  - profit factor;
  - the return distribution (deciles, the worst 1 % and 5 %, the largest loss).
- **Excursions:** MFE, MAE and the times to each.
- **Risk:** max drawdown (portfolio); capital and buying power; return on capital against return on risk, kept separate.
- **Time:** holding time.
- **Contributions:** partials, runner, adds and double-downs.
- **Breakdowns:** by root, structure, bucket, time of day, VIX tercile and IV regime.
- **Sensitivity:** spread, slippage and latency.
- **Uncertainty:** day-clustered bootstrap intervals throughout.

## 9. Not testable here (reported, not guessed)

- Dark-pool prints: not on disk.
- Unusual options activity on 0DTE chains: needs per-chain trade or OHLC pulls (about 4,000 requests). The plan is a Tier I volume pull after the Tier D pull; until then FLO is the dealer-gamma regime only.
- Single-name intraday lifecycles: Tier E pulls per hypothesis.
- Ticks: fills use 1-minute NBBO; a sample of fills is audited on ticks if a finalist emerges.

## Amendments

**L-A1 (2026-10-15, before any FLO, hold-out or entry-rule result was computed).**

1. *Flow & Positioning is a hold-out-only test.* UW's daily dealer greek-exposure on disk covers 2025-10-15 → 2026-10-13 for SPY, QQQ, IWM and SPX, which is exactly the hold-out. No development is possible, so the test is fixed here and run once.
   - The signal for session D is the sign of the prior session's net gamma (call_gamma + put_gamma, UW's sign) on the root (SPX's for SPXW). That value was published after the prior close, so it is knowable at D's open.
   - **H-FLO-1:** directional Steady longs (LC-S and LP-S, all directional setups pooled, M1_t30) have a higher expectancy on negative-gamma days than on positive-gamma days.
   - **H-FLO-2:** the 10:00 long straddle (ALL10V, STR, M0_cutoff) has a higher expectancy on negative-gamma days.
   - Each is one difference with a day-clustered 95 % interval, Holm across the two.
   - Either way it is a regime statement over one year, never a validated edge on its own.
2. *Entry-rule mechanics (§5), as implemented before running them:*
   - **E2** chooses the structure at the confirmation minute; **E2g** also applies the chase guard against the signal-minute mark.
   - **E3** is a package limit at mark − ½ × (open cost − mark) per share, which is mid − ¼ spread on one leg.
   - **E3atr** is a limit at mark − |net delta| × 0.25 × ATR(5m).
   - Both limits are good for 10 minutes and fill only when the package's open cost is at or below the limit − $0.01, paying the limit.
   - Entry rules run on real events only. Each is compared with E0 on the same events (paired), so no random controls are needed.
3. *Cutoff and expiry.* The protocol's M0 is two policies: hold to the 15:50 cutoff, and hold to expiry. For physically settled ETF options, holding to expiry means exercise or assignment at the 16:00 close and the shares sold at the next 09:30 open, so overnight gap risk is included. Both are reported side by side; the cutoff is the conservative one.

**L-A2 (2026-10-15, after the hold-out was opened for the finalists; before any result of the controls below was computed).**

1. *The RND control has a look-ahead.*
   - RND draws a minute uniformly from the whole entry window, but it takes the direction the setup decided at the event minute.
   - A control that falls before the event therefore enters in a direction chosen with knowledge of the move that produced the event.
   - The bias favours the controls of momentum setups (breakouts, QS): they enter long before the rise that triggered a long. This makes those setups look worse than random.
   - It penalises the controls of reversal setups (bounces): they enter long before the decline that preceded the bounce. This makes those setups look better than random.
   - The stage-1 "vs RND" figures and promotion rule R2 were computed with this control.
2. *Two controls replace it for the setup comparisons*, each computed on development and validation:
   - **RND-after:** a minute drawn uniformly from [event minute, end of the window], same session, same direction, 5 seeds. It uses only what the event knew.
   - **FLIP:** the event's own minute, the opposite direction, the mirrored structure (LC-S ↔ LP-S, LC-B ↔ LP-B, DCS ↔ DPS). It tests whether the setup chose the right side at that minute. CPS and CSP have no mirror.
   - Both are reported beside the original RND, never in place of it.
3. *R2 on the hold-out is re-scored against RND-after for the six finalists.*
   - This is labelled post hoc: the hold-out results were already seen when the flaw was found.
   - It cannot promote a configuration. A finalist that passes every rule under RND-after is reported as "passes only under a control chosen after the hold-out was opened" and needs a fresh hold-out (sessions after 2026-10-09) to be promoted.

**L-A3 (2026-10-15, before any hold-out row of this cell was read).**
- One long-premium cell held a lower bound above zero on development + validation: QS → debit call spread held to expiry (M0_expiry), +50.3 [+10.6, +93.7] on 2,749 trades.
  - It was not a finalist: its walk-forward lower bound was −19.6, because the early quarters chose other policies.
- It was chosen by looking at development + validation, so it is tested once on the untouched hold-out (2025-10-01 → 2026-10-09) as a single confirmatory test:
  - **H-DCS-1:** its hold-out expectancy > 0, one-sided bootstrap p < 0.05;
  - **H-DCS-2:** it beats RND-after (a random later minute, same direction, same structure and policy), paired, one-sided p < 0.05.
- Holm across the two. Passing both makes it a candidate for the fresh hold-out (sessions after 2026-10-09), not a promoted configuration: the cell was selected from about 1,000 stage-1 cells.

**L-A4 (2026-10-15, before the daily tier's full development + validation results; only a SPY preview of development + validation had been read, and no hold-out row).** The daily tier's finalists and its one hold-out evaluation, applied mechanically.

1. **Cells:** group (index ETFs; single names) × setup × bucket (W, S, P, L, X) × structure.
   - Setups: D_TP, D_BO, D_BOF, D_BN, D_BNF, D_EARN, D_FOMC.
   - The all-days rows (D_ALLL, D_ALLS, D_ALLV, D_ALLP, D_ALLF) are baselines. They are reported, never finalists.
2. **Finalist:**
   - the yearly walk-forward (2018–2023, a policy chosen per cell on all earlier years) has out-of-sample expectancy > 0 with lower bound > 0, on at least 100 trades and 60 sessions;
   - its frozen policy is the best lower bound on development + validation with at least 100 trades.
3. **Hold-out (2024-01-01 → 2026-10-09), opened once for the finalists.** Promotion needs all of:
   - **R1** expectancy > 0, one-sided bootstrap p below its Holm threshold across the finalists;
   - **R2** beats the random-day control in the same direction (controls on hold-out sessions only), paired lower bound > 0;
   - **R2b** beats the same bucket, structure and policy on the all-days baseline (D_ALLL for bullish, D_ALLS for bearish, D_ALLV for straddles) over the hold-out, lower bound > 0. This separates timing from the market's drift.
   - **R3** profit factor > 1;
   - **R4** at least 100 trades on 60 sessions;
   - **R5** still > 0 with $0.05 a contract a side of extra slippage;
   - **R6** the same family's policies have a positive median on the cell in development.
4. **Bookkeeping:** the hold-out is opened by `scripts/holdout_tier_d.py`, which writes a lock file and refuses a second run. The daily tier's controls are clean (random sessions from the whole sample, not tied to the event's own move).

**L-A4.1 (2026-10-15, before any daily-tier hold-out row was read).**
- The daily tier's hold-out is opened once *per group*:
  - **index ETFs** (SPY, QQQ, IWM), as soon as their runs finish;
  - **single names**, once their pull finishes, on the names complete by then (listed in `06_daily_tier.md`).
- Each group's finalists are chosen from that group's development + validation results alone, by the L-A4 rule.
- Holm runs within each group.
- `scripts/holdout_tier_d.py <group>` keeps one lock per group.
