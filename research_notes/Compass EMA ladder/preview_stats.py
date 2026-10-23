"""preview_stats.py — the preview table from out/preview_2025-03.json. PREVIEW — one month, no verdict."""
import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
J = json.load(open(HERE / 'out' / 'preview_2025-03.json'))
LAB = {'V1': 'EMA9 L1 (preview base)', 'V2': 'EMA9 L2', 'V3': 'EMA9 L3', 'V4': 'EMA20 L1', 'V5': 'EMA20 L2', 'V6': 'EMA20 L3',
       'V7': 'base + GEX < 0', 'V8': 'base + net premium side', 'V9': 'base + both filters', 'V10': 'base + 14:00 exit',
       'V11': 'base + spread <= 10%', 'V12': 'base + spread <= 3%', 'V13': 'base in the ATM contract'}
nd = len(J['days'])
rows = []
for v, T in J['trades'].items():
    n = len(T)
    if n == 0:
        rows.append(f'| {v} | {LAB[v]} | 0 | | | | | | | | | | |'); continue
    r = np.array([t['ret'] for t in T]); u = np.array([t['usd'] for t in T]); rm = np.array([t['ret_mid'] for t in T])
    w = r > 0
    why = {k: sum(t['why'] == k for t in T) / n for k in ('signal', '15:58', '14:00')}
    ex = '; '.join(f'{k} {100*x:.0f}%' for k, x in why.items() if x > 0)
    de = np.array([t['delta'] for t in T], float); pr = np.array([t['ask'] for t in T])
    dtxt = '—' if not np.isfinite(de).any() else f'{np.nanmedian(de):.2f} ({np.nanpercentile(de,25):.2f}–{np.nanpercentile(de,75):.2f})'
    rows.append(f'| {v} | {LAB[v]} | {n} | {n/nd:.1f} | {100*r.mean():+.2f}% | {u.mean():+.2f} | {100*w.mean():.1f}% | '
                f'{100*r[w].mean() if w.any() else float("nan"):+.1f}% | {100*r[~w].mean():+.1f}% | {ex} | {100*rm.mean():+.2f}% | '
                f'{dtxt} | ${np.median(pr):.2f} ({np.percentile(pr,25):.2f}–{np.percentile(pr,75):.2f}) |')
print(f'sessions {nd}')
print('| id | version | trades | per session | mean % after costs | mean $ | win rate | avg win | avg loss | exits | mid-to-mid no fee | |delta| median (IQR) | premium (ask) median (IQR) |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
print('\n'.join(rows))
print()
for v, nt in J['no_trade'].items():
    print(v, nt)
# per name, V1
for v in ('V1', 'V13'):
    for nm in ('SPY', 'QQQ', 'IWM'):
        T = [t for t in J['trades'][v] if t['name'] == nm]
        r = np.array([t['ret'] for t in T]); u = np.array([t['usd'] for t in T])
        print(v, nm, len(T), f'{100*r.mean():+.2f}%', f'{u.mean():+.2f}')
