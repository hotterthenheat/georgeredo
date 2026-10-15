# Lifecycle research — 6. The daily tier: Weekly, Swing, Position, Long-Dated, LEAPS; single names; earnings

**Scope**
- Compass's expiration buckets beyond same-day, at daily resolution.
- Every position is opened at a session's closing NBBO and managed session by session on the vendor's end-of-day NBBO, through the same position engine as Tier I (`lc/position.py`).

**Splits:** development ≤ 2021, validation 2022–2023, hold-out 2024-01-01 → 2026-10-09 (`02_protocol.md`, L-A4 and L-A4.1).

## 1. Data

| Root | Option EOD, every expiration | Rows | Sessions with entries | Positions (development + validation) |
|---|---|---|---|---|
| SPY | 2012-06 → 2026-10 (750 weeks) | 14.5 M | 6,843 events | 134,148 |
| QQQ | 2012-06 → 2026-10 (750 weeks) | 17.1 M | 7,299 | 145,699 |
| IWM | 2012-06 → 2026-10 (750 weeks) | 13.2 M | 7,101 | 135,388 |
| FB | 2017-06 → 2022-06 (263 weeks; the ticker became META) | 2.3 M | 2,182 | 36,513 |
| 40 single names | 2017-06 → 2026-10 | pull in progress | — | §8 |

**Pulled with** `scripts/pull_tier_d.py`, one week of every expiration a request, resumable (`jobs.jsonl`). Repartitioned per expiration month (`lc/daily.py`).

**Underlying closes**
- From the 1-minute bars where the vendor has them.
- The 2012–2016 index-ETF bars are empty at the vendor, so those closes come from put-call parity on the root's own chain: nearest expiration ≥ 5 days, the strike where |C − P| is smallest, r = 0.25 %. Measured against real 2017 closes: median +0.6 bp, 10th–90th percentile −10.9 to +9.9 bp. Those years are close-only, so the bounce setups (which need the day's open) start in 2017.
- **The vendor's META stock history is not Meta Platforms before 2022-06-09.**
  - It is empty before 2021-07-01.
  - It is the Roundhill Ball Metaverse ETF (about $15) from then to 2022-06-08.
  - So FB's closes come from parity on FB's own chain (2019-06-03: $164.14 against the real $164.15), and the META root starts on 2022-06-09.
- Splits are detected from the closes and every indicator is split-adjusted.

**Buckets** (calendar days from the entry session to the last trading day; the listed expiration nearest the target):

| Bucket | Days | Target |
|---|---|---|
| W, Weekly | 1–7 | 5 |
| S, Swing | 8–45 | 30 |
| P, Position | 46–90 | 60 |
| L, Long-Dated | 91–269 | 180 |
| X, LEAPS-tagged | 270 or more | 365 |

**Point in time**
- An expiration is used only on a session it was quoted (`lc/daily.py` `listed_ranges`). Before this fix the picker chose weeklies a year out that did not yet exist, and silently dropped most P/L/X entries.
- A position whose expiration lies after the data's end is left out, not settled early at intrinsic value. That is about 500 a root on the hold-out, and 1,015 for FB, whose chain stops at the 2022 rename.

## 2. Setups, baselines and controls (`lc/daily_events.py`), decided at a session's close on data known by then

| Setup | Rule |
|---|---|
| D_TP trend pullback | EMA 20 > 50 > 200 (or reversed), the low touched EMA 20 within 3 sessions, close back beyond it |
| D_BO breakout | the first close beyond the prior 20-session high (low) in 5 sessions |
| D_BOF failed breakout | within 3 sessions of a D_BO, a close back inside: trade the other way |
| D_BN / D_BNF | bounce: 20-session z-score ≤ −2 (≥ +2) and a reversal day; failed bounce |
| D_EARN | the 5th session before an earnings report (single names), straddle and strangle |
| D_FOMC | the session before an FOMC statement (index ETFs), straddle and strangle |
| **Baselines** | D_ALLL / D_ALLS: every Monday, long / short. D_ALLV: every Monday, straddle. D_ALLP: every Monday, put sale. D_ALLF: non-Fed weeks. |
| **Control** | a random session from the whole sample, same direction, 5 seeds. It is not tied to the event's own move, so it has no look-ahead. |

**Policies:** 25 daily policies (`lc/daily_runner.py`): hold to expiry; sell the session before the last trading day; sell at 21 days; 5/10/20-session exits; stops and targets; partials and trails; thesis; add on +1 ATR; double down at −40 %; RSI exit; straddle-leg rules; credit take-profit and stops; earnings pre/post.

## 3. The baselines: what the period paid for simply holding (index ETFs, development + validation, held to expiry)

Dollars per contract, every Monday 2013–2023 (about 1,680 entries per cell):

| Bucket | Steady call | Big Payoff call | Debit call spread | Cash-secured put | Steady put | Debit put spread | Straddle |
|---|---|---|---|---|---|---|---|
| W | +16 [−10, +42] | +7 | +4 | +5 | −12 | −3 | +8 |
| S | **+91** [+40, +146] | +19 | +47 | +84 | −144 | −54 | −30 |
| P | **+126** [+49, +207] | +36 | +53 | +149 | −268 | −121 | −100 |
| L | **+526** [+398, +659] | +180 | +234 | +428 | −713 | −262 | +5 |
| X | **+1,326** [+1,112, +1,542] | +589 | +454 | +749 | −1,443 | −600 | +495 |

**This table is the bar every setup must clear.**
- 2013–2023 was a strong bull market for SPY, QQQ and IWM. Any long-dated bullish structure bought on any Monday made money, and any bearish one lost.
- A setup's raw profit in these buckets says nothing until it is compared with this table and with random days.

**Result A (hindsight)** (`results/tier_d/result_A.csv`):
- On index-ETF Steady calls, the average best exit before expiry was +47 % (W) to +188 % (X) of premium.
- 42–76 % of entries touched +50 %.
- Holding to expiry returned +7 % (W) to +103 % (X).
- Steady puts touched +50 % in 35–44 % of entries, but returned −7 % to −58 % when held.

## 4. Do the setups beat the baselines? (development + validation)

**Each setup cell is compared two ways** (same bucket, structure and policy; `results/tier_d/setup_vs_alldays.csv`, `real_vs_control.csv`):
- against the all-days Monday baseline;
- against random days in the same direction.

| Setup | Cells | Better than all-days | Worse | Better than random days | Worse |
|---|---|---|---|---|---|
| D_TP trend pullback | 600 | 4 | **136** | 9 | **188** |
| D_BO breakout | 600 | 36 | 51 | 65 | 41 |
| D_BOF failed breakout | 600 | 49 | 13 | 70 | 12 |
| D_BN bounce | 556 | 19 | 28 | 15 | 17 |

These counts span 25 overlapping policies per bucket and structure, so they are not independent tests. The pattern by cell, held to expiry:

- **D_TP, bearish side (pullbacks in a downtrend):**
  - much worse than shorting every Monday, e.g. Steady puts in the P bucket −588 against −268, difference −320 [−530, −59];
  - in the X bucket, −1,052 [−1,417, −654].
  - Bearish trend continuations failed through 2013–2023's V-shaped recoveries.
- **D_TP, bullish side:** within noise of buying every Monday in every bucket but X. There the setup's calls did worse than the Monday baseline (Steady −243 [−484, +11]; debit spread −132 [−227, −20]).
- **D_BOF (failed breakout):**
  - point estimates mostly above both baselines, intervals mostly spanning zero;
  - cleared both in the Swing bucket's put sales: cash-secured put +135 [+60, +215] against all-days and +152 [+72, +234] against random days; credit put spread +13 [+3, +21] and +17 [+5, +27];
  - only about 100 trades a cell.
- **D_FOMC:**
  - straddles held to expiry did worse than in non-Fed weeks in the S/P/L buckets (S: −438 [−779, −86]);
  - held 5 sessions, through the announcement, no difference (S: +3 [−107, +118]).
  - The Fed event itself showed no edge either way. The long-hold gap is noise over the weeks after, on 24 Fed days.
- **D_BN / D_BNF:** too rare to estimate (insufficient in every cell, `09_setup_strategy_matrix.md`).

## 5. Management at daily resolution (index ETFs, each policy against holding to expiry)

**Mean difference across buckets; how many of the five buckets were better or worse with a lower/upper bound beyond zero** (`results/tier_d/policy_vs_expiry.csv`):

| Structure | Best policy | vs hold [buckets better / worse] | Worst policy | vs hold [better / worse] |
|---|---|---|---|---|
| Steady call | double down at −40 % | +30 [1 / 1] | exit after 5 sessions | −404 [0 / 4] |
| Big Payoff call | double down at −40 % | +41 [2 / 0] | exit after 5 sessions | −156 [0 / 3] |
| Debit call spread | double down at −40 % | −13 [1 / 4] | exit after 5 sessions | −176 [0 / 5] |
| Cash-secured put | close at 21 days | +9 [2 / 2] | exit after 5 sessions | −272 [0 / 4] |
| Credit put spread | hold to expiry | 0 | exit after 5 sessions | −31 [0 / 5] |
| Steady put | exit after 5 sessions | **+479 [4 / 0]** | double down at −40 % | −180 [1 / 2] |
| Big Payoff put | exit after 5 sessions | **+216 [4 / 0]** | double down at −40 % | −119 [0 / 2] |
| Debit put spread | exit after 5 sessions | **+164 [4 / 1]** | double down at −40 % | −78 [0 / 2] |
| Straddle | take 50 % on both legs | 0 | exit after 5 sessions | −111 [0 / 1] |

**The management rule that "works" is the market's direction, not a rule:**
- **Bullish structures:** hold every bullish position to expiry and add to losers.
- **Bearish structures:** cut every bearish position after 5 sessions and never add.

No management family helped bullish and bearish structures alike. The same pattern appeared at same-day resolution (`05_management_research.md` §5) and will reverse in a falling market.

## 6. Walk-forward and the hold-out (index ETFs)

**Walk-forward**
- Yearly, 2018–2023: each cell's policy chosen on all earlier years.
- 19 of 95 setup cells had out-of-sample lower bounds above zero, and 37 had intervals below zero.
- All 19 were bullish trades (calls, call spreads, cash-secured puts) on trend pullbacks (11) and breakouts (8), 15 of them in the Long-Dated and LEAPS buckets.

**The hold-out (2024-01 → 2026-10)**
- Opened once for the 19 finalists (`results/tier_d/holdout_verdicts_index_etf.csv`, L-A4.1).
- **None promoted.**

| Rule | Passed |
|---|---|
| R1 expectancy > 0 (Holm) | 15 of 19 |
| R2 beats random days, same direction | **0 of 19** |
| R2b beats the all-days baseline | 2 of 19 |
| R3 profit factor > 1 | 15 |
| R4 ≥ 100 trades on 60 sessions | 12 |
| R5 positive at +$0.05 a side | 15 |
| R6 development family median > 0 | 19 |

| Finalist (frozen policy) | Hold-out trades | Expectancy [lower bound] | vs random days | vs all-days |
|---|---|---|---|---|
| D_BO, X, Steady call (sell before last trading day) | 72 | +3,554 [+2,578] | +1,100 [−76, …] | +769 [−275, …] |
| D_TP, X, Steady call (same) | 257 | +2,638 [+2,198] | −294 [−822, …] | −147 [−778, …] |
| D_TP, X, cash-secured put (close at 21 days) | 257 | +1,901 [+1,818] | −68 [−177, …] | +17 [−78, …] |
| D_TP, L, Steady call (double down at −40 %) | 336 | +1,180 [+672] | −1,134 [−1,827, …] | −1,132 [−1,853, …] |
| D_BO, X, cash-secured put | 71 | +2,079 [+1,922] | +155 [−50, …] | **+195 [+31, …]** |
| D_BO, W, cash-secured put | 103 | +77 [+44] | +62 [−27, …] | **+55 [+3, …]** |
| D_TP, S, Steady call (hold to expiry) | 403 | **−235** [−373] | −497 | −463 |
| D_TP, P, debit call spread | 376 | **−236** [−324] | −374 | −372 |

Full table: 19 rows in the file.

**Reading**
- 2024–2026 rose strongly, so the long-dated bullish finalists made $500–3,500 a trade.
- Buying the same structure on a random day in the same direction did as well; R2 is 0 of 19.
- The two that beat the Monday baseline (breakout cash-secured puts) did not beat random days, and one had 71 trades.
- The shorter-dated trend-pullback finalists lost money outright.

## 7. Index-ETF conclusions

1. **Long-dated bullish structures earned large profits in 2013–2026, and every setup's profit there is the market's.** No setup beat random days in the same direction on the hold-out.
2. **Bearish daily setups lost heavily,** most of all trend-pullback shorts.
3. **The failed-breakout put sales in the Swing bucket are the one daily cell** that cleared both baselines in development + validation (on about 100 trades). It was not a walk-forward finalist, so the hold-out was not opened for it. It is a hypothesis for a fresh hold-out.
4. **Daily management rules follow the trend's sign:** hold and add on the trend side, cut against it. None is direction-neutral.

## 8. Single names

**Coverage: one name, FB (2017-06 → 2022-06). The 40 planned single names were not completed.**
- Their option EOD history needs about 28 minutes of pulling per name, about 19 hours in all.
- **This session's container is reclaimed when the session sits idle,** and background jobs do not count as activity.
- It restarted at about 06:26 and 07:22 UTC on 2026-10-15, stopping the pull both times.
- AAPL reached 437 of its 489 weeks (cached, resumable).
- No other name was started, and the pull was capped before the US session so it would not compete with the owner's Theta Terminal for the vendor login.
- `scripts/pull_tier_d.py` resumes from its cache, so the remaining names can be pulled on an always-on machine with the same command (`01_data_inventory.md` §6).

**What FB alone shows** (development 2017–2021, validation 2022-H1; `results/tier_d/cells.csv`, group `single`). None of it generalizes beyond one stock:
- **Its baselines are its own path:**
  - FB rose about 2.2× from 2017 to 2021 and fell about 50 % in 2022;
  - a LEAPS-bucket Steady call bought every Monday made +2,303 a contract; the matching Steady put lost −4,016.
- **The setups against the baselines:**
  - against FB's all-days baseline, 58 of 864 cells were better and 48 worse;
  - against random days in the same direction, 52 better and 64 worse;
  - about as many worse as better, so no direction; the 864 cells are about 40 policies on the same trades, so the counts are not independent tests.
- **Pre-earnings straddles (D_EARN, the 5th session before a report):**
  - 2–20 reports a cell (15–20 held to expiry), e.g. the Swing straddle held to expiry −12 [−756, +872] on 20 reports;
  - every cell is under the 30-trade floor used everywhere else, so no interval here is a finding, and the comparison against all-days straddles is not reported.
- **Cash-secured put assignment:**
  - FB's cash-secured puts were exercised and the shares sold at the next open as modelled;
  - with one name and its 2022 fall, the assignment outcomes are one stock's path, not evidence.
- **Walk-forward:** 7 of 60 FB cells had out-of-sample lower bounds above zero and 19 upper bounds below it.

**Bootstrap per group.** Each group (index ETFs; single names) is analysed with its own day bootstrap (`scripts/analyze_tier_d_groups.py`). With one shared bootstrap, FB's 4 trading days that the index ETFs' rows lack shifted the index cells' day weights and moved borderline index intervals; per group, the index ETFs' results equal the index-only run to rounding.

**No hold-out is possible:**
- FB's data ends at the 2022 rename, before the hold-out begins in 2024.
- The META root (2022-06-09 →) was not pulled.
- The single-name hold-out (L-A4.1) therefore stays unopened, with no single-name finalist.

**Single names, earnings and assignment are untested on a credible sample.** That is the main gap in this deliverable.
