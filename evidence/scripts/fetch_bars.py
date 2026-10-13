# Fetch Massive 1-minute option bars for every trade's contract from entry date to exit date (+1 day margin for swings).
import json, os, sys, time, urllib.request, urllib.parse, datetime
SP=os.environ['SP']; KEY=os.environ['MASSIVE_API_KEY']
d=json.load(open(SP+'/evidence/public_api/trades_all.json')); ts=d['trades']
out=SP+'/evidence/validation/bars'; log=open(SP+'/evidence/validation/fetch_log.txt','a')
def get(url):
    req=urllib.request.Request(url, headers={'Authorization':'Bearer '+KEY})
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=40) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(15*(i+1)); continue
            return e.code, None
        except Exception as e: time.sleep(3)
    return 0, None
done=0; skipped=0; fail=0
for t in ts:
    sym=t.get('optionSymbol'); tid=t['id']
    f=f'{out}/{tid}.json'
    if not sym or os.path.exists(f): skipped+=1; continue
    e=t['entryTime'][:10]; x=(t.get('exitTime') or t['entryTime'])[:10]
    if x<e: x=e
    url=f'https://api.massive.com/v2/aggs/ticker/{urllib.parse.quote(sym)}/range/1/minute/{e}/{x}?adjusted=true&sort=asc&limit=50000'
    code,res=get(url)
    if code==200 and res is not None:
        json.dump({'trade_id':tid,'symbol':sym,'entryTime':t['entryTime'],'exitTime':t.get('exitTime'),'entryPremium':t.get('entryPremium'),'exitPremium':t.get('exitPremium'),'results':res.get('results',[]),'resultsCount':res.get('resultsCount')}, open(f,'w'))
        done+=1
    else:
        fail+=1; log.write(f'{tid} {sym} {e} {x} code={code}\n'); log.flush()
    if (done+fail)%25==0: log.write(f'progress done={done} fail={fail} skipped={skipped} {datetime.datetime.utcnow().isoformat()}\n'); log.flush()
    time.sleep(0.25)
log.write(f'FINISHED done={done} fail={fail} skipped={skipped}\n'); log.close()
print('FINISHED', done, fail, skipped)
