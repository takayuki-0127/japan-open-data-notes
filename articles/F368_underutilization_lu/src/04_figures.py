"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#888888", "axes.grid": True,
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.8})
BLUE, ORANGE, GRAY, GREEN = "#2a78d6", "#eb6834", "#555555", "#3a9e6f"
SRC = "出典：総務省「労働力調査」詳細集計（年平均、年齢階級別未活用労働指標）をもとに作成者が加工して作成"
META = {"Software": None}
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]
PARTS = [("LU1", "失業者（LU1）", "#08519c"), ("addl_part", "もっと働きたい就業者の分（LU2−LU1）", "#6baed6"),
         ("potential_part", "潜在労働力の分（LU3−LU1）", ORANGE)]
d = pd.read_csv(RES / "lu_with_parts.csv")


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def stack(ax, z, x, width=0.6):
    bottom = np.zeros(len(z))
    for k, lab, c in PARTS:
        ax.bar(x, z[k].values, bottom=bottom, width=width, color=c, label=lab)
        bottom += z[k].values
    return bottom


def fig1():
    t = d[(d.sex == "男女計") & (d.age == "年齢計")].set_index("year")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for k, lab, c, ls in [("LU4", "LU4（すべて含む）", "#08306b", "-"), ("LU2", "LU2（失業者＋もっと働きたい就業者）", BLUE, "-"),
                          ("LU3", "LU3（失業者＋潜在労働力）", ORANGE, "--"), ("LU1", "LU1（失業者、失業率に近い）", GRAY, "-")]:
        ax.plot(t.index, t[k], color=c, lw=2.2, ls=ls, marker="o", ms=4, label=lab)
        ax.annotate(f"{t.loc[2025, k]:.1f}", (2025, t.loc[2025, k]), xytext=(5, 0), textcoords="offset points", va="center", color=c, fontsize=9)
    ax.set_ylim(0, 8.5)
    ax.set_xlim(2017.6, 2025.6)
    ax.set_ylabel("割合（%）")
    ax.set_xlabel("年（年平均）")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.set_title("未活用労働指標：LU4はLU1の2.1〜2.3倍（2025年はLU1 2.8%、LU4 6.1%）", loc="left", fontsize=11.5)
    save(fig, "fig1_lu_trend.png")


def fig2():
    t = d[d.age == "年齢計"].set_index(["sex", "year"])
    keys = [("男", 2019), ("男", 2025), ("女", 2019), ("女", 2025)]
    z = pd.DataFrame([t.loc[k] for k in keys])
    x = np.array([0, 1, 2.6, 3.6])
    fig, ax = plt.subplots(figsize=(8, 4.8))
    top = stack(ax, z, x, width=0.7)
    for xi, (k, v) in zip(x, zip(keys, top)):
        ax.text(xi, v + 0.15, f"LU4に近い計 {v:.1f}", ha="center", fontsize=8.5)
        ax.text(xi, t.loc[k, "LU1"] + t.loc[k, "addl_part"] / 2, f"{t.loc[k, 'addl_part']:.1f}", ha="center", va="center", fontsize=9)
    ax.set_xticks(x, [f"{s}\n{y}年" for s, y in keys])
    ax.set_ylim(0, 10)
    ax.set_ylabel("労働力人口などに対する割合（%）")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax.set_title("女は「もっと働きたい就業者」の分が4.1ポイント、男は1.7ポイント（2025年）", loc="left", fontsize=11.5)
    save(fig, "fig2_parts_by_sex.png")


def fig3():
    z = d[(d.sex == "男女計") & (d.year == 2025) & (d.age.isin(AGES))].set_index("age").loc[AGES]
    x = np.arange(len(AGES))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    top = stack(ax, z, x)
    for i, a in enumerate(AGES):
        ax.text(i, top[i] + 0.2, f"差 {z.loc[a, 'gap41']:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x, AGES)
    ax.set_ylim(0, 14)
    ax.set_ylabel("割合（%）")
    ax.legend(loc="upper right", frameon=False, fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax.set_title("年齢別（2025年、男女計）：LU4−LU1は15〜24歳で6.5ポイント", loc="left", fontsize=11.5)
    save(fig, "fig3_parts_by_age.png")


def fig4():
    q = pd.read_csv(RES / "requestion_age_sex_parts_2025.csv", index_col=0).loc[AGES]
    x = np.arange(len(AGES))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(x - 0.2, q["男_addl_part"], width=0.4, color=BLUE, label="男")
    ax.bar(x + 0.2, q["女_addl_part"], width=0.4, color=ORANGE, label="女")
    for i, a in enumerate(AGES):
        ax.text(i - 0.2, q.loc[a, "男_addl_part"] + 0.1, f"{q.loc[a, '男_addl_part']:.1f}", ha="center", fontsize=9)
        ax.text(i + 0.2, q.loc[a, "女_addl_part"] + 0.1, f"{q.loc[a, '女_addl_part']:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x, AGES)
    ax.set_ylim(0, 7)
    ax.set_ylabel("もっと働きたい就業者の分（LU2−LU1、ポイント）")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title("35〜54歳の女は約5ポイント、男は約1ポイント（2025年）", loc="left", fontsize=11.5)
    save(fig, "fig4_additional_hours_by_age_sex.png")


fig1()
fig2()
fig3()
fig4()
