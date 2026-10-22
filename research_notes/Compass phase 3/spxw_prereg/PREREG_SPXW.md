# SPXW pre-registration: the fly5 iron and condor_d20 analogues, fixed before any SPXW P&L is read

Written 2026-10-22 (UTC 02:20) and committed before any SPXW structure was priced against an outcome. Nothing in this
file was computed from an SPXW structure's P&L. To write it, the following were read and nothing else: the research
notes named in section 6; `scripts/paper_tracker.py` (the strike, delta and structure rules); `scripts/paper_backtest.py`
(the replay's spot and file conventions); `research_notes/Compass phase 3/backtest_audit/AUDIT.md` and `audit_lib.py`
(the report format, the calendar and the bootstraps); Cboe's and OCC's published fee documents and Cboe's SPX product
specification (section 4); and, from the stored minute files, the SPXW chains' STRIKE LISTS by minute and the SPX print and
SPY bar closes at 13:00, 15:00 and 15:30 on every fifth SPXW session (663 minute-points) — to fix the SPX/SPY ratio and
check which wing strikes are listed. No bid, ask or mid of an SPXW contract was read for this file.

The owner's instruction (2026-10-22): "SPXW, pre-registered. 1. Before reading any SPXW P&L, write and commit
PREREG_SPXW.md … 2. Source the official SPX closing value for every session in range … 3. Same run: ATM extrinsic in bps of
spot at 15:00, 15:30 and 15:58 for SPY, QQQ and SPXW, against the realized |move| to settlement, by period … 4. Same format
as AUDIT.md: periods never pooled, session-sum stats, block bootstraps, 15:58 exit alongside."

## 1. The instrument and the data

- **SPXW same-day contracts only**: PM-settled, cash-settled, European (Cboe SPX product specification, read 2026-10-22:
  "European - SPX/SPXW options generally may be exercised only on the expiration date"; SPXW "Exercise results in cash
  delivery … Settlement uses the closing sales prices of the component securities on the expiration date"; "Trading in
  SPXW options will ordinarily cease on the day of expiration, 3:00 pm CT"). Never the AM-settled SPX root. The chains
  are `data_full/chains/SPXW/<D>.parquet` under `PAPER_PARQUET_ROOT` (fetched by root SPXW, same-day expiry; 1,114 files
  2022-05-13 → 2026-10-21). From 2022-05-13 every weekday has an SPXW same-day expiry (Tuesday and Thursday expiries were
  listed by then), so every full session has one.
- **Session universe**: every full NYSE session in a period (the calendar written out in `backtest_audit/audit_lib.py`:
  holidays and half days out, as every ETF report and the tracker skip half days) that has an SPXW chain file, an SPX print
  file (`data/index/SPX`) and an SPY bar file (`data/underlying/SPY`). A session missing any of them, or missing its official
  close (section 5), is listed by date with the reason and left out of every statistic. A session in the universe where
  no structure was tradable counts as a session with P&L 0.
- **Minute conventions (the replay's, `paper_backtest.py`)**: minute m = 0 is 09:30 New York; a chain row stamped m is the
  NBBO at m; **SPX spot at m = the SPX print stamped m** (`SPX_SPOT_SOURCE`, "the SPX print at the minute (the research
  convention)"); SPY's spot at m = the close of the SPY bar stamped m − 1 (the bar that closes at m). A minute whose SPX
  print is missing has no spot and builds nothing (logged untradable, reason "no SPX print").
- **The chain at a minute** is `paper_tracker.Chain` built from the rows stamped m (the replay's adapter turns them into
  OCC symbols under the SPXW root): a quote stands when bid and ask are both present, ask ≥ bid and bid ≥ 0. "Listed
  strikes" at m = every strike in the rows stamped m (`Chain.listed`), quoted or not.

## 2. The two analogues, exactly

**The ratio.** At each entry minute m of each session: ratio(m) = SPX print stamped m ÷ the close of SPY's bar stamped
m − 1 (each instrument's replay spot at m). Measured on 663 minute-points (13:00, 15:00, 15:30 on every fifth SPXW session):
min 9.998, median 10.029, max 10.045 — so 5 × ratio is 49.99–50.23 and 2 × ratio 20.00–20.09. A minute with no SPY bar
close at m − 1 has no ratio and builds nothing.

**Rounding to listed strikes.** A wing target T is moved to the listed strike nearest T (a tie: the strike farther from the
structure's centre / short strike, i.e. the wider wing). The two wings are found separately, so a structure can be
asymmetric when a strike is not listed at the minute (2 of 663 checks put a fly's put wing at 55 instead of 50; 1 of 663
checks of a 2 × ratio offset, measured from K0, landed at 25 instead of 20). An asymmetric structure's max risk is the WIDER wing's width × 100 − the credit.

**(A) fly5 iron → SPXW iron fly, 15:00 and 15:30.** At m = 15:00 and m = 15:30, every session in the universe:
- K0 = the strike nearest SPX spot among the strikes with a call and a put both quoted with asks > 0 (a tie: the lower
  strike) — `paper_tracker.Chain.nearest`, the fly5 rule unchanged.
- Call wing K_hi = the listed strike nearest K0 + 5 × ratio(m); put wing K_lo = the listed strike nearest K0 − 5 × ratio(m)
  (expected: ±50 points on 661 of 663 checks).
- Legs: sell the K0 call and the K0 put, buy the K_lo put and the K_hi call, one contract each (four contracts).
- Tradable (fly5's rule, its threshold scaled by the ratio): both wings quoted (a `Chain` quote), both K0 bids > 0, and max
  risk at the legs' NBBO (wider wing − credit) ≥ 0.05 × ratio(m) (fly5's MIN_RISK 0.05 × ratio, ≈ $0.50). Otherwise the
  row is untradable with its reason; nothing is filled.
- Only the iron fly. The long call and long put flies are not part of this test.

**(B) condor_d20 → SPXW 20-delta iron condor, 13:00, 13:30, 14:00, 14:30, 15:00.** At each minute, every session:
- Short call and short put = `paper_tracker.nearest_delta(chain, S, side, 0.20)` with S = the SPX print at m — condor_d20's
  rule exactly, imported, never re-implemented: the OTM strike (a call K > S, a put K < S) whose Black-Scholes |delta| is
  nearest 0.20, r = q = 0, the vol implied by each option's own mid (σ√τ by 60 bisections on [1e-5, 5], so τ cancels), the
  candidates with mid > 0, ask > 0 and the mid under the no-arbitrage bound; a tie goes to the farther-OTM strike.
- Long call = the listed strike nearest K_sc + 2 × ratio(m); long put = the listed strike nearest K_sp − 2 × ratio(m)
  (expected: 20 points beyond each short).
- Tradable (condor_d20's `_condor` rule, the credit threshold scaled): each short's bid > 0, each long's ask > 0, both
  verticals present, and each vertical's credit (short bid − long ask) ≥ 0.05 × ratio(m) (MIN_CREDIT 0.05 × ratio ≈ $0.50;
  the condor's two together ≥ 0.10 × ratio).
- Four contracts. No filter on the frozen t2 model's decile (condor_d20 carries it as a column, never a filter; the model
  is SPY's and is not computed for SPXW).

Both are held to expiration (cash settlement on the official close, section 5). Beside the hold, each trade is also closed
at 15:58 (section 3). The structures are built through the tracker's `Chain`, `nearest_delta`, `Leg`, `Structure`, `_leg`
and `intrinsic` imported from `scripts/paper_tracker.py`; the only new code is the wing-to-listed-strike step and the
scaled thresholds above. 50 random structures are re-derived from the raw chain by separate plain-loop code (its own
delta bisection) before any table is read.

## 3. Fills

At entry, for every tradable structure:
1. **Legs at their own NBBO** (as the ETF replay): each short at its bid, each long at its ask; the credit is the sum.
2. **The package at its NBBO, rounded against us to the complex increment** — the PRIMARY fill for the pass/fail rule.
   The package's NBBO credit is the same net of the legs' bids and asks; a complex order's net price must be a multiple of
   $0.05, so the credit is rounded DOWN to the next multiple of $0.05 (credit_pkg = floor(credit / 0.05) × 0.05, with a
   1e-9 tolerance). Source: Cboe SPX options specifications, https://ww2.cboe.com/tradable_products/sp_500/spx_options/specifications
   (read 2026-10-22; the page carries no update date, ©2025): "Minimum tick for options trading below 3.00 is 0.05 ($5.00)
   and for all other series, 0.10 ($10.00)." and "For complex orders legs may trade in .01 ($1.00) increments, but net
   package price must be in .05 ($5.00) increments", "except for Boxes and Box Swaps which are eligible to trade in .01
   ($1.00) increments"; the single-leg increments are Cboe Rule 5.4(a) for classes outside the Penny Interval Program.
3. **Stresses on the package**: credit_pkg − $0.05 and credit_pkg − $0.10 (one and two complex increments worse).
4. **The mid**, every leg at its mid, as a reference only — never used to pass.

The data hold no complex order book and no fills: whether a package would have filled at its NBBO is not measured.

**The 15:58 exit (beside the hold, every trade).** The legs' NBBO at 15:58 (the rows stamped 15:58). Legs: the tracker's
`close_row` rule — a short bought back at its ask, a long sold at its bid; a long with no bid (bid 0 or no quote) is left
to expire with no fee and settles at intrinsic on the official close; a short with no ask at 15:58 makes the exit
unavailable (counted, left out of the 15:58 statistics). Package: the cost to close = Σ short asks − Σ long bids, rounded
UP to the next $0.05, every leg closed; the package stresses add $0.05 and $0.10 to that cost (and the entry is the
matching stressed entry). The mid exit closes every leg at its mid. Fees on every contract closed (section 4).

## 4. Fees (the owner's answer: "$0.65 per contract commission plus the published Cboe SPX/SPXW exchange and regulatory fees, as a stated assumption, not a specific broker")

Per contract, on every contract at the open and on every contract closed at 15:58; nothing at cash settlement:

| item | figure | source (read 2026-10-22) |
|---|---|---|
| commission | $0.65 | the owner's stated assumption |
| Cboe customer transaction fee, SPX (incl SPXW), premium < $1.00 (fee code CS) | $0.36 | Cboe Exchange Fees Schedule, October 1, 2026 (https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf), Rate Table – Underlying Symbol List A, Customer (C): "SPX (incl SPXW) {CS} $0.36 … {CT} $0.45"; Cboe fee codes (https://www.cboe.com/us/options/membership/fee_schedule/cboe/, shown effective October 8, 2026): "CS: Customer, Premium <$1.00, SPX" 0.36 |
| the same, premium ≥ $1.00 (CT) | $0.45 | the same: "CT: Customer, Premium >= $1.00 or Premium Recalculated After Market Close, SPX" 0.45 |
| SPXW Execution Surcharge (electronic) | $0.14 | the same schedule, "Execution Surcharge (21)(12)(41) … SPXW (electronic only) $0.14", capacity codes C F J L B N U (customers included); SEC Release 34-93955 (SR-CBOE, eff. 2022-01-02) raised it from $0.13 for non-Market-Maker orders, customers included |
| Index License Surcharge | $0.00 for a customer | the same schedule: $0.10 for capacity codes F J L M B N U — not C |
| Options Regulatory Fee (ORF) | $0.01248 a contract side | the same schedule, Regulatory Fees: "Options Regulatory Fee ("ORF") … $0.01248 per contract side" (assessed on the clearing firm, customer range; SPXW trades only on Cboe) |
| OCC clearing fee | $0.025 a contract | OCC Schedule of Fees "All Transactions $0.025/contract" (SR-OCC-2025-002, SEC Release 34-102437, effective 2025-02-14, up from $0.02; SR-OCC-2025-019, SEC Release 34-104274: a $0 fee holiday for December 2025 only, the $0.025 back from the first trading day of 2026) |

So **$1.18748 a contract when the leg's premium is under $1.00 and $1.27748 at or above $1.00**. The premium tier of a leg is
its own fill price at the NBBO side it trades (a short's bid, a long's ask; at 15:58 the ask bought, the bid sold); a
package fill gives no leg prices, so the legs' NBBO-side prices set the tiers for the package fills and the stresses as
well. The schedule has no separate customer rate for complex orders in SPX/SPXW: every leg pays per contract. Today's
schedule is applied to every period (in 2022–2024 OCC's fee was $0.02 — a $0.005 a contract overstatement there). Not
included: FINRA's Trading Activity Fee and the SEC's Section 31 fee on sales (broker pass-throughs, cents per trade),
AIM, floor-broker and GTH surcharges (the orders are assumed electronic, regular hours), any broker exercise or
cash-settlement fee (the Cboe schedule charges none at settlement). A broker may add any of these or absorb some of the
exchange, ORF and OCC fees; the figures are a stated assumption, not a broker's bill. The ETF reports charged $0.65 a
contract and nothing else — the SPXW fees are about $2.15–2.51 a structure higher a side and are not comparable to them.

## 5. Settlement

- **Primary: the official SPX closing value** for the session, from Cboe's published SPX daily history
  (`data/official_closes/cboe_SPX_History_2026-10-22.csv`, 1975 → 2026-10-21, fetched 2026-10-22, $0), cross-checked on
  their overlap against the older copies `…/scratchpad/spx/cboe_spx.csv` (Cboe, fetched 2026-10-14) and `fred_sp500.csv`
  (FRED SP500, S&P Dow Jones Indices); every disagreement over $0.005 is listed. A session with no official close in the
  Cboe file is left out (listed). Each leg pays its intrinsic on that value; P&L = (credit + payoff) × 100 − opening fees.
- **Secondary, labelled "≤ 16:00 print"**: the last SPX print at or before 16:00 (`ParquetSource.prints`, j ≤ 390) — the
  research's proxy. Shown beside the primary, never used to pass.

## 6. Periods, and what each has already been read for

| period | sessions | what SPXW in this span has already been read for |
|---|---|---|
| development | 2022-05-13 → 2024-12-31 | the fit period of every SPXW hypothesis: hyp_a (SPXW credit spreads and iron condors at 15:00, 15:30, 15:45 — d10/d15/d20/d25 by "|delta| ≤ x", m1.00/m1.25 — wings 5/10/25, hold / tp50 / stop2x; its pre-registered pick was an SPXW 25-wide call spread at 15:30); hyp_b (SPXW 5- and 10-wide credit spreads at the straddle-boundary touch, at 14 scan minutes 09:35 → 15:50, and the midday iron condors at 11:30, 12:00, 12:30, 13:00 and 13:30 — d15/d20/d25/em1/half — "every rule negative in fit", the 5-wide CIs excluding zero); hyp_c (SPXW iron, call and put flies ±5/±10/±25 and the straddle-width wing at 15:00 and 15:30: "No SPXW cell has a fit interval above zero"); hyp_d and the Compass engine audit (SPXW naked contracts and debit structures, entries and exits) |
| selection | 2025-01-02 → 2026-10-09 | the OOS period of the same: hyp_a (its SPXW pick lost −$33 a spread; "Not one of the 1,458 SPXW cells read out of sample has a bootstrap CI clear of zero"); hyp_b (SPXW 10-wide condors +0.1 to +0.9 % of risk with CIs of ±$25–35, 5-wide condors negative in BOTH periods; "SPXW — no edge at these widths at the NBBO"); hyp_c ("SPXW negative at every wing both periods", ±25 iron −2.3 % at 15:00 and −1.1 % at 15:30); hyp_f (C's four-name pool, SPXW included, reproduced); the engine audit and hyp_d; and the replay's fly_spxw candidate (±5 and ±25 flies) run as a one-week sanity run 2026-10-05 → 09, outside the repository. The two ETF candidates whose analogues these are were chosen on this span (fly5's iron ±5 found post hoc on hyp_c's OOS; condor_d20 set after hyp_e's OOS read) |
| forward | 2026-10-12 → 2026-10-21 | fetched 2026-10-22; the ETF candidates' forward replay was read, its SPXW P&L never — no SPXW structure has been priced on these 8 sessions |

Neither analogue's exact cell was in any grid: the widest SPXW fly read was ±25 (here ±50), the widest SPXW condor 10 or 25
points (here 20 beside a 0.20-delta short at 13:00–15:00; hyp_b's midday condors overlap at 13:00 and 13:30, hyp_a's at
15:00). But their neighbours were read in both historical periods, and read negative or flat. **No SPXW period is untouched by
related structures except the forward one.** That implies: (1) the selection period is a selection period in name only for
SPXW — nothing was picked on it for SPXW, but its SPXW results were seen, and the ETF structures being transplanted were
chosen on it; a PASS on it is weaker evidence than a clean out-of-sample read, and a FAIL is consistent with what the
neighbouring cells already showed; (2) the forward period is the only untouched span and holds 8 sessions — too few for a
20-session block bootstrap or for any verdict; it is reported, never used to pass; (3) **the ETF results are not evidence
for SPXW**: a different instrument (cash, European, no assignment), different widths in strike steps, different quotes,
different fees, and a settlement the ETF reports measured differently.

## 7. The pass/fail rule, fixed now, per analogue

Statistic: for each session in the period, the session sum = the sum of the analogue's trades that day (iron fly: 15:00 +
15:30; condor: the five minutes), 0 when none was tradable; the period's mean session sum in dollars, one lot, held to
the official close. Interval: the percentile interval of the moving-block bootstrap over sessions in calendar order,
blocks of 20 sessions, 2,000 draws, seed 20261022 — `audit_lib.session_stats`' `ci_session_b20`, unchanged.

**PASS** only if ALL of:
1. in the **selection** period, at the **package-NBBO fill** (rounded against us to $0.05), with the section 4 fees and the
   official-close settlement, the mean session sum is > 0 **and** its 20-session block-bootstrap 95 % interval excludes zero
   (lower bound > 0);
2. in the selection period, the mean session sum stays > 0 at the **+$0.05 package stress**;
3. in the **development** period, the mean session sum at the package-NBBO fill (same fees and settlement) is > 0.

Otherwise **FAIL**. Applied mechanically to each analogue, separately; the two are not combined. The forward period is
reported and never used to pass. The legs-NBBO fill, the +$0.10 stress, the mid, the ≤ 16:00-print settlement and the
15:58 exit are reported beside it and change nothing in the verdict. **A PASS means "continue paper testing on SPXW",
never production.** A FAIL ends this test for the analogue; it is not to be rescued by another width, minute, fill or
filter read on these periods.

## 8. The report and the extrinsic study (same run)

Reported per analogue per period, never pooled (AUDIT.md's format): sessions, trades, sessions traded / run, untradable
reasons, mean $ a trade and a session, mean % of max risk, win share (trades), profit factor, max drawdown and worst session
on the session sums, the longest losing streak (sessions), the full-loss share (≤ −95 % of max risk), iid-session, 5- and
20-session block intervals, effective N; the legs-NBBO vs package-NBBO vs +$0.05 / +$0.10 vs mid; the official close vs the
≤ 16:00 print; the 15:58 exit under each fill; then the verdict.

**ATM extrinsic against the realized move.** At 15:00, 15:30 and 15:58, every full session in each period, for SPY, QQQ
(chains `data_full/chains/{SPY,QQQ}`, from 2022-11-11; spot the close of the bar stamped m − 1) and SPXW (spot the SPX
print at m): K = the strike nearest spot with both sides quoted (`Chain.nearest`); extrinsic = call mid + put mid −
|spot − K| (the ITM side's intrinsic), in bps of spot; realized = |official close − spot| in bps of spot (SPY and QQQ: the
official close as AUDIT.md took it, Theta's EOD bar, checked against UW's daily bar; SPX: the Cboe close). By name, minute
and period: the mean extrinsic, the mean realized, their ratio (mean extrinsic ÷ mean realized) and the mean difference
(extrinsic − realized, bps); the SPY − SPXW and QQQ − SPXW gaps in the ratio and in the difference on the sessions all
three share, with 20-session block-bootstrap intervals (the same draws for numerator and denominator). The owner's reading:
if SPY/QQQ late-day extrinsic is richer than SPXW's relative to the realized move, that gap is the assignment premium. It
is reported as a hypothesis the gap is consistent with or not — the gap also holds the ETFs' dividend and settlement
mechanics, the $1 vs $5 strike grids (how far the ATM strike sits from spot), the quote widths behind the mids, and the
SPY close's auction vs the index's component closes — not as a measurement of an assignment premium.

## 9. Code and outputs

`research_notes/Compass phase 3/spxw_prereg/` holds this file (committed alone, before the run), the run's script, its
50-structure verification, `out/` and `SPXW_REPORT.md` with this file's commit hash at its top and the exact commands.
`scripts/` and `tests/` are imported read-only, never edited. No vendor is called; no key or secret is read or written.
