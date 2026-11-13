"""648 効きの弱い操作変数を使うと、推定はどれだけふつうの回帰の側に引っぱられるのか

架空のデータ（500件）：操作変数 z、説明変数 x = π·z + v、結果 y = 1.0·x + u。u と v の相関は0.6（x は誤差と相関していて、
ふつうの回帰は大きく出る）。操作変数の効き π を、第1段階の F が平均でおよそ 1・3・10・30・100 になるように変える。
  OLS ふつうの回帰／2SLS 操作変数（2段階最小二乗）。z が3つ（それぞれ同じ効き）の場合も試す
推定値の中央値の偏り（本当は1.0）・四分位の幅・95%区間（ふつうの標準誤差）の当たり方を各2,000回で数える。
数字は置いた相関・件数・効きで決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 648）"
rng = np.random.default_rng(648)
N, BETA, RHO, REPS = 500, 1.0, 0.6, 2000
FTARGET = [1, 3, 10, 30, 100]


def draw(F, k):
    pi = np.sqrt(max(F - 1, 0.05) / N)          # 平均の F がおよそ目標になる効き（z が k 個なら F はおよそ 1+(F−1)/k）
    Z = rng.standard_normal((N, k))
    e = rng.multivariate_normal([0, 0], [[1, RHO], [RHO, 1]], N)
    x = Z.sum(1) * pi / np.sqrt(k) + e[:, 1]          # z の効きの合計は k によらず同じ
    y = BETA * x + e[:, 0]
    return Z, x, y


def fit(Z, x, y):
    n, k = Z.shape
    Zc = np.column_stack([np.ones(n), Z]); X = np.column_stack([np.ones(n), x])
    g = np.linalg.lstsq(Zc, x, rcond=None)[0]; xh = Zc @ g
    rss1 = ((x - xh) ** 2).sum(); tss1 = ((x - x.mean()) ** 2).sum()
    F = ((tss1 - rss1) / k) / (rss1 / (n - k - 1))
    b_ols = np.linalg.lstsq(X, y, rcond=None)[0][1]
    Xh = np.column_stack([np.ones(n), xh])
    b = np.linalg.lstsq(Xh, y, rcond=None)[0]
    res = y - X @ b
    s2 = (res ** 2).sum() / (n - 2)
    se = np.sqrt(s2 * np.linalg.inv(Xh.T @ Xh)[1, 1])
    return b[1], se, b_ols, F


rows = []
for k in [1, 3]:
    for F in FTARGET:
        for r in range(REPS):
            b, se, bo, f = fit(*draw(F, k))
            rows.append({"k": k, "F_target": F, "rep": r, "iv": b, "se": se, "ols": bo, "F": f})
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
S = D.groupby(["k", "F_target"]).apply(lambda g: pd.Series({
    "F_mean": g.F.mean(), "iv_median": g.iv.median(), "iv_bias_median": g.iv.median() - BETA,
    "iv_iqr": g.iv.quantile(0.75) - g.iv.quantile(0.25), "ols_median": g.ols.median(),
    "coverage": ((g.iv - 1.96 * g.se <= BETA) & (BETA <= g.iv + 1.96 * g.se)).mean() * 100,
    "share_of_ols_bias": (g.iv.median() - BETA) / (g.ols.median() - BETA) * 100,
    "abs_gt1": (np.abs(g.iv - BETA) > 1).mean() * 100})).round(3)
S.to_csv(RES / "summary.csv")
out = {"n": N, "beta": BETA, "rho_uv": RHO, "reps": REPS, "k1": S.loc[1].to_dict(orient="index"), "k3": S.loc[3].to_dict(orient="index")}
json.dump(out, open(RES / "a648_main.json", "w"), ensure_ascii=False, indent=1)

lab = [f"F {S.loc[1].F_mean[f]:.0f}／{S.loc[3].F_mean[f]:.1f}" for f in FTARGET]
lab1 = [f"F≈{S.loc[1].F_mean[f]:.0f}" for f in FTARGET]
# 図1：推定値の分布（z が1つ）
fig, ax = plt.subplots(figsize=(8.5, 4.2))
d1 = D[D.k == 1]
data = [d1[d1.F_target == f].iv.clip(-1, 3) for f in FTARGET]
bp = ax.boxplot(data, showfliers=False, patch_artist=True, whis=[5, 95]); ax.set_xticks(range(1, len(lab) + 1)); ax.set_xticklabels(lab1)
for b in bp["boxes"]:
    b.set_facecolor(LIGHT)
ax.axhline(BETA, color=INK, ls="--", lw=1); ax.text(5.4, BETA, "本当の値1.0", va="bottom", ha="right", fontsize=8)
ax.axhline(d1.ols.median(), color=ORANGE, ls=":", lw=1.2); ax.text(5.4, d1.ols.median(), f"ふつうの回帰 {d1.ols.median():.2f}", va="bottom", ha="right", fontsize=8, color=ORANGE)
ax.set_ylabel("操作変数での推定値（箱は四分位、ひげは5〜95%点）"); ax.set_xlabel("第1段階の F（操作変数の効き）")
ax.set_title("効きが弱いほど、推定はふつうの回帰の側に寄り、大きく散らばる（z が1つ）")
save(fig, "a648_distribution.png", SRC)

# 図2：中央値の偏り（OLSの偏りに対する割合）
fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(len(FTARGET)); w = 0.38
for i, (k, c) in enumerate([(1, BLUE), (3, GREEN)]):
    v = S.loc[k].share_of_ols_bias.values
    ax.bar(x + (i - 0.5) * w, v, w, color=c, label=f"操作変数が{k}つ")
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 0.5) * w, vi, f"{vi:.0f}%", ha="center", va="bottom", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_xlabel("第1段階の F の平均（z が1つ／3つ）"); ax.set_ylabel("ふつうの回帰の偏りの何%残るか（中央値）")
ax.legend(frameon=False, fontsize=9); ax.set_title("同じ効きでも、操作変数を3つに分けると F が下がり、偏りが残る")
save(fig, "a648_bias_share.png", SRC)

# 図3：95%区間の当たり方
fig, ax = plt.subplots(figsize=(8, 3.8))
for k, c in [(1, BLUE), (3, GREEN)]:
    ax.plot(lab, S.loc[k].coverage, marker="o", color=c, label=f"操作変数が{k}つ")
ax.axhline(95, color=GRAY, ls="--", lw=0.8); ax.set_ylim(0, 100); ax.set_ylabel("95%区間が本当の値を含んだ割合（%）")
ax.set_xlabel("第1段階の F の平均（z が1つ／3つ）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("効きが弱いと、ふつうの標準誤差の区間は当たらない")
save(fig, "a648_coverage.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
