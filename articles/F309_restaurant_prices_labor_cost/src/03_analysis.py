"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "monthly.csv")
m["t"] = m.year * 12 + m.month - 1
m = m.set_index("t").sort_index()
r3 = lambda x: round(float(x), 3)
yoy = lambda s: 100 * (np.log(s) - np.log(s.shift(12)))
for c in ["cpi_eatout", "cpi_food_xfresh", "cpi_processed_food", "cpi_other_services", "cpi_all"]:
    m[f"y_{c}"] = yoy(m[c])
for c in ["wage_restaurant", "wage_M_part", "wage_TL_part"]:
    m[f"{c}_ma"] = m[c].rolling(12).mean()
    m[f"y_{c}"] = yoy(m[f"{c}_ma"])
T = lambda y, mo: y * 12 + mo - 1
tax = ((m.index >= T(2014, 4)) & (m.index <= T(2015, 3))) | ((m.index >= T(2019, 10)) & (m.index <= T(2020, 9)))
m["tax"] = tax
m.round(4).to_csv(RES / "monthly_yoy.csv")

def reg(y="y_cpi_eatout", food="y_cpi_processed_food", wage="y_wage_restaurant", lag=6, start=T(2010, 1), end=T(2026, 9)):
    d = pd.DataFrame({"y": m[y], "food": m[food].shift(lag), "wage": m[wage].shift(lag), "tax": m.tax}).loc[start:end]
    d = d[~d.tax].dropna()
    r = sm.OLS(d.y, sm.add_constant(d[["food", "wage"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    return dict(y=y, food=food, wage=wage, lag=lag, start=f"{start // 12}-{start % 12 + 1:02d}", n=int(r.nobs),
                b_food=r3(r.params["food"]), p_food=r3(r.pvalues["food"]), b_wage=r3(r.params["wage"]), p_wage=r3(r.pvalues["wage"]),
                const=r3(r.params["const"]), r2=r3(r.rsquared)), r

out = {}
h1, r1 = reg(); out["H1"] = h1
out["H1_verdict"] = "支持" if (h1["b_wage"] > 0 and h1["p_wage"] < 0.05) else "外れ"
out["H2_verdict"] = "支持" if h1["b_food"] > h1["b_wage"] else "外れ"
# H3 寄与：2021年12月→2026年9月の外食の上昇（対数差）と、各説明変数の前年比の和/12 × 係数
s, e = T(2021, 12), T(2026, 9)
rise = 100 * np.log(m.loc[e, "cpi_eatout"] / m.loc[s, "cpi_eatout"])
win = m.loc[s + 1:e]
lag = 6
contrib_food = h1["b_food"] * m["y_cpi_processed_food"].shift(lag).loc[s + 1:e].sum() / 12
contrib_wage = h1["b_wage"] * m["y_wage_restaurant"].shift(lag).loc[s + 1:e].sum() / 12
contrib_const = h1["const"] * len(win) / 12
out["H3"] = dict(period="2021-12→2026-09", eatout_rise=r3(rise), contrib_food=r3(contrib_food), contrib_wage=r3(contrib_wage), contrib_const=r3(contrib_const),
                 residual=r3(rise - contrib_food - contrib_wage - contrib_const),
                 processed_food_rise=r3(100 * np.log(m.loc[e, "cpi_processed_food"] / m.loc[s, "cpi_processed_food"])),
                 wage_rise=r3(100 * np.log(m.loc[T(2026, 8), "wage_restaurant_ma"] / m.loc[s, "wage_restaurant_ma"])),
                 other_services_rise=r3(100 * np.log(m.loc[e, "cpi_other_services"] / m.loc[s, "cpi_other_services"])),
                 all_rise=r3(100 * np.log(m.loc[e, "cpi_all"] / m.loc[s, "cpi_all"])))
out["H3_verdict"] = "支持" if contrib_food > contrib_wage else "外れ"
h4a, _ = reg(y="y_cpi_other_services", wage="y_wage_TL_part"); h4b, _ = reg(y="y_cpi_other_services", wage="y_wage_restaurant")
out["H4"] = h4a; out["H4_restaurant_wage"] = h4b
out["H4_verdict"] = "支持" if (h4a["b_wage"] > 0 and h4a["p_wage"] < 0.05) else "外れ"
rob = [h1 | {"spec": "主（ラグ6）"}]
for L in (0, 3, 12):
    rob.append(reg(lag=L)[0] | {"spec": f"R1 ラグ{L}"})
rob.append(reg(food="y_cpi_food_xfresh")[0] | {"spec": "R2 食材を生鮮食品を除く食料に"})
rob.append(reg(wage="y_wage_M_part", start=T(2011, 1))[0] | {"spec": "R3 時給を宿泊・飲食のパートに（2011年〜）"})
rob.append(reg(start=T(2015, 1))[0] | {"spec": "R4 2015年〜"})
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
out["robustness"] = rob
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "robustness"}, ensure_ascii=False, indent=0))
print(pd.DataFrame(rob)[["spec", "n", "b_food", "p_food", "b_wage", "p_wage", "r2"]].to_string())
