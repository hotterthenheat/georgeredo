# Compass Phase 2, Hypothesis B: straddle-boundary and midday theta capture

Scope: the counterparty to the audit's boundary fade — sell defined-risk 0DTE credit spreads at the first touch of
spot ± the ATM straddle (upper_1 / lower_1), and iron condors sold in the 11:30–13:30 window — on SPXW (5- and 10-wide)
and SPY (1- and 2-wide), under the owner's guardrails (no invented weights, picked on 2022–2024 and read once on
2025–2026, friction-adjusted, negative findings valid). Every number below comes from a script in
`research_notes/Compass phase 2/hyp_b_boundary_theta/` (`engine.py` → `out/trades_<P>.parquet`; `analyze.py` →
`out/touch_cells.csv`, `out/touch_byscan.csv`, `out/midday_cells.csv`, `out/prereg.txt`; `paired.py` → `out/paired.csv`;
`friction_full.py` → `out/friction_full.csv`; `friction.py` → `out/friction.csv` (an 80-session-a-period sample, superseded
by `friction_full.csv`); `verify.py` → `out/verify.txt`). The two `trades_<P>.parquet` files (26 MB) are rebuildable
intermediates: `engine.py SPXW` and `engine.py SPY` rebuild them from the raw chains and the audit's event tables in about
five minutes each. QQQ and IWM were not run (the brief names SPXW and SPY; the engine takes them with `WIDTHS` as listed).

## Verdict in one paragraph

**The touch is not a signal for the short side either.** Selling the spread at the boundary touch earns nothing stable
over selling the same structure at the same time of day without the touch: the touch's increment over the time-matched
unconditional sell is negative on every rule and both products in 2022–2024 (SPY 2-wide −0.9 to −1.0 % of max risk a
spread, SPXW −1.6 to −6.1 %) and positive in 2025–2026 (+0.4 to +3.1 %, +0.1 to +1.3 %) — the sign flips, which is noise
on top of a short-premium harvest that was simply richer in 2025–2026. SPXW loses at the NBBO in every touch cell of the
fit period (5-wide −2.6 to −8.9 % of max risk, CIs excluding zero) and is flat to negative out of sample. **The midday
iron condor on SPY is unconditional short premium that reads positive in both periods** — the pre-registered cell (SPY
2-wide, short strikes the first listed strike outside spot ± the ATM straddle, held to settlement, mid-VIX tercile)
made +4.6 % of max risk a condor in fit and +3.3 % out of sample (CI $0.03–$10.69 a condor), its unfiltered parent +2.8 %
and +3.1 % with both CIs excluding zero — but it is $5 a condor on a four-leg structure whose bid-ask and fees are 40–45 %
of the gross, it fails on SPXW in both periods, and managing it (50 % buy-back, 2× stop) turns it negative everywhere.
Verdict: **touch — no edge; midday SPY condor — needs X** (a forward paper run with real complex-order fills and a
settlement check), **SPXW — no edge at these widths at the NBBO.** No rule is justified for the terminal today beyond a
descriptive one (below).

## Data, events and conventions (exact)

- Raw: the local ThetaData store (`RAW`): same-day chains at 1-minute NBBO for SPXW (1,106 session files from 2022-05-13)
  and SPY (980 from 2022-11-11); SPX prints and VIX prints a minute; SPY 1-minute bars. No vendor call was made. Half days
  are skipped (the audit's event tables hold none). Full sessions used: SPXW 1,097 (fit 2022-05-13 → 2024-12-31: 656; OOS
  2025-01-02 → 2026-10-09: 441), SPY 971 (fit 530, OOS 441). Minute m = 0 is 09:30; an ETF bar stamped t closes at t+1 so the
  spot at m is the close of the bar stamped m−1; an SPX print stamped m is the price at m; a chain row stamped m is the
  NBBO at m; the close is minute 390.
- Events are the audit's own tables, read and never rebuilt (`AUDIT/out/scans_<P>.parquet`, `touches_<P>.parquet`,
  `daily_<SYM>.parquet`): at each of the 14 scan minutes (09:35, 10:00, 10:30 … 15:30, 15:50) the spot and the ATM
  straddle mid (M = straddle); the touch is the FIRST minute t > scan at which the spot reaches spot_scan ± M (mult 1.0) or
  ± 1.2533 M; `move_atr` = (px_t − prior close) / Wilder atr14 lagged one session (analyze_atr.py's definition; this test
  uses |move_atr|). A later scan's touch at the same minute is the same event and the same trade, so pooled cells are ONE
  ROW A TOUCH MINUTE (session, side, t, rule, width); the by-scan table keeps the scan-level rows. Touch minutes (mult 1.0,
  both sides): SPXW fit 4,640 in 650 sessions (2,321 up / 2,319 down), OOS 3,127 in 438; SPY fit 2,865 in 513 (1,350 up /
  1,515 down), OOS 2,561 in 432. Tradable touches are those at or before 15:58 (minute 388).
- Structures: an up touch sells a call credit spread (short K, long K + width), a down touch a put spread (short K, long
  K − width); iron condor = both. Widths SPXW 5 and 10, SPY 1 and 2. Short-strike rules at the touch: `at` = the first
  listed strike at or beyond the touch price; `half` = the first strike at or beyond px_t ± 0.5 × the REMAINING ATM straddle
  at t (the mid straddle of the strike nearest px_t with both sides quoted at t); `d15`/`d20`/`d25` = the OTM strike whose
  Black-Scholes |delta| is nearest 0.15 / 0.20 / 0.25, r = q = 0, the vol implied by the option's own mid at the entry
  minute, τ = minutes to 16:00 (only σ√τ enters delta, so the annualisation cancels). Scheduled sells (the baselines and the
  midday test) at every scan minute of every full session: `d10`/`d15`/`d20`/`d25`, `em1` = the first strike outside
  spot ± 1.0 × the straddle (the band's own edge), `em1p` = outside ± 1.2533 ×, `half` = outside ± 0.5 ×.
- Fills: a short leg sold at its bid, a long leg bought at its ask, at the entry minute's NBBO; credit ≥ $0.05 a spread or
  no trade; $0.65 a leg each way; a closing trade pays the fee on every leg closed; at expiry a worthless leg pays nothing
  and an in-the-money leg settles at intrinsic with no fee assumed. **SPXW settles on the last SPX print at or before
  16:00 as a proxy for the official SET** (the official settlement is not on disk — said here as the brief asks). **SPY
  settles on the close of the bar stamped 16:00** (the closing-auction print), **no assignment fee assumed.**
- Management, every row carries all four: hold to settlement; buy back at ≤ 50 % of the credit (`tp50`); stop at ≥ 2× the
  credit (`stop2x`); both (the earlier). Exits are checked at the NBBO of every minute from e+1 to 15:59 (cost to close =
  the short's ask − the long's bid; a minute where either side is unquoted cannot exit). A condor is managed as one
  position on its total credit.
- Max risk = width × 100 − credit × 100. Session bootstrap: 2,000 resamples of sessions. "Full loss" = P&L ≤ −95 % of max
  risk. The 1-lot sequence is the cell's trades in session, entry-minute order.
- Filters, pre-registered as cells: |move_atr| ≤ 1.5 vs all (and > 1.5); touches before 14:00 vs after; by scan time; by
  side; the 1.2533 multiplier. Midday: unconditional, |move_atr| ≤ 1.5 at the scan, and VIX terciles cut on the FIT
  period's VIX prints at those five minutes (SPY cuts 15.3 / 19.1; SPXW 14.9 / 19.9, the SPXW chain starting six months
  earlier).
- Verification: `verify.py` re-derived 50 random spreads (25 a product, touch and scheduled, every rule) from the raw
  chain files with plain loops — a scalar bisection for the delta rules, a dict of quotes, the minute-by-minute cost to
  close, settlement and the four P&Ls — **0 of 50 differ** from `engine.py` in any of short_k, long_k, credit, tp_m,
  stop_m, pnl_hold, pnl_tp, pnl_stop, pnl_both, settle (`out/verify.txt`). The engine was also run twice (the second run
  adding the legs' other sides for the friction decomposition): 809,458 SPXW and 553,024 SPY rows identical on every
  original column.

## The pre-registered picks (fixed on 2022–2024 before any 2025–2026 row was read)

The fit-only run (`analyze.py fit`) filters the OOS sessions out at load and writes `out/prereg.txt`. The rule, mechanical:
the cell with the highest fit-period lower 95 % bootstrap bound of mean $ per $100 of max risk, requiring N ≥ 300 trades,
≥ 150 sessions and a positive mean without the best five sessions; touch cells over product × width × rule × management
with filter in {all, |move_atr| ≤ 1.5} at mult 1.0; midday cells over product × width × structure × rule × management ×
filter in {all, |move_atr| ≤ 1.5, each VIX tercile}, scans pooled.

- **Touch pick: SPY, 2-wide, 25-delta short strike, hold to settlement, no filter.** Fit: N 2,890, 512 sessions, +$1.81 a
  spread, +1.07 % of max risk, CI [−$1.99, +$5.37], win 83.5 %, without the best five sessions +$1.36. Its lower bound is
  **negative** (−1.11 % of risk): no touch cell on either product had a fit-period CI excluding zero, and **no SPXW cell
  qualified at all** (every SPXW touch cell has a negative mean without its best five sessions). The pick is therefore
  "the least bad cell", recorded as such before the OOS read.
- **Midday pick: SPY, 2-wide iron condor, short strikes the first listed strike outside spot ± the ATM straddle (`em1`),
  hold to settlement, mid-VIX tercile (15.3–19.1).** Fit: N 748, 178 sessions, +$7.39 a condor, +4.61 % of max risk, CI
  [+$1.36, +$12.88], win 80.5 %, without the best five +$5.86, full-loss share 2.0 %. Its unfiltered parent (all VIX) was
  fourth in the ranking: +$4.64, +2.83 %, CI [+$0.86, +$8.22], N 2,340, 525 sessions.

## The touch test (`out/touch_cells.csv`, `out/paired.csv`, `out/touch_byscan.csv`)

### The pre-registered touch pick, fit and OOS

SPY 2-wide, d25, hold, all touches (mult 1.0), one row a touch minute:

| | fit 2022–2024 | OOS 2025–2026 |
|---|---|---|
| N / sessions | 2,890 / 512 | 2,600 / 432 |
| mean $ a spread / % of max risk | +1.81 / +1.07 % | +6.84 / +3.91 % |
| session-bootstrap 95 % CI ($) | [−1.99, +5.37] | [+3.29, +10.10] |
| win rate / avg win / avg loss | 83.5 % / +18.66 / −83.65 | 88.4 % / +20.68 / −95.74 |
| full-loss share | 3.7 % | 4.2 % |
| p5 / p1 / worst ($) | −120.30 / −181.30 / −195.30 | −104.30 / −175.30 / −191.30 |
| worst session | 2024-05-31, −$2,085.80 | 2026-04-13, −$1,527.30 |
| total / total without the worst session | +$5,231 / +$7,317 | +$17,784 / +$19,311 |
| profit factor | 1.13 | 1.60 |
| max drawdown / longest losing streak (1-lot) | $4,033 / 13 | $4,639 / 10 |
| mean without the best 5 sessions / their share of the total | +$1.36 / 26 % | +$6.37 / 9 % |
| by year ($) | 2022 +1.06, 2023 +1.15, 2024 +2.59 | 2025 +6.40, 2026 +7.41 |

A single tail day: the worst session is 8.6 % of the OOS total and 40 % of the fit total (which was only $5.2K on 2,890
spreads). The OOS cell reads well on its own — but see the baseline.

### What the touch adds (the paired comparison)

The brief's paired baseline — the same structure sold at the same scan time in every session — has a look-ahead when
paired within the session: a scan-time sell in a session that then reached the band on that side was run through by
construction, so "touch minus same-session pair" is +$19 to +$359 a spread in every cell (`paired.csv`, `paired_diff`) and
says nothing. The honest baseline is the **time-of-day-matched unconditional sell**: each touch at minute t is matched to
the scheduled sells of the same side, rule and width at the scan minute nearest t in every session of the period, weighted
by the touches' own mix of sides and times (`tod_pct_risk`). Mean % of max risk a spread, hold, mult 1.0 (scan-level rows):

| product, width, rule | fit: touch / time-matched / increment | OOS: touch / time-matched / increment |
|---|---|---|
| SPY 2, d25 (the pick) | +0.85 / +1.82 / **−0.97** | +3.84 / +2.37 / **+1.47** |
| SPY 2, at | +1.58 / +1.29 / +0.29 | +4.89 / +1.83 / +3.06 |
| SPY 2, d15 | −0.05 / +0.86 / −0.91 | +2.08 / +1.68 / +0.40 |
| SPY 2, half | +1.05 / +1.95 / −0.90 | +3.79 / +2.45 / +1.35 |
| SPY 1, d25 | +0.41 / +1.72 / −1.31 | +3.93 / +2.03 / +1.90 |
| SPXW 5, d15 | −3.22 / −1.31 / **−1.91** | −0.06 / −0.97 / **+0.91** |
| SPXW 5, at | −7.32 / −1.24 / −6.08 | −3.10 / −1.30 / −1.80 |
| SPXW 10, d25 | −2.27 / −0.25 / −2.03 | +0.87 / −0.44 / +1.31 |
| SPXW 10, d15 | −2.00 / −0.30 / −1.70 | +0.81 / −0.15 / +0.97 |

The touch's increment is negative in the fit period for 19 of the 20 product × width × rule cells (the exception SPY
2-wide `at`, +0.29) and positive in 2025–2026 for 19 of 20 (the exception SPXW 5-wide `at`). Nothing about the touch is
stable; what moved between the periods is the unconditional short-premium harvest itself (SPY 2-wide d25 time-matched
+1.82 % → +2.37 %) and the touch sessions' share of it. The audit's finding stands from the other side: the boundary is a
ruler, not a level, and the counterparty of a losing long fade is not a winning short — it is the unconditional short
premium with the spread paid.

### Every touch cell, hold, mult 1.0 (mean % of max risk; $ a spread; N; session-bootstrap CI in $)

SPXW (every fit cell negative; 5-wide CIs exclude zero):

| width, rule | fit all | fit \|move_atr\| ≤ 1.5 | fit < 14:00 / ≥ 14:00 | OOS all | OOS \|move_atr\| ≤ 1.5 | OOS < 14:00 / ≥ 14:00 |
|---|---|---|---|---|---|---|
| 5, at | −7.20 % (−$23.98, 4,648, [−35.3, −12.3]) | −7.01 % | −8.93 / −6.05 | −2.83 % (−$10.80, 3,139, [−24.0, +2.4]) | −2.98 | −4.00 / −1.93 |
| 5, half | −4.16 % (−$16.80, 4,608, [−27.7, −5.5]) | −3.84 | −4.92 / −3.66 | −1.26 % (−$5.78, 3,119, [−18.1, +6.0]) | −1.19 | −1.51 / −1.06 |
| 5, d15 | −3.13 % (−$14.47, 4,545, [−23.8, −5.6]) | −2.92 | −2.58 / −3.51 | −0.20 % (−$1.11, 3,077, [−10.3, +7.5]) | −0.20 | −0.17 / −0.22 |
| 5, d20 | −3.40 % (−$15.04, 4,623, [−24.9, −4.5]) | −3.14 | −2.94 / −3.70 | −0.28 % (−$1.68, 3,112, [−12.2, +8.4]) | −0.27 | −0.23 / −0.32 |
| 5, d25 | −3.67 % (−$15.44, 4,640, [−26.6, −4.1]) | −3.31 | −3.84 / −3.56 | −0.36 % (−$2.14, 3,127, [−13.7, +9.0]) | −0.32 | −0.02 / −0.61 |
| 10, at | −3.85 % (−$27.15, 4,654, [−49.2, −4.7]) | −3.59 | −5.13 / −3.00 | −0.16 % (−$3.45, 3,142, [−28.6, +21.7]) | −0.15 | −0.64 / +0.22 |
| 10, half | −2.40 % (−$20.45, 4,627, [−41.0, +0.7]) | −2.14 | −2.65 / −2.23 | +0.69 % (+$4.13, 3,143, [−17.7, +27.0]) | +0.70 | +0.89 / +0.54 |
| 10, d15 | −2.12 % (−$19.92, 4,600, [−36.0, −3.2]) | −1.95 | −1.77 / −2.36 | +0.80 % (+$7.11, 3,134, [−8.7, +21.7]) | +0.79 | +0.80 / +0.80 |
| 10, d20 | −2.11 % (−$19.21, 4,640, [−36.7, −0.1]) | −1.87 | −1.72 / −2.36 | +0.91 % (+$7.46, 3,143, [−10.9, +25.0]) | +0.91 | +1.03 / +0.83 |
| 10, d25 | −2.28 % (−$19.98, 4,656, [−39.3, +0.8]) | −1.99 | −2.11 / −2.40 | +1.01 % (+$7.68, 3,144, [−12.7, +27.6]) | +1.03 | +1.37 / +0.73 |

SPY:

| width, rule | fit all | fit \|move_atr\| ≤ 1.5 | fit < 14:00 / ≥ 14:00 | OOS all | OOS \|move_atr\| ≤ 1.5 | OOS < 14:00 / ≥ 14:00 |
|---|---|---|---|---|---|---|
| 1, at | +0.66 % (+$0.49, 2,995, [−2.2, +3.0]) | +0.49 | +0.53 / +0.76 | +3.48 % (+$2.41, 2,635, [−0.2, +5.0]) | +3.47 | +1.04 / +5.59 |
| 1, half | +0.83 % (+$0.62, 2,697, [−1.7, +2.9]) | +0.66 | +1.38 / +0.32 | +3.74 % (+$3.04, 2,466, [+0.8, +5.2]) | +3.90 | +2.40 / +5.02 |
| 1, d15 | −0.07 % (−$0.07, 2,087, [−2.1, +1.8]) | −0.11 | +0.20 / −0.37 | +1.90 % (+$1.71, 2,038, [−0.1, +3.4]) | +2.03 | +1.27 / +2.63 |
| 1, d20 | −0.01 % (−$0.03, 2,620, [−2.3, +1.9]) | −0.13 | +0.52 / −0.51 | +2.71 % (+$2.36, 2,414, [+0.4, +4.2]) | +2.87 | +1.68 / +3.74 |
| 1, d25 | +0.74 % (+$0.58, 2,865, [−1.6, +2.8]) | +0.62 | +0.91 / +0.59 | +4.08 % (+$3.41, 2,561, [+1.3, +5.4]) | +4.22 | +2.74 / +5.29 |
| 2, at | +1.86 % (+$2.70, 2,996, [−2.0, +6.9]) | +1.70 | +2.74 / +1.17 | +4.90 % (+$7.28, 2,648, [+2.7, +11.6]) | +5.01 | +3.71 / +5.93 |
| 2, half | +1.21 % (+$1.99, 2,745, [−2.2, +5.8]) | +1.10 | +1.88 / +0.62 | +4.07 % (+$6.89, 2,522, [+2.9, +10.4]) | +4.28 | +3.33 / +4.76 |
| 2, d15 | +0.15 % (+$0.26, 2,411, [−3.1, +3.2]) | +0.13 | +0.39 / −0.10 | +2.05 % (+$3.80, 2,350, [+1.0, +6.4]) | +2.15 | +1.69 / +2.43 |
| 2, d20 | +0.56 % (+$0.97, 2,729, [−2.8, +4.2]) | +0.50 | +1.26 / −0.07 | +2.98 % (+$5.35, 2,511, [+2.1, +8.1]) | +3.07 | +2.33 / +3.59 |
| 2, d25 (pick) | +1.07 % (+$1.81, 2,890, [−2.0, +5.4]) | +0.98 | +1.51 / +0.70 | +3.91 % (+$6.84, 2,600, [+3.3, +10.1]) | +4.05 | +3.13 / +4.61 |

Cuts that were pre-registered and what they did:
- **|move_atr| ≤ 1.5** removes 4–5 % of touches and changes every cell by under 0.4 points of risk, in no consistent
  direction (SPY 2-wide d25: 1.07 → 0.98 fit, 3.91 → 4.05 OOS; SPXW 5-wide d15: −3.13 → −2.92, −0.20 → −0.20). The
  excluded touches (|move_atr| > 1.5, SPY 2-wide d25) were +1.07 % fit and +2.1 % OOS: the ATR filter is not where the
  money is on the short side either.
- **Before vs after 14:00**: on SPY the fit period favoured the morning (d25 +1.51 vs +0.70) and the OOS period the
  afternoon (+3.13 vs +4.61); on SPXW the two halves are within a point of each other in both periods. Not stable.
- **Side**: SPY's down touches (put spreads) beat its up touches in fit (2-wide d25 +1.56 vs +0.51 %) and the reverse in
  OOS (+3.53 vs +4.33); SPXW's up touches (call spreads) were the worse side in fit (5-wide d25 −4.20 vs −3.14) and the
  better one in OOS (+0.72 vs −1.40). The audit's "upper touches revert less" did not turn into a side rule.
- **The 1.2533 multiplier** (fewer, later touches): SPY 2-wide d25 +0.40 % fit (N 1,916, CI [−4.1, +5.1]), SPXW every
  rule negative in fit (5-wide −2.9 to −6.4 %); OOS SPXW 5-wide d15 +1.06 % [−5.6, +13.6]. No improvement on 1.0.
- **By scan time** (`touch_byscan.csv`, 14 scans × 2 products × 2 widths × 5 rules × 4 managements): the SPY 2-wide d25
  touch cell was positive at 11 of 14 fit scans with every CI covering zero (best 11:30, +2.55 %, [−0.59, +8.98] $), and
  in OOS positive at all 14 with the CI clear of zero at nine (14:30 +6.14 %, 13:30 +5.20 %, 09:35 +4.41 %); the SPXW
  5-wide d15 cell was negative at every fit scan (09:35 −4.28 % to 11:30 −1.74 %) and mixed in OOS (09:35 +1.79 %,
  15:50 −4.10 %). The scan order does not carry over between the periods.

### Management (every cell, both periods, both products)

Hold to settlement beats every exit everywhere. SPY 2-wide d25, all touches: fit hold +1.07 % / stop2x −0.25 / tp50
−1.86 / both −2.18; OOS hold +3.91 / stop2x −0.55 / tp50 +1.10 / both −1.94. SPXW 5-wide d15: fit hold −3.13 / stop2x
−3.45 / tp50 −4.93 / both −4.18; OOS hold −0.20 / stop2x −3.67 / tp50 −1.86 / both −4.22. SPXW 5-wide `at`: fit both
−13.05 %, OOS −12.78 %. The stop at 2× credit on a $0.20–0.50 credit fires on a $0.20–0.50 move of the spread's mark —
noise on an SPXW 5-wide, where the quote itself is $0.10–0.30 wide a leg — and it closes 43–55 % of trades (win rates
fall to 42–57 %) with a second crossing of both legs' spreads and $1.30 more in fees; the 50 % buy-back pays the same
crossing to give up the second half of the credit on the 85–90 % of trades that would have expired worthless. On these
widths the only management that survives the fees is none.

### Where the result comes from (`friction_full.csv`: the same trades priced at the legs' mids with no fees)

| cell (touch, hold, one row a minute) | credit fill → mid | bid-ask + fees, % of risk | fit: at the mid / at the fill | OOS: at the mid / at the fill |
|---|---|---|---|---|
| SPY 2, d25, call (up touch) | $0.20 → $0.21 | 1.3 % | +1.80 / +0.51 | +5.66 / +4.33 |
| SPY 2, d25, put (down touch) | $0.21 → $0.22 | 1.3 % | +2.86 / +1.56 | +4.88 / +3.53 |
| SPY 2, at, call | $0.36 → $0.37 | 1.4 % | +2.31 / +0.86 | +7.62 / +5.99 |
| SPXW 5, d15, call | $0.41 → $0.49 | 2.0 % | **−1.41** / −3.36 | +1.93 / +0.07 |
| SPXW 5, d15, put | $0.39 → $0.47 | 2.1 % | **−0.83** / −2.90 | +1.61 / −0.46 |
| SPXW 5, at, call | $1.57 → $1.71 | 4.8 % | **−3.07** / −7.86 | +4.67 / −0.00 |
| SPXW 5, at, put | $1.49 → $1.66 | 5.2 % | **−1.34** / −6.54 | −0.67 / −5.57 |
| SPXW 10, d25, call | $1.30 → $1.39 | 1.2 % | **−1.63** / −2.86 | +2.78 / +1.58 |
| SPXW 10, d25, put | $1.30 → $1.41 | 1.4 % | −0.33 / −1.71 | +1.88 / +0.45 |

Two facts. On SPXW the loss in 2022–2024 is not only the spread: a call spread sold at an up touch lost 1.4–3.1 % of max
risk **at the mid with no fees** (the up touch continued, as the audit's P(back inside) 0.43 said), and the 5-wide spread's
two crossings cost another 2–5 % — an SPXW 0DTE vertical near the money gives up $8–16 a spread to the NBBO against a
$0.4–1.7 credit. On SPY the mid-priced result was positive in both periods and the friction is about 1.3 % of risk a
vertical, roughly 40–45 % of the mid's gross in fit; the OOS strength is in the premium itself (+4.9 to +7.6 % at the mid).

## The midday test (`out/midday_cells.csv`)

Iron condors and one-sided spreads sold at 11:30, 12:00, 12:30, 13:00 and 13:30 in every full session; short strikes at
10/15/20/25 delta and `em1` (the first strike outside spot ± the straddle at that minute; `em1p` and `half` also run).

### The pre-registered midday pick, fit and OOS

SPY 2-wide iron condor, `em1`, hold, scans pooled:

| | fit, VIX mid (15.3–19.1) | OOS, VIX mid | fit, all VIX | OOS, all VIX |
|---|---|---|---|---|
| N condors / sessions | 748 / 178 | 1,202 / 280 | 2,340 / 525 | 2,056 / 439 |
| mean $ a condor / % of max risk | +7.39 / +4.61 % | +5.55 / +3.25 % | +4.64 / +2.83 % | +5.19 / +3.13 % |
| session-bootstrap 95 % CI ($) | [+1.36, +12.88] | [+0.03, +10.69] | [+0.86, +8.22] | [+0.61, +9.61] |
| win rate / avg win / avg loss | 80.5 % / +26.03 / −69.48 | 82.4 % / +25.89 / −84.73 | 81.4 % / +23.98 / −79.83 | 81.4 % / +28.71 / −95.57 |
| full-loss share | 2.0 % | 5.0 % | 3.6 % | 6.7 % |
| p5 / p1 / worst ($) | −108.25 / −165.60 / −175.60 | −150.55 / −172.60 / −178.60 | −133.65 / −177.21 / −191.60 | −154.60 / −173.05 / −187.60 |
| worst session | 2024-07-25, −$764 | 2026-09-30, −$851 | 2023-08-04, −$902 | 2025-01-31, −$888 |
| total / without the worst session | +$5,524 / +$6,288 | +$6,677 / +$7,528 | +$10,848 / +$11,750 | +$10,676 / +$11,564 |
| profit factor | 1.54 | 1.36 | 1.31 | 1.29 |
| max drawdown / longest losing streak | $1,502 / 8 | $1,825 / 7 | $2,495 / 15 | $2,905 / 14 |
| mean without the best 5 / their share | +$5.86 / 23 % | +$4.64 / 18 % | +$4.10 / 13 % | +$4.56 / 13 % |
| by year ($) | 2023 +1.60, 2024 +13.63 | 2025 +7.66, 2026 +3.22 | 2022 +9.51, 2023 +0.97, 2024 +7.46 | 2025 +6.93, 2026 +3.10 |

A single tail day: the worst session is 8–13 % of each total; the five best sessions 13–23 %. The VIX-mid cell is the
pre-registered one and its OOS lower bound is +$0.03 — a hair above zero; the VIX cut did not help out of sample (low-VIX
+2.84 % on 62 sessions, high-VIX +2.99 %, mid +3.25 %, all +3.13 %) and the |move_atr| ≤ 1.5 cut read +3.75 % [+1.71,
+10.15]. By scan (all VIX, OOS): 11:30 +1.61 % [−$3.24, +$8.01], 12:00 +2.43 %, 12:30 +2.60 %, 13:00 +4.33 % [+1.68,
+12.21], 13:30 +4.92 % [+3.06, +12.46]; in fit the order was the reverse (11:30 +4.32 % [+2.94, +11.11] the best, 12:30
+1.13 % the worst). The scan ranking is not stable, so no time of day is picked. Management: stop2x −1.31 %, tp50 −1.58 %,
both −4.71 % OOS (fit −0.55, −1.45, −3.53): hold only.

### Every midday structure, hold, unfiltered (mean % of max risk; $; N; CI in $)

SPY 2-wide: condor d10 +1.14 % fit / +0.74 OOS; d15 +2.02 [−0.04, +6.95] / +3.22 [+1.63, +9.36]; d20 +2.11 / +4.80 [+3.12,
+12.13]; d25 +2.25 / +5.18; em1 +2.83 [+0.86, +8.22] / +3.13 [+0.61, +9.61]; em1p +2.46 [+0.76, +7.75] / +2.43 [−0.35,
+8.42]; half +2.42 / +5.79. One-sided call spreads +0.4 to +1.2 % fit, +0.4 to +3.8 OOS; put spreads +0.7 to +1.7 fit, +0.7 to
+1.4 OOS — every one-sided CI covers zero in fit. SPY 1-wide condors: em1 +1.34 % [−1.61, +3.58] fit / +1.07 [−2.10, +3.67]
OOS, d15 +0.63 / +2.14, d20 −0.01 / +3.61: the 1-wide pays the same bid-ask on half the credit.

SPXW: 10-wide condors every rule negative in fit (em1 −1.67 % = −$13.56, N 3,271, [−38.4, +11.3]; d15 −1.56; d25 −2.63;
half −2.15) and +0.1 to +0.9 % OOS with CIs of ±$25–35 a condor (em1 +0.48 % = +$4.47 [−27.4, +32.3], worst session
2025-08-25 −$4,388 against a +$9,834 total — one day is 45 % of it); 5-wide condors negative in BOTH periods, the fit CIs
excluding zero (em1 −5.01 % [−32.3, −5.3] $ fit, −1.74 % OOS; d15 −4.33 / −1.12; half −7.63 / −4.19). SPXW's VIX-mid
10-wide em1 condor: −1.43 % fit, +1.46 % OOS [−20.7, +44.6]. SPXW one-sided 10-wide puts were the only SPXW cells near
zero in fit (d25 +0.08 %, half +0.76 %) and they read −1.11 % and −1.86 % OOS.

Friction on the condor (two verticals): SPY 2-wide em1 legs give up $1.03–1.10 a vertical to the bid-ask plus $1.30 of
fees, about 1.25–1.3 % of max risk a side (`friction_full.csv`, sched rows); SPXW 10-wide em1 legs $8.4–10.2 a vertical,
1.1–1.3 % of risk, on a premium that was −0.2 to +1.2 % at the mid in fit — there is no premium left at these strikes once
two SPXW legs are crossed.

## Stress tests on the headline cells

- Session bootstrap: SPY touch pick fit [−$1.99, +$5.37] (covers zero); OOS [+$3.29, +$10.10]. SPY midday pick fit
  [+$1.36, +$12.88], OOS [+$0.03, +$10.69]; its parent [+$0.86, +$8.22] / [+$0.61, +$9.61]. SPXW: every fit touch CI at
  5-wide and the 5-wide condors exclude zero on the negative side; every OOS SPXW hold CI covers zero (the managed SPXW
  cells are negative with CIs excluding zero in both periods).
- Without the best five sessions: SPY touch pick +$1.36 fit / +$6.37 OOS; midday pick +$5.86 / +$4.64; SPXW touch cells
  −$15 to −$31 fit, −$0 to −$14 OOS at 5-wide, +$4.5 to +$5.5 at 10-wide d15–d25 OOS.
- By year: the SPY touch pick is positive in every year (2022 +1.06, 2023 +1.15, 2024 +2.59, 2025 +6.40, 2026 +7.41 $) but
  so is the time-matched unconditional sell; the SPY midday pick 2023 +1.60, 2024 +13.63, 2025 +7.66, 2026 +3.22; SPXW
  5-wide d25 touch 2023 −22.18, 2024 −11.23, 2025 −10.90, 2026 +8.87 — one positive year of four, the one in progress.
- The tail day: SPY cells lose 8–13 % of their total on their worst session; SPXW 10-wide cells 34–45 % (touch d25 OOS
  worst 2025-02-27 −$8,280 on a +$24,135 total; condor em1 OOS −$4,388 on +$9,834). On SPXW one session can take a
  quarter's result.
- Full-loss outcomes: 2–7 % of SPY condors and 4–9 % of SPY delta-rule touch spreads settle at or near the full width
  (15–17 % at the `at` strike on 1-wide); 6–15 % of SPXW 5-wide d15–d25 spreads and 15–23 % of SPXW 10-wide
  em1/d20/d25 condors.
- Settlement proxies: SPXW is settled on the last SPX print ≤ 16:00, not the official SET; the audit flagged the 16:00
  print as unresolved for its own late-day figures. A print error of a few points moves a settlement-touching 5-wide by up
  to its full width, so the SPXW rows are the ones a settlement check could move; the SPY 16:00 bar is the closing print.
- What the model does NOT assume: no complex-order fill between the legs' mids (every leg is at its own NBBO, which is
  conservative for SPY and realistic-to-conservative for SPXW), no slippage past the quote, no assignment fee on SPY, no
  margin cost, one lot at every event.

## Verdict

- **Boundary touch, short side: no edge.** The touch's increment over the time-matched unconditional sell changes sign
  between the periods on 19 of 20 cells in each direction; SPXW loses at the NBBO in every fit cell (CIs excluding zero
  at 5-wide) and is flat OOS; the SPY cells are the period's short-premium harvest, which the touch neither adds to nor
  times. Together with the audit's long fade (−11 to −29 % a trade), the band is now tested from both sides: neither
  buying nor selling at it has a stable return beyond the premium itself. Delete the fade; do not add a short at it.
- **Midday iron condor on SPY: needs X, not an edge yet.** The pre-registered cell held OOS (+3.25 % of max risk, CI
  lower bound +$0.03) and its parent held with a clearer margin (+3.13 %, [+$0.61, +$9.61]), both periods positive, PF
  1.3–1.5, drawdown $1.8–2.9K on a 1-lot sequence that made $10.7K OOS. But it is $5 a condor on four SPY legs; friction
  is 40–45 % of the gross; the VIX cut that made it the pick did not help OOS; the time-of-day order reversed; and it is
  the unconditional 0DTE variance premium the repository has met before, not boundary or midday-theta capture (every
  scan time and every rule shows it on SPY 2-wide). X = (1) a forward paper record of the exact rule below on SPY for at
  least 60 sessions with real complex-order fills (the question is whether the $1.05 a vertical of modelled bid-ask is
  real or the mid is reachable, which decides half the return); (2) the SPY 16:00 settlement checked against the official
  close on the sessions where a short strike was within $0.25 of it; (3) a re-read on the next 120 sessions with the rule
  unchanged. Until then it is a result, not a rule.
- **SPXW at 5 and 10 wide: no edge at the NBBO.** Negative in fit at every strike rule for touches and condors, flat with
  CIs of ±$25–35 a trade OOS, one session 34–45 % of a cell's total, and the premium at the mid is 0–1 % of risk against
  1–5 % of bid-ask and fees. An SPXW short structure needs wider spreads or fills inside the quote, neither of which this
  data can assume.

## The rule, conditional on X (not for the terminal today)

Descriptive, as the pre-registered cell was run: "On a full session, at each of 11:30, 12:00, 12:30, 13:00 and 13:30 New
York, sell one SPY 0DTE iron condor: short strikes the first listed strike above spot + the ATM straddle mid at that minute
and the first below spot − the same; wings 2 points; each leg at its NBBO; take it only if the condor's credit is ≥ $0.10
(two spreads at ≥ $0.05); hold to settlement; no stop, no buy-back." Expected on 2025–2026 at the NBBO: +$5.19 a condor on
$165 of max risk (+3.1 %), win 81 %, a full loss once in 15 condors, worst session −$888 across the five. The mid-VIX
condition (15.3–19.1) is the pre-registered cell but added nothing OOS and is dropped from the descriptive rule; the
13:00–13:30 strength is a post-hoc observation to be pre-registered, not used. Nothing in it is a boundary trigger.

## Gaps and what was not done

- QQQ and IWM were not run (not in the brief); the engine takes them unchanged.
- The SPXW settlement is a proxy (last print ≤ 16:00). The official SET and the 16:00 print question the audit left open
  were not resolved here and could move the SPXW rows that settle within a few points of a short strike.
- The ATM straddle at the touch (`half`) and the delta rules use the option's own mid as the vol; a leg with a crossed or
  one-sided quote is excluded, and a touch whose long leg is unquoted at the width is not traded (SPXW 1 %, SPY 14 % of
  touch rows; SPY's 1-wide strikes thin out away from the money and late in the day).
- The paired comparison the brief asked for (same scan, same session) is reported in `paired.csv` but is a look-ahead by
  construction; the time-of-day-matched unconditional sell is the comparison the verdict rests on.
- Each cell is one lot at every event; no sizing, margin or overlap of several open spreads in a session is modelled.

## Files

`research_notes/Compass phase 2/hyp_b_boundary_theta/`: `engine.py`, `analyze.py`, `paired.py`, `friction_full.py`,
`friction.py`, `verify.py`; `out/`: `trades_SPXW.parquet`, `trades_SPY.parquet` (rebuildable), `log_<P>.txt`,
`run_<P>.txt`, `prereg.txt`, `fit_touch_cells.csv`, `fit_touch_byscan.csv`, `fit_midday_cells.csv` (the fit-only run),
`touch_cells.csv`, `touch_byscan.csv`, `midday_cells.csv`, `summary.txt` (both periods), `paired.csv`, `friction_full.csv`,
`friction.csv`, `verify.txt`. Runs: engine 313 s (SPXW) and 211 s (SPY) at one thread, niced; analysis about four minutes.
No credentials or keys anywhere in the folder.
