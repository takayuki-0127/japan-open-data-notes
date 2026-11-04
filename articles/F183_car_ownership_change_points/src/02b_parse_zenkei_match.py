import json,re,sys
import numpy as np
from scipy.optimize import linear_sum_assignment
W=sys.argv[1]
d=json.load(open(f"{W}/f183_zenkei_tables.json")); air=json.load(open("pref_raw.json"))
P=list(air['2026'].keys())
H2R={'平成':1988,'令和':2018}
out={}
for k,v in d.items():
    m=re.match(r"(平成|令和)(元|\d+)年(3|12)月末",k)
    if not m: continue
    yy=H2R[m.group(1)]+(1 if m.group(2)=='元' else int(m.group(2))); mo=int(m.group(3))
    ay=str(yy if mo==3 else yy+1)
    if ay not in air or len(air[ay])<47: 
        if ay not in air: continue
    rows=[]
    for line in v['tabs'].split("\n"):
        nums=re.findall(r"\d{1,3}(?:,\d{3})+",line)
        if len(nums)>=2:
            a,b=int(nums[0].replace(",","")),int(nums[1].replace(",",""))
            if 50000<b<9000000 and a<b*2: rows.append((a,b))
    rows=list(dict.fromkeys(rows))
    if len(rows)<44: print(k,ay,'rows',len(rows)); continue
    rows=rows[:60]
    prefs=[p for p in P if p in air[ay]]
    C=np.array([[abs(np.log(r[1]/air[ay][p][1])) for p in prefs] for r in rows])
    ri,ci=linear_sum_assignment(C)
    dev=C[ri,ci]
    key=f"{yy}-{mo:02d}"
    if key in out: key+="b"
    out[key]={"airia_year":int(ay),"maxdev":float(dev.max()),"n":len(ri),"data":{prefs[c]:rows[r] for r,c in zip(ri,ci) if C[r,c]<0.03}}
    print(key,ay,len(rows),len(out[key]['data']),round(float(np.median(dev)),4),round(float(dev.max()),4))
json.dump(out,open("kei_raw.json","w"),ensure_ascii=False)
