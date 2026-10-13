# Massive cross-check fetch at <=5 requests/minute (observed plan limit); skips files already present.
import json, os, time, urllib.request, urllib.parse, datetime
SP=os.environ['SP']; KEY=os.environ['MASSIVE_API_KEY']
d=json.load(open(SP+'/evidence/public_api/trades_all.json')); ts=d['trades']
out=SP+'/evidence/validation/bars'; log=open(SP+'/evidence/validation/fetch_log.txt','a')
def get(url):
    req=urllib.request.Request(url, headers={'Authorization':'Bearer '+KEY})
    for i in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429,502,503,504): time.sleep(20); continue
            return e.code, None
        except Exception: time.sleep(5)
    return 0, None
ok=fail=skip=0
for t in ts:
    sym=t.get('optionSymbol'); tid=t['id']; f=f'{out}/{tid}.json'
    if not sym or os.path.exists(f): skip+=1; continue
    e=t['entryTime'][:10]; x=max((t.get('exitTime') or t['entryTime'])[:10], e)
    code,res=get(f'https://api.massive.com/v2/aggs/ticker/{urllib.parse.quote(sym)}/range/1/minute/{e}/{x}?adjusted=true&sort=asc&limit=50000')
    if code==200 and res is not None:
        json.dump({'trade_id':tid,'symbol':sym,'entryTime':t['entryTime'],'exitTime':t.get('exitTime'),'entryPremium':t.get('entryPremium'),'exitPremium':t.get('exitPremium'),'results':res.get('results',[]),'resultsCount':res.get('resultsCount')}, open(f,'w')); ok+=1
    else: fail+=1; log.write(f'{tid} {sym} {e} {x} code={code}\n'); log.flush()
    if (ok+fail)%20==0: log.write(f'slow progress ok={ok} fail={fail} skip={skip} {datetime.datetime.utcnow().isoformat()}\n'); log.flush()
    time.sleep(12.5)
log.write(f'SLOW FINISHED ok={ok} fail={fail} skip={skip}\n'); log.close(); print('FINISHED', ok, fail, skip)
