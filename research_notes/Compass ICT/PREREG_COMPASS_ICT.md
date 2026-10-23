# PREREG — Compass ICT (the owner's sweep → displacement → FVG rule), v0, variants, ablations, splits

Committed ALONE, before any setup, trade or P&L is computed. Research only; read-only on files already on disk (no fetch).

## 0. Inventory (read before this file; no P&L)

- SPY 1-min (`theta/data/underlying/SPY`, 3,687 files 2012-06-01 → 2026-10-22): **no file holds a row before 09:30**
  (0 of 3,687). The pre-market high/low is therefore **dropped** everywhere.
- SPX index 1-min (`theta/data/index/SPX`, 2,362 files 2017-06-01 → 2026-10-22): **one print a minute** (`timestamp, price`;
  the print stamped t is the close of bar t − 1; no open, high or low). **No SPX daily file is on disk**: daily bars are
  built from these regular-session prints (high = max print, low = min print, close = the 16:00 print).
- SPXW 0DTE 1-min NBBO (`theta/data_full/chains/SPXW`, 1,115 files 2022-05-13 → 2026-10-22; 391 rows a strike/right a day).

## 1. The rule, v0 (frozen; the owner's words, condensed)

**Data.** Instrument SPXW 0DTE. Signals from SPX 1-min bars; where SPX's bars are missing, SPY's scaled by SPX/SPY at 09:30.
New York clock; a bar stamped t covers t to t+1; only completed bars are used.

*Implementation of "missing" (stated, not a choice made after results):* SPX's open, high and low are missing for every
minute on disk (one print a minute), so the 1-min OHLC bars of the signal are **SPY's, scaled by the day's ratio
R = SPX print stamped 09:31 (the close of the 09:30 bar) ÷ SPY's 09:30 bar close**. Everything intraday (bars, PDH/PDL,
swings, sweeps, FVG, stops, targets) is in these scaled units. PDH/PDL = the prior session's SPY high/low × today's R.
The underlying's signed return of a trade is measured on SPX's own prints (entry minute → exit minute).

**Setup.**
- a) HTF bias. A daily swing high (low) is a daily bar whose high (low) is ≥ (≤) the highs (lows) of the 2 days on each side;
  known once those 2 later days close. At each day k, an event is a close above the high of the most recent swing high
  confirmed by k (j + 2 ≤ k) — bullish — or below the low of the most recent confirmed swing low — bearish. Bias at the
  09:30 open of D = the direction of the most recent event on a day ≤ D − 1; none → no trade that session (counted).
  Daily bars: SPX, built from 1-min prints (section 0).
- b) Levels: PDH, PDL (prior regular session's high/low). Pre-market dropped (no rows on disk). Asia/London dropped.
- c) Killzones, entries only: AM 09:30–11:00, PM 14:00–15:00 — the entry bar (stamp t) lies inside: 0 ≤ t < 90 or
  270 ≤ t < 330 (entry minute = t + 1).
- d) Sweep. A bar s with high ≥ level × (1 + 0.0002) (a high level) or low ≤ level × (1 − 0.0002) (a low level), and a bar
  k ∈ [s, s + 5] closing back inside (close < PDH / close > PDL), the first such k. A high swept is bearish, a low swept
  bullish. Must agree with the HTF bias, else ignored. Sweep extreme = the max high (min low) of bars s..k. After a sweep
  the next sweep of that level is searched from k + 1.
- e) Displacement + MSS. The first bar j ∈ [k, k + 15] in the setup's direction (bearish close < open) with body |C − O| ≥
  1.5 × the median body of the 20 bars before it (the prior session's bars used where today has fewer than 20), whose close
  breaks the most recent 1-min swing on the other side (bearish: close < the low of the latest swing low; bullish: close >
  the high of the latest swing high). A 1-min swing at t: high ≥ (low ≤) the 2 bars each side, confirmed when t + 2 ≤ j;
  swings searched over the prior session and today.
- f) FVG. j is bar 2 of three (bar1 = j − 1, bar3 = j + 1). Bearish: bar1.low > bar3.high, zone [bar3.high, bar1.low].
  Bullish: bar1.high < bar3.low, zone [bar1.high, bar3.low]. No gap → no setup (counted). Only the first j of (e) is tried.

**Entry and contract.**
- g) The first bar t ∈ [j + 2, j + 31] inside a killzone that trades into the zone (bearish high ≥ zone low; bullish low ≤
  zone high). Buy at the ask of the quote row stamped t + 1.
- h) SPXW 0DTE; put bearish, call bullish. Black-76 on the chain's parity forward at row t + 1 (the strike with both sides
  standing and |C_mid − P_mid| smallest; F = K* + C_mid − P_mid), discount factor 1, T = minutes to 16:00 ÷ 525,600, IV from
  the mid. Candidates: ask > bid > 0, spread ≤ 10% of mid, |delta| 0.45–0.60; the one nearest 0.50 (ties: lower spread, lower
  strike). None → no trade (counted).

**Exits** (at the bid of the row stamped u + 1 when bar u completes; a missing bid takes the last in the 10 minutes before;
none → $0, no fee). Bars after the entry bar are read; first trigger wins; within one bar the targets (touches) precede the
stop (a close).
- Stop: a 1-min close beyond the sweep's extreme.
- TP1: the underlying reaches (touch) the most recent opposite 1-min swing confirmed at entry (bearish: the latest swing low
  below the entry close; bullish: the latest swing high above it). Sell half; stop on the rest → the underlying's entry price
  (the entry bar's close). No such swing → no TP1.
- TP2: the opposite day level (bearish PDL, bullish PDH). Already beyond it at entry → no TP2 and TP1 sells all.
- Flat at 15:58 (row 388).
- Size 2 contracts (half = 1). Fees per contract each way (PREREG_PICKER.md §4): $1.18748 if that side's price < $1,
  $1.27748 if ≥ $1.

**Limits.** At most 1 open trade (an entry minute must be later than the previous exit minute) and 2 trades a session;
setups are taken in entry-minute order.

## 2. Variants

- **V1 — OTE entry:** the first killzone bar in [j + 2, j + 31] trading into 62–79% of the leg from the sweep extreme to the
  displacement bar's extreme (bearish: its low; zone [low + 0.62·leg, low + 0.79·leg]), in place of the FVG entry (the
  FVG is still required).
- **V2:** everything entered before 14:00 is out at the 14:00 bid (row 270) if still open.
- **V3:** AM-killzone entries only on sessions whose first-30-minute range (bars 09:30–09:59, scaled) ≥ 0.76 × the 9:31
  straddle (the implied move at row 1: C_mid + P_mid at K*). The range is known at 10:00, so no AM entry before 10:00 under
  V3 (no look-ahead). PM entries unchanged.
- **V4:** sweeps (5 bars), swings, displacement (15 bars, median of the prior 20 five-minute bodies), MSS, FVG and TP1's
  swing on clock-aligned 5-min bars (O first, H max, L min, C last of the 1-min scaled bars). Entry (first 1-min killzone bar
  into the zone within 30 minutes of bar 3's end), stop (1-min close) and TP touches on 1-min bars.

## 3. Ablations (descriptive)

v0 without the HTF bias (both directions); without the sweep (every bar a displacement candidate in the bias's direction;
stop = the extreme of the 15 bars before the displacement bar and the bar itself); without the FVG (enter at the
displacement bar's close, row j + 1, inside a killzone); without the killzones (entry minute 09:35–15:30).

## 4. Splits (written here; NOT run by this preview)

- **Exploration:** SPXW 2022-05-13 → 2026-10-09 minus the 28 months. Not run yet.
- **Holdout A:** SPX/SPY 2017-06 → 2022-05-12, the underlying's signed return per trade; pass: mean > 0 with the 20-session
  block-bootstrap interval at 1 − 0.05/k clear of zero (k = number of finalists).
- **Holdout B:** the 28 months 2017-06, 2017-09, 2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08, 2020-11, 2020-12,
  2021-01, 2021-03, 2021-05, 2021-11, 2022-04, 2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07, 2024-08, 2024-11,
  2025-08, 2025-11, 2026-03, 2026-04, 2026-08. Pass: options mean % > 0, interval clear of zero, ≥ 80 trades, above the
  97.5th percentile of 500 random-side draws; report the share of profit from the 5 best days.
- **Finalists:** v0 plus at most 2 variants with exploration mean > 0 and underlying return > 0.
- Disclosure: the picker test (`../Compass phase 3/picker_prereg/`) already read OR- and PDH-sweep rules on 2022–2026 options
  data.

## 5. Two-week preview (the only thing run now)

- **Window:** the last 10 full sessions with SPXW chains on disk: 2026-10-09, 10-12, 10-13, 10-14, 10-15, 10-16, 10-19,
  10-20, 10-21, 10-22 (no half day; every chain file 391 minutes to 16:00).
- **Neither holdout is read** (A ends 2022-05-12; B's months are not touched — the HTF daily history is read from
  2026-09-01 only, so the held-out 2026-08 is not read even as context: 27 prior sessions before 10-09, short of ~30, stated).
  The exploration span is not run.
- Rows: v0, V1–V4, the four ablations. Per row: trades and no-trade reasons; win rate (net > 0); mean % (net ÷ debit) and
  $ per trade after fees (ask in, bid out); average win and loss; exit-reason shares; the underlying's signed return entry →
  exit in bp and in units of the 09:30 implied move; per AM/PM killzone.
- 500 random-side draws at v0's entry times (each trade's side a fair coin; the same picker and exits; a flipped side keeps
  the stop at the same distance on its own side, TP1 = its own latest opposite swing, TP2 = its own day level); v0's
  percentile on mean % per trade. Seed 20261023.
- No bootstrap (10 sessions: meaningless). Everything labelled **PREVIEW — 10 sessions, no verdict**; no finalist is chosen.
- Integrity: every v0 setup and 5 no-trade sessions re-derived by separate plain-loop code (0 differences required); 3
  sessions rebuilt with the files cut at the entry minute, plus a control cut earlier.

## Amendment 1 (2026-10-23)

Committed alone, before any exploration setup, trade or P&L is computed. The owner's amendment.

- **Reason.** v0 traded once in the 10 preview sessions. At that rate holdout B gives far fewer than the 80 trades its
  pass needs: about 27 on its 269 full SPXW sessions (13 of the 28 months have SPXW chains; about 60 if all 28 had), so
  v0 cannot pass B whatever its edge. The amendment rests on trade counts only, not on returns.
- **Change 1.** The four ablations of section 3 (no HTF bias, no sweep, no FVG, no killzones) become finalist candidates
  under the same rule as V1–V4: exploration mean % per trade > 0 and the underlying's signed return > 0. Finalists stay
  v0 plus at most 2 candidates; k = the number of finalists (v0 included).
- **Change 2.** A candidate is eligible only if its projected holdout-B trade count is ≥ 80. Projected count =
  exploration trades per session × holdout-B sessions. The holdout-B sessions are counted from the SPXW files' dates
  (`theta/data_full/chains/SPXW`), without opening them: 273 files in the 28 months (2022-12 21, 2023-05 22, 2023-11 21,
  2024-05 22, 2024-06 19, 2024-07 22, 2024-08 22, 2024-11 20, 2025-08 21, 2025-11 19, 2026-03 22, 2026-04 21,
  2026-08 21), less the 4 exchange half days among them by the calendar (2023-11-24, 2024-07-03, 2024-11-29,
  2025-11-28) = **269 full sessions**. Every candidate's exploration count and projected B count is reported.
- **Ranking.** Section 4 does not say how the at most 2 are picked when more qualify. Tie-break, a mechanical consequence
  of Change 1 and not a new choice: **highest exploration mean % per trade**.
- **Forward sessions.** The 9 sessions after 2026-10-09 (2026-10-12, 10-13, 10-14, 10-15, 10-16, 10-19, 10-20, 10-21,
  10-22) are reported separately, apart from the exploration and both holdouts, and play no part in choosing
  finalists. 2026-10-09, inside the exploration span, was read once by the preview (section 5).
- **How the span is read (the preview's convention, section 5, carried over; not a rule change).** Full sessions only
  (the calendar's half days out, as in the preview). No file dated before 2022-05-13 (holdout A) or inside the 28 months
  is opened, even as context; a guard raises if one is. So the HTF daily history of a session starts at the first
  session after the most recent held-out month before it (or at 2022-05-13), as the preview's started at 2026-09-01;
  a session whose prior session is held out (the first session after each held-out month, and 2022-05-13) cannot form
  PDH/PDL or the prior-session bars and is not run (listed). Trades per session = trades ÷ exploration sessions run.
- **Nothing else changes.**
