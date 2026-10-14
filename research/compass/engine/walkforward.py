"""Chronological walk-forward over a set of candidate configurations (04_protocol.md §6, §8-§9).

Every candidate configuration is run once over the whole period by run.run_family (its trades carry the session date).
Selection for test year Y uses ONLY trades from sessions before Y minus the embargo, by the pre-specified objective;
the selected configuration's trades in year Y are the out-of-sample result. Because each configuration's trades are
fixed before selection, the procedure cannot peek: the selection statistic never sees year Y.

objective: 'lb' = day-clustered lower 95% bound of net expectancy per trade (requires >= min_trades on the training
window), 'mean' = net expectancy, 'ep_ewd' = mean net P&L / mean MAE (the owner's ranking quantity).
"""
from __future__ import annotations
import datetime as dt
import json, os
import numpy as np
import polars as pl
from . import calendar as cal, stats

def load_trades(result_dir: str) -> pl.DataFrame:
    t = pl.read_parquet(os.path.join(result_dir, 'trades.parquet'))
    return t.filter(pl.col('status') == 'filled').with_columns(pl.col('session').dt.year().alias('year'))

def objective(trades: pl.DataFrame, kind: str, min_trades: int, n_boot: int = 2000) -> float:
    if trades.height < min_trades: return -np.inf
    pnl = trades['pnl'].to_numpy(); days = trades['session'].cast(pl.Utf8).to_numpy()
    if kind == 'mean': return float(pnl.mean())
    if kind == 'ep_ewd':
        mae = trades['mae'].to_numpy(); return float(pnl.mean() / mae.mean()) if mae.mean() > 0 else -np.inf
    m, lo, hi = stats.cluster_bootstrap_ci(pnl, days, n_boot=n_boot)
    return lo

def walk_forward(candidates: dict[str, pl.DataFrame], years: list[int], objective_kind: str = 'lb', min_trades: int = 150,
                 min_train_years: int = 2, embargo_sessions: int = 5) -> dict:
    """candidates: config name -> filled trades (with 'year' and 'session'). Returns per-fold selections and the pooled
    out-of-sample trade table."""
    folds = []; oos = []
    all_years = sorted({y for t in candidates.values() for y in t['year'].unique().to_list()})
    for Y in years:
        train_years = [y for y in all_years if y < Y]
        if len(train_years) < min_train_years: folds.append({'test_year': Y, 'skipped': f'fewer than {min_train_years} training years'}); continue
        cutoff = cal.prev_session(dt.date(Y, 1, 1), embargo_sessions)
        scores = {}
        for name, t in candidates.items():
            tr = t.filter(pl.col('session') <= cutoff)
            scores[name] = objective(tr, objective_kind, min_trades)
        best = max(scores, key=scores.get)
        if not np.isfinite(scores[best]): folds.append({'test_year': Y, 'skipped': 'no candidate reached the minimum training trades', 'scores': scores}); continue
        test = candidates[best].filter(pl.col('year') == Y).with_columns(pl.lit(best).alias('config'), pl.lit(Y).alias('fold'))
        s = stats.summary(test) if test.height else {'n': 0}
        folds.append({'test_year': Y, 'selected': best, 'train_score': scores[best], 'train_trades': int(candidates[best].filter(pl.col('session') <= cutoff).height),
                      'test': {k: s.get(k) for k in ('n', 'days', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'profit_factor', 'max_drawdown', 'net_total')}, 'scores': {k: (None if not np.isfinite(v) else v) for k, v in scores.items()}})
        if test.height: oos.append(test)
    pooled = pl.concat(oos, how='diagonal_relaxed') if oos else pl.DataFrame()
    out = {'objective': objective_kind, 'min_trades': min_trades, 'embargo_sessions': embargo_sessions, 'folds': folds}
    if pooled.height:
        out['oos'] = stats.summary(pooled)
        out['oos_by_year'] = stats.by_group(pooled, ['year']).to_dicts()
    return out, pooled

def run(result_dirs: dict[str, str], years: list[int], out_path: str, **kw) -> dict:
    cands = {name: load_trades(d) for name, d in result_dirs.items()}
    res, pooled = walk_forward(cands, years, **kw)
    json.dump(res, open(out_path, 'w'), indent=1, default=str)
    if pooled.height: pooled.write_parquet(out_path.replace('.json', '_oos_trades.parquet'))
    return res
