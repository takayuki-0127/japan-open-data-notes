"""割合の推移、建て方・建築の時期別、都道府県と持ち家率の関係。仮説・頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
ts = pd.read_csv(ROOT / "data" / "timeseries.csv")
tk = pd.read_csv(ROOT / "data" / "tatekata.csv")
jk = pd.read_csv(ROOT / "data" / "jiki.csv")
ts["share"] = ts.solar_yes / ts.total * 100
ts["share_known"] = ts.solar_yes / (ts.solar_yes + ts.solar_no) * 100

nat = ts[ts.area == "全国"].pivot(index="year", columns="tenure", values=["share", "share_known", "solar_yes", "total"])
natf = pd.DataFrame({"share_all": nat[("share", "総数")], "share_own": nat[("share", "持ち家")], "share_rent": nat[("share", "借家")],
                     "share_known_all": nat[("share_known", "総数")], "solar_yes_all": nat[("solar_yes", "総数")],
                     "solar_yes_own": nat[("solar_yes", "持ち家")], "solar_yes_rent": nat[("solar_yes", "借家")], "total_all": nat[("total", "総数")]})
natf.round(4).to_csv(R / "national.csv")
inc = natf.share_all.diff()
inc_own = natf.share_own.diff(); inc_known = natf.share_known_all.diff()

tk["share"] = tk.solar_yes / tk.total * 100
tkw = tk.pivot(index="year", columns="type", values="share")
tkw.round(4).to_csv(R / "tatekata_share.csv")
r_det_apt = float(tkw.loc[2023, "一戸建"] / tkw.loc[2023, "共同住宅"])

jk["share"] = jk.solar_yes / jk.total * 100
jk.round(4).to_csv(R / "jiki_share.csv", index=False)
own = jk[jk.tenure == "持ち家"].set_index("period")
new_periods = ["2011～2015年", "2016～2018年", "2019年", "2020年", "2021年", "2022年", "2023年1月～9月"]
own_new = float(own.loc[new_periods, "solar_yes"].sum() / own.loc[new_periods, "total"].sum() * 100)
own_all = float(own.loc["総数", "share"])

# 都道府県（表の並び＝北から南）
prefs = [a for a in ts.area.unique() if a.endswith(("都", "道", "府", "県")) and a != "全国"][:47]
P = ts[ts.area.isin(prefs)]
pw = P.pivot_table(index="area", columns=["tenure", "year"], values=["share", "total"]).reindex(prefs)
pref = pd.DataFrame({"share_2013": pw[("share", "総数", 2013)], "share_2018": pw[("share", "総数", 2018)], "share_2023": pw[("share", "総数", 2023)],
                     "own_rate_2018": pw[("total", "持ち家", 2018)] / pw[("total", "総数", 2018)] * 100,
                     "own_rate_2023": pw[("total", "持ち家", 2023)] / pw[("total", "総数", 2023)] * 100,
                     "share_own_2023": pw[("share", "持ち家", 2023)]})
pref.index.name = "pref"
REG = ["北海道"] + ["東北"] * 6 + ["関東"] * 7 + ["中部"] * 9 + ["近畿"] * 7 + ["中国・四国"] * 9 + ["九州・沖縄"] * 8
pref["region"] = REG
tot = P[(P.tenure == "総数") & (P.year == 2023)].set_index("area").reindex(prefs)
reg = tot.assign(region=REG).groupby("region", sort=False)[["solar_yes", "total"]].sum()
reg["share_2023"] = reg.solar_yes / reg.total * 100
reg.round(3).to_csv(R / "regions.csv")
pref.round(3).to_csv(R / "prefectures.csv")
r23, p23 = stats.pearsonr(pref.share_2023, pref.own_rate_2023)
s23 = stats.spearmanr(pref.share_2023, pref.own_rate_2023).statistic
r18, _ = stats.pearsonr(pref.share_2018, pref.own_rate_2018)

rob = pd.DataFrame([
    {"check": "本線：総数、分母に不詳を含む", "inc_2008_13": round(float(inc.loc[2013]), 2), "inc_2013_18": round(float(inc.loc[2018]), 2), "inc_2018_23": round(float(inc.loc[2023]), 2)},
    {"check": "分母から設備の不詳を除く", "inc_2008_13": round(float(inc_known.loc[2013]), 2), "inc_2013_18": round(float(inc_known.loc[2018]), 2), "inc_2018_23": round(float(inc_known.loc[2023]), 2)},
    {"check": "持ち家だけ", "inc_2008_13": round(float(inc_own.loc[2013]), 2), "inc_2013_18": round(float(inc_own.loc[2018]), 2), "inc_2018_23": round(float(inc_own.loc[2023]), 2)},
])
rob.to_csv(R / "robustness.csv", index=False)
cor = pd.DataFrame([{"check": "本線：2023年 ピアソン", "r": round(float(r23), 3)}, {"check": "2023年 スピアマン", "r": round(float(s23), 3)},
                    {"check": "2018年 ピアソン", "r": round(float(r18), 3)}])
cor.to_csv(R / "robustness_corr.csv", index=False)

main = {
    "share_all": {int(k): round(float(v), 2) for k, v in natf.share_all.items()},
    "share_own": {int(k): round(float(v), 2) for k, v in natf.share_own.items()},
    "share_rent": {int(k): round(float(v), 2) for k, v in natf.share_rent.items()},
    "solar_yes_all": {int(k): float(v) for k, v in natf.solar_yes_all.items()},
    "increment_pt": {int(k): round(float(v), 2) for k, v in inc.dropna().items()},
    "tatekata_share_2023": {k: round(float(v), 2) for k, v in tkw.loc[2023].items()},
    "tatekata_share_2008": {k: round(float(v), 2) for k, v in tkw.loc[2008].items()},
    "detached_vs_apartment_2023": round(r_det_apt, 1),
    "own_share_all_2023": round(own_all, 2), "own_share_built_2011_2023": round(own_new, 2),
    "own_new_vs_all_ratio": round(own_new / own_all, 2),
    "pref_corr_2023": round(float(r23), 3), "pref_corr_2023_spearman": round(float(s23), 3), "pref_corr_2018": round(float(r18), 3),
    "region_share_2023": {k: round(float(v), 2) for k, v in reg.share_2023.items()},
    "pref_share_2023_min": round(float(pref.share_2023.min()), 2), "pref_share_2023_max": round(float(pref.share_2023.max()), 2),
    "hypotheses": {
        "H1_slowdown": {"inc_2013_18": round(float(inc.loc[2018]), 2), "inc_2018_23": round(float(inc.loc[2023]), 2),
                        "result": "支持" if inc.loc[2023] < inc.loc[2018] else "外れ"},
        "H2_detached_10x": {"value": round(r_det_apt, 1), "result": "支持" if r_det_apt >= 10 else "外れ"},
        "H3_new_own_2x": {"value": round(own_new / own_all, 2), "result": "支持" if own_new / own_all >= 2 else "外れ"},
        "H4_pref_corr_ge_0_5": {"value": round(float(r23), 3), "result": "支持" if r23 >= 0.5 else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rob.to_string()); print(cor.to_string())
print(own[["total", "solar_yes", "share"]].round(2).to_string())
