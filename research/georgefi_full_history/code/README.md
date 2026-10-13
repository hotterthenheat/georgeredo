# GeorgeFi full-history reconstruction: how to rerun

Inputs (read-only): `../normalized/trades.csv` (1,149 ledger rows), `../normalized/paper_trades_spx.csv` (84 SPX paper trades), `/home/user/georgeredo/backtest/{data,exits,costs}.py` and `trading_days.json`.
Outputs: `../results/` (CSV tables, `RESULTS.md`, `METHODOLOGY.md`, `bar_coverage*.{csv,md}`, `run_info.json`).

```
SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad   # or any scratch dir holding secrets/research.env and bt/cache
cd /home/user/georgeredo/research/georgefi_full_history/code
set -a; . "$SP/secrets/research.env"; set +a          # exports UW_API_TOKEN (never printed)
export BT_CACHE="$SP/bt/cache"                        # gzip cache shared with backtest/data.py
python3 -I fetch_bars.py        # step 1: UW 1-minute bars for every row (3 workers; ~2.5 min cold, seconds warm) -> results/bar_coverage.csv, bar_coverage_summary.md
python3 -I reconstruct.py       # step 2: analyses A-E (~35 s, all cache hits) -> results/*.csv, results/RESULTS.md
python3 -I spx_twin_check.py    # optional labelled sensitivity for the 4 plain-SPX-root rows -> results/spx_root_substitution.csv
```

Files:
- `common.py` loads both ledgers into one row schema, wraps `backtest/data.py` (one retry on a cache read failure because other processes write the same cache), parses UW bars, and provides `bar_at` / `first_bar_after` / `vwap`.
- `fetch_bars.py` builds the (contract, day) task list (entry day; every trading day through the exit day for multi-day holds; underlying bars for SHARES rows), fetches with 3 parallel workers, and writes per-row coverage with the reason for any gap.
- `reconstruct.py` runs A (reported), B (simulated fills at reported minutes), C (independent reconstruction + random baselines + MFE/MAE), D (era comparison), E (sanity checks) and renders `RESULTS.md`; `narrative_header.md` is inserted verbatim at the top of `RESULTS.md`.
- `spx_twin_check.py` fetches the SPXW twin of the four `SPX`-root contracts and reports a labelled substitution.

Seeds: bootstrap 1,000 resamples with numpy seed 7 (fresh generator per statistic); random entry minutes `random.Random(11)` consumed in ledger order. Rerunning reproduces every number in `RESULTS.md` exactly, given the same cache contents.
