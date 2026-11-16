"""主の分析：水稲作付田の減少の分解、田のかい廃の要因、田の作物、稲の中身、地域差。
結果は results/main.json と results/*.csv に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"
R = ROOT / "results"
R.mkdir(exist_ok=True)

s = pd.read_csv(D / "summer_paddy_use_national.csv").set_index("year")
reg = pd.read_csv(D / "summer_paddy_use_region.csv")
crops = pd.read_csv(D / "paddy_crops.csv").set_index("year")
ab = pd.read_csv(D / "paddy_expansion_abandon.csv").set_index("year")
land = pd.read_csv(D / "land_area_paddy.csv").set_index("year")
rice = pd.read_csv(D / "rice_area.csv").set_index("year")

main = {}


def r1(x, k=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


# ---- A. 分解 ---------------------------------------------------------------
def decompose(y0, y1, rice_col="rice_field", src=s):
    a, b = src.loc[y0], src.loc[y1]
    d_rice = b[rice_col] - a[rice_col]
    d_paddy = b["paddy"] - a["paddy"]
    d_non = b["nonrice_only"] - a["nonrice_only"]
    d_un = b["unplanted"] - a["unplanted"]
    d_res = d_paddy - d_non - d_un - d_rice   # 表の四捨五入などによる残り
    dec = -d_rice
    return {
        "y0": int(y0), "y1": int(y1), "rice_y0": float(a[rice_col]), "rice_y1": float(b[rice_col]),
        "rice_decline_ha": float(dec), "rice_decline_pct": r1(100 * dec / a[rice_col]),
        "paddy_loss_ha": float(-d_paddy), "nonrice_increase_ha": float(d_non), "unplanted_increase_ha": float(d_un),
        "residual_ha": float(d_res),
        "share_paddy_loss_pct": r1(100 * -d_paddy / dec), "share_nonrice_pct": r1(100 * d_non / dec),
        "share_unplanted_pct": r1(100 * d_un / dec), "share_residual_pct": r1(100 * d_res / dec),
    }


peak_year = int(s["rice_field"].idxmax())
main["peak_rice_field_year"] = peak_year
dec_rows = []
for lab, (y0, y1) in {"main_1969_2025": (1969, 2025), "start1975": (1975, 2025), "start2003": (2003, 2025),
                      "end2024": (1969, 2024)}.items():
    x = decompose(y0, y1)
    x["case"] = lab
    dec_rows.append(x)
# 稲の指標を「水稲（子実用）作付面積」に替える（田本地の減少は夏期の表のまま）
t = s.join(rice[["rice_grain_area"]])
x = decompose(1969, 2025, rice_col="rice_grain_area", src=t)
# 子実用は青刈りを除くので、残り（residual）に飼料用米・WCS などの差が入る
x["case"] = "rice_grain_area"
dec_rows.append(x)
dec = pd.DataFrame(dec_rows)
dec.to_csv(R / "decomposition.csv", index=False)
main["decomposition"] = {r["case"]: {k: v for k, v in r.items() if k != "case"} for r in dec_rows}

# 田本地を別の表（本地・けい畔別耕地面積）と照合
j = s[["paddy"]].join(land[["paddy_honchi"]], how="inner")
main["check_paddy_honchi_max_abs_diff_ha"] = float((j["paddy"] - j["paddy_honchi"]).abs().max())
main["check_paddy_honchi_years"] = [int(j.index.min()), int(j.index.max())]
x2 = decompose(1969, 2025, src=s.assign(paddy=land["paddy_honchi"].reindex(s.index)))
main["decomposition_alt_paddy_table"] = {k: v for k, v in x2.items()}

# 推移の割合（図1用）
sh = s[["paddy", "rice_field", "nonrice_only", "unplanted"]].copy()
for c in ["rice_field", "nonrice_only", "unplanted"]:
    sh[c + "_pct"] = 100 * sh[c] / sh["paddy"]
sh.to_csv(R / "summer_use_share.csv")
main["share_2025"] = {c: r1(sh.loc[2025, c + "_pct"]) for c in ["rice_field", "nonrice_only", "unplanted"]}
main["share_1969"] = {c: r1(sh.loc[1969, c + "_pct"]) for c in ["rice_field", "nonrice_only", "unplanted"]}
main["paddy_1969_ha"] = float(s.loc[1969, "paddy"])
main["paddy_2025_ha"] = float(s.loc[2025, "paddy"])
main["paddy_change_pct_1969_2025"] = r1(100 * (s.loc[2025, "paddy"] / s.loc[1969, "paddy"] - 1))
main["unplanted_max_year"] = int(s["unplanted"].idxmax())
main["unplanted_max_ha"] = float(s["unplanted"].max())
main["nonrice_max_year"] = int(s["nonrice_only"].idxmax())
main["nonrice_max_ha"] = float(s["nonrice_only"].max())
u = sh.loc[1998:2025, "unplanted_pct"]
main["unplanted_pct_range_1998_2025"] = [r1(u.min()), r1(u.max())]

# ---- B. 田のかい廃の要因 ----------------------------------------------------
w = ab.loc[1970:2016]
cum = {k: float(w[k].sum()) for k in ["ab_total", "ab_disaster", "ab_human", "ab_to_upland", "ab_factory", "ab_road",
                                     "ab_housing", "ab_farmroad", "ab_forest", "ab_other"]}
cum["exp_total"] = float(w["exp_total"].sum())
cum["exp_from_upland"] = float(w["exp_from_upland"].sum())
cum["check_sum_reasons"] = cum["ab_disaster"] + cum["ab_human"] + cum["ab_to_upland"]
h = cum["ab_human"]
abandon = {
    "period": [1970, 2016],
    "cum": cum,
    "share_to_upland_pct": r1(100 * cum["ab_to_upland"] / cum["ab_total"]),
    "share_human_pct": r1(100 * cum["ab_human"] / cum["ab_total"]),
    "share_disaster_pct": r1(100 * cum["ab_disaster"] / cum["ab_total"]),
    "human_breakdown_pct": {k: r1(100 * cum[k] / h) for k in ["ab_factory", "ab_road", "ab_housing", "ab_farmroad", "ab_forest", "ab_other"]},
}
w2 = ab.loc[1997:2016]
abandon["abandoned_1997_2016_ha"] = float(w2["ab_abandoned"].sum())
abandon["abandoned_share_of_total_1997_2016_pct"] = r1(100 * w2["ab_abandoned"].sum() / w2["ab_total"].sum())
abandon["to_upland_share_1997_2016_pct"] = r1(100 * w2["ab_to_upland"].sum() / w2["ab_total"].sum())
w3 = ab.loc[2017:2025]
abandon["total_2017_2025_ha"] = float(w3["ab_total"].sum())
abandon["abandoned_2017_2025_ha"] = float(w3["ab_abandoned"].sum())
abandon["abandoned_share_2017_2025_pct"] = r1(100 * w3["ab_abandoned"].sum() / w3["ab_total"].sum())
w4 = ab.loc[1970:2025]
abandon["total_1970_2025_ha"] = float(w4["ab_total"].sum())
abandon["exp_1970_2025_ha"] = float(w4["exp_total"].sum())
abandon["net_1970_2025_ha"] = float(w4["exp_total"].sum() - w4["ab_total"].sum())
abandon["land_table_change_paddy_total_1969_2025_ha"] = float(land.loc[2025, "paddy_total"] - land.loc[1969, "paddy_total"])
# 期間ごとの年平均（図2用）
per = []
for a0, a1 in [(1970, 1979), (1980, 1989), (1990, 1999), (2000, 2009), (2010, 2016), (2017, 2025)]:
    q = ab.loc[a0:a1]
    row = {"period": f"{a0}–{a1}", "years": len(q), "ab_total": q["ab_total"].mean(), "ab_to_upland": q["ab_to_upland"].mean(),
           "ab_disaster": q["ab_disaster"].mean(), "ab_abandoned": q["ab_abandoned"].mean(),
           "exp_total": q["exp_total"].mean()}
    if a0 >= 2017:
        row["ab_other_human"] = np.nan
    else:
        row["ab_other_human"] = (q["ab_human"] - q["ab_abandoned"].fillna(0)).mean()
    per.append(row)
per = pd.DataFrame(per)
per.to_csv(R / "abandon_by_period.csv", index=False)
abandon["by_period"] = per.round(0).to_dict(orient="records")
main["abandon"] = abandon

# ---- C. 田の作物（延べ面積） -------------------------------------------------
cl = ["rice", "wheat_barley", "pulses", "vegetables", "feed_green", "industrial", "minor_grains", "sweet_potato", "other"]
cc = pd.DataFrame({"y1969": crops.loc[1969, cl].astype(float), "y2016": crops.loc[2016, cl].astype(float)})
cc["change"] = cc["y2016"] - cc["y1969"].fillna(0)
cc.to_csv(R / "paddy_crops_change_1969_2016.csv")
non_rice_change = cc.drop(index="rice")["change"]
main["crops_1969_2016"] = {k: {"y1969": r1(v["y1969"], 0), "y2016": r1(v["y2016"], 0), "change": r1(v["change"], 0)} for k, v in cc.iterrows()}
main["crops_1969_2016_largest_nonrice_increase"] = str(non_rice_change.idxmax())
main["crops_total_1969_2016"] = [float(crops.loc[1969, "total"]), float(crops.loc[2016, "total"])]
main["crops_honchi_util_pct"] = {"1969": float(crops.loc[1969, "honchi_utilization_pct"]), "2016": float(crops.loc[2016, "honchi_utilization_pct"]),
                                 "2024": float(crops.loc[2024, "honchi_utilization_pct"])}
c2 = {k: {"y2017": float(crops.loc[2017, k]), "y2024": float(crops.loc[2024, k])} for k in ["wheat_barley", "soybean", "buckwheat", "other_2017", "rice"]}
main["crops_2017_2024"] = c2
# 大豆の代わりに豆類（2016年まで）の推移
main["pulses_on_paddy"] = {str(y): float(crops.loc[y, "pulses"]) for y in [1969, 1980, 1990, 2000, 2010, 2016]}
main["feed_green_on_paddy"] = {str(y): float(crops.loc[y, "feed_green"]) for y in [1969, 1980, 1990, 2000, 2010, 2016]}
main["wheat_on_paddy"] = {str(y): float(crops.loc[y, "wheat_barley"]) for y in [1969, 1980, 1990, 2000, 2010, 2016]}
crops.to_csv(R / "paddy_crops_series.csv")

# ---- D. 稲の中身 ------------------------------------------------------------
comp = []
for y in range(2008, 2026):
    rf = float(s.loc[y, "rice_field"])
    g = float(rice.loc[y, "rice_grain_area"]); st = float(rice.loc[y, "rice_staple_area"])
    fr = float(rice.loc[y, "feed_rice"]); wc = float(rice.loc[y, "wcs"])
    comp.append({"year": y, "rice_field": rf, "grain": g, "staple": st, "feed_rice": fr, "wcs": wc,
                 "other_nonstaple": rf - st - fr - wc,
                 "nonstaple_share_of_grain_pct": 100 * (g - st) / g,
                 "nonstaple_share_of_field_pct": 100 * (rf - st) / rf})
comp = pd.DataFrame(comp)
comp.to_csv(R / "rice_composition.csv", index=False)
c24 = comp.set_index("year").loc[2024]
c25 = comp.set_index("year").loc[2025]
main["rice_composition_2024"] = {k: r1(v) for k, v in c24.items()}
main["rice_composition_2025"] = {k: r1(v) for k, v in c25.items()}
main["feed_rice_peak"] = {"year": int(rice["feed_rice"].idxmax()), "ha": float(rice["feed_rice"].max())}

# ---- E. 地域 ----------------------------------------------------------------
reg["rice_pct"] = 100 * reg["rice_field"] / reg["paddy"]
reg["nonrice_pct"] = 100 * reg["nonrice_only"] / reg["paddy"]
reg["unplanted_pct"] = 100 * reg["unplanted"] / reg["paddy"]
reg.to_csv(R / "region_shares.csv", index=False)
rg = reg[reg.level == "地域"].pivot(index="name", columns="year", values=["paddy", "rice_pct", "nonrice_pct", "unplanted_pct"])
order = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
rg = rg.reindex(order)
region = {}
for n in order:
    region[n] = {"paddy_2003": float(rg.loc[n, ("paddy", 2003)]), "paddy_2025": float(rg.loc[n, ("paddy", 2025)]),
                 "paddy_change_pct": r1(100 * (rg.loc[n, ("paddy", 2025)] / rg.loc[n, ("paddy", 2003)] - 1)),
                 "rice_pct_2003": r1(rg.loc[n, ("rice_pct", 2003)]), "rice_pct_2025": r1(rg.loc[n, ("rice_pct", 2025)]),
                 "nonrice_pct_2003": r1(rg.loc[n, ("nonrice_pct", 2003)]), "nonrice_pct_2025": r1(rg.loc[n, ("nonrice_pct", 2025)]),
                 "unplanted_pct_2003": r1(rg.loc[n, ("unplanted_pct", 2003)]), "unplanted_pct_2025": r1(rg.loc[n, ("unplanted_pct", 2025)])}
main["region"] = region
west = ["近畿", "中国", "四国"]; north = ["北海道", "東北", "北陸"]
reg25 = reg[(reg.level == "地域") & (reg.year == 2025)].set_index("name")
def pooled(names, col):
    q = reg25.loc[names]
    return 100 * q[col].sum() / q["paddy"].sum()
main["h4"] = {
    "unplanted_pct_west_2025": r1(pooled(west, "unplanted")), "unplanted_pct_north_2025": r1(pooled(north, "unplanted")),
    "unplanted_pct_chugoku_2025": r1(region["中国"]["unplanted_pct_2025"]), "unplanted_pct_shikoku_2025": r1(region["四国"]["unplanted_pct_2025"]),
    "unplanted_pct_tohoku_2025": r1(region["東北"]["unplanted_pct_2025"]),
    "nonrice_max_region_2025": str(reg25.drop(index="沖縄")["nonrice_only"].div(reg25.drop(index="沖縄")["paddy"]).idxmax()),
}
# 都道府県で照合：地域ごとの都道府県の中央値と、2003→2025年の田本地の減り方と不作付の割合の変化の関係
pf = reg[reg.level == "都道府県"].pivot(index="name", columns="year", values=["paddy", "unplanted_pct", "nonrice_pct"])
pf = pf.dropna()
pref_region = {}
groups = {"北海道": ["北海道"], "東北": ["青森", "岩手", "宮城", "秋田", "山形", "福島"],
          "北陸": ["新潟", "富山", "石川", "福井"], "関東・東山": ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "山梨", "長野"],
          "東海": ["岐阜", "静岡", "愛知", "三重"], "近畿": ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"],
          "中国": ["鳥取", "島根", "岡山", "広島", "山口"], "四国": ["徳島", "香川", "愛媛", "高知"],
          "九州": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島"], "沖縄": ["沖縄"]}
for g, ps in groups.items():
    q = pf.loc[ps]
    pref_region[g] = {"n": len(ps), "unplanted_pct_2025_median": r1(q[("unplanted_pct", 2025)].median()),
                      "unplanted_pct_2025_min": r1(q[("unplanted_pct", 2025)].min()), "unplanted_pct_2025_max": r1(q[("unplanted_pct", 2025)].max())}
main["pref_by_region"] = pref_region
wp = [p for g in west for p in groups[g]]; npf = [p for g in north for p in groups[g]]
main["pref_unplanted_median_west_vs_north_2025"] = [r1(pf.loc[wp, ("unplanted_pct", 2025)].median()), r1(pf.loc[npf, ("unplanted_pct", 2025)].median())]
mw = stats.mannwhitneyu(pf.loc[wp, ("unplanted_pct", 2025)], pf.loc[npf, ("unplanted_pct", 2025)], alternative="two-sided")
main["pref_unplanted_west_vs_north_mannwhitney_p"] = r1(mw.pvalue, 4)
paddy_chg = 100 * (pf[("paddy", 2025)] / pf[("paddy", 2003)] - 1)
pd.DataFrame({"paddy_2003": pf[("paddy", 2003)], "paddy_2025": pf[("paddy", 2025)], "paddy_change_pct": paddy_chg, "unplanted_pct_2003": pf[("unplanted_pct", 2003)],
              "unplanted_pct_2025": pf[("unplanted_pct", 2025)], "nonrice_pct_2003": pf[("nonrice_pct", 2003)], "nonrice_pct_2025": pf[("nonrice_pct", 2025)]}).reindex(
    [p for g in groups.values() for p in g]).to_csv(R / "pref_shares.csv")

# ---- 仮説の判定 ---------------------------------------------------------------
m = main["decomposition"]["main_1969_2025"]
main["hypotheses"] = {
    "H1": {"value": m["share_paddy_loss_pct"], "rule": ">=50 で支持", "verdict": "支持" if m["share_paddy_loss_pct"] >= 50 else "外れ"},
    "H2": {"value": abandon["share_to_upland_pct"], "rule": "<30 で支持（1970〜2016年。2017年から田畑転換は調べていない）",
           "verdict": "支持" if abandon["share_to_upland_pct"] < 30 else "外れ"},
    "H3": {"value": r1(c24["nonstaple_share_of_grain_pct"]), "rule": ">=10 で支持（子実用のうち主食用以外）",
           "verdict": "支持" if c24["nonstaple_share_of_grain_pct"] >= 10 else "外れ",
           "note_field_basis": r1(c24["nonstaple_share_of_field_pct"])},
    "H4": {"verdict": "支持" if (region["中国"]["unplanted_pct_2025"] > region["東北"]["unplanted_pct_2025"]
                                and region["四国"]["unplanted_pct_2025"] > region["東北"]["unplanted_pct_2025"]
                                and main["h4"]["nonrice_max_region_2025"] == "北海道") else "外れ"},
}

with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main["hypotheses"], ensure_ascii=False))
