"""02_build.py : 雇用均等基本調査の表（年度で形が少し違う）から、男性・女性の育児休業者割合（総数・事業所規模別）と、
男性の取得期間の分布（総数・事業所規模別）を取り出す（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
SIZES = {"総数": "総数", "500人以上": "500人以上", "100～499人": "100〜499人", "30～99人": "30〜99人", "5～29人": "5〜29人",
         "30人以上(再掲)": "30人以上（再掲）"}


def n(s):
    return "" if pd.isna(s) else re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s))).replace("~", "～")


def num(x):
    s = n(x)
    if s in ("-", "－", "—"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return float("nan")


def rowlabel(v, i):
    for j in range(0, 3):
        s = n(v.iat[i, j])
        if s:
            return s
    return ""


def parse_rate(path, year):
    v = pd.read_excel(path, header=None)
    # 「男性」の見出しの列と、その次の「育児休業者」の列
    hr = next(i for i in range(0, 8) if any(n(v.iat[i, j]) == "男性" for j in range(v.shape[1])))
    jm = next(j for j in range(v.shape[1]) if n(v.iat[hr, j]) == "男性")
    jf = next(j for j in range(v.shape[1]) if n(v.iat[hr, j]) == "女性")
    assert n(v.iat[hr + 1, jm + 1]) == "育児休業者" and n(v.iat[hr + 1, jf + 1]) == "育児休業者", (path.name,)
    out = []
    for i in range(hr + 2, len(v)):
        lab = rowlabel(v, i)
        if lab in SIZES:
            out.append({"year": year, "size": SIZES[lab], "male": num(v.iat[i, jm + 1]), "female": num(v.iat[i, jf + 1])})
    df = pd.DataFrame(out).drop_duplicates("size")
    assert set(SIZES.values()) <= set(df["size"]), (path.name, list(df["size"]))
    return df


BINS = ["5日未満", "5日～2週間未満", "2週間～1か月未満", "1か月～3か月未満", "3か月～6か月未満", "6か月～8か月未満",
        "8か月～10か月未満", "10か月～12か月未満", "12か月～18か月未満", "18か月～24か月未満", "24か月～36か月未満", "36か月以上", "不明"]


def parse_period(path, year):
    xf = pd.ExcelFile(path)
    sh = next(s for s in xf.sheet_names if "男性" in n(" ".join(str(x) for x in xf.parse(s, header=None).iloc[0:3, 0:3].values.ravel())))
    v = xf.parse(sh, header=None)
    hr = next(i for i in range(0, 6) if any(n(v.iat[i, j]) == "5日未満" for j in range(v.shape[1])))
    cols = {}
    for j in range(v.shape[1]):
        h = n(v.iat[hr, j])
        for b in BINS:
            if h == n(b):
                cols[b] = j
    need = [b for b in BINS if b != "不明"]
    assert set(need) <= set(cols), (path.name, set(need) - set(cols))
    out = []
    for i in range(hr + 1, len(v)):
        lab = rowlabel(v, i)
        if lab in SIZES:
            rec = {"year": year, "size": SIZES[lab]}
            for b in BINS:
                rec[b] = num(v.iat[i, cols[b]]) if b in cols else 0.0
            out.append(rec)
    df = pd.DataFrame(out).drop_duplicates("size")
    assert set(SIZES.values()) <= set(df["size"]), (path.name, list(df["size"]))
    return df


if __name__ == "__main__":
    rate = pd.concat([parse_rate(p, int(re.search(r"(\d{4})", p.name).group(1))) for p in sorted(RAW.glob("leave_rate_*"))], ignore_index=True)
    rate.to_csv(OUT / "leave_rate.csv", index=False, float_format="%.3f")
    per = pd.concat([parse_period(p, int(re.search(r"(\d{4})", p.name).group(1))) for p in sorted(RAW.glob("leave_period_*"))], ignore_index=True)
    per.to_csv(OUT / "leave_period_male.csv", index=False, float_format="%.3f")
    print(rate.pivot_table(index="year", columns="size", values="male").round(2))
    print(per[per["size"] == "総数"].round(1).to_string())
