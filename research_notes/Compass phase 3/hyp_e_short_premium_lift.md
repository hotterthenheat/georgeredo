# Compass Phase 3, Hypothesis E: unconditional vs regime-filtered SPY short 0DTE premium held to the close

Scope: the owner's benchmark — SPY defined-risk 0DTE credit spreads and iron condors sold at every scan minute 10:00 → 15:30
and held to settlement, unconditionally — and the question whether the Phase 2 volatility model's BOTTOM deciles (D1–D2 of
Hypothesis D's t2 model, the minutes at which the model says the straddle is least likely to be beaten by the next 30
minutes) give a statistically significant lift over the time-of-day-matched unconditional sell. Every number below comes
from a script in `research_notes/Compass phase 3/hyp_e_short_premium_lift/` and its `out/`; nothing was fetched; nothing
outside that folder was edited (Hypothesis B's engine and trade table and Hypothesis D's feature and model code were read,
not touched). Fit 2022-11-11 → 2024-12-31 (530 full sessions), OOS 2025-01-02 → 2026-10-09 (441), read once after
`out/preregistered.md` was written (section 4, verbatim, timestamp 2026-10-21T21:00:44Z).

## Verdict in one paragraph

**The signal: no edge established — the test was not pre-registrable.** In the fit period no hold cell's paired
time-of-day-matched lift had a 95 % interval clear of zero (0 of 60; the best lower bound was −0.99 % of max risk: D1–2,
put vertical, 15-delta short strike, 2-wide, lift +0.72 % [−0.99, +2.20]). Read OOS for the record only, that pick's lift
is +1.46 % of risk [+0.05, +2.71] ($+2.69 [+0.06, +4.99] a spread) — at the edge of zero — and the grid as a whole reads
far better OOS than in fit (37 of 60 hold cells clear zero; the D1 condor cells +5 to +15 % of risk with intervals well
above zero) while the same cells were noise in 2022–2024 (D1 condor 20-delta 2-wide: fit +0.6 % [−5.4, +5.9], negative
without its best five sessions; OOS +9.0 % [+5.3, +12.3]). A lift that is absent in the period it was fitted on and large
in the single period read afterwards is a one-period, post-hoc observation, not a result; the robustness reads say why it
moves — the fit's lift is destroyed by FOMC decision days (a quiet morning before a 14:00 statement is exactly a D1 minute,
and the condor then takes its full loss), while in 2025–2026 those days were the condors' best; the logistic model's
deciles give no clear lift in fit and a weaker one OOS. **The benchmark: SPY 2-wide iron condors sold unconditionally from
13:00 to 15:00 and held are positive in both periods with intervals clear of zero** (20-delta: +2.3 % of max risk in fit
[$0.11, $7.27], +4.2 % OOS [$3.05, $10.09]; 25-delta +3.0 % / +4.6 %; the straddle-edge rule +2.3 % / +3.4 %), friction
41–56 % of the gross, hold beating every management, 1-wide and single verticals mostly inside the noise — Hypothesis B's
midday result, extended to the afternoon. **Verdict: signal — no edge (needs X: a forward pre-registered re-test of the D1
condor filter on ≥ 150 new sessions against the same time-matched benchmark, and an event calendar on disk); benchmark —
the unconditional afternoon condor stands as the thing to beat, itself still "needs X" (Hypothesis B's forward paper run).**
No rule for the terminal.

## 1. Data, conventions, what was built

- Raw (`RAW`, the local ThetaData store; nothing fetched): `data_full/chains/SPY/<date>.parquet` 1-minute NBBO of every
  same-day SPY contract, 980 session files 2022-11-11 → 2026-10-09; `data/underlying/SPY` 1-minute bars; `data/index/VIX`
  prints. Half days dropped (9: 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03,
  2025-11-28, 2025-12-24) → 971 full sessions, fit 530, OOS 441.
- Conventions (the audit's, Hypothesis B's and D's): minute m = 0 is 09:30 New York; a bar stamped t closes at t+1, so the
  spot at m is the close of the bar stamped m−1; a chain row stamped m is the NBBO at m; the close is minute 390. Each leg
  at its own NBBO (short at the bid, long at the ask); $0.65 a leg each way; a closing trade pays the fee on every leg
  closed; a leg expiring worthless pays nothing; an ITM leg settles at intrinsic on the close of the bar stamped 16:00 (the
  closing print), no assignment fee assumed (stated); credit ≥ $0.05 a vertical or no trade; one lot.
- Trades: Hypothesis B's scheduled-sell table, read-only (`hyp_b_boundary_theta/out/trades_SPY.parquet`, its `engine.py`):
  at each of the audit's scan minutes of every full session a call vertical (short K, long K + width), a put vertical
  (short K, long K − width) and the iron condor (both), short strike by rule, widths 1 and 2, with hold / 50 % buy-back
  (`tp50`) / 2× stop (`stop2x`) P&L. This test takes the 12 scans 10:00, 10:30 … 15:30 (m = 30 … 360), the rules d10 /
  d15 / d20 / d25 (the OTM strike whose Black-Scholes |delta| from its own mid, r = q = 0, is nearest 0.10 / 0.15 / 0.20 /
  0.25) and em1 (the first listed strike outside spot ± 1.0 × the ATM straddle mid at the scan), both widths, the three
  structures: 30 structure cells × 12 scans. Rows: fit 147,195 structures (530 sessions), OOS 128,686 (441).
- The signal: Hypothesis D's t2 model (`hyp_d_vol_breakout/lib.py`, `model.py`, read-only). SPY's scan-minute table was
  rebuilt for EVERY full session with Hypothesis D's own `session_rows` (`build_minutes.py`: 971 sessions kept of 980,
  69,912 scan minutes, 72 a session — 09:35 … 15:25 every five minutes as Hypothesis D had them, plus 15:30 added from
  the wrapper so this test's last scan has a score; 551 s single-threaded) and the t2 model refitted exactly as
  `model.py` does (`fit_model.py` imports its GBM settings, 5 contiguous-block out-of-fold scoring and decile function):
  fit = sessions before 2024-07-01, trained on the 71 scan minutes Hypothesis D used; cuts = the nine inner quantiles of
  the final score on 2024-07 → 2024-12; OOS scored once. Two stated differences from Hypothesis D: SPY alone (no product
  categorical; Hypothesis D pooled four products) and all sessions (it took every second). The decile used (`dec`): in
  the fit period the out-of-fold score cut at its own fit-period quantiles; in the cut and OOS periods the final model's
  score at the registered cuts — as Hypothesis D's fit+cut and oos reads.
- Scripts: `build_minutes.py` → `out/minutes_SPY_all.parquet` (rebuildable, 25 MB); `fit_model.py` → `out/scores_SPY.parquet`
  (rebuildable, 2 MB), `model_auc.csv`, `decile_rates.csv`, `feature_importance.csv`, `hypd_spy_auc.csv`; `fit_model.py oos`
  → `model_auc_oos.csv`, `decile_rates_oos.csv`; `analyze.py fit|oos` (THE PERIOD IS FILTERED AT LOAD — the fit pass never
  collects a 2025–2026 trade row) → `<mode>_uncond_byscan.csv`, `<mode>_uncond_pooled.csv`, `<mode>_lift_cells.csv`,
  `<mode>_lift_byscan.csv`, `<mode>_summary.txt`; `prereg.py` → `preregistered.md`; `verify.py fit|oos 50 <seed>` →
  `verify_<mode>.txt`; `report.py` → `tables.md`; `notes_tables.md` (`notes_tables.py`); `cluster.py` → `cluster.txt`,
  `signal_by_month.csv`; `robust.py` → `robust.txt`, `robust_lr_<mode>.csv`, `robust_fomc_<mode>.csv`. Logs in `logs/`.
  The two parquets in `out/` are the only intermediates and are rebuildable by the scripts named. Compute: every run
  `nice -n 10`, one thread (`POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1`, LightGBM `num_threads=1`), session by session; the
  longest run 551 s, the model 15 s, each analysis pass under 20 s.
- Order of the reads (file times, UTC, 2026-10-21): fit analysis 21:00:13–21:00:24, fit verification 21:00:35,
  `preregistered.md` 21:00:44, OOS analysis 21:01:10–21:01:19, OOS model read 21:01:20, OOS verification 21:01:34.
- Verification (`verify.py`, separate plain-loop code: dicts keyed by (right, strike, minute), a scalar Black-Scholes
  bisection through `math.erf`, its own strike rules, its own minute-by-minute cost to close, its own settlement): 50
  random structures of this test's cells from the fit period (seed 11) and 50 from the OOS period (seed 12), re-derived
  from the raw chain and bar files and compared with Hypothesis B's rows on short_k, long_k, credit, settle, settle_val,
  spot, tp_m, stop_m, pnl_hold, pnl_tp, pnl_stop (tolerance $0.005), and the scan minute's straddle, straddle/spot,
  implied30, 30-minute move and t2 target against this folder's minutes table: **0 differences of 50 (fit) and 0 of 50
  (OOS)** on the trades, **0 and 0** on the features (`out/verify_fit.txt`, `out/verify_oos.txt`).

## 2. Definitions

- Cell: structure (call / put / condor) × short-strike rule (d10 / d15 / d20 / d25 / em1) × width (1 / 2) × management
  (hold, the primary; tp50, stop2x secondary) × signal (D1–2 = the t2 GBM decile ≤ 2 at the scan minute, the bottom 20 %
  by the registered cuts; D1 = decile 1), pooled over the 12 scan minutes; also per scan minute.
- The lift of a cell = Σ_s N_sig(s) · [mean(net | signal at s) − mean(net | all sessions at s)] / Σ_s N_sig(s): the
  signal's mean net against the TIME-OF-DAY-MATCHED unconditional mean (every session of the period at the same scan
  minute, the signal's sessions included — so the lift is 1 − share(signal at s) times the lift over the rest; the lift
  against the rest, D3–D10, is in the CSVs as `lift_vs_rest`), weighted by the signal's own mix of scan minutes. In $ a
  structure and in $ per $100 of max risk (the cross-structure yardstick; the pre-registration ranks on it).
- The 95 % CI of a lift is a paired session bootstrap: 2,000 draws of the period's sessions with replacement (seed
  20261016; one draw matrix for every cell of the pass), both means recomputed from the same drawn sessions. The CI of
  a cell's own mean $ (and of the unconditional benchmark's) uses the same draws. "Significant" (the benchmark) = the CI
  of the mean $ lies above zero.
- Per cell: N structures, sessions, mean $, % of max risk (max risk = width × 100 − credit × 100), median credit, win
  rate, average win / loss, full-loss share (net ≤ −95 % of max risk), p5 / p1 / worst $, worst session, total, profit
  factor, max drawdown and longest losing streak (the 1-lot sequence in session and entry order), CI, mean without the
  best five sessions, by year; friction (hold) = the legs' bid-ask crossed at entry plus fees as a share of the gross at
  the legs' mids with no fees (a condor's mid credit is its two verticals' at the same minute). The lift without the best
  five sessions drops the five sessions that contribute most to the lift.
- Trade rows at a minute with no score (no straddle at the minute) stay in "all" and are in neither signal set: fit 0
  rows, OOS 12 rows in one session.

## 3. The model refit against Hypothesis D's

`out/model_auc.csv`, `model_auc_oos.csv`, `hypd_spy_auc.csv`, `decile_rates.csv`, `decile_rates_oos.csv`, `logs/fit_model.log`.

| model (t2) | fit in-sample | fit OOF | cut 2024H2 | OOS 2025–26 | Hyp D's pooled model read on its SPY rows: fit OOF / cut / OOS | Hyp D as published (four products) |
|---|---|---|---|---|---|---|
| full GBM | 0.809 | **0.613** | 0.599 | **0.590** | 0.617 / 0.557 / 0.602 | 0.613 / 0.588 / 0.609 |
| full logistic | 0.635 | 0.627 | 0.642 | 0.639 | 0.622 / 0.627 / 0.650 | 0.621 / 0.640 / 0.647 |
| baseline (m, straddle/spot) | 0.651 | 0.576 | 0.595 | 0.582 | 0.574 / 0.582 / 0.577 | 0.575 / 0.601 / 0.594 |

The AUC matches Hypothesis D's: 0.613 fit out-of-fold against its 0.613 (0.617 on its SPY rows), 0.59 OOS against 0.60–0.61.
Base rate of t2 (the realized |30-minute move| exceeds the straddle-implied one) 0.310 fit, 0.326 cut; the registered cuts
0.187, 0.235, 0.271, 0.300, 0.330, 0.360, 0.398, 0.445, 0.514. Top features by gain: m, realized vol so far, implied30, the
day's range and move in ATR units. The bottom decile realizes t2 at **0.163** (fit OOF, n 3,014), **0.196** (cut, 927) and
**0.185** (OOS, 2,444) — the 18–24 % Hypothesis D reported; D2 0.232 / 0.253 / 0.262; D10 0.466 / 0.458 / 0.459. Decile
drift OOS by the registered cuts: D1 holds 7.7 % of 2025–2026 scan minutes and D10 13.4 % (the period scored higher). On
this test's 12 scan minutes D1–2 holds 22.4 % of fit, 23.1 % of cut and 18.7 % of OOS minutes, and it is late-day heavy
(15:00: 49 % of fit minutes / 31 % OOS; 15:30: 53 % / 41 %; 10:00: 3 % / 1 %; `out/cluster.txt`) — which is why the
baseline is time-of-day matched.

## 4. The pre-registration (`out/preregistered.md`, verbatim, written before any 2025–2026 trade row was read)

--- begin out/preregistered.md ---
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
--- end out/preregistered.md ---

## 5. The unconditional benchmark (the owner's), fit and OOS

`out/fit_uncond_pooled.csv`, `oos_uncond_pooled.csv`, `fit_uncond_byscan.csv`, `oos_uncond_byscan.csv`; `out/tables.md`.
Mean % of max risk a structure, fees in; CI = session bootstrap of the mean $; "sig" = that CI above zero.

### Pooled over the 12 scan minutes, hold (ranked by the fit lower bound in % of risk)

| structure | rule | w | fit N | mean $ | % risk | CI $ | sig | win | full-loss | wo5 $ | PF | friction | OOS N | mean $ | % risk | CI $ | sig | win | full-loss | wo5 $ | PF | max DD / streak | friction |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor | d25 | 2 | 6049 | 4.47 | 2.99 | [0.46, 8.38] | * | 0.72 | 0.078 | 3.79 | 1.20 | 0.51 | 5161 | 6.74 | 4.55 | [2.67, 10.70] | * | 0.73 | 0.096 | 6.01 | 1.28 | 6828 / 22 | 0.42 |
| condor | em1 | 2 | 5055 | 3.65 | 2.25 | [0.33, 7.10] | * | 0.81 | 0.045 | 3.08 | 1.22 | 0.56 | 4623 | 5.60 | 3.39 | [1.98, 9.00] | * | 0.82 | 0.064 | 4.99 | 1.32 | 5492 / 19 | 0.46 |
| condor | d20 | 2 | 5814 | 3.71 | 2.33 | [0.11, 7.27] | * | 0.77 | 0.055 | 3.16 | 1.20 | 0.56 | 5024 | 6.75 | 4.22 | [3.05, 10.09] | * | 0.80 | 0.067 | 6.18 | 1.36 | 5814 / 19 | 0.41 |
| put | d25 | 2 | 6218 | 3.04 | 1.75 | [-0.29, 6.00] |  | 0.85 | 0.040 | 2.71 | 1.22 | 0.44 | 5209 | 1.88 | 1.06 | [-1.51, 5.17] |  | 0.84 | 0.051 | 1.50 | 1.12 | 6269 / 12 | 0.56 |
| condor | d15 | 2 | 5115 | 2.71 | 1.59 | [-0.50, 5.82] |  | 0.83 | 0.038 | 2.28 | 1.18 | 0.63 | 4610 | 5.49 | 3.19 | [2.13, 8.63] | * | 0.86 | 0.048 | 5.08 | 1.39 | 5535 / 19 | 0.46 |
| put | d20 | 2 | 6103 | 2.07 | 1.17 | [-0.78, 4.68] |  | 0.89 | 0.029 | 1.81 | 1.19 | 0.53 | 5133 | 2.62 | 1.45 | [-0.22, 5.31] |  | 0.89 | 0.035 | 2.34 | 1.23 | 4809 / 12 | 0.48 |
| put | d10 | 2 | 3970 | 1.26 | 0.66 | [-0.82, 3.00] |  | 0.95 | 0.015 | 1.10 | 1.26 | 0.65 | 3667 | 1.41 | 0.74 | [-0.88, 3.34] |  | 0.96 | 0.016 | 1.25 | 1.28 | 4235 / 9 | 0.62 |
| put | em1 | 2 | 5781 | 1.83 | 1.02 | [-0.80, 4.24] |  | 0.90 | 0.027 | 1.56 | 1.19 | 0.56 | 5018 | 2.74 | 1.51 | [-0.15, 5.38] |  | 0.89 | 0.034 | 2.44 | 1.25 | 4751 / 12 | 0.47 |
| call | em1 | 2 | 5282 | 1.57 | 0.87 | [-0.88, 3.99] |  | 0.90 | 0.017 | 1.29 | 1.18 | 0.60 | 4739 | 2.67 | 1.45 | [0.04, 5.15] | * | 0.90 | 0.028 | 2.36 | 1.29 | 4829 / 15 | 0.47 |
| put | d15 | 2 | 5682 | 1.29 | 0.70 | [-1.06, 3.39] |  | 0.92 | 0.021 | 1.09 | 1.16 | 0.64 | 4885 | 2.46 | 1.33 | [-0.10, 4.67] |  | 0.93 | 0.024 | 2.26 | 1.32 | 4524 / 12 | 0.49 |
| call | d15 | 2 | 5471 | 1.20 | 0.65 | [-1.13, 3.45] |  | 0.90 | 0.016 | 0.98 | 1.14 | 0.66 | 4825 | 2.84 | 1.53 | [0.39, 5.04] | * | 0.91 | 0.022 | 2.63 | 1.36 | 4260 / 14 | 0.45 |
| call | d20 | 2 | 5977 | 1.36 | 0.77 | [-1.51, 4.10] |  | 0.85 | 0.025 | 1.08 | 1.12 | 0.63 | 5120 | 3.90 | 2.18 | [1.02, 6.66] | * | 0.88 | 0.032 | 3.60 | 1.34 | 5382 / 16 | 0.38 |
| call | d10 | 2 | 3926 | 0.46 | 0.24 | [-1.75, 2.53] |  | 0.94 | 0.011 | 0.28 | 1.08 | 0.83 | 3672 | 1.44 | 0.75 | [-0.86, 3.49] |  | 0.94 | 0.016 | 1.27 | 1.27 | 3159 / 9 | 0.62 |
| call | d25 | 2 | 6137 | 1.48 | 0.85 | [-1.91, 4.75] |  | 0.81 | 0.037 | 1.11 | 1.10 | 0.61 | 5218 | 4.73 | 2.73 | [1.42, 8.11] | * | 0.84 | 0.045 | 4.33 | 1.31 | 6202 / 17 | 0.34 |
| put | d25 | 1 | 6108 | 0.99 | 1.19 | [-1.04, 2.88] |  | 0.85 | 0.082 | 0.80 | 1.10 | 0.70 | 5129 | -0.21 | -0.28 | [-2.25, 1.76] |  | 0.84 | 0.097 | -0.42 | 0.98 | 7092 / 13 | 1.10 |
| condor | d10 | 2 | 3085 | 1.29 | 0.72 | [-2.18, 4.46] |  | 0.89 | 0.029 | 0.85 | 1.12 | 0.78 | 3095 | 2.40 | 1.33 | [-1.01, 5.53] |  | 0.90 | 0.037 | 2.03 | 1.22 | 5307 / 9 | 0.66 |
| call | em1 | 1 | 4607 | 0.23 | 0.28 | [-1.50, 1.85] |  | 0.89 | 0.049 | 0.05 | 1.03 | 0.91 | 4240 | 0.76 | 0.86 | [-0.92, 2.41] |  | 0.89 | 0.054 | 0.58 | 1.11 | 3277 / 14 | 0.76 |
| put | d20 | 1 | 5815 | 0.38 | 0.46 | [-1.48, 2.04] |  | 0.88 | 0.060 | 0.23 | 1.05 | 0.86 | 4907 | 0.23 | 0.26 | [-1.47, 1.83] |  | 0.88 | 0.064 | 0.07 | 1.03 | 3563 / 12 | 0.91 |
| call | d15 | 1 | 4816 | -0.02 | -0.02 | [-1.64, 1.53] |  | 0.89 | 0.046 | -0.16 | 1.00 | 1.01 | 4312 | 0.93 | 1.05 | [-0.64, 2.43] |  | 0.91 | 0.046 | 0.80 | 1.15 | 2894 / 14 | 0.71 |
| put | em1 | 1 | 5225 | 0.15 | 0.20 | [-1.71, 1.75] |  | 0.89 | 0.054 | -0.01 | 1.02 | 0.94 | 4662 | 0.34 | 0.38 | [-1.40, 2.01] |  | 0.89 | 0.064 | 0.17 | 1.04 | 3039 / 12 | 0.88 |
| put | d15 | 1 | 4814 | -0.14 | -0.15 | [-1.79, 1.31] |  | 0.91 | 0.044 | -0.28 | 0.98 | 1.07 | 4060 | 0.51 | 0.57 | [-1.07, 1.97] |  | 0.92 | 0.045 | 0.38 | 1.09 | 2453 / 11 | 0.82 |
| call | d20 | 1 | 5805 | -0.00 | 0.00 | [-1.85, 1.81] |  | 0.84 | 0.064 | -0.17 | 1.00 | 1.00 | 4941 | 1.73 | 2.02 | [-0.06, 3.50] |  | 0.87 | 0.068 | 1.55 | 1.21 | 3376 / 19 | 0.58 |
| put | d10 | 1 | 1594 | -0.16 | -0.16 | [-2.05, 1.43] |  | 0.93 | 0.034 | -0.40 | 0.96 | 1.07 | 1115 | 0.25 | 0.28 | [-1.77, 1.95] |  | 0.95 | 0.035 | -0.02 | 1.06 | 977 / 7 | 0.90 |
| condor | em1 | 1 | 4139 | 0.46 | 0.66 | [-1.78, 2.73] |  | 0.79 | 0.108 | 0.06 | 1.04 | 0.91 | 3993 | 0.93 | 1.21 | [-1.38, 3.03] |  | 0.79 | 0.126 | 0.53 | 1.07 | 3786 / 18 | 0.84 |
| condor | d25 | 1 | 5936 | 0.87 | 1.21 | [-1.46, 3.21] |  | 0.68 | 0.174 | 0.48 | 1.05 | 0.84 | 5032 | 1.91 | 2.74 | [-0.50, 4.27] |  | 0.70 | 0.194 | 1.49 | 1.11 | 4365 / 22 | 0.72 |
| call | d10 | 1 | 2239 | -0.36 | -0.39 | [-2.11, 1.28] |  | 0.92 | 0.035 | -0.54 | 0.93 | 1.18 | 2082 | 0.07 | 0.08 | [-1.62, 1.62] |  | 0.93 | 0.036 | -0.11 | 1.02 | 1296 / 7 | 0.97 |
| condor | d20 | 1 | 5438 | 0.42 | 0.57 | [-1.76, 2.70] |  | 0.74 | 0.128 | 0.08 | 1.03 | 0.92 | 4695 | 1.99 | 2.65 | [-0.29, 4.03] |  | 0.77 | 0.136 | 1.65 | 1.15 | 3417 / 18 | 0.70 |
| call | d25 | 1 | 6109 | -0.07 | -0.12 | [-2.11, 2.03] |  | 0.80 | 0.090 | -0.27 | 0.99 | 1.03 | 5149 | 2.08 | 2.49 | [0.02, 4.13] | * | 0.83 | 0.094 | 1.85 | 1.20 | 3917 / 18 | 0.54 |
| condor | d15 | 1 | 3988 | -0.08 | -0.07 | [-2.33, 2.14] |  | 0.81 | 0.094 | -0.39 | 0.99 | 1.02 | 3626 | 1.40 | 1.75 | [-0.84, 3.48] |  | 0.83 | 0.098 | 1.11 | 1.13 | 3269 / 18 | 0.77 |
| condor | d10 | 1 | 897 | -0.74 | -0.80 | [-4.29, 2.50] |  | 0.87 | 0.072 | -1.58 | 0.92 | 1.19 | 744 | 1.02 | 1.20 | [-2.43, 3.82] |  | 0.90 | 0.074 | 0.27 | 1.13 | 976 / 6 | 0.82 |

Three cells clear zero in fit, the 2-wide condors at 20 and 25 delta and at the straddle's edge (+2.3 to +3.0 % of max
risk, $3.65–4.47 a condor, win 72–81 %, full loss 4.5–7.8 %), and the same three clear it OOS at +3.4 to +4.6 % ($5.60–6.75),
joined OOS by the 15-delta condor, every 2-wide call vertical but the 10-delta, and the 1-wide 25-delta call (the 2025–2026 harvest was richer, as Hypothesis B found).
The 2-wide put verticals are positive in both periods but inside the noise (25-delta +1.75 % / +1.06 %); the 1-wides and
the 10-delta cells are within ±1 % of zero in both, several negative. Friction on the 20/25-delta and straddle-edge 2-wide condors is 41–56 % of the
gross at the mids (a $0.28–0.49 condor credit at the fill gives up $2.06–2.19 to the bid-ask and $2.60 in fees; 63–78 % at 10 and 15 delta in fit), 44–83 % on the 2-wide
verticals, 70–120 % on the 1-wides. Max drawdown of the 1-lot sequence OOS $5.5–6.8K on the condors on totals of
$26–35K; longest losing streak 19–22.

### By scan minute: significant cells of 30, and the strongest fit cell read OOS (nothing chosen OOS)

| scan | fit: significant of 30 | fit strongest | N | % risk | mean $ [CI] | OOS: significant of 30 | that cell OOS N | % risk | mean $ [CI] | sig | OOS strongest (for the record, not chosen) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10:00 | 0 | put d15 w2 | 527 | 0.73 | 1.30 [-2.45, 4.78] | 0 | 438 | 0.35 | 0.65 [-3.78, 4.78] |  | put d10 w2: 0.88% [-1.46, 4.33] |
| 10:30 | 0 | put d25 w2 | 529 | 2.65 | 4.59 [-0.04, 8.84] | 1 | 438 | 1.80 | 3.03 [-2.22, 8.02] |  | condor d20 w2: 4.03% [0.09, 11.84] |
| 11:00 | 1 | put d25 w2 | 527 | 2.79 | 4.68 [0.28, 8.83] | 0 | 438 | 0.46 | 0.81 [-4.80, 6.12] |  | condor d15 w2: 3.03% [-0.02, 9.76] |
| 11:30 | 2 | condor em1 w2 | 495 | 4.32 | 7.11 [2.92, 11.21] | 0 | 431 | 1.61 | 2.69 [-3.02, 8.26] |  | condor d15 w2: 2.71% [-0.51, 9.49] |
| 12:00 | 3 | put d10 w1 | 153 | 3.10 | 2.90 [0.80, 4.51] | 1 | 109 | 0.10 | 0.08 [-4.09, 3.65] |  | condor d20 w2: 4.28% [0.86, 12.23] |
| 12:30 | 0 | call em1 w2 | 480 | 0.85 | 1.57 [-1.60, 4.47] | 7 | 423 | 1.92 | 3.56 [-0.01, 6.92] |  | call d20 w1: 4.01% [1.19, 5.81] |
| 13:00 | 0 | put d10 w2 | 346 | 1.33 | 2.57 [-0.04, 4.59] | 12 | 322 | 1.86 | 3.55 [1.05, 5.59] | * | condor d25 w2: 7.24% [4.48, 16.76] |
| 13:30 | 2 | condor d25 w2 | 521 | 3.91 | 5.49 [0.18, 10.82] | 17 | 435 | 6.75 | 10.14 [4.37, 15.88] | * | condor d20 w2: 6.63% [5.57, 15.24] |
| 14:00 | 1 | condor d25 w2 | 513 | 3.34 | 5.01 [0.03, 9.87] | 12 | 434 | 6.77 | 10.21 [4.58, 15.63] | * | condor d25 w2: 6.77% [4.58, 15.63] |
| 14:30 | 7 | condor d25 w2 | 505 | 4.80 | 7.76 [3.40, 11.91] | 22 | 428 | 5.17 | 8.09 [2.50, 13.13] | * | condor d20 w2: 6.53% [6.22, 14.72] |
| 15:00 | 9 | condor d25 w1 | 435 | 8.47 | 5.91 [2.88, 8.85] | 9 | 388 | 7.41 | 5.21 [1.76, 8.55] | * | call d25 w1: 6.07% [2.69, 7.31] |
| 15:30 | 13 | condor d25 w1 | 365 | 7.35 | 5.29 [2.16, 8.39] | 12 | 341 | 2.76 | 1.74 [-2.16, 5.44] |  | condor d20 w2: 4.36% [2.30, 11.54] |

| scan | structures fit / OOS | fit significant | OOS significant | cells with mean > 0, fit / OOS |
|---|---|---|---|---|
| 10:00 | 14570 / 12096 | 0 | 0 | 7 / 16 |
| 10:30 | 14275 / 12089 | 0 | 1 | 23 / 22 |
| 11:00 | 13964 / 11836 | 1 | 0 | 16 / 20 |
| 11:30 | 13707 / 11789 | 2 | 0 | 22 / 22 |
| 12:00 | 13451 / 11522 | 3 | 1 | 27 / 24 |
| 12:30 | 13102 / 11302 | 0 | 7 | 15 / 22 |
| 13:00 | 12760 / 11056 | 0 | 12 | 23 / 28 |
| 13:30 | 12215 / 10618 | 2 | 17 | 24 / 30 |
| 14:00 | 11407 / 10190 | 1 | 12 | 25 / 30 |
| 14:30 | 10763 / 9486 | 7 | 22 | 26 / 29 |
| 15:00 | 9498 / 8986 | 9 | 9 | 26 / 28 |
| 15:30 | 7483 / 7716 | 13 | 12 | 27 / 30 |

Where it is strongest: in fit the afternoon — 14:30, 15:00 and 15:30 hold 29 of the fit's 38 significant scan cells, the
25-delta condors the strongest (2-wide 14:30 +4.8 % [$3.40, $11.91]; 1-wide 15:00 +8.5 % [$2.88, $8.85], 15:30 +7.4 %
[$2.16, $8.39]); before 13:30 only 11:30 (the straddle-edge condor, +4.3 % [$2.92, $11.21]) and 12:00 stand out. OOS the
strength moved earlier, 13:00–14:30 (12, 17, 12 and 22 significant cells; the 25-delta 2-wide condor 13:00 +7.2 %
[$4.48, $16.76], 13:30 +6.8 %, 14:00 +6.8 %), and the fit's strongest cells read: 14:30 condor d25 w2 +5.2 % OOS (clear);
15:00 condor d25 w1 +7.4 % (clear); 15:30 condor d25 w1 +2.8 % (not clear); 11:30 condor em1 w2 +1.6 % (not clear);
11:00 put d25 w2 +0.5 % (not); 12:00 put d10 w1 +0.1 % (not). The morning (10:00–11:00) is never significant in either
period. The scan ranking carries over for the afternoon condors and not for anything else.

### Every cell by scan minute, hold: mean % of max risk, fit / OOS (* = CI of the mean $ above zero)

| cell | 10:00 | 10:30 | 11:00 | 11:30 | 12:00 | 12:30 | 13:00 | 13:30 | 14:00 | 14:30 | 15:00 | 15:30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| call d10 w1 | -0.8 / -1.1 | -1.3 / +0.9 | -0.4 / -0.9 | -1.1 / -1.4 | -0.1 / +0.1 | +0.9 / -0.7 | -0.4 / -1.9 | -1.6 / +2.8* | +0.8 / +2.6 | -0.0 / +0.7 | +1.6 / +3.5* | +1.0 / +0.7 |
| call d10 w2 | -0.5 / +0.9 | +0.1 / +0.8 | -0.7 / +0.6 | +0.7 / +0.2 | +0.9 / +1.0 | +0.3 / -0.5 | +0.2 / -0.4 | -0.2 / +1.7* | +0.6 / +1.6* | +1.3 / +1.6 | +0.9 / +1.3 | +0.8 / +1.7* |
| call d15 w1 | -1.6 / +0.1 | -0.9 / -0.3 | -1.9 / -0.4 | +0.0 / +0.4 | +0.7 / -0.0 | -0.4 / +2.5* | +0.4 / +1.6 | +0.3 / +2.0 | +0.6 / +1.3 | +1.1 / +4.0* | +1.6 / +1.5 | +2.5* / +1.5 |
| call d15 w2 | -0.4 / +1.1 | +0.1 / +1.0 | -0.7 / +1.0 | +1.2 / +1.3 | +1.0 / +1.1 | +0.4 / +2.1* | +1.0 / +2.0* | +0.8 / +2.2* | +1.0 / +1.2 | +1.4 / +2.8* | +1.1 / +1.1 | +1.7* / +1.6* |
| call d20 w1 | -2.1 / -2.0 | -0.2 / -0.3 | -2.2 / +0.7 | -0.8 / +0.4 | -0.4 / +1.8 | -1.7 / +4.0* | +0.6 / +3.3* | +0.2 / +4.2* | +1.3 / +2.8* | +2.3 / +4.5* | +2.6* / +3.5* | +2.0 / +2.3 |
| call d20 w2 | -0.5 / -0.1 | +0.4 / +1.1 | -0.6 / +1.7 | +0.6 / +1.3 | +0.5 / +2.1 | -0.1 / +3.2* | +1.4 / +2.8* | +0.8 / +3.5* | +1.5 / +2.3* | +2.1* / +3.5* | +2.0* / +2.8* | +1.6 / +2.1* |
| call d25 w1 | -2.5 / -1.2 | -1.0 / -1.5 | -1.4 / +0.2 | -1.7 / +0.8 | -0.2 / +2.7 | -2.1 / +3.1 | -1.3 / +5.5* | +1.3 / +4.4* | +1.4 / +4.8* | +1.2 / +3.9* | +3.4* / +6.1* | +2.6 / +1.3 |
| call d25 w2 | -0.7 / +0.6 | +0.5 / +0.3 | -0.2 / +1.5 | +0.1 / +1.6 | +0.8 / +2.7 | -0.2 / +3.4* | +0.4 / +4.3* | +1.5 / +4.2* | +1.8 / +4.0* | +1.7 / +3.9* | +2.9* / +4.4* | +2.1* / +2.0 |
| call em1 w1 | -1.2 / -0.3 | -0.4 / -0.8 | -1.8 / +0.2 | +0.5 / -1.0 | -0.0 / -0.5 | +0.4 / +2.2 | +0.7 / +1.0 | +0.9 / +2.5 | +0.8 / +2.5 | +0.9 / +3.9* | +2.4 / +1.0 | +3.9* / +1.6 |
| call em1 w2 | -0.2 / +1.0 | +0.3 / +1.0 | -0.8 / +1.4 | +1.6 / +0.4 | +0.9 / +0.6 | +0.8 / +1.9 | +1.3 / +1.6 | +1.3 / +2.1* | +1.2 / +2.0* | +1.4 / +2.9* | +1.5 / +1.2 | +2.6* / +1.8* |
| condor d10 w1 | -5.0 / +0.5 | -1.5 / +2.5 | +0.3 / -3.9 | -2.2 / -3.4 | +2.5 / -1.5 | +5.0 / +4.4 | -0.2 / +5.9 | -4.0 / +2.2 | +6.5 / +6.9 | -1.2 / +4.4 | -3.1 / -1.9 | +5.2 / +6.3 |
| condor d10 w2 | -1.2 / +1.6 | +0.5 / +0.7 | +0.5 / +1.2 | +1.8 / +0.1 | +1.8 / +0.9 | +1.3 / -1.4 | +0.8 / +1.6 | -0.6 / +3.0* | +1.0 / +2.3 | +3.0 / +4.4* | +2.1 / +1.8 | -0.7 / +4.1* |
| condor d15 w1 | -2.3 / -1.4 | -0.5 / +0.4 | -1.1 / +0.5 | -0.0 / +1.7 | +1.9 / -0.2 | -1.4 / +2.6 | +1.4 / +3.3 | +1.4 / +3.7 | -2.1 / +3.6 | +1.4 / +7.2* | -0.2 / +1.3 | +5.8 / +2.3 |
| condor d15 w2 | +0.4 / +1.5 | +1.3 / +2.7 | +1.1 / +3.0 | +3.0* / +2.7 | +2.5* / +2.0 | +0.7 / +2.8 | +2.0 / +4.0* | +1.9 / +4.7* | +0.8 / +3.5* | +1.8 / +6.0* | +1.6 / +2.6 | +3.0 / +3.6* |
| condor d20 w1 | -3.2 / -3.5 | +1.4 / +1.3 | -1.4 / -1.0 | +0.8 / +0.3 | +1.0 / +2.9 | -2.4 / +4.4 | +0.4 / +4.8* | +0.1 / +6.0* | +0.9 / +4.7* | +3.9 / +6.8* | +3.4 / +4.0 | +6.5* / +3.5 |
| condor d20 w2 | +0.6 / +0.3 | +2.9 / +4.0* | +1.1 / +2.8 | +2.9 / +3.2 | +2.9 / +4.3* | +0.6 / +4.7* | +2.3 / +5.3* | +1.9 / +6.6* | +2.7 / +4.3* | +4.2* / +6.5* | +2.9* / +4.5* | +3.8* / +4.4* |
| condor d25 w1 | -5.1 / -3.4 | +0.5 / -2.2 | +0.8 / -1.1 | -0.6 / -0.3 | +0.4 / +3.1 | -3.2 / +3.1 | -0.7 / +7.2* | +3.0 / +6.7* | +2.2 / +7.1* | +4.7* / +3.4 | +8.5* / +7.4* | +7.4* / +2.8 |
| condor d25 w2 | -0.0 / +1.0 | +3.8 / +2.7 | +2.8 / +2.1 | +1.9 / +3.2 | +3.0 / +4.5 | +0.3 / +4.2* | +2.2 / +7.2* | +3.9* / +6.8* | +3.3* / +6.8* | +4.8* / +5.2* | +5.9* / +6.5* | +5.0* / +4.6* |
| condor em1 w1 | -2.2 / -0.9 | +1.4 / +0.4 | -1.5 / -1.1 | +1.8 / -1.8 | +1.7 / +0.3 | -0.4 / +1.7 | +1.8 / +2.4 | +1.9 / +3.4 | -0.0 / +3.4 | +0.4 / +6.1* | +2.8 / +1.6 | +6.3* / +3.8 |
| condor em1 w2 | +0.8 / +2.0 | +2.3 / +3.5 | +0.9 / +2.8 | +4.3* / +1.6 | +3.3* / +2.4 | +1.1 / +2.6 | +2.4 / +4.3* | +2.9* / +4.9* | +1.8 / +3.9* | +2.0 / +6.2* | +2.5 / +3.1* | +3.8* / +4.4* |
| put d10 w1 | -1.9 / +0.0 | +0.4 / -2.0 | -1.8 / -1.8 | -0.0 / +0.7 | +3.1* / +0.1 | -0.3 / +1.8 | +1.2 / +1.3 | -0.5 / +1.9 | +0.5 / +0.5 | +0.2 / +3.5* | -2.4 / -2.4 | -0.7 / +2.5 |
| put d10 w2 | -0.1 / +0.9 | +0.9 / -0.2 | +0.8 / +0.6 | +1.0 / +0.2 | +0.5 / +0.3 | +0.5 / -0.1 | +1.3 / +1.9* | +0.7 / +1.5* | +0.3 / +0.3 | +1.7* / +2.0* | -0.1 / +1.4 | -0.5 / +2.0* |
| put d15 w1 | -0.2 / -1.0 | +0.1 / +0.9 | +0.5 / +0.9 | -0.0 / +0.2 | +0.1 / -0.9 | -1.4 / -0.5 | -0.1 / +1.2 | +0.6 / +1.2 | -2.1 / +1.2 | -0.2 / +2.8* | +0.3 / +0.0 | +0.6 / +2.2 |
| put d15 w2 | +0.7 / +0.3 | +1.2 / +1.5 | +1.3 / +1.8 | +1.0 / +1.1 | +0.9 / +0.3 | -0.0 / +0.5 | +0.6 / +1.8 | +1.2 / +1.8* | -0.2 / +1.3 | +0.6 / +2.5* | +0.3 / +1.4 | +0.8 / +1.9* |
| put d20 w1 | -0.7 / -1.0 | +1.0 / +1.1 | +0.9 / -1.2 | +1.6 / -0.3 | +1.0 / +0.4 | -0.3 / -0.5 | -0.8 / +0.9 | -0.2 / +0.8 | +0.2 / +1.3 | +1.1 / +0.8 | +0.6 / +0.2 | +1.2 / +1.0 |
| put d20 w2 | +1.0 / +0.5 | +2.1 / +2.4 | +1.6 / +0.9 | +1.9 / +1.4 | +1.8 / +1.4 | +0.5 / +0.8 | +0.4 / +1.8 | +0.8 / +1.9 | +0.9 / +1.3 | +1.4 / +2.4* | +0.5 / +1.1 | +1.0 / +1.7 |
| put d25 w1 | -1.7 / -1.8 | +1.6 / -0.3 | +2.2 / -1.1 | +1.2 / -1.2 | +0.6 / -0.5 | -0.4 / -0.6 | +0.7 / +0.3 | +1.0 / +0.8 | +0.9 / +1.2 | +2.9* / -1.4 | +3.3* / +0.3 | +2.7* / +1.1 |
| put d25 w2 | +0.5 / +0.1 | +2.6 / +1.8 | +2.8* / +0.5 | +1.6 / +0.9 | +1.9 / +0.8 | +0.5 / +0.3 | +1.5 / +1.5 | +1.9 / +1.4 | +1.3 / +1.7 | +2.4* / +0.6 | +2.1* / +1.2 | +1.7* / +2.0 |
| put em1 w1 | -0.6 / -0.6 | +1.0 / +1.0 | +0.8 / -0.8 | +0.4 / -0.8 | +0.8 / +0.2 | -0.9 / -0.9 | -0.0 / +1.0 | +0.8 / +0.4 | -0.9 / +1.4 | -0.2 / +1.6 | +0.4 / +0.7 | +1.2 / +2.8 |
| put em1 w2 | +0.9 / +0.8 | +1.8 / +2.2 | +1.4 / +1.1 | +1.5 / +1.2 | +1.5 / +1.3 | +0.1 / +0.5 | +0.8 / +1.8 | +1.4 / +1.7 | +0.4 / +1.3 | +0.7 / +2.5* | +0.3 / +1.6 | +1.0 / +2.4* |

### Management

Hold beats the 50 % buy-back and the 2× stop on every one of the 30 structure cells in both periods (`out/tables.md`,
"Management"): tp50 is −0.5 to −6.4 % of risk everywhere; stop2x is negative everywhere but the 2-wide 20/25-delta
condors (fit +0.3 / +1.6 %, OOS −0.1 / +1.1 %, against hold's +2.3 / +3.0 % and +4.2 / +4.6 %). As in Hypothesis B: on a
$0.10–0.50 credit the exit pays a second crossing of the spread and the fees for nothing.

## 6. The lift of the volatility model's bottom deciles

`out/fit_lift_cells.csv`, `oos_lift_cells.csv`, `fit_lift_byscan.csv`, `oos_lift_byscan.csv`, `tables.md`, `notes_tables.md`.

### Fit, 2022-11-11 → 2024-12-31 (530 sessions; the pre-registration's read)

- Hold, 60 cells (3 structures × 5 rules × 2 widths × D1–2 / D1): **no cell's lift CI excludes zero in % of risk or in $**
  (0 of 60; none below zero either); 42 point estimates positive, 15 positive without the best five sessions, 0 lifts
  against the rest (D3–D10) clear of zero. The put cells carry the positive point estimates (−0.1 to +2.5 % of risk), the
  call cells are flat to negative (−1.1 to +0.8 %), the condors between (−2.1 to +4.0 %, the widest intervals).
- The pick by the pre-registered rule (the highest lower bound among qualifying cells): **D1–2, put vertical, 15-delta,
  2-wide, hold** — N 1,169 in 377 sessions, cell +1.31 % of risk ($2.42, CI [−$1.87, +$5.91]), time-matched +0.59 %, lift
  **+0.72 % [−0.99, +2.20]**, $+1.32 [−1.85, +4.04], +$0.58 without the best five sessions, vs the rest $+2.20 [−1.67,
  +5.79], by year 2022 +$3.95 (n 97), 2023 +$2.13 (420), 2024 +$0.17 (652); win 93.3 %, full loss 1.8 %, worst session
  2024-12-18 −$1,482, PF 1.36, max drawdown $1,599 / streak 10, friction 49 % of the gross. By scan minute the lift is
  clear only at 14:30 (+$5.67 [+1.30, +9.69]) and negative at 10:00, 10:30, 12:30, 13:00 and 14:00. By month 18 of 26
  positive, −$1.03 without the five best months: the lift's total is −$1,146 in 2023-09 and −$1,426 in 2024-12 alone.
- The only fit lifts clear of zero are three stop2x cells (D1–2 put d15 w1 +1.15 % [+0.23, +2.07]; put d15 w2 +0.73 %
  [+0.09, +1.39]; put em1 w1 +1.19 % [+0.01, +2.35]) — lifts on a negative base (the cells themselves −1.4 to −0.1 % of
  risk, the time-matched stop2x sell −2.6 to −0.9 %): the signal loses less on a losing management. Recorded as secondary;
  OOS all three are −0.3 to −0.1 % [through zero].

### OOS, 2025-01-02 → 2026-10-09 (441 sessions), FOR THE RECORD ONLY — labelled not pre-registrable

- The pick (D1–2 put d15 w2 hold): N 904 in 273 sessions, cell **+2.89 %** of risk ($5.34, CI [+$2.43, +$7.75]),
  time-matched +1.43 %, lift **+1.46 % [+0.05, +2.71]**, $+2.69 [+0.06, +4.99], +$1.98 without the best five sessions, vs the
  rest $+3.47 [+0.18, +6.40], 2025 +$3.36 (n 600) / 2026 +$1.23 (304); win 94.2 %, full loss 1.3 % (vs 2.4 % at every
  minute), worst session 2026-06-17 −$633, PF 2.10, drawdown $785 / streak 4, friction 30 %. It would pass the OOS "edge"
  rule written in the pre-registration (both lift intervals above zero by $0.06 and 0.05 points, lift > 0 without the best
  five, the cell's own CI above zero, both years positive) — by a hair, and after the fit said the lift was noise; by scan
  it is clear at 13:30 and 14:00 only (and at 10:00 on five rows), by month 17 of 22 positive and +$0.72 without the five
  best months.
- The grid: **37 of 60 hold cells' lift CIs clear zero OOS** (none below), all 60 point estimates positive, 59 positive
  without the best five sessions, 38 clear against the rest. The large ones are the D1 condors and calls, not the puts:
  D1 condor d20 w2 lift +9.0 % of risk [+5.3, +12.3], $+13.87 [+8.31, +18.88], +$10.71 without the best five, 2025 +$14.30 /
  2026 +$12.35, the cell 13.7 % of risk against 4.7 % time-matched, full loss 2.5 % against 6.7 %; D1 condor d25 w1 +14.8 %
  [+6.7, +22.2]; D1 condor d25 w2 +11.1 % [+4.8, +16.7]; D1 call d25 w1 +8.2 % [+4.5, +11.5]; D1–2 condor em1 w2 +4.2 %
  [+1.6, +6.8]; D1–2 condor d25 w2 +4.2 % [+0.3, +8.0].
- The same cells in fit: D1 condor d20 w2 +0.6 % [−5.4, +5.9], −$2.80 without the best five sessions, −$5.36 without the
  five best months (the lift's total −$1,124 in 2022-11, −$1,121 in 2023-09, −$1,186 in 2023-12, −$964 in 2024-12), full
  loss 6.6 % against 5.5 % — the signal rows lost MORE than the time-matched sell; D1 condor d25 w1 +4.0 % [−4.5, +11.9],
  +$0.28 without the best five; D1 condor d25 w2 +1.5 % [−5.3, +7.8], −$2.26; D1 call d25 w1 +0.8 % [−4.9, +5.7], −$0.66;
  D1–2 condor em1 w2 +0.4 % [−3.4, +3.8], −$1.87. Nothing in the fit period picked these cells out; a tuner reading the
  grid in 2024 would have taken the puts.

### Every hold cell, fit and OOS

| signal | structure | rule | w | fit N | sess. | cell %risk | tod %risk | lift %risk [95% CI] | lift $ [CI] | wo5 $ | OOS N | sess. | cell %risk | tod %risk | lift %risk [CI] (* clear) | lift $ [CI] | wo5 $ | 2025 / 2026 $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1-2 | put | d15 | 2 | 1169 | 377 | 1.31 | 0.59 | +0.72 [-0.99, +2.20] | +1.32 [-1.85, +4.04] | +0.58 | 904 | 273 | 2.89 | 1.43 | +1.46 [+0.05, +2.71]* | +2.69 [+0.06, +4.99] | +1.98 | +3.4 / +1.2 |
| D1-2 | put | em1 | 2 | 1201 | 380 | 1.70 | 0.86 | +0.85 [-1.14, +2.53] | +1.55 [-2.01, +4.53] | +0.57 | 933 | 274 | 2.98 | 1.61 | +1.37 [-0.51, +3.10] | +2.44 [-0.92, +5.56] | +1.33 | +3.0 / +1.1 |
| D1-2 | put | em1 | 1 | 1025 | 344 | 1.77 | 0.22 | +1.55 [-1.14, +3.91] | +1.41 [-0.96, +3.51] | +0.79 | 866 | 269 | 1.89 | 0.68 | +1.21 [-1.42, +3.60] | +1.06 [-1.24, +3.17] | +0.35 | +1.5 / -0.1 |
| D1-2 | put | d20 | 2 | 1333 | 398 | 1.80 | 1.01 | +0.78 [-1.18, +2.49] | +1.43 [-2.07, +4.43] | +0.51 | 963 | 282 | 3.11 | 1.48 | +1.62 [-0.22, +3.43] | +2.87 [-0.40, +6.14] | +1.84 | +3.3 / +1.7 |
| D1-2 | put | d20 | 1 | 1223 | 378 | 1.84 | 0.56 | +1.29 [-1.38, +3.61] | +1.16 [-1.13, +3.18] | +0.62 | 925 | 281 | 2.00 | 0.41 | +1.59 [-0.93, +4.03] | +1.37 [-0.86, +3.51] | +0.71 | +1.5 / +0.7 |
| D1-2 | put | d15 | 1 | 929 | 331 | 1.25 | -0.12 | +1.36 [-1.44, +3.65] | +1.23 [-1.32, +3.32] | +0.73 | 733 | 251 | 2.81 | 0.82 | +1.99 [+0.08, +3.74]* | +1.79 [+0.04, +3.40] | +1.33 | +2.5 / +0.1 |
| D1-2 | put | d25 | 2 | 1386 | 405 | 2.58 | 1.77 | +0.80 [-1.63, +2.81] | +1.40 [-2.67, +4.82] | +0.25 | 978 | 286 | 2.78 | 1.18 | +1.60 [-1.14, +4.08] | +2.79 [-1.83, +7.04] | +1.30 | +3.4 / +0.4 |
| D1-2 | put | d25 | 1 | 1339 | 398 | 3.10 | 1.72 | +1.39 [-1.67, +4.00] | +1.18 [-1.34, +3.34] | +0.52 | 963 | 287 | 1.78 | 0.02 | +1.76 [-1.54, +4.81] | +1.49 [-1.29, +4.03] | +0.61 | +1.8 / +0.1 |
| D1-2 | put | d10 | 2 | 689 | 262 | 0.77 | 0.59 | +0.18 [-2.05, +1.86] | +0.33 [-3.89, +3.51] | -0.41 | 628 | 216 | 2.35 | 0.95 | +1.39 [+0.27, +2.46]* | +2.66 [+0.51, +4.70] | +2.19 | +3.4 / +1.8 |
| D1 | put | d25 | 1 | 690 | 253 | 4.25 | 1.72 | +2.53 [-2.34, +6.75] | +2.13 [-1.87, +5.64] | +0.99 | 454 | 180 | 3.41 | 0.05 | +3.36 [-2.26, +8.16] | +2.87 [-1.78, +6.85] | +1.34 | +5.2 / -2.3 |
| D1-2 | call | d15 | 2 | 1108 | 359 | 0.84 | 0.98 | -0.13 [-2.46, +1.71] | -0.23 [-4.43, +3.17] | -1.10 | 886 | 270 | 2.57 | 1.62 | +0.95 [-0.50, +2.20] | +1.68 [-1.04, +3.99] | +0.81 | +1.8 / +0.7 |
| D1-2 | call | d15 | 1 | 954 | 330 | 1.12 | 0.67 | +0.45 [-2.50, +2.89] | +0.42 [-2.21, +2.62] | -0.13 | 770 | 253 | 2.55 | 1.41 | +1.14 [-0.99, +2.95] | +1.00 [-0.89, +2.63] | +0.42 | +1.0 / +0.8 |
| D1-2 | call | d20 | 2 | 1293 | 395 | 1.06 | 1.18 | -0.12 [-2.50, +1.83] | -0.24 [-4.43, +3.25] | -1.35 | 954 | 279 | 3.89 | 2.49 | +1.40 [-0.38, +3.03] | +2.36 [-0.87, +5.27] | +1.18 | +2.6 / +1.6 |
| D1 | put | d20 | 2 | 692 | 253 | 1.99 | 1.03 | +0.96 [-2.58, +3.84] | +1.72 [-4.56, +6.84] | +0.12 | 451 | 179 | 4.26 | 1.50 | +2.76 [+0.10, +5.14]* | +4.98 [+0.27, +9.23] | +3.30 | +6.5 / +1.8 |
| D1 | put | d25 | 2 | 718 | 261 | 3.11 | 1.77 | +1.34 [-2.74, +4.85] | +2.33 [-4.67, +8.27] | +0.29 | 459 | 181 | 3.94 | 1.20 | +2.74 [-1.98, +6.70] | +4.81 [-3.18, +11.50] | +2.18 | +8.3 / -2.7 |
| D1-2 | call | d20 | 1 | 1242 | 389 | 1.01 | 0.80 | +0.21 [-2.75, +2.75] | +0.19 [-2.33, +2.40] | -0.47 | 915 | 274 | 4.55 | 2.68 | +1.87 [-0.48, +3.97] | +1.56 [-0.46, +3.37] | +0.87 | +1.5 / +1.6 |
| D1-2 | condor | d15 | 2 | 977 | 333 | 2.41 | 1.80 | +0.61 [-2.76, +3.53] | +1.05 [-4.54, +5.84] | -0.80 | 842 | 259 | 6.75 | 3.40 | +3.35 [+1.18, +5.31]* | +5.55 [+1.91, +8.88] | +3.98 | +6.0 / +3.7 |
| D1-2 | condor | d20 | 2 | 1225 | 383 | 3.21 | 2.69 | +0.52 [-2.81, +3.56] | +0.83 [-4.28, +5.47] | -1.35 | 937 | 274 | 8.55 | 4.62 | +3.93 [+1.17, +6.64]* | +5.87 [+1.58, +10.12] | +3.68 | +6.7 / +3.5 |
| D1-2 | call | em1 | 2 | 1042 | 343 | 0.87 | 1.27 | -0.40 [-2.85, +1.58] | -0.74 [-5.14, +2.83] | -1.89 | 874 | 268 | 3.27 | 1.57 | +1.70 [+0.08, +3.14] | +2.92 [-0.03, +5.58] | +1.82 | +3.1 / +2.0 |
| D1 | put | d15 | 2 | 614 | 229 | 1.17 | 0.62 | +0.56 [-2.92, +3.17] | +1.00 [-5.39, +5.84] | -0.28 | 429 | 172 | 3.41 | 1.44 | +1.97 [+0.11, +3.57]* | +3.60 [+0.14, +6.61] | +2.39 | +5.2 / +0.6 |
| D1-2 | call | d25 | 2 | 1352 | 400 | 1.14 | 1.40 | -0.26 [-2.96, +2.07] | -0.45 [-5.01, +3.54] | -1.82 | 975 | 285 | 4.64 | 3.07 | +1.58 [-0.71, +3.56] | +2.50 [-1.42, +5.81] | +0.84 | +2.3 / +2.8 |
| D1 | put | em1 | 2 | 623 | 233 | 1.75 | 0.89 | +0.86 [-2.96, +3.81] | +1.53 [-5.25, +6.82] | -0.21 | 438 | 174 | 4.01 | 1.64 | +2.37 [-0.37, +4.80] | +4.26 [-0.54, +8.56] | +2.45 | +6.1 / +0.6 |
| D1-2 | condor | d25 | 1 | 1281 | 390 | 4.98 | 3.08 | +1.90 [-3.07, +6.63] | +1.34 [-1.90, +4.41] | -0.11 | 945 | 282 | 8.45 | 3.80 | +4.64 [-0.76, +9.69] | +2.93 [-0.58, +6.26] | +1.08 | +3.1 / +2.0 |
| D1-2 | call | d25 | 1 | 1350 | 401 | 1.09 | 0.84 | +0.24 [-3.12, +3.21] | +0.21 [-2.55, +2.64] | -0.56 | 962 | 283 | 4.96 | 3.11 | +1.86 [-1.15, +4.44] | +1.45 [-1.01, +3.56] | +0.50 | +1.3 / +1.8 |
| D1-2 | call | d10 | 2 | 722 | 268 | -0.06 | 0.48 | -0.54 [-3.20, +1.49] | -1.03 [-6.00, +2.81] | -1.92 | 642 | 219 | 2.12 | 0.88 | +1.24 [+0.28, +2.26]* | +2.34 [+0.49, +4.28] | +1.73 | +2.8 / +0.9 |
| D1-2 | call | d10 | 1 | 445 | 191 | 0.26 | -0.04 | +0.30 [-3.21, +3.04] | +0.29 [-2.95, +2.82] | -0.46 | 338 | 143 | 2.37 | 0.60 | +1.78 [-0.21, +3.67] | +1.64 [-0.22, +3.42] | +0.98 | +2.1 / +0.6 |
| D1 | put | d20 | 1 | 625 | 230 | 2.10 | 0.60 | +1.50 [-3.22, +5.34] | +1.35 [-2.72, +4.62] | +0.36 | 434 | 175 | 3.46 | 0.43 | +3.03 [-0.90, +6.44] | +2.69 [-0.73, +5.67] | +1.61 | +3.7 / +0.5 |
| D1-2 | condor | d20 | 1 | 1096 | 355 | 3.21 | 1.72 | +1.49 [-3.23, +5.78] | +1.24 [-2.19, +4.33] | -0.11 | 877 | 270 | 8.57 | 3.60 | +4.97 [+1.10, +8.60]* | +3.58 [+0.72, +6.29] | +2.24 | +3.8 / +2.9 |
| D1 | put | em1 | 1 | 536 | 201 | 1.83 | 0.26 | +1.57 [-3.31, +5.36] | +1.42 [-2.81, +4.71] | +0.30 | 412 | 168 | 2.95 | 0.74 | +2.21 [-2.24, +5.98] | +1.95 [-1.90, +5.27] | +0.75 | +3.6 / -1.2 |
| D1-2 | condor | em1 | 2 | 957 | 327 | 2.94 | 2.52 | +0.42 [-3.35, +3.75] | +0.62 [-5.43, +5.94] | -1.87 | 850 | 259 | 7.84 | 3.62 | +4.22 [+1.59, +6.81]* | +6.51 [+2.30, +10.58] | +4.23 | +7.3 / +4.0 |
| D1-2 | condor | d25 | 2 | 1321 | 394 | 4.13 | 3.70 | +0.43 [-3.51, +4.09] | +0.60 [-4.86, +5.64] | -1.99 | 969 | 283 | 9.29 | 5.04 | +4.24 [+0.28, +8.03]* | +5.73 [+0.30, +11.10] | +2.59 | +6.4 / +3.2 |
| D1-2 | call | em1 | 1 | 886 | 313 | 0.70 | 1.08 | -0.38 [-3.55, +2.34] | -0.31 [-3.14, +2.10] | -1.09 | 763 | 250 | 3.78 | 1.29 | +2.49 [+0.33, +4.43]* | +2.13 [+0.19, +3.85] | +1.43 | +2.3 / +1.7 |
| D1-2 | condor | d15 | 1 | 707 | 265 | 1.91 | 0.63 | +1.28 [-3.84, +5.94] | +1.09 [-2.95, +4.79] | -0.33 | 628 | 218 | 7.91 | 2.38 | +5.53 [+2.24, +8.42]* | +4.46 [+1.80, +6.82] | +3.36 | +4.3 / +4.4 |
| D1 | put | d15 | 1 | 499 | 191 | 0.90 | -0.11 | +1.00 [-3.92, +4.78] | +0.91 [-3.56, +4.38] | +0.02 | 362 | 155 | 3.23 | 0.87 | +2.36 [-0.49, +4.77] | +2.11 [-0.54, +4.33] | +1.30 | +3.1 / -0.1 |
| D1 | call | d20 | 2 | 665 | 248 | 1.21 | 1.15 | +0.07 [-4.13, +3.35] | +0.13 [-7.20, +5.84] | -1.84 | 448 | 178 | 7.33 | 2.51 | +4.81 [+2.90, +6.51]* | +8.42 [+4.99, +11.47] | +6.83 | +7.4 / +10.0 |
| D1-2 | put | d10 | 1 | 301 | 116 | 0.31 | 0.03 | +0.28 [-4.14, +3.57] | +0.25 [-3.89, +3.31] | -0.74 | 239 | 98 | 1.95 | 0.79 | +1.17 [-1.18, +3.53] | +1.09 [-1.12, +3.33] | +0.31 | +1.4 / +0.1 |
| D1 | put | d10 | 2 | 385 | 151 | 0.58 | 0.58 | +0.01 [-4.26, +2.94] | -0.02 [-8.12, +5.54] | -1.29 | 306 | 124 | 3.15 | 0.99 | +2.15 [+1.12, +3.25]* | +4.10 [+2.14, +6.21] | +3.37 | +5.2 / +2.5 |
| D1 | call | d20 | 1 | 646 | 244 | 1.23 | 0.75 | +0.48 [-4.47, +4.60] | +0.43 [-3.72, +3.95] | -0.74 | 430 | 174 | 9.40 | 2.75 | +6.65 [+4.10, +9.00]* | +5.68 [+3.49, +7.69] | +4.79 | +5.2 / +6.5 |
| D1 | condor | d25 | 1 | 664 | 245 | 7.10 | 3.12 | +3.97 [-4.52, +11.94] | +2.82 [-2.54, +7.67] | +0.28 | 445 | 179 | 18.67 | 3.88 | +14.79 [+6.67, +22.18]* | +9.63 [+4.55, +14.22] | +6.91 | +10.6 / +7.2 |
| D1 | call | d25 | 2 | 699 | 256 | 1.49 | 1.39 | +0.10 [-4.55, +4.10] | +0.15 [-7.63, +6.82] | -2.26 | 456 | 181 | 9.27 | 3.08 | +6.19 [+3.40, +8.58]* | +10.37 [+5.76, +14.36] | +8.19 | +8.3 / +14.2 |
| D1 | call | d15 | 2 | 579 | 220 | 0.57 | 0.98 | -0.41 [-4.56, +2.80] | -0.73 [-8.35, +5.14] | -2.28 | 419 | 167 | 5.03 | 1.65 | +3.38 [+1.91, +4.82]* | +6.17 [+3.47, +8.86] | +5.06 | +5.3 / +7.0 |
| D1 | call | d25 | 1 | 704 | 255 | 1.71 | 0.86 | +0.84 [-4.88, +5.67] | +0.68 [-3.95, +4.58] | -0.66 | 449 | 180 | 11.34 | 3.13 | +8.21 [+4.49, +11.50]* | +6.70 [+3.78, +9.36] | +5.50 | +5.2 / +9.5 |
| D1-2 | condor | em1 | 1 | 735 | 270 | 2.19 | 1.47 | +0.72 [-4.92, +5.64] | +0.66 [-3.55, +4.42] | -1.17 | 714 | 237 | 7.66 | 1.99 | +5.67 [+1.40, +9.64]* | +4.28 [+1.04, +7.26] | +2.73 | +4.6 / +3.0 |
| D1 | call | d15 | 1 | 516 | 207 | 0.60 | 0.69 | -0.09 [-5.10, +3.99] | -0.06 [-4.54, +3.58] | -1.04 | 367 | 152 | 6.05 | 1.47 | +4.57 [+2.45, +6.58]* | +4.10 [+2.15, +5.90] | +3.45 | +3.7 / +4.7 |
| D1 | call | em1 | 2 | 546 | 206 | 0.67 | 1.28 | -0.62 [-5.19, +2.93] | -1.14 [-9.34, +5.28] | -3.21 | 413 | 167 | 5.53 | 1.58 | +3.94 [+2.18, +5.55]* | +6.98 [+3.79, +9.92] | +5.40 | +5.9 / +8.5 |
| D1 | condor | d25 | 2 | 683 | 252 | 5.18 | 3.70 | +1.47 [-5.26, +7.78] | +2.24 [-6.91, +10.67] | -2.26 | 455 | 180 | 16.20 | 5.08 | +11.12 [+4.76, +16.74]* | +15.47 [+6.92, +22.96] | +10.78 | +17.1 / +11.4 |
| D1 | call | d10 | 1 | 271 | 121 | -0.14 | -0.06 | -0.08 [-5.41, +3.93] | -0.05 [-4.97, +3.65] | -1.33 | 177 | 76 | 3.77 | 0.67 | +3.10 [+0.61, +5.30]* | +2.87 [+0.53, +4.93] | +1.96 | +3.1 / +2.3 |
| D1 | condor | d20 | 2 | 635 | 238 | 3.32 | 2.71 | +0.61 [-5.44, +5.89] | +1.00 [-8.02, +8.99] | -2.80 | 441 | 176 | 13.69 | 4.68 | +9.01 [+5.33, +12.29]* | +13.87 [+8.31, +18.88] | +10.71 | +14.3 / +12.3 |
| D1-2 | condor | d10 | 2 | 498 | 191 | 0.24 | 0.99 | -0.75 [-5.69, +3.41] | -1.41 [-10.22, +6.06] | -3.89 | 517 | 181 | 5.03 | 1.65 | +3.38 [+1.43, +5.16]* | +6.09 [+2.55, +9.35] | +4.85 | +7.1 / +4.1 |
| D1 | call | d10 | 2 | 408 | 157 | -0.65 | 0.45 | -1.10 [-5.72, +2.40] | -2.09 [-10.84, +4.53] | -3.73 | 316 | 126 | 3.28 | 0.89 | +2.40 [+1.11, +3.76]* | +4.53 [+2.09, +7.11] | +3.69 | +4.5 / +4.0 |
| D1 | condor | d15 | 2 | 517 | 197 | 1.99 | 1.85 | +0.13 [-6.05, +5.25] | +0.21 [-10.17, +8.79] | -2.99 | 400 | 156 | 9.99 | 3.45 | +6.54 [+3.93, +8.84]* | +10.93 [+6.68, +14.78] | +8.74 | +10.8 / +10.2 |
| D1 | put | d10 | 1 | 195 | 73 | 0.03 | 0.15 | -0.11 [-6.41, +4.62] | -0.13 [-6.05, +4.30] | -1.70 | 125 | 49 | 3.71 | 0.68 | +3.03 [+0.84, +5.32]* | +2.84 [+0.76, +5.01] | +1.91 | +2.8 / +2.6 |
| D1 | condor | em1 | 2 | 507 | 194 | 3.02 | 2.58 | +0.44 [-6.45, +6.46] | +0.49 [-10.56, +10.06] | -3.81 | 402 | 162 | 11.49 | 3.68 | +7.81 [+4.15, +11.13]* | +12.15 [+6.54, +17.35] | +8.81 | +12.2 / +11.0 |
| D1 | condor | d20 | 1 | 566 | 216 | 3.14 | 1.77 | +1.37 [-6.54, +8.59] | +1.25 [-4.31, +6.36] | -1.17 | 415 | 170 | 15.69 | 3.71 | +11.97 [+6.41, +16.83]* | +8.80 [+4.84, +12.33] | +6.87 | +9.3 / +7.6 |
| D1 | call | em1 | 1 | 480 | 190 | 0.08 | 1.06 | -0.98 [-6.75, +3.80] | -0.85 [-5.98, +3.34] | -2.25 | 364 | 152 | 7.14 | 1.34 | +5.80 [+3.54, +7.90]* | +5.07 [+3.06, +6.91] | +4.19 | +4.7 / +5.5 |
| D1-2 | condor | d10 | 1 | 207 | 76 | 0.34 | 0.34 | +0.00 [-8.03, +5.91] | -0.00 [-6.86, +5.08] | -3.31 | 159 | 65 | 4.60 | 1.88 | +2.73 [-1.80, +6.37] | +2.33 [-1.61, +5.49] | -0.07 | +1.9 / +2.9 |
| D1 | condor | d15 | 1 | 397 | 157 | 1.12 | 0.72 | +0.40 [-8.25, +8.10] | +0.42 [-6.49, +6.49] | -2.01 | 312 | 127 | 12.51 | 2.56 | +9.95 [+6.42, +13.24]* | +8.05 [+5.22, +10.70] | +6.65 | +7.3 / +9.1 |
| D1 | condor | em1 | 1 | 409 | 158 | 1.74 | 1.51 | +0.23 [-8.97, +8.61] | +0.26 [-6.54, +6.59] | -2.86 | 345 | 144 | 12.58 | 2.12 | +10.45 [+4.27, +15.65]* | +7.90 [+3.38, +11.80] | +5.69 | +8.4 / +6.3 |
| D1 | condor | d10 | 2 | 296 | 103 | -1.14 | 0.94 | -2.08 [-10.39, +4.56] | -3.85 [-18.75, +8.04] | -8.31 | 256 | 96 | 7.19 | 1.66 | +5.53 [+3.38, +7.65]* | +9.93 [+6.04, +13.73] | +8.13 | +11.2 / +7.5 |
| D1 | condor | d10 | 1 | 147 | 51 | -0.20 | 0.33 | -0.54 [-10.64, +7.12] | -0.46 [-9.05, +6.14] | -5.38 | 92 | 33 | 9.69 | 1.62 | +8.07 [+4.18, +11.81]* | +6.98 [+3.59, +10.25] | +4.94 | +6.3 / +8.0 |

### The managed cells (secondary)

### stop2x: the six best fit lower bounds, with the cell's own mean (the managed cells are negative unconditionally)

| signal | structure | rule | w | fit N | cell %risk | tod %risk | lift %risk [CI] | wo5 $ | OOS N | cell %risk | tod %risk | lift %risk [CI] | wo5 $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1-2 | put | d15 | 1 | 929 | -1.44 | -2.59 | +1.15 [+0.23, +2.07] | +0.55 | 733 | -2.97 | -2.65 | -0.32 [-1.39, +0.70] | -0.86 |
| D1-2 | put | d15 | 2 | 1169 | -0.12 | -0.85 | +0.73 [+0.09, +1.39] | +0.62 | 904 | -0.76 | -0.72 | -0.05 [-0.82, +0.68] | -0.91 |
| D1-2 | put | em1 | 1 | 1025 | -1.20 | -2.38 | +1.19 [+0.01, +2.35] | +0.46 | 866 | -2.19 | -2.13 | -0.06 [-1.43, +1.28] | -0.73 |
| D1-2 | put | em1 | 2 | 1201 | 0.04 | -0.67 | +0.71 [-0.13, +1.54] | +0.33 | 933 | -0.41 | -0.42 | +0.01 [-1.06, +1.02] | -1.06 |
| D1-2 | put | d10 | 2 | 689 | -0.78 | -1.18 | +0.40 [-0.20, +0.97] | +0.02 | 628 | -1.12 | -1.14 | +0.02 [-0.59, +0.60] | -0.59 |
| D1 | put | d15 | 1 | 499 | -1.27 | -2.60 | +1.34 [-0.22, +2.88] | +0.40 | 362 | -3.46 | -2.61 | -0.85 [-2.57, +0.90] | -1.88 |

### tp50: the six best fit lower bounds, with the cell's own mean (the managed cells are negative unconditionally)

| signal | structure | rule | w | fit N | cell %risk | tod %risk | lift %risk [CI] | wo5 $ | OOS N | cell %risk | tod %risk | lift %risk [CI] | wo5 $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | put | d25 | 1 | 690 | 1.02 | -2.29 | +3.32 [-0.25, +6.32] | +1.82 | 454 | -0.76 | -3.66 | +2.90 [-2.24, +7.07] | +0.95 |
| D1-2 | put | d25 | 1 | 1339 | -0.59 | -2.31 | +1.72 [-0.35, +3.68] | +0.87 | 963 | -2.12 | -3.70 | +1.58 [-1.13, +4.07] | +0.48 |
| D1-2 | put | d20 | 1 | 1223 | -1.30 | -2.90 | +1.61 [-0.42, +3.45] | +0.96 | 925 | -1.86 | -3.01 | +1.16 [-0.89, +3.15] | +0.33 |
| D1-2 | put | d20 | 2 | 1333 | -0.24 | -1.10 | +0.86 [-0.71, +2.18] | +0.86 | 963 | -0.01 | -0.99 | +0.98 [-0.44, +2.38] | +0.79 |
| D1-2 | put | d25 | 2 | 1386 | 0.35 | -0.65 | +1.00 [-0.77, +2.52] | +0.81 | 978 | -0.34 | -1.51 | +1.17 [-0.97, +3.11] | +0.75 |
| D1-2 | put | d15 | 2 | 1169 | -0.68 | -1.26 | +0.57 [-0.82, +1.75] | +0.47 | 904 | 0.42 | -0.77 | +1.19 [+0.06, +2.19] | +1.52 |

### The pick by scan minute

| scan | fit N | signal % risk | tod % risk | lift $ [CI] | OOS N | signal % risk | tod % risk | lift $ [CI] |
|---|---|---|---|---|---|---|---|---|
| 10:00 | 14 | -3.48 | 0.73 | -7.88 [-39.12, +16.16] | 5 | 9.21 | 0.35 | +16.05 [+11.07, +21.22] |
| 10:30 | 31 | -0.33 | 1.15 | -2.77 [-20.05, +10.29] | 30 | 1.94 | 1.53 | +0.61 [-15.01, +10.93] |
| 11:00 | 55 | 1.82 | 1.28 | +0.98 [-9.30, +9.21] | 58 | 3.62 | 1.83 | +3.26 [-5.02, +9.98] |
| 11:30 | 90 | 2.84 | 0.98 | +3.39 [-3.32, +9.04] | 73 | 1.50 | 1.06 | +0.84 [-6.99, +7.80] |
| 12:00 | 104 | 2.41 | 0.90 | +2.68 [-3.03, +7.85] | 90 | 2.09 | 0.31 | +3.26 [-4.29, +9.18] |
| 12:30 | 116 | -0.61 | -0.04 | -1.09 [-8.06, +4.95] | 101 | 0.86 | 0.48 | +0.72 [-5.83, +6.93] |
| 13:00 | 105 | 0.09 | 0.56 | -0.91 [-7.77, +5.31] | 65 | 4.11 | 1.77 | +4.29 [-2.97, +9.35] |
| 13:30 | 96 | 1.98 | 1.17 | +1.55 [-5.15, +7.02] | 73 | 4.92 | 1.84 | +5.67 [+1.20, +9.66] |
| 14:00 | 95 | -0.94 | -0.18 | -1.40 [-8.78, +5.02] | 69 | 4.53 | 1.30 | +6.04 [+1.91, +9.92] |
| 14:30 | 102 | 3.61 | 0.57 | +5.67 [+1.30, +9.69] | 77 | 4.36 | 2.49 | +3.43 [-0.02, +6.62] |
| 15:00 | 194 | 1.34 | 0.31 | +1.88 [-0.93, +4.81] | 116 | 1.91 | 1.42 | +0.88 [-3.39, +4.78] |
| 15:30 | 167 | 1.92 | 0.77 | +2.18 [-0.58, +5.36] | 147 | 2.83 | 1.94 | +1.62 [-1.37, +4.64] |

D1-2 share of the signal rows by scan (the pick, hold): fit 10:00 14, 10:30 31, 11:00 55, 11:30 90, 12:00 104, 12:30 116, 13:00 105, 13:30 96, 14:00 95, 14:30 102, 15:00 194, 15:30 167; OOS 10:00 5, 10:30 30, 11:00 58, 11:30 73, 12:00 90, 12:30 101, 13:00 65, 13:30 73, 14:00 69, 14:30 77, 15:00 116, 15:30 147

## 7. Stress tests

`out/cluster.txt`, `robust.txt`, `robust_lr_<mode>.csv`, `robust_fomc_<mode>.csv`, `signal_by_month.csv`, the cells CSVs.

- **Session bootstrap**: fit — no hold lift clear of zero (0 of 60); OOS — 37 of 60 clear, the pick's by +0.05 points of
  risk and $0.06. The benchmark's three 2-wide condor cells clear zero in both periods.
- **Without the best five sessions**: fit — the pick's lift +$0.58, the D1 condor d20 w2's −$2.80, 15 of 60 cells positive;
  OOS — 59 of 60 positive (the pick +$1.98, D1 condor d20 w2 +$10.71).
- **By year**: the pick's lift +$3.95 / +$2.13 / +$0.17 (2022 / 2023 / 2024) and +$3.36 / +$1.23 (2025 / 2026) — falling
  through the fit to nothing in 2024, then up again; D1 condor d20 w2 2025 +$14.30 / 2026 +$12.35 after a fit in which its
  worst months were −$1,000 each.
- **By month, without the five best months** (`cluster.txt`): the pick fit −$1.03 (18 of 26 months positive), OOS +$0.72
  (17 of 22); D1 condor d20 w2 fit −$5.36 (17 of 26), OOS +$9.84 (19 of 22); D1 condor d25 w1 fit −$1.89, OOS +$4.88; D1–2
  condor d25 w2 fit −$4.25, OOS −$0.39. In fit every condor cell's lift lives in four or five months of 2024 and dies in
  the event months; OOS it is broad.
- **FOMC decision days** (`robust.py`: a list of the 32 second-days of meetings 2022-11 → 2026-09 TYPED FROM MEMORY, not a
  file on disk and unverified — a descriptive read, 17 days in fit, 14 in OOS): in fit the unconditional 25-delta 2-wide
  condor made −6.5 % of risk on those days (full loss 24 %) against +3.3 % on the others, and the D1–2 rows on those days
  −7.6 % (141 rows): a quiet, low-realized-vol morning before a 14:00 statement is a D1 minute, and the condor sold into
  it takes the afternoon's move. With those 17 days removed, 20 of 60 fit hold lifts clear zero — the pick +1.11 %
  [+0.21, +1.94], D1 condor d25 w1 +7.7 % [+1.0, +13.9] — but D1 condor d20 w2 still does not (+2.0 % [−2.9, +5.9], +$0.17
  without the best five). OOS the decision days were the condors' BEST days (+11.4 % of risk, the D1–2 rows +23.8 %) and
  removing them changes little (25 of 60 clear; D1 condor d20 w2 +6.1 % [+2.7, +9.5]). So the lift's sign in a period is
  decided by whether the afternoon of a quiet morning holds an event the model cannot see — Hypothesis D's "needs X"
  (a scheduled-event calendar) from the other side.
- **The logistic model's deciles** (`robust_lr_*`): fit 0 of 60 clear (26 point estimates positive, 10 positive without
  the best five; the best lower bound −0.84 %); OOS 22 of 60 clear, the pick +0.49 % [−1.09, +1.83] (−$0.03 without the
  best five), D1 condor d20 w2 +3.8 % [−0.3, +7.8], D1 condor d25 w1 +4.1 % [−3.9, +12.2]. A second model of the same
  target halves the OOS lift and removes it from the headline cells.
- **Full-loss share**: the signal's rows settle at the full width less often than all rows OOS (the pick 1.3 % vs 2.4 %;
  D1 condor d20 w2 2.5 % vs 6.7 %; D1 condor d25 w1 10.3 % vs 19.4 %) and about as often or MORE often in fit (1.8 vs
  2.1 %; 6.6 vs 5.5 %; 16.3 vs 17.4 %). The credit is the same (D1 condor d20 w2 $0.370 vs $0.368): the signal does not
  find a richer sale, it finds — in one period of two — a quieter afternoon.
- **Tails, drawdown, streaks** (hold, the pick): fit p5 / p1 / worst −$35 / −$186 / −$196, worst session 2024-12-18
  −$1,482 (52 % of a $2,831 total), drawdown $1,599, streak 10; OOS −$9 / −$182 / −$192, worst 2026-06-17 −$633, drawdown
  $785, streak 4. D1 condor d20 w2 OOS: p5 / p1 / worst −$76 / −$155 / −$186, worst session 2025-04-16 (−$364), drawdown $706 / streak 5 on a total of $9,447; the fit's worst months were its −$1,000 lift totals (above).
- **Friction**: the pick 49 % of the gross in fit, 30 % OOS ($1.03 bid-ask + $1.30 fees on $4.75 and $7.68 of gross); the
  D1–2 2-wide condors 27–28 % OOS, 43–49 % in fit, the D1 2-wide condors 17–26 % OOS and 37–58 % in fit (the 10-delta 184 %); the unconditional 2-wide condors 41–56 %, the 1-wides 70–120 %.
- **Decile drift**: by the 2024H2 cuts D1 holds 7.7 % of OOS minutes (10.3 % in cut) and D10 13.4 %; the signal set is
  smaller OOS (D1–2 18.7 % of scan minutes against 22–23 %) and its scan mix moved earlier (15:00–15:30 hold 29 % of the
  pick's OOS rows against 31 % in fit; 11:00–12:30 36 % against 31 %). The paired baseline is matched by scan minute, so
  the mix does not enter the lift; the drift does say the registered cuts are from a lower-vol half-year.

## 8. Verdict and what would change it

- **Signal: no edge.** The pre-registration had to record "not pre-registrable": in 2022–2024 no hold cell's lift over the
  time-matched unconditional sell cleared zero, the best candidate was a put vertical with a +0.7 % lift inside a ±1.6-point
  interval, and the only clear lifts were on a losing management. The OOS record is positive and, on the D1 condors,
  large — but it is a single period read after the fit contradicted it, the fit's lift on the same cells was negative
  without its best months and sessions, it is decided by event days the model does not know, and a second model of the
  same target does not reproduce it. By the rule written before the OOS read this is a post-hoc observation.
- **Benchmark: unconditional SPY 2-wide condors, 13:00–15:00, hold, are positive in both periods with intervals clear of
  zero** (+2.3 to +3.0 % of risk fit, +3.4 to +4.6 % OOS), as Hypothesis B's midday condor was; the afternoon is where it
  is, the morning is nothing. It remains "needs X" as Hypothesis B left it (a forward paper record with real complex-order
  fills, since 41–56 % of the gross is modelled bid-ask; the 16:00 settlement check).
- **Needs X for the signal**: (1) a FORWARD pre-registered re-test on the next ≥ 150 full sessions, fixed now: D1 (the
  t2 GBM's bottom decile by the 2024H2 cuts, `out/scores_SPY.parquet`'s model) at the scan minutes 13:00–15:00, SPY 2-wide
  iron condor, short strikes at 20 delta, hold — judged by the same paired time-matched lift against the unconditional
  condor at the same minutes, edge = lift CI above zero in % of risk and $, positive without the best five sessions; the
  expectation written here from the fit: the lift is inside the noise; (2) an event calendar on disk (FOMC, CPI, payrolls)
  so that the lift can be read with and without event afternoons by a file, not a typed list; (3) the OOS read above is
  then one of two independent periods, not the only one.
- **Rule for the terminal: none.** The t2 decile may be shown as a display field (as Hypothesis D said), never as a
  trade trigger; nothing here licenses "sell premium when the model is quiet". The descriptive benchmark rule stays
  Hypothesis B's (unconditional afternoon condor, conditional on its X).

## 9. Files

`research_notes/Compass phase 3/hyp_e_short_premium_lift/`: `build_minutes.py`, `fit_model.py`, `analyze.py`, `prereg.py`,
`verify.py`, `report.py`, `notes_tables.py`, `cluster.py`, `robust.py`; `out/`: `minutes_SPY_all.parquet` (rebuildable, 25 MB),
`scores_SPY.parquet` (rebuildable, 2 MB), `model_auc.csv`, `model_auc_oos.csv`, `hypd_spy_auc.csv`, `decile_rates.csv`,
`decile_rates_oos.csv`, `feature_importance.csv`, `preregistered.md`, `fit_*.csv`, `oos_*.csv`, `fit_summary.txt`,
`oos_summary.txt`, `tables.md`, `notes_tables.md`, `cluster.txt`, `signal_by_month.csv`, `robust.txt`, `robust_*.csv`,
`verify_fit.txt`, `verify_oos.txt`; `logs/`. Commands, from the folder, each `nice -n 10 env POLARS_MAX_THREADS=1
OMP_NUM_THREADS=1 python3 -I …`: `build_minutes.py` (551 s), `fit_model.py` (15 s), `analyze.py fit` (18 s), `verify.py fit
50 11`, `prereg.py`, then `analyze.py oos` (16 s), `fit_model.py oos`, `verify.py oos 50 12`, `report.py`, `notes_tables.py`,
`cluster.py`, `robust.py`. No credentials or keys anywhere in the folder; nothing outside it was edited.
