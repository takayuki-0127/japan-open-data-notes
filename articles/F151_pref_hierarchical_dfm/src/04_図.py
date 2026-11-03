"""図を作る"""
import json, re
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
B = Path(__file__).resolve().parents[1]; RS = B/'results'; FG = B/'figures'; FG.mkdir(exist_ok=True)
S = json.load(open(RS/'summary.json'))
C = {'nat': '#2e86ab', 'reg': '#f18f01', 'idio': '#c8ccd0', 'dark': '#333333', 'red': '#d1495b'}
ORDER = ['北海道・東北', '関東', '中部', '近畿', '中国', '四国', '九州・沖縄']

# 図1：固有値（何個の動きがあるか）
fig, ax = plt.subplots(figsize=(8, 4.2))
for key, lab, col in [('nfac_m1', '1か月の変化', C['nat']), ('nfac_m3', '3か月の変化', C['reg']), ('nfac_m12', '12か月の変化', C['red'])]:
    sh = np.array(S[key]['share']) * 100
    ax.plot(range(1, 9), sh, marker='o', color=col, lw=2, label=lab)
ax.set_xlabel('主成分の番号'); ax.set_ylabel('47県の動きのうち説明できる割合（%）')
ax.set_title('47都道府県の求人倍率の動きは、ほぼ「1つの全国の動き」\n（主成分ごとの説明割合。2番目以降は3%前後で横ばい）', fontsize=11)
ax.legend(); ax.grid(alpha=.3); ax.set_ylim(0, 90)
fig.tight_layout(); fig.savefig(FG/'fig1_scree.png', dpi=150); plt.close()

# 図2：県ごとの分解（地方の順に並べ、地方の中は全国の割合の順）
D = pd.read_csv(RS/'decomp_main.csv')
D['ro'] = D.region.map({r: i for i, r in enumerate(ORDER)})
D = D.sort_values(['ro', 'national'], ascending=[True, False]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(12, 5.4))
x = np.arange(len(D))
ax.bar(x, D.national * 100, color=C['nat'], label='全国の動き')
ax.bar(x, D.regional * 100, bottom=D.national * 100, color=C['reg'], label='地方の動き')
ax.bar(x, D.idio * 100, bottom=(D.national + D.regional) * 100, color=C['idio'], label='その県だけの動き')
for r in ORDER:
    ix = np.array(D.index[D.region == r])
    ax.text(ix.mean(), 102, r, ha='center', fontsize=9)
    if ix.min() > 0: ax.axvline(ix.min() - .5, color='white', lw=2)
ax.set_xticks(x); ax.set_xticklabels([re.sub('[都府県]$', '', p) for p in D.pref], rotation=90, fontsize=8)
ax.set_ylim(0, 108); ax.set_ylabel('月々の変化の分散に占める割合（%）')
ax.set_title(f"県ごとの分け方：全国の動きが中央値{S['main']['nat_med']*100:.0f}%、地方の動きは{S['main']['reg_med']*100:.0f}%、県だけの動きが{S['main']['idio_med']*100:.0f}%\n（有効求人倍率の月々の変化、1990年2月〜2026年9月、階層型の動的因子モデル）", fontsize=11)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=9)
fig.tight_layout(); fig.savefig(FG/'fig2_decomposition.png', dpi=150); plt.close()

# 図3：全国の動きを除いた残りの相関と距離
dd = pd.read_csv(RS/'corr_distance_pairs.csv')
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.scatter(dd.km, dd['corr'], s=6, alpha=.25, color=C['dark'])
bins = [0, 100, 200, 300, 500, 800, 3000]; dd['bin'] = pd.cut(dd.km, bins)
m = dd.groupby('bin', observed=True).agg(km=('km', 'median'), c=('corr', 'mean'))
ax.plot(m.km, m.c, color=C['red'], marker='o', lw=2.5, label='距離の区間ごとの平均')
ax.axhline(0, color='gray', lw=.8)
ax.set_xlabel('県庁所在地どうしの距離（km）'); ax.set_ylabel('全国の動きを除いた残りの相関')
ax.set_title('全国の動きを除くと、近い県どうしほど一緒に動く\n（1,081組の県の組み合わせ）', fontsize=11)
ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FG/'fig3_corr_distance.png', dpi=150); plt.close()

# 図4：同調の強さの推移（10年の窓）
ro = pd.read_csv(RS/'rolling_pc1.csv')
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(ro.mid, ro.pc1_share * 100, color=C['nat'], lw=2.5, marker='o', ms=3, label='1番目の動き（全国）')
ax.plot(ro.mid, ro.pc2_share * 100, color=C['reg'], lw=2, marker='o', ms=3, label='2番目の動き')
ax.set_xticks(ro.mid[::4]); ax.set_xticklabels(ro.window[::4], rotation=30, fontsize=8)
ax.set_ylabel('説明できる割合（%）'); ax.set_ylim(0, 70); ax.grid(alpha=.3); ax.legend()
ax.set_title('47県がそろって動く度合いは、1980年代の2割台から2000年代に6割へ\n（10年ずつの窓で、主成分の説明割合）', fontsize=11)
fig.tight_layout(); fig.savefig(FG/'fig4_rolling.png', dpi=150); plt.close()

# 図5：全国の因子と鉱工業生産
nf = pd.read_csv(RS/'national_factor_iip.csv', index_col=0)
nf.index = pd.PeriodIndex(nf.index, freq='M').to_timestamp(); nf = nf.loc['1990-04':]
z = lambda s: (s - s.mean()) / s.std()
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(nf.index, z(nf.national_factor.rolling(3).mean()), color=C['nat'], lw=1.8, label='47県に共通する動き（3か月平均）')
ax.plot(nf.index, z(nf.iip_dlog.rolling(3).mean()), color=C['red'], lw=1.2, alpha=.8, label='鉱工業生産の前月比（3か月平均）')
ax.set_ylim(-6, 4); ax.axhline(0, color='gray', lw=.8); ax.grid(alpha=.3); ax.legend(loc='lower left', fontsize=9)
ax.set_ylabel('標準化した値')
ax.set_title(f"県に共通する動きは、全国の鉱工業生産と一緒に動く（3か月平均どうしの相関 {S['factor_vs_iip_3m']:.2f}）", fontsize=11)
fig.tight_layout(); fig.savefig(FG/'fig5_national_iip.png', dpi=150); plt.close()

# 図6：頑健性
rb = S['robust']; names = list(rb)
fig, ax = plt.subplots(figsize=(9, 5))
y = np.arange(len(names))[::-1]
ax.barh(y + .2, [rb[n]['nat_med'] * 100 for n in names], height=.4, color=C['nat'], label='全国の動き（中央値）')
ax.barh(y - .2, [rb[n]['reg_med'] * 100 for n in names], height=.4, color=C['reg'], label='地方の動き（中央値）')
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9); ax.set_xlabel('分散に占める割合（%）'); ax.grid(alpha=.3, axis='x')
ax.set_title('条件を変えても「全国が大きく、地方は小さい」は同じ', fontsize=11); ax.legend(fontsize=9, loc='lower right')
fig.tight_layout(); fig.savefig(FG/'fig6_robustness.png', dpi=150); plt.close()
print('ok')
