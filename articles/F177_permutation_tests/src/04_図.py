"""F177 の図（5枚）"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, FIG, DATA

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
C1, C2, C3, C4, GR = "#2b6cb0", "#dd6b20", "#2f855a", "#805ad5", "#a0aec0"
S = json.load(open(RES / "summary.json"))

# 図1：例1 並べ替えの分布と、1地点ずつ抜いたときの p
null = np.load(RES / "_ex1_null_mean.npy")
loo = pd.read_csv(RES / "ex1_leave_one_out.csv").sort_values("p_perm").reset_index(drop=True)
obs = S["ex1"]["diff"]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
ax[0].hist(null, bins=60, color=GR, density=True)
e1 = pd.read_csv(DATA / "ex1_heat_trend.csv")
se = np.sqrt(e1[e1.group == "U"].mu1.var(ddof=1) / 15 + e1[e1.group == "R"].mu1.var(ddof=1) / 15)
xs = np.linspace(null.min(), null.max(), 300)
ax[0].plot(xs, stats.norm.pdf(xs, 0, se), color=C1, lw=1.5, label="t 検定が想定する形（近似）")
for v in [obs, -obs]:
    ax[0].axvline(v, color=C2, lw=2)
ax[0].set_title("都市15地点と都市以外15地点を、でたらめに分け直した差")
ax[0].set_xlabel("年最高気温の上がり方の差（℃／100年）"); ax[0].set_ylabel("密度")
ax[0].text(obs, ax[0].get_ylim()[1] * 0.9, f" 実際の差 +{obs:.2f}\n 並べ替え p={S['ex1']['p_perm']['mean']:.3f}\n Welch p={S['ex1']['p_welch']:.3f}", color=C2, fontsize=9, va="top")
ax[0].legend(loc="upper left", fontsize=8, frameon=False)
ax[1].scatter(range(len(loo)), loo.p_perm, color=[C2 if g == "U" else C1 for g in loo.group], s=22, zorder=3)
ax[1].axhline(0.05, color="k", lw=1, ls="--")
ax[1].set_title("1地点ずつ抜いて並べ替え検定をやり直した p")
ax[1].set_xlabel("抜いた地点（p の小さい順。橙=都市、青=都市以外）"); ax[1].set_ylabel("並べ替え p")
ax[1].text(0.5, 0.052, "p=0.05", fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "f177_1_heat_permutation.png", dpi=150); plt.close()

# 図2：並べ替えの回数と p の揺れ
cv = pd.read_csv(RES / "ex1_number_of_permutations.csv")
fig, ax = plt.subplots(figsize=(7, 4.2))
xb = np.arange(len(cv))
ax.vlines(xb, cv.p_min, cv.p_max, color=C1, lw=6, alpha=0.5)
ax.scatter(xb, cv.p_median, color=C1, zorder=3)
ax.axhline(0.05, color="k", ls="--", lw=1)
ax.set_xticks(xb, [f"{b:,}回" for b in cv.B])
for i, r in cv.iterrows():
    ax.text(i + 0.08, r.p_max, f"{r.p_min:.3f}〜{r.p_max:.3f}\n0.05未満 {int(r.share_below_005*20)}/20", fontsize=8, va="top")
ax.set_ylabel("並べ替え p（種を変えて20回）"); ax.set_xlabel("並べ替えの回数")
ax.set_title("同じデータでも、並べ替えの回数が少ないと p が揺れる（例1）")
fig.tight_layout(); fig.savefig(FIG / "f177_2_number_of_permutations.png", dpi=150); plt.close()

# 図3：例2 Welch の p と、2つの並べ替えの p
e2 = pd.read_csv(RES / "ex2_per_indicator.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), sharey=False)
for a, col, ttl, c in [(ax[0], "p_perm_mean", "県をばらばらに並べ替え（1万回）", C1),
                       (ax[1], "p_contig_mean", "隣どうしつながる17県を選び直す（5千回）", C3)]:
    a.scatter(e2.p_welch, e2[col], s=14, color=c, alpha=0.8)
    a.plot([1e-6, 1], [1e-6, 1], color="k", lw=0.8)
    a.axvline(0.05, color="k", ls="--", lw=0.8); a.axhline(0.05, color="k", ls="--", lw=0.8)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(1e-6, 1.2); a.set_ylim(5e-5, 1.2)
    a.set_xlabel("Welch の t 検定の p"); a.set_ylabel("並べ替えの p")
    n = int((e2[col] < 0.05).sum())
    a.set_title(f"{ttl}\n0.05未満：Welch 19指標 → 並べ替え {n}指標", fontsize=10)
fig.suptitle("東日本17都道県と西日本30府県の100指標（例2）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f177_3_east_west_units.png", dpi=150); plt.close()

# 図4：例3 並べ替えの単位で p が変わる
e3 = pd.read_csv(RES / "ex3_disaster_units.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.4))
w = 0.26; xb = np.arange(len(e3))
for i, (col, lab, c) in enumerate([("p_t_months", "月をばらばらの標本とみなす t 検定", C2),
                                   ("p_time_placebo", "時期をずらす（にせの開始月 19通り）", C4),
                                   ("p_pref_placebo", "県をずらす（対照の県を被災県とみなす）", C1)]):
    ax.bar(xb + (i - 1) * w, e3[col], w, color=c, label=lab)
    for x_, v in zip(xb + (i - 1) * w, e3[col]):
        ax.text(x_, v + 0.01, f"{v:.2f}", ha="center", fontsize=8)
ax.axhline(0.05, color="k", ls="--", lw=1)
ax.set_xticks(xb, [f"{r.name}\n（被災{r.n_treated}県・6か月 {r.effect_pct:+.1f}%）" for r in e3.itertuples()], fontsize=9)
ax.set_ylabel("両側 p"); ax.set_ylim(0, 1)
ax.set_title("災害のあと6か月の宿泊者数の差：何を並べ替えるかで p が変わる（例3）")
ax.legend(fontsize=8, frameon=False, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "f177_4_disaster_units.png", dpi=150); plt.close()

# 図5：人工データ
sim = pd.read_csv(RES / "simulation.csv")
lab = {"welch": "Welch の t", "student": "Student の t", "perm_mean": "並べ替え（平均の差）", "perm_t": "並べ替え（Welch の t）", "mannwhitney": "順位（Mann–Whitney）"}
col = {"welch": C1, "student": GR, "perm_mean": C2, "perm_t": C4, "mannwhitney": C3}
dl = {"normal": "正規分布", "lognormal": "右に裾の長い分布", "outlier": "片方に外れ値1点", "unequal": "ばらつき3倍・人数半分"}
fig, ax = plt.subplots(2, 4, figsize=(13, 6.2), sharex=True)
for j, d in enumerate(["normal", "lognormal", "outlier", "unequal"]):
    for i, eff in enumerate([0, 1]):
        a = ax[i, j]
        for m in lab:
            s = sim[(sim.dist == d) & (sim.effect == eff) & (sim.method == m)]
            a.plot(s.n, s.reject, marker="o", color=col[m], label=lab[m], lw=1.6)
        if eff == 0:
            a.axhline(0.05, color="k", ls="--", lw=0.8); a.set_ylim(0, 0.2)
        else:
            a.set_ylim(0, 1)
        a.set_xticks([5, 10, 15])
        if i == 0: a.set_title(dl[d], fontsize=10)
        if j == 0: a.set_ylabel("差なしなのに「差あり」の割合" if eff == 0 else "差を見つけた割合（検出力）", fontsize=9)
        if i == 1: a.set_xlabel("1グループの人数")
ax[0, 0].legend(fontsize=7.5, frameon=False, loc="upper right")
fig.suptitle("人工データ（各2,000回）：t 検定と並べ替え検定", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f177_5_simulation.png", dpi=150); plt.close()
print("figs ok")
