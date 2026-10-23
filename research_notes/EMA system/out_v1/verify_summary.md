## 10. Integrity: a plain-loop re-derivation

`verify_plain_v1.py` (imports neither engine; raw parquet, plain Python loops, its own Black-Scholes bisection) re-derived 32 headline trades, one drawn (seed 20261023) per config × exit × stream × venue present: the rule at the entry minute, no earlier allowed minute (09:45–13:29) where the rule and a contract in either venue would have entered, both venues' contracts under the 3% cap and the cost-share choice, R, every exit leg with the 14:00 flat, the bids and the net. **Differences: 0.**

| config · exit | stream | venue | session | entry | contract | exit | net $ | check |
|---|---|---|---|---|---|---|---|---|
| A · X1 | IWM | IWM | 2026-02-02 | 12:50 | call 263.0 | stop at minute 219 | -17.37 | 0 differences |
| A · X1 | QQQ | QQQ | 2025-07-25 | 10:49 | call 566.0 | stop at minute 85 | -23.37 | 0 differences |
| A · X1 | S&P | SPXW | 2026-02-03 | 10:25 | put 6925.0 | stop at minute 81 | -872.55 | 0 differences |
| A · X1 | S&P | SPY | 2026-02-05 | 10:01 | put 679.0 | +1R at minute 42 | +79.63 | 0 differences |
| A · X2 | IWM | IWM | 2025-07-25 | 10:04 | put 222.5 | stop at minute 74 | -28.37 | 0 differences |
| A · X2 | QQQ | QQQ | 2026-02-05 | 09:58 | put 600.0 | 14:00 at minute 270 | -80.37 | 0 differences |
| A · X2 | S&P | SPXW | 2026-02-06 | 10:22 | call 6880.0 | +2R at minute 158 | +1087.45 | 0 differences |
| A · X2 | S&P | SPY | 2025-07-25 | 10:35 | call 636.0 | +2R at minute 163 | +17.63 | 0 differences |
| A · X3 | IWM | IWM | 2026-02-03 | 12:06 | put 262.0 | 14:00 at minute 270 | +227.63 | 0 differences |
| A · X3 | QQQ | QQQ | 2025-07-22 | 10:25 | put 560.0 | stop at minute 61 | -38.37 | 0 differences |
| A · X3 | S&P | SPXW | 2026-07-13 | 12:17 | put 7530.0 | runner at minute 220 | +137.45 | 0 differences |
| A · X3 | S&P | SPY | 2025-07-25 | 10:35 | call 636.0 | runner at minute 130 | +1.63 | 0 differences |
| A · X4 | IWM | IWM | 2026-02-02 | 12:50 | call 263.0 | runner at minute 215 | -113.75 | 0 differences |
| A · X4 | QQQ | QQQ | 2026-02-03 | 10:24 | put 618.0 | runner at minute 80 | -853.75 | 0 differences |
| A · X4 | S&P | SPXW | 2026-02-04 | 13:01 | put 6850.0 | runner at minute 235 | -4025.55 | 0 differences |
| A · X4 | S&P | SPY | 2026-02-05 | 10:01 | put 679.0 | runner at minute 110 | +684.25 | 0 differences |
| B · X1 | IWM | IWM | 2026-02-02 | 12:50 | call 263.0 | stop at minute 219 | -17.37 | 0 differences |
| B · X1 | QQQ | QQQ | 2026-02-05 | 11:10 | put 594.0 | stop at minute 106 | -79.37 | 0 differences |
| B · X1 | S&P | SPXW | 2026-02-06 | 10:22 | call 6880.0 | +1R at minute 77 | +597.45 | 0 differences |
| B · X1 | S&P | SPY | 2025-07-25 | 10:35 | call 636.0 | +1R at minute 72 | +10.63 | 0 differences |
| B · X2 | IWM | IWM | 2026-02-06 | 10:12 | call 262.0 | +2R at minute 131 | +78.63 | 0 differences |
| B · X2 | QQQ | QQQ | 2026-02-03 | 13:14 | put 613.0 | 14:00 at minute 270 | +73.63 | 0 differences |
| B · X2 | S&P | SPXW | 2025-07-21 | 10:21 | call 6335.0 | 14:00 at minute 270 | -287.55 | 0 differences |
| B · X2 | S&P | SPY | 2025-07-25 | 10:35 | call 636.0 | +2R at minute 163 | +17.63 | 0 differences |
| B · X3 | IWM | IWM | 2026-02-04 | 13:01 | put 257.0 | stop at minute 216 | -25.37 | 0 differences |
| B · X3 | QQQ | QQQ | 2026-07-14 | 11:05 | call 721.0 | runner at minute 140 | -1.37 | 0 differences |
| B · X3 | S&P | SPXW | 2026-07-13 | 12:17 | put 7530.0 | runner at minute 220 | +137.45 | 0 differences |
| B · X3 | S&P | SPY | 2025-07-25 | 10:35 | call 636.0 | runner at minute 130 | +1.63 | 0 differences |
| B · X4 | IWM | IWM | 2026-02-02 | 12:50 | call 263.0 | runner at minute 215 | -113.75 | 0 differences |
| B · X4 | QQQ | QQQ | 2025-07-22 | 10:25 | put 560.0 | stop at minute 61 | -383.75 | 0 differences |
| B · X4 | S&P | SPXW | 2026-02-04 | 13:01 | put 6850.0 | runner at minute 235 | -4025.55 | 0 differences |
| B · X4 | S&P | SPY | 2025-07-25 | 10:35 | call 636.0 | runner at minute 130 | +34.25 | 0 differences |
