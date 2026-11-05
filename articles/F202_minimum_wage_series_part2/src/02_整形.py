"""F202 整形：県×年（2017・2022）の就業調整の割合と最低賃金をつなぐ"""
import json
import numpy as np, pandas as pd
from common import RAW, DATA

mw = pd.read_csv(RAW / "minimum_wage_2002_2026.csv")
mw_pref = mw[mw["pref"] != "全国加重平均"].reset_index(drop=True)
mw_pref["code"] = np.arange(1, 48)
mw_nat = mw[mw["pref"] == "全国加重平均"].iloc[0]

# 全国加重平均の時系列
years = [str(y) for y in range(2002, 2027)]
nat = pd.DataFrame({"year": [int(y) for y in years],
                    "mw_wavg": [float(mw_nat[y]) for y in years]})
nat.to_csv(DATA / "mw_national.csv", index=False)

# 県×年度の最低賃金（長い形）
long = mw_pref.melt(id_vars=["pref", "code"], value_vars=years, var_name="year", value_name="mw")
long["year"] = long["year"].astype(int)
long.to_csv(DATA / "mw_pref_long.csv", index=False)

# 就業構造基本調査 第8表
sh = pd.read_csv(RAW / "shugyo_t8_adjust_pref_2017_2022.csv")
sh = sh[sh["idx"] >= 2].copy()
sh["code"] = sh["idx"] - 1
num = [c for c in sh.columns if c.startswith(("tot_", "adj_", "noadj_"))]
sh[num] = sh[num].apply(pd.to_numeric, errors="coerce")
for g in ("tot", "adj"):
    sh[f"{g}_25_54"] = sh[[f"{g}_25_34", f"{g}_35_44", f"{g}_45_54"]].sum(axis=1)
sh["share_adj"] = 100 * sh["adj_all"] / sh["tot_all"]
sh["share_adj_25_54"] = 100 * sh["adj_25_54"] / sh["tot_25_54"]

# 調査は10月時点。その年度の最低賃金（10月ごろ発効）と、カイツ指標（6月の最低賃金÷短時間労働者の時給、F201）をつなぐ
pw = pd.read_csv(RAW / "f201_panel_wage.csv")[["code", "year", "kaitz", "wage"]]
panel = (sh.merge(long[["code", "year", "mw"]], on=["code", "year"], how="left")
           .merge(pw, on=["code", "year"], how="left"))
panel["lmw"] = np.log(panel["mw"])
panel["hours130_week"] = 1_300_000 / panel["mw"] / 52
panel = panel[["year", "sex", "code", "pref", "tot_all", "adj_all", "share_adj",
               "tot_25_54", "adj_25_54", "share_adj_25_54", "mw", "lmw", "kaitz",
               "wage", "hours130_week"]]
panel.to_csv(DATA / "panel_adjust.csv", index=False)

# 全国の行
nat_sh = pd.read_csv(RAW / "shugyo_t8_adjust_pref_2017_2022.csv")
nat_sh = nat_sh[nat_sh["idx"] == 1][["year", "sex", "tot_all", "adj_all"]].copy()
nat_sh["share_adj"] = 100 * nat_sh["adj_all"] / nat_sh["tot_all"]
nat_sh.to_csv(DATA / "adjust_national.csv", index=False)

# シナリオ用：2025年の県の就業者（千人）、2025年度・2026年度の最低賃金、2025年のカイツ指標
pe = pd.read_csv(RAW / "f201_panel_emp.csv")
e25 = pe[pe["year"] == 2025][["code", "pref", "emp", "pop15", "emp_rate"]]
fj = json.load(open(RAW / "f201_for_F202.json", encoding="utf-8"))["for_F202"]
k25 = pd.Series({int(k): v for k, v in fj["kaitz_2025_by_pref"].items()}, name="kaitz2025")
sc = (e25.merge(mw_pref[["code", "2025", "2026"]].rename(columns={"2025": "mw2025", "2026": "mw2026"}), on="code")
         .merge(k25, left_on="code", right_index=True))
sc.to_csv(DATA / "scenario_base.csv", index=False)
print(panel.groupby(["year", "sex"]).size())
print(sc.head())
