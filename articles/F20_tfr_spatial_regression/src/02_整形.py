"""02 整形：出生率（ベイズ推定値）と地域の特徴を、市区町村（政令市は区）単位の1つの表にする。
単位は 国土数値情報 行政区域 2021（簡略版 TopoJSON）の1,902区域。"""
import json
import numpy as np
import pandas as pd
from common import RAW, DATA

d = json.load(open(RAW / "f20_raw.json", encoding="utf-8"))


def table(rows):
    h = rows[0]
    out = []
    for r in rows[1:]:
        code, name = r[0].split("_", 1)
        rec = {"code": code, "name": name}
        for c, v in zip(h[1:], r[1:]):
            v = v.replace(",", "")
            try:
                rec[c] = float(v)
            except ValueError:
                rec[c] = np.nan
        out.append(rec)
    return pd.DataFrame(out).set_index("code")


def tfr(rows):
    s = {}
    for code, name, bayes, raw in rows:
        s[code] = bayes if isinstance(bayes, (int, float)) else np.nan
    return pd.Series(s)


topo = json.load(open(RAW / "N03-21_210101.json", encoding="utf-8"))
geoms = list(topo["objects"].values())[0]["geometries"]
units = sorted({g["properties"]["N03_007"] for g in geoms if g["properties"].get("N03_007")})


def city_of(code):
    # 政令市の区（例 01101）→ 市（01100）。東京23区（131xx）はそのまま
    if code[:2] != "13" and code[2] == "1" and code[4] != "0":
        return code[:4] + "0"
    return code


def build(year_p, year_h, tfr_key):
    P = table(d[f"P{year_p}"])
    H = table(d[f"H{year_h}"])
    y = tfr(d[tfr_key])
    rows = []
    for u in units:
        rec = {"code": u}
        p = P.loc[u] if u in P.index else None
        if p is None:
            continue
        rec["name"] = p["name"]
        rec["pref"] = u[:2]
        rec["tfr"] = y.get(u, np.nan)
        pop = p["A1101"]
        rec["pop"] = pop
        rec["young_f"] = (p["A141402"] - p["A141502"]) / pop * 100
        # 所得：区の値がなければ市の値で補う
        inc, tax = p["C120110"], p["C120120"]
        if (np.isnan(inc) or np.isnan(tax)) and city_of(u) in P.index:
            inc, tax = P.loc[city_of(u), "C120110"], P.loc[city_of(u), "C120120"]
            rec["income_from_city"] = 1
        rec["income"] = np.log(inc / tax) if tax and tax > 0 else np.nan  # 納税者1人あたり課税対象所得（千円）の対数
        den = p["A6102"] + p["A6103"] + p["A6104"]
        rec["commute_out"] = (p["A6103"] + p["A6104"]) / den * 100 if den > 0 else np.nan
        nur = p.get("J250302", np.nan) if "J250302" in p.index else p.get("J2503", np.nan)
        rec["nursery"] = nur / p["A1405"] * 1000 if p["A1405"] > 0 else np.nan
        rec["tertiary"] = p["F2221"] / p["F1102"] * 100 if p["F1102"] > 0 else np.nan
        rec["density"] = np.log(pop / (p["B1103"] / 100)) if p["B1103"] > 0 else np.nan  # 可住地 1km2 あたり人口の対数
        rec["unmarried"] = p["A161001"]
        rec["aged"] = p["A1303"] / pop * 100
        if u in H.index:
            h = H.loc[u]
            rec["owner"] = h["H1310"] / h["H1101"] * 100 if h["H1101"] > 0 else np.nan
            rec["floor"] = h["H2130"]
        rows.append(rec)
    return pd.DataFrame(rows).set_index("code")


if __name__ == "__main__":
    a = build(2020, 2018, "tfr_2018_22")
    b = build(2015, 2013, "tfr_2013_17")
    a.to_csv(DATA / "municipal_2018_22.csv", encoding="utf-8")
    b.to_csv(DATA / "municipal_2013_17.csv", encoding="utf-8")
    for n, x in (("2018-22", a), ("2013-17", b)):
        print(n, len(x), "tfr", x.tfr.notna().sum(), "owner", x.owner.notna().sum(), "income_from_city", x.get("income_from_city", pd.Series()).sum())
        print(x.drop(columns=["name", "pref"]).describe().T[["count", "mean", "min", "max"]].round(2))
