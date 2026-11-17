"""03_analysis.py : 未活用労働指標 LU1〜LU4 の差と内訳を、男女・年齢・年で比べる（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "lu_annual.csv")
allv = pd.read_csv(ROOT / "data" / "lu_annual_all_versions.csv")
mo = pd.read_csv(ROOT / "data" / "lu1_monthly.csv")
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


d["gap41"] = d.LU4 - d.LU1
d["ratio41"] = d.LU4 / d.LU1
d["addl_part"] = d.LU2 - d.LU1
d["potential_part"] = d.LU3 - d.LU1
d["approx_err"] = d.gap41 - d.addl_part - d.potential_part
d.round(3).to_csv(RES / "lu_with_parts.csv", index=False)
tot = d[d.age == "年齢計"].set_index(["sex", "year"])
main = {"total": {f"{s}_{y}": {k: r(tot.loc[(s, y), k], 2) for k in ["LU1", "LU2", "LU3", "LU4", "gap41", "ratio41", "addl_part", "potential_part"]}
                  for s in ["男女計", "男", "女"] for y in [2018, 2019, 2020, 2021, 2025]}}
ra = tot.loc["男女計"].ratio41
main["H1"] = {"min_ratio": r(ra.min(), 3), "min_year": int(ra.idxmin()), "ratios": {int(y): r(v, 3) for y, v in ra.items()}}
gf = tot.loc["女"].gap41
gm = tot.loc["男"].gap41
main["H2"] = {"female_minus_male_gap": {int(y): r(gf.loc[y] - gm.loc[y], 2) for y in gf.index}, "min": r((gf - gm).min(), 2)}
c = tot.loc["男女計"]
main["H3"] = {"dLU1": r(c.loc[2020, "LU1"] - c.loc[2019, "LU1"], 2), "d_addl": r(c.loc[2020, "addl_part"] - c.loc[2019, "addl_part"], 2),
              "d_potential": r(c.loc[2020, "potential_part"] - c.loc[2019, "potential_part"], 2), "dLU4": r(c.loc[2020, "LU4"] - c.loc[2019, "LU4"], 2)}
for s in ["男", "女"]:
    cc = tot.loc[s]
    main[f"H3_{s}"] = {"dLU1": r(cc.loc[2020, "LU1"] - cc.loc[2019, "LU1"], 2), "d_addl": r(cc.loc[2020, "addl_part"] - cc.loc[2019, "addl_part"], 2),
                       "d_potential": r(cc.loc[2020, "potential_part"] - cc.loc[2019, "potential_part"], 2)}
age = d[d.age != "年齢計"].set_index(["sex", "year", "age"]).sort_index()


def top_age(y, s="男女計"):
    g = age.loc[(s, y)].gap41.loc[AGES]
    return g.idxmax(), r(g.max(), 2), {a: r(g.loc[a], 2) for a in AGES}


ta = top_age(2025)
main["H4"] = {"top_age_2025": ta[0], "top_value": ta[1], "gap41_by_age_2025": ta[2]}
main["age_2025"] = {s: {a: {k: r(age.loc[(s, 2025, a), k], 2) for k in ["LU1", "LU4", "gap41", "addl_part", "potential_part"]} for a in AGES} for s in ["男女計", "男", "女"]}
main["age_2018"] = {s: {a: {k: r(age.loc[(s, 2018, a), k], 2) for k in ["LU1", "LU4", "gap41"]} for a in AGES} for s in ["男女計"]}
# 頑健性
rb = [{"check": "主：LU4 ÷ LU1 の最小（2018〜2025年、男女計）", "value": r(ra.min(), 3), "note": f"{int(ra.idxmin())}年"},
      {"check": "1 差（LU4 − LU1）の最小（ポイント）", "value": r(c.gap41.min(), 2), "note": f"{int(c.gap41.idxmin())}年"}]
for y in [2019, 2022]:
    t_ = top_age(y)
    rb.append({"check": f"2 年齢別で LU4 − LU1 が最大の年齢（{y}年）", "value": t_[1], "note": t_[0]})
ov = allv[(allv.age == "年齢計")].pivot_table(index=["sex", "year"], columns="version", values="LU4")
diffs = []
for (s, y), row in ov.iterrows():
    vals = row.dropna()
    if len(vals) > 1:
        diffs.append(vals.max() - vals.min())
rb.append({"check": "3 版の違いによる LU4 の差の最大（同じ年・男女）", "value": r(max(diffs), 2), "note": "人口の基準の切り替えなど"})
mavg = mo.groupby("year").LU1_sa.mean()
dif = [abs(mavg.loc[y] - c.loc[y, "LU1"]) for y in range(2018, 2026)]
rb.append({"check": "4 長期時系列（月次、季節調整値）の年平均と年報の LU1 の差の最大", "value": r(max(dif), 2), "note": "2018〜2025年"})
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
main["lu1_monthly"] = {"max": r(mo.LU1_sa.max(), 1), "max_ym": f"{int(mo.loc[mo.LU1_sa.idxmax(), 'year'])}-{int(mo.loc[mo.LU1_sa.idxmax(), 'month']):02d}",
                       "min": r(mo.LU1_sa.min(), 1), "last": r(mo.LU1_sa.iloc[-1], 1), "last_ym": f"{int(mo.year.iloc[-1])}-{int(mo.month.iloc[-1]):02d}"}
mavg.round(3).to_csv(RES / "lu1_annual_from_monthly.csv")
# 問い直し：女と男の年齢別の追加就労希望の分（2025年）
q = pd.DataFrame({f"{s}_{k}": [age.loc[(s, 2025, a), k] for a in AGES] for s in ["男", "女"] for k in ["addl_part", "potential_part", "LU1"]}, index=AGES)
q.round(2).to_csv(RES / "requestion_age_sex_parts_2025.csv")
main["requestion"] = {a: {"female_addl": r(q.loc[a, "女_addl_part"], 2), "male_addl": r(q.loc[a, "男_addl_part"], 2),
                          "female_pot": r(q.loc[a, "女_potential_part"], 2), "male_pot": r(q.loc[a, "男_potential_part"], 2)} for a in AGES}
main["judgement"] = {"H1": "支持" if ra.min() >= 2 else "外れ", "H2": "支持" if (gf - gm).min() > 0 else "外れ",
                     "H3": "支持" if main["H3"]["d_addl"] > main["H3"]["dLU1"] else "外れ", "H4": "支持" if ta[0] in ("15〜24歳", "65歳以上") else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H3_男", "H3_女", "H4", "judgement", "robustness", "requestion", "lu1_monthly"]}, ensure_ascii=False, indent=0))
print(json.dumps(main["total"], ensure_ascii=False))
