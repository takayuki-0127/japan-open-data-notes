"""W2：日本近海の海面水温の上がり方は世界平均の何倍か（海域別・季節別、同じ期間でそろえた比較）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

g = load_global()
ja, meta = load_sst("all")
# ---- 気象庁の上昇率の再現（全期間、℃/100年）
rows = []
for a in [k for k in AREAS if k != "I"]:
    d, m = load_sst(a)
    for s in d.columns:
        t = trend(d[s], level=0.95)
        pub = m.loc["Slope", s] if m is not None else None
        rows.append(dict(area=a, name=AREAS[a], season=SEASONS[s], start=t["start"], end=t["end"], n=t["n"],
                         slope_100y=t["slope"] * 100, lo95_ols=t["lo_ols"] * 100, hi95_ols=t["hi_ols"] * 100,
                         lo95_hac=t["lo_hac"] * 100, hi95_hac=t["hi_hac"] * 100, jma_published=pub))
ar = pd.DataFrame(rows)
ar.round(3).to_csv(RES / "w2_area_season_trends.csv", index=False)
tg = trend(g, level=0.95)
print("全球 全期間", tg["start"], tg["end"], round(tg["slope"] * 100, 2), "（気象庁の公表 0.63）")
an = ar[ar.season == "年"]
print(an[["name", "start", "slope_100y", "jma_published"]].round(2).to_string())
print("再現の最大差", (ar["slope_100y"] - pd.to_numeric(ar["jma_published"], errors="coerce")).abs().max().round(3))

# ---- 同じ期間でそろえた比較
cmp = []
for a0, a1 in [(1908, 2025), (1950, 2025), (1980, 2025), (2000, 2025)]:
    tj, tw = trend(ja["Annual"], a0, a1, level=0.95), trend(g, a0, a1, level=0.95)
    cmp.append(dict(period=f"{a0}–{a1}", japan=tj["slope"] * 100, japan_lo=tj["lo_hac"] * 100, japan_hi=tj["hi_hac"] * 100,
                    globe=tw["slope"] * 100, globe_lo=tw["lo_hac"] * 100, globe_hi=tw["hi_hac"] * 100,
                    ratio=tj["slope"] / tw["slope"], n_japan=tj["n"]))
cmp = pd.DataFrame(cmp)
# 比の不確かさ：年々の差（日本−全球×比）ではなく、日本の値を全球で回帰した傾き（同じ年の変動を相殺）
for i, (a0, a1) in enumerate([(1908, 2025), (1950, 2025), (1980, 2025), (2000, 2025)]):
    j = pd.concat([ja["Annual"], g], axis=1, keys=["j", "g"]).loc[a0:a1].dropna()
    import statsmodels.api as sm
    f = sm.OLS(j["j"], sm.add_constant(j["g"])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    cmp.loc[i, "beta_japan_on_global"] = f.params["g"]; cmp.loc[i, "beta_se"] = f.bse["g"]
    cmp.loc[i, "corr"] = j.corr().iloc[0, 1]
cmp.round(3).to_csv(RES / "w2_japan_vs_global.csv", index=False)
print(cmp.round(2).to_string())

# 10年平均の差
dec = pd.DataFrame({"日本近海": [ja["Annual"].loc[a:a + 9].mean() for a in (1910, 1980, 2016)],
                    "全球": [g.loc[a:a + 9].mean() for a in (1910, 1980, 2016)]}, index=["1910–1919", "1980–1989", "2016–2025"])
print(dec.round(2)); dec.round(3).to_csv(RES / "w2_decade_means.csv")
print("日本近海 上位年", ja["Annual"].sort_values(ascending=False).head(5).round(2).to_dict())

# ---- 図1：日本近海と全球の推移
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(g.index, g, color=GRAY, lw=1, alpha=0.8); ax.plot(g.index, g.rolling(5, center=True).mean(), color=INK, lw=2, label="全球平均（5年移動平均）")
ax.plot(ja.index, ja["Annual"], color=LIGHT, lw=1); ax.plot(ja.index, ja["Annual"].rolling(5, center=True, min_periods=3).mean(), color=BLUE, lw=2, label="日本近海13海域平均（5年移動平均）")
for s, col, lab in [(ja["Annual"], BLUE, "日本近海"), (g, INK, "全球")]:
    t = trend(s, 1908, 2025); x = np.array([1908, 2025]); m = s.loc[1908:2025].dropna()
    ax.plot(x, t["slope"] * (x - m.index.values.mean()) + m.mean(), color=col, ls="--", lw=1.1)
r0 = cmp.iloc[0]
ax.text(1895, 1.38, f"1908–2025年の上昇率：日本近海 {r0.japan:.2f}℃/100年、全球 {r0.globe:.2f}℃/100年（{r0.ratio:.1f}倍）", fontsize=9.5)
ax.axhline(0, color=GRAY, lw=0.6); ax.set_ylim(-1.8, 1.65)
ax.set_title("年平均海面水温の平年差（1991–2020年平均との差、℃）"); ax.set_xlabel("年"); ax.set_ylabel("℃")
ax.legend(fontsize=9, frameon=False, loc="lower right")
fig.text(0, -0.03, SRC_SST, fontsize=8, color=GRAY); save(fig, "w2_series.png")

# ---- 図2：海域別（年）
a2 = an[an.area != "all"].sort_values("slope_100y")
fig, ax = plt.subplots(figsize=(8.5, 5))
yy = np.arange(len(a2))
ax.errorbar(a2["slope_100y"], yy, xerr=[a2["slope_100y"] - a2["lo95_hac"], a2["hi95_hac"] - a2["slope_100y"]], fmt="o", color=BLUE, capsize=3)
ax.axvline(tg["slope"] * 100, color=INK, ls="--", lw=1.2, label=f"全球平均 {tg['slope']*100:.2f}")
ax.axvline(an[an.area == "all"]["slope_100y"].iloc[0], color=ORANGE, ls="--", lw=1.2, label=f"日本近海平均 {an[an.area=='all']['slope_100y'].iloc[0]:.2f}")
ax.set_yticks(yy); ax.set_yticklabels(a2["name"]); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("年平均海面水温の上昇率（℃/100年、95%信頼区間はNewey-West）"); ax.set_title("海域別の上昇率（統計開始〜2025年）")
ax.legend(fontsize=9, frameon=False, loc="lower right")
fig.text(0, -0.03, SRC_SST + "。網走沖は期間が短いため除く", fontsize=8, color=GRAY); save(fig, "w2_area.png")

# ---- 図3：海域×季節
order = list(a2["name"])[::-1] + ["日本近海（13海域平均）"]
hm = ar.pivot(index="name", columns="season", values="slope_100y").loc[order, ["冬(1-3月)", "春(4-6月)", "夏(7-9月)", "秋(10-12月)", "年"]]
sig = ar.assign(s=(ar.lo95_ols > 0)).pivot(index="name", columns="season", values="s").loc[order, hm.columns]
fig, ax = plt.subplots(figsize=(7.5, 6))
im = ax.imshow(hm.values, cmap="OrRd", vmin=0, vmax=2.8, aspect="auto")
for i in range(hm.shape[0]):
    for j in range(hm.shape[1]):
        v = hm.values[i, j]; ax.text(j, i, f"{v:.2f}" + ("" if sig.values[i, j] else "*"), ha="center", va="center", fontsize=9,
                                    color="white" if v > 1.9 else INK)
ax.set_xticks(range(hm.shape[1])); ax.set_xticklabels(hm.columns); ax.set_yticks(range(hm.shape[0])); ax.set_yticklabels(hm.index)
ax.set_title("季節別の上昇率（℃/100年）"); fig.colorbar(im, ax=ax, shrink=0.7)
fig.text(0, -0.02, SRC_SST + "。*は95%で有意でない（OLS）", fontsize=8, color=GRAY); save(fig, "w2_season.png")
sea = ar[ar.area != "all"].groupby("season")["slope_100y"].agg(["mean", "min", "max"]); print(sea.round(2))
print(hm.round(2))
