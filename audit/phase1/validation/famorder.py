import json, collections, sys
ts=json.load(open(sys.argv[1]+'/evidence/public_api/trades_all.json'))['trades']
def fam(s): return s.split(':')[0]
def tagset(t): return set(fam(s) for s in (t.get('confluenceSignals') or []))
fams=collections.Counter(f for t in ts for f in tagset(t))
print('first 6 families in iteration order:', list(fams)[:6])
