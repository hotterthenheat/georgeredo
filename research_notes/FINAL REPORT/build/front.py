"""front.py — the opening pages of the final report: the title, the rules that passed, the holdout ledger (the
report's copy, updated), the data inventory, the forward tracking and the method."""
from __future__ import annotations

from base import RN

HEAD = """# Final research report

**Repository:** georgeredo, branch `claude/lucid-heisenberg-bpyq7k`. **Built:** 2026-10-23 by
`research_notes/FINAL REPORT/build/` (`build.py`, then `render.py` for the PDF); **re-scored 2026-10-24 at Robinhood's fees**.

**Fees: Robinhood is primary.** From 2026-10-24 the research's default cost model is Robinhood's options fee schedule
(`docs/FEES_ROBINHOOD.md`, read 2026-10-24). In short: $0 commission; ETF options about $0.04 a contract to buy and $0.06
to sell (a 1-lot); SPXW $1.04 a contract a side under $1.00 of premium and $1.13 at $1.00 and up (non-Gold); nothing at
expiry or settlement. The studies charged $0.65 a contract each way, or $0.68748 with pass-throughs, or $0.70 for the
older Compass studies; SPXW was $1.18748 / $1.27748.

Every trade is re-priced on its own fills: buys at the ask and sales at the bid, exactly as the study filled them. The
study's modelled fee is added back and Robinhood's is charged. Every figure is printed at Robinhood's fees first, with the
study's own beside it on page 1 and in each section's fee table.

Where a trade file lacks a leg's price, side or exit, Robinhood's fee is inferred from the rule. Those rows are marked ‡
and labelled "Robinhood fees inferred from the rule" in their section. Vendor-recorded rows (§) carry no fee in either
column.

Every verdict stays exactly as pre-registered, on the study's own fees. The column "would the verdict differ at Robinhood
fees?" only runs the frozen pass rule on the Robinhood-fee returns. It is descriptive, not a new verdict.
**Inventory of every study:** `INVENTORY.md`, the file beside this one.

This report is read-only with respect to the research. It adds no test, variant or fetch, opens no holdout and
changes no rule. Every metric is recomputed from a study's committed trade-level output, or from the scratchpad copy
that INVENTORY.md names, with one exception: two studies (#31 and #40) were rerun deterministically from their
committed scripts at their own commits, on the same stored inputs. Step 6's rule membership (#17) is recomputed by its committed
`step6/trade.py` `choose()`, on the scratchpad population it was built from. Where a figure cannot be produced, the report
writes "not available — <why>". GeorgeFi's own recorded card returns appear only in sections marked
**vendor-recorded, not re-marked** (#1, and the grade check in #29f).

**Units.** Return per trade is given as:

- % of premium paid, for long options;
- % of max risk, for spreads and butterflies;
- % of the credit received, for naked short straddles and strangles;
- % of cash set aside, for cash-secured puts;
- % of notional, for stock trades. Their "$" column is $ per 100 shares, because every stock trade here is 100 shares.

$ per trade is one lot, after every fee the study charged.
"""

SUMMARY_NOTE = """One row per strategy, on the period that carries its verdict, sorted by mean trade at Robinhood fees (% in
each row's own unit), with the mean at the study's own fees beside it. The table pools all names when a study judged them together, and shows one row per name or variant when it did
not. The interval is the 20-session moving-block bootstrap of the mean % a trade (`audit_lib.session_stats`, 2,000
draws). It is "n/a" when the period has fewer than 60 sessions. "Biggest win/loss" are $ for one trade, with its entry
date. The verdict is the study's own, as pre-registered. The last column is descriptive. It runs the study's frozen pass
rule on the Robinhood-fee returns: through the study's own code where the trade list allows (the Compass features' Δ, the
direction screen); otherwise through the rule's computable part, with the report's block-20 interval, and it says so. ‡ marks
a row whose Robinhood fees are partly inferred from the rule. § marks a vendor-recorded row."""

PASSED = """## The rules that passed, with their numbers

Seven rules passed a pre-registered holdout or single test. None of them makes a losing base set profitable, except H7,
which is a stock trade.

| rule | what it does | the test | result (Δ = with − without, points of the debit a trade; H7 = $ a trade) | forward N (committed) |
|---|---|---|---|---|
| **V1** spread veto | skip a base trade whose (ask − bid) ÷ mid > 10% at entry | Compass features Phase A holdout (a2e14e4, 2a49049) | Δ **+2.61 [+1.76, +3.46]**; −8.43% with vs −11.03% without | 23,960 sessions (out of reach) |
| **X3** 14:00 exit | sell a 0DTE long entered before 14:00 at the 14:00 bid | same | Δ **+7.78 [+4.14, +10.95]**; −9.51% vs −17.29% | 369 sessions |
| **VN1** venue | keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid | same (failed on the first, duplicated, read) | Δ **+1.18 [+0.50, +2.20]** | 587 |
| **BV1b** | V1 at 3% | Phase B holdout (b6737c7, e5dd8c6), not virgin | Δ **+4.30 [+2.66, +5.85]**; −6.73% vs −11.03% | 481 |
| **BX3e** | X3 on the physically settled names only | same | Δ **+7.67 [+4.23, +10.69]**; −11.03% vs −18.71% | 265 |
| **BC3** | V1 veto + X3 exit + D6 direction, against all base trades | same | Δ **+6.77 [+4.82, +8.19]**; −4.26% vs −11.03% | 341 |
| **H7** pre-FOMC drift | 100 shares from the close before a 2:00 pm FOMC statement to the 13:58 bar | single test (edca472, 6c94bb8) | SPY **+$70.43 [+14.64, +129.31]**, QQQ **+$69.59 [+23.10, +122.14]**; QQQ clears Bonferroni at m = 13 | 366 SPY / 483 QQQ trades (fcc1f4d) |

These rules are frozen as written:

- Compass's decision layer uses V1, X3 and VN1 exactly as frozen (`FORWARD_RULE.md` b101ae1, `PREREG_PICKER.md` §4
  fees).
- The daily forward job counts every rule here against its N. No verdict is read before a rule reaches its N.

Also positive on a single historical read, but not passed:

- S17's index put-writing passes its carry-lane rule (#7j). It is a carry with alpha 0, not an edge.
- H8 passes for QQQ at 1× only.
- Phase 3 hyp F (#25) passes its four-part rule on the OOS that chose it.
"""


def ledger() -> str:
    src = (RN / 'HOLDOUT_LEDGER.md').read_text()
    head, _, rest = src.partition('| study (commit) |')
    table = '| study (commit) |' + rest.split('\n\n**Running count')[0]
    tail = '**Running count' + rest.split('\n\n**Running count')[1] if '\n\n**Running count' in rest else ''
    add = """| Compass EMA (`9af93fc`) | prereg only; the run was stopped before computing | — | 0 | 0 |
| DR-GCE gates 1, 2 (`01d5c8e`, `041baba`, `b20eb9c`; `294d4f2`, `00eb3d5`) | SPXW 0DTE exploration 2023-12-01 → 2026-10-09, the 28 months never opened (guard selftest 5/5) | Mode 1 / Mode 2 touch gate; direction vs volatility | 0 | 0 |
| This final report (2026-10-23) | reads only spans already read; reruns #31 (exploration X only) and #40 (2025-02/03 only) | — | 0 | 0 |"""
    return ('## The holdout ledger (the report\'s copy)\n\n'
            'This is a copy of `research_notes/HOLDOUT_LEDGER.md` (9af93fc) with three rows added after it. The committed ledger '
            'is unchanged: nothing in it is wrong, it only predates DR-GCE.\n\n'
            '**Holdout A** = index direction data 2017-06-01 → 2022-05-12. **Holdout B** = the 28 drawn months.\n\n'
            + table.rstrip() + '\n' + add + '\n\n' + tail.strip() + """

**What has read each holdout, and what remains unopened**

| holdout | read by | unopened for |
|---|---|---|
| A (2017-06 → 2022-05-12) | ≥ 133 rules (S04, S06, S12, S16a, S03/S16b, H10, H17, S17, the daily tier, V6, V8, Compass H1, H4, H7/H8, Compass features, the scanner's signal check) | every rule from the scanner on: Compass ICT (#43), Compass EMA (#44), the EMA ladder (#40), DR-GCE (#45), step 6 (#17) |
| B (28 months) | ≥ 15,966 rules, before the holdout was defined (steps 1–5, S01/S02, S09/S10, S15, the short-premium grids, Tier I, V5/V7, the engine audit, phases 2–3, the picker) | the rules defined after it: #17, #39, #40, #43, #44, #45 ("unopened for this rule only") |
| Compass features' own (43 months + AVGO, MU, QQQ) | opened: Phase A twice (the first on duplicated rows), Phase B once | — |
| Compass direction: 1,600 names 2019-01 → 2022-12 | — | **unopened** (the screen failed) |
| Edge H3: 1,600 names | — | **unopened** (not fetched) |
| The scanner's held-out tickers AMD, AVGO | — | **unopened** |
| Lifecycle hold-out 2025-10-01 → 2026-10-09 | opened once per group (Tier I, L-A3, H-FLO, the daily tier, P1/P2) | — |
| V1–V8 hold-outs | each opened once | — |
| ThetaData lanes TEST (2025 → 2026-10) | read (T-A, T-B, T-C, T-E, H15) | — |
| Phase 2/3 OOS 2025-01 → 2026-10-09 | read once each; this is the tracker's and the SPXW test's "selection" period | — |
| Forward from 2026-10-12 | the paper tracker (9 sessions to 10-22) | features (0 sessions counted), H5 (none), H6 (from 2026-11-02), H7 (from 2026-10-28) |
""")


DATA = """## The data inventory

All market data is stored files. Nothing was fetched for this report.

| data | span | where |
|---|---|---|
| Same-day option chains, 1-minute NBBO (every contract) | SPY 989 sessions 2022-11-11 → 2026-10-22; QQQ 989, same span; IWM 629, 2024-04-19 → 2026-10-21; SPXW 1,115, 2022-05-13 → 2026-10-22 | scratchpad `theta/data_full/chains/` (forward sessions 2026-10-12 → 21 also committed in `data/theta_forward/`) |
| Underlying 1-minute bars | SPY 3,687 sessions 2012-06-01 → 2026-10-22; QQQ 3,619; IWM 3,618 | scratchpad `theta/data/underlying/` |
| SPX prints and VIX, 1-minute | SPX 2,362 sessions, VIX 2,395, 2017-06-01 → 2026-10-22 | scratchpad `theta/data/index/` |
| Official closes | Cboe's SPX history 1975 → 2026-10-21; UW daily bars | `data/official_closes/` |
| Option EOD and open interest, every contract | the account's bulk files 2026-10-06 → 12; index-ETF option EOD 2012-06 → 2026-10 | `data_lake/thetadata/flat/`, scratchpad `lifecycle/eod_by_exp` |
| Stock daily bars, every symbol | 2012-06 → 2026-10-13 (26,855 symbols listed) | `data_lake/thetadata/stock_eod/` |
| Unusual Whales per-ticker histories | daily bars, greek exposure, IV rank, realised volatility, VRP, earnings; about one year to 2026-10-13 | `data_lake/unusualwhales/` |
| Unusual Whales recorder (flow, dark pool, net-prem ticks, minute bars, OI by strike) | from 2026-10-21 | `data_recorder/` (git-ignored) |
| Post-market 1-minute bars (UW) | 16 name-sessions fetched once for the after-hours study, plus the backtest cache 2025-05 → 2026-10 | `data/postmarket_1m/`, scratchpad `bt/cache` |
| Macro calendar (FOMC, CPI, payrolls) | 2022 → 2027 | `data/macro_events_2022_2027.csv` |
| GeorgeFi evidence (cards, books, API captures) | 2026-01-20 → 2026-10-13 | `evidence/` at 7dfea57 |
| Trade-level outputs used here and not committed (kept in the scratchpad) | tracker `data_recorder/paper_backtest_official` (316 MB); step 6 population `step6/` (39 MB); features `features_work/{expl,hold}`; direction rerun `dir/work/expl_trades.parquet`; EMA ladder rerun `ema_ladder_out/` | as listed |
"""

FORWARD = """## Forward tracking

**The daily job.** `scripts/daily_forward.py` runs after each close, in this order, stopping at the first failure:

1. fetch the session's seven files: the Theta Terminal on the owner's machine, or one SDK login inside the owner's
   window;
2. verify them;
3. merge them;
4. read the official close: UW's daily bar, or Cboe for SPX;
5. read the post-market decision price;
6. replay the session through the live paper tracker (condor_em1, fly5, condor_d20), settled on the official close;
7. append it to `research_notes/Compass phase 3/forward_cumulative.md`;
8. run the Compass features forward test (V1, X3, VN1, BV1b, BX3e, BC3 under `FORWARD_RULE.md` b101ae1);
9. run the edge-search forward tests (H5, H6 and H7).

A session is appended only whole. No verdict is read before a model reaches its committed N. Interim figures are
logged without early stopping.

**Where it stands (2026-10-23).**

- **The paper tracker's period iii:** 9 sessions, 2026-10-12 → 22. Results in that window:
  - condor_em1: 44 trades, +$9.99 a trade.
  - fly5 iron: 36 trades, +$52.93.
  - condor_d20: 41 trades, +$23.38.

  This is an execution and data-quality record. The thresholds are 60 → 120 sessions for condor_em1, 150 for
  condor_d20's D1 re-test, and 250 a name for the flies.
- **The Compass features:** 0 forward sessions counted (from 2026-10-22).
- **H5:** forward from 2026-10-23.
- **H6:** from 2026-11-02.

**H7 live.** The pre-FOMC drift is wired into step 8 of the job (712b0ad). It trades 100 SPY / 100 QQQ from the official
close before each scheduled 2:00 pm statement to the 13:58 bar's close. It runs on the official closes and minute
bars the job already keeps, with the macro calendar and H7's dividend table. The first forward trade is the statement
of 2026-10-28. N is 366 trades for SPY and 483 for QQQ (`FORWARD_RULE_H7.md` fcc1f4d), about 46 and 60 years. The
verdict is read at N only.

**The H9 removal.** H9 (overnight drift) was registered forward-only (edca472) and wired in 712b0ad. The owner withdrew
it on 2026-10-23, and it was removed from the job (c68f389) before any H9 forward row was written. The registered rule
is unchanged.
"""

METHOD = """## Method (every section)

- **Fills.** As each study ran them: ask in, bid out, at the 1-minute NBBO unless the section says otherwise. Older
  studies (#2, #4b, #5) used Unusual Whales bars with a modelled spread. Each section states its fee schedule.
- **Fees (from 2026-10-24).** Every trade is re-priced at Robinhood's fees: `pnl_rh = pnl + the study's fee − Robinhood's
  fee`, on the study's own fills (`scripts/fees_robinhood.py`, `docs/FEES_ROBINHOOD.md`).
  - The study's fee is taken from its own fee column when the file has one, and otherwise from its code's formula.
  - Robinhood's fee is figured from each leg's contracts, side and price.
  - A contract held to expiry or settlement pays no exit fee. Where a study charged a sale on a contract held in the money
    to the close (steps 2 and 4), Robinhood's fee is $0.
  - Where only the structure's total price is kept, a leg's price is taken as its share of that total. It is used only for
    the SEC fee's cent and SPXW's $1.00 tier. A row that needed any other guess is labelled "inferred".
  - Stock trades: the studies' $0.01 a share on an auction fill is their fee allowance, so it is replaced. Their $0.005 a
    share on a bar fill is half the spread, so it stays.
- **Win and loss.** A win is a trade whose P&L after fees is above zero. A breakeven counts as a loss.
- **Session span.** The calendar is every stored SPY minute-file session in the period's span. A session with no trade
  counts as zero.
- **Interval.** The interval is `audit_lib.session_stats` with blocks of 20 sessions (2,000 draws, its own seed), for the
  mean $ and the mean % a trade. A period under 60 sessions gets no interval. Some studies used other intervals, such
  as iid session or trade bootstraps, so the numbers here can differ from a study's own; the verdict is always the
  study's.
- **Drawdown.** Max drawdown is taken on the cumulative $ of session sums. The longest drawdown is the longest run of
  sessions spent below a previous peak.
- **Top-5 share.** This is the five best sessions' share of a positive total. Where the total is ≤ 0, the five best
  sessions' $ and the total without them are printed instead.
- **Random baselines.** Each is quoted from the study that computed it. For S10, S12, S12b and S16b, the mean of the study's own matched-control rows (seeds 11–15) is taken from the same trade file. None was re-simulated.
- **By year.** All periods together, grouped by entry year.
- **Charts.** Cumulative $ per name and pooled, with each period shaded and labelled.
"""
