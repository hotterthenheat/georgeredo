# Final research report: inventory of every study (phase 1)

Built 2026-10-23 from `git log --all --name-status` (356 commits: the branch `claude/lucid-heisenberg-bpyq7k`, 315, plus 41 on
`origin/compass-research-2026-10-14`), the tree at `7dfea57` (tag `archive/before-reset-2026-10-16`, the last commit before
the fresh start `75c29c9`), the current tree and the two scratchpads. Read-only: nothing was run, fetched or changed.

**Where the files are.**
- `@7dfea57` means the file was deleted by `75c29c9` and comes back with `git show 7dfea57:<path>`.
- `SP` is `/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`.
- `SP2` is `/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`.
- `DR` is `data_recorder/` in the repo, which is git-ignored and exists on this disk only.

**Trade-level data codes.**
- **C**: committed (at HEAD, or `@7dfea57`).
- **S**: in a scratchpad or `DR` only.
- **R**: the rerun is needed. The script is committed and its inputs are on disk.
- **N**: none. Nothing to compute from: the study was descriptive or signal-only, was never run, or did not survive.

Every date is 2026-10-xx. Holdout A and holdout B are those of `research_notes/HOLDOUT_LEDGER.md`.

## A. Before the fresh start (recoverable from 7dfea57)

| # | study | folder | prereg / amend / results | date | trades | holdouts |
|---|---|---|---|---|---|---|
| 1 | GeorgeFi reverse-engineering + validation T1–T7 (vendor's own records) | `GEORGEFI_*.md`, `evidence/` @7dfea57 | — / errata 5ed66df / cf555c9 | 13 | C: vendor cards `evidence/public_api/trades_all.json.gz` (D1, 489 cards), books; `research/georgefi_full_history/normalized/trades.csv` | Epoch 1 / Epoch 2 (2026-03-02→), descriptive |
| 2 | "George rebuild": independent backtest of the reconstructed 0DTE level-sweep strategy, 144 variants (registry H1) | `backtest/`, `BACKTEST_RESULTS.md` @7dfea57 | — / — / 8f5b067 | 13 | C: `backtest/results/v1/trades.csv.gz` (192,900), `baseline.csv.gz` | IS < 2026-03-02, OOS 2026-03-02→10-09, read |
| 3 | "George engine audit": phase 1 reproduction audit of #1–#2 (byte-identical rerun); no new rule | `audit/phase1/` @7dfea57 | — / — / 5ed66df (+e95177c T5 rerun) | 13 | C (= #2's files) | — |
| 4 | GeorgeFi full history: A reported, B simulated fills, C reconstruction + random draws, F NBBO re-price, G3 direction/day cross-reference | `research/georgefi_full_history/` @7dfea57 | — / — / 5ed66df, c27ff28 (F), 3a2e8b6 (G3) | 13–14 | C: `C_trades.csv`, `F_nbbo_trades.csv`, `B_trades.csv`, `G_*_rows.csv`; A = vendor-recorded | Epochs, descriptive |
| 5 | Deep research round 1: flow predictors (H2), GEX regime/walls/exit engine q1–q4 (H4–H7, 576 exit configs), short-vol/session T1–T5 (H8) | `research/{flow_predictors,gex_regime_and_exits,short_vol_session}/`, report `Finding a 0DTE options edge.md` @7dfea57 | — / — / 3fc9ff5→fb4205f, 5208c8f | 13 | C partial: `short_vol_session/csv/t*.csv`, `q4_random_entries.csv`, `trade_rule_SPY_F1.csv`; q4 grid by config only | in/out split per note |
| 6 | ThetaData round 2 lanes: T-A 13:00 SPY/QQQ straddle (H9), T-B last-30-min momentum (H10), T-C SPXW straddle (H11), ETF short-premium grid (1,890 configs), SPXW grid, T-E PM-settled straddle (H13), H15 carry strangle, H16, vol filters (H17), settlement audit, full-chain SPXW rerun | `research/thetadata/`, report `High win rate 0DTE lanes.md` @7dfea57 | grid preregs `prereg_sha256.txt`, `protocol_sha256.txt` / gate v1→v2 924aee9 / ebde6ae, b209f7b, e3a76af, 01ee3f3, 5f253c6, 97e685a, 8fb5bad, 6691368 | 13–14 | C: `straddles_nbbo.csv.gz`, `tb_daily.csv`, `tc_straddles.csv`, `te_results.csv`, `spxw_v2/stress_trades.csv.gz`; S: `SP/hwr_grid/days_*.parquet` | TRAIN/TEST, TEST read; H15 T-G forward ≥ 150 sessions never started |
| 7 | Compass engine studies S01–S17 (Quick Scalps 0DTE, 41-variant grid + walk-forward, weekly, SPXW, short-premium fade, events, momentum, VRP straddle, gaps, prior-day fade, put-writing) | `research/compass/{studies,results/v1,engine}/` @7dfea57 | protocol 113cad7 / A1+A2 4aba507, A4 912b415, A5 fe93f87, A5.1 b9b9206, A5.2 eff2382, A6 0a4513b, A7 c81522a; config v1–v1.5 / S01 5e90201, S02 6bf5934, S03+S16b 3c8d6cb, S04 b037899, S06 4aba507, S06-TierA ad7ee20, S07 3562b95, S08 f3ec790, S09 7167541, S10 cf124a0 (rerun 3c8d6cb), S11 0a4513b, S12 2430c9b, S12b be991de, S13/S14 eff2382, d3e732a, S15 6ed12b6, S16a 2430c9b, S17 5e7e1bd | 14–15 | C: `trades.parquet` for S01, S02 (×41 + 3 WF OOS), S03, S09, S10, S11 (prelim), S12, S12b, S15, S16b; `cycles.parquet` S17; N (underlying screens, `rows.json`): S04, S06, S07, S08, S13, S14, S16a | walk-forward; reads counted in holdouts A/B (ledger) |
| 8 | Compass intel V1–V8 (universe straddles IV/RV + term slope, earnings straddles, single-name 0DTE, size forecast, chain calibration, levels vs placebo, event afternoons, month-end straddle) | `research/compass/intel/`, `studies/v*.py`, `results/v1/v*` @7dfea57 | A8 29f20e3 (A8.1–A8.4), A9 47c2c2f, A10–A10.4 9c476c5/048d33a, A11 07b4341, A12 69c055c, A13 50a7683, A14 f098520, A15 8bc3baf / V1 df4fe32+da60418, V2 152f786, V3+V4+V8 e4e4cea, V5 f5b23f6, V6 1660366, V7 f123778 | 15–16 | C: `v1 name_cycles.parquet` + per-cycle CSVs, `v2 trades.parquet`, `v3 trades.parquet`, `v4 index_trades.parquet`, `v8 trades.parquet`; N: V5–V7 (calibration and event tables) | each hold-out opened once (V1 2026-01→08, …) |
| 9 | Compass lifecycle: Tier I (113k setup events × 10 structures × 116 policies), controls L-A2, H-FLO, L-A3 debit call spread, daily tier L-A4/L-A4.1 (19 finalists), portfolios P1–P5 | `research/compass/lifecycle/` @7dfea57 | protocol 1f99d75 / L-A2, L-A3 889691a, L-A4 8bd322a, L-A4.1 f815d27 / 425c7f4, f6d5a98, d8a7ebb, 66bc5c9, 50de62a, b9d04b5, P5* 02b1663–9a9e64b | 15 | C: portfolio `P*_trades.parquet` (dev/val + hold-out); S: Tier I rows `SP/lifecycle/archive` (281 MB), `holdout_rows.parquet` | hold-out 2025-10-01→2026-10-09, OPENED (Tier I, L-A3, H-FLO, daily tier, P1/P2) |
| 10 | Branch `compass-research-2026-10-14`: ATM straddle price samples (SPY/QQQ/IWM + 7 singles; a measurement with no rule) and the independent short-premium prereg | `research/compass_2026_10_14/` on that branch | short_premium PREREG 2f97a0c / — / BLOCKED (ThetaData session lost; no result) | 14–15 | N (price samples only) | — |
| 11 | Price-action catalogue and atlas (43 names, descriptive) | `research/compass/intel/04, 06, 07`, `results/price_action` @7dfea57 | — / — / 048d33a, 0d706b6, 98fa5f0 | 15 | N | — |

## B. After the fresh start (current tree)

| # | study | folder | prereg / amend / results | date | trades | holdouts |
|---|---|---|---|---|---|---|
| 12 | Step 1, every 0DTE contract broken down (no rule) | `step1/` | — / — / 2185eb9 | 16 | C: `contracts_*.parquet` (descriptive) | — |
| 13 | Step 2, buy at nine times of day, sell at 2× or hold (10.5 M trades) | `step2/` | — / — / b15b56b | 16 | C: `entries_*.parquet` | none (option-era months, read) |
| 14 | Step 3, 108 exits × 9 conditions (pick 2022–24, check 2025–26) | `step3/` | — / — / 09885b6 | 16 | C: `paths_*.parquet`, `exits.csv` | pick/check |
| 15 | Step 4, turn-up buy + trailing stop (12.1 M trades) | `step4/` | — / — / 6c0e60b | 16 | C: `trades_*.parquet` | pick/check |
| 16 | Step 5, "runner model" (model A/B, 42 features), top 1% picks, 184 exits, volume | `step5/` | — / — / ae3c63d, 1227394, f9f2746, 491a0c7 | 16–17 | C: `scores.parquet`, `top1_daily.csv`, `exit_paths.parquet` | scored once on 2025–26 |
| 17 | Step 6, the anatomy of the runners (+40% / +500%), 6 rules × 3 exits | `step6/` | 30babaa / — / 44b5547 | 23 | S: `SP/step6/trades_*.parquet` (39 MB); C: `step6/out/results.csv` | 28 months never read |
| 18 | Compass engine audit, six module groups | `research_notes/Compass engine audit/`, `reports/Compass engine audit.md` | — / — / 9cf8110, 59e1a1a, d724ae4, 18cf86a, b84fa3c, 09799af; report 138ff0e | 21 | C: row-level `paths_*`, `events_*`, `spread_*`, `t*_rows.parquet`, horizon `entries_*.pkl` | pick 2022–24 / read 2025–26 |
| 19 | Phase 2 hyp A, closing-pin credit spreads (low moc_mag) | `Compass phase 2/hyp_a_closing_pin` | prereg in doc, before the OOS read (same commit) / — / 5deb793 | 21 | C: `spread_rows_{SPXW,SPY}.parquet` | fit 2022–24 / OOS 2025–26, read once |
| 20 | Phase 2 hyp B, boundary-touch theta and the midday condor (→ condor_em1) | `…/hyp_b_boundary_theta` | in-doc / — / 2c241f4 | 21 | C: `trades_{SPXW,SPY}.parquet` | same |
| 21 | Phase 2 hyp C, debit verticals and late flies (→ fly5, iron ±5) | `…/hyp_c_debit_flies` | `preregistration.md` timestamped before the OOS run / — / faea67c | 21 | C: `spreads_trades.parquet`, `flies_*.parquet`, `legs_*.parquet` | same |
| 22 | Phase 2 hyp D, volatility breakout (straddles) | `…/hyp_d_vol_breakout` | `out/preregistered.md` / — / da02507 | 21 | C: cell tables, `minutes_*.parquet`, `scores.parquet` (by cell, not a trade list) | fit / cut / OOS, read once |
| 23 | Phase 2 report: the midday condor and the iron fly written as candidates with confirmation tests | `reports/Compass phase 2.md` | — / — / 4cc968c | 21 | → #20, #21, #26 | — |
| 24 | Phase 3 hyp E, short-premium lift of the vol model's quiet deciles (→ condor_d20 D1) | `Compass phase 3/hyp_e_short_premium_lift` | `out/preregistered.md` (21:00:44Z) / — / 02d0dcd | 21 | C: by-scan cells, `minutes_SPY_all.parquet` | fit / OOS, read once |
| 25 | Phase 3 hyp F, 15:30 long call ±5 fly (cash account) | `…/hyp_f_cash_butterfly` | `out/preregistered.md` (20:44:54Z) / — / f2883c0; report b7ffa46 | 21 | C: `flies_{fit,oos}.parquet`, `fills.csv` | fit / OOS |
| 26 | Paper-tracker candidates condor_em1, fly5 (iron/call/put), condor_d20, fly_spxw: replay 971 sessions, audit, forward | `scripts/paper_tracker.py`, `Compass phase 3/{backtest_replay,backtest_audit,forward_*}` | defaults ba117a7, 6826b98 / settlement on the official close a4ebe90, 99a3d4e, 16eb3c0 / replay 94af538, 30bb73e; audit 1ca1f0e; forward d7115b6, 2a7bd3b | 21–22 | S: `DR/paper_backtest_official` (316 MB, every trade, git-ignored); C: report CSVs (by cell), `backtest_2026-10-12_2026-10-21.csv`; fly_spxw: N (a one-week sanity run 10-05→09, outside the repo) | i dev 2022-11→2024, ii selection 2025→26-10-09, iii forward 10-12→ |
| 27 | After-hours exercise risk (fly5 iron, condor_d20 hold-to-expiry) | `…/backtest_audit/AFTERHOURS.md` | owner's rule fixed before the read / — / 633fbff | 22 | C: `afterhours_trades.csv` | ii, iii (7 sessions) |
| 28 | SPXW pre-registered analogues (iron fly, 20Δ condor) + ETF−SPXW extrinsic comparison | `Compass phase 3/spxw_prereg` | 2820bb4 / — / 6bb230e | 22 | C: `out/trades.parquet`, `extrinsic*.parquet` | dev / selection / forward 8 sessions |
| 29 | Picker test (GeorgeFi rule): primary, narrative exits (secondary), S2 5-min hard exit, S3 SPXW ride, improved, flow gate, grade check | `Compass phase 3/picker_prereg` | c502122 / — / 1e10053 | 22 | C: `trades_{primary,secondary,s2,s3,improved}.csv`; flow gate 1 session; grade check on vendor cards (#1) | 134 card dates excluded; never-read 10-14→21 line |
| 30 | Compass features: Phase A (23 features), Phase B (33 variants, 3 candidates), forward | `research_notes/Compass features/` | inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049, B read e5dd8c6, forward wired 850268e | 22 | S: `SP/features_work/{expl,hold}/trades_with_inputs.parquet`, `expl/b_exits.parquet` | own: 43 months + AVGO/MU/QQQ: OPENED (Phase A twice, Phase B once); forward 0 sessions |
| 31 | Compass direction, post-earnings drift in 31–60 DTE options | `Compass direction/` | 38b11bf / ledger code 043d723 / 94fb69d | 22 | R: `build_direction.py expl` → `out/expl_trades.parquet` (not on disk; inputs `SP2/dir/store`) | 1,600 names UNOPENED |
| 32 | Compass H1 = edge H1, overnight reversal (SPY/QQQ stock) | `Compass H1/` | 38aca66 / — / 4a02144 | 23 | C: `out/h1_sessions.csv` | single test, none |
| 33 | Edge search queue and ledger | `Edge search/QUEUE.md`, `LEDGER.md` | a49c35b / additions 7ee1d6e / ledger 6b7c355…6612d67 | 22–23 | — | — |
| 34 | Edge H3, earnings IV-crush iron condor (singles) | `Edge search/H3` | 001a136 / — / 34c8fd8 | 23 | C: `out/trades_expl.csv` | 1,600 names UNOPENED |
| 35 | Edge H4, intraday momentum (SPY/QQQ stock) | `Edge search/H4` | b14b640 / — / dfa575d | 23 | C: `out/h4_sessions.csv` | test 2025-10-13→2026-10-22 (spent by S12 etc.) |
| 36 | Edge H5 SPY−SPXW late straddle; H6 monthly put spreads (forward only) | `Edge search/H5_H6` | e114e30 / — / wired 23c0cc3 | 23 | N (no forward row yet) | forward from 10-23 / 11-02 |
| 37 | Edge H7 pre-FOMC drift, H8 turn of the month; H7 forward rule; H7 baseline | `Edge search/H7_H8_H9` | edca472 / forward rule fcc1f4d / 6c94bb8; wired 712b0ad; baseline 827bd5e | 23 | C: `out/h7_trades.csv`, `out/h8_trades.csv` | single test; H7 forward from 10-28 (N 366/483) |
| 38 | Edge H9 overnight drift (forward only), withdrawn | same | edca472 / — / wired 712b0ad, removed c68f389 | 23 | N | forward, no row written |
| 39 | Compass scanner (score ≥ 80, SPY/QQQ/IWM) | `Compass scanner/` | 142fcf4 / — / 9e3888e | 23 | N: the signal check failed its gate; no option P&L; S: `SP/scanner_work/*.npz` | 28 months + AMD/AVGO UNOPENED |
| 40 | Compass EMA ladder: prereg, preview 2025-03 (13 versions), "nearest-EMA targets" rule + preview 2025-02/03 | `Compass EMA ladder/` | 0dd8c5d / rule aad56cf / previews cb79c23, e9d13c0 | 23 | S: `SP2/ema_ladder_out/*.json` (deterministic rerun); full study NOT run | 28 months UNOPENED |
| 41 | EMA system v0 (preview 2026-10-12→16) and v1 (three drawn weeks) | `EMA system/` | v0 af32405, v1 f171654 / — / 8765f71, f512d21 | 23 | C: `out/trades_full.csv`, `out_v1/trades_v1.csv` | previews, no verdict |
| 42 | George A+ entry + EMA targets | (`research_notes/George A+ EMA targets/` planned) | none: the run was stopped before its prereg was committed | 23 | N: no file exists on disk or in history | — |
| 43 | Compass ICT: prereg, 10-session preview, amendment 1, exploration (818 SPXW sessions) | `Compass ICT/` | 9d6c37e / 9dbc0bf / 315fe8e, 0943030 | 23 | C: `out/explore_trades.csv`, `out/trades.csv`, `out/forward_trades.csv` | A and B UNOPENED; finalists named, not read |
| 44 | Compass EMA (three models: EMA pullback/reclaim, 5-min ORB, …) + HOLDOUT_LEDGER | `Compass EMA/`, `HOLDOUT_LEDGER.md` | 9af93fc / — / none (stopped before any result) | 23 | N: partial engine only (`SP2/compass_ema_partial/`, `sessions.json`) | A and B UNOPENED |
| 45 | DR-GCE gate 1 (touch rate) and gate 2 (direction vs volatility) | `DR-GCE/` | 01d5c8e, 294d4f2 / A1 041baba / b20eb9c (PASS, narrow), 00eb3d5 (FAIL) | 23 | C: `out/signals.csv`, `gate2_pairs.csv` (touch outcomes, not P&L); the full backtest never written | 28 months UNOPENED |
| 46 | Trend-day test | — | never registered, never run (the trend-day share is only described in step 6) | — | N | — |
| 47 | Compass core spec v2 and the static checks (a specification, not a test) | `docs/compass-core-spec-v2.md`, `docs/compass-static-checks/` | 061fa99, ba117a7, 16eb3c0, 7883aee, a70e301 | 21 | N | — |
| 48 | reports/: engine audit, phase 2, phase 3, Compass final results (html+pdf) | `reports/` | 138ff0e, 4cc968c, b7ffa46, 64a79b7 | 21–22 | → #18–#30 | — |
| 49 | Daily forward job (steps 1–8: tracker, features, H5/H6, H7; H9 removed) | `scripts/daily_forward.py`, `tests/` | 6826b98, 850268e, 23c0cc3, 712b0ad, c68f389 | 22–23 | forward 10-12→21 (8 sessions) committed; 10-22 appended | forward |

## Notes

1. **"George engine audit"** has no file or commit by that name. It is mapped to #3, the phase 1 reproduction audit of the
   GeorgeFi reconstruction. If the owner meant the 2026-10-21 Compass engine audit, that is #18.
2. **"George rebuild (144 versions)"** is #2. The registry's old ids H1–H17 (#2–#6) are not the edge search's H1–H9
   (#32–#38).
3. **Edge search H2** never existed: the queue numbers skip it. "H2 not added" is recorded in `DIRECTION_REPORT.md`.
4. **Runner model** is step 5's model A (#16). Step 6 (#17) is its anatomy follow-up.
5. **Trade-level data that is NOT committed**, with the cheapest way to get it:
   - **Ready on disk:**
     - #26: the per-trade rows sit in `DR/paper_backtest_official`.
     - #30: the per-trade rows sit in the features scratch.
     - #17: the per-trade rows sit in `SP/step6`.
   - **Rerun needed:**
     - #31: deterministic from the committed script and the stored inputs.
     - #40: deterministic from the committed script and the stored inputs.
6. **Holdouts that remain UNOPENED:**
   - holdout A (2017-06-01 → 2022-05-12) for every rule after the ledger (#39–#45);
   - holdout B (the 28 months) for #17, #39, #40, #43, #44 and #45. Steps 1–5, S01/S02 and Tier I read those months before
     the holdout was defined; the holdout is unopened "for this rule only";
   - the 1,600 holdout names of #31 and #34;
   - AMD and AVGO for #39.
7. **Holdouts that were OPENED:**
   - #30 (three reads);
   - #8 (once each);
   - #9 (2025-10-01 → 2026-10-09);
   - #6 (TEST);
   - the 2025–26 out-of-sample splits of #18–#25, each read once. These are the "selection" period of #26 and #28.
