"""Session levels, VWAP, ATR and sweep/continuation signal detection on 1-minute RTH bars."""
import datetime
def hl(bars): return (max(b['h'] for b in bars), min(b['l'] for b in bars)) if bars else (None, None)

def session_levels(day_rth, day_pre, prev_days_rth, week_days_rth, gex):
    """Levels known before the session (plus ORB after 09:45)."""
    lv = {}
    if prev_days_rth:
        pdh, pdl = hl(prev_days_rth[-1]); lv['PDH'] = pdh; lv['PDL'] = pdl; lv['PDC'] = prev_days_rth[-1][-1]['c']
    if week_days_rth:
        allb = [b for d in week_days_rth for b in d]; pwh, pwl = hl(allb); lv['PWH'] = pwh; lv['PWL'] = pwl
    if day_pre:
        pmh, pml = hl(day_pre); lv['PMH'] = pmh; lv['PML'] = pml
    orb = [b for b in day_rth if b['t'].hour == 9 and b['t'].minute < 45]
    if len(orb) >= 10:
        orh, orl = hl(orb); lv['ORH'] = orh; lv['ORL'] = orl
    if gex:
        if gex.get('call_wall'): lv['CALL_WALL'] = gex['call_wall']
        if gex.get('put_wall'): lv['PUT_WALL'] = gex['put_wall']
        if gex.get('gamma_flip'): lv['FLIP'] = gex['gamma_flip']
        if gex.get('gamma_magnet'): lv['MAGNET'] = gex['gamma_magnet']
    return lv

RESIST = ('PDH', 'PWH', 'PMH', 'ORH', 'CALL_WALL')
SUPPORT = ('PDL', 'PWL', 'PML', 'ORL', 'PUT_WALL')

def running_series(rth):
    """Cumulative VWAP and ATR(14) per bar."""
    vwap = []; atr = []; cum_pv = 0.0; cum_v = 0; trs = []
    for i, b in enumerate(rth):
        cum_pv += (b['h'] + b['l'] + b['c']) / 3 * max(b['v'], 1); cum_v += max(b['v'], 1); vwap.append(cum_pv / cum_v)
        pc = rth[i - 1]['c'] if i else b['c']
        trs.append(max(b['h'] - b['l'], abs(b['h'] - pc), abs(b['l'] - pc)))
        atr.append(sum(trs[-14:]) / len(trs[-14:]))
    return vwap, atr

def detect(rth, i, levels, vwap, atr, mode='sweep', k=3, reclaim_atr=0.25, min_pct=0.0002):
    """Return list of (direction, level_name, level_price) signals at bar i (evaluated on its close)."""
    out = []
    if i < max(k, 15): return out
    px = rth[i]['c']; tol = max(reclaim_atr * atr[i], min_pct * px)
    win = rth[i - k + 1:i + 1]; prior = rth[max(0, i - k - 10):i - k + 1]
    for name, L in levels.items():
        if L is None or name in ('PDC', 'FLIP', 'MAGNET'): continue
        if name == 'ORH' or name == 'ORL':
            if rth[i]['t'].hour == 9: continue  # ORB only usable after it forms
        if name in RESIST:
            if mode == 'sweep':
                pierced = max(b['h'] for b in win) > L
                closes_above = sum(1 for b in win if b['c'] > L)
                was_below = prior and sum(1 for b in prior if b['c'] < L) >= len(prior) * 0.6
                if pierced and closes_above <= 1 and px < L - tol and was_below: out.append(('BEARISH', name, L))
            else:  # continuation: clean close above after being below
                was_below = prior and sum(1 for b in prior if b['c'] < L) >= len(prior) * 0.8
                if was_below and px > L + tol and rth[i - 1]['c'] <= L: out.append(('BULLISH', name, L))
        elif name in SUPPORT:
            if mode == 'sweep':
                pierced = min(b['l'] for b in win) < L
                closes_below = sum(1 for b in win if b['c'] < L)
                was_above = prior and sum(1 for b in prior if b['c'] > L) >= len(prior) * 0.6
                if pierced and closes_below <= 1 and px > L + tol and was_above: out.append(('BULLISH', name, L))
            else:
                was_above = prior and sum(1 for b in prior if b['c'] > L) >= len(prior) * 0.8
                if was_above and px < L - tol and rth[i - 1]['c'] >= L: out.append(('BEARISH', name, L))
    return out
