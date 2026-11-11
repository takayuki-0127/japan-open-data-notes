"""262 真夏日（日最高気温30℃以上）になる最初の日は、早くなったのか"""
import json, numpy as np, pandas as pd
from common import *
df = load(); df["doy"] = df.date.dt.dayofyear
ok = complete_years(df, "tmax")
def firsts(th):
    rows = []
    for (st, y), g in df.groupby(["station", "year"]):
        if (st, y) not in ok: continue
        h = g[g.tmax >= th]
        rows.append(dict(station=st, year=y, first=h.doy.min() if len(h) else np.nan, last=h.doy.max() if len(h) else np.nan, n=len(h)))
    return pd.DataFrame(rows)
f30 = firsts(30.0); f25 = firsts(25.0)
f30.to_csv(RES / "a262_first_last_30.csv", index=False)
out = {"stations": NAMES, "years": [1931, 2025]}
tab = []
for st in NAMES:
    g = f30[f30.station == st]; g2 = f25[f25.station == st]
    b, se, n = ols_trend(g.year.values.astype(float), g["first"].values)
    bl, sel, _ = ols_trend(g.year.values.astype(float), g["last"].values)
    p = {f"{a}-{b_}": g[(g.year >= a) & (g.year <= b_)]["first"].mean() for a, b_ in PERIODS}
    tab.append(dict(station=st, first_trend_per10y=b * 10, se=se * 10, n=n, last_trend_per10y=bl * 10,
                    theil_per10y=theil_sen(g.year.values.astype(float), g["first"].values) * 10,
                    first25_trend_per10y=ols_trend(g2.year.values.astype(float), g2["first"].values)[0] * 10,
                    none_years=int(g["first"].isna().sum()), **{"first_" + k: v for k, v in p.items()},
                    n30_1931_60=g[(g.year <= 1960)].n.mean(), n30_1996_2025=g[g.year >= 1996].n.mean()))
tab = pd.DataFrame(tab); tab.to_csv(RES / "a262_station_trends.csv", index=False)
# 真夏日がない年が多い地点（95年中6年以上）は、最初の日が「暑い年だけ」の値になるので平均から外す
MAIN = [s for s in RURAL if int(tab.loc[tab.station == s, "none_years"].iloc[0]) <= 5]
NORTH = [s for s in RURAL if s not in MAIN]
rur = tab[tab.station.isin(MAIN)]
# 13地点平均の「年ごとの偏差」（地点ごとに1961〜1990年平均からの差）
f = f30[f30.station.isin(MAIN)].copy()
f["anom"] = f.groupby("station")["first"].transform(lambda s: s - s[f.loc[s.index, "year"].between(1961, 1990)].mean())
f["anom_last"] = f.groupby("station")["last"].transform(lambda s: s - s[f.loc[s.index, "year"].between(1961, 1990)].mean())
ser = f.groupby("year")[["anom", "anom_last"]].mean(); ser.to_csv(RES / "a262_rural_anomaly.csv")
b, se, _ = ols_trend(ser.index.values.astype(float), ser.anom.values)
bl, sel, _ = ols_trend(ser.index.values.astype(float), ser.anom_last.values)
b61, se61, _ = ols_trend(ser.index.values[ser.index >= 1961].astype(float), ser.anom.values[ser.index >= 1961])
d_first = (rur["first_1996-2025"] - rur["first_1931-1960"]); d_last = []
for st in MAIN:
    g = f30[f30.station == st]; d_last.append(g[g.year >= 1996]["last"].mean() - g[g.year <= 1960]["last"].mean())
out.update(dict(
    rural_first_trend_per10y=b * 10, rural_first_se=se * 10, rural_last_trend_per10y=bl * 10, rural_last_se=sel * 10,
    rural_first_trend_1961_per10y=b61 * 10, rural_first_trend_1961_se=se61 * 10,
    rural_first_change_days_median=float(d_first.median()), rural_first_change_days_mean=float(d_first.mean()),
    rural_last_change_days_median=float(np.median(d_last)), rural_last_change_days_mean=float(np.mean(d_last)),
    n_earlier=int((d_first < 0).sum()), n_station=int(d_first.notna().sum()),
    stations_first_trend_sig_neg=int(((rur.first_trend_per10y + 1.96 * rur.se) < 0).sum()),
    tokyo=tab[tab.station == "東京"].iloc[0].to_dict(),
    first25_rural_median_per10y=float(rur.first25_trend_per10y.median()),
    theil_rural_median_per10y=float(rur.theil_per10y.median()),
    n30_rural_1931_60=float(rur.n30_1931_60.mean()), n30_rural_1996_2025=float(rur.n30_1996_2025.mean()),
    main_stations=MAIN, north_stations=NORTH,
    north_none=[{"station": st, "none_1931_60": int(f30[(f30.station == st) & (f30.year <= 1960)]["first"].isna().sum()), "none_1996_2025": int(f30[(f30.station == st) & (f30.year >= 1996)]["first"].isna().sum())} for st in NORTH],
    excluded_station_years=int(df.groupby(["station","year"]).ngroups - len(ok)),
))
# 期間平均の日付
for a, c in PERIODS:
    out[f"mean_first_{a}_{c}"] = {st: md_label(v, 1) for st, v in zip(tab.station, tab[f"first_{a}-{c}"]) if not np.isnan(v)}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
# 図1：13地点平均の偏差
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.axhline(0, color="#999", lw=0.8)
ax.plot(ser.index, ser.anom, color="#c0392b", lw=0.8, alpha=0.5, label="最初の真夏日")
ax.plot(ser.index, ser.anom.rolling(11, center=True, min_periods=6).mean(), color="#c0392b", lw=2.2)
ax.plot(ser.index, ser.anom_last, color="#2c7fb8", lw=0.8, alpha=0.5, label="最後の真夏日")
ax.plot(ser.index, ser.anom_last.rolling(11, center=True, min_periods=6).mean(), color="#2c7fb8", lw=2.2)
ax.set_ylabel("1961〜1990年平均からの差（日）\n下ほど早い")
ax.set_title("最初と最後の真夏日（10地点の平均、太線は11年移動平均）")
ax.legend(loc="lower left", fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a262_anomaly.png"); plt.close(fig)
# 図2：地点ごとの変化（1931〜60 → 1996〜2025）
t = tab.copy(); t["chg"] = t["first_1996-2025"] - t["first_1931-1960"]; t = t.sort_values("chg")
fig, ax = plt.subplots(figsize=(7.5, 5))
ax.barh(t.station, t.chg, color=["#7f7f7f" if s == "東京" else ("#f1a9a0" if s in NORTH else "#c0392b") for s in t.station]); ax.set_xlim(t.chg.min() * 1.18, max(1, t.chg.max() * 1.2))
ax.axvline(0, color="#333", lw=0.8)
for y_, v in enumerate(t.chg): ax.text(v - 0.5 if v < 0 else v + 0.5, y_, f"{v:+.0f}日", va="center", ha="right" if v < 0 else "left", fontsize=8.5)
ax.set_xlabel("最初の真夏日の変化（日）：1931〜1960年平均 → 1996〜2025年平均")
ax.set_title("地点ごとの変化（灰色は大都市の東京、薄い色は真夏日のない年が多い北の3地点）", fontsize=10)
ax.grid(axis="x", alpha=0.3); fig.tight_layout(); fig.savefig(FIG / "a262_station_change.png"); plt.close(fig)
# 図3：真夏日の季節の長さ（最後−最初）と日数
f["len"] = f["last"] - f["first"]
s2 = f.groupby("year")["len"].mean(); n2 = f30[f30.station.isin(MAIN)].groupby("year").n.mean()
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(n2.index, n2.values, color="#f4a582", width=0.9, label="真夏日の日数（10地点平均）")
ax.plot(n2.index, n2.rolling(11, center=True, min_periods=6).mean(), color="#b2182b", lw=2)
ax.set_ylabel("日"); ax.set_title("真夏日の日数（10地点平均、線は11年移動平均）"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a262_days.png"); plt.close(fig)
print(json.dumps({k: v for k, v in out.items() if not isinstance(v, dict)}, ensure_ascii=False, indent=0, default=float))
print(tab[["station","first_trend_per10y","se","last_trend_per10y","first_1931-1960","first_1996-2025","none_years"]].round(2).to_string())
