"""
guard.py — DR-GCE's held-out guard (GATE_PREREG.md section 1). Importing it wraps polars' file readers: a file whose name
holds a date inside one of the 28 held-out months, or outside the exploration span 2023-11-21 .. 2026-10-09, RAISES
before it is opened. Listing names is allowed; opening is not.
"""
from __future__ import annotations

import re
from pathlib import Path

import polars as pl

HELD_MONTHS = frozenset('''
2017-06 2017-09 2017-10 2018-01 2019-07 2019-08 2020-06 2020-08 2020-11 2020-12 2021-01 2021-03 2021-05 2021-11 2022-04
2022-12 2023-05 2023-11 2024-05 2024-06 2024-07 2024-08 2024-11 2025-08 2025-11 2026-03 2026-04 2026-08
'''.split())
assert len(HELD_MONTHS) == 28
SPAN = ('2023-11-21', '2026-10-09')
_DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')


class HeldOutRead(RuntimeError):
    pass


def held_out(day: str) -> bool:
    return day[:7] in HELD_MONTHS or day < SPAN[0] or day > SPAN[1]


def check(path) -> None:
    m = _DATE.search(Path(str(path)).name)
    if m and held_out(m.group(1)):
        raise HeldOutRead(f'held-out file opened: {path}')


def _wrap(fn):
    if getattr(fn, '_drgce', False):
        return fn

    def g(source, *a, **k):
        check(source)
        return fn(source, *a, **k)
    g._drgce = True
    return g


pl.read_parquet = _wrap(pl.read_parquet)
pl.scan_parquet = _wrap(pl.scan_parquet)


def selftest() -> str:
    bad = ('2023-11-30.parquet', '2024-06-03.parquet', '2026-08-31.parquet', '2026-10-12.parquet', '2023-11-20.parquet')
    for b in bad:
        try:
            pl.read_parquet(f'/nonexistent/{b}')
        except HeldOutRead:
            continue
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f'guard did not fire on {b}: {e!r}')
        raise AssertionError(f'guard did not fire on {b}')
    return f'guard selftest: raises on {len(bad)} of {len(bad)} ({", ".join(x[:10] for x in bad)})'
