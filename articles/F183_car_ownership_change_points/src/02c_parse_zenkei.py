import json,re
d=json.load(open("../f183_zenkei_tables.json")); km=json.load(open("kei_raw.json")); air=json.load(open("pref_raw.json"))
P=list(air['2026'].keys())
out={}
for k,v in km.items():
    if k.endswith("-03") and v['maxdev']<0.02: out[k]={p:list(x) for p,x in v['data'].items()}
for k,v in d.items():
    m=re.match(r"(平成|令和)(元|\d+)年12月末",k)
    if not m: continue
    yy={'平成':1988,'令和':2018}[m.group(1)]+(1 if m.group(2)=='元' else int(m.group(2)))
    if yy<2015: continue
    res={}
    for line in v['tabs'].split("\n"):
        c=line.split("\t")
        if len(c)<3: continue
        nm=c[0].replace(" ","").replace("　","")
        if nm in P and nm not in res:
            res[nm]=[int(c[1].replace(",","")),int(c[2].replace(",",""))]
    out[f"{yy}-12"]=res; print(yy,len(res))
print(sorted(out), {k:len(v) for k,v in out.items()})
json.dump(out,open("kei.json","w"),ensure_ascii=False)
