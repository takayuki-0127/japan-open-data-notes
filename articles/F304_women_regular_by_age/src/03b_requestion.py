"""問い直し（結果を見てから足した）：
同じ年で見た「25〜29歳から35〜39歳への落ち込み」は、2025年のほうが深かった（25〜29歳の率が大きく上がったため）。
では、同じ生まれ年の集まり（コホート）を10年後まで追うと、30代での落ち込みは小さくなったのか。
25〜29歳だった年 y と、10年後 y+10 の35〜39歳の正規雇用率を比べる（y = 2002〜2015）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "emptype_age_sex.csv")
f = d[d.sex == "female"].copy(); f["rate"] = 100 * f.regular / f.population
R = f.pivot(index="year", columns="age", values="rate")
r3 = lambda x: round(float(x), 3)
rows = []
for y in range(2002, 2016):
    for a0, a1 in (("25～29歳", "35～39歳"), ("30～34歳", "40～44歳"), ("20～24歳", "30～34歳")):
        rows.append(dict(start_year=y, birth_years=f"{y - int(a0[:2]) - 4}〜{y - int(a0[:2])}年生まれ", age_start=a0, age_end=a1,
                         rate_start=r3(R.loc[y, a0]), rate_end=r3(R.loc[y + 10, a1]), change=r3(R.loc[y + 10, a1] - R.loc[y, a0])))
c = pd.DataFrame(rows); c.to_csv(RES / "requestion_cohort.csv", index=False)
k = c[c.age_start == "25～29歳"].set_index("start_year")
out = dict(cohort_25_29_to_35_39={int(y): [k.loc[y, "rate_start"], k.loc[y, "rate_end"], k.loc[y, "change"]] for y in (2002, 2005, 2010, 2015)},
           change_first=r3(k.change.iloc[0]), change_last=r3(k.change.iloc[-1]),
           change_mean_2002_2006=r3(k.loc[2002:2006, "change"].mean()), change_mean_2011_2015=r3(k.loc[2011:2015, "change"].mean()))
k2 = c[c.age_start == "30～34歳"].set_index("start_year")
out["cohort_30_34_to_40_44_first_last"] = [r3(k2.change.iloc[0]), r3(k2.change.iloc[-1])]
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(k[["birth_years", "rate_start", "rate_end", "change"]].to_string())
