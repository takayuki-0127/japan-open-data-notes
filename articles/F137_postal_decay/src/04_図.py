"""04 図"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import importlib.util
ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'figures'; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
spec = importlib.util.spec_from_file_location('an', ROOT / 'src/03_分析.py')
W = pd.read_csv(ROOT / 'data/postal_annual_wide.csv', index_col='fy')
H15 = pd.read_csv(ROOT / 'data/whitepaper_h15_total.csv')
R = json.load(open(ROOT / 'results/results.json', encoding='utf-8'))
CV = pd.read_csv(ROOT / 'results/rolling_cv.csv')
BASE = 2025
C = {'指数（一定の割合で減る）': '#3366aa', '対数2次（減り方が加速）': '#cc5533', 'ロジスティック（下限あり）': '#559955', '指数＋下限': '#9966aa'}
def fexp(t, a, b): return a + b * t
def fquad(t, a, b, c): return a + b * t + c * t**2
def flog(t, F, U, k, t0): return np.log(F + (U - F) / (1 + np.exp(k * (t - t0))))
def fefl(t, F, A, k): return np.log(F + A * np.exp(-k * t))
FN = dict(zip(C, [fexp, fquad, flog, fefl]))

# 図1 長期の推移（参考の白書値＋郵便物＋総計）
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(H15.fy, H15['総引受_億通'], 'o-', color='#bbbbbb', label='総引受郵便物数（白書・参考、億通単位）')
s = W['郵便物'].dropna() / 1e5; tot = W['総計'].dropna() / 1e5
for seg in [(2003, 2007), (2011, 2025)]:
    ss = s.loc[seg[0]:seg[1]]; tt = tot.loc[seg[0]:seg[1]]
    ax.plot(ss.index, ss.values, 'o-', color='#3366aa', label='郵便物（手紙・はがきなど）' if seg[0] == 2003 else None)
    ax.plot(tt.index, tt.values, 's--', color='#888888', ms=4, label='郵便物＋荷物（ゆうパック・ゆうメール）' if seg[0] == 2003 else None)
ax.axhline(s.loc[2003] / 2, color='#cc5533', lw=1, ls=':')
ax.text(1993, s.loc[2003] / 2 + 3, f'2003年度の郵便物の半分（{s.loc[2003]/2:.0f}億通）', color='#cc5533', fontsize=10)
ax.set_ylabel('億通（個）'); ax.set_ylim(0, 290); ax.set_xlabel('年度')
ax.set_title('郵便物は2025年度に2003年度の半分を下回った（2008〜10年度は資料なし）', fontsize=12)
ax.legend(fontsize=9, loc='lower left', frameon=False)
fig.tight_layout(); fig.savefig(FIG / 'fig1_long_trend.png', dpi=150); plt.close()

# 図2 前年比
fig, ax = plt.subplots(figsize=(9, 4.2))
yo = (s.pct_change() * 100).loc[2012:]
cols = ['#cc5533' if v < -5 else '#3366aa' for v in yo.values]
ax.bar(yo.index, yo.values, color=cols)
for x, v in yo.items(): ax.text(x, v - 0.45, f'{v:.1f}', ha='center', fontsize=8.5)
ax.axhline(0, color='k', lw=.8); ax.set_ylabel('前年度比（%）'); ax.set_xlabel('年度')
ax.set_title('郵便物の前年度比：2010年代は年1〜3%減、2023年度からは年6〜7%減が続く', fontsize=12)
ax.annotate('2024年10月\n郵便料金の値上げ', xy=(2024, yo.loc[2024]), xytext=(2020.6, -8.4), fontsize=9, arrowprops=dict(arrowstyle='->', lw=.8))
ax.set_ylim(-9.5, 1)
fig.tight_layout(); fig.savefig(FIG / 'fig2_yoy.png', dpi=150); plt.close()

# 図3 4モデルの当てはめと予測
s_main = s.loc[2011:2025]
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(s_main.index, s_main.values, 'ko', label='実績（FY2011〜2025）')
tt = np.arange(2011, 2051)
for r in R['main']:
    if not r.get('ok'): continue
    y = np.exp(FN[r['model']](tt - BASE, *r['params']))
    hy = r.get('half_year'); lab = r['model'] + (f'：半分は{hy:.0f}年度ごろ' if hy and np.isfinite(hy) and hy < 2100 else '：2100年度までに半分にならない')
    if r['model'] == '指数＋下限': lab += '（下限は0と推定され、指数と重なる）'
    ax.plot(tt, y, color=C[r['model']], lw=1.8, label=lab, ls='--' if r['model'] == '指数＋下限' else '-')
ax.axhline(s_main.loc[2025] / 2, color='#cc5533', ls=':', lw=1)
ax.text(2026, s_main.loc[2025] / 2 - 6, f'2025年度の半分 = {s_main.loc[2025]/2:.1f}億通', color='#cc5533', fontsize=10)
ax.axvline(2025.5, color='#aaaaaa', lw=.8); ax.set_ylim(0, 200); ax.set_xlabel('年度'); ax.set_ylabel('郵便物（億通）')
ax.set_title('モデルの形で「半分になる年」は大きく変わる', fontsize=12)
ax.legend(fontsize=9, frameon=False, loc='lower left')
fig.tight_layout(); fig.savefig(FIG / 'fig3_models.png', dpi=150); plt.close()

# 図4 半分になる年度の予測区間（主分析＋頑健性）
rows = []
for spec, lst in [('主分析 2011〜2025', R['main'])] + list(R['robust'].items()):
    for r in lst:
        if r.get('ok') and r.get('half_q50') is not None:
            rows.append((spec.split('_')[-1] if '_' in spec else spec, r['model'], r['half_q05'], r['half_q50'], r['half_q95'], r['half_year']))
df = pd.DataFrame(rows, columns=['spec', 'model', 'q05', 'q50', 'q95', 'pt'])
fig, ax = plt.subplots(figsize=(9.5, 6.8))
specs = list(dict.fromkeys(df.spec)); models = list(C)
yy = 0; ticks = []; labs = []
for sp in specs:
    for m in models:
        d = df[(df.spec == sp) & (df.model == m)]
        if len(d):
            d = d.iloc[0]; hi = d.q95 if d.q95 is not None and np.isfinite(d.q95) else 2101
            ax.plot([d.q05, min(hi, 2101)], [yy, yy], color=C[m], lw=3, alpha=.6)
            ax.plot(d.pt if np.isfinite(d.pt) else 2101, yy, 'o', color=C[m])
            if hi > 2100: ax.text(2101.5, yy, '→', va='center', color=C[m], fontsize=9)
        yy -= 1
    ticks.append(yy + len(models) / 2 + .5); labs.append(sp); yy -= .8
ax.set_yticks(ticks); ax.set_yticklabels(labs, fontsize=10)
ax.set_xlim(2028, 2104); ax.set_xlabel('2025年度の半分（約59億通）を下回る年度')
for m in models: ax.plot([], [], color=C[m], lw=3, label=m)
ax.legend(fontsize=9, frameon=False, loc='upper center', bbox_to_anchor=(0.45, -0.1), ncol=2)
ax.text(2060, ticks[-1] - 0.9, '荷物を含む総計のロジスティックは、2100年度までに半分にならない', fontsize=8.5, color='#559955')
ax.set_title('「半分になる年」の90%予測区間（点は当てはめた値、→は2100年度以降まで広がる）', fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / 'fig4_half_year_intervals.png', dpi=150); plt.close()

# 図5 種類別（2011年度=100）
fig, ax = plt.subplots(figsize=(9, 4.8))
names = {'第一種': '第一種（封書）', '第二種': '第二種（はがき、年賀を除く）', '年賀': '年賀', '第三種': '第三種（定期刊行物）', '荷物': '荷物（ゆうパック・ゆうメールなど）'}
cc = ['#3366aa', '#559955', '#cc5533', '#999999', '#9966aa']
for (k, lab), c in zip(names.items(), cc):
    v = W[k].loc[2011:2025]; v = v / v.loc[2011] * 100
    hl = R['types'].get(f'{k}_2016', {}).get('half_life')
    ax.plot(v.index, v.values, 'o-', ms=3.5, color=c, label=lab + (f'（半減期 {hl:.0f}年）' if hl and hl < 50 else '（ほぼ横ばい）'))
ax.axhline(50, color='#aaaaaa', ls=':', lw=1); ax.set_ylabel('2011年度 = 100'); ax.set_xlabel('年度')
ax.set_title('種類で減り方は大きく違う（半減期はFY2016〜2025の指数モデル）', fontsize=12)
ax.legend(fontsize=9, frameon=False, loc='lower left')
fig.tight_layout(); fig.savefig(FIG / 'fig5_types.png', dpi=150); plt.close()
print('figs done')
