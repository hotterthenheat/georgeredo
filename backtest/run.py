"""Backtest driver: generate signals for every variant, prefetch option bars, simulate exits and costs, write trades CSV."""
import os, sys, json, csv, datetime, itertools, concurrent.futures, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data, features, exits, costs
_obc = {}
_orig_option_bars = data.option_bars
def _memo_option_bars(cid, date):
    k = (cid, date)
    if k not in _obc: _obc[k] = _orig_option_bars(cid, date)
    return _obc[k]
data.option_bars = _memo_option_bars
HERE = os.path.dirname(os.path.abspath(__file__))
days = json.load(open(HERE + '/trading_days.json'))
START, END, TICKERS, OUT = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4]
random.seed(42)
sel = [d for d in days if START <= d <= END]

WINDOWS = {'all': [(9*60+35, 15*60+30)], 'morning': [(10*60, 12*60)], 'no_lunch': [(9*60+35, 12*60), (13*60+15, 15*60)]}
LEVELSETS = {'ict': ('PDH','PDL','PWH','PWL','PMH','PML','ORH','ORL'), 'ict+gex': ('PDH','PDL','PWH','PWL','PMH','PML','ORH','ORL','CALL_WALL','PUT_WALL')}
GATES = ('none', 'posgamma_fade', 'avoid_pin')
MODES = ('sweep', 'continuation')
ENGINES = ('ladder', 'trail', 'bracket', 'hold')
COOLDOWN_MIN = 30; MAX_PER_DAY = 5
STRIKE_STEP = {'SPY': 1.0, 'QQQ': 1.0, 'IWM': 1.0}

def in_window(t, win):
    m = t.hour * 60 + t.minute
    return any(a <= m < b for a, b in WINDOWS[win])

def regime(gex, px):
    f = gex.get('gamma_flip')
    if f is None or px is None: return None
    return 'POS' if px > f else 'NEG'

def gate_ok(gate, gex, px, direction, mode):
    if gate == 'none': return True
    if gate == 'posgamma_fade':
        r = regime(gex, px)
        return (r == 'POS' and mode == 'sweep') or (r == 'NEG' and mode == 'continuation')
    if gate == 'avoid_pin':
        m = gex.get('gamma_magnet')
        return not (m and abs(px - m) / px < 0.001)
    return True

# ---------- phase 1: signals ----------
signals = []  # dict(ticker,date,i,t,px,direction,level,level_px,mode,levelset)
day_cache = {}
def load_day(t, d):
    if (t, d) not in day_cache: day_cache[(t, d)] = data.underlying_bars(t, d)
    return day_cache[(t, d)]
for tk in TICKERS:
    for d in sel:
        rth, pre = load_day(tk, d)
        if len(rth) < 300: continue
        idx = days.index(d)
        prev = [load_day(tk, days[idx-1])[0]] if idx >= 1 else []
        wk = [load_day(tk, days[j])[0] for j in range(max(0, idx-5), idx)]
        # prior week = the five sessions before today (simple rolling week)
        gex_prev = data.gex_levels(tk, days[idx-1]) if idx >= 1 else {}
        vwap, atr = features.running_series(rth)
        lv_static = features.session_levels(rth[:15], pre, prev, wk, gex_prev)   # pre-session levels (no ORB yet)
        lv_orb = features.session_levels(rth[:16], pre, prev, wk, gex_prev)      # adds ORH/ORL once the first 15 minutes are complete
        for lsname, lset in LEVELSETS.items():
            for mode in MODES:
                last_sig = {}
                for i in range(20, len(rth) - 5):
                    lv_all = lv_orb if i >= 15 else lv_static
                    lv = {k: v for k, v in lv_all.items() if k in lset or k in ('FLIP', 'MAGNET')}
                    for direction, name, L in features.detect(rth, i, lv, vwap, atr, mode=mode):
                        key = (direction, name)
                        if key in last_sig and (rth[i]['t'] - last_sig[key]).total_seconds() < 600: continue
                        last_sig[key] = rth[i]['t']
                        signals.append(dict(ticker=tk, date=d, i=i, t=rth[i]['t'], px=rth[i]['c'], direction=direction, level=name, level_px=L, mode=mode, levelset=lsname, regime=regime(gex_prev, rth[i]['c']), gex=gex_prev, vwap=vwap[i]))
print('raw signals', len(signals), collections.Counter((s['mode'], s['levelset']) for s in signals), flush=True)

# ---------- phase 2: option bars ----------
def contract_for(s):
    step = STRIKE_STEP[s['ticker']]; strike = round(s['px'] / step) * step
    side = 'C' if s['direction'] == 'BULLISH' else 'P'
    exp = datetime.date.fromisoformat(s['date'])
    return data.contract_id(s['ticker'], exp, side, strike), strike, side
needs = sorted({(contract_for(s)[0], s['date']) for s in signals})
print('contract-days to fetch', len(needs), flush=True)
def fetch(j): return j, len(data.option_bars(*j))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for n, (j, k) in enumerate(ex.map(fetch, needs)):
        if n % 300 == 0: print('bars', n, '/', len(needs), data.STATS, flush=True)

# ---------- phase 3: simulate ----------
def simulate_variant(window, gate, mode, lsname, engine, sigs):
    trades = []; open_until = {}; last_entry = {}; count = collections.Counter()
    for s in sorted(sigs, key=lambda s: s['t']):
        if s['mode'] != mode or s['levelset'] != lsname: continue
        if not in_window(s['t'], window): continue
        if not gate_ok(gate, s['gex'], s['px'], s['direction'], mode): continue
        tk, d = s['ticker'], s['date']
        if count[(tk, d)] >= MAX_PER_DAY: continue
        if (tk, d) in open_until and s['t'] < open_until[(tk, d)]: continue
        if (tk, d) in last_entry and (s['t'] - last_entry[(tk, d)]).total_seconds() < COOLDOWN_MIN * 60: continue
        cid, strike, side = contract_for(s)
        bars = data.option_bars(cid, d)
        # entry at the first option bar strictly after the signal minute
        eidx = next((k for k, b in enumerate(bars) if b['t'] > s['t']), None)
        if eidx is None or (bars[eidx]['t'] - s['t']).total_seconds() > 180: continue
        eb = bars[eidx]; entry_px = eb['vw'] or eb['o']
        if not entry_px or entry_px < 0.05: continue
        legs = exits.simulate(bars, eidx, entry_px, engine, {'stop': -0.25})
        if not legs: continue
        res = {m: costs.settle(tk, eb, entry_px, legs, m) for m in ('mid', 'spread', 'adverse')}
        exit_t = max(l[2] for l in legs); reasons = '+'.join(l[3] for l in legs)
        trades.append(dict(variant=f'{mode}|{lsname}|{window}|{gate}|{engine}', ticker=tk, date=d, signal_t=s['t'].isoformat(), entry_t=eb['t'].isoformat(), exit_t=exit_t.isoformat(), direction=s['direction'], level=s['level'], regime=s['regime'] or '', contract=cid, strike=strike, entry_px=round(entry_px, 3), hold_min=round((exit_t - eb['t']).total_seconds()/60, 1), reasons=reasons,
                           ret_mid=round(res['mid']['ret'], 4), usd_mid=round(res['mid']['dollars'], 2), ret_spread=round(res['spread']['ret'], 4), usd_spread=round(res['spread']['dollars'], 2), ret_adverse=round(res['adverse']['ret'], 4), usd_adverse=round(res['adverse']['dollars'], 2), mfe=round(max((b['h'] for b in bars[eidx+1:] if b['t'] < exits._close_time(b['t'])), default=entry_px)/entry_px-1, 4)))
        open_until[(tk, d)] = exit_t; last_entry[(tk, d)] = eb['t']; count[(tk, d)] += 1
    return trades

all_trades = []
for window, gate, mode, lsname, engine in itertools.product(WINDOWS, GATES, MODES, LEVELSETS, ENGINES):
    tr = simulate_variant(window, gate, mode, lsname, engine, signals); all_trades += tr
    print('variant done', window, gate, mode, lsname, engine, len(tr), flush=True)
print('variants', len(WINDOWS)*len(GATES)*len(MODES)*len(LEVELSETS)*len(ENGINES), 'trades', len(all_trades), flush=True)

# ---------- write main results first ----------
os.makedirs(OUT, exist_ok=True)
with open(OUT + '/trades.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(all_trades[0].keys())); w.writeheader(); w.writerows(all_trades)
json.dump([dict(s, t=s['t'].isoformat(), gex=None) for s in signals], open(OUT + '/signals.json', 'w'))
print('main results written', flush=True)

# ---------- baselines: random-time entries with the same per-day counts (ladder engine, no gate, window all), 1 rep ----------
ref = [t for t in all_trades if t['variant'].endswith('|all|none|ladder')]
per_day = collections.Counter((t['ticker'], t['date'], t['variant'].split('|')[0]) for t in ref)
draws = []
for (tk, d, mode), n in per_day.items():
    rth, _ = load_day(tk, d)
    for _ in range(n):
        i = random.randrange(20, len(rth) - 40); t = rth[i]['t']
        if not in_window(t, 'all'): continue
        direction = random.choice(['BULLISH', 'BEARISH']); s = dict(ticker=tk, date=d, px=rth[i]['c'], direction=direction)
        cid, strike, side = contract_for(s); draws.append((tk, d, mode, t, direction, cid))
bneeds = sorted({(cid, d) for tk, d, mode, t, direction, cid in draws})
print('baseline draws', len(draws), 'contract-days', len(bneeds), flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for n, (j, k) in enumerate(ex.map(fetch, bneeds)):
        if n % 500 == 0: print('baseline bars', n, '/', len(bneeds), data.STATS, flush=True)
base = []
for tk, d, mode, t, direction, cid in draws:
    bars = data.option_bars(cid, d)
    eidx = next((k for k, b in enumerate(bars) if b['t'] > t), None)
    if eidx is None or (bars[eidx]['t'] - t).total_seconds() > 180: continue
    eb = bars[eidx]; entry_px = eb['vw'] or eb['o']
    if not entry_px or entry_px < 0.05: continue
    legs = exits.simulate(bars, eidx, entry_px, 'ladder', {'stop': -0.25})
    res = {m: costs.settle(tk, eb, entry_px, legs, m) for m in ('mid', 'spread', 'adverse')}
    base.append(dict(variant=f'RANDOM|{mode}|all|none|ladder', ticker=tk, date=d, direction=direction, ret_mid=res['mid']['ret'], usd_mid=res['mid']['dollars'], ret_spread=res['spread']['ret'], usd_spread=res['spread']['dollars'], ret_adverse=res['adverse']['ret'], usd_adverse=res['adverse']['dollars']))
print('baseline trades', len(base), data.STATS, flush=True)
with open(OUT + '/baseline.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(base[0].keys())); w.writeheader(); w.writerows(base)
print('written', OUT)
