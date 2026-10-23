"""
preview.py — PREVIEW — 10 sessions, no verdict. Runs v0, V1-V4 and the four ablations of PREREG_COMPASS_ICT.md on the
ten sessions 2026-10-09 .. 2026-10-22, the 500 random-side draws at v0's entries, and writes out/preview.md, out/trades.csv.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

import ict

OUT = Path(__file__).resolve().parent / 'out'


STAGE = {'no HTF bias': 0, 'no sweep': 1, 'sweep without close-back': 2, 'no displacement + MSS': 3, 'no FVG': 4,
         'entry outside killzone': 5, 'no entry in window': 5, 'trade open': 6, 'session limit': 6, 'picker': 7}


def fmt(x, f='{:+.1f}'):
    return '—' if x is None or not np.isfinite(x) else f.format(x)


def summary(T):
    if not T:
        return dict(n=0)
    net = np.array([t['net'] for t in T])
    pct = np.array([t['pct'] for t in T]) * 100
    w, l_ = net[net > 0], net[net <= 0]
    return dict(n=len(T), win=100 * (net > 0).mean(), pct=pct.mean(), usd=net.mean(),
                aw=w.mean() if w.size else np.nan, al=l_.mean() if l_.size else np.nan,
                bp=np.mean([t['bp'] for t in T]), im=np.mean([t['im'] for t in T]))


def main():
    OUT.mkdir(exist_ok=True)
    res, sess = {}, {}
    for name, P in ict.VARIANTS.items():
        T, why = [], {}
        sess[name] = {}
        for d in ict.DAYS:
            t, w, *_ = ict.run_day(d, P)
            T += t
            if not t:
                k = max(w, key=lambda a: STAGE.get(a.split(':')[0], 9)) if w else 'no sweep'
                sess[name][k] = sess[name].get(k, 0) + 1
            for k, v in w.items():
                why[k] = why.get(k, 0) + v
        res[name] = (T, why)
    L = ['# PREVIEW — 10 sessions, no verdict', '',
         f'Sessions: {", ".join(ict.DAYS)}. Size 2 contracts; % = net ÷ debit; $ per 2-contract trade after fees.', '',
         '| row | trades | win % | mean %/trade | mean $/trade | avg win $ | avg loss $ | underlying bp | in 09:30 IMs | AM n / mean % | PM n / mean % |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for name, (T, why) in res.items():
        s = summary(T)
        kz = []
        for z in ('AM', 'PM'):
            Z = [t for t in T if t['kz'] == z]
            kz.append(f"{len(Z)} / {fmt(np.mean([t['pct'] for t in Z]) * 100) if Z else '—'}")
        if s['n'] == 0:
            L.append(f'| {name} | 0 | — | — | — | — | — | — | — | {kz[0]} | {kz[1]} |')
            continue
        L.append(f"| {name} | {s['n']} | {s['win']:.0f} | {fmt(s['pct'])} | {fmt(s['usd'])} | {fmt(s['aw'])} | {fmt(s['al'])} | "
                 f"{fmt(s['bp'])} | {fmt(s['im'], '{:+.2f}')} | {kz[0]} | {kz[1]} |")
    other = [t for t in res['A no killzones'][0] if t['kz'] == 'other']
    L += ['', f"('A no killzones' also has {len(other)} trades outside both killzones, mean "
              f"{fmt(np.mean([t['pct'] for t in other]) * 100) if other else '—'} %.)", '',
          '## No-trade reasons and exit reasons (counts over the ten sessions)', '']
    for name, (T, why) in res.items():
        ex = {}
        for t in T:
            ex[t['reason']] = ex.get(t['reason'], 0) + 1
        exs = ', '.join(f'{k} {v} ({100 * v / len(T):.0f}%)' for k, v in sorted(ex.items(), key=lambda a: -a[1])) or '—'
        ws = ', '.join(f'{k} {v}' for k, v in sorted(why.items(), key=lambda a: -a[1])) or '—'
        ns = sess[name]
        nss = ', '.join(f'{k} {v}' for k, v in sorted(ns.items(), key=lambda a: -a[1])) or '—'
        L.append(f'- **{name}** — sessions with no trade, by the furthest stage reached: {nss}. Setup-level counts: {ws}. '
                 f'Exits: {exs}.')
    # the random-side draws at v0's entries
    T0 = res['v0'][0]
    L += ['', '## v0 against 500 random-side draws at its entry times', '']
    if T0:
        alt = [ict.flip_trade(t['day'], ict.VARIANTS['v0'], t) for t in T0]
        rng = np.random.default_rng(20261023)
        same = np.array([t['pct'] for t in T0])
        flip = np.array([a['pct'] if a else np.nan for a in alt])
        draws = []
        for _ in range(500):
            f = rng.random(len(T0)) < 0.5
            x = np.where(f, flip, same)
            draws.append(np.nanmean(x))
        draws = np.array(draws)
        v = same.mean()
        pctile = 100 * ((draws < v).sum() + 0.5 * (draws == v).sum()) / draws.size
        L.append(f'v0 mean {v * 100:+.1f} % a trade over {len(T0)} trades; draws median {np.median(draws) * 100:+.1f} %, '
                 f'2.5–97.5th {np.percentile(draws, 2.5) * 100:+.1f} to {np.percentile(draws, 97.5) * 100:+.1f} %; '
                 f'**v0 at the {pctile:.0f}th percentile**. Flipped side with no qualifying contract: '
                 f'{int(np.isnan(flip).sum())} (left out of that draw\'s mean).')
    L += ['', 'No bootstrap: with 10 sessions an interval is meaningless. Nothing here is a finalist.']
    (OUT / 'preview.md').write_text('\n'.join(L) + '\n')
    with open(OUT / 'trades.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['row', 'day', 'entry', 'side', 'K', 'ask', 'delta', 'spread', 'sweep_ext', 'entry_u', 'tp1', 'tp2', 'exit',
                    'reason', 'net', 'pct', 'bp', 'im', 'kz'])
        for name, (T, _) in res.items():
            for t in T:
                w.writerow([name, t['day'], ict_mtxt(t['m']), 'C' if t['side'] > 0 else 'P', t['K'], round(t['ask'], 2), round(t['delta'], 3),
                            round(t['spread'], 4), round(t['ext'], 2), round(t['entry_u'], 2),
                            None if t['tp1'] is None else round(t['tp1'], 2), None if t['tp2'] is None else round(t['tp2'], 2),
                            ict_mtxt(t['exit_m']), t['reason'], round(t['net'], 2), round(t['pct'], 4), round(t['bp'], 1),
                            round(t['im'], 3), t['kz']])
    print('\n'.join(L))


def ict_mtxt(m):
    h, mm = divmod(570 + m, 60)
    return f'{h:02d}:{mm:02d}'


if __name__ == '__main__':
    main()
