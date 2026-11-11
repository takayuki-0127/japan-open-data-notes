import pandas as pd, json, os, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
plt.rcParams['font.family']='Noto Sans CJK JP'; plt.rcParams['axes.spines.top']=False; plt.rcParams['axes.spines.right']=False
B=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R=json.load(open(f'{B}/results/main.json')); F=f'{B}/figures'
# fig1 timeline（予定の60分の枠と、実際の記録）
plan=[('問いを分ける',0,10),('データを集める',10,15),('最初の答え',25,20),('確かめる',45,7),('1枚にまとめる',52,8)]
act=[1.5,0.5,0.5,1.0,0.5]  # 実際の記録（results/timeline_log.csv、分単位の時刻から。AI のコーディング支援あり）
fig,ax=plt.subplots(figsize=(10,3.8))
for i,(n,s0,w) in enumerate(plan):
    ax.barh(i-.18,w,left=s0,height=.34,color='#2f6fb3',alpha=.85,label='予定の枠' if i==0 else None); ax.text(s0+w+.6,i-.18,f'{w}分',va='center',fontsize=9)
    a0=sum(act[:i]); ax.barh(i+.18,act[i],left=a0,height=.34,color='#e67e22',label='実際（AIの支援あり）' if i==0 else None)
ax.legend(frameon=False,fontsize=9,loc='upper center')
ax.set_yticks(range(len(plan))); ax.set_yticklabels([p[0] for p in plan]); ax.invert_yaxis(); ax.set_xlim(0,70); ax.axvline(60,color='#c0392b',ls='--'); ax.text(60.5,4.3,'60分',color='#c0392b')
ax.set_xlabel('分'); ax.set_title('1時間の枠の予定（青）と実際（橙）。データとコードが手元にあり、計算は数分',fontsize=12); fig.tight_layout(); fig.savefig(f'{F}/fig1_timebox_plan.png',dpi=150); plt.close()
# fig2 recent yoy
y=pd.read_csv(f'{B}/results/A_yoy_recent.csv',index_col=0)
fig,ax=plt.subplots(figsize=(10,4.2)); ax.plot(y.index,y['全国'],'-o',ms=3,label='業界（全国）',color='#2f6fb3'); ax.plot(y.index,y['関東'],'-o',ms=3,label='業界（関東）',color='#7b8794')
ax.scatter(['2026-08'],[-1.0],s=90,color='#c0392b',zorder=5,label='あおばドラッグ（架空）8月 −1.0%'); ax.axhline(0,color='k',lw=.6)
ax.set_xticks(y.index[::3]); ax.tick_params(axis='x',rotation=45); ax.set_ylabel('前年同月比（%）'); ax.legend(frameon=False,fontsize=9); ax.set_title('ドラッグストア業界の前年同月比（直近24か月）と、架空チェーンの8月',fontsize=12)
fig.tight_layout(); fig.savefig(f'{F}/fig2_industry_yoy.png',dpi=150); plt.close()
# fig3 item contribution
c=pd.Series(R['B_item_contrib']).sort_values()
fig,ax=plt.subplots(figsize=(10,4.4)); ax.barh(c.index,c.values,color=['#c0392b' if v<0 else '#2f6fb3' for v in c.values])
for i,v in enumerate(c.values): ax.text(v+(0.03 if v>=0 else -0.03),i,f'{v:+.2f}',va='center',ha='left' if v>=0 else 'right',fontsize=9)
ax.set_xlim(-0.6,1.35); ax.axvline(0,color='k',lw=.6); ax.set_xlabel('8月の前年同月比への寄与（ポイント）'); ax.set_title(f'業界の8月 +{R["A_industry_aug_yoy"]:.1f}% の内訳：食品と調剤で7割',fontsize=12); fig.tight_layout(); fig.savefig(f'{F}/fig3_item_contrib.png',dpi=150); plt.close()
# fig4 comparisons
cc=pd.Series(R['C_comparisons'])
fig,ax=plt.subplots(figsize=(10,4.2)); ax.barh(cc.index,cc.values,color='#2f6fb3'); ax.axvline(-1.0,color='#c0392b',ls='--'); ax.text(-0.95,-0.62,'あおばドラッグ（架空）−1.0%',color='#c0392b',fontsize=9)
for i,v in enumerate(cc.values): ax.text(v+.05,i,f'{v:+.2f}%',va='center',fontsize=9)
lo,hi=R['C_mix_range_5_95']; ax.errorbar([(lo+hi)/2],[3],xerr=[[(hi-lo)/2]],fmt='none',color='k',capsize=4)
ax.invert_yaxis(); ax.set_xlim(-1.6,4.2); ax.set_xlabel('業界の8月の前年同月比（%）'); ax.set_title('比べ方を変えても、業界との差は3〜4ポイント残る',fontsize=12); fig.tight_layout(); fig.savefig(f'{F}/fig4_comparisons.png',dpi=150); plt.close()
# fig5 landing
L=pd.read_csv(f'{B}/results/D_annual_landing.csv'); L['lab']=L.モデル+'\n('+L.学習の始まり.str[:4]+'〜)'
fig,ax=plt.subplots(figsize=(10,4.2)); ax.bar(L.lab,L['2026年の着地_前年比'],color='#2f6fb3'); ax.axhline(R['D_jan_aug_yoy'],color='#7b8794',ls='--'); ax.text(-0.4,R['D_jan_aug_yoy']+0.05,f'1〜8月の実績 +{R["D_jan_aug_yoy"]:.1f}%',color='#52606d',fontsize=9)
for i,v in enumerate(L['2026年の着地_前年比']): ax.text(i,v+.04,f'+{v:.2f}',ha='center',fontsize=9)
ax.set_ylim(3.5,5.0); ax.set_ylabel('2026年の業界の販売額（前年比、%）'); ax.set_title('業界の年間の着地は +4.2〜+4.6%。1〜8月の実績（+4.5%）の前後',fontsize=12); ax.tick_params(axis='x',labelsize=8)
fig.tight_layout(); fig.savefig(f'{F}/fig5_annual_landing.png',dpi=150); plt.close()
