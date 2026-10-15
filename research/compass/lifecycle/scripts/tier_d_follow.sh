#!/bin/bash
# Runs the daily-tier research for each single name as soon as its option EOD pull finishes ("<SYM>: done" in the pull
# log), skipping roots already run; exits when the pull writes TIER_D_DONE and every finished root has been run.
LOG="$1"; OUT="$2"
cd "$(dirname "$0")/.."
WORK=$(python3 -c "from lc import paths; print(paths.WORK)")
while true; do
  for sym in $(grep -oE "^[0-9:]+ [A-Z]+: done" "$LOG" | awk '{print $2}' | tr -d ':'); do
    case "$sym" in SPY|QQQ|IWM) continue;; esac
    if [ ! -f "$WORK/runs/drows/$sym/run.json" ]; then
      echo "$(date -u +%H:%M:%S) research $sym" >> "$OUT"
      python3 scripts/run_tier_d_research.py "$sym" >> "$OUT" 2>&1 || echo "$(date -u +%H:%M:%S) FAILED $sym" >> "$OUT"
    fi
  done
  if grep -q TIER_D_DONE "$LOG"; then
    pending=0
    for sym in $(grep -oE "^[0-9:]+ [A-Z]+: done" "$LOG" | awk '{print $2}' | tr -d ':'); do
      case "$sym" in SPY|QQQ|IWM) continue;; esac
      [ -f "$WORK/runs/drows/$sym/run.json" ] || pending=1
    done
    [ $pending -eq 0 ] && { echo "$(date -u +%H:%M:%S) ALL_SINGLES_DONE" >> "$OUT"; exit 0; }
  fi
  sleep 60
done
