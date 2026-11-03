"""04 図（Noto Sans CJK JP）"""
import numpy as np, pandas as pd, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
import importlib.util, sys
df = pd.read_csv('data/fit_pref_long.csv'); df = df[df.pref != '合計']
def tyear(d): y, m = map(int, d.split('-')); return y + m / 12 - 2012.5
df['t'] = df.date.map(tyear)
fits = pd.read_csv('results/fits_all.csv'); res = json.load(open('results/results.json'))
pm = pd.read_csv('results/pref_metrics.csv', index_col=0)
REGC = {'北海道': '#4C78A8', '東北': '#72B7B2', '関東': '#F58518', '中部': '#E45756', '近畿': '#B279A2', '中国': '#54A24B', '四国': '#EECA3B', '九州・沖縄': '#9D755D'}
S = {'res_cnt_new': '住宅用太陽光（10kW未満・件数）', 'big_kw_new': '事業用太陽光（10kW以上・容量）', 'wind_kw_new': '風力（容量）'}
COL = {'res_cnt_new': '#F58518', 'big_kw_new': '#4C78A8', 'wind_kw_new': '#54A24B'}
def bass(t, m, p, q):
    E = np.exp(-(p + q) * t); return m * (1 - E) / (1 + (q / p) * E)
def logistic(t, K, r, t0): return K / (1 + np.exp(-r * (t - t0)))
def gompertz(t, K, b, c): return K * np.exp(-b * np.exp(-c * t))
M = {'Bass': bass, 'ロジスティック': logistic, 'ゴンペルツ': gompertz}

# 図1 全国：2026年3月の水準を100とした累積と、Bass の当てはめ
fig, ax = plt.subplots(figsize=(8, 5))
nat = df.groupby(['series', 't']).value.sum().reset_index()
tt = np.linspace(0, 20, 400)
for s, lab in S.items():
    d = nat[nat.series == s].sort_values('t'); last = d.value.iloc[-1]
    ax.plot(d.t + 2012.5, d.value / last * 100, 'o', ms=3.5, color=COL[s], label=lab)
    f = fits[(fits.series == s) & (fits.pref == '全国') & (fits.model == 'Bass')].iloc[0]
    K = f.K; par = [K, f.p1, f.p2]
    ax.plot(tt + 2012.5, bass(tt, *par) / last * 100, '-', color=COL[s], lw=1.4, alpha=.8)
ax.axvline(2026.25, color='gray', lw=.8, ls=':'); ax.text(2026.35, 5, '観測の最後\n(2026年3月)', fontsize=8, color='gray')
ax.set_xlim(2012, 2032.5); ax.set_ylim(0, 220)
ax.set_ylabel('2026年3月末の累積を100とした値'); ax.set_xlabel('年')
ax.set_title('全国の累積導入量と Bass モデルの当てはめ（線は当てはめと延長）', fontsize=11)
ax.legend(frameon=False, fontsize=9, loc='upper left')
fig.tight_layout(); fig.savefig('figures/fig1_national_curves.png', dpi=150); plt.close()

# 図2 都道府県ごとの「自分の2026年3月の水準に対する割合」：事業用太陽光 vs 住宅用太陽光
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, s in zip(axes, ['big_kw_new', 'res_cnt_new']):
    for p, g in df[df.series == s].groupby('pref'):
        g = g.sort_values('t'); y = np.r_[0, g.value.values]; t = np.r_[0, g.t.values]
        ax.plot(t + 2012.5, y / y[-1] * 100, color=REGC[pm.loc[p, 'region']], lw=.8, alpha=.7)
    ax.axhline(50, color='gray', lw=.7, ls='--')
    ax.set_title(S[s], fontsize=11); ax.set_xlabel('年'); ax.set_xlim(2012.4, 2026.4)
axes[0].set_ylabel('その県の2026年3月末を100とした累積')
hs = [plt.Line2D([], [], color=c, lw=2) for c in REGC.values()]
axes[1].legend(hs, REGC.keys(), frameon=False, fontsize=8, ncol=2, loc='upper left')
fig.suptitle('47都道府県の普及の進み方（1本の線が1つの県）', fontsize=12)
fig.text(0.01, 0.01, '※2012年7月（制度開始）を0とし、観測点の間は直線でつないだ', fontsize=8, color='gray')
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig('figures/fig2_pref_curves.png', dpi=150); plt.close()

# 図3 予測の検証（2023年3月までで当てはめ→2026年3月の誤差）
v = pd.DataFrame(res['validation_mape_2026_03'])
order_m = ['Bass', 'ロジスティック', 'ゴンペルツ', '直線（直近2年の伸び）']
fig, ax = plt.subplots(figsize=(8.5, 4.6)); w = .2
for i, m in enumerate(order_m):
    vals = [v[(v.series == s) & (v.model == m)].median_ape.values[0] for s in S]
    b = ax.bar(np.arange(3) + (i - 1.5) * w, vals, w, label=m, color=['#4C78A8', '#72B7B2', '#B279A2', '#BAB0AC'][i])
    for x, val in zip(np.arange(3) + (i - 1.5) * w, vals): ax.text(x, val + .4, f'{val:.0f}', ha='center', fontsize=8)
ax.set_xticks(range(3)); ax.set_xticklabels([S[s] for s in S], fontsize=9)
ax.set_ylabel('2026年3月末の予測誤差（%、47県の中央値）')
ax.set_title('2023年3月までのデータで当てはめて、3年後を予測した誤差', fontsize=11)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig('figures/fig3_validation.png', dpi=150); plt.close()

# 図4 住宅用太陽光の普及（一戸建1000戸あたり件数）と日照時間
fig, ax = plt.subplots(figsize=(7.5, 5))
for r in REGC:
    g = pm[pm.region == r]
    ax.scatter(g.sunshine_h, g.res_per1000det, color=REGC[r], s=40, label=r, edgecolor='white', lw=.5)
rho = res['spearman']['res_per1000det']['sunshine_h']['rho']; ci = res['bootstrap_ci_spearman_sunshine']['res_per1000det']
ax.set_xlabel('年間の日照時間（県庁所在地、2012〜2024年の平均, 時間）'); ax.set_ylabel('一戸建1000戸あたりの件数（2026年3月末）')
ax.set_title(f'住宅用太陽光（新規認定分）と日照時間　順位相関 {rho:.2f}（95%区間 {ci[0]:.2f}〜{ci[1]:.2f}）', fontsize=10.5)
ax.legend(frameon=False, fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig('figures/fig4_res_sunshine.png', dpi=150); plt.close()

# 図5 風力の地方別シェア 2017年6月 → 2026年3月
reg = pd.DataFrame(res['region']).set_index('region')
fig, ax = plt.subplots(figsize=(8, 3.6))
left = np.zeros(2)
for r in REGC:
    vals = np.array([reg.loc[r, 'wind_share_2017'], reg.loc[r, 'wind_share']]) * 100
    ax.barh([1, 0], vals, left=left, color=REGC[r], label=r, edgecolor='white')
    for y, (l, vv) in enumerate(zip(left[::-1], vals[::-1])):
        if vv >= 6: ax.text(l + vv / 2, y, f'{r}\n{vv:.0f}%', ha='center', va='center', fontsize=8, color='white')
    left += vals
ax.set_yticks([1, 0]); ax.set_yticklabels(['2017年6月末', '2026年3月末']); ax.set_xlim(0, 100)
ax.set_xlabel('風力の導入容量（新規認定分）に占める割合（%）')
ax.set_title('風力はどの地方で増えたか', fontsize=11)
ax.legend(frameon=False, fontsize=8, ncol=8, loc='upper center', bbox_to_anchor=(.5, -.28))
fig.tight_layout(); fig.savefig('figures/fig5_wind_regions.png', dpi=150); plt.close()
print('ok')
