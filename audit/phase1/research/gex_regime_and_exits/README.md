# GEX regime and exit-engine study (2026-10-13)

Scripts (all read-only against `../../backtest`; outputs in `out/`):

- `common.py` – shared helpers (trading days, price lookups, daily-block bootstrap, OLS slope, Spearman).
- `q1_regime_momentum.py` – prior-day gamma-flip regime vs PM-on-AM / last-30-on-prev-30 continuation, realized range, 1-min reversal rate. Outputs `q1_daily.csv`, `q1_summary.csv`, `q1_pos_minus_neg.csv`.
- `q2_fetch_exposures.py`, `q2_exposures.py` – UW `stock/SPY/spot-exposures` 1-minute data on 60 sessions; ICs vs next 30/60-min returns. Outputs `q2_sessions.json`, `q2_minute_obs.csv`, `q2_daily.csv`, `q2_ic_summary.csv`.
- `q3_walls.py` – first touch of prior-day call/put wall and gamma magnet vs distance-matched random levels. Outputs `q3_events.csv`, `q3_summary.csv`, `q3_real_minus_control.csv`.
- `q4_engine.py` – vectorised re-implementation of `exits.simulate` + `costs.settle` (verified leg-for-leg, `verify()`), the 576-configuration grid.
- `q0_data_checks.py` – gex-levels snapshot metadata (`q0_gex_levels_meta.csv`) and spot-exposures field behaviour; `q2_extra.py` – partial IC / between-vs-within-day decomposition (`q2_extra.csv`).
- `q4_load.py` – loads the two reference entry sets from `results/v1/trades.csv.gz`, verifies the engine, draws the 3,000 random entries (`q4_random_entries.csv`), writes `q4_bars.pkl` (250 MB, regenerable, not kept).
- `q4_grid.py` – runs the grid on strategy and random entries -> `q4_grid_strategy.npz`, `q4_grid_random.npz` (per-trade $ under mid/spread/adverse/spread+$0.01-floor, exit reasons, exit minute).
- `q4_report.py` – per-configuration table `q4_grid_summary.csv`, heads `q4_group_heads.csv`, `q4_strategy_minus_random.csv`, `q4_breakdowns.csv`; console summary in `q4_report.log`.
- `run.sh` – runs everything.

Notes: `../../research_notes/Finding a 0DTE options edge/empirical_gex_regime_and_exits.md`.
