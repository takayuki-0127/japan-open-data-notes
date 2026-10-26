"""図を5枚つくる。"""
import json

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA, RES, FIG

d = pd.read_csv(DATA / "demand.csv")
c = pd.read_csv(DATA / "candidates.csv")
city = gpd.read_file(DATA / "city.geojson")
summ = pd.read_csv(RES / "summary.csv")
curve = pd.read_csv(RES / "curve_p.csv")
rob = pd.read_csv(RES / "robustness.csv")
sels = json.load(open(RES / "selected_sites.json", encoding="utf-8"))
mx = np.load(DATA / "matrix.npz")
st = (c["type"] == "station").values
cur = np.where(st)[0]
C_CUR, C_NEW, C_GRAY = "#1f5fa8", "#d1495b", "#9aa3ad"
LON0 = np.cos(np.radians(36.05))


def base(ax):
    city.boundary.plot(ax=ax, color="#555", lw=0.8)
    ax.set_aspect(1 / LON0)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")


# 1 人口と今の消防署
fig, ax = plt.subplots(figsize=(7.2, 6.4))
base(ax)
sc = ax.scatter(d.lon, d.lat, c=d["pop"], s=14, marker="s", cmap="YlOrBr", vmin=0, vmax=np.quantile(d["pop"], 0.97))
ax.scatter(c.lon[st], c.lat[st], s=60, c=C_CUR, marker="^", edgecolor="white", lw=0.8, label="今の消防署・分署（21か所）")
plt.colorbar(sc, ax=ax, shrink=0.7, label="500mメッシュの人口（人）")
ax.legend(loc="lower left", fontsize=9, frameon=True)
ax.set_title("福井市の人口（2020年、500mメッシュ）と消防署の場所", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f23_1_map_current.png", bbox_inches="tight"); plt.close(fig)

# 2 選び直した配置
fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.6))
for ax, key, title in [(axes[0], "全部を選び直す", "平均距離を最小にする（p-median）"),
                       (axes[1], "5分カバーを最大にする", "5分以内の人口を最大にする（最大カバー）")]:
    base(ax)
    ax.scatter(d.lon, d.lat, c=d["pop"], s=8, marker="s", cmap="Greys", vmin=0, vmax=np.quantile(d["pop"], 0.97), alpha=0.6)
    ax.scatter(c.lon[st], c.lat[st], s=55, facecolor="none", edgecolor=C_CUR, lw=1.4, marker="^", label="今の場所")
    s = np.array(sels[key])
    ax.scatter(c.lon.values[s], c.lat.values[s], s=45, c=C_NEW, marker="o", edgecolor="white", lw=0.6, label="選び直した場所")
    r = summ.set_index("案").loc[key]
    ax.set_title(f"{title}\n平均{r['平均道路距離_km']:.2f}km・5分以内{r['5分以内の割合']*100:.1f}%", fontsize=11)
    ax.legend(loc="lower left", fontsize=8.5)
fig.suptitle("同じ21か所でも、何を良くするかで選ぶ場所が変わる", fontsize=12.5)
fig.tight_layout(); fig.savefig(FIG / "f23_2_map_optimal.png", bbox_inches="tight"); plt.close(fig)

# 3 拠点数と平均距離
fig, ax1 = plt.subplots(figsize=(8, 4.8))
ax1.plot(curve["拠点数"], curve["平均道路距離_km"], "-o", color=C_NEW, label="平均道路距離（全部を選び直す）")
s0 = summ.set_index("案")
ax1.scatter([21], [s0.loc["今の配置", "平均道路距離_km"]], s=90, color=C_CUR, marker="^", zorder=5, label="今の配置（21か所）")
add = summ[summ["案"].str.startswith("今の配置＋")]
ax1.plot(add["拠点数"], add["平均道路距離_km"], "--s", color=C_CUR, label="今の配置に足していく")
ax1.set_xlabel("拠点の数"); ax1.set_ylabel("人口で重みづけた平均道路距離（km）")
ax1.grid(alpha=0.3)
ax2 = ax1.twinx()
ax2.plot(curve["拠点数"], curve["5分以内の割合_最大"] * 100, ":", color=C_GRAY, label="5分以内の人口の割合（最大カバー）")
ax2.set_ylabel("5分以内の割合（%）", color="#666"); ax2.set_ylim(60, 101)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="center right")
ax1.set_title("拠点を増やすと距離は縮むが、15か所を超えると縮み方は小さくなる", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f23_3_curve.png", bbox_inches="tight"); plt.close(fig)

# 4 案ごとの比較（平均距離と5分以内）
order = ["今の配置", "今の配置＋1か所", "今の配置＋3か所", "本署は固定・ほかを選び直す", "全部を選び直す", "5分カバーを最大にする"]
t = summ.set_index("案").loc[order]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
cols = [C_CUR, C_CUR, C_CUR, C_NEW, C_NEW, "#8a5a9e"]
axes[0].barh(range(len(t)), t["平均道路距離_km"], color=cols)
axes[0].set_yticks(range(len(t))); axes[0].set_yticklabels(order, fontsize=9); axes[0].invert_yaxis()
for i, v in enumerate(t["平均道路距離_km"]): axes[0].text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)
axes[0].set_xlabel("平均道路距離（km、人口で重みづけ）"); axes[0].set_xlim(0, t["平均道路距離_km"].max() * 1.2)
axes[1].barh(range(len(t)), t["5分以内の割合"] * 100, color=cols)
axes[1].set_yticks(range(len(t))); axes[1].set_yticklabels([]); axes[1].invert_yaxis()
for i, v in enumerate(t["5分以内の割合"] * 100): axes[1].text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=9)
axes[1].set_xlim(90, 100.8); axes[1].set_xlabel("道路で5分以内に届く人口の割合（%）")
fig.suptitle("平均距離を縮める配置は、遠い地区の5分以内の割合を下げる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f23_4_compare.png", bbox_inches="tight"); plt.close(fig)

# 5 頑健性
r = rob.copy()
fig, ax = plt.subplots(figsize=(8.6, 4.8))
y = np.arange(len(r))
ax.barh(y, r["平均道路距離_km"], color=[C_CUR if "今の配置" in s else C_NEW for s in r["案"]])
ax.set_yticks(y); ax.set_yticklabels(r["案"], fontsize=9); ax.invert_yaxis()
for i, v in enumerate(r["平均道路距離_km"]): ax.text(v + 0.02, i, f"{v:.2f}km", va="center", fontsize=8.5)
ax.set_xlim(0, r["平均道路距離_km"].max() * 1.22)
ax.set_xlabel("平均道路距離（km、各行の重みで計算）")
ax.set_title("解き方・重み・候補地を変えても、選び直すと平均距離は2割ほど縮む", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f23_5_robustness.png", bbox_inches="tight"); plt.close(fig)
print("figs done")
