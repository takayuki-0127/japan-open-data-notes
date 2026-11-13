"""647 回帰不連続で、境目のまわりの幅を変えると、効果の推定の偏りとばらつきはどう入れ替わるのか

架空のデータ：割り当てを決める点数 x は −1〜1 の一様（1,000件）、x≥0 なら施策あり。
結果 y = f(x) + 0.3·[x≥0] + ノイズ（標準偏差0.5）。f は曲がった関数（境目の近くで傾きが変わる）。
境目の両側で、幅 h の中のデータに三角カーネルの重みをつけて直線（局所線形）または2次式（局所2次）を当て、
境目での跳び（効果）を推定する。h = 0.05〜1.0。偏り・ばらつき・95%区間（頑健な標準誤差）の当たり方を各1,000回で数える。
数字は置いた関数・ノイズ・件数で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 647）"
rng = np.random.default_rng(647)
N, TAU, SIG, REPS = 1000, 0.3, 0.5, 1000
HS = [0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0]


def f(x):
    return 0.4 * x + 1.5 * x ** 2 + 0.8 * np.sin(3 * x)


def draw():
    x = rng.uniform(-1, 1, N)
    y = f(x) + TAU * (x >= 0) + rng.normal(0, SIG, N)
    return x, y


def side_fit(x, y, h, deg):
    """片側：幅 h の三角カーネルで重みづけした多項式。境目（x=0）での値とその分散（HC1）を返す"""
    w = np.clip(1 - np.abs(x) / h, 0, None)
    m = w > 0
    x, y, w = x[m], y[m], w[m]
    X = np.vander(x, deg + 1, increasing=True)
    if len(x) <= deg + 2:
        return np.nan, np.nan
    XtW = X.T * w
    A = np.linalg.inv(XtW @ X)
    b = A @ XtW @ y
    e = y - X @ b
    meat = (X.T * (w * e) ** 2) @ X
    V = A @ meat @ A * len(x) / (len(x) - deg - 1)
    return b[0], V[0, 0]


def rd(x, y, h, deg):
    a1, v1 = side_fit(x[x >= 0], y[x >= 0], h, deg)
    a0, v0 = side_fit(-x[x < 0], y[x < 0], h, deg)          # 左側は向きを返して当てる（境目での値は同じ）
    return a1 - a0, np.sqrt(v1 + v0)


rows = []
for r in range(REPS):
    x, y = draw()
    for deg in [1, 2]:
        for h in HS:
            est, se = rd(x, y, h, deg)
            rows.append({"rep": r, "deg": deg, "h": h, "est": est, "se": se, "n_used": int((np.abs(x) < h).sum())})
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
S = D.groupby(["deg", "h"]).apply(lambda g: pd.Series({
    "bias": g.est.mean() - TAU, "sd": g.est.std(), "rmse": np.sqrt(((g.est - TAU) ** 2).mean()),
    "coverage": ((g.est - 1.96 * g.se <= TAU) & (TAU <= g.est + 1.96 * g.se)).mean() * 100,
    "mean_se": g.se.mean(), "n_used": g.n_used.mean()})).round(4)
S.to_csv(RES / "summary.csv")
best = {int(d): float(S.loc[d].rmse.idxmin()) for d in [1, 2]}
out = {"n": N, "tau": TAU, "noise_sd": SIG, "reps": REPS, "best_h_by_rmse": best,
       "local_linear": S.loc[1].to_dict(orient="index"), "local_quadratic": S.loc[2].to_dict(orient="index")}
json.dump(out, open(RES / "a647_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例の1回と、幅0.1と1.0の直線
x, y = draw()
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.scatter(x, y, s=5, color=GRAY, alpha=0.5)
for h, c in [(0.15, BLUE), (1.0, ORANGE)]:
    for sgn in [1, -1]:
        m = (sgn * x >= 0) & (np.abs(x) < h)
        w = np.clip(1 - np.abs(x[m]) / h, 0, None)
        b = np.polyfit(x[m], y[m], 1, w=np.sqrt(w))
        xx = np.linspace(0, sgn * h, 50)
        ax.plot(xx, np.polyval(b, xx), color=c, lw=2, label=f"幅 {h} の直線" if sgn == 1 else None)
xx = np.linspace(-1, 1, 400)
ax.plot(xx[xx < 0], f(xx[xx < 0]), color=INK, ls="--", lw=1, label="本当の関係")
ax.plot(xx[xx >= 0], f(xx[xx >= 0]) + TAU, color=INK, ls="--", lw=1)
ax.axvline(0, color=GRAY, lw=0.8); ax.set_xlabel("割り当てを決める点数（0以上で施策あり）"); ax.set_ylabel("結果")
ax.legend(frameon=False, fontsize=9); ax.set_title("広い幅の直線は曲がりを拾えず、境目の跳びを取り違える（例の1回）")
save(fig, "a647_example.png", SRC)

# 図2：偏りとばらつき（局所線形・局所2次）
fig, ax = plt.subplots(1, 2, figsize=(11, 3.9), sharey=False, gridspec_kw={"wspace": 0.28})
for deg, c, lab in [(1, BLUE, "局所線形"), (2, GREEN, "局所2次")]:
    s = S.loc[deg]
    ax[0].plot(HS, s.bias, marker="o", color=c, label=lab)
    ax[1].plot(HS, s.sd, marker="s", color=c, label=lab)
ax[0].axhline(0, color=GRAY, lw=0.8); ax[0].set_xlabel("幅 h"); ax[0].set_title("偏り（本当の効果0.3との差）", fontsize=11); ax[0].legend(frameon=False, fontsize=9)
ax[1].set_xlabel("幅 h"); ax[1].set_title("ばらつき（標準偏差）", fontsize=11)
save(fig, "a647_bias_sd.png", SRC, y=-0.06)

# 図3：誤差と区間の当たり方
fig, ax = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"wspace": 0.28})
for deg, c, lab in [(1, BLUE, "局所線形"), (2, GREEN, "局所2次")]:
    s = S.loc[deg]
    ax[0].plot(HS, s.rmse, marker="o", color=c, label=f"{lab}（最小は h={best[deg]}）")
    ax[1].plot(HS, s.coverage, marker="s", color=c, label=lab)
ax[0].set_xlabel("幅 h"); ax[0].set_title("誤差（RMSE）", fontsize=11); ax[0].legend(frameon=False, fontsize=9)
ax[1].axhline(95, color=GRAY, ls="--", lw=0.8); ax[1].set_xlabel("幅 h"); ax[1].set_ylim(0, 100)
ax[1].set_title("95%区間が本当の効果を含んだ割合（%）", fontsize=11)
save(fig, "a647_rmse_coverage.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
