# Empirical test: do Unusual Whales option-flow and dark-pool measures predict 15/30/60-minute SPY/QQQ/IWM returns (and ATM 0DTE option returns) after costs?

Run date 2026-10-13. Code and CSVs: `/home/user/georgeredo/research/flow_predictors/` (every number below is in a CSV there; the shell wrapper that sets `BT_CACHE` and sources the token env is in the session scratchpad and is not part of the repository). Nothing in `backtest/` or `evidence/` was modified; `backtest/data.py`, `backtest/exits.py` and `backtest/costs.py` are imported as-is.

**One-line verdict: none of the 58 predictive feature × horizon × ticker cells (signed net premium, signed ask-bid volume share, net delta, market tide, dark-pool buy share and net notional, per-strike premium bursts) has a Spearman IC or top-minus-bottom quintile spread distinguishable from zero after Bonferroni or Benjamini-Hochberg correction; nominal point estimates are |IC| ≤ 0.065 and quintile spreads of 0.2-2 bp of underlying return, below the ≈1.2 bp option cost hurdle; the best feature expressed as an ATM 0DTE rule returns −2.4 % per trade after costs, indistinguishable from random entries (−2.3 %).**

## Method, data and cost hurdle (applies to every test)

### Takeaway
Three complete 1-minute datasets for 339 sessions (2025-06-02..2026-10-09, three early-close days dropped), a fully paged dark-pool sample of 90 sessions × 3 tickers, and a 40-session per-strike sample; statistics are pooled Spearman ICs with daily-block bootstrap CIs, quintile forward returns in bp, hit rates, and a multiple-testing correction over 62 main cells. Within-day ("daily") ICs are reported but shown to be mechanically biased and are not used as evidence.

### Cited Findings
- Feature definitions (exact, from the docstring of [build_panel.py](/home/user/georgeredo/research/flow_predictors/build_panel.py)); window = the last 15 one-minute `net-prem-ticks` bars t-14..t, all complete at the close of minute t, aligned to the underlying 1-minute bar closing at the same second:
  - F1 = Σ(net_call_premium − net_put_premium) [$; > 0 bullish]
  - F2 = [(call_vol_ask − call_vol_bid) − (put_vol_ask − put_vol_bid)] / (call_vol_ask + call_vol_bid + put_vol_ask + put_vol_bid) [signed directional ask-minus-bid volume share]
  - F2u = [(call_vol_ask + put_vol_ask) − (call_vol_bid + put_vol_bid)] / same denominator [the literal unsigned "ask-side minus bid-side share"; not directional]
  - F3 = Σ net_delta over the 15 bars (= change of cumulative net delta over 15 minutes)
  - Forward returns r_h = ln(close[t+h]/close[t]), h ∈ {15, 30, 60}; t from 09:45 to 15:30 and t+h ≤ 15:59; ≥ 12 of the 15 flow minutes must be present.
  - Regime: POS if close[t] > the PRIOR session's `gex-levels.gamma_flip`, else NEG (no look-ahead). Time-of-day buckets 09:45-10:30, 10:30-12:00, 12:00-14:00, 14:00-15:30.
- `stock/{t}/net-prem-ticks?date=` returns ~405 one-minute rows per day (09:30-16:14 ET) whose values are per-minute, not cumulative: SPY 2026-09-15 call_volume sums to 4.78 M and put_volume to 5.38 M contracts for the day — [probe output recorded in this session; endpoint description in the UW OpenAPI spec](https://api.unusualwhales.com/api/openapi).
- `market/market-tide?date=` (5-minute, 81 rows/day) is cumulative since the open, and the row stamped T holds the value through T+4:59: on 2026-09-15 every 5-minute row equals the 1-minute-interval row at T+4 (e.g. 09:30 → 407,886 / −2,746,727 = the 1-minute row at 09:34). The tide row T is therefore only known at T+5:00 and is aligned to the SPY bar closing at T+4:59 ("tradable"); the "contemp" alignment (bar closing at T−0:01) is kept only as a non-tradable reference — [build_panel.py](/home/user/georgeredo/research/flow_predictors/build_panel.py).
- Panel sizes: 117,265-117,268 ticker-minutes per ticker, 339 sessions each, 0 skipped days; tide panel 22,372 tradable 5-minute observations — [panel_flow.csv.gz](/home/user/georgeredo/research/flow_predictors/panel_flow.csv.gz), [panel_tide.csv.gz](/home/user/georgeredo/research/flow_predictors/panel_tide.csv.gz).
- Statistics ([stats.py](/home/user/georgeredo/research/flow_predictors/stats.py)): pooled Spearman IC per cell; 95 % CI and SE from a daily-block bootstrap (B = 2000 for main cells, 1000 for conditional cells) that resamples trading days with replacement using per-day sufficient statistics of the globally ranked data; two-sided p from the normal approximation IC/SE. Quintiles are pooled per ticker; the Q5−Q1 spread CI uses the same day bootstrap. Hit rates: P(r>0 | Q5), P(r<0 | Q1) and sign agreement.
- Within-day ("daily") ICs are mechanically negative: on simulated iid random walks with the panel's shape (339 days × 390 minutes), the within-day Spearman IC of a trailing-15-minute return against the forward 15/30/60-minute return is −0.038 / −0.063 / −0.114 (t = −4.3 / −6.2 / −10.6) — [placebo_daily_ic.py](/home/user/georgeredo/research/flow_predictors/placebo_daily_ic.py). The real-data daily ICs (e.g. QQQ F2 vs r60: −0.136, t = −13.8; SPY F1 vs r60: −0.078, t = −7.1) are of the same size and sign and are therefore NOT evidence of mean reversion — [flow_ic_main.csv](/home/user/georgeredo/research/flow_predictors/flow_ic_main.csv).
- Cost hurdle in underlying-return units: 1 cent per share round trip at the sample-median spot = 0.15 bp (SPY, 684), 0.16 bp (QQQ, 617), 0.39 bp (IWM, 256). For the option route, 3.4 % of premium per round trip with the observed ATM 0DTE SPY premium (median 0.175 % of spot across 1,212 entries; 0.21 % in the 09:00 hour falling to 0.08 % in the 15:00 hour) and delta ≈ 0.5 requires ≈ 1.2 bp of favourable underlying move before theta — [trade_rule_SPY_F1.csv](/home/user/georgeredo/research/flow_predictors/trade_rule_SPY_F1.csv). For scale, the standard deviation of 30-minute returns is 16 bp (SPY), 22 bp (QQQ), 25 bp (IWM).
- Multiple testing ([mt_summary.py](/home/user/georgeredo/research/flow_predictors/mt_summary.py), [mt_summary.csv](/home/user/georgeredo/research/flow_predictors/mt_summary.csv)): 62 main cells = 36 flow (3 tickers × 4 features × 3 horizons) + 4 tide (tradable) + 12 dark pool (3 tickers × {D1, D2} × 2 horizons) + 10 burst cells (2 filters × {underlying 15/30/60, contract net 15/30}); Bonferroni threshold 0.05/62 = 0.00081; BH at q = 0.05. Conditional cells (regime, time of day) are reported separately: 216 flow, 24 tide, 108 dark pool.
- Runtime of a full reproduction (cache warm for bars/GEX): cheap prefetch 1,368 requests in 142 s; dark-pool paging 2,400 requests in ≈ 13.5 min; per-strike 240 requests ≈ 1 min; option bars ≈ 1,100 contract-days for the trading rule and 2,238 for bursts (most already cached); analyses ≈ 6 min — logs recorded in this session; cache now 387 MB.

### Inferences
- The pooled day-block-bootstrap IC is the only statistic among those computed that is both tradable (no look-ahead) and unbiased by within-day demeaning, so the verdicts below rest on it and on the quintile spreads.

### Gaps
- Bootstrap replicates reuse the full-sample ranks (standard shortcut); re-ranking inside each replicate would widen CIs slightly, which only strengthens the null results.
- `net-prem-ticks` minute stamps were assumed to be bucket starts (trades 09:45:00-09:45:59 in the 09:45 row); if UW stamps bucket ends the features are one minute staler than assumed, which again only strengthens the nulls.

## Key question 1 — Signed flow (F1 net premium, F2 ask-bid volume share, F3 net-delta change) vs forward 15/30/60-minute returns, by GEX regime and time of day

### Takeaway
All 36 pooled ICs lie between −0.011 and +0.020 with bootstrap CIs covering zero (smallest p = 0.064); Q5−Q1 spreads are −0.7 to +2.1 bp; by regime and time of day the 216 conditional cells contain 3 nominal p < 0.05 (chance expectation ≈ 11) and none survives correction.

### Cited Findings
- Main cells ([flow_ic_main.csv](/home/user/georgeredo/research/flow_predictors/flow_ic_main.csv)), pooled IC [95 % CI], Q5−Q1 spread in bp [CI], hit rates P(r>0|Q5)/P(r<0|Q1):
  - SPY F1: h15 0.007 [−0.010, 0.025], spread 0.62 bp [0.00, 1.29], 50.9 %/49.5 %; h30 0.020 [−0.002, 0.041] p = 0.072, spread 1.07 bp [−0.05, 2.21], 52.7 %/49.8 %; h60 0.015 [−0.007, 0.037], spread 1.23 bp [−0.41, 2.87].
  - SPY F2: h15 0.010 [−0.007, 0.026], spread 0.60 bp [0.04, 1.18] (nominal p = 0.042); h30 0.013 [−0.006, 0.031]; h60 −0.003 [−0.024, 0.016].
  - SPY F3: h15 0.007, h30 0.015 [−0.004, 0.034], h60 −0.002; spreads 0.56 / 0.78 / 0.37 bp, all CIs include 0.
  - QQQ F1: −0.008 / −0.005 / −0.011 (all CIs include 0; spreads 0.15 / 0.21 / −0.35 bp). QQQ F2: −0.010 / −0.009 / −0.010 (spreads −0.40 / −0.36 / −0.35 bp). QQQ F3: −0.008 / −0.006 / −0.004.
  - QQQ F2u (unsigned aggressor share): 0.014 [−0.002, 0.029] p = 0.086; 0.019 [−0.001, 0.038] p = 0.064; 0.012 [−0.013, 0.036]; spreads 0.67 / 0.75 / 0.40 bp.
  - IWM F1: 0.011 / 0.012 / 0.001 (spreads 0.73 / 1.17 / 0.39 bp, CIs include 0). IWM F2: 0.002 / 0.004 / −0.000. IWM F3: −0.001 / 0.002 / −0.009. IWM F2u: 0.004 / 0.013 / 0.018 [−0.005, 0.041] p = 0.126, spread at h60 2.11 bp [0.11, 4.06] (nominal p = 0.039, hit rate 52.5 %/49.5 %).
  - Sign agreement between feature sign and forward-return sign is 49.2-50.5 % in every cell.
- The features are mostly the recent move: Spearman correlation of each feature with the trailing 15-minute return is 0.51 (SPY F1), 0.67 (SPY F2), 0.65 (SPY F3), 0.47/0.62/0.62 (QQQ), 0.26/0.45/0.40 (IWM); F2u is uncorrelated with it (0.05, 0.03, −0.01) — column `ic_vs_trailing15` in [flow_ic_main.csv](/home/user/georgeredo/research/flow_predictors/flow_ic_main.csv).
- Conditional cells ([flow_ic_conditional.csv](/home/user/georgeredo/research/flow_predictors/flow_ic_conditional.csv), 216 cells): 3 with nominal p < 0.05; strongest SPY F1 vs r60 in 10:30-12:00: IC 0.066 [0.020, 0.108], p = 0.0037, spread 4.19 bp [−0.07, 8.14], hit rates 57.3 %/52.0 %, n = 30,495; next QQQ F1 vs r60 in 14:00-15:30: IC −0.060 [−0.113, −0.004] (wrong sign); SPY F1 vs r30 in POS gamma: IC 0.029 [−0.001, 0.057], p = 0.044, spread 1.50 bp [0.13, 2.93]. Bonferroni threshold for 216 cells is 0.00023; BH also rejects none.
- Regime split for SPY F1 (h30): POS IC 0.029 (n = 63,924) vs NEG −0.025 to +0.01 range across features; no feature flips to a reliable sign in NEG gamma — [flow_ic_conditional.csv](/home/user/georgeredo/research/flow_predictors/flow_ic_conditional.csv).

### Inferences
- Even taking the nominally best unconditional cell at face value (SPY F1, 30 min: Q5 mean +0.45 bp, Q1 mean −0.62 bp), a one-sided trade would expect ≈ 0.5 bp of underlying move: above the 0.15 bp share hurdle but a third of the ≈ 1.2 bp ATM-0DTE hurdle, with a per-trade Sharpe of ≈ 0.5/16 ≈ 0.03.
- The within-bucket SPY F1 10:30-12:00 result (IC 0.066) is the kind of cell one expects to find once among 216 at this p-value; it is not corroborated by the adjacent horizons (h30 IC 0.041, p = 0.066) or by QQQ (IC −0.010 to +0.027 in the same bucket).

### Gaps
- No feature was tested with longer windows (30/60-minute flow) or with volume-normalisation other than F2; the task fixed 15-minute windows.
- `net_delta` units (shares vs contracts) are undocumented; Spearman is invariant to scale so this does not affect the IC.

## Key question 2 — Market tide (market-wide net premium level and 30-minute change) vs SPY forward 30/60-minute returns

### Takeaway
With the correct (tradable) alignment the tide level and its 30-minute change have ICs of −0.002 to +0.020 (p ≥ 0.41) against SPY's forward 30/60-minute return; the same features aligned contemporaneously show IC 0.072 (p ≈ 1e-7), i.e. the information is coincident with the price move, not ahead of it.

### Cited Findings
- Tradable alignment ([tide_ic_main.csv](/home/user/georgeredo/research/flow_predictors/tide_ic_main.csv), n = 22,372 / 20,338, 339 days): T_level h30 IC 0.012 [−0.021, 0.044], spread 0.43 bp [−1.20, 1.93]; h60 0.020 [−0.027, 0.069], spread 0.92 bp [−2.36, 3.89]; T_chg30 h30 0.007 [−0.022, 0.035], spread 0.40 bp; h60 −0.002 [−0.039, 0.036], spread 0.26 bp. Hit rates 53 %/49-50 %.
- Non-tradable contemporaneous alignment (same file, `align = contemp`): T_chg30 h30 IC 0.072 [0.046, 0.098], p = 9.6e-8, spread 3.30 bp [1.92, 4.67]; h60 0.045 [0.010, 0.081]; T_level h30 0.029 [−0.003, 0.060].
- Conditional ([tide_ic_conditional.csv](/home/user/georgeredo/research/flow_predictors/tide_ic_conditional.csv), 24 cells): no cell with p < 0.05; the largest is T_chg30 h30 in 10:30-12:00, IC 0.041 [−0.011, 0.090], spread 3.21 bp [0.01, 6.30].

### Inferences
- The 5-minute bucket stamp convention matters: a naive join of the tide row T to the price at T would have produced a spurious "predictive" IC of 0.07.

### Gaps
- The 1-minute tide variant (`interval_5m=false`) and `otm_only=true` were not tested (one probe day only).

## Key question 3 — Dark pool: buy-initiated share and net notional over the last 30 minutes vs forward 30/60-minute returns; data completeness

### Takeaway
On 90 fully paged sessions × 3 tickers, dark-pool buy share and net notional have ICs between −0.065 and +0.037 with every CI covering zero (closest: SPY buy-share vs 60-minute, IC −0.065, p = 0.051, negative sign); the per-day print feed is complete once paged with `older_than` (median 13.8k SPY / 11.5k QQQ / 2.3k IWM RTH prints per day, 30-page cap hit once), but `tracking_id` is null for Sep-Dec 2025 sessions, which silently truncates any client that de-duplicates on it.

### Cited Findings
- Definitions ([analyze_dp.py](/home/user/georgeredo/research/flow_predictors/analyze_dp.py)): per minute t (10:00-15:30) over prints executed in t-29..t: D1 = notional with price ≥ NBBO mid / total notional (literal buy-initiated share); D1x = (notional above mid − notional below mid)/total (at-mid prints neutral); D2 = notional(≥ mid) − notional(< mid) in $. Prints are binned by `executed_at` (ET) and treated as known at the close of that minute.
- Main cells ([dp_ic_main.csv](/home/user/georgeredo/research/flow_predictors/dp_ic_main.csv), n = 29,700 / 27,000 per ticker, 90 days): SPY D1 h30 −0.030 [−0.078, 0.017]; h60 −0.065 [−0.130, −0.002], p = 0.051, spread −2.17 bp [−6.65, 2.37]; SPY D2 h30 −0.011, h60 −0.044 [−0.112, 0.023]. QQQ D1 0.010 / 0.019; D2 0.024 / 0.037 [−0.032, 0.101], spread 3.86 bp [−3.45, 10.50]. IWM D1 −0.011 / −0.058 [−0.119, 0.002] p = 0.059, spread −4.80 bp [−10.77, 0.92]; IWM D2 −0.007 / −0.045. D1x behaves like D1 (SPY h60 −0.053, IWM h60 −0.045). Hit rates P(r>0|Q5) 47-53 %.
- Conditional ([dp_ic_conditional.csv](/home/user/georgeredo/research/flow_predictors/dp_ic_conditional.csv), 108 cells): 9 nominal p < 0.05, the strongest IWM D1 vs r60 in 14:00-15:30: IC −0.170 [−0.297, −0.048], p = 0.007 (n = 5,400; the sign is contrarian), and QQQ D1x vs r60 in 10:30-12:00: IC 0.129 [0.032, 0.237], p = 0.014; Bonferroni threshold 0.00046; none survives.
- Completeness ([darkpool_coverage.csv](/home/user/georgeredo/research/flow_predictors/darkpool_coverage.csv), 270 ticker-days, sample 2025-06-30..2026-10-08): `darkpool/{t}?date=` returns the newest 500 prints (the `limit` schema says "Max: 500"), ordered newest-first; paging with `older_than = executed_at of the last row` (and `newer_than`) returns the full day: mean RTH prints SPY 16,084 (min 9,385, max 29,127, mean 33 pages), QQQ 13,032 (7,347-29,437), IWM 2,482 (1,515-5,405); all first prints at 09:30:00-09:30:01 ET; 1 ticker-day (QQQ 2026-06-05) hit the 60-page/30,000-print cap I imposed; every print carried nbbo_bid/ask; `trf_executed_at` equals `executed_at` on every print (reporting latency is not observable).
- Dark-pool print volume is 20.2 % (SPY median), 20.8 % (QQQ), 14.3 % (IWM) of consolidated 1-minute bar volume; 18.6 % / 14.1 % / 20.4 % of prints execute exactly at the NBBO mid (these count as "buys" in D1 and are neutral in D1x) — same file.
- `tracking_id` is null for the 13 sampled sessions between 2025-09-09 and 2025-12-02 (all three tickers); a first pass that de-duplicated pages by `tracking_id` kept only ≈ 250-500 prints from the last minutes of those days; the composite-key fix in [common.py](/home/user/georgeredo/research/flow_predictors/common.py) and [refetch_dp_gaps.py](/home/user/georgeredo/research/flow_predictors/refetch_dp_gaps.py) restored 1,515-29,437 prints per ticker-day.

### Inferences
- If anything, a higher dark-pool buy share is weakly followed by lower 60-minute returns in SPY and IWM (contrarian sign), but the effect is not significant even before correction and reverses sign in QQQ.
- The data cost of using this feed live is non-trivial (≈ 30 requests per ticker-day for SPY); the websocket would be needed for real-time use.

### Gaps
- Reporting delay between execution and availability cannot be measured from this endpoint, so the "known at the close of minute t" assumption is optimistic for a live trader.
- Only 90 of 342 sessions were paged (time budget); the 90 are a seeded random sample stratified by nothing other than chance ([samples.json](/home/user/georgeredo/research/flow_predictors/samples.json)).

## Key question 4 — Per-strike ask-side premium bursts (40-session sample): underlying and own-contract forward returns vs a random baseline

### Takeaway
Bursts (ask-side premium ≥ 5× or 10× the trailing 20-minute median at a strike within 1 % of spot) are followed by underlying moves of −0.9 to +0.1 bp in the burst direction (hit rate 49-50 %), no different from matched random minutes; the burst contract's own 15/30-minute return is ≈ 0 before costs and −6 to −8 % after the 1 %/2 % half-spread and $0.70/side fees, versus −4 to −6 % for random ATM entries. The endpoint only returns the day's top-8 strikes by a full-day filter, which both limits coverage and selects on outcome.

### Cited Findings
- Endpoint behaviour: `stock/{t}/flow-per-strike-intraday` has parameters `date` and `filter` ∈ {NetPremium (default), Volume, Trades}, documented as "Retrieve the strikes with the highest filter parameter"; it returns exactly 8 strikes per ticker-day, one row per minute per strike with per-minute (not cumulative) call/put premium and volume split by ask/bid side, aggregated across all expiries — [UW OpenAPI spec](https://api.unusualwhales.com/api/openapi) and [bursts_coverage.csv](/home/user/georgeredo/research/flow_predictors/bursts_coverage.csv). With the default filter only 1.3 (SPY) / 1.6 (QQQ) / 0.95 (IWM) of the 8 strikes lie within 1 % of midday spot on average; with `filter=Volume` 7.8 / 7.3 / 4.5 do.
- Burst definition ([analyze_bursts.py](/home/user/georgeredo/research/flow_predictors/analyze_bursts.py)): x(m) = call (or put) premium_ask_side in minute m at a strike; burst if x ≥ k·max(median(x[m-20..m-1]), floor) and x ≥ min_abs, floor $2,000 (SPY/QQQ) / $1,000 (IWM), min_abs $20,000 / $10,000, k ∈ {5, 10}; |strike/spot − 1| ≤ 1 % (main) or 2 %; 15-minute cooldown per strike-side; calls → long, puts → short. Baseline: the same number of random minutes per ticker-day, random side, ATM 0DTE contract.
- Counts over 40 sessions × 3 tickers ([bursts_events.csv](/home/user/georgeredo/research/flow_predictors/bursts_events.csv)): default filter, k = 5, 1 % band: 3,123 bursts (QQQ 1,277, SPY 982, IWM 864); k = 10: 1,488; Volume filter, k = 5: 14,065; k = 10: 6,202. 2,238 option contract-days were fetched; 100 % of burst contracts had 0DTE bars.
- Underlying forward return in the burst direction, bp, mean [day-block bootstrap CI] ([bursts_summary.csv](/home/user/georgeredo/research/flow_predictors/bursts_summary.csv)):
  - Default filter k = 5 (n = 3,123): h15 −0.27 [−0.69, 0.16]; h30 −0.34 [−0.79, 0.14]; h60 −0.03 [−0.92, 0.93]; 30-minute hit rate 49.3 %. Baseline (n = 3,123): +0.10 / −0.02 / +0.18, hit 50.2 %.
  - Default filter k = 10 (n = 1,488): −0.39 / −0.86 [−1.79, −0.02] / −1.05 [−2.44, 0.24]; hit 48.7 % (the only CI excluding zero is against the burst direction).
  - Volume filter k = 5 (n = 14,065): +0.07 / +0.07 / −0.34 [−0.74, 0.04]; hit 49.6 %. Baseline: −0.02 / +0.18 / +0.26. k = 10 (n = 6,202): +0.06 / −0.02 / −0.72 [−1.51, −0.03].
  - 2 % band results are within ±0.3 bp of the 1 % band results.
- Burst contract's own return from the next bar's VWAP (0DTE contract at the burst strike/side), raw and net of costs:
  - Default k = 5: 15-min raw −0.33 %, net −6.85 % [−8.96, −4.49], win rate 34.9 %; 30-min raw −0.45 %, net −6.97 % [−9.90, −3.44]. Baseline: raw +0.47 % / −0.74 %, net −4.18 % / −5.37 %, win 40.1 % / 37.3 %.
  - Default k = 10: net −7.41 % / −7.98 %. Volume k = 5: raw +0.43 % / +0.32 %, net −5.96 % / −6.07 %, win 34.6 % / 34.7 %; baseline net −5.04 % / −5.38 %. Volume k = 10: raw +0.87 % / +1.73 %, net −6.45 % / −5.61 %.
- Multiple-testing table: the four burst contract-net cells are the only cells in [mt_summary.csv](/home/user/georgeredo/research/flow_predictors/mt_summary.csv) that pass Bonferroni/BH, and they are significantly negative (p ≤ 3e-5).

### Inferences
- The cost of the round trip (≈ 6-7 % of a $1-2 premium at the 1 % half-spread + fees used here, more than the 3.4 % nominal hurdle because burst-minute premiums are small) dwarfs any raw drift, and the raw drift itself is zero within ±1 %.
- Because the endpoint picks strikes on full-day totals, a live trader cannot even reproduce this strike set in real time; the test is generous to the feature, which makes the null more convincing.

### Gaps
- All-expiry aggregation means some bursts were in non-0DTE contracts; the 0DTE contract was used as the tradable proxy throughout.
- A burst definition conditioned on the bid-side (closing) flow or on open-interest change was not tested.

## Key question 5 — The most promising feature as an ATM 0DTE trading rule with the `trail` engine

### Takeaway
SPY F1 (nominally the best unconditional cell) traded every 5 minutes as top/bottom-quintile call/put buys (638 trades) returns −0.40 % per trade before costs and −2.38 % [−3.66, −1.07] after the spread model with the trail engine; random entries matched per day return −0.28 % / −2.26 % [−3.67, −0.97]; a 30-minute hold gives −0.65 % / −2.62 % [−6.40, +1.25] vs −0.31 % / −2.29 % for random.

### Cited Findings
- Rule ([trade_rule.py](/home/user/georgeredo/research/flow_predictors/trade_rule.py)): every 5 minutes 09:45-15:00, F1 ≥ 80th percentile of the trailing-20-session F1 distribution → buy the ATM 0DTE call; ≤ 20th percentile → buy the ATM put; entry at the VWAP of the first option bar after the signal minute; `trail` engine with stop −25 % (breakeven lock after +6 %, 35 % give-back trail after +15 %, 30-minute time stop if flat/losing, 15:55 close); `costs.settle` 'mid' and 'spread' (1 % half-spread per side + $0.70 fees per side); max 2 trades/day, 30-minute cooldown. 638 signals (340 puts, 298 calls); baseline 574 random minutes/sides matched per day.
- Results ([trade_rule_SPY_F1_summary.csv](/home/user/georgeredo/research/flow_predictors/trade_rule_SPY_F1_summary.csv)): rule trail mid −0.40 % [−1.71, 0.92] (win 35.9 %, mean +$0.31/contract); trail spread −2.38 % [−3.66, −1.07] (mean −$4.12); hold30 mid −0.65 % [−4.51, 3.29] (win 43.6 %); hold30 spread −2.62 % [−6.40, 1.25]. Calls alone (trail, spread) −1.73 % [−3.54, 0.18]; puts alone −2.95 % [−4.79, −1.16]. Baseline: trail mid −0.28 % [−1.73, 1.03], trail spread −2.26 % [−3.67, −0.97], hold30 mid −0.31 % [−4.48, 3.94], hold30 spread −2.29 % [−6.37, 1.88].
- Exit-reason mix for the trail engine on 1-minute 0DTE bars: BREAKEVEN 37.8 %, TRAIL 35.9 %, STOP 26.0 %, TIME_STOP 0.3 %; median hold 3 minutes (75th percentile 5-6 minutes) for both rule and baseline — [trade_rule_SPY_F1.csv](/home/user/georgeredo/research/flow_predictors/trade_rule_SPY_F1.csv). Median entry premium $1.39 (rule) and $1.04 (baseline); cost drag (mid minus spread) 1.97 % per trade.

### Inferences
- The rule's expectancy is statistically and economically indistinguishable from random entries; the cost model alone explains the −2 % per trade.
- The trail engine exits most 0DTE trades within 3 minutes because a 6 % move of a ~$1.4 option is $0.08, routinely crossed inside one 1-minute bar; any feature with a 30-minute horizon is therefore better judged by the hold-30 variant, which is also null.

### Gaps
- Only SPY/F1 was run as a rule; given that no other cell is stronger, QQQ/IWM variants were not run.
- Thresholds use trailing-20-session quantiles; an alternative (e.g. z-scores within the day) was not tested.

## Overall verdict and multiple-testing note

### Takeaway
No feature is distinguishable from zero after correction and none clears the cost hurdle; the results are consistent with the flow and dark-pool feeds describing the recent move rather than the next one.

### Cited Findings
- Across the 62 main cells in [mt_summary.csv](/home/user/georgeredo/research/flow_predictors/mt_summary.csv): 58 predictive cells have minimum p = 0.051 (SPY dark-pool buy share vs 60-minute, negative sign) and zero with p < 0.05; Bonferroni threshold 0.00081, BH q = 0.05: zero survivors among predictive cells; the 4 survivors are the burst contracts' negative net returns. Quintile-spread p-values: 2 nominal (SPY F2 h15 0.60 bp, p = 0.042; IWM F2u h60 2.11 bp, p = 0.039), zero after Bonferroni or BH.
- Per-feature verdicts (pooled IC range across tickers/horizons; best Q5−Q1 spread; vs hurdle 0.15-0.39 bp shares / ≈ 1.2 bp ATM 0DTE):
  - F1 signed net premium: IC −0.011..+0.020; best spread 1.23 bp (SPY h60, CI includes 0); one-sided expectation ≈ 0.5 bp → below the option hurdle, not significant. **No edge.**
  - F2 signed ask-bid volume share: IC −0.010..+0.013; best spread 0.79 bp. **No edge.**
  - F2u unsigned aggressor share: IC −0.011..+0.019; best spread 2.11 bp (IWM h60, nominal only). **No edge after correction.**
  - F3 net-delta change: IC −0.009..+0.015; best spread 0.92 bp. **No edge.**
  - Market tide level / 30-minute change (tradable): IC −0.002..+0.020; spreads ≤ 0.92 bp. **No edge; contemporaneous only.**
  - Dark-pool buy share D1 / net notional D2: IC −0.065..+0.037, contrarian sign where largest; spreads −4.8..+3.9 bp with CIs spanning zero. **No edge.**
  - Per-strike bursts: directional drift −0.9..+0.1 bp; contract net −6..−8 % vs baseline −4..−6 %. **Negative after costs.**
  - SPY F1 rule on ATM 0DTE (trail): −2.4 % per trade after costs vs −2.3 % random. **No edge.**

### Inferences
- Any live strategy built on these UW aggregates would need to find its edge somewhere other than the sign of the last 15-30 minutes of premium, volume-side, delta, tide or dark-pool prints, because those quantities are ≥ 0.5 rank-correlated with the move that has already happened and ≤ 0.02 rank-correlated with the move that follows.

### Gaps
- Not tested here: flow conditioned on strike distance/expiry from the `flow-alerts` or `option-trades` feeds, open-interest changes, or interaction of flow with distance to call/put walls; only the prior session's gamma_flip was used for regime.
- Reproduction: `export BT_CACHE=…; export UW_API_TOKEN=…` (from the env file, never printed); then in `research/flow_predictors/`: `python3 -s prefetch_cheap.py 5; python3 -s prefetch_dp_fps.py; python3 -s prefetch_fps_volume.py; python3 -s refetch_dp_gaps.py 5; python3 -s build_panel.py; python3 -s analyze_flow.py; python3 -s analyze_tide.py; python3 -s analyze_dp.py; python3 -s analyze_bursts.py; python3 -s trade_rule.py SPY F1; python3 -s mt_summary.py; python3 -s placebo_daily_ic.py` (do not use `python3 -I`, which cannot import `common.py`).
