# After-hours exercise risk of the hold-to-expiry trades, 2025-10-13 → 2026-10-21

Written by `afterhours.py` in this folder. It reads the replay's rows (`data_recorder/paper_backtest`, read only), the official closes as `run_audit.official_closes()` builds them (Theta EOD, UW daily `r` rows incl. `data/official_closes/`), UW's 1-minute answers already on disk (`bt/cache`, `audit_fresh_cache`, `bt/probe`, `evidence/provider_tests` under the scratch folder, and `data_recorder/ohlc_1m/`), UW's daily `po` rows, the next sessions' 1-minute bars (`$PAPER_PARQUET_ROOT/data/underlying`) and the 15:58 quotes the audit cached (`out/quotes_1558_cache.parquet`). It calls no vendor. The UW 1-minute answers missing from disk were fetched once, with the owner's leave, by `fetch_postmarket_1m.py` (16 name-sessions, one call at a time, kept as answered under `data/postmarket_1m/<T>/<D>.json.gz`); a re-run reads those files and makes no call. Exercise / assignment fee: ${a.fee_ex:.2f} a contract (`--fee-ex`). Bootstraps: moving blocks of {BLOCK} sessions, {A.BOOT_N:,} draws, `audit_lib.block_draws(n, 20, seed=20261016)`, the same draws for every series of a candidate-period (so differences are paired). Periods are never pooled.

## Summary

- **Decision-price coverage** (name-sessions with the last post-market bar to 17:30): period ii's overlap 496/496 (UW 1-minute answers already on disk, `bt/cache`), period iii 16/16 (16 fetched for this study into `data/postmarket_1m/`). The next session's 09:30 open is missing only for 2026-10-21 (2026-10-22 is not on disk), so that session is left out of every case table and period iii has 7 sessions with a next open — too few for a 20-session block interval (60 needed): there the rule is decided by its first clause alone where the mean under (b) is ≤ 0, and left undecided where it is positive. UW answered every name-session asked of it.
- **fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30), period ii** (248 sessions with a next open): (0) +18.25 a trade, (a) +67.54, a−0 +49.29 [+0.25, +79.38]; (b) +22.52 [-20.07, +52.89], (c) +25.78, b−a -45.02 [-71.70, -11.93]; 15:58 exit -13.13; rule: **DROP** (mean under (b) +22.52 a trade, block-20 [-20.07, +52.89]).
- **fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30), period iii** (7 sessions with a next open): (0) +40.51 a trade, (a) +117.26, a−0 +76.75 —; (b) -41.81 —, (c) -41.81, b−a -159.07 —; 15:58 exit +3.39; rule: **DROP** (mean under (b) -41.81 a trade ≤ 0 — the rule's first clause decides alone; the block-20 interval cannot be formed on 7 sessions (needs 60)).
- **condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00), period ii** (248 sessions with a next open): (0) +7.10 a trade, (a) +13.27, a−0 +6.17 [-11.71, +20.22]; (b) +3.84 [-19.94, +22.74], (c) +10.21, b−a -9.42 [-21.59, +1.37]; 15:58 exit -6.29; rule: **DROP** (mean under (b) +3.84 a trade, block-20 [-19.94, +22.74]).
- **condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00), period iii** (7 sessions with a next open): (0) +20.69 a trade, (a) +48.79, a−0 +28.10 —; (b) +43.14 —, (c) +43.14, b−a -5.65 —; 15:58 exit +2.18; rule: **UNDECIDED** (mean under (b) +43.14 a trade > 0, and the block-20 interval the second clause needs cannot be formed on 7 sessions (needs 60)).
- **SPY on 2025-04-09.** Theta EOD's 548.62 is not confirmed by any second source on disk: SPX's official close (Cboe and FRED, 5456.90) anchored on SPY's 15:59 bar gives 543.72, the SPY/SPX ratio of the sessions around it 543.52, IVV and VOO anchored 543.57 and 542.97; 548.62 is also the EOD row's high of the day (section 5).
- **Pre-2025-10-13 sessions with |official − 15:59| > $0.25:** 22 name-sessions, every one with its official source (Theta EOD) and the second sources on disk (section 6).

The decision rule was fixed by the owner before any of these numbers were read: *"if a candidate's mean under (b) is ≤ 0 or its block-20 interval includes zero, drop it as a SPY/QQQ hold-to-expiry strategy."* Its measure was fixed in the code before the run (the mean $ a trade, Σ ÷ Σ, AUDIT.md's headline measure, with its 20-session block-bootstrap interval); it is applied mechanically below and not reinterpreted.

## 1. Post-market bars: what is on disk

UW's daily bars (`ohlc__1d`, `data/official_closes/uw_ohlc_1d_*.parquet`) carry ONE post-market row a session (`market_time = po`: the open, high, low and close of 16:00–20:00). They cannot give "the last bar at or before 17:30" and are not used for it. Minute bars with `po` rows exist on disk only as UW 1-minute answers (`/api/stock/{T}/ohlc/1m?date=D`, `start_time`/`end_time` in UTC): the backtest fetch cache (`bt/cache`, 2025-05-22 → 2026-10-09), the audit's fresh cache, two probe folders, the recorder's `data_recorder/ohlc_1m/{SPY,QQQ}/` (2026-10-21 only, taken at 17:24 New York) and, for period iii, the answers fetched for this study (`data/postmarket_1m/`). Theta's 1-minute underlying files stop at the 16:00 bar. A disk-wide search for other minute post-market files found none.

Rules applied: a bar belongs to session D when its start is on D in New York (UW files a winter session by its UTC date, so the evening before rides along in the file — 19:00–20:00 EST rows dated D−1 — and is left out); the decision price is the close of the last `po` bar ENDING at or before 17:30 New York; a file must show it was taken after 17:30 (a bar of D ending after 17:30, or its fetch time) — otherwise the last bar to 17:30 is not known and the session has no decision price.

| period | name | sessions | UW daily `po` row | UW 1-minute answer on disk | decision price (last `po` bar ≤ 17:30) | next session's 09:30 open | decision price inside the daily `po` range |
|---|---|---|---|---|---|---|---|
| ii (2025-10-13 → 2026-10-09) | SPY | 248 | 248 | 248 | 248 (100.0%) | 248 | 248 / 248 |
| ii (2025-10-13 → 2026-10-09) | QQQ | 248 | 248 | 248 | 248 (100.0%) | 248 | 248 / 248 |
| iii (2026-10-12 → 2026-10-21) | SPY | 8 | 8 | 8 | 8 (100.0%) | 7 | 8 / 8 |
| iii (2026-10-12 → 2026-10-21) | QQQ | 8 | 8 | 8 | 8 (100.0%) | 7 | 8 / 8 |

Where the decision bar ends: 17:30 382, 17:29 81, 17:28 28, 17:27 11, 17:25 4, 17:23 3, 17:26 2, 17:22 1 (a bar ending before 17:30 is the last trade-bearing minute before the cut-off). Name-sessions with two UW files whose decision prices disagree: 0; bars held by two files of one name-session: 4002, closes differing: 1 (SPY 2026-10-21, the bar 17:24–17:25: the recorder took it at 17:24:25, mid-minute, 772.9608 against the finished bar's 772.98; not the decision bar).

**Every session without a decision price** (0 name-sessions):

none.

**Sessions without a next-session 09:30 open** (2 name-sessions; their trades are left out of every case table, (0) included, so every comparison is on the same trades): SPY 2026-10-21 — no 09:30 bar for 2026-10-22 on disk (SPY/2026-10-22.parquet); QQQ 2026-10-21 — no 09:30 bar for 2026-10-22 on disk (QQQ/2026-10-22.parquet).


## 2. The cases

Every trade keeps the replay's entry (each leg at its NBBO, $0.65 × 4 contracts at the open). C = the official close; D = the decision price; O = the next session's 09:30 bar open (Theta 1-minute, `$PAPER_PARQUET_ROOT/data/underlying/<name>/<next>.parquet`). "In the money" = by $0.01 or more. An exercised or assigned leg delivers 100 shares a contract at its strike, the net stock marked at O: + (O − K) a long call, + (K − O) a long put, the negatives for a short; a leg not exercised expires worthless.

- **(0) current**: every leg at intrinsic on C (the audit's re-settled P&L; equal to it on 2231 of 2231 trades).
- **(a) exercise by exception on C**: every leg in the money at C exercised or assigned. a − 0 = net shares × (O − C): the overnight gap alone.
- **(b) counterparty adverse selection**: our longs by exception on C; each short assigned iff in the money at D (the holder decides after hours on what we do not see). b − a isolates it.
- **(c) both rational at D**: our longs exercised and the shorts assigned iff in the money at D.
- Fee: $0.00 a contract exercised or assigned. Not modeled: the stock commission at the next open, borrow on short stock, margin interest.

## 3. P&L under the cases, by candidate and period

Session sums (a session's trades added; zero on a session with no trade); mean $ a trade = Σ ÷ Σ; intervals are 20-session moving-block percentile intervals (— where a period has fewer than 60 sessions: the block intervals need more sessions). Universe A: sessions with a next open for every name the candidate trades; universe B: those that also have a decision price for every name.

| candidate | period | universe | sessions | trades | series | mean $ a trade | block-20 CI (trade) | mean $ a session | block-20 CI (session) | trades differing from (0) | total $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | A | 248 | 987 | (0) intrinsic at C | +18.25 | [+11.76, +25.13] | +72.64 | [+46.67, +100.20] | — | +18,014 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | A | 248 | 987 | (a) exception on C | +67.54 | [+15.26, +98.40] | +268.79 | [+60.80, +392.50] | 98.0% | +66,660 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | A | 248 | 987 | 15:58 exit, NBBO (982 with a value) | -13.13 | [-18.35, -8.58] | -52.01 | [-72.27, -34.14] | — | -12,898 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | 248 | 987 | (0) intrinsic at C | +18.25 | [+11.76, +25.13] | +72.64 | [+46.67, +100.20] | — | +18,014 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | 248 | 987 | (a) exception on C | +67.54 | [+15.26, +98.40] | +268.79 | [+60.80, +392.50] | 98.0% | +66,660 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | 248 | 987 | (b) shorts at D | +22.52 | [-20.07, +52.89] | +89.62 | [-79.77, +209.99] | 98.5% | +22,226 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | 248 | 987 | (c) both at D | +25.78 | [-17.35, +58.54] | +102.60 | [-68.63, +232.95] | 98.9% | +25,445 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | 248 | 987 | 15:58 exit, NBBO (982 with a value) | -13.13 | [-18.35, -8.58] | -52.01 | [-72.27, -34.14] | — | -12,898 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | A | 7 | 28 | (0) intrinsic at C | +40.51 | — | +162.03 | — | — | +1,134 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | A | 7 | 28 | (a) exception on C | +117.26 | — | +469.03 | — | 96.4% | +3,283 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | A | 7 | 28 | 15:58 exit, NBBO (28 with a value) | +3.39 | — | +13.57 | — | — | +95 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | 7 | 28 | (0) intrinsic at C | +40.51 | — | +162.03 | — | — | +1,134 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | 7 | 28 | (a) exception on C | +117.26 | — | +469.03 | — | 96.4% | +3,283 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | 7 | 28 | (b) shorts at D | -41.81 | — | -167.26 | — | 100.0% | -1,171 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | 7 | 28 | (c) both at D | -41.81 | — | -167.26 | — | 100.0% | -1,171 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | 7 | 28 | 15:58 exit, NBBO (28 with a value) | +3.39 | — | +13.57 | — | — | +95 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | A | 248 | 1176 | (0) intrinsic at C | +7.10 | [+2.00, +11.09] | +33.67 | [+9.38, +52.74] | — | +8,349 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | A | 248 | 1176 | (a) exception on C | +13.27 | [-6.31, +28.83] | +62.91 | [-29.51, +138.30] | 19.3% | +15,601 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | A | 248 | 1176 | 15:58 exit, NBBO (1170 with a value) | -6.29 | [-10.65, -3.55] | -29.66 | [-50.47, -16.50] | — | -7,355 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | 248 | 1176 | (0) intrinsic at C | +7.10 | [+2.00, +11.09] | +33.67 | [+9.38, +52.74] | — | +8,349 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | 248 | 1176 | (a) exception on C | +13.27 | [-6.31, +28.83] | +62.91 | [-29.51, +138.30] | 19.3% | +15,601 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | 248 | 1176 | (b) shorts at D | +3.84 | [-19.94, +22.74] | +18.23 | [-98.03, +108.10] | 27.1% | +4,521 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | 248 | 1176 | (c) both at D | +10.21 | [-9.71, +26.24] | +48.40 | [-46.15, +125.40] | 28.7% | +12,002 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | 248 | 1176 | 15:58 exit, NBBO (1170 with a value) | -6.29 | [-10.65, -3.55] | -29.66 | [-50.47, -16.50] | — | -7,355 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | A | 7 | 31 | (0) intrinsic at C | +20.69 | — | +91.63 | — | — | +641 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | A | 7 | 31 | (a) exception on C | +48.79 | — | +216.06 | — | 12.9% | +1,512 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | A | 7 | 31 | 15:58 exit, NBBO (31 with a value) | +2.18 | — | +9.66 | — | — | +68 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | 7 | 31 | (0) intrinsic at C | +20.69 | — | +91.63 | — | — | +641 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | 7 | 31 | (a) exception on C | +48.79 | — | +216.06 | — | 12.9% | +1,512 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | 7 | 31 | (b) shorts at D | +43.14 | — | +191.06 | — | 29.0% | +1,337 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | 7 | 31 | (c) both at D | +43.14 | — | +191.06 | — | 29.0% | +1,337 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | 7 | 31 | 15:58 exit, NBBO (31 with a value) | +2.18 | — | +9.66 | — | — | +68 |

**Paired differences** (per trade and per session; the tails are of the per-trade and per-session differences):

| candidate | period | universe | difference | mean $ a trade | block-20 CI (trade) | mean $ a session | block-20 CI (session) | trades affected | per trade p5 / p1 / worst | per session p5 / p1 / worst |
|---|---|---|---|---|---|---|---|---|---|---|
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | A | a − 0 | +49.29 | [+0.25, +79.38] | +196.15 | [+0.98, +315.73] | 98.0% (967) | -804 / -1,135 / -2,012 | -2,185 / -3,915 / -4,190 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | a − 0 | +49.29 | [+0.25, +79.38] | +196.15 | [+0.98, +315.73] | 98.0% (967) | -804 / -1,135 / -2,012 | -2,185 / -3,915 / -4,190 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | b − a | -45.02 | [-71.70, -11.93] | -179.17 | [-285.65, -47.28] | 17.2% (170) | -713 / -1,452 / -3,220 | -2,214 / -4,002 / -4,572 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | B | c − b | +3.26 | [-5.35, +14.08] | +12.98 | [-21.31, +55.93] | 2.2% (22) | +0 / -9 / -1,381 | +0 / -351 / -2,662 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | A | a − 0 | +76.75 | — | +307.00 | — | 96.4% (27) | -798 / -1,024 / -1,040 | -781 / -793 / -796 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | a − 0 | +76.75 | — | +307.00 | — | 96.4% (27) | -798 / -1,024 / -1,040 | -781 / -793 / -796 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | b − a | -159.07 | — | -636.29 | — | 21.4% (6) | -1,138 / -1,730 / -1,890 | -2,097 / -2,371 / -2,440 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | B | c − b | +0.00 | — | +0.00 | — | 0.0% (0) | +0 / +0 / +0 | +0 / +0 / +0 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | A | a − 0 | +6.17 | [-11.71, +20.22] | +29.24 | [-55.02, +95.98] | 19.3% (227) | -162 / -492 / -1,717 | -654 / -1,957 / -6,868 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | a − 0 | +6.17 | [-11.71, +20.22] | +29.24 | [-55.02, +95.98] | 19.3% (227) | -162 / -492 / -1,717 | -654 / -1,957 / -6,868 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | b − a | -9.42 | [-21.59, +1.37] | -44.67 | [-102.47, +6.72] | 12.4% (146) | -128 / -595 / -907 | -524 / -2,015 / -3,935 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | B | c − b | +6.36 | [+0.65, +12.88] | +30.17 | [+3.03, +60.69] | 3.4% (40) | +0 / -90 / -736 | +0 / -514 / -736 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | A | a − 0 | +28.10 | — | +124.43 | — | 12.9% (4) | +0 / -102 / -145 | -102 / -136 / -145 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | a − 0 | +28.10 | — | +124.43 | — | 12.9% (4) | +0 / -102 / -145 | -102 / -136 / -145 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | b − a | -5.65 | — | -25.00 | — | 16.1% (5) | -15 / -85 / -115 | -123 / -165 / -175 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | B | c − b | +0.00 | — | +0.00 | — | 0.0% (0) | +0 / +0 / +0 | +0 / +0 / +0 |

**After-hours range (upper bound, labelled).** The share of trades whose UW daily `po` range (16:00–20:00 high and low, with C) took a short strike across the money — wider than the 17:30 window, so an upper bound on the trades whose assignment could turn after the close — beside the share whose short-leg in-the-money state actually differs between C and D:

| candidate | period | daily `po` range crosses a short strike (upper bound) | short leg ITM at C ≠ ITM at D |
|---|---|---|---|
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | 56.6% of 987 | 17.2% of 987 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | 71.4% of 28 | 21.4% of 28 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | 51.5% of 1176 | 12.4% of 1176 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | 41.9% of 31 | 16.1% of 31 |

## 4. The decision rule, applied

Fixed by the owner before the numbers were read: if a candidate's mean under (b) is ≤ 0 or its 20-session block-bootstrap interval includes zero, it is dropped as a SPY/QQQ hold-to-expiry strategy. Measure fixed in the code before the run: mean $ a trade (Σ ÷ Σ) and its block-20 interval on universe B. A period with a decision price on fewer than 50% of its sessions is not judged.

Disclosure: where the block-20 interval cannot be formed (period iii, 7 sessions), the first version of this script marked the period "not applied". After the period-iii figures were on screen it was changed to apply the rule's two clauses as written — a mean ≤ 0 under (b) decides DROP on its own; a positive mean whose interval cannot be formed is UNDECIDED. Period ii's verdicts were not touched by the change. A reader who holds that no verdict should be read off 7 sessions should read period iii as not applied for both candidates.

- **fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) — period ii (2025-10-13 → 2026-10-09): DROP.** mean under (b) +22.52 a trade, block-20 [-20.07, +52.89]. Session-mean check: +89.62 [-79.77, +209.99] → DROP (the same).
- **fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) — period iii (2026-10-12 → 2026-10-21): DROP.** mean under (b) -41.81 a trade ≤ 0 — the rule's first clause decides alone; the block-20 interval cannot be formed on 7 sessions (needs 60).
- **condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) — period ii (2025-10-13 → 2026-10-09): DROP.** mean under (b) +3.84 a trade, block-20 [-19.94, +22.74]. Session-mean check: +18.23 [-98.03, +108.10] → DROP (the same).
- **condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) — period iii (2026-10-12 → 2026-10-21): UNDECIDED.** mean under (b) +43.14 a trade > 0, and the block-20 interval the second clause needs cannot be formed on 7 sessions (needs 60).

## 5. SPY on 2025-04-09: 548.62 against the second sources

| source | value | note |
|---|---|---|
| Theta EOD (`stock_eod`, the official close the audit uses) | close 548.62; open 493.5, high 548.62, low 493.05; last trade stamped 2025-04-09 17:16:04.861000-04:00; NBBO at the report 546.03 / 546.2 | the source under test |
| Theta 1-minute SPY, 15:59 bar close | 543.37 | the replay's settle |
| Theta 1-minute SPY, 16:00 bar | 543.48 (1310 shares, 1 trade(s)); highest 1-minute high of the day 546.33 | same vendor; one print |
| SPX official close, Cboe (`spx/cboe_spx.csv`) / FRED SP500 | 5456.90 / 5456.90 | independent of Theta |
| SPX print stamped 16:00 (Theta index file) | 5453.35 |  |
| SPY implied: 15:59 bar × SPX official ÷ SPX 16:00 print | **543.72** | SPX close independent |
| SPY implied: SPY/SPX close ratio of the sessions within 8 days (median) × SPX official | **543.52** (ratios 2025-04-01 0.09959, 2025-04-02 0.09955, 2025-04-03 0.09945, 2025-04-04 0.09958, 2025-04-07 0.09964, 2025-04-08 0.09964, 2025-04-10 0.09958, 2025-04-11 0.09955, 2025-04-14 0.09973, 2025-04-15 0.09962, 2025-04-16 0.09964, 2025-04-17 0.09965; on D: 548.62 ÷ 5456.90 = 0.10054) | SPX close independent |
| SPY implied: 15:59 bar × IVV EOD ÷ IVV 15:59 bar | 543.57 (IVV EOD 546.25, 15:59 546.05) | same vendor's EOD, another fund |
| SPY implied: 15:59 bar × VOO EOD ÷ VOO 15:59 bar | 542.97 (VOO EOD 499.1, 15:59 499.47) | same vendor's EOD, another fund |
| QQQ the same day: official − 15:59 | +0.86 (466.0 vs 465.14) | the sibling index fund |
| UW daily / UW 1-minute for the day | none on disk (UW daily starts 2025-10-13; the 1-minute cache 2025-05-22) |  |

**Verdict: not confirmed.** Every second source places SPY's close within $1 of the 15:59 bar (542.97–543.72), $4.90–5.65 below 548.62; 548.62 is also the Theta EOD row's high of the day, above every 1-minute high (546.33), so it reads as one late or out-of-sequence print taken as the last sale, not the closing auction (the row's own NBBO at its 17:16 report, an after-hours quote, stood near 546). None of the second sources is the primary listing's auction print itself, so this is a strong inconsistency, not a proof of the auction price; the audit's official-close re-settlement uses 548.62 for this day.

What the day carries in the audit (SPY trades on 2025-04-09, re-settled at 548.62 against the second sources' median of the anchored values, 543.57):

| candidate · structure | trades | total $ at 548.62 | total $ at 543.57 |
|---|---|---|---|
| condor_d20 condor | 5 | -764 | -402 |
| condor_em1 condor | 5 | -754 | -754 |
| fly5 call | 2 | -294 | -151 |
| fly5 iron | 2 | -282 | -139 |
| fly5 put | 2 | -293 | -150 |

## 6. Every pre-2025-10-13 name-session with |official − 15:59| > $0.25

The 15:59 bar is read again from the Theta 1-minute files; it equals the audit's `settlement_sessions.csv` value on 1445 of 1445 name-sessions held in both. UW's daily bars start 2025-10-13, so the official close before it has one source, Theta EOD; the second sources are values implied by other files: SPY — SPX's official close (Cboe) anchored on the 15:59 bars (independent of Theta), IVV and VOO EOD anchored on their 15:59 bars (Theta EOD, other funds); QQQ — TQQQ and SQQQ EOD anchored on their 15:59 bars (÷ ±3; SQQQ's minute files on disk are partial, so it is "—" where its file is missing), QQQM EOD × the median QQQ/QQQM ratio of the five sessions either side (Theta EOD, other funds); Theta's own 16:00 bar for both. "Nearer" says whether the median of the implied values is nearer the official close or the 15:59 bar.

| name | day | official | source | 15:59 bar | official − 15:59 | Theta 16:00 bar | second sources (implied close) | median of implied | nearer | official − median |
|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 2023-05-31 | 347.99 | theta_eod | 347.66 | +0.33 | 347.67 | TQQQ 347.66; SQQQ —; QQQM ratio 347.87 | 347.77 | 15:59 bar | +0.22 |
| QQQ | 2023-07-19 | 385.65 | theta_eod | 385.39 | +0.26 | — | TQQQ 385.72; SQQQ —; QQQM ratio 385.35 | 385.54 | official | +0.11 |
| QQQ | 2023-10-18 | 363.37 | theta_eod | 363.09 | +0.28 | — | TQQQ 363.12; SQQQ —; QQQM ratio 363.38 | 363.25 | official | +0.12 |
| QQQ | 2023-12-15 | 405.34 | theta_eod | 404.94 | +0.40 | 404.92 | TQQQ 404.99; SQQQ —; QQQM ratio 405.00 | 405.00 | 15:59 bar | +0.34 |
| QQQ | 2024-05-31 | 450.71 | theta_eod | 451.69 | -0.98 | — | TQQQ 451.59; SQQQ —; QQQM ratio 451.64 | 451.61 | 15:59 bar | -0.90 |
| QQQ | 2024-08-05 | 435.37 | theta_eod | 435.75 | -0.38 | — | TQQQ 435.72; SQQQ —; QQQM ratio 435.83 | 435.78 | 15:59 bar | -0.41 |
| QQQ | 2025-03-03 | 497.05 | theta_eod | 497.32 | -0.27 | — | TQQQ 497.27; SQQQ —; QQQM ratio 497.24 | 497.26 | 15:59 bar | -0.21 |
| QQQ | 2025-03-10 | 472.73 | theta_eod | 473.30 | -0.57 | — | TQQQ 473.37; SQQQ —; QQQM ratio 473.32 | 473.34 | 15:59 bar | -0.61 |
| QQQ | 2025-03-21 | 480.84 | theta_eod | 481.12 | -0.28 | 481.14 | TQQQ 480.99; SQQQ —; QQQM ratio 480.95 | 480.97 | official | -0.13 |
| QQQ | 2025-04-04 | 422.67 | theta_eod | 423.20 | -0.53 | — | TQQQ 423.20; SQQQ —; QQQM ratio 423.31 | 423.26 | 15:59 bar | -0.59 |
| QQQ | 2025-04-07 | 423.69 | theta_eod | 423.95 | -0.26 | 423.96 | TQQQ 423.88; SQQQ —; QQQM ratio 423.82 | 423.85 | 15:59 bar | -0.16 |
| QQQ | 2025-04-09 | 466.00 | theta_eod | 465.14 | +0.86 | — | TQQQ 464.93; SQQQ —; QQQM ratio 465.03 | 464.98 | 15:59 bar | +1.02 |
| QQQ | 2025-05-01 | 481.68 | theta_eod | 481.19 | +0.49 | — | TQQQ 481.16; SQQQ —; QQQM ratio 481.26 | 481.21 | 15:59 bar | +0.47 |
| SPY | 2023-12-20 | 468.26 | theta_eod | 467.97 | +0.29 | 467.97 | SPX-anchored 467.99; IVV 467.93; VOO 467.99 | 467.99 | 15:59 bar | +0.27 |
| SPY | 2024-06-21 | 544.51 | theta_eod | 544.13 | +0.38 | — | SPX-anchored 543.86; IVV 544.11; VOO 544.09 | 544.09 | 15:59 bar | +0.42 |
| SPY | 2024-07-31 | 550.81 | theta_eod | 550.44 | +0.37 | 550.44 | SPX-anchored 550.44; IVV 550.38; VOO 550.48 | 550.44 | 15:59 bar | +0.37 |
| SPY | 2024-09-30 | 573.76 | theta_eod | 574.02 | -0.26 | 574.02 | SPX-anchored 574.03; IVV 574.04; VOO 574.04 | 574.04 | 15:59 bar | -0.28 |
| SPY | 2024-12-20 | 591.15 | theta_eod | 590.87 | +0.28 | 590.91 | SPX-anchored 590.60; IVV 590.51; VOO 590.91 | 590.60 | 15:59 bar | +0.55 |
| SPY | 2025-04-03 | 536.70 | theta_eod | 537.64 | -0.94 | 537.67 | SPX-anchored 537.70; IVV 537.56; VOO 537.62 | 537.62 | 15:59 bar | -0.92 |
| SPY | 2025-04-08 | 496.48 | theta_eod | 496.74 | -0.26 | 496.75 | SPX-anchored 496.38; IVV 496.49; VOO 497.04 | 496.49 | official | -0.01 |
| SPY | 2025-04-09 | 548.62 | theta_eod | 543.37 | +5.25 | 543.48 | SPX-anchored 543.72; IVV 543.57; VOO 542.97 | 543.57 | 15:59 bar | +5.05 |
| SPY | 2025-04-22 | 527.25 | theta_eod | 526.94 | +0.31 | 526.94 | SPX-anchored 526.98; IVV 526.95; VOO 526.99 | 526.98 | 15:59 bar | +0.27 |

Of 22: the implied values sit nearer the official close on 4 and nearer the 15:59 bar on 18. Read with care: the fund-anchored values start from the 15:59 bar and add only the sibling's own move from 15:59 to its close, so they test whether SPY or QQQ moved into the close with its siblings; only the SPX-anchored value uses a close from outside Theta. Every row is in `out/afterhours_close_check.csv`.

## 7. Files and command

```
cd "research_notes/Compass phase 3/backtest_audit"
PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I afterhours.py [--fee-ex 0.0] [--scratch <dir>]
# done once (2026-10-22), the 16 period-iii name-sessions; a name-session already in data/postmarket_1m/ is never asked again
set -a; . <research.env>; set +a; python3 -I fetch_postmarket_1m.py --from-coverage
```

`--scratch` defaults to the parquet root's parent (the folder holding `bt/cache`, `audit_fresh_cache`, `bt/probe`, `evidence/provider_tests`, `spx/` and `theta/fetch_cache`). Outputs: `out/afterhours_coverage.csv` (every name-session: official close and source, UW daily `po` row, decision price, its bar, its file, why missing, the next open), `out/afterhours_trades.csv` (every trade under (0)/(a)/(b)/(c), contracts exercised, net shares, the 15:58 exit, the flags), `out/afterhours_summary.csv` (every statistic above), `out/afterhours_close_check.csv`, `out/afterhours_20250409.json`. Deterministic: files read in sorted order, seeded draws, no clock in the outputs. `afterhours.py` reads no secret and calls no vendor. `fetch_postmarket_1m.py` made the 16 UW calls once, one at a time with a 2 s pause (429 → back off), the token from the environment as a Bearer header, never printed or written; each answer is kept as its response body, gzipped with no timestamp. UW answered every name-session asked. The replay's rows, `scripts/`, `tests/` and the other audit files are only read.
