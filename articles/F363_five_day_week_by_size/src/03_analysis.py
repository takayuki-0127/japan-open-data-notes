"""03_analysis.py : 完全週休2日制（以上）の企業割合の規模の差の推移（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "weekly_holiday_by_size.csv")
SZ = ["計", "1000人以上", "300〜999人", "100〜299人", "30〜99人"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


add = np.where(d.year <= 2008, 0.0, np.where(d.year <= 2023, d["more"].fillna(0), d["w3any"].fillna(0)))
d["full_or_more"] = d["full"] + add
d.round(2).to_csv(RES / "shares_by_size_year.csv", index=False)
fm = d.pivot_table(index="year", columns="size", values="full_or_more")[SZ]
fu = d.pivot_table(index="year", columns="size", values="full")[SZ]
w1 = d.pivot_table(index="year", columns="size", values="w1")[SZ]
gap = (fm["1000人以上"] - fm["30〜99人"]).rename("gap_large_small")
gap_full = (fu["1000人以上"] - fu["30〜99人"]).rename("gap_full")
gap_mid = (fm["300〜999人"] - fm["100〜299人"]).rename("gap_mid")
ts = pd.concat([fm.add_prefix("fm_"), gap, gap_full, gap_mid], axis=1)
ts["gap_ma3"] = gap.rolling(3, center=True).mean()
ts.round(3).to_csv(RES / "gap_timeseries.csv")

main = {"full_or_more": {int(y): {s: r(fm.loc[y, s], 1) for s in SZ} for y in [2001, 2008, 2009, 2014, 2015, 2019, 2023, 2024, 2025]}}
main["full_only"] = {int(y): {s: r(fu.loc[y, s], 1) for s in SZ} for y in [2001, 2008, 2015, 2023, 2024, 2025]}
main["gap"] = {int(y): r(v, 2) for y, v in gap.items()}
main["gap_full"] = {int(y): r(v, 2) for y, v in gap_full.items()}
# 段差（2008→2009、2023→2024）
main["step_check"] = {"2008_2009_total": [r(fm.loc[2008, "計"], 1), r(fm.loc[2009, "計"], 1)],
                      "2023_2024_total": [r(fm.loc[2023, "計"], 1), r(fm.loc[2024, "計"], 1)],
                      "more_2023_total": r(d[(d.year == 2023) & (d["size"] == "計")]["more"].iloc[0], 1),
                      "w3any_2024_total": r(d[(d.year == 2024) & (d["size"] == "計")]["w3any"].iloc[0], 1)}
# H1
main["H1"] = {"gap_2025": r(gap.loc[2025], 2)}
# H2
main["H2"] = {"gap_2001": r(gap.loc[2001], 2), "gap_2025": r(gap.loc[2025], 2), "ratio": r(gap.loc[2025] / gap.loc[2001], 3),
              "gap_ma3_2002": r(ts.gap_ma3.loc[2002], 2), "gap_ma3_2024": r(ts.gap_ma3.loc[2024], 2),
              "min_year": int(gap.idxmin()), "min_value": r(gap.min(), 2)}
# H3：5年ごとの変化
ch5 = (gap - gap.shift(5)).dropna()
ch5.round(3).to_csv(RES / "gap_change_5yr.csv", header=["gap_change_5yr"])
early = ch5[ch5.index <= 2014]
late = ch5[ch5.index >= 2020]  # 2015年以降に始まる5年
main["H3"] = {"most_negative_end_year": int(ch5.idxmin()), "most_negative_value": r(ch5.min(), 2),
              "min_early_end_le_2014": r(early.min(), 2), "min_early_end_year": int(early.idxmin()),
              "min_late_start_ge_2015": r(late.min(), 2), "min_late_end_year": int(late.idxmin()),
              "all": {int(k): r(v, 2) for k, v in ch5.items()}}
# H4
main["H4"] = {"small_2001": r(fm.loc[2001, "30〜99人"], 1), "small_2025": r(fm.loc[2025, "30〜99人"], 1),
              "diff": r(fm.loc[2025, "30〜99人"] - fm.loc[2001, "30〜99人"], 1),
              "large_2001": r(fm.loc[2001, "1000人以上"], 1), "large_2025": r(fm.loc[2025, "1000人以上"], 1)}
main["judgement"] = {"H1": "支持" if gap.loc[2025] >= 10 else "外れ",
                     "H2": "支持" if gap.loc[2025] <= gap.loc[2001] / 2 else "外れ",
                     "H3": "支持" if late.min() < early.min() else "外れ",
                     "H4": "支持" if main["H4"]["diff"] >= 20 else "外れ"}
# 頑健性
rb = []


def row(name, s, y0, y1):
    rb.append({"check": name, "y0": y0, "v0": r(s.loc[y0], 2), "y1": y1, "v1": r(s.loc[y1], 2),
               "ratio": r(s.loc[y1] / s.loc[y0], 3) if s.loc[y0] else None})


row("主：完全週休2日制以上、1,000人以上−30〜99人", gap, 2001, 2025)
row("1 完全週休2日制だけ", gap_full, 2001, 2025)
row("2 300〜999人−100〜299人", gap_mid, 2001, 2025)
row("3 区分の変わらない期間（2009→2023年）", gap, 2009, 2023)
ma = ts.gap_ma3
rb.append({"check": "4 3年移動平均（2002年→2024年）", "y0": 2002, "v0": r(ma.loc[2002], 2), "y1": 2024, "v1": r(ma.loc[2024], 2), "ratio": r(ma.loc[2024] / ma.loc[2002], 3)})
rbd = pd.DataFrame(rb)
rbd.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
# 2009〜2023年の中の5年変化の最小
c59 = ch5[(ch5.index >= 2014) & (ch5.index <= 2023)]
main["H3_within_2009_2023"] = {int(k): r(v, 2) for k, v in c59.items()}

# 問い直し：週休1日制（又は1日半制）の割合
w = w1[["1000人以上", "300〜999人", "100〜299人", "30〜99人", "計"]]
w.round(2).to_csv(RES / "requestion_one_day_off.csv")
main["requestion_w1"] = {int(y): {s: r(w.loc[y, s], 1) for s in w.columns} for y in [2001, 2008, 2015, 2019, 2023, 2025]}
# 30〜99人と1000人以上の「完全週休2日制より少ない（月に何回か土曜も休む等）」
less = d.pivot_table(index="year", columns="size", values="less")
main["less_2009_2025"] = {int(y): {s: r(less.loc[y, s], 1) for s in ["1000人以上", "30〜99人", "計"]} for y in [2009, 2015, 2023, 2025]}

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "judgement", "step_check", "robustness", "requestion_w1", "less_2009_2025"]}, ensure_ascii=False, indent=1))
print(ts.round(1).to_string())
