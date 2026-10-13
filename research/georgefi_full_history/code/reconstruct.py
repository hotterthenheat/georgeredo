"""Step 2: analyses A-E on the full GeorgeFi history vs Unusual Whales 1-minute bars.

A  Reported (GeorgeFi's own numbers)                     -> results/A_*.csv
B  Simulated fills at the reported entry/exit minutes      -> results/B_*.csv
C  Independent reconstruction from the entry minute only   -> results/C_*.csv  (exits.simulate engines + costs.settle, random baseline, MFE/MAE)
D  Era comparison Epoch 1 vs Epoch 2                      -> results/D_*.csv
E  Sanity / leakage checks                                 -> results/E_*.csv
and results/RESULTS.md (tables). Run from this folder after fetch_bars.py (all bars are then cache hits):
  set -a; . "$SP/secrets/research.env"; set +a; export BT_CACHE="$SP/bt/cache"; python3 -I reconstruct.py
"""
import sys, os, csv, json, time, math, random, datetime, collections, statistics
sys.path.insert(0, '/home/user/georgeredo/backtest')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
import exits, costs

T0 = time.time()
BOOT_N, BOOT_SEED, RAND_SEED = 1000, 7, 11
K_RANDOM, K_MFE = 20, 50                      # random entries per actual trade (baseline) / per trade (MFE percentile)
costs.HALF_SPREAD.setdefault('SINGLE', 0.02)  # runtime-only key for single names (2 % half-spread); file untouched
FEES = costs.FEES

def cost_key(root):
    if root in C.INDEX_ROOTS: return 'SPX'          # 1.5 % half-spread for SPXW/NDXP/RUTW
    if root in ('SPY', 'QQQ', 'IWM'): return root   # 1 % / 1 % / 2 %
    return 'SINGLE'                                 # 2 %

def hs_for(root): return costs.HALF_SPREAD[cost_key(root)]

# ---------- stats helpers ----------
def boot_ci(vals, n=BOOT_N, seed=BOOT_SEED):
    v = np.asarray(vals, dtype=float)
    if len(v) == 0: return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n, len(v)))
    means = v[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))

def max_dd(vals):
    peak = cum = 0.0; dd = 0.0
    for x in vals:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
    return dd

def metrics(vals, order_vals=None):
    v = [float(x) for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not v: return dict(n=0, total=float('nan'), mean=float('nan'), ci_lo=float('nan'), ci_hi=float('nan'), win_rate=float('nan'), pf=float('nan'), max_dd=float('nan'), median=float('nan'))
    w = sum(x for x in v if x > 0); l = -sum(x for x in v if x < 0)
    lo, hi = boot_ci(v)
    return dict(n=len(v), total=sum(v), mean=statistics.mean(v), ci_lo=lo, ci_hi=hi, win_rate=sum(1 for x in v if x > 0) / len(v),
                pf=(w / l) if l > 0 else float('inf'), max_dd=max_dd(order_vals if order_vals is not None else v), median=statistics.median(v))

def f0(x): return 'n/a' if x is None or (isinstance(x, float) and math.isnan(x)) else (f'{x:,.0f}' if abs(x) >= 100 else f'{x:,.1f}')
def f1(x): return 'n/a' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:,.1f}'
def f2(x): return 'n/a' if x is None or (isinstance(x, float) and math.isnan(x)) else ('inf' if x == float('inf') else f'{x:,.2f}')
def pct(x): return 'n/a' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{100 * x:.1f} %'
def ci(m): return f'[{f0(m["ci_lo"])}, {f0(m["ci_hi"])}]'

def write_csv(path, rows):
    if not rows: open(path, 'w').write(''); return
    cols = []
    for r in rows:
        for k in r:
            if k not in cols: cols.append(k)
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

# ---------- load ----------
rows = C.load_all()
cov = {r['trade_id']: r for r in csv.DictReader(open(C.RES + '/bar_coverage.csv'))}
for r in rows:
    c = cov[r['trade_id']]
    r['cov'] = c
    r['has_entry_bars'] = c['bars_available'] == 'True'
    r['bar_entry_min'] = c['bar_at_entry_minute'] == 'True'
    r['bar_exit_min'] = c['bar_at_exit_minute'] == 'True'
    r['label'] = f"E{r['epoch']}" if r['group'] == 'ledger' else 'paper'
    # paper rows closed with size 0: GeorgeFi reports the post-close size; imply the lot from pnl / (exit-entry) / 100
    r['size_implied'] = False
    if r['group'] == 'paper' and r['size_n'] == 0 and r['entry_px'] and r['exit_px'] and r['exit_px'] != r['entry_px']:
        s = r['pnl'] / ((r['exit_px'] - r['entry_px']) * 100)
        if abs(s - round(s)) < 0.01 and round(s) > 0: r['size_n'] = float(round(s)); r['size_implied'] = True
MD = []  # RESULTS.md lines
def H(s): MD.append(s); MD.append('')
def T(lines): MD.extend(lines); MD.append('')

# ---------- bars cache (in-process) ----------
_bars = {}
def bars_for(r, date):
    key = ('opt', r['cid'], date) if r['is_option'] else ('und', r['ticker'], date)
    if key not in _bars:
        _bars[key] = C.option_bars(r['cid'], date) if r['is_option'] else C.underlying_bars(r['ticker'], date)
    return _bars[key]

# ======================================================================
# A. Reported by GeorgeFi
# ======================================================================
def group_rows(rs, keyf):
    g = collections.OrderedDict()
    for r in rs: g.setdefault(keyf(r), []).append(r)
    return g

def a_table(rs, keyf, keynames, extra_filters=True):
    out = []
    for k, v in group_rows(rs, keyf).items():
        v = sorted(v, key=lambda r: (r['exit_dt'] or r['entry_dt']))
        pn = [r['pnl'] for r in v]; m = metrics(pn, pn)
        clean = [r['pnl'] for r in v if not r['data_err'] and not r['mismatch']]
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,)))
        rec.update(n=m['n'], sum_pnl_reported=round(m['total'], 2), win_rate=round(m['win_rate'], 4), mean=round(m['mean'], 2), ci_lo=round(m['ci_lo'], 2), ci_hi=round(m['ci_hi'], 2),
                   max_drawdown=round(m['max_dd'], 2), pf=round(m['pf'], 3) if m['pf'] != float('inf') else 'inf',
                   median_hold_min=round(statistics.median([r['hold'] for r in v if r['hold'] is not None]), 1) if any(r['hold'] is not None for r in v) else '',
                   median_size=statistics.median([r['size_n'] for r in v]), median_entry_premium=round(statistics.median([r['entry_px'] for r in v if r['entry_px']]), 3),
                   n_data_error=sum(1 for r in v if r['data_err']), n_pnl_mismatch=sum(1 for r in v if r['mismatch']),
                   sum_pnl_excl_dataerr_mismatch=round(sum(clean), 2), n_excl=len(clean))
        out.append(rec)
    return out

A1 = a_table(rows, lambda r: (r['label'], r['book'], r['account_type']), ['epoch', 'book', 'account_type'])
A1e = a_table(rows, lambda r: (r['label'], 'ALL', 'ALL'), ['epoch', 'book', 'account_type'])
A1b = a_table(rows, lambda r: (r['label'], r['book'], 'ALL'), ['epoch', 'book', 'account_type'])
write_csv(C.RES + '/A_reported.csv', A1e + A1b + A1)
A2 = a_table(rows, lambda r: (r['label'], r['month']), ['epoch', 'month']); write_csv(C.RES + '/A_reported_by_month.csv', A2)
A3 = a_table(rows, lambda r: (r['label'], r['root']), ['epoch', 'root']); write_csv(C.RES + '/A_reported_by_root.csv', A3)
print(f'A done {time.time() - T0:.0f}s', flush=True)

# ======================================================================
# B. Simulated fills at the reported times
# ======================================================================
B = []
for r in rows:
    if not (r['bar_entry_min'] and r['bar_exit_min']) or r['exit_dt'] is None: continue
    eb = C.bar_at(bars_for(r, r['entry_date']), r['entry_dt']); xb = C.bar_at(bars_for(r, r['exit_date']), r['exit_dt'])
    if eb is None or xb is None: continue
    mult = 100.0 if r['is_option'] else 1.0; sz = r['size_n']; hs = hs_for(r['root']) if r['is_option'] else 0.0; fee = FEES if r['is_option'] else 0.0
    ve, vx = C.vwap(eb), C.vwap(xb)
    mid = (vx - ve) * mult * sz
    spread = (vx * (1 - hs) - ve * (1 + hs)) * mult * sz - 2 * fee * sz
    adverse = (xb['l'] - eb['h']) * mult * sz - 2 * fee * sz
    ep, xp = r['entry_px'], r['exit_px']
    rec = dict(group=r['group'], epoch=r['label'], book=r['book'], account_type=r['account_type'], trade_id=r['trade_id'], ticker=r['ticker'], root=r['root'], side=r['side'],
               month=r['month'], is_0dte=r['dte0'], data_error=r['data_err'], pnl_mismatch=r['mismatch'], size=sz, size_implied=r['size_implied'],
               entry_premium=ep, exit_premium=xp, entry_bar_vwap=ve, exit_bar_vwap=vx, entry_bar_low=eb['l'], entry_bar_high=eb['h'], exit_bar_low=xb['l'], exit_bar_high=xb['h'],
               entry_bar_vol=eb['vol'], exit_bar_vol=xb['vol'],
               pnl_reported=r['pnl'], pnl_recomputed=(xp - ep) * mult * sz, pnl_mid=mid, pnl_spread=spread, pnl_adverse=adverse, diff_reported_minus_mid=r['pnl'] - mid,
               entry_inside=(eb['l'] - 1e-9 <= ep <= eb['h'] + 1e-9), exit_inside=(xb['l'] - 1e-9 <= xp <= xb['h'] + 1e-9),
               entry_pos_in_bar=((ep - eb['l']) / (eb['h'] - eb['l'])) if eb['h'] > eb['l'] else 0.5,
               exit_pos_in_bar=((xp - xb['l']) / (xb['h'] - xb['l'])) if xb['h'] > xb['l'] else 0.5,
               entry_below_vwap=ep < ve, exit_above_vwap=xp > vx, entry_hour_et=r['entry_dt'].hour + r['entry_dt'].minute / 60)
    B.append(rec)
write_csv(C.RES + '/B_trades.csv', B)

MODELS = ['reported', 'mid', 'spread', 'adverse']
def b_table(bs, keyf, keynames):
    out = []
    for k, v in group_rows(bs, keyf).items():
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,))); rec['n'] = len(v)
        for mdl in MODELS:
            col = 'pnl_reported' if mdl == 'reported' else f'pnl_{mdl}'
            m = metrics([x[col] for x in v], [x[col] for x in sorted(v, key=lambda z: z['trade_id'])])
            rec[f'{mdl}_total'] = round(m['total'], 2); rec[f'{mdl}_mean'] = round(m['mean'], 2); rec[f'{mdl}_ci_lo'] = round(m['ci_lo'], 2); rec[f'{mdl}_ci_hi'] = round(m['ci_hi'], 2)
            rec[f'{mdl}_win_rate'] = round(m['win_rate'], 4); rec[f'{mdl}_pf'] = round(m['pf'], 3) if m['pf'] != float('inf') else 'inf'
        d = [x['diff_reported_minus_mid'] for x in v]; md_ = metrics(d)
        rec['diff_rep_minus_mid_mean'] = round(md_['mean'], 2); rec['diff_ci_lo'] = round(md_['ci_lo'], 2); rec['diff_ci_hi'] = round(md_['ci_hi'], 2)
        out.append(rec)
    return out
B1 = b_table(B, lambda x: (x['epoch'], 'ALL', 'ALL'), ['epoch', 'book', 'account_type']) + b_table(B, lambda x: (x['epoch'], x['book'], 'ALL'), ['epoch', 'book', 'account_type']) + b_table(B, lambda x: (x['epoch'], x['book'], x['account_type']), ['epoch', 'book', 'account_type'])
write_csv(C.RES + '/B_simulated_fills.csv', B1)
B2 = b_table(B, lambda x: (x['epoch'], x['month']), ['epoch', 'month']); write_csv(C.RES + '/B_by_month.csv', B2)
B2b = b_table(B, lambda x: (x['epoch'], x['root']), ['epoch', 'root']); write_csv(C.RES + '/B_by_root.csv', B2b)

def realism(bs, keyf, keynames):
    out = []
    for k, v in group_rows(bs, keyf).items():
        opt = [x for x in v if x['side'] != 'SHARES'] or v
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,)))
        rec.update(n=len(v), entry_inside_share=round(sum(1 for x in v if x['entry_inside']) / len(v), 4), exit_inside_share=round(sum(1 for x in v if x['exit_inside']) / len(v), 4),
                   median_entry_pos_in_bar=round(statistics.median(x['entry_pos_in_bar'] for x in v), 3), median_exit_pos_in_bar=round(statistics.median(x['exit_pos_in_bar'] for x in v), 3),
                   entry_below_vwap_share=round(sum(1 for x in v if x['entry_below_vwap']) / len(v), 4), exit_above_vwap_share=round(sum(1 for x in v if x['exit_above_vwap']) / len(v), 4),
                   both_inside_share=round(sum(1 for x in v if x['entry_inside'] and x['exit_inside']) / len(v), 4),
                   sum_reported=round(sum(x['pnl_reported'] for x in v), 2), sum_reported_outside_range=round(sum(x['pnl_reported'] for x in v if not (x['entry_inside'] and x['exit_inside'])), 2),
                   n_outside_range=sum(1 for x in v if not (x['entry_inside'] and x['exit_inside'])), median_entry_bar_vol=statistics.median(x['entry_bar_vol'] for x in v))
        out.append(rec)
    return out
B3 = realism(B, lambda x: (x['epoch'], 'ALL', 'ALL'), ['epoch', 'book', 'account_type']) + realism(B, lambda x: (x['epoch'], x['book'], x['account_type']), ['epoch', 'book', 'account_type'])
write_csv(C.RES + '/B_fill_realism.csv', B3)
# sensitivity: next-bar fallback (as in evidence/scripts/validate_trades.py) for rows without an exact-minute bar
Bfb = []
for r in rows:
    if r['exit_dt'] is None or not r['has_entry_bars'] or r['cov']['bars_available_exit_day'] != 'True': continue
    eb_ = bars_for(r, r['entry_date']); xb_ = bars_for(r, r['exit_date'])
    eb = C.bar_at(eb_, r['entry_dt']) or C.first_bar_after(eb_, r['entry_dt'])[1]; xb = C.bar_at(xb_, r['exit_dt']) or C.first_bar_after(xb_, r['exit_dt'])[1]
    if eb is None or xb is None: continue
    mult = 100.0 if r['is_option'] else 1.0; sz = r['size_n']
    Bfb.append(dict(epoch=r['label'], pnl_reported=r['pnl'], pnl_mid=(C.vwap(xb) - C.vwap(eb)) * mult * sz, exact=(r['bar_entry_min'] and r['bar_exit_min'])))
print(f'B done n={len(B)} {time.time() - T0:.0f}s', flush=True)

# ======================================================================
# C. Independent reconstruction from the entry minute (0DTE option rows)
# ======================================================================
ENGINES = ['trail', 'ladder', 'bracket', 'hold']; CMODELS = ['mid', 'spread', 'adverse']
def close_t(d): return d.replace(hour=15, minute=55, second=0, microsecond=0)
def feasible(bars, idx):
    return idx is not None and bars[idx]['t'] < close_t(bars[idx]['t']) and idx + 1 < len(bars)

def run_engines(bars, idx, root):
    eb = bars[idx]; px = C.vwap(eb); out = {}
    if px <= 0: return None
    for eng in ENGINES:
        legs = exits.simulate(bars, idx, px, eng)
        if not legs: return None
        for mdl in CMODELS:
            s = costs.settle(cost_key(root), eb, px, legs, mdl)
            out[(eng, mdl)] = (s['ret'], s['dollars'])
        out[(eng, 'reason')] = legs[-1][3]; out[(eng, 'exit_t')] = legs[-1][2]
    return out, px

def mfe_mae(bars, idx, px):
    after = [b for b in bars[idx + 1:] if b['t'] <= close_t(b['t'])]
    if not after: return None, None
    return max(b['h'] for b in after) / px - 1, min(b['l'] for b in after) / px - 1

rng = random.Random(RAND_SEED)
Crows = []; Crand = []
for r in rows:
    if not (r['is_option'] and r['dte0'] and r['has_entry_bars']): continue
    bars = bars_for(r, r['entry_date'])
    idx, eb = C.first_bar_after(bars, r['entry_dt'])
    if not feasible(bars, idx): continue
    res = run_engines(bars, idx, r['root'])
    if res is None: continue
    out, px = res
    mfe, mae = mfe_mae(bars, idx, px)
    rec = dict(group=r['group'], epoch=r['label'], book=r['book'], account_type=r['account_type'], trade_id=r['trade_id'], ticker=r['ticker'], root=r['root'], side=r['side'], month=r['month'],
               data_error=r['data_err'], size=r['size_n'], entry_minute_et=r['entry_dt'].strftime('%H:%M'), entry_bar_t=eb['t'].strftime('%H:%M'), entry_vwap=px, reported_entry_premium=r['entry_px'],
               pnl_reported=r['pnl'], pnl_pct_reported=(r['exit_px'] / r['entry_px'] - 1) if r['entry_px'] else None, mfe=mfe, mae=mae)
    for eng in ENGINES:
        rec[f'{eng}_reason'] = out[(eng, 'reason')]; rec[f'{eng}_exit_t'] = out[(eng, 'exit_t')].strftime('%H:%M')
        for mdl in CMODELS:
            rec[f'{eng}_{mdl}_ret'] = out[(eng, mdl)][0]; rec[f'{eng}_{mdl}_usd'] = out[(eng, mdl)][1]
    # random-time baseline: K_RANDOM uniformly random RTH minutes 09:30-15:53 on the same contract-day (and a +-30 min time-matched variant)
    day = eb['t'].replace(hour=9, minute=30, second=0, microsecond=0)
    def draw(lo_min, hi_min):
        for _ in range(50):
            m = day + datetime.timedelta(minutes=rng.randint(lo_min, hi_min))
            j, b = C.first_bar_after(bars, m - datetime.timedelta(minutes=1))  # first bar at/after minute m
            if feasible(bars, j):
                rr = run_engines(bars, j, r['root'])
                if rr: return rr, j
        return None, None
    acc = collections.defaultdict(list); accm = collections.defaultdict(list); mfe_r = []; nrand = 0
    for k in range(K_RANDOM):
        rr, j = draw(0, 383)
        if rr is None: continue
        nrand += 1
        for eng in ENGINES:
            for mdl in CMODELS: acc[(eng, mdl)].append(rr[0][(eng, mdl)][1]); acc[(eng, mdl, 'ret')].append(rr[0][(eng, mdl)][0])
        Crand.append(dict(epoch=r['label'], book=r['book'], trade_id=r['trade_id'], draw=k, **{f'{e}_{m}_usd': rr[0][(e, m)][1] for e in ENGINES for m in CMODELS}))
    em = (eb['t'] - day).total_seconds() / 60
    for k in range(K_RANDOM):
        rr, j = draw(max(0, int(em) - 30), min(383, int(em) + 30))
        if rr is None: continue
        for eng in ENGINES:
            for mdl in CMODELS: accm[(eng, mdl)].append(rr[0][(eng, mdl)][1])
    for k in range(K_MFE):
        for _ in range(50):
            m = day + datetime.timedelta(minutes=rng.randint(0, 383))
            j, b = C.first_bar_after(bars, m - datetime.timedelta(minutes=1))
            if feasible(bars, j):
                mm, _a = mfe_mae(bars, j, C.vwap(b))
                if mm is not None: mfe_r.append(mm); break
    rec['n_random'] = nrand
    for eng in ENGINES:
        for mdl in CMODELS:
            rec[f'rand_{eng}_{mdl}_usd'] = statistics.mean(acc[(eng, mdl)]) if acc[(eng, mdl)] else None
            rec[f'rand_{eng}_{mdl}_ret'] = statistics.mean(acc[(eng, mdl, 'ret')]) if acc[(eng, mdl, 'ret')] else None
            rec[f'randtm_{eng}_{mdl}_usd'] = statistics.mean(accm[(eng, mdl)]) if accm[(eng, mdl)] else None
    rec['mfe_pctile'] = ((sum(1 for v in mfe_r if v < mfe) + 0.5 * sum(1 for v in mfe_r if v == mfe)) / len(mfe_r)) if (mfe_r and mfe is not None) else None
    rec['n_mfe_random'] = len(mfe_r)
    Crows.append(rec)
write_csv(C.RES + '/C_trades.csv', Crows)
write_csv(C.RES + '/C_random_draws.csv', Crand)
print(f'C rows={len(Crows)} {time.time() - T0:.0f}s', flush=True)

def c_table(cs, keyf, keynames):
    out = []
    for k, v in group_rows(cs, keyf).items():
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,))); rec['n'] = len(v)
        mrep = metrics([x['pnl_pct_reported'] for x in v if x['pnl_pct_reported'] is not None])
        rec['reported_mean_ret'] = round(mrep['mean'], 4); rec['reported_win_rate'] = round(mrep['win_rate'], 4)
        for eng in ENGINES:
            for mdl in CMODELS:
                m = metrics([x[f'{eng}_{mdl}_usd'] for x in v]); mr = metrics([x[f'{eng}_{mdl}_ret'] for x in v])
                rec[f'{eng}_{mdl}_mean_usd'] = round(m['mean'], 2); rec[f'{eng}_{mdl}_ci_lo'] = round(m['ci_lo'], 2); rec[f'{eng}_{mdl}_ci_hi'] = round(m['ci_hi'], 2)
                rec[f'{eng}_{mdl}_total_usd_1lot'] = round(m['total'], 2); rec[f'{eng}_{mdl}_total_usd_sized'] = round(sum(x[f'{eng}_{mdl}_usd'] * x['size'] for x in v), 2)
                rec[f'{eng}_{mdl}_win_rate'] = round(m['win_rate'], 4); rec[f'{eng}_{mdl}_pf'] = round(m['pf'], 3) if m['pf'] != float('inf') else 'inf'; rec[f'{eng}_{mdl}_mean_ret'] = round(mr['mean'], 4)
                rv = [x[f'rand_{eng}_{mdl}_usd'] for x in v if x[f'rand_{eng}_{mdl}_usd'] is not None]
                d = [x[f'{eng}_{mdl}_usd'] - x[f'rand_{eng}_{mdl}_usd'] for x in v if x[f'rand_{eng}_{mdl}_usd'] is not None]
                md_ = metrics(d); rec[f'{eng}_{mdl}_random_mean_usd'] = round(statistics.mean(rv), 2) if rv else None
                rec[f'{eng}_{mdl}_minus_random_mean'] = round(md_['mean'], 2); rec[f'{eng}_{mdl}_minus_random_ci_lo'] = round(md_['ci_lo'], 2); rec[f'{eng}_{mdl}_minus_random_ci_hi'] = round(md_['ci_hi'], 2)
                dt = [x[f'{eng}_{mdl}_usd'] - x[f'randtm_{eng}_{mdl}_usd'] for x in v if x[f'randtm_{eng}_{mdl}_usd'] is not None]
                mt = metrics(dt); rec[f'{eng}_{mdl}_minus_random_timematched_mean'] = round(mt['mean'], 2); rec[f'{eng}_{mdl}_minus_random_tm_ci_lo'] = round(mt['ci_lo'], 2); rec[f'{eng}_{mdl}_minus_random_tm_ci_hi'] = round(mt['ci_hi'], 2)
        mf = [x['mfe'] for x in v if x['mfe'] is not None]; ma = [x['mae'] for x in v if x['mae'] is not None]; pcs = [x['mfe_pctile'] for x in v if x['mfe_pctile'] is not None]
        rec['mfe_median'] = round(statistics.median(mf), 4) if mf else None; rec['mae_median'] = round(statistics.median(ma), 4) if ma else None
        rec['mfe_ge_25_share'] = round(sum(1 for x in mf if x >= 0.25) / len(mf), 4) if mf else None; rec['mae_le_m25_share'] = round(sum(1 for x in ma if x <= -0.25) / len(ma), 4) if ma else None
        rec['mfe_pctile_median'] = round(100 * statistics.median(pcs), 1) if pcs else None; rec['mfe_pctile_mean'] = round(100 * statistics.mean(pcs), 1) if pcs else None
        if pcs:
            lo, hi = boot_ci(pcs); rec['mfe_pctile_mean_ci_lo'] = round(100 * lo, 1); rec['mfe_pctile_mean_ci_hi'] = round(100 * hi, 1)
        rec['median_entry_minute_after_open'] = statistics.median((int(x['entry_bar_t'][:2]) * 60 + int(x['entry_bar_t'][3:]) - 570) for x in v)
        out.append(rec)
    return out
C1 = c_table(Crows, lambda x: (x['epoch'], 'ALL'), ['epoch', 'book']) + c_table(Crows, lambda x: (x['epoch'], x['book']), ['epoch', 'book']) + c_table(Crows, lambda x: ('ALL', 'ALL'), ['epoch', 'book'])
write_csv(C.RES + '/C_reconstruction.csv', C1)
C2 = c_table(Crows, lambda x: (x['epoch'], x['month']), ['epoch', 'month']); write_csv(C.RES + '/C_by_month.csv', C2)
C3 = c_table(Crows, lambda x: (x['epoch'], x['root']), ['epoch', 'root']); write_csv(C.RES + '/C_by_root.csv', C3)
print(f'C tables {time.time() - T0:.0f}s', flush=True)

# ======================================================================
# D. Era comparison
# ======================================================================
def reason_family(s):
    u = (s or '').upper()
    if 'DATA ERROR' in u or 'INVALID' in u: return 'data_error'
    if 'EOD' in u or 'AUTO-CLOSE' in u or 'TIME' in u or 'THETA' in u or 'EXPIR' in u or 'FORCE' in u or 'BELL' in u: return 'time/eod'
    if 'STOP' in u or 'INVALIDAT' in u or 'EMERGENCY' in u: return 'stop'
    if 'PROFIT' in u or 'TIER' in u or 'TARGET' in u or 'TAKE' in u or 'LOCK' in u or 'TRAIL' in u or 'SCALP AT' in u: return 'profit-take/trail'
    return 'other'
Drows = []
for ep in ['E1', 'E2', 'paper']:
    v = [r for r in rows if r['label'] == ep]
    if not v: continue
    opt = [r for r in v if r['is_option']]
    fam = collections.Counter(reason_family(r['exit_reason']) for r in v)
    bb = [x for x in B if x['epoch'] == ep]
    rec = dict(epoch=ep, n=len(v), n_swing_acct=sum(1 for r in v if r['account_type'] == 'SWING'), share_swing_acct=round(sum(1 for r in v if r['account_type'] == 'SWING') / len(v), 4),
               n_shares=sum(1 for r in v if r['is_shares']), share_shares=round(sum(1 for r in v if r['is_shares']) / len(v), 4), n_0dte=sum(1 for r in v if r['dte0']),
               n_multi_day=sum(1 for r in v if r['exit_date'] and r['exit_date'] > r['entry_date']),
               hold_median_min=round(statistics.median([r['hold'] for r in v if r['hold'] is not None]), 1), hold_mean_min=round(statistics.mean([r['hold'] for r in v if r['hold'] is not None]), 1),
               size_median=statistics.median([r['size_n'] for r in v]), size_mean=round(statistics.mean([r['size_n'] for r in v]), 2), size_max=max(r['size_n'] for r in v),
               entry_premium_median=round(statistics.median([r['entry_px'] for r in opt if r['entry_px']]), 3), entry_premium_mean=round(statistics.mean([r['entry_px'] for r in opt if r['entry_px']]), 3),
               notional_median=round(statistics.median([r['entry_px'] * r['size_n'] * (100 if r['is_option'] else 1) for r in v if r['entry_px']]), 0),
               trades_per_day_mean=round(len(v) / len(set(r['entry_date'] for r in v)), 2), n_days=len(set(r['entry_date'] for r in v)),
               sum_pnl_reported=round(sum(r['pnl'] for r in v), 2), win_rate=round(sum(1 for r in v if r['pnl'] > 0) / len(v), 4),
               n_data_error=sum(1 for r in v if r['data_err']), sum_pnl_data_error=round(sum(r['pnl'] for r in v if r['data_err']), 2),
               n_mismatch=sum(1 for r in v if r['mismatch']), sum_pnl_mismatch=round(sum(r['pnl'] for r in v if r['mismatch']), 2),
               n_with_both_bars=len(bb), sum_reported_rows_with_bars=round(sum(x['pnl_reported'] for x in bb), 2), sum_reported_rows_without_bars=round(sum(r['pnl'] for r in v) - sum(x['pnl_reported'] for x in bb), 2),
               sum_mid=round(sum(x['pnl_mid'] for x in bb), 2), sum_spread=round(sum(x['pnl_spread'] for x in bb), 2), sum_adverse=round(sum(x['pnl_adverse'] for x in bb), 2),
               n_outside_bar_range=sum(1 for x in bb if not (x['entry_inside'] and x['exit_inside'])), sum_reported_outside_bar_range=round(sum(x['pnl_reported'] for x in bb if not (x['entry_inside'] and x['exit_inside'])), 2),
               sum_reported_outside_or_dataerr=round(sum(x['pnl_reported'] for x in bb if (not (x['entry_inside'] and x['exit_inside'])) or x['data_error']), 2),
               n_entry_outside=sum(1 for x in bb if not x['entry_inside']), n_exit_outside=sum(1 for x in bb if not x['exit_inside']))
    for f_ in ['profit-take/trail', 'stop', 'time/eod', 'data_error', 'other']: rec[f'exit_{f_}_share'] = round(fam[f_] / len(v), 4)
    Drows.append(rec)
write_csv(C.RES + '/D_era_comparison.csv', Drows)
# D: exit-reason top strings per epoch
Dx = []
for ep in ['E1', 'E2', 'paper']:
    cnt = collections.Counter(reason_family(r['exit_reason']) + ' | ' + (r['exit_reason'] or '')[:40] for r in rows if r['label'] == ep)
    for k, n in cnt.most_common(12): Dx.append(dict(epoch=ep, exit_reason=k, n=n))
write_csv(C.RES + '/D_exit_reasons_top.csv', Dx)

# ======================================================================
# E. Sanity / leakage checks
# ======================================================================
E = []
led = [r for r in rows if r['group'] == 'ledger']
E.append(dict(check='entry_before_exit_violations', value=sum(1 for r in rows if r['exit_dt'] and r['exit_dt'] <= r['entry_dt']), note='rows with exit <= entry (all groups)'))
E.append(dict(check='rows_without_exit_time', value=sum(1 for r in rows if r['exit_dt'] is None), note='open positions in the pull; reported pnl 0; excluded from B'))
late = [r for r in rows if r['exit_dt'] and (r['exit_dt'].hour, r['exit_dt'].minute) >= (16, 0)]
E.append(dict(check='exit_at_or_after_1600_ET', value=len(late), note='; '.join(f"{r['label']}/{r['book']}/{r['ticker']}/{r['exit_dt'].strftime('%Y-%m-%d %H:%M')}/pnl {r['pnl']:.0f}" for r in late)))
early = [r for r in rows if (r['entry_dt'].hour, r['entry_dt'].minute) < (9, 30)]
E.append(dict(check='entry_before_0930_ET', value=len(early), note='; '.join(f"{r['label']}/{r['ticker']}/{r['entry_dt'].strftime('%Y-%m-%d %H:%M')}" for r in early)))
E.append(dict(check='exit_after_1555_ET_0DTE', value=sum(1 for r in rows if r['dte0'] and r['exit_dt'] and (r['exit_dt'].hour, r['exit_dt'].minute) > (15, 55)), note='0DTE options closed after 15:55 (paper lane hard close)'))
zv = [r for r in rows if r['bar_entry_min'] and r['cov']['entry_minute_vol'] not in ('', None) and int(float(r['cov']['entry_minute_vol'])) == 0]
E.append(dict(check='entry_minute_bar_zero_volume', value=len(zv), note='bar exists at the entry minute but UW volume fields sum to 0'))
E.append(dict(check='entry_minute_no_bar_(no_prints)', value=sum(1 for r in rows if r['has_entry_bars'] and not r['bar_entry_min']), note='entry-day bars exist but no bar printed in the entry minute'))
E.append(dict(check='duplicate_trade_ids', value=len(rows) - len(set(r['trade_id'] for r in rows)), note=''))
dupk = collections.Counter((r['cid'] or r['ticker'], r['entry_dt'].strftime('%Y-%m-%d %H:%M'), r['side']) for r in rows)
E.append(dict(check='same_contract_same_entry_minute_pairs', value=sum(n - 1 for n in dupk.values() if n > 1), note='distinct ids sharing contract+entry minute (scale-ins / duplicates)'))
E.append(dict(check='pnl_mismatch_rows', value=sum(1 for r in rows if r['mismatch']), note=f"reported {sum(r['pnl'] for r in rows if r['mismatch']):.0f} vs recomputed {sum(float(r['pnl_recomputed']) for r in rows if r['mismatch']):.0f}"))
E.append(dict(check='data_error_rows', value=sum(1 for r in rows if r['data_err']), note=f"reported pnl {sum(r['pnl'] for r in rows if r['data_err']):.0f}"))
for ep in ['E1', 'E2', 'paper']:
    v = [r for r in rows if r['label'] == ep]; bb = [x for x in B if x['epoch'] == ep]
    E.append(dict(check=f'{ep}_reported_total_all', value=round(sum(r['pnl'] for r in v), 2), note=f'n={len(v)}'))
    E.append(dict(check=f'{ep}_reported_total_excl_mismatch', value=round(sum(r['pnl'] for r in v if not r['mismatch']), 2), note=f"n={sum(1 for r in v if not r['mismatch'])}"))
    E.append(dict(check=f'{ep}_reported_total_excl_dataerr', value=round(sum(r['pnl'] for r in v if not r['data_err']), 2), note=f"n={sum(1 for r in v if not r['data_err'])}"))
    E.append(dict(check=f'{ep}_reported_total_excl_both', value=round(sum(r['pnl'] for r in v if not r['data_err'] and not r['mismatch']), 2), note=f"n={sum(1 for r in v if not r['data_err'] and not r['mismatch'])}"))
    E.append(dict(check=f'{ep}_B_mid_total_excl_mismatch', value=round(sum(x['pnl_mid'] for x in bb if not x['pnl_mismatch']), 2), note=f"n={sum(1 for x in bb if not x['pnl_mismatch'])} (all rows: {sum(x['pnl_mid'] for x in bb):.0f}, n={len(bb)})"))
    E.append(dict(check=f'{ep}_B_spread_total_excl_mismatch', value=round(sum(x['pnl_spread'] for x in bb if not x['pnl_mismatch']), 2), note=f"all rows: {sum(x['pnl_spread'] for x in bb):.0f}"))
    E.append(dict(check=f'{ep}_B_recomputed_vs_reported_excl_mismatch', value=round(sum(x['pnl_recomputed'] - x['pnl_reported'] for x in bb if not x['pnl_mismatch']), 2), note='should be ~0'))
write_csv(C.RES + '/E_sanity.csv', E)
print(f'D/E done {time.time() - T0:.0f}s', flush=True)

# ======================================================================
# RESULTS.md (tables only; narrative added by hand afterwards)
# ======================================================================
H('# GeorgeFi full-history reconstruction vs Unusual Whales 1-minute bars: results')
MD.append(f'Generated {datetime.datetime.now(C.ET).strftime("%Y-%m-%d %H:%M ET")} by code/reconstruct.py. Labels: **Reported by GeorgeFi** = the operator\'s own ledger numbers; **Simulated fills (ours)** = GeorgeFi\'s entry/exit minutes re-priced on UW bars; **Independent reconstruction (ours)** = only the entry minute is taken from the ledger, exits are mechanical. Bootstrap CIs: {BOOT_N} resamples, seed {BOOT_SEED}; random baselines seed {RAND_SEED}. E1 = Epoch 1 main book (2026-01-20 to 02-27); E2 = Epoch 2 (main book + trade_now_v1, singles_today_v1, spx_plan_v1); paper = SPX paper book (spx_gex_engine).')
MD.append('')
H('## 0. Coverage')
MD.append(open(C.RES + '/bar_coverage_summary.md').read().split('\n', 2)[2])
H('## A. Reported by GeorgeFi (operator\'s own numbers, not independent)')
T(['| epoch | book | account | n | sum P&L | win rate | mean/trade | 95 % CI of mean | max DD | PF | median hold (min) | median size | n data-error | n P&L-mismatch | sum excl. both (n) |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {a['epoch']} | {a['book']} | {a['account_type']} | {a['n']} | {f0(a['sum_pnl_reported'])} | {pct(a['win_rate'])} | {f1(a['mean'])} | [{f1(a['ci_lo'])}, {f1(a['ci_hi'])}] | {f0(a['max_drawdown'])} | {a['pf']} | {a['median_hold_min']} | {a['median_size']} | {a['n_data_error']} | {a['n_pnl_mismatch']} | {f0(a['sum_pnl_excl_dataerr_mismatch'])} ({a['n_excl']}) |" for a in A1e + A1b + A1])
H('### A by month (Reported by GeorgeFi)')
T(['| epoch | month | n | sum P&L | win rate | mean | 95 % CI | max DD |', '|---|---|---|---|---|---|---|---|'] + [f"| {a['epoch']} | {a['month']} | {a['n']} | {f0(a['sum_pnl_reported'])} | {pct(a['win_rate'])} | {f1(a['mean'])} | [{f1(a['ci_lo'])}, {f1(a['ci_hi'])}] | {f0(a['max_drawdown'])} |" for a in A2])
H('### A by ticker root, n >= 10 (Reported by GeorgeFi)')
T(['| epoch | root | n | sum P&L | win rate | mean | 95 % CI |', '|---|---|---|---|---|---|---|'] + [f"| {a['epoch']} | {a['root']} | {a['n']} | {f0(a['sum_pnl_reported'])} | {pct(a['win_rate'])} | {f1(a['mean'])} | [{f1(a['ci_lo'])}, {f1(a['ci_hi'])}] |" for a in A3 if a['n'] >= 10])
H('## B. Simulated fills at the reported times (ours; rows with a UW bar in both the entry and the exit minute)')
MD.append('Entry at the entry-minute bar VWAP, exit at the exit-minute bar VWAP, reported size. `mid` = no cost; `spread` = half-spread per side (1 % SPY/QQQ, 2 % IWM, 1.5 % SPXW/NDXP/RUTW, 2 % single names) + $0.70/contract/side; `adverse` = buy entry-bar high, sell exit-bar low + fees. Shares: ×1, no fees, no spread (reported for completeness; $-magnitude is negligible). "reported" is GeorgeFi\'s P&L on the same rows.')
MD.append('')
T(['| epoch | book | account | n | reported total | mid total | spread total | adverse total | mid mean [CI] | spread mean [CI] | adverse mean [CI] | WR rep/mid/spread/adv | PF rep/mid/spread/adv | reported − mid mean [CI] |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {b['epoch']} | {b['book']} | {b['account_type']} | {b['n']} | {f0(b['reported_total'])} | {f0(b['mid_total'])} | {f0(b['spread_total'])} | {f0(b['adverse_total'])} | {f1(b['mid_mean'])} [{f1(b['mid_ci_lo'])}, {f1(b['mid_ci_hi'])}] | {f1(b['spread_mean'])} [{f1(b['spread_ci_lo'])}, {f1(b['spread_ci_hi'])}] | {f1(b['adverse_mean'])} [{f1(b['adverse_ci_lo'])}, {f1(b['adverse_ci_hi'])}] | {pct(b['reported_win_rate'])}/{pct(b['mid_win_rate'])}/{pct(b['spread_win_rate'])}/{pct(b['adverse_win_rate'])} | {b['reported_pf']}/{b['mid_pf']}/{b['spread_pf']}/{b['adverse_pf']} | {f1(b['diff_rep_minus_mid_mean'])} [{f1(b['diff_ci_lo'])}, {f1(b['diff_ci_hi'])}] |" for b in B1])
H('### B by month (Simulated fills, ours)')
T(['| epoch | month | n | reported | mid | spread | adverse | mid mean [CI] | spread mean [CI] |', '|---|---|---|---|---|---|---|---|---|'] + [f"| {b['epoch']} | {b['month']} | {b['n']} | {f0(b['reported_total'])} | {f0(b['mid_total'])} | {f0(b['spread_total'])} | {f0(b['adverse_total'])} | {f1(b['mid_mean'])} [{f1(b['mid_ci_lo'])}, {f1(b['mid_ci_hi'])}] | {f1(b['spread_mean'])} [{f1(b['spread_ci_lo'])}, {f1(b['spread_ci_hi'])}] |" for b in B2])
H('### B fill realism (reported premiums vs the traded range of the same minute)')
T(['| epoch | book | account | n | entry inside bar | exit inside bar | both inside | median entry pos (0=low,1=high) | median exit pos | entries below bar VWAP | exits above bar VWAP | n outside | reported P&L of outside rows | median entry-bar volume |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {b['epoch']} | {b['book']} | {b['account_type']} | {b['n']} | {pct(b['entry_inside_share'])} | {pct(b['exit_inside_share'])} | {pct(b['both_inside_share'])} | {b['median_entry_pos_in_bar']} | {b['median_exit_pos_in_bar']} | {pct(b['entry_below_vwap_share'])} | {pct(b['exit_above_vwap_share'])} | {b['n_outside_range']} | {f0(b['sum_reported_outside_range'])} | {b['median_entry_bar_vol']} |" for b in B3])
fb = collections.defaultdict(list)
for x in Bfb: fb[x['epoch']].append(x)
T(['Sensitivity (next-bar fallback as in evidence/scripts/validate_trades.py, i.e. the first bar at/after the entry or exit minute when the exact minute has no print):', '', '| epoch | n (fallback) | n exact | reported total | mid total | mid total exact-only |', '|---|---|---|---|---|---|'] +
  [f"| {ep} | {len(v)} | {sum(1 for x in v if x['exact'])} | {f0(sum(x['pnl_reported'] for x in v))} | {f0(sum(x['pnl_mid'] for x in v))} | {f0(sum(x['pnl_mid'] for x in v if x['exact']))} |" for ep, v in sorted(fb.items())])
H('## C. Independent reconstruction from the reported entry minute (ours; 0DTE option rows with bars)')
MD.append(f'Entry = VWAP of the first bar strictly after the entry minute; exits by backtest/exits.py engines (trail: stop −25 %, breakeven arm +6 %, guardian +15 %/35 % give-back, 30-min time stop, 15:55 close; ladder adds T1 +25 % half / T2 +45 %; bracket ±25 %; hold = 15:55 close), settled with backtest/costs.py (1 contract). Random baseline: for each trade, {K_RANDOM} uniformly random RTH entry minutes (09:30–15:53) on the same contract-day with the same engine/costs; "− random" = paired difference (strategy − mean of its random draws), bootstrap CI; "time-matched" = random minutes within ±30 min of the actual entry. $ figures are per contract (1 lot); "sized" multiplies by the reported size.')
MD.append('')
for eng in ENGINES:
    T([f'### C engine `{eng}` (Independent reconstruction, ours)', '', '| epoch | book | n | reported mean ret | model | mean $/contract [CI] | total $ 1-lot | total $ sized | WR | PF | mean ret | random mean $ | strategy − random [CI] | − random time-matched [CI] |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
      [f"| {c['epoch']} | {c['book']} | {c['n']} | {pct(c['reported_mean_ret'])} | {mdl} | {f1(c[f'{eng}_{mdl}_mean_usd'])} [{f1(c[f'{eng}_{mdl}_ci_lo'])}, {f1(c[f'{eng}_{mdl}_ci_hi'])}] | {f0(c[f'{eng}_{mdl}_total_usd_1lot'])} | {f0(c[f'{eng}_{mdl}_total_usd_sized'])} | {pct(c[f'{eng}_{mdl}_win_rate'])} | {c[f'{eng}_{mdl}_pf']} | {pct(c[f'{eng}_{mdl}_mean_ret'])} | {f1(c[f'{eng}_{mdl}_random_mean_usd'])} | {f1(c[f'{eng}_{mdl}_minus_random_mean'])} [{f1(c[f'{eng}_{mdl}_minus_random_ci_lo'])}, {f1(c[f'{eng}_{mdl}_minus_random_ci_hi'])}] | {f1(c[f'{eng}_{mdl}_minus_random_timematched_mean'])} [{f1(c[f'{eng}_{mdl}_minus_random_tm_ci_lo'])}, {f1(c[f'{eng}_{mdl}_minus_random_tm_ci_hi'])}] |" for c in C1 for mdl in CMODELS])
H('### C MFE / MAE and entry-timing percentile (ours)')
T(['| epoch | book | n | median MFE | median MAE | MFE ≥ +25 % | MAE ≤ −25 % | MFE percentile vs 50 random minutes: median | mean [CI] | median entry (min after open) |', '|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {c['epoch']} | {c['book']} | {c['n']} | {pct(c['mfe_median'])} | {pct(c['mae_median'])} | {pct(c['mfe_ge_25_share'])} | {pct(c['mae_le_m25_share'])} | {c['mfe_pctile_median']} | {c['mfe_pctile_mean']} [{c.get('mfe_pctile_mean_ci_lo')}, {c.get('mfe_pctile_mean_ci_hi')}] | {c['median_entry_minute_after_open']} |" for c in C1])
H('### C by month, trail engine (Independent reconstruction, ours)')
T(['| epoch | month | n | trail mid mean [CI] | trail spread mean [CI] | − random (mid) [CI] | MFE pctile median |', '|---|---|---|---|---|---|---|'] +
  [f"| {c['epoch']} | {c['month']} | {c['n']} | {f1(c['trail_mid_mean_usd'])} [{f1(c['trail_mid_ci_lo'])}, {f1(c['trail_mid_ci_hi'])}] | {f1(c['trail_spread_mean_usd'])} [{f1(c['trail_spread_ci_lo'])}, {f1(c['trail_spread_ci_hi'])}] | {f1(c['trail_mid_minus_random_mean'])} [{f1(c['trail_mid_minus_random_ci_lo'])}, {f1(c['trail_mid_minus_random_ci_hi'])}] | {c['mfe_pctile_median']} |" for c in C2])
H('## D. Era comparison (Epoch 1 vs Epoch 2 vs paper)')
keys = [k for k in Drows[0].keys() if k != 'epoch']
T(['| metric | ' + ' | '.join(d['epoch'] for d in Drows) + ' |', '|---|' + '---|' * len(Drows)] + [f"| {k} | " + ' | '.join(str(d.get(k, '')) for d in Drows) + ' |' for k in keys])
H('### D top exit reasons (families | first 40 chars)')
T(['| epoch | exit reason | n |', '|---|---|---|'] + [f"| {d['epoch']} | {d['exit_reason']} | {d['n']} |" for d in Dx])
H('## E. Sanity / leakage checks')
T(['| check | value | note |', '|---|---|---|'] + [f"| {e['check']} | {e['value']} | {e['note']} |" for e in E])
open(C.RES + '/RESULTS.md', 'w').write('\n'.join(MD) + '\n')
json.dump(dict(runtime_s=round(time.time() - T0), n_rows=len(rows), n_B=len(B), n_C=len(Crows), stats=C.data.STATS), open(C.RES + '/run_info.json', 'w'))
print(f'ALL DONE {time.time() - T0:.0f}s  rows={len(rows)} B={len(B)} C={len(Crows)}')
