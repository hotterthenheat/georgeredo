"""T3 supplement: stricter opening-range break definitions on the underlying only (no options). Writes csv/t3_orb_variants.csv and prints a table."""
import os, sys, collections, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
DEFS = {'close_beyond': dict(buf=0.0, confirm=1), 'buffer_0.05pct': dict(buf=0.0005, confirm=1), 'buffer_0.10pct': dict(buf=0.001, confirm=1), 'buffer_0.25pct': dict(buf=0.0025, confirm=1), '3_closes_beyond': dict(buf=0.0, confirm=3), 'buffer_0.10pct_3closes': dict(buf=0.001, confirm=3)}
rows = []
for tk in C.TICKERS:
    for d in C.SEL:
        rth, _ = C.ubars(tk, d)
        if len(rth) < 300: continue
        orb = [b for b in rth if C.hm(b['t']) < 585]; orh = max(b['h'] for b in orb); orl = min(b['l'] for b in orb)
        cl = C.px_before(rth, 956)
        for name, p in DEFS.items():
            ev = None
            for i in range(len(rth)):
                if C.hm(rth[i]['t']) < 585 or i < p['confirm'] - 1: continue
                win = rth[i - p['confirm'] + 1:i + 1]
                if all(b['c'] > orh * (1 + p['buf']) for b in win): ev = ('UP', i); break
                if all(b['c'] < orl * (1 - p['buf']) for b in win): ev = ('DN', i); break
            if ev is None or C.hm(rth[ev[1]]['t']) >= 900: continue
            side, i = ev; s = 1 if side == 'UP' else -1; c0 = rth[i]['c']; j30 = min(i + 30, len(rth) - 1); j60 = min(i + 60, len(rth) - 1)
            inside = (lambda b: b['c'] < orh) if side == 'UP' else (lambda b: b['c'] > orl)
            rows.append(dict(definition=name, ticker=tk, date=d, side=side, break_t=C.mstr(C.hm(rth[i]['t'])), ret30=s * (rth[j30]['c'] / c0 - 1) * 1e4, ret60=s * (rth[j60]['c'] / c0 - 1) * 1e4, ret_close=s * (cl / c0 - 1) * 1e4, back_inside30=int(any(inside(b) for b in rth[i + 1:i + 31]))))
C.write_csv(C.CSV + '/t3_orb_variants.csv', rows)
print('| definition | n (ticker-days with a break before 15:00) | median break time | mean +30m bp [CI] | cont. +30m | mean +60m bp | cont. +60m | mean to 15:55 bp [CI] | cont. close | back inside OR <=30m |')
print('|---|---|---|---|---|---|---|---|---|---|')
for name in DEFS:
    g = [r for r in rows if r['definition'] == name]
    r30 = np.array([r['ret30'] for r in g]); r60 = np.array([r['ret60'] for r in g]); rc = np.array([r['ret_close'] for r in g]); cl = [r['date'] for r in g]
    lo, hi = C.boot_ci(rc, cl); l30, h30 = C.boot_ci(r30, cl)
    print(f"| {name} | {len(g)} | {sorted(r['break_t'] for r in g)[len(g)//2]} | {r30.mean():.1f} [{l30:.1f},{h30:.1f}] | {100*(r30>0).mean():.0f}% | {r60.mean():.1f} | {100*(r60>0).mean():.0f}% | {rc.mean():.1f} [{lo:.1f},{hi:.1f}] | {100*(rc>0).mean():.0f}% | {100*np.mean([r['back_inside30'] for r in g]):.0f}% |")
