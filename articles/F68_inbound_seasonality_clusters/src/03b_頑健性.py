"""03b 頑健性とコロナ前後の比較

本体：ユークリッド距離の k-means（BASE_K は 03 の結果から決めた値）
- 期間を変える（2005〜09年、2016〜19年、2023〜25年）
- 日数をそろえる（1日あたり）
- 小さい国を除く（2019年に5万人未満）
- 別の分け方（Ward の階層クラスタリング、DTW、k-shape）
- 年を1年ずつ抜く
それぞれ、本体のラベルとの一致（ARI）と、本体の重心に当てはめたときに同じ型になる国の割合を出す。
"""
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.metrics import adjusted_rand_score as ari
from tslearn.clustering import TimeSeriesKMeans

from common import DATA, RES, SEED, BASE_YEARS, MONTHS, MARKETS, load_long, panel, profile

BASE_K = int((RES / "chosen_k.txt").read_text().strip())
prof = pd.read_csv(DATA / "profile_2015_2019.csv", index_col=0)
lab_all = pd.read_csv(RES / "labels_all.csv", index_col=0)


def km(X, k=BASE_K, seed=SEED):
    m = TimeSeriesKMeans(n_clusters=k, metric="euclidean", n_init=30, random_state=seed)
    return m.fit_predict(X[:, :, None]), m.cluster_centers_[:, :, 0]


base, cen = km(prof.values)
# 型の番号を、1月の値の大きい順など毎回同じになるよう並べ替える（人数の多い国を含む順）
ann = pd.read_csv(DATA / "annual_visitors.csv", index_col=0)
v19 = ann.loc[prof.index, "2019"].values
order = np.argsort([-v19[base == c].sum() for c in range(BASE_K)])
remap = {old: new for new, old in enumerate(order)}
base = np.array([remap[x] for x in base])
cen = cen[order]
pd.DataFrame({"type": base + 1}, index=prof.index).to_csv(RES / "base_labels.csv")
pd.DataFrame(cen, columns=MONTHS, index=[f"型{c+1}" for c in range(BASE_K)]).round(4).to_csv(RES / "base_centroids.csv")


def nearest(X):
    d = ((X[:, None, :] - cen[None, :, :]) ** 2).sum(-1)
    return d.argmin(1), np.sqrt(d.min(1))


rows = []
p = panel(load_long())


def add(name, X, idx=None, labels=None):
    idx = prof.index if idx is None else idx
    b = pd.Series(base, index=prof.index).loc[idx].values
    if labels is None:
        labels, _ = km(X, seed=SEED)
    same = (nearest(X)[0] == b).mean()
    rows.append(dict(setting=name, n=len(idx), ari=ari(b, labels), same_type_by_centroid=same))


add("本体（2015〜19年）", prof.values)
add("2016〜19年", profile(p, [2016, 2017, 2018, 2019]).values)
add("2005〜09年", profile(p, [2005, 2006, 2007, 2008, 2009]).values)
add("2023〜25年（コロナ後）", profile(p, [2023, 2024, 2025]).values)
add("1日あたり", profile(p, BASE_YEARS, per_day=True).values)
big = [m for m in MARKETS if ann.loc[m, "2019"] >= 50000]
add("2019年に5万人以上の国だけ", prof.loc[big].values, idx=big)
Z = linkage(prof.values, "ward")
add("Ward の階層クラスタリング", prof.values, labels=fcluster(Z, BASE_K, "maxclust"))
add("DTW の k-means", prof.values, labels=lab_all[f"dtw_k{BASE_K}"].values)
add("k-shape", prof.values, labels=lab_all[f"kshape_k{BASE_K}"].values)
for y in BASE_YEARS:
    ys = [x for x in BASE_YEARS if x != y]
    add(f"{y}年を抜く", profile(p, ys).values)
rob = pd.DataFrame(rows)
rob.to_csv(RES / "robustness.csv", index=False)
print(rob.round(3).to_string())

# 年ごとの形がどれだけ安定しているか（同じ国の年どうしの相関）
yrs = BASE_YEARS + [2023, 2024, 2025]
Y = {y: pd.read_csv(DATA / f"profile_year_{y}.csv", index_col=0) for y in yrs}
st = []
for m in prof.index:
    within = [np.corrcoef(Y[a].loc[m], Y[b].loc[m])[0, 1] for i, a in enumerate(BASE_YEARS) for b in BASE_YEARS[i + 1:]]
    post = profile(p, [2023, 2024, 2025]).loc[m]
    st.append(dict(market=m, type=base[list(prof.index).index(m)] + 1,
                   corr_between_years_2015_19=np.mean(within),
                   corr_pre_post=np.corrcoef(prof.loc[m], post)[0, 1],
                   post_type=nearest(post.values[None, :])[0][0] + 1,
                   peak_pre=prof.loc[m].idxmax(), peak_post=post.idxmax()))
st = pd.DataFrame(st)
st.to_csv(RES / "pre_post_by_market.csv", index=False)
print(st.round(2).to_string())

# 総数の季節の形を、型ごとの寄与に分ける（2019年と2025年）
dec = []
lab_s = pd.Series(base + 1, index=prof.index)
for y in [2019, 2025]:
    tot = p[y].sum()
    for t in range(1, BASE_K + 1):
        s = p[y].loc[lab_s[lab_s == t].index].sum()
        for mo in range(1, 13):
            dec.append(dict(year=y, type=t, month=mo, visitors=s[mo], share_of_total=s[mo] / tot[mo]))
pd.DataFrame(dec).to_csv(RES / "total_by_type.csv", index=False)

# 細かい分け方の一致：3手法 × k=3〜6 の12通りで、2つの国が同じ型になった割合（共起行列）
runs = [f"{m}_k{k}" for m in ["euclid", "dtw", "kshape"] for k in range(3, 7)]
L = lab_all[runs].values
co = (L[:, None, :] == L[None, :, :]).mean(-1)
pd.DataFrame(co, index=prof.index, columns=prof.index).round(3).to_csv(RES / "coassignment_k3to6.csv")
pairs = []
idx = list(prof.index)
for i in range(len(idx)):
    for j in range(i + 1, len(idx)):
        pairs.append(dict(a=idx[i], b=idx[j], share=co[i, j]))
pairs = pd.DataFrame(pairs).sort_values("share", ascending=False)
pairs.to_csv(RES / "coassignment_pairs.csv", index=False)
print("12通りすべてで同じ型になった組の数:", (pairs.share == 1).sum(), "/", len(pairs))
print(pairs[pairs.share == 1].to_string())
