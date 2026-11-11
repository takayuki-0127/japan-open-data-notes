"""263 初雪の日は、どれだけ遅くなったのか（日ごとの表で毎年そろえて作れる「初めて雪が1cm以上積もった日」で見る）"""
import json, numpy as np, pandas as pd
from common import *
df = load()
df["sdoy"], df["season"] = doy_from(df.date, 8)          # 8月1日を1日目とする寒候年（2024 = 2024年8月〜2025年7月）
df = df[(df.season >= 1931) & (df.season <= 2024)]
cov = df.groupby(["station", "season"]).snowdepth.apply(lambda s: s.notna().mean())
ok = cov[cov >= 0.95].index
rows = []
for (st, y), g in df.groupby(["station", "season"]):
    if (st, y) not in ok: continue
    s1 = g[g.snowdepth >= 1]; s5 = g[g.snowdepth >= 5]
    rows.append(dict(station=st, season=y, first=s1.sdoy.min() if len(s1) else np.nan, last=s1.sdoy.max() if len(s1) else np.nan,
                     first5=s5.sdoy.min() if len(s5) else np.nan, days=len(s1),
                     first_fall=g[g.snowfall >= 1].sdoy.min() if (g.snowfall >= 1).any() else np.nan))
F = pd.DataFrame(rows); F.to_csv(RES / "a263_first_snow_cover.csv", index=False)
tab = []
for st in NAMES:
    g = F[F.station == st]
    if len(g) < 60: tab.append(dict(station=st, seasons=len(g))); continue
    b, se, n = ols_trend(g.season.values.astype(float), g["first"].values)
    tab.append(dict(station=st, seasons=len(g), none=int(g["first"].isna().sum()), first_trend_per10y=b * 10, se=se * 10,
                    last_trend_per10y=ols_trend(g.season.values.astype(float), g["last"].values)[0] * 10,
                    first5_trend_per10y=ols_trend(g.season.values.astype(float), g["first5"].values)[0] * 10,
                    days_trend_per10y=ols_trend(g.season.values.astype(float), g["days"].values.astype(float))[0] * 10,
                    theil_per10y=theil_sen(g.season.values.astype(float), g["first"].values) * 10,
                    **{f"first_{a}-{c}": g[g.season.between(a, c)]["first"].mean() for a, c in [(1931, 1960), (1961, 1990), (1995, 2024)]},
                    **{f"days_{a}-{c}": g[g.season.between(a, c)]["days"].mean() for a, c in [(1931, 1960), (1995, 2024)]},
                    **{f"none_{a}-{c}": int(g[g.season.between(a, c)]["first"].isna().sum()) for a, c in [(1931, 1960), (1995, 2024)]}))
tab = pd.DataFrame(tab); tab.to_csv(RES / "a263_station_trends.csv", index=False)
MAIN = tab[(tab.seasons >= 90) & (tab.none <= 5)].station.tolist()
WARM = tab[(tab.seasons >= 90) & (tab.none > 5)].station.tolist()
m = tab[tab.station.isin(MAIN)].copy(); m["chg"] = m["first_1995-2024"] - m["first_1931-1960"]
f = F[F.station.isin(MAIN)].copy()
f["anom"] = f.groupby("station")["first"].transform(lambda s: s - s[f.loc[s.index, "season"].between(1961, 1990)].mean())
f["anom_last"] = f.groupby("station")["last"].transform(lambda s: s - s[f.loc[s.index, "season"].between(1961, 1990)].mean())
ser = f.groupby("season")[["anom", "anom_last"]].mean(); ser.to_csv(RES / "a263_main_anomaly.csv")
b, se, _ = ols_trend(ser.index.values.astype(float), ser.anom.values)
bl, sel, _ = ols_trend(ser.index.values.astype(float), ser.anom_last.values)
b61, se61, _ = ols_trend(ser.index.values[ser.index >= 1961].astype(float), ser.anom.values[ser.index >= 1961])
out = dict(main_stations=MAIN, warm_stations=WARM, no_record=tab[tab.seasons < 90].station.tolist(),
           first_trend_per10y=b * 10, first_se=se * 10, last_trend_per10y=bl * 10, last_se=sel * 10,
           first_trend_1961_per10y=b61 * 10, first_trend_1961_se=se61 * 10,
           chg_median=float(m.chg.median()), chg_mean=float(m.chg.mean()), n_later=int((m.chg > 0).sum()), n=len(m),
           sig_later=int(((m.first_trend_per10y - 1.96 * m.se) > 0).sum()),
           first5_median_per10y=float(m.first5_trend_per10y.median()), theil_median_per10y=float(m.theil_per10y.median()),
           days_change=dict(zip(m.station, (m["days_1995-2024"] - m["days_1931-1960"]).round(1))),
           warm=tab[tab.station.isin(WARM)][["station", "none_1931-1960", "none_1995-2024"]].to_dict("records"),
           dates_1931_60={s: md_label(v, 8) for s, v in zip(m.station, m["first_1931-1960"])},
           dates_1995_2024={s: md_label(v, 8) for s, v in zip(m.station, m["first_1995-2024"])})
# 「降雪の深さ1cm以上」の最初の日（1953年ごろから）との比較：同じ地点・同じ年でどれだけ違うか
both = F[F.station.isin(MAIN)].dropna(subset=["first", "first_fall"])
out["fall_vs_cover_median_diff_days"] = float((both["first"] - both["first_fall"]).median()); out["fall_vs_cover_n"] = len(both)
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.axhline(0, color="#999", lw=0.8)
ax.plot(ser.index, ser.anom, color="#2c7fb8", lw=0.8, alpha=0.5, label="初めて1cm積もった日")
ax.plot(ser.index, ser.anom.rolling(11, center=True, min_periods=6).mean(), color="#2c7fb8", lw=2.2)
ax.plot(ser.index, ser.anom_last, color="#7b3294", lw=0.8, alpha=0.5, label="最後に1cm積もっていた日")
ax.plot(ser.index, ser.anom_last.rolling(11, center=True, min_periods=6).mean(), color="#7b3294", lw=2.2)
ax.set_ylabel("1961〜1990年平均からの差（日）\n上ほど遅い"); ax.set_xlabel("寒候年（その年の8月〜翌年7月）")
ax.set_title(f"雪が積もる最初の日と最後の日（{len(MAIN)}地点の平均、太線は11年移動平均）"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a263_anomaly.png"); plt.close(fig)
t = m.sort_values("chg"); fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.barh(t.station, t.chg, color=["#7f7f7f" if s == "東京" else "#2c7fb8" for s in t.station]); ax.axvline(0, color="#333", lw=0.8); ax.set_xlim(min(-1.5, t.chg.min() * 1.3), t.chg.max() * 1.18)
for y_, v in enumerate(t.chg): ax.text(v + 0.4 if v >= 0 else v - 0.4, y_, f"{v:+.1f}日", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
ax.set_xlabel("初めて1cm積もった日の変化（日）：1931〜1960年平均 → 1995〜2024年平均"); ax.set_title("地点ごとの変化（プラスは遅くなった）")
ax.grid(axis="x", alpha=0.3); fig.tight_layout(); fig.savefig(FIG / "a263_station_change.png"); plt.close(fig)
d = F[F.station.isin(MAIN)].groupby("season").days.mean()
fig, ax = plt.subplots(figsize=(8, 4)); ax.bar(d.index, d.values, color="#9ecae1", width=0.9)
ax.plot(d.index, d.rolling(11, center=True, min_periods=6).mean(), color="#08519c", lw=2)
ax.set_ylabel("日"); ax.set_xlabel("寒候年"); ax.set_title(f"雪が1cm以上積もっていた日数（{len(MAIN)}地点平均、線は11年移動平均）"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a263_days.png"); plt.close(fig)
print(json.dumps(out, ensure_ascii=False, default=float)); print(tab.round(2).to_string())
