"""在学者・年齢・学校・入学の経路の推移、仮説の判定、頑健性。結果は results/ に書く。"""
import json
import pandas as pd
from common import ROOT

D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def r1(x, n=1):
    return round(float(x), n)


ny = pd.read_csv(D / "nenji_corr.csv").set_index("year")
age = pd.read_csv(D / "age.csv")
sch = pd.read_csv(D / "schools.csv").set_index("year")
ent = pd.read_csv(D / "entrants.csv").set_index("year")

ny["all_hs"] = ny.tsushin + ny.fullpart
ny["corr_share_pct"] = (100 * ny.tsushin / ny.all_hs).round(3)
ny.loc[1985:].to_csv(R / "by_year_nenji.csv")

GRP = {"15-17": ["15", "16", "17"], "18-19": ["18", "19"], "20+": ["20-24", "25-29", "30-39", "40-49", "50-59", "60+"]}
w = age[age.age != "計"].copy()
w["grp"] = w.age.map({a: g for g, ags in GRP.items() for a in ags})
g = w.groupby(["year", "grp"])[["total", "public", "private"]].sum().unstack("grp")
tot = age[age.age == "計"].set_index("year")
ag = pd.DataFrame(index=tot.index)
for kind in ["total", "public", "private"]:
    for gg in GRP:
        ag[f"{kind}_{gg}"] = g[(kind, gg)]
        ag[f"{kind}_{gg}_pct"] = (100 * g[(kind, gg)] / tot[kind]).round(2)
    ag[f"{kind}_all"] = tot[kind]
a15_18 = w[w.age.isin(["15", "16", "17", "18"])].groupby("year").total.sum()
ag["total_15-18_pct"] = (100 * a15_18 / tot.total).round(2)
a15 = w[w.age == "15"].set_index("year").total
ag["total_15_pct"] = (100 * a15 / tot.total).round(2)
ag.to_csv(R / "by_year_age.csv")

ent["midyear_share_pct"] = (100 * (1 - ent.may_prev_fy / ent.whole_prev_fy)).round(2)
ent["midyear_n"] = ent.whole_prev_fy - ent.may_prev_fy
ent.to_csv(R / "by_year_entrants.csv")
sch.to_csv(R / "by_year_schools.csv")

m = {}
m["corr"] = {int(y): int(ny.loc[y, "tsushin"]) for y in [1985, 1990, 2000, 2010, 2015, 2020, 2025]}
m["fullpart"] = {int(y): int(ny.loc[y, "fullpart"]) for y in [1990, 2000, 2015, 2025]}
m["corr_change_1990_2025_pct"] = r1(100 * (ny.loc[2025, "tsushin"] / ny.loc[1990, "tsushin"] - 1))
m["fullpart_change_1990_2025_pct"] = r1(100 * (ny.loc[2025, "fullpart"] / ny.loc[1990, "fullpart"] - 1))
m["corr_share_pct"] = {int(y): r1(ny.loc[y, "corr_share_pct"], 2) for y in [1990, 2000, 2015, 2025]}
m["corr_min_year_since1990"] = int(ny.loc[1990:, "tsushin"].idxmin())
m["corr_min_since1990"] = int(ny.loc[1990:, "tsushin"].min())
m["corr_change_2015_2025_pct"] = r1(100 * (ny.loc[2025, "tsushin"] / ny.loc[2015, "tsushin"] - 1))
m["corr_change_2000_2025_pct"] = r1(100 * (ny.loc[2025, "tsushin"] / ny.loc[2000, "tsushin"] - 1))
m["direct_to_corr_pt"] = {int(y): float(ny.loc[y, "direct_to_corr_pt"]) for y in [1990, 2000, 2010, 2015, 2020, 2025]}
m["independent_schools"] = {int(y): int(ny.loc[y, "corr_only_schools"]) for y in [1990, 2000, 2010, 2025]}
m["age"] = {int(y): {"15-17_pct": float(ag.loc[y, "total_15-17_pct"]), "18-19_pct": float(ag.loc[y, "total_18-19_pct"]),
                     "20+_pct": float(ag.loc[y, "total_20+_pct"]), "15-17_n": int(ag.loc[y, "total_15-17"]),
                     "20+_n": int(ag.loc[y, "total_20+"]), "15-18_pct": float(ag.loc[y, "total_15-18_pct"]),
                     "private_15-17_pct": float(ag.loc[y, "private_15-17_pct"]), "public_15-17_pct": float(ag.loc[y, "public_15-17_pct"]),
                     "public_20+_pct": float(ag.loc[y, "public_20+_pct"])} for y in ag.index}
m["private"] = {int(y): int(tot.loc[y, "private"]) for y in tot.index}
m["public"] = {int(y): int(tot.loc[y, "public"]) for y in tot.index}
inc = tot.loc[2025, "total"] - tot.loc[1990, "total"]
m["private_share_of_increase_1990_2025_pct"] = r1(100 * (tot.loc[2025, "private"] - tot.loc[1990, "private"]) / inc)
m["private_share_students_pct"] = {int(y): r1(100 * tot.loc[y, "private"] / tot.loc[y, "total"]) for y in tot.index}
m["schools"] = {int(y): {c: int(sch.loc[y, c]) for c in sch.columns} for y in sch.index}
m["midyear_share_pct"] = {int(y): float(ent.loc[y, "midyear_share_pct"]) for y in ent.index}
m["entrants"] = {int(y): {c: int(ent.loc[y, c]) for c in ["may_prev_fy", "whole_prev_fy", "midyear_n"]} for y in ent.index}
m["entrants_whole_change_1989_2024_pct"] = r1(100 * (ent.loc[2025, "whole_prev_fy"] / ent.loc[1990, "whole_prev_fy"] - 1))
m["entrants_may_change_1989_2024_pct"] = r1(100 * (ent.loc[2025, "may_prev_fy"] / ent.loc[1990, "may_prev_fy"] - 1))
m["midyear_n_change"] = [int(ent.loc[1990, "midyear_n"]), int(ent.loc[2025, "midyear_n"])]

a90, a25 = m["age"][1990]["15-17_pct"], m["age"][2025]["15-17_pct"]
dpt = m["direct_to_corr_pt"]
h = {
    "H1": {"rule": "通信制 +50%以上 かつ 全日制・定時制が減少（1990→2025）", "value": [m["corr_change_1990_2025_pct"], m["fullpart_change_1990_2025_pct"]],
           "verdict": "支持" if m["corr_change_1990_2025_pct"] >= 50 and m["fullpart_change_1990_2025_pct"] < 0 else "外れ"},
    "H2": {"rule": "15〜17歳の割合 1990 <50% かつ 2025 ≥70%", "value": [a90, a25], "verdict": "支持" if a90 < 50 and a25 >= 70 else "外れ"},
    "H3": {"rule": "1990→2025 の増加の8割以上が私立", "value": m["private_share_of_increase_1990_2025_pct"],
           "verdict": "支持" if m["private_share_of_increase_1990_2025_pct"] >= 80 else "外れ"},
    "H4": {"rule": "進学率の差 2000→2025 で +4ポイント以上", "value": [dpt[2000], dpt[2025]],
           "verdict": "支持" if dpt[2025] - dpt[2000] >= 4 else "外れ"},
    "H5": {"rule": "2024年度の入学者のうち5月2日以降が25%以上", "value": m["midyear_share_pct"][2025],
           "verdict": "支持" if m["midyear_share_pct"][2025] >= 25 else "外れ"},
}
m["hypotheses"] = h

rob = []
for y0 in [1990, 2000, 2015]:
    rob.append({"check": f"在学者の変化 {y0}→2025年", "corr_pct": r1(100 * (ny.loc[2025, "tsushin"] / ny.loc[y0, "tsushin"] - 1)),
                "fullpart_pct": r1(100 * (ny.loc[2025, "fullpart"] / ny.loc[y0, "fullpart"] - 1)),
                "corr_share_from": r1(ny.loc[y0, "corr_share_pct"], 2), "corr_share_to": r1(ny.loc[2025, "corr_share_pct"], 2)})
rob.append({"check": "年齢の区切りを15〜18歳にする（1990→2025年度の割合）", "corr_pct": None, "fullpart_pct": None,
            "corr_share_from": float(ag.loc[1990, "total_15-18_pct"]), "corr_share_to": float(ag.loc[2025, "total_15-18_pct"])})
rob.append({"check": "15歳だけの割合（1990→2025年度）", "corr_pct": None, "fullpart_pct": None,
            "corr_share_from": float(ag.loc[1990, "total_15_pct"]), "corr_share_to": float(ag.loc[2025, "total_15_pct"])})
inc15 = ag.loc[2025, "total_15-17"] - ag.loc[1990, "total_15-17"]
m["increase_15_17_share_of_total_increase_pct"] = r1(100 * inc15 / inc)
rob.append({"check": "1990→2025年度の生徒の増加のうち15〜17歳の分（%）", "corr_pct": m["increase_15_17_share_of_total_increase_pct"],
            "fullpart_pct": None, "corr_share_from": None, "corr_share_to": None})
robdf = pd.DataFrame(rob)
robdf.to_csv(R / "robustness.csv", index=False)
m["robustness"] = rob
json.dump(m, open(R / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: m[k] for k in ["corr", "corr_change_1990_2025_pct", "fullpart_change_1990_2025_pct", "corr_share_pct", "corr_min_year_since1990",
                                    "direct_to_corr_pt", "private_share_of_increase_1990_2025_pct", "private_share_students_pct",
                                    "midyear_share_pct", "hypotheses", "increase_15_17_share_of_total_increase_pct",
                                    "entrants_whole_change_1989_2024_pct", "entrants_may_change_1989_2024_pct", "midyear_n_change"]}, ensure_ascii=False, indent=1))
print(ag[["total_15-17_pct", "total_18-19_pct", "total_20+_pct", "public_15-17_pct", "private_15-17_pct", "total_15-17", "total_20+"]])
print(sch)
print(robdf)
