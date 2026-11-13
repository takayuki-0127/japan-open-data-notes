"""687 勾配ブースティングの学習率を大きくすると、木の数を合わせても成績はどれだけ変わるのか

架空のデータ：Friedman の式（y = 10 sin(π x1 x2) + 20 (x3-0.5)^2 + 10 x4 + 5 x5 + 誤差、x6〜x10 は効かない）。
学習用1,000件・確かめ用5,000件。誤差の標準偏差は1（誤差だけの下限は二乗誤差1.0）。
GradientBoostingRegressor（深さ3、行の8割で学習）を学習率0.3・0.1・0.03で木を1,500本まで育て、
木の本数ごとの確かめ用の誤差を記録する。さらに、学習用の1割を取り分けて「20本よくならなければ止める」
早めの打ち切りも試す。各10回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空のデータ（Friedman の式、作成者が乱数で作成、seed 687）"
rng = np.random.default_rng(687)
N, NT, REPS, T = 1000, 5000, 10, 1500
LRS = [0.3, 0.1, 0.03]


def draw(n):
    X = rng.uniform(0, 1, (n, 10))
    y = 10 * np.sin(np.pi * X[:, 0] * X[:, 1]) + 20 * (X[:, 2] - 0.5) ** 2 + 10 * X[:, 3] + 5 * X[:, 4] + rng.normal(0, 1, n)
    return X, y


curves = {lr: np.zeros(T) for lr in LRS}
rows, es_rows = [], []
for r in range(REPS):
    X, y = draw(N); Xt, yt = draw(NT)
    seed = int(rng.integers(1e9))
    for lr in LRS:
        m = GradientBoostingRegressor(learning_rate=lr, n_estimators=T, max_depth=3, subsample=0.8, random_state=seed).fit(X, y)
        err = np.array([np.mean((p - yt) ** 2) for p in m.staged_predict(Xt)])
        curves[lr] += err / REPS
        rows.append({"rep": r, "lr": lr, "best_mse": err.min(), "best_trees": int(err.argmin() + 1),
                     "mse_100": err[99], "mse_300": err[299], "mse_1500": err[-1]})
        es = GradientBoostingRegressor(learning_rate=lr, n_estimators=T, max_depth=3, subsample=0.8, random_state=seed,
                                       validation_fraction=0.1, n_iter_no_change=20).fit(X, y)
        es_rows.append({"rep": r, "lr": lr, "trees": int(es.n_estimators_), "mse": float(np.mean((es.predict(Xt) - yt) ** 2))})
D = pd.DataFrame(rows); E = pd.DataFrame(es_rows)
D.to_csv(RES / "reps.csv", index=False, float_format="%.5g"); E.to_csv(RES / "early_stopping.csv", index=False, float_format="%.5g")
pd.DataFrame({f"lr_{lr}": curves[lr] for lr in LRS}, index=pd.RangeIndex(1, T + 1, name="trees")).to_csv(RES / "curves.csv", float_format="%.5g")
S = D.groupby("lr").mean().drop(columns="rep"); SE = E.groupby("lr").mean().drop(columns="rep")
out = {"n_train": N, "n_test": NT, "reps": REPS, "max_trees": T,
       "by_lr": {str(lr): {"best_mse": round(S.loc[lr, "best_mse"], 3), "best_trees": round(S.loc[lr, "best_trees"]),
                            "mse_100": round(S.loc[lr, "mse_100"], 3), "mse_300": round(S.loc[lr, "mse_300"], 3),
                            "mse_1500": round(S.loc[lr, "mse_1500"], 3),
                            "early_stop_trees": round(SE.loc[lr, "trees"]), "early_stop_mse": round(SE.loc[lr, "mse"], 3)} for lr in LRS},
       "noise_floor": 1.0}
json.dump(out, open(RES / "a687_main.json", "w"), ensure_ascii=False, indent=1)

cols = {0.3: ORANGE, 0.1: BLUE, 0.03: GREEN}
# 図1：木の本数と誤差
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for lr in LRS:
    ax.plot(np.arange(1, T + 1), curves[lr], color=cols[lr], lw=2, label=f"学習率 {lr}")
    b = int(np.argmin(curves[lr])); ax.scatter(b + 1, curves[lr][b], color=cols[lr], zorder=3)
ax.set_xscale("log"); ax.set_ylim(1, 6); ax.axhline(1.0, color=INK, ls="--", lw=0.8)
ax.set_xlabel("木の本数（対数の目盛り）"); ax.set_ylabel("確かめ用の二乗誤差（10回の平均）"); ax.legend(frameon=False)
ax.set_title("学習率が小さいほど、たくさんの木が要るが、いちばん低い所はより低い")
save(fig, "a687_curves.png", SRC)

# 図2：いちばん良い誤差と、そのときの木の本数
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"wspace": 0.35})
xl = [f"学習率\n{lr}" for lr in LRS]
v = [S.loc[lr, "best_mse"] for lr in LRS]; t = [S.loc[lr, "best_trees"] for lr in LRS]
ax[0].bar(xl, v, color=[cols[lr] for lr in LRS]); [ax[0].text(i, v[i], f"{v[i]:.2f}", ha="center", va="bottom") for i in range(3)]
ax[0].set_ylim(1, max(v) * 1.15); ax[0].set_title("いちばん良いときの誤差", fontsize=11)
ax[1].bar(xl, t, color=[cols[lr] for lr in LRS]); [ax[1].text(i, t[i], f"{t[i]:.0f}本", ha="center", va="bottom") for i in range(3)]
ax[1].set_title("そのときの木の本数（平均）", fontsize=11)
save(fig, "a687_best.png", SRC, y=-0.04)

# 図3：木の本数を固定した場合と早めの打ち切り
fig, ax = plt.subplots(figsize=(8.5, 3.8))
lab = ["100本で固定", "300本で固定", "1,500本で固定", "早めの打ち切り"]
xi = np.arange(4); w = 0.26
for k, lr in enumerate(LRS):
    vals = [S.loc[lr, "mse_100"], S.loc[lr, "mse_300"], S.loc[lr, "mse_1500"], SE.loc[lr, "mse"]]
    ax.bar(xi + (k - 1) * w, vals, w, color=cols[lr], label=f"学習率 {lr}")
    for i, vv in enumerate(vals):
        ax.text(i + (k - 1) * w, vv, f"{vv:.2f}", ha="center", va="bottom", fontsize=7.5)
ax.set_xticks(xi); ax.set_xticklabels(lab); ax.set_ylabel("確かめ用の二乗誤差"); ax.set_ylim(0, None)
ax.legend(frameon=False, fontsize=9); ax.set_title("木の本数を決め打ちすると、学習率ごとに当たり外れが大きい")
save(fig, "a687_fixed_trees.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
