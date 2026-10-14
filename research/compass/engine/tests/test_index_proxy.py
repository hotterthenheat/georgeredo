"""IndexProxyStore: SPXW signal bars carry the SPX value at the bar's start and end with SPY's volume."""
import datetime as dt, os, sys
import polars as pl
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import store
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')

@pytest.mark.skipif(not os.path.isdir(os.path.join(SP, 'theta', 'data', 'index', 'SPX')), reason='index cache absent')
def test_spxw_proxy_bars():
    st = store.IndexProxyStore(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
    d = dt.date(2024, 3, 4)
    b = st.bars('SPXW', d, d); spy = st.bars('SPY', d, d)
    ix = st.index_minutes('SPX', d, d).filter(pl.col('price').is_not_null())
    assert b.height == spy.height - 1 or b.height == spy.height  # the 09:30 index value is a null placeholder
    assert b.null_count().sum_horizontal().item() == 0
    # close = index value at the bar's close timestamp; open = value at its start
    r = b.row(100, named=True)
    at = ix.filter(pl.col('timestamp').dt.replace_time_zone(None) == r['close_ts'])['price'][0]
    assert r['close'] == at
    assert r['high'] >= max(r['open'], r['close']) and r['low'] <= min(r['open'], r['close'])
    # volume is SPY's for the same minute
    sv = spy.filter(pl.col('close_ts') == r['close_ts'])['volume'][0]
    assert r['volume'] == sv
    assert 4000 < r['close'] < 7000  # an index level, not an ETF price
