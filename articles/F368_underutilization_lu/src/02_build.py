"""02_build.py : 年報の「年齢階級別未活用労働指標」（2019〜2025年版）と、LU1 の長期時系列（月次）を CSV にする（オフライン）。"""
import pathlib
import re
import unicodedata
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
KEYS = {"LU1": "未活用労働指標1", "LU2": "未活用労働指標2", "LU3": "未活用労働指標3", "LU4": "未活用労働指標4",
        "AUX1": "未活用労働補助指標1", "AUX2": "未活用労働補助指標2"}
AGES = ["15～24歳", "25～34歳", "35～44歳", "45～54歳", "55～64歳", "65歳以上"]


def n(s):
    return "" if pd.isna(s) else re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s))).replace("~", "～")


def parse(path, version):
    v = pd.read_excel(path, header=None)
    hr = next(i for i in range(0, 6) if any(n(v.iat[i, j]).startswith("未活用労働指標1") for j in range(v.shape[1])))
    cols = {}
    for k, key in KEYS.items():
        cols[k] = next(j for j in range(v.shape[1]) if n(v.iat[hr, j]).startswith(key) and not (k.startswith("LU") and "補助" in n(v.iat[hr, j])))
    rows = []
    sex = None
    year = None
    for i in range(hr + 1, len(v)):
        cells = [n(v.iat[i, j]) for j in range(0, min(cols.values()))]
        if any("対前年" in c for c in cells):
            break
        for c in cells:
            if c in ("男女計", "男", "女"):
                sex = c
        ym = next((re.match(r"^(\d{4})", c) for c in cells if re.match(r"^\d{4}", c)), None)
        age = next((c for c in cells if c in AGES), None)
        if ym:
            year = int(ym.group(1))
            label = "年齢計"
        elif age:
            label = age.replace("～", "〜")
        else:
            continue
        if sex is None:
            continue
        rec = {"version": version, "sex": sex, "year": year, "age": label}
        for k, j in cols.items():
            try:
                rec[k] = float(n(v.iat[i, j]))
            except ValueError:
                rec[k] = float("nan")
        rows.append(rec)
    df = pd.DataFrame(rows)
    assert set(df.sex) == {"男女計", "男", "女"}, (path.name, set(df.sex))
    return df


def build_monthly():
    v = pd.read_excel(RAW / "lu1_monthly_longterm.xlsx", sheet_name="季節調整値", header=None)
    assert "未活用労働指標" in n(v.iat[5, 7]) and n(v.iat[7, 7]) == "男女計"
    rows = []
    y = None
    for i in range(10, len(v)):
        a = n(v.iat[i, 0])
        m = re.match(r"^(\d{4})", a)
        if m:
            y = int(m.group(1))
        elif re.match(r"^(平成|令和)(\d+|元)年", a):
            g = re.match(r"^(平成|令和)(\d+|元)年", a)
            k = 1 if g.group(2) == "元" else int(g.group(2))
            y = (1988 if g.group(1) == "平成" else 2018) + k
        mm = re.match(r"^(\d+)月$", n(v.iat[i, 1]))
        if y and mm:
            try:
                val = float(n(v.iat[i, 7]))
            except ValueError:
                continue
            rows.append({"year": y, "month": int(mm.group(1)), "LU1_sa": val, "unemployed_sa_10k": float(n(v.iat[i, 4]))})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parts = [parse(p, int(re.search(r"(\d{4})", p.name).group(1))) for p in sorted(RAW.glob("lu_annual_*"))]
    allv = pd.concat(parts, ignore_index=True)
    allv.to_csv(OUT / "lu_annual_all_versions.csv", index=False, float_format="%.2f")
    use = allv.sort_values("version").drop_duplicates(["sex", "year", "age"], keep="last").sort_values(["sex", "age", "year"])
    use.to_csv(OUT / "lu_annual.csv", index=False, float_format="%.2f")
    mo = build_monthly()
    mo.to_csv(OUT / "lu1_monthly.csv", index=False, float_format="%.2f")
    print(use[use.age == "年齢計"].pivot_table(index="year", columns="sex", values=["LU1", "LU4"]))
    print(use[use.age != "年齢計"].groupby("year").size())
    print(mo.head(2), mo.tail(2), len(mo))
