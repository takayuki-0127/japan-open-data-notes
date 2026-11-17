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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ」、農林水産省「作物統計調査」「畜産統計調査」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
W = pd.read_csv(R / "ch4_series.csv").set_index("fy")
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
parts = [("rice", "稲作（田んぼ）"), ("enteric", "家畜の消化管内発酵（牛のげっぷなど）"), ("manure", "家畜排せつ物の管理"),
         ("landfill", "埋立（ごみ）"), ("fugitive", "燃料からの漏出（炭鉱など）")]
other = W.total - sum(W[c] for c, _ in parts)

# ---- 図1：分野別（積み上げ） -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.stackplot(W.index, [W[c].values for c, _ in parts] + [other.values], colors=C6,
             labels=[n for _, n in parts] + ["その他（排水処理・燃料の燃焼など）"], edgecolor="#fcfcfb", linewidth=0.6)
ax.legend(loc="upper right", frameon=False, fontsize=8.6)
ax.set_xlim(1990, 2024); ax.set_ylim(0, 62)
ax.set_ylabel("メタンの排出（百万トン CO2 換算）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"メタンは1990→2024年度で{main['total_1990']:.1f}→{main['total_2024']:.1f}百万トン。減ったのは主に埋立と炭鉱", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：CO2 換算（インベントリの地球温暖化係数）。2026年版。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_ch4_by_sector.png")

# ---- 図2：1990年度と2024年度の構成 ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 3.8))
for i, y in enumerate([1990, 2024]):
    left = 0.0
    vals = [W[c].loc[y] / W.total.loc[y] * 100 for c, _ in parts] + [other.loc[y] / W.total.loc[y] * 100]
    for k, v in enumerate(vals):
        ax.barh(i, v, left=left, color=C6[k], height=0.55, edgecolor="#fcfcfb", linewidth=1.5)
        if v >= 4:
            ax.text(left + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9.5, color="white" if k in (0, 1, 5) else INK)
        left += v
ax.set_yticks([0, 1]); ax.set_yticklabels(["1990年度", "2024年度"]); ax.invert_yaxis()
ax.set_xlim(0, 100); ax.set_xlabel("メタンの排出に占める割合（%）")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C6[k], label=n) for k, n in enumerate([n for _, n in parts] + ["その他"])], loc="upper center",
          bbox_to_anchor=(0.5, -0.32), ncol=3, frameon=False, fontsize=8.4)
ax.set_title(f"田んぼと牛（消化管内発酵）の割合は{main['share_rice_enteric_1990']:.0f}%→{main['share_rice_enteric_2024']:.0f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.42)
save(fig, "fig2_share_1990_2024.png")


def index_plot(name, cols, title, note, dys=(0, 0, 0)):
    fig, ax = plt.subplots(figsize=(8.8, 4.9))
    for (c, lab), col, dy in zip(cols, [C[1], C[0], C[2]], dys):
        v = W[c] / W[c].loc[1990] * 100
        ax.plot(W.index, v, color=col, lw=2.2)
        ax.text(2024.4, v.loc[2024] + dy, f"{lab} {v.loc[2024]:.0f}", va="center", fontsize=9, color=col if False else INK)
    ax.axhline(100, color=INK2, lw=0.8, ls=":")
    ax.set_xlim(1990, 2033); ax.set_ylim(50, 160)
    ax.set_xticks(range(1990, 2025, 5))
    ax.set_ylabel("1990年度＝100")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=11.5)
    fig.text(0.01, 0.01, note + "\n" + SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
    return fig, ax


# ---- 図3：稲作 ---------------------------------------------------------------------------------
fig, ax = index_plot("fig3", [("rice", "稲作のメタン"), ("rice_area_mha", "水稲の作付面積"), ("rice_per_ha", "面積あたり")],
                     f"田んぼの面積は35%減ったが、稲作のメタンは2023年度まで4%減にとどまった",
                     f"注：面積あたりの前年度比は2024年度に−{abs(req['per_ha_yoy_2024_pct']):.1f}%（1991〜2023年度の最大の動きは±{req['per_ha_yoy_max_abs_1991_2023']:.1f}%）。")
v = W.rice / W.rice.loc[1990] * 100
ax.annotate(f"2024年度 −{abs(req['rice_yoy_2024_pct']):.1f}%（面積は{req['area_yoy_2024_pct']:+.1f}%）", (2024, v.loc[2024]), xytext=(1996, 55), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
save(fig, "fig3_rice_index.png")

# ---- 図4：牛 ----------------------------------------------------------------------------------
fig, ax = index_plot("fig4", [("enteric", "消化管内発酵のメタン"), ("cattle_mhead", "牛の頭数"), ("enteric_per_head", "1頭あたり")],
                     "牛のげっぷなどのメタンは、ほぼ頭数に比例して動いた（1頭あたりは横ばい）",
                     "注：牛の頭数は乳用牛（めす）＋肉用牛の総頭数。年度 t には翌年2月1日現在の頭数を合わせた。消化管内発酵には牛以外の家畜も含む。", dys=(4, -4, 0))
save(fig, "fig4_enteric_index.png")
print("ok")
