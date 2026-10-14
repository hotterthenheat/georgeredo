# Pre-registration: high-win-rate short-premium grid on SPY / QQQ / IWM 0DTE at measured NBBO

Written 2026-10-13, before any code of this study was run on any date of the TEST period (the only TEST-period computation that
precedes the grid is the reproduction of an already published number, §9, which involves no choice that feeds the selection).
Nothing in this file is changed after the TEST run; any deviation found necessary is recorded in an "Amendments" section with
its time and reason, and the original text stays.

## 1. Question

For SPY, QQQ and IWM same-day-expiry options, filled at the measured NBBO, which configurations
(structure × strike distance × entry time × take-profit × stop × exit rule × event filter) have
(a) a win rate ≥ 70 % and (b) a day-clustered 95 % lower bound on the mean P&L per trade above zero in the TEST period,
when they are selected on the TRAIN period only. Negative results are valid outcomes.

## 2. Data and split

* Dataset: `research/thetadata/dataset` (loader `load.py`): 1-minute NBBO rows of the same-day expiry for strikes within ±2 % of
  the 09:31 underlying print (`chains/`), 1-minute underlying bars (`underlying/`).  A quote row stamped T is the NBBO in force at
  T:00; a stock bar stamped T covers [T, T+1 min), so the last trade price known at T is the close of the bar stamped T−1.
* TRAIN 2022-11-11 → 2024-12-31; TEST 2025-01-02 → 2026-10-09 (SPY, QQQ).  IWM: TRAIN 2024-04-19 → 2024-12-31 (flagged short,
  about 170 sessions), TEST 2025-01-02 → 2026-10-09.
* Sessions: every session with a chain file.  The nine early-close sessions (13:00 close) in the range are excluded
  (2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) because two of the
  four entry times and the 15:55 exit do not exist on them.  Sessions without a chain or underlying file are listed and excluded.
* Event days: `research/thetadata/vol_filters/events.csv`, FOMC rows (decision day of each scheduled meeting).  Month-end = the last
  trading session of each calendar month (the definition of `research/thetadata/vol_filters/build_daily.py`, used in
  `empirical_vol_filters_spx.md`), computed from the NYSE session calendar; 2026-10-09 (the last sample date) is not a month-end.

## 3. Trade construction

* Entry minute T ∈ {10:00, 11:00, 13:00, 14:05} ET.  Spot S = close of the underlying bar stamped T − 1 minute.
* Usable quote row: bid and ask non-null, ask > 0, ask ≥ bid.  At entry every leg must have a usable row stamped exactly T
  (otherwise the trade is skipped, reason `no_quote`).  After entry, an unusable row is replaced by the last usable row of that leg
  (forward fill), and the number of forward-filled exit rows is recorded.
* ATM strike K0 = the stored strike nearest to S with usable call and put rows at T (ties → the lower strike).
  Expected move EM = mid(call K0) + mid(put K0) at T, in $ per share.
* Short strikes at distance k·EM, k ∈ {0, 0.5, 1.0, 1.5}:
  k = 0 → short call and short put both at K0 (ATM straddle);
  k > 0 → short call at the smallest stored strike ≥ S + k·EM, short put at the largest stored strike ≤ S − k·EM.
  If the required strike lies beyond the stored band (no stored strike that far out) the trade is skipped, reason `out_of_band`,
  and counted (coverage is reported by k, structure, entry and ticker).
* Delta proxy (recorded, not used for selection): σ$ = EM·√(π/2) (an ATM straddle ≈ σ·√(2/π) for a driftless normal terminal
  price), proxy Δ = Φ(−|K − S| / σ$) per short leg.
* Structures: (i) short straddle / strangle (k = 0 straddle, k > 0 strangle); (ii) iron condor = the strangle plus a long call at
  the smallest stored strike ≥ S + (k + 1.0)·EM and a long put at the largest stored strike ≤ S − (k + 1.0)·EM; if a wing would
  coincide with its short strike the next stored strike outward is used; if no such strike is stored the trade is skipped
  (`out_of_band`).  The iron condor is not defined for k = 0.
* Fills: sell at the BID, buy at the ASK, per leg, at the row stamped T.  A leg (short or long) with bid = 0 at entry → the trade
  is skipped (`zero_bid`), exactly as instructed; for iron condors this also removes trades whose wing has a zero bid (counted).
  Net credit C = Σ bid(shorts) − Σ ask(longs); C ≤ 0 → skipped (`no_credit`).
* Fees: $0.70 per contract per side (opening and every closing trade); legs that expire are not charged a closing fee.
* All P&L is in $ per 1-lot (one contract per leg, multiplier 100).

## 4. Management rules (checked on minutes T+1 … 15:54)

* Cost to close X(m) = Σ ask(shorts) − Σ bid(longs) at the row stamped m (forward-filled as above).
* Take-profit p ∈ {none, 25 %, 50 %} of the initial credit: triggers at the first m with X(m) ≤ (1 − p)·C; filled at X(m) (a resting
  buy limit fills at the displayed ask of that row).
* Stop s ∈ {none, 1×, 2×} credit loss: triggers at the first m with X(m) ≥ (1 + s)·C; filled at X(m + 1) (the ASK/BID row of the
  next minute; a trigger at 15:54 fills at 15:55).
* The first trigger in time wins.  At a TP or stop exit every leg is closed (shorts at the ask, longs at the bid), except a long leg
  whose bid is 0, which cannot be sold and is left to expire.
* Exit rule if neither triggers:
  * **E1**: at 15:55 buy back each short leg at its ASK and sell each long leg at its BID, except legs whose ASK ≤ $0.05, which are
    left to expire (a long leg with bid 0 is also left to expire).
  * **E2**: hold all legs to expiry.
  * Legs left to expire are valued at intrinsic value against the settlement price = close of the last regular-session underlying
    bar (the bar stamped 15:59, i.e. the 16:00 close), with no spread and no fee.  Caveat (stated in every report): SPY, QQQ and IWM
    options are American and physically settled, trade until 16:15 ET and can be exercised on after-hours moves until 17:30 ET;
    this valuation ignores assignment, exercise-by-exception, after-hours risk and the cost of disposing of delivered shares.
* Diagnostic only (not in the grid, never selected): **E0** = buy back every leg at 15:55 (no leave-cheap-legs rule), to measure
  what the leave-cheap-legs rule contributes.

## 5. Event filters

(F0) none; (F1) skip FOMC decision days; (F2) on FOMC days the trade is entered at 14:05 instead of the configured entry time
(strikes and EM recomputed at 14:05; for configurations whose entry is already 14:05, F2 is identical to F0); (F3) skip days that are
FOMC decision days or month-end sessions.

## 6. The grid

7 structure-k cells (straddle k=0; strangle k=0.5, 1.0, 1.5; iron condor k=0.5, 1.0, 1.5) × 4 entries × 3 TP × 3 stops × 2 exits
(E1, E2) × 4 filters = **2,016 configurations per ticker** (126 of them, F2 at 14:05, duplicate their F0 twin, so 1,890 are
distinct).  Scopes: SPY, QQQ, IWM, and SPY+QQQ pooled (one trade per ticker per day; clusters = dates).  The same 2,016 per scope.

## 7. Statistics

* Per configuration × scope × period: n, win rate (share of trades with P&L > 0), mean P&L, day-clustered 95 % bootstrap CI of the
  mean (5,000 draws, seed 7; each draw resamples the period's sessions with replacement; mean = Σ P&L / Σ trades over the drawn
  sessions, so sessions without a trade contribute to neither; percentile interval), median, profit factor (Σ wins / |Σ losses|),
  maximum drawdown of the chronological cumulative P&L, worst 5 days (P&L summed by date), months spanned, mean credit, mean
  round-trip cost (Σ half-spreads of every filled leg at entry and exit + fees), coverage (trades / eligible sessions).
* **Selection (TRAIN only)**, per scope, among configurations with TRAIN n ≥ 100: (S1) the highest TRAIN lower bound; (S2) the
  highest TRAIN lower bound among configurations with TRAIN win rate ≥ 70 %.  Ties: higher TRAIN mean, then configuration id.
  The selections are written to `selection_train.json` before the TEST period is computed.
* The selected configurations are then evaluated on TEST (one pre-specified test each, no multiplicity adjustment needed for them).
* Full grid on TEST: number of distinct configurations with TEST lower bound > 0, compared with the number expected by chance
  under a global null (each configuration's mean = 0), estimated by a recentred joint day bootstrap (seed 8, 5,000 draws, same
  resampled days for every configuration so the cross-configuration correlation is kept): in each draw count configurations whose
  recentred bootstrap mean exceeds that configuration's lower half-width; report the mean and 95th percentile of the count.
* Data-snooping test on TEST over the grid: White's reality check with studentised statistics t_c = mean_c / se_c (se from the
  seed-7 bootstrap) and the max-statistic distribution max_c (mean*_c − mean_c) / se_c from the seed-8 joint draws; Romano–Wolf
  step-down at FWER 5 %.  Configurations with TEST n < 30 are left out of the max statistic.
* Random-entry baseline for every selected configuration: 5 draws (seeds 11–15); in draw s, `numpy.random.default_rng(s)` draws,
  for every (ticker, date) in sorted order (tickers SPY, QQQ, IWM; all sessions of the dataset ascending), one entry minute uniformly
  from 10:00 to 14:30 inclusive; the same structure, k, TP, stop, exit and filter (F2 → 14:05 on FOMC days) are applied.  The minute
  list is written to `random_minutes.csv.gz`.  Lane − baseline is paired by (ticker, date) and averaged over the five draws, with a
  day-clustered CI.
* **Gate** (COMPASS_RESEARCH_PLAN.md §1, items 1–2 as they apply to a measured-NBBO study): TEST lower bound > 0; TEST n ≥ 150;
  TEST spans ≥ 3 months; TEST mean − mean of the five random baselines > the configuration's mean TEST round-trip cost.  Fills are
  NBBO bid/ask (item 3); inputs are as-of the entry minute (item 4: spot from the bar ending at T, quotes stamped T, calendar
  events known in advance); seeds and code are committed (item 5).  The study's own objective adds TEST win rate ≥ 70 %.

## 8. Reported regardless of outcome

Grid tables (CSV per configuration with TRAIN and TEST metrics), the selections and their TEST results, the random baselines and
the gate verdict, the full-grid TEST distribution with the chance count and the reality check, the marginal effect of each rule
(TP, stop, E1 vs E2 vs diagnostic E0, filters) on win rate and mean, matched over the other dimensions, in TRAIN and TEST, and
coverage by k.  IWM is reported as incomplete if its chains are not complete when the study ends.

## 9. Sanity check before the grid

Recompute `research/thetadata/straddle_nbbo/RESULTS.md` T-A: 13:00 SPY+QQQ ATM straddle, sell both legs at the bid at 13:00, buy
both back at the ask at 15:55, $0.70 per contract per side, dates 2025-06-02 → 2026-10-09 (published +$8.60 [−6.07, 22.45],
n = 678), (a) with that study's strikes (`csv/straddles_nbbo.csv.gz`) and its bootstrap code, and (b) with this study's ATM rule.

## Amendments

**A1 (2026-10-13 23:58 UTC, before the grid engine was run on any date).**  The §9 reproduction showed that on days when the
underlying has moved more than 2 % from its 09:31 print by the entry minute (e.g. QQQ 2026-06-09 at 13:00: spot 692.57, stored strikes
709–737), "the stored strike nearest to S" is the edge of the band, not an at-the-money strike.  Clarification of §3: the ATM strike
K0 exists only when S lies inside the stored strike range [min stored strike, max stored strike]; otherwise every structure at that
entry is skipped with reason `out_of_band` and counted.  This is a definition fix, not a tuning choice (it does not depend on any
P&L); it makes the sample conditional on the entry-time spot being within the stored band, which is reported as a caveat with the
number of sessions affected per entry time.
