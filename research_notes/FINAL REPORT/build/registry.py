"""registry.py — every strategy section of the final report: what the study pre-registered, where its trades come from,
and the opening pages. The words are the studies' own (their preregs, reports and commit messages); the numbers in the
metrics tables are recomputed by build.py from the trade-level files, never copied."""
from __future__ import annotations

import json
import math
from pathlib import Path

import polars as pl

import loaders_compass as LC
import loaders_old as LO
import loaders_recent as LR
import metrics as M
from base import RN, Strategy

F_ETF = '$0.68748 a contract each way (SPY, QQQ, IWM: $0.65 commission + $0.03748 pass-throughs), nothing at expiry'
F_SPXW = 'SPXW $1.18748 a contract each way under $1 of premium, $1.27748 at $1 and up (commission, Cboe fee, SPXW surcharge, ORF, OCC)'
F_065 = '$0.65 a contract (leg) to open, nothing at expiry'
ASK_BID = 'bought at the ask, sold at the bid of the 1-minute NBBO (ThetaData)'

STRATEGIES: list[Strategy] = []


def add(**kw):
    STRATEGIES.append(Strategy(**kw))


# =======================================================================================================================================
# A. Before the fresh start (75c29c9): read from 7dfea57
# =======================================================================================================================================

add(sid='1', group='A', vendor=True, name='GeorgeFi vendor cards (the vendor\'s own recorded P&L)',
    folder='evidence/public_api/, research/georgefi_full_history/normalized/ (@7dfea57)', commits='— / errata 5ed66df / cf555c9',
    dates='2026-10-13', unit='premium',
    hypothesis='GeorgeFi\'s published 0DTE and swing calls carry a positive return.',
    rule='The vendor\'s own cards: ticker, contract, entry and exit premium, size and P&L as GeorgeFi recorded them (books v2.0.0-ict, trade_now_v1, singles_today_v1, spx_plan_v1).',
    costs='The vendor\'s recorded fills; no fee or spread applied by us.',
    data='1,149 closed cards, 2026-01-20 → 2026-10-13 (Epoch 1 2026-01-20 → 02-27; Epoch 2 from 2026-03-02).',
    periods='Epoch 1 / Epoch 2, descriptive. No holdout.',
    pass_rule='None (descriptive). The grade check of the picker test (#29) reads the same cards.',
    verdict='Not evidence: re-priced at the NBBO (#4) Epoch 1 falls from +$43,248 recorded to +$12,039 executable and Epoch 2 from −$3,757 to −$24,988 (G1).',
    integrity='pnl_reported is used as recorded; 24 cards carry a data_error flag and are kept, as the vendor kept them.',
    finding='The vendor\'s record is positive in Epoch 1 and near zero in Epoch 2; the same rows re-priced at the market\'s quotes are a loss in Epoch 2 (#4).',
    load=LO.vendor_cards, verdict_period='Epoch 2', period_order=['Epoch 1', 'Epoch 2'], pooled=True,
    summary_slices=[('all names', 'Epoch 1'), ('all names', 'Epoch 2')])

REB = 'sweep|ict+gex|all|none|ladder'  # the variant key in trades.csv.gz
REB_BEST = 'sweep|ict+gex|morning|posgamma_fade|trail'
add(sid='2', group='A', name='George rebuild: the GeorgeFi-like reference (sweep / ict+gex / all / none / ladder)',
    folder='backtest/, BACKTEST_RESULTS.md (@7dfea57)', commits='— / — / 8f5b067', dates='2026-10-13', unit='premium',
    hypothesis='A level-sweep reversal into the nearest-strike 0DTE contract, managed by GeorgeFi\'s ladder, makes money after costs.',
    rule='Levels PDH/PDL, PWH/PWL, PMH/PML, ORH/ORL and the prior-day call/put walls; a sweep within the last 3 bars closed back inside by max(0.25 ATR14, 0.02%) → buy the nearest-strike 0DTE call (low swept) or put (high swept) at the next bar\'s VWAP; ladder exit: stop −25%, T1 +25% half, T2 +45%, breakeven lock at +6%, trail at 65% of the high-water mark from +15%, 30-minute time stop, flat 15:55.',
    costs='The "spread" model: a half-spread of 1% (SPY, QQQ) or 2% (IWM) of premium each side plus $0.70 a contract each side; one contract. (Unusual Whales 1-minute bars, no NBBO.)',
    data='SPY, QQQ, IWM 0DTE, 345 sessions 2025-06-02 → 2026-10-09 (SPX excluded: no index bars on the plan).',
    periods='In-sample < 2026-03-02, out-of-sample 2026-03-02 → 2026-10-09 (read). No holdout.',
    pass_rule='None pre-registered (an exploratory grid of 144 variants).',
    verdict='Rejected: 0 of 144 variants positive after costs (registry H1).',
    baseline='random-time entries, same contract choice and ladder (9,896 trades): −$3.20 a trade [−3.70, −2.70] under the spread model; the reference is −$3.44 [−4.23, −2.70]. No percentile was computed.',
    integrity='Reproduced byte for byte by the phase 1 audit (#3): trades.csv sha256 0e8c41c819e74eb0… on both runs.',
    finding='The reference variant loses $3.44 a trade, no better than random entry times with the same exits.',
    load=lambda: LO.rebuild(REB), period_order=['in-sample 2025-06→2026-02', 'out-of-sample 2026-03→10'], verdict_period='out-of-sample 2026-03→10')

add(sid='2b', group='A', name='George rebuild: the best of 144 variants (sweep / ict+gex / morning / posgamma_fade / trail)',
    folder='backtest/ (@7dfea57)', commits='— / — / 8f5b067', dates='2026-10-13', unit='premium',
    hypothesis='The best-ranked of the 144 variants (selected in sample) holds out of sample.',
    rule='As #2 but 10:00–12:00 only, sweep reversals only when spot is above the prior-day gamma flip, and the trail engine (no profit targets).',
    costs='As #2 (spread model).', data='As #2.', periods='As #2.', pass_rule='None pre-registered.',
    verdict='Rejected: −$2.41 a trade [−4.10, −0.47]; out of sample −$1.8 [−4.5, +0.9].',
    baseline='random-time baseline −$3.20 a trade (as #2); the best variant beats it by about $0.8, inside its interval.',
    integrity='Selected as the best of 144 on the full sample (a selection effect the numbers include).',
    finding='Even the best of 144 variants loses after costs.',
    load=lambda: LO.rebuild(REB_BEST), period_order=['in-sample 2025-06→2026-02', 'out-of-sample 2026-03→10'], verdict_period='out-of-sample 2026-03→10')

add(sid='3', group='A', name='George engine audit: the phase 1 reproduction audit of #1–#2',
    folder='audit/phase1/ (@7dfea57)', commits='— / — / 5ed66df (+ e95177c deterministic T5 rerun)', dates='2026-10-13',
    hypothesis='The rebuild (#2) and the GeorgeFi validation tests T1–T7 reproduce from their artifacts.',
    rule='Rerun of backtest/run.py and the validation scripts; byte comparison of outputs.', costs='—', data='As #2.', periods='—',
    pass_rule='Reproduction (no trading rule).', verdict='Reproduced: the regenerated trades and baseline files are byte-identical once decompressed.',
    na='not available — the audit produced no trades of its own; its trade files are #2\'s, byte for byte (see #2).',
    integrity='Fixes the audit motivated were added, never overwritten (trading-days path, signals.json, deterministic T5 iteration).',
    finding='The rebuild is deterministic and reproducible; no new strategy was tested.')

add(sid='4', group='A', name='GeorgeFi\'s own trades re-priced at the NBBO (G1)',
    folder='research/georgefi_full_history/results/F_nbbo_*.csv (@7dfea57)', commits='— / — / c27ff28', dates='2026-10-13', unit='premium',
    hypothesis='The vendor\'s recorded trades were executable at the prices it recorded.',
    rule='Each card\'s own entry and exit second, filled at ThetaData\'s NBBO (ask in, bid out), the card\'s own size.',
    costs='NBBO at the reported second; no fee added.',
    data='1,220 cards with both sides quoted, 2026-01-20 → 2026-10-13, every root the vendor traded.',
    periods='ledger Epoch 1, ledger Epoch 2, paper book. Descriptive.',
    pass_rule='None (an execution check).',
    verdict='Not supported after execution: Epoch 1 +$22.2 a trade [day CI −11.2, +66.2], Epoch 2 −$42.1 [−78.8, −9.6], paper −$73.9 (registry G1); 58% of Epoch 1 rows filled better than the market.',
    integrity='Cards with a side unquoted, and the stock rows, are left out (as F_nbbo_trades.csv flags them).',
    finding='At the market\'s own quotes the vendor\'s live epoch loses $42 a trade.',
    load=LO.georgefi_nbbo, period_order=['ledger E1', 'ledger E2', 'paper book'], verdict_period='ledger E2', pooled=False)

add(sid='4b', group='A', name='GeorgeFi entries with the trail engine (reconstruction C, G2)',
    folder='research/georgefi_full_history/results/C_trades.csv (@7dfea57)', commits='— / — / 5ed66df', dates='2026-10-13', unit='premium',
    hypothesis='GeorgeFi\'s entry minutes carry timing information when managed by a fixed trail engine.',
    rule='The vendor\'s entry minute, the reconstructed contract, entry at the bar VWAP, the paper-lane trail engine.',
    costs='Spread model of #2 (half-spread + $0.70 a side).', data='972 reconstructed trades, 2026-01 → 2026-10.',
    periods='ledger Epoch 1 / Epoch 2 / paper.', pass_rule='None (descriptive).',
    verdict='No robust entry timing: Epoch 1 +$5.8 a contract [−5.7, +16.3], Epoch 2 +$2.3 [−10.5, +14.9]; MFE percentile against time-matched random minutes 53 and 48 (G2).',
    baseline='time-matched random minutes, trail engine: MFE percentile 53 [47.5, 59.2] (Epoch 1) and 48 (Epoch 2).',
    integrity='—', finding='The entries are as good as random minutes once the exit is fixed.',
    load=LO.georgefi_reconstructed, period_order=['ledger E1', 'ledger E2', 'paper book'], verdict_period='ledger E2', pooled=True)

add(sid='5', group='A', name='Deep research round 1: flow rule F1 on SPY (H2 family)',
    folder='research/flow_predictors/ (@7dfea57); report "Finding a 0DTE options edge"', commits='— / — / 96a2c09…fb4205f, 5208c8f',
    dates='2026-10-13', unit='premium',
    hypothesis='Options-flow imbalances (net premium, net delta, market tide, dark pool) lead the underlying.',
    rule='F1: the flow predictor\'s signal minute on SPY → buy the 0DTE contract in its direction, trail engine (as #4b).',
    costs='Spread model of #2 (1% half-spread + $0.70 a side), entry at the VWAP of the first option bar after the signal.', data='SPY, Unusual Whales flow and bars 2025-07-01 → 2026-10-09; F1 = 15-minute net premium against its trailing-20-session 20th/80th percentiles, every 5 minutes 09:45–15:00, at most 2 a day.',
    periods='One span (descriptive test 5).', baseline='random minutes matched per day, random side, same exits and costs (574 trades): −$3.34 a trade, −2.26% (the rule −$4.12, −2.38%).',
    pass_rule='Multiple-testing correction across 62 cells (exploratory).',
    verdict='Rejected: 0 of 62 cells survive correction; forward ICs ≤ 0.02 (registry H2). The other round-1 notes (GEX regime and exit grid of 576 configurations, short-vol session T1–T5) kept results by configuration only; their verdicts: H4 rejected, H6 rejected, H7 0 of 576 exit configurations positive (White p = 1), H8 every option expression negative.',
    integrity='—', finding='The one flow rule with a trade list loses after costs.',
    load=LO.flow_f1, pooled=False)

add(sid='6a', group='A', name='T-A: the 13:00 short ATM 0DTE straddle, SPY/QQQ/IWM, bought back 15:55 (H9)',
    folder='research/thetadata/straddle_nbbo/ (@7dfea57)', commits='— / gate v2 924aee9 / ebde6ae', dates='2026-10-13', unit='credit',
    hypothesis='Selling the 13:00 at-the-money straddle harvests intraday variance premium after measured costs.',
    rule='Sell the same-day ATM straddle at the 13:00 bids, buy it back at the 15:55 asks.',
    costs='Measured ThetaData NBBO both ways (the round trip $12.93 a SPY/QQQ straddle); return as % of the credit received.',
    data='SPY, QQQ, IWM 0DTE, 339 sessions each, 2025-06-02 → 2026-10-09.', periods='One span; no holdout ("previously analysed").',
    pass_rule='Gate v2: a positive lower bound at measured NBBO (T-A).',
    verdict='FAIL: +$8.60 a straddle [−6.07, +22.45] SPY/QQQ (n 678); IWM −$9.50 [−18.69, −0.44].',
    baseline='random entry times: +$13.10 [−2.42, +29.14] against a $12.93 round trip (registry H9).',
    integrity='The modelled-spread result (+$8.36) was optimistic by about $5 a straddle.',
    finding='The 13:00 short straddle is positive on SPY/QQQ with an interval through zero and negative on IWM.',
    load=LO.lane_ta)
add(sid='6b', group='A', name='T-B: gamma-conditioned last-30-minute momentum in SPY shares (H10)',
    folder='research/thetadata/index_tests/tb_momentum/ (@7dfea57)', commits='— / — / b209f7b', dates='2026-10-13', unit='stock',
    hypothesis='On negative-gamma days the last 30 minutes continue the session\'s move.',
    rule='On days with dealer gamma below the flip (prior-day UW levels): 100 SPY in the direction of the open→15:30 move, 15:30 → official close.',
    costs='Net of the study\'s cost per day (0.4 bp).', data='SPY, 299 negative-gamma days 2024-05-14 → 2026-10-07.',
    periods='One span.', pass_rule='T-B: positive mean with a positive lower bound.',
    verdict='FAIL (wrong sign): −3.07 bp a day [−5.73, −0.52], Sharpe −2.15.',
    integrity='The two gamma proxies agree on the regime 52% of days.', finding='The effect has the wrong sign.',
    load=LO.lane_tb)
add(sid='6c', group='A', name='T-C: the 13:00 SPXW short straddle bought back 15:55 (H11)',
    folder='research/thetadata/index_tests/tc_spxw_straddle/ (@7dfea57)', commits='— / — / b209f7b', dates='2026-10-13', unit='credit',
    hypothesis='As T-A on SPXW (cash-settled).', rule='Sell the SPXW ATM straddle at 13:00 (bids), buy back at 15:55 (asks).',
    costs='Measured NBBO; return as % of the credit.', data='SPXW 0DTE, 339 sessions 2025-06-02 → 2026-10-09.', periods='One span.',
    pass_rule='T-C: positive lower bound.', verdict='FAIL: +$72.4 a day [−75.8, +214.2], max drawdown −$21,180, worst day −$8,499.',
    baseline='random entry: +$40.6 [−73.4, +164.2] against a $68.9 cost.', integrity='—',
    finding='Positive mean, interval through zero, large tail days.', load=LO.lane_tc)
add(sid='6d', group='A', name='T-E: the 13:00 SPXW ATM straddle held to PM settlement, ex FOMC/CPI/NFP (H13)',
    folder='research/thetadata/hwr_grid/spxw_v2/ (@7dfea57)', commits='protocol sha256 in protocol_sha256.txt / — / 01ee3f3, 5f253c6 (full chains)', dates='2026-10-14', unit='credit',
    hypothesis='Holding the short straddle to cash settlement adds the last hour\'s decay.',
    rule='Sell the SPXW ATM straddle at 13:00, hold to the PM settlement (Cboe close), skip FOMC/CPI/NFP days.',
    costs='Measured NBBO in; settlement value out.', data='SPXW 0DTE 2022-05-13 → 2026-10-09 on complete chains.',
    periods='TRAIN 2022-05→2024 / TEST 2025→2026-10 (TEST read).', pass_rule='T-E gate on TEST.',
    verdict='FAIL: +$26.94 a day [−136.73, +170.75]; 2025-04-09 alone −$33,667 a lot; trails random entry in both windows.',
    integrity='Re-run on complete chains (5f253c6, 8fb5bad): no TEST figure changed.', finding='One day can erase years; no edge.',
    load=lambda: LO.lane_stress('TE_rule'), period_order=['TRAIN', 'TEST'], verdict_period='TEST')
add(sid='6e', group='A', name='H15 carry lane: the 14:05 SPXW short strangle at ±0.5 expected move, held to settlement',
    folder='research/thetadata/hwr_grid/spxw_v2/ (@7dfea57); report "High win rate 0DTE lanes"', commits='protocol_sha256.txt / — / 01ee3f3, 97e685a, 6691368', dates='2026-10-14', unit='credit',
    hypothesis='A 70%+ win-rate short strangle with a positive cost-realistic lower bound exists.',
    rule='14:05 sell the SPXW strangle at ±0.5 × the 14:05 expected move, held to cash settlement, skip FOMC and month-end (selection S2 on TRAIN).',
    costs='Measured NBBO in; settlement out.', data='SPXW 0DTE 2022-05-13 → 2026-10-09.',
    periods='TRAIN (selection) / TEST (read). The deciding test T-G (forward paper ≥ 150 sessions) was never started.',
    pass_rule='Positive TEST lower bound after the two selections; then T-G forward.',
    verdict='Open, NOT promotable: TEST +$151.17 a lot [+42.15, +251.73], win 70.8%; the pre-registered reselection on complete TRAIN picks a different S2 that fails (+$52.54 [−22.24, +122.49]); ±10% shock ≈ −$65k a lot.',
    baseline='matched random: +$22.60 [−147.61, +261.12].',
    integrity='All historical data has been used for selection; no further historical re-selection allowed (registry).',
    finding='Positive on TEST, but the reselection fails and the tail risk is unbounded.',
    load=lambda: LO.lane_stress('orig_S2'), period_order=['TRAIN', 'TEST'], verdict_period='TEST')

# ---- S01–S17 --------------------------------------------------------------------------------------------------------------------
S_COM = 'research/compass/studies/, results/v1/ (@7dfea57)'
S_FEE = '$0.70 a contract each side (protocol 113cad7), entry at the ask, exit at the bid, 1-minute NBBO'
S_PER = 'Walk-forward by calendar year (protocol 113cad7); reads counted in holdout B (ledger).'
add(sid='7a', group='A', name='S01 Quick Scalps (owner baseline) on index 0DTE', folder=S_COM, commits='protocol 113cad7 / — / 5e90201', dates='2026-10-14',
    hypothesis='The owner\'s Quick Scalps signal (RSI14 cross 55/45 + EMA9 lead, 5m EMA20 + VWAP confirm, 15m EMA alignment) predicts 0DTE moves.',
    rule='Signal → buy the 0DTE contract in a delta band at the ask; exits: stop, two targets, VWAP loss, invalidation, time.',
    costs=S_FEE, data='SPY/QQQ/IWM 0DTE 2022-11-11 → 2026-10-08.', periods=S_PER, pass_rule='Positive net expectancy with a positive lower bound (protocol).',
    verdict='REJECTED: −$4.19 a contract [−5.68, −2.81].', integrity='Status ≠ filled rows (no chain, in position, no expiry) are not trades.',
    finding='The baseline loses $4 a contract after costs.', load=lambda: LO.qs('s01_quick_scalps_0dte_baseline/trades.parquet'))
add(sid='7b', group='A', name='S02 Quick Scalps: 41-variant grid, walk-forward OOS (lower-bound selection)', folder=S_COM, commits='113cad7 / — / 6bf5934', dates='2026-10-14',
    hypothesis='A single-factor variant of the baseline holds out of sample.', rule='Each year, the variant with the best lower bound on the years before is traded the next year (walk-forward).',
    costs=S_FEE, data='SPY/QQQ/IWM 0DTE, OOS 2024-01 → 2026-10.', periods='Walk-forward OOS years 2024–2026.', pass_rule='Positive OOS lower bound, better than matched random.',
    verdict='Nothing promoted: OOS −$3.81 [−5.23, −2.35]; no variant positive or better than random.', integrity='—',
    finding='Variant selection does not rescue the signal.', load=LO.s02_wf)
add(sid='7c', group='A', name='S03 Quick Scalps with weekly expirations (1–7 days)', folder=S_COM, commits='113cad7 / — / 3c8d6cb', dates='2026-10-14',
    hypothesis='The signal works on weekly contracts.', rule='Quick Scalps signal → nearest Friday contract, OI > 250.', costs=S_FEE,
    data='SPY/QQQ/IWM weekly chains, sampled sessions 2017-06 → 2026-10.', periods=S_PER, pass_rule='As S01.',
    verdict='Nothing promoted: +$1.27 a contract [−3.69, +6.25] (= random).', integrity='A cut-short pull is a uniform sample by strata (d706328).',
    finding='Indistinguishable from zero.', load=lambda: LO.qs('s03_weekly_index_etfs_baseline/trades.parquet', pl.lit('2017-06→2026-10')))
add(sid='7d', group='A', name='S09 Quick Scalps on SPXW 0DTE', folder=S_COM, commits='113cad7 / — / 7167541', dates='2026-10-14',
    hypothesis='The baseline on SPXW.', rule='As S01, signals on SPX values with SPY volume.', costs=S_FEE + '; SPXW per its fees',
    data='SPXW 0DTE 2022-05-19 → 2026-10-08, 1,229 fills on 481 days.', periods=S_PER, pass_rule='As S01.',
    verdict='REJECTED: −$46.18 a contract [−63.19, −30.02], −$24 against matched random.', integrity='—', finding='Loses on SPXW too.',
    load=lambda: LO.qs('s09_spxw_0dte_baseline/trades.parquet', pl.lit('2022-05→2026-10')))
add(sid='7e', group='A', name='S10 Short premium: fade the Quick Scalps signal (single contract, 2× stop, to 15:50)', folder=S_COM, commits='A4 912b415 / rerun 1ecdfd5 / cf124a0, 3c8d6cb', dates='2026-10-14', unit='credit',
    hypothesis='Selling the contract the signal would buy earns its premium.', rule='Sell the signal\'s contract at the bid, buy back at 15:50 or at a 2× credit stop (the best cell).',
    costs=S_FEE, data='SPY/QQQ/IWM 0DTE 2022-11 → 2026-10.', periods=S_PER, pass_rule='Positive lower bound and better than random.',
    verdict='Nothing promoted: breakeven at best (+$0.52 a contract).',
    baseline=lambda: LO.seeded_baseline('s10_short_premium_0dte/trades.parquet', (pl.col('structure') == 'single') & (pl.col('exit_set') == 'cutoff_stop2') & (pl.col('adverse_tick') == 0.0), cost='credit'),
    integrity='The vertical rows were superseded after the protective-leg fix; the single-contract rows (shown) are unchanged.',
    finding='The fade is about breakeven.', load=LO.s10)
add(sid='7f', group='A', name='S12 Intraday momentum: first-half-hour direction → 10:00–15:00 long option', folder=S_COM, commits='A5 fe93f87 / — / 2430c9b', dates='2026-10-14',
    hypothesis='The first half hour\'s direction continues (Gao et al.).', rule='Buy the 0DTE contract in the first-half-hour direction at 10:00, exit 15:00.',
    costs=S_FEE, data='SPY/QQQ/IWM 2022-11 → 2026-10 (options).', periods=S_PER, pass_rule='Two-part promotion rule (A1).',
    verdict='Nothing promoted (QQQ-only underlying effect, not batch-robust; option cell negative).', integrity='seed 0 = the signal; 11–15 random.',
    finding='The option expression loses.', load=lambda: LO.seeded('s12_intraday_momentum/trades.parquet'),
    baseline=lambda: LO.seeded_baseline('s12_intraday_momentum/trades.parquet'))
add(sid='7g', group='A', name='S12b 10:00 long option in the first-half-hour direction', folder=S_COM, commits='A5.1 b9b9206 / — / be991de', dates='2026-10-14',
    hypothesis='As S12 with the baseline rule\'s contract.', rule='Buy the baseline-rule 0DTE contract at 10:00 in the first-half-hour direction; exit 15:00.',
    costs=S_FEE, data='SPY/QQQ/IWM 2022-11 → 2026-10.', periods=S_PER, pass_rule='As S12.', verdict='Nothing promoted: −$4.87 a contract [−14.18, +4.87].',
    integrity='—', finding='Negative.', load=lambda: LO.seeded('s12b_first_half_hour_expressions/trades.parquet', pl.col('structure') == 'long'),
    baseline=lambda: LO.seeded_baseline('s12b_first_half_hour_expressions/trades.parquet', pl.col('structure') == 'long'))
add(sid='7h', group='A', name='S15 VRP-conditioned 10:00 short ATM 0DTE straddle (unconditional row)', folder=S_COM, commits='A5 6dfba60 / — / 6ed12b6', dates='2026-10-14', unit='credit',
    hypothesis='Rich implied vs trailing realised volatility marks sellable straddles.', rule='Sell the 10:00 ATM straddle at the bids, buy back at 15:50 at the asks.',
    costs=S_FEE, data='SPY/QQQ 0DTE, 970/971 sessions 2022-11 → 2026-10.', periods=S_PER, pass_rule='A conditioned cell with a positive lower bound.',
    verdict='Nothing promoted: unconditional −$15.46 a straddle [−32.68, +0.29]; rich implied forecasts large moves.', integrity='—',
    finding='The 10:00 short straddle loses.', load=LO.s15)
add(sid='7i', group='A', name='S16b Prior-day fade with a weekly contract (time exit)', folder=S_COM, commits='A5 fe93f87 / — / 5cabc13, 3c8d6cb', dates='2026-10-14',
    hypothesis='The prior session\'s close-to-close move reverses.', rule='Buy the weekly contract against the prior move at the 09:31 close; time exit.',
    costs=S_FEE, data='SPY/QQQ/IWM weekly chains 2017-06 → 2026-10.', periods=S_PER, pass_rule='As S12.',
    verdict='Nothing promoted: −$9.91 a contract [−19.31, −0.26].', integrity='—', finding='Negative.',
    load=lambda: LO.seeded('s16b_prior_day_fade_weekly/trades.parquet', pl.col('exit_set') == 'time_only'),
    baseline=lambda: LO.seeded_baseline('s16b_prior_day_fade_weekly/trades.parquet', pl.col('exit_set') == 'time_only'))
for st_, lab in (('atm_put', 'ATM'), ('put_30d', '0.30-delta'), ('put_15d', '0.15-delta')):
    add(sid=f'7j-{st_}', group='A', name=f'S17 Index put-writing: monthly {lab} cash-secured put', folder=S_COM, commits='A7 c81522a / wording 9ea4adf / 5e7e1bd', dates='2026-10-15', unit='capital',
        hypothesis='Index put-writing earns the variance risk premium (Cboe PUT).', rule=f'Sell the standard monthly {lab} put at the bid at expiry roll, hold to expiration, cash-secured.',
        costs='Bid in; settlement out; $0.70 a contract.', data='SPY and QQQ standard monthlies 2012-06 → 2026-10.', periods='One span (2012–2026); no holdout.',
        pass_rule='A7 carry-lane rule (positive mean with a positive lower bound per cell).',
        verdict='PASSES A7 for QQQ ATM, 0.30Δ and 0.15Δ and SPY ATM puts; alpha 0 against the index, crash risk stated (a carry lane, not an edge).',
        integrity='Covered calls not significantly negative (9ea4adf).', finding='Put-writing earned its premium like the index it is short; a carry, not an edge.',
        load=(lambda s=st_: LO.s17(s)))

# ---- V1–V8 ------------------------------------------------------------------------------------------------------------------------
V_COM = 'research/compass/intel/, studies/v*.py, results/v1/ (@7dfea57)'
V_PER = 'development / validation / hold-out (each hold-out opened once).'
add(sid='8a', group='A', name='V1 T0: short every monthly ATM straddle across the optionable universe', folder=V_COM, commits='A8 29f20e3 (A8.1–A8.4) / — / aff15d9, df4fe32', dates='2026-10-15', unit='premium',
    hypothesis='Single-name monthly straddles are overpriced (volatility risk premium).', rule='Sell the ATM straddle of every optionable name at the cycle\'s entry, hold to expiration (adverse fill: one tick worse).',
    costs='$0.70 a contract each side; mid ± one tick ("adv").', data='The optionable universe 2023-11 → 2026-08, 44,447 name-cycles.',
    periods=V_PER, pass_rule='A8: negative T0 with sorts (T1 IV/RV, T2 term slope, T3 skew) adding a positive long-short.',
    verdict='Rejected: T0 −13.2% of premium dev+val [−22.4, −5.0], −23.6% hold-out; T1–T3 add nothing.',
    integrity='Corporate actions detected from the options market (A8.1–A8.3c).', finding='Selling every straddle lost; the spread takes the premium.',
    load=LO.v1, period_order=['development', 'validation', 'hold-out'], verdict_period='hold-out')
add(sid='8b', group='A', name='V2a: short ATM straddle across the earnings report', folder=V_COM, commits='A9 47c2c2f / — / 4ed84d4, 152f786', dates='2026-10-15', unit='premium',
    hypothesis='Earnings straddles are overpriced.', rule='Sell the ATM straddle at the close before the report, buy back after it (adverse fill).',
    costs='$0.70 a contract each side; adverse tick.', data='1,578 names, reports 2023-11 → 2026-09.', periods=V_PER, pass_rule='A9.',
    verdict='Rejected: −26.1% dev+val [−28.5, −23.3], −34.2% hold-out.', integrity='Friday-only expiry probe checked on all names (95c90f9: no change).',
    finding='Selling earnings straddles lost a quarter of the premium.', load=lambda: LO.v2('a'), period_order=['development', 'validation', 'hold-out'], verdict_period='hold-out')
add(sid='8c', group='A', name='V2b: long ATM straddle into the earnings report', folder=V_COM, commits='A9 47c2c2f / — / 152f786', dates='2026-10-15', unit='premium',
    hypothesis='Buying into the report captures the run-up in implied volatility.', rule='Buy the ATM straddle five sessions before the report, sell at the report.',
    costs='As V2a.', data='As V2a.', periods=V_PER, pass_rule='A9.', verdict='Rejected: −20.9% / −29.3%.', integrity='—',
    finding='Both sides of the earnings straddle lose.', load=lambda: LO.v2('b'), period_order=['development', 'validation', 'hold-out'], verdict_period='hold-out')
add(sid='8d', group='A', name='V3a: single-name 0DTE short ATM straddle 10:00 → 15:50', folder=V_COM, commits='A10–A10.4 9c476c5, 048d33a / — / e4e4cea', dates='2026-10-16', unit='premium',
    hypothesis='Single-name same-day premium is overpriced.', rule='Sell the ATM straddle at 10:00, buy back 15:50 (adverse).', costs='$0.70 a contract each side; adverse tick.',
    data='11 Mon/Wed/Fri names 2017-06 → 2026-10.', periods=V_PER, pass_rule='A10.', verdict='Rejected: −19.8% dev+val [−25.5, −14.7], −7.4% hold-out.',
    integrity='—', finding='Negative.', load=LO.v3, period_order=['development', 'validation', 'hold-out'], verdict_period='hold-out', pooled=True)
add(sid='8e', group='A', name='V8: month-end 13:00 long straddle on unread chains', folder=V_COM, commits='A15 8bc3baf / — / e4e4cea', dates='2026-10-16', unit='premium',
    hypothesis='Month-end afternoons move more than priced (from V7).', rule='Buy the ATM straddle at 13:00 on the month\'s last session, hold to settlement.',
    costs='Ask in (adverse); settlement out.', data='SPXW 2017-06 → 2022-04, SPY 2017-06 → 2022-10 (chains no study had read).', periods='One unread span.',
    pass_rule='A15.', verdict='Rejected: SPXW −6.6% [−24.5, +12.6], SPY −8.4% [−27.2, +11.3].', integrity='Read once on unread chains.',
    finding='The month-end effect V7 suggested did not appear on unread data.', load=LO.v8)

# ---- lifecycle ---------------------------------------------------------------------------------------------------------------------
L_COM = 'research/compass/lifecycle/ (@7dfea57)'
add(sid='9a', group='A', name='Lifecycle P1: Quick Scalps → cash-secured put sale (portfolio)', folder=L_COM, commits='protocol 1f99d75 / L-A4 8bd322a / 425c7f4, b9d04b5', dates='2026-10-15', unit='risk',
    hypothesis='The Tier I finalists, run as a portfolio, earn after costs.', rule='QS signal → sell a cash-secured put (s20 policy), one unit, the lifecycle position engine.',
    costs='$0.70 a contract each side, NBBO.', data='SPY/QQQ/IWM 0DTE 2022-11 → 2026-10.', periods='development + validation / hold-out 2025-10-01 → 2026-10-09 (opened once).',
    pass_rule='R1–R6 promotion rules (Holm; R2 random-day control).', verdict='Rejected: hold-out +$987 (about 1% a year, collateral-bound).',
    integrity='A superseded hold-out file is kept separately.', finding='The put sale earns cents on the cash it ties up.',
    load=lambda: LO.portfolio('P1_QS_CSP_s20'), period_order=['development + validation', 'hold-out 2025-10→2026-10'], verdict_period='hold-out 2025-10→2026-10')
add(sid='9b', group='A', name='Lifecycle P2: Quick Scalps → credit put spread to expiry (portfolio)', folder=L_COM, commits='1f99d75 / L-A4 / d8a7ebb', dates='2026-10-15', unit='risk',
    hypothesis='As P1 with a defined-risk spread.', rule='QS signal → credit put spread held to expiry.', costs='As P1.', data='SPY/QQQ/IWM/SPXW 0DTE.', periods='As P1.',
    pass_rule='As P1.', verdict='Rejected: hold-out −$6,805.', integrity='—', finding='Loses on the hold-out.',
    load=lambda: LO.portfolio('P2_QS_CPS_expiry'), period_order=['development + validation', 'hold-out 2025-10→2026-10'], verdict_period='hold-out 2025-10→2026-10')

add(sid='9c', group='A', name='Lifecycle Tier I, daily tier, L-A3, H-FLO (by configuration)', folder=L_COM,
    commits='1f99d75 / L-A2, L-A3 889691a, L-A4 8bd322a, L-A4.1 f815d27 / 425c7f4, f6d5a98, d8a7ebb, 66bc5c9, 50de62a', dates='2026-10-15',
    hypothesis='Some of 12 setups × 8 structures × 116 management policies (Tier I) or daily setups (Tier D) survive a hold-out.',
    rule='Grids; finalists chosen on development + validation.', costs='$0.70 a contract each side, NBBO.', data='0DTE SPY/QQQ/IWM/SPXW; index-ETF option EOD 2012-06 → 2026-10.',
    periods='hold-out 2025-10-01 → 2026-10-09, opened once per group.', pass_rule='R1–R6.',
    verdict='0 promoted: Tier I no long-premium policy with a positive lower bound, finalists all put sales; L-A3 debit call spread +$64.37 [−18.16, +138.67] p 0.064 (fail); daily tier 19 finalists, all fail R2 (random day); H-FLO a regime descriptor, not an edge.',
    na='not available — committed as configuration-level cells (grid_by_setup.csv, cells.csv); the trade rows are in the scratchpad (lifecycle/archive, 281 MB) and were not re-run for this report.',
    integrity='Random-minute look-ahead corrected (L-A2) before the hold-out.', finding='No configuration survived the hold-out.')

add(sid='10', group='A', name='ATM straddle samples and the independent short-premium prereg (branch compass-research-2026-10-14)',
    folder='research/compass_2026_10_14/ on origin/compass-research-2026-10-14', commits='short_premium PREREG 2f97a0c / — / BLOCKED', dates='2026-10-14 → 15',
    hypothesis='(Measurement) what short-dated ATM straddles cost on 10 names.', rule='—', costs='—', data='8–19 sessions a name.', periods='—', pass_rule='—',
    verdict='No result: the short-premium study was blocked (ThetaData session invalidated off-box).',
    na='not available — price samples only (no trade with an exit); the pre-registered study never ran.', integrity='—', finding='Medians of ATM straddle prices; no strategy.')
add(sid='11', group='A', name='Price-action catalogue and atlas (43 names)', folder='research/compass/intel/04, 06, 07 (@7dfea57)', commits='— / — / 048d33a, 0d706b6, 98fa5f0', dates='2026-10-15',
    hypothesis='(Descriptive) how price action behaves around levels.', rule='—', costs='—', data='43 names 2017–2026 bars.', periods='—', pass_rule='—', verdict='Descriptive; V6 tested its levels (rejected).',
    na='not available — descriptive tables, no trades.', integrity='—', finding='No strategy.')

# =======================================================================================================================================
# B. After the fresh start
# =======================================================================================================================================

add(sid='12', group='B', name='Step 1: every 0DTE contract broken down', folder='step1/', commits='— / — / 2185eb9', dates='2026-10-16',
    hypothesis='(Descriptive) the anatomy of 1,176,935 same-day contracts over 3,687 sessions.', rule='—', costs='—', data='SPY, QQQ, IWM, SPX 0DTE.', periods='—', pass_rule='—',
    verdict='Descriptive.', na='not available — a contract inventory, no trades.', integrity='Checked against the raw quotes (verify.py).', finding='No strategy.')
add(sid='13', group='B', name='Step 2: buy near the money, sell at +100% or hold (within 0.5% of the price)', folder='step2/', commits='— / — / b15b56b', dates='2026-10-16',
    hypothesis='A same-day contract that can double pays for those that do not.',
    rule='Buy every contract within 0.5% of the underlying at the ask at 9:31, 10:00, 10:30, 11:00, 12:00, 1:00, 2:00, 3:00, 3:30; sell the first minute the bid reaches 2× the price paid (at exactly 2×), else hold to the close (worth intrinsic).',
    costs='$0.65 a contract on the buy and on the sale; none when it expires worthless.', data='SPY, QQQ, IWM, SPX 0DTE 2022-05-13 → 2026-10-09 (the near-the-money slice of 10,547,433 trades).',
    periods='pick 2022–24 / check 2025–26 (no holdout; holdout B months read).', pass_rule='None pre-registered (a population study).',
    verdict='Every group loses before and after fees; near the money 29% double, below the share needed to break even.',
    integrity='Formulas: step2/summarize.py (tp100, fees), the committed loader step2.double.load.', finding='Near-the-money 0DTE buys lose 16–22% of premium a trade.',
    load=LR.step2_near, period_order=['pick 2022–24', 'check 2025–26'], verdict_period='check 2025–26')
add(sid='14', group='B', name='Step 3: 108 exits × 9 conditions', folder='step3/', commits='— / — / 09885b6', dates='2026-10-16',
    hypothesis='A target, stop or time exit, or a condition known at the buy, makes step 2\'s trades pay.', rule='108 exits × 9 entry conditions on step 2\'s trades.',
    costs='$0.65 a contract each way.', data='As step 2.', periods='discovery 2022–24 / check 2025–26.', pass_rule='None pre-registered.',
    verdict='Nothing made money in a way that held up; a −50% stop shrank losses; targets raised the win rate and lowered the average.',
    na='not available — committed as per-rule summaries (exits.csv, exits_best.csv); the per-trade paths are committed but the exit grid was not re-run here.',
    integrity='—', finding='No exit rule rescues the buys.')
add(sid='15', group='B', name='Step 4: turn-up buy (1.5× the low) + 20% trailing stop, near the money', folder='step4/', commits='— / — / 6c0e60b', dates='2026-10-16',
    hypothesis='Buying the turn up off the low and selling near the high with a trailing stop finds an edge.',
    rule='The first minute (9:36 → 15 minutes before the close) a contract\'s ask reaches 1.5× its low so far → buy at the ask; sell at the bid once it falls 20% from the highest bid since buying, else hold to the close. Strikes within 0.5% of the price.',
    costs='$0.65 a contract each way (none when worthless).', data='SPY, QQQ, IWM, SPX 0DTE 2022–2026 (this slice of 12,149,834 trades).',
    periods='pick 2022–24 / check 2025–26.', pass_rule='None pre-registered; 126 rules positive in both periods, the 11 biggest failed the stress test.',
    verdict='A trailing stop beats holding but still loses.', integrity='Formulas copied from step4/summarize.py prep().',
    finding='The near-the-money turn-up buy with a 20% trail loses 1–8% of premium a trade.', load=LR.step4, period_order=['pick 2022–24', 'check 2025–26'], verdict_period='check 2025–26')
add(sid='16', group='B', name='Step 5: the runner model (model A/B) and its top 1% picks', folder='step5/', commits='— / — / ae3c63d, 1227394, f9f2746, 491a0c7', dates='2026-10-16 → 17',
    hypothesis='What was visible at the turn tells runners from duds well enough to trade.', rule='Gradient-boosted model A (P(bid ≥ 3× paid)) and B; trade the top 1% / 0.5% / 0.1%, three exits.',
    costs='$0.65 a contract each way.', data='1,602,401 turn-up and range-break buys; trained 2022–24, scored once on 2025–26.', periods='train 2022–24 / scored 2025–26.',
    pass_rule='None pre-registered.', verdict='Runners partly separable (top 1% reach 3× 26% vs 6%) but do not pay; every pick total made money almost all on 2025-11-20, and without its best 5 days it lost $620,114.',
    na='not available — the picks are committed as daily sums (top1_daily.csv), not trades.', integrity='Scored once.', finding='The model ranks runners but its picks do not pay without a handful of days.')
add(sid='17', group='B', name='Step 6: the six pre-registered runner rules × three exits', folder='step6/', commits='30babaa / — / 44b5547', dates='2026-10-23',
    hypothesis='A condition visible at the buy raises the odds of a +40% (family A) or +500% (family B) run enough to trade.',
    rule='The top 3 rules of each family by Pick lift (one or two Part 2 buckets, ≥ 300 Pick trades on ≥ 60 dates), each buying every near-the-money population trade that meets it; exits (a) +40% / −30% / 60 minutes or 3:30, (b) 50% trail armed at +40%, out 3:30, (c) half at +40%, trail the rest 50%, out 3:30.',
    costs='$0.65 a contract each way (SPY/QQQ/IWM), SPXW per schedule; no sale fee at a $0 bid.', data='240,493 near-the-money 0DTE buys 2022-05 → 2026-10-09 (the 28 held-out months never read).',
    periods='pick 2022-05→2024 / check 2025→2026-10-09; the 28 holdout-B months UNOPENED.',
    pass_rule='Check: average r > 0, its 20-session block lower end > 0, and above the 97.5th percentile of 500 cell-matched random draws.',
    verdict='FAIL: 0 of 18 pass; all lose on Check (−3.3% to −21.9% a trade); 14 of 18 below the 20th random percentile.',
    baseline='500 cell-matched random draws per rule and exit (step6/out/results.csv): the rule\'s percentile is printed there; on Check 14 of 18 rule × exit cells sit below the 20th.',
    integrity='The rules are chosen by the committed step6/trade.py choose() on the scratchpad population (39 MB, not committed); verify.py 0 differences in 480 figures; lookahead.py 0 differences in 104,748 values.',
    finding='No rule chosen on Pick made money on Check.', load=LR.step6_rules, period_order=['pick 2022-05→2024', 'check 2025→2026-10-09'],
    verdict_period='check 2025→2026-10-09', pooled=False, summary_slices=[('A1a', 'check 2025→2026-10-09'), ('B1a', 'check 2025→2026-10-09')])

add(sid='18', group='B', name='Compass engine audit (six module groups)', folder='research_notes/Compass engine audit/, reports/Compass engine audit.md',
    commits='— / — / 9cf8110, 59e1a1a, d724ae4, 18cf86a, b84fa3c, 09799af; report 138ff0e', dates='2026-10-21',
    hypothesis='The owner\'s 16-module Compass specification picks direction and opens trades that pay after costs.',
    rule='Each module tested under its own definition (exits and sizing, expected move/ATR/flow, clock and power hour, greeks and books, horizons, sweep and grade).',
    costs='Ask in, bid out, $0.65 each way.', data='0DTE SPY/QQQ/IWM/SPXW 980/980/621/1,106 sessions; daily bars for horizons.', periods='fit 2022–24 / check 2025–26.',
    pass_rule='Picked on 2022–24, read on 2025–26, friction-adjusted.',
    verdict='No directional rule survives after fees. What holds: the 15:58 flat, the −32% backstop, a breakeven lock at +0% with a target on, a trailed remainder, the r,q pricer from parity, Method A flips with three books, net/gross confidence, the MOC magnitude as a volatility gauge, an ATR > 1.5 block on counter-trend fades.',
    na='not available — the audit committed row-level paths and events (paths_*.parquet, events_*.parquet) and per-cell tables; its exit stacks were scored by cell, and no single trade list per rule exists to recompute (spec stack A −4.3% / B −4.5% of debit a trade, exits_sizing.md line 14).',
    integrity='Six blockers stated (no OPRA tape, no strike-level OI history before 2026-10, …).', finding='Frictions, not edges.')

P2 = 'research_notes/Compass phase 2/'
add(sid='19', group='B', name='Phase 2 hyp A: the low-moc_mag closing pin (SPXW short call spread, 15:30, held)', folder=P2 + 'hyp_a_closing_pin', commits='prereg in-doc before the OOS read / — / 5deb793', dates='2026-10-21', unit='risk',
    hypothesis='On quiet closes (low moc_mag) the 15:30 short credit spread pins and pays.', rule='SPXW short call spread, short strike at 1.00 × the move rule, 25 wide, 15:30 at the NBBO, held to settlement, on low-moc_mag sessions (the pre-registered cell).',
    costs=F_065 + '; ' + ASK_BID, data='SPXW 2022-05-13 → 2026-10-09.', periods='fit 2022–24 / OOS 2025–26 (read once).',
    pass_rule='The pick fixed on fit; read OOS for a positive mean with an interval clear of zero.', verdict='NO EDGE: fit +$26 a spread, OOS −$33 [−84, +13].',
    integrity='Cells and the pick written before the OOS run (s3_report.py fit, then oos).', finding='The pin made money on fit and lost out of sample.',
    load=LC.hyp_a, period_order=['fit 2022–24', 'OOS 2025–26'], verdict_period='OOS 2025–26')
add(sid='20a', group='B', name='Phase 2 hyp B: boundary touch — SPY 2-wide 25-delta credit spread, held (the touch pick)', folder=P2 + 'hyp_b_boundary_theta', commits='out/prereg.txt before the OOS read / — / 2c241f4', dates='2026-10-21', unit='risk',
    hypothesis='When price touches the straddle boundary, the far side\'s credit spread decays faster.', rule='At a touch: sell the 2-wide spread on the touched side, short strike at 25 delta, held to settlement.',
    costs=F_065 + '; ' + ASK_BID, data='SPY 2022-11 → 2026-10.', periods='fit 2022–24 / OOS 2025–26.',
    pass_rule='The highest fit lower bound (N ≥ 300, ≥ 150 sessions, positive without the best 5); its lower bound was negative ("least bad").',
    verdict='No edge: the touch adds nothing over the unconditional sell at the same minute (the increment flips sign between periods).', integrity='Deduplicated as analyze.py (one touch a session, side, e, mult, rule, width).',
    finding='Positive in both periods but no better than selling unconditionally.', load=lambda: LC.hyp_b('touch'), period_order=['fit 2022–24', 'OOS 2025–26'], verdict_period='OOS 2025–26')
add(sid='20b', group='B', name='Phase 2 hyp B: the midday SPY iron condor (em1, mid-VIX), the midday pick', folder=P2 + 'hyp_b_boundary_theta', commits='out/prereg.txt / — / 2c241f4', dates='2026-10-21', unit='risk',
    hypothesis='Midday iron condors on SPY are unconditional short premium that pays.', rule='11:30–13:30 every half hour: SPY 2-wide iron condor, shorts at the first listed strikes outside spot ± the ATM straddle, held to settlement, VIX in the fit\'s middle tercile.',
    costs=F_065 + '; ' + ASK_BID, data='SPY 2022-11 → 2026-10.', periods='fit 2022–24 / OOS 2025–26.', pass_rule='As 20a.',
    verdict='"Needs X" (a forward paper run): +4.6% of risk fit, +3.3% OOS (CI $0.03–$10.69). Became the tracker\'s condor_em1 (all-VIX parent, #26).',
    integrity='The VIX terciles recomputed from the fit d15 condors exactly as analyze.py.', finding='Small positive in both periods; $5 a condor on a four-leg structure.',
    load=lambda: LC.hyp_b('mid'), period_order=['fit 2022–24', 'OOS 2025–26'], verdict_period='OOS 2025–26')
for k, kind, wing, lab in (('21a', 'iron', 'w2', 'P1 iron ±2'), ('21b', 'call', 'w2', 'P2 call ±2'), ('21c', 'call', 'w5', 'P3 call ±5')):
    add(sid=k, group='B', name=f'Phase 2 hyp C: 15:00 SPY/QQQ {lab} butterfly, held to settlement', folder=P2 + 'hyp_c_debit_flies', commits='preregistration.md before the OOS run / — / faea67c', dates='2026-10-21', unit='risk',
        hypothesis='Late-day ATM butterflies on quiet closes pin.', rule=f'15:00, SPY and QQQ, {lab} at the 4-leg NBBO, held to settlement, unconditional.',
        costs=F_065 + ' (four legs); ' + ASK_BID, data='SPY and QQQ 2022-11 → 2026-10.', periods='fit 2022–24 / OOS 2025–26.',
        pass_rule='Edge only if the OOS mean is positive with its interval clear of zero AND positive without the best five sessions AND both OOS years positive.',
        verdict='Not confirmed: the picks fell to +2 to +4.5% of risk OOS with intervals through zero and die under $0.01 a leg; the un-picked iron ±5 read +5.0/+6.0% (→ the tracker\'s fly5).',
        integrity='Fill stress ($0.01 a leg) read on both periods as a robustness check.', finding='Positive on fit, shrunk to noise out of sample.',
        load=(lambda kd=kind, w=wing: LC.hyp_c_fly(kd, w)), period_order=['fit 2022–24', 'OOS 2025–26'], verdict_period='OOS 2025–26')
add(sid='21d', group='B', name='Phase 2 hyp C: debit vertical 0.70/0.30, universe B, held (the vertical pick)', folder=P2 + 'hyp_c_debit_flies', commits='preregistration.md / — / faea67c', dates='2026-10-21', unit='premium',
    hypothesis='A debit vertical keeps the directional premium at lower cost.', rule='The audit\'s universe B entries, 0.70Δ/0.30Δ debit vertical, held to settlement.',
    costs=F_065 + '; ' + ASK_BID, data='SPY, QQQ, IWM, SPXW 2022–2026.', periods='fit / OOS.', pass_rule='Pre-registered expectation: negative OOS.',
    verdict='Loses less than the naked contract but still loses (−6.7% of debit fit).', integrity='—', finding='Verticals lose less than calls and puts, and still lose.',
    load=lambda: LC.hyp_c_vertical('B', 'hold'), period_order=['fit 2022–24', 'OOS 2025–26'], verdict_period='OOS 2025–26')
add(sid='22', group='B', name='Phase 2 hyp D: volatility breakout (straddles on the model\'s top decile)', folder=P2 + 'hyp_d_vol_breakout', commits='out/preregistered.md / — / da02507', dates='2026-10-21',
    hypothesis='The volatility model\'s top decile marks straddles worth buying.', rule='Buy straddles/strangles on the top-decile scan minutes.', costs=F_065, data='SPY/QQQ/IWM/SPXW 2022–2026.',
    periods='fit / cut / OOS (read once).', pass_rule='Best-on-fit cell positive OOS.', verdict='No edge: the best-on-fit cell flipped from +4.6% to −7.0%; the model forecasts volatility (AUC 0.71–0.73) but the straddle is already priced richer.',
    na='not available — committed as cells by scan minute and decile (cells_*.csv, minutes_*.parquet); no trade list of the pre-registered cell.', integrity='—', finding='Forecasting volatility is not trading it.')
add(sid='24', group='B', name='Phase 3 hyp E: short-premium lift of the vol model\'s quiet deciles', folder='research_notes/Compass phase 3/hyp_e_short_premium_lift', commits='out/preregistered.md / — / 02d0dcd', dates='2026-10-21',
    hypothesis='Quiet deciles lift the SPY short-premium spread over selling unconditionally.', rule='Sell the SPY spread on the bottom deciles vs unconditionally, same minute.', costs=F_065, data='SPY 2022-11 → 2026-10.',
    periods='fit / OOS.', pass_rule='A pre-registrable lift on fit.', verdict='No edge established — not pre-registrable (no fit cell clear of zero); the D1 condor read later became condor_d20 (#26).',
    na='not available — committed as by-scan cells and pooled tables; the candidate was set after the OOS read (see #26 condor_d20 for its trades).', integrity='—', finding='No lift on fit.')
add(sid='25', group='B', name='Phase 3 hyp F: the 15:30 SPY/QQQ long call ±5 butterfly (cash account)', folder='research_notes/Compass phase 3/hyp_f_cash_butterfly', commits='out/preregistered.md (20:44:54 UTC) / — / f2883c0; report b7ffa46', dates='2026-10-21', unit='risk',
    hypothesis='The cash-account call fly at 15:30 keeps hyp C\'s OOS edge under realistic complex-order fills.', rule='15:30, SPY and QQQ, long call butterfly ±5 around the ATM strike at the 4-leg NBBO package, held to settlement.',
    costs='$0.65 a leg, four legs to open, none at expiry; package at the NBBO (k = 0).', data='SPY, QQQ 2022-11-11 → 2026-10-09.', periods='fit 2022-11 → 2024 / OOS 2025 → 2026-10-09 (the same OOS C read).',
    pass_rule='Four parts: OOS mean > 0 with its interval clear of zero at k = 0; also under $0.01 a leg worse; positive without the best five sessions; both names positive.',
    verdict='Passes all four, but the cell was named after C\'s OOS was printed: a conditionally justified rule, to be confirmed forward (≈ 450 sessions); dies at $0.02 a leg.',
    integrity='The selection is not independent of the OOS it was read on (stated in the report).', finding='+3.85% of risk a fly OOS, carried by the same data that chose it.',
    load=LC.hyp_f, period_order=['fit 2022-11→2024', 'OOS 2025–26'], verdict_period='OOS 2025–26')

TRK = 'scripts/paper_tracker.py; research_notes/Compass phase 3/backtest_replay, backtest_audit, forward_*'
TRK_C = 'defaults ba117a7, 6826b98 / official-close settlement a4ebe90, 99a3d4e, 16eb3c0 / replay 94af538, 30bb73e; audit 1ca1f0e; forward d7115b6, 2a7bd3b'
TRK_P = 'i development 2022-11-11 → 2024-12-31 / ii selection 2025-01-02 → 2026-10-09 (read) / iii forward 2026-10-12 → (untouched). No historical period is untouched for any candidate (AUDIT.md §5).'
TRK_D = 'The replay of every stored session through the live tracker\'s code, settled on the official close (data_recorder/paper_backtest_official, git-ignored, every trade).'
add(sid='26a', group='B', name='Paper tracker: condor_em1 (SPY 2-wide iron condor at ± the ATM straddle, 11:30–13:30)', folder=TRK, commits=TRK_C, dates='2026-10-21 → 22', unit='risk',
    hypothesis='The midday SPY condor of hyp B (#20b), all-VIX form, pays forward.', rule='11:30, 12:00, 12:30, 13:00, 13:30: SPY 2-wide iron condor, shorts the first listed strikes outside spot ± the ATM straddle, held to the official close.',
    costs='Shorts at the bid, longs at the ask; ' + F_065 + '.', data=TRK_D, periods=TRK_P, pass_rule='Confirmation: 60 → 120 forward sessions (the candidate\'s threshold).',
    verdict='Historical periods through zero (i +3.47 [−0.04, +6.68], ii +4.10 [−0.51, +8.15]); the 15:58 close-out turns it negative; forward pending.',
    integrity='Deterministic (a cold replay equals the committed CSV byte for byte); 100 trades re-derived, 0 differences; re-settled on the official close (12,338 of 20,469 trades changed).',
    finding='A few dollars a condor in both historical periods, inside the noise.', load=lambda: LC.tracker('condor_em1'), period_order=['i', 'ii', 'iii'], verdict_period='ii')
add(sid='26b', group='B', name='Paper tracker: fly5 (SPY/QQQ ±5 butterflies at 15:00 and 15:30: iron, call, put)', folder=TRK, commits=TRK_C, dates='2026-10-21 → 22', unit='risk',
    hypothesis='The late-day ±5 fly of hyp C/F pays forward.', rule='15:00 and 15:30: SPY and QQQ ±5 iron, call and put butterflies (one trade seen three ways), held to the official close.',
    costs='Shorts at the bid, longs at the ask; ' + F_065 + '.', data=TRK_D, periods=TRK_P, pass_rule='Confirmation: 250 forward sessions a name.',
    verdict='Iron clear of zero in i and ii (+16.59, +16.20 a trade) but chosen on ii; hold-to-expiry leaves 100 shares a fly; the after-hours rule (#27) DROPS the iron as a SPY/QQQ hold-to-expiry strategy.',
    integrity='As 26a.', finding='Positive historically, but on the period that chose it, and not operationally clean.', load=lambda: LC.tracker('fly5'), period_order=['i', 'ii', 'iii'], verdict_period='ii')
add(sid='26c', group='B', name='Paper tracker: condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00)', folder=TRK, commits=TRK_C + '; candidate 3 99a3d4e', dates='2026-10-21 → 22', unit='risk',
    hypothesis='The 20-delta SPY condor (from hyp E\'s D1 read) pays forward.', rule='13:00, 13:30, 14:00, 14:30, 15:00: SPY 2-wide iron condor at 20 delta, held to the official close.',
    costs='Shorts at the bid, longs at the ask; ' + F_065 + '.', data=TRK_D,
    periods='i-a model training 2022-11 → 2024-06 (in-sample) / i-b decile cuts 2024-07 → 12 / ii selection 2025 → 2026-10-09 / iii forward.',
    pass_rule='Confirmation: 150 forward sessions for the D1 re-test.', verdict='Positive in ii (+7.67 [+3.87, +10.89]) but set after ii was read; the after-hours rule DROPS it as a hold-to-expiry strategy.',
    integrity='As 26a.', finding='Positive on the period it was chosen on.', load=lambda: LC.tracker('condor_d20'), period_order=['i-a', 'i-b', 'ii', 'iii'], verdict_period='ii')
add(sid='26d', group='B', name='Paper tracker: fly_spxw (SPX ±5 / ±25 flies)', folder=TRK, commits='scripts/paper_backtest.py (off unless listed)', dates='2026-10-21',
    hypothesis='The SPXW analogue of fly5.', rule='15:00 and 15:30 SPXW ±5 and ±25 flies.', costs=F_SPXW, data='One week, 2026-10-05 → 09.', periods='—', pass_rule='—',
    verdict='Run only as a one-week sanity run outside the repository; replaced by the pre-registered SPXW test (#28).', na='not available — a one-week sanity run outside the repository; no rows were kept.',
    integrity='—', finding='No result.')
add(sid='27a', group='B', name='After-hours exercise study: fly5 iron ±5, case (b) the post-market decision', folder='research_notes/Compass phase 3/backtest_audit/AFTERHOURS.md', commits='owner\'s rule fixed before the read / — / 633fbff', dates='2026-10-22', unit='risk',
    hypothesis='The SPY/QQQ hold-to-expiry candidates survive after-hours exercise.', rule='fly5 iron held to expiry; case (b): the counterparty exercises on the 17:30 post-market price, the position re-marked at the next 09:30 open.',
    costs='As #26 plus the exercise/assignment fee.', data='SPY/QQQ, period ii (2025-10-13 → 2026-10-09 overlap) and iii (2026-10-12 → 21).', periods='ii / iii (7 sessions with a next open).',
    pass_rule='"If a candidate\'s mean under (b) is ≤ 0 or its block-20 interval includes zero, drop it as a SPY/QQQ hold-to-expiry strategy."',
    verdict='DROP: (b) +22.52 a trade [−20.07, +52.89] in ii.', integrity='16 name-sessions of UW 1-minute post-market bars fetched once with the owner\'s leave; SPY 2025-04-09 official close flagged.',
    finding='Counting after-hours exercise, the iron fly\'s mean is inside the noise.', load=lambda: LC.afterhours('fly5'), period_order=['ii', 'iii'], verdict_period='ii')
add(sid='27b', group='B', name='After-hours exercise study: condor_d20, case (b)', folder='research_notes/Compass phase 3/backtest_audit/AFTERHOURS.md', commits='— / — / 633fbff', dates='2026-10-22', unit='risk',
    hypothesis='As 27a.', rule='condor_d20 held to expiry, case (b).', costs='As 27a.', data='As 27a.', periods='ii / iii.', pass_rule='As 27a.',
    verdict='DROP: (b) +3.84 [−19.94, +22.74] in ii; iii undecided (7 sessions).', integrity='As 27a.', finding='Inside the noise once exercise is counted.',
    load=lambda: LC.afterhours('condor_d20'), period_order=['ii', 'iii'], verdict_period='ii')
SPX = 'research_notes/Compass phase 3/spxw_prereg'
add(sid='28a', group='B', name='SPXW analogue A: iron fly ±5×ratio at 15:00 and 15:30 (fly5 iron)', folder=SPX, commits='2820bb4 / — / 6bb230e', dates='2026-10-22', unit='risk',
    hypothesis='The ETF fly5 iron result transfers to cash-settled SPXW.', rule='SPXW iron fly, wings ±5 × the SPX/SPY ratio, 15:00 and 15:30, package fill at the NBBO rounded against us to $0.05, held to cash settlement on the official SPX close.',
    costs=F_SPXW + '; about $4.93 to open a four-leg structure.', data='SPXW 1,105 full sessions 2022-05-13 → 2026-10-21.', periods='development 2022-05 → 2024 / selection 2025 → 2026-10-09 / forward 8 sessions.',
    pass_rule='(1) selection mean > 0 and block-20 lower bound > 0; (2) selection mean > 0 at +$0.05 package stress; (3) development mean > 0.',
    verdict='FAIL: selection −$39.64 a session [−173.06, +87.48].', integrity='The package rule cost nothing: the summed leg NBBO is always a multiple of $0.05.',
    finding='SPXW did not reproduce the ETF fly.', load=lambda: LC.spxw('iron_fly'), period_order=['development', 'selection', 'forward'], verdict_period='selection')
add(sid='28b', group='B', name='SPXW analogue B: 20-delta iron condor, wings 2×ratio, 13:00–15:00 (condor_d20)', folder=SPX, commits='2820bb4 / — / 6bb230e', dates='2026-10-22', unit='risk',
    hypothesis='As 28a for condor_d20.', rule='SPXW 20-delta iron condor, wings 2 × ratio, five entries 13:00–15:00, package fill, held to cash settlement.', costs=F_SPXW, data='As 28a.', periods='As 28a.',
    pass_rule='As 28a.', verdict='FAIL: selection +$120.76 a session [−95.03, +286.78] — positive but the interval crosses zero.', integrity='As 28a; the ETF−SPXW late-day extrinsic gap measured beside it.',
    finding='Positive in both periods, inside the noise.', load=lambda: LC.spxw('condor_d20'), period_order=['development', 'selection', 'forward'], verdict_period='selection')

PK = 'research_notes/Compass phase 3/picker_prereg'
PK_RULE = ('Opening range = the 09:30–09:59 bars; 10:00–11:59: the first bar with high ≥ ORH × (1 + 2 bp) and close < ORH → PUT '
           '(the low side → CALL); buy the nearest OTM 0DTE contract at the ask one bar later')
PK_COM = dict(folder=PK, commits='c502122 / — / 1e10053', dates='2026-10-22', unit='premium', costs=F_ETF + '; ' + F_SPXW + '; ' + ASK_BID + '; a target at its resting limit',
              data='SPY, QQQ (846 sessions), IWM (484), SPXW (972), 2022 → 2026-10-21, the 134 GeorgeFi card dates excluded.',
              periods='The whole tested span (verdict) and the never-read line 2026-10-14 → 21 (no verdict). The 2022–2026 NBBO had been read by the engine audit for the same universe (disclosed).',
              combined={'whole span (verdict)': ['whole span (card dates out)', 'never-read 2026-10-14→21']},
              period_order=['whole span (card dates out)', 'never-read 2026-10-14→21'], verdict_period='whole span (verdict)')
add(sid='29a', group='B', name='Picker (GeorgeFi rule), PRIMARY: opening-range fade, stop 0.68, target 1.25, 5-minute stop, flat 15:58',
    hypothesis='The opening-range sweep fade the GeorgeFi cards describe makes money as written.', rule=PK_RULE + '; exits: stop at 0.68 × ask, target 1.25 × ask (resting), out at 5 minutes unless +6% reached, flat 15:58.',
    pass_rule='"Pass: mean > 0 with the interval clear of zero on each name, judged only on the span with the excluded dates removed" (PRIMARY only; mean % of premium, 20-session block interval; every name must pass).',
    verdict='FAIL on every name: SPY −6.28% [−8.18, −4.41], QQQ −5.21%, IWM −9.47%, SPXW −4.96%.', integrity='verify_picker.py re-derives trades from the raw files; the flow gate had one session of data (0 trades gated).',
    finding='The fade loses 5–9% of premium a trade on every name.', load=lambda: LC.picker('primary'), **PK_COM)
add(sid='29b', group='B', name='Picker, SECONDARY: the narrative\'s +6% breakeven lock and VIX trail', hypothesis='The vendor\'s narrative exits rescue the rule.',
    rule=PK_RULE + '; exits: stop, target, breakeven lock at +6%, VIX-scaled trail, flat 15:58.', pass_rule='No verdict of its own (labelled).',
    verdict='Labelled: SPY −6.29%, QQQ −5.44%, IWM −9.91%, SPXW −5.01%.', integrity='As 29a.', finding='The narrative exits change nothing.', load=lambda: LC.picker('secondary'), **PK_COM)
add(sid='29c', group='B', name='Picker, S2: "5 minutes" as a hard exit', hypothesis='Reading the 5-minute rule as a hard exit helps.', rule=PK_RULE + '; exit at 5 minutes, or the stop/target first.',
    pass_rule='Sensitivity, no verdict.', verdict='Labelled: SPY −4.20%, QQQ −3.64%, IWM −7.42%, SPXW −3.10%.', integrity='As 29a.', finding='Shorter holds lose less, still lose.', load=lambda: LC.picker('s2'), **PK_COM)
add(sid='29d', group='B', name='Picker, S3: SPXW rides to the official close when in the money at 15:58', hypothesis='SPXW\'s cash settlement adds value.', rule=PK_RULE + '; SPXW only; ITM at 15:58 → settle.',
    pass_rule='Sensitivity, no verdict.', verdict='Labelled: identical to PRIMARY (no trade was open at 15:58).', integrity='As 29a.', finding='No trade reached 15:58.', load=lambda: LC.picker('s3'), **PK_COM)
add(sid='29e', group='B', name='Picker, IMPROVED (picked on the cards): PDH sweep → put, 10:00–12:00, +25% or 5 minutes', hypothesis='The owner\'s "improved" parameters, traced to the cards, work.',
    rule='SPXW/SPY/IWM: prior-day-high sweep → put, 10:00–12:00, sell at +25% or at 5 minutes.', pass_rule='Labelled, never pooled; the owner\'s rule shown for reading only.',
    verdict='FAIL on every name (read only): SPXW −3.81% [−6.76, −0.95], SPY −4.77%, IWM −10.38%.', integrity='Parameters picked from the cards, whose dates are excluded.', finding='Negative on every name.',
    load=lambda: LC.picker('improved'), **PK_COM)
add(sid='29f', group='B', name='Picker: flow gate and grade check', folder=PK, commits='c502122 / — / 1e10053', dates='2026-10-22',
    hypothesis='UW sweep flow on the trade\'s side, and the vendor\'s grades, separate winners.', rule='Gate: trade-side UW sweep ask-premium over the 5 minutes before entry > the other side. Grade: A+/A/B+ on the vendor cards.',
    costs='—', data='Flow: one session (2026-10-21). Grades: the D1 ledger (489 cards).', periods='—', pass_rule='Descriptive only.',
    verdict='Flow gate: 0 of 5 trades gated (one session). Grades (vendor-recorded, not re-marked): A+ +8.09% [+1.81, +19.44], A +3.12%, B+ −3.23%; A+ − A +4.97 [−3.79, +15.09].',
    na='not available — one session of flow (5 trades) and the vendor\'s own recorded returns (see #1, vendor-recorded).', integrity='—', finding='No usable gate; the grades rank the vendor\'s own record.')

FT = 'research_notes/Compass features/'
FT_COM = dict(folder=FT, commits='inventory 04ce685; prereg a2e14e4 / Phase B prereg b6737c7; forward rule b101ae1 / Phase A 2a49049; Phase B e5dd8c6; forward wired 850268e',
              dates='2026-10-22', unit='premium', costs=F_ETF + '; ' + F_SPXW + '; ' + ASK_BID + ' (0DTE at 13 fixed minutes; 1–60 DTE at the EOD closing ask)',
              data='The base trades: 0DTE at 13 fixed minutes (SPY/QQQ/SPXW and the singles\' expiry days) and 1–7, 8–30, 31–60 DTE at the EOD close, 15 names, five strike buckets, 2012-06 → 2026-10 (by span).',
              periods='exploration / holdout — the holdout (43 months + AVGO, MU, QQQ) was OPENED: read twice in Phase A (the first on a table with duplicated rows) and once in Phase B; forward from 2026-10-22 (0 sessions).',
              period_order=['exploration', 'holdout (opened)'], verdict_period='holdout (opened)', pooled=False)
add(sid='30a', group='B', name='Compass features: the base trades (every feature is judged against them)', hypothesis='(The reference set.)',
    rule='Every base trade, fixed exit: 0DTE sold at the 15:58 bid (SPXW held to settlement), multi-day at a fixed horizon.', pass_rule='—', verdict='Descriptive: −13.35% a trade (exploration), −11.03% (holdout).',
    integrity='The holdout join duplicated rows on the first read (777,571 rows for 580,274 trades); fixed with no feature, threshold or rule changed.',
    finding='The base trades lose 11–13% of the debit a trade.', load=lambda: LR.features('base'), **FT_COM)
add(sid='30b', group='B', name='Compass features V1: veto a spread over 10% of mid (PASSED)', hypothesis='Skipping wide spreads makes a losing set lose less.', rule='The base trades with (ask − bid) ÷ mid ≤ 10% at the entry quote.',
    pass_rule='Holdout Δ (with − without, % of debit) > 0 with its 20-session block 95% interval clear of zero.', verdict='PASS: holdout Δ +2.61 [+1.76, +3.46] (−8.43 with vs −11.03 without).',
    integrity='As 30a.', finding='A cost filter: the with-set still loses 8.4% a trade.', load=lambda: LR.features('V1'), **FT_COM)
add(sid='30c', group='B', name='Compass features X3: sell a same-day long option at the 14:00 bid (PASSED)', hypothesis='Selling 0DTE longs at 14:00 beats holding to 15:58/settlement.',
    rule='0DTE base trades entered before 14:00, sold at the 14:00 bid.', pass_rule='As 30b.', verdict='PASS: holdout Δ +7.78 [+4.14, +10.95] (−9.51 with vs −17.29 without).',
    integrity='As 30a.', finding='Selling at 14:00 halves the loss; the with-set still loses 9.5% a trade.', load=lambda: LR.features('X3'), **FT_COM)
add(sid='30d', group='B', name='Compass features BV1b: the V1 veto at 3% (PASSED, Phase B)', hypothesis='A stricter spread veto.', rule='The base trades with spread ≤ 3% of mid.',
    pass_rule='As 30b (Phase B, read once).', verdict='PASS: holdout Δ +4.30 [+2.66, +5.85] (−6.73 with vs −11.03) — the holdout was not virgin for it.', integrity='33 variants tried for 3 candidates.',
    finding='Still −6.7% a trade.', load=lambda: LR.features('BV1b'), **FT_COM)
add(sid='30e', group='B', name='Compass features BX3e: the 14:00 exit on the physically settled names only (PASSED, Phase B)', hypothesis='X3 without SPXW.', rule='X3 on SPY/QQQ/singles (physical settlement).',
    pass_rule='As 30d.', verdict='PASS: holdout Δ +7.67 [+4.23, +10.69] (−11.03 with vs −18.71).', integrity='As 30d.', finding='Still −11% a trade.', load=lambda: LR.features('BX3e'), **FT_COM)
add(sid='30f', group='B', name='Compass features VN1 (venue SPY vs SPXW) and BC3 (V1 + X3 + D6)', folder=FT, commits=FT_COM['commits'], dates='2026-10-22',
    hypothesis='The cheaper venue, and the stacked model, lose less.', rule='VN1: keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid. BC3: V1 veto + X3 exit + D6 direction.',
    costs=FT_COM['costs'], data=FT_COM['data'], periods=FT_COM['periods'], pass_rule='As 30b.',
    verdict='PASS: VN1 holdout Δ +1.18 [+0.50, +2.20] (failed on the duplicated table); BC3 +6.77 [+4.82, +8.19] (−4.26 with vs −11.03).',
    na='not available — VN1 pairs venues and BC3 needs the D6 direction feature; both are computed inside the study\'s screen code, and their per-trade arms are not on disk.',
    integrity='VN1 failed on the first (duplicated) holdout read and passes on the corrected one.', finding='Cost and timing filters; no direction feature passed.')

add(sid='31', group='B', name='Compass direction: post-earnings drift in 31–60 DTE options (rerun)', folder='research_notes/Compass direction/', commits='38b11bf / ledger code 043d723 / 94fb69d', dates='2026-10-22', unit='premium',
    hypothesis='After a report, options on the side of the earnings-day move drift in its direction (PEAD).', rule='At the close after the report: the 31–60 DTE expiry nearest 45 days; buy five strike buckets on the picked side (the sign of the report-day return) at the closing ask; sell at the closing bid 10 full sessions later ($0 if no bid).',
    costs=F_ETF + '; the closing NBBO (EOD).', data='Exploration set X: 1,601 names, 3,129 events (12,114 picked-side trades) 2019-04 → 2026-09.',
    periods='Exploration screen only; the 1,600 holdout names (2019-01 → 2022-12) UNOPENED.', pass_rule='Screen: Δ (picked − both sides) > 0 with its block-20 interval clear of zero; then the holdout once.',
    verdict='FAIL: Δ −0.90 pp [−3.53, +1.71]; the holdout is not fetched and not read.',
    integrity='Rerun for this report at 94fb69d from the stored files: screen.json equal to the committed one to the last float digit (summation order); the trade table expl_trades.parquet rewritten in the scratchpad.',
    finding='The picked side loses 24% of the debit a trade, no better than the other side.', load=LR.direction)

add(sid='32', group='B', name='Compass H1 / edge H1: overnight reversal of the late-day move (SPY, QQQ stock)', folder='research_notes/Compass H1/', commits='38aca66 / — / 4a02144', dates='2026-10-23', unit='stock',
    hypothesis='The 15:00 → close move reverses overnight.', rule='Short 100 shares at the official close if the close > the 15:00 price, long if below; exit at the next 09:30 open.',
    costs='$0.01 a share each way ($2.00 a trade at 1×); 2× shown in the study.', data='SPY 2017-01-03 → 2025-10-10, QQQ 2012-06-01 → 2025-10-10.', periods='Single test; no holdout.',
    pass_rule='In each name: mean $ a trade after costs > 0 and the 20-session block interval clear of zero (both names).', verdict='FAIL: SPY +$11.09 [−4.42, +28.72], QQQ +$9.42 [−0.06, +18.61].',
    integrity='verify_h1.py: 50 random trades re-derived, 0 differences.', finding='The longs carry the overnight drift; the shorts lose.', load=LR.h1, pooled=False)
add(sid='34', group='B', name='Edge H3: earnings IV-crush short iron condor (single names)', folder='research_notes/Edge search/H3', commits='001a136 / — / 34c8fd8', dates='2026-10-23', unit='risk',
    hypothesis='Implied volatility collapses across the report enough to pay a short condor.', rule='Shorts at K0 ± 0.5 implied move, longs ± 1.5, first expiry after R within 14 days, sold at the closing quote before the report, bought back at the reaction session\'s close.',
    costs='Bid/ask both ways, $0.68748 a contract each way.', data='Exploration: 1,601 X names, 2,209 condors 2019-04 → 2022-12.', periods='Exploration screen; holdout (1,600 H names) not fetched, UNOPENED.',
    pass_rule='Screen: mean > 0 with the block interval clear of zero.', verdict='FAIL: −$161.54 a condor [−180.68, −142.46] (−30.2% of max risk); at the mid −$20.',
    integrity='—', finding='The spread and fees take the crush.', load=LR.h3)
add(sid='35', group='B', name='Edge H4: market intraday momentum (SPY, QQQ stock)', folder='research_notes/Edge search/H4', commits='b14b640 / — / dfa575d', dates='2026-10-23', unit='stock',
    hypothesis='The first half hour\'s return predicts the last half hour (Gao, Han, Li & Zhou 2018).', rule='r1 = the 09:59 bar close ÷ the previous official close − 1; long 100 at the 15:30 bar open if r1 > 0, short if < 0; exit at the official close.',
    costs='$0.005 a share entry + $0.01 auction ($1.50 a trade).', data='Test 2025-10-13 → 2026-10-22 (257 sessions a name); exploration (context) SPY 2017 → 2025-10-10, QQQ 2012 → .',
    periods='test (the verdict) / exploration (context only, spent by S12 and others).', pass_rule='Each name: mean > 0 with the block-20 interval clear of zero.',
    verdict='FAIL: SPY −$2.95 [−19.01, +15.37], QQQ +$10.32 [−8.56, +35.77].', integrity='A-priori MDE $28–37 a trade: weak evidence either way.', finding='No momentum after costs.',
    load=LR.h4, period_order=['exploration (context)', 'test 2025-10-13→2026-10-22'], verdict_period='test 2025-10-13→2026-10-22', pooled=False)
add(sid='37a', group='B', name='Edge H7: the pre-FOMC drift (SPY, QQQ stock) — PASSED', folder='research_notes/Edge search/H7_H8_H9', commits='edca472 / forward rule fcc1f4d / 6c94bb8; wired 712b0ad; baseline 827bd5e', dates='2026-10-23', unit='stock',
    hypothesis='Stocks drift up in the 24 hours before a scheduled FOMC statement (Lucca & Moench 2015).', rule='Buy 100 at the official close of the session before each scheduled 2:00 pm statement (2013-03-20 on); sell at the 13:58 bar\'s close on the statement day.',
    costs='$0.01 a share auction entry + $0.005 exit ($1.50 a trade).', data='SPY 77 statements 2017-02 → 2026-09; QQQ 108 2013-03 → 2026-09.', periods='Single test (no study had read the signed pre-FOMC return); forward from 2026-10-28 (N 366 SPY / 483 QQQ).',
    pass_rule='Each name: mean > 0 with the block-20 interval (calendar sessions, 2,000 draws, seed 20261023) clear of zero at 1× and 2×; Bonferroni m = 13 for an EDGE.',
    verdict='PASS both names: SPY +$70.43 [+14.64, +129.31], QQQ +$69.59 [+23.10, +122.14]; QQQ clears Bonferroni (EDGE under rule 5); not "works" before its forward N.',
    baseline='descriptive baseline against every non-FOMC session over the same clock window (H7_BASELINE.md, 827bd5e), no new verdict.',
    integrity='The gross is the night (close → 09:30 ≈ +$73–74); QQQ before March 2016 −$3.00.', finding='About +$70 a trade (0.2% of notional) in both names, carried overnight.', load=LR.h7, pooled=False)
add(sid='37b', group='B', name='Edge H8: turn of the month (SPY, QQQ stock)', folder='research_notes/Edge search/H7_H8_H9', commits='edca472 / — / 6c94bb8', dates='2026-10-23', unit='stock',
    hypothesis='Returns concentrate from the last trading day to the third of the new month.', rule='Buy 100 at the official close of the second-to-last session of each month, sell at the official close of the third session of the next.',
    costs='$0.01 a share each way ($2.00 a trade).', data='SPY 117 turns 2017-01 → 2026-09; QQQ 172 2012-06 → 2026-09.', periods='Single test.', pass_rule='As H7.',
    verdict='SPY FAIL; QQQ PASS at 1× only (+$110.22 [+0.84, +218.26]) — not an EDGE.', integrity='The nine 2026 turns are about half of each total.', finding='Positive means, intervals at or through zero.', load=LR.h8, pooled=False)

for sid, nm, txt in (('36', 'Edge H5 (SPY − SPXW late straddle) and H6 (monthly put spreads), forward only', 'H5: no forward session read yet (N = 1,326 sessions); H6: entries from 2026-11-02 (N = 449 months). Their historical reads are spent (the SPXW report, S17).'),
                     ('38', 'Edge H9: overnight drift (forward only, withdrawn)', 'Withdrawn by the owner 2026-10-23 (c68f389) before any forward row was written; the registered rule edca472 is unchanged.')):
    add(sid=sid, group='B', name=nm, folder='research_notes/Edge search/', commits=('e114e30 / — / wired 23c0cc3' if sid == '36' else 'edca472 / — / wired 712b0ad, removed c68f389'), dates='2026-10-23',
        hypothesis='(See the prereg.)', rule='(See the prereg.)', costs='—', data='Forward only.', periods='Forward; no historical read.', pass_rule='At N forward trades only.', verdict='No verdict.',
        na='not available — forward-only: no trade exists. Every metric (trades, win rate, mean, interval, drawdown, by year) is "not available" because no forward session has been counted. ' + txt,
        integrity='—', finding='Nothing to report yet.')
add(sid='39', group='B', name='Compass scanner (score ≥ 80, SPY/QQQ/IWM 0DTE)', folder='research_notes/Compass scanner/', commits='142fcf4 / — / 9e3888e', dates='2026-10-23',
    hypothesis='The owner\'s scanner score (RSI/VWAP/RVOL/structure) gives a forward move worth an option trade.', rule='Signal check first: the underlying\'s forward return after a signal vs non-signal minutes; only then the option P&L.',
    costs='—', data='SPY/QQQ/IWM bars, Pick 2017-07-05 → 2022-11-18 and the option layer\'s Pick.', periods='Pick / Check; the 28 holdout months and AMD/AVGO UNOPENED.',
    pass_rule='At 15 or 30 minutes: excess > 0 with its block-20 interval clear of zero and a positive signal mean.', verdict='FAIL at the gate: 15 min −0.30 bp [−0.56, −0.07] (wrong side); 30 min −0.19 bp [−0.57, +0.21]. The study stopped.',
    na='not available — signal-only: the gate failed before any option was priced, so trades, win rate, average win/loss, biggest win/loss, profit factor, drawdown, top-5 share and by-year are not available; no exit or option P&L was ever read.',
    integrity='No held-out month read for an outcome.', finding='The scanner\'s signals do not move the underlying their way.')
add(sid='40a', group='B', name='Compass EMA ladder: PREVIEW 2025-03, 13 versions (rerun)', folder='research_notes/Compass EMA ladder/', commits='0dd8c5d / — / cb79c23', dates='2026-10-23', unit='premium',
    hypothesis='The owner\'s EMA ladder entries on 0DTE options make money.', rule='EMA 9 / ladder L1 (V1, the preview\'s base) and V2–V13 (one change each); the best-R/R execution contract; exits per PREREG_EMA_LADDER §3.',
    costs='$0.68748 a contract each way; ask in, bid out; bid 0 → $0, no exit fee.', data='SPY, QQQ, IWM 0DTE, 21 sessions 2025-03-03 → 31 (inside Pick, not held out).',
    periods='PREVIEW, no verdict; the full study was never run; the 28-month holdout UNOPENED for this rule.', pass_rule='None for a preview (the study\'s rule waits for the full run).',
    verdict='PREVIEW: every version loses.', integrity='Rerun for this report at cb79c23/e9d13c0 from the stored files: preview_2025-03.json byte-identical to the original run (sha256 81edab0c934effe5…).',
    finding='All 13 versions lose 3.6–26.7% of premium a trade in the month.', load=lambda: LR.ema_ladder('ladder'), pooled=False, summary_slices=[('V1', 'preview 2025-03')])
add(sid='40b', group='B', name='Compass EMA ladder: "take profits are the nearest EMAs" PREVIEW (E1 ATM, E2 best-R/R)', folder='research_notes/Compass EMA ladder/', commits='rule aad56cf / — / e9d13c0', dates='2026-10-23', unit='premium',
    hypothesis='Targets at the nearest EMAs rescue the entries.', rule='E1: the ATM contract (3% spread veto); E2: the best-R/R contract (3% cap); targets at the nearest EMAs, exits on the ATM chart.',
    costs='As 40a.', data='2025-02 (19 sessions, fresh) and 2025-03 (21, seen before).', periods='PREVIEW, no verdict.', pass_rule='None.',
    verdict='PREVIEW: both versions lose in both months.', integrity='Rerun byte-identical (targets_2025-02.json 6de804ea3ddfa9d5…, targets_2025-03.json 2b005e352e86e126…).',
    finding='E1 −2.3 to −2.8% and E2 −4.8 to −5.2% of premium a trade.', load=lambda: LR.ema_ladder('targets'), pooled=False, summary_slices=[('E1', 'preview 2025-02 (fresh)')])
add(sid='41a', group='B', name='EMA system v0: PREVIEW on 2026-10-12 → 16 (5 sessions)', folder='research_notes/EMA system/', commits='af32405 / — / 8765f71', dates='2026-10-23', unit='premium',
    hypothesis='The owner\'s EMA options system as specified (v0 defaults pinned).', rule='RULEBOOK_v0.md: Config A/B entries, exits X1 (+1R), X2 (+2R), X3 (runner), X4; SPXW (SPX prints), SPY, QQQ, IWM.',
    costs='$0.68748 SPY/QQQ/IWM; SPXW $1.18748/$1.27748; ask in, bid out.', data='5 full sessions 2026-10-12 → 16 (a falling week: SPY −1.96%).', periods='PREVIEW, no verdict.',
    pass_rule='None.', verdict='PREVIEW: every row net positive in a falling week, 86% of trades puts.', integrity='—', finding='One falling week, mostly puts.', load=lambda: LR.ema_system('v0'), pooled=False,
    summary_slices=[('Config A X1', 'preview 2026-10-12→16')])
add(sid='41b', group='B', name='EMA system v1: PREVIEW on three drawn weeks (up, flat, down)', folder='research_notes/EMA system/', commits='f171654 / — / f512d21', dates='2026-10-23', unit='premium',
    hypothesis='v0 with four changes (the three passed rules V1, X3, VN1 and a fix).', rule='RULEBOOK_v1.md.', costs='As 41a.', data='Weeks drawn by seed 2026102310: up 2025-07-21, flat 2026-02-02, down 2026-07-13.',
    periods='PREVIEW, no verdict; no day in a held-out month.', pass_rule='None.', verdict='PREVIEW: about zero pooled; the sign follows the week.', integrity='—', finding='The sign follows the week.',
    load=lambda: LR.ema_system('v1'), pooled=False, combined={'three weeks pooled': ['preview week: up', 'preview week: flat', 'preview week: down']},
    period_order=['preview week: up', 'preview week: flat', 'preview week: down'], summary_slices=[('Config A X1', 'three weeks pooled')])
add(sid='42', group='B', name='George A+ entry + EMA targets', folder='(research_notes/George A+ EMA targets/ was planned)', commits='none', dates='2026-10-23',
    hypothesis='The GeorgeFi "A+" entry with EMA price-target exits.', rule='—', costs='—', data='—', periods='—', pass_rule='—', verdict='Never run.',
    na='not available — the run was stopped before its prereg was committed; no file exists on disk or in history, so every metric is not available.', integrity='—', finding='No result.')
add(sid='43', group='B', name='Compass ICT: sweep → displacement/MSS → FVG on SPXW 0DTE', folder='research_notes/Compass ICT/', commits='9d6c37e / Amendment 1 9dbc0bf / preview 315fe8e; exploration 0943030', dates='2026-10-23', unit='premium',
    hypothesis='The owner\'s ICT rule (v0) and its variants trade SPXW 0DTE at a profit.', rule='HTF bias, a sweep of a level in a killzone, displacement/MSS, entry in the FVG; 2 contracts; TP1 half, TP2, stop; V1 OTE, V2 out 14:00, V3 range gate, V4 5-min; four ablations.',
    costs=F_SPXW + '; ask in, bid out.', data='SPXW 0DTE, 818 full sessions 2022-05-16 → 2026-10-09 (the 28 held-out months out); preview 2026-10-09 → 22.',
    periods='exploration / preview (10 sessions). Holdout A and holdout B UNOPENED; finalists named, never read.',
    pass_rule='Finalists: v0 plus at most 2 candidates with exploration mean % > 0 and underlying return > 0; holdout B pass: options mean % > 0, interval clear of zero, ≥ 80 trades.',
    verdict='Exploration only: v0 −0.8% [−7.7, +7.2], +$48 a trade; no holdout read.', integrity='Amendment 1 (ablations become candidates) committed before any exploration result.',
    finding='v0 is about zero, and 398% of its profit comes from its five best days.', load=LR.ict, pooled=False,
    period_order=['exploration 2022-05→2026-10-09', 'preview 2026-10-09→22'], verdict_period='exploration 2022-05→2026-10-09', summary_slices=[('v0', 'exploration 2022-05→2026-10-09')])
add(sid='44', group='B', name='Compass EMA: the owner\'s three EMA / ORB models', folder='research_notes/Compass EMA/', commits='9af93fc (prereg + HOLDOUT_LEDGER) / — / none', dates='2026-10-23',
    hypothesis='(See the prereg.)', rule='PREREG_COMPASS_EMA.md v0.', costs='—', data='SPXW (primary), QQQ (secondary).', periods='Holdouts A and B UNOPENED.', pass_rule='(See the prereg.)', verdict='Never computed.',
    na='not available — the run was stopped before computing: a partial engine and a session list exist in the scratchpad (compass_ema_partial/), no signal, trade or P&L.', integrity='—', finding='No result.')
add(sid='45', group='B', name='DR-GCE gates 1 and 2 (Mode 1 Gamma Vacuum Squeeze)', folder='research_notes/DR-GCE/', commits='01d5c8e, 294d4f2 / A1 041baba / b20eb9c, 00eb3d5', dates='2026-10-23',
    hypothesis='Mode 1 signals touch +18% within 4 minutes far more often than random (gate 1), and in their own direction (gate 2).', rule='Signal rows on SPXW 0DTE; the contract under the gate\'s rules; a touch = +18% within 4 minutes before the stop.',
    costs='Real NBBO.', data='504 exploration sessions 2023-12-01 → 2026-10-09; 98 Mode 1 signals.', periods='Exploration; the 28 held-out months UNOPENED.',
    pass_rule='Gate 1: touch-rate lower bound above the random baseline\'s 97.5%; gate 2: signal − opposite side touch difference clear of zero.',
    verdict='Gate 1 PASS (narrow: 32.7% [23.3, 40.2] vs 16.0% [9.2, 22.4]); gate 2 FAIL (the lift is volatility, not direction). No backtest was written.',
    na='not available — signal-only: touch outcomes (signals.csv, gate2_pairs.csv), never traded to an exit; no P&L metric exists.', integrity='Guard selftest 5 of 5.', finding='The lift is volatility after the impulse, not direction.')
add(sid='46', group='B', name='Trend-day test', folder='—', commits='none', dates='—', hypothesis='—', rule='—', costs='—', data='—', periods='—', pass_rule='—', verdict='Never registered, never run.',
    na='not available — never run (the trend-day share is only described in step 6).', integrity='—', finding='No result.')


# =======================================================================================================================================
# The opening pages
# =======================================================================================================================================

def _row(st, rows):
    """the page-1 rows of a strategy"""
    if st.load is None:
        return []
    want = st.summary_slices
    if not want:
        vp = st.verdict_period or (rows[0][1] if rows else '')
        pooled = [r for r in rows if r[1] == vp and r[0] == 'all names']
        if pooled:
            want = [('all names', vp)]
        else:
            want = [(r[0], r[1]) for r in rows if r[1] == vp]
    out = []
    for i, p in want:
        for inst, per, m in rows:
            if inst == i and per == p:
                out.append((st, inst, per, m))
    return out


def summary_table(summary) -> str:
    rows = []
    for st, rr in summary:
        rows += _row(st, rr)
    rows.sort(key=lambda t: (-(t[3].get('mean_pct') if math.isfinite(t[3].get('mean_pct', float('nan'))) else -1e9)))
    U = {'premium': '% prem', 'risk': '% risk', 'stock': '% notional', 'credit': '% credit', 'capital': '% capital'}
    out = ['| # | strategy | name | period | trades | win % | avg win | avg loss | mean trade | biggest win | biggest loss | 20-session block 95% (mean %) | verdict |',
           '|' + '|'.join('-' * (3 * k) for k in (3, 16, 6, 9, 5, 4, 7, 7, 9, 8, 8, 9, 12)) + '|']
    for st, inst, per, m in rows:
        f = M.fnum
        out.append(f"| {st.sid} | {label(st)} | {inst} | {per} | {m['trades']:,} | {m['win_rate']:.1f} | {f(m['avg_win_pct'], 1)}% / {f(m['avg_win_usd'], 0)} | "
                   f"{f(m['avg_loss_pct'], 1)}% / {f(m['avg_loss_usd'], 0)} | **{f(m['mean_pct'], 3 if st.unit == 'stock' else 2)} {U.get(st.unit, '')}** / {f(m['mean_usd'], 2)} | "
                   f"{f(m['best'][0], 0)} ({m['best'][2]}) | {f(m['worst'][0], 0)} ({m['worst'][2]}) | {M.fci(m['ci_pct'], 3 if st.unit == 'stock' else 2)} | {short_verdict(st)} |")
    return '\n'.join(out)


def label(st) -> str:
    n = (st.summary_label or st.name).replace('|', '/')
    return n if len(n) <= 80 else n[:78].rsplit(' ', 1)[0] + ' …'


def short_verdict(st) -> str:
    v = st.verdict.split(':')[0].split(' (')[0].replace('|', '/')
    return v if len(v) <= 70 else v[:68].rsplit(' ', 1)[0] + ' …'


def write_report(secs, summary, outdir: Path, want):
    import front
    body = [front.HEAD, '## Page 1. Every strategy, sorted by mean trade', '', front.SUMMARY_NOTE, '', summary_table(summary), '',
            '**Studies with no trade-level result** (each has its own short section below):', '',
            '| # | study | why no metrics | verdict |', '|' + '|'.join('-' * (3 * k) for k in (2, 14, 30, 10)) + '|']
    for st, _ in summary:
        if st.load is None:
            body.append(f"| {st.sid} | {st.name} | {st.na.replace('not available — ', '')[:160]} | {short_verdict(st)} |")
    body += ['', front.PASSED, '', front.ledger(), '', front.DATA, '', front.FORWARD, '', front.METHOD, '']
    cur = None
    for st, md in secs:
        if st.group != cur:
            cur = st.group
            body.append('# Part A. Studies before the fresh start (75c29c9), read from 7dfea57' if cur == 'A' else
                        '# Part B. Studies after the fresh start')
            body.append('')
        body.append(md)
    name = 'FINAL_RESEARCH_REPORT.md' if not want else 'FINAL_RESEARCH_REPORT.partial.md'
    text = '\n'.join(body).replace('_*.', '_\\*.').replace('_*_', '_\\*_')
    (outdir / name).write_text(text)
    print('wrote', outdir / name)
