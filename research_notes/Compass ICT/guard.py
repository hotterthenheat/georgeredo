"""
guard.py — the held-out guard of PREREG_COMPASS_ICT.md Amendment 1. Importing it wraps polars' file readers so that any
file whose name is a date before 2022-05-13 (holdout A) or inside one of the 28 held-out months (holdout B) RAISES before
it is opened. Listing a directory (file names only) is allowed; opening is not.
"""
from __future__ import annotations

import re
from pathlib import Path

import polars as pl

HELD_MONTHS = frozenset('''
2017-06 2017-09 2017-10 2018-01 2019-07 2019-08 2020-06 2020-08 2020-11 2020-12 2021-01 2021-03 2021-05 2021-11 2022-04
2022-12 2023-05 2023-11 2024-05 2024-06 2024-07 2024-08 2024-11 2025-08 2025-11 2026-03 2026-04 2026-08
'''.split())
A_END = '2022-05-12'                      # holdout A: SPX/SPY 2017-06 -> 2022-05-12
_DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')


class HeldOutRead(RuntimeError):
    pass


def held_out(day: str) -> bool:
    return day <= A_END or day[:7] in HELD_MONTHS


def check(path) -> None:
    m = _DATE.search(Path(str(path)).name)
    if m and held_out(m.group(1)):
        raise HeldOutRead(f'held-out file opened: {path}')


def _wrap(fn):
    if getattr(fn, '_guarded', False):
        return fn

    def g(source, *a, **k):
        check(source)
        return fn(source, *a, **k)
    g._guarded = True
    return g


pl.read_parquet = _wrap(pl.read_parquet)
pl.scan_parquet = _wrap(pl.scan_parquet)
pl.read_csv = _wrap(pl.read_csv)


def selftest() -> str:
    """the guard must raise on a held-out name (checked without the file existing: the check runs before the open)"""
    for bad in ('2024-06-03.parquet', '2022-05-12.parquet', '2017-06-01.parquet', '2026-08-31.parquet'):
        try:
            pl.read_parquet(f'/nonexistent/{bad}')
        except HeldOutRead:
            continue
        except Exception as e:                       # noqa: BLE001
            raise AssertionError(f'guard did not fire on {bad}: {e!r}')
        raise AssertionError(f'guard did not fire on {bad}')
    return 'guard selftest: raises on 2024-06-03, 2022-05-12, 2017-06-01, 2026-08-31 (4 of 4)'
