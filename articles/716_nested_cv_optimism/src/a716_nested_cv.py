"""716 交差検証でハイパーパラメータを選び、同じ交差検証の成績を報告すると、本当の成績よりどれだけよく見えるのか

2クラスの分類。変数は50個で、効くのは3個だけ（クラスの平均が±0.3、差0.6）。モデルは「50個から5個の変数を選んで使う
最近傍重心法」（クラスごとの平均に近いほうに分ける）。候補（変数の組）を1・5・20・100個用意し、
  1) 5-fold の交差検証で最もよい候補を選び、その交差検証の正解率をそのまま報告
  2) 入れ子の交差検証（外5-fold・内5-fold）で、選び方ごと評価
  3) 選んだ候補を、別の大きなテストデータ（5,000件）で評価＝本当の正解率
を、件数100・400、各200回で比べる。最近傍重心法は numpy で書いた。seed 716。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 716）"
rng = np.random.default_rng(716)
P, K, EFF, NTEST, REPS = 50, 5, 0.3, 5000, 200
CANDS, NS = [1, 5, 20, 100], [100, 400]


def gen(n):
    y = rng.integers(0, 2, n)
    X = rng.normal(0, 1, (n, P)); X[:, :3] += EFF * (2 * y[:, None] - 1)  # 効く3個：クラス0は−0.3、クラス1は+0.3（平均の差0.6）
    return X, y


def acc(Xtr, ytr, Xte, yte, cols):
    """cols：(候補数, K) の変数の番号。候補ごとの正解率を返す"""
    m0 = Xtr[ytr == 0].mean(0); m1 = Xtr[ytr == 1].mean(0)
    a = []
    for c in cols:
        d0 = ((Xte[:, c] - m0[c]) ** 2).sum(1); d1 = ((Xte[:, c] - m1[c]) ** 2).sum(1)
        a.append(((d1 < d0).astype(int) == yte).mean())
    return np.array(a)


def cv_scores(X, y, cols, folds=5):
    idx = rng.permutation(len(y)); parts = np.array_split(idx, folds)
    s = np.zeros(len(cols))
    for k in range(folds):
        te = parts[k]; tr = np.concatenate([parts[j] for j in range(folds) if j != k])
        s += acc(X[tr], y[tr], X[te], y[te], cols) * len(te)
    return s / len(y)


Xt, yt = gen(NTEST)
rows = []
for n in NS:
    for C in CANDS:
        for r in range(REPS):
            cols = np.array([rng.choice(P, K, replace=False) for _ in range(C)])
            X, y = gen(n)
            sc = cv_scores(X, y, cols)
            best = int(np.argmax(sc))
            true_acc = acc(X, y, Xt, yt, cols[[best]])[0]
            # 入れ子：外の各 fold で、内の交差検証で選んで外の fold で評価
            idx = rng.permutation(n); parts = np.array_split(idx, 5); ns = 0.0
            for k in range(5):
                te = parts[k]; tr = np.concatenate([parts[j] for j in range(5) if j != k])
                b = int(np.argmax(cv_scores(X[tr], y[tr], cols)))
                ns += acc(X[tr], y[tr], X[te], y[te], cols[[b]])[0] * len(te)
            rows.append({"n": n, "candidates": C, "rep": r, "cv_best": sc[best] * 100, "nested": ns / n * 100, "true": true_acc * 100,
                         "best_has_signal": int(np.isin(cols[best], [0, 1, 2]).any())})
R = pd.DataFrame(rows); R.round(3).to_csv(RES / "reps.csv", index=False)
S = R.groupby(["n", "candidates"]).agg(cv_best=("cv_best", "mean"), nested=("nested", "mean"), true=("true", "mean"),
                                         best_has_signal_pct=("best_has_signal", "mean")).reset_index()
S["optimism_cv_pt"] = S.cv_best - S.true; S["optimism_nested_pt"] = S.nested - S.true
S["best_has_signal_pct"] *= 100
S.round(2).to_csv(RES / "summary.csv", index=False)
out = {"features": P, "used_per_candidate": K, "signal_features": 3, "test_size": NTEST, "reps": REPS,
       "cells": {f"n={int(r.n)},candidates={int(r.candidates)}": {k: round(float(r[k]), 2) for k in ["cv_best", "nested", "true", "optimism_cv_pt", "optimism_nested_pt", "best_has_signal_pct"]} for _, r in S.iterrows()}}
json.dump(out, open(RES / "a716_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：n=100 で候補の数ごと
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, n in zip(axs, NS):
    s = S[S.n == n]
    ax.plot(s.candidates, s.cv_best, "o-", color=ORANGE, label="選んだ交差検証の成績をそのまま")
    ax.plot(s.candidates, s.nested, "s-", color=BLUE, label="入れ子の交差検証")
    ax.plot(s.candidates, s.true, "^-", color="black", label="本当の成績（別のテスト）")
    ax.set_xscale("log"); ax.set_xticks(CANDS); ax.set_xticklabels(CANDS); ax.set_xlabel("候補の数"); ax.set_title(f"{n}件", fontsize=11)
axs[0].set_ylabel("正解率（%）"); axs[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("候補が多いほど、選んだ候補の交差検証の成績は本当よりよく見える", fontsize=13)
save(fig, "a716_by_candidates.png", SRC)
# 図2：甘さ（ポイント）
fig, ax = plt.subplots(figsize=(8, 3.6)); x = np.arange(len(CANDS)); w = 0.2
for i, n in enumerate(NS):
    s = S[S.n == n]
    ax.bar(x + (i * 2 - 1.5) * w, s.optimism_cv_pt, w, color=ORANGE if n == 100 else "#f3a47f", label=f"そのまま（{n}件）")
    ax.bar(x + (i * 2 - 0.5) * w, s.optimism_nested_pt, w, color=BLUE if n == 100 else LIGHT, label=f"入れ子（{n}件）")
ax.axhline(0, color="black", lw=0.6); ax.set_xticks(x); ax.set_xticklabels(CANDS); ax.set_xlabel("候補の数")
ax.set_ylabel("報告した成績 − 本当の成績（ポイント）"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title("入れ子の交差検証の甘さは、候補が100個でもほぼ0")
save(fig, "a716_optimism.png", SRC)
# 図3：n=100, 候補100 の散布
s = R[(R.n == 100) & (R.candidates == 100)]
fig, ax = plt.subplots(figsize=(6.5, 4.5))
ax.scatter(s.true, s.cv_best, s=12, color=ORANGE, label="そのまま")
ax.scatter(s.true, s.nested, s=12, color=BLUE, label="入れ子")
lim = [40, 85]; ax.plot(lim, lim, color=GRAY, lw=0.8); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("本当の成績（%）"); ax.set_ylabel("報告した成績（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("100件・候補100個の200回：そのままはほぼすべて線の上", fontsize=11)
save(fig, "a716_scatter.png", SRC)
print(S.round(2).to_string())
