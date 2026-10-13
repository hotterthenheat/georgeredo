import json, sys, math
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
print('len', len(a), len(b), 'type', type(a).__name__)
def walk(x,y,path,diffs,maxabs):
    if isinstance(x,dict) and isinstance(y,dict):
        if set(x)!=set(y): diffs.append((path,'keys',sorted(set(x)^set(y))[:5])); return
        for k in x: walk(x[k],y[k],path+'.'+str(k),diffs,maxabs)
    elif isinstance(x,list) and isinstance(y,list):
        if len(x)!=len(y): diffs.append((path,'len',len(x),len(y))); return
        for i,(u,v) in enumerate(zip(x,y)): walk(u,v,path+f'[{i}]',diffs,maxabs)
    elif isinstance(x,(int,float)) and isinstance(y,(int,float)) and not isinstance(x,bool):
        d=abs(x-y); maxabs[0]=max(maxabs[0],d)
        if d>1e-9: diffs.append((path,x,y))
    elif x!=y: diffs.append((path,x,y))
diffs=[]; maxabs=[0.0]; walk(a,b,'',diffs,maxabs)
print('numeric max abs diff', maxabs[0], 'n diffs', len(diffs)); print(diffs[:10])
