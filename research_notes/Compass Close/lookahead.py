"""lookahead.py — Compass Close integrity, part 2 (PREREG section 7): on 10 gate-sample sessions (seed 20261024) every chain
row and SPX print stamped after 15:55 is blanked (SET kept) and the primary rebuilt; nothing may change. Control: the 15:56
quote read in place of the 15:55 one; K or the entry should change.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import close_lib as L  # noqa: E402


def key(row: dict) -> dict:
    e = row['15:55']
    p = L.books(row)['primary']
    return {'K': e['K'], 'C': e.get('C'), 'P': e.get('P'), 'trade': p['trade'], 'entry': p.get('entry'),
            'pnl': p.get('pnl'), 'why': p.get('why')}


def main() -> int:
    gdays = [r['session'] for r in csv.DictReader(open(HERE / 'sessions_new.csv')) if r['sample'] == 'gate']
    days = sorted(random.Random(20261024 + 1).sample(gdays, 10))
    same, ctrl_changed, rows = 0, 0, []
    for d in days:
        full = key(L.session_row(d, 'new'))
        cut = key(L.session_row(d, 'new', cut='15:55'))
        ctl = key(L.session_row(d, 'new', entry_quote_minute='15:56'))
        eq = full == cut
        ch = (ctl['K'] != full['K']) or (ctl['entry'] != full['entry']) or (ctl['trade'] != full['trade'])
        same += eq
        ctrl_changed += ch
        rows.append({'day': d, 'blanked_equal': eq, 'control_changed': ch, 'entry': full['entry'], 'entry_1556': ctl['entry'],
                     'trade': full['trade'], 'trade_1556': ctl['trade']})
    res = {'sessions': len(days), 'unchanged_when_blanked': same, 'control_changed': ctrl_changed, 'rows': rows}
    (HERE / 'out' / 'lookahead.json').write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != 'rows'}))
    for r in rows:
        print(r)
    return 0 if same == len(days) else 1


if __name__ == '__main__':
    sys.exit(main())
