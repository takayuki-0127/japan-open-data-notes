"""636 件数が少なく変数が多いとき、リッジ回帰はふつうの回帰より予測の誤差をどれだけ減らすのか

本当の係数が分かっている架空のデータ（説明変数30個、どの2つも相関0.5、効く変数は10個）で、
件数 n=40・60・100・300・1000 のとき、最小二乗法（OLS）とリッジ回帰（強さは5分割の交差検証で選ぶ）を当て、
新しいデータ（1万件）での予測の誤差と、係数のずれを比べる。各300回。誤差のばらつき（ノイズ）の分散は1。
数字は置いた変数の数・係数・相関で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression, RidgeCV
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 636）"
rng = np.random.default_rng(636)
P, RHO, REPS = 30, 0.5, 300
beta = np.zeros(P); beta[:10] = [0.6, -0.5, 0.4, 0.4, -0.3, 0.3, 0.2, -0.2, 0.2, 0.1]
C = np.full((P, P), RHO); np.fill_diagonal(C, 1.0); L = np.linalg.cholesky(C)
ALPHAS = np.logspace(-3, 3, 31)


def draw(n, snr_sd=1.0):
    X = rng.standard_normal((n, P)) @ L.T
    y = X @ beta + rng.standard_normal(n) * snr_sd
    return X, y


Xt, yt = draw(10000)
mu_t = Xt @ beta
rows = []
for n in [40, 60, 100, 300, 1000]:
    for r in range(REPS):
        X, y = draw(n)
        ols = LinearRegression().fit(X, y)
        rid = RidgeCV(alphas=ALPHAS, cv=5).fit(X, y)
        for name, m in [("OLS", ols), ("Ridge", rid)]:
            pe = float(np.mean((m.predict(Xt) - mu_t) ** 2))      # 本当の平均からのずれ（ノイズを除いた予測の誤差）
            ce = float(np.sum((m.coef_ - beta) ** 2))
            rows.append({"n": n, "rep": r, "model": name, "pred_excess": pe, "coef_sse": ce,
                         "alpha": float(getattr(m, "alpha_", 0.0)),
                         "beta1": float(m.coef_[0])})
D = pd.DataFrame(rows)
D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
S = D.groupby(["n", "model"]).agg(pred_excess=("pred_excess", "mean"), pred_excess_med=("pred_excess", "median"),
                                  coef_sse=("coef_sse", "mean"), beta1_mean=("beta1", "mean"), beta1_sd=("beta1", "std"),
                                  alpha_med=("alpha", "median")).round(4)
S.to_csv(RES / "summary.csv")
w = D.pivot_table(index=["n", "rep"], columns="model", values="pred_excess").reset_index()
win = w.groupby("n").apply(lambda g: float((g.Ridge < g.OLS).mean() * 100)).round(1)
# 予測の誤差（ノイズ1を足した全体の二乗誤差）での比
tot = S.pred_excess.unstack() + 1.0
ratio = (tot.Ridge / tot.OLS).round(3)
red = ((1 - S.pred_excess.unstack().Ridge / S.pred_excess.unstack().OLS) * 100).round(1)
out = {"p": P, "rho": RHO, "reps": REPS, "beta_nonzero": 10,
       "summary": S.reset_index().to_dict(orient="records"),
       "ridge_wins_pct": win.to_dict(), "total_mse_ratio_ridge_over_ols": ratio.to_dict(),
       "excess_error_reduction_pct": red.to_dict()}
json.dump(out, open(RES / "a636_main.json", "w"), ensure_ascii=False, indent=1)

ns = [40, 60, 100, 300, 1000]
U = S.unstack()
# 図1：予測の誤差（ノイズを除いた分）
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(ns, U.pred_excess.OLS, marker="o", color=ORANGE, label="ふつうの回帰（OLS）")
ax.plot(ns, U.pred_excess.Ridge, marker="s", color=BLUE, label="リッジ回帰（強さは交差検証）")
for n in ns:
    ax.text(n, U.pred_excess.OLS[n], f" {U.pred_excess.OLS[n]:.2f}", fontsize=8, color=ORANGE, va="bottom")
    ax.text(n, U.pred_excess.Ridge[n], f" {U.pred_excess.Ridge[n]:.2f}", fontsize=8, color=BLUE, va="top")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(ns); ax.set_xticklabels(ns)
ax.set_xlabel("件数（変数は30個）"); ax.set_ylabel("予測の誤差（ノイズを除いた分、対数）")
ax.legend(frameon=False); ax.set_title("件数が少ないほど、リッジ回帰は予測の誤差を大きく減らす（300回の平均）")
save(fig, "a636_pred_error.png", SRC)

# 図2：係数1つ目（本当は0.6）の分布、n=40
fig, ax = plt.subplots(figsize=(8, 4))
d40 = D[D.n == 40]
bins = np.linspace(-1.5, 2.5, 50)
ax.hist(d40[d40.model == "OLS"].beta1, bins=bins, color=ORANGE, alpha=0.6, label="OLS")
ax.hist(d40[d40.model == "Ridge"].beta1, bins=bins, color=BLUE, alpha=0.6, label="リッジ")
ax.axvline(0.6, color=INK, ls="--", lw=1); ax.text(0.62, ax.get_ylim()[1] * 0.9, "本当の値 0.6", fontsize=9)
ax.set_xlabel("1つ目の変数の係数の推定値"); ax.set_ylabel("回数（300回中）"); ax.legend(frameon=False)
ax.set_title("40件のとき：リッジは0の側に縮むが、ばらつきはずっと小さい")
save(fig, "a636_coef_dist.png", SRC)

# 図3：リッジが勝った割合と、選ばれた強さ
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"wspace": 0.35})
ax[0].bar([str(n) for n in ns], [win[n] for n in ns], color=BLUE)
for i, n in enumerate(ns):
    ax[0].text(i, win[n], f"{win[n]:.0f}%", ha="center", va="bottom", fontsize=9)
ax[0].set_ylim(0, 110); ax[0].set_xlabel("件数"); ax[0].set_title("リッジの方が予測の誤差が小さかった回の割合", fontsize=11)
ax[1].bar([str(n) for n in ns], [ratio[n] for n in ns], color=GREEN)
for i, n in enumerate(ns):
    ax[1].text(i, ratio[n], f"{ratio[n]:.2f}", ha="center", va="bottom", fontsize=9)
ax[1].axhline(1, color=GRAY, lw=0.8, ls="--"); ax[1].set_ylim(0, 1.15); ax[1].set_xlabel("件数")
ax[1].set_title("新しいデータの二乗誤差の比（リッジ÷OLS、ノイズ込み）", fontsize=11)
save(fig, "a636_win_ratio.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
