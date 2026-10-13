# T5: per-tag-family outcome comparison with bootstrap CIs; pre-registered claims; BH correction.
import json, os, collections, statistics, random, math
SP=os.environ['SP']; random.seed(11)
ts=json.load(open(SP+'/evidence/public_api/trades_all.json'))['trades']
def fam(s): return s.split(':')[0]
def tagset(t): return set(fam(s) for s in (t.get('confluenceSignals') or []))
def exact(t,prefix): return any(s.startswith(prefix) for s in (t.get('confluenceSignals') or []))
pnl=lambda t: t.get('pnlPercent') or 0.0
def boot_diff(a,b,n=2000):
    if not a or not b: return None
    diffs=[]
    for _ in range(n):
        sa=[random.choice(a) for _ in a]; sb=[random.choice(b) for _ in b]; diffs.append(statistics.mean(sa)-statistics.mean(sb))
    diffs.sort(); return (statistics.mean(a)-statistics.mean(b), diffs[int(0.025*n)], diffs[int(0.975*n)], sum(1 for d in diffs if d<=0)/n)
fams=collections.Counter(f for t in ts for f in tagset(t))
rows=[]
for f,n in sorted(fams.items()):  # sorted: deterministic consumption of the seeded RNG (2026-10-13 audit fix; original output kept as validation_T5_gates.txt)
    if n<30 or n>len(ts)-30: continue
    a=[pnl(t) for t in ts if f in tagset(t)]; b=[pnl(t) for t in ts if f not in tagset(t)]
    r=boot_diff(a,b); 
    if r: rows.append((f,len(a),len(b),100*statistics.mean(a),100*statistics.mean(b),100*r[0],100*r[1],100*r[2],2*min(r[3],1-r[3])))
rows.sort(key=lambda x:x[8])
m=len(rows); print(f'families tested: {m}')
print('family | n_with n_without | mean pnl% with / without | diff [95% CI] | two-sided bootstrap p | BH q<0.10?')
for i,(f,na,nb,ma,mb,dd,lo,hi,p) in enumerate(rows[:30]):
    q=p*m/(i+1); print(f'{f:34} {na:4d} {nb:4d} | {ma:6.1f} / {mb:6.1f} | {dd:+6.1f} [{lo:+6.1f},{hi:+6.1f}] | p={p:.3f} | {"YES" if q<0.10 else "no"}')
print('--- pre-registered claims (effect = mean pnl% with vs without, 95% CI):')
claims=[('grade A+ vs A', lambda t:t.get('setupGrade')=='A+', lambda t:t.get('setupGrade')=='A'),('grade A vs A-/B+', lambda t:t.get('setupGrade')=='A', lambda t:t.get('setupGrade') in ('A-','B+')),('SESSION_ADJ:+20 vs others', lambda t:exact(t,'SESSION_ADJ:+20'), lambda t:not exact(t,'SESSION_ADJ:+20')),('CHOP_DAY tag present', lambda t:'CHOP_DAY' in tagset(t), lambda t:'CHOP_DAY' not in tagset(t)),('GEX:NEGATIVE_GAMMA+10', lambda t:exact(t,'GEX:NEGATIVE_GAMMA'), lambda t:not exact(t,'GEX:NEGATIVE_GAMMA')),('SWEEP_ALIGNED', lambda t:'SWEEP_ALIGNED' in tagset(t), lambda t:'SWEEP_ALIGNED' not in tagset(t)),('TRIPLE_CONFIRM', lambda t:'TRIPLE_CONFIRM' in tagset(t), lambda t:'TRIPLE_CONFIRM' not in tagset(t)),('SWEEP_CONFLICT', lambda t:'SWEEP_CONFLICT' in tagset(t), lambda t:'SWEEP_CONFLICT' not in tagset(t)),('INST:MULTI_TICKER_CONFIRMATION', lambda t:exact(t,'INST:MULTI_TICKER'), lambda t:not exact(t,'INST:MULTI_TICKER')),('KILLZONE:NY_AM_SILVER_BULLET', lambda t:exact(t,'KILLZONE:NY_AM_SILVER'), lambda t:not exact(t,'KILLZONE:NY_AM_SILVER')),('confidence>=85 vs <85 (post-May only)', lambda t:(t.get('confidence') or 0)>=85 and t['entryTime']>='2026-05', lambda t:0<(t.get('confidence') or 0)<85 and t['entryTime']>='2026-05')]
for name,fa,fb in claims:
    a=[pnl(t) for t in ts if fa(t)]; b=[pnl(t) for t in ts if fb(t)]; r=boot_diff(a,b)
    if r: print(f'   {name:42} n={len(a):3d} vs {len(b):3d}: {100*statistics.mean(a):6.1f}% vs {100*statistics.mean(b):6.1f}% diff={100*r[0]:+6.1f} [{100*r[1]:+6.1f},{100*r[2]:+6.1f}] p={2*min(r[3],1-r[3]):.3f}')
# in-sample / out-of-sample grade monotonicity
for lab,cond in [('IS Mar-Jun', lambda t:t['entryTime']<'2026-07'),('OOS Jul-Oct', lambda t:t['entryTime']>='2026-07')]:
    print(f'--- {lab}: grade -> n, wr, mean pnl%')
    for g in ['A+','A','A-','B+']:
        v=[pnl(t) for t in ts if cond(t) and t.get('setupGrade')==g]
        if v: print(f'   {g:3} n={len(v):3d} wr={100*sum(1 for x in v if x>0)/len(v):5.1f}% mean={100*statistics.mean(v):6.1f}%')
