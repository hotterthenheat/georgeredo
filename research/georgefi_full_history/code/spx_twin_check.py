"""Labelled SUBSTITUTION sensitivity for the 4 ledger rows whose OCC root is plain 'SPX' (UW returns no bars for that id).
The SPXW twin (same strike, same expiry, PM-settled weekly root) is fetched and the B-style fill simulation is repeated.
This is reported separately and is NOT part of the primary tables. Output: results/spx_root_substitution.csv
"""
import sys, os, csv
sys.path.insert(0, '/home/user/georgeredo/backtest')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import costs
costs.HALF_SPREAD.setdefault('SINGLE', 0.02)
rows = [r for r in C.load_ledger() if r['root'] == 'SPX']
out = []
for r in rows:
    twin = 'SPXW' + r['cid'][3:]
    bars = C.option_bars(twin, r['entry_date'])
    rec = dict(trade_id=r['trade_id'], epoch=r['epoch'], ticker=r['ticker'], original_cid=r['cid'], substituted_cid=twin, same_strike_expiry=True, entry_et=r['entry_dt'].strftime('%Y-%m-%d %H:%M'),
               exit_et=r['exit_dt'].strftime('%Y-%m-%d %H:%M') if r['exit_dt'] else '', size=r['size_n'], entry_premium=r['entry_px'], exit_premium=r['exit_px'], pnl_reported=r['pnl'],
               twin_n_bars=len(bars), bar_at_entry_minute=False, bar_at_exit_minute=False)
    eb = C.bar_at(bars, r['entry_dt']) if bars else None; xb = C.bar_at(bars, r['exit_dt']) if (bars and r['exit_dt']) else None
    rec['bar_at_entry_minute'] = eb is not None; rec['bar_at_exit_minute'] = xb is not None
    if eb: rec.update(entry_bar_low=eb['l'], entry_bar_high=eb['h'], entry_bar_vwap=C.vwap(eb), entry_inside=(eb['l'] - 1e-9 <= r['entry_px'] <= eb['h'] + 1e-9))
    if xb: rec.update(exit_bar_low=xb['l'], exit_bar_high=xb['h'], exit_bar_vwap=C.vwap(xb), exit_inside=(xb['l'] - 1e-9 <= r['exit_px'] <= xb['h'] + 1e-9))
    if bars:  # context: next bar after entry, last bar of the day (0DTE SPXW stops printing at 16:00, so a 16:00 exit has no bar)
        i, nb = C.first_bar_after(bars, r['entry_dt']); rec['next_bar_after_entry'] = nb['t'].strftime('%H:%M') if nb else ''; rec['next_bar_vwap'] = C.vwap(nb) if nb else ''
        rec['last_bar_of_day'] = bars[-1]['t'].strftime('%H:%M'); rec['last_bar_low'] = bars[-1]['l']; rec['last_bar_high'] = bars[-1]['h']; rec['last_bar_vwap'] = C.vwap(bars[-1])
        if eb and xb is None and r['exit_dt'] and r['exit_dt'] > bars[-1]['t']:  # exit after the last print: value at the last bar's VWAP (labelled alternative)
            ve = C.vwap(eb); vx = C.vwap(bars[-1]); sz = r['size_n']; hs = costs.HALF_SPREAD['SPX']
            rec['pnl_mid_exit_at_last_bar'] = (vx - ve) * 100 * sz; rec['pnl_spread_exit_at_last_bar'] = (vx * (1 - hs) - ve * (1 + hs)) * 100 * sz - 2 * costs.FEES * sz
            rec['pnl_adverse_exit_at_last_bar'] = (bars[-1]['l'] - eb['h']) * 100 * sz - 2 * costs.FEES * sz
    if eb and xb:
        hs = costs.HALF_SPREAD['SPX']; ve, vx = C.vwap(eb), C.vwap(xb); sz = r['size_n']
        rec['pnl_mid'] = (vx - ve) * 100 * sz; rec['pnl_spread'] = (vx * (1 - hs) - ve * (1 + hs)) * 100 * sz - 2 * costs.FEES * sz; rec['pnl_adverse'] = (xb['l'] - eb['h']) * 100 * sz - 2 * costs.FEES * sz
    out.append(rec)
cols = []
for o in out:
    for k in o:
        if k not in cols: cols.append(k)
with open(C.RES + '/spx_root_substitution.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(out)
for o in out: print(o)
