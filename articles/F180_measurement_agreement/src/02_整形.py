"""02 整形：国勢調査（SSDSE-A）・住民基本台帳・労働力調査（モデル推計）を、同じ単位の表にそろえる。
入力: data/raw/ （01_取得.md の手順で取得したもの）
出力: data/pairs_pref.csv, data/pairs_muni.csv
"""
import pandas as pd, numpy as np, pathlib
B = pathlib.Path(__file__).resolve().parents[1]; R = B / "data" / "raw"; O = B / "data"

# --- 国勢調査（SSDSE-A。2021年版=2015年国勢調査、2026年版=2020年国勢調査）
KEEP = ["A1101", "A1102", "A1700", "A1302", "A1303", "A7101", "F1102", "F1107", "F1108"]
def ssdse(fn, year):
    raw = pd.read_csv(R / fn, encoding="cp932", header=None, dtype=str)
    cols = list(raw.iloc[0]); d = raw.iloc[3:].copy(); d.columns = cols
    d = d.rename(columns={cols[0]: "code", cols[1]: "pref", cols[2]: "muni"})
    d["code5"] = d["code"].str[1:]
    for k in KEEP: d[k] = pd.to_numeric(d[k], errors="coerce")
    d["year"] = year
    return d[["year", "code5", "pref", "muni"] + KEEP]
cen = pd.concat([ssdse("SSDSE-A-2021.csv", 2015), ssdse("SSDSE-A-2026.csv", 2020)])
cen["pref_code"] = cen["code5"].str[:2].astype(int)
cen.to_csv(O / "census_muni_2015_2020.csv", index=False)

# --- 住民基本台帳（翌年1月1日。2016年・2021年は都道府県と市区町村、2015年・2020年は都道府県の総数だけ）
j = pd.read_csv(R / "juki_2016_2021_raw.csv", dtype=str, encoding="utf-8-sig")
j["code5"] = j["c0"].str[:5]
def num(s): return pd.to_numeric(s, errors="coerce")
rows = []
for s, g in j.groupby("set"):
    yr = int(s[:4]) - 1  # 1月1日の値を、前年10月1日の国勢調査と並べる
    if "_pref_" in s:
        kind = s.split("_")[2]
        rows.append(pd.DataFrame({"year": yr, "pref_code": num(g["c0"].str[:2]).astype(int), "kind": kind,
                                  "pop": num(g["c4"]), "hh": num(g["c5"] if kind != "japanese" else g["c7"])}))
jp = pd.concat(rows).pivot_table(index=["year", "pref_code"], columns="kind", values=["pop", "hh"]).reset_index()
jp.columns = ["year", "pref_code"] + [f"juki_{a}_{b}" for a, b in jp.columns[2:]]
prev = pd.read_csv(R / "juki_pref_total_2015_2020.csv")
prev["year"] = prev["date"].str[:4].astype(int)
prev = prev.rename(columns={"juki_pop": "juki_pop_total_jan", "juki_hh": "juki_hh_total_jan"})[["year", "pref_code", "juki_pop_total_jan", "juki_hh_total_jan"]]
jp = jp.merge(prev, on=["year", "pref_code"], how="left")
# 10月1日へ直線でならした値（その年1月1日×0.25＋翌年1月1日×0.75）
for v in ["pop", "hh"]:
    jp[f"juki_{v}_total_oct"] = 0.25 * jp[f"juki_{v}_total_jan"] + 0.75 * jp[f"juki_{v}_total"]

m = j[j["set"].str.contains("muni_total") & j["c2"].notna() & (j["c2"] != "-") & (j["c2"] != "")].copy()
m = pd.DataFrame({"year": m["set"].str[:4].astype(int) - 1, "code5": m["code5"], "juki_pop": num(m["c5"]), "juki_hh": num(m["c6"])})

# --- 労働力調査 都道府県別モデル推計（F01 のデータ。千人単位、率は小数1桁）
l = pd.read_csv(R / "lfs_pref_panel_from_F01.csv")
l = l[l["year"].isin([2015, 2020])].rename(columns={"code": "pref_code"})
l = l[["year", "pref_code", "pop15", "emp", "emp_rate", "unemp_rate"]].rename(columns={
    "pop15": "lfs_pop15_k", "emp": "lfs_emp_k", "emp_rate": "lfs_emp_rate", "unemp_rate": "lfs_unemp_rate"})

# --- 都道府県にまとめる
cp = cen.groupby(["year", "pref_code"])[KEEP].sum().reset_index()
pref_name = cen.drop_duplicates("pref_code").set_index("pref_code")["pref"]
cp["pref"] = cp["pref_code"].map(pref_name)
cp["cen_lab_known"] = cp["F1102"] + cp["F1107"] + cp["F1108"]  # 労働力状態「不詳」を除いた15歳以上
cp["cen_pop15"] = cp["A1302"] + cp["A1303"]                       # 年齢「不詳」を除いた15歳以上
cp["cen_unemp_rate"] = 100 * cp["F1107"] / (cp["F1102"] + cp["F1107"])
cp["cen_emp_rate_known"] = 100 * cp["F1102"] / cp["cen_lab_known"]
cp["cen_emp_rate_all15"] = 100 * cp["F1102"] / cp["cen_pop15"]
cp["cen_labor_unknown_share"] = 100 * (1 - cp["cen_lab_known"] / cp["cen_pop15"])
P = cp.merge(jp, on=["year", "pref_code"]).merge(l, on=["year", "pref_code"])
P.to_csv(O / "pairs_pref.csv", index=False)

M = cen[["year", "code5", "pref_code", "A1101", "A7101"]].merge(m, on=["year", "code5"], how="inner")
M.to_csv(O / "pairs_muni.csv", index=False)
print("pref", P.shape, "muni", M.shape, "muni per year", M.groupby("year").size().to_dict(),
      "census munis", cen.groupby("year").size().to_dict())
