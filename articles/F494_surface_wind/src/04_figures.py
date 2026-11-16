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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.unicode_minus": False})
C = {"rural": "#2a78d6", "city": "#eb6834", "cold": "#1baf7a"}
GL = {"rural": "15地点", "city": "大都市", "cold": "寒い地域"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：気象庁「過去の気象データ検索」（年ごとの値・風）をもとに作成者が加工して作成"
META = {"Software": None}


def mi(v, fmt):
    return format(v, fmt).replace("-", "−")


def yt(ax, ticks):
    ax.set_yticks(ticks); ax.set_yticklabels([mi(t, "g") for t in ticks])


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
yr = pd.read_csv(R / "requestion_yearly.csv", index_col=0)
T = pd.read_csv(R / "station_table.csv")
S = pd.read_csv(R / "steps.csv")

# ---- 図1：32地点の年平均風速（地点の平均からの差の中央値） --------------------------------------------
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.plot(yr.index, yr["anom"], color=INK2, lw=1.6, label="そのまま（地点の全期間の平均からの差）")
ax.plot(yr.index, yr["anom_seg"], color="#2a78d6", lw=1.6, label="切れ目ごとの区間の平均からの差")
ax.axhline(0, color=INK2, lw=0.6)
ax.set_ylim(-0.6, 0.6); yt(ax, [-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6])
ax.set_ylabel("年平均風速の差（m/s、32地点の中央値）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title("年平均風速：そのままだと1975〜1982年に大きく下がって見える（32地点）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig1_yearly.png")

# ---- 図2：地点ごとの傾き（そのまま と 段差を許す）。北から南の順 -------------------------------------
fig, ax = plt.subplots(figsize=(8, 9.5))
y = np.arange(len(T))[::-1]
for i, r in T.iterrows():
    ax.plot([r["naive"], r["fe"]], [y[i], y[i]], color=GRID, lw=2, zorder=1)
ax.scatter(T["naive"], y, color="white", edgecolor=INK2, s=36, zorder=2, label="そのまま（Theil–Sen）")
ax.scatter(T["fe"], y, c=[C[g] for g in T["group"]], s=40, zorder=3, label="段差を許した傾き")
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(y); ax.set_yticklabels([f"{s}（{GL[g]}）" for s, g in zip(T["station"], T["group"])], fontsize=8.5)
ax.set_xlim(-0.45, 0.25); ax.set_xticks([-0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2])
ax.set_xticklabels([mi(t, "g") for t in [-0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2]])
ax.set_xlabel("年平均風速の傾き（m/s、10年あたり）")
ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("地点ごとの傾き（1961〜2025年、北から南の順）", fontsize=10.5, loc="left")
fig.text(0.01, 0.005, SRC + "。色は区分（青＝15地点、橙＝大都市、緑＝寒い地域）", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.015, 1, 1))
save(fig, "fig2_station_slopes.png")

# ---- 図3：切れ目での段差 ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.scatter(S["year"], S["step"], c=[C[g] for g in S["group"]], s=30, edgecolor="white", lw=0.5)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylim(-2.2, 2.2); yt(ax, [-2, -1, 0, 1, 2])
ax.set_xlabel("切れ目の年"); ax.set_ylabel("切れ目の後5年 − 前5年（m/s）")
for g in ("rural", "city", "cold"):
    ax.scatter([], [], c=C[g], s=30, label=GL[g])
ax.legend(frameon=False, loc="upper right", fontsize=9)
rq = json.load(open(R / "requestion.json", encoding="utf-8"))
p0 = rq["by_period"]["1961〜1975年"]
ax.text(1963, 1.9, f"1961〜1975年の切れ目：{p0['n']}か所のうち{p0['down']}か所で下がった", fontsize=9, color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("表の切れ目（赤い線）の前後での年平均風速の段差", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig3_steps.png")

# ---- 図4：区分ごとの中央値 -------------------------------------------------------------------------
bg = main["by_group"]
names = ["15地点", "大都市", "寒い地域"]
fig, ax = plt.subplots(figsize=(7.4, 4.4))
x = np.arange(3); w = 0.36
v1 = [bg[n]["naive"] for n in names]; v2 = [bg[n]["fe"] for n in names]
ax.bar(x - w / 2, v1, width=w, color=GRID, edgecolor=INK2, label="そのまま（Theil–Sen）")
ax.bar(x + w / 2, v2, width=w, color=[C["rural"], C["city"], C["cold"]], label="段差を許した傾き")
for xi, v in zip(x + w / 2, v2):
    ax.text(xi, v + (0.004 if v >= 0 else -0.004), mi(v, "+.3f"), ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{n}（{main['by_group_n'][n]}）" for n in names])
ax.set_ylim(-0.08, 0.1); yt(ax, [-0.08, -0.04, 0, 0.04, 0.08])
ax.set_ylabel("傾きの中央値（m/s、10年あたり）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("区分ごとの傾きの中央値（そのままの傾きはどれもほぼ0）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC, fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig4_groups.png")
print("figures done")
