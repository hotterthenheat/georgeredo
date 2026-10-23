# Compass ICT — exploration (run as pre-registered, 9d6c37e, amended 9dbc0bf)

SPXW 0DTE, 818 full sessions 2022-05-16 → 2026-10-09, the 28 held-out months out. 2 contracts a trade, ask in, bid out,
after fees. % = net ÷ debit. Intervals: 20-session moving-block bootstrap (`audit_lib.session_stats`, 2,000 draws).
**Neither holdout was read.** This report stops at naming the finalists.

| row | trades | per session | projected B | win % | mean %/trade [95%] | mean $/trade [95%] | underlying bp | in 09:30 IMs | top-5 days | qualifies? |
|---|---|---|---|---|---|---|---|---|---|---|
| v0 | 142 | 0.174 | 47 | 37 | −0.8 [−7.7, +7.2] | +48 [−158, +291] | +2.5 | +0.034 | 398% of profit | always a finalist |
| V1 OTE | 94 | 0.115 | 31 | 33 | −3.1 [−11.0, +5.5] | −78 [−270, +133] | +0.2 | +0.014 | total −$7,335 | no: mean, B count |
| V2 out 14:00 | 142 | 0.174 | 47 | 39 | +0.6 [−6.4, +8.4] | +83 [−102, +305] | +2.9 | +0.040 | 214% of profit | no: B count |
| V3 range gate | 84 | 0.103 | 28 | 37 | −6.0 [−14.1, +2.2] | −52 [−278, +207] | +0.4 | −0.012 | total −$4,346 | no: mean, B count |
| V4 5-min | 37 | 0.045 | 12 | 27 | −9.0 [−29.5, +14.6] | −308 [−802, +211] | −5.9 | −0.057 | total −$11,408 | no: mean, underlying, B count |
| A no HTF bias | 357 | 0.436 | 117 | 37 | −2.8 [−7.7, +2.4] | −62 [−211, +92] | −0.2 | +0.002 | total −$21,981 | no: mean, underlying |
| A no sweep | 1,266 | 1.548 | 416 | 41 | −4.1 [−6.3, −1.8] | −86 [−142, −25] | −0.3 | −0.009 | total −$108,450 | no: mean, underlying |
| A no FVG | 202 | 0.247 | 66 | 33 | +2.1 [−7.0, +11.9] | +145 [−129, +478] | +3.3 | +0.039 | 194% of profit | no: B count |
| A no killzones | 245 | 0.300 | 81 | 33 | −0.8 [−6.3, +5.4] | −4 [−156, +175] | +1.3 | +0.019 | total −$949 | no: mean |

Projected B = trades per session × 269 (the full SPXW sessions in the 28 months, counted from file names, Amendment 1).
"Top-5 days" = the five best days' net ÷ the row's total net, where the total is positive.

## Findings

1. **No candidate qualifies. Finalists: v0 alone; k = 1.** Amendment 1's rule needs mean % > 0, underlying > 0 and
   projected B ≥ 80 together. V2 and no-FVG pass the first two and fail the count (47 and 66). No-killzones passes the
   count (81) and fails the mean. No-bias and no-sweep pass the count and fail both returns.
2. **v0 itself cannot reach 80 trades in holdout B** (projected 47). Its B pass is out of reach whatever its edge.
   Holdout A (underlying return, k = 1, interval at 95%) is still open to it.
3. **Nothing separates from zero.** Every interval for mean % straddles zero except no-sweep's, which is below it
   (−4.1% [−6.3, −1.8]). v0's mean $ is positive (+$48) while its mean % is negative: a few dear winners. Without its
   five best days, v0 loses about $20,400 (+$6,852 total, +$27,254 from those five days).
4. **AM beats PM in every row but no-sweep.** v0 AM +3.7% (90 trades) against PM −8.5% (52); V1 PM −11.3% [−21.2, −1.5],
   clear of zero below. The only AM interval clear of zero is no-sweep's, and it is below (−4.3%).
5. **Years: no stable pattern.** v0 is negative 2022–2024 and positive in 2025 (+0.7%) and 2026 (+20.6%, 17 trades,
   [−5.8, +75.8]). No-FVG in 2024 is the one year-row clear of zero above (+22.8% [+1.9, +45.9], 29 trades), one of 45
   year-rows. Four are clear of zero below: V1 2022, V4 2022, no-sweep 2023 and no-sweep 2024.
6. **Forward sessions (2026-10-12 → 10-22, apart):** v0 1 trade, −$885 (−40.6%), the preview's 10-14 trade. Every row
   repeats the preview on those nine days; no-sweep has 17 trades there (−2.9%).

## No-trade reasons and exits (v0)

Of 818 sessions, 702 had no v0 trade. By the furthest stage reached: no sweep of the bias-side level 385, no HTF bias
114, no killzone entry in the 30-bar window 78, sweep without close-back 63, no displacement + MSS 36, no FVG 25,
picker (no delta 0.45–0.60) 1. Exits: TP1 then stop at entry 60%, stop 27%, TP1 then 15:58 flat 7%, TP1 + TP2 5%,
15:58 flat 1%. Every row's reasons and exits, by year and by killzone (with intervals): `out/exploration_tables.md`.

**The 114 no-bias sessions are all within 17 sessions after a history restart.** The HTF history can't read a
held-out month, so it starts again after each one (10 restarts; Amendment 1). If those sessions traded at the rate of the sessions with a bias, v0 would be at about 0.20 a session,
about 54 projected in B. That is still under 80. This is a note only; nothing is
changed.

## How it was run

- `explore.py` runs `ict.py` unchanged (the preview's engine). The one setting it changes per session is the HTF
  history's start: the first session after the latest held-out month, as the preview did from 2026-09-01.
- `guard.py` wraps polars' readers and raises on any file dated ≤ 2022-05-12 or inside the 28 months. Its self-test
  (4 of 4) runs on every start. 15 SPXW sessions were not run: 5 half days, and 10 whose prior session is held out
  (2022-05-13 and the first session after each held-out month). They are listed in `out/explore_sessions.json`.
- `summarize.py` computes the statistics and applies Amendment 1 mechanically (`out/exploration_summary.json`).
- Trades: `out/explore_trades.csv`, `out/forward_trades.csv`. The parquet copies are in the scratchpad
  (`compass_ict_explore/`).

## Integrity

- **`verify_explore.py`** re-derives v0 from the raw files with separate plain-loop code. It has its own readers,
  held-out test, daily swings and bias, sweeps, displacement + MSS, FVG, entry, Black-76 picker on `math.erf`, exits,
  fees and underlying return. Scope: 156 sessions, every session with a v0 trade (116) and 40 seeded no-trade sessions.
  It checked **255 setups** (sweep bar, extreme, displacement bar, FVG zone, entry minute), **142 trades** (strike,
  ask, every exit leg's size, minute, reason and bid; net; bp) and **40 no-trade sessions** (bias and furthest
  stage). **0 differences.** The check catches errors: zeroing the fee or breaking the median made 5 and 7 of 5 test
  sessions differ.
- **`lookahead_explore.py`** rebuilt 10 sessions' trades with every file cut at the entry minute: one per row, then v0
  again, seeded. **0 of 120 entry-time values differ.** The control, cut one minute earlier, differs on 120 of 120
  (the setup is gone).

## Code (sha256)

| file | sha256 |
|---|---|
| `guard.py` | `4f2e4d88587b027c6eef3230ac033311f3e82d78ea7e50921383509b2d41ddbe` |
| `explore.py` | `fc0cc1db2aacfd9e9119adbeb19844b7a17517441ae0c997a61e67cb387497b9` |
| `summarize.py` | `9f0d5000d4ca04c38e3fca676eeb5b4743eef22d690239a587ece43c441fff50` |
| `verify_explore.py` | `795490fb96ccd06402c1d919dffdbc8e273e8163efc5fd67a96f0a0f0faf80bc` |
| `lookahead_explore.py` | `4746d03a956d68175f6a85f9b079b81a2206919da81c2eca1e369e8090e21151` |
| `ict.py` (unchanged) | `2ce600f8f9e864c37439c9f52b39602cbabd75ff9ce12c2d722e618d21699ca3` |
| `lookahead.py` (unchanged) | `a434b231a68c73545af0147126505a04e27b36034af7493c121b5968511b585c` |

**Next step:** holdout A for v0 (k = 1), and only on the owner's go.
