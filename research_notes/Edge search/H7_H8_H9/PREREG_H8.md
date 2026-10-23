# H8 — the turn of the month, SPY and QQQ stock: pre-registration

Written 2026-10-23 and committed together with PREREG_H7.md and PREREG_H9.md, those three files alone, before any H8 quantity
is computed. The test is run once, by `run_h7_h8.py` (in this folder, not committed with this file), on the data in section 4.
Nothing in this file changes after the run. The queue's line (`research_notes/Edge search/QUEUE.md`, additions `7ee1d6e`, entry
8): "turn of the month (Ariel 1987; Lakonishok & Smidt 1988; McConnell & Xu 2008): long 100 shares SPY / QQQ from the close of
the last trading day before month end ... exactly as its prereg states (the published window: the last trading day through
the third trading day of the new month)."

What has been looked at before this file: coverage only — the session list (QQQ's stored 1-minute files, H1's rule) gives every
month from 2012-06 to 2026-10, and every entry and exit session the rule names has an official close in the source the rule
names (SPY 117 of 117 turns, QQQ 172 of 172); which of those sessions are half days (listed in section 2); and the sign-free
root-mean-square of every session's close-to-close return (`power_h7_h8.py`, section 5; no mean, no turn-of-month cut). No
turn-of-month return and no H8 P&L has been computed on these data.

## 1. Hypothesis and mechanism

**H8.** On SPY and on QQQ, a long position held over the turn of the month — the last trading day of a month and the first
three trading days of the next — makes money after costs.

**Why it might.**
- *Ariel, "A monthly effect in stock returns", JFE 18(1) (1987) 161–174*: US index returns 1963–1981 accrue in the first half
  of the month, from the last trading day of the previous month. *Lakonishok & Smidt, "Are seasonal anomalies real? A
  ninety-year perspective", Review of Financial Studies 1(4) (1988) 403–425*: the DJIA 1897–1986 earns about 0.47 % over the
  four days from the last trading day of a month through the third of the next (their −1 to +3 window), against about 0.06 %
  for an average four days. *McConnell & Xu, "Equity Returns at the Turn of the Month", Financial Analysts Journal 64(2) (2008)
  49–64*: over 1926–2005 the US market's whole positive return came in the turn-of-month days (last day through the third);
  the effect persisted after 1987, is not confined to small stocks or to December/January, and appears in 31 of 35 countries.
  The proposed mechanism: payments at month end (wages, pension and fund contributions) invested at the turn, and portfolio
  rebalancing or window dressing near month end. (The Lakonishok & Smidt and McConnell & Xu figures are as their papers are
  widely cited; I could not re-read either text from this container, and the catalogue `048d33a` quotes only McConnell & Xu's
  abstract — "persisted in 1987–2005", "31 of 35 countries". They set the hypothesis' sign, not any parameter of the rule
  beyond the published window.)
- *Against.* Calendar anomalies in general shrink after publication (Schwert 2003; McLean & Pontiff 2016, about −58 % after
  publication). The repository's catalogue rates the turn of the month "Low" priority (row C3, `048d33a`). I know of no
  peer-reviewed estimate for SPY or QQQ after 2012 that I can verify from this container, so none is quoted. The prior is
  modest: a long-only rule carries the market's own drift (about 2–3 bp a session over these years), so even no special effect
  would leave a small positive mean — the test asks whether it clears zero with costs and the interval, not whether it beats
  other days.

## 2. The rule, exactly (one variant)

Sessions = the dates on which QQQ's stored 1-minute file exists (one on every NYSE session, none on a holiday or closure; H1's
rule); SPY uses the same list. For each calendar month M with sessions, and its next month M′:
- **L(M)** = the last session of M; **E** = the session before L(M) (the second-to-last session of M); **X** = the third session
  of M′.
- **Entry: buy 100 shares at the official close of E. Exit: sell them at the official close of X.** The position is held over
  the closes of L(M), the first, the second and the third sessions of M′ — the four daily returns of Lakonishok & Smidt's −1
  to +3 window (the last trading day through the third trading day of the new month), measured close to close as they are.
  Both orders fill in the closing auction (market-on-close).
- Official close, as H1, H4 and H7: a session before 2025-10-13, ThetaData's stock EOD `close` whose `created` time in New York
  falls on that session (`run_h1.py` `eod()`'s files); on or after 2025-10-13, Unusual Whales' daily bar `close` with
  `market_time == 'r'` (`audit_lib.uw_daily()`). Two different closes for one session, or none → the turn is excluded and
  listed; no other price is substituted.
- **Half days stay in** (each has an official close, its 13:00 closing auction): entries on 2015-11-27 and 2020-11-27 (the
  second-to-last session of November), exits on 2013-07-03, 2014-07-03, 2019-07-03, 2024-07-03 and 2025-07-03 (the third
  session of July); half days inside other windows are simply held through.
- **The turns in the span**: a turn is in a name's span when E is on or after the name's first session with an official close
  and X is on or before 2026-10-22 — **SPY: M = 2017-01 → 2026-09 (117 turns; E 2017-01-30 → X 2026-10-05); QQQ: M = 2012-06 →
  2026-09 (172 turns; E 2012-06-28 → X 2026-10-05)**. (SPY has no official close on disk before 2017-01-03, and May 2012's
  sessions are not on disk.) Consecutive turns never overlap.
- **P&L of a trade, $:** `net = 100 × (C_X − C_E) + 100 × DIV − COSTS`
  - DIV = the sum of the cash dividends per share whose ex-date is a session after E and on or before X (the holder at E's
    close is paid them), from H1's frozen table `research_notes/Compass H1/data/dividends.json` (sha256
    `82c686294ff44dab705df2fd4a2295c1d258793c33742065012bf8ebe697c303`), H1's rule. The table's last SPY ex-date is
    2025-12-19 and QQQ's 2026-09-21; SPY's ex-dates fall on or about the third Friday of the month (the 15th to the 21st) and
    QQQ's in the week after it, so no turn-of-month window can hold one; the report lists any trade that does.
  - COSTS = 2 × 100 × $0.01: **$0.01 a share each way** in the closing auction (H1's figure). **1× = $2.00 a trade; 2× = $4.00**,
    reported beside it. The verdict is read at 1×.
  - No borrow (long only), no financing charge (as H1; the forgone bill interest over the 4 sessions, about 6–8 calendar days,
    is about 0–9 bp of the position over 2012–2026's bill rates — said beside the result in the report, not charged).

## 3. Statistic and pass rule

Per name, separately: the series is **every session of the name's calendar span** (SPY 2017-01-03 → 2026-10-22, QQQ
2012-06-01 → 2026-10-22), in calendar order; S_i = the net $ of the turn whose entry session E is session i (0 on every other
session), N_i = 1 on an entry session, else 0.
- **Mean $ a trade after costs** = Σ S ÷ Σ N, at 1× and at 2×.
- **Interval**: the 20-session moving-block bootstrap over those calendar sessions (sessions with no trade contribute no
  trade) — `audit_lib.block_draws(n, 20, B=2000, seed=20261023)`, each draw's Σ W·S ÷ Σ W·N (`audit_lib.weights_from`),
  `audit_lib.pct_ci` (2.5 and 97.5 percentiles); the same draws for 1× and 2× (paired); a draw with no trade counts as 0.
- **PASS, per name**: mean at 1× > 0 **and** the interval's lower end > 0. SPY and QQQ are judged separately; nothing is
  pooled; H8 has two verdicts and the ledger row records both.
- **Bonferroni (QUEUE rule 5)**: m = 13 — the ledger's 8 rows once H7, H8 and H9 are appended plus the 5 pre-ledger
  failures; α = 0.05 ÷ (2 × 13) = 0.1923 %, the 0.0962 and 99.9038 percentiles of the same 2,000 draws (about 2 draws a tail;
  coarse, reported as computed). A pass is an **EDGE** only if that lower end is also above zero, and not "an edge that works"
  before a forward N (QUEUE rule 6).
- Reported beside it, descriptive (no verdict): win rate, total, worst and best trade, the gross / dividend / cost pieces, per
  calendar year means at 1× and 2× (the year of E), and a flagged-close sensitivity (trades whose entry or exit close is in
  `backtest_audit/out/afterhours_close_check.csv` or differs from that session's 15:59 bar close by more than $0.25 — H1's
  flag — removed; same statistic and seed; no verdict).

## 4. Data and span

- Official closes as in section 2; sessions from QQQ's 1-minute files (`$SP/theta/data/underlying/QQQ/*.parquet`, SP =
  `/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`); the 15:59 bar close for the flag only.
- **The whole span above is the test** (the verdict): no study in this repository has read the signed turn-of-month return
  of SPY or QQQ (section 6), so there is no exploration span. Sessions after 2026-10-22 are not read. No vendor fetch is made.

## 5. Power (a priori)

`power_h7_h8.py` (committed with the run): the root-mean-square of the official close-to-close return over every session on
disk, 115.3 bp (SPY, 2,464 sessions) and 130.4 bp (QQQ, 3,618) — sign-free, no turn-of-month cut (those sessions are about a
fifth of the total). Over four sessions a trade's standard deviation is about 2.3 % (SPY) and 2.6 % (QQQ) of the position; over
117 and 172 trades the standard error of the mean is about 21 and 20 bp, so the **minimum detectable effect (80 % power, 5 %
two-sided) is about 60 bp (SPY) and 56 bp (QQQ) of the position** — $456 and $392 a 100-share trade at the 2026-10-22 closes,
less at earlier prices. Lakonishok & Smidt's 0.47 % (and an ordinary four days' drift of about 0.1 %) sit below it: **this test
can detect only an effect larger than the published one; a FAIL is weak evidence against the published size.**

## 6. What earlier work read (the same search as PREREG_H7.md §7, every ref)

No study in this repository computed the signed return of SPY or QQQ over the turn of the month, by any rule. What touched
month ends, read and disclosed:
- **The price-action catalogue** (`048d33a`): row C3 "Turn of the month … **Not tested** for returns (month-end variance:
  S10)"; literature only.
- **The atlas** (`0d706b6`, §7, `results/price_action/calendar.csv`): "month end" (the last session) and "first session of
  month" cuts of the full-day range, |10:00 → close| and |gap| for SPY and QQQ, 2017–2026 — unsigned medians. Two of H8's four
  sessions (the last and the first) were read for size, not direction.
- **V7** (`8bc3baf`, `f123778`): the 13:00 → 16:00 absolute move on month-end sessions (SPXW 2022-05 → 2026-10; SPY/QQQ
  descriptive) and an exploratory month-end 13:00 straddle; **V8** (`e4e4cea`): month-end 13:00 long straddles on SPXW
  2017-06 → 2022-04 and SPY 2017-06 → 2022-10 (rejected) — options and unsigned afternoon moves on the last session.
  **H17 / the vol-filter study**: SPX month-end afternoons 1.33× (unsigned). **S15, H15**: month-end skips for short premium.
- **S14** (`fe93f87`, 2024-01 → 2026-10): cross-sectional single-name momentum with month-end rebalancing — single names, 21
  sessions, not the index turn.
- **Overnight reads containing turn-of-month nights**: H1 (close → next open signed by the late-day move, 2012-06 → 2025-10-10),
  the after-hours study (close → next open, 2025-10-13 → 2026-10-21), S16a (overnight gaps 2017–2026) — none cut by month.
- The rule here was fixed from Lakonishok & Smidt's window and the queue, before any turn-of-month return of these ETFs was
  computed.

## 7. Outputs and the run

`run_h7_h8.py` → `out/h8_trades.csv` (every turn per name: M, E, L(M), X, the two closes and their sources, the dividend, gross,
costs, net 1× and 2×, flags, the reason a turn was excluded), `out/h7_h8_summary.json`, `H7_H8_REPORT.md` (this file's sha256
at the top). `verify_h7_h8.py` re-derives at least 30 H8 trades (15 a name, `random.Random(20261025)`) from the raw files with
plain loops and no code shared with the run, and must show 0 differences. Run once; the verdict as it comes; then one ledger row.
