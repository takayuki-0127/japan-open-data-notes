"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "rooms_national.csv")
U = d.pivot(index="year", columns="group", values="used_rooms"); O = d.pivot(index="year", columns="group", values="occupancy_pct"); S = d.pivot(index="year", columns="group", values="supply_rooms")
O.round(3).to_csv(RES / "occupancy.csv"); U.to_csv(RES / "used_rooms.csv"); S.round(0).to_csv(RES / "supply_rooms.csv")
def decomp(g, a, b):
    du = 100 * np.log(U.loc[b, g] / U.loc[a, g]); ds = 100 * np.log(S.loc[b, g] / S.loc[a, g]); do = 100 * np.log(O.loc[b, g] / O.loc[a, g])
    return dict(used=r3(du), supply=r3(ds), occupancy=r3(do), supply_share=r3(100 * ds / du) if du != 0 else None, occ_pt=r3(O.loc[b, g] - O.loc[a, g]))
TY = ["旅館", "リゾートホテル", "ビジネスホテル", "シティホテル", "簡易宿所", "会社・団体の宿泊所"]
out = {"occupancy_all": {int(y): r3(v) for y, v in O["all"].items()}}
out["H1"] = dict(y2019=r3(O.loc[2019, "all"]), y2025=r3(O.loc[2025, "all"]))
out["H1_verdict"] = "支持" if O.loc[2025, "all"] > O.loc[2019, "all"] else "外れ"
out["H2"] = decomp("all", 2019, 2025)
out["H2_verdict"] = "支持" if out["H2"]["used"] > 0 and out["H2"]["supply"] >= out["H2"]["used"] / 2 else "外れ"
out["H3"] = dict(city=r3(O.loc[2025, "シティホテル"]), business=r3(O.loc[2025, "ビジネスホテル"]), ryokan=r3(O.loc[2025, "旅館"]))
out["H3_verdict"] = "支持" if min(O.loc[2025, "シティホテル"], O.loc[2025, "ビジネスホテル"]) - O.loc[2025, "旅館"] >= 15 else "外れ"
out["H4"] = decomp("all", 2012, 2019)
out["H4_verdict"] = "支持" if out["H4"]["occupancy"] >= out["H4"]["used"] / 2 else "外れ"
out["by_type_2019_2025"] = {t: decomp(t, 2019, 2025) for t in TY}
out["by_type_2012_2019"] = {t: decomp(t, 2012, 2019) for t in TY if not np.isnan(S.loc[2012, t])}
rob = [dict(spec="R1 2018→2024年", **decomp("all", 2018, 2024)),
       dict(spec="R2 従業者10人以上の施設（2019→2025年）", **decomp("emp10plus", 2019, 2025)),
       dict(spec="R3 H4 を2015→2019年で", **decomp("all", 2015, 2019)),
       dict(spec="R4 簡易宿所と会社・団体の宿泊所を除く（2019→2025年）", **(lambda: (lambda u0, u1, s0, s1: dict(used=r3(100*np.log(u1/u0)), supply=r3(100*np.log(s1/s0)), occ2019=r3(100*u0/s0), occ2025=r3(100*u1/s1)))(
           U.loc[2019, TY[:4]].sum(), U.loc[2025, TY[:4]].sum(), S.loc[2019, TY[:4]].sum(), S.loc[2025, TY[:4]].sum()))()),
       dict(spec="R5 H4 を従業者10人以上で（2012→2019年）", **decomp("emp10plus", 2012, 2019))]
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "occupancy_all"}, ensure_ascii=False, indent=0))
