"""710 効かない変数を足していくと、k近傍法の当たり方はどれだけ落ちるのか

2クラスの分類。効く変数は2つ（x1, x2。クラスは x1²+x2² が中央値より大きいかで決まり、10%のラベルを入れ替える）。
効かない変数（クラスと無関係な正規乱数）を0〜50個足す。変数の単位（標準偏差）は0.5〜5でばらばら。
k近傍法（k=15）を 1) そのまま 2) 標準化してから 3) 学習データで効く変数を2つ選んでから（相互情報量。関係が曲がっているので F 検定では選べない）の3通りで、
学習1,000件・テスト2,000件、各10回の正解率を比べる。最も近い点と最も遠い点の距離の比も見る。seed 710。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from sklearn.pipeline import make_pipeline
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 710）"
rng = np.random.default_rng(710)
NOISE = [0, 2, 5, 10, 20, 50]
NTR, NTE, REPS, K = 1000, 2000, 10, 15


def gen(n, d, scales):
    s = rng.normal(0, 1, (n, 2))
    r = (s ** 2).sum(1)
    y = (r > 1.386).astype(int)  # χ²(2) の中央値
    flip = rng.random(n) < 0.10; y[flip] = 1 - y[flip]
    z = rng.normal(0, 1, (n, d))
    X = np.hstack([s, z]) * scales
    return X, y


rows = []
ratio = []
for d in NOISE:
    for r in range(REPS):
        scales = rng.uniform(0.5, 5, 2 + d)
        Xtr, ytr = gen(NTR, d, scales); Xte, yte = gen(NTE, d, scales)
        rec = {"noise_vars": d, "rep": r}
        models = {"raw": KNeighborsClassifier(K), "std": make_pipeline(StandardScaler(), KNeighborsClassifier(K)),
                  "select": make_pipeline(StandardScaler(), SelectKBest(lambda X, y: mutual_info_classif(X, y, random_state=0), k=2), KNeighborsClassifier(K))}
        for nm, m in models.items():
            m.fit(Xtr, ytr); rec[nm] = float((m.predict(Xte) == yte).mean() * 100)
        rows.append(rec)
        if r == 0:
            Z = StandardScaler().fit(Xtr).transform(Xte[:300])
            D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)); np.fill_diagonal(D, np.nan)
            ratio.append({"noise_vars": d, "near_far_ratio": float(np.nanmean(np.nanmin(D, 1) / np.nanmax(D, 1)))})
R = pd.DataFrame(rows); R.round(3).to_csv(RES / "reps.csv", index=False)
S = R.groupby("noise_vars")[["raw", "std", "select"]].mean().round(2)
S = S.join(pd.DataFrame(ratio).set_index("noise_vars").round(3))
S.to_csv(RES / "summary.csv")
out = {"train": NTR, "test": NTE, "reps": REPS, "k": K, "label_noise_pct": 10, "best_possible_accuracy_pct": 90,
       "by_noise_vars": {str(k): v for k, v in S.to_dict(orient="index").items()}}
json.dump(out, open(RES / "a710_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：正解率
fig, ax = plt.subplots(figsize=(8, 3.8))
for c, col, lab in [("raw", ORANGE, "そのまま"), ("std", BLUE, "標準化してから"), ("select", GREEN, "効く変数を2つ選んでから")]:
    ax.plot(S.index, S[c], "o-", color=col, label=lab)
ax.axhline(90, color=GRAY, lw=0.8, ls="--"); ax.axhline(50, color=GRAY, lw=0.8, ls=":")
ax.set_xlabel("足した効かない変数の数"); ax.set_ylabel("テストの正解率（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("効かない変数を足すほど、k近傍法の正解率は当て推量（50%）に近づく")
save(fig, "a710_accuracy.png", SRC)
# 図2：距離の比
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(S.index, S.near_far_ratio, "o-", color=BLUE)
ax.set_xlabel("足した効かない変数の数"); ax.set_ylabel("最も近い点の距離 ÷ 最も遠い点の距離")
ax.set_title("変数が増えると、「近い点」と「遠い点」の距離の差が縮む（標準化したテスト300件）")
save(fig, "a710_distance.png", SRC)
# 図3：例：効く2変数の散布図
Xs, ys = gen(1000, 0, np.ones(2))
fig, ax = plt.subplots(figsize=(5.5, 4.5))
ax.scatter(Xs[ys == 0, 0], Xs[ys == 0, 1], s=6, color=BLUE, label="クラス0")
ax.scatter(Xs[ys == 1, 0], Xs[ys == 1, 1], s=6, color=ORANGE, label="クラス1")
ax.set_xlabel("効く変数 x1"); ax.set_ylabel("効く変数 x2"); ax.legend(frameon=False, fontsize=9)
ax.set_title("正解の形：中心からの距離でクラスが決まる（10%は入れ替え）", fontsize=11)
save(fig, "a710_truth.png", SRC)
print(S.to_string())
