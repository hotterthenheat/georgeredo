import json, sys
def shape(v, depth=0, maxdepth=6, seen=None):
    pad = '  '*depth
    if depth > maxdepth: return
    if isinstance(v, dict):
        for k, x in v.items():
            t = type(x).__name__
            extra = ''
            if isinstance(x, (str,int,float,bool)) or x is None:
                s = json.dumps(x); extra = ' = ' + (s[:120] + ('…' if len(s)>120 else ''))
            elif isinstance(x, list): extra = f' [len={len(x)}]'
            print(f'{pad}{k}: {t}{extra}')
            if isinstance(x, dict): shape(x, depth+1, maxdepth)
            elif isinstance(x, list) and x: 
                print(f'{pad}  [0]:'); shape(x[0], depth+2, maxdepth)
    elif isinstance(v, list) and v:
        shape(v[0], depth, maxdepth)
    else:
        s=json.dumps(v); print(pad + s[:200])
d = json.load(open(sys.argv[1]))
path = sys.argv[2:] 
for p in path:
    d = d[int(p)] if isinstance(d, list) else d[p]
shape(d, 0, int(6))
