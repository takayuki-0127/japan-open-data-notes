"""266 初霜の日は、どれだけ遅くなったのか（日ごとの表で毎年そろえて作れる「最低気温が0℃を下回る最初の日（初冬日）」で見る）"""
import json, numpy as np, pandas as pd
from common import *
df = load(); df["sdoy"], df["season"] = doy_from(df.date, 8)
df = df[(df.season >= 1931) & (df.season <= 2024)]
cov = df.groupby(["station", "season"]).tmin.apply(lambda s: s.notna().mean()); ok = cov[cov >= 0.95].index
rows = []
for (st, y), g in df.groupby(["station", "season"]):
    if (st, y) not in ok: continue
    r = dict(station=st, season=y)
    for lab, th in [("lt0", 0.0), ("le2", 2.0), ("le4", 4.0)]:
        h = g[(g.tmin < th) if lab == "lt0" else (g.tmin <= th)]
        r["first_" + lab] = h.sdoy.min() if len(h) else np.nan; r["last_" + lab] = h.sdoy.max() if len(h) else np.nan; r["n_" + lab] = len(h)
    rows.append(r)
F = pd.DataFrame(rows); F["free_lt0"] = F.first_lt0 - F.groupby("station").last_lt0.shift(1)   # 前の冬の最後の冬日から今年の最初の冬日まで（冬日のない期間）
F.to_csv(RES / "a266_first_last.csv", index=False)
tab = []
for st in NAMES:
    g = F[F.station == st]; x = g.season.values.astype(float); r = dict(station=st, seasons=len(g), none=int(g.first_lt0.isna().sum()))
    for c in ["first_lt0", "last_lt0", "n_lt0", "first_le2", "first_le4", "free_lt0"]:
        b, se, _ = ols_trend(x, g[c].values.astype(float)); r[c + "_per10y"] = b * 10; r[c + "_se"] = se * 10
    r["theil_first_per10y"] = theil_sen(x, g.first_lt0.values) * 10
    for a, c2 in [(1931, 1960), (1961, 1990), (1995, 2024)]:
        q = g[g.season.between(a, c2)]; r[f"first_{a}-{c2}"] = q.first_lt0.mean(); r[f"last_{a}-{c2}"] = q.last_lt0.mean(); r[f"n_{a}-{c2}"] = q.n_lt0.mean(); r[f"none_{a}-{c2}"] = int(q.first_lt0.isna().sum())
    tab.append(r)
tab = pd.DataFrame(tab); tab.to_csv(RES / "a266_station_trends.csv", index=False)
MAIN = tab[tab.station.isin(RURAL) & (tab.none <= 5)].station.tolist(); WARM = [s for s in NAMES if s not in MAIN]
m = tab[tab.station.isin(MAIN)].copy(); m["chg_first"] = m["first_1995-2024"] - m["first_1931-1960"]; m["chg_last"] = m["last_1995-2024"] - m["last_1931-1960"]
f = F[F.station.isin(MAIN)].copy()
for c in ["first_lt0", "last_lt0"]:
    f[c + "_a"] = f.groupby("station")[c].transform(lambda s: s - s[f.loc[s.index, "season"].between(1961, 1990)].mean())
ser = f.groupby("season")[["first_lt0_a", "last_lt0_a"]].mean(); ser.to_csv(RES / "a266_main_anomaly.csv")
out = dict(main_stations=MAIN, other_stations=WARM)
for c in ["first_lt0_a", "last_lt0_a"]:
    b, se, _ = ols_trend(ser.index.values.astype(float), ser[c].values); out[c + "_per10y"] = b * 10; out[c + "_se"] = se * 10
    b, se, _ = ols_trend(ser.index.values[ser.index >= 1961].astype(float), ser[c].values[ser.index >= 1961]); out[c + "_1961_per10y"] = b * 10; out[c + "_1961_se"] = se * 10
out.update(dict(chg_first_median=float(m.chg_first.median()), chg_first_mean=float(m.chg_first.mean()), chg_last_median=float(m.chg_last.median()), chg_last_mean=float(m.chg_last.mean()),
    n_later=int((m.chg_first > 0).sum()), n_last_earlier=int((m.chg_last < 0).sum()), n=len(m), sig_later=int(((m.first_lt0_per10y - 1.96 * m.first_lt0_se) > 0).sum()),
    le2_median_per10y=float(m.first_le2_per10y.median()), le4_median_per10y=float(m.first_le4_per10y.median()), theil_median_per10y=float(m.theil_first_per10y.median()),
    first_lt0_median_per10y=float(m.first_lt0_per10y.median()),
    days_lt0_change=dict(zip(m.station, (m["n_1995-2024"] - m["n_1931-1960"]).round(1))),
    dates_1931_60={s: md_label(v, 8) for s, v in zip(m.station, m["first_1931-1960"])}, dates_1995_2024={s: md_label(v, 8) for s, v in zip(m.station, m["first_1995-2024"])},
    others=tab[tab.station.isin(WARM)][["station", "none_1931-1960", "none_1995-2024", "first_1931-1960", "first_1995-2024"]].to_dict("records")))
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.axhline(0, color="#999", lw=0.8)
ax.plot(ser.index, ser.first_lt0_a, color="#2c7fb8", lw=0.8, alpha=0.5, label="最初の冬日（秋）"); ax.plot(ser.index, ser.first_lt0_a.rolling(11, center=True, min_periods=6).mean(), color="#2c7fb8", lw=2.2)
ax.plot(ser.index, ser.last_lt0_a, color="#1a9850", lw=0.8, alpha=0.5, label="最後の冬日（春）"); ax.plot(ser.index, ser.last_lt0_a.rolling(11, center=True, min_periods=6).mean(), color="#1a9850", lw=2.2)
ax.set_ylabel("1961〜1990年平均からの差（日）\n上ほど遅い"); ax.set_xlabel("寒候年（その年の8月〜翌年7月）")
ax.set_title(f"最低気温が0℃未満になる最初と最後の日（{len(MAIN)}地点の平均、太線は11年移動平均）", fontsize=10.5); ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a266_anomaly.png"); plt.close(fig)
t = m.sort_values("chg_first"); yy = np.arange(len(t)); fig, ax = plt.subplots(figsize=(7.5, 5))
ax.barh(yy - 0.2, t.chg_first, 0.4, color="#2c7fb8", label="最初の冬日（プラス＝遅く）"); ax.barh(yy + 0.2, t.chg_last, 0.4, color="#1a9850", label="最後の冬日（マイナス＝早く）")
ax.set_yticks(yy, t.station); ax.axvline(0, color="#333", lw=0.8); ax.legend(fontsize=8.5, loc="lower right")
ax.set_xlabel("変化（日）：1931〜1960年平均 → 1995〜2024年平均"); ax.set_title("地点ごとの変化"); ax.grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a266_station.png"); plt.close(fig)
th = [("0℃未満", "first_lt0_per10y"), ("2℃以下", "first_le2_per10y"), ("4℃以下", "first_le4_per10y")]
v = [m[c].median() for _, c in th]; fig, ax = plt.subplots(figsize=(6.5, 3.8)); ax.bar([a for a, _ in th], v, color="#2c7fb8")
for i, x in enumerate(v): ax.text(i, x + 0.05, f"{x:+.1f}日", ha="center", fontsize=9)
ax.set_ylim(0, max(v) * 1.2); ax.set_ylabel("10年あたり遅くなった日数"); ax.set_title(f"最低気温の線を変えても遅くなった（{len(MAIN)}地点の中央値）"); ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a266_threshold.png"); plt.close(fig)
print(json.dumps(out, ensure_ascii=False, default=float))
print(tab[["station","seasons","none","first_lt0_per10y","first_lt0_se","last_lt0_per10y","first_1931-1960","first_1995-2024"]].round(2).to_string())
