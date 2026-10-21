# Compass modules 1 and 10: the session clock / regime router and the MOC / power-hour engine

Every number below comes from a script in `research_notes/Compass engine audit/clock_session/` (its `out/` folder holds the
rows and summaries). Conventions: minute t = hour×60 + minute New York; an underlying 1-minute bar stamped t closes at t+1;
a chain NBBO row stamped t is the quote at t; half days (13:00 close) are dropped; a contract is bought at the ask and sold at
the bid, $0.65 a contract each way, no fee when it expires worthless. Fit = 2022-2024, out-of-sample (OOS) = 2025-2026,
context = 2017-2021 (SPY, IWM; the vendor's SPY/IWM minute files before 2017-01-03 are empty) or 2012-2021 (QQQ). "95% CI" is a
2,000-draw bootstrap that resamples sessions; "wo5" is the mean without the best 5 sessions. Same-day chains: SPY/QQQ 980
sessions 2022-11-11 → 2026-10-09, IWM 621 from 2024-04-19, SPXW 1,106 from 2022-05-13. Nothing was called from any API.

Scripts: `common.py` (helpers), `t1_windows.py` + `t1b_eff_norm.py` (window biases), `t2_or_rule.py` (10:00 inside-OR rule),
`t3_charm_gex.py` (charm × GEX sign), `t4_settlement.py` (15:58 flat vs settlement), `t5a_moc_features.py` + `t5b_moc_test.py`
(MOC normalization, prediction and the power-hour rule), `t45_extras.py` (the moneyness, worthless-share, magnitude-quintile
and book-sign tables).

Short literature pass (context only, not a deliverable): the first half-hour's return predicts the last half-hour's on the S&P
500 ETF 1993-2013 ([Gao, Han, Li, Zhou 2018, JFE](https://profiles.wustl.edu/en/publications/market-intraday-momentum/)); the
rest-of-day return predicts the last 30 minutes across 60+ futures 1974-2020 and the authors attribute it to gamma-hedging
demand ([Baltussen, Da, Lammers, Martens 2021, JFE](https://www3.nd.edu/~zda/intramom.pdf)); retail 0DTE buyers on SPX lost on
average ([Beckmeyer, Branger, Gayda 2023](https://cxoadvisory.com/individual-investing/retail-0dte-option-trader-performance));
closing-auction imbalance feeds carry short-horizon information but NYSE auction moves reverse more than Nasdaq's
([Management Science, "Vestigial Tails?"](https://pubsonline.informs.org/doi/fpi/10.1287/mnsc.2023.00884)). These are about
the UNDERLYING's last-half-hour drift; none of them says that buying a same-day option into it pays after the spread.

## 1. The nine session windows: chase / fade / pin / neutral and "reversal-prone"

**What the spec says.** 0-570 pre-market (neutral, charm ×0.0); 570-595 opening drive (chase, ×1.0); 595-635 morning
reversal (fade, ×1.1, reversal-prone); 635-720 mid-morning (pin, ×1.25); 720-795 lunch (neutral, ×1.5; block new long 0DTE
scalps unless fading to the gross pin in positive gamma); 795-825 pre-power (neutral, ×1.75, reversal-prone); 825-900 dealer
hour (chase, ×2.4); 900-930 power hour (chase, ×3.0); 930-960 settlement (pin, ×3.5, reversal-prone); 960+ after hours.

**The test** (`t1_windows.py`, `t1b_eff_norm.py`; rows in `out/t1_window_rows.parquet`, summaries `out/t1_window_summary.csv`,
`out/t1b_eff_norm.csv`). SPY, QQQ, IWM 1-minute bars, every full session: fit 2,218 window-sessions per window (SPY 739, QQQ
744, IWM 735), OOS 1,309 (SPY 435-439, QQQ 436-439, IWM 428-437), context 4,777 (SPY 1,232, QQQ 2,317, IWM 1,228). Pre-market
and after-hours are not in the data (one bar at 16:00) — untestable here. Four measures per window, pooled across the three
names: **cont** = share of sessions where the window's first third and its remainder move the same way (null 0.5); **ac5** =
lag-1 autocorrelation of non-overlapping 5-minute log returns inside the window; **eff×√n** = |net move| / Σ|1-minute moves|
scaled by the window's bar count so a random walk reads 1.0 (above 1 trends, below 1 pins / reverts); **revprev** = share of
sessions where the window's net move has the opposite sign of the previous window's (null 0.5). Labels were fixed before
reading: chase if cont's CI sits above 0.5 and ac5 > 0; fade if the CI sits below 0.5 and ac5 < 0; else neutral.

**The numbers** (ALL three names; the per-name rows are in the csv and agree in sign):

| window | spec | cont fit | cont OOS | ac5 fit | ac5 OOS | eff×√n fit | eff×√n OOS | revprev fit | revprev OOS | label fit → OOS |
|---|---|---|---|---|---|---|---|---|---|---|
| 570-595 opening drive | chase | 0.508 [0.484, 0.533] | 0.499 [0.466, 0.530] | +0.002 | +0.043 [−0.006, +0.090] | **1.137 [1.094, 1.183]** | **1.133 [1.073, 1.196]** | — | — | neutral → neutral |
| 595-635 morning reversal | fade, rev | 0.517 [0.490, 0.546] | 0.527 [0.492, 0.562] | −0.014 | +0.007 | 1.063 [1.014, 1.113] | 1.056 [0.995, 1.119] | 0.480 [0.456, 0.507] | 0.481 [0.446, 0.516] | neutral → neutral |
| 635-720 mid-morning | pin | 0.486 | 0.522 | −0.017 | −0.027 | 0.993 [0.946, 1.040] | 1.017 [0.955, 1.082] | 0.473 | 0.477 | neutral → neutral |
| 720-795 lunch | neutral | 0.512 | 0.488 | +0.001 | −0.049 [−0.100, +0.002] | 0.997 | 0.972 [0.911, 1.029] | 0.506 | 0.503 | neutral → neutral |
| 795-825 pre-power | neutral, rev | 0.514 | 0.483 | +0.019 | +0.166 [+0.020, +0.230] | 1.038 | 1.005 | 0.495 | 0.504 | neutral → neutral |
| 825-900 dealer hour | chase | 0.503 | 0.468 [0.430, 0.506] | −0.021 | −0.022 | 1.006 | **0.940 [0.882, 0.999]** | 0.452 [0.423, 0.482] | 0.463 | neutral → neutral (QQQ reads fade OOS: cont 0.418 [0.372, 0.462]) |
| 900-930 power hour | chase | 0.490 [0.461, 0.520] | **0.562 [0.524, 0.598]** | +0.003 | +0.021 | **0.942 [0.898, 0.988]** | 1.012 | 0.471 | 0.510 | neutral → chase (OOS only; all three names 0.55-0.58) |
| 930-960 settlement | pin, rev | 0.518 | 0.494 | −0.014 | +0.054 [−0.000, +0.102] | 1.030 | 1.065 [1.000, 1.130] | 0.507 | 0.496 | neutral → neutral |

Context 2012/2017-2021 (4,700 window-sessions): every cont within 0.486-0.509, the dealer hour and power hour ac5 slightly
negative (−0.043 [−0.066, −0.019], −0.050 [−0.100, −0.003]), opening drive ac5 +0.044 [+0.009, +0.079].

Opening-range breakouts that START in a window (first 1-minute close beyond the 09:30-09:59 range; this count leaves out
breakouts in 600-634 because that window begins before 10:00; test 2 covers every breakout with real quotes): held to 15:58 in
55.3% [49.6, 60.6] of 398 fit cases and 54.7% [47.8, 61.1] of 254 OOS cases, with a mean move from the breakout close to 15:58 of
+1.0 bp [−8.3, +9.8] fit and +5.8 bp [−6.4, +19.4] OOS; in context 48.8% [45.4, 52.0] and −8.1 bp [−15.1, −2.1].

**Verdict.** The chase / fade / pin table does not hold. On 2022-2024 every window reads neutral by the pre-registered rule;
on 2025-2026 only the power hour reads chase (cont 0.562, CI above 0.5), and it was 0.490 on 2022-2024 and 0.486 in context,
so it is not a stable property of the clock. The dealer hour (spec: chase) reads mildly mean-reverting out of sample (eff×√n
0.940, QQQ cont 0.418) and in context (ac5 −0.043). "Reversal-prone" is not supported for any of the three windows: revprev's CI
contains 0.5 everywhere (the morning-reversal window's 0.480 is, if anything, continuation of the opening drive). The one
robust feature is that the OPENING DRIVE trends more than a random walk (eff×√n 1.14 in both periods and in context, and the
only positive ac5 in context) — but its first third does not predict its remainder (cont 0.50), so it is not usable as a
"chase" entry inside the window. The pin claims (635-720, 930-960) are not visible on the underlying: eff×√n is 0.99-1.07, i.e.
a random walk. The charm multipliers (1.0 → 3.5) are a monotone function of the clock with no window-level behaviour behind
them; see test 3 for what they do to charm_pressure.

**Replacement table (what the data supports):**

| window | bias | reversal-prone | note |
|---|---|---|---|
| 570-595 | neutral (trend-shaped: eff×√n 1.14) | no | no entry rule follows from it; the first third does not predict the rest |
| 595-635 | neutral | no | continuation share 0.52-0.53, not fade |
| 635-720 | neutral | no | not pin: random-walk efficiency |
| 720-795 | neutral | no | as the spec says; the "block unless fading to the gross pin" condition is untestable without strike-level OI (blocker) |
| 795-825 | neutral | no | revprev 0.50 |
| 825-900 | neutral, lean mean-reverting (OOS and context) | no | never chase |
| 900-930 | neutral | no | chase only in 2025-2026; keep as a boolean "last-half-hour" flag for the hedging-demand effect, not a bias |
| 930-960 | neutral | no | not pin on the underlying; see test 4 for what the last two minutes do to a contract |

Every bias becomes a boolean gate at most (window membership), with no direction attached. The literature's "last 30 minutes
continue the day" (Baltussen et al.) is not in these three names at 1-minute resolution for 2022-2024 by any of the four
measures; it appears in 2025-2026 only.

## 2. The 10:00 inside-opening-range rule

**What the spec says.** ORH/ORL from 570 ≤ t ≤ 599. At t = 600, if spot is strictly inside [ORL, ORH], block 0DTE breakout
trades and wait for a boundary sweep.

**First finding — the condition is vacuous as written.** The 10:00 spot is the close of the 09:59 bar, which is itself one of
the thirty bars that define ORH/ORL, so it is inside the range by construction unless it is the exact extreme. Measured on the
chain sessions: SPY 99.6% (fit) / 99.7% (OOS) of sessions are "inside", QQQ 99.7% / 99.4%, IWM 99.8% / 99.2%; SPXW (index prints
at 600 against the 570-599 prints) 93.4% / 91.4%. The rule therefore blocks the first breakout on essentially every session and
the question becomes: first breakout vs sweep-and-return vs post-sweep breakout.

**The test** (`t2_or_rule.py`; rows `out/t2_rows.parquet`, summary `out/t2_summary.csv`). Real same-day quotes, nearest strictly
out-of-the-money strike against the signal bar's close, bought at the ask one minute after the signal bar (the bar closes
then), signals up to 15:40. (i) first breakout: first close above ORH → call, below ORL → put; (ii) sweep-and-return: first bar
whose high exceeds ORH but closes at or below it → put (mirror → call); (iii) post-sweep breakout: the first close beyond a
boundary that had already been swept-and-returned. Two ways out: step 4's 50% trailing stop on the bid, and hold to the
15:58 bid. Fees $0.65 each way. SPXW: SPX index prints (one price a minute; a sweep is a print beyond the boundary followed by
a print back inside).

**The numbers** — $ per contract after fees (mean, 95% CI by session, without the best 5 days), and % of premium paid:

| name | way in | way out | fit n | fit $ | fit % | OOS n | OOS $ | OOS CI | OOS wo5 | OOS % |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | (i) breakout | trail 50% | 522 | +1.8 | +1.6 | 435 | −4.1 | [−17.1, +10.6] | −14.9 | +1.8 |
| SPY | (i) breakout | hold 15:58 | 522 | −5.1 | +0.8 | 435 | −3.1 | [−25.5, +23.0] | −20.9 | −1.0 |
| SPY | (ii) sweep-and-return | trail 50% | 502 | +0.3 | +2.2 | 413 | −4.1 | [−19.6, +13.6] | −17.5 | −5.2 |
| SPY | (ii) sweep-and-return | hold 15:58 | 502 | −11.0 | −12.3 | 413 | −18.4 | [−40.0, +4.6] | −35.1 | −15.6 [−29.9, −0.8] |
| SPY | (iii) post-sweep breakout | trail 50% | 498 | +4.4 | +7.1 | 410 | −6.1 | [−18.3, +7.9] | −16.8 | −0.3 |
| SPY | (iii) post-sweep breakout | hold 15:58 | 498 | +0.0 | +8.5 | 410 | +3.2 | [−21.5, +31.2] | −16.3 | +2.4 |
| QQQ | (i) | trail 50% | 520 | −0.2 | +1.1 | 429 | −8.5 | [−24.8, +9.8] | −22.8 | −1.9 |
| QQQ | (ii) | hold 15:58 | 488 | −22.7 [−35.8, −8.1] | −21.5 | 404 | −26.3 | [−50.4, −0.7] | −45.4 | −17.3 [−31.3, −4.0] |
| QQQ | (iii) | trail 50% | 478 | −5.5 | −5.7 | 398 | −9.8 | [−23.2, +5.2] | −21.8 | −5.5 |
| IWM | (i) | trail 50% | 172 | −6.3 | −15.2 | 429 | −2.8 | [−8.8, +4.0] | −8.0 | −8.5 |
| IWM | (ii) | trail 50% | 157 | +0.2 | +0.6 | 406 | −5.7 | [−11.4, +0.9] | −10.4 | −11.3 [−20.4, −1.1] |
| IWM | (iii) | trail 50% | 156 | −8.7 | −22.2 | 399 | −5.4 | [−10.1, +0.0] | −9.3 | −10.0 |
| SPXW | (i) | trail 50% | 553 | +10.3 | +0.1 | 352 | −123.7 | [−247.3, +2.1] | −217.4 | −1.9 |
| SPXW | (i) | hold 15:58 | 553 | +33.6 | +6.6 | 352 | +17.6 | [−255.0, +336.4] | −198.4 | +2.3 |
| SPXW | (ii) | trail 50% | 497 | −57.8 | −2.2 | 314 | +50.9 | [−111.3, +224.6] | −80.2 | +4.5 |
| SPXW | (ii) | hold 15:58 | 497 | −134.8 | −11.4 | 314 | −80.3 | [−313.4, +167.8] | −220.9 | −3.2 |
| SPXW | (iii) | trail 50% | 490 | +62.6 | +8.6 | 309 | −13.9 | [−157.8, +150.5] | −138.2 | +2.4 |
| SPXW | (iii) | hold 15:58 | 490 | −11.2 | +4.2 | 309 | +10.7 | [−216.5, +259.9] | −139.5 | +3.3 |
| ALL four | (i) | trail 50% | 1,767 | +3.1 | −0.6 | 1,645 | −30.5 | [−60.5, +2.7] | −54.3 | −2.6 |
| ALL four | (ii) | trail 50% | 1,644 | −20.5 | −3.0 | 1,537 | +5.9 | [−32.9, +50.1] | −25.3 | −4.9 |
| ALL four | (ii) | hold 15:58 | 1,644 | −52.0 | −14.9 [−26.8, −1.7] | 1,537 | −30.0 | [−88.7, +29.9] | −62.6 | −12.3 [−23.5, −0.7] |
| ALL four | (iii) | trail 50% | 1,622 | +17.8 | +1.0 | 1,516 | −8.5 | [−41.2, +30.3] | −37.2 | −3.6 |
| ALL four | (iii) | hold 15:58 | 1,622 | −7.9 | −1.4 | 1,516 | −2.5 | [−58.1, +54.4] | −38.3 | −4.3 |

Median entry 10:08-10:09 for (i) and (ii), 10:19-10:28 for (iii). Win rates 18-35% everywhere. Every "without the best 5
days" figure is negative in both periods for every name and way in. Sessions already outside the range at 10:00 (SPXW: 108 fit,
92 OOS; the ETFs: 1-10) give nothing usable either (SPXW (i) hold: −159 fit, −58 OOS).

**Verdict: not supported; the block adds nothing.** None of the three ways in has a positive friction-adjusted EV whose CI
excludes zero out of sample; the only CI that excludes zero is the sweep-and-return FADE held to the close, and it is negative
(−12.3% of premium [−23.5, −0.7] OOS, −14.9% fit). Waiting for the sweep then taking the breakout (iii) is not better than the
first breakout (i) out of sample (−8.5 vs −30.5 $ pooled, CIs overlap by far; both negative without the best 5 days). The
counterfactual on the underlying (test 1's breakout rows: held to 15:58 in 55% of cases, +1 to +6 bp mean, CIs through zero)
says the price path after a breakout carries no directional edge to pay the option spread. **Replacement rule:** none — drop
the inside-OR check (it is always true) and treat an opening-range breakout as a boolean event flag with no EV claim; if a
breakout trade is kept for other reasons, the trailing stop loses less than holding on every name but SPXW, as step 4 found.

## 4. The 15:58 flat rule vs riding to settlement

**What the spec says.** SPY/IWM 0DTE force flat at t ≥ 958; cash-settled SPX/RUT 0DTE: if ITM and delta-aligned at t = 958,
ride to the 16:00 settlement; longer horizons exempt, EOD structural stops evaluated at t = 955.

**The test** (`t4_settlement.py`; rows `out/t4_rows.parquet`, summary `out/t4_summary.csv`). Every same-day contract in the
money at 15:58 (spot = the close of the bar stamped 957, i.e. the price at 15:58; SPX: the 15:58 print) with a 15:58 bid > 0 and
intrinsic ≤ 1% of spot. ride_edge ($ per contract) = (intrinsic at the close − 15:58 bid) × 100 + $0.65 (the sale fee saved; no
fee assumed on exercise / cash settlement). Closing spot = the 16:00 bar's close where printed, else the 15:59 bar's close;
SPX = the 16:00 print (the official SPXW settlement is the SPX close from constituents' closing prints, which the 16:00 print
approximates — a residual caveat). "Nearest ITM" = the first in-the-money strike on each side, the contract a near-the-money
0DTE holder actually has. "Delta-aligned" = the 15:00 → 15:58 move has the contract's direction.

**The numbers** (ride_edge, $ per contract; positive = riding beat selling at 15:58):

| name | subset | fit n | fit mean [CI] | fit median | OOS n | OOS mean [CI] | OOS median | OOS p5 / p95 | share riding loses | OOS wo5 |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | nearest ITM | 1,060 | −7.4 [−8.8, −6.1] | −7.4 | 882 | −14.8 [−17.1, −12.6] | −15.4 | −88 / +55 | 66% | −15.6 |
| SPY | nearest, delta-aligned | 527 | −7.6 [−10.5, −4.7] | −9.4 | 438 | −15.7 [−19.8, −11.9] | −15.4 | −85 / +51 | 68% | −17.0 |
| SPY | nearest, not aligned | 533 | −7.2 [−10.1, −4.3] | −5.4 | 444 | −13.9 [−18.2, −9.7] | −13.9 | −93 / +56 | 64% | −15.9 |
| SPY | all ITM ≤ 1% | 5,121 | +6.2 [+5.3, +7.0] | +5.7 | 5,867 | +1.6 [+0.6, +2.5] | +1.7 | −70 / +73 | 49% | +1.2 |
| QQQ | nearest ITM | 1,060 | −10.0 [−12.0, −8.1] | −8.9 | 882 | −21.5 [−24.6, −18.7] | −21.1 | −103 / +48 | 68% | −22.4 |
| QQQ | nearest, delta-aligned | 530 | −10.4 [−13.6, −7.4] | −9.4 | 441 | −21.6 [−25.8, −17.2] | −22.4 | −95 / +45 | 70% | −22.9 |
| IWM | nearest ITM | 348 | +0.4 [−0.8, +1.3] | −0.4 | 882 | −0.9 [−1.5, −0.4] | −0.4 | −30 / +27 | 52% | −1.0 |
| IWM | nearest, delta-aligned | 174 | −2.8 [−5.2, −0.3] | −2.9 | 441 | −2.2 [−3.9, −0.7] | −2.4 | −28 / +26 | 54% | −2.7 |
| SPXW | nearest ITM | 1,324 | +21.2 [+14.5, +27.7] | −27.9 | 888 | +16.3 [+5.0, +27.5] | −41.9 | −389 / +585 | 56% | +10.1 |
| SPXW | nearest, delta-aligned | 656 | +27.3 [+6.0, +50.2] | −33.9 | 441 | +14.9 [−14.1, +43.3] | −38.4 | −390 / +581 | 56% | +2.2 |
| SPXW | nearest, not aligned | 668 | +15.2 [−3.4, +34.3] | −17.9 | 447 | +17.6 [−11.1, +48.8] | −54.4 | −389 / +595 | 56% | +3.0 |
| SPXW | all ITM ≤ 1% | 12,241 | +64.7 [+60.5, +68.6] | +59.7 | 11,824 | +52.8 [+50.8, +54.8] | +51.7 | −590 / +707 | 45% | +51.6 |

By year, SPY nearest ITM: 2022 −7.1, 2023 −5.3, 2024 −9.6, 2025 −14.8, 2026 −14.9; QQQ −4.1, −6.6, −14.0, −21.6, −21.5; SPXW
+33.3, +12.0, +22.6, +17.1, +15.2 (aligned: +75.3, +20.8, +3.1, +19.1, +9.6).

**Reading.** On SPY and QQQ the 15:58 bid of the nearest in-the-money contract stands ABOVE its eventual intrinsic by
$0.07-0.22 on average (it still carries two minutes of time value; the bid exceeds the final intrinsic on 60-68% of SPY/QQQ
contracts, and the nearest ITM contract ends worthless on 11-18% of SPY/QQQ sessions, 23-26% on SPXW), so riding loses $7-22 a contract with CIs well clear of zero in both periods and in every year, and the loss has
grown. On SPXW the nearest ITM contract's 15:58 bid sits BELOW the eventual intrinsic on average (+$16-21 a contract, CI
above zero in both periods) but the median ride is −$28 to −$42: riding loses on 55-56% of contracts and pays through the tail
(p95 +$585). "Delta-aligned" separates nothing (aligned +14.9 [−14.1, +43.3] vs not aligned +17.6 [−11.1, +48.8] OOS). The "all
ITM ≤ 1%" rows are dominated by deeper contracts whose wide 15:58 markets sit below parity; they say that a holder of a
deeper ITM contract should not hit the 15:58 bid on any name, but that is a quote-quality effect, not a settlement rule.

**Verdict.** SPY / QQQ / IWM: **keep the flat rule** (selling at the 15:58 bid beats the close's intrinsic by $7-22 a contract
on SPY/QQQ, $1-2 on IWM; robust by year and without the best 5 days). SPXW: **change the rule** — drop "delta-aligned" (it has
no effect); riding the nearest ITM SPXW contract has a positive mean (+$16 OOS, CI [+5, +28]) but a negative median and a
−$390 5th percentile, so it is a variance trade, not an edge: a boolean "may ride" gate for SPXW is defensible, a "should ride"
rule is not. A holder of a DEEPER ITM contract should not sell at the 15:58 bid on any name — by moneyness (`out/t4_by_moneyness.csv`,
all years): intrinsic under 0.1% of spot, riding loses $6-20 a contract on the ETFs (66-71% of contracts); 0.1-0.2%, −$1 to −$11;
0.2-0.5%, +$1 to +$4; 0.5-1%, +$7 to +$14 (riding wins 60-65%). On SPXW every bucket above 0.1% rides positive on average and
median (+$37 to +$73), so the flat rule there is only a question for the first strike. Residual caveat: the SPXW settlement is approximated by the 16:00
print; the official settlement value is not on disk (blocker for the last ~$0.5 of precision).

## 3. charm_pressure × GEX_book sign in the dealer hour / power hour (the owner's task (a))

**What the spec says.** charm_pressure = raw_charm × the window multiplier (825-900 ×2.4, 900-930 ×3.0, 930-960 ×3.5);
between t = 795 and 958, does high charm_pressure (> 2.4×) raise the win rate of trend-following power-hour trades against
mean-reverting pin trades, and how does it interact with the sign of the dealer gamma book?

**Definitions used** (`t3_charm_gex.py`; rows `out/t3_rows.parquet`, summary `out/t3_summary.csv`, book `out/t3_book.csv`).
- Book: Unusual Whales `greek-exposure` (daily, book level, UW's sign: call gamma > 0, put gamma < 0), the row dated the
  session BEFORE the trade (what is known at 15:00). gex_sign = sign(call_gamma + put_gamma); charm_net = call_charm +
  put_charm. Rows exist 2025-10-15 → 2026-10-13 only (250 a name), so the book splits cover 2025-10-16 → 2026-10-09: SPY
  244 sessions, QQQ 245, IWM 242, SPXW 245. **One year of book data cannot support a train/check split**; every book split
  below is read once, on the same year, and must be treated as descriptive.
- "raw_charm × multiplier" has no unit a threshold can be set on, so charm_pressure is read as |charm_net| ÷ the median of
  |charm_net| over the 20 book rows before it, × 3.0 (the multiplier at the 15:00 entry). "> 2.4×" then means |charm| above
  0.8 × its trailing median, which is true on 57-71% of sessions (median charm_pressure 2.95-3.14 by name) — i.e. the
  spec's threshold, applied at 15:00, only removes sessions whose charm is unusually small. Terciles of charm_pressure and
  the raw charm sign are reported beside it.
- Trades (nearest OTM same-day strike against the 15:00 spot, bought at the ask of the 15:00 row, sold at the 15:58 bid or
  on a 50% trailing stop; $0.65 each way): **trend** = the side of the 14:00 → 15:00 move; **fade** = the other side;
  **pin** = toward the pin proxy = the strike with the most same-day contract volume (calls + puts) in the bars closed by
  15:00, from the per-contract OHLC files (contracts within ±2% of the 09:31 price); skipped when the pin is the spot's strike.
  (Historical open interest by strike is not on disk — blocker for the spec's gross pin.) N without the book: fit 1,887 /
  OOS 1,759 trend trades across the four names (SPY 529/440, QQQ 530/440, IWM 173/438, SPXW 655/441).

**The numbers.** Pooled over the four names, held to 15:58, $ per contract after fees (win rate; % of premium):

| split | trend | fade | pin |
|---|---|---|---|
| 2022-2024, no book (n≈1,887) | −27.7 [−48.5, −4.9] (24%; −17.7%) | −32.2 [−51.8, −11.1] (22%; −23.8%) | −38.6 [−57.9, −19.2] (24%; −21.9%) |
| 2025-2026, no book (n≈1,759) | −28.6 [−53.2, −2.9] (25%; −19.5%) | +5.6 [−24.0, +39.7] (28%; −16.7% [−27, −6]) | −0.7 [−28.2, +30.8] (28%; −14.2% [−25, −3]) |
| book year, all (n≈976) | −22.9 [−52.6, +13.1] (25%) | +1.9 [−33.5, +46.9] (28%) | −7.4 [−40.8, +36.1] (27%) |
| book year, GEX > 0 (n=360) | −25.5 [−80.5, +33.7] (27%) | −42.4 [−89.0, +11.5] (28%) | −50.0 [−94.7, −1.1] (29%) |
| book year, GEX < 0 (n=614) | −21.5 [−54.7, +21.9] (24%) | +28.0 [−19.8, +85.2] (29%; wo5 −19.3) | +17.8 [−27.5, +75.9] (27%; wo5 −28.5) |
| book year, charm_pressure > 2.4 (n=557) | −21.1 [−63.1, +28.1] (23%) | +15.0 [−38.3, +87.5] (30%; wo5 −39.1) | +5.2 [−48.6, +75.7] (27%; wo5 −48.1) |
| book year, charm_pressure ≤ 2.4 (n=359) | −29.4 [−59.3, +1.0] (26%) | −0.7 [−35.7, +38.4] (28%) | −20.3 [−50.7, +13.8] (27%) |

With the 50% trailing stop the same pattern (trend OOS −12.5 [−28.9, +5.2]; fade GEX<0 +36.4 [−5.0, +92.5], wo5 −8.3; pin
GEX<0 +28.1 [−12.6, +85.9], wo5 −16.3). Per name, the largest book-year cells are SPXW fade with GEX < 0 (n=65, trail
+$300 [−14, +737], wo5 −48), QQQ fade/pin in the top charm tercile (n=76, +$22-27, CIs [−14, +79], wo5 −12 to −17), SPXW
trend in the top charm tercile (n=76, +$133 [−113, +430], wo5 −116); every one of them has a CI through zero and is negative
without its best 5 days. Trend-following by name, book year, charm_pressure > 2.4 vs ≤ 2.4, win rate: SPY 20% vs 29%, QQQ 26% vs
30%, IWM 17% vs 23%, SPXW 27% vs 22%; GEX > 0 vs < 0: SPY 25% / 24%, QQQ 32% / 27%, IWM 29% / 20%, SPXW 26% / 28%.

A note on the book itself: in UW's book-level sign the net gamma is positive on 74% of SPX sessions but on only 32% of SPY,
36% of QQQ and 7% of IWM sessions, and net charm is positive on 76% of SPY sessions and 21% of SPX's — two products on the
same index disagree on the sign most days, so a GEX_book sign from this feed is not a stable regime label across names.

**Verdict.** (1) No: high charm_pressure does not raise the trend-follower's win rate — pooled it is 23% above 2.4× against
26% below, and on three of four names it is lower above the threshold. (2) Every power-hour long-premium trade — trend,
fade or pin — loses on 2022-2024 with CIs clear of zero (−18% to −24% of premium) and on 2025-2026 trend still loses
(−19.5% [−31.5, −6.9]); the fade and pin rows that turn to +$2-28 in the book year or under GEX < 0 all have CIs through
zero and go negative without their best 5 days, so nothing survives the stress test. (3) The GEX sign × charm_pressure
interaction cannot be tested as a rule: one year of book data, four cells of 95-236 trades each, and the one cell that
looks best (fade/pin under GEX < 0 and high charm) is the kind of 2×2 read that a second year would be needed to confirm.
**Replacement:** keep charm_pressure and GEX sign as DISPLAY fields, not gates; the window multiplier (1.0 → 3.5) adds no
information beyond the clock and should not scale anything that sets a trade. Blocker for a causal test: book-level dealer
greeks before 2025-10-15 and strike-level OI history (the gross pin) are not on disk; UW's `greek-exposure` history endpoint
and a strike-level OI archive (UW `/option-contracts` by date or OCC daily OI) would be needed, and even then the sign
convention (naive dealer-short-customer) is an assumption, not an observation.

## 5. Module 10, the MOC score: the deterministic normalization (the owner's task (b)) and whether it predicts

**What the spec says.** moc_score from five magnitude_* inputs with weights 1.00 (truncated in the owner's copy; read as
closing-cross/volume imbalance, late-day range extension, late-day volume vs its time-of-day norm, sweep premium imbalance,
the move since 15:00). Power-hour rule (900 ≤ t < 960): close above the pre-15:00 session high + call sweep premium leading +
moc_score > 0 → buy a call; mirror for puts.

**Inputs on disk** (`t5a_moc_features.py` → `out/t5_features.parquet`; 36,630 session-checkpoints, SPY/QQQ 970 sessions each,
IWM 615, SPXW 1,106): late-day underlying volume (SPXW: SPY's volume, the index has none); the 15:00 → t range; the move
since 15:00; a sweep-premium proxy from the per-contract OHLC bars — premium = volume × close × 100, bought when the bar's
close is above the NBBO mid at the bar's end, sold when below (step 5's rule), summed by side and right over 15:00 → t;
sweep_imb = (call_bought − put_bought) / (call_bought + put_bought). **Not on disk: the closing-cross / auction imbalance
feed** (NYSE/Nasdaq imbalance messages from 15:50) — blocker; the formula below is written for four inputs and takes a fifth
term with weight 1.00 the day that feed exists.

**The formula, exactly** (`t5b_moc_test.py`; scores `out/t5_scores.parquet`). For a name, an input x and a checkpoint minute
t ∈ {905, 910, …, 950}: mean₂₀(x, t) and sd₂₀(x, t) are the mean and standard deviation of x at that same minute over the 20
sessions strictly before the day (at least 15 present, else no score that day).
```
x_vol   = ln(1 + volume_{15:00→t})          x_range = ln(1e-6 + (high − low)_{15:00→t} / close_{14:59})
x_move  = (close_{t−1} − close_{14:59}) / close_{14:59}     x_sweep = sweep_imb_{15:00→t}
z_i     = clip((x_i − mean₂₀(x_i, t)) / sd₂₀(x_i, t), −4, +4)
σ(z)    = 1 / (1 + e^{−z})                   u_i = 2·σ(z_i) − 1 ∈ (−1, 1)
moc_score (signed, every weight 1.00) = u_move + u_sweep + sign(x_move) · (u_vol + u_range)          ∈ (−4, 4)
moc_mag   (the spec's magnitude form)  = [ σ(z_vol) + σ(z_range) + σ(z_|move|) + σ(z_|sweep|) ] / 4     ∈ (0, 1)
```
(|move| and |sweep| are z-scored against their own 20-session minute norms.) Every term is a function of bars and quotes
closed by t and of the 20 prior sessions, so the score is reproducible to the bit from the stored files.

**Does it predict the 15:50 → 16:00 move?** (`out/t5_predictive.csv`; at t = 950, target = the close vs the 15:49 bar's
close; pooled n = 1,836 fit, 1,767 OOS.)

| | fit 2022-24 | OOS 2025-26 |
|---|---|---|
| Spearman ρ, signed moc_score vs the move | +0.069 (p = 0.003) | −0.010 (p = 0.68) |
| sign hit rate, all / |score| > 1 | 52.5% / 55.1% (n 712) | 48.7% / 47.1% (n 643) |
| mean move when score > 0 / < 0 (bp) | +1.7 / −0.7 | −0.4 / +0.4 |
| move in the score's top / bottom quintile (bp) | +2.1 / −2.6 | +0.1 / +2.5 |
| mean of sign(score) × move (bp) | +1.2 [+0.0, +2.3] | −0.4 [−1.8, +1.0] |
| Spearman ρ, moc_mag vs |move| | **+0.213** (p < 1e-15) | **+0.157** (p < 1e-10) |
| |move| by moc_mag quintile, bottom → top (bp, mean) | 9.5, 10.4, 10.8, 13.9, 17.3 | 10.0, 9.8, 10.9, 11.9, 17.7 |

By name the signed score's ρ is +0.07 / +0.00 (SPY), +0.09 / +0.06 (QQQ), +0.00 / −0.10 (IWM), +0.08 / −0.00 (SPXW) fit /
OOS; the magnitude ρ is +0.14 to +0.25 on every name in both periods (`out/t5_mag_quintiles.csv`). Components: z_vol and
z_range each carry ρ ≈ +0.20-0.25 with |move| in both periods; z_move and z_sweep carry +0.03-0.05 with the signed move in
fit and ~0 OOS.

**The power-hour rule with real 0DTE quotes** (`out/t5_rule_summary.csv`; first checkpoint 15:05-15:50 where the close is
beyond the pre-15:00 high/low, nearest OTM same-day contract, out at the 15:58 bid or on the 50% trailing stop; pooled
four names):

| variant | fit n | fit $ (hold) | fit $ (trail) | OOS n | OOS $ (hold) [CI] | OOS $ (trail) [CI] | OOS wo5 (hold) | OOS % of premium (hold) |
|---|---|---|---|---|---|---|---|---|
| breakout alone | 605 | −25.2 | −26.1 [−45.5, −4.4] | 482 | −16.4 [−59.0, +28.3] | −9.0 [−36.3, +21.8] | −52.6 | −21.8% [−40, −1] |
| breakout + sweep leading | 567 | −26.1 | −28.0 [−48.0, −5.0] | 465 | −14.7 [−57.6, +31.2] | −7.0 [−34.7, +27.7] | −52.1 | −20.3% [−39, −1] |
| breakout + moc_score > 0 | 564 | −25.4 | −29.6 [−50.0, −7.3] | 440 | −17.9 [−61.9, +33.3] | −7.1 [−36.7, +28.6] | −56.5 | −21.0% [−39, +0] |
| breakout + moc_mag > 0.5 | 483 | −21.9 | −30.5 [−53.8, −5.9] | 378 | −25.9 [−76.2, +28.1] | −10.0 [−42.7, +27.2] | −71.5 | −26.1% [−45, −6] |
| full rule (breakout + sweep + score) | 535 | −24.9 | −29.1 [−49.2, −6.9] | 427 | −15.7 [−60.3, +32.6] | −5.2 [−35.1, +30.9] | −55.4 | −19.1% [−38, +1] |

Win rates 17-28%. Per name OOS, the full rule held to 15:58: SPY −$6.7 (n 99), QQQ −$10.8 (n 100), IWM −$6.5 (n 104),
SPXW −$34.6 (n 124; by year 2025 −11, 2026 −63); every name's "without best 5 days" is negative in both periods. Adding the
sweep and score gates to the bare breakout changes the pooled OOS mean by +$0.7 to +$1.5 a contract, inside the noise.

**Verdict.** (b) is answered: the normalization above is fully deterministic and is the one to implement (20-session
same-minute mean/sd → clipped z → logistic → unit weights), with the closing-cross imbalance as the fifth term once a feed
exists. What it predicts: the MAGNITUDE score forecasts the size of the last ten minutes' move (ρ +0.16-0.21 with |move|,
top quintile 17-18 bp against 9-10 bp, in both periods on every name) — the late-day volume and range norms carry it. The
SIGNED score does not forecast the direction out of sample (ρ −0.01, sign hit 48.7%, 47.1% when |score| > 1; the +1.2 bp
of fit became −0.4 bp), and the power-hour rule loses 19-26% of premium a trade out of sample with or without its gates.
**Replacement:** keep the magnitude score as a volatility-of-the-close gauge (a sizing / "expect a move" flag — it is the
one piece of module 10 that holds up), drop the direction claim, and keep the power-hour long-premium rule out of the
engine; a short-premium use of the same magnitude score (selling the close's optionality when moc_mag is low) is the only
direction the data points to and was NOT tested here — it would need the owner's go-ahead as a new hypothesis. Blockers: the
closing-cross imbalance feed; a per-print options tape (the bar-close-vs-mid side rule is a proxy for sweep direction and
carried ρ ≈ 0 OOS).

## Cross-cutting blockers and what would be needed
- Pre-market (0-570) and after-hours (960+) windows: no bars on disk; untestable.
- The lunch rule "block unless fading to the gross pin in positive gamma", the spec's gross pin and the GEX sign before
  2025-10-15: strike-level open-interest history and book-level dealer greeks before that date are not on disk.
- The closing-cross / MOC imbalance input: not on disk; the MOC formula is written to take it as the fifth unit-weight term.
- SPXW settlement: approximated by the 16:00 index print; the official settlement series is not on disk (last ~$0.5).
- The four horizons beyond 0DTE (Weekly, Swing, LEAPS): the clock rules tested here only touch same-day contracts, as the
  spec's module 1/10 rules do; the longer horizons are exempt from the flat rule by the spec and nothing in them was tested.

## Summary table

| rule | verdict | replacement |
|---|---|---|
| nine-window chase / fade / pin / neutral | not supported (every window neutral on 2022-24; only the power hour reads chase in 2025-26 and not before) | all windows neutral; window membership as a boolean flag only; the opening drive is the one trend-shaped window (eff×√n 1.14, both periods) with no usable entry inside it |
| "reversal-prone" 595-635, 795-825, 930-960 | not supported (revprev 0.48-0.51, CIs through 0.5) | drop the flag |
| charm multipliers 1.0 → 3.5 | no window behaviour behind them; charm_pressure > 2.4× does not raise the trend win rate (23% vs 26%) | display only; never a gate or a scale on size |
| 10:00 inside-OR block | vacuous (true on 99.6% of ETF sessions by construction) and the three ways in all lose or sit on zero after fees | drop; opening-range breakout as a boolean event flag with no EV claim |
| 15:58 flat for SPY/IWM (and QQQ) | **keep** (riding the nearest ITM loses $7-22 a contract on SPY/QQQ, $1-2 on IWM; robust by year) | keep; add: a deeper ITM contract (> 0.2% of spot) should not be sold at the 15:58 bid |
| SPXW ride if ITM and delta-aligned | partly: riding the nearest ITM has a positive mean (+$16 OOS, CI [+5, +28]) but a negative median and −$390 p5; delta-aligned adds nothing | "may ride" boolean for SPXW, no delta condition; never a "should ride" |
| MOC normalization | defined (deterministic, above) | implement as written |
| moc_score → direction / power-hour buy | not supported OOS (ρ −0.01, −19% to −26% of premium a trade) | drop the directional use |
| moc_mag → size of the close's move | **supported** (ρ +0.16 to +0.21 both periods, every name) | keep as a magnitude gauge only |
