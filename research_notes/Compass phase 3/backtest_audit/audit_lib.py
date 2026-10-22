"""
audit_lib.py — the shared pieces of the backtest audit: the replay's rows read back (never written), the official
closes (Theta EOD, UW daily), the calendar, the macro events, the periods, and the session-level statistics.

It reads files only. No vendor call, no write outside this folder's out/ (the callers write). Every random draw is
seeded. Plain numpy / polars; POLARS_MAX_THREADS=1 is expected from the caller's environment.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / 'out'
SOURCE = 'backtest-parquet'
KEYS = ('condor_em1', 'fly5', 'condor_d20')
NAMES = {'condor_em1': ('SPY',), 'fly5': ('SPY', 'QQQ'), 'condor_d20': ('SPY',)}
STRUCTS = {'condor_em1': ('condor',), 'fly5': ('iron', 'call', 'put'), 'condor_d20': ('condor',)}
MINUTES = {'condor_em1': ('11:30', '12:00', '12:30', '13:00', '13:30'), 'fly5': ('15:00', '15:30'),
           'condor_d20': ('13:00', '13:30', '14:00', '14:30', '15:00')}
FEE = 0.65                      # a contract, as paper_tracker.FEE
CONTRACTS = 4                   # every structure here is four contracts (condor 1+1+1+1, iron fly 1+1+1+1, call/put fly 1+2+1)
BOOT_N = 2000
SEED = 20261022
HIST_START, HIST_END, FORWARD_START = '2022-11-11', '2026-10-09', '2026-10-12'

# ---- the periods (research notes; see AUDIT.md section 5) ------------------------------------------------------------------------------

PERIODS = {
    'condor_em1': [
        ('i', 'development: hyp_b fit (the pre-registration picked the VIX-mid cell; this all-VIX parent ranked 4th)', '2022-11-11', '2024-12-31'),
        ('ii', 'selection read: hyp_b OOS, read once; the tracked all-VIX form was written after it', '2025-01-02', HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
    'fly5': [
        ('i', 'development: hyp_c fit (C pre-registered 15:00 iron ±2, call ±2, call ±5 — not these cells)', '2022-11-11', '2024-12-31'),
        ('ii', 'selection read: hyp_c OOS — the iron ±5 found post hoc on it; the 15:30 call ±5 named after it (hyp_f)', '2025-01-02', HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
    'condor_d20': [
        ('i-a', 'model training: the frozen t2 model was fit on these sessions — its deciles here are IN-SAMPLE', '2022-11-11', '2024-06-30'),
        ('i-b', 'decile cuts: the nine cuts are this half-year\'s score quantiles (still hyp_e\'s fit period)', '2024-07-01', '2024-12-31'),
        ('ii', 'selection read: hyp_e OOS — out of the model\'s training, read before the candidate was set', '2025-01-02', HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
}


def period_of(key: str, day: str) -> str | None:
    for p, _, a, b in PERIODS[key]:
        if day >= a and (b is None or day <= b):
            return p
    return None


# ---- the exchange calendar (NYSE; written out, checked against Theta's EOD dates) ------------------------------------------------------

NYSE_HOLIDAYS = frozenset('''
2022-01-17 2022-02-21 2022-04-15 2022-05-30 2022-06-20 2022-07-04 2022-09-05 2022-11-24 2022-12-26
2023-01-02 2023-01-16 2023-02-20 2023-04-07 2023-05-29 2023-06-19 2023-07-04 2023-09-04 2023-11-23 2023-12-25
2024-01-01 2024-01-15 2024-02-19 2024-03-29 2024-05-27 2024-06-19 2024-07-04 2024-09-02 2024-11-28 2024-12-25
2025-01-01 2025-01-09 2025-01-20 2025-02-17 2025-04-18 2025-05-26 2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25
2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03 2026-09-07 2026-11-26 2026-12-25
'''.split())
NYSE_HALF_DAYS = frozenset('''
2022-11-25 2023-07-03 2023-11-24 2024-07-03 2024-11-29 2024-12-24 2025-07-03 2025-11-28 2025-12-24 2026-11-27 2026-12-24
'''.split())


def weekdays(a: str, b: str) -> list[str]:
    d, e, out = dt.date.fromisoformat(a), dt.date.fromisoformat(b), []
    while d <= e:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def expected_sessions(a: str, b: str) -> list[str]:
    """full NYSE sessions (half days out, as the reports and the tracker skip them)"""
    return [d for d in weekdays(a, b) if d not in NYSE_HOLIDAYS and d not in NYSE_HALF_DAYS]


# ---- the replay's rows ---------------------------------------------------------------------------------------------------------------

NUM = ('spot', 'k0', 'straddle', 'wing', 'price_nbbo', 'price_mid', 'price_1c', 'price_2c', 'max_risk', 'settle_px', 'close_1m_r',
       'close_official', 'payoff', 'pnl_nbbo', 'pnl_mid', 'pnl_1c', 'pnl_2c', 'liq_nbbo', 'liq_mid', 'legs_closed', 'fees_close',
       'pnl_1558_nbbo', 'pnl_1558_mid') + tuple(f'l{i}_{x}' for i in range(1, 5) for x in ('bid', 'ask', 'qty', 'bid_size', 'ask_size',
                                                                                           'bid_1558', 'ask_1558'))


def row_files(root: Path, keys=KEYS) -> list[Path]:
    out = []
    for k in keys:
        for nm in NAMES[k]:
            d = Path(root) / k / nm
            out += sorted(d.glob('*.parquet')) if d.is_dir() else []
    return out


def load_rows(root: Path, keys=KEYS, start: str | None = None, end: str | None = None) -> pl.DataFrame:
    """every replay row (capture, close1558, settle) of the candidates, source = backtest-parquet, numbers as Float64
    in `<col>_f` columns beside the strings"""
    frames = []
    for f in row_files(root, keys):
        if (start and f.stem < start) or (end and f.stem > end):
            continue
        frames.append(pl.read_parquet(f).with_columns(pl.lit(str(f.relative_to(root))).alias('_file')))
    if not frames:
        return pl.DataFrame()
    df = pl.concat(frames, how='diagonal_relaxed')
    df = df.filter(pl.col('source') == SOURCE)
    df = df.with_columns([pl.col(c).cast(pl.Float64, strict=False).alias(f'{c}_f') for c in NUM if c in df.columns])
    return df


def legs_of(row: dict) -> list[tuple[str, float, str, int]]:
    """(right C|P, strike, side, qty) from a capture row's OCC symbols"""
    out = []
    for i in range(1, 5):
        s = row.get(f'l{i}_symbol')
        if not s:
            continue
        body = s[-15:]
        out.append((body[6], round(int(body[7:]) / 1000.0, 3), row[f'l{i}_side'], int(float(row[f'l{i}_qty']))))
    return out


def intrinsic(px: float, k: float, right: str) -> float:
    return max(px - k, 0.0) if right == 'C' else max(k - px, 0.0)


def payoff(legs, px: float) -> float:
    """points a unit at expiry: + what the longs pay, − what the shorts cost"""
    return sum((1 if side == 'long' else -1) * q * intrinsic(px, k, r) for r, k, side, q in legs)


def trades(df: pl.DataFrame) -> pl.DataFrame:
    """one row a TRADE: a tradable capture joined to its settle row (official settle_source) and, for fly5, its 15:58
    row. Columns: key, name, day, minute, structure, legs (json), entry prices, the replay's settle and P&L."""
    caps = df.filter((pl.col('row_kind') == 'capture') & (pl.col('tradable') == 'true'))
    sett = df.filter(pl.col('row_kind') == 'settle')
    on = ['candidate', '_name', '_day', 'minute', 'structure']
    keep_s = sett.select(on + ['settle_source', 'settle_px_f', 'close_1m_r_f', 'close_official_f', 'pnl_nbbo_f', 'pnl_mid_f', 'pnl_1c_f',
                               'pnl_2c_f', 'payoff_f'] + [c for c in ('pnl_1558_nbbo_f', 'pnl_1558_mid_f', 'legs_closed_f') if c in sett.columns])
    t = caps.join(keep_s, on=on, how='left', suffix='_s')
    return t


# ---- official closes ---------------------------------------------------------------------------------------------------------------------

def theta_eod(symbols=('SPY', 'QQQ'), lake: Path = REPO / 'data_lake' / 'thetadata' / 'stock_eod') -> pl.DataFrame:
    """Theta's EOD daily bar: (symbol, day, close_theta); the day is the report's New York date (Theta writes it ~17:15)"""
    fs = sorted(glob.glob(str(lake / 'year=*' / '*.parquet')))
    parts = [pl.scan_parquet(f).filter(pl.col('symbol').is_in(list(symbols))).select('symbol', 'created', 'last_trade', 'close').collect() for f in fs]
    e = pl.concat(parts)
    e = e.with_columns(pl.col('created').dt.strftime('%Y-%m-%d').alias('day'), pl.col('last_trade').dt.strftime('%Y-%m-%d').alias('day_lt'))
    return e.select('symbol', 'day', 'day_lt', pl.col('close').alias('close_theta'))


def uw_daily(symbols=('SPY', 'QQQ'), lake: Path = REPO / 'data_lake' / 'unusualwhales') -> pl.DataFrame:
    fs = sorted(glob.glob(str(lake / 'ohlc__1d.part0*.parquet')))
    u = pl.concat([pl.scan_parquet(f).filter(pl.col('ticker').is_in(list(symbols)) & (pl.col('market_time') == 'r')).collect() for f in fs])
    return u.select(pl.col('ticker').alias('symbol'), pl.col('date').alias('day'), pl.col('close').cast(pl.Float64).alias('close_uw')).unique()


# ---- macro events ------------------------------------------------------------------------------------------------------------------------

def macro_days(path: Path = REPO / 'data' / 'macro_events_2022_2027.json') -> dict[str, set]:
    ev = json.loads(Path(path).read_text(encoding='utf-8'))
    out: dict[str, set] = {}
    for e in ev:
        out.setdefault(e['date'], set()).add(e['event'])
    return out


# ---- statistics --------------------------------------------------------------------------------------------------------------------------

def block_draws(n: int, block: int, B: int = BOOT_N, seed: int = SEED) -> np.ndarray:
    """B × n session indices by the moving-block bootstrap (overlapping blocks of `block` consecutive sessions, starts
    uniform on 0 .. n − block, concatenated and cut to n); block 1 = the iid session bootstrap"""
    rng = np.random.default_rng(seed + 7919 * block)
    if n == 0:
        return np.zeros((B, 0), int)
    b = max(1, min(block, n))
    k = int(math.ceil(n / b))
    starts = rng.integers(0, n - b + 1, (B, k))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(B, k * b)[:, :n]
    return idx


def weights_from(idx: np.ndarray, n: int) -> np.ndarray:
    W = np.zeros((idx.shape[0], n))
    for b in range(idx.shape[0]):
        W[b] = np.bincount(idx[b], minlength=n)
    return W


def pct_ci(x: np.ndarray) -> tuple[float, float]:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float('nan'), float('nan')
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def session_stats(S: np.ndarray, N: np.ndarray, blocks=(1, 5, 20)) -> dict:
    """S, N: per session (calendar order, every session the candidate ran, zero where it took no trade) the summed P&L and
    the trade count. → the session mean and the per-trade mean (Σ S / Σ N) with percentile CIs by the iid session
    bootstrap (block 1) and the moving-block bootstrap (blocks 5, 20); the lag-1..5 autocorrelation; effective N"""
    n = S.size
    out = {'sessions': int(n), 'sessions_traded': int((N > 0).sum()), 'trades': int(N.sum())}
    if n == 0 or N.sum() == 0:
        return out
    out['mean_session'] = float(S.mean())
    out['mean_trade'] = float(S.sum() / N.sum())
    var = {}
    for b in blocks:
        if n < 3 * b:                       # too few sessions for blocks this long: no interval
            out[f'ci_session_b{b}'] = out[f'ci_trade_b{b}'] = (float('nan'), float('nan'))
            continue
        W = weights_from(block_draws(n, b), n)
        ms = (W @ S) / n
        mt = (W @ S) / np.maximum(W @ N, 1)
        out[f'ci_session_b{b}'] = pct_ci(ms)
        out[f'ci_trade_b{b}'] = pct_ci(mt)
        var[b] = float(np.var(ms))
    x = S - S.mean()
    den = float((x * x).sum())
    ac = [float((x[:-k] * x[k:]).sum() / den) if den > 0 and n > k else float('nan') for k in range(1, 6)]
    out['acf'] = ac
    out['n_eff_acf'] = float(n / max(1e-9, 1 + 2 * sum((1 - k / n) * a for k, a in enumerate(ac, 1) if math.isfinite(a))))
    out['n_eff_block20'] = float(n * var[1] / var[20]) if 1 in var and 20 in var and var[20] > 0 else float('nan')
    return out


def drawdown(seq: np.ndarray) -> float:
    if seq.size == 0:
        return float('nan')
    c = np.cumsum(seq)
    peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    return float((peak - c).max())


def losing_streak(seq: np.ndarray) -> int:
    best = cur = 0
    for v in seq:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return best


def f(x, fmt='{:+.2f}'):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    return fmt.format(x)


def ci(t, fmt='{:+.2f}'):
    if not t or any((v is None or not math.isfinite(v)) for v in t):
        return '—'
    return f'[{fmt.format(t[0])}, {fmt.format(t[1])}]'
