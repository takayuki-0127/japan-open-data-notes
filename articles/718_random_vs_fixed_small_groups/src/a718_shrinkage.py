"""718 件数の少ない店が多いとき、店ごとの平均を「そのまま」出すのと、ランダム効果で縮めるのとでは、どれだけ当たり方が違うのか

架空の200店。店の本当の平均客単価は 平均3,000円・店の間の標準偏差150円の正規分布、
1件ごとのばらつきは標準偏差800円。1店あたりの件数は 2〜40件（多くの店が少ない）。
推定の3通り：
  そのまま：店ごとの平均
  縮小（ランダム効果）：店の平均を全体の平均の方へ w = τ²/(τ²+σ²/n) だけ寄せる（τ²・σ² はデータから推定）
  全体の平均：すべての店に同じ値
1つのデータで比べたあと、1店あたりの件数を 3・5・10・20・50件にそろえて各300回くり返す。
statsmodels の MixedLM（ランダム切片）の予測と、ここの縮小推定がほぼ同じになることも確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.formula.api as smf
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の200店の客単価（作成者が乱数で作成、seed 718）"
rng = np.random.default_rng(718)
K, MU, TAU, SIG = 200, 3000.0, 150.0, 800.0


def make(n_per):
    theta = rng.normal(MU, TAU, K)
    store = np.repeat(np.arange(K), n_per)
    y = theta[store] + rng.normal(0, SIG, store.size)
    return theta, store, y


def estimate(store, y):
    n = np.bincount(store, minlength=K).astype(float)
    m = np.bincount(store, y, minlength=K) / n
    resid = y - m[store]
    s2 = (resid ** 2).sum() / (y.size - K)                     # 店の中のばらつき
    gm = y.mean()
    tau2 = max(np.var(m, ddof=1) - np.mean(s2 / n), 0.0)       # 店の間のばらつき（モーメント法）
    w = tau2 / (tau2 + s2 / n)
    mu_hat = np.sum(w * m) / np.sum(w) if tau2 > 0 else gm
    shrunk = mu_hat + w * (m - mu_hat)
    return m, shrunk, np.full(K, gm), w, tau2, s2


def metrics(theta, est):
    rmse = float(np.sqrt(np.mean((est - theta) ** 2)))
    top = set(np.argsort(-theta)[:20]); 
    hit = len(top & set(np.argsort(-est)[:20])) / 20 if np.ptp(est) > 0 else np.nan
    rho = float(stats.spearmanr(theta, est).statistic) if np.ptp(est) > 0 else np.nan
    return rmse, hit, rho


# 1つのデータ：件数 2〜40件（少ない店が多い）
n_one = np.clip(np.round(rng.lognormal(np.log(6), 0.8, K)), 2, 40).astype(int)
theta, store, y = make(n_one)
raw, shr, gmv, w, tau2, s2 = estimate(store, y)
one = {nm: dict(zip(["rmse", "top20_hit", "spearman"], metrics(theta, e))) for nm, e in [("raw", raw), ("shrunk", shr), ("grand", gmv)]}

# MixedLM との照合
df = pd.DataFrame({"y": y, "store": store})
ml = smf.mixedlm("y ~ 1", df, groups=df["store"]).fit(reml=True)
blup = ml.fe_params["Intercept"] + np.array([ml.random_effects[k].iloc[0] for k in range(K)])
mixed_diff = float(np.abs(blup - shr).max())
assert mixed_diff < 30, mixed_diff

# くり返し
NLIST, REPS = [3, 5, 10, 20, 50], 300
rows = []
for npr in NLIST:
    for r in range(REPS):
        th, st, yy = make(np.full(K, npr))
        a, b, c, *_ = estimate(st, yy)
        for nm, e in [("raw", a), ("shrunk", b), ("grand", c)]:
            rm, hit, rho = metrics(th, e)
            rows.append({"n_per_store": npr, "method": nm, "rmse": rm, "top20_hit": hit, "spearman": rho})
R = pd.DataFrame(rows)
S = R.groupby(["n_per_store", "method"]).mean().reset_index()
S.round(4).to_csv(RES / "summary.csv", index=False)
piv = S.pivot(index="n_per_store", columns="method", values="rmse")

out = {"stores": K, "true_mean": MU, "tau": TAU, "sigma": SIG, "one_data": {"n_min": int(n_one.min()), "n_median": float(np.median(n_one)),
       "n_max": int(n_one.max()), "share_n_le5_pct": round(float((n_one <= 5).mean() * 100), 1),
       "tau_hat": round(float(np.sqrt(tau2)), 1), "sigma_hat": round(float(np.sqrt(s2)), 1),
       **{f"{k}_{m}": round(v, 3) for k, d in one.items() for m, v in d.items() if not (isinstance(v, float) and np.isnan(v))}},
       "mixedlm_max_abs_diff_yen": round(mixed_diff, 2), "reps": REPS,
       "rmse_by_n": {str(n): {m: round(float(piv.loc[n, m]), 1) for m in ["raw", "shrunk", "grand"]} for n in NLIST},
       "top20_by_n": {str(n): {m: round(float(S[(S.n_per_store == n) & (S.method == m)].top20_hit.iloc[0]) * 100, 1) for m in ["raw", "shrunk"]} for n in NLIST},
       "rmse_ratio_shrunk_vs_raw": {str(n): round(float(piv.loc[n, "shrunk"] / piv.loc[n, "raw"]), 3) for n in NLIST}}
json.dump(out, open(RES / "a718_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1つのデータで、そのままの平均と縮めた平均
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, e, nm, col in [(axes[0], raw, "そのままの店の平均", ORANGE), (axes[1], shr, "縮めた平均（ランダム効果）", BLUE)]:
    ax.scatter(theta, e, s=8 + n_one * 1.5, color=col, alpha=0.6)
    lo, hi = raw.min() - 50, raw.max() + 50; ax.plot([lo, hi], [lo, hi], color=INK, lw=0.8); ax.set_xlim(theta.min() - 50, theta.max() + 50); ax.set_ylim(lo, hi)
    rm = one["raw" if col == ORANGE else "shrunk"]["rmse"]
    ax.set_title(f"{nm}：誤差 {rm:.0f}円"); ax.set_xlabel("本当の店の平均（円）")
axes[0].set_ylabel("推定した店の平均（円）")
fig.suptitle("件数の少ない店（小さい点）ほど、そのままの平均は大きく外れる。縮めると全体の方へ寄る", y=1.02)
save(fig, "a718_one_data.png", SRC)

# 図2：1店あたりの件数ごとの誤差
fig, ax = plt.subplots(figsize=(8, 3.8))
lab = {"raw": "そのまま", "shrunk": "縮小（ランダム効果）", "grand": "全体の平均"}
for m, c in [("raw", ORANGE), ("shrunk", BLUE), ("grand", GRAY)]:
    ax.plot(NLIST, piv[m], marker="o", color=c, label=lab[m])
    for n in NLIST: ax.text(n, piv.loc[n, m] + 8, f"{piv.loc[n, m]:.0f}", ha="center", fontsize=8, color=c)
ax.set_xscale("log"); ax.set_xticks(NLIST); ax.set_xticklabels(NLIST); ax.set_xlabel("1店あたりの件数（log の目盛り）")
ax.set_ylabel("本当の平均との誤差（RMSE、円）"); ax.legend(frameon=False)
ax.set_title(f"件数が少ないほど、縮めた推定の誤差は小さい（{REPS}回の平均）")
save(fig, "a718_rmse_by_n.png", SRC)

# 図3：上位20店を当てた割合
fig, ax = plt.subplots(figsize=(8, 3.6)); x = np.arange(len(NLIST)); wd = 0.38
a = [out["top20_by_n"][str(n)]["raw"] for n in NLIST]; b = [out["top20_by_n"][str(n)]["shrunk"] for n in NLIST]
ax.bar(x - wd / 2, a, wd, color=ORANGE, label="そのまま"); ax.bar(x + wd / 2, b, wd, color=BLUE, label="縮小")
for i in range(len(NLIST)):
    ax.text(x[i] - wd / 2, a[i] + 1, f"{a[i]:.0f}", ha="center", fontsize=8.5); ax.text(x[i] + wd / 2, b[i] + 1, f"{b[i]:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"{n}件" for n in NLIST]); ax.set_ylabel("本当の上位20店を当てた割合（%）")
ax.set_xlabel("1店あたりの件数（どの店も同じ件数）"); ax.legend(frameon=False); ax.set_ylim(0, 100)
ax.set_title("件数がそろっていると、縮めても順位はほとんど変わらない")
save(fig, "a718_top20.png", SRC)
print(json.dumps(out, ensure_ascii=False))
