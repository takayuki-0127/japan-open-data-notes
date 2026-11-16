"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "rd_by_sector.csv")
R = d.pivot(index="year", columns="sector", values="researchers")
E = d.pivot(index="year", columns="sector", values="expenditure_mil")
S = d.pivot(index="year", columns="sector", values="staff_total")
PER = E / R * 1e6 / 1e4  # 研究者1人当たり研究費（万円）
R.to_csv(RES / "researchers_by_sector.csv"); E.to_csv(RES / "expenditure_by_sector.csv"); PER.round(3).to_csv(RES / "per_researcher_by_sector.csv")
SEC = ["business", "university", "public", "nonprofit", "total"]
def comp(X, a, b):
    return {s: dict(start=r3(X.loc[a, s].mean()), end=r3(X.loc[b, s].mean()), dlog=r3(100 * np.log(X.loc[b, s].mean() / X.loc[a, s].mean()))) for s in X.columns if X[s].notna().all()}
A, B = [2002, 2003, 2004], [2023, 2024, 2025]
out = {"researchers": comp(R[SEC], A, B), "expenditure": comp(E[SEC], A, B), "per_researcher_10k_yen": comp(PER[SEC], A, B)}
rr, ee = out["researchers"], out["expenditure"]
out["H1_verdict"] = "支持" if rr["business"]["dlog"] > rr["university"]["dlog"] else "外れ"
out["H2_verdict"] = "支持" if rr["public"]["dlog"] <= 0 else "外れ"
out["H3_verdict"] = "支持" if ee["business"]["dlog"] > ee["university"]["dlog"] else "外れ"
out["H4_verdict"] = "支持" if out["per_researcher_10k_yen"]["university"]["dlog"] <= 5 else "外れ"
tot_r = R.loc[B, "total"].mean() - R.loc[A, "total"].mean(); tot_e = E.loc[B, "total"].mean() - E.loc[A, "total"].mean()
out["contrib_researchers_pct"] = {s: r3(100 * (R.loc[B, s].mean() - R.loc[A, s].mean()) / tot_r) for s in SEC[:4]}
out["contrib_expenditure_pct"] = {s: r3(100 * (E.loc[B, s].mean() - E.loc[A, s].mean()) / tot_e) for s in SEC[:4]}
rob = []
for lab, a, b in [("R1 終点を2018〜20年調査", A, [2018, 2019, 2020]), ("R2 始点を2008〜10年調査", [2008, 2009, 2010], B)]:
    r_, e_, p_ = comp(R[SEC], a, b), comp(E[SEC], a, b), comp(PER[SEC], a, b)
    rob.append(dict(spec=lab, res_business=r_["business"]["dlog"], res_university=r_["university"]["dlog"], res_public=r_["public"]["dlog"],
                    exp_business=e_["business"]["dlog"], exp_university=e_["university"]["dlog"], per_univ=p_["university"]["dlog"]))
s_ = comp(S[SEC], A, B)
rob.append(dict(spec="R3 研究関係従業者数（総数）で", res_business=s_["business"]["dlog"], res_university=s_["university"]["dlog"], res_public=s_["public"]["dlog"]))
U = ["univ_national", "univ_public", "univ_private"]
ru, eu, pu = comp(R[U], A, B), comp(E[U], A, B), comp(PER[U], A, B)
for u, lab in zip(U, ["国立", "公立", "私立"]):
    rob.append(dict(spec=f"R4 大学等_{lab}", res=ru[u]["dlog"], exp=eu[u]["dlog"], per=pu[u]["dlog"]))
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(PER[SEC].round(0).to_string())
