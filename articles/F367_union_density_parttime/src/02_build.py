"""02_build.py : 労働組合基礎調査の時系列表から、年ごとの組合員数・雇用者数・パートの値、企業規模別の組合員数を取り出す（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def n(s):
    return "" if pd.isna(s) else re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    s = n(x).replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else float("nan")


def year_rows(v, col):
    out = {}
    for i in range(len(v)):
        y = num(v.iat[i, col])
        if 1940 < y < 2100 and int(y) not in out:
            out[int(y)] = i
    return out


def build_total():
    v = pd.read_excel(RAW / "ts1_members_density.xlsx", header=None)
    assert n(v.iat[2, 3]) == "単位労働組合" and n(v.iat[2, 5]) == "単一労働組合" and n(v.iat[2, 7]) == "雇用者数" and n(v.iat[2, 8]) == "推定組織率"
    rows = [{"year": y, "unit_unions": num(v.iat[i, 3]), "unit_members": num(v.iat[i, 4]), "single_unions": num(v.iat[i, 5]),
             "single_members": num(v.iat[i, 6]), "employees_10k": num(v.iat[i, 7]), "density_pub": num(v.iat[i, 8])}
            for y, i in year_rows(v, 2).items()]
    return pd.DataFrame(rows)


def build_part():
    v = pd.read_excel(RAW / "ts8_parttime.xlsx", header=None)
    assert "パートタイム労働者" in n(v.iat[1, 2]) and "旧定義" in n(v.iat[1, 4]) and "新定義" in n(v.iat[1, 7])
    rows = [{"year": y, "part_members": num(v.iat[i, 2]), "part_emp_old_10k": num(v.iat[i, 4]), "part_density_old": num(v.iat[i, 5]),
             "part_emp_new_10k": num(v.iat[i, 7]), "part_density_new": num(v.iat[i, 8])} for y, i in year_rows(v, 1).items()]
    return pd.DataFrame(rows)


def build_size():
    v = pd.read_excel(RAW / "ts3_by_firm_size.xlsx", header=None)
    cols = {"計（全体）": 3, "民営計": 5, "5000人以上": 7, "1000〜4999人": 9, "500〜999人": 13, "300〜499人": 15, "100〜299人": 17,
            "30〜99人": 19, "29人以下": 23, "民営その他": 25, "民営以外": 27}
    hdr = {"5000人以上": "5,000人以上", "1000〜4999人": "1,000～4,999人", "500〜999人": "500～999人", "300〜499人": "300～499人",
           "100〜299人": "100～299人", "30〜99人": "30～99人", "29人以下": "29人以下", "民営その他": "その他"}
    for k, h in hdr.items():
        assert n(v.iat[2, cols[k] - 1]) == n(h), (k, n(v.iat[2, cols[k] - 1]))
    rows = []
    for y, i in year_rows(v, 1).items():
        for k, c in cols.items():
            rows.append({"year": y, "size": k, "members": num(v.iat[i, c])})
    df = pd.DataFrame(rows)
    w = df.pivot_table(index="year", columns="size", values="members")
    ok = w.dropna()
    parts = ["5000人以上", "1000〜4999人", "500〜999人", "300〜499人", "100〜299人", "30〜99人", "29人以下", "民営その他"]
    chk = (ok[parts].sum(axis=1) - ok["民営計"]).abs().loc[2000:]
    assert chk.max() < 1, chk.max()
    return df


if __name__ == "__main__":
    t = build_total().merge(build_part(), on="year", how="left").sort_values("year")
    t.to_csv(OUT / "union_total_part.csv", index=False, float_format="%.1f")
    s = build_size().sort_values(["size", "year"])
    s.to_csv(OUT / "union_members_by_firm_size.csv", index=False, float_format="%.0f")
    print(t[t.year >= 2012].to_string())
