"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：法務省「出入国管理統計」（年報、港別の表）をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
yr = pd.read_csv(R / "series_by_year.csv", index_col="year")
reg = pd.read_csv(R / "by_region.csv", index_col="region")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：船で来た外国人（積み上げ）
fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = yr.index.values
a = yr.sea_entries / 1e4; b = yr.special_tourist / 1e4
ax.bar(x, a, 0.7, color=C[0], label="海港での入国（フェリーなど）")
ax.bar(x, b, 0.7, bottom=a, color=C[1], label="観光の特例上陸（クルーズの船舶観光上陸など）")
for xi, t in zip(x, a + b):
    ax.text(xi, t + 4, f"{t:.0f}", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(x, [str(v) for v in x], fontsize=9); ax.set_ylabel("万人（回）"); ax.set_ylim(0, 360)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.set_title("図1　船で日本に来た外国人（海港での入国＋観光の特例上陸）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.2)
foot(fig, "特例上陸は寄港地上陸・通過上陸・船舶観光上陸の合計（乗員上陸は入れない）。棒の上の数字は合計（万人）。")
save(fig, "fig1_sea_arrivals.png")

# 図2：2019年＝100 の推移
fig, ax = plt.subplots(figsize=(8.8, 4.8))
yy = yr.loc[2015:]
for col, c, nm in [("air_entries", C[2], "空港での入国（外国人）"), ("sea_total", "#1f1f1f", "船で来た外国人の合計"),
                   ("sea_entries", C[0], "海港での入国（フェリーなど）"), ("funa", C[1], "船舶観光上陸（クルーズ）")]:
    v = yy[col] / yr.loc[2019, col] * 100
    ax.plot(v.index, v, marker="o", ms=3.5, lw=2, color=c, label=nm)
    ax.text(2025.25, v.loc[2025], f"{v.loc[2025]:.0f}", va="center", fontsize=9, color=c)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2014.6, 2025.9); ax.set_ylim(0, 160); ax.set_ylabel("2019年＝100")
ax.set_xticks(range(2015, 2026)); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title("図2　2019年を100とした動き（2025年の値を右に表示）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.95, top=0.9, bottom=0.2)
foot(fig, "2021・2022年は船舶観光上陸が0。")
save(fig, "fig2_index_2019.png")

# 図3：地方別 2025年の2019年比（北から南）
fig, ax = plt.subplots(figsize=(8.8, 4.8))
yv = np.arange(len(reg))
ax.barh(yv, reg.ratio_2025_2019 * 100, 0.55, color=C[0], label="2019年＝100")
ax.scatter(reg.ratio_2025_2018 * 100, yv, color=C[1], zorder=3, s=30, label="2018年＝100")
for i, (r, row) in enumerate(reg.iterrows()):
    ax.text(max(row.ratio_2025_2019, row.ratio_2025_2018) * 100 + 6, i + 0.05, f"{row.ratio_2025_2019 * 100:.0f}（{row.total_2019 / 1e4:.1f}→{row.total_2025 / 1e4:.1f}万人）",
            va="center", fontsize=8.6, color=INK2)
ax.axvline(100, color=INK2, lw=0.8)
ax.set_yticks(yv, reg.index); ax.invert_yaxis(); ax.set_xlim(0, 340)
ax.set_xlabel("2025年の船で来た外国人（2019年＝100、点は2018年＝100）")
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("図3　地方別の戻り方（北から南の順）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.13, right=0.97, top=0.9, bottom=0.2)
foot(fig, "港の都道府県で地方に分けた。九州の大半は博多・長崎・対馬など、沖縄は那覇・石垣・平良など。")
save(fig, "fig3_by_region.png")

# 図4：海港での入国の国籍
G = ["韓国", "北アメリカ", "ヨーロッパ", "オセアニア", "台湾", "中国"]
bn = req["by_nationality"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
xx = np.arange(len(G)); w = 0.26
for k, (y, c) in enumerate([("2013", "#9b9a96"), ("2019", C[0]), ("2025", C[1])]):
    v = [bn[g][y] / 1e4 for g in G]
    ax.bar(xx + (k - 1) * w, v, w, color=c, label=f"{y}年")
    for xi, vv in zip(xx + (k - 1) * w, v):
        ax.text(xi, vv + 0.6, f"{vv:.1f}", ha="center", fontsize=7.6, color=INK2)
ax.set_xticks(xx, G); ax.set_ylabel("万人（回）"); ax.set_ylim(0, 52)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=9)
ax.set_title("図4　海港での入国（ふつうの入国）の国籍・地域", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.2)
foot(fig, "並びは国・地域の区分の順で、値の順ではない。北アメリカ・ヨーロッパ・オセアニアは地域の合計。")
save(fig, "fig4_sea_entries_nationality.png")
print("figures ok")
