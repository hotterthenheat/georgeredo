# T-B methodology: gamma-conditioned last-half-hour momentum (pre-registered, plan §5)

Pre-registration: `COMPASS_RESEARCH_PLAN.md` §5 T-B. Design follows Baltussen, Da, Lammers and Martens (2021), "Hedging demand and market intraday momentum", *Journal of Financial Economics*: the last-half-hour return is regressed on the rest-of-day return, and the effect is expected to be concentrated on days when option dealers are short gamma. Nothing was tuned after seeing results; every variant below was fixed before the data were pulled.

## Data

| Series | Source | Request | Notes |
|---|---|---|---|
| SPX 1-minute prices | ThetaData PRO, `index_history_price(symbol='SPX', interval='1m', start_date, end_date)` | monthly chunks 2017-06-01..2026-10-09 (bulk requests are capped at one month) | row at `HH:MM` = index value at `HH:MM:00` (verified against the 1-second series on 2026-03-02); the 09:30 row is a NaN placeholder, so the "open" is the first non-NaN print (09:31 on every valid day) |
| VIX 1-minute | same endpoint, `symbol='VIX'` | monthly | VIX at 15:30 on day T is the robustness regressor |
| SPY 1-minute OHLC | `stock_history_ohlc(symbol='SPY', interval='1m', venue='nqb')` | monthly | bars are stamped at their start; the 15:29 bar close is the last trade before 15:30:00; `nqb` and `utp_cta` returned identical bars on the day checked |
| SPX / SPY end-of-day | `index_history_eod`, `stock_history_eod` | monthly | official open/close (SPY close = closing auction, which is where a market-on-close exit fills) |
| Trading calendar | ThetaData `calendar_year(2017..2026)` | early closes (13:00) excluded; SPX returns a flat, stale price after 13:00 on those days |
| Dealer-gamma sign | Unusual Whales `stock/{SPY,SPX}/gex-levels?date=T-1` (`backtest/data.py` cache format) | every weekday 2023-11-01..2026-10-09 | `gamma_flip` of the prior session; the endpoint returns HTTP 403 before 2023-11-13 and a null `gamma_flip` before 2024-05-13 (see `tb_gex_availability.csv`); nulls after that date fall only on market holidays |

Cache: every ThetaData response is stored as gzip CSV under `$SP/theta/cache/index_tests/` keyed by method and parameters (`code/td_cache.py`); every Unusual Whales response in the shared `BT_CACHE` directory. Nothing is refetched. The ThetaData key is read from the environment only, never written to any file or log; exception text is redacted (`td1_prod_...`).

## Definitions (all computed in `analyze_tb.py`, bp = 1e-4)

* `r_ROD` = P(15:30) / P(open) − 1. SPX: 15:30:00 index value over the 09:31:00 value. SPY: close of the 15:29 bar over the 09:30 bar open.
* `r_last30` = P(16:00) / P(15:30) − 1. SPX: 16:00:00 value (index version, cost-free). SPY: official close over the 15:29-bar close (main), variants: 15:59-bar close exit; entry at the 15:30-bar close (one-minute delay).
* Strategy return = sign(`r_ROD`) × `r_last30`; SPY net return subtracts 2 × 0.2 bp (round trip) on every traded day; days with `r_ROD` = 0 are not traded.
* 15:45 variant: signal from P(15:45)/P(open), position 15:45 → close.
* Gamma regime for day T: `neg` if close(T−1) < gamma_flip(T−1), `pos` if above, `unknown` otherwise (missing level, or no gex-levels history). SPY proxy uses the SPY official close against the SPY gamma_flip; SPX proxy uses the SPX official close against the SPX gamma_flip. Both levels are stamped on T−1 (the `time` field is logged and checked to fall on T−1), so the regime is known before day T opens.
* VIX split (robustness, no gamma data needed): VIX at 15:30 on day T above/below the sample median, and above/below 20.

## Statistics

* Per regime (neg / pos / unknown / all) and per gamma proxy: n days, mean (bp), t-statistic (one observation per day, so the day-clustered standard error equals the plain one), annualized Sharpe = mean / sd × √252, hit rate, by year; 95 % confidence intervals for the mean and the Sharpe by bootstrap over days (5,000 draws, seed 7).
* Regression `r_last30 = a + β r_ROD + e` per regime, β reported ×100 with an HC1 (White) 95 % interval and a bootstrap interval, next to the Baltussen et al. priors (β×100 ≈ 6.6 on negative-gamma days vs 0.8 on positive-gamma days).
* Pass criterion (plan §5, fixed in advance): SPY net Sharpe > 1.0 on negative-gamma days with ≥ 300 such days, and no effect on positive-gamma days (operationalized as: the positive-day mean interval covers zero and |Sharpe| < 0.5). The verdict is given for both gamma proxies.

## Reproduce

```
export TD_CACHE=$SP/theta/cache/index_tests CAL_FILE=$TD_CACHE/calendar_2017_2026.csv TC_OUT=$SP/theta/tc UW_OUT=$SP/theta/uw_gex_levels_daily.csv BT_CACHE=$SP/bt/cache
set -a; . $SP/secrets/research.env; set +a        # THETADATA_KEY, UW_API_TOKEN (never printed)
python3 -I code/fetch_uw_gex.py                     # gex-levels, SPY and SPX, 3 concurrent
python3 -I code/fetch_all.py                        # one ThetaData session (the server allows one login per key), 2 worker threads
UW_GEX_CSV=$UW_OUT OUT_DIR=tb_momentum python3 -I tb_momentum/analyze_tb.py
```
Outputs: `tb_daily.csv` (one row per session with every price, return, regime and stamp used), `tb_summary.csv`, `tb_regression.csv`, `tb_by_year.csv`, `tb_gate.csv`, `tb_gex_availability.csv`, `RESULTS.md` (generated).
