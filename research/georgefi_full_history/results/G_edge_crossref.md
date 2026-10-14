# GeorgeFi ledger cross-reference: direction after his entries, and day selection (2026-10-14)

Code: `code/edge_crossref.py`. Source: `normalized/trades.csv` (1,149 ledger rows; 742 on index/ETF roots with entry and exit timestamps; single names excluded for lack of minute bars). Underlying: ThetaData 1-minute bars (SPXW → SPY, NDXP → QQQ, RUTW → IWM as proxies). The two questions the earlier reports did not answer directly: does the underlying move his way after his entries, and are the days he trades better than other days for the same trade?

## 1. Direction: signed underlying return after the entry (bp), with time-matched random minutes on the same symbol and day

| cell | n | +15 min [CI] | hit 15 | +30 min [CI] | vs random 30 [CI] | over his hold [CI] | hit hold | vs random, hold [CI] |
|---|---|---|---|---|---|---|---|---|
| all index/ETF trades | 735 | +4.5 [+1.1, +8.3] | 59 % | +3.0 [-1.8, +7.7] | +1.0 [-3.4, +5.0] | +2.8 [+1.1, +4.4] | 64 % | +2.3 [+0.7, +3.7] |
| epoch 1 | 285 | +12.5 [+5.0, +20.3] | 71 % | +9.4 [-1.9, +20.2] | +6.4 [-3.7, +15.6] | +7.2 [+4.6, +9.9] | 80 % | +6.6 [+4.3, +9.0] |
| epoch 2 | 450 | -0.6 [-2.1, +1.0] | 52 % | -1.1 [-3.3, +0.9] | -2.4 [-4.7, -0.3] | +0.1 [-1.3, +1.3] | 53 % | -0.5 [-1.7, +0.7] |
| epoch 1 0DTE | 285 | +12.5 [+5.0, +20.3] | 71 % | +9.4 [-1.9, +20.2] | +6.4 [-3.7, +15.6] | +7.2 [+4.6, +9.9] | 80 % | +6.6 [+4.3, +9.0] |
| epoch 2 0DTE | 431 | -0.7 [-2.2, +0.9] | 52 % | -1.4 [-3.6, +0.7] | -2.7 [-4.9, -0.6] | -0.4 [-1.5, +0.6] | 53 % | -0.9 [-2.0, +0.2] |
| book v2.0.0-ict | 677 | +4.8 [+1.1, +8.9] | 60 % | +3.3 [-1.6, +8.3] | +1.2 [-3.4, +5.7] | +3.1 [+1.3, +4.9] | 65 % | +2.6 [+0.9, +4.2] |
| book trade_now_v1 | 51 | +0.6 [-2.3, +3.6] | 53 % | -0.9 [-4.1, +2.3] | -1.1 [-4.8, +2.7] | -1.5 [-5.5, +2.4] | 49 % | -1.9 [-5.4, +1.4] |
| calls | 354 | +4.2 [+0.0, +8.2] | 60 % | +4.2 [-0.4, +8.9] | +2.2 [-2.7, +7.0] | +2.1 [+0.1, +3.7] | 65 % | +1.2 [-0.7, +2.8] |
| puts | 381 | +4.8 [+0.1, +11.2] | 59 % | +1.8 [-5.7, +10.5] | -0.1 [-6.5, +6.7] | +3.5 [+0.8, +6.3] | 62 % | +3.3 [+0.8, +5.6] |
| root SPY | 159 | +2.4 [-1.7, +5.5] | 62 % | -1.1 [-5.4, +2.9] | -2.7 [-6.7, +0.8] | +1.1 [-0.9, +2.8] | 65 % | +1.1 [-1.1, +2.7] |
| root QQQ | 167 | +4.6 [-2.2, +13.4] | 53 % | +1.8 [-9.9, +13.6] | +0.3 [-10.1, +11.6] | +2.1 [-0.9, +4.9] | 61 % | +2.1 [-0.8, +4.9] |
| root IWM | 99 | +14.8 [-0.9, +29.8] | 66 % | +14.6 [-3.9, +31.2] | +6.1 [-11.0, +20.4] | +11.3 [+3.2, +17.3] | 75 % | +7.4 [-0.4, +13.3] |
| root SPXW | 259 | +2.4 [+0.8, +4.0] | 59 % | +2.2 [+0.2, +4.1] | +2.4 [-0.3, +4.9] | +1.3 [-0.2, +2.6] | 62 % | +1.4 [-0.2, +2.7] |

## 2. Day selection: the same trade (contract rule 0.30–0.60 delta nearest 0.45, same entry minute, direction and hold; ask in / bid out, $0.70/contract/side) on his day vs on 5 random sessions within ±45 days

Raw means are dominated by a few SPXW random-day outliers (an index contract on a large-move day is worth thousands), so the table reports medians and 2–98 % winsorized means; CIs clustered by day.

| cell | n | median own | median random day | winsorized mean own | winsorized mean random day | difference [CI] | win own | win random |
|---|---|---|---|---|---|---|---|---|
| epoch 1 ETF roots (SPY/QQQ/IWM) | 217 | +15.6 | -3.6 | +13.7 | -2.1 | +15.8 [+7.1, +23.0] | 74 % | 39 % |
| epoch 1 SPXW | 59 | +98.6 | -43.4 | +118.3 | -38.5 | +156.8 [+88.7, +245.7] | 80 % | 34 % |
| epoch 2 ETF roots (SPY/QQQ/IWM) | 186 | -3.4 | -3.3 | -6.5 | -3.1 | -3.4 [-7.4, -0.0] | 41 % | 40 % |
| epoch 2 SPXW | 199 | -21.4 | -19.4 | -3.2 | -1.5 | -1.7 [-56.6, +49.7] | 46 % | 40 % |
| all ETF roots | 403 | +6.6 | -3.4 | +4.3 | -2.6 | +6.9 [+1.1, +12.3] | 59 % | 40 % |

## 3. Reading

**Epoch 1 (2026-01-20 → 02-27, 285 index/ETF trades)** shows a directional edge: the underlying moves his way by +12.5 bp in the 15 minutes after the entry [+5.0, +20.3], hit rate 71 %; over his own holds +7.2 bp [+4.6, +9.9], hit rate 80 %, +6.6 bp better than time-matched random minutes [+4.3, +9.0]; and his days are worth about +$48 per contract more than random days for the identical trade. **Epoch 2 (2026-03-02 → 10-13, 450 trades)** shows none of it: -0.6 bp at 15 minutes [-2.1, +1.0], hit rate 52 %; over his holds +0.1 bp, hit rate 53 %; -2.4 bp *worse* than random at 30 minutes [-4.7, -0.3]; day selection on the ETF roots within noise.

The two epochs differ in exactly the way `RESULTS_NBBO.md` found for the fills: Epoch 1 is the epoch whose reported entries sit at or below the bid 33.5 % of the time and whose exits sit at or above the ask 37.2 % of the time, with 27 % of same-minute repeats priced below the minute's lowest bid — a record whose prices (and therefore whose timestamps, which are what this cross-reference relies on) were not raw executions. A ledger whose entry time is written when the trade is closed, or whose entry is matched to a favourable second, would show precisely this pattern: strong "foresight" at 15 minutes that disappears in the epoch recorded under live conditions. Epoch 2, where the fills are more often within the NBBO and the record was produced day by day, has no directional information at any horizon, which agrees with G2 (MFE percentile 48 vs random) and with the 0-of-144 reconstruction backtest.

**What his edge is, as far as the data can say.** (1) In the only epoch whose prices are consistent with the market, there is no entry or direction edge and no day-selection edge; his executable result there is −$42 per trade (G1). (2) The apparent edge in Epoch 1 is inseparable from the fill anomaly of the same rows and cannot be credited to a signal. (3) The one component that holds up across both epochs is the exit discipline — breakeven lock, trailing give-back, fast time stop, no holding into the close — which loses less than any mechanical exit on the same entries (BACKTEST_RESULTS.md §2, Signal Research T3); it reduces losses, it does not create expectancy. Nothing in his record offers an entry rule worth porting; the exit layer is already the default risk layer in the Compass specification.
