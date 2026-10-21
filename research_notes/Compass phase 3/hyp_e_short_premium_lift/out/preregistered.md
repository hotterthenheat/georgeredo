# Hypothesis E, pre-registration - written 2026-10-21T21:00:44+00:00 (UTC) by prereg.py from the fit pass (2022-11-11 -> 2024-12-31) alone; no 2025-2026 trade row has been collected by any script in this folder (analyze.py filters the period at load; verify.py was run with `fit`).

## Rule (fixed before the OOS read)
- Cells: SPY 0DTE call vertical / put vertical / iron condor, short strike d10 / d15 / d20 / d25 / em1, widths 1 and 2, sold at the 12 scan minutes 10:00 .. 15:30, HOLD to settlement; signal = the t2 GBM decile at the scan minute (D1-2 or D1); the lift = the signal's mean net against the time-of-day-matched unconditional mean (all sessions at the same scan minute), weighted by the signal's scan mix; paired session bootstrap, 2,000 draws, seed 20261016.
- The pick = the hold cell with the highest fit LOWER 95% bound of the lift in % of max risk, with N >= 300 structures, >= 150 sessions, lift > 0 without the best 5 sessions, and the cell's own mean > 0 without its best 5 sessions.
- Pre-registrable only if that cell's fit lift CI excludes zero in % of risk and in $. OOS "edge" = the pick's OOS lift CI (in % of risk and in $) above zero AND its OOS lift > 0 without the best 5 sessions AND the signal cell's own OOS mean CI above zero AND the lift > 0 in each OOS year (2025, 2026). The OOS pass (analyze.py oos) is run once.
- The unconditional benchmark is read OOS regardless (the owner asked for it); its strongest fit cells are listed below so that no scan time or rule is chosen on the OOS read.

## Qualifying hold cells, ranked (fit; lift in % of max risk with its CI, then $)
```
shape: (14, 19)
┌────────┬───────────┬──────┬───────┬───┬───────────────┬──────────────────┬────────────────────┬──────────┐
│ signal ┆ structure ┆ rule ┆ width ┆ … ┆ lift_wo_best5 ┆ lift_vs_rest_usd ┆ lift_vs_rest_ci_lo ┆ wo_best5 │
│ ---    ┆ ---       ┆ ---  ┆ ---   ┆   ┆ ---           ┆ ---              ┆ ---                ┆ ---      │
│ str    ┆ str       ┆ str  ┆ f64   ┆   ┆ f64           ┆ f64              ┆ f64                ┆ f64      │
╞════════╪═══════════╪══════╪═══════╪═══╪═══════════════╪══════════════════╪════════════════════╪══════════╡
│ D1-2   ┆ put       ┆ d15  ┆ 2.000 ┆ … ┆ 0.584         ┆ 2.200            ┆ -1.671             ┆ 1.678    │
│ D1-2   ┆ put       ┆ em1  ┆ 2.000 ┆ … ┆ 0.566         ┆ 2.458            ┆ -1.845             ┆ 2.111    │
│ D1-2   ┆ put       ┆ em1  ┆ 1.000 ┆ … ┆ 0.789         ┆ 2.222            ┆ -0.759             ┆ 0.972    │
│ D1-2   ┆ put       ┆ d20  ┆ 2.000 ┆ … ┆ 0.509         ┆ 2.231            ┆ -2.256             ┆ 2.320    │
│ D1-2   ┆ put       ┆ d20  ┆ 1.000 ┆ … ┆ 0.622         ┆ 1.825            ┆ -1.230             ┆ 1.104    │
│ D1-2   ┆ put       ┆ d15  ┆ 1.000 ┆ … ┆ 0.730         ┆ 1.996            ┆ -1.094             ┆ 0.617    │
│ D1-2   ┆ put       ┆ d25  ┆ 2.000 ┆ … ┆ 0.253         ┆ 2.282            ┆ -2.932             ┆ 3.390    │
│ D1-2   ┆ put       ┆ d25  ┆ 1.000 ┆ … ┆ 0.518         ┆ 1.850            ┆ -1.293             ┆ 1.979    │
│ D1     ┆ put       ┆ d25  ┆ 1.000 ┆ … ┆ 0.986         ┆ 2.507            ┆ -1.944             ┆ 2.485    │
│ D1     ┆ put       ┆ d20  ┆ 2.000 ┆ … ┆ 0.116         ┆ 2.090            ┆ -4.776             ┆ 1.957    │
│ D1     ┆ put       ┆ d25  ┆ 2.000 ┆ … ┆ 0.292         ┆ 2.841            ┆ -4.873             ┆ 3.426    │
│ D1     ┆ put       ┆ d20  ┆ 1.000 ┆ … ┆ 0.362         ┆ 1.607            ┆ -2.833             ┆ 0.893    │
│ D1     ┆ put       ┆ em1  ┆ 1.000 ┆ … ┆ 0.301         ┆ 1.662            ┆ -2.995             ┆ 0.521    │
│ D1     ┆ condor    ┆ d25  ┆ 1.000 ┆ … ┆ 0.283         ┆ 3.389            ┆ -2.645             ┆ 2.611    │
└────────┴───────────┴──────┴───────┴───┴───────────────┴──────────────────┴────────────────────┴──────────┘
```

## Pick (the highest lower bound): signal D1-2, put d15 width 2, hold
- Fit: N 1169, sessions 377, mean $2.42 = 1.31% of max risk; time-matched unconditional 0.59%; lift +0.72% of risk, 95% CI [-0.99, +2.20]; lift $+1.32 [-1.85, +4.04]; lift without the best 5 sessions $+0.58; vs the rest (D3-D10) $+2.20 [-1.67, +5.79]; the cell's own mean without its best 5 $+1.68; win 0.933; full-loss share 0.018.
- Lift by year (fit): 2022 +3.95 (n 97), 2023 +2.13 (n 420), 2024 +0.17 (n 652)
- **NOT PRE-REGISTRABLE: the fit lift CI does not exclude zero (in % of risk and in $). The OOS lift is read for the record only, labelled not pre-registrable.**
- Qualifying hold cells whose fit lift CI excludes zero (both yardsticks): 0 of 14; of every hold cell (no size filter): 0 of 60; hold cells with a NEGATIVE lift upper bound: 0.
- For the record, the best managed cell (secondary, not the pick): stop2x D1-2 put d15 w1: lift +1.15% [+0.23, +2.07], N 929.

## The unconditional benchmark in fit (for the OOS read; nothing chosen OOS)
Pooled over the 12 scans, hold, the ten highest lower bounds (% of max risk; CI in $):
```
shape: (10, 15)
┌───────────┬──────┬───────┬──────┬───┬─────────────────┬──────────┬─────────────────────────┬─────────────┐
│ structure ┆ rule ┆ width ┆ N    ┆ … ┆ full_loss_share ┆ wo_best5 ┆ friction_share_of_gross ┆ significant │
│ ---       ┆ ---  ┆ ---   ┆ ---  ┆   ┆ ---             ┆ ---      ┆ ---                     ┆ ---         │
│ str       ┆ str  ┆ f64   ┆ i64  ┆   ┆ f64             ┆ f64      ┆ f64                     ┆ bool        │
╞═══════════╪══════╪═══════╪══════╪═══╪═════════════════╪══════════╪═════════════════════════╪═════════════╡
│ condor    ┆ d25  ┆ 2.000 ┆ 6049 ┆ … ┆ 0.078           ┆ 3.791    ┆ 0.512                   ┆ true        │
│ condor    ┆ em1  ┆ 2.000 ┆ 5055 ┆ … ┆ 0.045           ┆ 3.075    ┆ 0.561                   ┆ true        │
│ condor    ┆ d20  ┆ 2.000 ┆ 5814 ┆ … ┆ 0.055           ┆ 3.156    ┆ 0.557                   ┆ true        │
│ put       ┆ d25  ┆ 2.000 ┆ 6218 ┆ … ┆ 0.040           ┆ 2.710    ┆ 0.436                   ┆ false       │
│ condor    ┆ d15  ┆ 2.000 ┆ 5115 ┆ … ┆ 0.038           ┆ 2.277    ┆ 0.632                   ┆ false       │
│ put       ┆ d20  ┆ 2.000 ┆ 6103 ┆ … ┆ 0.029           ┆ 1.810    ┆ 0.530                   ┆ false       │
│ put       ┆ d10  ┆ 2.000 ┆ 3970 ┆ … ┆ 0.015           ┆ 1.100    ┆ 0.648                   ┆ false       │
│ put       ┆ em1  ┆ 2.000 ┆ 5781 ┆ … ┆ 0.027           ┆ 1.558    ┆ 0.561                   ┆ false       │
│ call      ┆ em1  ┆ 2.000 ┆ 5282 ┆ … ┆ 0.017           ┆ 1.292    ┆ 0.597                   ┆ false       │
│ put       ┆ d15  ┆ 2.000 ┆ 5682 ┆ … ┆ 0.021           ┆ 1.090    ┆ 0.643                   ┆ false       │
└───────────┴──────┴───────┴──────┴───┴─────────────────┴──────────┴─────────────────────────┴─────────────┘
```
Significant unconditional hold cells by scan (CI of the mean $ above zero), of 30 a scan:
- 10:00: 0 significant; strongest put d15 w2: +0.73% of risk, $+1.30 [-2.45, +4.78], N 527
- 10:30: 0 significant; strongest put d25 w2: +2.65% of risk, $+4.59 [-0.04, +8.84], N 529
- 11:00: 1 significant; strongest put d25 w2: +2.79% of risk, $+4.68 [+0.28, +8.83], N 527
- 11:30: 2 significant; strongest condor em1 w2: +4.32% of risk, $+7.11 [+2.92, +11.21], N 495
- 12:00: 3 significant; strongest put d10 w1: +3.10% of risk, $+2.90 [+0.80, +4.51], N 153
- 12:30: 0 significant; strongest call em1 w2: +0.85% of risk, $+1.57 [-1.60, +4.47], N 480
- 13:00: 0 significant; strongest put d10 w2: +1.33% of risk, $+2.57 [-0.04, +4.59], N 346
- 13:30: 2 significant; strongest condor d25 w2: +3.91% of risk, $+5.49 [+0.18, +10.82], N 521
- 14:00: 1 significant; strongest condor d25 w2: +3.34% of risk, $+5.01 [+0.03, +9.87], N 513
- 14:30: 7 significant; strongest condor d25 w2: +4.80% of risk, $+7.76 [+3.40, +11.91], N 505
- 15:00: 9 significant; strongest condor d25 w1: +8.47% of risk, $+5.91 [+2.88, +8.85], N 435
- 15:30: 13 significant; strongest condor d25 w1: +7.35% of risk, $+5.29 [+2.16, +8.39], N 365

Expectation written now: the unconditional short-premium harvest on SPY 2-wide reads positive in fit at most scans; the signal's lift is the question. If the lift is not pre-registrable, the expectation for the OOS lift is "inside the noise".
