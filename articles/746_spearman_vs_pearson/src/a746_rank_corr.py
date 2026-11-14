"""746 曲がった単調な関係で、ピアソンの相関とスピアマンの相関はどれだけ違うのか

架空のデータ。x は 0〜1 の一様分布、y = exp(c·x) に少しのばらつき（順位がほぼ保たれる程度）を足す。
曲がり方 c を 0（直線）〜 10 に変え、件数50で各1,000回、ピアソン（値の相関）・スピアマン（順位の相関）・ケンドール（順位の組の一致）を出す。
あわせて、直線の関係（本当の相関0.5）に外れ値を1点だけ足したとき、3つがどう動くかを見る。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 746）"
rng = np.random.default_rng(746)
N, R = 50, 1000
CS = [0, 1, 2, 4, 6, 8, 10]


def curve(c, n):
    x = rng.random(n)
    base = x if c == 0 else (np.exp(c * x) - 1) / (np.exp(c) - 1)
    y = base + rng.normal(0, .03, n) * (1 if c == 0 else base + .02)   # ばらつきは値に比例（順位はほぼ保つ）
    return x, y


def three(x, y):
    return stats.pearsonr(x, y)[0], stats.spearmanr(x, y)[0], stats.kendalltau(x, y)[0]


rows = []
for c in CS:
    v = np.array([three(*curve(c, N)) for _ in range(R)])
    rows.append(dict(c=c, pearson=v[:, 0].mean(), spearman=v[:, 1].mean(), kendall=v[:, 2].mean(),
                     pearson_p05=np.quantile(v[:, 0], .05), pearson_p95=np.quantile(v[:, 0], .95)))
S = pd.DataFrame(rows); S.to_csv(RES / "by_curvature.csv", index=False)

# 外れ値1点
rows2 = []
for out_y in [0, 3, 6, 10, 20]:
    v = []
    for r in range(R):
        x = rng.standard_normal(N - 1); y = .5 * x + np.sqrt(.75) * rng.standard_normal(N - 1)
        if out_y:
            x = np.append(x, 3.0); y = np.append(y, -out_y)       # 右下に外れ値
        else:
            x = np.append(x, rng.standard_normal()); y = np.append(y, .5 * x[-1] + np.sqrt(.75) * rng.standard_normal())
        v.append(three(x, y))
    v = np.array(v)
    rows2.append(dict(outlier_y=-out_y, pearson=v[:, 0].mean(), spearman=v[:, 1].mean(), kendall=v[:, 2].mean()))
O = pd.DataFrame(rows2); O.to_csv(RES / "by_outlier.csv", index=False)

g = lambda c, k: float(S[S.c == c][k].iloc[0])
out = {"n": N, "reps": R, "by_c": {int(c): {k: round(g(c, k), 3) for k in ["pearson", "spearman", "kendall"]} for c in CS},
       "c10_pearson": g(10, "pearson"), "c10_spearman": g(10, "spearman"), "c10_kendall": g(10, "kendall"),
       "c6_pearson": g(6, "pearson"), "c6_spearman": g(6, "spearman"),
       "c10_pearson_p05_p95": [g(10, "pearson_p05"), g(10, "pearson_p95")],
       "outlier": {int(r.outlier_y): {"pearson": round(r.pearson, 3), "spearman": round(r.spearman, 3), "kendall": round(r.kendall, 3)} for r in O.itertuples()}}
json.dump(out, open(RES / "a746_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：曲がり方の例
fig, axs = plt.subplots(1, 3, figsize=(10, 3.6), sharey=False)
for ax, c in zip(axs, [0, 4, 10]):
    x, y = curve(c, N); p, s, k = three(x, y)
    ax.scatter(x, y, s=12, color=BLUE)
    ax.set_title(f"曲がり c={c}\nピアソン {p:.2f}／スピアマン {s:.2f}", fontsize=10)
    ax.set_xlabel("x")
axs[0].set_ylabel("y")
fig.suptitle("どれも x が増えると y も増える（単調）。曲がるほどピアソンだけが下がる", y=1.06)
save(fig, "a746_examples.png", SRC, y=-0.07)

# 図2：曲がり方と3つの相関
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(S.c, S.pearson, "o-", color=ORANGE, label="ピアソン（値）")
ax.fill_between(S.c, S.pearson_p05, S.pearson_p95, color=ORANGE, alpha=.15)
ax.plot(S.c, S.spearman, "o-", color=BLUE, label="スピアマン（順位）")
ax.plot(S.c, S.kendall, "o-", color=GREEN, label="ケンドール（順位の組）")
ax.set_xlabel("曲がり方 c（0 は直線）"); ax.set_ylabel("相関（1,000回の平均）"); ax.set_ylim(0, 1.05)
ax.legend(frameon=False, loc="lower left"); ax.set_title("単調な関係なら、順位の相関は曲がっても1に近いまま（50件、帯は90%）")
save(fig, "a746_by_curve.png", SRC)

# 図3：外れ値1点
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(O)); w = .27
for j, (k, l, c) in enumerate([("pearson", "ピアソン", ORANGE), ("spearman", "スピアマン", BLUE), ("kendall", "ケンドール", GREEN)]):
    b = ax.bar(x + (j - 1) * w, O[k], w, color=c, label=l)
    for bb in b:
        v = bb.get_height(); ax.text(bb.get_x() + w / 2, v + (.02 if v >= 0 else -.06), f"{v:.2f}", ha="center", fontsize=8)
ax.axhline(0, color=GRAY, lw=1)
ax.set_xticks(x); ax.set_xticklabels(["外れ値なし"] + [f"(3, {v})" for v in O.outlier_y[1:]])
ax.set_xlabel("足した外れ値の位置（x, y）。ほかの49点は本当の相関0.5"); ax.set_ylabel("相関（1,000回の平均）")
ax.legend(frameon=False); ax.set_title("外れ値1点で、ピアソンは0.5からマイナスまで動く。順位の相関は少しだけ")
save(fig, "a746_outlier.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
