# Pre-registration: T-E (SPXW 13:00 straddle held to settlement) and a high-win-rate SPXW short-premium grid at measured NBBO

Written 2026-10-13 (UTC ≈ 23:55), before any code of this study was run on any date of the T-E window, the T-E holdout, or the
grid's TRAIN/TEST periods.  The only computation on option data that precedes this file is a look at the file layout of two
sessions (2022-05-13, 2024-06-12: column names, strike spacing).  The only computation that precedes it on any data is the tail
statistic in §T-E.4, computed from SPX index minutes 2017-06-01 → 2022-05-12 (before the first SPXW daily expiry, so outside every
window used here).  The SHA-256 of this file and the UTC time are written to `prereg_sha256.txt` before the first run.  Nothing in
this file is changed after the runs; any deviation found necessary is recorded under "Amendments" with its time and reason, and
the original text stays.  The design deliberately mirrors the sibling ETF pre-registration (`../etf/PREREGISTRATION.md`) so the two
grids can be compared; differences are SPXW-specific and listed in §G.9.

---------------------------------------------------------------------------------------------------------------------------------

## Part A — T-E (hypothesis H13 of `COMPASS_RESEARCH_PLAN.md` §8)

### T-E.1 Question
Does a 13:00 short ATM SPXW straddle, sold at the NBBO bid and **held to cash settlement**, with FOMC/CPI/NFP days excluded, have a
positive day-clustered 95 % lower confidence bound on its mean P&L per 1-lot?

### T-E.2 Window — and the one deviation from §8
* §8 wrote the window as 2022-01-03 → 2025-05-29.  SPXW same-day (daily) expirations exist only from **2022-05-13**
  (`research/thetadata/dataset/README.md`, `first_daily.py`; before that date most sessions have no expiring SPXW series and a
  "13:00 0DTE straddle" is undefined).  **The T-E window is therefore 2022-05-13 → 2025-05-29.**  This is the only deviation.
* Sessions: NYSE sessions in the window (calendar `research/thetadata/dataset/calendar_2017_2026.csv`) with a chain file, minus the
  early-close sessions (2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24), minus event days.  Expected count
  from the calendar: 757 regular sessions, 663 after the exclusion (≥ 500 required).
* Event exclusion fixed in advance: every date of `research/thetadata/vol_filters/events.csv` with event FOMC, CPI or NFP.
* Holdout: 2025-06-02 → 2026-10-09 (339 regular sessions, 299 ex-events), evaluated afterwards with **no change of any kind**.
  Disclosure: this holdout is the window on which H13 was observed (T-C, §8: [−18.5, +288.6] ex-events with the official close);
  its result is therefore not independent evidence — T-E's evidential weight sits in the 2022-05-13 → 2025-05-29 window.

### T-E.3 Trade (the T-C entry rule, `index_tests/tc_spxw_straddle/METHODOLOGY.md`)
* Spot = SPX index `price` stamped 13:00 (`index/SPX`), the index value at 13:00:00.
* Strike K = round(spot / 5) × 5 (Python `round`), used if the chain holds both a call and a put row at K stamped 13:00; otherwise
  the nearest stored strike with both rows (flagged).
* Sell one call and one put at the NBBO **bid** of the 13:00 row.  Skip (and list) the session if either leg has a null or zero bid
  or ask, or ask < bid.
* Hold to settlement: P&L = (bid_call + bid_put − |S − K|) × 100 − $2 (fees $1.00 per contract, entry side only; no exit trade).
  S = SPX `price` stamped **16:00** in `index/SPX` (if null: the last non-null price stamped 15:59–16:00, flagged).
  Stated approximation: the official SPXW exercise-settlement value is computed from the components' closing-auction prices and
  can differ from the 16:00:00 index print by several basis points; as a sensitivity only (never the verdict), the same run is
  repeated with the official SPX close from the cached ThetaData EOD files (`$SP/theta/cache/index_tests/index_history_eod__*`).

### T-E.4 Margin and tail sizing (stated before the run; reporting conventions, not part of the pass rule)
* Margin (Cboe strategy-based, short index straddle): the larger side's requirement (100 % of proceeds + 15 % of index value − OTM
  amount, minimum 10 %) plus the other side's proceeds ⇒ ≈ 0.15 × SPX × 100 + credit per lot (≈ $60,000 at SPX 4,000, ≈ $90,000 at
  6,000).  Portfolio margin (Cboe scenario −8 %/+6 %) would be ≈ (0.08 × SPX − credit) × 100; brokers may add 0DTE house margin.
  Return on capital, when quoted, uses the Reg-T figure computed per day.
* Tail: the largest 13:00 → 16:00 SPX move in 2017-06-01 → 2022-05-12 (1,236 regular sessions, computed from `index/SPX` before
  this file was written) is **6.33 %** (2020-03-13; next −4.51 % 2020-03-12; 99th percentile of |move| 2.44 %, 99.9th 4.39 %).
  Stress loss per lot = (0.0633 × SPX(13:00) − credit) × 100.  **Tail sizing rule: capital per lot = stress loss / 0.08**
  (an 8 % max-loss budget against the stress move), i.e. roughly 0.79 × notional per straddle.
* Also reported (descriptive): full-Kelly capital per lot C* = argmax mean log(1 + P&L/C) on the T-E window series, quarter-Kelly
  = 4 C*, and their drawdowns / P(end < start) on the holdout and on 3,000 day-resampled paths (seed 7), as in
  `research_notes/High win rate 0DTE lanes/filters_regimes_and_sizing.md` §5.

### T-E.5 Statistics and pass rule
* n, total, mean P&L per 1-lot, 95 % CI by day-clustered percentile bootstrap (5,000 draws, `numpy.random.default_rng(7)`, the
  `cluster_boot` function of `analyze_tc.py`), win rate (P&L > 0), profit factor, maximum drawdown of the cumulative 1-lot P&L,
  five worst days, by year.
* **PASS iff lower bound > 0 and n ≥ 500** on 2022-05-13 → 2025-05-29.  Holdout: reported with the same statistics; it "confirms" iff
  its lower bound > 0 with n ≥ 150 spanning ≥ 3 months (plan §1.2).
* Also reported, not part of the T-E pass rule: the plan §1 gate items — random-entry baseline (5 draws, entry minute uniform on
  10:00–14:30, seeds 11–15, ATM straddle at that minute, same hold-to-settlement and exclusion), lane − baseline vs one round-trip
  cost (entry half-spreads × 100 + $2), the adverse-fill sensitivity (one $0.05 tick worse per leg), and the official-close
  sensitivity.

---------------------------------------------------------------------------------------------------------------------------------

## Part G — pre-registered SPXW short-premium grid

### G.1 Question
For SPXW same-day options filled at the measured NBBO, which configurations (structure × strike distance × entry time ×
take-profit × stop × exit rule × event filter) have (a) a TEST win rate ≥ 70 % and (b) a TEST day-clustered 95 % lower bound on mean
P&L per trade above zero, when selected on TRAIN only?  How do win rate and expectancy trade off?  Negative results are valid.

### G.2 Data and split
* Dataset `research/thetadata/dataset` (loader `load.py`): `chains/SPXW/{date}.parquet` (1-minute NBBO of the same-day SPXW expiry,
  strikes within ±2 % of the 09:31 SPX price; a row stamped T is the NBBO in force at T:00) and `index/SPX/{date}.parquet` (index
  value at each minute boundary).
* **TRAIN 2022-05-13 → 2024-12-31; TEST 2025-01-02 → 2026-10-09.**  Expected regular sessions: 656 TRAIN, 441 TEST.
* Sessions: every session with a chain file; the nine early-close sessions in range (2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03,
  2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) are excluded (two entries, the 15:55 exit and the 16:00 settlement do
  not exist on them).  Missing chain or index files are listed and excluded.  If the chain build has not finished when the run must
  start, the run uses what exists and reports coverage.
* Events: `research/thetadata/vol_filters/events.csv` (FOMC = decision day of each scheduled meeting; CPI; NFP).  Month-end = last
  trading session of each calendar month (definition of `vol_filters/build_daily.py`, used in `empirical_vol_filters_spx.md`), from
  the NYSE calendar; 2026-10-09 is not a month-end.
* Disclosure: TEST overlaps the T-C window (2025-06-02 → 2026-10-09), whose 13:00 straddle results (15:55 buy-back, stop,
  settlement) were published before this file; for the 13:00 straddle family TEST is therefore not unseen.

### G.3 Trade construction
* Entry minute T ∈ {10:00, 11:00, 13:00, 14:05} ET.  Spot S = SPX `price` stamped T.
* Usable quote row: bid and ask non-null, ask > 0, ask ≥ bid.  At entry every leg must have a usable row stamped exactly T (else skip,
  `no_quote`).  After entry an unusable row is replaced by that leg's last usable row (forward fill; count recorded).
* ATM strike K0 = round(S / 5) × 5 if usable call and put rows exist there at T, else the nearest stored strike with both (ties →
  lower).  Expected move EM = mid(call K0) + mid(put K0) at T (index points).
* Short strikes at k·EM, k ∈ {0, 0.5, 1.0, 1.5}: k = 0 → call and put at K0; k > 0 → short call at the smallest stored strike
  ≥ S + k·EM, short put at the largest stored strike ≤ S − k·EM ("nearest listed strike outward").  A required strike beyond the
  stored band → skip, `out_of_band` (counted by k, structure, entry).
* Structures (8 structure-k cells):
  (i) naked: k = 0 short straddle; k = 0.5, 1.0, 1.5 short strangle;
  (ii) winged: long call at the smallest stored strike ≥ S + (k + 1.0)·EM and long put at the largest stored strike
  ≤ S − (k + 1.0)·EM; k = 0 is the **iron butterfly** (shorts at K0, wings at 1.0·EM), k = 0.5, 1.0, 1.5 the **iron condor**.
  A wing that would coincide with its short strike moves to the next stored strike outward; none stored → `out_of_band`.
* Fills: sell at the BID, buy at the ASK, per leg, at the row stamped T.  **A leg (short or long) with bid = 0 at entry → skip**
  (`zero_bid`), as instructed; for winged structures this also removes trades whose wing is bid 0 (counted).  Diagnostic only,
  never selected: the winged cells re-run with zero-bid wings allowed (bought at the ask), labelled `W*`.
  Net credit C = Σ bid(shorts) − Σ ask(longs); C ≤ 0 → skip (`no_credit`).
* Fees $1.00 per contract per side (opening and every closing trade); legs left to settle pay no closing fee.  P&L in $ per 1-lot
  (one contract per leg, multiplier 100).

### G.4 Management (checked on minutes T+1 … 15:54)
* Cost to close X(m) = Σ ask(shorts) − Σ bid(longs) at the row stamped m (forward-filled as above).
* Take-profit p ∈ {none, 25 %, 50 %} of C: first m with X(m) ≤ (1 − p)·C; filled at X(m).
* Stop s ∈ {none, 1×, 2×} credit loss: first m with X(m) ≥ (1 + s)·C; filled at X(m+1) (next-minute ASK for shorts / BID for
  longs; a trigger at 15:54 fills at 15:55).
* First trigger in time wins.  At a TP or stop exit every leg is traded (shorts at the ask, longs at the bid) except a long leg whose
  bid is 0, which is left to settle.
* If neither triggers:
  **E1** at 15:55 buy back each short at its ASK and sell each long at its BID, except legs whose ASK ≤ $0.10 (two SPXW ticks) and
  long legs with bid 0, which are left to settle;
  **E2** hold every leg to settlement (no exit spread, no exit fee).
  Settlement value of a leg = intrinsic value against the SPX `price` stamped 16:00 (same approximation statement as T-E.3).
* Diagnostic only (not in the grid, never selected, not counted for multiplicity): **E0** = buy back every leg at 15:55 (shorts at
  the ask, longs at the bid if > 0), to measure what "leave cheap legs" and "hold to settlement" add.

### G.5 Event filters
(F0) none; (F1) skip FOMC decision days; (F2) on FOMC days enter at 14:05 instead of the configured time (strikes and EM recomputed
at 14:05; for 14:05 configurations F2 ≡ F0); (F3) skip FOMC days and month-end sessions; (F4) skip FOMC, CPI and NFP days (the T-E
filter).

### G.6 The grid
8 structure-k cells × 4 entries × 3 TP × 3 stops × 2 exits (E1, E2) × 5 filters = **2,880 configurations**; the 144 F2-at-14:05
configurations duplicate their F0 twins, so **2,736 are distinct** (the multiplicity count).  The T-E rule is one cell of the grid
(13:00, k = 0 naked, no TP, no stop, E2, F4) up to the strike tie rule.

### G.7 Statistics, selection, multiplicity
* Per configuration × period: n, win rate (P&L > 0), mean, day-clustered 95 % bootstrap CI of the mean (5,000 draws, seed 7; each
  draw resamples the configuration's trade days with replacement; percentile interval), median, total, s.d., profit factor, maximum
  drawdown of the chronological cumulative P&L, worst 5 days, months spanned, mean credit, mean round-trip cost (Σ half-spreads of
  every traded leg at entry and exit × 100 + fees), coverage (trades / eligible sessions) and skip counts by reason; mean P&L under an
  adverse-fill sensitivity (one $0.05 tick worse on every traded leg).
* **Selection (TRAIN only)** among configurations with TRAIN n ≥ 150: (S1) highest TRAIN lower bound; (S2) highest TRAIN lower bound
  among configurations with TRAIN win rate ≥ 70 %.  Ties: higher TRAIN mean, then configuration id.  Written to
  `selection_train.json` before any TEST statistic is computed.  The TRAIN top 10 by lower bound are also carried to TEST
  (descriptive).
* The selected configurations are evaluated once on TEST.
* Full grid on TEST (and TRAIN): number of distinct configurations with lower bound > 0, against the number expected by chance under
  the global null (every configuration's mean = 0), from a recentred joint day bootstrap (seed 8, 5,000 draws, the same resampled
  days for all configurations): in each draw count configurations whose recentred bootstrap mean exceeds that configuration's lower
  half-width (mean − lower bound); report the mean and 95th percentile of the count.  White's reality check with studentised
  statistics t_c = mean_c / se_c (se = s.d. of the seed-7 bootstrap means) and the max-statistic distribution of
  max_c (mean*_c − mean_c)/se*_c from the seed-8 draws; Romano–Wolf step-down at FWER 5 %.  Configurations with n < 30 are left out
  of the max statistic.
* Random-entry baseline for every selected configuration: 5 draws, seeds 11–15; in draw s, `numpy.random.default_rng(s)` draws one
  entry minute uniformly on 10:00–14:30 inclusive for every session of the sorted list of the 1,097 regular sessions
  2022-05-13 → 2026-10-09 (written to `random_minutes.csv` before use); same structure, k, TP, stop, exit and filter (F2 → 14:05 on
  FOMC days).  Lane − baseline paired by date, averaged over the five draws, day-clustered CI.
* **Gate** (`COMPASS_RESEARCH_PLAN.md` §1 items 1–5 as they apply to a measured-NBBO study): TEST lower bound > 0; TEST n ≥ 150;
  TEST spans ≥ 3 months; TEST mean − mean of the five random baselines > the configuration's mean TEST round-trip cost; fills at NBBO
  bid/ask and the edge survives the adverse-fill sensitivity; inputs as-of the entry minute (spot and quotes stamped T, calendar
  events known in advance); seeds and code in the repository.  The study's objective adds TEST win rate ≥ 70 %.

### G.8 Sizing (for every configuration whose TEST lower bound is > 0)
Capital per 1-lot (a) at quarter-Kelly: 4 × C*, C* = argmax mean log(1 + P&L/C), computed on TRAIN (the decision-time estimate) and,
for reference, on TEST; (b) at an 8 % max-loss budget: winged structures — structural maximum loss max over TRAIN trades of
(wider wing width − credit) × 100 + entry fees; naked — the worst TRAIN day loss; capital = that loss / 0.08.  For each: maximum
drawdown of the actual TEST sequence, and over 3,000 day-resampled TEST-length paths (seed 7) the median maximum drawdown,
P(drawdown > 20 %), P(> 30 %), P(> 50 %) and P(end below start).

### G.9 Differences from the ETF sibling (SPXW-specific)
Spot is the index value stamped T (no bar lag needed: the index row is the value at T:00); ATM uses the T-C rounding rule (so T-E is
nested in the grid); fees $1.00 (instructed) instead of $0.70; the leave-to-settle threshold is ask ≤ $0.10 (two SPXW ticks) instead
of $0.05; SPXW is European and cash-settled, so legs left to settle carry no assignment or after-hours risk (only the 16:00-print vs
official-close approximation); a fifth filter F4 and an iron butterfly cell (k = 0 winged) are added.

### G.10 Reported regardless of outcome
T-C reproduction (below); T-E verdict and holdout; grid CSV per configuration with TRAIN and TEST metrics; selections and their
TEST results with random baselines and the gate verdict; the TEST and TRAIN chance counts and reality check; the marginal effect of
each rule (TP, stop, E0 vs E1 vs E2, filters, entry time, k, structure) on win rate and mean, matched over the other dimensions;
coverage by k, structure and entry; the win-rate/expectancy trade-off table; sizing for TEST-positive configurations.

### G.11 Sanity check before the new work
Recompute `index_tests/tc_spxw_straddle/RESULTS.md` on 2025-06-02 → 2026-10-09 from the dataset: 13:00 ATM straddle, sell at the bid,
buy back at the 15:55 ask, $1/side (published +$72.4 [−75.8, 214.2], n = 339); hold to settlement (+$156.8 [+5.8, +305.0]);
ex-FOMC/CPI/NFP hold to settlement ([−18.5, +288.6], n = 299).  T-C settled on the official close; both the official close (cache)
and the 16:00 print are reported, and per-session quotes are compared with `tc_straddles.csv`.

## Amendments

(none at the time of writing)

**Amendment 1 (2026-10-14 ≈ 00:04 UTC, before any TEST-period statistic or T-E/holdout statistic was computed; found while
testing the code on a dev split of early TRAIN dates, 2022-05 → 2023-06).**  In G.7, "max_c (mean*_c − mean_c)/se*_c" is
implemented as the ETF sibling does: the denominator is the configuration's seed-7 bootstrap standard error se_c, fixed across the
seed-8 draws (primary).  Studentising within each draw (se from the resampled days) is unstable for short-premium series whose
losses are rare and large — a draw that omits the one large loss has a near-zero s.e. and a large positive deviation, which put the
95th percentile of the null max-t near 30 on the dev split — so it is reported only as a secondary column.  Nothing else changes.
