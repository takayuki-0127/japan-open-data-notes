"""メタンの分野別の割合、面積あたり・頭数あたり、仮説、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
ch4 = pd.read_csv(ROOT / "data" / "ch4_long.csv")
act = pd.read_csv(ROOT / "data" / "activity.csv").set_index("year")


def wide(ver):
    return ch4[ch4.version == ver].pivot(index="fy", columns="sector", values="mt").sort_index()


def build(ver, lag=1, old2019=False):
    w = wide(ver).copy()
    w["rice_area_mha"] = act.rice_area_ha.reindex(w.index).values / 1e6  # 作付面積はその年の産
    heads = act.cattle_head.copy()
    if old2019:  # 2019年の（旧）でつなぐ
        heads.loc[2019] = act.dairy_head_old2019.loc[2019] + act.beef_head_old2019.loc[2019]
    w["cattle_mhead"] = heads.reindex(w.index + lag).values / 1e6  # 年度 t ↔ 調査年 t+lag（2月1日現在）
    w["rice_per_ha"] = w.rice / w.rice_area_mha          # t CO2 換算 / ha
    w["enteric_per_head"] = w.enteric / w.cattle_mhead   # t CO2 換算 / 頭
    w["rice_enteric"] = w.rice + w.enteric
    w["share_rice_enteric_pct"] = w.rice_enteric / w.total * 100
    w["share_rice_pct"] = w.rice / w.total * 100
    w["share_enteric_pct"] = w.enteric / w.total * 100
    w["share_landfill_pct"] = w.landfill / w.total * 100
    return w


W = build(2026)
W.round(5).to_csv(R / "ch4_series.csv")


def pct(a, b):
    return float((b / a - 1) * 100)


# H1：面積あたり 1990→2023（2024年度は問い直しで別に見る）
h1 = pct(W.rice_per_ha.loc[1990], W.rice_per_ha.loc[2023])
# H2：頭数あたり 1990→2024
h2 = pct(W.enteric_per_head.loc[1990], W.enteric_per_head.loc[2024])
# H3：前年度比の相関（1991〜2023）
dl = np.log(W[["rice", "rice_area_mha"]]).diff().loc[1991:2023]
h3 = float(dl.corr().iloc[0, 1])
# H4：2013→2024 の減少率
h4_total = pct(W.total.loc[2013], W.total.loc[2024]); h4_re = pct(W.rice_enteric.loc[2013], W.rice_enteric.loc[2024])

# 1990→2024 の合計の減少を分野に分ける
secs = {"rice": "稲作", "enteric": "家畜の消化管内発酵", "manure": "家畜排せつ物の管理", "landfill": "埋立",
        "wastewater": "排水処理", "fugitive": "燃料からの漏出（炭鉱など）", "fuel_combustion": "燃料の燃焼"}
dtot = float(W.total.loc[2024] - W.total.loc[1990])
dec = []
acc = 0.0
for k, n in secs.items():
    v = float(W[k].loc[2024] - W[k].loc[1990]); acc += v
    dec.append({"sector": n, "mt_1990": round(float(W[k].loc[1990]), 3), "mt_2024": round(float(W[k].loc[2024]), 3),
                "change_mt": round(v, 3), "share_of_decline_pct": round(v / dtot * 100, 1)})
dec.append({"sector": "その他", "mt_1990": None, "mt_2024": None, "change_mt": round(dtot - acc, 3), "share_of_decline_pct": round((dtot - acc) / dtot * 100, 1)})
pd.DataFrame(dec).to_csv(R / "decline_by_sector.csv", index=False)

# ---- 頑健性 -------------------------------------------------------------------------------
rob = []
for name, w, a, b in [("本線：2026年版、頭数は翌年2月", W, 1990, 2023),
                      ("2025年版", build(2025), 1990, 2023),
                      ("頭数は同じ年の2月（年度 t ↔ 調査年 t）", build(2026, lag=0), 1990, 2023),
                      ("2019年は（旧）でつなぐ", build(2026, old2019=True), 1990, 2023),
                      ("期間：1990→2018年度（集計方法の変更の前）", W, 1990, 2018),
                      ("期間：2005→2023年度", W, 2005, 2023)]:
    d = np.log(w[["rice", "rice_area_mha"]]).diff().loc[a + 1:b]
    rob.append({"check": name, "period": f"{a}-{b}",
                "rice_per_ha_change_pct": round(pct(w.rice_per_ha.loc[a], w.rice_per_ha.loc[b]), 1),
                "enteric_per_head_change_pct": round(pct(w.enteric_per_head.loc[a], w.enteric_per_head.loc[b]), 1),
                "corr_rice_area_yoy": round(float(d.corr().iloc[0, 1]), 2),
                "share_rice_enteric_end_pct": round(float(w.share_rice_enteric_pct.loc[b]), 1)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

main = {
    "total_1990": round(float(W.total.loc[1990]), 2), "total_2013": round(float(W.total.loc[2013]), 2), "total_2024": round(float(W.total.loc[2024]), 2),
    "rice_1990": round(float(W.rice.loc[1990]), 2), "rice_2023": round(float(W.rice.loc[2023]), 2), "rice_2024": round(float(W.rice.loc[2024]), 2),
    "enteric_1990": round(float(W.enteric.loc[1990]), 2), "enteric_2024": round(float(W.enteric.loc[2024]), 2),
    "landfill_1990": round(float(W.landfill.loc[1990]), 2), "landfill_2024": round(float(W.landfill.loc[2024]), 2),
    "share_rice_enteric_1990": round(float(W.share_rice_enteric_pct.loc[1990]), 1), "share_rice_enteric_2024": round(float(W.share_rice_enteric_pct.loc[2024]), 1),
    "share_rice_2024": round(float(W.share_rice_pct.loc[2024]), 1), "share_enteric_2024": round(float(W.share_enteric_pct.loc[2024]), 1),
    "share_agri_2024": round(float(W.agriculture.loc[2024] / W.total.loc[2024] * 100), 1),
    "share_landfill_1990": round(float(W.share_landfill_pct.loc[1990]), 1), "share_landfill_2024": round(float(W.share_landfill_pct.loc[2024]), 1),
    "ch4_share_of_ghg_note": "温室効果ガス全体に占めるメタンの割合は 1.Summary シート（F480 と同じ版）で約2.7%（2024年度）",
    "rice_area_mha_1990": round(float(W.rice_area_mha.loc[1990]), 3), "rice_area_mha_2023": round(float(W.rice_area_mha.loc[2023]), 3),
    "rice_area_mha_2024": round(float(W.rice_area_mha.loc[2024]), 3),
    "rice_per_ha_1990": round(float(W.rice_per_ha.loc[1990]), 3), "rice_per_ha_2023": round(float(W.rice_per_ha.loc[2023]), 3),
    "cattle_mhead_1990": round(float(W.cattle_mhead.loc[1990]), 3), "cattle_mhead_2024": round(float(W.cattle_mhead.loc[2024]), 3),
    "enteric_per_head_1990": round(float(W.enteric_per_head.loc[1990]), 3), "enteric_per_head_2024": round(float(W.enteric_per_head.loc[2024]), 3),
    "decline_1990_2024_mt": round(dtot, 2),
    "decline_share_pct": {r["sector"]: r["share_of_decline_pct"] for r in dec},
    "total_change_2013_2024_pct": round(h4_total, 1), "rice_enteric_change_2013_2024_pct": round(h4_re, 1),
    "hypotheses": {
        "H1_rice_per_ha_within_10pct": {"value": round(h1, 1), "result": "支持" if abs(h1) <= 10 else "外れ"},
        "H2_enteric_per_head_up_5pct": {"value": round(h2, 1), "result": "支持" if h2 >= 5 else "外れ"},
        "H3_corr_ge_0_5": {"value": round(h3, 2), "result": "支持" if h3 >= 0.5 else "外れ"},
        "H4_rice_enteric_fell_less": {"total_pct": round(h4_total, 1), "rice_enteric_pct": round(h4_re, 1),
                                      "result": "支持" if h4_re > h4_total else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rob.to_string()); print(pd.DataFrame(dec).to_string())
