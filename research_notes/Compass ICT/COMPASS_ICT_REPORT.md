# Compass ICT — PREVIEW — 10 sessions, no verdict

Rule, variants, ablations and splits: `PREREG_COMPASS_ICT.md` (commit 9d6c37e, committed alone before any setup or P&L).
Read-only on files already on disk; no fetch. Neither holdout read; the exploration span not run; nothing selected.

## Inventory
SPY 1-min 2012-06-01 → 2026-10-22, **no pre-market rows in any of 3,687 files** (pre-market high/low dropped). SPX 1-min
2017-06-01 → 2026-10-22, one print a minute (no O/H/L), **no SPX daily file** — daily bars built from the regular-session
prints. SPXW 0DTE 1-min NBBO 2022-05-13 → 2026-10-22 (1,115 files).

As pre-registered: the signal's 1-min OHLC bars are SPY's scaled by SPX/SPY at 09:30 (SPX's own O/H/L are missing); the
underlying return is on SPX's prints. The HTF history starts 2026-09-01 (27 sessions before 10-09, not ~30) so the held-out
2026-08 is not read. Bias: bullish 10-09 → 10-14, bearish 10-15 → 10-22.

## Sessions
2026-10-09, 10-12, 10-13, 10-14, 10-15, 10-16, 10-19, 10-20, 10-21, 10-22 (full sessions, chains to 16:00).

## Results (2 contracts a trade; % = net ÷ debit; after fees, ask in, bid out)
| row | trades | win % | mean %/trade | mean $/trade | avg win $ | avg loss $ | underlying bp | in 09:30 IMs | AM n / mean % | PM n / mean % |
|---|---|---|---|---|---|---|---|---|---|---|
| v0 | 1 | 0 | -40.6 | -885.1 | — | -885.1 | -16.2 | -0.45 | 1 / -40.6 | 0 / — |
| V1 OTE | 1 | 0 | -10.0 | -265.1 | — | -265.1 | -2.0 | -0.05 | 1 / -10.0 | 0 / — |
| V2 out 14:00 | 1 | 0 | -40.6 | -885.1 | — | -885.1 | -16.2 | -0.45 | 1 / -40.6 | 0 / — |
| V3 range gate | 1 | 100 | +6.7 | +174.9 | +174.9 | — | +3.0 | +0.08 | 1 / +6.7 | 0 / — |
| V4 5-min | 1 | 0 | -13.1 | -105.1 | — | -105.1 | +0.2 | +0.01 | 0 / — | 1 / -13.1 |
| A no HTF bias | 4 | 25 | +0.6 | +169.9 | +3454.9 | -925.1 | -3.1 | -0.10 | 3 / +4.2 | 1 / -10.4 |
| A no sweep | 19 | 37 | -2.9 | -114.6 | +1342.0 | -964.3 | -3.3 | -0.09 | 14 / -3.5 | 5 / -1.4 |
| A no FVG | 2 | 50 | -11.4 | -415.1 | +174.9 | -1005.1 | -6.5 | -0.18 | 1 / -37.8 | 1 / +15.1 |
| A no killzones | 4 | 0 | -50.0 | -722.6 | — | -722.6 | -11.4 | -0.32 | 1 / -40.6 | 0 / — |
('A no killzones' also has 3 trades outside both killzones, mean -53.1 %.)

## No-trade reasons and exit reasons (counts over the ten sessions)

- **v0** — sessions with no trade, by the furthest stage reached: no sweep 5, no entry in window 3, no displacement + MSS 1. Setup-level counts: sweep without close-back 10, no sweep 5, no displacement + MSS 4, no entry in window 4, no FVG 3. Exits: stop 1 (100%).
- **V1 OTE** — sessions with no trade, by the furthest stage reached: no sweep 5, no entry in window 3, no displacement + MSS 1. Setup-level counts: sweep without close-back 10, no sweep 5, no displacement + MSS 4, no entry in window 4, no FVG 3. Exits: stop 1 (100%).
- **V2 out 14:00** — sessions with no trade, by the furthest stage reached: no sweep 5, no entry in window 3, no displacement + MSS 1. Setup-level counts: sweep without close-back 10, no sweep 5, no displacement + MSS 4, no entry in window 4, no FVG 3. Exits: stop 1 (100%).
- **V3 range gate** — sessions with no trade, by the furthest stage reached: no sweep 5, no entry in window 3, no displacement + MSS 1. Setup-level counts: sweep without close-back 10, no sweep 5, no displacement + MSS 4, no entry in window 4, no FVG 3. Exits: stop 1 (100%).
- **V4 5-min** — sessions with no trade, by the furthest stage reached: no sweep 5, no displacement + MSS 2, no FVG 1, no entry in window 1. Setup-level counts: no sweep 5, no displacement + MSS 5, sweep without close-back 5, no entry in window 2, no FVG 1. Exits: TP1+stop@entry 1 (100%).
- **A no HTF bias** — sessions with no trade, by the furthest stage reached: no entry in window 4, no sweep 2, sweep without close-back 1. Setup-level counts: sweep without close-back 20, no entry in window 8, no displacement + MSS 7, no FVG 5, no sweep 2, trade open 1. Exits: stop 3 (75%), TP1+flat 15:58 1 (25%).
- **A no sweep** — sessions with no trade, by the furthest stage reached: —. Setup-level counts: no FVG 92, no entry in window 92, session limit 26, trade open 16, picker: delta 0.45-0.60 2. Exits: stop 7 (37%), TP1 5 (26%), TP1+stop@entry 4 (21%), TP2 2 (11%), TP1+TP2 1 (5%).
- **A no FVG** — sessions with no trade, by the furthest stage reached: no sweep 5, picker: delta 0.45-0.60 1, no displacement + MSS 1, entry outside killzone 1. Setup-level counts: sweep without close-back 10, no sweep 5, no displacement + MSS 4, entry outside killzone 4, picker: delta 0.45-0.60 1, trade open 1. Exits: stop 1 (50%), TP1+stop@entry 1 (50%).
- **A no killzones** — sessions with no trade, by the furthest stage reached: no sweep 5, no entry in window 1, no displacement + MSS 1. Setup-level counts: sweep without close-back 10, no sweep 5, no displacement + MSS 4, no FVG 3, no entry in window 1. Exits: stop 3 (75%), TP1+stop@entry 1 (25%).
## v0 against 500 random-side draws
v0 mean -40.6 % a trade over 1 trades; draws median +10.6 %, 2.5–97.5th -40.6 to +10.6 %; **v0 at the 24th percentile**. Flipped side with no qualifying contract: 0 (left out of that draw's mean). With one trade the draws take two values (same side −40.6 %, flipped +10.6 %);
the percentile says nothing. No bootstrap (10 sessions). Every trade: `out/trades.csv`.

## Integrity
- `verify_plain.py`: v0, no-HTF-bias and no-killzones re-derived on all 10 sessions with separate plain-loop code
  (independent readers, swings, sweeps, Black-76 on math.erf, exits, fees): **10 setups, 9 trades, 9 v0 no-trade sessions,
  0 differences** (`out/verify.txt`).
- `lookahead.py`: 3 sessions' trades (v0 10-14 09:50; no-bias 10-15 09:43, 10-16 14:01) rebuilt from files cut at the entry
  minute: **0 of 36 entry-time values differ**; control cut one minute earlier: 36 of 36 differ, setup gone
  (`out/lookahead.txt`).

## Reading
v0 fired once in ten sessions (10-14, a call bought at 09:50, stopped at 09:53: −$885, −40.6 %). Five sessions never swept
the bias-side level, three found no killzone entry, one no displacement + MSS. Too few trades for any reading; the
pre-registered exploration span (2022-05-13 → 2026-10-09 minus the 28 months) is the next step, only on the owner's word.

## Code (sha256)
| file | sha256 |
|---|---|
| `ict.py` | `2ce600f8f9e864c37439c9f52b39602cbabd75ff9ce12c2d722e618d21699ca3` |
| `preview.py` | `d8d9ecca0c6d3ab3a774f3581e393f0ad6f3388ffb7d41790f68fed66b3e8379` |
| `verify_plain.py` | `5b38e0138f250222e76c1de35a523f0f6e45ffe27741bbdb29e94c40adf5b352` |
| `lookahead.py` | `a434b231a68c73545af0147126505a04e27b36034af7493c121b5968511b585c` |
