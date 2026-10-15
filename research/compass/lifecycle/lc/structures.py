"""Strike selection for every Compass structure at the fill minute (lifecycle protocol §4), on the chain's snapshot.
IV and delta are solved from each contract's mid with the stated carry (engine.greeks).

Returns (legs, ratio, info) or (None, None, {'skip': reason}). Legs index ChainDay contracts; ratio +1 long, -1 short."""
from __future__ import annotations
import numpy as np
import os, sys
from . import paths
sys.path.insert(0, os.path.dirname(paths.HERE))
from . import bs  # noqa: E402

STRUCTURES = ('LC-S', 'LP-S', 'LC-B', 'LP-B', 'DCS', 'DPS', 'CPS', 'CSP', 'STR', 'STG')
DIRECTIONAL_LONG = {+1: ('LC-S', 'LC-B', 'DCS', 'CPS', 'CSP'), -1: ('LP-S', 'LP-B', 'DPS')}
MAX_REL_SPREAD = 0.20
MIN_LONG_ASK = 0.05

def snapshot(cd, m: int, t_years: float):
    bid = cd.bid[:, m]; ask = cd.ask[:, m]
    ok = np.isfinite(bid) & np.isfinite(ask) & (ask > 0) & (ask >= bid)
    mid = np.where(ok, (bid + ask) / 2.0, np.nan)
    S = cd.spot[m]
    right = np.where(cd.is_call, 1.0, -1.0)
    n = cd.strike.size
    tt = np.full(n, t_years); SS = np.full(n, S)
    iv = bs.implied_vol(mid, SS, cd.strike, tt, right)
    d = bs.delta(SS, cd.strike, tt, np.where(np.isnan(iv), 0.3, iv), right)
    d = np.where(np.isnan(iv), np.nan, d)
    with np.errstate(invalid='ignore', divide='ignore'):
        rel = np.where(mid > 0, (ask - bid) / mid, np.nan)
    return dict(ok=ok, bid=bid, ask=ask, mid=mid, iv=iv, delta=d, rel=rel, S=S)

def _pick(sn, cd, call: bool, lo: float, hi: float, target: float, long_leg: bool):
    d = np.abs(sn['delta'])
    m = sn['ok'] & (cd.is_call == call) & np.isfinite(d) & (d >= lo) & (d <= hi) & (sn['rel'] <= MAX_REL_SPREAD)
    if long_leg: m &= sn['ask'] >= MIN_LONG_ASK
    else: m &= sn['bid'] > 0
    idx = np.where(m)[0]
    if idx.size == 0: return -1
    return int(idx[np.argmin(np.abs(d[idx] - target) + 1e-6 * sn['rel'][idx])])

def _next_lower_put(sn, cd, short_idx: int, min_width: float):
    K0 = cd.strike[short_idx]
    m = sn['ok'] & (~cd.is_call) & (cd.strike <= K0 - min_width - 1e-9) & (sn['ask'] >= 0.01)
    idx = np.where(m)[0]
    if idx.size == 0: return -1
    return int(idx[np.argmax(cd.strike[idx])])

def _nearest_strike_pair(sn, cd):
    S = sn['S']
    calls = np.where(sn['ok'] & cd.is_call)[0]; puts = np.where(sn['ok'] & ~cd.is_call)[0]
    common = np.intersect1d(cd.strike[calls], cd.strike[puts])
    if common.size == 0: return -1, -1
    K = common[np.argmin(np.abs(common - S))]
    return int(calls[np.where(cd.strike[calls] == K)[0][0]]), int(puts[np.where(cd.strike[puts] == K)[0][0]])

def build(cd, m: int, t_years: float, code: str, direction: int = 0, sn: dict | None = None):
    sn = sn or snapshot(cd, m, t_years)
    min_w = 5.0 if cd.root.startswith('SPX') else 1.0
    def fail(r): return None, None, {'skip': r}
    if code in ('LC-S', 'LP-S'):
        c = _pick(sn, cd, code == 'LC-S', 0.50, 0.80, 0.55, True)
        if c < 0: return fail('no_steady')
        legs, ratio = [c], [1]
    elif code in ('LC-B', 'LP-B'):
        c = _pick(sn, cd, code == 'LC-B', 0.10, 0.35, 0.20, True)
        if c < 0: return fail('no_big_payoff')
        legs, ratio = [c], [1]
    elif code in ('DCS', 'DPS'):
        call = code == 'DCS'
        a = _pick(sn, cd, call, 0.40, 0.60, 0.50, True)
        b = _pick(sn, cd, call, 0.15, 0.35, 0.25, False)
        if a < 0 or b < 0: return fail('no_spread_leg')
        if (call and cd.strike[b] <= cd.strike[a]) or ((not call) and cd.strike[b] >= cd.strike[a]): return fail('spread_inverted')
        legs, ratio = [a, b], [1, -1]
    elif code == 'CPS':
        s = _pick(sn, cd, False, 0.15, 0.30, 0.20, False)
        if s < 0: return fail('no_short_put')
        l = _next_lower_put(sn, cd, s, min_w)
        if l < 0: return fail('no_wing')
        legs, ratio = [s, l], [-1, 1]
    elif code == 'CSP':
        s = _pick(sn, cd, False, 0.20, 0.40, 0.30, False)
        if s < 0: return fail('no_short_put')
        legs, ratio = [s], [-1]
    elif code == 'STR':
        c, p = _nearest_strike_pair(sn, cd)
        if c < 0: return fail('no_atm_pair')
        if sn['rel'][c] > MAX_REL_SPREAD or sn['rel'][p] > MAX_REL_SPREAD: return fail('wide')
        legs, ratio = [c, p], [1, 1]
    elif code == 'STG':
        c = _pick(sn, cd, True, 0.15, 0.35, 0.25, True); p = _pick(sn, cd, False, 0.15, 0.35, 0.25, True)
        if c < 0 or p < 0: return fail('no_strangle_leg')
        legs, ratio = [c, p], [1, 1]
    else:
        raise ValueError(code)
    info = {'strikes': [float(cd.strike[i]) for i in legs], 'rights': ['C' if cd.is_call[i] else 'P' for i in legs],
            'deltas': [float(sn['delta'][i]) for i in legs], 'ivs': [float(sn['iv'][i]) for i in legs],
            'rel_spread': float(np.nanmax(sn['rel'][legs])), 'spot': float(sn['S'])}
    short = [cd.strike[i] for i, r in zip(legs, ratio) if r < 0]
    info['short_strike'] = float(short[0]) if short else float('nan')
    return np.array(legs + [0] * (4 - len(legs)), np.int64), np.array(ratio + [0] * (4 - len(ratio)), np.float64), {**info, 'nleg': len(legs)}
