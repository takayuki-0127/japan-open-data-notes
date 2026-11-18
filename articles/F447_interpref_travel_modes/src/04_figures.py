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
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
COL = {"rail": "#2a78d6", "air": "#eb6834", "bus": "#1baf7a", "ship": "#eda100", "taxi": "#9b9a97"}
NAME = {"rail": "鉄道（定期外）", "air": "航空", "bus": "バス", "ship": "旅客船", "taxi": "タクシー等"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：国土交通省「旅客地域流動調査」、気象庁「地域気象観測所一覧」をもとに作成者が加工して作成"
META = {"Software": None}
BLAB = ["100km未満", "100〜300km", "300〜500km", "500〜700km", "700〜1,000km", "1,000km以上"]


def save(fig, name):
    fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
bs = pd.read_csv(R / "band_mode_share.csv")

# 図1：距離帯ごとの手段の割合（2017〜19年度）
t = bs[bs.period == "2017_19"].set_index("band").loc[BLAB]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
left = np.zeros(len(BLAB)); y = np.arange(len(BLAB))[::-1]
for k in ["rail", "bus", "air", "ship", "taxi"]:
    ax.barh(y, t[k], left=left, color=COL[k], label=NAME[k], height=0.62)
    for i, (l, v) in enumerate(zip(left, t[k])):
        if v >= 6:
            ax.text(l + v / 2, y[i], f"{v:.0f}%", ha="center", va="center", fontsize=9, color="white")
    left += t[k].values
vol = m["band_volume_2017_19_million_per_year"]
ax.set_yticks(y, [f"{b}\n（{vol[b]:,.0f}百万人/年）" for b in BLAB], fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("県をまたぐ公共交通の定期外の人数に占める割合（%）")
ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.13))
ax.set_title("距離で手段が入れ替わる：500〜700kmで鉄道と航空がほぼ半々（2017〜19年度）", loc="left", fontsize=12, color=INK, pad=10)
fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.25)
save(fig, "fig1_band_mode_share.png")

# 図2：鉄道の割合の変化（距離帯別、3時点）
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(len(BLAB))
for per, lab, c, mk in [("2000_02", "2000〜02年度", "#9b9a97", "o"), ("2017_19", "2017〜19年度", COL["rail"], "o"), ("2024", "2024年度", COL["air"], "D")]:
    v = bs[bs.period == per].set_index("band").loc[BLAB, "rail"]
    ax.plot(x, v, marker=mk, color=c, lw=1.6, label=lab, ms=6)
a = bs[bs.period == "2000_02"].set_index("band").loc[BLAB, "rail"]; b = bs[bs.period == "2017_19"].set_index("band").loc[BLAB, "rail"]
for i in range(len(BLAB)):
    ax.text(i + 0.08, b.iloc[i] + 3, f"{b.iloc[i] - a.iloc[i]:+.1f}", fontsize=8.5, color=COL["rail"])
ax.set_xticks(x, BLAB, fontsize=9.5)
ax.set_ylabel("鉄道の割合（%）"); ax.set_ylim(0, 105)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9.5)
ax.set_title("鉄道の割合は300〜700kmで上がった（青い数字は2000〜02→2017〜19年度の差、ポイント）", loc="left", fontsize=11.5, color=INK, pad=10)
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig2_rail_share_by_band.png")

# 図3：機関別の県間の人数（2019年度＝100）
idx = pd.read_csv(R / "index_2019_100.csv").set_index("fy").loc[2010:2024]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
for k in ["rail", "air", "bus"]:
    ax.plot(idx.index, idx[k], color=COL[k], lw=2, label=NAME[k])
    off = {"air": 3.5, "rail": -3.5, "bus": 0}[k]
    ax.text(2024.2, idx.loc[2024, k] + off, f"{idx.loc[2024, k]:.0f}", color=COL[k], fontsize=9.5, va="center")
ax.axhline(100, color=INK2, lw=0.7, ls=":")
ax.set_xlim(2010, 2025.3); ax.set_ylim(0, 130)
ax.set_ylabel("2019年度＝100"); ax.set_xlabel("年度")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9.5, loc="lower left")
ax.set_title("2024年度、県間の鉄道と航空はコロナ前を超え、バスは7割台", loc="left", fontsize=12, color=INK, pad=10)
fig.subplots_adjust(left=0.09, right=0.95, top=0.89, bottom=0.17)
save(fig, "fig3_recovery_index.png")

# 図4：問い直し　乗合バスと貸切バス（県間、百万人）
q = pd.read_csv(R / "requestion_bus_route_charter.csv").set_index("fy")
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.plot(q.index, q["bus_route"], color=COL["bus"], lw=2, label="乗合バス（高速バスなどを含む）")
ax.plot(q.index, q["bus_charter"], color=COL["ship"], lw=2, label="貸切バス")
for yy in (2011, 2019):
    ax.axvline(yy - 0.5, color=GRID, lw=1.2, ls="--")
ax.text(2010.6, 125, "貸切は2011・2019年度に\n段差（理由は表から分からない）", fontsize=8.5, color=INK2)
ax.set_ylim(0, 140); ax.set_xlabel("年度"); ax.set_ylabel("県をまたぐ人数（百万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9.5, loc="lower left")
ax.set_title("乗合バスは2019年度まで伸びて2024年度に76%、貸切バスは長く減り続けた", loc="left", fontsize=12, color=INK, pad=10)
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig4_bus_route_charter.png")
print("ok")
