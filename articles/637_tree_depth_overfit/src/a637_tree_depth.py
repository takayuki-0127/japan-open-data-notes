"""637 決定木の深さを増やすと、学習のデータと新しいデータの成績はどこで分かれるのか

本当の関係が分かっている架空のデータ（説明変数5つ、効くのは2つ。y = 本当の関数＋ノイズ、ノイズの分散1）で、
深さ1〜20の決定木を当て、学習のデータと新しいデータ（1万件）の二乗誤差を比べる。
学習の件数 200・1,000・5,000、各100回。5分割の交差検証で選んだ深さが、新しいデータでいちばん良い深さとどれだけずれるかも見る。
数字は置いた関数とノイズで決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import KFold
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 637）"
rng = np.random.default_rng(637)
DEPTHS = list(range(1, 21)); REPS = 100


def f(X):
    return 2 * np.sin(1.5 * X[:, 0]) + 1.5 * (X[:, 1] > 0.3) + 0.8 * X[:, 0] * X[:, 1]


def draw(n):
    X = rng.uniform(-2, 2, (n, 5))
    return X, f(X) + rng.standard_normal(n)


Xt = rng.uniform(-2, 2, (10000, 5)); mt = f(Xt)
rows, sel = [], []
for n in [200, 1000, 5000]:
    for r in range(REPS):
        X, y = draw(n)
        te = {}
        for d in DEPTHS:
            m = DecisionTreeRegressor(max_depth=d, random_state=0).fit(X, y)
            tr = float(np.mean((m.predict(X) - y) ** 2))
            te[d] = float(np.mean((m.predict(Xt) - mt) ** 2)) + 1.0      # 新しいデータの二乗誤差（ノイズ1を含む期待値）
            rows.append({"n": n, "rep": r, "depth": d, "train_mse": tr, "test_mse": te[d]})
        # 交差検証で深さを選ぶ
        cv = {d: 0.0 for d in DEPTHS}
        for a, b in KFold(5, shuffle=True, random_state=r).split(X):
            for d in DEPTHS:
                m = DecisionTreeRegressor(max_depth=d, random_state=0).fit(X[a], y[a])
                cv[d] += float(np.mean((m.predict(X[b]) - y[b]) ** 2)) / 5
        dcv = min(cv, key=cv.get); dbest = min(te, key=te.get)
        sel.append({"n": n, "rep": r, "best_depth": dbest, "cv_depth": dcv, "test_best": te[dbest], "test_cv": te[dcv],
                    "test_d20": te[20]})
D = pd.DataFrame(rows); E = pd.DataFrame(sel)
D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g"); E.to_csv(RES / "depth_choice.csv", index=False)
S = D.groupby(["n", "depth"])[["train_mse", "test_mse"]].mean().round(4)
S.to_csv(RES / "summary.csv")
best_mean = {n: int(S.loc[n].test_mse.idxmin()) for n in [200, 1000, 5000]}
out = {"reps": REPS, "noise_var": 1.0,
       "best_depth_of_mean_curve": best_mean,
       "test_at_best": {n: float(S.loc[(n, best_mean[n]), "test_mse"]) for n in best_mean},
       "test_at_depth20": {n: float(S.loc[(n, 20), "test_mse"]) for n in best_mean},
       "train_at_depth20": {n: float(S.loc[(n, 20), "train_mse"]) for n in best_mean},
       "test_at_depth1": {n: float(S.loc[(n, 1), "test_mse"]) for n in best_mean},
       "cv_choice": E.groupby("n").agg(best_depth_med=("best_depth", "median"), cv_depth_med=("cv_depth", "median"),
                                       cv_exact_pct=("cv_depth", lambda s: 0), test_best=("test_best", "mean"),
                                       test_cv=("test_cv", "mean"), test_d20=("test_d20", "mean")).round(4).to_dict(orient="index")}
for n in best_mean:
    e = E[E.n == n]
    out["cv_choice"][n]["cv_exact_pct"] = round(float((e.cv_depth == e.best_depth).mean() * 100), 1)
    out["cv_choice"][n]["cv_within1_pct"] = round(float(((e.cv_depth - e.best_depth).abs() <= 1).mean() * 100), 1)
    out["cv_choice"][n]["cv_extra_error_pct"] = round(float((e.test_cv / e.test_best - 1).mean() * 100), 2)
json.dump(out, open(RES / "a637_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1,000件での学習と新しいデータの誤差
s = S.loc[1000]
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(DEPTHS, s.train_mse, marker="o", color=BLUE, label="学習のデータ")
ax.plot(DEPTHS, s.test_mse, marker="s", color=ORANGE, label="新しいデータ")
ax.axhline(1.0, color=GRAY, ls=":", lw=1); ax.text(20, 1.03, "ノイズの分（これ以下にはならない）", ha="right", fontsize=8, color=GRAY)
b = best_mean[1000]; ax.axvline(b, color=GREEN, ls="--", lw=1); ax.text(b + 0.2, ax.get_ylim()[1] * 0.92, f"新しいデータで最良：深さ{b}", fontsize=9, color=GREEN)
ax.set_xticks(DEPTHS); ax.set_xlabel("決定木の深さ"); ax.set_ylabel("二乗誤差の平均"); ax.legend(frameon=False)
ax.set_title("学習1,000件：深くするほど学習の誤差は0へ、新しいデータの誤差は途中から増える")
save(fig, "a637_train_test.png", SRC)

# 図2：件数ごとの新しいデータの誤差
fig, ax = plt.subplots(figsize=(8.5, 4))
for n, c in zip([200, 1000, 5000], [ORANGE, BLUE, GREEN]):
    ax.plot(DEPTHS, S.loc[n].test_mse, marker="o", ms=4, color=c, label=f"学習{n:,}件（最良は深さ{best_mean[n]}）")
ax.axhline(1.0, color=GRAY, ls=":", lw=1)
ax.set_xticks(DEPTHS); ax.set_xlabel("決定木の深さ"); ax.set_ylabel("新しいデータの二乗誤差"); ax.legend(frameon=False, fontsize=9)
ax.set_title("件数が多いほど、深くしても崩れにくく、最良の深さも深くなる")
save(fig, "a637_by_n.png", SRC)

# 図3：交差検証で選んだ深さと、最良の深さ
fig, ax = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True, gridspec_kw={"wspace": 0.15})
for a_, n in zip(ax, [200, 1000, 5000]):
    e = E[E.n == n]
    a_.scatter(e.best_depth + rng.uniform(-0.2, 0.2, len(e)), e.cv_depth + rng.uniform(-0.2, 0.2, len(e)), s=12, color=BLUE, alpha=0.6)
    a_.plot([1, 20], [1, 20], color=GRAY, lw=0.8, ls="--")
    a_.set_title(f"学習{n:,}件：一致{out['cv_choice'][n]['cv_exact_pct']:.0f}%・±1で{out['cv_choice'][n]['cv_within1_pct']:.0f}%", fontsize=10)
    a_.set_xlabel("新しいデータで最良の深さ"); a_.set_xlim(0, 21); a_.set_ylim(0, 21)
ax[0].set_ylabel("交差検証で選んだ深さ")
save(fig, "a637_cv_choice.png", SRC, y=-0.08)
print(json.dumps(out, ensure_ascii=False, indent=1))
