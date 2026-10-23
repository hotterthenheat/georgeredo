"""
summarize.py — the exploration's per-row statistics (prereg section 4's list as the owner gave it, Amendment 1's
finalist rule applied mechanically) from explore.py's tables. Writes out/exploration_tables.md and
out/exploration_summary.json. Reads no market file.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402
import explore as E  # noqa: E402

OUT = HERE / 'out'
ROWS = list(E.ict.VARIANTS)
CANDIDATES = [r for r in ROWS if r != 'v0']


def hm(m):
    h, mm = divmod(570 + int(m), 60)
    return f'{h:02d}:{mm:02d}'


def f(x, fm='{:+.1f}'):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else fm.format(x)


def ci(t, fm='{:+.1f}'):
    return AL.ci(t, fm)


def block(T: pl.DataFrame, days: list[str]) -> dict:
    """every statistic for the trades T over the sessions `days` (calendar order, zero where no trade)"""
    n = T.height
    o = dict(trades=n, sessions=len(days), rate=n / len(days) if days else float('nan'))
    if n == 0:
        return o
    per = T.group_by('day').agg(pl.len().alias('N'), pl.col('pct').sum().alias('P'), pl.col('net').sum().alias('U'),
                                pl.col('bp').fill_nan(None).sum().alias('BP'))
    mp = {r['day']: r for r in per.iter_rows(named=True)}
    N = np.array([mp[d]['N'] if d in mp else 0 for d in days], float)
    P = np.array([mp[d]['P'] if d in mp else 0.0 for d in days]) * 100
    U = np.array([mp[d]['U'] if d in mp else 0.0 for d in days])
    sp = AL.session_stats(P, N, blocks=(20,))
    su = AL.session_stats(U, N, blocks=(20,))
    net, pct = T['net'].to_numpy(), T['pct'].to_numpy() * 100
    bp, im = T['bp'].to_numpy().astype(float), T['im'].to_numpy().astype(float)
    win = net > 0
    o.update(win=100 * win.mean(), mean_pct=float(pct.mean()), ci_pct=sp.get('ci_trade_b20'), mean_usd=float(net.mean()),
             ci_usd=su.get('ci_trade_b20'), avg_win_usd=float(net[win].mean()) if win.any() else float('nan'),
             avg_loss_usd=float(net[~win].mean()) if (~win).any() else float('nan'),
             avg_win_pct=float(pct[win].mean()) if win.any() else float('nan'),
             avg_loss_pct=float(pct[~win].mean()) if (~win).any() else float('nan'),
             bp=float(np.nanmean(bp)), im=float(np.nanmean(im)), bp_missing=int(np.isnan(bp).sum()),
             total_usd=float(net.sum()))
    ex = T['reason'].value_counts().sort('count', descending=True)
    o['exits'] = {r['reason']: r['count'] / n for r in ex.iter_rows(named=True)}
    dsum = per.sort('U', descending=True)
    top5 = float(dsum['U'].head(5).sum())
    o['top5_usd'] = top5
    o['top5_share'] = top5 / o['total_usd'] if o['total_usd'] > 0 else float('nan')
    return o


def reasons(S: pl.DataFrame) -> tuple[dict, dict]:
    st = S.filter(pl.col('n') == 0)['stage'].value_counts().sort('count', descending=True)
    stage = {r['stage']: r['count'] for r in st.iter_rows(named=True)}
    why: dict[str, int] = {}
    for w in S['why'].to_list():
        for k, v in json.loads(w).items():
            why[k] = why.get(k, 0) + v
    return stage, dict(sorted(why.items(), key=lambda a: -a[1]))


def main():
    T = pl.read_parquet(E.BIG / 'explore_trades.parquet').with_columns(pl.col('day').str.slice(0, 4).alias('year'))
    S = pl.read_parquet(E.BIG / 'explore_sessions.parquet')
    TF = pl.read_parquet(E.BIG / 'forward_trades.parquet')
    sess = json.loads((OUT / 'explore_sessions.json').read_text())
    days = sess['run']
    years = sorted({d[:4] for d in days})
    R = {}
    for r in ROWS:
        Tr, Sr = T.filter(pl.col('row') == r), S.filter(pl.col('row') == r)
        o = block(Tr, days)
        o['projected_B'] = o['rate'] * E.B_SESSIONS
        o['no_trade_stage'], o['setup_counts'] = reasons(Sr)
        o['by_year'] = {y: block(Tr.filter(pl.col('year') == y), [d for d in days if d[:4] == y]) for y in years}
        o['by_kz'] = {z: block(Tr.filter(pl.col('kz') == z), days) for z in ('AM', 'PM', 'other')}
        Fr = TF.filter(pl.col('row') == r)
        o['forward'] = block(Fr, list(E.FORWARD))
        o['forward_trades'] = Fr.select('day', 'm', 'side', 'K', 'ask', 'exit_m', 'reason', 'net', 'pct', 'bp').to_dicts()
        R[r] = o
    # Amendment 1, mechanically
    q = []
    for r in CANDIDATES:
        o = R[r]
        ok_mean = o['trades'] > 0 and o['mean_pct'] > 0
        ok_u = o['trades'] > 0 and o['bp'] > 0
        ok_b = o['projected_B'] >= 80
        o['qualifies'] = dict(mean_pct_gt0=ok_mean, underlying_gt0=ok_u, projected_B_ge80=ok_b, all=ok_mean and ok_u and ok_b)
        if o['qualifies']['all']:
            q.append(r)
    q.sort(key=lambda r: -R[r]['mean_pct'])
    fin = ['v0'] + q[:2]
    summary = dict(rows=R, qualified=q, finalists=fin, k=len(fin), sessions_run=len(days), dropped=sess['dropped'],
                   B_sessions=E.B_SESSIONS)
    (OUT / 'exploration_summary.json').write_text(json.dumps(summary, indent=1, default=float))
    # tables
    L = ['# Exploration tables (generated by summarize.py)', '',
         f'{len(days)} exploration sessions run ({days[0]} .. {days[-1]}, full sessions, the 28 months out); '
         f'{len(sess["dropped"])} not run (listed in explore_sessions.json). Holdout-B full sessions: {E.B_SESSIONS}. '
         'Size 2 contracts; % = net ÷ debit; after fees, ask in, bid out; intervals: 20-session moving-block bootstrap '
         '(audit_lib.session_stats, 2,000 draws).', '',
         '## Headline', '',
         '| row | trades | per session | projected B | win % | mean %/trade [95%] | mean $/trade [95%] | avg win $ | avg loss $ | '
         'underlying bp | in 09:30 IMs | top-5 days share | qualifies |', '|' + '---|' * 13]
    for r in ROWS:
        o = R[r]
        qq = '(v0: always a finalist)' if r == 'v0' else ('yes' if o['qualifies']['all'] else
                                                          'no: ' + ', '.join(k for k, v in o['qualifies'].items() if k != 'all' and not v))
        if o['trades'] == 0:
            L.append(f"| {r} | 0 | 0 | 0 | — | — | — | — | — | — | — | — | {qq} |")
            continue
        L.append(f"| {r} | {o['trades']} | {o['rate']:.3f} | {o['projected_B']:.0f} | {o['win']:.0f} | {f(o['mean_pct'])} "
                 f"{ci(o['ci_pct'])} | {f(o['mean_usd'], '{:+.0f}')} {ci(o['ci_usd'], '{:+.0f}')} | {f(o['avg_win_usd'], '{:+.0f}')} | "
                 f"{f(o['avg_loss_usd'], '{:+.0f}')} | {f(o['bp'])} | {f(o['im'], '{:+.3f}')} | "
                 f"{f(100 * o['top5_share'], '{:.0f}%') if math.isfinite(o['top5_share']) else 'n/a (total ' + f(o['total_usd'], '{:+.0f}') + ' $)'} | {qq} |")
    L += ['', f"Qualified candidates (mean % > 0, underlying > 0, projected B ≥ 80): {', '.join(q) or 'none'}. "
              f"**Finalists: {', '.join(fin)}; k = {len(fin)}.**", '', '## Exits and no-trade reasons', '']
    for r in ROWS:
        o = R[r]
        ex = ', '.join(f'{k} {100 * v:.0f}%' for k, v in o.get('exits', {}).items()) or '—'
        st = ', '.join(f'{k} {v}' for k, v in o['no_trade_stage'].items()) or '—'
        sc = ', '.join(f'{k} {v}' for k, v in o['setup_counts'].items()) or '—'
        L.append(f"- **{r}** — exits: {ex}. Sessions with no trade, by the furthest stage reached: {st}. Setup-level counts: {sc}.")
    for key, labels in (('by_year', years), ('by_kz', ['AM', 'PM', 'other'])):
        L += ['', f"## {'By year' if key == 'by_year' else 'By killzone'}", '',
              '| row | ' + ('year' if key == 'by_year' else 'killzone') + ' | sessions | trades | win % | mean %/trade [95%] | mean $/trade [95%] | '
              'avg win $ | avg loss $ | underlying bp | in IMs | exits |', '|' + '---|' * 12]
        for r in ROWS:
            for y in labels:
                o = R[r][key][y]
                if o['trades'] == 0:
                    if key == 'by_year' or y != 'other':
                        L.append(f"| {r} | {y} | {o['sessions']} | 0 | — | — | — | — | — | — | — | — |")
                    continue
                ex = ', '.join(f'{k} {100 * v:.0f}%' for k, v in o['exits'].items())
                L.append(f"| {r} | {y} | {o['sessions']} | {o['trades']} | {o['win']:.0f} | {f(o['mean_pct'])} {ci(o['ci_pct'])} | "
                         f"{f(o['mean_usd'], '{:+.0f}')} {ci(o['ci_usd'], '{:+.0f}')} | {f(o['avg_win_usd'], '{:+.0f}')} | "
                         f"{f(o['avg_loss_usd'], '{:+.0f}')} | {f(o['bp'])} | {f(o['im'], '{:+.3f}')} | {ex} |")
    L += ['', '## Forward sessions (2026-10-12 .. 10-22; apart from the exploration and both holdouts; no interval)', '',
          '| row | trades | win % | mean %/trade | mean $/trade | underlying bp | in IMs | the trades |', '|' + '---|' * 8]
    for r in ROWS:
        o = R[r]['forward']
        tl = '; '.join(f"{t['day'][5:]} {hm(t['m'])} {'C' if t['side'] > 0 else 'P'} → {hm(t['exit_m'])} {t['reason']} "
                       f"{t['net']:+.0f}" for t in R[r]['forward_trades']) or '—'
        if o['trades'] == 0:
            L.append(f'| {r} | 0 | — | — | — | — | — | — |')
            continue
        L.append(f"| {r} | {o['trades']} | {o['win']:.0f} | {f(o['mean_pct'])} | {f(o['mean_usd'], '{:+.0f}')} | {f(o['bp'])} | "
                 f"{f(o['im'], '{:+.3f}')} | {tl} |")
    (OUT / 'exploration_tables.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L[:20]))


if __name__ == '__main__':
    main()
