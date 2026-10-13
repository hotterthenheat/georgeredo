"""Tests 1-5: enumerate decision points on cached underlying bars, prefetch option bars once, simulate, write CSVs under csv/.
Usage: python3 -I run_tests.py            (needs UW_API_TOKEN and BT_CACHE in the environment)"""
import os, sys, random, collections, datetime, math, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
random.seed(42)
t0 = time.time()
DAYSET = []
for tk in C.TICKERS:
    for d in C.SEL:
        rth, pre = C.ubars(tk, d)
        if len(rth) < 300: print('skip half-day', tk, d, len(rth)); continue
        DAYSET.append((tk, d, rth))
print('ticker-days', len(DAYSET), flush=True)

STRADDLE_T = [575, 600, 660, 780, 870]          # 09:35 10:00 11:00 13:00 14:30
STRANGLE_T = 600
STRANGLE_W = {'SPY': 0.005, 'QQQ': 0.005, 'IWM': 0.0075}
RAND_T = {(tk, d): random.randrange(575, 871) for tk, d, _ in DAYSET}       # random-time baseline for combos
RAND_ORB = {(tk, d): (random.randrange(586, 900), random.choice('CP')) for tk, d, _ in DAYSET}

def close_px(rth):
    return C.px_before(rth, C.CLOSE_MIN + 1)   # close of the 15:55 bar (last bar with start <= 15:55)

def base_row(tk, d, rth):
    return dict(ticker=tk, date=d, weekday=C.weekday(d), ivpct=C.ivpct_prior(tk, d))

# ---------------- decision enumeration ----------------
needs = set(); straddle_dec = []; strangle_dec = []; orb_dec = []; mom_dec = []; gap_dec = []
def orb_events(rth):
    orb = [b for b in rth if C.hm(b['t']) < 585]
    if len(orb) < 10: return None
    orh = max(b['h'] for b in orb); orl = min(b['l'] for b in orb); ev = {}
    for i, b in enumerate(rth):
        if C.hm(b['t']) < 585: continue
        if 'UP' not in ev and b['c'] > orh: ev['UP'] = i
        if 'DN' not in ev and b['c'] < orl: ev['DN'] = i
        if len(ev) == 2: break
    return orh, orl, ev

for tk, d, rth in DAYSET:
    idx = C.DAYS.index(d)
    # T1 straddles at fixed times + one random time
    for T in STRADDLE_T + [RAND_T[(tk, d)]]:
        px = C.px_before(rth, T); K = C.atm(px)
        straddle_dec.append((tk, d, T, px, K, T in STRADDLE_T)); needs.add((C.cid(tk, d, 'C', K), d)); needs.add((C.cid(tk, d, 'P', K), d))
    # T2 strangle at 10:00 + random time
    for T in (STRANGLE_T, RAND_T[(tk, d)]):
        px = C.px_before(rth, T); w = STRANGLE_W[tk]; Kc = float(round(px * (1 + w))); Kp = float(round(px * (1 - w)))
        strangle_dec.append((tk, d, T, px, Kc, Kp, T == STRANGLE_T)); needs.add((C.cid(tk, d, 'C', Kc), d)); needs.add((C.cid(tk, d, 'P', Kp), d))
    # T3 ORB events (+ random baseline)
    oe = orb_events(rth)
    if oe:
        orh, orl, ev = oe
        for side, i in ev.items():
            K = C.atm(rth[i]['c']); orb_dec.append((tk, d, side, i, orh, orl, K))
            if C.hm(rth[i]['t']) < 900: needs.add((C.cid(tk, d, 'C', K), d)); needs.add((C.cid(tk, d, 'P', K), d))
        Tr, _ = RAND_ORB[(tk, d)]; Kr = C.atm(C.px_before(rth, Tr)); needs.add((C.cid(tk, d, 'C', Kr), d)); needs.add((C.cid(tk, d, 'P', Kr), d))
    # T4 15:00 momentum trade
    px = C.px_before(rth, 900); K = C.atm(px); mom_dec.append((tk, d, px, K)); needs.add((C.cid(tk, d, 'C', K), d)); needs.add((C.cid(tk, d, 'P', K), d))
    # T5 gap (contracts = the 09:35 ATM pair, already in needs)
    prev_rth = C.ubars(tk, C.DAYS[idx - 1])[0]
    if prev_rth: gap_dec.append((tk, d, prev_rth[-1]['c'], rth[0]['o'] / prev_rth[-1]['c'] - 1))
print('decisions: straddle', len(straddle_dec), 'strangle', len(strangle_dec), 'orb', len(orb_dec), 'mom', len(mom_dec), 'gap', len(gap_dec), '| unique contract-days', len(needs), flush=True)
cached = sum(1 for c, d in needs if os.path.exists(os.path.join(C.data.CACHE, C.data._key(f'option-contract/{c}/intraday', {'date': d}) + '.json.gz')))
print('already cached', cached, 'to fetch', len(needs) - cached, flush=True)
C.prefetch(needs, 'options')
print('prefetch done at', round(time.time() - t0), 's', flush=True)

# ---------------- T1: straddles ----------------
rows = []
for tk, d, T, px, K, fixed in straddle_dec:
    rth = C._ub[(tk, d)][0]; legs = [(C.cid(tk, d, 'C', K), K, 'C'), (C.cid(tk, d, 'P', K), K, 'P')]
    move = abs(close_px(rth) / px - 1)
    for side, stop, name in (('short', None, 'short_hold'), ('short', 1.5, 'short_stop1.5'), ('short', 2.0, 'short_stop2.0'), ('long', None, 'long_hold'), ('long', 0.5, 'long_stop50')):
        r = C.sim_combo(tk, d, T, legs, side, stop)
        if r is None: continue
        rows.append(dict(test='T1_straddle', variant=name, time=C.mstr(T) if fixed else 'random', **base_row(tk, d, rth), T=C.mstr(T), under_px=px, strike=K, move_to_close=round(move, 5), **r))
C.write_csv(C.CSV + '/t1_straddles.csv', rows); print('T1 rows', len(rows), round(time.time() - t0), 's', flush=True)

# ---------------- T2: strangles ----------------
rows = []
for tk, d, T, px, Kc, Kp, fixed in strangle_dec:
    rth = C._ub[(tk, d)][0]; legs = [(C.cid(tk, d, 'C', Kc), Kc, 'C'), (C.cid(tk, d, 'P', Kp), Kp, 'P')]
    move = abs(close_px(rth) / px - 1)
    for side, stop, name in (('short', None, 'short_hold'), ('short', 1.5, 'short_stop1.5'), ('short', 2.0, 'short_stop2.0'), ('long', None, 'long_hold')):
        r = C.sim_combo(tk, d, T, legs, side, stop)
        if r is None: continue
        rows.append(dict(test='T2_strangle', variant=name, time=C.mstr(T) if fixed else 'random', **base_row(tk, d, rth), T=C.mstr(T), under_px=px, strike_c=Kc, strike_p=Kp, move_to_close=round(move, 5), **r))
C.write_csv(C.CSV + '/t2_strangles.csv', rows); print('T2 rows', len(rows), round(time.time() - t0), 's', flush=True)

# ---------------- T3: opening-range break, underlying + options ----------------
urows = []; orows = []
first_break = {}
for tk, d, side, i, orh, orl, K in orb_dec:
    if (tk, d) not in first_break or i < first_break[(tk, d)][1]: first_break[(tk, d)] = (side, i)
for tk, d, side, i, orh, orl, K in orb_dec:
    rth = C._ub[(tk, d)][0]; s = 1 if side == 'UP' else -1; c0 = rth[i]['c']; n = len(rth)
    cl = close_px(rth); j30 = min(i + 30, n - 1); j60 = min(i + 60, n - 1)
    fut = [s * (b['c'] / c0 - 1) for b in rth[i + 1:] if C.hm(b['t']) <= C.CLOSE_MIN]
    inside = lambda b: (b['c'] < orh) if side == 'UP' else (b['c'] > orl)
    u = dict(test='T3_orb', **base_row(tk, d, rth), side=side, first=int(first_break[(tk, d)] == (side, i)), break_t=C.mstr(C.hm(rth[i]['t'])), break_px=c0, strike=K,
             or_width_pct=round((orh - orl) / orl * 100, 3), ret30=round(s * (rth[j30]['c'] / c0 - 1) * 1e4, 1), ret60=round(s * (rth[j60]['c'] / c0 - 1) * 1e4, 1), ret_close=round(s * (cl / c0 - 1) * 1e4, 1),
             back_inside30=int(any(inside(b) for b in rth[i + 1:i + 31])), back_inside60=int(any(inside(b) for b in rth[i + 1:i + 61])),
             mfe_bp=round(max(fut, default=0) * 1e4, 1), mae_bp=round(min(fut, default=0) * 1e4, 1))
    urows.append(u)
    if C.hm(rth[i]['t']) >= 900: continue
    T = C.hm(rth[i]['t'])
    for opt in 'CP':
        r = C.sim_long(tk, d, C.cid(tk, d, opt, K), T, 'trail', strict_after=True)
        if r is None: continue
        style = 'breakout' if (opt == 'C') == (side == 'UP') else 'fade'
        orows.append(dict(test='T3_orb_opt', variant=style, **base_row(tk, d, rth), side=side, first=u['first'], break_t=u['break_t'], opt=opt, strike=K, **r))
# random-time, random-direction baseline on days with a first break before 15:00
for (tk, d), (side, i) in first_break.items():
    rth = C._ub[(tk, d)][0]
    if C.hm(rth[i]['t']) >= 900: continue
    Tr, dr = RAND_ORB[(tk, d)]; Kr = C.atm(C.px_before(rth, Tr))
    for opt in 'CP':
        r = C.sim_long(tk, d, C.cid(tk, d, opt, Kr), Tr, 'trail')
        if r is None: continue
        orows.append(dict(test='T3_orb_opt', variant='random_coinflip', **base_row(tk, d, rth), side='RND', first=1, break_t=C.mstr(Tr), opt=opt, strike=Kr, **r))
C.write_csv(C.CSV + '/t3_orb_underlying.csv', urows); C.write_csv(C.CSV + '/t3_orb_options.csv', orows)
print('T3 rows', len(urows), len(orows), round(time.time() - t0), 's', flush=True)

# ---------------- T4: half-hour seasonality, momentum, 15:00 option ----------------
hrows = []; mrows = []
for tk, d, rth in DAYSET:
    bounds = [570 + 30 * k for k in range(14)]; prev = rth[0]['o']; j = 0; rets = []
    for k in range(13):
        last = None
        while j < len(rth) and C.hm(rth[j]['t']) < bounds[k + 1]: last = rth[j]; j += 1
        rets.append(last['c'] / prev - 1 if last else float('nan')); prev = last['c'] if last else prev
    r1500_1555 = C.px_before(rth, 956) / C.px_before(rth, 900) - 1
    hrows.append(dict(ticker=tk, date=d, weekday=C.weekday(d), ivpct=C.ivpct_prior(tk, d), **{f'hh{k:02d}': round(r * 1e4, 2) for k, r in enumerate(rets)}, r1500_1555=round(r1500_1555 * 1e4, 2), day_ret=round((rth[-1]['c'] / rth[0]['o'] - 1) * 1e4, 2)))
C.write_csv(C.CSV + '/t4_halfhour_returns.csv', hrows)
for tk, d, px, K in mom_dec:
    rth = C._ub[(tk, d)][0]; h = next(x for x in hrows if x['ticker'] == tk and x['date'] == d); f30 = h['hh00']
    if f30 == 0 or math.isnan(f30): continue
    want = 'C' if f30 > 0 else 'P'
    for opt in 'CP':
        for eng in ('hold', 'trail'):
            r = C.sim_long(tk, d, C.cid(tk, d, opt, K), 900, eng)
            if r is None: continue
            mrows.append(dict(test='T4_mom_opt', variant=('momentum' if opt == want else 'contrarian') + '_' + eng, **base_row(tk, d, rth), first30_bp=f30, opt=opt, strike=K, under_px=px, **r))
C.write_csv(C.CSV + '/t4_momentum_options.csv', mrows); print('T4 rows', len(hrows), len(mrows), round(time.time() - t0), 's', flush=True)

# ---------------- T5: gap fill ----------------
grows = []; gorows = []
for tk, d, pc, gap in gap_dec:
    rth = C._ub[(tk, d)][0]; up = gap > 0
    touch = lambda b: (b['l'] <= pc) if up else (b['h'] >= pc)
    first_touch = next((C.hm(b['t']) for b in rth if touch(b)), None)
    g = dict(test='T5_gap', **base_row(tk, d, rth), prev_close=pc, open=rth[0]['o'], gap_bp=round(gap * 1e4, 1), absgap_bp=round(abs(gap) * 1e4, 1), big=int(abs(gap) > 0.003), direction='UP' if up else 'DN',
             filled_pre0935=int(first_touch is not None and first_touch < 575), filled_by1030=int(first_touch is not None and first_touch < 630), filled_by1555=int(first_touch is not None and first_touch <= 955),
             first_touch=C.mstr(first_touch) if first_touch is not None else '', ret_0935_close_bp=round((close_px(rth) / C.px_before(rth, 575) - 1) * 1e4, 1))
    grows.append(g)
    px = C.px_before(rth, 575); K = C.atm(px); toward = 'P' if up else 'C'
    for opt in 'CP':
        r = C.sim_long(tk, d, C.cid(tk, d, opt, K), 575, 'trail')
        if r is None: continue
        gorows.append(dict(test='T5_gap_opt', variant=('toward_fill' if opt == toward else 'with_gap'), big=g['big'], unfilled_at_0935=int(not g['filled_pre0935']), **base_row(tk, d, rth), gap_bp=g['gap_bp'], opt=opt, strike=K, **r))
C.write_csv(C.CSV + '/t5_gap_underlying.csv', grows); C.write_csv(C.CSV + '/t5_gap_options.csv', gorows)
print('T5 rows', len(grows), len(gorows), round(time.time() - t0), 's', C.data.STATS, flush=True)
