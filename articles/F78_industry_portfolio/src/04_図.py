"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

r = json.load(open(RES / "results.json"))
d = pd.read_csv(RES / "municipal_analysis.csv", dtype={"code": str, "pref": str})
q = pd.read_csv(RES / "by_diversity_quintile.csv")
pq = pd.read_csv(RES / "by_portfolio_quintile.csv")
rob = pd.read_csv(RES / "robustness.csv")
pref = pd.read_csv(RES / "pref47.csv", index_col=0)
C1, C2, C3 = "#2b6cb0", "#c05621", "#718096"

# 1 多様性と町の大きさ
fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.scatter(d["pop2015"], d["eff_n"], s=6, alpha=.35, color=C1)
ax.set_xscale("log")
ax.set_xlabel("2015年の人口（対数）")
ax.set_ylabel("実質的な産業の数（1/HHI、2016年）")
ax.set_title(f"産業がばらけている町ほど、人口も多い（相関 {r['summary']['corr_effn_logpop']:.2f}）", fontsize=11)
ax.axhline(r["summary"]["eff_n_median"], color=C3, lw=.8, ls="--")
ax.text(ax.get_xlim()[0] * 1.2, r["summary"]["eff_n_median"] + .15, f"中央値 {r['summary']['eff_n_median']:.1f}", color=C3, fontsize=9)
fig.text(.01, .01, "出典：経済センサス（e-Stat 社会・人口統計体系）、国勢調査。民営18産業。1,735市区町村", fontsize=8, color=C3)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / "f78_diversity_size.png"); plt.close()

# 2 多様性の5分位ごとの「その町だけのぶれ」と大きな落ち込み
fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.2))
x = np.arange(5); lab = [f"{v:.1f}" for v in q["eff_n"]]
axes[0].bar(x, q["abs_u"], color=C1)
for i, v in enumerate(q["abs_u"]):
    axes[0].text(i, v + .1, f"{v:.1f}", ha="center", fontsize=9)
axes[0].set_xticks(x, lab); axes[0].set_xlabel("実質的な産業の数（5分位の中央値）")
axes[0].set_ylabel("その町だけのぶれ（%、平均）")
axes[0].set_title("そのまま比べると、多様な町ほどぶれは小さい", fontsize=10)
axes[1].bar(x, 100 * q["drop10"], color=C2)
for i, v in enumerate(q["drop10"]):
    axes[1].text(i, 100 * v + .2, f"{100*v:.1f}", ha="center", fontsize=9)
axes[1].set_xticks(x, lab); axes[1].set_xlabel("実質的な産業の数（5分位の中央値）")
axes[1].set_ylabel("従業者が10%超減った町（%）")
b = r["abs_dev"]["eff"]
axes[1].set_title("大きく落ちた町の割合も小さい", fontsize=10)
fig.suptitle(f"ただし人口などをそろえると、多様性1SDあたり {b['b']:+.2f}%（95%区間 {b['lo']:+.2f}〜{b['hi']:+.2f}）で差は消える", fontsize=10)
fig.text(.01, .01, "出典：経済センサス（2016・2021年）。ぶれ＝実際の伸び−産業構成から予測した伸び（バーティク）", fontsize=8, color=C3)
fig.tight_layout(rect=(0, .03, 1, .94)); fig.savefig(FIG / "f78_quintiles.png"); plt.close()

# 3 ポートフォリオで予測したぶれと実際のぶれ
fig, ax = plt.subplots(figsize=(6.4, 4.8))
ax.plot(pq["port_sd"], pq["u_sd"], "o-", color=C2, ms=8)
for _, row in pq.iterrows():
    ax.annotate(f"第{int(row.port_q)+1}分位", (row.port_sd, row.u_sd), textcoords="offset points", xytext=(6, -12), fontsize=8)
lim = [5, 10.5]
ax.plot(lim, lim, color=C3, ls="--", lw=.8); ax.text(9.2, 9.6, "予測＝実際", color=C3, fontsize=8)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("産業ごとのぶれと産業間の相関から予測した、その町のぶれ（標準偏差、%）")
ax.set_ylabel("実際のぶれ（実際−バーティクの標準偏差、%）")
ax.set_title(f"「どの産業に偏っているか」で決まる予測は、実際のぶれとよく並ぶ（5分位の相関 {r['port_vs_actual_corr']:.2f}）", fontsize=9.5)
fig.text(.01, .01, "出典：経済センサス（2016・2021年）。産業別の町レベルの伸びのばらつき（2016年に30人以上の町）から計算", fontsize=7.5, color=C3)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / "f78_portfolio.png"); plt.close()

# 4 頑健性
fig, ax = plt.subplots(figsize=(7.6, 4.8))
rob2 = rob[rob.setting != "結果を二乗（分散）に"].reset_index(drop=True)
y = np.arange(len(rob2))[::-1]
ax.errorbar(rob2["b"], y, xerr=[rob2["b"] - rob2["lo"], rob2["hi"] - rob2["b"]], fmt="o", color=C1, capsize=3)
ax.axvline(0, color=C3, lw=.8)
ax.set_yticks(y, rob2["setting"], fontsize=8.5)
ax.set_xlabel("多様性1標準偏差あたりの、ぶれ |実際−バーティク| の差（%ポイント、95%区間）")
ax.set_title("多様性の指標・対象・期間を変えても、ぶれを小さくする効果ははっきりしない", fontsize=10)
fig.text(.01, .01, "人口（対数）・65歳以上と15〜64歳の割合・都道府県の固定効果をそろえた回帰。標準誤差は都道府県でクラスター", fontsize=7.5, color=C3)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / "f78_robustness.png"); plt.close()

# 5 都道府県：リーマン・ショックとコロナ
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8))
for ax, col, title in [(axes[0], "lehman", "リーマン・ショック 2008→10年"), (axes[1], "covid", "コロナ 2019→21年")]:
    sc = ax.scatter(pref["eff_n"], pref[col], c=100 * pref["shr_mfg"], cmap="Oranges", s=35, edgecolor="k", lw=.3)
    ax.axhline(0, color=C3, lw=.7)
    ax.set_xlabel("実質的な産業の数（2016年）")
    ax.set_ylabel("就業者の変化（%）")
    pr = r["prefecture"][col]
    ax.set_title(f"{title}\n相関 {pr['corr']:+.2f}／産業の割合をそろえると差は消える", fontsize=9.5)
cb = fig.colorbar(sc, ax=axes, shrink=.8); cb.set_label("製造業の割合（%）")
fig.text(.01, -.02, "出典：労働力調査 都道府県別結果（モデル推計値）、経済センサス。47都道府県。色は製造業の割合", fontsize=8, color=C3)
fig.savefig(FIG / "f78_prefecture.png", bbox_inches="tight"); plt.close()

# 6 産業間の相関（GitHub のみ）
corr = pd.read_csv(RES / "industry_corr.csv", index_col=0)
fig, ax = plt.subplots(figsize=(7.5, 6.5))
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-.5, vmax=.5)
ax.set_xticks(range(len(corr)), corr.columns, rotation=90, fontsize=7.5)
ax.set_yticks(range(len(corr)), corr.index, fontsize=7.5)
fig.colorbar(im, shrink=.7, label="町レベルの伸びの相関")
ax.set_title(f"同じ町の中の産業どうしの伸びの相関（平均 {r['industry_corr_mean']:.2f}）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f78_industry_corr.png"); plt.close()
print("ok")
