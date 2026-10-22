"""
uw_features.py — the Unusual Whales feature values at every entry, point in time (prereg 3.1, 3.2): for each index name
(SPY, QQQ, IWM; SPXW read as UW's SPX) and session, at each 0DTE entry minute and at the EOD entry (stamped 16:00):

  G    (SD1)  gamma_per_one_percent_move_oi of the last row whose minute ended by the entry (start_time + 1 min ≤ m)
  flip (SD2)  gamma_flip of gex-levels for the session BEFORE the entry session
  cw, pw (X2) the call wall (largest call_gex) and the put wall (most negative put_gex) of greek-exposure/strike, prior session
  d1   (D1)   Σ (net_call_premium − net_put_premium) of net-prem-ticks stamped 09:30 … m − 1 min
  d2   (D2)   Σ over sweep alerts created in [09:30, m): calls (ask − bid side premium) − puts (the same); SPXW: SPX + SPXW alerts
  d3   (D3)   nope of the last row stamped ≤ m − 1 min (SPY, QQQ, IWM; SPX not served)
  d4   (D4)   net_call_premium − net_put_premium of the last 5-minute market-tide row with timestamp + 5 min ≤ m
  d5   (D5)   Σ premium × sign(price − NBBO mid) over dark prints executed in [09:30, m), premium ≥ $1M (SPY, QQQ, IWM)

A missing file, an empty answer or no qualifying row leaves the value null (undefined). Output:
$SP/features_work/uw/<split>/<name>.parquet.

  POLARS_MAX_THREADS=1 python3 -I uw_features.py expl
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402

NY = ZoneInfo('America/New_York')
UW_TICKER = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
MINUTES = tuple(C.ENTRY_M) + (C.EOD_M,)
UW_FIRST = '2023-11-21'


def upath(route: str, t: str, d: str) -> Path | None:
    C.guard_ticker(t)
    p = C.UW / route / t / f'{d}.parquet'
    return p if p.exists() else None


def ny_min(col: str):
    """minutes since 09:30 New York (fractional) of a UTC datetime column"""
    z = pl.col(col).dt.convert_time_zone('America/New_York')
    return (z.dt.hour().cast(pl.Float64) * 60 + z.dt.minute().cast(pl.Float64) + z.dt.second().cast(pl.Float64) / 60
            + z.dt.microsecond().cast(pl.Float64) / 6e7) - 570.0


def same_day(col: str, d: str):
    return pl.col(col).dt.convert_time_zone('America/New_York').dt.date() == dt.date.fromisoformat(d)


def read(route, t, d, cols=None):
    p = upath(route, t, d)
    if p is None:
        return None
    try:
        x = pl.read_parquet(p, columns=cols)
    except Exception:
        x = pl.read_parquet(p)
    return x


def last_before(x: pl.DataFrame, tcol: str, val: str, cut_fn) -> dict[int, float | None]:
    out = {}
    if x is None or x.height == 0:
        return {m: None for m in MINUTES}
    x = x.sort(tcol)
    tm = x['_tm'].to_numpy()
    v = x[val].to_numpy().astype(float)
    for m in MINUTES:
        ok = cut_fn(tm, m) & np.isfinite(v)
        out[m] = float(v[ok][-1]) if ok.any() else None
    return out


def name_day(name: str, d: str) -> list[dict]:
    t = UW_TICKER[name]
    res = {m: dict(name=name, day=d, m=m) for m in MINUTES}
    prev = C.prev_tday(d)
    # SD1: the per-minute whole-book GEX
    x = read('spot_exposures', t, d, ['start_time', 'gamma_per_one_percent_move_oi'])
    if x is not None and x.height:
        x = x.filter(same_day('start_time', d)).with_columns(ny_min('start_time').alias('_tm'))
        g = last_before(x, '_tm', 'gamma_per_one_percent_move_oi', lambda tm, m: tm + 1.0 <= m + 1e-9)
        for m in MINUTES:
            res[m]['G'] = g[m]
    # SD2 and X2: the prior session's end state
    flip = cw = pw = None
    if prev:
        y = read('gex_levels', t, prev)
        if y is not None and y.height and 'gamma_flip' in y.columns:
            v = y['gamma_flip'].drop_nulls()
            flip = float(v[0]) if v.len() else None
        z = read('greek_exposure_strike', t, prev, ['strike', 'call_gex', 'put_gex'])
        if z is not None and z.height:
            z = z.filter(pl.col('call_gex').is_not_null() & pl.col('put_gex').is_not_null())
            if z.height:
                cmax = z['call_gex'].max()
                pmin = z['put_gex'].min()
                cw = float(z.filter(pl.col('call_gex') == cmax)['strike'].min())
                pw = float(z.filter(pl.col('put_gex') == pmin)['strike'].min())
    for m in MINUTES:
        res[m].update(flip=flip, cw=cw, pw=pw)
    # D1: net premium ticks
    x = read('net_prem_ticks', t, d, ['tape_time', 'net_call_premium', 'net_put_premium'])
    if x is not None and x.height:
        x = x.filter(same_day('tape_time', d)).with_columns(ny_min('tape_time').alias('_tm'),
                                                            (pl.col('net_call_premium') - pl.col('net_put_premium')).alias('_v'))
        tm, v = x['_tm'].to_numpy(), x['_v'].fill_null(0.0).to_numpy()
        for m in MINUTES:
            ok = (tm >= 0) & (tm <= m - 1 + 1e-9)
            res[m]['d1'] = float(v[ok].sum()) if ok.any() else None
    # D2: sweep alerts
    frames = []
    for tt in (('SPX', 'SPXW') if name == 'SPXW' else (t,)):
        y = read('flow_alerts', tt, d, ['created_at', 'type', 'has_sweep', 'total_ask_side_prem', 'total_bid_side_prem'])
        if y is not None:
            frames.append(y)
    if frames:
        y = pl.concat(frames, how='diagonal_relaxed').filter(pl.col('has_sweep') == True)  # noqa: E712
        y = y.filter(same_day('created_at', d)).with_columns(ny_min('created_at').alias('_tm'),
                                                             ((pl.col('total_ask_side_prem').fill_null(0) - pl.col('total_bid_side_prem').fill_null(0))
                                                              * pl.when(pl.col('type') == 'call').then(1.0).otherwise(-1.0)).alias('_v'))
        tm, v = y['_tm'].to_numpy(), y['_v'].to_numpy()
        for m in MINUTES:
            ok = (tm >= 0) & (tm < m)
            res[m]['d2'] = float(v[ok].sum()) if ok.any() else None
    # D3: NOPE
    if name != 'SPXW':
        x = read('nope', t, d, ['timestamp', 'nope'])
        if x is not None and x.height:
            x = x.filter(same_day('timestamp', d)).with_columns(ny_min('timestamp').alias('_tm'))
            g = last_before(x, '_tm', 'nope', lambda tm, m: tm <= m - 1 + 1e-9)
            for m in MINUTES:
                res[m]['d3'] = g[m]
    # D4: market tide
    x = read('market_tide', 'market', d, ['timestamp', 'net_call_premium', 'net_put_premium'])
    if x is not None and x.height:
        x = x.filter(same_day('timestamp', d)).with_columns(ny_min('timestamp').alias('_tm'),
                                                            (pl.col('net_call_premium') - pl.col('net_put_premium')).alias('_v'))
        g = last_before(x, '_tm', '_v', lambda tm, m: tm + 5.0 <= m + 1e-9)
        for m in MINUTES:
            res[m]['d4'] = g[m]
    # D5: dark pool
    if name != 'SPXW':
        x = read('darkpool', t, d, ['executed_at', 'price', 'premium', 'nbbo_bid', 'nbbo_ask'])
        if x is not None and x.height:
            x = x.filter(same_day('executed_at', d) & (pl.col('premium') >= 1_000_000)).with_columns(
                ny_min('executed_at').alias('_tm'),
                (pl.col('premium') * (pl.col('price') - (pl.col('nbbo_bid') + pl.col('nbbo_ask')) / 2).sign()).alias('_v'))
            tm, v = x['_tm'].to_numpy(), x['_v'].fill_null(0.0).fill_nan(0.0).to_numpy()
            for m in MINUTES:
                ok = (tm >= 0) & (tm < m)
                res[m]['d5'] = float(v[ok].sum()) if ok.any() else None
    return list(res.values())


def _job(args):
    name, d, split = args
    C.set_split(split)
    return name_day(name, d)


def run(split: str, names: list[str]):
    import multiprocessing as mp
    C.set_split(split)
    for name in names:
        t0 = time.time()
        days = [d for d in C.sessions() if UW_FIRST <= d <= C.LAST_DAY and
                ((split == 'hold') == ((name in C.HELD_T) or C.held_month(d)))]
        rows = []
        with mp.get_context("spawn").Pool(3) as pool:
            for rr in pool.imap(_job, [(name, d, split) for d in days], chunksize=8):
                rows += rr
        schema = {'name': pl.String, 'day': pl.String, 'm': pl.Int64, 'G': pl.Float64, 'flip': pl.Float64, 'cw': pl.Float64,
                  'pw': pl.Float64, 'd1': pl.Float64, 'd2': pl.Float64, 'd3': pl.Float64, 'd4': pl.Float64, 'd5': pl.Float64}
        df = pl.DataFrame([{k: r.get(k) for k in schema} for r in rows], schema=schema)
        C.write_parquet(df, C.WORK / 'uw' / split / f'{name}.parquet')
        print('uw', split, name, len(days), 'days', {c: int(df[c].is_not_null().sum()) for c in schema if c not in ('name', 'day', 'm')},
              f'{time.time() - t0:.0f}s', flush=True)


# ---- V2: open interest from the dated chain --------------------------------------------------------------------------------------

def occ(name: str, expiry: str, right: str, strike: float) -> str:
    y, mo, dd = expiry[2:4], expiry[5:7], expiry[8:10]
    return f'{name}{y}{mo}{dd}{right}{int(round(strike * 1000)):08d}'


def oi_for(name: str, d: str, symbols: list[str]) -> dict[str, int]:
    """the open_interest field of the chain dated d (the count published the morning of d)"""
    t = UW_TICKER[name]
    x = read('oi_chain', t, d, ['option_symbol', 'open_interest'])
    if x is None or x.height == 0:
        return {}
    x = x.filter(pl.col('option_symbol').is_in(symbols))
    return {a: int(b) for a, b in x.iter_rows() if b is not None}


if __name__ == '__main__':
    split = sys.argv[1]
    names = sys.argv[2:] or [n for n in C.INDEX if (n not in C.HELD_T) or split == 'hold']
    if split == 'expl':
        assert not set(names) & set(C.HELD_T)
    run(split, names)
