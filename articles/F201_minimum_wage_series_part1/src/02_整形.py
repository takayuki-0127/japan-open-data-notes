"""パネルを整える：就業のパネル（県×年）と時給のパネル、県の賃金の低さ（3分位）。"""
import numpy as np, pandas as pd
from common import RAW, DATA

p = pd.read_csv(RAW / "f01_panel.csv")
bite = pd.read_csv(RAW / "f156_pref_bite.csv")
# 基準期間（2009〜11年）の bite で3つに分ける（高＝最低賃金が平均時給に近い＝賃金の低い県）
bite["bite_terc"] = pd.qcut(bite["bite0"].rank(method="first"), 3, labels=["低", "中", "高"])
p = p.merge(bite[["code", "bite0", "bite_terc"]], on="code", how="left")
p = p.sort_values(["code", "year"])
p["d_emp"] = p.groupby("code")["emp_rate"].diff()
p["d_unemp"] = p.groupby("code")["unemp_rate"].diff()
p["d_lmw"] = p.groupby("code")["log_mw"].diff()
p.to_csv(DATA / "panel_emp.csv", index=False)

w = pd.read_csv(RAW / "f156_panel_wage.csv")
w = w.merge(bite[["code", "bite_terc"]], on="code", how="left")
w.to_csv(DATA / "panel_wage.csv", index=False)
print(p.shape, w.shape, p.year.min(), p.year.max())
