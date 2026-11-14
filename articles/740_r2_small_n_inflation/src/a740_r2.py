"""740 件数が少ないとき、関係のない変数を入れた回帰の R² はどれだけ高く出るのか

架空の店のデータ。売上は、効く変数1つ（本当の R² を 0 または 0.2 に置く）と、関係のない変数で回帰する。
件数 n＝10〜500、変数の数 p＝1・3・5・8（効く変数を含む場合は1つ＋関係のない p−1 個）。
R²・自由度調整済み R²・5-fold の交差検証の R²（当てはめていないデータでの R²）を各1,000回で比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 740）"
rng = np.random.default_rng(740)
R = 1000
NS = [10, 15, 20, 30, 50, 100, 500]
PS = [1, 3, 5, 8]


def fit_r2(X, y):
    X1 = np.column_stack([np.ones(len(y)), X]); b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    e = y - X1 @ b; return 1 - e @ e / np.sum((y - y.mean()) ** 2)


def cv_r2(X, y, k=5):
    n = len(y); idx = rng.permutation(n); folds = np.array_split(idx, k); sse = 0
    for f in folds:
        tr = np.setdiff1d(idx, f)
        X1 = np.column_stack([np.ones(len(tr)), X[tr]]); b, *_ = np.linalg.lstsq(X1, y[tr], rcond=None)
        pred = np.column_stack([np.ones(len(f)), X[f]]) @ b; sse += np.sum((y[f] - pred) ** 2)
    return 1 - sse / np.sum((y - y.mean()) ** 2)


rows = []
for true_r2 in [0.0, 0.2]:
    for p in PS:
        for n in NS:
            if n <= p + 2:
                continue
            r2, ad, cv = [], [], []
            for r in range(R):
                X = rng.standard_normal((n, p))
                y = (np.sqrt(true_r2) * X[:, 0] + np.sqrt(1 - true_r2) * rng.standard_normal(n))
                v = fit_r2(X, y); r2.append(v); ad.append(1 - (1 - v) * (n - 1) / (n - p - 1)); cv.append(cv_r2(X, y))
            rows.append(dict(true_r2=true_r2, p=p, n=n, r2=np.mean(r2), adj=np.mean(ad), cv=np.median(cv),
                             r2_p90=np.quantile(r2, .9), r2_over_03=np.mean(np.array(r2) >= .3)))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
g = lambda t, p, n, c: float(S[(S.true_r2 == t) & (S.p == p) & (S.n == n)][c].iloc[0])
out = {"reps": R,
       "null_p5_n10_r2": g(0, 5, 10, "r2"), "null_p5_n20_r2": g(0, 5, 20, "r2"), "null_p5_n100_r2": g(0, 5, 100, "r2"),
       "null_p5_n10_adj": g(0, 5, 10, "adj"), "null_p5_n20_adj": g(0, 5, 20, "adj"),
       "null_p5_n20_cv_median": g(0, 5, 20, "cv"), "null_p8_n15_r2": g(0, 8, 15, "r2"),
       "null_p5_n20_r2_ge03": g(0, 5, 20, "r2_over_03"), "null_p5_n10_r2_ge03": g(0, 5, 10, "r2_over_03"),
       "null_p5_n20_r2_p90": g(0, 5, 20, "r2_p90"),
       "true02_p5_n20_r2": g(.2, 5, 20, "r2"), "true02_p5_n20_adj": g(.2, 5, 20, "adj"), "true02_p5_n20_cv": g(.2, 5, 20, "cv"),
       "true02_p5_n500_r2": g(.2, 5, 500, "r2"), "theory_null_p5_n20": 5 / 19}
json.dump(out, open(RES / "a740_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：関係のない変数だけ、件数と R²
fig, ax = plt.subplots(figsize=(9, 4.6))
for p, c in zip(PS, [LIGHT, BLUE, ORANGE, GREEN]):
    d = S[(S.true_r2 == 0) & (S.p == p)]; ax.plot(d.n, d.r2, "o-", color=c, label=f"変数{p}個")
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
ax.set_xlabel("件数（対数の目盛り）"); ax.set_ylabel("R²（1,000回の平均）"); ax.legend(frameon=False)
ax.set_title("どの変数も関係ないのに、件数が少ないと R² は高く出る")
save(fig, "a740_null_r2.png", SRC)

# 図2：3つの R²（関係なし、変数5個）
fig, ax = plt.subplots(figsize=(9, 4.6))
d = S[(S.true_r2 == 0) & (S.p == 5)]
ax.plot(d.n, d.r2, "o-", color=ORANGE, label="R²")
ax.plot(d.n, d.adj, "o-", color=BLUE, label="自由度調整済み R²")
ax.plot(d.n, d.cv, "o-", color=GREEN, label="交差検証の R²（中央値）")
ax.axhline(0, color=GRAY, lw=1)
ax.set_xscale("log"); ax.set_xticks(d.n); ax.set_xticklabels(d.n); ax.set_ylim(-1, .7)
ax.set_xlabel("件数（対数の目盛り）"); ax.set_ylabel("R²"); ax.legend(frameon=False)
ax.set_title("変数5個・関係なし：調整すると0前後、交差検証ではマイナス")
save(fig, "a740_three.png", SRC)

# 図3：本当の R² 0.2 のとき
fig, ax = plt.subplots(figsize=(9, 4.6))
d = S[(S.true_r2 == .2) & (S.p == 5)]
ax.plot(d.n, d.r2, "o-", color=ORANGE, label="R²")
ax.plot(d.n, d.adj, "o-", color=BLUE, label="自由度調整済み R²")
ax.plot(d.n, d.cv, "o-", color=GREEN, label="交差検証の R²（中央値）")
ax.axhline(.2, color=GRAY, ls="--", lw=1); ax.text(10, .22, "本当の R² 0.2", color=GRAY, fontsize=9)
ax.set_xscale("log"); ax.set_xticks(d.n); ax.set_xticklabels(d.n); ax.set_ylim(-1, .8)
ax.set_xlabel("件数（対数の目盛り）"); ax.set_ylabel("R²"); ax.legend(frameon=False, loc="lower right")
ax.set_title("効く変数1つ＋関係のない4つ：件数が少ないと実力より高く見える")
save(fig, "a740_true02.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
