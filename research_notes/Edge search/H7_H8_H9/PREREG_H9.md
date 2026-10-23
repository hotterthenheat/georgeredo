# H9 — the overnight drift, SPY and QQQ stock: pre-registration, FORWARD ONLY

Written 2026-10-23 and committed together with PREREG_H7.md and PREREG_H8.md, those three files alone, before any forward
session of H9 is read. The queue's line (`research_notes/Edge search/QUEUE.md`, additions `7ee1d6e`, entry 9): "overnight drift
(Cliff, Cooper & Gulen 2008; Kelly & Clark 2011): long 100 shares SPY / QQQ every close → next open. H1 already read its
components (longs and shorts at the close → open), so H9 is FORWARD-ONLY from 2026-10-23."

**No historical H9 result is computed, now or later.** Its historical read is spent (section 5): H1's long legs are H9's trades on
the sessions where the close was below the 15:00 price, and other studies read the close → open gap. The only figure taken from
history is the variance that sets N (section 4), read from H1's committed per-session file.

## 1. Hypothesis and mechanism

**H9.** On SPY and on QQQ, a long position held from the official close to the next session's 09:30 open, every session, makes
money after costs.

**Why it might.** Cliff, Cooper & Gulen ("Return differences between trading and non-trading hours: like night and day", 2008
working paper; 1993–2006) find that US equity index and ETF returns accrue overnight, the day's return near zero or negative;
Kelly & Clark ("Returns in trading versus non-trading hours: the difference is day and night", Journal of Asset Management
2011) report the same for index ETFs, overnight returns higher and less volatile; Lou, Polk & Skouras (JFE 2019) document the
overnight/intraday split in the cross-section. The repository's atlas (`0d706b6` §8) found the median of 43 names' mean overnight
return at +4.9 bp (2017–22) and +6.8 bp (2023–26). **Against**: the overnight premium is not stable across subperiods; a long
every night carries the market's whole equity premium, so a pass says that premium was earned overnight net of costs, not that
something beyond holding the index was found; and the closing-auction and opening prints carry costs that the literature's
close-to-open index returns do not.

## 2. The rule, exactly (one variant)

For each name (SPY, QQQ) and each session d on or after **2026-10-23** (every NYSE session; half days included — they have an
official close):
- **Entry**: buy 100 shares at **C = the official close of d** (market-on-close): Unusual Whales' daily bar `close` with
  `market_time == 'r'` (`audit_lib.uw_daily()` / the daily job's official closes, `data/official_closes/`), the source H4 and the
  forward job use from 2025-10-13.
- **Exit**: sell at **O = the `open` of the 1-minute bar stamped 09:30 on the next session** (market-on-open; the bar's first
  trade — H1's and the after-hours study's next-open source), from ThetaData `stock_history_ohlc` 1m bars of that session (the
  daily job's under files for SPY and QQQ).
- **P&L, $**: `net = 100 × (O − C) + 100 × DIV − COSTS`; DIV = the cash dividend per share whose ex-date is the next session (a
  long holder at the close is paid it; the price falls by it at the open), from the fund's declared distribution, kept with its
  source; COSTS = **$0.01 a share each way** (H1's figure) = **$2.00 a trade at 1×, $4.00 at 2×** (reported beside it). No
  borrow, no financing charge.
- A session's row is **complete** when C, the next session's 09:30 bar and the dividend calendar through the next session are
  on disk. A missing or unpriced input fails loudly for that session and nothing is substituted; the session is counted when
  its input arrives (rows are counted in calendar order: the count is the length of the complete prefix).

## 3. Statistic, N and the verdict

- Per name, separately; the series is the counted sessions in calendar order, S_i = net $ (every session trades).
- **Verdict only at exactly N = 7,940 counted sessions a name, on the first N alone**: mean $ a trade at 1× > 0 **and** the
  lower end of the 20-session moving-block bootstrap 95 % interval > 0 (`audit_lib.block_draws(N, 20, B=2000,
  seed=20261023)`, `audit_lib.pct_ci`) ⇒ **PASS**, else **FAIL** — per name, written once, never revised. Before N: no verdict,
  interim figures only, and no interval under 60 sessions.
- A PASS is called an **EDGE** only if its interval also clears zero at the Bonferroni level of the ledger count at that time
  (α = 0.05 ÷ (2 × m); m = 13 today: the ledger's 8 rows with H7, H8 and H9 plus the 5 pre-ledger failures) — QUEUE rule 5.

## 4. How N was set (the effect assumption, stated honestly)

- **Variance**: H1's committed file `research_notes/Compass H1/out/h1_sessions.csv` (`4a02144`), the long trades only (side
  +1; the close below the 15:00 price; H1's rule exits at the next 09:30 open, H9's exit): the standard deviation of (O − C) ÷ C
  is **66.08 bp (SPY, 1,086 long trades, 2017-01 → 2025-10)** and **79.51 bp (QQQ, 1,586, 2012-06 → 2025-10)** — 64.6 / 68.1 bp
  (SPY) and 81.8 / 87.9 bp (QQQ) in 2017–2021 / 2022–2025. These long legs are a subset of H9's nights selected by a late-day
  fall; their spread is taken as the spread of every night (an assumption; the subset's
  mean is not used).
- **The effect assumed**: **+2.5 bp of the position a night after costs** — about 2.8 bp gross, which is a 7 % a year equity
  premium (≈ 2.8 bp a session over 252) earned wholly overnight, as Cliff, Cooper & Gulen and Kelly & Clark describe, less the
  $2.00 of costs (≈ 0.26–0.28 bp at the 2026-10-22 closes). **Not assumed**: H1's long legs' mean (+$26.55 SPY, +$22.49 QQQ a
  trade at 1×, about 5–8 bp at their prices) — those nights were chosen by a late-day fall, so their mean carries any reversal
  as well as the drift, and they belong to a rule that failed; nor the atlas's cross-name means (+4.9 / +6.8 bp, 43 names, mostly
  single stocks, not these ETFs).
- **N** = ⌈((z₀.₉₇₅ + z₀.₈₀) × σ ÷ μ)²⌉ with z sum 2.8016 (80 % power, 5 % two-sided, independent nights): **SPY 5,484, QQQ
  7,940 → N = 7,940 sessions for both names** (the larger, so both are judged on the same sessions): about **31.5 years**.
  For the reader only (not the rule): at μ = 4 bp N would be 2,143 / 3,102; at μ = 6 bp, 953 / 1,379. The 20-session block
  interval widens little for overnight returns (their autocorrelation is small); N is not inflated for it.
- So the test is honest about its reach: at the effect the literature supports for an index, no verdict comes in any useful
  time; it is registered so that the forward record accrues under a rule fixed now.

## 5. What was read before (why forward only)

- **H1** (`38aca66`, `4a02144`): close → next 09:30 open, long when the close was below the 15:00 price, SPY 2017-01-03 →
  2025-10-10 and QQQ 2012-06-01 → 2025-10-10 — H9's trades on about half the nights, with their P&L (long legs +$22–27 a trade).
- **The after-hours study** (`633fbff`): the official close against the next 09:30 open on SPY/QQQ, 2025-10-13 → 2026-10-21.
- **S16a** (`2430c9b`): the overnight gap (the open against the previous last 1-minute close) on SPY/QQQ/IWM 2017-06 → 2026-10.
- **The atlas** (`0d706b6` §8): mean overnight and intraday returns across 43 names, 2017–2026.
- **H4's power script and test** read the previous official close against the 09:59 close (it contains the gap), 2012–2026.
Every historical session to 2026-10-22 is therefore spent for H9; only sessions from 2026-10-23 count.

## 6. The forward runner

The rule is fixed here; its forward runner is to be added to the daily job (an H9 row builder beside H5 and H6 in
`research_notes/Edge search/H5_H6/edge_forward.py`, its call in step 8 of `scripts/daily_forward.py`, a dividend calendar the job
carries, and tests). Until then nothing is lost: the official closes and both names' 1-minute bars are already stored by the
daily job for every session, and a later runner computes the rows from 2026-10-23 in calendar order under this rule unchanged.
No forward figure of H9 is read before the runner applies this rule to them.
