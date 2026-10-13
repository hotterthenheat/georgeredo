# Replay, inside the user's own authenticated page context, the GET /api/* calls the member pages made, and save sanitized bodies.
import json, glob, os, re, urllib.parse, urllib.request, time, sys
SP=os.environ['SP']; A=SP+'/evidence/auth_pages'; OUT=SP+'/evidence/auth_api'
skip=('/api/admin/','/api/auth/','/api/stripe/','/api/user/','/api/consent','/api/geo/','/api/access/','/api/promo/','/api/pricing/','/api/maintenance','/api/themes','/api/_nuxt_icon','/api/realtime','/api/options/prices','/api/account/','/api/analysis?','/api/analysis','/api/signals','/api/portfolio','/api/epochs','/api/plans/post-market')
urls={}
for f in sorted(glob.glob(A+'/*.net.json')):
    for x in json.load(open(f))['items']:
        if x['ev']=='res' and x['s']==200 and '/api/' in x['u']:
            u=x['u']; path=u.replace('https://georgefi.trade','')
            if any(path.startswith(s) or path==s.rstrip('?') for s in skip): continue
            if path.startswith('/api/analysis/') or path.startswith('/api/analysis?')==False and path not in urls: urls[path]=os.path.basename(f)[:-9]
            elif path not in urls: urls[path]=os.path.basename(f)[:-9]
print('replaying', len(urls), 'endpoints')
def ev(js):
    r=urllib.request.urlopen('http://127.0.0.1:9333/eval?js='+urllib.parse.quote(js), timeout=90).read(); return json.loads(r).get('value')
def red(s): 
    s=re.sub(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}','REDACTED_JWT',s)
    return re.sub(r'([?&](auth|token|access_token|apiKey|api_key)=)[^&"]+', r'\1REDACTED', s)
index=[]
for path,page in urls.items():
    js="(async()=>{try{const a=JSON.parse(localStorage.getItem('pocketbase_auth')||localStorage.getItem('pb_auth')||'{}');const h={};if(a&&a.token)h['Authorization']='Bearer '+a.token;const r=await fetch(%s,{credentials:'include',headers:h});const t=await r.text();return JSON.stringify({s:r.status,ct:r.headers.get('content-type')||'',body:t.slice(0,600000),len:t.length});}catch(e){return JSON.stringify({err:String(e)})}})()" % json.dumps(path)
    try: v=json.loads(ev(js) or '{}')
    except Exception as e: v={'err':str(e)}
    name=re.sub(r'[^A-Za-z0-9._-]+','_',path.replace('/api/','')).strip('_')[:120]
    body=red(v.get('body','')) if 'body' in v else ''
    open(f'{OUT}/{name}.json','w').write(body if body else json.dumps(v))
    index.append(dict(path=path, page=page, status=v.get('s'), ct=v.get('ct'), len=v.get('len'), file=name+'.json', err=v.get('err')))
    print(f"{v.get('s')}  {str(v.get('len')):>8}  {path[:110]}")
    time.sleep(0.4)
json.dump(index, open(OUT+'/_index.json','w'), indent=1)
