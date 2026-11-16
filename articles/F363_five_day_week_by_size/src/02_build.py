"""02_build.py : 各年の週休制の表（形が年で違う）から、規模別・産業計の割合を取り出す（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
SIZES = {"計": "計", "企業規模計": "計", "調査計": "計", "1,000人以上": "1000人以上", "1000人以上": "1000人以上",
         "100~999人": "100〜999人", "300~999人": "300〜999人", "100~299人": "100〜299人", "30~99人": "30〜99人"}


def n(s):
    if pd.isna(s):
        return ""
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    s = n(x)
    if s in ("-", "", "…"):
        return 0.0 if s == "-" else float("nan")
    return float(s)


def classify(h):
    h = re.sub(r"\d\)", "", h).replace("(単位:%)|", "").replace("|", "")
    if "週休1日" in h:
        return "w1"
    if "何らかの週休3日" in h:
        return "w3any"
    if "週休3日" in h:
        return None
    if "より" in h and "多い" in h:
        return "more"
    if "より" in h and "少ない" in h:
        return "less"
    if h == "完全週休2日制":
        return "full"
    if "何らかの週休2日" in h or h in ("週休2日制計", "週休2日制"):
        return "w2any"
    if "その他の週休2日" in h:
        return "other2"
    return None


def colmap(v, rows, cols):
    m = {}
    for j in cols:
        h = "|".join(n(v.iat[i, j]) for i in rows if n(v.iat[i, j]) and not re.fullmatch(r"[\d.\-]+", n(v.iat[i, j])))
        c = classify(h)
        if c and c not in m:
            m[c] = j
    assert "full" in m and "w1" in m, m
    return m


def rec(year, size, v, i, m):
    d = {"year": year, "size": size}
    for k in ["w1", "w2any", "less", "full", "more", "other2", "w3any"]:
        d[k] = num(v.iat[i, m[k]]) if k in m else float("nan")
    return d


def parse(year, path):
    xf = pd.ExcelFile(path)
    out = []
    if 2004 <= year <= 2021:
        for s in xf.sheet_names:
            v = xf.parse(s, header=None)
            size = next(SIZES[n(v.iat[r, c])] for r in range(1, 5) for c in range(3, 8) if n(v.iat[r, c]) in SIZES)
            m = colmap(v, range(2, 10), range(5, v.shape[1]))
            i = next(i for i in range(8, 14) if n(v.iat[i, 2]) == "調査産業計")
            out.append(rec(year, size, v, i, m))
    elif year <= 2003:
        v = xf.parse(xf.sheet_names[0], header=None)
        m = colmap(v, range(2, 9), range(6, v.shape[1]))
        size = None
        for i in range(len(v)):
            if n(v.iat[i, 0]) == "企業規模":
                size = SIZES[n(v.iat[i, 5])]
            if n(v.iat[i, 2]) == "調査産業計":
                out.append(rec(year, size, v, i, m))
    elif year == 2022:
        v = xf.parse(xf.sheet_names[0], header=None)
        m = colmap(v, range(5, 7), range(1, v.shape[1]))
        size = None
        for i in range(len(v)):
            a = n(v.iat[i, 0])
            if a in SIZES:
                size = SIZES[a]
            if "調査産業計" in a:
                out.append(rec(year, size, v, i, m))
    else:
        v = xf.parse(xf.sheet_names[0], header=None)
        m = colmap(v, range(2, 9), range(5, v.shape[1]))
        for i in range(9, 17):
            a = n(v.iat[i, 2]) or n(v.iat[i, 3])
            if a in SIZES:
                out.append(rec(year, SIZES[a], v, i, m))
    df = pd.DataFrame(out)
    assert set(["計", "1000人以上", "300〜999人", "100〜299人", "30〜99人"]) <= set(df["size"]), (year, list(df["size"]))
    return df


if __name__ == "__main__":
    parts = []
    for y in range(2001, 2026):
        p = next(RAW.glob(f"weekly_holiday_{y}.xls*"))
        parts.append(parse(y, p))
    df = pd.concat(parts, ignore_index=True)
    df.to_csv(OUT / "weekly_holiday_by_size.csv", index=False, float_format="%.1f")
    print(df[df["size"].isin(["計", "1000人以上", "30〜99人"])].pivot_table(index="year", columns="size", values="full"))
