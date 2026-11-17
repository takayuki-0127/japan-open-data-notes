"""02_build.py : 労働力調査（詳細集計）長期時系列の雇用形態別雇用者数を、年・男女・年齢ごとの長い形にする（オフライン）。"""
import pathlib
import re
import unicodedata
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
ITEMS = ["就業者", "雇用者", "役員を除く雇用者", "正規", "非正規", "パート・アルバイト", "パート", "アルバイト", "派遣社員", "契約社員", "嘱託", "その他"]
AGES = [("総数", 2), ("15〜24歳", 16), ("15〜24歳（在学中を除く）", 30), ("25〜34歳", 44), ("35〜44歳", 58), ("45〜54歳", 72), ("55〜64歳", 86), ("65歳以上", 100)]


def n(s):
    return "" if pd.isna(s) else re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    s = n(x)
    try:
        return float(s)
    except ValueError:
        return float("nan")


def check_header(v):
    assert "労働者派遣事業所の派遣社員" in n(v.iat[12, 10]), n(v.iat[12, 10])
    for lab, c in AGES[1:]:
        h = n(v.iat[6, c])
        key = lab.split("（")[0].replace("〜", "~")
        assert key in h, (lab, h)
        assert "派遣社員" in " ".join(n(v.iat[i, c + 8]) for i in range(6, 14)), (lab,)


def annual():
    xf = pd.ExcelFile(RAW / "lfs_detail_10_1_annual.xlsx")
    rows = []
    for sex in ["男女計", "男", "女"]:
        v = xf.parse(sex, header=None)
        check_header(v)
        for i in range(15, len(v)):
            m = re.match(r"^(\d{4})", n(v.iat[i, 1]))
            if not m:
                continue
            y = int(m.group(1))
            for lab, c in AGES:
                rec = {"year": y, "sex": sex, "age": lab}
                for k, it in enumerate(ITEMS):
                    rec[it] = num(v.iat[i, c + k])
                rows.append(rec)
    return pd.DataFrame(rows)


def published():
    v = pd.read_excel(RAW / "lfs_detail_10_1_annual.xlsx", sheet_name="男女計 (既公表値)", header=None)
    rows = []
    for i in range(15, len(v)):
        m = re.match(r"^(\d{4})", n(v.iat[i, 1]))
        if m:
            rows.append({"year": int(m.group(1)), "派遣社員_既公表": num(v.iat[i, 10]), "非正規_既公表": num(v.iat[i, 6])})
    return pd.DataFrame(rows)


def quarterly():
    v = pd.read_excel(RAW / "lfs_detail_9_1_quarterly.xlsx", sheet_name="男女計", header=None)
    assert "Dispat" in n(v.iat[12, 11]) or "派遣" in " ".join(n(v.iat[i, 11]) for i in range(6, 13))
    rows = []
    for i in range(14, len(v)):
        m = re.match(r"^(\d{4})(Jan|Apr|Jul|Oct)", n(v.iat[i, 2]))
        if m:
            q = {"Jan": 1, "Apr": 2, "Jul": 3, "Oct": 4}[m.group(2)]
            rows.append({"year": int(m.group(1)), "q": q, "非正規": num(v.iat[i, 7]), "派遣社員": num(v.iat[i, 11])})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    a = annual()
    a.to_csv(OUT / "employment_type_annual.csv", index=False, float_format="%.0f")
    published().to_csv(OUT / "published_annual.csv", index=False, float_format="%.0f")
    q = quarterly()
    q.to_csv(OUT / "dispatched_quarterly.csv", index=False, float_format="%.0f")
    print(a[(a.age == "総数")].pivot_table(index="year", columns="sex", values="派遣社員").T)
    print(q.head(3), q.tail(3), len(q))
