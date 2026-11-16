"""紅葉（黄葉）から落葉までの期間の変化。地点ごとの Theil–Sen の傾き、期間の平均の差、固定効果の回帰。仮説・頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
p = pd.read_csv(ROOT / "data" / "phenology.csv")


def panel(sp, drop_sub=False, y0=None):
    q = p[p.item.isin([f"{sp}_color", f"{sp}_fall"])]
    if drop_sub:
        q = q[~q.mark.isin([6, 7])]
    w = q.pivot_table(index=["station", "name", "year"], columns="item", values="doy").reset_index()
    w = w.dropna(subset=[f"{sp}_color", f"{sp}_fall"])
    w["span"] = w[f"{sp}_fall"] - w[f"{sp}_color"]
    w = w[w.span >= 0]  # 落葉が紅葉より前の記録（ありえない並び）は除く
    if y0:
        w = w[w.year >= y0]
    return w.rename(columns={f"{sp}_color": "color", f"{sp}_fall": "fall"})


def slopes(w, col, min_n=20):
    out = []
    for st, g in w.groupby("station", sort=True):
        g = g.dropna(subset=[col])
        if len(g) >= min_n:
            s = stats.theilslopes(g[col], g.year)[0] * 10
            out.append({"station": st, "name": g.name.iloc[0], "n": len(g), "slope_per_decade": s, "mean_color": g.color.mean()})
    return pd.DataFrame(out)


def period_diff(w, col):
    a = w[(w.year >= 1961) & (w.year <= 1990)].groupby("station")[col].agg(["mean", "size"])
    b = w[(w.year >= 1996) & (w.year <= 2025)].groupby("station")[col].agg(["mean", "size"])
    m = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    m = m[(m.size_a >= 10) & (m.size_b >= 10)]
    return float((m.mean_b - m.mean_a).median()), int(len(m))


def fe(w, col):
    f = smf.ols(f"{col} ~ year + C(station)", w).fit(cov_type="cluster", cov_kwds={"groups": w.year})
    return float(f.params["year"] * 10), float(f.bse["year"] * 10)


res = {}
for sp in ["kaede", "ichou"]:
    w = panel(sp)
    w.to_csv(R / f"panel_{sp}.csv", index=False)
    S = {c: slopes(w, c) for c in ["color", "fall", "span"]}
    S["span"].round(3).to_csv(R / f"station_span_slopes_{sp}.csv", index=False)
    d, nd = period_diff(w, "span")
    res[sp] = {
        "n_obs": int(len(w)), "n_stations_slope": int(len(S["span"])),
        "median_slope": {c: round(float(S[c].slope_per_decade.median()), 2) for c in S},
        "share_negative_span_slope_pct": round(float((S["span"].slope_per_decade < 0).mean() * 100), 1),
        "period_diff_span_days": round(d, 1), "period_diff_n": nd,
        "period_diff_color_days": round(period_diff(w, "color")[0], 1), "period_diff_fall_days": round(period_diff(w, "fall")[0], 1),
        "fe_span_per_decade": [round(x, 2) for x in fe(w, "span")],
        "mean_span_1961_1990": round(float(w[(w.year >= 1961) & (w.year <= 1990)].span.mean()), 1),
        "mean_span_1996_2025": round(float(w[(w.year >= 1996) & (w.year <= 2025)].span.mean()), 1),
    }
    # 全地点の平均の年ごとの値（図用）：地点の平均を引いた偏差の年平均
    w["span_dev"] = w.span - w.groupby("station").span.transform("mean")
    w["color_dev"] = w.color - w.groupby("station").color.transform("mean")
    w["fall_dev"] = w.fall - w.groupby("station").fall.transform("mean")
    w.groupby("year")[["color_dev", "fall_dev", "span_dev"]].mean().join(w.groupby("year").size().rename("n_stations")).round(3).to_csv(R / f"yearly_dev_{sp}.csv")

rob = []
for sp in ["kaede", "ichou"]:
    for name, w, mn in [("本線：全地点（20年以上）", panel(sp), 20), ("代わりの種目の値を除く", panel(sp, drop_sub=True), 20),
                        ("1981年以降", panel(sp, y0=1981), 20), ("30年以上の地点だけ", panel(sp), 30)]:
        s = slopes(w, "span", mn)
        fb, fs = fe(w, "span")
        rob.append({"species": sp, "check": name, "n_stations": len(s), "median_span_slope": round(float(s.slope_per_decade.median()), 2),
                    "share_negative_pct": round(float((s.slope_per_decade < 0).mean() * 100), 1), "fe_slope": round(fb, 2), "fe_se": round(fs, 2)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

k, i = res["kaede"], res["ichou"]
main = {"kaede": k, "ichou": i, "hypotheses": {
    "H1_kaede_span_slope_le_-0.5": {"value": k["median_slope"]["span"], "result": "支持" if k["median_slope"]["span"] <= -0.5 else "外れ"},
    "H2_ichou_span_slope_le_-0.5": {"value": i["median_slope"]["span"], "result": "支持" if i["median_slope"]["span"] <= -0.5 else "外れ"},
    "H3_kaede_period_diff_le_-3": {"value": k["period_diff_span_days"], "result": "支持" if k["period_diff_span_days"] <= -3 else "外れ"},
    "H4_kaede_fall_slope_ge_1.5": {"value": k["median_slope"]["fall"], "result": "支持" if k["median_slope"]["fall"] >= 1.5 else "外れ"},
}}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rob.to_string())
