"""450 k-means は、丸くないまとまりや大きさの違うまとまりを、どれだけ取り違えるのか
架空の点（2次元・3つのまとまり・計600点）。正解のまとまりが分かっているので、当たった割合を測れる。seed 450"""
import json, warnings
import numpy as np, pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from common import *
warnings.filterwarnings("ignore")

rng = np.random.default_rng(450)
REP = 100


def scene(name):
    if name == "丸くて同じ大きさ":
        c = np.array([[0, 0], [6, 0], [3, 5.2]]); n = [200, 200, 200]
        X = np.vstack([rng.normal(ci, 1.0, (ni, 2)) for ci, ni in zip(c, n)])
    elif name == "細長い":
        c = np.array([[0, 0], [0, 3], [0, 6]]); n = [200, 200, 200]
        X = np.vstack([np.column_stack([rng.normal(ci[0], 5.0, ni), rng.normal(ci[1], 0.6, ni)]) for ci, ni in zip(c, n)])
        th = np.deg2rad(30); R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]); X = X @ R.T
    elif name == "広がりが違う":
        c = np.array([[0, 0], [5, 0], [2.5, 6]]); n = [200, 200, 200]; sd = [0.5, 1.0, 2.5]
        X = np.vstack([rng.normal(ci, s, (ni, 2)) for ci, ni, s in zip(c, n, sd)])
    elif name == "点の数が違う":
        c = np.array([[0, 0], [5, 0], [2.5, 4.3]]); n = [500, 80, 20]
        X = np.vstack([rng.normal(ci, 1.0, (ni, 2)) for ci, ni in zip(c, n)])
    y = np.repeat([0, 1, 2], n)
    return X, y


SCENES = ["丸くて同じ大きさ", "細長い", "広がりが違う", "点の数が違う"]


def acc(y, lab):
    k = max(y.max(), lab.max()) + 1; C = np.zeros((k, k), int)
    for a, b in zip(y, lab): C[a, b] += 1
    r, c = linear_sum_assignment(-C); return C[r, c].sum() / len(y)


def per_cluster_recall(y, lab):
    k = max(y.max(), lab.max()) + 1; C = np.zeros((k, k), int)
    for a, b in zip(y, lab): C[a, b] += 1
    r, c = linear_sum_assignment(-C); m = dict(zip(r, c))
    return [C[i, m[i]] / max(C[i].sum(), 1) for i in range(3)]


def methods(X, seed):
    return {"k-means": KMeans(3, n_init=10, random_state=seed).fit_predict(X),
            "混合正規分布（ふつうの出発点）": GaussianMixture(3, covariance_type="full", n_init=3, random_state=seed).fit_predict(X),
            "混合正規分布（出発点を20通り）": GaussianMixture(3, covariance_type="full", n_init=20, init_params="random_from_data", random_state=seed).fit_predict(X),
            "階層的（ウォード法）": AgglomerativeClustering(3, linkage="ward").fit_predict(X),
            "階層的（平均連結）": AgglomerativeClustering(3, linkage="average").fit_predict(X)}


rows, krows, rec = [], [], []
example = {}
for s in SCENES:
    A = {m: [] for m in ["k-means", "混合正規分布（ふつうの出発点）", "混合正規分布（出発点を20通り）", "階層的（ウォード法）", "階層的（平均連結）"]}
    ks_sil, ks_bic, ks_sil_std = [], [], []
    for r in range(REP):
        X, y = scene(s); L = methods(X, r)
        for m, lab in L.items(): A[m].append(acc(y, lab))
        rec.append(dict(scene=s, **{f"recall_{i+1}": v for i, v in enumerate(per_cluster_recall(y, L["k-means"]))}))
        if r == 0: example[s] = (X, y, L["k-means"], L["混合正規分布（出発点を20通り）"])
        if r < 50:   # まとまりの数を選ぶ（2〜6）
            sil = [silhouette_score(X, KMeans(k, n_init=5, random_state=r).fit_predict(X)) for k in range(2, 7)]
            bic = [GaussianMixture(k, covariance_type="full", n_init=10, init_params="random_from_data", random_state=r).fit(X).bic(X) for k in range(1, 7)]
            ks_sil.append(2 + int(np.argmax(sil))); ks_bic.append(1 + int(np.argmin(bic)))
    for m, v in A.items():
        v = np.array(v); rows.append(dict(scene=s, method=m, accuracy=v.mean(), accuracy_p05=np.percentile(v, 5), accuracy_min=v.min(), share_below_90=(v < 0.9).mean()))
    for rule, ks in [("シルエット（k-means）", ks_sil), ("BIC（混合正規分布・出発点を10通り）", ks_bic)]:
        ks = np.array(ks); krows.append(dict(scene=s, rule=rule, **{f"share_k{k}": (ks == k).mean() for k in range(1, 7)}))
res = pd.DataFrame(rows); res.round(4).to_csv(RES / "accuracy_by_scene.csv", index=False)
ksel = pd.DataFrame(krows); ksel.round(4).to_csv(RES / "number_of_clusters.csv", index=False)
recall = pd.DataFrame(rec).groupby("scene").mean().reindex(SCENES); recall.round(4).to_csv(RES / "kmeans_recall_by_cluster.csv")

# ---- 標準化で変わる度合い（丸い3つのまとまり。片方の軸の単位だけが違う）
srows = []
for label, mult, noise_y in [("片方の軸を100倍の単位で書いた（中身は同じ）", (100, 1), None), ("差のない軸がもともと小さな桁で入っている", (1, 1), 0.2)]:
    a_raw, a_std = [], []
    for r in range(REP):
        if noise_y is None:
            X, y = scene("丸くて同じ大きさ"); X = X * np.array(mult)
        else:                                   # まとまりは横の軸だけで分かれ、縦の軸は差のない小さな振れ
            y = np.repeat([0, 1, 2], 200); X = np.column_stack([rng.normal(np.array([0, 4, 8])[y], 1.0), rng.normal(0, noise_y, 600)])
        Z = (X - X.mean(0)) / X.std(0)
        a_raw.append(acc(y, KMeans(3, n_init=10, random_state=r).fit_predict(X))); a_std.append(acc(y, KMeans(3, n_init=10, random_state=r).fit_predict(Z)))
    srows.append(dict(case=label, kmeans_raw=np.mean(a_raw), kmeans_standardized=np.mean(a_std)))
std = pd.DataFrame(srows); std.round(4).to_csv(RES / "standardization.csv", index=False)

# ---- 細長さを変える（縦の広がり0.6に対する横の広がり）
erows = []
for sx in [0.6, 1.2, 2.0, 3.0, 5.0, 8.0]:
    a_k, a_g, a_g2 = [], [], []
    for r in range(40):
        c = np.array([[0, 0], [0, 3], [0, 6]]); y = np.repeat([0, 1, 2], 200)
        X = np.vstack([np.column_stack([rng.normal(0, sx, 200), rng.normal(ci[1], 0.6, 200)]) for ci in c])
        a_k.append(acc(y, KMeans(3, n_init=10, random_state=r).fit_predict(X))); a_g.append(acc(y, GaussianMixture(3, covariance_type="full", n_init=3, random_state=r).fit_predict(X)))
        a_g2.append(acc(y, GaussianMixture(3, covariance_type="full", n_init=20, init_params="random_from_data", random_state=r).fit_predict(X)))
    erows.append(dict(length_over_width=sx / 0.6, kmeans=np.mean(a_k), gmm=np.mean(a_g), gmm_20_starts=np.mean(a_g2)))
elong = pd.DataFrame(erows); elong.round(4).to_csv(RES / "elongation_sweep.csv", index=False)

for s in SCENES:
    X, y, lk, lg = example[s]
    pd.DataFrame({"x1": X[:, 0], "x2": X[:, 1], "true": y, "kmeans": lk, "gmm": lg}).round(4).to_csv(DATA / f"example_{SCENES.index(s)+1}.csv", index=False)

g = lambda s, m, c="accuracy": round(float(res[(res.scene == s) & (res.method == m)][c].iloc[0]), 4)
main = dict(rep=REP, accuracy={s: {m: g(s, m) for m in res.method.unique()} for s in SCENES},
            share_below_90={s: {m: g(s, m, "share_below_90") for m in res.method.unique()} for s in SCENES},
            kmeans_recall={s: [round(float(v), 4) for v in recall.loc[s]] for s in SCENES},
            k_selection=ksel.round(3).to_dict("records"), standardization=std.round(4).to_dict("records"), elongation=elong.round(4).to_dict("records"))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

SRC = "架空の点（作成者が乱数で作成、seed 450）。3つのまとまり・計600点"
C3 = np.array([BLUE, ORANGE, GREEN])
fig, axes = plt.subplots(2, 4, figsize=(12.5, 6.2))
for j, s in enumerate(SCENES):
    X, y, lk, lg = example[s]
    k = 3; Cm = np.zeros((k, k), int)
    for a, b in zip(y, lk): Cm[a, b] += 1
    r_, c_ = linear_sum_assignment(-Cm); inv = {b: a for a, b in zip(r_, c_)}; lk2 = np.array([inv[b] for b in lk])
    axes[0, j].scatter(X[:, 0], X[:, 1], s=5, c=C3[y]); axes[0, j].set_title(s, fontsize=11)
    axes[1, j].scatter(X[:, 0], X[:, 1], s=5, c=C3[lk2]); axes[1, j].set_title(f"k-means（当たり {acc(y, lk)*100:.0f}%）", fontsize=10)
    for ax in axes[:, j]: ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal", adjustable="datalim")
axes[0, 0].set_ylabel("正解"); axes[1, 0].set_ylabel("k-means の分け方")
fig.suptitle("上が正解、下が k-means の分け方（1回分の例）", y=0.99)
save(fig, "a450_scenes_true_vs_kmeans.png", SRC)

fig, ax = plt.subplots(figsize=(9.2, 4.5))
ms = list(res.method.unique()); w = 0.17; cc = [GRAY, "#f3b79f", ORANGE, BLUE, LIGHT]
for i, m in enumerate(ms):
    v = [g(s, m) * 100 for s in SCENES]; b = ax.bar(np.arange(4) + (i - 2) * w, v, w, color=cc[i], label=m)
    for x_, v_ in zip(np.arange(4) + (i - 2) * w, v): ax.text(x_, v_ + 1, f"{v_:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(range(4)); ax.set_xticklabels(SCENES); ax.set_ylim(0, 128); ax.set_yticks([0, 25, 50, 75, 100]); ax.set_ylabel("正しいまとまりに入った点の割合（%）")
ax.set_title("丸くて同じ大きさならどの方法も当たる。形や大きさが違うと差が出る"); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper center")
save(fig, "a450_accuracy_by_method.png", SRC + "。100回の平均")

fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
for i, (rule, c) in enumerate([("シルエット（k-means）", GRAY), ("BIC（混合正規分布・出発点を10通り）", ORANGE)]):
    d = ksel[ksel.rule == rule].set_index("scene").reindex(SCENES)
    b = axes[0].bar(np.arange(4) + (i - 0.5) * 0.38, d.share_k3 * 100, 0.38, color=c, label=rule)
    for x_, v_ in zip(np.arange(4) + (i - 0.5) * 0.38, d.share_k3 * 100): axes[0].text(x_, v_ + 1.5, f"{v_:.0f}", ha="center", fontsize=9)
axes[0].set_xticks(range(4)); axes[0].set_xticklabels(SCENES, fontsize=9); axes[0].set_ylim(0, 138); axes[0].set_yticks([0, 25, 50, 75, 100]); axes[0].set_ylabel("まとまりの数を3と当てた割合（%）")
axes[0].set_title("まとまりの数を選ぶ指標"); axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
axes[1].plot(elong.length_over_width, elong.kmeans * 100, "o-", color=GRAY, label="k-means"); axes[1].plot(elong.length_over_width, elong.gmm * 100, "o-", color="#f3b79f", label="混合正規分布（ふつうの出発点）"); axes[1].plot(elong.length_over_width, elong.gmm_20_starts * 100, "o-", color=ORANGE, label="混合正規分布（出発点を20通り）")
axes[1].set_xlabel("まとまりの長さ ÷ 幅"); axes[1].set_ylabel("正しいまとまりに入った点の割合（%）"); axes[1].set_title("細長くなるほど k-means は外れる"); axes[1].legend(frameon=False, fontsize=8.5); axes[1].set_ylim(0, 105)
save(fig, "a450_k_selection_and_elongation.png", SRC + "。左は50回、右は40回")
print(json.dumps(main, ensure_ascii=False, indent=0)[:3800])
