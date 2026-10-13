# Reproduction audit of the three committed empirical studies under `research/`

Audit date: 2026-10-13 (18:56–19:09 UTC). Scope: can `research/short_vol_session`, `research/gex_regime_and_exits` and `research/flow_predictors` be regenerated from their committed code, and do the regenerated outputs match the committed ones and the headline numbers quoted in `research_notes/Finding a 0DTE options edge/`? Everything below was verified by running the committed commands in copies under `audit/phase1/research/` and diffing against the committed files. Nothing was changed to force a match.

## Verdicts

| study | status | one-line reason |
|---|---|---|
| short_vol_session | **Reproduced exactly** | 13 of 14 committed outputs byte-identical (all 10 CSVs, `summary.md`, `summarize.log`, `t3_variants.md`); `run_tests.log` differs only in cache-hit counters and elapsed seconds. 13:00 short-straddle headline +$8.36 [−3.15, 19.52] reproduced. |
| flow_predictors | **Reproduced exactly** | all 17 committed outputs byte-identical (payload-identical for the three `.csv.gz`); the four prefetch steps were cache-only no-ops; console output of `mt_summary.py`, `trade_rule.py` and `placebo_daily_ic.py` matches the original run logs. SPY F1 h30 IC 0.020 and dark-pool SPY D1 h60 IC −0.065 reproduced to all printed digits. |
| gex_regime_and_exits | **Partially reproduced** | q0–q3 and every *strategy* result of q4 are byte/numerically identical (17 of 26 files identical; 4 more differ only in counters/timings). The **random-entry control set of q4 is not reproducible**: `q4_load.py` draws it from "whatever option-contract files happen to be in the cache", which is uncommitted state that changed between the committed run (7,330 files) and now (13,502 at run time, 14,054 after a sibling job). Result: 5 q4 files differ in their random-group rows; the note's random-control numbers (best random config −$1.34 [−2.23, −0.46]; "0 configs beat random, 51 worse") become −$2.32 [−3.35, −1.33] and "8 configs with strategy−random CI above zero, 3 below". The headline −$1.78 [−2.80, −0.73] (strategy, pooled) and "0 of 576 configurations positive" reproduce exactly. |

## Environment and method

- Host: Linux 6.18, 4 cores, 15 GB RAM; Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1 (the same interpreter the committed runs used on 2026-10-13).
- Data: the Unusual Whales gzip cache at `$BT_CACHE` (24,289 files, 387 MB; not committed). `backtest/data.py` keys every GET by `sha1(path + sorted params)` and never expires an entry, so a warm cache is a pure function of (endpoint, params) and is read read-only by every study. The token is only touched on a cache miss.
- Procedure: each study was copied to `audit/phase1/research/<study>/` (without `__pycache__`), **all committed outputs were deleted from the copy** (so a stale copy could never masquerade as a match; the comparison script also checks that every file's mtime is after the run start), and the committed commands were run from inside the copy with `python3 -s`.
- Token-less first pass: all three studies were run with `UW_API_TOKEN` **unset**. In `data.get` a miss would raise `TypeError` before any request, so a completed run with `misses: 0` in the logs proves that the warm cache makes every prefetch step a no-op and that no live call (and therefore no UW parallelism) was needed. No step needed the token; nothing was re-run with it. No Massive/Polygon call is made by any of the three studies.
- Concurrency during the audit: two sibling audit sessions were running CPU-bound jobs (a backtest rerun and a validity gate) on the same 4 cores and the same cache for the whole window, so the wall-clock times below are upper bounds; the cache file count was 24,289 before and after the runs (no sibling added files that the three studies read).
- Comparison: `compare.py` (scratchpad) does an exact byte comparison (payload comparison for `.csv.gz`, since the gzip header carries a timestamp); for differing CSVs it aligns columns, reports shape, the number of numeric columns that differ and the maximum absolute / relative difference, plus text-column mismatches; for `.log`/`.md`/`.json` it reports the number of changed lines and a sample diff.
- Nothing under `backtest/`, `research/`, `evidence/`, `reports/`, `research_notes/` or the top-level `*.md` files was modified (`git status` at the end shows only `audit/`).

## Edits made to the copies

| copy | file | change | reason |
|---|---|---|---|
| flow_predictors | `common.py` line 4 | `BT = os.path.abspath(os.path.join(HERE, '..', '..', 'backtest'))` → `BT = '/home/user/georgeredo/backtest'` (with an `# AUDIT COPY EDIT` comment) | the relative path resolves to `audit/phase1/backtest`, which is a sibling auditor's working directory and holds no `data.py`/`trading_days.json`; a symlink there would have collided with that directory, and `PYTHONPATH` cannot help because `trading_days.json` is loaded from `BT` by path. The other two studies already hard-code the same absolute path. |

No other file in any copy was changed. The `-s`/`-I` question: `short_vol_session`'s README says `python3 -I`; that works for its three scripts because they insert their own directory into `sys.path`, but the gex and flow scripts do a bare `from common import *` and fail under `-I` (verified: `ModuleNotFoundError`), so `python3 -s` (or plain `python3`, as gex's `run.sh` uses) is the invocation that works for all three.

## Commands and runtimes

Wall-clock times are from this audit (4 cores shared with two other CPU-bound audit jobs; load average 8–11). The README figures are in parentheses.

| study | commands (run from inside the copy, `BT_CACHE` set, token unset) | steps and seconds | total |
|---|---|---|---|
| short_vol_session | `python3 -s run_tests.py > run_tests.log 2>&1 && python3 -s summarize.py > summarize.log 2>&1 && python3 -s t3_variants.py > t3_variants.md` (the committed `.log`/`.md` files are these stdout redirects; `summarize.py` prints the md before appending its period-split section, which is why `summarize.log` is a prefix of `summary.md`) | run_tests 133, summarize 87, t3_variants 22 | 242 s (README: ~2 min warm) |
| gex_regime_and_exits | `bash run.sh` — verified: `cd "$(dirname "$0")"`, writes only to `out/`, reads `../../backtest/results/v1/trades.csv.gz` read-only via the absolute `BT` path; runs q0, q1, q3, q2-chain and q4-chain as 5 parallel background jobs then `wait` (note: `wait` under `set -e` does not propagate a failing background job, so the logs must be checked — 0 tracebacks found) | run.sh 510 (q4_load alone 284 s of it under contention; committed log: 80 s) | 510 s (README: ~8 min) |
| flow_predictors | `python3 -s prefetch_cheap.py 5; python3 -s prefetch_dp_fps.py; python3 -s prefetch_fps_volume.py; python3 -s refetch_dp_gaps.py 5; python3 -s build_panel.py; python3 -s analyze_flow.py; python3 -s analyze_tide.py; python3 -s analyze_dp.py; python3 -s analyze_bursts.py; python3 -s trade_rule.py SPY F1; python3 -s mt_summary.py; python3 -s placebo_daily_ic.py` (stdout of each step kept in the scratchpad; no logs are committed for this study) | prefetch_cheap 3, prefetch_dp_fps 52, prefetch_fps_volume 5, refetch_dp_gaps 1, build_panel 43, analyze_flow 246, analyze_tide 24, analyze_dp 93, analyze_bursts 233, trade_rule 14, mt_summary <1, placebo 3 | 717 s |

Live-call check (token unset, so a miss would have crashed): every log ends with `misses: 0, errors: 0` — short_vol_session `{'hits': 13401, 'misses': 0}`, gex q2 `{'hits': 402, 'misses': 0}`, flow prefetch_cheap `{'hits': 1368, 'misses': 0}`, prefetch_dp_fps `{'hits': 6309, 'misses': 0}`, prefetch_fps_volume `{'hits': 120, 'misses': 0}`, refetch_dp_gaps `gap ticker-days 0`, bursts/trade_rule `misses: 0`. `samples.json` is regenerated by `prefetch_dp_fps.py` from `random.Random(7)` and came back identical, so the sampled sessions are fixed by code, not by the committed file. Nothing in the three studies depends on "today": no `date.today()`/`now()` anywhere; the only clock use is elapsed-time printing. `trade_rule.py` shells out to `pgrep -f prefetch_` (read-only process scan, needs procps) to throttle itself; it found nothing and used 5 workers on cache hits.

## Comparison tables

Columns: status (IDENTICAL = byte-identical, or payload-identical for `.csv.gz`), regen? (file mtime after the run start, i.e. really regenerated), committed/regenerated sizes, and for differing files the shape, number of numeric columns that differ, max absolute and max relative difference, or the number of changed lines for text files.

### short_vol_session (14 committed outputs)

| file | status | regen? | committed | regenerated | shape/lines | numeric cols differing | max abs | max rel | text/other |
|---|---|---|---|---|---|---|---|---|---|
| research/short_vol_session/csv/summary_all.csv | IDENTICAL | y | 64032 | 64032 |  |  |  |  |  |
| research/short_vol_session/csv/t1_straddles.csv | IDENTICAL | y | 5291195 | 5291195 |  |  |  |  |  |
| research/short_vol_session/csv/t2_strangles.csv | IDENTICAL | y | 1432717 | 1432717 |  |  |  |  |  |
| research/short_vol_session/csv/t3_orb_options.csv | IDENTICAL | y | 637118 | 637118 |  |  |  |  |  |
| research/short_vol_session/csv/t3_orb_underlying.csv | IDENTICAL | y | 138468 | 138468 |  |  |  |  |  |
| research/short_vol_session/csv/t3_orb_variants.csv | IDENTICAL | y | 584076 | 584076 |  |  |  |  |  |
| research/short_vol_session/csv/t4_halfhour_returns.csv | IDENTICAL | y | 117155 | 117155 |  |  |  |  |  |
| research/short_vol_session/csv/t4_momentum_options.csv | IDENTICAL | y | 556833 | 556833 |  |  |  |  |  |
| research/short_vol_session/csv/t5_gap_options.csv | IDENTICAL | y | 259972 | 259972 |  |  |  |  |  |
| research/short_vol_session/csv/t5_gap_underlying.csv | IDENTICAL | y | 79018 | 79018 |  |  |  |  |  |
| research/short_vol_session/run_tests.log | DIFFERS | y | 1457 | 1454 | 32 vs 32 lines, 20 changed |  |  |  |  |
| research/short_vol_session/summarize.log | IDENTICAL | y | 45650 | 45650 |  |  |  |  |  |
| research/short_vol_session/summary.md | IDENTICAL | y | 48238 | 48238 |  |  |  |  |  |
| research/short_vol_session/t3_variants.md | IDENTICAL | y | 842 | 842 |  |  |  |  |  |

`run_tests.log`: the 20 changed lines are `already cached 11276 to fetch 79` → `11355 / 0`, the per-1000 `hits` counters, `misses: 79` → `0` and the elapsed seconds; the row counts (`T1 rows 30510`, `T2 rows 8068`, `T3 rows 1475 4919`, `T4 rows 1017 4068`, `T5 rows 1017 2034`) and the decision counts are identical. Bootstrap seeds are fixed (`boot_ci` seed 7, `random.seed(42)` for the random-time baselines), which is why even the CI columns are byte-identical.

### gex_regime_and_exits (26 committed outputs; `q4_bars.pkl` and the two `.npz` grids are gitignored and were regenerated: 257 MB + 8.8 MB + 17 MB in the copy)

| file | status | regen? | committed | regenerated | shape/lines | numeric cols differing | max abs | max rel | text/other |
|---|---|---|---|---|---|---|---|---|---|
| research/gex_regime_and_exits/out/q0.log | IDENTICAL | y | 759 | 759 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q0_gex_levels_meta.csv | IDENTICAL | y | 138725 | 138725 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q1.log | IDENTICAL | y | 12223 | 12223 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q1_daily.csv | IDENTICAL | y | 226909 | 226909 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q1_pos_minus_neg.csv | IDENTICAL | y | 2692 | 2692 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q1_summary.csv | IDENTICAL | y | 20588 | 20588 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2.log | IDENTICAL | y | 18281 | 18281 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2_daily.csv | IDENTICAL | y | 3923 | 3923 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2_extra.csv | IDENTICAL | y | 394 | 394 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2_extra.log | IDENTICAL | y | 331 | 331 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2_fetch.log | DIFFERS | y | 1041 | 1040 | 62 vs 62 lines, 1 changed |  |  |  |  |
| research/gex_regime_and_exits/out/q2_ic_summary.csv | IDENTICAL | y | 15855 | 15855 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2_minute_obs.csv | IDENTICAL | y | 5153249 | 5153249 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q2_sessions.json | IDENTICAL | y | 840 | 840 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q3.log | IDENTICAL | y | 40595 | 40595 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q3_events.csv | IDENTICAL | y | 2860856 | 2860856 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q3_real_minus_control.csv | IDENTICAL | y | 1225 | 1225 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q3_summary.csv | IDENTICAL | y | 26525 | 26525 |  |  |  |  |  |
| research/gex_regime_and_exits/out/q4_breakdowns.csv | DIFFERS | y | 9788 | 9818 | 60x11 vs 60x11 | 7 | 66 | 1.89 | text mismatches {'value': 2} |
| research/gex_regime_and_exits/out/q4_grid.log | DIFFERS | y | 357 | 357 | 14 vs 14 lines, 14 changed |  |  |  |  |
| research/gex_regime_and_exits/out/q4_grid_summary.csv | DIFFERS | y | 1130043 | 1133754 | 2304x33 vs 2304x33 | 29 | 4.69e+03 | 2 |  |
| research/gex_regime_and_exits/out/q4_group_heads.csv | DIFFERS | y | 1491 | 1484 | 4x18 vs 4x18 | 8 | 77 | 1.23 | text mismatches {'best_is_cfg': 1, 'worst_cfg': 1} |
| research/gex_regime_and_exits/out/q4_load.log | DIFFERS | y | 205 | 208 | 6 vs 6 lines, 4 changed |  |  |  |  |
| research/gex_regime_and_exits/out/q4_random_entries.csv | DIFFERS | y | 332763 | 332773 | 3000x9 vs 3000x9 | 2 | 563 | 0.977 | text mismatches {'ticker': 2025, 'date': 2992, 'signal_t': 3000, 'entry_t': 3000, 'direction': 1534, 'contract': 3000} |
| research/gex_regime_and_exits/out/q4_report.log | DIFFERS | y | 29728 | 29693 | 113 vs 109 lines, 48 changed |  |  |  |  |
| research/gex_regime_and_exits/out/q4_strategy_minus_random.csv | DIFFERS | y | 77310 | 77254 | 576x8 vs 576x8 | 5 | 2.04 | 2 |  |

Per-group breakdown of the five differing CSVs (numeric max |diff| over all columns):

| file | strategy_sweep | strategy_continuation | strategy_pooled | random |
|---|---|---|---|---|
| q4_grid_summary.csv (576 cfg × 4 groups × 33 cols) | 0 | 0 | 0 | 29 of 33 numeric cols differ, max |diff| 4,687 (`total` $ column); best random cfg exp_spread −1.34 → −2.32 |
| q4_group_heads.csv | 0 | 0 | 0 | 8 numeric cols + `best_is_cfg`, `worst_cfg` text differ |
| q4_breakdowns.csv (60 rows) | — | — | 32 strategy rows: 0 | 28 random rows: 7 cols differ, max |diff| 66 (`n`), 2 text (`value`) |
| q4_strategy_minus_random.csv (576 rows, same cfg order) | `strategy_exp`, `strategy_mid`: 0 | | | `random_exp` max |diff| 1.56 $, `diff_lo` 2.04, `diff_hi` 1.68; committed `diff_lo>0: 0, diff_hi<0: 51` → regenerated `8 / 3` |
| q4_random_entries.csv (3,000 × 9) | | | | 2,426 of 2,996 unique (ticker, date, minute, contract) entries are shared with the committed set but every row is shifted; 574 entries are new |

The other four "DIFFERS" files are counters/timings only: `q2_fetch.log` (`STATS misses: 60` → `0`), `q4_load.log` (`cached contract-days 7330` → `13502`, `tries 4242` → `3445`, timings), `q4_grid.log` (14 timing lines), `q4_report.log` (every changed line is a random-group line — the `HEAD {"group": "random"...}` record, the `strategy-minus-random` count, the random `BR` breakdown rows and the `RTOP` random top-6 — plus a trailing `real/user/sys` block in the committed log, which shows the committed `q4_report.log` was produced with `time python3 q4_report.py`, not by `run.sh` verbatim). The three strategy `HEAD` records, the `ORIGINAL pooled` and `BEST pooled` lines are byte-identical.

**Cause, verified.** `q4_load.py` builds `avail` by globbing `$BT_CACHE/*option-contract_*_intraday_date-*` and accepts a `random.Random(2026)` candidate only if its contract-day is already cached. The committed run logged 7,330 such files; the cache holds 13,502 now (the short_vol_session study fetched ~5,600 contract-days *after* the committed `q4_load` ran at 17:34–17:35, and a sibling audit job added 552 more during this audit, after my `q4_load` had globbed). Re-drawing with `avail` restricted to cache files with mtime before 17:34:53Z (exactly 7,330 files) reproduces **3,000 of 3,000** committed random entries and the logged 4,242 tries (`scratchpad/audit_run/q4_random_diag.py`, log `q4_random_diag.log`); with today's files it reproduces 0 of 3,000 in place. So this is neither bootstrap noise (all seeds are fixed: `boot_mean_ci` 7, `q4_report.analyse` 7, strategy-minus-random 3) nor a code bug, but an uncommitted dependency on the cache's contents: the control set is a function of which contracts other studies happened to fetch first. The committed `q4_random_entries.csv` is therefore the only record of the control set that the note's random-control numbers come from; a reader cannot regenerate it from code plus data alone.

### flow_predictors (17 committed outputs)

| file | status | regen? | committed | regenerated | shape/lines | numeric cols differing | max abs | max rel | text/other |
|---|---|---|---|---|---|---|---|---|---|
| research/flow_predictors/bursts_coverage.csv | IDENTICAL | y | 7985 | 7985 |  |  |  |  |  |
| research/flow_predictors/bursts_events.csv | IDENTICAL | y | 5192648 | 5192648 |  |  |  |  |  |
| research/flow_predictors/bursts_summary.csv | IDENTICAL | y | 7165 | 7165 |  |  |  |  |  |
| research/flow_predictors/darkpool_coverage.csv | IDENTICAL | y | 28231 | 28231 |  |  |  |  |  |
| research/flow_predictors/dp_ic_conditional.csv | IDENTICAL | y | 14335 | 14335 |  |  |  |  |  |
| research/flow_predictors/dp_ic_main.csv | IDENTICAL | y | 3643 | 3643 |  |  |  |  |  |
| research/flow_predictors/flow_ic_conditional.csv | IDENTICAL | y | 29235 | 29235 |  |  |  |  |  |
| research/flow_predictors/flow_ic_main.csv | IDENTICAL | y | 7716 | 7716 |  |  |  |  |  |
| research/flow_predictors/mt_summary.csv | IDENTICAL | y | 7424 | 7424 |  |  |  |  |  |
| research/flow_predictors/panel_darkpool.csv.gz | IDENTICAL | y | 2814836 | 2814836 |  |  |  |  |  |
| research/flow_predictors/panel_flow.csv.gz | IDENTICAL | y | 13842250 | 13842250 |  |  |  |  |  |
| research/flow_predictors/panel_tide.csv.gz | IDENTICAL | y | 831699 | 831699 |  |  |  |  |  |
| research/flow_predictors/samples.json | IDENTICAL | y | 2125 | 2125 |  |  |  |  |  |
| research/flow_predictors/tide_ic_conditional.csv | IDENTICAL | y | 3429 | 3429 |  |  |  |  |  |
| research/flow_predictors/tide_ic_main.csv | IDENTICAL | y | 1855 | 1855 |  |  |  |  |  |
| research/flow_predictors/trade_rule_SPY_F1.csv | IDENTICAL | y | 156137 | 156137 |  |  |  |  |  |
| research/flow_predictors/trade_rule_SPY_F1_summary.csv | IDENTICAL | y | 1160 | 1160 |  |  |  |  |  |

Console outputs (not committed, compared against the original run's logs kept in the scratchpad `fp/` directory): `mt_summary.py` stdout identical to `mt.log` (62 cells, Bonferroni threshold 8.06e-4, 4 nominal / 4 Bonferroni / 4 BH survivors — all four are the burst contract-net-return cells, negative); `trade_rule.py` summary table identical to `trade_rule.log` apart from cache-counter lines; `placebo_daily_ic.py` prints mean −0.0380 / −0.0634 / −0.1141 (t −4.3 / −6.2 / −10.6), matching the note's −0.038 / −0.063 / −0.114. `analyze_bursts.py` event counts (burst/baseline × Volume/NetPremium = 15,794 / 14,065 / 5,643 / 3,123; 2,238 contract-days) identical.

## Headline numbers quoted in the notes

| note | quoted | regenerated | match |
|---|---|---|---|
| empirical_short_vol_and_session.md | 13:00 short straddle, spread model: +$8.36 [−3.15, 19.52], win 65.1 %, PF 1.22, maxDD −5,084 | `summary.md` line 22: `short_hold / 13:00 | 1021 | 8.36 | [-3.15, 19.52] | 65.1% | 1.22 | -5084` | exact |
| same | mid +16.69 [5.36, 27.71], adverse −13.56 [−24.91, −2.48] at 13:00 | `summary.md` line 52 | exact |
| same | ORB variants table (`t3_variants.md`) | byte-identical | exact |
| empirical_gex_regime_and_exits.md | best configuration (stop −60, be +6, guard 25 %@+15, no partial, no time stop): spread −$1.78 [−2.80, −0.73], trade-level [−2.70, −0.89], mid +$2.45, adverse −$10.18, floor −$1.97, win 43.4 %, PF 0.83, maxDD −9,886, IS −2.38, OOS −1.11 [−2.85, 0.61], hold 12.1/4, mix STOP 12.4 / BE 44.1 / TRAIL 43.5 / CLOSE 0.04 | `BEST pooled` line of `q4_report.log` byte-identical; `strategy_pooled` rows of `q4_grid_summary.csv` identical | exact |
| same | original config pooled −$3.84 [−4.52, −3.19]; 0 of 576 configurations positive on sweep / continuation / pooled | `ORIGINAL pooled` line identical; `n_cfg_exp_above_zero: 0` for all three strategy groups | exact |
| same | random entries: best −$1.34 [−2.23, −0.46], same exit mix (STOP 11 / BE 45 / TRAIL 44), "no configuration beats random entries" (0 above / 51 below) | random best −$2.32 [−3.35, −1.33], mix STOP 11 / BE 46 / TRAIL 43; strategy−random: 8 configs with CI above zero, 3 below | **not reproduced** (control set differs, see above); the weaker claim "0 of 576 positive for random entries" still holds (`n_cfg_exp_above_zero: 0`) |
| same | q1 regime / q2 spot-exposure ICs (e.g. partial IC −0.1706 [−0.2506, −0.0986], n 19,371) / q3 wall touches | `q1*.csv`, `q2*.csv`, `q2_extra.log`, `q3*.csv` byte-identical | exact |
| empirical_flow_predictors.md | SPY F1 h30 IC 0.020 [−0.002, 0.041], p 0.072, spread 1.07 bp [−0.05, 2.21] | `flow_ic_main.csv`: ic 0.019541, lo −0.0021216, hi 0.040513, p 0.072445, spread 1.0747 [−0.054362, 2.2064] | exact |
| same | dark pool SPY D1 h60 IC −0.065 [−0.130, −0.002], p 0.051, spread −2.17 bp [−6.65, 2.37] | `dp_ic_main.csv`: −0.064547 [−0.13005, −0.0023024], p 0.050821, spread −2.1727 [−6.6492, 2.3711] | exact |
| same | SPY F1 rule on ATM 0DTE (trail, spread): −2.4 % per trade vs −2.3 % random | `trade_rule_SPY_F1_summary.csv`: rule −0.023768 [−0.0366, −0.0107], baseline −0.022579 [−0.0367, −0.0097] | exact |
| same | tide tradable ICs −0.002..+0.020; contemporaneous T_chg30 h30 IC 0.072 (p 9.6e-8) | `tide_ic_main.csv` byte-identical | exact |
| same | placebo within-day ICs −0.038 / −0.063 / −0.114 | stdout −0.0380 / −0.0634 / −0.1141 | exact |

## What a third party needs

1. **The Unusual Whales cache, which is not committed.** All three studies read `backtest/data.py`'s gzip cache (`$BT_CACHE`): 24,289 files / 387 MB at the start of this audit (13,502 option-contract intraday files, 5,972 dark-pool pages, 1,044 each of 1-minute OHLC / interpolated-IV / gex-levels, 1,026 net-prem-ticks, 342 market-tide, 244 flow-per-strike, 61 spot-exposures). With the cache every run above is a pure replay (zero live calls); without it a `UW_API_TOKEN` is required and the data must be re-fetched: roughly 13,400 GETs for short_vol_session (README: ~12 min at 6 workers), ~5,600 for gex, ~15,000 for flow_predictors (net-prem-ticks/tide 1,368, dark-pool pages 5,972, flow-per-strike 244, ~4,500 option contract-days, plus OHLC and gex-levels) — of the order of 35–45 minutes total at the studies' 5–6-worker settings (the original logs show ~10–16 GETs/s), subject to UW rate limits. The studies make no Massive/Polygon calls.
2. **Byte-identity is only guaranteed from this cache.** A fresh fetch is not guaranteed to return the same payloads (UW can revise bars/prints; `darkpool_rth` pages with `older_than` cursors taken from the previous page, so any revision changes the page keys), and `data.py` caches 4xx responses as `{'error': code}` while 5xx/transport failures are *not* cached, so a transient failure in one study silently changes what a later run sees. The expectation for a cold reproduction is "same to printed precision", not byte-identical.
3. **gex q4 is reproducible only with the exact cache state** (see Cause above): `q4_load.py` restricts the random control to contract-days *already* cached, and `q0_data_checks.py` counts whatever `*gex-levels*` files the cache holds (1,044 now; q0 runs concurrently with q1/q3 in `run.sh`, so on a cold cache it would race with the fetches). To make q4 reproducible the control set would have to be drawn from a committed universe (or `q4_random_entries.csv` treated as an input), which is a code change outside this audit's remit.
4. **Invocation.** Run each script from inside its directory. `python3 -s` (or plain `python3`) works for all three; `python3 -I`, as written in the short_vol_session README, works only for that study's scripts (they insert their own directory into `sys.path`) and fails with `ModuleNotFoundError: common` for gex and flow_predictors. `flow_predictors/common.py` locates `backtest/` relative to its own location (`../../backtest`), so it must stay two levels below the repo root or be pointed at the package (the one-line edit above). `backtest/trading_days.json` and `backtest/results/v1/trades.csv.gz` (q4's reference entries) are committed.
5. **Interpreter.** Python 3.13 with numpy 2.5.3 / pandas 3.0.5 / scipy 1.18.1; the bootstraps use `numpy.random.default_rng` with fixed seeds, so other numpy versions should reproduce the CSVs to printed precision but not necessarily byte-for-byte (`%.5g`/`%.6g` formatting plus float32 arrays in q4).
6. **Secrets.** Only `UW_API_TOKEN` (env; the studies never read it from a file). It was not needed for this audit.

## Audit artefacts

- Copies with regenerated outputs: `audit/phase1/research/{short_vol_session,gex_regime_and_exits,flow_predictors}/` (the identical files are duplicates of the committed ones and could be dropped before committing; `q4_bars.pkl` and the `.npz` grids are gitignored). The sibling backtest audit's directory `audit/phase1/backtest/` is untouched by this audit.
- Scratchpad (`audit_run/`): `compare.py`, per-study JSON/MD comparison outputs (`svs_all`, `gex_all`, `fp_all`), the flow_predictors step logs (`fp_logs/`), timing files, the token-less runner scripts, `cache_before.txt`/`cache_after.txt` listings and the q4 diagnostic (`q4_random_diag.py`, `.log`).
- `git status` at the end of the audit: no modifications under `backtest/`, `research/`, `evidence/`, `reports/`, `research_notes/` or the top-level `*.md` files from this audit; `audit/phase1/research/` is untracked (not committed — the coordinator commits). Modifications to `backtest/*.py`, `evidence/scripts/*.py`, `DATA_PROVIDER_AUDIT.md` and `GEORGEFI_SIGNAL_RESEARCH.md` that appeared in `git status` during the audit were made and committed by the parallel sessions (commit `5ed66df`, 19:09), not by this audit, whose only writes were to the copies and the scratchpad.

## Follow-up (2026-10-13, 19:14–19:18 UTC): making the gex q4 random control reproducible

At the coordinator's request one additive change was made to the original `research/gex_regime_and_exits/q4_load.py` (5 inserted lines after `days_ok = ...`, dated comment included): if `out/q4_random_entries.csv` exists and `Q4_REDRAW` is not set, the random control set is loaded from that committed file (and the option bars for its 3,000 contract-days are loaded from the cache) instead of being redrawn from the cache listing; `Q4_REDRAW=1` keeps the original redraw path intact. No other original file was touched. The same patched `q4_load.py` was placed in the audit copy, the committed `q4_random_entries.csv` was copied into the copy's `out/`, the previous q4 outputs of the copy were moved to `out/pre_followup/` for the record, and `python3 -s q4_load.py && q4_grid.py && q4_report.py` was re-run with `BT_CACHE` set and no token (q4_load 41 s, q4_grid 105 s, q4_report 74 s; 220 s total; `cached contract-days 14054`; load path taken: `random entries loaded from out/q4_random_entries.csv 3000`, `tries 0`, ticker counts IWM 1014 / QQQ 1008 / SPY 978 as in the committed log).

| file | result |
|---|---|
| q4_grid_summary.csv (2304 × 33) | **byte-identical** (1,130,043 bytes) |
| q4_group_heads.csv | **byte-identical** — random head restored to best −$1.335 [−2.228, −0.459] |
| q4_strategy_minus_random.csv (576 × 8) | **byte-identical** — `0 configs with diff CI above zero, 51 below` restored |
| q4_breakdowns.csv (60 × 11) | **byte-identical** |
| q4_report.log | 109 of 109 content lines identical (all `HEAD`, `ORIGINAL`, `BEST`, `BR`, `RTOP`, strategy-minus-random lines); the only difference is the 4-line `real/user/sys` footer that the committed log carries from having been run under `time` |
| q4_random_entries.csv | byte-identical after `write_csv`'s round-trip of the loaded rows |
| q4_load.log / q4_grid.log | differ only in the new `loaded from` line, `tries 4242` → `0`, `cached contract-days`, and elapsed seconds |

Conclusion: with the committed draw treated as an input, the whole gex study — including the random-control comparison — reproduces byte-for-byte from committed artefacts plus the warm cache; the gex status moves from "partially reproduced" to "reproduced exactly (given the committed control set)". The redraw path remains available for anyone who wants a fresh control set, with the caveat documented above that it depends on the cache's contents.
