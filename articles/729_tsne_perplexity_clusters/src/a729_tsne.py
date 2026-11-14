"""729 t-SNE の2次元の図で、まとまりの大きさや間の距離は、元のデータをどれだけ映しているのか

架空の会員300人の10項目の利用状況（標準化した値）を2通り作る：
  まとまりなし：10次元の正規分布（どこにも固まりがない）
  本当に3つ：A・B・C の3つのまとまり（各100人）。広がり（標準偏差）は A 0.3・B 0.6・C 1.2（C は A の4倍）、
            中心の間の距離は A–B 3、A–C と B–C は約9（C だけ3倍遠い）
t-SNE（perplexity 2・5・15・30・50、初期値は主成分、乱数の種0）と主成分分析（上位2つ）で2次元にする。
  まとまりのないデータの固まり具合：Clark–Evans の比（最も近い点までの距離の平均 ÷ 同じ広さに一様に散らばったときの値）。
                  1 なら一様、1 より小さいほど小さな塊に固まって見える。参考に k-means（k＝2〜8）のシルエット係数の最大も出す
  大きさの映り方：C の広がり÷A の広がり（中心からの距離の平均の比）
  距離の映り方：A–C の中心の距離÷A–B の中心の距離
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from scipy.spatial import ConvexHull
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の会員300人の利用状況（作成者が乱数で作成、seed 729）"
rng = np.random.default_rng(729)
N, D = 300, 10
X_noise = rng.normal(0, 1, (N, D))
lab = np.repeat([0, 1, 2], N // 3)
c = np.zeros((3, D)); c[1, 0] = 3.0; c[2, 0] = 1.5; c[2, 1] = np.sqrt(9.0 ** 2 - 1.5 ** 2)
sd = np.array([0.3, 0.6, 1.2])
X_3 = c[lab] + rng.normal(0, 1, (N, D)) * sd[lab][:, None]
PERP = [2, 5, 15, 30, 50]


def sil_max(Y):
    return max(silhouette_score(Y, KMeans(k, n_init=4, random_state=0).fit_predict(Y)) for k in range(2, 9))


def clark_evans(Y):
    d = NearestNeighbors(n_neighbors=2).fit(Y).kneighbors(Y)[0][:, 1]
    area = ConvexHull(Y).volume
    return d.mean() / (0.5 / np.sqrt(len(Y) / area))


def geom(Y):
    m = np.array([Y[lab == g].mean(0) for g in range(3)])
    spread = np.array([np.linalg.norm(Y[lab == g] - m[g], axis=1).mean() for g in range(3)])
    return spread[2] / spread[0], np.linalg.norm(m[2] - m[0]) / np.linalg.norm(m[1] - m[0])


emb = {}
rows = []
for key in ["10次元", "PCA"] + PERP:
    if key == "10次元":
        Yn, Y3 = X_noise, X_3
    elif key == "PCA":
        Yn, Y3 = PCA(2).fit_transform(X_noise), PCA(2).fit_transform(X_3)
    else:
        Yn = TSNE(2, perplexity=key, init="pca", random_state=0, max_iter=1000).fit_transform(X_noise)
        Y3 = TSNE(2, perplexity=key, init="pca", random_state=0, max_iter=1000).fit_transform(X_3)
    emb[key] = (Yn, Y3)
    sr, dr = geom(Y3)
    rows.append({"view": str(key), "noise_clark_evans": clark_evans(Yn) if key != "10次元" else np.nan, "noise_silhouette_max": sil_max(Yn), "size_ratio_C_over_A": sr, "dist_ratio_AC_over_AB": dr})
R = pd.DataFrame(rows); R.round(4).to_csv(RES / "summary.csv", index=False)
Ri = R.set_index("view")

out = {"n": N, "dims": D, "perplexities": PERP,
       "noise_clark_evans": {k: round(float(Ri.loc[k, "noise_clark_evans"]), 3) for k in Ri.index if k != "10次元"},
       "noise_silhouette_max": {k: round(float(Ri.loc[k, "noise_silhouette_max"]), 3) for k in Ri.index},
       "size_ratio_C_over_A": {k: round(float(Ri.loc[k, "size_ratio_C_over_A"]), 2) for k in Ri.index},
       "dist_ratio_AC_over_AB": {k: round(float(Ri.loc[k, "dist_ratio_AC_over_AB"]), 2) for k in Ri.index},
       "true_sd": sd.tolist(), "silhouette_rule": "k-means k=2..8 の最大"}
json.dump(out, open(RES / "a729_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：まとまりのないデータ
fig, axes = plt.subplots(1, 5, figsize=(14, 3.2))
for ax, key in zip(axes, ["PCA", 2, 5, 30, 50]):
    Y = emb[key][0]; ax.scatter(Y[:, 0], Y[:, 1], s=5, color=BLUE)
    ax.set_title(("主成分分析" if key == "PCA" else f"t-SNE perplexity {key}") + f"\n固まり具合（Clark–Evans）{Ri.loc[str(key), 'noise_clark_evans']:.2f}", fontsize=9.5)
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("まとまりのないデータでも、perplexity が小さいと小さな塊に割れて見える（1 なら一様、小さいほど塊）", y=1.06)
save(fig, "a729_noise.png", SRC, y=-0.03)

# 図2：3つのまとまり
fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
for ax, key in zip(axes, ["PCA", 5, 30, 50]):
    Y = emb[key][1]
    for g, col, nm in [(0, BLUE, "A（広がり0.3）"), (1, GREEN, "B（0.6）"), (2, ORANGE, "C（1.2）")]:
        ax.scatter(Y[lab == g, 0], Y[lab == g, 1], s=5, color=col, label=nm)
    ax.set_title(("主成分分析" if key == "PCA" else f"t-SNE perplexity {key}") +
                 f"\n大きさ C÷A {Ri.loc[str(key), 'size_ratio_C_over_A']:.1f}倍・距離 AC÷AB {Ri.loc[str(key), 'dist_ratio_AC_over_AB']:.1f}倍", fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.06))
fig.suptitle(f"本当は C が A の{Ri.loc['10次元', 'size_ratio_C_over_A']:.1f}倍広く、A–C は A–B の{Ri.loc['10次元', 'dist_ratio_AC_over_AB']:.1f}倍遠い", y=1.06)
save(fig, "a729_three.png", SRC, y=-0.08)

# 図3：perplexity ごとのまとめ
fig, axes = plt.subplots(1, 3, figsize=(13, 3.6)); xs = [str(p) for p in PERP]
axes[0].plot(xs, [Ri.loc[p, "noise_clark_evans"] for p in xs], marker="o", color=ORANGE, label="t-SNE")
axes[0].axhline(1.0, color=INK, ls="--", lw=0.8, label="一様に散らばったとき")
axes[0].axhline(Ri.loc["PCA", "noise_clark_evans"], color=GRAY, ls=":", lw=1, label="主成分分析")
axes[0].set_title("まとまりのないデータの固まり具合", fontsize=11); axes[0].set_xlabel("perplexity"); axes[0].legend(frameon=False, fontsize=8)
axes[0].set_ylim(0, None)
axes[1].plot(xs, [Ri.loc[p, "size_ratio_C_over_A"] for p in xs], marker="o", color=ORANGE)
axes[1].axhline(Ri.loc["10次元", "size_ratio_C_over_A"], color=INK, ls="--", lw=0.8); axes[1].axhline(Ri.loc["PCA", "size_ratio_C_over_A"], color=GRAY, ls=":", lw=1)
axes[1].set_title("大きさの比 C÷A", fontsize=11); axes[1].set_xlabel("perplexity"); axes[1].set_ylim(0, None)
axes[2].plot(xs, [Ri.loc[p, "dist_ratio_AC_over_AB"] for p in xs], marker="o", color=ORANGE)
axes[2].axhline(Ri.loc["10次元", "dist_ratio_AC_over_AB"], color=INK, ls="--", lw=0.8); axes[2].axhline(Ri.loc["PCA", "dist_ratio_AC_over_AB"], color=GRAY, ls=":", lw=1)
axes[2].set_title("距離の比 A–C÷A–B", fontsize=11); axes[2].set_xlabel("perplexity"); axes[2].set_ylim(0, None)
fig.suptitle("中と右：黒い点線＝10次元のまま、灰色の点線＝主成分分析", y=1.03, fontsize=10)
save(fig, "a729_summary.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False))
