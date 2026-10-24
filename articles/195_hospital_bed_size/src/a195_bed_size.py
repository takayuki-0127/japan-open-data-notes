"""A195 病院の数は、どの病床規模から減っているか（医療施設調査 1987〜2025年）"""
from common import *
d = load("hospitals_by_bed_size.csv")
B = ["20-29", "30-39", "40-49", "50-99", "100-149", "150-199", "200-299", "300-399", "400-499", "500-599", "600-699", "700-799", "800-899", "900+"]
G = {"20-29": "20〜99床", "30-39": "20〜99床", "40-49": "20〜99床", "50-99": "20〜99床", "100-149": "100〜199床", "150-199": "100〜199床",
     "200-299": "200〜399床", "300-399": "200〜399床", "400-499": "400〜599床", "500-599": "400〜599床", "600-699": "600床以上", "700-799": "600床以上", "800-899": "600床以上", "900+": "600床以上"}
GL = ["20〜99床", "100〜199床", "200〜399床", "400〜599床", "600床以上"]
t = d[d.type == "総数"].pivot(index="year", columns="band", values="hospitals")[B]
tot = t.sum(axis=1)
g = d[d.type == "総数"].assign(grp=lambda x: x.band.map(G)).pivot_table(index="year", columns="grp", values="hospitals", aggfunc="sum")[GL]
g.to_csv(RES / "a195_groups.csv")
def chg(a, b):
    c = pd.DataFrame({"band": B, f"n{a}": t.loc[a].values, f"n{b}": t.loc[b].values}); c["diff"] = c[f"n{b}"] - c[f"n{a}"]; c["pct"] = (c[f"n{b}"] / c[f"n{a}"] - 1) * 100
    c["share_of_total_change"] = c["diff"] / c["diff"].sum() * 100; return c
c1 = chg(1990, 2025); c2 = chg(2002, 2025); c3 = chg(2014, 2025)
c1.to_csv(RES / "a195_change_1990_2025.csv", index=False); c2.to_csv(RES / "a195_change_2002_2025.csv", index=False); c3.to_csv(RES / "a195_change_2014_2025.csv", index=False)
gp = lambda a, b: (g.loc[b] - g.loc[a]).astype(int)
pg = d[d.type != "総数"].assign(grp=lambda x: x.band.map(G)).pivot_table(index=["type", "year"], columns="grp", values="hospitals", aggfunc="sum")[GL]
pg.to_csv(RES / "a195_groups_by_type.csv")
with open(RES / "a195_summary.txt", "w") as f:
    f.write("病院総数:\n" + tot.to_string() + "\n\n")
    for a, b, c in [(1990, 2025, c1), (2002, 2025, c2), (2014, 2025, c3)]:
        f.write(f"{a}→{b} 病床規模別の増減（総数{int(tot[b]-tot[a])}、{(tot[b]/tot[a]-1)*100:.1f}%）:\n" + c.round(1).to_string(index=False) + "\n\n")
    f.write("グループ別:\n" + g.to_string() + "\n\n1990→2025: " + gp(1990, 2025).to_string() + "\n2002→2025: " + gp(2002, 2025).to_string() + "\n2014→2025: " + gp(2014, 2025).to_string() + "\n\n")
    f.write("精神科・一般:\n" + pg.to_string() + "\n")
    f.write("\n20〜99床の割合: " + (g["20〜99床"] / tot * 100).round(1).to_string() + "\n")
# fig1: groups over time
fig, ax = plt.subplots(figsize=(8, 4.8)); cols = [ORANGE, "#e0a33a", GREEN, LIGHT, BLUE]
for gname, col in zip(GL, cols):
    ax.plot(g.index, g[gname], marker="o", ms=4, color=col, lw=2, label=gname)
    ax.annotate(f"{g[gname].iloc[-1]:,}", (2025, g[gname].iloc[-1]), xytext=(5, 7 if gname == "20〜99床" else (-7 if gname == "100〜199床" else 0)), textcoords="offset points", va="center", fontsize=9, color=col)
ax.set_ylabel("病院数"); ax.set_title(f"病床の規模別の病院数（総数 {tot[1990]:,}（1990年）→{tot[2025]:,}（2025年））"); ax.legend(frameon=False, fontsize=9, ncol=3); ax.set_ylim(0, 5600)
save(fig, "a195_groups.png")
# fig2: change by band 1990-2025 and 2002-2025
fig, ax = plt.subplots(figsize=(8, 4.8)); x = np.arange(len(B)); w = 0.4
ax.bar(x - w / 2, c1["diff"], w, color=GRAY, label="1990→2025年"); ax.bar(x + w / 2, c2["diff"], w, color=ORANGE, label="2002→2025年")
for i, v in enumerate(c1["diff"]): ax.text(i - w / 2, v + (8 if v >= 0 else -8), f"{v:+d}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7.5)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([b.replace("-", "〜").replace("900+", "900〜") for b in B], rotation=45, fontsize=8.5)
ax.set_ylabel("病院数の増減"); ax.set_title("病床の規模（床）別にみた病院数の増減"); ax.legend(frameon=False)
save(fig, "a195_change.png")
# fig3: index 2002=100 for general vs psychiatric by group
gen = pg.loc["一般病院"]; psy = pg.loc["精神科病院"]
fig, axs = plt.subplots(1, 2, figsize=(9, 4.4), sharey=True)
for ax, dd, ttl in [(axs[0], gen, "一般病院"), (axs[1], psy, "精神科病院")]:
    for gname, col in zip(GL, cols):
        if dd[gname].iloc[0] < 15: continue
        ax.plot(dd.index, dd[gname] / dd[gname].iloc[0] * 100, marker="o", ms=3, color=col, lw=2, label=f"{gname}（{dd[gname].iloc[0]:,}→{dd[gname].iloc[-1]:,}）")
    ax.axhline(100, color=GRAY, lw=0.8, ls="--"); ax.set_title(ttl); ax.legend(frameon=False, fontsize=7.5, loc="lower left")
axs[0].set_ylabel("2002年＝100"); fig.suptitle("一般病院と精神科病院の規模別の推移（2002年＝100）", fontsize=13, y=1.04); axs[0].set_ylim(40, 125)
save(fig, "a195_type.png")
