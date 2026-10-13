#!/usr/bin/env bash
# Re-run the whole study (~8 min on 4 cores). Needs BT_CACHE (gzip cache used by backtest/data.py) and, for q2 only, UW_API_TOKEN in the env.
set -euo pipefail
cd "$(dirname "$0")"
python3 q0_data_checks.py > out/q0.log 2>&1 &
python3 q1_regime_momentum.py > out/q1.log 2>&1 &
python3 q3_walls.py > out/q3.log 2>&1 &
python3 q2_fetch_exposures.py > out/q2_fetch.log 2>&1 && python3 q2_exposures.py > out/q2.log 2>&1 && python3 q2_extra.py > out/q2_extra.log 2>&1 &
python3 q4_load.py > out/q4_load.log 2>&1 && python3 q4_grid.py > out/q4_grid.log 2>&1 && python3 q4_report.py > out/q4_report.log 2>&1 &
wait
echo done
