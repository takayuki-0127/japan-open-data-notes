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

SRC = "出典：外務省「海外在留邦人数調査統計」（e-Stat）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
N = pd.read_csv(RES / "national.csv").set_index("year")
R = pd.read_csv(RES / "region_2019_2025.csv")
CL = pd.read_csv(RES / "country_long_2019_2025.csv").set_index("country")
REGIONS = ["アジア", "大洋州", "北米", "中米", "南米", "西欧", "東欧・旧ソ連", "中東", "アフリカ"]


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(N.index, N.long / 1e4, color=C[0], width=0.8, label="長期滞在者（仕事・留学など）")
    ax.bar(N.index, N.perm / 1e4, bottom=N.long / 1e4, color=C[1], width=0.8, label="永住者")
    for y in (2019, 2025):
        ax.annotate(f"{N.total[y]/1e4:.1f}万人", (y, N.total[y] / 1e4), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
    ax.text(1990.3, 140, f"長期滞在者 {N.long[2019]/1e4:.1f}万→{N.long[2025]/1e4:.1f}万（{M['chg_2019_2025']['long']:+.1f}%）\n永住者 {N.perm[2019]/1e4:.1f}万→{N.perm[2025]/1e4:.1f}万（{M['chg_2019_2025']['perm']:+.1f}%）\n（2019→2025年）", ha="left", va="top", fontsize=9)
    ax.set_ylim(0, 165)
    ax.set_ylabel("海外在留邦人（万人、各年10月1日）")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_title("海外在留邦人は2019年の141.0万人がピーク。長期滞在者が減り、永住者は増え続けた", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC)
    save(fig, "fig1_long_perm.png")


def fig2():
    l = R[R.kind == "long"].set_index("region").reindex(REGIONS)
    p = R[R.kind == "perm"].set_index("region").reindex(REGIONS)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    y = np.arange(len(REGIONS))[::-1]
    ax.barh(y + 0.18, l["diff"] / 1e4, height=0.36, color=C[0], label="長期滞在者")
    ax.barh(y - 0.18, p["diff"] / 1e4, height=0.36, color=C[1], label="永住者")
    for yi, d in zip(y, l["diff"]):
        if abs(d) >= 3000:
            ax.text(d / 1e4 - 0.15, yi + 0.18, f"{d/1e4:+.1f}万", va="center", ha="right", fontsize=8.5)
    for yi, d in zip(y, p["diff"]):
        if abs(d) >= 3000:
            ax.text(d / 1e4 + (0.15 if d > 0 else -0.15), yi - 0.18, f"{d/1e4:+.1f}万", va="center", ha="left" if d > 0 else "right", fontsize=8.5)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, REGIONS)
    ax.set_xlim(-9.5, 4.5)
    ax.set_xlabel("2019年→2025年の増減（万人）")
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.grid(axis="y", visible=False)
    ax.set_title("長期滞在者はアジア・北米・西欧で減り、永住者は北米・西欧・アジアで増えた", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.9, bottom=0.13)
    source(fig, SRC + "。地域は表の順。南極は省略")
    save(fig, "fig2_region_change.png")


def fig3():
    c = CL.sort_values("diff").head(10)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    y = np.arange(len(c))[::-1]
    col = {"アジア": C[0], "北米": C[1], "西欧": C[2]}
    ax.barh(y, c["diff"] / 1e4, color=[col.get(r, "#999999") for r in c.region], height=0.6)
    for yi, d, s in zip(y, c["diff"], c.share_of_change):
        ax.text(d / 1e4 - 0.1, yi, f"{d/1e4:+.2f}万人（減少の{s:.1f}%）", va="center", ha="right", fontsize=8.5)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, [f"{k}（{r}）" for k, r in zip(c.index, c.region)])
    ax.set_xlim(-7.5, 0.3)
    ax.set_xlabel("長期滞在者の増減（2019年→2025年、万人）")
    ax.grid(axis="y", visible=False)
    ax.set_title("長期滞在者の減少（−18.2万人）で最も大きいのは米国（27.6%）、次いで中国（14.4%）", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.13)
    source(fig, SRC + "。減少の大きい10か国（地域）")
    save(fig, "fig3_country_long.png")


def fig4():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    n = N.copy()
    ax.plot(n.index, n.female_share_perm, color=C[1], lw=2.2, label="永住者のうち女性")
    ax.plot(n.index, n.female_share, color="#222222", lw=2.2, label="全体のうち女性")
    ax.plot(n.index, n.female_share_long, color=C[0], lw=2.2, label="長期滞在者のうち女性")
    for col, dy in (("female_share_perm", 8), ("female_share", 8), ("female_share_long", -16)):
        for y in (1991, 2025):
            ax.annotate(f"{n[col][y]:.1f}%", (y, n[col][y]), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=9)
    ax.axhline(50, color="#888888", lw=0.8, ls="--")
    ax.set_xlim(1989, 2027); ax.set_ylim(40, 70)
    ax.set_ylabel("女性の割合（%）")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_title("女性の割合は全体で48.7%→54.3%。長期滞在者ではほぼ横ばい", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。1997年の長期滞在者・永住者の男女は表になし")
    save(fig, "fig4_female_share.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
