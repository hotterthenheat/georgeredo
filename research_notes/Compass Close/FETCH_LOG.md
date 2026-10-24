# Compass Close — the fetch (2026-10-23 20:32–20:44 New York, after the prereg 1ce2039)

- Path: thetadata SDK 1.0.14 (gRPC), the daily job's `--source sdk` login; key loaded in-process from the scratchpad's
  secrets file, never printed. **Two logins, not one**: the first run logged in, read Theta's SPXW expiration list and
  asked one session (2017-06-02), then stopped on a bug in this script's SPX filter before writing anything; the fixed
  script ran again under a second login (a run of its own: the expiration list, a smoke session, the rest). No other
  login ran in that hour; no UNAUTHENTICATED answer was seen.
- Clock: 20:32–20:44 New York, outside 00:00–01:45 and 19:40–20:30 (checked before every request by the script).
- Requests: 2 expiration lists + 471 `option_history_quote` (one a session; 2017-06-02 twice), 3 in flight.
  Answers: **470 of 470 sessions OK; 0 empty, 0 denied, 0 failed** (`_fetch_log.jsonl`). 1774 s of request time,
  median 3.5 s, max 13.3 s.
- Theta's SPXW expiration list (2285 dates) lists every one of the 470 sessions.
- Every answer is root SPXW (PM-settled), expiration = the session's date, stamps 15:45 … 16:00 (16 a contract); no AM SPX
  root. `fetch_close.py verify`: 470 of 470 pass (same-day SPXW, one date, a 15:55 stamp, kept strikes bracket every
  SPX print 15:45–16:00).
- Rows: 3,062,512 answered, 160,096 kept; listed strikes a session median 192 (min 97, max 467),
  kept median 10 (min 9, max 30). Disk: 5.8 MB under
  `theta/data_full/chains_close/SPXW/` (scratchpad, not committed): `<D>.parquet` (timestamp, strike, right, bid, ask,
  sizes) and `<D>.meta.json` (the request, every listed strike, roots, expirations, stamps).
