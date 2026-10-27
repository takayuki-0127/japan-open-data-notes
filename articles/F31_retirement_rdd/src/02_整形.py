"""02 整形：5回の国勢調査の表を「年×男女×年齢（各歳）」の縦長の表にそろえる。
就業率 = 就業者 ÷（総数 − 労働力状態「不詳」）。不詳は2015・2020年に大きく増えたので、分母から除く。
2000・2005年の表には不詳の列がないので、総数 −（労働力人口＋非労働力人口）を不詳とみなす。"""
import json, re
import numpy as np, pandas as pd
from common import RAW, DATA

def num(v):
    if v is None: return np.nan
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace(",", "")
    try: return float(s)
    except ValueError: return np.nan

def age_of(label):
    s = str(label).replace("　", "").replace(" ", "").replace("歳", "")
    s = re.sub(r"^\d\d_", "", s)
    return int(s) if re.fullmatch(r"\d{1,3}", s) else None

def rows_old(a, year):
    """2000・2005年（報告書掲載表の Excel）。列：11 総数,12 労働力人口,13 就業者,18 完全失業者,19 非労働力人口"""
    sexmap = {"01": "総数", "02": "男", "03": "女"}
    out = []
    for r in a:
        if r is None or len(r) < 20 or r[2] is None: continue
        sx = sexmap.get(str(r[2]).strip())
        ag = age_of(r[7]) if r[7] is not None else None
        if sx is None or ag is None: continue
        tot, lf, emp, un, nlf = num(r[11]), num(r[12]), num(r[13]), num(r[18]), num(r[19])
        out.append(dict(year=year, sex=sx, age=ag, pop=tot, lf=lf, emp=emp, unemp=un, nlf=nlf, unknown=tot - lf - nlf))
    return out

def rows_2010(a):
    sexmap = {"01": "総数", "02": "男", "03": "女"}
    out = []
    for r in a:
        if len(r) < 20 or str(r[3]).strip() != "a" or str(r[2]).strip() != "00000": continue
        sx = sexmap.get(str(r[1]).strip()); ag = age_of(r[6])
        if sx is None or ag is None: continue
        out.append(dict(year=2010, sex=sx, age=ag, pop=num(r[7]), lf=num(r[8]), emp=num(r[9]),
                        unemp=num(r[14]), nlf=num(r[15]), unknown=num(r[19])))
    return out

def rows_2015(a):
    """2015年：大項目 01=国籍総数, 02=日本人。列は 総数(7〜20)・男(21〜34)・女(35〜48)"""
    out = []
    for r in a:
        if len(r) < 49 or str(r[3]).strip() != "a" or str(r[2]).strip() != "00000": continue
        nat = {"01": "総数", "02": "日本人"}.get(str(r[1]).strip()); ag = age_of(r[6])
        if nat is None or ag is None: continue
        for sx, o in [("総数", 7), ("男", 21), ("女", 35)]:
            out.append(dict(year=2015, nat=nat, sex=sx, age=ag, pop=num(r[o]), lf=num(r[o + 1]), emp=num(r[o + 2]),
                            unemp=num(r[o + 7]), nlf=num(r[o + 8]), unknown=num(r[o + 12])))
    return out

def rows_2020(rows, region="00000_全国"):
    sexmap = {"0_総数": "総数", "1_男": "男", "2_女": "女"}
    out = []
    for r in rows:
        if len(r) < 18 or r[1] is None: continue
        if region is not None and r[1] != region: continue
        sx = sexmap.get(r[3]); ag = age_of(r[4])
        if sx is None or ag is None or not str(r[2]).startswith("0_"): continue
        out.append(dict(year=2020, pref=r[1], sex=sx, age=ag, pop=num(r[5]), lf=num(r[6]), emp=num(r[7]),
                        unemp=num(r[12]), nlf=num(r[13]), unknown=num(r[17])))
    return out

if __name__ == "__main__":
    d = json.load(open(RAW / "f31_census_lfs.json", encoding="utf-8"))
    p = json.load(open(RAW / "f31_census2020_pref.json", encoding="utf-8"))
    sheet = lambda y: list(d[str(y)]["sheets"].values())[0]
    rows = rows_old(sheet(2000), 2000) + rows_old(sheet(2005), 2005) + rows_2010(sheet(2010))
    r15 = rows_2015(sheet(2015))
    rows += [{k: v for k, v in x.items() if k != "nat"} for x in r15 if x["nat"] == "総数"]
    rows += [{k: v for k, v in x.items() if k != "pref"} for x in rows_2020(p["rows"])]
    df = pd.DataFrame(rows).drop_duplicates(["year", "sex", "age"])
    df["pop_known"] = df["pop"] - df["unknown"]
    df["emp_rate"] = df["emp"] / df["pop_known"]
    df["lf_rate"] = df["lf"] / df["pop_known"]
    df["unemp_rate"] = df["unemp"] / df["lf"]
    df["unknown_share"] = df["unknown"] / df["pop"]
    df = df.sort_values(["year", "sex", "age"])
    df.to_csv(DATA / "lfs_single_age.csv", index=False, encoding="utf-8")
    # 2015年 日本人（頑健性）
    jp = pd.DataFrame([x for x in r15 if x["nat"] == "日本人"]).drop(columns="nat")
    jp["pop_known"] = jp["pop"] - jp["unknown"]; jp["emp_rate"] = jp["emp"] / jp["pop_known"]
    jp.to_csv(DATA / "lfs_single_age_2015_japanese.csv", index=False, encoding="utf-8")
    # 2020年 都道府県
    pr = pd.DataFrame([x for x in rows_2020(p["rows"], region=None) if x["pref"] != "00000_全国"])
    pr["pop_known"] = pr["pop"] - pr["unknown"]; pr["emp_rate"] = pr["emp"] / pr["pop_known"]
    pr.to_csv(DATA / "lfs_single_age_2020_pref.csv", index=False, encoding="utf-8")
    # 検算：各歳の合計が総数行と一致するか（年×男女）
    print(df.groupby(["year", "sex"]).agg(n=("age", "size"), amin=("age", "min"), amax=("age", "max"), pop=("pop", "sum")))
    print(df[(df.sex == "総数") & df.age.isin([59, 60, 64, 65])][["year", "age", "emp_rate", "unknown_share"]])
    print("pref", pr.pref.nunique(), len(pr))
