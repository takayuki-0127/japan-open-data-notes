"""図を作る（figures/ に PNG で保存）"""
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from libpysal.weights import Queen
from libpysal.weights.spatial_lag import lag_spatial
from common import DATA, RES, FIG, CITIES, MIN_POP, setup_font

setup_font(); FIG.mkdir(exist_ok=True)
cities = list(CITIES)


def load(city, year):
    g = gpd.read_file(DATA / "units.gpkg", layer=city)
    l = pd.read_csv(RES / f"lisa_{city}_{year}.csv", dtype={"KEY": str})
    return g, g.merge(l, on="KEY")


# 図1 高齢化率の地図（2020年）
fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
for ax, c in zip(axes, cities):
    g, d = load(c, 2020)
    g.plot(ax=ax, color="#eeeeee", linewidth=0)
    d.plot(ax=ax, column="rate", cmap="YlOrRd", vmin=10, vmax=45, linewidth=0.05, edgecolor="white")
    ax.set_title(f"{c}（2020年）", fontsize=13); ax.set_axis_off()
sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(10, 45))
cb = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.04, pad=0.02, shrink=0.5)
cb.set_label("65歳以上の割合（%）。灰色は人口50人未満などで除いた区域")
fig.suptitle("町丁・字ごとの高齢化率", fontsize=15)
fig.savefig(FIG / "f06_map_rate2020.png", bbox_inches="tight"); plt.close(fig)

# 図2 Moran 散布図（2020年）と Moran's I の 2000→2020
mm = pd.read_csv(RES / "moran_main.csv")
fig, axes = plt.subplots(1, 4, figsize=(17, 4.4), gridspec_kw=dict(width_ratios=[1, 1, 1, 0.9]))
for ax, c in zip(axes, cities):
    g, d = load(c, 2020)
    w = Queen.from_dataframe(d, use_index=False, silence_warnings=True); w.transform = "r"
    z = (d["rate"] - d["rate"].mean()) / d["rate"].std()
    lz = lag_spatial(w, z.values)
    ax.scatter(z, lz, s=4, alpha=0.35, color="#c0504d")
    b = np.polyfit(z, lz, 1); xs = np.linspace(z.min(), z.max(), 10); ax.plot(xs, b[0] * xs + b[1], color="black", lw=1)
    ax.axhline(0, color="grey", lw=0.6); ax.axvline(0, color="grey", lw=0.6)
    I = mm[(mm.city == c) & (mm.year == 2020)].I.iloc[0]
    ax.set_title(f"{c}  Moran's I = {I:.2f}", fontsize=12)
    ax.set_xlabel("その区域の高齢化率（標準化）"); ax.set_ylabel("隣の区域の平均（標準化）")
    ax.set_xlim(-3, 5); ax.set_ylim(-2.5, 3.5)
ax = axes[3]
x = np.arange(3)
for i, (y, col) in enumerate([(2000, "#9bbbd9"), (2020, "#1f4e79")]):
    v = [mm[(mm.city == c) & (mm.year == y)].I.iloc[0] for c in cities]
    ax.bar(x + (i - 0.5) * 0.38, v, width=0.38, color=col, label=f"{y}年")
    for xi, vi in zip(x, v): ax.text(xi + (i - 0.5) * 0.38, vi + 0.01, f"{vi:.2f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(cities); ax.set_ylim(0, 0.5); ax.legend(frameon=False)
ax.set_title("Moran's I（2000年→2020年）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f06_moran.png", bbox_inches="tight"); plt.close(fig)

# 図3 LISA の塊（2020年）
colors = {"高高": "#d7191c", "低低": "#2c7bb6", "高低": "#fdae61", "低高": "#abd9e9", "該当なし": "#f0f0f0"}
fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
for ax, c in zip(axes, cities):
    g, d = load(c, 2020)
    g.plot(ax=ax, color="#dddddd", linewidth=0)
    for k, col in colors.items():
        s = d[d.lisa == k]
        if len(s): s.plot(ax=ax, color=col, linewidth=0.05, edgecolor="white")
    ax.set_title(f"{c}（2020年）", fontsize=13); ax.set_axis_off()
fig.legend(handles=[Patch(color=v, label=k) for k, v in colors.items()], loc="lower center", ncol=5, frameon=False,
           title="LISA（並べ替え999回、p<0.05）高高＝高齢化率が高い区域が高い区域に囲まれている")
fig.suptitle("高齢化の「塊」：LISA クラスタ", fontsize=15)
fig.savefig(FIG / "f06_lisa2020.png", bbox_inches="tight"); plt.close(fig)

# 図4 2000→2020 の高高の移り変わり
cat_col = {"両方の年で高高": "#7b3294", "2020年に新しく高高": "#d7191c", "2000年だけ高高": "#80cdc1"}
fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
for ax, c in zip(axes, cities):
    g = gpd.read_file(DATA / "units.gpkg", layer=c)
    a = pd.read_csv(RES / f"lisa_{c}_2000.csv", dtype={"KEY": str})[["KEY", "lisa"]]
    b = pd.read_csv(RES / f"lisa_{c}_2020.csv", dtype={"KEY": str})[["KEY", "lisa"]]
    m = g.merge(a, on="KEY", how="left").merge(b, on="KEY", how="left", suffixes=("_00", "_20"))
    m["cat"] = np.select([(m.lisa_00 == "高高") & (m.lisa_20 == "高高"), (m.lisa_20 == "高高"), (m.lisa_00 == "高高")],
                         list(cat_col), default="")
    m.plot(ax=ax, color="#eeeeee", linewidth=0)
    for k, col in cat_col.items():
        s = m[m.cat == k]
        if len(s): s.plot(ax=ax, color=col, linewidth=0)
    cfg = CITIES[c]
    p = gpd.GeoSeries(gpd.points_from_xy([cfg["center"][0]], [cfg["center"][1]]), crs=4612).to_crs(cfg["epsg"])
    p.plot(ax=ax, color="black", marker="*", markersize=120)
    ax.set_title(c, fontsize=13); ax.set_axis_off()
fig.legend(handles=[Patch(color=v, label=k) for k, v in cat_col.items()] + [plt.Line2D([], [], color="black", marker="*", ls="", ms=12, label="市役所")],
           loc="lower center", ncol=4, frameon=False)
fig.suptitle("高齢化の塊（高高）は20年でどこへ動いたか（2000年は2020年の境界に面積按分）", fontsize=14)
fig.savefig(FIG / "f06_hh_change.png", bbox_inches="tight"); plt.close(fig)

# 図5 都心からの距離と高齢化率
dr = pd.read_csv(RES / "rate_by_distance.csv")
fig, axes = plt.subplots(1, 3, figsize=(15, 4.3), sharey=True)
for ax, c in zip(axes, cities):
    for y, col in [(2000, "#9bbbd9"), (2020, "#1f4e79")]:
        s = dr[(dr.city == c) & (dr.year == y) & (dr.n >= 10)]
        ax.plot(s.km, s.rate, marker="o", color=col, label=f"{y}年")
    ax.set_title(c, fontsize=13); ax.set_xlabel("市役所からの距離（km、帯の下端）"); ax.grid(alpha=0.3)
axes[0].set_ylabel("65歳以上の割合（%、人口で重み付け）"); axes[0].legend(frameon=False)
fig.suptitle("都心からの距離と高齢化率", fontsize=14); fig.tight_layout()
fig.savefig(FIG / "f06_distance.png", bbox_inches="tight"); plt.close(fig)
print("ok")
