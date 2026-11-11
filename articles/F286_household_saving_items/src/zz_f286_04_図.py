"""F286 図"""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
for f in fm.findSystemFonts():
    if 'NotoSansCJK' in f or 'Noto Sans CJK' in f:
        fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
os.makedirs('figures', exist_ok=True)
R = json.load(open('results/main.json'))
A = pd.read_csv('results/A_items_avg.csv')
pct = lambda x: (np.exp(x) - 1) * 100

# 図5 食料の量（重みつき、2019年=0）
s = R['reask']['food_q_index_vs2019']
yrs = [int(k) for k in s]; v = [pct(s[k]) for k in s]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(yrs, v, marker='o', color='#2b6cb0')
ax.axhline(0, color='gray', lw=0.8)
ax.annotate('2020年は家で食べる量が増えた', (2020, v[yrs.index(2020)]), xytext=(2021.2, 5.0), arrowprops=dict(arrowstyle='->'))
ax.set_title('図5 食料の購入数量（121品目、2019年の支出で重みづけ、2019年＝0）')
ax.set_ylabel('2019年からの変化（%）'); ax.set_xticks(yrs)
fig.tight_layout(); fig.savefig('figures/fig1_food_quantity_index.png', dpi=150); plt.close()

# 図1 大分類別の分解
bb = pd.DataFrame(R['by_big']).sort_values('w', ascending=False)
bb = bb[bb.big.isin(['食料', '光熱・水道', '交通・通信', '住居', '被服及び履物', '家具・家事用品'])]
x = np.arange(len(bb)); wd = 0.25
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.bar(x - wd, pct(bb.wmean_dlq), wd, label='量', color='#2b6cb0')
ax.bar(x, pct(bb.wmean_dlcpi), wd, label='物価指数', color='#dd6b20')
ax.bar(x + wd, pct(bb.wmean_mix), wd, label='価格の差（平均価格−物価指数）', color='#38a169')
ax.axhline(0, color='gray', lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{b}\n({n}品目)" for b, n in zip(bb.big, bb.n)])
ax.set_ylabel('2020→2025年（%）'); ax.legend(fontsize=9)
ax.set_title('図1 大分類ごとの 量・物価指数・価格の差（支出の重みつき平均）')
fig.tight_layout(); fig.savefig('figures/fig2_decomposition_by_group.png', dpi=150); plt.close()

# 図2 食料：物価指数の上がり方と量の変化
F = A[(A.big == '食料') & A.dlcpi.notna()]
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.scatter(pct(F.dlcpi), pct(F.dlq), s=F.w * 4000, alpha=0.45, color='#2b6cb0')
for n in ['米', '牛肉', '豚肉', '鶏肉', 'ビール', '鶏卵', 'キャベツ', 'チョコレート', '食パン']:
    r = F[F.name == n]
    if len(r):
        ax.annotate(n, (pct(r.dlcpi.iloc[0]), pct(r.dlq.iloc[0])), fontsize=9)
ax.axhline(0, color='gray', lw=0.8)
ax.set_xlabel('物価指数の上がり方 2020→2025年（%）'); ax.set_ylabel('購入数量の変化（%）')
ax.set_title('図2 食料の品目：値上がりと量の変化（円の大きさは2020年の支出）')
fig.tight_layout(); fig.savefig('figures/fig3_food_price_vs_quantity.png', dpi=150); plt.close()

# 図3 量の減りの寄与 上位10
top = pd.DataFrame(R['H3']['top10'])
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.barh(top.name[::-1], top.qcontrib[::-1] * 100, color='#2b6cb0')
ax.set_xlabel('支出の重み × 量の変化（ポイント）')
ax.set_title(f"図3 量の減りの寄与が大きい10品目（減った{R['H3']['n_neg']}品目の合計の{R['H3']['top10_share']*100:.0f}%）")
fig.tight_layout(); fig.savefig('figures/fig4_top10_quantity_cuts.png', dpi=150); plt.close()

# 図4 収入五分位
q = R['H5']['by_quintile']; ks = ['q1', 'q2', 'q3', 'q4', 'q5']
x = np.arange(5)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(x - 0.18, [pct(q[k]['wmean_dlq']) for k in ks], 0.36, label='量', color='#2b6cb0')
ax.bar(x + 0.18, [pct(q[k]['wmean_mix']) for k in ks], 0.36, label='価格の差（平均価格−物価指数）', color='#38a169')
ax.axhline(0, color='gray', lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(['Ⅰ（低い）', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ（高い）'])
ax.set_ylabel('2020→2025年（%）'); ax.legend()
ax.set_title('図4 年間収入五分位別：量の変化と価格の差（支出の重みつき）')
fig.tight_layout(); fig.savefig('figures/fig5_by_income_quintile.png', dpi=150); plt.close()

# 図6 問い直し：前からの流れを引いた量の変化（食料、2019→2024年）
C = pd.read_csv('results/C_reask_food_trend.csv')
hi = (np.exp(C.dlprice) - 1) >= 0.10
fig, ax = plt.subplots(figsize=(8, 4.8))
bins = np.linspace(-80, 80, 33)
ax.hist(pct(C.excess[hi]).clip(-80, 80), bins=bins, alpha=0.6, label=f'平均価格が10%以上上がった品目（{hi.sum()}）', color='#dd6b20')
ax.hist(pct(C.excess[~hi]).clip(-80, 80), bins=bins, alpha=0.6, label=f'それ以外（{(~hi).sum()}）', color='#2b6cb0')
ax.axvline(0, color='gray', lw=0.8)
ax.set_xlabel('2019→2024年の量の変化 − 2014→2019年の量の変化（%、±80で切った）'); ax.set_ylabel('品目の数')
ax.set_title('図6 前からの流れを除いた量の変化（食料121品目、2019→2024年）')
ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig('figures/fig6_reask_excess_vs_trend.png', dpi=150); plt.close()
print('ok')
