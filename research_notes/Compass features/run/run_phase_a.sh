#!/bin/bash
# Phase A, in the order it was run. Inputs are the stored ThetaData and UW files under $SP (see fetch/README.md); every step
# is deterministic and resumable. The exploration steps never open AVGO, MU or QQQ (fcommon.guard_ticker) and never read an
# outcome in a held-out month; the holdout steps run once, at the end, for the features the screen passed.
set -e
cd "$(dirname "$0")"
export POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1
EX="SPY IWM SPXW AAPL AMZN GOOGL MSFT NVDA TSLA AMD INTC META"

# exploration
python3 -I daily.py $EX                       # 15:59 closes, regular and opening ranges
python3 -I build_0dte.py expl $EX             # 0DTE base trades (+ X1, X3, D6, D7, ES3 inputs)
python3 -I build_eod.py expl $EX              # EOD inputs (pass 1) and the 1-60 DTE base trades (pass 2)
python3 -I tiers.py $EX
python3 -I uw_features.py expl                # SPY, IWM, SPXW (UW's SPX)
python3 -I screen.py expl A                   # veto, venue, expiry/strike
python3 -I gex_check.py                       # the gate for SD1, SD2, X2
# python3 -I x2.py expl                       # only when the gate passed
python3 -I screen.py expl B                   # strike distance, exit, direction
python3 -I verify_features.py expl

# holdout (once; the features the screen passed are named on the screen line)
python3 -I daily.py --hold QQQ AVGO MU
python3 -I build_0dte.py hold
python3 -I build_eod.py hold
python3 -I tiers.py --hold QQQ AVGO MU
python3 -I uw_features.py hold
python3 -I screen.py hold V1 VN1 X3          # the three the screen passed (run once more after the duplicated-row fix: see the report)
python3 -I verify_features.py hold
python3 -I deviations.py hold
python3 -I write_report.py
