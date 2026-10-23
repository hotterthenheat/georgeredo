# EMA system — PREVIEW on last week (2026-10-12 → 2026-10-16)

**PREVIEW — 5 sessions, no verdict.** Five full sessions (Mon–Fri), run exactly as written in RULEBOOK_v0.md (commit af32405), on the owner's request "test just on last weeks data so i can see the results fast". Five sessions cannot separate a rule from luck: one large SPXW move can make a whole row. Nothing here is a finding, and nothing is selected from it.

Labels: **OBSERVED** = read off the data (the bars, the NBBO, open interest, volume); **CALCULATED** = arithmetic of observed (P&L, fees, R, bp); **MODELED** = the Black-Scholes delta used to choose the contract. All P&L is CALCULATED from OBSERVED quotes: bought at the ask, sold at the bid, fees each way.

Earlier results to keep in mind: every pre-registered 0DTE long-option rule run on this data has lost after costs (the Compass scanner study stopped at its signal gate, 9e3888e; the EMA ladder preview lost in all 13 versions, cb79c23; the "nearest EMA targets" preview lost in both versions and both months, e9d13c0). This same week was already read by the forward paper-tracker replays of other rules (research_notes/Compass phase 3/forward_2026-10-12_2026-10-21), so it is neither fresh nor held out.

Code: `ema_system.py` (engine), `preview.py` (this report), `test_ema_system.py`, `verify_plain.py`; sha256 (16): `ema_system.py` b30f975989db2de7, `preview.py` 92e552bd6c87c2cd, `test_ema_system.py` 24f739188a075f0d, `verify_plain.py` b817728e0f4cda84. Trade list: `out/trades_full.csv`.

## 0. Read this first

**PREVIEW — 5 sessions, no verdict.**

- **The week fell**: from the 2026-10-09 close to the 2026-10-16 close SPX −1.96%, SPY −1.96%, QQQ −5.51%, IWM −3.04% (OBSERVED). The 15-minute bias put most signals on the put side: 86% of all full-strategy trades are puts. A rule that buys puts in a falling week shows a profit for that reason alone.
- **Every row of the full strategy is net positive this week** (X2: Config A 53 trades, +$3,253, +$61.38 a trade, +17.4% of premium; Config B 49, +$2,145, +$43.78, +12.6%); IWM is the exception, negative in most rows.
- **The random baseline is positive too**: the same count per name, the same minutes and the same put share, entered at random, made +$18.75 a trade on average (Config A's draws; band 5–95% −$36.16 to +$75.86). The full strategy's total sits at the 89th (A) and 80th (B) percentile of the random trials — inside the band, not beyond it.
- **One trade moves a row**: the largest X2 trade is SPXW 2026-10-14 09:53 +$1,427 (A) — 44% of A's X2 total. The session bootstrap intervals (§4) all include zero.
- **The filters did beat the plain baselines this week**: (a) the 1m crossover and (b) alignment alone made less or lost (§5). One week of one direction cannot say whether that holds.
- **Costs were small here** (0DTE near-the-money, |delta| ≈ 0.45, spreads ≈ 1–2% of mid): fees ≈ 0.5–0.6% and half-spreads ≈ 1.5–2% of premium (§7). The EMA ladder previews traded far more (≈2,800 trades in a month) and their best-R/R pick sat far out of the money (median |delta| 0.18); their ATM version still lost (−3.61%), cb79c23.
- Against the record: every pre-registered 0DTE long-option rule on this data lost after costs over months and years. Five positive sessions in a trending week do not move that; they make the rule worth writing down, not trading.

## 1. The full strategy, all four names together

**PREVIEW — 5 sessions, no verdict.** 1 contract (X4: 10). Expectancy % = net ÷ premium paid. MFE / MAE = the best / worst bid during the hold against the entry ask (mean over trades). Hold in minutes.

| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | MFE / MAE (option) | long (calls) | short (puts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Config A · X1 | 57 | 61% | +$134.99 / −$103.27 | +$43.03 | +11.9% | +$2,558 | +$2,452 | 2.08 | 13 / 7 | +25% / −18% | 8 −$491 | 49 +$2,944 |
| Config A · X2 | 53 | 49% | +$232.16 / −$103.07 | +$61.38 | +17.4% | +$3,352 | +$3,253 | 2.17 | 24 / 14 | +45% / −24% | 8 −$571 | 45 +$3,824 |
| Config A · X3 | 48 | 29% | +$560.15 / −$101.33 | +$91.60 | +30.3% | +$4,484 | +$4,397 | 2.28 | 36 / 20 | +89% / −26% | 7 −$529 | 41 +$4,925 |
| Config A · X4 | 48 | 33% | +$3,182.94 / −$920.11 | +$447.58 | +14.8% | +$22,356 | +$21,484 | 1.73 | 36 / 20 | +89% / −26% | 7 −$4,602 | 41 +$26,086 |
| Config B · X1 | 55 | 64% | +$125.30 / −$106.01 | +$41.19 | +11.5% | +$2,367 | +$2,265 | 2.07 | 14 / 7 | +24% / −19% | 7 −$369 | 48 +$2,634 |
| Config B · X2 | 49 | 47% | +$208.98 / −$102.36 | +$43.78 | +12.6% | +$2,236 | +$2,145 | 1.81 | 24 / 12 | +40% / −25% | 7 −$449 | 42 +$2,594 |
| Config B · X3 | 46 | 28% | +$596.57 / −$100.87 | +$96.23 | +31.8% | +$4,510 | +$4,427 | 2.33 | 35 / 18 | +81% / −27% | 6 −$406 | 40 +$4,833 |
| Config B · X4 | 46 | 33% | +$3,352.92 / −$915.35 | +$476.48 | +15.7% | +$22,751 | +$21,918 | 1.77 | 35 / 18 | +81% / −27% | 6 −$3,376 | 40 +$25,294 |

Without SPXW (SPY, QQQ, IWM only — SPXW premiums are ~10× an ETF's, so its dollars dominate):

| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | MFE / MAE (option) | long (calls) | short (puts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Config A · X1 | 34 | 65% | +$52.40 / −$35.12 | +$21.51 | +21.1% | +$778 | +$731 | 2.73 | 19 / 12 | +32% / −23% | 1 −$23 | 33 +$755 |
| Config A · X2 | 31 | 48% | +$105.29 / −$42.19 | +$29.17 | +28.4% | +$947 | +$904 | 2.34 | 33 / 24 | +55% / −29% | 1 −$23 | 30 +$928 |
| Config A · X3 | 30 | 33% | +$109.73 / −$35.47 | +$12.93 | +13.0% | +$429 | +$388 | 1.55 | 41 / 26 | +95% / −28% | 1 −$23 | 29 +$411 |
| Config A · X4 | 30 | 37% | +$802.70 / −$305.85 | +$100.62 | +10.1% | +$3,431 | +$3,019 | 1.52 | 41 / 26 | +95% / −28% | 1 −$234 | 29 +$3,252 |
| Config B · X1 | 33 | 67% | +$51.99 / −$35.65 | +$22.78 | +22.1% | +$797 | +$752 | 2.92 | 19 / 12 | +31% / −23% | 1 −$23 | 32 +$775 |
| Config B · X2 | 29 | 45% | +$111.32 / −$42.25 | +$26.59 | +25.3% | +$811 | +$771 | 2.14 | 32 / 21 | +49% / −30% | 1 −$23 | 28 +$795 |
| Config B · X3 | 29 | 31% | +$112.29 / −$35.77 | +$10.18 | +10.0% | +$335 | +$295 | 1.41 | 39 / 25 | +80% / −29% | 1 −$23 | 28 +$319 |
| Config B · X4 | 29 | 34% | +$819.65 / −$314.17 | +$76.80 | +7.5% | +$2,626 | +$2,227 | 1.37 | 39 / 25 | +80% / −29% | 1 −$234 | 28 +$2,461 |

## 2. By instrument

**PREVIEW — 5 sessions, no verdict.** SPXW: signals on SPX prints, RVOL condition dropped (no volume), VWAP is the time-weighted stand-in.

### Config A

| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | MFE / MAE (option) | long (calls) | short (puts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 · SPXW (no RVOL) | 23 | 57% | +$274.75 / −$185.05 | +$74.84 | +10.1% | +$1,780 | +$1,721 | 1.93 | 5 / 3 | +15% / −12% | 7 −$468 | 16 +$2,189 |
| X1 · SPY | 11 | 91% | +$52.03 / −$29.37 | +$44.63 | +40.1% | +$506 | +$491 | 17.71 | 19 / 12 | +43% / −14% | 0 +$0 | 11 +$491 |
| X1 · QQQ | 14 | 64% | +$61.63 / −$56.97 | +$19.27 | +14.7% | +$289 | +$270 | 1.95 | 24 / 10 | +30% / −26% | 0 +$0 | 14 +$270 |
| X1 · IWM | 9 | 33% | +$25.96 / −$17.87 | −$3.26 | −7.2% | −$17 | −$29 | 0.73 | 13 / 12 | +23% / −29% | 1 −$23 | 8 −$6 |
| X2 · SPXW (no RVOL) | 22 | 50% | +$405.17 / −$191.64 | +$106.77 | +15.1% | +$2,405 | +$2,349 | 2.11 | 11 / 4 | +31% / −17% | 7 −$548 | 15 +$2,897 |
| X2 · SPY | 11 | 55% | +$107.79 / −$45.77 | +$37.99 | +35.9% | +$433 | +$418 | 2.83 | 29 / 24 | +68% / −25% | 0 +$0 | 11 +$418 |
| X2 · QQQ | 12 | 58% | +$118.77 / −$67.77 | +$41.04 | +29.9% | +$509 | +$493 | 2.45 | 41 / 28 | +58% / −31% | 0 +$0 | 12 +$493 |
| X2 · IWM | 8 | 25% | +$50.63 / −$17.87 | −$0.75 | −1.6% | +$5 | −$6 | 0.94 | 28 / 14 | +32% / −31% | 1 −$23 | 7 +$17 |
| X3 · SPXW (no RVOL) | 18 | 22% | +$1,686.20 / −$195.41 | +$222.72 | +34.8% | +$4,055 | +$4,009 | 2.47 | 28 / 12 | +79% / −24% | 6 −$505 | 12 +$4,514 |
| X3 · SPY | 7 | 29% | +$308.13 / −$28.97 | +$67.34 | +65.7% | +$481 | +$471 | 4.25 | 58 / 24 | +151% / −26% | 0 +$0 | 7 +$471 |
| X3 · QQQ | 14 | 36% | +$76.23 / −$50.93 | −$5.52 | −4.2% | −$58 | −$77 | 0.83 | 40 / 28 | +83% / −29% | 0 +$0 | 14 −$77 |
| X3 · IWM | 9 | 33% | +$33.29 / −$17.71 | −$0.71 | −1.6% | +$6 | −$6 | 0.94 | 31 / 17 | +72% / −28% | 1 −$23 | 8 +$17 |
| X4 · SPXW (no RVOL) | 18 | 28% | +$8,419.45 / −$1,817.86 | +$1,025.84 | +16.0% | +$18,925 | +$18,465 | 1.78 | 28 / 12 | +79% / −24% | 6 −$4,368 | 12 +$22,833 |
| X4 · SPY | 7 | 43% | +$1,426.58 / −$221.25 | +$484.96 | +47.3% | +$3,491 | +$3,395 | 4.84 | 58 / 24 | +151% / −26% | 0 +$0 | 7 +$3,395 |
| X4 · QQQ | 14 | 36% | +$727.45 / −$429.31 | −$16.18 | −1.2% | −$34 | −$226 | 0.94 | 40 / 28 | +83% / −29% | 0 +$0 | 14 −$226 |
| X4 · IWM | 9 | 33% | +$304.25 / −$177.08 | −$16.64 | −3.7% | −$26 | −$150 | 0.86 | 31 / 17 | +72% / −28% | 1 −$234 | 8 +$84 |

### Config B

| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | MFE / MAE (option) | long (calls) | short (puts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 · SPXW (no RVOL) | 22 | 59% | +$249.37 / −$192.00 | +$68.81 | +9.3% | +$1,570 | +$1,514 | 1.88 | 5 / 4 | +14% / −14% | 6 −$345 | 16 +$1,859 |
| X1 · SPY | 11 | 100% | +$49.35 / — | +$49.35 | +45.8% | +$558 | +$543 | ∞ | 18 / 12 | +47% / −13% | 0 +$0 | 11 +$543 |
| X1 · QQQ | 14 | 64% | +$61.63 / −$56.97 | +$19.27 | +14.7% | +$289 | +$270 | 1.95 | 24 / 10 | +30% / −26% | 0 +$0 | 14 +$270 |
| X1 · IWM | 8 | 25% | +$23.13 / −$17.87 | −$7.62 | −16.2% | −$50 | −$61 | 0.43 | 13 / 13 | +12% / −31% | 1 −$23 | 7 −$38 |
| X2 · SPXW (no RVOL) | 20 | 50% | +$335.95 / −$198.55 | +$68.70 | +9.8% | +$1,425 | +$1,374 | 1.69 | 12 / 4 | +28% / −18% | 6 −$425 | 14 +$1,799 |
| X2 · SPY | 10 | 50% | +$112.03 / −$45.97 | +$33.03 | +31.3% | +$344 | +$330 | 2.44 | 26 / 14 | +62% / −26% | 0 +$0 | 10 +$330 |
| X2 · QQQ | 12 | 58% | +$118.77 / −$67.77 | +$41.04 | +29.9% | +$509 | +$493 | 2.45 | 41 / 28 | +58% / −31% | 0 +$0 | 12 +$493 |
| X2 · IWM | 7 | 14% | +$55.63 / −$17.87 | −$7.37 | −15.2% | −$42 | −$52 | 0.52 | 24 / 12 | +14% / −34% | 1 −$23 | 6 −$28 |
| X3 · SPXW (no RVOL) | 17 | 24% | +$1,686.20 / −$201.02 | +$243.03 | +37.6% | +$4,175 | +$4,132 | 2.58 | 29 / 12 | +83% / −24% | 5 −$383 | 12 +$4,514 |
| X3 · SPY | 7 | 29% | +$308.13 / −$30.17 | +$66.48 | +64.0% | +$475 | +$465 | 4.08 | 55 / 18 | +143% / −26% | 0 +$0 | 7 +$465 |
| X3 · QQQ | 14 | 36% | +$76.23 / −$50.93 | −$5.52 | −4.2% | −$58 | −$77 | 0.83 | 40 / 28 | +83% / −29% | 0 +$0 | 14 −$77 |
| X3 · IWM | 8 | 25% | +$6.63 / −$17.71 | −$11.62 | −24.7% | −$82 | −$93 | 0.12 | 22 / 14 | +21% / −31% | 1 −$23 | 7 −$70 |
| X4 · SPXW (no RVOL) | 17 | 29% | +$8,419.45 / −$1,867.22 | +$1,158.27 | +17.9% | +$20,125 | +$19,691 | 1.88 | 29 / 12 | +83% / −24% | 5 −$3,143 | 12 +$22,833 |
| X4 · SPY | 7 | 43% | +$1,426.58 / −$260.75 | +$462.39 | +44.5% | +$3,333 | +$3,237 | 4.10 | 55 / 18 | +143% / −26% | 0 +$0 | 7 +$3,237 |
| X4 · QQQ | 14 | 36% | +$727.45 / −$429.31 | −$16.18 | −1.2% | −$34 | −$226 | 0.94 | 40 / 28 | +83% / −29% | 0 +$0 | 14 −$226 |
| X4 · IWM | 8 | 25% | +$139.75 / −$177.08 | −$97.87 | −20.8% | −$673 | −$783 | 0.26 | 22 / 14 | +21% / −31% | 1 −$234 | 7 −$549 |

## 3. Signals without a trade, by reason

**PREVIEW — 5 sessions, no verdict.** A minute whose rule held while no position was open but no contract passed §4 (each such minute counted). Identical across exit variants unless the timing of earlier trades differs.

| config · exit | SPXW | SPY | QQQ | IWM |
|---|---|---|---|---|
| A · X1 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| A · X2 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| A · X3 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| A · X4 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| B · X1 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| B · X2 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| B · X3 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |
| B · X4 | 0 | 0 | 0 | no delta 0.30-0.60: 3 |

## 4. How trades ended, by hour of entry, by day

**PREVIEW — 5 sessions, no verdict.**

| config · exit | stop | +1R | +2R | runner | flat 15:58 |
|---|---|---|---|---|---|
| A · X1 | 22 | 35 | 0 | 0 | 0 |
| A · X2 | 26 | 0 | 26 | 0 | 1 |
| A · X3 | 22 | 0 | 0 | 26 | 0 |
| A · X4 | 22 | 0 | 0 | 26 | 0 |
| B · X1 | 20 | 35 | 0 | 0 | 0 |
| B · X2 | 25 | 0 | 23 | 0 | 1 |
| B · X3 | 22 | 0 | 0 | 24 | 0 |
| B · X4 | 22 | 0 | 0 | 24 | 0 |

By hour of entry (trades · net $):

| config · exit | 9:xx | 10:xx | 11:xx | 12:xx | 13:xx | 14:xx | 15:xx |
|---|---|---|---|---|---|---|---|
| A · X1 | 10 · +$525 | 7 · +$117 | 13 · +$1,149 | 8 · +$85 | 7 · +$730 | 8 · −$108 | 4 · −$47 |
| A · X2 | 9 · +$1,101 | 6 · +$157 | 10 · +$1,039 | 7 · +$434 | 8 · +$1,419 | 7 · −$628 | 6 · −$267 |
| A · X3 | 9 · +$2,649 | 4 · −$125 | 10 · +$3,900 | 3 · −$103 | 6 · −$124 | 9 · −$1,375 | 7 · −$423 |
| A · X4 | 9 · +$18,098 | 4 · −$1,255 | 10 · +$22,249 | 3 · −$1,660 | 6 · −$709 | 9 · −$11,006 | 7 · −$4,233 |
| B · X1 | 10 · +$525 | 7 · +$178 | 12 · +$1,117 | 7 · +$50 | 5 · +$215 | 9 · +$200 | 5 · −$20 |
| B · X2 | 9 · +$1,101 | 6 · +$157 | 9 · +$993 | 6 · +$347 | 5 · +$473 | 8 · −$659 | 6 · −$267 |
| B · X3 | 9 · +$2,649 | 4 · −$125 | 9 · +$3,813 | 3 · −$103 | 4 · +$23 | 10 · −$1,406 | 7 · −$423 |
| B · X4 | 9 · +$18,098 | 4 · −$1,255 | 9 · +$21,616 | 3 · −$1,660 | 4 · +$662 | 10 · −$11,309 | 7 · −$4,233 |

By session (trades · net $):

| config · exit | 2026-10-12 | 2026-10-13 | 2026-10-14 | 2026-10-15 | 2026-10-16 |
|---|---|---|---|---|---|
| A · X1 | 9 · −$624 | 7 · +$31 | 18 · +$1,865 | 6 · −$215 | 17 · +$1,395 |
| A · X2 | 9 · −$562 | 7 · +$48 | 15 · +$3,100 | 5 · −$728 | 17 · +$1,396 |
| A · X3 | 9 · −$578 | 6 · +$47 | 18 · +$2,271 | 5 · −$609 | 10 · +$3,266 |
| A · X4 | 9 · −$5,507 | 6 · +$1,178 | 18 · +$12,066 | 5 · −$3,758 | 10 · +$17,505 |
| B · X1 | 9 · −$624 | 7 · +$31 | 18 · +$1,926 | 5 · −$92 | 16 · +$1,024 |
| B · X2 | 9 · −$562 | 7 · +$48 | 15 · +$3,099 | 4 · −$606 | 14 · +$166 |
| B · X3 | 9 · −$578 | 6 · +$47 | 18 · +$2,265 | 4 · −$487 | 9 · +$3,179 |
| B · X4 | 9 · −$5,507 | 6 · +$1,178 | 18 · +$11,908 | 4 · −$2,533 | 9 · +$16,872 |

Session bootstrap (iid over the 5 sessions, audit_lib.session_stats, 2,000 draws) of net per trade — printed to show how wide five sessions are, not as an interval anyone should lean on:

| config · exit | net per trade | 95% (sessions) | without SPXW | 95% |
|---|---|---|---|---|
| A · X1 | +$43.03 | [−$44.50, +$85.09] | +$21.51 | [−$2.72, +$37.00] |
| A · X2 | +$61.38 | [−$72.38, +$148.79] | +$29.17 | [−$28.44, +$49.21] |
| A · X3 | +$91.60 | [−$68.47, +$224.37] | +$12.93 | [−$27.80, +$47.63] |
| A · X4 | +$447.58 | [−$510.35, +$1,217.75] | +$100.62 | [−$140.44, +$338.15] |
| B · X1 | +$41.19 | [−$40.04, +$85.91] | +$22.78 | [−$2.21, +$40.44] |
| B · X2 | +$43.78 | [−$69.34, +$144.00] | +$26.59 | [−$28.44, +$47.55] |
| B · X3 | +$96.23 | [−$65.09, +$232.36] | +$10.18 | [−$27.80, +$43.13] |
| B · X4 | +$476.48 | [−$465.65, +$1,249.03] | +$76.80 | [−$140.44, +$304.10] |

## 5. Baselines (X2 exit, same contract rule, same stop definition)

**PREVIEW — 5 sessions, no verdict.** (a) and (b) under the same risk rules; (c) RANDOM: 500 seeded trials, the full strategy's X2 count per name, minutes drawn from its entry minutes, its call share.

| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | MFE / MAE (option) | long (calls) | short (puts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Config A · FULL strategy · X2 | 53 | 49% | +$232.16 / −$103.07 | +$61.38 | +17.4% | +$3,352 | +$3,253 | 2.17 | 24 / 14 | +45% / −24% | 8 −$571 | 45 +$3,824 |
| Config A · (a) crossover | 81 | 32% | +$254.26 / −$88.06 | +$21.82 | +7.9% | +$1,905 | +$1,768 | 1.37 | 36 / 15 | +33% / −29% | 55 +$162 | 26 +$1,605 |
| Config A · (b) alignment only | 45 | 29% | +$83.97 / −$98.50 | −$45.78 | −16.4% | −$1,982 | −$2,060 | 0.35 | 27 / 10 | +20% / −27% | 18 −$1,486 | 27 −$574 |
| Config B · FULL strategy · X2 | 49 | 47% | +$208.98 / −$102.36 | +$43.78 | +12.6% | +$2,236 | +$2,145 | 1.81 | 24 / 12 | +40% / −25% | 7 −$449 | 42 +$2,594 |
| Config B · (a) crossover | 79 | 32% | +$197.14 / −$104.70 | −$9.18 | −3.4% | −$593 | −$725 | 0.87 | 41 / 23 | +37% / −34% | 45 −$305 | 34 −$420 |
| Config B · (b) alignment only | 45 | 29% | +$92.12 / −$90.18 | −$37.51 | −14.0% | −$1,611 | −$1,688 | 0.42 | 23 / 5 | +18% / −26% | 17 −$1,144 | 28 −$545 |

| (c) RANDOM | trades a trial | call share | net per trade: mean [5%, 95%] | total net: mean [5%, 95%] | win: mean | full strategy X2: per trade / total | full's percentile among the trials (total) |
|---|---|---|---|---|---|---|---|
| Config A | 53 | 15% | +$18.75 [−$36.16, +$75.86] | +$994 [−$1,917, +$4,021] | 42% | +$61.38 / +$3,253 | 89th |
| Config B | 49 | 14% | +$15.08 [−$42.04, +$81.76] | +$739 [−$2,060, +$4,006] | 42% | +$43.78 / +$2,145 | 80th |

Baselines without SPXW:

| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | MFE / MAE (option) | long (calls) | short (puts) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Config A · FULL · X2 | 31 | 48% | +$105.29 / −$42.19 | +$29.17 | +28.4% | +$947 | +$904 | 2.34 | 33 / 24 | +55% / −29% | 1 −$23 | 30 +$928 |
| Config A · (a) crossover | 59 | 31% | +$83.96 / −$33.96 | +$2.01 | +2.4% | +$200 | +$119 | 1.09 | 38 / 18 | +37% / −31% | 39 −$287 | 20 +$406 |
| Config A · (b) alignment only | 31 | 32% | +$57.93 / −$29.47 | −$1.28 | −1.5% | +$3 | −$40 | 0.94 | 36 / 13 | +26% / −28% | 10 −$176 | 21 +$136 |
| Config B · FULL · X2 | 29 | 45% | +$111.32 / −$42.25 | +$26.59 | +25.3% | +$811 | +$771 | 2.14 | 32 / 21 | +49% / −30% | 1 −$23 | 28 +$795 |
| Config B · (a) crossover | 59 | 32% | +$70.20 / −$34.70 | −$0.92 | −1.1% | +$27 | −$54 | 0.96 | 39 / 14 | +37% / −34% | 35 −$199 | 24 +$145 |
| Config B · (b) alignment only | 32 | 31% | +$57.53 / −$28.42 | −$1.56 | −1.9% | −$6 | −$50 | 0.92 | 29 / 6 | +23% / −27% | 10 −$136 | 22 +$86 |

## 6. Stock-only study: the underlying's move, entry → exit

**PREVIEW — 5 sessions, no verdict.** CALCULATED: the signed move of the underlying (SPX for SPXW) from C[s] at entry to the close of the exit bar (X4: the quantity-weighted exit), in bp and in R. Signal quality apart from the option's spread, decay and fees.

| config · exit | trades | mean bp | median bp | mean R | median R | share > 0 | SPXW mean bp | SPY | QQQ | IWM |
|---|---|---|---|---|---|---|---|---|---|---|
| A · X1 | 57 | +4.3 | +5.2 | +0.33 | +1.07 | 61% | +1.6 | +11.8 | +6.7 | -1.6 |
| A · X2 | 53 | +4.8 | -1.1 | +0.49 | -0.65 | 49% | +2.5 | +6.9 | +10.1 | +0.6 |
| A · X3 | 48 | +3.2 | -4.4 | +0.32 | -0.94 | 29% | +3.0 | +10.8 | +0.7 | +1.5 |
| A · X4 | 48 | +2.3 | -4.3 | +0.15 | -0.71 | 33% | +1.3 | +8.5 | +1.3 | +0.7 |
| B · X1 | 55 | +4.3 | +6.9 | +0.38 | +1.07 | 64% | +1.7 | +13.4 | +6.7 | -5.0 |
| B · X2 | 49 | +3.6 | -1.1 | +0.41 | -1.01 | 47% | +1.9 | +5.5 | +10.1 | -5.2 |
| B · X3 | 46 | +2.0 | -4.8 | +0.28 | -0.96 | 28% | +3.4 | +10.5 | +0.7 | -5.8 |
| B · X4 | 46 | +1.3 | -4.6 | +0.11 | -0.82 | 33% | +1.6 | +7.7 | +1.3 | -5.1 |

The same for the baselines (X2):

| baseline | trades | mean bp | median bp | mean R | share > 0 |
|---|---|---|---|---|---|
| Config A · (a) crossover | 81 | +1.5 | -5.7 | -0.05 | 33% |
| Config A · (b) alignment only | 45 | -1.1 | -3.3 | +0.89 | 33% |
| Config B · (a) crossover | 79 | -0.1 | -6.1 | -0.05 | 38% |
| Config B · (b) alignment only | 45 | -1.3 | -3.0 | +0.82 | 31% |

## 7. Costs

**PREVIEW — 5 sessions, no verdict.** CALCULATED. Fees at the rulebook's rates; the half-spreads are what the ask-in / bid-out fills paid over the mid (exit half-spread read on the exit row; a missing exit quote counts 0).

| config · exit | gross | fees | half-spreads paid | net | fees ÷ premium | half-spreads ÷ premium | gross mid-to-mid (gross + half-spreads) |
|---|---|---|---|---|---|---|---|
| A · X1 | +$2,558 | −$106 | −$312 | +$2,452 | +0.51% | +1.52% | +$2,870 |
| A · X2 | +$3,352 | −$99 | −$297 | +$3,253 | +0.53% | +1.59% | +$3,649 |
| A · X3 | +$4,484 | −$87 | −$295 | +$4,397 | +0.60% | +2.04% | +$4,780 |
| A · X4 | +$22,356 | −$872 | −$2,744 | +$21,484 | +0.60% | +1.89% | +$25,100 |
| B · X1 | +$2,367 | −$102 | −$296 | +$2,265 | +0.51% | +1.50% | +$2,662 |
| B · X2 | +$2,236 | −$91 | −$260 | +$2,145 | +0.53% | +1.53% | +$2,496 |
| B · X3 | +$4,510 | −$83 | −$278 | +$4,427 | +0.60% | +2.00% | +$4,788 |
| B · X4 | +$22,751 | −$833 | −$2,579 | +$21,918 | +0.60% | +1.85% | +$25,330 |

## 8. Context columns (reported, not required in v0)

**PREVIEW — 5 sessions, no verdict.** Full strategy, X2. "With" = the 15m close on the trade's side of EMA200(15m) / the last two confirmed 5-bar swings (2 each side, known 2 bars later) rising for calls, falling for puts.

| config | 200 EMA with: n · net | against: n · net | structure with: n · net | not: n · net |
|---|---|---|---|---|
| A | 47 · +$3,479 | 6 · −$226 | 10 · +$92 | 43 · +$3,161 |
| B | 44 · +$2,249 | 5 · −$104 | 9 · +$45 | 40 · +$2,100 |

## 9. Config A against Config B

**PREVIEW — 5 sessions, no verdict.** Trades shared = the same name, session, entry minute and side.

| exit | A trades | B trades | shared | A net | B net | A − B net |
|---|---|---|---|---|---|---|
| X1 | 57 | 55 | 52 | +$2,452 | +$2,265 | +$187 |
| X2 | 53 | 49 | 48 | +$3,253 | +$2,145 | +$1,108 |
| X3 | 48 | 46 | 45 | +$4,397 | +$4,427 | −$30 |
| X4 | 48 | 46 | 45 | +$21,484 | +$21,918 | −$434 |

## 11. What a full program would need

- **Data ranges**: the 0DTE 1-minute chains on disk (SPY, QQQ, SPXW, IWM) and the underlying bars back to 2017 (SPX prints too); open interest from UW's dated chain only from 2023-11-21 (before it the OI ≥ 250 filter cannot be applied — run it as a stated variant without OI there); previous-session volume from ThetaData EOD. Non-0DTE 1-minute quotes are not on disk: any 1–7 DTE version of the spec needs them fetched first.
- **Splits, fixed before a result**: a development (Pick) span, a check span and a held-out span drawn once by month (as the scanner study did, scanner_lib HELD_M), with this week and every week the forward trackers already read marked as seen. Every v0 choice above (EMA warm-up, SPX bars and VWAP stand-in, targets on closes, the "crossed EMA50" reading, the delta band and pick, the 12% spread cap, the cooldown) becomes a named variant tested on Pick only, the winner fixed and committed before Check and the holdout are read once.
- **Regimes**: up, down and flat weeks, high- and low-VIX months, FOMC/CPI days, and the call side alone (this week had almost no calls). Gate on the random baseline (same minutes, same side mix) per regime, not on the raw P&L.
- **Statistics**: a session-block bootstrap with at least ~250 sessions per name, Bonferroni over the configs × exits chosen from, and a forward paper run after the holdout before any money.
- **Caveats of this preview**: the EMA warm-up read the 60 sessions from 2026-07-17, which include 2026-08, a month the scanner study holds out — only the underlying bars were read there, for EMA warm-up, no option or outcome; SPX bars are one print a minute (high = low = close), so its pullback and stop read closes only; X4 is 10 contracts, so its dollars are ~10× the others.

## 10. Integrity: a plain-loop re-derivation

`verify_plain.py` (does not import the engine; raw parquet, plain Python loops, its own Black-Scholes bisection) re-derived 14 trades drawn (seed 20261023) one per config × exit × name: the rule at the entry minute, no earlier allowed minute where the rule and a contract would have entered, the contract, R, every exit leg, the bids and the net. **Differences: 0.**

| config · exit | name | session | entry | contract | exit | net $ | check |
|---|---|---|---|---|---|---|---|
| A · X1 | SPY | 2026-10-16 | 13:04 | put 765.0 | +1R at minute 223 | +86.63 | 0 differences |
| A · X3 | QQQ | 2026-10-14 | 13:51 | put 728.0 | runner at minute 285 | -38.37 | 0 differences |
| A · X2 | SPY | 2026-10-15 | 09:47 | put 766.0 | stop at minute 41 | -73.37 | 0 differences |
| B · X1 | SPXW | 2026-10-16 | 11:51 | put 7710.0 | +1R at minute 145 | +297.45 | 0 differences |
| A · X4 | QQQ | 2026-10-16 | 12:31 | put 716.0 | runner at minute 255 | +1191.25 | 0 differences |
| A · X3 | IWM | 2026-10-12 | 13:35 | put 278.0 | runner at minute 270 | -10.37 | 0 differences |
| B · X3 | IWM | 2026-10-15 | 11:11 | call 274.0 | stop at minute 113 | -23.37 | 0 differences |
| A · X3 | SPY | 2026-10-16 | 14:17 | put 763.0 | runner at minute 345 | -23.37 | 0 differences |
| B · X2 | SPXW | 2026-10-12 | 12:18 | call 7815.0 | stop at minute 172 | -92.55 | 0 differences |
| A · X3 | SPXW | 2026-10-12 | 14:32 | put 7800.0 | stop at minute 313 | -127.55 | 0 differences |
| A · X1 | QQQ | 2026-10-14 | 09:58 | put 736.0 | +1R at minute 123 | +105.63 | 0 differences |
| B · X4 | IWM | 2026-10-15 | 11:11 | call 274.0 | stop at minute 113 | -233.75 | 0 differences |
| A · X1 | IWM | 2026-10-14 | 11:58 | put 272.0 | +1R at minute 167 | +36.63 | 0 differences |
| B · X3 | SPXW | 2026-10-12 | 15:18 | put 7800.0 | stop at minute 349 | -82.55 | 0 differences |

Unit tests (`python3 test_ema_system.py`): all tests pass (no-lookahead: 16758 decisions unchanged under perturbed future bars) — EMA, Wilder RSI against an independent loop, VWAP (and SPX's time-weighted stand-in), ROC across the session edge, the 5m/15m candle completion, RVOL, the swing confirmation two bars late, the fees; no-lookahead = every decision at m identical when every bar after m − 1 is perturbed.

