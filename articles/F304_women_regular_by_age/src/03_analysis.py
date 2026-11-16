"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "emptype_age_sex.csv")
AGES = ["15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65～69歳", "70～74歳", "75歳以上"]
WORK = AGES[1:10]  # 20〜64歳
r3 = lambda x: round(float(x), 3)

def tab(sex, y):
    x = d[(d.sex == sex) & (d.year == y)].set_index("age").reindex(AGES)
    x["rate"] = 100 * x.regular / x.population
    x["reg_share"] = 100 * x.regular / x.employees_ex_exec
    return x

def decompose(sex, a, b, base="start"):
    A, B = tab(sex, a), tab(sex, b)
    ra, rb = A.regular / A.population, B.regular / B.population
    if base == "start":
        popc = (B.population - A.population) * ra; ratec = A.population * (rb - ra); inter = (B.population - A.population) * (rb - ra)
    else:
        popc = (B.population - A.population) * rb; ratec = B.population * (rb - ra); inter = -(B.population - A.population) * (rb - ra)
    t = pd.DataFrame({"age": AGES, "regular_start": A.regular.values, "regular_end": B.regular.values, "d_regular": (B.regular - A.regular).values,
                      "nonregular_start": A.nonregular.values, "nonregular_end": B.nonregular.values, "d_nonregular": (B.nonregular - A.nonregular).values,
                      "pop_start": A.population.values, "pop_end": B.population.values,
                      "rate_start": (100 * ra).values, "rate_end": (100 * rb).values, "d_rate_pt": (100 * (rb - ra)).values,
                      "share_start": A.reg_share.values, "share_end": B.reg_share.values,
                      "pop_effect": popc.values, "rate_effect": ratec.values, "interaction": inter.values})
    tot_reported = float(B.loc[:, "regular"].sum() - A.loc[:, "regular"].sum())
    s = dict(sex=sex, period=f"{a}-{b}", base=base, d_regular_sum_ages=r3(t.d_regular.sum()), pop_effect=r3(t.pop_effect.sum()),
             rate_effect=r3(t.rate_effect.sum()), interaction=r3(t.interaction.sum()))
    s["rate_share"] = r3(t.rate_effect.sum() / t.d_regular.sum()) if t.d_regular.sum() != 0 else None
    w = t[t.age.isin(WORK)]
    s["max_d_rate_age"] = w.loc[w.d_rate_pt.idxmax(), "age"]; s["max_d_rate_pt"] = r3(w.d_rate_pt.max())
    g = t.set_index("age")
    s["m_dip_start"] = r3(g.loc["25～29歳", "rate_start"] - g.loc["35～39歳", "rate_start"])
    s["m_dip_end"] = r3(g.loc["25～29歳", "rate_end"] - g.loc["35～39歳", "rate_end"])
    a2544 = ["25～29歳", "30～34歳", "35～39歳", "40～44歳"]
    s["d_regular_25_44"] = r3(g.loc[a2544, "d_regular"].sum()); s["d_nonregular_25_44"] = r3(g.loc[a2544, "d_nonregular"].sum())
    s["d_regular_45_64"] = r3(g.loc[["45～49歳", "50～54歳", "55～59歳", "60～64歳"], "d_regular"].sum())
    s["d_regular_65p"] = r3(g.loc[["65～69歳", "70～74歳", "75歳以上"], "d_regular"].sum())
    s["d_regular_15_24"] = r3(g.loc[["15～19歳", "20～24歳"], "d_regular"].sum())
    return s, t

out = {}
main, t = decompose("female", 2015, 2025)
t.round(3).to_csv(RES / "female_by_age_2015_2025.csv", index=False)
out["main"] = main
tot = d[(d.sex == "female") & (d.age == "総数")].set_index("year")
out["female_regular_total"] = {y: float(tot.loc[y, "regular"]) for y in (2002, 2013, 2015, 2019, 2025)}
out["female_nonregular_total"] = {y: float(tot.loc[y, "nonregular"]) for y in (2002, 2013, 2015, 2019, 2025)}
out["H1_verdict"] = "支持" if main["rate_share"] >= 0.8 else "外れ"
out["H2_verdict"] = "支持" if main["max_d_rate_age"] in ("25～29歳", "30～34歳") else "外れ"
out["H3_verdict"] = "支持" if (main["m_dip_start"] - main["m_dip_end"]) >= 3 else "外れ"
out["H4_verdict"] = "支持" if main["d_nonregular_25_44"] < 0 else "外れ"
# 年齢の形（M字）を年ごとに
shape = []
for y in range(2002, 2026):
    x = tab("female", y)
    for a in AGES:
        shape.append(dict(year=y, age=a, rate=r3(x.loc[a, "rate"]), reg_share=r3(x.loc[a, "reg_share"])))
pd.DataFrame(shape).to_csv(RES / "female_rate_by_age_year.csv", index=False)
# 頑健性
rob = [main | {"spec": "主 女性 2015→2025"},
       decompose("female", 2013, 2025)[0] | {"spec": "R1a 女性 2013→2025"},
       decompose("female", 2019, 2025)[0] | {"spec": "R1b 女性 2019→2025"},
       decompose("male", 2015, 2025)[0] | {"spec": "R3 男性 2015→2025"},
       decompose("female", 2015, 2025, base="end")[0] | {"spec": "R4 女性 基準を2025年"}]
# R2 正規の割合（分母＝役員を除く雇用者）
ts, te = tab("female", 2015), tab("female", 2025)
dsh = (te.reg_share - ts.reg_share).loc[WORK]
out["R2_reg_share_max_age"] = dsh.idxmax(); out["R2_reg_share_max_pt"] = r3(dsh.max())
out["R2_m_dip_share_2015"] = r3(ts.loc["25～29歳", "reg_share"] - ts.loc["35～39歳", "reg_share"])
out["R2_m_dip_share_2025"] = r3(te.loc["25～29歳", "reg_share"] - te.loc["35～39歳", "reg_share"])
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
out["robustness"] = rob
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "robustness"}, ensure_ascii=False, indent=0))
print(pd.DataFrame(rob)[["spec", "d_regular_sum_ages", "pop_effect", "rate_effect", "interaction", "rate_share", "max_d_rate_age", "max_d_rate_pt", "m_dip_start", "m_dip_end", "d_regular_25_44", "d_nonregular_25_44"]].to_string())
print(t.round(1).to_string())
