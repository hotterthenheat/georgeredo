# T6: forward contract returns after public-tape alerts, by subsystem/kind/direction, using UW 1-minute bars (close of alert minute -> +15m, +60m, 15:55 ET).
import csv, json, os, datetime, statistics, collections
SP=os.environ['SP']; ET=datetime.timezone(datetime.timedelta(hours=-4))
def P(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
cache={}
def bars(cid, day):
    k=(cid,day)
    if k in cache: return cache[k]
    f=f'{SP}/evidence/validation/uw_tape_bars/{cid}_{day}.json'
    if not os.path.exists(f): cache[k]=None; return None
    b=[]
    for r in json.load(open(f))['data']:
        try: b.append((P(r['start_time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])))
        except: pass
    b.sort(); cache[k]=b; return b
def close_at(b, when):
    best=None
    for t,o,h,l,c in b:
        if t<=when: best=c
        else: break
    return best
rows=list(csv.DictReader(open(SP+'/evidence/analysis/public_tape_signals.csv')))
out=[]
for r in rows:
    if not r['occ']: continue
    b=bars(r['occ'][2:], r['session'])
    if not b: continue
    at=P(r['at']); c0=close_at(b, at+datetime.timedelta(seconds=59))
    if not c0: continue
    eod=at.astimezone(ET).replace(hour=15,minute=55,second=0,microsecond=0).astimezone(datetime.timezone.utc)
    if r['expiry']!=r['session']: eod=b[-1][0]  # non-0DTE: use last bar of session
    c15=close_at(b, at+datetime.timedelta(minutes=15)); c60=close_at(b, at+datetime.timedelta(minutes=60)); cE=close_at(b, eod)
    mfe=max([h for t,o,h,l,c in b if t>at], default=c0)/c0-1; mae=min([l for t,o,h,l,c in b if t>at], default=c0)/c0-1
    out.append(dict(session=r['session'], subsystem=r['subsystem'], kind=r['kind'], direction=r['direction'], loud=r['loud'], ticker=r['ticker'], occ=r['occ'], c0=c0, r15=(c15/c0-1) if c15 else None, r60=(c60/c0-1) if c60 else None, rE=(cE/c0-1) if cE else None, mfe=mfe, mae=mae, dte0=(r['expiry']==r['session'])))
print('alerts with bars:', len(out), 'of', sum(1 for r in rows if r['occ']))
def summ(v, lab):
    v=[x for x in v if x is not None]
    if len(v)<5: return
    print(f'   {lab:52} n={len(v):4d} mean={100*statistics.mean(v):+6.1f}% med={100*statistics.median(v):+6.1f}% pos={100*sum(1 for x in v if x>0)/len(v):4.0f}%')
for sub in ['sus-strike','momentum-ignition','index-read','relative-burst','block-sniper','moc-wick','big-print','accumulation-sniper','trade-now','hold-advisor']:
    v=[o for o in out if o['subsystem']==sub]
    if not v: continue
    print(f'=== {sub} (n={len(v)})')
    for lab,f in [('+15m',lambda o:o['r15']),('+60m',lambda o:o['r60']),('to 15:55 / last bar',lambda o:o['rE']),('MFE',lambda o:o['mfe']),('MAE',lambda o:o['mae'])]: summ([f(o) for o in v], lab)
    # by direction (the contract itself is the play; direction LONG means calls expected to gain)
    for dirn in ['LONG','SHORT','NEUTRAL','']:
        vv=[o for o in v if o['direction']==dirn]
        if len(vv)>=5: summ([o['r60'] for o in vv], f'  direction={dirn or "(none)"} +60m')
    for kind,n in collections.Counter(o['kind'] for o in v).most_common(6):
        vv=[o for o in v if o['kind']==kind]
        if len(vv)>=5: summ([o['r60'] for o in vv], f'  kind={kind[:40]} +60m'); summ([o['rE'] for o in vv], f'  kind={kind[:40]} to close')
# loud vs not
print('=== loud=True all subsystems'); summ([o['r60'] for o in out if o['loud']=='True'], 'loud +60m'); summ([o['rE'] for o in out if o['loud']=='True'], 'loud to close')
print('=== all 0DTE contracts baseline (every alert)'); summ([o['rE'] for o in out if o['dte0']], '0DTE alert contract to 15:55'); summ([o['rE'] for o in out if not o['dte0']], 'non-0DTE to last bar')
json.dump(out, open(SP+'/evidence/validation/tape_value_results.json','w'), default=str)
