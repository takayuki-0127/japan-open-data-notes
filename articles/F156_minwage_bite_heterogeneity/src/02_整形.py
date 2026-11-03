"""県×年のパネルを作る（賃金：6月調査、雇用：暦年）。賃金の低さ（bite）は基準期間の値で固定する。"""
import numpy as np, pandas as pd
from common import RAW, DATA, PREFS, REGION

mw = pd.read_csv(RAW / "minimum_wage_2002_2026.csv").set_index("pref")
mw = mw[[str(y) for y in range(2002, 2027)]].astype(float)
mw.columns = mw.columns.astype(int)
mw = mw.loc[PREFS]
w = pd.read_csv(RAW / "wage_short_pref_2009_2025.csv")

# 6月の調査時点で効いている最低賃金＝前年度（前年10月前後に改定）の額
w["mw_june"] = [mw.loc[p, y - 1] for p, y in zip(w.pref, w.year)]
w["mw_june_prev"] = [mw.loc[p, y - 2] for p, y in zip(w.pref, w.year)]
w = w.sort_values(["code", "year"])
w["kaitz"] = w["mw_june"] / w["wage"]
w["dlw"] = w.groupby("code")["wage"].transform(lambda s: np.log(s).diff()) * 100
w["dlmw"] = (np.log(w["mw_june"]) - np.log(w["mw_june_prev"])) * 100
w["dlworkers"] = w.groupby("code")["workers10"].transform(lambda s: np.log(s).diff()) * 100
w["region"] = w.pref.map(REGION)

# 賃金の低さ（基準）：2009〜11年の「最低賃金÷短時間労働者の平均時給」の平均。推定は2012年以降の変化だけを使う
base = w[w.year.between(2009, 2011)].groupby("code").agg(bite0=("kaitz", "mean"), wage0=("wage", "mean"))
# 別の測り方：①2011年度の最低賃金の水準（調査の誤差を含まない）②F17 と同じ2015年の bite
base["lmw0"] = np.log(mw.loc[PREFS, 2011].values)
b15 = w[w.year == 2015].set_index("code")
base["bite15"] = mw.loc[PREFS, 2015].values / b15["wage"]
w = w.merge(base, left_on="code", right_index=True)

# 雇用（労働力調査モデル推計値、暦年）。最低賃金は暦年換算（F01 と同じ）
e = pd.read_csv(RAW / "f01_panel.csv").sort_values(["code", "year"])
e["dlmw"] = e.groupby("code")["log_mw"].diff() * 100
e["d_emp"] = e.groupby("code")["emp_rate"].diff()
e["d_unemp"] = e.groupby("code")["unemp_rate"].diff()
e["d_jor"] = e.groupby("code")["jor"].diff()
e["lag_d_emp"] = e.groupby("code")["d_emp"].shift()
e["lead_dlmw"] = e.groupby("code")["dlmw"].shift(-1)
e["region"] = e["code"].map({i + 1: REGION[p] for i, p in enumerate(PREFS)})
e = e.merge(base, left_on="code", right_index=True)
# 賃金の側の先行（来年の引き上げ）
w["lead_dlmw"] = w.groupby("code")["dlmw"].shift(-1)

w.to_csv(DATA / "panel_wage.csv", index=False)
e.to_csv(DATA / "panel_emp.csv", index=False)
base.round(5).to_csv(DATA / "pref_bite.csv")
print(base.describe().round(3))
print("region NA", e.region.isna().sum())
