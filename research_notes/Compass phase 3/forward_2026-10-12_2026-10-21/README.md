# Forward replay, 2026-10-12 → 2026-10-21 (untouched sessions)

**Read this first.** These are 8 sessions that no candidate, model or rule was built, selected or tuned on. Eight
sessions are an initial execution and data-quality check — not proof of an edge. They are never pooled with the
historical (development / selection) results. The candidates' confirmation thresholds stand: 60 → 120 sessions for the
midday condor, 150 for the 20-delta condor's D1 re-test, 250 a name for the flies.

## Data — fetched in this container (2026-10-22, owner-approved ThetaData sign-in)

| sessions | count |
|---|---|
| expected (NYSE full sessions: Oct 12, 13, 14, 15, 16, 19, 20, 21 — Oct 12 Columbus Day, markets open) | 8 |
| fetched | 8 (56 files: same-day full chains SPY, QQQ, SPXW; 1-minute bars SPY, QQQ; SPX and VIX prints) |
| complete (`--verify-parquet` PASS: 391/391 minutes per file, no duplicates, strikes and NBBO sanity within the stored norms) | 8 |
| missing / excluded | 0 / 0 |
| settled (official close on every name-session) | 8 |

- Fetch path: `sdk_fetch.py` (this folder) — the same `thetadata` SDK calls and frame shaping that built the stored
  dataset; one login, one request in flight; staging → verify → merge (stops on any overlap; none) → verify of
  2026-10-05 → 21 with the prior sessions candidate 3 reads: PASS.
- Smallest live test first: SPY bars 2026-10-12 (schema equal to the stored files) and the stored 2026-10-09 SPY bars
  fetched again — equal value for value (391 of 391 rows), so the venue and shaping match the history.
- Files kept for reproducibility: `data/theta_forward/` (19 MB, with the per-day manifests). The key was read from
  the environment only and is in no file or log.
- Official closes: UW daily bars (`/api/stock/{T}/ohlc/1d`, regular session), kept as fetched in
  `data/official_closes/uw_ohlc_1d_2026-10-22.parquet`.

**Official close against the 15:59 bar** (the replay's own convention settles on the 15:59 bar; the audit re-settles on
the official close):

| | Oct 12 | 13 | 14 | 15 | 16 | 19 | 20 | 21 |
|---|---|---|---|---|---|---|---|---|
| SPY official − 15:59 | +0.03 | 0.00 | −0.02 | +0.05 | −0.02 | −0.06 | +0.04 | −0.01 |
| QQQ official − 15:59 | +0.06 | −0.07 | +0.11 | −0.06 | −0.06 | +0.08 | +0.13 | −0.01 |

## Integrity

- Deterministic: the replay run again into an empty root gives a byte-identical report (sha256 `d6a34589fa6ef6ad…`).
- Trades: every tradable capture has exactly one settle row; 0 unmatched. Untradable captures (a vertical under the
  $0.05 minimum credit): condor_em1 1, condor_d20 4, fly5 0. Strategy parameters, entry minutes, strike rules, fees
  and settlement are the live tracker's code, unchanged.

## Results — official close, legs at their own NBBO, $0.65 a contract at the open, none at expiry

Session-aggregated; the interval is the iid-session bootstrap (8 sessions — block intervals need more sessions and are
not reported).

| candidate | valid trades | mean $ a trade | % of max risk | win | mean $ a session | session 95% CI | worst session | +$0.02 a contract | sold at 15:58 instead |
|---|---|---|---|---|---|---|---|---|---|
| SPY midday em1 condor | 39 | +6.35 | 3.5% | 85% | +30.95 | [−117.63, +125.75] | Oct 16 −455 | −1.65 | −6.28 |
| SPY/QQQ ±5 iron fly | 32 | +52.62 | 17.5% | 69% | +210.47 | [+63.03, +352.11] | Oct 19 −100 | +44.62 | +3.07 |
| SPY/QQQ ±5 long call fly | 32 | +49.68 | 16.5% | 69% | +198.72 | [+51.40, +337.10] | Oct 19 −112 | +41.68 | −3.92 |
| SPY/QQQ ±5 long put fly | 32 | +50.21 | 16.6% | 69% | +200.85 | [+53.64, +341.64] | Oct 19 −111 | +42.21 | −2.81 |
| SPY 20-delta condor, 13:00–15:00 (unconditional) | 36 | +21.59 | 12.8% | 94% | +97.18 | [+67.85, +124.20] | Oct 12 +21 | +13.59 | +1.16 |
| — its D1 subset (separate; not the benchmark) | 1 | +38.40 | | | | | | | |

- The flies' three forms share every session's price path (session P&L correlation ≈ 0.99): they are one bet, not three.
- The flies' forward mean is about three times their historical mean: a quiet, pinning stretch for SPY and QQQ at
  15:00–16:00 — eight sessions of one regime, not a new level.
- D1: one trade in one session. Nothing can be read from it; the pre-registered D1 re-test needs ≥ 150 sessions.
- Hold to expiry vs the 15:58 exit: on SPY/QQQ (American, physically settled) holding means stock delivery on any leg
  in the money at the close — the audit's expiration section; the 15:58 column is the exit a cash account can take.

## Commands

```
python3 -I sdk_fetch.py smallest | all | verify | merge | final        # with THETADATA_KEY in the environment
PAPER_PARQUET_ROOT=<stored theta root> python3 -I scripts/paper_tracker.py --backtest --start 2026-10-12 --end 2026-10-21 \
    --candidates condor_em1,fly5,condor_d20 --out "research_notes/Compass phase 3/forward_2026-10-12_2026-10-21"
cd "research_notes/Compass phase 3/backtest_audit" && PAPER_PARQUET_ROOT=<stored theta root> python3 -I run_audit.py --through 2026-10-21
```

`backtest_2026-10-12_2026-10-21.md` here is the replay's own report (15:59-bar settlement, its original method); the
official-close figures above and the period-separated tables are in `../backtest_audit/cumulative_through_2026-10-21.md`.
