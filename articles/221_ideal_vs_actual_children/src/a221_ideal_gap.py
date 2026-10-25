"""221 理想の子ども数と実際の子ども数の差は、いつから広がったのか？（長期時系列の比較）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

a, dur, dist = load()
d15 = dur[dur.duration == "15-19"].set_index("year")
a = a.set_index("year")
a["ideal_15_19"] = d15.ideal; a["planned_15_19"] = d15.planned
a["gap_ideal_planned_all"] = (a.ideal_all - a.planned_all).round(2)
a["gap_ideal15_completed"] = (a.ideal_15_19 - a.completed_15_19).round(2)
a.to_csv(RES / "gaps_by_round.csv", encoding="utf-8-sig")
dur["gap"] = (dur.ideal - dur.planned).round(2)
G = dur.pivot(index="year", columns="duration", values="gap")[["0-4", "5-9", "10-14", "15-19"]]
G.to_csv(RES / "gap_ideal_planned_by_duration.csv", encoding="utf-8-sig")
dist = dist.set_index("year"); dist["c0_1"] = dist.c0 + dist.c1; dist["c3plus"] = dist.c3 + dist.c4plus
dist.to_csv(RES / "distribution_with_groups.csv", encoding="utf-8-sig")
pd.set_option("display.width", 200); print(a.to_string()); print(G.to_string()); print(dist.to_string())
X = a.index.values

# 図1 理想・予定・完結
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(X, a.ideal_all, "o-", color=ORANGE, lw=2, label="平均理想子ども数（妻50歳未満の夫婦）")
ax.plot(X, a.planned_all, "s--", color=BLUE, lw=2, label="平均予定子ども数（同）")
ax.plot(X, a.completed_15_19, "D-", color=INK, lw=2, label="完結出生子ども数（結婚15〜19年の夫婦）")
ax.plot([2021], [a.loc[2021, "completed_15_19_wife_under50"]], "D", mfc="white", color=INK, label="2021年を前回までと同じ妻50歳未満で集計")
for x, v in zip(X, a.ideal_all): ax.text(x, v + 0.04, f"{v:.2f}", ha="center", fontsize=8, color=ORANGE)
for x, v in zip(X, a.completed_15_19): ax.text(x, v - 0.09, f"{v:.2f}", ha="center", fontsize=8)
ax.set_ylim(1.6, 2.85); ax.set_xticks(X); ax.set_ylabel("人"); ax.legend(frameon=False, fontsize=8.5, loc="lower left")
ax.set_title("理想・予定・実際の子ども数（出生動向基本調査、1977〜2021年）", loc="left")
save(fig, "a221_levels.png")

# 図2 差（理想−予定、結婚持続期間別）と（理想−完結）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
ax = axes[0]
for c, col in zip(G.columns, [LIGHT, GREEN, BLUE, INK]):
    ax.plot(G.index, G[c], "o-", color=col, lw=1.8, ms=4, label=f"結婚{c}年")
ax.set_title("理想−予定（結婚持続期間別）", loc="left"); ax.legend(frameon=False, fontsize=9); ax.set_ylabel("人")
ax = axes[1]
ax.plot(X, a.gap_ideal15_completed, "D-", color=ORANGE, lw=2, label="結婚15〜19年の夫婦の理想−完結出生子ども数")
for x, v in zip(X, a.gap_ideal15_completed): ax.text(x, v + 0.015, f"{v:.2f}", ha="center", fontsize=8)
ax.set_title("理想−実際（子どもを生み終えた夫婦）", loc="left"); ax.legend(frameon=False, fontsize=8.5, loc="lower left")
for ax in axes: ax.set_xticks([1977, 1987, 1997, 2005, 2015, 2021]); ax.set_ylim(0, 0.65)
fig.suptitle("理想と予定・実際の差は広がっていない（差が小さくなったのは、理想が下がったため）", x=0.01, ha="left", fontsize=11, y=1.02)
fig.tight_layout(); save(fig, "a221_gap.png")

# 図3 出生子ども数の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
cols = ["#f2f2f0", LIGHT, BLUE, ORANGE, "#a8431b"]; labs = ["0人", "1人", "2人", "3人", "4人以上"]
bottom = np.zeros(len(dist)); xs = np.arange(len(dist))
for c, col, lab in zip(["c0", "c1", "c2", "c3", "c4plus"], cols, labs):
    ax.bar(xs, dist[c], bottom=bottom, color=col, edgecolor="white", label=lab, width=0.75)
    for x, b, v in zip(xs, bottom, dist[c]):
        if v >= 7: ax.text(x, b + v / 2, f"{v:.1f}", ha="center", va="center", fontsize=8, color="white" if c in ("c2", "c3") else INK)
    bottom += dist[c].values
ax.set_xticks(xs, dist.index); ax.set_ylim(0, 100); ax.set_ylabel("%")
ax.legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(1.0, 0.5), reverse=True)
ax.set_title("結婚15〜19年の夫婦の出生子ども数の分布（%）", loc="left")
save(fig, "a221_distribution.png")
