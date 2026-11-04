# 02 整形の確認：20区分の合計が1440分（24時間）になっているか
import os, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = pd.read_csv(os.path.join(ROOT, "data", "time_use_by_age_1976_2021.csv"))
a = a[~a.activity.str.contains("次活動") & (a.year >= 1996)]
s = a.groupby(["sex", "group", "age", "year"]).value.sum()
print("合計の範囲（分）:", s.min(), "〜", s.max(), " 行数:", len(s))
print("1440分からのずれが3分を超える行:", int((s.sub(1440).abs() > 3).sum()))
