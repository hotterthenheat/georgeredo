# PREREG — Compass Final: one clean test, at Robinhood's fees, of every rule the final report left standing

Committed ALONE with `../HOLDOUT_LEDGER.md` (its new row) and the stage-1 files beside this one, BEFORE any fetch for this
test and before any return, P&L or ratio of this test is computed. The owner attached the final research report and said
"reverse engineer until you figure out a final that works". The instruction is carried out as written: the surviving
candidates are picked from the report by a rule fixed here, then each gets ONE test on data that no study has read for its
rule, at the owner's Robinhood fees, with nothing tuned. A negative result is a valid outcome.

Stage-1 files committed with this prereg (no outcome read by any of them):
- `probe_entitlement.py`, `out/probe_entitlement.json`, `out/probe_entitlement_2.json`: what Theta serves (section 2.1).
- `stage1_sessions.py`, `sessions_<family>.csv` (six files), `out/stage1_summary.json`: the fresh sessions and the
  exclusions (section 2.2).
- `mde_prereg.py`, `out/sd_previous.json`, `out/mde_prereg.json`: planned trade counts, MDEs and forward Ns (sections 7
  and 9), from SDs measured on previously read periods only.

## 1. Stage 1: the candidates, picked by a fixed rule

### 1.1 The rule (fixed before any row was looked at for this purpose)

A row of the final report's page 1 (`research_notes/FINAL REPORT/FINAL_RESEARCH_REPORT.md`, Robinhood-fee primary since
`00116d0`) is a candidate when ALL of:

1. its mean trade at Robinhood fees is > 0;
2. the lower end of its 20-session block interval (the page-1 column "20-session block 95% (mean %, Robinhood)") is > 0,
   on the period the row reports (the study's own out-of-sample / check / selection period);
3. it has ≥ 300 trades;
4. it is not vendor-recorded (§), not a PREVIEW and not a descriptive "base trades" row.

Rows that are the same family on the same instrument are grouped. A family is tested on its pre-registered or tracked
cell, never on its best cell.

### 1.2 The rows that pass

| page-1 row | strategy | period | trades | mean at Robinhood fees | block-20 lower end |
|---|---|---|---|---|---|
| 6e | H15: 14:05 SPXW short strangle ±0.5 EM, held to settlement | TEST | 407 | +17.98 % credit | +3.49 |
| 6d | T-E (H13): 13:00 SPXW ATM straddle to settlement, ex FOMC/CPI/NFP | TEST | 388 | +8.74 % credit | +1.85 |
| 21a | hyp C: 15:00 SPY/QQQ iron ±2 fly | OOS 2025–26 | 878 | +7.46 % risk | +0.15 |
| 26c | tracker condor_d20 | ii | 2,090 | +6.11 % risk | +3.87 |
| 20b | hyp B: midday SPY em1 condor, mid-VIX | OOS 2025–26 | 1,202 | +4.67 % risk | +1.62 |
| 20a | hyp B: SPY 2-wide 25-delta credit spread at the boundary touch | OOS 2025–26 | 2,600 | +4.59 % risk | +2.24 |
| 25 | hyp F: 15:30 SPY/QQQ call ±5 fly | OOS 2025–26 | 879 | +4.50 % risk | +2.14 |
| 26b | tracker fly5 (iron, call, put ±5, 15:00 and 15:30) | ii | 5,271 | +4.29 % risk | +2.45 |
| 26a | tracker condor_em1 | ii | 2,068 | +3.90 % risk | +0.90 |
| 21c | hyp C: 15:00 SPY/QQQ call ±5 fly | OOS 2025–26 | 878 | +2.84 % risk | +0.10 |
| 7j-atm_put | S17: monthly ATM cash-secured put, SPY+QQQ | 2012-06→2026-10 | 334 | +0.66 % capital | +0.17 |
| 7j-put_30d | S17: monthly 0.30-delta cash-secured put | 2012-06→2026-10 | 334 | +0.46 % capital | +0.03 |
| 32 (QQQ) | Compass H1: overnight reversal of the late-day move, QQQ | single test | 3,299 | +0.038 % notional | +0.005 |

### 1.3 Rows that fail the rule (named because the owner expected some of them)

- **Edge H7, pre-FOMC drift** (37a): positive, interval clear of zero, but **108 (QQQ) and 77 (SPY) trades < 300**. Not a
  candidate. It is already in the daily forward job (forward N 366 SPY / 483 QQQ, `fcc1f4d`).
- **Edge H8, QQQ turn of the month** (37b QQQ): **172 trades < 300**. Not a candidate. (SPY's lower end is < 0.)
- **S17 0.15-delta put** (7j-put_15d): lower end −0.09. Not a candidate.
- Excluded by condition 4: #1 (vendor-recorded), #41a and #41b (PREVIEW), #30a (base trades; its mean is negative too).
- Every other row has a mean ≤ 0 or a lower end ≤ 0 (page 1). In particular #27a and #27b (the after-hours study's
  case (b)) and #28a/#28b (the SPXW analogues) fail condition 2. They are not candidates, and #27's method is used below as
  the settlement of the SPY/QQQ families.

### 1.4 The families and the cell each is tested on

| test | family (rows) | the cell tested, and why that cell | frozen as committed |
|---|---|---|---|
| **T1 fly5_iron** | SPY/QQQ late ATM butterflies (21a, 21c, 25, 26b) | the iron butterfly ±5 at 15:00 and 15:30, SPY and QQQ pooled: the cell hyp C §6 wrote as the confirmation test ("Structure: iron butterfly, SPY and QQQ … wings ±5, entered at 15:30 (and 15:00 as the second cell)"), the tracker logs as fly5's iron, and the after-hours study judged. The tracker's call and put flies (the same strikes) are reported, not judged. | hyp C `preregistration.md` / §6 at `faea67c`; tracker `scripts/paper_tracker.py` RULES_VERSION `rules-2026-10-21.1` (`a4ebe90`), run as at `6826b98` |
| **T2 condor_em1** | SPY midday iron condors (20b, 26a, 26c) | the tracker's condor_em1 (all VIX, 11:30–13:30): the family's tracked cell; hyp B's own rule text drops the mid-VIX condition ("added nothing OOS and is dropped from the descriptive rule") | hyp B "The rule, conditional on X" (`2c241f4`); tracker `rules-2026-10-21.1` (`a4ebe90`) |
| **T3 condor_d20** | same family | the tracker's condor_d20 (13:00–15:00, every session, the vol model's decile a column, never a filter): the family's second tracked cell. Both tracked cells are tested and each counts in k. | hyp E §8 "needs X (1)" (`02d0dcd`); tracker C3 `rules-c3-2026-10-21.1` (`99a3d4e`) |
| **T4 touch_d25** | SPY boundary-touch credit spread (20a) | hyp B's pre-registered touch pick: SPY, 2-wide, 25-delta short strike, hold, no filter, mult 1.0, one row a touch minute | hyp B `out/prereg.txt` and `engine.py`/`analyze.py` (`2c241f4`); events by the engine audit's `move_atr_flow/engine.py` |
| **T5 h13_te** | SPXW 13:00 straddle (6d) | T-E's rule = grid cell `N0.0\|13:00\|tp0\|st0\|E2\|F4` | `research/thetadata/hwr_grid/spxw/PREREGISTRATION.md` (sha256 in `prereg_sha256.txt`) and `spxw_v2/sim.py` (protocol sha256 in `protocol_sha256.txt`), at `7dfea57` |
| **T6 h15_s2** | SPXW 14:05 strangle (6e) | the round-2 S2 definition `N0.5\|14:05\|tp0\|st0\|E2\|F3` — the H15 carry lane named for forward test T-G and the page-1 row. (The S2 re-selected on complete TRAIN data, `N1.0\|14:05\|tp0\|st2\|E2\|F3`, is not tested: it is a different cell, and it failed its own TEST.) | same, at `7dfea57` |
| **T7 h1_qqq** | Compass H1, QQQ (32 QQQ) | the pre-registered H1 rule on QQQ | `research_notes/Compass H1/PREREG_H1.md` (`38aca66`), `run_h1.py` (`4a02144`) |
| forward only | S17 index put-writing (7j-atm_put, 7j-put_30d) | the ATM put, SPY and QQQ: the hypothesis's own instrument ("Index put-writing earns the variance risk premium (Cboe PUT)"; the Cboe PUT index writes the ATM put); the 0.30-delta put logged beside it, not judged | S17 `research/compass/studies/s17_put_write.py`, A7 `c81522a`, results `5e7e1bd`, at `7dfea57` |

H13 and H15 are two families, not one: each was pre-registered on its own (T-E as a single test, H15 as the grid's lane),
with different strikes, times and filters. Both count in k.

### 1.5 The frozen rules, verbatim

**T1, fly5 (tracker docstring, `rules-2026-10-21.1`):** "SPY and QQQ, same-day expiry, at 15:00 and 15:30 New York. K0 = the
strike nearest spot with a call and a put quoted (a tie: the lower strike); wings ±5. Three structures a capture: the iron
butterfly (sell the K0 call and put at the bid, buy the K0−5 put and the K0+5 call at the ask; max risk 5 − credit), the
long call fly (buy K0−5 and K0+5 calls at the ask, sell two K0 calls at the bid; max risk = the debit) and the long put
fly. A structure's max risk must be >= $0.05 and its short legs' bids > 0." Spot at a minute m is the close of the bar
stamped m − 1 (the replay's adapter, the research's convention).

**T2, condor_em1 (tracker docstring):** "SPY, same-day expiry, at 11:30, 12:00, 12:30, 13:00 and 13:30 New York, every VIX.
The ATM straddle M = call mid + put mid at the strike nearest spot with both sides quoted (a tie: the lower strike); short
call = the first listed strike >= spot + M; short put = the first listed strike <= spot − M; wings 2 points (long call =
short call + 2, long put = short put − 2). NBBO fill: the shorts at their bid, the longs at their ask; each spread's credit
must be >= $0.05 (the condor's >= $0.10) or the row is logged `tradable=false`."

**T3, condor_d20 (tracker docstring, C3):** "SPY, same-day expiry, at 13:00, 13:30, 14:00, 14:30 and 15:00 New York, every
session, held to the close: the 2-wide iron condor whose short call and short put are the OTM strikes whose Black-Scholes
|delta| is nearest 0.20 — Hypothesis B's `nearest_delta` exactly (engine.py): r = q = 0, the vol implied by each option's
own mid … a tie in |delta − 0.20| goes to the FARTHER out-of-the-money strike …; longs 2 points beyond; fills and the
tradable rule as condor_em1."

**T4, the touch pick (hyp B `out/prereg.txt`, `engine.py`, `analyze.py`):** "TOUCH PICK: {'product': 'SPY', 'width': 2.0,
'rule': 'd25', 'filter': 'all', 'management': 'hold'}", mult 1.0. Events: "at each of the 14 scan minutes (09:35, 10:00,
10:30 … 15:30, 15:50) the spot and the ATM straddle mid (M = straddle); the touch is the FIRST minute t > scan at which the
spot reaches spot_scan ± M (mult 1.0)"; "an up touch sells a call credit spread (short K, long K + width), a down touch a
put spread"; "`d25` = the OTM strike whose Black-Scholes |delta| is nearest … 0.25, r = q = 0, the vol implied by the
option's own mid at the entry minute"; "a short leg sold at its bid, a long leg bought at its ask, at the entry minute's
NBBO; credit ≥ $0.05 a spread or no trade"; "Tradable touches are those at or before 15:58 (minute 388)"; "pooled cells
are ONE ROW A TOUCH MINUTE (session, side, t, rule, width)" (`analyze.py`: `unique(subset=['session', 'touch_side', 'e',
'mult', 'rule', 'width'], keep='first')` after sorting by m_scan).

**T5, T-E (spxw PREREGISTRATION.md T-E.3 and `sim.py`):** "13:00 ATM straddle, sell bid, hold to settlement at the official
Cboe SPX close, $2 fees, ex FOMC/CPI/NFP". Spot = the SPX print stamped 13:00; ATM = `round(spot / 5) * 5` when both sides
are quoted there, else the quoted strike nearest spot (a tie the lower); skip on no spot, no quote or a zero bid; credit =
the two bids; P&L = (credit − intrinsic at the Cboe close) × 100 − fees.

**T6, H15 round-2 S2 (`sim.py`, `analyze.py` FNAME):** `N0.5|14:05|tp0|st0|E2|F3`: at 14:05, EM = the ATM straddle mid (as
T5's ATM); short call = the smallest listed strike ≥ spot + 0.5·EM, short put = the largest ≤ spot − 0.5·EM; both sold at
the bid; no take-profit, no stop, held to settlement at the Cboe close; F3 = "skip FOMC + month-end" (month-end = the last
session of the month on the full NYSE calendar, early closes counted as sessions).

**T7, H1 (PREREG_H1.md, as the final report states it):** "Short 100 shares at the official close if the close > the 15:00
price, long if below; exit at the next 09:30 open", with PREREG_H1.md's dividend, borrow (0.30 % a year on a short, Actual/360)
and tie rules, `run_h1.py` unchanged in every constant but the span.

**S17 (`results/v1/s17_put_write/REPORT.md`):** "Sell the next standard monthly at the closing bid on the roll date, hold to
its last trading day, settle at intrinsic (underlying from put-call parity at the expiration-day close); … no interest
credited on collateral"; the ATM put (and the 0.30-delta put, logged).

## 2. Data that no study has read for these rules

### 2.1 What Theta serves (stage-1 probes, 2026-10-23 21:20–21:22 New York, one SDK login each, every probe on a Tuesday or Thursday with no SPY, QQQ or SPXW expiry)

| input | served from | evidence |
|---|---|---|
| SPY 1-minute bars (regular and after hours), SPY EOD | **2017-01-03** | 2012-06-05 and 2014-03-04: rows but no price on either venue; EOD "No data" 2014-03 and 2016-12-20; 2017-01-05 bars to 17:31 and EOD present. The stored SPY files hold prices from 2017-01-03. (H1's stage 1 found the same.) |
| QQQ 1-minute bars (regular and after hours), QQQ EOD | **2012-06-01** (the stored files' start) | 2014-03-04: 427 bars with a close to 17:31, 36 of them after 16:00; EOD present |
| SPX 1-minute index prints | **2017-01** | 2017-01-05 and 2017-05-16 present; 2012-06-05, 2014-03-04, 2016-12-20 "No data" |
| SPY, QQQ, SPXW option NBBO | 2012-06 (as far as the probes went) | 2012-06-05 and 2014-03-04 quotes present |

So **after-hours SPY and QQQ prices for the fresh span CAN be fetched**, and the AFTERHOURS.md method is the primary
settlement of the physically settled families (section 4). Every rule here takes its spot from bars (SPY/QQQ) or SPX prints
(SPXW), so the fresh span starts where those are served: SPY and SPXW **2017-01-03**, QQQ **2012-06-01**.

### 2.2 The fresh sessions (stage1_sessions.py; the counts are `out/stage1_summary.json`)

- **End: 2022-05-12.** From 2022-05-13 SPXW same-day chains were read intraday on every session (steps 1–5, Tier I, H11,
  H13, H15, S09, Compass ICT, the picker …); under the read rule below (union across index products) every later session
  is excluded for every family. SPY's and QQQ's own same-day chains were first stored from 2022-11-11.
- **Same-day expiry:** an expiration on Theta's lists (`research/thetadata/dataset/expirations/expirations_<ROOT>.csv` at
  `7dfea57`, re-checked at fetch time) dated on the session. Before 2015-02 the standard monthlies were dated on the
  Saturday after the third Friday; the frozen rules ask for the chain whose expiration is the session, so those third
  Fridays carry no same-day expiry here and are not in the test (QQQ only: SPY's span starts 2017).
- **Sessions and half days:** QQQ's stored 1-minute files with ≥ 30 closes are the sessions; a half day's last close is
  stamped before 15:00. Every half day is out (the frozen rules skip them). From 2017 the bar rule and the dataset calendar
  agree exactly (11 half days, no holiday with a file).
- **Excluded as already read** (Compass Close step 0's precedent, union across SPY, QQQ, IWM, SPX and SPXW): a session on
  which an earlier study held an index-product option position, or read an index-product option P&L, at any minute of the
  family's window [first entry minute, 16:00]: **V8** [13:00, 16:00]; **S03** filled trades [entry, exit]; **S16b** filled
  trades [09:31, + hold_min]; **Compass Close's gate sample** [15:45, 16:00] (its plain-loop and lookahead checks drew only
  from it — asserted).
- **Not counted as reads** (Compass Close's decision 1, kept): end-of-day closing marks — the Lifecycle daily tier, the
  Compass features' ETF base trades before 2022-11 (entered and exited at minute 390, none same-day) and S17's monthly
  cycles. **Every fresh session carries such a mark** (the column `eod_marks`), so the sensitivity line "EOD-marked sessions
  out" has n = 0 and is printed as such.
- **Compass Close's P&L sample** (its even months: SPXW 15:45–16:00 quotes fetched, never read for an outcome) is NOT
  excluded; a sensitivity line drops it (`compass_close_pnl_sample`).

| test | instrument | listed same-day sessions in span | half days | excluded as read | **in the test** | span |
|---|---|---|---|---|---|---|
| T1 fly5_iron | SPY | 782 | 10 | V8 81, S03 137, S16b 392, Compass Close 326 (both names, union 793) | **266** | 2017-01-04 → 2022-04-27 |
|  | QQQ | 616 | 13 |  | **339** | 2012-06-01 → 2022-04-27 |
| T2 condor_em1 | SPY | 782 | 10 | V8 43, S03 124, S16b 255, CC 223 (union 516) | **266** | 2017-01-04 → 2022-04-27 |
| T3 condor_d20 | SPY | 782 | 10 | V8 43, S03 104, S16b 255, CC 223 (union 516) | **266** | same |
| T4 touch_d25 | SPY | 782 | 10 | V8 43, S03 139, S16b 255, CC 223 (union 516) | **266** | same |
| T5 h13_te | SPXW | 855 | 11 | V8 56, S03 110, S16b 275, CC 236 (union 558) | **297**, of which **246** not FOMC/CPI/NFP | 2017-01-03 → 2022-04-27 |
| T6 h15_s2 | SPXW | 855 | 11 | V8 56, S03 102, S16b 275, CC 236 (union 558) | **297**, of which **281** not FOMC or month-end | same |
| T7 h1_qqq | QQQ stock | — | 2 (2025-11-28, 2025-12-24) | none read H1's rule here | **257** signal sessions | 2025-10-13 → 2026-10-22 |

T1 by year (sessions): SPY 2017 61, 2018 52, 2019 47, 2020 48, 2021 44, 2022 14; QQQ 2012 24, 2013 41, 2014 42, 2015 53,
2016 53, 2017 30, 2018 19, 2019 14, 2020 14, 2021 35, 2022 14. By weekday: SPY Mon 66, Tue 1, Wed 102, Thu 4, Fri 93; QQQ
Mon 19, Tue 4, Wed 16, Thu 11, Fri 289. T1's two names fall on **479** distinct calendar sessions. SPY's 266 include
223 of Compass Close's P&L sample; SPXW's 297 include 234.

T7's span: H1's own prereg stopped at 2025-10-10 and named the sessions from 2025-10-13 as unopened data for SPY/QQQ; no
study has read the H1 rule there (Edge H4 read the same bars for a different rule). Everything T7 needs is on disk: QQQ
bars to 2026-10-23, Theta's EOD (official close) through 2026, H1's dividend table to 2026-09-21. No fetch.

**Holdout A** (2017-06-01 → 2022-05-12) is read again, and 15 of holdout B's 28 months lie in the SPY/SPXW span (T7 adds
2025-11, 2026-03, 2026-04, 2026-08). The ledger row is added in this commit.

### 2.3 Families with no fresh data

- **S17 put-writing:** its single test read SPY and QQQ standard monthlies 2012-06 → 2026-10, which is all Theta serves
  (the option lists start 2012-06-01). **Forward only** (section 9).
- **H7 and QQQ turn of the month** are not candidates (section 1.3). H7 is already forward-tracked; nothing is added.

### 2.4 What the fetch will be (section 10 says how)

| what | sessions | window | why |
|---|---|---|---|
| SPY same-day chain, every strike, 1-minute NBBO | 266 | 09:30–16:00 | T1–T4 (T4's first scan is 09:35) |
| QQQ same-day chain, every strike | 339 | 15:00–16:00 | T1 |
| SPXW same-day chain, every strike | 297 | 13:00–14:05 (kept: the rows stamped 13:00 and 14:05) | T5, T6 |
| SPX 1-minute prints | the SPXW sessions not on disk (2017-01-03 → 2017-05-31) | full day | T5, T6 spot |
| SPY and QQQ 1-minute bars | 266 and 339 | 16:00–17:31 | the after-hours decision price D |

On disk, not fetched: SPY bars 2017→, QQQ bars 2012→ (spot and the next 09:30 open), Theta EOD (the official close:
`research_notes/Compass H1/data/stock_eod_2012_2018.parquet`, `$SP/lake/stock_eod/year=2019`,
`data_lake/thetadata/stock_eod/year=2020..`), Cboe's SPX closes (`data/official_closes/cboe_SPX_History_2026-10-23.csv`),
VIX prints 2017-06→ (condor_d20's decile column only), SPX prints 2017-06→.

## 3. Fees

**Primary: Robinhood** (`docs/FEES_ROBINHOOD.md`, `scripts/fees_robinhood.py`). Fills are unchanged: buy at the ask, sell at
the bid of the NBBO row stamped at the entry minute.
- SPY/QQQ options: $0.0403 a contract bought; $0.0403 + TAF ($0.00329) + SEC ($20.60 per million of proceeds), each rounded
  up to the cent per sold leg; nothing at expiry, exercise or assignment.
- SPXW: $1.0403 a contract a side under $1.00 of premium, $1.1303 at $1.00 and up (non-Gold); nothing at settlement.
- Stock (T7, and the shares an exercise or assignment leaves under case (b)): $0 commission; on a sale the SEC fee and the
  TAF ($0.000195 a share), each rounded up to the cent; CAT $0.000003 a share each side. Under case (b) the shares are
  closed at the next 09:30 open and that closing trade pays these fees; the exercise or assignment itself pays $0.
- T7's fills: H1's $0.01 a share is a fee-only auction cost (FEES_ROBINHOOD.md) and is replaced by Robinhood's fees.

**Reported beside it: each study's own fees** — $0.65 a contract (leg) to open, nothing at expiry (T1–T4; the 15:58 exit
pays $0.65 a contract closed); $1.00 a contract a side (T5, T6); $0.01 a share each way (T7).

## 4. Settlement

**SPY and QQQ held to the close (T1–T4): PRIMARY = AFTERHOURS.md case (b)**, the measure its owner-fixed drop rule used:
- C = the official close (Theta EOD, `paper_audit.OfficialCloses` order); D = the close of the last post-market bar ENDING
  at or before 17:30 New York (a bar stamped t ends at t + 1); O = the next session's 09:30 bar open (Theta 1-minute).
- "In the money" = by $0.01 or more. Our long legs are exercised by exception on C; each short leg is assigned iff it is in
  the money at D. Every exercised or assigned leg delivers 100 shares a contract at its strike, the net shares marked at O:
  + (O − K) a long call, + (K − O) a long put, the negatives for a short. A leg not exercised expires worthless. A session
  with no D for the name is out of case (b) (counted, listed); a test whose D covers fewer than 50 % of its sessions is not
  judged (AFTERHOURS.md's rule).
- Not modelled (as AFTERHOURS.md): borrow on short stock, margin interest, a gap fill worse than the 09:30 bar's open.

**Reported, no verdict:** (0) every leg at intrinsic on C — "held to settlement, intrinsic at the official close",
**flagged: it carries the after-hours exercise risk it does not price**; (a) exercise by exception on C for every leg;
(c) both sides decided at D; for T1–T3 the tracker's own 15:58 exit (its `close1558` rows, at Robinhood's fees on both
sides); the study's own convention at its own fees (the tracker: (0) at $0.65; hyp B: the 16:00 bar at $0.65).

**SPXW (T5, T6):** cash-settled on Cboe's official SPX close; no exercise risk. **T7:** a stock trade (no option).

The 15:59 close-out is NOT the primary: it was pre-registered by the owner only for the case where after-hours prices could
not be fetched, and they can (2.1).

## 5. The code: the frozen rules run as committed

No strike, fill, tradable or settlement rule is re-implemented. What the drivers change is listed in full:
- **T1–T3:** `paper_tracker.py --backtest`'s replay (`paper_backtest.replay`) on a fresh Parquet root holding the fetched
  chains and symlinks to the stored bars, VIX and SPX files. The one substitution: the replay's calendar (which reads SPY's
  files, empty before 2017) is given this prereg's session list (stage1) through `ParquetSource.days`/`is_session`/`is_half`,
  so QQQ's 2012–2016 sessions run; the tracker's capture, close-quote and settle code is untouched. The official closes:
  `paper_audit.OfficialCloses(theta_glob=…)` over the three EOD stores of 2.4. Output rows go to a root of their own.
- **T4:** `Compass engine audit/move_atr_flow/engine.py`'s `session()` builds the scans and touches tables of the fresh
  sessions (RAW and OUT pointed at this study's folders; its flow and sweep tables are not used), then hyp B `engine.py`'s
  `run('SPY')` (its AUDIT path pointed at those tables) and `analyze.py`'s de-duplication and cell filter.
- **T5, T6:** `spxw_v2/sim.py`'s `Session`, `build` and `simulate` as at `7dfea57` (copied from git, sha256 recorded), with
  three inputs pointed: the chain root (`HWR_CHAIN_ROOT`), the SPX prints (this study's 2017-01 → 05 files, then the stored
  ones) and the Cboe closes (the full Cboe file in place of the 2022→ reconciliation CSV). The cells read: `exit = E2`,
  `tp = 0`, `stop = 0`, `cell N0.0` at 13:00 (T5) and `N0.5` at 14:05 (T6), with the F4 / F3 day filters.
- **T7:** `run_h1.py`'s functions with `NAMES = ('QQQ',)`, `FIRST = 2025-10-13`, `LAST = 2026-10-22`, and the two half days
  of the span added to its HALF_DAYS; every other constant unchanged.
- **Events** (T5's F4, T6's F3): the repo's `research/thetadata/vol_filters/events.csv` (`7dfea57`, 2017-06 →) plus, for
  2017-01 → 05: FOMC from `Edge search/H7_H8_H9/data/fomc_statements_2012_2026.json` (2017-02-01, 2017-03-15, 2017-05-03);
  CPI 2017-01-18, 02-15, 03-15, 04-14, 05-12 and NFP 2017-01-06, 02-03, 03-10, 04-07, 05-05 from the BLS release archives
  (https://www.bls.gov/bls/news-release/cpi.htm and empsit.htm, archive file names cpi_MMDDYYYY / empsit_MMDDYYYY, read
  2026-10-24).

## 6. The test, run once a family

Unit: % of max risk a trade (T1–T4: max risk = width − credit for a credit structure, the debit for a debit fly, × 100);
% of the credit (T5, T6); % of notional (T7). Under case (b) the return stays a share of the structure's max risk, which
an assigned overnight gap can exceed.

Sessions S_i in calendar order: every in-test session of the family (T1: the 479 calendar sessions of both names),
S_i = the summed % returns of the session's trades (0 if none), N_i = its trade count. Statistics: `audit_lib`
(`../Compass phase 3/backtest_audit/audit_lib.py`): `block_draws(n, 20)` (2,000 draws, house seed 20261022),
`weights_from`, per-trade mean = (W·S) / (W·N).

**k = 7 tests** (T1–T7). **Bonferroni:** the interval is the two-sided 1 − 0.05/7 percentile interval of the block-20
draws, so its lower end is the **0.357th percentile** (0.05/7/2).

**PASS, all five, at Robinhood's fees under the primary settlement:**
1. mean % per trade > 0;
2. the block-20 Bonferroni lower end > 0;
3. the top-5 sessions' share of total profit ≤ 100 % (the five largest session P&Ls in $ ÷ the total P&L in $; a total ≤ 0
   fails);
4. ≥ 300 trades;
5. every calendar year of the fresh span has a mean > 0, or at most one year has a mean ≤ 0.

**Stated before anything is computed:** T5 holds at most **246** trades, T6 at most **281** and T7 at most **257**, so
**condition 4 cannot be met by T5, T6 or T7**. They are run once and reported in full, and they FAIL on condition 4
whatever the returns. (They are still counted in k.)

## 7. MDE, committed before reading (`out/mde_prereg.json`)

MDE = (z_{1−0.05/14} + z_{0.80}) × SD / √n = (2.6901 + 0.8416) × SD / √n, with SD from the PREVIOUSLY READ period at
Robinhood's fees, under the primary settlement where it exists, and n the planned maximum. The per-session form uses the SD
of the per-session mean return and the session count (a session's trades move together).

| test | planned n (trades / sessions) | SD trade / session | source of the SD | MDE per trade | MDE per session | previously read mean |
|---|---|---|---|---|---|---|
| T1 fly5_iron | 1,210 / 479 | 144.0 / 115.2 % risk | AFTERHOURS period ii, fly5 iron, case (b) | **14.6 %** | **18.6 %** | +6.9 % (case b) |
| T2 condor_em1 | 1,330 / 266 | 128.1 / 98.8 | condor_d20 case (b) (proxy: no case (b) was run on em1) | 12.4 % | 21.4 % | +3.9 % (case 0) |
| T3 condor_d20 | 1,330 / 266 | 128.1 / 98.8 | AFTERHOURS period ii, condor_d20, case (b) | 12.4 % | 21.4 % | +3.8 % (case b) |
| T4 touch_d25 | ≈ 1,601 / 266 | 128.1 / 98.8 | proxy: condor_d20 case (b) | 11.3 % | 21.4 % | +4.6 % (case 0) |
| T5 h13_te | 246 / 246 | 80.0 % credit | final report 6d TEST | 18.0 % | 18.0 % | +8.7 % |
| T6 h15_s2 | 281 / 281 | 137.9 % credit | final report 6e TEST | 29.1 % | 29.1 % | +18.0 % |
| T7 h1_qqq | 257 / 257 | 0.80 % notional | final report 32 QQQ | 0.176 % | 0.176 % | +0.038 % |

**Read before the result:** every MDE is two to five times the mean the earlier read found. Case (b)'s overnight stock
risk (an SD of 100–145 % of max risk a trade) swamps a +4–7 % edge. **A FAIL here is weak evidence that no edge exists; a
PASS would be strong evidence.** The realised n and the MDE at it are printed with the result.

## 8. Also reported (no verdict)

For every test, at Robinhood's fees (and the headline line at the study's own fees): trades, sessions, win rate (P&L > 0),
average win and loss, median, best and worst trade with dates, profit factor, max drawdown ($, 1 lot, cumulative from 0 in
entry order), longest drawdown (sessions from a peak to the next high, or the end), the 95 % block-20 interval beside the
Bonferroni one, by year, by weekday and by entry time; **$1,000** walked through the trades (a) **at a fixed 1 lot**
(1,000 + the cumulative $ P&L; the minimum and the first date it is ≤ 0, if any) and (b) **at 10 % per trade** (the final
report's method B, `FINAL REPORT/build/thousand.py`: each trade gets 10 % of the balance at its session's start, 100 % ÷ n
when a session has more than ten); the settlement lines of section 4; T1 by name, by time (15:00 / 15:30) and its call and
put flies; the sensitivity lines (Compass Close's P&L-sample sessions out; EOD-marked sessions out, n = 0); the sessions
whose |official − 15:59 bar| > $0.25 (flagged, kept); the realised MDE.

## 9. Forward

- **S17 (no fresh data): forward only.** Primary: the ATM put, SPY and QQQ pooled, at Robinhood's fees, the S17 rule
  unchanged (sell the next standard monthly ATM put at the closing bid on each monthly expiration day, hold to its last
  trading day, settle at intrinsic on the expiration-day close; % of the cash set aside). **Forward N for 80 % power
  (one-sided 5 %): 147 cycles** (mean +0.66 %, SD 3.21 % a cycle, from the 2012–2026 read), about six years at two a month.
  Logged beside it, not judged: the 0.30-delta put (N 278 SPY / 146 QQQ a name). Pass at N: mean > 0 and the block-20
  95 % lower end > 0, and at most one negative year. S17 is not in the daily job; it is added to step 8 (end-of-day option
  quotes on each monthly expiration day — the path H6 already uses), with no change to the job's schedule.
- **A test that passes:** its rule goes into a one-page rulebook and to the forward paper test (it is already in the daily
  job for T1–T3; T4–T6 would be added); its forward N for 80 % power is computed from this test's own mean and SD and
  printed with the verdict. A pass on history still needs the forward test.
- **T5, T6, T7** cannot pass (section 6); the forward N is printed for each (T7: 2,763 trades, about 11 years).

## 10. Fetch [pin]

One ThetaData SDK login a fetch run (the daily job's `--source sdk` path; the key loaded in-process from
`$SP/secrets/research.env`, never printed, logged or committed; `td1_prod_…` redacted in every log), at most 3 requests in
flight, never 00:00–01:45 or 19:40–20:30 New York (checked before every request). Requests:
`option_history_quote(<ROOT>, expiration=D, date=D, interval='1m', strike='*', right='both', start_time, end_time)` one a
session; `stock_history_ohlc(<SYM>, interval='1m', date=D, start_time='16:00:00', end_time='17:31:00')`;
`index_history_price('SPX', date=D, interval='1m')`; `option_list_expirations` once a root to re-check the lists. Every file
is checked: root, expiration = the session, stamps inside the window; an empty or denied answer is logged with its request
and retried, never filled in. Raw data stay in the scratchpad (`$SP/compass_final/`), never committed. No outcome is
computed during the fetch; its verification reads roots, expirations, stamps and row counts only.

## 11. Integrity

- **Plain-loop re-derivation:** 70 trades (10 a test, seed 20261024) re-derived from the raw files with separate code (no
  polars, no shared helper, pyarrow to read rows into lists): strikes, the entry quotes, the settlement inputs (C, D, O /
  the Cboe close), the P&L under the primary at Robinhood's fees. **0 differences** required (tolerance 1e-6).
- **Lookahead check on 10 sessions with a control** (seed 20261024): every chain row and bar stamped after the entry
  minute blanked (the settlement inputs kept); no entry may change (strikes, quotes, tradable). Control: the entry read one
  minute later; entries should change.
- **Units asserted** at every boundary: option prices per share in (0, 1000) and SPX points in (0, 10,000); a $ P&L = 100 ×
  points − fees; % = $ ÷ the unit's $ base × 100; fees in $ a contract.
- The replay's own parity tests (`tests/test_paper_tracker.py`) and the frozen files' sha256 are recorded.

## 12. Files and stop rule

`research_notes/Compass Final/`: this prereg and the stage-1 files; then the fetch code and `FETCH_LOG.md`; then the run
code, `COMPASS_FINAL_REPORT.md` and `.pdf` (rendered as the final report was), and a one-page rulebook for any test that
passes. **Each test is run once.** If nothing passes, the report says so and the work stops.

## 13. Holdout ledger

One row in `../HOLDOUT_LEDGER.md`, added in this commit: 9 entry rules (T1–T7, and T1's call and put flies) and 4 settlement
lines on each of the 6 physically settled cells (24) — A ≥ 32 (T7 lies outside A), B ≥ 33.
