"""04 図：係数・説明できる割合・月ごとの寄与・来年の補正表・期間外の検証"""
import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path
B = Path(__file__).resolve().parents[1]; F = B/'figures'; R = B/'results'; F.mkdir(exist_ok=True)
fp = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'; fm.fontManager.addfont(fp)
plt.rcParams['font.family'] = fm.FontProperties(fname=fp).get_name(); plt.rcParams['axes.spines.top']=False; plt.rcParams['axes.spines.right']=False
G = ['百貨店','スーパー','コンビニ','ドラッグストア','ホームセンター','家電大型専門店']
C1,C2,C3,GR = '#2b6cb0','#dd6b20','#38a169','#a0aec0'
co = pd.read_csv(R/'A_coef_main.csv')

# 図1 カレンダーの係数
fig, ax = plt.subplots(figsize=(10,5.2)); w=0.26; x=np.arange(len(G))
for i,(v,lab,c) in enumerate([('d_n_sat','平日1日 → 土曜',C1),('d_n_sun','平日1日 → 日曜（土曜の祝日を含む）',C2),('d_n_hol_wd','平日1日 → 平日の祝日',C3)]):
    t = co[co.変数==v].set_index('業態').loc[G]
    ax.bar(x+(i-1)*w, t.係数, w, color=c, label=lab, yerr=[t.係数-t.lo, t.hi-t.係数], capsize=3, error_kw=dict(lw=0.8,color='#444'))
ax.axhline(0,color='#333',lw=0.8); ax.set_xticks(x); ax.set_xticklabels(G); ax.set_ylabel('月の前年同月比の変化（%ポイント）')
ax.set_title('休みの日が1日多い月は、前年同月比が何ポイント動くか（95%区間つき）'); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(F/'fig1_calendar_coef.png', dpi=150); plt.close()

# 図2 ふだんの月で説明できる割合
d2 = pd.read_csv(R/'B2_r2_normal_months.csv').set_index('業態').loc[G]
fig, ax = plt.subplots(figsize=(10,4.8))
ax.barh(G, d2.R2_カレンダー*100, color=C1, label='カレンダー（曜日・祝日・連休・うるう年）')
ax.barh(G, d2.R2_天気*100, left=d2.R2_カレンダー*100, color=C2, label='天気（気温・雨の日数）')
ax.barh(G, 100-d2.R2_計*100, left=d2.R2_計*100, color='#e2e8f0', label='それ以外（販促・景気・店の数など）')
for i,g in enumerate(G): ax.text(d2.R2_計[g]*100+1, i, f'{d2.R2_計[g]*100:.0f}%', va='center', fontsize=9)
ax.invert_yaxis(); ax.set_xlim(0,100); ax.set_xlabel('前年同月比の月ごとの揺れのうち、説明できる割合（%、消費税の前後の月を除く）')
ax.set_title('前年同月比の揺れの1〜5割は、カレンダーと天気で説明できた'); ax.legend(frameon=False, fontsize=9, loc='upper right')
fig.tight_layout(); fig.savefig(F/'fig2_r2_normal_months.png', dpi=150); plt.close()

# 図3 スーパーの月ごとの寄与（2023-06〜2026-08）
c = pd.read_csv(R/'C_monthly_contrib.csv'); c = c[(c.業態=='スーパー')&(c.ym>='2023-06')]
fig, ax = plt.subplots(figsize=(11,5)); xx = np.arange(len(c))
ax.bar(xx-0.2, c.カレンダー寄与, 0.4, color=C1, label='カレンダーの寄与'); ax.bar(xx+0.2, c.天気寄与, 0.4, color=C2, label='天気の寄与')
ax.plot(xx, c.y, color='#222', marker='o', ms=3, lw=1.4, label='前年同月比（そのまま）')
ax.plot(xx, c.調整後, color=C3, marker='o', ms=3, lw=1.4, ls='--', label='カレンダーと天気を引いた前年同月比')
ax.axhline(0,color='#999',lw=0.6); ax.set_xticks(xx[::3]); ax.set_xticklabels(c.ym.values[::3], rotation=45, fontsize=8)
ax.set_ylabel('%'); ax.set_title('スーパー（既存店）の前年同月比と、カレンダー・天気の寄与'); ax.legend(frameon=False, fontsize=9, ncol=2)
fig.tight_layout(); fig.savefig(F/'fig3_super_monthly_contrib.png', dpi=150); plt.close()

# 図4 来年の補正表（カレンダーだけで前年同月比が何ポイント動くか）
ft = pd.read_csv(R/'G_calendar_effect_2026_2027.csv').pivot(index='ym', columns='業態', values='カレンダー寄与')[G]
fig, ax = plt.subplots(figsize=(10,6.2)); v = np.abs(ft.values).max()
im = ax.imshow(ft.values, cmap='RdBu', vmin=-v, vmax=v, aspect='auto')
ax.set_xticks(range(len(G))); ax.set_xticklabels(G); ax.set_yticks(range(len(ft))); ax.set_yticklabels(ft.index, fontsize=8)
for i in range(ft.shape[0]):
    for j in range(ft.shape[1]): ax.text(j,i,f'{ft.values[i,j]:+.1f}',ha='center',va='center',fontsize=7.5,color='#111')
ax.set_title('2026年9月〜2027年12月の各月、カレンダーだけで前年同月比が何ポイント動くか'); fig.colorbar(im, ax=ax, label='%ポイント')
fig.tight_layout(); fig.savefig(F/'fig4_calendar_effect_2026_2027.png', dpi=150); plt.close()

# 図5 期間外の検証
o = pd.read_csv(R/'D_out_of_sample.csv').set_index('業態').loc[G]
fig, ax = plt.subplots(figsize=(10,4.6)); x=np.arange(len(G))
ax.bar(x-0.2, o.sd_raw, 0.4, color=GR, label='そのままの前年同月比の揺れ（標準偏差）'); ax.bar(x+0.2, o.sd_adj, 0.4, color=C3, label='カレンダーと天気を引いたあとの揺れ')
for i,g in enumerate(G): ax.text(i, max(o.sd_raw[g],o.sd_adj[g])+0.15, f'{-o.減少率[g]*100:+.0f}%', ha='center', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(G); ax.set_ylabel('%ポイント'); ax.legend(frameon=False, fontsize=9)
ax.set_title('2013〜2019年の係数で、2023年6月〜2026年8月を補正すると揺れはどれだけ減るか')
fig.tight_layout(); fig.savefig(F/'fig5_out_of_sample.png', dpi=150); plt.close()
print('ok')
