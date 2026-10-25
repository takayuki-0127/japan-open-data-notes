"""k=5 の k-means で分類し、プロフィール・町ごとの安定性・手法や指標を変えたときの一致度を出す。"""
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score, silhouette_samples
import umap
import hdbscan
from common import DATA, RES, SEED

K = 5
d = pd.read_csv(DATA / "indicators.csv")
Z = pd.read_csv(DATA / "z.csv")
P = pd.read_csv(DATA / "pcs.csv").values
km = KMeans(K, n_init=50, random_state=SEED).fit(P)
lab = km.labels_
# クラスタ番号を「平均人口の大きい順」に並べ替える
order = pd.Series(d["人口（対数）"]).groupby(lab).mean().sort_values(ascending=False).index
remap = {o: i for i, o in enumerate(order)}
lab = np.array([remap[l] for l in lab])

# 町ごとの安定性：ブートストラップで「基準の同じ組の町と、また同じ組になる割合」
rng = np.random.default_rng(SEED)
B = 100
same = np.zeros(len(P))
for b in range(B):
    idx = rng.integers(0, len(P), len(P))
    l2 = KMeans(K, n_init=5, random_state=1000 + b).fit(P[idx]).predict(P)
    # 基準の組ごとに、最も多く対応する組を探して一致を数える
    ct = pd.crosstab(lab, l2)
    best = ct.idxmax(axis=1)
    same += (l2 == best.loc[lab].values)
stab = same / B
sil = silhouette_samples(P, lab)

out = d[["code", "pref", "name", "pop"]].copy()
out["cluster"] = lab + 1
out["stability"] = stab
out["silhouette"] = sil

# UMAP（図用）
emb = umap.UMAP(n_neighbors=30, min_dist=0.2, random_state=SEED).fit_transform(P)
out["umap1"], out["umap2"] = emb[:, 0], emb[:, 1]
out.to_csv(RES / "clusters.csv", index=False, encoding="utf-8-sig")

# プロフィール
prof_z = Z.groupby(lab).mean()
prof_z.index = [f"タイプ{i+1}" for i in prof_z.index]
prof_z.T.to_csv(RES / "profile_z.csv", encoding="utf-8-sig")
raw_cols = ["人口（対数）", "65歳以上の割合", "15歳未満の割合", "第1次産業就業者の割合", "従業者の割合：製造業",
            "単独世帯の割合", "純移動率", "1人あたり歳出（対数）", "地方税/歳入", "女性の就業率", "従業者の割合：宿泊・飲食業"]
med = d[raw_cols].groupby(lab).median()
med["人口（対数）"] = np.exp(med["人口（対数）"])
med["1人あたり歳出（対数）"] = np.exp(med["1人あたり歳出（対数）"])
med = med.rename(columns={"人口（対数）": "人口（中央値）", "1人あたり歳出（対数）": "1人あたり歳出（千円、中央値）"})
med.insert(0, "町の数", pd.Series(lab).value_counts().sort_index().values)
med.insert(1, "人口の合計（万人）", (d.groupby(lab)["pop"].sum() / 1e4).round(0).values)
med.insert(2, "安定性の中央値", out.groupby("cluster")["stability"].median().values)
med.index = [f"タイプ{i+1}" for i in med.index]
med.to_csv(RES / "profile_median.csv", encoding="utf-8-sig")
print(med.round(3).T.to_string())
for i in range(K):
    s = prof_z.iloc[i].sort_values()
    print(f"タイプ{i+1} 高い:", list(s.index[-6:][::-1]), "\n        低い:", list(s.index[:4]))
    ex = out[(out.cluster == i + 1)].sort_values("pop", ascending=False).head(8)
    print("   例:", list((ex.pref + ex.name)))

# 手法を変える
alts = {}
alts["ガウス混合（5）"] = GaussianMixture(K, covariance_type="full", n_init=5, random_state=SEED).fit(P).predict(P)
alts["ウォード法（5）"] = AgglomerativeClustering(K, linkage="ward").fit_predict(P)
alts["UMAP上の k-means（5）"] = KMeans(K, n_init=20, random_state=SEED).fit_predict(emb)
hd = hdbscan.HDBSCAN(min_cluster_size=40).fit_predict(emb)
alts["UMAP上の HDBSCAN"] = hd
# 指標を変える
def refit(cols_drop=None, npc=None, use_pca=True):
    X = d.iloc[:, 4:]
    if cols_drop:
        X = X.drop(columns=[c for c in X.columns if any(k in c for k in cols_drop)])
    X = X.clip(X.quantile(0.01), X.quantile(0.99), axis=1)
    Zs = StandardScaler().fit_transform(X)
    if use_pca:
        pca = PCA(random_state=SEED).fit(Zs)
        n = npc or int(np.searchsorted(pca.explained_variance_ratio_.cumsum(), 0.8) + 1)
        Zs = pca.transform(Zs)[:, :n]
    return KMeans(K, n_init=20, random_state=SEED).fit_predict(Zs)
fin = ["経常収支", "公債費", "歳出", "地方税", "民生費", "土木費", "教育費", "職員数"]
alts["財政の指標を除く"] = refit(fin)
alts["産業別の従業者の割合を除く"] = refit(["従業者の割合："])
alts["医療・教育・生活の指標を除く"] = refit(["病院", "診療所", "医師", "薬剤師", "保育所", "図書館", "小売店", "飲食店", "大型小売", "水洗", "小学校", "高校"])
alts["主成分を5つだけ使う"] = refit(npc=5)
alts["主成分にしない（62指標のまま）"] = refit(use_pca=False)
rob = pd.DataFrame([{"比べたもの": k, "ARI": adjusted_rand_score(lab, v), "組の数": len(set(v) - {-1}),
                     "外れ（HDBSCANのみ）": int((v == -1).sum())} for k, v in alts.items()])
rob.to_csv(RES / "robustness_ari.csv", index=False, encoding="utf-8-sig")
print(rob.round(3).to_string())
summ = {"k": K, "stability_median": float(np.median(stab)), "share_stab_ge_0.9": float((stab >= 0.9).mean()),
        "share_stab_lt_0.6": float((stab < 0.6).mean()), "silhouette_mean": float(sil.mean()),
        "share_sil_neg": float((sil < 0).mean())}
json.dump(summ, open(RES / "cluster_summary.json", "w"), ensure_ascii=False, indent=1)
print(summ)
