# georgeredo

**Fresh start, 2026-10-16.** At the owner's request, everything built before this date was cleared from this branch: the GeorgeFi research, the Compass studies, the backtests and the reports. Nothing was deleted from history. All of it is in commit `7dfea57`, and `git checkout 7dfea57 -- <path>` brings any file back.

**Kept:** raw market data only.
- `data_lake/`: the vendor downloads (see `data_lake/README.md`).
- `data_lake/fetch/`: the scripts that download them.

**Step 1 (done):** every same-day (0DTE) option contract on SPY, QQQ, IWM and SPX, broken down one contract at a time: 1,176,935 contracts over 3,687 sessions, checked against the raw quotes (`step1/`).
