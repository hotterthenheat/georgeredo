# Compass direction: post-earnings drift in 31–60 DTE options, run as pre-registered

**Pre-registration: `PREREG_DIRECTION.md`, commit `38b11bf`, sha256 `233e17b49f12c0fb9e4c58eec87b8b0030cc13a39f9b30d47ec192da9f976053`** (committed alone and pushed before anything was computed). Code in this folder: `ledger.py` (the draw), `dcommon.py`, `fetch_direction.py`, `build_direction.py`, `verify_direction.py`, `write_report.py`. Outputs: `out/`.

## Summary

- **Exploration screen: Δ -0.90 pp [-3.53, +1.71]** (picked side minus both sides, mean return per trade after costs, % of the debit) on 3,129 events, 12,114 / 24,316 trades, 1,849 sessions (893 with a trade); effective N 1,928 (block) / 974 (acf). → **FAIL — the holdout is not fetched and not read**.
- Absolute means per trade: the picked side -24.29 %, the other side -22.50 %, both -23.39 %; 5.3 % of the trades exit at a $0 bid.
- **Holdout: not read** (the screen did not pass). The 1,600 holdout names stay unopened for 2019-01 → 2022-12.
- Verifier: 40 exploration trades re-derived from the raw files by a plain loop, 0 differences.
- H1 (overnight reversal): no such study exists in either repository; the only overnight study (S16a) promoted nothing. **H2 not added.**
- Power, as pre-registered (§8): the test finds the effect only if it is about as large as the 1970s–80s extreme-decile drift on every report; at the size recent work suggests its power is about 0.1. A FAIL is not evidence that no small drift exists.

## 1. The ledger and the sets

- Opened names (before 2023): 134; every optionable name is opened from 2023. Optionable names with a timed report in 2019-04 → 2022-12: 3,280; not opened: 3,201; holdout H 1,600 names (22,598 timed reports), exploration X 1,601 names (46,344 timed reports 2019-04 → 2026-09) plus the on-disk names (507 reports listed).
- Event-list hashes reproduced by `ledger.py`: holdout `7d87d8c44d66c1c4…`, exploration `ba8b9dcacec164a6…` (equal to the prereg's).

## 2. The fetch

- expl: 12,367 events walked in the seeded order; stopped: fetch time 3.00 h reached the 3.0 h cut; 12,114 requests this set, fetch time 3.00 h, 68.6 MB stored.
  - stages: under the $50 M floor 8,578; fetched 3,005; no bar for P or R 541; under 50 of 60 days of bars 134; no listed 31-60 expiry 75; entry chain empty 18; entry session is a half day 15; entry chain failed 1
- hold: not fetched.

## 3. Events and trades: what was formed and why not

- exploration, fetched events built: 3,005; trade: no standing quote in the bucket 6,940; events with trades 2,935; trade: no EOD row at the exit 38; no standing ATM pair 30; expiry on a half day 15; bars and options disagree (parity > 5 %) 11; events with no trade 6; g = 0: undefined 4; a split-sized close-to-close move in P..X 4
- exploration, on-disk events listed: 507; outside the stored option EOD span 285; events with trades 194; trade: no standing quote in the bucket 56; no bar for P or R 21; entry session is a half day 3; under 50 of 60 days of bars 2; no listed 31-60 expiry 1; a split-sized close-to-close move in P..X 1

## 4. The exploration screen

| cut | events | trades with / without | sessions traded | mean with % | mean without % | Δ (pp) [95 % block-20] |
|---|---|---|---|---|---|---|
| **all (the screen)** | 3,129 | 12,114 / 24,316 | 893 | -24.29 | -23.39 | **-0.90** [-3.53, +1.71] |
| X before 2023 (unopened cells) | 1,220 | 4,768 / 9,579 | 410 | -20.35 | -19.59 | **-0.76** [-5.74, +3.77] |
| X from 2023 (opened cells) | 1,715 | 6,404 / 12,853 | 461 | -28.81 | -28.68 | **-0.13** [-2.93, +2.82] |
| on-disk names (opened) | 194 | 942 / 1,884 | 146 | -13.54 | -6.63 | **-6.91** [-19.09, +5.78] |
| pick=C | 1,586 | 6,155 / 12,405 | 657 | -17.62 | -24.03 | **+6.41** [-0.48, +13.62] |
| pick=P | 1,543 | 5,959 / 11,911 | 651 | -31.19 | -22.73 | **-8.46** [-16.09, -1.01] |
| report_time=postmarket | 1,555 | 6,127 / 12,278 | 581 | -22.69 | -21.49 | **-1.20** [-5.12, +2.97] |
| report_time=premarket | 1,574 | 5,987 / 12,038 | 690 | -25.93 | -25.33 | **-0.60** [-4.05, +2.77] |
| sb=ATM | 2,192 | 2,190 / 4,373 | 791 | -18.41 | -17.16 | **-1.25** [-3.68, +1.29] |
| sb=ITM | 2,717 | 2,365 / 4,767 | 847 | -16.46 | -15.58 | **-0.88** [-3.34, +1.57] |
| sb=OTM1 | 2,710 | 2,395 / 4,749 | 847 | -20.98 | -20.49 | **-0.49** [-3.31, +2.30] |
| sb=OTM2 | 2,953 | 2,700 / 5,407 | 880 | -27.14 | -25.61 | **-1.53** [-4.32, +1.49] |
| sb=OTM3 | 2,813 | 2,464 / 5,020 | 869 | -37.15 | -36.61 | **-0.54** [-3.91, +2.79] |
| settlement=physical | 3,129 | 12,114 / 24,316 | 893 | -24.29 | -23.39 | **-0.90** [-3.53, +1.71] |
| tier=1 | 34 | 167 / 334 | 33 | -24.16 | -15.56 | **-8.60** [-29.41, +15.63] |
| tier=2 | 79 | 375 / 752 | 60 | -21.37 | -6.82 | **-14.55** [-35.34, +3.69] |
| tier=3 | 2,994 | 11,540 / 23,169 | 884 | -24.30 | -24.03 | **-0.27** [-3.03, +2.46] |
| tier=U | 22 | 32 / 61 | 22 | -56.97 | -29.27 | **-27.69** [-63.04, +10.58] |
| year=2019 | 194 | 702 / 1,407 | 71 | -10.35 | -11.33 | **+0.97** [-10.29, +6.67] |
| year=2020 | 300 | 1,187 / 2,389 | 105 | -27.94 | -21.08 | **-6.86** [-15.44, +4.63] |
| year=2021 | 372 | 1,485 / 2,987 | 124 | -20.78 | -20.17 | **-0.60** [-12.59, +7.44] |
| year=2022 | 386 | 1,549 / 3,106 | 113 | -19.35 | -20.83 | **+1.48** [-7.85, +9.54] |
| year=2023 | 402 | 1,520 / 3,059 | 116 | -25.15 | -21.27 | **-3.88** [-9.59, +2.81] |
| year=2024 | 418 | 1,604 / 3,222 | 117 | -24.67 | -27.93 | **+3.26** [-3.04, +9.14] |
| year=2025 | 563 | 2,170 / 4,349 | 146 | -24.51 | -25.15 | **+0.64** [-5.30, +6.85] |
| year=2026 | 494 | 1,897 / 3,797 | 101 | -32.71 | -29.80 | **-2.90** [-11.72, +3.83] |

Arms (block 1 / 5 / 20 intervals of the per-trade mean, %):
- arm_with: 12,114 trades, mean -24.29; b1 [-27.28, -21.00], b5 [-27.55, -20.70], b20 [-28.28, -19.98]
- arm_without: 24,316 trades, mean -23.39; b1 [-25.15, -21.69], b5 [-25.56, -21.01], b20 [-26.33, -20.21]

## 5. Reading (no holdout)

- The picked side lost -24.29 % a trade against -22.50 % for the other side at the same entries: after a positive earnings-day return the call did not beat the put by more than the period's drift, and after a negative one the put did worse than the call. Split by the pick (descriptive): after an up day the call minus both sides is +6.41 pp [-0.48, +13.62]; after a down day the put minus both is -8.46 pp [-16.09, -1.01] — the sign of the market's own drift over 2019–2026 (calls beat puts whatever the report did), which the pooled Δ cancels. Nothing in the cuts (unopened 2019–2022 cells, opened 2023–2026 cells, pre- or post-market, strike bucket, tier, year) has an interval clear of zero on the positive side.
- The base itself loses about a quarter of the debit in ten sessions on these mostly Tier 3 names (spread and decay); Δ would have had to be large and positive to matter, and it is about zero.
- Consistent with S08 (2024–2026, the underlying: no drift after the event-day move) and with the literature on liquid names after 2000. Underpowered for a small drift (prereg §8), so the result says "no drift large enough to carry through 31–60 DTE options", not "no drift".
- The on-disk names: AAPL and FB contribute only from 2019 (the bars on disk start in 2019-01), so their 2015–2018 reports are counted as "no bar for P or R".

## 6. Checks

- `verify_direction.py`: 40 exploration trades (3 from the stored weekly files, 37 from this fetch), drawn with seed 20261027, re-derived field by field (R, P, E1, the exit session, the pick, the expiry, the strike, F, IM, the entry ask, the exit bid, r): **0 differences**.

## 7. Deviations

- **No rule, threshold, window or set was changed after a number was read.** The screen was computed once, after the fetch's
  3.0-hour cut, and it failed; the holdout was not fetched and not read.
- Before the cut, two checks ran on the exploration files fetched so far, printing only counts and entry-side fields (dates,
  expiry, strike, F, IM, bid, ask, tier) — never a return, an exit price or a P&L: the builder's dry run (to see the files
  parse), and the verifier on a temporary trades table (it printed the number of differences only, 0 of 40). Neither changed
  any code that decides a trade.
- Before the prereg, ThetaData request timings were measured on five names in February–March 2024 (opened cells). One of
  them, ZS, was later drawn into the holdout H; only its 2024 rows' counts and request seconds were seen, and the holdout's
  cells are 2019-01 → 2022-12 (disclosed in the prereg's opening paragraph).
- One fetched answer failed verification (RRC 2024-02-23, every expiry: "expirations before the date"); it stays in staging
  and the event is not formed, as §7 says.
- `screen.json`'s "events" column counts the events with at least one trade in the "without" arm of each cut.
- The tier spread's NaN rows raise a numpy "invalid value" warning before the mask drops them; no figure is affected.


## 8. Commands

```
python3 -I ledger.py
python3 -I fetch_direction.py expl
POLARS_MAX_THREADS=4 python3 -I build_direction.py expl
python3 -I verify_direction.py expl 40
# only after a screen pass: fetch_direction.py hold; build_direction.py hold; verify_direction.py hold 40
python3 -I write_report.py
```
