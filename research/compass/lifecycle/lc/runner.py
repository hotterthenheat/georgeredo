"""Run setup events (and their random-minute controls) through every allowed structure and a policy set, session by
session, on the Tier I chains (lifecycle protocol §3-§5). Writes, per root and stage:

  WORK/runs/<stage>/<root>/positions.parquet   one row per (event, control seed, structure): the structure chosen at the
                                               fill minute, its legs' strikes/deltas/IVs/spread, and Result A (hindsight)
  WORK/runs/<stage>/<root>/outcomes.parquet    one row per (position, policy): the executable result (Result B inputs)
  WORK/runs/<stage>/<root>/run.json            counts, configuration, timing, configurations evaluated

Resumable by root. Controls: for each real event and seed 0..4 a minute drawn uniformly from the entry window on the same
session with the same direction; the control's invalidation sits the same distance from its spot as the event's did."""
from __future__ import annotations
import datetime as dt, json, os, sys, time, zlib
import numpy as np
import polars as pl
from . import paths, chainmat as cm, aux as ax, structures as stc, position as ps, policies as pol
from .events import WINDOW
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import calendar as cal  # noqa: E402

SEEDS = (0, 1, 2, 3, 4)

def allowed_structures(setup: str, direction: int) -> tuple[str, ...]:
    if setup in ('VOLC', 'EVF', 'ALL10V', 'ALL1330'): return ('STR', 'STG')
    if setup in ('VOLR', 'ALL10P'): return ('CPS', 'CSP')
    return stc.DIRECTIONAL_LONG[1 if direction > 0 else -1]

ENTRY_RULES = ('E0', 'E1L1', 'E1L3', 'E2', 'E3', 'E3atr', 'E2g', 'E1L3g')

def _cost_ps(cd, legs, ratio, nleg, k):
    """Open cost per share of one unit at minute k (ask for longs, bid for shorts); NaN if a leg is unquoted."""
    s = 0.0
    for i in range(nleg):
        c = legs[i]; b = cd.bid[c, k]; a = cd.ask[c, k]
        if not (np.isfinite(b) and np.isfinite(a) and a > 0 and a >= b): return np.nan
        s += (a if ratio[i] > 0 else b) * ratio[i]
    return s

def _mark_ps(cd, legs, ratio, nleg, k):
    s = 0.0
    for i in range(nleg):
        c = legs[i]; b = cd.bid[c, k]; a = cd.ask[c, k]
        if not (np.isfinite(b) and np.isfinite(a) and a > 0 and a >= b): return np.nan
        s += 0.5 * (a + b) * ratio[i]
    return s

def entry_plan(cd, rule: str, m: int, direction: int, legs, ratio, nleg, atr5: float, delta_net: float):
    """(fill minute, limit price per share or NaN, skip reason or None) for an order decided at instant m.
    E0 market now; E1L1/E1L3 market 1/3 minutes later; E2 at the next 5m close beyond the signal's spot in the trade's
    direction within 15 minutes, else cancelled; E3 limit at mark - half the half-spread (mid - 1/4 spread on one leg),
    E3atr limit at mark - |net delta| x 0.25 ATR(5m); both good for 10 minutes and filled only when the market's open
    cost trades through the limit by a cent (paying the limit). The 'g' variants add the chase guard: skip if the fill's
    cost exceeds 1.10 x the signal-time mark."""
    last = cd.n_min - 2
    if rule == 'E0': return m, np.nan, None
    if rule.startswith('E1L'):
        L = int(rule[3]); k = min(m + L, last)
        if rule.endswith('g'):
            c = _cost_ps(cd, legs, ratio, nleg, k); mk = _mark_ps(cd, legs, ratio, nleg, m)
            if np.isfinite(c) and np.isfinite(mk) and mk > 0 and c > 1.10 * mk: return None, np.nan, 'chase_guard'
        return k, np.nan, None
    if rule.startswith('E2'):
        s0 = cd.spot[m]
        for k in range(m + 1, min(m + 15, last) + 1):
            if k % 5 == 0 and (cd.spot[k] - s0) * (direction if direction != 0 else 1) > 0:
                if rule.endswith('g'):
                    c = _cost_ps(cd, legs, ratio, nleg, k); mk = _mark_ps(cd, legs, ratio, nleg, m)
                    if np.isfinite(c) and np.isfinite(mk) and mk > 0 and c > 1.10 * mk: return None, np.nan, 'chase_guard'
                return k, np.nan, None
        return None, np.nan, 'no_confirmation'
    if rule.startswith('E3'):
        mk = _mark_ps(cd, legs, ratio, nleg, m); c0 = _cost_ps(cd, legs, ratio, nleg, m)
        if not (np.isfinite(mk) and np.isfinite(c0)): return None, np.nan, 'no_quote'
        if rule == 'E3': lim = mk - 0.5 * (c0 - mk)
        else:
            if not np.isfinite(atr5) or not np.isfinite(delta_net): return None, np.nan, 'no_atr'
            lim = mk - abs(delta_net) * 0.25 * atr5
        for k in range(m + 1, min(m + 10, last) + 1):
            c = _cost_ps(cd, legs, ratio, nleg, k)
            if np.isfinite(c) and c <= lim - 0.01: return k, lim, None
        return None, np.nan, 'limit_unfilled'
    raise ValueError(rule)

def _seed(root, session, i, s):
    return zlib.crc32(f'{root}|{session}|{i}|{s}'.encode())

def controls(ev_day: pl.DataFrame, root: str, n_min: int, spot: np.ndarray) -> list[dict]:
    out = []
    hi = min(WINDOW[1], n_min - 61)
    for i, r in enumerate(ev_day.iter_rows(named=True)):
        dist = abs(r['spot'] - r['inv']) if (r['inv'] is not None and r['spot'] is not None and np.isfinite(r['inv'])) else None
        for s in SEEDS:
            rng = np.random.default_rng(_seed(root, r['session'], i, s))
            m = int(rng.integers(WINDOW[0], hi + 1))
            inv = float(spot[m] - r['direction'] * dist) if dist is not None else np.nan
            out.append({**r, 'm': m, 'inv': inv, 'ctrl': s, 'event_i': i})
    return out

HOLDOUT_START = dt.date(2025, 10, 1)
AGG = ['n', 'wins', 'pnl', 'pnl_sq', 'win_pnl', 'loss_pnl', 'cost', 'capital', 'hold', 'fees', 'partial1', 'partial2', 'runner',
       'lot_initial', 'lot_add', 'lot_dd', 'lot_scale', 'n_filled']

def _agg_block(o: np.ndarray) -> np.ndarray:
    """Per-policy sums for one position's outputs [P, NO] -> [P, len(AGG)]."""
    f = o[:, ps.O['filled']] > 0
    pnl = np.where(f, o[:, ps.O['pnl']], 0.0)
    a = np.zeros((o.shape[0], len(AGG)))
    a[:, 0] = f; a[:, 1] = f & (pnl > 0); a[:, 2] = pnl; a[:, 3] = pnl * pnl
    a[:, 4] = np.where(pnl > 0, pnl, 0.0); a[:, 5] = np.where(pnl < 0, pnl, 0.0)
    a[:, 6] = np.where(f, np.abs(o[:, ps.O['cost0']]), 0.0); a[:, 7] = np.where(f, o[:, ps.O['capital_peak']], 0.0)
    a[:, 8] = np.where(f, o[:, ps.O['hold_min']], 0.0); a[:, 9] = np.where(f, o[:, ps.O['fees']], 0.0)
    a[:, 10] = o[:, ps.O['pnl_partial1']]; a[:, 11] = o[:, ps.O['pnl_partial2']]; a[:, 12] = o[:, ps.O['pnl_runner']]
    a[:, 13] = o[:, ps.O['pnl_lot_initial']]; a[:, 14] = o[:, ps.O['pnl_lot_add']]; a[:, 15] = o[:, ps.O['pnl_lot_dd']]
    a[:, 16] = o[:, ps.O['pnl_lot_scale']]; a[:, 17] = f
    return a

def run_root(root: str, stage: str, policy_set, sessions: list[dt.date] | None = None, out_root: str | None = None, log=print,
             mode: str = 'rows', include_holdout: bool = False, events_file: str | None = None, entry_rule: str = 'E0',
             setups: tuple | None = None, structures: tuple | None = None, with_controls: bool = True):
    """mode 'rows': one outcome row per (position, policy). mode 'daily': per (session, setup, structure, policy, real or
    control) sums (AGG) — the management grid, too large to keep per row. The hold-out (from 2025-10-01) is left out
    unless include_holdout."""
    out_dir = out_root or f'{paths.WORK}/runs/{stage}/{root}'
    os.makedirs(out_dir, exist_ok=True)
    names = [n for n, _, _ in policy_set]; fams = [f for _, f, _ in policy_set]
    PM = np.vstack([p for _, _, p in policy_set])
    kind_p = {k: np.array([i for i, f in enumerate(fams) if f in pol.FAMILY_FOR_STRUCTURE[k]], np.int64) for k in pol.FAMILY_FOR_STRUCTURE}
    ev_all = pl.read_parquet(events_file or f'{paths.WORK}/events/{root}.parquet')
    if setups: ev_all = ev_all.filter(pl.col('setup').is_in(list(setups)))
    ss = sessions or cm.sessions_0dte(root)
    if not include_holdout: ss = [d for d in ss if d < HOLDOUT_START]
    st = ax.make_store()
    daily = {}; chunks = ([], [], [], [], [], [])
    feat = ax.feature_frame(st, root, ss[0], ss[-1])
    fby = {s: g for (s,), g in feat.group_by(['session'], maintain_order=True)}
    opens = feat.group_by('session').agg(pl.col('open').first()).sort('session')
    nxt = dict(zip(opens['session'].to_list()[:-1], opens['open'].to_list()[1:]))
    cash = root.startswith('SPX')
    pos_rows, out_blocks, out_keys = [], [], []
    t0 = time.time(); n_runs = 0; pid = 0
    for si, session in enumerate(ss):
        ev_day = ev_all.filter(pl.col('session') == session)
        if ev_day.height == 0: continue
        cd = cm.load_0dte(root, session)
        if cd is None or session not in fby: continue
        series = ax.session_series(fby[session], session, cd.n_min)
        a = {'ema5': series['ema5'], 'rsi': series['rsi'], 'atr5': series['atr5'], 'ativ': ax.atm_iv(cd)}
        tg = ax.t_years_grid(cd)
        nop = float(nxt.get(session, np.nan))
        items = [{**r, 'ctrl': -1, 'event_i': i} for i, r in enumerate(ev_day.iter_rows(named=True))]
        if with_controls: items += controls(ev_day, root, cd.n_min, cd.spot)
        snaps = {}
        for it in items:
            m = int(it['m'])
            if m >= cd.n_min - 2: continue
            if m not in snaps: snaps[m] = stc.snapshot(cd, m, tg[m])
            for code in allowed_structures(it['setup'], it['direction']):
                if structures and code not in structures: continue
                m_sig = m
                if entry_rule.startswith('E2'):
                    # confirmation first, then the structure is chosen at the confirmation minute
                    k, _, why = entry_plan(cd, 'E2', m, int(it['direction']), None, None, 0, np.nan, np.nan)
                    if k is None:
                        pos_rows.append(dict(pos_id=pid, session=session, event_i=it['event_i'], ctrl=it['ctrl'], setup=it['setup'], direction=int(it['direction']),
                                             structure=code, m=m, spot=float(cd.spot[m]), inv=np.nan, skip=why)); pid += 1; continue
                    m = k
                    if m not in snaps: snaps[m] = stc.snapshot(cd, m, tg[m])
                legs, ratio, info = stc.build(cd, m, tg[m], code, it['direction'], snaps[m])
                key = dict(pos_id=pid, session=session, event_i=it['event_i'], ctrl=it['ctrl'], setup=it['setup'], direction=int(it['direction']),
                           structure=code, m=m, spot=float(cd.spot[m]), inv=float(it['inv']) if it['inv'] is not None else np.nan)
                if legs is None:
                    pos_rows.append({**key, 'skip': info['skip']}); pid += 1; m = m_sig; continue
                nleg = info['nleg']
                override = np.nan
                if entry_rule == 'E2g':
                    c = _cost_ps(cd, legs, ratio, nleg, m); mk = _mark_ps(cd, legs, ratio, nleg, m_sig)
                    if np.isfinite(c) and np.isfinite(mk) and mk > 0 and c > 1.10 * mk:
                        pos_rows.append({**key, 'skip': 'chase_guard'}); pid += 1; m = m_sig; continue
                if entry_rule not in ('E0', 'E2', 'E2g'):
                    dnet = float(np.nansum(np.array(info['deltas']) * ratio[:nleg]))
                    k, lim, why = entry_plan(cd, entry_rule, m, int(it['direction']), legs, ratio, nleg, float(a['atr5'][m]), dnet)
                    if k is None:
                        pos_rows.append({**key, 'skip': why}); pid += 1; m = m_sig; continue
                    m = k; override = lim
                h = ps.hindsight(cd.bid, cd.ask, legs, ratio, nleg, m, min(pol.CUT, cd.n_min - 1), 0.0)
                he = ps.hindsight(cd.bid, cd.ask, legs, ratio, nleg, m, cd.n_min - 1, 0.0)
                if np.isfinite(override): h[0] = override * 100.0
                pos_rows.append({**key, 'skip': None, 'k1': info['strikes'][0], 'k2': info['strikes'][1] if nleg > 1 else np.nan,
                                 'd1': info['deltas'][0], 'd2': info['deltas'][1] if nleg > 1 else np.nan,
                                 'iv1': info['ivs'][0], 'iv2': info['ivs'][1] if nleg > 1 else np.nan, 'rel_spread': info['rel_spread'],
                                 'cost0': h[0], 'mark0': h[7], 'mfe_liq': h[1] - h[0], 't_mfe': h[2] - m, 'mae_liq': h[3] - h[0], 't_mae': h[4] - m,
                                 'mfe_mark': h[5] - h[7], 'liq_cutoff': h[6] - h[0], 'mfe_liq_exp': he[1] - he[0], 'liq_last': he[6]})
                kind = pol.kind_of(code)
                pidx = kind_p[kind]
                o = ps.run_policies(cd.bid, cd.ask, cd.strike, cd.is_call, cd.spot, a['ema5'], a['rsi'], a['atr5'], a['ativ'], cd.n_min,
                                    legs, ratio, nleg, m, int(it['direction']), float(it['inv']) if it['inv'] is not None else np.nan,
                                    override, nop, cash, info['short_strike'], PM, pidx)
                if mode == 'rows':
                    out_blocks.append(o.astype(np.float32)); out_keys.append(np.column_stack([np.full(pidx.size, pid), pidx]))
                else:
                    k = (session, it['setup'], code, 0 if it['ctrl'] < 0 else 1)
                    acc = daily.get(k)
                    if acc is None: acc = daily[k] = np.zeros((len(PM), len(AGG)))
                    acc[pidx] += _agg_block(o)
                n_runs += pidx.size; pid += 1; m = m_sig
        if mode == 'daily': _flush_daily(daily, chunks)
        if si % 50 == 0: log(f'{root} {stage}: {si + 1}/{len(ss)} sessions, {pid} positions, {n_runs} runs, {time.time() - t0:.0f}s')
    pos = pl.DataFrame(pos_rows, infer_schema_length=None)
    pos.write_parquet(f'{out_dir}/positions.parquet', compression='zstd')
    if mode == 'daily':
        _flush_daily(daily, chunks)
        _write_daily(out_dir, chunks)
    else:
        _write_rows(out_dir, out_keys, out_blocks)
    meta = {'root': root, 'stage': stage, 'mode': mode, 'sessions': [str(ss[0]), str(ss[-1]), len(ss)], 'positions': pid, 'runs': int(n_runs),
            'policies': names, 'families': fams, 'seconds': round(time.time() - t0, 1), 'seeds': list(SEEDS), 'window': list(WINDOW),
            'holdout_included': include_holdout, 'generated': dt.datetime.now(dt.timezone.utc).isoformat()}
    json.dump(meta, open(f'{out_dir}/run.json', 'w'), indent=1)
    log(f'{root} {stage}: done {pid} positions {n_runs} runs in {time.time() - t0:.0f}s')
    return meta

def _flush_daily(daily, chunks):
    """Move one session's accumulators into compact column chunks (the dict per root ran out of memory)."""
    sess, setup, struct, ctrl, polc, vals = chunks
    for (session, st_, code, cv), acc in daily.items():
        used = np.where(acc[:, 0] > 0)[0]
        if used.size == 0: continue
        sess.append(np.full(used.size, (session - dt.date(1970, 1, 1)).days, np.int32))
        setup.append(np.full(used.size, st_, object)); struct.append(np.full(used.size, code, object))
        ctrl.append(np.full(used.size, cv, np.int8)); polc.append(used.astype(np.int16)); vals.append(acc[used].astype(np.float32))
    daily.clear()

def _write_daily(out_dir, chunks):
    sess, setup, struct, ctrl, polc, vals = chunks
    V = np.vstack(vals)
    cols = {'session': pl.Series(np.concatenate(sess)).cast(pl.Date), 'setup': np.concatenate(setup).astype(str),
            'structure': np.concatenate(struct).astype(str), 'ctrl': np.concatenate(ctrl), 'policy': np.concatenate(polc)}
    for i, c in enumerate(AGG): cols[c] = V[:, i]
    pl.DataFrame(cols).write_parquet(f'{out_dir}/daily.parquet', compression='zstd')

def _write_rows(out_dir, out_keys, out_blocks):
    K = np.vstack(out_keys); O = np.vstack(out_blocks)
    keep = ['filled', 'exit_m', 'pnl', 'fees', 'cost0', 'credit', 'capital_peak', 'units_peak', 'pnl_lot_initial', 'pnl_lot_add', 'pnl_lot_dd',
            'pnl_lot_scale', 'n_adds', 'n_dd', 'n_scale', 'final_reason', 'hold_min', 'warned'] + [f'pnl_{r}' for r in ps.R_NAMES]
    cols = {'pos_id': K[:, 0].astype(np.int32), 'policy': K[:, 1].astype(np.int16)}
    for c in keep: cols[c] = O[:, ps.O[c]]
    pl.DataFrame(cols).write_parquet(f'{out_dir}/outcomes.parquet', compression='zstd')
