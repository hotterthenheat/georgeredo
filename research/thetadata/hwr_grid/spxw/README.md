# SPXW high-win-rate short-premium grid and pre-registered test T-E

Pre-registered study on the local ThetaData SPXW dataset (`research/thetadata/dataset`, 1-minute NBBO of the same-day SPXW
expiry within ±2 % of the 09:31 SPX price; SPX index minutes).  Design, splits, seeds and pass rules: `PREREGISTRATION.md`
(hash and time in `prereg_sha256.txt`, written before any run).  Generated numbers: `RESULTS.md`.  Narrative note:
`research_notes/High win rate 0DTE lanes/empirical_spxw_grid_and_te.md`.

## Outcome (2026-10-14; details in RESULTS.md and the research note)

* T-C reproduced on 337/339 sessions exactly (the 2 others: 13:00 ATM strike outside the stored band).
* **T-E FAILS**: T-E window 2022-05-13 → 2025-05-29, n = 663, +$26.37 per straddle [−138.17, +169.77]; holdout +$152.93
  [+1.91, +294.08] (n = 299; the window that generated H13); the lane does not beat random entry times in either window.
* Grid (2,736 distinct configurations): S1 (14:05 straddle, 1× stop, settle, skip FOMC+month-end) TEST +$99.1 [−34.0, +226.0];
  S2 (14:05 ±0.5·EM strangle, settle, skip FOMC+month-end) TEST +$162.0 [+63.2, +258.4], win 71.5 %, but it does not beat its
  random-entry baseline (−$92.8 [−184.5, +1.1]) → gate FAIL.  135 TEST lower bounds > 0 vs 51 expected by chance (95th pct 232).
  No winged structure qualifies.  Many 13:00 strangle results depend on the band skipping 2025-04-09 (`bandcheck.py`).

## Files

| File | Role |
|---|---|
| `PREREGISTRATION.md`, `prereg_sha256.txt` | design fixed before the runs (Part A = T-E, Part G = grid) |
| `sim.py` | per-session simulator: strikes from SPX at the entry minute and the ATM straddle mid (EM), bid/ask fills, $1/side, TP/stop on the executable close cost, E0/E1/E2 exits, settlement at the SPX 16:00 print |
| `random_minutes.csv` | committed random-entry minutes (seeds 11–15, uniform 10:00–14:30, one per regular session 2022-05-13 → 2026-10-09) |
| `run_grid.py` | simulates every regular session → `$SP/hwr_grid/spxw/trades/{date}.parquet` and `skips/{date}.parquet` (per-trade data, not in git) |
| `stats.py` | day-clustered bootstrap (the T-C `cluster_boot` and an equivalent vectorised version), drawdown, Kelly, path statistics |
| `te.py` | T-C reproduction and T-E (window + holdout, sensitivities, random baseline, margin/sizing) |
| `analyze.py` | `train` stage: TRAIN metrics + `selection_train.json` (no TEST date loaded); `test` stage: TEST metrics, selected configurations, random baselines, gate, multiplicity, rule effects, coverage, trade-off, sizing |
| `bandcheck.py` | post-hoc data-limitation check: strangle days skipped because a strike lay outside the stored ±2 % band, added back with optimistic / estimated / zero credit |
| `diag.py` | data diagnostics (ATM strike outside the band, forward-filled exit rows, settlement fallbacks, legs left to settle) |
| `report.py` | writes `RESULTS.md` from `results/` |
| `results/` | `grid_configs.csv.gz` (one row per configuration, TRAIN and TEST metrics), `train_metrics.csv.gz`, `selection_train.json`, `selected_test.csv`, `selected_random_baseline.csv`, `gate.csv`, `multiplicity.json`, `rule_effects.csv`, `winrate_expectancy_tradeoff.csv`, `coverage.csv`, `test_wr70_lbpos.csv`, `sizing_test_lbpos.csv`, `tc_reproduction.csv`, `tc_repro_session_diffs.csv`, `te_results.csv`, `te_by_year.csv`, `te_summary.json`, `run_status.json` |

Configuration id: `{cell}|{entry}|tp{25|50|0}|st{0|1|2}|{E0|E1|E2}|{F0..F4}|{P|W}` where cell `N`/`W` = naked/winged and the
number is k (`N0.0` straddle, `N0.5`… strangles, `W0.0` iron butterfly, `W0.5`… iron condors); `P` = pre-registered literal rule
(skip if any leg is bid 0 at entry), `W` = diagnostic with zero-bid wings allowed; `E0` = diagnostic buy-back of every leg at 15:55.
The 2,736 distinct grid configurations are the rows with `distinct == True`.

## Reproduce

```bash
SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad
cd /home/user/georgeredo/research/thetadata/hwr_grid/spxw
python3 -c "import sim; sim.write_random_minutes()"           # deterministic; already committed
HWR_END=2024-12-31 python3 run_grid.py                          # TRAIN sessions (2 workers)
python3 analyze.py train                                        # TRAIN metrics + selection_train.json
python3 run_grid.py                                             # remaining sessions (resumable)
cp $SP/hwr_grid/spxw/run_status.json results/
python3 te.py                                                   # T-C reproduction + T-E
python3 analyze.py test                                         # TEST stage
python3 bandcheck.py; python3 diag.py                           # post-hoc band check, diagnostics
python3 report.py                                               # RESULTS.md
```
No network access and no ThetaData login are needed (the dataset and the cached SPX EOD files are local).
