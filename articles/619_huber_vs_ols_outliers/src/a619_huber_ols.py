"""619 外れ値が混ざったデータで、ふつうの回帰と Huber の回帰では係数はどれだけ違うのか

本当の関係は y = 1 + 2x + 誤差（x〜N(0,1)、誤差〜N(0,1)）、200件。外れ値を 0〜20% 混ぜる。
  縦の外れ値：y に +15 を足す（x はふつう）
  てこの外れ値：x を 4〜6 に置き、y を −8 前後にする（傾きを引っぱる位置）
比べる方法：
  OLS（ふつうの最小二乗）、Huber（statsmodels RLM、HuberT、c=1.345）、
  除外OLS（OLS の標準化残差の絶対値が3を超える点を除いて当て直す）
各条件500回。傾き（本当は2）の平均・標準偏差・RMSE を出す。数字は置いた外れ値の作り方で決まる。
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 619）"
rng = np.random.default_rng(619)
N, REPS, B1 = 200, 500, 2.0
FRACS = [0, 0.01, 0.05, 0.10, 0.20]


def make(f, kind, rng):
    x = rng.normal(0, 1, N); y = 1 + B1 * x + rng.normal(0, 1, N)
    k = int(round(f * N)); idx = np.arange(k)
    if kind == "vertical":
        y[idx] += 15
    else:
        x[idx] = rng.uniform(4, 6, k); y[idx] = rng.normal(-8, 1, k)
    return x, y, k


def fits(x, y):
    X = sm.add_constant(x)
    b_ols = sm.OLS(y, X).fit()
    b_hub = sm.RLM(y, X, M=sm.robust.norms.HuberT()).fit()
    r = b_ols.get_influence().resid_studentized_internal
    keep = np.abs(r) <= 3
    b_trim = sm.OLS(y[keep], X[keep]).fit()
    return b_ols.params[1], b_hub.params[1], b_trim.params[1], int((~keep).sum())


rows = []
for kind in ["vertical", "leverage"]:
    for f in FRACS:
        for r in range(REPS):
            x, y, k = make(f, kind, rng)
            o, h, t, nd = fits(x, y)
            rows.append({"kind": kind, "frac": f, "rep": r, "ols": o, "huber": h, "trim": t, "n_dropped": nd, "k": k})
R = pd.DataFrame(rows)
R.round(5).to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
M = ["ols", "huber", "trim"]
summ = []
for (kind, f), g in R.groupby(["kind", "frac"]):
    for m in M:
        summ.append({"kind": kind, "frac": f, "method": m, "mean": g[m].mean(), "sd": g[m].std(),
                     "rmse": np.sqrt(((g[m] - B1) ** 2).mean())})
S = pd.DataFrame(summ)
S.round(4).to_csv(RES / "summary.csv", index=False)
drop = R.groupby(["kind", "frac"]).n_dropped.mean().round(2).reset_index()
drop.to_csv(RES / "trim_dropped.csv", index=False)
eff = float((S.query("frac==0 and method=='ols'").sd.iloc[0] / S.query("frac==0 and method=='huber'").sd.iloc[0]) ** 2)
out = {"n": N, "reps": REPS, "true_slope": B1, "summary": S.round(4).to_dict(orient="records"),
       "trim_dropped": drop.to_dict(orient="records"), "huber_efficiency_clean": round(eff, 3)}
json.dump(out, open(RES / "a619_main.json", "w"), ensure_ascii=False, indent=1)

COL = {"ols": BLUE, "huber": ORANGE, "trim": GREEN}
LAB = {"ols": "ふつうの回帰（OLS）", "huber": "Huber の回帰", "trim": "残差が3を超える点を除いた OLS"}
TT = {"vertical": "縦の外れ値（y に +15）", "leverage": "てこの外れ値（x が 4〜6、y が −8 前後）"}
# 図1：傾きの平均
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"wspace": 0.25})
for i, kind in enumerate(["vertical", "leverage"]):
    for m in M:
        s = S[(S.kind == kind) & (S.method == m)]
        ax[i].plot(s.frac * 100, s["mean"], marker="o", color=COL[m], label=LAB[m])
    ax[i].axhline(B1, color=GRAY, ls=":"); ax[i].set_title(TT[kind]); ax[i].set_xlabel("外れ値の割合（%）")
ax[0].set_ylabel("傾きの平均（本当は 2）"); ax[1].legend(frameon=False, fontsize=9)
save(fig, "a619_slope_mean.png", SRC, y=-0.04)

# 図2：RMSE
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"wspace": 0.25})
w = 0.27; xs = np.arange(len(FRACS))
for i, kind in enumerate(["vertical", "leverage"]):
    for j, m in enumerate(M):
        s = S[(S.kind == kind) & (S.method == m)]
        ax[i].bar(xs + (j - 1) * w, s.rmse, w, color=COL[m], label=LAB[m])
    ax[i].set_xticks(xs); ax[i].set_xticklabels([f"{int(f*100)}%" for f in FRACS]); ax[i].set_yscale("log")
    ax[i].set_title(TT[kind]); ax[i].set_xlabel("外れ値の割合")
ax[0].set_ylabel("傾きの誤差（RMSE、対数目盛）"); ax[0].legend(frameon=False, fontsize=9)
save(fig, "a619_rmse.png", SRC, y=-0.04)

# 図3：1回分の例（てこの外れ値10%）
x, y, k = make(0.10, "leverage", np.random.default_rng(6190))
o, h, t, nd = fits(x, y)
X = sm.add_constant(x)
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.scatter(x[k:], y[k:], s=12, color=GRAY, alpha=0.6, label="ふつうの点")
ax.scatter(x[:k], y[:k], s=18, color=INK, marker="x", label="てこの外れ値（10%）")
xx = np.linspace(-3, 6, 50)
for m, b in [("ols", sm.OLS(y, X).fit().params), ("huber", sm.RLM(y, X, M=sm.robust.norms.HuberT()).fit().params)]:
    ax.plot(xx, b[0] + b[1] * xx, color=COL[m], label=f"{LAB[m]}：傾き {b[1]:.2f}")
ax.plot(xx, 1 + B1 * xx, color=INK, ls=":", lw=1, label="本当の線：傾き 2")
ax.legend(frameon=False, fontsize=9); ax.set_xlabel("x"); ax.set_ylabel("y")
ax.set_title("てこの外れ値は、Huber の回帰でも線を引っぱる")
save(fig, "a619_example.png", SRC)
print(S.round(3).to_string()); print(drop); print(eff)
