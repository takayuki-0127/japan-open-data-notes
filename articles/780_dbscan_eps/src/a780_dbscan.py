"""780 DBSCAN の eps を少し変えると、まとまりの数と外れ値の数はどれだけ変わるのか

架空のデータ。2次元で、密度の違うまとまり3つ（標準偏差0.25・0.5・1.0、各300点）と、全体に散らばる外れの点60点。
DBSCAN（min_samples=10）の eps を0.1〜1.5に変え、見つかったまとまりの数・外れ値（ラベル−1）の割合・正解との一致（ARI）を数える。
k 距離の図（10番目に近い点までの距離を並べたもの）の曲がり目から eps を選ぶ方法もあわせて見る。データは10組作り、平均をとる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import NearestNeighbors
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 780）"
rng = np.random.default_rng(780)
EPS = np.round(np.arange(.1, 1.51, .05), 2); MS, NSET = 10, 10
CEN = np.array([[0, 0], [5, 0], [2.5, 5]]); SD = [.25, .5, 1.0]


def make():
    X = np.vstack([rng.normal(c, s, (300, 2)) for c, s in zip(CEN, SD)] + [rng.uniform([-3, -3], [8, 9], (60, 2))])
    y = np.r_[np.repeat([0, 1, 2], 300), np.full(60, -1)]
    return X, y


def knee(X):
    d = np.sort(NearestNeighbors(n_neighbors=MS).fit(X).kneighbors(X)[0][:, -1])
    i = np.arange(len(d)); line = d[0] + (d[-1] - d[0]) * i / (len(d) - 1)
    return d, float(d[np.argmax(line - d)])           # 両端を結ぶ直線から最も離れた所


rows = []; knees = []; ex = None
for k in range(NSET):
    X, y = make()
    d, ke = knee(X); knees.append(ke)
    if k == 0: ex = (X, y, d, ke)
    for e in EPS:
        lab = DBSCAN(eps=e, min_samples=MS).fit_predict(X)
        rows.append(dict(set=k, eps=e, clusters=len(set(lab)) - (-1 in lab), noise=(lab == -1).mean(), ari=adjusted_rand_score(y, lab)))
    lab = DBSCAN(eps=ke, min_samples=MS).fit_predict(X)
    rows.append(dict(set=k, eps=-1.0, clusters=len(set(lab)) - (-1 in lab), noise=(lab == -1).mean(), ari=adjusted_rand_score(y, lab)))
D = pd.DataFrame(rows); D.to_csv(RES / "by_set.csv", index=False, float_format="%.5f")
S = D[D.eps > 0].groupby("eps").agg(clusters=("clusters", "mean"), noise=("noise", "mean"), ari=("ari", "mean"),
                                    three=("clusters", lambda s: (s == 3).mean())).reset_index()
S.to_csv(RES / "summary.csv", index=False)
K = D[D.eps < 0]
g = lambda e, c: float(S[np.isclose(S.eps, e)][c].iloc[0])
best = S.loc[S.ari.idxmax()]
three_range = S[S.three >= .9].eps
out = {"points": 960, "true_clusters": 3, "true_noise_share": 60 / 960, "min_samples": MS, "sets": NSET,
       "by_eps": {f"{e:.2f}": {"clusters": round(g(e, "clusters"), 2), "noise": round(g(e, "noise"), 3), "ari": round(g(e, "ari"), 3)} for e in [.1, .2, .3, .4, .5, .6, .8, 1.0, 1.2, 1.5]},
       "best_eps": float(best.eps), "best_ari": float(best.ari),
       "three_clusters_eps_min": float(three_range.min()) if len(three_range) else None,
       "three_clusters_eps_max": float(three_range.max()) if len(three_range) else None,
       "knee_eps_mean": float(np.mean(knees)), "knee_eps_min": float(np.min(knees)), "knee_eps_max": float(np.max(knees)),
       "knee_clusters_mean": float(K.clusters.mean()), "knee_noise_mean": float(K.noise.mean()), "knee_ari_mean": float(K.ari.mean())}
json.dump(out, open(RES / "a780_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：eps とまとまりの数・外れ値
fig, ax = plt.subplots(figsize=(9, 4.6)); ax2 = ax.twinx()
ax.plot(S.eps, S.clusters, "o-", color=BLUE, ms=4, label="まとまりの数（左）")
ax2.plot(S.eps, S.noise * 100, "s-", color=ORANGE, ms=4, label="外れ値の割合（右）")
ax.axhline(3, color=BLUE, ls=":", lw=1); ax2.axhline(100 * 60 / 960, color=ORANGE, ls=":", lw=1)
ax.set_xlabel("eps"); ax.set_ylabel("まとまりの数（10組の平均）", color=BLUE); ax2.set_ylabel("外れ値の割合（%）", color=ORANGE)
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right")
ax.set_title("eps が小さいと薄いまとまりが外れ値に、大きいとまとまりがつながる（点線が正解）")
save(fig, "a780_eps.png", SRC)
# 図2：ARI
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.eps, S.ari, "o-", color=GREEN, ms=4, label="eps を固定")
ax.axvspan(out["knee_eps_min"], out["knee_eps_max"], color=GRAY, alpha=.3, label="k 距離の図の曲がり目（10組の範囲）")
ax.set_xlabel("eps"); ax.set_ylabel("正解との一致（ARI、10組の平均）"); ax.set_ylim(0, 1); ax.legend(frameon=False)
ax.set_title(f"eps 0.5〜1.2 なら一致は0.9前後、その外では急に下がる（最もよいのは eps={best.eps:.2f}）")
save(fig, "a780_ari.png", SRC)
# 図3：例
X, y, d, ke = ex
fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharex=True, sharey=True)
for ax, e in zip(axs, [.2, round(ke, 2), 1.0]):
    lab = DBSCAN(eps=e, min_samples=MS).fit_predict(X)
    ax.scatter(X[lab == -1, 0], X[lab == -1, 1], s=4, color=GRAY)
    ax.scatter(X[lab >= 0, 0], X[lab >= 0, 1], s=4, c=lab[lab >= 0], cmap="tab10")
    ax.set_title(f"eps={e}：まとまり{len(set(lab)) - (-1 in lab)}・外れ値{(lab == -1).mean():.0%}", fontsize=10)
fig.suptitle("同じデータでも eps で答えが変わる（灰色が外れ値、真ん中は k 距離の図で選んだ eps）", y=1.03)
save(fig, "a780_example.png", SRC, y=-0.05)
print(json.dumps(out, ensure_ascii=False, indent=1))
