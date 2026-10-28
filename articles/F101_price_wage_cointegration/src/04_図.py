"""04 図：5枚"""
import pandas as pd, numpy as np, matplotlib, pathlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
H=pathlib.Path(__file__).resolve().parents[1]; R=H/'results'; F=H/'figures'
C1,C2,C3,G='#2a6fb0','#d0703c','#5a9e6f','#888888'
def qx(s): return s.str[:4].astype(int)+(s.str[-1].astype(int)-1)/4

# 図1 1996年からの伸び
g=pd.read_csv(R/'growth_since_1996.csv'); x=qx(g.quarter)
fig,ax=plt.subplots(2,1,figsize=(8,6.2),sharex=True,gridspec_kw={'height_ratios':[2,1]})
ax[0].plot(x,g.wage_regular,color=C1,lw=2,label='賃金（きまって支給する給与）'); ax[0].plot(x,g.cpi_ex_rent,color=C2,lw=2,label='物価（持家の帰属家賃を除く総合）')
ax[0].axhline(100,color=G,lw=.8); ax[0].set_ylabel('1996年1〜3月＝100'); ax[0].legend(frameon=False,loc='upper left')
ax[0].set_title('図1　1996年からの賃金と物価（季節調整、四半期）',loc='left')
rw=g.wage_regular/g.cpi_ex_rent*100
ax[1].plot(x,rw,color=C3,lw=2); ax[1].axhline(100,color=G,lw=.8); ax[1].set_ylabel('実質賃金（同＝100）')
for t,lab in [(2013,'2013'),(2022,'2022')]: 
    for a in ax: a.axvline(t,color=G,ls=':',lw=.8)
fig.text(0.01,0.005,'出典：総務省「消費者物価指数」、厚生労働省「毎月勤労統計調査」（5人以上・調査産業計）を加工',fontsize=8,color=G)
fig.tight_layout(rect=(0,0.02,1,1)); fig.savefig(F/'fig1_levels.png'); plt.close()

# 図2 15年の窓をずらした EG の p 値
r=pd.read_csv(R/'rolling_eg.csv'); x=qx(r.end)
fig,ax=plt.subplots(figsize=(8,4.2))
ax.plot(x,r.p_const,color=C1,lw=2,label='定数だけ'); ax.plot(x,r.p_trend,color=C2,lw=1.6,ls='--',label='定数＋トレンド')
ax.axhline(0.05,color='k',lw=.8); ax.text(x.min(),0.07,'p＝0.05（これより下なら「長期の関係あり」）',fontsize=9)
ax.set_ylim(0,1.02); ax.set_xlabel('15年の窓の終わり'); ax.set_ylabel('Engle–Granger 検定の p 値')
ax.set_title('図2　15年ずつ区切って検定すると、2000年代以降はほぼ「関係なし」',loc='left'); ax.legend(frameon=False,loc='upper right')
fig.tight_layout(); fig.savefig(F/'fig2_rolling.png'); plt.close()

# 図3 期間ごとの検定結果（EG 18通りの p 値と Johansen のランク）
e=pd.read_csv(R/'engle_granger.csv'); j=pd.read_csv(R/'johansen.csv')
order=['1981–1995','1996–2019','1996–2026','2013–2026']
fig,ax=plt.subplots(figsize=(8,4.4))
rng=np.random.default_rng(0)
for i,p in enumerate(order):
    s=e[e.期間==p]; xx=i+rng.uniform(-.18,.18,len(s))
    ax.scatter(xx,s.p値,s=26,color=np.where(s.p値<0.05,C2,C1),alpha=.85)
    jj=j[j.期間==p]; ax.text(i,1.06,f'Johansen：{(jj.ランク>=1).sum()}/{len(jj)}通りで関係あり\nEG：{(s.p値<0.05).sum()}/{len(s)}通りで関係あり',ha='center',fontsize=8.5)
ax.axhline(0.05,color='k',lw=.8); ax.set_xticks(range(4)); ax.set_xticklabels(order); ax.set_ylim(0,1.18); ax.set_ylabel('Engle–Granger 検定の p 値')
ax.set_title('図3　期間ごとの検定（賃金3系列×物価3系列×トレンド2通り）',loc='left',pad=34)
fig.tight_layout(); fig.savefig(F/'fig3_tests_by_period.png'); plt.close()

# 図4 始まりの年を変える
b=pd.read_csv(R/'robust_2013.csv'); b=b[b.検証=='始まりの年']; sy=b.期間.str[:4].astype(int)
fig,ax=plt.subplots(1,2,figsize=(8.6,3.8))
ax[0].bar(sy,b.p値_近似,color=np.where(b.p値_近似<0.05,C2,C1)); ax[0].axhline(0.05,color='k',lw=.8)
ax[0].set_title('EG 検定の p 値',loc='left',fontsize=10); ax[0].set_xlabel('分析の始まりの年（終わりは2026年）')
ax[1].plot(sy,b.alpha_物価,'o-',color=C2,label='物価の戻り（α物価）'); ax[1].plot(sy,b.alpha_賃金,'o-',color=C1,label='賃金の戻り（α賃金）')
ax[1].axhline(0,color=G,lw=.8); ax[1].set_title('ずれへの反応（誤差修正の係数）',loc='left',fontsize=10); ax[1].legend(frameon=False,fontsize=8.5); ax[1].set_xlabel('分析の始まりの年')
fig.suptitle('図4　「2013年以降」の関係は、始まりの年を2012年以前にすると消える',x=0.01,ha='left',fontsize=12)
fig.tight_layout(); fig.savefig(F/'fig4_start_year.png'); plt.close()

# 図5 2013–2026 のずれと戻り方
ec=pd.read_csv(R/'ec_series.csv'); ec=ec.dropna(subset=['2013–2026']); x=qx(ec.quarter)
m=pd.read_csv(R/'ecm.csv'); m=m[(m.期間=='2013–2026')&(m.トレンド=='なし')]
fig,ax=plt.subplots(1,2,figsize=(8.8,3.9),gridspec_kw={'width_ratios':[1.6,1]})
ax[0].plot(x,ec['2013–2026']*100,color=C3,lw=2); ax[0].axhline(0,color=G,lw=.8)
ax[0].set_ylabel('長期の関係からのずれ（%）'); ax[0].set_title('賃金 −（0.64×物価）のずれ',loc='left',fontsize=10)
for t,l in [(2014.25,'消費税8%'),(2019.75,'消費税10%')]: ax[0].axvline(t,color=G,ls=':',lw=.8); ax[0].text(t+.1,ax[0].get_ylim()[1]*0.85,l,fontsize=8,color=G)
lab=[f'ラグ{L}' for L in m.ラグ]; xx=np.arange(len(m))
ax[1].bar(xx-0.18,m.alpha_w,0.36,color=C1,label='賃金'); ax[1].bar(xx+0.18,m.alpha_p,0.36,color=C2,label='物価')
for i,(pw,pp) in enumerate(zip(m.alpha_w_p,m.alpha_p_p)):
    ax[1].text(i-0.18,m.alpha_w.iloc[i]-0.06,'' if pw<0.05 else 'n.s.',ha='center',fontsize=8); ax[1].text(i+0.18,m.alpha_p.iloc[i]+0.02,'*' if pp<0.05 else 'n.s.',ha='center',fontsize=9)
ax[1].axhline(0,color=G,lw=.8); ax[1].set_ylim(-0.36,0.84); ax[1].set_xticks(xx); ax[1].set_xticklabels(lab); ax[1].legend(frameon=False,fontsize=8.5)
ax[1].set_title('ずれ1%への次の期の反応',loc='left',fontsize=10)
fig.suptitle('図5　2013〜2026年：ずれを埋めていたのは物価の側（*は5%で有意、n.s.は有意でない）',x=0.01,ha='left',fontsize=11.5)
fig.tight_layout(); fig.savefig(F/'fig5_ecm_2013.png'); plt.close()
print('ok')
