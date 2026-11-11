"""04 図：6枚"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import RES, FIG, SEXES, COL, GLABEL

FIG.mkdir(exist_ok=True)
SRC = "出典：日本版死亡データベース（JMD、元は人口動態統計）から作成"
t = pd.read_csv(RES / "A_rates_by_age.csv")
roll = pd.read_csv(RES / "C_rolling10.csv")
ex = pd.read_csv(RES / "B_excess_vs_trend.csv")
arr = pd.read_csv(RES / "D_arriaga.csv")
coh = pd.read_csv(RES / "F_reask_cohort_dev.csv")

# 図1 改善率の地図（10年窓）
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
norm = TwoSlopeNorm(vmin=-2, vcenter=0, vmax=5)
for ax, s in zip(axes, SEXES):
    p = roll[(roll.sex == s) & (roll.g >= 9)].pivot_table(index="g", columns="end", values="rate")
    im = ax.imshow(p.values, aspect="auto", origin="lower", cmap="RdBu", norm=norm,
                   extent=[p.columns.min() - .5, p.columns.max() + .5, -.5, len(p) - .5])
    ax.set_yticks(range(len(p))); ax.set_yticklabels([GLABEL[i] for i in p.index], fontsize=8)
    ax.set_title(f"{s}"); ax.set_xlabel("10年の窓の終わりの年")
    ax.axvline(2019.5, color="k", lw=0.8, ls="--")
cb = fig.colorbar(im, ax=axes, shrink=0.85); cb.set_label("死亡率の改善（年あたり%、青＝改善が大きい）")
fig.suptitle("死亡率の改善率の地図（40歳以上、10年の平均。赤は死亡率が上がった）")
fig.text(0.01, 0.01, SRC, fontsize=7)
fig.savefig(FIG / "fig1_improvement_map.png", dpi=150, bbox_inches="tight"); plt.close()

# 図2 A・B・C の比較（40歳以上）
u = t[t.age0 >= 40]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, s in zip(axes, SEXES):
    v = u[u.sex == s]; x = np.arange(len(v))
    ax.bar(x - 0.27, v.A_2000_09, 0.27, label="2000年代（1999→2009）", color="#9ecae1")
    ax.bar(x, v.B_2010_19, 0.27, label="2010年代（2009→2019）", color="#3182bd")
    ax.bar(x + 0.27, v.C_2020_24, 0.27, label="2019→2024", color="#fdae6b")
    ax.axhline(0, color="k", lw=0.6); ax.set_xticks(x); ax.set_xticklabels(v.label, rotation=60, fontsize=8)
    ax.set_title(s)
axes[0].set_ylabel("年あたりの改善率（%）"); axes[0].legend(fontsize=8)
fig.suptitle("年齢別の死亡率の改善（年あたり%）：10年ごとの比較")
fig.text(0.01, -0.03, SRC + "。区間の始まりと終わりの年の死亡率から計算", fontsize=7)
fig.savefig(FIG / "fig2_rates_by_decade.png", dpi=150, bbox_inches="tight"); plt.close()

# 図3 鈍りの大きさを3つの測り方で
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, s in zip(axes, SEXES):
    v = u[u.sex == s]; x = np.arange(len(v))
    ax.plot(x, v.slow_AB, "o-", label="10年（区間の端の年）", color="#08519c")
    ax.plot(x, v.slow_A5B5, "s--", label="5年（2004→09 と 2014→19）", color="#6baed6")
    ax.plot(x, v.slow_ols, "^:", label="10年の直線の傾き（2011年を除く）", color="#e6550d")
    ax.axhline(0, color="k", lw=0.6); ax.set_xticks(x); ax.set_xticklabels(v.label, rotation=60, fontsize=8)
    for i in np.where((v.slow_AB > 0) & (v.slow_A5B5 > 0) & (v.slow_ols > 0))[0]:
        ax.axvspan(i - 0.4, i + 0.4, color="#ffd92f", alpha=0.35, lw=0)
    ax.set_title(s)
axes[0].set_ylabel("改善率の低下（2000年代−2010年代、%ポイント）"); axes[0].legend(fontsize=8)
fig.suptitle("改善が鈍った年齢（上がプラス＝鈍った）。黄色は3つの測り方すべてで鈍った区分")
fig.text(0.01, -0.03, SRC, fontsize=7)
fig.savefig(FIG / "fig3_slowdown_three_ways.png", dpi=150, bbox_inches="tight"); plt.close()

# 図4 コロナ期の上振れ（40歳以上、2010〜2019年の直線との比）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, s in zip(axes, SEXES):
    v = ex[(ex.sex == s) & (ex.age0 >= 40)]
    for y, c in zip(range(2020, 2025), ["#c6dbef", "#9ecae1", "#fd8d3c", "#e6550d", "#a63603"]):
        w = v[v.year == y]; ax.plot(range(len(w)), w.ratio, "o-", color=c, label=str(y), ms=3)
    ax.axhline(0, color="k", lw=0.6); ax.set_xticks(range(len(w))); ax.set_xticklabels(w.label, rotation=60, fontsize=8)
    ax.set_title(s)
axes[0].set_ylabel("2010〜2019年の傾向を延ばした値との差（%）"); axes[0].legend(fontsize=8)
fig.suptitle("2020〜2024年の死亡率は、それまでの傾向からどれだけ上に出たか（40歳以上）")
fig.text(0.01, -0.03, SRC + "。区分ごとに2010〜2019年の対数の直線を当てはめて延ばした", fontsize=7)
fig.savefig(FIG / "fig4_excess_vs_trend.png", dpi=150, bbox_inches="tight"); plt.close()

# 図5 平均寿命の変化を年齢に分ける
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
per = ["2000→2010", "2010→2019", "2019→2024"]; cols = ["#9ecae1", "#3182bd", "#fd8d3c"]
for ax, s in zip(axes, SEXES):
    for k, (p, c) in enumerate(zip(per, cols)):
        v = arr[(arr.sex == s) & (arr.period == p)]
        ax.bar(np.arange(len(v)) + (k - 1) * 0.27, v.contrib, 0.27, color=c,
               label=f"{p}（計 {v.contrib.sum():+.2f}年）")
    ax.axhline(0, color="k", lw=0.6); ax.set_xticks(range(len(GLABEL))); ax.set_xticklabels(GLABEL, rotation=70, fontsize=7)
    ax.set_title(s); ax.legend(fontsize=8)
axes[0].set_ylabel("平均寿命の変化への寄与（年）")
fig.suptitle("平均寿命の変化を、どの年齢の死亡率の変化から来たかに分ける（Arriaga 法）")
fig.text(0.01, -0.04, SRC, fontsize=7)
fig.savefig(FIG / "fig5_arriaga.png", dpi=150, bbox_inches="tight"); plt.close()

# 図6 問い直し：生まれ年ごとの偏り（60〜79歳、1995〜2019年）
fig, ax = plt.subplots(figsize=(9, 4.4))
for s in SEXES:
    v = coh[(coh.sex == s) & coh.cohort.between(1920, 1960)]
    ax.plot(v.cohort, v["mean"], "o-", color=COL[s], label=s, ms=3)
ax.axhline(0, color="k", lw=0.6); ax.axvspan(1944.5, 1949.5, color="#ffd92f", alpha=0.35, lw=0)
ax.set_xlabel("生まれ年"); ax.set_ylabel("同じ年齢の平均との差（%ポイント）")
ax.set_title("60〜79歳の5年の改善率を生まれ年ごとに見る（1995〜2019年）：1945〜49年生まれで低い")
ax.legend(); fig.text(0.01, -0.03, SRC + "。各歳の5年の改善率から年齢ごとの平均を引いて、生まれ年で平均", fontsize=7)
fig.savefig(FIG / "fig6_reask_cohort.png", dpi=150, bbox_inches="tight"); plt.close()
print("ok")
