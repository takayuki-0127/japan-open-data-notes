"""639 k-means の k をエルボーとシルエットで選ぶと、本当のまとまりの数を何%で当てるのか

本当のまとまりの数 K（2〜6）が分かっている架空のデータ（2次元、300件、各まとまりは標準偏差1の丸い正規分布）で、
k=1〜8 の k-means を当て、
  EL エルボー（k に対する群内平方和の曲線で、両端を結んだ直線からいちばん離れた点）
  SI シルエット（平均シルエット係数が最大の k、k=2〜8）
  GP ギャップ統計量（一様な乱数データ5組と比べ、gap(k) >= gap(k+1) − s(k+1) となる最小の k）
で k を選び、本当の K と一致する割合を数える。まとまりの中心どうしの最小距離（離れ方）を 2.5・4・6 に変える。各条件40回。
数字は置いたまとまりの数・離れ方・件数で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 639）"
rng = np.random.default_rng(639)
N, KMAX, REPS, B = 300, 8, 40, 5


def centers(K, sep):
    side = sep * (1.2 + 0.6 * K)
    while True:
        c = rng.uniform(0, side, (K, 2))
        d = np.sqrt(((c[:, None] - c[None]) ** 2).sum(-1))[np.triu_indices(K, 1)]
        if d.min() >= sep and d.min() <= sep * 1.3:
            return c


def draw(K, sep):
    c = centers(K, sep)
    lab = rng.integers(0, K, N)
    return c[lab] + rng.standard_normal((N, 2)), lab


def inertia(X, k, seed, n_init=3):
    return KMeans(k, n_init=n_init, random_state=seed).fit(X)


def choose(X, seed):
    W, sil = [], {}
    for k in range(1, KMAX + 1):
        m = inertia(X, k, seed)
        W.append(m.inertia_)
        if k >= 2:
            sil[k] = silhouette_score(X, m.labels_)
    W = np.array(W); ks = np.arange(1, KMAX + 1)
    # エルボー：正規化した曲線で、端を結ぶ直線から最も離れた点
    x = (ks - 1) / (KMAX - 1); y = (W - W.min()) / (W.max() - W.min())
    el = int(ks[np.argmax((1 - x) - y)])
    si = int(max(sil, key=sil.get))
    # ギャップ統計量
    lo, hi = X.min(0), X.max(0)
    Wr = np.zeros((B, KMAX))
    for b in range(B):
        R = rng.uniform(lo, hi, X.shape)
        for k in ks:
            Wr[b, k - 1] = inertia(R, int(k), seed + b, n_init=1).inertia_
    lw = np.log(Wr); gap = lw.mean(0) - np.log(W); sk = lw.std(0) * np.sqrt(1 + 1 / B)
    gp = KMAX
    for k in range(1, KMAX):
        if gap[k - 1] >= gap[k] - sk[k]:
            gp = k
            break
    return {"EL": el, "SI": si, "GP": gp}, W, sil


rows = []
for sep in [2.5, 4.0, 6.0]:
    for K in range(2, 7):
        for r in range(REPS):
            X, _ = draw(K, sep)
            c, _, _ = choose(X, r)
            rows.append({"sep": sep, "K": K, "rep": r, **c})
D = pd.DataFrame(rows); D.to_csv(RES / "choices.csv", index=False)
M = ["EL", "SI", "GP"]
hit = D.groupby(["sep", "K"]).apply(lambda g: pd.Series({m: (g[m] == g.K).mean() * 100 for m in M})).round(1)
med = D.groupby(["sep", "K"])[M].median()
hit.to_csv(RES / "hit_rate.csv"); med.to_csv(RES / "median_choice.csv")
avg = D.assign(**{f"hit_{m}": D[m] == D.K for m in M}).groupby("sep")[[f"hit_{m}" for m in M]].mean().mul(100).round(1)
avg.to_csv(RES / "hit_rate_by_sep.csv")
under = D.assign(**{f"under_{m}": D[m] < D.K for m in M}).groupby("sep")[[f"under_{m}" for m in M]].mean().mul(100).round(1)
over = D.assign(**{f"over_{m}": D[m] > D.K for m in M}).groupby("sep")[[f"over_{m}" for m in M]].mean().mul(100).round(1)
out = {"n": N, "kmax": KMAX, "reps": REPS, "gap_refs": B,
       "hit_by_sep": avg.to_dict(orient="index"), "under_by_sep": under.to_dict(orient="index"),
       "over_by_sep": over.to_dict(orient="index"),
       "hit": {str(k): v for k, v in hit.reset_index().set_index(["sep", "K"]).to_dict(orient="index").items()}}

lab = {"EL": "エルボー", "SI": "シルエット", "GP": "ギャップ統計量"}
col = {"EL": ORANGE, "SI": BLUE, "GP": GREEN}
# 図1：離れ方ごとの当たる割合（K=2〜6 の平均）
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(3); w = 0.26
for i, m in enumerate(M):
    v = avg[f"hit_{m}"].values
    ax.bar(x + (i - 1) * w, v, w, color=col[m], label=lab[m])
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 1) * w, vi, f"{vi:.0f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(["近い（中心の距離2.5）", "中くらい（4）", "離れている（6）"])
ax.set_ylabel("本当の数を当てた割合（%）"); ax.set_ylim(0, 110); ax.legend(frameon=False, ncol=3, fontsize=9)
ax.set_title("まとまりの離れ方と、3つの決め方の当たる割合（K=2〜6、各40回）")
save(fig, "a639_hit_by_sep.png", SRC)

# 図2：本当の数ごとの当たる割合（中くらい）
fig, ax = plt.subplots(1, 3, figsize=(11, 3.7), sharey=True, gridspec_kw={"wspace": 0.12})
for a_, sep in zip(ax, [2.5, 4.0, 6.0]):
    for m in M:
        a_.plot(range(2, 7), hit.loc[sep][m].values, marker="o", color=col[m], label=lab[m])
    a_.set_title(f"中心の距離 {sep}", fontsize=11); a_.set_xlabel("本当のまとまりの数"); a_.set_xticks(range(2, 7)); a_.set_ylim(-5, 105)
ax[0].set_ylabel("当てた割合（%）"); ax[0].legend(frameon=False, fontsize=8)
save(fig, "a639_hit_by_k.png", SRC, y=-0.06)

# 図3：例（K=4、距離4）のデータとエルボー・シルエット
X, labx = draw(4, 4.0)
c, W, sil = choose(X, 999)
out["example"] = {"K": 4, "sep": 4.0, **c, "silhouette": {int(k): round(float(v), 3) for k, v in sil.items()}}
fig, ax = plt.subplots(1, 3, figsize=(12, 3.7), gridspec_kw={"wspace": 0.35})
ax[0].scatter(X[:, 0], X[:, 1], c=[[BLUE, ORANGE, GREEN, GRAY][l] for l in labx], s=8)
ax[0].set_title("例：本当は4つ（中心の距離4）", fontsize=11); ax[0].set_aspect("equal")
ax[1].plot(range(1, KMAX + 1), W, marker="o", color=ORANGE); ax[1].axvline(c["EL"], color=ORANGE, ls="--", lw=1)
ax[1].set_title(f"群内平方和（エルボーは k={c['EL']}）", fontsize=11); ax[1].set_xlabel("k")
ax[2].plot(list(sil), list(sil.values()), marker="o", color=BLUE); ax[2].axvline(c["SI"], color=BLUE, ls="--", lw=1)
ax[2].set_title(f"平均シルエット（最大は k={c['SI']}）", fontsize=11); ax[2].set_xlabel("k")
save(fig, "a639_example.png", SRC, y=-0.06)
json.dump(out, open(RES / "a639_main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
