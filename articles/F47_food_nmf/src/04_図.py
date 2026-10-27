"""図を作る"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from common import DATA, RAW, RES, FIG, CITIES, REGION

NAMES = {"P1": "P1 九州・沖縄型", "P2": "P2 関西・北陸型", "P3": "P3 果物・麺の内陸型",
         "P4": "P4 日本海の魚介型", "P5": "P5 かつお・しらすの太平洋型", "P6": "P6 東日本・大都市型"}
COL = {"P1": "#d95f02", "P2": "#7570b3", "P3": "#66a61e", "P4": "#1f78b4", "P5": "#e6ab02", "P6": "#888888"}
P = list(NAMES)
S = json.load(open(RES / "summary.json"))
share = pd.read_csv(RES / "W_city_share.csv", index_col=0, encoding="utf-8-sig")
H = pd.read_csv(RES / "H_item_weights.csv", index_col=0, encoding="utf-8-sig")
r = pd.read_csv(DATA / "ratio_2023_2025.csv", index_col=0, encoding="utf-8-sig")
r = r[~r.index.str.startswith("他の")]

# 図1：品目×都市の表（全国比のばらつきが大きい30品目）
X = r[CITIES]
sd = np.log(X).std(axis=1).sort_values(ascending=False)
top = sd.head(30).index
fig, ax = plt.subplots(figsize=(13, 7.6))
im = ax.imshow(np.log2(X.loc[top].values), cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
ax.set_yticks(range(len(top)), top, fontsize=8)
ax.set_xticks(range(len(CITIES)), [c.replace("東京都区部", "東京区部") for c in CITIES], rotation=90, fontsize=7.5)
pos = 0
for reg, cs in REGION[:-1]:
    pos += len(cs)
    ax.axvline(pos - 0.5, color="k", lw=0.6)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
cb.set_ticks([-2, -1, 0, 1, 2], labels=["1/4", "1/2", "全国並み", "2倍", "4倍"])
ax.set_title("全国との比（都市によって差の大きい30品目、2023〜25年平均、二人以上の世帯の支出金額）", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "f47_heatmap.png", dpi=150)
plt.close()

# 図2：パターンごとの代表品目（そのパターンが占める重みの割合）
share_items = H[P].div(H[P].sum(axis=1), axis=0)
fig, axes = plt.subplots(2, 3, figsize=(13, 7.4))
for ax, p, q in zip(axes.ravel(), P, S["patterns"]):
    it = q["top_items"][:8][::-1]
    ax.barh(range(len(it)), share_items.loc[it, p], color=COL[p])
    ax.set_yticks(range(len(it)), it, fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_title(NAMES[p] + f"（主な都市 {q['n_dominant']}）", fontsize=10)
    ax.tick_params(axis="x", labelsize=8)
for ax in axes[1]:
    ax.set_xlabel("その品目の重みのうち、このパターンが占める割合", fontsize=8.5)
fig.suptitle("NMFで取り出した6つの「好みのパターン」と、それぞれを特徴づける品目", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "f47_patterns.png", dpi=150)
plt.close()

# 図3：都市ごとのパターンの構成（北から順）
fig, ax = plt.subplots(figsize=(13, 5.6))
left = np.zeros(len(CITIES))
for p in P:
    v = share.loc[CITIES, p].values
    ax.bar(range(len(CITIES)), v, bottom=left, color=COL[p], label=NAMES[p], width=0.85)
    left += v
ax.set_xticks(range(len(CITIES)), [c.replace("東京都区部", "東京区部") for c in CITIES], rotation=90, fontsize=8)
ax.set_ylim(0, 1)
ax.set_ylabel("パターンの構成（合計=1）")
pos = 0
for reg, cs in REGION:
    ax.text(pos + len(cs) / 2 - 0.5, 1.02, reg, ha="center", fontsize=8.5)
    pos += len(cs)
    if pos < len(CITIES):
        ax.axvline(pos - 0.5, color="k", lw=0.8)
ax.legend(ncol=6, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.32), frameon=False)
ax.set_title("都市ごとの「好みのパターン」の組み合わせ", fontsize=11, pad=18)
fig.tight_layout()
fig.savefig(FIG / "f47_city_mix.png", dpi=150)
plt.close()

# 図4：地図（いちばん大きいパターンの色、点の大きさはその割合）
g = gpd.read_file(RAW / "N03-21_210101.json")
g = g.set_crs(4326, allow_override=True)
pref = g.dissolve("N03_001")
# 沖縄は右上へずらして表示（枠で囲む）
OK_DX, OK_DY = 8.0, 3.0
pref.loc["沖縄県", "geometry"] = pref.loc[["沖縄県"]].translate(OK_DX, OK_DY).iloc[0]
def city_geom(c):
    if c == "東京都区部":
        sel = g[(g.N03_001 == "東京都") & g.N03_007.str[:3].eq("131")]
    else:
        sel = g[(g.N03_003 == c) | (g.N03_004 == c)]
    return sel.to_crs(6677).union_all().centroid
pts = gpd.GeoSeries([city_geom(c) for c in CITIES], index=CITIES, crs=6677).to_crs(4326)
pts.loc["那覇市"] = gpd.GeoSeries([pts.loc["那覇市"]], crs=4326).translate(OK_DX, OK_DY).iloc[0]
fig, ax = plt.subplots(figsize=(9, 9))
pref.boundary.plot(ax=ax, color="#bbbbbb", lw=0.4)
pref.plot(ax=ax, color="#f4f4f4", zorder=0)
dom = share.loc[CITIES, "主なパターン"]
for p in P:
    idx = dom[dom == p].index
    if len(idx) == 0:
        continue
    ax.scatter(pts.loc[idx].x, pts.loc[idx].y, s=40 + 400 * share.loc[idx, p], color=COL[p],
               edgecolor="k", lw=0.4, label=NAMES[p], zorder=3)
ax.set_xlim(128.5, 146); ax.set_ylim(28.3, 45.7)
ax.plot([134.3, 137.0, 137.0, 134.3, 134.3], [28.5, 28.5, 30.4, 30.4, 28.5], color="#999", lw=0.6)
ax.set_axis_off()
ax.legend(fontsize=9, loc="upper left", frameon=False)
ax.set_title("いちばん大きいパターン（点の大きさはその割合）", fontsize=11)
ax.text(137.2, 28.6, "枠内は沖縄（位置をずらして表示）\n境界：国土数値情報（行政区域）を加工した簡略版", fontsize=7, color="#666")
fig.tight_layout()
fig.savefig(FIG / "f47_map.png", dpi=150)
plt.close()

# 図5：因子の数を変えたときの誤差と安定性
k = pd.read_csv(RES / "k_selection.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(k.k, k.err_nndsvda, "o-")
ax[0].set_xlabel("パターンの数 k"); ax[0].set_ylabel("相対誤差（小さいほどよく再現）")
ax[0].axvline(6, color="r", ls=":")
ax[0].set_title("パターンを増やすと誤差は少しずつ下がる", fontsize=10)
st = pd.read_csv(RES / "stability_seeds.csv")
c = st[[f"cos_{p}" for p in P]]
ax[1].boxplot([c[f"cos_{p}"] for p in P], tick_labels=P)
ax[1].set_ylabel("本体とのコサイン類似度")
ax[1].set_ylim(0.7, 1.01)
n_same = int((c.min(axis=1) > 0.99).sum())
ax[1].set_title(f"初期値20通り：{n_same}回は本体と同じ解（k=6）", fontsize=10)
fig.tight_layout()
fig.savefig(FIG / "f47_k_stability.png", dpi=150)
plt.close()

# 図6：10年前（2013〜15年平均）との比較（本体のパターンを固定して都市の構成を求めた）
ch = pd.read_csv(RES / "share_change_vs_2013_15.csv", index_col=0, encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
now = share.loc[CITIES, P]
old = now - ch.loc[CITIES, P]
for p in P:
    axes[0].scatter(old[p], now[p], s=14, color=COL[p], label=NAMES[p])
axes[0].plot([0, 0.8], [0, 0.8], "k:", lw=0.8)
axes[0].set_xlabel("2013〜15年平均の構成"); axes[0].set_ylabel("2023〜25年平均の構成")
axes[0].legend(fontsize=7, frameon=False)
axes[0].set_title("同じパターンで見た都市の構成は10年でほとんど変わらない", fontsize=10)
rb = pd.read_csv(RES / "robustness.csv")
rb = rb[rb.k == 6]
y = np.arange(len(rb))
axes[1].barh(y + 0.2, rb.cos_med, height=0.38, label="パターン（品目の重み）の類似度・中央値")
axes[1].barh(y - 0.2, rb.city_corr_med, height=0.38, label="都市の構成の相関・中央値")
axes[1].set_yticks(y, rb.name, fontsize=9)
axes[1].set_xlim(0, 1.05)
axes[1].legend(fontsize=7.5, loc="lower left")
axes[1].set_title("設定を変えて分解し直したとき（k=6）", fontsize=10)
fig.tight_layout()
fig.savefig(FIG / "f47_robust.png", dpi=150)
plt.close()
print("ok")
