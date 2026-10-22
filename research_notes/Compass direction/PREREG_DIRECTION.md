# Compass direction, pre-registered: post-earnings drift in 31–60 DTE options

Written 2026-10-22 and committed alone, before any result of this study is computed. Nothing in this file was computed
from an option's return, a P&L, an earnings-day return, a post-earnings move or any relation between them. To write it,
these were read and nothing else: the git history of this repository (commit messages, the notes and reports at HEAD and
at `75c29c9^`, the commit before the "Fresh start" removed them), `research_notes/Compass features/PREREG_FEATURES.md`
(commit `a2e14e4`, sha256 `840f7671…5d314cfc62cd`) and `INVENTORY.md`, the code of `research_notes/Compass features/run/`
(fcommon, stats, tiers, build_eod), the UW earnings calendar's columns `ticker, report_type, report_date, report_time` (never
an EPS, an estimate or a surprise), ThetaData's list of expirations per option root (`data_lake/universe/expirations.jsonl.gz`),
the stored files' schemas, and three timing measurements of ThetaData requests on OPENED cells (DECK, ULTA, ROKU, ETSY, ZS in
February–March 2024: request seconds and row counts only — no price was looked at).

**Disclosure — what the author already knows about this hypothesis on opened data.** The headline lines of earlier notes were
read to build the ledger (§1). Among them: S08 (2026-10-14, `research/compass/05_results.md` at `75c29c9^`) found, on the
optionable universe 2024-01 → 2026-10 (10,426 reports), that the sign of the event-day move predicts nothing at 1–21
sessions on the underlying (−8 bp [−29, +11] absolute and −5 bp [−23, +13] against the universe at 10 sessions from the next
open), and that beats underperform after the gap ("sell the beat"). That is the same signal as this study's, on the
underlying, on cells this study's exploration set partly re-uses (2024 → 2026). It is the reason the prior for a pass here is
low, and it is stated before anything is computed.

---

## 1. The opened ledger: what earlier studies read against outcomes

"Opened" = a (ticker, month, data kind) that an earlier study read against an outcome (a return, a P&L, a realized move, a
hold rate). Sources: `git log --all --stat` (306 commits), the commit messages, `reports/`, `research_notes/*`, `step1/`–`step5/`,
and the files removed by `75c29c9` read with `git show 75c29c9^:<path>` (`research/compass/05_results.md`, `07_coverage_report.md`,
`04_protocol.md`, `intel/02_volatility_pricing.md`, `intel/06_price_action_atlas.md`, `lifecycle/01_data_inventory.md`,
`lifecycle/06_daily_tier.md`, `lifecycle/12_per_ticker_playbook.md`, `registry.jsonl`).

| study (commit) | names | span | data kind read against outcomes |
|---|---|---|---|
| **S07** daily triggers (`3562b95`) | every optionable root with ≥ $50 M prior-year median dollar volume (1,119 / 1,210 / 1,510 a year) | outcomes 2024-01-02 → 2026-10-13; 2023 read as the universe year | stock EOD bars |
| **S08** earnings family (`f3ec790`) | the S07 universe: 10,439 reports on 1,186 names | 2024-01-02 → 2026-10-13 (2023 inputs) | UW earnings calendar × stock EOD; **post-earnings drift by surprise sign and by event-day-move sign, next-open entry, 1–21 sessions** |
| **S13 / S14** pre-earnings run-up; cross-sectional momentum/reversal (`eff2382`, `d3e732a`) | the S07 universe | 2024 → 2026 | stock EOD bars |
| **S11** event verticals (`0a4513b`) | 520 roots, earnings and breakout windows (12 % sample) | 2024-01-02 → 2026-09-01 | single-name option EOD, one expiry per event |
| **V1 / V2** universe straddles; earnings straddles (`df4fe32`, `152f786`) | 1,086–1,700 optionable names a cycle | 2023-11 → 2026-09 | UW closing chains, ThetaData closes |
| **V3** single-name same-day premium (`e4e4cea`) | AAPL AMZN AVGO GOOGL META(FB) MSFT NVDA TSLA AMD INTC MU | 2017-06 → 2026-10 | expiry-day 1-min chains |
| **S05/S06** Tier A screen, **atlas**, **V4**, **V6** (`ad7ee20`, `0d706b6`, `1660366`) | the 41 names of the 1-min bar cache (AAPL ADBE AMD AMZN AVGO BAC COIN COST CRM DIA FB GLD GOOG GOOGL HYG INTC IVV JPM LLY LQD META MSFT MSTR MU NFLX NVDA PLTR QCOM SMCI SMH SOXL SQQQ TLT TQQQ TSLA TSM UNH V VOO XLF XOM), SPY QQQ IWM | 2017-06 → 2026-10 | 1-min underlying bars |
| **Lifecycle** daily tier (`50de62a`, `2b60ef2`) | SPY QQQ IWM; 40 Tier A singles queued, FB done; AAPL option EOD on disk | ETFs 2012-06 →; FB 2017-06 → 2022-06; AAPL EOD 2015-03 → 2025-09 | option EOD, every expiry |
| **Engine audit, horizons** (`b84fa3c`) | the top 20 (NVDA TSLA AAPL MU INTC AMZN TLT META EWZ PLTR AMD IBIT MSFT GOOGL MSTR HYG AVGO SOFI ORCL GME) | daily bars 2020 → 2026-10; **earnings-day moves of its 16 reporting names 1996 →** | stock EOD, UW earnings |
| **Compass features** Phase A/B (`2a49049`, `e5dd8c6`) | SPY QQQ IWM SPXW; AAPL AMZN AVGO GOOGL MSFT NVDA TSLA AMD INTC MU META (holdout AVGO MU QQQ also read) | ETFs 2012-06 →; singles 0DTE 2017-06 →, EOD 2022-11 → 2026-10 | option EOD and 1-min chains, bars, UW |
| S01–S04, S09, S10, S12, S15–S17, V5–V8, steps 1–5, phases 2–3, picker, SPXW, after-hours, the forward tracker, the deep-research and high-win-rate rounds, the GeorgeFi reverse-engineering | SPY QQQ IWM SPX/SPXW (S17 SPY/QQQ 2012 →; V8 SPXW/SPY month-ends 2017 → 2022) | 2012 → 2026-10 | index products only |
| Retail options edge sweep L1–L6 | literature; SPY; the S11 chains | 2024 → 2026 | — |

**What that leaves.** From 2023 on, every optionable name is opened (S07/S08's universe year 2023, outcomes 2024 →; V1/V2
from 2023-11). Before 2023, single names were opened only by name: the lists above. The ledger's name set
(`ledger.py OPENED`, 134 names) is that union **plus, conservatively, names never read against an outcome before 2023**: the
step-0 inventory's 30 singles and 10 ETFs, the recorder's 24 names, the 2025 and 2026 Tier A lists (the top 100 by dollar
volume each year, the S05 pull's queue), and every index/ETF root. Not opened, therefore: **every other single name, every
month before 2023.**

Opened names (134): AAPL ABBV ACN ADBE AMAT AMD AMZN APP ARM ASML ASTS AVGO BA BABA BAC BKNG BMNR C CAT COIN COST CRCL CRM
CRWD CRWV CSCO CVX DELL DIA DIS EEM EFA EWZ FB FXI GDX GE GEV GLD GME GOOG GOOGL GS HD HIMS HOOD HYG IBIT IBM INTC INTU IREN
IVV IWM JNJ JPM KO LLY LQD LRCX MA MARA MCD META MRK MRVL MSFT MSTR MU NBIS NDX NDXP NFLX NKE NOW NVDA NVDL ORCL PANW PDD PEP
PFE PG PLTR QCOM QQQ RSP RUT RUTW SBUX SGOV SKHY SLV SMCI SMH SNDK SNOW SOFI SOXL SOXS SOXX SPCX SPOT SPX SPXW SPY SQQQ TLT
TMO TQQQ TSLA TSLL TSM TXN UBER UNH V VIX VIXW VOO VTI WFC WMT WULF XBI XLE XLF XLI XLK XLP XLU XLV XOM XSP.

**What the unopened cells need, and what is obtainable.** (a) Option EOD: ThetaData's `/option/history/eod` serves single
names from 2012-06 (INVENTORY.md §1a, the plan's PRO tier); none of it is on disk for an unopened name, so it is fetched
(§7). (b) Bars for the earnings-day return: ThetaData stock EOD for every symbol, on disk for 2019 (`$SP/lake/stock_eod`) and
2020 → 2026 (`data_lake/thetadata/stock_eod`); before 2019 it would have to be fetched (2–4 s a name-year, measured), and
CTA-listed names have none before 2017. (c) Report dates and times: the UW calendar, 1996 → 2026-12, on disk. **The
window chosen is 2019-04 → 2022-12**: every month in it has (a) obtainable, (b) on disk for every symbol (the 60-session
liquidity window of an April 2019 report starts in January 2019), and (c) on disk.

**Size of the unopened pool in that window** (metadata only): 3,280 optionable names (an option root listed during the
window, a ticker of one to five letters) carry a quarterly UW report with a known time (pre-market or post-market) dated
2019-04-01 → 2022-12-31; 3,201 of them are not opened. Their timed reports: 45,247; the holdout half's are **22,598**
(§2). Enough data is left; the binding limit is the fetch budget (§7) and, above all, power (§8).

---

## 2. The holdout and the exploration set (drawn now)

Drawn with `numpy` 2.5.3 `default_rng` by `ledger.py` (committed after this file; the code that matters is reproduced here):

```python
unopened = sorted(names with a timed quarterly UW report dated 2019-04-01 → 2022-12-31, an option root listed in that window,
                  ^[A-Z]{1,5}$, not in OPENED)                                    # 3,201 names
H = sorted(np.random.default_rng(20261024).choice(unopened, size=len(unopened) // 2, replace=False).tolist())   # 1,600
X = [t for t in unopened if t not in set(H)]                                                                    # 1,601
holdout_events = timed quarterly reports of H dated 2019-04-01 → 2022-12-31, sorted (ticker, date), then permuted by
                 np.random.default_rng(20261025).permutation                       # 22,598; sha256 7d87d8c4…80d316c83
exploration_events = timed quarterly reports of X dated 2019-04-01 → 2026-09-30, sorted, permuted by
                 np.random.default_rng(20261026).permutation                       # 46,344; sha256 ba8b9dca…5206dce05
```

(A UW (ticker, date) carried with two different times is dropped: 80 pairs. Each list's sha256 is of its JSON with no spaces;
`ledger.json` keeps both hashes and every name.)

**The holdout: the 1,600 names of H (appendix A), every month 2019-01 → 2022-12.** Outcomes are read only for trades whose
every session from entry to exit lies in 2019-04 → 2022-12; inputs (the liquidity and tier windows) may reach back to
2019-01. **Rule: no file of an H name in 2019-01 → 2022-12 is fetched or read — inputs included — until the exploration
screen has passed, and then the holdout is read once, by the single test.** Nothing of an H name after 2022 is used at all.

**The exploration set** (any cells, opened or not):
- the 1,601 names of X, reports 2019-04-01 → 2026-09-30 (unopened cells before 2023, opened from 2023);
- the opened names whose option EOD is already on disk (every expiry, every day): AAPL 2015-03 → 2026-10, FB 2017-06 →
  2022-06 (UW files Facebook's reports under META), and AMZN AVGO GOOGL MSFT NVDA TSLA AMD INTC MU META 2022-11 → 2026-10.
  An event of these names is used only where its entry and exit sessions are in those files.

---

## 3. The hypothesis and its mechanism

**H (post-earnings announcement drift, PEAD).** After a quarterly report, the stock keeps moving in the direction of its
earnings-day return for weeks; a 31–60 DTE call bought after a positive earnings-day return and a put bought after a negative
one therefore earn more than the same contracts on both sides.

**Mechanism.** Under-reaction: investors do not fully process what a report implies for later earnings, so the price moves
part of the way on the day and the rest gradually (Ball & Brown 1968; **Bernard & Thomas 1989**, J. Accounting Research 27,
"Post-earnings-announcement drift: delayed price response or risk premium?"; **Bernard & Thomas 1990**, J. Accounting and
Economics 13, "Evidence that stock prices do not fully reflect the implications of current earnings for future earnings"). The
drift also follows the earnings-ANNOUNCEMENT RETURN, not only the accounting surprise (Chan, Jegadeesh & Lakonishok 1996,
J. Finance; Brandt, Kishore, Santa-Clara & Venkatachalam 2008, "Earnings announcements are full of surprises"). It is
**weaker in large and liquid stocks and after 2000**: concentrated in illiquid names (Chordia, Goyal, Sadka, Sadka &
Shivakumar 2009, Financial Analysts Journal) and close to gone among large caps in recent decades (Martineau 2022, Critical
Finance Review, "Rest in peace post-earnings announcement drift"). The vehicle: a 31–60 DTE option carries the direction with
leverage, but pays the spread at entry and exit and ten sessions of time decay; the comparison below takes the spread and
decay out by setting the chosen side against both sides at the same entries.

**Why this vehicle is "the cheapest".** The owner's phrase; PREREG_FEATURES's 31–60 bucket is the multi-day bucket with the
lowest spread on single names in the inventory's October 2026 measurements (29–60 DTE 5.0 % against 8.5 % at 8–14), and its
fixed 10-session exit never meets expiry.

---

## 4. Exact definitions

**Calendar.** Trading days and full sessions as PREREG_FEATURES §2.1 (`fcommon.trading_days` / `sessions`: SPY's option EOD
dates before 2022, `audit_lib`'s NYSE rule from 2022; half days are trading days but not full sessions). New York dates.

**Bars.** ThetaData stock EOD (`$SP/lake/stock_eod/year=2019`, `data_lake/thetadata/stock_eod/year=2020…2026`): a row counts for
day d when its `last_trade` date is d (the stock traded that day); `close` is that row's close, `volume` its volume. Unadjusted.

**Earnings event.** One UW quarterly row (`report_type = quarterly`) with `report_time` pre-market or post-market; reports with
no time are not events (counted). Its dates:
- **reaction session R**: pre-market on day E → E if E is a trading day, else the next trading day; post-market on E → the
  next trading day after E;
- **earnings-day return** g = close(R) ÷ close(P) − 1 with P the trading day before R (the close before the report in both
  cases: E−1 for a pre-market report, E itself for a post-market one). Both closes must exist (else not formed, counted);
- **sign rule**: g > 0 → the call; g < 0 → the put; g = 0 → undefined (the event is in neither arm). **No dead band.**
- "As scheduled before entry": the entry (below) is one full session after R, when the report has been out for at least a
  session; the date and time used are UW's recorded ones, which by then are history, not a forecast. A wrong UW time makes g
  the wrong session's return (noise), never a look-ahead, because the entry is after both candidate sessions.

**Liquidity eligibility (an input, point in time).** The median of close × volume over the 60 trading days ending at P must be
at least **$50 M** (S07's threshold, measured on the days before the report instead of the prior calendar year), with at least
50 of the 60 days present. Else the event is not formed (counted) and nothing of it is fetched.

**Entry.** "Entering the session after the report" is read as **the closing quote of the full session after the reaction
session**: E1 = the first trading day after R; if E1 is a half day the event is not formed (counted). The base trades are
bought at the **closing ask** of E1's option EOD row (ThetaData `/option/history/eod`: the last NBBO at report generation,
PREREG_FEATURES §2.3).

**Expiry and strikes (PREREG_FEATURES §2.2–2.4, the 31–60 bucket).** Among the expiries in E1's EOD file whose last trading day
is 31–60 calendar days after E1, the one nearest 45 days (ties: the earlier); one that expires on a half day is not used (not
formed). On that expiry: K* (both sides standing, |C_mid − P_mid| smallest, ties the lower strike), F = K* + C_mid − P_mid,
IM = C_mid + P_mid, x = (K − F)/IM for a call and (F − K)/IM for a put; the five buckets ITM [−0.50, −0.15), ATM [−0.15, 0.15],
OTM1 (0.15, 0.50], OTM2 (0.50, 1.00], OTM3 (1.00, 1.50], in each the standing contract nearest the centre (ties: the lower
strike). A quote stands when bid > 0, ask > 0 and ask ≥ bid. No standing ATM pair → no trade at that event (counted); a bucket
with no standing contract → no trade in it (counted). **Parity check** (added for single names drawn from a symbol list, where
a ticker can belong to another security in another year): |F ÷ close(E1) − 1| ≤ 5 %, else the event is not formed (counted as
"bars and options disagree").

**Exit (PREREG_FEATURES §2.5, 31–60).** Sell at the **closing bid of the 10th full session after E1** (`nth_session_after(E1,
10)`); no standing bid there → $0 and no exit fee; no EOD row for the contract that day → not formed (counted). **Splits:** an
event is not formed when any trading day from P to the exit has a close-to-close ratio within 10 % of a split ratio of 2:1 or
larger (1/2, 1/3, 1/4, 1/5, 1/10, 1/20, 1/50 and the reverse ratios; the A10.2 rule at `75c29c9^`).

**Fees and the return (PREREG_FEATURES §2.6).** $0.68748 a contract each way (the singles take the SPY figure), nothing on an
exit at $0; r = ((exit − entry ask) × 100 − fee in − fee out) ÷ (entry ask × 100).

**Liquidity tiers (PREREG_FEATURES §2.7, with one stated change).** For the name and the calendar month of E1, on the 20 full
sessions before the month's first session: spread = the median (ask − bid) ÷ mid at the closing quote over every standing
contract 1–60 DTE with |x| ≤ 0.5 (x by its own expiry's F and IM), volume = the median day's total option volume (every expiry
and strike); Tier 1 volume ≥ 900,000 and spread ≤ 5 %, Tier 3 volume < 400,000 or spread > 10 %, Tier 2 otherwise. **Change,
for the fetch's cost (decided now, before any data):** the two quantities are measured on **2 of the 20 sessions, the 10th and
the 20th** (the 20th is the session before the month's first), not on all 20 — every expiry of the name on those two days, one
request each. Tier U when either day returns no rows. For the on-disk names the same two sessions are read from the stored
files, so every name is measured the same way.

**Settlement type**: every name here is a physically settled single stock; the per-settlement split has one row.

**Exploration vs holdout membership.** A trade is a holdout trade when its name is in H and every session from E1 to its exit
is in 2019-04 → 2022-12; an H trade that leaves the window is not formed (counted). An exploration trade: an X name, any
months 2019-04 → 2026-10-21 (the last session on disk), or an on-disk name inside its files' span.

---

## 5. The comparison

Exactly PREREG_FEATURES's direction form (§3.2 family 6): at each event with a defined sign, the base trades are the formed
31–60 trades in every strike bucket on **both sides**. **With** = the trades on the side the rule picks (the call after g > 0,
the put after g < 0); **without** = all the base trades at those same events, calls and puts together. Per entry session s in
calendar order: S_s = Σ r and N_s = the number of trades of the arm entered on s (all names together). Each arm's mean = Σ S ÷
Σ N; **Δ = mean(with) − mean(without)**. (Δ ≈ half the difference between the picked side and the other side.)

**Interval** (PREREG_FEATURES §6, unchanged): the 20-session moving-block bootstrap over the set's full sessions in date order,
`audit_lib.block_draws(n, 20)` (seed 20261022 + 7919 × 20), `weights_from`, 2,000 draws, the same draw W for both arms, Δ_b =
(W·S_with)/(W·N_with) − (W·S_without)/(W·N_without), 95 % percentile interval (`pct_ci`); none under 60 sessions. Sessions:
exploration — every full session from the exploration's first entry session to its last; holdout — every full session
2019-04-01 → 2022-12-30. Effective N: `n_eff_block20` (block-1 ÷ block-20 variance of Δ) and `n_eff_acf` of the per-session
difference series, as `stats.py`. Each arm's `session_stats` (blocks 1, 5, 20). (`audit_lib.py` sha256 3fcbb80b…cfc62cd.)

**Screen (exploration).** Δ > 0 **and** the block-20 interval's lower end > 0. If the screen fails, the holdout is **not
fetched and not read**, and the study ends with the exploration's result.

**Holdout test (once, only after a pass).** The rule unchanged, on the holdout set. **PASS: holdout Δ > 0 with the block-20 95 %
interval's lower end > 0.** The verdict comes from the holdout alone.

**Reported beside the verdict, descriptive, no verdict of their own**: per tier (1, 2, 3, U), per settlement type, per strike
bucket, calls-after-up vs puts-after-down, pre-market vs post-market reports, by year; the exploration split into its unopened
part (X before 2023) and its opened part (X from 2023, the on-disk names); the absolute mean per trade of each arm (the base
loses the spread: Δ > 0 does not make the picked trade profitable, and the report says so).

**One hypothesis, one test.** Nothing is tuned: no threshold on |g|, no other expiry, exit, strike, tier filter or entry day
is tried on either set. Under the null the chance of a false pass through both stages is about 0.025² ≈ 0.0006.

---

## 6. H1 (overnight reversal) and H2

Searched: `git log --all -S"overnight reversal"` (hits `3e86683` and `75c29c9`: the phrase is in the literature note
`zero_dte_microstructure_and_exits.md` — the closing-auction deviation that reverts overnight, Bogousslavsky & Muravyev — not a
study), `git log --all -i --grep=overnight`, the registry (`registry.jsonl` at `75c29c9^`, where **H1 is the level-sweep 0DTE
family, "closed, rejected", 0 of 144 variants**), `reports/`, `research_notes/*`, `step*/`, and 3abida's
`docs/research-2026-10-13/`. The only overnight study is **S16a** (`2430c9b`, "overnight gaps on the underlying", 2017-06 →
2026-10, SPY/QQQ/IWM): gap continuation and gap fade indistinguishable from zero; fading the prior session's close-to-close
move had 6 of 108 cells with a positive lower bound against 2.7 expected by chance, the largest +17.8 bp, and **nothing was
promoted**; its option expression S16b on weeklies lost (−$9.91 [−19.31, −0.26] a contract). **No study named "H1 overnight
reversal" exists, and nothing overnight passed as a stock trade. H2 is not added.** (Another agent's work in progress was
not read beyond a file list.)

---

## 7. The fetch: what, how, the budget, and the cut

- **What**: for each event that is formed up to the option stage (bars present, eligible, E1 a full session, inside its set's
  window): (1) E1's option EOD, every expiry (one request: `option_history_eod(E1, E1, symbol, expiration='*')`); (2) the exit
  session's option EOD of the one expiry chosen from (1) (one request); (3) per name-month, the two tier sessions, every expiry
  (one request each, once). Raw rows kept: date, expiration, strike, right, bid, ask, volume — nothing else.
- **How**: the `thetadata` SDK, one login a run, the key loaded inside the process from the secrets file, never printed,
  logged or written; one request in flight (concurrency measured on 2024 cells gave the same rows a second at 1, 4 and 8 in
  flight); each answer staged as `.part`, verified (the columns and types, the requested date only, the requested expiry only
  for (2), no duplicate (date, expiration, strike, right), no negative price), then renamed into the store — never over an
  existing file. Never between 00:00 and 01:45 New York. The fetcher computes no return and prints no price.
- **Order and cut, independent of any outcome**: each set's events are walked in their seeded order (§2). **Exploration**: the
  fetch stops after **3.0 hours** of fetch time or **0.6 GB** stored, whichever is first. **Holdout** (only after a screen
  pass): it stops after **4.0 hours** or **1.0 GB**. Every fetch stops when the disk's free space falls under 1.5 GB. The set
  tested is every event whose files were all stored before the stop; an event cut mid-way is dropped whole; the H events never
  reached are never read. With the measured cost (about 0.4–2.6 s a request, 2–4 requests an eligible event) the exploration's
  3 hours reach a few thousand eligible events; the holdout's 4 hours most or all of its eligible ones.
- Total new data under 2 GB; total fetch time under 8 hours.

---

## 8. Power, stated before anything is computed

Assumptions (literature, not data): a 45-DTE single-name option's elasticity to the stock is about 8 (ATM) to 13 (OTM3) at
an implied volatility near 45 %, so Δ ≈ 10 × μ, μ the mean signed 10-session drift; the per-event Δ has a standard deviation
near 1.0 (10 × the 10-session stock move of about 9 %), inflated 1.5× by events clustering in earnings seasons. With N events
in the holdout, SE(Δ) ≈ √(1.5 / N); the smallest Δ found with 80 % power at the one-sided 2.5 % the rule implies is 2.8 × SE.

| N (holdout events with trades) | SE(Δ) | Δ found 80 % of the time | the 10-session drift it needs |
|---|---|---|---|
| 3,000 | 2.2 % | 6.3 % | 0.63 % |
| 7,000 | 1.5 % | 4.1 % | 0.41 % |
| 22,000 (every timed H report) | 0.8 % | 2.3 % | 0.23 % |

The published drift for the extreme surprise deciles is about 4 % over 60 trading days long-short (Bernard & Thomas 1989,
1974–1986), about 0.35 % a side over 10 sessions; for every report signed by its earnings-day return it is a fraction of that,
and after 2000 among optionable names it is near zero (Chordia et al. 2009; Martineau 2022; S08 here). **So the test can find
the effect only if every report drifted about as much as the 1970s–80s extreme deciles (power ≈ 0.35–0.7 at N 3,000–7,000);
at the size the recent literature suggests its power is about 0.1.** A FAIL is therefore not evidence that no small drift
exists; it is evidence that no drift large enough to pay through this vehicle's spread showed up. This is stated now so the
result cannot be read otherwise.

---

## 9. Departures from PREREG_FEATURES, all decided here

1. Tiers on 2 of the 20 sessions (§4), for the fetch's cost.
2. The universe is a seeded half of the unopened optionable names with a $50 M point-in-time liquidity floor, not 15 fixed
   names; a parity check (5 %) guards against a ticker that was another security.
3. The entry is on event days only (one entry session per report), not every session.
4. The split rule is A10.2's ratio rule on the bars (no list of the names' splits exists).
5. Report dates are UW's recorded dates (by the entry they are history, §4).

## 10. What is reported (DIRECTION_REPORT.md)

This file's sha256 at the top (AUDIT.md's format: what was run, the data, the counts, the results, the checks, the
deviations). The ledger summary; the fetch (requests, rows, bytes, hours, what the cut left out); events at each stage and why
each was not formed; the exploration screen (Δ, interval, effective N, sessions, trades per arm, each arm's mean) and, only if
it passed, the holdout test with its verdict; the descriptive rows of §5; a plain-loop verifier re-deriving at least 30 trades
from the raw files with 0 differences; anything changed after a number was read, listed as a deviation.

---

## Appendix A. The holdout's 1,600 names (H)

```
A AA AAL AAOI AB ABAT ABEO ABG ABM ABNB ABOS ABR ABSI ABUS ACCO ACEL ACGL ACH ACHC ACHR ACHV ACI ACIC ACIU ACIW ACM ACMR
ACNT ACTG ACVA ACXP ADI ADIL ADPT ADSK ADT ADTN ADV AEC AEE AEHR AEM AEO AER AEYE AFRM AFYA AGCO AGIO AGL AGM AGNC AHT
AIG AIN AIR AIRG AIRS AIT AKAM AKTS ALB ALDX ALEX ALG ALGT ALHC ALIT ALK ALKS ALLO ALLT ALNY ALRS ALTO ALV AMAL AMBR AMC
AMCI AME AMGN AMH AMP AMPH AMPL AMPY AMRC AMT AMTD AMWD AMX AN ANAB ANF ANIP ANNX ANY AOS AOSL AP APAM APD API APLE APO
APOG APPF APXT APYX AQMS AQN AQST ARCB ARCC ARE AREC ARI ARIS ARKO ARMK AROW ARQT ARR ASH ASIX ASLE ASND ASR ASUR ATAI
ATCX ATER ATEX ATHM ATI ATLC ATNI ATO ATOM ATOS ATRC AUB AUPH AUR AUTL AVB AVNS AVNW AVO AVT AVTR AVTX AVX AVY AWI AWR
AXGN AXS AXSM AXTI BAND BANR BARK BATRA BB BBAR BBCP BBDC BBIO BBUC BBVA BBW BC BCE BCSF BCTX BCYC BDTX BDX BE BEEM BEN
BEP BETR BFAM BFH BFRI BFST BHC BHE BHP BHR BHVN BIDU BIIB BILL BIOX BITF BJRI BKKT BKSY BKU BKYI BLDR BLK BLMN BLND BLX
BMEA BMI BMRN BMY BNC BNGO BNL BNS BNTC BNTX BOKF BORR BPOP BRBR BRBS BRC BRCC BRKR BRLT BROS BRX BRZE BSAC BSM BTAI
BTBT BTE BTG BTI BTX BURL BUSE BV BVN BVS BW BWB BXP BY BZ BZFD BZUN CAAP CAC CACC CAG CANF CAPR CARE CARG CARS CATY
CBAN CBL CBOE CBRE CBT CCB CCI CCL CCO CCOI CCSI CD CDNS CDRE CDW CDXS CDZI CECO CEG CELC CENN CENT CEVA CF CG CGAU CGEM
CGNT CHCO CHD CHDN CHKP CHMI CHPT CHRS CHT CI CIB CIFR CIG CIM CINF CL CLB CLBK CLDT CLF CLGN CLH CLMT CLNE CLPR CLPT
CLS CLSK CLX CM CMCSA CME CMI CMPR CMTG CNA CNC CNDT CNET CNMD CNNE CNOB CNP CNR CNTB CNXC CNXN COF COLB COLM COMP COO
COOK COR CORT COUR CPB CPK CPNG CPRX CPSH CPT CQP CR CRAI CRDO CRESY CRH CRL CRMD CRMT CRNT CRON CRS CRSP CRSR CRUS CRVS
CSGP CSR CSTL CSTM CSV CSWC CSX CTKB CTOS CTRA CTSH CTSO CTVA CTXR CUZ CVCO CVE CVEO CVLT CVNA CVRX CVS CVU CW CWCO CWH
CWST CWT CX CXW CYBR CYH CYN CYTK CZR D DAN DAO DAVA DAVE DB DBI DBRG DBVT DCI DCO DCOM DDOG DEA DECK DERM DFNS DGICA
DGII DGX DIBS DIN DINO DIOD DK DKL DKNG DKS DLR DLX DMAC DMLP DNA DNN DOC DOCU DOLE DOMO DOV DOX DPRO DRH DSP DSX DTE
DTIL DUOL DV DVN DXC DXCM DY DYAI EA EARN EAT EBC EBF EBS ED EDAP EDIT EDU EEFT EFC EFSC EGAN EGHT EGY EHC EIX EL ELAN
ELDN ELMD EMBC EMR ENB ENIC ENLV ENOV ENR ENS ENSC ENSG ENTA ENTX ENVA ENVB ENVX EOG EPAC EPAM EPD EQIX EQNR EQT EQX
ERIE ERII ERO ES ESAB ESE ESNT ETN ETON EVCM EVEX EVGN EVGO EVH EVRG EWCZ EWTX EXAS EXC EXE EXFY EXP EXR EXTR EYE EYPT
EZPW FA FAF FBNC FBRX FC FCBC FCN FCNCA FDP FDUS FDX FE FEAM FELE FFBC FFIN FFIV FFWM FHI FHN FIBK FICO FINV FIS FISV
FLD FLEX FLNC FLO FMC FMS FMX FN FNF FNKO FNV FOA FOLD FOR FORM FORR FOSL FOX FR FRBA FRHC FRO FROG FRSH FRST FRT FSLY
FSM FSS FSV FTDR FTHM FTK FTS FUL FULC G GAIN GAMB GAME GANX GATX GBDC GBTG GCMG GDDY GDRX GEL GEN GEO GEOS GETY GEVO
GFF GFI GFL GFS GGAL GGB GGG GHI GHM GIC GIL GILT GLBE GLDD GLMD GLOB GMGI GNLN GNRC GNTX GOGO GOLD GOLF GORO GP GPC GPK
GPMT GPOR GPRE GRBK GREE GRMN GROV GRPN GRWG GSK GT GTE GTLS GV GVA GWRE GWRS GXO H HAE HAL HALO HAS HASI HAYW HBNC HBT
HCA HCKT HCSG HDSN HE HEI HESM HFFG HI HIMX HITI HIW HL HLF HLI HLIT HLLY HLMN HMC HMN HMY HNRG HNST HOLX HOMB HON HPK
HPQ HQY HRB HRI HRMY HRTG HRZN HSBC HTGC HTHT HUBB HUBS HUMA HUN HURN HVT HWC HWKN HWM HYLN IAG IART IBCP IBIO IBKR IBP
IBRX ICE ICL ICUI IDN IDT IFF IFRX IHS IIIN IIIV IMAX IMCC IMNM IMO IMTX INCR INCY INDB INFY ING INGN INGR INMB INMD
INNV INO INOD INSG INSP INSW INTR INTT INTZ INVH IONQ IOSP IOT IOVA IP IPGP IQ IQV IRDM IRM IRS ISRG IT ITGR ITP ITRI
ITRN ITT ITUB IVR IVVD J JAKK JANX JAZZ JBL JBLU JBSS JD JEF JELD JKHY JLL JMIA JOE JRVR JSPR JYNT KALU KB KDP KE KELYA
KEX KEY KEYS KFRC KFY KHC KINS KLAC KMB KMI KMPR KNDI KNOP KNSA KNX KOPN KOS KR KRC KRNT KRNY KROS KT KTB KTOS KULR KURA
KYMR KZR L LAB LAC LAD LADR LAKE LAUR LAW LAZ LBRDK LBRT LBTYA LDI LE LEE LEG LEGH LEGN LESL LEU LFMD LFT LFUS LGHL LGO
LH LI LIDR LII LILA LILAK LIN LITE LITM LIVN LKFN LKQ LMB LMFA LNC LNN LOGI LOMA LOW LPLA LPSN LPX LQDA LQDT LSAK LSCC
LSTR LTBR LULU LUMN LUNG LUV LVO LVWR LW LWLG LXFR LXU LYB LYEL LYFT LYTS LYV LZ LZB MAC MAIN MANH MANU MAS MASS MATV
MATW MAX MAXN MBC MBI MBIN MBIO MBLY MBUU MCB MCFT MCHP MCO MCRI MD MDXG MEC MED MEG MELI MEOH MESO MFA MFC MFG MG MGM
MGPI MGTX MGY MIDD MIST MITT MKSI MKTX MLCO MLM MLR MLSS MMS MMYT MNR MNRO MNSO MO MOH MOV MOVE MP MPC MPWR MPX MQ MRAM
MRCY MRKR MRNA MS MSA MSCI MSI MSM MTA MTC MTCH MTG MTLS MTRN MTW MTZ MUSA MUX MVO MWA MX MXCT MYE MYPS NABL NAK NAVI
NBHC NBIX NBR NBTB NCLH NCNO NE NERV NET NEWP NEWT NFBK NFGC NG NGD NGVT NHI NI NICE NJR NKTX NMFC NMM NNI NOG NOMD NOVT
NPO NRDY NRG NRGV NRIX NRP NRT NSC NSSC NTES NTGR NTRA NTRS NTST NU NUVL NVAX NVCR NVGS NVT NVTS NWL NWPX NWS NWSA NXE
NXRT NXST NYT OCFC OCG OCGN OCSL OCUL ODC ODV OEC OFG OFIX OFS OGN OI OII OKE OKTA OLED OLLI OLMA OM OMC OMCL ON ONB ONC
ONDS ONL ONON ONTF OOMA OPEN OPTT ORC ORIC ORLA ORLY ORMP ORN OSBC OSCR OSG OSIS OSK OSPN OSS OSUR OSW OTEX OTLY OTTR
OUST OWL OWLT OXSQ PACB PACK PAGP PAR PARR PATK PAVM PAYS PBF PBH PBI PCAR PCT PCTY PCVX PDFS PDM PESI PFBC PFGC PGC
PGNY PGR PH PHG PHI PHIO PHUN PII PINE PINS PKG PKX PL PLAY PLCE PLG PLMR PLNT PLOW PLRX PLSE PLUG PLXS PNC PNR PODD
POOL POWI PPC PPG PPL PRAX PRDO PRE PRG PRGO PRIM PRM PRQR PRSO PRTA PRU PSEC PSFE PSMT PSNL PSNY PSTG PSX PTC PTON PUBM
PULM PUMP PVH PWP PWR PYPL QBTS QDEL QGEN QIPT QNST QRVO QSI QTRX QTWO QUAD RACE RAIL RBA RBBN RBOT RCAT RCEL RCKT RCMT
RCUS RDN RDNT RDWR RDY REAL REAX REE RELX RELY REPL REPX RES REXR REYN REZI RGA RGNX RGR RH RHP RICK RIGL RILY RIOT RITM
RIVN RKT RL RLAY RLX RMAX RMNI RNA RNG ROAD ROK ROKU ROL ROOT ROP ROST RPC RPD RPM RRR RRX RSI RTO RTX RUN RUSHA RVMD
RWAY RWT RXO RXST RXT RY RYAAY RYAM RYI RYN SA SABR SACH SAFE SAFT SAIA SAM SANM SATS SAVA SB SBAC SBEV SBH SBSI SBSW
SCHL SCM SCYX SD SE SEMR SES SFBS SFIX SFM SFNC SG SGHC SGHT SGI SGRY SHEL SHOO SHOP SHW SIFY SIMO SIRI SITE SJM SJT SKE
SKIN SKT SKY SKYH SKYT SKYW SLB SLDB SLDP SLGN SLNH SLP SLQT SLS SMC SMFG SMTC SNBR SNCR SNCY SNDR SNN SNT SNX SNY SO
SOC SONO SONY SOUN SPB SPCE SPG SPGI SPH SPNT SPRO SPSC SPWR SQM SR SRAD SRCE SRG SRPT SRRK SSD SSL SSNC SSSS SSTI SSTK
SSYS ST STAG STBA STC STEP STI STIM STM STN STNE STRA STRL STRO STVN STWD STXS STZ SUPN SVC SVM SVRA SWK SWKS SWX SXC
SXI SYBT SYK SYM T TAC TAL TALK TALO TAP TBBK TBLA TBPH TCBK TCPC TD TDUP TDY TE TEAM TECK TELA TEN TENX TEO TFC TFX TGB
TGLS TGNA TGS TGTX TH THO THRY THS TITN TJX TK TLRY TLSA TMC TME TMHC TMUS TNC TNDM TNET TNL TNXP TNYA TOL TOST TPB TPC
TPH TR TRAK TRC TREX TRI TRIB TRIN TRN TRNO TROW TROX TRST TRUP TRVI TRX TS TSHA TSN TTD TTE TTEC TTEK TTMI TTWO TUYA TV
TWIN TX TXRH TYRA TZOO U UAA UAMY UAN UAVS UBS UCTT UDMY UE UEC UGP UHAL UHT UI UIS ULTA UMBF UNF UNFI UNIT UNM UP UPS
UPST UPXI URI USAC USAU USB USFD USNA UTHR UTL UVSP UXIN VAL VALE VCTR VCYT VEON VERI VGZ VICI VINP VIR VIRT VIV VLRS
VLY VMI VNDA VNO VNT VOD VOR VOYA VRA VRCA VRE VREX VRRM VRSN VRT VSCO VSEC VSTM VTEX VTGN VTYX VUZI VVOS VVPR VVV VYGR
VZ W WABC WAFD WAL WASH WAT WB WBD WBS WEN WERN WES WEX WHR WING WIT WIX WKC WKEY WKSP WLDN WMG WNC WNEB WOOF WPM WPP
WRBY WRLD WSC WSO WSR WTRG WTS WTTR WU WVE WWD WWW WYNN XAIR XEL XFOR XGN XHR XNET XP XPEV XPO XPOF XRX XYL YCBD YELP
YETI YEXT YMM YOU YPF YUMC ZBRA ZEUS ZG ZIM ZION ZIP ZS ZTO ZTS ZWS
```
