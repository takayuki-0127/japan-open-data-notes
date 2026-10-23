"""植物（うめ・さくら・いちょう・かえで）の開花・紅葉日の変化：地点ごとのTheil–Sen、地点固定効果の回帰、気温との関係"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from common import *

d = load(); T = jpn_temp()
SP = {"001": ("うめの開花", [1, 2]), "004": ("さくらの開花", [2, 3]), "005": ("さくらの満開", [3, 4]),
      "013": ("いちょうの黄葉", [10, 11]), "015": ("かえでの紅葉", [10, 11])}
COL = {"001": PURPLE, "004": ORANGE, "005": "#f2a07b", "013": "#d4a72c", "015": "#c0392b"}
# さくらは rm が 6・7 の値（北海道・沖縄などでソメイヨシノ以外を観測していると考えられる地点）を除く
x = d[(d.obs == 1) & d.code.isin(SP)].copy()
x = x[~((x.code.isin(["004", "005"])) & x.rm.isin(["6", "7"]))]
x = x[x.year <= 2025]
x["temp"] = [T.loc[y, SP[c][1]].mean() if y in T.index else np.nan for y, c in zip(x.year, x.code)]

# 地点ごとのTheil–Sen（1953〜2025年、30年以上観測がある地点）
st = []
for (c, s), g in x.groupby(["code", "st"]):
    if len(g) < 30: continue
    b, lo, hi = theil(g.doy.values, g.year.values)
    tb = np.polyfit(g.temp, g.doy, 1)[0] if g.temp.notna().sum() >= 30 else np.nan
    st.append({"code": c, "name": SP[c][0], "st": s, "stname": g.stname.iloc[0], "lat": g.lat.iloc[0], "n": len(g),
               "first": g.year.min(), "last": g.year.max(), "slope_dec": b * 10, "lo": lo * 10, "hi": hi * 10, "days_per_C": tb})
ST = pd.DataFrame(st); ST.to_csv(RES / "s1_station_trends.csv", index=False, encoding="utf-8-sig")

# 地点固定効果つきの回帰（年トレンド、気温）
rows = []
for c, (nm, mon) in SP.items():
    g = x[(x.code == c) & x.st.isin(ST[ST.code == c].st)]
    m1 = smf.ols("doy ~ year + C(st)", g).fit(cov_type="cluster", cov_kwds={"groups": g.year})
    m2 = smf.ols("doy ~ temp + C(st)", g.dropna(subset=["temp"])).fit(cov_type="cluster", cov_kwds={"groups": g.dropna(subset=["temp"]).year})
    a = g[g.year.between(1961, 1990)].groupby("st").doy.mean(); b = g[g.year.between(1996, 2025)].groupby("st").doy.mean()
    both = a.index.intersection(b.index)
    s = ST[ST.code == c]
    rows.append({"code": c, "name": nm, "temp_months": "・".join(f"{k}月" for k in mon), "n_stations": len(s), "n_obs": len(g),
                 "trend_dec": m1.params["year"] * 10, "trend_lo": m1.conf_int().loc["year", 0] * 10, "trend_hi": m1.conf_int().loc["year", 1] * 10,
                 "days_per_C": m2.params["temp"], "dpc_lo": m2.conf_int().loc["temp", 0], "dpc_hi": m2.conf_int().loc["temp", 1],
                 "change_6190_9625": (b[both] - a[both]).mean(), "n_both": len(both),
                 "station_median_dec": s.slope_dec.median(), "share_earlier": (s.slope_dec < 0).mean() * 100,
                 "corr_lat_sens": s[["lat", "days_per_C"]].corr().iloc[0, 1]})
R = pd.DataFrame(rows); R.to_csv(RES / "s1_pooled.csv", index=False, encoding="utf-8-sig"); print(R.round(2).to_string())

# 年ごとの観測地点数（2021年の見直しの影響）
cnt = x.groupby(["code", "year"]).st.nunique().unstack(0); cnt.to_csv(RES / "s1_nstations_by_year.csv", encoding="utf-8-sig")
print(cnt.loc[[1953, 1990, 2019, 2020, 2021, 2025]])

# さくら開花：地点平均からの偏差の全国平均（地点の平年＝1991〜2020年平均）
g = x[(x.code == "004") & x.st.isin(ST[ST.code == "004"].st)].copy()
g["anom"] = g.doy - g.groupby("st").doy.transform(lambda s: s[g.loc[s.index, "year"].between(1991, 2020)].mean())
nat = g.groupby("year").agg(anom=("anom", "mean"), n=("st", "nunique"), temp=("temp", "first")).reset_index()
nat.to_csv(RES / "s1_sakura_national.csv", index=False, encoding="utf-8-sig")
r = np.corrcoef(nat.anom, nat.temp)[0, 1]; print("sakura corr with Feb-Mar temp", r)

lab = {c: v[0] for c, v in SP.items()}
# 図1：地点ごとの変化（10年あたり日）
fig, ax = plt.subplots(figsize=(8.4, 4.2))
codes = list(SP)
data = [ST[ST.code == c].slope_dec.dropna() for c in codes]
bp = ax.boxplot(data, vert=False, widths=.55, patch_artist=True, showfliers=False)
for p_, c in zip(bp["boxes"], codes): p_.set_facecolor(COL[c]); p_.set_alpha(.55)
for i, (c, v) in enumerate(zip(codes, data)):
    ax.scatter(v, np.random.default_rng(0).normal(i + 1, .06, len(v)), s=8, color=COL[c], alpha=.7, zorder=3)
    rr = R[R.code == c].iloc[0]
    ax.text(ax.get_xlim()[1] if False else 9.6, i + 1, f"中央値 {rr.station_median_dec:+.1f}日\n早まった地点 {rr.share_earlier:.0f}%", va="center", fontsize=8.5)
ax.axvline(0, color=INK, lw=.7); ax.set_yticks(range(1, 6)); ax.set_yticklabels([lab[c] + f"（{len(v)}地点）" for c, v in zip(codes, data)])
ax.set_xlim(-6, 13); ax.set_xlabel("10年あたりの変化（日、マイナス＝早まった）")
ax.set_title("地点ごとの変化の速さ（1953〜2025年、30年以上観測した地点）", loc="left", fontsize=12)
note(ax, SOURCE + "\nTheil–Sen推定。さくらはソメイヨシノ以外と考えられる値（rm 6・7）を除く", -0.15)
fig.savefig(FIG / "s1_station_trends.png"); plt.close(fig)

# 図2：さくら開花の全国偏差と2〜3月の気温
fig, ax = plt.subplots(figsize=(8.4, 4.0))
ax.bar(nat.year, nat.anom, color=np.where(nat.anom < 0, ORANGE, LIGHT), width=.8)
ax.set_ylabel("開花日の平年差（日）"); ax.axhline(0, color=INK, lw=.6)
ax2 = ax.twinx(); ax2.plot(nat.year, nat.temp, color=INK, lw=1.3); ax2.invert_yaxis(); ax2.set_ylabel("2〜3月の気温偏差（℃、上下反転）")
ax2.spines["top"].set_visible(False)
ax.set_title(f"さくらの開花日（地点平均の平年差、棒）と2〜3月の気温（線）　相関 {r:.2f}", loc="left", fontsize=11.5)
note(ax, SOURCE + "\n気温は気象庁「日本の月平均気温偏差」（15地点平均、1991〜2020年平均との差）", -0.14)
fig.savefig(FIG / "s1_sakura_temp.png"); plt.close(fig)

# 図3：1℃あたりの日数と、地点の緯度
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.0), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axes[0]
for i, c in enumerate(codes):
    rr = R[R.code == c].iloc[0]
    ax.barh(i, rr.days_per_C, color=COL[c], alpha=.85)
    ax.errorbar(rr.days_per_C, i, xerr=[[rr.days_per_C - rr.dpc_lo], [rr.dpc_hi - rr.days_per_C]], color=INK, capsize=3, lw=1)
    ax.text(0.3 if rr.days_per_C < 0 else -0.3, i, f"{rr.days_per_C:+.1f}日", ha="left" if rr.days_per_C < 0 else "right", va="center", fontsize=9.5)
ax.axvline(0, color=INK, lw=.6); ax.set_yticks(range(5)); ax.set_yticklabels([f"{lab[c]}\n（{SP[c][1][0]}・{SP[c][1][1]}月の気温）" for c in codes], fontsize=8.5)
ax.invert_yaxis(); ax.set_xlabel("気温が1℃高い年の日のずれ（日）"); ax.set_title("1℃あたり何日ずれるか", loc="left", fontsize=11.5)
ax = axes[1]
for c in ["004", "015"]:
    s = ST[ST.code == c]
    ax.scatter(s.lat, s.days_per_C, s=18, color=COL[c], label=lab[c], alpha=.85)
    k = np.polyfit(s.lat.dropna(), s.days_per_C[s.lat.notna()], 1); xx = np.linspace(s.lat.min(), s.lat.max(), 10); ax.plot(xx, np.polyval(k, xx), color=COL[c], lw=1)
ax.axhline(0, color=INK, lw=.6); ax.set_xlabel("地点の緯度（度）"); ax.set_ylabel("1℃あたりの日数（地点ごと）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("地点の緯度と気温への反応", loc="left", fontsize=11.5)
note(axes[0], SOURCE, -0.2)
fig.savefig(FIG / "s1_temp_sensitivity.png"); plt.close(fig)
