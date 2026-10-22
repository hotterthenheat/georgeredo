# The picker, pre-registered: the 0DTE opening-range fade, frozen before any of its P&L is read

Written 2026-10-22 and committed alone, before any trade of this rule is priced against an outcome. Nothing in this file
was computed from an option's price against its later path. To write it, the following were read: the sources named in
section 1 (documents and code, at the commits given); the GeorgeFi cards' DATES, GRADES and LEVEL FIELDS (not their P&L);
the stored minute files' COVERAGE (file lists, columns, a strike list); the stored UNDERLYING bars on card dates, to test
whether the cards' level prices can be reproduced (section 2.3 — no option price was read); and the flow recorder's
coverage (section 7). The fee figures are those cited in `../spxw_prereg/PREREG_SPXW.md` section 4.

**A disclosure the reader needs.** The engine audit already priced an entry universe built the same way as this rule
(`research_notes/Compass engine audit/exits_sizing.md` line 5, universe A, 2022–2026) under a fuller exit stack, and its
headline numbers are in that note's line 14, which the author read while looking for the rule's source. So the stored
2022–2026 NBBO is out of sample for this rule with respect to the CARDS it came from (GeorgeFi's 2026 ledger), not data
no study has looked at. The only sessions on disk that no study of this rule has read are 2026-10-14 → 2026-10-21; they are
reported as their own line (section 9), with no verdict of their own.

The owner's instruction (2026-10-22), item by item, is answered in sections 2–10. The pass rule is section 10.

---

## 1. Sources: which is the cards' code, which is the parameter writeup, which are the "improved" parameters

| what | where it is | status |
|---|---|---|
| **The cards** | GeorgeFi's closed-trade ledger (D1, `v2.0.0-ict` "ICT Main", 489 trades 2026-03-02 → 2026-10-08, every field), `evidence/public_api/trades_all.json.gz` at commit `75c29c9^` (= `7dfea57`, removed from HEAD by `75c29c9` "Fresh start"); the other books and captures in section 3 | read for dates, grades, level fields, outcomes (outcomes only for section 8) |
| **The code that produces the cards** | GeorgeFi's server-side engine | **NOT IN ANY REPO.** Not in georgeredo's history (every ref searched), not in the Slayer terminal (`/home/user/3abida`). What exists: the client bundle (`evidence/bundle_static/` at `75c29c9^`, the scratchpad's `evidence/nuxt_bundle/*.js`) — display strings only (e.g. "SL -25% · T1 +25% · T2 +45%"), no engine; and the cards' own fields (level types, `sweepsToday` with `sweptAt`, confluence tags such as `SWEEP_ALIGNED:+25(PDH)`), which name the levels but carry no threshold, window or bar rule |
| The Slayer terminal's Compass | `/home/user/3abida/src/components/compass/`, `src/data/compassStandIn.ts` (branch `claude/trusting-planck-o77m11`, HEAD `d6f2e09`) | a UI on the house's simulated stand-in: `compassStandIn.ts` lines 1–40 say "THE STAND-IN MAPPING, TO BE REPLACED BY THE ENGINE … nothing here prices or ranks anything". No sweep, level or exit rule; it does not produce the cards |
| **The parameter writeup** (the rule "as written") | the owner's Compass specification, whose text is not on disk; its parameters are recorded by the engine audit and implemented as code there: `research_notes/Compass engine audit/exits_sizing.md` (commit `9cf8110`) line 5 (universe A) and line 14 (the spec stack); `research_notes/Compass engine audit/exits_sizing/extract.py` (`9cf8110`) lines 3–6, 29–31, 73–75, 86–93, 98–110 (the entry); `…/exits_sizing/engine.py` (`9cf8110`; last touched `09799af`) lines 19, 79–137 (the exits); `research_notes/Compass engine audit/clock_session.md` (`d724ae4`) lines 93–94 (the opening range) and 153–154 (15:58); the constants as locked in `docs/compass-core-spec-v2.md` (`16eb3c0`) lines 41–60 (EPS, ticks), 131–158 (15:58, `may_ride`), 316 (0.68), 354 (1.25), 365–373 (the 5-minute stop), 381 | **the authority for every definition frozen below** (the cards' code being absent) |
| **The narrative** | GeorgeFi's own `/how` page, as recorded in `GEORGEFI_PRODUCT_MAP.md` line 161 and `GEORGEFI_SIGNAL_RESEARCH.md` lines 100–104 (both at `75c29c9^`); `STRATEGY_SPEC.md` lines 34–39 (`75c29c9^`) | "T1 +25 % sell half, T2 +45 %, breakeven lock at +6 % HWM, VIX-scaled trails 8/11/14 %, sweep stop −32 %, auto-close 15:58 ET"; "cash-settled ITM index contracts may ride to settlement" |
| **The "improved" parameters** | the owner's item 6 ("SPX/SPY/IWM only, prior-day-high sweep, 10:00–12:00, sell at +25% or 5 minutes"). No single document on disk states this set. Each piece traces to the cards: the ticker split, the 10:00–12:00 bucket and the median hold of 5.5 minutes in `evidence/analysis/trades_breakdown_v2.txt` lines 97–110 and 130–131 (`75c29c9^`) and `GEORGEFI_SIGNAL_RESEARCH.md` lines 84 and 102; the product list "approve SPX, SPY, IWM; block QQQ" in `sweep_trigger.md` line 316 (`09799af`, quoting the owner's spec, itself read off the ledger); the PDH sweep in the cards' `SWEEP_ALIGNED:+25(PDH)` tag (`GEORGEFI_SIGNAL_RESEARCH.md` line 77) | frozen from the owner's words, section 6 |

Every gap this leaves is named where it binds, with the choice made.

---

## 2. The primary rule: the opening-range fade, 10:00–12:00, exactly

### 2.1 Minutes and data

Minute m = 0 is 09:30 New York. A 1-minute bar stamped m closes at m + 1. A chain row stamped m is the NBBO at m. A quote
**stands** when bid and ask are both present, ask ≥ bid ≥ 0 and ask > 0 (`extract.py` line 81). Every price is rounded to
four decimals on load and every threshold test carries EPS = 1e−9 (`compass-core-spec-v2.md` lines 30–45; the audit's
float32 bug, `exits_sizing.md` line 5). Files (read only):

- chains `…/scratchpad/theta/data_full/chains/{SPY,QQQ,IWM,SPXW}/<D>.parquet` (same-day expiry only);
- ETF bars `…/theta/data/underlying/{SPY,QQQ,IWM}/<D>.parquet`; SPX prints and VIX `…/theta/data/index/{SPX,VIX}/<D>.parquet`;
- `…` = `/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`.

### 2.2 The level: the opening range

ORH = the highest high and ORL = the lowest low of the bars stamped 09:30–09:59 (m = 0..29, thirty bars) —
`extract.py` lines 73–75; the owner's spec "ORH/ORL from 570 ≤ t ≤ 599" (`clock_session.md` line 93). Valid from the bar
stamped 10:00.

### 2.3 The levels the cards name, and what could not be reproduced

The cards' `watchLevels.allLevels` name ORH, ORL, PDH, PDL, PWL, GEX_SUPPORT, GEX_RESISTANCE and GAMMA_FLIP, each with a
price and a `sweepDirection` (BEARISH for a high, BULLISH for a low — the fade). Their prices were checked against the
stored bars on the cards' own dates: on the 96 SPY/QQQ/IWM cards that carry levels, **none of 98 ORH/ORL values equals the
stored bars' high/low of the first 1, 5, 10, 15, 30 or 60 minutes within $0.02, and none of 18 PDH values equals the prior
session's regular-hours high** (the cards' feed or window differs and cannot be recovered). So the cards' own level
computation is a gap; the writeup's (2.2, 6.2) is used. GeorgeFi's reconstruction elsewhere used a 15-minute range usable
from 09:45 (`STRATEGY_SPEC.md` line 74, `BACKTEST_RESULTS.md` line 16); that variant is not run.

**Walls.** GEX_SUPPORT / GEX_RESISTANCE / GAMMA_FLIP need a strike-level dealer book at each date. None exists on disk for
the test span (`sweep_trigger.md` lines 179, 184 and 375: the UW levels file has every wall column empty; UW's daily
`greek-exposure` is one net number a day from 2025-10-15). The level set is therefore reduced to the opening range
(primary) and the prior-day high (the improved run). No wall enters any run.

### 2.4 The sweep ("raid") and the direction

For each name and session, separately for each side, scan the bars stamped 10:00 through 11:59 (m = 30..149) in order
(`extract.py` lines 29, 86–93):

- **High side → PUT**: the first bar with high ≥ ORH × (1 + 2/10,000) **and** close < ORH.
- **Low side → CALL**: the first bar with low ≤ ORL × (1 − 2/10,000) **and** close > ORL.

That is: an excursion of at least 2 bps beyond the level and a close back inside on the same 1-minute bar
(`BUFFER_BPS = 2.0`, line 31). No condition on the bar before; no confirmation bar. The fade buys the side against the
sweep: a high-side sweep buys a put, a low-side sweep a call.

**SPXW.** SPX has one print a minute and no bar high/low, so the sweep is read on SPY's bars scaled by the SPX/SPY ratio
(`extract.py` lines 55–66, a stated proxy): ORH, ORL and the trigger bar's high, low and close are SPY's × ratio. One
change from `extract.py`, to remove a look-ahead: its ratio is the median over quote minutes 25–34 (09:55–10:04), which
reaches past an entry at 10:01–10:03; here **ratio = the median, over quote minutes m = 21..30 (09:51–10:00), of the SPX
print stamped m ÷ the close of SPY's bar stamped m − 1** (all known at 10:00, before the first possible entry). No ratio
(no pair in those minutes) → no SPXW trade that session, logged.

### 2.5 Entry and the contract ("nearest")

- **Entry minute** e = the trigger bar's stamp + 1 (the quote at the bar's close; `extract.py` line 91: `bm + 1`), so
  e ∈ 10:01 … 12:00. No entry if e > close − 2 (`extract.py` line 99).
- **Spot at e**: ETF — the close of the bar stamped e − 1 (the trigger bar); SPXW — the SPX print stamped e. No spot →
  no trade, logged.
- **Nearest**: among the same-day contracts of the trade's side whose quote stands at e, the **nearest out-of-the-money
  strike**: for a put the highest strike strictly below spot, for a call the lowest strike strictly above spot
  (`extract.py` lines 101–104). No such contract → `NO_TRADE('no eligible contract')`, logged. No spread filter (the
  writeup's code applies none; the locked spec's 5% spread guard, `compass-core-spec-v2.md` line 271, came later from
  the audit and is not "as written"); no delta band.
- **Fill**: 1 contract at the **ask** stamped e.

### 2.6 The cap

At most **one trade per name, per session, per side** — the first sweep of each side (`extract.py` lines 86–93, the
`break`). A put and a call may both be taken in one session, and may overlap in time (the writeup's code allows it; the
narrative's "one position per ticker, 30-minute cooldown", `GEORGEFI_PRODUCT_MAP.md` line 161, is not in the code and is
not applied).

---

## 3. Which exit set is live, and what is run

**What the cards show.** The cards' exits are the narrative family, not the formal set: `STOP LOSS (-12%)` 25,
`SNIPER: EMERGENCY_STOP (-24…-50%)` 62, `TRAILING PROFIT (+8…+24% locked)` 40, `SNIPER: T1 PROFIT LOCK (+31…+60%)` 43,
`HARD KILL (-25|-28% floor)` 16, structure and GEX exits, theta-burn time stops at 10–18 minutes, a breakeven field
(`break_even_active`), and some manual exits (`GEORGEFI_SIGNAL_RESEARCH.md` lines 100–104; `trades_breakdown_v2.txt`
lines 2–80). No card shows a 0.68 × ask stop, an all-out 1.25 × ask target or a 5-minute time stop. So the live engine
behind the cards ran the narrative's kind of exits, with thresholds that changed by era.

**What the writeup says.** The formal set: stop 0.68 × entry ask, target 1.25 × entry ask, the 5-minute time stop, flat
15:58 (the owner's spec as recorded in `exits_sizing.md` line 14 and locked in `compass-core-spec-v2.md` lines 316, 354,
365–373, 381).

They disagree, so by the owner's instruction **the formal set is the PRIMARY test** and the narrative's breakeven lock
and VIX trail are a labelled SECONDARY. Exactly:

### 3.1 PRIMARY — formal: stop 0.68, target 1.25, 5 minutes, 15:58

Checked at every quote minute m = e + 1 … 15:58 (m = 388) whose contract quote stands, on the **bid**:

1. **Target**: T = 1.25 × entryAsk rounded UP to the option's tick (a resting sell rounds up; ETF $0.01; SPXW $0.05 under
   $3.00, $0.10 at or above — `compass-core-spec-v2.md` lines 46–60). It fills at the first minute whose bid ≥ T − EPS,
   **at T** (a resting limit: a bid at or above it has traded with it; never more than that minute's bid).
2. **Stop**: the first minute whose bid ≤ 0.68 × entryAsk + EPS sells at **that minute's bid** (a gap through sells at
   the gapped bid). The threshold itself is not rounded to the tick.
3. **5 minutes**: at minute e + 5, if the highest bid over minutes e + 1 … e + 5 is below 1.06 × entryAsk − EPS, sell at
   the bid of minute e + 5 (if no quote stands at e + 5, the last standing bid after e; if none, $0). This is the time
   stop as the writeup states it — "5-minute time stop if no +6%" (`exits_sizing.md` line 14; `engine.py` lines 96–103;
   `compass-core-spec-v2.md` lines 372–373). If the bid has reached +6% by e + 5, the stop does not fire and the trade
   runs on under 1, 2 and 4.
4. **Flat 15:58**: sell at the bid of minute 15:58 (m = 388; if no quote stands then, the last standing bid before it).
   The ETFs are never held past 15:58 (physically settled). **SPXW is flat at 15:58 too**: the writeup as locked has
   `SPXW_MAY_RIDE = False` (`compass-core-spec-v2.md` lines 131–158, the owner's default), and the cards show no rides
   (two scalps of 451 exited after 15:50, `GEORGEFI_SIGNAL_RESEARCH.md` line 103). The narrative's "may ride" is a
   labelled sensitivity (3.4).
5. **Ties in one minute**: the target first; then the stop; then the 5-minute stop; then the flat (`engine.py`: a target
   at or before the common exit wins; the common exits in the order stop, time, flat with strict `<`).
6. **No bid**: an exit whose price is $0 (bid 0 or none) sells nothing and pays no exit fee. An ETF contract left so is
   worth $0 (it is out of the money; any that is in the money at the 15:58 spot is listed). An SPXW contract with no bid
   at 15:58 is cash-settled at its intrinsic value on the official SPX close (`data/official_closes/
   cboe_SPX_History_2026-10-22.csv`), no fee.

### 3.2 SECONDARY — the narrative's breakeven lock and VIX trail (labelled, never a verdict)

The same entries; stop 0.68 × ask, target 1.25 × ask (one contract, all out — "sell half" needs two), flat 15:58, **no**
5-minute stop, and:

- **Breakeven lock at +6%**: armed at the first minute whose bid ≥ 1.06 × entryAsk − EPS (the peak including that
  minute); from the next minute on, sell at the first bid ≤ entryAsk + EPS (`engine.py` lines 88–91).
- **VIX trail**: active at minute m once the highest bid through m − 1 ≥ 1.06 × entryAsk − EPS; sell at the first active
  minute whose bid ≤ (1 − t) × that peak + EPS, with t by the VIX print at e (else the highest of the five prints
  before, else 11%): VIX < 15 → 6%, < 20 → 8%, < 30 → 11%, else 14% (`engine.py` line 19 — the owner's spec's tiers;
  the narrative's "8/11/14%" is the same ladder without its bottom rung).
- Ties: target, stop, lock, trail, flat.

### 3.3 Sensitivity S2 (labelled, no verdict): "5 minutes" as a hard exit

The primary with item 3 replaced by: at e + 5, sell at the bid whatever the bid has done. Reported because the owner's
own summary reads "5 minutes" plainly; the writeup's code conditions it on +6%.

### 3.4 Sensitivity S3 (labelled, no verdict): SPXW rides if in the money

The primary for SPXW, except that a position still open at 15:58 whose contract is in the money on the 15:58 SPX print is
not sold but cash-settled at its intrinsic value on the official SPX close (the original spec's "if ITM and
delta-aligned at 958, ride", `clock_session.md` line 153; a long option in the money is aligned), no exit fee.

---

## 4. Fees ($0.65 + pass-throughs per contract each way; nothing at expiry)

Per contract on the buy and on every sale; nothing on a contract that expires or is cash-settled; nothing on an exit
at $0.

| name | per contract, each way | items and sources |
|---|---|---|
| SPY, QQQ, IWM | **$0.68748** | $0.65 commission (the owner's assumption) + Options Regulatory Fee $0.01248 a contract side (Cboe Exchange Fees Schedule, October 1, 2026, Regulatory Fees, as cited in `../spxw_prereg/PREREG_SPXW.md` line 116) + OCC clearing fee $0.025 a contract (OCC Schedule of Fees, SR-OCC-2025-002, SEC Release 34-102437, as cited in `PREREG_SPXW.md` line 117). No exchange transaction fee is assumed for these multi-listed ETF options (none is cited; a customer order's exchange fee depends on venue and broker). ORF is charged per exchange on its own rules; Cboe's figure is the stated assumption. |
| SPXW | **$1.18748** when that side's fill price is under $1.00, **$1.27748** at $1.00 or more | `PREREG_SPXW.md` section 4, lines 105–127 (commit `2820bb4`): $0.65 + Cboe customer fee $0.36 (CS) / $0.45 (CT) + SPXW execution surcharge $0.14 + ORF $0.01248 + OCC $0.025; the tier of each side by its own fill (the ask paid, the price sold at) |

Not included, as in `PREREG_SPXW.md` lines 123–127: FINRA's TAF and the SEC's Section 31 fee (cents a trade), any broker
fee. Today's schedule is applied to every year (OCC's fee was $0.02 before 2025-02-14: a $0.005 overstatement then).

---

## 5. The test span, per name, and the excluded dates

**Sessions.** Every full NYSE session (`research_notes/Compass phase 3/backtest_audit/audit_lib.py`
`expected_sessions`: holidays and half days out, as every report here) from the name's first same-day chain to its last
on disk, **minus the excluded dates**, that has the chain file, the bar files (ETF: its own; SPXW: SPY's) and, for SPXW,
the SPX print file. A session missing any file is listed by date with the reason and left out. A session in the universe
with no trade counts with P&L 0.

| name | chains on disk | span tested (before exclusions) | note |
|---|---|---|---|
| SPY | 988 files 2022-11-11 → 2026-10-21 | 2022-11-11 → 2026-10-21 | |
| QQQ | 988 files 2022-11-11 → 2026-10-21 | 2022-11-11 → 2026-10-21 | |
| SPXW | 1,114 files 2022-05-13 → 2026-10-21 | 2022-05-13 → 2026-10-21 | sweeps on SPY bars × ratio (2.4) |
| IWM | 621 files 2024-04-19 → 2026-10-09 | 2024-04-19 → 2026-10-09 | IWM's chains and bars for 2026-10-12 → 21 are not on disk (section 11) |

**Excluded dates: every date a card exists for, 134 dates (133 weekdays), 2026-03-02 → 2026-10-13.** The union of:

| source (at `75c29c9^`) | dates | span |
|---|---|---|
| D1 ICT Main ledger, `evidence/public_api/trades_all.json.gz`, entry and exit dates in New York (489 trades; the source of the "improved" parameters too) | 114 | 2026-03-02 → 2026-10-08 |
| Trade Now book `trades_book_trade_now_v1.json.gz` (52 cards graded A+/A) | 34 | 2026-07-09 → 2026-10-12 |
| Singles TODAY `trades_book_singles_today_v1.json.gz`, SPX Plans `trades_book_spx_plan_v1.json.gz` | 8, 7 | 2026-10-05 → 2026-10-13 |
| SPX paper trades `evidence/auth_api/spx_paper-trades_days_30_ticker_SPX.json` (21, graded) | 11 | 2026-09-14 → 2026-10-07 |
| Recap alerts `evidence/analysis/recap_alerts.csv`; public tape `evidence/analysis/public_tape_signals.csv`; decision snapshots `evidence/analysis_snapshots/` | 9, 6, 1 | 2026-09-25 → 2026-10-13 |

The list:

2026-03-02 2026-03-03 2026-03-04 2026-03-05 2026-03-06 2026-03-09 2026-03-10 2026-03-11 2026-03-12 2026-03-13
2026-03-16 2026-03-17 2026-03-18 2026-03-19 2026-03-20 2026-03-23 2026-03-24 2026-03-25 2026-03-26 2026-03-27
2026-03-30 2026-03-31 2026-04-01 2026-04-02 2026-04-06 2026-04-07 2026-04-08 2026-04-09 2026-04-10 2026-04-13
2026-04-14 2026-04-16 2026-04-17 2026-04-20 2026-04-21 2026-04-22 2026-04-23 2026-04-24 2026-04-27 2026-04-28
2026-04-29 2026-04-30 2026-05-01 2026-05-04 2026-05-06 2026-05-08 2026-05-11 2026-05-12 2026-05-13 2026-05-14
2026-05-15 2026-05-18 2026-05-20 2026-05-21 2026-05-26 2026-05-27 2026-05-28 2026-05-29 2026-06-01 2026-06-02
2026-06-03 2026-06-08 2026-06-11 2026-06-12 2026-06-15 2026-06-16 2026-06-17 2026-06-22 2026-06-24 2026-06-25
2026-06-26 2026-06-29 2026-06-30 2026-07-01 2026-07-06 2026-07-07 2026-07-08 2026-07-09 2026-07-10 2026-07-13
2026-07-14 2026-07-15 2026-07-16 2026-07-17 2026-07-20 2026-07-21 2026-07-22 2026-07-27 2026-07-28 2026-07-29
2026-07-30 2026-07-31 2026-08-03 2026-08-04 2026-08-11 2026-08-13 2026-08-14 2026-08-17 2026-08-18 2026-08-19
2026-08-20 2026-08-21 2026-08-24 2026-08-26 2026-08-27 2026-08-28 2026-08-31 2026-09-01 2026-09-02 2026-09-04
2026-09-09 2026-09-10 2026-09-11 2026-09-14 2026-09-15 2026-09-16 2026-09-17 2026-09-18 2026-09-21 2026-09-23
2026-09-24 2026-09-25 2026-09-28 2026-09-29 2026-09-30 2026-10-01 2026-10-05 2026-10-06 2026-10-07 2026-10-08
2026-10-09 2026-10-10 2026-10-12 2026-10-13

(2026-10-10 is a Saturday recap date.) `run_picker.py` re-derives this list from the git objects and stops if it differs.
The sessions between card dates in 2026 (e.g. 2026-04-15) are not card dates and stay in, as the instruction reads.

---

## 6. The second run, labelled "IMPROVED (picked on the cards)" — separate, never pooled

The owner's item 6, frozen literally:

- **Names**: SPXW (SPX's 0DTE; the AM-settled SPX root is never traded), SPY, IWM. Not QQQ.
- **Level**: PDH = the highest high of the prior session's regular-hours bars (the previous session with a bar file,
  a half day included, bars stamped 09:30 to its close). SPXW: SPY's prior-session high × today's ratio (2.4), the
  stated proxy.
- **Sweep**: the first bar stamped 10:00–11:59 with high ≥ PDH × (1 + 2/10,000) and close < PDH (the same bar shape as
  2.4). **PDH only, so puts only**; the PDL mirror is not the owner's set and is not run.
- **Entry, contract, fill, cap**: as 2.5–2.6 (one a name a session).
- **Exit**: the target T = 1.25 × entryAsk (tick-rounded up, filled at T on the first bid ≥ T − EPS); else **sell at the
  bid of minute e + 5** (unconditionally; the last standing bid after e if none at e + 5; $0 if none). No stop (the
  owner's set names none). The 15:58 flat stays as a backstop (it cannot bind before 12:05).
- **Fees, sessions, statistics**: as sections 4, 5, 9. **Excluded dates**: the same 134 — the improved parameters were
  read off D1, whose dates are all inside that list.

---

## 7. The flow gate

**Definition** (the owner's spec, module 11, as recorded: "trade-side sweep premium > other side", `sweep_trigger.md`
and `move_atr_flow.md` lines 78–81; `compass-core-spec-v2.md` lines 859–866): a trade on side X entered at minute e
passes the gate when, over Unusual Whales flow alerts for the name (SPXW: the `SPX` file, roots SPXW and SPX) with
`has_sweep = true` and `created_at` in [e − 5 min, e) New York, the summed `total_ask_side_prem` of alerts of type X
(`put` for a put trade, `call` for a call) is strictly greater than that of the other type. Any expiry. No alert in the
window → the gate fails.

**Coverage.** Flow history on disk: `data_recorder/flow_alerts/{SPY,QQQ,IWM,SPX}/` — **one session, 2026-10-21** (and
`net_prem_ticks` the same single day). `data_lake/unusualwhales/` holds no flow (earnings, greek-exposure, IV rank, max
pain, daily OHLC, realized vol, VRP only). So the flow history does **not** cover the span: **the primary test runs
without the gate**, and the flow-gated run is the primary rule restricted to 2026-10-21, gate applied, for SPY, QQQ and
SPXW (IWM's chain for that day is not on disk), reported separately and descriptively (no interval, no verdict — one
session).

---

## 8. The grade check (descriptive only)

The grade is NOT a filter in any run: the writeup says it cannot be rebuilt from its inputs (`GEORGEFI_SIGNAL_RESEARCH.md`
line 56: "grade is not a pure function of recorded confidence"; `sweep_trigger.md` section 4 and line 322).

Separately, on the cards that store a grade and an outcome:

- **Primary set**: D1 (489 trades): `setupGrade` A+ (177), A (227), A− (53), B+ (30), B (2). Return per trade =
  `pnlPercent` × 100 (% of the entry premium, as the card records it); dollars = `pnl`.
- For each grade: n, mean return per trade, win rate (`pnl` > 0), and a **20-session moving-block bootstrap** 95% interval
  of the per-trade mean over the cards' sessions (the New York entry dates, 114, in calendar order; per session the sum of
  that grade's returns and its count, zero where none; `audit_lib.session_stats`, 2,000 draws, seed 20261022). The
  orderings A+ − A and A − B+ (and A+ − B+) as paired differences of the per-trade means on the same block draws, each
  with its interval. A− and B are shown, not compared.
- The same table on the 0DTE-account subset (`accountType = 0DTE`), and, as their own lines, the Trade Now book (A+/A
  only) and the SPX paper trades (by `setupGrade`).
- Read as: does A+ > A > B+ hold in the means, and do the intervals of the differences clear zero. Descriptive: no
  verdict, no use in any run.

---

## 9. What is reported (PICKER_REPORT.md, in AUDIT.md's format)

The prereg hash at the top. For each run (PRIMARY; SECONDARY; S2; S3 for SPXW; IMPROVED), **per name × per calendar year
and per name over the whole tested span**: sessions, trades, mean $ per trade after costs and mean return per trade in %
of the entry premium (P&L after both fees ÷ (entry ask × 100)), each with its **20-session moving-block bootstrap 95%
interval** (`audit_lib.session_stats`, blocks of 20 consecutive sessions of the name's tested sessions, 2,000 draws, seed
20261022; no interval under 60 sessions, shown "—"), the win rate (P&L after costs > 0) beside it, and the share of exits
by stop / target / 5 minutes / 15:58 (the secondary: stop / target / lock / trail / 15:58). Also: trades not taken and
why (no ratio, no spot, no eligible contract), exits at $0, ETF contracts in the money with no bid at 15:58. A line for
the never-read sessions 2026-10-14 → 2026-10-21 (no verdict). The flow-gated run (7) and the grade check (8). What IWM and
RUT would cost to fetch (11).

`run_picker.py` reads files only and is deterministic (no draw but the seeded bootstraps); `verify_picker.py` re-derives
at least 30 random primary trades (and 10 improved) from the raw quote and bar files with separate plain-loop code — the
trigger bar and that no earlier bar qualified, the ratio, the strike, the entry ask, every exit minute and price, the
fees and the P&L — and requires 0 differences.

---

## 10. The pass rule, exactly as the owner wrote it

"Pass: mean > 0 with the interval clear of zero on each name, judged only on the span with the excluded dates removed."

Applied mechanically to the **PRIMARY** run only: for each name, over its whole tested span (section 5, the excluded
dates removed, all years together), the mean return per trade after costs (% of the entry premium) and its 20-session
block-bootstrap 95% interval. **A name PASSES iff the mean > 0 and the interval's lower end > 0.** A name with no interval
(under 60 sessions) does not pass. The rule passes as a whole only if every tested name passes. The dollar mean and its
interval are reported beside it and do not change the verdict. The per-year rows, the secondary, S2, S3, the improved run,
the flow-gated run and the never-read line carry no verdict of their own (the improved run's numbers are shown against the
same rule, labelled, for reading only). Nothing in this file is changed after any number is read; any deviation is listed
in the report as a deviation.

---

## 11. IWM and RUT: not fetched; what they would cost (no vendor call is made)

- **IWM**: chains and bars are on disk 2024-04-19 → 2026-10-09 and are used. Missing: the 8 sessions 2026-10-12 → 10-21
  (2 are card dates). Fetching them is 8 × ThetaData `/v3/option/history/quote` (symbol IWM, expiration = date = D,
  interval 1m) + 8 × `/v3/stock/history/ohlc` (IWM, 1m) = 16 requests, about 2.6 MB (IWM's stored files average 0.32 MB a
  session; the bars are kilobytes) — the request shapes of `scripts/paper_backtest.py` lines 2001–2003.
- **RUT** (RUTW same-day, cash-settled; RUT's index prints): nothing on disk. One `/v3/option/list/expirations` call
  (symbol RUTW) fixes which sessions had a same-day RUTW expiry; then one `/v3/option/history/quote` (RUTW, expiration = date
  = D, 1m) and one `/v3/index/history/price` (RUT, 1m) a session. Bounds over 2022-11-11 → 2026-10-21 (≈ 980 sessions):
  at most ≈ 1,960 requests if every session had one, ≈ 1,180 at three expiries a week; size about 0.3–0.8 MB a session
  (between IWM's 0.32 MB and SPXW's 0.78 MB stored averages — RUT lists fewer strikes than SPX), so about 0.2–0.8 GB. RUT
  has no bar high/low either: its sweeps would be read on IWM's bars × the RUT/IWM ratio (the SPXW proxy's analogue). The
  owner decides before anything is fetched.
