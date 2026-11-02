import numpy as np, pandas as pd, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from scipy.stats import norm
from common import RAW, DATA, RES, FIG
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: fm.fontManager.addfont(f)
plt.rcParams['font.family']='Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus']=False
est=pd.read_csv(RAW/'estimates_common_unit.csv'); emp=est[est.outcome=='emp']
mp=pd.read_csv(RES/'main_power.csv'); v=pd.read_csv(DATA/'variation.csv')
col={'F01':'#2b6cb0','F15':'#c05621','F17':'#2f855a','F89':'#553c9a'}
name={'F01':'F01 県×年の固定効果','F15':'F15 県境のペア','F17':'F17 因果フォレスト（前年差）','F89':'F89 3本の統合'}
# 図1：全仕様の推定値（弾力性）と文献の範囲
fig,ax=plt.subplots(figsize=(9,6)); y=0; yt=[];yl=[]
for s in ['F01','F15','F17']:
    d=emp[emp.study==s]
    for _,r in d.iterrows():
        ax.errorbar(r.est,y,xerr=1.96*r.se,fmt='o' if r.main else 's',color=col[s],ms=7 if r.main else 4,alpha=1 if r.main else .55,capsize=2)
        yt.append(y); yl.append(f"{s} {r.spec[:22]}"); y-=1
    y-=0.6
m=mp[mp.study=='F89'].iloc[0]; ax.errorbar(m.est,y,xerr=1.96*m.se,fmt='D',color=col['F89'],ms=8,capsize=3); yt.append(y); yl.append('F89 3本の統合')
ax.axvspan(-0.3,0,color='#f6e05e',alpha=.25,label='海外でよく報告される範囲（0〜−0.3）'); ax.axvline(0,color='gray',lw=.8)
ax.set_yticks(yt); ax.set_yticklabels(yl,fontsize=8); ax.set_xlim(-2.5,5); ax.set_xlabel('雇用の弾力性（最低賃金が1%上がると就業が何%変わるか）')
ax.set_title('17通りの推定：主な推定はどれも区間が広く、0も文献の範囲も含む'); ax.legend(loc='lower right',fontsize=8)
fig.tight_layout(); fig.savefig(FIG/'fig1_all_estimates.png',dpi=150); plt.close()
# 図2：識別に使えた最低賃金の変動
fig,ax=plt.subplots(figsize=(9,4.8))
lab=['F01 全体のばらつき\n（2008–19年）','F01 県と年の効果を\n除いたあと','F01 さらに県ごとの\nトレンドも除く','F15 接するペアの中の\n上昇率の差','F17 上昇率の\n年平均からのずれ']
f01=v[(v.study=='F01')&(v.period=='2008–2019')].iloc[0]
vals=[f01.sd_total_pct,f01.sd_resid_pct,f01.sd_resid_trend_pct,v[(v.study=='F15')&(v.n==724)].sd_resid_pct.iloc[0],v[v.study=='F17'].sd_resid_pct.iloc[0]]
cc=['#a0aec0',col['F01'],col['F01'],col['F15'],col['F17']]
b=ax.bar(lab,vals,color=cc)
for bb,x in zip(b,vals): ax.text(bb.get_x()+bb.get_width()/2,x+0.15,f'{x:.2f}%',ha='center',fontsize=9)
ax.set_ylabel('標準偏差（%）'); ax.set_title('比べるのに使えた最低賃金の差は、どの手法でも1%未満')
plt.xticks(fontsize=8); fig.tight_layout(); fig.savefig(FIG/'fig2_variation.png',dpi=150); plt.close()
# 図3：検出力の曲線
fig,ax=plt.subplots(figsize=(8,5)); t=np.linspace(0,0.6,121)
for _,r in mp.iterrows():
    pw=norm.cdf(t/r.se-1.96)+norm.cdf(-t/r.se-1.96); ax.plot(-t,pw,color=col[r.study],lw=2.2 if r.study=='F89' else 1.6,ls='--' if r.study=='F89' else '-',label=f"{name[r.study]}（MDE80={r.mde80:.2f}）")
ax.axhline(0.8,color='gray',ls=':',lw=1); ax.axvspan(-0.3,0,color='#f6e05e',alpha=.2)
ax.set_xlabel('本当の弾力性（マイナス＝雇用が減る）'); ax.set_ylabel('「差がある」と見つけられる確率'); ax.set_ylim(0,1)
ax.set_title('文献の範囲（0〜−0.3）の効果は、どの記事も80%では見つけられない'); ax.legend(fontsize=8,loc='upper left')
fig.tight_layout(); fig.savefig(FIG/'fig3_power_curves.png',dpi=150); plt.close()
# 図4：手法の違いで答えが動いた幅（記事の中）と、記事の間
w=pd.read_csv(RES/'within_study_spread.csv')
fig,ax=plt.subplots(figsize=(8,4.5))
for i,s in enumerate(['F01','F15','F17']):
    d=emp[emp.study==s]; ax.scatter([i]*len(d),d.est,color=col[s],alpha=.7); r=w[w.study==s].iloc[0]
    ax.vlines(i,r['min'],r['max'],color=col[s],lw=3,alpha=.35); ax.text(i+0.08,r['max'],f"幅 {r['range']:.2f}",fontsize=9)
ax.axhspan(-0.3,0,color='#f6e05e',alpha=.2); ax.axhline(0,color='gray',lw=.8)
ax.set_xticks([0,1,2]); ax.set_xticklabels([name[s] for s in ['F01','F15','F17']]); ax.set_ylabel('弾力性（仕様違いを含む）')
ax.set_title('同じ記事の中でも、仕様の選び方で答えが動く（F15 は特に大きい）')
fig.tight_layout(); fig.savefig(FIG/'fig4_within_spread.png',dpi=150); plt.close()
# 図5：標準誤差の分解の考え方（変動と標本の大きさ）
fig,ax=plt.subplots(figsize=(7.5,4.8))
pts=[('F01',f01.sd_resid_pct,mp[mp.study=='F01'].se.iloc[0],564),('F15',v[(v.study=='F15')&(v.n==724)].sd_resid_pct.iloc[0],mp[mp.study=='F15'].se.iloc[0],724),('F17',v[v.study=='F17'].sd_resid_pct.iloc[0],mp[mp.study=='F17'].se.iloc[0],611)]
for s,x,se,n in pts: ax.scatter(x,se,s=n/3,color=col[s]); ax.annotate(f"{name[s]}\n(n={n}、標準誤差 {se:.2f})",(x,se),textcoords='offset points',xytext=(10,-18) if s=='F15' else (8,4),fontsize=8)
ax.set_xlabel('比べるのに使えた最低賃金の変動（標準偏差、%）'); ax.set_ylabel('弾力性の標準誤差'); ax.set_ylim(0,1.1); ax.set_xlim(0.3,0.85)
ax.set_title('区間の広さは「使えた変動」と「結果のぶれ」で決まる\n（F15 は市区町村の雇用の伸びのぶれが大きい）',fontsize=11)
fig.tight_layout(); fig.savefig(FIG/'fig5_se_vs_variation.png',dpi=150); plt.close()
print('ok')
