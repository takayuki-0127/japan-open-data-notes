"""図を作る。"""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from common import RAW, RES, FIG, DATA

FIG.mkdir(exist_ok=True)
NAMES = {1: "1 都市", 2: "2 ものづくりの町", 3: "3 地方の中小の市と町", 4: "4 高齢化が進んだ小さな町村", 5: "5 観光・一次産業の小さな町"}
COL = {1: "#3b6fb6", 2: "#e08a2c", 3: "#5aa36b", 4: "#8e6bb8", 5: "#d1495b"}
cl = pd.read_csv(RES / "clusters.csv")

# 図1 主成分の負荷量
load = pd.read_csv(RES / "pca_loadings.csv", index_col=0)
var = pd.read_csv(RES / "pca_variance.csv")
fig, axes = plt.subplots(1, 3, figsize=(15, 6.2))
for i, ax in enumerate(axes):
    s = load[f"PC{i+1}"]
    top = pd.concat([s.nsmallest(6), s.nlargest(6)]).sort_values()
    ax.barh(range(len(top)), top.values, color=["#9aa5b1" if v < 0 else "#3b6fb6" for v in top.values])
    ax.set_yticks(range(len(top))); ax.set_yticklabels(top.index, fontsize=9)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_title(f"第{i+1}主成分（全体のばらつきの{var.ratio[i]*100:.1f}%）", fontsize=11)
fig.suptitle("主成分の負荷量：絶対値の大きい指標（＋側と−側の6つずつ）", fontsize=13)
fig.tight_layout(); fig.savefig(FIG / "f08_loadings.png", dpi=150); plt.close()

# 図2 クラスタ数の決め方
ks = pd.read_csv(RES / "k_selection.csv"); st = pd.read_csv(RES / "k_stability.csv")
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
axes[0].plot(ks.k, ks.silhouette, "o-", color="#3b6fb6"); axes[0].set_title("シルエット係数（k-means、大きいほど良い）")
axes[1].plot(ks.k, ks.gmm_bic, "o-", color="#e08a2c"); axes[1].set_title("BIC（ガウス混合、小さいほど良い）")
axes[2].plot(st.k, st.ari_mean, "o-", color="#5aa36b")
axes[2].fill_between(st.k, st.ari_p10, st.ari_p90, color="#5aa36b", alpha=0.2)
axes[2].set_title("ブートストラップ安定性（ARI、10〜90%点）")
for ax in axes:
    ax.axvline(5, color="gray", ls="--", lw=1); ax.set_xlabel("組の数 k"); ax.set_xticks(range(2, 13))
fig.suptitle("組の数をいくつにするか（点線が採用した k=5）", fontsize=13)
fig.tight_layout(); fig.savefig(FIG / "f08_k_selection.png", dpi=150); plt.close()

# 図3 UMAP
fig, ax = plt.subplots(figsize=(8.5, 7))
for c in range(1, 6):
    s = cl[cl.cluster == c]
    ax.scatter(s.umap1, s.umap2, s=np.clip(np.sqrt(s["pop"]) / 15, 3, 120), c=COL[c], alpha=0.65,
               label=f"{NAMES[c]}（{len(s)}）", edgecolors="none")
low = cl[cl.stability < 0.6]
ax.scatter(low.umap1, low.umap2, s=6, facecolors="none", edgecolors="k", lw=0.4, label="安定性0.6未満（境界の町）")
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("1,740市区町村を2次元に縮めた図（UMAP、円の大きさは人口）", fontsize=12)
ax.legend(fontsize=9, loc="best", markerscale=0.8)
fig.tight_layout(); fig.savefig(FIG / "f08_umap.png", dpi=150); plt.close()

# 図4 プロフィール
pz = pd.read_csv(RES / "profile_z.csv", index_col=0)
rows = ["人口（対数）", "可住地の人口密度（対数）", "15歳未満の割合", "65歳以上の割合", "単独世帯の割合", "純移動率",
        "女性の就業率", "第1次産業就業者の割合", "従業者の割合：製造業", "従業者の割合：宿泊・飲食業",
        "従業者の割合：医療・福祉", "外国人の割合（対数）", "地方税/歳入", "1人あたり歳出（対数）", "一般病院/人口（対数）", "飲食店/人口（対数）"]
m = pz.loc[rows]
m.columns = [NAMES[i + 1] for i in range(5)]
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(m.values, cmap="RdBu_r", vmin=-1.6, vmax=1.6, aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels(m.columns, fontsize=10, rotation=15)
ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=10)
for i in range(m.shape[0]):
    for j in range(5):
        ax.text(j, i, f"{m.values[i, j]:+.1f}", ha="center", va="center", fontsize=8.5)
fig.colorbar(im, ax=ax, shrink=0.7, label="全国の平均との差（標準偏差の単位）")
ax.set_title("5つのタイプの特徴（指標を標準化した値の平均）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f08_profile.png", dpi=150); plt.close()

# 図5 地図
g = gpd.read_file(RAW / "N03-21_210101.json")
g["code5"] = g["N03_007"].astype(str).str.zfill(5)
g = g[g["N03_007"].notna()]
cl["code5"] = cl["code"].str[1:]
cl["key"] = (cl["pref"] + cl["name"]).str.replace("檮", "梼")
codes = set(cl.code5)
# 政令市の区は市にまとめる（N03_003 が市名、N03_004 が区名）
is_ward = g["N03_004"].fillna("").str.endswith("区") & g["N03_003"].fillna("").str.endswith("市")
g["key"] = np.where(is_ward, g["N03_001"] + g["N03_003"].fillna(""), g["N03_001"] + g["N03_004"].fillna(""))
g["key"] = g["key"].str.replace("檮", "梼")
g = g.dissolve(by="key", as_index=False)
gm = g.merge(cl[["key", "cluster"]], on="key", how="left")
print("地図で結べなかった市区町村:", cl.loc[~cl.key.isin(g.key), "key"].tolist()[:10], (~cl.key.isin(g.key)).sum())
fig, ax = plt.subplots(figsize=(10, 10))
gm[gm.cluster.isna()].plot(ax=ax, color="#eeeeee", lw=0)
for c in range(1, 6):
    gm[gm.cluster == c].plot(ax=ax, color=COL[c], lw=0.05, edgecolor="white")
ax.set_xlim(128.5, 146.2); ax.set_ylim(30.5, 45.7); ax.set_axis_off()
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=COL[c], label=NAMES[c]) for c in range(1, 6)], loc="lower right", fontsize=10)
ax.set_title("市区町村の5つのタイプ（沖縄・小笠原などの離島は範囲外）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f08_map.png", dpi=150); plt.close()

# 図6 頑健性
rob = pd.read_csv(RES / "robustness_ari.csv")
fig, ax = plt.subplots(figsize=(9, 5))
cols = ["#e08a2c" if i < 4 else "#3b6fb6" for i in range(len(rob))]
ax.barh(range(len(rob))[::-1], rob.ARI, color=cols)
ax.set_yticks(range(len(rob))[::-1]); ax.set_yticklabels(rob["比べたもの"], fontsize=10)
for i, v in enumerate(rob.ARI):
    ax.text(v + 0.01, len(rob) - 1 - i, f"{v:.2f}", va="center", fontsize=9)
ax.set_xlim(0, 1.05); ax.set_xlabel("基準の分類との一致度（ARI、1で完全に一致）")
ax.set_title("手法（橙）や指標（青）を変えると、分類はどれだけ変わるか", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f08_robustness.png", dpi=150); plt.close()
print("ok")
