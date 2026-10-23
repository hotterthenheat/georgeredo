# EMA system — RULEBOOK v1 (written before any v1 signal, trade or P&L, and before the test weeks are drawn)

Status: written and committed ALONE, before any v1 signal, trade or P&L is computed, before the week-selection rule below
is run, and before any return of any candidate week is looked at. The run that follows (PREVIEW_v1_weeks.md) applies these
rules exactly; anything changed after a result is seen is v2 and is said so.

v1 = **RULEBOOK_v0.md (commit af32405) with exactly the four changes of §1**, each taken from a rule that passed an earlier
held-out test in this repo. Every other choice of v0 — including every **[v0]** default — stands unchanged and is not
restated except where a change touches it. The v0 preview on 2026-10-12..16 (PREVIEW_last_week.md, 8765f71) is what
prompted v1; that week is excluded from the draw below.

**PREVIEW — 15 sessions, no verdict.** Three weeks cannot separate a rule from luck. Nothing in the run is selected by its
result: every row listed in §5 is printed, the headline is fixed here, and the variants are reported beside it.

Files only. No vendor call is planned (all inputs are on disk; §4 says what makes a week eligible). Deterministic; every
random draw seeded.

## 1. The four changes from v0

### 1.1 The 14:00 exit (from X3, Compass features Phase A)
Source: FEATURES_REPORT.md (Phase A, 2a49049), X3 "0DTE entries before 14:00 sold at the 14:00 bid": holdout Δ **+7.78**
[+4.14, +10.95] points of the debit, PASS (still losing per trade: −9.51 with vs −17.29 without). Frozen in
FORWARD_RULE.md (b101ae1).
- v0's 15:58 flat (minute 388) is replaced, **for every exit variant X1–X4**, by a **14:00 flat (minute 270)**: anything
  still open after the bar completing at 14:00 has been read is sold at the **bid of the chain row stamped 270** (the same
  missing-bid rule as v0: the last bid in the 10 rows before, none → 0). In the v0 loop this is FLAT_M = 270: bars
  completing at minutes ≤ 270 can still trigger a stop, target or runner exit (sold at that row's bid — at minute 270 the
  same bid as the flat); otherwise the 14:00 sale.
- **No new entries at or after 13:30**: entry minutes m = 15..299 (09:45..13:29). v0's 15:30 limit (§3.6, §6) is replaced.

### 1.2 The 3% spread veto (from BV1b, Compass features Phase B)
Source: PHASE_B.md (e5dd8c6), BV1b "V1 spread veto at 3%": holdout Δ **+4.30** [+2.66, +5.85], PASS (still losing per
trade: −6.73 with vs −11.03 without; disclosed there that the holdout was not virgin for V1).
- v0 §4's "spread (ask − bid)/mid ≤ 12%" becomes **≤ 3%** (kept at exactly 3%, tolerance 1e-12 as v0). The filter order is
  v0's (standing quote → spread → |delta| 0.30–0.60 → OI ≥ 250 → previous volume ≥ 100; nearest |delta| 0.45; ties the
  tighter spread, then the lower strike). If no contract passes, **no trade**, counted with the first filter that empties
  the list (e.g. "spread > 3%").

### 1.3 The venue (VN1, Compass features Phase A — the weakest evidence of the three)
Source: FEATURES_REPORT.md, VN1 "keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid": holdout Δ
**+1.18** [+0.50, +2.20], PASS — the weakest of the three, and the first holdout read (on a table with duplicated rows)
had failed it (−5.77); FEATURES_REPORT.md discloses both reads.
- **The S&P is ONE signal stream, read on SPY's 1-minute bars** with the full v0 rule — bias, alignment, pullback, trigger,
  RSI, ROC **and RVOL on SPY's volume**. It is **one name** for the per-name cap (5 entries a session), the
  one-position rule and the 5-minute cooldown. **There is no separate SPX-signal stream in v1** (v0's SPXW stream on SPX
  prints, with its time-weighted VWAP stand-in and no RVOL, is gone from v1; it remains in "v0 as written", §6).
- At an S&P entry minute m, two candidates are picked, each by the full contract rule of §1.2 and §1.4 (same side,
  0DTE, nearest |delta| 0.45 within 0.30–0.60, passing the 3% veto, OI ≥ 250, previous volume ≥ 100):
  - **SPY**: the SPY 0DTE chain row stamped m; delta with spot = SPY's C[s] (s = m − 1).
  - **SPXW**: the SPXW 0DTE chain row stamped m; delta with spot = the SPX print stamped m (v0 §1's SPX close of bar s).
    No SPX print stamped m → SPXW is not a candidate at m.
  - Each candidate's **cost share** = ((ask − mid) + fee ÷ 100) ÷ mid, mid = (ask + bid)/2, fee = that venue's one-way
    fee at the ask (SPY $0.68748; SPXW $1.18748 if the ask < $1.00, else $1.27748). **The lower cost share is traded**;
    a tie (|difference| ≤ 1e-12) → **SPY**. If only one venue has a passing contract, it is traded; if neither, no trade
    (the reason recorded as "SPY: <reason> / SPXW: <reason>").
- The stop level, R, the +1R/+2R targets and the X3 runner are computed on **SPY's bars** whatever the venue; the trade is
  only **priced** in the chosen venue: bought at its ask at row m, every exit leg sold at its bid at the exit row, its fees.
- Size is v0's: 1 contract (X4: 10) **in the chosen venue**. An SPXW contract is ~10× an SPY contract's notional, so an
  SPXW trade weighs ~10× in dollars; % of premium is reported beside every dollar figure for that reason.

### 1.4 Kept as v0
The near-money contract (|delta| 0.30–0.60, nearest 0.45, Black-Scholes from the mid, r = 0.045, T = minutes to 16:00 ÷
525,600), open interest ≥ 250 (UW chain dated the session; SPXW read from UW's SPX chain under the SPXW root), and
previous-session volume ≥ 100 (ThetaData EOD of the session before, same contract), exactly as v0 §4.

## 2. Everything else is v0
QQQ and IWM are their own streams on their own bars and chains, exactly as v0 but for §1.1–§1.2. So v1 has **three signal
streams: S&P (SPY bars; SPY or SPXW contract), QQQ, IWM.** Unchanged from v0: Configs A (5m EMA5>15>20>50, pullback
EMA20 1m) and B (5m EMA9>21>50, pullback EMA21 1m); the 15m EMA50 bias; the 1m setup window W (last 5 bars) and its
"no close across the 1m EMA50"; the trigger (close beyond the previous bar's high/low and beyond VWAP); RSI14 (Wilder) > / <
50; ROC5 > / < 0; RVOL ≥ 1.5 (10 prior sessions, at least 5); first entry minute 09:45; the stop level beyond W's extreme
and R; exits X1 (+1R), X2 (+2R), X3 (5m close through EMA9(5m), the runner), X4 (10 contracts: 2 at +1R, 3 at +2R, 5 on
the runner), each with the stop active and now the 14:00 flat; targets on 1m closes; max 5 entries a name a session; one
position a name; next entry at minute ≥ the previous exit + 1 (+ 5 after a stop); fees each way as v0; buy at the ask, sell
at the bid. EMA warm-up: **the 60 trading days before each test week's Monday**, a separate warm-up per week (each week is
run on its own, its EMAs seeded at the first close of its own warm-up).

## 3. Tracked variants (counted and reported separately — NOT the headline)

The **headline** is §1–§2 as written. Variants, each defined here before any result:

- **V-chop.** For each stream and session (the S&P stream on SPY's bars):
  - first-hour range FHR = (max high − min low over the bars stamped 09:30..10:29, those present) ÷ the open of the 09:30
    bar; undefined if the 09:30 bar is missing.
  - The reference: FHR of the same stream on each of the **previous 60 trading days on disk** (bar file present, FHR
    defined; half days included), at least 40 defined, else the day is not a chop day. p33 = numpy.percentile(those
    values, 33) (default linear interpolation).
  - P1030 = the close of the 10:29 bar (the price at 10:30). Undefined (bar missing) → not a chop day.
  - **Chop day** ⇔ FHR < p33 **and** low₁ + 0.25 × (high₁ − low₁) ≤ P1030 ≤ low₁ + 0.75 × (high₁ − low₁), high₁/low₁ the
    first hour's high and low.
  - On a chop day: **no entries at m ≥ 60 (10:30)**; entries before 10:30 unchanged; everything else as the headline.
    (Entries before 10:30 never depend on later minutes, so V-chop = the headline's trades less those entered at or after
    10:30 on a chop day; a trade entered before 10:30 keeps its exits, wherever they fall.)
  The decision uses only bars completed by 10:30 and earlier sessions.
- **V-noIWM**: the headline's trades minus IWM's (the streams are independent, so this is a filter on the trade list).
- **V-calls / V-puts**: the headline's trades split by side.

**Rows reported**: 2 configs × 4 exits × 5 trade sets (headline, V-chop, V-noIWM, V-calls, V-puts) = **40 rows per
period**, for each of the 3 weeks and pooled = **160 rows**, plus the baselines (§6). All are printed; none is selected,
ranked or promoted by its result. The headline is fixed above.

## 4. The test weeks (fixed here; the rule may read ONLY SPY's weekly return)

**Eligible weeks**: Monday–Friday weeks, all five weekdays NYSE trading days and none a half day
(scanner_lib.trading_days / HALF_DAYS), with Monday ≥ 2024-05-01 and Friday ≤ 2026-10-09, and:
- no day of the week in a held-out month: 2017-06, 2017-09, 2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08,
  2020-11, 2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04, 2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07,
  2024-08, 2024-11, 2025-08, 2025-11, 2026-03, 2026-04, 2026-08 (scanner_lib.HELD_M; a week touching one is ineligible);
- not 2026-10-12..16;
- every input on disk (file present) for every day of the week: the 0DTE 1-minute chain of SPY, QQQ, IWM and SPXW
  (theta/data_full/chains); the 1-minute bars of SPY, QQQ, IWM (theta/data/underlying) and the SPX prints
  (theta/data/index/SPX); UW's dated chain for SPY, QQQ, IWM and SPX (features_data/uw/oi_chain); a ThetaData EOD file
  covering the previous trading day for SPY, QQQ, IWM and SPXW (theta/fetch_cache/eod_all);
- history on disk: the 1-minute bars of SPY, QQQ, IWM and the SPX prints on **each of the 60 trading days before the
  week's Monday** (the EMA warm-up; this also covers RVOL's 10 and V-chop's 60 previous sessions);
- the weekly return defined: SPY's bar files on the week's Friday and on the last trading day before its Monday.

**Weekly return** = SPY's Friday close ÷ SPY's close on the last trading day before the week's Monday (normally the
previous Friday) − 1, each close = the close of the last 1-minute regular-session bar on disk that day (the 15:59 bar when
present). This is the only market figure the selection reads.

**The draw**: rng = numpy.random.default_rng(**2026102310**); the eligible weeks are listed by Monday, ascending; then in
this order:
1. **Up week**: among eligible weeks with return > +1.5%, index = rng.integers(n_up).
2. **Flat week**: among eligible weeks with |return| < 0.3%, index = rng.integers(n_flat).
3. **Down week** (re-tests the v0 preview's conditions out of sample): among eligible weeks with return < −1.5%, index =
   rng.integers(n_down).
An empty category is reported empty and not replaced. The selection prints the counts of eligible weeks, of each category,
the weeks dropped by each eligibility test, and the three weeks with their returns.

**Disclosure (said before the draw)**: these weeks are not virgin for the market data in general. Other studies in this
repo read some of the eligible span for other rules: the EMA ladder / "nearest EMA targets" previews used 2025-02 and
2025-03 (cb79c23, e9d13c0); the Compass scanner and Compass features studies used broad Pick / exploration / check sets
of sessions over 2022–2026 (their non-held-out months), and the forward trackers read October 2026. None of them ran this
EMA system. The EMA warm-up, RVOL and V-chop history read only **underlying 1-minute bars** of the 60 sessions before a
week, which may fall in a held-out month (as v0's warm-up did for 2026-08): no option quote, signal outcome or selection is
read there, and scanner_lib's chain guard (which refuses a held-out month) stays on.

## 5. What is reported (each week, and the three pooled)

For each of the 40 rows a period: trades; net $; net $ a trade; net % of premium (Σ net ÷ Σ premium paid); win rate
(net > 0 after costs); calls / puts count; the largest single trade's share of the row's net total (|largest| ÷ |total|,
the trade with the largest |net|); fees and half-spread costs ($ and % of premium); and the S&P stream's venue counts
(SPY / SPXW). Also: no-trades by reason; how trades ended (stop, +1R, +2R, runner, 14:00).

- **Session bootstrap** (labelled as such): with 5 sessions a week no per-week interval is drawn; on the **pooled 15
  sessions**, an iid bootstrap over sessions, 2,000 draws, seed **2026102311**, of net per trade (Σ net ÷ Σ trades of the
  drawn sessions), 2.5–97.5% percentile interval, for every headline row (and V-noIWM).
- **Random-entry baseline** (headline only, every config × exit): **500 seeded trials** (seed **2026102312**, one
  generator a config × exit, its draws in a fixed order: week, stream, entry). Per trial, per week, per stream: the same
  number of entries as the headline's trades of that stream in that week; each entry draws a session uniformly from the
  week's five, an entry minute uniformly from the headline's entry minutes in that week (pooled over streams), a side
  that is a put with probability = the headline's put share in that week; the trade is then built **exactly as a headline
  trade**: stop level and R from the last 5 bars (as v0 §7c), the same contract picker, 3% veto and (for the S&P stream)
  venue rule, the same exit variant, the 14:00 sell. Risk rules not applied (draws independent, overlap allowed); a draw
  with no trade (no contract, zero R) is drawn again, up to 50 times. Reported per week and pooled: the baseline's mean
  net per trade and total, the 5–95% band of the total and of net per trade, and **the headline's percentile** (the share of
  trials whose total is below the headline's total).
- **Crossover (a) and alignment-only (b) baselines** as in v0's preview (v0 §7a/§7b signals), run **under v1's trading
  rules** (three streams, S&P on SPY's bars with the venue rule, 3% veto, entries 09:45–13:29, 14:00 flat, X2 exit, v0's
  risk rules).
- **v0 as written** (RULEBOOK_v0.md, its own code unchanged: SPXW stream on SPX prints, SPY, QQQ, IWM; 12% veto; 15:58
  flat; entries to 15:30) on the same three weeks, each week with its own 60-day warm-up, all 2 × 4 rows beside v1's
  headline, so the change v0 → v1 is visible.

**Integrity**: a plain-loop re-derivation (a new script that does not import the engine) of **at least 15 headline trades**
— the rule at the entry minute, no earlier allowed entry, both venues' contracts and the venue choice, R, every exit leg,
the bids, the net — target 0 differences, any difference reported; the **no-look-ahead** unit test (every v1 decision —
the signal and the V-chop gate — unchanged when every bar after the decision's last bar is truncated (set missing));
unit tests of the 14:00 flat, the 13:30 cut, the 3% veto, the venue choice and the chop definition. The sha256 of every
script used is printed in the report. The v0 files (ema_system.py, preview.py, verify_plain.py, test_ema_system.py) are
imported or copied, never edited.

Labels as v0: OBSERVED / CALCULATED / MODELED. Every table: **PREVIEW — 15 sessions, no verdict.** Ideas that come from
the results go in a "next version ideas" section, untested.
