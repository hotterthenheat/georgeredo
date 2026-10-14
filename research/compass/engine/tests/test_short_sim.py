"""Short-premium pieces: the protective leg is further out of the money on both sides for either right naming, and a short
single/vertical settles at the ask on exit with fees per leg."""
import datetime as dt, os, sys
import numpy as np
import polars as pl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import short_sim

def _snap(right_names=('CALL', 'PUT')):
    rows = []
    for k, d in ((95, 0.75), (100, 0.5), (105, 0.3), (110, 0.15), (115, 0.07)):
        rows.append({'strike': float(k), 'right': right_names[0], 'bid': 1.0, 'ask': 1.1, 'delta_abs': d})
    for k, d in ((105, 0.75), (100, 0.5), (95, 0.3), (90, 0.15), (85, 0.07)):
        rows.append({'strike': float(k), 'right': right_names[1], 'bid': 1.0, 'ask': 1.1, 'delta_abs': d})
    return pl.DataFrame(rows)

def test_long_leg_is_further_otm_on_both_sides():
    for names in (('CALL', 'PUT'), ('C', 'P')):
        s = _snap(names)
        c = short_sim.pick_long_leg(s, {'strike': 105.0, 'right': names[0]}, 1, target_delta=0.15, lo=0.05, hi=0.25)
        p = short_sim.pick_long_leg(s, {'strike': 95.0, 'right': names[1]}, -1, target_delta=0.15, lo=0.05, hi=0.25)
        assert c is not None and c['strike'] == 110.0, names
        assert p is not None and p['strike'] == 90.0, names

def test_short_single_pnl_and_exit_at_ask():
    ts = [dt.datetime(2024, 3, 4, 10, 0) + dt.timedelta(minutes=i) for i in range(0, 400)]
    bid = np.linspace(1.0, 0.0, 400); ask = bid + 0.02
    q = pl.DataFrame({'timestamp': ts, 'bid': bid, 'ask': ask})
    r = short_sim.simulate({'close_ts': ts[0]}, q, None, {'stop_mult': 2.0, 'max_hold_min': None, 'session_cutoff_minute': 380, 'commission': 0.70})
    assert r['status'] == 'filled' and r['exit_reason'] == 'session_cutoff'
    assert abs(r['credit'] - 1.0) < 1e-9 and r['pnl'] == (1.0 - r['exit_cost']) * 100 - 1.4
