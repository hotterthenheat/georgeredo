# H5 — the SPY late-day straddle premium over SPXW: a FORWARD-ONLY pre-registration

Written Thursday 2026-10-22, 22:50–23:59 New York, committed together with `PREREG_H6.md` and nothing else, and pushed
before any H5 quantity is computed on any session. **H5 is tested on forward sessions only, from Friday 2026-10-23**: the
first full session after this commit. No historical H5 result is computed, now or later — the historical read of this
gap is spent (`research_notes/Compass phase 3/spxw_prereg/SPXW_REPORT.md`, commit `6bb230e`, section 9). The code that
computes it is written after this file, in this folder, and wired into the daily forward job (`scripts/daily_forward.py`)
as its step 8; nothing in this file is changed after a forward row exists.

The queue's definition (`research_notes/Edge search/QUEUE.md`, commit `a49c35b`), verbatim: "H5 — the SPY/QQQ late-day
extrinsic premium over SPXW (measured in research_notes/Compass phase 3/spxw_prereg/): sell the SPY/QQQ 15:30
at-the-money straddle and buy the SPXW one in matched notional, flat 15:58 — only if a cash account's assignment can be
avoided by the 15:58 exit; forward-only test (the historical read is spent)." The queue's rules 1–6 apply; rule 2's
"forward sessions from 2026-10-22" is met by starting at 2026-10-23, the first session after this file.

**What was looked at to write this file** (all committed before it): QUEUE.md and LEDGER.md (`0418fa2`); SPXW_REPORT.md
and PREREG_SPXW.md (`6bb230e`, `2820bb4`); backtest_audit/AFTERHOURS.md (`633fbff`); `research_notes/Compass
features/FORWARD_RULE.md` and `forward/forward_features.py` (how a forward rule with N is set and appended);
PREREG_FEATURES.md section 2.6 (fees); `scripts/daily_forward.py`, `scripts/paper_backtest.py` (ParquetSource,
chain_rows, FETCH_CHAINS), `scripts/paper_tracker.py` (Chain); `audit_lib.py` (block_draws, pct_ci, SEED). **No price,
quote or P&L of the H5 package has been computed on any session**: the only numbers used below are the committed
report's published means and intervals.

---

## 1. Hypothesis and mechanism

**H5.** On a full session, a package that SELLS the SPY same-day at-the-money straddle at 15:30 and BUYS the SPXW
same-day at-the-money straddle at 15:30 in matched notional, and closes all four legs at 15:58, makes money on average
after crossing every spread and paying fees.

**Mechanism (the premise).** SPXW_REPORT.md section 9 found, in both of its historical periods, that late in a 0DTE
session SPY's at-the-money straddle is priced richer, relative to the move SPY then makes to its official close, than
SPXW's is relative to SPX's move: the SPY − SPXW gap in (extrinsic − realized move) is +1.82 / +1.97 bps of spot at 15:30
and +3.01 / +4.09 bps at 15:58 (development 2022-11-11 → 2024-12-31, 530 common sessions / selection 2025-01-02 →
2026-10-09, 441), every block-20 interval clear of zero. A candidate cause, stated there and not measured: SPY's options
are American and physically settled, so a writer carries the after-hours exercise and assignment the official-close
measure leaves out (AFTERHOURS.md); SPXW is European and cash-settled. The package sells the rich side and buys the
cheaper side, so the common move largely cancels and what is left is the difference in how the two straddles' extrinsic
values change between 15:30 and 15:58.

**The mapped prior is NEGATIVE, stated before anything is computed.** If each straddle's price is its fair value plus an
excess, and the fair value is a martingale, the package's expected P&L at the mid from 15:30 to 15:58 is (the SPY − SPXW
excess at 15:30) − (the same excess at 15:58), because the exit buys back the SPY straddle and sells the SPXW one at
15:58's excess. With the report's figures that is 1.82 − 3.01 = **−1.19 bps** (development) and 1.97 − 4.09 = **−2.12
bps** (selection): the gap WIDENS into 15:58, so a package flat at 15:58 pays more of it back than it collected. After
costs (section 4: about 1.3 bps of spreads and 0.42 bps of fees) the mapped expectation is about **−2.9 to −3.8 bps of
the package's notional, about −$226 to −$298 a package** at SPY $775. The mapping is approximate (the report measured
extrinsic against the move to the official close, not a 15:30 → 15:58 trade, and its realized move is a proxy for fair
value), but its sign is not close. **H5 is expected to fail.** It is registered because the queue fixed it, because the
15:30 → 15:58 path of the gap has never been traded or read, and because a forward-only test costs no data already spent.

## 2. The package (the rule, exactly)

**Sessions.** Every full NYSE session from 2026-10-23 on (the recorder's calendar: `eod_recorder` HOLIDAYS / HALF_DAYS;
half days excluded, as `paper_tracker.is_tracked_day`), on which the daily forward job completes the session (section 5).
One package a session at most.

**Data** (all already fetched by the daily forward job every session; nothing new is asked for H5): the SPY and SPXW
same-day 1-minute chains (`data_full/chains/SPY|SPXW/<D>.parquet`), SPY's 1-minute bars (`data/underlying/SPY/<D>.parquet`)
and SPX's 1-minute prints (`data/index/SPX/<D>.parquet`), read through `paper_backtest.ParquetSource` and `chain_rows`
into `paper_tracker.Chain` (a quote stands when both sides are there, ask ≥ bid ≥ 0). "The quote at 15:30" is the row
stamped 15:30 (minute index 360); "at 15:58" the row stamped 15:58 (388).

**Spot.** SPY: the close of the bar stamped 15:29 (the repository's convention, the bar stamped m − 1). SPX: the print
stamped 15:30. At the exit (used only by the missing-quote rule below): SPY's bar stamped 15:57, SPX's print stamped 15:58.

**Strikes.** K_SPY = `Chain.nearest(S_SPY)` on SPY's 15:30 chain and K_SPXW = `Chain.nearest(S_SPX)` on SPXW's 15:30 chain:
the strike nearest spot among those with a call and a put quoted, both asks > 0; a tie goes to the lower strike. The
same two strikes are closed at 15:58 (no re-centring).

**Size: 10 SPY straddles against 1 SPXW straddle, fixed.** 10 SPY straddles cover 1,000 shares; one SPXW straddle covers
100 × SPX. Matched notional is n_SPXW = round(10 × 100 × S_SPY ÷ (100 × S_SPX)) = round(10 × S_SPY ÷ S_SPX) per 10 SPY
straddles, which is 1 for any SPX/SPY ratio between 6.67 and 20; the ratio has stood at 10.03 (the SPXW report's median in
every period), so the SPY side is about 0.3 % smaller in notional. The 10 : 1 is never resized.

**Entry, 15:30.** SELL 10 SPY K_SPY calls and 10 SPY K_SPY puts at their 15:30 BIDS; BUY 1 SPXW K_SPXW call and 1 SPXW
K_SPXW put at their 15:30 ASKS. No trade that session (a row with N = 0 and the reason, counted as a session) when
K_SPY or K_SPXW does not exist, or either SPY bid is 0 (nothing can be sold for nothing).

**Exit, 15:58.** BUY BACK the 20 SPY contracts at their 15:58 ASKS; SELL the 2 SPXW contracts at their 15:58 BIDS. All four
legs are closed; nothing is held into the close.

**A missing exit quote** (the leg has no two-sided quote at 15:58 though the chain file and minute are there) is never
skipped and never filled from another minute: a SPY leg to buy back is valued at its intrinsic value on the exit spot
plus that leg's own 15:30 spread (ask − bid); an SPXW leg to sell at max(0, intrinsic on the exit spot − its 15:30
spread). The row is flagged. (H3's rule, `PREREG_H3.md`.) A missing FILE, a missing minute of a chain, a missing spot bar
or print is a data failure: the job fails loudly for that session and writes nothing (section 5).

**P&L of a package, $** = 100 × [10 × (bid_C,SPY,15:30 + bid_P,SPY,15:30 − ask_C,SPY,15:58 − ask_P,SPY,15:58)
− (ask_C,SPXW,15:30 + ask_P,SPXW,15:30 − bid_C,SPXW,15:58 − bid_P,SPXW,15:58)] − fees.

**Fees** (PREREG_FEATURES.md section 2.6; PREREG_SPXW.md section 4): SPY **$0.68748** a contract each way (20 contracts
in, 20 out: $27.4992 a package); SPXW **$1.18748** a contract when that leg's fill price is under $1.00 and **$1.27748** at
$1.00 or more (the leg's own fill: the ask it was bought at, the bid it was sold at). Not included: FINRA's TAF and the
SEC's Section 31 fee (cents), any broker fee.

## 3. Assignment, the account, and QQQ

- **Assignment is avoided by the 15:58 exit.** An exercise notice is assigned by OCC against short positions OPEN AT THE
  END of the day it is filed; a SPY short bought back at 15:58 is not open then, so it cannot be assigned, and nothing is
  held through the close into the after-hours window AFTERHOURS.md measured. The queue's condition is met in that sense.
- **But the package is not a cash-account trade.** A short SPY call and put are uncovered writes; a long SPXW straddle is
  a different product and is not recognised as cover by strategy-based margin, so the package needs a margin account
  approved for uncovered writing (portfolio margin would net them). This is said, not modelled.
- **QQQ is not in H5.** The daily forward job fetches SPY, QQQ and SPXW chains, SPY/QQQ bars and SPX/VIX prints — no NDX or
  NDXP. A QQQ-against-SPXW package is a cross-index hedge (the report's QQQ realized moves stand 2.7–5.1 bps above SPXW's
  at 15:00 and 15:30), not the matched cash-settled pair the hypothesis needs. QQQ against NDXP would need an NDXP chain and
  NDX prints in the job: a new pre-registration, not this one.

## 4. The statistic, the interval, and the pass rule

- Per counted session s (calendar order from 2026-10-23): S_s = the package P&L in dollars (0 when no trade), N_s = 1 if a
  package was traded, else 0.
- **Δ = Σ S_s ÷ Σ N_s over the counted sessions = the mean dollars per package after all costs.**
- **The interval: the 20-session moving-block bootstrap** of `audit_lib.block_draws(n, 20)` (2,000 draws, `audit_lib.SEED`
  = 20261022, its generator seeded 20261022 + 7919 × 20), the percentile 95 % interval (`audit_lib.pct_ci`) of
  Σ S_b ÷ Σ N_b. None is printed under 60 sessions.
- **PASS (the queue's rule 4) at exactly N counted sessions, on the first N only: Δ > 0 and the interval's lower end > 0.**
  Otherwise FAIL. The verdict is written once and never revised; sessions after N are logged and do not change it.
- **No verdict before N**: interim figures may be printed, each labelled "no verdict"; no early stop, no extension, no
  change of N, rule, size, minutes, costs or statistic once a forward row exists.
- Logged beside each row for reading only (never judged): the package at the mids, the spreads paid, each leg's quotes.

## 5. Counting

A forward session **counts** only when it is complete: the daily forward job's fetch, verify and merge passed, its replay
came out whole (the job's step 5), and the H5 row is written. A session whose inputs are missing fails loudly
(`DAILY-FORWARD FAIL <day> edge-…`, the job's exit 1) and writes no H5 row; it is not counted and not replaced; the next
complete session is the next count. A no-trade session (section 2) counts as a session with N_s = 0.

## 6. N, and its basis

**N = 1,326 counted sessions** (about 5.3 years at 252 sessions a year).

Because no historical read of this package is allowed, the effect and the variance are taken from SPXW_REPORT.md's
committed figures (section 9, "The gaps, on the sessions all three share", the SPY rows), mapped as follows:

1. **The per-session standard deviation of each gap series** is recovered from its published block-20 interval:
   sd = (upper − lower) ÷ (2 × 1.959964) × √n. At 15:30: development (2.28 − 1.40) → 5.17 bps, selection (2.72 − 1.25) →
   7.88 bps; at 15:58: development (3.71 − 2.38) → 7.81 bps, selection (5.13 − 3.20) → 10.34 bps. Because they come from
   block-20 intervals, they already carry the series' autocorrelation.
2. **The package's per-session σ** is taken as √(sd₁₅:₃₀² + sd₁₅:₅₈²) — the two gaps' correlation set to zero (not
   published; a positive correlation would lower σ, to 9.35 bps at 0.5) — in the period that gives the larger value,
   selection: **σ = 13.00 bps of the package's notional** (≈ $1,007 at SPY $775). Development gives 9.37 bps.
3. **The effect.** The mapped effect is negative (section 1): there is no positive effect in the committed figures to
   power against, so N is set on an **ASSUMED effect: δ = +1.0 bp of the package's notional after costs** (≈ +$78 a
   package at SPY $775). Reasons: it is about half the 15:30 gap itself (1.82–1.97 bps), the most the package could
   collect if the 15:58 excess vanished, and it is the smallest net effect worth trading on a $775,000 package (it must
   clear 1.72 bps of costs on top). It is not a forecast — the forecast is section 1's negative number.
4. **N0 = ⌈((1.959964 + 0.841621) × σ ÷ δ)²⌉ = ⌈(2.801585 × 13.00 ÷ 1.0)²⌉ = 1,326**, at least 60 (the floor of
   FORWARD_RULE.md; not binding). The normal approximation is used directly (σ already block-adjusted); no simulation,
   since no historical series of the package may be read to resample.

**Costs in the mapping** (bps of the package's notional, 1,000 × S_SPY): spreads 2 × (w_SPY + w_SPXW), with each ATM
quote 0.2–0.45 bps of spot wide (SPXW_REPORT.md section 9), so 0.8–1.8 bps, 1.3 central; fees $32.52 a package
(SPY $27.50, SPXW four legs at $1.27748 in and the mean of the two tiers out) = 0.42 bps at SPY $775.

**Sensitivity (N, sessions)** — the same formula; the rule's N is the bold one:

| δ after costs (bps) | σ = 8 | σ = 9.37 (development) | σ = 11.2 | σ = 13.00 (selection) | σ = 16 |
|---|---|---|---|---|---|
| 0.5 | 2,010 | 2,755 | 3,939 | 5,304 | 8,038 |
| 1.0 | 503 | 689 | 985 | **1,326** | 2,010 |
| 2.0 | 126 | 173 | 247 | 332 | 503 |

The hypothesis's own best case under the mapping — the whole 15:30 gap (mean of the two periods, 1.895 bps) collected at
the mid, minus 1.72 bps of costs, = +0.175 bp — would need 43,096 sessions: a pass at N = 1,326 would mean the package is far better than the
committed figures imply. **At the rule's N, about 5.3 years, a verdict is reachable but late; the expected verdict is
FAIL.**

## 7. Not modelled, said

The size a 15:30 / 15:58 order could fill at the NBBO (the ATM quotes show sizes; they are logged, not used); a complex
order filling inside the summed NBBO; SPY's closing-auction risk (none: nothing is held to the close); margin and its cost;
the SPY side's 0.3 % smaller notional; the strike-grid mismatch (SPY strikes are $1 apart, SPXW's 5 points), which is part
of the package's risk and is in its P&L as traded.

## 8. Where it is written

`research_notes/Edge search/H5_H6/forward/h5_sessions.csv` (one row a counted session, append-only, never rewritten),
the report `forward/EDGE_FORWARD_REPORT.md` (rewritten each run: counted / N, interim figures labelled "no verdict"), and
the verdict, once N is reached, in `forward/verdicts.json` (written once). LEDGER.md gets one row: "registered, forward —
no verdict before N = 1,326 sessions".
