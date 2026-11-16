"""前年比・年度平均・4月の前月比・品目別の上昇・軽油との回帰。results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "monthly.csv", index_col="ym")
m = m.loc[:202609]
idx = pd.PeriodIndex([pd.Period(f"{str(i)[:4]}-{str(i)[4:]}", "M") for i in m.index])
m.index = idx
yoy = (m / m.shift(12) - 1) * 100
mom = (m / m.shift(1) - 1) * 100
fy = lambda p: p.year if p.month >= 4 else p.year - 1
yoy["fy"] = [fy(p) for p in yoy.index]

# 年度平均の前年比
fy_tab = yoy[(yoy.fy >= 2016) & (yoy.fy <= 2025)].groupby("fy")[["road", "all", "all_ex_intl", "parcel", "truck_food", "truck_chem", "truck_metal", "truck_misc", "rail", "coastal", "warehouse", "diesel"]].mean()
fy_tab["n_months"] = yoy[(yoy.fy >= 2016) & (yoy.fy <= 2025)].groupby("fy").size()
fy_tab.to_csv(R / "yoy_by_fiscal_year.csv", float_format="%.4f")

# 4月の前月比
apr = mom[mom.index.month == 4].copy(); apr.index = apr.index.year
apr = apr.loc[2016:2026, ["road", "all_ex_intl", "parcel", "truck_food", "truck_chem", "truck_metal", "truck_misc"]]
apr.to_csv(R / "april_mom.csv", float_format="%.4f")

P = lambda y, mo: pd.Period(f"{y}-{mo:02d}", "M")
def chg(col, a, b):
    return float((m.loc[b, col] / m.loc[a, col] - 1) * 100)

items = ["road", "parcel", "truck_food", "truck_chem", "truck_metal", "truck_misc", "rail", "coastal", "warehouse", "all_ex_intl", "all", "diesel"]
two = pd.DataFrame({"chg_2303_2503": [chg(c, P(2023, 3), P(2025, 3)) for c in items],
                    "chg_2103_2303": [chg(c, P(2021, 3), P(2023, 3)) for c in items],
                    "chg_2303_2603": [chg(c, P(2023, 3), P(2026, 3)) for c in items],
                    "chg_1503_2303": [chg(c, P(2015, 3), P(2023, 3)) for c in items]}, index=items)
two.index.name = "series"
two.to_csv(R / "change_by_item.csv", float_format="%.4f")

# 軽油との回帰：road の前年比 ~ 軽油の前年比（同じ月）＋ 6か月前
def fit(start, end):
    d = pd.DataFrame({"y": yoy.road, "x0": yoy.diesel, "x6": yoy.diesel.shift(6)}).dropna()
    tr = d.loc[P(*start):P(*end)]
    X = sm.add_constant(tr[["x0", "x6"]])
    res = sm.OLS(tr.y, X).fit()
    te = d.loc[P(2024, 4):P(2025, 3)]
    pr = res.get_prediction(sm.add_constant(te[["x0", "x6"]], has_constant="add")).summary_frame(alpha=0.05)
    return res, te, pr
res, te, pr = fit((2016, 1), (2023, 12))
pred = pd.DataFrame({"actual": te.y, "pred": pr["mean"], "pi_lo": pr["obs_ci_lower"], "pi_hi": pr["obs_ci_upper"]})
pred.index = pred.index.astype(str)
pred.to_csv(R / "diesel_regression_fy2024.csv", float_format="%.4f")
res2, te2, pr2 = fit((2016, 1), (2019, 12))

main = {}
main["fy_road"] = {int(k): round(float(v), 2) for k, v in fy_tab.road.items()}
main["fy_all_ex_intl"] = {int(k): round(float(v), 2) for k, v in fy_tab.all_ex_intl.items()}
main["fy2025_months"] = int(fy_tab.loc[2025, "n_months"])
main["road_2303_2503"] = round(two.loc["road", "chg_2303_2503"], 1)
main["allex_2303_2503"] = round(two.loc["all_ex_intl", "chg_2303_2503"], 1)
main["all_2303_2503"] = round(two.loc["all", "chg_2303_2503"], 1)
main["road_2103_2303"] = round(two.loc["road", "chg_2103_2303"], 1)
main["allex_2103_2303"] = round(two.loc["all_ex_intl", "chg_2103_2303"], 1)
main["road_2303_2603"] = round(two.loc["road", "chg_2303_2603"], 1)
main["allex_2303_2603"] = round(two.loc["all_ex_intl", "chg_2303_2603"], 1)
main["road_1503_2303"] = round(two.loc["road", "chg_1503_2303"], 1)
main["allex_1503_2303"] = round(two.loc["all_ex_intl", "chg_1503_2303"], 1)
main["item_2303_2503"] = {k: round(float(v), 1) for k, v in two.chg_2303_2503.items()}
main["apr_road"] = {int(k): round(float(v), 2) for k, v in apr.road.items()}
main["apr_road_avg_2016_2023"] = round(float(apr.road.loc[2016:2023].mean()), 2)
main["apr_road_2024"] = round(float(apr.road.loc[2024]), 2)
main["apr_road_2025"] = round(float(apr.road.loc[2025]), 2)
main["apr_road_2026"] = round(float(apr.road.loc[2026]), 2)
main["apr_allex_avg_2016_2023"] = round(float(apr.all_ex_intl.loc[2016:2023].mean()), 2)
main["apr_allex_2024"] = round(float(apr.all_ex_intl.loc[2024]), 2)
main["reg"] = {"coef_x0": round(float(res.params.x0), 3), "coef_x6": round(float(res.params.x6), 3), "r2": round(float(res.rsquared), 3), "n": int(res.nobs),
               "fy2024_actual_mean": round(float(pred.actual.mean()), 2), "fy2024_pred_mean": round(float(pred.pred.mean()), 2),
               "months_above_pi": int((pred.actual > pred.pi_hi).sum()), "pi_hi_mean": round(float(pred.pi_hi.mean()), 2)}
p2 = pd.DataFrame({"actual": te2.y, "pred": pr2["mean"], "hi": pr2["obs_ci_upper"]})
main["reg_pre_covid"] = {"r2": round(float(res2.rsquared), 3), "n": int(res2.nobs), "fy2024_pred_mean": round(float(p2.pred.mean()), 2),
                         "months_above_pi": int((p2.actual > p2.hi).sum()), "pi_hi_mean": round(float(p2.hi.mean()), 2)}
truck4 = ["truck_food", "truck_chem", "truck_metal", "truck_misc"]
main["truck4_avg_2303_2503"] = round(float(two.loc[truck4, "chg_2303_2503"].mean()), 1)
main["road_level_2609"] = float(m.loc[P(2026, 9), "road"]); main["road_level_2303"] = float(m.loc[P(2023, 3), "road"])
main["hypotheses"] = {
    "H1": "支持" if main["fy_road"][2024] > main["fy_road"][2023] else "外れ",
    "H2": "支持" if main["road_2303_2503"] > main["allex_2303_2503"] else "外れ",
    "H3": "支持" if main["apr_road_2024"] >= 2 * main["apr_road_avg_2016_2023"] else "外れ",
    "H4": "支持" if pred.actual.mean() > pred.pi_hi.mean() else "外れ",
}
# 頑健性
rb = pd.DataFrame([
    dict(check="基本：2023年3月→2025年3月、道路貨物輸送 − 総平均（除く国際運輸）", value=round(main["road_2303_2503"] - main["allex_2303_2503"], 1), unit="ポイント"),
    dict(check="相手を総平均（含む国際運輸）にする", value=round(main["road_2303_2503"] - main["all_2303_2503"], 1), unit="ポイント"),
    dict(check="期間を2023年3月→2026年3月（3年）にする", value=round(main["road_2303_2603"] - main["allex_2303_2603"], 1), unit="ポイント"),
    dict(check="宅配便を除く自動車貨物輸送4品目の単純平均 − 総平均（除く国際運輸）", value=round(main["truck4_avg_2303_2503"] - main["allex_2303_2503"], 1), unit="ポイント"),
    dict(check="比べる時期：2021年3月→2023年3月（2024年問題の前の2年）", value=round(main["road_2103_2303"] - main["allex_2103_2303"], 1), unit="ポイント"),
    dict(check="回帰を2016〜2019年で推計：2024年度の実際 − 予測の上限（平均）", value=round(float(p2.actual.mean() - p2.hi.mean()), 2), unit="ポイント"),
    dict(check="回帰を2016〜2023年で推計：2024年度の実際 − 予測の上限（平均）", value=round(float(pred.actual.mean() - pred.pi_hi.mean()), 2), unit="ポイント"),
])
rb.to_csv(R / "robustness.csv", index=False)
main["robust"] = {r.check: r.value for r in rb.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(fy_tab.round(2).to_string())
