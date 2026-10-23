# H6 — monthly short put spreads on SPY and QQQ at 30–45 days: a FORWARD-ONLY pre-registration

Written Thursday 2026-10-22, 22:50–23:59 New York, committed together with `PREREG_H5.md` and nothing else, and pushed
before any H6 quantity is computed on any session. **H6 is tested on forward entries only, from the first session of
November 2026 (Monday 2026-11-02)**. No historical H6 result is computed: the historical read of index put-writing on
these two names is spent (S17, 2012-06 → 2026-10, `research/compass/results/v1/s17_put_write/`, commit `5e7e1bd`;
its pre-registration, amendment A7, commit `c81522a`). The code is written after this file, in this folder, and wired
into the daily forward job (`scripts/daily_forward.py`) as part of its step 8; nothing here is changed after a forward
row exists.

The queue's definition (`research_notes/Edge search/QUEUE.md`, commit `a49c35b`), verbatim: "H6 — volatility risk premium
at 30–45 DTE: monthly short put spreads on SPY/QQQ (S17 read 2012–2026 put-writing and covered calls: forward-only)."
The queue's rules 1–6 apply.

**What was looked at to write this file** (all committed before it): QUEUE.md and LEDGER.md (`0418fa2`); S17's REPORT.md,
summary.json and cycles.parquet at `5e7e1bd` (read from git; already read when S17 reported) and `04_protocol.md`'s A7
at `c81522a`; FORWARD_RULE.md and `forward/forward_features.py`; PREREG_FEATURES.md section 2.6 (fees);
`scripts/daily_forward.py`, `scripts/paper_backtest.py` (ThetaFetch, FETCH_CHAINS), `scripts/paper_tracker.py`
(bsm_abs_delta, otm_deltas, nearest_delta); `research_notes/Edge search/H3/fetch_h3.py` (the SDK's end-of-day call);
`audit_lib.py`. **No H6 spread has been priced on any date.**

---

## 1. Hypothesis and mechanism

**H6.** Selling a SPY (and, separately, a QQQ) put spread — short the put nearest 0.30 delta, long the put nearest 0.15
delta, on the expiration 30–45 days out — at the close of the first session of each month, and buying it back at the
close of the first session 21 days before its expiration, makes money on average after crossing the spreads both ways
and fees.

**Mechanism.** The volatility risk premium: index options' implied variance exceeds the variance later realized on
average, most in out-of-the-money puts (the variance and skew premium Cboe's PUT and BXMD indexes collect). S17 found it
in the same names over 2012–2026 for the 0.30/0.15 put spread held to expiry: **+$50.8 a spread [−10.7, +106.5] on
SPY (166 cycles) and +$55.9 [−1.2, +105.2] on QQQ (167)**, cycle bootstrap — positive in 5 and 4 of 5 sub-periods,
with no alpha against the underlying and a crash-shaped left tail (worst cycle −89 % / −86 % of the width's capital).
H6 differs in three stated ways: it enters at 39–45 days instead of S17's 28–35, it exits three weeks before expiry
(at 21 days) instead of settling, and it pays the spread at the exit as well.

## 2. The trade (the rule, exactly)

**Names**: SPY and QQQ, one spread each a month, judged as one pool (section 4).

**Entry session D**: the first full NYSE session of each calendar month (the recorder's calendar, `eod_recorder`
HOLIDAYS / HALF_DAYS; `paper_tracker.is_tracked_day`), from November 2026 (2026-11-02, 2026-12-01, 2027-01-04, …).

**Quotes**: Theta Data's end-of-day option report for the session (its closing bid and ask for every listed contract, as
the vendor reports them — after SPY's and QQQ's options stop trading at 16:15), fetched by the job's step 8 (section 5).
A contract's quote stands when bid ≥ 0, ask > 0 and ask ≥ bid (a 0/0 quote is no quote). **Spot** = the name's official
close of the session (the job's step 4: UW's daily bar, else Theta's end-of-day; never a 15:59 bar).

**Expiration E**: among the expirations in the session's end-of-day answer with 30 ≤ (E − D) ≤ 45 calendar days, the
latest. (SPY and QQQ list a Friday expiration every week at that range, so E is 39–45 days out.) None in 30–45 → no trade
that month for that name (a final row with its reason).

**Strikes** (puts of E only): |Δ| of each out-of-the-money put by `paper_tracker.bsm_abs_delta` — the European total
volatility solved from the put's own end-of-day mid at r = q = 0 on the official close, |Δ| = 1 − N(d1); the puts taken
are those of `otm_deltas` (K < spot, mid > 0, ask > 0, mid < K). **Short K_s = the put whose |Δ| is nearest 0.30; long
K_l = the put whose |Δ| is nearest 0.15** (`nearest_delta`; a tie goes to the lower strike). K_l ≥ K_s → no trade (a final
row with the reason).

**Entry fill**: SELL 1 K_s put at its BID, BUY 1 K_l put at its ASK. Credit c = bid(K_s) − ask(K_l). No trade (a final row)
when bid(K_s) = 0 or c ≤ 0.

**Exit session X**: the first full session on or after E − 21 calendar days (a half day or a holiday moves it to the next
full session). **Exit fill** on X's end-of-day report for E: BUY BACK K_s at its ASK, SELL K_l at its BID (a long put quoted
0 bid is sold for 0). Debit d = ask(K_s) − bid(K_l). Nothing is held to expiration.

**A missing exit quote** (no two-sided quote for the leg on X, the answer otherwise whole) is never skipped and never taken
from another day: K_s is valued at its intrinsic on X's official close plus its own entry spread (ask − bid at D); K_l at
max(0, intrinsic − its entry spread). The row is flagged (H3's rule, `PREREG_H3.md`). A missing answer, a failed call or a
missing official close is a data failure: the job fails loudly and writes nothing (section 5).

**P&L of a spread, $** = 100 × (c − d) − 4 × **$0.68748** (two contracts in, two out; PREREG_FEATURES.md section 2.6:
$0.65 commission + ORF $0.01248 + OCC $0.025). Logged beside it, for reading: the width K_s − K_l, the risk
100 × (K_s − K_l − c), both legs' quotes and |Δ| at entry, the spot at entry and exit, and whether the short put's exit bid
stood below its intrinsic value (a marker of early-exercise exposure).

## 3. Not modelled, said

- **Early assignment.** The short put is American; when it is deep in the money its holder may exercise before X. The test
  books the rule's quoted exit regardless; the flag above marks the trades exposed. A put spread is defined-risk only
  while both legs are held.
- **The account.** A put spread needs a margin account (or a broker that allows defined-risk spreads against cash equal to
  the risk); the risk 100 × (width − credit) is logged.
- The quote time (the end-of-day report's closing quote, after 16:00) against a 16:00 official close; fills at the NBBO for
  one spread; dividends (SPY's and QQQ's quarterly ex-dates are in the quotes, not adjusted).

## 4. The statistic, the interval, and the pass rule

- **The unit is the entry month** (calendar order from November 2026). For month m: S_m = the sum of that month's closed
  spreads' P&L in dollars over SPY and QQQ, N_m = the number of spreads traded (0, 1 or 2).
- **Δ = Σ S_m ÷ Σ N_m over the counted months = the mean dollars per spread after all costs**, SPY and QQQ pooled (the
  queue's rule 4: a pre-stated pool). The per-name means are printed beside it, with no verdict of their own.
- **The interval: a moving-block bootstrap with blocks of 3 consecutive counted months** — `audit_lib.block_draws(n, 3)`
  (2,000 draws, `audit_lib.SEED` = 20261022, its generator seeded 20261022 + 7919 × 3; both names of a month always
  together), the percentile 95 % interval (`audit_lib.pct_ci`) of Σ S_b ÷ Σ N_b. None is printed under 12 months.
- **PASS at exactly N counted months, on the first N only: Δ > 0 and the interval's lower end > 0.** Otherwise FAIL. The
  verdict is written once and never revised; months after N are logged and do not change it.
- **No verdict before N**: interim figures only, labelled "no verdict"; no early stop, no extension, no change of N, rule,
  names, deltas, days, costs or statistic once a forward row exists.

## 5. Data, and counting

**The daily forward job does not fetch end-of-day option chains** (it fetches the same-day 1-minute chains of SPY, QQQ and
SPXW). Step 8 adds the minimal fetch H6 needs, through the job's own `--source`: on an entry session one call a name for
every expiration (the terminal's `/option/history/eod` with `expiration=*`, `start_date` = `end_date` = D; the SDK's
`option_history_eod` with the same arguments), on an exit session one call a name for E alone — **at most four calls a
month**, kept as answered under the Parquet root (`edge_forward/eod/<NAME>/<D>__<ALL|E>.parquet`) and never asked twice.
If the source does not serve that route, step 8 fails loudly and H6 is registered but not collectable until it does —
no other source is substituted.

**A month counts** when both names' outcomes for it are final: a closed spread (its exit priced) or a no-trade row from the
entry rule. An entry or exit session whose data fail is retried on the next run and is never replaced by another session
or source. Months are counted in calendar order.

## 6. N, and its basis

**N = 449 counted months — 898 spreads, about 37.4 years.** **No verdict is reachable in any useful time**; the test is
kept in the job and logged, as FORWARD_RULE.md keeps V1 (whose N is likewise out of reach). This is said plainly here,
before any forward row: a reader should expect H6 to stay "no verdict" for decades, and a forward pass of a smaller,
unregistered N would not be one.

The effect and the variance come from S17's committed per-cycle rows (`cycles.parquet` at `5e7e1bd`, structure
`put_spread_30_15`, no adverse tick), in **return on the spread's capital** (`ret` = P&L ÷ (width × 100), so 2012's $60
QQQ and 2026's $600 QQQ are on one scale; the dollar statistic of section 4 is the same quantity at a forward price level
that moves little over a few years):

1. **The pooled month** (the mean of SPY's and QQQ's `ret` on the 166 entry dates both hold): mean **μ = 0.04491**, standard
   deviation **0.26693**; the 3-cycle moving-block bootstrap's standard error × √n = 0.26006 (no inflation over iid, so the
   larger, 0.26693, is used). SPY and QQQ's cycle returns correlate 0.827.
2. **The mapping to H6's holding.** S17 held 31.2 days on average (entry to expiry); H6 holds about 21 (from 39–45 days to
   21). The premium is taken to accrue and the variance to grow in proportion to the time held: f = 21 ÷ 31.195 = 0.6732,
   **δ = f × μ − the exit's extra cost** and **σ = √f × 0.26693 = 0.21901**. The exit's extra cost (S17 settled at intrinsic;
   H6 buys back): about $3 a spread in half-spreads (two legs, about $0.01–0.02 a share each), on the spread's capital at
   S17's 2025–2026 level, $2,411: 0.00124. So **δ = 0.02899 of capital a spread (≈ +$70 at that capital), σ = 0.21901
   (≈ $528)**. A longer tenor widens the strikes for the same deltas, which scales δ and σ alike and cancels in the ratio.
3. **N0 = ⌈((1.959964 + 0.841621) × σ ÷ δ)²⌉ = ⌈(2.801585 × 0.21901 ÷ 0.02899)²⌉ = 449 months**, at least 12 (not
   binding). The normal approximation is used; the block bootstrap of S17's months shows no autocorrelation to add.

**Sensitivity (N, months)**: δ at 0.5× / 0.75× / 1× / 1.5× of the mapped value: 1,793 / 797 / **449** / 200; with S17's
unscaled month (μ = 0.04491, σ = 0.26693, no holding or exit adjustment): 278. Every one is decades.

**Uncertainty, stated**: the proportional mapping of premium and variance to the time held is an assumption (theta and
gamma are not uniform over a spread's life); S17's cycles are monthly-expiration to monthly-expiration, not first-of-month;
its fees were $0.70 a contract four times a spread (its fills, the short at the closing bid and the long at the closing ask,
are H6's entry); its 14 years
include 2020 and 2022, whose drawdowns a forward window may or may not see.

## 7. Where it is written

`research_notes/Edge search/H5_H6/forward/h6_entries.csv` (one row a name a month at entry: the expiration, strikes,
quotes, credit, planned exit session, or the no-trade reason) and `forward/h6_trades.csv` (one row a closed spread), both
append-only; the report `forward/EDGE_FORWARD_REPORT.md` (rewritten each run); the verdict, once N is reached, in
`forward/verdicts.json` (written once). LEDGER.md gets one row: "registered, forward — no verdict before N = 449 months
(898 spreads)".
