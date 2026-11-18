"""主な分析：機関別の割合、ユニットロードの量、2024年4月前後の前年同月比、1トンあたりの距離、頑健性。
出力：results/main.json、results/share_fy.csv、results/unitload_fy.csv、results/yoy_monthly.csv、results/distance_fy.csv、results/robustness.csv"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
a = pd.read_csv(ROOT / "data" / "annual_fy.csv").set_index("fy")
mo = pd.read_csv(ROOT / "data" / "monthly.csv")
main = {}

# ---- 割合（トンキロ・トン、分母2通り）----
def shares(truck_col, unit):
    tr = a[f"{truck_col}_{unit}"]; rl = a[f"rail_{unit}"]; sh = a[f"ship_{unit}"]
    tot = tr + rl + sh
    return pd.DataFrame({"truck": 100 * tr / tot, "rail": 100 * rl / tot, "ship": 100 * sh / tot,
                         "rail_ship": 100 * (rl + sh) / tot, "total": tot})

S = {}
for tc, nm in (("truck", "all"), ("truck_comm", "comm")):
    for unit in ("tkm", "ton"):
        if unit == "ton" and a["rail_ton"].isna().any():
            d = shares(tc, unit).loc[2017:]
        else:
            d = shares(tc, unit)
        S[(nm, unit)] = d
share = []
for (nm, unit), d in S.items():
    t = d.reset_index(); t["truck_def"] = nm; t["unit"] = unit; share.append(t)
pd.concat(share).round(3).to_csv(R / "share_fy.csv", index=False)
M = S[("all", "tkm")]
for fy in (2015, 2019, 2023, 2024, 2025):
    for k in ("truck", "rail", "ship", "rail_ship"):
        main[f"share_{k}_{fy}"] = round(float(M.loc[fy, k]), 2)
    main[f"total_tkm_{fy}"] = round(float(M.loc[fy, "total"]))
main["share_rail_ship_diff_2025_2015"] = round(float(M.loc[2025, "rail_ship"] - M.loc[2015, "rail_ship"]), 2)
main["H1_supported"] = bool(main["share_rail_ship_diff_2025_2015"] < 1)
main["share_rail_ship_max"] = round(float(M["rail_ship"].max()), 2)
main["share_rail_ship_max_fy"] = int(M["rail_ship"].idxmax())
main["share_rail_ship_min"] = round(float(M["rail_ship"].min()), 2)
main["share_rail_ship_min_fy"] = int(M["rail_ship"].idxmin())
for k in ("truck_tkm", "truck_comm_tkm", "rail_tkm", "rail_cont_tkm", "ship_tkm", "roro_tkm", "contship_tkm"):
    main[f"chg_{k}_2025_vs_2015"] = round(100 * (a.loc[2025, k] / a.loc[2015, k] - 1), 2)
    main[f"chg_{k}_2025_vs_2019"] = round(100 * (a.loc[2025, k] / a.loc[2019, k] - 1), 2)
    main[f"chg_{k}_2025_vs_2023"] = round(100 * (a.loc[2025, k] / a.loc[2023, k] - 1), 2)
    main[f"chg_{k}_2025_vs_2024"] = round(100 * (a.loc[2025, k] / a.loc[2024, k] - 1), 2)
    main[f"{k}_2015"] = round(float(a.loc[2015, k]), 1); main[f"{k}_2025"] = round(float(a.loc[2025, k]), 1)
    main[f"{k}_2023"] = round(float(a.loc[2023, k]), 1)

# ---- ユニットロード（鉄道コンテナ＋RORO船＋コンテナ専用船）----
u = pd.DataFrame({"rail_cont": a.rail_cont_tkm, "roro": a.roro_tkm, "contship": a.contship_tkm})
u["unitload"] = u.sum(axis=1)
u["idx2023"] = 100 * u.unitload / u.loc[2023, "unitload"]
u["double_pace_from2023"] = [100 * 2 ** ((fy - 2023) / 10) for fy in u.index]
u["share_in_unit_plus_truckcomm"] = 100 * u.unitload / (u.unitload + a.truck_comm_tkm)
u["share_in_all"] = 100 * u.unitload / (a.truck_tkm + a.rail_tkm + a.ship_tkm)
u["roro_share_in_unit"] = 100 * u.roro / u.unitload
u.reset_index().round(3).to_csv(R / "unitload_fy.csv", index=False)
cagr = 100 * ((u.loc[2025, "unitload"] / u.loc[2023, "unitload"]) ** 0.5 - 1)
main["unit_tkm_2015"] = round(float(u.loc[2015, "unitload"]), 1)
main["unit_tkm_2019"] = round(float(u.loc[2019, "unitload"]), 1)
main["unit_tkm_2023"] = round(float(u.loc[2023, "unitload"]), 1)
main["unit_tkm_2025"] = round(float(u.loc[2025, "unitload"]), 1)
main["unit_cagr_2023_2025"] = round(cagr, 2)
main["double_pace_cagr"] = round(100 * (2 ** 0.1 - 1), 2)
main["unit_idx_2025"] = round(float(u.loc[2025, "idx2023"]), 1)
main["double_pace_idx_2025"] = round(float(u.loc[2025, "double_pace_from2023"]), 1)
main["H2_supported"] = bool(cagr < 100 * (2 ** 0.1 - 1))
main["unit_chg_2025_vs_2015"] = round(100 * (u.loc[2025, "unitload"] / u.loc[2015, "unitload"] - 1), 2)
for fy in (2015, 2019, 2023, 2025):
    main[f"unit_share_in_unit_plus_truckcomm_{fy}"] = round(float(u.loc[fy, "share_in_unit_plus_truckcomm"]), 2)
    main[f"unit_share_in_all_{fy}"] = round(float(u.loc[fy, "share_in_all"]), 2)
    main[f"roro_share_in_unit_{fy}"] = round(float(u.loc[fy, "roro_share_in_unit"]), 1)
    main[f"rail_cont_tkm_{fy}"] = round(float(u.loc[fy, "rail_cont"]), 1)
    main[f"roro_tkm_{fy}"] = round(float(u.loc[fy, "roro"]), 1)

# ---- 月の前年同月比 ----
mo = mo.sort_values(["year", "month"]).reset_index(drop=True)
V = ["truck_tkm", "truck_comm_tkm", "rail_tkm", "rail_cont_tkm", "ship_comm_tkm"]
for v in V:
    mo[v + "_yoy"] = 100 * (mo[v] / mo[v].shift(12) - 1)
y = mo.dropna(subset=[V[0] + "_yoy"]).copy()
y["period"] = np.where((y.year * 100 + y.month) >= 202404, "after", "before")
cols = ["year", "month", "fy", "period"] + [v + "_yoy" for v in V]
y[cols].round(3).to_csv(R / "yoy_monthly.csv", index=False)
w = y[(y.year * 100 + y.month) >= 202204]
for v in V:
    for p in ("before", "after"):
        main[f"yoy_mean_{v}_{p}"] = round(float(w[w.period == p][v + "_yoy"].mean()), 2)
for v in ("rail_cont_tkm", "ship_comm_tkm", "rail_tkm"):
    main[f"corr_truckcomm_{v}_2022_2026"] = round(float(w["truck_comm_tkm_yoy"].corr(w[v + "_yoy"])), 3)
    aa = w[w.period == "after"]
    main[f"corr_truckcomm_{v}_after"] = round(float(aa["truck_comm_tkm_yoy"].corr(aa[v + "_yoy"])), 3)
main["H3_supported"] = bool(main["corr_truckcomm_rail_cont_tkm_2022_2026"] > -0.3 and main["corr_truckcomm_ship_comm_tkm_2022_2026"] > -0.3)
main["n_months_corr"] = int(len(w))
# 2024年4月〜2025年3月・2025年4月〜2026年3月 の年度の伸び
for fy in (2023, 2024, 2025):
    for k in ("truck_comm_tkm", "rail_cont_tkm", "ship_tkm", "roro_tkm"):
        main[f"fy_growth_{k}_{fy}"] = round(100 * (a.loc[fy, k] / a.loc[fy - 1, k] - 1), 2)

# ---- 1トンあたりの距離（km）----
dist = pd.DataFrame({
    "truck_comm": 1000 * a.truck_comm_tkm / a.truck_comm_ton,
    "truck_all": 1000 * a.truck_tkm / a.truck_ton,
    "rail_cont": 1000 * a.rail_cont_tkm / a.rail_cont_ton,
    "ship": 1000 * a.ship_tkm / a.ship_ton,
    "roro": 1000 * a.roro_tkm / a.roro_ton,
    "contship": 1000 * a.contship_tkm / a.contship_ton,
})
dist.reset_index().round(2).to_csv(R / "distance_fy.csv", index=False)
for k in dist.columns:
    for fy in (2015, 2017, 2019, 2023, 2024, 2025):
        if not np.isnan(dist.loc[fy, k]):
            main[f"dist_{k}_{fy}"] = round(float(dist.loc[fy, k]), 1)
    main[f"dist_chg_{k}_2025_vs_2023"] = round(100 * (dist.loc[2025, k] / dist.loc[2023, k] - 1), 2)
main["H4_supported"] = bool(main["dist_chg_truck_comm_2025_vs_2023"] <= -3 and main["dist_chg_rail_cont_2025_vs_2023"] > -3
                            and main["dist_chg_ship_2025_vs_2023"] > -3)

# ---- 頑健性 ----
rb = []
def add(name, h, val, ok, note=""):
    rb.append({"check": name, "hypothesis": h, "value": round(float(val), 3), "supported": bool(ok), "note": note})
add("主（トンキロ、トラック全体、2015年度比）", "H1", main["share_rail_ship_diff_2025_2015"], main["H1_supported"])
d = S[("all", "ton")]; v = d.loc[2025, "rail_ship"] - d.loc[2017, "rail_ship"]
add("トンで（2017年度比。鉄道のトンが2017年度から）", "H1", v, v < 1, f"{d.loc[2017,'rail_ship']:.2f}%→{d.loc[2025,'rail_ship']:.2f}%")
d = S[("comm", "tkm")]; v = d.loc[2025, "rail_ship"] - d.loc[2015, "rail_ship"]
add("分母を営業用トラックだけ", "H1", v, v < 1, f"{d.loc[2015,'rail_ship']:.2f}%→{d.loc[2025,'rail_ship']:.2f}%")
v = M.loc[2025, "rail_ship"] - M.loc[2019, "rail_ship"]
add("基準を2019年度", "H1", v, v < 1, f"{M.loc[2019,'rail_ship']:.2f}%→{M.loc[2025,'rail_ship']:.2f}%")
yy = [fy for fy in M.index if fy not in (2020, 2021)]
b = np.polyfit(yy, M.loc[yy, "rail_ship"].values, 1)[0]
add("2020・2021年度を除いた傾き（ポイント／年）", "H1", b, b * 10 < 1, "10年分に直して1ポイント未満なら支持")
add("主（2023→2025年度の年率）", "H2", cagr, main["H2_supported"])
c2 = 100 * ((u.loc[2025, "unitload"] / u.loc[2019, "unitload"]) ** (1 / 6) - 1)
add("基準を2019年度（年率）", "H2", c2, c2 < 7.18)
c3 = 100 * ((u.loc[2025, "unitload"] / u.loc[2015, "unitload"]) ** (1 / 10) - 1)
add("基準を2015年度（年率）", "H2", c3, c3 < 7.18)
c4 = 100 * ((u.loc[2025, "roro"] / u.loc[2023, "roro"]) ** 0.5 - 1)
add("RORO船だけ（2023→2025年度の年率）", "H2", c4, c4 < 7.18)
c5 = 100 * ((u.loc[2025, "rail_cont"] / u.loc[2023, "rail_cont"]) ** 0.5 - 1)
add("鉄道コンテナだけ（2023→2025年度の年率）", "H2", c5, c5 < 7.18)
add("主（2022年4月〜2026年3月、鉄道コンテナ）", "H3", main["corr_truckcomm_rail_cont_tkm_2022_2026"], main["corr_truckcomm_rail_cont_tkm_2022_2026"] > -0.3)
add("主（2022年4月〜2026年3月、内航営業用）", "H3", main["corr_truckcomm_ship_comm_tkm_2022_2026"], main["corr_truckcomm_ship_comm_tkm_2022_2026"] > -0.3)
for v_ in ("rail_cont_tkm", "ship_comm_tkm"):
    add(f"2024年4月以降だけ（{'鉄道コンテナ' if v_ == 'rail_cont_tkm' else '内航営業用'}）", "H3", main[f"corr_truckcomm_{v_}_after"], main[f"corr_truckcomm_{v_}_after"] > -0.3)
ww = y.copy()
for v_ in ("rail_cont_tkm", "ship_comm_tkm"):
    cc = ww["truck_tkm_yoy"].corr(ww[v_ + "_yoy"])
    add(f"トラック全体・2021年4月から（{'鉄道コンテナ' if v_ == 'rail_cont_tkm' else '内航営業用'}）", "H3", cc, cc > -0.3)
add("主（営業用トラック・鉄道コンテナ・内航、2023→2025年度）", "H4", main["dist_chg_truck_comm_2025_vs_2023"], main["H4_supported"],
    f"鉄道コンテナ {main['dist_chg_rail_cont_2025_vs_2023']:.1f}%、内航 {main['dist_chg_ship_2025_vs_2023']:.1f}%")
v = 100 * (dist.loc[2025, "truck_comm"] / dist.loc[2019, "truck_comm"] - 1)
v2 = 100 * (dist.loc[2025, "rail_cont"] / dist.loc[2019, "rail_cont"] - 1); v3 = 100 * (dist.loc[2025, "ship"] / dist.loc[2019, "ship"] - 1)
add("基準を2019年度", "H4", v, v <= -3 and v2 > -3 and v3 > -3, f"鉄道コンテナ {v2:.1f}%、内航 {v3:.1f}%")
v = 100 * (dist.loc[2025, "truck_all"] / dist.loc[2023, "truck_all"] - 1); v4 = 100 * (dist.loc[2025, "roro"] / dist.loc[2023, "roro"] - 1)
add("トラック全体・RORO船で", "H4", v, v <= -3 and v4 > -3, f"RORO船 {v4:.1f}%")
pd.DataFrame(rb).to_csv(R / "robustness.csv", index=False)
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(pd.DataFrame(rb).to_string())
for k in sorted(main):
    if k.startswith(("share_", "unit_", "H", "corr", "yoy_mean", "dist_", "double", "fy_growth")):
        print(k, main[k])
