## 10. Integrity: a plain-loop re-derivation

`verify_plain.py` (does not import the engine; raw parquet, plain Python loops, its own Black-Scholes bisection) re-derived 14 trades drawn (seed 20261023) one per config × exit × name: the rule at the entry minute, no earlier allowed minute where the rule and a contract would have entered, the contract, R, every exit leg, the bids and the net. **Differences: 0.**

| config · exit | name | session | entry | contract | exit | net $ | check |
|---|---|---|---|---|---|---|---|
| A · X1 | SPY | 2026-10-16 | 13:04 | put 765.0 | +1R at minute 223 | +86.63 | 0 differences |
| A · X3 | QQQ | 2026-10-14 | 13:51 | put 728.0 | runner at minute 285 | -38.37 | 0 differences |
| A · X2 | SPY | 2026-10-15 | 09:47 | put 766.0 | stop at minute 41 | -73.37 | 0 differences |
| B · X1 | SPXW | 2026-10-16 | 11:51 | put 7710.0 | +1R at minute 145 | +297.45 | 0 differences |
| A · X4 | QQQ | 2026-10-16 | 12:31 | put 716.0 | runner at minute 255 | +1191.25 | 0 differences |
| A · X3 | IWM | 2026-10-12 | 13:35 | put 278.0 | runner at minute 270 | -10.37 | 0 differences |
| B · X3 | IWM | 2026-10-15 | 11:11 | call 274.0 | stop at minute 113 | -23.37 | 0 differences |
| A · X3 | SPY | 2026-10-16 | 14:17 | put 763.0 | runner at minute 345 | -23.37 | 0 differences |
| B · X2 | SPXW | 2026-10-12 | 12:18 | call 7815.0 | stop at minute 172 | -92.55 | 0 differences |
| A · X3 | SPXW | 2026-10-12 | 14:32 | put 7800.0 | stop at minute 313 | -127.55 | 0 differences |
| A · X1 | QQQ | 2026-10-14 | 09:58 | put 736.0 | +1R at minute 123 | +105.63 | 0 differences |
| B · X4 | IWM | 2026-10-15 | 11:11 | call 274.0 | stop at minute 113 | -233.75 | 0 differences |
| A · X1 | IWM | 2026-10-14 | 11:58 | put 272.0 | +1R at minute 167 | +36.63 | 0 differences |
| B · X3 | SPXW | 2026-10-12 | 15:18 | put 7800.0 | stop at minute 349 | -82.55 | 0 differences |
