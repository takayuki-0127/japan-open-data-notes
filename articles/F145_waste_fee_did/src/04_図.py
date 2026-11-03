# 04 図
import os, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
    if os.path.exists(f): font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results'); FIG = os.path.join(ROOT, 'figures'); os.makedirs(FIG, exist_ok=True)
R = json.load(open(os.path.join(RES, 'results.json'), encoding='utf-8'))
P = pd.read_csv(os.path.join(ROOT, 'data/panel.csv'), dtype={'code': str})
G = pd.read_csv(os.path.join(RES, 'cohorts.csv'), dtype={'code': str}).set_index('code')['g']
C1, C2, C3, CG = '#2b6cb0', '#dd6b20', '#38a169', '#718096'
pct = lambda x: (np.exp(x) - 1) * 100

# 図1 有料化の割合の推移と、新たに有料化した自治体の数
st = pd.read_csv(os.path.join(RES, 'fee_share_by_year.csv')).set_index('year')
gi = G[G.str.fullmatch(r'\d{4}')].astype(int).value_counts().sort_index()
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].stackplot(st.index, st.paid * 100, st.partial * 100, st.free * 100, labels=['有料', '一部有料', '無料'], colors=[C1, '#90cdf4', '#e2e8f0'])
ax[0].set_ylim(0, 100); ax[0].set_ylabel('自治体の割合（%）'); ax[0].set_title('家庭の可燃ごみの手数料（市区町村）')
ax[0].legend(loc='lower right', fontsize=9); ax[0].set_xlabel('年度')
ax[1].bar(gi.index, gi.values, color=C1)
for x, v in gi.items(): ax[1].text(x, v + 0.5, str(v), ha='center', fontsize=9)
ax[1].set_title('分析に使った「新たに有料化した自治体」の数'); ax[1].set_xlabel('有料化した年度'); ax[1].set_ylabel('自治体数')
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig1_fee_adoption.png'), dpi=150); plt.close(fig)

# 図2 生のデータ：有料化の年を0として、有料化した自治体と最後まで無料の自治体の平均
W = P.pivot(index='code', columns='year', values='seikatsu_gpd')
W = W.loc[W.notna().all(axis=1)]
never = G[G == 'never'].index.intersection(W.index)
rows = []
for c, g in G.items():
    if not str(g).isdigit() or c not in W.index: continue
    g = int(g)
    for t in W.columns:
        rows.append((t - g, W.loc[c, t] / W.loc[c, g - 1] * 100, W.loc[never, t].mean() / W.loc[never, g - 1].mean() * 100))
D = pd.DataFrame(rows, columns=['e', 'tr', 'nv']).groupby('e').agg(tr=('tr', 'mean'), nv=('nv', 'mean'), n=('tr', 'size'))
D = D[(D.index >= -5) & (D.index <= 5)]
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(D.index, D.tr, 'o-', color=C1, label='有料化した自治体')
ax.plot(D.index, D.nv, 's--', color=CG, label='最後まで無料の自治体（同じ年で比べたもの）')
ax.axvline(-0.5, color='k', lw=0.8, ls=':'); ax.axhline(100, color='k', lw=0.5)
ax.set_xlabel('有料化した年度からの年数（0＝有料化した年度）'); ax.set_ylabel('有料化の前年＝100')
ax.set_title('1人1日あたりの生活系ごみ（生のデータの平均）'); ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig2_raw_event.png'), dpi=150); plt.close(fig)

# 図3 イベントスタディ（段階的な差の差）
ev = pd.read_csv(os.path.join(RES, 'event_main.csv')).set_index('e')
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.fill_between(ev.index, pct(ev.lo), pct(ev.hi), color=C1, alpha=0.2, label='95%区間（自治体のブートストラップ）')
ax.plot(ev.index, pct(ev.att), 'o-', color=C1, label='推定値')
ax.axhline(0, color='k', lw=0.6); ax.axvline(-0.5, color='k', lw=0.8, ls=':')
tw = R['twfe']['beta']
ax.axhline(pct(tw), color=C2, ls='--', lw=1, label=f'比較：普通の二元固定効果 {pct(tw):.1f}%')
ax.set_xlabel('有料化した年度からの年数（基準＝前年度）'); ax.set_ylabel('最後まで無料の自治体との差（%）')
ax.set_title('有料化の前後の1人1日あたり生活系ごみ（差の差）'); ax.legend(fontsize=9, loc='lower left')
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig3_event_study.png'), dpi=150); plt.close(fig)

# 図4 有料化の年度ごとの効果
cg = pd.read_csv(os.path.join(RES, 'att_by_cohort.csv'))
fig, ax = plt.subplots(figsize=(7.5, 4.0))
ax.bar(cg.g.astype(int), pct(cg.att), color=C1)
for x, y, n in zip(cg.g.astype(int), pct(cg.att), cg.n.astype(int)):
    ax.text(x, y - 1.2 if y < 0 else y + 0.4, f'n={n}', ha='center', fontsize=8)
ax.axhline(pct(R['main']['overall']), color=C2, ls='--', lw=1, label=f"全体 {pct(R['main']['overall']):.1f}%")
ax.axhline(0, color='k', lw=0.6)
ax.margins(y=0.15); ax.set_xlabel('有料化した年度'); ax.set_ylabel('導入後の平均の差（%）'); ax.set_title('有料化した年度ごとの、導入後の平均の差'); ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig4_by_cohort.png'), dpi=150); plt.close(fig)

# 図5 頑健性
items = [R['main']] + [r for r in R['robust'] if 'リサイクル率' not in r['label']]
lab = ['主な推定'] + [r['label'] for r in items[1:]]
y = np.arange(len(items))[::-1]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for yi, r in zip(y, items):
    lo, hi = r['ci']; ax.plot([pct(lo), pct(hi)], [yi, yi], color=C1, lw=2)
    ax.plot(pct(r['overall']), yi, 'o', color=C1 if r is not R['main'] else C2, ms=7)
tw = R['twfe']; ax.plot([pct(tw['ci'][0]), pct(tw['ci'][1])], [-1, -1], color=CG, lw=2); ax.plot(pct(tw['beta']), -1, 'D', color=CG)
ax.set_yticks(list(y) + [-1]); ax.set_yticklabels(lab + ['比較：普通の二元固定効果'], fontsize=8.5)
ax.axvline(0, color='k', lw=0.6); ax.set_xlabel('導入後の平均の差（%）と95%区間')
ax.set_title('条件を変えたときの推定値')
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig5_robustness.png'), dpi=150); plt.close(fig)
print('figs ok')
