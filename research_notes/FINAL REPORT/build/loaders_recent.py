"""loaders_recent.py — the trade frames of the 2026-10-16 → 23 studies: steps 2, 4, 6, the Compass features (#30), the
direction rerun (#31), H1, H3, H4, H7, H8, the EMA ladder rerun (#40), the EMA system (#41), Compass ICT (#43)."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import polars as pl

from base import EXACT, FR, INFERRED, REPO, RN, SP, SP2, WORK, std

BUY = lambda root, px, q=1.0: FR.option_fee_expr(root, px, q, 'buy')   # noqa: E731
SELL = lambda root, px, q=1.0: FR.option_fee_expr(root, px, q, 'sell')  # noqa: E731


def _fees(old, rh, how):
    return [old.alias('fee_old'), rh.alias('fee_rh'), (pl.lit(how) if isinstance(how, str) else how).alias('fee_how')]

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
    cache = WORK / 'step2_near_v2.parquet'
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
        # the study: $0.65 to buy, $0.65 on the sale at the target or on a contract held in the money (sold at the close);
        # Robinhood: the buy, the sale at the target (2 × the price paid); a contract held to the close is expiry — no fee
        old = FEE + pl.when(hit | (pl.col('settle') > 0)).then(FEE).otherwise(0.0)
        rh = BUY(root, pl.col('entry_ask')) + pl.when(hit).then(SELL(root, 2 * pl.col('entry_ask'))).otherwise(0.0)
        fr.append(T.select(pl.col('session').alias('date'), pl.lit(root).alias('inst'), _pc().alias('period'), con.alias('contract'),
                           (pl.col('entry_ask') * 100).alias('cost'), net.alias('pnl'), why.alias('reason'), *_fees(old, rh, EXACT)))
    d = std(pl.concat(fr))
    d.write_parquet(cache)
    return d


def step4(tag: str = 'bounce1.5', exit_: str = 'trail20') -> pl.DataFrame:
    cache = WORK / f'step4_{tag}_{exit_}_v2.parquet'
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
        old = FEE + pl.when(sold).then(FEE).otherwise(0.0)
        rh = BUY(root, pl.col('entry_ask')) + pl.when(hit).then(SELL(root, pl.col(exit_ + '_bid'))).otherwise(0.0)
        fr.append(T.select(pl.col('session').alias('date'), pl.lit(root).alias('inst'), _pc().alias('period'), con.alias('contract'),
                           (pl.col('entry_ask') * 100).alias('cost'), net.alias('pnl'), why.alias('reason'), *_fees(old, rh, EXACT)))
    d = std(pl.concat(fr))
    d.write_parquet(cache)
    return d


# ---- step 6: the six rules' trades, chosen by the committed step6/trade.py choose() on the scratchpad population ---------------------------

def step6_rules() -> pl.DataFrame:
    cache = WORK / 'step6_rules_v2.parquet'
    if cache.exists():
        return pl.read_parquet(cache)
    sys.path.insert(0, str(REPO))
    from step6 import trade as T6
    from step6.data import load
    T = load()
    memb = pl.read_parquet(os.path.join(T6.WORK, 'membership.parquet'))
    chosen, _ = T6.choose(T, memb)
    # step6/build.py fee(): $0.65 (SPY/QQQ/IWM); SPXW $1.18748 / $1.27748; no sale fee at a $0 bid
    ask0 = pl.col('entry_ask')
    root = pl.col('root')        # SPXW (product 'SPX'), SPY, QQQ, IWM: the fee's root

    def old_of(xp):
        f_in = pl.when(root == 'SPXW').then(pl.when(ask0 < 1.0).then(1.18748).otherwise(1.27748)).otherwise(0.65)
        f_out = pl.when(xp > 0).then(pl.when(root == 'SPXW').then(pl.when(xp < 1.0).then(1.18748).otherwise(1.27748)).otherwise(0.65)).otherwise(0.0)
        return f_in + f_out

    def rh_of(xp):
        return BUY(root, ask0) + pl.when(xp > 0).then(SELL(root, xp)).otherwise(0.0)

    # exit (c) is two contracts: one sold at +40% (its price read back from net_c − net_b), the other trailed as (b)
    def xp_c1():
        n1 = pl.col('net_c') - pl.col('net_b')
        base = n1 / 100 + ask0 + pl.when(root == 'SPXW').then(pl.when(ask0 < 1.0).then(1.18748).otherwise(1.27748)).otherwise(0.65) / 100
        etf = base + 0.0065
        lo, hi = base + 0.0118748, base + 0.0127748
        spx = pl.when(lo < 1.0).then(lo).otherwise(hi)
        return pl.when(base.abs() <= 1e-7).then(0.0).otherwise(pl.when(root == 'SPXW').then(spx).otherwise(etf))
    fee_x = {'a': (old_of(pl.col('xp_a')), rh_of(pl.col('xp_a'))), 'b': (old_of(pl.col('xp_b')), rh_of(pl.col('xp_b'))),
             'c': (old_of(pl.col('xp_b')) + old_of(xp_c1()), rh_of(pl.col('xp_b')) + rh_of(xp_c1()))}
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
                                   why.cast(pl.Utf8).alias('reason'), *_fees(*fee_x[x], EXACT)))
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
        T = pl.read_parquet(FW / sub / 'trades_with_inputs.parquet', columns=['name', 'day', 'm', 'eb', 'strike', 'right', 'ask', 'spread', 'r', 'pnl', 'r_x3', 'settle', 'exit_px'])
        T = T.with_columns(pl.lit(per).alias('per'), (pl.col('ask') * 100).alias('cost'))
        T = T.with_columns(features_fees(T))
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
            g = g.with_columns((pl.col('r_x3') * pl.col('cost')).alias('p'), pl.lit('sold at the 14:00 bid').alias('why'),
                               pl.col('fee_old_x3').alias('fee_old'), pl.col('fee_rh_x3').alias('fee_rh'))
        else:
            raise ValueError(which)
        fr.append(g)
    d = pl.concat(fr, how='vertical_relaxed')
    con = pl.concat_str([pl.col('name'), pl.lit(' '), pl.col('eb'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('right').cast(pl.Utf8).str.slice(0, 1)])
    return std(d.select(pl.col('day').alias('date'), pl.lit('0DTE→60 DTE, 15 names').alias('inst'), pl.col('per').alias('period'), con.alias('contract'),
                        pl.col('cost'), pl.col('p').alias('pnl'), pl.col('why').alias('reason'), 'fee_old', 'fee_rh', pl.lit(EXACT).alias('fee_how')))


def _f_old(name, px):
    """fcommon.fee: $0.68748 (ETF and single names), SPXW $1.18748 / $1.27748; nothing at a $0 price"""
    return pl.when(px > 0).then(pl.when(name == 'SPXW').then(pl.when(px < 1.0 - 1e-9).then(1.18748).otherwise(1.27748)).otherwise(0.68748)).otherwise(0.0)


def features_fees(T: pl.DataFrame) -> list:
    """the study's fee and Robinhood's on the fixed exit and on the X3 exit (fcommon.ret: the buy at the ask, the exit at
    exit_px — SPXW held to settlement pays no exit fee; a $0 bid pays none). The 14:00 bid is not kept: it is read back
    from r_x3 (pnl = (px − ask) × 100 − fee(ask) − fee(px)), each fee tier tried in turn."""
    nm, ask = pl.col('name'), pl.col('ask')
    settled = (nm == 'SPXW') & ((pl.col('eb') == '0DTE') | (pl.col('eb') == '1-7'))
    f_in = _f_old(nm, ask)
    old = f_in + pl.when(settled).then(0.0).otherwise(_f_old(nm, pl.col('exit_px')))
    rh = BUY(nm, ask) + pl.when(settled | (pl.col('exit_px') <= 0)).then(0.0).otherwise(SELL(nm, pl.col('exit_px')))
    base = pl.col('r_x3') * ask + ask + f_in / 100          # px − fee(px) / 100
    etf, lo, hi = base + 0.0068748, base + 0.0118748, base + 0.0127748
    px3 = pl.when(base.abs() < 1e-7).then(0.0).otherwise(
        pl.when(nm == 'SPXW').then(pl.when(lo < 1.0 - 1e-9).then(lo).otherwise(hi)).otherwise(etf))
    old3 = f_in + _f_old(nm, px3)
    rh3 = BUY(nm, ask) + pl.when(px3 > 0).then(SELL(nm, px3)).otherwise(0.0)
    return [old.alias('fee_old'), rh.alias('fee_rh'), old3.alias('fee_old_x3'), rh3.alias('fee_rh_x3')]


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
                        cost.alias('cost'), pl.col('pnl'), why.alias('reason'),
                        # $0.68748 in, $0.68748 out unless the exit bid is $0
                        *_fees(0.68748 + pl.when(pl.col('exit_zero')).then(0.0).otherwise(0.68748),
                               BUY(pl.col('ticker'), pl.col('ask')) + pl.when(pl.col('exit_zero')).then(0.0).otherwise(SELL(pl.col('ticker'), pl.col('exit_px'))),
                               EXACT)))


# ---- stock studies: H1, H4, H7, H8 ---------------------------------------------------------------------------------------------------

def _stock(side, entry_px, exit_px, old, how=EXACT):
    """a 100-share trade: the study's fee-only part (`old`) against Robinhood's (the sale's SEC fee and TAF, CAT both
    sides); a long sells at the exit, a short at the entry"""
    sale_px = pl.when(side == 1).then(exit_px).otherwise(entry_px)
    rh = pl.lit(2 * FR.CAT_SHARE * 100) + 0.02 + ((FR.SEC_RATE * sale_px * 100 * 100) - 1e-9).ceil() / 100
    return _fees(old, rh, how)


def h1() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Compass H1' / 'out' / 'h1_sessions.csv', infer_schema_length=100000).filter(
        (pl.col('excluded').fill_null('') == '') & pl.col('side').is_in([1, -1]))
    side = pl.when(pl.col('side') == 1).then(pl.lit('long')).otherwise(pl.lit('short'))
    return std(d.select(pl.col('day').alias('date'), pl.col('name').alias('inst'), pl.lit('single test').alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' '), side]).alias('contract'), (pl.col('C') * 100).alias('cost'),
                        pl.col('net_1x').alias('pnl'), pl.lit('next 09:30 open').alias('reason'),
                        # PREREG_H1 §2: $0.01 a share each way, fees alone (MOC and MOO fills)
                        *_stock(pl.col('side'), pl.col('C'), pl.col('O'), pl.lit(2.0))))


def h4() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H4' / 'out' / 'h4_sessions.csv', infer_schema_length=100000).filter(
        (pl.col('excluded').fill_null('') == '') & pl.col('side').is_in([1, -1]))
    side = pl.when(pl.col('side') == 1).then(pl.lit('long')).otherwise(pl.lit('short'))
    per = pl.when(pl.col('span') == 'test').then(pl.lit('test 2025-10-13→2026-10-22')).otherwise(pl.lit('exploration (context)'))
    return std(d.select(pl.col('day').alias('date'), pl.col('name').alias('inst'), per.alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' '), side]).alias('contract'), (pl.col('E') * 100).alias('cost'),
                        pl.col('net_1x').alias('pnl'), pl.lit('official close').alias('reason'),
                        # PREREG_H4: $0.005 at the 15:30 entry is half the spread (kept); $0.01 at the close is fees (replaced)
                        *_stock(pl.col('side'), pl.col('E'), pl.col('C'), pl.lit(1.0))))


def h7() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H7_H8_H9' / 'out' / 'h7_trades.csv', infer_schema_length=100000).filter(pl.col('excluded').fill_null('') == '')
    return std(d.select(pl.col('prev').alias('date'), pl.col('name').alias('inst'), pl.lit('single test').alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' long, FOMC '), pl.col('A')]).alias('contract'),
                        (pl.col('C_prev') * 100).alias('cost'), pl.col('net_1x').alias('pnl'), pl.lit('13:58 bar close on the statement day').alias('reason'),
                        # PREREG_H7: $0.01 at the auction entry is fees (replaced); $0.005 at the exit is half the spread (kept)
                        *_stock(pl.lit(1), pl.col('C_prev'), pl.col('X'), pl.lit(1.0))))


def h8() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H7_H8_H9' / 'out' / 'h8_trades.csv', infer_schema_length=100000).filter(pl.col('excluded').fill_null('') == '')
    return std(d.select(pl.col('E').alias('date'), pl.col('name').alias('inst'), pl.lit('single test').alias('period'),
                        pl.concat_str([pl.lit('100 '), pl.col('name'), pl.lit(' long, turn '), pl.col('M').cast(pl.Utf8)]).alias('contract'),
                        (pl.col('C_E') * 100).alias('cost'), pl.col('net_1x').alias('pnl'), pl.lit('official close, 3rd session').alias('reason'),
                        # PREREG_H8: $0.01 a share each way in the closing auctions, fees alone
                        *_stock(pl.lit(1), pl.col('C_E'), pl.col('C_X'), pl.lit(2.0))))


def h3() -> pl.DataFrame:
    d = pl.read_csv(RN / 'Edge search' / 'H3' / 'out' / 'trades_expl.csv', infer_schema_length=100000)
    cost = pl.when(pl.col('pct_risk').abs() > 1e-12).then(pl.col('pnl') / pl.col('pct_risk')).otherwise(None)
    return std(d.select(pl.col('P').alias('date'), pl.lit('single names').alias('inst'), pl.lit('exploration (holdout unopened)').alias('period'),
                        pl.concat_str([pl.col('ticker'), pl.lit(' '), pl.col('expiry').cast(pl.Utf8), pl.lit(' '), pl.col('Kpl').cast(pl.Utf8), pl.lit('/'),
                                       pl.col('Kps').cast(pl.Utf8), pl.lit('P '), pl.col('Kcs').cast(pl.Utf8), pl.lit('/'), pl.col('Kcl').cast(pl.Utf8), pl.lit('C')]).alias('contract'),
                        cost.alias('cost'), pl.col('pnl'), pl.col('how').alias('reason'), *h3_fees()))


def h3_fees():
    """$0.68748 a leg traded: four to open; at the reaction close the shorts bought back at their asks and the longs sold at
    their bids, a leg at $0 not traded. One row (a split-sized move, booked at max loss) keeps no exit quotes: eight legs."""
    t, x = pl.col('ticker'), {k: pl.col(f'x_{k}').fill_null(0.0) for k in ('cs', 'ps', 'cl', 'pl')}
    q = pl.col('how') == 'quotes'
    n_out = sum((x[k] > 0).cast(pl.Float64) for k in x)
    old = pl.when(q).then(0.68748 * (4 + n_out)).otherwise(8 * 0.68748)
    rh_in = SELL(t, pl.col('cs_bid')) + SELL(t, pl.col('ps_bid')) + BUY(t, pl.col('cl_ask')) + BUY(t, pl.col('pl_ask'))
    rh_out = (BUY(t, x['cs'], (x['cs'] > 0).cast(pl.Float64)) + BUY(t, x['ps'], (x['ps'] > 0).cast(pl.Float64))
              + SELL(t, x['cl'], (x['cl'] > 0).cast(pl.Float64)) + SELL(t, x['pl'], (x['pl'] > 0).cast(pl.Float64)))
    rh = rh_in + pl.when(q).then(rh_out).otherwise(2 * BUY(t, pl.lit(1.0)) + 2 * SELL(t, pl.lit(1.0)))
    how = pl.when(q).then(pl.lit(EXACT)).otherwise(pl.lit(INFERRED('no exit quotes kept: four legs closed at $1.00 assumed')))
    return [old.alias('fee_old'), rh.alias('fee_rh'), how.alias('fee_how')]


# ---- #40 the EMA ladder previews (the deterministic rerun at e9d13c0) -------------------------------------------------------------------

def ema_ladder(which: str) -> pl.DataFrame:
    rows = []
    if which == 'ladder':
        j = json.load(open(SP2 / 'ema_ladder_out' / 'preview_2025-03.json'))
        for v, ts in j['trades'].items():
            for t in ts:
                rows.append({'date': t['date'], 'inst': v, 'period': 'preview 2025-03', 'contract': f"{t['name']} {t['k_ex']:g}{t['side']} m{t['m']}",
                             'cost': t['ask'] * 100, 'pnl': t['usd'], 'reason': t['why'], **_ladder_fee(t)})
    else:
        for mo in ('2025-02', '2025-03'):
            j = json.load(open(SP2 / 'ema_ladder_out' / f'targets_{mo}.json'))
            for v in ('E1', 'E2'):
                for t in j[v]['trades']:
                    rows.append({'date': t['date'], 'inst': v, 'period': f'preview {mo}' + (' (fresh)' if mo == '2025-02' else ' (seen before)'),
                                 'contract': f"{t['name']} {t['k_ex']:g}{t['side']} m{t['m']}", 'cost': t['ask'] * 100, 'pnl': t['usd'], 'reason': t['why'],
                                 **_ladder_fee(t)})
    return std(pl.DataFrame(rows))


def _ladder_fee(t) -> dict:
    """$0.68748 in, $0.68748 out unless the exit bid is $0 (no exit fee)"""
    sold = t['bid_out'] > 0
    return {'fee_old': 0.68748 * (2 if sold else 1),
            'fee_rh': FR.option_fee(t['name'], t['ask'], 1, 'buy') + (FR.option_fee(t['name'], t['bid_out'], 1, 'sell') if sold else 0.0),
            'fee_how': EXACT}


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
    root = 'name' if v == 'v0' else 'venue'
    d = d.with_columns(pl.struct(root, 'ask', 'qty', 'legs').map_elements(lambda r: _legs_fee(r[root], r['ask'], r['qty'], r['legs']), return_dtype=pl.Float64).alias('fee_rh'))
    return std(d.select(pl.col('day').alias('date'), inst.alias('inst'), per.alias('period'), con.alias('contract'), pl.col('cost'),
                        pl.col('net').alias('pnl'), pl.col('reason'), pl.col('fees').alias('fee_old'), 'fee_rh', pl.lit(EXACT).alias('fee_how')))


def _legs_fee(root: str, ask: float, qty: float, legs: str) -> float:
    """Robinhood on the buy of `qty` at the ask and each exit in `legs` ("q@time:price:why;…"), a $0 price not sold"""
    f = FR.option_fee(root, ask, qty, 'buy')
    for part in str(legs or '').split(';'):
        if '@' not in part:
            continue
        q, rest = part.split('@', 1)
        bits = rest.split(':')
        px = float(bits[1]) if len(bits) > 1 and bits[1] not in ('', 'None') else 0.0
        if px > 0:
            f += FR.option_fee(root, px, float(q), 'sell')
    return f


# ---- #43 Compass ICT --------------------------------------------------------------------------------------------------------------------

def ict() -> pl.DataFrame:
    fr = []
    e = pl.read_csv(RN / 'Compass ICT' / 'out' / 'explore_trades.csv', infer_schema_length=100000).with_columns(pl.lit('exploration 2022-05→2026-10-09').alias('per'))
    f = pl.read_csv(RN / 'Compass ICT' / 'out' / 'forward_trades.csv', infer_schema_length=100000).with_columns(pl.lit('preview 2026-10-09→22').alias('per'))
    for d in (e, f):
        cost = pl.when(pl.col('pct').abs() > 1e-12).then(pl.col('net') / pl.col('pct')).otherwise(pl.col('ask') * 200)
        d = d.with_columns(pl.struct('ask', 'legs').map_elements(lambda r: _legs_fee('SPXW', r['ask'], 2.0, r['legs']), return_dtype=pl.Float64).alias('fee_rh'))
        fr.append(d.select(pl.col('day').alias('date'), pl.col('row').alias('inst'), pl.col('per').alias('period'),
                           pl.concat_str([pl.lit('SPXW '), pl.col('K').cast(pl.Utf8), pl.col('side').cast(pl.Utf8).str.slice(0, 1), pl.lit(' ×2 m'), pl.col('m').cast(pl.Utf8)]).alias('contract'),
                           cost.alias('cost'), pl.col('net').alias('pnl'), pl.col('reason'), pl.col('fees').alias('fee_old'), 'fee_rh',
                           pl.lit(EXACT).alias('fee_how')))
    return std(pl.concat(fr))
