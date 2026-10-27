import pandas as pd, numpy as np, json
import matplotlib.pyplot as plt
from common import RES, FIG, DATA, AGES
C1,C2,C3,G="#2b6cb0","#dd6b20","#38a169","#718096"
S=json.load(open(RES/"summary.json"))
# 1 全国：粗は上がり、年齢別はすべて下がった
n3=pd.read_csv(RES/"r1b_national_3years.csv"); at=pd.read_csv(RES/"r1c_national_age_rates.csv",index_col=0)
fig,ax=plt.subplots(1,2,figsize=(11,4.4))
ax[0].plot(n3.year,n3.crude,"o-",color=C2,label="粗死亡率（そのまま）")
ax[0].plot(n3.year,n3.std2010,"o-",color=C1,label="年齢調整死亡率（2010年の人口構成）")
for x,a,b in zip(n3.year,n3.crude,n3.std2010):
    ax[0].text(x,a+0.15,f"{a:.1f}",ha="center",color=C2); ax[0].text(x,b-0.45,f"{b:.1f}",ha="center",color=C1)
ax[0].set_xticks([2010,2015,2020]); ax[0].set_ylabel("人口1,000人あたりの死亡"); ax[0].set_ylim(7,12.5); ax[0].legend(frameon=False,fontsize=9)
ax[0].set_title("全国：そのままでは上がり、年齢をそろえると下がる")
r=(at["2020"]/at["2010"]-1)*100
ax[1].barh(range(len(r)),r.values,color=C1); ax[1].set_yticks(range(len(r))); ax[1].set_yticklabels(r.index,fontsize=8); ax[1].invert_yaxis()
ax[1].axvline(0,color=G,lw=.8); ax[1].set_xlabel("2010→2020年の死亡率の変化（%）"); ax[1].set_title("19の年齢階級すべてで下がった")
fig.tight_layout(); fig.savefig(FIG/"f62_national.png",dpi=150); plt.close()
# 2 分解
t=pd.read_csv(RES/"r1_national_2010_2020.csv")
fig,ax=plt.subplots(figsize=(7.5,4))
x=np.arange(len(t)); w=.35
ax.bar(x-w/2,t.rate_effect,w,color=C1,label="年齢別の死亡率が下がった分")
ax.bar(x+w/2,t.composition_effect,w,color=C2,label="高齢の人が増えた分")
for i,(a,b) in enumerate(zip(t.rate_effect,t.composition_effect)):
    ax.text(i-w/2,a-0.3,f"{a:+.2f}",ha="center"); ax.text(i+w/2,b+0.1,f"{b:+.2f}",ha="center")
ax.axhline(0,color=G,lw=.8); ax.set_xticks(x); ax.set_xticklabels(["男女計","男","女"]); ax.set_ylabel("粗死亡率の変化への寄与（1,000人あたり）")
ax.set_title("2010→2020年の粗死亡率の変化を2つに分ける"); ax.legend(frameon=False,fontsize=9); ax.set_ylim(-2.5,4.2)
fig.tight_layout(); fig.savefig(FIG/"f62_decomp.png",dpi=150); plt.close()
# 3 都道府県 散布図
R=pd.read_csv(RES/"r2_pref_2020.csv")
fig,ax=plt.subplots(1,2,figsize=(11,4.4))
sc=ax[0].scatter(R.old,R.crude,c=R.direct,cmap="viridis",s=30)
ax[0].set_xlabel("65歳以上の割合（%）"); ax[0].set_ylabel("粗死亡率（1,000人あたり）"); ax[0].set_title(f"粗死亡率はほぼ高齢化率で決まる（順位相関 {S['pref2020']['rho_crude_old']:.2f}）")
plt.colorbar(sc,ax=ax[0],label="年齢調整死亡率")
ax[1].scatter(R.crude,R.direct,color=C1,s=30)
ax[1].set_xlabel("粗死亡率"); ax[1].set_ylabel("年齢調整死亡率（2020年全国の人口構成）")
ax[1].set_title(f"粗と年齢調整の順位相関は {S['pref2020']['rho_crude_direct']:.2f}")
fig.tight_layout(); fig.savefig(FIG/"f62_pref_scatter.png",dpi=150); plt.close()
# 4 順位の入れ替わり
fig,ax=plt.subplots(figsize=(6,6.5))
for _,r in R.iterrows():
    mv=abs(r.rank_crude-r.rank_direct)
    ax.plot([0,1],[r.rank_crude,r.rank_direct],color=C2 if mv>=20 else (C1 if mv>=10 else "#cbd5e0"),lw=1.6 if mv>=10 else 1)
ax.set_xticks([0,1]); ax.set_xticklabels(["粗死亡率の順位","年齢調整死亡率の順位"]); ax.set_ylabel("順位（1＝最も低い）"); ax.invert_yaxis()
ax.set_title(f"20位以上動いた県 {S['pref2020']['n_move20']}（橙）、10位以上 {S['pref2020']['n_move10']}（青＋橙）",fontsize=11)
fig.tight_layout(); fig.savefig(FIG/"f62_rank_shift.png",dpi=150); plt.close()
# 5 賃金
W=pd.read_csv(RES/"r5_wage_std.csv"); g=S["wage"]["gender_gap"]
fig,ax=plt.subplots(1,2,figsize=(11,4.2))
for sx,c in [("男",C1),("女",C2)]:
    z=W[W.sex==sx]; ax[0].scatter(z.crude,z["std"],color=c,s=22,label=f"{sx}性（順位相関 {S['wage'][sx]['rho']:.3f}）")
lim=[min(W.crude.min(),W["std"].min())-5,max(W.crude.max(),W["std"].max())+5]; ax[0].plot(lim,lim,color=G,lw=.8)
ax[0].set_xlabel("平均の所定内給与（そのまま、千円）"); ax[0].set_ylabel("年齢構成をそろえた平均（千円）"); ax[0].legend(frameon=False,fontsize=9)
ax[0].set_title("都道府県の賃金：年齢をそろえても順位はほぼ同じ")
v=[g["crude"]*100,g["std_female_ages"]*100,g["std_male_ages"]*100]
ax[1].bar(range(3),v,color=[C2,C1,C1]); [ax[1].text(i,x+.4,f"{x:.1f}%",ha="center") for i,x in enumerate(v)]
ax[1].set_xticks(range(3)); ax[1].set_xticklabels(["そのまま","女性の年齢構成で\nそろえる","男性の年齢構成で\nそろえる"]); ax[1].set_ylabel("男女の賃金差（%）"); ax[1].set_ylim(0,30)
ax[1].set_title("男女の賃金差は、年齢をそろえても少ししか縮まない")
fig.tight_layout(); fig.savefig(FIG/"f62_wage.png",dpi=150); plt.close()
# 6 頑健性
rb=pd.read_csv(RES/"r4_robust.csv")
lab={"national":"その年の全国","nat2010":"2010年の全国","prefmean":"47県の平均構成","uniform":"均等"}
fig,ax=plt.subplots(figsize=(9,4.2))
for k,(sx,c) in enumerate([("計",C1),("男",C3),("女",C2)]):
    z=rb[rb.sex==sx]
    ax.scatter(np.arange(len(z))+k*0.0,z.rho_crude_direct,color=c,label=sx if sx!="計" else "男女計",s=28)
z=rb[rb.sex=="計"]; ax.set_xticks(range(len(z))); ax.set_xticklabels([f"{y}\n{lab[s]}" for y,s in zip(z.year,z["std"])],fontsize=7)
ax.axhline(0,color=G,lw=.8); ax.set_ylabel("粗と年齢調整の順位相関"); ax.legend(frameon=False,fontsize=9)
ax.set_title("年・標準人口・男女を変えても、粗と年齢調整の順位は大きく食い違う")
fig.tight_layout(); fig.savefig(FIG/"f62_robust.png",dpi=150); plt.close()
print("ok")
