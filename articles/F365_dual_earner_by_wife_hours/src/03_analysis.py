"""03_analysis.py : 共働き世帯を妻の週の就業時間で分け、専業主婦世帯と比べる（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "couples.csv")
HOURS = ["休業者", "週1～14時間", "週15～34時間", "週35時間以上"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def table(base, hh):
    w = d[(d.base == base) & (d.household == hh)].pivot_table(index="year", columns="wife", values="value")
    t = pd.DataFrame(index=w.index)
    t["dual"] = w["雇用者_非農林業"]
    t["housewife"] = w["非労働力人口"] + w["完全失業者"]
    for h in HOURS + ["週15～29時間", "週30～34時間"]:
        t[h] = w[h]
    t["dual_ft35"] = w["週35時間以上"]
    t["dual_pt"] = w["週1～14時間"] + w["週15～34時間"]
    known = w[["週1～14時間", "週15～34時間", "週35時間以上"]].sum(axis=1)
    t["dual_ft35_leave_alloc"] = w["週35時間以上"] + w["休業者"] * w["週35時間以上"] / known
    t["dual_ft30"] = w["週35時間以上"] + w["週30～34時間"]
    t["dual_month121"] = w["月121～180時間"] + w["月181～240時間"] + w["月241時間以上"]
    t["ratio_dual_hw"] = t.dual / t.housewife
    t["share_ft35"] = t.dual_ft35 / t.dual * 100
    t["ratio_ft35_hw"] = t.dual_ft35 / t.housewife
    t["ratio_ft35alloc_hw"] = t.dual_ft35_leave_alloc / t.housewife
    t["ratio_ft30_hw"] = t.dual_ft30 / t.housewife
    t["ratio_m121_hw"] = t.dual_month121 / t.housewife
    t["share_ft30"] = t.dual_ft30 / t.dual * 100
    return t


main = {}
cur = table("2020年基準", "夫婦のいる世帯")
kid = table("2020年基準", "夫婦と子供から成る世帯")
old = pd.concat([table("2010年基準", "夫婦のいる世帯"), table("2015年基準", "夫婦のいる世帯")])
cur.round(3).to_csv(RES / "dual_vs_housewife_2018_2025.csv")
kid.round(3).to_csv(RES / "dual_vs_housewife_couple_with_children.csv")
old.round(3).to_csv(RES / "old_base_2016_2021.csv")
for y in [2018, 2025]:
    main[f"y{y}"] = {k: r(cur.loc[y, k], 3) for k in ["dual", "housewife", "dual_ft35", "dual_pt", "休業者", "週1～14時間", "週15～34時間",
                                                      "share_ft35", "ratio_dual_hw", "ratio_ft35_hw", "share_ft30"]}
inc = cur.loc[2025] - cur.loc[2018]
main["change_2018_2025"] = {k: r(inc[k], 1) for k in ["dual", "housewife", "dual_ft35", "dual_pt", "休業者", "週1～14時間", "週15～34時間"]}
main["H1"] = {"ratio": r(cur.loc[2025, "ratio_dual_hw"], 3)}
main["H2"] = {"share_ft35": r(cur.loc[2025, "share_ft35"], 2)}
main["H3"] = {"ratio_ft35_hw": r(cur.loc[2025, "ratio_ft35_hw"], 3), "first_year_ft35_gt_hw": int(cur.index[cur.dual_ft35 > cur.housewife][0]) if (cur.dual_ft35 > cur.housewife).any() else None}
main["H4"] = {"share_of_increase_ft35": r(inc["dual_ft35"] / inc["dual"], 3)}
main["share_ft35_by_year"] = {int(y): r(v, 2) for y, v in cur.share_ft35.items()}
main["ratio_by_year"] = {int(y): {"dual_hw": r(cur.loc[y, "ratio_dual_hw"], 3), "ft35_hw": r(cur.loc[y, "ratio_ft35_hw"], 3)} for y in cur.index}
main["judgement"] = {"H1": "支持" if cur.loc[2025, "ratio_dual_hw"] >= 2 else "外れ", "H2": "支持" if cur.loc[2025, "share_ft35"] < 50 else "外れ",
                     "H3": "支持" if cur.loc[2025, "ratio_ft35_hw"] > 1 else "外れ", "H4": "支持" if inc["dual_ft35"] / inc["dual"] >= 0.5 else "外れ"}
# 頑健性
rb = [
    {"check": "主：週35時間以上、2025年", "share": r(cur.loc[2025, "share_ft35"], 2), "ratio_to_housewife": r(cur.loc[2025, "ratio_ft35_hw"], 3)},
    {"check": "1 線を週30時間以上に", "share": r(cur.loc[2025, "share_ft30"], 2), "ratio_to_housewife": r(cur.loc[2025, "ratio_ft30_hw"], 3)},
    {"check": "2 休業者を時間の分かる人の割合で振り分け", "share": r(cur.loc[2025, "dual_ft35_leave_alloc"] / cur.loc[2025, "dual"] * 100, 2), "ratio_to_housewife": r(cur.loc[2025, "ratio_ft35alloc_hw"], 3)},
    {"check": "3 旧基準（2015年基準）2021年", "share": r(old.loc[2021, "share_ft35"], 2), "ratio_to_housewife": r(old.loc[2021, "ratio_ft35_hw"], 3)},
    {"check": "3' 新基準 2021年（比べる相手）", "share": r(cur.loc[2021, "share_ft35"], 2), "ratio_to_housewife": r(cur.loc[2021, "ratio_ft35_hw"], 3)},
    {"check": "4 月121時間以上（月間の時間）", "share": r(cur.loc[2025, "dual_month121"] / cur.loc[2025, "dual"] * 100, 2), "ratio_to_housewife": r(cur.loc[2025, "ratio_m121_hw"], 3)},
]
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
main["old_base"] = {int(y): {"dual_hw": r(old.loc[y, "ratio_dual_hw"], 3), "share_ft35": r(old.loc[y, "share_ft35"], 2), "ft35_hw": r(old.loc[y, "ratio_ft35_hw"], 3)} for y in [2016, 2017]}
# 問い直し：夫婦と子供から成る世帯
main["children"] = {int(y): {k: r(kid.loc[y, k], 3) for k in ["dual", "housewife", "dual_ft35", "share_ft35", "ratio_dual_hw", "ratio_ft35_hw"]} for y in [2018, 2025]}
ik = kid.loc[2025] - kid.loc[2018]
main["children_change"] = {k: r(ik[k], 1) for k in ["dual", "housewife", "dual_ft35", "dual_pt"]}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True))
