# H4 — market intraday momentum (first half-hour → last half-hour), SPY and QQQ stock: pre-registration

Written 2026-10-23, committed alone, before any H4 quantity is computed. The test is run once, by `run_h4.py` (in this folder,
not committed with this file), on the data listed in section 4; nothing in this file is changed after the run. The queue's line
(`research_notes/Edge search/QUEUE.md`, `a49c35b`, entry 3): "intraday momentum (first half-hour return predicts the last
half-hour, Gao, Han, Li & Zhou 2018), SPY/QQQ stock, on sessions 2025-10-13 → today plus forward (S12 already read 2017–2025 on
QQQ: those sessions are exploration only)". Section 7 corrects that parenthesis: earlier studies read more than that, including
most of the test span, with a related signal.

What has been looked at before this file: the inputs' coverage only (which sessions have a bar file, which have a priced 09:59
close, 15:30 open and 15:59 close, which have an official close in each source, the dividend table's last dates) and one
sign-free figure for the power statement, the root-mean-square of the 15:30-open → official-close return on the exploration
span (`power_h4.py`, section 6; it prints no mean of anything). No r1, no signed return, no H4 P&L, on any span, has been computed.

## 1. Hypothesis and mechanism

**H4.** On SPY and on QQQ, the sign of the return from the previous session's official close to 10:00 predicts the sign of the
return from 15:30 to the official close: a 100-share position in the direction of the first return, opened at 15:30 and closed
in the closing auction, makes money after costs.

**Why it might.**
- *Gao, Han, Li & Zhou, "Market intraday momentum", Journal of Financial Economics 129(2) (2018) 394–414.* On SPY, February
  1993 → December 2013, the first half-hour return measured **from the previous day's close** to 10:00 positively predicts the
  last half-hour return (15:30 → 16:00), with an in-sample R² of roughly 1.6–2 % (the published and working-paper figures), the
  predictability stronger on volatile days, high-volume days, recession days and major macro-news days, and present in ten other
  actively traded ETFs. They relate it to infrequent portfolio rebalancing (Bogousslavsky 2016: investors who trade late in the
  day on information that arrived in the morning) and to late-informed traders who trade near the close.
- *Baltussen, Da, Lammers & Martens, "Hedging demand and market intraday momentum", JFE 142(1) (2021) 377–403.* In 60+ futures
  1974–2020, the return over the rest of the day (prior close to 15:30) predicts the last 30 minutes; they tie it to gamma hedging
  by option dealers who are net short gamma and to leveraged-ETF rebalancing (much stronger on negative-gamma days), and find the
  predictability reverts over the following days (price pressure). Their predictor is not GHLZ's r1; H4 uses GHLZ's.
- *Li, Sakkas & Urquhart, "Intraday time series momentum: global evidence and links to market characteristics", Journal of
  Financial Markets (2022)*: the effect in most of 16 developed markets, in and out of sample (as summarised in the repo's
  price-action catalogue, `048d33a`).
- *Against — decay after publication.* Anomalies in general earn less after publication (McLean & Pontiff, Journal of Finance
  2016: portfolio returns about 26 % lower out of sample and 58 % lower after publication). For this effect on SPY after the
  2013 sample end, I have no SPY-specific post-publication replication I can verify from this container, so none is quoted; the
  repo's own reads (section 7) found no last-half-hour momentum on SPY or QQQ 2017 → 2026 with an open-based first half hour,
  and a gamma-conditioned version (the earlier programme's H10) had the wrong sign on SPY 2024-05 → 2026-10. The prior for H4 is
  therefore low, and this test has little power against the small effect the literature reports (section 6).

## 2. The rule, exactly (one variant)

For each name (SPY, QQQ) and each session d in the span (section 4):
- **Cprev** = the **official close of the previous session** (the session before d in the session list). Chosen over the
  previous session's 15:59 bar close because GHLZ measure r1 from the previous day's close, and because it is the same source and
  the same kind of price (the closing auction) that H4 exits at. It is NOT adjusted for a dividend whose ex-date is d (GHLZ's r1
  is a price return; the dividend table on disk has no SPY ex-date after 2025-12-19, so an adjustment could not be applied
  uniformly without a fetch). On an ex-date, r1 carries the dividend drop (SPY ≈ 0.2–0.3 %, QQQ ≈ 0.1–0.15 %, four sessions a
  year); the report lists the traded sessions on ex-dates the table knows, descriptively.
- **P10** = the "price at 10:00" = the `close` of the 1-minute bar stamped **09:59** (bars are stamped at their start; the last
  trade printed before 10:00:00 in the feed). An unpriced or missing 09:59 bar → the session is excluded and listed; no other bar
  is substituted.
- **r1** = P10 ÷ Cprev − 1. **Side**: P10 − Cprev ≥ $0.00005 → **long** 100 shares; Cprev − P10 ≥ $0.00005 → **short** 100
  shares; otherwise (equal to the fourth decimal) → **flat** (the session stays in the series with P&L 0 and no trade).
- **Entry E** = the `open` of the 1-minute bar stamped **15:30** (the first trade printed at or after 15:30:00). Unpriced or
  missing → excluded, listed.
- **Exit C** = the **official close of d** (the closing auction), and Cprev likewise for the previous session:
  - a session before 2025-10-13: ThetaData's stock EOD `close` whose `created` time in New York falls on that session — the
    source and the reading of `research_notes/Compass H1/run_h1.py` `eod()` (the same files: `Compass H1/data/
    stock_eod_2012_2018.parquet`, `$SP/lake/stock_eod/year=2019`, `data_lake/thetadata/stock_eod/year=*`); two different closes
    for one session → no official close (excluded, listed);
  - a session on or after 2025-10-13: Unusual Whales' daily bar `close` (`market_time == 'r'`), `audit_lib.uw_daily()` — the
    lake's `ohlc__1d` parts and `data/official_closes/uw_ohlc_1d_*.parquet`. Coverage checked: one row a session for both names
    on every session 2025-10-13 → 2026-10-22 (259), no duplicates.
  So the first test session, 2025-10-13, takes its Cprev from ThetaData's 2025-10-10 row.
- **Half days are excluded** (the market closes at 13:00; there is no 15:30–16:00 window), listed. Exploration: 2012-07-03,
  2012-11-23, 2012-12-24, 2013-07-03, 2013-11-29, 2013-12-24, 2014-07-03, 2014-11-28, 2014-12-24, 2015-11-27, 2015-12-24,
  2016-11-25, 2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23, 2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27,
  2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03 (H1's list).
  Test: **2025-11-28 and 2025-12-24** (the coverage check found the 15:30 and 15:59 bars unpriced on exactly these two sessions
  of the test span, both names; 2026 has no half day before 2026-10-22). A half day as the *previous* session is a normal
  Cprev (its official close).
- **P&L of a trade, $** (100 shares; side +1 long, −1 short):
  `net = side × 100 × (C − E) − COSTS − BORROW`
  - COSTS = 100 × (h + a): **h = $0.005 a share** at entry (half of SPY's and QQQ's typical one-cent spread: a marketable order
    at 15:30 pays half the spread over the bar's first print, which E stands for) and **a = $0.01 a share** at exit in the
    closing auction (H1's figure: commission at a retail per-share schedule ≈ $0.0035, auction and clearing fees, FINRA TAF and
    the SEC fee on the sale; a market-on-close order fills at the official close C). **1× = $0.015 a share round trip = $1.50 a
    trade**; **2× = $0.03 = $3.00 a trade**, reported beside it (it also covers a commission at entry and a wider spread). The
    verdict is read at 1×.
  - BORROW (shorts only) = 0.30 % a year (H1's figure) × 100 × E × (30 minutes ÷ 1,440) ÷ 360 — about $0.0013 a short on a
    $650 share. A short opened and covered in the same session is normally charged no borrow fee at all (fees accrue on
    positions held over settlement); the pro-rata figure is charged anyway and is immaterial.
  - No dividend term: the position is opened and closed inside one session.

## 3. Statistic and pass rule

Per name, separately, per span: the included sessions in calendar order, S_i = net $ of session i (0 when flat), N_i = 1 if it
traded.
- **Mean $ a trade after costs** = Σ S / Σ N, at 1× and 2×.
- **Interval**: 20-session moving-block bootstrap over sessions — `audit_lib.block_draws(n, 20, B=2000, seed=20261023)` (the
  backtest audit's library, read not edited), each draw's Σ W·S / Σ W·N (`audit_lib.weights_from`), and `audit_lib.pct_ci`
  (2.5 and 97.5 percentiles). The same draws serve 1× and 2× (paired).
- **PASS, per name, on the test span only**: mean at 1× > 0 **and** the interval's lower bound > 0. SPY and QQQ are judged
  separately; each gets its own verdict; nothing is pooled. H4 has two verdicts (one a name); the ledger row records both.
- Reported beside it (descriptive, no verdict): trades long / short / flat, the mean of the long and of the short trades, win
  rate (share of trades with net > 0), total, worst and best trade, the gross / cost / borrow pieces, per-year means at 1× and 2×
  (by calendar year), the traded sessions on ex-dates the dividend table knows, the sessions excluded and why.
- **Exploration span**: the same statistic, interval and descriptive lines, reported for context only. No choice in this file
  is made from it and no verdict is read from it.

## 4. Data and spans

- 1-minute bars: `$SP/theta/data/underlying/{SPY,QQQ}/<day>.parquet` (SP = `/tmp/claude-0/-home-user-georgeredo/
  c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`), ThetaData `stock_history_ohlc` 1m, 391 rows 09:30–16:00 stamped at the
  bar's start. QQQ priced from 2012-06-01; SPY's files before 2017 are all-NaN (H1's stage-1 probe), so SPY starts 2017.
- Sessions: the dates on which QQQ's stored 1-minute file exists (H1's rule; one file every NYSE session, none on a holiday or a
  closure). SPY uses the same list. Previous session = the date before d in that list.
- **Exploration (context only)**: every session before 2025-10-13 on disk — **QQQ 2012-06-01 → 2025-10-10, SPY 2017-01-03 →
  2025-10-10**. The first session of each has no previous official close on disk (QQQ 2012-05-31 is not a session on disk;
  ThetaData answered NOT_FOUND for SPY's 2016 EOD), so each is excluded by the Cprev rule and listed. This span includes every
  session S12 read (section 7).
- **Test (the verdict)**: **2025-10-13 → 2026-10-22**, 259 sessions, 257 after the two half days, a name. 2026-10-22 is the last
  session with an official close on disk (`data/official_closes/uw_ohlc_1d_2026-10-22.parquet`).
- **Forward**: sessions from 2026-10-23 are not part of this verdict. If a name passes, a FORWARD rule (the same rule, its N and
  its pass line) is committed before any forward session of it is read (QUEUE rule 6); if neither passes, no forward rule.
- No vendor fetch is needed; none is made.

## 5. Ledger count and the Bonferroni rule (QUEUE rule 5)

H4 is the ledger's third hypothesis (H1 FAIL, H3 FAIL). A pass under section 3 is reported with the ledger count; it is called an
**EDGE** only if its interval also clears zero at a Bonferroni level across the ledger, counting both of H4's names as separate
tests: α = 0.05 ÷ (2 × m), the two-sided percentile interval of the same 2,000 draws:
- **m = 3** (this ledger): α = 0.05 ÷ 6 = 0.833 % → the 0.417 and 99.583 percentiles;
- **m = 8** (counting the earlier programme's five pre-registered failures: the 0DTE picker, the SPXW analogues, the 23-feature
  direction family, post-earnings drift in options, the after-hours rule): α = 0.05 ÷ 16 = 0.3125 % → the 0.156 and 99.844
  percentiles.
With 2,000 draws these tails rest on about 8 and 3 draws; they are reported as computed and are coarse. Even an EDGE at these
levels is not "an edge that works" before its forward N (QUEUE rule 6).

## 6. Power (a priori)

`power_h4.py` (committed with the run) computed, on the exploration span only, the root-mean-square of the last-half-hour return
x = C ÷ E − 1 (15:30 open → official close), sqrt(mean(x²)) — a sign-free figure, the same for any long/short rule, and an upper
bound on the de-meaned standard deviation; no mean was computed or printed. At each name's 2025-10-10 official close, over the
test's 257 sessions (assuming roughly independent sessions):

| name | span of the RMS | RMS | $ a 100-share trade | standard error of the mean, 257 trades | minimum detectable effect (80 % power, 5 % two-sided) |
|---|---|---|---|---|---|
| SPY | 2017-01 → 2025-10 | 32.5 bp | $212 (at $653.02) | $13.2 | $37 (≈ 5.7 bp) |
| SPY | 2022-10 → 2025-10 | 24.4 bp | $159 | $9.9 | $28 (≈ 4.3 bp) |
| QQQ | 2012-06 → 2025-10 | 32.3 bp | $190 (at $589.50) | $11.9 | $33 (≈ 5.6 bp) |
| QQQ | 2022-10 → 2025-10 | 28.0 bp | $165 | $10.3 | $29 (≈ 4.9 bp) |

So the test detects reliably only a true mean of about **$28–37 a trade (4–6 bp of the 30-minute move)** after costs of $1.50.
The repo's earlier reads (section 7) put the open-signed last-half-hour mean within ±2 bp. **A FAIL here is weak evidence
against an effect of the size the literature or the earlier reads suggest; a PASS would need an effect two to three times larger
than anything seen on these ETFs since 2017.**

## 7. What earlier studies already read (the test span is NOT unopened)

- **S12** (`fe93f87` code, `2430c9b` results, 2026-10-14; `research/compass/studies/s12_intraday_momentum.py`, removed from the
  tree by `75c29c9`): **SPY, QQQ and IWM, 2017-06-01 → 2026-10-09** (2,326 sessions SPY/QQQ, 2,324 IWM) — not "2017–2025 on QQQ"
  as the queue says. Signal: the sign of **09:30 open → 10:00** (the 09:30 bar's open to the 09:59 bar's close; it excludes the
  overnight gap, unlike GHLZ's r1), sessions with r = 0 dropped. Cells read, in bp, signed by that sign, CIs clustered by date:
  10:00 → 15:00, 15:00 → 15:50 and **15:30 → 16:00 (the 15:29 bar's close to the 15:59 bar's close)**, on all days and on days
  with |first half hour| ≥ 0.3 %. Results: 15:30 → 16:00 all days SPY −0.8 bp [−2.2, +0.5], QQQ −0.5 [−2.0, +1.0], IWM +0.1;
  ≥ 0.3 % days SPY −1.8 [−6.0, +2.4], QQQ −1.2 [−4.0, +1.7]; per year (all days, 15:30 → 16:00) SPY 2025 +0.5, 2026 −0.9, QQQ
  2025 +0.9, 2026 −1.9. Also 10:00 → 15:00 (QQQ +4.3 [+0.8, +7.8], +9.0 [+2.8, +15.3] on ≥ 0.3 % days, not batch-robust) and a
  15:00 → 15:50 0DTE option cell (−$4.36 [−8.48, +0.21]); S12b (`b9b9206`, re-run `be991de`) the 10:00 option expressions.
  **S12's window covers 248 of the test span's 257 full sessions**; only 2026-10-12 → 2026-10-22 (9 sessions) are after it.
- **The session study's T4** (`research/short_vol_session/summary.md`, before `75c29c9`; cited in `reports/Finding a 0DTE
  options edge.md`): **SPY, QQQ, IWM 2025-06-02 → 2026-10-09** (339 sessions a name), first half hour (09:30 open → 10:00) →
  15:30–16:00: SPY corr −0.042, sign agreement 45.1 %, mean of sign(x)·y −0.90 bp [−2.61, +0.75]; QQQ −0.026, 46.6 %, −1.17 bp
  [−3.53, +1.16]; pooled −0.036, 46.7 %. Also 15:00–15:30 → last 30 (QQQ corr 0.172) and 15:00-momentum 0DTE options. It covers
  the test span to 2026-10-09.
- **The price-action atlas** (`research/compass/intel/06_price_action_atlas.md`, before `75c29c9`): 43 names incl. SPY/QQQ,
  2017-06-01 → 2026-10-09, first half hour (09:30 → 10:00) against the last, cross-name correlation −0.022 (2017–22) and
  +0.009 (2023–26), using the last bar's close, not the official close.
- **The earlier programme's H10** (catalogue row D4/R1, `048d33a`): SPY on negative-gamma days, 2024-05 → 2026-10, the
  BDLM-style last-half-hour momentum: −3.07 bp a day [−5.73, −0.52], the wrong sign.
- **H1** (`38aca66`, `4a02144`): the 14:59 bar close and the official close on the exploration span (15:00 → close, then the
  close → next open); it did not read the test span. **The after-hours study** (`633fbff`): the official close against the next
  09:30 open on 2025-10-13 → 2026-10-21. **The backtest audit, the SPXW pre-registration, hyp_c/e/f**: 15:00 → close option P&L
  on SPY/QQQ 0DTE structures 2022-11 → 2026-10.
- **What H4 adds over those reads**: GHLZ's own r1 (from the previous official close, so the overnight gap is in the signal), an
  executable entry (the 15:30 bar's open) and exit (the official close, the closing auction), and dollar P&L after stated costs,
  judged once on 2025-10-13 → 2026-10-22. The open-based signals above and r1 share the 09:30 → 10:00 move but differ by the
  gap, so the earlier reads are evidence about a related, not the same, predictor. Because the test span's last-half-hour returns
  have been read (open-signed) and published as near zero or negative, **the test is not on unopened data**; QUEUE rule 2's
  unopened data for SPY/QQQ is, in truth, only the forward sessions from 2026-10-23 (and the nine sessions after 2026-10-09 for the
  open-signed reads). The rule here was fixed from the paper and the queue, not from those numbers; the verdict is reported as
  it comes, and a pass would still need the forward rule.

## 8. Outputs and the run

`run_h4.py` (deterministic: files read in sorted order, seeded draws, no clock in the outputs) → `out/h4_sessions.csv` (every
calendar session per name and span: Cprev, P10, r1, E, C, side, gross, costs, borrow, net 1× and 2×, the reason it was excluded),
`out/h4_summary.json`, `H4_REPORT.md` (this file's sha256 at the top). `verify_h4.py` re-derives at least 40 traded sessions (20
a name from the test span and 10 a name from the exploration span, `random.Random(20261024)`) from the raw files with plain loops
(polars only to read Parquet into Python lists — no pyarrow here) and no shared code, and must show 0 differences. Run once; the
verdict as it comes. Then one row is appended to `research_notes/Edge search/LEDGER.md`.
