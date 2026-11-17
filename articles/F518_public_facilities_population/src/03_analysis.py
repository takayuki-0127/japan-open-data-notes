"""主な分析：市町村の行政財産の建物の延面積（全国・都道府県）と人口、1人あたり、用途別、施設の数、仮説、頑健性。
延面積は2011年度から（2006〜2010年度の表には公有財産の値がない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
f = pd.read_csv(ROOT / "data" / "pref_facilities.csv")
p = pd.read_csv(ROOT / "data" / "pref_population.csv")
d = f.merge(p, on=["year", "pref_code"], how="left")
d["bld_school"] = d.bld_elem + d.bld_junior + d.bld_compulsory
d["bld_nonschool"] = d.bld_admin_total - d.bld_school
d["bld_ex_housing"] = d.bld_admin_total - d.bld_housing
d["bld_with_general"] = d.bld_admin_total + d.bld_general_total
COLS = ["bld_admin_total", "bld_school", "bld_nonschool", "bld_housing", "bld_ex_housing", "bld_with_general", "bld_honchosha",
        "bld_public_other", "kominkan_n", "toshokan_n", "taiikukan_n", "shisho_n", "jidokan_n", "kokaido_n", "n_municipalities", "pop_thousand"]
nat = d.groupby("year")[COLS].sum()
nat["m2_per_person"] = nat.bld_admin_total / (nat.pop_thousand * 1000)
nat.round(4).to_csv(R / "national_by_year.csv")
Y0, Y1 = 2011, 2024


def r(x, k=1):
    return round(float(x), k)


def pct(a, b):
    return r(100 * (b / a - 1), 2)


pr = d[d.year.isin([Y0, Y1])].pivot(index="pref_code", columns="year", values=["bld_admin_total", "pop_thousand", "bld_ex_housing", "bld_with_general"])
pref = pd.DataFrame({"pop_change_pct": 100 * (pr["pop_thousand"][Y1] / pr["pop_thousand"][Y0] - 1),
                     "area_change_pct": 100 * (pr["bld_admin_total"][Y1] / pr["bld_admin_total"][Y0] - 1)})
for k in ["bld_admin_total", "bld_ex_housing", "bld_with_general"]:
    pref[f"{k}_pc_change_pct"] = 100 * ((pr[k][Y1] / pr["pop_thousand"][Y1]) / (pr[k][Y0] / pr["pop_thousand"][Y0]) - 1)
pref["pc_2024_m2"] = pr["bld_admin_total"][Y1] / (pr["pop_thousand"][Y1] * 1000)
pref.round(3).to_csv(R / "pref_change_2011_2024.csv")
rho = float(np.corrcoef(pref.pop_change_pct, pref.bld_admin_total_pc_change_pct)[0, 1])
sp = float(stats.spearmanr(pref.pop_change_pct, pref.bld_admin_total_pc_change_pct).statistic)
slope = float(np.polyfit(pref.pop_change_pct, pref.bld_admin_total_pc_change_pct, 1)[0])

hyp = {
    "H1": {"area_2011": r(nat.bld_admin_total[Y0] / 1e6, 2), "area_2024": r(nat.bld_admin_total[Y1] / 1e6, 2), "change_pct": pct(nat.bld_admin_total[Y0], nat.bld_admin_total[Y1]),
           "verdict": "支持" if nat.bld_admin_total[Y1] >= nat.bld_admin_total[Y0] else "外れ"},
    "H2": {"pc_change_pct": pct(nat.m2_per_person[Y0], nat.m2_per_person[Y1]), "verdict": "支持" if pct(nat.m2_per_person[Y0], nat.m2_per_person[Y1]) >= 5 else "外れ"},
    "H3": {"pearson": r(rho, 3), "spearman": r(sp, 3), "slope": r(slope, 3), "verdict": "支持" if rho <= -0.5 else "外れ"},
    "H4": {"school_change_pct": pct(nat.bld_school[Y0], nat.bld_school[Y1]), "nonschool_change_pct": pct(nat.bld_nonschool[Y0], nat.bld_nonschool[Y1]),
           "verdict": "支持" if (pct(nat.bld_school[Y0], nat.bld_school[Y1]) <= -5 and nat.bld_nonschool[Y1] > nat.bld_nonschool[Y0]) else "外れ"},
}
# 頑健性
rob = []
for lab, col, y0, y1 in [("本線：行政財産の建物 2011→2024", "bld_admin_total", 2011, 2024), ("2011→2017", "bld_admin_total", 2011, 2017),
                         ("2017→2024", "bld_admin_total", 2017, 2024), ("公営住宅を除く 2011→2024", "bld_ex_housing", 2011, 2024),
                         ("普通財産の建物も含む 2011→2024", "bld_with_general", 2011, 2024)]:
    pc0 = nat[col][y0] / nat.pop_thousand[y0]; pc1 = nat[col][y1] / nat.pop_thousand[y1]
    rob.append({"check": lab, "area_change_pct": pct(nat[col][y0], nat[col][y1]), "pop_change_pct": pct(nat.pop_thousand[y0], nat.pop_thousand[y1]),
                "per_capita_change_pct": pct(pc0, pc1)})
for lab, k in [("県別の相関：公営住宅を除く", "bld_ex_housing_pc_change_pct"), ("県別の相関：普通財産も含む", "bld_with_general_pc_change_pct")]:
    rob.append({"check": lab, "area_change_pct": None, "pop_change_pct": None, "per_capita_change_pct": None,
                "pearson": r(np.corrcoef(pref.pop_change_pct, pref[k])[0, 1], 3), "spearman": r(stats.spearmanr(pref.pop_change_pct, pref[k]).statistic, 3)})
rob.append({"check": "県別の相関：本線", "pearson": r(rho, 3), "spearman": r(sp, 3)})
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)

peak_year = int(nat.bld_admin_total.loc[Y0:].idxmax())
main = {
    "years_area": [Y0, Y1], "years_counts": [2006, Y1],
    "area_million_m2": {str(y): r(nat.bld_admin_total[y] / 1e6, 2) for y in [Y0, peak_year, Y1]}, "area_peak_year": peak_year,
    "pop_million": {str(y): r(nat.pop_thousand[y] / 1e3, 2) for y in [2006, Y0, Y1]},
    "m2_per_person": {str(y): r(nat.m2_per_person[y], 3) for y in [Y0, Y1]},
    "use_change_pct": {k: pct(nat[k][Y0], nat[k][Y1]) for k in ["bld_school", "bld_nonschool", "bld_housing", "bld_honchosha", "bld_public_other"]},
    "use_2024_million_m2": {k: r(nat[k][Y1] / 1e6, 2) for k in ["bld_school", "bld_housing", "bld_public_other", "bld_honchosha"]},
    "counts": {k: {"2006": int(nat[k][2006]), str(Y1): int(nat[k][Y1]), "change_pct": pct(nat[k][2006], nat[k][Y1])} for k in ["kominkan_n", "toshokan_n", "taiikukan_n", "shisho_n", "jidokan_n", "kokaido_n"]},
    "n_municipalities": {"2006": int(nat.n_municipalities[2006]), "2011": int(nat.n_municipalities[2011]), str(Y1): int(nat.n_municipalities[Y1])},
    "pref_pop_change_range": [r(pref.pop_change_pct.min()), r(pref.pop_change_pct.max())],
    "pref_pc_change_range": [r(pref.bld_admin_total_pc_change_pct.min()), r(pref.bld_admin_total_pc_change_pct.max())],
    "pref_n_pc_up": int((pref.bld_admin_total_pc_change_pct > 0).sum()),
    "pref_n_area_down": int((pref.area_change_pct < 0).sum()),
    "hypotheses": hyp,
    "note": "市町村（特別区を含む）が持つ行政財産の建物の延面積（年度末）。人口は人口推計の10月1日。延面積は2011年度から。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=0)[:2500]); print(pd.read_csv(R / "robustness.csv").to_string())
