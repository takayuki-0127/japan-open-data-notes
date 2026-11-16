"""03 分析：茅恒等式（3要因）の LMDI 分解、部門別、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
D = pd.read_csv(ROOT / "data" / "series.csv").set_index("year")
LAST = int(D.index.max())
def r(x, n=1): return float(round(float(x), n))
def L(a, b): return (a - b) / (np.log(a) - np.log(b)) if a != b else a

def lmdi(y0, y1, col="co2_energy_Mt"):
    c0, c1 = D.loc[y0, col], D.loc[y1, col]
    P0, P1 = D.loc[y0, "pop_k"], D.loc[y1, "pop_k"]
    g0, g1 = D.loc[y0, "gdp_real_bn"] / P0, D.loc[y1, "gdp_real_bn"] / P1
    i0, i1 = c0 / D.loc[y0, "gdp_real_bn"], c1 / D.loc[y1, "gdp_real_bn"]
    w = L(c1, c0)
    return {"変化_Mt": c1 - c0, "人口": w * np.log(P1 / P0), "1人あたりGDP": w * np.log(g1 / g0), "GDPあたり排出": w * np.log(i1 / i0)}

def seq(y0, y1, col="co2_energy_Mt"):
    c0 = D.loc[y0, col]; P0, P1 = D.loc[y0, "pop_k"], D.loc[y1, "pop_k"]
    G0, G1 = D.loc[y0, "gdp_real_bn"], D.loc[y1, "gdp_real_bn"]
    a = c0 * P1 / P0 - c0; b = c0 * G1 / G0 - c0 * P1 / P0; c = D.loc[y1, col] - c0 * G1 / G0
    return {"変化_Mt": D.loc[y1, col] - c0, "人口": a, "1人あたりGDP": b, "GDPあたり排出": c}

M = {}
e = D["co2_energy_Mt"]; peak = int(e.idxmax())
M["エネルギー起源CO2"] = {"1990_Mt": r(e[1990]), "山の年度": peak, "山_Mt": r(e[peak]), f"{LAST}_Mt": r(e[LAST]),
                       "山からの変化_%": r((e[LAST] / e[peak] - 1) * 100), "1990年度比_%": r((e[LAST] / e[1990] - 1) * 100)}
M["H1"] = {"判定": ("支持" if (2010 <= peak <= 2015 and (e[LAST] / e[peak] - 1) * 100 <= -20) else "外れ") + "（参考：推移の大きさを先に見ていた）"}
rows = []
for y0, y1 in [(1990, 2013), (2013, LAST)]:
    d = lmdi(y0, y1); rows.append({"期間": f"{y0}→{y1}", **{k: r(v, 2) for k, v in d.items()}})
K = pd.DataFrame(rows); K.to_csv(RES / "kaya_lmdi.csv", index=False)
d = lmdi(2013, LAST)
sh = {k: r(v / d["変化_Mt"] * 100) for k, v in d.items() if k != "変化_Mt"}
M["2013→最新_分解"] = {**{k: r(v, 1) for k, v in d.items()}, "割合_%": sh}
M["1990→2013_分解"] = {k: r(v, 1) for k, v in lmdi(1990, 2013).items()}
M["H2"] = {"GDPあたり排出の寄与_%": sh["GDPあたり排出"], "判定": "支持" if sh["GDPあたり排出"] > 100 else "外れ"}
M["H3"] = {"人口の寄与_%": sh["人口"], "判定": "支持" if sh["人口"] < 10 else "外れ"}
M["指標"] = {"人口_変化_%": r((D.loc[LAST, "pop_k"] / D.loc[2013, "pop_k"] - 1) * 100, 2),
            "実質GDP_変化_%": r((D.loc[LAST, "gdp_real_bn"] / D.loc[2013, "gdp_real_bn"] - 1) * 100, 2),
            "GDPあたり排出_変化_%": r(((e[LAST] / D.loc[LAST, "gdp_real_bn"]) / (e[2013] / D.loc[2013, "gdp_real_bn"]) - 1) * 100, 2)}
# 部門別（電気・熱配分後）
SEC = {"sec_industry_Mt": "産業", "sec_commercial_Mt": "業務その他", "sec_residential_Mt": "家庭", "sec_transport_Mt": "運輸", "sec_conversion_Mt": "エネルギー転換"}
sec = pd.DataFrame({lab: D[c] for c, lab in SEC.items()})
sec.round(2).to_csv(RES / "sector_series.csv")
ds = (sec.loc[LAST] - sec.loc[2013])
M["部門_2013→最新_Mt"] = {k: r(v) for k, v in ds.items()}
M["部門_2013→最新_%"] = {k: r((sec.loc[LAST, k] / sec.loc[2013, k] - 1) * 100) for k in sec.columns}
M["H4"] = {"減少がいちばん大きい部門": ds.idxmin(), "判定": "支持" if ds.idxmin() == "産業" else "外れ"}

# ---- 頑健性
rob = []
d19 = lmdi(2013, 2019); rob.append(("2013→2019年度", d19))
for lab, col in [("CO2 の合計（非エネルギー起源を含む）", "co2_total_Mt"), ("温室効果ガスの合計", "ghg_total_Mt")]:
    rob.append((lab, lmdi(2013, LAST, col)))
rob.append(("順番を決めた単純な分け方", seq(2013, LAST)))
RB = pd.DataFrame([{"変えたこと": lab, **{k: r(v, 2) for k, v in dd.items()},
                    "GDPあたり排出の割合_%": r(dd["GDPあたり排出"] / dd["変化_Mt"] * 100), "人口の割合_%": r(dd["人口"] / dd["変化_Mt"] * 100)} for lab, dd in rob])
RB["H2"] = np.where(RB["GDPあたり排出の割合_%"] > 100, "支持", "外れ"); RB["H3"] = np.where(RB["人口の割合_%"] < 10, "支持", "外れ")
RB.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {row["変えたこと"]: {k: row[k] for k in RB.columns if k != "変えたこと"} for _, row in RB.iterrows()}

# ---- 問い直し（結果を見てから足した）：減った分は、電気の使用に伴う排出か、燃料を直接燃やす排出か。燃料では何が減ったか
el = D["electricity_alloc_Mt"]
M["問い直し"] = {"電気の使用に伴う排出_2013_Mt": r(el[2013]), f"電気の使用に伴う排出_{LAST}_Mt": r(el[LAST]),
               "電気の使用に伴う排出の変化_Mt": r(el[LAST] - el[2013]), "エネルギー起源CO2の変化_Mt": r(e[LAST] - e[2013]),
               "電気の分の割合_%": r((el[LAST] - el[2013]) / (e[LAST] - e[2013]) * 100)}
fu = pd.DataFrame({"石炭・石炭製品": D.fuel_coal_Mt + D.fuel_coalprod_Mt, "石油（原油・石油製品）": D.fuel_crude_Mt + D.fuel_oilprod_Mt,
                   "ガス（天然ガス・都市ガス）": D.fuel_natgas_Mt + D.fuel_citygas_Mt})
fu.round(2).to_csv(RES / "fuel_series.csv")
M["問い直し"]["燃料_2013→最新_Mt"] = {k: r(fu.loc[LAST, k] - fu.loc[2013, k]) for k in fu.columns}
M["問い直し"]["燃料_2013→最新_%"] = {k: r((fu.loc[LAST, k] / fu.loc[2013, k] - 1) * 100) for k in fu.columns}

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps(M, ensure_ascii=False, indent=1))
