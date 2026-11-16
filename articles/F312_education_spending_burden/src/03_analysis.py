"""H1〜H4 と頑健性。結果は results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"; RES.mkdir(exist_ok=True)
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "edu_by_age.csv")
cpi = pd.read_csv(D / "cpi_edu_annual.csv").set_index("year")
W = d.pivot_table(index=["age", "year"], columns="item", values="amount")
W["share_edu"] = 100 * W.education / W.consumption
W["share_cram_in_edu"] = 100 * W.cram / W.education
W["share_tuition_in_edu"] = 100 * W.tuition / W.education
yrs = W.index.get_level_values("year")
W["real_edu"] = W.education / cpi.loc[yrs, "cpi_edu"].values * 100
W["real_edu_per_child"] = W.real_edu / W.children
W["nom_edu_per_child"] = W.education / W.children
W["real_edu_per_person"] = W.real_edu / W.hh_size
W.round(4).to_csv(RES / "panel_by_age_year.csv")
def avg(age, col, ys): return float(W.loc[[(age, y) for y in ys], col].mean())
S, E = [2002, 2003, 2004], [2023, 2024, 2025]
def run(age, S=S, E=E):
    o = {}
    o["share_edu"] = [r3(avg(age, "share_edu", S)), r3(avg(age, "share_edu", E))]
    o["share_edu_change_pt"] = r3(o["share_edu"][1] - o["share_edu"][0])
    for c in ["real_edu_per_child", "nom_edu_per_child", "real_edu_per_person", "real_edu", "education", "children"]:
        o[c + "_dlog"] = r3(100 * np.log(avg(age, c, E) / avg(age, c, S)))
    o["children"] = [r3(avg(age, "children", S)), r3(avg(age, "children", E))]
    o["share_cram"] = [r3(avg(age, "share_cram_in_edu", S)), r3(avg(age, "share_cram_in_edu", E))]
    o["share_cram_change_pt"] = r3(o["share_cram"][1] - o["share_cram"][0])
    o["share_tuition"] = [r3(avg(age, "share_tuition_in_edu", S)), r3(avg(age, "share_tuition_in_edu", E))]
    o["education_yen"] = [r3(avg(age, "education", S)), r3(avg(age, "education", E))]
    o["tuition_2018_19_to_2021_22"] = r3(100 * np.log(avg(age, "tuition", [2021, 2022]) / avg(age, "tuition", [2018, 2019])))
    return o
out = {"age40": run("40～49歳"), "age30": run("30～39歳"), "avg": run("平均"), "age50": run("50～59歳")}
a = out["age40"]
out["H1_verdict"] = "支持" if a["share_edu_change_pt"] >= 0.5 else "外れ"
out["H2_verdict"] = "支持" if a["real_edu_per_child_dlog"] >= 10 else "外れ"
out["H3_verdict"] = "支持" if a["share_cram_change_pt"] >= 3 else "外れ"
out["H4_verdict"] = "支持" if a["tuition_2018_19_to_2021_22"] <= -5 else "外れ"
out["cpi_edu_change"] = r3(100 * np.log(cpi.loc[E, "cpi_edu"].mean() / cpi.loc[S, "cpi_edu"].mean()))
out["cpi_all_change"] = r3(100 * np.log(cpi.loc[E, "cpi_all"].mean() / cpi.loc[S, "cpi_all"].mean()))
out["cpi_tuition_2018_19_to_2021_22"] = r3(100 * np.log(cpi.loc[[2021, 2022], "cpi_tuition"].mean() / cpi.loc[[2018, 2019], "cpi_tuition"].mean()))
b = run("40～49歳", [2005, 2006, 2007])
rob = [dict(spec="R1 30代の世帯", H1=out["age30"]["share_edu_change_pt"], H2=out["age30"]["real_edu_per_child_dlog"], H3=out["age30"]["share_cram_change_pt"], H4=out["age30"]["tuition_2018_19_to_2021_22"]),
       dict(spec="R2 名目で H2", H2=a["nom_edu_per_child_dlog"]),
       dict(spec="R3 始点を2005〜07年", H1=b["share_edu_change_pt"], H2=b["real_edu_per_child_dlog"], H3=b["share_cram_change_pt"]),
       dict(spec="R4 世帯人員1人当たり（実質）", H2=a["real_edu_per_person_dlog"]),
       dict(spec="R5 50代の世帯", H1=out["age50"]["share_edu_change_pt"], H2=out["age50"]["real_edu_per_child_dlog"], H3=out["age50"]["share_cram_change_pt"], H4=out["age50"]["tuition_2018_19_to_2021_22"])]
out["robustness"] = rob
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
