"""問い直し（結果を見てから足した）：割合（分担率）の上がり下がりは、分子（船・鉄道の量）と分母（トラックの量）のどちらから来たのか。
割合 s = U ÷ (U + T)。年度 t0→t1 の変化を、
  分子の寄与 = s(U1, T0) − s(U0, T0)、分母の寄与 = s(U1, T1) − s(U1, T0) に分ける（足すと変化に一致）。
出力：results/requestion.json、results/share_decomp.csv"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
a = pd.read_csv(ROOT / "data" / "annual_fy.csv").set_index("fy")
a["unit"] = a.rail_cont_tkm + a.roro_tkm + a.contship_tkm
a["rail_ship"] = a.rail_tkm + a.ship_tkm


def s(u, t):
    return 100 * u / (u + t)


rows, out = [], {}
for nm, U, T in (("unit_vs_truckcomm", "unit", "truck_comm_tkm"), ("railship_vs_truck", "rail_ship", "truck_tkm")):
    for t0, t1 in ((2015, 2025), (2019, 2025), (2023, 2025), (2024, 2025), (2015, 2024)):
        u0, u1, tr0, tr1 = a.loc[t0, U], a.loc[t1, U], a.loc[t0, T], a.loc[t1, T]
        tot = s(u1, tr1) - s(u0, tr0)
        num_c = s(u1, tr0) - s(u0, tr0)
        den_c = s(u1, tr1) - s(u1, tr0)
        rows.append({"share": nm, "from": t0, "to": t1, "share_from": s(u0, tr0), "share_to": s(u1, tr1), "change_pt": tot,
                     "numerator_pt": num_c, "denominator_pt": den_c,
                     "numerator_chg_pct": 100 * (u1 / u0 - 1), "denominator_chg_pct": 100 * (tr1 / tr0 - 1)})
        key = f"{nm}_{t0}_{t1}"
        out[key + "_change_pt"] = round(tot, 2)
        out[key + "_numerator_pt"] = round(num_c, 2)
        out[key + "_denominator_pt"] = round(den_c, 2)
        out[key + "_numerator_chg_pct"] = round(100 * (u1 / u0 - 1), 2)
        out[key + "_denominator_chg_pct"] = round(100 * (tr1 / tr0 - 1), 2)
# 倍増の目安：ユニットロードの割合（分母に営業用トラック）を2倍にするには、トラックが変わらないとき量が何倍要るか
s23 = s(a.loc[2023, "unit"], a.loc[2023, "truck_comm_tkm"]) / 100
need = (2 * s23 / (1 - 2 * s23)) * a.loc[2023, "truck_comm_tkm"] / a.loc[2023, "unit"]
out["unit_share_2023"] = round(100 * s23, 2)
out["unit_multiple_needed_for_double_share_truck_fixed"] = round(float(need), 2)
pd.DataFrame(rows).round(3).to_csv(R / "share_decomp.csv", index=False)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
for k, v in out.items():
    print(k, v)
