"""Tables for the lifecycle reports (deliverables 3-8), from the stage-1 rows and the grid's daily sums. Development and
validation only: nothing here opens the hold-out (lc.runner.HOLDOUT_START).

Units: one unit of a structure (one contract per leg). $ figures are per unit after fees; '% of premium' is P&L over
|open cost| (the debit paid, or the credit taken); a trade-level percentage is averaged over trades (equal weight), a
cell-level 'return on premium' is sum(P&L) / sum(|cost|)."""
from __future__ import annotations
import numpy as np
import polars as pl
from . import analyze as an

def rows_to_daily(rows: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    f = rows.filter(pl.col('filled') > 0)
    f = f.with_columns((pl.col('pnl') > 0).cast(pl.Int32).alias('w'))
    return f.group_by(keys + ['session']).agg([
        pl.len().alias('n'), pl.col('w').sum().alias('wins'), pl.col('pnl').sum(), (pl.col('pnl') ** 2).sum().alias('pnl_sq'),
        pl.when(pl.col('pnl') > 0).then(pl.col('pnl')).otherwise(0).sum().alias('win_pnl'),
        pl.when(pl.col('pnl') < 0).then(pl.col('pnl')).otherwise(0).sum().alias('loss_pnl'),
        pl.col('cost0').abs().sum().alias('cost'), pl.col('capital_peak').sum().alias('capital'), pl.col('hold_min').sum().alias('hold'),
        pl.col('fees').sum()])

def trade_level(rows: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Distribution figures that need individual trades: mean and median % of premium, deciles, tails, Result A."""
    f = rows.filter(pl.col('filled') > 0).with_columns((pl.col('pnl') / pl.col('cost0').abs()).alias('ret'))
    return f.group_by(keys).agg([
        pl.col('ret').mean().alias('mean_pct'), pl.col('ret').median().alias('median_pct'),
        pl.col('ret').quantile(0.05).alias('p05_pct'), pl.col('ret').quantile(0.95).alias('p95_pct'),
        pl.col('pnl').median().alias('median_usd'), pl.col('pnl').min().alias('worst_usd'), pl.col('pnl').quantile(0.01).alias('p01_usd'),
        (pl.col('mfe_liq') / pl.col('cost0').abs()).mean().alias('mfe_pct'),
        (pl.col('mfe_liq') / pl.col('cost0').abs()).median().alias('mfe_pct_med'),
        ((pl.col('mfe_liq') / pl.col('cost0').abs()) >= 0.5).mean().alias('share_mfe50'),
        ((pl.col('mfe_liq') / pl.col('cost0').abs()) >= 1.0).mean().alias('share_mfe100'),
        (pl.col('mae_liq') / pl.col('cost0').abs()).mean().alias('mae_pct'),
        pl.col('t_mfe').median().alias('t_mfe_med'), pl.col('t_mae').median().alias('t_mae_med'),
        (pl.col('mfe_mark') / pl.col('cost0').abs()).mean().alias('mfe_mid_pct'),
        pl.col('rel_spread').median().alias('rel_spread_med'), pl.col('cost0').abs().median().alias('cost_med'),
    ])

def fmt_table(df: pl.DataFrame, cols: list[tuple[str, str, str]]) -> str:
    """cols: (column, header, format) with format 'usd', 'pct', 'int', 'num', 'str'."""
    def f(v, kind):
        if v is None or (isinstance(v, float) and not np.isfinite(v)): return '—'
        if kind == 'usd': return f'{v:+,.2f}'
        if kind == 'pct': return f'{100 * v:+.1f}%'
        if kind == 'rate': return f'{100 * v:.1f}%'
        if kind == 'int': return f'{int(v):,}'
        if kind == 'num': return f'{v:.2f}'
        return str(v)
    head = '| ' + ' | '.join(h for _, h, _ in cols) + ' |'
    sep = '|' + '|'.join('---' if k == 'str' else '---:' for _, _, k in cols) + '|'
    lines = [head, sep]
    for r in df.iter_rows(named=True):
        lines.append('| ' + ' | '.join(f(r.get(c), k) for c, _, k in cols) + ' |')
    return '\n'.join(lines)
