"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
cpi = pd.read_csv(D / "cpi_rent_annual.csv").set_index("year")
ts = pd.read_csv(D / "jutaku_rent_timeseries.csv")
t = pd.read_csv(D / "t27_cells.csv")
MID = {"昭和25年以前に建築": 1945.0, "昭和26年～45年": 1960.5, "昭和46年～55年": 1975.5, "昭和56年～平成２年": 1985.5, "平成３年～12年": 1995.5,
       "平成13年～17年": 2003.0, "平成18年～22年": 2008.0, "平成23年～27年": 2013.0, "平成28年～令和２年": 2018.0, "令和３年～５年９月": 2022.4}
MOVE = {"令和３年～５年９月に入居": "2021〜23年", "平成28年～令和２年に入居": "2016〜20年"}
YEARS = [1973, 1978, 1983, 1988, 1993, 1998, 2003, 2008, 2013, 2018, 2023]
out = {}

# 住調と CPI を同じ年で並べる
pt = ts[ts.measure == "rent_per_tatami"].pivot(index="year", columns="tenure", values="value")
mr = ts[ts.measure == "monthly_rent"].pivot(index="year", columns="tenure", values="value")
cnt = t[(t.section == "count") & (t.movein == "総数") & (t.construction == "総数")].set_index("tenure").value
w_wood = cnt["private_wood"] / (cnt["private_wood"] + cnt["private_nonwood"])
comp = pd.DataFrame({"cpi_private_rent": cpi.loc[YEARS, "private_rent"], "tatami_wood": pt.loc[YEARS, "private_wood"], "tatami_nonwood": pt.loc[YEARS, "private_nonwood"],
                     "monthly_wood": mr.loc[YEARS, "private_wood"], "monthly_nonwood": mr.loc[YEARS, "private_nonwood"], "cpi_all_items": cpi.loc[YEARS, "all_items"]})
comp.index.name = "year"; comp.to_csv(RES / "cpi_vs_jutaku_by_year.csv")
def dl(a, b): return 100 * np.log(b / a)
def h1(y0, y1, kind="tatami"):
    w = w_wood * dl(comp.loc[y0, f"{kind}_wood"], comp.loc[y1, f"{kind}_wood"]) + (1 - w_wood) * dl(comp.loc[y0, f"{kind}_nonwood"], comp.loc[y1, f"{kind}_nonwood"])
    c = dl(comp.loc[y0, "cpi_private_rent"], comp.loc[y1, "cpi_private_rent"])
    return dict(jutaku=r3(w), cpi=r3(c), gap=r3(w - c), wood=r3(dl(comp.loc[y0, f"{kind}_wood"], comp.loc[y1, f"{kind}_wood"])), nonwood=r3(dl(comp.loc[y0, f"{kind}_nonwood"], comp.loc[y1, f"{kind}_nonwood"])))
out["w_wood_2023"] = r3(w_wood)
out["H1"] = h1(2003, 2023); out["H1_verdict"] = "支持" if out["H1"]["gap"] >= 5 else "外れ"
out["H1_periods"] = {f"{a}-{b}": h1(a, b) for a, b in zip(YEARS[5:-1], YEARS[6:])}

# 第27表のマス
def cells(col="private", sec="rent_per_tatami", minc=1000):
    c = t[(t.tenure == col) & (t.movein != "総数") & (t.construction != "総数")]
    x = c[c.section == sec].set_index(["movein", "construction"]).value.rename("rent")
    n = c[c.section == "count"].set_index(["movein", "construction"]).value.rename("n")
    z = pd.concat([x, n], axis=1).reset_index().dropna()
    z = z[z.n >= minc].copy()
    z["lr"] = 100 * np.log(z.rent); z["age"] = 2023.75 - z.construction.map(MID)
    z["mv"] = z.movein.map(MOVE).fillna("2015年以前")
    return z
def h2(col="private", sec="rent_per_tatami"):
    c = t[(t.tenure == col) & (t.movein == "総数") & (t.section == sec)].set_index("construction").value
    return r3(dl(c["平成３年～12年"], c["平成28年～令和２年"]))
def h3(z):
    X = pd.get_dummies(z[["construction", "mv"]], drop_first=False).astype(float)
    X = X.drop(columns=["construction_平成３年～12年", "mv_2015年以前"])
    X = sm.add_constant(X)
    m = sm.WLS(z.lr, X, weights=z.n).fit(cov_type="HC3")
    return dict(new_vs_old=r3(m.params["mv_2021〜23年"]), new_se=r3(m.bse["mv_2021〜23年"]), mid_vs_old=r3(m.params["mv_2016〜20年"]), n_cells=int(len(z)))
def h4(z, only_new_build=False):
    if only_new_build: z = z[z.construction.map(MID) >= 2003]
    X = pd.get_dummies(z[["mv"]], drop_first=False).astype(float).drop(columns=["mv_2015年以前"], errors="ignore")
    X["age"] = z.age; X = sm.add_constant(X)
    m = sm.WLS(z.lr, X, weights=z.n).fit(cov_type="HC3")
    return dict(slope_per_year=r3(m.params["age"]), se=r3(m.bse["age"]), n_cells=int(len(z)))
z = cells()
z.to_csv(RES / "t27_private_cells.csv", index=False)
out["H2"] = {"new_2016_20_vs_1991_2000": h2()}; out["H2_verdict"] = "支持" if out["H2"]["new_2016_20_vs_1991_2000"] >= 18 else "外れ"
out["H3"] = h3(z); out["H3_verdict"] = "支持" if out["H3"]["new_vs_old"] >= 3 else "外れ"
out["H4"] = h4(z)
b = out["H4"]["slope_per_year"]
out["H4"]["cpi_2003_2023"] = out["H1"]["cpi"]
out["H4"]["aging_addback_20y"] = r3(-b * 20)
out["H4"]["cpi_adjusted_2003_2023"] = r3(out["H1"]["cpi"] - b * 20)
out["H4_verdict"] = "支持" if out["H4"]["cpi_adjusted_2003_2023"] > 0 else "外れ"

# 頑健性
rob = []
for col, lab in [("private_wood", "木造"), ("private_nonwood", "非木造")]:
    zz = cells(col)
    rob.append(dict(spec=f"R1 民営借家（{lab}）", H2=h2(col), H3=h3(zz)["new_vs_old"], H4_slope=h4(zz)["slope_per_year"]))
zz = cells(sec="rent_per_tatami_incl_fee")
rob.append(dict(spec="R2 共益費・管理費を含む", H2=h2(sec="rent_per_tatami_incl_fee"), H3=h3(zz)["new_vs_old"], H4_slope=h4(zz)["slope_per_year"]))
zz = cells(minc=5000)
rob.append(dict(spec="R3 小さいマスの基準 5,000戸", H2=out["H2"]["new_2016_20_vs_1991_2000"], H3=h3(zz)["new_vs_old"], H4_slope=h4(zz)["slope_per_year"]))
rob.append(dict(spec="R4 経年の率を2001年以降の建築だけで", H2=None, H3=None, H4_slope=h4(z, True)["slope_per_year"]))
rob.append(dict(spec="R5 H1 を1か月当たり家賃で", H1_gap=h1(2003, 2023, "monthly")["gap"], H1_jutaku=h1(2003, 2023, "monthly")["jutaku"]))
out["robustness"] = rob
for r in rob:
    if r.get("H4_slope") is not None:
        r["cpi_adjusted"] = r3(out["H1"]["cpi"] - r["H4_slope"] * 20)
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
