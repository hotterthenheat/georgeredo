# Short-vol and session-effect tests on 0DTE SPY/QQQ/IWM (2025-06-02..2026-10-09)

Code: `common.py` (fills, combo/long simulation, cost models, cluster bootstrap), `run_tests.py` (tests 1-5, writes `csv/t*.csv`),
`summarize.py` (writes `summary.md` and `csv/summary_all.csv`), `t3_variants.py` (stricter opening-range break definitions, underlying only).
Reuses `../../backtest/data.py` (Unusual Whales client + gzip cache), `exits.py` (`trail` engine) and `costs.py` (constants). Nothing in `backtest/` is modified.

Reproduce (about 2 minutes from a warm cache; ~12 minutes if the ~11,400 option contract-days must be fetched):
```
export UW_API_TOKEN=...            # never commit
export BT_CACHE=/path/to/cache
python3 -I run_tests.py && python3 -I summarize.py && python3 -I t3_variants.py
```
Findings are written up in `../../research_notes/Finding a 0DTE options edge/empirical_short_vol_and_session.md`.
