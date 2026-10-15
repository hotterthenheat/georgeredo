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

<!-- P5: filled from results/portfolio/summary.json once the P5 runs finish -->

## 4. The hold-out

<!-- HOLDOUT: P1 and P2 run on 2025-10-01 -> 2026-10-09, the rules frozen as above -->

## 5. Portfolio conclusions

<!-- CONCLUSIONS -->
