import json, os, csv, collections, sys
SP=sys.argv[1]
ts=json.load(open(SP+'/evidence/public_api/trades_all.json'))['trades']
ub=set(os.listdir(SP+'/evidence/validation/uw_bars')); tb=set(os.listdir(SP+'/evidence/validation/uw_tape_bars')); mb=set(os.listdir(SP+'/evidence/validation/bars'))
print('uw_bars files', len(ub), '| uw_tape_bars files', len(tb), '| massive bars files', len(mb))
ids=set(t['id'] for t in ts); print('ledger trades', len(ts), 'unique ids', len(ids))
entry_ok=[t for t in ts if f"{t['id']}_{t['entryTime'][:10]}.json" in ub]
missing=[t for t in ts if f"{t['id']}_{t['entryTime'][:10]}.json" not in ub]
print('trades with entry-day uw bar file:', len(entry_ok), '| missing:', len(missing))
for t in missing: print('   MISSING', t['id'], t['ticker'], t.get('optionSymbol'), t['entryTime'][:10], (t.get('exitTime') or '')[:10], t['tradeType'])
# expected job set per fetch_uw_bars.py
jobs=set()
for t in ts:
    for day in {t['entryTime'][:10], (t.get('exitTime') or t['entryTime'])[:10]}: jobs.add(f"{t['id']}_{day}.json")
print('expected (trade,day) files per fetch_uw_bars.py:', len(jobs), '| present:', len(jobs&ub), '| absent:', sorted(jobs-ub), '| extra files not in job set:', len(ub-jobs))
both=[t for t in ts if f"{t['id']}_{t['entryTime'][:10]}.json" in ub and f"{t['id']}_{(t.get('exitTime') or t['entryTime'])[:10]}.json" in ub]
print('trades with entry AND exit-day files:', len(both))
# empty-data files
empty=[f for f in ub if not json.load(open(SP+'/evidence/validation/uw_bars/'+f))['data']]
print('uw_bars files with empty data[]:', len(empty), empty[:10])
# massive bars coverage
mids=set(f[:-5] for f in mb); print('massive bars: trade ids covered', len(mids&ids), 'of', len(ids), '| not in ledger', len(mids-ids))
# tape coverage
rows=list(csv.DictReader(open(SP+'/evidence/analysis/public_tape_signals.csv')))
subs=('index-read','trade-now','moc-wick','block-sniper','sus-strike','momentum-ignition','relative-burst','big-print','accumulation-sniper','power-hour','anchor-book','hold-advisor')
pairs=set((r['occ'][2:], r['session']) for r in rows if r['occ'] and r['subsystem'] in subs)
allpairs=set((r['occ'][2:], r['session']) for r in rows if r['occ'])
print('tape rows', len(rows), '| with occ', sum(1 for r in rows if r['occ']), '| unique (contract,session) pairs in fetch subsystems', len(pairs), '| all subsystems', len(allpairs))
have=set(f"{c}_{d}.json" for c,d in pairs)&tb
print('pairs with bar file:', len(have), '| absent:', sorted(set(f"{c}_{d}.json" for c,d in pairs)-tb))
print('alerts (with occ) whose pair has a bar file:', sum(1 for r in rows if r['occ'] and f"{r['occ'][2:]}_{r['session']}.json" in tb), 'of', sum(1 for r in rows if r['occ']))
tempty=[f for f in tb if not json.load(open(SP+'/evidence/validation/uw_tape_bars/'+f))['data']]
print('uw_tape_bars files with empty data[]:', len(tempty), tempty[:10])
