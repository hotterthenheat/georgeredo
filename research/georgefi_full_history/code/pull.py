# Pull GET /api/* paths inside the user's own authenticated GeorgeFi page (token never leaves the page),
# preserve raw bodies (token/JWT/email-redacted) with sha256 + timestamp, append an index. Usage: pull.py OUTDIR path [path...]
import json, os, re, sys, time, hashlib, urllib.parse, urllib.request, datetime
OUT=sys.argv[1]; paths=sys.argv[2:]; os.makedirs(OUT, exist_ok=True)
EMAIL=os.environ.get('GEORGEFI_EMAIL','')
def ev(js):
    r=urllib.request.urlopen('http://127.0.0.1:9333/eval?js='+urllib.parse.quote(js), timeout=180).read(); return json.loads(r).get('value')
def red(s):
    s=re.sub(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}','REDACTED_JWT',s)
    s=re.sub(r'([?&](auth|token|access_token|apiKey|api_key)=)[^&"]+', r'\1REDACTED', s)
    if EMAIL: s=s.replace(EMAIL,'REDACTED_EMAIL')
    return s
idxf=OUT+'/_index.jsonl'
for path in paths:
    js="(async()=>{try{const a=JSON.parse(localStorage.getItem('pocketbase_auth')||localStorage.getItem('pb_auth')||'{}');const h={};if(a&&a.token)h['Authorization']='Bearer '+a.token;const t0=Date.now();const r=await fetch(%s,{credentials:'include',headers:h});const t=await r.text();return JSON.stringify({s:r.status,ct:r.headers.get('content-type')||'',ms:Date.now()-t0,body:t,len:t.length});}catch(e){return JSON.stringify({err:String(e)})}})()" % json.dumps(path)
    ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    try: v=json.loads(ev(js) or '{}')
    except Exception as e: v={'err':str(e)}
    body=red(v.get('body','')) if 'body' in v else ''
    name=re.sub(r'[^A-Za-z0-9._-]+','_',path.replace('/api/','')).strip('_')[:140]+'.json'
    open(f'{OUT}/{name}','w').write(body if body else json.dumps(v))
    rec=dict(ts_utc=ts, path=path, status=v.get('s'), ct=v.get('ct'), len=v.get('len'), ms=v.get('ms'), sha256=hashlib.sha256(body.encode()).hexdigest() if body else None, file=name, err=v.get('err'))
    open(idxf,'a').write(json.dumps(rec)+'\n')
    n=None
    try:
        d=json.loads(body); 
        if isinstance(d,dict):
            for k in ('trades','epochs','books','data','items'):
                if isinstance(d.get(k),list): n=f'{k}={len(d[k])}'; break
            if n is None: n='keys='+','.join(list(d.keys())[:12])
    except Exception: pass
    print(f"{v.get('s')}  {str(v.get('len')):>9}  {path[:100]}  {n or v.get('err','')}")
    time.sleep(0.5)
