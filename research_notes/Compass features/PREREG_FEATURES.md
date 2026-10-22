# Compass features, pre-registered: every feature, its one decision, the base trades, the holdout and the pass rule

Written 2026-10-22 and committed alone, before any result of this study is computed. Nothing in this file was computed
from an option's return, a P&L, a realized move, a feature-outcome relation or a GEX-versus-move relation. To write it,
these were read and nothing else:

- the frozen data scope set by the coordinator on 2026-10-22 (`features_scope.md` in the session's scratch folder;
  reproduced in section 1 so this file stands alone);
- `research_notes/Compass features/INVENTORY.md` (commit `04ce685`): spans, point-in-time status per route, blockers;
- `research_notes/Compass phase 3/picker_prereg/PREREG_PICKER.md` section 4 and `…/spxw_prereg/PREREG_SPXW.md` section 4
  (the fees);
- `research_notes/Compass phase 3/backtest_audit/audit_lib.py` (the calendar, the macro reader and the bootstrap);
- file SCHEMAS (column names and types) of the stored ThetaData Parquet (0DTE chains, expiry-day chains, option EOD,
  underlying bars) and the FIELD NAMES of the 28 Unusual Whales (UW) probe answers stored by the inventory;
- the event calendars' schema and dates (`data/macro_events_2022_2027.json`: event, date, time, status;
  `data_lake/unusualwhales/earnings.parquet`: columns and the `report_time` values);
- ThetaData's own description of its option EOD route (`openapiv3.yaml`, `/option/history/eod`).

**Disclosure.** To list the prior reads (section 10) the author opened the first lines of earlier notes in this repo. Those
lines carry their headline results, among them: the engine audit's containment of the remaining-day close by the 09:35
at-the-money straddle on SPY/QQQ/IWM/SPXW (`Compass engine audit/move_atr_flow.md` lines 13–18); the same audit's
statement that sign(GEX) gives coin-flip direction and that a GEX z-score predicts lower next-session realized vol on
UW's daily book 2025-10-15 → 2026-10-12 (`greeks_books.md` lines 24, 36, 90); and the lifecycle study's reading that long
premium lost less after negative net gamma, not significant within a root (`research/compass/lifecycle/11_conclusions.md`
at `6b166fd`, §B1). No number of this study was seen. The data these touched are therefore not virgin for the GEX check
(section 7) or the regime feature, and the reader should weigh those two accordingly.

---

## 1. Data scope (frozen 2026-10-22), why it is reduced, and what is out of scope

**Why reduced.** The full list in `INVENTORY.md` §3 is about 38 GB of UW JSON and about 224 hours of UW calls; the
container has 5.8 GB free and is ephemeral. The scope below targets under 3 GB of new data and about 15 hours of
fetching, and still covers every step of the owner's specification. The fetch stops if free disk falls under 1.5 GB.

**Universe, 15 tickers.**
- Index/ETF: SPY, QQQ, IWM (physically settled) and SPXW (cash-settled, European, PM-settled, priced off SPX). The AM-settled
  SPX root is never used.
- Single stocks, 11: AAPL, AMZN, AVGO, GOOGL, MSFT, NVDA, TSLA, AMD, INTC, MU, META (META is FB in the stored files before
  2022-06). Every one is physically settled.

**Out of scope (cost, disk), said once here and not tested:** XSP, NDXP, RUTW, DIA, the other 19 single names and the
ETF add-on of `INVENTORY.md`; UW's Options Pulse (`options-pulse`: empty at the window floor, start unpinned, not in the
fetch — the owner's "Pulse" item is therefore not tested); UW's full tape and per-print flow (B1); UW's
`flow-per-strike-intraday`, `spot-exposures/strike`, `spot-exposures/expiry-strike`, `oi-per-strike`, `interpolated-iv`
and contract minutes; ThetaData open interest (B7) and vendor greeks (B11); the owner's PC caches (B12); every UW
feature on the single names (they get ThetaData-derived features only, by the scope).

**Base-trade data (ThetaData).**

| bucket | name | source | span |
|---|---|---|---|
| 0DTE | SPY, QQQ | 1-min full chains (NBBO) on disk | 2022-11-11 → 2026-10-21 |
| 0DTE | SPXW | 1-min full chains on disk | 2022-05-13 → 2026-10-21 |
| 0DTE | IWM | 1-min full chains on disk, extended by the fetch | 2024-04-19 → 2026-10-21 |
| 0DTE | 11 singles | 1-min expiry-day full chains on disk, extended by the fetch | 2017-06-02 (META 2021-07-16; FB 2017-06-02 → 2022-06-03) → 2026-10-21, expiry days only (B10) |
| 1–7, 8–30, 31–60 DTE | SPY, QQQ, IWM | option EOD, every expiry, on disk, extended by the fetch | 2012-06-01 → 2026-10-21 |
| 1–7, 8–30, 31–60 DTE | 11 singles | option EOD fetched | 2022-11-01 → 2026-10-21 |
| 1–7, 8–30, 31–60 DTE | SPXW | option EOD **only if the fetch stores it** (the fetch agent decides from a measured request, by cost, before any result) | 2022-11-11 → 2026-10-21 if stored; otherwise SPXW is in the 0DTE bucket alone and every 1–60 DTE line says "SPXW: not on disk" |
| underlying | SPY, QQQ, IWM 1-min bars; SPX 1-min index prints; singles 1-min bars | on disk / fetched | 2017-06 → 2026-10-21 (the ETFs' stored bars before 2017 are NaN) |

**Feature data.**
- ThetaData (every name): the chains and EOD files above (quotes, EOD volume); the underlying bars; implied volatility and
  greeks are SOLVED from the NBBO mid (section 2.2), never the vendor's.
- UW (SPY, QQQ, IWM and SPX for SPXW; UW span 2023-11-21 → 2026-10-21, each route from its own served start), stored
  compact, only the fields used: `spot-exposures` per-minute series (from 2023-12-08); `greek-exposure/strike` (the
  after-close book of each session); `gex-levels` (non-null from 2024-05-13); `net-prem-ticks`; `flow-alerts`;
  `market-tide` (market-wide); `nope` (from its bisected start, ≤ 6 calls); `darkpool/{ticker}` with a premium floor IF
  the route takes one (else not fetched); `option-contracts?date=` dated chains (open interest).
- Calendars: `data/macro_events_2022_2027.json` (FOMC decisions, CPI, NFP); UW's earnings calendar in
  `data_lake/unusualwhales/earnings.parquet` (`report_date`, `report_time`); the official SPX close
  (`data/official_closes/cboe_SPX_History_2026-10-22.csv`); the ETFs' and singles' official closes from Theta's stock EOD
  (`data_lake/thetadata/stock_eod`), else UW's daily bar, else the 15:59 bar's close (labelled where used).

---

## 2. Base trades: the one set every feature is judged against

### 2.1 Conventions

- Times are New York. A 1-minute underlying bar stamped m closes at m + 1. A chain row stamped m is the NBBO at m.
- **Sessions**: full NYSE sessions. 2022 → 2026: `audit_lib.expected_sessions` (holidays and half days out). Before 2022:
  the dates present in SPY's option EOD files, minus the NYSE early closes 2012-07-03, 2012-11-23, 2012-12-24, 2013-07-03,
  2013-11-29, 2013-12-24, 2014-07-03, 2014-11-28, 2014-12-24, 2015-11-27, 2015-12-24, 2016-11-25, 2017-07-03, 2017-11-24,
  2018-07-03, 2018-11-23, 2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26; any date
  where the file list and this rule disagree is listed in the report. No base trade is entered on a half day, and none
  expires on one (such a trade is not formed; listed).
- **A quote stands** when bid > 0, ask > 0 and ask ≥ bid. **Untradable (excluded before any feature)**: no standing quote on
  the contract at entry (no bid, bid 0, crossed, ask ≤ 0), or no standing at-the-money pair to define the implied move.
- **Expiry buckets** by calendar days from the entry date to the expiry date: **0DTE** (0), **1–7**, **8–30**, **31–60**.

### 2.2 The forward, the implied move and the strike distance (one definition everywhere)

For a ticker, an entry snapshot (a chain row at minute m, or the EOD closing quote) and an expiry:
- K* = the strike at which both the call and the put stand and |C_mid − P_mid| is smallest (ties: the lower strike);
- forward **F = K* + C_mid(K*) − P_mid(K*)** (put–call parity; it carries the rate and dividends of that expiry);
- **implied move to expiry IM = C_mid(K*) + P_mid(K*)**, the at-the-money straddle mid in dollars, **unscaled** (no 0.8
  factor: the straddle itself is the unit, so 1 IM ≈ 0.8 σ of the move priced to expiry);
- **distance x** of a strike K: a call x = (K − F) / IM; a put x = (F − K) / IM (x > 0 out of the money).
- IV of a contract: Black-76 on F with discount factor 1, solved from its mid; T = (expiry at 16:00 − entry time) in
  calendar minutes ÷ 525,600. Delta from the same model. On the single names only out-of-the-money contracts' IVs are used
  where an at-the-money IV is needed (the call above F, the put below; at K* the mean of the two).

### 2.3 Entries

- **0DTE**: at 13 fixed minutes, at the ask of the chain row stamped m: **09:45, 10:15, 10:45, 11:15, 11:45, 12:15, 12:45,
  13:15, 13:45, 14:15, 14:45, 15:15, 15:30**. The owner wrote "every 30 minutes, 09:45–15:30"; a 30-minute step from 09:45
  ends at 15:15, so both named endpoints are kept and the last step is 15 minutes. The single names enter only on their
  expiry days (B10).
- **1–7, 8–30, 31–60 DTE**: once a session, at the **EOD closing quote** — ThetaData's option EOD row, whose bid and ask
  are "the last NBBO reported by OPRA at the time of report generation", the report being generated at **17:15 ET**
  (vendor documentation, `/option/history/eod`); in practice the session's last NBBO (16:00 for the single names, 16:15
  for the ETF options). The stored files keep no `created` stamp. Entry at the closing ask.
- **One expiry per multi-day bucket**: the listed expiry whose calendar DTE is nearest the bucket's centre (1–7: 4; 8–30:
  19; 31–60: 45; ties: the earlier). The 0DTE bucket's expiry is the entry date.

### 2.4 Strike buckets and the contract

Five strike buckets by x (section 2.2), the same for calls and puts:

| bucket | x range | centre |
|---|---|---|
| ITM | [−0.50, −0.15) | −0.325 |
| ATM | [−0.15, +0.15] | 0 |
| OTM1 | (+0.15, +0.50] | +0.325 |
| OTM2 | (+0.50, +1.00] | +0.75 |
| OTM3 | (+1.00, +1.50] | +1.25 |

Why: ±0.15 IM isolates the contract nearest the money; the three out-of-the-money buckets step by about half a straddle,
out to 1.5 IM, beyond which a same-day contract is a few ticks of premium; one in-the-money bucket keeps the deep side
represented without contracts that are mostly intrinsic. **Selection inside a bucket**: among the contracts of that expiry
and side with a standing quote and x in the bucket, the one whose x is nearest the bucket's centre (ties: the lower
strike). A bucket with no such contract has no trade (counted and listed).

So a base trade is one contract per (ticker, entry, expiry bucket, strike bucket, side): up to 13 × 5 × 2 = 130 a 0DTE
session per name, and 3 × 5 × 2 = 30 a multi-day session per name.

### 2.5 The fixed exit per expiry bucket (the same for every feature)

| bucket | physically settled (SPY, QQQ, IWM, singles) | cash-settled (SPXW) |
|---|---|---|
| 0DTE | sell at the bid of the 15:58 row | held to settlement: intrinsic on the official SPX close, no exit fee |
| 1–7 | held to the expiry day, sell at the bid of the 15:58 row of the expiry-day 1-min chain (SPY/QQQ/IWM: the same-day chain file; singles: the expiry-day chain file). A trade whose expiry-day chain is not on disk is not formed (listed) — in practice SPY/QQQ 1–7 trades start 2022-11-11, IWM 2024-04-19, singles 2022-11-01 | settlement at intrinsic on the official SPX close of the expiry date |
| 8–30 | sell at the EOD closing bid of the 5th session after the entry session, or of the session before the expiry day if that is earlier | the same |
| 31–60 | sell at the EOD closing bid of the 10th session after the entry session (always before the expiry day) | the same |

- Why: 0DTE and 1–7 run to the last minute a physically settled holder may stay (the owner's 15:58) or to cash settlement
  (the owner: "cash-settled index options may hold to the official close"); 8–30 and 31–60 hold a fixed number of sessions,
  about a quarter to a third of the shortest life in the bucket, so no multi-day trade meets expiry and each is priced on
  quotes the EOD files hold.
- **No bid at an exit**: the last standing bid within the 10 minutes before the exit minute (intraday), else $0 with no
  exit fee; an ETF or single contract in the money left so is listed. An EOD exit with no row for the contract at the exit
  session is not formed (a data gap, decided by file presence, listed).
- A multi-day trade whose holding period spans a split or strike adjustment of its name is not formed (listed with the
  corporate action).

### 2.6 Fees and the return

Per contract on the buy and on every sale; nothing at expiry or cash settlement; nothing on an exit at $0
(`PREREG_PICKER.md` §4, `PREREG_SPXW.md` §4, commit `2820bb4`):

| name | each way |
|---|---|
| SPY, QQQ, IWM and the 11 single names | **$0.68748** ($0.65 commission + ORF $0.01248 + OCC $0.025; the singles take the SPY figure, as the owner set) |
| SPXW | **$1.18748** when that side's price is under $1.00, **$1.27748** at $1.00 or more |

Today's schedule is applied to every year (OCC's fee was $0.02 before 2025-02-14). FINRA's TAF, the SEC's Section 31 fee
and any broker fee are not included.

**Return of a trade** r = ((exit price − entry ask) × 100 − fee in − fee out) ÷ (entry ask × 100). The dollar P&L is
reported beside it. **A session's figures**: S = Σ r and N = number of trades over every name in the comparison, by the
ENTRY session.

### 2.7 Liquidity tiers (point in time, monthly)

For each name and calendar month, on the **20 full sessions before the month's first session**, from the option EOD files:
- **spread** = the median of (ask − bid) ÷ mid at the closing quote over every contract with a standing quote, 1–60 DTE,
  |x| ≤ 0.5 (x by its own expiry's F and IM);
- **volume** = the median over the 20 sessions of the day's total option volume (every expiry and strike).

**Tier 1**: volume ≥ 900,000 and spread ≤ 5%. **Tier 3**: volume < 400,000 or spread > 10%. **Tier 2**: otherwise.
**Tier U**: the 20 sessions are not on disk (SPXW unless its EOD is stored; the singles before 2022-12). The volume cuts
are the inventory's own (its T1 ≥ 0.9 M, T2 0.4–0.9 M contracts a day, read on 2026-10-06 → 12: B9); the spread cuts are
fixed here. A trade takes its name's tier for its entry month. **Every result is reported per tier (1, 2, 3, U) and per
settlement type (physical, cash)**, beside the pooled figure that carries the verdict.

---

## 3. The features, each with its one decision

### 3.1 Rules common to every feature

- **Point in time.** A feature's value uses only what was available at the entry minute m: a UW per-minute row counts
  only if its minute ended by m (its `start_time` + 1 minute ≤ m, or its `time`/`timestamp`/`tape_time` ≤ m − 1 minute;
  a 5-minute tide row only if its timestamp + 5 minutes ≤ m); an underlying bar only if stamped ≤ m − 1; for an EOD entry
  everything through the session's 16:00. UW's end-state routes (`greek-exposure/strike`, `gex-levels`) are read for the
  **session before** the entry session, never the entry session (B2). Open interest is the count published the morning
  of the entry session. IV rank uses closes before the entry. Event dates are the published release dates (3.2, V4–V5).
- **Comparison**, for every feature and for that decision only: on the base trades the decision acts on, inside the
  feature's span and where the feature is defined, the **mean return per trade after costs with the decision applied
  minus the mean return per trade of the same base trades without it** (Σ S / Σ N of each arm, section 6). A base trade at
  an entry where the feature is undefined (data missing, a neutral value) is in neither arm.
- **One threshold per feature, no grid.** No feature is tuned. No features are combined until each passes on its own.
- **Nothing from the GeorgeFi specification**: no formula, order score, confidence, physics, helix, nerve or MOC weight.
  Walls and the flip are read off UW's answers, never recomputed.

### 3.2 The list (23 features; 22 if the dark-pool route takes no premium floor and is not fetched)

Decision forms: **veto** = drop the base trade when the condition holds (with: the kept trades; without: all);
**venue** = among the SPXW and SPY base trades with the same entry minute, expiry bucket, strike bucket and side, keep the
one the feature selects (without: both); **expiry/strike** = among the base trades at the same ticker, entry and side, keep
only the bucket the feature selects (without: every bucket at those entries); **exit** = replace the bucket's fixed exit
(2.5) by the feature's exit (without: the fixed exit); **direction** = at the same ticker, entry, expiry bucket and strike
bucket, keep the call or the put the feature points to (without: both).

#### Family 1 — Veto (6)

| id | feature | definition and threshold | applies to | source | span |
|---|---|---|---|---|---|
| V1 | spread | veto when the contract's (ask − bid) ÷ mid at the entry quote > **10%** | every name, every bucket | ThetaData chain / EOD | base spans |
| V2 | open interest | veto when the contract's open interest published the morning of the entry session < **500** | SPY, QQQ, IWM, SPXW, every bucket | UW `option-contracts?date=D` field `open_interest` only (the count published the morning of D = positions at D−1's close, `INVENTORY.md` call 18). The scope fetches the chain dated D−1 for every session D, so the chain dated D is on disk as session D+1's; nothing else in a dated chain (its IV, greeks, volume and NBBO are D's end state) is read. A contract not found by its OCC symbol is undefined | UW span |
| V3 | volume | veto when the contract's volume on the last completed session < **100**: for a 0DTE entry on D the contract's EOD volume of D−1; for an EOD entry the entry session's own EOD volume (complete at its close) | every name with option EOD files (SPY/QQQ/IWM, singles from 2022-11-01, SPXW if stored) | ThetaData option EOD `volume` | as the EOD files |
| V4 | earnings | veto when an earnings release of the name falls after the last close before the entry minute and before the expiry's 16:00 (pre-market on E counts at E's 09:30, post-market at E's 16:00; a null `report_time` counts if either reading falls inside) | the 11 singles, every bucket | UW earnings calendar (`report_date`, `report_time`) | 2017-06 → |
| V5 | macro | the same window rule for an FOMC decision (14:00), CPI (08:30) or NFP (08:30) | every name, every bucket | `data/macro_events_2022_2027.json` | 2022-01-05 → (entries before 2022 undefined) |
| V6 | IV rank | veto when IV rank ≥ **0.80**. IV30 of a session = the at-the-money IV (2.2) at the EOD closing quote, interpolated linearly in total variance between the two listed expiries around 30 calendar days; IV rank = (IV30 − min) ÷ (max − min) over the trailing 252 sessions ending at the last close before the entry (0DTE on D: D−1; EOD entry on D: D), at least 200 valid values | every name with EOD files | ThetaData option EOD | from 252 sessions after each name's first EOD file |

Point-in-time notes. V4–V5 use the realized release dates. A confirmed earnings date is public weeks ahead, but a
contract of up to 60 days can be entered before confirmation; and the October–November 2025 government shutdown moved the
CPI and NFP releases (the file has CPI 2025-10-24, NFP 2025-11-20, NFP 2025-12-16 and CPI 2025-12-18), so for entries made
before each new date was announced the realized date is not what was scheduled. Both are known departures from "as
scheduled before entry", reported as such (the trades they touch are counted).

#### Family 2 — Venue (1)

| id | feature | definition | applies to | source | span |
|---|---|---|---|---|---|
| VN1 | entry cost share | keep the venue with the lower c = ((ask − mid) + fee in ÷ 100) ÷ mid at the entry quote, the strike buckets matched by x (2.4), not by dollars; a tie keeps both | SPXW vs SPY pairs: 0DTE; and 1–60 DTE only if SPXW's EOD is stored | ThetaData chains / EOD | SPXW ∩ SPY spans (0DTE 2022-11-11 →) |

Each venue keeps its own fixed exit (SPY flat at 15:58, SPXW to settlement), as the owner's settlement rule sets; the
comparison therefore includes the settlement difference, and is reported per settlement type beside the pair figure.
"SPXW only" and "SPY only" are shown as descriptive lines, with no verdict and not counted as features.

#### Family 3 — Expiry and strike (4)

| id | feature | definition (one choice each) | applies to | source |
|---|---|---|---|---|
| ES1 | term structure → expiry | at an EOD entry, keep only the multi-day expiry bucket whose selected expiry has the lowest at-the-money IV (same ticker, side, strike bucket) | 1–7, 8–30, 31–60 | ThetaData EOD |
| ES2 | implied vs realized move → expiry | RV20 = the standard deviation of the last 20 daily log returns of the underlying's 15:59-bar close (SPX: its 15:59 print), through the entry session; RM = F × RV20 × √(sessions to expiry) × √(2/π); keep only the expiry bucket with the lowest IM ÷ RM | 1–7, 8–30, 31–60; undefined where 20 returns of bars are not on disk (ETFs before 2017) | ThetaData EOD and bars |
| ES3 | distance in IM units → strike | x_RM = RM ÷ IM (for 0DTE, RM = S × RV20 × √(minutes from m to 16:00 ÷ 390) × √(2/π)); keep only the strike bucket containing x_RM (x_RM ≤ 0.15: ATM; above 1.5: OTM3) | every bucket | ThetaData chains / EOD and bars |
| ES4 | delta → strike | keep only the strike bucket whose selected contract's \|delta\| (2.2) is nearest **0.30** (ties: the nearer the money) | every bucket | ThetaData chains / EOD |

#### Family 4 — Strike distance from move size (2; both GEX features, gated by section 7)

| id | feature | definition | applies to | source | span |
|---|---|---|---|---|---|
| SD1 | UW GEX regime | G = `gamma_per_one_percent_move_oi` of the last complete minute before entry (EOD entry: the last row through 16:00), sign as UW gives it. G > 0 → keep only the ATM bucket; G < 0 → keep only OTM2; G = 0 or missing → undefined | SPY, QQQ, IWM, SPXW (UW ticker SPX); every bucket | UW `spot-exposures` (per minute, point in time) | 2023-12-08 → |
| SD2 | distance to UW's flip | flip = `gamma_flip` of UW's `gex-levels` for the session before the entry session (B2). The underlying price at entry (0DTE: the bar stamped m − 1; SPXW: the SPX print; EOD entry: the 15:59 bar) above the flip → keep only ATM; below → keep only OTM2; null flip → undefined | as SD1 | UW `gex-levels` (end state of D−1, `source: vol`, B5) | 2024-05-13 → |

Rationale written before any read: positive UW GEX (and price above the flip) is the reading under which smaller moves are
expected, so the nearer strike; negative (or below the flip), larger moves, so the farther strike.

#### Family 5 — Exit (3; X2 is a GEX feature, gated by section 7)

| id | feature | definition | applies to | source |
|---|---|---|---|---|
| X1 | expected move as target | target level = S_entry + IM (call) or S_entry − IM (put), S_entry the underlying price at entry (0DTE: the bar stamped m − 1, SPX print for SPXW; EOD entry: the 15:59 bar). 0DTE: at the first bar stamped b ≥ m whose close reaches the level, sell at the bid of row b + 1 (if b + 1 is after 15:58, the fixed exit). Multi-day: at the first session after entry, up to the fixed-exit session (1–7: up to the session before expiry), whose 15:59 close reaches it, sell at that session's EOD closing bid; else the fixed exit | every bucket; undefined where bars are not on disk | ThetaData chains / EOD, bars |
| X2 | UW's walls as targets | the call wall = the strike with the largest `call_gex`, the put wall = the strike with the most negative `put_gex` (signs as UW gives them), in UW's `greek-exposure/strike` book of the session before the entry session (B2). A call takes the call wall as its level if it is above S_entry, a put the put wall if below; otherwise the fixed exit stands (the trade is in the "defined" set only when the wall is on the trade's side). Exit mechanics as X1 | SPY, QQQ, IWM, SPXW (UW SPX); every bucket | UW `greek-exposure/strike` (end state of D−1), ThetaData chains / EOD, bars |
| X3 | time-of-day decay | a 0DTE trade entered before 14:00 is sold at the bid of the 14:00 row instead of the fixed exit (SPXW too, with its exit fee) | 0DTE entries 09:45–13:45 | ThetaData chains |

#### Family 6 — Direction (7)

Each points to the call (value > 0) or the put (value < 0); a value of exactly 0, or no data, is undefined.

| id | feature | definition | applies to | source | span |
|---|---|---|---|---|---|
| D1 | net premium | Σ (`net_call_premium` − `net_put_premium`) over the session's ticks from 09:30 to the last complete minute before entry | SPY, QQQ, IWM, SPXW (UW SPX); every bucket | UW `net-prem-ticks` | UW span |
| D2 | flow and sweeps | over the ticker's alerts with `has_sweep` true and `created_at` in [09:30, m): Σ calls (`total_ask_side_prem` − `total_bid_side_prem`) − Σ puts (the same) | as D1 | UW `flow-alerts` (the only sweep history on the trial token, B1) | UW span |
| D3 | NOPE | `nope` of the last complete minute before entry | as D1 | UW `nope` | from its served start (bisected, B3) |
| D4 | market tide | `net_call_premium` − `net_put_premium` of the last complete 5-minute tide row before entry, as UW serves it | SPY, QQQ, IWM, SPXW (by the scope; the singles take no UW feature) | UW `market-tide` | UW span |
| D5 | dark pool | over the ticker's dark prints with `executed_at` in [09:30, m) and premium ≥ the fetch's floor: Σ premium × sign(price − (`nbbo_bid` + `nbbo_ask`) ÷ 2) | SPY, QQQ, IWM (UW serves no index: SPXW undefined) | UW `darkpool/{ticker}` | UW span; **only if fetched** (else "not tested, no data", and the count is 22) |
| D6 | opening range | ORH/ORL = the high/low of the bars stamped 09:30–09:59 (SPXW: SPX prints); at entry the close of the bar stamped m − 1 above ORH → call, below ORL → put, inside → undefined | 0DTE entries from 10:15, every name | ThetaData bars / SPX prints | bars' spans |
| D7 | prior-day structure | the prior session's regular high/low (bars 09:30–15:59); the price at entry (0DTE: bar m − 1; EOD entry: the 15:59 close) above the prior high → call, below the prior low → put, inside → undefined | every name, every bucket | ThetaData bars / SPX prints | bars' spans |

### 3.3 The count

| family | features | of which GEX (gated by section 7) |
|---|---|---|
| veto | 6 (V1–V6) | 0 |
| venue | 1 (VN1) | 0 |
| expiry and strike | 4 (ES1–ES4) | 0 |
| strike distance from move size | 2 (SD1, SD2) | 2 |
| exit | 3 (X1–X3) | 1 (X2) |
| direction | 7 (D1–D7) | 0 |
| **screened** | **23** (22 if the dark pool is not fetched) | **3** |

If the GEX check fails, SD1, SD2 and X2 are dropped untested and reported as such; they still count as screened in the
false-pass arithmetic of section 6 (the conservative count).

---

## 4. How each blocker that touches a feature is handled

| # | blocker | handling here |
|---|---|---|
| B1 | trial token: no full tape past 30 days | flow and sweeps only through `flow-alerts` (D2); no per-print or per-contract-minute flow |
| B2 | no past-minute GEX book, walls or flip | the walls (X2) and the flip (SD2) are the PRIOR session's after-close answers; the only intraday GEX is the whole-book per-minute series (SD1, section 7), which is point in time; nothing is modelled or recomputed |
| B3 | unpinned starts | NOPE from its bisected start (D3); Pulse, `flow-per-strike-intraday`, `oi-per-strike` and `spot-exposures/strike` are not used |
| B4 | UW's rolling window | the UW span is what the fetch holds (floor 2023-11-21 at the time of the inventory); each feature's span is stated by its route's first served date on disk |
| B5 | `gex-levels` volume-sourced, null before 2024-05-13 | SD2 starts at each name's first non-null flip (2024-05-13 for SPY/SPX; QQQ and IWM likewise); the walls (X2) come from the OI-sourced per-strike book instead |
| B6 | NDX refused before 2026-05 | NDXP is out of scope |
| B7 | ThetaData OI throttled | open interest only from UW's dated chain, index names only (V2); the singles have no OI veto |
| B8 | no rate history before 2024 | not needed: Black-76 on the parity forward (2.2) |
| B9 | universe and tier cuts read on five 2026 sessions | the 15 names are a 2026 choice (recency and survivorship stated); tiers are measured point in time each month (2.7) |
| B10 | single-name 0DTE only on expiry days | the singles' 0DTE base trades exist only on their expiry days |
| B11 | vendor greeks start 2016–17 | not used; IV and greeks solved from the NBBO |
| B12 | the owner's PC caches | not used |
| B13 | UW quota shared with the recorder | a fetch schedule matter (one call in flight 09:00–17:00 New York on weekdays); no feature effect |

---

## 5. Holdout (drawn now, before anything is computed)

**Drawn with `numpy` 2.5.3, `default_rng`, by exactly this code:**

```python
import numpy as np
TICKERS = ['SPY', 'QQQ', 'IWM', 'SPXW', 'AAPL', 'AMZN', 'AVGO', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'INTC', 'MU', 'META']
MONTHS = [f'{y}-{m:02d}' for y in range(2012, 2027) for m in range(1, 13) if '2012-06' <= f'{y}-{m:02d}' <= '2026-10']
held_t = sorted(np.random.default_rng(20261022).choice(TICKERS, size=3, replace=False).tolist())   # 20% of 15
k = int(np.floor(0.25 * len(MONTHS) + 0.5))                                                       # 25% of 173 → 43
held_m = sorted(np.random.default_rng(20261023).choice(MONTHS, size=k, replace=False).tolist())
```

**Held-out tickers (3 of 15): AVGO, MU, QQQ.**

**Held-out months (43 of the 173 calendar months 2012-06 → 2026-10)**: 2012-11, 2013-05, 2014-06, 2014-09, 2015-01,
2015-03, 2015-06, 2015-07, 2015-09, 2015-10, 2015-11, 2016-01, 2016-04, 2016-08, 2017-02, 2017-06, 2018-05, 2018-12,
2019-01, 2019-06, 2019-08, 2020-01, 2021-09, 2021-10, 2021-12, 2022-03, 2022-09, 2022-10, 2023-02, 2023-03, 2023-06,
2023-09, 2023-10, 2024-01, 2024-06, 2024-11, 2025-01, 2025-06, 2025-10, 2025-11, 2026-04, 2026-06, 2026-10.

Held-out months inside each span: singles' 0DTE (2017-06 →) 28 of 113; SPXW 0DTE (2022-05 →) 17 of 54; the base span and
the singles' EOD (2022-11 →) 15 of 48; the UW span (2023-11 →) 10 of 36; `spot-exposures` (2023-12 →) 10 of 35; IWM 0DTE
(2024-04 →) 9 of 31; `gex-levels` non-null (2024-05 →) 9 of 30. **UW-based features use the same split within each
route's span** (the same tickers, the same months).

**Rules.**
- A base trade belongs to the **holdout** if its ticker is held out, or if any session from its entry to its exit falls in
  a held-out month; otherwise to the **exploration** set.
- **The held-out tickers are never opened** before the final test: no file of AVGO, MU or QQQ (ThetaData or UW) is read,
  for inputs or outcomes, and no tier of theirs is measured.
- **Held-out months are never read for an outcome** before the final test: no exit price, return, P&L, realized move or
  GEX-versus-move figure in a held-out month. A trailing-window INPUT of an exploration trade (the 20-session tier window,
  RV20, the 252-session IV rank, the prior day) may read quotes and bars that fall in a held-out month, because these
  windows cannot otherwise be formed; no such read is ever paired with an outcome.
- **Venue (SPXW vs SPY)**: a pair is in the holdout if either venue's ticker is held out or a held-out month is touched;
  had SPY or SPXW been drawn, every pair would be holdout and VN1 would have no exploration screen (it would not be sent to
  the holdout). Neither was drawn, so VN1 screens on the exploration months and is tested on the held-out months.
- The GEX check (section 7) runs on the exploration set only: SPY, IWM and SPX (QQQ is held out).
- 2026-10 is a held-out month, so the forward sessions 2026-10-12 → 21 are holdout for every name.

---

## 6. Test order, statistics, and the pass rule

**Order.** (1) veto, (2) venue, (3) expiry and strike, (4) the GEX check (section 7), then strike distance from move size,
(5) exit, (6) direction. The order fixes the sequence of work and reporting only: every feature is judged alone against
the same base set; no passed feature is applied before another is judged; nothing is combined.

**Statistic.** For a feature and an arm, per exploration (or holdout) session s in calendar order: S_s = Σ r and N_s =
number of trades of that arm entered in s, all tickers together. The arm's mean return per trade is Σ S ÷ Σ N. The
difference Δ = mean(with) − mean(without).

**Interval.** The moving-block bootstrap over dates, **20-session blocks**, all tickers resampled together (a session's
whole row, every name and bucket), 2,000 draws: `audit_lib.block_draws(n, 20)` (seed 20261022 + 7919 × 20 as in that
function) and `audit_lib.weights_from`; for each draw W, Δ_b = (W·S_with) ÷ (W·N_with) − (W·S_without) ÷ (W·N_without),
the SAME W for both arms; the 95% interval is `audit_lib.pct_ci` (2.5th and 97.5th percentiles). The sessions are the
set's sessions in date order, concatenated across the holes the held-out months leave. No interval under 60 sessions
(`session_stats` returns none under 3 × 20): such a feature does not pass. Each arm is also reported through
`audit_lib.session_stats(S, N)` (sessions, sessions traded, trades, mean per trade, block 1/5/20 intervals).

**Effective N.** As `session_stats`' `n_eff_block20`: n × var(Δ under block 1) ÷ var(Δ under block 20), computed for Δ
with the same draws; and `n_eff_acf` of the per-session difference series S_with − (N_with ÷ N_without) × S_without
(sessions with N_without > 0). Both are reported with the raw session and trade counts.

**Exploration screen (what sends a feature to the holdout).** On the exploration set: Δ > 0 **and** the block-20 95%
interval's lower end > 0.

**Holdout test (once).** A feature that passed the screen is run once on the holdout set, unchanged. **Pass: the holdout
Δ > 0 with its block-20 95% interval clear of zero (lower end > 0).** Verdicts come from the holdout only. The holdout's
two parts (the held-out tickers over all months; the exploration tickers over the held-out months) are shown as
descriptive rows, no verdict of their own.

**Multiple testing.** No correction is applied unless the owner asks. Under the null (Δ = 0 for every feature, the
intervals correctly sized) a one-sided pass of a 95% two-sided interval has probability 0.025: expected false passes
at the exploration screen 23 × 0.025 = **0.58** (22: 0.55); read as a two-sided 5% test, 1.15 (1.10). A false final pass
needs both stages: 23 × 0.025² ≈ **0.014** if the two sets were independent (they share the trades' market, so somewhat
more). The count screened and the count passed are reported.

---

## 7. The GEX check (step 6): before any GEX feature is tested

- **Sessions**: exploration sessions in the `spot-exposures` span (2023-12-08 → 2026-10-21, minus held-out months);
  names SPY, IWM (0DTE from 2024-04-19), SPX (QQQ is held out). A name-session counts when it has a 09:45 GEX row, a 09:45
  0DTE implied move and an official close.
- **GEX at 09:45**: `gamma_per_one_percent_move_oi` of the UW `spot-exposures` row of the last complete minute before
  09:45 (the row whose minute ended by 09:45:00), **sign as UW gives it**. Positive vs negative; exactly 0 left out.
- **Realized move** = |official close − P| ÷ IM, P the price at 09:45 (ETF: the close of the bar stamped 09:44; SPX: its
  09:45 print), IM the implied move to the close at 09:45: the 0DTE at-the-money straddle mid of the chain row stamped
  09:45 (section 2.2; SPX: the SPXW same-day chain). Official close: the SPX Cboe file; the ETFs' Theta stock EOD close,
  else UW's daily bar.
- **Statistic**: Δ_GEX = mean realized move on negative-GEX name-sessions − mean on positive-GEX name-sessions (pooled over
  names), its block-20 bootstrap interval as section 6 (A_s, B_s the per-session sums of the two groups, the same W).
  Reported pooled, per name, and per tier (2.7), with effective N.
- **Gate**: if the pooled Δ_GEX > 0 and its interval's lower end > 0, the GEX features (SD1, SD2, X2) are tested;
  **otherwise every GEX feature, walls and flip included, is dropped untested.** The per-tier and per-name rows do not
  change the gate. The check is computed on the exploration set only and never on the holdout.

---

## 8. What is reported (FEATURES_REPORT.md)

The prereg's hash at the top. The base set described per bucket, tier and settlement type (trades formed, trades not
formed and why — no standing quote, no ATM pair, no expiry-day chain, an exit row missing, a split — and the base mean per
trade with its interval, descriptive, no verdict). The GEX check (section 7). Then for each feature, in the order of
section 6: **decision, source, span (first and last session, sessions, trades in each arm), exploration Δ with its
block-20 interval and effective N, holdout Δ with its interval and effective N (or "not sent", "dropped by the GEX check",
"not tested — no data"), PASS or FAIL**, with the per-tier and per-settlement rows beside it (descriptive). At the end:
how many features were screened, how many passed the screen, how many passed the holdout. The known departures (the
0DTE grid's 15:30, the realized event dates, the OI date convention, SPXW 1–60 and the dark pool by what the fetch
stored, NOPE's start) are listed. Anything changed after a number is read is listed as a deviation.

---

## 9. What this file does not decide, and why

Nothing here is left to choose after a result. Three things depend on what the fetch stores, each decided by data cost
before any result, and each with its consequence fixed above: SPXW's option EOD (1–60 DTE SPXW trades, V3/V6 on SPXW and
the 1–60 VN1 pairs exist only if it is stored); the dark-pool route's premium floor (D5 exists only if fetched); and
NOPE's first served date (D3's span). The scope note asks for the UW dated chain "date = D−1 for OI as published that
morning"; the chain dated D−1 carries the count published the morning of D−1, one session older than the owner's "as
published that morning", so V2 reads the `open_interest` field of the chain dated D (fetched as session D+1's D−1) and
nothing else from it; the last session of the span, whose dated chain is not fetched, has V2 undefined.

---

## 10. Prior reads: which spans are not virgin

| study | what it read |
|---|---|
| Step 1–5 (`step1/` … `step5/`, commits `2185eb9` → `491a0c7`) | every same-day contract's minute quotes on SPY, QQQ, IWM, SPXW, 2022-05-13 → 2026-10-09 (3,687 sessions): distance, time of day, price, weekday, exits, turn-up entries, per-contract volume; step 5 scored a model once on 2025–2026 |
| Lifecycle research (`research/compass/lifecycle/`, removed from HEAD; protocol at `889691a`, conclusions at `6b166fd`) | 0DTE SPY/QQQ/SPXW/IWM 2022 → 2026-10-09 (development ≤ 2024, validation 2025-01 → 09, hold-out 2025-10-01 → 2026-10-09); a daily tier on SPY/QQQ/IWM from 2012-06 and 40 single names from 2017-06; UW daily dealer-gamma sign 2025-10-15 → 2026-10-13 as a regime filter on long premium |
| Engine audit (`research_notes/Compass engine audit/`) | 0DTE chains and bars SPY/QQQ/IWM/SPXW 2022–2026 (fit 2022–24, read 2025–26; context 2012/2017–2021): the sweep trigger, the opening range, expected-move containment by the straddle, ATR, flow; greeks and UW's daily books and flip/walls (2025-10-15 → 2026-10-12, the GEX-vs-volatility regime claim); the multi-day engine on SPY/QQQ/IWM daily bars 2012 → 2026-10-09 and twenty names 2020 → 2026-10-13 |
| Phase 2, hypotheses A–D | SPXW/SPY/QQQ/IWM 0DTE credit spreads, condors, debit verticals, butterflies, straddles 2022 → 2026-10-09 (fit 2022–24, read 2025–26), late-day and midday |
| Phase 3, E and F; the backtest audit; after-hours | SPY short 0DTE premium 10:00–15:30; the 15:30 SPY/QQQ butterflies; the paper tracker's replay 2022-11-11 → 2026-10-09; after-hours 2025-10-13 → 2026-10-21 |
| SPXW prereg (`2820bb4`) and its test (`6bb230e`) | SPXW 0DTE iron fly and condor analogues 2022 → 2026 |
| Picker prereg (`c502122`) and test (`1e10053`) | SPY/QQQ/IWM/SPXW 0DTE long calls and puts on the opening-range fade, 2022 → 2026-10-21, incl. the never-read 2026-10-14 → 21 |
| The forward tracker (`forward_cumulative.md`) | SPY/QQQ 0DTE 2026-10-12 → 21 |

So: the index names' 0DTE quotes 2022 → 2026-10-09 have been read many times (long calls and puts by distance and time of
day among them — close to this study's 0DTE base set); UW's daily book after 2025-10-15 has been read against volatility
and long premium; the multi-day ETF data from 2012 were read at daily resolution. The single names' expiry-day minute
chains, their option EOD, and UW's per-minute GEX, net premium, flow alerts, NOPE, tide and dark pool before 2025-06 have
not been read against an outcome in this repo. The random month holdout (section 5) is the protection this study has; it
cannot undo what earlier studies saw.
