"""主な分析：2019年同月比の指数、落ちの比、弾力性、2019→2025年の比較、頑健性。
出力：results/main.json、results/index_monthly.csv、results/elasticity.csv、results/robustness.csv、results/annual.csv"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
dom = pd.read_csv(ROOT / "data" / "domestic_monthly.csv")
intl = pd.read_csv(ROOT / "data" / "intl_monthly.csv")
intl["segment"] = "intl"
intl = intl.rename(columns={"seat_km_k": "seat_km", "cargo_tkm_k": "cargo_tkm", "mail_tkm_k": "mail_tkm"})
for d in (dom, intl):
    d["cargo_mail_kg"] = d["cargo_kg"] + d["mail_kg"]
VARS = ["flights", "pax", "seat_km", "cargo_kg", "cargo_tkm", "cargo_mail_kg"]
allm = pd.concat([dom[["segment", "year", "month"] + VARS], intl[["segment", "year", "month"] + VARS + ["atk_k", "load_factor_w"]]],
                 ignore_index=True)


def index_vs(base_year):
    b = allm[allm.year == base_year].set_index(["segment", "month"])[VARS]
    out = allm.copy()
    for v in VARS:
        out[v + "_idx"] = [100 * r[v] / b.loc[(r.segment, r.month), v] for _, r in out.iterrows()]
    return out


idx = index_vs(2019)
cols = ["segment", "year", "month"] + [v + "_idx" for v in VARS]
idx[cols].round(2).to_csv(R / "index_monthly.csv", index=False)


def drop(seg, months, var, base=2019, year=2020, df=None):
    """year の months の合計の、base 年の同じ月の合計に対する減少率（%、正が減少）"""
    df = allm if df is None else df
    a = df[(df.segment == seg) & (df.year == year) & df.month.isin(months)][var].sum()
    b = df[(df.segment == seg) & (df.year == base) & df.month.isin(months)][var].sum()
    return 100 * (1 - a / b)


main = {}
# H1：国内 2020年4〜5月
for seg in ("total", "intl"):
    for nm, ms in (("apr_may", [4, 5]), ("apr_jun", [4, 5, 6]), ("apr_dec", list(range(4, 13)))):
        for v in VARS:
            main[f"drop_{seg}_{nm}_{v}"] = round(drop(seg, ms, v), 2)
for seg in ("total", "intl"):
    for nm in ("apr_may", "apr_jun", "apr_dec"):
        main[f"ratio_{seg}_{nm}_cargo_vs_seatkm"] = round(main[f"drop_{seg}_{nm}_cargo_kg"] / main[f"drop_{seg}_{nm}_seat_km"], 3)
        main[f"ratio_{seg}_{nm}_cargo_vs_flights"] = round(main[f"drop_{seg}_{nm}_cargo_kg"] / main[f"drop_{seg}_{nm}_flights"], 3)
main["H1_ratio"] = main["ratio_total_apr_may_cargo_vs_seatkm"]
main["H1_supported"] = bool(0.7 <= main["H1_ratio"] <= 1.3)
main["H2_ratio"] = main["ratio_intl_apr_jun_cargo_vs_seatkm"]
main["H2_supported"] = bool(main["H2_ratio"] < 0.5)

# 最も落ちた月
for seg in ("total", "trunk", "local", "intl"):
    s = idx[(idx.segment == seg) & (idx.year.between(2020, 2022))]
    for v in ("cargo_kg", "seat_km", "flights"):
        k = s[v + "_idx"].idxmin()
        main[f"min_{seg}_{v}_idx"] = round(float(s.loc[k, v + "_idx"]), 1)
        main[f"min_{seg}_{v}_ym"] = f"{int(s.loc[k, 'year'])}-{int(s.loc[k, 'month']):02d}"

# 年の合計
ann = allm.groupby(["segment", "year"], sort=True)[VARS].sum().reset_index()
ia = intl.groupby("year", sort=True).agg(cargo_tkm=("cargo_tkm", "sum"), atk_k=("atk_k", "sum")).reset_index()
ann.to_csv(R / "annual.csv", index=False, float_format="%.1f")
A = ann.set_index(["segment", "year"])
for seg in ("total", "trunk", "local", "intl"):
    for v in VARS:
        for y in (2020, 2021, 2022, 2023, 2024, 2025):
            main[f"chg_{seg}_{v}_{y}_vs2019"] = round(100 * (A.loc[(seg, y), v] / A.loc[(seg, 2019), v] - 1), 2)
    main[f"chg_{seg}_cargo_kg_2019_vs2014"] = round(100 * (A.loc[(seg, 2019), "cargo_kg"] / A.loc[(seg, 2014), "cargo_kg"] - 1), 2)
for y in (2014, 2019, 2020, 2021, 2022, 2025):
    main[f"cargo_t_total_{y}"] = round(A.loc[("total", y), "cargo_kg"] / 1000)
    main[f"cargo_t_intl_{y}"] = round(A.loc[("intl", y), "cargo_kg"] / 1000)
    main[f"cargo_t_trunk_{y}"] = round(A.loc[("trunk", y), "cargo_kg"] / 1000)
    main[f"cargo_t_local_{y}"] = round(A.loc[("local", y), "cargo_kg"] / 1000)
main["H3_cargo_chg"] = main["chg_total_cargo_kg_2025_vs2019"]
main["H3_seatkm_chg"] = main["chg_total_seat_km_2025_vs2019"]
main["H3_supported"] = bool(main["H3_cargo_chg"] <= -10 and main["H3_seatkm_chg"] >= -5)
main["H4_trunk"] = main["chg_trunk_cargo_kg_2025_vs2019"]
main["H4_local"] = main["chg_local_cargo_kg_2025_vs2019"]
main["H4_gap"] = round(abs(main["H4_trunk"] - main["H4_local"]), 2)
main["H4_supported"] = bool(main["H4_gap"] <= 10)
# 国際：利用可能トンキロと重量利用率
I = intl.set_index(["year", "month"])
# 貨物トンキロが利用可能トンキロ（運べる重さ×距離）に占める割合。重量利用率は旅客の重さも含むので別に出す
for y in (2019, 2020, 2021, 2025):
    g = intl[intl.year == y]
    main[f"intl_cargo_share_atk_{y}"] = round(float(100 * g.cargo_tkm.sum() / g.atk_k.sum()), 1)
    main[f"intl_wlf_{y}"] = round(float((g.load_factor_w * g.atk_k).sum() / g.atk_k.sum()), 1)
    main[f"intl_atk_chg_{y}_vs2019"] = round(100 * (g.atk_k.sum() / intl[intl.year == 2019].atk_k.sum() - 1), 2)
g20 = intl[(intl.year == 2020) & intl.month.isin([4, 5, 6])]; g19 = intl[(intl.year == 2019) & intl.month.isin([4, 5, 6])]
main["intl_atk_drop_apr_jun"] = round(100 * (1 - g20.atk_k.sum() / g19.atk_k.sum()), 2)
main["intl_cargo_share_atk_apr_jun_2020"] = round(float(100 * g20.cargo_tkm.sum() / g20.atk_k.sum()), 1)
main["intl_cargo_share_atk_apr_jun_2019"] = round(float(100 * g19.cargo_tkm.sum() / g19.atk_k.sum()), 1)
# 1便あたりの貨物（トン）
for seg in ("total", "intl"):
    for y in (2019, 2020, 2025):
        main[f"cargo_per_flight_t_{seg}_{y}"] = round(A.loc[(seg, y), "cargo_kg"] / A.loc[(seg, y), "flights"] / 1000, 3)
    g20 = allm[(allm.segment == seg) & (allm.year == 2020) & allm.month.isin([4, 5])]
    main[f"cargo_per_flight_t_{seg}_2020_apr_may"] = round(g20.cargo_kg.sum() / g20.flights.sum() / 1000, 3)

# 弾力性：log(貨物) ~ log(座席キロ) + 月の固定効果
rows = []
for seg in ("total", "trunk", "local", "intl"):
    for per, (y0, y1) in (("2014-2019", (2014, 2019)), ("2020-2022", (2020, 2022)), ("2014-2025", (2014, 2025)), ("2023-2025", (2023, 2025))):
        d = allm[(allm.segment == seg) & allm.year.between(y0, y1)].copy()
        d["ly"] = np.log(d.cargo_kg); d["lx"] = np.log(d.seat_km); d["m"] = d.month.astype(str)
        f = smf.ols("ly ~ lx + C(m)", data=d).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        rows.append({"segment": seg, "period": per, "n": int(f.nobs), "b": f.params["lx"], "se": f.bse["lx"],
                     "lo": f.conf_int().loc["lx", 0], "hi": f.conf_int().loc["lx", 1]})
el = pd.DataFrame(rows)
el.round(4).to_csv(R / "elasticity.csv", index=False)
for _, r in el.iterrows():
    main[f"elast_{r.segment}_{r.period}"] = [round(r.b, 3), round(r.lo, 3), round(r.hi, 3)]

# 頑健性
rb = []
def add(name, h, val, ok, note=""):
    rb.append({"check": name, "hypothesis": h, "value": round(val, 3), "supported": bool(ok), "note": note})
add("主（座席キロ、2019年基準、重量）", "H1", main["H1_ratio"], main["H1_supported"])
r = drop("total", [4, 5], "cargo_kg", base=2018) / drop("total", [4, 5], "seat_km", base=2018)
add("基準を2018年", "H1", r, 0.7 <= r <= 1.3)
r = drop("total", [4, 5], "cargo_tkm") / drop("total", [4, 5], "seat_km")
add("トンキロで", "H1", r, 0.7 <= r <= 1.3)
r = main["ratio_total_apr_may_cargo_vs_flights"]
add("運航回数で割る", "H1", r, 0.7 <= r <= 1.3)
r = drop("total", [4, 5], "cargo_mail_kg") / drop("total", [4, 5], "seat_km")
add("郵便物を足す", "H1", r, 0.7 <= r <= 1.3)
for seg, nm in (("trunk", "幹線だけ"), ("local", "ローカル線だけ")):
    r = drop(seg, [4, 5], "cargo_kg") / drop(seg, [4, 5], "seat_km")
    add(nm, "H1", r, 0.7 <= r <= 1.3)
add("主（座席キロ、2019年基準、重量）", "H2", main["H2_ratio"], main["H2_supported"])
r = drop("intl", [4, 5, 6], "cargo_kg", base=2018) / drop("intl", [4, 5, 6], "seat_km", base=2018)
add("基準を2018年", "H2", r, r < 0.5)
r = drop("intl", [4, 5, 6], "cargo_tkm") / drop("intl", [4, 5, 6], "seat_km")
add("トンキロで", "H2", r, r < 0.5)
r = drop("intl", [4, 5, 6], "cargo_kg") / drop("intl", [4, 5, 6], "flights")
add("運航回数で割る", "H2", r, r < 0.5)
r = drop("intl", [4, 5, 6], "cargo_mail_kg") / drop("intl", [4, 5, 6], "seat_km")
add("郵便物を足す", "H2", r, r < 0.5)
r = drop("intl", list(range(4, 13)), "cargo_kg") / drop("intl", list(range(4, 13)), "seat_km")
add("2020年4〜12月で", "H2", r, r < 0.5)
c = 100 * (A.loc[("total", 2025), "cargo_kg"] / A.loc[("total", 2018), "cargo_kg"] - 1)
s = 100 * (A.loc[("total", 2025), "seat_km"] / A.loc[("total", 2018), "seat_km"] - 1)
add("基準を2018年（貨物の変化率）", "H3", c, c <= -10 and s >= -5, f"座席キロ {s:.1f}%")
c = 100 * (A.loc[("total", 2025), "cargo_tkm"] / A.loc[("total", 2019), "cargo_tkm"] - 1)
add("トンキロで（貨物の変化率）", "H3", c, c <= -10 and main["H3_seatkm_chg"] >= -5)
c = 100 * (A.loc[("total", 2025), "cargo_mail_kg"] / A.loc[("total", 2019), "cargo_mail_kg"] - 1)
add("郵便物を足す（変化率）", "H3", c, c <= -10 and main["H3_seatkm_chg"] >= -5)
c = 100 * (A.loc[("total", 2024), "cargo_kg"] / A.loc[("total", 2019), "cargo_kg"] - 1)
s = 100 * (A.loc[("total", 2024), "seat_km"] / A.loc[("total", 2019), "seat_km"] - 1)
add("2024年で（貨物の変化率）", "H3", c, c <= -10 and s >= -5, f"座席キロ {s:.1f}%")
t = 100 * (A.loc[("trunk", 2025), "cargo_kg"] / A.loc[("trunk", 2018), "cargo_kg"] - 1)
l = 100 * (A.loc[("local", 2025), "cargo_kg"] / A.loc[("local", 2018), "cargo_kg"] - 1)
add("基準を2018年（幹線とローカルの差）", "H4", abs(t - l), abs(t - l) <= 10, f"幹線 {t:.1f}%、ローカル {l:.1f}%")
t = 100 * (A.loc[("trunk", 2025), "cargo_tkm"] / A.loc[("trunk", 2019), "cargo_tkm"] - 1)
l = 100 * (A.loc[("local", 2025), "cargo_tkm"] / A.loc[("local", 2019), "cargo_tkm"] - 1)
add("トンキロで（幹線とローカルの差）", "H4", abs(t - l), abs(t - l) <= 10, f"幹線 {t:.1f}%、ローカル {l:.1f}%")
pd.DataFrame(rb).to_csv(R / "robustness.csv", index=False)
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
for k in ["H1_ratio", "H1_supported", "H2_ratio", "H2_supported", "H3_cargo_chg", "H3_seatkm_chg", "H3_supported", "H4_trunk", "H4_local", "H4_supported"]:
    print(k, main[k])
print(pd.DataFrame(rb).to_string())
print(el.round(3).to_string())
