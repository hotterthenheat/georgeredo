# SPY / QQQ / IWM 0DTE short-premium grid on complete option chains (etf_v2)

Re-run of the pre-registered grid in `../etf/` on the full same-day option chains, answering the developer review of the round-2
report: the original study priced only strikes within ±2 % of the 09:31 print, skipped every entry whose strikes (or spot) fell outside
that band (amendment A1), and therefore dropped extreme-move days (e.g. the April 2025 tariff days) from the lane while the random-entry
baseline could still trade some of them.  Nothing in the pre-registered rules is changed: same 2,016 configurations per scope, same
TRAIN/TEST split, seeds, $0.70/side fills, exits, statistics and selection rule (`PREREGISTRATION_original.md` is a byte-identical copy
of `../etf/PREREGISTRATION.md`, sha256 ddc4e053…).  The original folder is not modified.  Results: `RESULTS.md`.  Research note:
`research_notes/High win rate 0DTE lanes/empirical_etf_full_chain_rerun.md`.

## Data

* Option quotes: `<scratchpad>/theta/data_full/chains/{SPY,QQQ,IWM}/{date}.parquet` — same schema as the original dataset
  (1-minute NBBO, 09:30–16:00 ET), every listed same-day strike (fetched with `THETA_DS_BAND=0`).  Read through `load_full.py`, a copy of
  `research/thetadata/dataset/load.py` whose chain root is `data_full` (`$HWR_CHAIN_ROOT`); the original loader is not edited.
* Underlying 1-minute bars: `<scratchpad>/theta/data/underlying/` (unchanged; also used for the 2017–2026 historical-move stress).
* SPY after-hours inputs: `../etf/results/diag_settlement_spy.csv` (EOD close and 17:15 quote mid per date), read unchanged.
* No ThetaData login was used by this study.

## Files

| file | role |
|---|---|
| `common.py`, `engine.py`, `analyze.py`, `analyze_test.py` | copies of `../etf/` with the changes listed in each docstring: full-chain loader, work dir `$HWR_WORK` (default `<scratchpad>/hwr_grid_v2`), a scope is computed only when all its tickers exist, TRAIN selection merged per scope; `engine.py` also writes `integrity_*.parquet` (skip status of every structure-k at every minute 10:00–14:30 under the trade loop's own rules); `analyze_test.py` also evaluates the original selections on complete TEST data, the random baseline on matched days, a Bonferroni bound over the 8 pre-registered selections, and the trades added relative to the band run |
| `integrity.py TICKER` | per-file manifest: sha256, rows, strikes, range, whether the listed strikes span the session's price range, and quote-by-quote comparison with the original band file |
| `integrity_summary.py` | data-integrity tables: status counts per entry set, still-missing list, originally skipped entries now tradable, strike reach in EM units |
| `validate_band.py` | code validation: this folder's engine run on the original band data reproduces the original per-trade, skip, selection and selected-TEST files exactly |
| `settlement.py` | SPY E2 after-hours re-valuation (repeat of the original post-hoc diagnostic B) on complete data |
| `stress.py` | historical entry-to-close moves 2017–2026 and stress P&L, capital per lot and margin estimates for every selection |
| `gates.py` | COMPASS §10 gate verdicts, item by item, carry-lane and signal-lane versions |
| `report.py` | builds `RESULTS.md` from `results/` |
| `run_stage.sh TICKER`, `run_final.sh` | the run order used (per ticker: TRAIN trades + manifest → TRAIN selection → TEST trades; then the TEST stage and everything else) |
| `results/` | `selection_train.json` (full-chain TRAIN selection), `grid_train.csv.gz`, `grid.csv.gz`, `selected_test.csv`, `selected_by_year.csv`, `baselines.csv`, `marginal_effects.csv`, `wr_vs_expectancy.csv`, `coverage.csv`, `grid_test_summary.json`, `integrity*.{csv,json}`, `data_manifest.csv`, `validation_band_reproduction.json`, `settlement_spy.csv`, `stress_*.csv`, `gates.csv` |

Per-trade data stays outside the repo in `$HWR_WORK`.

## Reproduce (no network; polars + numpy)

```bash
cd research/thetadata/hwr_grid/etf_v2
for t in SPY QQQ IWM; do ./run_stage.sh $t; done     # needs the complete data_full chains of each ticker
./run_final.sh
# code validation on the original band data (writes to <scratchpad>/hwr_grid_v2_bandcheck):
HWR_CHAIN_ROOT=<scratchpad>/theta/data HWR_WORK=<scratchpad>/hwr_grid_v2_bandcheck HWR_OUT=<scratchpad>/hwr_grid_v2_bandcheck/results_test \
  sh -c 'for t in SPY QQQ IWM; do python3 engine.py $t TRAIN; python3 engine.py $t TEST; done; python3 analyze.py train; python3 analyze.py test; python3 integrity.py SPY; python3 integrity.py QQQ; python3 integrity.py IWM'
```

## Run record (2026-10-14 UTC)

* 01:30–01:45 code copied from `../etf/` and edited (no rule changed).  Code validation on the ORIGINAL band data
  (`<scratchpad>/hwr_grid_v2_bandcheck`): 01:32 SPY TEST, 01:40–01:42 the other five ticker-periods, then `analyze.py train/test`,
  `settlement.py`, `stress.py`, `gates.py`, `report.py` on that copy — per-trade and skip files, TRAIN selections, selected-TEST rows and
  the SPY settlement re-valuation all identical to the original study (`results/validation_band_reproduction.json`).
* The full chains were written by the fetch job after SPXW; this study only read them when a ticker's count was complete
  (`*.parquet` files, no `.tmp`, no `.nodata`; fetch `progress.json` final: SPY 980 ok, QQQ 980 ok, IWM 621 ok, 0 errors).
* SPY complete 02:32 → `run_stage.sh SPY` 02:32:41–02:35:52; `selection_train.json` (SPY scope) sha256 74db493a… at 02:34:47, before
  `engine.py SPY TEST` started.
* QQQ complete 02:53 → `run_stage.sh QQQ` 02:53:11–02:56:27; selection adds QQQ and SPY+QQQ (SPY asserted unchanged), sha256 9dc7d131… at 02:55:27.
* IWM complete 02:59:52 → `run_stage.sh IWM` 02:59:58–03:01:34; selection adds IWM, final sha256 b3d83a32… at 03:00:50.
* `run_final.sh` 03:01:34–03:02:39 (TEST stage, integrity summary, validation, settlement, stress, gates, report).
* ~03:05 `gates.py` and `report.py` re-run after adding the paired-CI column, the band-skipped summary table and the 2024-06-21 note
  (formatting only; no computed number changed).
* Data finding: on 2024-06-21 (June quad-witching, TRAIN) the full pull lacks 2,346 (SPY), 3,910 (QQQ) and 1,564 (IWM) quote rows that
  the band pull had, and both pulls are irregular that day; every other session's overlapping quotes are identical row for row.
