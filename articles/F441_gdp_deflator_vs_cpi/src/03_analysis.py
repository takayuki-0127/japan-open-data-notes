"""差の4段の分解、分散への寄与、仮説の判定、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
a = pd.read_csv(ROOT / "data" / "annual.csv").set_index("year")


def g(s):
    return (s / s.shift(1) - 1) * 100


def build(a, cpi="cpi_all", hh="impl_hh_xrent", src="impl"):
    p = (lambda k: a[f"{src}_{k}"]) if src == "impl" else (lambda k: a[f"defl_{k}"])
    d = pd.DataFrame(index=a.index)
    d["cpi"] = g(a[cpi]); d["cpi_xrent"] = g(a["cpi_xrent"])
    d["hh"] = g(p(hh.replace(f"{src}_", "").replace("impl_", "")))
    d["dd"] = g(p("dd")); d["gdp"] = g(p("gdp")); d["x"] = g(p("x")); d["m"] = g(p("m"))
    d["gap"] = d.cpi - d.gdp
    d["s1_rent"] = d.cpi - d.cpi_xrent
    d["s2_formula"] = d.cpi_xrent - d.hh
    d["s3_nonconsumption"] = d.hh - d.dd
    d["s4_trade"] = d.dd - d.gdp
    # 4段目の近似分解（前年の名目の割合、対数の差）
    sx = (a.nom_x / a.nom_gdp).shift(1); sm = (a.nom_m / a.nom_gdp).shift(1); sd = (a.nom_dd / a.nom_gdp).shift(1)
    lx = np.log(p("x")).diff() * 100; lm = np.log(p("m")).diff() * 100; ld = np.log(p("dd")).diff() * 100
    lg = np.log(p("gdp")).diff() * 100
    d["s4_imports"] = sm * lm                      # 輸入の値段が上がるほど GDP デフレーターは下がる → 差（DD−GDP）はプラス
    d["s4_exports"] = -sx * lx                     # 輸出の値段が上がるほど GDP デフレーターは上がる → 差はマイナス
    d["s4_dd_weight"] = (1 - sd) * ld              # 国内需要の割合が1と違うぶん
    d["s4_resid"] = (ld - lg) - d.s4_imports - d.s4_exports - d.s4_dd_weight
    return d.loc[1995:2025]


def var_share(d, cols, years=None):
    x = d if years is None else d.loc[years]
    v = x.gap.var(ddof=0)
    return {c: float(np.cov(x[c], x.gap, ddof=0)[0, 1] / v) for c in cols}


def ann(series_level, y0, y1):
    return float(((series_level.loc[y1] / series_level.loc[y0]) ** (1 / (y1 - y0)) - 1) * 100)


STEPS = ["s1_rent", "s2_formula", "s3_nonconsumption", "s4_trade"]
d = build(a)
d.round(4).to_csv(R / "annual_gap_decomposition.csv")
assert (d[STEPS].sum(axis=1) - d.gap).abs().max() < 1e-9

vs = var_share(d, STEPS)
# 期間の年率
lev = {"cpi": a.cpi_all, "cpi_xrent": a.cpi_xrent, "hh": a.impl_hh_xrent, "dd": a.impl_dd, "gdp": a.impl_gdp, "x": a.impl_x, "m": a.impl_m}
periods = [(1994, 2025), (1994, 2012), (2012, 2019), (2019, 2025), (2021, 2025)]
rows = []
for y0, y1 in periods:
    r = {"period": f"{y0}-{y1}"}
    for k, s in lev.items():
        r[k] = ann(s, y0, y1)
    r["gap"] = r["cpi"] - r["gdp"]; r["s1_rent"] = r["cpi"] - r["cpi_xrent"]; r["s2_formula"] = r["cpi_xrent"] - r["hh"]
    r["s3_nonconsumption"] = r["hh"] - r["dd"]; r["s4_trade"] = r["dd"] - r["gdp"]
    r["cum_cpi"] = float((a.cpi_all.loc[y1] / a.cpi_all.loc[y0] - 1) * 100); r["cum_gdp"] = float((a.impl_gdp.loc[y1] / a.impl_gdp.loc[y0] - 1) * 100)
    rows.append(r)
per = pd.DataFrame(rows); per.round(4).to_csv(R / "period_annualized.csv", index=False)
P = per.set_index("period")

# 仮説
big_m = d[d.m >= 10]
h1 = max(vs, key=vs.get) == "s4_trade"
h2_share_pos = float((big_m.gap > 0).mean())
h3 = P.loc["1994-2025", "s2_formula"]
h4a = float(d.loc[2022, "gap"]); h4b = float(d.loc[[2023, 2024], "gap"].min())
hyp = {
    "H1": {"var_share": {k: round(v, 3) for k, v in vs.items()}, "max": max(vs, key=vs.get), "result": "支持" if h1 else "外れ"},
    "H2": {"years_import_10pct": [int(y) for y in big_m.index], "gap": [round(float(v), 2) for v in big_m.gap], "share_positive": round(h2_share_pos, 3),
           "result": "支持" if h2_share_pos > 0.5 else "外れ"},
    "H3": {"s2_formula_annual_1994_2025": round(float(h3), 3), "result": "支持" if h3 > 0 else "外れ"},
    "H4": {"gap_2022": round(h4a, 2), "gap_2023": round(float(d.loc[2023, "gap"]), 2), "gap_2024": round(float(d.loc[2024, "gap"]), 2),
           "result": "支持" if (h4a > 0 and h4b < 0) else "外れ"},
}

# 頑健性
rob = []
def add(name, dd, years=None, note=""):
    v = var_share(dd, [c for c in STEPS if c in dd], years)
    top = max(v, key=v.get)
    rob.append({"check": name, "s1_rent": v.get("s1_rent", np.nan), "s2_formula": v["s2_formula"], "s3_nonconsumption": v["s3_nonconsumption"],
                "s4_trade": v["s4_trade"], "top": top, "note": note})
add("基本：1995〜2025年", d)
add("期間を2000〜2025年", d, list(range(2000, 2026)))
dx = build(a, cpi="cpi_xrent"); dx["gap"] = dx.cpi_xrent - dx.gdp
add("CPI を持家の帰属家賃を除く総合に（1段目なし）", dx.assign(s1_rent=0.0))
dp = build(a, hh="impl_pce")
add("家計ではなく民間最終消費支出（NPISH を含む）デフレーター", dp)
dt = build(a, src="defl", hh="defl_hh_xrent")
add("表のデフレーター（小数1桁に丸めた値）で計算", dt)
drop = [1997, 2009, 2014, 2019, 2022]
add("大きな年（1997・2009・2014・2019・2022年）を除く", d, [y for y in d.index if y not in drop])
robdf = pd.DataFrame(rob); robdf.round(4).to_csv(R / "robustness.csv", index=False)

yrs = {int(y): {k: round(float(d.loc[y, k]), 2) for k in ["cpi", "gdp", "gap"] + STEPS + ["m", "x", "s4_imports", "s4_exports", "s4_dd_weight", "s4_resid"]}
       for y in [1997, 2008, 2009, 2014, 2015, 2019, 2021, 2022, 2023, 2024, 2025]}
main = {
    "years": [int(d.index.min()), int(d.index.max())],
    "var_share": {k: round(v, 3) for k, v in vs.items()},
    "gap_sd": round(float(d.gap.std(ddof=0)), 3),
    "corr_gap_import_growth": round(float(d.gap.corr(d.m)), 3),
    "n_gap_positive": int((d.gap > 0).sum()), "n_years": int(len(d)),
    "selected_years": yrs,
    "periods": {p: {k: round(float(v), 3) for k, v in P.loc[p].items()} for p in P.index},
    "hypotheses": hyp,
    "robustness_top": {r["check"]: r["top"] for r in rob},
    "s4_import_part_share_of_s4_var": round(float(np.cov(d.s4_imports, d.s4_trade, ddof=0)[0, 1] / d.s4_trade.var(ddof=0)), 3),
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)[:4000])
print(robdf.round(3).to_string())
