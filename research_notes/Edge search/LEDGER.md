# Edge search — ledger (every hypothesis tested, pass or fail)

Rules: research_notes/Edge search/QUEUE.md (a49c35b). Count of hypotheses tested so far is the number of rows below.

| # | Hypothesis | Prereg | Result commit | Data (exploration / holdout) | Result (mean $ a trade after costs [block-20 95%]) | Verdict |
|---|---|---|---|---|---|---|
| 1 | H1 overnight reversal, SPY/QQQ stock: short 100 at the official close if close > 15:00 price, long if below; exit next 09:30 open; $0.01/share each way | 38aca66 | 4a02144 | single test, QQQ 2012-06 → 2025-10-10, SPY 2017-01 → 2025-10-10 | SPY +11.09 [−4.42, +28.72]; QQQ +9.42 [−0.06, +18.61]; at 2× SPY +9.09, QQQ +7.42, both intervals across zero. Longs carry the mean (overnight drift), shorts lose. | FAIL |
| 2 | H3 earnings IV crush, single names: short iron condor (shorts at K0 ± 0.5 IM, longs ± 1.5 IM, first expiry after R within 14 days) sold at the closing quote before the report, bought back at the reaction session's close; bid/ask both ways, $0.68748 a contract each way | 001a136 | 34c8fd8 | exploration: 1,601 X names, reports with P and R in 2019-04 → 2022-12 (2,209 trades); holdout (1,600 H names) not fetched, not read | −161.54 [−180.68, −142.46] a condor (−30.2 % of max risk), negative every year; at the mid (exploratory) −$20, the rest spreads and fees | FAIL (screen); no pass, so no Bonferroni level is reached (m = 2; also fails at m = 7) |

Prior programme results (before this ledger, all pre-registered, all failed or were dropped): the 0DTE picker rule (c502122), the SPXW analogues (2820bb4), the 23-feature study's direction family (a2e14e4), post-earnings drift in options (38b11bf); the after-hours rule dropped fly5 iron and condor_d20 as SPY/QQQ hold-to-expiry strategies (633fbff).
