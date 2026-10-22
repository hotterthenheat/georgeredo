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
