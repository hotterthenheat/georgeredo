"""Shared helpers for the gex-regime / exit-engine research. Reuses the backtest package read-only."""
import os, sys, json, gzip, csv, datetime
import numpy as np
BT = '/home/user/georgeredo/backtest'
sys.path.insert(0, BT)
import data, exits, costs  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
START, END, SPLIT = '2025-06-02', '2026-10-09', '2026-03-02'
TICKERS = ('SPY', 'QQQ', 'IWM')
DAYS_ALL = json.load(open(BT + '/trading_days.json'))
DAYS = [d for d in DAYS_ALL if START <= d <= END]

def prior_day(d):
    i = DAYS_ALL.index(d)
    return DAYS_ALL[i - 1] if i > 0 else None

def hhmm(t):
    return t.hour * 60 + t.minute

def px_at(rth, minute_of_day, field='c'):
    """Close (default) of the 1-minute bar starting at minute_of_day; None if that bar is missing."""
    for b in rth:
        m = hhmm(b['t'])
        if m == minute_of_day: return b[field]
        if m > minute_of_day: return None
    return None

def bar_index_at_or_after(rth, minute_of_day):
    for i, b in enumerate(rth):
        if hhmm(b['t']) >= minute_of_day: return i
    return None

def boot_mean_ci(v, groups=None, n_boot=2000, seed=7):
    """95% bootstrap CI of the mean. If groups is given, resample whole groups (daily blocks)."""
    rng = np.random.default_rng(seed)
    v = np.asarray(v, dtype=float)
    if len(v) < 3: return (float('nan'), float('nan'))
    if groups is None:
        idx = rng.integers(0, len(v), size=(n_boot, len(v)))
        m = v[idx].mean(axis=1)
    else:
        g = np.asarray(groups); ug, inv = np.unique(g, return_inverse=True)
        sums = np.bincount(inv, weights=v, minlength=len(ug)); cnt = np.bincount(inv, minlength=len(ug)).astype(float)
        idx = rng.integers(0, len(ug), size=(n_boot, len(ug)))
        m = sums[idx].sum(axis=1) / cnt[idx].sum(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def ols_slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm = x - x.mean(); ym = y - y.mean()
    d = (xm * xm).sum()
    return float((xm * ym).sum() / d) if d > 0 else float('nan')

def boot_slope_ci(x, y, groups, n_boot=2000, seed=7):
    """Daily-block bootstrap CI for an OLS slope (resample whole dates)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); y = np.asarray(y, float); g = np.asarray(groups)
    ug, inv = np.unique(g, return_inverse=True)
    members = [np.where(inv == k)[0] for k in range(len(ug))]
    out = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(ug), size=len(ug))
        idx = np.concatenate([members[k] for k in pick])
        out.append(ols_slope(x[idx], y[idx]))
    out = np.array(out)
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))

def spearman(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    if rx.std() == 0 or ry.std() == 0: return float('nan')
    return float(np.corrcoef(rx, ry)[0, 1])

def boot_stat_ci(fn, arrays, groups, n_boot=1000, seed=7):
    rng = np.random.default_rng(seed)
    g = np.asarray(groups); ug, inv = np.unique(g, return_inverse=True)
    members = [np.where(inv == k)[0] for k in range(len(ug))]
    out = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(ug), size=len(ug))
        idx = np.concatenate([members[k] for k in pick])
        out.append(fn(*[a[idx] for a in arrays]))
    out = np.array(out, float)
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))

def write_csv(path, rows, fields=None):
    if not rows: open(path, 'w').write(''); return
    fields = fields or list(rows[0].keys())
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
