"""A1：「平均所得ランキング」の読み方（納税者1人あたり と 住民1人あたり、小さな町の跳ね方）"""
from common import *
from scipy.stats import spearmanr

d = load()
d["pc"] = d["C120110"] / d["A2301"] * 100            # 住民1人あたり（万円）
d["taxrate"] = d["C120120"] / d["A2301"]              # 納税者の割合（住民に対する）
d["r_inc"] = d["inc"].rank(ascending=False, method="min").astype(int)
d["r_pc"] = d["pc"].rank(ascending=False, method="min").astype(int)
d["move"] = d["r_pc"] - d["r_inc"]
d["band"] = pd.cut(d["A2301"], [0, 5000, 10000, 30000, 100000, 1e9], labels=["5千人未満", "5千〜1万", "1万〜3万", "3万〜10万", "10万人以上"])
d["dev"] = np.log(d["inc"]) - np.log(d["inc"]).groupby(d["pref_code"]).transform("median")

s = {"n": len(d), "spearman_inc_pc": spearmanr(d.inc, d.pc)[0], "median_inc": d.inc.median(), "median_pc": d.pc.median(),
     "taxrate_min": d.taxrate.min(), "taxrate_max": d.taxrate.max(), "taxrate_median": d.taxrate.median(),
     "corr_taxrate_old": np.corrcoef(d.taxrate, d.old)[0, 1], "share_move_over300": (d.move.abs() >= 300).mean(),
     "top20_small_under10k": int((d.nsmallest(20, "r_inc").A2301 < 10000).sum()), "share_under10k": (d.A2301 < 10000).mean()}
pd.Series(s).round(3).to_csv(RES / "a1_summary.csv", header=["value"]); print(pd.Series(s).round(3))
cols = ["pref_name", "name", "A2301", "inc", "pc", "taxrate", "old", "r_inc", "r_pc", "move"]
d.nsmallest(20, "r_inc")[cols].round(3).to_csv(RES / "a1_top20.csv", index=False, encoding="utf-8-sig")
pd.concat([d.nlargest(10, "move"), d.nsmallest(10, "move")])[cols].round(3).to_csv(RES / "a1_movers.csv", index=False, encoding="utf-8-sig")
g = d.groupby("band", observed=True).agg(n=("inc", "size"), median=("inc", "median"), sd_log_dev=("dev", "std")).round(3)
g.to_csv(RES / "a1_band.csv", encoding="utf-8-sig"); print(g)

# 図1：納税者1人あたり と 住民1人あたり
fig, ax = plt.subplots(figsize=(8, 5))
sc = ax.scatter(d.inc, d.pc, c=d.taxrate * 100, cmap="Blues", vmin=28, vmax=60, s=12, lw=0, alpha=0.85)
for _, r in pd.concat([d.nlargest(3, "move"), d.nsmallest(3, "move")]).iterrows():
    ax.annotate(f"{r['name']}（{r.r_inc}位→{r.r_pc}位）", (r.inc, r.pc), xytext=(5, -3), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(240, 800); ax.set_ylim(65, 450)
from matplotlib.ticker import FixedLocator, NullLocator
ax.xaxis.set_major_locator(FixedLocator([250, 300, 400, 500, 600, 800])); ax.xaxis.set_minor_locator(NullLocator()); ax.set_xticklabels(["250", "300", "400", "500", "600", "800"])
ax.yaxis.set_major_locator(FixedLocator([75, 100, 150, 200, 300, 400])); ax.yaxis.set_minor_locator(NullLocator()); ax.set_yticklabels(["75", "100", "150", "200", "300", "400"])
ax.set_xlabel("納税者1人あたり所得（万円、対数目盛）"); ax.set_ylabel("住民1人あたり所得（万円、対数目盛）")
cb = fig.colorbar(sc, ax=ax, pad=0.01); cb.set_label("住民に占める納税者の割合（%）")
ax.set_title("「1人あたり」の分母を変えると、順位が約1,000位動く町がある", loc="left")
fig.text(0.01, -0.03, SOURCE + "（所得は2024年度＝2023年分。港区など800万円超の6区市は範囲外）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "a1_two_ranks.png"); plt.close(fig)

# 図2：納税者の割合と高齢化
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.scatter(d.old * 100, d.taxrate * 100, s=10, color=BLUE, alpha=0.5, lw=0)
ax.set_xlabel("65歳以上の割合（%、2020年）"); ax.set_ylabel("住民に占める納税者の割合（%）")
ax.set_title(f"高齢化が進んだ町ほど、納税者の割合が低い（相関 {s['corr_taxrate_old']:.2f}）", loc="left")
fig.text(0.01, -0.04, SOURCE, fontsize=8, color="#8a8984"); fig.savefig(FIG / "a1_taxrate_old.png"); plt.close(fig)

# 図3：人口規模と、上位に出てくる小さな町
fig, ax = plt.subplots(figsize=(8, 4.8))
top = d.nsmallest(20, "r_inc")
ax.scatter(d.A2301, d.inc, s=9, color=GRAY, alpha=0.5, lw=0, label="全市区町村")
sm = top[top.A2301 < 20000]
ax.scatter(top.A2301, top.inc, s=24, color=BLUE, label="上位20")
ax.scatter(sm.A2301, sm.inc, s=40, color=ORANGE, label="上位20のうち人口2万人未満")
for _, r in sm.iterrows():
    ax.annotate(f"{r['name']}（{r.r_inc}位）", (r.A2301, r.inc), xytext=(6, -12 if r['name'] == "猿払村" else 3), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_xscale("log"); ax.set_ylim(230, 950)
from matplotlib.ticker import FixedLocator, NullLocator
ax.xaxis.set_major_locator(FixedLocator([1e3, 1e4, 1e5, 1e6])); ax.xaxis.set_minor_locator(NullLocator()); ax.set_xticklabels(["1千", "1万", "10万", "100万"]); ax.set_xlabel("人口（住民基本台帳、対数目盛）"); ax.set_ylabel("納税者1人あたり所得（万円）")
ax.legend(frameon=False, loc="upper left"); ax.set_title("上位20に、人口2万人未満の町村が6つ入っている", loc="left")
fig.text(0.01, -0.04, SOURCE + "（港区・千代田区・渋谷区は範囲外）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "a1_size.png"); plt.close(fig)
