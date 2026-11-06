import sys, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
W = sys.argv[1]; FD = sys.argv[2]
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']: fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
o = json.load(open(f'{W}/results/main.json'))
A = pd.read_csv(f'{W}/results/A_change_2006_2026.csv.gz')
BL, OR, GR, GY = '#2b6cb0', '#dd6b20', '#2f855a', '#718096'
# fig1 map
fig, ax = plt.subplots(figsize=(8, 8))
v = np.clip(np.expm1(A.dl) * 100, -60, 100)
sc = ax.scatter(A.lon, A.lat, c=v, cmap='RdBu_r', vmin=-60, vmax=60, s=3, alpha=.8, linewidths=0)
cb = plt.colorbar(sc, ax=ax, shrink=.6); cb.set_label('2006→2026年の変化（%）')
ax.set_xlim(127.5, 146); ax.set_ylim(26, 45.8); ax.set_aspect(1.2); ax.set_xticks([]); ax.set_yticks([])
ax.set_title(f'20年で地価が上がった地点（赤）と下がった地点（青）\n2006〜2026年に同じ地点が続いた{len(A):,}地点、上がったのは{o["A_share_up"]*100:.0f}%', fontsize=12)
fig.text(.02, .02, '出典：国土交通省「地価公示」（国土数値情報 L01-26）をもとに作成', fontsize=8, color=GY)
fig.savefig(f'{FD}/f207_1_map_20y.png', dpi=150, bbox_inches='tight'); plt.close()
# fig2 bins
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, key, ttl, xl in [(axs[0], 'A_bin_dm', '三大都市の中心からの距離', '中心からの距離'), (axs[1], 'A_bin_pc', '市区町村の人口の増減（2015→2020）', '人口の増減')]:
    dct = o[key]; lab = list(dct); med = [dct[k][2] for k in lab]; up = [dct[k][1] * 100 for k in lab]; n = [dct[k][0] for k in lab]
    cols = [OR if m > 0 else BL for m in med]
    ax.bar(range(len(lab)), med, color=cols)
    for i, (m, u, nn) in enumerate(zip(med, up, n)): ax.text(i, m + (3 if m > 0 else -3), f'{m:+.0f}%\n上昇{u:.0f}%', ha='center', va='bottom' if m > 0 else 'top', fontsize=8.5)
    ax.axhline(0, color='k', lw=.8); ax.set_xticks(range(len(lab))); ax.set_xticklabels(lab, fontsize=9); ax.set_title(ttl, fontsize=11); ax.set_ylabel('20年の変化（中央値、%）')
    ax.set_ylim(min(med) - 22, max(med) + 28)
fig.suptitle('上がった地点は「大都市の中心に近い」「人口が増えている」場所に集まった（住宅地・商業地）', fontsize=12)
fig.savefig(f'{FD}/f207_2_where_rose.png', dpi=150, bbox_inches='tight'); plt.close()
# fig3 decades
dc = o['A_decades']; up_up = dc['both_up']; dn_up = dc['down_then_up']; up_dn = dc['2006_16_up'] - up_up; dn_dn = 1 - up_up - dn_up - up_dn
fig, ax = plt.subplots(figsize=(8, 3.6))
parts = [('前の10年も後の10年も上昇', up_up, OR), ('前の10年は下落→後の10年は上昇', dn_up, '#f6ad55'), ('前の10年は上昇→後の10年は下落', up_dn, '#90cdf4'), ('どちらの10年も下落', dn_dn, BL)]
left = 0
for nm, val, col in parts:
    ax.barh(0, val * 100, left=left, color=col)
    if val > .02: ax.text(left + val * 50, 0, f'{val*100:.0f}%', ha='center', va='center', fontsize=11, color='white' if col in (OR, BL) else 'k')
    left += val * 100
ax.set_xlim(0, 100); ax.set_yticks([]); ax.set_xlabel('地点の割合（%）')
ax.legend([plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in parts], [n for n, _, _ in parts], ncol=2, fontsize=9, loc='upper center', bbox_to_anchor=(.5, -.35), frameon=False)
ax.set_title(f'2006→16年に上がった地点は{dc["2006_16_up"]*100:.0f}%、2016→26年は{dc["2016_26_up"]*100:.0f}%。\n後の10年の上昇の多くは「前の10年に下がった地点の戻り」だった', fontsize=11)
fig.savefig(f'{FD}/f207_3_two_decades.png', dpi=150, bbox_inches='tight'); plt.close()
# fig4 cv
cv = o['B_cv']; names = {'OLS_基本': '説明のモデル\n（回帰・7変数）', 'OLS_市区町村の人口も': '説明のモデル\n＋市区町村の人口', 'LightGBM': '当てるモデル\n（LightGBM・14変数）'}
fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(3); w = .36
for j, (k, lbl, col) in enumerate([('block', '場所で分けて確かめる', BL), ('random', 'ランダムに分けて確かめる', '#a0aec0')]):
    vals = [cv[m][k][0] * 100 for m in names]; ax.bar(x + (j - .5) * w, vals, w, color=col, label=lbl)
    for i, v in enumerate(vals): ax.text(i + (j - .5) * w, v + 1, f'{v:.0f}%', ha='center', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(names.values(), fontsize=9.5); ax.set_ylabel('外れの大きさ（中央値、%）'); ax.legend(frameon=False, fontsize=9)
ax.set_title('当てる力は、機械学習（LightGBM）が説明のモデルの半分以下の外れ', fontsize=11)
fig.savefig(f'{FD}/f207_4_explain_vs_predict.png', dpi=150, bbox_inches='tight'); plt.close()
# fig5 station distance effect -> % change 0km -> 1.72km (log1p(km)=1)
ef = o['B_eff']; lbl = {'OLS_基本': '回帰（7変数）', 'OLS_市区町村の人口も': '回帰＋市区町村の人口', 'OLS_緯度経度も': '回帰＋人口＋緯度経度', 'OLS_市区町村の固定効果': '回帰＋市区町村ごとの比較\n（固定効果）', 'LightGBM_平均の差分': 'LightGBM（平均の差分）'}
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ks = list(lbl); ys = np.arange(len(ks))[::-1]
for y, k in zip(ys, ks):
    b, se = ef[k]; pt = np.expm1(b) * 100
    if se: ax.errorbar(pt, y, xerr=[[pt - np.expm1(b - 1.96 * se) * 100], [np.expm1(b + 1.96 * se) * 100 - pt]], fmt='o', color=BL if 'OLS' in k else OR, capsize=4)
    else: ax.plot(pt, y, 'o', color=OR)
    ax.text(pt, y - .32, f'{pt:.0f}%', ha='center', fontsize=9)
ax.axvline(0, color='k', lw=.8); ax.set_yticks(ys); ax.set_yticklabels([lbl[k] for k in ks], fontsize=9.5); ax.set_xlabel('駅のすぐそば → 駅から約1.7km での地価の差（%）')
ax.set_title('「駅から離れると地価はどれだけ下がるか」の答えは、\n回帰では入れる変数しだいで−3%〜−32%と10倍変わった', fontsize=11)
fig.savefig(f'{FD}/f207_5_station_effect_models.png', dpi=150, bbox_inches='tight'); plt.close()
# fig6 event study
ev = o['C_event']; k = sorted(int(x) for x in ev); m = [ev[str(i)][0] * 100 for i in k]; lo = [ev[str(i)][1] * 100 for i in k]; hi = [ev[str(i)][2] * 100 for i in k]
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.fill_between(k, lo, hi, color=OR, alpha=.2); ax.plot(k, m, 'o-', color=OR, label='新しい駅から1km以内（ほかの駅から1km超）−比較の地点（1.5〜4km）')
ax.axhline(0, color='k', lw=.8); ax.axvline(-.5, color=GY, ls='--'); ax.text(-.4, max(hi) * .9, '開業後はじめての地価公示', fontsize=9, color=GY)
ax.set_xlabel('開業後はじめての公示からの年（0＝開業後はじめての公示）'); ax.set_ylabel('開業1年前の公示からの差（%）'); ax.set_xticks(k)
cm = o['C_main']
ax.set_title(f'新しい駅のそばの地価は、開業の「前」から比較の地点より伸びていた\n{cm["n_st"]}駅・{o["C_n_points"]["treat"]}地点。帯は駅を単位にしたブートストラップ95%区間', fontsize=11)
ax.legend(frameon=False, fontsize=8.5, loc='lower right')
fig.savefig(f'{FD}/f207_6_new_station_event.png', dpi=150, bbox_inches='tight'); plt.close()
print('ok')
