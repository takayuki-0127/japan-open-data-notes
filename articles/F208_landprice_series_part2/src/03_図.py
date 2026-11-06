# 使い方：python src/03_図.py <この記事のフォルダ>
import sys, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
W = sys.argv[1]; FD = f'{W}/figures'
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
    try: fm.fontManager.addfont(f)
    except Exception: pass
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 11})
o = json.load(open(f'{W}/results/main.json'))
BL, OR, GR, GY, PU = '#2b6cb0', '#dd6b20', '#2f855a', '#718096', '#6b46c1'
SRC_A = '出典：国土交通省「不動産取引価格情報」（F182 で整形）、「地価公示」（国土数値情報 L01-26）をもとに作成'
SRC_B = '出典：国土交通省「地価公示」「駅別乗降客数」（国土数値情報）、総務省「令和2年国勢調査」をもとに作成'
def save(fig, name, src):
    fig.text(.01, -.01, src, fontsize=7.5, color=GY, ha='left', va='top'); fig.savefig(f'{FD}/{name}', dpi=150, bbox_inches='tight'); plt.close(fig)

# 1 national index
n = pd.read_csv(f'{W}/results/A_national_index.csv')
y0 = int(n.year.iloc[0] - 1)
yrs = [y0] + n.year.tolist()
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(yrs, [100] + n.condo_idx.tolist(), color=OR, lw=2.6, marker='o', label='中古マンション（築年数・広さなどをそろえた㎡単価）')
ax.plot(yrs, [100] + n.land_idx.tolist(), color=BL, lw=2.6, marker='o', label='同じ市区町村の住宅地の地価（翌年1月の公示）')
for ab, col in zip(['築0〜9年', '築30年以上'], ['#f6ad55', '#9c4221']):
    d = o['A_nat_by_age'][ab]; ks = sorted(int(k) for k in d)
    ax.plot([y0] + ks, [100] + [d[str(k)] for k in ks], color=col, lw=1.3, ls='--', label=f'マンションのうち{ab}')
ax.axhline(100, color=GY, lw=.8); ax.set_ylabel(f'{y0}年＝100'); ax.legend(fontsize=8.5, frameon=False, loc='upper left')
ax.set_title(f'マンションの値段は地価より速く上がった（{y0}→{yrs[-1]}年）\n取引のある市区町村の年ごとの変化を取引数で重みづけしてつないだ指数', fontsize=12)
save(fig, 'f208_1_condo_vs_land_index.png', SRC_A)

# 2 muni scatter cumulative
cu = pd.read_csv(f'{W}/results/A_muni_cumulative.csv', dtype={'muni': str})
fig, ax = plt.subplots(figsize=(7.2, 6))
cols = {'東京圏': OR, '大阪圏': GR, '名古屋圏': PU, '地方圏': BL}
for a, g in cu.groupby('area'):
    ax.scatter(np.expm1(g.dland) * 100, np.expm1(g.dcondo) * 100, s=np.clip(g.n / 40, 4, 120), alpha=.55, color=cols[a], label=a, linewidths=0)
lim = [-40, 120]; ax.plot(lim, lim, color=GY, lw=1, ls=':'); ax.text(95, 85, '同じだけ上がる線', fontsize=8, color=GY, ha='right')
xs = np.linspace(cu.dland.min(), cu.dland.max(), 50); ax.plot(np.expm1(xs) * 100, np.expm1(o['A_cum']['intercept'] + o['A_cum']['slope'] * xs) * 100, color='k', lw=1.5)
ax.set_xlim(-40, 120); ax.set_ylim(-40, 160)
ax.set_xlabel('住宅地の地価の変化（2017→2025年1月、%）'); ax.set_ylabel('中古マンションの㎡単価の変化（2016→2024年、%）')
ax.legend(frameon=False, fontsize=9, loc='upper left', title='点の大きさ＝取引数', title_fontsize=8)
c = o['A_cum']
ax.set_title(f'地価が上がった市区町村ほどマンションも上がったが、ほぼどこでも地価より上\n{c["n_muni"]}市区町村、マンションが地価を上回ったのは{c["share_condo_gt_land"]*100:.0f}%、黒線の傾き{c["slope"]:.2f}', fontsize=11)
save(fig, 'f208_2_muni_scatter.png', SRC_A)

# 3 slopes by age band + robustness
fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={'width_ratios': [1, 1.3], 'wspace': 0.55})
ab = o['A_slope_by_age']; ks = list(ab)
v = [ab[k][0] for k in ks]; lo = [ab[k][0] - ab[k][1] for k in ks]; hi = [ab[k][2] - ab[k][0] for k in ks]
axs[0].bar(ks, v, color=['#f6ad55', '#ed8936', '#c05621', '#9c4221'], yerr=[lo, hi], capsize=4)
axs[0].axhline(0, color=GY, lw=.8); axs[0].set_ylabel('地価が1%動いた年の、マンションの動き（%）')
axs[0].set_title('築年数別：同じ年の中で比べた連動の強さ\n（年の固定効果つき、線は95%区間）', fontsize=10.5, pad=12)
for i, x in enumerate(v): axs[0].text(i, 0.015, f'{x:.2f}', ha='center', fontsize=10, color='white', fontweight='bold')
axs[0].tick_params(axis='x', labelsize=9)
rb = o['A_rob']; rb = {('主の条件' if k.startswith('主') else k): v for k, v in rb.items()}; names = list(rb)
vals = [rb[k][0] for k in names]; l2 = [rb[k][0] - rb[k][1] for k in names]; h2 = [rb[k][2] - rb[k][0] for k in names]
yy = np.arange(len(names))[::-1]
axs[1].errorbar(vals, yy, xerr=[l2, h2], fmt='o', color=BL, capsize=3); axs[1].axvline(0, color=GY, lw=.8)
axs[1].set_yticks(yy); axs[1].set_yticklabels(names, fontsize=8.5); axs[1].set_xlabel('連動の強さ（地価1%あたり、%）')
axs[1].set_title('条件を変えても、地価1%に対して0.25〜0.43%\n（主の条件：住宅地、取引20件以上、公示は翌年1月）', fontsize=10.5)
save(fig, 'f208_3_link_by_age_and_robust.png', SRC_A)

# 4 map of misses
pt = pd.read_csv(f'{W}/results/B_point_miss.csv.gz', dtype={'code': str})
fig, ax = plt.subplots(figsize=(8, 8))
vv = np.clip(np.expm1(pt.e_mean) * 100, -40, 40)
sc = ax.scatter(pt.lon, pt.lat, c=vv, cmap='RdBu_r', vmin=-40, vmax=40, s=3, alpha=.8, linewidths=0)
cb = plt.colorbar(sc, ax=ax, shrink=.6); cb.set_label('外れの平均（%、赤＝予測が高すぎ、青＝低すぎ）')
ax.set_xlim(127.5, 146); ax.set_ylim(26, 45.8); ax.set_aspect(1.2); ax.set_xticks([]); ax.set_yticks([])
ax.set_title(f'毎年更新した予測の外れの向き（2018〜2026年の平均）\n{len(pt):,}地点。同じ色の点がまとまる＝場所ごとに同じ向きに外れ続けている', fontsize=11.5)
save(fig, 'f208_4_miss_map.png', SRC_B)

# 5 where misses: price decile & own change decile & area
fig, axs = plt.subplots(1, 3, figsize=(13, 4.4))
def bar(ax, d, title, xl, color):
    ks = list(d); v = [d[k][1] for k in ks]
    ax.bar(range(len(ks)), v, color=[OR if x > 0 else BL for x in v]); ax.axhline(0, color=GY, lw=.8)
    ax.set_xticks(range(len(ks))); ax.set_xticklabels(ks, fontsize=8, rotation=0 if len(ks) <= 5 else 0)
    ax.set_title(title, fontsize=10); ax.set_xlabel(xl, fontsize=9)
bar(axs[0], o['B_by_price_decile'], '地価の水準別（2017年、10等分）', '1＝安い … 10＝高い', OR)
axs[0].set_ylabel('外れの向きの中央値（%）\n＋は予測が高すぎ')
bar(axs[1], o['B_by_own_change_decile'], 'その地点の10年の変化別（10等分）', '1＝下がった … 10＝上がった', OR)
bar(axs[2], o['B_by_popchg'], '市区町村の人口の増減別（2015→20年）', '', OR)
for t in axs[2].get_xticklabels(): t.set_fontsize(7.5)
fig.suptitle('外れやすいのは「安い所は高めに、高い所は低めに」と「動いた所」', fontsize=12, y=1.03)
save(fig, 'f208_5_where_misses.png', SRC_B)

# 6 persistence and year trend
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
by = o['B_by_year']; ys = sorted(int(k) for k in by)
axs[0].plot(ys, [by[str(y)]['mape_med'] for y in ys], color=BL, marker='o', lw=2, label='外れの大きさ（中央値）')
axs[0].plot(ys, [by[str(y)]['bias_med'] for y in ys], color=OR, marker='o', lw=2, label='外れの向き（中央値、＋は高すぎ）')
axs[0].axhline(0, color=GY, lw=.8); axs[0].set_ylabel('%'); axs[0].legend(frameon=False, fontsize=9)
axs[0].set_title('前の年の公示で学習して当てた年ごとの外れ\n（見ていない場所、20km四方で分割）', fontsize=10.5)
pe = o['B_persistence_by_year']; py = sorted(int(k) for k in pe)
axs[1].bar([str(y) for y in py], [pe[str(y)] for y in py], color=PU)
axs[1].set_ylim(0, 1); axs[1].set_ylabel('同じ地点の、前の年の外れとの相関')
axs[1].set_title(f'同じ地点は毎年同じ向きに外れる（相関の平均{o["B_persistence_mean"]:.2f}）\n外れのばらつきのうち地点に固有の分 {o["B_stable_share"]*100:.0f}%', fontsize=10.5)
save(fig, 'f208_6_persistence.png', SRC_B)
print('ok')
