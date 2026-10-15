#!/bin/bash
# After a root's grid+stage1 run ends, run its entry-rule and volatility runs.
L=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/lifecycle
cd "$(dirname "$0")/.."
R=$1
until grep -q "stage1: done" $L/grid_$R.log || grep -q Traceback $L/grid_$R.log; do sleep 15; done
python3 scripts/run_more.py $R entry > $L/more_$R.log 2>&1
python3 scripts/run_more.py $R vol >> $L/more_$R.log 2>&1
echo ALL_DONE >> $L/more_$R.log
