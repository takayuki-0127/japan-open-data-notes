"""03_analysis.py : 組織率の低下を、組合員数と雇用者数、パートとパート以外に分ける（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
t = pd.read_csv(ROOT / "data" / "union_total_part.csv").set_index("year")
s = pd.read_csv(ROOT / "data" / "union_members_by_firm_size.csv").pivot_table(index="year", columns="size", values="members")


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


emp = t.employees_10k * 1e4
d = pd.DataFrame(index=t.index)
d["density_pub"] = t.density_pub
d["density_unit"] = t.unit_members / emp * 100
d["density_single"] = t.single_members / emp * 100
d["part_members"] = t.part_members
d["part_emp"] = t.part_emp_new_10k * 1e4
d["part_density"] = t.part_members / d.part_emp * 100
d["ft_members"] = t.unit_members - t.part_members
d["ft_emp"] = emp - d.part_emp
d["ft_density"] = d.ft_members / d.ft_emp * 100
d["part_share_emp"] = d.part_emp / emp * 100
d["part_share_members"] = t.part_members / t.unit_members * 100
d["part_emp_old"] = t.part_emp_old_10k * 1e4
d["ft_density_olddef"] = (t.unit_members - t.part_members) / (emp - d.part_emp_old) * 100
d["unit_members"] = t.unit_members
d["single_members"] = t.single_members
d["employees"] = emp
dd = d.loc[2010:]
dd.round(4).to_csv(RES / "density_decomposition_series.csv")
main = {}
Y0, Y1 = 2013, 2025


def dec(y0, y1, mem="unit_members"):
    dm = np.log(d.loc[y1, mem] / d.loc[y0, mem])
    de = np.log(d.loc[y1, "employees"] / d.loc[y0, "employees"])
    return {"dlog_density": r(dm - de, 4), "dlog_members": r(dm, 4), "dlog_employees": r(de, 4),
            "share_denominator": r(de / (de - dm), 3) if (de - dm) != 0 else None}


main["levels"] = {int(y): {k: r(d.loc[y, k], 3) for k in ["density_pub", "density_unit", "part_density", "ft_density", "part_share_emp", "part_share_members"]}
                  for y in [2013, 2019, 2025]}
main["counts"] = {int(y): {"unit_members": r(d.loc[y, "unit_members"], 0), "single_members": r(d.loc[y, "single_members"], 0), "part_members": r(d.loc[y, "part_members"], 0),
                           "ft_members": r(d.loc[y, "ft_members"], 0), "employees_10k": r(t.loc[y, "employees_10k"], 0), "part_emp_10k": r(t.loc[y, "part_emp_new_10k"], 0)} for y in [2013, 2019, 2025]}
main["H1"] = {"part_members_ratio": r(d.loc[Y1, "part_members"] / d.loc[Y0, "part_members"], 3), "density_pub_2013": r(d.loc[Y0, "density_pub"], 1), "density_pub_2025": r(d.loc[Y1, "density_pub"], 1)}
main["H2"] = {"ft_change_pt": r(d.loc[Y1, "ft_density"] - d.loc[Y0, "ft_density"], 2), "all_unit_change_pt": r(d.loc[Y1, "density_unit"] - d.loc[Y0, "density_unit"], 2),
              "part_change_pt": r(d.loc[Y1, "part_density"] - d.loc[Y0, "part_density"], 2)}
main["H3"] = dec(Y0, Y1)
main["dec_single_2013_2025"] = dec(Y0, Y1, "single_members")
main["dec_2013_2019"] = dec(2013, 2019)
main["ft_members_change_pct"] = r((d.loc[Y1, "ft_members"] / d.loc[Y0, "ft_members"] - 1) * 100, 2)
main["ft_emp_change_pct"] = r((d.loc[Y1, "ft_emp"] / d.loc[Y0, "ft_emp"] - 1) * 100, 2)
main["part_emp_change_pct"] = r((d.loc[Y1, "part_emp"] / d.loc[Y0, "part_emp"] - 1) * 100, 2)
main["record_low_pub"] = {"min_year": int(d.density_pub.idxmin()), "min": r(d.density_pub.min(), 1)}
# 規模別
sizes = ["5000人以上", "1000〜4999人", "500〜999人", "300〜499人", "100〜299人", "30〜99人", "29人以下", "民営その他", "民営計", "民営以外"]
sz = pd.DataFrame({"m2013": s.loc[Y0, sizes], "m2025": s.loc[Y1, sizes]})
sz["chg_pct"] = (sz.m2025 / sz.m2013 - 1) * 100
large = s.loc[[Y0, Y1], ["5000人以上", "1000〜4999人"]].sum(axis=1)
small = s.loc[[Y0, Y1], ["500〜999人", "300〜499人", "100〜299人", "30〜99人", "29人以下"]].sum(axis=1)
sz.round(2).to_csv(RES / "members_by_firm_size_2013_2025.csv")
main["size"] = {k: {"m2013": r(sz.loc[k, "m2013"], 0), "m2025": r(sz.loc[k, "m2025"], 0), "chg_pct": r(sz.loc[k, "chg_pct"], 1)} for k in sizes}
main["H4"] = {"large_1000plus_chg_pct": r((large.loc[Y1] / large.loc[Y0] - 1) * 100, 2), "under1000_chg_pct": r((small.loc[Y1] / small.loc[Y0] - 1) * 100, 2),
              "large_share_private_2013": r(large.loc[Y0] / s.loc[Y0, "民営計"] * 100, 1), "large_share_private_2025": r(large.loc[Y1] / s.loc[Y1, "民営計"] * 100, 1)}
ss = s.loc[2000:, sizes]
ss.to_csv(RES / "members_by_firm_size_series.csv")
# 問い直し：パートの雇用者の割合が2013年のままなら
w0 = d.loc[Y0, "part_share_emp"] / 100
cf = (w0 * d.part_density + (1 - w0) * d.ft_density).loc[2013:]
q = pd.DataFrame({"actual_unit": d.density_unit.loc[2013:], "fixed_part_share_2013": cf, "part_share_emp": d.part_share_emp.loc[2013:]})
q.round(4).to_csv(RES / "requestion_fixed_part_share.csv")
main["requestion"] = {"actual_2025": r(q.loc[2025, "actual_unit"], 2), "fixed_2025": r(q.loc[2025, "fixed_part_share_2013"], 2), "actual_2013": r(q.loc[2013, "actual_unit"], 2),
                      "part_share_emp_2013": r(d.loc[2013, "part_share_emp"], 2), "part_share_emp_2025": r(d.loc[2025, "part_share_emp"], 2)}
# 頑健性
rb = [
    {"check": "主：2013→2025、単位組合員、パート新定義", "all_change_pt": main["H2"]["all_unit_change_pt"], "ft_change_pt": main["H2"]["ft_change_pt"], "share_denominator": main["H3"]["share_denominator"]},
    {"check": "1 期間を2013→2019年に", "all_change_pt": r(d.loc[2019, "density_unit"] - d.loc[2013, "density_unit"], 2), "ft_change_pt": r(d.loc[2019, "ft_density"] - d.loc[2013, "ft_density"], 2), "share_denominator": main["dec_2013_2019"]["share_denominator"]},
    {"check": "2 公表の組織率（単一組合員）で分解", "all_change_pt": r(d.loc[Y1, "density_single"] - d.loc[Y0, "density_single"], 2), "ft_change_pt": None, "share_denominator": main["dec_single_2013_2025"]["share_denominator"]},
    {"check": "3 パートの雇用者を旧定義（週35時間未満）に", "all_change_pt": main["H2"]["all_unit_change_pt"], "ft_change_pt": r(d.loc[Y1, "ft_density_olddef"] - d.loc[Y0, "ft_density_olddef"], 2), "share_denominator": None},
    {"check": "3' 旧定義で2010→2025年", "all_change_pt": r(d.loc[2025, "density_unit"] - d.loc[2010, "density_unit"], 2), "ft_change_pt": r(d.loc[2025, "ft_density_olddef"] - d.loc[2010, "ft_density_olddef"], 2), "share_denominator": dec(2010, 2025)["share_denominator"]},
]
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
main["employees_2021_2022"] = [r(t.loc[2021, "employees_10k"], 0), r(t.loc[2022, "employees_10k"], 0)]
main["judgement"] = {"H1": "支持" if main["H1"]["part_members_ratio"] >= 1.5 and d.loc[Y1, "density_pub"] < d.loc[Y0, "density_pub"] else "外れ",
                     "H2": "支持" if main["H2"]["ft_change_pt"] < main["H2"]["all_unit_change_pt"] else "外れ",
                     "H3": "支持" if (main["H3"]["share_denominator"] or 0) >= 0.5 else "外れ",
                     "H4": "支持" if main["H4"]["under1000_chg_pct"] < main["H4"]["large_1000plus_chg_pct"] else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=0, sort_keys=True))
