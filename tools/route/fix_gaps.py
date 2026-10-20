"""Close sub-millimetre same-net track gaps that the SES round trip leaves (KiCad reports them as unconnected track-track pairs)."""
import sys, json, re, uuid
B=sys.argv[1]; DRC=sys.argv[2]
d=json.load(open(DRC)); s=open(B).read()
segs=[(m.start(), m.group(0), float(m.group(1)),float(m.group(2)),float(m.group(3)),float(m.group(4)),m.group(5),m.group(6),m.group(7)) for m in re.finditer(r'\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*\(width ([-\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net "([^"]*)"\)', s)]
add=[]; n=0
for x in d.get("unconnected_items",[]):
    items=x["items"]
    if len(items)!=2 or not all(i.get("description","").startswith("Track [") for i in items): continue
    net=items[0]["description"][items[0]["description"].find("[")+1:items[0]["description"].find("]")]
    cand=[g for g in segs if g[8]==net]
    best=None
    for a in cand:
        for b in cand:
            if a is b: continue
            for pa in [(a[2],a[3]),(a[4],a[5])]:
                for pb in [(b[2],b[3]),(b[4],b[5])]:
                    dist=((pa[0]-pb[0])**2+(pa[1]-pb[1])**2)**0.5
                    if 0.001<dist<1.6 and a[7]==b[7] and (best is None or dist<best[0]): best=(dist,pa,pb,a[6],a[7],net)
    if best:
        dist,pa,pb,w,layer,net=best
        add.append(f'\t(segment\n\t\t(start {pa[0]} {pa[1]})\n\t\t(end {pb[0]} {pb[1]})\n\t\t(width {w})\n\t\t(layer "{layer}")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n'); n+=1
if add:
    i=s.rstrip().rfind(")"); s=s[:i]+"".join(add)+s[i:]; open(B,"w").write(s)
print("gaps closed:", n)
