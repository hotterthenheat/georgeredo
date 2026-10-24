"""lib_final.py — Compass Final's statistics (PREREG_COMPASS_FINAL.md sections 6 and 8), one function for every test.

A test's trade frame has one row a trade with at least:
  date (YYYY-MM-DD, the entry session), entry (HH:MM), inst (a label), cost ($ base of the unit: max risk x 100, credit x 100,
  or notional), pnl ($ at Robinhood's fees under the primary settlement), pnl_old ($ at the study's own fees, the same
  settlement), and any number of `line_<name>` columns ($ at Robinhood's fees under a reported settlement line).
`sessions` is the test's in-test calendar sessions (the S_i are taken over all of them, zero where nothing traded).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

K_TESTS = 7
ALPHA = 0.05 / K_TESTS                 # two-sided 1 - 0.05/7 interval: lower end at the 100 * ALPHA / 2 = 0.357th percentile
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = SP / 'compass_final'


def block_ci(S: np.ndarray, N: np.ndarray) -> dict:
    """the per-trade mean (sum S / sum N) and its block-20 percentile intervals: 95 % and the Bonferroni 1 - 0.05/7"""
    n = S.size
    out = {'sessions': int(n), 'trades': int(N.sum()), 'mean': float(S.sum() / N.sum()) if N.sum() else float('nan')}
    if n < 60 or N.sum() == 0:
        out['ci95'] = out['ci_bonf'] = (float('nan'), float('nan'))
        return out
    W = AL.weights_from(AL.block_draws(n, 20), n)
    mt = (W @ S) / np.maximum(W @ N, 1)
    out['ci95'] = AL.pct_ci(mt)
    out['ci_bonf'] = (float(np.percentile(mt, 100 * ALPHA / 2)), float(np.percentile(mt, 100 * (1 - ALPHA / 2))))
    return out


def session_arrays(t: pl.DataFrame, sessions: list[str], col: str) -> tuple[np.ndarray, np.ndarray]:
    g = t.group_by('date').agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
    m = {d: (s, n) for d, s, n in g.iter_rows()}
    S = np.array([m.get(d, (0.0, 0))[0] for d in sessions], float)
    N = np.array([m.get(d, (0.0, 0))[1] for d in sessions], float)
    return S, N


def walk_1lot(t: pl.DataFrame) -> dict:
    """$1,000 plus the cumulative $ P&L of one lot a trade, entry order"""
    x = t.sort(['date', 'entry', 'inst'])
    bal = 1000.0 + np.cumsum(x['pnl'].to_numpy())
    below = np.where(bal <= 0)[0]
    return {'end': float(bal[-1]) if bal.size else 1000.0, 'min': float(min(1000.0, bal.min())) if bal.size else 1000.0,
            'first_at_or_below_0': x['date'][int(below[0])] if below.size else None}


def walk_10pct(t: pl.DataFrame) -> dict:
    """the final report's method B: each trade gets 10 % of the balance at its session's start (100 % / n when a session
    holds more than ten trades); the trade's return is pnl / cost"""
    bal, low, gone = 1000.0, 1000.0, None
    for d, g in t.sort(['date', 'entry']).group_by('date', maintain_order=True):
        r = (g['pnl'] / g['cost']).to_numpy()
        w = min(0.10, 1.0 / len(r))
        bal = bal * (1 + w * r.sum())
        if bal <= 0 and gone is None:
            gone = d[0]
            bal = 0.0
        low = min(low, bal)
        if bal <= 0:
            break
    return {'end': float(bal), 'min': float(low), 'wiped_out_on': gone}


def drawdowns(t: pl.DataFrame, sessions: list[str]) -> dict:
    x = t.sort(['date', 'entry', 'inst'])
    c = np.cumsum(x['pnl'].to_numpy())
    peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    maxdd = float((peak - c).max()) if c.size else 0.0
    # the longest drawdown in sessions: from a session-end peak to the next new high (or the end)
    g = x.group_by('date', maintain_order=True).agg(pl.col('pnl').sum())
    daily = dict(zip(g['date'].to_list(), g['pnl'].to_list()))
    cum, hi, peak_i, longest = 0.0, 0.0, -1, 0          # the start (balance 0) is the first peak
    for i, d in enumerate(sessions):
        cum += daily.get(d, 0.0)
        if cum >= hi - 1e-9:                             # a new high (or equal): the drawdown since peak_i is over
            longest = max(longest, i - peak_i - 1)
            hi, peak_i = cum, i
    longest = max(longest, len(sessions) - 1 - peak_i)   # still under water at the end
    return {'max_dd_usd': maxdd, 'longest_dd_sessions': int(longest)}


def describe(t: pl.DataFrame, sessions: list[str], unit: str) -> dict:
    """everything section 8 asks for, at Robinhood's fees under the primary settlement"""
    if t.height == 0:
        return {'unit': unit, 'trades': 0, 'sessions_in_test': len(sessions), 'sessions_traded': 0, 'mean_pct': float('nan'),
                'ci95': (float('nan'), float('nan')), 'ci_bonf': (float('nan'), float('nan')), 'total_usd': 0.0, 'top5_share': float('nan'),
                'win_rate': float('nan'), 'by_year': [], 'by_weekday': [], 'by_time': [], 'by_inst': [], 'empty': True}
    t = t.with_columns((pl.col('pnl') / pl.col('cost') * 100).alias('pct'))
    p = t['pnl'].to_numpy()
    pct = t['pct'].to_numpy()
    win = p > 0
    S, N = session_arrays(t, sessions, 'pct')
    st = block_ci(S, N)
    wins, losses = p[win].sum(), -p[~win].sum()
    best = t.sort('pnl', descending=True).row(0, named=True) if t.height else None
    worst = t.sort('pnl').row(0, named=True) if t.height else None
    sess_pnl = t.group_by('date').agg(pl.col('pnl').sum().alias('s')).sort('s', descending=True)
    total = float(p.sum())
    top5 = float(sess_pnl['s'].head(5).sum())
    out = {
        'unit': unit, 'trades': t.height, 'sessions_in_test': len(sessions), 'sessions_traded': t['date'].n_unique(),
        'mean_pct': st['mean'], 'ci95': st['ci95'], 'ci_bonf': st['ci_bonf'],
        'mean_usd': float(p.mean()) if p.size else float('nan'), 'total_usd': total,
        'win_rate': float(win.mean()) if p.size else float('nan'),
        'avg_win_pct': float(pct[win].mean()) if win.any() else float('nan'),
        'avg_loss_pct': float(pct[~win].mean()) if (~win).any() else float('nan'),
        'avg_win_usd': float(p[win].mean()) if win.any() else float('nan'),
        'avg_loss_usd': float(p[~win].mean()) if (~win).any() else float('nan'),
        'median_pct': float(np.median(pct)) if pct.size else float('nan'),
        'best': {k: best[k] for k in ('date', 'entry', 'inst', 'pnl', 'pct')} if best else None,
        'worst': {k: worst[k] for k in ('date', 'entry', 'inst', 'pnl', 'pct')} if worst else None,
        'profit_factor': float(wins / losses) if losses > 0 else float('inf'),
        'top5_share': (top5 / total) if total > 0 else float('nan'),
        **drawdowns(t, sessions),
        'walk_1lot': walk_1lot(t), 'walk_10pct': walk_10pct(t),
    }
    for key, col in (('by_year', pl.col('date').str.slice(0, 4)), ('by_weekday', pl.col('date').str.to_date().dt.strftime('%a')),
                     ('by_time', pl.col('entry')), ('by_inst', pl.col('inst'))):
        g = t.group_by(col.alias('k')).agg(pl.len().alias('n'), pl.col('pct').mean().alias('mean_pct'), (pl.col('pnl') > 0).mean().alias('win'),
                                           pl.col('pnl').sum().alias('usd')).sort('k')
        out[key] = g.to_dicts()
    return out


def verdict(d: dict) -> dict:
    """the five conditions of section 6"""
    years = d['by_year']
    neg_years = [y['k'] for y in years if not (y['mean_pct'] > 0)]
    c = {
        '1 mean > 0': bool(d['mean_pct'] > 0) if d['trades'] else False,
        '2 Bonferroni lower end > 0': bool(d['ci_bonf'][0] > 0) if not math.isnan(d['ci_bonf'][0]) else False,
        '3 top-5 share <= 100%': bool(d['total_usd'] > 0 and d['top5_share'] <= 1.0 + 1e-12),
        '4 >= 300 trades': bool(d['trades'] >= 300),
        '5 at most one year <= 0': bool(len(neg_years) <= 1),
    }
    return {'conditions': c, 'negative_years': neg_years, 'pass': all(c.values())}


def mean_line(t: pl.DataFrame, sessions: list[str], col: str) -> dict:
    """a reported line: the mean % and its 95 % block-20 interval for another $ column on the same trades"""
    x = t.filter(pl.col(col).is_not_null()).with_columns((pl.col(col) / pl.col('cost') * 100).alias('_p'))
    S, N = session_arrays(x, sessions, '_p')
    st = block_ci(S, N)
    return {'trades': x.height, 'mean_pct': st['mean'], 'ci95': st['ci95'], 'mean_usd': float(x[col].mean()) if x.height else float('nan'),
            'total_usd': float(x[col].sum()) if x.height else 0.0, 'win_rate': float((x[col] > 0).mean()) if x.height else float('nan')}


def mde(sd_trade: float, n_trades: int, sd_session: float, n_sessions: int) -> dict:
    from statistics import NormalDist
    z = NormalDist().inv_cdf(1 - ALPHA / 2) + NormalDist().inv_cdf(0.80)
    return {'mde_trade': z * sd_trade / math.sqrt(max(n_trades, 1)), 'mde_session': z * sd_session / math.sqrt(max(n_sessions, 1))}
