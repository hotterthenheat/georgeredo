"""The vectorised simulator must reproduce the reference loop on real data, trade for trade (entry, exit, reason, P&L, MAE)."""
import datetime as dt, os, sys
import numpy as np
import polars as pl
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import bars, signals, contracts, sim, calendar as cal

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
UND = os.path.join(SP, 'theta', 'data', 'underlying'); CHAINS = os.path.join(SP, 'theta', 'data_full', 'chains')

@pytest.mark.skipif(not os.path.isdir(UND) or not os.path.isdir(CHAINS), reason='cache absent')
@pytest.mark.parametrize('exits', [{}, {'tp1_frac': 0.0}, {'use_vwap_loss': False, 'use_invalidation': False}, {'stop_pct': 0.10, 'max_hold_min': 30}, {'use_ema_target': False, 'tp2_pct': 1.0, 'max_hold_min': 300}])
def test_vectorised_matches_loop(exits):
    df1 = bars.load_minutes('SPY', UND, dt.date(2023, 9, 1), dt.date(2023, 10, 13))
    feat = signals.features(df1)
    ev = signals.baseline_events(feat, {'entry_end_minute': 320, 'use_relvol': False})
    n = 0
    for d in cal.sessions(dt.date(2023, 10, 2), dt.date(2023, 10, 13)):
        day = ev.filter(pl.col('session') == d)
        f = os.path.join(CHAINS, 'SPY', f'{d}.parquet')
        if day.height == 0 or not os.path.exists(f): continue
        chain = pl.read_parquet(f).with_columns(pl.col('timestamp').dt.replace_time_zone(None))
        fday = feat.filter(pl.col('session') == d)
        for e in day.iter_rows(named=True):
            snap = chain.filter(pl.col('timestamp') == e['close_ts']).select(['strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])
            if snap.height == 0: continue
            row, _ = contracts.select(snap, e['spot'], contracts.years_to_expiry(e['close_ts'], d), e['direction'], {'min_oi': None, 'min_volume': None})
            if row is None: continue
            quotes = chain.filter((pl.col('strike') == row['strike']) & (pl.col('right') == row['right'])).select(['timestamp', 'bid', 'ask'])
            c = {**row, 'last_trading_day': d}
            a = sim.simulate(e, c, quotes, fday, {**exits, 'settle_intrinsic': False})
            b = sim.simulate_loop(e, c, quotes, fday, exits)
            assert (a is None) == (b is None)
            if a is None: continue
            assert a['status'] == b['status'], (a, b)
            if a['status'] != 'filled': continue
            for k in ('entry_ts', 'exit_ts', 'exit_reason', 'partial'):
                assert a[k] == b[k], (k, a, b)
            for k in ('entry_ask', 'exit_bid', 'pnl', 'gross', 'commission', 'hold_min', 'mae', 'mfe', 'ret_pct'):
                assert abs(a[k] - b[k]) < 1e-9, (k, a[k], b[k])
            n += 1
    assert n >= 10, f'only {n} trades compared'
