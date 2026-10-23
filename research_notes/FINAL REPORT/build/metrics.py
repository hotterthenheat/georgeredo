"""metrics.py — the one set of figures the final report prints for every strategy.

Input: a trade frame (polars) with the standard columns
    date      the entry session, 'YYYY-MM-DD' (New York)
    inst      the instrument the verdict is read on (SPY, QQQ, SPXW, ...)
    period    the study's own period label (exploration / check / holdout / forward / ...)
    contract  what was traded (OCC symbol, strikes, or the study's own label)
    cost      the base a trade's return is measured on, in dollars (> 0): the debit paid for a long option, the max
              risk for a spread, the notional of 100 shares for stock
    pnl       the trade's dollars after every fee, as the study filled it
    reason    the exit reason as the study recorded it ('' when the study records none)
and `unit` = 'premium' | 'risk' | 'stock'.  ret = 100 * pnl / cost (% of premium, % of max risk, or % of notional; for
stock the report also prints $ per 100 shares, which is pnl itself because every stock trade here is 100 shares).

Win = pnl > 0 after fees; a breakeven (pnl == 0) counts as a loss.
Interval: the 20-session moving-block bootstrap of audit_lib (research_notes/Compass phase 3/backtest_audit/audit_lib.py,
session_stats, 2,000 draws, its own seed), over every calendar session of the span in order (zero on a session with no
trade), for the mean $ a trade and the mean % a trade; none under 60 sessions (audit_lib's 3 x block rule).
Drawdown: on the cumulative $ of the session sums in calendar order; the longest drawdown is the longest run of
sessions (calendar sessions of the span) from a peak until the cumulative $ is back at or above it (or the span ends).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

SPY_DAYS = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta/data/underlying/SPY')
_CAL: list[str] | None = None


def calendar() -> list[str]:
    """every session with a stored SPY minute file (2012-06-01 → 2026-10-22), plus AL's full sessions after it"""
    global _CAL
    if _CAL is None:
        days = sorted(p.stem for p in SPY_DAYS.glob('*.parquet'))
        extra = [d for d in AL.expected_sessions('2026-10-23', '2026-12-31')]
        _CAL = days + extra
    return _CAL


def sessions_between(a: str, b: str, trade_days: set[str]) -> list[str]:
    cal = [d for d in calendar() if a <= d <= b]
    s = set(cal) | {d for d in trade_days if a <= d <= b}
    return sorted(s)


def _boot(S: np.ndarray, N: np.ndarray):
    st = AL.session_stats(S, N, blocks=(1, 20))
    return st.get('ci_trade_b20', (float('nan'), float('nan')))


def metrics(df: pl.DataFrame, unit: str, span: tuple[str, str] | None = None) -> dict:
    """the full set of figures for one instrument × period (or any slice)"""
    out: dict = {'unit': unit}
    if df.height == 0:
        out['trades'] = 0
        return out
    df = df.with_columns((100.0 * pl.col('pnl') / pl.col('cost')).alias('ret')).sort('date')
    pnl = df['pnl'].to_numpy().astype(float)
    ret = df['ret'].to_numpy().astype(float)
    win = pnl > 0
    out['trades'] = int(df.height)
    out['sessions_traded'] = int(df['date'].n_unique())
    out['win_rate'] = float(win.mean() * 100)
    out['avg_win_pct'] = float(ret[win].mean()) if win.any() else float('nan')
    out['avg_win_usd'] = float(pnl[win].mean()) if win.any() else float('nan')
    out['avg_loss_pct'] = float(ret[~win].mean()) if (~win).any() else float('nan')
    out['avg_loss_usd'] = float(pnl[~win].mean()) if (~win).any() else float('nan')
    out['median_pct'] = float(np.median(ret))
    out['median_usd'] = float(np.median(pnl))
    out['mean_pct'] = float(ret.mean())
    out['mean_usd'] = float(pnl.mean())
    out['total_usd'] = float(pnl.sum())
    out['mean_cost'] = float(df['cost'].mean())
    iw, il = int(np.argmax(pnl)), int(np.argmin(pnl))
    rw, rl = df.row(iw, named=True), df.row(il, named=True)
    out['best'] = (float(pnl[iw]), float(ret[iw]), rw['date'], str(rw['contract']))
    out['worst'] = (float(pnl[il]), float(ret[il]), rl['date'], str(rl['contract']))
    gp, gl = float(pnl[pnl > 0].sum()), float(-pnl[pnl < 0].sum())
    out['profit_factor'] = gp / gl if gl > 0 else float('inf')
    # sessions of the span, in calendar order
    days = set(df['date'].to_list())
    a, b = span if span else (min(days), max(days))
    sess = sessions_between(a, b, days)
    by = df.group_by('date').agg(pl.col('pnl').sum().alias('S'), pl.col('ret').sum().alias('R'), pl.len().alias('N'))
    m = {r['date']: (r['S'], r['R'], r['N']) for r in by.iter_rows(named=True)}
    S = np.array([m.get(d, (0.0, 0.0, 0))[0] for d in sess], float)
    R = np.array([m.get(d, (0.0, 0.0, 0))[1] for d in sess], float)
    N = np.array([m.get(d, (0.0, 0.0, 0))[2] for d in sess], float)
    out['sessions_span'] = len(sess)
    c = np.cumsum(S)
    peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    out['max_dd_usd'] = float((peak - c).max()) if c.size else float('nan')
    longest = cur = 0
    for v, p in zip(c, peak):
        cur = cur + 1 if v < p - 1e-9 else 0
        longest = max(longest, cur)
    out['longest_dd_sessions'] = int(longest)
    # share of the profit from the five best days
    day_sums = np.sort(by['S'].to_numpy().astype(float))[::-1]
    top5 = float(day_sums[:5].sum())
    out['top5_usd'] = top5
    out['top5_share'] = top5 / out['total_usd'] * 100 if out['total_usd'] > 0 else float('nan')
    out['without_top5_usd'] = out['total_usd'] - top5
    if len(sess) >= 60:
        out['ci_usd'] = _boot(S, N)
        out['ci_pct'] = _boot(R, N)
    else:
        out['ci_usd'] = out['ci_pct'] = (float('nan'), float('nan'))
    # exit reasons
    if 'reason' in df.columns:
        rs = df['reason'].fill_null('').cast(pl.Utf8).value_counts().sort('count', descending=True)
        out['reasons'] = [(r['reason'] or '(none recorded)', int(r['count']) / df.height * 100) for r in rs.iter_rows(named=True)]
    return out


def by_year(df: pl.DataFrame) -> list[dict]:
    if df.height == 0:
        return []
    df = df.with_columns((100.0 * pl.col('pnl') / pl.col('cost')).alias('ret'), pl.col('date').str.slice(0, 4).alias('year'))
    g = df.group_by('year').agg(pl.len().alias('n'), (pl.col('pnl') > 0).mean().alias('win'), pl.col('ret').mean().alias('mpct'),
                                pl.col('pnl').mean().alias('musd'), pl.col('pnl').sum().alias('tot')).sort('year')
    return g.to_dicts()


# ---- formatting ------------------------------------------------------------------------------------------------------------------------

def fnum(x, d=2, sign=True) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    s = f'{x:+,.{d}f}' if sign else f'{x:,.{d}f}'
    return s.replace('-', '−')


def fci(ci, d=2) -> str:
    if not ci or not all(isinstance(v, float) and math.isfinite(v) for v in ci):
        return 'n/a (< 60 sessions)'
    return f'[{fnum(ci[0], d)}, {fnum(ci[1], d)}]'
