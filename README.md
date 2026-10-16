# georgeredo

**Fresh start, 2026-10-16.** At the owner's request, everything built before this date was cleared from this branch: the GeorgeFi research, the Compass studies, the backtests and the reports. Nothing was deleted from history. All of it is in commit `7dfea57`, and `git checkout 7dfea57 -- <path>` brings any file back.

**Kept:** raw market data only.
- `data_lake/`: the vendor downloads (see `data_lake/README.md`).
- `data_lake/fetch/`: the scripts that download them.

**Step 1 (done):** every same-day (0DTE) option contract on SPY, QQQ, IWM and SPX, broken down one contract at a time: 1,176,935 contracts over 3,687 sessions, checked against the raw quotes (`step1/`).

**Step 2 (done):** can a same-day contract make +100%? Every contract was bought at nine times of day, sold the first minute its bid doubled, and otherwise held to the close: 10.5 million trades, checked against the raw quotes.
- Near the money, 29% of trades doubled.
- Every group still lost money, because the share needed to break even is higher.
- See `step2/README.md`.

**Step 3 (done):** every one of the 10.5 million trades broken down: how far each ran (+25% to +1,000%), what the losing ones did first, 108 ways out (targets, stops, time exits) and 9 conditions known when buying. Each rule was picked on 2022–2024 and checked on 2025–2026.
- A −50% stop shrank the losses.
- Profit targets raised the win rate but lowered the average.
- Nothing made money in a way that held up.
- See `step3/README.md`.
