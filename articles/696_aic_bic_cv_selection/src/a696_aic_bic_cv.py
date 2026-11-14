"""696 AIC・BIC・交差検証で回帰の変数を選ぶと、本当の変数を何%当てるのか

架空のデータ：候補の説明変数10個（どの2つも相関0.3）、本当に効くのは k 個（係数0.3、k = 2・4・6）、誤差の標準偏差1。
件数 n = 100・300・1,000。前向きの段階的選択（効きのいい変数を1つずつ足す）で、変数0〜10個のモデルの列を作り、
その中から AIC・BIC・5-fold の交差検証（予測の二乗誤差がいちばん小さいもの）で1つ選ぶ。
選んだ変数の組が本当の組とぴったり同じだった割合、効く変数をすべて含んだ割合、効かない変数の数を、各300回で数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 696）"
rng = np.random.default_rng(696)
P, RHO, BETA, REPS = 10, 0.3, 0.3, 300
NS, KS = [100, 300, 1000], [2, 4, 6]
L = np.linalg.cholesky(np.full((P, P), RHO) + np.eye(P) * (1 - RHO))


def rss(X, y, cols):
    Xc = np.column_stack([np.ones(len(y))] + [X[:, c] for c in cols])
    b, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    r = y - Xc @ b
    return r @ r, b


def forward(X, y):
    path, rest = [[]], list(range(P))
    while rest:
        best = min(rest, key=lambda c: rss(X, y, path[-1] + [c])[0])
        path.append(path[-1] + [best]); rest.remove(best)
    return path


def cv_err(X, y, cols, folds):
    e = 0.0
    for f in range(5):
        tr, te = folds != f, folds == f
        _, b = rss(X[tr], y[tr], cols)
        Xc = np.column_stack([np.ones(te.sum())] + [X[te][:, c] for c in cols])
        e += ((y[te] - Xc @ b) ** 2).sum()
    return e


rows = []
for k in KS:
    beta = np.r_[np.full(k, BETA), np.zeros(P - k)]
    true = set(range(k))
    for n in NS:
        for r in range(REPS):
            X = rng.normal(0, 1, (n, P)) @ L.T
            y = X @ beta + rng.normal(0, 1, n)
            path = forward(X, y)
            rs = np.array([rss(X, y, c)[0] for c in path]); m = np.arange(P + 1) + 1
            folds = rng.permutation(np.arange(n) % 5)
            choice = {"AIC": int(np.argmin(n * np.log(rs / n) + 2 * m)), "BIC": int(np.argmin(n * np.log(rs / n) + np.log(n) * m)),
                      "CV": int(np.argmin([cv_err(X, y, c, folds) for c in path]))}
            for meth, j in choice.items():
                sel = set(path[j])
                rows.append({"k": k, "n": n, "rep": r, "method": meth, "size": len(sel), "exact": int(sel == true),
                             "all_true": int(true <= sel), "n_false": len(sel - true), "n_missed": len(true - sel)})
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
S = D.groupby(["k", "n", "method"]).agg(exact=("exact", "mean"), all_true=("all_true", "mean"), n_false=("n_false", "mean"),
                                         n_missed=("n_missed", "mean"), size=("size", "mean")).reset_index()
S["exact"] *= 100; S["all_true"] *= 100
S.round(3).to_csv(RES / "summary.csv", index=False)
out = {"p": P, "rho": RHO, "beta": BETA, "reps": REPS,
       "summary": {f"k{k}_n{n}": {m: {c: round(float(S[(S.k == k) & (S.n == n) & (S.method == m)][c].iloc[0]), 2)
                                      for c in ["exact", "all_true", "n_false", "n_missed", "size"]} for m in ["AIC", "BIC", "CV"]}
                   for k in KS for n in NS}}
json.dump(out, open(RES / "a696_main.json", "w"), ensure_ascii=False, indent=1)
col = {"AIC": ORANGE, "BIC": BLUE, "CV": GREEN}

# 図1：ぴったり当てた割合（k=4）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(3); w = 0.27
for i, m in enumerate(["AIC", "BIC", "CV"]):
    v = [S[(S.k == 4) & (S.n == n) & (S.method == m)].exact.iloc[0] for n in NS]
    ax.bar(x + (i - 1) * w, v, w, color=col[m], label=m if m != "CV" else "交差検証")
    for j, vv in enumerate(v):
        ax.text(j + (i - 1) * w, vv, f"{vv:.0f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{n:,}件" for n in NS]); ax.set_ylabel("本当の組とぴったり同じだった割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False, loc="upper left"); ax.set_title("効く変数4個のとき：件数が増えると BIC はほぼ当て、AIC と交差検証は余分を足す")
save(fig, "a696_exact.png", SRC)

# 図2：効かない変数の数と、落とした効く変数の数（k=4）
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.3})
for i, m in enumerate(["AIC", "BIC", "CV"]):
    vf = [S[(S.k == 4) & (S.n == n) & (S.method == m)].n_false.iloc[0] for n in NS]
    vm = [S[(S.k == 4) & (S.n == n) & (S.method == m)].n_missed.iloc[0] for n in NS]
    ax[0].plot(NS, vf, color=col[m], marker="o", lw=2, label=m if m != "CV" else "交差検証")
    ax[1].plot(NS, vm, color=col[m], marker="o", lw=2)
for a_, t in zip(ax, ["選んだ効かない変数の数（平均）", "落とした効く変数の数（平均）"]):
    a_.set_xscale("log"); a_.set_xticks(NS); a_.set_xticklabels([f"{n:,}" for n in NS]); a_.set_xlabel("件数"); a_.set_title(t, fontsize=11)
ax[0].legend(frameon=False)
save(fig, "a696_false_missed.png", SRC, y=-0.06)

# 図3：効く変数の数ごと（n=300）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
for i, m in enumerate(["AIC", "BIC", "CV"]):
    v = [S[(S.k == k) & (S.n == 300) & (S.method == m)].exact.iloc[0] for k in KS]
    ax.bar(x + (i - 1) * w, v, w, color=col[m], label=m if m != "CV" else "交差検証")
    for j, vv in enumerate(v):
        ax.text(j + (i - 1) * w, vv, f"{vv:.0f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"効く変数 {k}個" for k in KS]); ax.set_ylabel("ぴったり同じだった割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False, loc="upper right"); ax.set_title("300件のとき：効かない変数が多いほど、AIC と交差検証は外しやすい")
save(fig, "a696_by_k.png", SRC)
print(json.dumps(out["summary"]["k4_n300"], ensure_ascii=False, indent=1))
