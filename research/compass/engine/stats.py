"""Statistics for trade tables: day-clustered bootstrap, summary metrics, grouped tables (04_protocol.md §7)."""
from __future__ import annotations
import numpy as np
import polars as pl

def cluster_bootstrap_ci(values: np.ndarray, clusters: np.ndarray, n_boot: int = 5000, seed: int = 7, alpha: float = 0.05) -> tuple[float, float, float]:
    """Mean and percentile CI of the mean, resampling clusters (trading days) with replacement."""
    values = np.asarray(values, float); clusters = np.asarray(clusters)
    if values.size == 0: return (np.nan, np.nan, np.nan)
    uniq, inv = np.unique(clusters, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=uniq.size); counts = np.bincount(inv, minlength=uniq.size).astype(float)
    rng = np.random.default_rng(seed)
    k = uniq.size
    idx = rng.integers(0, k, size=(n_boot, k))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return (float(values.mean()), float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2))))

def summary(trades: pl.DataFrame, pnl_col: str = 'pnl', day_col: str = 'session', n_boot: int = 5000, seed: int = 7) -> dict:
    if trades.height == 0: return {'n': 0}
    pnl = trades[pnl_col].to_numpy().astype(float); days = trades[day_col].cast(pl.Utf8).to_numpy()
    mean, lo, hi = cluster_bootstrap_ci(pnl, days, n_boot, seed)
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    daily = trades.group_by(day_col).agg(pl.col(pnl_col).sum().alias('d')).sort(day_col)['d'].to_numpy()
    cum = np.cumsum(daily); dd = cum - np.maximum.accumulate(cum)
    sd = daily.std(ddof=1) if daily.size > 1 else np.nan
    downside = daily[daily < 0].std(ddof=1) if (daily < 0).sum() > 1 else np.nan
    out = {
        'n': int(pnl.size), 'days': int(np.unique(days).size), 'net_total': float(pnl.sum()), 'mean': mean, 'ci_lo': lo, 'ci_hi': hi,
        'median': float(np.median(pnl)), 'win_rate': float((pnl > 0).mean()),
        'avg_win': float(wins.mean()) if wins.size else np.nan, 'avg_loss': float(losses.mean()) if losses.size else np.nan,
        'median_win': float(np.median(wins)) if wins.size else np.nan, 'median_loss': float(np.median(losses)) if losses.size else np.nan,
        'profit_factor': float(wins.sum() / -losses.sum()) if losses.size and losses.sum() < 0 else np.inf,
        'max_drawdown': float(dd.min()) if dd.size else 0.0,
        'worst_5_trades': [float(x) for x in np.sort(pnl)[:5]], 'worst_5_days': [float(x) for x in np.sort(daily)[:5]],
        'sharpe_daily_ann': float(daily.mean() / sd * np.sqrt(252)) if sd and sd > 0 else np.nan,
        'sortino_daily_ann': float(daily.mean() / downside * np.sqrt(252)) if downside and downside > 0 else np.nan,
    }
    for c in ('mae', 'mfe', 'commission', 'gross', 'hold_min'):
        if c in trades.columns:
            v = trades[c].to_numpy().astype(float)
            out[f'{c}_mean'] = float(np.nanmean(v)); out[f'{c}_p95'] = float(np.nanpercentile(v, 95))
    if 'gross' in trades.columns:
        g = float(trades['gross'].sum()); out['cost_share'] = float(trades['commission'].sum() / abs(g)) if g else np.nan
    return out

def by_group(trades: pl.DataFrame, keys: list[str], n_boot: int = 2000) -> pl.DataFrame:
    rows = []
    for k, sub in trades.group_by(keys, maintain_order=True):
        s = summary(sub, n_boot=n_boot)
        rows.append({**dict(zip(keys, k if isinstance(k, tuple) else (k,))), 'n': s['n'], 'days': s['days'], 'mean': s['mean'], 'ci_lo': s['ci_lo'], 'ci_hi': s['ci_hi'], 'win_rate': s['win_rate'], 'profit_factor': s['profit_factor'], 'max_drawdown': s['max_drawdown'], 'net_total': s['net_total']})
    return pl.DataFrame(rows) if rows else pl.DataFrame()

def paired_difference_ci(a: np.ndarray, b: np.ndarray, clusters: np.ndarray, n_boot: int = 5000, seed: int = 7) -> tuple[float, float, float]:
    return cluster_bootstrap_ci(np.asarray(a, float) - np.asarray(b, float), clusters, n_boot, seed)
