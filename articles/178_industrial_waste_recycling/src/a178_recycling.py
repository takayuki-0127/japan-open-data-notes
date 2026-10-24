"""178 産業廃棄物の再生利用率は、種類でどう違い、どう伸びたか"""
from common import *

n = load("national_flow_1996_2023.csv")
n["emission"] = n.recycle_mt + n.reduction_mt + n.final_mt
n["recycle_rate"] = n.recycle_mt / n.emission * 100
n["final_rate"] = n.final_mt / n.emission * 100
n.round(2).to_csv(RES / "a178_national.csv", index=False, encoding="utf-8-sig")

t = load("by_type_2010_2023.csv")
t["recycle_rate"] = t.recycle_kt / t.emission_kt * 100
t["final_rate"] = t.final_kt / t.emission_kt * 100
w = t.pivot(index="type", columns="fiscal_year", values="recycle_rate")
w.round(1).to_csv(RES / "a178_rate_by_type.csv", encoding="utf-8-sig")
e = t.pivot(index="type", columns="fiscal_year", values="emission_kt")
r = t.pivot(index="type", columns="fiscal_year", values="recycle_kt")

out = []
def ln(s): out.append(s)
for y in [1996, 2000, 2005, 2010, 2015, 2019, 2023]:
    x = n[n.fiscal_year == y].iloc[0]; ln(f"{y}: 排出{x.emission} 再生{x.recycle_mt} 率{x.recycle_rate:.1f}% 最終{x.final_mt} 率{x.final_rate:.1f}%")
ln(f"max recycle rate year {n.loc[n.recycle_rate.idxmax(),'fiscal_year']} {n.recycle_rate.max():.1f}")
x = n.set_index("fiscal_year").recycle_rate
ln(f"2008-2023 range {x.loc[2008:].min():.1f}-{x.loc[2008:].max():.1f}")
d = (w[2023] - w[2010]).sort_values()
ln("rate 2010->2023: " + "; ".join(f"{k} {w.loc[k,2010]:.1f}->{w.loc[k,2023]:.1f}({v:+.1f})" for k, v in d.items()))
# 汚泥を除いた再生利用率
for y in [2010, 2023]:
    ex = e[y].drop(["合計", "汚泥"]).sum(); rx = r[y].drop(["合計", "汚泥"]).sum()
    ln(f"{y} 汚泥除く再生利用率 {rx/ex*100:.1f}%  汚泥の排出割合 {e.loc['汚泥',y]/e.loc['合計',y]*100:.1f}%  汚泥の減量化 share")
# 2023 composition of recycled amount
c = (r[2023].drop("合計") / r.loc["合計", 2023] * 100).sort_values(ascending=False)
ln("2023 再生利用量の内訳: " + ", ".join(f"{k}{v:.1f}%" for k, v in c.head(6).items()))
ln("2023 rates: " + ", ".join(f"{k}{v:.1f}" for k, v in w[2023].sort_values(ascending=False).items()))
# 汚泥 rate series
ln("汚泥 rate: " + ", ".join(f"{y}:{w.loc['汚泥',y]:.1f}" for y in w.columns))
ln("廃プラ rate: " + ", ".join(f"{y}:{w.loc['廃プラスチック類',y]:.1f}" for y in w.columns))
ln("ばいじん rate: " + ", ".join(f"{y}:{w.loc['ばいじん',y]:.1f}" for y in w.columns))
ln("ガラス rate: " + ", ".join(f"{y}:{w.loc['ガラスくず・コンクリートくず及び陶磁器くず',y]:.1f}" for y in w.columns))
ln("合計 rate: " + ", ".join(f"{y}:{w.loc['合計',y]:.1f}" for y in w.columns))
fr = t.pivot(index="type", columns="fiscal_year", values="final_kt")
ln(f"最終処分 2010->2023: {fr.loc['合計',2010]:.0f}->{fr.loc['合計',2023]:.0f} kt; 汚泥 {fr.loc['汚泥',2010]:.0f}->{fr.loc['汚泥',2023]:.0f}; ばいじん {fr.loc['ばいじん',2010]:.0f}->{fr.loc['ばいじん',2023]:.0f}; がれき {fr.loc['がれき類',2010]:.0f}->{fr.loc['がれき類',2023]:.0f}")
(RES / "a178_summary.txt").write_text("\n".join(out), encoding="utf-8"); print("\n".join(out))

# 図1 全体の推移
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(n.fiscal_year, n.recycle_rate, color=BLUE, lw=2, label="再生利用率")
ax.plot(n.fiscal_year, n.final_rate, color=ORANGE, lw=2, label="最終処分率")
for y in [1996, 2005, 2023]:
    v = n.set_index("fiscal_year").loc[y]
    ax.annotate(f"{v.recycle_rate:.1f}%", (y, v.recycle_rate), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9, color=BLUE)
    ax.annotate(f"{v.final_rate:.1f}%", (y, v.final_rate), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=9, color=ORANGE)
ax.set_ylim(0, 65); ax.set_ylabel("排出量に対する割合（%）"); ax.legend(frameon=False, loc="center right")
ax.set_title("産業廃棄物の再生利用率と最終処分率（1996〜2023年度）", loc="left")
save(fig, "a178_national.png")

# 図2 種類別 2010→2023（ダンベル）
order = w[2023].drop("合計").sort_values().index
fig, ax = plt.subplots(figsize=(8, 7))
yy = np.arange(len(order))
ax.hlines(yy, w.loc[order, 2010], w.loc[order, 2023], color=GRAY, lw=1.5)
ax.scatter(w.loc[order, 2010], yy, color=LIGHT, s=40, zorder=3, label="2010年度")
ax.scatter(w.loc[order, 2023], yy, color=BLUE, s=40, zorder=3, label="2023年度")
for i, k in enumerate(order):
    ax.text(max(w.loc[k, 2010], w.loc[k, 2023]) + 1.5, i, f"{w.loc[k,2023]:.0f}%", va="center", fontsize=8.5)
lab = [k.replace("ガラスくず・コンクリートくず及び陶磁器くず", "ガラス・コンクリート・陶磁器くず") for k in order]
ax.set_yticks(yy, lab, fontsize=9); ax.set_xlim(0, 105); ax.set_xlabel("再生利用率（%）")
ax.axvline(w.loc["合計", 2023], color=GRAY, ls="--", lw=0.8); ax.text(w.loc["合計", 2023] + 1, -0.9, f"全体 {w.loc['合計',2023]:.1f}%", fontsize=8.5, color=GRAY)
ax.legend(frameon=False, loc="lower right"); ax.set_title("種類別の再生利用率：2010年度と2023年度", loc="left")
save(fig, "a178_by_type.png")

# 図3 主な種類の推移
fig, ax = plt.subplots(figsize=(8, 4.5))
sel = [("汚泥", ORANGE), ("廃プラスチック類", PURPLE), ("ガラスくず・コンクリートくず及び陶磁器くず", GREEN), ("ばいじん", INK), ("合計", BLUE)]
for k, c in sel:
    lw = 2.5 if k == "合計" else 1.6
    ax.plot(w.columns, w.loc[k], marker="o", ms=4, color=c, lw=lw)
    nm = "ガラス・コンクリート・陶磁器くず" if k.startswith("ガラス") else ("全体" if k == "合計" else k)
    ax.text(2023.3, w.loc[k, 2023], nm, va="center", fontsize=8.5, color=c)
ax.set_xlim(2009.5, 2027.5); ax.set_xticks(range(2010, 2024, 2)); ax.set_ylim(0, 100); ax.set_ylabel("再生利用率（%）")
ax.set_title("主な種類の再生利用率の推移（2010〜2023年度、データのある年）", loc="left")
ax.text(2010, 3, "2014・2016〜2018年度は表がないため線でつないでいる", fontsize=8, color=GRAY)
save(fig, "a178_trend.png")
