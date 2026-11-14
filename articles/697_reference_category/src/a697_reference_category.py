"""697 ダミー変数の基準のカテゴリを変えると、係数と有意の見え方はどれだけ変わるのか

架空の6店（A〜F）の1日の売上（万円）。件数は A 300日・B 250・C 200・D 150・E 120・F 15日（Fだけ少ない）。
本当の平均は A 50・B 52・C 51・D 53・E 50・F 53、日ごとのばらつき（標準偏差）8。
店のダミー変数で回帰し、基準の店を A〜F に変えて、係数・p 値・全体の F 検定・予測値を比べる。
1つのデータで比べたあと、同じ作り方で2,000回くり返し、基準ごとに「有意（p<0.05）になる店の数」を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の6店の売上（作成者が乱数で作成、seed 697）"
rng = np.random.default_rng(697)
SH = list("ABCDEF")
NS = np.array([300, 250, 200, 150, 120, 15])
MU = np.array([50, 52, 51, 53, 50, 53.0])
SD = 8.0
store = np.repeat(np.arange(6), NS)
N = len(store)


def fit(y, base):
    """基準 base のダミー回帰。係数・標準誤差・p・F・予測値を返す"""
    others = [k for k in range(6) if k != base]
    X = np.column_stack([np.ones(N)] + [(store == k).astype(float) for k in others])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; df = N - X.shape[1]; s2 = r @ r / df
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    p = 2 * stats.t.sf(np.abs(b / se), df)
    tss = ((y - y.mean()) ** 2).sum(); F = ((tss - r @ r) / 5) / (r @ r / df)
    return {"others": others, "b": b, "se": se, "p": p, "F": F, "pF": stats.f.sf(F, 5, df), "pred": X @ b, "df": df}


y = MU[store] + rng.normal(0, SD, N)
fits = [fit(y, k) for k in range(6)]
rows = []
for k, f in enumerate(fits):
    for j, o in enumerate(f["others"]):
        rows.append({"base": SH[k], "store": SH[o], "coef": f["b"][j + 1], "se": f["se"][j + 1], "p": f["p"][j + 1]})
C = pd.DataFrame(rows); C.round(4).to_csv(RES / "coef_by_base.csv", index=False)
nsig = {SH[k]: int((f["p"][1:] < 0.05).sum()) for k, f in enumerate(fits)}
pred_diff = max(float(np.abs(f["pred"] - fits[0]["pred"]).max()) for f in fits)
F_vals = [float(f["F"]) for f in fits]

# 2,000回のくり返し
REPS = 2000
ns_sim = np.zeros((REPS, 6), dtype=int); fsig = np.zeros(REPS, dtype=bool)
for i in range(REPS):
    yy = MU[store] + rng.normal(0, SD, N)
    for k in range(6):
        f = fit(yy, k); ns_sim[i, k] = (f["p"][1:] < 0.05).sum()
        if k == 0: fsig[i] = f["pF"] < 0.05
sim = pd.DataFrame({"base": SH, "mean_sig": ns_sim.mean(0), "zero_sig_pct": (ns_sim == 0).mean(0) * 100,
                    "ge3_sig_pct": (ns_sim >= 3).mean(0) * 100})
sim.round(3).to_csv(RES / "sim_by_base.csv", index=False)
spread = ns_sim.max(1) - ns_sim.min(1)

means = pd.Series(y).groupby(store).mean().values
out = {"n_by_store": dict(zip(SH, NS.tolist())), "true_mean": dict(zip(SH, MU.tolist())), "sample_mean": dict(zip(SH, np.round(means, 2).tolist())),
       "n_sig_by_base": nsig, "F": round(F_vals[0], 3), "F_max_abs_diff": float(np.round(max(F_vals) - min(F_vals), 10)),
       "F_p": float(fits[0]["pF"]), "pred_max_abs_diff": float(np.round(pred_diff, 10)),
       "coef_F_vs_baseA": {"coef": round(float(C[(C.base == "A") & (C.store == "F")].coef.iloc[0]), 2), "p": round(float(C[(C.base == "A") & (C.store == "F")].p.iloc[0]), 3)},
       "sim_reps": REPS, "sim_mean_sig": dict(zip(SH, np.round(ns_sim.mean(0), 2).tolist())),
       "sim_zero_sig_pct": dict(zip(SH, np.round((ns_sim == 0).mean(0) * 100, 1).tolist())),
       "sim_spread_ge2_pct": round(float((spread >= 2).mean() * 100), 1), "sim_F_sig_pct": round(float(fsig.mean() * 100), 1)}
json.dump(out, open(RES / "a697_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：基準 A と基準 F の係数（95%区間）
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, bk in zip(axes, ["A", "F"]):
    c = C[C.base == bk].reset_index(drop=True); x = np.arange(len(c))
    sig = c.p < 0.05
    ax.errorbar(x, c.coef, yerr=1.96 * c.se, fmt="none", ecolor=GRAY, lw=1.2, capsize=3)
    ax.scatter(x[sig], c.coef[sig], color=ORANGE, zorder=3, label="有意（p<0.05）")
    ax.scatter(x[~sig], c.coef[~sig], color=BLUE, zorder=3, label="有意でない")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"店{s}" for s in c.store])
    ax.set_title(f"基準＝店{bk}（{NS[SH.index(bk)]}日）：有意 {nsig[bk]}店")
axes[0].set_ylabel("基準との差（万円）"); axes[0].legend(frameon=False, fontsize=9, loc="lower left")
fig.suptitle("同じデータでも、基準を件数の少ない店Fにすると区間が広がり、有意の店が減る", y=1.02)
save(fig, "a697_coef.png", SRC)

# 図2：基準ごとの有意な店の数（このデータ・2,000回の平均）
fig, ax = plt.subplots(figsize=(8, 3.6)); x = np.arange(6); w = 0.38
ax.bar(x - w / 2, [nsig[s] for s in SH], w, color=ORANGE, label="このデータ")
ax.bar(x + w / 2, ns_sim.mean(0), w, color=BLUE, label=f"{REPS:,}回の平均")
for i in range(6): ax.text(x[i] + w / 2, ns_sim.mean(0)[i] + 0.05, f"{ns_sim.mean(0)[i]:.2f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"店{s}\n({n}日)" for s, n in zip(SH, NS)]); ax.set_ylabel("有意になった店の数（5店中）")
ax.set_xlabel("基準にした店"); ax.legend(frameon=False, fontsize=9)
ax.set_title("基準を変えるだけで、「有意な店」の数が変わる")
save(fig, "a697_nsig_by_base.png", SRC)

# 図3：全体の F 検定と予測値は基準によらない
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
axes[0].bar(SH, F_vals, color=GREEN); axes[0].set_ylabel("全体の F 値"); axes[0].set_xlabel("基準にした店")
axes[0].set_title(f"F 値はどれも {F_vals[0]:.2f}"); axes[0].set_ylim(0, max(F_vals) * 1.25)
pm = np.array([fits[k]["pred"][np.searchsorted(store, np.arange(6))] for k in range(6)])
for k in range(6): axes[1].plot(SH, pm[k], marker="o", lw=1, alpha=0.8, label=f"基準＝店{SH[k]}")
axes[1].scatter(SH, MU, marker="x", color=INK, zorder=4, label="本当の平均")
axes[1].set_ylabel("店ごとの予測値（万円）"); axes[1].set_title("店ごとの予測値は6通りとも同じ（差は1e-10万円未満）")
axes[1].legend(frameon=False, fontsize=7.5, ncol=2)
save(fig, "a697_same_fit.png", SRC)
print(json.dumps(out, ensure_ascii=False))
