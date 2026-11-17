"""洗濯代の長期の山、2015→2025年の変化（名目・実質）、季節の割合、仮説、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
mon = pd.read_csv(ROOT / "data" / "laundry_monthly.csv")
old = pd.read_csv(ROOT / "data" / "laundry_1963_2007.csv").set_index("year")
age = pd.read_csv(ROOT / "data" / "laundry_age.csv")
cpi = pd.read_csv(ROOT / "data" / "cpi.csv").set_index("year")
cpi["cpi_clean"] = (cpi.cpi_clean_a + cpi.cpi_clean_b) / 2

L = mon[mon.item == "洗濯代"].pivot(index="year", columns="month", values="yen")
C = mon[mon.item == "消費支出"].pivot(index="year", columns="month", values="yen")
y = pd.DataFrame({"laundry_yen": L.sum(axis=1), "consumption_yen": C.sum(axis=1)})
A = age.pivot_table(index="year", columns=["item", "age"], values="yen")
y["laundry_yen_annual_table"] = A[("洗濯代", "平均")]
y["share_of_consumption_pct"] = y.laundry_yen / y.consumption_yen * 100
y["cpi_clean"] = cpi.cpi_clean.reindex(y.index)
y["real_yen_2025prices"] = y.laundry_yen / y.cpi_clean * 100
y.round(3).to_csv(R / "annual_2015_2025.csv")

# 季節の割合
S = L.div(L.sum(axis=1), axis=0) * 100
S.round(3).to_csv(R / "monthly_share.csv")
PEAK = [4, 5, 6, 10, 11]
peak_share = S[PEAK].sum(axis=1)
ps_1519 = float(peak_share.loc[2015:2019].mean()); ps_2125 = float(peak_share.loc[2021:2025].mean())

# 長期（1963〜2007年）
old["cpi_clean"] = cpi.cpi_clean.reindex(old.index)
old["real_yen_2025prices"] = old.yen / old.cpi_clean * 100
old.round(3).to_csv(R / "annual_1963_2007.csv")
peak_year = int(old.yen.idxmax())
real_peak_year = int(old.real_yen_2025prices.idxmax())


def pct(a, b):
    return float((b / a - 1) * 100)


nom = pct(y.laundry_yen.loc[2015], y.laundry_yen.loc[2025])
real = pct(y.real_yen_2025prices.loc[2015], y.real_yen_2025prices.loc[2025])

# ---- 頑健性 -------------------------------------------------------------------------------
rob = []
def add(name, n, r, ps_a=None, ps_b=None):
    rob.append({"check": name, "nominal_change_pct": round(n, 1), "real_change_pct": round(r, 1) if r is not None else None,
                "peak5_share_before": round(ps_a, 1) if ps_a is not None else None, "peak5_share_after": round(ps_b, 1) if ps_b is not None else None})
add("本線：月別の和、2015→2025年、物価はＡ・Ｂの平均", nom, real, ps_1519, ps_2125)
add("年報（第4-6表の平均）で見る", pct(y.laundry_yen_annual_table.loc[2015], y.laundry_yen_annual_table.loc[2025]),
    pct(y.laundry_yen_annual_table.loc[2015] / y.cpi_clean.loc[2015], y.laundry_yen_annual_table.loc[2025] / y.cpi_clean.loc[2025]))
add("3年平均：2015〜17年→2023〜25年", pct(y.laundry_yen.loc[2015:2017].mean(), y.laundry_yen.loc[2023:2025].mean()),
    pct(y.real_yen_2025prices.loc[2015:2017].mean(), y.real_yen_2025prices.loc[2023:2025].mean()))
for k, lab in [("cpi_clean_a", "Ａだけ"), ("cpi_clean_b", "Ｂだけ")]:
    add(f"物価はクリーニング代{lab}", nom, pct(y.laundry_yen.loc[2015] / cpi[k].loc[2015], y.laundry_yen.loc[2025] / cpi[k].loc[2025]))
add("季節：後の期間に2020年を含める（2020〜2025年）", nom, real, ps_1519, float(peak_share.loc[2020:2025].mean()))
add("季節：前を2016〜2019年、後を2022〜2025年", nom, real, float(peak_share.loc[2016:2019].mean()), float(peak_share.loc[2022:2025].mean()))
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

main = {
    "laundry_2015": float(y.laundry_yen.loc[2015]), "laundry_2019": float(y.laundry_yen.loc[2019]), "laundry_2020": float(y.laundry_yen.loc[2020]),
    "laundry_2025": float(y.laundry_yen.loc[2025]),
    "nominal_change_2015_2025_pct": round(nom, 1), "real_change_2015_2025_pct": round(real, 1),
    "cpi_clean_2015": round(float(y.cpi_clean.loc[2015]), 2), "cpi_clean_2025": round(float(y.cpi_clean.loc[2025]), 2),
    "cpi_clean_change_pct": round(pct(y.cpi_clean.loc[2015], y.cpi_clean.loc[2025]), 1),
    "share_2015_pct": round(float(y.share_of_consumption_pct.loc[2015]), 3), "share_2025_pct": round(float(y.share_of_consumption_pct.loc[2025]), 3),
    "old_peak_year": peak_year, "old_peak_yen": float(old.yen.loc[peak_year]), "old_1963_yen": float(old.yen.loc[1963]), "old_2007_yen": float(old.yen.loc[2007]),
    "old_real_peak_year": real_peak_year,
    "ratio_2025_to_peak_nominal": round(float(y.laundry_yen.loc[2025] / old.yen.loc[peak_year]), 3),
    "real_1970": round(float(old.real_yen_2025prices.loc[1970]), 0), "real_peak_nominal_year": round(float(old.real_yen_2025prices.loc[peak_year]), 0),
    "real_2007": round(float(old.real_yen_2025prices.loc[2007]), 0), "real_2025": round(float(y.real_yen_2025prices.loc[2025]), 0),
    "ratio_2025_to_peak_real": round(float(y.real_yen_2025prices.loc[2025] / old.real_yen_2025prices.loc[peak_year]), 3),
    "peak5_share_2015_2019": round(ps_1519, 1), "peak5_share_2021_2025": round(ps_2125, 1),
    "top_month_2015_2019": int(S.loc[2015:2019].mean().idxmax()), "top_month_2021_2025": int(S.loc[2021:2025].mean().idxmax()),
    "may_share_2015_2019": round(float(S.loc[2015:2019, 5].mean()), 1), "may_share_2021_2025": round(float(S.loc[2021:2025, 5].mean()), 1),
    "hypotheses": {
        "H1_peak_in_1990s": {"value": peak_year, "result": "支持" if 1990 <= peak_year <= 1999 else "外れ"},
        "H2_nominal_down_20": {"value": round(nom, 1), "result": "支持" if nom <= -20 else "外れ"},
        "H3_real_fell_more": {"nominal": round(nom, 1), "real": round(real, 1), "result": "支持" if real < nom else "外れ"},
        "H4_peak5_ge_50_and_not_down_3": {"before": round(ps_1519, 1), "after": round(ps_2125, 1),
                                          "result": "支持" if (ps_1519 >= 50 and ps_1519 - ps_2125 < 3) else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rob.to_string()); print(y.round(1).to_string())
