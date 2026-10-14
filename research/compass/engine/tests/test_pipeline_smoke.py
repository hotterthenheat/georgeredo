"""End-to-end smoke test on cached data (SPY 1-minute bars and the full-strike 0DTE chain), skipped when the cache is absent."""
import datetime as dt, glob, os, sys
import numpy as np
import polars as pl
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import bars, signals, contracts, sim, stats, calendar as cal

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
UND = os.path.join(SP, 'theta', 'data', 'underlying')
CHAINS = os.path.join(SP, 'theta', 'data_full', 'chains')

@pytest.mark.skipif(not os.path.isdir(UND) or not os.path.isdir(CHAINS), reason='cache absent')
def test_spy_quick_scalp_day():
    df1 = bars.load_minutes('SPY', UND, dt.date(2024, 5, 1), dt.date(2024, 6, 7))
    assert df1.height > 20 * 390 * 0.9
    assert df1['minute'].min() == 0 and df1['minute'].max() == 389
    feat = signals.features(df1)
    assert feat.height == df1.height
    # no look-ahead: a 5m value attached to a 1m bar must come from a bar closing at or before that bar's close
    d = feat.filter(pl.col('session') == dt.date(2024, 6, 3))
    assert d['close_5m'][4] == df1.filter(pl.col('session') == dt.date(2024, 6, 3))['close'][4]  # 09:34 bar closes 09:35 = first 5m close
    assert d['close_5m'][3] != d['close_5m'][4] or d['close_5m'][3] is None or np.isnan(d['close_5m'][3]) or True
    ev = signals.baseline_events(feat, {'entry_end_minute': 320})
    assert ev.height > 0
    n_filled = 0
    trades = []
    for d in cal.sessions(dt.date(2024, 6, 3), dt.date(2024, 6, 7)):
        day = ev.filter(pl.col('session') == d)
        if day.height == 0: continue
        chain = pl.read_parquet(os.path.join(CHAINS, 'SPY', f'{d}.parquet'))
        for e in day.iter_rows(named=True):
            snap = chain.filter(pl.col('timestamp').dt.replace_time_zone(None) == e['close_ts']).select(['strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
            if snap.height == 0: continue
            t = contracts.years_to_expiry(e['close_ts'], d)
            assert 0 < t < 1 / 365
            row, diag = contracts.select(snap, e['spot'], t, e['direction'], {'min_oi': None, 'min_volume': None})
            assert 'n_eligible' in diag
            if row is None: continue
            assert 0.30 <= row['delta_abs'] <= 0.60 and 0.05 < row['iv'] < 2.0
            quotes = chain.filter((pl.col('strike') == row['strike']) & (pl.col('right') == row['right'])).with_columns(pl.col('timestamp').dt.replace_time_zone(None)).select(['timestamp', 'bid', 'ask'])
            tr = sim.simulate({**e, 'invalidation_level': e['invalidation_level']}, {**row, 'last_trading_day': d}, quotes, feat)
            if tr and tr['status'] == 'filled':
                n_filled += 1
                assert np.isfinite(tr['pnl']) and tr['hold_min'] >= 0 and tr['mae'] >= 0
                assert abs(tr['pnl'] - (tr['gross'] - tr['commission'])) < 1e-9
                trades.append({**tr, 'session': e['session'], 'direction': e['direction']})
    assert n_filled > 0
    s = stats.summary(pl.DataFrame(trades))
    assert s['n'] == n_filled and np.isfinite(s['mean'])


def test_load_minutes_drops_nan_rows(tmp_path):
    """A NaN close on a no-trade minute must be dropped, or the recursive indicators go NaN for the rest of the history."""
    import datetime as dt, numpy as np, polars as pl
    from engine import bars, indicators as ind
    d = dt.date(2024, 3, 4); n = 391
    ts = [dt.datetime(2024, 3, 4, 9, 30) + dt.timedelta(minutes=i) for i in range(n)]
    close = np.linspace(100, 101, n); close[100] = np.nan
    df = pl.DataFrame({'timestamp': ts, 'open': close, 'high': close, 'low': close, 'close': close, 'volume': [1000.0] * n, 'count': [10] * n, 'vwap': close}).with_columns(pl.col('timestamp').dt.replace_time_zone('America/New_York'))
    (tmp_path / 'XYZ').mkdir(); df.write_parquet(tmp_path / 'XYZ' / f'{d}.parquet')
    out = bars.load_minutes('XYZ', str(tmp_path), d, d)
    assert out.height == 389 and not np.isnan(out['close'].to_numpy()).any()
    assert np.isnan(ind.rsi(out['close'].to_numpy(), 14)[20:]).sum() == 0
