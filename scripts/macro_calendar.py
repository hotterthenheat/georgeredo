#!/usr/bin/env python3
"""
macro_calendar.py — the scheduled US macro releases on disk, for stamping the recorder's and the paper tracker's rows.

The calendar is data/macro_events_2022_2027.json (MACRO_EVENTS overrides the path): a JSON list of
  {"date": "YYYY-MM-DD", "time_et": "HH:MM", "event": "FOMC_DECISION" | "FOMC_MINUTES" | "CPI" | "NFP",
   "reference_period": ..., "status": ..., "source": ...}
(a {"events": [...]} wrapper is read too). An entry whose status says cancelled / canceled / postponed is left out;
every other status counts. The New York day of an entry is its `date`; `time_et` is New York wall time (08:30, 14:00).

THE STAMPS (every row; `stamps(day, at)`):
  is_macro_event_day          'true' / 'false' — the day holds at least one release
  macro_events                the day's kinds in time order, each once, joined by '+' ('CPI', 'FOMC_DECISION',
                              'CPI+FOMC_MINUTES'); '' on a day with none
  minutes_to_macro_release    minutes from `at` to the NEXT release of that New York day (0 at the release minute);
                              null once every release of the day is past, null on a day with none, null when `at` is
                              None (an end-of-day row)
  minutes_since_last_release  minutes from the most recent release of the day at or before `at`; null before the
                              day's first release, on a day with none, and when `at` is None
So a 13:00 row on an FOMC day (decision 14:00) reads 60 and null; a 15:00 row reads null and 60. Minutes are New York
wall-clock minutes, to two decimals when `at` has seconds.

A MISSING OR UNREADABLE CALENDAR never stops a caller: every field is null (unknown — not 'false'), and one WARN line
says so (once a path a process).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
REPO = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO / 'data' / 'macro_events_2022_2027.json'
FIELDS = ('is_macro_event_day', 'macro_events', 'minutes_to_macro_release', 'minutes_since_last_release')
KINDS = ('FOMC_DECISION', 'FOMC_MINUTES', 'CPI', 'NFP')
DROPPED_STATUS = ('cancel', 'postpone')
_WARNED: set = set()


def calendar_path() -> Path:
    return Path(os.environ.get('MACRO_EVENTS') or DEFAULT_PATH)


class MacroCalendar:
    """The releases by New York day: {day: [(minute_of_day or None, kind), ...]} in time order"""

    def __init__(self, events: dict | None, path: Path, error: str | None = None):
        self.events = events          # None: no calendar
        self.path = path
        self.error = error

    @property
    def loaded(self) -> bool:
        return self.events is not None

    @classmethod
    def load(cls, path: Path | str | None = None, log: logging.Logger | None = None) -> 'MacroCalendar':
        p = Path(path) if path else calendar_path()
        try:
            raw = json.loads(p.read_text(encoding='utf-8'))
            items = raw.get('events') if isinstance(raw, dict) else raw
            if not isinstance(items, list):
                raise ValueError('not a list of events')
            ev: dict[str, list] = {}
            for e in items:
                if not isinstance(e, dict) or not e.get('date') or not e.get('event'):
                    continue
                if any(w in str(e.get('status') or '').lower() for w in DROPPED_STATUS):
                    continue
                day = str(e['date'])[:10]
                dt.date.fromisoformat(day)
                t = e.get('time_et')
                mins = None
                if t:
                    h, m = str(t).strip()[:5].split(':')
                    mins = int(h) * 60 + int(m)
                ev.setdefault(day, []).append((mins, str(e['event'])))
            for day in ev:
                ev[day].sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else 0, x[1]))
            return cls(ev, p)
        except Exception as e:  # missing, unreadable, malformed: unknown, never a crash
            msg = f'{type(e).__name__}: {e}' if not isinstance(e, FileNotFoundError) else 'no such file'
            key = str(p)
            if key not in _WARNED:
                _WARNED.add(key)
                text = f'WARN macro calendar {p} not read ({msg}) — is_macro_event_day, macro_events and the minutes are null'
                (log.warning(text) if log else print(text, flush=True))
            return cls(None, p, msg)

    # -- the day --
    def events_on(self, day: str) -> list[tuple]:
        """[(HH:MM or None, kind), ...] in time order; [] on a day with none; [] without a calendar (check `loaded`)"""
        if not self.loaded:
            return []
        return [(None if m is None else f'{m // 60:02d}:{m % 60:02d}', k) for m, k in self.events.get(day, [])]

    def is_macro_event_day(self, day: str) -> bool | None:
        if not self.loaded:
            return None
        return bool(self.events.get(day))

    def kinds(self, day: str) -> str | None:
        if not self.loaded:
            return None
        out = []
        for _, k in self.events.get(day, []):
            if k not in out:
                out.append(k)
        return '+'.join(out)

    # -- the minutes --
    @staticmethod
    def _ny_minute(at: dt.datetime) -> tuple[str, float]:
        t = at.astimezone(NY) if at.tzinfo else at.replace(tzinfo=NY)
        return t.strftime('%Y-%m-%d'), t.hour * 60 + t.minute + t.second / 60 + t.microsecond / 6e7

    def minutes_to_macro_release(self, at: dt.datetime | None) -> float | None:
        """Minutes from `at` to the next release that New York day (0 at the release); None once all are past"""
        if at is None or not self.loaded:
            return None
        day, now = self._ny_minute(at)
        ahead = [m - now for m, _ in self.events.get(day, []) if m is not None and m >= now - 1e-9]
        return round(min(ahead), 2) if ahead else None

    def minutes_since_last_release(self, at: dt.datetime | None) -> float | None:
        if at is None or not self.loaded:
            return None
        day, now = self._ny_minute(at)
        past = [now - m for m, _ in self.events.get(day, []) if m is not None and m <= now + 1e-9]
        return round(min(past), 2) if past else None

    def stamps(self, day: str, at: dt.datetime | None = None) -> dict:
        """The four fields as the rows carry them (strings, the recorder's convention; None for null)"""
        if not self.loaded:
            return {k: None for k in FIELDS}
        to, since = self.minutes_to_macro_release(at), self.minutes_since_last_release(at)
        return {'is_macro_event_day': 'true' if self.is_macro_event_day(day) else 'false',
                'macro_events': self.kinds(day),
                'minutes_to_macro_release': None if to is None else _num(to),
                'minutes_since_last_release': None if since is None else _num(since)}


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f'{x:.2f}'.rstrip('0').rstrip('.')


_CACHE: dict = {}


def calendar(log: logging.Logger | None = None, path: Path | str | None = None, reload: bool = False) -> MacroCalendar:
    """The calendar at `path` (MACRO_EVENTS, else the default), read once a process — re-read when the file appears or changes"""
    p = Path(path) if path else calendar_path()
    try:
        stamp = p.stat().st_mtime
    except OSError:
        stamp = None
    key = str(p)
    hit = _CACHE.get(key)
    if hit is None or reload or hit[0] != stamp:
        _CACHE[key] = (stamp, MacroCalendar.load(p, log))
    return _CACHE[key][1]


if __name__ == '__main__':
    import sys
    cal = calendar()
    day = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    print(cal.path, 'loaded' if cal.loaded else f'NOT loaded ({cal.error})')
    print(day, cal.events_on(day), cal.stamps(day, dt.datetime.fromisoformat(day).replace(hour=13, tzinfo=NY)))
