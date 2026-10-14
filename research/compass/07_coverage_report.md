# Coverage report — what history each study used, what the vendors hold, and what was not pulled (2026-10-14)

Companion to `02_coverage_matrix.md` (measured floors per endpoint) and `registry.jsonl` (every run). The owner's decisions: use the full history each dataset permits; no full-archive download; cache only what the next experiments need.

## 1. Histories available versus used

| Dataset | Vendor floor (measured) | Cached and used | Used by | Not used (and why) |
|---|---|---|---|---|
| SPY / QQQ / IWM 1-minute OHLCV | 2012-06-04 (SPY verified; 2014 verified) | **2017-06-01 → 2026-10-09** (2,353 sessions each; `$SP/theta/data/underlying`) | S01 warm-up, S04, S06 | 2012-06 → 2017-05 not pulled: the index-regime series (SPX, VIX) start 2017-01-03 and the screens were already decisive on nine years; extending adds 5 years of the same product class with no regime variables |
| Index 1-minute (SPX, VIX) | 2017-01-03 | 2017-06-01 → 2026-10-09 | S01 regime cells (VIX terciles) | — |
| SPY / QQQ / IWM / SPXW full-strike 1-minute NBBO, same-day expirations | daily expirations exist from 2022-11-11 (SPY, QQQ), 2022-05-13 (SPXW), 2024-04-19 (IWM) | **complete** (`$SP/theta/data_full/chains`, 2.2 GB; manifest `research/thetadata/dataset/MANIFEST_full_chains.md`) | S01, S02 | nothing earlier exists: the 0DTE category has no history before daily listings |
| SPY / QQQ / IWM weekly-expiration chains (1-minute NBBO + OHLC + OI, nearest Friday 1–7 days) | 2012-06-04 | **pulling** 2017-06-01 → 2026-10-09 (`$SP/theta/fetch_cache`, S03 pull; resumable, log `s03_pull.log`) | S03 (pending) | 2012-06 → 2017-05 deferred for the same reason as the bars; pulled on request |
| Tier A single-name 1-minute OHLCV (union of Tier A 2025–2026 ≈ 100–150 roots) | 2012-06 (UTP tape) / 2017-01 (CTA tape) | **queued** 2017-06-01 → 2026-10-09 (S05 pull, after S03) | S06 on Tier A (pending) | tiers before 2025 need the daily-bar years still downloading (2022 → 2012) |
| Stock EOD, every symbol (26,855 listed; ~13–15 k with data per year) | 2012-06-01 (UTP) / 2017-01-03 (CTA) | **2023 → 2026 in the repository** (`data_lake/thetadata/stock_eod`, 11.3 M rows); 2022 downloading; years continue to 2012 in the background at the lowest priority (research pulls hold the single login) | S07, S08 (2024 → 2026 with 2023 as the point-in-time universe year), universe tiers | earlier years extend S07/S08 as they land |
| Option expirations per root (15,817 roots) | all history | complete (`data_lake/universe/expirations.jsonl.gz`) | universe, expiry categories | — |
| Unusual Whales earnings calendar | 1996 → 2026-12 | complete (`data_lake/unusualwhales/earnings.parquet`, 384 k rows) | S08 | before 2024 waits for the daily-bar years |
| Unusual Whales options flow / exposures / contract bars | 2023-11-13 / 2025-04-01 | pulled for the earlier GeorgeFi work (`data_lake/unusualwhales`) | none of S01–S08 | the Compass families in the owner's specification use price, volume and chain liquidity, not flow; flow features are a separate hypothesis class (registry H-entries) and would be tested on their own window against a matched baseline |
| Vendor Greeks / IV | 2020 → | not pulled | — | the engine computes IV and Greeks from the NBBO mid (`engine/greeks.py`); vendor values would not reach 2012–2019 anyway |
| Interest rates | not probed | — | — | r = 0.04 stated constant (`06_implementation_record.md`, known defects) |

## 2. Per study

| Study | Window | Sessions / events | Instruments | Fraction of the vendor history used | Why not more |
|---|---|---|---|---|---|
| S01 owner baseline, 0DTE | 2022-11-11 → 2026-10-09 | 980 sessions (SPY/QQQ), 621 (IWM); 6,882 signals; 2,886 fills | SPY, QQQ, IWM same-day expirations | **100 %** of the 0DTE history | daily expirations did not exist earlier |
| S02 single-factor grid | same | 41 variants × same window | same | 100 % | — |
| S03 weekly expirations | 2017-06-01 → 2026-10-09 | 2,353 sessions per root | SPY, QQQ, IWM nearest-Friday weeklies | 66 % of the option-NBBO history (2012-06 →) | regime series start 2017; extension on request |
| S04 signal validity (underlying) | 2017-06-01 → 2026-10-09 | 2,353 sessions; 5,000–5,400 baseline signals and ~73 k RSI crosses per symbol | SPY, QQQ, IWM | 66 % of the 1-minute bar history | as above |
| S06 trigger screen (underlying) | 2017-06-01 → 2026-10-09 | 2,353 sessions; ~450 k trigger events | SPY, QQQ, IWM; Tier A pending | 66 % | as above |
| S07 daily triggers | 2024-01-02 → 2026-10-13 | 698 sessions; 1,119 / 1,210 / 1,510 symbols per year; 112,938 breakout events | every optionable root ≥ $50 M prior-year median dollar volume | 20 % of the daily history (2012 →) | daily-bar years 2022 → 2012 still downloading; the study re-runs as they land |
| S08 earnings family | 2024-01-02 → 2026-10-13 | 594 event dates; 10,439 reports | same universe | 20 % | same |

## 3. Known limits on the results as they stand

- The intraday findings (S01, S02, S04, S06) rest on three index ETFs over nine years. The single-name intraday screen (S06 on Tier A) is queued behind the S05 pull; until it runs, "no intraday trigger predicts the underlying" is a statement about index products.
- The daily findings (S07, S08) rest on three calendar years (2024 → 2026), a period of persistent index drift; their benchmark-adjusted numbers are the ones to read. The negative sign of breakouts and pullbacks and the absence of post-earnings drift are each consistent across the three years, but three years is three regimes at most.
- No study has yet run on 2012 → 2016; nothing in the coverage prevents it (option NBBO, OHLC and OI exist from 2012-06-04; SPY/QQQ 1-minute bars exist from 2012-06-04), and the fetchers are resumable. The deferral is a sequencing choice recorded here, not a data limit.
- Costs: the C1 half-spread measurements (registry) come from 2025–2026 chains. No spread has been measured on earlier chains, so an option result on 2012–2019 data would carry an unmeasured cost until the half-spreads are measured on those chains (the fetcher caches the NBBO, so the measurement is one pass over the pulled files).
