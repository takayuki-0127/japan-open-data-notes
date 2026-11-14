"""730 階層クラスタリングのつなぎ方（最短・最長・群平均・ウォード）で、本当のまとまりを何%で当てるのか

架空の店300店の2つの指標（標準化した値）。本当のまとまりは3つ：
  A：細長いまとまり（120店、横に長い）
  B：小さく詰まったまとまり（60店）
  C：大きく広がったまとまり（120店）
階層クラスタリング（最短距離法・最長距離法・群平均法・ウォード法）と k-means で3つに分け、
本当のまとまりとの一致を ARI（調整ランド指数、1 が完全一致、0 は偶然と同じ）で測る。
「ほぼ当てた」は ARI 0.9 以上とする。5店以下の小さなまとまりができた回も数える。300回くり返す。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の300店の2つの指標（作成者が乱数で作成、seed 730）"
rng = np.random.default_rng(730)
METHODS = [("single", "最短距離法"), ("complete", "最長距離法"), ("average", "群平均法"), ("ward", "ウォード法"), ("kmeans", "k-means")]


def make():
    a = np.column_stack([rng.normal(0, 2.2, 120), rng.normal(0, 0.35, 120)])
    b = np.column_stack([rng.normal(1.0, 0.3, 60), rng.normal(3.0, 0.3, 60)])
    c = np.column_stack([rng.normal(6.5, 1.1, 120), rng.normal(2.5, 1.1, 120)])
    X = np.vstack([a, b, c]); y = np.repeat([0, 1, 2], [120, 60, 120])
    return X, y


def cluster(X, m):
    if m == "kmeans": return KMeans(3, n_init=10, random_state=0).fit_predict(X)
    return fcluster(linkage(X, method=m), 3, criterion="maxclust")


REPS = 300
rows = []
for r in range(REPS):
    X, y = make()
    for m, _ in METHODS:
        lb = cluster(X, m); sizes = np.bincount(lb)[np.bincount(lb) > 0]
        rows.append({"rep": r, "method": m, "ari": adjusted_rand_score(y, lb), "min_size": int(sizes.min())})
R = pd.DataFrame(rows); R.round(4).to_csv(RES / "reps.csv", index=False)
S = R.groupby("method", sort=False).agg(ari_mean=("ari", "mean"), ari_median=("ari", "median"),
                                        hit_pct=("ari", lambda v: (v >= 0.9).mean() * 100),
                                        tiny_pct=("min_size", lambda v: (v <= 5).mean() * 100)).reset_index()
S.round(3).to_csv(RES / "summary.csv", index=False)

out = {"stores": 300, "reps": REPS, "hit_rule": "ARI>=0.9", "tiny_rule": "smallest cluster <= 5",
       "by_method": {r.method: {"ari_mean": round(r.ari_mean, 3), "hit_pct": round(r.hit_pct, 1), "tiny_cluster_pct": round(r.tiny_pct, 1)} for r in S.itertuples()}}
json.dump(out, open(RES / "a730_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1つのデータでの分け方
X, y = make(); cols = np.array([BLUE, GREEN, ORANGE, GRAY])
fig, axes = plt.subplots(1, 6, figsize=(16, 3.0), sharex=True, sharey=True)
axes[0].scatter(X[:, 0], X[:, 1], c=cols[y], s=5); axes[0].set_title("本当のまとまり", fontsize=10)
for ax, (m, nm) in zip(axes[1:], METHODS):
    lb = cluster(X, m)
    # 色：それぞれの組を、いちばん多く重なる本当のまとまりの色にする。同じ色を取り合ったら大きい組だけ、残りは灰色
    ks = sorted(np.unique(lb), key=lambda k: -np.sum(lb == k)); taken = set(); cmap = {}
    for k in ks:
        t = int(np.bincount(y[lb == k], minlength=3).argmax()); cmap[k] = 3 if t in taken else t; taken.add(t)
    cc = [cmap[k] for k in lb]
    ax.scatter(X[:, 0], X[:, 1], c=cols[np.array(cc)], s=5)
    ax.set_title(f"{nm}\nARI {adjusted_rand_score(y, lb):.2f}", fontsize=10)
for ax in axes: ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("同じデータでも、つなぎ方で分け方が大きく変わる（灰色は本当のまとまりと対応しない組）", y=1.08)
save(fig, "a730_example.png", SRC, y=-0.03)

# 図2：ARI の平均と「ほぼ当てた」割合
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6)); names = [nm for _, nm in METHODS]
axes[0].bar(names, S.ari_mean, color=[ORANGE, GRAY, GRAY, BLUE, GREEN])
for i, v in enumerate(S.ari_mean): axes[0].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
axes[0].set_ylabel("ARI の平均"); axes[0].set_ylim(0, 1.1); axes[0].tick_params(axis="x", labelsize=9)
axes[1].bar(names, S.hit_pct, color=[ORANGE, GRAY, GRAY, BLUE, GREEN])
for i, v in enumerate(S.hit_pct): axes[1].text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
axes[1].set_ylabel("ARI 0.9 以上の割合（%）"); axes[1].set_ylim(0, 110); axes[1].tick_params(axis="x", labelsize=9)
fig.suptitle(f"本当のまとまりを当てた度合い（{REPS}回）", y=1.02)
save(fig, "a730_ari.png", SRC)

# 図3：小さなまとまりができた割合
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(names, S.tiny_pct, color=[ORANGE, GRAY, GRAY, BLUE, GREEN])
for i, v in enumerate(S.tiny_pct): ax.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
ax.set_ylabel("5店以下のまとまりができた回（%）"); ax.set_ylim(0, 110)
ax.set_title("最短距離法は、はずれた数店だけのまとまりを作りやすい")
save(fig, "a730_tiny.png", SRC)
print(json.dumps(out, ensure_ascii=False))
