"""P04 Double/Debiased ML：機械学習で交絡を取るとき、交差適合（cross-fitting）がないと何が起きるか。
部分線形モデル Y = θD + 1.5h(X) + ε, D = h(X) + v（θ=0.5）を、種を固定して100回つくり、3つの推定を比べる。
使い方: cd src && python p04_dml.py
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
THETA, N, P, REPS = 0.5, 1000, 5, 100


def make(rng):
    X = rng.uniform(-1, 1, (N, P))
    h = np.sin(np.pi * X[:, 0]) + 1.5 * X[:, 1] ** 2 + X[:, 2] * X[:, 3]   # D と Y の両方に効く、曲がった交絡
    D = h + rng.normal(0, 1, N)
    Y = THETA * D + 1.5 * h + rng.normal(0, 1, N)
    return X, D, Y


def deep_rf(seed):
    # 葉に1件まで残す深いランダムフォレスト。学習に使ったデータはほぼ丸暗記する
    return RandomForestRegressor(n_estimators=100, min_samples_leaf=1, max_features=1.0, random_state=seed, n_jobs=1)


def rf(seed):
    # 勾配ブースティング（LightGBM）。木を少しずつ足して当てはめる機械学習
    return lgb.LGBMRegressor(n_estimators=200, num_leaves=15, learning_rate=0.05, min_child_samples=10,
                             subsample=0.8, subsample_freq=1, random_state=seed, num_threads=1, verbose=-1)


def resid_theta(ry, rd):
    th = np.sum(rd * ry) / np.sum(rd * rd)
    psi = (ry - th * rd) * rd
    se = np.sqrt(np.mean(psi ** 2) / np.mean(rd * rd) ** 2 / len(ry))
    return th, se


rows = []
for r in range(REPS):
    rng = np.random.default_rng(1000 + r)
    X, D, Y = make(rng)
    # 1. 線形回帰（X を1次で入れる。g と m の形が違うので偏る）
    Z = np.column_stack([np.ones(N), D, X])
    b, *_ = np.linalg.lstsq(Z, Y, rcond=None)
    res = Y - Z @ b
    XtX = np.linalg.inv(Z.T @ Z)
    se_ols = np.sqrt(np.sum(res ** 2) / (N - Z.shape[1]) * XtX[1, 1])
    rows.append({"rep": r, "method": "線形回帰", "theta": b[1], "se": se_ols})
    for name, learner in (("LightGBM", rf), ("深いランダムフォレスト", deep_rf)):
        # 2. 交差適合なし：同じデータで学習して、同じデータの残差を使う
        ly = learner(r).fit(X, Y).predict(X); md = learner(r + 7).fit(X, D).predict(X)
        th, se = resid_theta(Y - ly, D - md)
        rows.append({"rep": r, "method": f"{name}・交差適合なし", "theta": th, "se": se})
        # 3. DML：5分割の交差適合
        ry = np.empty(N); rd = np.empty(N)
        for k, (tr, te) in enumerate(KFold(5, shuffle=True, random_state=r).split(X)):
            ry[te] = Y[te] - learner(r * 10 + k).fit(X[tr], Y[tr]).predict(X[te])
            rd[te] = D[te] - learner(r * 10 + k + 5).fit(X[tr], D[tr]).predict(X[te])
        th, se = resid_theta(ry, rd)
        rows.append({"rep": r, "method": f"{name}・DML（5分割の交差適合）", "theta": th, "se": se})

df = pd.DataFrame(rows)
df["covered"] = (df.theta - 1.96 * df.se <= THETA) & (THETA <= df.theta + 1.96 * df.se)
df["z"] = (df.theta - THETA) / df.se
df.round(6).to_csv(R / "sims.csv", index=False, encoding="utf-8")
order = ["線形回帰", "LightGBM・交差適合なし", "LightGBM・DML（5分割の交差適合）", "深いランダムフォレスト・交差適合なし", "深いランダムフォレスト・DML（5分割の交差適合）"]
S = df.groupby("method").agg(mean_theta=("theta", "mean"), bias=("theta", lambda x: x.mean() - THETA),
                             sd=("theta", "std"), mean_se=("se", "mean"), coverage=("covered", "mean")).reindex(order)
S.round(4).to_csv(R / "summary.csv", encoding="utf-8")
json.dump({"theta_true": THETA, "n": N, "reps": REPS,
           **{m: {k: round(float(v), 4) for k, v in S.loc[m].items()} for m in order}},
          open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

fig, axs = plt.subplots(1, 5, figsize=(16, 3.8), dpi=120, sharey=True)
xs = np.linspace(-6, 6, 200)
for ax, m, c in zip(axs, order, ["#c0692b", "#8fa9c2", "#1f5f8b", "#b5452b", "#2e7d4f"]):
    z = df.loc[df.method == m, "z"].clip(-8, 8)
    ax.hist(z, bins=30, range=(-8, 8), density=True, color=c, alpha=.8)
    ax.plot(xs, np.exp(-xs ** 2 / 2) / np.sqrt(2 * np.pi), color="#333", lw=1)
    ax.axvline(0, color="#999", ls="--", lw=1)
    ax.set_title(f"{m.replace('・', chr(10))}\n偏り {S.loc[m, 'bias']:+.3f}・区間に入った {S.loc[m, 'coverage']:.0%}", fontsize=9)
    ax.set_xlabel("(推定値 − 真の値) ÷ 標準誤差")
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
fig.suptitle("真の効果 0.5 を100回推定。線形回帰の偏りは直交化で消えるが、学習器が弱いと交差適合しても偏りが残る", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "p04_01_dml_z.png"); plt.close(fig)
print(S.round(3))
