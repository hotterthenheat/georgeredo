"""loaders_old.py — the trade frames of the studies before the fresh start (75c29c9), read from the archive commit
7dfea57 with `git show` (never checked out), plus the vendor's own ledger."""
from __future__ import annotations

import polars as pl

from base import git_frame, std

RES = 'research/compass/results/v1/'


def _d(col='session'):
    return pl.col(col).cast(pl.Utf8).str.slice(0, 10)


# ---- #1 GeorgeFi's own cards (vendor-recorded) ------------------------------------------------------------------------------------------

def vendor_cards() -> pl.DataFrame:
    n = git_frame('research/georgefi_full_history/normalized/trades.csv')
    prem = pl.when(pl.col('avg_entry_premium') > 0).then(pl.col('avg_entry_premium')).otherwise(pl.col('entry_premium'))
    per = pl.concat_str([pl.lit('Epoch '), pl.col('epoch_number').cast(pl.Utf8)])
    inst = pl.concat_str([pl.col('book'), pl.lit(' '), pl.col('account_type')])
    return std(n.select(pl.col('entry_date_et').alias('date'), inst.alias('inst'), per.alias('period'), pl.col('occ').alias('contract'),
                        (prem * 100 * pl.col('size')).alias('cost'), pl.col('pnl_reported').alias('pnl'),
                        pl.col('exit_reason').str.slice(0, 40).alias('reason')))


# ---- #2 the George rebuild (144 variants) ---------------------------------------------------------------------------------------------

_BT = None


def rebuild(variant: str | None, model: str = 'spread') -> pl.DataFrame:
    global _BT
    if _BT is None:
        _BT = git_frame('backtest/results/v1/trades.csv.gz')
    b = _BT if variant is None else _BT.filter(pl.col('variant') == variant)
    per = pl.when(pl.col('date') < '2026-03-02').then(pl.lit('in-sample 2025-06→2026-02')).otherwise(pl.lit('out-of-sample 2026-03→10'))
    return std(b.select(pl.col('date'), pl.col('ticker').alias('inst'), per.alias('period'), pl.col('contract'),
                        (pl.col('entry_px') * 100).alias('cost'), pl.col(f'usd_{model}').alias('pnl'), pl.col('reasons').alias('reason')))


def rebuild_baseline() -> pl.DataFrame:
    b = git_frame('backtest/results/v1/baseline.csv.gz')
    return b


# ---- #4 GeorgeFi's trades re-priced at the NBBO, and reconstructed ----------------------------------------------------------------------

def georgefi_nbbo() -> pl.DataFrame:
    g = git_frame('research/georgefi_full_history/results/F_nbbo_trades.csv').filter(pl.col('both_ok') == True)  # noqa: E712
    per = pl.when(pl.col('group') == 'paper').then(pl.lit('paper book')).otherwise(pl.concat_str([pl.lit('ledger '), pl.col('epoch')]))
    ask = pl.col('entry_ask').cast(pl.Float64, strict=False)
    return std(g.filter(pl.col('kind') == 'opt').select(pl.col('day').alias('date'), pl.lit('all roots').alias('inst'), per.alias('period'),
                        pl.concat_str([pl.col('root'), pl.lit(' '), pl.col('side'), pl.lit(' '), pl.col('trade_id').cast(pl.Utf8)]).alias('contract'),
                        (ask * 100 * pl.col('size')).alias('cost'), pl.col('pnl_exec_nbbo').alias('pnl'),
                        pl.lit('vendor exit time, filled at the NBBO').alias('reason')))


def georgefi_reconstructed(engine: str = 'trail') -> pl.DataFrame:
    c = git_frame('research/georgefi_full_history/results/C_trades.csv')
    c = c.filter(pl.col(f'{engine}_spread_usd').is_not_null())
    days = git_frame('research/georgefi_full_history/normalized/trades.csv').select(pl.col('trade_id').cast(pl.Utf8), pl.col('entry_date_et').alias('day')).unique('trade_id')
    c = c.with_columns(pl.col('trade_id').cast(pl.Utf8)).join(days, on='trade_id', how='left').filter(pl.col('day').is_not_null())
    per = pl.when(pl.col('group') == 'paper').then(pl.lit('paper book')).otherwise(pl.concat_str([pl.lit('ledger '), pl.col('epoch')]))
    cost = pl.when(pl.col(f'{engine}_spread_ret').abs() > 1e-12).then(pl.col(f'{engine}_spread_usd') / pl.col(f'{engine}_spread_ret')).otherwise(pl.col('entry_vwap') * 100)
    return std(c.select(pl.col('day').alias('date'),
                        pl.col('root').alias('inst'), per.alias('period'),
                        pl.concat_str([pl.col('root'), pl.lit(' '), pl.col('side'), pl.lit(' '), pl.col('trade_id').cast(pl.Utf8)]).alias('contract'),
                        cost.alias('cost'), pl.col(f'{engine}_spread_usd').alias('pnl'), pl.col(f'{engine}_reason').alias('reason')))  # noqa


# ---- #5 deep research round 1: the flow rule F1 on SPY ------------------------------------------------------------------------------------

def flow_f1() -> pl.DataFrame:
    d = git_frame('research/flow_predictors/trade_rule_SPY_F1.csv').filter(pl.col('set') == 'rule')
    return std(d.select(pl.col('date'), pl.lit('SPY').alias('inst'), pl.lit('2025-07→2026-10').alias('period'), pl.col('contract'),
                        (pl.col('entry_px') * 100).alias('cost'), pl.col('trail_spread_usd').alias('pnl'), pl.col('trail_reason').alias('reason')))


# ---- #6 ThetaData lanes --------------------------------------------------------------------------------------------------------------

def lane_ta() -> pl.DataFrame:
    t = git_frame('research/thetadata/straddle_nbbo/csv/straddles_nbbo.csv.gz').filter(pl.col('time') == '13:00')
    return std(t.select(pl.col('date'), pl.col('ticker').alias('inst'), pl.lit('2025-06→2026-10').alias('period'),
                        pl.concat_str([pl.col('ticker'), pl.lit(' 13:00 short straddle '), pl.col('strike').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('credit_bid') * 100).alias('cost'), pl.col('pnl_exec').alias('pnl'), pl.lit('bought back 15:55').alias('reason')))


def lane_tb() -> pl.DataFrame:
    d = git_frame('research/thetadata/index_tests/tb_momentum/tb_daily.csv').filter((pl.col('regime_spy') == 'neg') & (pl.col('valid') == 1))
    side = pl.when(pl.col('spy_rod') > 0).then(pl.lit('long')).otherwise(pl.lit('short'))
    return std(d.select(pl.col('date'), pl.lit('SPY').alias('inst'), pl.lit('negative-gamma days 2024-05→2026-10').alias('period'),
                        pl.concat_str([pl.lit('100 SPY '), side, pl.lit(' 15:30→close')]).alias('contract'),
                        (pl.col('spy_c1530') * 100).alias('cost'), (pl.col('strat_spy_net') / 1e4 * pl.col('spy_c1530') * 100).alias('pnl'),
                        pl.lit('official close').alias('reason')))


def lane_tc() -> pl.DataFrame:
    c = git_frame('research/thetadata/index_tests/tc_spxw_straddle/tc_straddles.csv')
    return std(c.select(pl.col('date'), pl.lit('SPXW').alias('inst'), pl.lit('2025-06→2026-10').alias('period'),
                        pl.concat_str([pl.lit('SPXW 13:00 short straddle '), pl.col('strike').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('credit_exec') * 100).alias('cost'), pl.col('pnl_exec_15:55').alias('pnl'), pl.lit('bought back 15:55').alias('reason')))


def lane_stress(label: str) -> pl.DataFrame:
    s = git_frame('research/thetadata/hwr_grid/spxw_v2/results/stress_trades.csv.gz').filter(pl.col('label') == label)
    return std(s.select(pl.col('date'), pl.lit('SPXW').alias('inst'), pl.col('period'),
                        pl.concat_str([pl.lit('SPXW '), pl.col('entry_hm'), pl.lit(' '), pl.col('kp').cast(pl.Utf8), pl.lit('P/'),
                                       pl.col('kc').cast(pl.Utf8), pl.lit('C')]).alias('contract'),
                        (pl.col('credit') * 100).alias('cost'), pl.col('pnl'), pl.col('how').alias('reason')))


# ---- #7 Compass engine studies S01–S17 -------------------------------------------------------------------------------------------------

def qs(path: str, period_fn=None) -> pl.DataFrame:
    d = git_frame(RES + path).filter(pl.col('status') == 'filled')
    per = period_fn if period_fn is not None else pl.lit('2022-11→2026-10')
    return std(d.select(_d().alias('date'), pl.col('symbol').alias('inst'), per.alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' '), pl.col('expiration').cast(pl.Utf8), pl.lit(' '),
                                       pl.col('strike').cast(pl.Utf8), pl.col('right')]).alias('contract'),
                        (pl.col('entry_ask') * 100).alias('cost'), pl.col('pnl'), pl.col('exit_reason').alias('reason')))


def wf_period():
    return pl.concat_str([pl.lit('walk-forward OOS '), pl.col('year').cast(pl.Utf8)])


def s02_wf() -> pl.DataFrame:
    d = git_frame(RES + 's02_walkforward/walkforward_lb_oos_trades.parquet').filter(pl.col('status') == 'filled')
    return std(d.select(_d().alias('date'), pl.col('symbol').alias('inst'), pl.lit('walk-forward OOS 2024-01→2026-10').alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('right'), pl.lit(' '), pl.col('config')]).alias('contract'),
                        (pl.col('entry_ask') * 100).alias('cost'), pl.col('pnl'), pl.col('exit_reason').alias('reason')))


def s10() -> pl.DataFrame:
    d = git_frame(RES + 's10_short_premium_0dte/trades.parquet').filter(
        (pl.col('status') == 'filled') & (pl.col('structure') == 'single') & (pl.col('exit_set') == 'cutoff_stop2') & (pl.col('adverse_tick') == 0.0) & (pl.col('seed') == 0))
    return std(d.select(_d().alias('date'), pl.col('symbol').alias('inst'), pl.lit('2022-11→2026-10').alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' short '), pl.col('strike').cast(pl.Utf8), pl.col('right')]).alias('contract'),
                        (pl.col('credit') * 100).alias('cost'), pl.col('pnl'), pl.col('exit_reason').alias('reason')))


def seeded(path: str, extra=None, seed: int = 0, cost='entry_ask') -> pl.DataFrame:
    d = git_frame(RES + path).filter((pl.col('status') == 'filled') & (pl.col('seed') == seed))
    if extra is not None:
        d = d.filter(extra)
    return std(d.select(_d().alias('date'), pl.col('symbol').alias('inst'), pl.lit('2017-06→2026-10' if 's16b' in path else '2022-11→2026-10').alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('right')]).alias('contract'),
                        (pl.col(cost) * 100).alias('cost'), pl.col('pnl'), pl.col('exit_reason').alias('reason')))


def s15() -> pl.DataFrame:
    d = git_frame(RES + 's15_vrp_short_straddle/trades.parquet')
    return std(d.select(_d().alias('date'), pl.col('symbol').alias('inst'), pl.lit('2022-11→2026-10').alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' 10:00 short straddle '), pl.col('strike').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('credit') * 100).alias('cost'), pl.col('pnl'), pl.lit('bought back 15:50').alias('reason')))


def s17(structure: str) -> pl.DataFrame:
    d = git_frame(RES + 's17_put_write/cycles.parquet').filter((pl.col('structure') == structure) & (pl.col('adverse') == 0.0))
    return std(d.select(_d('entry').alias('date'), pl.col('root').alias('inst'), pl.lit('2012-06→2026-10').alias('period'),
                        pl.concat_str([pl.col('root'), pl.lit(' '), pl.col('expiration').cast(pl.Utf8), pl.lit(' '), pl.col('strike').cast(pl.Utf8)]).alias('contract'),
                        pl.col('capital').alias('cost'), pl.col('pnl'), pl.lit('held to expiration').alias('reason')))


# ---- #8 Compass intel V1–V8 ------------------------------------------------------------------------------------------------------------

def _split():
    return pl.col('split').replace({'dev': 'development', 'val': 'validation', 'holdout': 'hold-out'})


def v1() -> pl.DataFrame:
    d = git_frame(RES + 'v1_vol_pricing/name_cycles.parquet')
    return std(d.select(_d('D').alias('date'), pl.col('issue_type').fill_null('stock').alias('inst'), _split().alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' '), pl.col('E').cast(pl.Utf8), pl.lit(' '), pl.col('K').cast(pl.Utf8), pl.lit(' straddle')]).alias('contract'),
                        (pl.col('mid') * 100).alias('cost'), pl.col('short_pnl_adv').alias('pnl'), pl.lit('held to expiration').alias('reason')))


def v2(leg: str) -> pl.DataFrame:
    d = git_frame(RES + 'v2_earnings_vol/trades.parquet').filter(pl.col(f'{leg}_status') == 'ok')
    cost = pl.col(f'{leg}_pnl_adv') / pl.col(f'{leg}_r_adv')
    return std(d.select(_d('P0' if leg == 'a' else 'P5').alias('date'), pl.lit('single names').alias('inst'), _split().alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' '), pl.col('E').cast(pl.Utf8), pl.lit(' '), pl.col(f'{leg}_K').cast(pl.Utf8)]).alias('contract'),
                        cost.alias('cost'), pl.col(f'{leg}_pnl_adv').alias('pnl'), pl.lit('closed after the report' if leg == 'a' else 'closed at the report').alias('reason')))


def v3() -> pl.DataFrame:
    d = git_frame(RES + 'v3_single_name_0dte/trades.parquet').filter(pl.col('a_status') == 'ok')
    return std(d.select(_d().alias('date'), pl.col('symbol').alias('inst'), _split().alias('period'),
                        pl.concat_str([pl.col('symbol'), pl.lit(' 10:00 short straddle '), pl.col('K').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('straddle_mid') * 100).alias('cost'), (pl.col('a_r_adv') * pl.col('straddle_mid') * 100).alias('pnl'),
                        pl.lit('bought back 15:50').alias('reason')))


def v8() -> pl.DataFrame:
    d = git_frame(RES + 'v8_monthend/trades.parquet')
    return std(d.select(_d().alias('date'), pl.col('root').alias('inst'), pl.lit('2017-06→2022 (unread chains)').alias('period'),
                        pl.concat_str([pl.col('root'), pl.lit(' 13:00 long straddle '), pl.col('K').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('mid') * 100).alias('cost'), (pl.col('r_adv') * pl.col('mid') * 100).alias('pnl'), pl.lit('held to settlement').alias('reason')))


# ---- #9 lifecycle portfolios P1, P2 --------------------------------------------------------------------------------------------------------

def portfolio(name: str) -> pl.DataFrame:
    fr = []
    for per, lab in (('devval', 'development + validation'), ('holdout', 'hold-out 2025-10→2026-10')):
        d = git_frame(f'research/compass/lifecycle/results/portfolio/{name}_{per}_trades.parquet').with_columns(pl.lit(lab).alias('per'))
        fr.append(d)
    d = pl.concat(fr, how='diagonal_relaxed').filter(pl.col('status') == 'filled')
    cost = pl.when(pl.col('risk') > 0).then(pl.col('risk')).otherwise(pl.col('cost_unit').abs() * pl.col('units'))
    return std(d.select(_d().alias('date'), pl.col('root').alias('inst'), pl.col('per').alias('period'),
                        pl.concat_str([pl.col('root'), pl.lit(' '), pl.col('structure'), pl.lit(' m'), pl.col('m').cast(pl.Utf8)]).alias('contract'),
                        cost.alias('cost'), pl.col('pnl'), pl.col('closed_by').alias('reason')))


def seeded_baseline(path: str, extra=None, cost='entry_ask', structure_cost=None) -> str:
    """the study's own matched random controls (seeds 11–15, the signal is seed 0): their mean, for the section text"""
    d = git_frame(RES + path).filter((pl.col('status') == 'filled') & (pl.col('seed') != 0))
    if extra is not None:
        d = d.filter(extra)
    c = pl.col(cost) * 100
    m = d.select(pl.len().alias('n'), pl.col('pnl').mean().alias('usd'), (100 * pl.col('pnl') / c).mean().alias('pct'),
                 pl.col('seed').n_unique().alias('k')).row(0, named=True)
    return (f"the study's matched random controls ({m['k']} seeds, same symbols, sessions and exits, {m['n']:,} trades): "
            f"mean {m['usd']:+.2f} dollars and {m['pct']:+.2f}% a trade (no percentile was computed).").replace('-', '−')
