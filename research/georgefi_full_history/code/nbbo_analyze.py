"""Step 2 of the NBBO study: classify every reported fill against the ThetaData 1-second NBBO at the reported second and
reprice the ledger at executable prices (entry at ASK, exit at BID, $0.70/contract/side). Reads only the cache written by
nbbo_fetch.py (no network). Run from this folder:
  SP="$SP" python3 -I nbbo_analyze.py
Outputs: results/F_nbbo_trades.csv (one row per ledger/paper row), F_nbbo_coverage.csv, F_nbbo_fill_class.csv,
F_nbbo_repricing.csv, F_nbbo_spreads.csv, F_nbbo_repeats.csv, F_nbbo_run_info.json and results/RESULTS_NBBO.md.
"""
import sys, os, csv, json, math, time, datetime, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import nbbo_common as N
import common as C

T0 = time.time()
BOOT_N, SEED = 1000, 7
TOL = 0.004          # |reported - bid| or |reported - ask| within $0.004 counts as "at" (premiums are cents or half-cents)
MID_TOL = 0.01       # |reported - mid| <= $0.01 counts as "at mid"
ASSUMED_HS = {'SPY': 0.01, 'QQQ': 0.01, 'IWM': 0.02}   # backtest/costs.py half-spread assumptions (% of price); index roots 1.5 %, single names 2 %
def assumed_hs(root, kind):
    if kind == 'stk': return float('nan')
    if root in C.INDEX_ROOTS: return 0.015
    return ASSUMED_HS.get(root, 0.02)
CLASSES = ['below_bid', 'at_bid', 'inside', 'at_mid', 'at_ask', 'above_ask']
RES = C.RES
ONE_S = datetime.timedelta(seconds=1)

# ---------------------------------------------------------------- helpers
def isnum(x): return x is not None and not (isinstance(x, float) and math.isnan(x))
def valid_quote(q):
    if q is None: return False
    b, a = q[0], q[1]
    return isnum(b) and isnum(a) and a > 0 and a >= b and b >= 0

def classify(p, q):
    b, a = q[0], q[1]; mid = (a + b) / 2
    if p < b - TOL: return 'below_bid'
    if abs(p - b) <= TOL: return 'at_bid'
    if p > a + TOL: return 'above_ask'
    if abs(p - a) <= TOL: return 'at_ask'
    if abs(p - mid) <= MID_TOL: return 'at_mid'
    return 'inside'

def position(p, q):
    b, a = q[0], q[1]
    return (p - b) / (a - b) if a > b else float('nan')

def in_rth(t): return datetime.time(9, 30) <= t.timetz().replace(tzinfo=None) < datetime.time(16, 0)

def boot_ci(vals, seed=SEED, n=BOOT_N):
    v = np.asarray(vals, dtype=float)
    if len(v) == 0: return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(v), size=(n, len(v)))
    m = v[idx].mean(axis=1); return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def boot_ci_cluster(vals, clusters, seed=SEED, n=BOOT_N):
    """Cluster bootstrap of the per-trade mean (resample clusters = ET entry days with replacement)."""
    sums = collections.defaultdict(float); cnts = collections.defaultdict(int)
    for v, c in zip(vals, clusters): sums[c] += float(v); cnts[c] += 1
    keys = list(sums)
    if not keys: return (float('nan'), float('nan'), 0)
    S = np.array([sums[k] for k in keys]); K = np.array([cnts[k] for k in keys], dtype=float)
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(keys), size=(n, len(keys)))
    m = S[idx].sum(axis=1) / K[idx].sum(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), len(keys)

def metrics(vals, days):
    v = [float(x) for x in vals]
    if not v: return dict(n=0, total=float('nan'), mean=float('nan'), ci_lo=float('nan'), ci_hi=float('nan'), dci_lo=float('nan'), dci_hi=float('nan'), n_days=0, win_rate=float('nan'), pf=float('nan'))
    w = sum(x for x in v if x > 0); l = -sum(x for x in v if x < 0)
    lo, hi = boot_ci(v); dlo, dhi, nd = boot_ci_cluster(v, days)
    return dict(n=len(v), total=sum(v), mean=statistics.mean(v), ci_lo=lo, ci_hi=hi, dci_lo=dlo, dci_hi=dhi, n_days=nd,
                win_rate=sum(1 for x in v if x > 0) / len(v), pf=(w / l) if l > 0 else float('inf'))

def f0(x): return 'n/a' if not isnum(x) else (f'{x:,.0f}' if abs(x) >= 100 else f'{x:,.1f}')
def f1(x): return 'n/a' if not isnum(x) else f'{x:,.1f}'
def f2(x): return 'n/a' if not isnum(x) else ('inf' if x == float('inf') else f'{x:,.2f}')
def f3(x): return 'n/a' if not isnum(x) else f'{x:,.3f}'
def pct(x): return 'n/a' if not isnum(x) else f'{100 * x:.1f} %'
def pf_s(x): return 'n/a' if not isnum(x) else ('inf' if x == float('inf') else f'{x:.2f}')
def r2(x): return round(x, 2) if isnum(x) else ''
def r4(x): return round(x, 4) if isnum(x) else ''

def write_csv(path, rows):
    if not rows: open(path, 'w').write(''); return
    cols = []
    for r in rows:
        for k in r:
            if k not in cols: cols.append(k)
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

def group(rs, keyf):
    g = collections.OrderedDict()
    for r in rs: g.setdefault(keyf(r), []).append(r)
    return g

# ---------------------------------------------------------------- load
rows = N.load_rows()
merged = N.build_requests(rows)
book = N.QuoteBook(merged)
Btr = {r['trade_id']: r for r in csv.DictReader(open(RES + '/B_trades.csv'))}
n_req = sum(len(v) for v in merged.values())
st_counts = collections.Counter('not_fetched' if st is None else ('ok' if st.get('ok') else ('nodata' if st.get('nodata') else 'error')) for st in book.status.values())
print(f'rows={len(rows)} contract-days={len(merged)} requests={n_req} status={dict(st_counts)} load {time.time() - T0:.0f}s', flush=True)

# ---------------------------------------------------------------- per-row evaluation
def side_eval(r, which):
    """Quote status and fields for the reported entry or exit of row r."""
    t = r['entry_dt'] if which == 'entry' else r['exit_dt']
    p = r['entry_px'] if which == 'entry' else r['exit_px']
    out = dict(status='', rth=None, bid0=None, ask0=None, bsz0=None, asz0=None, bid1=None, ask1=None, cls0='', pos0=float('nan'), cls1='', pos1=float('nan'),
               hs0=float('nan'), hs0_pct=float('nan'), mid0=float('nan'), mid1=float('nan'), valid0=False, valid1=False)
    if r['kind'] is None: out['status'] = 'no_instrument'; return out
    if t is None: out['status'] = 'no_exit'; return out
    out['rth'] = in_rth(t)
    ck = N.contract_key(r, t.strftime('%Y-%m-%d')); st = book.status_for(ck, t)
    if st is None: out['status'] = 'not_fetched'; return out
    if st.get('nodata'): out['status'] = 'nodata'; return out
    if not st.get('ok'): out['status'] = 'error'; return out
    s0 = N.floor_s(t); q0 = book.at(ck, s0); q1 = book.at(ck, s0 + ONE_S)
    if q0 is None: out['status'] = 'missing_second'; return out
    out['bid0'], out['ask0'], out['bsz0'], out['asz0'] = q0[0], q0[1], q0[2], q0[3]
    if q1 is not None: out['bid1'], out['ask1'] = q1[0], q1[1]
    if not valid_quote(q0): out['status'] = 'no_quote'; return out
    out['status'] = 'ok'; out['valid0'] = True
    out['cls0'] = classify(p, q0); out['pos0'] = position(p, q0); out['mid0'] = (q0[0] + q0[1]) / 2
    out['hs0'] = (q0[1] - q0[0]) / 2; out['hs0_pct'] = out['hs0'] / out['mid0'] if out['mid0'] > 0 else float('nan')
    if valid_quote(q1):
        out['valid1'] = True; out['cls1'] = classify(p, q1); out['pos1'] = position(p, q1); out['mid1'] = (q1[0] + q1[1]) / 2
    return out

F = []
for r in rows:
    en = side_eval(r, 'entry'); ex = side_eval(r, 'exit')
    mult = 100.0 if r['kind'] == 'opt' else 1.0; sz = r['size_n']; fee = N.FEES if r['kind'] == 'opt' else 0.0
    both0 = en['valid0'] and ex['valid0']; both1 = en['valid1'] and ex['valid1']
    exec0 = (ex['bid0'] - en['ask0']) * mult * sz - 2 * fee * sz if both0 else float('nan')
    exec1 = (ex['bid1'] - en['ask1']) * mult * sz - 2 * fee * sz if both1 else float('nan')
    nmid0 = (ex['mid0'] - en['mid0']) * mult * sz if both0 else float('nan')
    rec = dict(group=r['group'], epoch=r['label'], book=r['book'], account_type=r['account_type'], trade_id=r['trade_id'], ticker=r['ticker'], root=r['t_root'], kind=r['kind'] or '',
               side=r['side'], month=r['month'], day=r['day'], is_0dte=r['dte0'], data_error=r['data_err'], pnl_mismatch=r['mismatch'], size=sz, cluster=r['cluster'],
               entry_et=r['entry_dt'].isoformat(), exit_et=r['exit_dt'].isoformat() if r['exit_dt'] else '', entry_premium=r['entry_px'], exit_premium=r['exit_px'], pnl_reported=r['pnl'],
               entry_status=en['status'], exit_status=ex['status'], entry_rth=en['rth'], exit_rth=ex['rth'],
               entry_bid=en['bid0'], entry_ask=en['ask0'], entry_bid_size=en['bsz0'], entry_ask_size=en['asz0'], entry_bid_1s=en['bid1'], entry_ask_1s=en['ask1'],
               exit_bid=ex['bid0'], exit_ask=ex['ask0'], exit_bid_size=ex['bsz0'], exit_ask_size=ex['asz0'], exit_bid_1s=ex['bid1'], exit_ask_1s=ex['ask1'],
               entry_class=en['cls0'], entry_pos=r4(en['pos0']), entry_class_1s=en['cls1'], entry_pos_1s=r4(en['pos1']),
               exit_class=ex['cls0'], exit_pos=r4(ex['pos0']), exit_class_1s=ex['cls1'], exit_pos_1s=r4(ex['pos1']),
               entry_half_spread=r4(en['hs0']), entry_half_spread_pct=r4(en['hs0_pct']), exit_half_spread=r4(ex['hs0']), exit_half_spread_pct=r4(ex['hs0_pct']),
               both_ok=both0, both_ok_1s=both1, pnl_exec_nbbo=r2(exec0), pnl_exec_nbbo_1s=r2(exec1), pnl_nbbo_mid=r2(nmid0),
               diff_reported_minus_exec=r2(r['pnl'] - exec0) if both0 else '', diff_reported_minus_nbbo_mid=r2(r['pnl'] - nmid0) if both0 else '',
               entry_better_than_market=en['cls0'] in ('below_bid', 'at_bid'), exit_better_than_market=ex['cls0'] in ('at_ask', 'above_ask'),
               entry_better_1s=en['cls1'] in ('below_bid', 'at_bid'), exit_better_1s=ex['cls1'] in ('at_ask', 'above_ask'),
               in_B_sample=r['trade_id'] in Btr, pnl_bar_mid_B=float(Btr[r['trade_id']]['pnl_mid']) if r['trade_id'] in Btr else '',
               pnl_bar_spread_B=float(Btr[r['trade_id']]['pnl_spread']) if r['trade_id'] in Btr else '')
    rec['_en'] = en; rec['_ex'] = ex; rec['_exec0'] = exec0; rec['_exec1'] = exec1; rec['_nmid0'] = nmid0; rec['_r'] = r
    F.append(rec)
write_csv(RES + '/F_nbbo_trades.csv', [{k: v for k, v in x.items() if not k.startswith('_')} for x in F])
print(f'per-row done {time.time() - T0:.0f}s', flush=True)

# ---------------------------------------------------------------- 1. coverage
STATUSES = ['ok', 'no_quote', 'nodata', 'error', 'missing_second', 'not_fetched', 'no_exit', 'no_instrument']
def coverage(fs, keyf, keynames):
    out = []
    for k, v in group(fs, keyf).items():
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,)))
        rec.update(n=len(v), n_with_instrument=sum(1 for x in v if x['kind']), n_entry_ok=sum(1 for x in v if x['entry_status'] == 'ok'), n_exit_ok=sum(1 for x in v if x['exit_status'] == 'ok'),
                   n_both_ok=sum(1 for x in v if x['both_ok']), n_both_ok_1s=sum(1 for x in v if x['both_ok_1s']),
                   n_entry_outside_rth=sum(1 for x in v if x['entry_rth'] is False), n_exit_outside_rth=sum(1 for x in v if x['exit_rth'] is False),
                   reported_pnl_all=round(sum(x['pnl_reported'] for x in v), 2), reported_pnl_both_ok=round(sum(x['pnl_reported'] for x in v if x['both_ok']), 2))
        for s in STATUSES: rec[f'entry_{s}'] = sum(1 for x in v if x['entry_status'] == s)
        for s in STATUSES: rec[f'exit_{s}'] = sum(1 for x in v if x['exit_status'] == s)
        out.append(rec)
    return out
COV = coverage(F, lambda x: (x['epoch'], 'ALL', 'ALL'), ['epoch', 'book', 'account_type']) + coverage(F, lambda x: (x['epoch'], x['book'], x['account_type']), ['epoch', 'book', 'account_type'])
COVr = coverage(F, lambda x: (x['epoch'], x['root']), ['epoch', 'root'])
write_csv(RES + '/F_nbbo_coverage.csv', COV + [dict(epoch=c['epoch'], book='root:' + c['root'], account_type='ALL', **{k: v for k, v in c.items() if k not in ('epoch', 'root')}) for c in COVr])

# ---------------------------------------------------------------- 2. fill classification
def fill_class(fs, keyf, keynames):
    out = []
    for k, v in group(fs, keyf).items():
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,)))
        en = [x for x in v if x['entry_status'] == 'ok']; ex = [x for x in v if x['exit_status'] == 'ok']
        en1 = [x for x in v if x['_en']['valid1']]; ex1 = [x for x in v if x['_ex']['valid1']]
        rec['n_entry'] = len(en); rec['n_exit'] = len(ex)
        for c in CLASSES: rec[f'entry_{c}'] = round(sum(1 for x in en if x['entry_class'] == c) / len(en), 4) if en else ''
        for c in CLASSES: rec[f'exit_{c}'] = round(sum(1 for x in ex if x['exit_class'] == c) / len(ex), 4) if ex else ''
        rec['entry_at_or_below_bid'] = round(sum(1 for x in en if x['entry_better_than_market']) / len(en), 4) if en else ''
        rec['exit_at_or_above_ask'] = round(sum(1 for x in ex if x['exit_better_than_market']) / len(ex), 4) if ex else ''
        rec['entry_at_or_below_bid_1s'] = round(sum(1 for x in en1 if x['entry_better_1s']) / len(en1), 4) if en1 else ''
        rec['exit_at_or_above_ask_1s'] = round(sum(1 for x in ex1 if x['exit_better_1s']) / len(ex1), 4) if ex1 else ''
        rec['entry_within_nbbo'] = round(sum(1 for x in en if x['entry_class'] in ('at_bid', 'inside', 'at_mid', 'at_ask')) / len(en), 4) if en else ''
        rec['exit_within_nbbo'] = round(sum(1 for x in ex if x['exit_class'] in ('at_bid', 'inside', 'at_mid', 'at_ask')) / len(ex), 4) if ex else ''
        pe = [x['_en']['pos0'] for x in en if isnum(x['_en']['pos0'])]; px = [x['_ex']['pos0'] for x in ex if isnum(x['_ex']['pos0'])]
        rec['entry_pos_median'] = round(statistics.median(pe), 3) if pe else ''; rec['entry_pos_mean'] = round(statistics.mean(pe), 3) if pe else ''
        rec['exit_pos_median'] = round(statistics.median(px), 3) if px else ''; rec['exit_pos_mean'] = round(statistics.mean(px), 3) if px else ''
        both = [x for x in v if x['both_ok']]
        rec['n_both'] = len(both)
        rec['either_side_better'] = round(sum(1 for x in both if x['entry_better_than_market'] or x['exit_better_than_market']) / len(both), 4) if both else ''
        rec['both_sides_within_nbbo'] = round(sum(1 for x in both if x['entry_class'] in ('at_bid', 'inside', 'at_mid', 'at_ask') and x['exit_class'] in ('at_bid', 'inside', 'at_mid', 'at_ask')) / len(both), 4) if both else ''
        rec['reported_pnl_rows_either_better'] = round(sum(x['pnl_reported'] for x in both if x['entry_better_than_market'] or x['exit_better_than_market']), 2)
        rec['reported_pnl_rows_both_within'] = round(sum(x['pnl_reported'] for x in both if not (x['entry_better_than_market'] or x['exit_better_than_market'])), 2)
        rec['median_entry_bid_size'] = statistics.median([x['entry_bid_size'] for x in en if isnum(x['entry_bid_size'])]) if en else ''
        rec['median_entry_ask_size'] = statistics.median([x['entry_ask_size'] for x in en if isnum(x['entry_ask_size'])]) if en else ''
        out.append(rec)
    return out
FC = fill_class(F, lambda x: (x['epoch'], 'ALL', 'ALL'), ['epoch', 'book', 'account_type']) + fill_class(F, lambda x: (x['epoch'], x['book'], x['account_type']), ['epoch', 'book', 'account_type'])
FCr = fill_class(F, lambda x: (x['epoch'], x['root']), ['epoch', 'root'])
write_csv(RES + '/F_nbbo_fill_class.csv', FC + [dict(epoch=c['epoch'], book='root:' + c['root'], account_type='ALL', **{k: v for k, v in c.items() if k not in ('epoch', 'root')}) for c in FCr])

# ---------- E1 ledger-size sensitivity: does the better-than-market share depend on the reported size (bid/ask depth)?
def size_vs_depth(fs):
    out = []
    for x in fs:
        if not x['both_ok'] or x['kind'] != 'opt': continue
        out.append(dict(epoch=x['epoch'], size=x['size'], entry_ask_size=x['entry_ask_size'], exit_bid_size=x['exit_bid_size'],
                        entry_size_gt_ask_depth=(isnum(x['entry_ask_size']) and x['size'] > x['entry_ask_size']), exit_size_gt_bid_depth=(isnum(x['exit_bid_size']) and x['size'] > x['exit_bid_size'])))
    return out
SD = size_vs_depth(F)
depth = {}
for ep in ('E1', 'E2', 'paper'):
    v = [x for x in SD if x['epoch'] == ep]
    depth[ep] = dict(n=len(v), entry_size_gt_ask_depth=round(sum(1 for x in v if x['entry_size_gt_ask_depth']) / len(v), 4) if v else '', exit_size_gt_bid_depth=round(sum(1 for x in v if x['exit_size_gt_bid_depth']) / len(v), 4) if v else '')

# ---------------------------------------------------------------- 3. executable repricing
def repricing(fs, keyf, keynames):
    out = []
    for k, v in group(fs, keyf).items():
        both = [x for x in v if x['both_ok']]
        if not both: continue
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,))); rec['n'] = len(both); rec['n_days'] = len(set(x['day'] for x in both))
        days = [x['day'] for x in both]
        for name, col in (('reported', 'pnl_reported'), ('exec', '_exec0'), ('nbbo_mid', '_nmid0')):
            m = metrics([x[col] for x in both], days)
            rec[f'{name}_total'] = round(m['total'], 2); rec[f'{name}_mean'] = round(m['mean'], 2); rec[f'{name}_ci_lo'] = r2(m['ci_lo']); rec[f'{name}_ci_hi'] = r2(m['ci_hi'])
            rec[f'{name}_dci_lo'] = r2(m['dci_lo']); rec[f'{name}_dci_hi'] = r2(m['dci_hi']); rec[f'{name}_win_rate'] = round(m['win_rate'], 4); rec[f'{name}_pf'] = round(m['pf'], 3) if m['pf'] != float('inf') else 'inf'
        b1 = [x for x in v if x['both_ok_1s']]
        if b1:
            m = metrics([x['_exec1'] for x in b1], [x['day'] for x in b1])
            rec['n_1s'] = len(b1); rec['exec_1s_total'] = round(m['total'], 2); rec['exec_1s_mean'] = round(m['mean'], 2); rec['exec_1s_dci_lo'] = r2(m['dci_lo']); rec['exec_1s_dci_hi'] = r2(m['dci_hi'])
            rec['exec_1s_win_rate'] = round(m['win_rate'], 4); rec['exec_1s_pf'] = round(m['pf'], 3) if m['pf'] != float('inf') else 'inf'
            rec['reported_total_1s_rows'] = round(sum(x['pnl_reported'] for x in b1), 2)
        else:
            rec['n_1s'] = 0
        d = metrics([x['pnl_reported'] - x['_exec0'] for x in both], days)
        rec['diff_rep_minus_exec_mean'] = round(d['mean'], 2); rec['diff_dci_lo'] = r2(d['dci_lo']); rec['diff_dci_hi'] = r2(d['dci_hi']); rec['diff_ci_lo'] = r2(d['ci_lo']); rec['diff_ci_hi'] = r2(d['ci_hi'])
        d2 = metrics([x['pnl_reported'] - x['_nmid0'] for x in both], days)
        rec['diff_rep_minus_nbbo_mid_mean'] = round(d2['mean'], 2); rec['diff_mid_dci_lo'] = r2(d2['dci_lo']); rec['diff_mid_dci_hi'] = r2(d2['dci_hi'])
        rec['spread_plus_fees_total'] = round(sum(x['_nmid0'] - x['_exec0'] for x in both), 2)
        inB = [x for x in both if x['in_B_sample']]
        rec['n_in_B'] = len(inB)
        rec['reported_total_in_B'] = round(sum(x['pnl_reported'] for x in inB), 2); rec['exec_total_in_B'] = round(sum(x['_exec0'] for x in inB), 2)
        rec['bar_mid_total_in_B'] = round(sum(x['pnl_bar_mid_B'] for x in inB), 2); rec['bar_spread_total_in_B'] = round(sum(x['pnl_bar_spread_B'] for x in inB), 2)
        rec['reported_total_all_rows'] = round(sum(x['pnl_reported'] for x in v), 2); rec['n_all_rows'] = len(v)
        clean = [x for x in both if not x['data_error'] and not x['pnl_mismatch']]
        rec['n_excl_dataerr_mismatch'] = len(clean); rec['reported_total_excl'] = round(sum(x['pnl_reported'] for x in clean), 2); rec['exec_total_excl'] = round(sum(x['_exec0'] for x in clean), 2)
        out.append(rec)
    return out
RP = repricing(F, lambda x: (x['epoch'], 'ALL', 'ALL'), ['epoch', 'book', 'account_type']) + repricing(F, lambda x: (x['epoch'], x['book'], 'ALL'), ['epoch', 'book', 'account_type']) + repricing(F, lambda x: (x['epoch'], x['book'], x['account_type']), ['epoch', 'book', 'account_type'])
RPm = repricing(F, lambda x: (x['epoch'], x['month']), ['epoch', 'month'])
RPr = repricing(F, lambda x: (x['epoch'], x['root']), ['epoch', 'root'])
write_csv(RES + '/F_nbbo_repricing.csv', RP + [dict(epoch=c['epoch'], book='month:' + c['month'], account_type='ALL', **{k: v for k, v in c.items() if k not in ('epoch', 'month')}) for c in RPm]
          + [dict(epoch=c['epoch'], book='root:' + c['root'], account_type='ALL', **{k: v for k, v in c.items() if k not in ('epoch', 'root')}) for c in RPr])
print(f'repricing done {time.time() - T0:.0f}s', flush=True)

# ---------------------------------------------------------------- 4. spreads
def spreads(fs, keyf, keynames):
    out = []
    for k, v in group(fs, keyf).items():
        en = [x for x in v if x['entry_status'] == 'ok']; ex = [x for x in v if x['exit_status'] == 'ok']
        if not en and not ex: continue
        rec = dict(zip(keynames, k if isinstance(k, tuple) else (k,))); rec['kind'] = v[0]['kind']
        rec['assumed_half_spread_pct'] = assumed_hs(v[0]['root'], v[0]['kind']) if len(set(x['root'] for x in v)) == 1 else ''
        for nm, s, key in (('entry', en, '_en'), ('exit', ex, '_ex')):
            hs = [x[key]['hs0'] for x in s]; hp = [x[key]['hs0_pct'] for x in s if isnum(x[key]['hs0_pct'])]
            rec[f'n_{nm}'] = len(s)
            rec[f'{nm}_hs_median'] = round(statistics.median(hs), 4) if hs else ''; rec[f'{nm}_hs_mean'] = round(statistics.mean(hs), 4) if hs else ''
            rec[f'{nm}_hs_pct_median'] = round(statistics.median(hp), 4) if hp else ''; rec[f'{nm}_hs_pct_mean'] = round(statistics.mean(hp), 4) if hp else ''
            rec[f'{nm}_hs_pct_p25'] = round(float(np.percentile(hp, 25)), 4) if hp else ''; rec[f'{nm}_hs_pct_p75'] = round(float(np.percentile(hp, 75)), 4) if hp else ''
            a = rec['assumed_half_spread_pct']
            rec[f'{nm}_share_above_assumed'] = round(sum(1 for h in hp if h > a) / len(hp), 4) if (hp and isinstance(a, float) and isnum(a)) else ''
            mids = [x[key]['mid0'] for x in s]
            rec[f'{nm}_mid_median'] = round(statistics.median(mids), 3) if mids else ''
        out.append(rec)
    return out
SPR = spreads(F, lambda x: (x['epoch'], 'ALL'), ['epoch', 'root']) + spreads(F, lambda x: (x['epoch'], x['root']), ['epoch', 'root'])
write_csv(RES + '/F_nbbo_spreads.csv', SPR)
# realized half-spread (% of mid) by assumption bucket, for the comparison sentence
def bucket(root, kind):
    if kind == 'stk': return 'shares'
    if root in C.INDEX_ROOTS: return 'index (assumed 1.5 %)'
    if root in ('SPY', 'QQQ'): return 'SPY/QQQ (assumed 1 %)'
    if root == 'IWM': return 'IWM (assumed 2 %)'
    return 'single names (assumed 2 %)'
SPRb = spreads([dict(x, root=bucket(x['root'], x['kind'])) for x in F], lambda x: (x['epoch'], x['root']), ['epoch', 'bucket'])
for b in SPRb:
    b['assumed_half_spread_pct'] = {'index (assumed 1.5 %)': 0.015, 'SPY/QQQ (assumed 1 %)': 0.01, 'IWM (assumed 2 %)': 0.02, 'single names (assumed 2 %)': 0.02}.get(b['bucket'], '')

# ---------------------------------------------------------------- 5. same-minute repeats (Epoch 1)
csize = collections.Counter(x['cluster'] for x in F if x['group'] == 'ledger')
REP = []
for x in F:
    if x['group'] != 'ledger' or x['kind'] != 'opt': continue
    r = x['_r']; x['_repeat'] = csize[x['cluster']] >= 2
    ck = N.contract_key(r, r['entry_date']); qs = [q for q in book.minute(ck, r['entry_dt']) if isnum(q[1]) and isnum(q[2]) and q[2] > 0]
    p = r['entry_px']
    rec = dict(epoch=x['epoch'], book=x['book'], account_type=x['account_type'], trade_id=x['trade_id'], root=x['root'], cluster=x['cluster'], cluster_size=csize[x['cluster']], is_repeat=x['_repeat'],
               entry_premium=p, pnl_reported=x['pnl_reported'], n_quote_seconds=len(qs))
    if qs:
        nb = len(set((b, a) for _, b, a in qs)); minb = min(b for _, b, _ in qs); maxa = max(a for _, _, a in qs); minm = min((a + b) / 2 for _, b, a in qs); maxm = max((a + b) / 2 for _, b, a in qs)
        rec.update(n_distinct_nbbo=nb, nbbo_changed=nb > 1, min_bid=minb, max_ask=maxa, min_ask=min(a for _, _, a in qs), max_bid=max(b for _, b, _ in qs),
                   matches_bid_any_second=any(abs(p - b) <= TOL for _, b, _ in qs), matches_ask_any_second=any(abs(p - a) <= TOL for _, _, a in qs),
                   matches_mid_any_second=any(abs(p - (a + b) / 2) <= MID_TOL for _, b, a in qs),
                   within_minute_nbbo_range=(minb - TOL <= p <= maxa + TOL), below_min_bid=p < minb - TOL, above_max_ask=p > maxa + TOL,
                   below_min_mid=p < minm - MID_TOL, matches_any_quote=any(abs(p - b) <= TOL or abs(p - a) <= TOL or abs(p - (a + b) / 2) <= MID_TOL for _, b, a in qs))
    REP.append(rec)
write_csv(RES + '/F_nbbo_repeats.csv', REP)
def rep_summary(rs):
    out = []
    for key, v in group(rs, lambda z: (z['epoch'], 'repeat' if z['is_repeat'] else 'single')).items():
        w = [z for z in v if z['n_quote_seconds'] > 0]
        rec = dict(epoch=key[0], rows=key[1], n=len(v), n_with_minute_quotes=len(w), n_clusters=len(set(z['cluster'] for z in v)), reported_pnl=round(sum(z['pnl_reported'] for z in v), 2))
        if w:
            for f in ('nbbo_changed', 'matches_bid_any_second', 'matches_ask_any_second', 'matches_mid_any_second', 'matches_any_quote', 'within_minute_nbbo_range', 'below_min_bid', 'above_max_ask', 'below_min_mid'):
                rec[f] = round(sum(1 for z in w if z[f]) / len(w), 4)
            rec['median_distinct_nbbo'] = statistics.median(z['n_distinct_nbbo'] for z in w)
            rec['reported_pnl_below_min_bid'] = round(sum(z['pnl_reported'] for z in w if z['below_min_bid']), 2)
        out.append(rec)
    return out
REPS = rep_summary(REP)
print(f'repeats done {time.time() - T0:.0f}s', flush=True)

# ---------------------------------------------------------------- RESULTS_NBBO.md
MD = []
def H(s): MD.append(s); MD.append('')
def T(lines): MD.extend(lines); MD.append('')
def byk(lst, **kw):
    for x in lst:
        if all(x.get(k) == v for k, v in kw.items()): return x
    return None

e1 = byk(RP, epoch='E1', book='ALL'); e2 = byk(RP, epoch='E2', book='ALL'); pp = byk(RP, epoch='paper', book='ALL')
c1 = byk(COV, epoch='E1', book='ALL'); c2 = byk(COV, epoch='E2', book='ALL'); cp = byk(COV, epoch='paper', book='ALL')
fc1 = byk(FC, epoch='E1', book='ALL'); fc2 = byk(FC, epoch='E2', book='ALL'); fcp = byk(FC, epoch='paper', book='ALL')
B_pub = {'E1': dict(n=452, reported=36729, mid=21567, spread=7914, adverse=-24279), 'E2': dict(n=501, reported=2043, mid=-3098, spread=-14913, adverse=-51494), 'paper': dict(n=84, reported=-3632, mid=-4702, spread=-6217, adverse=-13597)}
A_pub = {'E1': 43248, 'E2': -3757, 'paper': -3632}

H('# GeorgeFi reported fills vs the ThetaData 1-second NBBO: results')
MD.append(f'Generated {datetime.datetime.now(C.ET).strftime("%Y-%m-%d %H:%M ET")} by code/nbbo_analyze.py from the cache written by code/nbbo_fetch.py. This extends RESULTS.md section B (Unusual Whales 1-minute bar ranges) with the measured NBBO at the reported second. Labels: **Reported by GeorgeFi** = the operator\'s ledger premiums and P&L; **Executable at NBBO (ours)** = the same trades filled at the ask (entry) and the bid (exit) prevailing at the reported second, $0.70/contract/side. Bootstrap CIs: {BOOT_N} resamples, numpy seed {SEED}; "day CI" resamples ET entry days (clusters), "CI" resamples trades. E1 = Epoch 1 main book; E2 = Epoch 2 (all four books); paper = SPX paper book. Shares rows are priced on the stock NBBO (no fees).')
MD.append('')
H('## Summary (every number is copied from the tables below)')
def cov_s(c): return f"{c['n_both_ok']}/{c['n']} rows ({pct(c['n_both_ok'] / c['n'])}) have a valid NBBO at both the entry and the exit second; entry quotes {c['n_entry_ok']}, exit quotes {c['n_exit_ok']}"
MD.append(f"**Coverage.** E1: {cov_s(c1)}. E2: {cov_s(c2)}. Paper: {cov_s(cp)}. Missing reasons are in the coverage table (plain-`SPX` root = no data on ThetaData; entries/exits outside 09:30–16:00 ET carry an empty quote; the 3 open rows have no exit).")
MD.append('')
def fc_s(f): return (f"entry at/below bid {pct(f['entry_at_or_below_bid'])} (below bid {pct(f['entry_below_bid'])}, at bid {pct(f['entry_at_bid'])}), inside {pct(f['entry_inside'])}, at mid {pct(f['entry_at_mid'])}, at ask {pct(f['entry_at_ask'])}, above ask {pct(f['entry_above_ask'])}; "
                      f"exit at/above ask {pct(f['exit_at_or_above_ask'])} (at ask {pct(f['exit_at_ask'])}, above ask {pct(f['exit_above_ask'])}), below bid {pct(f['exit_below_bid'])}; median entry position in the spread {f['entry_pos_median']}, exit {f['exit_pos_median']}; "
                      f"either side better than the market {pct(f['either_side_better'])} of rows with both quotes")
MD.append(f"**Fill classification (Reported by GeorgeFi vs the NBBO at the reported second).** E1 ({fc1['n_entry']} entries / {fc1['n_exit']} exits): {fc_s(fc1)}. E2 ({fc2['n_entry']} / {fc2['n_exit']}): {fc_s(fc2)}. Paper ({fcp['n_entry']} / {fcp['n_exit']}): {fc_s(fcp)}.")
MD.append('')
def rp_s(e, ep):
    b = B_pub[ep]
    return (f"{e['n']} rows: reported {f0(e['reported_total'])} (all {e['n_all_rows']} rows of the epoch: {f0(e['reported_total_all_rows'])}; RESULTS.md A: {A_pub[ep]:,}) → executable at NBBO {f0(e['exec_total'])} "
            f"({f1(e['exec_mean'])}/trade, day CI [{f1(e['exec_dci_lo'])}, {f1(e['exec_dci_hi'])}], trade CI [{f1(e['exec_ci_lo'])}, {f1(e['exec_ci_hi'])}]; win rate {pct(e['exec_win_rate'])} vs reported {pct(e['reported_win_rate'])}; PF {pf_s(e['exec_pf'])} vs {pf_s(e['reported_pf'])}); "
            f"1-second-later variant {f0(e.get('exec_1s_total'))} on {e.get('n_1s')} rows; NBBO mid without costs {f0(e['nbbo_mid_total'])}; reported − executable {f1(e['diff_rep_minus_exec_mean'])}/trade, day CI [{f1(e['diff_dci_lo'])}, {f1(e['diff_dci_hi'])}], "
            f"of which reported − NBBO mid {f1(e['diff_rep_minus_nbbo_mid_mean'])}/trade [{f1(e['diff_mid_dci_lo'])}, {f1(e['diff_mid_dci_hi'])}] and spread + fees {f0(e['spread_plus_fees_total'])} in total. "
            f"On the {e['n_in_B']} rows shared with RESULTS.md §B: reported {f0(e['reported_total_in_B'])}, bar-VWAP mid {f0(e['bar_mid_total_in_B'])}, modelled spread {f0(e['bar_spread_total_in_B'])}, executable NBBO {f0(e['exec_total_in_B'])} (§B published on its {b['n']} rows: reported {b['reported']:,}, mid {b['mid']:,}, spread {b['spread']:,}, adverse {b['adverse']:,})")
MD.append(f"**Executable repricing (ours).** E1: {rp_s(e1, 'E1')}. E2: {rp_s(e2, 'E2')}. Paper: {rp_s(pp, 'paper')}.")
MD.append('')
sp_all = {s['epoch']: s for s in SPR if s['root'] == 'ALL'}
def sp_s(ep):
    s = sp_all.get(ep)
    if not s: return 'n/a'
    return f"median realized half-spread at entry {pct(s['entry_hs_pct_median'])} of mid (mean {pct(s['entry_hs_pct_mean'])}, ${s['entry_hs_median']}), at exit {pct(s['exit_hs_pct_median'])} (mean {pct(s['exit_hs_pct_mean'])})"
MD.append(f"**Spreads.** E1: {sp_s('E1')}. E2: {sp_s('E2')}. Paper: {sp_s('paper')}. Per root and per assumption bucket below (RESULTS.md §B used 1 % SPY/QQQ, 2 % IWM, 1.5 % index roots, 2 % single names).")
MD.append('')
rs1 = byk(REPS, epoch='E1', rows='repeat'); rs1s = byk(REPS, epoch='E1', rows='single')
if rs1:
    MD.append(f"**Epoch 1 same-minute repeats.** {rs1['n']} rows in {rs1['n_clusters']} same-contract-same-minute clusters ({rs1['n_with_minute_quotes']} with quotes in the minute): the NBBO changed within the entry minute for {pct(rs1['nbbo_changed'])} (median {rs1['median_distinct_nbbo']} distinct NBBOs per minute); the reported entry premium equals a bid, ask or mid of some second in that minute for {pct(rs1['matches_any_quote'])} of rows, lies within [min bid, max ask] of the minute for {pct(rs1['within_minute_nbbo_range'])}, and is below the minute's lowest bid for {pct(rs1['below_min_bid'])} (reported P&L of those rows {f0(rs1['reported_pnl_below_min_bid'])}). Non-repeated E1 rows: matches {pct(rs1s['matches_any_quote'])}, below lowest bid {pct(rs1s['below_min_bid'])}.")
    MD.append('')

H('## 1. Coverage')
MD.append(f'Rows: {len(rows)} (ledger 1,149 + paper 84); contract-days {len(merged)}; ThetaData 1-second quote requests {n_req} ({dict(st_counts)}). Status per side: `ok` = valid NBBO row at the reported second (ask > 0, ask ≥ bid); `no_quote` = a row exists but bid/ask are 0 or empty (outside 09:30–16:00 ET); `nodata` = ThetaData has no quotes for the contract (plain-`SPX` root); `missing_second` = window returned but no row at that second; `no_exit` = open position.')
MD.append('')
T(['| epoch | book | account | n | instrument | entry ok | exit ok | both ok | both ok (1 s later) | entry: no_quote / nodata / error / no_exit / not_fetched | exit: no_quote / nodata / error / no_exit / not_fetched | entry outside RTH | exit outside RTH | reported P&L (all rows) | reported P&L (both ok) |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {c['epoch']} | {c['book']} | {c['account_type']} | {c['n']} | {c['n_with_instrument']} | {c['n_entry_ok']} | {c['n_exit_ok']} | {c['n_both_ok']} | {c['n_both_ok_1s']} | {c['entry_no_quote']} / {c['entry_nodata']} / {c['entry_error']} / {c['entry_no_exit']} / {c['entry_not_fetched']} | {c['exit_no_quote']} / {c['exit_nodata']} / {c['exit_error']} / {c['exit_no_exit']} / {c['exit_not_fetched']} | {c['n_entry_outside_rth']} | {c['n_exit_outside_rth']} | {f0(c['reported_pnl_all'])} | {f0(c['reported_pnl_both_ok'])} |" for c in COV])
H('### Coverage by OCC root (n ≥ 5)')
T(['| epoch | root | n | entry ok | exit ok | both ok | entry no_quote / nodata | exit no_quote / nodata |', '|---|---|---|---|---|---|---|---|'] +
  [f"| {c['epoch']} | {c['root']} | {c['n']} | {c['n_entry_ok']} | {c['n_exit_ok']} | {c['n_both_ok']} | {c['entry_no_quote']} / {c['entry_nodata']} | {c['exit_no_quote']} / {c['exit_nodata']} |" for c in COVr if c['n'] >= 5])

H('## 2. Fill classification: Reported by GeorgeFi vs the NBBO at the reported second')
MD.append(f'Classes of the reported premium p against the NBBO [bid, ask] at the reported second (q0 = last quote at or before HH:MM:SS): below bid (p < bid − ${TOL}), at bid (±${TOL}), inside, at mid (±${MID_TOL}), at ask, above ask. Position = (p − bid)/(ask − bid). GeorgeFi is long: an entry at or below the bid, or an exit at or above the ask, is better than the market offered at that second. "1 s later" repeats the better-than-market share against the quote at HH:MM:SS+1 (the first snapshot that includes updates posted during the reported second).')
MD.append('')
T(['| epoch | book | account | n entry | below bid | at bid | inside | at mid | at ask | above ask | entry ≤ bid | entry ≤ bid (1 s later) | median pos | n exit | below bid | at bid | inside | at mid | at ask | above ask | exit ≥ ask | exit ≥ ask (1 s later) | median pos | either side better (n both) | both within NBBO | reported P&L either better / both within |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {f['epoch']} | {f['book']} | {f['account_type']} | {f['n_entry']} | {pct(f['entry_below_bid'])} | {pct(f['entry_at_bid'])} | {pct(f['entry_inside'])} | {pct(f['entry_at_mid'])} | {pct(f['entry_at_ask'])} | {pct(f['entry_above_ask'])} | {pct(f['entry_at_or_below_bid'])} | {pct(f['entry_at_or_below_bid_1s'])} | {f['entry_pos_median']} | {f['n_exit']} | {pct(f['exit_below_bid'])} | {pct(f['exit_at_bid'])} | {pct(f['exit_inside'])} | {pct(f['exit_at_mid'])} | {pct(f['exit_at_ask'])} | {pct(f['exit_above_ask'])} | {pct(f['exit_at_or_above_ask'])} | {pct(f['exit_at_or_above_ask_1s'])} | {f['exit_pos_median']} | {pct(f['either_side_better'])} ({f['n_both']}) | {pct(f['both_sides_within_nbbo'])} | {f0(f['reported_pnl_rows_either_better'])} / {f0(f['reported_pnl_rows_both_within'])} |" for f in FC if f['n_entry'] or f['n_exit']])
H('### Fill classification by OCC root (n entry ≥ 10)')
T(['| epoch | root | n entry | entry ≤ bid | entry inside/mid | entry ≥ ask | median entry pos | n exit | exit ≤ bid | exit inside/mid | exit ≥ ask | median exit pos |', '|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {f['epoch']} | {f['root']} | {f['n_entry']} | {pct(f['entry_at_or_below_bid'])} | {pct((f['entry_inside'] or 0) + (f['entry_at_mid'] or 0))} | {pct((f['entry_at_ask'] or 0) + (f['entry_above_ask'] or 0))} | {f['entry_pos_median']} | {f['n_exit']} | {pct((f['exit_below_bid'] or 0) + (f['exit_at_bid'] or 0))} | {pct((f['exit_inside'] or 0) + (f['exit_at_mid'] or 0))} | {pct(f['exit_at_or_above_ask'])} | {f['exit_pos_median']} |" for f in FCr if f['n_entry'] >= 10])
MD.append(f"Reported size vs displayed NBBO depth (option rows with both quotes): share of rows whose reported size exceeds the ask size at entry / the bid size at exit — E1 {pct(depth['E1']['entry_size_gt_ask_depth'])} / {pct(depth['E1']['exit_size_gt_bid_depth'])} (n {depth['E1']['n']}), E2 {pct(depth['E2']['entry_size_gt_ask_depth'])} / {pct(depth['E2']['exit_size_gt_bid_depth'])} (n {depth['E2']['n']}), paper {pct(depth['paper']['entry_size_gt_ask_depth'])} / {pct(depth['paper']['exit_size_gt_bid_depth'])} (n {depth['paper']['n']}).")
MD.append('')

H('## 3. Executable repricing: Reported by GeorgeFi vs Executable at NBBO (ours)')
MD.append('Rows with a valid NBBO at both the entry and the exit second. Executable = buy at the ask of the entry second, sell at the bid of the exit second, reported size, $0.70/contract/side (shares: stock NBBO, no fees). "NBBO mid" = mid-to-mid, no costs (the NBBO analogue of §B\'s bar-VWAP `mid`). "1 s later" uses the quotes at HH:MM:SS+1. CIs: day = ET-entry-day cluster bootstrap; trade = plain bootstrap. The §B columns repeat RESULTS.md section B\'s bar-VWAP mid and modelled-spread P&L on the rows shared with that sample.')
MD.append('')
T(['| epoch | book | account | n (days) | reported total | executable total | executable mean [day CI] [trade CI] | WR rep/exec | PF rep/exec | 1 s later: n / exec total | NBBO mid total | reported − exec mean [day CI] | reported − NBBO mid mean [day CI] | spread + fees total | §B rows: n / reported / bar mid / bar spread / exec NBBO | excl. data-error & mismatch: n / reported / exec |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {e['epoch']} | {e['book']} | {e['account_type']} | {e['n']} ({e['n_days']}) | {f0(e['reported_total'])} | {f0(e['exec_total'])} | {f1(e['exec_mean'])} [{f1(e['exec_dci_lo'])}, {f1(e['exec_dci_hi'])}] [{f1(e['exec_ci_lo'])}, {f1(e['exec_ci_hi'])}] | {pct(e['reported_win_rate'])}/{pct(e['exec_win_rate'])} | {pf_s(e['reported_pf'])}/{pf_s(e['exec_pf'])} | {e['n_1s']} / {f0(e.get('exec_1s_total'))} | {f0(e['nbbo_mid_total'])} | {f1(e['diff_rep_minus_exec_mean'])} [{f1(e['diff_dci_lo'])}, {f1(e['diff_dci_hi'])}] | {f1(e['diff_rep_minus_nbbo_mid_mean'])} [{f1(e['diff_mid_dci_lo'])}, {f1(e['diff_mid_dci_hi'])}] | {f0(e['spread_plus_fees_total'])} | {e['n_in_B']} / {f0(e['reported_total_in_B'])} / {f0(e['bar_mid_total_in_B'])} / {f0(e['bar_spread_total_in_B'])} / {f0(e['exec_total_in_B'])} | {e['n_excl_dataerr_mismatch']} / {f0(e['reported_total_excl'])} / {f0(e['exec_total_excl'])} |" for e in RP])
H('### Epoch totals side by side (same rows unless stated)')
T(['| epoch | rows | Reported by GeorgeFi (RESULTS.md A, all rows) | Reported on NBBO-covered rows | Executable at NBBO (ours) | Executable, 1 s later | NBBO mid, no costs | §B bar-VWAP mid (published, §B rows) | §B modelled spread (published, §B rows) | §B adverse (published, §B rows) |', '|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {e['epoch']} | {e['n']} | {A_pub[e['epoch']]:,} ({e['n_all_rows']} rows) | {f0(e['reported_total'])} | {f0(e['exec_total'])} | {f0(e.get('exec_1s_total'))} ({e['n_1s']} rows) | {f0(e['nbbo_mid_total'])} | {B_pub[e['epoch']]['mid']:,} ({B_pub[e['epoch']]['n']} rows) | {B_pub[e['epoch']]['spread']:,} | {B_pub[e['epoch']]['adverse']:,} |" for e in (e1, e2, pp) if e])
H('### Repricing by month')
T(['| epoch | month | n (days) | reported | executable | executable mean [day CI] | WR rep/exec | PF rep/exec | NBBO mid | 1 s later exec |', '|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {e['epoch']} | {e['month']} | {e['n']} ({e['n_days']}) | {f0(e['reported_total'])} | {f0(e['exec_total'])} | {f1(e['exec_mean'])} [{f1(e['exec_dci_lo'])}, {f1(e['exec_dci_hi'])}] | {pct(e['reported_win_rate'])}/{pct(e['exec_win_rate'])} | {pf_s(e['reported_pf'])}/{pf_s(e['exec_pf'])} | {f0(e['nbbo_mid_total'])} | {f0(e.get('exec_1s_total'))} |" for e in RPm])
H('### Repricing by OCC root (n ≥ 10)')
T(['| epoch | root | n | reported | executable | executable mean [day CI] | WR rep/exec | NBBO mid | reported − exec mean |', '|---|---|---|---|---|---|---|---|---|'] +
  [f"| {e['epoch']} | {e['root']} | {e['n']} | {f0(e['reported_total'])} | {f0(e['exec_total'])} | {f1(e['exec_mean'])} [{f1(e['exec_dci_lo'])}, {f1(e['exec_dci_hi'])}] | {pct(e['reported_win_rate'])}/{pct(e['exec_win_rate'])} | {f0(e['nbbo_mid_total'])} | {f1(e['diff_rep_minus_exec_mean'])} |" for e in RPr if e['n'] >= 10])

H('## 4. Realized half-spreads (ours) vs the assumptions in backtest/costs.py and RESULTS.md §B')
MD.append('Half-spread = (ask − bid)/2 at the reported second, in $ and as a share of the NBBO mid; "share above assumed" = rows whose realized half-spread (% of mid) exceeds the flat assumption used in §B (1 % SPY/QQQ, 2 % IWM, 1.5 % SPXW/NDXP/RUTW, 2 % single names).')
MD.append('')
T(['| epoch | bucket | assumed | n entry | entry hs % median (mean) [p25, p75] | entry hs $ median | share above assumed | n exit | exit hs % median (mean) | exit hs $ median | share above assumed | median mid (entry) |', '|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {s['epoch']} | {s['bucket']} | {pct(s['assumed_half_spread_pct']) if isinstance(s['assumed_half_spread_pct'], float) else 'n/a'} | {s['n_entry']} | {pct(s['entry_hs_pct_median'])} ({pct(s['entry_hs_pct_mean'])}) [{pct(s['entry_hs_pct_p25'])}, {pct(s['entry_hs_pct_p75'])}] | {s['entry_hs_median']} | {pct(s['entry_share_above_assumed']) if s['entry_share_above_assumed'] != '' else 'n/a'} | {s['n_exit']} | {pct(s['exit_hs_pct_median'])} ({pct(s['exit_hs_pct_mean'])}) | {s['exit_hs_median']} | {pct(s['exit_share_above_assumed']) if s['exit_share_above_assumed'] != '' else 'n/a'} | {s['entry_mid_median']} |" for s in SPRb])
H('### By OCC root (n entry ≥ 5)')
T(['| epoch | root | assumed | n entry | entry hs % median (mean) | entry hs $ median | share above assumed | n exit | exit hs % median (mean) | exit hs $ median | median mid |', '|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {s['epoch']} | {s['root']} | {pct(s['assumed_half_spread_pct']) if isinstance(s['assumed_half_spread_pct'], float) and isnum(s['assumed_half_spread_pct']) else 'n/a'} | {s['n_entry']} | {pct(s['entry_hs_pct_median'])} ({pct(s['entry_hs_pct_mean'])}) | {s['entry_hs_median']} | {pct(s['entry_share_above_assumed']) if s['entry_share_above_assumed'] != '' else 'n/a'} | {s['n_exit']} | {pct(s['exit_hs_pct_median'])} ({pct(s['exit_hs_pct_mean'])}) | {s['exit_hs_median']} | {s['entry_mid_median']} |" for s in SPR if s['n_entry'] >= 5])

H('## 5. Epoch 1 same-contract-same-minute repeats vs the NBBO within the minute')
MD.append(f'For every ledger option row, all 1-second NBBO rows of the reported entry minute (up to 60). "repeat" = the row shares contract and entry minute with at least one other ledger row (RESULTS.md: 382 such rows in Epoch 1). "matches any quote" = the reported entry premium equals the bid or ask (±${TOL}) or the mid (±${MID_TOL}) of at least one second of that minute.')
MD.append('')
T(['| epoch | rows | n | with minute quotes | clusters | reported P&L | NBBO changed in minute | median distinct NBBOs | matches bid | matches ask | matches mid | matches any quote | within [min bid, max ask] | below min bid | above max ask | below min mid | reported P&L of rows below min bid |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|'] +
  [f"| {s['epoch']} | {s['rows']} | {s['n']} | {s['n_with_minute_quotes']} | {s['n_clusters']} | {f0(s['reported_pnl'])} | {pct(s.get('nbbo_changed'))} | {s.get('median_distinct_nbbo', 'n/a')} | {pct(s.get('matches_bid_any_second'))} | {pct(s.get('matches_ask_any_second'))} | {pct(s.get('matches_mid_any_second'))} | {pct(s.get('matches_any_quote'))} | {pct(s.get('within_minute_nbbo_range'))} | {pct(s.get('below_min_bid'))} | {pct(s.get('above_max_ask'))} | {pct(s.get('below_min_mid'))} | {f0(s.get('reported_pnl_below_min_bid'))} |" for s in REPS])

H('## 6. Interpretation')
if e1 and fc1:
    share_expl = (e1['reported_total'] - e1['exec_total']) / e1['reported_total'] if e1['reported_total'] else float('nan')
    share_mid = (e1['reported_total'] - e1['nbbo_mid_total']) / e1['reported_total'] if e1['reported_total'] else float('nan')
    MD.append(f"On the {e1['n']} Epoch 1 rows with an NBBO at both reported seconds, GeorgeFi reports {f0(e1['reported_total'])}; filled at the NBBO ask and bid of those same seconds the rows are worth {f0(e1['exec_total'])} ({f1(e1['exec_mean'])}/trade, day-cluster CI [{f1(e1['exec_dci_lo'])}, {f1(e1['exec_dci_hi'])}]). The gap, {f0(e1['reported_total'] - e1['exec_total'])} or {pct(share_expl)} of the reported total on these rows, is the fill assumption: {f0(e1['reported_total'] - e1['nbbo_mid_total'])} ({pct(share_mid)}) comes from reported premiums better than the NBBO mid and {f0(e1['spread_plus_fees_total'])} from crossing the realized spread plus fees. {pct(fc1['entry_at_or_below_bid'])} of Epoch 1 entries are at or below the bid and {pct(fc1['exit_at_or_above_ask'])} of exits at or above the ask; {pct(fc1['either_side_better'])} of rows have at least one fill better than the market offered at that second, and those rows carry {f0(fc1['reported_pnl_rows_either_better'])} of reported P&L against {f0(fc1['reported_pnl_rows_both_within'])} for rows whose fills both lie within the NBBO. The 1-second-later variant gives {f0(e1.get('exec_1s_total'))} on {e1.get('n_1s')} rows, so the result does not hinge on sub-second timestamp alignment.")
    MD.append('')
if e2 and fc2:
    MD.append(f"Epoch 2 ({e2['n']} rows): reported {f0(e2['reported_total'])} → executable {f0(e2['exec_total'])} ({f1(e2['exec_mean'])}/trade, day CI [{f1(e2['exec_dci_lo'])}, {f1(e2['exec_dci_hi'])}]); {pct(fc2['entry_at_or_below_bid'])} of entries at or below the bid, {pct(fc2['exit_at_or_above_ask'])} of exits at or above the ask. Paper ({pp['n']} rows): reported {f0(pp['reported_total'])} → executable {f0(pp['exec_total'])}; {pct(fcp['entry_at_or_below_bid'])} / {pct(fcp['exit_at_or_above_ask'])}.")
    MD.append('')
MD.append('What this does and does not show: the NBBO is the best displayed quote with its displayed size; a marketable order can fill inside the spread (price improvement, hidden liquidity, auctions) and a resting limit order can fill at the bid, so a reported entry at the bid is not impossible — but a record in which a large share of entries sit at or below the bid and exits at or above the ask is better than the market offered at those seconds, and the executable repricing is the number a taker would have obtained. Rows filled at the reported size could also exceed the displayed NBBO size (the size-vs-depth line in section 2). Nothing here speaks to signal quality; see RESULTS.md section C for that.')
MD.append('')

H('## METHODOLOGY')
MD.append(f"""- **Timestamps.** Ledger `entryTime`/`exitTime` are UTC with milliseconds; converted to America/New_York. The reported second is HH:MM:SS (milliseconds truncated).
- **Quotes.** ThetaData `option_history_quote` / `stock_history_quote`, `interval='1s'`, root = OCC root (SPXW, RUTW, NDXP, SPY, QQQ, IWM, single names), strike as the plain number string (`'612.5'` for half strikes), one request per merged window [reported minute start − {N.PRE_S} s, reported second + {N.POST_S} s] per contract-day (windows that overlap or touch are merged); {n_req} requests, 2 concurrent, every response cached as gzip CSV under `$SP/theta/cache/georgefi_nbbo/` (never refetched; transport errors were retried with a fresh login). Per the ThetaData API description, the row stamped T "represents the last quote prior to the interval's timestamp", i.e. the NBBO prevailing at T.000. q0 = row at the reported second (the last quote at or before HH:MM:SS); q1 = row at HH:MM:SS+1 (the first snapshot that includes updates posted during the reported second). The true quote at HH:MM:SS.mmm lies between the two; the tables use q0 and show q1 as the "1 s later" variant. NDXP option quotes are served (the Nasdaq GIDS restriction in provider_audit.md applies to the NDX index price only); the plain-`SPX` root returns no data (4 rows; the SPXW twin is not substituted here).
- **Valid quote.** ask > 0 and ask ≥ bid (bid may be 0). Rows outside 09:30–16:00 ET usually carry 0/empty quotes and are counted as `no_quote`; rows after 16:00 that carry a quote (ETF options trade to 16:15) are used as found and flagged `exit_rth = False` in F_nbbo_trades.csv.
- **Classification.** below bid / at bid (±${TOL}) / inside / at mid (±${MID_TOL}) / at ask (±${TOL}) / above ask; position = (p − bid)/(ask − bid). Within-NBBO = at bid, inside, at mid or at ask.
- **Executable P&L.** (bid at exit second − ask at entry second) × 100 × reported size − 2 × $0.70 × size for options; (bid − ask) × shares for stock rows, no fees. NBBO-mid P&L = (mid_exit − mid_entry) × 100 × size, no fees. Rows with a valid quote at both seconds only; partial exits / scale-ins are priced at the ledger's final size and premiums exactly as §B does (P&L-mismatch rows are flagged and the totals are repeated without them).
- **Statistics.** Win rate = share of P&L > 0; PF = gross wins / gross losses; bootstrap {BOOT_N} resamples, `numpy.random.default_rng({SEED})` fresh per statistic; day CI resamples ET entry days with replacement and recomputes the per-trade mean.
- **Spreads.** Half-spread (ask − bid)/2 and its share of the mid at the reported second; medians and means by OCC root, epoch and §B assumption bucket.
- **Repeats.** All 1-second NBBO rows of the reported entry minute; cluster = contract + entry minute as in RESULTS.md.
- **Limitations.** The NBBO carries no depth beyond the displayed size at the best price (fills larger than the displayed size would walk the book; the displayed sizes are in F_nbbo_trades.csv). Index-option (SPXW/RUTW/NDXP) quotes update many times per second; a 1-second snapshot can miss a quote that existed for part of the second, which is why both q0 and q1 are shown. Quote timestamps are the SIP's; the ledger's clock is GeorgeFi's. Pre-market entries (3 rows, 2026-02-10) and the 4 plain-`SPX` rows cannot be checked. Shares rows use the consolidated stock NBBO (SIP), 50 rows. Nothing was tuned; every row is in F_nbbo_trades.csv.
- **Commands.** `set -a; . "$SP/secrets/research.env"; set +a; SP="$SP" python3 -I nbbo_fetch.py` then `SP="$SP" python3 -I nbbo_analyze.py` from `research/georgefi_full_history/code/`.""")
MD.append('')
open(RES + '/RESULTS_NBBO.md', 'w').write('\n'.join(MD))
json.dump(dict(generated=datetime.datetime.now(C.ET).isoformat(), rows=len(rows), contract_days=len(merged), requests=n_req, request_status=dict(st_counts), boot_n=BOOT_N, seed=SEED, tol=TOL, mid_tol=MID_TOL, runtime_s=round(time.time() - T0)),
          open(RES + '/F_nbbo_run_info.json', 'w'), indent=1)
print(f'RESULTS_NBBO.md written {time.time() - T0:.0f}s', flush=True)
