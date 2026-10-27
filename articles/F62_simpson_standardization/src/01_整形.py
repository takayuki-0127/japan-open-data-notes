"""生命表（F49）と人口（F45＝社人研の基準人口）から、都道府県×男女×5歳階級の死亡率・人口・死亡数を作る"""
import pandas as pd, numpy as np
from common import RAW, DATA, AGES
lt = pd.read_csv(RAW/"lifetables_f49.csv")
lt["g"] = np.minimum(lt.age//5, 18)
# 5歳階級の死亡率 m = Σdx / ΣLx（90+ は開いた年齢の Lx＝Tx を含む）
m = lt.groupby(["year","pref_code","pref","sex","g"]).agg(dx=("dx","sum"),Lx=("Lx","sum")).reset_index()
m["m"] = m.dx/m.Lx
src = {2010:("pop_2013_pref.csv",2010), 2015:("pop_2018.csv",2015), 2020:("pop_2023.csv",2020)}
rows=[]
for y,(f,yy) in src.items():
    p = pd.read_csv(RAW/f); p = p[(p.kind.astype(str)=="a")&(p.year==yy)]
    cols=[c for c in p.columns if c.startswith("a") and c[1:].isdigit()]
    for _,r in p.iterrows():
        v=[r[c] for c in cols]
        v=v[:18]+[sum(v[18:])]          # 90歳以上にまとめる
        for g,x in enumerate(v):
            rows.append(dict(year=y,pref_code=int(r.code)//1000,sex={"M":"男","F":"女"}[r.sex],g=g,pop=x))
pop=pd.DataFrame(rows)
nat=pop.groupby(["year","sex","g"],as_index=False)["pop"].sum(); nat["pref_code"]=0
pop=pd.concat([pop,nat])
d=m.merge(pop,on=["year","pref_code","sex","g"],how="inner")
d["deaths"]=d.m*d["pop"]; d["age"]=d.g.map(lambda g:AGES[g])
d=d[["year","pref_code","pref","sex","g","age","pop","m","deaths"]].sort_values(["year","pref_code","sex","g"])
d.to_csv(DATA/"mortality_cells.csv",index=False)
print(d.groupby("year").pref_code.nunique(), d.shape)
