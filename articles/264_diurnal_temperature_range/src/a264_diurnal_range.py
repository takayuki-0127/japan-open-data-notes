"""264 1日の気温差（日較差＝日最高気温−日最低気温）は、小さくなっているのか"""
import json, numpy as np, pandas as pd
from common import *
df = load(); df["dtr"] = df.tmax - df.tmin
ok = complete_years(df, "dtr", 350)
SEAS = {12: "冬", 1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春", 6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋"}
df["seas"] = df.month.map(SEAS)
A = df.set_index(["station", "year"]).loc[lambda d: d.index.isin(ok)].reset_index()
Y = A.groupby(["station", "year"])[["tmax", "tmin", "dtr"]].mean().reset_index(); Y.to_csv(RES / "a264_annual.csv", index=False)
tab = []
for st in NAMES:
    g = Y[Y.station == st]; x = g.year.values.astype(float); r = dict(station=st, years=len(g))
    for c in ["tmax", "tmin", "dtr"]:
        b, se, _ = ols_trend(x, g[c].values); r[c + "_per100y"] = b * 100; r[c + "_se"] = se * 100
        b2, se2, _ = ols_trend(x[x >= 1961], g[c].values[x >= 1961]); r[c + "_1961_per100y"] = b2 * 100
    for a, c2 in PERIODS: r[f"dtr_{a}-{c2}"] = g[g.year.between(a, c2)].dtr.mean()
    S = A[A.station == st].groupby(["year", "seas"]).dtr.mean().unstack()
    for s in ["冬", "春", "夏", "秋"]: r["dtr_" + s + "_per100y"] = ols_trend(S.index.values.astype(float), S[s].values)[0] * 100
    tab.append(r)
tab = pd.DataFrame(tab); tab.to_csv(RES / "a264_station_trends.csv", index=False)
R = tab[tab.station.isin(RURAL)]
y = Y[Y.station.isin(RURAL)].copy()
for c in ["tmax", "tmin", "dtr"]:
    y[c + "_a"] = y.groupby("station")[c].transform(lambda s: s - s[y.loc[s.index, "year"].between(1961, 1990)].mean())
ser = y.groupby("year")[["tmax_a", "tmin_a", "dtr_a"]].mean(); ser.to_csv(RES / "a264_rural_anomaly.csv")
out = dict(stations=NAMES, rural=RURAL)
for c in ["tmax", "tmin", "dtr"]:
    b, se, _ = ols_trend(ser.index.values.astype(float), ser[c + "_a"].values); out[c + "_rural_per100y"] = b * 100; out[c + "_rural_se"] = se * 100
    b, se, _ = ols_trend(ser.index.values[ser.index >= 1961].astype(float), ser[c + "_a"].values[ser.index >= 1961]); out[c + "_rural_1961_per100y"] = b * 100; out[c + "_rural_1961_se"] = se * 100
    b, se, _ = ols_trend(ser.index.values[ser.index >= 1991].astype(float), ser[c + "_a"].values[ser.index >= 1991]); out[c + "_rural_1991_per100y"] = b * 100; out[c + "_rural_1991_se"] = se * 100
out.update(dict(n_dtr_down=int((R.dtr_per100y < 0).sum()), n=len(R), dtr_rural_median_per100y=float(R.dtr_per100y.median()),
    dtr_by_season_median={s: float(R["dtr_" + s + "_per100y"].median()) for s in ["冬", "春", "夏", "秋"]},
    tokyo=tab[tab.station == "東京"].iloc[0].to_dict(),
    dtr_period_mean_rural={f"{a}-{c}": float(R[f"dtr_{a}-{c}"].mean()) for a, c in PERIODS}))
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.axhline(0, color="#999", lw=0.8)
for c, col, lab in [("tmax_a", "#d6604d", "日最高気温"), ("tmin_a", "#4393c3", "日最低気温"), ("dtr_a", "#333333", "日較差（最高−最低）")]:
    ax.plot(ser.index, ser[c], color=col, lw=0.7, alpha=0.45); ax.plot(ser.index, ser[c].rolling(11, center=True, min_periods=6).mean(), color=col, lw=2.2, label=lab)
ax.set_ylabel("1961〜1990年平均からの差（℃）"); ax.set_title("最高・最低気温と日較差（13地点の平均、太線は11年移動平均）"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a264_anomaly.png"); plt.close(fig)
t = tab.sort_values("dtr_per100y"); fig, ax = plt.subplots(figsize=(7.5, 5))
yy = np.arange(len(t)); ax.barh(yy - 0.2, t.tmax_per100y, 0.4, color="#d6604d", label="最高気温"); ax.barh(yy + 0.2, t.tmin_per100y, 0.4, color="#4393c3", label="最低気温")
ax.scatter(t.dtr_per100y, yy, color="#111", zorder=3, s=22, label="日較差")
ax.set_yticks(yy, [s + ("（大都市）" if s == "東京" else "") for s in t.station]); ax.axvline(0, color="#333", lw=0.8)
ax.set_xlabel("100年あたりの変化（℃）、1931〜2025年"); ax.set_title("地点ごとの上がり方：最低気温のほうが大きいと日較差は縮む"); ax.legend(fontsize=8.5, loc="lower right"); ax.grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a264_station.png"); plt.close(fig)
ss = ["冬", "春", "夏", "秋"]; v = [R["dtr_" + s + "_per100y"].median() for s in ss]
fig, ax = plt.subplots(figsize=(6.5, 3.8)); ax.bar(ss, v, color=["#4393c3" if x < 0 else "#d6604d" for x in v]); ax.axhline(0, color="#333", lw=0.8)
for i, x in enumerate(v): ax.text(i, x + (0.03 if x >= 0 else -0.03), f"{x:+.2f}", ha="center", va="bottom" if x >= 0 else "top", fontsize=9)
ax.set_ylim(min(v) * 1.2, max(0.1, max(v) * 1.2)); ax.set_ylabel("日較差の100年あたりの変化（℃）"); ax.set_title("季節ごとの日較差の変化（13地点の中央値）"); ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a264_season.png"); plt.close(fig)
print(json.dumps({k: v for k, v in out.items() if k not in ("tokyo",)}, ensure_ascii=False, default=float))
print(tab[["station","years","tmax_per100y","tmin_per100y","dtr_per100y","dtr_se","dtr_1961_per100y"]].round(2).to_string())
