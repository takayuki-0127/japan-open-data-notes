"""02 整形：住宅・土地統計調査の表を、都道府県×所得階級×世帯人員×住宅の所有の関係の縦長の表にする"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
raw = json.load(open(ROOT / "data/raw/f153_housing_income.json", encoding="utf-8"))
SIZES = ["total", "p1", "p2", "p3", "p4", "p5", "p6", "p7plus"]

# 階級の下限・上限（万円）
B23 = {"01": (0, 100), "02": (100, 150), "03": (150, 200), "04": (200, 300), "05": (300, 400),
       "06": (400, 500), "07": (500, 700), "08": (700, 1000), "09": (1000, 1500), "10": (1500, 2000), "11": (2000, None)}
B18 = {"01": (0, 100), "02": (100, 200), "03": (200, 300), "04": (300, 400), "05": (400, 500),
       "06": (500, 700), "07": (700, 1000), "08": (1000, 1500), "09": (1500, 2000), "10": (2000, None)}


def tidy(rows, bounds, year):
    out = []
    for r in rows:
        code, name = r[0].split("_", 1)
        ten = r[1].split("_", 1)[1]
        inc = r[2].split("_", 1)[0]
        vals = [0 if (v in ("-", "", None) or isinstance(v, str)) else float(v) for v in r[3:11]]
        if inc == "00":
            lo, hi, lab = None, None, "総数"
        elif inc == "99":
            lo, hi, lab = None, None, "不詳"
        else:
            lo, hi = bounds[inc]
            lab = r[2].split("_", 1)[1]
        for s, v in zip(SIZES, vals):
            out.append(dict(year=year, code=code, pref=name, tenure=ten, inc_code=inc, inc_label=lab,
                            lo=lo, hi=hi, size=s, households=v))
    return pd.DataFrame(out)


df = pd.concat([tidy(raw["h23"], B23, 2023), tidy(raw["h18"], B18, 2018)], ignore_index=True)
df.to_csv(ROOT / "data/households_long.csv", index=False, encoding="utf-8")

# 整合のチェック：階級の合計＋不詳＝総数
chk = (df[df.inc_code.isin(["00"])].groupby(["year", "code", "tenure", "size"]).households.sum()
       - df[~df.inc_code.isin(["00"])].groupby(["year", "code", "tenure", "size"]).households.sum())
print("総数との差（世帯）の最大の絶対値：", chk.abs().max())
tot = df[(df.inc_code == "00") & (df["size"] == "total") & (df.tenure == "総数")]
unk = df[(df.inc_code == "99") & (df["size"] == "total") & (df.tenure == "総数")]
m = tot.merge(unk, on=["year", "code"], suffixes=("_t", "_u"))
m["unk_share"] = m.households_u / m.households_t
print(m.groupby("year").unk_share.describe())
print(df.groupby("year").code.nunique())
