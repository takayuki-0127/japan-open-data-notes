"""S1：県庁所在市ごとに「全国より何倍買っているか」（特化係数）と、食べ方の似た都市のグループ（階層クラスタリング）"""
from common import *
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster

d, lab = read("SSDSE-C-2026")
d = d.rename(columns={d.columns[0]: "code", d.columns[1]: "pref", d.columns[2]: "city"})
items = [c for c in d.columns if c.startswith("LB") and len(c) == 8]                 # 品目（大分類の合計は除く）
nat = d[d.code == "R00000"].iloc[0]
cities = d[d.code != "R00000"].set_index("city")
keep = [c for c in items if nat[c] >= 1000]                                            # 全国で年1,000円以上の品目だけ
LQ = cities[keep].astype(float) / nat[keep].astype(float).values                       # 特化係数（全国＝1）
LQ.columns = [lab[c] for c in keep]
LQ.round(3).to_csv(RES / "s1_lq.csv", encoding="utf-8-sig")
top = pd.DataFrame([{"city": c, "pref": cities.loc[c, "pref"], "item": LQ.loc[c].idxmax(), "lq": LQ.loc[c].max(),
                     "yen": cities.loc[c, keep[list(LQ.columns).index(LQ.loc[c].idxmax())]]} for c in LQ.index])
top.round(2).to_csv(RES / "s1_top_item.csv", index=False, encoding="utf-8-sig"); print(top.sort_values("lq", ascending=False).head(15))
item_top = pd.DataFrame([{"item": i, "city": LQ[i].idxmax(), "lq": LQ[i].max(), "spread": LQ[i].max() / LQ[i].min()} for i in LQ.columns])
item_top.sort_values("spread", ascending=False).round(2).to_csv(RES / "s1_item_spread.csv", index=False, encoding="utf-8-sig")

# 階層クラスタリング（Ward 法、特化係数の対数）
X = np.log(LQ.clip(lower=0.05))
Z = linkage(X.values, method="ward")
cl = fcluster(Z, 6, criterion="maxclust"); pd.Series(cl, index=X.index, name="cluster").to_csv(RES / "s1_clusters.csv", encoding="utf-8-sig")
s = {"cities": len(LQ), "items_used": len(keep), "items_total": len(items), "max_lq_city": top.loc[top.lq.idxmax(), "city"],
     "max_lq_item": top.loc[top.lq.idxmax(), "item"], "max_lq": top.lq.max()}
pd.Series(s).to_csv(RES / "s1_summary.csv", header=["value"]); print(pd.Series(s))

# 図1：各都市でいちばん特化している品目（上位20都市）
t = top.sort_values("lq").tail(20)
fig, ax = plt.subplots(figsize=(8, 6.2)); y = np.arange(len(t))
ax.barh(y, t.lq, color=BLUE, height=0.65)
for yi, (_, r) in zip(y, t.iterrows()):
    ax.text(r.lq + 0.1, yi, f"{r['item']}　{r.lq:.1f}倍", va="center", fontsize=9)
ax.set_yticks(y, t.city); ax.set_xlim(0, t.lq.max() * 1.45); ax.set_xlabel("全国平均の何倍買っているか（1世帯あたりの年間支出）")
ax.set_title("その街で「いちばん全国より多く買っている品目」（上位20都市）", loc="left")
fig.text(0.01, -0.03, source("SSDSE-家計消費（SSDSE-C-2026）") + "（家計調査 2023〜2025年平均、二人以上の世帯。全国で年1,000円以上の品目）", fontsize=7.5, color="#8a8984")
fig.savefig(FIG / "s1_top.png"); plt.close(fig)

# 図2：デンドログラム
fig, ax = plt.subplots(figsize=(9, 9))
dendrogram(Z, labels=list(X.index), orientation="left", color_threshold=Z[-6, 2], ax=ax, leaf_font_size=8.5, above_threshold_color=GRAY)
ax.set_xlabel("距離（Ward 法）"); ax.spines["left"].set_visible(False)
ax.set_title("食料の買い方が似ている都市（階層クラスタリング）", loc="left")
fig.text(0.01, 0.02, source("SSDSE-家計消費（SSDSE-C-2026）") + "（品目ごとの特化係数の対数）", fontsize=7.5, color="#8a8984")
fig.savefig(FIG / "s1_dendrogram.png"); plt.close(fig)
