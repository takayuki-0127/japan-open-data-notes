"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：厚生労働省「雇用保険事業年報」平成29〜令和7年度 第1表をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)
Y = sorted(int(k) for k in m["rate_by_fy"])

# 図1：開業率と廃業率
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.86, top=0.83, bottom=0.14)
r = [m["rate_by_fy"][str(y)] for y in Y]; c = [m["closure_by_fy"][str(y)] for y in Y]
ax.plot(Y, r, color=C6[0], lw=2, marker="o", ms=5); ax.text(2025.3, r[-1] + 0.12, "開業率", fontsize=9, color=C6[0])
ax.plot(Y, c, color=C6[1], lw=2, marker="o", ms=5); ax.text(2025.3, c[-1] - 0.2, "廃業率", fontsize=9, color=C6[1])
for y, v in zip(Y, r): ax.text(y, v + 0.12, f"{v:.1f}", ha="center", fontsize=8.5, color=C6[0])
ax.set_ylabel("前年度末の適用事業所に対する割合（%）"); ax.set_xlabel("年度"); ax.set_ylim(0, 6); ax.set_xticks(Y); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("雇用保険の開業率は4%前後で、2023年度からは廃業率とほぼ同じ", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"開業率 ＝ 新規適用事業所数 ÷ 前年度末の適用事業所数。2018〜2025年度の平均 {m['H1']['mean']:.1f}%（最小 {m['H1']['min']:.1f}%、最大 {m['H1']['max']:.1f}%）", fontsize=9, color=INK2)
save(fig, "fig1_startup_closure_rates.png")

# 図2：産業別の開業率（上位8と下位5）
im = list(m["industry_mean_rate"].items())
show = im[:9] + im[-5:]
fig, ax = plt.subplots(figsize=(8.4, 5.4)); fig.subplots_adjust(left=0.33, right=0.95, top=0.84, bottom=0.12)
labels = [k.split(" ", 1)[1] for k, _ in show]; vals = [v for _, v in show]
cols = [C6[1] if k.startswith("Ｄ") else C6[0] for k, _ in show]
yy = np.arange(len(show)); ax.barh(yy, vals, color=cols, height=0.65)
for yi, v in zip(yy, vals): ax.text(v + 0.1, yi, f"{v:.1f}%", va="center", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels(labels); ax.invert_yaxis(); ax.set_xlim(0, 11)
ax.axhline(8.5, color=GRAY, lw=0.8, ls=":"); ax.set_xlabel("開業率の2018〜2025年度平均（%）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
fig.suptitle("いちばん高いのは宿泊業・飲食サービス業。建設業は中ほどだった", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.895, f"大分類18産業のうち上位9と下位5（点線の上と下）。建設業 {m['H2']['construction']:.1f}%（オレンジ）", fontsize=9, color=INK2)
save(fig, "fig2_rate_by_industry.png")

# 図3：2020年度に跳ねた分
ch = pd.read_csv(RES / "requestion_2020_change.csv", index_col=0).head(6)
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.33, right=0.95, top=0.82, bottom=0.14)
yy = np.arange(len(ch)); ax.barh(yy, ch.change_2019_2020, color=[C6[0] if i == 0 else GRAY for i in range(len(ch))], height=0.6)
for yi, v in zip(yy, ch.change_2019_2020): ax.text(v + 150, yi, f"{v:+,.0f}", va="center", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels(ch.name); ax.invert_yaxis(); ax.set_xlim(-1000, 13000)
ax.set_xlabel("新規適用事業所数の増減（2019年度→2020年度、所）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
fig.suptitle("2020年度の開業率の跳ね上がりは、半分が宿泊業・飲食サービス業", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.875, f"全体の増加 {q['total_change_2019_2020']:+,} 所のうち {q['share_M']:.0f}%。宿泊業・飲食サービス業を除くと2020年度の開業率は {q['rate_2020_exM']:.1f}%（全体では {m['rate_by_fy']['2020']:.1f}%）", fontsize=9, color=INK2)
save(fig, "fig3_fy2020_jump.png")

# 図4：数え方を変えた開業率
rb = {r["spec"]: r for r in m["robustness"]}
items = [("ふつうの開業率", m["H1"]["mean"]), ("分母を年度の初めと終わりの平均に", rb["R1 分母を年度の初めと終わりの平均に"]["mean"]),
         ("任意適用を除く", rb["R5 任意適用を分子から除く"]["mean"]), ("建設業を除く", m["H3"]["ex_construction_mean"]),
         ("産業の構成を2017年度末に固定", rb["R3 産業の構成を平成29年度末に固定"]["mean"]), ("どの産業も同じ重み", m["H4"]["equal_weight_mean"]),
         ("2020・2021年度を除く", rb["R2 令和2・3年度を除く"]["mean"]), ("宿泊業・飲食サービス業を除く", float(np.mean(list(q["rate_exM_by_fy"].values())))),
         ("開業率 − 廃業率（純増）", rb["R4 純増の率（開業率−廃業率）"]["mean"])]
fig, ax = plt.subplots(figsize=(8.4, 5.2)); fig.subplots_adjust(left=0.36, right=0.95, top=0.84, bottom=0.12)
yy = np.arange(len(items)); vals = [v for _, v in items]
ax.barh(yy, vals, color=[C6[0]] + [GRAY] * (len(items) - 2) + [C6[1]], height=0.6)
for yi, v in zip(yy, vals): ax.text(v + 0.05, yi, f"{v:.2f}%", va="center", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels([k for k, _ in items]); ax.invert_yaxis(); ax.set_xlim(0, 5.2)
ax.set_xlabel("2018〜2025年度の平均（%）"); ax.grid(axis="x", color="#e6e5e1", lw=0.6)
fig.suptitle("数え方を変えても、開業率は3.9〜4.3%の幅に収まった", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.895, "大きく変わるのは、廃業を差し引いた「純増」で見るときだけ", fontsize=9, color=INK2)
save(fig, "fig4_counting_methods.png")
print("ok")
