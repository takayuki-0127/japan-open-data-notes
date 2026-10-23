"""台風の強さと場所：最も発達したとき（最低気圧）の緯度の北上（Kossin型の検定）、急発達（24時間で30hPa以上の低下）、日本に最も近づいたときの気圧"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

d = load(); s = pd.read_csv(RES / "y1_storms.csv", index_col=0, dtype={"sid": str})
s.index = s.index.astype(str).str.zfill(4)
d = d[d.sid.isin(s.index)]
ts = d[d.grade.isin(TS_GRADES)]
# 最低気圧と、そのときの緯度（最低気圧に初めて達した時刻）
i = ts.sort_values(["sid", "pres", "time"]).groupby("sid").head(1).set_index("sid")
s["pmin"] = i.pres; s["lat_lmi"] = i.lat; s["lon_lmi"] = i.lon
# 急発達：元データの時刻で、24時間後の気圧が30hPa以上低い（TS以上の期間）
ri = []
for sid, g in ts.groupby("sid"):
    g = g.set_index("time").pres.sort_index(); g = g[~g.index.duplicated()]
    g24 = g.reindex(g.index + pd.Timedelta(hours=24)).values
    drop = g.values - g24
    ri.append((sid, np.nanmax(drop) if np.isfinite(drop).any() else np.nan))
ri = pd.Series(dict(ri)); s["max24drop"] = ri; s["RI"] = (s.max24drop >= 30).astype(int)
s.to_csv(RES / "y2_storms.csv", encoding="utf-8-sig")

strong = s[s.pmin <= 975]  # 強い台風に限る（風速の記録がない1977年より前とも比べられるよう気圧で定義）


def ols_trend(y, x, label, B=2000, seed=0):
    X = sm.add_constant((x - 2000) / 10)
    m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    # 年ごとのブートストラップ（年をまるごと復元抽出）
    rng = np.random.default_rng(seed); df = pd.DataFrame({"y": y, "x": x}); yrs = df.x.unique(); bs = []
    for _ in range(B):
        pick = rng.choice(yrs, len(yrs)); dd = pd.concat([df[df.x == k] for k in pick])
        bs.append(np.polyfit((dd.x - 2000) / 10, dd.y, 1)[0])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"series": label, "n": len(y), "period": f"{int(x.min())}-{int(x.max())}", "slope_per_decade": np.asarray(m.params)[1],
            "hac_lo": np.asarray(m.conf_int())[1, 0], "hac_hi": np.asarray(m.conf_int())[1, 1], "p": np.asarray(m.pvalues)[1], "boot_lo": lo, "boot_hi": hi}


R = []
for y0 in (1951, 1980):
    g = strong[strong.year >= y0]
    R.append(ols_trend(g.lat_lmi.values, g.year.values.astype(float), "最も発達したときの緯度（度、975hPa以下の台風）"))
    g2 = s[s.year >= y0]
    R.append(ols_trend(g2.lat_lmi.values, g2.year.values.astype(float), "最も発達したときの緯度（度、全台風）"))
    R.append(ols_trend(g2.pmin.values, g2.year.values.astype(float), "生涯の最低気圧（hPa、全台風）"))
    a = s[(s.year >= y0) & (s.approach == 1) & s.pres_at_closest.notna()]
    R.append(ols_trend(a.pres_at_closest.values, a.year.values.astype(float), "日本に最も近づいたときの気圧（hPa、接近した台風）"))
R = pd.DataFrame(R); R.to_csv(RES / "y2_trends.csv", index=False, encoding="utf-8-sig"); print(R.round(3).to_string())

# 年ごとの指標
yr = pd.DataFrame({"lat_lmi_strong": strong.groupby("year").lat_lmi.mean(), "n_strong": strong.groupby("year").size(),
                   "n_le930": s[s.pmin <= 930].groupby("year").size(), "n_RI": s.groupby("year").RI.sum(), "n": s.groupby("year").size(),
                   "app_pres_mean": s[s.approach == 1].groupby("year").pres_at_closest.mean(),
                   "app_le960": s[(s.approach == 1) & (s.pres_at_closest <= 960)].groupby("year").size()}).reindex(range(Y0, Y1 + 1))
yr[["n_strong", "n_le930", "n_RI", "app_le960"]] = yr[["n_strong", "n_le930", "n_RI", "app_le960"]].fillna(0)
yr["RI_share"] = yr.n_RI / yr.n
yr.index.name = "year"; yr.to_csv(RES / "y2_yearly.csv", encoding="utf-8-sig")

# 回数のトレンド（ポアソン、HAC）
C = []
for col in ["n_le930", "n_RI", "app_le960", "n_strong"]:
    for y0 in (1951, 1980):
        sub = yr.loc[y0:]; X = sm.add_constant((sub.index.values - 2000) / 10)
        m = sm.GLM(sub[col].values, X, family=sm.families.Poisson(), exposure=sub.n.values if col == "n_RI" else None).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        b, se = np.asarray(m.params)[1], np.asarray(m.bse)[1]
        C.append({"series": col, "period": f"{y0}-{Y1}", "pct_per_decade": (np.exp(b) - 1) * 100, "lo": (np.exp(b - 1.96 * se) - 1) * 100, "hi": (np.exp(b + 1.96 * se) - 1) * 100, "p": np.asarray(m.pvalues)[1]})
C = pd.DataFrame(C); C.to_csv(RES / "y2_count_trends.csv", index=False, encoding="utf-8-sig"); print(C.round(3).to_string())

per = {}
for a, b in [(1951, 1980), (1980, 2000), (1996, 2025)]:
    g = s[(s.year >= a) & (s.year <= b)]; n = b - a + 1
    per[f"{a}-{b}"] = {"lat_lmi_strong": g[g.pmin <= 975].lat_lmi.mean(), "pmin_median": g.pmin.median(), "le930_per_year": (g.pmin <= 930).sum() / n,
                       "RI_per_year": g.RI.sum() / n, "RI_share": g.RI.mean(), "app_pres_mean": g[g.approach == 1].pres_at_closest.mean(),
                       "app_le960_per_year": ((g.approach == 1) & (g.pres_at_closest <= 960)).sum() / n}
P = pd.DataFrame(per); P.to_csv(RES / "y2_period.csv", encoding="utf-8-sig"); print(P.round(3))

# 図1：最も発達したときの緯度
fig, ax = plt.subplots(figsize=(8.8, 4.2))
ax.scatter(strong.year, strong.lat_lmi, s=6, color=LIGHT, alpha=.7, label="1つ1つの台風")
ax.plot(yr.index, yr.lat_lmi_strong.rolling(11, center=True, min_periods=6).mean(), color=BLUE, lw=2.4, label="11年移動平均（975hPa以下）")
allm = s.groupby("year").lat_lmi.mean().reindex(yr.index)
ax.plot(yr.index, allm.rolling(11, center=True, min_periods=6).mean(), color=GREEN, lw=2.0, label="11年移動平均（全台風）")
r = R.iloc[0]; xx = np.array([1951, 2025]); g = strong
b = np.polyfit((g.year - 2000) / 10, g.lat_lmi, 1); ax.plot(xx, b[1] + b[0] * (xx - 2000) / 10, "--", color=ORANGE, lw=1.6, label=f"直線（10年で{r.slope_per_decade:+.2f}度）")
ax.set_ylabel("最も発達したときの北緯（度）"); ax.set_xlim(1950, 2026); ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2); ax.set_ylim(0, 58)
ax.set_title("台風が最も発達した場所の緯度（点と破線は最低気圧975hPa以下の台風）", loc="left", fontsize=12)
note(ax, SOURCE, -0.12); fig.savefig(FIG / "y2_lat_lmi.png"); plt.close(fig)

# 図2：強い台風と急発達の数
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, col, t, c in [(axes[0], "n_le930", "最低気圧930hPa以下まで発達した台風", PURPLE), (axes[1], "n_RI", "急発達（24時間で30hPa以上低下）した台風", ORANGE)]:
    ax.bar(yr.index, yr[col], color=c, alpha=.45); ax.plot(yr.index, yr[col].rolling(11, center=True).mean(), color=c, lw=2.2)
    ax.set_title(t, loc="left", fontsize=11); ax.set_xlim(1950, 2026)
axes[0].set_ylabel("1年あたりの個数（線は11年移動平均）")
note(axes[0], SOURCE, -0.14); fig.savefig(FIG / "y2_strong_ri.png"); plt.close(fig)

# 図3：日本に最も近づいたときの気圧
a = s[(s.approach == 1) & s.pres_at_closest.notna()]
fig, ax = plt.subplots(figsize=(8.8, 4.2))
ax.scatter(a.year, a.pres_at_closest, s=8, color=LIGHT, alpha=.8, label="接近した台風")
ax.plot(yr.index, yr.app_pres_mean.rolling(11, center=True, min_periods=6).mean(), color=BLUE, lw=2.4, label="年平均の11年移動平均")
ax.invert_yaxis(); ax.set_ylabel("最接近時の中心気圧（hPa、上ほど強い）"); ax.set_xlim(1950, 2026)
ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=2); ax.set_ylim(1022, 890)
ax.set_title("日本に近づいたときの台風の強さ", loc="left", fontsize=12)
note(ax, SOURCE + "\n最も近づいた時刻＝全国50か所の気象台のどれかとの距離が最も小さくなった時刻（300km以内に入った台風）", -0.12)
fig.savefig(FIG / "y2_approach_pres.png"); plt.close(fig)
