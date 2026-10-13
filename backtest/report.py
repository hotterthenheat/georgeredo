"""Summarise backtest trades: per-variant metrics with vectorised bootstrap CIs, IS/OOS split, baselines, breakdowns."""
import csv, sys, os, collections, statistics, json
import numpy as np
rng = np.random.default_rng(7)
OUT = sys.argv[1]; SPLIT = sys.argv[2] if len(sys.argv) > 2 else '2026-03-02'
rows = list(csv.DictReader(open(OUT + '/trades.csv'))); base = list(csv.DictReader(open(OUT + '/baseline.csv'))) if os.path.exists(OUT + '/baseline.csv') else []
for r in rows + base:
    for k in ('ret_mid', 'usd_mid', 'ret_spread', 'usd_spread', 'ret_adverse', 'usd_adverse'): r[k] = float(r[k])
def ci(v, n=1000):
    v = np.asarray(v, dtype=float)
    if len(v) < 5: return (float('nan'), float('nan'))
    idx = rng.integers(0, len(v), size=(n, len(v))); m = v[idx].mean(axis=1); return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
def dd(v):
    c = np.cumsum(v); peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]; return float((c - peak).min()) if len(c) else 0.0
def summ(tr, key='usd_spread'):
    if not tr: return None
    v = np.array([t[key] for t in tr]); w = v[v > 0]; l = v[v < 0]; lo, hi = ci(v)
    return dict(n=int(len(v)), total=round(float(v.sum()), 1), wr=round(100 * len(w) / len(v), 1), exp=round(float(v.mean()), 2), lo=round(lo, 2), hi=round(hi, 2), pf=round(float(w.sum() / abs(l.sum())), 2) if len(l) and l.sum() != 0 else float('inf'), mdd=round(dd(v), 1), avg_ret=round(100 * float(np.mean([t['ret_mid'] for t in tr])), 1))
byv = collections.defaultdict(list)
for r in rows: byv[r['variant']].append(r)
print(f'variants: {len(byv)} | trades total: {len(rows)} | split IS < {SPLIT} <= OOS')
print('variant (mode|levels|window|gate|engine) | model=spread: n total wr exp [95% CI] PF maxDD | mid exp | adverse exp | IS exp | OOS(spread): n exp [CI]')
table = []
for v, tr in byv.items():
    s = summ(tr); m = summ(tr, 'usd_mid'); a = summ(tr, 'usd_adverse')
    oos = summ([t for t in tr if t['date'] >= SPLIT]); ins = summ([t for t in tr if t['date'] < SPLIT])
    table.append((v, s, m, a, ins, oos))
table.sort(key=lambda x: -(x[1]['exp'] if x[1] else -1e9))
for v, s, m, a, ins, oos in table:
    print(f"{v:48} | n={s['n']:5d} tot={s['total']:8.0f} wr={s['wr']:4.1f} exp={s['exp']:6.1f} [{s['lo']:6.1f},{s['hi']:6.1f}] PF={s['pf']:4.2f} DD={s['mdd']:7.0f} | mid={m['exp']:6.1f} | adv={a['exp']:6.1f} | IS n={ins['n'] if ins else 0:4d} exp={ins['exp'] if ins else float('nan'):6.1f} | OOS n={oos['n'] if oos else 0:4d} exp={oos['exp'] if oos else float('nan'):6.1f} [{oos['lo'] if oos else float('nan'):6.1f},{oos['hi'] if oos else float('nan'):6.1f}]")
if base:
    print('\n--- random-time baselines (same per-day counts, ladder engine):')
    bb = collections.defaultdict(list)
    for r in base: bb[r['variant']].append(r)
    for v, tr in bb.items():
        s = summ(tr); m = summ(tr, 'usd_mid'); a = summ(tr, 'usd_adverse'); print(f"{v:48} | n={s['n']:5d} spread exp={s['exp']:6.1f} [{s['lo']:6.1f},{s['hi']:6.1f}] wr={s['wr']:4.1f} | mid={m['exp']:6.1f} | adv={a['exp']:6.1f}")
print('\n--- breakdowns for top 3 variants by spread-model expectancy, plus the GeorgeFi-like reference (sweep|ict+gex|all|none|ladder):')
picks = [x for x in table[:3]] + [x for x in table if x[0] == 'sweep|ict+gex|all|none|ladder']
for v, s, m, a, ins, oos in picks:
    tr = byv[v]
    print(f'== {v}')
    for key, fn in [('ticker', lambda t: t['ticker']), ('direction', lambda t: t['direction']), ('level', lambda t: t['level']), ('regime', lambda t: t['regime'] or 'n/a'), ('hour', lambda t: t['entry_t'][11:13]), ('exit', lambda t: t['reasons'].split('+')[-1]), ('month', lambda t: t['date'][:7])]:
        g = collections.defaultdict(list)
        for t in tr: g[fn(t)].append(t)
        print('   by', key, ' | '.join(f"{k}: n={len(x)} exp={np.mean([y['usd_spread'] for y in x]):.0f} wr={100*sum(1 for y in x if y['usd_spread']>0)/len(x):.0f}%" for k, x in sorted(g.items(), key=lambda kv: -len(kv[1]))[:12]))
    tot = sum(t['usd_spread'] for t in tr); top = sorted(tr, key=lambda t: -t['usd_spread'])[:5]
    print('   top-5 share of total:', (round(100 * sum(t['usd_spread'] for t in top) / tot) if tot else 'n/a'), '% | median hold min:', statistics.median(float(t['hold_min']) for t in tr), '| MFE>=25%:', f"{100*sum(1 for t in tr if float(t['mfe'])>=0.25)/len(tr):.0f}%")
json.dump({v: dict(all=s, mid=m, adverse=a, IS=ins, OOS=oos) for v, s, m, a, ins, oos in table}, open(OUT + '/summary.json', 'w'), indent=1, default=str)
