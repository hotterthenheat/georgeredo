# H3 — earnings implied-volatility crush, a short iron condor across the report: pre-registration

Written 2026-10-22 (New York), committed alone and pushed before any H3 quantity is computed. The test is run once, by code in
this folder committed after this file; nothing in this file is changed after the run. The queue's definition
(`research_notes/Edge search/QUEUE.md`, commit `a49c35b`), verbatim: "H3 — earnings implied-volatility crush: a defined-risk
short iron condor (wings 1 implied move out) entered at the close before a report, exited at the close of the reaction session,
single names; exploration on the 1,601-name 2019–2022 exploration set, holdout the 1,600 unopened names (their option EOD
fetched only if the screen passes)." The queue's rules 1–6 apply unchanged.

**What was looked at to write this file**: QUEUE.md, LEDGER.md, `research_notes/Compass direction/` (PREREG_DIRECTION.md
sha256 `233e17b4…9f976053`, DIRECTION_REPORT.md, ledger.py, ledger.json, dcommon.py, fetch_direction.py), PREREG_FEATURES.md
(sha256 `840f7671…5d314cfc62cd`) §2 and §6, `audit_lib.py` (sha256 `3fcbb80b…b7935936`), PREREG_H1.md's layout, the earlier
programme's notes at `75c29c9^` (`research/compass/05_results.md`, `intel/02_volatility_pricing.md`), the UW calendar's
`report_time` counts for the exploration names in 2019-04 → 2022-12, and the PEAD fetch's per-event stage counts (how many
2019–2022 exploration events cleared the $50 M floor: metadata, no price). **No option price, implied move, credit, P&L or
post-report move of any H3 event has been computed or looked at.**

---

## 1. Hypothesis and mechanism

**H3.** On single names, a defined-risk short iron condor opened at the closing quote of the last full session before a
scheduled quarterly earnings announcement and closed at the closing quote of the reaction session makes money on average
after buying at the ask, selling at the bid and fees.

**Mechanism.** Implied volatility of short-dated options rises into a scheduled announcement, which carries a known jump in
the price, and falls when the announcement resolves it (Patell & Wolfson 1979, J. Accounting and Economics; 1981, J. Accounting
Research). Dubinsky & Johannes (2006, working paper, "Earnings announcements and equity options"; later Dubinsky, Johannes,
Kaeck & Seeger 2019, Review of Financial Studies, "Option pricing of earnings announcement risks") model the announcement as a
priced jump and recover its size from the term structure of implied volatility before the event. Whether the option price of
that jump exceeds what is realized on average — an earnings variance risk premium that sellers earn — is the trade's premise:
Barth & So (2014, The Accounting Review, "Non-diversifiable volatility risk and risk premiums at earnings announcements") find
that announcement-period volatility carries a risk premium priced in options. Gao, Xing & Zhang (2018, J. Financial and
Quantitative Analysis, "Anticipating uncertainty: straddles around earnings announcements") document the run-up in implied
volatility before announcements and positive average returns to long straddles held in the days BEFORE the announcement
(volatility bid up into it), i.e. the timing structure H3 sells into at its peak; their result is about the window before the
report, not across it. **The crash risk is documented**: a short-volatility position across an announcement has a short
left tail (the realized jump exceeds the priced one in a minority of reports, and those losses are large), which is why the
structure here is defined-risk. The citations are given as the author recalls them; none of their numbers is used below.

**Against (disclosed, from opened data — section 7).** The earlier programme's V2a (2023-11 → 2026-09, 11,802 reports on the
optionable universe) sold the at-the-money straddle at the close before the report and bought it back at the reaction
session's close: −26.1 % of premium (development + validation) and −34.2 % (hold-out). Reports moved a median 0.59 of the
implied move, sellers earned +6.9 % at the mid on same-day settlements, and half the 12.9 % median straddle spread took all of
it. H3 crosses eight spreads (four legs in, four out) instead of four. **The prior for a pass is low**, and this is stated
before anything is computed.

## 2. Events, dates and the sets

- **Events**: the exploration list of `research_notes/Compass direction/events.json.gz` (`exploration`: the 1,601 names of X,
  timed quarterly UW reports, sorted by (ticker, date) then permuted with `np.random.default_rng(20261026)`; list sha256
  `ba8b9dca…5206dce05`), kept when **both P and R (below) are in 2019-04-01 → 2022-12-30** — the unopened-before-2023 cells of
  the X names only (X from 2023 is opened, and V2a read this trade there). The **holdout** is the `holdout` list (the 1,600
  names of H, PREREG_DIRECTION appendix A; permuted with seed 20261025; sha256 `7d87d8c4…80d316c83`), same window rule.
- **Timing**: UW's `report_time`, premarket or postmarket. The lists hold only timed reports; a (ticker, date) carried with two
  times was dropped when the lists were drawn (counted). An untimed report is not an event (counted in the report; in the X
  window the UW calendar carries 22,651 quarterly X reports, every one timed; 2 ambiguous pairs).
- **Reaction session R**: premarket on day E → E if E is a trading day, else the next trading day; postmarket on E → the next
  trading day after E (PREREG_DIRECTION §4, `dcommon.event_dates`).
- **Entry session P** = the trading day before R: the last session that closes before the announcement (E − 1 for a premarket
  report, E itself for a postmarket one). **P and R must both be full sessions** (no half days; else not formed, listed).
- **"As scheduled before entry"**: the date and time used are UW's recorded ones. A trader at P's close knows a confirmed date
  in nearly every case (companies confirm two to four weeks ahead), but the test cannot verify that a recorded date was the
  date known at P. A wrong recorded time puts the trade a session late (both P and R after the release: no crush to collect)
  or early (no release inside the trade); either error works against H3, never for it.
- **Post-market timing of the closing quote**: ThetaData's option EOD bid/ask is the last NBBO at report generation; for single
  names that is in practice the 16:00 NBBO (PREREG_FEATURES §2.3). A postmarket release comes after 16:00, so the entry quote
  is taken before it. Assumed, not verifiable from the stored fields.
- **Bars**: ThetaData stock EOD as PREREG_DIRECTION §4 (`dcommon.load_bars`: 2019 in the old scratch lake, 2020 → in
  `data_lake/thetadata/stock_eod`). close(P) is required (no bar for P → not formed). close(R) is used only by the split rule
  and the exit fallback (section 3).
- **Liquidity floor (input, point in time)**: the median close × volume over the 60 trading days ending at the session BEFORE P
  ≥ $50 M with at least 50 of the 60 days present (PREREG_DIRECTION's floor, ending one session earlier so that P's own final
  volume is never needed). Else not formed, and nothing of the event is fetched.

## 3. The structure, exactly

**Expiry.** From P's option EOD (every expiry, `option_history_eod(P, P, symbol, expiration='*')`): the earliest listed
expiration (rows present at P) whose last trading day (`dcommon.last_trading_day`) is **after R** and whose date is **at most
14 calendar days after P**. None → not formed ("no expiry after R within 14 days", listed — names with monthly expiries only
fall here most quarters).

**The strikes.** On that expiry at P (strikes of a side = strikes with a row of that right in P's file):
- **K0** = the strike with both a call row and a put row nearest close(P) (ties: the lower).
- **IM** = C_mid(K0) + P_mid(K0), the at-the-money straddle mid in dollars (mid = (bid + ask)/2). Both K0 quotes must stand
  (bid > 0, ask > 0, ask ≥ bid), else not formed ("no standing ATM pair"). **Parity check** (PREREG_DIRECTION's guard against a
  ticker that was another security): F = K0 + C_mid − P_mid; |F ÷ close(P) − 1| ≤ 5 %, else not formed ("bars and options
  disagree").
- **The choice — shorts at K0 ± 0.5·IM, longs at K0 ± 1.5·IM** (one variant only; no other is run):
  short call Kcs = the call strike nearest K0 + 0.5·IM; long call Kcl = the call strike nearest K0 + 1.5·IM; short put Kps =
  the put strike nearest K0 − 0.5·IM; long put Kpl = the put strike nearest K0 − 1.5·IM (ties: the strike farther from K0).
  Required Kcl > Kcs and Kpl < Kps, else not formed ("strike grid too coarse for the wings", listed). Kcs and Kps may both
  equal K0 when half an implied move is under half a strike step (the condor becomes an iron fly; counted, kept).
  **Why this one.** The queue names an iron *condor*: two short strikes apart, one on each side of the money; the iron fly
  (both shorts at K0) is a different structure and is not what was queued. "Wings 1 implied move out" is read as the width of
  each wing — each long strike one implied move beyond its short strike — so the body is the implied move's own span centred
  on the money (shorts half an implied move either side, one implied move apart) and each wing adds one implied move of
  protection. The reading that puts the shorts a full implied move out (longs further still) sells almost no premium at the
  ask/bid on these names and is not taken. The choice is made from the words, before any price of an H3 event is seen.
- **One contract a leg.**

**Entry (decided at P only).** Every leg must stand at P: bid > 0, ask > 0, ask ≥ bid. A leg with no bid, no ask or a crossed
quote → the event is untradable and not formed (listed by leg). Opened by **selling the two shorts at their bids and buying
the two longs at their asks**: credit c = bid(Kcs) + bid(Kps) − ask(Kcl) − ask(Kpl). c ≤ 0 → not formed ("no credit");
c ≥ W → not formed ("credit at or above the width", a bad quote), where **W = max(Kcl − Kcs, Kps − Kpl)**.

**Exit (R's closing quote, one request: `option_history_eod(R, R, symbol, expiration=<the expiry>)`).** Closed by **buying
the shorts at their asks and selling the longs at their bids**:
- a short leg with a standing ask at R (a row with ask > 0 and ask ≥ bid; bid may be 0) is bought at the ask;
- a long leg with bid > 0 and ask ≥ bid is sold at the bid; a row with bid 0 (ask > 0) is sold for $0 with no fee;
- **a missing quote is valued, never excluded** (so no large real move can leave the sample): a short leg with no row, no ask
  or a crossed quote is bought at its intrinsic value on close(R) **plus that leg's entry spread** (ask − bid at P); a long leg
  with no row or a crossed quote is sold at max(intrinsic on close(R) − its entry spread, 0). An exit file with no rows at
  all values all four legs so. If a fallback is needed and there is no bar for R, the trade is booked at its maximum loss.
- **Splits**: if close(R) ÷ close(P) is within 10 % of a split ratio of 2:1 or larger (1/2, 1/3, 1/4, 1/5, 1/10, 1/20, 1/50
  and the reverse ratios; the A10.2 rule), the trade is **booked at its maximum loss** — never dropped, since a crash of that
  size is exactly the tail the test must keep (a true split on the report night would be a non-event; booking it at the worst
  case can only hurt H3).
- **No early assignment is modelled**: every leg is closed at R's close, one session after entry, before the expiry; the only
  American-exercise risk is an in-the-money short call before an ex-dividend date inside the one night (a single name's
  quarterly dividend rarely makes early exercise optimal on a contract with days of time value left). Accepted and stated.

**Fees.** $0.68748 a contract each way (PREREG_FEATURES §2.6: $0.65 + ORF $0.01248 + OCC $0.025, the singles at the SPY
figure; today's schedule applied to every year): four legs in (2.74992), each leg out at a price above $0 (at most 2.74992);
nothing on a leg sold for $0.

**The return of a trade.** Exit cost x = ask(Kcs)′ + ask(Kps)′ − bid(Kcl)′ − bid(Kpl)′ (primes: R's prices or the fallback
values). **$ per condor = 100 × (c − x) − fees in − fees out.** Also **% of max risk = $ ÷ (100 × (W − c))**. A split-booked
or no-bar-fallback trade's $ = −100 × (W − c) − fees in − 4 × 0.68748.

## 4. Statistic, interval and the pass rule

- **Sessions = exit dates.** The series is every full session (`dcommon.sessions()`) from 2019-04-01 to 2022-12-30 in date
  order, zeros where no trade exits. S_s = Σ $ of the trades whose R is s; N_s = their count. **The statistic: mean $ per
  trade = Σ S ÷ Σ N.**
- **Interval**: the 20-session moving-block bootstrap over those sessions, `audit_lib.block_draws(n, 20)` (B = 2,000, its
  default seed 20261022, i.e. `default_rng(20261022 + 7919 × 20)`), `audit_lib.weights_from`, per draw (W·S) ÷ (W·N), the 95 %
  interval by `audit_lib.pct_ci`; `audit_lib.session_stats(S, N)` reported beside (blocks 1, 5, 20, effective N). No interval
  under 60 sessions (no pass).
- **Exploration screen**: mean > 0 **and** the block-20 95 % lower bound > 0. Fail → the holdout is not fetched and not read,
  the study ends, the LEDGER row is added.
- **Holdout test (once, only after a screen pass)**: the same rule, unchanged, on the H events. **PASS: holdout mean > 0 with
  the block-20 95 % lower bound > 0.** The verdict is the holdout's alone.
- **Reported beside, descriptive, no verdict of their own**: the mean % of max risk (same bootstrap); win rate ($ > 0); the
  worst trade; the 1st and 5th percentiles of $ a trade; the median; per year of R; per liquidity tier; premarket vs
  postmarket; iron-fly-shaped vs condor-shaped; the count of exit fallbacks and split bookings; the mean credit and mean exit
  cost in implied moves; the realized move |close(R) ÷ close(P) − 1| × close(P) ÷ IM (median) for context.
- **Liquidity tiers** (PREREG_FEATURES §2.7 measured as PREREG_DIRECTION §4: on 2 of the 20 full sessions before the first
  session of P's calendar month, the 10th and the 20th, `dcommon.tier_days` / `tier_measure` / `tier_of`). Tier files are
  read from the PEAD store where it already holds them (read-only), else fetched — in a second pass after every event file,
  inside the same budget; a name-month whose tier files were not reached is Tier U.

## 5. Multiple testing

H3 is the **2nd** hypothesis in LEDGER.md (H1 failed); before the ledger the earlier programme recorded 5 pre-registered
failures or drops (LEDGER.md's last line). Under the null a single screen passes about 2.5 % of the time and both stages
about 0.025² ≈ 0.0006 (more, since the sets share a market). **QUEUE.md rule 5**: a holdout pass is called an **EDGE** only if
it also clears a **Bonferroni level across the ledger**: with m = the ledger's rows including H3 (m = 2), the holdout's
block-20 bootstrap interval at 1 − 0.05/m two-sided (the 1.25th–98.75th percentiles of the same 2,000 draws) must have its
lower end > 0. The stricter count that adds the earlier programme's 5 entries (m = 7: the 0.36th–99.64th percentiles) is
reported beside it. Without that, a pass is reported as a pass "not yet an edge", and even an EDGE is not called "works"
before the forward N rule (rule 6).

## 6. Data, fetch, budget and the cut (stated now)

- **Paths**: `$SP` = `/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad` (the stored
  data and the secrets file, as `dcommon.SP_OLD`); `$SPN` = `/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`
  (the PEAD store `$SPN/dir/store`, and this study's).
- **What is fetched** (ThetaData `thetadata` SDK, `option_history_eod`; one login a run; the key `THETADATA_KEY` read from
  `$SP/secrets/research.env` inside the process, never printed, logged or written): per event formed up to the option stage
  (window, full P and R, bar at P, the floor): (1) P's file, every expiry; (2) only if the entry is formed from (1) (every
  rule of section 3 up to the credit): R's file of the one chosen expiry. Then (3) the tier files (section 4). Raw rows kept:
  date, expiration, strike, right, bid, ask, volume. Each answer staged (`.part`), verified (columns and types, the requested
  date only, the requested expiry only for (2), no duplicate (date, expiration, strike, right), no negative price, no
  expiration before the date), then renamed into the store (`$SPN/h3/store`), never over an existing file; a failed
  verification stays in staging and the event is not formed (listed). **Reused**: no stored file covers P or R with a
  ≤ 14-day expiry (the PEAD fetch stored E1 = R + 1 every expiry and its exit day's 31–60 DTE expiry); the PEAD store is
  read only for tier files and for any P file it happens to hold.
- **Sessions with ThetaData**: none held 19:40–20:30 or 00:00–01:45 New York — the fetcher starts no request and exits from
  19:35 and from 23:50, and is restarted (a new login) after 20:30 / 01:45.
- **Budget per phase (exploration; holdout only after a pass)**: stop at **8.0 hours of fetch time** or **1.5 GB stored**,
  or when the disk's free space falls under **1.5 GB**, whichever is first. The PEAD fetch's measured cost (0.9 s and
  5.7 KB a request; about 22 % of 2019–2022 exploration events clear the floor) puts the exploration at about 5,000 events
  and 10,000–15,000 requests, inside the budget.
- **The cut, if the budget binds**: events are walked in their list's seeded order (section 2); the set tested is every event
  whose event files (1) and, where needed, (2) were stored before the stop; an event cut mid-way is dropped whole; events never
  reached are never read. Tier files come after every event file, so a binding budget leaves tiers U, never events.

## 7. Prior reads on these data (not virgin, disclosed)

- **S08** (`f3ec790`, 2024-01 → 2026-10, the S07 universe of 1,186 names): post-earnings drift on the **stock** by surprise
  sign and event-day-move sign; nothing on implied volatility. **S13** (`eff2382`, 2024 → 2026): the pre-earnings run-up on
  the **stock** (+20 bp specific to the window); it named the rise of implied volatility into the report as what a long
  straddle sold at the pre-event close would collect, and its option expression (S11, A5.2: pre-earnings long call /
  straddle / debit vertical, 10 sessions) had n ≤ 20 — not read. Neither touches 2019–2022.
- **V2** (`152f786`, 2023-11-27 → 2026-09-30, 11,836 reports on 1,587 optionable names, UW closing chains / ThetaData
  closes): **V2a is H3's nearest sibling** — a short at-the-money straddle across the report, close before to the reaction
  close — and lost (section 1); V2b (long straddle into the report) lost. **The IV-crush trade has been read, as a straddle, on
  2023-11 → 2026-09.** It has **not** been read on any 2019–2022 cell, and not on the H names' 2019–2022 cells, the H3 holdout.
- **V1** (2023-11 → 2026-09): monthly straddles with a report inside the month (−14.8 %); same window.
- **PEAD** (PREREG_DIRECTION, `38b11bf` / `94fb69d`): read 31–60 DTE option EOD of 3,005 exploration events (1,238 of them
  in 2019–2022) at E1 = R + 1 and ten sessions later; the H names were not fetched. No P-to-R option price was read.
- **Not read by the author for this file**: any option quote at a P or an R of any 2019–2022 event.

## 8. Power (a priori, no H3 data)

The P&L a condor has a standard deviation σ of the order of its maximum risk's size; with N formed trades whose exits cluster
in earnings seasons (variance inflated about 2× over independent trades), SE(mean) ≈ σ √(2/N), and the mean found 80 % of the
time at the rule's one-sided 2.5 % is 2.8 × SE: **0.07 σ at N = 3,000, 0.056 σ at 5,000.** The test can see a premium of a
few percent of a condor's maximum risk; V2a's straddle lost about a quarter of its premium, a far larger effect in the other
direction. A FAIL says no premium large enough to pay eight crossings of the spread showed up, not that no earnings variance
premium exists at the mid.

## 9. Outputs and the run

`H3_REPORT.md` (this file's sha256 at the top): the ledger count and Bonferroni status; the fetch (requests, rows, bytes,
hours, what the cut left out); events at each stage and why each was not formed; the screen (mean $, interval, sessions,
effective N, trades) and, only after a pass, the holdout test; the descriptive rows of section 4; a **plain-loop verifier**
re-deriving at least 40 trades from the raw files with 0 differences; any deviation, listed. The LEDGER.md row is appended
at the end with the commit hashes and the Bonferroni status.
