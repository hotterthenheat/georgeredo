# Hypothesis C — pre-registration (written from the 2022–2024 tables only, before any 2025–2026 figure was computed)

Written 2026-10-21 after `PERIOD=fit run_spreads.py` (out/spreads_summary.csv, out/spreads_paired.csv) and
`PERIOD=fit run_flies.py` (out/flies_summary.csv, out/flies_magdiff.csv). The OOS runs (`PERIOD=all`) were started only
after this file was saved; the file timestamps in this folder record the order.

## Debit verticals (universes A and B, the audit's entries)

What 2022–2024 shows, pooled over the four names (out/spreads_summary.csv, product = ALL):
- every cell × exit is negative; the best exit for a spread is HOLD to settlement (−6.7 % to −16.8 % of debit by cell),
  because every early close pays the second bid-ask on both legs (out/diag_cost.csv: a 1-wide ATM/first-OTM spread
  gives back 5–15 % of its debit the minute after entry against 1–4 % for the naked contract);
- the least negative cells are the WIDE vertical, 0.70Δ / 0.30Δ: A struct0 −5.2 % [−6.3, −4.1], A t1_bs_lock0 −5.5 %
  [−6.5, −4.4], B hold −6.7 % [−10.1, −3.2], B t1_bs_lock0 −7.2 % [−8.1, −6.4];
- paired against the naked contract on the same entries, the spread is better only under HOLD (A d70_30 +11.0 points
  of debit [+2.2, +19.4]; B d70_30 +13.6 [+5.3, +20.9]) and under t1_bs on B d70_30 (+1.6 [+0.4, +2.8]); under the
  audit's own best exits for the naked contract (trail50, struct0) the spread is worse in every cell, and in dollars
  per structure the 0.70/0.30 spread loses more than the naked contract in almost every cell (it costs 2–5× as much).

Pre-registered picks (one per universe; the rest of the cells are read OOS as a grid, not as picks):
- A: 0.70Δ / 0.30Δ vertical, structural stop at the swept level + 0 bps, flat at 15:58 (`d70_30 / struct0`).
- B: 0.70Δ / 0.30Δ vertical, held to settlement (`d70_30 / hold`).
- The paired claim to check OOS: "a 0.70/0.30 debit vertical held to settlement loses a smaller share of its debit than
  the naked nearest-OTM contract held to settlement" (A and B, d70_30, hold).
Pre-registered expectation: all three stay negative in 2025–2026 (every fit interval is below zero and the loss is the
round trip plus the decay, not a signal); the hypothesis that the vertical "keeps the directional premium" is already
rejected on fit because there is no directional premium in these entries (the audit's underlying forward returns are
±2 bps). A positive OOS cell would be read as noise unless its fit figure was also positive, which none is.
Universe B IWM's three positive hold cells (+5.9 %, −0.1 %, +10.2 %; n 72–173, eight months of fit data, every
interval through zero) are noted and NOT picked.

## Late-day ATM butterflies (15:00 and 15:30, held to settlement), cut by moc_mag

What 2022–2024 shows (out/flies_summary.csv, out/flies_magdiff.csv; % = of max risk):
- SPXW: ±5 loses −29 % (15:00) / −20 % (15:30) of risk (win 0.27 / 0.35: the wings are a strike apart and the fills eat
  the structure); ±10 −5 %; ±25 +0.8 % [−3.0, +4.6] / −0.1 %; the straddle-width wing (median 10) −6 % / −8 %. No SPXW cell
  has a fit interval above zero.
- SPY and QQQ: the ±2 fly is positive at both times in every form — call fly SPY 15:00 +8.1 % [+3.0, +13.5], QQQ +10.8 %
  [+5.4, +16.3], SPY 15:30 +6.8 % [+2.4, +11.4], QQQ +9.1 % [+4.4, +13.8]; pooled ETF+SPXW iron ±2 15:00 +10.9 % [+6.1, +15.7],
  wo5 +9.1 %, PF 1.54, every fit year positive (QQQ 15:30 2022 −2 % on n = 32). ±5 is positive with a tighter interval
  (SPY 15:00 +2.8 % [+0.7, +4.8], QQQ +3.9 % [+1.7, +6.0]); ±1 and the straddle-width wing (median 1) sit on zero.
- IWM (fit = 2024-04 to 2024-12 only): every cell negative.
- moc_mag: Q12 (low) minus Q345 (high) is POSITIVE in every pooled cell (+2 to +11 points of risk) but the interval
  includes zero in all but SPXW 15:00 ±5 (+18.8 [+0.5, +37.8]) and IWM 15:30 (n 64 / 92). The sign agrees with the
  hypothesis (a quiet close pins), the size is not established on fit.

Pre-registered picks:
- P1 (primary): SPY and QQQ, 15:00, iron butterfly ±2, unconditional (`1500 / iron / w2`, products SPY and QQQ).
- P2 (the cash-account form of P1): SPY and QQQ, 15:00, long call butterfly ±2 (`1500 / call / w2`).
- P3 (secondary): SPY and QQQ, 15:00, long call butterfly ±5 (`1500 / call / w5`).
- The signal claim to check OOS: on P1–P3, Q12 mean > Q345 mean (expected +2 to +6 points, interval likely through zero).
- No SPXW pick (no fit cell clear of zero on the positive side); no IWM pick (eight months of fit, all negative);
  15:30 cells are read OOS as the grid, not as picks.
Pre-registered expectation: P1–P3 positive OOS with smaller means than fit (selection on the best of 14 ETF wing × time
cells shrinks); the verdict is "edge" only if the OOS mean of a pick is positive with its session-bootstrap interval
clear of zero AND the mean without the best five sessions is positive AND both OOS years are positive; otherwise
"needs more data". A fill stress of $0.01 a leg against the structure (stress_fills.py, written after this file) is
read on both periods as a robustness check, not as a selection.
