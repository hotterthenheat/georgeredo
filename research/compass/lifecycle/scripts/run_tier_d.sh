#!/bin/bash
# Tier D pull: index ETFs from 2012-06, Tier A single names from 2017-06 (FB for META's pre-rename years). Resumable.
set -a; . /tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/secrets/research.env; set +a
cd "$(dirname "$0")/.."
python3 -I scripts/pull_tier_d.py SPY,QQQ,IWM 2012-06-01 2026-10-09 --nw 4
python3 -I scripts/pull_tier_d.py FB 2017-06-01 2022-06-10 --nw 4 --no-minutes
python3 -I scripts/pull_tier_d.py AAPL,MSFT,NVDA,AMZN,GOOGL,GOOG,META,TSLA,AMD,AVGO,NFLX,ADBE,CRM,INTC,QCOM,MU,TSM,SMCI,PLTR,COIN,MSTR,JPM,BAC,V,UNH,LLY,COST,XOM,DIA,IVV,VOO,XLF,SMH,SOXL,TQQQ,SQQQ,TLT,HYG,LQD,GLD 2017-06-01 2026-10-09 --nw 4 --no-minutes
echo TIER_D_DONE
