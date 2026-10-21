# eod_recorder.py — the Compass Phase 2 recorder

An append-only Unusual Whales recorder for the Compass universe, one Python process, one schedule: an intraday scan
loop (the spot-exposures book by strike at 09:35, every half hour from 10:00 to 15:30, and 15:50 New York) and a
post-close pass at 16:15 (flow alerts of $25,000 and up, dark-pool prints with their NBBO, net-premium ticks, the
day's minute bars, open interest by strike and by contract). Monday to Friday, never on an exchange holiday.

Built 2026-10-21 from the owner's brief, the Unusual Whales docs on disk, the terminal's typed routes and its own
recorder (3abida `src/data/feed/uw.ts`, `server/feed.ts`, `server/fieldRecorder.ts`, `docs/data-feed.md`,
`docs/data-feed-samples.md`), the audit's endpoint list (`research_notes/Compass engine audit/move_atr_flow.md`,
key question 6) and the lake's conventions (`data_lake/README.md`). **No vendor call was made while building it**;
the first live call is the owner's smoke test (below). What that test must settle is listed at the end.

Needs: Python 3.11+ (zoneinfo; on Windows `pip install tzdata`), `polars` (its own Parquet writer — pyarrow is not
needed; it is not installed on the build machine). Nothing else beyond the standard library.

## What it records, from where

| pass | folder | route | a call asks | paging | rows a day (SPY, expected) |
|---|---|---|---|---|---|
| scan | `spot_strike` | `GET /api/stock/{t}/spot-exposures/strike` | the whole book by strike, every expiry together, as UW figured it (`time`, `price` on every row); `limit=500`, `page` from 0 | by `page` until a page is short; cap 10 | 491 a scan × 14 scans |
| eod | `flow_alerts` | `GET /api/option-trades/flow-alerts` | `ticker_symbol`, `min_premium=25000`, `limit=200`, `newer_than` = the day's start, `older_than` walked back on `created_at` | by `older_than`; cap 60 pages | hundreds |
| eod | `darkpool` | `GET /api/darkpool/{t}` | `date=D`, `limit=500` (200 if refused), `newer_than`/`older_than` walked back on `executed_at` | by `older_than`; cap 250 pages | thousands |
| eod | `net_prem_ticks` | `GET /api/stock/{t}/net-prem-ticks` | `date=D` | one call | ~390 (a tick a minute) |
| eod | `ohlc_1m` | `GET /api/stock/{t}/ohlc/1m` | `date=D`, `limit=1000` | one call | ~750 (pre-market to after hours; `market_time` r = regular) |
| eod | `oi_strike` | `GET /api/stock/{t}/oi-per-strike` | `date=D` | one call | 491 (`call_oi`, `put_oi` a strike) |
| eod | `chain` | `GET /api/stock/{t}/option-contracts` | `exclude_zero_oi_chains=true`, `limit=500`, `page` from 0 | by `page`; cap 40 | ~9,900 contracts (20 pages) |

The flow alerts are asked on the MARKET route with `ticker_symbol`: the per-name route `/api/stock/{t}/flow-alerts`
answers without `id`, `start_time` or `end_time` (seen live 2026-10-12). Every field a live answer carried is kept —
`has_sweep`, `has_floor`, `has_singleleg`, `has_multileg`, `all_opening_trades`, `total_premium`,
`total_ask_side_prem`, `total_bid_side_prem`, `total_size`, `trade_count`, `volume`, `open_interest`,
`volume_oi_ratio`, `price`, `bid`, `ask`, `theo`, `underlying_price`, the greeks and IVs, `alert_rule`, `rule_id`,
`expiry`, `strike`, `type`, `created_at`, `start_time`, `end_time`, `sector`, `issue_type`, `marketcap`,
`next_earnings_date`, `er_time` — and any field the vendor adds later lands as an extra column.

The dark-pool rows keep `price`, `size`, `premium`, `volume`, `nbbo_bid`, `nbbo_ask`, `nbbo_bid_quantity`,
`nbbo_ask_quantity`, `executed_at`, `trf_executed_at`, `market_center`, `canceled`, `sale_cond_codes`,
`ext_hour_sold_codes`, `trade_code`, `trade_settlement`, `tracking_id`. The "print ≥ ask = buy, ≤ bid = sell"
signature is computed by the reader from `price` against the two NBBO fields; nothing in the row names the initiator.

### Why open interest comes from `oi-per-strike` and `option-contracts`, not `greek-exposure/strike`

The brief offered "the option-contracts chain or greek-exposure-by-strike". The docs on disk settle it:
`/greek-exposure/strike`'s schema carries **no open-interest field at all** (only `call_gex`, `put_gex`, `call_delta`,
`put_delta`, `call_charm`, `put_charm`, `call_vanna`, `put_vanna`, `strike`) — it is the greeks the OI produces, in
units of its own. So:

- `oi_strike` is `/oi-per-strike?date=D`: the call and put count by strike, every expiry together, one call a name —
  the exact "open interest by strike".
- `chain` is `/option-contracts?exclude_zero_oi_chains=true`: every contract with open interest, its `open_interest`,
  `prev_oi`, `implied_volatility`, UW's greeks, the day's volume by side (`ask_volume`, `bid_volume`, `sweep_volume`,
  `floor_volume` …), NBBO and `last_tape_time` — the per-expiry, per-strike detail `oi-per-strike` flattens, and the
  input the terminal's Terrain field is rebuilt from.

**When a count is counted.** Open interest is published once a day, about 06:45 New York: the count dated D is the
positions at the close of the session BEFORE D. So the 16:15 pass on D records the count published on D's morning
(`oi_strike`'s `date` = D; `chain`'s `open_interest`), and the positions at D's own close arrive in the pass of D+1
(`oi_strike` dated D+1; `chain`'s `open_interest` on D+1, with D's morning count as its `prev_oi`). A reader who wants
"OI at the close of D" reads the row recorded on the next session. `option-contracts` takes no `date`: it answers the
current day only, so a `--force` re-run on a later day records that later day's count (the marker normally prevents
it; the dedupe on `option_symbol` within the day's file keeps the first row).

### The universe

`SPX, SPY, QQQ, IWM` and the audit's top 20 roots by option volume (`research_notes/Compass engine audit/horizons/
top20.json` `top20_used`, SPCX replaced by GME): NVDA, TSLA, AAPL, MU, INTC, AMZN, TLT, META, EWZ, PLTR, AMD, IBIT,
MSFT, GOOGL, MSTR, HYG, AVGO, SOFI, ORCL, GME — 24 names. `--names FILE` (one a line, `#` comments) replaces the list.

An index is asked by UW's own name (`SPX`): its book under `SPX` covers SPXW's dates (UW answered a SPXW date with
rows under SPX, 2026-10-12). It has no stock prints and no bars on Basic (`/darkpool/SPX` has nothing to say;
`/ohlc/1m` answers 422 `cboe_index_access_missing`), so those two are not asked for an index. Its flow alerts are asked
under BOTH roots, `SPX` and `SPXW` (and `NDX`/`NDXP`, `RUT`/`RUTW`, `VIX`/`VIXW` — `ALERT_ROOTS`), the dedupe on `id`
making the second ask harmless; which root UW files them under is unsettled (below).

## Where it lands, and the schema

The data root is `RECORDER_DATA`, else `data_recorder/` in the repository (git-ignored; `--data` overrides). Under it:

```
<root>/<endpoint>/<NAME>/<YYYY-MM-DD>.parquet     one file a name a New York day (zstd)
<root>/_markers/<endpoint>/<NAME>/<day>/<scan>.json   a run marker: done | partial, rows, pages, calls, note
<root>/_failures/<day>.jsonl                      every failed call: when, endpoint, name, scan, the scrubbed error
<root>/_budget/<day>.json                         the day's calls so far (the budget survives a restart)
<root>/_logs/recorder-<utc day>.log               the log (also on stderr)
<root>/dryrun/…, <root>/smoke/…                   the dry run's and the smoke test's own roots, never mixed with the real one
```

**Every column is a string** (`Utf8`), the vendor's value exactly as sent — a numeric string stays the string
(`"0.2376321752265861027190332387"` keeps its digits), a JSON number is printed by Python (`7854`, `-1.5461e-06`),
a bool is `true`/`false`, a null stays null, a list or object is JSON text — the lake's own convention
(`data_lake/README.md`: "values are stored as strings exactly as the API returned them"). A reader casts what it
needs:

```python
import polars as pl
fa = pl.read_parquet('data_recorder/flow_alerts/SPY/2026-10-22.parquet').with_columns(
    pl.col('total_premium', 'total_ask_side_prem', 'total_bid_side_prem', 'strike', 'price').cast(pl.Float64),
    pl.col('has_sweep', 'has_floor') == 'true',
    pl.col('created_at').str.to_datetime('%Y-%m-%dT%H:%M:%S%.fZ', time_zone='UTC'),
)
dp = pl.read_parquet('data_recorder/darkpool/SPY/*.parquet').with_columns(
    pl.col('price', 'nbbo_bid', 'nbbo_ask').cast(pl.Float64), pl.col('size').cast(pl.Int64))
```

The six stamps lead every file, then the endpoint's known columns (the field list a live answer carried on
2026-10-12, `ENDPOINTS[…].columns` in the script), then any extra column the vendor sent, sorted:

| stamp | meaning |
|---|---|
| `_day` | the New York day the row belongs to, `2026-10-22` |
| `_scan` | `eod`, or the scan's label `09:35` … `15:50` (`smoke` from the smoke test) |
| `_scan_at` | the instant the scan was scheduled for, UTC `2026-10-22T13:35:00Z` |
| `_fetched_at` | when the row was fetched, UTC |
| `_name` | the universe name asked (`SPX` for a row whose `ticker` reads `SPXW`) |
| `_key` | the row's identity (24 hex chars, see the dedupe) |

Known columns per endpoint: `flow_alerts` 43, `darkpool` 18, `net_prem_ticks` 13, `ohlc_1m` 9, `oi_strike` 4,
`spot_strike` 37 (`ticker`, `date`, `time`, `price`, `strike` and the 32 `{call,put}_{gamma,delta,charm,vanna}_{oi,vol,ask,bid}`
figures — charm as UW sends it, a YEAR's: the terminal divides it by 365 to print a day's), `chain` 26. A column the
answer did not carry is null; the smoke test prints which known columns were missing and which were new.

### Idempotent: the markers and the dedupe

- **A marker per (endpoint, name, day, scan).** A run that finds a `done` marker makes no call and adds nothing
  (`--force` fetches again; the dedupe still holds). A fetch that did not reach the end of the day — a call that
  failed five times, a page cap — writes a `partial` marker with the reason, and the next run fetches it again.
- **Rows are deduplicated on the vendor's own id**: `flow_alerts` on `id`; `darkpool` on `tracking_id` (with
  `executed_at`, `price`, `size`); `net_prem_ticks` on `tape_time`; `ohlc_1m` on `start_time`; `oi_strike` on
  `date` + `strike`; `chain` on `option_symbol`; `spot_strike` on the scan label + `strike`. A row with none of its id
  fields is keyed on its whole content. The key is `_key`; an append reads the day's file, adds the rows whose key it
  does not hold, keeps the FIRST row of a key (the recorded one, never changed), and writes the file whole through a
  temporary name. Nothing is ever deleted.
- The dry run proves it: a second `--eod` on the same day skips all 144 jobs, makes no call and adds no row
  (`tests/test_eod_recorder.py`).

## The limiter and the budget

`RateLimiter`: at most **3 calls in flight** (UW Basic answers three at once — the fourth of a burst came back 429
"You have exceeded 3 concurrent requests", seen 2026-10-12), a token bucket of **100 calls a minute** (it starts full,
refills at 100/60 a second; `--per-minute`), and a **daily budget of 20,000 calls** (`--budget`, `RECORDER_BUDGET`),
counted per New York day in `_budget/<day>.json` so a restart goes on counting. At the budget the run stops with one
line — `STOP: the daily budget of N calls is spent — the eod pass for D ends here; the markers say what was recorded` —
and the markers of what was not asked stay absent, so the next run (or `--eod` by hand the next morning, before 06:45
if the day's `oi_strike` is wanted as published) picks them up.

Retries: **429** waits the `Retry-After` header (seconds, capped at 120) or 2, 4, 8, 16 s; **5xx and a network
failure** the same; five tries, then the call is given up and the job marked partial. **Any other 4xx** (401, 403, 404,
422) is recorded in `_failures/` and passed over at once — a 422 for a refused `limit` is tried once more at the
fallback limit (darkpool 500 → 200, flow alerts 200 → 100), which then stands for the rest of the run. Every call is
logged as `GET <path?query> -> <status> <ms>`; the query never holds the token.

### The arithmetic (24 names: 3 indices' worth of exclusions = 1 index, SPX)

| | calls | note |
|---|---|---|
| scans | 14 × 24 = **336** | one page a name (SPX 2–3 pages if the book pages at 500: +~40) |
| flow_alerts | ~2–4 pages × 25 roots ≈ **75** | a busy day on SPY may take 5–10 pages of 200 |
| darkpool | 23 stocks × ~5–40 pages of 200 ≈ **300–900** | SPY/QQQ print the most; the cap is 250 pages a name |
| net_prem_ticks | **24** | |
| ohlc_1m | **23** | no index |
| oi_strike | **24** | |
| chain | SPY 20 pages, most names 5–15 ≈ **250–480** | the cap is 40 pages a name |
| **a day, expected** | **≈ 1,100–1,900** | under a tenth of the budget, under 1.2% of UW's 160k |
| **a day, every cap hit** | 3,360 + 1,500 + 5,750 + 71 + 960 = **11,641** | still under 20,000 (`test_budget_arithmetic…`) |

Retries multiply a failing route by five at most; the daily budget is the hard stop either way.

## The schedule and the holidays

New York time, `zoneinfo`: scans at `09:35, 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30,
15:00, 15:30, 15:50`; the EOD pass at `16:15`. Monday–Friday. On a half day (`HALF_DAYS`: the day after Thanksgiving,
Christmas Eve when it falls on a weekday — 2026-11-27, 2026-12-24, 2027-11-26) the scans end at 12:50 and the EOD pass
runs at 13:15.

`HOLIDAYS` is the NYSE calendar the terminal keeps (3abida `src/core/calendar.ts`): 2026 — Jan 1, Jan 19, Feb 16,
Apr 3, May 25, Jun 19, Jul 3, Sep 7, Nov 26, Dec 25; 2027 — Jan 1, Jan 18, Feb 15, Mar 26, May 31, Jun 18, Jul 5,
Sep 6, Nov 25, Dec 24. **Extend both lists each autumn.** A day missing from the list is recorded like a weekday (the
calls answer the session before's rows or nothing — a few hundred wasted calls, never a wrong row: every row carries
its own vendor date or time).

The daemon (`--daemon`) sleeps to the next pass and runs it; started late on a trading day it runs the day's EOD pass
at once if that pass is not yet marked done (a missed scan is simply missing: the book of a past minute cannot be
asked for). `--auto` runs the one pass the clock calls for — a scan within ±4 minutes of its time, the EOD pass any
time after 16:15 until midnight — and otherwise says nothing is due; it is what cron calls.

## Modes

```
python3 -I scripts/eod_recorder.py --eod [--day 2026-10-22] [--only flow_alerts,darkpool] [--force]
python3 -I scripts/eod_recorder.py --scan [--scan-time 10:30] [--day …]
python3 -I scripts/eod_recorder.py --daemon
python3 -I scripts/eod_recorder.py --auto              # for cron: the pass due now, or nothing
python3 -I scripts/eod_recorder.py --smoke [--name SPY]  # ONE call an endpoint; the first live run
python3 -I scripts/eod_recorder.py --status [--data …]
python3 -I scripts/eod_recorder.py --eod --dry-run     # no network: the fake client, a fake clock, under <root>/dryrun
```

Common options: `--data ROOT`, `--names FILE`, `--budget N`, `--per-minute N`, `--in-flight N`, `--min-premium N`.
The token: `UW_API_TOKEN` in the environment, nothing else; the script refuses to start a live mode without it and
never reads a file in the repository for it.

`--dry-run` serves the shapes of `tests/fixtures/uw_templates.json` with made-up rows for the day (a fake clock, so the
100-a-minute pacing costs no wall time) and exercises everything but the socket: the limiter, both kinds of paging,
the `limit` fallback (the fake refuses `darkpool` above 200), the day filter (the fake ignores `newer_than` and
`date=D` on the paged routes on purpose, so the recorder must drop the rows before the day's start — it does), the
dedupe, the markers, the Parquet schema. Measured here: a full `--eod --dry-run` for the 24 names is 144 jobs, 378
calls, 108,658 rows; a `--scan --dry-run` 24 jobs, 26 calls, 12,393 rows; the repeat `--eod` 144 jobs skipped, 0
calls, 0 rows added.

## The first run: the smoke test (the owner)

1. Put the token in the environment of that shell only — never in a file inside the repo:
   `set UW_API_TOKEN=…` (Windows) / `export UW_API_TOKEN=…` (bash). Optionally `RECORDER_DATA`.
2. `python3 -I scripts/eod_recorder.py --smoke --name SPY` — one call an endpoint (seven calls, one page each; the
   flow alerts of SPX would be two). It prints, for each route: the status, rows, the columns the answer carried,
   which known columns were missing, which columns are new, and the first row. It writes under `<root>/smoke/`,
   never the real store. Read the output against the list "Unsettled" below and note what each point settled.
3. `python3 -I scripts/eod_recorder.py --smoke --name SPX` — the index: the book answers; `darkpool` and `ohlc_1m`
   say "not asked"; whether `net_prem_ticks`, `oi_strike` and `chain` answer for SPX, and under which root the flow
   alerts come, is what this run settles.
4. If something refuses (a 422 on a `limit`, a 403 on a route), the message is in the output and in
   `<root>/smoke/_failures/<day>.jsonl`; change the `Endpoint` line in the script (`page_limit`, `max_pages`, the
   params in `fetch`) and run the smoke again. The budget: a smoke run is about ten calls.
5. The first real day: `python3 -I scripts/eod_recorder.py --eod` after 16:15 New York, then `--status`. Check the
   markers are `done` (a `partial` names its reason), and the row counts against the vendor's own pages for one name.
6. Then register the daemon (below) and let it run. `--status` any time; the log under `<root>/_logs/`.

## Keeping it running

**Windows (the owner's machine), Task Scheduler:** `scripts\eod_recorder.cmd` is a restart loop in the style of the
terminal's `recorder.cmd`: it loads `NAME=value` lines from `%USERPROFILE%\.eod_recorder\env` (or `RECORDER_ENV`) —
a file OUTSIDE the repository holding `UW_API_TOKEN=…` and optionally `RECORDER_DATA=…`, `RECORDER_BUDGET=…` — and
runs `python -I scripts\eod_recorder.py --daemon`, starting it again 10 s after it stops. Register the .cmd with
Task Scheduler to run at startup whether or not anyone is logged on; its own log is `<data root>\recorder.cmd.log`.
`pip install polars tzdata` first.

**Linux, systemd:** `scripts/eod_recorder.service` (Type=simple, `--daemon`, Restart=always, the token from an
`EnvironmentFile` outside the repo, mode 600) and `scripts/eod_recorder.timer` (starts the service at boot and each
weekday at 09:00 New York if it is not running). Copy both to `/etc/systemd/system/`, set the user and paths,
`systemctl daemon-reload && systemctl enable --now eod_recorder.timer eod_recorder.service`.

**cron, no daemon:** one line a pass, with `--auto` deciding which pass is due (so a clock a minute off still lands):

```
# crontab -e, TZ of the machine set to America/New_York (or CRON_TZ=America/New_York on cronie)
CRON_TZ=America/New_York
35 9 * * 1-5     cd /home/compass/georgeredo && . /home/compass/.config/eod_recorder/env && python3 -I scripts/eod_recorder.py --auto >> data_recorder/cron.log 2>&1
0,30 10-15 * * 1-5 cd /home/compass/georgeredo && . /home/compass/.config/eod_recorder/env && python3 -I scripts/eod_recorder.py --auto >> data_recorder/cron.log 2>&1
50 15 * * 1-5    cd /home/compass/georgeredo && . /home/compass/.config/eod_recorder/env && python3 -I scripts/eod_recorder.py --auto >> data_recorder/cron.log 2>&1
15 16 * * 1-5    cd /home/compass/georgeredo && . /home/compass/.config/eod_recorder/env && python3 -I scripts/eod_recorder.py --auto >> data_recorder/cron.log 2>&1
```

(`--auto` on a holiday or a weekend does nothing; on a half day the 13:00–15:50 lines find nothing due and the EOD
runs from the 16:15 line — later than 13:15, which is fine for an end-of-day pass. The env file is sourced, never
copied into the crontab.)

## The tests

`python3 -I tests/test_eod_recorder.py` (or `python3 -I -m pytest tests/test_eod_recorder.py -q` where pytest is
installed; it is not on the build machine). Seventeen tests, all on the fake client and a fake clock, all passing on
2026-10-21: two runs add no duplicate and the second makes no call; a partial marker is fetched again without a
duplicate; the marker file's shape; the limiter paces 100 a minute (the 101st call waits 0.6 s, two hundred take a
minute, three threads make 300 calls in 120 fake seconds without spinning), holds three in flight, and stops at the
budget with the STOP line while saving the count; 429 waits the Retry-After, 5xx backs off 2-4-8-16 and gives up
after five, a 404 is one call recorded and passed over; the token never appears in a log line, a marker, a failure
record or an error even when a staged exception carries it, and the scrubber masks any Bearer value; every Parquet
column is a string with the stamps first and every known column present, a bool as text, a null as null; the day's
bounds in EDT and EST, the timestamp parser, the schedule (weekends, Thanksgiving, the half day, Friday evening →
Monday 09:35, `--auto`'s window); the universe; the budget arithmetic.

## Unsettled until the smoke test (each coded on the best reading, marked in the script's `Endpoint.note`)

1. **`flow-alerts` paging.** `limit=200` is assumed (UW caps `congress/recent-trades` and `multi-leg` at 200;
   nothing on disk states this route's cap) with 100 as the fallback; `older_than` is assumed to compare `created_at`
   (the answer echoes `older_than`/`newer_than` as ISO times); `newer_than` is assumed honoured but the recorder keeps
   only the day's rows regardless. The echoed `newer_than` two months back suggests a 60-day window — a backfill of
   past days with `--day` may reach that far, and no further.
2. **`darkpool/{t}` paging.** `limit=500` is asked first (200 seen live; a 422 naming `limit` drops it to 200),
   `older_than` on `executed_at` (the changelog of 2024-05-30 adds it to this route), `date=D` passed as well; whether
   `date=D` alone bounds the day, and the per-day print count (hence the pages) for SPY, are unknown — the cap is 250
   pages (50,000 prints).
3. **`spot-exposures/strike` paging.** The route lists `limit` and `page`; the terminal read 491 rows for SPY in one
   answer without either. The recorder asks `limit=500&page=0,1,…` and stops at a short page. If the route ignores
   `page` and answers the same 491 rows for every page, the cap (10) ends it and the file holds 491 rows, the marker
   `partial` with "page cap reached" — the smoke test's `pages` figure says which; then set `paging='none'`.
4. **An index.** `SPX`'s book, OI by strike and chain: whether `/oi-per-strike` and `/option-contracts` answer for an
   index, and whether the chain includes SPXW's contracts or only SPX's AM monthlies (the expiry breakdown lists the
   roots apart; the book under SPX answered a SPXW date). `net-prem-ticks` for an index: unknown. Flow alerts: asked
   under `SPX` and `SPXW` both — the smoke on SPX shows which root carries rows.
5. **`ohlc/1m` `limit=1000`.** Seen live on 2026-10-12 (`date=D&limit=1000` answered a day's 746 bars). If a day
   ever carries more than 1,000 bars the file is short by the oldest pre-market minutes; raise the limit.
6. **`option-contracts` page count.** 20 pages for SPY on 2026-10-12 (9,875 contracts with OI); the cap is 40.
   A name with more than 20,000 open contracts would be cut — none in the universe is near it.
7. **Rate ceilings.** Three in flight is measured; the 100-a-minute bucket and the 20,000 daily budget are the
   brief's, well under the 160,000 the plan allows (the per-minute header read 1,000,000 on 2026-10-12).
8. **Holidays past 2027** and any early close other than the two listed: extend `HOLIDAYS` and `HALF_DAYS`.
