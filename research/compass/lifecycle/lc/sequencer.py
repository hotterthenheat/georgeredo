"""Sequencing and portfolio simulation (lifecycle protocol §5 M10/M11, §12): events taken in time order across roots,
one session at a time, with a position engine run per trade and forced exits when a rule closes a trade early.

Per root at most one open position. On a new event for a root:
  same direction while open          ignored (no pyramiding here; adds are a policy's job)
  opposite direction while open      M11: 'ignore' | 'close' (exit at this minute) | 'reverse' (exit, then open the new one)
  after a losing exit                M10: 'take' | 'skip' (no more entries on that root that session) | 'cool15' (skip 15 min)
Portfolio limits: starting equity, risk per trade (fixed contracts or fixed dollars of maximum loss), a cap on capital at
risk across all open positions, a cap per correlated bucket (every Tier I root is one bucket: US equity index), and the
displayed size at the fill (units never exceed the smallest displayed size of any leg)."""
from __future__ import annotations
import datetime as dt
import numpy as np
import polars as pl
from . import chainmat as cm, aux as ax, structures as stc, position as ps, paths
from .runner import allowed_structures

BUCKET = {'SPY': 'us_index', 'QQQ': 'us_index', 'IWM': 'us_index', 'SPXW': 'us_index'}

def max_loss_per_unit(info: dict, cost_unit: float, legs, ratio, nleg, cd) -> float:
    """Dollars a unit can lose: the debit for a debit structure; width x 100 - credit for a credit spread; the strike x
    100 - credit for a cash-secured put (its collateral)."""
    if cost_unit > 0: return cost_unit
    credit = -cost_unit
    if nleg == 1: return cd.strike[legs[0]] * 100.0 - credit
    w = 0.0
    for i in range(nleg):
        for j in range(nleg):
            if ratio[i] < 0 and ratio[j] > 0 and cd.is_call[legs[i]] == cd.is_call[legs[j]]:
                w = max(w, abs(cd.strike[legs[i]] - cd.strike[legs[j]]))
    return w * 100.0 - credit

def simulate(events: pl.DataFrame, structure_for: dict, pvec: np.ndarray, *, reverse: str = 'ignore', reentry: str = 'take',
             equity0: float = 100_000.0, sizing: str = 'fixed_risk', risk_per_trade: float = 500.0, fixed_units: int = 1,
             max_total_risk: float = 0.10, max_bucket_risk: float = 0.10, log=None) -> tuple[pl.DataFrame, pl.DataFrame]:
    """events: root, session, m, direction, setup, inv (all roots, any order). structure_for: setup -> structure code.
    Returns (trades, daily equity). Units are whole contracts; a trade whose sizing gives 0 units is skipped ('size')."""
    ev = events.sort(['session', 'm', 'root'])
    trades = []; days = []
    equity = equity0
    feat_cache = {}
    st = ax.make_store()
    for (session,), day in ev.group_by(['session'], maintain_order=True):
        roots = day['root'].unique().to_list()
        cds, aux_d, tgs, nxt = {}, {}, {}, {}
        for r in roots:
            cd = cm.load_0dte(r, session)
            if cd is None: continue
            if r not in feat_cache:
                ss = cm.sessions_0dte(r)
                f = ax.feature_frame(st, r, ss[0], ss[-1])
                feat_cache[r] = ({s: g for (s,), g in f.group_by(['session'], maintain_order=True)},
                                 dict(zip(*[f.group_by('session').agg(pl.col('open').first()).sort('session')[c].to_list() for c in ('session', 'open')])))
            fby, opens = feat_cache[r]
            if session not in fby: continue
            se = ax.session_series(fby[session], session, cd.n_min)
            cds[r] = cd; aux_d[r] = {'ema5': se['ema5'], 'rsi': se['rsi'], 'atr5': se['atr5'], 'ativ': ax.atm_iv(cd)}
            tgs[r] = ax.t_years_grid(cd)
            sess_sorted = sorted(opens); i = sess_sorted.index(session) if session in opens else -1
            nxt[r] = opens[sess_sorted[i + 1]] if 0 <= i < len(sess_sorted) - 1 else np.nan
        open_pos = {}            # root -> dict(trade fields, 'exit_m')
        blocked_until = {}       # root -> minute (or 10**6 for the session)
        day_pnl = 0.0
        def risk_in_use(at_m):
            return sum(p['risk'] for p in open_pos.values() if p['exit_m'] > at_m)
        for e in day.iter_rows(named=True):
            r = e['root']
            if r not in cds: continue
            cd = cds[r]; m = int(e['m'])
            # retire positions that closed by now
            p = open_pos.get(r)
            if p is not None and p['exit_m'] <= m:
                if p['pnl'] < 0:
                    if reentry == 'skip': blocked_until[r] = 10**6
                    elif reentry == 'cool15': blocked_until[r] = p['exit_m'] + 15
                del open_pos[r]; p = None
            if blocked_until.get(r, -1) > m: continue
            if p is not None:
                if np.sign(e['direction']) == np.sign(p['direction']) or reverse == 'ignore': continue
                # an opposite event: close the open one at this minute (re-run it with the cutoff here)
                q = pvec.copy(); q[ps.P['CUTOFF']] = m
                o = ps.run_one(cd, aux_d[r], p['legs'], p['ratio'], p['nleg'], p['m0'], p['direction'], p['inv'], q, next_open=nxt[r], short_strike=p['short'])
                delta = (o['pnl'] - p['pnl_unit']) * p['units']
                day_pnl += delta; p['trade']['pnl'] = o['pnl'] * p['units']; p['trade']['exit_m'] = o['exit_m']; p['trade']['closed_by'] = 'opposite_event'
                if o['pnl'] < 0 and reentry == 'skip': blocked_until[r] = 10**6
                elif o['pnl'] < 0 and reentry == 'cool15': blocked_until[r] = m + 15
                del open_pos[r]
                if reverse == 'close': continue
                if blocked_until.get(r, -1) > m: continue
            code = structure_for.get(e['setup'])
            if code is None or code not in allowed_structures(e['setup'], e['direction']): continue
            if m >= cd.n_min - 2: continue
            legs, ratio, info = stc.build(cd, m, tgs[r][m], code, e['direction'])
            if legs is None: continue
            nleg = info['nleg']
            o = ps.run_one(cd, aux_d[r], legs, ratio, nleg, m, e['direction'], e['inv'] if e['inv'] is not None else np.nan, pvec, next_open=nxt[r], short_strike=info['short_strike'])
            if o['filled'] < 1: continue
            mlu = max_loss_per_unit(info, o['cost0'], legs, ratio, nleg, cd)
            if sizing == 'fixed_units': units = fixed_units
            else: units = int(risk_per_trade // max(mlu, 1e-9))
            m0 = int(o['entry_m'])
            disp = min(int(cd.ask_size[legs[i], m0] if ratio[i] > 0 else cd.bid_size[legs[i], m0]) for i in range(nleg))
            units = min(units, max(disp, 0))
            if units <= 0: trades.append({'root': r, 'session': session, 'm': m, 'setup': e['setup'], 'structure': code, 'status': 'size'}); continue
            risk = units * mlu
            in_use = risk_in_use(m)
            if in_use + risk > max_total_risk * equity or in_use + risk > max_bucket_risk * equity:
                trades.append({'root': r, 'session': session, 'm': m, 'setup': e['setup'], 'structure': code, 'status': 'risk_cap'}); continue
            tr = {'root': r, 'session': session, 'm': m, 'setup': e['setup'], 'structure': code, 'status': 'filled', 'direction': e['direction'],
                  'units': units, 'cost_unit': o['cost0'], 'max_loss_unit': mlu, 'risk': risk, 'pnl': o['pnl'] * units, 'pnl_unit': o['pnl'],
                  'exit_m': o['exit_m'], 'hold': o['hold_min'], 'closed_by': 'policy'}
            trades.append(tr)
            day_pnl += tr['pnl']
            open_pos[r] = {'legs': legs, 'ratio': ratio, 'nleg': nleg, 'm0': m0, 'direction': e['direction'], 'inv': e['inv'] if e['inv'] is not None else np.nan,
                           'short': info['short_strike'], 'exit_m': o['exit_m'] if o['exit_m'] >= 0 else cd.n_min, 'pnl': o['pnl'], 'pnl_unit': o['pnl'],
                           'units': units, 'risk': risk, 'trade': tr}
        equity += day_pnl
        days.append({'session': session, 'pnl': day_pnl, 'equity': equity})
    tdf = pl.DataFrame(trades, infer_schema_length=None) if trades else pl.DataFrame()
    ddf = pl.DataFrame(days)
    if ddf.height:
        ddf = ddf.with_columns((pl.col('equity') / pl.col('equity').cum_max() - 1).alias('drawdown'))
    return tdf, ddf
