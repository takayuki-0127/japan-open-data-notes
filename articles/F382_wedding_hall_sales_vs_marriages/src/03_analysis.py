"""主な分析：伸び率をつないだ指数、婚姻件数との比較、売上の分解、頑健性。結果は results/ へ（ネットにはつながない）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
w = pd.read_csv(DATA / "wedding_annual.csv")
mar = pd.read_csv(DATA / "marriage_annual.csv").set_index("year")
cpi = pd.read_csv(DATA / "cpi_annual.csv").set_index("year")
out = {}


def r(x, k=4):
    return None if x is None or not np.isfinite(x) else round(float(x), k)


# 1) 伸び率（断層を調整した前年比）をつないだ指数。旧様式は2000年＝100、新様式は2015年＝100
idx = []
for era, base in [("old", 2000), ("new", 2015)]:
    e = w[w.era == era].sort_values("year").reset_index(drop=True)
    s = c = emp = 100.0
    for i, row in e.iterrows():
        if row.year > base:
            s *= 1 + row.sales_growth / 100
            c *= 1 + row.count_growth / 100
            emp *= 1 + row.emp_growth / 100
        idx.append({"era": era, "year": int(row.year), "sales_idx": s, "count_idx": c, "emp_idx": emp,
                    "marr_idx": 100 * mar.loc[row.year, "marriages"] / mar.loc[base, "marriages"],
                    "first_idx": 100 * mar.loc[row.year, "both_first"] / mar.loc[base, "both_first"],
                    "cpi_idx": 100 * cpi.loc[row.year, "cpi_all"] / cpi.loc[base, "cpi_all"],
                    "cpicore_idx": 100 * cpi.loc[row.year, "cpi_core"] / cpi.loc[base, "cpi_core"],
                    "marriages": int(mar.loc[row.year, "marriages"]), "sales_level": row.sales_level, "count_level": row.count_level})
idx = pd.DataFrame(idx)
idx["unit_idx"] = 100 * idx.sales_idx / idx.count_idx
idx["unit_real_idx"] = 100 * idx.unit_idx / idx.cpi_idx
idx["share_idx"] = 100 * idx.count_idx / idx.marr_idx          # 結婚1組あたりの式場の件数（基準年＝100）
idx["share_first_idx"] = 100 * idx.count_idx / idx.first_idx
idx["unit_level_man_yen"] = 100 * idx.sales_level / idx.count_level   # 実数どうしの1件あたり売上（万円、断層を含む参考値）
idx.to_csv(RES / "index_annual.csv", index=False, float_format="%.4f")


def at(era, y, col):
    return float(idx[(idx.era == era) & (idx.year == y)][col].iloc[0])


def period(era, y0, y1, drop=()):
    """年あたりの対数の平均変化（×100）。drop の年の変化は平均から外す。"""
    e = idx[(idx.era == era) & (idx.year >= y0) & (idx.year <= y1)].sort_values("year").set_index("year")
    res = {}
    for col in ["sales_idx", "count_idx", "marr_idx", "first_idx", "unit_idx", "unit_real_idx", "share_idx", "cpi_idx", "cpicore_idx", "emp_idx"]:
        dl = 100 * np.log(e[col]).diff().dropna()
        dl = dl[~dl.index.isin(drop)]
        res[col.replace("_idx", "") + "_rate"] = float(dl.mean())
        res[col.replace("_idx", "") + "_cum_pct"] = float(100 * (e[col].iloc[-1] / e[col].iloc[0] - 1))
    res["years"] = f"{y0}→{y1}"
    return res


P = {"old": period("old", 2000, 2014), "new_pre": period("new", 2015, 2019), "new_all": period("new", 2015, 2024),
     "covid": period("new", 2019, 2024), "after": period("new", 2022, 2024)}
pt = pd.DataFrame(P).T
pt.index.name = "period"
pt.to_csv(RES / "periods.csv", float_format="%.4f")
out["periods"] = {k: {kk: (r(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in P.items()}

# 2) 売上の分解（対数の変化、×100）：売上 ＝ 婚姻件数 ＋ 結婚1組あたりの件数 ＋ 1件あたりの売上
dec = []
for name, era, y0, y1 in [("2000→2014年（旧様式）", "old", 2000, 2014), ("2015→2019年（新様式・コロナ前）", "new", 2015, 2019),
                          ("2019→2024年（新様式・コロナ後）", "new", 2019, 2024), ("2015→2024年（新様式）", "new", 2015, 2024)]:
    f = lambda col: 100 * np.log(at(era, y1, col) / at(era, y0, col))
    dec.append({"period": name, "sales": f("sales_idx"), "marriages": f("marr_idx"), "share": f("share_idx"),
                "unit_price": f("unit_idx"), "unit_real": f("unit_real_idx"), "cpi": f("cpi_idx")})
dec = pd.DataFrame(dec)
dec["check"] = dec.sales - (dec.marriages + dec.share + dec.unit_price)
dec.to_csv(RES / "decomposition.csv", index=False, float_format="%.4f")
out["decomposition"] = [{k: (r(v, 2) if isinstance(v, float) else v) for k, v in row.items()} for row in dec.to_dict("records")]

# 3) 仮説の判定
gap_old = P["old"]["count_rate"] - P["old"]["marr_rate"]
gap_new = P["new_pre"]["count_rate"] - P["new_pre"]["marr_rate"]
out["H1_detail"] = {"gap_old": r(gap_old, 3), "gap_new_pre": r(gap_new, 3)}
out["H1"] = "支持" if (gap_old <= -1 and gap_new <= -1) else ("判定できず" if (gap_old <= -1 or gap_new <= -1) else "外れ")
ur_old, ur_new = P["old"]["unit_real_cum_pct"], P["new_pre"]["unit_real_cum_pct"]
out["H2_detail"] = {"unit_real_cum_old": r(ur_old, 2), "unit_real_cum_new_pre": r(ur_new, 2), "unit_real_cum_new_all": r(P["new_all"]["unit_real_cum_pct"], 2),
                    "unit_nominal_cum_old": r(P["old"]["unit_cum_pct"], 2), "unit_nominal_cum_new_all": r(P["new_all"]["unit_cum_pct"], 2)}
out["H2"] = "支持" if (ur_old >= 5 and ur_new >= 5) else ("外れ" if (ur_old <= 0 and ur_new <= 0) else "判定できず")
c19, m19 = 100 * at("new", 2024, "count_idx") / at("new", 2019, "count_idx"), 100 * at("new", 2024, "marr_idx") / at("new", 2019, "marr_idx")
s19 = 100 * at("new", 2024, "sales_idx") / at("new", 2019, "sales_idx")
out["H3_detail"] = {"count_2024_vs_2019": r(c19, 2), "marr_2024_vs_2019": r(m19, 2), "sales_2024_vs_2019": r(s19, 2), "diff_pt": r(c19 - m19, 2),
                    "marr_2025_vs_2019": r(100 * mar.loc[2025, "marriages"] / mar.loc[2019, "marriages"], 2)}
out["H3"] = "支持" if c19 - m19 <= -10 else "外れ"
g1 = P["old"]["count_rate"] - P["old"]["first_rate"]
g2 = P["new_pre"]["count_rate"] - P["new_pre"]["first_rate"]
h4 = "支持" if (g1 <= -1 and g2 <= -1) else ("判定できず" if (g1 <= -1 or g2 <= -1) else "外れ")
out["H4_detail"] = {"gap_old_first": r(g1, 3), "gap_new_pre_first": r(g2, 3), "H1_with_first": h4}
out["H4"] = "支持" if h4 == out["H1"] else "外れ"

# 4) 頑健性
rob = []
lv = w.set_index("year")


def add(case, gap_old_, gap_new_, unit_old_, unit_new_, note=""):
    rob.append({"case": case, "gap_old": gap_old_, "gap_new": gap_new_, "unit_real_old": unit_old_, "unit_real_new": unit_new_, "note": note})


add("主な結果（伸び率をつないだ指数、総数の婚姻、総合の物価）", gap_old, gap_new, ur_old, ur_new)
# (1) 実数の比（断層のない区間）：旧 2006→2013年（2006年1月と2014年4月の対象追加の間）、新 2015→2018年（2019年1月の見直しの前）
def lvl_gap(y0, y1):
    n = y1 - y0
    cr = 100 * np.log(lv.loc[y1, "count_level"] / lv.loc[y0, "count_level"]) / n
    mr = 100 * np.log(mar.loc[y1, "marriages"] / mar.loc[y0, "marriages"]) / n
    u = (lv.loc[y1, "sales_level"] / lv.loc[y1, "count_level"]) / (lv.loc[y0, "sales_level"] / lv.loc[y0, "count_level"])
    ur = 100 * (u / (cpi.loc[y1, "cpi_all"] / cpi.loc[y0, "cpi_all"]) - 1)
    return cr - mr, ur
lo = lvl_gap(2006, 2013)
ln = lvl_gap(2015, 2018)
add("実数の比（断層をまたがない区間：旧 2006→2013年、新 2015→2018年）", lo[0], ln[0], lo[1], ln[1], "途中に一部数値の変更あり（表の注）")
add("婚姻を「夫妻とも初婚」に替える（H4）", g1, g2, ur_old, ur_new)
po = period("old", 2000, 2014, drop=(2011,))
add("2011年の変化を除く（旧様式）", po["count_rate"] - po["marr_rate"], gap_new, po["unit_real_cum_pct"], ur_new, "1件あたりは2011年を含む累積")
pa = P["new_all"]
add("新様式を2015→2024年に延ばす", gap_old, pa["count_rate"] - pa["marr_rate"], ur_old, pa["unit_real_cum_pct"])
add("物価を「生鮮食品を除く総合」に替える", gap_old, gap_new,
    100 * ((1 + P["old"]["unit_cum_pct"] / 100) / (1 + P["old"]["cpicore_cum_pct"] / 100) - 1),
    100 * ((1 + P["new_pre"]["unit_cum_pct"] / 100) / (1 + P["new_pre"]["cpicore_cum_pct"] / 100) - 1))
# (6) 月の伸び率から作った年の値との照合（前年の月の実数で重みづけ）
mo = pd.read_csv(DATA / "wedding_monthly.csv")
chk = []
for y in range(2001, 2025):
    if y == 2015:
        continue
    cur = mo[mo.year == y].set_index("month")
    prev = mo[mo.year == y - 1].set_index("month")
    if len(cur) < 12 or len(prev) < 12 or cur.count_growth.isna().any():
        continue
    gm = 100 * ((prev.count_level * (1 + cur.count_growth / 100)).sum() / prev.count_level.sum() - 1)
    ga = float(w[(w.year == y)].count_growth.dropna().iloc[0])
    chk.append({"year": y, "annual_growth": ga, "from_monthly": gm, "diff": gm - ga})
chk = pd.DataFrame(chk)
chk.to_csv(RES / "check_monthly_vs_annual.csv", index=False, float_format="%.4f")
out["monthly_check"] = {"n_years": int(len(chk)), "max_abs_diff": r(float(chk["diff"].abs().max()), 2), "mean_abs_diff": r(float(chk["diff"].abs().mean()), 2)}
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")
out["robust"] = {"n": int(len(rob)), "gap_old_max": r(float(rob.gap_old.max()), 3), "gap_new_max": r(float(rob.gap_new.max()), 3),
                 "gap_old_min": r(float(rob.gap_old.min()), 3), "gap_new_min": r(float(rob.gap_new.min()), 3),
                 "unit_real_old_min": r(float(rob.unit_real_old.min()), 2), "unit_real_new_min": r(float(rob.unit_real_new.min()), 2)}
# 要約
out["levels"] = {"marr_2000": int(mar.loc[2000, "marriages"]), "marr_2014": int(mar.loc[2014, "marriages"]), "marr_2015": int(mar.loc[2015, "marriages"]),
                 "marr_2019": int(mar.loc[2019, "marriages"]), "marr_2024": int(mar.loc[2024, "marriages"]), "marr_2025": int(mar.loc[2025, "marriages"]),
                 "unit_2000_man": r(at("old", 2000, "unit_level_man_yen"), 1), "unit_2014_man": r(at("old", 2014, "unit_level_man_yen"), 1),
                 "unit_2015_man": r(at("new", 2015, "unit_level_man_yen"), 1), "unit_2019_man": r(at("new", 2019, "unit_level_man_yen"), 1),
                 "unit_2024_man": r(at("new", 2024, "unit_level_man_yen"), 1),
                 "count_idx_2014": r(at("old", 2014, "count_idx"), 2), "marr_idx_2014": r(at("old", 2014, "marr_idx"), 2), "sales_idx_2014": r(at("old", 2014, "sales_idx"), 2),
                 "share_idx_2014": r(at("old", 2014, "share_idx"), 2), "share_idx_2019": r(at("new", 2019, "share_idx"), 2), "share_idx_2024": r(at("new", 2024, "share_idx"), 2),
                 "count_idx_2019": r(at("new", 2019, "count_idx"), 2), "marr_idx_2019": r(at("new", 2019, "marr_idx"), 2), "sales_idx_2019": r(at("new", 2019, "sales_idx"), 2),
                 "count_idx_2024": r(at("new", 2024, "count_idx"), 2), "marr_idx_2024": r(at("new", 2024, "marr_idx"), 2), "sales_idx_2024": r(at("new", 2024, "sales_idx"), 2)}
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
print(rob.to_string()); print(dec.to_string()); print(chk.to_string())
