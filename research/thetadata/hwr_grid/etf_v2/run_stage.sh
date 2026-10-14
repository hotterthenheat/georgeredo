#!/bin/bash
# One ticker's stage of the etf_v2 run, started when the ticker's full-chain files are complete:
#   TRAIN trades + file manifest (2 processes) -> TRAIN selection (adds the scopes now complete) -> TEST trades.
# Usage: run_stage.sh TICKER        (then, after the last ticker: run_final.sh)
set -e
cd "$(dirname "$0")"
T=$1
echo "$(date -u +%FT%TZ) stage $T start"
python3 engine.py $T TRAIN & P1=$!
python3 integrity.py $T & P2=$!
wait $P1; wait $P2
echo "$(date -u +%FT%TZ) $T TRAIN trades + manifest done"
python3 analyze.py train
echo "$(date -u +%FT%TZ) selection_train.json sha256 $(sha256sum results/selection_train.json | cut -c1-16)"
python3 engine.py $T TEST
echo "$(date -u +%FT%TZ) stage $T done"
