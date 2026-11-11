"""F265 04 図：figures/ に PNG を6枚。"""
import os, io, contextlib, importlib.util, numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
B = os.path.join(os.path.dirname(__file__), '..'); R = os.path.join(B, 'results'); F = os.path.join(B, 'figures')
os.makedirs(F, exist_ok=True)
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f or 'NotoSansCJKjp-Regular' in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e', 'axes.grid': True,
                     'grid.color': '#e6e5e0', 'grid.linewidth': .8, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.dpi': 160})
INK, INK2 = '#1f1e1c', '#52514e'; BLUE, GREEN, ORANGE, PINK, GOLD, GRAY = '#2a78d6', '#1baf7a', '#eb6834', '#e87ba4', '#eda100', '#9a9893'
spec = importlib.util.spec_from_file_location('a', os.path.join(os.path.dirname(__file__), 'zz_f265_03_分析.py'))
a = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(a)
S = a.S; NAMES = a.NAMES; TG = a.TG
V20 = pd.read_csv(os.path.join(R, 'A_vintage2020.csv')); NOW = pd.read_csv(os.path.join(R, 'B_now.csv'))
RQ = pd.read_csv(os.path.join(R, 'E_reask_required_pace.csv')); ROB = pd.read_csv(os.path.join(R, 'D_robustness.csv'))
ERR = pd.read_csv(os.path.join(R, 'C_backtest_errors.csv'))
MC = {'M1': ORANGE, 'M2': BLUE, 'M3': GREEN}
ML = {'M1': 'M1 直近5点の直線', 'M2': 'M2 直近5点のロジット', 'M3': 'M3 直近10点の直線'}
UNIT = {'male_leave': '年度（調査年度）', 'paid_leave': '年（取得した年）', 'female_emp': '年'}
def save(fig, n): fig.savefig(os.path.join(F, n), bbox_inches='tight'); plt.close(fig)

# 図1 3つの指標と目標
fig, axs = plt.subplots(1, 3, figsize=(13, 4.3))
for ax, ind in zip(axs, ['male_leave', 'paid_leave', 'female_emp']):
    d = S[S.indicator == ind].sort_values('year'); d = d[d.year >= 1996]
    ax.plot(d.year, d.value, 'o-', color=INK, ms=3.5, lw=1.6)
    for i, (_, t) in enumerate(TG[TG.indicator == ind].iterrows()):
        c = {'少子化社会対策大綱（2015）': GRAY, '少子化社会対策大綱（2020）': ORANGE}.get(t.plan, BLUE)
        ax.plot([t.target_year], [t.target_value], marker='*', ms=13, color=c, ls='none')
        ax.annotate(f"{t.target_value:g}%（{t.target_year}）", (t.target_year, t.target_value), textcoords='offset points', xytext=(-8, 8) if ind != 'paid_leave' else (-6, -16 - 13 * i), fontsize=8.5, color=c, ha='right')
    ax.set_title(NAMES[ind], fontsize=11.5, loc='left'); ax.set_xlabel(UNIT[ind], fontsize=9.5)
    ax.set_xlim(1995, 2032)
axs[0].set_ylabel('%')
axs[0].plot([], [], '*', color=GRAY, ms=10, label='2015年大綱の目標'); axs[0].plot([], [], '*', color=ORANGE, ms=10, label='2020年大綱の目標'); axs[0].plot([], [], '*', color=BLUE, ms=10, label='その後の計画の目標')
axs[0].legend(loc='upper left', fontsize=8.5, frameon=False)
fig.suptitle('図1　3つの指標の推移と、目標（★）', x=0.01, ha='left', fontsize=12.5)
save(fig, 'f265_1_series_targets.png')

# 図2 2020年5月の時点で延ばした見通しと、その後の実績
fig, axs = plt.subplots(1, 3, figsize=(13, 4.3))
for ax, ind in zip(axs, ['male_leave', 'paid_leave', 'female_emp']):
    yrs, vals = a.series(ind, until=a.VINTAGE_2020)
    allv = S[S.indicator == ind].sort_values('year'); allv = allv[allv.year >= 2008]
    t = TG[(TG.indicator == ind) & TG.plan.str.contains('2020')].iloc[0]
    ax.plot(allv.year, allv.value, 'o-', color=INK, ms=3.5, lw=1.6, label='実績')
    for m in ['M1', 'M2', 'M3']:
        xs = np.arange(yrs[-1], t.target_year + 1)
        ys = [a.fit_predict(yrs, vals, x, m) for x in xs]
        ax.plot(xs, ys, '--', color=MC[m], lw=1.4, label=ML[m])
        r = V20[(V20.indicator == ind) & (V20.method == m)].iloc[0]
        ax.plot([t.target_year + {'M1': -.15, 'M2': 0, 'M3': .15}[m]] * 2, [r.lo80, r.hi80], color=MC[m], lw=4, alpha=.45)
    ax.axhline(t.target_value, color=GRAY, lw=1, ls=':'); ax.text(2008.2, t.target_value + .6, f'2025年の目標 {t.target_value:g}%', fontsize=8.5, color=INK2)
    ax.axvline(yrs[-1] + .5, color=GRAY, lw=.8); ax.text(yrs[-1] + .6, ax.get_ylim()[0] + .3 if ind != 'male_leave' else 45, '2020年5月に\n分かっていた値まで', fontsize=8, color=INK2)
    ax.set_title(NAMES[ind], fontsize=11.5, loc='left'); ax.set_xlabel(UNIT[ind], fontsize=9.5)
axs[0].set_ylabel('%'); axs[0].legend(loc='upper left', fontsize=8, frameon=False)
fig.suptitle('図2　大綱を決めた2020年5月の時点のペースで延ばすと（破線は当てはめた線、縦の太線は過去の外れでつくった80%の幅）', x=0.01, ha='left', fontsize=12.5)
save(fig, 'f265_2_vintage2020.png')

# 図3 いまのペースで先の目標へ
fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
for ax, (ind, ty, tv) in zip(axs, [('male_leave', 2030, 85), ('paid_leave', 2028, 70)]):
    yrs, vals = a.series(ind, until=a.NOW)
    allv = S[S.indicator == ind].sort_values('year'); allv = allv[allv.year >= 2010]
    ax.plot(allv.year, allv.value, 'o-', color=INK, ms=3.5, lw=1.6, label='実績')
    for m in ['M1', 'M2', 'M3']:
        xs = np.arange(yrs[-1], ty + 1); ys = [a.fit_predict(yrs, vals, x, m) for x in xs]
        ax.plot(xs, ys, '--', color=MC[m], lw=1.4, label=ML[m])
        r = NOW[(NOW.indicator == ind) & (NOW.method == m) & (NOW.target_year == ty)].iloc[0]
        ax.plot([ty + {'M1': -.15, 'M2': 0, 'M3': .15}[m]] * 2, [r.lo80, r.hi80], color=MC[m], lw=4, alpha=.45)
        ax.text(ty + .35, r.pred, f"{r.pred:.0f}%（届く確率 {r.p_reach*100:.0f}%）", fontsize=8.3, color=MC[m], va='center')
    if ind == 'male_leave':
        msk = yrs <= 2022; xs = np.arange(2022, ty + 1); ys = [a.fit_predict(yrs[msk], vals[msk], x, 'M2') for x in xs]
        ax.plot(xs, ys, ':', color=PINK, lw=1.6, label='参考：2022年度までの5点でロジット')
    ax.axhline(tv, color=GRAY, lw=1, ls=':'); ax.text(2010.2, tv + 1, f'目標 {tv}%（{ty}）', fontsize=8.8, color=INK2)
    ax.set_xlim(2009.5, ty + 4.2); ax.set_title(NAMES[ind], fontsize=11.5, loc='left'); ax.set_xlabel(UNIT[ind], fontsize=9.5)
axs[0].set_ylabel('%'); axs[0].legend(loc='lower right', fontsize=8, frameon=False)
fig.suptitle('図3　いま（2026年11月）までの値で、先の目標へ延ばすと（破線は当てはめた線、縦の太線は80%の幅）', x=0.01, ha='left', fontsize=12.5)
save(fig, 'f265_3_now.png')

# 図4 過去の外れ（M1）：何年先かごとの分布
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), sharey=False)
for ax, ind in zip(axs, ['male_leave', 'paid_leave', 'female_emp']):
    e = ERR[(ERR.indicator == ind) & (ERR.method == 'M1')]
    hs = list(range(1, 9)); data = [e[e.h == h].err.values for h in hs]
    bp = ax.boxplot([d if len(d) else [np.nan] for d in data], positions=hs, widths=.55, whis=(10, 90), showfliers=False, patch_artist=True)
    for b in bp['boxes']: b.set(facecolor='#fbe1d6', edgecolor=ORANGE)
    for k in ['whiskers', 'caps', 'medians']:
        for l in bp[k]: l.set(color=ORANGE)
    ax.axhline(0, color=GRAY, lw=1)
    for h, d in zip(hs, data): ax.text(h, ax.get_ylim()[1] if False else np.nan, '')
    ax.set_title(NAMES[ind] + f'（外れ {len(e)}個）', fontsize=11, loc='left'); ax.set_xlabel('何年先を予測したか', fontsize=9.5)
axs[0].set_ylabel('実績 − 予測（ポイント）')
fig.suptitle('図4　「直近5点の直線」で過去に予測していたら、どれだけ外れたか（箱は25〜75%、ひげは10〜90%）', x=0.01, ha='left', fontsize=12.5)
save(fig, 'f265_4_backtest.png')

# 図5 問いの立て直し：目標が求めた伸び ÷ それまでの伸び
r = RQ.copy(); r['label'] = r.name.str.replace('25〜44歳の女性の就業率', '女性（25〜44歳）就業率').str.replace('の育児休業取得率', '育休').str.replace('年次有給休暇取得率', '有給取得率') + '\n' + r.target.map(lambda v: f'{v:g}%') + '（' + r.target_year.astype(str) + '）'
r = r.sort_values('ratio_needed_to_past')
col = r.reached.map({True: GREEN, False: ORANGE}).fillna(GRAY)
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.barh(range(len(r)), r.ratio_needed_to_past, color=col)
for i, (_, x) in enumerate(r.iterrows()):
    st = {True: '届いた', False: '届かず'}.get(x.reached, 'まだ分からない')
    ax.text(x.ratio_needed_to_past + .2, i, f"{x.ratio_needed_to_past:.1f}倍　{st}（{x.plan.replace('（', ' ').replace('）', '')}）", va='center', fontsize=8.6, color=INK2)
ax.set_yticks(range(len(r))); ax.set_yticklabels(r.label, fontsize=8.6)
ax.axvline(1, color=GRAY, lw=1, ls=':'); ax.text(1.1, len(r) - .45, '← 1倍＝それまでと同じペースで届く', fontsize=8.5, color=INK2)
ax.set_xlabel('目標までに必要な1年あたりの伸び ÷ 目標を決める前の5点の伸び（倍）'); ax.set_xlim(0, 22)
ax.set_title('図5　目標は「それまでのペースの何倍」を求めていたか（緑＝届いた、橙＝届かず、灰＝まだ分からない）', fontsize=11.5, loc='left')
save(fig, 'f265_5_required_pace.png')

# 図6 頑健性：窓の長さで先の目標の見通しがどう動くか
rr = ROB[ROB.check.str.startswith('窓') & ROB.tag.isin(['いま→2030', 'いま→2028', '2020時点→2025'])].copy()
rr['k'] = rr.check.str.extract(r'窓(\d+)点').astype(int); rr['tr'] = np.where(rr.check.str.contains('ロジット'), 'ロジット', '直線')
fig, axs = plt.subplots(1, 3, figsize=(13, 4.0))
panels = [('male_leave', 'いま→2030', 85, '男性育休 2030年（目標85%）'), ('paid_leave', 'いま→2028', 70, '有給取得率 2028年（目標70%）'), ('male_leave', '2020時点→2025', 30, '参考：男性育休 2020年5月時点→2025年（目標30%）')]
for ax, (ind, tag, tv, ttl) in zip(axs, panels):
    q = rr[(rr.indicator == ind) & (rr.tag == tag)]
    for tr, c in [('直線', ORANGE), ('ロジット', BLUE)]:
        z = q[q.tr == tr].sort_values('k'); ax.plot(z.k, z.pred, 'o-', color=c, label=tr)
    ax.axhline(tv, color=GRAY, ls=':', lw=1); ax.set_xticks([3, 5, 7, 10]); ax.set_xlabel('延ばすのに使った直近の点の数', fontsize=9.5)
    ax.set_title(ttl, fontsize=10.5, loc='left')
axs[0].set_ylabel('目標の年の予測（%）'); axs[0].legend(fontsize=8.5, frameon=False)
fig.suptitle('図6　何点で延ばすかで、見通しはどれだけ動くか', x=0.01, ha='left', fontsize=12.5)
save(fig, 'f265_6_window.png')
print(sorted(os.listdir(F)))
