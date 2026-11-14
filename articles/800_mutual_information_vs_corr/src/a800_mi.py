"""800 U字の関係では、相関係数と相互情報量はどれだけ違う答えを出すのか

架空のデータ。x は −1〜1 の一様分布、y は次の4つの関係に、ばらつきを足したもの。
  直線：y = x　　U字：y = x²　　波：y = sin(3πx)　　関係なし：y は x と無関係
件数 n（50・200・1,000）で各300回、ピアソンの相関・スピアマンの相関（絶対値）・相互情報量（k 近傍で推定）を出す。
「関係なし」の300回の95%点を物差しにして、それを超えた割合を「関係を見つけた割合」とする。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from sklearn.feature_selection import mutual_info_regression
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 800）"
rng = np.random.default_rng(800)
R = 300
NS = [50, 200, 1000]
SHAPES = {"linear": lambda x: x, "u": lambda x: x ** 2 - 1 / 3, "wave": lambda x: np.sin(3 * np.pi * x), "none": lambda x: 0 * x}
NOISE = {"linear": .35, "u": .1, "wave": .35, "none": .35}
NAME = {"linear": "直線", "u": "U字", "wave": "波", "none": "関係なし"}


def make(shape, n):
    x = rng.uniform(-1, 1, n)
    y = SHAPES[shape](x) * (1 if shape != "none" else 0) + rng.normal(0, NOISE[shape], n)
    if shape == "none": y = rng.normal(0, .35, n)
    return x, y


def measures(x, y, seed):
    return (abs(stats.pearsonr(x, y)[0]), abs(stats.spearmanr(x, y)[0]),
            float(mutual_info_regression(x.reshape(-1, 1), y, n_neighbors=3, random_state=seed)[0]))


rows = []
for n in NS:
    for shape in SHAPES:
        for r in range(R):
            x, y = make(shape, n)
            p, s, mi = measures(x, y, r)
            rows.append(dict(n=n, shape=shape, rep=r, pearson=p, spearman=s, mi=mi))
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
summ = []
for n in NS:
    null = D[(D.n == n) & (D["shape"] == "none")]
    th = {m: null[m].quantile(.95) for m in ["pearson", "spearman", "mi"]}
    for shape in SHAPES:
        d = D[(D.n == n) & (D["shape"] == shape)]
        summ.append(dict(n=n, shape=shape, **{f"{m}_mean": d[m].mean() for m in th}, **{f"{m}_detect": float((d[m] > th[m]).mean()) for m in th}))
S = pd.DataFrame(summ); S.to_csv(RES / "summary.csv", index=False)
g = lambda n, sh, c: float(S[(S.n == n) & (S["shape"] == sh)][c].iloc[0])
out = {"reps": R, "ns": NS,
       "by": {f"{sh}_n{n}": {c: round(g(n, sh, c), 3) for c in S.columns if c not in ("n", "shape")} for n in NS for sh in SHAPES},
       "u_n200_pearson_mean": g(200, "u", "pearson_mean"), "u_n200_mi_mean": g(200, "u", "mi_mean"),
       "u_n200_pearson_detect": g(200, "u", "pearson_detect"), "u_n200_mi_detect": g(200, "u", "mi_detect"),
       "lin_n200_pearson_mean": g(200, "linear", "pearson_mean"), "lin_n200_mi_mean": g(200, "linear", "mi_mean"),
       "wave_n200_mi_detect": g(200, "wave", "mi_detect"), "wave_n200_pearson_detect": g(200, "wave", "pearson_detect"),
       "u_n50_mi_detect": g(50, "u", "mi_detect"), "lin_n50_pearson_detect": g(50, "linear", "pearson_detect"), "lin_n50_mi_detect": g(50, "linear", "mi_detect")}
json.dump(out, open(RES / "a800_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：4つの関係の例と、3つの物差し（n=200）
fig, axs = plt.subplots(1, 4, figsize=(12, 3.6))
for ax, shape in zip(axs, SHAPES):
    x, y = make(shape, 200); p, s, mi = measures(x, y, 0)
    ax.scatter(x, y, s=6, color=BLUE)
    ax.set_title(f"{NAME[shape]}\nピアソン {p:.2f}／相互情報量 {mi:.2f}", fontsize=10); ax.set_xticks([-1, 0, 1])
fig.suptitle("U字や波は、はっきりした関係でも相関係数は小さい（200件）", y=1.06)
save(fig, "a800_examples.png", SRC, y=-0.07)

# 図2：見つけた割合（n=200）
fig, ax = plt.subplots(figsize=(9, 4.4)); s = S[S.n == 200]; x = np.arange(4); w = .27
for j, (m, c, l) in enumerate([("pearson", ORANGE, "ピアソン"), ("spearman", GRAY, "スピアマン"), ("mi", BLUE, "相互情報量")]):
    ax.bar(x + (j - 1) * w, s[f"{m}_detect"] * 100, w, color=c, label=l)
    for xi, v in zip(x, s[f"{m}_detect"]): ax.text(xi + (j - 1) * w, v * 100 + 1, f"{v:.0%}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([NAME[k] for k in s["shape"]]); ax.set_ylabel("関係を見つけた割合（%）"); ax.set_ylim(0, 112)
ax.legend(frameon=False, ncol=3, loc="upper center"); ax.set_title("U字は相互情報量だけが見つけた。相関係数は「関係なし」とほぼ同じ（200件、300回）")
save(fig, "a800_detect.png", SRC)

# 図3：件数と見つけた割合（直線と U字）
fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, shape in zip(axs, ["linear", "u"]):
    s = S[S["shape"] == shape]
    for m, c, l in [("pearson", ORANGE, "ピアソン"), ("spearman", GRAY, "スピアマン"), ("mi", BLUE, "相互情報量")]:
        ax.plot(s.n, s[f"{m}_detect"] * 100, "o-", color=c, label=l)
    ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS); ax.set_xlabel("件数"); ax.set_title(NAME[shape], fontsize=11)
axs[0].set_ylabel("関係を見つけた割合（%）"); axs[1].legend(frameon=False)
fig.suptitle("直線なら相関係数で十分。U字は相互情報量でないと見つからない", y=1.03)
save(fig, "a800_by_n.png", SRC, y=-0.06)
print(S.round(3).to_string())
