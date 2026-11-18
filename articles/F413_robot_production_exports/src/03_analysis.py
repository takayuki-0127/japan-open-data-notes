"""輸出 ÷ 生産、前年比の相関、輸出先の割合、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
NAME_JA = {105: "中国", 103: "韓国", 106: "台湾", 304: "米国", 213: "ドイツ", 110: "ベトナム", 111: "タイ", 123: "インド",
           113: "マレーシア", 118: "インドネシア", 305: "メキシコ", 112: "シンガポール", 108: "香港", 117: "フィリピン",
           220: "イタリア", 209: "ルクセンブルク", 210: "フランス", 205: "英国", 207: "オランダ", 302: "カナダ", 218: "スペイン", 234: "トルコ",
           224: "ロシア", 223: "ポーランド", 245: "チェコ", 410: "ブラジル"}
ZONE_JA = {"Asia": "アジア", "Western Europe": "西欧", "North America": "北米", "Central and East Europe, Russia etc.": "中東欧・ロシアなど",
           "Central and South America": "中南米", "Middle East": "中東", "Africa": "アフリカ", "Oceania": "大洋州"}


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


def main():
    p = pd.read_csv(D / "production_annual.csv", index_col=0)
    e = pd.read_csv(D / "exports_by_country.csv", dtype={"hs": str})
    yrs = list(range(2009, 2026))
    ex = e.groupby(["year", "hs"])[["value_kyen", "units"]].sum().unstack("hs").fillna(0)
    t = pd.DataFrame(index=yrs)
    t.index.name = "year"
    t["prod_oku"] = p.loc[yrs, "value_total"] / 100  # 百万円 → 億円
    t["prod_ex_parts_oku"] = (p.loc[yrs, "value_total"] - p.loc[yrs, "parts_value"]) / 100
    t["prod_units_pb_nc"] = p.loc[yrs, "playback_qty"] + p.loc[yrs, "nc_qty"]
    t["prod_value_pb_nc_oku"] = (p.loc[yrs, "playback_value"] + p.loc[yrs, "nc_value"]) / 100
    t["exp_847950_oku"] = ex[("value_kyen", "847950")].reindex(yrs).values / 1e5
    t["exp_842870_oku"] = ex[("value_kyen", "842870")].reindex(yrs).fillna(0).values / 1e5 if ("value_kyen", "842870") in ex.columns else 0.0
    t["exp_oku"] = t["exp_847950_oku"] + t["exp_842870_oku"]
    t["exp_units"] = (ex[("units", "847950")].reindex(yrs).values + (ex[("units", "842870")].reindex(yrs).fillna(0).values if ("units", "842870") in ex.columns else 0))
    t["ratio_pct"] = t["exp_oku"] / t["prod_oku"] * 100
    t["ratio_ex_parts_pct"] = t["exp_oku"] / t["prod_ex_parts_oku"] * 100
    t["ratio_847950_only_pct"] = t["exp_847950_oku"] / t["prod_oku"] * 100
    t["ratio_units_pct"] = t["exp_units"] / t["prod_units_pb_nc"] * 100
    t["prod_minus_exp_oku"] = t["prod_oku"] - t["exp_oku"]
    t["dl_prod"] = np.log(t["prod_oku"]).diff() * 100
    t["dl_exp"] = np.log(t["exp_oku"]).diff() * 100
    t["dl_rest"] = np.log(t["prod_minus_exp_oku"]).diff() * 100
    t.to_csv(R / "annual_panel.csv", float_format="%.6f")

    m = {"years": [yrs[0], yrs[-1]]}
    for y in [2009, 2012, 2017, 2022, 2025]:
        m[f"prod_{y}_oku"] = r6(t.loc[y, "prod_oku"]); m[f"exp_{y}_oku"] = r6(t.loc[y, "exp_oku"]); m[f"ratio_{y}_pct"] = r6(t.loc[y, "ratio_pct"])
    m["exp_842870_2025_oku"] = r6(t.loc[2025, "exp_842870_oku"])
    m["ratio_mean_2009_2012"] = r6(t.loc[2009:2012, "ratio_pct"].mean()); m["ratio_mean_2022_2025"] = r6(t.loc[2022:2025, "ratio_pct"].mean())
    m["ratio_max"] = r6(t["ratio_pct"].max()); m["ratio_max_year"] = int(t["ratio_pct"].idxmax())
    m["prod_peak_year"] = int(t["prod_oku"].idxmax()); m["prod_peak_oku"] = r6(t["prod_oku"].max())
    m["exp_peak_year"] = int(t["exp_oku"].idxmax()); m["exp_peak_oku"] = r6(t["exp_oku"].max())
    m["prod_ratio_2025_2009"] = r6(t.loc[2025, "prod_oku"] / t.loc[2009, "prod_oku"])
    m["exp_ratio_2025_2009"] = r6(t.loc[2025, "exp_oku"] / t.loc[2009, "exp_oku"])
    m["prod_ratio_2025_2012"] = r6(t.loc[2025, "prod_oku"] / t.loc[2012, "prod_oku"])
    m["exp_ratio_2025_2012"] = r6(t.loc[2025, "exp_oku"] / t.loc[2012, "exp_oku"])
    # 2012→2025 の生産の増加のうち、輸出の増加が占める割合
    dprod = t.loc[2025, "prod_oku"] - t.loc[2012, "prod_oku"]; dexp = t.loc[2025, "exp_oku"] - t.loc[2012, "exp_oku"]
    m["dprod_2012_2025_oku"] = r6(dprod); m["dexp_2012_2025_oku"] = r6(dexp); m["exp_share_of_growth_2012_2025"] = r6(dexp / dprod)
    m["rest_2012_oku"] = r6(t.loc[2012, "prod_minus_exp_oku"]); m["rest_2025_oku"] = r6(t.loc[2025, "prod_minus_exp_oku"])

    z = t.loc[2010:2025]
    c = float(np.corrcoef(z["dl_prod"], z["dl_exp"])[0, 1])
    m["corr_dl_2010_2025"] = r6(c)
    m["corr_dl_rest_2010_2025"] = r6(float(np.corrcoef(z["dl_prod"], z["dl_rest"])[0, 1]))
    m["same_sign_years"] = int((np.sign(z["dl_prod"]) == np.sign(z["dl_exp"])).sum()); m["n_years_corr"] = int(len(z))
    # レビューで追加：残り（生産 − 輸出）と生産の向きがそろった年数、2022〜2024年の前年差（億円）の内訳
    m["same_sign_years_rest"] = int((np.sign(z["dl_prod"]) == np.sign(z["dl_rest"])).sum())
    for y in [2022, 2023, 2024]:
        m[f"diff_prod_{y}_oku"] = r6(t.loc[y, "prod_oku"] - t.loc[y - 1, "prod_oku"])
        m[f"diff_exp_{y}_oku"] = r6(t.loc[y, "exp_oku"] - t.loc[y - 1, "exp_oku"])
        m[f"diff_rest_{y}_oku"] = r6(t.loc[y, "prod_minus_exp_oku"] - t.loc[y - 1, "prod_minus_exp_oku"])
    # 前年比で見た、生産と輸出の大きな動き
    m["dl_prod_2009"] = r6(np.log(t.loc[2009, "prod_oku"] / (p.loc[2008, "value_total"] / 100)) * 100)
    for y in [2017, 2019, 2021, 2024, 2025]:
        m[f"dl_prod_{y}"] = r6(t.loc[y, "dl_prod"]); m[f"dl_exp_{y}"] = r6(t.loc[y, "dl_exp"])

    # 輸出先
    e["name_ja"] = e["country"].map(NAME_JA).fillna(e["name_en"])
    e["zone_ja"] = e["zone"].map(ZONE_JA)
    tot = e.groupby("year")["value_kyen"].sum()
    bc = e.groupby(["year", "country", "name_ja"])["value_kyen"].sum().reset_index()
    bc["share_pct"] = bc.apply(lambda r: r["value_kyen"] / tot[r["year"]] * 100, axis=1)
    bc = bc.sort_values(["year", "value_kyen"], ascending=[True, False])
    bc.to_csv(R / "exports_share_by_country.csv", index=False, float_format="%.6f")
    bz = e.groupby(["year", "zone_ja"])["value_kyen"].sum().reset_index()
    bz["share_pct"] = bz.apply(lambda r: r["value_kyen"] / tot[r["year"]] * 100, axis=1)
    bz.to_csv(R / "exports_share_by_zone.csv", index=False, float_format="%.6f")
    top = {}
    for y in [2009, 2012, 2017, 2021, 2024, 2025]:
        s = bc[bc["year"] == y].head(6)
        top[str(y)] = [{"country": int(r.country), "name_ja": r.name_ja, "share_pct": r6(r.share_pct), "oku": r6(r.value_kyen / 1e5)} for r in s.itertuples()]
    m["top_destinations"] = top
    cn = bc[bc["country"] == 105].set_index("year")["share_pct"]
    top1 = bc.groupby("year").head(1).set_index("year")["country"]
    cn_top = [y for y in yrs if top1[y] == 105]
    m["china_top_years"] = cn_top
    m["china_top_from"] = int(min(y for y in yrs if all(top1[k] == 105 for k in range(y, yrs[-1] + 1))))
    m["china_share"] = {str(y): r6(cn.get(y, np.nan)) for y in yrs}
    m["china_share_max_year"] = int(cn.idxmax()); m["china_share_max"] = r6(cn.max())
    asia = bz[bz["zone_ja"] == "アジア"].set_index("year")["share_pct"]
    m["asia_share_2009"] = r6(asia[2009]); m["asia_share_2025"] = r6(asia[2025])
    # 中国向けの前年比と生産の前年比
    cnv = bc[bc["country"] == 105].set_index("year")["value_kyen"].reindex(yrs)
    t2 = pd.DataFrame({"dl_prod": t["dl_prod"], "dl_cn": np.log(cnv).diff() * 100, "dl_noncn": np.log(tot.reindex(yrs) - cnv).diff() * 100}).loc[2010:2025]
    m["corr_dl_prod_china"] = r6(float(np.corrcoef(t2["dl_prod"], t2["dl_cn"])[0, 1]))
    m["corr_dl_prod_nonchina"] = r6(float(np.corrcoef(t2["dl_prod"], t2["dl_noncn"])[0, 1]))

    # 仮説
    m["H1"] = {"ratio_2025": m["ratio_2025_pct"], "judge": "支持" if m["ratio_2025_pct"] >= 50 else "外れ"}
    d2 = m["ratio_mean_2022_2025"] - m["ratio_mean_2009_2012"]
    m["H2"] = {"diff_pt": r6(d2), "judge": "支持" if d2 >= 10 else "外れ"}
    m["H3"] = {"corr": m["corr_dl_2010_2025"], "judge": "支持" if c >= 0.8 else "外れ"}
    first = top["2025"][0]
    m["H4"] = {"top_2025": first["name_ja"], "share": first["share_pct"], "judge": "支持" if first["country"] == 105 and first["share_pct"] >= 30 else "外れ"}

    rob = []
    def add(check, how, value, judge):
        rob.append({"check": check, "how": how, "value": r6(value), "judge": judge})
    add("H1", "基本：2025年 輸出額 ÷ 生産金額（%）", m["ratio_2025_pct"], m["H1"]["judge"])
    v = t.loc[2025, "ratio_ex_parts_pct"]; add("H1", "生産金額から部品・付帯装置を除く", v, "支持" if v >= 50 else "外れ")
    v = t.loc[2025, "ratio_847950_only_pct"]; add("H1", "HS 8428.70 を足さない（8479.50 だけ）", v, "支持" if v >= 50 else "外れ")
    v = t.loc[2025, "ratio_units_pct"]; add("H1", "台数で（輸出台数 ÷ プレイバック・数値制御ロボットの生産台数）", v, "支持" if v >= 50 else "外れ")
    v = t.loc[2022:2025, "ratio_pct"].mean(); add("H1", "2022〜2025年の平均", v, "支持" if v >= 50 else "外れ")
    add("H2", "基本：2022〜25年平均 − 2009〜12年平均（ポイント）", d2, m["H2"]["judge"])
    v = t.loc[2022:2025, "ratio_pct"].mean() - t.loc[2010:2012, "ratio_pct"].mean(); add("H2", "基準を2010〜12年に（2009年を除く）", v, "支持" if v >= 10 else "外れ")
    v = t.loc[2022:2025, "ratio_units_pct"].mean() - t.loc[2009:2012, "ratio_units_pct"].mean(); add("H2", "台数で", v, "支持" if v >= 10 else "外れ")
    v = t.loc[2022:2025, "ratio_847950_only_pct"].mean() - t.loc[2009:2012, "ratio_847950_only_pct"].mean(); add("H2", "HS 8479.50 だけで", v, "支持" if v >= 10 else "外れ")
    add("H3", "基本：前年比の相関（2010〜2025年、16年）", c, m["H3"]["judge"])
    zz = z.drop(index=[2020, 2021]); v = float(np.corrcoef(zz["dl_prod"], zz["dl_exp"])[0, 1])
    add("H3", "2020・2021年を除く", v, "支持" if v >= 0.8 else "外れ")
    v = float(stats.spearmanr(z["dl_prod"], z["dl_exp"]).statistic); add("H3", "順位相関（スピアマン）", v, "支持" if v >= 0.8 else "外れ")
    zz = z.drop(index=[2010]); v = float(np.corrcoef(zz["dl_prod"], zz["dl_exp"])[0, 1])
    add("H3", "2010年（リーマン後の戻り）を除く", v, "支持" if v >= 0.8 else "外れ")
    w = t.loc[2010:2025]; v = float(np.corrcoef(np.log(w["prod_ex_parts_oku"]).diff().dropna(), np.log(w["exp_oku"]).diff().dropna())[0, 1])
    add("H3", "部品を除く生産で（2011〜2025年）", v, "支持" if v >= 0.8 else "外れ")
    add("H4", "基本：2025年の1位と割合（%）", first["share_pct"], m["H4"]["judge"])
    f24 = top["2024"][0]; add("H4", f"2024年（1位：{f24['name_ja']}）", f24["share_pct"], "支持" if f24["country"] == 105 and f24["share_pct"] >= 30 else "外れ")
    hk = bc[(bc["year"] == 2025) & (bc["country"].isin([105, 108]))]["share_pct"].sum(); add("H4", "中国＋香港（2025年）", hk, "支持" if hk >= 30 else "外れ")
    v = cn.loc[2021:2025].mean(); add("H4", "中国の割合の2021〜2025年の平均", v, "支持" if v >= 30 else "外れ")
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
    (R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["H1", "H2", "H3", "H4"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
