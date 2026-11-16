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
SRC = "出典：総務省「家計調査」二人以上の世帯 第4-6表（世帯主の年齢階級別、年次）、総務省「消費者物価指数」をもとに作成者が加工"
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
W = pd.read_csv(RES / "panel_by_age_year.csv")
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：教育費の割合（30代・40代・50代）
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.86, top=0.83, bottom=0.14)
for k, a in enumerate(["30～39歳", "40～49歳", "50～59歳"]):
    s = W[W.age == a].set_index("year").share_edu
    ax.plot(s.index, s, color=C6[k], lw=2); ax.text(2025.4, {"30～39歳": s.iloc[-1], "40～49歳": 7.1, "50～59歳": 8.8}[a], a, fontsize=9, va="center", color=C6[k])
ax.set_ylabel("消費支出に占める教育費の割合（%）"); ax.set_xlabel("年"); ax.set_ylim(0, 11); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("40代の世帯では教育費の割合が下がり、50代では上がった", x=0.02, ha="left", fontsize=13, y=0.97)
a4, a5 = m["age40"], m["age50"]
fig.text(0.02, 0.885, f"世帯主の年齢別。2002〜04年平均→2023〜25年平均：40代 {a4['share_edu'][0]:.1f}%→{a4['share_edu'][1]:.1f}%、50代 {a5['share_edu'][0]:.1f}%→{a5['share_edu'][1]:.1f}%", fontsize=9, color=INK2)
save(fig, "fig1_edu_share_by_age.png")

# 図2：年齢ごとの割合と子どもの数（始点・終点）
P = q["profile"]; x = np.arange(len(AG)); w = 0.38
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.16)
s0 = [P["2002〜04年"][a]["share"] for a in AG]; s1 = [P["2023〜25年"][a]["share"] for a in AG]
ax.bar(x - w / 2, s0, w, color=GRAY, label="2002〜04年")
ax.bar(x + w / 2, s1, w, color=C6[0], label="2023〜25年")
for xi, a in zip(x, AG):
    ax.text(xi - w / 2, P["2002〜04年"][a]["share"] + 0.15, f"{P['2002〜04年'][a]['children']:.2f}", ha="center", fontsize=7.8, color=INK2)
    ax.text(xi + w / 2, P["2023〜25年"][a]["share"] + 0.15, f"{P['2023〜25年'][a]['children']:.2f}", ha="center", fontsize=7.8)
ax.set_xticks(x); ax.set_xticklabels(AG); ax.set_ylabel("消費支出に占める教育費の割合（%）"); ax.set_ylim(0, 11)
ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=9)
fig.suptitle("教育費の山は、40代から50代へ広がった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, "棒の上の数字は、1世帯当たりの18歳未満の人数（人）。50代は 0.32人→0.47人に増えた", fontsize=9, color=INK2)
save(fig, "fig2_age_profile.png")

# 図3：40代の授業料等と補習教育（名目）
s = W[W.age == "40～49歳"].set_index("year")
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.1, right=0.85, top=0.83, bottom=0.14)
ax.plot(s.index, s.tuition / 1000, color=C6[0], lw=2); ax.text(2025.4, s.tuition.iloc[-1] / 1000, "授業料等", fontsize=9, va="center")
ax.plot(s.index, s.cram / 1000, color=C6[1], lw=2); ax.text(2025.4, s.cram.iloc[-1] / 1000, "補習教育\n（塾など）", fontsize=9, va="center")
ax.axvspan(2019.5, 2020.5, color="#e6e5e1", lw=0)
ax.set_ylabel("1世帯の年間の支出（千円、名目）"); ax.set_xlabel("年"); ax.set_ylim(0, 320); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("40代の世帯：授業料等は2020年に下がり、塾などの割合が上がった", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"灰色は2020年。授業料等 2018〜19年→2021〜22年 {a4['tuition_2018_19_to_2021_22']:.1f}（対数差×100）。教育費に占める補習教育 {a4['share_cram'][0]:.1f}%→{a4['share_cram'][1]:.1f}%", fontsize=9, color=INK2)
save(fig, "fig3_age40_tuition_cram.png")

# 図4：18歳未満1人当たりの実質の教育費（指数）
r = pd.read_csv(RES / "requestion_40_59_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.8, top=0.83, bottom=0.14)
b4 = s.real_edu_per_child; i4 = 100 * b4 / b4.loc[[2002, 2003, 2004]].mean()
ic = 100 * r.real_per_child / r.real_per_child.loc[[2002, 2003, 2004]].mean()
ax.plot(i4.index, i4, color=C6[0], lw=2); ax.text(2025.4, i4.iloc[-1] - 3, "40代の世帯", fontsize=9, va="center")
ax.plot(ic.index, ic, color=C6[3], lw=2); ax.text(2025.4, ic.iloc[-1] + 3, "40代と50代の世帯\n（まとめて）", fontsize=9, va="center")
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（2002〜04年平均＝100）"); ax.set_xlabel("年"); ax.set_ylim(70, 130); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("18歳未満1人当たりの実質の教育費は、40〜50代でまとめると増えた", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"教育の物価で割った実質。2002〜04年→2023〜25年：40代 {a4['real_edu_per_child_dlog']:+.1f}、40〜50代 {q['age40_59']['real_per_child_dlog']:+.1f}（対数差×100）", fontsize=9, color=INK2)
save(fig, "fig4_real_per_child.png")
print("ok")
