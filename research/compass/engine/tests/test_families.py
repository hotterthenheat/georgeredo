"""Family triggers run on cached SPY bars, return the expected columns, are subsets of the baseline where the protocol says
so, and carry levels that sit on the correct side of the spot."""
import datetime as dt, os, sys
import numpy as np
import polars as pl
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import bars, signals

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
UND = os.path.join(SP, 'theta', 'data', 'underlying')

@pytest.mark.skipif(not os.path.isdir(UND), reason='cache absent')
def test_family_triggers_on_spy():
    df1 = bars.load_minutes('SPY', UND, dt.date(2024, 3, 1), dt.date(2024, 6, 28))
    feat = signals.features(df1)
    base = signals.baseline_events(feat, {'entry_end_minute': 360})
    for fam in ('trend_plays', 'breakouts', 'bounces'):
        ev = signals.family_events(feat, fam, {'entry_end_minute': 360}, df1)
        assert 'family' in ev.columns and (ev['family'] == fam).all()
        assert ev.height <= base.height
        # every family event is a baseline event (same close_ts and direction)
        j = ev.select(['close_ts', 'direction']).join(base.select(['close_ts', 'direction']), on=['close_ts', 'direction'], how='inner')
        assert j.height == ev.height
        if fam in ('breakouts', 'bounces') and ev.height:
            d = ev['direction'].to_numpy(); spot = ev['spot'].to_numpy(); inv = ev['invalidation_level'].to_numpy(); tgt = ev['target_price'].to_numpy()
            ok = np.isfinite(inv) & np.isfinite(tgt)
            assert ok.any()
            assert np.all(np.where(d[ok] > 0, tgt[ok] > spot[ok], tgt[ok] < spot[ok]))
            if fam == 'bounces': assert np.all(np.where(d[ok] > 0, inv[ok] < spot[ok], inv[ok] > spot[ok]))
        print(fam, ev.height, 'of', base.height)
