"""L2：この10年（2016→2026年）で、どんな標準地の地価が上がったか。上がった地点の割合、駅からの距離・用途・もとの価格との関係（重回帰）、都道府県別"""
from common import *
import statsmodels.formula.api as smf
d = load()
x = d[d[2016].notna() & d[2026].notna() & d.use.isin(["住宅地", "商業地"])].copy()
x["chg"] = (x[2026] / x[2016] - 1) * 100; x["lchg"] = np.log(x[2026] / x[2016]) * 100
x["lp16"] = np.log(x[2016]); x["km"] = x.station_m / 1000
x["km_bin"] = pd.cut(x.km, [-0.01, 0.5, 1, 2, 5, 1e3], labels=["〜0.5km", "0.5〜1km", "1〜2km", "2〜5km", "5km〜"])
print(len(x))
# 1) 上がった・下がった地点の割合
share = x.groupby(["area", "use"]).agg(n=("chg", "size"), up=("chg", lambda s: (s > 0).mean() * 100), down=("chg", lambda s: (s < 0).mean() * 100), median=("chg", "median"))
share.round(1).to_csv(RES / "l2_share_up.csv", encoding="utf-8-sig"); print(share.round(1))
# 2) 駅からの距離
kb = x.groupby(["use", "km_bin"]).chg.median().unstack(0); kb.round(1).to_csv(RES / "l2_by_station_km.csv", encoding="utf-8-sig"); print(kb.round(1))
# 3) 重回帰：10年の変化（対数×100）
m = smf.ols("lchg ~ C(area, Treatment('地方圏')) * C(use) + np.log1p(km) + lp16", x).fit(cov_type="cluster", cov_kwds={"groups": x.code})
m_pref = smf.ols("lchg ~ C(pref) + C(use) + np.log1p(km) + lp16", x).fit(cov_type="cluster", cov_kwds={"groups": x.code})
print(m.params.round(2)); print("pref FE:", m_pref.params[["np.log1p(km)", "lp16"]].round(2), m_pref.pvalues[["np.log1p(km)", "lp16"]].round(3), m_pref.rsquared)
# もとの価格が高い地点ほど上がったか（県の中で）
x["lp16_rank_in_pref"] = x.groupby(["pref", "use"]).lp16.rank(pct=True)
q = pd.cut(x.lp16_rank_in_pref, [0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=["下位20%", "20〜40%", "40〜60%", "60〜80%", "上位20%"])
qq = x.groupby([q, "use"]).chg.median().unstack(); qq.round(1).to_csv(RES / "l2_by_price_quintile_in_pref.csv", encoding="utf-8-sig"); print(qq.round(1))
# 4) 都道府県別（住宅地の中央値）
pr = x[x.use == "住宅地"].assign(pref=lambda v: v.pref.map(PREF)).groupby("pref").agg(n=("chg", "size"), median=("chg", "median"), up=("chg", lambda s: (s > 0).mean() * 100)).sort_values("median")
pr.round(1).to_csv(RES / "l2_pref_residential.csv", encoding="utf-8-sig"); print(pr.head(5).round(1), pr.tail(8).round(1))
# 上位の地点
top = x.sort_values("chg", ascending=False)[["address", "use", "station", "station_m", 2016, 2026, "chg"]].head(15); top.to_csv(RES / "l2_top_points.csv", index=False, encoding="utf-8-sig"); print(top.to_string())
s = {"n": len(x), "share_up_all": (x.chg > 0).mean() * 100, "share_down_all": (x.chg < 0).mean() * 100, "median_all": x.chg.median(),
     "b_logkm": m_pref.params["np.log1p(km)"], "p_logkm": m_pref.pvalues["np.log1p(km)"], "b_lp16": m_pref.params["lp16"], "p_lp16": m_pref.pvalues["lp16"], "r2_pref": m_pref.rsquared,
     "res_top_q": qq.loc["上位20%", "住宅地"], "res_bottom_q": qq.loc["下位20%", "住宅地"], "com_top_q": qq.loc["上位20%", "商業地"], "com_bottom_q": qq.loc["下位20%", "商業地"],
     "pref_res_max": pr.index[-1], "pref_res_max_v": pr["median"].iloc[-1], "pref_res_min": pr.index[0], "pref_res_min_v": pr["median"].iloc[0],
     "n_pref_res_median_negative": int((pr["median"] < 0).sum())}
pd.Series(s).to_csv(RES / "l2_summary.csv", header=["value"]); print(pd.Series(s))

# 図1：地図（変化率の散布）
fig, ax = plt.subplots(figsize=(7.5, 7.5))
z = x.sort_values("chg"); c = np.clip(z.lchg, -40, 60)
sc = ax.scatter(z.lon, z.lat, c=c, cmap="RdBu_r", vmin=-40, vmax=40, s=3, lw=0)
ax.set_xlim(127.5, 146); ax.set_ylim(26, 45.6); ax.set_aspect(1.2); ax.axis("off")
cb = fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.01); cb.set_label("2016→2026年の変化（対数×100、±40で頭打ち）")
ax.set_title("この10年の地価の変化：赤は上昇、青は下落", loc="left")
fig.text(0.01, 0.02, SOURCE, fontsize=6.5, color="#8a8984"); fig.savefig(FIG / "l2_map.png"); plt.close(fig)

# 図2：圏域×用途の上昇地点の割合
fig, ax = plt.subplots(figsize=(9, 4)); sh = share.reset_index(); sh["o"] = sh.area.map({"東京圏": 0, "大阪圏": 1, "名古屋圏": 2, "地方圏": 3}); sh = sh.sort_values(["o", "use"]); lab = sh.area + "・" + sh.use; yy = np.arange(len(sh))
ax.barh(yy, sh.up, color=BLUE, label="上がった"); ax.barh(yy, sh.down, left=sh.up, color=ORANGE, label="下がった")
for i, (u, med) in enumerate(zip(sh.up, sh["median"])): ax.text(101, i, f"中央値 {med:+.0f}%", va="center", fontsize=8.5)
ax.set_yticks(yy, lab); ax.invert_yaxis(); ax.set_xlim(0, 125); ax.set_xlabel("標準地の割合（%）"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.18), ncol=2, fontsize=9)
ax.set_title("2016→2026年：地方圏の住宅地は、上がった地点と下がった地点が半々", loc="left", fontsize=12)
fig.text(0.01, -0.13, SOURCE + "（圏域は都道府県で近似）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "l2_share.png"); plt.close(fig)

# 図3：県の中で、もとの価格が高い地点ほど上がったか
fig, ax = plt.subplots(figsize=(9, 3.8)); xx = np.arange(len(qq))
ax.bar(xx - 0.2, qq["住宅地"], 0.4, color=BLUE, label="住宅地"); ax.bar(xx + 0.2, qq["商業地"], 0.4, color=ORANGE, label="商業地")
for i, (a_, b_) in enumerate(zip(qq["住宅地"], qq["商業地"])): ax.text(i - 0.2, a_ + 1, f"{a_:.0f}", ha="center", fontsize=8.5); ax.text(i + 0.2, b_ + 1, f"{b_:.0f}", ha="center", fontsize=8.5)
ax.axhline(0, color=INK, lw=0.6); ax.set_xticks(xx, qq.index); ax.set_xlabel("2016年の価格の、県の中での順位"); ax.set_ylabel("2016→2026年の変化（中央値、%）"); ax.legend(frameon=False)
ax.set_title("同じ県の中でも、もともと高い地点ほど大きく上がった（二極化）", loc="left")
fig.text(0.01, -0.06, SOURCE, fontsize=7, color="#8a8984"); fig.savefig(FIG / "l2_quintile.png"); plt.close(fig)

# 図4：都道府県（住宅地の中央値）
fig, ax = plt.subplots(figsize=(8, 9)); yy = np.arange(len(pr))
ax.barh(yy, pr["median"], color=[ORANGE if v > 0 else BLUE for v in pr["median"]])
ax.set_yticks(yy, pr.index, fontsize=8); ax.axvline(0, color=INK, lw=0.6); ax.set_xlabel("住宅地の2016→2026年の変化（標準地の中央値、%）")
ax.set_title(f"住宅地：47都道府県のうち{int((pr['median'] < 0).sum())}で、中央値が下落", loc="left")
fig.text(0.01, 0.01, SOURCE, fontsize=6.5, color="#8a8984"); fig.savefig(FIG / "l2_pref.png"); plt.close(fig)
