"""県×年のパネルに、処置（最低賃金の上がり幅）・結果（就業率の変化）・県の特徴を付ける"""
import numpy as np, pandas as pd
from common import RAW, DATA

p = pd.read_csv(RAW / "f01_panel.csv").sort_values(["code", "year"])
# 処置：前年からの最低賃金（暦年換算）の上がり幅を、2015年の短時間労働者の平均時給に対する%ptで表す
p["treat"] = p.groupby("code")["mw"].diff() / p["hourly_wage_yen"] * 100
p["treat_pct"] = p.groupby("code")["log_mw"].diff() * 100            # 参考：上昇率（%）
# 結果：就業率・完全失業率の前年差（%pt）
p["d_emp"] = p.groupby("code")["emp_rate"].diff()
p["d_unemp"] = p.groupby("code")["unemp_rate"].diff()
# 前年の動き（交絡の調整用）
p["lag_d_emp"] = p.groupby("code")["d_emp"].shift()
p["lag_d_jor"] = p.groupby("code")["jor"].diff().groupby(p["code"]).shift()

# 2015年の値（引き上げが続く前）
b = p[p.year == 2015].set_index("code")
base = pd.DataFrame({"bite": b["bite"], "wage15": b["hourly_wage_yen"], "emp15": b["emp_rate"],
                     "unemp15": b["unemp_rate"], "jor15": b["jor"], "logpop15": np.log(b["pop15"])})

# 65歳以上の割合（SSDSE-B、2015年度）
sb = pd.read_csv(RAW / "SSDSE-B-2026.csv", encoding="cp932", skiprows=[1])
sb = sb[sb["SSDSE-B-2026"].astype(str) == "2015"].copy()
sb["code"] = sb["Code"].str[1:3].astype(int)
base["age65"] = (sb.set_index("code")["A1303"] / sb.set_index("code")["A1101"] * 100)

# 産業別の従業者の割合（SSDSE-A-2021 の経済センサス2016年を県で合計）
sa = pd.read_csv(RAW / "SSDSE-A-2021.csv", encoding="cp932", skiprows=[1, 2])
sa["code"] = sa["SSDSE-A-2021"].str[1:3].astype(int)
g = sa.groupby("code")[["C2208", "C220837", "C220841", "C220847", "C220850", "C220836"]].sum()
for col, k in [("sh_manu", "C220837"), ("sh_retail", "C220841"), ("sh_food", "C220847"),
               ("sh_welfare", "C220850"), ("sh_constr", "C220836")]:
    base[col] = g[k] / g["C2208"] * 100

df = p.merge(base.drop(columns=["bite"]), left_on="code", right_index=True)
df = df[df.year >= 2010].dropna(subset=["treat", "d_emp", "lag_d_emp", "lag_d_jor"])
df.to_csv(DATA / "f17_panel.csv", index=False)
base.round(4).to_csv(DATA / "f17_pref_features.csv")
print(df.shape, df.year.min(), df.year.max())
print(df.groupby("year")[["treat", "treat_pct", "d_emp"]].agg(["mean", "std"]).round(3))
print(base.describe().round(2).T)
