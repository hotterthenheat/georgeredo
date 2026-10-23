# PREVIEW — 10 sessions, no verdict

Sessions: 2026-10-09, 2026-10-12, 2026-10-13, 2026-10-14, 2026-10-15, 2026-10-16, 2026-10-19, 2026-10-20, 2026-10-21, 2026-10-22. Size 2 contracts; % = net ÷ debit; $ per 2-contract trade after fees.

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

## v0 against 500 random-side draws at its entry times

v0 mean -40.6 % a trade over 1 trades; draws median +10.6 %, 2.5–97.5th -40.6 to +10.6 %; **v0 at the 24th percentile**. Flipped side with no qualifying contract: 0 (left out of that draw's mean).

No bootstrap: with 10 sessions an interval is meaningless. Nothing here is a finalist.
