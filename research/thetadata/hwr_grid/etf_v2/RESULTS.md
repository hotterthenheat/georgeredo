# SPY / QQQ / IWM 0DTE short-premium grid on complete option chains (etf_v2): results

Re-run of the pre-registered grid of `../etf/` (protocol `PREREGISTRATION_original.md`, sha256 ddc4e053496cb3f5…, identical to `../etf/PREREGISTRATION.md`; no rule changed) on the full same-day chains (`data_full`: every listed strike, no ±2 % band).  TRAIN re-selection: `results/selection_train.json` (sha256 b3d83a325690de18…), written by `analyze.py train` from TRAIN trades only before `analyze.py test` ran.  Original selections: `../etf/results/selection_train.json` (sha256 3f8a89deaa80a1ff…).  All $ are per 1-lot (one contract per leg) after bid/ask fills and $0.70 per contract per side.  CIs: 95 % bootstrap over trading days (5,000 draws, seed 7).  TRAIN 2022-11-11 → 2024-12-31 (IWM from 2024-04-19); TEST 2025-01-02 → 2026-10-09.  The TEST window was already seen (on band data) by the original study, so it is out of sample for the selection rule but not a fresh holdout.

**Code validation.**  Run on the original band dataset, this folder's engine reproduces the original per-trade and skip files exactly: SPY_TRAIN identical (695718 rows); SPY_TEST identical (577080 rows); QQQ_TRAIN identical (618714 rows); QQQ_TEST identical (522909 rows); IWM_TRAIN identical (164556 rows); IWM_TEST identical (443718 rows); TRAIN selections identical: {'SPY': True, 'QQQ': True, 'IWM': True, 'SPY+QQQ': True}; selected-TEST rows compared 16, max |difference| {'test_n': 0.0, 'test_mean': 0.0, 'test_lo': 0.0, 'lane_minus_base': 0.0} (`results/validation_band_reproduction.json`).

## 1. Data integrity (full chains)

| ticker | sessions in window | full-chain files | .nodata | listed strikes per session, median (min) | sessions whose listed strikes span the whole 09:30–16:00 price range: full chains / original band | band rows found unchanged in the full pull |
|---|---|---|---|---|---|---|
| SPY | 980 (of which 9 early closes, excluded by design) | 980 (sha256 each, `data_manifest.csv`) | 0 | 139 (40) | 980 / 938 of 980 | 17,333,421 of 17,335,767 quote rows identical; band strikes ⊆ full strikes: False; band rows missing from the full pull: 2346 |
| QQQ | 980 (of which 9 early closes, excluded by design) | 980 (sha256 each, `data_manifest.csv`) | 0 | 131 (38) | 980 / 881 of 980 | 15,306,477 of 15,310,387 quote rows identical; band strikes ⊆ full strikes: False; band rows missing from the full pull: 3910 |
| IWM | 621 (of which 6 early closes, excluded by design) | 621 (sha256 each, `data_manifest.csv`) | 0 | 79 (30) | 621 / 520 of 621 | 4,733,446 of 4,735,010 quote rows identical; band strikes ⊆ full strikes: True; band rows missing from the full pull: 1564 |

Per-entry check (engine.py `entry_status`, the trade loop's own skip rules, at every pre-registered entry, every seed-11..15 random-baseline minute, and every minute 10:00–14:30): a slot is one entry × structure-k.  Data reasons = a needed strike is not listed beyond spot ± k·EM / (k+1)·EM (`out_of_band`), spot outside the listed range (`out_of_band_spot`, amendment A1), or no usable quote at the entry minute (`no_quote`).  Market reasons (`zero_bid`, `no_credit`) are pre-registered skips that reflect the quote, not missing data.

| ticker | period | entry set | slots | traded-eligible (ok) | out_of_band | out_of_band_spot (A1) | no_quote | zero_bid | no_credit |
|---|---|---|---|---|---|---|---|---|---|
| SPY | TRAIN | fixed | 14,840 | 14,759 | 0 | 0 | 11 | 63 | 7 |
| SPY | TRAIN | random | 18,550 | 18,448 | 0 | 0 | 19 | 69 | 14 |
| SPY | TRAIN | all_minutes | 1,005,410 | 1,000,297 | 0 | 0 | 937 | 3620 | 556 |
| SPY | TEST | fixed | 12,348 | 12,332 | 0 | 0 | 2 | 13 | 1 |
| SPY | TEST | random | 15,435 | 15,417 | 0 | 0 | 5 | 13 | 0 |
| SPY | TEST | all_minutes | 836,577 | 835,667 | 0 | 0 | 301 | 551 | 58 |
| QQQ | TRAIN | fixed | 14,840 | 14,743 | 0 | 0 | 15 | 74 | 8 |
| QQQ | TRAIN | random | 18,550 | 18,418 | 0 | 0 | 31 | 97 | 4 |
| QQQ | TRAIN | all_minutes | 1,005,410 | 998,790 | 0 | 0 | 1248 | 5074 | 298 |
| QQQ | TEST | fixed | 12,348 | 12,319 | 0 | 0 | 0 | 29 | 0 |
| QQQ | TEST | random | 15,435 | 15,406 | 0 | 0 | 0 | 27 | 2 |
| QQQ | TEST | all_minutes | 836,577 | 834,527 | 6 | 0 | 299 | 1721 | 24 |
| IWM | TRAIN | fixed | 4,872 | 4,254 | 0 | 0 | 12 | 583 | 23 |
| IWM | TRAIN | random | 6,090 | 5,357 | 0 | 0 | 19 | 703 | 11 |
| IWM | TRAIN | all_minutes | 330,078 | 290,346 | 0 | 0 | 880 | 38193 | 659 |
| IWM | TEST | fixed | 12,348 | 11,300 | 0 | 0 | 0 | 1015 | 33 |
| IWM | TEST | random | 15,435 | 14,102 | 0 | 0 | 11 | 1288 | 34 |
| IWM | TEST | all_minutes | 836,577 | 765,514 | 2 | 0 | 135 | 69452 | 1474 |

Fixed or random-baseline entry slots still missing a needed strike or quote: **125** (by reason {'out_of_band': 0, 'out_of_band_spot': 0, 'no_quote': 125, 'no_spot': 0, 'no_em': 0}; list in `results/integrity_missing.csv`).

| ticker | period | date | entry | sk | reason |
|---|---|---|---|---|---|
| IWM | TRAIN | 2024-06-21 | 10:00 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 10:00 | I1.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 10:00 | S1.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r11 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r11 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | r11 | I1.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r11 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r11 | S1.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r14 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r14 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | r14 | I1.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r14 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r14 | S1.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 11:00 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 11:00 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | 11:00 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r12 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r12 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | r12 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 13:00 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 13:00 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | 13:00 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r15 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r15 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | r15 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r13 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | r13 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | r13 | S0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 14:05 | I0.5 | no_quote |
| IWM | TRAIN | 2024-06-21 | 14:05 | I1 | no_quote |
| IWM | TRAIN | 2024-06-21 | 14:05 | S0.5 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | I0.5 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | I1 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | I1.5 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | S0 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | S0.5 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | S1 | no_quote |
| IWM | TEST | 2025-07-30 | r13 | S1.5 | no_quote |
| IWM | TEST | 2025-10-22 | r15 | I0.5 | no_quote |
| IWM | TEST | 2025-10-22 | r15 | I1 | no_quote |

(85 more rows in `results/integrity_missing.csv`.)

Sessions where the full pull does not contain every quote row of the original band pull: IWM 2024-06-21 (1,564 of 3,128 band rows absent, 6 band strikes vs 102 listed); QQQ 2024-06-21 (3,910 of 10,557 band rows absent, 17 band strikes vs 246 listed); SPY 2024-06-21 (2,346 of 12,121 band rows absent, 18 band strikes vs 203 listed).  On every other session the overlapping quotes are identical row for row.

Entry slots (entry × structure-k) that the original run skipped because a strike or spot lay outside the ±2 % band, and their status on the full chains:

| ticker | period | entries | band-skipped slots | now traded | now zero_bid | now no_credit | now no_quote |
|---|---|---|---|---|---|---|---|
| SPY | TRAIN | fixed | 712 | 703 | 9 | 0 | 0 |
| SPY | TRAIN | random | 925 | 912 | 13 | 0 | 0 |
| SPY | TEST | fixed | 694 | 694 | 0 | 0 | 0 |
| SPY | TEST | random | 819 | 814 | 3 | 0 | 2 |
| QQQ | TRAIN | fixed | 2,309 | 2,278 | 30 | 1 | 0 |
| QQQ | TRAIN | random | 2,812 | 2,775 | 33 | 0 | 4 |
| QQQ | TEST | fixed | 1,778 | 1,768 | 10 | 0 | 0 |
| QQQ | TEST | random | 2,192 | 2,182 | 10 | 0 | 0 |
| IWM | TRAIN | fixed | 1,121 | 932 | 172 | 10 | 7 |
| IWM | TRAIN | random | 1,405 | 1,200 | 191 | 3 | 11 |
| IWM | TEST | fixed | 2,633 | 2,356 | 270 | 7 | 0 |
| IWM | TEST | random | 3,227 | 2,867 | 353 | 3 | 4 |

Total: fixed entries 8,731 of 9,247 band-skipped slots now traded; random entries 10,750 of 11,380 band-skipped slots now traded (the rest are pre-registered skips: a zero bid on a leg or wing or no net credit, which are market facts, or no usable quote at the entry minute, a data gap).


Entries the original band-data run skipped, by original reason, and what they are on the full chains (`results/integrity_recovered.csv`):

| ticker | period | entries | original skip reason | now | entry × structure-k slots | sessions |
|---|---|---|---|---|---|---|
| IWM | TEST | fixed | no_credit | no_credit | 26 | 20 |
| IWM | TEST | fixed | out_of_band | no_credit | 6 | 5 |
| IWM | TEST | fixed | out_of_band | traded | 1981 | 276 |
| IWM | TEST | fixed | out_of_band | zero_bid | 247 | 120 |
| IWM | TEST | fixed | out_of_band_spot | no_credit | 1 | 1 |
| IWM | TEST | fixed | out_of_band_spot | traded | 375 | 33 |
| IWM | TEST | fixed | out_of_band_spot | zero_bid | 23 | 10 |
| IWM | TEST | fixed | zero_bid | zero_bid | 745 | 203 |
| IWM | TEST | random | no_credit | no_credit | 31 | 22 |
| IWM | TEST | random | no_quote | no_quote | 7 | 1 |
| IWM | TEST | random | out_of_band | no_credit | 3 | 2 |
| IWM | TEST | random | out_of_band | traded | 2358 | 250 |
| IWM | TEST | random | out_of_band | zero_bid | 327 | 123 |
| IWM | TEST | random | out_of_band_spot | no_quote | 4 | 1 |
| IWM | TEST | random | out_of_band_spot | traded | 509 | 30 |
| IWM | TEST | random | out_of_band_spot | zero_bid | 26 | 11 |
| IWM | TEST | random | zero_bid | zero_bid | 935 | 188 |
| IWM | TRAIN | fixed | no_credit | no_credit | 13 | 8 |
| IWM | TRAIN | fixed | no_quote | no_quote | 2 | 1 |
| IWM | TRAIN | fixed | no_quote | traded | 2 | 1 |
| IWM | TRAIN | fixed | out_of_band | no_credit | 10 | 7 |
| IWM | TRAIN | fixed | out_of_band | no_quote | 7 | 1 |
| IWM | TRAIN | fixed | out_of_band | traded | 778 | 114 |
| IWM | TRAIN | fixed | out_of_band | zero_bid | 158 | 67 |
| IWM | TRAIN | fixed | out_of_band_spot | traded | 154 | 13 |
| IWM | TRAIN | fixed | out_of_band_spot | zero_bid | 14 | 8 |
| IWM | TRAIN | fixed | zero_bid | no_quote | 2 | 1 |
| IWM | TRAIN | fixed | zero_bid | zero_bid | 410 | 101 |
| IWM | TRAIN | random | no_credit | no_credit | 8 | 6 |
| IWM | TRAIN | random | no_quote | no_quote | 4 | 1 |
| IWM | TRAIN | random | no_quote | traded | 1 | 1 |
| IWM | TRAIN | random | out_of_band | no_credit | 3 | 1 |
| IWM | TRAIN | random | out_of_band | no_quote | 11 | 1 |
| IWM | TRAIN | random | out_of_band | traded | 974 | 100 |
| IWM | TRAIN | random | out_of_band | zero_bid | 172 | 56 |
| IWM | TRAIN | random | out_of_band_spot | traded | 226 | 12 |
| IWM | TRAIN | random | out_of_band_spot | zero_bid | 19 | 7 |
| IWM | TRAIN | random | zero_bid | no_quote | 2 | 1 |
| IWM | TRAIN | random | zero_bid | zero_bid | 511 | 94 |
| QQQ | TEST | fixed | out_of_band | traded | 1509 | 226 |
| QQQ | TEST | fixed | out_of_band | zero_bid | 10 | 10 |
| QQQ | TEST | fixed | out_of_band_spot | traded | 259 | 24 |
| QQQ | TEST | fixed | zero_bid | zero_bid | 19 | 16 |
| QQQ | TEST | random | no_credit | no_credit | 2 | 1 |
| QQQ | TEST | random | out_of_band | traded | 1803 | 209 |
| QQQ | TEST | random | out_of_band | zero_bid | 4 | 4 |
| QQQ | TEST | random | out_of_band_spot | traded | 379 | 22 |
| QQQ | TEST | random | out_of_band_spot | zero_bid | 6 | 1 |
| QQQ | TEST | random | zero_bid | zero_bid | 17 | 12 |
| QQQ | TRAIN | fixed | no_credit | no_credit | 7 | 7 |
| QQQ | TRAIN | fixed | no_quote | no_quote | 1 | 1 |
| QQQ | TRAIN | fixed | no_quote | traded | 1 | 1 |
| QQQ | TRAIN | fixed | out_of_band | no_credit | 1 | 1 |
| QQQ | TRAIN | fixed | out_of_band | traded | 1985 | 330 |
| QQQ | TRAIN | fixed | out_of_band | zero_bid | 29 | 24 |
| QQQ | TRAIN | fixed | out_of_band_spot | traded | 293 | 26 |
| QQQ | TRAIN | fixed | out_of_band_spot | zero_bid | 1 | 1 |
| QQQ | TRAIN | fixed | zero_bid | zero_bid | 44 | 39 |
| QQQ | TRAIN | random | no_credit | no_credit | 4 | 4 |
| QQQ | TRAIN | random | no_quote | no_quote | 11 | 4 |
| QQQ | TRAIN | random | no_quote | traded | 3 | 1 |
| QQQ | TRAIN | random | out_of_band | no_quote | 4 | 2 |
| QQQ | TRAIN | random | out_of_band | traded | 2419 | 299 |
| QQQ | TRAIN | random | out_of_band | zero_bid | 32 | 19 |
| QQQ | TRAIN | random | out_of_band_spot | traded | 356 | 20 |
| QQQ | TRAIN | random | out_of_band_spot | zero_bid | 1 | 1 |
| QQQ | TRAIN | random | zero_bid | zero_bid | 64 | 42 |
| SPY | TEST | fixed | no_credit | no_credit | 1 | 1 |
| SPY | TEST | fixed | no_quote | no_quote | 2 | 1 |
| SPY | TEST | fixed | out_of_band | traded | 596 | 119 |
| SPY | TEST | fixed | out_of_band_spot | traded | 98 | 9 |
| SPY | TEST | fixed | zero_bid | zero_bid | 13 | 10 |
| SPY | TEST | random | no_quote | no_quote | 3 | 2 |
| SPY | TEST | random | out_of_band | no_quote | 2 | 1 |
| SPY | TEST | random | out_of_band | traded | 653 | 109 |
| SPY | TEST | random | out_of_band | zero_bid | 3 | 1 |
| SPY | TEST | random | out_of_band_spot | traded | 161 | 10 |
| SPY | TEST | random | zero_bid | zero_bid | 10 | 7 |
| SPY | TRAIN | fixed | no_credit | no_credit | 7 | 7 |
| SPY | TRAIN | fixed | no_quote | no_quote | 2 | 1 |
| SPY | TRAIN | fixed | no_quote | traded | 1 | 1 |
| SPY | TRAIN | fixed | out_of_band | traded | 647 | 135 |
| SPY | TRAIN | fixed | out_of_band | zero_bid | 9 | 6 |
| SPY | TRAIN | fixed | out_of_band_spot | traded | 56 | 6 |
| SPY | TRAIN | fixed | zero_bid | zero_bid | 54 | 39 |
| SPY | TRAIN | random | no_credit | no_credit | 14 | 11 |
| SPY | TRAIN | random | out_of_band | traded | 800 | 119 |
| SPY | TRAIN | random | out_of_band | zero_bid | 13 | 8 |
| SPY | TRAIN | random | out_of_band_spot | traded | 112 | 7 |
| SPY | TRAIN | random | zero_bid | zero_bid | 56 | 38 |

Amendment A1 (skip when spot at entry is outside the stored strike range): SPY TRAIN: originally 56 fixed-entry slots on 6 sessions, now traded 56; SPY TEST: originally 98 fixed-entry slots on 9 sessions, now traded 98; QQQ TRAIN: originally 294 fixed-entry slots on 26 sessions, now traded 293; QQQ TEST: originally 259 fixed-entry slots on 24 sessions, now traded 259; IWM TRAIN: originally 168 fixed-entry slots on 13 sessions, now traded 154; IWM TEST: originally 399 fixed-entry slots on 33 sessions, now traded 375.

How far the listed strikes reach beyond spot, in units of the entry-time expected move EM (the widest structure needs 2.5 EM: condor k = 1.5 wings):

| ticker | period | entry set | slots | strikes per session (median) | reach above spot: min / 1st pct / median | reach below spot: min / 1st pct / median | slots with reach < 2.5 EM on either side |
|---|---|---|---|---|---|---|---|
| SPY | TRAIN | fixed | 2,120 | 133 | 9.5 / 15.01 / 43.52 | 7.4 / 16.32 / 61.17 | 0 |
| SPY | TRAIN | all_minutes | 143,630 | 133 | 9.31 / 15.16 / 45.05 | 7.4 / 16.51 / 62.8 | 0 |
| SPY | TEST | fixed | 1,764 | 163 | 10.61 / 17.05 / 63.91 | 7.18 / 22.5 / 96.77 | 0 |
| SPY | TEST | all_minutes | 119,509 | 163 | 5.62 / 17.48 / 66.2 | 5.7 / 23.3 / 101.91 | 0 |
| QQQ | TRAIN | fixed | 2,120 | 124 | 6.3 / 12.36 / 34.6 | 4.94 / 12.18 / 42.16 | 0 |
| QQQ | TRAIN | all_minutes | 143,615 | 124 | 6.02 / 12.61 / 35.88 | 4.94 / 12.58 / 44.01 | 0 |
| QQQ | TEST | fixed | 1,764 | 145 | 6.32 / 10.9 / 42.89 | 7.79 / 12.81 / 57.19 | 0 |
| QQQ | TEST | all_minutes | 119,510 | 145 | 1.52 / 11.32 / 44.7 | 1.0 / 13.24 / 60.4 | 2 |
| IWM | TRAIN | fixed | 696 | 75 | 7.33 / 11.95 / 49.65 | 7.99 / 13.36 / 55.75 | 0 |
| IWM | TRAIN | all_minutes | 47,154 | 75 | 7.33 / 13.39 / 52.26 | 7.67 / 14.02 / 57.91 | 0 |
| IWM | TEST | fixed | 1,764 | 80 | 7.05 / 12.28 / 40.55 | 5.51 / 11.36 / 66.6 | 0 |
| IWM | TEST | all_minutes | 119,495 | 80 | 1.5 / 12.95 / 42.42 | 3.23 / 11.2 / 70.71 | 1 |

## 2. TRAIN selections and their TEST results on complete data

S1 = best TRAIN lower bound (TRAIN n ≥ 100); S2 = best TRAIN lower bound among TRAIN win ≥ 70 % (pre-registered).  `S1`/`S2` = re-selected on the full-chain TRAIN data; `S1-orig`/`S2-orig` = the original band-data TRAIN selections evaluated on complete TEST data; `PH-…` = the original post-hoc E1-only rule applied to the full-chain TRAIN grid (not pre-registered, not promotable).

| scope | original S1 / S2 (band TRAIN) | full-chain S1 / S2 | same? |
|---|---|---|---|
| SPY | `S0|14:05|tp0|st1|E2|F3` / `S0.5|14:05|tp0|st2|E2|F3` | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp50|st2|E2|F3` | S1 yes, S2 no |
| QQQ | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp0|st2|E2|F3` | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp0|st1|E2|F3` | S1 yes, S2 no |
| IWM | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp0|st2|E2|F3` | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp0|st2|E2|F3` | S1 yes, S2 yes |
| SPY+QQQ | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp0|st2|E2|F3` | `S0|14:05|tp0|st1|E2|F3` / `S0|14:05|tp0|st2|E2|F3` | S1 yes, S2 yes |

| scope | sel | configuration | TRAIN (full chains) n / win / mean [CI] | TEST on band data (original run) n / mean [CI] | **TEST on complete data** n / win / mean [CI] | Bonferroni-8 LB | Romano–Wolf | PF / maxDD $ / worst trade $ | trades added by the full chains: n, Σ $, worst | common trades max |Δ| $ |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 490 / 67.8 % / +26.41 [+18.50, +34.14] | 400 / +34.82 [+23.09, +46.26] | **407 / 68.1 % / +34.33 [+21.02, +47.24]** | +15.41 | rejected | 1.99 / -1034 / -801 | 7, +47.80, SPY 2025-04-08 -801 | +0.0000 |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` straddle k=0 @14:05, TP 50%, stop 2x, E2, skip FOMC+month-end | 490 / 70.4 % / +21.71 [+13.66, +29.60] | not evaluated | **407 / 70.3 % / +32.09 [+19.93, +43.76]** | +15.35 | rejected | 2.02 / -1211 / -609 | 7, +279.40, SPY 2025-04-04 -447 | +0.0000 |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 490 / 67.8 % / +26.41 [+18.50, +34.14] | 400 / +34.82 [+23.09, +46.26] | **407 / 68.1 % / +34.33 [+21.02, +47.24]** | +15.41 | rejected | 1.99 / -1034 / -801 | 7, +47.80, SPY 2025-04-08 -801 | +0.0000 |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` strangle k=0.5 @14:05, no TP, stop 2x, E2, skip FOMC+month-end | 489 / 76.7 % / +18.73 [+13.39, +23.90] | 397 / +20.69 [+12.19, +29.03] | **407 / 75.9 % / +21.29 [+11.05, +31.28]** | +7.07 | rejected | 1.79 / -909 / -720 | 10, +453.20, SPY 2025-04-08 -720 | +0.0000 |
| SPY | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` strangle k=0.5 @14:05, no TP, stop 2x, E1, skip FOMC+month-end | 489 / 74.2 % / +9.28 [+4.46, +13.79] | 397 / +7.74 [+0.39, +14.83] | **407 / 73.5 % / +7.62 [-1.05, +16.13]** | -5.44 | not rejected | 1.29 / -1843 / -720 | 10, +28.50, SPY 2025-04-08 -720 | +0.0000 |
| SPY | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` strangle k=0.5 @14:05, no TP, stop 2x, E1, skip FOMC+month-end | 489 / 74.2 % / +9.28 [+4.46, +13.79] | 397 / +7.74 [+0.39, +14.83] | **407 / 73.5 % / +7.62 [-1.05, +16.13]** | -5.44 | not rejected | 1.29 / -1843 / -720 | 10, +28.50, SPY 2025-04-08 -720 | +0.0000 |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 490 / 70.0 % / +32.44 [+24.30, +40.48] | 391 / +28.55 [+14.89, +41.98] | **407 / 64.9 % / +28.10 [+14.03, +41.97]** | +9.33 | rejected | 1.62 / -1396 / -652 | 16, +273.71, QQQ 2025-04-08 -652 | +0.0000 |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 490 / 70.0 % / +32.44 [+24.30, +40.48] | 391 / +28.55 [+14.89, +41.98] | **407 / 64.9 % / +28.10 [+14.03, +41.97]** | +9.33 | rejected | 1.62 / -1396 / -652 | 16, +273.71, QQQ 2025-04-08 -652 | +0.0000 |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 490 / 70.0 % / +32.44 [+24.30, +40.48] | 391 / +28.55 [+14.89, +41.98] | **407 / 64.9 % / +28.10 [+14.03, +41.97]** | +9.33 | rejected | 1.62 / -1396 / -652 | 16, +273.71, QQQ 2025-04-08 -652 | +0.0000 |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` straddle k=0 @14:05, no TP, stop 2x, E2, skip FOMC+month-end | 490 / 71.8 % / +32.46 [+23.36, +41.25] | 391 / +35.05 [+21.44, +48.47] | **407 / 67.8 % / +33.01 [+18.05, +47.32]** | +12.29 | rejected | 1.78 / -1697 / -776 | 16, -267.29, QQQ 2025-04-08 -776 | +0.0000 |
| QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st1|E1|F3` strangle k=0.5 @14:05, no TP, stop 1x, E1, skip FOMC+month-end | 489 / 68.9 % / +10.08 [+5.83, +14.16] | 383 / +4.82 [-2.63, +12.07] | **407 / 65.1 % / +5.50 [-2.31, +13.28]** | -5.42 | not rejected | 1.19 / -2224 / -314 | 24, +395.10, QQQ 2025-04-08 -276 | +0.0000 |
| QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` strangle k=0.5 @14:05, no TP, stop 2x, E1, skip FOMC+month-end | 489 / 75.5 % / +10.30 [+5.42, +15.02] | 383 / +6.26 [-2.06, +14.63] | **407 / 70.3 % / +5.14 [-4.52, +14.56]** | -9.87 | not rejected | 1.16 / -2649 / -803 | 24, -304.10, QQQ 2025-04-08 -803 | +0.0000 |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 161 / 69.6 % / +18.42 [+10.88, +25.55] | 383 / +8.69 [+2.71, +14.50] | **407 / 61.7 % / +8.78 [+2.52, +14.95]** | -0.66 | not rejected | 1.41 / -1069 / -304 | 24, +243.00, IWM 2025-04-08 -304 | +0.0000 |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` straddle k=0 @14:05, no TP, stop 2x, E2, skip FOMC+month-end | 161 / 70.8 % / +18.58 [+10.57, +25.93] | 383 / +12.20 [+6.28, +17.74] | **407 / 63.9 % / +12.40 [+6.36, +18.35]** | +3.38 | rejected | 1.66 / -1006 / -298 | 24, +375.00, IWM 2026-02-03 -259 | +0.0000 |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 161 / 69.6 % / +18.42 [+10.88, +25.55] | 383 / +8.69 [+2.71, +14.50] | **407 / 61.7 % / +8.78 [+2.52, +14.95]** | -0.66 | not rejected | 1.41 / -1069 / -304 | 24, +243.00, IWM 2025-04-08 -304 | +0.0000 |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` straddle k=0 @14:05, no TP, stop 2x, E2, skip FOMC+month-end | 161 / 70.8 % / +18.58 [+10.57, +25.93] | 383 / +12.20 [+6.28, +17.74] | **407 / 63.9 % / +12.40 [+6.36, +18.35]** | +3.38 | rejected | 1.66 / -1006 / -298 | 24, +375.00, IWM 2026-02-03 -259 | +0.0000 |
| IWM | PH-S1-E1 | `S0.5|11:00|tp0|st0|E1|F1` strangle k=0.5 @11:00, no TP, no stop, E1, skip FOMC | 167 / 77.8 % / +11.29 [+2.07, +19.98] | not evaluated | **427 / 66.3 % / -4.30 [-16.18, +5.42]** | -21.27 | not rejected | 0.87 / -4000 / -1488 | 21, -1137.60, IWM 2025-04-09 -1488 | +0.0000 |
| IWM | PH-S2-E1 | `S0.5|11:00|tp0|st0|E1|F1` strangle k=0.5 @11:00, no TP, no stop, E1, skip FOMC | 167 / 77.8 % / +11.29 [+2.07, +19.98] | not evaluated | **427 / 66.3 % / -4.30 [-16.18, +5.42]** | -21.27 | not rejected | 0.87 / -4000 / -1488 | 21, -1137.60, IWM 2025-04-09 -1488 | +0.0000 |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 980 / 68.9 % / +29.43 [+21.78, +37.09] | 791 / +31.72 [+19.56, +43.52] | **814 / 66.5 % / +31.22 [+18.07, +44.25]** | +13.25 | rejected | 1.78 / -2195 / -801 | 23, +321.51, SPY 2025-04-08 -801 | +0.0000 |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` straddle k=0 @14:05, no TP, stop 2x, E2, skip FOMC+month-end | 980 / 70.5 % / +29.58 [+20.96, +37.77] | 791 / +36.45 [+24.16, +48.48] | **814 / 68.6 % / +35.75 [+22.31, +49.03]** | +17.19 | rejected | 1.97 / -2729 / -776 | 23, +268.91, QQQ 2025-04-08 -776 | +0.0000 |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` straddle k=0 @14:05, no TP, stop 1x, E2, skip FOMC+month-end | 980 / 68.9 % / +29.43 [+21.78, +37.09] | 791 / +31.72 [+19.56, +43.52] | **814 / 66.5 % / +31.22 [+18.07, +44.25]** | +13.25 | rejected | 1.78 / -2195 / -801 | 23, +321.51, SPY 2025-04-08 -801 | +0.0000 |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` straddle k=0 @14:05, no TP, stop 2x, E2, skip FOMC+month-end | 980 / 70.5 % / +29.58 [+20.96, +37.77] | 791 / +36.45 [+24.16, +48.48] | **814 / 68.6 % / +35.75 [+22.31, +49.03]** | +17.19 | rejected | 1.97 / -2729 / -776 | 23, +268.91, QQQ 2025-04-08 -776 | +0.0000 |
| SPY+QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` strangle k=0.5 @14:05, no TP, stop 2x, E1, skip FOMC+month-end | 978 / 74.8 % / +9.79 [+5.24, +14.09] | 780 / +7.01 [-0.53, +14.27] | **814 / 71.9 % / +6.38 [-2.77, +15.05]** | -7.44 | not rejected | 1.22 / -4438 / -803 | 34, -275.60, QQQ 2025-04-08 -803 | +0.0000 |
| SPY+QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` strangle k=0.5 @14:05, no TP, stop 2x, E1, skip FOMC+month-end | 978 / 74.8 % / +9.79 [+5.24, +14.09] | 780 / +7.01 [-0.53, +14.27] | **814 / 71.9 % / +6.38 [-2.77, +15.05]** | -7.44 | not rejected | 1.22 / -4438 / -803 | 34, -275.60, QQQ 2025-04-08 -803 | +0.0000 |

Worst five TEST days of each selection on complete data (date, $ summed over the scope's tickers):

- SPY `S0|14:05|tp0|st1|E2|F3`: 2025-04-08 -801; 2025-04-04 -447; 2026-03-09 -354; 2026-06-10 -334; 2025-03-03 -320
- SPY `S0|14:05|tp50|st2|E2|F3`: 2025-03-03 -609; 2026-06-05 -473; 2025-04-04 -447; 2026-03-09 -417; 2025-02-27 -416
- SPY `S0.5|14:05|tp0|st2|E2|F3`: 2025-04-08 -720; 2025-04-04 -382; 2026-06-26 -309; 2026-06-10 -301; 2025-03-03 -297
- SPY `S0.5|14:05|tp0|st2|E1|F3`: 2025-04-08 -720; 2025-03-03 -297; 2025-04-04 -289; 2026-03-09 -278; 2026-06-05 -264
- QQQ `S0|14:05|tp0|st1|E2|F3`: 2025-04-08 -652; 2026-06-11 -477; 2025-04-04 -416; 2025-03-03 -386; 2025-10-10 -366
- QQQ `S0|14:05|tp0|st2|E2|F3`: 2025-04-08 -776; 2026-06-05 -681; 2025-03-03 -620; 2025-02-27 -526; 2026-01-21 -430
- QQQ `S0.5|14:05|tp0|st1|E1|F3`: 2026-03-09 -314; 2025-03-03 -278; 2025-04-08 -276; 2025-04-04 -264; 2026-06-10 -242
- QQQ `S0.5|14:05|tp0|st2|E1|F3`: 2025-04-08 -803; 2026-06-11 -477; 2026-06-05 -379; 2026-01-21 -342; 2025-03-03 -339
- IWM `S0|14:05|tp0|st1|E2|F3`: 2025-04-08 -304; 2026-03-09 -245; 2026-03-19 -222; 2026-03-10 -199; 2026-02-04 -183
- IWM `S0|14:05|tp0|st2|E2|F3`: 2026-03-09 -298; 2026-02-03 -259; 2026-01-21 -204; 2025-03-03 -201; 2026-03-19 -195
- IWM `S0.5|11:00|tp0|st0|E1|F1`: 2025-04-09 -1488; 2025-11-20 -674; 2025-04-08 -615; 2025-10-10 -451; 2026-03-09 -355
- SPY+QQQ `S0|14:05|tp0|st1|E2|F3`: 2025-04-08 -1453; 2025-04-04 -864; 2025-03-03 -706; 2026-03-09 -667; 2026-06-10 -633
- SPY+QQQ `S0|14:05|tp0|st2|E2|F3`: 2025-03-03 -1229; 2026-06-05 -1154; 2025-04-08 -1088; 2025-02-27 -942; 2025-04-04 -864
- SPY+QQQ `S0.5|14:05|tp0|st2|E1|F3`: 2025-04-08 -1523; 2026-06-05 -643; 2025-03-03 -636; 2026-03-09 -592; 2026-01-21 -559

By calendar year (TEST, complete data):

| scope | sel | config | year | n | win % | mean $ [CI] | PF | maxDD $ |
|---|---|---|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 68.9 | +43.05 [+23.73, +62.18] | 2.32 | -897 |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 67.0 | +23.23 [+5.86, +40.20] | 1.62 | -947 |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025 | 228 | 71.1 | +38.92 [+22.23, +55.08] | 2.37 | -1211 |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2026 | 179 | 69.3 | +23.39 [+5.62, +40.32] | 1.66 | -909 |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 68.9 | +43.05 [+23.73, +62.18] | 2.32 | -897 |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 67.0 | +23.23 [+5.86, +40.20] | 1.62 | -947 |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025 | 228 | 78.5 | +29.41 [+14.86, +43.71] | 2.2 | -720 |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2026 | 179 | 72.6 | +10.95 [-2.40, +24.01] | 1.37 | -906 |
| SPY | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2025 | 228 | 76.3 | +14.97 [+1.72, +27.35] | 1.63 | -803 |
| SPY | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2026 | 179 | 69.8 | -1.73 [-13.11, +9.26] | 0.94 | -1839 |
| SPY | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2025 | 228 | 76.3 | +14.97 [+1.72, +27.35] | 1.63 | -803 |
| SPY | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2026 | 179 | 69.8 | -1.73 [-13.11, +9.26] | 0.94 | -1839 |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 69.3 | +38.99 [+19.99, +58.06] | 2.03 | -753 |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 59.2 | +14.23 [-7.56, +35.19] | 1.26 | -1325 |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 69.3 | +38.99 [+19.99, +58.06] | 2.03 | -753 |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 59.2 | +14.23 [-7.56, +35.19] | 1.26 | -1325 |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 69.3 | +38.99 [+19.99, +58.06] | 2.03 | -753 |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 59.2 | +14.23 [-7.56, +35.19] | 1.26 | -1325 |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025 | 228 | 71.5 | +43.48 [+23.36, +63.20] | 2.23 | -1357 |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2026 | 179 | 63.1 | +19.69 [-2.87, +41.36] | 1.39 | -1697 |
| QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st1|E1|F3` | 2025 | 228 | 68.9 | +12.94 [+2.43, +23.29] | 1.53 | -509 |
| QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st1|E1|F3` | 2026 | 179 | 60.3 | -3.96 [-15.92, +7.65] | 0.89 | -2224 |
| QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2025 | 228 | 72.8 | +12.93 [-0.69, +25.29] | 1.49 | -956 |
| QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2026 | 179 | 67.0 | -4.78 [-20.09, +9.60] | 0.88 | -2501 |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 61.4 | +11.91 [+3.46, +20.39] | 1.6 | -732 |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 62.0 | +4.78 [-5.00, +14.35] | 1.2 | -1009 |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025 | 228 | 64.5 | +16.94 [+8.98, +24.72] | 2.05 | -567 |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2026 | 179 | 63.1 | +6.62 [-2.96, +16.38] | 1.3 | -947 |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025 | 228 | 61.4 | +11.91 [+3.46, +20.39] | 1.6 | -732 |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2026 | 179 | 62.0 | +4.78 [-5.00, +14.35] | 1.2 | -1009 |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025 | 228 | 64.5 | +16.94 [+8.98, +24.72] | 2.05 | -567 |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2026 | 179 | 63.1 | +6.62 [-2.96, +16.38] | 1.3 | -947 |
| IWM | PH-S1-E1 | `S0.5|11:00|tp0|st0|E1|F1` | 2025 | 239 | 66.1 | -11.25 [-30.51, +4.46] | 0.71 | -4000 |
| IWM | PH-S1-E1 | `S0.5|11:00|tp0|st0|E1|F1` | 2026 | 188 | 66.5 | +4.55 [-6.75, +15.02] | 1.18 | -591 |
| IWM | PH-S2-E1 | `S0.5|11:00|tp0|st0|E1|F1` | 2025 | 239 | 66.1 | -11.25 [-30.51, +4.46] | 0.71 | -4000 |
| IWM | PH-S2-E1 | `S0.5|11:00|tp0|st0|E1|F1` | 2026 | 188 | 66.5 | +4.55 [-6.75, +15.02] | 1.18 | -591 |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025 | 456 | 69.1 | +41.02 [+22.65, +59.79] | 2.16 | -1650 |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2026 | 358 | 63.1 | +18.73 [-0.08, +36.96] | 1.41 | -2151 |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025 | 456 | 71.1 | +46.03 [+27.60, +64.40] | 2.44 | -2387 |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2026 | 358 | 65.4 | +22.67 [+2.99, +41.49] | 1.52 | -2729 |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025 | 456 | 69.1 | +41.02 [+22.65, +59.79] | 2.16 | -1650 |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2026 | 358 | 63.1 | +18.73 [-0.08, +36.96] | 1.41 | -2151 |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025 | 456 | 71.1 | +46.03 [+27.60, +64.40] | 2.44 | -2387 |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2026 | 358 | 65.4 | +22.67 [+2.99, +41.49] | 1.52 | -2729 |
| SPY+QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2025 | 456 | 74.6 | +13.95 [+0.84, +26.04] | 1.56 | -1751 |
| SPY+QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2026 | 358 | 68.4 | -3.25 [-15.93, +8.78] | 0.9 | -4340 |
| SPY+QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2025 | 456 | 74.6 | +13.95 [+0.84, +26.04] | 1.56 | -1751 |
| SPY+QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 2026 | 358 | 68.4 | -3.25 [-15.93, +8.78] | 0.9 | -4340 |

## 3. Random-entry baselines on matched days

Entry minute uniform 10:00–14:30 (seeds 11–15, the committed minute list), same structure, k, TP, stop, exit and filter.  Pre-registered gate item: TEST mean − mean of the five baselines > mean round-trip cost (unpaired).  Matched: lane and baseline on the same (ticker, date) pairs only (paired, averaged over seeds, day-clustered CI).  "Baseline-only" = baseline trades on days the lane did not trade (the one-sided days of the original study).

| scope | sel | config | lane TEST mean | baseline mean (5 seeds) | unpaired diff (pre-registered) | matched pairs | matched lane mean | matched baseline mean | paired diff [CI] | round trip $ | baseline-only trades (mean $) | beats random by > cost: unpaired / matched |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | +34.33 | +26.10 | +8.23 | 407 | +34.33 | +26.10 | +8.23 [-6.65, +23.97] | 3.28 | 0 (n/a) | ✓ / ✓ |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | +32.09 | +20.94 | +11.15 | 407 | +32.09 | +20.94 | +11.15 [-3.31, +27.48] | 3.49 | 0 (n/a) | ✓ / ✓ |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | +34.33 | +26.10 | +8.23 | 407 | +34.33 | +26.10 | +8.23 [-6.65, +23.97] | 3.28 | 0 (n/a) | ✓ / ✓ |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | +21.29 | +22.86 | -1.57 | 407 | +21.29 | +23.14 | -1.84 [-13.57, +11.47] | 2.98 | 0 (n/a) | ✗ / ✗ |
| SPY | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | +7.62 | +7.76 | -0.14 | 407 | +7.62 | +8.01 | -0.39 [-11.35, +11.68] | 5.16 | 0 (n/a) | ✗ / ✗ |
| SPY | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | +7.62 | +7.76 | -0.14 | 407 | +7.62 | +8.01 | -0.39 [-11.35, +11.68] | 5.16 | 0 (n/a) | ✗ / ✗ |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | +28.10 | +29.94 | -1.84 | 407 | +28.10 | +29.37 | -1.27 [-16.77, +15.76] | 4.26 | 0 (n/a) | ✗ / ✗ |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | +28.10 | +29.94 | -1.84 | 407 | +28.10 | +29.37 | -1.27 [-16.77, +15.76] | 4.26 | 0 (n/a) | ✗ / ✗ |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | +28.10 | +29.94 | -1.84 | 407 | +28.10 | +29.37 | -1.27 [-16.77, +15.76] | 4.26 | 0 (n/a) | ✗ / ✗ |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | +33.01 | +38.85 | -5.83 | 407 | +33.01 | +38.04 | -5.03 [-20.81, +12.53] | 3.39 | 0 (n/a) | ✗ / ✗ |
| QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st1|E1|F3` | +5.50 | +9.46 | -3.95 | 407 | +5.50 | +9.13 | -3.62 [-13.59, +6.49] | 6.00 | 0 (n/a) | ✗ / ✗ |
| QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | +5.14 | +9.43 | -4.29 | 407 | +5.14 | +8.92 | -3.78 [-14.75, +8.65] | 6.53 | 0 (n/a) | ✗ / ✗ |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | +8.78 | +7.36 | +1.42 | 407 | +8.78 | +7.36 | +1.42 [-4.89, +8.06] | 4.09 | 0 (n/a) | ✗ / ✗ |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | +12.40 | +10.51 | +1.89 | 407 | +12.40 | +10.51 | +1.89 [-4.76, +8.90] | 3.27 | 0 (n/a) | ✗ / ✗ |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | +8.78 | +7.36 | +1.42 | 407 | +8.78 | +7.36 | +1.42 [-4.89, +8.06] | 4.09 | 0 (n/a) | ✗ / ✗ |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | +12.40 | +10.51 | +1.89 | 407 | +12.40 | +10.51 | +1.89 [-4.76, +8.90] | 3.27 | 0 (n/a) | ✗ / ✗ |
| IWM | PH-S1-E1 | `S0.5|11:00|tp0|st0|E1|F1` | -4.30 | +0.08 | -4.38 | 427 | -4.30 | +0.07 | -4.37 [-11.83, +2.19] | 8.61 | 0 (n/a) | ✗ / ✗ |
| IWM | PH-S2-E1 | `S0.5|11:00|tp0|st0|E1|F1` | -4.30 | +0.08 | -4.38 | 427 | -4.30 | +0.07 | -4.37 [-11.83, +2.19] | 8.61 | 0 (n/a) | ✗ / ✗ |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | +31.22 | +28.02 | +3.20 | 814 | +31.22 | +27.74 | +3.48 [-10.65, +18.83] | 3.77 | 0 (n/a) | ✗ / ✗ |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | +35.75 | +34.96 | +0.79 | 814 | +35.75 | +34.57 | +1.19 [-13.43, +17.67] | 3.10 | 0 (n/a) | ✗ / ✗ |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | +31.22 | +28.02 | +3.20 | 814 | +31.22 | +27.74 | +3.48 [-10.65, +18.83] | 3.77 | 0 (n/a) | ✗ / ✗ |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | +35.75 | +34.96 | +0.79 | 814 | +35.75 | +34.57 | +1.19 [-13.43, +17.67] | 3.10 | 0 (n/a) | ✗ / ✗ |
| SPY+QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | +6.38 | +8.59 | -2.21 | 814 | +6.38 | +8.46 | -2.08 [-12.57, +9.57] | 5.84 | 0 (n/a) | ✗ / ✗ |
| SPY+QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | +6.38 | +8.59 | -2.21 | 814 | +6.38 | +8.46 | -2.08 [-12.57, +9.57] | 5.84 | 0 (n/a) | ✗ / ✗ |

Pre-registered four-item gate of the original study (TEST LB > 0, n ≥ 150, ≥ 3 months, beats random by > cost, unpaired), on complete data:

| scope | sel | config | items | verdict | TEST win ≥ 70 % |
|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✓ | **PASS** | no |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | ✓✓✓✓ | **PASS** | yes |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✓ | **PASS** | no |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | ✓✓✓✗ | **FAIL** | yes |
| SPY | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | ✗✓✓✗ | **FAIL** | yes |
| SPY | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | ✗✓✓✗ | **FAIL** | yes |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st1|E1|F3` | ✗✓✓✗ | **FAIL** | no |
| QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | ✗✓✓✗ | **FAIL** | yes |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| IWM | PH-S1-E1 | `S0.5|11:00|tp0|st0|E1|F1` | ✗✓✓✗ | **FAIL** | no |
| IWM | PH-S2-E1 | `S0.5|11:00|tp0|st0|E1|F1` | ✗✓✓✗ | **FAIL** | no |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | ✓✓✓✗ | **FAIL** | no |
| SPY+QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | ✗✓✓✗ | **FAIL** | yes |
| SPY+QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | ✗✓✓✗ | **FAIL** | yes |

Per-seed baselines (TEST, complete data):

| scope | sel | seed | n | win % | mean $ [CI] |
|---|---|---|---|---|---|
| SPY | S1 | 11 | 407 | 64.4 | +26.46 [+8.26, +44.17] |
| SPY | S1 | 12 | 407 | 66.1 | +26.35 [+9.47, +42.88] |
| SPY | S1 | 13 | 407 | 65.8 | +28.62 [+9.62, +46.12] |
| SPY | S1 | 14 | 407 | 66.8 | +23.52 [+4.85, +41.51] |
| SPY | S1 | 15 | 407 | 65.1 | +25.57 [+6.88, +43.78] |
| SPY | S2 | 11 | 407 | 68.6 | +15.41 [-7.97, +35.92] |
| SPY | S2 | 12 | 407 | 69.0 | +28.37 [+12.25, +43.42] |
| SPY | S2 | 13 | 407 | 68.6 | +22.72 [+2.37, +40.94] |
| SPY | S2 | 14 | 407 | 70.8 | +17.52 [-1.59, +35.61] |
| SPY | S2 | 15 | 407 | 69.5 | +20.71 [+0.29, +39.34] |
| SPY | S1-orig | 11 | 407 | 64.4 | +26.46 [+8.26, +44.17] |
| SPY | S1-orig | 12 | 407 | 66.1 | +26.35 [+9.47, +42.88] |
| SPY | S1-orig | 13 | 407 | 65.8 | +28.62 [+9.62, +46.12] |
| SPY | S1-orig | 14 | 407 | 66.8 | +23.52 [+4.85, +41.51] |
| SPY | S1-orig | 15 | 407 | 65.1 | +25.57 [+6.88, +43.78] |
| SPY | S2-orig | 11 | 407 | 72.7 | +23.27 [+4.90, +39.47] |
| SPY | S2-orig | 12 | 406 | 73.9 | +29.34 [+15.82, +42.04] |
| SPY | S2-orig | 13 | 407 | 73.7 | +21.37 [+4.38, +36.35] |
| SPY | S2-orig | 14 | 407 | 74.9 | +20.76 [+4.55, +35.84] |
| SPY | S2-orig | 15 | 407 | 73.5 | +19.58 [+4.84, +34.19] |
| SPY | PH-S1-E1 | 11 | 407 | 68.6 | +6.96 [-10.54, +22.23] |
| SPY | PH-S1-E1 | 12 | 406 | 68.7 | +13.70 [+1.30, +25.40] |
| SPY | PH-S1-E1 | 13 | 407 | 68.8 | +6.34 [-9.88, +20.87] |
| SPY | PH-S1-E1 | 14 | 407 | 72.5 | +6.84 [-8.77, +21.21] |
| SPY | PH-S1-E1 | 15 | 407 | 69.5 | +4.98 [-9.18, +18.55] |
| SPY | PH-S2-E1 | 11 | 407 | 68.6 | +6.96 [-10.54, +22.23] |
| SPY | PH-S2-E1 | 12 | 406 | 68.7 | +13.70 [+1.30, +25.40] |
| SPY | PH-S2-E1 | 13 | 407 | 68.8 | +6.34 [-9.88, +20.87] |
| SPY | PH-S2-E1 | 14 | 407 | 72.5 | +6.84 [-8.77, +21.21] |
| SPY | PH-S2-E1 | 15 | 407 | 69.5 | +4.98 [-9.18, +18.55] |
| QQQ | S1 | 11 | 406 | 66.3 | +42.72 [+22.93, +62.33] |
| QQQ | S1 | 12 | 407 | 66.1 | +30.98 [+10.68, +51.37] |
| QQQ | S1 | 13 | 407 | 66.6 | +27.78 [+4.81, +48.92] |
| QQQ | S1 | 14 | 407 | 65.8 | +30.74 [+10.82, +50.03] |
| QQQ | S1 | 15 | 407 | 63.6 | +17.50 [-3.22, +37.61] |
| QQQ | S2 | 11 | 406 | 66.3 | +42.72 [+22.93, +62.33] |
| QQQ | S2 | 12 | 407 | 66.1 | +30.98 [+10.68, +51.37] |
| QQQ | S2 | 13 | 407 | 66.6 | +27.78 [+4.81, +48.92] |
| QQQ | S2 | 14 | 407 | 65.8 | +30.74 [+10.82, +50.03] |
| QQQ | S2 | 15 | 407 | 63.6 | +17.50 [-3.22, +37.61] |
| QQQ | S1-orig | 11 | 406 | 66.3 | +42.72 [+22.93, +62.33] |
| QQQ | S1-orig | 12 | 407 | 66.1 | +30.98 [+10.68, +51.37] |
| QQQ | S1-orig | 13 | 407 | 66.6 | +27.78 [+4.81, +48.92] |
| QQQ | S1-orig | 14 | 407 | 65.8 | +30.74 [+10.82, +50.03] |
| QQQ | S1-orig | 15 | 407 | 63.6 | +17.50 [-3.22, +37.61] |
| QQQ | S2-orig | 11 | 406 | 67.7 | +48.69 [+27.53, +69.65] |
| QQQ | S2-orig | 12 | 407 | 68.6 | +39.92 [+16.90, +61.30] |
| QQQ | S2-orig | 13 | 407 | 68.3 | +32.26 [+7.64, +54.34] |
| QQQ | S2-orig | 14 | 407 | 68.3 | +44.37 [+24.41, +63.87] |
| QQQ | S2-orig | 15 | 407 | 66.1 | +28.98 [+6.93, +49.87] |
| QQQ | PH-S1-E1 | 11 | 406 | 65.5 | +16.19 [+3.15, +29.10] |
| QQQ | PH-S1-E1 | 12 | 407 | 63.9 | +14.35 [+1.59, +26.84] |
| QQQ | PH-S1-E1 | 13 | 407 | 62.2 | +1.05 [-12.64, +13.90] |
| QQQ | PH-S1-E1 | 14 | 407 | 63.6 | +11.58 [-1.05, +23.92] |
| QQQ | PH-S1-E1 | 15 | 407 | 62.4 | +4.11 [-9.04, +16.61] |
| QQQ | PH-S2-E1 | 11 | 406 | 71.7 | +18.47 [+3.58, +33.43] |
| QQQ | PH-S2-E1 | 12 | 407 | 69.5 | +12.19 [-4.07, +27.91] |
| QQQ | PH-S2-E1 | 13 | 407 | 69.8 | +3.19 [-14.02, +18.84] |
| QQQ | PH-S2-E1 | 14 | 407 | 71.3 | +11.03 [-4.68, +25.85] |
| QQQ | PH-S2-E1 | 15 | 407 | 67.3 | +2.27 [-13.85, +17.84] |
| IWM | S1 | 11 | 407 | 62.2 | +12.74 [+4.11, +21.29] |
| IWM | S1 | 12 | 407 | 59.7 | +6.11 [-3.64, +15.53] |
| IWM | S1 | 13 | 407 | 61.9 | +9.19 [+0.26, +17.90] |
| IWM | S1 | 14 | 407 | 61.7 | +5.30 [-4.44, +14.21] |
| IWM | S1 | 15 | 407 | 60.4 | +3.45 [-5.38, +11.76] |
| IWM | S2 | 11 | 407 | 65.1 | +16.13 [+6.55, +25.34] |
| IWM | S2 | 12 | 407 | 61.9 | +9.28 [-0.55, +18.76] |
| IWM | S2 | 13 | 407 | 64.1 | +13.44 [+4.03, +22.43] |
| IWM | S2 | 14 | 407 | 64.4 | +6.49 [-4.68, +16.32] |
| IWM | S2 | 15 | 407 | 63.1 | +7.23 [-1.81, +15.93] |
| IWM | S1-orig | 11 | 407 | 62.2 | +12.74 [+4.11, +21.29] |
| IWM | S1-orig | 12 | 407 | 59.7 | +6.11 [-3.64, +15.53] |
| IWM | S1-orig | 13 | 407 | 61.9 | +9.19 [+0.26, +17.90] |
| IWM | S1-orig | 14 | 407 | 61.7 | +5.30 [-4.44, +14.21] |
| IWM | S1-orig | 15 | 407 | 60.4 | +3.45 [-5.38, +11.76] |
| IWM | S2-orig | 11 | 407 | 65.1 | +16.13 [+6.55, +25.34] |
| IWM | S2-orig | 12 | 407 | 61.9 | +9.28 [-0.55, +18.76] |
| IWM | S2-orig | 13 | 407 | 64.1 | +13.44 [+4.03, +22.43] |
| IWM | S2-orig | 14 | 407 | 64.4 | +6.49 [-4.68, +16.32] |
| IWM | S2-orig | 15 | 407 | 63.1 | +7.23 [-1.81, +15.93] |
| IWM | PH-S1-E1 | 11 | 427 | 74.5 | +5.28 [-1.07, +10.99] |
| IWM | PH-S1-E1 | 12 | 427 | 70.3 | -1.59 [-11.77, +6.68] |
| IWM | PH-S1-E1 | 13 | 427 | 73.5 | +3.37 [-3.95, +10.13] |
| IWM | PH-S1-E1 | 14 | 427 | 70.7 | -6.40 [-17.82, +2.99] |
| IWM | PH-S1-E1 | 15 | 425 | 73.2 | -0.24 [-7.80, +6.50] |
| IWM | PH-S2-E1 | 11 | 427 | 74.5 | +5.28 [-1.07, +10.99] |
| IWM | PH-S2-E1 | 12 | 427 | 70.3 | -1.59 [-11.77, +6.68] |
| IWM | PH-S2-E1 | 13 | 427 | 73.5 | +3.37 [-3.95, +10.13] |
| IWM | PH-S2-E1 | 14 | 427 | 70.7 | -6.40 [-17.82, +2.99] |
| IWM | PH-S2-E1 | 15 | 425 | 73.2 | -0.24 [-7.80, +6.50] |
| SPY+QQQ | S1 | 11 | 813 | 65.3 | +34.58 [+18.94, +50.61] |
| SPY+QQQ | S1 | 12 | 814 | 66.1 | +28.67 [+13.39, +43.78] |
| SPY+QQQ | S1 | 13 | 814 | 66.2 | +28.20 [+9.67, +44.95] |
| SPY+QQQ | S1 | 14 | 814 | 66.3 | +27.13 [+11.26, +42.44] |
| SPY+QQQ | S1 | 15 | 814 | 64.4 | +21.53 [+4.34, +37.61] |
| SPY+QQQ | S2 | 11 | 813 | 67.3 | +37.68 [+18.62, +56.09] |
| SPY+QQQ | S2 | 12 | 814 | 68.3 | +39.12 [+22.18, +55.47] |
| SPY+QQQ | S2 | 13 | 814 | 67.9 | +33.03 [+12.37, +51.46] |
| SPY+QQQ | S2 | 14 | 814 | 68.7 | +35.67 [+18.59, +51.93] |
| SPY+QQQ | S2 | 15 | 814 | 66.6 | +29.33 [+10.42, +47.21] |
| SPY+QQQ | S1-orig | 11 | 813 | 65.3 | +34.58 [+18.94, +50.61] |
| SPY+QQQ | S1-orig | 12 | 814 | 66.1 | +28.67 [+13.39, +43.78] |
| SPY+QQQ | S1-orig | 13 | 814 | 66.2 | +28.20 [+9.67, +44.95] |
| SPY+QQQ | S1-orig | 14 | 814 | 66.3 | +27.13 [+11.26, +42.44] |
| SPY+QQQ | S1-orig | 15 | 814 | 64.4 | +21.53 [+4.34, +37.61] |
| SPY+QQQ | S2-orig | 11 | 813 | 67.3 | +37.68 [+18.62, +56.09] |
| SPY+QQQ | S2-orig | 12 | 814 | 68.3 | +39.12 [+22.18, +55.47] |
| SPY+QQQ | S2-orig | 13 | 814 | 67.9 | +33.03 [+12.37, +51.46] |
| SPY+QQQ | S2-orig | 14 | 814 | 68.7 | +35.67 [+18.59, +51.93] |
| SPY+QQQ | S2-orig | 15 | 814 | 66.6 | +29.33 [+10.42, +47.21] |
| SPY+QQQ | PH-S1-E1 | 11 | 813 | 70.1 | +12.71 [-0.38, +25.57] |
| SPY+QQQ | PH-S1-E1 | 12 | 813 | 69.1 | +12.94 [+0.89, +24.57] |
| SPY+QQQ | PH-S1-E1 | 13 | 814 | 69.3 | +4.76 [-9.99, +18.28] |
| SPY+QQQ | PH-S1-E1 | 14 | 814 | 71.9 | +8.93 [-4.52, +21.70] |
| SPY+QQQ | PH-S1-E1 | 15 | 814 | 68.4 | +3.63 [-9.84, +16.03] |
| SPY+QQQ | PH-S2-E1 | 11 | 813 | 70.1 | +12.71 [-0.38, +25.57] |
| SPY+QQQ | PH-S2-E1 | 12 | 813 | 69.1 | +12.94 [+0.89, +24.57] |
| SPY+QQQ | PH-S2-E1 | 13 | 814 | 69.3 | +4.76 [-9.99, +18.28] |
| SPY+QQQ | PH-S2-E1 | 14 | 814 | 71.9 | +8.93 [-4.52, +21.70] |
| SPY+QQQ | PH-S2-E1 | 15 | 814 | 68.4 | +3.63 [-9.84, +16.03] |

## 4. Full grid in TEST: lower bounds > 0 vs chance, and the max-statistic reality check

Chance count: recentred joint day bootstrap (seed 8, 5,000 draws, correlation across configurations kept).  Reality check: studentised max-t over configurations with TEST n ≥ 30; Romano–Wolf step-down at FWER 5 %.  "band" = the original run on band data (`../etf/results/grid_test_summary.json`).

| scope | data | distinct configs | TEST days | TEST LB > 0 | chance mean / p95 | LB > 0 among TRAIN-win≥70 | chance mean / p95 | win ≥ 70 % & LB > 0 | White RC best t (config), p | Romano–Wolf rejections | Spearman TRAIN vs TEST mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | band | 1890 | 441 | 240 | 31.8 / 150 | 139 of 974 | 14.3 / 73 | 174 | 6.333 (`S0.5|13:00|tp0|st0|E2|F3`), p = 0.0 | 102 | 0.73 |
| SPY | complete | 1890 | 441 | 161 | 26.5 / 134 | 92 of 990 | 12.3 / 62 | 114 | 6.388 (`S1|14:05|tp0|st0|E2|F3`), p = 0.0 | 78 | 0.72 |
| QQQ | band | 1890 | 441 | 314 | 32.6 / 138 | 192 of 1078 | 17.1 / 75 | 212 | 6.94 (`S1.5|14:05|tp0|st0|E2|F3`), p = 0.0 | 110 | 0.782 |
| QQQ | complete | 1890 | 441 | 240 | 29.5 / 143 | 134 of 1079 | 15.2 / 77 | 155 | 5.467 (`S1.5|14:05|tp0|st0|E2|F0`), p = 0.0 | 76 | 0.773 |
| IWM | band | 1890 | 441 | 63 | 30.3 / 117 | 37 of 708 | 9.1 / 45 | 33 | 4.768 (`S0.5|14:05|tp0|st0|E2|F0`), p = 0.0002 | 20 | 0.673 |
| IWM | complete | 1890 | 441 | 55 | 23.0 / 105 | 29 of 766 | 8.6 / 48 | 25 | 5.295 (`S1|14:05|tp0|st0|E2|F0`), p = 0.0 | 20 | 0.683 |
| SPY+QQQ | band | 1890 | 441 | 293 | 32.3 / 154 | 175 of 1024 | 15.6 / 76 | 198 | 6.805 (`S1.5|14:05|tp0|st0|E2|F3`), p = 0.0 | 127 | 0.779 |
| SPY+QQQ | complete | 1890 | 441 | 193 | 27.5 / 144 | 107 of 1045 | 13.8 / 74 | 126 | 5.893 (`S1.5|14:05|tp0|st0|E2|F3`), p = 0.0 | 81 | 0.771 |

Romano–Wolf-rejected configurations by exit and structure (TEST, complete data):

| scope | E1 | E2 | straddle/strangle | iron condor |
|---|---|---|---|---|
| SPY | 4 | 74 | 77 | 1 |
| QQQ | 0 | 76 | 76 | 0 |
| IWM | 0 | 20 | 20 | 0 |
| SPY+QQQ | 2 | 79 | 81 | 0 |

TEST lower-bound quantiles over the distinct grid (complete data): SPY {'5': -28.82, '25': -15.59, '50': -10.08, '75': -5.42, '95': 3.27, '100': 26.15}; QQQ {'5': -25.18, '25': -13.97, '50': -9.15, '75': -3.97, '95': 4.97, '100': 22.99}; IWM {'5': -20.35, '25': -13.92, '50': -10.43, '75': -7.02, '95': -1.43, '100': 6.56}; SPY+QQQ {'5': -25.03, '25': -14.31, '50': -9.31, '75': -4.38, '95': 3.89, '100': 23.08}

## 5. Win rate vs expectancy, rule effects and coverage (complete data)

Median over the distinct configurations in each cell:

| scope | structure-k | exit | TRAIN median win % | TRAIN median mean $ | TRAIN LB>0 | TEST median win % | TEST median mean $ | TEST LB>0 |
|---|---|---|---|---|---|---|---|---|
| SPY | I0.5 | E1 | 65.1 | -6.10 | 0 | 65.1 | -9.36 | 0 |
| SPY | I0.5 | E2 | 71.3 | -4.71 | 7 | 70.5 | -3.51 | 7 |
| SPY | I1 | E1 | 63.4 | -7.05 | 0 | 64.8 | -8.12 | 0 |
| SPY | I1 | E2 | 68.5 | -6.47 | 0 | 72.8 | -5.22 | 4 |
| SPY | I1.5 | E1 | 41.9 | -7.28 | 0 | 53.3 | -7.26 | 0 |
| SPY | I1.5 | E2 | 43.1 | -6.47 | 0 | 55.1 | -6.07 | 0 |
| SPY | S0 | E1 | 64.3 | +3.53 | 14 | 66.1 | -2.58 | 0 |
| SPY | S0 | E2 | 65.3 | +9.42 | 51 | 69.6 | +14.79 | 53 |
| SPY | S0.5 | E1 | 77.1 | +1.47 | 20 | 73.7 | -0.85 | 1 |
| SPY | S0.5 | E2 | 78.5 | +2.56 | 42 | 77.9 | +5.95 | 33 |
| SPY | S1 | E1 | 79.4 | -1.67 | 24 | 80.3 | -0.70 | 4 |
| SPY | S1 | E2 | 80.6 | -1.04 | 35 | 82.0 | +2.53 | 22 |
| SPY | S1.5 | E1 | 80.9 | -2.34 | 25 | 83.0 | -0.85 | 12 |
| SPY | S1.5 | E2 | 81.7 | -1.87 | 33 | 83.8 | +0.84 | 25 |
| QQQ | I0.5 | E1 | 68.8 | -6.22 | 0 | 67.3 | -8.79 | 0 |
| QQQ | I0.5 | E2 | 71.6 | -2.31 | 16 | 73.5 | +0.78 | 12 |
| QQQ | I1 | E1 | 67.1 | -7.12 | 0 | 71.9 | -7.10 | 0 |
| QQQ | I1 | E2 | 71.1 | -4.98 | 6 | 74.8 | -2.83 | 8 |
| QQQ | I1.5 | E1 | 48.9 | -7.58 | 0 | 63.0 | -6.81 | 0 |
| QQQ | I1.5 | E2 | 50.0 | -6.66 | 0 | 65.0 | -4.69 | 0 |
| QQQ | S0 | E1 | 65.5 | +3.42 | 20 | 66.2 | -0.99 | 0 |
| QQQ | S0 | E2 | 67.4 | +16.12 | 77 | 69.4 | +21.83 | 68 |
| QQQ | S0.5 | E1 | 76.6 | +1.73 | 25 | 76.0 | +2.30 | 0 |
| QQQ | S0.5 | E2 | 78.3 | +6.16 | 59 | 79.9 | +11.57 | 47 |
| QQQ | S1 | E1 | 79.7 | -0.42 | 30 | 81.1 | +1.80 | 5 |
| QQQ | S1 | E2 | 81.5 | +1.33 | 40 | 84.1 | +5.61 | 49 |
| QQQ | S1.5 | E1 | 82.1 | -1.83 | 27 | 83.2 | -0.12 | 14 |
| QQQ | S1.5 | E2 | 83.8 | -1.41 | 32 | 83.9 | +0.90 | 37 |
| IWM | I0.5 | E1 | 61.5 | -6.61 | 0 | 58.8 | -10.53 | 0 |
| IWM | I0.5 | E2 | 61.5 | -5.88 | 3 | 65.2 | -7.78 | 3 |
| IWM | I1 | E1 | 43.2 | -6.95 | 0 | 48.2 | -9.11 | 0 |
| IWM | I1 | E2 | 43.2 | -6.57 | 0 | 48.2 | -8.09 | 0 |
| IWM | I1.5 | E1 | 24.3 | -7.28 | 0 | 27.6 | -9.00 | 0 |
| IWM | I1.5 | E2 | 24.3 | -7.12 | 0 | 28.1 | -8.27 | 0 |
| IWM | S0 | E1 | 66.7 | +2.81 | 12 | 58.3 | -10.97 | 0 |
| IWM | S0 | E2 | 67.3 | +7.22 | 52 | 63.9 | -1.28 | 24 |
| IWM | S0.5 | E1 | 76.9 | +0.12 | 22 | 75.2 | -5.14 | 0 |
| IWM | S0.5 | E2 | 79.8 | +0.82 | 29 | 76.9 | -2.49 | 13 |
| IWM | S1 | E1 | 77.4 | -1.51 | 8 | 76.6 | -4.04 | 3 |
| IWM | S1 | E2 | 78.0 | -0.79 | 15 | 79.4 | -2.67 | 9 |
| IWM | S1.5 | E1 | 67.8 | -1.85 | 7 | 74.9 | -3.63 | 0 |
| IWM | S1.5 | E2 | 68.3 | -1.62 | 14 | 74.9 | -3.08 | 3 |
| SPY+QQQ | I0.5 | E1 | 66.8 | -6.33 | 0 | 66.3 | -9.42 | 0 |
| SPY+QQQ | I0.5 | E2 | 71.6 | -3.67 | 10 | 72.0 | -1.75 | 10 |
| SPY+QQQ | I1 | E1 | 64.2 | -7.12 | 0 | 67.8 | -7.67 | 0 |
| SPY+QQQ | I1 | E2 | 69.8 | -5.57 | 1 | 73.5 | -3.83 | 5 |
| SPY+QQQ | I1.5 | E1 | 45.3 | -7.50 | 0 | 57.9 | -6.95 | 0 |
| SPY+QQQ | I1.5 | E2 | 46.0 | -6.50 | 0 | 61.3 | -5.16 | 0 |
| SPY+QQQ | S0 | E1 | 64.8 | +3.27 | 16 | 65.9 | -1.64 | 0 |
| SPY+QQQ | S0 | E2 | 66.3 | +12.94 | 71 | 69.5 | +17.15 | 60 |
| SPY+QQQ | S0.5 | E1 | 77.4 | +1.15 | 24 | 74.9 | +0.66 | 0 |
| SPY+QQQ | S0.5 | E2 | 78.5 | +4.23 | 47 | 78.8 | +8.58 | 40 |
| SPY+QQQ | S1 | E1 | 79.8 | -1.10 | 31 | 80.7 | +0.62 | 5 |
| SPY+QQQ | S1 | E2 | 81.0 | +0.30 | 37 | 83.1 | +4.13 | 32 |
| SPY+QQQ | S1.5 | E1 | 81.4 | -2.21 | 28 | 83.2 | -0.67 | 10 |
| SPY+QQQ | S1.5 | E2 | 82.6 | -1.68 | 34 | 83.7 | +0.69 | 31 |

By TRAIN win-rate bin:

| scope | TRAIN win % bin | configs | TRAIN median mean $ | TRAIN LB>0 | TEST median win % | TEST median mean $ | TEST LB>0 | TEST mean > 0 (% of configs) |
|---|---|---|---|---|---|---|---|---|
| SPY | 0-50 | 210 | -8.00 | 0 | 46.5 | -7.62 | 0 | 0.0 |
| SPY | 50-60 | 137 | -3.58 | 5 | 59.5 | -6.82 | 1 | 16.8 |
| SPY | 60-70 | 553 | +1.71 | 140 | 66.1 | -1.17 | 68 | 47.7 |
| SPY | 70-80 | 498 | -1.34 | 84 | 76.0 | -1.68 | 45 | 36.5 |
| SPY | 80-90 | 403 | -2.10 | 20 | 85.0 | -0.97 | 32 | 40.0 |
| SPY | 90-100 | 89 | -3.15 | 2 | 93.9 | +2.09 | 15 | 71.9 |
| QQQ | 0-50 | 170 | -7.47 | 0 | 53.1 | -6.95 | 0 | 0.0 |
| QQQ | 50-60 | 138 | -3.65 | 8 | 59.7 | -5.55 | 2 | 18.8 |
| QQQ | 60-70 | 503 | +3.56 | 170 | 66.4 | +2.37 | 104 | 55.1 |
| QQQ | 70-80 | 551 | -0.79 | 112 | 76.2 | +0.74 | 74 | 53.5 |
| QQQ | 80-90 | 436 | -1.57 | 40 | 86.1 | +0.31 | 44 | 51.8 |
| QQQ | 90-100 | 92 | -3.88 | 2 | 94.1 | +2.59 | 16 | 71.7 |
| IWM | 0-50 | 447 | -7.46 | 0 | 31.3 | -9.17 | 0 | 0.0 |
| IWM | 50-60 | 234 | -4.30 | 1 | 55.8 | -7.10 | 0 | 0.0 |
| IWM | 60-70 | 443 | +0.12 | 85 | 63.3 | -5.43 | 26 | 18.5 |
| IWM | 70-80 | 428 | -1.39 | 33 | 74.0 | -4.74 | 8 | 11.9 |
| IWM | 80-90 | 260 | -0.19 | 33 | 83.2 | -2.29 | 16 | 25.0 |
| IWM | 90-100 | 78 | +0.36 | 10 | 90.9 | -1.74 | 5 | 39.7 |
| SPY+QQQ | 0-50 | 200 | -7.72 | 0 | 51.2 | -7.08 | 0 | 0.0 |
| SPY+QQQ | 50-60 | 119 | -2.27 | 10 | 58.4 | -5.31 | 1 | 17.6 |
| SPY+QQQ | 60-70 | 526 | +2.88 | 161 | 66.1 | +1.11 | 85 | 53.2 |
| SPY+QQQ | 70-80 | 540 | -1.04 | 101 | 75.9 | -0.64 | 62 | 45.4 |
| SPY+QQQ | 80-90 | 414 | -1.91 | 23 | 85.4 | -0.51 | 32 | 45.4 |
| SPY+QQQ | 90-100 | 91 | -3.84 | 4 | 94.0 | +1.87 | 13 | 75.8 |

Matched-pair rule effects (SPY+QQQ and IWM; per-ticker rows in `results/marginal_effects.csv`):

| scope | period | factor: ref → alt | pairs | median Δ win (pts) | median Δ mean $ | share with higher mean | median Δ LB $ | note |
|---|---|---|---|---|---|---|---|---|
| IWM | TRAIN | tp: 0 → 25 | 672 | -8.38 | -6.02 | 0.0 % | -4.61 |  |
| IWM | TRAIN | tp: 0 → 50 | 672 | +1.79 | -4.28 | 1.8 % | -3.59 |  |
| IWM | TRAIN | st: 0 → 1 | 672 | -18.10 | -2.28 | 21.1 % | +0.60 |  |
| IWM | TRAIN | st: 0 → 2 | 672 | -5.97 | -0.82 | 36.9 % | +0.91 |  |
| IWM | TRAIN | st: 2 → 1 | 672 | -11.56 | -1.35 | 14.6 % | -0.59 |  |
| IWM | TRAIN | ex: E1 → E2 | 1008 | +0.60 | +0.53 | 72.8 % | +0.42 | E0 = diagnostic buy-back-all at 15:55 |
| IWM | TRAIN | ex: E1 → E0 | 1008 | -0.62 | -0.39 | 0.0 % | -0.44 | E0 = diagnostic buy-back-all at 15:55 |
| IWM | TRAIN | ex: E0 → E1 | 1008 | +0.62 | +0.39 | 82.9 % | +0.44 | leave-cheap-legs effect |
| IWM | TRAIN | filt: F0 → F1 | 378 | -0.25 | +0.19 | 56.3 % | +0.89 | entries other than 14:05 |
| IWM | TRAIN | filt: F0 → F2 | 378 | +0.00 | -0.07 | 44.7 % | +0.12 | entries other than 14:05 |
| IWM | TRAIN | filt: F0 → F3 | 378 | -0.05 | +0.30 | 57.1 % | +0.86 | entries other than 14:05 |
| IWM | TRAIN | struct: S → I | 864 | -25.11 | -5.79 | 0.2 % | -5.71 | iron condor vs strangle at the same k |
| IWM | TRAIN | kk: 0 → 0.5 | 288 | +9.11 | -3.33 | 21.2 % | +0.75 | strangle k vs straddle |
| IWM | TRAIN | kk: 0 → 1 | 288 | +8.15 | -4.73 | 16.0 % | +0.71 | strangle k vs straddle |
| IWM | TRAIN | kk: 0 → 1.5 | 288 | +0.01 | -5.49 | 12.8 % | +1.41 | strangle k vs straddle |
| IWM | TRAIN | entry: 13:00 → 10:00 | 504 | -2.38 | -3.43 | 13.3 % | -5.85 |  |
| IWM | TRAIN | entry: 13:00 → 11:00 | 504 | +2.48 | +0.11 | 52.4 % | -0.47 |  |
| IWM | TRAIN | entry: 13:00 → 14:05 | 504 | +1.80 | +0.39 | 64.3 % | +0.52 |  |
| IWM | TEST | tp: 0 → 25 | 672 | +1.96 | -3.82 | 10.0 % | -2.46 |  |
| IWM | TEST | tp: 0 → 50 | 672 | +1.59 | -3.27 | 7.4 % | -2.64 |  |
| IWM | TEST | st: 0 → 1 | 672 | -16.71 | -2.29 | 16.8 % | -0.26 |  |
| IWM | TEST | st: 0 → 2 | 672 | -5.82 | -1.02 | 27.8 % | +0.00 |  |
| IWM | TEST | st: 2 → 1 | 672 | -11.31 | -1.01 | 18.5 % | -0.43 |  |
| IWM | TEST | ex: E1 → E2 | 1008 | +1.65 | +1.58 | 85.2 % | +1.69 | E0 = diagnostic buy-back-all at 15:55 |
| IWM | TEST | ex: E1 → E0 | 1008 | -0.47 | -0.41 | 0.8 % | -0.44 | E0 = diagnostic buy-back-all at 15:55 |
| IWM | TEST | ex: E0 → E1 | 1008 | +0.47 | +0.41 | 89.4 % | +0.44 | leave-cheap-legs effect |
| IWM | TEST | filt: F0 → F1 | 378 | -0.52 | -0.71 | 6.3 % | -0.78 | entries other than 14:05 |
| IWM | TEST | filt: F0 → F2 | 378 | -0.28 | -0.47 | 17.5 % | -0.45 | entries other than 14:05 |
| IWM | TEST | filt: F0 → F3 | 378 | -0.61 | -0.65 | 9.3 % | -0.94 | entries other than 14:05 |
| IWM | TEST | struct: S → I | 864 | -26.07 | -5.37 | 0.0 % | -4.36 | iron condor vs strangle at the same k |
| IWM | TEST | kk: 0 → 0.5 | 288 | +11.79 | +2.01 | 66.0 % | +4.85 | strangle k vs straddle |
| IWM | TEST | kk: 0 → 1 | 288 | +13.61 | +2.61 | 66.0 % | +6.91 | strangle k vs straddle |
| IWM | TEST | kk: 0 → 1.5 | 288 | +10.78 | +2.55 | 65.3 % | +9.10 | strangle k vs straddle |
| IWM | TEST | entry: 13:00 → 10:00 | 504 | -1.17 | -2.18 | 16.1 % | -3.38 |  |
| IWM | TEST | entry: 13:00 → 11:00 | 504 | -1.04 | -1.85 | 30.6 % | -2.42 |  |
| IWM | TEST | entry: 13:00 → 14:05 | 504 | -2.69 | +2.12 | 93.1 % | +4.01 |  |
| SPY+QQQ | TRAIN | tp: 0 → 25 | 672 | +11.72 | -8.10 | 0.0 % | -6.62 |  |
| SPY+QQQ | TRAIN | tp: 0 → 50 | 672 | +5.62 | -5.94 | 2.2 % | -5.17 |  |
| SPY+QQQ | TRAIN | st: 0 → 1 | 672 | -12.76 | +0.67 | 62.9 % | +3.45 |  |
| SPY+QQQ | TRAIN | st: 0 → 2 | 672 | -4.82 | +0.84 | 71.1 % | +2.98 |  |
| SPY+QQQ | TRAIN | st: 2 → 1 | 672 | -8.00 | -0.55 | 28.7 % | +0.21 |  |
| SPY+QQQ | TRAIN | ex: E1 → E2 | 1008 | +1.51 | +1.92 | 97.2 % | +1.85 | E0 = diagnostic buy-back-all at 15:55 |
| SPY+QQQ | TRAIN | ex: E1 → E0 | 1008 | -0.19 | -0.30 | 1.2 % | -0.34 | E0 = diagnostic buy-back-all at 15:55 |
| SPY+QQQ | TRAIN | ex: E0 → E1 | 1008 | +0.19 | +0.30 | 96.4 % | +0.34 | leave-cheap-legs effect |
| SPY+QQQ | TRAIN | filt: F0 → F1 | 378 | -0.14 | -0.39 | 18.3 % | -0.33 | entries other than 14:05 |
| SPY+QQQ | TRAIN | filt: F0 → F2 | 378 | +0.08 | -0.08 | 43.9 % | -0.05 | entries other than 14:05 |
| SPY+QQQ | TRAIN | filt: F0 → F3 | 378 | +0.02 | +0.00 | 50.3 % | +0.05 | entries other than 14:05 |
| SPY+QQQ | TRAIN | struct: S → I | 864 | -10.86 | -6.27 | 0.3 % | -5.15 | iron condor vs strangle at the same k |
| SPY+QQQ | TRAIN | kk: 0 → 0.5 | 288 | +8.28 | -3.49 | 27.1 % | -0.04 | strangle k vs straddle |
| SPY+QQQ | TRAIN | kk: 0 → 1 | 288 | +11.49 | -6.21 | 16.7 % | -1.04 | strangle k vs straddle |
| SPY+QQQ | TRAIN | kk: 0 → 1.5 | 288 | +12.61 | -6.93 | 9.0 % | -0.58 | strangle k vs straddle |
| SPY+QQQ | TRAIN | entry: 13:00 → 10:00 | 504 | +0.09 | -0.36 | 40.3 % | -1.94 |  |
| SPY+QQQ | TRAIN | entry: 13:00 → 11:00 | 504 | +1.66 | +1.21 | 86.7 % | +0.46 |  |
| SPY+QQQ | TRAIN | entry: 13:00 → 14:05 | 504 | +1.32 | +1.35 | 97.2 % | +2.16 |  |
| SPY+QQQ | TEST | tp: 0 → 25 | 672 | +12.81 | -7.09 | 1.6 % | -3.26 |  |
| SPY+QQQ | TEST | tp: 0 → 50 | 672 | +5.85 | -6.15 | 4.9 % | -4.66 |  |
| SPY+QQQ | TEST | st: 0 → 1 | 672 | -12.62 | -2.89 | 20.1 % | +0.83 |  |
| SPY+QQQ | TEST | st: 0 → 2 | 672 | -4.02 | -0.89 | 36.3 % | +1.35 |  |
| SPY+QQQ | TEST | st: 2 → 1 | 672 | -8.49 | -1.74 | 17.1 % | -0.54 |  |
| SPY+QQQ | TEST | ex: E1 → E2 | 1008 | +2.61 | +4.97 | 98.2 % | +4.85 | E0 = diagnostic buy-back-all at 15:55 |
| SPY+QQQ | TEST | ex: E1 → E0 | 1008 | -0.12 | -0.35 | 4.1 % | -0.37 | E0 = diagnostic buy-back-all at 15:55 |
| SPY+QQQ | TEST | ex: E0 → E1 | 1008 | +0.12 | +0.35 | 94.0 % | +0.37 | leave-cheap-legs effect |
| SPY+QQQ | TEST | filt: F0 → F1 | 378 | -0.33 | -1.16 | 0.8 % | -1.39 | entries other than 14:05 |
| SPY+QQQ | TEST | filt: F0 → F2 | 378 | -0.34 | -0.78 | 3.7 % | -0.79 | entries other than 14:05 |
| SPY+QQQ | TEST | filt: F0 → F3 | 378 | +0.33 | +0.16 | 56.1 % | -0.18 | entries other than 14:05 |
| SPY+QQQ | TEST | struct: S → I | 864 | -9.18 | -8.37 | 0.0 % | -5.87 | iron condor vs strangle at the same k |
| SPY+QQQ | TEST | kk: 0 → 0.5 | 288 | +7.86 | -3.28 | 39.6 % | +2.87 | strangle k vs straddle |
| SPY+QQQ | TEST | kk: 0 → 1 | 288 | +12.37 | -3.88 | 34.7 % | +5.45 | strangle k vs straddle |
| SPY+QQQ | TEST | kk: 0 → 1.5 | 288 | +14.23 | -5.07 | 34.0 % | +6.53 | strangle k vs straddle |
| SPY+QQQ | TEST | entry: 13:00 → 10:00 | 504 | -2.61 | -1.23 | 39.1 % | -3.41 |  |
| SPY+QQQ | TEST | entry: 13:00 → 11:00 | 504 | -2.21 | -4.22 | 10.1 % | -7.34 |  |
| SPY+QQQ | TEST | entry: 13:00 → 14:05 | 504 | -2.89 | -0.39 | 44.8 % | +2.05 |  |

Coverage (share of sessions with a trade, mean over the four entries; `results/coverage.csv`):

| ticker | period | sessions | S0 | S0.5 | S1 | S1.5 | I0.5 | I1 | I1.5 |
|---|---|---|---|---|---|---|---|---|---|
| IWM | TEST | 441 | 100.0 % | 100.0 % | 99.5 % | 97.6 % | 93.4 % | 84.2 % | 65.8 % |
| IWM | TRAIN | 174 | 100.0 % | 99.4 % | 98.6 % | 95.7 % | 89.4 % | 75.9 % | 52.3 % |
| QQQ | TEST | 441 | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 98.4 % |
| QQQ | TRAIN | 530 | 100.0 % | 99.8 % | 99.8 % | 100.0 % | 99.8 % | 99.8 % | 96.1 % |
| SPY | TEST | 441 | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 99.9 % | 99.2 % |
| SPY | TRAIN | 530 | 100.0 % | 99.9 % | 99.8 % | 100.0 % | 99.8 % | 99.6 % | 97.1 % |

## 6. Settlement realism of hold-to-expiry (E2) — optimistic for the ETFs

SPY, QQQ and IWM options are American and physically settled; they trade until 16:15 ET and can be exercised on after-hours moves.  Every E2 number in this file values the legs at intrinsic against the 16:00 close (15:59-bar close) and is **optimistic**.  Only SPY can be re-valued (inputs: EOD close and 17:15 quote mid per date in `../etf/results/diag_settlement_spy.csv`, unchanged).  Columns as in the original diagnostic B; `results/settlement_spy.csv`.

| config | used by | period | trades (with after-hours data) | (1) as run, 16:00 | (2) EOD close | (3) auto-exercise, shares closed 17:15 | (4) rational after-hours exercise | (5) pessimistic |
|---|---|---|---|---|---|---|---|---|
| `S0|14:05|tp0|st1|E2|F3` | SPY S1; SPY S1-orig; SPY+QQQ S1; SPY+QQQ S1-orig; original diagnostic set | TRAIN | 490 (490) | +26.41 [+18.46, +34.61] | +26.11 [+18.15, +34.30] | +26.98 [+17.46, +36.69] | +20.56 [+12.17, +29.26] | +6.82 [-1.21, +15.00] |
| `S0|14:05|tp50|st2|E2|F3` | SPY S2 | TRAIN | 490 (490) | +21.71 [+13.45, +30.09] | +21.31 [+13.06, +29.75] | +22.21 [+12.92, +31.56] | +18.05 [+9.37, +26.50] | +5.30 [-3.19, +13.80] |
| `S0.5|14:05|tp0|st2|E2|F3` | SPY S2-orig; original diagnostic set | TRAIN | 489 (489) | +18.73 [+13.48, +23.95] | +18.61 [+13.32, +23.85] | +18.85 [+12.76, +24.81] | +14.13 [+8.23, +19.82] | +10.57 [+4.58, +16.25] |
| `S0|14:05|tp0|st2|E2|F3` | SPY+QQQ S2; SPY+QQQ S2-orig; original diagnostic set | TRAIN | 490 (490) | +26.70 [+17.96, +35.60] | +26.35 [+17.54, +35.19] | +28.05 [+17.96, +38.15] | +21.62 [+12.35, +30.64] | +6.05 [-2.88, +14.86] |
| `S0|14:05|tp0|st0|E2|F0` | original diagnostic set | TRAIN | 530 (530) | +19.52 [+7.48, +30.08] | +19.21 [+7.21, +29.69] | +20.90 [+8.29, +32.51] | +14.76 [+2.61, +25.81] | -1.86 [-13.79, +8.79] |
| `S1|14:05|tp0|st0|E2|F0` | original diagnostic set | TRAIN | 529 (529) | +6.16 [-2.47, +13.13] | +6.14 [-2.46, +13.13] | +6.69 [-1.78, +13.75] | +3.57 [-4.72, +10.73] | +0.45 [-8.24, +7.83] |
| `S0|14:05|tp0|st1|E2|F3` | SPY S1; SPY S1-orig; SPY+QQQ S1; SPY+QQQ S1-orig; original diagnostic set | TEST | 407 (407) | +34.33 [+21.37, +47.10] | +32.29 [+19.17, +45.08] | +40.20 [+23.40, +58.45] | +23.03 [+8.73, +37.27] | +1.01 [-12.68, +14.66] |
| `S0|14:05|tp50|st2|E2|F3` | SPY S2 | TEST | 407 (407) | +32.09 [+19.87, +43.55] | +30.29 [+17.68, +41.86] | +35.23 [+19.39, +52.27] | +21.30 [+7.38, +34.99] | +1.58 [-12.61, +15.01] |
| `S0.5|14:05|tp0|st2|E2|F3` | SPY S2-orig; original diagnostic set | TEST | 407 (407) | +21.29 [+11.16, +31.04] | +19.24 [+9.18, +28.90] | +24.51 [+13.88, +34.84] | +11.29 [+0.21, +22.03] | +3.95 [-7.28, +14.78] |
| `S0|14:05|tp0|st2|E2|F3` | SPY+QQQ S2; SPY+QQQ S2-orig; original diagnostic set | TEST | 407 (407) | +38.49 [+25.26, +51.10] | +36.46 [+22.89, +49.18] | +44.65 [+27.70, +62.97] | +25.98 [+10.86, +40.53] | +1.57 [-13.11, +15.74] |
| `S0|14:05|tp0|st0|E2|F0` | original diagnostic set | TEST | 441 (441) | +36.85 [+23.61, +49.81] | +34.89 [+21.52, +47.87] | +43.23 [+25.83, +61.20] | +24.90 [+9.44, +39.65] | -1.46 [-16.52, +12.84] |
| `S1|14:05|tp0|st0|E2|F0` | original diagnostic set | TEST | 441 (441) | +20.47 [+13.27, +27.18] | +19.54 [+12.27, +26.17] | +19.89 [+10.90, +28.11] | +13.21 [+3.90, +21.79] | +7.85 [-1.61, +16.57] |

## 7. Tail stress

Historical entry-to-close moves (close of the 15:59 bar vs close of the bar before entry), 1-minute underlying series, all full sessions 2017-06-01 → 2026-10-09 (`results/stress_hist_summary.csv`, top 10 per side in `results/stress_hist_moves.csv`):

| ticker | entry | sessions | worst down % (date) | worst up % (date) | 2025-04-09 % |
|---|---|---|---|---|---|
| SPY | 10:00 | 2333 | -4.95 (2025-04-08) | +8.71 (2025-04-09) | +8.71 |
| SPY | 11:00 | 2333 | -6.20 (2020-03-20) | +10.17 (2025-04-09) | +10.17 |
| SPY | 13:00 | 2333 | -4.58 (2020-03-12) | +8.41 (2025-04-09) | +8.41 |
| SPY | 14:05 | 2333 | -3.63 (2020-03-20) | +5.09 (2020-03-13) | +1.39 |
| SPY | any minute 10:00–14:30 | 2333 | -6.90 (2020-03-12) | +10.17 (2025-04-09) | +10.17 |
| QQQ | 10:00 | 2333 | -5.52 (2025-04-08) | +10.41 (2025-04-09) | +10.41 |
| QQQ | 11:00 | 2333 | -6.52 (2020-03-20) | +11.85 (2025-04-09) | +11.85 |
| QQQ | 13:00 | 2333 | -5.61 (2020-03-16) | +9.89 (2025-04-09) | +9.89 |
| QQQ | 14:05 | 2333 | -4.37 (2020-03-16) | +5.46 (2020-03-13) | +1.84 |
| QQQ | any minute 10:00–14:30 | 2333 | -8.15 (2020-03-16) | +11.85 (2025-04-09) | +11.85 |
| IWM | 10:00 | 2333 | -5.51 (2025-04-08) | +8.29 (2025-04-09) | +8.29 |
| IWM | 11:00 | 2333 | -6.50 (2020-03-20) | +10.46 (2025-04-09) | +10.46 |
| IWM | 13:00 | 2333 | -4.75 (2024-12-18) | +9.18 (2025-04-09) | +9.18 |
| IWM | 14:05 | 2333 | -4.54 (2024-12-18) | +4.12 (2020-03-10) | -0.70 |
| IWM | any minute 10:00–14:30 | 2333 | -7.08 (2020-03-16) | +10.47 (2025-04-09) | +10.47 |

Settlement P&L per 1-lot if the underlying ends the day at entry spot × (1 + move), every leg expiring (unprotected: no stop fill assumed), over the selection's TEST trades (median trade / worst trade); capital per lot for an 8 % max-loss budget; margin estimates per lot (formula-based, not broker-verified).  `results/stress_selected.csv`.

| scope | sel | config | n | median credit $ | −5 % | +5 % | −8.42 % | +8.42 % | −10 % | +10 % | −15 % | +15 % | worst historical down (move) | worst historical up (move) | capital/lot, 8 % budget, ±15 % (median trade) | stop at trigger (optimistic) | Reg-T 20 % / 15 % | PM-style −8/+6 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 407 | 148 | -3181 / -3793 | -3182 / -3814 | -5470 / -6453 | -5477 / -6475 | -6518 / -7682 | -6533 / -7708 | -9878 / -11580 | -9877 / -11608 | -2268 / -2732 (SPY -3.63 % (2020-03-20)) | -3242 / -3883 (SPY +5.09 % (2020-03-13)) | 123,589 | -151 | 13,555 / 10,219 | 5,186 |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 407 | 148 | -3181 / -3793 | -3182 / -3814 | -5470 / -6453 | -5477 / -6475 | -6518 / -7682 | -6533 / -7708 | -9878 / -11580 | -9877 / -11608 | -2268 / -2732 (SPY -3.63 % (2020-03-20)) | -3242 / -3883 (SPY +5.09 % (2020-03-13)) | 123,589 | -299 | 13,555 / 10,219 | 5,186 |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 407 | 148 | -3181 / -3793 | -3182 / -3814 | -5470 / -6453 | -5477 / -6475 | -6518 / -7682 | -6533 / -7708 | -9878 / -11580 | -9877 / -11608 | -2268 / -2732 (SPY -3.63 % (2020-03-20)) | -3242 / -3883 (SPY +5.09 % (2020-03-13)) | 123,589 | -151 | 13,555 / 10,219 | 5,186 |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 407 | 61 | -3145 / -3759 | -3146 / -3776 | -5440 / -6416 | -5449 / -6444 | -6489 / -7649 | -6492 / -7677 | -9843 / -11550 | -9834 / -11578 | -2234 / -2697 (SPY -3.63 % (2020-03-20)) | -3204 / -3846 (SPY +5.09 % (2020-03-13)) | 123,283 | -125 | 13,358 / 10,015 | 5,158 |
| SPY | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 407 | 61 | -3145 / -3759 | -3146 / -3776 | -5440 / -6416 | -5449 / -6444 | -6489 / -7649 | -6492 / -7677 | -9843 / -11550 | -9834 / -11578 | -2234 / -2697 (SPY -3.63 % (2020-03-20)) | -3204 / -3846 (SPY +5.09 % (2020-03-13)) | 123,283 | -125 | 13,358 / 10,015 | 5,158 |
| SPY | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 407 | 61 | -3145 / -3759 | -3146 / -3776 | -5440 / -6416 | -5449 / -6444 | -6489 / -7649 | -6492 / -7677 | -9843 / -11550 | -9834 / -11578 | -2234 / -2697 (SPY -3.63 % (2020-03-20)) | -3204 / -3846 (SPY +5.09 % (2020-03-13)) | 123,283 | -125 | 13,358 / 10,015 | 5,158 |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 407 | 176 | -2811 / -3672 | -2808 / -3722 | -4872 / -6239 | -4866 / -6327 | -5819 / -7431 | -5826 / -7530 | -8838 / -11238 | -8834 / -11337 | -2432 / -3195 (QQQ -4.37 % (2020-03-16)) | -3090 / -4076 (QQQ +5.46 % (2020-03-13)) | 110,783 | -179 | 12,284 / 9,267 | 4,618 |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 407 | 176 | -2811 / -3672 | -2808 / -3722 | -4872 / -6239 | -4866 / -6327 | -5819 / -7431 | -5826 / -7530 | -8838 / -11238 | -8834 / -11337 | -2432 / -3195 (QQQ -4.37 % (2020-03-16)) | -3090 / -4076 (QQQ +5.46 % (2020-03-13)) | 110,783 | -179 | 12,284 / 9,267 | 4,618 |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 407 | 176 | -2811 / -3672 | -2808 / -3722 | -4872 / -6239 | -4866 / -6327 | -5819 / -7431 | -5826 / -7530 | -8838 / -11238 | -8834 / -11337 | -2432 / -3195 (QQQ -4.37 % (2020-03-16)) | -3090 / -4076 (QQQ +5.46 % (2020-03-13)) | 110,783 | -179 | 12,284 / 9,267 | 4,618 |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 407 | 176 | -2811 / -3672 | -2808 / -3722 | -4872 / -6239 | -4866 / -6327 | -5819 / -7431 | -5826 / -7530 | -8838 / -11238 | -8834 / -11337 | -2432 / -3195 (QQQ -4.37 % (2020-03-16)) | -3090 / -4076 (QQQ +5.46 % (2020-03-13)) | 110,783 | -355 | 12,284 / 9,267 | 4,618 |
| QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st1|E1|F3` | 407 | 77 | -2768 / -3623 | -2786 / -3630 | -4833 / -6228 | -4844 / -6227 | -5775 / -7431 | -5795 / -7430 | -8790 / -11238 | -8805 / -11237 | -2382 / -3140 (QQQ -4.37 % (2020-03-16)) | -3067 / -3982 (QQQ +5.46 % (2020-03-13)) | 110,186 | -80 | 12,012 / 9,002 | 4,580 |
| QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 407 | 77 | -2768 / -3623 | -2786 / -3630 | -4833 / -6228 | -4844 / -6227 | -5775 / -7431 | -5795 / -7430 | -8790 / -11238 | -8805 / -11237 | -2382 / -3140 (QQQ -4.37 % (2020-03-16)) | -3067 / -3982 (QQQ +5.46 % (2020-03-13)) | 110,186 | -157 | 12,012 / 9,002 | 4,580 |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 407 | 77 | -1139 / -1484 | -1146 / -1499 | -1984 / -2518 | -1990 / -2540 | -2374 / -2995 | -2383 / -3021 | -3602 / -4507 | -3612 / -4543 | -1025 / -1344 (IWM -4.54 % (2024-12-18)) | -932 / -1232 (IWM +4.12 % (2020-03-10)) | 45,440 | -80 | 5,012 / 3,782 | 1,876 |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 407 | 77 | -1139 / -1484 | -1146 / -1499 | -1984 / -2518 | -1990 / -2540 | -2374 / -2995 | -2383 / -3021 | -3602 / -4507 | -3612 / -4543 | -1025 / -1344 (IWM -4.54 % (2024-12-18)) | -932 / -1232 (IWM +4.12 % (2020-03-10)) | 45,440 | -157 | 5,012 / 3,782 | 1,876 |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 407 | 77 | -1139 / -1484 | -1146 / -1499 | -1984 / -2518 | -1990 / -2540 | -2374 / -2995 | -2383 / -3021 | -3602 / -4507 | -3612 / -4543 | -1025 / -1344 (IWM -4.54 % (2024-12-18)) | -932 / -1232 (IWM +4.12 % (2020-03-10)) | 45,440 | -80 | 5,012 / 3,782 | 1,876 |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 407 | 77 | -1139 / -1484 | -1146 / -1499 | -1984 / -2518 | -1990 / -2540 | -2374 / -2995 | -2383 / -3021 | -3602 / -4507 | -3612 / -4543 | -1025 / -1344 (IWM -4.54 % (2024-12-18)) | -932 / -1232 (IWM +4.12 % (2020-03-10)) | 45,440 | -157 | 5,012 / 3,782 | 1,876 |
| IWM | PH-S1-E1 | `S0.5|11:00|tp0|st0|E1|F1` | 427 | 48 | -1054 / -1409 | -1057 / -1434 | -1892 / -2448 | -1897 / -2476 | -2283 / -2928 | -2283 / -2956 | -3517 / -4447 | -3510 / -4479 | -1424 / -1865 (IWM -6.50 % (2020-03-20)) | -2394 / -3096 (IWM +10.46 % (2025-04-09)) | 44,101 | n/a | 4,872 / 3,651 | 1,792 |
| IWM | PH-S2-E1 | `S0.5|11:00|tp0|st0|E1|F1` | 427 | 48 | -1054 / -1409 | -1057 / -1434 | -1892 / -2448 | -1897 / -2476 | -2283 / -2928 | -2283 / -2956 | -3517 / -4447 | -3510 / -4479 | -1424 / -1865 (IWM -6.50 % (2020-03-20)) | -2394 / -3096 (IWM +10.46 % (2025-04-09)) | 44,101 | n/a | 4,872 / 3,651 | 1,792 |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 814 | 162 | -2998 / -3793 | -3005 / -3814 | -5148 / -6453 | -5159 / -6475 | -6139 / -7682 | -6147 / -7708 | -9273 / -11580 | -9284 / -11608 | -2344 / -3195 (QQQ -4.37 % (2020-03-16); SPY -3.63 % (2020-03-20)) | -3177 / -4076 (QQQ +5.46 % (2020-03-13); SPY +5.09 % (2020-03-13)) | 116,438 | -165 | 12,655 / 9,529 | 4,885 |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 814 | 162 | -2998 / -3793 | -3005 / -3814 | -5148 / -6453 | -5159 / -6475 | -6139 / -7682 | -6147 / -7708 | -9273 / -11580 | -9284 / -11608 | -2344 / -3195 (QQQ -4.37 % (2020-03-16); SPY -3.63 % (2020-03-20)) | -3177 / -4076 (QQQ +5.46 % (2020-03-13); SPY +5.09 % (2020-03-13)) | 116,438 | -327 | 12,655 / 9,529 | 4,885 |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 814 | 162 | -2998 / -3793 | -3005 / -3814 | -5148 / -6453 | -5159 / -6475 | -6139 / -7682 | -6147 / -7708 | -9273 / -11580 | -9284 / -11608 | -2344 / -3195 (QQQ -4.37 % (2020-03-16); SPY -3.63 % (2020-03-20)) | -3177 / -4076 (QQQ +5.46 % (2020-03-13); SPY +5.09 % (2020-03-13)) | 116,438 | -165 | 12,655 / 9,529 | 4,885 |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 814 | 162 | -2998 / -3793 | -3005 / -3814 | -5148 / -6453 | -5159 / -6475 | -6139 / -7682 | -6147 / -7708 | -9273 / -11580 | -9284 / -11608 | -2344 / -3195 (QQQ -4.37 % (2020-03-16); SPY -3.63 % (2020-03-20)) | -3177 / -4076 (QQQ +5.46 % (2020-03-13); SPY +5.09 % (2020-03-13)) | 116,438 | -327 | 12,655 / 9,529 | 4,885 |
| SPY+QQQ | PH-S1-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 814 | 68 | -2964 / -3759 | -2963 / -3776 | -5123 / -6416 | -5116 / -6444 | -6109 / -7649 | -6107 / -7677 | -9246 / -11550 | -9233 / -11578 | -2307 / -3140 (QQQ -4.37 % (2020-03-16); SPY -3.63 % (2020-03-20)) | -3130 / -3982 (QQQ +5.46 % (2020-03-13); SPY +5.09 % (2020-03-13)) | 115,924 | -138 | 12,498 / 9,367 | 4,859 |
| SPY+QQQ | PH-S2-E1 | `S0.5|14:05|tp0|st2|E1|F3` | 814 | 68 | -2964 / -3759 | -2963 / -3776 | -5123 / -6416 | -5116 / -6444 | -6109 / -7649 | -6107 / -7677 | -9246 / -11550 | -9233 / -11578 | -2307 / -3140 (QQQ -4.37 % (2020-03-16); SPY -3.63 % (2020-03-20)) | -3130 / -3982 (QQQ +5.46 % (2020-03-13); SPY +5.09 % (2020-03-13)) | 115,924 | -138 | 12,498 / 9,367 | 4,859 |

Realized P&L of the pre-registered selections on the largest-move TEST days (now priced; `results/stress_extreme_days.csv`):

| scope | sel | config | date | move entry→close % | traded | P&L $ | exit |
|---|---|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | SPY -1.44 | 1 | -287.80 | STOP |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-28 | SPY +1.66 | 0 | n/a |  |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | SPY -0.76 | 1 | -108.40 | EXPIRE |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | SPY -1.77 | 1 | -447.40 | EXPIRE |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | SPY -0.72 | 1 | +476.60 | EXPIRE |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | SPY -1.82 | 1 | -800.80 | STOP |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | SPY +1.39 | 1 | +260.60 | EXPIRE |
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | SPY -0.45 | 1 | +628.60 | EXPIRE |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-02-27 | SPY -1.44 | 1 | -415.80 | STOP |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-02-28 | SPY +1.66 | 0 | n/a |  |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-04-03 | SPY -0.76 | 1 | -108.40 | EXPIRE |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-04-04 | SPY -1.77 | 1 | -447.40 | EXPIRE |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-04-07 | SPY -0.72 | 1 | +476.60 | EXPIRE |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-04-08 | SPY -1.82 | 1 | -312.40 | EXPIRE |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-04-09 | SPY +1.39 | 1 | +260.60 | EXPIRE |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | 2025-04-10 | SPY -0.45 | 1 | +458.20 | TP |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | SPY -1.44 | 1 | -287.80 | STOP |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-02-28 | SPY +1.66 | 0 | n/a |  |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | SPY -0.76 | 1 | -108.40 | EXPIRE |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | SPY -1.77 | 1 | -447.40 | EXPIRE |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | SPY -0.72 | 1 | +476.60 | EXPIRE |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | SPY -1.82 | 1 | -800.80 | STOP |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | SPY +1.39 | 1 | +260.60 | EXPIRE |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | SPY -0.45 | 1 | +628.60 | EXPIRE |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-02-27 | SPY -1.44 | 1 | -201.80 | STOP |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-02-28 | SPY +1.66 | 0 | n/a |  |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-04-03 | SPY -0.76 | 1 | -68.40 | EXPIRE |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-04-04 | SPY -1.77 | 1 | -382.40 | EXPIRE |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-04-07 | SPY -0.72 | 1 | +457.60 | EXPIRE |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-04-08 | SPY -1.82 | 1 | -719.80 | STOP |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-04-09 | SPY +1.39 | 1 | +319.60 | EXPIRE |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | 2025-04-10 | SPY -0.45 | 1 | +454.60 | EXPIRE |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | QQQ -2.07 | 1 | -342.80 | STOP |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-28 | QQQ +1.75 | 0 | n/a |  |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | QQQ -0.68 | 1 | -18.40 | EXPIRE |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | QQQ -1.93 | 1 | -416.28 | EXPIRE |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | QQQ -1.02 | 1 | +337.60 | EXPIRE |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | QQQ -2.24 | 1 | -651.80 | STOP |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | QQQ +1.84 | 1 | +84.60 | EXPIRE |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | QQQ -0.49 | 1 | +577.60 | EXPIRE |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | QQQ -2.07 | 1 | -342.80 | STOP |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-28 | QQQ +1.75 | 0 | n/a |  |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | QQQ -0.68 | 1 | -18.40 | EXPIRE |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | QQQ -1.93 | 1 | -416.28 | EXPIRE |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | QQQ -1.02 | 1 | +337.60 | EXPIRE |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | QQQ -2.24 | 1 | -651.80 | STOP |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | QQQ +1.84 | 1 | +84.60 | EXPIRE |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | QQQ -0.49 | 1 | +577.60 | EXPIRE |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | QQQ -2.07 | 1 | -342.80 | STOP |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-02-28 | QQQ +1.75 | 0 | n/a |  |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | QQQ -0.68 | 1 | -18.40 | EXPIRE |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | QQQ -1.93 | 1 | -416.28 | EXPIRE |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | QQQ -1.02 | 1 | +337.60 | EXPIRE |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | QQQ -2.24 | 1 | -651.80 | STOP |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | QQQ +1.84 | 1 | +84.60 | EXPIRE |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | QQQ -0.49 | 1 | +577.60 | EXPIRE |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-02-27 | QQQ -2.07 | 1 | -525.80 | STOP |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-02-28 | QQQ +1.75 | 0 | n/a |  |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-03 | QQQ -0.68 | 1 | -18.40 | EXPIRE |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-04 | QQQ -1.93 | 1 | -416.28 | EXPIRE |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-07 | QQQ -1.02 | 1 | +337.60 | EXPIRE |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-08 | QQQ -2.24 | 1 | -775.80 | STOP |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-09 | QQQ +1.84 | 1 | +84.60 | EXPIRE |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-10 | QQQ -0.49 | 1 | +577.60 | EXPIRE |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-03-03 | IWM -1.50 | 1 | -145.80 | STOP |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | IWM -0.69 | 1 | +13.60 | EXPIRE |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | IWM -0.52 | 1 | +137.60 | EXPIRE |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | IWM -0.98 | 1 | +162.60 | EXPIRE |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | IWM -1.64 | 1 | -303.80 | STOP |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | IWM -0.70 | 1 | +228.60 | EXPIRE |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | IWM -0.66 | 1 | +192.60 | EXPIRE |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-09-17 | IWM -1.93 | 0 | n/a |  |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2026-02-03 | IWM +1.50 | 1 | -147.80 | STOP |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | 2026-03-09 | IWM +2.20 | 1 | -244.80 | STOP |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-03-03 | IWM -1.50 | 1 | -200.80 | STOP |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-03 | IWM -0.69 | 1 | +13.60 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-04 | IWM -0.52 | 1 | +137.60 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-07 | IWM -0.98 | 1 | +162.60 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-08 | IWM -1.64 | 1 | -92.40 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-09 | IWM -0.70 | 1 | +228.60 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-10 | IWM -0.66 | 1 | +192.60 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-09-17 | IWM -1.93 | 0 | n/a |  |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2026-02-03 | IWM +1.50 | 1 | -259.40 | EXPIRE |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | 2026-03-09 | IWM +2.20 | 1 | -297.80 | STOP |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-03-03 | IWM -1.50 | 1 | -145.80 | STOP |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | IWM -0.69 | 1 | +13.60 | EXPIRE |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | IWM -0.52 | 1 | +137.60 | EXPIRE |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | IWM -0.98 | 1 | +162.60 | EXPIRE |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | IWM -1.64 | 1 | -303.80 | STOP |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | IWM -0.70 | 1 | +228.60 | EXPIRE |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | IWM -0.66 | 1 | +192.60 | EXPIRE |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-09-17 | IWM -1.93 | 0 | n/a |  |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2026-02-03 | IWM +1.50 | 1 | -147.80 | STOP |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2026-03-09 | IWM +2.20 | 1 | -244.80 | STOP |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-03-03 | IWM -1.50 | 1 | -200.80 | STOP |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-03 | IWM -0.69 | 1 | +13.60 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-04 | IWM -0.52 | 1 | +137.60 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-07 | IWM -0.98 | 1 | +162.60 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-08 | IWM -1.64 | 1 | -92.40 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-09 | IWM -0.70 | 1 | +228.60 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-10 | IWM -0.66 | 1 | +192.60 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-09-17 | IWM -1.93 | 0 | n/a |  |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2026-02-03 | IWM +1.50 | 1 | -259.40 | EXPIRE |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2026-03-09 | IWM +2.20 | 1 | -297.80 | STOP |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | SPY -1.44; QQQ -2.07 | 2 | -630.60 | STOP;STOP |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | SPY -0.76; QQQ -0.68 | 2 | -126.80 | EXPIRE;EXPIRE |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | SPY -1.77; QQQ -1.93 | 2 | -863.68 | EXPIRE;EXPIRE |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | SPY -0.72; QQQ -1.02 | 2 | +814.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | SPY -1.82; QQQ -2.24 | 2 | -1452.60 | STOP;STOP |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | SPY +1.39; QQQ +1.84 | 2 | +345.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | SPY -0.45; QQQ -0.49 | 2 | +1206.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-02-27 | SPY -1.44; QQQ -2.07 | 2 | -941.60 | STOP;STOP |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-03 | SPY -0.76; QQQ -0.68 | 2 | -126.80 | EXPIRE;EXPIRE |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-04 | SPY -1.77; QQQ -1.93 | 2 | -863.68 | EXPIRE;EXPIRE |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-07 | SPY -0.72; QQQ -1.02 | 2 | +814.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-08 | SPY -1.82; QQQ -2.24 | 2 | -1088.20 | STOP;EXPIRE |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-09 | SPY +1.39; QQQ +1.84 | 2 | +345.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | 2025-04-10 | SPY -0.45; QQQ -0.49 | 2 | +1206.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-02-27 | SPY -1.44; QQQ -2.07 | 2 | -630.60 | STOP;STOP |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-03 | SPY -0.76; QQQ -0.68 | 2 | -126.80 | EXPIRE;EXPIRE |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-04 | SPY -1.77; QQQ -1.93 | 2 | -863.68 | EXPIRE;EXPIRE |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-07 | SPY -0.72; QQQ -1.02 | 2 | +814.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-08 | SPY -1.82; QQQ -2.24 | 2 | -1452.60 | STOP;STOP |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-09 | SPY +1.39; QQQ +1.84 | 2 | +345.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | 2025-04-10 | SPY -0.45; QQQ -0.49 | 2 | +1206.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-02-27 | SPY -1.44; QQQ -2.07 | 2 | -941.60 | STOP;STOP |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-03 | SPY -0.76; QQQ -0.68 | 2 | -126.80 | EXPIRE;EXPIRE |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-04 | SPY -1.77; QQQ -1.93 | 2 | -863.68 | EXPIRE;EXPIRE |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-07 | SPY -0.72; QQQ -1.02 | 2 | +814.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-08 | SPY -1.82; QQQ -2.24 | 2 | -1088.20 | STOP;EXPIRE |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-09 | SPY +1.39; QQQ +1.84 | 2 | +345.20 | EXPIRE;EXPIRE |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | 2025-04-10 | SPY -0.45; QQQ -0.49 | 2 | +1206.20 | EXPIRE;EXPIRE |

## 8. COMPASS §10 gate verdicts

Carry lane = data integrity, execution realism, statistical validity (complete data, out of sample, Bonferroni over the 8 pre-registered selections), tail survival, forward validation, classification.  Signal lane = the same plus beating random entry on the same days by more than one round trip.  `results/gates.csv` has the detail text.

| scope | sel | config | data integrity | execution realism | statistical validity | tail survival | forward validation | classification | beats random by > cost (matched, point) | paired CI excludes 0 | carry verdict | signal verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✓ | ✗ | **FAIL** | **FAIL** |
| SPY | S2 | `S0|14:05|tp50|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✓ | ✗ | **FAIL** | **FAIL** |
| SPY | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✓ | ✗ | **FAIL** | **FAIL** |
| SPY | S2-orig | `S0.5|14:05|tp0|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY | PH-S1-E1 (post-hoc) | `S0.5|14:05|tp0|st2|E1|F3` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY | PH-S2-E1 (post-hoc) | `S0.5|14:05|tp0|st2|E1|F3` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| QQQ | S2 | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| QQQ | PH-S1-E1 (post-hoc) | `S0.5|14:05|tp0|st1|E1|F3` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| QQQ | PH-S2-E1 (post-hoc) | `S0.5|14:05|tp0|st2|E1|F3` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| IWM | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| IWM | S2 | `S0|14:05|tp0|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| IWM | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| IWM | S2-orig | `S0|14:05|tp0|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| IWM | PH-S1-E1 (post-hoc) | `S0.5|11:00|tp0|st0|E1|F1` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| IWM | PH-S2-E1 (post-hoc) | `S0.5|11:00|tp0|st0|E1|F1` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY+QQQ | S1 | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY+QQQ | S2 | `S0|14:05|tp0|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY+QQQ | S1-orig | `S0|14:05|tp0|st1|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY+QQQ | S2-orig | `S0|14:05|tp0|st2|E2|F3` | ✓ | ✗ | ✓ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY+QQQ | PH-S1-E1 (post-hoc) | `S0.5|14:05|tp0|st2|E1|F3` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |
| SPY+QQQ | PH-S2-E1 (post-hoc) | `S0.5|14:05|tp0|st2|E1|F3` | ✓ | ✓ | ✗ | ✗ | ✗ | carry | ✗ | ✗ | **FAIL** | **FAIL** |

Item detail for the full-chain TRAIN selections:

- **SPY S1 `S0|14:05|tp0|st1|E2|F3`** — data: 407 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); SPY pessimistic after-hours re-valuation +1.01 [-12.68, +14.66] (n = 407). Statistics: TEST n = 407, mean +34.33 [+21.02, +47.24]; Bonferroni-8 lower bound +15.41; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -9878, +15 % -9877, -8.42 % -5470, +8.42 % -5477; worst trade at the worst historical move -3883; capital per lot for an 8 % budget at +-15 %: 123589 (median trade); margin estimates (formula, not broker-verified): Reg-T 13555 (20 %) / 10219 (15 %), PM-style -8/+6 % 5186; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +34.33 vs random +26.10, paired diff +8.23 [-6.65, +23.97] vs round trip 3.28 (CI includes zero); pre-registered unpaired diff +8.23; baseline trades on days without a lane trade: 0.
- **SPY S2 `S0|14:05|tp50|st2|E2|F3`** — data: 407 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); SPY pessimistic after-hours re-valuation +1.58 [-12.61, +15.01] (n = 407). Statistics: TEST n = 407, mean +32.09 [+19.93, +43.76]; Bonferroni-8 lower bound +15.35; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -9878, +15 % -9877, -8.42 % -5470, +8.42 % -5477; worst trade at the worst historical move -3883; capital per lot for an 8 % budget at +-15 %: 123589 (median trade); margin estimates (formula, not broker-verified): Reg-T 13555 (20 %) / 10219 (15 %), PM-style -8/+6 % 5186; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +32.09 vs random +20.94, paired diff +11.15 [-3.31, +27.48] vs round trip 3.49 (CI includes zero); pre-registered unpaired diff +11.15; baseline trades on days without a lane trade: 0.
- **QQQ S1 `S0|14:05|tp0|st1|E2|F3`** — data: 407 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); no after-hours data for this ticker. Statistics: TEST n = 407, mean +28.10 [+14.03, +41.97]; Bonferroni-8 lower bound +9.33; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -8838, +15 % -8834, -8.42 % -4872, +8.42 % -4866; worst trade at the worst historical move -4076; capital per lot for an 8 % budget at +-15 %: 110783 (median trade); margin estimates (formula, not broker-verified): Reg-T 12284 (20 %) / 9267 (15 %), PM-style -8/+6 % 4618; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +28.10 vs random +29.37, paired diff -1.27 [-16.77, +15.76] vs round trip 4.26 (CI includes zero); pre-registered unpaired diff -1.84; baseline trades on days without a lane trade: 0.
- **QQQ S2 `S0|14:05|tp0|st1|E2|F3`** — data: 407 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); no after-hours data for this ticker. Statistics: TEST n = 407, mean +28.10 [+14.03, +41.97]; Bonferroni-8 lower bound +9.33; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -8838, +15 % -8834, -8.42 % -4872, +8.42 % -4866; worst trade at the worst historical move -4076; capital per lot for an 8 % budget at +-15 %: 110783 (median trade); margin estimates (formula, not broker-verified): Reg-T 12284 (20 %) / 9267 (15 %), PM-style -8/+6 % 4618; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +28.10 vs random +29.37, paired diff -1.27 [-16.77, +15.76] vs round trip 4.26 (CI includes zero); pre-registered unpaired diff -1.84; baseline trades on days without a lane trade: 0.
- **IWM S1 `S0|14:05|tp0|st1|E2|F3`** — data: 407 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); no after-hours data for this ticker. Statistics: TEST n = 407, mean +8.78 [+2.52, +14.95]; Bonferroni-8 lower bound -0.66; Romano-Wolf rejected in the TEST grid: no. Tail: unprotected settlement P&L per lot, median trade: -15 % -3602, +15 % -3612, -8.42 % -1984, +8.42 % -1990; worst trade at the worst historical move -1344; capital per lot for an 8 % budget at +-15 %: 45440 (median trade); margin estimates (formula, not broker-verified): Reg-T 5012 (20 %) / 3782 (15 %), PM-style -8/+6 % 1876; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +8.78 vs random +7.36, paired diff +1.42 [-4.89, +8.06] vs round trip 4.09 (CI includes zero); pre-registered unpaired diff +1.42; baseline trades on days without a lane trade: 0.
- **IWM S2 `S0|14:05|tp0|st2|E2|F3`** — data: 407 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); no after-hours data for this ticker. Statistics: TEST n = 407, mean +12.40 [+6.36, +18.35]; Bonferroni-8 lower bound +3.38; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -3602, +15 % -3612, -8.42 % -1984, +8.42 % -1990; worst trade at the worst historical move -1344; capital per lot for an 8 % budget at +-15 %: 45440 (median trade); margin estimates (formula, not broker-verified): Reg-T 5012 (20 %) / 3782 (15 %), PM-style -8/+6 % 1876; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +12.40 vs random +10.51, paired diff +1.89 [-4.76, +8.90] vs round trip 3.27 (CI includes zero); pre-registered unpaired diff +1.89; baseline trades on days without a lane trade: 0.
- **SPY+QQQ S1 `S0|14:05|tp0|st1|E2|F3`** — data: 814 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); SPY pessimistic after-hours re-valuation +1.01 [-12.68, +14.66] (n = 407). Statistics: TEST n = 814, mean +31.22 [+18.07, +44.25]; Bonferroni-8 lower bound +13.25; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -9273, +15 % -9284, -8.42 % -5148, +8.42 % -5159; worst trade at the worst historical move -4076; capital per lot for an 8 % budget at +-15 %: 116438 (median trade); margin estimates (formula, not broker-verified): Reg-T 12655 (20 %) / 9529 (15 %), PM-style -8/+6 % 4885; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +31.22 vs random +27.74, paired diff +3.48 [-10.65, +18.83] vs round trip 3.77 (CI includes zero); pre-registered unpaired diff +3.20; baseline trades on days without a lane trade: 0.
- **SPY+QQQ S2 `S0|14:05|tp0|st2|E2|F3`** — data: 814 TEST entry slots, 0 with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv). Execution: E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); SPY pessimistic after-hours re-valuation +1.57 [-13.11, +15.74] (n = 407). Statistics: TEST n = 814, mean +35.75 [+22.31, +49.03]; Bonferroni-8 lower bound +17.19; Romano-Wolf rejected in the TEST grid: yes. Tail: unprotected settlement P&L per lot, median trade: -15 % -9273, +15 % -9284, -8.42 % -5148, +8.42 % -5159; worst trade at the worst historical move -4076; capital per lot for an 8 % budget at +-15 %: 116438 (median trade); margin estimates (formula, not broker-verified): Reg-T 12655 (20 %) / 9529 (15 %), PM-style -8/+6 % 4885; loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed. Forward: 0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months). Random entry: matched days: lane +35.75 vs random +34.57, paired diff +1.19 [-13.43, +17.67] vs round trip 3.10 (CI includes zero); pre-registered unpaired diff +0.79; baseline trades on days without a lane trade: 0.
