"""658 ゼロを含むデータを log(y+c) で回帰すると、c の選び方で係数はどれだけ変わるのか

架空の商品×日の売上個数（ゼロが多い）。施策のあった日（x=1）は、売上の平均が本当に1.35倍（log で0.3）になる。
売上の平均の水準を変えて、ゼロの割合を変える（10%〜80%）。個数は負の二項分布（ばらつき大きめ）。
  L1 log(y+1) を OLS
  L01 log(y+0.1)、L001 log(y+0.01)
  LH log(y + 正の値の最小の半分)（個数なので0.5）
  P  ポアソン回帰（log の平均を当てる。ゼロをそのまま使える）
係数を exp(係数)−1 の「何%増えたか」で比べる。各設定500回、1設定 n=2,000。seed 658。
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
warnings.filterwarnings("ignore")
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 658）"
rng = np.random.default_rng(658)
B, N, REPS, K = 0.3, 2000, 500, 1.5   # 本当の効果、件数、くり返し、負の二項の形（小さいほどばらつく）
LEVELS = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 20.0]  # 施策なしの日の平均個数
CS = {"L1": 1.0, "LH": 0.5, "L01": 0.1, "L001": 0.01}


def ols_slope(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0][1]


rows = []
for mu0 in LEVELS:
    for r in range(REPS):
        x = (rng.random(N) < 0.5).astype(float)
        mu = mu0 * np.exp(B * x)
        lam = rng.gamma(K, mu / K)
        y = rng.poisson(lam)
        X = np.column_stack([np.ones(N), x])
        rec = {"mu0": mu0, "zero_share": (y == 0).mean()}
        for k, c in CS.items():
            rec[k] = ols_slope(X, np.log(y + c))
        rec["P"] = sm.GLM(y, X, family=sm.families.Poisson()).fit().params[1] if r < 200 else np.log(y[x == 1].mean() / y[x == 0].mean())
        rows.append(rec)
R = pd.DataFrame(rows)
# ポアソン回帰は2値の x では「平均の比の log」と同じ値になる（最初の200回で確かめる）
R.round(5).to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
S = R.groupby("mu0").mean()
for k in list(CS) + ["P"]:
    S[k + "_pct"] = (np.exp(S[k]) - 1) * 100
S.round(4).to_csv(RES / "summary.csv")
# 1回分でポアソン回帰と平均の比が一致することを確かめる
r1 = np.random.default_rng(6581); x = (r1.random(N) < 0.5).astype(float); y = r1.poisson(r1.gamma(K, 0.5 * np.exp(B * x) / K))
pfit = sm.GLM(y, np.column_stack([np.ones(N), x]), family=sm.families.Poisson()).fit().params[1]
assert np.isclose(pfit, np.log(y[x == 1].mean() / y[x == 0].mean()), atol=1e-6)
true_pct = (np.exp(B) - 1) * 100
out = {"true_coef": B, "true_increase_pct": round(true_pct, 1), "n": N, "reps": REPS, "nb_shape": K,
       "by_level": {str(m): {"zero_share_pct": round(float(S.loc[m, "zero_share"]) * 100, 1),
                             **{k: round(float(S.loc[m, k + "_pct"]), 1) for k in list(CS) + ["P"]}} for m in LEVELS}}
json.dump(out, open(RES / "a658_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ゼロの割合と、増えた割合の推定
fig, ax = plt.subplots(figsize=(8.5, 4))
zs = S.zero_share * 100
for k, col, lab, mk in [("L001", GRAY, "log(y+0.01)", "v"), ("L01", LIGHT, "log(y+0.1)", "^"), ("LH", GREEN, "log(y+0.5)", "D"),
                        ("L1", ORANGE, "log(y+1)", "s"), ("P", BLUE, "ポアソン回帰", "o")]:
    ax.plot(zs, S[k + "_pct"], marker=mk, color=col, label=lab)
ax.axhline(true_pct, color="black", ls="--", lw=1, label=f"本当 +{true_pct:.0f}%")
ax.set_xlabel("ゼロの日の割合（%）"); ax.set_ylabel("施策で増えた割合の推定（%）"); ax.invert_xaxis()
ax.legend(frameon=False, fontsize=8.5, ncol=2); ax.set_title("ゼロが多いほど、c の選び方で推定が大きく変わる")
save(fig, "a658_by_zero_share.png", SRC)
# 図2：ゼロ50%前後の設定での分布
m_mid = min(LEVELS, key=lambda m: abs(S.loc[m, "zero_share"] - 0.55))
sub = R[R.mu0 == m_mid]
fig, ax = plt.subplots(figsize=(8, 3.8))
for k, col, lab in [("L1", ORANGE, "log(y+1)"), ("LH", GREEN, "log(y+0.5)"), ("L001", GRAY, "log(y+0.01)"), ("P", BLUE, "ポアソン回帰")]:
    ax.hist((np.exp(sub[k]) - 1) * 100, bins=40, alpha=0.6, color=col, label=lab)
ax.axvline(true_pct, color="black", ls="--", lw=1)
ax.set_xlabel("施策で増えた割合の推定（%）"); ax.set_ylabel("回数（500回中）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"ゼロが{S.loc[m_mid, 'zero_share'] * 100:.0f}%のとき：同じデータで +{(np.exp(S.loc[m_mid, 'L1']) - 1) * 100:.0f}% から +{(np.exp(S.loc[m_mid, 'L001']) - 1) * 100:.0f}% まで")
save(fig, "a658_dist_mid.png", SRC)
# 図3：c を細かく変える（1回分のデータ）
r3 = np.random.default_rng(6583); x = (r3.random(N) < 0.5).astype(float); y = r3.poisson(r3.gamma(K, m_mid * np.exp(B * x) / K))
cgrid = np.logspace(-4, 1, 41); X = np.column_stack([np.ones(N), x])
est = [(np.exp(ols_slope(X, np.log(y + c))) - 1) * 100 for c in cgrid]
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(cgrid, est, color=ORANGE); ax.set_xscale("log"); ax.axhline(true_pct, color="black", ls="--", lw=1)
ax.axhline((np.exp(np.log(y[x == 1].mean() / y[x == 0].mean())) - 1) * 100, color=BLUE, lw=1, label="ポアソン回帰（このデータ）")
ax.set_xlabel("足す数 c（対数の目盛り）"); ax.set_ylabel("増えた割合の推定（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("同じ1つのデータでも、c を小さくするほど効果は大きく出る")
save(fig, "a658_c_curve.png", SRC)
out["mid_level"] = m_mid; out["c_curve_min_pct"] = round(float(min(est)), 1); out["c_curve_max_pct"] = round(float(max(est)), 1)
json.dump(out, open(RES / "a658_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
