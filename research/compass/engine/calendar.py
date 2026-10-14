"""NYSE session calendar 2012-2027: full closes, early (13:00) closes, session lists, "days to expiration" helpers.

Rule-based (holiday rules + the special closures on record) and verified against ThetaData's SPY daily bars by
tests/test_calendar.py. If `exchange_calendars` is installed it is used as a cross-check, never as the source, so that the
engine runs identically on a machine without it.
"""
from __future__ import annotations
import datetime as dt
from functools import lru_cache

D = dt.date
SPECIAL_CLOSES = {D(2012, 10, 29), D(2012, 10, 30), D(2018, 12, 5), D(2025, 1, 9)}  # Sandy, G.H.W. Bush, Carter

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> D:
    first = D(year, month, 1)
    off = (weekday - first.weekday()) % 7
    return first + dt.timedelta(days=off + 7 * (n - 1))

def _last_weekday(year: int, month: int, weekday: int) -> D:
    nxt = D(year + (month == 12), month % 12 + 1, 1)
    last = nxt - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)

def easter(year: int) -> D:
    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; month = (h + l - 7 * m + 114) // 31; day = (h + l - 7 * m + 114) % 31 + 1
    return D(year, month, day)

def _observed(d: D) -> D | None:
    """Weekend holidays observed on the nearest weekday; a Saturday holiday observed Friday only if that Friday is in the
    same year (NYSE rule: no observance when Saturday falls on the last day of the year... Jan 1 Saturday is not observed)."""
    if d.weekday() == 5:
        f = d - dt.timedelta(days=1)
        return f if f.year == d.year else None
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d

@lru_cache(maxsize=None)
def full_closes(year: int) -> frozenset[D]:
    out = set()
    for d in (_observed(D(year, 1, 1)), _observed(D(year, 7, 4)), _observed(D(year, 12, 25))):
        if d: out.add(d)
    if year >= 2022:
        d = _observed(D(year, 6, 19))
        if d: out.add(d)
    out.add(_nth_weekday(year, 1, 0, 3))      # MLK
    out.add(_nth_weekday(year, 2, 0, 3))      # Presidents
    out.add(easter(year) - dt.timedelta(days=2))  # Good Friday
    out.add(_last_weekday(year, 5, 0))        # Memorial
    out.add(_nth_weekday(year, 9, 0, 1))      # Labor
    out.add(_nth_weekday(year, 11, 3, 4))     # Thanksgiving
    out |= {d for d in SPECIAL_CLOSES if d.year == year}
    return frozenset(out)

@lru_cache(maxsize=None)
def early_closes(year: int) -> frozenset[D]:
    """13:00 closes: the day after Thanksgiving; July 3 when it is a weekday session; December 24 when it is a weekday
    session (a Friday Dec 24 that is itself the observed Christmas holiday is a full close, handled by full_closes)."""
    out = {_nth_weekday(year, 11, 3, 4) + dt.timedelta(days=1)}
    for d in (D(year, 7, 3), D(year, 12, 24)):
        if d.weekday() < 5 and d not in full_closes(year): out.add(d)
    return frozenset(out)

def is_session(d: D) -> bool:
    return d.weekday() < 5 and d not in full_closes(d.year)

def is_early_close(d: D) -> bool:
    return is_session(d) and d in early_closes(d.year)

def close_time(d: D) -> dt.time:
    return dt.time(13, 0) if is_early_close(d) else dt.time(16, 0)

def sessions(start: D, end: D) -> list[D]:
    out = []; d = start
    while d <= end:
        if is_session(d): out.append(d)
        d += dt.timedelta(days=1)
    return out

def next_session(d: D, n: int = 1) -> D:
    while n > 0:
        d += dt.timedelta(days=1)
        if is_session(d): n -= 1
    return d

def prev_session(d: D, n: int = 1) -> D:
    while n > 0:
        d -= dt.timedelta(days=1)
        if is_session(d): n -= 1
    return d

def sessions_between(a: D, b: D) -> int:
    """Sessions strictly after a up to and including b (0 if b <= a)."""
    if b <= a: return 0
    return len(sessions(a + dt.timedelta(days=1), b))

def calendar_days(a: D, b: D) -> int:
    return (b - a).days

EXPIRY_CATS = (('0dte', 0, 0), ('weekly', 1, 7), ('swing', 8, 30), ('position', 31, 90), ('long', 91, 364), ('leaps', 365, 10**6))

def expiry_category(decision_date: D, last_trading_day: D) -> str | None:
    """The brief's categories on calendar days from the decision date to the contract's last trading day."""
    n = calendar_days(decision_date, last_trading_day)
    if n < 0: return None
    for name, lo, hi in EXPIRY_CATS:
        if lo <= n <= hi: return name
    return None

def last_trading_day(expiration: D, am_settled: bool) -> D:
    """An AM-settled contract (SPX third-Friday monthlies) stops trading the session before its expiration date."""
    d = expiration if is_session(expiration) else prev_session(expiration)
    return prev_session(d) if am_settled else d

def third_friday(year: int, month: int) -> D:
    return _nth_weekday(year, month, 4, 3)

def is_spx_am_settled(root: str, expiration: D) -> bool:
    """SPX (plain root) monthlies on the third Friday are AM-settled; SPXW and all equity/ETF options are PM."""
    return root.upper() == 'SPX' and expiration == third_friday(expiration.year, expiration.month)
