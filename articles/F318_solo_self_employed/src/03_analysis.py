"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "lfs_status.csv")
d["solo_share"] = 100 * d.solo / d.employed
d["self_fam"] = d.self_employed + d.family
P = {s: d[d.sex == s].set_index("year") for s in ["total", "male", "female"]}
P["total"][["employed", "self_employed", "with_employees", "solo", "family", "employees", "solo_share"]].to_csv(RES / "total_by_year.csv")
def avg(s, col, ys): return float(P[s].loc[ys, col].mean())
def dl(s, col, a, b): return r3(100 * np.log(avg(s, col, b) / avg(s, col, a)))
A, B = [2000, 2001, 2002], [2023, 2024, 2025]
out = {"solo": {s: dict(start=r3(avg(s, "solo", A)), end=r3(avg(s, "solo", B)), dlog=dl(s, "solo", A, B)) for s in P}}
out["H1_verdict"] = "支持" if out["solo"]["total"]["dlog"] < 0 else "外れ"
out["share"] = dict(start=r3(avg("total", "solo_share", A)), end=r3(avg("total", "solo_share", B)))
out["share"]["change_pt"] = r3(out["share"]["end"] - out["share"]["start"])
out["H2_verdict"] = "支持" if out["share"]["change_pt"] < 0 else "外れ"
out["H3_verdict"] = "支持" if out["solo"]["female"]["dlog"] < out["solo"]["male"]["dlog"] else "外れ"
C = [2013, 2014, 2015]
out["H4"] = {s: dict(start=r3(avg(s, "solo", C)), end=r3(avg(s, "solo", B)), dlog=dl(s, "solo", C, B)) for s in P}
out["H4_verdict"] = "支持" if out["H4"]["total"]["dlog"] > 0 else "外れ"
out["employed_dlog"] = dl("total", "employed", A, B); out["employees_dlog"] = dl("total", "employees", A, B)
out["with_employees_dlog"] = dl("total", "with_employees", A, B)
rob = [dict(spec="R1 始点を1995〜97年平均", solo_dlog=dl("total", "solo", [1995, 1996, 1997], B)),
       dict(spec="R2 自営業主全体（雇有業主を含む）", dlog=dl("total", "self_employed", A, B)),
       dict(spec="R3 H4 の始点を2016〜18年平均", solo_dlog=dl("total", "solo", [2016, 2017, 2018], B), female=dl("female", "solo", [2016, 2017, 2018], B), male=dl("male", "solo", [2016, 2017, 2018], B)),
       dict(spec="R4 自営業主＋家族従業者", dlog=dl("total", "self_fam", A, B))]
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
print(pd.DataFrame({s: P[s].loc[2010:2025, "solo"] for s in P}).to_string())
