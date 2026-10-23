"""C1：市区町村をクラスタリング（k-means）すると、どんなグループに分かれるか"""
from common import *
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.decomposition import PCA

d = load_extra()
d["foreign_log"] = np.log(d.A1700 / d.A1101 * 100 + 0.1)
d["daynight_log"] = np.log(d.A6107 / d.A1101)
d["child"] = d.A1405 / d.A1101
COLS = {"log_inc": "所得（対数）", "old": "65歳以上の割合", "child": "0〜5歳の割合", "univ": "大卒の割合", "log_density": "人口密度（対数）",
        "mfg": "第2次産業の割合", "primary": "第1次産業の割合", "single": "単独世帯の割合", "foreign_log": "外国人の割合（対数）", "daynight_log": "昼夜間人口比（対数）"}
Z = d[list(COLS)].apply(lambda s: s.clip(s.quantile(.01), s.quantile(.99)))   # 外れ値（上下1%）を丸める
X = StandardScaler().fit_transform(Z)

sil = pd.DataFrame([{"k": k, "silhouette": silhouette_score(X, KMeans(k, n_init=20, random_state=0).fit_predict(X))} for k in range(2, 10)])
sil.round(3).to_csv(RES / "c1_silhouette.csv", index=False); print(sil.round(3))
K = 5
km = KMeans(K, n_init=50, random_state=0).fit(X); d["cl"] = km.labels_
ari = [adjusted_rand_score(km.labels_, KMeans(K, n_init=10, random_state=s).fit_predict(X)) for s in range(1, 11)]
# グループの名前は中身（中央値）を見て付ける
prof = pd.DataFrame(X, columns=list(COLS)).groupby(d["cl"].values).median()
med = d.groupby("cl").agg(n=("inc", "size"), pop_median=("A1101", "median"), inc=("inc", "median"), old=("old", "median"), univ=("univ", "median"),
                          mfg=("mfg", "median"), primary=("primary", "median"), single=("single", "median"))
order = med.sort_values("univ", ascending=False).index.tolist()
names = {}
for c in med.index:
    m = med.loc[c]
    if m.univ >= med.univ.max() - 1e-9: names[c] = "大都市と近郊"
    elif m.primary >= med.primary.max() - 1e-9: names[c] = "農林漁業の町村"
    elif m.old >= med.old.max() - 1e-9: names[c] = "高齢化が進んだ市町"
    elif m.mfg >= med.mfg.max() - 1e-9: names[c] = "郊外・工業のある都市"
    else: names[c] = "家族世帯が多い地方の市町"
d["group"] = d.cl.map(names); med["name"] = med.index.map(names)
med["examples"] = [ "・".join(d[d.cl == c].nlargest(4, "A1101")["name"]) for c in med.index]
med.round(3).to_csv(RES / "c1_groups.csv", encoding="utf-8-sig"); print(med.round(3))
d[["code", "pref_name", "name", "group"]].to_csv(RES / "c1_assignments.csv", index=False, encoding="utf-8-sig")
s = {"n": len(d), "k": K, "silhouette_k": sil.set_index("k").loc[K, "silhouette"], "silhouette_best_k": int(sil.loc[sil.silhouette.idxmax(), "k"]),
     "silhouette_best": sil.silhouette.max(), "ari_seed_min": min(ari), "ari_seed_median": float(np.median(ari))}
pca = PCA(2).fit(X); P = pca.transform(X); s["pca_var_explained"] = pca.explained_variance_ratio_.sum()
pd.Series(s).round(3).to_csv(RES / "c1_summary.csv", header=["value"]); print(pd.Series(s).round(3))
pref = pd.crosstab(d.pref_name, d.group, normalize="index").round(3); pref.to_csv(RES / "c1_pref_share.csv", encoding="utf-8-sig")

PAL = {"大都市と近郊": BLUE, "郊外・工業のある都市": "#7a5bd6", "家族世帯が多い地方の市町": "#3aa07a", "高齢化が進んだ市町": ORANGE, "農林漁業の町村": "#c9a227"}
gorder = [names[c] for c in order]
# 図1：PCA の平面に色分け
fig, ax = plt.subplots(figsize=(8, 5.4))
for g in gorder:
    m = d.group == g; ax.scatter(P[m, 0], P[m, 1], s=8, color=PAL[g], alpha=0.65, lw=0, label=f"{g}（{m.sum()}）")
for n in ["横浜市", "千代田区", "大泉町", "川上村", "夕張市", "豊田市"]:
    i = d.index[d["name"] == n][0]; ax.annotate(n, (P[i, 0], P[i, 1]), xytext=(4, 3), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_xlabel(f"第1主成分（都市か地方か。{pca.explained_variance_ratio_[0] * 100:.0f}%）"); ax.set_ylabel(f"第2主成分（{pca.explained_variance_ratio_[1] * 100:.0f}%）")
ax.legend(frameon=False, fontsize=8.5, loc="upper right", markerscale=2)
ax.set_title("1,740市区町村を5つのグループに分けた（k-means）", loc="left")
fig.text(0.01, -0.03, SOURCE + "（10の指標を標準化。上下1%は丸めた）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "c1_pca.png"); plt.close(fig)

# 図2：グループの特徴（標準化した値の中央値）
H = prof.loc[order]; H.index = gorder; H.columns = [COLS[c] for c in H.columns]
fig, ax = plt.subplots(figsize=(9, 3.8))
im = ax.imshow(H.values, cmap="RdBu_r", vmin=-1.6, vmax=1.6, aspect="auto")
ax.set_xticks(range(H.shape[1]), H.columns, rotation=35, ha="right", fontsize=9); ax.set_yticks(range(H.shape[0]), H.index)
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        ax.text(j, i, f"{H.values[i, j]:+.1f}", ha="center", va="center", fontsize=8, color="white" if abs(H.values[i, j]) > 0.9 else "#0b0b0b")
for sp in ax.spines.values(): sp.set_visible(False)
fig.colorbar(im, ax=ax, pad=0.01).set_label("全国平均からの差（標準偏差）")
ax.set_title("グループごとの特徴（赤＝全国より高い、青＝低い）", loc="left")
fig.text(0.01, -0.25, SOURCE, fontsize=8, color="#8a8984"); fig.savefig(FIG / "c1_profile.png"); plt.close(fig)

# 図3：いくつに分けるのがよいか（シルエット係数）
fig, ax = plt.subplots(figsize=(8, 3.2))
ax.plot(sil.k, sil.silhouette, marker="o", color=BLUE); ax.axvline(K, color=GRAY, ls=":")
ax.set_xlabel("グループの数 k"); ax.set_ylabel("シルエット係数"); ax.set_ylim(0, 0.5)
ax.text(K + 0.1, 0.45, f"この記事は k={K}", fontsize=9, color="#52514e")
ax.set_title("どの k でもシルエット係数は0.3未満：はっきりした塊はない", loc="left")
fig.text(0.01, -0.08, SOURCE + "（0.5以上なら塊がはっきりしている目安とされることが多い）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "c1_silhouette.png"); plt.close(fig)
