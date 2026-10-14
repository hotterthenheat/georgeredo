import datetime as dt, glob, os, sys
import polars as pl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine import calendar as cal

D = dt.date

def test_known_full_closes():
    assert not cal.is_session(D(2024, 1, 15))       # MLK
    assert not cal.is_session(D(2024, 3, 29))       # Good Friday
    assert not cal.is_session(D(2024, 6, 19))       # Juneteenth
    assert not cal.is_session(D(2021, 12, 24))      # Christmas observed Friday
    assert not cal.is_session(D(2012, 10, 29)) and not cal.is_session(D(2012, 10, 30))  # Sandy
    assert not cal.is_session(D(2018, 12, 5))
    assert not cal.is_session(D(2025, 1, 9))
    assert cal.is_session(D(2022, 1, 3))            # Jan 1, 2022 Saturday: not observed Friday Dec 31 2021
    assert cal.is_session(D(2021, 12, 31))
    assert not cal.is_session(D(2023, 1, 2))        # Jan 1 2023 Sunday -> Monday observed
    assert cal.is_session(D(2021, 6, 18))           # Juneteenth not yet a NYSE holiday in 2021

def test_known_early_closes():
    assert cal.is_early_close(D(2024, 11, 29))
    assert cal.is_early_close(D(2024, 7, 3))
    assert cal.is_early_close(D(2024, 12, 24))
    assert cal.is_early_close(D(2023, 7, 3))
    assert not cal.is_early_close(D(2020, 7, 3))    # observed holiday (full close)
    assert not cal.is_session(D(2020, 7, 3))
    assert cal.is_early_close(D(2019, 7, 3))
    assert not cal.is_early_close(D(2022, 12, 23))  # Dec 24 2022 is a Saturday: no early close that year
    assert cal.close_time(D(2024, 11, 29)) == dt.time(13, 0)

def test_sessions_match_spy_daily_bars():
    """Every SPY daily bar in the data lake is a session, and every session in that range has a bar."""
    root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data_lake', 'thetadata', 'stock_eod')
    files = sorted(glob.glob(os.path.join(root, 'year=*', 'part-*.parquet')))
    if not files: return
    days = set()
    for f in files:
        df = pl.read_parquet(f, columns=['symbol', 'created']).filter(pl.col('symbol') == 'SPY')
        if df.height: days |= set(df['created'].dt.date().to_list())
    assert days, 'SPY bars present'
    for d in days: assert cal.is_session(d), f'{d} has a SPY bar but is not a session'
    lo, hi = min(days), max(days)
    missing = [d for d in cal.sessions(lo, hi) if d not in days]
    assert not missing, f'sessions without a SPY bar: {missing[:10]}'

def test_early_closes_match_spy_minute_bars():
    """On the cached SPY 1-minute series, half days end at 12:59 and full days at 15:59."""
    sp = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
    files = sorted(glob.glob(os.path.join(sp, 'theta', 'data', 'underlying', 'SPY', '*.parquet')))
    if not files: return
    for f in files:
        d = D.fromisoformat(os.path.basename(f)[:10])
        df = pl.read_parquet(f, columns=['timestamp', 'open']).filter(pl.col('open').is_not_null())
        if df.height == 0: continue
        last = df['timestamp'].max().replace(tzinfo=None).time()
        if cal.is_early_close(d): assert last <= dt.time(13, 0), f'{d} early close but last bar {last}'
        else: assert last >= dt.time(15, 55), f'{d} full day but last bar {last}'

def test_expiry_categories_and_am_settlement():
    assert cal.expiry_category(D(2024, 6, 3), D(2024, 6, 3)) == '0dte'
    assert cal.expiry_category(D(2024, 6, 3), D(2024, 6, 7)) == 'weekly'
    assert cal.expiry_category(D(2024, 6, 3), D(2024, 6, 28)) == 'swing'
    assert cal.expiry_category(D(2024, 6, 3), D(2024, 8, 16)) == 'position'
    assert cal.expiry_category(D(2024, 6, 3), D(2025, 1, 17)) == 'long'
    assert cal.expiry_category(D(2024, 6, 3), D(2026, 1, 16)) == 'leaps'
    assert cal.is_spx_am_settled('SPX', D(2024, 6, 21)) and not cal.is_spx_am_settled('SPXW', D(2024, 6, 21))
    assert cal.last_trading_day(D(2024, 6, 21), am_settled=True) == D(2024, 6, 20)
    assert cal.last_trading_day(D(2024, 3, 29), am_settled=False) == D(2024, 3, 28)  # Good Friday expiry trades Thursday
