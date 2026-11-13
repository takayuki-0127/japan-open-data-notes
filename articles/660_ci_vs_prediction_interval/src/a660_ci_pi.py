"""660 回帰の「平均の区間」を新しい1件の予測の区間と取り違えると、何%の回が外れるのか

架空の店の「広告費 x と売上 y」：y = 2 + 0.5x + 雑音（標準偏差1）、x は0〜10の一様。
回帰を当てて、新しい1店（x0 ランダム）について次の2つの95%区間を作り、その店の本当の売上が入るかを見る。
  CI 平均の信頼区間（x0 の店の「平均的な」売上がどこにあるか）
  PI 予測区間（x0 の新しい1店の売上がどこにあるか）
件数 n=10〜2,000、各5,000回。1回分は statsmodels の get_prediction と一致を確かめる。seed 660。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 660）"
rng = np.random.default_rng(660)
A, B, S, REPS = 2.0, 0.5, 1.0, 5000
NS = [10, 20, 50, 100, 200, 500, 1000, 2000]


def bands(x, y, x0):
    n = len(x); X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta; s2 = res @ res / (n - 2)
    XtXi = np.linalg.inv(X.T @ X); v = np.array([1, x0])
    se_mean = np.sqrt(s2 * v @ XtXi @ v); se_pred = np.sqrt(s2 * (1 + v @ XtXi @ v))
    t = stats.t.ppf(0.975, n - 2); f = v @ beta
    return f, se_mean * t, se_pred * t


# 1回分を statsmodels で確かめる
x = rng.uniform(0, 10, 50); y = A + B * x + rng.normal(0, S, 50)
f, hc, hp = bands(x, y, 7.0)
sf = sm.OLS(y, sm.add_constant(x)).fit().get_prediction(np.array([[1, 7.0]])).summary_frame(alpha=0.05)
assert np.isclose(f - hc, sf.mean_ci_lower.iloc[0]) and np.isclose(f + hp, sf.obs_ci_upper.iloc[0])

rows = []
for n in NS:
    for r in range(REPS):
        x = rng.uniform(0, 10, n); y = A + B * x + rng.normal(0, S, n)
        x0 = rng.uniform(0, 10); y0 = A + B * x0 + rng.normal(0, S)
        f, hc, hp = bands(x, y, x0)
        rows.append((n, abs(y0 - f) <= hc, abs(y0 - f) <= hp, abs(A + B * x0 - f) <= hc, 2 * hc, 2 * hp))
R = pd.DataFrame(rows, columns=["n", "new_in_ci", "new_in_pi", "mean_in_ci", "ci_width", "pi_width"])
S_ = R.groupby("n").mean(); S_["ratio"] = S_.pi_width / S_.ci_width
S_.round(4).to_csv(RES / "summary.csv")
out = {"reps": REPS, "model": "y = 2 + 0.5x + N(0,1)",
       "by_n": {str(n): {"new_obs_in_CI_pct": round(float(S_.loc[n, "new_in_ci"]) * 100, 1), "new_obs_in_PI_pct": round(float(S_.loc[n, "new_in_pi"]) * 100, 1),
                         "true_mean_in_CI_pct": round(float(S_.loc[n, "mean_in_ci"]) * 100, 1), "ci_width": round(float(S_.loc[n, "ci_width"]), 3),
                         "pi_width": round(float(S_.loc[n, "pi_width"]), 3), "pi_over_ci": round(float(S_.loc[n, "ratio"]), 2)} for n in NS}}
json.dump(out, open(RES / "a660_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：新しい1店が入る割合
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(NS, S_.new_in_pi * 100, marker="o", color=BLUE, label="予測区間に入った割合")
ax.plot(NS, S_.new_in_ci * 100, marker="s", color=ORANGE, label="平均の信頼区間に入った割合")
ax.plot(NS, S_.mean_in_ci * 100, marker="^", color=GRAY, ls=":", label="（参考）平均が信頼区間に入った割合")
ax.axhline(95, color=GRAY, lw=0.8, ls="--"); ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS])
ax.set_xlabel("回帰に使った店の数（対数の目盛り）"); ax.set_ylabel("新しい1店の売上が区間に入った割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_title("件数が増えるほど、平均の区間は新しい1店を外す")
save(fig, "a660_coverage.png", SRC)
# 図2：幅の比
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar([f"{n:,}" for n in NS], S_.ratio, color=[ORANGE if v > 5 else LIGHT for v in S_.ratio])
for i, v in enumerate(S_.ratio):
    ax.text(i, v + 0.2, f"{v:.1f}倍", ha="center", fontsize=8.5)
ax.set_xlabel("回帰に使った店の数"); ax.set_ylabel("予測区間の幅 ÷ 平均の区間の幅")
ax.set_title("予測区間は、件数が増えても雑音の分より狭くならない")
save(fig, "a660_width_ratio.png", SRC)
# 図3：例（n=200）
r3 = np.random.default_rng(6603); n = 200
x = r3.uniform(0, 10, n); y = A + B * x + r3.normal(0, S, n)
grid = np.linspace(0, 10, 101)
bb = np.array([bands(x, y, g) for g in grid])
fig, ax = plt.subplots(figsize=(8, 4))
ax.scatter(x, y, s=8, color=GRAY, alpha=0.6)
ax.fill_between(grid, bb[:, 0] - bb[:, 2], bb[:, 0] + bb[:, 2], color=LIGHT, alpha=0.6, label="95%予測区間（新しい1店）")
ax.fill_between(grid, bb[:, 0] - bb[:, 1], bb[:, 0] + bb[:, 1], color=ORANGE, alpha=0.7, label="95%信頼区間（平均）")
ax.plot(grid, bb[:, 0], color=BLUE, lw=1.2)
ax.set_xlabel("広告費（架空の単位）"); ax.set_ylabel("売上（架空の単位）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("200店の1回分：点の多くは、平均の区間の外にある")
save(fig, "a660_example.png", SRC)
fit_in = np.mean([abs(yy - bands(x, y, xx)[0]) <= bands(x, y, xx)[1] for xx, yy in zip(x, y)])
out["example_n200_points_inside_CI_pct"] = round(float(fit_in) * 100, 1)
json.dump(out, open(RES / "a660_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
