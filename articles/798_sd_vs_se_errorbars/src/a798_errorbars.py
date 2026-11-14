"""798 グラフのひげが標準偏差か標準誤差かを取り違えると、差の大きさはどれだけ違って見えるのか

架空のデータ。2つの群（標準偏差1）。本当の差 d＝0.3（1人1人で見ると、B が A より大きい確率は58%）。
各群の件数 n を 10〜1,000 に変え、各2,000回、
  ひげ＝標準偏差（SD）／標準誤差（SE）／平均の95%区間
で、2つのひげが重ならない割合と、差の t 検定で有意な割合を比べる。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 798）"
rng = np.random.default_rng(798)
D_TRUE, R = 0.3, 2000
NS = [10, 30, 100, 300, 1000]
rows = []
for n in NS:
    a = rng.standard_normal((R, n)); b = rng.standard_normal((R, n)) + D_TRUE
    ma, mb = a.mean(1), b.mean(1); sa, sb = a.std(1, ddof=1), b.std(1, ddof=1)
    tq = stats.t.ppf(.975, n - 1)
    sep = lambda ha, hb: float(((ma + ha) < (mb - hb)).mean())
    p = stats.ttest_ind(b, a, axis=1).pvalue
    rows.append(dict(n=n, sd_len=float(sa.mean()), se_len=float((sa / np.sqrt(n)).mean()), ratio=float(np.sqrt(n)),
                     sep_sd=sep(sa, sb), sep_se=sep(sa / np.sqrt(n), sb / np.sqrt(n)), sep_ci=sep(tq * sa / np.sqrt(n), tq * sb / np.sqrt(n)),
                     sig=float((p < .05).mean())))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
p_sup = float(stats.norm.cdf(D_TRUE / np.sqrt(2)))
g = lambda n, c: float(S[S.n == n][c].iloc[0])
out = {"true_d": D_TRUE, "reps": R, "prob_b_gt_a": p_sup, "overlap_of_individuals": float(2 * stats.norm.cdf(-D_TRUE / 2)),
       "by_n": S.round(4).set_index("n").to_dict(orient="index"),
       "n1000_sep_se": g(1000, "sep_se"), "n1000_sep_sd": g(1000, "sep_sd"), "n1000_sig": g(1000, "sig"),
       "n100_sep_se": g(100, "sep_se"), "n100_sep_ci": g(100, "sep_ci"), "n100_sig": g(100, "sig"),
       "n30_sep_se": g(30, "sep_se"), "n30_sig": g(30, "sig")}
json.dump(out, open(RES / "a798_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：同じデータを3通りのひげで（n=300）
n = 300; a = rng.standard_normal(n); b = rng.standard_normal(n) + D_TRUE
fig, axs = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
for ax, (h, t) in zip(axs, [(lambda x: x.std(ddof=1), "ひげ＝標準偏差（SD）"), (lambda x: x.std(ddof=1) / np.sqrt(n), "ひげ＝標準誤差（SE）"),
                            (lambda x: stats.t.ppf(.975, n - 1) * x.std(ddof=1) / np.sqrt(n), "ひげ＝平均の95%区間")]):
    for i, (x, c) in enumerate([(a, GRAY), (b, BLUE)]):
        ax.bar(i, x.mean(), color=c, alpha=.35, width=.6); ax.errorbar(i, x.mean(), yerr=h(x), fmt="o", color=c, capsize=8, lw=2)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["群A", "群B"]); ax.set_title(t, fontsize=11); ax.axhline(0, color=GRAY, lw=.6)
axs[0].set_ylabel("平均")
fig.suptitle(f"同じデータ（各{n}件、本当の差0.3）でも、ひげの意味でまったく違う図に見える", y=1.03)
save(fig, "a798_three_bars.png", SRC, y=-0.06)

# 図2：SD と SE の長さの比
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.plot(S.n, S.sd_len, "o-", color=ORANGE, label="標準偏差（1人1人のばらつき）")
ax.plot(S.n, S.se_len, "o-", color=BLUE, label="標準誤差（平均の不確かさ）")
for x, s1, s2 in zip(S.n, S.sd_len, S.se_len): ax.text(x, s2 * .75, f"1/{np.sqrt(x):.0f}", ha="center", fontsize=9, color=BLUE)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
ax.set_xlabel("各群の件数"); ax.set_ylabel("ひげの長さ（片側、対数）"); ax.legend(frameon=False)
ax.set_title("標準誤差は標準偏差の 1/√件数。件数が多いほど、2つの差は大きくなる")
save(fig, "a798_length.png", SRC)

# 図3：ひげが重ならない割合と有意な割合
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for c, col, l in [("sep_sd", ORANGE, "SD のひげが重ならない"), ("sep_se", BLUE, "SE のひげが重ならない"), ("sep_ci", GREEN, "95%区間のひげが重ならない"), ("sig", "#0b0b0b", "差の t 検定で有意")]:
    ax.plot(S.n, S[c] * 100, "o-", color=col, label=l, ls="--" if c == "sig" else "-")
ax.axhline(p_sup * 100, color=GRAY, ls=":", lw=1); ax.text(10, p_sup * 100 + 2, f"1人1人で B＞A の確率は {p_sup:.0%}", fontsize=9, color=GRAY)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS); ax.set_xlabel("各群の件数"); ax.set_ylabel("割合（%）")
ax.legend(frameon=False, fontsize=9, loc="center right"); ax.set_title("SE のひげは件数が多いとすぐ離れるが、1人1人の差はずっと小さいまま")
save(fig, "a798_separation.png", SRC)
print(S.round(3).to_string()); print(p_sup, out["overlap_of_individuals"])
