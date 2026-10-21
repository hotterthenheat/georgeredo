# Compass Phase 2, Hypothesis C: defined-risk structures in place of the naked 0DTE contract

Debit verticals (long ~0.60Δ / short ~0.40Δ and three neighbours) at the audit's own entries, and late-day ATM butterflies
held to settlement, on SPXW, SPY, QQQ and IWM same-day contracts. Every number comes from a script in
`research_notes/Compass phase 2/hyp_c_debit_flies/` (its `out/` holds the rows and summaries, `logs/` the runs). Nothing was
called from any API. Picked on 2022–2024, read once on 2025–2026; the picks were written to `preregistration.md` before the
2025–2026 runs were started (the file timestamps record the order: fit summaries 19:30–19:33, preregistration 19:34, the OOS
runs after it).

**The short answer.** A debit vertical does not keep a directional premium, because the audit's entries have none: every
spread cell is negative in both periods (pooled, −4 % to −28 % of the debit by cell and exit), and the one thing the
vertical does — losing a smaller share of its debit than the naked contract when both are held to settlement — is
confirmed out of sample (+9 to +16 points of debit) but turns a −15 % trade into a −6 % to +1.5 % one, with the naked
contract's own best exits still ahead. The late-day butterfly is where the data points: on SPY and QQQ a fly held to
settlement from 15:00 or 15:30 is positive after fees on both periods, but the three pre-registered picks (iron ±2 at
15:00, call ±2, call ±5) fell to +2 to +4.5 % of risk out of sample with intervals through zero and die under a $0.01-a-leg
worse fill, while a neighbouring cell I did not pick (the IRON ±5, SPY/QQQ, 15:00 and 15:30: +5.0 % and +6.0 % of risk OOS,
intervals clear of zero, every year positive, the mean still positive at $0.02 a leg worse fills) is the one that looks
like an edge. It was
identified after the OOS read, so it is a candidate for a confirmation test on sessions not yet in the set, not a rule.
moc_mag adds nothing reliable: the low-magnitude group is better at 15:00 and worse at 15:30, with every pooled interval
through zero but one that points the wrong way.

## 1. Data, conventions, fills

- Chains: `RAW/data_full/chains/{SPXW,SPY,QQQ,IWM}/<date>.parquet`, every same-day contract's 1-minute NBBO. SPXW 1,106
  sessions 2022-05-13 → 2026-10-09, SPY/QQQ 980 from 2022-11-11, IWM 621 from 2024-04-19. Half days dropped (SPXW 9, SPY 9,
  QQQ 9, IWM 6; the 41 audit trades that fell on them are left out of the pairing). Underlying: ETF 1-minute bars; SPX
  prints; VIX prints. Minute m = 0 is 09:30; a bar stamped t closes at t+1; a chain row stamped t is the quote at t; spot at
  quote minute m is the close of the bar stamped m−1 (ETF) or the SPX print at m.
- Fills: a long leg bought at the ask and sold at the bid, a short leg sold at the bid and bought back at the ask; $0.65 a
  leg each way; a leg expiring worthless pays nothing to close; a leg in the money at expiry settles at intrinsic with no
  fee — SPXW cash-settled on the last SPX print at or before 16:00 (a proxy for the official SET, stated as such; the
  audit's `spot_close`), SPY/QQQ/IWM on the 16:00 close (the bar stamped 15:59), no assignment or exercise fee assumed.
- Deltas: Black-Scholes on the mid's implied vol with r = q = 0. With r = q = 0 the delta depends on σ√T alone, so the
  total vol is solved directly from the mid by bisection and no day count enters. A contract with mid − intrinsic ≤ 0.01
  is skipped (no vol can be read off it).
- Split: fit 2022–2024, OOS 2025–2026 (IWM's fit is 2024-04 → 2024-12). "CI" is a 2,000-draw bootstrap resampling sessions;
  "wo5" the mean without the best five sessions; max drawdown and the longest losing streak are those of the 1-lot
  chronological sequence of the cell.
- Verification: `verify.py` re-derived 50 random structures (25 verticals, 25 butterflies, seed 20261021) from the raw
  chain and underlying files with plain row-by-row loops and a scalar bisection: the strikes chosen, the debit or credit,
  the settlement, the hold, flat and 50 %-trail results. **50 of 50 agree, 0 differences** (`out/verify.json`). The naked
  contract replayed by this folder's simulator agrees with the audit's `engine.simulate` on **7,105 of 7,105 trades** for
  each of the six rules both have (hold, flat, T1/backstop, T1/backstop/lock, struct 0 bp, struct 2 bp;
  `logs/run_spreads_all.log`).

Scripts: `common.py` (pricing, settlement, stats), `build.py` (one chain read per session → `out/spreads_<P>.parquet`,
`out/legs_<P>.parquet`, `out/flies_<P>.parquet`; all rebuildable from the raw files, ~2 minutes a product),
`moc15.py` (moc_mag at 15:00 and 15:30 → `out/moc_mag.parquet`), `run_spreads.py` (→ `spreads_summary[_all].csv`,
`spreads_paired[_all].csv`, `spreads_trades.parquet`), `run_flies.py` (→ `flies_summary[_all].csv`,
`flies_magdiff[_all].csv`), `picks.py` (the pre-registered picks on SPY+QQQ with the fill stress → `picks.csv`,
`picks_fillstress.csv`), `diag_cost.py` (round-trip cost → `diag_cost.csv`), `verify.py`. Run as
`nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I <script>`; the longest run is under 10 minutes.

## 2. Exact definitions

**Entries (reused, not re-derived).** The two universes are the audit's stored trades
(`Compass engine audit/exits_sizing/out/paths_<P>.parquet`, built by its `extract.py`; the rows `engine.load()` keeps,
`quotes_after ≥ 5`): universe A, the sweep fade — between the bars stamped 10:00 and 11:59 the first bar whose high is
≥ 2 bps above the 09:30–09:59 range high and whose close is back below it → put at the ask on that close (mirror for the
range low → call), one a session a side; universe B, one random quote minute a session in [10:00, 15:00] (seed 20261016),
call or put at random. Naked = the audit's nearest-OTM contract bought at the ask. A 3,433 trades (1,826 fit / 1,607 OOS),
B 3,672 (1,900 / 1,772) before the half-day cut.

**Debit verticals** at every entry, same side as the audit's trade, from the chain at the entry minute:
- `d60_40`: long the strike whose |Δ| is nearest 0.60, short the one nearest 0.40; `d70_30` and `d55_45` likewise;
- `atm_otm1`: long the strike nearest spot (a tie → the in-the-money one), short the next strike out of the money.
The long must be strictly more in the money than the short, its ask > 0, the short's bid > 0, the debit > 0; else no
structure (`d55_45` has none on 55 % of IWM, 30 % of SPY, 24 % of QQQ entries — the two deltas land on one $1 strike; `d60_40`
on 19 % of IWM; the rest under 6 %). Debit = long ask − short bid; max risk = the debit; width = |K_long − K_short|.
Mark at minute m = long bid − short ask (what closing at market returns). Structures built: A d60_40 3,352, d70_30 3,410,
d55_45 2,814, atm_otm1 3,410; B 3,382 / 3,650 / 2,452 / 3,651 (`spreads_trades.parquet`).

**Exits, judged on the mark at every minute after entry, filled at that minute's mark** (a target at its price exactly —
the audit's resting-limit rule); hard flat at 15:58 at the last mark quoted at or before it; a sale whose mark is ≤ 0 is
not made — the structure is held to settlement (the audit held a 0-bid contract the same way); fees $0.65 a leg each way,
none at settlement: `hold` (settlement); `flat` (15:58 only); `trail50` (step 4's 50 % trailing stop on the mark's running
peak from the first minute after entry, + flat); `t1_bs` (+25 % target on the debit, −32 % backstop, + flat);
`t1_bs_lock0` (t1_bs + the breakeven lock at +0 %: once the mark has been at or above the debit, sell at the first later
mark at or below it); `struct0` / `struct2` (universe A: the underlying trades back through the swept level + 0 / 2 bps on
a bar's high or low, sold at the next minute's mark, + flat). The naked contract is replayed by the same code (mark = its
bid, one leg) so every paired difference is like for like.

**Butterflies** at 15:00 (m = 330) and 15:30 (m = 360): K0 = the strike nearest spot with a call and a put quoted; wings
W = ±5 / ±10 / ±25 on SPXW, ±1 / ±2 / ±5 on SPY and QQQ, ±0.5 / ±1 / ±2 on IWM (scaled by price; ±0.5 exists on 12–18
sessions only and is ignored below), and W = the ATM straddle's mid rounded to the strike grid ($5 SPXW, $1 the ETFs; a
median of 10 on SPXW, 1 on the ETFs at 15:00). Long call fly: buy K0−W, sell 2 K0, buy K0+W, all calls, debit = ask + ask −
2 bid; long put fly likewise; iron fly: sell the K0 call and put at the bid, buy the K0−W put and the K0+W call at the ask,
credit = the two bids − the two asks, max risk = W − credit. Every leg must be quoted at the minute, the short legs' bids
> 0, max risk ≥ $0.05. Held to settlement; fees 4 × $0.65 at the open, none at expiry. % = of max risk.

**moc_mag.** At 15:30 the audit's own checkpoint t = 930 (inputs 15:00 → 15:30, `clock_session/out/t5_features.parquet`).
At 15:00 the audit's four inputs are re-computed over **14:30 → 15:00** (stated here because the audit's checkpoints start at
15:05): volume summed over the bars stamped 870..899 (SPXW: SPY's volume stands in, as in the audit), range = (highest
high − lowest low) / close(14:29) (SPX: prints 870..900 / print(870)), move = (close(14:59) − close(14:29)) / close(14:29),
sweep imbalance from the per-contract OHLC bars 870..899 against the chain mid at each bar's end with the audit's side
rule. Both are normalized by `t5b_moc_test.normalize()` **imported unchanged** (20-session same-minute mean/sd per name,
clipped z, logistic, moc_mag = the mean of the four sigmoids); the t = 930 rows come out identical to the audit's
`t5_scores.parquet` (3,663 rows, max |diff| 0.0). Quintile cuts are the 20/40/60/80th percentiles of moc_mag over the FIT
sessions per name and time (SPY 15:00: 0.350 / 0.433 / 0.510 / 0.614; `logs/moc15.log`); Q12 = below the fit 40th
percentile, read against the same cuts in both periods. About 97 % of fly sessions carry a score (the first 20 sessions a
name and sessions with fewer than 15 of the 20 prior do not).

## 3. The pre-registered picks (from `preregistration.md`, written before the OOS runs)

- Verticals, A: `d70_30 / struct0`. B: `d70_30 / hold`. Paired claim: a 0.70/0.30 vertical held to settlement loses a smaller
  share of its debit than the naked contract held (A and B). Expectation: all negative OOS — rejected on fit already,
  since there is no directional premium in these entries.
- Butterflies: P1 SPY+QQQ 15:00 iron ±2; P2 SPY+QQQ 15:00 long call ±2 (the cash-account form); P3 SPY+QQQ 15:00 long call
  ±5. Signal claim: Q12 > Q345 on P1–P3. "Edge" only if the OOS mean is positive with its interval clear of zero AND wo5 > 0
  AND both OOS years > 0; else "needs more data". No SPXW or IWM pick; 15:30 read as the grid.
- Why these and not the iron ±5: the fit tables I pre-registered from were the pooled four-name table (where SPXW's
  one-strike ±5 fly, −29 %, drags every ±5 cell under) and the per-name CALL-fly rows; the per-name IRON ±5 rows
  (SPY +4.8 %, QQQ +5.7 % on fit, intervals clear of zero) were never printed before the picks were written. That is a
  pre-registration miss on my side and the reason the iron ±5 is reported below as post hoc.

## 4. Debit verticals — results

**Round trip (friction, both periods pooled; `out/diag_cost.csv`).** The share of the debit given back the minute after
entry (debit − first mark) / debit: `atm_otm1` 5.4–8.9 % on the ETFs and 13–15 % on SPXW; `d60_40` 3.4–7.6 % / 5–6 %;
`d70_30` 2.3–6.5 % / 3.3 %; the naked contract 1.0–3.4 % on SPY/QQQ, 3.4–5.9 % on IWM, 1.5–2.5 % on SPXW. Two legs, two
spreads: the tighter the vertical, the larger the share of its debit that is bid-ask, and every early exit pays it twice.

**Pooled four names, % of debit after fees (mean [95 % CI], $ a structure, win rate, PF, wo5), fit → OOS**
(`out/spreads_summary_all.csv`; every cell × exit is in the CSV, these are the exits the audit kept):

| uni | cell | exit | fit n | fit % | OOS n | OOS % [CI] | OOS $ | win | PF | wo5 | 2025 / 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | d60_40 | hold | 1,788 | −10.0 | 1,564 | −7.6 [−14.0, −1.1] | −25.7 | 0.47 | 0.83 | −8.6 | −9.5 / −5.2 |
| A | d60_40 | t1_bs_lock0 | 1,788 | −8.5 | 1,564 | −8.3 [−9.5, −7.0] | −20.1 | 0.16 | 0.39 | −8.8 | −8.0 / −8.8 |
| A | d60_40 | struct0 | 1,788 | −8.5 | 1,564 | −7.5 [−8.6, −6.3] | −15.3 | 0.09 | 0.43 | −8.1 | −7.8 / −7.1 |
| A | **d70_30** | hold | 1,809 | −8.3 | 1,601 | −6.0 [−11.9, −0.2] | −41.1 | 0.45 | 0.85 | −6.8 | −7.3 / −4.3 |
| A | d70_30 | t1_bs_lock0 | 1,809 | −5.5 | 1,601 | −5.5 [−6.7, −4.4] | −25.8 | 0.17 | 0.53 | −5.9 | −5.3 / −5.8 |
| A | **d70_30** | **struct0 (pick)** | 1,809 | −5.2 | 1,601 | **−4.3 [−5.5, −3.0]** | −14.0 | 0.13 | 0.66 | −4.8 | −4.2 / −4.4 |
| A | d55_45 | hold | 1,497 | −10.8 | 1,317 | −8.8 [−16.0, −1.9] | −17.6 | 0.47 | 0.82 | −9.9 | −9.1 / −8.4 |
| A | d55_45 | struct0 | 1,497 | −12.3 | 1,317 | −10.9 [−12.1, −9.7] | −17.0 | 0.06 | 0.23 | −11.8 | −11.3 / −10.5 |
| A | atm_otm1 | hold | 1,809 | −16.8 | 1,601 | −12.9 [−19.9, −5.7] | −14.0 | 0.41 | 0.74 | −14.8 | −15.3 / −9.7 |
| A | atm_otm1 | struct0 | 1,809 | −15.6 | 1,601 | −14.8 [−16.0, −13.6] | −14.9 | 0.05 | 0.11 | −15.5 | −15.4 / −14.1 |
| B | d60_40 | hold | 1,767 | −8.6 | 1,615 | +1.5 [−2.8, +5.7] | +3.1 | 0.52 | 1.03 | +0.7 | −2.3 / +6.2 |
| B | d60_40 | t1_bs_lock0 | 1,767 | −10.5 | 1,615 | −8.6 [−9.5, −7.7] | −15.8 | 0.14 | 0.36 | −8.7 | −8.6 / −8.5 |
| B | **d70_30** | **hold (pick)** | 1,889 | −6.7 | 1,761 | **+1.3 [−2.6, +5.0]** | +4.9 | 0.52 | 1.03 | +0.6 | −2.2 / +5.6 |
| B | d70_30 | trail50 | 1,889 | −11.0 | 1,761 | −5.3 [−8.2, −2.3] | −3.6 | 0.36 | 0.97 | −5.7 | −6.5 / −3.8 |
| B | d70_30 | t1_bs_lock0 | 1,889 | −7.2 | 1,761 | −5.7 [−6.5, −4.9] | −17.1 | 0.16 | 0.56 | −5.8 | −5.7 / −5.7 |
| B | d55_45 | hold | 1,276 | −12.1 | 1,176 | +1.8 [−3.4, +7.0] | +1.2 | 0.53 | 1.02 | +0.7 | −0.8 / +4.9 |
| B | atm_otm1 | hold | 1,890 | −14.9 | 1,761 | −5.2 [−10.6, −0.0] | −4.1 | 0.44 | 0.91 | −7.0 | −10.1 / +1.0 |

Tails of the picks OOS: A d70_30/struct0 avg win +$219, avg loss −$48, p5 −$193, p1 −$363, worst −$1,393 (2025-04-23),
max drawdown −$26,047 over the 1-lot sequence, longest losing streak 78; B d70_30/hold avg win +$348, avg loss −$361,
p5 −$1,121, p1 −$2,073, worst −$7,091 (2025-04-10), MDD −$32,756, streak 9. `flat` and `trail50` are the worst exits for
every spread cell in both periods (−5 to −28 %): they pay the second round trip on both legs. By product
(`spreads_summary_all.csv`, d70_30 OOS): A struct0 SPXW −2.3 % [−4.1, −0.3], SPY −3.2 %, QQQ −4.2 %, IWM −7.3 %; A hold
−8.2 / −7.9 / −2.3 / −5.8 %; B hold SPXW −0.5 % [−7.9, +7.0] (2025 −2.4, 2026 +1.8), SPY +7.2 % [−0.3, +14.3] (2026 +13.0),
QQQ +2.3 %, IWM −3.9 %.

**Paired against the naked contract on the same entries, OOS** (`out/spreads_paired_all.csv`; diff = spread − naked in
points of each trade's own debit, and in $ a structure):

| uni | cell | exit | n | spread % | naked % | diff pts [CI] | spread $ | naked $ | diff $ [CI] |
|---|---|---|---|---|---|---|---|---|---|
| A | d70_30 | hold | 1,601 | −6.0 | −15.2 | +9.3 [−1.2, +18.3] | −41.1 | −20.5 | −20.6 [−107.6, +48.2] |
| A | d70_30 | struct0 | 1,601 | −4.3 | −2.0 | −2.2 [−5.1, +0.3] | −14.0 | +10.0 | −24.0 [−46.4, −6.2] |
| A | d70_30 | t1_bs_lock0 | 1,601 | −5.5 | −5.6 | +0.1 [−0.7, +0.9] | −25.8 | −20.5 | −5.2 [−11.8, +1.9] |
| A | d60_40 | hold | 1,564 | −7.6 | −15.0 | +7.4 [−3.1, +17.0] | −25.7 | −20.7 | −5.0 [−95.4, +72.3] |
| A | d60_40 | struct0 | 1,564 | −7.5 | −1.8 | −5.6 [−8.7, −2.9] | −15.3 | +10.3 | −25.5 [−53.8, −2.6] |
| A | atm_otm1 | trail50 | 1,601 | −27.6 | −7.4 | −20.1 [−25.8, −14.5] | −30.1 | −16.6 | −13.5 [−66.5, +31.3] |
| B | d70_30 | hold | 1,761 | +1.3 | −15.2 | **+16.4 [+7.4, +24.7]** | +4.9 | −31.7 | +36.7 [+5.6, +66.0] |
| B | d70_30 | trail50 | 1,761 | −5.3 | −1.8 | −3.4 [−9.0, +2.0] | −3.6 | −0.1 | −3.5 [−28.3, +20.4] |
| B | d70_30 | t1_bs | 1,761 | −6.2 | −8.3 | +2.1 [+0.7, +3.3] | −16.0 | −18.2 | +2.2 [−7.1, +11.8] |
| B | d60_40 | hold | 1,615 | +1.5 | −13.5 | +15.0 [+6.3, +23.3] | +3.1 | −34.1 | +37.2 [+1.3, +69.9] |
| B | d55_45 | hold | 1,176 | +1.8 | −10.7 | +12.5 [+1.8, +22.0] | +1.2 | −47.1 | +48.3 [−5.5, +99.3] |
| B | atm_otm1 | hold | 1,761 | −5.2 | −15.2 | +9.9 [+1.9, +17.2] | −4.1 | −31.7 | +27.6 [−11.5, +61.4] |

Fit paired (same file): A d70_30 hold +11.0 [+2.2, +19.4]; B d70_30 hold +13.6 [+5.3, +20.9]; under trail50 and struct0
the spread is worse than the naked contract in every cell in both periods. Note the naked contract's own struct0 on
universe A reads +$10 a contract (−1.8 to −2.0 % of debit) OOS — the audit's figure, not a finding here.

**Stress on the picks.** A d70_30/struct0: fit [−6.3, −4.1], OOS [−5.5, −3.0], every year 2022–2026 negative (pooled
−3.9, −4.4, −6.2, −4.2, −4.4 %), wo5 −4.8 %, worst session 2025-04-23 (−$1,854 over its 1-lot structures). B d70_30/hold:
fit −6.7 % (pooled by year −9.3, −7.7, −5.3 %), OOS +1.3 % with 2025 −2.2 % and 2026 +5.6 %, wo5 +0.6 %, PF 1.03, worst
session 2025-04-10 (−$7,165); 2026's +5.6 % is carried by SPY (+13.0 %) — a year, not a rule, and the fit figure for the
same cell was negative in every year. The three delta-picked B hold cells read +1.3 to +1.8 % OOS after −6.7 to −12.1 %
on fit; atm_otm1 held reads −5.2 %.

**Verdict — debit verticals: no edge.** The hypothesis was that the vertical neutralizes enough decay and vega to keep
a directional premium. What the data shows: (i) the spread's loss is smaller in share-of-debit terms than the naked
contract's when both are held (confirmed, +9 to +16 points, clear of zero on B in both periods), because the short leg
pays back part of the decay — but the audit's entries carry no direction (the underlying's forward return is within
±2 bps), so what is kept is a smaller loss, not a premium; (ii) every early exit on a spread pays two bid-asks and is
worse than holding, so the audit's exit stack cannot be transplanted onto a vertical; (iii) the spread costs 2–5× the
naked contract, and in dollars a structure it loses as much or more in almost every cell; (iv) against the naked
contract's own best exits (struct0 on A, trail50 on B) the spread is behind everywhere. Keep the vertical out of the
engine. The one honest use is as the cash-account way to express a view the engine already has — and it has none.

## 5. Butterflies — results

**By name, OOS 2025–2026, held to settlement, % of max risk [CI], $ a structure, win, PF, wo5, by year**
(`out/flies_summary_all.csv`; call fly and iron fly — the put fly sits between them, same payoff, different fills).
Fit figures in brackets after the name where the cell matters (`out/flies_summary.csv`, `out/picks.csv`).

| name | time | wing | form | OOS n | OOS % [CI] | $ | win | PF | wo5 % | 2025 / 2026 % |
|---|---|---|---|---|---|---|---|---|---|---|
| SPXW | 15:00 | ±5 | call | 439 | −41.9 [−52.1, −31.7] | −43.8 | 0.23 | 0.47 | −47.0 | −38.8 / −46.0 |
| SPXW | 15:00 | ±10 | call | 440 | −17.0 [−26.2, −7.9] | −48.6 | 0.38 | 0.70 | −20.6 | −17.4 / −16.5 |
| SPXW | 15:00 | ±25 | call (fit +0.8) | 439 | −3.5 [−8.6, +1.6] | −45.7 | 0.54 | 0.85 | −5.5 | −5.1 / −1.5 |
| SPXW | 15:00 | ±25 | iron (fit +3.0) | 439 | −2.3 [−7.4, +2.9] | −28.1 | 0.55 | 0.91 | −4.3 | −3.8 / −0.4 |
| SPXW | 15:00 | straddle (med 10) | iron | 439 | −10.3 [−19.4, −1.4] | −35.7 | 0.41 | 0.82 | −12.2 | −11.2 / −9.2 |
| SPXW | 15:30 | ±25 | iron (fit +1.9) | 440 | −1.1 [−5.6, +3.3] | −20.9 | 0.55 | 0.92 | −2.6 | −3.7 / +2.3 |
| SPXW | 15:30 | ±5 / ±10 | iron | 440 / 439 | −27.1 / −10.5 | −31.7 / −37.1 | 0.28 / 0.41 | 0.62 / 0.77 | | |
| SPY | 15:00 | ±1 | call (fit +3.4) | 438 | −10.2 [−21.5, +2.2] | −3.0 | 0.38 | 0.81 | −15.5 | −13.9 / −5.5 |
| SPY | 15:00 | ±2 | call (fit +8.1) **P2** | 439 | +5.1 [−1.8, +12.7] | +4.0 | 0.54 | 1.17 | +2.1 | −0.3 / +12.0 |
| SPY | 15:00 | ±2 | iron (fit +11.0) **P1** | 438 | +6.8 [−0.1, +14.6] | +5.5 | 0.55 | 1.24 | +3.7 | +1.9 / +13.1 |
| SPY | 15:00 | ±5 | call (fit +2.8) **P3** | 440 | +3.4 [+0.3, +6.3] | +10.5 | 0.62 | 1.33 | +2.2 | +2.1 / +5.1 |
| SPY | 15:00 | ±5 | iron (fit +4.8 [+2.7, +6.8]) | 440 | +5.0 [+1.9, +8.0] | +16.3 | 0.64 | 1.55 | +3.8 | +3.6 / +6.8 |
| SPY | 15:00 | straddle (med 1) | iron | 439 | +0.6 [−8.9, +10.5] | +1.6 | 0.47 | 1.07 | −1.2 | −3.6 / +6.0 |
| SPY | 15:30 | ±2 | call (fit +6.8) | 439 | +7.2 [+1.0, +13.7] | +5.3 | 0.60 | 1.25 | +4.7 | +2.3 / +13.4 |
| SPY | 15:30 | ±2 | iron | 439 | +9.1 [+2.7, +15.7] | +7.1 | 0.60 | 1.34 | +6.5 | +4.3 / +15.2 |
| SPY | 15:30 | ±5 | call (fit +1.6) | 440 | +4.2 [+1.9, +6.7] | +13.1 | 0.64 | 1.53 | +3.3 | +3.0 / +5.8 |
| SPY | 15:30 | ±5 | iron (fit +3.2 [+1.4, +5.0]) | 440 | +5.5 [+3.1, +8.1] | +17.7 | 0.66 | 1.76 | +4.6 | +4.3 / +7.2 |
| QQQ | 15:00 | ±1 | call (fit +3.6) | 441 | −18.0 [−30.2, −5.8] | −4.4 | 0.35 | 0.73 | −23.4 | −18.1 / −17.9 |
| QQQ | 15:00 | ±2 | call (fit +10.8) **P2** | 441 | −0.9 [−9.2, +7.2] | −1.3 | 0.48 | 0.95 | −3.8 | −2.1 / +0.6 |
| QQQ | 15:00 | ±2 | iron (fit +14.3) **P1** | 440 | +2.2 [−6.3, +10.7] | +1.4 | 0.50 | 1.05 | −1.0 | +1.0 / +3.6 |
| QQQ | 15:00 | ±5 | call (fit +3.9) **P3** | 438 | +0.9 [−2.6, +4.6] | −1.5 | 0.55 | 0.97 | −0.6 | +0.3 / +1.7 |
| QQQ | 15:00 | ±5 | iron (fit +5.7 [+3.4, +7.9]) | 438 | +5.0 [+1.4, +8.7] | +13.9 | 0.61 | 1.38 | +3.5 | +4.7 / +5.4 |
| QQQ | 15:30 | ±2 | call | 440 | +5.4 [−1.9, +13.0] | +2.0 | 0.56 | 1.08 | +3.0 | +3.1 / +8.3 |
| QQQ | 15:30 | ±2 | iron | 440 | +8.5 [+1.0, +16.4] | +5.0 | 0.57 | 1.21 | +6.0 | +6.0 / +11.7 |
| QQQ | 15:30 | ±5 | call | 439 | +3.5 [+0.5, +6.5] | +6.7 | 0.60 | 1.20 | +2.1 | +2.8 / +4.3 |
| QQQ | 15:30 | ±5 | iron (fit +4.6 [+2.6, +6.6]) | 439 | +6.4 [+3.3, +9.5] | +17.3 | 0.64 | 1.59 | +5.1 | +6.1 / +6.7 |
| IWM | 15:00 | ±1 | call (fit −8.3) | 438 | −8.3 [−14.9, −2.0] | −3.9 | 0.50 | 0.75 | −11.0 | −7.5 / −9.3 |
| IWM | 15:00 | ±2 | call (fit −2.3) | 438 | −0.1 [−3.5, +3.1] | −0.8 | 0.57 | 0.95 | −1.5 | +0.4 / −0.9 |
| IWM | 15:00 | ±2 | iron | 438 | +3.0 [−0.6, +6.3] | +3.3 | 0.59 | 1.21 | +1.5 | +3.3 / +2.5 |
| IWM | 15:30 | ±2 | iron | 436 | +3.5 [+0.7, +6.5] | +4.0 | 0.59 | 1.32 | +2.4 | +2.2 / +5.2 |

Every SPXW cell is negative or on zero in both periods: with $5 strikes a ±5 or ±10 fly is one or two strikes wide and the
four fills are most of the structure (±5: risk $1.14, win 0.23); ±25 is the only SPXW wing whose fills do not dominate, and
it is −2 to −4 % OOS after +1 to +3 % on fit. IWM is negative on every call-fly cell in both periods and marginal on the
iron ±2. The ETF ±1 fly and the straddle-width wing (which is ±1 on the ETFs) flip from +2 to +4 % on fit to −10 to −18 %
OOS: a $0.30 structure with $2.60 of fees.

**The pre-registered picks and the post-hoc iron ±5, SPY + QQQ pooled** (`out/picks.csv`, `out/picks_fillstress.csv`;
% of max risk; "1c" / "2c" = every leg filled $0.01 / $0.02 worse than the NBBO used, $4 / $8 a structure):

| cell | period | n | mean $ | mean % [CI] | win | avg W / L $ | p5 / p1 / worst $ | PF | MDD $ | streak | wo5 % | by year % | 1c % [CI] | 2c % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **P1** 15:00 iron ±2 | fit | 1,046 | +11.4 | +12.6 [+7.3, +18.0] | 0.63 | +49 / −51 | −98 / −126 / −147 | 1.60 | −870 | 8 | +10.3 | 22: +24.6, 23: +12.2, 24: +11.4 | +8.2 [+3.1, +13.2] | +4.1 |
| P1 | OOS | 878 | +3.4 | **+4.5 [−2.8, +11.7]** | 0.52 | +54 / −52 | −90 / −113 / −133 | 1.14 | −1,817 | 13 | +1.5 | 25: +1.5, 26: +8.3 | −0.5 [−7.3, +6.3] | −4.9 |
| **P2** 15:00 call ±2 | fit | 1,047 | +8.4 | +9.4 [+4.5, +14.6] | 0.61 | +47 / −52 | −101 / −130 / −152 | 1.41 | −934 | 9 | +7.2 | +20.7, +9.2, +8.2 | +5.2 [+0.5, +10.1] | +1.4 |
| P2 | OOS | 880 | +1.3 | **+2.1 [−5.1, +9.0]** | 0.51 | +53 / −53 | −92 / −115 / −134 | 1.05 | −2,167 | 16 | −0.8 | 25: −1.2, 26: +6.3 | −2.6 [−9.3, +3.9] | −6.9 |
| **P3** 15:00 call ±5 | fit | 1,047 | +11.3 | +3.4 [+1.4, +5.3] | 0.66 | +56 / −74 | −140 / −274 / −408 | 1.44 | −1,339 | 8 | +2.5 | +6.0, +3.4, +3.0 | +2.3 [+0.4, +4.3] | +1.3 |
| P3 | OOS | 878 | +4.5 | **+2.2 [−1.0, +5.2]** | 0.59 | +73 / −92 | −197 / −315 / −471 | 1.12 | −3,295 | 8 | +1.0 | 25: +1.2, 26: +3.4 | +1.0 [−2.1, +4.0] | −0.1 |
| post hoc: 15:00 iron ±5 | fit | 1,047 | +18.5 | +5.3 [+3.2, +7.3] | 0.69 | +60 / −74 | −132 / −267 / −389 | 1.81 | −1,183 | 8 | +4.4 | +7.7, +4.8, +5.4 | +4.2 [+2.1, +6.2] | +3.1 [+1.1, +5.1] |
| post hoc: 15:00 iron ±5 | OOS | 878 | +15.1 | **+5.0 [+1.7, +8.2]** | 0.62 | +77 / −87 | −185 / −302 / −350 | 1.46 | −2,190 | 8 | +3.9 | 25: +4.2, 26: +6.1 | +3.8 [+0.5, +7.0] | +2.6 [−0.6, +5.7] |
| post hoc: 15:30 iron ±5 | fit | 1,048 | +13.5 | +3.9 [+2.1, +5.6] | 0.68 | +50 / −66 | −121 / −262 / −402 | 1.65 | −1,514 | 8 | +3.4 | +3.6, +3.9, +3.9 | +2.9 [+1.1, +4.5] | +1.8 [+0.1, +3.5] |
| post hoc: 15:30 iron ±5 | OOS | 879 | +17.5 | **+6.0 [+3.4, +8.4]** | 0.65 | +67 / −75 | −154 / −250 / −323 | 1.67 | −2,145 | 8 | +4.6 | 25: +5.2, 26: +6.9 | +4.8 [+2.3, +7.2] | +3.6 [+1.2, +6.0] |
| grid: 15:30 iron ±2 | OOS | 879 | +6.1 | +8.8 [+2.2, +15.6] | 0.59 | | | 1.27 | −1,693 | 8 | +5.3 | +4.2, +10.7 | +4.1 [−2.1, +10.3] | −0.2 |
| grid: 15:30 call ±5 | OOS | 879 | +9.9 | +3.9 [+1.4, +6.2] | 0.62 | | | 1.34 | −2,519 | 8 | +2.7 | +2.9, +5.1 | +2.7 [+0.3, +5.1] | +1.6 |

Worst OOS sessions (SPY + QQQ, one structure each): P1 2026-01-07 (−$250), P2 2025-11-05 (−$262), P3 and the 15:00
iron ±5 2026-03-09 (−$706 / −$693), the 15:30 iron ±5 2025-03-04 (−$600); days up 282 of 441 OOS sessions on the 15:00
iron ±5, 298 of 441 at 15:30. Why the iron form beats the call form at the same wing: the long call fly pays the ITM wing's wider spread (the
K0−5 call); the iron buys the OTM put there instead, and sells the ATM straddle at the bid — the same settlement payoff
for $3–8 less a structure. An iron fly is a defined-risk credit combination, which most cash accounts cannot hold
(spread approval); the long call/put fly can, and it is the form that did not pass.

**moc_mag** (`out/flies_magdiff_all.csv`, `out/picks.csv`; Q12 − Q345 in points of risk, interval from a session
bootstrap within each group): P1 OOS Q12 +8.5 % (n 363, win 0.58) vs Q345 +1.7 % (515, 0.48), +6.8 [−7.7, +20.3]; P2 +6.2 vs
−0.8, +7.1 [−7.0, +20.9]; P3 +3.4 vs +1.3, +2.1 [−3.9, +7.9]; 15:00 iron ±5 +6.0 vs +4.3, +1.7 [−4.6, +7.6] (fit −0.5 [−4.1,
+3.3]). At 15:30 the sign turns: iron ±5 Q12 +2.8 vs Q345 +8.4, **−5.6 [−10.4, −0.8]** (SPY −4.4 [−9.0, −0.1], QQQ −6.7
[−12.5, −1.1]), call ±5 −5.1 [−9.8, −0.4], iron ±2 −6.6 [−19.1, +5.5]. On fit every pooled contrast was +2 to +11 with
intervals through zero. The pooled four-name OOS contrasts (`flies_magdiff_all.csv`) are the same picture. A signal that
helps at 15:00 and hurts at 15:30 with every interval through zero but one pointing the wrong way is not a signal; the
audit's reading of moc_mag as a volatility gauge (ρ +0.16–0.21 with |move|) does not translate into a better fly cut,
because a fly's result depends on where the close lands relative to K0, and the gauge says how far, not where.

**Verdict — butterflies.**
- P1, P2, P3 (pre-registered): **needs more data / no edge established.** All three keep a positive sign OOS, none has its
  interval clear of zero, P2's wo5 and 2025 are negative, and a $0.01-a-leg worse fill takes P1 and P2 below zero (P3 to
  +1.0 % [−2.1, +4.0]). The fit means shrank by 60–80 %, the shrinkage one expects from picking the best of 14 ETF cells.
- SPXW and IWM flies: **no edge** (SPXW negative at every wing both periods; IWM negative or marginal).
- The iron ±5 on SPY and QQQ at 15:00 and 15:30: **a candidate, not a rule.** Positive in every year 2022–2026, intervals
  clear of zero in both periods, wo5 positive, PF 1.46–1.81; at $0.02 a leg worse than the NBBO the mean stays positive
  in all four period × time cells and the interval clear of zero in three (the 15:00 OOS cell reads +2.6 % [−0.6, +5.7]).
  It was not pre-registered (section 3 says why), so this folder's OOS cannot confirm it:
  the same data that found it is the data it is read on.

## 6. The exact rule, if one is justified

None is justified from the pre-registered picks. What the data supports is a **confirmation test**, not a trade:

- Structure: iron butterfly, SPY and QQQ, K0 = the strike nearest spot at the entry minute, wings ±5, entered at 15:30
  (and 15:00 as the second cell), every leg at the NBBO, held to settlement, no exit. 1 lot. Fees $0.65 a leg.
- Pass criteria, fixed now: on sessions after 2026-10-09 (none are in this data set), at least 250 sessions a name, the
  SPY + QQQ pooled mean > 0 with its session-bootstrap 95 % interval clear of zero under the $0.01-a-leg stress, wo5 > 0,
  and both names positive. Fail on any one. Code: `build.py` + `picks.py`, unchanged.
- Until then, nothing in the Compass engine: no fly, no cut by moc_mag, no late-day structure. If the owner wants the
  cash-account form, the long call ±5 fly is the one to test the same way — it reads +3.9 % [+1.4, +6.2] at 15:30 OOS but
  +2.2 % [−1.0, +5.2] at 15:00, and its fit figures were the weaker ones.

## 7. Gaps and limits

- One-minute NBBO only: a stop "on every tick" would fire inside the minute; exits here fire on the recorded minute's
  mark. The flies have no exit, so this does not touch them.
- The naked contract's entry universe is the audit's; a vertical or fly at a different entry (an underlying signal with
  real direction) is untested here — and the audit found none.
- SPXW settlement is the last SPX print at or before 16:00, not the official SET; the ETF close is the 15:59 bar's close
  with no assignment fee; a fly with an ITM short pair on an ETF carries pin risk at the close that intrinsic settlement
  does not price.
- The iron fly's fills are the NBBO at one minute; the $0.01 and $0.02 stresses stand in for queue position, not for
  size. Quoted sizes were not checked for the flies.
- IWM's fit is eight months; its results are OOS-heavy and read accordingly.
- moc_mag at 15:00 is a construction of this study (14:30 → 15:00 inputs through the audit's normalization), not the
  audit's own checkpoint.
