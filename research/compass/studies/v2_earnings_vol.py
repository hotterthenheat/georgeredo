"""Study V2 (amendment A9): the earnings volatility cycle across the optionable universe.
V2a sells the ATM straddle at the close before the report session (P0) and buys it back at the report session's close;
V2b buys the ATM straddle five sessions earlier (P-5) and sells the same strike at P0.

  python3 v2_earnings_vol.py plan       events, sessions and the point-in-time universe -> events.parquet
  python3 v2_earnings_vol.py fetch      E* discovery at P-5 (Friday by Friday), then the P0 and event-session chains
  python3 v2_earnings_vol.py build      trades -> trades.parquet
  python3 v2_earnings_vol.py analyze [--holdout]

Chains share V1's cache and fetcher (v1_vol_pricing.py), so nothing is fetched twice."""
import datetime as dt, json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v1_vol_pricing as v1

OUT = os.path.join(v1.HERE, '..', 'results', 'v1', 'v2_earnings_vol'); os.makedirs(OUT, exist_ok=True)
LEDGER = os.path.join(OUT, 'ledger.jsonl')
START, END = dt.date(2023, 11, 27), dt.date(2026, 9, 30)
DEV_END, VAL_END = dt.date(2024, 12, 31), dt.date(2025, 12, 31)

def sessions():
    st = v1.stock_eod()
    return st, sorted(st.filter(pl.col('symbol') == 'SPY')['date'].to_list())

def fridays(after: dt.date, ss: set, horizon=35):
    """Friday expirations (the Thursday when Friday is a holiday) from `after` to `after` + horizon days"""
    out = []; d = after + dt.timedelta(days=(4 - after.weekday()) % 7)
    while d <= after + dt.timedelta(days=horizon):
        x = d
        while x not in ss and x > after: x -= dt.timedelta(days=1)
        if x >= after and x in ss: out.append(x)
        d += dt.timedelta(days=7)
    return out

def plan():
    st, ss = sessions(); sset = set(ss)
    e = pl.read_parquet(os.path.join(v1.ROOT, 'data_lake', 'unusualwhales', 'earnings.parquet'), columns=['ticker', 'report_date', 'report_time', 'report_type'])
    e = e.with_columns(pl.col('report_date').str.to_date(strict=False)).filter(pl.col('report_date').is_between(START, END) & pl.col('report_time').is_in(['premarket', 'postmarket']))
    e = e.unique(['ticker', 'report_date'])
    st = st.with_columns((pl.col('close') * pl.col('volume')).alias('dv'))
    by = {k[0]: g for k, g in st.group_by('symbol')}
    rows = []
    for r in e.iter_rows(named=True):
        t, rd = r['ticker'], r['report_date']
        nxt = [s for s in ss if s >= rd] if r['report_time'] == 'premarket' else [s for s in ss if s > rd]
        if not nxt: continue
        ev = nxt[0]; i = ss.index(ev)
        if i < 6: continue
        p0, p5 = ss[i - 1], ss[i - 6]
        g = by.get(t)
        if g is None: continue
        w = g.filter(pl.col('date') <= p5).tail(20)
        if w.height < 15 or w['date'][-1] != p5: continue
        if float(w['dv'].median()) < 50e6 or float(w['close'][-1]) < 10: continue
        rows.append({'symbol': t, 'report_date': rd, 'report_time': r['report_time'], 'event': ev, 'P0': p0, 'P5': p5,
                     'fridays': [str(x) for x in fridays(ev, sset)]})
    E = pl.DataFrame(rows).with_columns(
        pl.when(pl.col('event') <= DEV_END).then(pl.lit('dev')).when(pl.col('event') <= VAL_END).then(pl.lit('val')).otherwise(pl.lit('holdout')).alias('split'))
    E.write_parquet(f'{OUT}/events.parquet')
    print(E.group_by('split').agg(pl.len()).sort('split')); print('events', E.height, 'names', E['symbol'].n_unique())

_lock = threading.Lock()
def _run(jobs, tag):
    todo = [j for j in jobs if not os.path.exists(v1._path(*j))]
    print(f'{tag}: {len(jobs)} jobs, {len(todo)} to fetch', flush=True); t0 = time.time(); n = 0
    def one(j):
        nonlocal n
        res = v1._get(*j)
        with _lock:
            n += 1
            with open(LEDGER, 'a') as f: f.write(json.dumps({'t': j[0], 'D': str(j[1]), 'E': str(j[2]), 'which': tag, 'res': res}) + '\n')
            if n % 500 == 0: print(f'{tag} {n}/{len(todo)} {time.time() - t0:.0f}s', flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex: list(ex.map(one, todo))

def _nonempty(t, d, e):
    c = v1.chain(t, d, e)
    return c is not None and c.height > 0

def estar(r):
    for f in r['fridays']:
        f = dt.date.fromisoformat(f)
        if not os.path.exists(v1._path(r['symbol'], r['P5'], f)): return None, False      # not yet probed
        if _nonempty(r['symbol'], r['P5'], f): return f, True
    return None, True

def fetch():
    E = pl.read_parquet(f'{OUT}/events.parquet')
    for k in range(6):                                 # Friday by Friday until each event has its E* or runs out
        jobs = []
        for r in E.iter_rows(named=True):
            e, done = estar(r)
            if e is None and not done:
                nxt = next(dt.date.fromisoformat(f) for f in r['fridays'] if not os.path.exists(v1._path(r['symbol'], r['P5'], dt.date.fromisoformat(f))))
                jobs.append((r['symbol'], r['P5'], nxt))
        if not jobs: break
        _run(jobs, f'probe{k}')
    jobs = []
    for r in E.iter_rows(named=True):
        e, _ = estar(r)
        if e is None: continue
        jobs.append((r['symbol'], r['P0'], e))
        if e > r['event']: jobs.append((r['symbol'], r['event'], e))
    _run(jobs, 'P0+event')
    print('fetch done', flush=True)

def _leg(c, k, right):
    r = c.filter((pl.col('strike') == k) & (pl.col('right') == right) & pl.col('bid').is_finite() & pl.col('ask').is_finite() & (pl.col('ask') >= pl.col('bid')))
    return r.row(0, named=True) if r.height else None

def build():
    E = pl.read_parquet(f'{OUT}/events.parquet')
    st = v1.stock_eod().filter(pl.col('symbol').is_in(E['symbol'].unique().to_list()))
    st = st.with_columns((pl.col('close') / pl.col('close').shift(1).over('symbol')).alias('ratio'))
    by = {k[0]: g.sort('date') for k, g in st.group_by('symbol')}
    fee = 2 * v1.FEE / 100
    rows, excl = [], []
    for r in E.iter_rows(named=True):
        t, p5, p0, ev = r['symbol'], r['P5'], r['P0'], r['event']
        base = {k: r[k] for k in ('symbol', 'report_date', 'report_time', 'event', 'P0', 'P5', 'split')}
        es, _ = estar(r)
        if es is None: excl.append({**base, 'reason': 'no listed Friday expiration within 35 days (or not probed)'}); continue
        g = by.get(t)
        if g is None: excl.append({**base, 'reason': 'no stock rows'}); continue
        cl = dict(zip(g['date'].to_list(), g['close'].to_list()))
        if any(d not in cl for d in (p5, p0, ev)): excl.append({**base, 'reason': 'missing close at P-5, P0 or the event session'}); continue
        hit, how = v1.corp_hit(t, g, p5, ev)
        if hit: excl.append({**base, 'reason': hit, 'rule': how}); continue
        s5, s0, se = cl[p5], cl[p0], cl[ev]
        c5, c0 = v1.chain(t, p5, es), v1.chain(t, p0, es)
        ce = v1.chain(t, ev, es) if es > ev else None
        out = {**base, 'ca_rule': how, 'E': es, 'dte_event': (es - ev).days, 's5': s5, 's0': s0, 'se': se, 'realised_move': abs(se / s0 - 1)}
        # V2a: short at P0, out at the event close (or settle when E* is the event session)
        a = v1.straddle(c0, s0) if c0 is not None and c0.height else None
        if a is None: out['a_status'] = 'no two-sided ATM straddle at P0'
        else:
            k = a['strike']; mid0 = (a['cb'] + a['ca'] + a['pb'] + a['pa']) / 2
            out.update({'a_K': k, 'a_mid0': mid0, 'implied_move': mid0 / s0, 'a_rel_spread': (a['ca'] + a['pa'] - a['cb'] - a['pb']) / mid0, 'a_iv0': float(np.nanmean([a['civ'], a['piv']]))})
            credit = a['cb'] + a['pb']; t_in = v1.TICK(a['ca']) + v1.TICK(a['pa'])
            if es == ev:
                cost, t_out, fee_out = abs(se - k), 0.0, 0.0
            else:
                lc, lp = (_leg(ce, k, 'C'), _leg(ce, k, 'P')) if ce is not None and ce.height else (None, None)
                if lc is None or lp is None or not (lc['ask'] > 0 and lp['ask'] > 0): cost = None
                else: cost, t_out, fee_out = lc['ask'] + lp['ask'], v1.TICK(lc['ask']) + v1.TICK(lp['ask']), fee
            if cost is None: out['a_status'] = 'no two-sided exit quote at the event close'
            else:
                out['a_status'] = 'ok'
                out['a_pnl'] = (credit - cost - fee - fee_out) * 100
                out['a_pnl_adv'] = (credit - t_in - cost - t_out - fee - fee_out) * 100
                out['a_r'] = out['a_pnl'] / (mid0 * 100); out['a_r_adv'] = out['a_pnl_adv'] / (mid0 * 100)
        # V2b: long at P-5, out at P0 (same strike)
        b = v1.straddle(c5, s5) if c5 is not None and c5.height else None
        if b is None: out['b_status'] = 'no two-sided ATM straddle at P-5'
        else:
            k = b['strike']; mid5 = (b['cb'] + b['ca'] + b['pb'] + b['pa']) / 2
            lc, lp = (_leg(c0, k, 'C'), _leg(c0, k, 'P')) if c0 is not None and c0.height else (None, None)
            if lc is None or lp is None or not (lc['bid'] > 0 and lp['bid'] > 0): out['b_status'] = 'no two-sided exit quote at P0'
            else:
                debit = b['ca'] + b['pa']; proceeds = lc['bid'] + lp['bid']
                t_all = v1.TICK(b['ca']) + v1.TICK(b['pa']) + v1.TICK(lc['ask']) + v1.TICK(lp['ask'])
                out.update({'b_status': 'ok', 'b_K': k, 'b_mid5': mid5, 'b_rel_spread': (b['ca'] + b['pa'] - b['cb'] - b['pb']) / mid5,
                            'b_iv5': float(np.nanmean([b['civ'], b['piv']])), 'b_iv0': float(np.nanmean([lc['iv'], lp['iv']])),
                            'b_pnl': (proceeds - debit - 2 * fee) * 100, 'b_pnl_adv': (proceeds - debit - t_all - 2 * fee) * 100})
                out['b_r'] = out['b_pnl'] / (mid5 * 100); out['b_r_adv'] = out['b_pnl_adv'] / (mid5 * 100)
        rows.append(out)
    T = pl.DataFrame(rows, infer_schema_length=None)
    T = T.with_columns(pl.col('event').dt.truncate('1w').alias('week'))
    T.write_parquet(f'{OUT}/trades.parquet'); X = pl.DataFrame(excl); X.write_parquet(f'{OUT}/exclusions.parquet')
    print('events built', T.height, 'excluded', X.height)
    print(X.group_by(pl.col('reason').str.slice(0, 50)).agg(pl.len()).sort('len', descending=True))
    print(T.group_by('a_status').agg(pl.len()), T.group_by('b_status').agg(pl.len()))

def cboot(df, col, B=10000, seed=9):
    """mean per event, 95 % interval resampling event weeks"""
    d = df.filter(pl.col(col).is_finite())
    if d.height < 10: return d.height, float('nan'), float('nan'), float('nan'), float('nan')
    g = d.group_by('week').agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
    s, n = g['s'].to_numpy(), g['n'].to_numpy(); rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(B, len(s)))
    b = s[idx].sum(1) / n[idx].sum(1)
    p = 2 * min((b <= 0).mean(), (b >= 0).mean())
    return d.height, float(d[col].mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float(max(p, 1 / B))

def analyze(holdout=False):
    T = pl.read_parquet(f'{OUT}/trades.parquet')
    if not holdout: T = T.filter(pl.col('split') != 'holdout')
    sp_list = ['dev', 'val', 'devval'] + (['holdout'] if holdout else [])
    rows = []
    for col, lab in (('a_r', 'V2a short across the report'), ('a_r_adv', 'V2a, one tick worse'), ('b_r', 'V2b long into the report'), ('b_r_adv', 'V2b, one tick worse')):
        for sp in sp_list:
            d = T.filter(pl.col('split') != 'holdout') if sp == 'devval' else T.filter(pl.col('split') == sp)
            n, m, lo, hi, p = cboot(d, col)
            rows.append({'test': lab, 'split': sp, 'events': n, 'mean': m, 'lo': lo, 'hi': hi, 'p': p})
    R = pl.DataFrame(rows); R.write_csv(f'{OUT}/results{"_holdout" if holdout else ""}.csv')
    dv = T.filter(pl.col('split') != 'holdout')
    desc = []
    for lab, f in (('pre-market', pl.col('report_time') == 'premarket'), ('post-market', pl.col('report_time') == 'postmarket')):
        for col in ('a_r', 'b_r'):
            n, m, lo, hi, p = cboot(dv.filter(f), col); desc.append({'cut': lab, 'col': col, 'events': n, 'mean': m, 'lo': lo, 'hi': hi})
    for col, q in (('implied_move', 'a_r'), ('a_rel_spread', 'a_r'), ('b_rel_spread', 'b_r')):
        d = dv.filter(pl.col(col).is_finite() & pl.col(q).is_finite())
        if d.height < 30: continue
        d = d.with_columns(((pl.col(col).rank('ordinal') - 1) * 3 // d.height).alias('t3'))
        for k in range(3):
            n, m, lo, hi, p = cboot(d.filter(pl.col('t3') == k), q); desc.append({'cut': f'{col} tercile {k + 1}', 'col': q, 'events': n, 'mean': m, 'lo': lo, 'hi': hi})
    ok = dv.filter(pl.col('implied_move').is_finite() & pl.col('realised_move').is_finite())
    ratio = (ok['realised_move'] / ok['implied_move']).to_numpy()
    desc.append({'cut': 'realised / implied move, median', 'col': 'ratio', 'events': len(ratio), 'mean': float(np.median(ratio)), 'lo': float(np.quantile(ratio, 0.25)), 'hi': float(np.quantile(ratio, 0.75))})
    desc.append({'cut': 'share of reports moving more than implied', 'col': 'ratio', 'events': len(ratio), 'mean': float((ratio > 1).mean()), 'lo': float('nan'), 'hi': float('nan')})
    pl.DataFrame(desc).write_csv(f'{OUT}/descriptive{"_holdout" if holdout else ""}.csv')
    pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(220); pl.Config.set_float_precision(4)
    print(R); print(pl.DataFrame(desc))

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'plan': plan()
    elif cmd == 'fetch': fetch()
    elif cmd == 'build': build()
    elif cmd == 'analyze': analyze('--holdout' in sys.argv)
