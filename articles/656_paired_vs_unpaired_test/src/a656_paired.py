"""656 同じ店の前と後を比べるとき、対応のない検定にすると、差を見つける力はどれだけ落ちるのか

架空の40店。施策の前と後の1か月の指標（例：客数の指数）を測る。全体のばらつき（標準偏差1）を、
店ごとの水準の差と、月ごとの揺れに分け、その割合を変える。
  ρ = 店のばらつき² ÷ 全体のばらつき² ＝ 前と後の相関
施策の本当の効果 δ（0.3、効果なしの0も）。
  T1 対応のある t 検定（店ごとの差を検定）
  T2 対応のない t 検定（前と後を別の群とみなす、等分散）
各設定3,000回、seed 656。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 656）"
rng = np.random.default_rng(656)
N, REPS = 40, 3000
RHOS = [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
rows = []
for delta in [0.0, 0.3]:
    for rho in RHOS:
        ss, se = np.sqrt(rho), np.sqrt(1 - rho)
        mu = rng.normal(0, ss, (REPS, N))
        pre = mu + rng.normal(0, se, (REPS, N)); post = mu + delta + rng.normal(0, se, (REPS, N))
        d = post - pre
        p1 = stats.ttest_1samp(d, 0, axis=1).pvalue
        p2 = stats.ttest_ind(post, pre, axis=1).pvalue
        se1 = d.std(axis=1, ddof=1) / np.sqrt(N)
        sp = np.sqrt((pre.var(axis=1, ddof=1) + post.var(axis=1, ddof=1)) / 2); se2 = sp * np.sqrt(2 / N)
        w1 = 2 * stats.t.ppf(0.975, N - 1) * se1; w2 = 2 * stats.t.ppf(0.975, 2 * N - 2) * se2
        rows.append({"delta": delta, "rho": rho, "power_paired": (p1 < 0.05).mean(), "power_unpaired": (p2 < 0.05).mean(),
                     "ci_width_paired": w1.mean(), "ci_width_unpaired": w2.mean(), "obs_corr": np.mean([np.corrcoef(pre[i], post[i])[0, 1] for i in range(200)])})
R = pd.DataFrame(rows); R.round(4).to_csv(RES / "summary.csv", index=False)
# 必要な店の数（効果0.3、検出力80%）を、ρ=0.5 と 0.8 で数える
need = {}
for rho in [0.5, 0.8]:
    ss, se = np.sqrt(rho), np.sqrt(1 - rho); res = {}
    for kind in ["paired", "unpaired"]:
        for n in range(10, 401, 5):
            mu = rng.normal(0, ss, (1500, n)); pre = mu + rng.normal(0, se, (1500, n)); post = mu + 0.3 + rng.normal(0, se, (1500, n))
            p = stats.ttest_1samp(post - pre, 0, axis=1).pvalue if kind == "paired" else stats.ttest_ind(post, pre, axis=1).pvalue
            if (p < 0.05).mean() >= 0.8:
                res[kind] = n; break
        else:
            res[kind] = ">400"
    need[str(rho)] = res
E = R[R.delta == 0.3].set_index("rho"); Z = R[R.delta == 0.0].set_index("rho")
out = {"stores": N, "reps": REPS, "delta": 0.3,
       "power": {str(r): {"paired": round(float(E.loc[r, "power_paired"]) * 100, 1), "unpaired": round(float(E.loc[r, "power_unpaired"]) * 100, 1)} for r in RHOS},
       "false_positive_delta0": {str(r): {"paired": round(float(Z.loc[r, "power_paired"]) * 100, 1), "unpaired": round(float(Z.loc[r, "power_unpaired"]) * 100, 1)} for r in RHOS},
       "ci_width_ratio_unpaired_over_paired": {str(r): round(float(E.loc[r, "ci_width_unpaired"] / E.loc[r, "ci_width_paired"]), 2) for r in RHOS},
       "stores_needed_80pct_power": need}
json.dump(out, open(RES / "a656_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：検出力
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(RHOS, E.power_paired * 100, marker="o", color=BLUE, label="対応のある t 検定")
ax.plot(RHOS, E.power_unpaired * 100, marker="s", color=ORANGE, label="対応のない t 検定")
ax.set_xlabel("前と後の相関 ρ（全体のばらつきのうち、店ごとの水準の差が占める割合）"); ax.set_ylabel("差を見つけた割合（%）")
ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=9); ax.set_title("効果0.3・40店：相関が高いほど、対応のある検定だけが差を見つける")
save(fig, "a656_power.png", SRC)
# 図2：区間の幅
fig, ax = plt.subplots(figsize=(8, 3.6))
ratio = E.ci_width_unpaired / E.ci_width_paired
ax.bar([str(r) for r in RHOS], ratio, color=[ORANGE if v > 1.5 else LIGHT for v in ratio])
for i, v in enumerate(ratio):
    ax.text(i, v + 0.03, f"{v:.2f}倍", ha="center", fontsize=8.5)
ax.axhline(1, color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("前と後の相関 ρ"); ax.set_ylabel("対応のない区間の幅 ÷ 対応のある区間の幅")
ax.set_title("相関0.8で、対応のない95%区間は2.2倍の幅になる" if abs(ratio.loc[0.8] - 2.2) < 0.15 else "相関が高いほど、対応のない区間は広くなる")
save(fig, "a656_ci_width.png", SRC)
# 図3：例
r1 = np.random.default_rng(6561); ss, se = np.sqrt(0.8), np.sqrt(0.2)
mu = r1.normal(0, ss, N); pre = 10 + mu + r1.normal(0, se, N); post = 10 + mu + 0.3 + r1.normal(0, se, N)
fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
for i in range(N):
    axs[0].plot([0, 1], [pre[i], post[i]], color=LIGHT, lw=0.8)
axs[0].scatter(np.zeros(N), pre, color=GRAY, s=12); axs[0].scatter(np.ones(N), post, color=BLUE, s=12)
axs[0].set_xticks([0, 1]); axs[0].set_xticklabels(["前", "後"]); axs[0].set_ylabel("指標"); axs[0].set_title("店ごとの前と後（ρ=0.8 の1回分）")
axs[1].hist(post - pre, bins=12, color=BLUE, edgecolor="white"); axs[1].axvline(0, color=GRAY, lw=0.8)
p1 = stats.ttest_1samp(post - pre, 0).pvalue; p2 = stats.ttest_ind(post, pre).pvalue
axs[1].set_xlabel("後 − 前"); axs[1].set_ylabel("店の数"); axs[1].set_title(f"差だけ見ると p={p1:.3f}\n（対応なしだと p={p2:.2f}）", fontsize=11)
fig.tight_layout(); save(fig, "a656_example.png", SRC)
out["example_p_paired"] = round(float(p1), 4); out["example_p_unpaired"] = round(float(p2), 3)
json.dump(out, open(RES / "a656_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
