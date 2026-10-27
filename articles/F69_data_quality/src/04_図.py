"""F69 図（5枚）"""
import sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import *

plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['figure.dpi'] = 150
FIG.mkdir(exist_ok=True)
C_NUM, C_ZERO, C_SYM = '#9db4c0', '#5c6b73', '#e07a5f'

# ---- 図1：5つの表のセルの中身（数値・0・記号）
s = load_ssds(); k = load_kakei(); i = load_idwr(); v = load_vital(); c = load_census()
v = v[v.raw != '']
cvals = pd.concat([c[col] for col in CENSUS_COLS[:-1]])
comp = []
def row(name, raws, sym_label):
    n = pd.Series(raws).map(to_num)
    comp.append(dict(table=name, 数値=(n.notna() & (n != 0)).mean() * 100, ゼロ=(n == 0).mean() * 100,
                     記号=n.isna().mean() * 100, label=sym_label))
row('T1 社会・人口統計体系\n（市区町村）', s.raw, "'-'")
row('T2 家計調査\n（増減率の表）', k[k.kind != '支出金額'].raw, "'-'")
row('T3 感染症発生動向調査\n（報告数）', i.reports, "'-'・'…'")
row('T4 人口動態\n（市区町村別の死亡数）', v[v.table == '死亡数（第3表）'].raw, "'…'")
row('T5 国勢調査2020\n（就業状態の人数）', cvals, "'-'")
cp = pd.DataFrame(comp)
fig, ax = plt.subplots(figsize=(8.2, 4.6))
y = np.arange(len(cp))[::-1]
ax.barh(y, cp['数値'], color=C_NUM, label='数値（0以外）')
ax.barh(y, cp['ゼロ'], left=cp['数値'], color=C_ZERO, label='数字の 0')
ax.barh(y, cp['記号'], left=cp['数値'] + cp['ゼロ'], color=C_SYM, label='記号')
for yy, (_, r) in zip(y, cp.iterrows()):
    ax.text(101, yy, f"記号 {r['記号']:.1f}%（{r.label}）\n0 {r['ゼロ']:.2f}%", va='center', fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(cp.table, fontsize=9)
ax.set_xlim(0, 135); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xlabel('セルの割合（%）')
ax.set_title('5つの統計表のセルの中身：数値・0・記号', fontsize=11)
ax.legend(loc='lower center', bbox_to_anchor=(0.4, -0.32), ncol=3, fontsize=8.5, frameon=False)
fig.tight_layout(); fig.savefig(FIG / 'f69_cells.png'); plt.close()
cp.to_csv(RES / 'cell_composition.csv', index=False)

# ---- 図2：「-」は 0 か欠測か（合計のチェック）
t3 = pd.read_csv(RES / 't3_sum_summary.csv')
t5 = pd.read_csv(RES / 't5_identity_check.csv')
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), gridspec_kw=dict(width_ratios=[1, 1.6]))
ax = axes[0]
vals = [t3.loc[0, '一致した週'], t3.loc[1, '一致した週']]
ax.bar([0, 1], vals, color=[C_NUM, C_SYM], width=0.6)
ax.axhline(736, color='#333', lw=0.8, ls='--'); ax.text(0.5, 760, '全736週', ha='center', fontsize=8.5)
for x, val in zip([0, 1], vals):
    ax.text(x, val + 10, f'{val}週', ha='center', fontsize=9)
ax.set_xticks([0, 1]); ax.set_xticklabels(["'-' を 0\nとみなす", "'-' を欠測\nとみなす"], fontsize=9)
ax.set_ylim(0, 820); ax.set_ylabel('合計＝総数 になった週')
ax.set_title('T3 感染症：47都道府県の報告数の合計＝総数', fontsize=9.5)
ax = axes[1]
lab = {'総数＝労働力＋非労働力＋不詳': '総数＝労働力＋非労働力＋不詳',
       '労働力＝就業者＋完全失業者': '労働力＝就業者＋失業者',
       '就業者＝主に仕事＋家事のほか＋通学のかたわら＋休業者': '就業者＝4つの内訳',
       '非労働力＝家事＋通学＋その他': '非労働力＝家事＋通学＋その他'}
d0 = t5[t5['mode'] == 'dash0'].set_index('identity'); dn = t5[t5['mode'] == 'dashNA'].set_index('identity')
yy = np.arange(4)[::-1]
ax.barh(yy + 0.18, d0.ok.reindex(lab) / 13248 * 100, height=0.34, color=C_NUM, label="'-' を 0 とみなす")
ax.barh(yy - 0.18, dn.ok.reindex(lab) / 13248 * 100, height=0.34, color=C_SYM, label="'-' を欠測とみなす")
for y0, a, b in zip(yy, d0.ok.reindex(lab) / 13248 * 100, dn.ok.reindex(lab) / 13248 * 100):
    ax.text(a + 1, y0 + 0.18, f'{a:.0f}%', va='center', fontsize=8)
    ax.text(b + 1, y0 - 0.18, f'{b:.0f}%', va='center', fontsize=8)
ax.set_yticks(yy); ax.set_yticklabels(list(lab.values()), fontsize=8.5); ax.set_xlim(0, 115)
ax.set_xlabel('式が成り立った行の割合（%、全13,248行）')
ax.set_title('T5 国勢調査：内訳の合計＝総数', fontsize=9.5)
ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.45, -0.17), ncol=2, frameon=False)
fig.suptitle("「-」を 0 とみなすと、合計はすべて合う", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'f69_sumcheck.png'); plt.close()

# ---- 図3：社会・人口統計体系の「-」の3つの意味
g = pd.read_csv(RES / 't1_dash_groups.csv')
g = g[g.cells > 0]
fig, ax = plt.subplots(figsize=(8.4, 3.9))
yy = np.arange(len(g))[::-1]
ax.barh(yy, g.cells, color=[C_SYM, '#f2cc8f', '#81b29a', '#bbbbbb'][:len(g)])
for y0, (_, r) in zip(yy, g.iterrows()):
    ax.text(r.cells + 80, y0, f"{r.cells:,}セル・{r.munis}区域\n2020年人口の中央値 {r.pop_median_2020/1e4:.1f}万人", va='center', fontsize=8)
ax.set_yticks(yy); ax.set_yticklabels([t.replace('（', '\n（') for t in g.group], fontsize=8.5)
ax.set_xlim(0, 9800); ax.set_xlabel("'-' のセルの数（全12,699セル）")
ax.set_title("T1 社会・人口統計体系：同じ '-' でも意味は3通り以上", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'f69_ssds_dash.png'); plt.close()

# ---- 図4：人口動態の「…」は小さい地域に集まる
t4 = pd.read_csv(RES / 't4_ellipsis_by_size.csv')
fig, ax = plt.subplots(figsize=(7.2, 3.8))
x = np.arange(len(t4))
ax.bar(x, t4.share_rows_with_ellipsis * 100, color=C_SYM, width=0.6)
for xx, (_, r) in zip(x, t4.iterrows()):
    ax.text(xx, r.share_rows_with_ellipsis * 100 + 2, f"{r.share_rows_with_ellipsis*100:.0f}%\n（1行あたり {r.mean_ellipsis_per_row:.1f}個）",
            ha='center', fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"{s}\n（{n}市区町村）" for s, n in zip(t4['size'], t4.areas)], fontsize=8.5)
ax.set_ylim(0, 125); ax.set_ylabel("'…' がある行の割合（%）")
ax.set_xlabel('5年間の死亡数（男女計）の大きさ')
ax.set_title("T4 人口動態：'…' は死亡数の少ない市区町村に集まる（数字の 0 は表に1つもない）", fontsize=9.5)
fig.tight_layout(); fig.savefig(FIG / 'f69_vital_ellipsis.png'); plt.close()

# ---- 図5：扱いを間違えたときのずれ
t3d = pd.read_csv(RES / 't3_mean_dash_demo.csv')
t1d = pd.read_csv(RES / 't1_dash_as_zero_demo.csv')
t5l = pd.read_csv(RES / 't5_lfpr_recalc.csv')
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.9), gridspec_kw=dict(width_ratios=[1.6, 1, 1]))
ax = axes[0]
ax.bar(t3d.season.astype(str), (t3d.ratio - 1) * 100, color=C_SYM)
ax.set_ylabel('平均の過大（%）'); ax.set_xlabel('シーズン（始まりの年）')
ax.set_title("T3：'-' を欠測にすると\n定点当たりの平均が大きく出る", fontsize=9.5)
ax.tick_params(axis='x', labelrotation=60, labelsize=8)
ax = axes[1]
fz = t1d[t1d.item.str.contains('財政力')].iloc[0]
ax.bar([0, 1], [fz['欠測として扱う'], fz['ゼロとして扱う']], color=[C_NUM, C_SYM], width=0.6)
for x0, val in zip([0, 1], [fz['欠測として扱う'], fz['ゼロとして扱う']]):
    ax.text(x0, val + 0.01, f'{val:.3f}', ha='center', fontsize=9)
ax.set_xticks([0, 1]); ax.set_xticklabels(['欠測として\n除く', '0 として\n含める'], fontsize=8.5)
ax.set_ylim(0, 0.62); ax.set_title('T1：財政力指数の平均\n（2020年、市区町村）', fontsize=9.5)
ax = axes[2]
ax.bar([0, 1], t5l['差の中央値（pt）'], color=[C_NUM, C_SYM], width=0.6)
for x0, val in zip([0, 1], t5l['差の中央値（pt）']):
    ax.text(x0, val + 0.05, f'{val:.2f}pt', ha='center', fontsize=9)
ax.set_xticks([0, 1]); ax.set_xticklabels(['分母から不詳を\n除く（公表の定義）', '分母に不詳を\n含める'], fontsize=8)
ax.set_ylim(0, 3.5); ax.set_ylabel('公表の労働力率との差（中央値）')
ax.set_title('T5：労働力率の計算し直し', fontsize=9.5)
fig.suptitle('記号や「不詳」の扱いを間違えると、どれだけずれるか', fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'f69_impact.png'); plt.close()
print('ok')
