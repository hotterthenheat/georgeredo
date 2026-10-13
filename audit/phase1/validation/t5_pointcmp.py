import re, sys
def parse(f):
    fam={}; claims={}; tail=[]
    for line in open(f):
        m=re.match(r'^(\S+)\s+(\d+)\s+(\d+) \|\s+(-?[\d.]+) /\s+(-?[\d.]+) \|\s+([+-][\d.]+) \[',line)
        if m: fam[m.group(1)]=tuple(m.group(2,3,4,5,6)); continue
        m=re.match(r'^   (.+?)\s+n=\s*(\d+) vs\s+(\d+):\s+(-?[\d.]+)% vs\s+(-?[\d.]+)% diff=([+-][\d.]+) \[',line)
        if m: claims[m.group(1).strip()]=tuple(m.group(2,3,4,5,6)); continue
        if line.startswith('---') or line.startswith('   ') : tail.append(line.rstrip())
    return fam, claims, tail
a=parse(sys.argv[1]); b=parse(sys.argv[2])
print('families tested line equal:', open(sys.argv[1]).readline()==open(sys.argv[2]).readline())
common=set(a[0])&set(b[0]); print('top-30 rows: committed', len(a[0]), 'regenerated', len(b[0]), 'common families', len(common), '| only committed:', sorted(set(a[0])-set(b[0])), '| only regenerated:', sorted(set(b[0])-set(a[0])))
print('point estimates (n_with,n_without,mean_with,mean_without,diff) equal on common rows:', all(a[0][k]==b[0][k] for k in common))
print('pre-registered claims: n', len(a[1]), len(b[1]), 'point estimates equal:', all(a[1][k]==b[1][k] for k in a[1]), '| mismatches:', [k for k in a[1] if a[1][k]!=b[1].get(k)])
ia=[l for l in a[2] if l.startswith('--- IS') or l.startswith('--- OOS')]; 
# IS/OOS block: compare the last 10 lines verbatim
la=open(sys.argv[1]).read().splitlines()[-10:]; lb=open(sys.argv[2]).read().splitlines()[-10:]
print('IS/OOS grade block (last 10 lines) identical:', la==lb)
