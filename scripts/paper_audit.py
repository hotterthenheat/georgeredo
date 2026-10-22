#!/usr/bin/env python3
"""
paper_audit.py — the backtest audit's corrections as the paper tracker's own code (2026-10-22, the owner: "Make the
audit's corrections the tracker's defaults so forward reports don't need a separate audit"). Imported by
paper_tracker.py (the settle rows' flags and period), paper_backtest.py (the replay's official close, the report's
period tables) and daily_forward.py. It reads files only; it never calls a vendor.

  - THE PERIODS (research_notes/Compass phase 3/backtest_audit/AUDIT.md section 5, audit_lib.PERIODS): every row carries
    `period`; the report keeps them apart and never pools them into a headline. Forward (iii) = 2026-10-12 on.
  - THE OFFICIAL CLOSE (AUDIT.md section 2): the options settle and are auto-exercised on the primary listing's closing
    print, not the 15:59 bar. `OfficialCloses` is the source chain for SPY and QQQ: UW's daily bar (`r` row) from
    data/official_closes (the forward fetches, kept as fetched), the lake's ohlc__1d and the live tracker's own settle
    rows ("the recorder"); then Theta's EOD daily bar (data_lake/thetadata/stock_eod, its 17:15 report). Nothing found:
    the caller settles on the 15:59 bar and labels the row `settle_source = '1559_bar'`, the session flagged.
  - THE FLAGS (AUDIT.md section 8): shares left after expiry under OCC's exercise-by-exception (in the money by $0.01 or
    more at the official close), by sign; the official close within $0.25 / $0.50 of a short strike (the pin); the
    post-market range across a short strike (UW's daily `po` bar, where on disk).
  - THE AFTER-HOURS P&L (the hook for the after-hours study): cases 0 / a / b / c of one settled trade, below.
  - THE SESSION STATISTICS (audit_lib.block_draws … session_stats, ported unchanged — tests/test_paper_tracker.py checks
    they agree with audit_lib's to the last digit): session sums, the iid-session and moving-block bootstraps.
"""
from __future__ import annotations

import datetime as dt
import glob
import math
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# ---- the periods ---------------------------------------------------------------------------------------------------------------------

HIST_START, HIST_END, FORWARD_START = '2022-11-11', '2026-10-09', '2026-10-12'
PRE = 'pre'                      # a session before the research's span (2022-11-11): in no period the audit defined
# (code, what the span was used for, first day, last day or None) — audit_lib.PERIODS, word for word, plus fly_spxw
PERIODS = {
    'condor_em1': [
        ('i', 'development: hyp_b fit (the pre-registration picked the VIX-mid cell; this all-VIX parent ranked 4th)', HIST_START, '2024-12-31'),
        ('ii', 'selection read: hyp_b OOS, read once; the tracked all-VIX form was written after it', '2025-01-02', HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
    'fly5': [
        ('i', 'development: hyp_c fit (C pre-registered 15:00 iron ±2, call ±2, call ±5 — not these cells)', HIST_START, '2024-12-31'),
        ('ii', 'selection read: hyp_c OOS — the iron ±5 found post hoc on it; the 15:30 call ±5 named after it (hyp_f)', '2025-01-02', HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
    'condor_d20': [
        ('i-a', 'model training: the frozen t2 model was fit on these sessions — its deciles here are IN-SAMPLE', HIST_START, '2024-06-30'),
        ('i-b', 'decile cuts: the nine cuts are this half-year\'s score quantiles (still hyp_e\'s fit period)', '2024-07-01', '2024-12-31'),
        ('ii', 'selection read: hyp_e OOS — out of the model\'s training, read before the candidate was set', '2025-01-02', HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
    # not in the audit: the cash-settled copy of fly5, named on 2026-10-21 after fly5's cells were found on this span
    'fly_spxw': [
        ('hist', 'history: fly5\'s cells copied to SPXW after they were found on this span (hyp_c / hyp_f) — not untouched', HIST_START, HIST_END),
        ('iii', 'untouched forward', FORWARD_START, None)],
}
PERIOD_ORDER = ('pre', 'i', 'i-a', 'i-b', 'hist', 'ii', 'gap', 'iii')


def period_of(key: str, day: str | None) -> str | None:
    """The period of `day` for candidate `key` — ONE function for the rows and the report. Before 2022-11-11: 'pre';
    between the history's end and the forward start (no session falls there): 'gap'; a key with no periods of its own
    reads condor_em1's (i / ii / iii)."""
    if not day:
        return None
    for code, _, a, b in PERIODS.get(key, PERIODS['condor_em1']):
        if day >= a and (b is None or day <= b):
            return code
    return PRE if day < HIST_START else 'gap'


def period_label(key: str, code: str) -> str:
    for c, label, a, b in PERIODS.get(key, PERIODS['condor_em1']):
        if c == code:
            return f'{a} → {b or "on"}: {label}'
    return {'pre': f'before {HIST_START}: outside the research\'s span', 'gap': 'between the history and the forward start'}.get(code, code)


def period_sort(code: str) -> int:
    return PERIOD_ORDER.index(code) if code in PERIOD_ORDER else len(PERIOD_ORDER)


# ---- the official close ------------------------------------------------------------------------------------------------------------

UW_DIRS = (REPO / 'data' / 'official_closes',)
UW_LAKE_GLOB = str(REPO / 'data_lake' / 'unusualwhales' / 'ohlc__1d.part0*.parquet')
THETA_EOD_GLOB = str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet')
LIVE_PAPER_ROOT = REPO / 'data_recorder' / 'paper'
SRC_UW, SRC_UW_LIVE, SRC_THETA = 'uw_1d', 'uw_1d_live_tracker', 'theta_eod'
FALLBACK_1559 = '1559_bar'


def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


class OfficialCloses:
    """(name, day) → the official close and where it came from: UW's daily bar first (its `r` row: the forward fetches
    in `uw_dirs`, the lake's ohlc__1d, the live tracker's settle rows read off UW's daily bar), then Theta's EOD daily
    bar (its `created` date, as audit_lib reads it). UW's `po` row (16:00–20:00) gives the post-market range; a file
    holding `_fetched_at` is newer than one without, and the newest fetch of a row wins (a later fetch carries the whole
    evening). Loaded once, lazily, for `names` only."""

    def __init__(self, names=('SPY', 'QQQ'), uw_dirs=UW_DIRS, uw_lake_glob: str | None = UW_LAKE_GLOB,
                 theta_glob: str | None = THETA_EOD_GLOB, live_root: Path | None = LIVE_PAPER_ROOT):
        self.names = tuple(names)
        self.uw_dirs = tuple(Path(d) for d in (uw_dirs or ()))
        self.uw_lake_glob, self.theta_glob, self.live_root = uw_lake_glob, theta_glob, live_root
        self._r: dict | None = None
        self._po: dict = {}
        self._open: dict = {}

    @classmethod
    def none(cls) -> 'OfficialCloses':
        """no source at all (tests; a replay told to find nothing)"""
        return cls(uw_dirs=(), uw_lake_glob=None, theta_glob=None, live_root=None)

    def _uw_frames(self) -> list:
        out = []
        files = []
        for d in self.uw_dirs:
            files += sorted(d.glob('uw_ohlc_1d_*.parquet')) if d.is_dir() else []
        lake = sorted(glob.glob(self.uw_lake_glob)) if self.uw_lake_glob else []
        for rank, f in [(0, x) for x in lake] + [(1, x) for x in files]:
            try:
                lf = pl.scan_parquet(f)
                cols = lf.collect_schema().names()
                df = lf.filter(pl.col('ticker').is_in(list(self.names))).select(
                    'ticker', 'date', 'market_time', 'open', 'high', 'low', 'close',
                    (pl.col('_fetched_at').cast(pl.Utf8) if '_fetched_at' in cols else pl.lit(None, pl.Utf8)).alias('_fetched_at')).collect()
            except Exception:  # noqa: BLE001 — an unreadable file is no source
                continue
            out.append(df.with_columns([pl.col(c).cast(pl.Utf8) for c in ('date', 'market_time', 'open', 'high', 'low', 'close')])
                       .with_columns(pl.lit(rank).alias('_rank'), pl.lit(str(f)).alias('_file')))
        return out

    def _load(self) -> None:
        if self._r is not None:
            return
        r: dict = {}
        frames = self._uw_frames()
        if frames:
            u = pl.concat(frames, how='diagonal_relaxed').sort(['_rank', '_fetched_at', '_file'], nulls_last=False)
            for row in u.to_dicts():                         # later (newer) rows overwrite earlier ones
                k = (row['ticker'], str(row['date'])[:10])
                if row['market_time'] == 'r' and _f(row['close']) is not None:
                    r[k] = (_f(row['close']), SRC_UW)
                    if _f(row['open']) is not None:
                        self._open[k] = _f(row['open'])
                elif row['market_time'] == 'po' and _f(row['low']) is not None and _f(row['high']) is not None:
                    fa = row['_fetched_at']
                    self._po[k] = (_f(row['low']), _f(row['high']), 'uw_1d po' + (f' (fetched {fa})' if fa else ''), fa)
        if self.live_root is not None and Path(self.live_root).is_dir():
            for name in self.names:
                for f in sorted(Path(self.live_root).glob(f'*/{name}/*.parquet')):
                    k = (name, f.stem)
                    if k in r:
                        continue
                    try:
                        df = pl.read_parquet(f)
                        if 'close_official' not in df.columns:
                            continue
                        s = df.filter((pl.col('row_kind') == 'settle') & pl.col('close_official').is_not_null()
                                      & (pl.col('close_official_from') == 'daily bar'))
                        if s.height:
                            r[k] = (float(s['close_official'][0]), SRC_UW_LIVE)
                    except Exception:  # noqa: BLE001
                        continue
        if self.theta_glob:
            parts = []
            for f in sorted(glob.glob(self.theta_glob)):
                try:
                    parts.append(pl.scan_parquet(f).filter(pl.col('symbol').is_in(list(self.names))).select('symbol', 'created', 'close').collect())
                except Exception:  # noqa: BLE001
                    continue
            if parts:
                e = pl.concat(parts).with_columns(pl.col('created').dt.strftime('%Y-%m-%d').alias('day'))
                for sym, day, c in e.select('symbol', 'day', 'close').iter_rows():
                    if (sym, day) not in r and c is not None and math.isfinite(c):
                        r[(sym, day)] = (float(c), SRC_THETA)
        self._r = r

    def get(self, name: str, day: str) -> tuple[float | None, str | None]:
        """(official close, source) — (None, None) when no source on disk carries the day"""
        self._load()
        return self._r.get((name, day), (None, None))

    def post_market(self, name: str, day: str) -> tuple[float | None, float | None, str]:
        """(low, high, source) of UW's `po` bar; (None, None, 'none: no UW post-market bar on disk') when absent"""
        self._load()
        v = self._po.get((name, day))
        return (v[0], v[1], v[2]) if v else (None, None, 'none: no UW post-market bar on disk')

    def open_r(self, name: str, day: str) -> float | None:
        """UW's regular-session open of `day` (the daily bar's `r` row) — the fallback for the next 09:30 open"""
        self._load()
        return self._open.get((name, day))


# ---- expiration mechanics -------------------------------------------------------------------------------------------------------

ITM_MIN = 0.01                    # OCC exercise-by-exception: in the money by $0.01 or more at the close
_EPS = 1e-6
PIN_BANDS = (0.25, 0.50)


def intrinsic(px: float, k: float, right: str) -> float:
    return max(px - k, 0.0) if right == 'C' else max(k - px, 0.0)


def is_itm(px: float, k: float, right: str) -> bool:
    return intrinsic(px, k, right) >= ITM_MIN - _EPS


def _legs(s) -> list[tuple[str, float, str, int]]:
    """(right, strike, side, qty) of a paper_tracker Structure, or of such tuples already"""
    out = []
    for l in (s.legs if hasattr(s, 'legs') else s):
        out.append((l.right, float(l.strike), l.side, int(l.qty)) if hasattr(l, 'right') else (l[0], float(l[1]), l[2], int(l[3])))
    return out


def shares_of(right: str, side: str, qty: int) -> int:
    """shares a contract's exercise or assignment leaves: a long call +100, a long put −100, a short call −100, a
    short put +100 (× qty)"""
    return 100 * qty * (1 if side == 'long' else -1) * (1 if right == 'C' else -1)


def stock_left(s, px: float) -> int:
    """Net shares left after expiry when every leg in the money by ≥ $0.01 at `px` is exercised or assigned (OCC's
    exercise-by-exception at the official close); 0 when nothing is or the deliveries offset"""
    return sum(shares_of(r, side, q) for r, k, side, q in _legs(s) if is_itm(px, k, r))


def pin_distance(s, px: float) -> float | None:
    shorts = [k for r, k, side, q in _legs(s) if side == 'short']
    return min(abs(px - k) for k in shorts) if shorts else None


def pm_cross(s, close: float, low: float | None, high: float | None) -> bool | None:
    """True when the post-market range (with the close itself) took a short strike across the money — the trades
    whose assignment was undecided at 16:00 (AUDIT.md section 8: the range [min(low, close), max(high, close)] holds
    the strike and the leg's in-the-money state differs at its two ends); None without a range"""
    if low is None or high is None:
        return None
    lo, hi = min(low, close), max(high, close)
    return any(lo <= k <= hi and is_itm(lo, k, r) != is_itm(hi, k, r) for r, k, side, q in _legs(s) if side == 'short')


def flags(s, px: float, pm_low: float | None = None, pm_high: float | None = None, cash_settled: bool = False) -> dict:
    """The settle row's expiration flags at the settlement price `px` (values, not yet strings)"""
    d = pin_distance(s, px)
    out = {'pin_dist': d, 'pin_025': None if d is None else d <= PIN_BANDS[0] + _EPS,
           'pin_050': None if d is None else d <= PIN_BANDS[1] + _EPS}
    if cash_settled:
        out.update(stock_left=None, stock_left_side='cash-settled', pm_cross=None)
        return out
    sh = stock_left(s, px)
    out.update(stock_left=sh, stock_left_side='long' if sh > 0 else 'short' if sh < 0 else 'none', pm_cross=pm_cross(s, px, pm_low, pm_high))
    return out


# ---- the after-hours P&L (the hook the after-hours study fills) --------------------------------------------------------------------

AH_CASES = ('0', 'a', 'b', 'c')


def after_hours_pnl(s, entry_cash: float, official_close: float, next_open: float | None, decision_price: float | None,
                    fee_per_exercise: float = 0.0, open_fees: float = 2.60, cash_settled: bool = False) -> dict:
    """One settled trade's P&L in $ a structure under four expiry cases. `s` a paper_tracker Structure (or (right,
    strike, side, qty) tuples); `entry_cash` the cash a unit at the open (+ a credit, − a debit; the NBBO fill);
    `open_fees` the opening fees in $ ($0.65 × 4 contracts); `fee_per_exercise` $ for each contract exercised or
    assigned (default 0 — the reports' convention).

      0  hold to expiry at intrinsic on the official close — the tracker's settle P&L (no stock, no fee)
      a  OCC's default on the official close: every leg in the money by ≥ $0.01 is exercised or assigned; the net
         stock is marked at the next session's 09:30 open
      b  our shorts are assigned iff in the money at the decision price (the holder decides on after-hours prices),
         our longs by default (in the money at the official close); stock at the next 09:30 open
      c  both sides at the decision price (we file contrary instructions too); stock at the next 09:30 open

    An exercised or assigned leg is worth (open − K) a call, (K − open) a put, signed by the side, × qty, at the open:
    the delivered shares marked at it. A cash-settled structure (SPXW) delivers no stock: every case is case 0.
    → {'pnl_ah0', 'pnl_ah_a', 'pnl_ah_b', 'pnl_ah_c'}: None where the next open (a, b, c) or the decision price (b, c)
    is missing."""
    legs = _legs(s)
    pay0 = sum((1 if side == 'long' else -1) * q * intrinsic(official_close, k, r) for r, k, side, q in legs)
    out = {'pnl_ah0': (entry_cash + pay0) * 100 - open_fees}
    if cash_settled:
        return dict(out, pnl_ah_a=out['pnl_ah0'], pnl_ah_b=out['pnl_ah0'], pnl_ah_c=out['pnl_ah0'])

    def case(exercised) -> float:
        cash, n = 0.0, 0
        for r, k, side, q in legs:
            if not exercised(r, k, side):
                continue
            value = (next_open - k) if r == 'C' else (k - next_open)
            cash += (1 if side == 'long' else -1) * q * value
            n += q
        return (entry_cash + cash) * 100 - open_fees - fee_per_exercise * n

    out['pnl_ah_a'] = None if next_open is None else case(lambda r, k, side: is_itm(official_close, k, r))
    ok = next_open is not None and decision_price is not None
    out['pnl_ah_b'] = case(lambda r, k, side: is_itm(decision_price if side == 'short' else official_close, k, r)) if ok else None
    out['pnl_ah_c'] = case(lambda r, k, side: is_itm(decision_price, k, r)) if ok else None
    return out


# ---- the decision price: the last UW post-market minute bar at or before 17:30 (the after-hours study's rule) ---------------------

DECISION_CUTOFF = (17, 30)
POSTMARKET_DIR = REPO / 'data' / 'postmarket_1m'                  # UW /ohlc/1m answers kept as answered: <T>/<D>.json.gz
RECORDER_OHLC_1M = REPO / 'data_recorder' / 'ohlc_1m'
UW_1M_FILE_RX = r'stock_(SPY|QQQ)_ohlc_1m_date[-_](\d{4}-\d\d-\d\d)'


def _ny(ts: str) -> dt.datetime:
    from zoneinfo import ZoneInfo
    return dt.datetime.fromisoformat(str(ts).replace('Z', '+00:00')).astimezone(ZoneInfo('America/New_York'))


def decision_of(day: str, rows: list, fetched: dt.datetime | None = None) -> dict:
    """research_notes/Compass phase 3/backtest_audit/afterhours.py `decision_of`, the same rule: the close of the last
    `po` bar of `day` (its START on `day` in New York — UW files a winter session by its UTC date, so the evening before
    rides along and is left out) ENDING at or before 17:30 New York; only when the file proves it was taken after 17:30
    (a bar of the day ending after 17:30, or its fetch time) — else the last bar to 17:30 is not known. → {'px', 'end',
    'complete', 'note'}"""
    from zoneinfo import ZoneInfo
    cut = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(*DECISION_CUTOFF), ZoneInfo('America/New_York'))
    po, after = [], False
    for r in rows:
        st, en = _ny(r['start_time']), _ny(r['end_time'])
        if st.date().isoformat() != day:
            continue
        if en > cut:
            after = True
        if r.get('market_time') == 'po' and en <= cut:
            po.append((en, float(r['close'])))
    complete = after or (fetched is not None and fetched >= cut)
    if not po:
        return {'px': None, 'end': None, 'complete': complete, 'note': 'no post-market bar ending at or before 17:30 in the file'}
    en, c = max(po)
    if not complete:
        return {'px': None, 'end': en.strftime('%H:%M'), 'complete': False,
                'note': f'the file was taken before 17:30: the last bar to 17:30 is not known (last seen {en:%H:%M} at {c})'}
    return {'px': c, 'end': en.strftime('%H:%M'), 'complete': True, 'note': ''}


def uw_minute_answers(names=('SPY', 'QQQ'), postmarket_dir: Path | None = POSTMARKET_DIR, extra_dirs: tuple = (),
                      recorder: Path | None = RECORDER_OHLC_1M) -> dict:
    """{(name, day): [(label, rows, fetched_at)]} — every UW 1-minute answer on disk, in the study's order: the
    post-market files fetched for it (data/postmarket_1m), then `extra_dirs` (folders of UW answers named
    stock_<T>_ohlc_1m_date-<D>…), then the recorder's ohlc_1m Parquet (with its fetch time)"""
    import gzip
    import json
    import re
    out: dict = {}
    if postmarket_dir is not None and Path(postmarket_dir).is_dir():
        for f in sorted(Path(postmarket_dir).glob('*/*.json.gz')):
            if f.parent.name in names:
                out.setdefault((f.parent.name, f.name[:10]), []).append((str(f), json.loads(gzip.open(f).read())['data'], None))
    rx = re.compile(UW_1M_FILE_RX)
    for d in extra_dirs:
        d = Path(d)
        for f in sorted(d.iterdir()) if d.is_dir() else []:
            m = rx.search(f.name)
            if not m or f.suffix == '.headers' or m[1] not in names:
                continue
            try:
                raw = gzip.open(f).read() if f.suffix == '.gz' else f.read_bytes()
                rows = json.loads(raw)['data']
            except Exception:  # noqa: BLE001
                continue
            out.setdefault((m[1], m[2]), []).append((str(f), rows, None))
    if recorder is not None:
        for nm in names:
            d = Path(recorder) / nm
            for f in sorted(d.glob('*.parquet')) if d.is_dir() else []:
                t = pl.read_parquet(f)
                fetched = max(_ny(x) for x in t['_fetched_at'].to_list()) if '_fetched_at' in t.columns and t.height else None
                out.setdefault((nm, f.stem), []).append((str(f), t.select('start_time', 'end_time', 'close', 'market_time').to_dicts(), fetched))
    return out


def decision_prices_on_disk(names=('SPY', 'QQQ'), postmarket_dir: Path | None = POSTMARKET_DIR, extra_dirs: tuple = (),
                            recorder: Path | None = RECORDER_OHLC_1M) -> dict:
    """{(name, day): decision price} from every UW 1-minute answer on disk — the first file (in uw_minute_answers'
    order) that names the last post-market bar to 17:30, as the after-hours study takes it"""
    out = {}
    for k, srcs in uw_minute_answers(names, postmarket_dir, extra_dirs, recorder).items():
        for _, rows, fetched in srcs:
            dec = decision_of(k[1], rows, fetched)
            if dec['px'] is not None:
                out[k] = dec['px']
                break
    return out


# ---- session statistics (audit_lib, ported unchanged) -----------------------------------------------------------------------------

BOOT_N = 2000
SEED = 20261022


def block_draws(n: int, block: int, B: int = BOOT_N, seed: int = SEED) -> np.ndarray:
    """B × n session indices by the moving-block bootstrap (overlapping blocks of `block` consecutive sessions, starts
    uniform on 0 .. n − block, concatenated and cut to n); block 1 = the iid session bootstrap"""
    rng = np.random.default_rng(seed + 7919 * block)
    if n == 0:
        return np.zeros((B, 0), int)
    b = max(1, min(block, n))
    k = int(math.ceil(n / b))
    starts = rng.integers(0, n - b + 1, (B, k))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(B, k * b)[:, :n]
    return idx


def weights_from(idx: np.ndarray, n: int) -> np.ndarray:
    W = np.zeros((idx.shape[0], n))
    for b in range(idx.shape[0]):
        W[b] = np.bincount(idx[b], minlength=n)
    return W


def pct_ci(x: np.ndarray) -> tuple[float, float]:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float('nan'), float('nan')
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def session_stats(S: np.ndarray, N: np.ndarray, blocks=(1, 5, 20)) -> dict:
    """S, N: per session (calendar order, every session the candidate ran, zero where it took no trade) the summed P&L and
    the trade count. → the session mean and the per-trade mean (Σ S / Σ N) with percentile CIs by the iid session
    bootstrap (block 1) and the moving-block bootstrap (blocks 5, 20); the lag-1..5 autocorrelation; effective N"""
    n = S.size
    out = {'sessions': int(n), 'sessions_traded': int((N > 0).sum()), 'trades': int(N.sum())}
    if n == 0 or N.sum() == 0:
        return out
    out['mean_session'] = float(S.mean())
    out['mean_trade'] = float(S.sum() / N.sum())
    var = {}
    for b in blocks:
        if n < 3 * b:                       # too few sessions for blocks this long: no interval
            out[f'ci_session_b{b}'] = out[f'ci_trade_b{b}'] = (float('nan'), float('nan'))
            continue
        W = weights_from(block_draws(n, b), n)
        ms = (W @ S) / n
        mt = (W @ S) / np.maximum(W @ N, 1)
        out[f'ci_session_b{b}'] = pct_ci(ms)
        out[f'ci_trade_b{b}'] = pct_ci(mt)
        var[b] = float(np.var(ms))
    x = S - S.mean()
    den = float((x * x).sum())
    ac = [float((x[:-k] * x[k:]).sum() / den) if den > 0 and n > k else float('nan') for k in range(1, 6)]
    out['acf'] = ac
    out['n_eff_acf'] = float(n / max(1e-9, 1 + 2 * sum((1 - k / n) * a for k, a in enumerate(ac, 1) if math.isfinite(a))))
    out['n_eff_block20'] = float(n * var[1] / var[20]) if 1 in var and 20 in var and var[20] > 0 else float('nan')
    return out


def session_series(days: list, trade_days: list, values: list) -> tuple[np.ndarray, np.ndarray]:
    """per session in `days` (calendar order): the summed value and the count of the trades on it (None values out)"""
    ix = {d: i for i, d in enumerate(days)}
    S, N = np.zeros(len(days)), np.zeros(len(days))
    for d, v in zip(trade_days, values):
        if d in ix and v is not None and isinstance(v, (int, float)) and math.isfinite(v):
            S[ix[d]] += v
            N[ix[d]] += 1
    return S, N


def drawdown(seq: np.ndarray) -> float:
    if seq.size == 0:
        return float('nan')
    c = np.cumsum(seq)
    peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    return float((peak - c).max())


def ny_now(now: dt.datetime | None = None) -> dt.datetime:
    from zoneinfo import ZoneInfo
    return (now or dt.datetime.now(dt.timezone.utc)).astimezone(ZoneInfo('America/New_York'))
