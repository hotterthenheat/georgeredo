# Compass modules 2 and 9: the sweep trigger, the exclusions, the score and the FVG / order-block / OTE geometry

Scope: the order trigger (liquidity sweep + order block), the setup taxonomy and its exclusions, the grade/score engine,
and module 9's geometry, audited on the owner's data under the five guardrails. Every number below was computed by a
script in `sweep_trigger/` (the logs in `sweep_trigger/logs/`, the tables in `sweep_trigger/out/*.csv`); nothing was
tuned after the out-of-sample read. The literature pass is short (section 0) because the deliverable is the computed
tests; the published evidence, where it exists, points the same way as the tests.

**Headline.** The liquidity sweep carries no directional information on these four products at these horizons (the
underlying's 30-minute return in the fade direction is between +0.1 and −1.8 bps, 45–50% positive, in both periods), and every
long-premium fade of it loses after fees with every exit tried (SPY −6%/−8% of premium a trade with the trailing stop
on 2022–24 / 2025–26; QQQ −13%/−12%; IWM −19%/−14%; SPXW −4%/−5%). The definition that looked best on 2022–24
(+$27 a contract) read −$56 on 2025–26. The score (logistic or boosted) does not rank the trade's outcome out of
sample (AUC 0.53 / 0.51 against 0.5). The geometry entries (OTE, order block) fill 31–68% of the time and do not beat
the sweep bar's close. The exclusions the spec calls "proven negative EV" are true but not discriminating: the things
they keep are as negative as the things they exclude. The only rules that survive are the quote hygiene, the
spread/mid ≤ 5% picker rule (which does bind, badly on IWM and in the last hour everywhere) and "block if the score is
missing" — and those are frictions, not edges. Nothing in modules 2 and 9 should be given a weight; nothing in them
should be traded long premium on 0DTE as specified.

## Data, conventions and what was built

- Data (on disk, no vendor calls): ThetaData 1-minute NBBO of every same-day contract, SPY and QQQ 2022-11-11 → 2026-10-09
  (980 sessions), SPXW 2022-05-13 → (1,106), IWM 2024-04-19 → (621); 1-minute underlying bars; SPX and VIX prints. Half
  days (20) are dropped. Train = sessions before 2025-01-01, test = 2025-01-01 → 2026-10-09; nothing in the test period
  was read while a definition, feature set or threshold was chosen. Fees $0.65 a contract each way, none when a contract
  expires worthless. Entries 09:35–15:57, the sale at 15:58 at the latest ("hold"), settle = intrinsic at the closing
  spot if the 15:58 bid is zero.
- SPXW's sweeps and levels are detected on SPY's 1-minute bars (SPX has one print a minute, no bar high/low); its spot,
  strikes and deltas are SPX's own prints. This is a stated proxy (sweeplib `BAR_SOURCE`).
- Scripts: `sweeplib.py` (definitions, picks, exits, stress test), `daytable.py` (prior-day / prior-week levels, ATR14,
  volume norms from the 2012→ bars), `build_events.py` (every event of the grid with its features and trades, session by
  session, two workers, ~4 minutes a product), `fix_fwd.py` (forward returns re-measured from the entry minute),
  `verify.py` (240 random events re-derived from the raw files with separate plain-loop code: the sweep conditions, the
  entry quote, the trailing-stop exit, the net dollars, the forward return — 1 difference of 240, an entry at 15:58 with
  no minute left to sell in, now excluded from every analysis), `grid.py` (Q1), `exclusions.py` (Q2), `geometry.py` and
  `ote_variant.py` (Q3), `score.py` (Q4), `spread.py` (Q5), `windows_stress.py` and `extra_stress.py` (every cell that
  read positive anywhere, stress-tested).
- Stress test (`sweeplib.stress`): the mean per contract, its 95% range from 1,000 resamples of sessions, the mean
  without the best 5 sessions, sessions up. Dollar means pool SPXW (10× the ETFs' notional) with the ETFs, so the
  percentage of premium a trade is quoted beside every dollar figure and is the cross-product yardstick.

## 0. Literature pass: published evidence on sweep reversals, opening-range breakouts and ICT concepts

### Takeaway
There is no peer-reviewed evidence that a liquidity sweep predicts a reversal; the one academic root (Osler's
stop-loss clustering) is about price *acceleration* through levels, i.e. continuation, not fade. The published
opening-range-breakout result does not survive costs in an independent replication, and the one controlled test of
fair-value gaps found no edge over placebo zones.

### Cited Findings
- Osler (NY Fed Staff Report 150): stop-loss orders cluster just beyond round numbers and exchange-rate trends are
  "unusually rapid" when rates reach those levels — price cascades, i.e. continuation through the level, on
  minute-by-minute dollar-mark, dollar-yen and dollar-pound 1996–1998 — [Osler, Stop-loss orders and price cascades](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf); the clustering evidence itself is [NY Fed SR 125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf).
- A web search for empirical stop-hunt / liquidity-sweep reversal studies returned only indicator pages and glossaries; one concept page notes that many runs through a high or low keep going — [LuxAlgo, Liquidity sweep](https://www.luxalgo.com/library/concept/liquidity-sweep.md). No backtest with a sample size or out-of-sample statistic was found.
- Opening-range breakout (Zarattini & Aziz, SSRN 4416622) replicated unchanged on NQ, SPX, Dow, DAX, FTSE 2015–2026 by an independent blog: gross +0.13 R on NQ matches the paper, but net of spread and slippage no market is distinguishable from zero and four of five are negative (SPX −0.081 R, t = −1.6); 2021–2026 out of sample at most +0.06 R; the paper itself has no out-of-sample period — [MQL5 replication](https://www.mql5.com/en/blogs/post/776235).
- A fair-value-gap test with matched placebo zones (same height, direction and distance, anchored where no gap formed) across three asset classes, three timeframes and two periods found the real-minus-placebo hit-rate difference under one percentage point and no measurement significant; the author also notes order blocks are usually drawn with look-ahead (the block is only identifiable after the later structure break) — [TradingView, FVG Statistics with Placebo Control](https://fr.tradingview.com/scripts/backtest/).
- Retail 0DTE buyers on S&P 500 options lost about $358,000 a day after daily expirations began in May 2022, more than 60% of it transaction costs (University of Münster study reported by Bloomberg) — [Bloomberg, 2023-04-21](https://www.bloomberg.com/news/articles/2023-04-21/day-traders-lose-358-000-per-day-gambling-on-zero-day-options); 0DTEs were nearly 60% of S&P 500 index option volume in 2025 — [HKUST, Are 0DTE options mispriced](https://bm.hkust.edu.hk/bizinsight/2026/04/are-0dte-options-mispriced).

### Inferences
- The spec's entry model inverts the one documented mechanism: stop clusters beyond levels produce cascades through
  them, which is why the fade's forward return in the tests below is slightly negative rather than positive.
- The ORB literature's pattern — gross signal, net zero after costs, no out-of-sample period — is the pattern the ledger
  the spec was reverse-engineered from would show if it were audited the same way.

### Gaps
- No peer-reviewed study of ICT order blocks or OTE retracements was found; the only controlled test is a practitioner's.

## 1. The sweep definition grid (events a session, the fade's EV, the underlying's own forward return)

### Takeaway
Across 4 levels × 5 excursions × 4 return windows × 2 confirmations (160 definitions, 225,390 event rows), no
definition gives the fade a positive, stable expectation. The underlying does not reverse after a sweep, so the
option's result is the option's cost. The definition chosen on 2022–24 lost on 2025–26.

### Cited Findings
- Events a session for the merged trigger (any level, X = 0 bps, the sweep bar itself closes back inside, no
  confirmation; one entry a minute and side): SPY 4.6 / 4.3 a session (2022–24 / 2025–26), QQQ 4.0 / 3.9, IWM 3.6 / 3.8,
  SPXW 4.5 / 4.3 — [extra_stress.py](sweep_trigger/extra_stress.py), `logs/extra_stress.log`. Per definition the counts run from
  0.4 a session (prior-week levels at X = 0) to 10 (session high/low, k = 3); X = 10 bps leaves 123 / 197 events in
  all and X = 20 bps 20 / 43 — [grid.py](sweep_trigger/grid.py), `out/grid_full.csv`.
- The underlying's forward return in the fade direction after a sweep (X = 0, k = 1, bps, mean; share positive at 30 min):
  OR 2022–24 −0.6 bps at 30 min (SE 0.4), 48.9% positive, −4.1 to the close; 2025–26 −0.2, 49.1%, −0.9. PD −0.4 / −1.4
  at 30 min, −1.4 / −0.5 to the close. PW +0.1 / −1.8; −0.8 / −2.8. SH −0.3 / −0.4; −0.8 / +1.0. The share moving ≥ 10 bps
  in the fade direction within 30 minutes is 24–28% at every level in both periods — `out/underlying_fwd.csv`.
- The merged trigger's fade, nearest OTM strike, 50% trailing stop, % of premium a trade (and $ a contract), with the
  95% day-bootstrap range: SPY −6.1% [−11.4, 0.0] on 2022–24 and −8.0% [−13.2, −2.5] on 2025–26 (−$2.2 / −$3.1); QQQ
  −12.6% [−17.5, −6.7] / −11.5% [−16.0, −6.7] (−$7.2 / −$14.1); IWM −18.6% [−26, −11.6] / −13.7% [−19.5, −7.4] (−$3.1 /
  −$2.4); SPXW −4.5% [−9.1, 0.0] / −5.1% [−10.6, 0.4] (−$25.7 / −$16.4). Win rates 0.18–0.20 — `logs/windows_stress.log`,
  `logs/grid.log`.
- The other exits are worse: +25% target / −32% stop: SPY −7.0% / −6.9%, QQQ −8.5% / −5.6%, IWM −14.6% / −11.9%, SPXW
  −4.2% / −4.8%; hold to 15:58: SPY −12.5% / −13.9%, QQQ −21.2% / −17.7%, IWM −29.5% / −25.2%, SPXW −11.8% / −11.0% —
  `logs/grid.log` (merged trigger table).
- Pooled dollars, merged trigger: trailing stop −$12.1 [−28.7, 6.2] (without the best 5 days −$24.5) on 2022–24;
  −$9.1 [−34, 21] (−$30.4; 119 of 440 sessions up) on 2025–26. By year: 2022 −$30.6, 2023 −$15.8, 2024 −$4.8, 2025
  +$4.6, 2026 −$27.6 — `logs/grid.log`.
- The 0.30–0.45 |delta| pick (Black-Scholes on the mid's implied vol, r = 0) is available at the sweep minute 96–100% of
  the time before 13:45 on SPY/QQQ/SPXW but 45% of the time on SPY after 15:30, 41% on IWM 13:45–15:30 and 22% on IWM
  after 15:30. Its fade: SPY −2.3% / −6.4%, QQQ −10.1% / −10.8%, IWM −2.3% / −8.5%, SPXW −5.2% / −4.8%; pooled % −5.5%
  [−10.1, −0.9] / −7.4% [−11.9, −2.4] — `logs/spread.log`, `logs/extra_stress.log`.
- Excursion X and confirmation, k = 1, levels pooled (trailing stop, % of premium, 2022–24 / 2025–26): X = 0 −7.9% /
  −9.4%; X = 2 −10.3% / −5.0%; X = 5 −6.6% / −2.9% (623 / 670 events); X = 10 −19.7% / −23.2%; X = 20 −20.1% / −7.9%.
  With the next bar's confirmation: X = 0 −8.1% / −7.2%; X = 2 −12.2% / +0.6%; X = 5 −15.2% / +2.9% (321 / 344 events) —
  `out/grid_by_x_confirm.csv`.
- 5-minute bars (X = 0, no confirmation, trailing stop, %): OR −9.8% / −7.2%, PD −10.2% / −10.8%, PW −5.6% / −6.8%, SH
  −12.4% / −8.8% — `out/grid_by_level.csv`.
- The choice on 2022–24 (largest trailing-stop $ a contract with ≥ 500 events): PD, X = 2, k = 3, confirmed —
  +$27.2 on 621 events, whose own stress test already failed (95% [−38, 106], −$44 without the best 5 days, 65 of 287
  sessions up; −3.8% of premium). Read on 2025–26: −$56.4 on 565 events, win 0.19 → 0.15, −19.7% of premium; by product
  SPY −22.5%, QQQ −19.3%, IWM −15.4%, SPXW −22.8% — `logs/grid.log`.
- Of the ten best definitions on 2022–24, five flipped sign on 2025–26; the four that stayed positive in dollars
  (OR X=2 k=5 confirmed; OR X=5 k=5 confirmed and unconfirmed; PD X=5 k=5) are −1.9% → +0.6%, −1.7% → +1.8%, −1.2% →
  −2.3% and −3.8% → −6.9% of premium, every 95% range straddles zero in both periods, and every one is negative without
  its best 5 days (e.g. OR X=2 k=5 confirmed on 2025–26: +0.6% [−8.0, 9.7], −6.3% without the best 5 days, 94 of 354
  sessions up) — `logs/extra_stress.log`.
- Step 4 of this repository found the same for SPY near-the-money contracts bought at fixed times: −8.7% a trade with a
  20% trailing stop, −19.7% held — [step4/README.md](../../step4/README.md).

### Inferences
- A sweep fade on SPY (−6% to −8%) is indistinguishable from buying a near-the-money 0DTE at a random time (−9% with a
  trailing stop in step 4): the trigger adds no information and the result is the premium's decay plus the spread.
- Wider excursions (X ≥ 10 bps) select real breakouts and lose more; narrow ones select noise around the level. Neither
  side of the grid holds a positive region that survives a day-bootstrap.
- The confirmation bar does not help: it costs one bar of the move (when there is one) and halves the event count.

### Gaps
- Sweeps on SPXW are SPY-bar sweeps: an SPX-only wick that SPY did not print is not an event here. SPX bar high/low data
  would be needed to test SPXW on its own prints.

## 2. The exclusions as causal claims (displacement-only, ORH-only, QQQ, direction windows, gamma sign)

### Takeaway
Every exclusion in the spec excludes something that loses — but what it keeps loses as much. The "proven negative EV"
claims are artifacts of a ledger in which everything long premium is negative; none of them separates a positive
subset from a negative one, in either period.

### Cited Findings
- Displacement-only bars (range ≥ 2× the trailing 14-bar mean range, closing in its direction, no sweep within 3 bars;
  9,023 / 8,146 bars): continuation, nearest OTM, trailing stop −10.2% / −10.8% of premium (−$18.0 [−29.5, −6.6] /
  −$11.6 [−25.1, 2.6]); faded instead −1.7% / −12.0%; the sweep entries beside them −8.1% / −9.4%. By product the
  continuation is SPY −10.7% / −7.5%, QQQ −9.5% / −8.1%, IWM −23.9% / −23.9%, SPXW −6.8% / −4.0% — [exclusions.py](sweep_trigger/exclusions.py), `out/disp_co.csv`, `out/disp_fo.csv`.
- ORH/ORL sweeps (X = 0, k = 1) whose level lies within 0.2% of the prior day's high or low (pd_near = 1) against the
  rest: −4.6% / −4.6% of premium against −7.5% / −10.3%; in dollars −$4.7 / +$70.3 against −$17.1 / −$24.3, the +$70.3 on
  2025–26 with a 95% range of [−27, 225], −$32.8 without its best 5 days, 61 of 245 sessions up; by product on 2025–26
  SPY +0.4%, SPXW +3.0%, QQQ −12.9%, IWM −20.2% — `out/or_pdnear.csv`, `logs/exclusions.log`.
- QQQ against the rest (merged trigger, fade, trailing stop): QQQ's loss is larger than SPY's and SPXW's in both periods
  (−12.6% / −11.5% against SPY −6.1% / −8.0%, SPXW −4.5% / −5.1%) and its 95% range excludes zero in both periods, but
  IWM, which the spec approves, is the worst product (−18.6% / −13.7%) — `logs/windows_stress.log`.
- Direction by the spec's windows (merged sweeps; fade against continuation; trailing stop; $ a contract and % of
  premium; 2022–24 / 2025–26; underlying's 30-minute return in the fade direction):
  09:35–09:55 (chase): fade −$13 (−6.7%) / +$5 (+3.1%), continuation −$49 (−5.1%) / +$7 (−3.2%); +0.8 / −3.4 bps.
  09:55–10:35 (fade): fade +$6 (−0.9%) / +$38 (−5.0%), continuation −$13 (+0.3%) / −$12 (−1.4%); −0.6 / −1.2 bps.
  10:35–12:00 (fade): fade −$24 (−6.6%) / −$27 (−10.9%), continuation +$10 (+1.4%) / +$11 (−0.9%); +0.1 / −1.0 bps.
  12:00–13:45 (unassigned): fade −$14 (−7.7%) / −$7 (−4.7%), continuation +$4 (−1.4%) / −$26 (−7.7%).
  13:45–15:30 (chase): fade −$11 (−10.1%) / −$35 (−17.0%), continuation −$21 (−8.9%) / −$5 (−12.0%).
  15:30–15:57 (fade): fade −$12 (−28.5%) / −$6 (−24.3%), continuation −$10 (−19.8%) / −$15 (−16.2%) — `out/direction_by_window.csv`.
- The one window that reads positive in dollars (09:55–10:35 fade): +$6.0 [−42, 56] (−$37.9 without the best 5 days) on
  2022–24 and +$37.5 [−68, 220] (−$69.6) on 2025–26; −0.9% / −5.0% of premium; by year −12.3%, +5.9%, −4.0%, −2.0%,
  −9.2%. Its high side on 2025–26, +$123, is +1.0% [−16.2, 22.3] of premium, −$86 without the best 5 days, 53 of 246
  sessions up, and +$7.3 [−20, 48] without SPXW — [windows_stress.py](sweep_trigger/windows_stress.py), `logs/windows_stress.log`.
- Gamma sign (Unusual Whales daily net dealer gamma, call_gamma + put_gamma, the row dated the session; coverage
  2025-10-15 → 2026-10-09 only, 245 sessions, 3,774 events — SPY 80 positive / 170 negative sessions, QQQ 90 / 160, IWM
  17 / 233, SPX 185 / 65): fade on positive-gamma days −9.6% of premium (−$2.8 [−44, 47], −$44 without the best 5 days)
  against −9.3% (−$16.0 [−38, 12]) on negative; continuation −0.7% against −10.1%; underlying +0.3 against −0.6 bps at
  30 minutes. The one positive cell, positive gamma in 09:55–10:35 (251 events): +7.4% [−15.5, 37.9] of premium, −16.9%
  without its best 5 days, 27 of 115 sessions up — `out/gamma_split.csv`, `logs/extra_stress.log`.

### Inferences
- "Displacement-only is negative EV" is true (−10%) and so is "sweep is negative EV" (−8% to −9%): the exclusion does
  not move the engine from a losing trigger to a winning one.
- "ORH-only is worse than ORH at PDH/PDL" ranks correctly in both periods (−7.5% → −4.6%; −10.3% → −4.6%) — the only
  exclusion with a stable ordering — but the kept set is still negative and its dollar reading rests on five SPXW days.
- "Block QQQ" ranks correctly but is incomplete: by the same yardstick IWM should be blocked first and SPXW/SPY are
  only less negative. NDX is untestable here (no NDX data).
- The direction rule is not supported: fades lose in the fade windows (10:35–12:00 −6.6% / −10.9%) and continuations
  lose in the chase windows; the underlying's 30-minute return after a sweep is within ±3.4 bps of zero in every window
  and period, with no sign pattern that follows the windows.
- The gamma split cannot be tested as specified ("positive gamma between walls" needs strike-level walls, which the UW
  table on disk does not carry — its levels file is empty), and the net-sign version covers one year, out of sample only,
  and shows no difference in the fade's percentage result.

### Gaps
- NDX: no data. "Major gamma wall within 0.2% of spot": no strike-level dealer book for any date in the test window
  (`RAW/uw_gex_levels_daily.csv` has 1,521 rows and every wall column empty) — untestable, a blocker.
- The gamma sign is one year and one regime (2025-10 → 2026-10); the split is reported, not relied on.

## 3. Module 9's geometry: OTE retracement, order block, FVG (triple confirmation)

### Takeaway
On the same episodes, an order-block or OTE entry fills 31–68% of the time, waits 1–7 minutes, and ends no better than
the sweep bar's close; an FVG is present on 4.5% of sweeps and marks events whose underlying continues *against* the
fade more, not less. The confirmation bar's apparent edge is a selection effect.

### Cited Findings
- Definitions in code ([sweeplib.py](sweep_trigger/sweeplib.py)): `fvg_present` — a three-candle gap in the fade direction
  with its window ending at r−1 or r (bearish: low[t−2] > high[t]; bullish: high[t−2] < low[t]); `order_block` — the
  last opposite-colour candle in [r−5, r−1] before the return bar r, zone = its body, a doji (body under one tick) takes
  its full range, a zero range is no block; `ote_fill` — after r the impulse runs from the sweep extreme H to the running
  extreme of the displacement, the fill is the first bar whose range reaches the 0.62–0.705 zone of that leg measured
  back toward H, the leg must be ≥ 1 bp of price (the doji / zero-division guard), a bar through H voids the setup, 30
  bars allowed; `ob_fill` — the first bar after r whose range returns into the block, voided through H, 30 bars.
- k = 1 (16,980 episodes, 1,094 sessions; nearest OTM fade, trailing stop; 2022–24 / 2025–26): fill rate — close entry
  1.00, confirmation 0.49 / 0.48, OTE 0.58 / 0.55, order block 0.62 / 0.59; wait after r — OTE 2.7 min, OB 1.2 min;
  % of premium — close −7.9% / −9.4%, confirmation −8.1% / −7.2%, OTE −8.9% / −10.4%, OB −8.1% / −10.1%; time in trade
  65–72 minutes for all four; win rates 0.19–0.20 — [geometry.py](sweep_trigger/geometry.py), `out/geometry_entries.csv`.
- On the episodes where the OTE filled, the close entry on those same episodes was −$15.4 against the OTE's −$22.2
  (2022–24) and −$3.1 against −$10.9 (2025–26); where the order block filled, +$0.6 against −$14.4 and +$13.8 against
  −$1.6 — `logs/geometry.log`.
- k = 3 (25,028 episodes): OTE fill 0.63 / 0.60, −11.5% / −10.2% against the close's −8.4% / −9.4%; OB fill 0.68 / 0.66,
  −8.8% / −10.6% — `logs/geometry.log`.
- A stricter OTE on SPY (the leg ≥ 5 bps of price, the fill sought from the third bar after r, so the impulse is a
  displacement and not the sweep bar's own range): fills 35% / 31%, waits 6.7 / 7.1 minutes, −11.0% / −3.1% of premium
  (−$3.5 [−9.5, 3.2] / −$1.5 [−9.8, 8.0]) against the close entry's −10.8% / −2.4% on the same episodes — [ote_variant.py](sweep_trigger/ote_variant.py), `logs/ote_variant.log`.
- FVG present on 412 of 9,147 (4.5%) and 367 of 7,833 (4.7%) k = 1 sweeps: trailing-stop −1.0% / −11.9% of premium
  against −8.3% / −9.2% without it; win 0.199 / 0.185 against 0.193 / 0.193; dollars −$19.8 [−73, 41] / −$7.3 [−138,
  196]; the underlying's 30-minute return in the fade direction −1.0 / −5.7 bps with an FVG against −0.4 / −0.4 without
  — `out/fvg_split_k1.csv`.
- An order block is present (an opposite-colour candle in the five bars before r) on 99.7% of sweeps, so "OB present" is
  not a condition.
- The confirmation entry's apparent lift on 2025–26 (+$6.1 [−33.5, 58], −$31 without the best 5 days) is a selection
  effect: on the episodes where the confirming bar formed, the close entry one bar earlier made +$16.1 / +$35.5 because
  it owns the confirming bar's move; the confirmed entry itself made −$15.4 / +$6.1 — `logs/geometry.log`.

### Inferences
- Module 9 as specified (OTE 0.62–0.705, OB = last opposite candle, FVG three-candle gap, the doji guard) is
  implementable and was implemented; it does not improve fill quality or expectation over the plain sweep close, and
  the FVG, if anything, flags momentum against the fade (consistent with Osler's cascades).
- "Triple confirmation upgrades an A setup" is not supported: the triple-confirmed subset has the same win rate and a
  worse underlying path.

### Gaps
- The ICT definitions have many variants (full-range vs body order blocks, gaps that must be "unmitigated", swing-based
  impulses); one variant each was tested, plus one stricter OTE. None of the published sources gives a canonical
  tick-level definition to test against.

## 4. The score: can a fitted model rank sweep fades out of sample?

### Takeaway
A logistic regression on 2022–24 with the spec's features ranks the fade trade's out-of-sample outcome at AUC 0.53
(a boosted model 0.51 after 0.77 in sample); the top decile's EV rests on five SPXW days and is negative without them.
The score should not exist as a weight; the boolean gate is as good — and both are negative.

### Cited Findings
- Sample: the merged trigger (X = 0, k = 1, no confirmation), 7,989 train / 6,928 test events; outcome A = fade trade net
  > 0 (nearest OTM, trailing stop, fees in), base rate 0.195 / 0.192; outcome B = underlying moves ≥ 10 bps in the fade
  direction within 30 minutes, base rate 0.539 / 0.531. Features: sweep depth (bps), bars outside, level type, minute of
  day and the spec's window, position in the opening range, relative volume (last 5 bars against the 20-session median
  of the same minutes), VIX, the strike's distance in ATM-straddle units, straddle/spot, the return bar's range, FVG,
  OB, the day's move in ATR14 units, the pick's spread and ask, product, side; NaN filled with the train median —
  [score.py](sweep_trigger/score.py), `out/score_summary.csv`.
- Outcome A, logistic: AUC 0.563 train, 0.528 test. Out-of-sample deciles run from a 0.143 win rate (decile 1) to
  0.214 (decile 10); dollars by decile are unordered (decile 6 −$55, decile 9 +$15, decile 10 +$40). Top 10% by the
  train threshold: 465 test trades, +$64, win 0.222, 95% [−44, 217], −$39 without the best 5 days, 38 of 164 sessions up,
  2025 +$107 / 2026 −$32, SPXW +$718 on 44 trades, QQQ −$83, SPY +$15, IWM +$5. Top 20%: +$22 [−42, 101], −$37 without
  the best 5 days — `out/score_deciles_yA_logistic.csv`, `logs/score.log`.
- Outcome A, gradient boosting (depth 3, 300 rounds, leaf ≥ 200): AUC 0.773 train → 0.513 test; top 10% −$36 [−125,
  67] — `out/score_deciles_yA_gbm.csv`.
- Outcome B (the underlying moves ≥ 10 bps): logistic AUC 0.677 / 0.710, well calibrated (decile 10 predicted 0.87,
  realised 0.79), driven by straddle/spot (+0.28), VIX (+0.17), relative volume (+0.16), depth (+0.13) and the
  windows — a volatility forecast, not a direction forecast; the trade's dollars by decile are unordered (decile 10
  +$14 with win 0.19) and its top 10% is +$5 [−110, 171], −$91 without the best 5 days — `out/score_deciles_yB_logistic.csv`.
- The plain gate (every merged sweep): −$12.1 train, −$9.1 test [−35, 19] — `logs/score.log`.
- Single features by quintile (outcome A rate, train / test): the strike's distance in straddle units is the only
  monotone one — 0.239 / 0.211 in the nearest quintile falling to 0.147 / 0.144 in the farthest — and its nearest
  quintile makes +$1.3 / +$12.0, i.e. nothing after the spread; depth's best quintile moves (4th on train, 5th on test);
  relative volume, VIX and the day's move in ATR show no stable order — `logs/score.log`.

### Inferences
- There is no empirical win-probability for the score to "reflect": the fade's 20% win rate is flat across every
  feature the spec names, and a 0–100 score fitted on it would be noise scaled to 100. Guardrail (2) therefore leaves
  the rules as boolean gates — and the gates themselves fail guardrail (5).
- The out-of-sample "lift" of a top decile (+$64) is the kind of number a ledger reports; it fails the stress test the
  owner set (negative without five days, 23% of sessions up, 2026 negative).

### Gaps
- The feature list is the spec's; flow into the contract (who is buying), dealer strike-level positioning and event
  times are not in this data and are the only candidates step 5 of this repository left open.

## 5. Quote hygiene, "block if the score is missing", the spread/mid ≤ 5% picker rule

### Takeaway
Keep the hygiene and the missing-score block (they cost nothing). The spread rule binds: on IWM it rejects the
nearest-OTM candidate 30–44% of the time at sweep minutes and more than half the time after 13:00; on SPY/QQQ/SPXW it
rejects a few percent before 14:00 and most candidates after 15:30. The candidates it rejects are cheap and lose more
in percentage terms, so the rule is a sensible friction filter, not an edge.

### Cited Findings
- Share of nearest-OTM candidates with (ask − bid)/mid ≤ 5%, every session and minute 09:35–15:58 (2.8 M rows), by half
  hour: SPY 0.999 at 09:30, 0.996 at 12:00, 0.915 at 14:00, 0.743 at 15:00, 0.478 at 15:30; QQQ 0.999 → 0.993 → 0.912 →
  0.711 → 0.413; SPXW 0.996 → 0.990 → 0.932 → 0.782 → 0.441; IWM 0.945 → 0.697 → 0.370 → 0.156 → 0.042. Median spread/mid
  at 15:30: SPY 5.1%, QQQ 6.1%, SPXW 5.5%, IWM 22.2% — [spread.py](sweep_trigger/spread.py), `out/spread_by_halfhour.csv`.
- By year, all minutes: SPY 0.944 (2022) → 0.950 (2026); QQQ 0.797 → 0.967; SPXW 0.887 → 0.964; IWM 0.462 (2024) → 0.580
  → 0.670 — `out/spread_by_year.csv`.
- At sweep minutes (merged trigger) the nearest-OTM fade pick fails the rule: SPY 8.3% / 4.7% of picks (2022–24 /
  2025–26), QQQ 10.9% / 5.4%, SPXW 10.3% / 5.0%, IWM 44.1% / 30.4%; after 15:30, 645 of 999 picks; 13:45–15:30, 716 of
  3,235. The failing picks cost $0.19–0.32 on the ETFs against $0.54–1.33 for the passing ones and lose more of their
  premium (SPY −28.5% / −24.7% against −4.1% / −7.2% with the trailing stop) — `logs/spread.log`.
- Quote hygiene (ask > 0, bid > 0, bid ≤ ask) is applied at every entry in `sweeplib.pick_contracts`; a candidate failing
  it is skipped, which left 0.1–0.2% of merged sweeps without a fill.

### Inferences
- The rule mostly binds where the spec's own windows send trades (the last 90 minutes) and on IWM, which the spec
  approves for 0DTE scalps; on IWM the picker will often have nothing to buy.
- Rejected candidates are the pennies-with-wide-spreads subset that step 5 found to be "mostly fees"; keeping the rule
  removes the worst fills but does not create a positive remainder.

### Gaps
- None for this rule; it is fully testable and was tested on every minute.

## 6. Rule-by-rule verdicts

| Rule in the spec | Test (data, N, split) | Numbers | Verdict |
|---|---|---|---|
| Quote hygiene: ask > 0, bid > 0, bid ≤ ask | Applied at every entry; 14,917 merged sweeps | 0.1–0.2% of sweeps had no clean candidate | **Keep.** |
| Missing or zero score blocks the trade | Not testable as EV; a safety rule | — | **Keep** (as a guard, since no score exists that should be acted on). |
| 0DTE tickers: approve SPX, SPY, IWM; block QQQ on A+ fades; NDX unless proven | Merged fades by product, both periods | SPY −6.1% / −8.0%, SPXW −4.5% / −5.1%, QQQ −12.6% / −11.5%, IWM −18.6% / −13.7% of premium; all 95% ranges ≤ 0.4% at the top | **Change:** the ranking is SPXW ≈ SPY > QQQ > IWM; IWM is the worst, not an approval. No product is positive, so the list is moot for long premium. NDX untestable (no data). |
| Entry model: liquidity sweep + order block as the primary trigger | 160 definitions, 225,390 rows; chosen on 2022–24, read on 2025–26 | Underlying between +0.1 and −1.8 bps at 30 min in the fade direction; every definition negative after fees; the chosen one +$27 → −$56 | **Reject as an edge.** As a *detector* it is well defined (section 7) and can stay a boolean gate with no weight; it must not be sold as positive EV. |
| Reject displacement-only entries on 0DTE ("proven negative EV") | 17,169 displacement bars vs 14,917 sweeps | Displacement continuation −10.2% / −10.8%; sweeps −8.1% / −9.4% | **True but not discriminating** — keep as a gate if the engine needs one; it does not make the kept set positive. |
| Reject ORH-only sweeps unless with PDH/PDL within 0.2% or a gamma wall | OR sweeps with/without PDH/PDL within 0.2%, k = 1: 3,042 / 2,543 events | −7.5% → −4.6% (2022–24), −10.3% → −4.6% (2025–26); the dollar +$70 on 2025–26 is −$33 without 5 days | **Keep the ranking as a gate, drop the EV claim.** The gamma-wall clause is untestable (no strike-level book on disk). |
| Triple confirmation (OB + sweep + FVG) upgrades an A setup | FVG on 4.5% of sweeps, 779 events | Win 0.199 / 0.185 with FVG vs 0.193 / 0.193 without; underlying −1.0 / −5.7 bps vs −0.4 | **Reject.** OB presence is 99.7% (not a condition); FVG does not raise the win rate. |
| Direction: fade in 595–635, 635–720, 930–960; chase in 570–595, 825–930; gamma regime | Fade vs continuation by window, both periods; gamma sign on 245 sessions | Fades lose in every fade window but 09:55–10:35 (whose +$ fails the stress test); continuations lose in the chase windows; underlying within ±3.4 bps in every cell | **Reject as a rule.** Untestable as "between walls"; by net gamma sign no difference (−9.6% vs −9.3%). |
| Grade gate: ≥ 90 take, 80–89 take with triple confirmation, < 80 pass; remove SWEEP_FLOOR / BONUS_CAP / CONFIDENCE_CAP overwrites | Logistic and GBM fitted on 2022–24, scored once on 2025–26 | AUC 0.528 / 0.513 for the trade's outcome; top decile +$64 [−44, 217], −$39 without 5 days | **No score.** Removing the overwrites is right (they are invented weights); replacing them with a fitted 0–100 is not supported — leave boolean gates. |
| Contract picker: nearest same-day strike at or beyond spot, or 0.30–0.45 delta; spread/mid ≤ 5% | Every minute of every session (2.8 M candidates); the delta pick's availability | Delta pick unavailable 36–78% of the time after 15:30 and 59% of the time on IWM 13:45–15:30; spread rule rejects 30–44% of IWM picks and most picks after 15:30 | **Keep both picker rules as frictions**; add "no candidate → no trade" explicitly. The delta pick's fade is as negative as the nearest-OTM's (−5.5% / −7.4% pooled). |
| Module 9: FVG, order block, OTE 0.62–0.705, doji guard, on 1 m and 5 m after a sweep | 16,980 (k=1) and 25,028 (k=3) episodes; a stricter OTE on SPY | OTE fills 55–63%, −8.9% / −10.4% vs the close's −7.9% / −9.4%; OB fills 59–68%, −8.1% / −10.1%; strict OTE −11.0% / −3.1% vs −10.8% / −2.4% on the same episodes | **Implement only as a display**; as an entry rule it lowers the fill rate and does not improve the result. |
| Exits used by the spec (step 4's 50% trailing stop; +25% / −32%; hold to 15:58) | All three on every trade | Trailing stop is the least bad (−4% to −19% by product); target/stop −4% to −15%; hold −11% to −30% | No exit turns the fade positive. |

## 7. The formal sweep definition (code-ready) and the replacement rules

The definition below is what the tests above used; it is exact, has no look-ahead, and is offered as the detector the
engine should display — with the explicit statement that it carries no tested edge for long premium on 0DTE.

```python
# bars: 1-minute OHLC indexed by the minute the bar CLOSES (m = 1 closes at 09:31; m = 390 at 16:00).
# A level L is one of: ORH/ORL = max high / min low of bars 1..30 (valid from m = 31); PDH/PDL = prior session's
# regular-hours high/low; PWH/PWL = prior ISO week's high/low; SH/SL = the running session high/low over bars 1..e-1,
# counted only if it has not moved for SH_AGE = 10 bars (a swing extreme with resting orders).
# Parameters: X (bps beyond the level; 0 in the reference), k (bars allowed for the close back inside; 1 in the reference).

def sweep_high(bars, L, e, X=0, k=1):
    """A high-side liquidity sweep whose excursion bar is e. Returns the return bar r (the entry minute) or None."""
    thr = L * (1 + X / 1e4)
    if not (bars.high[e] >= thr and bars.close[e - 1] < L and bars.high[e - 1] < thr):   # beyond the line, from inside
        return None
    for r in range(e, e + k):                                                             # the close back inside within k bars
        if bars.close[r] < L:
            return r
    return None
# sweep_low mirrors it with low <= L(1 - X/1e4), close[e-1] > L, low[e-1] > thr, close[r] > L.
# Depth = (max high over e..r − L) / L in bps. Episodes of one (level, side, X) are at least 30 minutes apart.
# Confirmation (optional, not recommended): close[r+1] < close[r]; entry at r+1.
# Fade direction: PUT after a high-side sweep, CALL after a low-side sweep; entry at the ask stamped r (the quote at
# the bar's close), the nearest strike at or beyond spot with ask > 0, bid > 0, bid <= ask and (ask−bid)/mid <= 0.05.
```

The spec's phrase "fade-side sweep premium > breakout-side premium" was not made a condition: the fade-side and
breakout-side contracts are the two sides of the same chain at the same distance and their premia track each other
within the spread; a condition on it would select on noise. It is noted as untested.

Replacement rules, as the audit allows:
1. Keep quote hygiene, the spread/mid ≤ 5% rule and "missing score blocks" unchanged; add "no eligible contract → no
   trade" as an explicit outcome (it happens on IWM afternoons and after 15:30 everywhere).
2. Remove SWEEP_FLOOR, BONUS_CAP and CONFIDENCE_CAP (invented weights) and do not replace them with a fitted score:
   the rules stay boolean gates (sweep detected; level type; displacement-only; ORH coinciding with PDH/PDL), and the
   gates are documented as *not* positive EV on 2022–2026 for long premium.
3. Do not implement the direction-by-window rule or the "between walls" regime as a trade rule; show the window and,
   when strike-level dealer data exist, the regime, as context.
4. Module 9 geometry: implement the three constructs as drawn objects with the exact definitions in `sweeplib.py`, not
   as entry conditions.
5. The only product ordering the data supports is SPXW ≈ SPY (least negative) > QQQ > IWM; it is an ordering of losses.

## Blockers and gaps across the module

- NDX and QQQ-specific "A+" setups: no NDX data; "A+" has no empirical definition (section 4).
- "Major gamma wall within 0.2% of spot" and "positive gamma between walls": no strike-level dealer book on disk for the
  test window (the UW levels file is empty; the daily greek-exposure table is one net number a day for the last year).
- "Fade-side premium > breakout-side premium": not formalised (see section 7).
- SPXW on its own prints (no SPX bar high/low on disk); SPY's bars are the stated proxy.
- The three horizons beyond 0DTE (Weekly 4–7 DTE, Swing 8–28, LEAPS 90–365+) are outside this data set (same-day chains
  only); the trigger's lack of directional information in the underlying (section 1) applies to them, the option
  pricing does not.
