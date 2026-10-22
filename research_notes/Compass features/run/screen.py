"""
screen.py — every feature's one decision (prereg 3.2) against the base trades, in the prereg's order (veto, venue,
expiry/strike, [the GEX check] strike distance, exit, direction): with vs without, the mean return per trade after costs,
the 20-session block interval over dates with every name resampled together, effective N, per tier and per settlement type.

  python3 -I screen.py expl            → out/screen_expl.json (the exploration screen; which features go to the holdout)
  python3 -I screen.py hold F1 F2 …    → out/holdout.json     (the once-only holdout test of the features named)

The holdout run refuses any feature that the exploration screen did not pass, and refuses to run twice.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import daily as D  # noqa: E402
import stats as ST  # noqa: E402
import tiers as TI  # noqa: E402
import uw_features as UF  # noqa: E402

SQ2PI = math.sqrt(2.0 / math.pi)
KEEP = ['name', 'day', 'm', 'eb', 'expiry', 'listed', 'strike', 'right', 'sb', 'x', 'bid', 'ask', 'mid', 'spread', 'F', 'IM', 'S',
        'r', 'pnl', 'x1_def', 'r_x1', 'r_x3', 'iv', 'delta', 'd6', 'd7', 'xrm', 'atm_iv', 'vol', 'exit_day', 'exit_px']


def names_of(split: str) -> list[str]:
    return list(C.EXPL_T) if split == 'expl' else list(C.TICKERS)


def split_sessions(split: str) -> list[str]:
    s = C.sessions()
    if split == 'expl':
        return [d for d in s if not C.held_month(d)]
    return list(s)


# ---- the base trades ------------------------------------------------------------------------------------------------------------------

def load_base(split: str) -> pl.DataFrame:
    parts = []
    for nm in names_of(split):
        for kind in ('0dte', 'eod'):
            p = C.WORK / split / kind / f'{nm}.parquet'
            if not p.exists():
                continue
            x = pl.read_parquet(p)
            if x.height == 0:
                continue
            if kind == '0dte':
                x = x.with_columns(pl.col('day').alias('listed'), pl.lit(None, pl.Float64).alias('atm_iv'), pl.lit(None, pl.Int64).alias('vol'))
            else:
                x = x.with_columns(pl.lit(None, pl.Float64).alias('r_x3'), pl.lit(0, pl.Int64).alias('d6'), pl.lit(None, pl.Int64).alias('d7'),
                                   pl.lit(None, pl.Float64).alias('xrm'))
            x = x.select([pl.col(c).cast(pl.Float64) if c in ('strike', 'x', 'bid', 'ask', 'mid', 'spread', 'F', 'IM', 'S', 'r', 'pnl', 'r_x1',
                                                              'r_x3', 'iv', 'delta', 'xrm', 'atm_iv', 'exit_px') else
                          (pl.col(c).cast(pl.Int64) if c in ('m', 'd6', 'd7', 'vol') else pl.col(c)) for c in KEEP])
            parts.append(x)
    T = pl.concat(parts, how='vertical_relaxed')
    tt = TI.table(sorted(set(T['name'].to_list())))
    T = T.with_columns(pl.col('day').str.slice(0, 7).alias('month'),
                       pl.when(pl.col('name') == 'SPXW').then(pl.lit('cash')).otherwise(pl.lit('physical')).alias('settle'))
    T = T.with_columns(pl.struct('name', 'month').map_elements(lambda s: tt.get((s['name'], s['month']), 'U'), return_dtype=pl.String).alias('tier'))
    T = T.with_row_index('tid')
    # D7 for the EOD entries: the 15:59 close against the prior session's range
    d7 = []
    for nm, d, S, m in T.select('name', 'day', 'S', 'm').iter_rows():
        if m != C.EOD_M:
            d7.append(None)
            continue
        ph, plo = D.prior_hl(nm, d)
        d7.append(None if not (np.isfinite(S) and np.isfinite(ph)) else (1 if S > ph else (-1 if S < plo else 0)))
    T = T.with_columns(pl.when(pl.col('m') == C.EOD_M).then(pl.Series('d7e', d7, pl.Int64)).otherwise(pl.col('d7')).alias('d7'))
    return T


# ---- feature inputs -------------------------------------------------------------------------------------------------------------------

def iv30_series(name: str) -> dict[str, float]:
    p = C.WORK / 'eod' / name / 'expiries.parquet'
    if not p.exists():
        return {}
    e = pl.read_parquet(p).filter(pl.col('atm_iv').is_not_null() & pl.col('atm_iv').is_finite() & (pl.col('atm_iv') > 0))
    out = {}
    for (d,), g in e.group_by('day'):
        g = g.sort('dte')
        dte = g['dte'].to_numpy().astype(float)
        iv = g['atm_iv'].to_numpy()
        w = iv * iv * dte / 365.0
        if (dte == 30).any():
            out[d] = float(iv[dte == 30][0])
            continue
        lo = np.where(dte < 30)[0]
        hi = np.where(dte > 30)[0]
        if lo.size == 0 or hi.size == 0:
            continue
        i, j = lo[-1], hi[0]
        w30 = w[i] + (w[j] - w[i]) * (30 - dte[i]) / (dte[j] - dte[i])
        if w30 > 0:
            out[d] = float(math.sqrt(w30 * 365.0 / 30.0))
    return out


def ivrank_series(name: str) -> dict[str, float]:
    """IV rank at each full session's close: (IV30 − min) ÷ (max − min) over the 252 full sessions ending there, ≥ 200 valid"""
    iv = iv30_series(name)
    s = C.sessions()
    vals = np.array([iv.get(d, np.nan) for d in s])
    out = {}
    for i, d in enumerate(s):
        if i < 251 or not np.isfinite(vals[i]):
            continue
        w = vals[i - 251:i + 1]
        ok = np.isfinite(w)
        if ok.sum() < 200:
            continue
        lo, hi = w[ok].min(), w[ok].max()
        if hi > lo:
            out[d] = float((vals[i] - lo) / (hi - lo))
    return out


def add_inputs(T: pl.DataFrame, split: str) -> pl.DataFrame:
    names = sorted(set(T['name'].to_list()))
    # V3: the contract's volume on the last completed session
    nv = []
    for nm in names:
        p = C.WORK / 'eod' / nm / 'nextvol.parquet'
        if p.exists():
            nv.append(pl.read_parquet(p).with_columns(pl.lit(nm).alias('name')))
    T = T.with_columns(pl.col('day').map_elements(lambda d: C.prev_tday(d), return_dtype=pl.String).alias('_pday'))
    if nv:
        nvd = pl.concat(nv).rename({'day': '_pday', 'volume': '_v0', 'expiry': 'listed'}).with_columns(pl.col('strike').cast(pl.Float64).round(4))
        nvd = nvd.unique(['name', '_pday', 'listed', 'strike', 'right'], keep='first', maintain_order=True)
        T = T.join(nvd, on=['name', '_pday', 'listed', 'strike', 'right'], how='left')
    else:
        T = T.with_columns(pl.lit(None, pl.Int64).alias('_v0'))
    T = T.with_columns(pl.when(pl.col('eb') == '0DTE').then(pl.col('_v0')).otherwise(pl.col('vol')).alias('v3vol'))
    # V6: IV rank at the last close before the entry (0DTE on D: the session before D; an EOD entry on D: D)
    ivr = {nm: ivrank_series(nm) for nm in names}
    rows = []
    for nm, d, eb in T.select('name', 'day', 'eb').unique().iter_rows():
        ref = C.prev_session(d) if eb == '0DTE' else d
        rows.append((nm, d, eb, ivr[nm].get(ref)))
    T = T.join(pl.DataFrame(rows, schema=['name', 'day', 'eb', 'ivr'], orient='row'), on=['name', 'day', 'eb'], how='left')
    # ES2 / ES3 on the EOD entries: RM = F × RV20 × √(sessions to expiry) × √(2/π)
    rv = {}
    for nm, d in T.filter(pl.col('m') == C.EOD_M).select('name', 'day').unique().iter_rows():
        rv[(nm, d)] = D.rv20_through(nm, d)
    nsess = {}
    for d, e in T.filter(pl.col('m') == C.EOD_M).select('day', 'expiry').unique().iter_rows():
        nsess[(d, e)] = len(C.sessions_between(d, e))
    rm = []
    for nm, d, e, F, IM, m in T.select('name', 'day', 'expiry', 'F', 'IM', 'm').iter_rows():
        if m != C.EOD_M:
            rm.append(None)
            continue
        v = rv.get((nm, d), float('nan'))
        n = nsess.get((d, e), 0)
        rm.append(F * v * math.sqrt(n) * SQ2PI if (np.isfinite(v) and n > 0) else None)
    T = T.with_columns(pl.Series('rm_eod', rm, pl.Float64))
    T = T.with_columns(pl.when(pl.col('m') == C.EOD_M).then(pl.col('rm_eod') / pl.col('IM')).otherwise(pl.col('xrm')).alias('xrm'),
                       (pl.col('IM') / pl.col('rm_eod')).alias('im_rm'))
    # UW values at the entry
    uwp = [C.WORK / 'uw' / split / f'{nm}.parquet' for nm in names if nm in C.INDEX]
    uwp = [p for p in uwp if p.exists()]
    if uwp:
        U = pl.concat([pl.read_parquet(p) for p in uwp])
        T = T.join(U, on=['name', 'day', 'm'], how='left')
    else:
        T = T.with_columns([pl.lit(None, pl.Float64).alias(c) for c in ('G', 'flip', 'cw', 'pw', 'd1', 'd2', 'd3', 'd4', 'd5')])
    # V2: open interest published the morning of the entry session
    oi = []
    for (nm, d), g in T.filter(pl.col('name').is_in(list(C.INDEX)) & (pl.col('day') >= UF.UW_FIRST)).group_by('name', 'day'):
        syms = [UF.occ(nm, e, r, k) for e, r, k in g.select('listed', 'right', 'strike').iter_rows()]
        got = UF.oi_for(nm, d, list(set(syms)))
        for tid, s in zip(g['tid'].to_list(), syms):
            oi.append((tid, got.get(s)))
    T = T.join(pl.DataFrame(oi, schema={'tid': pl.UInt32, 'oi': pl.Int64}, orient='row'), on='tid', how='left')
    # V4 / V5: the event windows
    T = add_events(T)
    if T['tid'].n_unique() != T.height:
        raise RuntimeError(f'a join duplicated base trades: {T.height - T["tid"].n_unique()} extra rows')
    return T.drop('_pday', '_v0', 'rm_eod')


def earnings_times() -> dict[str, list[tuple[str, str | None]]]:
    e = pl.read_parquet(C.REPO / 'data_lake' / 'unusualwhales' / 'earnings.parquet', columns=['ticker', 'report_date', 'report_time', 'report_type'])
    e = e.filter(pl.col('ticker').is_in(list(C.SINGLES)) & pl.col('report_date').is_not_null()).unique(['ticker', 'report_date', 'report_time'])
    out = {}
    for t, d, rt, _ in e.iter_rows():
        out.setdefault(t, []).append((d, rt))
    return out


def macro_times() -> list[str]:
    ev = json.loads((C.REPO / 'data' / 'macro_events_2022_2027.json').read_text())
    out = []
    for e in ev:
        if e['event'] == 'FOMC_DECISION':
            out.append(e['date'] + ' 14:00')
        elif e['event'] in ('CPI', 'NFP'):
            out.append(e['date'] + ' 08:30')
    return sorted(out)


def add_events(T: pl.DataFrame) -> pl.DataFrame:
    """V4/V5: an event inside (the last close before the entry minute, the expiry's 16:00): the last close before an entry on D
    is the 16:00 of the trading day before D (an EOD entry is stamped 16:00 on D, so its last close BEFORE is also D−1's);
    pre-market earnings count at E 09:30, post-market at E 16:00, a null time if either reading falls inside"""
    et = earnings_times()
    mt = macro_times()
    v4, v5 = [], []
    cache = {}
    for nm, d, e in T.select('name', 'day', 'expiry').iter_rows():
        key = (nm, d, e)
        if key not in cache:
            p = C.prev_tday(d)
            lo, hi = f'{p} 16:00', f'{e} 16:00'
            a = None
            if nm in C.SINGLES:
                a = False
                for rd, rt in et.get(nm, []):
                    reads = [f'{rd} 09:30'] if rt == 'premarket' else ([f'{rd} 16:00'] if rt == 'postmarket' else [f'{rd} 09:30', f'{rd} 16:00'])
                    if any(lo < x < hi for x in reads):
                        a = True
                        break
            b = None
            if d >= '2022-01-01':
                i = bisect.bisect_right(mt, lo)
                b = i < len(mt) and mt[i] < hi
            cache[key] = (a, b)
        a, b = cache[key]
        v4.append(a)
        v5.append(b)
    return T.with_columns(pl.Series('ev_earn', v4, pl.Boolean), pl.Series('ev_macro', v5, pl.Boolean))


# ---- the features: each returns (with, without) frames over the base trades -----------------------------------------------------

ARM_COLS = ['tid', 'name', 'day', 'm', 'eb', 'sb', 'right', 'tier', 'settle']


def arms(w: pl.DataFrame, wo: pl.DataFrame, col_w='r', col_wo='r'):
    return (w.select(ARM_COLS + [pl.col(col_w).alias('r')]), wo.select(ARM_COLS + [pl.col(col_wo).alias('r')]))


def veto(T, defined, vetoed):
    d = T.filter(defined)
    return arms(d.filter(~vetoed), d)


def choose(T, defined, chosen):
    d = T.filter(defined)
    return arms(d.filter(chosen), d)


def f_V1(T):
    return veto(T, pl.col('spread').is_not_null(), pl.col('spread') > 0.10)


def f_V2(T):
    return veto(T, pl.col('name').is_in(list(C.INDEX)) & pl.col('oi').is_not_null(), pl.col('oi') < 500)


def f_V3(T):
    return veto(T, pl.col('v3vol').is_not_null(), pl.col('v3vol') < 100)


def f_V4(T):
    return veto(T, pl.col('ev_earn').is_not_null(), pl.col('ev_earn'))


def f_V5(T):
    return veto(T, pl.col('ev_macro').is_not_null(), pl.col('ev_macro'))


def f_V6(T):
    return veto(T, pl.col('ivr').is_not_null(), pl.col('ivr') >= 0.80)


def f_VN1(T):
    x = T.filter(pl.col('name').is_in(['SPY', 'SPXW'])).with_columns(
        (((pl.col('ask') - pl.col('mid')) + pl.when(pl.col('name') == 'SPXW')
          .then(pl.when(pl.col('ask') < 1.0).then(C.FEE_SPXW_LO).otherwise(C.FEE_SPXW_HI)).otherwise(C.FEE_ETF) / 100.0) / pl.col('mid')).alias('c'))
    key = ['day', 'm', 'eb', 'sb', 'right']
    x = x.with_columns(pl.col('name').n_unique().over(key).alias('_n'), pl.col('c').min().over(key).alias('_cmin'))
    x = x.filter(pl.col('_n') == 2)
    return arms(x.filter((pl.col('c') - pl.col('_cmin')).abs() <= 1e-12), x)


def eod_bucket_choice(T, val: str, label: str):
    """ES1/ES2: at an EOD entry keep only the multi-day expiry bucket with the lowest value (same ticker, side, strike bucket)"""
    e = T.filter((pl.col('m') == C.EOD_M) & pl.col(val).is_not_null() & pl.col(val).is_finite())
    per = e.group_by('name', 'day', 'eb').agg(pl.col(val).first().alias('_v'))
    per = per.with_columns(pl.col('eb').n_unique().over('name', 'day').alias('_k'))
    per = per.filter(pl.col('_k') >= 2)
    best = per.sort(['name', 'day', '_v', 'eb']).group_by('name', 'day', maintain_order=True).agg(pl.col('eb').first().alias('_best'))
    x = e.join(per.select('name', 'day', 'eb'), on=['name', 'day', 'eb'], how='inner').join(best, on=['name', 'day'], how='inner')
    return arms(x.filter(pl.col('eb') == pl.col('_best')), x)


def f_ES1(T):
    return eod_bucket_choice(T, 'atm_iv', 'ATM IV')


def f_ES2(T):
    return eod_bucket_choice(T, 'im_rm', 'IM ÷ RM')


def f_ES3(T):
    b = pl.when(pl.col('xrm') <= 0.15).then(pl.lit('ATM')).when(pl.col('xrm') <= 0.50).then(pl.lit('OTM1')) \
        .when(pl.col('xrm') <= 1.00).then(pl.lit('OTM2')).otherwise(pl.lit('OTM3'))
    return choose(T, pl.col('xrm').is_not_null() & pl.col('xrm').is_finite(), pl.col('sb') == b)


def f_ES4(T):
    key = ['name', 'day', 'm', 'eb', 'right']
    x = T.filter(pl.col('delta').is_not_null()).with_columns((pl.col('delta').abs() - 0.30).abs().alias('_d'), pl.col('x').abs().alias('_ax'))
    best = x.sort(key + ['_d', '_ax']).group_by(key, maintain_order=True).agg(pl.col('tid').first().alias('_best'))
    x = x.join(best, on=key)
    return arms(x.filter(pl.col('tid') == pl.col('_best')), x)


def f_SD1(T):
    d = pl.col('name').is_in(list(C.INDEX)) & pl.col('G').is_not_null() & (pl.col('G') != 0)
    return choose(T, d, pl.col('sb') == pl.when(pl.col('G') > 0).then(pl.lit('ATM')).otherwise(pl.lit('OTM2')))


def f_SD2(T):
    d = pl.col('name').is_in(list(C.INDEX)) & pl.col('flip').is_not_null() & pl.col('S').is_not_null() & pl.col('S').is_finite() \
        & (pl.col('S') != pl.col('flip'))
    return choose(T, d, pl.col('sb') == pl.when(pl.col('S') > pl.col('flip')).then(pl.lit('ATM')).otherwise(pl.lit('OTM2')))


def f_X1(T):
    d = T.filter(pl.col('x1_def') == True)  # noqa: E712
    return arms(d, d, 'r_x1', 'r')


def f_X2(T):
    if 'r_x2' not in T.columns:
        raise RuntimeError('X2 exits were not computed')
    d = T.filter(pl.col('x2_def') == True)  # noqa: E712
    return arms(d, d, 'r_x2', 'r')


def f_X3(T):
    d = T.filter((pl.col('eb') == '0DTE') & (pl.col('m') < C.X3_M) & pl.col('r_x3').is_not_null())
    return arms(d, d, 'r_x3', 'r')


def direction(T, col, extra=None):
    d = pl.col(col).is_not_null() & (pl.col(col) != 0)
    if extra is not None:
        d = d & extra
    return choose(T, d, (pl.col('right') == 'C') == (pl.col(col) > 0))


def f_D1(T):
    return direction(T, 'd1', pl.col('name').is_in(list(C.INDEX)))


def f_D2(T):
    return direction(T, 'd2', pl.col('name').is_in(list(C.INDEX)))


def f_D3(T):
    return direction(T, 'd3', pl.col('name').is_in(list(C.INDEX)))


def f_D4(T):
    return direction(T, 'd4', pl.col('name').is_in(list(C.INDEX)))


def f_D5(T):
    return direction(T, 'd5', pl.col('name').is_in(['SPY', 'QQQ', 'IWM']))


def f_D6(T):
    return direction(T, 'd6', (pl.col('eb') == '0DTE') & (pl.col('m') >= C.mi('10:15')))


def f_D7(T):
    return direction(T, 'd7')


FEATURES = [
    ('V1', 'veto', 'spread: veto when (ask − bid) ÷ mid at the entry quote > 10%', 'ThetaData chain / EOD', f_V1, False),
    ('V2', 'veto', 'open interest: veto when the contract\'s OI published the morning of the entry session < 500', 'UW option-contracts?date=D', f_V2, False),
    ('V3', 'veto', 'volume: veto when the contract\'s volume on the last completed session < 100', 'ThetaData option EOD volume', f_V3, False),
    ('V4', 'veto', 'earnings: veto when a release falls between the last close before entry and the expiry\'s 16:00', 'UW earnings calendar', f_V4, False),
    ('V5', 'veto', 'macro: the same window for an FOMC decision, CPI or NFP', 'data/macro_events_2022_2027.json', f_V5, False),
    ('V6', 'veto', 'IV rank: veto when IV rank ≥ 0.80', 'ThetaData option EOD', f_V6, False),
    ('VN1', 'venue', 'entry cost share: keep the SPXW/SPY venue with the lower ((ask − mid) + fee ÷ 100) ÷ mid', 'ThetaData chains / EOD', f_VN1, False),
    ('ES1', 'expiry', 'term structure: keep the multi-day expiry bucket with the lowest at-the-money IV', 'ThetaData EOD', f_ES1, False),
    ('ES2', 'expiry', 'implied vs realized: keep the expiry bucket with the lowest IM ÷ RM', 'ThetaData EOD and bars', f_ES2, False),
    ('ES3', 'strike', 'distance: keep the strike bucket containing x_RM = RM ÷ IM', 'ThetaData chains / EOD and bars', f_ES3, False),
    ('ES4', 'strike', 'delta: keep the strike bucket whose contract\'s |delta| is nearest 0.30', 'ThetaData chains / EOD', f_ES4, False),
    ('SD1', 'strike', 'UW GEX regime: G > 0 keep ATM, G < 0 keep OTM2', 'UW spot-exposures', f_SD1, True),
    ('SD2', 'strike', 'UW flip: price above the prior session\'s flip keep ATM, below keep OTM2', 'UW gex-levels (D−1)', f_SD2, True),
    ('X1', 'exit', 'the implied move as the target', 'ThetaData chains / EOD, bars', f_X1, False),
    ('X2', 'exit', 'UW\'s walls (prior session) as targets', 'UW greek-exposure/strike (D−1)', f_X2, True),
    ('X3', 'exit', '0DTE entries before 14:00 sold at the 14:00 bid', 'ThetaData chains', f_X3, False),
    ('D1', 'direction', 'net premium since 09:30', 'UW net-prem-ticks', f_D1, False),
    ('D2', 'direction', 'sweep alerts: calls (ask − bid premium) − puts', 'UW flow-alerts', f_D2, False),
    ('D3', 'direction', 'NOPE of the last complete minute', 'UW nope', f_D3, False),
    ('D4', 'direction', 'market tide: net call − net put premium', 'UW market-tide', f_D4, False),
    ('D5', 'direction', 'dark pool: Σ premium × sign(price − NBBO mid), prints ≥ $1M', 'UW darkpool', f_D5, False),
    ('D6', 'direction', 'opening range: above ORH → call, below ORL → put (0DTE from 10:15)', 'ThetaData bars / SPX prints', f_D6, False),
    ('D7', 'direction', 'prior-day structure: above the prior high → call, below the prior low → put', 'ThetaData bars / SPX prints', f_D7, False),
]
BY_ID = {f[0]: f for f in FEATURES}


def evaluate(fid: str, T: pl.DataFrame, sess_all: list[str]) -> dict:
    _, fam, desc, src, fn, gex = BY_ID[fid]
    w, wo = fn(T)
    res = dict(id=fid, family=fam, decision=desc, source=src, gex=gex)
    if wo.height == 0:
        res.update(status='not tested — no data', trades_with=0, trades_without=0)
        return res
    a, b = wo['day'].min(), wo['day'].max()
    sess = [d for d in sess_all if a <= d <= b]
    res['span'] = dict(first=a, last=b, sessions=len(sess), names=sorted(set(wo['name'].to_list())),
                       buckets=sorted(set(wo['eb'].to_list())))
    res['pooled'] = ST.delta(w, wo, sess)
    res['by_tier'] = {t: ST.delta(w.filter(pl.col('tier') == t), wo.filter(pl.col('tier') == t), sess, full=False)
                      for t in ('1', '2', '3', 'U') if wo.filter(pl.col('tier') == t).height}
    res['by_settle'] = {t: ST.delta(w.filter(pl.col('settle') == t), wo.filter(pl.col('settle') == t), sess, full=False)
                        for t in ('physical', 'cash') if wo.filter(pl.col('settle') == t).height}
    res['by_bucket'] = {t: ST.delta(w.filter(pl.col('eb') == t), wo.filter(pl.col('eb') == t), sess, full=False)
                        for t in ('0DTE', '1-7', '8-30', '31-60') if wo.filter(pl.col('eb') == t).height}
    res['pass'] = ST.passes(res['pooled'])
    return res


def base_summary(T: pl.DataFrame, sess_all: list[str]) -> dict:
    out = {}
    a, b = T['day'].min(), T['day'].max()
    sess = [d for d in sess_all if a <= d <= b]
    idx = {d: i for i, d in enumerate(sess)}

    def st(x):
        S, N = ST.per_session(x, sess)
        return ST.clean(AL_stats(S, N))
    out['all'] = st(T)
    for col, vals in (('eb', ('0DTE', '1-7', '8-30', '31-60')), ('tier', ('1', '2', '3', 'U')), ('settle', ('physical', 'cash'))):
        for v in vals:
            x = T.filter(pl.col(col) == v)
            if x.height:
                out[f'{col}={v}'] = st(x)
    for nm in sorted(set(T['name'].to_list())):
        out[f'name={nm}'] = st(T.filter(pl.col('name') == nm))
    out['sessions'] = dict(first=a, last=b, n=len(sess))
    return out


def AL_stats(S, N):
    return C.AL.session_stats(S, N, blocks=(1, 20))


STAGE_A = ('V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'VN1', 'ES1', 'ES2', 'ES3', 'ES4')
STAGE_B = ('SD1', 'SD2', 'X1', 'X2', 'X3', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7')


def holdout_parts(fid: str, T: pl.DataFrame, sess_all: list[str]) -> dict:
    """the holdout's two parts, descriptive: the held-out tickers over all months; the exploration tickers over the
    held-out months"""
    w, wo = BY_ID[fid][4](T)
    out = {}
    for label, cond in (('held-out tickers, all months', pl.col('name').is_in(list(C.HELD_T))),
                        ('exploration tickers, held-out months', ~pl.col('name').is_in(list(C.HELD_T)))):
        a, b = w.filter(cond), wo.filter(cond)
        if b.height:
            x, y = b['day'].min(), b['day'].max()
            out[label] = ST.delta(a, b, [d for d in sess_all if x <= d <= y], full=False)
    return out


def main():
    split = sys.argv[1]
    C.set_split(split)
    t0 = time.time()
    stage = None
    if split == 'hold':
        want = sys.argv[2:]
        scr = json.loads((C.OUT / 'screen_expl.json').read_text())
        passed = [f['id'] for f in scr['features'] if f.get('pass')]
        bad = [f for f in want if f not in passed]
        if bad:
            raise SystemExit(f'not passed on the exploration screen: {bad}')
        if (C.OUT / 'holdout.json').exists():
            raise SystemExit('the holdout was already read (out/holdout.json exists)')
        ids = want
    else:
        stage = sys.argv[2] if len(sys.argv) > 2 else 'A'
        ids = list(STAGE_A if stage == 'A' else STAGE_B)
    cache = C.WORK / split / 'trades_with_inputs.parquet'
    if split == 'expl' and stage == 'B' and cache.exists():
        T = pl.read_parquet(cache)
    else:
        T = load_base(split)
        print('base', T.height, f'{time.time() - t0:.0f}s', flush=True)
        T = add_inputs(T, split)
        C.write_parquet(T, cache)
    xp = C.WORK / split / 'x2.parquet'
    if xp.exists():
        T = T.join(pl.read_parquet(xp).drop('x2_hit'), on=['name', 'day', 'm', 'eb', 'strike', 'right', 'sb'], how='left')
    print('inputs', T.height, f'{time.time() - t0:.0f}s', flush=True)
    sess_all = split_sessions(split)
    gate = None
    gp = C.OUT / 'gex_check.json'
    if gp.exists():
        gate = json.loads(gp.read_text())['gate']
    dest = C.OUT / ('screen_expl.json' if split == 'expl' else 'holdout.json')
    out = json.loads(dest.read_text()) if (split == 'expl' and stage == 'B' and dest.exists()) else \
        dict(split=split, prereg=C.PREREG_COMMIT, base=base_summary(T, sess_all), features=[])
    out['features'] = [f for f in out['features'] if f['id'] not in ids]
    for fid in ids:
        f = BY_ID[fid]
        if f[5] and split == 'expl' and gate is not True:
            out['features'].append(dict(id=fid, family=f[1], decision=f[2], source=f[3], gex=True, **{'pass': False},
                                        status='dropped by the GEX check (untested)' if gate is False else 'GEX check not run'))
            print(fid, 'dropped', gate, flush=True)
            continue
        res = evaluate(fid, T, sess_all)
        if split == 'hold':
            res['parts'] = holdout_parts(fid, T, sess_all)
        out['features'].append(res)
        p = res.get('pooled', {})
        print(fid, res.get('status', ''), p.get('trades_with'), p.get('trades_without'), p.get('delta'), p.get('ci'), res.get('pass'),
              f'{time.time() - t0:.0f}s', flush=True)
    order = [f[0] for f in FEATURES]
    out['features'].sort(key=lambda f: order.index(f['id']))
    C.jdump(out, dest)


if __name__ == '__main__':
    main()
