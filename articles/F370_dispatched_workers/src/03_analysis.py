"""03_analysis.py : 派遣社員の数の推移を、男女・年齢・非正規の中の割合で見る（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
a = pd.read_csv(ROOT / "data" / "employment_type_annual.csv")
pub = pd.read_csv(ROOT / "data" / "published_annual.csv").set_index("year")
q = pd.read_csv(ROOT / "data" / "dispatched_quarterly.csv").dropna()
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


t = a[a.age == "総数"].pivot_table(index="year", columns="sex", values="派遣社員")
nr = a[(a.age == "総数") & (a.sex == "男女計")].set_index("year")
share = pd.DataFrame({"派遣社員": nr["派遣社員"], "非正規": nr["非正規"], "役員を除く雇用者": nr["役員を除く雇用者"],
                      "share_of_nonregular": nr["派遣社員"] / nr["非正規"] * 100, "share_of_employees": nr["派遣社員"] / nr["役員を除く雇用者"] * 100,
                      "男": t["男"], "女": t["女"]})
share.round(3).to_csv(RES / "dispatched_annual.csv")
main = {"total": {int(y): r(t.loc[y, "男女計"], 0) for y in t.index}}
main["H1"] = {"y2008": r(t.loc[2008, "男女計"], 0), "y2025": r(t.loc[2025, "男女計"], 0), "trough_year": int(t.loc[2008:2012, "男女計"].idxmin()), "trough": r(t.loc[2008:2012, "男女計"].min(), 0),
              "first_above_2008": int(t.index[(t.index > 2008) & (t["男女計"] > t.loc[2008, "男女計"])][0]) if ((t.index > 2008) & (t["男女計"] > t.loc[2008, "男女計"])).any() else None}
main["H2"] = {s: r((t.loc[2012, s] / t.loc[2008, s] - 1) * 100, 1) for s in ["男", "女", "男女計"]}
ag = a[(a.sex == "男女計") & (a.age.isin(AGES))].pivot_table(index="year", columns="age", values="派遣社員")[AGES]
agsh = ag.div(ag.sum(axis=1), axis=0) * 100
ag.round(0).to_csv(RES / "dispatched_by_age.csv")
agsh.round(2).to_csv(RES / "dispatched_age_share.csv")
o45 = agsh[["45〜54歳", "55〜64歳", "65歳以上"]].sum(axis=1)
main["H3"] = {"share45plus_2008": r(o45.loc[2008], 1), "share45plus_2013": r(o45.loc[2013], 1), "share45plus_2025": r(o45.loc[2025], 1)}
main["age_counts"] = {int(y): {k: r(ag.loc[y, k], 0) for k in AGES} for y in [2008, 2012, 2013, 2019, 2025]}
main["H4"] = {"share_nonreg_2008": r(share.loc[2008, "share_of_nonregular"], 2), "share_nonreg_2025": r(share.loc[2025, "share_of_nonregular"], 2),
              "share_emp_2008": r(share.loc[2008, "share_of_employees"], 2), "share_emp_2025": r(share.loc[2025, "share_of_employees"], 2)}
main["step_2012_2013"] = {k: [r(nr.loc[2012, k], 0), r(nr.loc[2013, k], 0)] for k in ["派遣社員", "非正規", "契約社員", "嘱託", "その他", "パート・アルバイト"]}
# 四半期
qq = q.copy()
qq["t"] = qq.year + (qq.q - 1) / 4
pk = qq[qq.year <= 2010].sort_values("派遣社員", ascending=False).iloc[0]
tr = qq[(qq.year >= 2008) & (qq.year <= 2013)].sort_values("派遣社員").iloc[0]
main["quarterly"] = {"peak": [int(pk.year), int(pk.q), r(pk["派遣社員"], 0)], "trough": [int(tr.year), int(tr.q), r(tr["派遣社員"], 0)],
                     "latest": [int(qq.iloc[-1].year), int(qq.iloc[-1].q), r(qq.iloc[-1]["派遣社員"], 0)], "max_all": r(qq["派遣社員"].max(), 0)}
qq.to_csv(RES / "dispatched_quarterly.csv", index=False)
# 頑健性
rb = [
    {"check": "主：年平均、2008年→2025年（万人）", "v0": r(t.loc[2008, "男女計"], 0), "v1": r(t.loc[2025, "男女計"], 0)},
    {"check": "1 四半期のピーク→最新", "v0": r(pk["派遣社員"], 0), "v1": r(qq.iloc[-1]["派遣社員"], 0)},
    {"check": "2 H3 2013→2025年（45歳以上の割合、%）", "v0": r(o45.loc[2013], 1), "v1": r(o45.loc[2025], 1)},
    {"check": "2 H4 2013→2025年（非正規に占める割合、%）", "v0": r(share.loc[2013, "share_of_nonregular"], 2), "v1": r(share.loc[2025, "share_of_nonregular"], 2)},
    {"check": "3 役員を除く雇用者に占める割合（2008→2025年、%）", "v0": r(share.loc[2008, "share_of_employees"], 2), "v1": r(share.loc[2025, "share_of_employees"], 2)},
    {"check": "4 既公表値（2008年→2021年、万人。既公表値は2021年まで）", "v0": r(pub.loc[2008, "派遣社員_既公表"], 0), "v1": r(pub.loc[2021, "派遣社員_既公表"], 0)},
]
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
# 問い直し：世代を10年追う（10歳階級を10年ずらす）
co = []
pairs = [("15〜24歳", "25〜34歳"), ("25〜34歳", "35〜44歳"), ("35〜44歳", "45〜54歳"), ("45〜54歳", "55〜64歳")]
for y0 in [2005, 2008, 2013, 2015]:
    for a0, a1 in pairs:
        if y0 + 10 in ag.index:
            co.append({"start_year": y0, "start_age": a0, "end_age": a1, "n0": ag.loc[y0, a0], "n1": ag.loc[y0 + 10, a1], "ratio": ag.loc[y0 + 10, a1] / ag.loc[y0, a0]})
co = pd.DataFrame(co)
co.round(3).to_csv(RES / "requestion_cohort.csv", index=False)
main["requestion"] = [{k: (r(v, 3) if isinstance(v, float) else (int(v) if isinstance(v, (np.integer,)) else v)) for k, v in row.items()} for row in co.to_dict(orient="records")]
main["judgement"] = {"H1": "支持" if t.loc[2025, "男女計"] > t.loc[2008, "男女計"] else "外れ", "H2": "支持" if main["H2"]["男"] < main["H2"]["女"] else "外れ",
                     "H3": "支持" if o45.loc[2025] - o45.loc[2008] >= 15 else "外れ", "H4": "支持" if share.loc[2025, "share_of_nonregular"] < share.loc[2008, "share_of_nonregular"] else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "judgement", "step_2012_2013", "quarterly", "robustness", "age_counts"]}, ensure_ascii=False, indent=0))
print(co.round(2).to_string())
