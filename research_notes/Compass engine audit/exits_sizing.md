# Compass Modules 3 and 4: sizing, budget, exits and the ledger circuit breakers

Scope: the 0DTE exit stack (premium backstop, structural stop, T1/T2 targets, breakeven lock, VIX-tiered trail, time stop, hard flat), the sizing cap, the rolling-30 profit-factor breaker, and the Weekly/Swing/LEAPS premium stops. Every number below is computed by a script in `research_notes/Compass engine audit/exits_sizing/` (paths relative to the repo) from the local ThetaData parquet files; no API was called. The web pass is short and marked as such.

**Method, in one paragraph.** `extract.py` builds two 0DTE entry universes on SPY, QQQ, IWM and SPXW and stores every trade's full minute path (bid, ask, bid_size, ask_size, spot, bar high/low, VIX at entry). Universe A (sweep fade): the first 1-minute bar stamped 10:00–11:59 NY whose high is ≥ 2 bps above the 09:30–09:59 range high and whose close is back below it → buy the nearest out-of-the-money same-day put at the ask on that close (mirror for the range low → call), one event a session per side. Universe B: one random quote minute a session in [10:00, 15:00] (seed 20261016), call or put at random, nearest OTM at the ask. SPXW uses the SPX print for spot and strike choice and SPY bars × the 10:00 SPX/SPY ratio as a stated proxy for bar highs/lows. `engine.py` replays every exit rule on the stored paths: minute m = 0 is 09:30; the bar stamped t closes at t+1; a stop, trail, time stop or hard flat sells at the **bid** of the minute it first triggers (a bid that gaps through a stop sells at the gapped bid); a target fills at the target price (a resting limit); hard flat at 15:58 (m = 388; 208 on a half day); settle = intrinsic at the closing spot; fees $0.65 a contract each way, none on a contract held to settlement. Only one-minute NBBO exists on disk, so "every bid tick" is "every minute's bid" — intra-minute paths are unobserved (stated as a limit below). Split: pick on 2022–2024 ("disc"), read on 2025–2026 ("check"). Stress: bootstrap by session (1,000 draws), without the best 5 sessions, by year. `verify.py` re-derived 80 random trades' entries, settles, peak bids and four exit rules from the raw files with plain-loop code: 80 of 80 agree (after one real bug was found and fixed — the paths were stored as float32, so a bid of exactly 1.05 read back as 1.04999995 and missed a 1.05 threshold; prices are now rounded to 4 decimals on load). `contrasts.py` gives paired per-trade differences between rules with a session-bootstrap 95% interval, which is the test behind every "change to X" verdict.

| Universe | Trades | 2022–24 | 2025–26 | Sessions | SPY / QQQ / IWM / SPXW | Median entry ask | Median spread / ask |
|---|---|---|---|---|---|---|---|
| A sweep fade | 3,433 | 1,826 | 1,607 | 1,034 | 890 / 949 / 573 / 1,021 | $1.25 | 1.4% |
| B random minute | 3,672 | 1,900 | 1,772 | 1,105 | 977 / 975 / 617 / 1,103 | $0.90 | 2.0% |

(IWM from 2024-04-19, SPXW from 2022-05-13, SPY/QQQ from 2022-11-11, all to 2026-10-09. `out/summary.json`.) In both universes the bid reached +6% at some point after entry in 83% of trades, +25% in 67%, +50% in 53% — and holding to 15:58 with no exit lost 12–20% of the debit a trade. Everything that follows is about which exit loses least; **no exit configuration turned either entry universe positive in either period**, which matches steps 3–5 of this repo.

**The spec stack as written, replayed** (`run_tests.py` → `out/t0_spec_stack_{A,B}.csv`; "spec 1c" = −32% backstop, structural stop at the swept level + 2 bps (universe B: entry spot ± 15 bps), breakeven lock at +6%, VIX-tiered trail active once the bid has been +6%, 5-minute time stop if no +6%, hard flat 15:58, one contract sold at T1 +25%; "3c" = 1 contract at +25%, 1 at +50%, 1 trailed):

| | 2022–24 EV | 2025–26 EV | win rate | avg win | avg loss | bootstrap 95% | without best 5 days | days up | 2025 / 2026 |
|---|---|---|---|---|---|---|---|---|---|
| A, spec 1c | −4.3% | −4.5% | 25.6% | +14.7% | −11.2% | −5.4% to −3.6% | −5.0% | 100 of 429 | −4.1% / −5.1% |
| A, spec 3c | −3.7% | −3.9% | 25.5% | +17.5% | −11.5% | −5.0% to −2.7% | −4.5% | 110 of 429 | −3.3% / −4.6% |
| B, spec 1c | −6.3% | −6.0% | 31.4% | +16.3% | −16.3% | −7.0% to −5.0% | −6.4% | 123 of 444 | −6.1% / −6.0% |
| B, spec 3c | −5.7% | −5.0% | 31.3% | +19.7% | −16.2% | −6.0% to −3.9% | −5.5% | 133 of 444 | −5.0% / −5.0% |

EV is per contract in % of the debit after fees; dollars per contract in the CSVs. Per product (`out/by_product.csv`, 2025–26, spec 1c): A SPY −3.7%, QQQ −3.5%, IWM −7.6%, SPXW −3.2%; B SPY −3.4%, QQQ −4.5%, IWM −13.6%, SPXW −2.8%. Every bootstrap interval is below zero.

## Audit task (a) and test 1: the −32% premium backstop, the −15.2% arithmetic, and the structural stop

### Takeaway
The ledger's debitPercent 5.83% / lossPercent 0.886% = −15.2% is the **average realised loss on losing trades across every exit that produced a loss**, not a stop level: in the replayed spec stack the −32% backstop is the exit on only 0.7% (A) to 6.3% (B) of trades, and the average losing trade is −10.5% to −16.3% because the structural stop, the breakeven lock and the time stop take the losses out first. The backstop level is irrelevant inside the stack (−15%, −20%, −25%, −32%, −50% give the same EV to the second decimal). As a stand-alone rule a −32% premium stop is at least as good as −15%/−20% in the out-of-sample period, and the structural stop at the level itself fires on 86–96% of sweep-fade trades.

### Cited Findings
- Exit mix of the spec stack, universe A (share of trades, average result): structural stop 58.8% (−11.3%), target 13.2% (+23.8%), breakeven lock 11.9% (−4.7%), trail 8.0% (+4.2%), time stop 7.4% (−5.7%), premium backstop **0.7%** (−38.2%). Of the losing trades: structural 73.5% at −12.4%, lock 15.9% at −4.7%, time 8.3% at −7.2%, backstop 1.0% at −38.2%. Average losing trade −10.5% (2022–24), −11.2% (2025–26). — `out/t0_spec_stack_A.csv`
- Universe B: time stop 43.2% (−13.0%), lock 18.2% (−6.5%), target 17.4% (+23.0%), trail 9.7% (+3.8%), backstop **6.3%** (−43.3%), structural 5.1% (−21.9%). Losing trades: time 55.9% at −14.5%, lock 25.8% at −6.5%, backstop 8.9% at −43.3%, structural 7.1% at −22.6%. Average losing trade −14.3% / −16.3%. — `out/t0_spec_stack_B.csv`
- Average losing trade by product in 2025–26 (spec 1c): A SPY −10.5%, QQQ −9.9%, IWM −13.8%, SPXW −10.2%; B SPY −14.0%, QQQ −14.0%, IWM −22.7%, SPXW −13.4%. — `out/by_product.csv`
- The backstop level inside the full stack changes nothing: A 2025–26 EV −4.5% at −15%, −20%, −25%, −32% and −50% alike (win rate 25.5–25.6%); B −6.0% to −6.2%. Paired −20% vs −32% inside the stack: +0.05% [−0.01%, +0.11%] (A), −0.12% [−0.38%, +0.12%] (B). — `out/t1_stops_in_stack_{A,B}.csv`, `out/contrasts.csv`
- Stand-alone premium stops with a hard flat and nothing else (EV 2022–24 / 2025–26; realised average loss on the stop exits; share of stop exits more than 5 points beyond the level; share that fired within 3 minutes of entry): universe A — none −19.7% / −12.2%; −15%: −5.8% / −4.5%, realised −19.6%, 34% beyond, **25.5% within 3 minutes**; −20%: −7.6% / −4.6%, realised −24.3%, 32%, 14.1%; −25%: −7.5% / −5.3%, realised −29.2%, 31%, 7.5%; −32%: −7.4% / **−2.6%**, realised −35.8% (p10 −40%), 26%, 2.4%; −50%: −9.8% / −5.9%, realised −52.6%. Universe B — −15%: −5.9% / −2.3%; −20%: −5.8% / −3.0%; −25%: −8.0% / −1.7%; −32%: −7.6% / **−0.6%**, realised −36.6%, 33% beyond; −50%: −10.0% / −2.5%. — `out/t1_stops_{A,B}.csv`
- Paired, flat base: −20% vs −32%: A −0.2% [−4.6%, +3.8%] in 2022–24, −1.9% [−7.8%, +2.6%] in 2025–26; B +1.8% [−0.9%, +4.5%] then −2.4% [−6.0%, +0.7%]. −50% vs −32%: A −2.5% [−5.6%, +1.1%] then −3.3% [−6.6%, +0.5%] (−5.9% without the 5 days that favour −50% most); B −2.4% then −1.9%. — `out/contrasts.csv`
- Structural stop alone (universe A, the underlying trading back through the swept level, judged on bar highs/lows): at the level + 0 bps it fires on 95.8% of trades, realised −9.4% (p10 −21.9%), EV −3.7% / −2.1%; + 2 bps: 93.7%, −14.7% (p10 −29.2%), −6.0% / −3.8%; + 5 bps: 90.1%, −22.4%, −8.2% / −3.5%. Universe B (entry spot moved 10/15/20 bps against the trade): fires on 77% / 66% / 56%, realised −38% / −49% / −56%, EV −9.7% / −8.7% / −9.4% then −3.0% / −3.7% / −3.5%. — `out/t1_stops_{A,B}.csv`
- Structural stop vs none inside the spec stack (paired): A −0.05% [−0.7%, +0.6%] then +0.6% [−0.0%, +1.2%]; B +0.1% then +0.02%. — `out/contrasts.csv`
- Practitioner view (opinion, not a backtest): stops on a speculative long option should be placed on the stock price, not the option price, because the option is "a derivative security, and often a relatively illiquid one". — [McMillan, Option Strategist](https://optionstrategist.com/node/6081)
- Stocks, 1970–2005, random buy dates (NYSE/AMEX): fixed and trailing stop-loss returns "statistically indistinguishable from buy-and-hold"; trailing stops reduced return volatility; transaction costs not addressed. — [Lei & Li 2008 via CXO Advisory](https://www.cxoadvisory.com/technical-trading/using-trailing-stop-losses-to-reduce-risk)

### Inferences
- **Resolution of −15.2%.** 0.886 / 5.83 = 0.152. If lossPercent is the average over losing trades, the ledger's −15.2% sits exactly where the replayed stack puts it (−10.5% to −16.3% by universe, −10% to −23% by product): a mix of structural (−12%), lock (−5 to −7%) and time (−6 to −14%) exits with the backstop touched on about 1–6% of trades at −38 to −43% realised. If instead lossPercent is the average over *all* trades, −15.2% of the debit is simply a negative-EV engine. Under neither reading is there a hidden −15% stop, and the stack's figures do not need a tighter backstop to be reproduced.
- **A −15% to −20% underlying-triggered stop does not outperform the −32% premium stop on 0DTE.** As stand-alone rules, −32% is the best premium level in 2025–26 in both universes and the paired differences against −20% are negative out of sample with intervals that include zero; the tighter the premium stop, the larger the share that fires within three minutes of entry on bid-ask noise (25% at −15% vs 2% at −32%) and the larger the realised overshoot (every level realises 3–5 points worse than its nominal because the first bid at or below the level is already past it). Inside the stack the question is moot: the backstop is a tail guard that fires on ≤ 6% of trades.
- **The structural stop is the stack's main loser-maker, and it is also what makes the spec's average loss small.** At 0–5 bps past the swept level it fires on 90–96% of sweep-fade trades, i.e. the underlying re-tests the level almost always; it converts a −37% average premium-stop loss into a −9% to −22% average loss. It does not change EV materially (paired ±0.6% inside the stack), because what it saves on losers it gives up on winners that were re-tested first.
- Verdicts: **−32% backstop: keep** (never widened; it is nearly inert inside the stack and the best stand-alone level OOS). **Structural stop: keep, with the buffer at 0–2 bps** (the 5 bps buffer is worse in 2022–24 and no better in 2025–26); the choice is about the loss distribution, not EV. **No replacement rule**: no stop variant improves friction-adjusted EV on 2025–26 with a confidence interval clear of zero.

### Gaps
- Intra-minute ticks are not on disk; a stop that is "checked on every bid tick" would fire earlier within the minute, at a bid between the previous minute's and the recorded one. The realised-overshoot figures are therefore an upper bound on gap-through for a tick-watching engine and a lower bound on the number of triggers.
- The SPXW structural level uses SPY bars × the 10:00 ratio as the index's bar high/low; SPX prints are one price a minute. SPXW results for the structural stop are a proxy.

## Audit task (b) and test 2: the +6% high-bid breakeven lock

### Takeaway
The +6% lock is set on 83% of trades and hit on 47% of those when a +25% target is on (78% with no target); of the trades it sells, 63–66% go on to touch +25% later and 51–55% +45%. That "choke" is real but it is not a bid-ask-bounce artefact and raising the threshold does not reduce it (+12%: 63–65% still choked, EV 1% worse). With a target in the rule the lock at +6% beats no lock by +2.0% (A) / +1.0% (B) of debit in 2025–26 with paired intervals clear of zero, and a +0% lock (stop to entry as soon as the bid is at the ask) beats +6% by a further +1%; without a target the lock's sign flips between periods.

### Cited Findings
- Lock set / hit / choke (same in both universes within a point): at +6% the lock is set on 83.5% of trades (the bid reached +6%); with the −32% stop and a flat only, 77.6% of those are then sold at or below the entry ask; with a +25% target on, 46.8%. Of the lock exits, 64.2% (A) / 64.7% (B) would have gone on to +25% before 15:58 and 51.5% / 51.8% to +45%. Lock exits average −5.6% to −7.2% (the bid at or just below the entry ask, less fees). — `out/t2_belock_{A,B}.csv`
- Threshold grid, T1 +25% all-out with −32% stop, EV 2022–24 / 2025–26, universe A: none −8.6% / −8.5%; +0% −5.1% / −5.6%; +3% −5.6% / −6.3%; +6% −6.3% / −6.6%; +9% −6.6% / −7.2%; +12% −7.3% / −7.7%; +15% −8.0% / −8.2%; +20% −8.4% / −8.3%. Universe B: none −10.0% / −8.3%; +0% −7.2% / −7.0%; +6% −8.2% / −7.3%; +12% −8.9% / −7.9%; +20% −10.0% / −8.3%. Choke share of lock hits by threshold: 62.5% at +0%, 63.2% at +6%, 63.4% at +12%, 67.6% at +20% (A); the lock-set share falls from 90% to 71% over the same range. — `out/t2_belock_{A,B}.csv`
- Counterfactual on the trades the +6% lock sold (T1 base): with the lock they realised −5.6% (A) / −6.7% (B); the same trades under the identical rule without the lock realised −11.2% / −10.4% (win rate 42% / 45%): the 64% that went on to +25% collected +25%, the rest fell to the −32% stop or settled. — `out/t2_belock_{A,B}.csv` (`lock_hits_if_no_lock_pct`)
- Paired contrasts (2022–24; 2025–26): lock +6% vs none, T1 base: A +2.4% [+1.2%, +3.4%]; +2.0% [+0.7%, +3.3%], +1.5% without the 5 best days; B +1.8% [+1.0%, +2.7%]; +1.0% [+0.07%, +1.9%]. Lock +12% vs +6%: A −1.0% [−1.7%, −0.4%]; −1.2% [−1.9%, −0.4%]; B −0.7% [−1.3%, −0.2%]; −0.6% [−1.2%, −0.0%]. Lock +0% vs +6%: A +1.1% [+0.5%, +1.9%]; +1.0% [+0.1%, +1.8%]; B +1.0% [+0.4%, +1.6%]; +0.3% [−0.2%, +0.9%]. Lock +6% vs none with **no target**: A +4.1% [−0.7%, +8.6%] then −2.0% [−9.3%, +4.0%]; B +3.8% then −1.9%. — `out/contrasts.csv`
- Entry spread: median 1.4% of the ask (A), 2.0% (B); the contracts are $1.25 / $0.90 at the median, not $2.20. — `out/summary.json`
- Microstructure background: transaction prices bounce between bid and ask, inducing negative autocorrelation in transaction-price returns even on a random-walk efficient price (Roll 1984), through the magnitude of price changes rather than their direction. — [arXiv 2606.29591](https://arxiv.org/pdf/2606.29591); options stops are unreliable except in the most liquid contracts and the opening and closing minutes have "especially variable and jumpy bids and asks" (practitioner FAQ, not peer-reviewed). — [r/options wiki](https://r.datuan.dev/r/options/wiki/faq/pages/stop_loss)

### Inferences
- **Does the +6% lock choke winners through bid-ask bounce?** The choke is real (about two in three lock exits would have reached +25%), but it is not a bounce effect: with a 1.4–2% spread a bid that has been +6% and comes back to the entry ask has moved 6% against the trade, three to four spreads, and the choke share is flat from +0% to +12% (62–63%) — a higher threshold only sets the lock on fewer trades and sells fewer of them; it does not sell *better* ones. 0DTE premiums retrace through entry on the way to +25% in two thirds of cases regardless of how much progress was first banked.
- **Which activation threshold does best?** With a target in the rule, lower is better monotonically: +0% > +3% > +6% > … > +20% in both periods and both universes, and the paired +0%-vs-+6% gain is +1.0% [+0.1%, +1.8%] in 2025–26 on A (B +0.3%, interval touching zero). The owner's two candidates: **+6% beats +12%** by about 1% of debit out of sample with intervals clear of zero. The lock is, in effect, a tighter stop; it helps a rule whose upside is capped by a +25% target (where cutting a −32% loser to −6% is the whole game) and does nothing reliable for an uncapped rule (sign flips between periods).
- Verdict: **keep the lock when a T1 target is on; change the activation from +6% to +0% only if the engine's T1 is kept** (the +0% rule is: once the bid has traded at or above the entry ask, sell at the first bid at or below the entry ask). Under the house rule of falsifiable improvement, the +6%→+0% change passes on universe A (OOS +1.0%, interval clear of zero, +0.6% without the best 5 days) and is positive but not clear of zero on B (+0.3%); +6%→+12% fails. Everything here is a smaller loss, not a profit.

### Gaps
- The lock is judged on the minute's bid. A tick-level lock would be hit more often (any one-tick print at the entry ask triggers it); the choke rate would, if anything, rise.
- The ledger's ~$2.20 options are richer than this universe's median $1.25 / $0.90 (nearest OTM). The spread-as-share-of-ask is lower on a $2.20 option, which makes the bounce explanation weaker, not stronger.

## Test 3: the VIX-tiered trailing stop

### Takeaway
A trailing stop keyed to VIX (6/8/11/14%) is indistinguishable from a flat 6% or 10% trail from the peak: paired differences are within ±0.3% of debit with intervals straddling zero in both periods and both universes, and within each VIX tier the tier's own rate never beats the best flat rate in both periods. A trail of any kind vs no trail flips sign between 2022–24 and 2025–26.

### Cited Findings
- Trail active once the bid has been +6% (with the −32% stop and a hard flat), EV 2022–24 / 2025–26, universe A: none −7.4% / −2.6%; VIX-tiered −4.2% / −4.3% (win rate 39%); flat 6% −4.4% / −4.0%; 10% −4.3% / −4.0%; 20% −4.9% / −5.0%; 30% −5.1% / −6.4%; 50% −5.3% / −5.3%. Universe B: none −7.6% / −0.6%; VIX −5.5% / −3.8%; 6% −5.7% / −3.7%; 10% −5.6% / −3.7%; 20% −5.7% / −3.4%; 30% −4.3% / −4.4%; 50% −5.3% / −1.4%. Trails active from entry (peak = highest bid since entry, no activation): A VIX −3.5% / −3.9%, 10% −3.6% / −3.7%; B VIX −5.1% / −4.1%. — `out/t3_trail_{A,B}.csv`
- By VIX tier at entry (2025–26, A; n per tier 102 / 1,056 / 395 / 54): VIX < 15: tiered 6% −9.5%, flat 10% −7.9%; 15–20: tiered 8% −4.6%, flat 10% −4.5%, flat 20% −4.3%; 20–30: tiered 11% −2.2%, flat 6% −1.6%, flat 10% −2.1%; > 30: tiered 14% −3.3%, flat 6% +0.8%. Universe B shows the same pattern (20–30: tiered −0.4%, flat 6% +0.2%, flat 20% +1.7%; > 30, n = 49: tiered +2.6%, flat 20% +14.7%). — `out/t3_trail_{A,B}.csv`
- Paired: VIX-tiered vs flat 10%: A −0.05% [−0.7%, +0.7%] then +0.3% [−0.2%, +0.9%]; B −0.1% then +0.1%. VIX-tiered vs flat 6%: A −0.2% then +0.3%; B −0.2% then +0.1% (all intervals include zero). VIX trail vs no trail: A +3.2% [−3.3%, +9.3%] then −1.7% [−9.8%, +5.6%]; B +2.1% then −3.2%. — `out/contrasts.csv`
- Spec 1c stack vs "−32% stop + flat 10% trail from +6%": A −0.06% [−1.6%, +1.5%] then −0.6% [−2.3%, +1.2%]; B −0.8% then **−2.3% [−3.8%, −0.9%]** — the whole stack is no better than a stop plus a flat trail, and worse on universe B out of sample. — `out/contrasts.csv`
- Literature: trailing stops reduce return volatility but not returns in stocks (Lei & Li 2008); McMillan prefers trailing stops to targets "because that is the way that one can let his profits run" (opinion). — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/using-trailing-stop-losses-to-reduce-risk), [Option Strategist](https://optionstrategist.com/node/6081)

### Inferences
- The VIX tiers are an invented weight with no measurable effect: the trail's result is driven by the activation and by whether a trail exists at all, not by 6% vs 11%. Within tiers the direction of the evidence is, if anything, that a *tighter* trail does better when VIX is high (6% beats 11–14% in the 20–30 and > 30 tiers in 2025–26), the opposite of the spec's widening.
- A trail vs no trail is a loss-distribution choice (win rate 39% vs 13%, average loss −22% vs −37%) that does not change EV reliably.
- Verdict: **change to a flat trail** (10% from the peak, active once the bid has been +6%) — not because it is better, but because the VIX tiers are an unsupported parameter; the paired difference is zero within noise, so this is a simplification with no EV claim. If a trail is kept at all; "no trail" was better in 2025–26 and worse in 2022–24 in both universes.

### Gaps
- VIX > 30 tiers hold 28–54 trades; nothing can be said about them.

## Test 4: the 5-minute time stop

### Takeaway
"Exit at 5 minutes if the bid has not been +6%" fires on 47% of trades in both universes (a +6% bid within five minutes is rare), sells them at −13%, and the same trades held under the −32% stop would have averaged −12% to −13%: a wash. 10, 15, 30 minutes and a "structural progress" variant (spot 5 bps in favour) are the same within noise.

### Cited Findings
- With the −32% stop and a hard flat, EV 2022–24 / 2025–26, universe A: no time stop −7.4% / −2.6%; 5 min −8.7% / −1.3% (fires 47.0%, time exits −13.2%, those trades held −13.1%); 5 min with spot-progress waiver −8.5% / −0.1% (43.7%); 10 min −9.0% / −1.6% (26.7%); 15 min −8.7% / −1.7% (16.4%); 30 min −8.0% / −2.7% (4.4%); 60 min −7.6% / −2.4% (1.0%). Universe B: none −7.6% / −0.6%; 5 min −7.1% / −2.6% (46.7%, exits −13.5%, held −12.1%); 10 min −8.4% / −0.5%; 15 min −7.1% / −0.0%; 30 min −7.4% / −0.4%. — `out/t4_timestop_{A,B}.csv`
- Paired 5 min vs none: A −1.3% [−6.4%, +3.3%] then +1.3% [−2.1%, +4.4%]; B +0.6% [−2.8%, +3.7%] then −2.0% [−6.1%, +1.4%]. 15 vs 5 min: A −0.03% then −0.4%; B −0.06% then +2.6% [−0.8%, +6.6%]. — `out/contrasts.csv`
- In the spec stack the time stop is the exit on 7.4% of universe-A trades (the structural stop usually fires first) and on 43.2% of universe-B trades, where it is the largest single source of losses (56% of losers, −14.5%). — `out/t0_spec_stack_{A,B}.csv`

### Inferences
- The time stop is a loss-sizing device (it turns −32% losers into −13% losers and −25% winners into −13% losers at about the same rate), not an edge. No window between 5 and 60 minutes is distinguishable from none.
- Verdict: **untestable as an improvement; keep or drop at the owner's taste.** If kept, 5 minutes is as good as any; there is no case for a change.

### Gaps
- "Structural progress" is not defined in the spec; the test used "spot moved 5 bps in the trade's favour at any minute before the window ends". A different definition would move the 47% fire rate but, given the grid, not the verdict.

## Test 5: targets T1 +25%, T2 +45–50%, and the scale-out with 2, 3, 4 contracts

### Takeaway
+25% is touched on 67% of trades before 15:58 but on only 46–49% before the −32% stop; an all-out +25% target needs a 61–63% win rate to break even against its −37% average loss and gets 46–49%, so it loses 8–10% of debit in both periods and both universes and is worse than no target out of sample (B: −7.7% [−14.2%, −2.0%]). A scale-out that keeps a trailed leg (3c, 4c) beats the 1-contract T1 exit by +0.7% to +1.0% of debit with intervals clear of zero — a real but small difference between two losing rules. Target fills are realistic at these sizes.

### Cited Findings
- Hit rates (2022–24 / 2025–26, universe A; B within 2 points): +25% before 15:58 66.9% / 66.6%, before the −32% stop 46.4% / 46.8%; +45%: 55.2% / 55.5% and 35.3% / 35.3%; +50%: 52.5% / 53.6% and 32.3% / 33.7%; +100%: 34.3% / 36.8% and 19.9% / 21.5%. — `out/t5_target_hits_{A,B}.csv`
- All-out with the −32% stop, 2025–26 (A): +25% EV −8.5%, win 46.8%, avg win +23.8%, avg loss −37.0%, break-even win rate 60.8%; +45% −8.4%, win 35.3%, break-even 45.7%; +50% −8.0%, break-even 43.1%; +100% −7.6%, win 21.7%, break-even 27.3%; no target −2.6%, win 12.7%, avg win +234%, break-even 13.7%. B: +25% −8.3% (break-even 62.8% vs 49.4% actual); no target −0.6%. — `out/t5_scaleout_{A,B}.csv`
- Scale-outs (2025–26): 2c 1@+25 + 1 trailed (VIX, from +6%) −5.5% (A) / −5.5% (B); 2c 1@+25 + 1@+50 −8.3% / −8.4%; 3c 1@+25, 1@+50, 1 trailed −5.4% / −5.6%; 4c 1@+25, 2@+50, 1 trailed −5.4% / −5.6%. Paired spec 3c vs spec 1c: A +0.6% [+0.3%, +0.9%] then +0.7% [+0.3%, +1.1%]; B +0.7% [+0.4%, +1.0%] then +1.0% [+0.7%, +1.4%]. — `out/t5_scaleout_{A,B}.csv`, `out/contrasts.csv`
- Paired T1 +25% all-out vs no target (−32% stop, flat): A −1.3% [−7.9%, +4.9%] then −5.9% [−13.8%, +1.2%]; B −2.4% [−7.9%, +2.7%] then **−7.7% [−14.2%, −2.0%]**. — `out/contrasts.csv`
- Fill realism: bid_size at the exit minute was ≥ 1 contract on 100% of +25% and +50% target exits (median bid_size 33–61); the 2-contract +50% leg of the 4c rule had bid_size ≥ 2 on 96.1% (A) / 96.6% (B). — `out/t5_scaleout_{A,B}.csv` (`target_fill_ok`)
- McMillan: "we most certainly do not endorse the approach of using targets"; partial profits "harm the overall return on the position" when the move continues (opinion with one worked example). — [Option Strategist](https://optionstrategist.com/node/6081)

### Inferences
- The win rate the stop requires is the arithmetic the spec never does: at T1 +25% against a −37% realised loss, break-even is 61%; the sweep fade and the random entry both deliver 46–49%. T2 at +45–50% needs 43–46% and gets 34–37%. The only target that lowers the required win rate below what the entries deliver is none at all, which is why "no target" is the best single exit in 2025–26 and the worst in 2022–24 (its +234% average win is a handful of days).
- The scale-out's gain over all-out comes entirely from the trailed leg; 1@+25 + 1@+50 with no trailed leg is as bad as all-out. Whether 2, 3 or 4 contracts does not matter (−5.4% to −5.6%) because a leg's per-contract result does not depend on the other legs.
- Verdict: **T1/T2 as all-out exits: do not keep as the primary exit** (they fail the break-even arithmetic in both periods); **scale-out: keep a trailed remainder** (3c beats 1c by +0.7–1.0% OOS, intervals clear of zero), with no claim that the result is positive. Replacement, if a target is wanted at all: 1 contract at +25%, the rest trailed 10% from the peak once +6%, no T2.

### Gaps
- Targets fill at the target price (limit); with a market order at the minute's bid the result would be the same or better, since the bid is at or above the target. No tick data to test a partial fill within the minute.

## Test 6: the size cap (< 5 contracts) and liquidity at the quoted NBBO

### Takeaway
At the quoted NBBO both sides (ask_size at entry and bid_size at the exit minute of the spec stack) cover 2 contracts on 95–96% of trades, 3 on 92–94%, 5 on 89–92%, 10 on 80–85% (SPXW the thinnest: 84–86% at 5). Per-contract EV does not vary with quoted size in a direction that would justify a cap. "≥ 5 contracts had negative EV" in the ledger is an outcome of a negative-EV engine traded at every size, not a causal rule, unless the vendor's size was set by something (conviction, time of day) that itself predicts the result — which this data cannot see.

### Cited Findings
- Share of trades with ask_size ≥ k at entry **and** bid_size ≥ k at the spec stack's exit minute, universe A / B: k = 1: 100% / 100%; 2: 94.6% / 96.1%; 3: 92.0% / 94.0%; 5: 88.8% / 91.5%; 10: 80.1% / 85.0%. By product at k = 5 (A): SPY 93.4%, QQQ 89.4%, IWM 89.4%, SPXW 84.0%. — `out/t6_liquidity_{A,B}.csv`
- Spec stack EV by quoted ask_size at entry, 2025–26: A 0–5 contracts quoted −2.4% (n 95, median ask $9.60), 5–20 −4.6% (247, $2.37), 20–100 −4.1% (742, $1.70), 100+ −5.5% (523, $0.91); B −4.7% (90), +0.3% (180), −3.8% (688), −9.5% (814, $0.56). — `out/t6_by_size_{A,B}.csv`
- Fees are $1.30 a contract round trip: 1.0% of a $1.25 debit, 2.3% of a $0.56 one; the 100+ size bucket holds the cheapest contracts. — arithmetic on `out/summary.json`

### Inferences
- A 1–3 contract order never exhausts the displayed NBBO on these names, and 5 would have on about one trade in ten; the per-contract result is therefore the same at 1, 3 and 5 on nine trades in ten, and on the tenth the fill would be at the next level, which the data cannot price. The ledger's size/EV correlation is, on this evidence, the base rate of a losing engine showing up on its largest tickets; the only size effect visible here runs the other way (the largest *quoted* sizes sit on the cheapest contracts, where fees bite hardest).
- Verdict: **the < 5 cap is untestable as a causal rule and unnecessary as a liquidity rule at 1–3; keep it only as a risk-budget choice.** Replacement: size by the dollar risk budget, not by a count, and never read a size-EV correlation in the ledger as a rule without the counterfactual (the same trades at 1 contract).

### Gaps
- Depth beyond the NBBO (what 5+ contracts would pay) is not on disk. The ledger's own trades (sizes and times) were not available to this group, so the size-vs-outcome correlation in it could not be decomposed.

## Test 7: Module 4, the rolling 30-trade profit-factor breaker (< 1.05 → paper)

### Takeaway
On a losing stream the breaker does what it should — it keeps the engine in paper mode 66–100% of the time per product — but it does not raise the live-only EV (worse than no breaker in 7 of 8 product × universe cells in 2025–26 for the spec stack), and the trades it skips win as often as the ones it takes. Its sampling noise is the real finding: a 30-trade profit factor cannot tell a genuinely +5%-of-debit engine from a losing one (it trips in 49–85% of 200-trade runs), and for a low-win-rate, fat-tailed exit (13% wins, +240% average win) it trips in ~100% of runs even at a true +10% EV and in 95–98% at +20%.

### Cited Findings
- Simulation on each product's chronological trade sequence (spec 1c; PF over the last 30 trades, live and paper alike; PF < 1.05 → the next trade is paper), 2025–26: universe A SPY all trades −3.7% vs live-only −8.2% (22 live of 384, 94% paper); QQQ −3.5% vs −5.3% (43 live, 90%); IWM −7.6% vs −16.3% (3 live, 99%); SPXW −3.2% vs −5.7% (48 live, 88%); pooled across products −4.5% vs −2.5% (349 live, 78%). Universe B: SPY −3.4% vs −1.5% (121 live, 73%); QQQ −4.5% vs −5.4% (89%); IWM −13.6% vs −35% (1 live); SPXW −2.8% vs −3.3% (74%); pooled −6.0% vs −5.0% (66%). Share of skipped trades that won: 22–36%, against win rates of 25–37% overall. — `out/t7_breaker_{A,B}.csv`
- The same with the "−32% stop + flat" exit (13% win rate, heavy tails), 2025–26: A SPY +1.7% all vs +5.7% live (141 live), QQQ −0.9% vs +15.5% (142), IWM −10.4% vs −26.8% (77), SPXW −0.4% vs +2.4% (135); B SPY +10.4% vs +7.0%, QQQ −6.7% vs −0.8%, IWM −5.7% vs −17.2%, SPXW −0.4% vs −2.8%; by year the live-only figure swings from −30.8% (QQQ B 2026) to +22.3% (QQQ B 2025). — `out/t7_breaker_{A,B}.csv`
- Sampling noise (2,000 streams of 200 i.i.d. trades drawn from each exit's 2025–26 outcomes, shifted to a true EV of 0 / +5% / +10% / +20% of debit): spec-1c-shaped outcomes (win rate 59–61% at +5%, avg win +13–17%, avg loss −7 to −14%): the breaker trips at least once in 100% / 49% / 0% / 0% (A) and 100% / 85% / 15% / 0% (B) of runs, with median first trip at trade 71–99 at +5%. Flat-exit-shaped outcomes (win rate 13–14%, avg win +240–250%, avg loss −15 to −38%): trips in 100% / 100% / 100% / 95–98% of runs, spending 17–21% of the stream in paper at a true +20% EV. — `out/t7_breaker_noise_{A,B}.csv`

### Inferences
- A 30-trade profit factor on an engine whose edge, if any, is a few percent of debit with winners of +15–25% and losers of −10–15% is a coin flip at +5% true EV; on an engine whose profit is a few +200% days a year, it is a machine for switching off right before them. The breaker therefore cannot be the thing that separates a working lane from a broken one; it can only be a drawdown governor, and the ledger results it produces (a product "in paper") are outcomes of sampling, not evidence about the lane.
- The live-only results that look better (QQQ A flat, +15.5%) rest on 142 trades in a window where the same rule's unbrokered EV flipped from −21.5% (2024) to +22.3% (2025) and back to −30.8% (2026); the breaker lagged each regime by 30 trades, which is why its year-by-year sign tracks the previous year's.
- Verdict: **do not use PF < 1.05 over 30 trades as a lane-quality test; untestable as an improvement** (no configuration raised live-only EV across products and periods). If a governor is wanted, state it as a drawdown budget in dollars with a re-entry rule, and note in the UI that a 30-trade window has the trip rates above. Any replacement window must be sized to the exit's win-rate shape: for the spec stack a 30-trade window has a ~50–85% false-trip rate at +5%; the noise table should be recomputed for the actual lane before a threshold is chosen.

### Gaps
- The breaker was simulated per product on each universe's one-trade-a-session sequence; the ledger's own trade cadence (several a day, several tickers) would make the 30-trade window shorter in calendar time and the noise worse, not better.
- "Per horizon/ticker subset" was tested per ticker on the 0DTE horizon only.

## Test 8: Weekly / Swing / LEAPS exit rules — blocker, and the Black-Scholes drag of a −20% / −17% / −25% premium stop

### Takeaway
There are no multi-day option paths on disk (only same-day chains and a few October 2026 EOD sessions), so the Weekly/Swing/LEAPS stops, scale-outs, RSI exit, 3-day time stop and the 60-DTE roll are **untestable here — a blocker for the horizons group.** What can be said is arithmetic: at IV 20% a −20% premium stop on a 7-DTE ATM option is a 0.47% adverse move at entry, 0.20% after one trading day, and is tripped by time decay alone by the third day; at 14 DTE the move is 0.67% / 0.48% / 0.08%; at 30 DTE 0.98% / 0.85% / 0.58%; at 90 DTE 1.70% / 1.62% / 1.46%; a −25% stop on a 365-DTE LEAPS is a 4.3% move. A 4–5 vol-point IV drop trips the −20% stop at entry at every tenor to 90 DTE.

### Cited Findings
- Black-Scholes, ATM, r = 4%, no dividend, trading days converted at 252/365 (`bs_drag.py` → `out/t8_bs_drag.csv`; IV 15% and 30% rows in the file). IV 20%: 7 DTE premium 1.14% of spot, decay −11.3% after one trading day, −39.2% after three; adverse move to −20% 0.47% (0.37 of a daily 1σ), after one day 0.20%, after three 0.0%; to −17% 0.40% / 0.13% / 0.0%; to −25% 0.60% / 0.32% / 0.0%. 14 DTE: premium 1.64%, decay −5.5% / −17.6%; −20% move 0.67% / 0.48% / 0.08%. 30 DTE: 2.45%, −2.6% / −8.0%; 0.98% / 0.85% / 0.58%. 90 DTE: 4.45%, −0.9% / −2.7%; 1.70% / 1.62% / 1.46%; −25% 2.16%. 365 DTE: 9.9%, −0.2% / −0.7%; −25% 4.31% / 4.27% / 4.19%. IV drop that trips −20% at entry: 4.1 points (7 DTE), 4.2 (14), 4.3 (30), 4.5 (90), 5.2 (365). — `out/t8_bs_drag.csv`
- The spec's underlying level stops for Weekly/Swing sit 2.4–4.6% away (median 3.45%). — the spec as given

### Inferences
- For a 4–7 DTE weekly, the −20% / −17% premium backstop is reached by a move smaller than half a daily standard deviation on the entry day and by theta alone within three sessions: it is a time stop in disguise and will fire long before the 2.4–4.6% underlying level stop on nearly every trade. For a 14-DTE swing the backstop is a 0.5–0.7% move inside two days; for 30 DTE about 0.6–1.0%; only at 90+ DTE does a −20% premium stop correspond to a move of a daily σ or more. The "A+ −20% / A −17%" distinction is a 0.07% difference in the underlying at 7 DTE — within the spread.
- A −25% LEAPS stop (4.3% move) and "a weekly close beyond the macro wall / 200-DMA" are of comparable scale and the two may be redundant; which fires first depends on where the wall sits.
- Verdict: **untestable on this data; blocker.** The horizons group should test these on multi-day paths; until then the arithmetic says the Weekly −17%/−20% premium stop and the level stop cannot both be binding, and the premium stop will be the one that fires.

### Gaps
- No multi-day option quotes on disk; no earnings/event IV paths; no data on the ledger's A/A+ grading. Theta/vega drag was computed with a flat IV surface and no skew.

## What is kept, what changes, what cannot be tested (summary table)

| Rule (spec) | Verdict | Basis |
|---|---|---|
| −32% premium backstop, never widened | Keep | Inert inside the stack (0.7–6% of exits); best stand-alone premium level OOS; tighter levels fire on bid-ask noise (25% within 3 min at −15%) and realise 3–5 points past nominal |
| −15.2% ledger "stop" | Not a stop | Average realised loss across structural/lock/time exits (−10% to −16% replayed); the backstop fires on ≤ 6% |
| Structural stop (swept level + buffer) | Keep, buffer 0–2 bps | Fires on 90–96% of sweep fades; sets the loss distribution, EV ±0.6% |
| Breakeven lock at +6% high bid | Keep with a target; **change activation to +0%** | +6% beats none (+2.0% / +1.0% OOS, CIs clear of zero) and +12% (−1.2% / −0.6%); +0% beats +6% (+1.0% A, CI clear; +0.3% B, not clear). Choke 63–66% at every threshold: not a bounce effect |
| VIX-tiered trail 6/8/11/14% | Change to flat 10% from the peak, active from +6% | Paired difference ±0.3%, CIs include zero; tiers never beat the best flat rate; a simplification, no EV claim |
| 5-minute time stop if < +6% | Keep or drop; no change | Fires on 47%; sells at −13% what would have made −12 to −13% |
| T1 +25% / T2 +45–50% all-out | Do not use as primary exit | Needs 61–63% / 43–46% win rate; gets 46–49% / 34–37%; worse than no target OOS (B −7.7%, CI clear) |
| Scale-out 25/50/rest | Keep a trailed remainder | 3c beats 1c by +0.7–1.0% OOS (CIs clear of zero); contract count 2/3/4 immaterial |
| Hard flat 15:58 | Keep | Not contested; every rule above used it |
| Size cap < 5 ("≥ 5 lost") | Outcome, not a rule | NBBO covers 5 on 89–92%, 3 on 92–94%; EV by quoted size non-monotonic |
| PF < 1.05 over 30 trades → paper | Do not use as a lane test | Live-only EV worse in 7 of 8 cells; trips 49–85% at a true +5%, ~100% for a fat-tailed exit |
| Weekly/Swing/LEAPS stops, scale, RSI, 3-day, roll | Blocker | No multi-day paths on disk; BS drag table given |

Files: `extract.py` (paths), `engine.py` (exit engine), `run_tests.py` (tests 1–7 → `out/t*_{A,B}.csv`, `out/summary.json`), `by_product.py` (→ `out/by_product.csv`), `contrasts.py` (paired day-bootstrap → `out/contrasts.csv`), `bs_drag.py` (test 8 → `out/t8_bs_drag.csv`), `verify.py` (80 of 80 trades re-derived independently, 0 differences). Logs in `out/*.log`. The path parquets (`out/paths_*.parquet`, ~7,100 trades × 391 minutes × 7 series) are intermediate data. No keys, no credentials, no API calls.
