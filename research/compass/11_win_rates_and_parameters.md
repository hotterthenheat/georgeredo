# 11 — Win rate and average trade, every configuration tested

Written 2026-10-15 from the result files under `results/v1/` (the same rows `05_results.md` reports).
Fills are ask in / bid out, $0.70 a contract a side. "Avg $" is per one contract (per 100 shares for the
covered call). "Avg % of premium" is the trade's P&L over the premium paid (a long) or the credit taken
(a short). A win is a trade that closed above zero after costs.

## The Slayer / Compass baseline parameters (config v0, protocol §4)

| Part | Parameter |
|---|---|
| Trigger | RSI 14 on 1-minute bars crossing 55 up (calls) / 45 down (puts), close beyond EMA 9 |
| EMAs | 5 / 9 / 20 / 50 / 200 on 1m, 5m, 15m, 30m, 1h and daily |
| 5-minute confirmation | close beyond EMA 20 and the session VWAP |
| 15-minute alignment | EMA 20 vs EMA 50, price on its side ("EMA 15" read as the 15-minute timeframe) |
| Relative volume | ≥ 1.0× the same minute of the prior 20 sessions |
| Structure | higher highs / higher lows (lower for puts) on 5-minute pivots, 3 bars each side |
| Entry window | 09:45–14:50 New York |
| Contract | delta 0.30–0.60, nearest 0.45 (delta from the mid's implied vol) |
| Liquidity | spread < 12% of mid, ask ≥ $0.05, OI > 250 and volume > 100 where available |
| Exits, first hit wins | 15:50 cutoff · 5-minute close through the swing level · 1-minute close through VWAP · −25% stop · +25% on half, +50% on the rest · next 15-minute EMA · 60 minutes held |
| Book | one position a symbol; ranking = expected net profit ÷ expected worst drawdown |

Universe: 0DTE SPY/QQQ/IWM (S01), SPXW (S09), weekly expirations (S03), 40 Tier A single names (S06).

## Directional and short-premium setups (all rejected)

| Configuration | Trades | Win rate | Avg $ / trade | Avg % of premium | Avg win % | Avg loss % |
|---|---:|---:|---:|---:|---:|---:|
| S01 baseline Quick Scalps 0DTE SPY/QQQ/IWM | 2886 | 34.3% | -4.19 | -4.9% | +36.2% | -26.4% |
| S09 baseline Quick Scalps 0DTE SPXW | 1229 | 33.8% | -46.18 | -3.8% | +37.8% | -25.0% |
| S03 baseline on weekly expirations | 818 | 37.7% | +1.27 | -0.1% | +26.6% | -16.2% |
| S12 15:00 long, first-half-hour direction | 2214 | 30.4% | -4.36 | -15.1% | +100.1% | -65.3% |
| S12b 10:00 long to 15:00 | 2499 | 33.4% | -4.87 | -3.6% | +145.6% | -78.3% |
| S12b 10:00 short opposite vertical | 2455 | 53.9% | -2.56 | -10.1% | +81.9% | -117.9% |
| S10 short single fade, cutoff_stop2 | 2886 | 55.4% | +0.52 | -3.6% | +74.4% | -100.7% |
| S10 short single fade, hold60_stop2 | 2886 | 54.6% | -2.59 | -5.6% | +45.2% | -66.6% |
| S10 short single fade, cutoff_nostop | 2886 | 65.1% | -2.80 | -8.2% | +72.7% | -159.2% |
| S10 short vertical fade, cutoff_stop2 | 2857 | 49.4% | -5.65 | -15.3% | +71.0% | -99.6% |
| S15 short ATM straddle 10:00-15:50 | 1941 | 58.0% | -15.46 | -5.5% | +43.6% | -73.2% |
| S16b weekly prior-day fade, time_only | 1041 | 37.8% | -9.91 | -6.8% | +51.7% | -42.3% |
| S16b weekly prior-day fade, stop50 | 1041 | 36.2% | -7.50 | -5.4% | +52.3% | -38.2% |
| S11 short vertical into breakout, 21 sessions (prelim) | 173 | 39.9% | -193.25 | -215.8% | +61.6% | -399.9% |

The S01 row is the baseline on its own. The S02 grid below changes one parameter at a time.
S11 is preliminary: 21 sessions of the event pull, marked on end-of-day quotes. S06 (40 single names),
S07 and S08 (daily screens, earnings drift) were tested on the underlying's return, not on option
trades, so they have no option win rate; none cleared its rule (`05_results.md`).

## S02 — the baseline with one parameter changed (41 variants, 0DTE SPY/QQQ/IWM)

| Variant | Trades | Win rate | Avg $ / trade | Avg % of premium | Avg win % | Avg loss % |
|---|---:|---:|---:|---:|---:|---:|
| invalidation_only | 1939 | 39.0% | -2.69 | -2.0% | +67.6% | -46.5% |
| daily_trend | 1473 | 35.9% | -3.44 | -4.0% | +35.7% | -26.3% |
| slow200 | 2484 | 35.0% | -3.54 | -4.2% | +36.4% | -26.0% |
| tp50_100 | 2642 | 30.5% | -4.08 | -4.2% | +51.3% | -28.6% |
| delta40_60 | 2624 | 35.1% | -4.42 | -4.3% | +34.8% | -25.5% |
| no_15m | 4597 | 36.2% | -3.46 | -4.4% | +33.5% | -26.0% |
| rsi21 | 2476 | 34.5% | -3.97 | -4.5% | +36.6% | -26.2% |
| tp100 | 2642 | 32.6% | -4.03 | -4.5% | +38.8% | -25.5% |
| pick_tightest | 2824 | 34.8% | -4.20 | -4.5% | +35.3% | -25.8% |
| stop40 | 2518 | 40.4% | -3.92 | -4.6% | +36.5% | -32.5% |
| rsi_60_40 | 2647 | 35.2% | -4.45 | -4.6% | +36.9% | -27.2% |
| no_structure | 5184 | 33.9% | -3.76 | -4.7% | +36.1% | -25.6% |
| stop30 | 2699 | 36.6% | -3.89 | -4.7% | +37.0% | -28.8% |
| no_5m | 3680 | 33.6% | -3.84 | -4.8% | +32.0% | -23.4% |
| slow100 | 2684 | 34.4% | -4.06 | -4.8% | +36.3% | -26.3% |
| no_partial | 2888 | 30.1% | -4.35 | -4.8% | +51.2% | -28.9% |
| lead13 | 2958 | 34.3% | -4.15 | -4.9% | +36.1% | -26.3% |
| hold30 | 3105 | 37.3% | -4.14 | -4.9% | +31.5% | -26.5% |
| mid34 | 2856 | 34.1% | -3.94 | -4.9% | +35.9% | -26.0% |
| lead8 | 2885 | 34.3% | -4.20 | -4.9% | +36.2% | -26.4% |
| spread5 | 2819 | 34.3% | -4.28 | -4.9% | +36.1% | -26.3% |
| mid21 | 2885 | 34.2% | -4.09 | -4.9% | +36.2% | -26.3% |
| spread10 | 2885 | 34.3% | -4.21 | -4.9% | +36.2% | -26.4% |
| no_ema_target | 2886 | 34.3% | -4.19 | -4.9% | +36.2% | -26.4% |
| spread8 | 2878 | 34.3% | -4.23 | -4.9% | +36.1% | -26.4% |
| rsi7 | 3677 | 34.2% | -3.85 | -5.0% | +35.8% | -26.1% |
| spread15 | 2887 | 34.3% | -4.19 | -5.0% | +36.2% | -26.4% |
| no_vwap_loss | 2773 | 35.4% | -4.17 | -5.0% | +36.8% | -27.9% |
| no_invalidation | 2881 | 34.3% | -4.18 | -5.0% | +36.3% | -26.5% |
| hold120 | 2830 | 32.9% | -4.24 | -5.0% | +38.0% | -26.0% |
| lead3 | 2960 | 34.2% | -4.25 | -5.0% | +36.2% | -26.4% |
| relvol125 | 1400 | 33.9% | -4.83 | -5.0% | +36.0% | -26.1% |
| lead5 | 2902 | 34.3% | -4.31 | -5.0% | +36.1% | -26.5% |
| rsi9 | 3343 | 34.0% | -4.01 | -5.0% | +35.9% | -26.2% |
| stop20 | 3139 | 33.0% | -4.40 | -5.0% | +33.6% | -24.1% |
| rsi_50_50 | 2374 | 33.6% | -3.81 | -5.5% | +35.4% | -26.2% |
| delta30_50 | 2805 | 33.2% | -4.25 | -5.7% | +37.0% | -26.8% |
| relvol_off | 5681 | 32.8% | -4.27 | -5.8% | +35.3% | -25.8% |
| relvol150 | 656 | 32.6% | -6.42 | -6.0% | +34.5% | -25.6% |
| relvol200 | 161 | 30.4% | -10.39 | -6.9% | +36.3% | -25.8% |
| delta20_40 | 3059 | 30.8% | -3.76 | -8.0% | +38.5% | -28.7% |

No variant has a positive average after costs, and none passed the walk-forward out of sample.

## S17 — monthly index put-writing, 2012–2026 (the one pass, under the A7 carry-lane rule)

One trade a monthly expiration, opened the session after the prior expiration, held to settlement.
Annual return is on the cash that secures the put (on the spread's width for the spread; the spread rows
are sized all-in on width, which is why they ran to −100%). Buy and hold over the same cycles:
QQQ 18.9% a year (max drawdown −32.1%), SPY 13.6% (−31.4%).

| Configuration | Trades | Win rate | Avg $ / trade | Avg % of premium | Avg win % | Avg loss % | Annual | Max DD | Beta | Alpha / cycle [95% CI] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| QQQ atm_put | 167 | 80.2% | +198.81 | +35.3% | +95.7% | -210.1% | +8.0% | -23.7% | 0.49 | -0.09% [-0.44, +0.36] |
| QQQ put_30d | 167 | 85.6% | +151.44 | +40.1% | +96.9% | -298.3% | +5.8% | -22.5% | 0.34 | -0.05% [-0.45, +0.44] |
| QQQ put_15d | 167 | 93.4% | +89.16 | +48.8% | +98.1% | -650.1% | +3.4% | -19.6% | 0.19 | -0.01% [-0.46, +0.39] |
| QQQ put_spread_30_15 | 167 | 83.8% | +55.87 | +27.5% | +95.9% | -327.1% | -37.3% | -100.0% | 3.65 | -1.36% [-5.13, +2.68] |
| QQQ covered_call_30d | 167 | 74.9% | +317.30 | +139.2% (stock included) | +363.4% | -527.9% | +14.0% | -26.1% | 0.71 | +0.05% [-0.21, +0.37] |
| SPY atm_put | 167 | 82.6% | +199.73 | +33.1% | +94.4% | -258.7% | +6.4% | -29.6% | 0.56 | -0.09% [-0.44, +0.39] |
| SPY put_30d | 167 | 85.6% | +131.86 | +35.6% | +98.9% | -341.6% | +4.2% | -28.8% | 0.43 | -0.13% [-0.54, +0.39] |
| SPY put_15d | 167 | 94.6% | +75.87 | +41.2% | +98.3% | -960.7% | +2.2% | -27.4% | 0.29 | -0.14% [-0.61, +0.36] |
| SPY put_spread_30_15 | 166 | 85.5% | +50.78 | +25.9% | +97.3% | -396.3% | -43.3% | -100.0% | 3.92 | -0.71% [-4.74, +3.16] |
| SPY covered_call_30d | 167 | 78.4% | +319.63 | +123.9% (stock included) | +338.1% | -655.5% | +10.5% | -30.8% | 0.75 | +0.02% [-0.20, +0.34] |

What passed: QQQ ATM, 30-delta and 15-delta puts and SPY ATM puts, against their pre-registered rule
(positive mean with a bootstrap lower bound above zero). What it is: the volatility risk premium at
a fraction of the index's beta (0.19–0.56 for the single puts) — alpha is zero inside every interval, and the Bonferroni lower bounds are just
under zero. The high win rates come from selling far out of the money: the 15-delta put wins 93–95% of
months and loses 6.5× (QQQ) to 9.6× (SPY) the credit when it loses, for 2–3% a year on the cash.

## Against the target (70%+ win rate, average trade ≥ +45%)

- No directional or 0DTE configuration reaches 70% or a positive average % of premium (S10's +$0.52
  and S03's +$1.27 a trade are −3.6% and −0.1% of premium, inside noise). The highest 0DTE win rate is
  the S10 short single fade with no stop, 65.1%, at −8.2% a trade.
- QQQ 15-delta put-writing meets both numbers (93.4%, +48.8% of the credit), and SPY's comes close
  (94.6%, +41.2%). Neither is an edge over holding the index: they returned 3.4% and 2.2% a year against
  18.9% and 13.6% for buy and hold, and the losing months are 6–10 times the credit.

