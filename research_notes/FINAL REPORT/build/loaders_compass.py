"""loaders_compass.py — the trade frames of the 2026-10-21/22 Compass studies (phase 2, phase 3, the paper tracker, the
after-hours study, the SPXW analogues, the picker). Each returns the standard frame (base.STD)."""
from __future__ import annotations

import json
import sys

import numpy as np
import polars as pl

from base import DR, RN, WORK, std

P2 = RN / 'Compass phase 2'
P3 = RN / 'Compass phase 3'
sys.path.insert(0, str(P3 / 'backtest_audit'))
import audit_lib as AL  # noqa: E402


def _occ(sym: str | None) -> str:
    if not sym:
        return ''
    b = sym[-15:]
    return f"{b[6]}{int(b[7:]) / 1000:g}"


# ---- the paper tracker's replay (official-close settlement), every trade ------------------------------------------------------------

def tracker_rows() -> pl.DataFrame:
    cache = WORK / 'tracker_settle.parquet'
    if cache.exists():
        return pl.read_parquet(cache)
    df = AL.load_rows(DR / 'paper_backtest_official')
    s = df.filter((pl.col('row_kind') == 'settle') & (pl.col('tradable') == 'true'))
    s = s.with_columns(pl.struct(['candidate', '_day']).map_elements(lambda r: AL.period_of(r['candidate'], r['_day']),
                                                                     return_dtype=pl.Utf8).alias('per'))
    keep = ['candidate', '_name', '_day', 'minute', 'structure', 'per', 'settle_source', 'price_nbbo_f', 'max_risk_f', 'pnl_nbbo_f',
            'package'] + [f'l{i}_symbol' for i in range(1, 5)] + [f'l{i}_side' for i in range(1, 5)]
    s = s.select(keep)
    s.write_parquet(cache)
    return s


def tracker(cand: str) -> pl.DataFrame:
    s = tracker_rows().filter(pl.col('candidate') == cand)
    rows = []
    for r in s.iter_rows(named=True):
        legs = '/'.join(f"{'+' if r[f'l{i}_side'] == 'long' else '−'}{_occ(r[f'l{i}_symbol'])}" for i in range(1, 5) if r[f'l{i}_symbol'])
        inst = r['_name'] if cand != 'fly5' else f"{r['_name']} {r['structure']}"
        rows.append({'date': r['_day'], 'inst': inst, 'period': r['per'], 'contract': f"{r['_name']} {r['minute']} {legs}",
                     'cost': r['max_risk_f'] * 100, 'pnl': r['pnl_nbbo_f'], 'reason': 'held to settlement (official close)'})
    return std(pl.DataFrame(rows))


# ---- the after-hours study: case (b), the post-market decision -----------------------------------------------------------------------

def afterhours(cand: str) -> pl.DataFrame:
    a = pl.read_csv(P3 / 'backtest_audit' / 'out' / 'afterhours_trades.csv', infer_schema_length=100000)
    a = a.filter((pl.col('candidate') == cand) & ((pl.col('structure') == 'iron') | (pl.lit(cand) != 'fly5')))
    t = tracker_rows().filter(pl.col('candidate') == cand).select(
        pl.col('_name').alias('name'), pl.col('_day').alias('day'), 'minute', 'structure', 'max_risk_f')
    a = a.join(t, on=['name', 'day', 'minute', 'structure'], how='left')
    a = a.filter(pl.col('pnl_b').is_not_null())
    return std(a.select(pl.col('day').alias('date'), pl.col('name').alias('inst'), pl.col('period'),
                        (pl.col('name') + ' ' + pl.col('minute') + ' ' + pl.col('legs').cast(pl.Utf8)).alias('contract'),
                        (pl.col('max_risk_f') * 100).alias('cost'), pl.col('pnl_b').alias('pnl'),
                        pl.lit('held; after-hours decision (b) on the 17:30 price').alias('reason')))


# ---- the SPXW analogues (package fill, official SPX close) ------------------------------------------------------------------------------

def spxw(analogue: str) -> pl.DataFrame:
    d = pl.read_parquet(P3 / 'spxw_prereg' / 'out' / 'trades.parquet').filter(pl.col('tradable') & (pl.col('analogue') == analogue))
    con = pl.concat_str([pl.lit('SPXW '), pl.col('minute'), pl.lit(' '), pl.col('k_lp').cast(pl.Utf8), pl.lit('/'), pl.col('k_sp').cast(pl.Utf8),
                         pl.lit('P '), pl.col('k_sc').cast(pl.Utf8), pl.lit('/'), pl.col('k_lc').cast(pl.Utf8), pl.lit('C')])
    return std(d.select(pl.col('day').alias('date'), pl.lit('SPXW').alias('inst'), pl.col('period'), con.alias('contract'),
                        pl.col('risk_pkg').alias('cost'), pl.col('pnl_pkg_off').alias('pnl'),
                        pl.lit('held to cash settlement (official SPX close)').alias('reason')))


# ---- the picker (five runs) ------------------------------------------------------------------------------------------------------------

def picker(run: str) -> pl.DataFrame:
    d = pl.read_csv(P3 / 'picker_prereg' / 'out' / f'trades_{run}.csv', infer_schema_length=100000)
    per = pl.when(pl.col('session') >= '2026-10-14').then(pl.lit('never-read 2026-10-14→21')).otherwise(pl.lit('whole span (card dates out)'))
    con = pl.concat_str([pl.col('name'), pl.lit(' '), pl.col('session'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('side').str.slice(0, 1)])
    return std(d.select(pl.col('session').alias('date'), pl.col('name').alias('inst'), per.alias('period'), con.alias('contract'),
                        (pl.col('entry_ask') * 100).alias('cost'), pl.col('pnl'), pl.col('reason')))


# ---- phase 2 ---------------------------------------------------------------------------------------------------------------------------

def hyp_a() -> pl.DataFrame:
    d = pl.read_csv(P2 / 'hyp_a_closing_pin' / 'out' / 'pick_rows.csv', infer_schema_length=100000)
    con = pl.concat_str([pl.lit('SPXW 15:30 '), pl.col('Ks').cast(pl.Utf8), pl.lit('/'), pl.col('Kl').cast(pl.Utf8), pl.lit('C')])
    per = pl.when(pl.col('period') == 'fit').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))
    return std(d.select(pl.col('date'), pl.lit('SPXW').alias('inst'), per.alias('period'), con.alias('contract'),
                        pl.col('max_risk').alias('cost'), pl.col('pnl'), pl.lit('held to settlement').alias('reason')))


def _hb_period():
    return pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))


def hyp_b(which: str) -> pl.DataFrame:
    X = pl.read_parquet(P2 / 'hyp_b_boundary_theta' / 'out' / 'trades_SPY.parquet')
    if which == 'touch':
        T = X.filter(pl.col('test') == 'touch')
        T1 = T.sort('session', 'touch_side', 'e', 'mult', 'rule', 'width', 'm_scan').unique(
            subset=['session', 'touch_side', 'e', 'mult', 'rule', 'width'], keep='first')
        g = T1.filter((pl.col('mult') == 1.0) & (pl.col('width') == 2.0) & (pl.col('rule') == 'd25'))
        con = pl.concat_str([pl.lit('SPY '), pl.col('short_k').cast(pl.Utf8), pl.lit('/'), pl.col('long_k').cast(pl.Utf8), pl.lit(' '),
                             pl.col('touch_side')])
    else:
        MID = [120, 150, 180, 210, 240]
        fitv = X.filter((pl.col('session') <= '2024-12-31') & (pl.col('test') == 'sched') & pl.col('m_scan').is_in(MID)
                        & (pl.col('structure') == 'condor') & (pl.col('rule') == 'd15') & (pl.col('width') == 1.0))
        vq = fitv['vix_e'].drop_nulls().to_numpy()
        v1, v2 = float(np.percentile(vq, 100 / 3)), float(np.percentile(vq, 200 / 3))
        g = X.filter((pl.col('test') == 'sched') & pl.col('m_scan').is_in(MID) & (pl.col('structure') == 'condor')
                     & (pl.col('width') == 2.0) & (pl.col('rule') == 'em1') & (pl.col('vix_e') >= v1) & (pl.col('vix_e') < v2))
        con = pl.concat_str([pl.lit('SPY condor short '), pl.col('short_k').cast(pl.Utf8), pl.lit(' m'), pl.col('m_scan').cast(pl.Utf8)])
    g = g.filter(pl.col('pnl_hold').is_not_null())
    return std(g.select(pl.col('session').alias('date'), pl.lit('SPY').alias('inst'), _hb_period().alias('period'), con.alias('contract'),
                        pl.col('max_risk').alias('cost'), pl.col('pnl_hold').alias('pnl'), pl.lit('held to settlement').alias('reason')))


def hyp_c_fly(kind: str, wing: str, t: str = '1500') -> pl.DataFrame:
    fr = []
    for P in ('SPY', 'QQQ'):
        d = pl.read_parquet(P2 / 'hyp_c_debit_flies' / 'out' / f'flies_{P}.parquet')
        d = d.filter((pl.col('t') == t) & (pl.col('kind') == kind) & (pl.col('wing') == wing) & pl.col('pnl').is_not_null())
        fr.append(d)
    d = pl.concat(fr)
    per = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))
    con = pl.concat_str([pl.col('product'), pl.lit(f' {t} {kind} K0 '), pl.col('K0').cast(pl.Utf8), pl.lit(' ±'), pl.col('W').cast(pl.Utf8)])
    return std(d.select(pl.col('session').alias('date'), pl.col('product').alias('inst'), per.alias('period'), con.alias('contract'),
                        (pl.col('risk') * 100).alias('cost'), pl.col('pnl'), pl.lit('held to settlement').alias('reason')))


def hyp_c_vertical(universe: str, exit_: str) -> pl.DataFrame:
    d = pl.read_parquet(P2 / 'hyp_c_debit_flies' / 'out' / 'spreads_trades.parquet').filter(
        (pl.col('universe') == universe) & (pl.col('cell') == 'd70_30') & (pl.col('exit') == exit_) & pl.col('pnl').is_not_null())
    per = pl.when(pl.col('period') == 'fit').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))
    con = pl.concat_str([pl.col('product'), pl.lit(' '), pl.col('side'), pl.lit(' 0.70/0.30 m'), pl.col('entry_m').cast(pl.Utf8)])
    return std(d.select(pl.col('session').alias('date'), pl.col('product').alias('inst'), per.alias('period'), con.alias('contract'),
                        (pl.col('debit') * 100).alias('cost'), pl.col('pnl'), pl.col('reason')))


# ---- phase 3 F -------------------------------------------------------------------------------------------------------------------------

def hyp_f(form: str = 'call', t: str = '1530') -> pl.DataFrame:
    fr = []
    for per, f in (('fit 2022-11→2024', 'flies_fit.parquet'), ('OOS 2025–26', 'flies_oos.parquet')):
        d = pl.read_parquet(P3 / 'hyp_f_cash_butterfly' / 'out' / f).filter(
            (pl.col('form') == form) & (pl.col('t') == t) & pl.col('pnl_nbbo').is_not_null())
        fr.append(d.with_columns(pl.lit(per).alias('per')))
    d = pl.concat(fr, how='diagonal_relaxed')
    con = pl.concat_str([pl.col('product'), pl.lit(f' {t} {form} fly K0 '), pl.col('K0').cast(pl.Utf8), pl.lit(' ±5')])
    return std(d.select(pl.col('session').alias('date'), pl.col('product').alias('inst'), pl.col('per').alias('period'), con.alias('contract'),
                        (pl.col('risk_nbbo') * 100).alias('cost'), pl.col('pnl_nbbo').alias('pnl'), pl.lit('held to settlement').alias('reason')))
