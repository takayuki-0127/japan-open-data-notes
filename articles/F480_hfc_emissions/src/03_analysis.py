"""HFC の推移、ピーク、用途別の分解、CO2 との比較、仮説の判定、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "fgas_long.csv")


def wide(ver):
    d = df[df.version == ver]
    w = d.pivot_table(index="fy", columns=["gas", "use"], values="mt").sort_index()
    w.columns = [f"{g}_{u}" for g, u in w.columns]
    w["HFC_ex_byproduct"] = w.HFC_total - w.HFC_byproduct_hfc23
    return w


W = wide(2026); W25 = wide(2025)
W.round(4).to_csv(R / "series_2026.csv")


def peak_info(s, ma=False):
    x = s.rolling(3, center=True).mean().dropna() if ma else s
    py = int(x.idxmax())
    before = x.loc[:py]
    my = int(before.idxmin())  # ピーク前の最小
    last = int(s.index.max())
    return {"peak_year": py, "peak": float(x.loc[py]), "min_year": my, "min": float(x.loc[my]),
            "last_year": last, "last": float(s.loc[last]),
            "ratio_last_to_min": float(s.loc[last] / x.loc[my]), "last_vs_peak_pct": float((s.loc[last] / x.loc[py] - 1) * 100)}


hfc = peak_info(W.HFC_total)
# 用途別の分解（期間ごとの増減、Mt）
USES = ["refrig_commercial", "refrig_household_ac", "refrig_car_ac", "refrig_other", "foam", "aerosol", "byproduct_hfc23"]
NAMES = {"refrig_commercial": "業務用冷凍空調機器", "refrig_household_ac": "家庭用エアコン", "refrig_car_ac": "カーエアコン",
         "refrig_other": "冷凍空調のその他", "foam": "発泡剤", "aerosol": "エアゾール・MDI", "byproduct_hfc23": "HCFC22製造時の副生HFC23", "rest": "その他の用途"}
periods = [(1990, hfc["min_year"]), (hfc["min_year"], hfc["peak_year"]), (hfc["peak_year"], 2024)]
dec = []
for a, b in periods:
    row = {"period": f"{a}-{b}", "total_change": round(float(W.HFC_total.loc[b] - W.HFC_total.loc[a]), 3)}
    acc = 0.0
    for u in USES:
        v = float(W[f"HFC_{u}"].loc[b] - W[f"HFC_{u}"].loc[a]); acc += v
        row[u] = round(v, 3)
    row["rest"] = round(row["total_change"] - acc, 3)
    dec.append(row)
dec = pd.DataFrame(dec)
dec.to_csv(R / "hfc_decomposition.csv", index=False)

# 2024年度の内訳
y = 2024
share_refrig = float(W.HFC_refrig_total.loc[y] / W.HFC_total.loc[y] * 100)
mix = {NAMES[u]: round(float(W[f"HFC_{u}"].loc[y]), 3) for u in USES}
# CO2 との比較（2013 → 2024）
co2_chg = float((W.CO2_total.loc[2024] / W.CO2_total.loc[2013] - 1) * 100)
hfc_chg_13 = float((W.HFC_total.loc[2024] / W.HFC_total.loc[2013] - 1) * 100)
hfc_share = {int(k): round(float(v), 3) for k, v in (W.HFC_total / W.GHG_total * 100).loc[[1990, 2005, 2013, 2021, 2024]].items()}

# ---- 頑健性 -------------------------------------------------------------------------------
rob = []
for name, s in [("本線：2026年版 HFC 計", W.HFC_total), ("2025年版 HFC 計（〜2023年度）", W25.HFC_total),
                ("副生HFC23を除く HFC", W.HFC_ex_byproduct), ("代替フロン等4ガス 計", W.FGAS_total)]:
    p = peak_info(s)
    rob.append({"check": name, "peak_year": p["peak_year"], "peak_mt": round(p["peak"], 2), "min_year": p["min_year"], "min_mt": round(p["min"], 2),
                "last_year": p["last_year"], "last_mt": round(p["last"], 2), "last_vs_peak_pct": round(p["last_vs_peak_pct"], 1),
                "ratio_last_to_min": round(p["ratio_last_to_min"], 2), "ratio_last_to_2005": round(float(s.iloc[-1] / s.loc[2005]), 2)})
p = peak_info(W.HFC_total, ma=True)
rob.append({"check": "3年移動平均でピークを決める（2026年版）", "peak_year": p["peak_year"], "peak_mt": round(p["peak"], 2), "min_year": p["min_year"],
            "min_mt": round(p["min"], 2), "last_year": p["last_year"], "last_mt": round(p["last"], 2),
            "last_vs_peak_pct": round(p["last_vs_peak_pct"], 1), "ratio_last_to_min": round(p["ratio_last_to_min"], 2),
            "ratio_last_to_2005": round(float(W.HFC_total.iloc[-1] / W.HFC_total.loc[2005]), 2)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

# 版による書き換え（2025年版→2026年版、共通の年）
common = W25.index.intersection(W.index)
rev = pd.DataFrame({"hfc_2025ver": W25.HFC_total.loc[common], "hfc_2026ver": W.HFC_total.loc[common],
                    "household_ac_2025ver": W25.HFC_refrig_household_ac.loc[common], "household_ac_2026ver": W.HFC_refrig_household_ac.loc[common]})
rev["hfc_diff"] = rev.hfc_2026ver - rev.hfc_2025ver
rev.round(4).to_csv(R / "vintage_revision.csv")
max_rev_year = int(rev.hfc_diff.abs().idxmax())

h = {
    "H1_ratio_ge_2": {"value": round(hfc["ratio_last_to_min"], 2), "min_year": hfc["min_year"], "result": "支持" if hfc["ratio_last_to_min"] >= 2 else "外れ"},
    "H2_peak_le_2022_and_5pct_below": {"peak_year": hfc["peak_year"], "value": round(hfc["last_vs_peak_pct"], 1),
                                       "result": "支持" if (hfc["peak_year"] <= 2022 and hfc["last_vs_peak_pct"] <= -5) else "外れ"},
    "H3_refrig_share_ge_80": {"value": round(share_refrig, 1), "result": "支持" if share_refrig >= 80 else "外れ"},
    "H4_co2_down_20_and_hfc_up": {"co2_pct": round(co2_chg, 1), "hfc_pct": round(hfc_chg_13, 1),
                                  "result": "支持" if (co2_chg <= -20 and hfc_chg_13 > 0) else "外れ"},
}
main = {
    "hfc_1990": round(float(W.HFC_total.loc[1990]), 2), "hfc_min_year": hfc["min_year"], "hfc_min": round(hfc["min"], 2),
    "hfc_peak_year": hfc["peak_year"], "hfc_peak": round(hfc["peak"], 2), "hfc_2013": round(float(W.HFC_total.loc[2013]), 2),
    "hfc_2024": round(float(W.HFC_total.loc[2024]), 2), "hfc_ratio_2024_to_min": round(hfc["ratio_last_to_min"], 2),
    "hfc_2024_vs_peak_pct": round(hfc["last_vs_peak_pct"], 1),
    "byproduct_1990": round(float(W.HFC_byproduct_hfc23.loc[1990]), 2), "byproduct_2005": round(float(W.HFC_byproduct_hfc23.loc[2005]), 2),
    "refrig_2005": round(float(W.HFC_refrig_total.loc[2005]), 2), "refrig_2021": round(float(W.HFC_refrig_total.loc[2021]), 2),
    "refrig_2024": round(float(W.HFC_refrig_total.loc[2024]), 2), "refrig_share_2024_pct": round(share_refrig, 1),
    "mix_2024_mt": mix,
    "co2_2013": round(float(W.CO2_total.loc[2013]), 2), "co2_2024": round(float(W.CO2_total.loc[2024]), 2),
    "co2_change_2013_2024_pct": round(co2_chg, 1), "hfc_change_2013_2024_pct": round(hfc_chg_13, 1),
    "hfc_share_of_ghg_pct": hfc_share,
    "fgas_2024": round(float(W.FGAS_total.loc[2024]), 2),
    "vintage_2023_hfc_2025ver": round(float(W25.HFC_total.loc[2023]), 2), "vintage_2023_hfc_2026ver": round(float(W.HFC_total.loc[2023]), 2),
    "vintage_max_rev_year": max_rev_year, "vintage_max_rev_mt": round(float(rev.hfc_diff.loc[max_rev_year]), 2),
    "hypotheses": h,
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(dec.to_string()); print(rob.to_string()); print(rev.round(2).loc[2005:].to_string())
