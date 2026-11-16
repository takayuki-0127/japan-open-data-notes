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
SRC = "出典：農林水産省「漁業・養殖業生産統計」長期累年をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
b = pd.read_csv(R / "bumon_series.csv").set_index("year")
s = pd.read_csv(R / "shurui_series.csv").set_index("year")
sp = pd.read_csv(R / "requestion_split.csv").set_index("year")
mix = pd.read_csv(R / "distant_tuna_mix.csv").set_index("year")

# ---- 図1：部門別 -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("offshore", "沖合", C[0]), ("coastal", "沿岸", C[2]), ("distant", "遠洋", C[1])]:
    ax.plot(b.index, b[col] / 1000, color=c, lw=2.2)
    ax.text(2024.5, b[col].loc[2024] / 1000, f"{lab} {b[col].loc[2024]/1000:.2f}", va="center", fontsize=9.5, color=INK)
ax.annotate(f"遠洋の最大 {main['distant_peak_year']}年 {main['distant_peak_kt']/1000:.2f}", (main["distant_peak_year"], main["distant_peak_kt"] / 1000),
            xytext=(1990, 3.2), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(1979, 2031); ax.set_ylim(0, 7.5)
ax.set_ylabel("漁獲量（百万トン）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"遠洋漁業は{main['distant_peak_year']}年の{main['distant_pct_of_peak']:.0f}%に。海面漁業に占める割合は{main['distant_share_2024']:.0f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：海面漁業（養殖を除く）の部門別の漁獲量。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_sectors.png")

# ---- 図2：遠洋の中身 ------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.stackplot(sp.index, [sp.tuna3 / 1000, sp.other_distant / 1000], colors=[C[1], C[0]],
             labels=["カツオ・マグロの3漁法（はえ縄・一本釣・まき網）", "それ以外の遠洋（北洋の底びき網・いか釣など）"], edgecolor="#fcfcfb", linewidth=0.6)
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.set_xlim(1983, 2024); ax.set_ylim(0, 2.6)
ax.set_ylabel("遠洋漁業の漁獲量（百万トン）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"遠洋の減少はおもに北洋など。2024年は遠洋の{req['tuna3_share_2024_pct']:.0f}%がカツオ・マグロ", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：「それ以外」＝部門別の遠洋 − 種類別の遠洋かつお・まぐろ3漁法。まき網が統計に現れる1983年から。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig2_distant_split.png")

# ---- 図3：3漁法 -------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("longline_distant", "遠洋まぐろはえ縄", C[0]), ("polepole_distant", "遠洋かつお一本釣", C[2]), ("seine_distant", "遠洋かつお・まぐろまき網", C[1])]:
    x = s[col].dropna()
    ax.plot(x.index, x, color=c, lw=2.2)
    dy = {"longline_distant": 6, "polepole_distant": -6, "seine_distant": 0}[col]
    ax.text(2024.5, x.loc[2024] + dy, f"{lab} {x.loc[2024]:.0f}", va="center", fontsize=9, color=INK)
ax.set_xlim(1956, 2043); ax.set_ylim(0, 310)
ax.set_xticks(range(1960, 2025, 10))
ax.set_ylabel("漁獲量（千トン）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"はえ縄は最大の{main['longline_pct_of_peak']:.0f}%、一本釣は20%。まき網は最大の73%を保つ", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：遠洋かつお・まぐろまき網は1983年から、遠洋まぐろはえ縄は1971年から、遠洋かつお一本釣は1965年から統計に値がある。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_three_gears.png")

# ---- 図4：構成比 ------------------------------------------------------------------------------
yrs = [1985, 1990, 2000, 2010, 2024]
fig, ax = plt.subplots(figsize=(8.8, 4.2))
for i, y in enumerate(yrs):
    left = 0
    for col, c in [("longline_distant", C[0]), ("polepole_distant", C[2]), ("seine_distant", C[1])]:
        v = mix.loc[y, col]
        if pd.isna(v):
            continue
        ax.barh(i, v, left=left, color=c, height=0.6, edgecolor="#fcfcfb", linewidth=1.5)
        ax.text(left + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9, color="white" if c != C[2] else INK)
        left += v
ax.set_yticks(range(len(yrs))); ax.set_yticklabels([f"{y}年" for y in yrs]); ax.invert_yaxis()
ax.set_xlim(0, 100); ax.set_xlabel("遠洋のカツオ・マグロ3漁法に占める割合（%）")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C[0], label="はえ縄"), Patch(color=C[2], label="一本釣"), Patch(color=C[1], label="まき網")],
          loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=9)
ax.set_title(f"まき網の割合は{main['mix_1990']['seine_distant']:.0f}%（1990年）→{main['mix_2024']['seine_distant']:.0f}%（2024年）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：遠洋かつお・まぐろまき網の値がそろう年から。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.3)
save(fig, "fig4_mix.png")
print("ok")
