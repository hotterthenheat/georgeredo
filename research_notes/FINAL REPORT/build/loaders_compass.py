"""loaders_compass.py — the trade frames of the 2026-10-21/22 Compass studies (phase 2, phase 3, the paper tracker, the
after-hours study, the SPXW analogues, the picker). Each returns the standard frame (base.STD)."""
from __future__ import annotations

import json
import sys

import numpy as np
import polars as pl

from base import DR, EXACT, FR, INFERRED, RN, WORK, std

BUY = lambda root, px, q=1.0: FR.option_fee_expr(root, px, q, 'buy')   # noqa: E731
SELL = lambda root, px, q=1.0: FR.option_fee_expr(root, px, q, 'sell')  # noqa: E731


def _fees(old, rh, how):
    return [old.alias('fee_old'), rh.alias('fee_rh'), (pl.lit(how) if isinstance(how, str) else how).alias('fee_how')]


def _legs_rh(root: str, legs) -> float:
    """Robinhood to open a structure: each short leg sold at its bid, each long bought at its ask ([(side, qty, bid, ask)])"""
    f = 0.0
    for side, qty, bid, ask in legs:
        f += FR.option_fee(root, bid, qty, 'sell') if side == 'short' else FR.option_fee(root, ask, qty, 'buy')
    return f

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


def tracker_open_fees() -> dict:
    """(candidate, structure, name, day, minute) → Robinhood's fee to open the structure, off the capture rows' legs
    (shorts sold at the bid, longs bought at the ask, each with its quantity); the tracker charged $0.65 × 4 contracts"""
    cache = WORK / 'tracker_open_rh.parquet'
    if not cache.exists():
        df = AL.load_rows(DR / 'paper_backtest_official')
        c = df.filter((pl.col('row_kind') == 'capture') & pl.col('l1_symbol').is_not_null() & pl.col('l1_qty').is_not_null())
        rows = []
        for r in c.iter_rows(named=True):
            legs = [(r[f'l{i}_side'], float(r[f'l{i}_qty']), float(r[f'l{i}_bid']), float(r[f'l{i}_ask'])) for i in range(1, 5) if r[f'l{i}_symbol']]
            rows.append({'candidate': r['candidate'], 'structure': r['structure'], '_name': r['_name'], '_day': r['_day'], 'minute': r['minute'],
                         'rh_open': _legs_rh(r['_name'], legs)})
        pl.DataFrame(rows).unique(subset=['candidate', 'structure', '_name', '_day', 'minute'], keep='first').write_parquet(cache)
    t = pl.read_parquet(cache)
    return {(a, b, c_, d, e): f for a, b, c_, d, e, f in t.iter_rows()}


def tracker(cand: str) -> pl.DataFrame:
    s = tracker_rows().filter(pl.col('candidate') == cand)
    fo = tracker_open_fees()
    rows = []
    for r in s.iter_rows(named=True):
        legs = '/'.join(f"{'+' if r[f'l{i}_side'] == 'long' else '−'}{_occ(r[f'l{i}_symbol'])}" for i in range(1, 5) if r[f'l{i}_symbol'])
        inst = r['_name'] if cand != 'fly5' else f"{r['_name']} {r['structure']}"
        rh = fo.get((cand, r['structure'], r['_name'], r['_day'], r['minute']))
        rows.append({'date': r['_day'], 'inst': inst, 'period': r['per'], 'contract': f"{r['_name']} {r['minute']} {legs}",
                     'cost': r['max_risk_f'] * 100, 'pnl': r['pnl_nbbo_f'], 'reason': 'held to settlement (official close)',
                     'fee_old': 2.60, 'fee_rh': rh if rh is not None else 0.2012,
                     'fee_how': EXACT if rh is not None else INFERRED('no capture legs: two 1-lot sales and two buys')})
    return std(pl.DataFrame(rows))


# ---- the after-hours study: case (b), the post-market decision -----------------------------------------------------------------------

def afterhours(cand: str) -> pl.DataFrame:
    a = pl.read_csv(P3 / 'backtest_audit' / 'out' / 'afterhours_trades.csv', infer_schema_length=100000)
    a = a.filter((pl.col('candidate') == cand) & ((pl.col('structure') == 'iron') | (pl.lit(cand) != 'fly5')))
    t = tracker_rows().filter(pl.col('candidate') == cand).select(
        pl.col('_name').alias('name'), pl.col('_day').alias('day'), 'minute', 'structure', 'max_risk_f')
    a = a.join(t, on=['name', 'day', 'minute', 'structure'], how='left')
    a = a.filter(pl.col('pnl_b').is_not_null())
    # the tracker's $2.60 to open (no exercise or assignment fee, no stock commission); Robinhood: the opening legs, $0 to
    # exercise or be assigned, and on the shares case (b) leaves, re-marked at the next 09:30 open, a sale's SEC fee and TAF
    # (net long) or a purchase's CAT (net short)
    fo = tracker_open_fees()
    a = a.with_columns(pl.struct('name', 'day', 'minute', 'structure').map_elements(
        lambda r: fo.get((cand, r['structure'], r['name'], r['day'], r['minute'])), return_dtype=pl.Float64).alias('rh_open'))
    sh = pl.col('net_shares_b').fill_null(0).cast(pl.Float64)
    px = pl.col('next_open_0930').fill_null(0.0)
    stock = (sh.abs() * FR.CAT_SHARE + pl.when(sh > 0).then(
        ((pl.min_horizontal(sh * FR.TAF_SHARE, pl.lit(FR.TAF_MAX)) * 100 - 1e-9).ceil() + (FR.SEC_RATE * px * sh * 100 - 1e-9).ceil()) / 100).otherwise(0.0))
    return std(a.select(pl.col('day').alias('date'), pl.col('name').alias('inst'), pl.col('period'),
                        (pl.col('name') + ' ' + pl.col('minute') + ' ' + pl.col('legs').cast(pl.Utf8)).alias('contract'),
                        (pl.col('max_risk_f') * 100).alias('cost'), pl.col('pnl_b').alias('pnl'),
                        pl.lit('held; after-hours decision (b) on the 17:30 price').alias('reason'),
                        pl.lit(2.60).alias('fee_old'), (pl.col('rh_open').fill_null(0.2012) + stock).alias('fee_rh'),
                        pl.when(pl.col('rh_open').is_null()).then(pl.lit(INFERRED('no capture legs'))).otherwise(pl.lit(EXACT)).alias('fee_how')))


# ---- the SPXW analogues (package fill, official SPX close) ------------------------------------------------------------------------------

def spxw(analogue: str) -> pl.DataFrame:
    d = pl.read_parquet(P3 / 'spxw_prereg' / 'out' / 'trades.parquet').filter(pl.col('tradable') & (pl.col('analogue') == analogue))
    con = pl.concat_str([pl.lit('SPXW '), pl.col('minute'), pl.lit(' '), pl.col('k_lp').cast(pl.Utf8), pl.lit('/'), pl.col('k_sp').cast(pl.Utf8),
                         pl.lit('P '), pl.col('k_sc').cast(pl.Utf8), pl.lit('/'), pl.col('k_lc').cast(pl.Utf8), pl.lit('C')])
    # fees_open: the study's SPXW schedule on the four legs; held to cash settlement (no close fee)
    d = d.with_columns(pl.col('legs_json').map_elements(
        lambda j: _legs_rh('SPXW', [(l['side'], float(l['qty']), float(l['bid']), float(l['ask'])) for l in json.loads(j)]),
        return_dtype=pl.Float64).alias('rh_open'))
    return std(d.select(pl.col('day').alias('date'), pl.lit('SPXW').alias('inst'), pl.col('period'), con.alias('contract'),
                        pl.col('risk_pkg').alias('cost'), pl.col('pnl_pkg_off').alias('pnl'),
                        pl.lit('held to cash settlement (official SPX close)').alias('reason'),
                        *_fees(pl.col('fees_open'), pl.col('rh_open'), EXACT)))


# ---- the picker (five runs) ------------------------------------------------------------------------------------------------------------

def picker(run: str) -> pl.DataFrame:
    d = pl.read_csv(P3 / 'picker_prereg' / 'out' / f'trades_{run}.csv', infer_schema_length=100000)
    per = pl.when(pl.col('session') >= '2026-10-14').then(pl.lit('never-read 2026-10-14→21')).otherwise(pl.lit('whole span (card dates out)'))
    con = pl.concat_str([pl.col('name'), pl.lit(' '), pl.col('session'), pl.lit(' '), pl.col('strike').cast(pl.Utf8), pl.col('side').str.slice(0, 1)])
    return std(d.select(pl.col('session').alias('date'), pl.col('name').alias('inst'), per.alias('period'), con.alias('contract'),
                        (pl.col('entry_ask') * 100).alias('cost'), pl.col('pnl'), pl.col('reason'),
                        *_fees(pl.col('fee_in') + pl.col('fee_out'), BUY(pl.col('name'), pl.col('entry_ask'))
                               + pl.when((pl.col('fee_out') > 0) & (pl.col('exit_px') > 0)).then(SELL(pl.col('name'), pl.col('exit_px'))).otherwise(0.0), EXACT)))


# ---- phase 2 ---------------------------------------------------------------------------------------------------------------------------

def hyp_a() -> pl.DataFrame:
    d = pl.read_csv(P2 / 'hyp_a_closing_pin' / 'out' / 'pick_rows.csv', infer_schema_length=100000)
    con = pl.concat_str([pl.lit('SPXW 15:30 '), pl.col('Ks').cast(pl.Utf8), pl.lit('/'), pl.col('Kl').cast(pl.Utf8), pl.lit('C')])
    per = pl.when(pl.col('period') == 'fit').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))
    return std(d.select(pl.col('date'), pl.lit('SPXW').alias('inst'), per.alias('period'), con.alias('contract'),
                        pl.col('max_risk').alias('cost'), pl.col('pnl'), pl.lit('held to settlement').alias('reason'),
                        # $0.65 a leg to open (both legs), held to cash settlement
                        *_fees(pl.lit(1.30), SELL('SPXW', pl.col('bid_s')) + BUY('SPXW', pl.col('ask_l')), EXACT)))


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
    if which == 'touch':     # $0.65 a leg to open, held: the short sold at its bid, the long bought at its ask
        fees = _fees(pl.lit(1.30), SELL('SPY', pl.col('short_bid')) + BUY('SPY', pl.col('long_ask')), EXACT)
    else:                    # the condor's legs are not kept: two shorts sold (each a 1-lot under $4.85: TAF and SEC a cent each), two longs
        fees = _fees(pl.lit(2.60), 2 * SELL('SPY', pl.lit(1.0)) + 2 * BUY('SPY', pl.lit(1.0)), EXACT)
    return std(g.select(pl.col('session').alias('date'), pl.lit('SPY').alias('inst'), _hb_period().alias('period'), con.alias('contract'),
                        pl.col('max_risk').alias('cost'), pl.col('pnl_hold').alias('pnl'), pl.lit('held to settlement').alias('reason'), *fees))


def hyp_c_fly(kind: str, wing: str, t: str = '1500') -> pl.DataFrame:
    fr = []
    for P in ('SPY', 'QQQ'):
        d = pl.read_parquet(P2 / 'hyp_c_debit_flies' / 'out' / f'flies_{P}.parquet')
        d = d.filter((pl.col('t') == t) & (pl.col('kind') == kind) & (pl.col('wing') == wing) & pl.col('pnl').is_not_null())
        fr.append(d)
    d = pl.concat(fr)
    per = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))
    con = pl.concat_str([pl.col('product'), pl.lit(f' {t} {kind} K0 '), pl.col('K0').cast(pl.Utf8), pl.lit(' ±'), pl.col('W').cast(pl.Utf8)])
    # build.py: 4 contracts × $0.65 to open, held. Robinhood: iron — the ATM call and put sold, the wings bought; call/put — the
    # wings bought, the body sold as one leg of two; each body leg priced at half the ATM straddle (only for the SEC cent)
    P = pl.col('product')
    rh = (SELL(P, pl.col('straddle') / 2) * 2 + BUY(P, pl.lit(1.0)) * 2) if kind == 'iron' else (BUY(P, pl.lit(1.0)) * 2 + SELL(P, pl.col('straddle') / 2, 2.0))
    return std(d.select(pl.col('session').alias('date'), pl.col('product').alias('inst'), per.alias('period'), con.alias('contract'),
                        (pl.col('risk') * 100).alias('cost'), pl.col('pnl'), pl.lit('held to settlement').alias('reason'),
                        *_fees(pl.lit(2.60), rh, EXACT)))


def hyp_c_vertical(universe: str, exit_: str) -> pl.DataFrame:
    d = pl.read_parquet(P2 / 'hyp_c_debit_flies' / 'out' / 'spreads_trades.parquet').filter(
        (pl.col('universe') == universe) & (pl.col('cell') == 'd70_30') & (pl.col('exit') == exit_) & pl.col('pnl').is_not_null())
    per = pl.when(pl.col('period') == 'fit').then(pl.lit('fit 2022–24')).otherwise(pl.lit('OOS 2025–26'))
    con = pl.concat_str([pl.col('product'), pl.lit(' '), pl.col('side'), pl.lit(' 0.70/0.30 m'), pl.col('entry_m').cast(pl.Utf8)])
    # run_spreads.py: $0.65 a leg to open (2), and to close when sold; 'hold' rows settle. The legs' own prices are not kept:
    # an ETF leg's fee does not depend on them (a 1-lot sale under $4.85); an SPXW leg is taken at the $1.00-and-up tier
    P = pl.col('product')
    sold = pl.col('reason') != 'settle'
    rh = BUY(P, pl.lit(1.0)) + SELL(P, pl.lit(1.0)) + pl.when(sold).then(BUY(P, pl.lit(1.0)) + SELL(P, pl.lit(1.0))).otherwise(0.0)
    how = pl.when(P == 'SPXW').then(pl.lit(INFERRED('SPXW legs\' price tier ($1.00 and up)'))).otherwise(pl.lit(EXACT))
    return std(d.select(pl.col('session').alias('date'), pl.col('product').alias('inst'), per.alias('period'), con.alias('contract'),
                        (pl.col('debit') * 100).alias('cost'), pl.col('pnl'), pl.col('reason'),
                        *_fees(1.30 + pl.when(sold).then(1.30).otherwise(0.0), rh, how)))


# ---- phase 3 F -------------------------------------------------------------------------------------------------------------------------

def hyp_f(form: str = 'call', t: str = '1530') -> pl.DataFrame:
    fr = []
    for per, f in (('fit 2022-11→2024', 'flies_fit.parquet'), ('OOS 2025–26', 'flies_oos.parquet')):
        d = pl.read_parquet(P3 / 'hyp_f_cash_butterfly' / 'out' / f).filter(
            (pl.col('form') == form) & (pl.col('t') == t) & pl.col('pnl_nbbo').is_not_null())
        fr.append(d.with_columns(pl.lit(per).alias('per')))
    d = pl.concat(fr, how='diagonal_relaxed')
    con = pl.concat_str([pl.col('product'), pl.lit(f' {t} {form} fly K0 '), pl.col('K0').cast(pl.Utf8), pl.lit(' ±5')])
    P = pl.col('product')
    rh = pl.lit(0.0)
    for i in range(4):
        q = pl.col(f'l{i}_lots').fill_null(0).cast(pl.Float64)
        rh = rh + pl.when(pl.col(f'l{i}_long').fill_null(True)).then(BUY(P, pl.col(f'l{i}_ask').fill_null(0.0), q)).otherwise(SELL(P, pl.col(f'l{i}_bid').fill_null(0.0), q))
    return std(d.select(pl.col('session').alias('date'), pl.col('product').alias('inst'), pl.col('per').alias('period'), con.alias('contract'),
                        (pl.col('risk_nbbo') * 100).alias('cost'), pl.col('pnl_nbbo').alias('pnl'), pl.lit('held to settlement').alias('reason'),
                        *_fees(pl.lit(2.60), rh, EXACT)))
