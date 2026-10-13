# Reproduction audit of the committed validation tests (T1–T7)

**Scope.** Can the committed outputs under `evidence/analysis/` and `evidence/validation/` be regenerated from the committed scripts (`evidence/scripts/*.py`) and the committed data archives, with no network access and no credentials? Everything below was verified by running and diffing; nothing under `evidence/`, `backtest/`, `research/`, `reports/`, `research_notes/` or the top-level `*.md` files was modified, and no script was edited.

**Environment.** Repo HEAD `5208c8f`; Python 3.13.16 (`python3 -I`); Linux; 4 CPUs; audit date 2026-10-13. Staging tree built in the scratchpad (`$STAGE`, outside the repo); scripts run from `$STAGE/evidence/scripts` with `SP=$STAGE`.

## 1. Results per test

| Test | Script | Committed output(s) | Verdict | Evidence / exact reason |
|---|---|---|---|---|
| T1–T4 fill realism, cost models, exit alternatives, MFE/MAE | `validate_trades.py` (seed 7) | `evidence/analysis/validation_T1-T4.txt`; `evidence/validation/validation_results.json` | **Reproduced exactly** | stdout byte-identical (27 lines, sha256 `0988b2e7…`), including both bootstrap 95 % CIs (`[-12.9, 28.0]`, `[-138.9, -96.7]`) and the random-time MFE baseline; JSON byte-identical (486 records, 295,963 bytes). A second run gave identical stdout and JSON, so the seed-7 bootstrap is stable run-to-run. Header `trades=489 evaluated=486 missing_bars=3 no_bar_at_entry=0` reproduced. |
| T5 gate / grade validity | `gate_validity.py` (seed 11) | `evidence/analysis/validation_T5_gates.txt` | **Partially reproduced** (point estimates exact; bootstrap CIs, p-values, row order and one top-30 row differ) | `families tested: 144` identical. For every family row and all 11 pre-registered claims, `n_with`, `n_without`, both means and the `diff` are identical; the last-10-line IS/OOS grade block is identical. CI bounds differ by up to ~1.1 pct-pt and p-values by up to ~0.003 (e.g. GEX CI committed `[+7.7,+18.8]` vs regenerated `[+8.3,+18.9]`); because rows are sorted by bootstrap p, the order differs and the 30th row swaps (`GAMEPLAN` in committed, `AMD` in regenerated; 29/30 families common). All `BH q<0.10` flags shown are `YES` in both. Cause: see §4 — the script seeds `random` but iterates tag families from Python `set`s, whose order changes with per-process hash randomization. |
| T6 public-tape signal value | `tape_value.py` | `evidence/analysis/validation_T6_tape.txt`; `evidence/validation/tape_value_results.json` | **Reproduced exactly** | stdout byte-identical (103 lines, sha256 `557a4a14…`); JSON byte-identical (825 records). Header `alerts with bars: 825 of 830` reproduced. No randomness in this script. |
| Tape CSV (input to T6) | `tape_signals.py` | `evidence/analysis/public_tape_signals.csv` | **Reproduced exactly** | Regenerated from the 8 committed `evidence/public_api/todays_signals_history/2026-10-06..13.json` files; 972 rows, 830 with a parsable OCC symbol; byte-identical (sha256 `b03e2c45…`). No snapshot files from `evidence/analysis_snapshots/` are needed. |
| Ledger breakdown | `analyze_trades_a.py <trades_all.json>` | `evidence/analysis/trades_breakdown.txt` | **Reproduced exactly, including a crash** | The script exits with `statistics.StatisticsError: no median for empty data` at line 49 (`entryDelta` is empty/zero for all 489 trades). The committed file is the stdout up to that point (181 lines, ends at `--- pnl% quantiles`), byte-identical to the regenerated stdout. The remaining sections the script would print (entryDelta, entryIV, daily P&L / max drawdown, equity curve, exit-reason examples) do not exist in the committed file. Traceback saved as `validation/trades_breakdown.stderr.txt`. |
| Confluence vocabulary | `analyze_trades_b.py` | `evidence/analysis/confluence_vocab.txt` | **Reproduced exactly** | byte-identical (298 lines). |
| Ledger rules | `analyze_trades_c.py` | `evidence/analysis/trades_rules.txt` | **Reproduced exactly** | byte-identical (35 lines). |
| Ledger eras | `analyze_trades_d.py` | `evidence/analysis/trades_eras.txt` | **Reproduced exactly** | byte-identical (40 lines). |
| Field profile | `profile_trades.py` | *(no committed output; cited in `VALIDATION_PLAN.md` line 95 as a command only)* | **n/a** | Runs cleanly (rc 0); stdout saved as `validation/profile_trades.txt` for the record. |
| T7 refresh stability | *(no committed script)* | Figures quoted in `GEORGEFI_SIGNAL_RESEARCH.md` §5 and §8.6 only | **Reproduced by auditor recomputation** (two descriptive caveats) | Five snapshots exist in the repo: `evidence/public_api/analysis.json` (`updatedAt` 14:16:08 UTC) and `evidence/analysis_snapshots/analysis_2026101{3T144839,3T145341,3T145843,3T150344}Z.json` (14:47:52, 14:52:28, 14:56:44, 15:03:08). My script `validation/t7_recompute.py` reproduces §5 exactly: direction 4/37, action 19/37, confidence 20/37, setupGrade 18/37, contract 18/37, gexRegime 1/37, crowd_mood 0/37 — **but** the 37 consecutive ticker-pairs come from all 20 `decisions` tickers (3 tickers absent in one snapshot), not "6 core tickers" as the text says (the 6 index tickers give 12 pairs). §8.6 reproduces exactly over the 6 index tickers and 5 snapshots (24 pairs): 25 %, 38 %, 50 %, 38 %, 54 %, 4 %, 0 %. The ^SPX, ^NDX and QQQ paths quoted in the text match. The §8.6 action histogram differs slightly: recomputed WATCHING 34, WATCHING (Pending Entry) 14, DO NOTHING 13, BLOCKED (all variants) **33** (text: 32), WAITING FOR TRIGGER 2, BUY_CALLS 2, plus **WATCHING (Sweep Retest) 2** which the text omits (recomputed total 100 = 5×20; text total 97). |
| T8 | — | — | Not attempted: `VALIDATION_PLAN.md` lists it as planned; no script or output is committed. | |

## 2. Commands (as run)

```bash
STAGE=<scratchpad>/audit_validation; REPO=/home/user/georgeredo
mkdir -p $STAGE/evidence/{scripts,analysis,public_api,validation} $STAGE/out
cp $REPO/evidence/scripts/*.py $STAGE/evidence/scripts/
cp $REPO/evidence/analysis/*   $STAGE/evidence/analysis/
cp -r $REPO/evidence/public_api/. $STAGE/evidence/public_api/
cd $STAGE/evidence/public_api && for g in *.gz; do gunzip -kc "$g" > "${g%.gz}"; done   # trades_all.json (29.97 MB, 489 trades) + 3 book files
cp $REPO/evidence/validation/*.txt $STAGE/evidence/validation/      # the two result JSONs are NOT copied: the scripts regenerate them
cd $STAGE/evidence/validation && tar xzf $REPO/evidence/validation/uw_bars.tar.gz \
  && tar xzf $REPO/evidence/validation/uw_tape_bars.tar.gz && tar xzf $REPO/evidence/validation/massive_bars_partial.tar.gz
# archives extract to uw_bars/<trade_id>_<YYYY-MM-DD>.json, uw_tape_bars/<contract>_<YYYY-MM-DD>.json, bars/<trade_id>.json
cd $STAGE/evidence/scripts; export SP=$STAGE
python3 -I validate_trades.py   > $STAGE/out/validation_T1-T4.txt     # also writes $SP/evidence/validation/validation_results.json
python3 -I gate_validity.py     > $STAGE/out/validation_T5_gates.txt
python3 -I tape_value.py        > $STAGE/out/validation_T6_tape.txt   # also writes $SP/evidence/validation/tape_value_results.json
python3 -I tape_signals.py      # rewrites $SP/evidence/analysis/public_tape_signals.csv from public_api/todays_signals_history/*.json
python3 -I analyze_trades_a.py $STAGE/evidence/public_api/trades_all.json > $STAGE/out/trades_breakdown.txt   # rc=1, see above
python3 -I analyze_trades_b.py $STAGE/evidence/public_api/trades_all.json > $STAGE/out/confluence_vocab.txt
python3 -I analyze_trades_c.py $STAGE/evidence/public_api/trades_all.json > $STAGE/out/trades_rules.txt
python3 -I analyze_trades_d.py $STAGE/evidence/public_api/trades_all.json > $STAGE/out/trades_eras.txt
python3 -I profile_trades.py   $STAGE/evidence/public_api/trades_all.json > $STAGE/out/profile_trades.txt
diff $REPO/evidence/analysis/<name>.txt $STAGE/out/<name>.txt ; cmp <committed json> <regenerated json>
```
Order matters only for T6: `tape_value.py` reads `public_tape_signals.csv`; I ran it on the committed CSV first and then regenerated the CSV, which turned out byte-identical, so the result is the same either way.

## 3. Runtimes (wall clock, this machine)

| Script | Runtime | rc |
|---|---|---|
| validate_trades.py (T1–T4) | 12.0 s (26.4 s on the second run, machine loaded) | 0 |
| gate_validity.py (T5) | 183.2 s (144 families × 2000 resamples + 11 claims) | 0 |
| tape_value.py (T6) | 1.0 s | 0 |
| tape_signals.py | 0.1 s | 0 |
| analyze_trades_a.py | 1.2 s | **1** (StatisticsError, line 49) |
| analyze_trades_b/c/d.py | 1.0 / 1.0 / 2.5 s | 0 |
| profile_trades.py | 1.3 s | 0 |
| t7_recompute.py (auditor) | <1 s | 0 |

## 4. Diff summaries and the T5 non-determinism

* Byte-identical (sha256 in `validation/checksums.txt`): `validation_T1-T4.txt`, `validation_T6_tape.txt`, `trades_breakdown.txt`, `trades_eras.txt`, `trades_rules.txt`, `confluence_vocab.txt`, `public_tape_signals.csv`, `validation_results.json`, `tape_value_results.json`.
* `validation_T5_gates.txt`: 86 diff lines over 54. Only the `[lo, hi]` CI bounds, `p=` values, the p-sorted row order and the 30th row differ; all counts, means and diffs are identical (checked programmatically with `validation/t5_pointcmp.py`-style parsing: 29 common families, point estimates equal on all; 11 claims equal once ` [`…` is stripped; IS/OOS block identical).
* Mechanism, verified: `gate_validity.py` calls `random.seed(11)` once, then loops `for f,n in fams.items()` where `fams = Counter(f for t in ts for f in tagset(t))` and `tagset()` returns a Python `set` of strings. String hashing is randomized per process (PYTHONHASHSEED; `python3 -I` ignores any PYTHONHASHSEED set in the environment), so the insertion order of `fams`, and therefore the order in which families consume the seeded random stream, changes every run. Two `-I` runs of the family-order snippet (`validation/famorder.py`-equivalent) gave different first families (`ENTRY, MTF_ALIGNED, GENOME, …` vs `MTF_ALIGNED, BOS, VWAP, …`); two runs with `PYTHONHASHSEED=0` gave the same order. The claims block, which iterates a fixed list, is reached with a different random state and therefore also differs. By contrast `validate_trades.py` only iterates lists, so seed 7 reproduces exactly.
* Re-run evidence: see §4a (filled in from three further full T5 runs).

### 4a. T5 re-runs

Three further full runs of the unmodified `gate_validity.py` (each 357–360 s because the three ran in parallel):

| Run | Invocation | vs. first `-I` run | vs. committed file |
|---|---|---|---|
| `-I` run 2 | `python3 -I gate_validity.py` | **differs** (78 changed lines; e.g. GEX CI `[+8.3,+18.9]` → `[+8.1,+18.8]`) | differs |
| `PYTHONHASHSEED=0` run 1 | `PYTHONHASHSEED=0 python3 -s gate_validity.py` | differs | differs (72 changed lines; GEX CI `[+8.1,+18.5]` vs committed `[+7.7,+18.8]`) |
| `PYTHONHASHSEED=0` run 2 | same | — | **byte-identical to `PYTHONHASHSEED=0` run 1** |

So: (a) two `-I` runs of the same script on the same data do not agree with each other, (b) fixing the hash seed makes the output fully deterministic, (c) the author's hash seed is not 0 and is not recorded, so the committed CI/p digits cannot be regenerated. The GEX point estimate (`+13.4`, n 367/122, means 8.1/−5.3) is identical in all five outputs (committed + 4 runs). Saved copies: `validation/validation_T5_gates.rerun2_-I.txt`, `validation/validation_T5_gates.PYTHONHASHSEED0.txt`.

## 5. Archive coverage (computed by `validation/coverage.py`, output in `validation/archive_coverage.txt`)

| Archive | Files | Coverage |
|---|---|---|
| `uw_bars.tar.gz` | 506 JSON files (`uw_bars/<trade_id>_<day>.json`) | Exactly the 506 (trade, day) jobs `fetch_uw_bars.py` would generate for the 489 ledger trades (entry day + exit day for multi-day trades): 506 present, 0 absent, 0 extra. **All 489 trades have an entry-day file and an exit-day file.** 3 files have an empty `data` array (UW returned no bars): `81kodfn91162hwg_2026-04-17` and `wrz65879h3yf4c9_2026-04-17` (both `^SPX O:SPX260417C07055000`), `3i5i5g4100v5op2_2026-03-20` (`^SPX O:SPX260320P06585000`). `validate_trades.py` treats an empty bar list as missing, which is exactly the committed `missing_bars=3`, `evaluated=486`. Matches `uw_fetch_log.txt` (`FINISHED ok 506 fail 0`). |
| `uw_tape_bars.tar.gz` | 643 JSON files (`uw_tape_bars/<contract>_<session>.json`) | The CSV yields 648 unique (contract, session) pairs across the fetched subsystems; 643 present, 5 absent — exactly the five `code=422` failures in `uw_tape_fetch_log.txt` (AMZN270121C00260000 2026-10-09, MSFT261217C00550000 2026-10-13, MSFT270121C00550000 2026-10-13, NVDA270119C00225000 2026-10-09, SPY261215C00780000 2026-10-13). 825 of the 830 alerts with an OCC symbol have a bar file, matching `alerts with bars: 825 of 830`. No empty `data` arrays. |
| `massive_bars_partial.tar.gz` | 85 JSON files (`bars/<trade_id>.json`) | 85 of 489 trade ids; written by `fetch_bars.py` / `fetch_bars_slow.py`. **Not read by any committed validation script** (T1–T6 use only `uw_bars` / `uw_tape_bars`); labelled "cross-check, partial" in `GEORGEFI_SIGNAL_RESEARCH.md`. |

## 6. What a third party needs

1. Only the committed repo: `evidence/scripts/*.py`, `evidence/public_api/trades_all.json.gz` (+ `todays_signals_history/*.json` for the CSV), the three validation tarballs, and Python ≥3.10 stdlib (no third-party packages). No network, no API keys.
2. Set `SP` to a directory laid out like `evidence/` (the scripts read `$SP/evidence/public_api/trades_all.json`, `$SP/evidence/validation/uw_bars/…`, `$SP/evidence/validation/uw_tape_bars/…`, `$SP/evidence/analysis/public_tape_signals.csv` and **write** `$SP/evidence/validation/{validation_results,tape_value_results}.json` and `$SP/evidence/analysis/public_tape_signals.csv`). Run from a copy, not the repo, or the committed files are overwritten in place.
3. Expect `analyze_trades_a.py` to crash after the pnl% quantile line; the committed `trades_breakdown.txt` is that partial stdout.
4. Expect `validation_T5_gates.txt` CI/p/order to differ from the committed file on every run unless the hash seed is fixed; the author's hash seed is unknown, so the committed CI digits are not recoverable. The point estimates are. A fix would be to iterate `sorted(fams)` (not applied here).
5. T7 has no script; `audit/phase1/validation/t7_recompute.py` is the auditor's reconstruction from the five committed snapshots and reproduces the quoted rates with the two wording caveats in §1.
6. The ET offset is hard-coded as UTC-4 in all scripts (`datetime.timedelta(hours=-4)`); fine for Mar–Oct 2026 data, but it is not a reproduction issue.
7. Files in this directory: regenerated outputs (`validation/*.txt`, `validation/public_tape_signals.regenerated.csv`), `checksums.txt`, `archive_coverage.txt`, the auditor helper scripts, and the `analyze_trades_a.py` traceback. Bar files were not copied (sizes: 150 MB staged).

## 7. Housekeeping notes

* This audit wrote only to the scratchpad, `audit/phase1/validation/` and this file. The final `git status` shows **no modification to any tracked file under `evidence/`, `research/`, `reports/`, `research_notes/` or the top-level `*.md`**.
* The final `git status` does show `M backtest/README.md`, `M backtest/prefetch.py`, `M backtest/run.py` and an untracked `backtest/results/v1/signals.json.gz`, plus untracked `audit/phase1/backtest_reproduction.md`, `audit/phase1/research/…` and `research/georgefi_full_history/…`. None of these were touched by this audit (no command here referenced `backtest/` or `research/`; the files' mtimes fall in the same minutes as another session's `audit/phase1/backtest_reproduction.md`), so they come from a concurrent session working in the same checkout. Whoever consolidates `audit/phase1/` should confirm that with the owner of that session before committing anything.
