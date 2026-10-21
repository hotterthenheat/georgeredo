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

**Step 4 (done):** buying on the turn up off the low and selling near the high with a trailing stop, retested on 12.1 million trades.
- A trailing stop beat holding but still lost.
- Turn-up buys caught more runners and ended near zero.
- Of 126 rules that made money in both periods, the 11 biggest all failed the stress test.
- See `step4/README.md`.

**Step 5 (done):** can what was visible at the turn tell the runners from the duds? Two models read 42 measurements known at the minute of buying for all 1.6 million turn-up buys, trained on 2022–2024 and scored once on 2025–2026.
- Runners can be partly told apart: the top 1% reached 3× the price paid 26% of the time, against 6% for all turn-up buys.
- They still don't pay reliably. Three in four of the best picks fail, and no way out of 184 kept the winners' runs. What profit there is comes from a handful of days.
- Trading only the top 1%: every pick made money in total, almost all of it on one day (2025-11-20); without its best 5 days it lost $620,114, and one pick a day lost money.
- Adding each contract's minute-by-minute trading volume (3,687 sessions) barely changed how well the models rank, and their top picks still rest on a handful of days.
- See `step5/README.md`.

## Compass engine audit (2026-10-21)

The owner's 16-module Compass specification audited under its own guardrails (no invented weights, friction-adjusted, picked on 2022–2024 and read on 2025–2026). Six groups of tests on the data on disk, one report: `reports/Compass engine audit.md`, with every number's script under `research_notes/Compass engine audit/`. No directional rule survives after fees; what holds is the 15:58 flat, the −32% backstop, a breakeven lock at +0% with a target on, a trailed remainder, the r,q pricer read off put-call parity, Method A flips with three-book slicing, a net/gross confidence in place of the sign gate, the MOC magnitude as a volatility gauge, and an ATR > 1.5 block on counter-trend fades.
