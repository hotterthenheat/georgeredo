# Reproduction of the published T-A lane (13:00 SPY+QQQ ATM straddle, NBBO, close 15:55)

Published (research/thetadata/straddle_nbbo/RESULTS.md): n = 678, mean +$8.60, 95 % CI [-6.07, 22.45], win 64.7 %.

| variant | n | mean $ | 95 % CI (date clusters, 5,000 draws, seed 7) | win | rows equal to the published P&L (±$0.01) |
|---|---|---|---|---|---|
| published strikes, this dataset | 669 | +9.32 | [-5.35, 22.93] | 64.7 % | 669 |
| this study's ATM rule (nearest stored strike to the 12:59 close) | 669 | +9.62 | [-4.94, 23.18] | 65.0 % | 665 |
| published per-row P&L (check) | 678 | +8.60 | [-6.07, 22.45] | 64.7 % | 678 |
| published per-row P&L on the rows of (a) | 669 | +9.32 | [-5.35, 22.93] | 64.7 % | 669 |

Strike differences between the two ATM rules: 13 of 678 rows.  Skips: {'strike_not_stored': 9} (a), {'out_of_band': 9} (b).
Max |row difference| (a vs published): $0.00; rows differing by more than $0.01: 0.
