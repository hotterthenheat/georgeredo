# Edge search — the queue, fixed before any of its results (2026-10-22)

The owner (2026-10-22): "self prompt until you come to the final and you have a edge that works, a actual strat".
This file fixes the order and the rules of that search before any queued hypothesis is computed.

## Rules for every entry
1. A PREREG file committed alone, before any result of that hypothesis is computed.
2. Tested once, on data it was not built on: the exploration/holdout split stated in its prereg, using unopened data where
   it exists (the 1,600 single names 2019-04 → 2022-12 drawn in research_notes/Compass direction/PREREG_DIRECTION.md;
   sessions after 2025-10-13 for SPY/QQQ; forward sessions from 2026-10-22).
3. Costs at least as strict as the repo's: buy at the ask, sell at the bid for options; a stated per-share auction or
   spread cost for stock; fees as PREREG_PICKER.md / PREREG_FEATURES.md.
4. Pass: mean $ per trade after costs > 0 with the 20-session block-bootstrap interval clear of zero, per name or per
   pre-stated pool; no variants after the result.
5. Every entry, pass or fail, is added to LEDGER.md with its commit hashes. The ledger's count of hypotheses tested is
   reported beside any pass (expected false passes at 5% ≈ 0.05 × count; a pass is called an EDGE only if it also clears a
   Bonferroni level across the ledger, or is confirmed on forward sessions under a FORWARD rule committed before them).
6. "An edge that works" = passes its holdout AND is put into the daily forward job under a pre-committed N rule. No
   verdict of "works" before that forward N.

## Order (highest prior first; each starts when the one before it reports)
1. H1 — overnight reversal of the late-day move, SPY/QQQ stock (running; research_notes/Compass H1/).
2. H3 — earnings implied-volatility crush: a defined-risk short iron condor (wings 1 implied move out) entered at the
   close before a report, exited at the close of the reaction session, single names; exploration on the 1,601-name
   2019–2022 exploration set, holdout the 1,600 unopened names (their option EOD fetched only if the screen passes).
3. H4 — intraday momentum (first half-hour return predicts the last half-hour, Gao, Han, Li & Zhou 2018), SPY/QQQ stock,
   on sessions 2025-10-13 → today plus forward (S12 already read 2017–2025 on QQQ: those sessions are exploration only).
4. H5 — the SPY/QQQ late-day extrinsic premium over SPXW (measured in research_notes/Compass phase 3/spxw_prereg/):
   sell the SPY/QQQ 15:30 at-the-money straddle and buy the SPXW one in matched notional, flat 15:58 — only if a cash
   account's assignment can be avoided by the 15:58 exit; forward-only test (the historical read is spent).
5. H6 — volatility risk premium at 30–45 DTE: monthly short put spreads on SPY/QQQ (S17 read 2012–2026 put-writing and
   covered calls: forward-only).
Anything added later goes to the end of the queue with its reason, never ahead of an untested entry.

## Additions (2026-10-23, after H1, H3 and H4 failed and H5/H6 went forward-only; appended before any of these is computed)
Reason: the queue's historical tests are exhausted with no pass. These are calendar effects with long published records on
the index itself, cheap to trade in stock, and not read by any study in this repo (each prereg must confirm that).
7. H7 — pre-FOMC drift (Lucca & Moench 2015): long 100 shares SPY / QQQ from the close two sessions before... exactly as its
   prereg states (the published window: the 24 hours before the 2:00 pm announcement), scheduled FOMC dates only.
8. H8 — turn of the month (Ariel 1987; Lakonishok & Smidt 1988; McConnell & Xu 2008): long 100 shares SPY / QQQ from the close
   of the last trading day before month end... exactly as its prereg states (the published window: the last trading day
   through the third trading day of the new month).
9. H9 — overnight drift (Cliff, Cooper & Gulen 2008; Kelly & Clark 2011): long 100 shares SPY / QQQ every close → next
   open. H1 already read its components (longs and shorts at the close → open), so H9 is FORWARD-ONLY from 2026-10-23.
