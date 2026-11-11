import json
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import DATA, RAW, RES, IND16, SIZE_NAME

out = {}
# ---------- H1 広さ：産業 ----------
ind = pd.read_csv(DATA / "industry_general.csv", dtype={"産業分類": str})
ind["yoy_hourly"] = ((1 + ind.yoy_sched / 100) / (1 + ind.yoy_hours / 100) - 1) * 100
rows = []
for y, g in ind.groupby("年"):
    g = g.dropna(subset=["yoy_sched"])
    if len(g) < 14: continue
    r = {"年": y, "n": len(g)}
    for th in (1, 2, 3):
        r[f"share_ge{th}"] = (g.yoy_sched >= th).mean() * 100
        w = g.workers.fillna(0)
        r[f"wshare_ge{th}"] = (w * (g.yoy_sched >= th)).sum() / w.sum() * 100
        r[f"hshare_ge{th}"] = (g.yoy_hourly >= th).mean() * 100
    r["share_pos"] = (g.yoy_sched > 0).mean() * 100
    r["median_yoy"] = g.yoy_sched.median()
    r["sd_yoy"] = g.yoy_sched.std()
    rows.append(r)
br = pd.DataFrame(rows)
br.to_csv(RES / "h1_breadth_by_year.csv", index=False)
def per(df, a, b, col): return df[(df.年 >= a) & (df.年 <= b)][col].mean()
h1 = []
for col in ["share_ge1", "share_ge2", "share_ge3", "wshare_ge2", "hshare_ge2", "share_pos", "median_yoy"]:
    h1.append({"指標": col, "2015-19": per(br, 2015, 2019, col), "2011-19（2010年は産業分類が足りず除外）": per(br, 2011, 2019, col),
               "2022-23": per(br, 2022, 2023, col), "2024-25": per(br, 2024, 2025, col), "2025": per(br, 2025, 2025, col)})
h1 = pd.DataFrame(h1); h1.to_csv(RES / "h1_breadth_periods.csv", index=False)
out["h1"] = h1.round(2).to_dict(orient="records")
out["h1_2025_industries_below2"] = ind[(ind.年 == 2025) & (ind.yoy_sched < 2)][["産業分類", "yoy_sched"]].values.tolist()

# ---------- H2 追いつき：規模 ----------
sz = pd.read_csv(DATA / "size_levels.csv", dtype={"規模": str, "就業形態": str})
sz["hourly"] = sz["所定内給与"] / sz["所定内労働時間"]
sz = sz.sort_values(["規模", "就業形態", "年"])
for c in ["所定内給与", "hourly"]:
    sz["yoy_" + c] = sz.groupby(["規模", "就業形態"])[c].pct_change() * 100
sz.to_csv(RES / "h2_size_yoy.csv", index=False)
gap = []
for f in ["0", "1", "2"]:
    for c in ["所定内給与", "hourly"]:
        p = sz[sz.就業形態 == f].pivot(index="年", columns="規模", values="yoy_" + c)
        lv = sz[sz.就業形態 == f].pivot(index="年", columns="規模", values=c)
        for y in p.index:
            gap.append({"就業形態": f, "指標": c, "年": y, "yoy_500plus": p.loc[y, "4"], "yoy_5_29": p.loc[y, "9"],
                        "yoy_30_99": p.loc[y, "7"], "yoy_100_499": p.loc[y, "5"],
                        "gap_large_minus_small": p.loc[y, "4"] - p.loc[y, "9"], "ratio_small_large": lv.loc[y, "9"] / lv.loc[y, "4"]})
gap = pd.DataFrame(gap); gap.to_csv(RES / "h2_size_gap.csv", index=False)
g1 = gap[(gap.就業形態 == "1") & (gap.指標 == "所定内給与")].set_index("年")
out["h2_general_monthly"] = g1.loc[2015:2025, ["yoy_500plus", "yoy_100_499", "yoy_30_99", "yoy_5_29", "gap_large_minus_small", "ratio_small_large"]].round(3).reset_index().to_dict(orient="records")
summ = []
for (f, c), g in gap.groupby(["就業形態", "指標"]):
    g = g.set_index("年")
    summ.append({"就業形態": f, "指標": c, "gap_2015_19": g.loc[2015:2019, "gap_large_minus_small"].mean(),
                 "gap_2010_19": g.loc[2010:2019, "gap_large_minus_small"].mean(),
                 "gap_2023_25": g.loc[2023:2025, "gap_large_minus_small"].mean(),
                 "small_beats_large_2yrs_2024_25": bool((g.loc[2024:2025, "yoy_5_29"] > g.loc[2024:2025, "yoy_500plus"]).all()),
                 "ratio_2019": g.loc[2019, "ratio_small_large"], "ratio_2022": g.loc[2022, "ratio_small_large"], "ratio_2025": g.loc[2025, "ratio_small_large"]})
summ = pd.DataFrame(summ); summ.to_csv(RES / "h2_size_summary.csv", index=False)
out["h2_summary"] = summ.round(4).to_dict(orient="records")
# 企業規模（賃金引上げ等の実態調査）
t1 = pd.read_csv(RAW / "chingin_hikiage_table1.csv")
p1 = t1.pivot(index="year", columns="size", values="rate_pct")
p1["gap"] = p1["5,000人以上"] - p1["100～299人"]
p1.to_csv(RES / "h2_firm_size_rate.csv")
t4 = pd.read_csv(RAW / "chingin_hikiage_table4.csv").pivot(index="year", columns="size", values="raised")
out["h2_firm"] = {"gap_2015_19": p1.loc[2015:2019, "gap"].mean(), "gap_2010_19": p1.loc[2010:2019, "gap"].mean(),
                  "gap_2023_25": p1.loc[2023:2025, "gap"].mean(), "gap_2025": p1.loc[2025, "gap"],
                  "rate_2025": p1.loc[2025, ["5,000人以上", "100～299人"]].to_dict(),
                  "raised_share_100_299": t4.loc[[2019, 2022, 2025], "100～299人"].to_dict(),
                  "raised_share_5000": t4.loc[[2019, 2022, 2025], "5,000人以上"].to_dict()}

# ---------- H3 パートと最低賃金 ----------
nat = pd.read_csv(DATA / "national.csv", dtype={"就業形態": str})
pt = nat[nat.就業形態 == "2"].set_index("年").sort_index()
pt["yoy_hourly"] = ((1 + pt.yoy_sched / 100) / (1 + pt.yoy_hours / 100) - 1) * 100
pt["lvl_hourly"] = pt.lvl_sched / pt.lvl_hours
mw = pd.read_csv(RAW / "mw_national.csv").set_index("fiscal_year")["mw_weighted_avg_yen"]
# 暦年の平均：10月改定なので 1〜9月は前年度の額、10〜12月はその年度の額
mwcy = pd.Series({y: 0.75 * mw[y - 1] + 0.25 * mw[y] for y in range(2008, 2026)})
pt["mw_cy"] = mwcy
pt["mw_yoy"] = pt["mw_cy"].pct_change() * 100
pt["mw_yoy_fy"] = pd.Series({y: (mw[y] / mw[y - 1] - 1) * 100 for y in range(2008, 2026)})
pt["mw_yoy_lag"] = pt["mw_yoy_fy"].shift(1)
pt.to_csv(RES / "h3_part_mw.csv")
def reg(df, x, y="yoy_hourly"):
    d = df.dropna(subset=[y, x])
    m = sm.OLS(d[y], sm.add_constant(d[x])).fit(cov_type="HC1")
    hac = sm.OLS(d[y], sm.add_constant(d[x])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    ci = m.conf_int().loc[x].tolist()
    return {"n": int(m.nobs), "b": m.params[x], "ci": ci, "ci_hac2": hac.conf_int().loc[x].tolist(), "a": m.params["const"], "r2": m.rsquared}
h3 = {}
base = pt.loc[2010:2025]
h3["main_cy_2010_25"] = reg(base, "mw_yoy")
h3["excl_covid"] = reg(base.drop([2020, 2021]), "mw_yoy")
h3["fy_same_year"] = reg(base, "mw_yoy_fy")
h3["fy_lag1"] = reg(base, "mw_yoy_lag")
h3["since2015"] = reg(pt.loc[2015:2025], "mw_yoy")
cum = lambda s, a, b: (s.loc[b] / s.loc[a] - 1) * 100
# 感度：2025年度の最低賃金は11月〜翌3月に発効した県が多い。2025暦年を2024年度の額だけで置いた下限
mw_low = pt["mw_cy"].copy(); mw_low.loc[2025] = mw[2024]
pt["mw_yoy_low2025"] = mw_low.pct_change() * 100
h3["mw2025_lowerbound"] = reg(pt.loc[2010:2025], "mw_yoy_low2025")
h3["mw2025_lowerbound_cy_value"] = float(mw[2024]); h3["mw2025_cy_value"] = float(pt.loc[2025, "mw_cy"])
h3["ratio_part_to_mw_2025_lowerbound"] = float(pt.loc[2025, "lvl_hourly"] / mw[2024])
h3["cum_2016_25_mw_cy_lowerbound"] = (mw[2024] / pt.loc[2016, "mw_cy"] - 1) * 100
h3["cum_2016_25_part_hourly_lvl"] = cum(pt.lvl_hourly, 2016, 2025)
h3["cum_2016_25_mw_cy"] = cum(pt.mw_cy, 2016, 2025)
h3["part_hourly_lvl"] = pt.lvl_hourly.loc[[2016, 2019, 2022, 2025]].round(0).to_dict()
h3["ratio_part_to_mw"] = (pt.lvl_hourly / pt.mw_cy).loc[[2010, 2016, 2019, 2022, 2025]].round(3).to_dict()
idx = (1 + pt.yoy_hourly.loc[2017:2025] / 100).prod()
h3["cum_2016_25_part_hourly_idx"] = (idx - 1) * 100
out["h3"] = h3
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda v: round(float(v), 3)))
