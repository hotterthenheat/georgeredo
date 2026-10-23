# H7 — the pre-FOMC drift, SPY and QQQ stock: the forward rule (committed before any forward datum of H7 exists)

History: written late on Thursday 2026-10-22, New York time (2026-10-23 UTC), before the 2026-10-23 session opened, and
committed with its power script alone —
`FORWARD_RULE_H7.md`, `power_h7_forward.py` and its output `power_h7_forward.json`, nothing else. The first forward trade's
entry is the official close of Tuesday 2026-10-27 (the statement of Wednesday 2026-10-28); no session from 2026-10-23 on had
been read when this file was written, and none is read by the power script. The exact commit time is the commit's own
timestamp. Nothing in this file is changed once a forward row exists.

Why this file: H7 passed its pre-registered test in both names (`PREREG_H7.md`, `edca472`; result `6c94bb8`, SPY +$70.43 a
trade [+14.64, +129.31], QQQ +$69.59 [+23.10, +122.14]; QQQ also at the ledger's Bonferroni level). Under the queue's rule 6
(`QUEUE.md`) a pass is not "an edge that works" until it is confirmed on forward sessions under a rule, an N and a pass line
committed before them. This is that rule, in the house style of `research_notes/Compass features/FORWARD_RULE.md`.

## 1. What is frozen

- **The rule**, exactly as `PREREG_H7.md` section 2 states it (commit `edca472`, sha256
  `f81606b5c0a0f0e21e9234b2fc5cc77c0c51fb3f1dcaaa79010b3dfdcb519742`): for each scheduled FOMC statement released at 2:00 pm
  on date A, **buy 100 shares at the official close of the session before A**, **sell at the close of the 1-minute bar stamped
  13:58 on A** (the last trade printed before 13:59:00 in ThetaData's `stock_history_ohlc` 1-minute feed), `net = 100 × (X −
  C_prev) + 100 × DIV − COSTS`, with **COSTS = 100 × ($0.01 + $0.005) = $1.50 a trade at 1×, $3.00 at 2×**; no borrow, no
  financing charge. One variant; no threshold, filter or size changes.
- **The names**: SPY and QQQ, each judged on its own.
- **The test it confirms**: `out/h7_trades.csv` (`6c94bb8`, sha256 `c1af017ae6932dbd6f66e4fcb9fd372eec3851090310770e824447e9c79e0e50`),
  the only input of the power figures below.

## 2. The forward set (which trades count) and the inputs of a trade

- **Statements**: every scheduled FOMC statement with A on or after **2026-10-28**, in calendar order: 2026-10-28 (entry the
  2026-10-27 close), 2026-12-09, then 2027-01-27, 03-17, 04-28, 06-09, 07-28, 09-15, 10-27, 12-08, and so on. The dates are
  the `FOMC_DECISION` rows of `data/macro_events_2022_2027.json` (committed `69591dd`; the Fed's calendar page
  https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), cross-checked against the meetings listed in
  `data/fomc_statements_2012_2026.json` (`6c94bb8`; parsed from the same page on 2026-10-23; through 2027 they agree). Scheduled
  meetings only: an unscheduled meeting, conference call or notation vote is never a trade. Years after 2027 are added to that
  calendar file from the Fed's page (scheduled meetings only, with the source) before their first entry close; the forward
  runner refuses, loudly, to judge any session past the last calendar year the file lists — a statement is never missed by a
  calendar that ran out. If the Fed moves a scheduled meeting, the calendar row is corrected from the Fed's page before the
  entry close it affects, in a commit that names the page.
- **Only statements released at 2:00 pm** (as the prereg): a calendar row whose `time_et` is not 14:00, or a statement on a
  day that is not a full session, is excluded and listed (no trade).
- **C_prev**: Unusual Whales' daily bar `close` with `market_time == 'r'` for the session before A — the prereg's source from
  2025-10-13 — as the daily forward job keeps it (`data/official_closes/`, read through `paper_audit.OfficialCloses`, source
  `uw_1d`). A close from any other source, or none yet, is not substituted: the trade waits, and the runner says so.
- **X**: the `close` of the 1-minute bar stamped 13:58 on A in the daily job's layout (`<parquet root>/data/underlying/<name>/
  <A>.parquet`, ThetaData `stock_history_ohlc` 1m — the test's feed). A file that is in the layout but has no priced 13:58 bar →
  the meeting is excluded and listed, as the prereg says; no other bar is substituted. A file not yet in the layout → the trade
  waits (it is not excluded).
- **DIV**: the cash dividend per share whose ex-date is A (the prereg's rule). H1's frozen table ends at SPY 2025-12-19, so the
  forward source is a committed table of announced ex-dates (`research_notes/Edge search/H7_H8_H9/data/dividends_forward.json`,
  added with the runner), each row with its source, and a `complete_through` date per name; a trade whose A is past that date
  fails loudly and waits — a dividend is never assumed to be 0 because a row is missing.

## 3. N, its basis, and how long it takes

N is set in **trades per name** from the committed test's own per-trade spread and a **shrunk** effect — not the in-sample mean.

- **Spread** (`power_h7_forward.py` on `out/h7_trades.csv`): each included trade's net at 1× as bp of its position, `net_1x ÷
  (100 × C_prev) × 10⁴`. **SPY: 77 trades, mean 19.01 bp, sd 64.90 bp. QQQ: 108 trades, mean 21.05 bp, sd 82.49 bp.** (Lag-1
  correlation of successive trades 0.13 and 0.19, within noise at these counts.) N is computed in bp so that it does not depend
  on the price level of the years ahead; the verdict is read in dollars a trade, as the test's.
- **The effect assumed: half the test's mean** — **μ = 9.50 bp (SPY), 10.52 bp (QQQ)** a trade after costs (≈ $72.61 and
  $74.14 a trade at the 2026-10-22 closes $763.96 and $704.47). Why shrunk: H7 is reported because it passed; a mean selected by
  passing a test overstates the true effect (the winner's curse), and the published record after 2011 is far below the test's
  mean. Why half and not a published figure: the instruction's alternative was the published post-2016 estimate on the S&P 500
  if it is lower. The only post-2016 window in the record (`PREREG_H7.md` section 1) is Song's (SPX and ES 2016–2023): the
  overnight gap +0.19 % and open-to-release −0.03 %, about **+16 bp** close-to-release (≈ 15.8 bp after this rule's costs) —
  higher than half the test's mean, so half the mean is used (the more conservative of the two). Printed beside it for the
  reader (not the rule): Hu, Pan, Wang & Zhu's 2012–2018 figure, 3.96 bp (t 0.74) — a window mostly before 2016 — and Lucca &
  Moench's 49 bp (1994–2011, a different 24-hour window).
- **The interval used for the verdict: the test's own** — the 20-session moving-block bootstrap over every calendar session
  (section 4). Chosen over an iid trade-level interval to keep the committed test's statistic unchanged; the two nearly
  coincide here, because scheduled statements were 29 to 65 weekdays apart in the test (mean 33), so a 20-session block holds
  at most one trade and the block bootstrap resamples trades as if independently, with a random trade count per draw.
- **N0 = ⌈((z₀.₉₇₅ + z₀.₈₀) × σ ÷ μ)²⌉** (z sum 2.8016): **SPY 366, QQQ 483 trades.** Then the simulated power of the rule's own
  verdict at N0 (2,000 outer draws of N0 trades drawn iid from the name's test trades re-centred to μ, seed 20261023 + N, placed
  on a forward calendar from 2026-10-23 with the test's gaps between statements, each judged by the section-4 interval):
  **0.821 (SPY) and 0.826 (QQQ)** — at or above 0.80, so N = N0 (the rule would have raised N in 5 % steps otherwise).

| name | test trades | mean (bp) | sd (bp) | μ assumed = mean ÷ 2 (bp) | **N (trades)** | power at N | years at 8 statements a year |
|---|---|---|---|---|---|---|---|
| SPY | 77 | 19.01 | 64.90 | 9.50 | **366** | 0.821 | **≈ 45.8** |
| QQQ | 108 | 21.05 | 82.49 | 10.52 | **483** | 0.826 | **≈ 60.4** |

**Plainly: N implies about 46 years of statements for SPY and 60 for QQQ** (eight scheduled statements a year; the forward
calendar reaches the 366th SPY statement around 2072 and the 483rd QQQ statement around 2087). At the effect this rule
assumes, no verdict comes in any useful time. For the reader only (formula N, not the rule): at the unshrunk test mean, 92 (SPY)
and 121 (QQQ) trades, 11.5 and 15 years; at Song's ≈ 15.8 bp, 133 and 214; at Hu et al.'s 3.96 bp, 2,339 and 3,778. The rule is
registered so that the forward record accrues under terms fixed now, and so that nothing short of N is ever read as a
confirmation.

## 4. The statistic (the test's, on the forward sessions)

Per name, separately: the series is **every NYSE session from 2026-10-23** (the recorder's calendar, `scripts/eod_recorder.py`
HOLIDAYS; half days are sessions), in calendar order, through the session of the last counted trade; S_i = the net $ at 1× of
the trade whose statement date A is session i (0 on every other session), N_i = 1 on a traded A, else 0.

- **Δ = Σ S ÷ Σ N** — the mean $ a trade after costs at 1× (2× reported beside it, same draws).
- **Interval**: `audit_lib.block_draws(n, 20, B=2000, seed=20261023)` over those n sessions, `audit_lib.weights_from`, each
  draw's Σ W·S ÷ max(Σ W·N, 1) (a draw with no trade counts as 0, as in the test), `audit_lib.pct_ci` (2.5 and 97.5 percentiles).

## 5. The rule

1. A trade **counts** only when its row is final: C_prev from the stated source, X from the stated bar (or the meeting excluded
   and listed under section 2), the dividend table complete through A. A trade that waits is not counted and nothing stands in
   for it; trades are counted in calendar order (the count is the length of the final prefix). Excluded meetings are listed
   and are not trades.
2. **No verdict before N** (SPY 366 trades, QQQ 483 trades). No early stop, no extension, no change of N, rule, names, costs,
   calendar source or statistic once a forward row exists.
3. **At exactly N counted trades**, per name, on those N trades only (the series cut at the N-th trade's session): **Δ > 0 and
   the lower end of the 95 % interval of section 4 > 0 ⇒ CONFIRMED; otherwise NOT CONFIRMED.** The verdict is written once and
   never revised; trades after N are logged and change nothing.
4. SPY and QQQ are read separately: two verdicts, nothing pooled. No multiple-test correction is applied to the forward
   verdict (the hypothesis was pre-registered and passed its test; the ledger carries its count), and this is said beside each
   verdict. CONFIRMED in a name is QUEUE rule 6's "an edge that works" for that name.

## 6. Checkpoints (descriptive, no verdict)

After every **8 counted trades** in a name (8, 16, 24, … — about a year each), the forward report prints for that name: the
count, Δ at 1× and 2×, the share of trades with net > 0, the total, worst and best trade, and from the 16th trade on the
section-4 interval — each line labelled **"checkpoint — no verdict"**. A checkpoint never stops, extends or alters the test,
whatever it shows. Between checkpoints the report shows the count against N only.

## 7. Where it runs

The daily forward job's step 8 (`scripts/daily_forward.py`), on the official closes and 1-minute bars it already keeps, writing
append-only files under `research_notes/Edge search/H7_H8_H9/forward/`; the runner and its tests are committed after this file.
Until the runner is wired nothing is lost: the inputs are stored daily, and the runner computes every trade from 2026-10-28 in
calendar order under this rule unchanged.
