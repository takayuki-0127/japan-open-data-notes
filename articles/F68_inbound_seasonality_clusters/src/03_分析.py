"""03 分析：36の国・地域の季節の形を、3つの時系列クラスタリングで分ける

- ユークリッド距離の k-means（季節の形そのものを比べる。基準）
- DTW の k-means（ピークの月が1〜2か月ずれても似ているとみなす。Sakoe–Chiba 半径2）
- k-shape（形をそろえたうえで、ずらしても重なるかを見る。値は平均0・標準偏差1にそろえる）
クラスタ数 k は 2〜8 をシルエットと「年を入れ替えたときの安定性」で比べる。
"""
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score as ari, silhouette_score
from tslearn.clustering import TimeSeriesKMeans, KShape
from tslearn.metrics import cdist_dtw
from tslearn.preprocessing import TimeSeriesScalerMeanVariance

from common import DATA, RES, SEED, BASE_YEARS, MONTHS

prof = pd.read_csv(DATA / "profile_2015_2019.csv", index_col=0)
X = prof.values
Xz = TimeSeriesScalerMeanVariance().fit_transform(X[:, :, None])[:, :, 0]
D_euc = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
D_dtw = cdist_dtw(X[:, :, None], global_constraint="sakoe_chiba", sakoe_chiba_radius=2)


def sbd_matrix(Z):
    n = len(Z)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            cc = np.correlate(Z[i], Z[j], mode="full") / (np.linalg.norm(Z[i]) * np.linalg.norm(Z[j]))
            D[i, j] = 1 - cc.max()
    return D


D_sbd = np.clip(sbd_matrix(Xz), 0, None)
np.fill_diagonal(D_sbd, 0)


def fit(method, k, data=None, seed=SEED):
    data = X if data is None else data
    if method == "euclid":
        m = TimeSeriesKMeans(n_clusters=k, metric="euclidean", n_init=20, random_state=seed)
        return m.fit_predict(data[:, :, None]), m
    if method == "dtw":
        m = TimeSeriesKMeans(n_clusters=k, metric="dtw", metric_params={"global_constraint": "sakoe_chiba", "sakoe_chiba_radius": 2},
                             n_init=10, max_iter=50, random_state=seed)
        return m.fit_predict(data[:, :, None]), m
    if method == "kshape":
        z = TimeSeriesScalerMeanVariance().fit_transform(data[:, :, None])
        m = KShape(n_clusters=k, n_init=10, random_state=seed)
        return m.fit_predict(z), m


DIST = {"euclid": D_euc, "dtw": D_dtw, "kshape": D_sbd}

# --- k の選び方：シルエットと、年をブートストラップしたときの安定性 ---
years = {y: pd.read_csv(DATA / f"profile_year_{y}.csv", index_col=0).values for y in BASE_YEARS}
rng = np.random.default_rng(SEED)
B = 40
rows = []
labels = {}
for method in ["euclid", "dtw", "kshape"]:
    for k in range(2, 9):
        lab, _ = fit(method, k)
        labels[(method, k)] = lab
        sil = silhouette_score(DIST[method], lab, metric="precomputed") if len(set(lab)) > 1 else np.nan
        aris = []
        for b in range(B):
            ys = rng.choice(BASE_YEARS, size=len(BASE_YEARS), replace=True)
            Xb = np.mean([years[y] for y in ys], axis=0)
            lb, _ = fit(method, k, Xb, seed=SEED + b + 1)
            aris.append(ari(lab, lb))
        rows.append(dict(method=method, k=k, silhouette=sil, stability_ari=np.mean(aris),
                         stability_p10=np.quantile(aris, 0.1), sizes="/".join(map(str, sorted(np.bincount(lab), reverse=True)))))
        print(method, k, round(sil, 3), round(np.mean(aris), 3))
sel = pd.DataFrame(rows)
sel.to_csv(RES / "k_selection.csv", index=False)

# 全手法・全 k のラベル
lab_df = pd.DataFrame({f"{m}_k{k}": v for (m, k), v in labels.items()}, index=prof.index)
lab_df.to_csv(RES / "labels_all.csv")

# 手法どうしの一致（同じ k）
agree = []
for k in range(2, 9):
    for a, b in [("euclid", "dtw"), ("euclid", "kshape"), ("dtw", "kshape")]:
        agree.append(dict(k=k, pair=f"{a}-{b}", ari=ari(labels[(a, k)], labels[(b, k)])))
pd.DataFrame(agree).to_csv(RES / "method_agreement.csv", index=False)

# 距離行列も保存
pd.DataFrame(D_euc, index=prof.index, columns=prof.index).round(4).to_csv(RES / "dist_euclid.csv")
pd.DataFrame(D_dtw, index=prof.index, columns=prof.index).round(4).to_csv(RES / "dist_dtw.csv")
pd.DataFrame(D_sbd, index=prof.index, columns=prof.index).round(4).to_csv(RES / "dist_sbd.csv")
