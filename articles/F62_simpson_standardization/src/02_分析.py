"""粗死亡率・年齢調整死亡率（直接法）・SMR（間接法）、シンプソンのパラドックスの数え上げ、賃金の例"""
import pandas as pd, numpy as np, json, itertools
from scipy.stats import spearmanr
from common import DATA, RAW, RES
d = pd.read_csv(DATA/"mortality_cells.csv")
d["sexall"]="計"
both = d.groupby(["year","pref_code","pref","g","age"],as_index=False).agg(pop=("pop","sum"),deaths=("deaths","sum"))
both["m"]=both.deaths/both["pop"]; both["sex"]="計"
D = pd.concat([d.drop(columns="sexall"),both])
out={}

def rates(D, year, sex, std_pop):
    x=D[(D.year==year)&(D.sex==sex)&(D.pref_code>0)]
    nat=D[(D.year==year)&(D.sex==sex)&(D.pref_code==0)].set_index("g").m
    r=[]
    for (pc,pn),g in x.groupby(["pref_code","pref"]):
        g=g.set_index("g")
        crude=g.deaths.sum()/g["pop"].sum()*1e3
        direct=(g.m*std_pop).sum()/std_pop.sum()*1e3
        exp=(nat*g["pop"]).sum(); smr=g.deaths.sum()/exp*100
        old=g.loc[g.index>=13,"pop"].sum()/g["pop"].sum()*100   # 65歳以上
        r.append(dict(pref_code=pc,pref=pn,crude=crude,direct=direct,smr=smr,old=old))
    r=pd.DataFrame(r)
    for c in ["crude","direct","smr"]: r["rank_"+c]=r[c].rank()
    return r

def std(year,sex,which="national"):
    x=D[(D.sex==sex)&(D.pref_code==0)]
    if which=="national": return x[x.year==year].set_index("g")["pop"]
    if which=="nat2010": return x[x.year==2010].set_index("g")["pop"]
    if which=="prefmean":
        y=D[(D.year==year)&(D.sex==sex)&(D.pref_code>0)].copy()
        y["sh"]=y["pop"]/y.groupby("pref_code")["pop"].transform("sum")
        return y.groupby("g").sh.mean()
    if which=="uniform": return pd.Series(1.0,index=range(19))

# 1) 全国：粗死亡率は上がったが、年齢別はすべて下がった（時間のシンプソン）
nat=D[(D.pref_code==0)]
tab=[]
for s in ["計","男","女"]:
    a=nat[(nat.sex==s)&(nat.year==2010)].set_index("g"); b=nat[(nat.sex==s)&(nat.year==2020)].set_index("g")
    cr=lambda z:z.deaths.sum()/z["pop"].sum()*1e3
    stdp=a["pop"]
    dr=lambda z:(z.m*stdp).sum()/stdp.sum()*1e3
    fell=int((b.m<a.m).sum())
    # 粗死亡率の差の分解（Kitagawa）：率の差 × 平均構成 + 構成の差 × 平均率
    ca,cb=a["pop"]/a["pop"].sum(), b["pop"]/b["pop"].sum()
    rate_eff=((b.m-a.m)*(ca+cb)/2).sum()*1e3; comp_eff=((cb-ca)*(a.m+b.m)/2).sum()*1e3
    tab.append(dict(sex=s,crude2010=cr(a),crude2020=cr(b),std2010=dr(a),std2020=dr(b),age_groups_fell=fell,n_groups=19,rate_effect=rate_eff,composition_effect=comp_eff))
tab=pd.DataFrame(tab); tab.to_csv(RES/"r1_national_2010_2020.csv",index=False); out["national"]=tab.round(3).to_dict("records")
# 3時点
n3=[]
for y in [2010,2015,2020]:
    z=nat[(nat.sex=="計")&(nat.year==y)].set_index("g"); s0=nat[(nat.sex=="計")&(nat.year==2010)].set_index("g")["pop"]
    n3.append(dict(year=y,crude=z.deaths.sum()/z["pop"].sum()*1e3,std2010=(z.m*s0).sum()/s0.sum()*1e3,old=z.loc[z.index>=13,"pop"].sum()/z["pop"].sum()*100))
pd.DataFrame(n3).to_csv(RES/"r1b_national_3years.csv",index=False); out["national3"]=pd.DataFrame(n3).round(3).to_dict("records")
agetab=nat[(nat.sex=="計")&(nat.year.isin([2010,2020]))].pivot_table(index="age",columns="year",values="m",sort=False)*1e3
agetab.to_csv(RES/"r1c_national_age_rates.csv")

# 2) 都道府県：粗と年齢調整で順位が入れ替わる
R=rates(D,2020,"計",std(2020,"計"))
R.to_csv(RES/"r2_pref_2020.csv",index=False)
rho_cd=spearmanr(R.crude,R.direct)[0]; rho_co=spearmanr(R.crude,R.old)[0]; rho_ds=spearmanr(R.direct,R.smr)[0]
mv=(R.rank_crude-R.rank_direct).abs()
out["pref2020"]=dict(rho_crude_direct=rho_cd,rho_crude_old=rho_co,rho_direct_smr=rho_ds,
    crude_range=[R.crude.min(),R.crude.max()],direct_range=[R.direct.min(),R.direct.max()],
    crude_ratio=R.crude.max()/R.crude.min(),direct_ratio=R.direct.max()/R.direct.min(),
    median_rank_move=float(mv.median()),n_move10=int((mv>=10).sum()),n_move20=int((mv>=20).sum()))
# 粗では低いほう／年齢調整では高いほう、の逆転ペア
pairs=list(itertools.combinations(R.index,2))
rev=sum(1 for i,j in pairs if np.sign(R.crude[i]-R.crude[j])*np.sign(R.direct[i]-R.direct[j])<0)
out["pref2020"]["pairs"]=len(pairs); out["pref2020"]["reversed_pairs"]=rev

# 3) 本物のシンプソン：年齢別ではすべて（またはほぼすべて）低いのに、粗では高い
def simpson_pairs(year,sex,var="m",thr=19):
    x=D[(D.year==year)&(D.sex==sex)&(D.pref_code>0)]
    M=x.pivot(index="pref_code",columns="g",values="m")
    crude=x.groupby("pref_code")[["deaths","pop","g","m"]].apply(lambda z:z.deaths.sum()/z["pop"].sum())
    res=[]
    for i,j in itertools.permutations(M.index,2):
        lower=(M.loc[i]<M.loc[j]).sum()
        if lower>=thr and crude[i]>crude[j]: res.append((i,j,int(lower)))
    return res
sp={}
for thr in [19,17,15]:
    sp[thr]=len(simpson_pairs(2020,"計",thr=thr))
# 65歳以上の5つの階級（老年）だけで見た場合
x=D[(D.year==2020)&(D.sex=="計")&(D.pref_code>0)]
M=x.pivot(index="pref_code",columns="g",values="m"); crude=x.groupby("pref_code")[["deaths","pop","g","m"]].apply(lambda z:z.deaths.sum()/z["pop"].sum())
old_all=sum(1 for i,j in itertools.permutations(M.index,2) if (M.loc[i,13:]<M.loc[j,13:]).all() and crude[i]>crude[j])
out["simpson_pairs_2020"]=dict(all19_lower_but_crude_higher=sp[19],ge17=sp[17],ge15=sp[15],all_65plus_lower_but_crude_higher=old_all,ordered_pairs=47*46)

# 4) 頑健性：標準人口・年・男女で、粗と年齢調整の相関・逆転ペア
rob=[]
for year in [2010,2015,2020]:
    for sex in ["計","男","女"]:
        for w in ["national","nat2010","prefmean","uniform"]:
            r=rates(D,year,sex,std(year,sex,w))
            rv=sum(1 for i,j in itertools.combinations(r.index,2) if np.sign(r.crude[i]-r.crude[j])*np.sign(r.direct[i]-r.direct[j])<0)
            base=rates(D,year,sex,std(year,sex,"national"))
            rob.append(dict(year=year,sex=sex,std=w,rho_crude_direct=spearmanr(r.crude,r.direct)[0],
                rho_vs_nationalstd=spearmanr(r.direct,base.direct)[0],reversed_pairs=rv,
                top5_same=len(set(r.nlargest(5,"direct").pref_code)&set(base.nlargest(5,"direct").pref_code))))
rob=pd.DataFrame(rob); rob.to_csv(RES/"r4_robust.csv",index=False)
# 10歳階級
D10=D.copy(); D10["g"]=np.minimum(D10.g//2,9)
D10=D10.groupby(["year","pref_code","pref","sex","g"],as_index=False).agg(pop=("pop","sum"),deaths=("deaths","sum")); D10["m"]=D10.deaths/D10["pop"]
x=D10[(D10.year==2020)&(D10.sex=="計")]; s=x[x.pref_code==0].set_index("g")["pop"]
r10=x[x.pref_code>0].groupby("pref_code")[["deaths","pop","g","m"]].apply(lambda z:(z.set_index("g").m*s).sum()/s.sum()*1e3)
out["robust_10yr_rho_vs_5yr"]=spearmanr(r10.values,R.sort_values("pref_code").direct.values)[0]
out["robust_summary"]=dict(rho_crude_direct_range=[rob.rho_crude_direct.min(),rob.rho_crude_direct.max()],
    rho_vs_nationalstd_min=rob.rho_vs_nationalstd.min(),reversed_pairs_range=[int(rob.reversed_pairs.min()),int(rob.reversed_pairs.max())])

# 5) 賃金の例（F54 の 2020年 都道府県×男女×5歳階級、20〜64歳）
w=pd.read_csv(RAW/"wage_cells_f54.csv"); w=w.dropna(subset=["wage","workers"])
wt=[]
stdw=w.groupby("age").workers.sum()
for (p,sx),g in w.groupby(["pref","sex"]):
    g=g.set_index("age")
    wt.append(dict(pref=p,sex=sx,crude=(g.wage*g.workers).sum()/g.workers.sum(),std=(g.wage*stdw).sum()/stdw.reindex(g.index).sum(),
        share_45_59=g.loc[[a for a in g.index if a in("45-49","50-54","55-59")],"workers"].sum()/g.workers.sum()))
wt=pd.DataFrame(wt); wt.to_csv(RES/"r5_wage_std.csv",index=False)
ww={}
for sx in ["男","女"]:
    z=wt[wt.sex==sx]
    ww[sx]=dict(rho=spearmanr(z.crude,z["std"])[0],max_rank_move=float((z.crude.rank()-z["std"].rank()).abs().max()),
        median_rank_move=float((z.crude.rank()-z["std"].rank()).abs().median()))
# 男女差：粗と年齢をそろえた差
m_=w[w.sex=="男"].groupby("age")[["wage","workers"]].apply(lambda g:(g.wage*g.workers).sum()/g.workers.sum()); f_=w[w.sex=="女"].groupby("age")[["wage","workers"]].apply(lambda g:(g.wage*g.workers).sum()/g.workers.sum())
mc=(w[w.sex=="男"].wage*w[w.sex=="男"].workers).sum()/w[w.sex=="男"].workers.sum(); fc=(w[w.sex=="女"].wage*w[w.sex=="女"].workers).sum()/w[w.sex=="女"].workers.sum()
wf=w[w.sex=="女"].groupby("age").workers.sum(); wm=w[w.sex=="男"].groupby("age").workers.sum()
ww["gender_gap"]=dict(crude=1-fc/mc,std_female_ages=1-(f_*wf).sum()/(m_*wf).sum(),std_male_ages=1-(f_*wm).sum()/(m_*wm).sum())
out["wage"]=ww
json.dump(out,open(RES/"summary.json","w"),ensure_ascii=False,indent=1,default=float)
print(json.dumps(out,ensure_ascii=False,indent=1,default=lambda v:round(float(v),3))[:4000])
