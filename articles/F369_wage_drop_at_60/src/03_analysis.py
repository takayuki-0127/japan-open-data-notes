"""03_analysis.py : 55〜59歳から60〜64歳への所定内給与の下がり方を、性・規模・学歴・年で比べる（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
g = pd.read_csv(ROOT / "data" / "general.csv")
SIZES = ["企業規模計", "1000人以上", "100〜999人", "10〜99人"]
HARM = {"高校卒": "高校", "高校": "高校", "大学・大学院卒": "大学大学院", "大学": "大学大学院", "大学院": "大学大学院"}


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


e = g[g.edu.isin(HARM)].copy()
e["eh"] = e.edu.map(HARM)
e["ww"] = e.wage * e.workers10
eh = e.groupby(["year", "sex", "eh", "age", "size"], as_index=False)[["ww", "workers10"]].sum(min_count=1)
eh["wage"] = eh.ww / eh.workers10
H = pd.concat([g[g.edu == "学歴計"].assign(eh="学歴計")[["year", "sex", "eh", "age", "size", "wage", "workers10"]],
               eh[["year", "sex", "eh", "age", "size", "wage", "workers10"]]], ignore_index=True)


def ratio(sex, size="企業規模計", edu="学歴計", num="60〜64歳", den="55〜59歳", col="wage"):
    s = H[(H.sex == sex) & (H["size"] == size) & (H.eh == edu)]
    p = s.pivot_table(index="year", columns="age", values=col)
    return p[num] / p[den]


ts = {}
for sex in ["男", "女", "男女計"]:
    for sz in SIZES:
        ts[f"{sex}_{sz}"] = ratio(sex, sz)
for sex in ["男", "女"]:
    for edu in ["高校", "大学大学院"]:
        ts[f"{sex}_{edu}"] = ratio(sex, edu=edu)
ts["男_50_54基準"] = ratio("男", den="50〜54歳")
ts["男_65_69÷60_64"] = ratio("男", num="65〜69歳", den="60〜64歳")
ts["女_65_69÷60_64"] = ratio("女", num="65〜69歳", den="60〜64歳")
T = pd.DataFrame(ts) * 100
T.index.name = "year"
T.round(2).to_csv(RES / "ratio_60_64_to_55_59.csv")
main = {"series": {k: {int(y): r(v, 1) for y, v in T[k].items() if y in (2006, 2010, 2013, 2019, 2020, 2025)} for k in T.columns}}
m = T["男_企業規模計"]
main["H1"] = {"y2006": r(m.loc[2006], 2), "y2025": r(m.loc[2025], 2), "chg": r(m.loc[2025] - m.loc[2006], 2)}
gap = T["男_10〜99人"] - T["男_1000人以上"]
main["H2"] = {"min_gap_small_minus_large": r(gap.min(), 2), "min_year": int(gap.idxmin()), "gap_2006": r(gap.loc[2006], 2), "gap_2025": r(gap.loc[2025], 2), "max_gap": r(gap.max(), 2), "max_year": int(gap.idxmax())}
main["H3"] = {"male_2025": r(T.loc[2025, "男_企業規模計"], 2), "female_2025": r(T.loc[2025, "女_企業規模計"], 2)}
pre = (m.loc[2013] - m.loc[2006]) / 7
post = (m.loc[2025] - m.loc[2013]) / 12
main["H4"] = {"pre_per_year": r(pre, 3), "post_per_year": r(post, 3), "m2013": r(m.loc[2013], 2)}
# 金額
w = H[(H.eh == "学歴計") & (H.age.isin(["55〜59歳", "60〜64歳"]))].pivot_table(index=["sex", "size", "year"], columns="age", values="wage")
main["wages"] = {f"{s}_{sz}_{y}": [r(w.loc[(s, sz, y), "55〜59歳"], 1), r(w.loc[(s, sz, y), "60〜64歳"], 1)] for s in ["男", "女"] for sz in SIZES for y in [2006, 2025]}
# 問い直し：労働者数（十人）の比 60〜64 ÷ 55〜59
nw = {}
for sex in ["男", "女"]:
    for sz in SIZES:
        nw[f"{sex}_{sz}"] = ratio(sex, sz, col="workers10") * 100
NW = pd.DataFrame(nw)
NW.index.name = "year"
NW.round(2).to_csv(RES / "requestion_worker_ratio.csv")
main["requestion"] = {k: {int(y): r(NW.loc[y, k], 1) for y in (2006, 2013, 2019, 2025)} for k in NW.columns}
c = np.corrcoef(NW["男_企業規模計"], T["男_企業規模計"])[0, 1]
main["requestion_corr_male_total"] = r(c, 3)
# 頑健性
rb = [{"check": "主：男・学歴計・規模計（2006→2025年）", "v0": r(m.loc[2006], 2), "v1": r(m.loc[2025], 2), "chg": r(m.loc[2025] - m.loc[2006], 2)}]
for k, lab in [("男_高校", "1a 男・高校卒"), ("男_大学大学院", "1b 男・大学大学院卒")]:
    rb.append({"check": lab, "v0": r(T.loc[2006, k], 2), "v1": r(T.loc[2025, k], 2), "chg": r(T.loc[2025, k] - T.loc[2006, k], 2)})
rb.append({"check": "2 3年平均（2006〜08→2023〜25年）", "v0": r(m.loc[2006:2008].mean(), 2), "v1": r(m.loc[2023:2025].mean(), 2), "chg": r(m.loc[2023:2025].mean() - m.loc[2006:2008].mean(), 2)})
k = "男_50_54基準"
rb.append({"check": "3 60〜64歳 ÷ 50〜54歳（男）", "v0": r(T.loc[2006, k], 2), "v1": r(T.loc[2025, k], 2), "chg": r(T.loc[2025, k] - T.loc[2006, k], 2)})
k = "男_65_69÷60_64"
rb.append({"check": "4 65〜69歳 ÷ 60〜64歳（男）", "v0": r(T.loc[2006, k], 2), "v1": r(T.loc[2025, k], 2), "chg": r(T.loc[2025, k] - T.loc[2006, k], 2)})
for sz in ["1000人以上", "100〜999人", "10〜99人"]:
    k = f"男_{sz}"
    rb.append({"check": f"5 規模 {sz}（男）", "v0": r(T.loc[2006, k], 2), "v1": r(T.loc[2025, k], 2), "chg": r(T.loc[2025, k] - T.loc[2006, k], 2)})
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
main["judgement"] = {"H1": "支持" if main["H1"]["chg"] >= 5 else "外れ", "H2": "支持" if gap.min() > 0 else "外れ",
                     "H3": "支持" if T.loc[2025, "男_企業規模計"] < T.loc[2025, "女_企業規模計"] else "外れ", "H4": "支持" if post > pre else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "judgement", "robustness", "requestion", "requestion_corr_male_total"]}, ensure_ascii=False, indent=0))
print(T.round(1).to_string())
