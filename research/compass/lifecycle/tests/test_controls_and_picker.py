"""The clean controls (amendment L-A2) and the daily tier's point-in-time expiration picker."""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
import pytest
from lc import runner

def _events():
    return pl.DataFrame({'session': [dt.date(2024, 6, 4)] * 3, 'm': [40, 200, 320], 'direction': [1, -1, 1], 'setup': ['QS'] * 3,
                         'spot': [500.0, 501.0, 502.0], 'inv': [499.0, 502.5, np.nan]})

def test_after_control_never_precedes_its_event():
    spot = np.linspace(500, 505, 390)
    out = runner.controls(_events(), 'SPY', 390, spot, mode='after')
    assert len(out) == 3 * len(runner.SEEDS)
    for c in out:
        ev = _events().row(c['event_i'], named=True)
        assert c['m'] >= min(ev['m'], 329), (c['m'], ev['m'])      # at or after the event (or the window's last minute)
        assert c['direction'] == ev['direction']

def test_window_control_can_precede_its_event():
    # the original control (kept for the record) draws from the whole window: the look-ahead L-A2 removed
    spot = np.linspace(500, 505, 390)
    out = runner.controls(_events(), 'SPY', 390, spot, mode='window')
    assert any(c['m'] < _events()['m'][c['event_i']] for c in out)

def test_flip_control_same_minute_opposite_direction_mirrored_invalidation():
    spot = np.linspace(500, 505, 390)
    out = runner.controls(_events(), 'SPY', 390, spot, mode='flip')
    assert len(out) == 3
    for c in out:
        ev = _events().row(c['event_i'], named=True)
        assert c['m'] == ev['m'] and c['direction'] == -ev['direction']
        if ev['inv'] is not None and np.isfinite(ev['inv']):
            dist = abs(ev['spot'] - ev['inv'])
            assert c['inv'] == pytest.approx(spot[c['m']] + ev['direction'] * dist)   # on the flipped side

from lc import daily as _dy
@pytest.mark.skipif(not os.path.isdir(f'{_dy.BYEXP}/SPY'), reason='needs the SPY daily chains')
def test_picker_uses_only_expirations_listed_that_day():
    from lc import daily_runner as dr
    ch = dr.Chains('SPY')
    for d in (dt.date(2017, 1, 9), dt.date(2020, 6, 1), dt.date(2022, 3, 7)):
        for b in ('W', 'S', 'P', 'L', 'X'):
            pk = ch.pick(d, b)
            if pk is None: continue
            first, last = ch.listed[pk[0]]
            assert first <= d <= last
