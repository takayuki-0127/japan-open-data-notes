"""797 2つの95%区間が重なっていたら「差なし」と読むと、本当は差がある場合を何%見逃すのか

架空のデータ。2つの群（各50件、標準偏差1）。本当の差 d を 0〜0.8 に変え、各5,000回。
それぞれの群の平均の95%区間（t 分布）を出し、
  区間が重なれば「差なし」とする読み方／差の t 検定（5%）／差の95%区間が0を含むか
で「差あり」と言えた割合を比べる。区間が重なっていたのに t 検定では有意だった割合も数える。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 797）"
rng = np.random.default_rng(797)
N, R = 50, 5000
DS = np.round(np.arange(0, .85, .1), 2)
tq = stats.t.ppf(.975, N - 1)
rows = []
for d in DS:
    a = rng.standard_normal((R, N)); b = rng.standard_normal((R, N)) + d
    ma, mb = a.mean(1), b.mean(1); sa, sb = a.std(1, ddof=1) / np.sqrt(N), b.std(1, ddof=1) / np.sqrt(N)
    overlap = (ma + tq * sa >= mb - tq * sb) & (mb + tq * sb >= ma - tq * sa)
    t, p = stats.ttest_ind(b, a, axis=1)
    rows.append(dict(d=d, overlap_says_diff=float((~overlap).mean()), ttest_says_diff=float((p < .05).mean()),
                     overlap_but_sig=float((overlap & (p < .05)).mean()), share_overlap=float(overlap.mean()),
                     sig_given_overlap=float((p[overlap] < .05).mean()) if overlap.any() else np.nan))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
# 区間が重ならない ⇔ 差が 2×1.96×SE を超える。差の検定は √2×1.96×SE。重なり読みの実際の有意水準
alpha_overlap = float(2 * stats.norm.sf(1.96 * np.sqrt(2)))
g = lambda d, c: float(S[np.isclose(S.d, d)][c].iloc[0])
out = {"n_per_group": N, "reps": R, "alpha_overlap_rule_approx": alpha_overlap,
       "by_d": S.round(4).set_index("d").to_dict(orient="index"),
       "d05_overlap": g(.5, "overlap_says_diff"), "d05_ttest": g(.5, "ttest_says_diff"),
       "d05_miss_overlap": 1 - g(.5, "overlap_says_diff"), "d05_miss_ttest": 1 - g(.5, "ttest_says_diff"),
       "d0_overlap": g(0, "overlap_says_diff"), "d0_ttest": g(0, "ttest_says_diff"),
       "d05_overlap_but_sig": g(.5, "overlap_but_sig"), "d05_sig_given_overlap": g(.5, "sig_given_overlap"),
       "max_overlap_but_sig": float(S.overlap_but_sig.max()), "d_at_max_overlap_but_sig": float(S.d[S.overlap_but_sig.idxmax()])}
json.dump(out, open(RES / "a797_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例（区間が重なるのに有意）
while True:
    a = rng.standard_normal(N); b = rng.standard_normal(N) + .5
    ma, mb = a.mean(), b.mean(); sa, sb = a.std(ddof=1) / np.sqrt(N), b.std(ddof=1) / np.sqrt(N)
    p = stats.ttest_ind(b, a).pvalue
    if ma + tq * sa > mb - tq * sb and p < .03: break
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for i, (m, s, c, l) in enumerate([(ma, sa, GRAY, "A"), (mb, sb, BLUE, "B")]):
    ax.errorbar(i, m, yerr=tq * s, fmt="o", color=c, capsize=8, lw=2, ms=8)
    ax.text(i + .08, m, f"群{l}：平均 {m:.2f}\n95%区間 {m-tq*s:.2f}〜{m+tq*s:.2f}", va="center", fontsize=9)
ax.axhspan(mb - tq * sb, ma + tq * sa, color=ORANGE, alpha=.15); ax.set_xlim(-.5, 1.9); ax.set_xticks([0, 1]); ax.set_xticklabels(["群A", "群B"])
dd = mb - ma; sd = np.sqrt(sa ** 2 + sb ** 2); tq2 = stats.t.ppf(.975, 2 * N - 2)
ax.set_ylabel("平均"); ax.set_title(f"区間は重なっている（オレンジ）が、差の検定では p＝{p:.3f}、差の95%区間は {dd-tq2*sd:.2f}〜{dd+tq2*sd:.2f}")
save(fig, "a797_example.png", SRC)

# 図2：差あり、と言えた割合
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(S.d, S.ttest_says_diff * 100, "o-", color=BLUE, label="差の t 検定（5%）")
ax.plot(S.d, S.overlap_says_diff * 100, "o-", color=ORANGE, label="2つの区間が重ならない")
ax.set_xlabel("本当の差（標準偏差を1とした差）"); ax.set_ylabel("「差あり」と言えた割合（%）"); ax.legend(frameon=False)
ax.set_title("区間の重なりで読むと、本当の差を見つける割合が大きく下がる（各群50件）")
save(fig, "a797_detect.png", SRC)

# 図3：区間が重なったのに有意だった割合
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.bar(S.d, S.overlap_but_sig * 100, width=.07, color=ORANGE)
for x, v in zip(S.d, S.overlap_but_sig): ax.text(x, v * 100 + .4, f"{v:.0%}", ha="center", fontsize=9)
ax.set_xlabel("本当の差"); ax.set_ylabel("全体のうち「重なる・有意」の割合（%）")
ax.set_title("区間が重なっていても、差の検定では有意、という回がこれだけある")
save(fig, "a797_overlap_sig.png", SRC)
print(S.round(3).to_string()); print(alpha_overlap)
