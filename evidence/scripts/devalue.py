# Decode Nuxt 3 devalue-style payload (array of nodes with index refs)
import json, sys
raw=json.load(open(sys.argv[1]))
cache={}
def rev(i, depth=0):
    if not isinstance(i,int) or i<0 or i>=len(raw) or depth>200: return i
    if i in cache: return cache[i]
    v=raw[i]
    if isinstance(v,list):
        if v and isinstance(v[0],str) and v[0] in ("ShallowReactive","Reactive","Ref","ShallowRef","Set","Map","Date","NaN","undefined"):
            if v[0]=="Date": out=v[1]
            elif v[0] in ("Set",): out=[rev(x,depth+1) for x in v[1:]]
            elif v[0]=="Map": out={rev(v[j],depth+1):rev(v[j+1],depth+1) for j in range(1,len(v)-1,2)}
            else: out=rev(v[1],depth+1) if len(v)>1 else None
        else:
            out=[rev(x,depth+1) for x in v]
    elif isinstance(v,dict):
        out={k:rev(x,depth+1) for k,x in v.items()}
    else:
        out=v
    cache[i]=out
    return out
root=rev(0)
json.dump(root, open(sys.argv[2],'w'), indent=1)
print('decoded ->', sys.argv[2])
