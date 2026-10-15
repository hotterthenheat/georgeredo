"""A real trade checked against the raw files (not through the engine's own loaders): SPY 2024-06-04, the 530 call
bought at 09:40 and sold 50 minutes later; the underlying's grid value against the raw minute bar."""
import datetime as dt, os, sys
import numpy as np, polars as pl, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc import chainmat as cm, position as ps, paths

F = f'{paths.CHAINS_0DTE}/SPY/2024-06-04.parquet'
pytestmark = pytest.mark.skipif(not os.path.exists(F), reason='cache not on this machine')

def raw_quote(ts):
    df = pl.read_parquet(F).filter((pl.col('strike') == 530.0) & (pl.col('right').cast(pl.Utf8).str.starts_with('C')))
    r = df.filter(pl.col('timestamp').dt.replace_time_zone(None) == ts)
    return float(r['bid'][0]), float(r['ask'][0])

def test_real_trade_matches_raw_quotes():
    cd = cm.load_0dte('SPY', dt.date(2024, 6, 4))
    c = cd.contract(530.0, True)
    b_in, a_in = raw_quote(dt.datetime(2024, 6, 4, 9, 40)); b_out, a_out = raw_quote(dt.datetime(2024, 6, 4, 10, 30))
    aux = dict(ema5=np.full(cd.n_min, np.nan), rsi=np.full(cd.n_min, 60.0), atr5=np.full(cd.n_min, 1.0), ativ=np.full(cd.n_min, 0.2))
    o = ps.run_one(cd, aux, [c, 0, 0, 0], [1, 0, 0, 0], 1, 10, 1, np.nan, ps.params(TIME_EXIT=50))
    expect = (b_out * 100 - 0.70) - (a_in * 100 + 0.70)
    assert o['entry_m'] == 10 and o['exit_m'] == 60
    assert abs(o['pnl'] - expect) < 1e-9, (o['pnl'], expect, b_in, a_in, b_out, a_out)

def test_underlying_grid_is_bar_close():
    cd = cm.load_0dte('SPY', dt.date(2024, 6, 4))
    u = pl.read_parquet(f'{paths.UNDERLYING}/SPY/2024-06-04.parquet')
    bar = u.filter(pl.col('timestamp').dt.replace_time_zone(None) == dt.datetime(2024, 6, 4, 9, 39))   # closes at 09:40
    assert abs(cd.spot[10] - float(bar['close'][0])) < 1e-9
    first = u.filter(pl.col('timestamp').dt.replace_time_zone(None) == dt.datetime(2024, 6, 4, 9, 30))
    assert abs(cd.spot[0] - float(first['open'][0])) < 1e-9
    last = u.filter(pl.col('timestamp').dt.replace_time_zone(None) == dt.datetime(2024, 6, 4, 15, 59))
    assert abs(cd.spot[390] - float(last['close'][0])) < 1e-9
