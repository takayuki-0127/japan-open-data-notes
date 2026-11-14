"""779 混合正規分布を EM 法で当てはめると、初期値によって何%の回で別の答えになるのか

架空のデータ。2次元で、正規分布4つ（中心は正方形の4隅、間隔 s）からそれぞれ150点、計600点。
間隔 s を変えて重なりの大きさを変える。データ1組につき、初期値を120通りに変えて EM 法（sklearn の GaussianMixture、成分4つ、共分散は full）を当てはめる。
初期値の作り方は「データから乱数で4点を選んで中心にする」（init_params='random_from_data'）と「k-means」の2通り、さらに k-means の初期値で10回やって最もよいものを選ぶ（n_init=10）も比べる。
全部の当てはめの中で最もよい対数尤度との差が 1 を超えた回を「別の答え」とし、正解の分け方との一致（ARI）も見る。データは各 s で5組。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 779）"
rng = np.random.default_rng(779)
SEPS, NSET, NINIT, NPER = [2.0, 3.0, 4.0, 6.0], 5, 120, 150


def make(s):
    C = np.array([[0, 0], [s, 0], [0, s], [s, s]])
    X = np.vstack([rng.normal(c, 1, (NPER, 2)) for c in C]); y = np.repeat(np.arange(4), NPER)
    return X, y


rows = []; ex = None
for s in SEPS:
    for k in range(NSET):
        X, y = make(s)
        res = []
        for init in ["random_from_data", "kmeans"]:
            for i in range(NINIT):
                g = GaussianMixture(4, covariance_type="full", init_params=init, n_init=1, random_state=i, max_iter=300).fit(X)
                res.append(dict(init=init, ll=g.score(X) * len(X), ari=adjusted_rand_score(y, g.predict(X))))
        for i in range(20):
            g = GaussianMixture(4, covariance_type="full", init_params="kmeans", n_init=10, random_state=1000 + i, max_iter=300).fit(X)
            res.append(dict(init="kmeans10", ll=g.score(X) * len(X), ari=adjusted_rand_score(y, g.predict(X))))
        R = pd.DataFrame(res); best = R.ll.max()
        R["gap"] = best - R.ll; R["other"] = R.gap > 1
        if s == 3.0 and k == 0: ex = (X, y, R.copy())
        for init, d in R.groupby("init"):
            rows.append(dict(sep=s, set=k, init=init, other=d.other.mean(), ari=d.ari.mean(), ari_best=R.loc[R.ll.idxmax(), "ari"], gap_max=d.gap.max()))
D = pd.DataFrame(rows); D.to_csv(RES / "by_set.csv", index=False, float_format="%.5f")
S = D.groupby(["sep", "init"]).agg(other=("other", "mean"), ari=("ari", "mean"), gap_max=("gap_max", "max")).reset_index()
S.to_csv(RES / "summary.csv", index=False)
g = lambda s, i, k: float(S[(S.sep == s) & (S.init == i)][k].iloc[0])
out = {"points": 4 * NPER, "inits_per_set": NINIT, "sets_per_sep": NSET,
       "by_sep": {str(s): {i: {"other": round(g(s, i, "other"), 3), "ari": round(g(s, i, "ari"), 3)} for i in ["random_from_data", "kmeans", "kmeans10"]} for s in SEPS}}
for s in SEPS:
    out[f"other_random_s{int(s)}"] = g(s, "random_from_data", "other"); out[f"other_kmeans_s{int(s)}"] = g(s, "kmeans", "other"); out[f"other_kmeans10_s{int(s)}"] = g(s, "kmeans10", "other")
json.dump(out, open(RES / "a779_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：別の答えになる割合
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(SEPS)); w = .27
for j, (i, l, c) in enumerate([("random_from_data", "乱数で選んだ点を初期値", ORANGE), ("kmeans", "k-means の初期値", BLUE), ("kmeans10", "k-means で10回して最もよいもの", GREEN)]):
    v = [g(s, i, "other") * 100 for s in SEPS]; b = ax.bar(x + (j - 1) * w, v, w, color=c, label=l)
    for bb, vv in zip(b, v): ax.text(bb.get_x() + w / 2, vv + 1, f"{vv:.0f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([f"間隔 {s:g}" for s in SEPS]); ax.set_xlabel("まとまりの中心の間隔（大きいほど重なりが小さい）")
ax.set_ylabel("最もよい答えと別の答えになった割合（%）"); ax.legend(frameon=False); ax.set_ylim(0, 100)
ax.set_title("重なりが大きいほど、初期値で答えが変わる")
save(fig, "a779_other.png", SRC)
# 図2：対数尤度の差の分布（間隔3の1組）
X, y, R = ex
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(0, max(R.gap.max(), 5), 40)
for i, l, c in [("random_from_data", "乱数で選んだ点を初期値", ORANGE), ("kmeans", "k-means の初期値", BLUE)]:
    ax.hist(R[R.init == i].gap, bins=bins, color=c, alpha=.55, label=l)
ax.axvline(1, color="black", ls="--", lw=1); ax.text(1.1, ax.get_ylim()[1] * .9, "差1（別の答えとする境目）", fontsize=9)
ax.set_xlabel("最もよい対数尤度との差"); ax.set_ylabel("回数（120通りの初期値）"); ax.legend(frameon=False)
ax.set_title("間隔3の1組：初期値ごとに、たどり着く答えがばらばら")
save(fig, "a779_gap.png", SRC)
# 図3：よい答えと悪い答えの例
fig, axs = plt.subplots(1, 2, figsize=(10, 4.6), sharex=True, sharey=True)
best_i = int(R[R.init == "random_from_data"].ll.idxmax()); worst_i = int(R[R.init == "random_from_data"].ll.idxmin())
for ax, ii, t in [(axs[0], best_i, "最もよい答え"), (axs[1], worst_i, "最も悪い答え")]:
    seed = ii if ii < NINIT else ii - NINIT
    gm = GaussianMixture(4, covariance_type="full", init_params="random_from_data", n_init=1, random_state=seed, max_iter=300).fit(X)
    lab = gm.predict(X)
    ax.scatter(X[:, 0], X[:, 1], c=lab, cmap="tab10", s=6)
    ax.set_title(f"{t}（ARI {adjusted_rand_score(y, lab):.2f}）", fontsize=11)
fig.suptitle("同じデータ・同じ成分の数でも、初期値で分け方が変わる（乱数で選んだ点を初期値）", y=1.02)
save(fig, "a779_example.png", SRC, y=-0.04)
print(json.dumps(out, ensure_ascii=False, indent=1))
