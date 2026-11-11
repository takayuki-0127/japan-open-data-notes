"""265 雨の降る日は減り、1回の雨は強くなったのか（年降水量＝降水日数×1日あたりの雨量に分ける）"""
import json, numpy as np, pandas as pd
from common import *
df = load()
ok = complete_years(df, "prec", 360)
A = df.set_index(["station", "year"]).loc[lambda d: d.index.isin(ok)].reset_index()
def agg(g, th=1.0):
    w = g.prec >= th
    return pd.Series(dict(total=g.prec.sum(), wet=w.sum(), sdii=g.prec[w].sum() / max(w.sum(), 1), d50=(g.prec >= 50).sum(), d100=(g.prec >= 100).sum(),
                          wet05=(g.prec >= 0.5).sum(), wet10=(g.prec >= 10).sum(), p_top=np.nan))
Y = A.groupby(["station", "year"]).apply(agg).reset_index()
Y["sdii05"] = A.groupby(["station", "year"]).apply(lambda g: g.prec[g.prec >= 0.5].sum() / max((g.prec >= 0.5).sum(), 1)).values
Y = Y.drop(columns="p_top"); Y.to_csv(RES / "a265_annual.csv", index=False)
tab = []
for st in NAMES:
    g = Y[Y.station == st]; x = g.year.values.astype(float); r = dict(station=st, years=len(g))
    for c in ["total", "wet", "sdii", "d50", "wet05", "sdii05", "wet10"]:
        b, se, _ = ols_trend(x, g[c].values.astype(float)); r[c + "_per100y"] = b * 100; r[c + "_se"] = se * 100
    for a, c2 in PERIODS:
        q = g[g.year.between(a, c2)]; r[f"total_{a}-{c2}"] = q.total.mean(); r[f"wet_{a}-{c2}"] = q.wet.mean(); r[f"sdii_{a}-{c2}"] = q.sdii.mean(); r[f"d50_{a}-{c2}"] = q.d50.mean()
    tab.append(r)
tab = pd.DataFrame(tab); tab.to_csv(RES / "a265_station_trends.csv", index=False)
R = tab[tab.station.isin(RURAL)].copy()
# 分解：log(年降水量) の変化 = log(降水日数) の変化 + log(1日あたり雨量) の変化（1931〜1960 → 1996〜2025、地点平均）
R["dlog_total"] = np.log(R["total_1996-2025"] / R["total_1931-1960"]); R["dlog_wet"] = np.log(R["wet_1996-2025"] / R["wet_1931-1960"])
R["dlog_sdii"] = R.dlog_total - R.dlog_wet
y = Y[Y.station.isin(RURAL)].copy()
for c in ["total", "wet", "sdii", "d50"]:
    base = y[y.year.between(1961, 1990)].groupby("station")[c].mean(); y[c + "_r"] = y[c] / y.station.map(base) * 100
ser = y.groupby("year")[["total_r", "wet_r", "sdii_r", "d50_r"]].mean(); ser.to_csv(RES / "a265_rural_index.csv")
out = dict(stations=NAMES, rural=RURAL)
for c in ["total_r", "wet_r", "sdii_r", "d50_r"]:
    b, se, _ = ols_trend(ser.index.values.astype(float), ser[c].values); out[c + "_per100y"] = b * 100; out[c + "_se"] = se * 100
    b, se, _ = ols_trend(ser.index.values[ser.index >= 1961].astype(float), ser[c].values[ser.index >= 1961]); out[c + "_1961_per100y"] = b * 100; out[c + "_1961_se"] = se * 100
out.update(dict(
    pct_change_mean=dict(total=float((np.exp(R.dlog_total.mean()) - 1) * 100), wet=float((np.exp(R.dlog_wet.mean()) - 1) * 100), sdii=float((np.exp(R.dlog_sdii.mean()) - 1) * 100)),
    n_wet_down=int((R["wet_1996-2025"] < R["wet_1931-1960"]).sum()), n_sdii_up=int((R["sdii_1996-2025"] > R["sdii_1931-1960"]).sum()),
    n_total_up=int((R["total_1996-2025"] > R["total_1931-1960"]).sum()), n=len(R),
    wet_mean={k: float(R[f"wet_{k}"].mean()) for k in ["1931-1960", "1961-1990", "1996-2025"]},
    sdii_mean={k: float(R[f"sdii_{k}"].mean()) for k in ["1931-1960", "1961-1990", "1996-2025"]},
    total_mean={k: float(R[f"total_{k}"].mean()) for k in ["1931-1960", "1961-1990", "1996-2025"]},
    d50_mean={k: float(R[f"d50_{k}"].mean()) for k in ["1931-1960", "1961-1990", "1996-2025"]},
    wet05_median_per100y=float(R.wet05_per100y.median()), sdii05_median_per100y=float(R.sdii05_per100y.median()), wet10_median_per100y=float(R.wet10_per100y.median()),
    tokyo=tab[tab.station == "東京"].iloc[0].to_dict()))
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
R[["station", "dlog_total", "dlog_wet", "dlog_sdii"]].to_csv(RES / "a265_decomposition.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 4.2)); ax.axhline(100, color="#999", lw=0.8)
for c, col, lab in [("wet_r", "#4393c3", "降水日数（1mm以上）"), ("sdii_r", "#d6604d", "1日あたりの雨量（降った日の平均）"), ("total_r", "#333", "年降水量")]:
    ax.plot(ser.index, ser[c], color=col, lw=0.7, alpha=0.4); ax.plot(ser.index, ser[c].rolling(11, center=True, min_periods=6).mean(), color=col, lw=2.2, label=lab)
ax.set_ylabel("1961〜1990年平均＝100"); ax.set_title("降水日数と1日あたりの雨量（13地点の平均、太線は11年移動平均）"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a265_index.png"); plt.close(fig)
t = R.sort_values("dlog_wet"); yy = np.arange(len(t)); fig, ax = plt.subplots(figsize=(7.5, 5))
ax.barh(yy - 0.2, (np.exp(t.dlog_wet) - 1) * 100, 0.4, color="#4393c3", label="降水日数"); ax.barh(yy + 0.2, (np.exp(t.dlog_sdii) - 1) * 100, 0.4, color="#d6604d", label="1日あたりの雨量")
ax.scatter((np.exp(t.dlog_total) - 1) * 100, yy, color="#111", s=22, zorder=3, label="年降水量"); ax.set_yticks(yy, t.station); ax.axvline(0, color="#333", lw=0.8)
ax.set_xlabel("変化（%）：1931〜1960年平均 → 1996〜2025年平均"); ax.set_title("地点ごとの分解：日数が減り、1日の雨量が増えた"); ax.legend(fontsize=8.5, loc="lower right"); ax.grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a265_station.png"); plt.close(fig)
fig, ax = plt.subplots(figsize=(8, 3.8)); d = y.groupby("year").d50.mean()
ax.bar(d.index, d.values, color="#fdae61", width=0.9); ax.plot(d.index, d.rolling(11, center=True, min_periods=6).mean(), color="#b2182b", lw=2)
ax.set_ylabel("日"); ax.set_title("1日に50mm以上降った日数（13地点平均、線は11年移動平均）"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "a265_d50.png"); plt.close(fig)
print(json.dumps({k: v for k, v in out.items() if k != "tokyo"}, ensure_ascii=False, default=float))
print(tab[["station","years","total_per100y","wet_per100y","wet_se","sdii_per100y","sdii_se","d50_per100y"]].round(2).to_string())
