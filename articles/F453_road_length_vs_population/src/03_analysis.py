"""全国の道路の長さと人口、種類別の伸び、県ごとの伸び。results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
nat = pd.read_csv(ROOT / "data" / "road_national.csv")
pop = pd.read_csv(ROOT / "data" / "population_thousand.csv", index_col="code")
pop.columns = pop.columns.astype(int)
pref = pd.read_csv(ROOT / "data" / "road_pref.csv", index_col="code")

# 人口を道路の時点 t に線形補間（人口は各年10月1日 = 年 + 0.75）
pn = pop.loc[0].dropna()
px = np.array(pn.index) + 0.75
nat["pop_thousand"] = np.interp(nat.t, px, pn.values, left=np.nan, right=np.nan)
nat["expressway_f"] = nat.expressway.fillna(0)
nat["total_km"] = nat.general + nat.expressway_f
nat["m_per_person"] = nat.total_km * 1000 / (nat.pop_thousand * 1000)
nat.to_csv(R / "national_road_pop.csv", index=False, float_format="%.4f")
T = nat.set_index("t")


def chg(col, a, b):
    return float(T.loc[b, col] - T.loc[a, col]), float((T.loc[b, col] / T.loc[a, col] - 1) * 100)


A, B = 2008.25, 2024.25
main = {"t_start": A, "t_end": B}
for c in ["total_km", "general", "expressway_f", "national", "prefectural", "municipal", "pop_thousand", "m_per_person"]:
    d, p = chg(c, A, B)
    main[f"{c}_start"] = round(float(T.loc[A, c]), 1); main[f"{c}_end"] = round(float(T.loc[B, c]), 1)
    main[f"{c}_diff"] = round(d, 1); main[f"{c}_pct"] = round(p, 2)
inc = {k: main[f"{k}_diff"] for k in ["expressway_f", "national", "prefectural", "municipal"]}
main["increase_by_type_km"] = inc
main["increase_share_pct"] = {k: round(v / sum(inc.values()) * 100, 1) for k, v in inc.items()}
main["pop_peak_year"] = int(pn.idxmax()); main["pop_peak_thousand"] = float(pn.max())
# 1年あたりの伸び（km/年）の時代別
def per_year(a, b, col="total_km"):
    return round((float(T.loc[b, col]) - float(T.loc[a, col])) / (b - a), 1)
main["km_per_year_1990_2008"] = per_year(1990.25, 2008.25)
main["km_per_year_2008_2024"] = per_year(2008.25, 2024.25)
main["km_per_year_2019_2024"] = per_year(2019.25, 2024.25)
main["muni_km_per_year_1990_2008"] = per_year(1990.25, 2008.25, "municipal")
main["muni_km_per_year_2008_2024"] = per_year(2008.25, 2024.25, "municipal")

# 県ごと：道路 2015年4月1日→2024年3月31日、人口 2015年10月→2023年10月
P0, P1 = 2015, 2023
pf = pref.copy()
pf["road_pct"] = (pf.road_2025ed_km / pf.road_2016ed_km - 1) * 100
pf["road_pref_only_pct"] = (pf.road_pref_only_2025ed_km / pf.road_pref_only_2016ed_km - 1) * 100
pf["pop_pct"] = (pop.loc[pf.index, P1] / pop.loc[pf.index, P0] - 1) * 100
pf["pop_pct_2014_2024"] = (pop.loc[pf.index, 2024] / pop.loc[pf.index, 2014] - 1) * 100
pf["m_per_person_2015"] = pf.road_2016ed_km * 1000 / (pop.loc[pf.index, P0] * 1000)
pf["m_per_person_2023"] = pf.road_2025ed_km * 1000 / (pop.loc[pf.index, P1] * 1000)
pf.to_csv(R / "prefecture_road_pop.csv", float_format="%.4f")
dec = pf[pf.pop_pct < 0]
main["n_pref_pop_decline"] = int(len(dec)); main["n_pref_pop_decline_road_up"] = int((dec.road_pct > 0).sum())
main["share_pop_decline_road_up"] = round(float((dec.road_pct > 0).mean() * 100), 1)
main["n_pref_road_down"] = int((pf.road_pct < 0).sum())
main["corr_pop_road"] = round(float(np.corrcoef(pf.pop_pct, pf.road_pct)[0, 1]), 3)
main["median_road_pct_pop_decline"] = round(float(dec.road_pct.median()), 2)
main["median_road_pct_pop_growth"] = round(float(pf[pf.pop_pct >= 0].road_pct.median()), 2) if (pf.pop_pct >= 0).any() else None
main["n_pref_pop_growth"] = int((pf.pop_pct >= 0).sum())
main["nat_road_pct_2015_2024"] = round(float((pf.road_2025ed_km.sum() / pf.road_2016ed_km.sum() - 1) * 100), 2)
main["hypotheses"] = {
    "H1": "支持" if main["total_km_diff"] > 0 else "外れ",
    "H2": "支持" if max(inc, key=inc.get) == "municipal" else "外れ",
    "H3": "支持" if main["m_per_person_pct"] >= 3 else "外れ",
    "H4": "支持" if main["share_pop_decline_road_up"] >= 75 else "外れ",
}
# 頑健性
rb = []
d, p = chg("total_km", 2010.75 if 2010.75 in T.index else 2010.25, B); rb.append(dict(check="始まりを2010年度当初にする：道路の増加率", value=round(p, 2), unit="%"))
d, p = chg("m_per_person", 2010.25, B); rb.append(dict(check="始まりを2010年度当初にする：1人あたりの道路の増加率", value=round(p, 2), unit="%"))
d, p = chg("general", A, B); rb.append(dict(check="高速道路を除く一般道路だけ：2008→2024年の増加率", value=round(p, 2), unit="%"))
dec2 = pf[pf.pop_pct < 0]; rb.append(dict(check="県の行だけ（政令市を足さない）：人口が減った県で道路が増えた割合", value=round(float((dec2.road_pref_only_pct > 0).mean() * 100), 1), unit="%"))
dec3 = pf[pf.pop_pct_2014_2024 < 0]; rb.append(dict(check="人口の時点を2014→2024年にする：人口が減った県で道路が増えた割合", value=round(float((dec3.road_pct > 0).mean() * 100), 1), unit="%"))
rb.append(dict(check="人口の時点を2014→2024年にする：人口が減った県の数", value=int(len(dec3)), unit="県"))
rb.append(dict(check="県の道路の伸びと人口の伸びの相関（2015→2023/24）", value=main["corr_pop_road"], unit="相関係数"))
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {r.check: r.value for r in rbd.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(rbd.to_string())
