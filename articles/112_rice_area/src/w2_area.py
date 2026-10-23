"""W2：水稲の作付面積は、どこで減ったのか（都道府県、1958〜2025年）"""
from common import *
SRC2 = "出典：農林水産省「作物統計調査」（e-Stat）をもとに作成者が加工して作成"

p = panel()
pf = p[(p.level == "pref") & (p.year >= 1958)].copy()
nat = p[(p.level == "region") & (p.name == "全国")].set_index("year")
pf["block"] = pf.name.map(BLOCK)
# 3つのまとまり：北海道・東北・北陸（北日本の主産地）、関東・東山、西日本（東海〜沖縄）
GROUP = {"北海道": "北海道・東北・北陸", "東北": "北海道・東北・北陸", "北陸": "北海道・東北・北陸", "関東・東山": "関東・東山"}
pf["group"] = pf.block.map(lambda b: GROUP.get(b, "東海以西（西日本）"))
G3 = ["北海道・東北・北陸", "関東・東山", "東海以西（西日本）"]

# ---- 全国の推移
n = nat.loc[1958:, ["area_ha", "harvest_t"]]
print("全国の最大：", nat.area_ha.idxmax(), nat.area_ha.max(), " 2025：", nat.loc[2025, "area_ha"],
      f"（{(nat.loc[2025, 'area_ha'] / nat.area_ha.max() - 1) * 100:.1f}%）")
print("最小：", nat.loc[1958:].area_ha.idxmin(), nat.loc[1958:].area_ha.min())

# ---- 都道府県：ピークの年と、ピーク→2025年の減少率、1969→2025年の減少率
def one(g):
    g = g.set_index("year")
    pk = g.area_ha.idxmax()
    return pd.Series({"block": g.block.iloc[0], "group": g.group.iloc[0], "peak_year": pk, "peak_ha": g.area_ha.max(),
                      "ha_1969": g.area_ha.get(1969), "ha_2025": g.area_ha.get(2025),
                      "harvest_1969": g.harvest_t.get(1969), "harvest_2025": g.harvest_t.get(2025)})
pr = pf.groupby("name").apply(one).reindex(PREFS)
pr["decline_from_peak_pct"] = (1 - pr.ha_2025 / pr.peak_ha) * 100
pr["decline_from_1969_pct"] = (1 - pr.ha_2025 / pr.ha_1969) * 100
pr["share_1969_pct"] = pr.ha_1969 / pr.ha_1969.sum() * 100
pr["share_2025_pct"] = pr.ha_2025 / pr.ha_2025.sum() * 100
pr.round(2).to_csv(RES / "w2_pref_decline.csv", encoding="utf-8")
s = pr.sort_values("decline_from_peak_pct")
print(s[["block", "peak_year", "peak_ha", "ha_2025", "decline_from_peak_pct", "share_1969_pct", "share_2025_pct"]].round(1).to_string())
print("ピークの年：", pr.peak_year.value_counts().sort_index().to_dict())
print("減少率の中央値：", round(pr.decline_from_peak_pct.median(), 1))

# ---- まとまり別
gg = pf.groupby(["group", "year"])[["area_ha", "harvest_t"]].sum().reset_index()
tot = gg.groupby("year")[["area_ha", "harvest_t"]].transform("sum")
gg["area_share"] = gg.area_ha / tot.area_ha * 100; gg["harvest_share"] = gg.harvest_t / tot.harvest_t * 100
gg.round(3).to_csv(RES / "w2_group_share.csv", index=False, encoding="utf-8")
gt = gg[gg.year.isin([1958, 1969, 1990, 2010, 2025])].pivot(index="group", columns="year", values=["area_ha", "area_share", "harvest_share"]).loc[G3]
print(gt.round(1).to_string())
for g in G3:
    a = gg[(gg.group == g)].set_index("year")
    print(g, "1969→2025の減少率", round((1 - a.loc[2025, "area_ha"] / a.loc[1969, "area_ha"]) * 100, 1))
bb = pf.groupby(["block", "year"]).area_ha.sum().unstack()
bd = ((1 - bb[2025] / bb[1969]) * 100).drop("沖縄").round(1).sort_values()  # 沖縄は1973年から
bd.to_csv(RES / "w2_block_decline.csv", encoding="utf-8"); print(bd.to_string())

# ---- 集中度：都道府県の面積シェアのHHIと、上位5・10県のシェア
def conc(g):
    sh = g.area_ha / g.area_ha.sum()
    srt = sh.sort_values(ascending=False)
    return pd.Series({"hhi": (sh ** 2).sum() * 10000, "top5_pct": srt.head(5).sum() * 100, "top10_pct": srt.head(10).sum() * 100,
                      "n_equiv": 1 / (sh ** 2).sum(), "top1": g.loc[srt.index[0], "name"]})
cc = pf.dropna(subset=["area_ha"]).groupby("year").apply(conc)
cc.to_csv(RES / "w2_concentration.csv", encoding="utf-8")
print(cc.loc[[1958, 1969, 1980, 1990, 2000, 2010, 2020, 2025]].to_string())
print("2025年の上位10県：", pr.ha_2025.sort_values(ascending=False).head(10).round(0).to_dict())

# ---- 図1：都道府県の減少率（ピーク→2025年）
col = {"北海道・東北・北陸": BLUE, "関東・東山": GREEN, "東海以西（西日本）": ORANGE}
fig, a = plt.subplots(figsize=(8, 10))
a.barh(range(len(s)), s.decline_from_peak_pct, color=[col[g] for g in s.group])
a.set_yticks(range(len(s))); a.set_yticklabels(s.index, fontsize=8.5); a.invert_yaxis()
for i, v in enumerate(s.decline_from_peak_pct):
    a.text(v + 0.8, i, f"{v:.0f}%", va="center", fontsize=7.5)
from matplotlib.patches import Patch
a.legend(handles=[Patch(color=col[g], label=g) for g in G3], frameon=False, loc="center right"); a.set_xlim(0, 105)
a.set_xlabel("作付面積の減少率（1958年以降で最も広かった年→2025年、%）")
a.set_title("水稲の作付面積はどこで減ったか（都道府県）")
note(a, SRC2, y=-0.075)
fig.savefig(FIG / "w2_pref.png"); plt.close(fig)

# ---- 図2：まとまり別の面積と全国に占める割合
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for g in G3:
    d = gg[gg.group == g]
    ax[0].plot(d.year, d.area_ha / 1e4, color=col[g], lw=1.8, label=g)
    ax[1].plot(d.year, d.area_share, color=col[g], lw=1.8, label=g)
ax[0].set_title("作付面積（万ha）"); ax[1].set_title("全国に占める割合（%）")
ax[0].legend(frameon=False); ax[0].set_ylim(0)
ax[1].set_ylim(0, 60)
fig.suptitle("北日本の割合が上がり、西日本の割合が下がった", fontsize=13)
note(ax[0], SRC2, y=-0.14)
fig.savefig(FIG / "w2_group.png"); plt.close(fig)

# ---- 図3：集中度
fig, a = plt.subplots(figsize=(8.5, 4.6))
a.plot(cc.index, cc.top10_pct, color=BLUE, lw=1.8, label="上位10道県の割合（%）")
a.plot(cc.index, cc.top5_pct, color=LIGHT, lw=1.8, label="上位5道県の割合（%）")
a.set_ylabel("%"); a.set_ylim(0, 70)
b = a.twinx(); b.plot(cc.index, cc.hhi, color=ORANGE, lw=1.6, ls="--", label="HHI（右目盛）"); b.set_ylim(0, 700)
b.spines["right"].set_visible(True); b.set_ylabel("HHI")
h1, l1 = a.get_legend_handles_labels(); h2, l2 = b.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, frameon=False, loc="lower right")
a.set_title("作付面積の、主な産地への集中")
note(a, SRC2, y=-0.14)
fig.savefig(FIG / "w2_concentration.png"); plt.close(fig)
