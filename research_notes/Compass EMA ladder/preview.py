"""preview.py — the owner's one-month preview (PREREG_EMA_LADDER.md, 0dd8c5d): all 13 versions on 2025-03, V1 as the base.
PREVIEW — one month, no verdict."""
import json, sys
from pathlib import Path
import numpy as np
import ema_lib as E

HERE = Path(__file__).resolve().parent
days = [d for d in E.S.split_sessions('option')['pick'] if d.startswith('2025-03')]
VIDS = [f'V{i}' for i in range(1, 14)]
vers = {v: E.version(v, base='V1') for v in VIDS}
T = {v: [] for v in VIDS}
NT = {v: {} for v in VIDS}
for d in days:
    for nm in E.NAMES:
        for v in VIDS:
            t, nt = E.run_day(nm, d, vers[v])
            T[v] += t
            for a, b in nt.items():
                NT[v][a] = NT[v].get(a, 0) + b
    print(d, {v: len(T[v]) for v in ('V1', 'V2', 'V3')}, flush=True)
(HERE / 'out').mkdir(exist_ok=True)
json.dump({'days': days, 'trades': T, 'no_trade': NT}, open(HERE / 'out' / 'preview_2025-03.json', 'w'))
