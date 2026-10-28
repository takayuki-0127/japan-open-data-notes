import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, AGES

t1 = pd.read_csv(DATA/'cells_industry_size.csv')
S = json.load(open(RES/'summary.json', encoding='utf-8'))
rob = pd.read_csv(RES/'robustness.csv'); byage = pd.read_csv(RES/'by_age.csv'); comp = pd.read_csv(RES/'composition.csv')
CM, CW, CE, CU = '#2b6cb0', '#c05621', '#2f855a', '#a0aec0'

# 1 年齢別の所定内給与（産業計・規模計、学歴計を学歴セルから再集計）
x = t1[(t1.industry=='産業計')&(t1['size']=='計')].dropna(subset=['shoteinai','workers'])
g = x.groupby(['sex','age']).apply(lambda d: np.average(d.shoteinai, weights=d.workers), include_groups=False).unstack(0).reindex(AGES)
fig, ax = plt.subplots(figsize=(8,4.6))
ax.plot(range(len(AGES)), g['男'], 'o-', color=CM, label='男性'); ax.plot(range(len(AGES)), g['女'], 'o-', color=CW, label='女性')
ax2 = ax.twinx(); ax2.bar(range(len(AGES)), (g['女']/g['男'])*100, color='#e2e8f0', zorder=0, alpha=.9, label='女性÷男性（右軸）')
ax2.set_ylim(0,140); ax2.set_ylabel('女性÷男性（%）'); ax.set_zorder(ax2.get_zorder()+1); ax.patch.set_visible(False)
for i,v in enumerate((g['女']/g['男'])*100): ax2.text(i, v+2, f'{v:.0f}', ha='center', fontsize=8, color='#4a5568')
ax.set_xticks(range(len(AGES))); ax.set_xticklabels(AGES, rotation=45, fontsize=8); ax.set_ylabel('所定内給与額（千円／月）')
ax.set_title('年齢別の所定内給与額（一般労働者、2025年）'); ax.legend(loc='upper left')
fig.tight_layout(); fig.savefig(FIG/'f84_age_profile.png', dpi=150); plt.close()

# 2 基本の分解
b = S['oaxaca']['基本（男性の係数）']
items = list(b['detail'].items()) + [('説明できない部分', b['unexplained'])]
fig, ax = plt.subplots(figsize=(8,4.4))
vals = [v*100 for _,v in items]; labs=[k for k,_ in items]
cols = [CE if v>=0 else '#e53e3e' for v in vals[:-1]] + [CU]
ax.barh(range(len(vals))[::-1], vals, color=cols)
for i,v in enumerate(vals): ax.text(v+(0.3 if v>=0 else -0.3), len(vals)-1-i, f'{v:+.1f}', va='center', ha='left' if v>=0 else 'right', fontsize=9)
ax.set_yticks(range(len(vals))[::-1]); ax.set_yticklabels(labs); ax.axvline(0,color='k',lw=.8); ax.set_xlim(min(vals)-3, max(vals)+2.5)
ax.set_xlabel('対数の賃金差への寄与（×100、約％ポイント）')
ax.set_title(f'男女の賃金差（対数×100）{b["gap"]*100:.1f} の内訳：説明できる部分 {b["explained"]*100:.1f}（{b["share_explained"]*100:.0f}%）')
fig.tight_layout(); fig.savefig(FIG/'f84_decomposition.png', dpi=150); plt.close()

# 3 頑健性
rw = S['reweight']
r = rob[['setting','share_explained']].copy()
r = pd.concat([r, pd.DataFrame([{'setting':'組み替え（女性の賃金表）','share_explained':rw['share_w']},{'setting':'組み替え（男性の賃金表）','share_explained':rw['share_m']}])])
fig, ax = plt.subplots(figsize=(8,5))
ax.barh(range(len(r))[::-1], r.share_explained*100, color=[CE if i==0 else '#9ae6b4' for i in range(len(r))])
for i,v in enumerate(r.share_explained*100): ax.text(v+0.5, len(r)-1-i, f'{v:.0f}%', va='center', fontsize=9)
ax.set_yticks(range(len(r))[::-1]); ax.set_yticklabels(r.setting, fontsize=9); ax.set_xlim(0,60)
ax.set_xlabel('賃金差のうち「説明できる部分」の割合（%）'); ax.set_title('設定を変えても、説明できる部分は1〜4割')
fig.tight_layout(); fig.savefig(FIG/'f84_robustness.png', dpi=150); plt.close()

# 4 年齢別の分解
fig, ax = plt.subplots(figsize=(8,4.6))
idx = np.arange(len(byage))
ax.bar(idx, byage.explained*100, color=CE, label='説明できる部分（学歴・勤続・産業・規模）')
ax.bar(idx, byage.unexplained*100, bottom=np.where(byage.explained>0, byage.explained*100, 0), color=CU, label='説明できない部分')
ax.plot(idx, byage.gap*100, 'ko-', ms=4, label='男女差（対数×100）')
ax.axhline(0,color='k',lw=.6); ax.set_xticks(idx); ax.set_xticklabels(byage.age, rotation=45, fontsize=8)
ax.set_ylabel('対数の賃金差（×100）'); ax.set_title('年齢の中で分けると：差は40〜50代で大きく、多くは説明できない部分'); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG/'f84_by_age.png', dpi=150); plt.close()

# 5 構成の違い（勤続の平均、産業の割合）
c = pd.read_csv(RES/'coefficients.csv', index_col=0)
fig, axes = plt.subplots(1,2, figsize=(10,4.6))
ind = comp[comp['var']=='industry'].copy(); ind['diff']=(ind.women-ind.men)*100; ind=ind.sort_values('diff')
axes[0].barh(range(len(ind)), ind['diff'], color=[CW if v>0 else CM for v in ind['diff']])
axes[0].set_yticks(range(len(ind))); axes[0].set_yticklabels([s[:10] for s in ind.level], fontsize=8); axes[0].axvline(0,color='k',lw=.6)
axes[0].set_xlabel('女性の割合 − 男性の割合（ポイント）'); axes[0].set_title('働いている産業の違い')
m = S['means']
axes[1].bar([0,1],[m['男']['tenure'], m['女']['tenure']], color=[CM,CW]); axes[1].set_xticks([0,1]); axes[1].set_xticklabels(['男性','女性'])
for i,v in enumerate([m['男']['tenure'], m['女']['tenure']]): axes[1].text(i, v+0.2, f'{v:.1f}年', ha='center')
axes[1].set_ylabel('平均勤続年数（年）'); axes[1].set_title('勤続年数の違い（差の内訳でいちばん大きい）')
fig.tight_layout(); fig.savefig(FIG/'f84_composition.png', dpi=150); plt.close()
print('ok')
