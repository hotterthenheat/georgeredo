"""Walk-forward selection must never see the test year, and must pick the configuration that is best on the training
window by the stated objective. Synthetic trade tables with known per-year means."""
import datetime as dt, os, sys
import numpy as np
import polars as pl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import walkforward as wf, calendar as cal, stats

def _trades(year_means: dict[int, float], seed: int, n_per_year: int = 200) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for y, m in year_means.items():
        days = cal.sessions(dt.date(y, 1, 1), dt.date(y, 12, 31))
        for i in range(n_per_year):
            rows.append({'session': days[rng.integers(0, len(days))], 'pnl': m + rng.normal(0, 5), 'mae': abs(rng.normal(20, 5)), 'status': 'filled'})
    return pl.DataFrame(rows).with_columns(pl.col('session').dt.year().alias('year'))

def test_selection_uses_only_training_years():
    # config A is good in 2022-2023 and bad in 2024; config B the reverse. For test year 2024 the walk-forward must pick A
    # (best on 2022-2023) even though B is better in 2024: the selection cannot see 2024.
    A = _trades({2022: 3.0, 2023: 3.0, 2024: -3.0}, 1)
    B = _trades({2022: -3.0, 2023: -3.0, 2024: 3.0}, 2)
    res, pooled = wf.walk_forward({'A': A, 'B': B}, [2024], objective_kind='mean', min_trades=50, min_train_years=2)
    f = res['folds'][0]
    assert f['selected'] == 'A' and f['test']['mean'] < 0
    assert pooled['year'].unique().to_list() == [2024]

def test_embargo_and_minimums():
    A = _trades({2022: 1.0, 2023: 1.0, 2024: 1.0}, 3, n_per_year=60)
    res, _ = wf.walk_forward({'A': A}, [2023, 2024], objective_kind='lb', min_trades=100, min_train_years=1, embargo_sessions=5)
    assert 'skipped' in res['folds'][0]          # 60 training trades < 100
    assert res['folds'][1]['selected'] == 'A'    # 120 training trades
    assert res['folds'][1]['train_trades'] <= 120

def test_cluster_bootstrap_ci_contains_mean_and_widens_with_clustering():
    rng = np.random.default_rng(0)
    days = np.repeat(np.arange(50), 10)
    day_effect = rng.normal(0, 10, 50)[days]
    pnl = 2.0 + day_effect + rng.normal(0, 1, 500)
    m, lo, hi = stats.cluster_bootstrap_ci(pnl, days, n_boot=2000, seed=7)
    assert lo < m < hi and abs(m - pnl.mean()) < 1e-12
    # ignoring clusters (one cluster per trade) gives a narrower, over-confident interval
    m2, lo2, hi2 = stats.cluster_bootstrap_ci(pnl, np.arange(500), n_boot=2000, seed=7)
    assert (hi2 - lo2) < (hi - lo)

def test_summary_fields():
    t = _trades({2024: 5.0}, 4, n_per_year=300)
    s = stats.summary(t)
    assert s['n'] == 300 and s['days'] <= 252 and s['ci_lo'] < s['mean'] < s['ci_hi'] and 0 < s['win_rate'] <= 1 and s['max_drawdown'] <= 0
    assert len(s['worst_5_trades']) == 5 and s['worst_5_trades'] == sorted(s['worst_5_trades'])
