"""717 5段階の評価を1〜5の数として回帰するのと、順序ロジットで見るのとでは、効果の向きや有意はどれだけ違うのか

5段階の評価は、目に見えない「満足の度合い」（潜在変数）が区切りを超えたかで決まると考える。区切りは不ぞろい（−2.5・−1.5・−0.5・0.5）。
場面1：2つの案（各100人）。潜在変数はロジスティック分布で、案Bは平均が d だけ高い（d=0・0.25・0.5）。散らばりは同じ。
場面2：案Aは平均+0.3・散らばり1、案Bは平均0・散らばり2.5（B は好き嫌いが分かれる）。潜在の平均は A が高い。
比べ方：1〜5を数として t 検定（＝線形回帰）／順序ロジット（statsmodels の OrderedModel）／上位2つ（4・5）の割合の差の検定。
各300回、両側5%。seed 717。
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.miscmodels.ordinal_model import OrderedModel
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

warnings.filterwarnings("ignore")
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 717）"
rng = np.random.default_rng(717)
CUTS = [-2.5, -1.5, -0.5, 0.5]
N, REPS = 100, 300
x = np.repeat([0, 1], N)


def score(lat):
    return np.digitize(lat, CUTS) + 1


def tests(y):
    a, b = y[x == 0], y[x == 1]
    t = stats.ttest_ind(b, a)
    lin = (np.sign(b.mean() - a.mean()), t.pvalue)
    m = OrderedModel(y, x[:, None].astype(float), distr="logit").fit(method="bfgs", disp=False)
    ordl = (np.sign(m.params[0]), m.pvalues[0])
    pa, pb = (a >= 4).mean(), (b >= 4).mean(); p = (pa + pb) / 2
    z = (pb - pa) / np.sqrt(p * (1 - p) * 2 / N) if 0 < p < 1 else 0.0
    top = (np.sign(pb - pa), 2 * stats.norm.sf(abs(z)))
    return lin, ordl, top


M = ["1〜5を数として（t 検定）", "順序ロジット", "上位2つの割合"]
rows = []
for d in [0.0, 0.25, 0.5]:
    R = []
    for _ in range(REPS):
        lat = rng.logistic(0, 1, 2 * N) + d * x
        R.append(tests(score(lat)))
    rec = {"scenario": f"同じ散らばり d={d}"}
    for k, m in enumerate(M):
        rec[f"sig_{m}"] = round(float(np.mean([r[k][1] < 0.05 for r in R]) * 100), 1)
        rec[f"sig_correct_dir_{m}"] = round(float(np.mean([(r[k][1] < 0.05) and (r[k][0] > 0) for r in R]) * 100), 1)
    rows.append(rec)
# 場面2
R = []
for _ in range(REPS):
    lat = np.where(x == 0, 0.3 + rng.logistic(0, 1, 2 * N), 0.0 + 2.5 * rng.logistic(0, 1, 2 * N))
    R.append(tests(score(lat)))
rec = {"scenario": "散らばりが違う（潜在の平均は A が0.3高い）"}
for k, m in enumerate(M):
    rec[f"sig_{m}"] = round(float(np.mean([r[k][1] < 0.05 for r in R]) * 100), 1)
    rec[f"sig_B_higher_{m}"] = round(float(np.mean([(r[k][1] < 0.05) and (r[k][0] > 0) for r in R]) * 100), 1)
    rec[f"sig_A_higher_{m}"] = round(float(np.mean([(r[k][1] < 0.05) and (r[k][0] < 0) for r in R]) * 100), 1)
rows.append(rec)
T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)
# 場面2の母集団の分布（大きな標本で）
big = 400000
la = score(0.3 + rng.logistic(0, 1, big)); lb = score(2.5 * rng.logistic(0, 1, big))
dist = pd.DataFrame({"A": pd.Series(la).value_counts(normalize=True).sort_index(), "B": pd.Series(lb).value_counts(normalize=True).sort_index()}) * 100
lat0 = score(rng.logistic(0, 1, big))
out = {"cuts": CUTS, "per_group": N, "reps": REPS, "results": rows,
       "scenario2_population": {"mean_score_A": round(float(la.mean()), 3), "mean_score_B": round(float(lb.mean()), 3),
                                "top2_A_pct": round(float((la >= 4).mean() * 100), 1), "top2_B_pct": round(float((lb >= 4).mean() * 100), 1),
                                "dist_A_pct": dist.A.round(1).to_dict(), "dist_B_pct": dist.B.round(1).to_dict()},
       "base_distribution_pct": (pd.Series(lat0).value_counts(normalize=True).sort_index() * 100).round(1).to_dict()}
out["scenario2_population"]["dist_A_pct"] = {str(k): v for k, v in out["scenario2_population"]["dist_A_pct"].items()}
out["scenario2_population"]["dist_B_pct"] = {str(k): v for k, v in out["scenario2_population"]["dist_B_pct"].items()}
out["base_distribution_pct"] = {str(k): v for k, v in out["base_distribution_pct"].items()}
json.dump(out, open(RES / "a717_main.json", "w"), ensure_ascii=False, indent=1)

cols = [ORANGE, BLUE, GREEN]
# 図1：場面1の有意の割合
fig, ax = plt.subplots(figsize=(8, 3.8)); xs = np.arange(3); w = 0.25
for k, (m, c) in enumerate(zip(M, cols)):
    v = T.iloc[:3][f"sig_{m}"].values
    ax.bar(xs + (k - 1) * w, v, w, color=c, label=m)
    for i, a in enumerate(v):
        ax.text(i + (k - 1) * w, a + 1, f"{a:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(xs); ax.set_xticklabels(["効果0", "効果0.25", "効果0.5"]); ax.set_ylabel("「有意」になった割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("散らばりが同じなら、3つの見方の差は小さい（各100人・300回）")
save(fig, "a717_same_spread.png", SRC)
# 図2：場面2の分布
fig, ax = plt.subplots(figsize=(8, 3.6)); xs = np.arange(1, 6)
ax.bar(xs - 0.2, dist.A, 0.4, color=BLUE, label=f"案A（平均点{la.mean():.2f}）"); ax.bar(xs + 0.2, dist.B, 0.4, color=ORANGE, label=f"案B（平均点{lb.mean():.2f}）")
ax.set_xticks(xs); ax.set_xlabel("評価"); ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("場面2：B は好き嫌いが分かれ、5の割合は同じでも1が多い")
save(fig, "a717_split_dist.png", SRC)
# 図3：場面2の検定の向き
s2 = T.iloc[3]
fig, ax = plt.subplots(figsize=(8, 3.6)); xs = np.arange(3)
ax.bar(xs - 0.2, [s2[f"sig_B_higher_{m}"] for m in M], 0.4, color=ORANGE, label="「B が有意に高い」")
ax.bar(xs + 0.2, [s2[f"sig_A_higher_{m}"] for m in M], 0.4, color=BLUE, label="「A が有意に高い」")
ax.set_xticks(xs); ax.set_xticklabels(M, fontsize=9); ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("場面2：向きはどれも「A が高い」だが、有意になる割合は見方で46〜78%と違う", fontsize=11)
save(fig, "a717_split_tests.png", SRC)
print(T.to_string()); print(json.dumps(out["scenario2_population"], ensure_ascii=False))
