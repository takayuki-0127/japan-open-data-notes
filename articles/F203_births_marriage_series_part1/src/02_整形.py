"""raw の表を、分析に使う整った CSV にする。

出力（data/）
- national_asfr5.csv     : 全国の5歳階級別出生率（各歳の率の平均）1950〜2023年（F58 のデータから）
- national_married.csv   : 全国の女性の年齢別 有配偶割合・未婚割合（国勢調査 1970〜2020年、2025年は不詳補完値）
- areas_2020.csv         : 都道府県・市区町村ごとの、女性の年齢別 総数・有配偶・未婚（2020年国勢調査 不詳補完値）と
                            合計特殊出生率・母の年齢階級別出生率（2018〜22年、ベイズ推定値と素の値）
"""
import json, re
import numpy as np, pandas as pd
from common import RAW, DATA, AGES

# 1) 全国 5歳階級の出生率（年 × 年齢階級）。各歳の率を足して5で割る＝5歳階級の平均の率
a = pd.read_csv(RAW / "f58_asfr_single_year.csv")
rows = []
for _, r in a.iterrows():
    d = {"year": int(r["year"])}
    for g in AGES:
        lo = int(g[:2]); d[g] = float(np.mean([r[str(x)] for x in range(lo, lo + 5)]))
    d["tfr"] = 5 * sum(d[g] for g in AGES)
    rows.append(d)
pd.DataFrame(rows).to_csv(DATA / "national_asfr5.csv", index=False)

# 2) 全国の有配偶・未婚の割合（％）。表6-24 の女の部分
t = json.load(open(RAW / "f87_ipss_T06.json", encoding="utf-8"))["T06-24"]
def women(sheet):
    tab = t[sheet]; hdr = tab[2]
    years = [int(re.match(r"(\d{4})", str(h)).group(1)) for h in hdr[1:]]
    i0 = [i for i, r in enumerate(tab) if r[1] == "女"][0]
    out = {}
    for r in tab[i0 + 1:]:
        lab = str(r[0]).strip().replace("～", "-")
        if lab in AGES:
            out[lab] = dict(zip(years, r[1:]))
    return out
mar = women("T06-24 (2)"); unm = women("T06-24(1)")
rows = []
for y in [1970, 1980, 1990, 2000, 2010, 2015, 2020]:
    for g in AGES:
        rows.append({"year": y, "age": g, "married": mar[g][y] / 100, "never": unm[g][y] / 100})
# 2025 年（不詳補完値の全国の数）
h = json.load(open(RAW / "f120_census_hokan_marital.json", encoding="utf-8"))["t4_3_hokan2025"].split("\n")
def pick(kind):
    for line in h:
        c = line.split(",")
        if len(c) > 13 and c[3] == "0_国籍総数" and c[4] == "2_女" and c[5] == kind:
            return [float(x) for x in c[7:14]]
tot, m25, n25 = pick("0_総数"), pick("2_有配偶"), pick("1_未婚")
for g, T, M, N in zip(AGES, tot, m25, n25):
    rows.append({"year": 2025, "age": g, "married": M / T, "never": N / T})
pd.DataFrame(rows).to_csv(DATA / "national_married.csv", index=False)

# 3) 地域：国勢調査2020（不詳補完値）と 出生率2018〜22（ベイズ推定値）
c = pd.read_csv(RAW / "f203_census2020_women_marital.csv", dtype={"code": str})
c["code"] = c["code"].str.zfill(5)
cols = ["a15_19", "a20_24", "a25_29", "a30_34", "a35_39", "a40_44", "a45_49"]
w = c.pivot_table(index=["code", "name", "level"], columns="marital", values=cols, aggfunc="first")
out = pd.DataFrame(index=w.index)
for col, g in zip(cols, AGES):
    out["tot_" + g] = w[(col, 0)]; out["mar_" + g] = w[(col, 2)]; out["nev_" + g] = w[(col, 1)]
out = out.reset_index()
f = pd.read_csv(RAW / "f203_tfr_bayes_2018_22.csv", dtype=str)
f["key"] = f["label"].str.extract(r"^(\d+)")[0]
f.loc[f["label"].str.contains("全国"), "key"] = "00"
def num(s):
    return pd.to_numeric(s.str.replace("*", "", regex=False).replace({"-": "0", "…": np.nan, "": np.nan}), errors="coerce")
for k in ["tfr_bayes", "b15", "b20", "b25", "b30", "b35", "b40", "b45", "tfr_raw", "r15", "r20", "r25", "r30", "r35", "r40", "r45"]:
    f[k] = num(f[k])
f["tfr_flag"] = f["tfr_flag"].fillna("").str.contains(r"\*")
pref = f[f["key"].str.len() == 2].copy(); pref["code"] = pref["key"] + "000"
muni = f[f["key"].str.len() == 5].copy(); muni["code"] = muni["key"]
nat = f[f["key"] == "00"]
f = f[f["key"].notna() & (f["key"] != "00")].copy()
keep = ["code", "tfr_bayes", "b15", "b20", "b25", "b30", "b35", "b40", "b45", "tfr_raw", "tfr_flag", "r15", "r20", "r25", "r30", "r35", "r40", "r45"]
pref_c = out[out["level"] == "a"].copy(); pref_c = pref_c[pref_c["code"] != "00000"]
pref_c["code"] = pref_c["code"].str[:2] + "000"
pref_df = pref_c.merge(pref[keep], on="code", how="inner"); pref_df["kind"] = "pref"
# 市区町村：市町村・政令市（全体）・東京23区。政令市の区は使わない（市全体で数える）
lv = out["level"].astype(str)
is_unit = lv.isin(["1", "2", "3"]) | ((lv == "0") & out["code"].str.startswith("131"))
mu = out[is_unit & (out["code"] != "13100")].copy()
muni_df = mu.merge(muni[keep], on="code", how="inner"); muni_df["kind"] = "muni"
areas = pd.concat([pref_df, muni_df], ignore_index=True)
areas.to_csv(DATA / "areas_2020.csv", index=False)
n = nat.iloc[0]
pd.DataFrame([{"age": g, "asfr_bayes": float(n[k]) / 1000} for g, k in zip(AGES, ["b15", "b20", "b25", "b30", "b35", "b40", "b45"])]).to_csv(DATA / "national_asfr_2018_22.csv", index=False)
print("pref", len(pref_df), "muni", len(muni_df), "unmatched muni", len(mu) - len(muni_df))
