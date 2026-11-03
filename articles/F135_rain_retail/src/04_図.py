# 図を作る
import pandas as pd, numpy as np, pathlib, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
A = pathlib.Path(__file__).resolve().parents[1]; R = A/'results'; F = A/'figures'
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: fm.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
BLUE, ORANGE, GRAY = '#2a6fb0', '#e07b39', '#8a8a8a'
ORDER = ['ホームセンター', 'ドラッグストア', '百貨店', '家電大型専門店', 'スーパー', 'コンビニ']

def forest(ax, df, ycol, color, offset=0.0, label=None, marker='o'):
    ys = np.arange(len(df)) + offset
    ax.errorbar(df.係数, ys, xerr=[df.係数-df.下限, df.上限-df.係数], fmt=marker, color=color, ecolor=color, capsize=3, label=label, ms=6)
    return ys

# 図1：残差どうしの散布図（ホームセンターとスーパー）
P = pd.read_csv(A/'data/national_prepped.csv')
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharex=True)
for ax, gy, c in zip(axes, ['ホームセンター', 'スーパー'], [ORANGE, BLUE]):
    x = P[P.業態 == gy]
    ax.scatter(x.res_rain, x.res_g, s=18, color=c, alpha=.7)
    b = np.polyfit(x.res_rain, x.res_g, 1); xx = np.linspace(x.res_rain.min(), x.res_rain.max(), 10)
    ax.plot(xx, np.polyval(b, xx), color='k', lw=1.2)
    ax.axhline(0, color=GRAY, lw=.6); ax.axvline(0, color=GRAY, lw=.6)
    ax.set_title(f'{gy}（傾き {b[0]:+.2f}%／日）'); ax.set_xlabel('雨の日数の前年差（日、他の要因を除いた残り）')
axes[0].set_ylabel('販売額の前年比（%、他の要因を除いた残り）')
fig.suptitle('雨の日が前年より多い月ほど、ホームセンターの売上は前年を下回った', x=.02, ha='left', fontsize=13)
fig.text(.02, -.02, '9地点（各経済産業局の代表都市）の1mm以上の降水日数の平均。気温・土日祝の日数・月の日数・消費税の前後を除いた残差。スーパーは2014年1月〜、ホームセンターは2015年1月〜2026年8月（2020年2月〜2023年5月を除く）', fontsize=8, color=GRAY)
fig.tight_layout(); fig.savefig(F/'fig1_scatter.png', dpi=150, bbox_inches='tight'); plt.close()

# 図2：業態ごとの係数（全国の時系列 と 地域パネル）
M = pd.read_csv(R/'main_by_format.csv').set_index('系列').loc[ORDER].reset_index()
PN = pd.read_csv(R/'panel_region.csv'); PN = PN[PN.条件 == '基本'].set_index('系列').reindex(ORDER).reset_index()
fig, ax = plt.subplots(figsize=(8, 4.6))
forest(ax, M, '系列', BLUE, -.15, '全国の月次（前年同月どうし）')
ok = PN.dropna(subset=['係数'])
ys = [ORDER.index(s)+.15 for s in ok.系列]
ax.errorbar(ok.係数, ys, xerr=[ok.係数-ok.下限, ok.上限-ok.係数], fmt='s', color=ORANGE, capsize=3, label='地域パネル（月の固定効果）', ms=6)
ax.set_yticks(range(len(ORDER))); ax.set_yticklabels([o if o in set(ok.系列) else o+'（地域なし）' for o in ORDER]); ax.invert_yaxis()
ax.axvline(0, color='k', lw=.8); ax.set_xlabel('雨の日が1日増えたときの販売額の変化（%）')
ax.set_title('雨の日1日あたりの売上の変化：ホームセンターが最も大きかった', loc='left'); ax.legend(loc='lower left', fontsize=9, frameon=False)
fig.text(.01, -.03, '線は95%区間。百貨店・スーパーは既存店ベース。百貨店・スーパーは地域別の月次がないため全国のみ', fontsize=8, color=GRAY)
fig.tight_layout(); fig.savefig(F/'fig2_by_format.png', dpi=150, bbox_inches='tight'); plt.close()

# 図3：品目
I = pd.read_csv(R/'items.csv')
fig, ax = plt.subplots(figsize=(8, 4.6))
cols = [ORANGE if '衣料' in s else (GRAY if '非食品' in s else (BLUE if '食' in s else GRAY)) for s in I.系列]
for i, (_, r) in enumerate(I.iterrows()):
    ax.errorbar(r.係数, i, xerr=[[r.係数-r.下限], [r.上限-r.係数]], fmt='o', color=cols[i], capsize=3)
ax.set_yticks(range(len(I))); ax.set_yticklabels(I.系列); ax.invert_yaxis(); ax.axvline(0, color='k', lw=.8)
ax.set_xlabel('雨の日が1日増えたときの販売額の変化（%）'); ax.set_title('スーパーでは、衣料品は雨で減ったが、食品はほとんど動かなかった', loc='left')
fig.text(.01, -.03, '橙＝衣料品、青＝食品、灰＝その他。線は95%区間。全国の月次', fontsize=8, color=GRAY)
fig.tight_layout(); fig.savefig(F/'fig3_items.png', dpi=150, bbox_inches='tight'); plt.close()

# 図4：土日祝の雨 と 平日の雨
O = pd.read_csv(R/'offday_vs_weekday.csv')
fig, ax = plt.subplots(figsize=(8, 4.6))
for lab, c, off, mk in [('土日祝の雨', ORANGE, -.15, 'o'), ('平日の雨', BLUE, .15, 's')]:
    x = O[O.雨の曜日 == lab].set_index('系列').loc[ORDER].reset_index(); forest(ax, x, '系列', c, off, lab, mk)
ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(ORDER); ax.invert_yaxis(); ax.axvline(0, color='k', lw=.8)
ax.set_xlabel('その曜日の雨の日が1日増えたときの販売額の変化（%）'); ax.legend(frameon=False, fontsize=9, loc='lower left')
ax.set_title('百貨店は、土日祝の雨のときだけ売上が減っていた', loc='left')
fig.text(.01, -.03, '線は95%区間。全国の月次。家電大型専門店は区間が広いため横軸の外にはみ出す部分あり', fontsize=8, color=GRAY)
ax.set_xlim(-1.0, 0.6)
fig.tight_layout(); fig.savefig(F/'fig4_offday.png', dpi=150, bbox_inches='tight'); plt.close()

# 図5：頑健性
RB = pd.read_csv(R/'robustness_national.csv'); RB = RB[RB.条件 != '月の降水量（対数）']
conds = list(dict.fromkeys(RB.条件)); cmap = plt.get_cmap('tab10')
fig, ax = plt.subplots(figsize=(8.5, 5))
for j, c in enumerate(conds):
    x = RB[RB.条件 == c].set_index('系列').loc[ORDER].reset_index()
    ys = np.arange(len(ORDER)) + (j - (len(conds)-1)/2)*0.11
    ax.errorbar(x.係数, ys, xerr=[x.係数-x.下限, x.上限-x.係数], fmt='o', ms=4, color=cmap(j), capsize=0, lw=1, label=c)
ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(ORDER); ax.invert_yaxis(); ax.axvline(0, color='k', lw=.8)
ax.set_xlabel('雨の日（または10mm以上の日）が1日増えたときの販売額の変化（%）'); ax.set_xlim(-1.0, 0.5)
ax.legend(frameon=False, fontsize=8, loc='lower left'); ax.set_title('条件を変えても、ホームセンターとドラッグストアの減少は残った', loc='left')
fig.text(.01, -.03, '全国の月次。線は95%区間（一部は横軸の外まで伸びる）', fontsize=8, color=GRAY)
fig.tight_layout(); fig.savefig(F/'fig5_robustness.png', dpi=150, bbox_inches='tight'); plt.close()
print('ok')
