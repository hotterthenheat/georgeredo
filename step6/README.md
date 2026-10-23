# Step 6: the anatomy of the runners

**The owner's request:** "don't hold to close and the ones that moved 40%+ figure out how they worked, and the ones that moved 500%+ figure out how, that's the whole game reversed engineering and figuring out how".

**Short answer:**
- **How they worked:** a runner is the underlying moving the contract's way, far and steadily. Nothing else comes close.
  - A +40% run in the hour after buying needed a median move of 0.72 of the remaining expected move, over 39 minutes.
  - A +500% run by 3:30 pm needed 2.8 remaining moves, over 3¾ hours, almost never in one burst.
  - The price move made 97–108% of the gain. A rise in implied vol added 2% (+40%) to 12% (+500%). Time decay took back 2–11%, and the spread 1–3%.
- **What was visible before:** almost nothing that raised the odds by the pre-registered 25%.
  - Of 1,476 tests, 24 passed on 2022–2024. Only 4 held on 2025–2026, and all 4 *lowered* the odds.
  - Small lifts (3–24%) did hold in both periods. A wide first half hour, a jumpy tape, a contract already crushed, and the contract rising in the last 1–5 minutes all helped. A positive UW gamma regime, a quiet tape and a contract not yet crushed all hurt.
- **Trading it without holding to the close:** the 6 rules picked on 2022–2024, each with 3 exits, all lost money on 2025–2026.
  - That is 0 of 18 rules and exits passing, at −3% to −22% a trade.
  - Most did no better than random contracts bought at the same times and moneyness.
  - The rules' lift on 2022–2024 (1.4× for +40%, 3.5× for +500%) fell to about 1× or below on 2025–2026.

**The trades:** step 2's buys, near the money only: 240,493 trades over 828 sessions, 2022-05-13 to 2026-10-09.

| Filter | Rule |
|---|---|
| Strike | Within one remaining expected move of the price (step 3's at-the-money straddle) |
| Spread | 10% of the mid or less |
| Buy times | 9:31 am to 3:00 pm |
| Sessions | Full sessions only |
| Held out | The 28 held-out months were never opened |

By period and product:

| | Trades | Sessions |
|---|---|---|
| Pick (2022–2024) | 111,575 | 490 |
| Check (2025 – 2026-10-09) | 128,918 | 338 |
| SPX | 114,663 | |
| SPY | 50,733 | |
| QQQ | 58,084 | |
| IWM | 17,013 | |

Everything was written down first in `PREREG.md` (commit `30babaa`), before any lift, rule or P&L was computed.

## The classes

The classes are measured by the **bid's peak**, never the close. Two windows:
- **H60:** the 60 minutes after buying, never past 3:30 pm.
- **H1530:** from buying to 3:30 pm.

| Class | Peak | Share, H60 | Share, H1530 |
|---|---|---|---|
| R40 | +40% or more | 38.1% | 55.8% |
| R100 | +100% or more | 12.8% | 31.4% |
| R500 | +500% or more | 0.29% (695 trades) | 2.4% (5,685 trades) |
| DUD | never above +10% | 30.3% | 21.2% |

Pick and Check are within 3 points of each other on every class (`out/classes.csv`).

## Part 1: how the moves happened

All figures are medians over both periods. Pick and Check alone agree closely (`out/how.csv` has every figure by period). Columns marked † could only be known after the fact.

| | DUD (H60) | R40 (H60) | R100 (H60) | R500 (H60) | R500 (H1530) |
|---|---|---|---|---|---|
| Trades | 72,773 | 91,625 | 30,733 | 695 | 5,685 |
| † Minutes from buy to peak | 3 | 39 | 46 | 51 | 225 |
| † Underlying move its way, in remaining expected moves | 0.04 | 0.72 | 1.09 | 2.54 | 2.84 |
| † Same, in 9:31 straddles | 0.03 | 0.55 | 0.83 | 1.92 | 2.38 |
| † Same, % | 0.02% | 0.38% | 0.55% | 1.24% | 1.56% |
| † Largest 5 minutes, share of the move | — | 55% | 45% | 39% | 24% |
| † A burst (one 5-minute stretch carried ≥ 60%) | — | 42% | 22% | 26% | 3% |
| † Gain from the price move | | 108% | 103% | 97% | 100% |
| † Gain from implied vol rising | | +2% | +4% | +6% | +12% |
| † Gain lost to time | | −7% | −5% | −2% | −11% |
| † Gain lost to the spread | | −3% | −2% | −1% | −1% |
| † Implied vol change, buy to peak | 0.0 pts | +0.3 | +0.8 | +4.9 | +8.6 |
| † Made a new session high (calls) / low (puts) on the way | 17% | 65% | 75% | 91% | 97% |
| † Broke the opening range its way on the way | 4% | 34% | 42% | 41% | 60% |
| † Crossed the prior session's UW gamma flip its way (where covered) | 2% | 20% | 28% | 49% | 48% |
| † Trend day (close − open ≥ half the day's range) | 54% | 52% | 52% | 61% | 72% |
| † Day's range ÷ 9:31 straddle | 1.65 | 1.73 | 1.90 | 2.92 | 3.01 |
| † The day closed the contract's way | 35% | 65% | 73% | 91% | 95% |
| Calls (the rest are puts) | 49% | 49% | 44% | 38% | 39% |

How to read it:
- **The gain split.** The change in the option's price is split three ways by repricing it with Black-Scholes on the market's own forward (put-call parity): the price move (delta and gamma), the change in implied vol (vega), and time (theta). The fourth part is the spread paid in and out. The four add up exactly to (peak bid − ask paid). Shares are of the class's total gain. The vol part can't be solved for some deep in-the-money peaks: 3% of R500 (H60) and 18% of R500 (H1530) are left out of the split.
- **The +40% runs are ordinary moves.** Under three quarters of the move the market was pricing, over about 40 minutes, 42% of them mostly in one 5-minute burst. Implied vol barely moved.
- **The +500% runs are rare days.**
  - The underlying went 2.5–3 times the remaining expected move.
  - The day's range was about 3 times the 9:31 straddle, against 1.7 on an ordinary day.
  - 97% made a new session extreme on the way, and 95% of those days closed the contract's way.
  - Implied vol rose 5–9 points and paid for about as much as time decay took.
  - Over the whole afternoon these were steady grinds, not spikes: only 3% were bursts.
- **Puts dominate the biggest runs:** 61% of R500 (H1530).
- **Scheduled events:**
  - FOMC days are not over-represented among runners (2–6% of each class, against 4–8% of duds).
  - On FOMC days, every R500 peak came after the 2:00 pm statement.
  - NFP days are over-represented among R500 (8% against 5% of duds).
- **Runners cluster by day.** R40 runs happened on all 828 days. R500 (H1530) happened on 382 days, and 17% of them came from 5 days. The busiest was 2025-04-09 (392 trades), then 2025-04-08, 2026-06-05, 2026-06-09 and 2024-12-18 (`out/runner_days.csv`).

**Knowable at the buy:** the time, the moneyness, the price, implied vol at the buy, the gap and VIX. Everything marked † is only known afterwards. It explains a move; it cannot be traded.

### The 30 largest +500% runs (H1530)

They come from 6 days. A few:

| Date | Contract | Bought | Ask | Peak bid | Peak at | × | Underlying, buy → peak | Remaining moves |
|---|---|---|---|---|---|---|---|---|
| 2024-04-04 | SPX 5240 put | 12:00 pm | $2.15 | $83.00 | 3:30 pm | 38.6 | 5,251 → 5,155 (−1.8%) | 8.6 |
| 2025-10-10 | QQQ 610 put | 10:30 am | $0.48 | $17.62 | 3:29 pm | 36.7 | 611.9 → 592.3 (−3.2%) | 9.6 |
| 2023-12-20 | SPX 4770 put | 1:00 pm | $1.70 | $58.40 | 3:09 pm | 34.4 | 4,777 → 4,711 (−1.4%) | 7.4 |
| 2026-06-09 | QQQ 717 put | 10:00 am | $1.04 | $29.00 | 12:41 pm | 27.9 | 721.5 → 687.1 (−4.8%) | 7.0 |
| 2025-04-09 | QQQ 426 call | 12:00 pm | $1.33 | $37.00 | 3:26 pm | 27.8 | 418.2 → 463.3 (+10.8%) | 5.2 |

- **2024-04-04:** SPX sat flat near 5,250 until about 1:30 pm, then fell for two hours. The 12:00 put rode it in steps; its largest 5 minutes were 25% of the move.
- **2025-10-10:** QQQ fell all afternoon. The 610 put's implied vol went from 8% to 69%, and vol added 7.7 times the price paid on top of the price move.
- **2025-04-09:** the day of the tariff pause. Implied vol was already 49% at the buy.

Every one of the 30 needed a move of 4.6 to 9.6 remaining expected moves. `out/r500_cases.csv` has all 30 with the underlying every 15 minutes.

## Part 2: what was visible before (lift)

**The trap.** Describing winners says nothing on its own: losers may look the same. Only the lift counts. Lift is how often the trades in a bucket ran, against how often trades bought **at the same time and the same moneyness** ran in the same period (1.0 = no better).

**What was tested:**
- Step 5's 42 measurements, less three that are constant or duplicated here.
- Nine more known by the buy minute: the gap, the first-30-minute range against the 9:31 straddle, the VWAP side and distance, the opening-range state, the UW gamma regime and distance to the prior session's flip, the scheduled event, and the contract's implied vol.
- `lookahead.py` rebuilds them with every raw file cut at the buy minute.

Each measurement was cut into fifths on Pick. The intervals come from resampling blocks of 5 dates.

**The pre-registered test:** a bucket passes on Pick when its lift is at least 1.25 (or at most 0.80), its interval clears 1, and it has 300 trades on 30 dates. It holds when Check's interval clears 1 on the same side.
- 1,476 tests, 24 passed on Pick and 4 held. All 4 held ones *lower* the odds (`out/lift_held.csv`):

| Class | Bucket | Pick lift | Check lift |
|---|---|---|---|
| R100 in H60 | Contract had fallen less than 1.9× from its earlier high (not crushed) | 0.71 | 0.62 |
| R500 in H60 | VIX 19.7–23.5 | 0.43 | 0.37 |
| R500 in H60 | Gapped up more than 0.47% the contract's way (calls on a gap up, puts on a gap down) | 0.40 | 0.45 |
| R500 in H60 | Contract's opening ask under 1.26× its low so far (it had barely fallen from the open) | 0.18 | 0.13 |

- No bucket raised the odds of a +40% run by 25%. The best on Pick was NFP day at 1.23 (Check 1.19), on too few dates to count.

**Smaller lifts that held in both periods.** These were not pre-registered and are shown for the record: 62 buckets had intervals clear of 1 on the same side in both periods (`out/lift_consistent.csv`). The clearest:

| Class | Bucket | Base rate (Pick / Check) | Lift (Pick / Check) |
|---|---|---|---|
| R100 in H60 | First 30 minutes' range ≥ 0.76 of the 9:31 straddle | 11.6% / 13.8% | 1.17 / 1.24 |
| R100 in H60 | Contract's ask up ≥ 5.5% in the last minute | | 1.16 / 1.16 |
| R100 in H60 | Contract's ask up ≥ 12.6% in the last 5 minutes | | 1.15 / 1.17 |
| R100 in H60 | Contract fallen ≥ 6.2× from its earlier high (crushed) | | 1.13 / 1.13 |
| R40 in H60 | Jumpiest fifth of the last 15 minutes (1-minute volatility) | 36.5% / 39.5% | 1.14 / 1.12 |
| R40 in H60 | Ask ≥ 2.5× its own low so far | | 1.11 / 1.09 |
| R40 in H60 | Day's range so far ≥ 1.0% | | 1.10 / 1.10 |
| R40 in H60 | UW gamma regime positive | | 0.88 / 0.90 |
| R40 in H60 | Quietest fifth of the last 15 minutes | | 0.85 / 0.85 |
| R40 in H60 | First 30 minutes' range < 0.37 of the 9:31 straddle | | 0.86 / 0.80 |

- These agree with step 5: a moving tape, a crushed contract, and a contract already turning up.
- They are small. The best moves a 14% chance of a +100% hour to about 17%.

## Part 3: trading it without holding to the close

**The rules** were picked mechanically on Pick, as in `PREREG.md`: the best one or two conditions by lift, with at least 300 trades on 60 dates.

| Family | Rule (Pick buckets) | Pick trades | Pick lift | Check lift |
|---|---|---|---|---|
| A (R40 in H60) | Underlying moved against the contract in the last 15 minutes but its way over 30 | 665 | 1.45 | 1.04 |
| A | Contract's ask down 10–23% in 15 minutes, underlying up ≥ 0.17% its way over 30 | 1,081 | 1.41 | 0.92 |
| A | Underlying 0.05–0.17% its way over 30 minutes, jumpiest fifth of the tape | 1,239 | 1.40 | 1.02 |
| B (R500 in H1530) | Ask ≥ $14.50 (SPX), VIX 14.2–17.2 | 2,426 | 3.58 | 0.95 |
| B | Ask ≥ $14.50 (SPX), prior session's range < 0.72% | 2,483 | 3.51 | 0.51 |
| B | In the money 0.19–0.59 moves, and the price 1.33+ remaining moves on the far side of the prior session's UW gamma flip (below it for a call, above it for a put) | 752 | 3.49 | 0.88 |

**The exits** (never held to the close):
- (a) Sell at +40% or at a −30% stop, otherwise at 60 minutes (or 3:30 pm).
- (b) A 50% trailing stop armed at +40%, otherwise out at 3:30 pm.
- (c) Sell half at +40% and trail the rest as in (b).

Fills are at the ask in and the bid out. Fees are $0.65 a contract each way, and SPXW's own schedule ($1.19 or $1.28).

**Check (2025 – 2026-10-09), never seen while choosing:**

| Rule | Exit | Trades | Win rate | Avg a trade | Median | Avg win | Avg loss | 95% range (20-session blocks) | Random, avg (97.5th pct) | Rule's percentile |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | a | 1,035 | 37% | −7.5% | −31% | +37% | −33% | −14.8% to −0.6% | −6.1% (−4.1%) | 9 |
| A1 | b | 1,035 | 27% | −21.5% | −30% | +83% | −61% | −40.0% to −1.1% | −5.9% (+1.3%) | 0 |
| A1 | c | 1,035 | 53% | −19.1% | +4% | +35% | −81% | −37.3% to −0.8% | −8.7% (−4.0%) | 0 |
| A2 | a | 1,502 | 32% | −11.2% | −32% | +36% | −34% | −14.8% to −7.6% | −6.3% (−4.5%) | 0 |
| A2 | b | 1,502 | 36% | −11.9% | −25% | +81% | −64% | −29.4% to +8.8% | −6.0% (−0.1%) | 2 |
| A2 | c | 1,502 | 55% | −13.7% | +6% | +42% | −82% | −28.7% to +4.1% | −8.9% (−5.0%) | 1 |
| A3 | a | 2,435 | 37% | −7.6% | −32% | +37% | −34% | −11.9% to −3.5% | −6.1% (−4.7%) | 1 |
| A3 | b | 2,435 | 29% | −21.9% | −28% | +75% | −61% | −32.1% to −7.7% | −6.0% (−1.5%) | 0 |
| A3 | c | 2,435 | 54% | −19.4% | +4% | +35% | −83% | −28.5% to −8.2% | −8.8% (−5.7%) | 0 |
| B1 | a | 6,350 | 42% | −4.0% | −18% | +32% | −30% | −4.7% to −3.4% | −4.2% (−3.4%) | 72 |
| B1 | b | 6,350 | 35% | −3.3% | −22% | +94% | −56% | −8.2% to +2.3% | −4.0% (−1.7%) | 72 |
| B1 | c | 6,350 | 59% | −5.5% | +7% | +43% | −75% | −8.3% to −2.8% | −6.1% (−4.5%) | 75 |
| B2 | a | 5,406 | 40% | −5.1% | −20% | +32% | −29% | −6.4% to −4.0% | −4.3% (−3.5%) | 3 |
| B2 | b | 5,406 | 35% | −4.3% | −22% | +93% | −58% | −9.7% to +3.6% | −4.0% (−1.6%) | 43 |
| B2 | c | 5,406 | 57% | −7.0% | +7% | +44% | −76% | −10.5% to −2.6% | −6.1% (−4.4%) | 16 |
| B3 | a | 5,454 | 37% | −6.4% | −31% | +36% | −32% | −7.6% to −5.1% | −4.8% (−4.0%) | 0 |
| B3 | b | 5,454 | 31% | −7.7% | −26% | +95% | −55% | −12.1% to −3.0% | −4.4% (−2.2%) | 0 |
| B3 | c | 5,454 | 54% | −9.9% | +4% | +43% | −71% | −13.6% to −6.5% | −6.6% (−4.8%) | 0 |

- **0 of 18 passed.** Every average is negative. No interval's lower end is above zero. None beats the 97.5th percentile of its 500 random draws.
- The six rules lost **more** than random contracts bought at the same times and moneyness in 14 of 18 cases (below the 20th percentile).
- Every population trade, for scale (Check): (a) −6.3%, (b) −5.8%, (c) −8.6% a trade, win rates 39%, 32% and 57%. The rules sit near or below these.
- On Pick, where they were chosen, the rules made −9% to +12% a trade, every interval including zero or below it (`out/results.csv`). So even there, the higher odds of a run did not become money after the spread and fees.
- **Why +40% runs don't pay:**
  - Exit (a) wins 37% of the time at about +37% and loses about −33% when it doesn't. That nets about −6% after costs.
  - A 38% chance of a +40% hour sounds high, but a +40% target with a −30% stop needs about 43% to break even before costs.
  - The best visible-before lift (1.1–1.2×) is not enough to close that gap.
- **The best-5-days share** is left blank where the total is a loss (all 18 Check rows). On Pick, the rules that made money took 2–83 times their whole profit from their 5 best days.

## What it means

- **How the runners worked is clear.** The underlying moved the contract's way by one expected move for +100% and by 2.5–3 for +500%. That happened on a trend day, through the session's extreme, mostly as a grind. Implied vol rose with the biggest runs, but the price move did almost all the work.
- **When it would happen was not visible.** Nothing known at the buy minute raised the chance of such a move by much. The one sizeable lift chosen on 2022–2024 (3.5× for +500%) was a selection artefact and vanished on 2025–2026.
- **Trading the visible-before conditions with fixed exits lost money in every combination tested**, usually more than random.
- **This is a negative result, like steps 2–5.** Nothing was tuned after Check was read.

## Checks

- `verify.py`: 40 trades re-derived from the raw quotes with separate plain-loop code. That is 30 random trades and 10 that reached +500% by 3:30 pm. The figures checked are:
  - the entry quote;
  - the straddle and moneyness, so each trade's place in the population;
  - the peaks and their minutes in both windows;
  - the underlying at the buy and at the peak;
  - the three exits' dollar results.

  **0 differences in 480 figures.**
- `lookahead.py`: 1,204 trades on 16 sessions (half in the UW years) rebuilt with every raw file cut at the buy minute. That means quotes and prints stamped later, ETF bars not yet closed, and UW rows stamped later were all removed (17.2 million rows).
  - **0 differences in 104,748 feature values.**
  - As a control, the after-the-fact columns (the day's high and close, the peak) did change in 5,148 of 6,020 values, so the cut was real.
- Step 5's feature code was reused unchanged (`step5/features.py`). Its straddle equals step 3's on every trade (build.py stops otherwise).

**Limits:**
- Only one-minute quotes exist, so peaks and stops are read once a minute.
- UW data starts 2023-12-08. Before that, the UW buckets are "not available", and only about 3,700 Pick trades per fifth carry the flip distance.
- SPX's VWAP is SPY's scaled by SPX/SPY, since SPX has no volume.
- Implied vol is in trading-time units (252 × 390 minutes a year), solved from the mid.

## Files

| File | What it is |
|---|---|
| `PREREG.md` | The definitions, tests, rule selection, exits and pass rule, committed alone first (`30babaa`) |
| `build.py` → `$SP/step6/trades_<PRODUCT>.parquet` (scratchpad, 39 MB, not committed) | Every population trade: both windows' peaks, the Part 1 measures, the Black-Scholes split, the three exits, and every buy-minute feature (step 5's code plus this step's) |
| `data.py` | The shared reader: step 5's derived features (step 5's own formulas), the classes |
| `anatomy.py` → `out/classes.csv`, `how.csv`, `how_by_time.csv`, `runner_days.csv`, `r500_cases.csv` | Part 1 |
| `lift.py` → `out/lift.csv`, `lift_held.csv`, `lift_consistent.csv`, `buckets.json` | Part 2 |
| `trade.py` → `out/rules.csv`, `results.csv`, `results_all.csv` | Part 3 |
| `verify.py`, `lookahead.py` | The checks above |

sha256 of the scripts as run:

```
1f85ee904e48c7e87ba67176aeef813cfa45f47c23f8d0fbf1dbdc4c0b3df13c  build.py
69e09d10c7307ab90a2f825e2537580b472098f25c3e794c7a17312e5596c7a5  data.py
f01c4e6027505d385be568607253f241853dafb91f359ca50d4fdef7708ae8c9  anatomy.py
85da190999cf0fbe199874b73ebe53c2bb7ca5dcf5a38c529d968394fe1ee709  lift.py
e89285ce75373d1ba16e476c82abf133ed043a0850db81dd1b3f6877275541a3  trade.py
08dc66a32c9505f4a7c6bc6fc169604d5b5aaf2013b58c24c46562291ff839c3  verify.py
123951e7a5014e356177a3caefedae98821c1e88f387c3143b3441b1446d47d6  lookahead.py
```

Run order: `python3 -I step6/build.py`, then `anatomy.py`, `lift.py`, `trade.py`, `verify.py`, `lookahead.py`.
