# Compass EMA ladder — PREVIEW, 2025-03

**PREVIEW — one month, no verdict, ~20 sessions.** Run on the owner's request ("test 1 month data first so i can see the
results fast") after the pre-registration (PREREG_EMA_LADDER.md, `0dd8c5d`) was committed alone. Nothing here is a test:
no interval, no eligibility, no BASE choice, no holdout. The full study waits for the owner's go.

- Month: **2025-03**, 21 full sessions (2025-03-03 → 2025-03-31). It is not one of the scanner's 28 held-out months and
  lies inside the main Pick split (2022-11-11 → 2025-04-02). Its sessions stay in Pick for the full study (disclosed in the
  prereg).
- Names SPY, QQQ, IWM pooled; 0DTE; every rule exactly as the prereg (best-R/R execution contract, fees $0.68748 each way).
- **The preview's base is V1 (EMA 9, L1)**, labelled so: V7–V13 are V1 plus one change. In the study the BASE is chosen on
  the whole Pick split (prereg §6), and may differ.
- Code: `ema_lib.py` sha256 `e56328fe396893209cb5b6d6b5a0587936c1c59a371734324d7677cdb4a8ae64`, `preview.py`
  `d0f2e72e37b60211317e9094aaf280e4b5ae1d0f65557c75866f077ba5c90fc8`, `preview_stats.py`
  `8e243556a23f38845148c67b354dda50c077505171b0edcd21a34d422cf3a123`. The trade list (`out/preview_2025-03.json`, 7.9 MB)
  is not committed; the run is deterministic and rebuilds it.

## The table (PREVIEW — one month, no verdict, ~20 sessions)

Mean % = mean per-trade return after costs ((exit bid − entry ask) × 100 − fees) ÷ (entry ask × 100); win = return > 0;
avg win / avg loss are the mean returns of winning / losing trades; mid-to-mid = the same trades marked mid to mid, no fee;
|delta| and premium are the bought contract's at entry (V13 buys the ATM contract, whose delta is not computed).

| id | version | trades | per session | mean % after costs | mean $ | win rate | avg win | avg loss | exits | mid-to-mid no fee | |delta| median (IQR) | premium (ask) median (IQR) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | EMA9 L1 (preview base) | 2781 | 132.4 | -9.20% | -2.76 | 15.5% | +37.5% | -17.7% | signal 100% | -0.93% | 0.18 (0.17–0.21) | $0.34 (0.25–0.45) |
| V2 | EMA9 L2 | 768 | 36.6 | -16.78% | -5.60 | 13.2% | +84.7% | -32.1% | signal 100%; 15:58 0% | -8.79% | 0.18 (0.16–0.21) | $0.35 (0.26–0.46) |
| V3 | EMA9 L3 | 253 | 12.0 | -24.32% | -10.15 | 10.7% | +163.8% | -46.8% | signal 93%; 15:58 7% | -16.50% | 0.19 (0.17–0.22) | $0.37 (0.28–0.49) |
| V4 | EMA20 L1 | 2214 | 105.4 | -8.50% | -2.51 | 12.5% | +65.4% | -19.1% | signal 100%; 15:58 0% | -0.17% | 0.19 (0.17–0.22) | $0.34 (0.25–0.45) |
| V5 | EMA20 L2 | 511 | 24.3 | -16.15% | -6.37 | 11.2% | +131.3% | -34.7% | signal 99%; 15:58 1% | -8.08% | 0.18 (0.16–0.21) | $0.36 (0.26–0.48) |
| V6 | EMA20 L3 | 192 | 9.1 | -26.68% | -11.22 | 8.3% | +233.2% | -50.3% | signal 89%; 15:58 11% | -19.04% | 0.18 (0.16–0.21) | $0.40 (0.30–0.51) |
| V7 | base + GEX < 0 | 2749 | 130.9 | -9.15% | -2.75 | 15.5% | +37.3% | -17.7% | signal 100% | -0.92% | 0.18 (0.17–0.21) | $0.34 (0.25–0.45) |
| V8 | base + net premium side | 2101 | 100.0 | -8.50% | -2.38 | 14.8% | +46.0% | -17.9% | signal 100% | -0.19% | 0.18 (0.17–0.22) | $0.34 (0.25–0.45) |
| V9 | base + both filters | 2076 | 98.9 | -8.40% | -2.37 | 14.8% | +46.0% | -17.9% | signal 100% | -0.13% | 0.18 (0.17–0.21) | $0.34 (0.25–0.45) |
| V10 | base + 14:00 exit | 1996 | 95.0 | -7.62% | -2.71 | 17.0% | +32.1% | -15.8% | signal 98%; 14:00 2% | -0.30% | 0.18 (0.17–0.21) | $0.38 (0.28–0.50) |
| V11 | base + spread <= 10% | 2765 | 131.7 | -8.88% | -2.76 | 15.6% | +37.6% | -17.5% | signal 100% | -0.81% | 0.18 (0.17–0.22) | $0.34 (0.25–0.45) |
| V12 | base + spread <= 3% | 2350 | 111.9 | -5.91% | -2.87 | 18.5% | +32.2% | -14.5% | signal 100% | -0.69% | 0.22 (0.18–0.31) | $0.47 (0.41–0.56) |
| V13 | base in the ATM contract | 2794 | 133.0 | -3.61% | -2.91 | 22.3% | +23.3% | -11.3% | signal 100% | -0.34% | — | $1.22 (0.76–1.85) |

No-trade counts (minutes where a version's signal fired but no trade was made): V1 no R/R contract 24, both sides 1; V2 16,
1; V3 6, 0; V4 27, 1; V5 7, 0; V6 4, 0; V7 GEX 47 (+24 no contract, 1 both); V8 premium 995 (+18, 1); V9 premium 984, GEX
49 (+18, 1); V10 both sides 1; V11 no R/R contract 44 (+1); V12 no R/R contract 680 (+1); V13 both sides 1.

Per name, V1 (preview base): SPY 917 trades −7.65% / −$2.80, QQQ 898 −7.20% / −$2.83, IWM 966 −12.54% / −$2.65. V13 (ATM):
SPY 917 −2.21% / −$2.28, QQQ 898 −2.18% / −$2.85, IWM 979 −6.24% / −$3.57.

## What the month shows (descriptive only)

- Every version lost after costs in 2025-03; V1–V6 also lose mid to mid (−0.2% to −19%), so on this month the cost is not
  the only problem: the higher ladders (L2, L3) lose more, with fewer and larger winners.
- L1 trades very often (about 44 a name a session) and is out within minutes; the 1-minute EMA flips with quote noise.
- The best-R/R pick lands at the delta floor: median |delta| 0.18 (IQR 0.17–0.21), premium about $0.34 — the R/R formula
  favours the cheapest contract the 0.15 floor allows. The ATM execution (V13) loses less in % (−3.6%) but about the
  same in $ per trade (−$2.91), on premiums near $1.22.
- The GEX filter barely bit (GEX was negative almost every minute of this month: 47 signals blocked). The premium filter
  removed a quarter of the trades and moved the mean little (−9.20% → −8.50%).

**Integrity (preview only, not the prereg's verifier):** 12 trades (6 V1, 3 V3, 3 V13) re-derived by a separate plain loop
from the raw chain files — the chart's EMA break at entry, the exit minute, the entry ask, the exit bid and the $ —
0 differences. The prereg's full verifier (≥ 30 trades, ≥ 20 no-trade minutes, the ATM strike and the R/R pick
included) runs with the study.
