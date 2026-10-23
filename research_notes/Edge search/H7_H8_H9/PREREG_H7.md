# H7 — the pre-FOMC drift, SPY and QQQ stock: pre-registration

Written 2026-10-23 and committed together with PREREG_H8.md and PREREG_H9.md, those three files alone, before any H7 quantity
is computed. The test is run once, by `run_h7_h8.py` (in this folder, not committed with this file), on the data in section 4.
Nothing in this file changes after the run. The queue's line (`research_notes/Edge search/QUEUE.md`, additions `7ee1d6e`, entry
7): "pre-FOMC drift (Lucca & Moench 2015): long 100 shares SPY / QQQ ... exactly as its prereg states (the published window:
the 24 hours before the 2:00 pm announcement), scheduled FOMC dates only."

What has been looked at before this file:
- the Federal Reserve Board's FOMC calendar pages (the dates and release times in section 4);
- coverage only: on every scheduled statement date in each name's span, the session list has the date, the stored 1-minute
  file has a priced bar stamped 13:58, and the previous session has an official close in the source the rule names (SPY 77 of
  77 meetings 2017-02-01 → 2026-09-16; QQQ 114 of 114 meetings 2012-06-20 → 2026-09-16, of which 6 fall before 2013-03-20);
  none of these sessions is a half day;
- one sign-free figure for the power statement: the root-mean-square of every session's close-to-close return
  (`power_h7_h8.py`, section 5); it prints no mean and makes no FOMC cut.
No pre-FOMC return, no H7 P&L and no FOMC-day price difference of any kind has been computed on these data.

## 1. Hypothesis and mechanism

**H7.** On SPY and on QQQ, a long position held from the official close of the session before a scheduled FOMC statement to
one minute before the 2:00 pm statement makes money after costs.

**Why it might.**
- *Lucca & Moench, "The Pre-FOMC Announcement Drift", Journal of Finance 70(1) (2015) 329–371* (NY Fed Staff Report 512): the
  S&P 500 rose on average 49 bp in the 24 hours before scheduled FOMC announcements (2:00 pm on the day before to 2:00 pm, or
  the 15 minutes before the release), 1994–2011, t above 4.5 — about 80 % of the realised US equity premium over the sample,
  with nothing comparable before other macro releases or in Treasuries. Their reading: a premium for a risk that resolves at
  the announcement, or demand pressure before it; they leave the mechanism open.
- *Against — it decayed after publication.* Hu, Pan, Wang & Zhu (Journal of Financial Economics 2022), Table 2: the return
  from the close of day −1 to five minutes before the release was 35.81 bp in 1994–2000, 35.55 bp in 2001–2011 and **3.96 bp
  (t 0.74) in 2012–2018**. Kurov, Wolfe & Gilbert (Finance Research Letters 40, 2021): the drift "essentially disappeared after
  2015". Song (working paper, 2026; SPX and ES 2016–2023): open-to-release −0.03 %, only the overnight gap (+0.19 %) is
  significant, a structural break at the March 2016 meeting. Pan & Peng (working paper, June 2026): over September 1994 →
  December 2025 the close-to-release SPX return still averages 26.84 bp (t 6.74), carried by the years before 2012. Johannes,
  Kaeck & Seeger (Journal of Finance, forthcoming; abstract): no expected-return premium for FOMC event risk before the
  announcement. These figures come from the papers as summarised in the repository's notes (section 7); none is a read of
  this repository's data. **The prior for H7 is low**: the published record after 2011, on the index, is near zero.
- *What H7 adds*: the effect in dollars of a 100-share ETF position after costs, entered at a price one can trade at (the
  closing auction), exited at a stated minute, on 2013-03 → 2026-09, judged once.

## 2. The rule, exactly (one variant)

For each name (SPY, QQQ) and each included scheduled FOMC statement date A (section 4):
- **Entry.** Buy 100 shares at **C_prev = the official close of the session before A** (the date before A in the session list
  — for a two-day meeting, its first day). Official close: a session before 2025-10-13, ThetaData's stock EOD `close` whose
  `created` time in New York falls on that session (the reading of `research_notes/Compass H1/run_h1.py` `eod()`, the same
  files: `Compass H1/data/stock_eod_2012_2018.parquet`, `$SP/lake/stock_eod/year=2019`, `data_lake/thetadata/stock_eod/
  year=*`; two different closes for one session → no official close, excluded and listed); a session on or after 2025-10-13,
  Unusual Whales' daily bar `close` with `market_time == 'r'` (`audit_lib.uw_daily()`: the lake's `ohlc__1d` parts and
  `data/official_closes/uw_ohlc_1d_*.parquet`), as in H4.
- **Exit.** Sell the 100 shares at **X = the `close` of the 1-minute bar stamped 13:58 on A** (`$SP/theta/data/underlying/
  <name>/<A>.parquet`; bars are stamped at their start, so this is the last trade printed before 13:59:00 in that feed): the
  price at which a marketable sell sent at 13:59:00 is measured, one minute before the 2:00 pm statement — clear of the release,
  and of the seconds before it, when quotes widen. Chosen over the 14:00 print because that is the release itself. A missing or
  unpriced 13:58 bar → the meeting is excluded and listed; no other bar is substituted.
- **Which statements.** Scheduled meetings only (section 4's list); unscheduled meetings, conference calls, notation votes and
  the cancelled 2020-03-17/18 meeting are not FOMC statement dates here. **Only statements released at 2:00 pm**: the Fed
  released every scheduled statement at 2:00 pm from 2013-03-20 (its 2013-03-13 announcement); before that, statements came
  at 12:30 pm on press-conference days (e.g. 2012-12-12) and at another afternoon time otherwise, so a 13:59 exit is not "before
  the 2:00 pm announcement" for them. The six such meetings in QQQ's span (2012-06-20, 2012-08-01, 2012-09-13, 2012-10-24,
  2012-12-12, 2013-01-30) are excluded and listed. A statement on a day that is not a session (none found) would be excluded.
- **P&L of a trade, $:** `net = 100 × (X − C_prev) + 100 × DIV − COSTS`
  - DIV = the cash dividend per share whose ex-date is A (the holder at C_prev is paid it; the price falls by it at A's open),
    from H1's frozen table `research_notes/Compass H1/data/dividends.json` (sha256 `82c686294ff44dab705df2fd4a2295c1d258793c
    33742065012bf8ebe697c303`) — the dividend rule of H1. The table's last SPY ex-date is 2025-12-19 and QQQ's 2026-09-21; an
    A after a name's last tabled ex-date carries no dividend term. SPY's ex-dates are the third Friday of March, June, September
    and December (the session before when that Friday is a holiday) and the 2026 statements (Jan 28, Mar 18, Apr 29, Jun 17,
    Jul 29, Sep 16) fall on none of them, so nothing is lost. The report lists every trade with a dividend term.
  - COSTS = 100 × ($0.01 + $0.005): **$0.01 a share at entry** in the closing auction (H1's figure: commission at a retail
    per-share schedule, auction and clearing fees, FINRA TAF and the SEC fee on the sale) and **$0.005 a share at exit**, half
    of SPY's and QQQ's one-cent spread on a marketable sell at 13:59, over the bar's last print that X stands for. **1× =
    $1.50 a trade; 2× = $3.00 a trade**, reported beside it. The verdict is read at 1×.
  - No borrow (long only), no financing charge (as H1: the position is held in cash, and the forgone bill interest for one day
    is not charged; at a 4–5 % bill rate it is about 1–2 bp of the position, said beside the result in the report).

## 3. Statistic and pass rule

Per name, separately: the series is **every session of the name's calendar span** (SPY 2017-01-03 → 2026-10-22, QQQ
2012-06-01 → 2026-10-22; sessions = the dates on which QQQ's stored 1-minute file exists, H1's rule), in calendar order; S_i =
the net $ of the trade whose statement date A is session i (0 on every other session), N_i = 1 on a traded A, else 0.
- **Mean $ a trade after costs** = Σ S ÷ Σ N, at 1× and at 2×.
- **Interval**: the 20-session moving-block bootstrap over those calendar sessions (sessions with no trade contribute no
  trade) — `audit_lib.block_draws(n, 20, B=2000, seed=20261023)` (the backtest audit's library, read not edited; its rng is
  seeded with seed + 7919 × block), each draw's Σ W·S ÷ Σ W·N (`audit_lib.weights_from`), and `audit_lib.pct_ci` (the 2.5 and
  97.5 percentiles). The same draws serve 1× and 2× (paired). A draw with no trade (not expected: about 77 or 108 trades in a
  draw) counts as 0.
- **PASS, per name**: mean at 1× > 0 **and** the interval's lower end > 0. SPY and QQQ are judged separately; nothing is
  pooled; H7 has two verdicts and the ledger row records both.
- **Bonferroni (QUEUE rule 5).** The ledger count used is **m = 13**: the ledger's rows once H7, H8 and H9 are appended (H1,
  H3, H4, H5, H6, H7, H8, H9 = 8) plus the 5 pre-registered failures before the ledger (the 0DTE picker, the SPXW analogues,
  the 23-feature direction family, post-earnings drift in options, the after-hours rule). Both names count as tests: α =
  0.05 ÷ (2 × 13) = 0.1923 %, the two-sided percentile interval of the same 2,000 draws (the 0.0962 and 99.9038 percentiles —
  about 2 draws in each tail, so coarse; reported as computed). A pass is called an **EDGE** only if that interval's lower end
  is also above zero; even then not "an edge that works" before a forward N (QUEUE rule 6).
- Reported beside it, descriptive (no verdict): win rate (share of trades with net > 0), total, worst and best trade, the gross /
  dividend / cost pieces, **per calendar year** means at 1× and 2×, the means before and from the March 2016 meeting (Song's
  break: A ≤ 2016-01-27 and A ≥ 2016-03-16), the split of the gross into the night (C_prev → the 09:30 bar's open on A) and the
  day (that open → X), and a flagged-close sensitivity: the trades whose entry close is in
  `research_notes/Compass phase 3/backtest_audit/out/afterhours_close_check.csv` or differs from the entry session's 15:59 bar
  close by more than $0.25 (H1's flag), removed — same statistic and seed, no verdict.

## 4. Data, spans and the statement dates

- 1-minute bars: `$SP/theta/data/underlying/{SPY,QQQ}/<day>.parquet` (SP = `/tmp/claude-0/-home-user-georgeredo/
  c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`), ThetaData `stock_history_ohlc` 1m, 391 rows 09:30–16:00. QQQ priced from
  2012-06-01, SPY from 2017-01-03 (H1's stage 1).
- **The span (the verdict)**: every included statement whose previous session is in the name's span and whose date is on or
  before 2026-10-22 — **SPY 2017-02-01 → 2026-09-16 (77 meetings), QQQ 2013-03-20 → 2026-09-16 (108 meetings)**; the
  2026-10-28 statement is after the data. No study in this repository has read the pre-FOMC return of SPY or QQQ (section 7),
  so the whole span is the test; there is no exploration span and no other variant.
- **The statement dates.** Parsed on 2026-10-23 from https://www.federalreserve.gov/monetarypolicy/fomchistorical<YEAR>.htm
  (2012–2020; each meeting's "Statement" link gives the release date) and https://www.federalreserve.gov/monetarypolicy/
  fomccalendars.htm (2021–2026); kept with each source URL in `data/fomc_statements_2012_2026.json` (committed with the run).
  2022-01 → 2026-10-22: the 38 dates equal the FOMC_DECISION dates of `data/macro_events_2022_2027.json`. Release time: 2:00
  pm for every scheduled statement from 2013-03-20 (https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm;
  https://www.federalreserve.gov/monetarypolicy/fomcpresconf20130320.htm "Released March 20, 2013 at 2:00 p.m."), 12:30 pm on
  2012-12-12 (https://www.federalreserve.gov/monetarypolicy/fomcpresconf20121212.htm).
  Scheduled statements (month-day):
  - 2012: 01-25, 03-13, 04-25, 06-20, 08-01, 09-13, 10-24, 12-12 (not 2:00 pm; those in QQQ's span excluded, section 2)
  - 2013: 01-30 (not 2:00 pm, excluded), 03-20, 05-01, 06-19, 07-31, 09-18, 10-30, 12-18
  - 2014: 01-29, 03-19, 04-30, 06-18, 07-30, 09-17, 10-29, 12-17
  - 2015: 01-28, 03-18, 04-29, 06-17, 07-29, 09-17, 10-28, 12-16
  - 2016: 01-27, 03-16, 04-27, 06-15, 07-27, 09-21, 11-02, 12-14
  - 2017: 02-01, 03-15, 05-03, 06-14, 07-26, 09-20, 11-01, 12-13
  - 2018: 01-31, 03-21, 05-02, 06-13, 08-01, 09-26, 11-08, 12-19
  - 2019: 01-30, 03-20, 05-01, 06-19, 07-31, 09-18, 10-30, 12-11
  - 2020: 01-29, 04-29, 06-10, 07-29, 09-16, 11-05, 12-16 (the 03-17/18 meeting was cancelled)
  - 2021: 01-27, 03-17, 04-28, 06-16, 07-28, 09-22, 11-03, 12-15
  - 2022: 01-26, 03-16, 05-04, 06-15, 07-27, 09-21, 11-02, 12-14
  - 2023: 02-01, 03-22, 05-03, 06-14, 07-26, 09-20, 11-01, 12-13
  - 2024: 01-31, 03-20, 05-01, 06-12, 07-31, 09-18, 11-07, 12-18
  - 2025: 01-29, 03-19, 05-07, 06-18, 07-30, 09-17, 10-29, 12-10
  - 2026: 01-28, 03-18, 04-29, 06-17, 07-29, 09-16 (10-28 and 12-09 after the data)
  Not scheduled statements (excluded): 2013-10-16 and 2014-03-04 (unscheduled), 2019-10-04 (unscheduled call), 2020-03-03 and
  2020-03-15 (unscheduled meetings), 2020-03-19, 2020-03-23, 2020-03-31, 2020-08-27 and 2025-08-22 (notation votes).
- No vendor fetch is needed; none is made. Sessions after 2026-10-22 are not read.

## 5. Power (a priori)

`power_h7_h8.py` (committed with the run) computed one sign-free figure a name: the root-mean-square of the official close-to-
close return over every session on disk, 115.3 bp (SPY, 2,464 sessions) and 130.4 bp (QQQ, 3,618) — no mean, no FOMC cut (the
statement days are about 3 % of those sessions). Taking the H7 window (close → 13:58 next session) as one session's variance
(an upper figure: the pre-FOMC session is usually quiet), a trade's standard deviation is about 1.15–1.30 % of the position;
over 77 (SPY) and 108 (QQQ) trades the standard error of the mean is about 13 and 13 bp, so the **minimum detectable effect
(80 % power, 5 % two-sided) is about 37 bp (SPY) and 35 bp (QQQ) of the position** — $281 and $247 a 100-share trade at the
2026-10-22 closes ($763.96, $704.47), less at the lower prices of the earlier years. Lucca & Moench's 49 bp would be
detectable; the post-2011 published figure (about 4 bp) would not. **A FAIL here says little against a drift of the post-2011
size; a PASS needs one near the pre-2012 size.**

## 6. Outputs and the run

`run_h7_h8.py` (deterministic: files read in sorted order, seeded draws, no clock in the outputs) → `out/h7_trades.csv` (every
statement date per name: A, the previous session, C_prev and its source, the 09:30 open, X, the dividend, gross, costs, net 1×
and 2×, flags, the reason a meeting was excluded), `out/h7_h8_summary.json`, and `H7_H8_REPORT.md` with this file's sha256 at
the top. `verify_h7_h8.py` re-derives at least 30 H7 trades (15 a name, `random.Random(20261025)`) from the raw files with plain
loops and no code shared with `run_h7_h8.py` (polars only to read a Parquet file into Python lists) and must show 0 differences.
Run once; the verdict as it comes; then one ledger row is appended (`research_notes/Edge search/LEDGER.md`).

## 7. What earlier work read (searched on every ref, `git log --all -S`/`-i -S` for FOMC, pre-FOMC, Lucca, Moench, turn of
the month, month-end, month end, calendar effect, seasonal, day of week; and `git grep` of the trees at `75c29c9^`,
`origin/compass-research-2026-10-14` and HEAD)

No study in this repository computed the signed return of SPY or QQQ over the pre-FOMC window, by any rule. What touched FOMC
days, read and disclosed:
- **The price-action catalogue** (`048d33a`, `research/compass/intel/04_price_action_angles.md`): row C1 "Pre-FOMC drift …
  **Not tested** (direction); only D_FOMC straddles"; literature figures only (Lucca & Moench, Kurov et al.).
- **The atlas** (`0d706b6`, `06_price_action_atlas.md` §7, `results/price_action/calendar.csv`): on FOMC days 2017–2026 the
  full-day range, the |10:00 → close| move and the |gap| (unsigned medians; SPY's FOMC-day |gap| 0.157 % and 0.140 % against
  0.327 % and 0.290 % on all sessions). Sizes, not the signed drift; the gap there is the statement day's open against the
  previous close — part of H7's window — read unsigned.
- **V7** (`f098520`, `8bc3baf`, `f123778`): the 13:00 → 16:00 absolute move against the 13:00 straddle on FOMC days, SPXW
  2022-05 → 2026-10, SPY/QQQ/IWM descriptive — after the statement, unsigned. **H17 / the vol-filter study** (SPX 2017–2026):
  FOMC afternoons move 2.08× (unsigned, after 14:00). **A13 EVF, D_FOMC** (Fed-day straddles, options).
- **The research notes** (`7e4f0f2`, `2eaed11`, `research_notes/High win rate 0DTE lanes/filters_regimes_and_sizing.md`,
  `research_notes/Retail options edge sweep/earnings-events.md`): the literature in section 1 (Hu–Pan–Wang–Zhu, Song, Pan &
  Peng, Kurov et al., Johannes et al.) and option P&L on FOMC days (SPXW and SPY/QQQ 0DTE straddles 2025-06 → 2026-10); a
  captured, never-run idea for an event-eve SPXW straddle and a 1-DTE SPY call over the pre-FOMC night (record only).
- **Option studies cut by event days**: the backtest audit (`1ca1f0e`; condor P&L with and without FOMC sessions, 2022-11 →
  2026-10), the Compass features' V5 macro veto (`a2e14e4`, `2a49049`; option windows around 14:00, 2022 →), S15's skip.
- **Overnight reads that contain the night before a statement** (C_prev → A's open is part of H7): H1 (`38aca66`, `4a02144`;
  close → next open signed by the late-day move, 2012-06 → 2025-10-10), the after-hours study (`633fbff`; close → next open,
  2025-10-13 → 2026-10-21, as stock legs of option trades), S16a (`2430c9b`; overnight gaps 2017–2026). None was cut by FOMC
  date.
- **The published record on the same years** (section 1): Hu–Pan–Wang–Zhu measured close(−1) → release(−5 min) on the S&P 500
  for 2012–2018, Song open → release for 2016–2023, Pan & Peng through 2025 — the index, not these ETFs after costs, and read
  from the papers, not from this repository's data. The rule here was fixed from Lucca & Moench and the queue before any of this
  repository's FOMC-window returns were computed; the reader should weigh a result knowing the published post-2011 figure is
  near zero.
