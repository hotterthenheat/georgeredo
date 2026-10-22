# `--fetch-theta` audit (2026-10-22)

`paper_tracker.py --fetch-theta` writes new sessions into the Parquet layout that `--backtest` replays. Until now it
had only been tested against a fake server. This file covers four things: the audit of every item the owner listed
against what has actually run live, the fixes (each with a regression test), the new `--verify-parquet` and
`--merge-parquet` modes, and the exact commands for the first live run on the owner's PC.

**What "has run live" means here.** Nothing in this audit called a Theta host. The references are:

- **The stored dataset itself**: `theta/data_full/chains`, `theta/data/underlying`, `theta/data/index` in the research
  scratchpad. It was built on 2026-10-13 with the `thetadata` Python SDK 1.0.14 over gRPC (`theta/ds/build.py` and its
  `fetch.py` twin, which ran with no strike band). The run's job log is `data_full/_jobs.jsonl`, and the SDK's live
  answer shapes are in `ds/probe/probe1.log`.
- **The Slayer Terminal's live v3 code**, which ran against the terminal on 2026-10-14:
  - `3abida/server/feed.ts`
  - `scripts/theta-history`
  - `scripts/theta-probe/lib.ts` (Theta's status table)
  - `docs/data-feed.md` "Theta Data"
- **ThetaData's v3 documentation** for `/option/history/quote`, `/stock/history/ohlc`, `/index/history/price` and
  `/calendar/on_date`, plus the v3 announcement: "There is no more next-page header / pagination".

## The audit

| # | Item | What `--fetch-theta` did | Reference | Verdict | Fix (test) |
|---|---|---|---|---|---|
| 1 | **Date boundaries** | Every weekday in `[start, end]`, inclusive. A day in `R.HOLIDAYS` was skipped. A day ≥ today was asked anyway. | The recorder's calendar (`eod_recorder.HOLIDAYS` / `HALF_DAYS`, carried from 2026). It agrees with the research calendar `calendar_2017_2026.csv`. 2026-10-12 (Columbus Day) is an equity and option session. | Inclusive and weekends were correct. A session not yet over could be fetched as a partial day. | `session_of(day)` returns full / half / holiday / weekend, or "unknown" before 2026. A day is asked only after 16:30 New York on it. A holiday is never asked; it is recorded in the manifest. (`test_the_fetch_waits_out_…`) |
| 2 | **Exchange calendar** | Not checked against Theta. | `GET /v3/calendar/on_date?date=` returns `open` / `full_close` / `early_close` / `weekend`. | Unverified. | Each day's type is asked once (a cheap call). If it disagrees with the recorder's calendar, that day is FAILED with no data call, and you fix `HOLIDAYS` first. Both words are kept in the manifest. (same test) |
| 3 | **A 472 / empty answer on a session** | A 472 or an empty 200 went into `empty`, the exit code was **0**, and nothing marked the day. A later replay then treated a weekday with no SPY file **as a holiday** (`install_calendar`). That is a silent empty session. | 3abida's proxy turns a 472 into "no rows". That is fine for a UI, but wrong for a dataset. | **Bug.** | A 472, an empty 200, a cut stream, an error, or an answer short of the norm on a calendar session is **FAILED / INCOMPLETE** in the manifest. Nothing is placed and the exit code is 1. From 2026 on, the replay's calendar is the recorder's: a missing SPY file is "missing files", never a holiday. A file its manifest refuses is read as absent, and the day says `refused`. (`test_a_session_without_data_is_failed_…`, `test_the_replay_reads_a_refused_file_as_absent_…`) |
| 4 | **Authentication** | No key is sent. Only `http://127.0.0.1` is used ("localhost" is refused). No proxy. | Theta 476 WRONG_IP for "localhost". The terminal holds the key. A second sign-in anywhere returns 478 INVALID_SESSION_ID. | Correct, but there was no pre-flight check and 478 did not stop the run. | `GET /v3/terminal/mdds/status` must answer `CONNECTED` before any data call, otherwise nothing is asked. 476, 478 and a refused connection **stop the run**: every later call is "not asked". The test checks that no `Authorization` header or key parameter is ever sent. (`test_the_theta_fetch_reproduces_…`, `test_theta_statuses_…`) |
| 5 | **Endpoint paths and params** | Chain: `/option/history/quote?symbol&expiration=D&date=D&interval=1m&start_time=09:30:00&end_time=16:00:00`. Bars: `/stock/history/ohlc?…start_date=D&end_date=D&venue=utp_cta`. Index: `/index/history/price?symbol&date=D&interval=1m`. All with `format=ndjson`. | v3 docs: `strike` defaults to `*`, `right` to both, both times are inclusive. The SDK calls that built the dataset were the same apart from the venue (item 6). | Correct, except the venue. | No change to the chain or index calls. They are pinned in the test. |
| 6 | **Stock venue** | `venue=utp_cta` (copied from the 3abida downloader). | The SDK that built `data/underlying` (1.0.14, installed 2026-10-13 19:42 UTC, before the build) sends **`venue='nqb'` by default**, and build.py passed no venue. v3's own default is also `nqb`. | **Discrepancy.** The bars set the replay's spot, its 15:59 settlement and candidate 3's relative volume against the 20 stored sessions before, so mixing venues would bias them. | The default is now **`nqb`**, recorded on every bar file's manifest entry. `--stock-venue utp_cta` is kept for the overlap check (step 2 below). A day's volume under a quarter of the stored norm is INCOMPLETE ("another venue?"). Supporting evidence: the stored SPY 2026-10-09 bars sum 18.5 M shares against UW's regular-session 19.4 M. That **cannot** say which venue the server actually served, so the overlap check decides. (`test_the_theta_fetch_reproduces_…` pins `nqb`; `test_the_answer_shape_…` covers the volume check) |
| 7 | **Pagination** | None handled. | The v3 announcement: "no more next-page header / pagination". The SDK answer streamed in 224 messages, not pages. | Correct for v3, but undefended. | A `Next-Page` header that is not `null` fails the answer (status 477); page 1 is never taken alone. (`test_theta_statuses_…`) |
| 8 | **Timestamps** | `"2026-10-09T09:30:00.000"` read as New York wall clock with no offset, giving `Datetime(ms, America/New_York)`. A stamp that failed to parse became null and was **silently dropped**. | 3abida `nyStampMs` (seen live). The stored files are `Datetime(ms, America/New_York)`, 391 minutes 09:30–16:00. v3: a quote "represents the last quote at the interval's timestamp" (the replay's "row stamped t is the quote at t"). A bar's stamp "represents the opening time of the bar" (the replay's "a bar stamped t closes at t+1"). An index price is "the price at the exact time". | Zone and convention correct. The silent drop was a bug. | A stamp that does not parse, a stamp not on a whole minute, a row of another day, a missing minute, or a minute outside 09:30–16:00 is reported, never dropped. (`test_the_answer_shape_…`) |
| 9 | **Quote fields** | `bid`, `ask`, `bid_size`, `ask_size` were read with a lenient parser. A field under another name (e.g. `bid_price`) would have become **null everywhere**, which silently substitutes "no quote". An unparseable size became 0. | The SDK's live answer (probe1.log): `symbol, expiration, strike, right, timestamp, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition`. The 09:30 no-quote row is NaN / NaN with sizes 0 (stored as null). The v3 docs list the same names. | **Bug** (silent substitution). | Every required field must be present in every row. A missing field or an unparseable number is FAILED. Nothing is ever filled in: a no-quote minute (0 / 0, sizes 0, or null) is null; a real 0 bid with an ask is kept; the mid is never invented (it is `(bid + ask) / 2` on the row, as the dataset has it); no trade price is ever used. (`test_the_answer_shape_…`) |
| 10 | **Symbol mapping** | `right`: anything not starting with C became **PUT**. Strike in dollars. | v3 docs: strike "in dollars"; right "call or put". SDK live: `"CALL"` / `"PUT"`, `strike: 533.0`. 3abida guards v2's thousandths (`> 100000 → /1000`). | **Bug** (silent PUT). The unit was unguarded. | Right must be one of C, CALL, P or PUT in any case; anything else is FAILED. Strikes far from the stored norm's median, or above 50,000 with no norm, are INCOMPLETE ("strike units?"). The OCC symbol the replay writes is unchanged (strike × 1000, 8 digits). (`test_the_answer_shape_…`) |
| 11 | **Expiration and roots** | `expiration=D`, the same day. SPXW asked as `SPXW` (the stored `data_full/chains/SPXW`). The `symbol` and `expiration` the rows carry were not read. | SDK live: `expiration` "2024-06-03" on every row, and `symbol` the root asked. | Correct asks, but the answers were unchecked. | A row whose expiration is not the day, or whose root is not the one asked (e.g. SPX monthlies inside SPXW), is FAILED. (`test_the_answer_shape_…`) |
| 12 | **Retries** | None. | 3abida's status table: 429 OS_LIMIT, 474 DISCONNECTED, 571 SERVER_STARTING, 572 UNCAUGHT_ERROR are transient. The SDK build saw `UNAVAILABLE: Stream removed (Socket closed)` on a 172 s SPXW day. | **Missing.** | 429, 474, 571, 572, a timeout and a cut stream (a non-JSON line, `IncompleteRead`) are asked again after 5, 15, 45 and 120 s, each plus up to 25 %. The cap is 5 attempts. 471, 473 and 570 fail at once; 476 and 478 stop the run. The timeout is 900 s (it was 300 s). The manifest records every attempt's status. (`test_theta_statuses_…`, `test_a_session_without_data_…`) |
| 13 | **Rate limits** | At most 3 in flight. | The Pro account allows 8 at once. The owner's recorder keeps one; the 3abida downloader takes 3 in the recorder's hours (06:00–17:00 ET) and 7 outside them. Nothing may be asked in Theta's gap (00:00–01:45 ET). | 3 was correct, but there was no gap rule and no way to lower it. | Still 3 by default. `--theta-in-flight 1` is for when `theta:history` runs outside its recorder hours (7 + 3 > 8, which would bring 429s; those are retried anyway). Inside Theta's gap nothing is asked, not even the status. (`test_the_fetch_waits_out_…`) |
| 14 | **Output schema** | Column names and dtypes as stored. | The stored files: chain `timestamp, strike, right, bid, ask, bid_size (i32), ask_size (i32), mid`, sorted by strike, right, timestamp. Bars `timestamp, open, high, low, close, volume (i64), count (i64), vwap`, with the 16:00 no-trade bar's prices null and its VWAP kept. Index `timestamp, price`, with SPX's 09:30 null. 391 minutes; every contract quoted every minute (rows = strikes × 2 × 391). | Correct. Now proven. | **Round trip**: a fake terminal answers the stored 2026-10-09 in v3's shape, and the seven fetched files are **equal** to the stored ones (schema, keys, every value). The replay's condor_em1 captures on the fetched day equal those on the stored day. (`test_the_theta_fetch_reproduces_…`) |
| 15 | **Overwrites, overlaps, duplicates** | An existing file was skipped; `--force` overwrote it in place. A duplicate row went straight in. | — | **Bug** (`--force` lost the original). | Every file is staged under `<root>/_staging/<run>/`, validated, and only then placed. An existing target is never touched without `--force`. `--force` keeps the old file beside the new one as `<name>.prev-<run>`; identical bytes are left alone. A duplicate `(timestamp, strike, right)` (or a duplicate timestamp) is INCOMPLETE. `--merge-parquet` checks every file first and copies **nothing** while any file fails or any target exists. (`test_merge_checks_everything_first_…`, `test_the_theta_fetch_reproduces_…`) |
| 16 | **Missing / short data** | Not measured. | The stored norms (2026, 80 sessions): strikes SPY 110–336 (median 173), QQQ 146–389, SPXW 238–644; 391 minutes; at most 2 crossed quotes a day; no unquoted row after 09:30. | Missing. | INCOMPLETE when any of these holds: a minute is missing; a minute holds under 99 % of the day's contracts; strikes or rows are under half the median of the 20 stored sessions before (floors 80 / 100 / 150 with no history); crossed quotes are over 0.5 %; unquoted rows after 09:30 are over 2 %; any negative value; under 98 % of bars priced (a holiday's padded file); no 15:59 close. (`test_the_answer_shape_…`, `test_verify_parquet_…`) |

## `--verify-parquet`

```
python3 -I scripts/paper_tracker.py --verify-parquet --start D1 --end D2 --parquet-root R [--only …] [--no-prior] [--compare-root REF] [--verify-json FILE]
```

For each New York weekday and each of the seven files, the check reports:

- whether a file is expected (the recorder's calendar, half days marked);
- whether it is present;
- what the manifest says about it;
- whether it is complete: the minutes for its root, the strike count against the stored norm, and NBBO sanity (bid ≤ ask, nothing negative, the share of crossed, unquoted and zero-bid rows);
- duplicates.

It also checks the sessions before that the replay reads: SPY's bars for the 20 sessions before (candidate 3) and VIX's and QQQ's for the session before. With `--compare-root`, every file found there is compared value for value. The exit code is 1 on any failure.

- **The stored 2026-10-05 → 09** (`theta/` in the research scratchpad): **PASS**. That covers 35 files plus the prior-session rows. SPY has 136,850–143,106 rows, 175–183 strikes, 391/391 minutes and 0–2 crossed quotes. QQQ has 177–206 strikes and SPXW 242–308.
- **A deliberately broken copy** (in a temp dir; the originals were not touched) **FAILs with exit 1** on every planted fault:
  - 30 minutes cut from a chain;
  - 500 duplicated rows;
  - a chain cut to a tenth of its strikes;
  - 2 % crossed quotes;
  - VIX deleted;
  - SPY's bars padded empty (the shape the stock route gives a day with no trades);
  - a prior session's SPY file deleted.

## The first live run, on the owner's PC (PowerShell)

Run it any time **outside 00:00–01:45 New York (23:00–00:45 Chicago)**, with the Theta Terminal already running and
signed in on the PC. Nothing here starts or signs into one. If `npm run theta:history` is running outside 6 am–5 pm
New York, add `--theta-in-flight 1` to the fetch lines.

```powershell
cd <the georgeredo clone>
git fetch origin; git checkout claude/lucid-heisenberg-bpyq7k; git pull
python -m pip install polars numpy tzdata
$env:PYTHONUTF8 = "1"
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:25503/v3/terminal/mdds/status).Content      # must print CONNECTED

# 1. The smallest live test: one route, one session, one call (plus the status and calendar calls)
python -I scripts\paper_tracker.py --fetch-theta --start 2026-10-12 --end 2026-10-12 --only SPY-underlying --parquet-root data\theta_forward --compare-root data\theta_reference
python -I scripts\paper_tracker.py --verify-parquet --start 2026-10-12 --end 2026-10-12 --only SPY-underlying --parquet-root data\theta_forward --no-prior --compare-root data\theta_reference

# 2. The live answers against the stored files: re-fetch the stored 2026-10-09 (7 calls) and compare value for value
#    with data\theta_reference (the stored 2026-10-09, copied into the repo). Every row must say `ok (equal to the reference)` and the run PASS.
python -I scripts\paper_tracker.py --fetch-theta --start 2026-10-09 --end 2026-10-09 --parquet-root data\theta_overlap --compare-root data\theta_reference
python -I scripts\paper_tracker.py --verify-parquet --start 2026-10-09 --end 2026-10-09 --parquet-root data\theta_overlap --no-prior --compare-root data\theta_reference --verify-json data\theta_overlap\_manifest\verify.json
#    ONLY IF the two underlying files differ: ask them on the other venue, compare, and stop here. Send the output; if
#    utp_cta is the one that equals, re-run step 1 with --force --stock-venue utp_cta before step 3.
python -I scripts\paper_tracker.py --fetch-theta --start 2026-10-09 --end 2026-10-09 --only SPY-underlying,QQQ-underlying --stock-venue utp_cta --parquet-root data\theta_overlap_utp
python -I scripts\paper_tracker.py --verify-parquet --start 2026-10-09 --end 2026-10-09 --only SPY-underlying,QQQ-underlying --parquet-root data\theta_overlap_utp --no-prior --compare-root data\theta_reference

# 3. The whole window: 8 sessions × 7 files = 56 calls (what step 1 placed is skipped)
python -I scripts\paper_tracker.py --fetch-theta --start 2026-10-12 --end 2026-10-21 --parquet-root data\theta_forward --compare-root data\theta_reference
python -I scripts\paper_tracker.py --verify-parquet --start 2026-10-12 --end 2026-10-21 --parquet-root data\theta_forward --no-prior --compare-root data\theta_reference --verify-json data\theta_forward\_manifest\verify_2026-10-12_2026-10-21.json
#    A FAILED / INCOMPLETE file is NOT placed (its staged copy and reason are under data\theta_forward\_staging and
#    _manifest). Run the same fetch line again later to retry just those; it never re-asks a placed file.

# 4. Into the repository (data/ is not git-ignored there; _staging is)
Get-ChildItem data\theta_forward, data\theta_overlap -Recurse -File -Exclude *.json | Measure-Object Length -Sum -Maximum
git add data/theta_forward data/theta_overlap
git status          # no _staging path may appear
git commit -m "Theta 2026-10-12..21 (and the 2026-10-09 overlap check) via --fetch-theta, verified"
git push origin claude/lucid-heisenberg-bpyq7k
```

Each fetch prints a JSON summary: `written`, `skipped`, `failed`, `incomplete`, the calendar answers, `calls` and `rc`.
Any `FAILED` / `INCOMPLETE` / `ABORTED` line goes to stderr with its reason, and the exit code is 1. Every request
(URL, HTTP status, each attempt's status, rows, bytes, seconds) is kept in `data\theta_forward\_manifest\<D>.json`.

**Expected size.** A session holds three chains (0.7–1.9 MB each in 2026; the stored 2026 maximum is 1.93 MB) plus
four tiny files of 3–12 KB. That is about **2.3 MB a session and about 18–25 MB for the 8 sessions**, plus 2.3 MB for
the overlap day. Every file stays far under the 50 MB limit. The fake-terminal rehearsal of the whole window (the
stored day's content served for each date) came to 18 MB.

**Back in the container** (the replay itself is the coordinator's):

```bash
git pull
TH=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta
python3 -I scripts/paper_tracker.py --verify-parquet --start 2026-10-09 --end 2026-10-09 --parquet-root data/theta_overlap --no-prior --compare-root $TH
# a combined root: links to the stored files (never changed) plus the new sessions
C=<scratchpad>/theta_combined
for d in data/underlying/SPY data/underlying/QQQ data/index/SPX data/index/VIX data_full/chains/SPY data_full/chains/QQQ data_full/chains/SPXW; do mkdir -p $C/$d; cp -s $TH/$d/*.parquet $C/$d/; done
python3 -I scripts/paper_tracker.py --merge-parquet data/theta_forward --parquet-root $C          # stops if anything overlaps
python3 -I scripts/paper_tracker.py --verify-parquet --start 2026-10-05 --end 2026-10-21 --parquet-root $C
```

The whole sequence (steps 1, 3, the merge into a linked copy of the stored root, a second merge stopped by the overlap,
and the combined verify of 2026-10-05 → 21 with the sessions before) was rehearsed through the CLI against the fake
terminal. Every step gave the expected exit code.

## What stays unverifiable until the live run

- **Which venue the server actually served for the stored bars.** The SDK sent `nqb`, but whether v3 serves Nasdaq Basic
  or the SIP for a past day is not documented. Step 2 settles it.
- **v3 REST against the gRPC SDK, value for value.** That covers the same quote at the same minute, and whether the
  09:30 no-quote row comes as 0 / 0 or null (both are read as null). Step 2 settles it for one session of each route.
- **Whether a no-trade bar on v3 carries zero prices** (3abida: "a minute with no print has no prices (0)") **or the
  last close.** The second case would show as a value difference on the 16:00 bar in step 2.
- **The exact status Theta gives a session with no data** (472, or an empty 200, or all-zero bars). All three are
  handled as failures.
- **The calendar route's answer shape** (`type` per the docs). If the call fails, the run carries on on the recorder's
  calendar and says so in the summary.

## The container route (the thetadata SDK, the stored files' own path)

The coordinator relayed the owner's go-ahead to sign in from the container instead (which signs the PC terminal out).
The permission system refused the sign-in from a relayed message, so **no Theta call was made**. A wrapper is ready
for when the owner approves it directly. It is `sdk_fetch.py` in this session's scratchpad. It makes the same SDK calls
and frame shaping as `build.py` / `fetch.py` (no band, the SDK's default venue), uses one login and one request in
flight, keeps the key in the environment only and redacts it, writes to a staging root, then validates, verifies, merges
(it stops on any overlap) and runs the final verify. Its shaping was checked offline: SDK-shaped frames rebuilt from the
stored 2026-10-09 come out equal to the stored files. Steps: `smallest`, `all`, `verify`, `merge`, `final`.
