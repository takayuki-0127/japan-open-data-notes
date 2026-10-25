"""A216 要支援・要介護の内訳18年（2007〜2024年度末）：構成比の推移、2007年度=100の指数、第1号の認定率"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import load, LEVELS, NAMES, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

d, pop = load()
tot = d[d.grp == "tot"].set_index("year")
share = tot[LEVELS].div(tot.total, axis=0) * 100
idx = tot[LEVELS + ["total"]] / tot.loc[2007, LEVELS + ["total"]] * 100
d1 = d[d.grp == "d1"].set_index("year")
rate = (d1.total / pop * 100).rename("rate_d1")
a85 = d[d.grp == "a85p"].set_index("year")
sh85 = (a85.total / d1.total * 100).dropna()
light = share[["s1", "s2", "k1"]].sum(axis=1); heavy = share[["k3", "k4", "k5"]].sum(axis=1)
out = pd.concat([tot[LEVELS + ["total"]], share.add_suffix("_pct").round(2), rate.round(2), d1.total.rename("d1_total"), pop.rename("insured65")], axis=1)
out.to_csv(RES / "care_levels_share.csv")
idx.round(1).to_csv(RES / "care_levels_index.csv")

L = []
L.append(f"認定者総数 2007年度末 {tot.loc[2007,'total']:,} → 2024年度末 {tot.loc[2024,'total']:,}（{(tot.loc[2024,'total']/tot.loc[2007,'total']-1)*100:+.1f}%）")
for k in LEVELS + ["total"]:
    L.append(f"{NAMES.get(k,'合計')}: {tot.loc[2007,k]:,} → {tot.loc[2024,k]:,} 指数{idx.loc[2024,k]:.1f}  構成比 {share.loc[2007,k] if k!='total' else 100:.1f}% → {share.loc[2024,k] if k!='total' else 100:.1f}%")
L.append(f"軽度（要支援1・2＋要介護1）の割合 {light[2007]:.1f}% → {light[2024]:.1f}%、重度（要介護3〜5）{heavy[2007]:.1f}% → {heavy[2024]:.1f}%")
L.append(f"第1号の認定率（第1号認定者÷第1号被保険者） {rate[2007]:.2f}% → {rate[2024]:.2f}%  最低 {rate.idxmin()} {rate.min():.2f}%")
L.append(f"第1号認定者に占める85歳以上 {sh85.index[0]} {sh85.iloc[0]:.1f}% → 2024 {sh85.iloc[-1]:.1f}%")
L.append(f"第1号被保険者 2007 {pop[2007]:,} → 2024 {pop[2024]:,}（{(pop[2024]/pop[2007]-1)*100:+.1f}%）")
d2 = d[d.grp == "d2"].set_index("year").total
L.append(f"第2号認定者 2007 {d2[2007]:,} → 2024 {d2[2024]:,}")
a6 = d[d.grp == "a65_74"].set_index("year").total; a7 = d[d.grp == "a75p"].set_index("year").total
L.append(f"65〜74歳の認定者 2007 {a6[2007]:,} → 2024 {a6[2024]:,}、75歳以上 {a7[2007]:,} → {a7[2024]:,}")
L.append("年平均増加率（2007→2024）: " + ", ".join(f"{NAMES[k]} {((tot.loc[2024,k]/tot.loc[2007,k])**(1/17)-1)*100:.2f}%" for k in LEVELS))
open(RES / "summary.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))

cols = ["#a9c9ef", "#6fa6e3", "#f4c19a", "#eb9a6a", "#eb6834", "#c4471d", "#7a2a0f"]
fig, ax = plt.subplots(figsize=(9, 5))
ax.stackplot(share.index, *[share[k] for k in LEVELS], colors=cols, labels=[NAMES[k] for k in LEVELS])
for k, c in zip(LEVELS, cols):
    pass
cum = share.cumsum(axis=1)
for k in LEVELS:
    y = cum[k].iloc[-1] - share[k].iloc[-1] / 2
    ax.text(2024.3, y, f"{NAMES[k]} {share[k].iloc[-1]:.1f}%", va="center", fontsize=9)
    y0 = cum[k].iloc[0] - share[k].iloc[0] / 2
    ax.text(2007.2, y0, f"{share[k].iloc[0]:.1f}%", va="center", ha="left", fontsize=9, color="white" if k in ("k3","k4","k5") else INK)
ax.set_xlim(2007, 2024); ax.set_ylim(0, 100); ax.set_ylabel("認定者に占める割合（%）")
ax.set_title("要支援・要介護の内訳（年度末、全国）")
fig.text(0.01, -0.02, SOURCE + "。経過的要介護は要介護1に含めた", fontsize=8, color=GRAY)
fig.savefig(FIG / "a216_share.png"); plt.close()

fig, ax = plt.subplots(figsize=(9, 5))
for k, c in zip(LEVELS, cols):
    ax.plot(idx.index, idx[k], color=c, lw=2.2 if k in ("k1", "k5") else 1.6)
    off = {"s1": -3.5, "k1": 3.5, "k4": 1.5, "k2": -1.5}.get(k, 0)
    ax.text(2024.3, idx[k].iloc[-1] + off, f"{NAMES[k]} {idx[k].iloc[-1]:.0f}", va="center", fontsize=9, color=c if k not in ("s1",) else BLUE)
ax.plot(idx.index, idx.total, color=INK, lw=1.2, ls="--"); ax.text(2007.2, idx.total.iloc[0] + 4, "")
ax.axhline(100, color=GRAY, lw=0.8); ax.set_xticks(range(2008, 2025, 2))
ax.set_xlim(2007, 2027); ax.set_ylabel("2007年度末＝100")
ax.set_title(f"要介護度ごとの認定者数の伸び（点線は合計 {idx.total.iloc[-1]:.0f}）")
fig.text(0.01, -0.02, SOURCE, fontsize=8, color=GRAY)
fig.savefig(FIG / "a216_index.png"); plt.close()

fig, ax1 = plt.subplots(figsize=(9, 5))
ax1.plot(rate.index, rate, color=BLUE, lw=2.2, marker="o", ms=3, label="第1号の認定率（左）")
ax1.set_ylabel("第1号被保険者に占める認定者（%）", color=BLUE)
ax2 = ax1.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(sh85.index, sh85, color=ORANGE, lw=2.2, marker="s", ms=3, label="第1号認定者のうち85歳以上（右）")
ax2.set_ylabel("85歳以上の割合（%）", color=ORANGE)
ax1.annotate(f"{rate[2007]:.1f}%", (2007, rate[2007]), textcoords="offset points", xytext=(0, 8), color=BLUE, fontsize=9)
ax1.annotate(f"{rate[2024]:.1f}%", (2024, rate[2024]), textcoords="offset points", xytext=(-10, 8), color=BLUE, fontsize=9)
ax2.annotate(f"{sh85.iloc[0]:.1f}%", (sh85.index[0], sh85.iloc[0]), textcoords="offset points", xytext=(0, -14), color=ORANGE, fontsize=9)
ax2.annotate(f"{sh85.iloc[-1]:.1f}%", (2024, sh85.iloc[-1]), textcoords="offset points", xytext=(-10, -14), color=ORANGE, fontsize=9)
ax1.set_xticks(range(2008, 2025, 2))
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
ax1.set_title("65歳以上の認定率と、認定者の高齢化")
fig.text(0.01, -0.02, SOURCE + "。85歳以上の区分は2014年度から", fontsize=8, color=GRAY)
fig.savefig(FIG / "a216_rate.png"); plt.close()
