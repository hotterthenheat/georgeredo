# Step 6 pre-registration: the anatomy of the runners

Written and committed **alone**, before any conditional lift, any rule, any exit or any P&L of this step is computed.
Before writing it, only these were looked at: the step 1–5 READMEs and scripts, the schemas of the raw files, the
coverage of the UW and macro files, and the population's trade counts by product and buy time (counts only, no
outcome).

The owner's request: *"don't hold to close and the ones that moved 40%+ figure out how they worked, and the ones that
moved 500%+ figure out how, that's the whole game reversed engineering and figuring out how"*.

## 1. The trades (the population)

Step 2's trades (`step2/out/entries_<PRODUCT>.parquet`): every same-day contract on SPY, QQQ, IWM and SPX (root SPXW),
bought at the ask at a fixed time when it has a bid and an ask (ask > 0). Same clock, prices and half days as steps 1–5.
A trade is in the population when **all** of these hold:

| Filter | Rule | Why |
|---|---|---|
| Buy time | 9:31, 10:00, 10:30, 11:00, 12:00, 1:00 pm, 2:00, 3:00 (step 2's nine times less 3:30) | No position is held past 3:30 pm, so a 3:30 buy has no window |
| Near the money | \|strike − price\| ≤ one remaining expected move, the move being step 3's at-the-money straddle mid at the buy minute (`straddle_entry`) | Step 5 found the runner zone is set in expected-move units. A fixed 0.5% band is about 0.3 moves at 9:31 and 2+ moves at 3:00, so it would mix very different contracts across buy times |
| Spread | (ask − bid) / mid ≤ 10% at the buy minute | As asked |
| Days | Full sessions only (half days out); sessions up to 2026-10-09 (step 2's end) | Half days have no 3:30 pm |
| Held out | Never read: 2017-06, 2017-09, 2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08, 2020-11, 2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04, 2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07, 2024-08, 2024-11, 2025-08, 2025-11, 2026-03, 2026-04, 2026-08 | No raw file of a held-out session is opened. A figure that would come from a held-out session (the prior session's close, range or UW gamma flip, on the first session after a held-out month) is left blank |

Coverage: SPX from 2022-05-13, SPY and QQQ from 2022-11-11, IWM from 2024-04-19 (the raw chains' own starts).

**Periods.** Pick: 2022-05-13 to 2024-12-31. Check: 2025-01-02 to 2026-10-09. Everything chosen is chosen on Pick
and read once on Check, unchanged.

**Moneyness bin** (used for every base rate): x = (strike − price) / straddle, signed so out of the money is positive
for calls and puts alike. Six bins: [−1, −0.5), [−0.5, −0.2), [−0.2, 0), [0, 0.2), [0.2, 0.5), [0.5, 1].
**Cell** = buy time × moneyness bin (8 × 6 = 48 cells).

## 2. Runner classes (the bid's peak, never the close)

The peak is the highest bid (minutes with a two-sided quote, as in step 2) in a fixed window after the buy. Its minute
is the first minute the peak is reached. Two windows, both fixed here:

- **H60**: from the minute after the buy to 60 minutes after it, but never past 3:30 pm (minute 360).
- **H1530**: from the minute after the buy to 3:30 pm.

Classes, by the peak bid against the ask paid (a tolerance of 1e-9, as in step 2):

| Class | Peak |
|---|---|
| R40 | ≥ 1.40 × ask (+40%) |
| R100 | ≥ 2.00 × ask (+100%) |
| R500 | ≥ 6.00 × ask (+500%) |
| DUD | ≤ 1.10 × ask (never above +10%), or no quote in the window |

R40 ⊃ R100 ⊃ R500. For side-by-side description the exclusive bands are also used: DUD, +10–40%, +40–100%,
+100–500%, +500% and up. **Primary pairs** for Part 2: R40 and R100 in H60, R500 in H1530. All six (3 classes × 2
windows) are reported.

## 3. Part 1: how the moves happened (descriptive, Pick and Check together and apart)

For every trade and each window, from the buy minute to the peak minute:

1. **The underlying's move** in the contract's direction (up for calls, down for puts): in points, in %, in units of the
   straddle at the buy (`straddle_entry`) and in units of the 9:31 straddle (step 3's straddle at the 9:31 entry).
2. **Minutes to the peak.**
3. **Steady or burst**: the largest one-minute move in the contract's direction between the buy and the peak, and the
   largest five-minute move (any five consecutive minutes), each as a share of the whole move. Only where the move is
   positive. **Burst** = the largest five-minute stretch carried 60% or more of it; **steady** otherwise.
4. **The option's gain split by Black-Scholes repricing** (Black-76 on the forward): the forward at a minute is the median
   of K + C_mid − P_mid over the three strikes nearest the price with both sides quoted (put-call parity, so the carry
   r − q is read from the market, as the engine audit set); discounting is left out (r·τ is under 0.02% of the price
   for a same-day contract). Time τ = minutes to 4:00 pm ÷ (252 × 390). The implied vol at the buy and at the peak is
   solved from the mid. The change in the mid is split three ways — **price** (the forward's move: delta, gamma and
   higher order), **IV** (vega) and **time** (theta) — by the Shapley average over the eight corners of
   (forward, vol, time), so the three parts add up exactly. The fourth part is the **spread**: (mid − ask) at the buy plus
   (bid − mid) at the peak. The four add up to bid at the peak − ask paid. Shown as % of the ask paid and as shares of
   the gain.
5. **IV at the buy and at the peak.**
6. **Time of day** of the buy and of the peak.
7. **What the underlying did between the buy and the peak**: broke the opening range (9:31–10:00 prices) in the
   contract's direction for the first time; crossed VWAP the contract's way (on the wrong side at the buy, the right
   side at the peak); crossed the prior session's UW gamma flip the contract's way (where covered); made a new session
   high (calls) or low (puts); made a new session low (calls) or high (puts) after the buy and then reversed to the peak.
8. **The day**: its range ÷ the 9:31 straddle, trend day (|close − open| ≥ half the day's range) or not, the gap, VIX
   at the buy and its change over the session.
9. **Scheduled events**: FOMC decision (2:00 pm), CPI, NFP (8:30 am) days, from `data/macro_events_2022_2027.json`.
   For FOMC days, whether the peak came after 2:00 pm.
10. **R500 case table**: the 30 largest peaks in H1530: date, product, side, strike, buy time, ask paid, peak bid, peak
    time, multiple, and the underlying's path (its price every 15 minutes from the buy to the peak).

Each measure is marked **knowable at the buy** or **only after the fact**. Items 1–3, the IV at the peak, the peak's
time, item 7, the day's range, trend and VIX change are after the fact: they explain a move, they cannot be traded.

## 4. Part 2: what was visible before (lift against the same buy time and moneyness)

**The trap, stated first.** A description of winners alone says nothing, since non-winners may look the same. Only the
lift against non-runners bought at the same time at the same moneyness counts.

**Features**, all known by the end of the buy minute:
- **Step 5's 42** computed for these fixed-time buys by step 5's own code (`step5/features.py` `session`, the same
  formulas as `step5/model.py`), less the three that are constant or duplicated here (`kind`: every buy is a fixed
  time; `half_day`: none; `to_close`: equals the buy time on a full day): product, is_call, weekday, entry_minute, otm,
  otm_im, price, spread, bid_size, ask_size, size_imb, turn, low_age, fall, open_vs_low, ask_vs_open, mom1, mom5, mom15,
  dret1, dret5, dret15, dret30, dmove, dgap, pos, new_ext5, new_against5, range_pct, prior_range_pct, rv15_pct, vix,
  vix_chg, vix_chg15, implied_rest, implied_open, iv_now, iv_ratio, range_im.
- **Day context known by then**: |gap| (gap_abs); the first-30-minute range (9:31–10:00 prices) ÷ the 9:31 straddle
  (or30_im, buys from 10:00); VWAP side in the contract's direction (vwap_side) and the distance to VWAP in remaining
  moves (vwap_im) — an ETF's VWAP from its own one-minute bars ((high + low + close) / 3 × volume, bars closed by the
  buy minute), SPX's as SPY's VWAP × SPX / SPY at the minute (SPX has no volume); the opening-range state in the
  contract's direction (or_state: forming at 9:31 and 10:00; inside; broke with; broke against; broke both); the UW
  gamma regime, the sign of `gamma_per_one_percent_move_oi` at the latest UW spot-exposure row stamped at or before the
  buy minute (uw_regime: positive / negative); the distance to the prior session's UW gamma flip
  (`gex_levels` of the session before, stamped after that session's close), in the contract's direction, in remaining
  moves (flip_im); the scheduled event (event: FOMC, CPI, NFP, none); the contract's implied vol at the buy (iv_entry,
  as in Part 1).
- UW coverage starts 2023-12-08 (spot exposures) and 2023-11-21 (levels): earlier trades have those features blank.

**Buckets.** A feature with six or fewer distinct values is read as categories. Every other feature is cut at its
quintiles on Pick (the cut points then used unchanged on Check). A blank is its own bucket ("not available").

**Lift.** For class C and window h, the base rate b(cell) is the share of class C among all population trades in that
cell, **in the same period**. For a bucket: lift = (trades of class C in the bucket) ÷ (Σ over the bucket's trades of
b(cell)). So a lift of 1 means the bucket runs as often as any trade bought at the same time at the same moneyness.
Interval: a moving-block bootstrap over calendar dates (blocks of 5 dates, 2,000 draws, `audit_lib.block_draws`), the
2.5–97.5 percentiles of the ratio.

**A bucket raised the odds in Pick** when it has ≥ 300 Pick trades on ≥ 30 Pick dates, lift ≥ 1.25 and the interval's
lower end above 1. (Lowered: lift ≤ 0.80 and the upper end below 1.) **It held in Check** when its Check lift is on the
same side of 1 with the Check interval excluding 1. Only buckets that pass on Pick are read for holding. The number of
tests (features × buckets × 6 class-window pairs) is reported beside the count that held.

## 5. Part 3: trading it without holding to the close

### 5.1 Choosing the rules on Pick (mechanical)

- A **condition** is one Part 2 bucket (not a "not available" bucket) with ≥ 300 Pick trades. A **rule** is one
  condition, or two conditions on two different features joined by AND.
- **Family A** (the +40% runners): every rule with ≥ 300 Pick trades on ≥ 60 Pick dates is ranked by its Pick lift for
  R40 in H60. The top three are taken, skipping a rule that uses the same feature set as one already taken. Ties go to
  more trades.
- **Family B** (the +500% runners): the same, ranked by the Pick lift for R500 in H1530.
- A rule buys **every** population trade that meets it (one contract each), as step 5's "every pick".

### 5.2 The exits (fixed; nothing is held to the close)

Bought at the ask. A target sells at the target price the first minute the bid reaches it (a resting limit, as in
steps 2–4); a stop or trail sells at that minute's bid; a time exit sells at the last bid at or before its minute.

- **(a) +40% / −30%**: sell at 1.40 × ask when the bid reaches it; sell at the bid the first minute it is ≤ 0.70 × ask;
  otherwise sell at the bid at the earlier of 60 minutes after the buy and 3:30 pm.
- **(b) 50% trail armed at +40%**: no stop until the bid first reaches 1.40 × ask; from then, sell at the bid the first
  later minute it is ≤ half the highest bid since the buy; otherwise sell at the bid at 3:30 pm.
- **(c) half and trail**: two contracts. Sell one at 1.40 × ask when the bid reaches it; trail the other as in (b); if
  +40% never comes, sell both at the bid at 3:30 pm. The result is per contract (the two together over twice the cost).

**Fees** each way per contract: SPY, QQQ, IWM $0.65; SPXW per its schedule in the repository
(`research_notes/Compass features/PREREG_FEATURES.md` §2.6): $1.18748 when that side's price is under $1.00, $1.27748 at
$1.00 or more. No sale fee when the exit bid is $0 (nothing to sell). **Return of a trade** r = net $ ÷ (ask × 100 ×
contracts).

### 5.3 What is reported, per rule × exit, on Pick and on Check

Trades, win rate (net > 0), average r, median r, average win, average loss, total $, the share of the total made on the
best 5 days, and on Check a **20-session moving-block bootstrap 95% interval** of the average r per trade
(`research_notes/Compass phase 3/backtest_audit/audit_lib.py` `session_stats`, every Check date in the series, zero
where the rule took no trade).

**Random baseline**: 500 seeded draws (seed 20261023): each draw takes, without replacement, the same number of trades in
each cell (buy time × moneyness bin) as the rule took in that period, from the whole population of that period, and
applies the same exit. The rule's average r is placed among the 500 averages (its percentile).

**A rule-exit passes** when, on Check: its average r is above 0, the bootstrap interval's lower end is above 0, and its
average r is above the 97.5th percentile of the 500 random draws. 6 rules × 3 exits = 18 tests; about 0.5 would pass by
chance at 2.5% each.

## 6. Integrity

- `verify.py`: at least 30 random trades and 10 R500 paths re-derived from the raw chain files with separate code
  (plain Python loops over the rows): the peaks and their minutes in both windows, the three exits' results, the
  underlying's move to the peak, and the buy-minute figures. 0 differences required.
- No look-ahead: for sampled sessions, the whole feature build is run again with every raw file cut at the buy minute
  (quotes and prints stamped after it, ETF bars not yet closed, UW rows stamped after it, removed); the features must
  be identical.
- sha256 of every script in the README.
- Negative results are reported as they come. Nothing is tuned after Check is read.
