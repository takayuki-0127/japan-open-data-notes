"""03_analysis.py : 男性の育児休業取得率の規模別の推移と、取得期間の分布の変化（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
rate = pd.read_csv(ROOT / "data" / "leave_rate.csv")
per = pd.read_csv(ROOT / "data" / "leave_period_male.csv")
SZ = ["500人以上", "100〜499人", "30〜99人", "5〜29人"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


m = rate.pivot_table(index="year", columns="size", values="male")
f = rate.pivot_table(index="year", columns="size", values="female")
t = m[["総数"] + SZ + ["30人以上（再掲）"]].copy()
t["gap_500_vs_5_29"] = m["500人以上"] - m["5〜29人"]
t["ratio_500_vs_5_29"] = m["500人以上"] / m["5〜29人"]
t["gap_500_vs_30plus"] = m["500人以上"] - m["30人以上（再掲）"]
t["gap_30plus_vs_5_29"] = m["30人以上（再掲）"] - m["5〜29人"]
t.round(3).to_csv(RES / "male_rate_by_size.csv")
main = {"male_total": {int(y): r(v) for y, v in m["総数"].items()}}
main["male_by_size"] = {int(y): {s: r(m.loc[y, s]) for s in SZ} for y in [2009, 2015, 2019, 2020, 2022, 2023, 2024, 2025]}
ch = {s: r(m.loc[2025, s] - m.loc[2019, s]) for s in SZ}
main["H1"] = {"change_2019_2025": ch, "min": min(ch.values())}
main["H2"] = {"gap_2025": r(t.loc[2025, "gap_500_vs_5_29"])}
main["H3"] = {"gap_2019": r(t.loc[2019, "gap_500_vs_5_29"]), "gap_2025": r(t.loc[2025, "gap_500_vs_5_29"]),
              "ratio_2019": r(t.loc[2019, "ratio_500_vs_5_29"], 3), "ratio_2025": r(t.loc[2025, "ratio_500_vs_5_29"], 3)}
main["gap_by_year"] = {int(y): r(v) for y, v in t.gap_500_vs_5_29.items()}
# 取得期間
p = per.copy()
p["lt2w"] = p["5日未満"] + p["5日～2週間未満"]
p["w2_1m"] = p["2週間～1か月未満"]
p["m1_3"] = p["1か月～3か月未満"]
p["ge3m"] = p[["3か月～6か月未満", "6か月～8か月未満", "8か月～10か月未満", "10か月～12か月未満", "12か月～18か月未満",
               "18か月～24か月未満", "24か月～36か月未満", "36か月以上"]].sum(axis=1)
p["ge1m"] = p.m1_3 + p.ge3m
p[["year", "size", "lt2w", "w2_1m", "m1_3", "ge3m", "ge1m", "5日未満"]].round(2).to_csv(RES / "male_period_grouped.csv", index=False)
pp = p.set_index(["size", "year"])
main["period_total"] = {int(y): {k: r(pp.loc[("総数", y), k], 1) for k in ["5日未満", "lt2w", "w2_1m", "m1_3", "ge3m", "ge1m"]} for y in [2012, 2015, 2018, 2021, 2023, 2025]}
main["H4"] = {"lt2w_2018": r(pp.loc[("総数", 2018), "lt2w"], 1), "lt2w_2025": r(pp.loc[("総数", 2025), "lt2w"], 1)}
main["period_size"] = {s: {int(y): {k: r(pp.loc[(s, y), k], 1) for k in ["lt2w", "ge1m"]} for y in [2018, 2025]} for s in SZ}
# 頑健性
rb = [
    {"check": "主：差（500人以上 − 5〜29人）", "v2019": r(t.loc[2019, "gap_500_vs_5_29"]), "v2025": r(t.loc[2025, "gap_500_vs_5_29"]), "widened": bool(t.loc[2025, "gap_500_vs_5_29"] > t.loc[2019, "gap_500_vs_5_29"])},
    {"check": "1 比（500人以上 ÷ 5〜29人）", "v2019": r(t.loc[2019, "ratio_500_vs_5_29"], 3), "v2025": r(t.loc[2025, "ratio_500_vs_5_29"], 3), "widened": bool(t.loc[2025, "ratio_500_vs_5_29"] > t.loc[2019, "ratio_500_vs_5_29"])},
    {"check": "2 差（30人以上 − 5〜29人）", "v2019": r(t.loc[2019, "gap_30plus_vs_5_29"]), "v2025": r(t.loc[2025, "gap_30plus_vs_5_29"]), "widened": bool(t.loc[2025, "gap_30plus_vs_5_29"] > t.loc[2019, "gap_30plus_vs_5_29"])},
    {"check": "3 起点を2020年度に（差）", "v2019": r(t.loc[2020, "gap_500_vs_5_29"]), "v2025": r(t.loc[2025, "gap_500_vs_5_29"]), "widened": bool(t.loc[2025, "gap_500_vs_5_29"] > t.loc[2020, "gap_500_vs_5_29"])},
    {"check": "3' 3年平均（2018〜20年度→2023〜25年度、差）", "v2019": r(t.gap_500_vs_5_29.loc[2018:2020].mean()), "v2025": r(t.gap_500_vs_5_29.loc[2023:2025].mean()), "widened": bool(t.gap_500_vs_5_29.loc[2023:2025].mean() > t.gap_500_vs_5_29.loc[2018:2020].mean())},
    {"check": "3'' 3年平均の比（2018〜20年度→2023〜25年度）", "v2019": r(m["500人以上"].loc[2018:2020].mean() / m["5〜29人"].loc[2018:2020].mean(), 3),
     "v2025": r(m["500人以上"].loc[2023:2025].mean() / m["5〜29人"].loc[2023:2025].mean(), 3),
     "widened": bool(m["500人以上"].loc[2023:2025].mean() / m["5〜29人"].loc[2023:2025].mean() > m["500人以上"].loc[2018:2020].mean() / m["5〜29人"].loc[2018:2020].mean())},
    {"check": "4a H4 500人以上（2週間未満、2018→2025）", "v2019": r(pp.loc[("500人以上", 2018), "lt2w"], 1), "v2025": r(pp.loc[("500人以上", 2025), "lt2w"], 1), "widened": None},
    {"check": "4b H4 5〜29人（2週間未満、2018→2025）", "v2019": r(pp.loc[("5〜29人", 2018), "lt2w"], 1), "v2025": r(pp.loc[("5〜29人", 2025), "lt2w"], 1), "widened": None},
]
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
# 問い直し：男性 ÷ 女性
q = (m[SZ + ["総数"]] / f[SZ + ["総数"]] * 100)
q.round(2).to_csv(RES / "requestion_male_over_female.csv")
main["requestion"] = {int(y): {s: r(q.loc[y, s], 1) for s in SZ + ["総数"]} for y in [2019, 2025]}
main["female_2025"] = {s: r(f.loc[2025, s], 1) for s in SZ + ["総数"]}
main["female_2019"] = {s: r(f.loc[2019, s], 1) for s in SZ + ["総数"]}
main["judgement"] = {"H1": "支持" if min(ch.values()) >= 20 else "外れ", "H2": "支持" if t.loc[2025, "gap_500_vs_5_29"] >= 10 else "外れ",
                     "H3": "支持" if t.loc[2025, "gap_500_vs_5_29"] > t.loc[2019, "gap_500_vs_5_29"] else "外れ",
                     "H4": "支持" if pp.loc[("総数", 2025), "lt2w"] < pp.loc[("総数", 2018), "lt2w"] else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as fo:
    json.dump(main, fo, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "judgement", "robustness", "requestion", "period_total", "period_size", "female_2025", "female_2019"]}, ensure_ascii=False, indent=0))
