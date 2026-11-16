"""02_build.py : data/raw の Excel（一般労働者 産業計）から、性・学歴・年齢・規模別の所定内給与と労働者数の表 data/general.csv を作る（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
YEARS = range(2006, 2026)
SIZES = ["企業規模計", "1000人以上", "100〜999人", "10〜99人"]
SEXES = ["男女計", "男", "女"]


def norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"\s", "", s)


def num(v):
    if isinstance(v, (int, float)) and not pd.isna(v):
        return float(v)
    s = norm(v)
    try:
        return float(s)
    except ValueError:
        return float("nan")


def rawfile(stem):
    for ext in (".xlsx", ".xls"):
        p = RAW / (stem + ext)
        if p.exists():
            return p
    raise FileNotFoundError(stem)


AGE_RE = re.compile(r"^(〜19歳|\d\d〜\d\d歳|70歳〜)$")


def build_general():
    rows = []
    for y in YEARS:
        xf = pd.ExcelFile(rawfile(f"general_{y}"))
        v = xf.parse("産業計", header=None)
        sex = edu = None
        for i in range(len(v)):
            lab = norm(v.iat[i, 2]).replace("~", "〜").replace("～", "〜")
            m = re.match(r"^(男女計|男|女)(.*)$", lab)
            if m and (m.group(2) == "" or "学歴計" in m.group(2) or m.group(2).endswith("卒") or m.group(2) in ("中学", "高校", "専門学校", "高専・短大", "大学", "大学院")):
                sex = m.group(1)
                edu = m.group(2) or "学歴計"
                age = "年齢計"
            elif lab in ("中学卒", "高校卒", "高専・短大卒", "大学・大学院卒", "中学", "高校", "専門学校", "高専・短大", "大学", "大学院", "不明"):
                edu = lab
                age = "年齢計"
            elif AGE_RE.match(lab):
                age = lab
            else:
                continue
            if sex is None:
                continue
            for k, size in enumerate(SIZES):
                rows.append({"year": y, "sex": sex, "edu": edu, "age": age, "size": size,
                             "wage": num(v.iat[i, 8 + 8 * k]), "workers10": num(v.iat[i, 10 + 8 * k])})
    df = pd.DataFrame(rows)
    dup = df.duplicated(["year", "sex", "edu", "age", "size"]).sum()
    if dup:
        print(df[df.duplicated(["year", "sex", "edu", "age", "size"], keep=False)].head(12))
    assert dup == 0, dup
    df.to_csv(OUT / "general.csv", index=False, float_format="%.1f")
    return df


if __name__ == "__main__":
    b = build_general()
    print(len(b))
