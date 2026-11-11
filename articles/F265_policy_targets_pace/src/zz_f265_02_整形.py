"""F265 02 整形：3つの指標を「目標の年」とそろえた年の系列にする。"""
import pathlib, pandas as pd, numpy as np
base = pathlib.Path(__file__).resolve().parents[1]
raw, out = base / "data" / "raw", base / "data" / "processed"
out.mkdir(parents=True, exist_ok=True)

m = pd.read_csv(raw / "mhlw_koyoukintou_male_leave.csv")
male = pd.DataFrame({"indicator": "male_leave", "year": m["fiscal_year_survey"], "value": m["male_rate"],
                     "published": m["fiscal_year_survey"] + 1.58})  # 令和T年度（FY T）は翌年7月末公表 → T+1.58
pl = pd.read_csv(raw / "jilpt_g0504_paid_leave.csv")
paid = pd.DataFrame({"indicator": "paid_leave", "year": pl["survey_year"] - 1, "value": pl["take_rate"],
                     "published": pl["survey_year"] + 0.83, "survey_year": pl["survey_year"]})  # 調査年の10〜11月公表
f = pd.read_csv(raw / "lfs_female_25_44_counts.csv")
emp = f[["emp25_29", "emp30_34", "emp35_39", "emp40_44"]].sum(axis=1)
pop = f[["pop25_29", "pop30_34", "pop35_39", "pop40_44"]].sum(axis=1)
fem = pd.DataFrame({"indicator": "female_emp", "year": f["year"], "value": (100 * emp / pop).round(4),
                    "published": f["year"] + 1.08, "emp_10k": emp, "pop_10k": pop})  # 翌年1月末公表
df = pd.concat([male, paid, fem], ignore_index=True)
df.to_csv(out / "series.csv", index=False)

# 公表値との照合（女性就業率：厚生労働省 001558023.pdf のグラフの値）
official = {1985: 56.5, 1990: 60.5, 1995: 60.5, 2000: 61.2, 2005: 64.0, 2010: 66.5, 2015: 71.6, 2016: 72.7, 2017: 74.3,
            2018: 76.5, 2019: 77.7, 2020: 77.4, 2021: 78.6, 2022: 79.8, 2023: 80.8, 2024: 81.9}
chk = fem.set_index("year").loc[list(official), ["value"]].assign(official=pd.Series(official))
chk["diff"] = (chk["value"] - chk["official"]).round(3)
chk.to_csv(out / "female_emp_check.csv")
print(chk.to_string())
print(df.groupby("indicator")["year"].agg(["min", "max", "count"]))
