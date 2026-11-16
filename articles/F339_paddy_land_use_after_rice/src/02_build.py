"""data/raw の Excel から、分析に使う整った CSV を data/ に作る（オフライン）。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def era_years(era_col, num_col):
    """元号の列（上の行から引き継ぐ）と年の列から西暦を作る。"""
    era = pd.Series(era_col).where(pd.Series(era_col).isin(ERA.keys())).ffill()
    out = []
    for e, n in zip(era, num_col):
        if pd.isna(e) or pd.isna(n):
            out.append(np.nan)
            continue
        s = str(n).strip()
        if s == "元":
            k = 1
        else:
            try:
                k = int(float(s))
            except ValueError:
                out.append(np.nan)
                continue
        out.append(ERA[e] + k)
    return out


def num(x):
    """「…」「-」などを数値に。- は 0、… は欠測。"""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().replace(",", "")
    if s in ("-", "－"):
        return 0.0
    if s in ("…", "x", "X", ""):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def build_summer_national():
    d = pd.read_excel(RAW / "summer_paddy_use_1966_2025.xlsx", header=None)
    d = d.iloc[10:70].copy()
    d["year"] = era_years(d[1], d[2])
    out = pd.DataFrame({
        "year": d["year"].astype(int),
        "paddy": d[4].map(num),
        "rice_field": d[5].map(num),          # 水稲作付田（2002年から）
        "rice_only": d[6].map(num),           # 水稲のみの作付田（2001年まで）
        "rice_and_other": d[7].map(num),      # 水稲と他作物の作付田（2001年まで）
        "nonrice_only": d[8].map(num),
        "unplanted": d[9].map(num),
    })
    # 2001年までは「水稲のみ」+「水稲と他作物」= 水稲作付田
    m = out["rice_field"].isna()
    out.loc[m, "rice_field"] = out.loc[m, "rice_only"] + out.loc[m, "rice_and_other"]
    out["residual"] = out["paddy"] - out["rice_field"] - out["nonrice_only"] - out["unplanted"]
    out = out.sort_values("year").reset_index(drop=True)
    out.to_csv(OUT / "summer_paddy_use_national.csv", index=False)
    return out


REGIONS = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉",
         "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重",
         "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島",
         "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]


def build_summer_region():
    rows = []
    # 令和7年の表：1〜4列が2024年、5〜8列が2025年
    d = pd.read_excel(RAW / "summer_paddy_use_region_2025.xlsx", header=None)
    names = d[0].astype(str).str.strip()
    i_pref = int(np.where(names == "（都道府県）")[0][0])
    for i in range(len(d)):
        nm = names.iloc[i]
        level = None
        if nm == "全国":
            level = "全国"
        elif nm in REGIONS and i < i_pref:
            level = "地域"
        elif nm in PREFS and i > i_pref:
            level = "都道府県"
        if level is None:
            continue
        for yr, c0 in ((2024, 1), (2025, 5)):
            rows.append(dict(level=level, name=nm, year=yr, paddy=num(d.iat[i, c0]), rice_field=num(d.iat[i, c0 + 1]),
                             nonrice_only=num(d.iat[i, c0 + 2]), unplanted=num(d.iat[i, c0 + 3])))
    # 平成16年の表：5〜8列が2004年、14〜17列が2003年。北海道は地域の行を都道府県にも使う
    d = pd.read_excel(RAW / "summer_paddy_use_region_2004.xls", header=None)
    names = d[0].astype(str).str.strip()
    i_pref = int(np.where(names == "中国四国農政局")[0][0])
    i_end = int(np.where(names == "（北海道内訳）")[0][0])
    for i in range(len(d)):
        nm = names.iloc[i]
        levels = []
        if nm == "全国":
            levels = ["全国"]
        elif nm in REGIONS and i < i_pref:
            levels = ["地域"] + (["都道府県"] if nm in ("北海道", "沖縄") else [])
        elif nm in PREFS and i_pref < i < i_end:
            levels = ["都道府県"]
        for level in levels:
            for yr, c0 in ((2004, 5), (2003, 14)):
                un = 8 if yr == 2004 else 17
                rows.append(dict(level=level, name=nm, year=yr, paddy=num(d.iat[i, c0]), rice_field=num(d.iat[i, c0 + 1]),
                                 nonrice_only=num(d.iat[i, c0 + 2]), unplanted=num(d.iat[i, un])))
    out = pd.DataFrame(rows)
    order = {n: k for k, n in enumerate(["全国"] + REGIONS)}
    porder = {n: k for k, n in enumerate(PREFS)}
    out["order"] = [order[n] if lv != "都道府県" else porder[n] for lv, n in zip(out["level"], out["name"])]
    out = out.sort_values(["level", "order", "year"]).reset_index(drop=True)
    out.to_csv(OUT / "summer_paddy_use_region.csv", index=False)
    return out


def build_paddy_crops():
    d = pd.read_excel(RAW / "paddy_crops_1967_2016.xls", header=None)
    d = d.iloc[9:59].copy()
    d["year"] = era_years(d[1], d[2])
    a = pd.DataFrame({"year": d["year"].astype(int), "total": d[5].map(num), "rice": d[6].map(num),
                      "wheat_barley": d[7].map(num), "sweet_potato": d[8].map(num), "minor_grains": d[9].map(num),
                      "pulses": d[10].map(num), "vegetables": d[11].map(num), "fruit": d[12].map(num),
                      "industrial": d[13].map(num), "mulberry": d[14].map(num), "feed_green": d[15].map(num),
                      "other": d[16].map(num), "utilization_pct": d[17].map(num), "honchi_utilization_pct": d[18].map(num)})
    a["table"] = "3-1（2016年まで）"
    d = pd.read_excel(RAW / "paddy_crops_2017_2024.xls", header=None)
    d = d.iloc[10:18].copy()
    d["year"] = era_years(d[1], d[2])
    b = pd.DataFrame({"year": d["year"].astype(int), "total": d[4].map(num), "wheat_barley": d[5].map(num),
                      "soybean": d[6].map(num), "buckwheat": d[7].map(num), "other_2017": d[8].map(num),
                      "utilization_pct": d[9].map(num), "honchi_utilization_pct": d[10].map(num)})
    # 2017年からの表には水稲の列がない。延べ面積から他の列を引いた残りを「水稲（なたねを含む）」とする
    b["rice"] = b["total"] - b["wheat_barley"] - b["soybean"] - b["buckwheat"] - b["other_2017"]
    b["table"] = "3-2（2017年から）"
    out = pd.concat([a, b], ignore_index=True).sort_values("year").reset_index(drop=True)
    out.to_csv(OUT / "paddy_crops.csv", index=False)
    return out


def build_abandon():
    d = pd.read_excel(RAW / "paddy_expansion_abandon_1956_2025.xlsx", header=None)
    d = d.iloc[13:83].copy()
    d["year"] = era_years(d[0], d[1])
    cols = {3: "exp_total", 4: "exp_reclaim", 5: "exp_landfill", 6: "exp_restore", 7: "exp_from_upland",
            8: "ab_total", 9: "ab_disaster", 10: "ab_human", 11: "ab_factory", 12: "ab_road", 13: "ab_housing",
            14: "ab_farmroad", 15: "ab_forest", 16: "ab_other", 17: "ab_abandoned", 18: "ab_to_upland"}
    out = pd.DataFrame({"year": d["year"].astype(int)})
    for c, n in cols.items():
        out[n] = d[c].map(num).values
    out = out.sort_values("year").reset_index(drop=True)
    out.to_csv(OUT / "paddy_expansion_abandon.csv", index=False)
    return out


def build_land():
    d = pd.read_excel(RAW / "land_area_honchi_1956_2025.xlsx", header=None)
    d = d.iloc[7:77].copy()
    yrs = d[0].astype(str).str.extract(r"\((\d{4})\)")[0]
    out = pd.DataFrame({"year": yrs.astype(float), "paddy_total": d[4].map(num), "paddy_honchi": d[5].map(num),
                        "paddy_keihan": d[6].map(num)}).dropna(subset=["year"])
    out["year"] = out["year"].astype(int)
    out.to_csv(OUT / "land_area_paddy.csv", index=False)
    return out


def build_rice():
    d = pd.read_excel(RAW / "rice_suito_longterm.xls", header=None)
    yrs = d[0].astype(str).str.extract(r"\((\d{4})\)")[0]
    out = pd.DataFrame({"year": yrs, "rice_grain_area": d[1].map(num), "rice_staple_area": d[2].map(num)}).dropna(subset=["year"])
    out["year"] = out["year"].astype(int)
    out = out[out["year"] >= 1956]
    f = pd.read_excel(RAW / "feed_rice_wcs_2008_2025.xlsx", header=None)
    f = f.iloc[8:26].copy()
    f["year"] = era_years(f[1], f[2])
    f = pd.DataFrame({"year": f["year"].astype(int), "feed_rice": f[4].map(num), "wcs": f[5].map(num)})
    out = out.merge(f, on="year", how="left").sort_values("year").reset_index(drop=True)
    out.to_csv(OUT / "rice_area.csv", index=False)
    return out


if __name__ == "__main__":
    s = build_summer_national()
    r = build_summer_region()
    c = build_paddy_crops()
    a = build_abandon()
    l = build_land()
    ri = build_rice()
    for n, x in [("summer_national", s), ("region", r), ("crops", c), ("abandon", a), ("land", l), ("rice", ri)]:
        print(n, x.shape)
