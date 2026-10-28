# 04_図
import sys, os, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, os.path.dirname(__file__)); from common import P, area
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in os.path.basename(f).replace(' ', ''): font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
S = json.load(open(P('results/summary.json')))
AC = {'東京圏': '#c0392b', '名古屋圏・大阪圏': '#d68910', '地方圏': '#2471a3'}
d = pd.read_csv(P('results/pref_2024.csv'), index_col=0)
note = '課税対象所得÷納税義務者数（社会・人口統計体系）と消費者物価地域差指数（小売物価統計調査 構造編）、2024年'
# 図1 散布図
fig, ax = plt.subplots(figsize=(8, 5))
for a, g in d.groupby('area'):
    ax.scatter(g.inc / 1000, g.price, s=36, color=AC[a], label=f'{a}（{len(g)}）', alpha=.85, edgecolor='white')
x = np.log(d.inc); b = np.polyfit(x, np.log(d.price / 100), 1)
xs = np.linspace(x.min(), x.max(), 50); ax.plot(np.exp(xs) / 1000, 100 * np.exp(np.polyval(b, xs)), color='k', lw=1.2)
ax.annotate('東京都', (d.inc[13] / 1000, d.price[13]), xytext=(-48, -4), textcoords='offset points', fontsize=9)
ax.set_xscale('log'); ax.set_xticks([3, 3.5, 4, 4.5, 5, 5.5]); ax.set_xticklabels(['300', '350', '400', '450', '500', '550'])
ax.set_xlabel('納税義務者1人当たりの課税対象所得（万円、対数目盛）'); ax.set_ylabel('消費者物価地域差指数（総合、全国＝100）')
m = S['main_2024']
ax.set_title(f"所得が10%高い県でも、物価は約{m['beta']*10:.1f}%しか高くない（傾き{m['beta']:.3f}）", fontsize=11.5)
ax.legend(frameon=False, fontsize=9, loc='upper left'); ax.grid(alpha=.3)
ax.text(0.99, 0.02, note, transform=ax.transAxes, ha='right', fontsize=6.5, color='gray')
fig.tight_layout(); fig.savefig(P('figures/fig1_income_vs_price.png'), dpi=150); plt.close()

# 図2 名目と実質（中央値＝1）の並び
d2 = d.sort_values('inc').copy()
d2['nom_rel'] = d2.inc / d2.inc.median(); d2['real_rel'] = d2.real / d2.real.median()
fig, ax = plt.subplots(figsize=(8, 5))
yy = np.arange(len(d2))
for i, (_, r) in enumerate(d2.iterrows()):
    ax.plot([r.nom_rel, r.real_rel], [i, i], color=AC[r.area], lw=1.2, alpha=.6)
ax.scatter(d2.nom_rel, yy, s=18, facecolor='white', edgecolor='k', lw=.8, label='名目（そのままの所得）', zorder=3)
ax.scatter(d2.real_rel, yy, s=18, c=[AC[a] for a in d2.area], label='実質（地域差指数で割った所得）', zorder=4)
ax.set_yticks([]); ax.set_ylabel('47都道府県（名目の所得の順）'); ax.set_xlabel('47都道府県の中央値との比')
ax.axvline(1, color='gray', lw=.8)
t = S['tokyo_2024']
ax.annotate(f"東京都：名目{t['nom_ratio']:.2f}倍 → 実質{t['real_ratio']:.2f}倍", (d2.real_rel.iloc[-1], len(d2) - 1), xytext=(-120, -60), textcoords='offset points', fontsize=9, arrowprops=dict(arrowstyle='->', color='gray'))
ax.set_title(f"物価で割っても、並びはほとんど変わらない（順位の相関{m['rho']:.3f}、5位以上動いたのは{S['rank_2024']['moved5']}県）", fontsize=10.5)
ax.legend(frameon=False, fontsize=9, loc='lower right'); ax.grid(alpha=.3, axis='x')
fig.tight_layout(); fig.savefig(P('figures/fig2_nominal_real.png'), dpi=150); plt.close()

# 図3 住居の重みと、物価が打ち消す所得の差の割合
sw = pd.read_csv(P('results/housing_weight_sweep.csv')); ht = pd.read_csv(P('results/household_types_2024.csv'))
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.plot(sw.housing_share * 100, sw.shrink * 100, color='#566573', lw=2)
for _, r in ht.iterrows():
    ax.scatter(r.housing_share * 100, r.shrink * 100, s=40, color='#c0392b' if '借家' in r.type else '#2471a3', zorder=3)
    if '借家' not in r.type: ax.annotate(r.type, (r.housing_share * 100, r.shrink * 100), xytext=(5, 3), textcoords='offset points', fontsize=8)
rr = ht[ht.type.str.contains('借家')]
ax.annotate('民営借家（総世帯・勤労者・単身）\n住居の割合27〜30%、縮む割合' + f"{rr.shrink.min()*100:.1f}〜{rr.shrink.max()*100:.1f}%", (rr.housing_share.mean() * 100, rr.shrink.mean() * 100),
            xytext=(-150, 25), textcoords='offset points', fontsize=8, arrowprops=dict(arrowstyle='-', color='gray'))
ax.set_xlabel('物価の重みのうち住居（家賃など）の割合（%）'); ax.set_ylabel('所得の差（標準偏差）が物価で縮む割合（%）')
ax.set_title('家賃の重い世帯ほど物価の差は効くが、それでも所得の差の15%ほど', fontsize=11.5)
ax.set_ylim(0, 20); ax.grid(alpha=.3)
ax.text(0.99, 0.02, '10大費目の地域差指数（2024年）を家計調査（2024年）の支出の割合で平均し直した', transform=ax.transAxes, ha='right', fontsize=7, color='gray')
fig.tight_layout(); fig.savefig(P('figures/fig3_housing_weight.png'), dpi=150); plt.close()

# 図4 年による違い
yt = pd.read_csv(P('results/by_year_taxable.csv')); kp = pd.read_csv(P('results/by_year_kenmin.csv'))
fig, ax = plt.subplots(figsize=(8, 4.5))
for col, c, lab in [('総合', '#c0392b', '課税対象所得 × 総合'), ('家賃を除く総合', '#e59866', '課税対象所得 × 家賃を除く総合')]:
    g = yt[yt.price == col]; ax.plot(g.year, g.shrink * 100, 'o-', color=c, label=lab, lw=2)
ax.plot(kp.year, kp.shrink * 100, 's--', color='#2471a3', label='1人当たり県民所得 × 総合', lw=1.5)
ax.plot(kp.year, kp.shrink_xr * 100, 's:', color='#7fb3d5', label='1人当たり県民所得 × 家賃を除く総合', lw=1.5)
ax.set_ylim(0, 12); ax.set_ylabel('所得の差が物価で縮む割合（%）'); ax.set_xticks(range(2013, 2025))
ax.set_title('どの年・どの所得の物差しでも、物価で縮むのは所得の差の1〜9%', fontsize=11.5)
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc='upper right'); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(P('figures/fig4_by_year.png'), dpi=150); plt.close()

# 図5 物価の差はどの費目から来るか（分散への寄与）と、都市で見たとき
vs = pd.Series(S['variance_share_2024']).sort_values()
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.6), gridspec_kw=dict(width_ratios=[1.2, 1]))
a1.barh(vs.index, vs.values * 100, color=['#c0392b' if i == '住居' else '#7f8c8d' for i in vs.index])
for i, v in enumerate(vs.values): a1.text(v * 100 + .5, i, f'{v*100:.0f}%', va='center', fontsize=8)
a1.set_xlabel('47都道府県の物価（総合）のばらつきへの寄与（%）'); a1.set_title('物価の差の4分の1が住居、4分の1強が食料', fontsize=10.5)
cc = pd.read_csv(P('results/city_2020.csv'), dtype={'code': str})
a2.scatter(cc.inc_tp / 1000, cc['総合'], s=22, color='#566573')
tk = cc[cc.code == '13100']
a2.scatter(tk.inc_tp / 1000, tk['総合'], s=30, color='#c0392b'); a2.annotate('東京都区部', (tk.inc_tp.iloc[0] / 1000, tk['総合'].iloc[0]), xytext=(-62, -2), textcoords='offset points', fontsize=8)
a2.set_xlabel('課税対象所得÷納税義務者（万円）'); a2.set_ylabel('地域差指数（総合）')
cs = S['city_2020']
a2.set_title(f"都市（{cs['n']}市、2020年）でも縮むのは{cs['shrink']*100:.0f}%", fontsize=10.5); a2.grid(alpha=.3)
a2.set_xticks([3, 4, 5, 6]); a2.set_xticklabels(['300', '400', '500', '600'])
fig.tight_layout(); fig.savefig(P('figures/fig5_components_city.png'), dpi=150); plt.close()
print('ok')
