"""Validate data/macro_events_2022_2027.json (and its CSV twin).

Run: python3 data/check_macro_events.py
Exits non-zero on any hard failure; prints counts and the documented exceptions.
"""
import csv, json, sys, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
J, C = HERE / 'macro_events_2022_2027.json', HERE / 'macro_events_2022_2027.csv'
KEYS = ['date', 'time_et', 'event', 'reference_period', 'status', 'source']
TIMES = {'FOMC_DECISION': '14:00', 'FOMC_MINUTES': '14:00', 'CPI': '08:30', 'NFP': '08:30'}
BUILT = dt.date(2026, 10, 21)
YEARS = range(2022, 2028)
# Documented gaps (README): releases BLS cancelled, and the 2027 FOMC minutes the Fed has not dated.
CANCELLED = {('CPI', '2025-10'), ('NFP', '2025-10')}
# Expected counts per year when a gap or the source's horizon shortens a year (README explains each).
EXPECT = {('CPI', y): 12 for y in YEARS} | {('NFP', y): 12 for y in YEARS} \
       | {('FOMC_DECISION', y): 8 for y in YEARS} | {('FOMC_MINUTES', y): 8 for y in YEARS}
EXPECT[('CPI', 2025)] = 11      # October 2025 CPI cancelled (Sep CPI moved into late Oct; Nov CPI on Dec 18)
EXPECT[('NFP', 2025)] = 11      # October 2025 report cancelled; Oct payrolls published with Nov on Dec 16
EXPECT[('FOMC_MINUTES', 2025)] = 9  # by release year: Dec 2024 minutes (Jan 8) + all eight 2025 meetings (Dec 9-10 minutes out Dec 30)
EXPECT[('FOMC_MINUTES', 2027)] = 0  # Fed has not listed release dates for 2027 minutes

fail = []
def bad(msg): fail.append(msg)

rows = json.loads(J.read_text())
with C.open(newline='') as f:
    crows = list(csv.DictReader(f))
if crows != rows: bad('CSV rows differ from JSON rows')

# schema
for i, r in enumerate(rows):
    if list(r.keys()) != KEYS: bad(f'row {i}: keys {list(r.keys())}')
    try: d = dt.date.fromisoformat(r['date'])
    except Exception: bad(f'row {i}: bad date {r["date"]}'); continue
    if r['event'] not in TIMES: bad(f'row {i}: bad event {r["event"]}')
    elif r['time_et'] != TIMES[r['event']]: bad(f'row {i}: time {r["time_et"]} for {r["event"]}')
    if r['status'] not in ('released', 'scheduled'): bad(f'row {i}: status {r["status"]}')
    if (r['status'] == 'released') != (d <= BUILT): bad(f'row {i}: status {r["status"]} on {d} (built {BUILT})')
    if not r['source'].startswith(('https://www.bls.gov/', 'https://www.federalreserve.gov/')):
        bad(f'row {i}: non-primary source {r["source"]}')
    if not (dt.date(2022, 1, 1) <= d <= dt.date(2027, 12, 31)): bad(f'row {i}: out of range {d}')
    if d.weekday() > 4: bad(f'row {i}: {d} is a {d:%A}')

# sorting and duplicates
keys = [(r['date'], r['time_et']) for r in rows]
if keys != sorted(keys): bad('not sorted by date then time')
dup = [k for k, n in Counter((r['event'], r['reference_period']) for r in rows).items() if n > 1]
if dup: bad(f'duplicate event/reference rows: {dup}')
dup2 = [k for k, n in Counter((r['date'], r['event']) for r in rows).items() if n > 1]
if dup2: bad(f'two rows of one event on one date: {dup2}')

# CPI / NFP: one per reference month, consecutive months except documented gaps
nfp_exceptions = []
for ev in ('CPI', 'NFP'):
    refs = sorted(r['reference_period'] for r in rows if r['event'] == ev)
    y, m = map(int, refs[0].split('-'))
    seen = set(refs)
    while f'{y}-{m:02d}' <= refs[-1]:
        p = f'{y}-{m:02d}'
        if p not in seen and (ev, p) not in CANCELLED: bad(f'{ev}: reference month {p} missing')
        if p in seen and (ev, p) in CANCELLED: bad(f'{ev}: {p} is listed as cancelled but present')
        m += 1
        if m == 13: y, m = y + 1, 1
    for r in rows:
        if r['event'] != ev: continue
        d = dt.date.fromisoformat(r['date']); ry, rm = map(int, r['reference_period'].split('-'))
        lag = (d.year - ry) * 12 + d.month - rm
        if lag < 1 or (lag > 1 and not (ev, r['reference_period']) in {('NFP', '2025-09')}):
            bad(f'{ev} {r["reference_period"]} released {d}: {lag} months after the reference month')
        if ev == 'NFP' and d.weekday() != 4:
            nfp_exceptions.append(f'{d} ({d:%A}) NFP for {r["reference_period"]} [{r["status"]}]')

# FOMC: minutes about three weeks after the decision of the same meeting
dec = {r['reference_period']: dt.date.fromisoformat(r['date']) for r in rows if r['event'] == 'FOMC_DECISION'}
gaps = []
for r in rows:
    if r['event'] != 'FOMC_MINUTES': continue
    start, end = (dt.date.fromisoformat(x) for x in r['reference_period'].split('/'))
    d = dt.date.fromisoformat(r['date'])
    if r['reference_period'] in dec and dec[r['reference_period']] != end: bad(f'minutes {r["reference_period"]}: decision row on another day')
    lag = (d - end).days
    gaps.append(lag)
    if not 19 <= lag <= 23: bad(f'minutes {r["reference_period"]} released {d}: {lag} days after the decision')
for ref, d in dec.items():
    start, end = (dt.date.fromisoformat(x) for x in ref.split('/'))
    if d != end or (end - start).days not in (1,): bad(f'decision {ref}: not a two-day meeting ending on its date')

# counts per year per kind
cnt = Counter((r['event'], int(r['date'][:4])) for r in rows)
for k, n in EXPECT.items():
    if cnt.get(k, 0) != n: bad(f'{k[0]} {k[1]}: {cnt.get(k, 0)} rows, expected {n}')

print(f'rows: {len(rows)}  (released {sum(r["status"]=="released" for r in rows)}, scheduled {sum(r["status"]=="scheduled" for r in rows)})')
print('\ncounts per year per kind (by release date):')
kinds = ['FOMC_DECISION', 'FOMC_MINUTES', 'CPI', 'NFP']
print('year  ' + '  '.join(f'{k:>13}' for k in kinds))
for y in YEARS:
    print(f'{y}  ' + '  '.join(f'{cnt.get((k, y), 0):>13}' for k in kinds))
print('total ' + '  '.join(f'{sum(cnt.get((k, y), 0) for y in YEARS):>13}' for k in kinds))
print(f'\nminutes lag after decision (days): min {min(gaps)}, max {max(gaps)}, {Counter(gaps)}')
print('\nNFP not on a Friday (each checked against BLS):')
why = {'2025-07-03': 'Independence Day on Friday Jul 4', '2026-07-02': 'Independence Day observed Friday Jul 3',
       '2025-11-20': '2025 lapse in appropriations', '2025-12-16': '2025 lapse in appropriations',
       '2026-02-11': '2026 lapse in appropriations (moved from Fri Feb 6)'}
for e in nfp_exceptions: print('  ' + e + ' - ' + why.get(e[:10], 'UNEXPLAINED'))
if any(e[:10] not in why for e in nfp_exceptions): bad('an NFP off a Friday has no documented reason')
print('\ncancelled releases (no row by design): ' + ', '.join(f'{e} {p}' for e, p in sorted(CANCELLED)))
if fail:
    print(f'\nFAILED ({len(fail)}):'); [print('  ' + m) for m in fail]; sys.exit(1)
print('\nALL CHECKS PASSED')
