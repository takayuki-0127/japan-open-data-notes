"""3〜4月の割合、ピークの倍率、ハーフィンダール指数（長期・日本人）と、年齢別の3〜4月の割合（2019・2023〜25年）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
L = pd.read_csv(ROOT / "data" / "long_monthly.csv")
A = pd.read_csv(ROOT / "data" / "age_monthly.csv")


def stats(g):
    s = g.set_index("month").movers.reindex(range(1, 13))
    sh = s / s.sum()
    return pd.Series({"total": s.sum(), "share_mar_apr": (sh[3] + sh[4]) * 100, "share_mar": sh[3] * 100, "share_apr": sh[4] * 100,
                      "peak_ratio_mar": s[3] / s.drop(3).mean(), "peak_ratio_mar_vs_non_marapr": s[3] / s.drop([3, 4]).mean(),
                      "hhi": float((sh ** 2).sum()) * 10000})


yr = L.groupby(["kind", "year"])[["month", "movers"]].apply(stats).reset_index()
yr.to_csv(R / "season_by_year.csv", index=False, float_format="%.4f")
I = yr[yr.kind == "inter"].set_index("year"); N = yr[yr.kind == "intra"].set_index("year")
m = lambda T, c, ys: float(T.loc[ys, c].mean())
P, Q = [2017, 2018, 2019], [2023, 2024, 2025]
main = {
    "inter_share_1719": round(m(I, "share_mar_apr", P), 2), "inter_share_2325": round(m(I, "share_mar_apr", Q), 2),
    "inter_share_8089": round(m(I, "share_mar_apr", list(range(1980, 1990))), 2),
    "inter_share_1519": round(m(I, "share_mar_apr", list(range(2015, 2020))), 2),
    "inter_share_6069": round(m(I, "share_mar_apr", list(range(1960, 1970))), 2),
    "inter_share_max": round(float(I.share_mar_apr.max()), 2), "inter_share_max_year": int(I.share_mar_apr.idxmax()),
    "inter_share_2019": round(float(I.loc[2019, "share_mar_apr"]), 2), "inter_share_2025": round(float(I.loc[2025, "share_mar_apr"]), 2),
    "inter_share_2020": round(float(I.loc[2020, "share_mar_apr"]), 2), "inter_share_2021": round(float(I.loc[2021, "share_mar_apr"]), 2),
    "inter_peak_1719": round(m(I, "peak_ratio_mar", P), 2), "inter_peak_2325": round(m(I, "peak_ratio_mar", Q), 2),
    "inter_hhi_1719": round(m(I, "hhi", P), 1), "inter_hhi_2325": round(m(I, "hhi", Q), 1),
    "intra_share_1719": round(m(N, "share_mar_apr", P), 2), "intra_share_2325": round(m(N, "share_mar_apr", Q), 2),
    "intra_peak_1719": round(m(N, "peak_ratio_mar", P), 2), "intra_peak_2325": round(m(N, "peak_ratio_mar", Q), 2),
    "inter_mar_1719": round(m(I, "share_mar", P), 3), "inter_mar_2325": round(m(I, "share_mar", Q), 3),
    "inter_apr_1719": round(m(I, "share_apr", P), 3), "inter_apr_2325": round(m(I, "share_apr", Q), 3),
    "inter_total_1719": round(m(I, "total", P)), "inter_total_2325": round(m(I, "total", Q)),
    "even_share_2months": round(2 / 12 * 100, 2),
}
main["h1_diff"] = round(main["inter_share_2325"] - main["inter_share_1719"], 2)

# 年齢別
AG = {"0-14": ["0-4", "5-9", "10-14"], "15-19": ["15-19"], "20-24": ["20-24"], "25-29": ["25-29"], "30-39": ["30-34", "35-39"],
      "40-64": ["40-44", "45-49", "50-54", "55-59", "60-64"], "65+": ["65-69", "70-74", "75-79", "80-84", "85-89", "90+"],
      "15-24": ["15-19", "20-24"], "25-64": ["25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"], "total": ["total"]}
rows = []
for y, g in A.groupby("year"):
    g = g.set_index("month")
    for k, cols in AG.items():
        s = g[cols].sum(axis=1)
        rows.append(dict(year=y, age=k, annual=float(s.sum()), share_mar_apr=float((s[3] + s[4]) / s.sum() * 100),
                         share_of_marapr_movers=float((s[3] + s[4]) / (g["total"][3] + g["total"][4]) * 100)))
ag = pd.DataFrame(rows)
ag.to_csv(R / "age_share_mar_apr.csv", index=False, float_format="%.4f")
G = ag.pivot(index="age", columns="year", values="share_mar_apr")
main["age_share"] = {a: {int(y): round(float(G.loc[a, y]), 2) for y in G.columns} for a in G.index}
main["age_share_of_marapr_2025"] = {r.age: round(r.share_of_marapr_movers, 1) for r in ag[ag.year == 2025].itertuples()}
main["h3_gap_2025"] = round(float(G.loc["20-24", 2025] - G.loc["total", 2025]), 2)
main["h4_drop_15_24"] = round(float(G.loc["15-24", 2025] - G.loc["15-24", 2019]), 2)
main["h4_drop_25_64"] = round(float(G.loc["25-64", 2025] - G.loc["25-64", 2019]), 2)
main["hypotheses"] = {
    "H1": "支持" if main["h1_diff"] <= -1 else "外れ",
    "H2": "支持" if main["inter_share_1519"] > main["inter_share_8089"] else "外れ",
    "H3": "支持" if main["h3_gap_2025"] >= 10 else "外れ",
    "H4": "支持" if main["h4_drop_25_64"] < main["h4_drop_15_24"] else "外れ",
}
rb = pd.DataFrame([
    dict(check="基本：都道府県間（日本人）3〜4月の割合 2017〜19→2023〜25", before=main["inter_share_1719"], after=main["inter_share_2325"], unit="%"),
    dict(check="都道府県内の移動", before=main["intra_share_1719"], after=main["intra_share_2325"], unit="%"),
    dict(check="3月のピークの倍率（3月 ÷ ほかの11か月の平均）都道府県間", before=main["inter_peak_1719"], after=main["inter_peak_2325"], unit="倍"),
    dict(check="3月のピークの倍率 都道府県内", before=main["intra_peak_1719"], after=main["intra_peak_2325"], unit="倍"),
    dict(check="1年ずつ：2019年→2025年 都道府県間", before=main["inter_share_2019"], after=main["inter_share_2025"], unit="%"),
    dict(check="ハーフィンダール指数（12か月の割合の2乗の和×1万）都道府県間", before=main["inter_hhi_1719"], after=main["inter_hhi_2325"], unit="（均等なら833）"),
    dict(check="外国人を含む移動者（月報、全年齢）2019年→2025年", before=round(float(G.loc["total", 2019]), 2), after=round(float(G.loc["total", 2025]), 2), unit="%"),
])
rb["diff"] = (rb.after - rb.before).round(2)
rb.to_csv(R / "robustness.csv", index=False)
main["robust"] = {r.check: {"before": r.before, "after": r.after, "diff": r.diff} for r in rb.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(rb.to_string())
print(I.loc[2010:, ["share_mar_apr", "peak_ratio_mar", "hhi"]].round(2).to_string())
