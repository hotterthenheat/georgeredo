# Compass Final — fetch log

The fetch of PREREG_COMPASS_FINAL.md sections 2.4 and 10, after the prereg (`4bc546f`). Code: `fetch_final.py`. Raw data stay
in the scratchpad (`$SP/compass_final/`, 148 MB), never committed. Every request and answer is in
`$SP/compass_final/_fetch_log.jsonl`. No outcome was computed during the fetch; its checks read roots, expirations, stamps
and row counts only.

## Logins and hours

| run | New York time | what | logins |
|---|---|---|---|
| stage 1 probes (before the prereg) | 2026-10-23 21:20–21:22 | `probe_entitlement.py` and its second probe, on non-expiry days only | 2 |
| the fetch | 21:38:40 → 21:59 | `fetch_final.py run`: the expiration check, every job, the verify | 1 |
| the retry | 22:00:21 → 22:00:25 | `fetch_final.py all chains`: the 8 empty answers asked once more (the prereg: "retried, never filled in"); every file already on disk skipped | 1 |

Every request was outside 00:00–01:45 and 19:40–20:30 New York; 3 in flight; the key was loaded in-process, never printed
or logged (the logs pass through a `td1_prod_` redaction). The daily job signs in at 19:47 on weekdays; these logins came
after it.

## Expirations re-checked at fetch time

Theta's `option_list_expirations` lists every prereg session's date: SPY 266 of 266, QQQ 339 of 339, SPXW 297 of 297.

## What came back

| what | sessions asked | files | rows | every file's root | expiration = the session | problems | seconds a request (median / max) |
|---|---|---|---|---|---|---|---|
| SPY same-day chain, 09:30–16:00, every strike | 266 | 266 | 24,124,700 | SPY | yes | 0 | 6.4 / 18.2 |
| QQQ same-day chain, 15:00–16:00, every strike | 339 | **331** | 3,192,801 | QQQ | yes | 0 | 1.2 / 4.8 |
| SPXW same-day chain, 13:00–14:06 (kept: 13:00, 13:01, 14:05, 14:06) | 297 | 297 | 450,092 | SPXW | yes | 0 | 4.1 / 11.6 |
| SPX 1-minute prints (sessions not on disk: 2017-01-03 → 2017-05-31) | 63 | 63 | 391 a session | — | — | 0 | — |
| SPY 1-minute bars 16:00–17:31 | 266 | 266 | — | — | — | 0 (every file has post-market bars with a close) | — |
| QQQ 1-minute bars 16:00–17:31 | 339 | 339 | — | — | — | 0 (every file has post-market bars with a close) | — |

Median strikes a session: SPY 109, QQQ 63, SPXW 169.

**Empty answers (NOT_FOUND, asked twice, not filled in):** QQQ 2012-12-28, 2014-03-28, 2015-05-08, 2015-05-22,
2015-06-19, 2015-07-31, 2015-08-07, 2015-12-31. Those 8 QQQ sessions stay in T1's session list with no trade (the
prereg's rule: every in-test session is a row of the session series, zero when nothing traded). No other answer was empty,
denied or failed.

## Checks before the run (on previously read data only)

Every run script was first exercised on sessions the research had already read, with outputs kept in a scratch folder:
- `run_t123.py` on 2025-10-13 → 10-17 through a throwaway root of the stored chains: the replay's case (0) P&L at the
  study's fees equals the committed replay (`data_recorder/paper_backtest_official`) on 110 of 110 trades (max |Δ| 5e-12);
  the 15:58 exit equals it; C, O and case (a) equal AFTERHOURS.md's committed rows on 45 of 45 trades.
- `run_t4.py` on the same week: the engine audit's scans (70) and touches (81) and hyp B's 3,375 rows rebuilt exactly.
- `run_t56.py` on five 2025 sessions: the T-E and H15 trades equal the final report's rows at both fees (and the same
  event days are skipped).
- `run_t7.py`'s path on QQQ 2024-01: H1's committed rows exactly (21 of 21).
- `analyze_final.py` and `lib_final.py` on those outputs (the statistics run end to end).

T7 needs no fetch and was run once at 21:56 New York, before this commit; its outputs are committed with the results.
