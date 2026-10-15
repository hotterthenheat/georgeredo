# Lifecycle research — 8. Portfolio simulation (deliverable 7)

## 1. The simulator (`lc/sequencer.py`, `scripts/run_portfolio.py`)

**How it runs**
- Setup events from all roots are taken in time order, one session at a time.
- Each trade is run through the same position engine as the research (`lc/position.py`), with NBBO fills, fees, exits and expiry.

**Its rules**
- **At most one open position per root.** A same-direction signal while a position is open is ignored; adding to a position is a policy's job, not the portfolio's.
- **Opposite signal (M11):** `ignore`; `close` (exit at that minute, by re-running the open trade with its cutoff moved there); or `reverse` (exit, then open the new trade).
- **After a losing exit (M10):** `take` the next signal; `skip` the root for the rest of the session; or `cool15` (skip 15 minutes).
- **Sizing:**
  - fixed contracts, or fixed dollars of maximum loss (a debit; width × 100 − credit for a spread; strike × 100 − credit for a cash-secured put);
  - never more units than the smallest displayed size of any leg at the fill;
  - a cap on capital at risk across open positions and per correlated bucket (all four roots are one bucket: US equity index).
- A trade that does not fit the caps is shrunk to fit, or refused when even one unit does not fit.

**Starting equity is $100,000.** The CAGR is computed over trading days / 252.

## 2. Configurations and results: development + validation (2022-05 → 2025-09)

| Configuration | Trades | Refused (caps / size) | Total P&L | CAGR | Max drawdown | Daily Sharpe | Win rate | Average trade | Worst trade | Worst day |
|---|---|---|---|---|---|---|---|---|---|---|
| **P1** QS → cash-secured put, stop 2× credit, 1 contract, collateral capped at the account (SPY, QQQ, IWM) | 408 | 251 / 0 | +$1,437 | +0.8 % | −1.0 % | 0.85 | 61 % | +$3.52 | −$198 | −$330 |
| **P2** QS → credit put spread to expiry, $1,000 maximum loss a trade, 10 % at risk at most | 604 | 0 / 0 | +$10,165 | +4.8 % | −10.1 % | 0.67 | 90 % | +$16.83 | −$2,161 | −$4,434 |
| **P3** QS → Steady call or put, 30-minute exit, $1,000 of premium a trade | 2,217 | 0 / 967 | −$38,668 | −21.2 % | −42.9 % | −1.13 | 45 % | −$17.44 | −$2,324 | −$2,489 |
| **P4** every engine and pattern setup → Steady call or put, 30-minute exit, $1,000 a trade | 4,639 | 4,426 / 3,636 | **−$99,590** | −80.6 % | **−99.6 %** | −1.70 | 42 % | −$21.47 | −$934 | −$4,642 |

**Per root**

| Configuration | SPY | QQQ | IWM | SPXW |
|---|---|---|---|---|
| P1 | 155 trades, +$897 | 165, +$750 | 88, −$211 | — (its collateral is several times the account) |
| P2 | 169, +$6,881 | 173, +$846 | 80, +$4,843 | 182, −$2,405 |
| P3 | 737, −$14,980 | 734, −$23,529 | 352, −$15,758 | 394, +$15,599 |

**Notes**
- P3's 967 size refusals are all SPXW: a Steady SPX option costs more than $1,000.
- P4's SPXW refusals are the same.
- P4's cap refusals come from the shrinking account.

**Reading**
- **P1 is the best hold-out finalist traded as a portfolio, and it is tiny.**
  - One cash-secured put ties up $40,000–$65,000.
  - So the account holds one or two positions, and 251 of 659 signals were refused for collateral.
  - +0.8 % a year on the account, with a 1 % drawdown, is short-put carry at a very low notional exposure. It is not an edge worth the capital.
- **P2 earns 4.8 % a year with a 10 % drawdown and a 90 % win rate:**
  - its worst trade was −$2,161;
  - its worst day was −$4,434, 4.4 % of the account (2024-08 drawdown);
  - SPXW lost money in it, and IWM and SPY carried it.
  - This is the profile of selling same-day put spreads: many small wins, rare large losses. Its expectancy is within noise of zero on the hold-out (+5.96 [−19.86, +24.51] a trade, `07_validation.md` §4).
- **P3 and P4 show what negative expectancy does at fixed dollar risk:**
  - P4 is ruined: equity $410 by 2025-09.
  - Once the account shrinks, the caps decide which trades are taken.
- **No same-day long-premium portfolio** of these setups is viable at any size.

## 3. Re-entry (M10) and reverse (M11)

**These rules never fired in their first configurations**, so those configurations measure nothing:
- **P2r** (skip after a loss) equals P2 to the cent. A credit spread held to expiry never closes inside the session, so there is never a closed loss before the next signal.
- **P3r** (reverse) and **P3c** (close on an opposite signal) equal P3 to the cent. QS signals both directions on one root in a session on only 37 of 1,639 root-sessions, and never while a 30-minute trade is open.

The rules are therefore measured on the pooled engine and pattern setups (QS, TP, BO, BOF, LS, MSS, FVG), where both directions occur on almost every session. They are run at one contract a trade with no caps, so each variant differs from the base only by its rule (P5).

| Configuration (pooled setups → Steady call or put, 30-minute exit, 1 contract) | Trades | Closed by an opposite signal | Total P&L | Per trade | Win rate | Daily Sharpe | Worst day |
|---|---|---|---|---|---|---|---|
| **P5** base: ignore opposite signals, take every signal after a loss | 8,260 | — | −$119,914 | −$14.52 | 41.9 % | −1.81 | −$5,560 |
| **P5r** M11 reverse: close and open the other way | 10,147 | 2,246 | −$178,930 | −$17.63 | 40.9 % | −2.37 | −$18,741 |
| **P5c** M11 close on an opposite signal, stay flat | 8,839 | 1,839 | −$160,354 | −$18.14 | 41.2 % | −2.39 | −$12,998 |
| **P5s** M10 skip the root for the rest of the session after a loss | 4,033 | — | −$68,293 | −$16.93 | 42.8 % | −1.50 | −$2,733 |
| **P5k** M10 wait 15 minutes after a loss | 7,629 | — | −$119,583 | −$15.67 | 42.1 % | −1.89 | −$5,560 |

**Reading**
- **Reversing or closing on an opposite signal makes every trade worse:** −$17.6 to −$18.1 a trade against −$14.5.
  - An opposite signal arrives, on average, after the trade has already moved against it.
  - Closing then sells at the bid and pays the spread again.
  - Reversing also buys the other side after the move.
- **Skipping the session after a loss loses less in total only because it trades half as often:**
  - its trades are worse per trade (−$16.9) than the base's;
  - the same number of trades skipped at random would lose about 4,033 × $14.52 ≈ $58,600;
  - so the rule carries no information about which later trades will lose.
- **A 15-minute cool-down changes nothing material.**
- **No re-entry or reverse rule turns a negative-expectancy signal set positive, or improves it per trade.** The figures are on an account no cap can bind, so the differences are the rules alone.

## 4. The hold-out

P1 and P2 use the finalists' cells with their rules frozen as above. They were run on 2025-10-01 → 2026-10-09 after the finalists' hold-out was opened.

| Configuration | Period | Trades | Refused for capital | Total P&L | Annualised | Max drawdown | Win rate | Average trade | Worst trade | Worst day |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 QS → cash-secured put, stop 2× | development + validation | 408 | 251 | +$1,437 | +0.8 % | −1.0 % | 61 % | +$3.52 | −$198 | −$330 |
| P1 | **hold-out** | 122 | 156 | **+$987** | +1.4 % | −0.8 % | 63 % | +$8.09 | −$198 | −$283 |
| P2 QS → credit put spread to expiry, $1,000 risk a trade | development + validation | 604 | 0 | +$10,165 | +4.8 % | −10.1 % | 90 % | +$16.83 | −$2,161 | −$4,434 |
| P2 | **hold-out** | 196 | 0 | **−$6,805** | −9.6 % | −11.9 % | 88 % | **−$34.72** | −$5,196 | −$7,556 |

**Notes**
- P1's first hold-out run used a $100 M account by a configuration error. The edit that gave the P5 runs their uncapped account also matched P1's settings. That run (+$1,666 on 157 trades, no collateral refusals) is kept under `results/portfolio/superseded/` and labelled in `summary.json`. The table shows the rerun at $100,000.
- **P2 lost money on the hold-out.** An 88 % win rate, then one bad stretch: a −$5,196 trade and a −$7,556 day. That is the short-premium profile: the wins are small, and the year's losses arrive in a few days.
- **P1 stayed slightly positive.** It is still too small to matter: one or two cash-secured puts at a time on $100,000, earning about 1 % a year.

## 5. Portfolio conclusions

1. **No portfolio of these setups is worth running.**
   - The long-premium portfolios lose steadily and, sized at $1,000 a trade, ruin the account (P3, P4).
   - The put-selling portfolios earn carry that a random entry earns too:
     - P1 is about 1 % a year on $100,000, limited by collateral;
     - P2 won 4.8 % a year in development + validation and lost 9.6 % on the hold-out.
2. **Re-entry and reverse rules make a losing signal set lose more per trade** (§3).
3. **Capital use decides what a short-put portfolio can be.** A cash-secured put on SPY ties up $45,000–$70,000 for a day to earn about $8–50. A credit spread frees the capital but keeps the tail: the worst trade on the hold-out was −$5,196 on $1,000 of planned risk across several units.
