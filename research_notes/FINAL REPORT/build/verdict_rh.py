"""verdict_rh.py — "would the verdict differ at Robinhood fees?" for every page-1 row: the study's FROZEN pass rule, as
pre-registered, applied to the same trades at the study's own fees and at Robinhood's (pnl + fee_old − fee_rh). The answer
is descriptive. It is never a new verdict: every verdict stays exactly as the study pre-registered it, on its own fees.

Where a rule can be run whole on the trade list, it is run (the Compass features' Δ through the study's own stats.delta;
the direction screen through its own build_direction.analyse; hyp C's and hyp F's four parts; the SPXW analogues' three).
Where it needs what the list does not hold (a multiple-testing family, a random-draw percentile, a sort), only its
computable part is run and the answer says so. The interval is the report's 20-session block bootstrap of the row unless
the study's own code is called; a study that used another interval can read differently at its own fees too.
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache

import polars as pl

import metrics as M
from base import RN, SP, SP2

# sid → (kind, words). Kinds: none | lb (mean % > 0, lower end > 0) | lb_usd (on $ a trade) | names / names_usd (each name of
# the verdict period) | hypc | hypf | spxw | delta | dir | forward | keep (an after-hours DROP rule: keep iff mean > 0 and
# the interval clear of zero)
RULES = {
    '1': ('none', 'descriptive'), '2': ('none', 'no pass rule pre-registered'), '2b': ('none', 'no pass rule pre-registered'),
    '4': ('none', 'an execution check'), '4b': ('none', 'descriptive'),
    '5': ('lb_part', 'its 62-cell multiple-testing correction needs the other cells'),
    '6a': ('lb_usd', ''), '6b': ('lb', ''), '6c': ('lb_usd', ''), '6d': ('lb_usd', ''),
    '6e': ('lb_part', 'the reselection and the forward T-G are not in the trade list'),
    '7a': ('lb_usd', ''), '7b': ('lb_part', 'the matched-random comparison is not recomputed'), '7c': ('lb_usd', ''), '7d': ('lb_usd', ''),
    '7e': ('lb_part', 'the matched-random comparison is not recomputed'),
    '7f': ('lb_part', 'its two-part rule A1 also reads the underlying'), '7g': ('lb_part', 'its two-part rule A1 also reads the underlying'),
    '7h': ('none', 'the rule reads the conditioned cells; this row is the unconditional one'),
    '7i': ('lb_part', 'its two-part rule A1 also reads the underlying'),
    '7j-atm_put': ('each_usd', 'A7, per cell'), '7j-put_30d': ('each_usd', 'A7, per cell'), '7j-put_15d': ('each_usd', 'A7, per cell'),
    '8a': ('none', 'A8 reads T0\'s sign and the sorts\' long-short, not this list alone'),
    '8b': ('lb_part', 'rule A9 is not restated in the trade list'), '8c': ('lb_part', 'rule A9 is not restated in the trade list'),
    '8d': ('lb_part', 'rule A10 is not restated in the trade list'), '8e': ('lb_part', 'rule A15 is not restated in the trade list'),
    '9a': ('lb_part', 'R1–R6 (Holm, the random-day control) need more than this list'),
    '9b': ('lb_part', 'R1–R6 (Holm, the random-day control) need more than this list'),
    '13': ('none', 'a population study'), '15': ('none', 'no pass rule pre-registered'),
    '17': ('lb_part', 'the 97.5th percentile of 500 cell-matched random draws is not recomputed'),
    '19': ('lb_usd', ''), '20a': ('lb_part', 'the rule picks the cell on fit; read here on OOS'),
    '20b': ('lb_part', 'the rule picks the cell on fit; read here on OOS'),
    '21a': ('hypc', ''), '21b': ('hypc', ''), '21c': ('hypc', ''), '21d': ('none', 'the pre-registered expectation was a negative OOS'),
    '25': ('hypf', ''), '26a': ('forward', ''), '26b': ('forward', ''), '26c': ('forward', ''),
    '27a': ('keep', ''), '27b': ('keep', ''), '28a': ('spxw', ''), '28b': ('spxw', ''),
    '29a': ('names', 'every name must pass'), '29b': ('none', 'no verdict of its own'), '29c': ('none', 'a sensitivity'),
    '29d': ('none', 'a sensitivity'), '29e': ('none', 'labelled, read only'),
    '30a': ('none', 'the reference set'), '30b': ('delta', 'V1'), '30c': ('delta', 'X3'), '30d': ('delta', 'BV1b'), '30e': ('delta', 'BX3e'),
    '31': ('dir', ''), '32': ('names_usd', 'both names must pass'), '34': ('lb_usd', ''), '35': ('each_usd', 'each name read alone'),
    '37a': ('each_usd', 'each name read alone, at 1× (Bonferroni and 2× not re-read)'), '37b': ('each_usd', 'each name read alone, at 1× (2× not re-read)'),
    '40a': ('none', 'a preview'), '40b': ('none', 'a preview'), '41a': ('none', 'a preview'), '41b': ('none', 'a preview'),
    '43': ('none', 'exploration only; no holdout read'),
}


def _f(x, d=2):
    return M.fnum(x, d)


def _lb(m, usd=False):
    mean = m.get('mean_usd' if usd else 'mean_pct', float('nan'))
    ci = m.get('ci_usd' if usd else 'ci_pct', (float('nan'), float('nan')))
    if not (isinstance(ci, (tuple, list)) and all(isinstance(v, float) and math.isfinite(v) for v in ci)):
        return None, mean, None
    return bool(mean > 0 and ci[0] > 0), mean, ci[0]


def _say(a, b, what):
    """a, b: the rule's outcome at the study's fees and at Robinhood's (True pass / False fail / None not computable)"""
    if a is None or b is None:
        return f'not computable ({what})'
    word = lambda x: 'passes' if x else 'fails'   # noqa: E731
    if a == b:
        return f'No — {word(b)} at both ({what})'
    return f'**Yes** — {word(a)} at the study\'s fees, {word(b)} at Robinhood\'s ({what})'


def answer(st, inst, per, m_rh, m_st, d_rh, d_st, slices_rh, slices_st) -> str:
    kind, words = RULES.get(st.sid, ('none', 'no pass rule recorded'))
    unit = '$' if kind.endswith('usd') else '%'
    if kind == 'none':
        return f'— (no pass rule: {words})'
    if kind == 'forward':
        return '— (verdict at the forward N only; the historical rows are descriptive)'
    if kind in ('lb', 'lb_usd', 'lb_part', 'keep'):
        usd = kind in ('lb_usd', 'keep')
        a, _, _ = _lb(m_st, usd)
        b, mean, lo = _lb(m_rh, usd)
        what = f"Robinhood: mean {_f(mean)}{'' if usd else '%'}, lower end {_f(lo)}"
        s = _say(a, b, what)
        if kind == 'lb_part':
            s = 'Its computable part (mean > 0, interval clear of zero): ' + s + f'; {words}'
        if kind == 'keep':
            s = 'Keep-or-drop rule: ' + s.replace('passes', 'kept').replace('fails', 'dropped')
        return s
    if kind in ('each_usd',):          # each name is its own verdict: the row's name
        a, _, _ = _lb(m_st, True)
        b, mean, lo = _lb(m_rh, True)
        return _say(a, b, f"{words}; Robinhood: mean {_f(mean)} $, lower end {_f(lo)}")
    if kind in ('names', 'names_usd'):  # one verdict over every name of the verdict period
        usd = kind == 'names_usd'
        A, B, parts = [], [], []
        for (i, p, mr), (_, _, ms) in zip(slices_rh, slices_st):
            if p != per or i == 'all names':
                continue
            a, _, _ = _lb(ms, usd)
            b, mean, lo = _lb(mr, usd)
            A.append(a)
            B.append(b)
            parts.append(f"{i} {'passes' if b else 'fails'}{' (changed)' if a != b else ''} (mean {_f(mean)}, lower end {_f(lo)})")
        aa = None if None in A else all(A)
        bb = None if None in B else all(B)
        return _say(aa, bb, f"{words}; at Robinhood's fees " + '; '.join(parts))
    if kind == 'hypc':
        return _four(d_rh, d_st, m_rh, m_st, kind)
    if kind == 'hypf':
        return _four(d_rh, d_st, m_rh, m_st, kind)
    if kind == 'spxw':
        def three(sl, stress):
            sel = [m for i, p, m in sl if p == 'selection']
            dev = [m for i, p, m in sl if p == 'development']
            if not sel or not dev:
                return None
            ok1, _, _ = _lb(sel[0], True)
            return bool(ok1 and stress > 0 and dev[0]['mean_usd'] > 0)
        s_rh = d_rh.filter(pl.col('period') == 'selection')['pnl'].mean() - 5.0     # +$0.05 on the package = $5 a trade
        s_st = d_st.filter(pl.col('period') == 'selection')['pnl'].mean() - 5.0
        a, b = three(slices_st, s_st), three(slices_rh, s_rh)
        return _say(a, b, f"three parts; Robinhood: selection mean {_f(m_rh['mean_usd'])} $, lower end {_f(m_rh['ci_usd'][0])}, "
                          f"at +$0.05 {_f(s_rh)}")
    if kind == 'delta':
        r = features_delta(words)
        return _say(r['study']['pass'], r['rh']['pass'],
                    f"the study's own stats.delta on the holdout; Δ {_f(r['study']['delta'] * 100)} → {_f(r['rh']['delta'] * 100)} points, "
                    f"Robinhood interval [{_f(r['rh']['ci'][0] * 100)}, {_f(r['rh']['ci'][1] * 100)}]")
    if kind == 'dir':
        r = direction_screen()
        return _say(r['study']['pass'], r['rh']['pass'],
                    f"the study's own analyse(); Δ {_f(r['study']['delta'] * 100)} → {_f(r['rh']['delta'] * 100)} pp, "
                    f"Robinhood interval [{_f(r['rh']['ci'][0] * 100)}, {_f(r['rh']['ci'][1] * 100)}]")
    return f'not computable ({kind})'


def _four(d_rh, d_st, m_rh, m_st, kind):
    """hyp C (21a–c): OOS mean > 0 with the interval clear of zero, positive without the best five sessions, both OOS years
    positive. hyp F (25): the same first part, also under $0.01 a leg worse (4 legs: $4 a fly), positive without the best
    five, both names positive."""
    def run(d, m):
        o = d.filter(pl.col('period') == 'OOS 2025–26')
        ok1, _, _ = _lb(m, False)
        if ok1 is None:
            return None, ''
        top = float(o.group_by('date').agg(pl.col('pnl').sum())['pnl'].sort(descending=True)[:5].sum())
        wo5 = float(o['pnl'].sum()) - top
        if kind == 'hypc':
            yrs = o.with_columns(pl.col('date').str.slice(0, 4).alias('y')).group_by('y').agg(pl.col('pnl').mean())
            ok = ok1 and wo5 > 0 and bool((yrs['pnl'] > 0).all())
            return ok, f"without the best five {_f(wo5, 0)} $, years {', '.join(f'{y} {_f(v)}' for y, v in sorted(yrs.rows()))}"
        stress = o.with_columns(pl.col('pnl') - 4.0)
        s_m = M.metrics(stress, 'risk')
        ok_s, _, _ = _lb(s_m, False)
        nm = o.group_by('inst').agg(pl.col('pnl').mean())
        ok = ok1 and bool(ok_s) and wo5 > 0 and bool((nm['pnl'] > 0).all())
        return ok, f"at $0.01 a leg {_f(s_m['mean_pct'])}%, without the best five {_f(wo5, 0)} $, names {', '.join(f'{n} {_f(v)}' for n, v in sorted(nm.rows()))}"
    a, _ = run(d_st, m_st)
    b, words = run(d_rh, m_rh)
    return _say(a, b, f"all four parts; Robinhood: mean {_f(m_rh['mean_pct'])}%, lower end {_f(m_rh['ci_pct'][0])}, {words}")


# ---- the two rules run by the studies' own code ----------------------------------------------------------------------------------------

@lru_cache(maxsize=8)
def features_delta(fid: str) -> dict:
    sys.path.insert(0, str(RN / 'Compass features' / 'run'))
    import fcommon as C
    import stats as ST
    import loaders_recent as LR
    T = pl.read_parquet(SP / 'features_work' / 'hold' / 'trades_with_inputs.parquet',
                        columns=['name', 'day', 'm', 'eb', 'strike', 'right', 'ask', 'spread', 'r', 'pnl', 'r_x3', 'settle', 'exit_px'])
    T = T.with_columns(LR.features_fees(T))
    T = T.with_columns(((pl.col('pnl') + pl.col('fee_old') - pl.col('fee_rh')) / (pl.col('ask') * 100)).alias('r_rh'),
                       ((pl.col('r_x3') * pl.col('ask') * 100 + pl.col('fee_old_x3') - pl.col('fee_rh_x3')) / (pl.col('ask') * 100)).alias('r_x3_rh'))
    sess_all = list(C.sessions())
    out = {}
    for lab, rc, xc in (('study', 'r', 'r_x3'), ('rh', 'r_rh', 'r_x3_rh')):
        if fid in ('V1', 'BV1b'):
            thr = 0.10 if fid == 'V1' else 0.03
            d = T.filter(pl.col('spread').is_not_null())
            w = d.filter(~(pl.col('spread') > thr)).select('day', pl.col(rc).alias('r'))
            wo = d.select('day', pl.col(rc).alias('r'))
        else:
            d = T.filter(pl.col('r_x3').is_not_null())
            d = d.filter((pl.col('eb') == '0DTE') & (pl.col('m') < C.X3_M)) if fid == 'X3' else d.filter(pl.col('name') != 'SPXW')
            w, wo = d.select('day', pl.col(xc).alias('r')), d.select('day', pl.col(rc).alias('r'))
        a, b = wo['day'].min(), wo['day'].max()
        res = ST.delta(w, wo, [s for s in sess_all if a <= s <= b], full=False)
        res['pass'] = ST.passes(res)
        out[lab] = res
    return out


@lru_cache(maxsize=1)
def direction_screen() -> dict:
    sys.path.insert(0, str(RN / 'Compass direction'))
    import build_direction as BD
    import dcommon as DC
    import loaders_recent  # noqa: F401  (the fee columns' definitions)
    d = pl.read_parquet(SP2 / 'dir' / 'work' / 'expl_trades.parquet')
    sess = DC.sessions_in(d['day'].min(), d['day'].max())
    out = {}
    from base import FR
    rh = FR.option_fee_expr(pl.col('ticker'), pl.col('ask'), 1.0, 'buy') + pl.when(pl.col('exit_zero')).then(0.0).otherwise(
        FR.option_fee_expr(pl.col('ticker'), pl.col('exit_px'), 1.0, 'sell'))
    old = 0.68748 + pl.when(pl.col('exit_zero')).then(0.0).otherwise(0.68748)
    cost = pl.when(pl.col('r').abs() > 1e-12).then(pl.col('pnl') / pl.col('r')).otherwise(pl.col('ask') * 100)
    d_rh = d.with_columns(((pl.col('pnl') + old - rh) / cost).alias('r'))
    for lab, x in (('study', d), ('rh', d_rh)):
        res = BD.analyse(x, sess)
        out[lab] = dict(res['main'], **{'pass': res['pass']})
    return out
