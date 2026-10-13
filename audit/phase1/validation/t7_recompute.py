# Auditor's recomputation of T7 (refresh stability) from the committed snapshots. NOT the author's script (none is committed).
import json, sys, collections, os
files=sys.argv[1:]
snaps=[]
for f in files:
    d=json.load(open(f)); snaps.append((d['updatedAt'], os.path.basename(f), {x['ticker']:x for x in d['decisions']}, [i['ticker'] for i in d['indices']]))
snaps.sort()
print('snapshots (updatedAt):', [(s[0][11:19], s[1]) for s in snaps])
print('index tickers:', snaps[0][3])
print('decision tickers per snapshot:', [len(s[2]) for s in snaps], '| union', len(set().union(*[set(s[2]) for s in snaps])))
d0=next(iter(snaps[0][2].values())); print('ALL decision keys:', sorted(d0.keys()))
def gexreg(x):
    if x.get('gexRegime') is not None: return x.get('gexRegime')
    gp=x.get('gexProfile') or x.get('gex_profile') or {}
    return gp.get('regime') if isinstance(gp,dict) else None
def mood(x):
    for k in ('crowd_mood','crowdMood'):
        if k in x: return x[k]
    for sub in ('ictContext','ict_context','volumeAnalysis','volume_analysis','gexProfile'):
        v=x.get(sub)
        if isinstance(v,dict):
            for k in ('crowd_mood','crowdMood','mood'):
                if k in v: return v[k]
    return None
fields={'direction':lambda x:x.get('direction'),'action':lambda x:x.get('action'),'confidence':lambda x:x.get('confidence'),'setupGrade':lambda x:x.get('setupGrade'),'contract':lambda x:x.get('contract'),'gexRegime':gexreg,'crowd_mood':mood}
def run(sub, tickers=None, label=''):
    ch=collections.Counter(); pairs=0
    for (a,b) in zip(sub, sub[1:]):
        for tk in a[2]:
            if tk not in b[2]: continue
            if tickers and tk not in tickers: continue
            pairs+=1
            for fn,f in fields.items():
                if f(a[2][tk])!=f(b[2][tk]): ch[fn]+=1
    print(f'--- {label}: consecutive ticker-pairs={pairs}', {k:f'{ch[k]}/{pairs} ({100*ch[k]/pairs:.0f}%)' for k in fields})
run(snaps[:3], None, 'first 3 snapshots, all 20 tickers')
run(snaps[:3], set(snaps[0][3]), 'first 3 snapshots, 6 index tickers')
run(snaps, None, 'all 5 snapshots, all tickers')
run(snaps, set(snaps[0][3]), 'all 5 snapshots, 6 index tickers')
acts=collections.Counter(x.get('action') for s in snaps for x in s[2].values()); print('--- action histogram across 5 snapshots:', acts.most_common())
def blocked_group(a): return 'BLOCKED (various)' if (a or '').startswith('BLOCKED') else a
print('--- grouped:', collections.Counter(blocked_group(x.get('action')) for s in snaps for x in s[2].values()).most_common())
for tk in ['^SPX','^NDX','QQQ']:
    print(f'--- {tk} path:', [ (s[0][11:16], (s[2].get(tk) or {}).get('direction'), (s[2].get(tk) or {}).get('confidence'), (s[2].get(tk) or {}).get('setupGrade'), ((s[2].get(tk) or {}).get('action') or '')[:28]) for s in snaps])
print('--- sample crowd_mood / gexRegime values:', [ (mood(x), gexreg(x)) for x in list(snaps[0][2].values())[:4]])
