# eod_recorder.py — the Compass Phase 2 recorder

An append-only Unusual Whales recorder for the Compass universe, one Python process, one schedule: an intraday scan
loop (the spot-exposures book by strike at 09:35, every half hour from 10:00 to 15:30, and 15:50 New York) and a
post-close pass at 16:15 (flow alerts of $25,000 and up, dark-pool prints with their NBBO, net-premium ticks, the
day's minute bars, open interest by strike and by contract). Monday to Friday, never on an exchange holiday.

Built 2026-10-21 from the owner's brief, the Unusual Whales docs on disk, the terminal's typed routes and its own
recorder (3abida `src/data/feed/uw.ts`, `server/feed.ts`, `server/fieldRecorder.ts`, `docs/data-feed.md`,
`docs/data-feed-samples.md`), the audit's endpoint list (`research_notes/Compass engine audit/move_atr_flow.md`,
key question 6) and the lake's conventions (`data_lake/README.md`). **No vendor call was made while building it**;
the first live calls were the owner's smoke test of 2026-10-21 (below); what it settled is listed at the end.

Needs: Python 3.11+ (zoneinfo; on Windows `pip install tzdata`), `polars` (its own Parquet writer — pyarrow is not
needed; it is not installed on the build machine). Nothing else beyond the standard library.

## What it records, from where

| pass | folder | route | a call asks | paging | rows a day (SPY, expected) |
|---|---|---|---|---|---|
| scan | `spot_strike` | `GET /api/stock/{t}/spot-exposures/strike` | the whole book by strike, every expiry together, as UW figured it (`time`, `price` on every row); `limit=500`, `page` from 0 (honoured) | by `page` until a page is short; cap 10 | 491 a scan × 14 scans (SPX 824, two pages) |
| eod | `flow_alerts` | `GET /api/option-trades/flow-alerts` | `ticker_symbol`, `min_premium=25000`, `limit=200` (accepted), `newer_than` = the day's start (honoured), `older_than` walked back on `created_at` | by `older_than`; cap 60 pages | hundreds (200 a page) |
| eod | `darkpool` | `GET /api/darkpool/{t}` | `date=D` (does not bound the day — the recorder's filter does), `limit=500` (accepted; 200 if refused), `newer_than`/`older_than` walked back on `executed_at` | by `older_than`; cap 250 pages | thousands (a page of 500 spans ~35 minutes) |
| eod | `net_prem_ticks` | `GET /api/stock/{t}/net-prem-ticks` | `date=D` | one call | ~390 (a tick a minute) |
| eod | `ohlc_1m` | `GET /api/stock/{t}/ohlc/1m` | `date=D`, `limit=1000` | one call | ~870 (04:00 to 20:00; `market_time` pr / r / po, every row kept) |
| eod | `oi_strike` | `GET /api/stock/{t}/oi-per-strike` | `date=D` | one call | 491 (`call_oi`, `put_oi` a strike) |
| eod | `chain` | `GET /api/stock/{t}/option-contracts` | `exclude_zero_oi_chains=true`, `limit=500`, `page` from 0 | by `page` until a page is short; cap 40, **150 for an index** (SPX: both roots in one chain) | 9,625 contracts (20 pages, the last 125 rows); SPX more than 20,000 |

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
making a row filed twice harmless; UW files them under both (the smoke: SPX 174 rows, SPXW 200).

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

Known columns per endpoint: `flow_alerts` 44 (`missing_periscope` on an index's rows), `darkpool` 18, `net_prem_ticks` 13, `ohlc_1m` 9, `oi_strike` 4,
`spot_strike` 37 (`ticker`, `date`, `time`, `price`, `strike` and the 32 `{call,put}_{gamma,delta,charm,vanna}_{oi,vol,ask,bid}`
figures — charm as UW sends it, a YEAR's: the terminal divides it by 365 to print a day's), `chain` 26. A column the
answer did not carry is null; the smoke test prints which known columns were missing and which were new. Since `.3`
four more close every row: `is_macro_event_day`, `macro_events`, `minutes_to_macro_release` and
`minutes_since_last_release` (the scan's minutes at its scan time, an EOD row's null; all null when the calendar is not
on disk — "The macro stamps" below); they are not vendor fields and never part of the key.

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
| chain | SPY 20 pages, most names 5–15, SPX ~45–60 ≈ **275–520** | the cap is 40 pages a name, 150 for an index (SPX) |
| **a day, expected** | **≈ 1,100–1,900** | under a tenth of the budget, under 1.2% of UW's 160k |
| **a day, every cap hit** | 3,360 + 1,500 + 5,750 + 71 + (23 × 40 + 150 =) 1,070 = **11,751** | still under 20,000 (`test_budget_arithmetic…`) |

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
   never the real store. The run of 2026-10-21 is kept in `data_recorder/smoke/smoke_SPY.txt`; what it settled is the list "Settled by the smoke test" below.
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
installed; it is not on the build machine). Twenty-one tests, all on the fake client and a fake clock, all passing on
2026-10-21: two runs add no duplicate and the second makes no call; a partial marker is fetched again without a
duplicate; the marker file's shape; the limiter paces 100 a minute (the 101st call waits 0.6 s, two hundred take a
minute, three threads make 300 calls in 120 fake seconds without spinning), holds three in flight, and stops at the
budget with the STOP line while saving the count; 429 waits the Retry-After, 5xx backs off 2-4-8-16 and gives up
after five, a 404 is one call recorded and passed over; the token never appears in a log line, a marker, a failure
record or an error even when a staged exception carries it, and the scrubber masks any Bearer value; SPX's 824-strike book pages twice and its alert rows carry `missing_periscope` as a known column; the eod chain walk stops on the short page (20 pages for 9,625 contracts); every Parquet
column is a string with the stamps first and every known column present, a bool as text, a null as null; the day's
bounds in EDT and EST, the timestamp parser, the schedule (weekends, Thanksgiving, the half day, Friday evening →
Monday 09:35, `--auto`'s window); the universe; the budget arithmetic; since `.3`, an index's chain pages to 150 (a
25,000-contract SPX chain done in 51 calls) while a stock's stops at 40 and is marked partial, and every row carries
the macro stamps (a 10:30 scan 210 minutes before a 14:00 FOMC decision; an EOD row null minutes; a missing calendar
null with one WARN; the stamps never in the key).

## The forward paper tracker (scripts/paper_tracker.py)

A second, isolated logger beside the recorder — it imports the recorder's client, limiter, scrubber, store and calendar
and adds nothing to the UI or to any signal. It records, every session, the candidates at their minutes from Unusual
Whales' same-day chain, so their forward confirmation samples accumulate on their own (`paper-tracker-2026-10-21.2`):

| candidate | names | minutes (New York) | the structure, as its report's engine picks it | threshold |
|---|---|---|---|---|
| `condor_em1` (`hyp_b_boundary_theta.md`, "The rule, conditional on X") | SPY | 11:30, 12:00, 12:30, 13:00, 13:30 | the ATM straddle M = call mid + put mid at the strike nearest spot with both sides quoted (a tie → the lower strike); short call = the first listed strike ≥ spot + M, short put = the first listed strike ≤ spot − M; longs 2 points beyond; shorts filled at the bid, longs at the ask; each spread's credit ≥ $0.05 (the condor's ≥ $0.10) else the row says `tradable=false`; every VIX | 60 settled sessions, then 120 |
| `fly5` (`hyp_c_debit_flies.md` section 6) | SPY, QQQ | 15:00, 15:30 (+ 15:58 close quotes) | K0 = the strike nearest spot with a call and a put quoted (a tie → the lower); wings ±5; three structures a capture — the iron fly (sell the K0 call and put at the bid, buy the K0−5 put and K0+5 call at the ask; max risk 5 − credit), the long call fly and the long put fly (buy the wings at the ask, sell two K0 at the bid; max risk = the debit); the short legs' bids > 0, max risk ≥ $0.05; stress fills $0.01 and $0.02 a leg worse | 250 settled sessions a name |
| `condor_d20` — **candidate 3** (`hyp_e_short_premium_lift.md` §8, "needs X (1)") | SPY | 13:00, 13:30, 14:00, 14:30, 15:00 | the 2-wide iron condor at Hypothesis B's `d20` short strikes (below), longs 2 beyond, held; fills and the tradable rule as `condor_em1`; every row carries the live t2 decile of the FROZEN SPY volatility model (below) — a column, never a filter | 150 settled sessions |
| `fly_spxw` (`--spxw` only, OFF by default) | SPX (the SPXW root) | 15:00, 15:30 | the iron, call and put flies at ±5 and ±25 around K0 = the listed SPXW strike nearest parity-implied SPX (below) | 250 settled sessions |

Quotes: `GET /api/stock/{name}/option-contracts?expiry=D&limit=500&page=0…` (a same-day chain is one page — SPY's 302
contracts on 2026-10-21, zero-OI strikes included; paged until a short page, cap 5), `nbbo_bid` / `nbbo_ask` a contract,
the strike, right and expiry read off `option_symbol`. Spot: `GET /api/stock/{name}/stock-state` `close`. **The route
carries no quote sizes**, so the `l*_bid_size` / `l*_ask_size` columns stay null until a route that does is found.

The settle pass at **16:20** logs, a name: `ohlc/1m`'s last regular bar's close (the 15:59 bar, `close_1m_r`) and the
bar stamped 16:00 (`close_1m_1600`), the stock-state `close` at that minute with its `market_time` (after the close it
is the post-market last print — 773.50 against the official 773.09 on 2026-10-21 — logged, never used as the
settlement) and its `prev_close`, and the official close from the daily bar (`/ohlc/1d?date=D`, the `r` row dated D,
`close_official`). The settlement used is the official close when the bar carries it, else the 15:59 bar; each leg at
intrinsic; $0.65 a leg at the open, nothing at expiry (a worthless leg pays nothing, an in-the-money leg settles at
intrinsic with no fee assumed — the reports' convention); P&L at the NBBO fill, at the mid, and at the two stresses;
and the **$0.25 settlement check** = |15:59 bar close − official close| ≤ 0.25 (`check_025`), a session. `--settle` is
re-runnable: a name settled on the official close is skipped before any call; one settled on the 15:59 bar alone is
asked again and gains its `official` rows once the daily bar has the day. The 16:20 time is the brief's; the terminal
reads the official close from 4:01 pm and keeps it from 4:30 pm, so a 16:20 pass may find the daily bar's `r` row not
yet there — the next `--settle` (or the daemon's next day) fills it. SPY's whole-day `ohlc/1m` answer read there is
also kept in the model's minute-bar cache (no extra call). A settle row carries its capture's macro stamps and (for
candidate 3) its deciles, and (for fly5) the 15:58 exit beside the 16:00 settlement.

### Candidate 3: the strike rule

Hypothesis B's `nearest_delta` (`hyp_b_boundary_theta/engine.py`), reproduced line for line in `paper_tracker.py`
(`bsm_abs_delta`, `otm_deltas`, `nearest_delta`): the candidates are the OTM strikes (a call K > spot, a put K < spot)
whose quote stands (bid and ask, ask ≥ bid ≥ 0) with mid > 0, ask > 0 and the mid under its no-arbitrage bound (a
call's < spot, a put's < K); each one's total vol v = σ√τ is solved from its own mid by 60 bisections on [1e-5, 5] at
r = q = 0 (a put through parity, C = P + S − K); |delta| = N(d1) for a call, 1 − N(d1) for a put. Only σ√τ enters the
delta, so the "τ to the 16:00 close" of the brief cancels — no clock is read. The short is the strike whose |delta| is
nearest **0.20**; **a tie goes to the FARTHER out-of-the-money strike** — the larger call strike, the smaller put
strike — because the code sorts `np.lexsort((-ks if call else ks, |delta − target|))`; the line's comment says "ties:
the nearer-the-money strike", but the code is what produced the research's trades, so the code is reproduced (an exact
tie in floating point is all but impossible on real quotes). Spot is UW's stock-state `close` at the minute, as for
`condor_em1` (Hypothesis B used the close of the bar ending at the minute; `model_spot` logs that one). Longs at the
short ± 2 (listed and quoted); each vertical's credit ≥ $0.05 or the row is `tradable=false` with its reason.
Logged: `short_call_k`, `short_put_k`, `short_call_delta`, `short_put_delta`, `delta_target`; `k0` and `straddle`
are the ATM straddle as `condor_em1` reads it (for the record). The tests price a chain at a known σ√τ and check the
deltas against the closed form (S 500, v 0.01: the 0.20 call is 504 at 0.2142, the put 496 at 0.2095).

### Candidate 3: the frozen model

Hypothesis E's t2 model (`hyp_e_short_premium_lift/fit_model.py` `full_gbm`), refit ONCE by
`scripts/models/freeze_t2_spy.py` exactly as Hypothesis E did — SPY alone, Hypothesis D's 25 features (`lib.FEATURES`,
in that order) on `out/minutes_SPY_all.parquet`, fit = sessions before 2024-07-01 on the 71 scan minutes 09:35 … 15:25
(28,750 rows, 405 sessions), Hypothesis D's LightGBM settings from its `model.py` (`num_leaves` 15, `learning_rate`
0.05, 400 trees, `min_child_samples` 200, `subsample` 0.8, `colsample_bytree` 0.8, `reg_lambda` 1, `num_threads` 1,
`random_state` 1), the nine decile cuts the inner quantiles of the final score on 2024-07 → 2024-12. **It reproduced
Hypothesis E to the bit**: the scores of all 69,895 rows equal `out/scores_SPY.parquet`'s (max difference 0.0), AUC
in-sample 0.8092, out-of-fold 0.6131, cut 0.5994 (Hypothesis E's 0.809 / 0.613 / 0.599), the cuts 0.187, 0.2351,
0.2705, 0.3001, 0.3303, 0.3604, 0.3983, 0.4452, 0.5135 (its log). A second model, **`t2_spy_novix`**, is fitted
identically without the four VIX features (`vix`, `vix_chg_open`, `vix_chg30`, `vix_chg_prev`; 21 features; AUC
0.7919 / 0.6164 / 0.6108, its own cuts) so that a session without VIX still has a decile.

Files, `scripts/models/`: `t2_spy_full.txt` and `t2_spy_novix.txt` (LightGBM's text model), `*.cuts.json` (the nine
cuts and the decile rule — `clip(searchsorted(cuts, score, side='right'), 0, 9) + 1`), `*.manifest.json` (the features
in order, the training rows and sessions, the AUCs, the settings, LightGBM 4.7.0, the sha256 of the model and the
cuts, the reproduction check). The tracker **loads, never refits**: `vol_model.FrozenModel.load` checks both sha256s
against the manifest and refuses a changed file; it scores in plain Python (`vol_model.TextBooster` walks the text
model's trees as LightGBM's NumericalDecision does), so the owner's machine needs no LightGBM — checked equal to
LightGBM's own scores on 3,000 rows (max difference 0.0) and on the ten fixture rows a model in
`tests/fixtures/t2_feature_rows.json`. Columns a candidate-3 row carries: `t2_score_full`, `t2_decile_full`,
`t2_score_novix`, `t2_decile_novix`, `t2_decile_primary`, `t2_primary_model`, the 25 features as `f_<name>`,
`vix_source`, `vix_note`, `model_spot`, `model_atm_k`, `model_straddle`, `t2_bar_last` (the last bar's start, New
York), `t2_bar_complete`, `t2_bar_asks`, `t2_prior_sessions`, `t2_atr_sessions`, `t2_relvol_sessions`, `t2_note`,
`t2_model_full_sha`, `t2_model_novix_sha` (the first 16 of the sha256).

The live features (`vol_model.features_at`, the exact definitions of `hyp_d_vol_breakout/lib.py` `session_rows`),
from UW alone but VIX:

- **SPY's minute bars**: `GET /api/stock/SPY/ohlc/1m?date=D&limit=1000`, the regular rows (`market_time` `r`). UW stamps
  a bar by its open — `start_time` 13:30:00Z, `end_time` 13:31:00Z is the 09:30 bar (checked on the recorder's
  2026-10-21 file and the two parity days) — the convention the model assumed (Theta's bars, stamped at their open):
  the bar starting at 09:30 + (m − 1) closes at minute m and its close is the price known at m. A capture reads the bars
  closing at or before its minute; if the bar closing AT the minute (stamped m − 1) is not out yet it asks once more
  after 20 s, and otherwise carries the last close (`t2_bar_complete=false`, said in `t2_note`).
- **The sessions before** (ATR14, the previous close, the 20-session relative-volume norm): the cache
  `data_recorder/paper/_cache/bars/SPY/<day>.json`, a whole session a file — filled by the settle pass (its `ohlc/1m`
  answer), else read from the recorder's own `data_recorder/ohlc_1m/SPY/<day>.parquet` (no call), else backfilled ONCE
  with one call a day. The previous close is the last regular bar's close of the session before and ATR14 the mean
  true range of the 14 sessions before (at least 10) — the audit's day table, which is built from minute bars, so the
  "daily bars" are the cached minute bars' daily aggregates (UW's `/ohlc/1d?date=D` answers one day a call — its
  `limit` does not reach back — so 15 calls would buy a definition the model was not trained on). `rel_vol` = the five
  bars closing m−4 … m over the median of the same five bars in the up to 20 sessions before (at least 10; a missing
  minute 0). The previous sessions are the recorder's calendar (half days included, as in the day table).
- **The ATM straddle**: off the chain the capture already read — among the five listed strikes nearest the bars' spot,
  the nearest with both sides quoted (ask > 0), call mid + put mid.
- **VIX**: UW first — `GET /api/stock/VIX/stock-state` **answers 422 "Stock state data is not available for index
  ticker VIX" on UW Basic (checked live 2026-10-21, one GET)**; the tracker asks at most once a session and remembers
  the 422 for the day (`_cache/vix/<day>.json`). Then the owner's **Theta Terminal** at `http://127.0.0.1:25503/v3`
  (`/index/history/price?symbol=VIX&date=YYYYMMDD&interval=1m&format=ndjson`; the terminal holds the key, none is sent;
  always 127.0.0.1, never "localhost"; no proxy; `THETA_BASE` overrides): the day's VIX minutes (the print stamped m is
  the price at m; `vix_chg_open` off the 09:31 print, `vix_chg30` off m − 30) and the session before's last print to
  16:00, kept a day. Else none: the VIX features are null, `vix_source=none`, one WARN line a session.

### Candidate 3: the pre-registration (written 2026-10-21, before any live session is logged)

- **The primary decile** of a row is `t2_decile_full` (the full model) when all four VIX features are present at the
  minute (`vix_source=theta`, normally), else `t2_decile_novix` (the no-VIX model): `t2_decile_primary`,
  `t2_primary_model`. Both models' deciles are on every row; the other one is secondary.
- **The test** (Hypothesis E §8, fixed there): signal = primary decile 1 at the capture minute; cell = SPY 2-wide iron
  condor, 20-delta shorts, the five minutes 13:00 … 15:00, held to settlement; P&L = `pnl_nbbo` of the `official`
  settle rows (shorts at the bid, longs at the ask, $0.65 a leg in, nothing at expiry; Hypothesis E settled on the 16:00
  bar — `close_1m_1600` is logged beside it); rows `tradable=true`. The lift = Σ_s N_D1(s) · [mean(net | D1 at s) −
  mean(net | every session at s)] / Σ_s N_D1(s), in % of max risk and in $, a 95 % paired session bootstrap (2,000
  draws, seed 20261016). **Edge = both intervals above zero AND the lift > 0 without the best five sessions**, read
  once at **≥ 150 settled sessions**. The expectation, written in Hypothesis E from the fit: inside the noise.
  Secondary reads (never the verdict): the full and the no-VIX deciles each; with and without macro-event days
  (`is_macro_event_day`, `minutes_to_macro_release` — the FOMC-afternoon effect Hypothesis E found); the unconditional
  condor itself (the benchmark, "needs X" from Hypothesis B).
- What the parity check (below) means for it: the live decile is the frozen model applied to UW's bars, which differ
  from Theta's by cents; it agrees with the Theta-built decile at 80 % of minutes (all disagreements within one decile
  at the candidate's five minutes, where it agreed 10 of 10). The test reads the live decile as defined here; it does
  not claim to reproduce Theta's.

### Candidate 3: parity of the live features (`scripts/models/parity/parity_t2_spy.py`, `parity_result.txt`)

- **The port** (Theta's own bars, VIX prints and chain through `vol_model`, 14 sessions 2023-03 → 2026-10, every scan
  minute, 1,008 rows): every feature equals `out/minutes_SPY_all.parquet` (max difference 0; `rv_session` 3e-12), the
  decile agrees 1,008 of 1,008 for both models.
- **UW's bars in place of Theta's** (2026-10-08 and 2026-10-09, `ohlc/1m?date=D` — two GETs, the answers kept in `data_recorder/parity/` (git-ignored); the sessions before and
  VIX still Theta's, since rebuilding 20 sessions before each from UW is 20 calls a day): UW has the same 390 regular
  minutes, but closes differ by more than half a cent at 85 and 144 of 390 minutes (max 7 and 12 cents; highs up to 24
  cents), volume a minute 0.996–0.998 of Theta's at the median (0.79–1.42 at the extremes). Max |difference| by feature,
  2026-10-09 / 2026-10-08: ret1 0.52 / 0.91 bp, ret5 0.45 / 0.65, ret15 0.45 / 1.17, ret30 0.45 / 0.78, rng1–30 0.77 /
  0.52 bp, range_pos 0.032 / 0.041, or_pos 0.021 / 0.047, day_move_atr 0.005 / 0.008, day_range_atr 0.009 / 0.002,
  rv_session 0.26 / 0.12 bp, rel_vol 0.07 / 1.17 (a 4.41 → 5.58 burst minute), straddle_rel and implied30 ~1e-7 (the
  spot only), VIX features 0. **The decile agrees at 58 of 72 and 57 of 72 scan minutes (full model), 56 and 54
  (no-VIX)**; all but three disagreements are one decile apart (three are two apart: 2026-10-08 m 35, 40, 265); D1 changed at 2 minutes
  (full) and 2 (no-VIX) of the 144; **at candidate 3's minutes (13:00 … 15:00) the full-model decile agreed 10 of 10**
  (5→5, 4→4, 5→5, 5→5, 2→2 and 7→7, 6→6, 6→6, 8→8, 8→8).

### The 15:58 close quotes (fly5)

At **15:58** New York the tracker reads SPY's and QQQ's same-day chain once a name and writes a `close1558` row for
every fly5 structure logged that day (the iron, call and put flies of the 15:00 and the 15:30 captures): the four legs'
NBBO (`l*_bid_1558`, `l*_ask_1558`), the liquidation value at the NBBO (`liq_nbbo`, cash a unit: sell what was bought
at its bid, buy back what was sold at its ask) and at the mid (`liq_mid`), and the 15:58 exit P&L = (entry cash +
liquidation cash) × 100 − $2.60 to open − $0.65 a contract closed (`pnl_1558_nbbo`: the NBBO both ways;
`pnl_1558_mid`: the mid both ways). A long leg with no bid at 15:58 cannot be sold: it is left to expire (0 in both
values, no fee); a leg missing from the chain leaves the row without a value and says so (`close_reason`). The settle
rows carry the same figures beside the 16:00 intrinsic settlement (no fee at expiry). **Why**: an ETF option is
physically settled — a SPY or QQQ option in the money at the close is exercised or assigned in shares. A fly that
closes between its strikes leaves a long call exercised (100 shares bought, about $77,000 of SPY at ~773) and, past K0,
two short calls assigned (200 shares sold, a net short of 100) — positions a cash account cannot carry overnight; the
exit before 16:00 is the trade a cash account can actually make, so the forward record needs its price.

**The cash-settled SPXW equivalent** (`--spxw`, OFF by default): the owner asked for it only at zero extra calls, and
it is not — the tracker does not otherwise read SPX's chain at 15:00, 15:30 or 15:58. With `--spxw` it reads
`/api/stock/SPX/option-contracts?expiry=D` (both roots in one answer; the SPXW root alone is kept — a third Friday's AM
SPX contracts share the date) at 15:00 and 15:30 and builds the iron, call and put flies at ±5 and ±25 around K0.
**SPX's price**: UW Basic has none (stock-state 422; ohlc 422 `cboe_index_access_missing`), and `option-contracts`
rows carry no underlying price, so SPX at the capture is read off the same chain by **put-call parity** at r = q = 0
(same day): the median of K + call mid − put mid over the three strikes where |call mid − put mid| is smallest, both
bids > 0 (`spot_source`, `parity_strikes`). The settle (16:20) takes `price` from SPX's `/spot-exposures/strike`
(page 0; UW's own SPX figure — a proxy for the official 16:00 SET, labelled `settle_source=spx_book_price`). Cost:
**3–5 calls a session** (one chain page at each capture, two if the expiry's chain passes 500 contracts, and one at the
settle). Cash-settled, SPXW needs no 15:58 exit.

### The macro stamps

Every row — the recorder's and the tracker's — carries four columns from `scripts/macro_calendar.py`, which reads
`data/macro_events_2022_2027.json` (`MACRO_EVENTS` overrides the path; 231 releases 2022–2027: FOMC decisions and
minutes at 14:00, CPI and payrolls at 08:30; a release whose status says cancelled or postponed is left out):
`is_macro_event_day` ('true'/'false'), `macro_events` (the day's kinds in time order joined by '+', '' on a day with
none), `minutes_to_macro_release` (minutes from the row's time to the next release that New York day, 0 at the
release, **null once every release of the day is past**) and `minutes_since_last_release` (minutes since the latest
release of the day at or before the row's time, null before the first) — so a 13:00 capture on an FOMC day reads 60
and null, a 15:00 one null and 60. The recorder's scan rows read the minutes at their scan time, its EOD rows null; the
tracker's capture rows at their capture minute, a settle or 15:58 row its capture's (the trade's entry). Without the
file every field is null (unknown — never 'false') and one WARN line says so; the file is re-read when it changes. In
the recorder the four columns follow the vendor's and are never part of a row's key.

Where it writes: `data_recorder/paper/<candidate>/<NAME>/<YYYY-MM-DD>.parquet` (`PAPER_DATA` or `--data` moves the
root) — a `capture` row a structure a minute, a `close1558` row a fly5 structure a minute and a `settle` row a structure
a minute a settlement source, the recorder's six stamps first (`_scan` the minute, `close1558`, `settle`, or `smoke`),
every value a string, the dedupe on (`row_kind`, `minute`, `structure`, `settle_source`); markers under
`_markers/<candidate>/<NAME>/<day>/`, failures and the budget as the recorder's; the model's caches under `_cache/`.
**A second capture of the same minute makes no call and adds no row**; a partial (a failed call) is asked again.
`data_recorder/paper/smoke/` holds the live smoke capture of 2026-10-21 (`_scan` = `smoke`, taken at 16:56 ET on the
closing quotes: K0 773, straddle 0.83, shorts 775 and 772, both spreads under $0.05 — `tradable=false`); `--status`
reads the real root alone and never counts it. `--dry-run` writes under `data_recorder/paper/dryrun/`.

### The budget

A session's calls, the default candidates (`condor_em1`, `fly5`, `condor_d20`), recomputed for `.2`:

| | calls | note |
|---|---|---|
| captures: chain + stock-state | 11 name-minutes × 2 = **22** | SPY at 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 (9 × 2 = 18, candidate 3 sharing the 13:00, 13:30 and 15:00 reads) + QQQ at 15:00 and 15:30 (2 × 2 = 4) = 22 |
| candidate 3: today's bars | **5** | one `ohlc/1m` a capture minute (+1 when the minute's bar is not out yet: at most +5) |
| candidate 3: VIX | **1** | UW's VIX stock-state, once a session while it answers 422; Theta Data is not a UW call |
| candidate 3: the sessions before | **0** warm / **20** cold | the cache; the first day backfills 20 sessions once (19 tomorrow: the recorder's 2026-10-21 file is read free) |
| 15:58 close quotes | **2** | one chain a name |
| the settle | **6** | `ohlc/1m`, stock-state, `ohlc/1d` × SPY and QQQ (SPY's `ohlc/1m` also fills the cache) |
| **a session, warm** | **36** | the tests' second day: 36 exactly |
| **the first day, cold** | **56** | the tests' first day: 56 exactly |
| the worst | **61** | cold, every bar asked twice |
| `--spxw` | **+3 to +5** | |

The default `--budget` (`PAPER_BUDGET`) is **80**: the cold worst (61) with a fifth to spare, `--spxw` included (66).
It is counted per New York day in `_budget/<day>.json` across runs; at the budget a capture stops with the STOP line.
`--budget 22` still runs the old pair (`condor_em1` and `fly5` alone, 18 captures and 4 settle calls — the daily bar
left out and the official close read later off the next session's first stock-state `prev_close`, 773.09 both, checked
live 2026-10-21), but with candidate 3 on, 22 is short: the default is the number to run. `--backfill [--day D]` warms
the cache ahead (at most 20 calls, none for a day already kept) — run it once in the evening before the first live
session so the 13:00 capture does not spend them. The limiter is one call in flight, 30 a minute.

Modes:

```
python3 -I scripts/paper_tracker.py --log --when 11:30 [--day D]   # one capture (a scheduler's line); 11:30 12:00 12:30 13:00 13:30 14:00 14:30 15:00 15:30, and 15:58 (the close quotes)
python3 -I scripts/paper_tracker.py --settle [--day D] [--official] # the after-close pass; re-runnable
python3 -I scripts/paper_tracker.py --backfill [--day D]            # the model's 20 sessions before into the cache (once)
python3 -I scripts/paper_tracker.py --daemon [--spxw]               # sleeps to each minute, 15:58 and 16:20, Mon–Fri, holidays and half days skipped
python3 -I scripts/paper_tracker.py --status [--data …]             # sessions logged, mean P&L (NBBO, mid, 1c, 2c), the 15:58 exit, candidate 3 by decile, the check, what remains
python3 -I scripts/paper_tracker.py --dry-run --log --when 13:00    # the fixture chain, a fake Theta, no network
python3 -I scripts/paper_tracker.py --log --when 11:30 --smoke      # a live capture under <root>/smoke/, labelled smoke, never a session
python3 -I scripts/models/freeze_t2_spy.py                          # (once, done) refit and freeze the two t2 models; needs lightgbm
python3 -I scripts/models/parity/parity_t2_spy.py                   # the parity check (Theta's files on disk, the two saved UW answers)
```

Half days are skipped whole (the reports skipped them; a 13:00 close has no 13:30 or 15:00 minute). A daemon started
after 16:20 runs the day's settle pass; a capture minute it slept through is simply missing (a past minute's quotes
cannot be asked for) — the `--log` lines from cron are the belt and braces.

Keeping it running — **a second daemon beside the recorder**, my call: the two schedules do not overlap in a way worth
one process (the recorder's scans are on the half hour at :00 and :30; the tracker's minutes too, but the tracker must
hold its own one-in-flight budget and the recorder's budget must not pay for it), and a crash in one must not stop the
other.

- Windows, Task Scheduler: `scripts\paper_tracker.cmd`, a restart loop like `eod_recorder.cmd`, reading the SAME env
  file (`%USERPROFILE%\.eod_recorder\env` or `RECORDER_ENV`: `UW_API_TOKEN=…`, optionally `PAPER_DATA=…`,
  `PAPER_BUDGET=…`, `MACRO_EVENTS=…`); register it as a second task at startup. Its log: `<paper root>\tracker.cmd.log`.
  On the owner's machine the Theta Terminal answers on 127.0.0.1, so VIX comes from it and the full model's decile is
  the primary; a tracker on a machine without the terminal logs `vix_source=none` and the no-VIX decile.
- Linux, systemd: `scripts/paper_tracker.service` (`--daemon`, Restart=always, the same `EnvironmentFile` as the
  recorder) and `scripts/paper_tracker.timer` (boot, and weekdays 11:00 New York). Copy beside the recorder's units,
  then `systemctl daemon-reload && systemctl enable --now paper_tracker.timer paper_tracker.service`.
- cron, no daemon (`CRON_TZ=America/New_York`, the env file sourced): `30 11,12,13,14 * * 1-5` and
  `0 12,13,14,15 * * 1-5` and `30 15 * * 1-5` and `58 15 * * 1-5` → `python3 -I scripts/paper_tracker.py --log --when
  HH:MM` with the matching minute (one line a minute, ten lines), and `20 16 * * 1-5 … --settle`.

Tests: `python3 -I tests/test_paper_tracker.py` — twenty tests on the fixture chain, a fake Theta and a fake clock: the
two old strike rules land on the hand-set strikes (spot 773.40 → straddle 2.10 at 773 → shorts 776 and 771, longs 778
and 769, credit $0.30 at the NBBO and $0.355 at the mid; K0 773 ±5 → iron credit 1.88 / risk 3.12, call fly debit
3.27, put fly 3.30); the P&L on a known settlement (777.20: condor −$92.60 NBBO / −$87.10 mid; iron −$234.60; call fly
−$249.60; put fly −$252.60; at 773.00 the condor keeps $27.40); the old pair's session is 24 calls and a repeat
capture or settle makes none; the official close arriving later is added once; a tight budget takes it from the next
session's `prev_close`; a failed call is recorded and asked again; the schedule (weekends, holidays, half days, 15:58);
and since `.2`: the macro stamps on a fixture calendar (FOMC at 14:00 → 60 at 13:00, null and 60 at 15:00; CPI + minutes
→ 'CPI+FOMC_MINUTES', 60 and 270; a cancelled release left out) and a missing or broken calendar (null, one WARN);
candidate 3's rule on a chain priced at a known σ√τ (deltas against the closed form, 504 / 496) and its tie-break; the
frozen models load (hashes checked, a changed file refused) and score the fixture rows to LightGBM's deciles 1 … 10;
a candidate-3 capture (Theta's VIX → the full model primary; 24 calls cold at 13:00, 3 at 13:30, the VIX probe once;
the decile re-scored from the logged features) and one without VIX (the no-VIX decile primary, one WARN, a late bar
asked twice); the 15:58 liquidation on a known quote (iron −$133.55 NBBO / −$115.05 mid, a bidless long left to
expire; call fly −$167.20); a whole default session cold (56) then warm (36) under the default budget with the settle
carrying the 15:58 exit, the capture's stamps and deciles; `--spxw` (the SPXW root alone, parity spot, K0 3865 ±5 and
±25, the book-price settle, 1 + 1 calls); the token never in a line, a marker, a failure record, a cache file or a
Parquet cell, and no key in `vol_model.py` or `macro_calendar.py`. All passing on 2026-10-21.

## Settled by the smoke test (2026-10-21, the owner's token; `data_recorder/smoke/smoke_SPY.txt`, `smoke_SPX.txt`, the Parquet rows beside them, and seven follow-up probes the same evening)

Every route answered 200 for SPY and for SPX. What each point of the build's list came to:

1. **`flow-alerts` paging — settled.** `limit=200` is accepted (200 rows a page; SPY's page reached from 20:14Z back to
   19:43Z, so a day is several pages); `newer_than` and `older_than` are both honoured on `created_at` (the window
   [04:00Z, 13:00Z) of the day answered `[]`, not the session before's rows). The 100 fallback stays for a refusal.
   An index is filed under BOTH roots — SPX 174 rows and SPXW 200 (its page cap) — so both stay asked; the dedupe on
   `id` covers a row filed twice. Index rows carry one more field, `missing_periscope` ("true"), now a known column
   (`FLOW_ALERT_COLUMNS`); a stock's rows leave it null.
2. **`darkpool/{t}` paging — settled.** `limit=500` is accepted: the page of 500 held 490 distinct rows (ten exact
   duplicates; 446 `tracking_id`s — the key is `tracking_id` + `executed_at` + `price` + `size`, which is why). **`date=D`
   does NOT bound the rows**: `date=2026-10-21&older_than=2026-10-21T04:00:00Z` answered the session before's prints
   (23:59Z of the 20th), so the day is bounded by the recorder's own filter and the walk stops once a page's oldest
   row is before the day's start. One page spanned 19:58–20:33Z (35 minutes of SPY), so a day is 10–20 pages of 500,
   far under the cap of 250.
3. **`spot-exposures/strike` paging — settled: `page` is honoured.** SPY's book is 491 strikes in one page; SPX's
   page 0 answered 500 rows (strikes 200 → 7660) and page 1 the remaining 324 — 824 strikes, two pages, the walk
   stopping on the short page. The cap stays a generous 10 (5,000 strikes). `tests/test_eod_recorder.py` keeps the
   two-page case.
4. **An index — settled.** `/net-prem-ticks` answers for SPX (428 rows from 09:30 ET, the 13 fields); `/oi-per-strike`
   answers (548 strikes); `/option-contracts` answers under SPX with BOTH roots' contracts in one chain (`SPXW261021…`
   first — the heaviest volume — and `SPX261…` monthlies), 500 a page; the book answers under SPX (above). `darkpool`
   and `ohlc/1m` are not asked for an index, by design (no stock prints; bars are a CBOE grant).
5. **`ohlc/1m` `limit=1000` — settled.** 669 bars at 16:37 ET: 242 `pr` from 04:00, the 390 `r` of 09:30–15:59 and 37
   `po` so far; a whole day to 20:00 is about 870, under the limit. Every row is kept and stamped; `market_time` says
   which session. The 15:59 bar is the last regular one (its close 773.13 on the 21st; UW's daily bar put the
   official close at 773.09 — the closing print is not a minute bar's close).
6. **`option-contracts` page count — settled.** The eod walk asks `page` 0, 1, … and stops on the first page short of
   500 (`_walk_pages`); SPY's page 19 answered 125 rows — 9,625 contracts with open interest in 20 pages — so the cap
   of 40 is not near. The smoke's "500 / page cap 1" was the smoke's own one-page rule. The route also takes
   `expiry=YYYY-MM-DD` (SPY's 2026-10-21 chain: 302 contracts in one page, zero-OI strikes included), which the
   paper tracker uses.
7. **Rate ceilings** — unchanged: three in flight is measured; the 100-a-minute bucket and the 20,000 daily budget are
   the brief's (the smoke runs spent 26 calls in all).

8. **SPX's chain — settled by the first real EOD pass (2026-10-21, 627 calls, 0 failed).** SPX's `option-contracts`
   stopped at the 40-page cap: 20,000 rows (12,226 SPXW and 7,774 SPX; heaviest volume first, 9,866 rows with volume,
   then the open-interest tail, down to 3 contracts at the cut), marker `partial`. Since `.3` an index pages to
   `max_pages_index` = 150 (75,000 rows; a page costs a call only while the chain lasts — expected ~45–60 pages); a
   stock keeps 40. The partial marker means the next run asks SPX's chain again: a daemon (re)started the same New York
   day after 16:15 runs the EOD catch-up (`due_now`), skips every `done` job and refetches SPX's chain whole (the dedupe
   on `option_symbol` keeps the 20,000 rows once). The route has no date: re-asked after midnight New York it answers
   the NEXT day's chain, so a 2026-10-21 refetch is only right before then — after that, leave the day partial.

## Still unsettled

- **A full day's page counts** for `flow_alerts` and `darkpool` on a busy name (the smoke asked one page each): the
  caps (60 and 250) stand far above the extrapolation (5–10 and 10–20 pages); the first real `--eod` run's markers say
  the counts.
- **Holidays past 2027** and any early close other than the two listed: extend `HOLIDAYS` and `HALF_DAYS` each autumn.
- **Whether `newer_than` reaches further back than about 60 days** for a backfill of old days with `--day` (the echoed
  `newer_than` on 2026-10-12 sat two months back); not needed for the forward record.
