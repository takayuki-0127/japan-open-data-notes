"""04 図：figures/ に6枚"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f:
        fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(H, 'results')
F = os.path.join(H, 'figures')
os.makedirs(F, exist_ok=True)
O = json.load(open(os.path.join(R, 'main.json')))
BLUE, ORANGE, GRAY, GREEN, RED = '#2b6cb0', '#dd6b20', '#a0aec0', '#2f855a', '#c53030'

# 1 品目の寄与 上位15と下位5
A = pd.read_csv(os.path.join(R, 'A_item_contrib_2020_2025.csv'))
t = pd.concat([A.head(15), A.tail(5)]).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 7.5))
ax.barh(t.item, t.pp, color=[BLUE if v > 0 else ORANGE for v in t.pp])
for y, (v, c) in enumerate(zip(t.pp, t.chg_pct)):
    ax.text(v + (0.01 if v > 0 else -0.01), y, f'{v:+.2f}（値段 {c:+.0f}%）', va='center', ha='left' if v > 0 else 'right', fontsize=8.5)
ax.axvline(0, color='k', lw=.6)
ax.set_xlim(-1.6, 1.0)
ax.set_xlabel('物価全体の上昇（2020→2025年 +11.9%）への寄与（ポイント）')
ax.set_title('物価の上昇を押し上げた品目・押し下げた品目（582品目のうち上位15と下位5）', fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f209_1_item_contrib.png'), dpi=150); plt.close()

# 2 前年比の寄与：財とサービス（月次）
g = pd.read_csv(os.path.join(R, 'A_gs_monthly_yoy_contrib.csv'), dtype={'ym': str})
g['date'] = pd.to_datetime(g.ym, format='%Y%m')
parts = [('食料工業製品', '食料工業製品', '#2b6cb0'), ('生鮮商品', '生鮮商品', '#63b3ed'), ('他の農水畜産物', '他の農水畜産物（米など）', '#90cdf4'),
         ('電気・都市ガス・水道', '電気・ガス・水道', '#dd6b20'), ('石油製品', 'ガソリン・灯油など', '#f6ad55'),
         ('他の工業製品', '他の工業製品（家電・日用品など）', '#805ad5'), ('繊維製品', '衣類など', '#b794f4'), ('出版物', '出版物', '#d6bcfa')]
svc = ['公共サービス', '外食', '民営家賃', '持家の帰属家賃', '他のサービス']
g['サービス計'] = g[svc].sum(axis=1)
fig, ax = plt.subplots(figsize=(10, 5.2))
bot_p = np.zeros(len(g)); bot_n = np.zeros(len(g))
for col, lab, c in parts + [('サービス計', 'サービス（家賃・外食・通信料など）', '#2f855a')]:
    v = g[col].values
    b = np.where(v >= 0, bot_p, bot_n)
    ax.bar(g.date, v, bottom=b, width=25, color=c, label=lab)
    bot_p += np.where(v >= 0, v, 0); bot_n += np.where(v < 0, v, 0)
ax.plot(g.date, g.total_yoy, color='k', lw=1.6, label='物価全体の前年比')
ax.axhline(0, color='k', lw=.6)
ax.set_ylabel('前年同月比（%）とその内訳（ポイント）')
ax.set_title('前年比の内訳：物価を押し上げてきたのは主に「財」（2021年1月〜2026年9月）', fontsize=11)
ax.legend(fontsize=8, ncol=3, loc='upper left')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f209_2_goods_services_yoy.png'), dpi=150); plt.close()

# 3 世帯の区分別の物価上昇（2020→2025）
B = pd.read_csv(os.path.join(R, 'B_household_inflation.csv'))
mainv, w25 = '重み2020・2020→2025', '重み2025・2020→2025'
order = [('q5', '第Ⅰ五分位'), ('q5', '第Ⅱ五分位'), ('q5', '第Ⅲ五分位'), ('q5', '第Ⅳ五分位'), ('q5', '第Ⅴ五分位'), ('q5', '平均'),
         ('age', '29歳以下'), ('age', '30〜39歳'), ('age', '40〜49歳'), ('age', '50〜59歳'), ('age', '60〜69歳'), ('age', '70歳以上')]
lab, v1, v2 = [], [], []
for tab, l in order:
    lab.append(('収入 ' if tab == 'q5' else '年齢 ') + l)
    v1.append(B[(B.variant == mainv) & (B.tab == tab) & (B.label == l)].pct.iloc[0])
    v2.append(B[(B.variant == w25) & (B.tab == tab) & (B.label == l)].pct.iloc[0])
fig, ax = plt.subplots(figsize=(9.5, 5.2))
x = np.arange(len(lab))
cols = [BLUE] * 5 + [GRAY] + [GREEN] * 6
ax.bar(x, v1, color=cols, width=.62, label='2020年の買い方で計算')
ax.scatter(x, v2, color='k', zorder=3, s=22, label='2025年の買い方で計算')
for i, v in enumerate(v1):
    ax.text(i, v - 1.3, f'{v:.1f}', ha='center', fontsize=9, color='white', fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(lab, rotation=40, ha='right', fontsize=9)
ax.set_ylim(0, 19)
ax.set_ylabel('2020→2025年の物価上昇（%）')
ax.set_title('世帯の区分ごとの物価の上がり方（二人以上の世帯、持家の帰属家賃を除く）', fontsize=11)
ax.legend(fontsize=9, loc='upper left')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f209_3_household_inflation.png'), dpi=150); plt.close()

# 4 差の内訳（第Ⅰ−第Ⅴ五分位、70歳以上−29歳以下）
gq = pd.read_csv(os.path.join(R, 'B_gap_q1_minus_q5.csv'), index_col=0).iloc[:, 0]
ga = pd.read_csv(os.path.join(R, 'B_gap_age70_minus_u29.csv'), index_col=0).iloc[:, 0]
fig, axs = plt.subplots(1, 2, figsize=(11, 5.6))
for ax, s, ttl in [(axs[0], gq, f'収入の低い20% − 高い20%（差 {gq.sum():+.1f}pt）'), (axs[1], ga, f'70歳以上 − 29歳以下（差 {ga.sum():+.1f}pt）')]:
    s = pd.concat([s.head(4), s.tail(6)])
    ax.barh(s.index, s.values, color=[BLUE if v > 0 else ORANGE for v in s.values])
    ax.axvline(0, color='k', lw=.6)
    ax.set_title(ttl, fontsize=10.5)
    ax.set_xlabel('差への寄与（ポイント）')
    ax.tick_params(axis='y', labelsize=9)
fig.suptitle('物価の上がり方の差は、どの費目から来ているか（2020→2025年）', fontsize=11.5)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f209_4_gap_decomposition.png'), dpi=150); plt.close()

# 5 品目の値段の変化と購入数量の変化（2020→2024）
L = pd.read_csv(os.path.join(R, 'C_long_diff_2020_2024.csv'))
L['cp'] = (np.exp(L.dlp) - 1) * 100; L['cq'] = (np.exp(L.dlq) - 1) * 100
fig, ax = plt.subplots(figsize=(9, 6))
grp = L.group.unique()
cmap = plt.get_cmap('tab10')
for i, gname in enumerate(grp):
    x = L[L.group == gname]
    ax.scatter(x.cp, x.cq, s=np.sqrt(x.w) / 2.2, alpha=.65, color=cmap(i % 10), label=gname)
b = O['C_long_2020_2024']['b']
xs = np.linspace(L.dlp.min(), L.dlp.max(), 50)
a = np.average(L.dlq - b * L.dlp, weights=L.w)
ax.plot((np.exp(xs) - 1) * 100, (np.exp(a + b * xs) - 1) * 100, color='k', lw=1.4, label=f'当てはめ（傾き {b:.2f}）')
for _, r in L.iterrows():
    if r['name'] in ('たまねぎ', 'ほたて貝', 'オレンジ', 'あさり', '電気代', '米', 'マヨネーズ・マヨネーズ風調味料', '食用油', 'キャベツ', '牛乳', '鶏卵', 'ビール'):
        ax.annotate(r['name'].replace('・マヨネーズ風調味料', ''), (r.cp, r.cq), fontsize=8, xytext=(3, 3), textcoords='offset points')
ax.axhline(0, color='k', lw=.5); ax.axvline(0, color='k', lw=.5)
ax.set_xlabel('平均価格の変化（2020→2024年、%）')
ax.set_ylabel('購入数量の変化（%）')
ax.set_title('値段が大きく上がった品目ほど、買う量を減らしていた（130品目、円の大きさは支出）', fontsize=11)
ax.legend(fontsize=7.5, ncol=2, loc='lower left')
fig.tight_layout(); fig.savefig(os.path.join(F, 'f209_5_price_quantity.png'), dpi=150); plt.close()

# 6 弾力性の比較
C = pd.read_csv(os.path.join(R, 'C_elasticity.csv'))
lr = O['C_long_2020_2024']
C = pd.concat([C, pd.DataFrame([{'label': '長い差（2020→2024年の4年）', 'b': lr['b'], 'lo': lr['lo'], 'hi': lr['hi']}])])
C = C.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 6.2))
y = np.arange(len(C))
ax.errorbar(C.b, y, xerr=[C.b - C.lo, C.hi - C.b], fmt='o', color=BLUE, ecolor=GRAY, capsize=3)
ax.set_yticks(y); ax.set_yticklabels(C.label.str.replace('群:', '食料の群：'), fontsize=9)
ax.axvline(0, color='k', lw=.6); ax.axvline(-1, color=ORANGE, lw=.8, ls='--')
ax.text(-0.97, -0.75, '点線の−1：値段が1%上がると量も1%減り、支出は変わらない', fontsize=8, color=ORANGE, ha='left')
ax.set_ylim(-1.1, len(C) - .5)
ax.set_xlabel('値段が1%上がったときの購入数量の変化（%）＝価格弾力性（95%区間）')
ax.set_title('買う量の反応（価格弾力性）は、品目の群と見る期間で大きく違う', fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(F, 'f209_6_elasticity.png'), dpi=150); plt.close()
print('ok')
