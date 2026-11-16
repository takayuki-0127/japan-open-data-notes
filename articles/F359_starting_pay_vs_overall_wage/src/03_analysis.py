"""03_analysis.py : 新卒の給与の伸びを、一般労働者全体の伸びと比べる（オフライン）。結果は results/ に出す。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

ng = pd.read_csv(D / "newgrad.csv")
gen = pd.read_csv(D / "general.csv")
old = pd.read_csv(D / "old_ts_starting_pay.csv")
AGES = ["〜19歳", "20〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜44歳", "45〜49歳",
        "50〜54歳", "55〜59歳", "60〜64歳", "65〜69歳", "70歳〜"]
SIZES = ["企業規模計", "1000人以上", "100〜999人", "10〜99人"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def ng_series(edu="大学", sex="男女計", size="企業規模計"):
    s = ng[(ng.edu == edu) & (ng.sex == sex) & (ng["size"] == size)].set_index("year")["wage"]
    return s.sort_index()


def gen_series(sex="男女計", age="年齢計", size="企業規模計"):
    s = gen[(gen.edu == "学歴計") & (gen.sex == sex) & (gen.age == age) & (gen["size"] == size)]
    return s.set_index("year")["wage"].sort_index()


def gen_fixed(sex="男女計", size="企業規模計", base=2019):
    g = gen[(gen.edu == "学歴計") & (gen.sex == sex) & (gen["size"] == size) & (gen.age.isin(AGES))]
    w = g[g.year == base].set_index("age")["workers10"]
    w = w / w.sum()
    p = g.pivot_table(index="year", columns="age", values="wage")[AGES]
    return (p * w[AGES]).sum(axis=1)


def yoy(s):
    return (s / s.shift(1) - 1) * 100


# ---- 主な系列 ----
series = pd.DataFrame({
    "ng_univ": ng_series("大学"), "ng_high": ng_series("高校"),
    "gen_all": gen_series(), "gen_fixed2019": gen_fixed(), "gen_20_24": gen_series(age="20〜24歳"),
    "gen_25_29": gen_series(age="25〜29歳"), "gen_50_54": gen_series(age="50〜54歳"),
})
growth = series.apply(yoy)
growth["gap_univ_all"] = growth.ng_univ - growth.gen_all
growth["gap_high_all"] = growth.ng_high - growth.gen_all
growth["gap_univ_fixed"] = growth.ng_univ - growth.gen_fixed2019
growth["gap_univ_20_24"] = growth.ng_univ - growth.gen_20_24
out = series.round(2).join(growth.add_suffix("_yoy").round(3))
out.index.name = "year"
out.to_csv(RES / "series_yoy.csv")

g = growth.loc[2007:2025]


def rank_info(col):
    s = g[col]
    return {"value_2025": r(s.loc[2025], 3), "max_year": int(s.idxmax()), "max_value": r(s.max(), 3),
            "rank_2025_of": [int((s > s.loc[2025]).sum()) + 1, int(s.notna().sum())],
            "second_year": int(s.drop(2025).idxmax()), "second_value": r(s.drop(2025).max(), 3)}


main = {"period_newmethod": [2006, 2025]}
main["levels_2025"] = {k: r(series.loc[2025, k], 1) for k in series.columns}
main["levels_2024"] = {k: r(series.loc[2024, k], 1) for k in series.columns}
main["yoy_2025"] = {k: r(growth.loc[2025, k], 2) for k in growth.columns}
main["H1_ng_univ_yoy"] = rank_info("ng_univ")
main["H2_gap_univ_all"] = rank_info("gap_univ_all")
main["ng_high_yoy"] = rank_info("ng_high")
main["gap_high_all"] = rank_info("gap_high_all")
main["mean_yoy_2007_2019"] = {k: r(growth.loc[2007:2019, k].mean(), 2) for k in ["ng_univ", "ng_high", "gen_all", "gen_fixed2019"]}
main["mean_yoy_2021_2025"] = {k: r(growth.loc[2021:2025, k].mean(), 2) for k in ["ng_univ", "ng_high", "gen_all", "gen_fixed2019"]}
main["yoy_by_year_2021_2025"] = {int(y): {k: r(growth.loc[y, k], 2) for k in ["ng_univ", "ng_high", "gen_all", "gen_fixed2019", "gen_20_24"]} for y in range(2021, 2026)}

# ---- H3：2019→2025 の累積 ----
cum = []
for a in ["年齢計"] + AGES[:10]:
    s = gen_series(age=a)
    cum.append({"group": f"一般労働者 {a}", "w2019": s.loc[2019], "w2025": s.loc[2025], "growth_pct": (s.loc[2025] / s.loc[2019] - 1) * 100})
for e in ["大学", "高校"]:
    s = ng_series(e)
    cum.append({"group": f"新卒 {e}", "w2019": s.loc[2019], "w2025": s.loc[2025], "growth_pct": (s.loc[2025] / s.loc[2019] - 1) * 100})
s = gen_fixed()
cum.append({"group": "一般労働者 年齢構成を2019年に固定", "w2019": s.loc[2019], "w2025": s.loc[2025], "growth_pct": (s.loc[2025] / s.loc[2019] - 1) * 100})
cum = pd.DataFrame(cum)
cum.round(2).to_csv(RES / "cum_2019_2025.csv", index=False)
cg = cum.set_index("group")["growth_pct"]
main["H3_cum_2019_2025"] = {k: r(v, 2) for k, v in cg.items()}
main["H3_support"] = bool(cg["新卒 大学"] > cg["一般労働者 年齢計"] and cg["新卒 高校"] > cg["一般労働者 年齢計"]
                          and cg["新卒 大学"] > cg["一般労働者 50〜54歳"] and cg["新卒 高校"] > cg["一般労働者 50〜54歳"])

# 2006→2025 の累積も
main["cum_2006_2025"] = {k: r((series.loc[2025, k] / series.loc[2006, k] - 1) * 100, 2) for k in series.columns}

# 50〜54歳 ÷ 20〜24歳
ratio = (series.gen_50_54 / series.gen_20_24).rename("ratio_50_54_to_20_24")
ratio.round(4).to_csv(RES / "ratio_50_54_to_20_24.csv")
main["ratio_50_54_to_20_24"] = {int(y): r(ratio.loc[y], 3) for y in [2006, 2010, 2015, 2019, 2020, 2024, 2025]}
main["ratio_max_year"] = int(ratio.idxmax())

# ---- H4：旧推計方法の長い系列 ----
o = old[(old.sex == "男") & (old.edu == "大学")].set_index("year")["wage"].sort_index()
oy = yoy(o)
chk = old[(old.sex == "男") & (old.edu == "大学")].set_index("year")["pct_table"]
diff = (oy.round(1) - chk).abs().loc[1977:2019]
pd.DataFrame({"wage": o, "yoy_calc": oy.round(3), "yoy_table": chk}).to_csv(RES / "old_series_univ_male.csv")
thr = main["yoy_2025"]["ng_univ"]
main["H4_old"] = {"threshold": thr, "years_ge_threshold": [int(y) for y in oy[oy >= thr].index],
                  "n_years_ge": int((oy >= thr).sum()), "max_year": int(oy.idxmax()), "max_value": r(oy.max(), 2),
                  "last_year_ge": int(oy[oy >= thr].index.max()) if (oy >= thr).any() else None,
                  "max_abs_diff_vs_table": r(diff.max(), 2), "mean_1977_1991": r(oy.loc[1977:1991].mean(), 2),
                  "mean_1992_2019": r(oy.loc[1992:2019].mean(), 2),
                  "near_years_ge_5_5": {int(y): r(v, 2) for y, v in oy[oy >= 5.5].items()}}
# 新方式の男 大学 との照合（同じ年の旧方式と新方式の差）
ngm = ng_series("大学", "男")
main["old_vs_new_2019_univ_male"] = {"old": r(o.loc[2019], 1), "new": r(ngm.loc[2019], 1)}

# ---- 頑健性 ----
rob = []


def add(name, ng_s, gen_s, note=""):
    gy = yoy(ng_s).loc[2007:2025]
    ay = yoy(gen_s).loc[2007:2025]
    gap = gy - ay
    rob.append({"check": name, "ng_yoy_2025": gy.loc[2025], "gen_yoy_2025": ay.loc[2025],
                "gap_2025": gap.loc[2025], "ng_yoy_rank_2025": int((gy > gy.loc[2025]).sum()) + 1,
                "gap_rank_2025": int((gap > gap.loc[2025]).sum()) + 1, "n_years": int(gy.notna().sum()),
                "gap_max_year": int(gap.idxmax()), "note": note})


add("主：大学・男女計・規模計 vs 一般労働者の年齢計", ng_series("大学"), gen_series())
add("1a 男", ng_series("大学", "男"), gen_series("男"))
add("1b 女", ng_series("大学", "女"), gen_series("女"))
for sz in SIZES[1:]:
    add(f"2 規模 {sz}", ng_series("大学", size=sz), gen_series(size=sz))
add("3a 比べる相手を年齢構成固定の平均に", ng_series("大学"), gen_fixed())
add("3b 比べる相手を20〜24歳に", ng_series("大学"), gen_series(age="20〜24歳"))
add("5 高校・男女計・規模計", ng_series("高校"), gen_series())
rb = pd.DataFrame(rob)
# 4：2021〜2025年だけの順位
gy = yoy(ng_series("大学")).loc[2021:2025]
ay = yoy(gen_series()).loc[2021:2025]
rob4 = {"check": "4 2021〜2025年だけ", "ng_yoy_2025": gy.loc[2025], "gen_yoy_2025": ay.loc[2025],
        "gap_2025": gy.loc[2025] - ay.loc[2025], "ng_yoy_rank_2025": int((gy > gy.loc[2025]).sum()) + 1,
        "gap_rank_2025": int(((gy - ay) > (gy - ay).loc[2025]).sum()) + 1, "n_years": 5,
        "gap_max_year": int((gy - ay).idxmax()), "note": "推計方法の変わった2020年をまたがない"}
rb = pd.concat([rb, pd.DataFrame([rob4])], ignore_index=True)
for c in ["ng_yoy_2025", "gen_yoy_2025", "gap_2025"]:
    rb[c] = rb[c].round(2)
rb.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb.to_dict(orient="records")

# ---- 問い直し：新卒 ÷ 25〜29歳 ----
q = pd.DataFrame({
    "univ_new_over_25_29_all": series.ng_univ / series.gen_25_29,
    "high_new_over_20_24_all": series.ng_high / series.gen_20_24,
})
u2529 = gen[(gen.sex == "男女計") & (gen.age == "25〜29歳") & (gen["size"] == "企業規模計") & (gen.edu.isin(["大学", "大学・大学院卒"]))].set_index("year")["wage"]
q["univ_new_over_25_29_univ"] = series.ng_univ / u2529
q["univ_25_29_edu_label"] = gen[(gen.sex == "男女計") & (gen.age == "25〜29歳") & (gen["size"] == "企業規模計") & (gen.edu.isin(["大学", "大学・大学院卒"]))].set_index("year")["edu"]
q.index.name = "year"
q.round(4).to_csv(RES / "requestion_newgrad_vs_25_29.csv")
main["requestion"] = {
    "univ_new_over_25_29_all": {int(y): r(q.loc[y, "univ_new_over_25_29_all"], 3) for y in [2006, 2010, 2015, 2019, 2020, 2024, 2025]},
    "univ_new_over_25_29_univ_2020_2025": {int(y): r(q.loc[y, "univ_new_over_25_29_univ"], 3) for y in range(2020, 2026)},
    "high_new_over_20_24_all": {int(y): r(q.loc[y, "high_new_over_20_24_all"], 3) for y in [2006, 2019, 2025]},
    "ratio_max_year_all": int(q.univ_new_over_25_29_all.idxmax()),
    "gen_25_29_yoy_2025": r(growth.loc[2025, "gen_25_29"], 2),
    "gen_25_29_cum_2019_2025": r((series.loc[2025, "gen_25_29"] / series.loc[2019, "gen_25_29"] - 1) * 100, 2),
}

# ---- 仮説の判定 ----
main["judgement"] = {
    "H1": "支持" if main["H1_ng_univ_yoy"]["rank_2025_of"][0] == 1 else "外れ",
    "H2": "支持" if main["H2_gap_univ_all"]["rank_2025_of"][0] == 1 else "外れ",
    "H3": "支持" if main["H3_support"] else "外れ",
    "H4": "支持" if main["H4_old"]["n_years_ge"] > 0 else "外れ",
}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True))
