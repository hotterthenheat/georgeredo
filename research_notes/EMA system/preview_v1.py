"""
preview_v1.py — runs RULEBOOK_v1.md on the three weeks drawn by select_weeks_v1.py (out_v1/weeks.json) and writes the
tables of PREVIEW_v1_weeks.md (out_v1/tables.md), the trade list (out_v1/trades_v1.csv) and small summaries.
PREVIEW — 15 sessions, no verdict.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

import ema_system as E
import ema_v1 as V

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out_v1'
LBL = '**PREVIEW — 15 sessions, no verdict.**'
S = E.S

W = json.loads((OUT / 'weeks.json').read_text())
KINDS = [k for k in ('up', 'flat', 'down') if W['picks'][k]]
WEEKS = {k: tuple(W['picks'][k]['days']) for k in KINDS}
RET = {k: W['picks'][k]['ret'] for k in KINDS}
PERIODS = KINDS + ['pooled']
CFGS, EXITS = ('A', 'B'), E.EXITS


def money(x):
    return '—' if x is None or not np.isfinite(x) else (f'−${abs(x):,.0f}' if x < 0 else f'+${x:,.0f}')


def money2(x):
    return '—' if x is None or not np.isfinite(x) else (f'−${abs(x):,.2f}' if x < 0 else f'+${x:,.2f}')


def pct(x, d=1):
    return '—' if x is None or not np.isfinite(x) else (f'−{abs(100 * x):.{d}f}%' if x < 0 else f'+{100 * x:.{d}f}%')


def per(D, k, period):
    return D[k][period] if period != 'pooled' else [t for p in KINDS for t in D[k][p]]


def st(T):
    n = len(T)
    if not n:
        return dict(n=0)
    net = np.array([t['net'] for t in T])
    cost = sum(t['cost'] for t in T)
    big = max(T, key=lambda t: abs(t['net']))
    tot = float(net.sum())
    return dict(n=n, net=tot, exp=tot / n, prem=tot / cost, win=float((net > 0).mean()),
                calls=sum(t['side'] > 0 for t in T), puts=sum(t['side'] < 0 for t in T),
                big=abs(big['net']) / abs(tot) if tot != 0 else np.inf, fees=float(sum(t['fees'] for t in T)),
                hs=float(sum(t.get('halfspread', np.nan) for t in T)), cost=cost,
                spy=sum(t.get('venue') == 'SPY' for t in T), spxw=sum(t.get('venue') == 'SPXW' for t in T),
                reasons={r: sum(t['reason'] == r for t in T) for r in ('stop', '+1R', '+2R', 'runner', '14:00', 'flat')})


HEAD = ('| | trades | net $ | net $/trade | net % of premium | win (after costs) | calls / puts | largest trade ÷ |total| | '
        'fees ($, % prem) | half-spreads ($, % prem) | S&P venue SPY / SPXW |\n|---|---|---|---|---|---|---|---|---|---|---|')


def row(label, s):
    if s['n'] == 0:
        return f'| {label} | 0 |' + ' — |' * 10
    bg = '—' if not np.isfinite(s['big']) else f"{100 * s['big']:.0f}%"
    hs = f"{money(-s['hs'])}, {pct(s['hs'] / s['cost'], 2)}" if np.isfinite(s['hs']) else '—'
    return (f"| {label} | {s['n']} | {money(s['net'])} | {money2(s['exp'])} | {pct(s['prem'])} | {100 * s['win']:.0f}% | "
            f"{s['calls']} / {s['puts']} | {bg} | {money(-s['fees'])}, {pct(s['fees'] / s['cost'], 2)} | {hs} | "
            f"{s['spy']} / {s['spxw']} |")


def boot(T, days, draws=2000, seed=2026102311):
    Sx = np.array([sum(t['net'] for t in T if t['day'] == d) for d in days])
    Nx = np.array([sum(1 for t in T if t['day'] == d) for d in days], float)
    if Nx.sum() == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(days), size=(draws, len(days)))
    ss, nn = Sx[idx].sum(1), Nx[idx].sum(1)
    v = ss[nn > 0] / nn[nn > 0]
    return Sx.sum() / Nx.sum(), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def main():
    H, SK, CH, BC, BA, V0 = ({} for _ in range(6))
    for cfg in CFGS:
        for x in EXITS:
            k = (cfg, x)
            H[k], SK[k], CH[k], V0[k] = {}, {}, {}, {}
            for p in KINDS:
                H[k][p], SK[k][p] = V.run_week(WEEKS[p], cfg, x)
                CH[k][p], _ = V.run_week(WEEKS[p], cfg, x, chop=True)
                V0[k][p] = V.run_v0_week(WEEKS[p], cfg, x)
        BC[cfg] = {p: V.run_week(WEEKS[p], cfg, 'X2', 'cross')[0] for p in KINDS}
        BA[cfg] = {p: V.run_week(WEEKS[p], cfg, 'X2', 'align')[0] for p in KINDS}
        print('ran', cfg, flush=True)
    RB = {}
    for cfg in CFGS:
        for x in EXITS:
            RB[(cfg, x)] = V.random_baseline([WEEKS[p] for p in KINDS], [H[(cfg, x)][p] for p in KINDS], x)
            print('random', cfg, x, flush=True)

    # trade list (headline) for the verifier
    keys = ['week', 'cfg', 'exit', 'stream', 'venue', 'day', 'entry', 'm', 'side', 'right', 'K', 'ask', 'bid_in', 'spread', 'delta',
            'oi', 'pvol', 'cs_spy', 'cs_spxw', 'spx', 'qty', 'entry_u', 'level', 'R', 'exit_m', 'hold', 'reason', 'exit_u',
            'gross', 'fees', 'halfspread', 'net', 'cost', 'mfe', 'mae', 'legs']
    with open(OUT / 'trades_v1.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(keys)
        for k in sorted(H):
            for p in KINDS:
                for t in H[k][p]:
                    t['week'] = p
                    w.writerow([t[c] if c != 'legs' else ';'.join(f'{q}@{S.mtxt(ex)}:{px:.2f}:{why}' for q, ex, px, why in t['legs'])
                                for c in keys])

    L = []
    P = L.append
    chop_days = {}
    for p in KINDS:
        for st_ in V.STREAMS:
            X = V.series(st_, WEEKS[p])
            for d in WEEKS[p]:
                chop_days[(V.LABEL[st_], d)] = V.chop_day(X, X.di(d))
    summ = {}

    P('## 2. The headline (v1 as written), by week and pooled\n')
    P(LBL + ' Three streams (S&P on SPY\'s bars, priced in SPY or SPXW; QQQ; IWM). 1 contract (X4: 10). Win = net > 0 after '
      'fees and spreads. Largest trade = the trade with the largest |net|, as a share of |the row\'s net total|. Half-spreads: '
      '(ask − mid) at entry plus (mid − bid) on each exit row (CALCULATED).\n')
    for p in PERIODS:
        lab = (f"{p} week {WEEKS[p][0]} → {WEEKS[p][4]} (SPY {pct(RET[p], 2)})" if p != 'pooled' else 'pooled (15 sessions)')
        P(f'### {lab}\n')
        P(HEAD)
        for cfg in CFGS:
            for x in EXITS:
                s = st(per(H, (cfg, x), p))
                summ[(p, cfg, x)] = s
                P(row(f'{cfg} · {x}', s))
        P('')
    P('How the headline trades ended (pooled; X4 counts a trade once, by its last leg or "stop" if any leg stopped):\n')
    P('| config · exit | stop | +1R | +2R | runner | 14:00 |\n|---|---|---|---|---|---|')
    for cfg in CFGS:
        for x in EXITS:
            s = summ[('pooled', cfg, x)]
            P(f'| {cfg} · {x} | ' + ' | '.join(str(s['reasons'][r]) for r in ('stop', '+1R', '+2R', 'runner', '14:00')) + ' |')
    P('')

    P('## 3. By stream (pooled)\n')
    P(LBL + '\n')
    P(HEAD)
    for cfg in CFGS:
        for x in EXITS:
            for lab in ('S&P', 'QQQ', 'IWM'):
                P(row(f'{cfg} · {x} · {lab}', st([t for t in per(H, (cfg, x), 'pooled') if t['stream'] == lab])))
    P('')
    P('The S&P stream by venue (pooled):\n')
    P(HEAD)
    for cfg in CFGS:
        for x in EXITS:
            for vn in ('SPY', 'SPXW'):
                P(row(f'{cfg} · {x} · S&P in {vn}', st([t for t in per(H, (cfg, x), 'pooled') if t['stream'] == 'S&P' and t['venue'] == vn])))
    P('')

    P('## 4. Tracked variants (not the headline)\n')
    P(LBL + ' V-chop: no entries from 10:30 on a chop day (RULEBOOK_v1 §3). V-noIWM: the headline less IWM. V-calls / '
      'V-puts: the headline split by side.\n')
    P('Chop days (first-hour range below its 60-session p33 and the 10:30 price in the middle half): ' +
      '; '.join(f"{lab}: " + (', '.join(d for (l2, d), v in sorted(chop_days.items()) if l2 == lab and v) or 'none')
                for lab in ('S&P', 'QQQ', 'IWM')) + '.\n')
    for p in PERIODS:
        lab = (f"{p} week {WEEKS[p][0]}" if p != 'pooled' else 'pooled (15 sessions)')
        P(f'### {lab}\n')
        P(HEAD)
        for cfg in CFGS:
            for x in EXITS:
                Hs = per(H, (cfg, x), p)
                P(row(f'{cfg} · {x} · V-chop', st(per(CH, (cfg, x), p))))
                P(row(f'{cfg} · {x} · V-noIWM', st([t for t in Hs if t['stream'] != 'IWM'])))
                P(row(f'{cfg} · {x} · V-calls', st([t for t in Hs if t['side'] > 0])))
                P(row(f'{cfg} · {x} · V-puts', st([t for t in Hs if t['side'] < 0])))
        P('')

    P('## 5. Session bootstrap on the pooled 15 sessions\n')
    P(LBL + ' iid over the 15 sessions (a session with no trade counts as zero trades), 2,000 draws, seed 2026102311, net '
      'per trade = Σ net ÷ Σ trades of the drawn sessions, 2.5–97.5% percentiles. Fifteen sessions from three hand-labelled '
      'regimes: the interval shows how wide this is, not a test.\n')
    alld = [d for p in KINDS for d in WEEKS[p]]
    P('| config · exit | headline net/trade | 95% | V-noIWM net/trade | 95% |\n|---|---|---|---|---|')
    for cfg in CFGS:
        for x in EXITS:
            Hs = per(H, (cfg, x), 'pooled')
            a = boot(Hs, alld); b = boot([t for t in Hs if t['stream'] != 'IWM'], alld)
            P(f'| {cfg} · {x} | {money2(a[0])} | [{money2(a[1])}, {money2(a[2])}] | {money2(b[0])} | [{money2(b[1])}, {money2(b[2])}] |')
    P('')

    P('## 6. Random-entry baseline (headline, every config × exit)\n')
    P(LBL + ' 500 seeded trials (seed 2026102312, one generator a config × exit). Per trial, per week, per stream: the headline\'s '
      'count of that stream that week; session uniform over the week; minute drawn from the headline\'s entry minutes that week; '
      'put with the headline\'s put share that week; the trade built exactly as a headline trade (stop from the last 5 bars, '
      'contract picker, 3% veto, venue rule, the exit variant, the 14:00 sell); no risk rules; a draw with no trade redrawn up to '
      '50 times. Percentile = share of trials whose total is below the headline\'s total.\n')
    P('| config · exit | period | headline total | headline $/trade | random total: mean [5%, 95%] | random $/trade: mean [5%, 95%] | '
      'headline percentile |\n|---|---|---|---|---|---|---|')
    rsum = {}
    for cfg in CFGS:
        for x in EXITS:
            rb = RB[(cfg, x)]
            for j, p in enumerate(PERIODS):
                tot = rb['tot'][:, j] if p != 'pooled' else rb['tot'].sum(1)
                nn = rb['n'][:, j] if p != 'pooled' else rb['n'].sum(1)
                s = summ[(p, cfg, x)]
                if s['n'] == 0:
                    P(f'| {cfg} · {x} | {p} | 0 trades | — | — | — | — |')
                    continue
                pt = tot / np.maximum(nn, 1)
                q = float((tot < s['net']).mean())
                rsum[(p, cfg, x)] = dict(q=q, mean_pt=float(pt.mean()), mean_tot=float(tot.mean()))
                P(f"| {cfg} · {x} | {p} | {money(s['net'])} | {money2(s['exp'])} | {money(tot.mean())} "
                  f"[{money(np.percentile(tot, 5))}, {money(np.percentile(tot, 95))}] | {money2(pt.mean())} "
                  f"[{money2(np.percentile(pt, 5))}, {money2(np.percentile(pt, 95))}] | {100 * q:.0f}th |")
            if rb['fails']:
                P(f'| {cfg} · {x} | (draws that found no trade in 50 tries: {rb["fails"]}) | | | | | |')
    P('')

    P('## 7. Crossover and alignment-only baselines (X2, under v1\'s trading rules)\n')
    P(LBL + ' (a) the 1m EMA crossover (A: EMA5/15, B: EMA9/21); (b) the 15m bias + the config\'s 5m alignment turning on; '
      'both on the three streams with the 3% veto, the venue rule, entries 09:45–13:29, the X2 exit, the 14:00 flat and v0\'s '
      'risk rules.\n')
    P(HEAD)
    for p in PERIODS:
        for cfg in CFGS:
            P(row(f'{p} · {cfg} · headline X2', summ[(p, cfg, 'X2')]))
            P(row(f'{p} · {cfg} · (a) crossover', st(BC[cfg][p] if p != 'pooled' else [t for q in KINDS for t in BC[cfg][q]])))
            P(row(f'{p} · {cfg} · (b) alignment only', st(BA[cfg][p] if p != 'pooled' else [t for q in KINDS for t in BA[cfg][q]])))
    P('')

    P('## 8. v0 as written beside v1, on the same weeks\n')
    P(LBL + ' v0 = RULEBOOK_v0 run by its own unchanged code (ema_system.run_day): SPXW on SPX prints (no RVOL, time-weighted '
      'VWAP), SPY, QQQ, IWM as four streams, 12% veto, entries to 15:30, 15:58 flat; each week with its own 60-day warm-up.\n')
    P('| config · exit | period | v0 trades | v0 net | v0 $/trade | v0 % prem | v0 win | v1 trades | v1 net | v1 $/trade | v1 % prem | v1 win |\n'
      '|---|---|---|---|---|---|---|---|---|---|---|---|')
    v0s = {}
    for cfg in CFGS:
        for x in EXITS:
            for p in PERIODS:
                a = st(per(V0, (cfg, x), p)); b = summ[(p, cfg, x)]
                v0s[(p, cfg, x)] = a
                f = lambda s: (f"{s['n']} | {money(s['net'])} | {money2(s['exp'])} | {pct(s['prem'])} | {100 * s['win']:.0f}%"  # noqa: E731
                               if s['n'] else '0 | — | — | — | —')
                P(f'| {cfg} · {x} | {p} | {f(a)} | {f(b)} |')
    P('')
    P('v0 as written without its SPXW stream (SPY, QQQ, IWM), pooled — v0\'s SPXW stream has no counterpart in v1:\n')
    P('| config · exit | trades | net | $/trade | % prem | win |\n|---|---|---|---|---|---|')
    for cfg in CFGS:
        for x in EXITS:
            a = st([t for t in per(V0, (cfg, x), 'pooled') if t['name'] != 'SPXW'])
            P(f"| {cfg} · {x} | {a['n']} | {money(a['net'])} | {money2(a['exp'])} | {pct(a['prem'])} | {100 * a['win']:.0f}% |" if a['n']
              else f'| {cfg} · {x} | 0 | — | — | — | — |')
    P('')

    P('## 9. Signals without a trade, by reason (headline)\n')
    P(LBL + ' A minute whose rule held while no position was open but no trade could be built (each such minute counted).\n')
    P('| config · exit | period | S&P | QQQ | IWM |\n|---|---|---|---|---|')
    for cfg in CFGS:
        for x in EXITS:
            for p in KINDS:
                k = SK[(cfg, x)][p]
                cells = []
                for lab in ('S&P', 'QQQ', 'IWM'):
                    c = {a: b for (n2, a), b in k.items() if n2 == lab}
                    cells.append(', '.join(f'{a}: {b}' for a, b in sorted(c.items())) or '0')
                P(f'| {cfg} · {x} | {p} | ' + ' | '.join(cells) + ' |')
    P('')

    (OUT / 'tables.md').write_text('\n'.join(L) + '\n')
    js = {f'{p}|{cfg}|{x}': dict(v1={k: v for k, v in summ[(p, cfg, x)].items() if k != 'reasons'},
                                 v0={k: v for k, v in v0s[(p, cfg, x)].items() if k != 'reasons'},
                                 rand=rsum.get((p, cfg, x)))
          for p in PERIODS for cfg in CFGS for x in EXITS}
    (OUT / 'summary.json').write_text(json.dumps(js, indent=1, default=float))
    print('tables written')


if __name__ == '__main__':
    main()
