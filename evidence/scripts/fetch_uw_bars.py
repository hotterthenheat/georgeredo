# Fetch Unusual Whales 1-minute contract bars (OHLC + IV + side-of-trade premium) for each traded contract on its entry (and exit) date.
import json, os, time, urllib.request, urllib.parse, datetime, concurrent.futures, threading
SP=os.environ['SP']; KEY=os.environ['UW_API_TOKEN']
d=json.load(open(SP+'/evidence/public_api/trades_all.json')); ts=d['trades']
out=SP+'/evidence/validation/uw_bars'; lock=threading.Lock(); log=open(SP+'/evidence/validation/uw_fetch_log.txt','a')
def get(url):
    req=urllib.request.Request(url, headers={'Authorization':'Bearer '+KEY,'Accept':'application/json'})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429,502,503,504): time.sleep(5*(i+1)); continue
            return e.code, None
        except Exception: time.sleep(3)
    return 0, None
jobs=[]
for t in ts:
    sym=t.get('optionSymbol'); 
    if not sym: continue
    cid=sym[2:] if sym.startswith('O:') else sym
    days=sorted({t['entryTime'][:10], (t.get('exitTime') or t['entryTime'])[:10]})
    for day in days: jobs.append((t['id'], cid, day))
def work(j):
    tid,cid,day=j; f=f'{out}/{tid}_{day}.json'
    if os.path.exists(f): return 'skip'
    code,res=get(f'https://api.unusualwhales.com/api/option-contract/{cid}/intraday?date={day}')
    if code==200 and res is not None:
        json.dump({'trade_id':tid,'contract':cid,'date':day,'data':res.get('data',[])}, open(f,'w')); return 'ok'
    with lock: log.write(f'{tid} {cid} {day} code={code}\n'); log.flush()
    return 'fail'
c={'ok':0,'fail':0,'skip':0}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for i,r in enumerate(ex.map(work, jobs)):
        c[r]+=1
        if i%50==0:
            with lock: log.write(f'progress {c} of {len(jobs)} {datetime.datetime.utcnow().isoformat()}\n'); log.flush()
        time.sleep(0.05)
log.write(f'FINISHED {c}\n'); log.close(); print('FINISHED', c)
