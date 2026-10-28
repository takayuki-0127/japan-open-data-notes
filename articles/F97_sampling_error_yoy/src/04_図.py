"""図を作る。"""
import json
import numpy as np, pandas as pd
from scipy.stats import norm
import matplotlib.pyplot as plt
from common import RES, FIG, DATA, CATS
S = json.load(open(RES/'summary_main.json'))
Z = norm.ppf(0.975)
# 図1 月の実質前年同月比と標本誤差の幅
m = pd.read_csv(RES/'monthly_total_yoy.csv', parse_dates=['ym']).set_index('ym')
m = m[m.index >= '2015-01-01']; thr = S['monthly_total']['thr95']
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.axhspan(-thr, thr, color='#dadce0', alpha=.6, label=f'標本誤差の範囲（±{thr:.1f}ポイント、95%）')
c = np.where(m.real.abs() > thr, '#d93025', '#5f6368')
ax.bar(m.index, m.real, width=25, color=c)
ax.plot(m.index, m.ma13, color='#1a73e8', lw=1.6, label='13か月の移動平均')
ax.axhline(0, color='k', lw=.6)
ax.set_ylim(-16, 16); ax.set_ylabel('実質・前年同月比（%）')
ax.set_title('家計調査の消費支出（二人以上の世帯）：灰色の帯の中は「標本の入れ替わりでも起こる幅」')
ax.legend(loc='lower left', fontsize=9); ax.text(m.index[3], 12, '赤：帯の外（95%で増減と言える月）', color='#d93025', fontsize=9)
fig.tight_layout(); fig.savefig(FIG/'fig1_monthly_yoy_band.png', dpi=150); plt.close()
# 図2 見つけられる最小の変化
d = pd.read_csv(RES/'mdc_table.csv')
sel = []
for c in CATS: sel.append((c+'（年）', d[(d.series==c)&(d.kind=='二人以上・年')].thr95.iloc[0], '#1a73e8'))
sel.append(('消費支出（月）', d[(d.series=='消費支出')&(d.kind=='二人以上・月')].thr95.iloc[0], '#e8710a'))
sel.append(('消費支出・単身（年）', d[d.kind=='単身・年'].thr95.iloc[0], '#188038'))
reg = d[d.kind.str.startswith('地方・年')&~d.kind.str.contains('全国')]
sel.append((f'消費支出・地方（年、{reg.thr95.min():.1f}〜{reg.thr95.max():.1f}）', reg.thr95.mean(), '#9334e6'))
sel = sorted(sel, key=lambda x: x[1])
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh([s[0] for s in sel], [s[1] for s in sel], color=[s[2] for s in sel])
for i, s in enumerate(sel): ax.text(s[1]+.1, i, f'±{s[1]:.1f}', va='center', fontsize=9)
ax.set_xlim(0, 9.6); ax.axvline(1, color='#d93025', ls='--', lw=1); ax.text(1.05, len(sel)-0.6, '「+1%」', color='#d93025', fontsize=9)
ax.set_xlabel('前年比がこれより大きければ、95%で「増えた（減った）」と言える（ポイント）')
ax.set_title('家計調査で「前年比」を読むときの最小の目安（標準誤差率から計算）')
fig.tight_layout(); fig.savefig(FIG/'fig2_min_detectable_change.png', dpi=150); plt.close()
# 図3 年の前年比：費目ごとの「言える年」の割合と、ふだんの変化の大きさ
b = pd.read_csv(RES/'annual_10cat_summary.csv').set_index('item').loc[CATS]
fig, ax = plt.subplots(figsize=(8.5, 6))
sc = ax.scatter(b.thr, b.med_abs, s=60+400*b.share_sig, c=b.share_sig, cmap='viridis', vmin=0, vmax=1, edgecolor='k')
lim = 9; ax.plot([0, lim], [0, lim], color='#9aa0a6', ls='--', lw=1); ax.text(3.6, 4.2, '点線：ふだんの変化＝誤差の幅', color='#5f6368', fontsize=9)
for n, r in b.iterrows(): ax.annotate(f'{n} {r.share_sig*100:.0f}%', (r.thr, r.med_abs), xytext=(6, 4), textcoords='offset points', fontsize=9)
ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(0.4, 12); ax.set_ylim(0.8, 5)
from matplotlib.ticker import FixedLocator, FormatStrFormatter, NullFormatter
ax.xaxis.set_major_locator(FixedLocator([0.5,1,2,4,8])); ax.yaxis.set_major_locator(FixedLocator([1,2,3,4]))
for a in (ax.xaxis, ax.yaxis): a.set_major_formatter(FormatStrFormatter('%g')); a.set_minor_formatter(NullFormatter())
ax.set_xlabel('95%で「増えた」と言える最小の前年比（ポイント、対数目盛）'); ax.set_ylabel('前年比の大きさの中央値（ポイント、対数目盛）')
ax.set_title('年の前年比（2001〜2025年、2018・2019年を除く23年）\n％は「標本誤差の外」だった年の割合')
plt.colorbar(sc, ax=ax, label='誤差の外だった年の割合')
fig.tight_layout(); fig.savefig(FIG/'fig3_annual_by_category.png', dpi=150); plt.close()
# 図4 完全失業率の前月差
u = pd.read_csv(RES/'lfs_urate_changes.csv')
dist = pd.Series(S['lfs_d1_dist']); x = [float(k) for k in dist.index]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.bar(x, dist.values, width=0.07, color='#5f6368')
for v, n in zip(x, dist.values): ax.text(v, n+2, str(n), ha='center', fontsize=9)
for rho, col in [('0', '#d93025'), ('0.5', '#e8710a')]:
    t = S['lfs'][rho]['thr_median']
    for s in [-1, 1]: ax.axvline(s*t, color=col, ls='--', lw=1.2)
    ax.text(t+0.01, 140 if rho=='0' else 120, f'±{t:.2f}（標本の相関{rho}）', color=col, fontsize=9)
ax.set_xlabel('完全失業率（季節調整値）の前月差（ポイント）'); ax.set_ylabel('月の数')
ax.set_title('完全失業率の「前月から0.1ポイント上昇」は、標本誤差の範囲の中（1994年2月〜2026年8月）')
fig.tight_layout(); fig.savefig(FIG/'fig4_unemployment_monthly_change.png', dpi=150); plt.close()
# 図5 「本当に増えた」確からしさ
se = S['se_annual_two']
cases = [('年・消費支出（標準誤差率0.4%）', se['消費支出'], '#1a73e8'), ('月・消費支出（1.4%）', S['se_month_total_mean'], '#e8710a'),
         ('年・単身世帯の消費支出（1.4%）', 1.38, '#188038'), ('年・教育（3.1%）', se['教育'], '#9334e6')]
v = np.linspace(0, 6, 200)
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for lab, s, col in cases: ax.plot(v, norm.cdf(v/(s*np.sqrt(2))), color=col, lw=2, label=lab)
ax.axvline(1, color='#9aa0a6', ls=':'); ax.axhline(0.975, color='#9aa0a6', ls=':')
ax.set_xlabel('公表された前年比（%）'); ax.set_ylabel('本当の変化が0より大きい確からしさ（目安）'); ax.set_ylim(0.5, 1.0)
ax.set_title('同じ「+1%」でも、どの数字かで重みがちがう')
ax.legend(fontsize=9, loc='lower right'); fig.tight_layout(); fig.savefig(FIG/'fig5_prob_increase.png', dpi=150); plt.close()
print('ok')
