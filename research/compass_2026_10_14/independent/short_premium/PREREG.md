# Pre-registration: independent short-premium study (written 2026-10-15 15:35 UTC, before any study data was pulled)

Author: Grok Bot (executor) for Zak Ali. Data: ThetaData PRO via the shared Theta Terminal (127.0.0.1:25503), 5-minute NBBO
(`/v3/option/history/quote`, "last quote at the interval timestamp"), SPX 1-minute index prices, ETF 1-minute OHLC.

## Universe and window
- Roots: SPY, QQQ, IWM (ETF, physically settled, AM/PM: PM), SPXW and XSP (cash-settled, PM).
- Window: 2025-01-02 to 2026-10-09, every session with a listed same-day expiry. **Every rule below is fixed now; there is no
  parameter search, so the entire window is out-of-sample for this study.** Caveat stated up front: earlier repo work
  (plan §8–§9) already looked at overlapping data, so this is an independent replication, not virgin data.

## Setups (one structure, 1 lot, per root per session per entry)
Strike selection at entry from the chain itself: ATM = strike minimising |call mid − put mid| (two-sided quotes only);
EM (expected move) = ATM straddle mid.
1. **STRADDLE**: sell ATM call + ATM put.
2. **STRANGLE**: sell call at the first strike ≥ K_atm + 0.5·EM and put at the first strike ≤ K_atm − 0.5·EM.
3. **PCS** (put credit spread): sell the strangle put, buy the first put strike ≤ K_atm − 1.0·EM (must be a different strike).
4. **CCS** (call credit spread): mirror of PCS on calls.
5. **IC** (iron condor): PCS + CCS together.

Expirations / entries:
- **0DTE**: entries 10:00, 13:00, 15:00 ET on the expiry day.
- **1DTE**: entry 15:50 ET on the previous session, held overnight.
- Exit (primary): buy back at 15:55 ET on expiry day at the ask, except the H14 execution rule (plan §9): a short leg whose ask ≤ $0.05
  (ETF, XSP) / ≤ $0.10 (SPXW) is left to expire; long legs are sold at the bid if bid > 0, else left to expire. Legs left to
  expire are valued at intrinsic against the 16:00 settlement (ETF: 15:59 1-min close; SPXW: SPX 16:00 print; XSP: SPX/10).
- Secondary (reported, not used for promotion): hold everything to settlement at intrinsic.

## Costs (adverse NBBO fills, criterion 3)
Sell at bid, buy at ask, at the 5-minute stamp. Fees $0.70 per contract per side (ETF, XSP), $1.00 (SPXW). Entry requires two-sided
quotes on every leg (bid > 0 for shorts); otherwise the trade is skipped and counted.

## Random baseline (criterion 2)
Same structure, same root-days, entry time drawn uniformly from the 5-min stamps 09:45–15:30 (0DTE) or the previous session
09:45–15:50 (1DTE); exit identical. Five draws, seeds 1–5, from the committed contract-day list `results/contract_days.csv`.

## Gate (per setup × expiry × entry × root, and pooled per setup across roots, day-clustered)
PASS only if all hold: n ≥ 150 trades over ≥ 3 months; 95 % day-clustered bootstrap (2,000 resamples, seed 0) lower bound of mean
net P&L > 0; (lane mean − mean of five random draws) > mean round-trip cost of the lane (entry spread + exit spread paid + fees).
With 5 setups × 4 entries × 5 roots = 100 cells, a Bonferroni-adjusted bound (99.95 %) is also reported; a cell passing only
at 95 % is labelled "nominal".
