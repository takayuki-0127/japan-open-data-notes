"""図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import json
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
C = ["#2a78d6", "#eb6834", "#1f9e74", "#8a5cc2", "#c2a01f", "#555555", "#d64f8a"]
GRAY = "#555555"
META = {"Software": None}


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def source(fig, text):
    fig.text(0.01, 0.012, text, fontsize=7.5, color=GRAY)

SRC = "出典：総務省「国勢調査」（2010・2015・2020年）職業（大分類）・配偶関係・年齢別就業者数をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
T = pd.read_csv(RES / "rates_by_occupation.csv")
ORDER = list(M["by_occ"]["男"].keys())


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ys = [2010, 2015, 2020]
    for sex, c in (("男", C[0]), ("女", C[1])):
        v = [M["overall"][sex][str(y)] for y in ys]
        ax.plot(ys, v, color=c, lw=2.6, marker="o", label=f"{sex}性の就業者")
        for x, vv in zip(ys, v):
            ax.text(x, vv + 0.8, f"{vv:.1f}%", ha="center", fontsize=10, color=c)
    d = M["decomposition_2010_2020"]["男"]
    ax.text(0.02, 0.06, f"男性の2010→2020年の上がり（分類不能を除く）{d['total']:+.1f}ポイント\n＝ 職業の中で上がった分 {d['within']:+.1f} ＋ 職業の構成が変わった分 {d['composition']:+.1f}",
            transform=ax.transAxes, fontsize=9.5)
    ax.set_xticks(ys); ax.set_xlim(2008, 2022); ax.set_ylim(0, 30)
    ax.set_ylabel("45〜54歳の就業者のうち未婚の割合（%）")
    ax.legend(loc="upper left", fontsize=10, frameon=False)
    ax.set_title("働いている45〜54歳の未婚の割合：10年で男性15.7%→22.4%、女性10.5%→17.0%", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig1_overall.png")


def fig2():
    m = M["by_occ"]["男"]
    y = np.arange(len(ORDER))[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.barh(y + 0.2, [m[o]["2010"] for o in ORDER], 0.4, color="#9cbfe9", label="2010年")
    ax.barh(y - 0.2, [m[o]["2020"] for o in ORDER], 0.4, color=C[0], label="2020年")
    for yi, o in zip(y, ORDER):
        ax.text(m[o]["2020"] + 0.4, yi - 0.2, f"{m[o]['2020']:.1f}", va="center", fontsize=8.5)
    ax.set_yticks(y, ORDER, fontsize=9.5)
    ax.set_xlim(0, 48)
    ax.set_xlabel("45〜54歳の男性の就業者のうち未婚の割合（%）")
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.set_title("男性（職業は国勢調査の分類の順）：11職業すべてで上がった", loc="left", fontsize=12)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.14)
    source(fig, SRC)
    save(fig, "fig2_men_by_occupation.png")


def fig3():
    m = M["by_occ"]["男"]; w = M["by_occ"]["女"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for o in ORDER:
        ax.scatter(m[o]["2020"], w[o]["2020"], color=C[3], s=45)
        ax.annotate(o, (m[o]["2020"], w[o]["2020"]), xytext=(5, 3) if m[o]["2020"] < 38 else (-5, 6), ha="left" if m[o]["2020"] < 38 else "right", textcoords="offset points", fontsize=8.5)
    ax.plot([0, 45], [0, 45], color="#bbbbbb", ls="--", lw=1)
    sp = M["spearman_men_women_2020"]
    ax.text(0.98, 0.04, f"順位相関 ρ = {sp['rho']:+.2f}（p = {sp['p']:.2f}、11職業）", transform=ax.transAxes, ha="right", fontsize=9.5)
    ax.set_xlim(0, 50); ax.set_ylim(0, 25)
    ax.set_xlabel("男性の未婚の割合（%、2020年、45〜54歳の就業者）")
    ax.set_ylabel("女性の未婚の割合（%）")
    ax.set_title("職業による違いの形は男女で逆向きの傾向（弱い）：男性で高い職業は女性で低め", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.14)
    source(fig, SRC)
    save(fig, "fig3_men_vs_women.png")


def fig4():
    q = pd.read_csv(RES / "requestion_35_44.csv")
    a = q[(q.sex == "男") & (q.year == 2020) & (q.occ != "総数")].set_index("occ").rate.loc[ORDER]
    b = M["by_occ"]["男"]
    y = np.arange(len(ORDER))[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.barh(y + 0.2, a.values, 0.4, color=C[2], label="35〜44歳")
    ax.barh(y - 0.2, [b[o]["2020"] for o in ORDER], 0.4, color=C[0], label="45〜54歳")
    for yi, v in zip(y, a.values):
        ax.text(v + 0.4, yi + 0.2, f"{v:.1f}", va="center", fontsize=8.5)
    ax.set_yticks(y, ORDER, fontsize=9.5)
    ax.set_xlim(0, 55)
    ax.set_xlabel("男性の就業者のうち未婚の割合（%、2020年）")
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.set_title("35〜44歳でも職業による違いの形はほぼ同じ（男性、2020年）", loc="left", fontsize=12)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.14)
    source(fig, SRC)
    save(fig, "fig4_younger_men.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
