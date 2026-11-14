"""790 学習データを2倍にすると、テストの誤差はどれだけ減り、どこで頭打ちになるのか

架空のデータ。x は3つの一様乱数、y = sin(2x1)·2 + x2² + x1·x3 + ばらつき（sd 1）。ばらつきの分（誤差の下限）は1。
学習件数を50〜12,800と2倍ずつ増やし、線形回帰と決定木（葉の最小件数5）を学習して、
2万件のテストデータで二乗平均誤差（RMSE）を測る。各件数20回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 790）"
rng = np.random.default_rng(790)
NS = [50 * 2 ** i for i in range(9)]       # 50〜12,800
R = 20


def make(n):
    X = rng.uniform(-2, 2, (n, 3))
    f = 2 * np.sin(2 * X[:, 0]) + X[:, 1] ** 2 + X[:, 0] * X[:, 2]
    return X, f + rng.normal(0, 1, n), f


Xte, yte, fte = make(20000)
models = {"linear": lambda: LinearRegression(), "tree": lambda: DecisionTreeRegressor(min_samples_leaf=5, random_state=0)}
rows = []
for n in NS:
    for r in range(R):
        X, y, _ = make(n)
        row = dict(n=n, rep=r)
        for k, m in models.items():
            mm = m().fit(X, y); p = mm.predict(Xte)
            row[f"{k}_rmse"] = float(np.sqrt(np.mean((yte - p) ** 2))); row[f"{k}_train"] = float(np.sqrt(np.mean((y - mm.predict(X)) ** 2)))
        rows.append(row)
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv", index=False)
S = D.groupby("n").mean(numeric_only=True).drop(columns="rep").reset_index()
for k in models: S[f"{k}_drop"] = 1 - S[f"{k}_rmse"] / S[f"{k}_rmse"].shift(1)
S.to_csv(RES / "summary.csv", index=False)
g = lambda n, c: float(S[S.n == n][c].iloc[0])
best_lin = float(np.sqrt(np.mean((yte - LinearRegression().fit(*make(200000)[:2]).predict(Xte)) ** 2)))
out = {"ns": NS, "reps": R, "noise_floor": 1.0, "linear_limit": best_lin,
       "by_n": {str(n): {"linear": round(g(n, "linear_rmse"), 3), "tree": round(g(n, "tree_rmse"), 3)} for n in NS},
       "linear_50": g(50, "linear_rmse"), "linear_400": g(400, "linear_rmse"), "linear_12800": g(12800, "linear_rmse"),
       "tree_50": g(50, "tree_rmse"), "tree_400": g(400, "tree_rmse"), "tree_12800": g(12800, "tree_rmse"),
       "tree_drop_first": g(100, "tree_drop"), "tree_drop_last": g(12800, "tree_drop"),
       "linear_drop_after_400": [round(g(n, "linear_drop"), 4) for n in NS if n > 400],
       "cross_n": int(S[S.tree_rmse < S.linear_rmse].n.min())}
json.dump(out, open(RES / "a790_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：学習曲線
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for k, c, l in [("linear", ORANGE, "線形回帰"), ("tree", BLUE, "決定木")]:
    ax.plot(S.n, S[f"{k}_rmse"], "o-", color=c, label=f"{l}（テスト）"); ax.plot(S.n, S[f"{k}_train"], "o--", color=c, alpha=.5, label=f"{l}（学習データ）")
ax.axhline(1, color=GRAY, ls=":", lw=1); ax.text(NS[0], 1.02, "ばらつきの分（これ以上は下がらない）", fontsize=9, color=GRAY)
ax.axhline(best_lin, color=ORANGE, ls=":", lw=1); ax.text(NS[-1], best_lin + .02, f"線形回帰の限界 {best_lin:.2f}", fontsize=9, color=ORANGE, ha="right")
ax.set_xscale("log", base=2); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS], rotation=45)
ax.set_xlabel("学習データの件数"); ax.set_ylabel("誤差（RMSE）"); ax.legend(frameon=False, fontsize=9, ncol=2)
ax.set_title("線形回帰は200件ほどでほぼ頭打ち。決定木は件数を増やすほど下がり続ける（20回の平均）")
save(fig, "a790_curve.png", SRC)

# 図2：2倍にしたときに誤差が何%減るか
fig, ax = plt.subplots(figsize=(8.5, 4.4)); x = np.arange(1, len(NS)); w = .38
ax.bar(x - w / 2, S.linear_drop.iloc[1:] * 100, w, color=ORANGE, label="線形回帰")
ax.bar(x + w / 2, S.tree_drop.iloc[1:] * 100, w, color=BLUE, label="決定木")
ax.axhline(0, color=GRAY, lw=.8); ax.set_xticks(x); ax.set_xticklabels([f"{a:,}→{b:,}" for a, b in zip(NS[:-1], NS[1:])], rotation=45, fontsize=9)
ax.set_ylabel("2倍にしたときの誤差の減り（%）"); ax.legend(frameon=False)
ax.set_title("2倍にしたときの効き目は、件数が増えるほど小さくなる")
save(fig, "a790_drop.png", SRC)

# 図3：誤差のうち、ばらつき以外の分（減らせる分）
fig, ax = plt.subplots(figsize=(8.5, 4.4))
for k, c, l in [("linear", ORANGE, "線形回帰"), ("tree", BLUE, "決定木")]:
    ax.plot(S.n, np.sqrt(np.maximum(S[f"{k}_rmse"] ** 2 - 1, 0)), "o-", color=c, label=l)
ax.set_xscale("log", base=2); ax.set_yscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS], rotation=45)
ax.set_xlabel("学習データの件数"); ax.set_ylabel("ばらつきを除いた誤差（対数）"); ax.legend(frameon=False)
ax.set_title("ばらつきの分を除くと、決定木はほぼまっすぐ減り、線形回帰は平らになる")
save(fig, "a790_reducible.png", SRC)
print(S.round(3).to_string()); print(out["linear_limit"], out["cross_n"])
