"""04 図：6枚。"""
import json, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); FIG = os.path.join(ROOT, 'figures'); os.makedirs(FIG, exist_ok=True)
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK' in f and 'Regular' in f:
        font_manager.fontManager.addfont(f); plt.rcParams['font.family'] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({'figure.dpi': 110, 'savefig.dpi': 150, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': 'f285'})
A = pd.read_csv(os.path.join(ROOT, 'data', 'processed', 'actuals.csv')).set_index('year')
P = pd.read_csv(os.path.join(ROOT, 'data', 'raw', 'projections.csv'))
D = pd.read_csv(os.path.join(ROOT, 'results', 'A_path_errors.csv'))
T = pd.read_csv(os.path.join(ROOT, 'results', 'B_target_year_errors.csv'))
L = pd.read_csv(os.path.join(ROOT, 'results', 'C_latest_errors.csv'))
RA = pd.read_csv(os.path.join(ROOT, 'results', 'D_reask_gdp_intensity.csv'))
COL = {1998: '#8c564b', 2001: '#9467bd', 2004: '#e377c2', 2008: '#d62728', 2010: '#ff7f0e', 2015: '#1f77b4', 2021: '#2ca02c', 2025: '#17becf'}
MAIN = {'demand': 'demand_fy', 'generation': 'gen_owid_cal_twh'}
def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(FIG, name), metadata={'Software': None}); plt.close(fig)
def ratio(r):
    return (1 + r.growth_rate) ** (r.target_year - r.base_year) if not np.isnan(r.growth_rate) else r.target_value / r.base_value
# 図1：実績（年度の電力需要の指数）と各見通しの道筋（実績の基準年に合わせる）
fig, ax = plt.subplots(figsize=(9, 5.2))
dem = A['demand_fy'].dropna(); base = dem.loc[2000]
ax.plot(dem.index, dem / base * 100, color='black', lw=2.4, label='実績（年度の電力需要、2000年度=100）')
for _, r in P.iterrows():
    if r.case_rank not in ('high', 'low') and r.vintage not in (2010, 2021):
        continue
    yrs = np.arange(r.base_year, r.target_year + 1); R = ratio(r)
    y = dem.loc[r.base_year] / base * 100 * R ** ((yrs - r.base_year) / (r.target_year - r.base_year))
    ax.plot(yrs, y, color=COL[r.vintage], lw=1.4, ls='-' if r.case_rank != 'low' else '--', alpha=0.9)
    ax.text(yrs[-1] + 0.3, y[-1], f"{r.vintage}", color=COL[r.vintage], fontsize=8, va='center')
ax.set_xlim(1990, 2043); ax.set_ylabel('2000年度=100'); ax.set_title('図1　見通しの道筋（実線＝高いケース、破線＝低いケース）と実績')
ax.legend(loc='upper left', fontsize=9, frameon=False); ax.grid(alpha=0.3)
save(fig, 'fig1_paths_vs_actual.png')
# 図2：目標年が来た見通しのずれ
fig, ax = plt.subplots(figsize=(9, 4.8))
t = T.copy(); t['lab'] = t.vintage.astype(str) + ' ' + t.case.str.replace('ケース', '') + f'\n→' + t.target_year.astype(str)
c = [COL[v] for v in t.vintage]
ax.barh(range(len(t)), t.err_pct, color=c); ax.set_yticks(range(len(t))); ax.set_yticklabels(t.lab, fontsize=8); ax.invert_yaxis()
ax.axvline(0, color='black', lw=0.8); ax.axvline(5, color='grey', lw=0.6, ls=':'); ax.axvline(-5, color='grey', lw=0.6, ls=':')
for i, v in enumerate(t.err_pct): ax.text(v + (0.6 if v >= 0 else -0.6), i, f'{v:+.1f}%', va='center', ha='left' if v >= 0 else 'right', fontsize=8)
ax.set_xlabel('見通しの伸び − 実績の伸び（%、＋は見通しが多すぎ）'); ax.set_title('図2　目標年が来た見通しのずれ（目標年の1年で比べた値）')
save(fig, 'fig2_target_errors.png')
# 図3：先の長さとずれ
fig, ax = plt.subplots(figsize=(8.5, 5))
for v, g in D.groupby('vintage'):
    ax.scatter(g.horizon, g.err_pct, s=8, color=COL[v], alpha=0.35)
for _, r in L.iterrows():
    ax.scatter(r.horizon, r.err_pct, s=40, color=COL[r.vintage], edgecolor='black', lw=0.6, zorder=3)
for v in sorted(D.vintage.unique()): ax.scatter([], [], color=COL[v], label=str(v))
ax.axhline(0, color='black', lw=0.8); ax.set_xlabel('先の長さ（比べる年 − 基準年、年）'); ax.set_ylabel('ずれ（%）')
ax.set_title('図3　先の年ほどずれは大きい（小さい点＝途中の年、大きい点＝最新か目標年）'); ax.legend(title='公表年', fontsize=8, ncol=2, frameon=False); ax.grid(alpha=0.3)
save(fig, 'fig3_horizon.png')
# 図4：高いケースと低いケース（目標年の1年／前後3年平均）
import json as _j
M = _j.load(open(os.path.join(ROOT, 'results', 'main.json')))
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
for ax, (key, ttl) in zip(axs, [('H', '目標年の1年'), ('R2', '目標年の前後3年平均')]):
    rows = M['H']['H3']['rows'] if key == 'H' else M['robust']['R2_avg3_at_target']['H3']['rows']
    x = np.arange(len(rows)); ax.bar(x - 0.2, [r['high_abs'] for r in rows], 0.4, color='#d62728', label='高いケース')
    ax.bar(x + 0.2, [r['low_abs'] for r in rows], 0.4, color='#1f77b4', label='低いケース（省エネ・対策を多く見込む）')
    ax.set_xticks(x); ax.set_xticklabels([str(r['vintage']) for r in rows]); ax.set_title(ttl)
axs[0].set_ylabel('ずれの大きさ（絶対値、%）'); axs[0].legend(fontsize=8, frameon=False)
fig.suptitle('図4　低いケースが近いかは、比べ方で入れ替わる（2004年の見通し）')
save(fig, 'fig4_high_vs_low.png')
# 図5：問い直し GDP と原単位
fig, ax = plt.subplots(figsize=(9, 4.8))
r = RA.copy(); r['lab'] = r.vintage.astype(str) + ' ' + r.case.str.replace('ケース', '') + '→' + r.year.astype(str)
y = np.arange(len(r)); ax.barh(y, r.err_gdp, color='#ff7f0e', label='GDPの前提のずれ')
ax.barh(y, r.err_intensity, left=np.where(r.err_intensity * r.err_gdp > 0, r.err_gdp, 0), color='#1f77b4', label='GDPあたりの電力（原単位）のずれ')
ax.scatter(r.err_total, y, color='black', zorder=3, s=18, label='合計のずれ')
ax.set_yticks(y); ax.set_yticklabels(r.lab, fontsize=8); ax.invert_yaxis(); ax.axvline(0, color='black', lw=0.8)
ax.set_xlabel('log差×100（＋は見通しが多すぎ）'); ax.set_title('図5　ずれの大半はGDPの前提から。原単位（省エネ）のずれは向きがまちまち'); ax.legend(fontsize=8, frameon=False, loc='lower right')
save(fig, 'fig5_reask_gdp_intensity.png')
# 図6：最近の見通し（2010・2015・2021・2025）と2024年度までの実績
fig, ax = plt.subplots(figsize=(9, 4.8))
for _, rr in P[P.vintage.isin([2010, 2015, 2021, 2025])].iterrows():
    col = MAIN[rr.metric]; s = A[col]; yrs = np.arange(rr.base_year, min(rr.target_year, 2032) + 1)
    yv = 100 * ratio(rr) ** ((yrs - rr.base_year) / (rr.target_year - rr.base_year))
    ax.plot(yrs, yv, color=COL[rr.vintage], ls='--' if rr.case_rank == 'low' else '-', lw=1.4)
    a = s.loc[rr.base_year:2024] / s.loc[rr.base_year] * 100
    ax.plot(a.index, a.values, color=COL[rr.vintage], lw=2.6, alpha=0.45)
    ax.text(yrs[-1] + 0.2, yv[-1], f'{rr.vintage} {rr.case}', fontsize=7, color=COL[rr.vintage], va='center')
ax.axhline(100, color='grey', lw=0.6); ax.set_xlim(2006, 2038); ax.set_ylabel('各見通しの基準年=100')
ax.set_title('図6　最近の見通しの道筋（細線）と実績（太線）'); ax.grid(alpha=0.3)
save(fig, 'fig6_recent_paths.png')
print('ok')
