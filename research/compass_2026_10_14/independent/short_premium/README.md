# Independent short-premium study (SPY, QQQ, IWM, SPXW, XSP; 0DTE and 1DTE) — status: BLOCKED, no results

**No P&L numbers exist in this folder, because no study data could be pulled.** Nothing here supports or rejects any setup.

## What is here
- `PREREG.md`: the full design, committed *before* any study data was pulled. It covers the universe, the 2025-01-02 → 2026-10-09 window, five setups (straddle,
  strangle, put/call credit spreads, iron condor) at 0DTE 10:00/13:00/15:00 and 1DTE 15:50 entries, NBBO-adverse fills, the H14 exit rule, the five-draw random
  baseline and the COMPASS_RESEARCH_PLAN §1 gate.
- `code/fetch.py`: the paced fetcher. It uses the shared Terminal only, with 2 concurrent requests, hashes raw data into `results/raw_index.jsonl` and backs off on
  session errors.
- The contract-day list (2,220 root-expiries over 445 sessions, built from live `list/expirations`) is written to `results/contract_days.csv` by `fetch.py`.
  It is not committed yet and will be committed with the data run, before the random-baseline draws.

## Why it is blocked (2026-10-15)
- Between 15:30 and 15:32 UTC the shared Terminal on the box (127.0.0.1:25503, started by the Compass 2020-2021 agent at 15:30:07) served real data:
  SPY/SPXW/XSP expirations, a 5-minute SPY 0DTE chain and an SPXW two-day chain, about 9–16 s per chain request.
- From 15:30:52 its log shows intermittent `UNAUTHENTICATED: Invalid session ID`, and from about 15:36 every request fails (112 warnings by 15:46). The box
  showed a single Terminal listener on the port, so another Terminal is most likely logged in with the same key **off the box** (one login per key, plan §8).
  The likeliest candidate is the PC Terminal that `theta-terminal.cmd` restarts from Task Scheduler.
- Following instructions, this study did not start, stop or restart any Terminal. The fetcher was stopped after about 10 minutes of failures, with 0 study files saved.

## To resume
Make sure no Terminal for this key runs anywhere except the box: disable the Task Scheduler restart on the PC, or use a separate key. Then run
`python3 code/fetch.py` (about 2,220 chain requests, roughly 3–4 h at 2 concurrent requests). After that, run the analysis described in PREREG.md.
