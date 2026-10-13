import sys, urllib.parse, urllib.request, json
js=open(sys.argv[1]).read()
r=urllib.request.urlopen('http://127.0.0.1:9333/eval?js='+urllib.parse.quote(js), timeout=60).read()
print(json.loads(r).get('value'))
