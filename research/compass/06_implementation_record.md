# Implementation record (running log; deliverable 12 of the brief)

Every entry: what was done, the exact command or file, its verified outcome. Newest at the bottom. Times UTC, 2026-10-14 unless stated.

| Time | Action | Outcome |
|---|---|---|
| 15:17 | Owner's decisions received: GeorgeFi work stops; no full-archive download; use both repositories; full history where fields exist; research edges with gates | Recorded in `03_reconciliation.md` and the registry (`RULE-separation`) |
| 15:19 | `add_repo hotterthenheat/3abida`, `git clone --depth 1` → `/home/user/3abida` at `d2553cc` | Clone OK; shallow (no earlier history readable) |
| 15:20–15:27 | Read Compass engine, stand-in mapping, contract weigher, types, expiry logic, indicator library, feed clients, backtest spec, setups spec | `01_implementation_audit.md` (commit `17ad7d8`): the engine is a hash-seeded placeholder on a simulator; none of the brief's parameters exist in either repo |
| 15:28–15:30 | `boundary_probe.py` against ThetaData (stock job paused at a batch boundary and restarted) | `data_audit/probe1.log`, `thetadata_boundaries.json`; option NBBO/OI/EOD verified 2012-06; stock EOD/tick floors tape-dependent (2012-06 UTP, 2017-01 CTA); index 2017-01 |
| 15:35–15:47 | `boundary_probe2.py` (corrected argument types) | `probe2.log`, `thetadata_boundaries2.json`; stock EOD by year, quotes/trades floors, Greeks only from ~2020; the 2016 option probe hit a Sunday (my error, bracketed by 2014 and 2020) |
| 15:37 | `registry.jsonl`, `03_reconciliation.md` | Commit `386fea8`: H1–H15, G1–G2, C1, gates v1/v2, data limitations |
| 15:40 | `04_protocol.md` pre-registered; `universe/list_expirations.py` | Commit `113cad7` |
| 15:49–15:52 | `list_expirations.py` over 15,817 roots (job paused/restarted around it) | 15,817 records, 0 errors, 157 s → `data_lake/universe/expirations.jsonl.gz` (sha256 in `manifest.json`) |
| 15:44–15:50 | Engine: `calendar.py`, `indicators.py`, `bars.py`, `greeks.py` + tests | 14 tests pass; calendar verified against SPY daily bars (2024–2026) and minute-bar half days (2017–2026) |
| 15:50 | `02_coverage_matrix.md` | Commit `d16a813` with the probes, engine pipeline (signals, contracts, sim, stats, store, run), smoke test |
| 15:53 | `universe/tiers.py` | Tiers for 2025 and 2026 (6,026 optionable roots with bars in 2026; Tier A floor $1.03 B median daily dollar volume); earlier years wait for the daily bars (job in progress) |
| 15:55 | Study S01 launched: `studies/s01_quick_scalps_0dte.py` (loop simulator) | SPY: 2,392 signals, 1,126 filled in 341 s; QQQ/IWM running |
| 15:58 | Found 264 SPY minute-bar cache files (2018) typed as strings and 89 holiday files; loader now casts and skips non-sessions | Commit `29a8152` |
| 16:02–16:06 | Vectorised `sim.simulate`; equivalence test against the loop on real data (5 exit sets) | 20 tests pass; commit `cd835f9` |
| 16:08 | Study S02 grid launched (42 single-factor variants, 3 workers) | Running; outputs under `results/v1/s02_quick_scalps_grid/` |
| 16:10 | S03 pull chain armed: after the 2023 daily bars finish, pause the stock job, pull the weekly-category chains for SPY/QQQ/IWM 2017→2026 (OI for every candidate expiration, then NBBO + OHLC of the most-OI expiration), restart the job | Background task `be4tsjpfo` |

## Known defects and open items
- Event flags (FOMC/CPI/NFP) exist only from 2017-02; earlier sessions report `unknown`.
- Interest rate r is a stated constant (0.04); the ThetaData rate series is not wired.
- Settlement for physically settled ETF contracts held to expiry is modelled at intrinsic on the 16:00 close (after-hours exercise caveat from the prior studies applies; the long-option families never hold to expiry by design).
- Open interest and intraday option volume are not in the 0DTE cache, so S01/S02 run without the OI > 250 / volume > 100 filters; S03 onwards applies them (pulled with the chains).
