"""Screens: forward returns start at the next session's open (daily) or the next bar (intraday) with no look-ahead, and
the triggers fire where a constructed series says they must."""
import datetime as dt, os, sys
import numpy as np
import polars as pl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import daily_screen as ds, screen

def _daily(n=300, seed=3):
    rng = np.random.default_rng(seed)
    d0 = dt.date(2024, 1, 2); dates = []; d = d0
    while len(dates) < n:
        if d.weekday() < 5: dates.append(d)
        d += dt.timedelta(days=1)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n)); high = np.maximum(open_, close) * 1.005; low = np.minimum(open_, close) * 0.995
    vol = rng.integers(1_000_000, 2_000_000, n)
    return pl.DataFrame({'symbol': ['AAA'] * n, 'date': dates, 'open': open_, 'high': high, 'low': low, 'close': close, 'volume': vol})

def test_daily_forward_returns_start_at_next_open():
    df = _daily(); f = ds.features(df)
    o = df['open'].to_numpy(); c = df['close'].to_numpy()
    r1 = f['r1'].to_numpy(); r5 = f['r5'].to_numpy()
    t = 250
    assert np.isclose(r1[t], c[t + 1] / o[t + 1] - 1)
    assert np.isclose(r5[t], c[t + 5] / o[t + 1] - 1)
    assert np.isnan(r5[-3])  # no future rows -> null, never filled from elsewhere

def test_daily_breakout_fires_on_new_high_only():
    df = _daily()
    # force a breakout on day 260: close above the prior 20-day high
    c = df['close'].to_numpy().copy(); h = df['high'].to_numpy().copy()
    c[260] = h[240:260].max() * 1.02; h[260] = c[260] * 1.001
    df = df.with_columns(pl.Series('close', c), pl.Series('high', h))
    f = ds.features(df); d = ds.trigger_direction(f, 'breakout20')
    assert d[260] == 1
    assert d[259] in (0, -1, 1)  # defined
    # the day after cannot be a new breakout unless it exceeds day 260's high
    assert d[261] != 1 or f['close'][261] > h[260]

def test_daily_universe_is_prior_year():
    df = _daily(n=520)
    u = ds.universe(df, min_dollar_volume=1e6, min_days=100, min_price=1)
    yrs = sorted(u['year'].to_list())
    assert yrs and all(y >= 2025 for y in yrs)  # eligibility for 2025 comes from 2024 data

def test_intraday_forward_returns_stay_in_session():
    n = 390 * 3; close = 100 + np.cumsum(np.random.default_rng(1).normal(0, 0.01, n))
    sess = [d for d in (dt.date(2024, 3, 4), dt.date(2024, 3, 5), dt.date(2024, 3, 6)) for _ in range(390)]
    feat = pl.DataFrame({'close': close, 'session': pl.Series(sess, dtype=pl.Date)})
    idx = np.array([380, 400]); direction = np.array([1, -1])
    out = screen.forward_returns(feat, idx, direction)
    assert np.isnan(out['fwd_30m_bp'][0])  # 380 + 30 crosses into the next session
    assert np.isclose(out['fwd_30m_bp'][1], -(close[430] / close[400] - 1) * 1e4)
    assert np.isclose(out['fwd_close_bp'][1], -(close[779] / close[400] - 1) * 1e4)
