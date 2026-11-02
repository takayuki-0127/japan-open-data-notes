"""04 図（Noto Sans CJK JP）"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
ROOT = pathlib.Path(__file__).resolve().parents[1]; R = ROOT/'results'; FIG = ROOT/'figures'; FIG.mkdir(exist_ok=True)
S = json.load(open(R/'summary.json'))
C = dict(stock='#c8553d', pop='#e0a03a', size='#4f7cac', rest='#9aa5b1', total='#2f3e46')
man = lambda v: v / 1e4

# 1 全国の要因分解（2003→2023 と 2008→2023）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
for ax, key, ttl in zip(axes, ['nat_2003_2023', 'nat_2008_2023'], ['2003→2023年', '2008→2023年']):
    n = S[key]
    labs = ['住宅ストック\nの増加', '人口の減少', '世帯の\n小型化', 'その他', '空き家の\n増加（実際）']
    vals = [n['c_stock'], n['c_pop'], n['c_size'], n['c_rest']]
    cum = 0; xs = range(5)
    for i, v in enumerate(vals):
        ax.bar(i, man(abs(v)), bottom=man(cum) if v >= 0 else man(cum + v), color=[C['stock'], C['pop'], C['size'], C['rest']][i])
        ax.text(i, man(cum + max(v, 0)) + 15, f'{man(v):+,.0f}', ha='center', fontsize=9)
        if i < 3: ax.plot([i + 0.4, i + 0.6], [man(cum + v)] * 2, color='k', lw=0.6)
        cum += v
    ax.bar(4, man(n['dV']), color=C['total']); ax.text(4, man(n['dV']) + 15, f'{man(n["dV"]):+,.0f}', ha='center', fontsize=9, fontweight='bold')
    ax.set_xticks(list(xs)); ax.set_xticklabels(labs, fontsize=9); ax.axhline(0, color='k', lw=0.6); ax.set_title(ttl, loc='left')
axes[0].set_ylabel('空き家の増減への寄与（万戸）')
fig.suptitle('全国の空き家の増加を要因に分けると：住宅が世帯より多く増えた分が中心', x=0.01, ha='left', fontsize=12)
fig.tight_layout(); fig.savefig(FIG/'fig1_national_decomposition.png', dpi=150); plt.close()

# 2 都道府県：人口の伸びと空き家率の変化（2008→2023）
d = pd.read_csv(R/'decomp_pref_2008_2023.csv')
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
ax = axes[0]
sc = ax.scatter(d.pop_g * 100, d.d_vac_rate, c=(d.stock_g - d.hh_g) * 100, cmap='RdBu_r', vmin=-8, vmax=8, s=28, edgecolor='k', lw=0.3)
ax.axhline(0, color='k', lw=0.5); ax.axvline(0, color='k', lw=0.5)
ax.set_xlabel('人口（世帯人員）の増減率（%）'); ax.set_ylabel('空き家率の変化（ポイント）')
ax.set_title(f'人口の伸びと空き家率（相関 {S["corr_2008_2023"]["popg_vs_dvacrate"]:.2f}）', loc='left', fontsize=10)
cb = fig.colorbar(sc, ax=ax); cb.set_label('住宅の伸び − 世帯の伸び（ポイント）', fontsize=8)
ax = axes[1]
ax.scatter((d.stock_g - d.hh_g) * 100, d.d_vac_rate, s=28, color='#7d8b99', edgecolor='k', lw=0.3)
ax.axhline(0, color='k', lw=0.5); ax.axvline(0, color='k', lw=0.5)
ax.set_xlabel('住宅の増加率 − 世帯の増加率（ポイント）'); ax.set_ylabel('空き家率の変化（ポイント）')
ax.set_title(f'住宅と世帯の伸びの差と空き家率（相関 {S["corr_2008_2023"]["stockg_minus_hhg_vs_dvacrate"]:.2f}）', loc='left', fontsize=10)
fig.suptitle('都道府県（47）、2008→2023年', x=0.01, ha='left', fontsize=11)
fig.tight_layout(); fig.savefig(FIG/'fig2_pref_scatter.png', dpi=150); plt.close()

# 3 地方ブロック別の要因分解（2008→2023）
b = pd.read_csv(R/'decomp_region_2008_2023.csv').set_index('region')
order = ['北海道', '東北', '関東', '中部', '近畿', '中国', '四国', '九州・沖縄']; b = b.loc[order]
fig, ax = plt.subplots(figsize=(10, 4.4)); x = np.arange(len(b)); w = 0.18
for k, (col, lab) in enumerate([('c_stock', '住宅ストックの増加'), ('c_pop', '人口の増減'), ('c_size', '世帯の小型化'), ('dV', '空き家の増加（実際）')]):
    ax.bar(x + (k - 1.5) * w, man(b[col]), w, label=lab, color=[C['stock'], C['pop'], C['size'], C['total']][k])
ax.set_xticks(x); ax.set_xticklabels(order); ax.axhline(0, color='k', lw=0.6)
ax.set_ylabel('空き家の増減への寄与（万戸）'); ax.legend(ncol=4, fontsize=8, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.1))
ax.set_title('地方ブロック別（2008→2023年）：人口が減った地方でも、空き家の増加は人口要因より小さい', loc='left', fontsize=10)
fig.tight_layout(); fig.savefig(FIG/'fig3_region_decomposition.png', dpi=150); plt.close()

# 4 空き家の種類：全国の推移と、人口の伸びとの関係
nat = pd.read_csv(R/'national_trend.csv')
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axes[0]
ax.plot(nat.year, nat.other_rate, 'o-', color=C['stock'], label='その他の空き家（使い道のない空き家）')
ax.plot(nat.year, nat.rent_rate, 's-', color=C['size'], label='賃貸用の空き家')
ax.set_ylim(0, 8.5); ax.set_xticks(nat.year); ax.set_ylabel('総住宅数に対する割合（%）'); ax.legend(fontsize=8, frameon=False, loc='lower right')
ax.set_title('全国：種類別の空き家率', loc='left', fontsize=10)
ax = axes[1]
ax.scatter(d.pop_g * 100, d.d_other_rate, color=C['stock'], s=24, label=f'その他（相関 {S["corr_2008_2023"]["popg_vs_dother"]:.2f}）')
ax.scatter(d.pop_g * 100, d.d_rent_rate, color=C['size'], marker='s', s=24, label=f'賃貸用（相関 {S["corr_2008_2023"]["popg_vs_drent"]:.2f}）')
ax.axhline(0, color='k', lw=0.5); ax.axvline(0, color='k', lw=0.5)
ax.set_xlabel('人口（世帯人員）の増減率（%）'); ax.set_ylabel('種類別の空き家率の変化（ポイント）'); ax.legend(fontsize=8, frameon=False)
ax.set_title('都道府県、2008→2023年', loc='left', fontsize=10)
fig.tight_layout(); fig.savefig(FIG/'fig4_vacancy_types.png', dpi=150); plt.close()

# 5 回帰係数（人口減1世帯分あたり、空き家は何戸増えたか）
r = pd.DataFrame(S['regression']); r = r[r.coef.isin(['popl_s', 'popl_h'])].iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 4.4)); y = np.arange(len(r))
ax.errorbar(r.b, y, xerr=[r.b - r.lo, r.hi - r.b], fmt='o', color='#2f3e46', capsize=3)
ax.axvline(0, color='k', lw=0.5); ax.axvline(1, color=C['stock'], ls='--', lw=0.8); ax.text(1.0, len(r) - 0.4, '「減った分だけ」＝1', color=C['stock'], fontsize=8, ha='center')
ax.set_yticks(y); ax.set_yticklabels(r.spec, fontsize=8.5); ax.set_xlim(-0.95, 1.15)
ax.set_xlabel('人口の減少（世帯数に換算）1世帯分あたりの空き家の増加（戸）と95%区間')
ax.set_title('都道府県パネル（5年ごとの差分、47県×4期）', loc='left', fontsize=10)
fig.tight_layout(); fig.savefig(FIG/'fig5_regression.png', dpi=150); plt.close()
print('ok')
