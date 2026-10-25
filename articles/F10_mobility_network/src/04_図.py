"""図を作る。"""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from common import DATA, RES, FIG, RAW

FIG.mkdir(exist_ok=True)
PAL = ["#2f6f9f", "#e07b39", "#3a9a5b", "#c0504d", "#8064a2", "#4bacc6", "#9b7b3a", "#d16fa8", "#7f7f7f", "#b5b83b", "#5c5c99", "#2ca089"]
pref = gpd.read_file(DATA / "pref.geojson").set_index("N03_001")
xy = pd.read_csv(DATA / "pref_xy.csv").set_index("pref")
memb = pd.read_csv(RES / "membership_pref.csv", index_col=0)
PREF = list(memb.index)
cen = pd.read_csv(RES / "centrality.csv")

def okinawa_shift(gdf):
    # 沖縄を左上に寄せて表示
    g = gdf.copy()
    m = g.index == "沖縄県"
    g.loc[m, "geometry"] = g.loc[m, "geometry"].translate(xoff=5.5, yoff=15.5)
    return g

def recolor(m):
    # 北から順に色を割り当てる（色の対応を図どうしでそろえる）
    order = []
    for p in PREF:
        if m[p] not in order:
            order.append(m[p])
    return {p: PAL[order.index(m[p]) % len(PAL)] for p in PREF}

def draw_map(ax, col, title):
    g = okinawa_shift(pref)
    m = memb[col]
    cmap = recolor(m)
    g.plot(ax=ax, color=[cmap[p] for p in g.index], edgecolor="white", linewidth=0.4)
    ax.plot([131.6, 135.2, 135.2], [40.9, 40.9, 43.0], color="#999", lw=0.6)
    ax.text(133.4, 43.1, "沖縄", fontsize=7, color="#777", ha="center")
    ax.set_xlim(128.5, 146.2); ax.set_ylim(30.5, 45.8); ax.set_axis_off()
    ax.set_title(title, fontsize=11)

# 図1：2025年の移動ネットワーク
fig, ax = plt.subplots(figsize=(8.2, 8.2))
g = okinawa_shift(pref)
m = memb["2025_count_1.0"]; cmap = recolor(m)
g.plot(ax=ax, color=[cmap[p] for p in g.index], alpha=0.18, edgecolor="#bbb", linewidth=0.4)
M = pd.read_csv(DATA / "migration_2025.csv", index_col=0).values
A = M + M.T
pxy = xy.copy(); pxy.loc["沖縄県", "lon"] += 5.5; pxy.loc["沖縄県", "lat"] += 15.5
iu = np.triu_indices(47, 1)
vals = A[iu]; order = np.argsort(vals)[::-1][:70]
segs, ws = [], []
for k in order:
    i, j = iu[0][k], iu[1][k]
    segs.append([(pxy.iloc[i].lon, pxy.iloc[i].lat), (pxy.iloc[j].lon, pxy.iloc[j].lat)]); ws.append(vals[k])
ws = np.array(ws)
ax.add_collection(LineCollection(segs, linewidths=0.4 + 5 * ws / ws.max(), colors="#333", alpha=0.45))
pr = cen[cen.year == 2025].set_index("pref")["pagerank"]
ax.scatter(pxy.lon, pxy.lat, s=3000 * pr.reindex(PREF).values, c=[cmap[p] for p in PREF], edgecolor="white", linewidth=0.8, zorder=3)
for p in ["東京都", "大阪府", "愛知県", "福岡県", "宮城県", "北海道", "広島県"]:
    ax.annotate(p.replace("都", "").replace("府", "").replace("県", ""), (pxy.loc[p].lon, pxy.loc[p].lat), xytext=(6, 6), textcoords="offset points", fontsize=9)
ax.plot([131.6, 135.2, 135.2], [40.9, 40.9, 43.0], color="#999", lw=0.6)
ax.set_xlim(128.5, 146.2); ax.set_ylim(30.5, 45.8); ax.set_axis_off()
ax.set_title("都道府県間の移動（2025年、日本人）：太い線ほど行き来が多い\n点の大きさ＝PageRank、色＝コミュニティ（解像度1）", fontsize=11)
fig.text(0.02, 0.02, "行き来（両方向の合計）の上位70組を表示。出典：総務省「住民基本台帳人口移動報告」", fontsize=7.5, color="#555")
fig.savefig(FIG / "f10_network_2025.png", bbox_inches="tight"); plt.close(fig)

# 図2：解像度を変えたコミュニティ（2025年）
fig, axes = plt.subplots(2, 2, figsize=(10, 10))
axes = axes.ravel()
for ax, r in zip(axes, ["0.75", "1.0", "1.5", "2.0"]):
    k = memb[f"2025_count_{r}"].nunique()
    draw_map(ax, f"2025_count_{r}", f"解像度 {r}：{k}つ")
fig.suptitle("解像度（どこまで細かく分けるか）を変えると、圏の数は2→4→8→9に（2025年）", fontsize=12)
fig.savefig(FIG / "f10_resolution_maps.png", bbox_inches="tight"); plt.close(fig)

# 図3：中心性（PageRank）1990→2025
a = cen[cen.year == 1990].set_index("pref")["pagerank"]; b = cen[cen.year == 2025].set_index("pref")["pagerank"]
top = b.sort_values(ascending=False).head(12).index[::-1]
fig, ax = plt.subplots(figsize=(7.2, 5.4))
for i, p in enumerate(top):
    ax.plot([a[p], b[p]], [i, i], color="#bbb", lw=2, zorder=1)
ax.scatter(a[top], range(len(top)), color="#999", label="1990年", zorder=2)
ax.scatter(b[top], range(len(top)), color="#c0504d", label="2025年", zorder=3)
ax.set_yticks(range(len(top))); ax.set_yticklabels(top)
ax.set_xlabel("PageRank（移動の流れでみた「集まる先」としての重要度）")
for i, p in enumerate(top):
    ax.text(max(a[p], b[p]) + 0.002, i, f"{a[p]:.3f}→{b[p]:.3f}", va="center", fontsize=8, color="#444")
ax.set_xlim(0, 0.2)
ax.legend(loc="lower right", frameon=False)
ax.set_title("流れの中心は東京で、30年でさらに強まった", fontsize=11)
fig.savefig(FIG / "f10_pagerank.png", bbox_inches="tight"); plt.close(fig)

# 図4：1都3県の通勤のまとまり
nodes = pd.read_csv(RES / "commute_nodes.csv", dtype={"code": str}).set_index("code")
mg = gpd.read_file(RAW / "N03-21_210101.json")
mg = mg[mg["N03_007"].notna()]
mg["code"] = mg["N03_007"].astype(str).str.zfill(5)
mg = mg[mg["code"].isin(nodes.index)].dissolve(by="code")
mg = mg.join(nodes)
order = []
for c in nodes.sort_values("pagerank", ascending=False)["comm_1.0"]:
    if c not in order: order.append(c)
fig, ax = plt.subplots(figsize=(8.4, 7.4))
mg.plot(ax=ax, color=[PAL[order.index(c) % len(PAL)] for c in mg["comm_1.0"]], edgecolor="white", linewidth=0.25)
pb = pref.loc[["埼玉県", "千葉県", "東京都", "神奈川県"]]
pb.boundary.plot(ax=ax, color="#222", linewidth=1.0)
summ = pd.read_csv(RES / "commute_communities_r1.csv")
for c in order:
    sub = nodes[nodes["comm_1.0"] == c].sort_values("in_commuters", ascending=False)
    k = sub.index[0]
    if k in mg.index:
        pt = mg.loc[k].geometry.representative_point()
        off = {"新宿区": (-45, 25), "千代田区": (40, 30), "港区": (-40, -25)}.get(sub["name"].iloc[0], (0, 0))
        ax.annotate(sub["name"].iloc[0], (pt.x, pt.y), xytext=off, textcoords="offset points", fontsize=8.5, ha="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="-", color="#222", lw=0.6) if off != (0, 0) else None)
ax.set_xlim(138.9, 140.9); ax.set_ylim(34.9, 36.3); ax.set_axis_off()
ax.set_title("通勤で分けた1都3県（2020年、市区町村）：6つのまとまり（解像度1）\n黒線は都県境。まとまりは都県境をまたいでいる", fontsize=11)
fig.text(0.02, 0.02, "ラベル＝そのまとまりで通勤の流入がいちばん多い市区町村。島しょ部は表示外。出典：総務省「令和2年国勢調査」従業地・通学地集計", fontsize=7.5, color="#555")
fig.savefig(FIG / "f10_commute_map.png", bbox_inches="tight"); plt.close(fig)

# 図5：1990年と2025年の比較
fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
draw_map(axes[0], "1990_count_1.0", "1990年（解像度1）：4つ")
draw_map(axes[1], "2025_count_1.0", "2025年（解像度1）：4つ")
for ax, col in zip(axes, ["1990_count_1.0", "2025_count_1.0"]):
    for p in ["静岡県", "山口県"]:
        pt = pref.loc[p].geometry.representative_point()
        ax.annotate(p, (pt.x, pt.y), xytext=(0, -22), textcoords="offset points", ha="center", fontsize=9,
                    arrowprops=dict(arrowstyle="-", color="#333", lw=0.6))
fig.suptitle("30年で入れ替わったのは2県だけ：静岡は「東」から「中部」へ、山口は「中国・四国」から「九州」へ", fontsize=12)
fig.savefig(FIG / "f10_1990_2025.png", bbox_inches="tight"); plt.close(fig)

# 図6：頑健性
grid = pd.read_csv(RES / "community_grid.csv"); blk = pd.read_csv(RES / "vs_regional_blocks.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for y, c in zip(["1990", "2000", "2010", "2025"], ["#999", "#4bacc6", "#2f6f9f", "#c0504d"]):
    s = grid[(grid.year == int(y)) & (grid.norm == "count")]
    axes[0].plot(s.resolution, s.n_comm, marker="o", color=c, label=f"{y}年")
    b = blk[blk.year == int(y)]
    axes[1].plot(b.res, b.NMI_vs_8blocks, marker="o", color=c, label=f"{y}年")
s = grid[(grid.year == 2025) & (grid.norm == "lift")]
axes[0].plot(s.resolution, s.n_comm, ls="--", color="#c0504d", label="2025年（期待値との比）")
axes[0].set_xlabel("解像度"); axes[0].set_ylabel("コミュニティの数"); axes[0].legend(frameon=False, fontsize=8)
axes[0].set_title("解像度ごとの圏の数：どの年もほぼ同じ", fontsize=11)
axes[1].set_xlabel("解像度"); axes[1].set_ylabel("8地方区分との一致（NMI）"); axes[1].set_ylim(0, 1)
axes[1].set_title("解像度1.5前後で、教科書の8地方区分に近づく", fontsize=11)
fig.savefig(FIG / "f10_robustness.png", bbox_inches="tight"); plt.close(fig)
print("figs ok")
