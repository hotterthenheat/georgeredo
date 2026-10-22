# SPXW pre-registered test: the fly5 iron and condor_d20 analogues, and the late-day extrinsic against the realized move

**Pre-registration: `PREREG_SPXW.md`, commit `2820bb4e061d865ddb2fcb640d1661b6c5105909`** (pushed to `claude/lucid-heisenberg-bpyq7k` at 2026-10-22 02:22 UTC, before any SPXW structure was priced against an outcome). Every rule below is that file's; nothing was changed after the run. Built 2026-10-22T02:30:47+00:00 by `run_spxw.py` in this folder (174 s, three worker processes), from the stored minute Parquet (`PAPER_PARQUET_ROOT`), Cboe's SPX history (`data/official_closes/cboe_SPX_History_2026-10-22.csv`) and, for SPY and QQQ, the official closes AUDIT.md used (Theta EOD, else UW's daily bar). Nothing was fetched for the run; the fee documents were read on 2026-10-22 (section 3).

## Summary

- **(A) SPXW iron fly ±5×ratio (fly5 iron analogue), 15:00 + 15:30: FAIL.** Selection mean session sum at the package fill -39.64 [-173.06, +87.48] (20-session block); at +$0.05 -49.64; development +79.78. 1: selection mean > 0 — NO; 1: selection block-20 lower bound > 0 — NO; 2: selection mean at +$0.05 package stress > 0 — NO; 3: development mean > 0 — yes.
- **(B) SPXW 20-delta iron condor, wings 2×ratio (condor_d20 analogue), 13:00–15:00: FAIL.** Selection mean session sum at the package fill +120.76 [-95.03, +286.78] (20-session block); at +$0.05 +96.30; development +35.29. 1: selection mean > 0 — yes; 1: selection block-20 lower bound > 0 — NO; 2: selection mean at +$0.05 package stress > 0 — yes; 3: development mean > 0 — yes.
- **The package rule cost nothing and gave nothing back.** SPXW's single-leg quotes sit on $0.05 / $0.10 ticks, so the summed leg NBBO is always a multiple of $0.05: on every one of the 7,598 tradable entries the package fill at its NBBO rounded against us equals the legs-at-NBBO fill (mean lost to the rounding $0.000). Whether a complex order would have filled inside the summed NBBO is not in the data; the mid column is the most it could get.
- **(A) the iron fly is near zero in % of risk and turns with the period**: +$39.89 a trade (+1.07 % of a $4,091 max risk) in development, −$19.82 (−0.41 %) in selection; win 63 % / 59 %, profit factor 1.15 / 0.94; worst sessions −$7,891 (2024-05-31) and −$6,757 (2026-09-30). The ETF fly5 iron read +4.7 % / +5.4 % of risk on the same spans (AUDIT.md) — not evidence for SPXW, and SPXW did not reproduce it.
- **(B) the condor is positive in both periods but inside the noise**: +$7.25 a trade (+0.49 % of $1,697) in development, +$24.69 (+1.49 % of $1,688) in selection; the selection session mean +$120.76 has a 20-session block interval of [−$95, +$287]. It stays positive at +$0.05 and +$0.10 package stress in selection (+$96, +$72) but not at +$0.10 in development (−$13). It fails the rule on the interval alone.
- **The 15:58 exit is negative for both analogues in both historical periods** at every fill but the mid (iron fly −$57 / −$113 a session, condor −$137 / −$92 at the package NBBO): the hold's whole result is the last two minutes' time value plus the settlement, and the exit's second crossing and $4.8 of closing fees take more than that. SPXW's hold needs no early exit: cash-settled and European, it leaves no stock and no exercise decision after the close.
- **Fees**: $0.65 + Cboe $0.36 (premium < $1) or $0.45 (≥ $1) + the SPXW execution surcharge $0.14 + ORF $0.01248 + OCC $0.025 = $1.187 / $1.277 a contract; about $4.93 to open a four-leg structure, $4.8 more to close it at 15:58.
- **The extrinsic gap is there, in both periods and growing into the close.** Relative to the realized move to the official close, SPY's and QQQ's ATM straddle is richer than SPXW's at every minute: SPY − SPXW ratio gap +0.08 / +0.11 at 15:00, +0.12 / +0.13 at 15:30 and +0.61 / +0.80 at 15:58 (development / selection; every block-20 interval clear of zero), QQQ +0.17 / +0.11, +0.18 / +0.17 and +1.20 / +1.39. At 15:58 the ETF straddle carries 4.1 (SPY) and 7.5 (QQQ) bps more extrinsic in excess of the move than SPXW's in selection; SPXW's own straddle sits BELOW its realized move (ratio 0.79 at 15:58, 0.92 at 15:00–15:30). It is consistent with the owner's assignment-premium reading; section 9 says what it does not show.

## 1. Sessions, settlement and the code

Full NYSE sessions 2022-05-13 → 2026-10-21 (audit_lib's calendar, half days out): 1105; with an SPXW chain, SPX prints, SPY bars and an official SPX close: **1105**; left out: 0. SPXW chain files on dates that are not full sessions (half days), not used: 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24.

Sessions by period: development 656 (2022-05-13 → 2024-12-31), selection 441 (2025-01-02 → 2026-10-09), forward 8 (2026-10-12 → 2026-10-21).

| source | span | overlap days in 2022-05-13 → 2026-10-21 | disagreements > $0.005 | largest |diff| in range |
|---|---|---|---|---|
| Cboe SPX history, fetched 2026-10-22 (the primary) | 13060 rows, 1975-01-02 → 2026-10-21 |  |  |  |
| Cboe SPX history, fetched 2026-10-14 (scratchpad/spx/cboe_spx.csv) | overlap 13054 days, 1975-01-02 → 2026-10-13 | 1108 | 0 (0 in range) | 0.0000 |
| FRED SP500 (S&P DJI), scratchpad/spx/fred_sp500.csv | overlap 2512 days, 2016-10-14 → 2026-10-13 | 1108 | 9 (0 in range) | 0.0000 |

The Cboe history fetched 2026-10-22 equals the copy fetched 2026-10-14 to the cent on every overlapping day (13,054, 1975-01-02 → 2026-10-13) and FRED's SP500 on every overlapping day inside 2022-05-13 → 2026-10-13; FRED disagrees on 9 days, all before this range. The eight forward sessions (2026-10-12 → 21) after 10-13 rest on the 2026-10-22 file alone. All 1,105 full sessions in range have an official close: none was left out.

**Official close vs the last SPX print at or before 16:00** (the research's proxy), on the 1105 sessions with a trade: equal within $0.005 on 5; |difference| mean 0.64, median 0.45, p95 1.79, max 18.32 (2026-06-26: official 7354.02, print 7335.70); over 1 point on 196, over 5 on 2.

**The code imported** (read, never written), with the SHA-256 of the working-tree file the run loaded and whether every function or class used is identical to the committed HEAD version (other agents edit `scripts/` concurrently):

- `scripts/paper_tracker.py` `d8ca2db07e5986cfca946f826ee41a859b0f6763045f4fe226bacd0d2fbfb56c` — HEAD `2820bb4e06`; used code equal to HEAD: 12 of 12
- `scripts/paper_backtest.py` `f03b2b9085e4f0a6d631f809f39462b9e5af6be71e1074dd25808b6011f377a0` — HEAD `2820bb4e06`; used code equal to HEAD: 4 of 4

## 2. The structures and the 50-structure check

| analogue | period | entries | tradable | untradable: the reasons (count of reason parts) | wing width (points): trades | median ratio | mean credit, legs | mean credit, package | mean lost to the $0.05 rounding | mean opening fees |
|---|---|---|---|---|---|---|---|---|---|---|
| (A) iron fly | development | 1312 | 1312 | — | 50.0: 1306, 55.0: 6 | 10.0275 | 9.11 | 9.11 | 0.000 | $4.93 |
| (A) iron fly | selection | 882 | 882 | — | 50.0: 878, 55.0: 4 | 10.0313 | 10.58 | 10.58 | 0.000 | $4.94 |
| (A) iron fly | forward | 16 | 16 | — | 50.0: 16 | 10.0338 | 9.02 | 9.02 | 0.000 | $4.93 |
| (B) condor | development | 3280 | 3193 | call spread credit # under # (# x ratio) (56); put spread credit # under # (# x ratio) (48); long call # not quoted (ask > #) (3) | 20.0: 3191, 25.0: 2 | 10.0275 | 3.03 | 3.03 | 0.000 | $4.94 |
| (B) condor | selection | 2205 | 2157 | call spread credit # under # (# x ratio) (31); put spread credit # under # (# x ratio) (23) | 20.0: 2153, 25.0: 4 | 10.0313 | 3.13 | 3.13 | 0.000 | $4.97 |
| (B) condor | forward | 40 | 38 | put spread credit # under # (# x ratio) (1); call spread credit # under # (# x ratio) (1) | 20.0: 38 | 10.0339 | 2.66 | 2.66 | 0.000 | $4.93 |

**Verification** (`verify_50.py`, separate plain-loop code reading the raw Parquet (polars as the file reader only) and the Cboe CSV with the csv module, its own Black-Scholes bisection; no import of the tracker, the replay, audit_lib or run_spxw): 50 entries (25 a structure, seed 20261022; 50 tradable) — spot, ratio, K0, wings, the 20-delta shorts, the tradable rule, the legs' credit, the package credit, the opening fees, the package P&L on the official close and the 15:58 package exit. Differences: spot 0, ratio 0, k0 0, k_hi 0, k_lo 0, k_sc 0, k_sp 0, k_lc 0, k_lp 0, tradable 0, width 0, credit_legs 0, credit_pkg 0, fees_open 0, pnl_pkg_off 0, x_pkg 0; entries with any difference: 0.

## 3. Fees, as fixed in the pre-registration

| item | a contract | source (read 2026-10-22) |
|---|---|---|
| commission | $0.65 | the owner's stated assumption |
| Cboe customer transaction fee, SPX (incl SPXW), premium < $1.00 / ≥ $1.00 | $0.36 / $0.45 | Cboe Exchange Fees Schedule, October 1, 2026, Rate Table – Underlying Symbol List A, fee codes CS / CT (https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf; the fee-code page https://www.cboe.com/us/options/membership/fee_schedule/cboe/, shown effective October 8, 2026) |
| SPXW Execution Surcharge (electronic; customers included) | $0.14 | the same schedule; SEC Release 34-93955 ($0.13 → $0.14 from 2022-01-02) |
| Index License Surcharge | $0 for a customer | the same schedule ($0.10 for F J L M B N U, not C) |
| Options Regulatory Fee | $0.01248 | the same schedule, Regulatory Fees, "per contract side" |
| OCC clearing fee | $0.025 | OCC Schedule of Fees, SR-OCC-2025-002 / SEC Release 34-102437 (from 2025-02-14; $0.02 before); SR-OCC-2025-019 / 34-104274 (December 2025 holiday only) |
| total | $1.18748 (< $1.00) / $1.27748 (≥ $1.00) | on every contract at the open and at the 15:58 close; nothing at cash settlement |

A broker may add (exercise or settlement fees, its own pass-through of FINRA TAF and SEC Section 31 on sales) or absorb some of these (exchange, ORF and OCC fees are often bundled); the figures are a stated assumption, not a broker's bill. Complex orders carry no separate customer rate in the schedule; each leg pays per contract. The ETF reports charged $0.65 a contract only.

## 4. Session-level inference by period (package NBBO rounded against us to $0.05, fees in, official close)

A session's P&L is the sum of the analogue's trades that day (0 on a session in the universe with no tradable entry); the session mean's percentile intervals from the iid session bootstrap and the moving-block bootstrap over sessions in calendar order (blocks of 5 and 20, 2,000 draws, seed 20261022 — audit_lib.session_stats unchanged); the per-trade mean's block-20 interval; effective N from the session autocorrelations and from Var_iid ÷ Var_block-20. Periods are never pooled.

| analogue | period | sessions | trades | sessions traded / run | mean $ a trade | mean % of max risk | mean max risk | mean $ a session | session CI (iid) | block-5 CI | block-20 CI | mean $ a trade, block-20 CI | session acf lag 1..5 | effective N (acf / block-20) | total $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (A) iron fly | development | 2022-05-13 → 2024-12-31 | 1312 | 656 / 656 | +39.89 | 1.07% | $4091 | +79.78 | [-25.13, +184.63] | [-35.76, +176.72] | [-4.51, +178.27] | [-2.25, +89.13] | +0.02 -0.02 -0.04 -0.04 -0.05 | 862 / 874 | +52,337 |
| (A) iron fly | selection | 2025-01-02 → 2026-10-09 | 882 | 441 / 441 | -19.82 | -0.41% | $3944 | -39.64 | [-190.41, +99.15] | [-179.48, +99.64] | [-173.06, +87.48] | [-86.53, +43.74] | +0.01 -0.05 -0.00 -0.03 -0.09 | 673 / 529 | -17,481 |
| (A) iron fly | forward | 2026-10-12 → 2026-10-21 | 16 | 8 / 8 | +148.63 | 3.91% | $4098 | +297.27 | [-131.75, +669.65] | — | — | — | -0.39 -0.13 +0.12 -0.28 +0.37 | 30 / — | +2,378 |
| (B) condor | development | 2022-05-13 → 2024-12-31 | 3193 | 656 / 656 | +7.25 | 0.49% | $1697 | +35.29 | [-143.99, +222.41] | [-142.04, +187.27] | [-95.72, +174.29] | [-19.82, +35.62] | +0.01 -0.02 -0.12 -0.06 -0.01 | 1099 / 1143 | +23,149 |
| (B) condor | selection | 2025-01-02 → 2026-10-09 | 2157 | 441 / 441 | +24.69 | 1.49% | $1688 | +120.76 | [-89.40, +311.88] | [-96.49, +318.66] | [-95.03, +286.78] | [-19.39, +58.74] | +0.02 +0.02 +0.01 +0.01 -0.07 | 446 / 495 | +53,255 |
| (B) condor | forward | 2026-10-12 → 2026-10-21 | 38 | 8 / 8 | +206.80 | 12.19% | $1734 | +982.31 | [+700.38, +1306.99] | — | — | — | -0.23 -0.07 +0.12 -0.11 -0.27 | 24 / — | +7,858 |

## 5. Fills and settlement

Mean $ a session (block-20 interval), held to the official close; the last column the same package fill settled on the last SPX print at or before 16:00 (labelled secondary).

| analogue | period | legs at NBBO | package NBBO, $0.05 against us | package +$0.05 | package +$0.10 | mid (reference) | package, ≤ 16:00 print (secondary) | sessions where the two closes differ / trades whose P&L changes |
|---|---|---|---|---|---|---|---|---|
| (A) iron fly | development | +79.78 [-4.51, +178.27] | +79.78 [-4.51, +178.27] | +69.78 [-14.51, +168.27] | +59.78 [-24.51, +158.27] | +126.65 [+40.81, +225.66] | +78.43 [-5.61, +176.80] | 652 / 1292 |
| (A) iron fly | selection | -39.64 [-173.06, +87.48] | -39.64 [-173.06, +87.48] | -49.64 [-183.06, +77.48] | -59.64 [-193.06, +67.48] | +1.55 [-130.38, +127.97] | -27.93 [-165.41, +102.03] | 440 / 867 |
| (A) iron fly | forward | +297.27 — | +297.27 — | +287.27 — | +277.27 — | +331.33 — | +254.27 — | 8 / 16 |
| (B) condor | development | +35.29 [-95.72, +174.29] | +35.29 [-95.72, +174.29] | +10.95 [-119.85, +149.77] | -13.39 [-143.99, +125.25] | +116.01 [-16.67, +256.75] | +33.17 [-100.64, +174.98] | 652 / 926 |
| (B) condor | selection | +120.76 [-95.03, +286.78] | +120.76 [-95.03, +286.78] | +96.30 [-119.18, +262.36] | +71.85 [-143.63, +237.93] | +197.91 [-18.77, +360.95] | +147.58 [-64.58, +309.72] | 440 / 595 |
| (B) condor | forward | +982.31 — | +982.31 — | +958.56 — | +934.81 — | +1042.94 — | +919.06 — | 8 / 8 |

Mean $ a trade by fill (official close): (A) iron fly development: legs +39.89, pkg +39.89, pkg5 +34.89, pkg10 +29.89, mid +63.32; (A) iron fly selection: legs -19.82, pkg -19.82, pkg5 -24.82, pkg10 -29.82, mid +0.78; (A) iron fly forward: legs +148.63, pkg +148.63, pkg5 +143.63, pkg10 +138.63, mid +165.66; (B) condor development: legs +7.25, pkg +7.25, pkg5 +2.25, pkg10 -2.75, mid +23.83; (B) condor selection: legs +24.69, pkg +24.69, pkg5 +19.69, pkg10 +14.69, mid +40.46; (B) condor forward: legs +206.80, pkg +206.80, pkg5 +201.80, pkg10 +196.80, mid +219.57.

Settling on the last print at or before 16:00 instead of the official close moves the selection means by +$11.71 (iron fly) and +$26.82 (condor) a session and the development means by −$1.35 and −$2.12; no verdict condition changes under it (labelled secondary, never used). The two closes differ by more than one SPX point on 196 of 1,105 sessions; the largest, 18.32 points, is 2026-06-26 (a Russell reconstitution close).

Every 15:58 legs exit abandons at least one long wing (bid 0 at 15:58: ±50 from the money on the fly, 20 beyond a 20-delta short on the condor); those wings settle at intrinsic on the official close with no fee. No trade had a leg unquoted at 15:58.

## 6. Risk (package NBBO, official close, one lot)

Max risk: the wider wing × 100 − the package credit × 100 (fees not in the denominator). Drawdown, worst session, streak and the percentiles on the session sums in calendar order.

| analogue | period | mean $ a trade | mean % of max risk | win (trades) | profit factor | max drawdown $ (sessions) | worst session | longest losing streak (sessions) | full-loss share (≤ −95 % of max risk) | p1 session $ | p5 session $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| (A) iron fly | development | +39.89 | 1.07% | 62.6% | 1.15 | 30,003 | 2024-05-31 (-7,891) | 6 | 1.0% | -5,123 | -2,580 |
| (A) iron fly | selection | -19.82 | -0.41% | 58.8% | 0.94 | 39,380 | 2026-09-30 (-6,757) | 5 | 1.9% | -5,751 | -3,518 |
| (A) iron fly | forward | +148.63 | 3.91% | 62.5% | 2.22 | 814 | 2026-10-19 (-814) | 1 | 0.0% | -795 | -719 |
| (B) condor | development | +7.25 | 0.49% | 74.4% | 1.04 | 56,703 | 2024-05-31 (-8,610) | 7 | 5.3% | -7,794 | -5,637 |
| (B) condor | selection | +24.69 | 1.49% | 76.8% | 1.13 | 35,113 | 2026-04-13 (-8,614) | 5 | 5.2% | -7,724 | -4,570 |
| (B) condor | forward | +206.80 | 12.19% | 89.5% | 8.53 | 0 | 2026-10-12 (+397) | 0 | 0.0% | +406 | +445 |

## 7. The 15:58 exit, alongside

Every trade closed at the rows stamped 15:58: legs — a short bought back at its ask, a long sold at its bid, a long with no bid left to expire (no fee, intrinsic on the official close); package — Σ short asks − Σ long bids rounded UP to $0.05, every leg closed, the +$0.05 / +$0.10 stress on BOTH the entry and the exit; mid — every leg at its mid both ways. Fees on every contract closed. A trade with a leg unquoted at 15:58 has no exit value (counted). Mean $ a session, block-20 interval.

| analogue | period | hold, package (section 4) | 15:58 exit, legs at NBBO | 15:58 exit, package NBBO, $0.05 against us | 15:58 exit, package +$0.05 | 15:58 exit, package +$0.10 | 15:58 exit, mid (reference) | trades with no 15:58 value | trades with a long abandoned (legs) | mean closing fees (package) |
|---|---|---|---|---|---|---|---|---|---|---|
| (A) iron fly | development | +79.78 | -51.85 [-121.89, +39.20] | -56.54 [-126.58, +34.48] | -76.54 [-146.58, +14.48] | -96.54 [-166.58, -5.52] | +103.07 [+21.21, +195.49] | 0 | 1312 | $4.84 |
| (A) iron fly | selection | -39.64 | -108.68 [-257.13, +21.10] | -113.30 [-261.69, +16.42] | -133.30 [-281.69, -3.58] | -153.30 [-301.69, -23.58] | +6.93 [-131.29, +129.52] | 0 | 882 | $4.85 |
| (A) iron fly | forward | +297.27 | +274.57 — | +269.82 — | +249.82 — | +229.82 — | +354.51 — | 0 | 16 | $4.85 |
| (B) condor | development | +35.29 | -125.98 [-244.80, +13.72] | -136.89 [-255.58, +2.75] | -185.57 [-304.00, -46.18] | -234.24 [-352.54, -95.04] | +93.69 [-34.49, +226.98] | 0 | 3193 | $4.79 |
| (B) condor | selection | +120.76 | -81.07 [-279.37, +69.51] | -91.68 [-289.93, +58.77] | -140.60 [-338.67, +9.74] | -189.51 [-387.18, -39.31] | +92.37 [-94.34, +233.79] | 0 | 2157 | $4.79 |
| (B) condor | forward | +982.31 | +701.27 — | +690.14 — | +642.64 — | +595.14 — | +806.70 — | 0 | 38 | $4.77 |

## 8. The pass/fail rule, applied mechanically

| analogue | 1: selection mean > 0 | 1: selection block-20 lower bound > 0 | 2: selection mean at +$0.05 package stress > 0 | 3: development mean > 0 | verdict |
|---|---|---|---|---|---|
| (A) SPXW iron fly ±5×ratio (fly5 iron analogue), 15:00 + 15:30 | **no** | **no** | **no** | yes | **FAIL** |
| (B) SPXW 20-delta iron condor, wings 2×ratio (condor_d20 analogue), 13:00–15:00 | yes | **no** | yes | yes | **FAIL** |

The rule (PREREG_SPXW.md section 7): PASS only if, in the selection period, at the package-NBBO fill with the cited fees and the official-close settlement, the mean session sum is > 0 with its 20-session block-bootstrap 95 % interval excluding zero, AND the mean stays > 0 at +$0.05 package stress, AND the development-period mean is > 0. The forward period is reported, never used to pass. A PASS means "continue paper testing on SPXW", never production; a FAIL is not to be rescued by another width, minute, fill or filter read on these periods. The ETF results are not evidence for SPXW.

**Both analogues FAIL.** (A) fails conditions 1 and 2 — its selection mean is negative at the package fill (−$39.64 a session) and at +$0.05 (−$49.64); its development mean is positive. (B) fails condition 1's interval only: its selection mean is positive (+$120.76) and stays positive at +$0.05 (+$96.30), its development mean is positive (+$35.29), but the 20-session block interval [−$95.03, +$286.78] includes zero (effective N about 450–500 sessions). Under the pre-registered rule a FAIL ends this test for the analogue; it is not rescued by another width, minute, fill or filter read on these periods.

The forward period (8 sessions, never used to pass) is positive for both — the iron fly +$297 a session, the condor +$982 — the same eight sessions in which every ETF candidate was also positive (AUDIT.md's forward rows); eight sessions cannot separate a small edge from a run of quiet closes, and no interval is computed on them.

## 9. ATM extrinsic against the realized move to settlement

At 15:00, 15:30 and 15:58, every full session: K = the strike nearest spot with both sides quoted (the tracker's `Chain.nearest`); extrinsic = call mid + put mid − |spot − K|, in bps of spot; realized = |official close − spot| in bps of spot (SPY and QQQ: Theta EOD, else UW's daily bar, as AUDIT.md; SPX: Cboe). Spot: SPY and QQQ the close of the bar stamped m − 1, SPX the print stamped m. SPY and QQQ chains start 2022-11-11, so their development period is 2022-11-11 → 2024-12-31; the gaps use the sessions all three names share. Ratio = mean extrinsic ÷ mean realized; diff = mean (extrinsic − realized); intervals: 20-session moving-block bootstrap, 2,000 draws, the same draws for numerator and denominator (none under 60 sessions).

Rows without a value: QQQ no chain: 378, SPY no chain: 378. Rows with no official close: none. ATM strikes off the $0.50 grid (adjusted series): QQQ: 32.

| period | minute | name | sessions | first | mean extrinsic bps | mean realized bps | ratio | ratio block-20 CI | mean ext − real bps | block-20 CI | median extrinsic bps | median realized bps | mean |K − spot| bps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| development | 15:00 | SPY | 530 | 2022-11-11 | 19.28 | 18.98 | 1.016 | [0.950, 1.115] | +0.30 | [-0.96, +2.03] | 17.10 | 13.49 | 5.23 |
| development | 15:00 | QQQ | 530 | 2022-11-11 | 24.69 | 22.21 | 1.112 | [1.047, 1.217] | +2.48 | [+1.07, +4.64] | 21.39 | 15.07 | 6.25 |
| development | 15:00 | SPXW | 656 | 2022-05-13 | 21.50 | 21.94 | 0.980 | [0.923, 1.057] | -0.44 | [-1.65, +1.20] | 18.51 | 14.41 | 2.77 |
| development | 15:30 | SPY | 530 | 2022-11-11 | 14.77 | 14.97 | 0.986 | [0.920, 1.081] | -0.20 | [-1.22, +1.16] | 12.81 | 10.48 | 5.29 |
| development | 15:30 | QQQ | 530 | 2022-11-11 | 18.69 | 17.83 | 1.048 | [0.975, 1.166] | +0.86 | [-0.45, +2.79] | 15.83 | 12.69 | 6.26 |
| development | 15:30 | SPXW | 656 | 2022-05-13 | 15.57 | 17.08 | 0.912 | [0.852, 0.970] | -1.51 | [-2.47, -0.48] | 13.42 | 12.05 | 2.91 |
| development | 15:58 | SPY | 530 | 2022-11-11 | 7.40 | 5.53 | 1.339 | [1.213, 1.495] | +1.88 | [+1.18, +2.68] | 5.68 | 4.37 | 5.44 |
| development | 15:58 | QQQ | 530 | 2022-11-11 | 10.49 | 5.43 | 1.931 | [1.738, 2.188] | +5.06 | [+3.95, +6.39] | 7.19 | 4.11 | 6.15 |
| development | 15:58 | SPXW | 656 | 2022-05-13 | 3.74 | 4.75 | 0.787 | [0.703, 0.851] | -1.01 | [-1.44, -0.69] | 3.09 | 3.55 | 2.67 |
| selection | 15:00 | SPY | 441 | 2025-01-02 | 19.62 | 18.98 | 1.033 | [0.971, 1.119] | +0.63 | [-0.61, +1.92] | 15.48 | 11.85 | 3.67 |
| selection | 15:00 | QQQ | 441 | 2025-01-02 | 24.97 | 24.19 | 1.032 | [0.963, 1.124] | +0.78 | [-1.00, +2.65] | 19.87 | 15.71 | 4.27 |
| selection | 15:00 | SPXW | 441 | 2025-01-02 | 17.66 | 19.14 | 0.923 | [0.863, 0.992] | -1.48 | [-2.85, -0.13] | 13.92 | 12.36 | 1.93 |
| selection | 15:30 | SPY | 441 | 2025-01-02 | 15.58 | 14.83 | 1.050 | [0.966, 1.141] | +0.75 | [-0.56, +1.84] | 11.98 | 10.57 | 3.83 |
| selection | 15:30 | QQQ | 441 | 2025-01-02 | 20.30 | 18.60 | 1.091 | [1.010, 1.182] | +1.70 | [+0.20, +3.15] | 15.89 | 12.28 | 4.02 |
| selection | 15:30 | SPXW | 441 | 2025-01-02 | 13.63 | 14.85 | 0.917 | [0.837, 0.995] | -1.23 | [-2.65, -0.07] | 10.56 | 10.60 | 1.86 |
| selection | 15:58 | SPY | 441 | 2025-01-02 | 8.69 | 5.45 | 1.592 | [1.371, 1.826] | +3.23 | [+2.10, +4.48] | 6.22 | 4.03 | 3.91 |
| selection | 15:58 | QQQ | 441 | 2025-01-02 | 12.28 | 5.64 | 2.176 | [1.880, 2.521] | +6.64 | [+4.96, +8.88] | 8.34 | 4.24 | 4.38 |
| selection | 15:58 | SPXW | 441 | 2025-01-02 | 3.24 | 4.09 | 0.791 | [0.703, 0.886] | -0.85 | [-1.26, -0.47] | 2.87 | 3.09 | 1.85 |
| forward | 15:00 | SPY | 8 | 2026-10-12 | 13.43 | 12.84 | 1.046 | — | +0.59 | — | 11.64 | 13.80 | 3.31 |
| forward | 15:00 | QQQ | 8 | 2026-10-12 | 20.96 | 15.50 | 1.352 | — | +5.46 | — | 19.09 | 14.31 | 4.77 |
| forward | 15:00 | SPXW | 8 | 2026-10-12 | 11.29 | 12.07 | 0.935 | — | -0.79 | — | 9.72 | 14.09 | 1.98 |
| forward | 15:30 | SPY | 8 | 2026-10-12 | 12.64 | 7.79 | 1.622 | — | +4.85 | — | 13.31 | 6.38 | 2.39 |
| forward | 15:30 | QQQ | 8 | 2026-10-12 | 20.55 | 9.29 | 2.212 | — | +11.26 | — | 22.89 | 6.88 | 2.57 |
| forward | 15:30 | SPXW | 8 | 2026-10-12 | 9.25 | 7.08 | 1.307 | — | +2.17 | — | 9.17 | 4.88 | 1.80 |
| forward | 15:58 | SPY | 8 | 2026-10-12 | 8.24 | 4.28 | 1.926 | — | +3.96 | — | 6.95 | 4.62 | 2.59 |
| forward | 15:58 | QQQ | 8 | 2026-10-12 | 13.52 | 5.69 | 2.379 | — | +7.84 | — | 10.54 | 5.78 | 2.94 |
| forward | 15:58 | SPXW | 8 | 2026-10-12 | 2.55 | 3.14 | 0.810 | — | -0.60 | — | 2.35 | 3.30 | 1.40 |

**The gaps, on the sessions all three share** (ETF − SPXW; a positive ratio gap = the ETF priced richer relative to its own realized move):

| period | minute | ETF | common sessions | ETF ratio | SPXW ratio | ratio gap | block-20 CI | gap in (ext − real) bps | block-20 CI | gap in extrinsic bps | block-20 CI | gap in realized bps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| development | 15:00 | SPY | 530 | 1.016 | 0.939 | +0.077 | [+0.050, +0.113] | +1.47 | [+0.96, +2.00] | +1.26 | [+0.83, +1.76] | -0.21 |
| development | 15:00 | QQQ | 530 | 1.112 | 0.939 | +0.173 | [+0.128, +0.238] | +3.65 | [+2.74, +4.83] | +6.68 | [+5.70, +7.82] | +3.03 |
| development | 15:30 | SPY | 530 | 0.986 | 0.866 | +0.120 | [+0.093, +0.155] | +1.82 | [+1.40, +2.28] | +1.70 | [+1.33, +2.17] | -0.12 |
| development | 15:30 | QQQ | 530 | 1.048 | 0.866 | +0.182 | [+0.125, +0.262] | +2.88 | [+1.91, +4.11] | +5.61 | [+4.66, +6.61] | +2.73 |
| development | 15:58 | SPY | 530 | 1.339 | 0.733 | +0.606 | [+0.505, +0.728] | +3.01 | [+2.38, +3.71] | +4.28 | [+3.61, +4.98] | +1.27 |
| development | 15:58 | QQQ | 530 | 1.931 | 0.733 | +1.198 | [+1.005, +1.449] | +6.20 | [+5.01, +7.51] | +7.37 | [+6.17, +8.70] | +1.17 |
| selection | 15:00 | SPY | 441 | 1.033 | 0.923 | +0.111 | [+0.070, +0.156] | +2.12 | [+1.52, +2.73] | +1.96 | [+1.57, +2.38] | -0.16 |
| selection | 15:00 | QQQ | 441 | 1.032 | 0.923 | +0.110 | [+0.066, +0.162] | +2.26 | [+1.25, +3.37] | +7.31 | [+6.23, +8.61] | +5.05 |
| selection | 15:30 | SPY | 441 | 1.050 | 0.917 | +0.133 | [+0.081, +0.192] | +1.97 | [+1.25, +2.72] | +1.95 | [+1.38, +2.57] | -0.02 |
| selection | 15:30 | QQQ | 441 | 1.091 | 0.917 | +0.174 | [+0.119, +0.239] | +2.93 | [+1.98, +3.97] | +6.68 | [+5.62, +8.04] | +3.75 |
| selection | 15:58 | SPY | 441 | 1.592 | 0.791 | +0.801 | [+0.634, +1.007] | +4.09 | [+3.20, +5.13] | +5.45 | [+4.41, +6.94] | +1.36 |
| selection | 15:58 | QQQ | 441 | 2.176 | 0.791 | +1.385 | [+1.149, +1.672] | +7.49 | [+6.02, +9.54] | +9.04 | [+7.58, +11.21] | +1.55 |
| forward | 15:00 | SPY | 8 | 1.046 | 0.935 | +0.112 | — | +1.38 | — | +2.15 | — | +0.76 |
| forward | 15:00 | QQQ | 8 | 1.352 | 0.935 | +0.417 | — | +6.25 | — | +9.67 | — | +3.43 |
| forward | 15:30 | SPY | 8 | 1.622 | 1.307 | +0.316 | — | +2.68 | — | +3.39 | — | +0.71 |
| forward | 15:30 | QQQ | 8 | 2.212 | 1.307 | +0.906 | — | +9.09 | — | +11.29 | — | +2.20 |
| forward | 15:58 | SPY | 8 | 1.926 | 0.810 | +1.115 | — | +4.56 | — | +5.70 | — | +1.14 |
| forward | 15:58 | QQQ | 8 | 2.379 | 0.810 | +1.568 | — | +8.43 | — | +10.98 | — | +2.54 |

**What the gap shows.** Late in a 0DTE session the ETF straddle at the money is priced above what the underlying then moves to its official close, and SPXW's is not — SPXW's is priced below it (ratio 0.79 at 15:58 in both periods). The gap is not a quoting artefact: the ATM quotes are 0.2–0.45 bps of spot wide on all three, an order of magnitude under the 4–9 bp gap at 15:58; the 32 QQQ rows on an adjusted (.78) strike do not move it (ratio 1.957 / 2.176 at 15:58 without them); and the strike grid works the other way — SPY's and QQQ's ATM strike sits 3.7–6.5 bps from spot against SPXW's 1.9–2.9, which lowers the ETF straddle's extrinsic, not raises it. The realized moves are close to each other (SPY within 0.2 bps of SPXW's at 15:00–15:30, 1.3 bps more at 15:58); the gap is in the price.

**What it does not show.** It does not measure an assignment premium; it is consistent with one. An ETF option's holder can exercise or abandon until about 5:30 pm on after-hours prices and a writer can be assigned on information he does not have at 16:00 — an option the realized-to-the-official-close measure leaves out, so part or all of the ETF's excess may be the price of the after-hours move it pays off on (the after-hours study, backtest_audit/AFTERHOURS.md, is the place that move is measured). Other candidates the data here cannot separate from it: the dealer's overnight stock and margin risk on a physically settled position; the ETF's closing-auction risk (the official close is an auction print — SPY's 2025-04-09 cross was $5.25 off its 15:59 bar); the ETFs' dividend and early-exercise mechanics on ex-dividend eves; and, on the SPXW side, that the official SPX close is computed from the components' closing prices and differs from the last print (mean 0.64 points, about 1 bp), part of SPXW's realized move a 15:58 quote may not price. Nor is it a tradable edge: selling the ETF straddle at 15:58 to collect it means carrying exactly the assignment and after-hours exposure the premium may be paying for, and the ETF hold-to-expiry results (AUDIT.md section 8) are the trades that carried it.

## 10. Files and commands

```
cd "research_notes/Compass phase 3/spxw_prereg"
export PAPER_PARQUET_ROOT=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta
# the structures, every fill, both settlements, the 15:58 exits and the extrinsic rows → out/trades.parquet, out/extrinsic_raw.parquet, out/build.json
POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 python3 -I run_spxw.py build --workers 3
# 50 structures re-derived by separate code → out/verify_50.json
python3 -I verify_50.py
# the statistics, the verdicts and the extrinsic study → out/results.json, out/extrinsic.parquet, SPXW_REPORT.md
POLARS_MAX_THREADS=1 python3 -I run_spxw.py report
```

`PREREG_SPXW.md` (the pre-registration, commit 2820bb4e06), `run_spxw.py` (build, statistics), `verify_50.py`, `write_report.py` (this file's tables), `prose.json` (the report's written paragraphs, added after the numbers were read); `out/`: trades.parquet (one row an entry: legs, quotes, every P&L), extrinsic_raw.parquet / extrinsic.parquet, build.json (sessions, exclusions, the SPX close cross-check, the code hashes), results.json, verify_50.json. `scripts/` and `tests/` were not edited. No vendor was called; no key or secret was read or written.
