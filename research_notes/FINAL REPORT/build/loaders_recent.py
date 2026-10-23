"""loaders_recent.py — the trade frames of the 2026-10-16 → 23 studies: steps 2, 4, 6, the Compass features (#30), the
direction rerun (#31), H1, H3, H4, H7, H8, the EMA ladder rerun (#40), the EMA system (#41), Compass ICT (#43)."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import polars as pl

from base import REPO, RN, SP, SP2, WORK, std

FEE = 0.65


# ---- steps 2 and 4 (formulas copied from step2/summarize.py and step4/summarize.py, unchanged) ------------------------------------------

def _settle():
    return pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise(
        (pl.col('strike') - pl.col('spot_close')).clip(0))


def _otm():
    sgn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    return sgn * (pl.col('strike') - pl.col('spot_entry')) / pl.col('spot_entry') * 100


def _pc():
    return pl.when(pl.col('session') < pl.date(2025, 1, 1)).then(pl.lit('pick 2022–24')).otherwise(pl.lit('check 2025–26'))


def step2_near() -> pl.DataFrame:
    """every step 2 trade within 0.5% of the money, sold at +100% or held to the close"""
    cache = WORK / 'step2_near.parquet'
    if cache.exists():
        return pl.read_parquet(cache)
    sys.path.insert(0, str(REPO))
    from step2.double import load  # the committed loader (derived columns: tp100 etc.)
    fr = []
    for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        T = load(root).filter(pl.col('otm_entry_pct').abs() <= 0.5)
        hit = pl.col('double_minute').is_not_null()
        net = (pl.col('tp100') * 100 - FEE - pl.when(hit | (pl.col('settle') > 0)).then(FEE).otherwise(0))
        why = pl.when(hit).then(pl.lit('+100% target')).otherwise(pl.lit('held to the close'))
        con = pl.concat_str([pl.lit(root + ' '), pl.col('strike').cast(pl.Utf8), pl.col('right').str.slice(0, 1), pl.lit(' m'), pl.col('entry_minute').cast(pl.Utf8)])
        fr.append(T.select(pl.col('session').alias('date'), pl.lit(root).alias('inst'), _pc().alias('period'), con.alias('contract'),
                           (pl.col('entry_ask') * 100).alias('cost'), net.alias('pnl'), why.alias('reason')))
    d = std(pl.concat(fr))
    d.write_parquet(cache)
    return d


def step4(tag: str = 'bounce1.5', exit_: str = 'trail20') -> pl.DataFrame:
    cache = WORK / f'step4_{tag}_{exit_}.parquet'
    if cache.exists():
        return pl.read_parquet(cache)
    fr = []
    for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        T = pl.read_parquet(REPO / 'step4' / 'out' / f'trades_{root}.parquet').filter(pl.col('tag') == tag)
        T = T.with_columns(_settle().alias('settle'), _otm().alias('otm')).filter(pl.col('otm').abs() <= 0.5)
        hit = pl.col(exit_ + '_minute').is_not_null()
        price = pl.when(hit).then(pl.col(exit_ + '_bid')).otherwise(pl.col('settle'))
        sold = hit | (pl.col('settle') > 0)
        net = (price - pl.col('entry_ask')) * 100 - FEE - pl.when(sold).then(FEE).otherwise(0.0)
        why = pl.when(hit).then(pl.lit(exit_.replace('trail', '') + '% trailing stop')).otherwise(pl.lit('held to the close'))
        con = pl.concat_str([pl.lit(root + ' '), pl.col('strike').cast(pl.Utf8), pl.col('right').str.slice(0, 1), pl.lit(' m'), pl.col('entry_minute').cast(pl.Utf8)])
        fr.append(T.select(pl.col('session').alias('date'), pl.lit(root).alias('inst'), _pc().alias('period'), con.alias('contract'),
                           (pl.col('entry_ask') * 100).alias('cost'), net.alias('pnl'), why.alias('reason')))
    d = std(pl.concat(fr))
    d.write_parquet(cache)
    return d


# ---- step 6: the six rules' trades, chosen by the committed step6/trade.py choose() on the scratchpad population ---------------------------

def step6_rules() -> pl.DataFrame:
    cache = WORK / 'step6_rules.parquet'
    if cache.exists():
        return pl.read_parquet(cache)
    sys.path.insert(0, str(REPO))
    from step6 import trade as T6
    from step6.data import load
    T = load()
    memb = pl.read_parquet(os.path.join(T6.WORK, 'membership.parquet'))
    chosen, _ = T6.choose(T, memb)
    fr = []
    for fam, taken in chosen.items():
        for t in taken:
            G = T.filter(pl.Series(t['mask']))
            for x, lab in T6.EXITS.items():
                con = pl.concat_str([pl.col('product'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('right').str.slice(0, 1),
                                     pl.lit(' m'), pl.col('entry_minute').cast(pl.Utf8)])
                why = pl.col(f'why_{x}') if f'why_{x}' in G.columns else pl.lit(lab)
                fr.append(G.select(pl.col('date').cast(pl.Utf8).alias('date'), pl.lit(f'{fam}{t["rank"]}{x}').alias('inst'),
                                   pl.col('period').replace({'pick': 'pick 2022-05→2024', 'check': 'check 2025→2026-10-09'}).alias('period'),
                                   con.alias('contract'), (pl.col('entry_ask') * 100).alias('cost'), pl.col(f'net_{x}').alias('pnl'),
                                   why.cast(pl.Utf8).alias('reason')))
    d = std(pl.concat(fr, how='vertical_relaxed'))
    d.write_parquet(cache)
    return d


# ---- #30 Compass features: the base trades and the passed decisions --------------------------------------------------------------------

FW = SP / 'features_work'
X3_M = None


def features(which: str) -> pl.DataFrame:
    global X3_M
    if X3_M is None:
        sys.path.insert(0, str(RN / 'Compass features' / 'run'))
        import fcommon as C
        X3_M = C.X3_M
    fr = []
    for per, sub in (('exploration', 'expl'), ('holdout (opened)', 'hold')):
        T = pl.read_parquet(FW / sub / 'trades_with_inputs.parquet', columns=['name', 'day', 'm', 'eb', 'strike', 'right', 'ask', 'spread', 'r', 'pnl', 'r_x3', 'settle'])
        T = T.with_columns(pl.lit(per).alias('per'), (pl.col('ask') * 100).alias('cost'))
        if which == 'base':
            g = T.with_columns(pl.col('pnl').alias('p'), pl.lit('fixed exit').alias('why'))
        elif which == 'V1':
            g = T.filter(pl.col('spread').is_not_null() & (pl.col('spread') <= 0.10)).with_columns(pl.col('pnl').alias('p'), pl.lit('fixed exit').alias('why'))
        elif which == 'BV1b':
            g = T.filter(pl.col('spread').is_not_null() & (pl.col('spread') <= 0.03)).with_columns(pl.col('pnl').alias('p'), pl.lit('fixed exit').alias('why'))
        elif which in ('X3', 'BX3e'):
            g = T.filter((pl.col('eb') == '0DTE') & (pl.col('m') < X3_M) & pl.col('r_x3').is_not_null())
            if which == 'BX3e':
                g = g.filter(pl.col('settle') == 'physical')
            g = g.with_columns((pl.col('r_x3') * pl.col('cost')).alias('p'), pl.lit('sold at the 14:00 bid').alias('why'))
        else:
            raise ValueError(which)
        fr.append(g)
    d = pl.concat(fr, how='vertical_relaxed')
    con = pl.concat_str([pl.col('name'), pl.lit(' '), pl.col('eb'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('right').cast(pl.Utf8).str.slice(0, 1)])
    return std(d.select(pl.col('day').alias('date'), pl.lit('0DTE→60 DTE, 15 names').alias('inst'), pl.col('per').alias('period'), con.alias('contract'),
                        pl.col('cost'), pl.col('p').alias('pnl'), pl.col('why').alias('reason')))


# ---- #31 Compass direction (the deterministic rerun at 94fb69d) ---------------------------------------------------------------------------

def direction(picked_only: bool = True) -> pl.DataFrame:
    d = pl.read_parquet(SP2 / 'dir' / 'work' / 'expl_trades.parquet')
    if picked_only:
        d = d.filter(pl.col('picked'))
    cost = pl.when(pl.col('r').abs() > 1e-12).then(pl.col('pnl') / pl.col('r')).otherwise(pl.col('ask') * 100)
    why = pl.when(pl.col('exit_zero')).then(pl.lit('no bid at exit ($0)')).otherwise(pl.lit('closing bid 10 sessions later'))
    return std(d.select(pl.col('day').alias('date'), pl.lit('single names').alias('inst'), pl.lit('exploration (holdout unopened)').alias('period'),
                        pl.concat_str([pl.col('ticker'), pl.lit(' '), pl.col('expiry').cast(pl.Utf8), pl.lit(' '), pl.col('strike').cast(pl.Utf8),
                                       pl.col('right').cast(pl.Utf8).str.slice(0, 1)]).alias('contract'),
                        cost.alias('cost'), pl.col('pnl'), why.alias('reason')))


# ---- stock studies: H1, H4, H7, H8 ---------------------------------------------------------------------------------------------------

def h1() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Compass H1' / 'out' / 'h1_sessions.csv', infer_schema_length=100000).filter(
        (pl.col('excluded').fill_null('') == '') & pl.col('side').is_in([1, -1]))
    side = pl.when(pl.col('side') == 1).then(pl.lit('long')).otherwise(pl.lit('short'))
    return std(d.select(pl.col('day').alias('date'), pl.col('name').alias('inst'), pl.lit('single test').alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' '), side]).alias('contract'), (pl.col('C') * 100).alias('cost'),
                        pl.col('net_1x').alias('pnl'), pl.lit('next 09:30 open').alias('reason')))


def h4() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H4' / 'out' / 'h4_sessions.csv', infer_schema_length=100000).filter(
        (pl.col('excluded').fill_null('') == '') & pl.col('side').is_in([1, -1]))
    side = pl.when(pl.col('side') == 1).then(pl.lit('long')).otherwise(pl.lit('short'))
    per = pl.when(pl.col('span') == 'test').then(pl.lit('test 2025-10-13→2026-10-22')).otherwise(pl.lit('exploration (context)'))
    return std(d.select(pl.col('day').alias('date'), pl.col('name').alias('inst'), per.alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' '), side]).alias('contract'), (pl.col('E') * 100).alias('cost'),
                        pl.col('net_1x').alias('pnl'), pl.lit('official close').alias('reason')))


def h7() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H7_H8_H9' / 'out' / 'h7_trades.csv', infer_schema_length=100000).filter(pl.col('excluded').fill_null('') == '')
    return std(d.select(pl.col('prev').alias('date'), pl.col('name').alias('inst'), pl.lit('single test').alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' long, FOMC '), pl.col('A')]).alias('contract'),
                        (pl.col('C_prev') * 100).alias('cost'), pl.col('net_1x').alias('pnl'), pl.lit('13:58 bar close on the statement day').alias('reason')))


def h8() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H7_H8_H9' / 'out' / 'h8_trades.csv', infer_schema_length=100000).filter(pl.col('excluded').fill_null('') == '')
    return std(d.select(pl.col('E').alias('date'), pl.col('name').alias('inst'), pl.lit('single test').alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' long, turn '), pl.col('M').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('C_E') * 100).alias('cost'), pl.col('net_1x').alias('pnl'), pl.lit('official close, 3rd session').alias('reason')))


def h3() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H3' / 'out' / 'trades_expl.csv', infer_schema_length=100000)
    cost = pl.when(pl.col('pct_risk').abs() > 1e-12).then(pl.col('pnl') / pl.col('pct_risk')).otherwise(None)
    return std(d.select(pl.col('P').alias('date'), pl.lit('single names').alias('inst'), pl.lit('exploration (holdout unopened)').alias('period'),
                        pl.concat_str([pl.col('ticker'), pl.lit(' '), pl.col('expiry').cast(pl.Utf8), pl.lit(' '), pl.col('Kpl').cast(pl.Utf8), pl.lit('/'),
                                       pl.col('Kps').cast(pl.Utf8), pl.lit('P '), pl.col('Kcs').cast(pl.Utf8), pl.lit('/'), pl.col('Kcl').cast(pl.Utf8), pl.lit('C')]).alias('contract'),
                        cost.alias('cost'), pl.col('pnl'), pl.col('how').alias('reason')))


# ---- #40 the EMA ladder previews (the deterministic rerun at e9d13c0) -------------------------------------------------------------------

def ema_ladder(which: str) -> pl.DataFrame:
    rows = []
    if which == 'ladder':
        j = json.load(open(SP2 / 'ema_ladder_out' / 'preview_2025-03.json'))
        for v, ts in j['trades'].items():
            for t in ts:
                rows.append({'date': t['date'], 'inst': v, 'period': 'preview 2025-03', 'contract': f"{t['name']} {t['k_ex']:g}{t['side']} m{t['m']}",
                             'cost': t['ask'] * 100, 'pnl': t['usd'], 'reason': t['why']})
    else:
        for mo in ('2025-02', '2025-03'):
            j = json.load(open(SP2 / 'ema_ladder_out' / f'targets_{mo}.json'))
            for v in ('E1', 'E2'):
                for t in j[v]['trades']:
                    rows.append({'date': t['date'], 'inst': v, 'period': f'preview {mo}' + (' (fresh)' if mo == '2025-02' else ' (seen before)'),
                                 'contract': f"{t['name']} {t['k_ex']:g}{t['side']} m{t['m']}", 'cost': t['ask'] * 100, 'pnl': t['usd'], 'reason': t['why']})
    return std(pl.DataFrame(rows))


# ---- #41 the EMA system previews ---------------------------------------------------------------------------------------------------------

def ema_system(v: str) -> pl.DataFrame:
    if v == 'v0':
        d = pl.read_csv(RN / 'EMA system' / 'out' / 'trades_full.csv', infer_schema_length=100000)
        per = pl.lit('preview 2026-10-12→16')
        con = pl.concat_str([pl.col('name'), pl.lit(' '), pl.col('K').cast(pl.Utf8), pl.col('right').cast(pl.Utf8), pl.lit(' '), pl.col('entry').cast(pl.Utf8)])
    else:
        d = pl.read_csv(RN / 'EMA system' / 'out_v1' / 'trades_v1.csv', infer_schema_length=100000)
        per = pl.concat_str([pl.lit('preview week: '), pl.col('week')])
        con = pl.concat_str([pl.col('venue'), pl.lit(' '), pl.col('K').cast(pl.Utf8), pl.col('right').cast(pl.Utf8), pl.lit(' '), pl.col('entry').cast(pl.Utf8)])
    inst = pl.concat_str([pl.lit('Config '), pl.col('cfg'), pl.lit(' '), pl.col('exit')])
    return std(d.select(pl.col('day').alias('date'), inst.alias('inst'), per.alias('period'), con.alias('contract'), pl.col('cost'),
                        pl.col('net').alias('pnl'), pl.col('reason')))


# ---- #43 Compass ICT --------------------------------------------------------------------------------------------------------------------

def ict() -> pl.DataFrame:
    fr = []
    e = pl.read_csv(RN / 'Compass ICT' / 'out' / 'explore_trades.csv', infer_schema_length=100000).with_columns(pl.lit('exploration 2022-05→2026-10-09').alias('per'))
    f = pl.read_csv(RN / 'Compass ICT' / 'out' / 'forward_trades.csv', infer_schema_length=100000).with_columns(pl.lit('preview 2026-10-09→22').alias('per'))
    for d in (e, f):
        cost = pl.when(pl.col('pct').abs() > 1e-12).then(pl.col('net') / pl.col('pct')).otherwise(pl.col('ask') * 200)
        fr.append(d.select(pl.col('day').alias('date'), pl.col('row').alias('inst'), pl.col('per').alias('period'),
                           pl.concat_str([pl.lit('SPXW '), pl.col('K').cast(pl.Utf8), pl.col('side').cast(pl.Utf8).str.slice(0, 1), pl.lit(' ×2 m'), pl.col('m').cast(pl.Utf8)]).alias('contract'),
                           cost.alias('cost'), pl.col('net').alias('pnl'), pl.col('reason')))
    return std(pl.concat(fr))
