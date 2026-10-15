"""Re-fetch SPY 1-minute bars for sessions whose cached file held no prices (moved to quarantine on 2026-10-15):
month requests through the engine's fetcher, which writes only sessions not on disk. One login."""
import os, sys, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lc import paths
from engine import calendar as cal
from engine.data.theta_fetch import ThetaFetcher
Q = sys.argv[1]
days = sorted(dt.date.fromisoformat(os.path.basename(f)[:10]) for f in glob.glob(f'{Q}/*.parquet'))
days = [d for d in days if cal.is_session(d)]
months = sorted({(d.year, d.month) for d in days})
fx = ThetaFetcher(os.path.dirname(paths.UNDERLYING), nw=1)
for y, m in months:
    a = dt.date(y, m, 1); b = (a + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
    fx.stock_minutes('SPY', a, b)
print('months', len(months), 'stats', fx.stats)
