"""698 件数が多いと、正規性の検定はどれだけ小さなずれでも「正規でない」と言うのか

架空のデータ。3つの分布から n 件を取り、Shapiro–Wilk と Jarque–Bera（5%）で「正規でない」と言う割合を数える。
- 正規分布（ずれなし）
- 少し右に歪んだ分布：ガンマ分布（形 100、歪度 0.2）を標準化
- 少し裾が重い分布：t 分布（自由度 20、尖度の超過 0.375）を標準化
n＝20・50・100・300・1,000・3,000・5,000、各1,000回。seed 698。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 698）"
rng = np.random.default_rng(698)
NS = [20, 50, 100, 300, 1000, 3000, 5000]
REPS = 1000
SHAPE, DF = 100, 20
DIST = {"正規分布": lambda n: rng.normal(0, 1, n),
        "少し歪んだ分布": lambda n: (rng.gamma(SHAPE, 1, n) - SHAPE) / np.sqrt(SHAPE),
        "少し裾が重い分布": lambda n: rng.standard_t(DF, n) / np.sqrt(DF / (DF - 2))}

rows = []
keep = {}
for name, gen in DIST.items():
    for n in NS:
        sw = np.empty(REPS); jb = np.empty(REPS)
        for i in range(REPS):
            x = gen(n); sw[i] = stats.shapiro(x).pvalue; jb[i] = stats.jarque_bera(x).pvalue
            if n == 5000 and i == 0: keep[name] = x
        rows.append({"dist": name, "n": n, "sw_reject": (sw < 0.05).mean() * 100, "jb_reject": (jb < 0.05).mean() * 100})
S = pd.DataFrame(rows); S.round(2).to_csv(RES / "summary.csv", index=False)


def r(d, n, t):
    return round(float(S[(S.dist == d) & (S.n == n)][t].iloc[0]), 1)


# ずれの大きさ：上側1%点と、密度の差の最大
q = 0.99
z99 = stats.norm.ppf(q)
g99 = (stats.gamma.ppf(q, SHAPE) - SHAPE) / np.sqrt(SHAPE)
t99 = stats.t.ppf(q, DF) / np.sqrt(DF / (DF - 2))
xs = np.linspace(-4, 4, 801)
dens = {"正規分布": stats.norm.pdf(xs),
        "少し歪んだ分布": stats.gamma.pdf(xs * np.sqrt(SHAPE) + SHAPE, SHAPE) * np.sqrt(SHAPE),
        "少し裾が重い分布": stats.t.pdf(xs * np.sqrt(DF / (DF - 2)), DF) * np.sqrt(DF / (DF - 2))}
out = {"reps": REPS, "n_list": NS,
       "normal_reject": {str(n): [r("正規分布", n, "sw_reject"), r("正規分布", n, "jb_reject")] for n in NS},
       "skew_reject": {str(n): [r("少し歪んだ分布", n, "sw_reject"), r("少し歪んだ分布", n, "jb_reject")] for n in NS},
       "heavy_reject": {str(n): [r("少し裾が重い分布", n, "sw_reject"), r("少し裾が重い分布", n, "jb_reject")] for n in NS},
       "skewness": round(2 / np.sqrt(SHAPE), 3), "excess_kurtosis_t": round(6 / (DF - 4), 3),
       "q99": {"normal": round(float(z99), 3), "skew": round(float(g99), 3), "heavy": round(float(t99), 3)},
       "max_density_gap": {k: round(float(np.abs(v - dens["正規分布"]).max()), 4) for k, v in dens.items() if k != "正規分布"}}
json.dump(out, open(RES / "a698_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：件数と「正規でない」と言う割合
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
cols = {"正規分布": GRAY, "少し歪んだ分布": ORANGE, "少し裾が重い分布": BLUE}
for ax, (t, lab) in zip(axes, [("sw_reject", "Shapiro–Wilk"), ("jb_reject", "Jarque–Bera")]):
    for d, c in cols.items():
        s = S[S.dist == d]; ax.plot(s.n, s[t], marker="o", color=c, label=d)
    ax.axhline(5, color=INK, lw=0.7, ls=":"); ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS], fontsize=8.5)
    ax.set_xlabel("件数"); ax.set_title(lab)
axes[0].set_ylabel("「正規でない」と言った割合（%）"); axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("ほぼ正規の分布でも、件数が数千になると、検定はほぼ毎回「正規でない」と言う", y=1.02)
save(fig, "a698_reject_by_n.png", SRC)

# 図2：分布の形の違い（密度）
fig, ax = plt.subplots(figsize=(8.5, 3.6))
for d, c in cols.items(): ax.plot(xs, dens[d], color=c, lw=1.6 if d != "正規分布" else 2.4, label=d, ls="-" if d != "正規分布" else "--")
ax.set_xlim(-4, 4); ax.set_xlabel("標準化した値"); ax.set_ylabel("密度")
ax.set_title(f"3つの形はほぼ重なる（上側1%点：正規 {z99:.2f}、歪み {g99:.2f}、裾 {t99:.2f}）")
ax.legend(frameon=False, fontsize=9)
save(fig, "a698_density.png", SRC)

# 図3：5,000件の Q-Q プロット
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4))
for ax, d in zip(axes, ["少し歪んだ分布", "少し裾が重い分布"]):
    x = np.sort(keep[d]); th = stats.norm.ppf((np.arange(1, len(x) + 1) - 0.5) / len(x))
    ax.scatter(th, x, s=3, color=cols[d], alpha=0.6); ax.plot([-4, 4], [-4, 4], color=INK, lw=0.8)
    p1 = stats.shapiro(x).pvalue
    ax.set_title(f"{d}（5,000件）\nShapiro–Wilk の p＝{p1:.1e}", fontsize=11); ax.set_xlabel("正規分布の分位点")
axes[0].set_ylabel("データの分位点")
fig.suptitle("Q-Q プロットでは、ずれは端の数点だけ", y=1.03)
save(fig, "a698_qq.png", SRC)
print(json.dumps(out, ensure_ascii=False))
