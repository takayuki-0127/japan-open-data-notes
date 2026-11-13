"""627 相関の強さが同じでも、正規コピュラと t コピュラでは、同時に大きな損害が出る確率はどれだけ違うのか

架空の2つの事業の年間の損害（どちらも対数正規、平均100、変動係数0.5）を、3つのコピュラでつなぐ。
つながりの強さは、順位の相関（ケンドールの τ）を 0.35 にそろえる。
  正規コピュラ（ρ = sin(πτ/2)）、t コピュラ（自由度3、同じ ρ）、ガンベル・コピュラ（θ = 1/(1−τ)、大きい側で強く一緒に動く）
どちらも自分の q 点を超える確率、片方が超えたときにもう片方も超える割合、合計の99.5%点・99.9%点を出す。
各300万回。数字は置いた分布で決まる。料率・備金・資本の助言ではない。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の年間の損害（作成者が乱数で作成、seed 627）"
rng = np.random.default_rng(627)
N, TAU, NU = 3_000_000, 0.35, 3
RHO = float(np.sin(np.pi * TAU / 2)); THETA = 1 / (1 - TAU)
s2 = np.log(1 + 0.5 ** 2); MU, SD = np.log(100) - s2 / 2, np.sqrt(s2)


def gauss(n, rng):
    z = rng.standard_normal((n, 2)); z[:, 1] = RHO * z[:, 0] + np.sqrt(1 - RHO ** 2) * z[:, 1]
    return stats.norm.cdf(z)


def tcop(n, rng):
    z = rng.standard_normal((n, 2)); z[:, 1] = RHO * z[:, 0] + np.sqrt(1 - RHO ** 2) * z[:, 1]
    w = np.sqrt(NU / rng.chisquare(NU, n))[:, None]
    return stats.t.cdf(z * w, NU)


def gumbel(n, rng):
    a = 1 / THETA
    U = rng.uniform(0, np.pi, n); W = rng.exponential(1, n)
    S = np.sin(a * U) / np.sin(U) ** (1 / a) * (np.sin((1 - a) * U) / W) ** ((1 - a) / a)   # 正の安定分布
    E = rng.exponential(1, (n, 2))
    return np.exp(-(E / S[:, None]) ** a)


COP = {"gauss": ("正規コピュラ", gauss, BLUE), "t": ("t コピュラ（自由度3）", tcop, ORANGE), "gumbel": ("ガンベル・コピュラ", gumbel, GREEN)}
LEV = [0.9, 0.95, 0.99, 0.995, 0.999]
res, cond, samples = {}, [], {}
for k, (lab, f, c) in COP.items():
    u = f(N, rng)
    x = np.exp(MU + SD * stats.norm.ppf(np.clip(u, 1e-12, 1 - 1e-12)))
    tau_hat = stats.kendalltau(u[:20000, 0], u[:20000, 1]).statistic
    tot = x.sum(1)
    for q in LEV:
        both = ((u[:, 0] > q) & (u[:, 1] > q)).mean()
        cond.append({"copula": k, "level": q, "both_exceed_pct": 100 * both, "cond_pct": 100 * both / (1 - q),
                     "indep_both_pct": 100 * (1 - q) ** 2})
    res[k] = {"tau_check": round(float(tau_hat), 3), "q995_sum": float(np.quantile(tot, 0.995)), "q999_sum": float(np.quantile(tot, 0.999)),
              "mean_sum": float(tot.mean())}
    samples[k] = u[:4000]
CD = pd.DataFrame(cond); CD.round(4).to_csv(RES / "joint_exceedance.csv", index=False)
q1 = float(np.exp(MU + SD * stats.norm.ppf(0.995)))
S = pd.DataFrame(res).T; S["vs_gauss_q995_pct"] = 100 * (S.q995_sum / S.loc["gauss", "q995_sum"] - 1); S["vs_gauss_q999_pct"] = 100 * (S.q999_sum / S.loc["gauss", "q999_sum"] - 1)
S.round(3).to_csv(RES / "summary.csv")
out = {"n": N, "tau": TAU, "rho_gauss_t": round(RHO, 4), "nu": NU, "theta_gumbel": round(THETA, 4), "standalone_q995_each": round(q1, 2),
       "sum_of_standalone_q995": round(2 * q1, 2), "summary": S.round(3).to_dict(orient="index"), "joint": CD.round(4).to_dict(orient="records")}
json.dump(out, open(RES / "a627_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：順位の散布図
fig, ax = plt.subplots(1, 3, figsize=(11.5, 3.9), gridspec_kw={"wspace": 0.25})
for i, (k, (lab, f, c)) in enumerate(COP.items()):
    u = samples[k]
    ax[i].scatter(u[:, 0], u[:, 1], s=2, color=c, alpha=0.5)
    ax[i].add_patch(plt.Rectangle((0.95, 0.95), 0.05, 0.05, fill=False, ec=INK, lw=1))
    n_c = int(((u[:, 0] > 0.95) & (u[:, 1] > 0.95)).sum())
    ax[i].set_title(f"{lab}\n右上の四角（どちらも上位5%）に {n_c}点", fontsize=10.5)
    ax[i].set_xlim(0, 1); ax[i].set_ylim(0, 1); ax[i].set_aspect("equal")
ax[0].set_ylabel("事業2の損害の順位（0〜1）"); ax[1].set_xlabel("事業1の損害の順位（0〜1）。4,000年分")
save(fig, "a627_rank_scatter.png", SRC, y=-0.02)

# 図2：片方が超えたとき、もう片方も超える割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for k, (lab, f, c) in COP.items():
    s = CD[CD.copula == k]
    ax.plot(range(len(LEV)), s.cond_pct, marker="o", color=c, label=lab)
    ax.text(len(LEV) - 1 + 0.08, s.cond_pct.iloc[-1], f"{s.cond_pct.iloc[-1]:.0f}%", color=c, va="center", fontsize=9)
ax.plot(range(len(LEV)), [100 * (1 - q) for q in LEV], ls=":", color=GRAY, label="独立なら")
ax.set_xticks(range(len(LEV))); ax.set_xticklabels([f"{q*100:g}%点" for q in LEV]); ax.set_xlabel("それぞれの損害の水準")
ax.set_ylabel("事業1が超えた年に事業2も超える割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("同じ順位の相関（τ=0.35）でも、大きな損害ほど一緒に起きる割合が違う")
save(fig, "a627_conditional.png", SRC)

# 図3：合計の分位点
fig, ax = plt.subplots(figsize=(8.5, 4))
w = 0.25; xs = np.arange(2)
for j, (k, (lab, f, c)) in enumerate(COP.items()):
    v = [res[k]["q995_sum"], res[k]["q999_sum"]]
    ax.bar(xs + (j - 1) * w, v, w, color=c, label=lab)
    for x, vv in zip(xs + (j - 1) * w, v):
        ax.text(x, vv + 3, f"{vv:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(xs); ax.set_xticklabels(["合計の99.5%点（200年に1度）", "合計の99.9%点（1000年に1度）"])
ax.set_ylabel("2つの事業の合計の損害"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, max(r["q999_sum"] for r in res.values()) * 1.15)
ax.set_title("合計の大きな分位点（平均の合計は200）")
save(fig, "a627_sum_quantiles.png", SRC)
print(S.round(2)); print(CD.round(3).to_string())
