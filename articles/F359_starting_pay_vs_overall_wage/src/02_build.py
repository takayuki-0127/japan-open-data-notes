"""02_build.py : data/raw の Excel から、分析に使う表（CSV）を data/ に作る（オフライン）。"""
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


def build_newgrad():
    rows = []
    for y in YEARS:
        xf = pd.ExcelFile(rawfile(f"newgrad_{y}"))
        for sh in xf.sheet_names:
            edu = norm(sh)
            if edu in ("学歴計", "中学"):
                continue
            v = xf.parse(sh, header=None)
            hit = [i for i in range(len(v)) if "産業計" in norm(v.iat[i, 1]) + norm(v.iat[i, 2])]
            assert len(hit) == 3, (y, sh, hit)
            for sex, i in zip(SEXES, hit):
                for k, size in enumerate(SIZES):
                    rows.append({"year": y, "edu": edu, "sex": sex, "size": size,
                                 "wage": num(v.iat[i, 3 + 2 * k]), "workers10": num(v.iat[i, 4 + 2 * k])})
    df = pd.DataFrame(rows)
    # 男女計は男と女の間にあるはず（並びの確かめ）
    p = df[df["size"] == "企業規模計"].pivot_table(index=["year", "edu"], columns="sex", values="wage")
    assert ((p["男女計"] <= p[["男", "女"]].max(axis=1) + 1e-9) & (p["男女計"] >= p[["男", "女"]].min(axis=1) - 1e-9)).all()
    df.to_csv(OUT / "newgrad.csv", index=False, float_format="%.1f")
    return df


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


def build_old():
    v = pd.read_excel(rawfile("old_ts_starting_pay"), sheet_name=0, header=None)
    cols = {"男": {"大学院": 1, "大学": 3, "高専・短大": 5, "高校": 7},
            "女": {"大学院": 9, "大学": 11, "高専・短大": 13, "高校": 15}}
    rows = []
    for j, i in enumerate(range(7, 51)):
        y = 1976 + j
        for sex, d in cols.items():
            for edu, c in d.items():
                rows.append({"year": y, "sex": sex, "edu": edu, "wage": num(v.iat[i, c]),
                             "pct_table": num(v.iat[i, c + 1])})
    df = pd.DataFrame(rows)
    assert norm(v.iat[50, 0]) == "令和元年"
    df.to_csv(OUT / "old_ts_starting_pay.csv", index=False, float_format="%.1f")
    return df


if __name__ == "__main__":
    a = build_newgrad()
    b = build_general()
    c = build_old()
    print(len(a), len(b), len(c))
    print(b[(b["sex"] == "男女計") & (b["age"] == "年齢計") & (b["size"] == "企業規模計")].groupby("edu").size())
