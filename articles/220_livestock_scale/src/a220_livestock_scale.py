"""220 養豚と採卵鶏の大規模化は、どれだけ進んだか？（規模分布・ジニ係数）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

pig, lay, ps, ls = load()

# 規模の階層をそろえる（豚：肥育豚の頭数規模、採卵鶏：成鶏めすの羽数規模）
def pig_classes(m):
    s = ps[ps.measure == m].set_index("year")
    return pd.DataFrame({"1〜99頭": s.c1_99, "100〜299": s.c100_299, "300〜499": s.c300_499, "500〜999": s.c500_999,
                         "1,000〜1,999": s.c1000_1999, "2,000頭以上": s.c2000plus})

def lay_classes(m):
    s = ls[ls.measure == m].set_index("year")
    return pd.DataFrame({"1,000〜9,999羽": s.c1000_4999 + s.c5000_9999.fillna(0), "1万〜4.9万": s.c10000_49999,
                         "5万〜9.9万": s.c50000_99999, "10万羽以上": s.c100000_499999 + s.c500000plus.fillna(0)})

PF, PH, LF, LH = pig_classes("farms"), pig_classes("head"), lay_classes("farms"), lay_classes("hens_thousand")


def gini(f, h):
    """階層別の戸数 f と頭数 h から、階層の中は同じ規模とみなしたローレンツ曲線とジニ係数"""
    x = np.r_[0, np.cumsum(f) / f.sum()]; y = np.r_[0, np.cumsum(h) / h.sum()]
    return 1 - np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1])), x, y


rows = []
for y in PF.index:
    gp = gini(PF.loc[y].values, PH.loc[y].values)[0]; gl = gini(LF.loc[y].values, LH.loc[y].values)[0]
    p3 = ps[(ps.year == y) & (ps.measure == "head")].c3000plus.iloc[0] / ps[(ps.year == y) & (ps.measure == "head")].subtotal.iloc[0]
    f3 = ps[(ps.year == y) & (ps.measure == "farms")].c3000plus.iloc[0] / ps[(ps.year == y) & (ps.measure == "farms")].subtotal.iloc[0]
    rows.append(dict(year=y, gini_pig=round(gp, 3), gini_layer=round(gl, 3),
                     pig_top_head_share=round(PH.loc[y, "2,000頭以上"] / PH.loc[y].sum() * 100, 1),
                     pig_top_farm_share=round(PF.loc[y, "2,000頭以上"] / PF.loc[y].sum() * 100, 1),
                     pig_3000_head_share=round(p3 * 100, 1) if p3 == p3 else None, pig_3000_farm_share=round(f3 * 100, 1) if f3 == f3 else None,
                     layer_top_hen_share=round(LH.loc[y, "10万羽以上"] / LH.loc[y].sum() * 100, 1),
                     layer_top_farm_share=round(LF.loc[y, "10万羽以上"] / LF.loc[y].sum() * 100, 1)))
G = pd.DataFrame(rows); G.to_csv(RES / "concentration_2002_2023.csv", index=False, encoding="utf-8-sig")

# 豚：3,000頭以上を分けた7階層でのジニ係数（2008年以降）と、最上位階層の1戸あたり規模
extra = []
for y in PF.index[PF.index >= 2008]:
    f = ps[(ps.year == y) & (ps.measure == "farms")].iloc[0]; h = ps[(ps.year == y) & (ps.measure == "head")].iloc[0]
    cl = lambda r: np.array([r.c1_99, r.c100_299, r.c300_499, r.c500_999, r.c1000_1999, r.c2000plus - r.c3000plus, r.c3000plus], float)
    extra.append(dict(year=y, gini_pig_7class=round(gini(cl(f), cl(h))[0], 3), pig_mean_3000plus=round(h.c3000plus / f.c3000plus),
                      pig_mean_2000plus=round(h.c2000plus / f.c2000plus)))
X = pd.DataFrame(extra)
X["layer_mean_100k_plus_thousand"] = [round(LH.loc[y, "10万羽以上"] / LF.loc[y, "10万羽以上"], 1) for y in X.year]
X.to_csv(RES / "pig_7class_and_top_mean.csv", index=False, encoding="utf-8-sig"); print(X.to_string())

pig["per_farm"] = pig["head"] / pig["farms"]
lay["per_farm"] = lay.hens_thousand * 1000 / lay.farms_layer.fillna(lay.farms_all)
L = lay[~((lay.year == 1997) & (lay.basis == "ge300"))]
pig.to_csv(RES / "pig_per_farm.csv", index=False, encoding="utf-8-sig"); L.to_csv(RES / "layer_per_farm.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 200); print(G.to_string())
print(pig[pig.year.isin([1960, 1970, 1980, 1990, 2000, 2010, 2014, 2024])].to_string())
print(L[L.year.isin([1960, 1970, 1980, 1990, 1991, 1998, 2008, 2024])].to_string())

# 図1 戸数と1戸あたり（対数目盛）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
ax = axes[0]
ax.plot(pig.year, pig.farms, "-", color=ORANGE, lw=2, label="養豚の飼養戸数")
for b, ls_ in [("all", "-"), ("ge300", "--"), ("ge1000", ":")]:
    s = L[L.basis == b]; ax.plot(s.year, s.farms_layer.fillna(s.farms_all), ls_, color=BLUE, lw=2,
                                 label={"all": "採卵鶏の飼養戸数（すべて）", "ge300": "採卵鶏（成鶏めす300羽以上）", "ge1000": "採卵鶏（1,000羽以上）"}[b])
ax.set_yscale("log"); ax.set_title("飼養戸数（戸、対数目盛）", loc="left"); ax.legend(frameon=False, fontsize=8)
ax = axes[1]
ax.plot(pig.year, pig.per_farm, color=ORANGE, lw=2, label="豚：1戸あたり飼養頭数（頭）")
for b, ls_ in [("all", "-"), ("ge300", "--"), ("ge1000", ":")]:
    s = L[L.basis == b]; ax.plot(s.year, s.per_farm, ls_, color=BLUE, lw=2, label="採卵鶏：1戸あたり成鶏めす（羽）" if b == "all" else None)
ax.set_yscale("log"); ax.set_title("1戸あたりの規模（対数目盛）", loc="left"); ax.legend(frameon=False, fontsize=8)
fig.suptitle("戸数は減り、1戸あたりの規模は大きくなった（1960〜2024年、全国。採卵鶏は1991年と1998年に調査対象が変わった）", x=0.01, ha="left", fontsize=11, y=1.02)
fig.tight_layout(); save(fig, "a220_long.png")

# 図2 規模別の頭羽数の構成比
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
for ax, H, title, cmap in [(axes[0], PH, "豚：肥育豚の頭数規模別の飼養頭数の割合（%）", "Oranges"), (axes[1], LH, "採卵鶏：羽数規模別の成鶏めす羽数の割合（%）", "Blues")]:
    sh = H.div(H.sum(1), axis=0) * 100; cols = plt.get_cmap(cmap)(np.linspace(0.2, 0.95, sh.shape[1]))
    ax.stackplot(sh.index, sh.T.values, labels=sh.columns, colors=cols)
    ax.set_xlim(2002, 2023); ax.set_ylim(0, 100); ax.set_xticks([2002, 2006, 2010, 2014, 2018, 2023]); ax.set_title(title, loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8, loc="lower left", reverse=True)
fig.suptitle("いちばん大きい階層に、頭羽数が集まっていった（2002〜2023年、調査休止年は前後をつないだ）", x=0.01, ha="left", fontsize=11, y=1.02)
fig.tight_layout(); save(fig, "a220_share.png")

# 図3 ローレンツ曲線（2002年と2023年）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
for ax, F, H, title, c in [(axes[0], PF, PH, "豚（肥育豚の頭数）", ORANGE), (axes[1], LF, LH, "採卵鶏（成鶏めすの羽数）", BLUE)]:
    for y, ls_ in [(2002, "--"), (2023, "-")]:
        g, x, yy = gini(F.loc[y].values, H.loc[y].values)
        ax.plot(x * 100, yy * 100, ls_, color=c, lw=2, marker="o", ms=3, label=f"{y}年（ジニ係数 {g:.3f}）")
    ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8)
    ax.set_xlabel("規模の小さい順に並べた戸数の累積（%）"); ax.set_ylabel("頭羽数の累積（%）")
    ax.set_title(title, loc="left"); ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.suptitle("ローレンツ曲線：線が右下にふくらむほど、少ない経営に集中している", x=0.01, ha="left", fontsize=11, y=1.02)
fig.tight_layout(); save(fig, "a220_lorenz.png")
