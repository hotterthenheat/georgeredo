"""base.py — what a strategy entry is, and the paths every loader reads (files only; nothing is fetched or written outside
the report folder and the scratchpad)."""
from __future__ import annotations

import gzip
import io
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import polars as pl

REPO = Path(__file__).resolve().parents[3]
RN = REPO / 'research_notes'
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
SP2 = Path('/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
WORK = SP2 / 'fr'                     # the report's own intermediates (never committed)
DR = REPO / 'data_recorder'
ARCHIVE = '7dfea57'                   # the last commit before the fresh start (75c29c9)

STD = ['date', 'inst', 'period', 'contract', 'cost', 'pnl', 'reason']
FEE_COLS = ['fee_old', 'fee_rh', 'fee_how']   # the study's own fee on the trade, Robinhood's, and how Robinhood's was found

sys.path.insert(0, str(REPO / 'scripts'))
import fees_robinhood as FR  # noqa: E402  (the default cost model from 2026-10-24: docs/FEES_ROBINHOOD.md)

EXACT = 'exact'
VENDOR = 'vendor-recorded: no fee in either column'


def INFERRED(why: str) -> str:
    return 'Robinhood fees inferred from the rule: ' + why


def git_bytes(path: str, rev: str = ARCHIVE) -> bytes:
    """a file as committed at `rev` (the pre-reset tree is read this way, never checked out)"""
    return subprocess.run(['git', '-C', str(REPO), 'show', f'{rev}:{path}'], check=True, capture_output=True).stdout


def git_frame(path: str, rev: str = ARCHIVE) -> pl.DataFrame:
    b = git_bytes(path, rev)
    if path.endswith('.parquet'):
        return pl.read_parquet(io.BytesIO(b))
    if path.endswith('.gz'):
        b = gzip.decompress(b)
    return pl.read_csv(io.BytesIO(b), infer_schema_length=100000)


def std(df: pl.DataFrame) -> pl.DataFrame:
    """the standard trade frame: types fixed, rows with no P&L or no positive base dropped. Every loader also gives
    fee_old (the dollars the study charged the trade), fee_rh (Robinhood's dollars on the same fills) and fee_how; the
    trade's P&L at Robinhood's fees is pnl + fee_old − fee_rh (pnl_rh)."""
    missing = [c for c in FEE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f'a loader must give {FEE_COLS}; missing {missing}')
    out = df.select(
        pl.col('date').cast(pl.Utf8).str.slice(0, 10),
        pl.col('inst').cast(pl.Utf8),
        pl.col('period').cast(pl.Utf8),
        pl.col('contract').cast(pl.Utf8),
        pl.col('cost').cast(pl.Float64),
        pl.col('pnl').cast(pl.Float64),
        pl.col('reason').cast(pl.Utf8).fill_null(''),
        pl.col('fee_old').cast(pl.Float64).fill_null(0.0),
        pl.col('fee_rh').cast(pl.Float64).fill_null(0.0),
        pl.col('fee_how').cast(pl.Utf8),
    ).with_columns((pl.col('pnl') + pl.col('fee_old') - pl.col('fee_rh')).alias('pnl_rh'))
    return out.filter(pl.col('pnl').is_not_null() & pl.col('pnl').is_finite() & (pl.col('cost') > 0))


@dataclass
class Strategy:
    sid: str                      # inventory number, e.g. '29'
    name: str
    folder: str
    commits: str                  # prereg / amend / results, as text
    dates: str
    hypothesis: str
    rule: str                     # entry, contract, exits
    costs: str                    # fills and fees
    data: str                     # instruments, span, sessions
    periods: str                  # the periods and each holdout's status
    pass_rule: str
    verdict: str
    integrity: str                # amendments, deviations, integrity checks
    finding: str                  # one factual sentence
    unit: str = 'premium'         # premium | risk | stock
    load: Callable[[], pl.DataFrame] | None = None
    verdict_period: str = ''      # the period the verdict reads (summary table row)
    period_order: list = field(default_factory=list)
    period_spans: dict = field(default_factory=dict)   # period -> (first, last) calendar span for the bootstrap
    baseline: str = 'not available — no random baseline was computed by this study'
    na: str = ''                  # when no trade-level data: why
    extra: str = ''               # extra markdown (tables the study reports, labelled)
    group: str = ''
    vendor: bool = False          # vendor-recorded, not re-marked
    summary_label: str = ''       # the label in the page-1 table (default: name)
    pooled: bool = True           # add an all-instrument line per period
    combined: dict = field(default_factory=dict)       # label -> [periods] also reported together
    summary_slices: list = field(default_factory=list)  # [(inst, period)] for the page-1 table; default: pooled verdict period
