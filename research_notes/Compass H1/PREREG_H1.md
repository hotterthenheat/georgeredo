# H1 — overnight reversal of the late-day move, SPY and QQQ stock: pre-registration

Written 2026-10-22, committed alone, before any H1 quantity is computed. The test is run once, by `run_h1.py` (in this folder,
not committed with this file), on the data listed in section 4; nothing in this file is changed after the run. The owner's
spec, verbatim: "Run H1 now, pre-registered, stock only. Commit the prereg alone before computing any result; test once. Rule: at
the official close, short 100 shares if the close is above the 15:00 price, long if below, flat if equal. Exit at the next
session's 09:30 open, same source as the after-hours study. SPY and QQQ reported separately. Data: every session before
2025-10-13. … Costs: state an auction-fill cost per share each way in the prereg; report it at 2x too. Pass: mean $ per trade
after costs > 0 with the 20-session block-bootstrap interval clear of zero, in each name. No variants."

What has been looked at before this file: the inputs' coverage only (which files exist, which are all-NaN, which sessions have a
priced 14:59 bar in QQQ's files, the EOD rows' dates and duplicates, the dividend table's dates against the session list). No
close, 15:00 price, next open or difference of them has been computed for H1. Section 7 lists what earlier studies already read
on these same data.

## 1. Hypothesis and mechanism

**H1.** On SPY and on QQQ, the move from 15:00 to the official close partly reverses between the official close and the next
session's 09:30 open: a stock position against that move, opened at the official close and closed at the next open, makes money
after costs.

**Why it might.** Late-day flows that are not about information push the price, and the overnight gap gives part of it back:
- *Hedging demand.* Baltussen, Da, Lammers & Martens ("Hedging Demand and Market Intraday Momentum", JFE 142 (2021) 377–403) find,
  in over 60 futures from 1974 to 2020, that the return over the rest of the day (prior close to the last 30 minutes) positively
  predicts the last-30-minute return; they tie it to gamma hedging by option market makers and leveraged-ETF rebalancing (much
  stronger on days when dealers' net gamma is negative), and report that the predictability **reverts over the following
  days** — the signature of price pressure rather than news. H1 asks whether a reversal of the late move is visible in the very
  next interval, close to next open, on the two ETFs. Their test is futures-based, their late window is 15:30–16:00 and their
  reversal horizon is days; H1's window (15:00 → close) and horizon (one night) are not theirs.
- *Closing-auction pressure.* Bogousslavsky & Muravyev ("Who Trades at the Close?", working paper, 2020 draft; read through the
  repo's literature note in commit `3e86683`) find closing prices deviate from the 16:00 midquote by about 8 bp on average
  (3.6 bp for large ETFs such as SPY and QQQ) and that the deviation reverts by half shortly after the close and fully overnight.
  Hu & Murphy (Management Science) find larger reversals after larger last-minute NYSE imbalances.
- *Clienteles.* Lou, Polk & Skouras ("A Tug of War: Overnight versus Intraday Expected Returns", JFE 2019) document, in the
  cross-section of single stocks, persistent overnight and intraday return components with opposite signs across the two
  periods (a cross-period reversal), which they attribute to different investor clienteles trading at the open and during the
  day. It is a cross-sectional result about stocks, not a test on index ETFs; it motivates, it does not predict H1's sign on SPY.
- *Against.* Baltussen, Da & Soebhag ("End-of-Day Reversal", working paper 2025) find the prior-close-to-15:00 return
  negatively predicts the last half hour **in the cross-section** while the market (time-series) component shows momentum; the
  repo's own S12 (commit `2430c9b`) found no last-half-hour momentum on SPY, QQQ or IWM 2017–2026. Overnight returns on US
  equity indices have a positive average historically (most of the equity premium has accrued overnight in several samples;
  not stable across subperiods), so a rule that is long more often than short carries that drift; the result is reported as
  it comes, with the long and short trades' means beside it (descriptive).

## 2. The rule, exactly

For each name (SPY, QQQ) and each signal session d in the span (section 4):
- **C** = the official close of d = the `close` of ThetaData's stock EOD row for the name whose `created` time, in New York, falls
  on d (the source the after-hours study and `audit_lib.theta_eod` / `run_audit.official_closes` use for every session before
  2025-10-13). Two EOD rows with different closes for one name-session → no official close (excluded, listed). None were found
  2012→2025 (coverage check, the 2012–2018 rows fetched for H1 included).
- **P15** = the "15:00 price" = the `close` of the 1-minute bar stamped **14:59** in the stored 1-minute files
  (`$SP/theta/data/underlying/<name>/<d>.parquet`, ThetaData `stock_history_ohlc` 1m, venue nqb). Bars are stamped at their
  start, so this is the last trade printed before 15:00:00 in that feed — the last price knowable at 15:00. Chosen over the open
  of the 15:00 bar because that is a trade after 15:00 and part of the move being measured. A 14:59 bar with no price (NaN or
  null) → excluded, listed; no earlier bar is substituted.
- **Side**: C − P15 ≥ $0.00005 → **short** 100 shares at C; P15 − C ≥ $0.00005 → **long** 100 shares at C; otherwise (equal to
  the fourth decimal) → **flat**, no trade (the session stays in the series with P&L 0 and no trade).
- **Exit O** = the next session's 09:30 open = the `open` of the bar stamped **09:30** in the next session's stored 1-minute file
  for the same name — exactly `afterhours.py`'s `bar_at(<underlying>/<name>/<next>.parquet, 9, 30, 'open')` (the after-hours
  study's next-open source). The next session = the next date in the session list (below). A missing or unpriced 09:30 bar →
  the session is excluded and listed; no later bar is substituted.
- **Sessions**: the dates on which QQQ's stored 1-minute file exists (one file every NYSE session from 2012-06-01, none on a
  holiday; the 2012-10-29/30, 2018-12-05 and 2025-01-09 closures are not sessions). SPY uses the same list.
- **Half days** are excluded and listed: 2012-07-03, 2012-11-23, 2012-12-24, 2013-07-03, 2013-11-29, 2013-12-24, 2014-07-03,
  2014-11-28, 2014-12-24, 2015-11-27, 2015-12-24, 2016-11-25, 2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23, 2018-12-24,
  2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03,
  2024-11-29, 2024-12-24, 2025-07-03 (the market closes at 13:00, so no 15:00 price exists; the coverage check found QQQ's 14:59
  bar unpriced on exactly these sessions plus 2013-08-22, the Nasdaq halt, which drops out by the 14:59 rule above). A half day
  as the *next* session is a normal exit (it opens at 09:30).
- **P&L of a trade, $** (100 shares; side +1 long, −1 short):
  `net = side × 100 × (O − C) + side × 100 × DIV − BORROW − COSTS`
  - DIV = the cash dividend per share whose ex-date is the next session (a long holder at the close is paid it; a short owes it;
    the price falls by it at the open). Source, frozen before this commit: `data/dividends.json` (sha256
    `82c686294ff44dab705df2fd4a2295c1d258793c33742065012bf8ebe697c303`; SPY from Yahoo's chart events — Nasdaq serves no SPY
    history; QQQ from Nasdaq's dividend history, Yahoo for the two 2012 rows Nasdaq lacks; raw answers in
    `data/dividends_raw/`; every ex-date in the span is a session). This is part of the stock position's P&L, not a variant.
  - BORROW (shorts only) = 0.30% a year × 100 × C × calendar days from d to the next session ÷ 360 (SPY and QQQ are general
    collateral; 0.30% is a stated retail figure for an easy-to-borrow ETF, ≈ $0.40 a night on a $500 share, ≈ $1.25 over a
    weekend). No other financing.
  - COSTS = 2 × c × 100, with **c = $0.01 a share each way** (1×) — $2.00 a round trip — and **c = $0.02** (2×) — $4.00.
    Basis for $0.01: commission at a retail per-share schedule ≈ $0.0035 (IBKR Pro tiered) plus exchange auction and clearing
    fees ≈ $0.001–0.002, FINRA TAF ≈ $0.0002 on the sale, the SEC fee on the sale (≈ $0.003 a share at $27.80 per million on a
    $500 share; less in earlier years and $0 since May 2025); no slippage term, because a market-on-close order fills at the
    official close C and a market-on-open order at the opening print, which O stands for. The 2× figure covers a $1.00-minimum
    fixed-commission schedule ($0.01 a share on 100 shares) plus the gap between the 09:30 bar's first nqb trade and the primary
    listing's opening print. The verdict is read at 1×; 2× is reported beside it. The dividend and borrow terms are the same at 1× and 2×.

## 3. Statistic and pass rule

Per name, separately: the included sessions in calendar order, S_i = net $ of session i (0 when flat), N_i = 1 if it traded.
- **Mean $ a trade after costs** = Σ S / Σ N, at 1× and 2×.
- **Interval**: 20-session moving-block bootstrap over sessions — `audit_lib.block_draws(n, 20, B=2000, seed=20261022)` (the
  backtest audit's library, read not edited; its rng is seeded with seed + 7919 × block), each draw's Σ W·S / Σ W·N, and
  `audit_lib.pct_ci` (2.5 and 97.5 percentiles). The same draws serve 1× and 2× (paired).
- **PASS** in a name: mean at 1× > 0 **and** the interval's lower bound > 0. **H1 passes only if it passes in each name.**
- Reported beside it (descriptive, no verdict): win rate (share of trades with net > 0), total $, worst and best trade, counts
  long / short / flat, the mean of the long and of the short trades, the gross / dividend / borrow / cost pieces of the mean, the
  number of trades over an ex-date, and per-year means at 1× and 2× (by the year of the signal session).

## 4. Data and span

- 1-minute bars: `$SP/theta/data/underlying/{SPY,QQQ}/<day>.parquet`, ThetaData `stock_history_ohlc(symbol, interval='1m',
  date=D)` (venue nqb), 391 rows 09:30–16:00. QQQ priced from 2012-06-01. SPY's files 2012-06-01 → 2016-12-30 are all-NaN, and the
  stage-1 probe (`stock_history_ohlc(SPY, '1m', 2016-06-01)`) came back NaN again, so no SPY bars were fetched: **SPY's bars start
  2017-01-03**.
- Official close: ThetaData stock EOD (`stock_history_eod`) — 2012–2018 fetched for H1 into `data/stock_eod_2012_2018.parquet`
  (sha256 `80e4cedba55c1226b3ecd8e32655ba35a9489aa10c35a88422f8b70880a39cf5`; QQQ 2012-06-01 →, SPY from 2017 — ThetaData answered NOT_FOUND for SPY 2012–2016), 2019 `$SP/lake/stock_eod/year=2019`, 2020 → `data_lake/thetadata/stock_eod/year=*`.
- **Signal sessions: QQQ 2012-06-01 → 2025-10-10 (3,360 sessions); SPY 2017-01-03 → 2025-10-10 (2,206 sessions)** — 2025-10-10
  is the last session before 2025-10-13, and its exit is the 2025-10-13 09:30 open. Every one of these sessions has an EOD row
  (checked); the half days and any session missing the 14:59 or next 09:30 price are excluded and listed in the report. SPY and QQQ are judged separately; nothing
  is pooled.
- The stage-1 fetch (requests, bytes, what came back) is in `fetch/FETCH_NOTES.md` and `fetch/fetch_summary.json`.
- Note on the queue: `research_notes/Edge search/QUEUE.md` rule 2 prefers unopened data (sessions after 2025-10-13 for
  SPY/QQQ); the owner's spec for H1 names every session before 2025-10-13, and that governs here. Section 7 says which of these
  sessions earlier studies have read.

## 5. Data-quality rule (pre-specified sensitivity)

ThetaData's EOD close is the only official-close source before 2025-10-13 and has known bad prints:
`research_notes/Compass phase 3/backtest_audit/out/afterhours_close_check.csv` lists 22 name-sessions with |official − 15:59
bar close| > $0.25 (13 QQQ, 9 SPY; checked on the replay's sessions 2022-11-11 → 2025-10-10, the 22 falling 2023-05-31 →
2025-05-01), and SPY 2025-04-09's 548.62 is unconfirmed (second sources 543.0–543.7). **All sessions
stay in for the verdict.** A sensitivity is reported beside it, with the flagged sessions removed: flagged = the name-sessions in
that CSV plus every session in the span where |EOD close − close of the 15:59 bar| > $0.25 (mechanical; a session without a
priced 15:59 bar is not flagged). Same statistic, same seed, at 1× and 2×; it carries no verdict. **No other variants.**

## 6. Power (a priori, from no H1 data)

Close-to-open moves of SPY/QQQ have had a standard deviation of roughly 0.5–0.8% of price; at average prices of $200–400 that is
about $100–300 a 100-share trade. With 2,000–3,300 trades a name the standard error of the mean is about $3–6, so a true mean
of roughly $6–12 a trade after costs is needed to clear zero reliably. For scale, the Bogousslavsky–Muravyev auction deviation
for large ETFs (3.6 bp ≈ $0.11 a share on a $300 share, ≈ $11 a trade if a rule captured all of it, which this one does not
target directly) is of that order; a fail is therefore not evidence of no reversal smaller than that.

## 7. What earlier studies already read on these data (the data are not virgin)

- **S16a** (`2430c9b`, 2026-10-14, "overnight gaps on the underlying", SPY/QQQ/IWM 2017-06 → 2026-10 from the same 1-minute
  files): the overnight gap (open vs the prior session's last 1-minute close) and the prior close-to-close move as open-time
  signals for open → close, → next close, → third close. Gap continuation and fade indistinguishable from zero; 6 of 108 cells
  with a positive lower bound fading the prior close-to-close move; **nothing promoted**. It read the close-to-open gap's
  distribution and its sign as a predictor of later returns — not the 15:00 → close move as a predictor of the gap.
- **S12** (`2430c9b`, intraday momentum, 2017-06 → 2026-10): read 10:00 → 15:00, 15:00 → 15:50 and 15:30 → 16:00 returns
  conditioned on the first half hour (no last-half-hour momentum on SPY/QQQ/IWM). It read the late-day move H1 signals on, not
  its overnight sequel.
- **The after-hours study** (`633fbff`, `backtest_audit/afterhours.py`, AFTERHOURS.md): read the official close against the next
  session's 09:30 open for SPY/QQQ on the sessions 2025-10-13 → 2026-10-21 (and its overlap from 2025-01), as net stock
  positions of option trades; and the close check (`afterhours_close_check.csv`) read |official − 15:59| on 2022-11-11 → 2025-10-10.
- The backtest audit (`backtest_audit/AUDIT.md`), the SPXW pre-registration and hyp_c/hyp_e/hyp_f read 15:00 → close option
  P&L on SPY/QQQ 0DTE structures 2022-11 → 2026-10, not the stock's overnight return.
- The Compass engine audit's daily bars (`research_notes/Compass engine audit/horizons`, `greeks_books`) aggregated these
  1-minute files into daily OHLC 2012 → 2026 for model work (close-to-close horizons), not the 15:00 → close → open sequence.
- **H1 does not exist as a named prior study**: `git log --all -S"overnight reversal"` hits `3e86683` and `75c29c9`, where the
  phrase is the literature note on the closing-auction reversal (Bogousslavsky & Muravyev), not a test; the registry's "H1" at
  `75c29c9^` is the level-sweep 0DTE family; `research_notes/Compass direction/PREREG_DIRECTION.md` §6 records the same search.
- This is the first entry of the edge-search queue (`research_notes/Edge search/QUEUE.md`, `a49c35b`).

## 8. Outputs and the run

`run_h1.py` (deterministic: files read in sorted order, seeded draws, no clock in the outputs) → `out/h1_sessions.csv` (every
calendar session per name: C, P15, O, the 15:59 close, dividend, side, each P&L piece, the reason it was excluded, the flags),
`out/h1_summary.json`, `H1_REPORT.md` (this file's sha256 at the top). `verify_h1.py` re-derives 25 random trades a name (50 in all, `random.Random(20261023)`) from
the raw files with plain loops and pyarrow (no shared code) and must show 0 differences. Run once; the verdict as it comes.
