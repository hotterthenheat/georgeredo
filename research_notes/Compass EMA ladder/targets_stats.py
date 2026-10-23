"""targets_stats.py — the preview table from out/targets_<month>.json. PREVIEW — one month each, no verdict."""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
print('| version | month | sessions | trades | skips | mean % after costs | mean $ | win rate | avg win | avg loss | exits target / stop / 15:58 | median hold (min) | mid-to-mid no fee | median abs delta | median premium (ask) | SPY / QQQ / IWM mean % |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
extra = []
for ver in ('E1', 'E2'):
    for mo in ('2025-02', '2025-03'):
        J = json.load(open(HERE / 'out' / f'targets_{mo}.json'))
        R = J[ver]
        T = R['trades']
        n = len(T)
        r = np.array([t['ret'] for t in T]); u = np.array([t['usd'] for t in T]); rm = np.array([t['ret_mid'] for t in T])
        w = r > 0
        sh = {k: sum(t['why'] == k for t in T) / n for k in ('target', 'stop', '15:58')}
        hold = np.median([t['x'] - t['m'] for t in T])
        de = np.array([t['delta'] for t in T], float); pr = np.array([t['ask'] for t in T])
        pn = []
        for nm in ('SPY', 'QQQ', 'IWM'):
            rn = np.array([t['ret'] for t in T if t['name'] == nm])
            pn.append(f'{100*rn.mean():+.2f}% ({rn.size})')
        sk = '; '.join(f'{a} {b}' for a, b in sorted(R['skips'].items(), key=lambda z: -z[1]))
        print(f'| {ver} | {mo} | {len(J["days"])} | {n} | {sk} | {100*r.mean():+.2f}% | {u.mean():+.2f} | {100*w.mean():.1f}% | '
              f'{100*r[w].mean():+.1f}% | {100*r[~w].mean():+.1f}% | {100*sh["target"]:.0f}% / {100*sh["stop"]:.0f}% / {100*sh["15:58"]:.1f}% | '
              f'{hold:.0f} | {100*np.nanmean(rm):+.2f}% | {np.nanmedian(de):.2f} | ${np.median(pr):.2f} | {" / ".join(pn)} |')
        # descriptive: by exit reason
        for k in ('target', 'stop', '15:58'):
            rk = np.array([t['ret'] for t in T if t['why'] == k])
            if rk.size:
                extra.append(f'{ver} {mo} {k}: {rk.size} trades, mean {100*rk.mean():+.2f}%, win {100*(rk>0).mean():.1f}%')
        gap = np.array([(t['T'] - t['close_in']) / t['close_in'] for t in T])
        extra.append(f'{ver} {mo} target distance (T - close)/close median {100*np.median(gap):.1f}%; '
                     f'breaks with no EMA above {R["breaks_no_ema_above"]}')
print()
print('\n'.join(extra))
