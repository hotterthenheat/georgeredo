#!/usr/bin/env python3
"""Amendment 1 resolution: compare every result file before (2024-06-21 on the band-file fallback; snapshot in
$SP/hwr_grid/spxw_v2/results_amend1) and after (2024-06-21 on its complete chain).  Writes results/resolution_changes.csv:
one row per changed numeric cell (file, row key, column, before, after)."""
import os, sys, json, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
OLD = os.environ.get('OLD_DIR', sim.L.SP + '/hwr_grid/spxw_v2/results_amend1'); NEW = os.path.join(HERE, 'results')
KEYS = ['label', 'selection', 'cid', 'period', 'item', 'series', 'window', 'study', 'capital_rule', 'source', 'block', 'horizon_sessions',
        'entry', 'cell', 'kind', 'k', 'metric', 'dimension', 'change', 'family', 'win_rate_bin', 'rule', 'date', 'close_source', 'direction', 'rank']
rows = []
for f in sorted(glob.glob(NEW + '/*.csv')) + sorted(glob.glob(NEW + '/*.csv.gz')):
    nm = os.path.basename(f); o = os.path.join(OLD, nm)
    if not os.path.exists(o) or nm.startswith('resolution_'): continue
    a = pd.read_csv(o); b = pd.read_csv(f)
    keys = [k for k in KEYS if k in a.columns and k in b.columns]
    if not keys:
        a['_i'] = range(len(a)); b['_i'] = range(len(b)); keys = ['_i']
    a = a.drop_duplicates(keys); b = b.drop_duplicates(keys)
    m = a.merge(b, on=keys, how='outer', suffixes=('_old', '_new'), indicator=True)
    for _, r in m[m['_merge'] != 'both'].iterrows():
        rows.append(dict(file=nm, key=' | '.join(str(r[k]) for k in keys), column='(row)', before='present' if r['_merge'] == 'left_only' else 'absent',
                         after='absent' if r['_merge'] == 'left_only' else 'present'))
    m = m[m['_merge'] == 'both']
    for c in [c for c in a.columns if c not in keys and c in b.columns]:
        x, y = m[c + '_old'], m[c + '_new']
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            d = ~(np.isclose(x.astype(float), y.astype(float), rtol=1e-9, atol=1e-9, equal_nan=True))
        else:
            d = (x.astype(str) != y.astype(str)) & ~(x.isna() & y.isna())
        for i in np.where(np.asarray(d))[0]:
            r = m.iloc[i]
            rows.append(dict(file=nm, key=' | '.join(str(r[k]) for k in keys), column=c, before=r[c + '_old'], after=r[c + '_new']))
for nm in ('multiplicity.json', 'te_summary.json', 'integrity_summary.json', 'selection_train.json'):
    def flat(o, p=''):
        if isinstance(o, dict):
            for k, v in o.items(): yield from flat(v, f'{p}.{k}' if p else k)
        elif isinstance(o, list) and o and isinstance(o[0], (dict, list)):
            for i, v in enumerate(o): yield from flat(v, f'{p}[{i}]')
        else: yield p, o
    A = dict(flat(json.load(open(os.path.join(OLD, nm))))); B = dict(flat(json.load(open(os.path.join(NEW, nm)))))
    for k in sorted(set(A) | set(B)):
        if k.endswith('written_utc') or k.endswith('sha256') or k == 'secs': continue
        va, vb = A.get(k), B.get(k)
        same = (isinstance(va, float) and isinstance(vb, float) and np.isclose(va, vb, rtol=1e-9)) or va == vb
        if not same: rows.append(dict(file=nm, key=k, column='', before=str(va)[:300], after=str(vb)[:300]))
D = pd.DataFrame(rows); D.to_csv(os.path.join(NEW, 'resolution_changes.csv'), index=False)
print(D.groupby('file').size().to_string())
