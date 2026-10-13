# Backtest reproduction audit — `backtest/results/v1`

Audit of whether the committed backtest (`backtest/`, results in `backtest/results/v1/`) can be reproduced from the committed code and artifacts. Only what was actually run and diffed is reported. Nothing under `backtest/`, `research/`, `evidence/`, `reports/`, `research_notes/` or the top-level `*.md` was modified (final `git status` on those paths: clean).

- Repository state audited: HEAD `5208c8f0e775e1b5d1d21c01fd180ab9f6e01c8c`, 2026-10-13 (UTC).
- All outputs of this audit live under `audit/phase1/backtest/` (listed at the end). Scratch copies of scripts and the fresh cache used for Step D live in the session scratchpad (`$SP/audit_bt`, `$SP/audit_scripts`, `$SP/audit_fresh_cache`), not in the repo.

## Status table

| Step | What | Status | Exact reason |
|---|---|---|---|
| A | `report.py` regenerated from committed `trades.csv.gz` + `baseline.csv.gz` | **Reproduced exactly** | `report.txt` and `summary.json` byte-identical to the committed files (sha256 `c53e5301…`/`4af5fbe9…`). `report.py` seeds its RNG (`np.random.default_rng(7)`), so the bootstrap CIs are deterministic. |
| B | `match_georgefi.py` on the committed artifacts | **Not reproduced from committed artifacts / Reproduced exactly from the re-run** | The script reads `OUTDIR/signals.json`, which is **not committed** in `results/v1/` → `FileNotFoundError`. Run on the re-run's `signals.json` (Step C) the output is byte-identical to the committed `georgefi_match.txt`. |
| C | Full `run.py` re-run from the warm cache + `report.py` | **Reproduced exactly** (with one path workaround) | `trades.csv` (192 900 rows), `baseline.csv` (9 896 rows), `signals.json` (18 386 signals), `report.txt`, `summary.json` all byte-identical to v1. Workaround: committed `run.py`/`prefetch.py` load `backtest/probe/trading_days.json`, a directory that is not in the repo (the file is committed as `backtest/trading_days.json`), so the unmodified scripts were run from a scratchpad copy with `probe/trading_days.json` added. |
| D | Cache provenance spot check (live API vs warm cache) | **Reproduced exactly** | 30/30 sampled requests (10 underlying 1-m bar days, 6 gex-levels, 4 interpolated-iv, 10 option-contract intraday days from v1 trades) returned payloads deep-equal to the warm-cache payloads; 0 errors. |

Headline numbers of the re-run (identical to v1): 18 386 raw signals (sweep/ict+gex 6 368, sweep/ict 5 309, continuation/ict+gex 3 647, continuation/ict 3 062); 4 279 contract-days of option bars; 144 variants, 192 900 trades; 9 897 baseline draws → 9 896 baseline trades; all 144 per-variant trade counts identical to `run_v1.log`; per-variant `usd_spread` totals: max |Δ| = 0.0; every field of `summary.json` (n, total, wr, exp, CI lo/hi, PF, maxDD, avg_ret; all/mid/adverse/IS/OOS): max |Δ| = 0.0.

## Machine

- Python 3.13.16, numpy 2.5.3 (the only non-stdlib dependency; used by `report.py` only), Linux 6.18.44 x86_64, 4 CPUs, 15 GB RAM.
- Scripts run with `python3 -I` and `PYTHONDONTWRITEBYTECODE=1`; no `__pycache__` written into the repo.
- Unusual Whales token loaded only in the same shell command as the python run (`set -a; . "$SP/secrets/research.env"; set +a`), never printed or logged; the logs were grepped for `Bearer`/`UW_API` (0 hits). Parallelism: `run.py` uses `ThreadPoolExecutor(max_workers=6)`; Step D used 3 workers. The backtest code only talks to `api.unusualwhales.com`.

## Code-reading notes (what determines reproducibility)

- **Cache key** (`data.py:_key`): `sha1(path + '?' + urlencode(sorted(params)))[:24] + '_' + sanitized(path?params)[:90]`, stored as `BT_CACHE/<key>.json.gz` containing the raw JSON response. Lookup is hit-before-fetch: an existing file is never re-fetched or overwritten by `data.get`. HTTP 404/422/400 are cached as `{"error": code}`; after 5 failed retries on other errors the call returns `{"error": str}` **without caching** (so transient failures silently produce "no bars" for that key → trade dropped). If `UW_API_TOKEN` is unset, `'Bearer ' + None` raises inside the retry loop, which is swallowed: a cold-cache run without a token completes with empty data rather than failing loudly.
- **Seeds**: `run.py` calls `random.seed(42)` at import; the random-time baseline is drawn after the (deterministic) simulation in insertion order of a `Counter`, so it is reproducible given identical trades. `report.py` uses `np.random.default_rng(7)` and calls `ci()` in a fixed order (variant insertion order from `trades.csv`), so bootstrap CIs are deterministic.
- **Threading**: option bars are prefetched with 6 threads into a memo dict; only the *order of completion* varies, which affects nothing except the `STATS` counters printed at the first progress line (`hits` 2069 in the re-run vs 2068 in `run_v1.log` at `bars 0 / 4279`; final counts are consistent). Signal generation and simulation are single-threaded and sorted with a stable sort.
- **Time dependence**: none in code (no `now()`); the day list comes from the static `trading_days.json`; the date range is fixed on the command line. Reproducibility therefore depends only on the data vendor returning the same payloads (checked in Step D).
- **Path defect**: `run.py` line 13 and `prefetch.py` line 5 read `<script dir>/probe/trading_days.json`; the repo commits `backtest/trading_days.json` and no `probe/` directory, so a fresh clone fails with `FileNotFoundError` until the file is placed at `backtest/probe/trading_days.json` (the README does not mention this). The committed `trading_days.json` is byte-identical to the `probe/trading_days.json` used by the original run (scratchpad copy).
- **Missing artifact**: `signals.json` (4.7 MB, written by `run.py`) is required by `match_georgefi.py` but is not committed.
- The committed `trades.csv.gz`/`baseline.csv.gz` decompress to files byte-identical to the original run's uncompressed outputs still present in the session scratchpad (`$SP/bt/out/v1/`), and the committed scripts are byte-identical to the scratchpad copies the original run used.

## Step A — report regeneration from committed results

```
mkdir -p audit/phase1/backtest/v1_copy
cp backtest/results/v1/trades.csv.gz backtest/results/v1/baseline.csv.gz audit/phase1/backtest/v1_copy/
gunzip -k audit/phase1/backtest/v1_copy/trades.csv.gz audit/phase1/backtest/v1_copy/baseline.csv.gz
python3 -I backtest/report.py audit/phase1/backtest/v1_copy 2026-03-02 > audit/phase1/backtest/v1_copy/report.txt
```
- Start 18:52:59.59 UTC, end 18:53:23.34 UTC; `report.py` wall 10.35 s (user 9.09 s).
- `cmp report.txt backtest/results/v1/report.txt` → identical (188 lines each); `cmp summary.json …` → identical. Exact diff is empty, so no tolerance comparison was needed; there is no bootstrap-CI noise because the RNG is seeded.
- 192 901 lines in `trades.csv` (192 900 trades), 9 897 lines in `baseline.csv` (9 896 rows).

## Step B — GeorgeFi coincidence script

```
python3 -I backtest/match_georgefi.py audit/phase1/backtest/v1_copy evidence/public_api/trades_all.json.gz > audit/phase1/backtest/v1_copy/georgefi_match.txt
```
- 18:53:45.91–18:53:45.97 UTC, exit 1: `FileNotFoundError: …/v1_copy/signals.json` (stderr saved in `v1_copy/georgefi_match.stderr.txt`; stdout empty). The script handles the gzipped ledger itself (`LEDGER.endswith('.gz')`), so the ledger path is fine; the blocker is the uncommitted `signals.json`.
- Re-run on Step C's output: `python3 -I backtest/match_georgefi.py audit/phase1/backtest/rerun evidence/public_api/trades_all.json.gz > audit/phase1/backtest/rerun/georgefi_match.txt` (18:59:07.66–18:59:10.47 UTC, 2.8 s, exit 0) → byte-identical to `backtest/results/v1/georgefi_match.txt` (188 scalps; 14/16/9/10 same-direction hits; 2 944 sweep signals, 19 matched; agree 124 / disagree 143).

## Step C — full pipeline re-run from the warm cache

Set-up (committed scripts copied unchanged; hashes verified against `backtest/*.py` and `backtest/trading_days.json`):
```
AB=$SP/audit_bt; mkdir -p $AB/probe
cp backtest/{run,data,features,exits,costs,report,match_georgefi,prefetch}.py $AB/
cp backtest/trading_days.json $AB/probe/trading_days.json      # path workaround, see notes
export BT_CACHE=$SP/bt/cache PYTHONDONTWRITEBYTECODE=1
set -a; . $SP/secrets/research.env; set +a
setsid nohup $AB/run_wrapper.sh $AB/run.py 2025-06-02 2026-10-09 SPY,QQQ,IWM \
    /home/user/georgeredo/audit/phase1/backtest/rerun > audit/phase1/backtest/rerun/run.log 2>&1 < /dev/null &
python3 -I backtest/report.py audit/phase1/backtest/rerun 2026-03-02 > audit/phase1/backtest/rerun/report.txt
```
(`run_wrapper.sh` only echoes START/END timestamps and the exit code around `python3 -I "$@"`.)

- `run.py`: START 18:55:27.27 UTC, END 18:57:58.44 UTC, **151 s wall**, exit 0. Peak RSS ≈ 1.3 GB. Cache: every lookup was a hit (`misses: 0, errors: 0` in all progress lines; final `{'hits': 8799, 'misses': 0, 'errors': 0}`); the warm cache had 24 289 files before and after (nothing added). The original run was not timed in its log; its phase-2 `STATS` lines show the same 0-miss pattern (its baseline phase fetched 1 788 contract-days live, which are now cached).
- `report.py` on the re-run: 18:58:30.28–18:58:51.43 UTC, 21.1 s wall (9.3 s user; the machine was busy with Step D set-up).
- Comparison (`rerun/compare_vs_v1.json`, produced by `$SP/audit_scripts/compare_rerun.py`):
  - `trades.csv`: 192 900 vs 192 900 rows, header identical, **0 rows differ positionally**, 0 keys only in one side (key = variant, ticker, date, signal_t, entry_t, exit_t, contract, entry_px, usd_spread, reasons), 0 variants with different counts, max |Δ| of per-variant `usd_spread` totals = 0.0. sha256 `0e8c41c8…` on both sides.
  - `baseline.csv`: 9 896 vs 9 896, 0 differing rows, sha256 `ed2ebd16…` on both sides (seeded, see notes).
  - `signals.json`: byte-identical to the original run's uncommitted `signals.json` in the scratchpad (sha256 `10b440c6…`; 18 386 signals).
  - `report.txt` / `summary.json`: byte-identical to v1 (same sha256 as Step A); max |Δ| over every numeric field in `summary.json` = 0.0.
  - The 144 `variant done … <count>` lines in `rerun/run.log` are identical to those in `backtest/results/v1/run_v1.log`.
- No differences to explain. The candidate causes listed in the brief (cache entries rewritten by later studies, thread ordering, RNG) did not manifest: the research studies reuse `backtest/data.py` (hit-before-fetch; the only removal path is `research/short_vol_session/common.py:_safe_option_bars`, which deletes a cache file only after three consecutive read failures and then refetches), thread ordering only affects the printed counters, and both RNGs are seeded.

## Step D — cache provenance spot check (live API vs warm cache)

```
export BT_CACHE=$SP/audit_fresh_cache   # fresh, empty → every call goes to the live API
export WARM_CACHE=$SP/bt/cache AB=$SP/audit_bt V1=audit/phase1/backtest/v1_copy OUTJSON=audit/phase1/backtest/provenance/provenance_check.json
set -a; . $SP/secrets/research.env; set +a; python3 -I $SP/audit_scripts/provenance_check.py > audit/phase1/backtest/provenance/provenance_check.log
```
- 18:59:11.46–18:59:23.72 UTC (12.3 s wall, 7.7 s of requests at 3 parallel workers); `STATS {'hits': 0, 'misses': 30, 'errors': 0}`; 30 files written to the fresh cache (scratchpad only).
- Sample (seeded `random.Random(2026)`): 10 × `stock/{T}/ohlc/1m?date=…&limit=2000` (random days 2025-06-03 … 2026-08-21, SPY/QQQ/IWM), 6 × `stock/{T}/gex-levels?date=…`, 4 × `stock/{T}/interpolated-iv?date=…`, 10 × `option-contract/{CID}/intraday?date=…` with contract ids/dates sampled from `v1_copy/trades.csv` (e.g. `SPY250805P00631000` 2025-08-05, `QQQ260729P00675000` 2026-07-29, `IWM251118C00231000` 2025-11-18).
- Result: **identical 30 / differing 0 / no warm entry 0 / errors 0** (deep JSON equality of the whole response, including row order). Per type: ohlc1m 10/10, gex 6/6, iv 4/4, optbars 10/10. Details per request (key, warm-file mtime, live latency, row counts) are in `provenance/provenance_check.json`.
- Scope caveat: 30 keys out of the ≈ 9.9 k distinct requests the pipeline makes; it shows that, as of 2026-10-13 ~19:00 UTC, the vendor returns the same payloads the cache holds for the sampled keys, not that every key is unchanged.

Warm-cache facts (`$SP/bt/cache`, 387 MB, 24 289 gzip files, all written 2026-10-13 15:46–17:54 UTC): 13 502 option-contract intraday days, 1 044 each of underlying 1-m bars / gex-levels / interpolated-iv (3 tickers × 348 sessions incl. 6 look-back days, all written in the 15:xx prefetch), plus entries only used by the research studies (5 975 darkpool, 1 026 net-prem-ticks, 343 market, 250 flow-per-strike, 61 spot-exposures). Of the option-contract entries, 2 284 were written in the 15:xx hour, 5 046 in 16:xx (incl. the 1 788 baseline fetches of the v1 run) and 6 172 in 17:xx (later studies, different keys).

## What a third party needs to reproduce from a fresh clone

1. **The cache is not committed** (387 MB; `.gitignore` excludes nothing under `backtest/cache`, it simply was never added). Everything must be re-fetched from Unusual Whales: ≈ 3 132 prefetch requests (3 endpoints × 1 044 ticker-days) + 4 279 option contract-days for signals + ≈ 2 451 extra contract-days for the random baseline ≈ 9.9 k requests at ≤ 6 parallel (the original prefetch wrote 3 132 entries in ≈ 8 min; expect roughly 20–30 min for the full set, subject to vendor rate limits). Whether the vendor still serves identical 1-minute history later is not guaranteed by anything in the repo; Step D shows it did on 2026-10-13 for 30 sampled keys.
2. **A UW API token** with access to `stock/*/ohlc/1m`, `gex-levels`, `interpolated-iv` and `option-contract/*/intraday`, exported as `UW_API_TOKEN`. Note the silent-failure modes above (missing token / transient errors are not cached and produce empty data instead of aborting).
3. **Fix the day-list path**: create `backtest/probe/trading_days.json` as a copy of `backtest/trading_days.json` (or patch the two scripts); otherwise `prefetch.py` and `run.py` fail immediately.
4. Run exactly: `prefetch.py 2025-06-02 2026-10-09 SPY,QQQ,IWM`, `run.py 2025-06-02 2026-10-09 SPY,QQQ,IWM OUT`, `report.py OUT 2026-03-02`, `match_georgefi.py OUT evidence/public_api/trades_all.json.gz`. With a warm cache the pipeline takes ≈ 2.5 min (`run.py`) + ≈ 10–20 s (`report.py`) + 3 s on a 4-CPU machine, ≈ 1.3 GB RAM.
5. Python ≥ 3.9 with `zoneinfo` and numpy (only for `report.py`). Determinism does not depend on numpy/Python versions beyond float formatting (verified here only with Python 3.13.16 / numpy 2.5.3).
6. `match_georgefi.py` additionally needs `signals.json` from the same `run.py` output directory (not committed), and the committed ledger `evidence/public_api/trades_all.json.gz`.

## Files produced by this audit (`audit/phase1/backtest/`)

- `v1_copy/`: `trades.csv.gz`, `baseline.csv.gz` (copies of the committed artifacts; the uncompressed CSVs were deleted after use), `report.txt`, `summary.json` (Step A output), `report_time.txt`, `georgefi_match.txt` (empty) + `georgefi_match.stderr.txt` (Step B failure).
- `rerun/`: `run.log` (full `run.py` log with START/END/EXIT), `trades.csv.gz`, `baseline.csv.gz`, `signals.json.gz` (re-run outputs, gzipped), `report.txt`, `summary.json`, `report_time.txt`, `georgefi_match.txt`, `compare_vs_v1.json`, `cache_count_before.txt`.
- `provenance/`: `provenance_check.json`, `provenance_check.log` (Step D).
- Scratchpad (not in repo): `$SP/audit_bt/` (verbatim script copies + `probe/trading_days.json` + `run_wrapper.sh`), `$SP/audit_scripts/{compare_rerun.py,provenance_check.py}`, `$SP/audit_fresh_cache/` (30 live responses).

Note: an untracked directory `research/georgefi_full_history/` appeared in `git status` during this audit; it was not created or touched by this audit (it belongs to a concurrent task) and is outside its scope.
