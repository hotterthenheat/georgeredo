"""Step 1: fetch Unusual Whales 1-minute bars for every ledger/paper row and write results/bar_coverage.csv.

Option rows: contract bars (option-contract/{cid}/intraday?date=) for the ET entry date and, for multi-day holds,
every trading day through the exit date. SHARES rows: underlying 1-minute bars for entry and exit dates.
Run:  set -a; . "$SP/secrets/research.env"; set +a; export BT_CACHE="$SP/bt/cache"; python3 -I fetch_bars.py
"""
import sys, os, csv, json, time, datetime, collections, concurrent.futures as cf
sys.path.insert(0, '/home/user/georgeredo/backtest')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

WORKERS = 3  # UW concurrency limit (429 concurrent_limit_exceeded above 3)
t0 = time.time()
rows = C.load_all()
TD = C.trading_days()
tdset = set(TD)

def days_between(d0, d1):
    """Trading days from d0 through d1 inclusive (ISO strings); falls back to [d0, d1] if a date is not in the calendar."""
    if d1 is None or d1 <= d0: return [d0]
    ds = [d for d in TD if d0 <= d <= d1]
    if d0 not in tdset: ds = [d0] + ds
    if d1 not in tdset: ds = ds + [d1]
    return sorted(set(ds))

tasks = {}
for r in rows:
    if r['is_option'] and r['cid']:
        for d in days_between(r['entry_date'], r['exit_date']):
            tasks[('opt', r['cid'], d)] = None
    elif r['is_shares']:
        for d in sorted(set([r['entry_date']] + ([r['exit_date']] if r['exit_date'] else []))):
            tasks[('und', r['ticker'], d)] = None
print(f'rows={len(rows)} unique fetch tasks={len(tasks)}', flush=True)

def fetch(key):
    kind, ident, date = key
    if kind == 'opt': p = C.option_payload(ident, date)
    else: p = C.underlying_payload(ident, date)
    if not isinstance(p, dict): return key, dict(status='bad_payload', n=0)
    if 'error' in p: return key, dict(status=f'http_{p["error"]}', n=0)
    n = len(p.get('data') or [])
    return key, dict(status='ok' if n else 'empty_payload', n=n)

done = 0
with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for key, res in ex.map(fetch, list(tasks.keys())):
        tasks[key] = res; done += 1
        if done % 100 == 0: print(f'  {done}/{len(tasks)} fetched  {time.time() - t0:.0f}s  stats={C.data.STATS}', flush=True)
print(f'fetch done in {time.time() - t0:.0f}s stats={C.data.STATS}', flush=True)

# per-row coverage
out = []
for r in rows:
    rec = dict(group=r['group'], epoch=r['epoch'], book=r['book'], trade_id=r['trade_id'], ticker=r['ticker'], root=r['root'],
               account_type=r['account_type'], side=r['side'], cid=r['cid'], entry_date=r['entry_date'], exit_date=r['exit_date'] or '',
               month=r['month'], is_0dte=r['dte0'], data_error=r['data_err'], pnl_mismatch=r['mismatch'], pnl_reported=r['pnl'],
               multi_day=bool(r['exit_date'] and r['exit_date'] > r['entry_date']))
    kind = 'opt' if r['is_option'] else ('und' if r['is_shares'] else None)
    ident = r['cid'] if r['is_option'] else r['ticker']
    if kind is None or (kind == 'opt' and not ident):
        rec.update(bars_available=False, n_bars=0, http_error='', bars_available_exit_day=False, n_bars_exit_day=0, http_error_exit='',
                   days_needed=0, days_available=0, bar_at_entry_minute=False, bar_at_exit_minute=False, entry_minute_vol='', missing_reason='no_occ')
        out.append(rec); continue
    days = days_between(r['entry_date'], r['exit_date']) if kind == 'opt' else sorted(set([r['entry_date']] + ([r['exit_date']] if r['exit_date'] else [])))
    st = {d: tasks[(kind, ident, d)] for d in days}
    e = st[r['entry_date']]; x = st[r['exit_date']] if r['exit_date'] else dict(status='no_exit_time', n=0)
    rec['bars_available'] = e['status'] == 'ok'; rec['n_bars'] = e['n']; rec['http_error'] = e['status'] if e['status'].startswith('http_') else ''
    rec['bars_available_exit_day'] = x['status'] == 'ok'; rec['n_bars_exit_day'] = x['n']; rec['http_error_exit'] = x['status'] if x['status'].startswith('http_') else ''
    rec['days_needed'] = len(days); rec['days_available'] = sum(1 for d in days if st[d]['status'] == 'ok')
    # bar at entry / exit minute
    if rec['bars_available']:
        bars = C.option_bars(ident, r['entry_date']) if kind == 'opt' else C.underlying_bars(ident, r['entry_date'])
        eb = C.bar_at(bars, r['entry_dt'])
        rec['bar_at_entry_minute'] = eb is not None; rec['entry_minute_vol'] = eb['vol'] if eb else ''
    else:
        rec['bar_at_entry_minute'] = False; rec['entry_minute_vol'] = ''
    if rec['bars_available_exit_day'] and r['exit_dt']:
        xbars = bars if r['exit_date'] == r['entry_date'] else (C.option_bars(ident, r['exit_date']) if kind == 'opt' else C.underlying_bars(ident, r['exit_date']))
        rec['bar_at_exit_minute'] = C.bar_at(xbars, r['exit_dt']) is not None
    else:
        rec['bar_at_exit_minute'] = False
    if e['status'] == 'ok': reason = 'ok'
    elif e['status'] == 'empty_payload' and r['root'] == 'SPX': reason = 'no bars (SPX root)'
    elif e['status'] == 'empty_payload': reason = 'empty_payload'
    elif e['status'].startswith('http_'): reason = e['status']
    else: reason = e['status']
    if reason == 'ok' and r['data_err']: reason = 'ok (data_error row)'
    rec['missing_reason'] = reason
    out.append(rec)

cols = list(out[0].keys())
with open(C.RES + '/bar_coverage.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(out)

# summary
def tab(keyf, title):
    g = collections.OrderedDict()
    for o in out:
        k = keyf(o); g.setdefault(k, []).append(o)
    lines = [f'### {title}', '', '| key | rows | entry-day bars | exit-day bars | bar at entry min | bar at exit min | all days (multi-day) | sum reported P&L (rows w/o entry bars) |', '|---|---|---|---|---|---|---|---|']
    for k in sorted(g, key=lambda z: str(z)):
        v = g[k]
        lines.append(f'| {k} | {len(v)} | {sum(1 for o in v if o["bars_available"])} | {sum(1 for o in v if o["bars_available_exit_day"])} | {sum(1 for o in v if o["bar_at_entry_minute"])} | {sum(1 for o in v if o["bar_at_exit_minute"])} | {sum(1 for o in v if o["days_needed"] and o["days_available"] == o["days_needed"])}/{sum(1 for o in v if o["days_needed"])} | {sum((o["pnl_reported"] or 0) for o in v if not o["bars_available"]):,.0f} |')
    return '\n'.join(lines) + '\n'

md = ['# Bar coverage (Unusual Whales 1-minute contract/underlying bars)', '',
      f'Rows: {len(out)} (ledger {sum(1 for o in out if o["group"] == "ledger")}, paper {sum(1 for o in out if o["group"] == "paper")}); unique (contract, day) fetches: {len(tasks)}; '
      f'cache hits {C.data.STATS["hits"]}, misses {C.data.STATS["misses"]}, request errors {C.data.STATS["errors"]}; runtime {time.time() - t0:.0f}s.', '',
      f'Earliest ledger date {min(o["entry_date"] for o in out)}; earliest date with contract bars available: {min((o["entry_date"] for o in out if o["bars_available"] and o["side"] != "SHARES"), default="n/a")}.', '']
md.append(tab(lambda o: (o['group'], o['epoch'], o['book']), 'By group / epoch / book'))
md.append(tab(lambda o: (o['epoch'], o['account_type'], o['side']), 'By epoch / account type / side'))
md.append(tab(lambda o: o['root'], 'By ticker root'))
md.append(tab(lambda o: (o['epoch'], o['month']), 'By epoch / month'))
md.append('### Reason for missing entry-day bars\n\n| epoch | reason | rows | sum reported P&L |\n|---|---|---|---|')
g = collections.Counter(); s = collections.Counter()
for o in out:
    g[(o['epoch'], o['missing_reason'])] += 1; s[(o['epoch'], o['missing_reason'])] += (o['pnl_reported'] or 0)
for k in sorted(g): md.append(f'| {k[0]} | {k[1]} | {g[k]} | {s[k]:,.0f} |')
md.append('\n### Task status counts\n')
md.append('| status | tasks |\n|---|---|')
for k, v in sorted(collections.Counter(t['status'] for t in tasks.values()).items()): md.append(f'| {k} | {v} |')
open(C.RES + '/bar_coverage_summary.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(md[-30:]))
print('wrote', C.RES + '/bar_coverage.csv', 'and bar_coverage_summary.md')
