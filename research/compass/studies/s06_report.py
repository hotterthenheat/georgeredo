"""S06 report: markdown tables from a screen run's rows.json (absolute forward returns with CIs, pre-signal drift, the
matched random control and the difference). A trigger is promoted only if BOTH the absolute 30- or 60-minute lower bound
is >= +3 bp AND the paired lower bound against the matched random control is > 0 (05_results.md §S06 explains why both).
Usage: python3 s06_report.py <result_name> [hurdle_bp]"""
import json, os, sys
import polars as pl
HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1] if len(sys.argv) > 1 else 's06_signal_screen_index'
hurdle = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
D = os.path.join(HERE, '..', 'results', 'v1', name)
rows = json.load(open(os.path.join(D, 'rows.json')))
f = lambda x, d=1: '' if x is None or x != x else f'{x:+.{d}f}'
L = [f'# {name}: entry triggers on the underlying, signed return after the decision bar (bp)', '',
     'Absolute = direction × underlying return; random = minutes drawn uniformly in the entry window on the same symbol/date/direction (5 seeds); CIs day-clustered.', '',
     '| symbol | trigger | filters | n | days | pre 30m | +5m | +15m | +30m [CI] | +60m [CI] | to close | hit 30m | random 30m | vs random 30m [CI] | vs random 60m [CI] | promoted |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
prom = []
for r in rows:
    if not r.get('days'): L.append(f"| {r['symbol']} | {r['trigger']} | {r['filters']} | {r.get('n', 0)} | | | | | | | | | | | | |"); continue
    abs_ok = (r.get('fwd_30m_bp_lo') or -1e9) >= hurdle or (r.get('fwd_60m_bp_lo') or -1e9) >= hurdle
    rel_ok = (r.get('vs_random_30m_lo') or -1e9) > 0 or (r.get('vs_random_60m_lo') or -1e9) > 0
    p = 'YES' if abs_ok and rel_ok else ('abs only' if abs_ok else ('vs-random only' if rel_ok else 'no'))
    if abs_ok and rel_ok: prom.append((r['symbol'], r['trigger'], r['filters']))
    L.append(f"| {r['symbol']} | {r['trigger']} | {r['filters']} | {r['n']} | {r['days']} | {f(r['pre_30m_bp'])} | {f(r['fwd_5m_bp'])} | {f(r['fwd_15m_bp'])} | **{f(r['fwd_30m_bp'])}** [{f(r['fwd_30m_bp_lo'])}, {f(r['fwd_30m_bp_hi'])}] | {f(r['fwd_60m_bp'])} [{f(r['fwd_60m_bp_lo'])}, {f(r['fwd_60m_bp_hi'])}] | {f(r['fwd_close_bp'])} | {r['hit_30m'] * 100:.0f} % | {f(r.get('random_30m_bp'))} | {f(r.get('vs_random_30m_bp'))} [{f(r.get('vs_random_30m_lo'))}, {f(r.get('vs_random_30m_hi'))}] | {f(r.get('vs_random_60m_bp'))} [{f(r.get('vs_random_60m_lo'))}, {f(r.get('vs_random_60m_hi'))}] | {p} |")
L += ['', f'Promotion rule: absolute lower bound at 30 or 60 min ≥ +{hurdle:g} bp AND paired lower bound vs random > 0. Promoted: {prom or "none"}.', '']
# year-by-year of the vs-random 30m for rows with n >= 500
L += ['## vs random, 30 min, by year (rows with n ≥ 500)', '']
years = sorted({y for r in rows for y in (r.get('by_year_vs_random_30m') or {})})
L.append('| symbol | trigger | filters | ' + ' | '.join(years) + ' |'); L.append('|---|---|---|' + '---|' * len(years))
for r in rows:
    if (r.get('n') or 0) < 500: continue
    by = r.get('by_year_vs_random_30m') or {}
    L.append(f"| {r['symbol']} | {r['trigger']} | {r['filters']} | " + ' | '.join(f(by.get(y)) for y in years) + ' |')
open(os.path.join(D, 'REPORT.md'), 'w').write('\n'.join(L) + '\n')
json.dump({'hurdle_bp': hurdle, 'promoted': prom, 'rows': len(rows)}, open(os.path.join(D, 'summary.json'), 'w'), indent=1)
print('\n'.join(L))
