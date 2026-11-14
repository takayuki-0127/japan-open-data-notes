"""768 強く相関する変数があるとき、部分依存の図はどれだけ本当の効き方とずれるのか

架空のデータ。x1・x2 は標準正規で相関 rho（0〜0.95）。本当の関係は y = x1 + sin(2·x2)・2 + ばらつき。
勾配ブースティング（HistGradientBoosting）で学習し、x1・x2 の部分依存（PD）と ALE（累積局所効果）を出して、
本当の効き方（x1 は直線、x2 は sin）との差（中心化した曲線の RMSE）を比べる。
PD を計算するときに使う (x1, x2) の組のうち、データにほとんどない組（近くの学習データまでの距離が遠い）の割合も数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
from scipy.spatial import cKDTree
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 768）"
rng = np.random.default_rng(768)
N, R = 2000, 5
RHOS = [0.0, 0.5, 0.8, 0.9, 0.95]
G = np.linspace(-2, 2, 21)
f1 = lambda x: x
f2 = lambda x: 2 * np.sin(2 * x)


def make(rho, n):
    z = rng.standard_normal((n, 2))
    x1 = z[:, 0]; x2 = rho * z[:, 0] + np.sqrt(1 - rho ** 2) * z[:, 1]
    X = np.c_[x1, x2]
    y = f1(x1) + f2(x2) + rng.normal(0, .5, n)
    return X, y


def pd_curve(m, X, j):
    out = []
    for g in G:
        Z = X.copy(); Z[:, j] = g; out.append(m.predict(Z).mean())
    return np.array(out)


def ale_curve(m, X, j, K=40):
    edges = np.quantile(X[:, j], np.linspace(0, 1, K + 1))
    idx = np.clip(np.searchsorted(edges, X[:, j], side="right") - 1, 0, K - 1)
    eff = np.zeros(K)
    for k in range(K):
        s = X[idx == k]
        if len(s) == 0: continue
        lo, hi = s.copy(), s.copy(); lo[:, j] = edges[k]; hi[:, j] = edges[k + 1]
        eff[k] = (m.predict(hi) - m.predict(lo)).mean()
    acc = np.r_[0, np.cumsum(eff)]
    return np.interp(G, edges, acc)


def cen(v): return v - v.mean()


def rmse(a, b): return float(np.sqrt(np.mean((cen(a) - cen(b)) ** 2)))


rows = []; keep = {}
for rho in RHOS:
    for r in range(R):
        X, y = make(rho, N)
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=.1, random_state=r).fit(X, y)
        res = dict(rho=rho, rep=r)
        for j, f in [(0, f1), (1, f2)]:
            p = pd_curve(m, X, j); a = ale_curve(m, X, j); t = f(G)
            res[f"pd_rmse_x{j+1}"] = rmse(p, t); res[f"ale_rmse_x{j+1}"] = rmse(a, t)
            if r == 0: keep[(rho, j)] = (p, a)
        # PD で使う組のうち、データから遠い組の割合（最も近い学習点までの距離 > 0.3）
        tree = cKDTree(X); far = []
        for g in G:
            Z = X[:500].copy(); Z[:, 0] = g; d, _ = tree.query(Z); far.append((d > .3).mean())
        res["far_share"] = float(np.mean(far))
        rows.append(res)
D = pd.DataFrame(rows)
S = D.groupby("rho").mean().drop(columns="rep").reset_index()
S.to_csv(RES / "summary.csv", index=False)
g = lambda rho, k: float(S[S.rho == rho][k].iloc[0])
out = {"n": N, "reps": R, "true": "y = x1 + 2·sin(2·x2) + N(0, 0.5²)",
       "by_rho": {str(rho): {k: round(g(rho, k), 3) for k in ["pd_rmse_x1", "ale_rmse_x1", "pd_rmse_x2", "ale_rmse_x2", "far_share"]} for rho in RHOS}}
for k in ["pd_rmse_x1", "ale_rmse_x1", "pd_rmse_x2", "ale_rmse_x2", "far_share"]:
    out[f"{k}_rho0"] = g(0.0, k); out[f"{k}_rho095"] = g(0.95, k)
json.dump(out, open(RES / "a768_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：相関0.95のときの x2 の曲線
fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, rho in zip(axs, [0.0, 0.95]):
    p, a = keep[(rho, 1)]
    ax.plot(G, cen(f2(G)), color=GRAY, lw=3, label="本当の効き方")
    ax.plot(G, cen(p), "o-", color=ORANGE, ms=4, label="部分依存")
    ax.plot(G, cen(a), "s-", color=BLUE, ms=4, label="ALE")
    ax.set_title(f"x1 と x2 の相関 {rho}"); ax.set_xlabel("x2")
axs[0].set_ylabel("x2 の効き（平均を0にそろえた）"); axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("相関が強いと、部分依存は x2 の効きに x1 の分をまぜて描く", y=1.03)
save(fig, "a768_curves.png", SRC, y=-0.05)

# 図2：相関とずれ
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.rho, S.pd_rmse_x2, "o-", color=ORANGE, label="部分依存（x2）")
ax.plot(S.rho, S.ale_rmse_x2, "s-", color=BLUE, label="ALE（x2）")
ax.plot(S.rho, S.pd_rmse_x1, "o--", color=ORANGE, alpha=.6, label="部分依存（x1）")
ax.plot(S.rho, S.ale_rmse_x1, "s--", color=BLUE, alpha=.6, label="ALE（x1）")
ax.set_xlabel("x1 と x2 の相関"); ax.set_ylabel("本当の曲線とのずれ（RMSE）"); ax.set_ylim(0, None)
ax.legend(frameon=False); ax.set_title(f"相関が強いほど部分依存のずれが大きくなる（{N:,}件、各{R}回の平均）")
save(fig, "a768_rmse.png", SRC)

# 図3：データから遠い組の割合
fig, ax = plt.subplots(figsize=(9, 4.6))
b = ax.bar([str(r) for r in S.rho], S.far_share * 100, color=GREEN)
for bb, v in zip(b, S.far_share * 100): ax.text(bb.get_x() + bb.get_width() / 2, v + 1, f"{v:.0f}%", ha="center")
ax.set_xlabel("x1 と x2 の相関"); ax.set_ylabel("データから遠い組の割合（%）")
ax.set_title("部分依存が予測に使う (x1, x2) の組のうち、近くに学習データがない組")
save(fig, "a768_far.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
