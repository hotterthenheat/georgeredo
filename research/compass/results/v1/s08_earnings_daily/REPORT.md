# s08_earnings_daily: earnings reports, direction = surprise sign (or the event-day move), entry at the event open (gap) or the next open (drift), 2024 → 2026

Signed return in bp from the next session's open to the close h sessions after the signal; adjusted = minus the same-date eligible-universe mean in the trigger's direction; CIs clustered by event date (1,000 draws).

| trigger | filters | n | days | symbols | calls | signal-day move | overnight gap at entry | +1d abs | +5d abs [CI] | +10d abs [CI] | +21d abs [CI] | +5d adj [CI] | +10d adj [CI] | +21d adj [CI] | hit 10d | promoted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| surprise_sign@gap | all | 9957 | 590 | 1185 | 77 % | +131 | +132 | -1 | +18 [-3, +40] | +30 [+8, +54] | +68 [+35, +99] | **-8** [-25, +11] | **-17** [-35, +3] | **-31** [-59, -2] | 51 % | abs only |
| surprise_sign@gap | top_tercile_beats | 3482 | 480 | 954 | 100 % | +209 | +206 | +3 | +46 [+2, +90] | +79 [+26, +131] | +132 [+66, +196] | **+0** [-36, +34] | **-12** [-51, +29] | **-49** [-103, +1] | 53 % | abs only |
| surprise_sign@gap | bottom_tercile_misses | 2996 | 461 | 970 | 23 % | +180 | +164 | +15 | -5 [-42, +29] | -26 [-73, +18] | -39 [-97, +21] | **+15** [-18, +48] | **+20** [-22, +59] | **+56** [+3, +108] | 49 % | adj only |
| surprise_sign@gap | premarket | 5491 | 534 | 858 | 78 % | +142 | +131 | +11 | +31 [+9, +54] | +47 [+19, +73] | +78 [+42, +116] | **+4** [-16, +24] | **-2** [-24, +22] | **-27** [-57, +3] | 52 % | abs only |
| surprise_sign@gap | postmarket | 4466 | 442 | 666 | 76 % | +118 | +133 | -16 | +1 [-26, +26] | +10 [-24, +43] | +57 [+10, +104] | **-24** [-47, +2] | **-36** [-64, -9] | **-36** [-79, +7] | 51 % | no |
| surprise_sign@drift | all | 9957 | 590 | 1185 | 77 % | +131 | +132 | -7 | +9 [-8, +27] | +23 [+1, +44] | +55 [+23, +85] | **-17** [-28, -6] | **-25** [-39, -9] | **-44** [-70, -17] | 52 % | no |
| surprise_sign@drift | top_tercile_beats | 3482 | 480 | 954 | 100 % | +209 | +206 | -14 | +27 [-12, +64] | +63 [+6, +115] | +96 [+26, +156] | **-19** [-41, +2] | **-28** [-60, +3] | **-86** [-136, -39] | 54 % | no |
| surprise_sign@drift | bottom_tercile_misses | 2996 | 461 | 970 | 23 % | +180 | +164 | +5 | -24 [-54, +4] | -44 [-84, -4] | -52 [-108, +8] | **-4** [-28, +19] | **+2** [-31, +33] | **+43** [-5, +90] | 48 % | no |
| surprise_sign@drift | premarket | 5491 | 534 | 858 | 78 % | +142 | +131 | -11 | +7 [-11, +27] | +22 [-5, +46] | +50 [+13, +85] | **-20** [-35, -6] | **-27** [-45, -8] | **-55** [-88, -25] | 52 % | no |
| surprise_sign@drift | postmarket | 4466 | 442 | 666 | 76 % | +118 | +133 | -1 | +11 [-12, +34] | +24 [-9, +54] | +63 [+18, +103] | **-13** [-32, +5] | **-22** [-48, +0] | **-31** [-68, +6] | 52 % | no |
| event_day_move@drift | all | 10426 | 593 | 1186 | 50 % | +583 | +399 | +2 | -1 [-16, +13] | -8 [-29, +11] | -10 [-33, +12] | **+0** [-13, +12] | **-5** [-23, +13] | **-12** [-35, +8] | 50 % | no |
| event_day_move@drift | big_move_2sigma | 5150 | 530 | 1110 | 51 % | +950 | +670 | +3 | -6 [-24, +12] | -14 [-37, +8] | -12 [-44, +19] | **-4** [-20, +12] | **-8** [-28, +12] | **-14** [-46, +16] | 49 % | no |
| event_day_move@drift | agrees_with_surprise | 5628 | 540 | 1160 | 74 % | +634 | +472 | -4 | +7 [-12, +28] | +13 [-16, +39] | +43 [+8, +80] | **-15** [-32, +1] | **-26** [-48, -6] | **-48** [-78, -17] | 51 % | no |
| event_day_move@drift | against_surprise | 4318 | 507 | 1134 | 19 % | +524 | +311 | +10 | -11 [-35, +13] | -36 [-71, +1] | -72 [-115, -32] | **+19** [+2, +36] | **+21** [-6, +49] | **+39** [-1, +73] | 47 % | adj only |

Promotion rule (A2): absolute lower bound ≥ +30 bp at 5, 10 or 21 sessions AND adjusted lower bound > 0. Promoted: none.

## Adjusted 10-session return by year and by side

| trigger | filters | 2024 | 2025 | 2026 | calls | puts |
|---|---|---|---|---|---|---|
| surprise_sign@gap | all | -29.2 | -15.5 | -7.4 | -33.7 | +37.7 |
| surprise_sign@gap | top_tercile_beats | -34.0 | -36.2 | +36.4 | -11.9 |  |
| surprise_sign@gap | bottom_tercile_misses | +32.5 | +7.6 | +22.0 | -37.9 | +37.7 |
| surprise_sign@gap | premarket | -29.9 | +12.3 | +9.7 | -23.2 | +73.8 |
| surprise_sign@gap | postmarket | -28.4 | -50.4 | -29.1 | -46.9 | -3.0 |
| surprise_sign@drift | all | -11.2 | -27.4 | -35.0 | -34.7 | +8.6 |
| surprise_sign@drift | top_tercile_beats | -11.5 | -58.8 | -12.2 | -28.4 |  |
| surprise_sign@drift | bottom_tercile_misses | +22.2 | -4.5 | -11.1 | -20.9 | +8.6 |
| surprise_sign@drift | premarket | -21.8 | -15.9 | -43.6 | -42.9 | +29.2 |
| surprise_sign@drift | postmarket | +1.1 | -41.8 | -24.2 | -24.3 | -14.7 |
| event_day_move@drift | all | +25.2 | +16.0 | -56.8 | -33.1 | +23.8 |
| event_day_move@drift | big_move_2sigma | +34.2 | +10.5 | -82.7 | -32.5 | +17.3 |
| event_day_move@drift | agrees_with_surprise | +11.2 | -12.7 | -81.0 | -40.7 | +14.6 |
| event_day_move@drift | against_surprise | +42.4 | +44.9 | -22.2 | +1.2 | +26.4 |
