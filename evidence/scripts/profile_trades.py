import json, sys, collections, statistics
d=json.load(open(sys.argv[1])); ts=d['trades']
C=collections.Counter
def cnt(k): return C(str(t.get(k)) for t in ts).most_common(25)
print('N=',len(ts))
for k in ['strategyVersion','bookVersion','bookName','exitReason','entrySource','accountType','tradeType','setupGrade','action','instrument_type','entryEnvironment','gexRegimeAtEntry','epochId','ictProfileType','quoteQuality','spxTradeType','themeName','auto_executed','size','initial_size','challengeId','is_public_signals','physicsVerdictEntry','dayTypeGateVerdict']:
    print(f'--- {k}:', cnt(k))
flags=[k for k in ts[0] if k.startswith('is_') or k.startswith('is')]
print('--- boolean flags true-count:')
for f in sorted(set(flags)):
    n=sum(1 for t in ts if t.get(f) is True)
    if n: print(f'   {f}: {n}')
print('--- numeric fields:')
for k in ['confidence','confidencePreCap','discomfortScore','entryPremium','exitPremium','pnl','pnlPercent','entryDelta','entryIV','entryGamma','entryTheta','entryVega','stopLoss','takeProfit','riskBudget','highWaterMark','entryPrice','exitPrice','sniper_swing_score','physicsScoreEntry']:
    v=[t.get(k) for t in ts if isinstance(t.get(k),(int,float)) and not isinstance(t.get(k),bool)]
    if v: print(f'   {k}: n={len(v)} min={min(v):.4g} med={statistics.median(v):.4g} mean={statistics.mean(v):.4g} max={max(v):.4g}')
print('--- sample times:', ts[0].get('entryTime'), ts[0].get('exitTime'), ts[0].get('expirationDate'))
print('--- tickers:', C(t['ticker'] for t in ts).most_common(40))
tot=sum(t.get('pnl') or 0 for t in ts); print('--- sum pnl:', round(tot,2), 'wins:', sum(1 for t in ts if (t.get('pnl') or 0)>0), 'losses:', sum(1 for t in ts if (t.get('pnl') or 0)<0), 'zero:', sum(1 for t in ts if (t.get('pnl') or 0)==0))
# confluence vocabulary
voc=C()
for t in ts:
    for s in (t.get('confluenceSignals') or []):
        voc[s.split(':')[0]]+=1
print('--- confluence prefixes (top 80):', voc.most_common(80))
print('--- exitReason full:', C(str(t.get('exitReason')) for t in ts).most_common(60))
