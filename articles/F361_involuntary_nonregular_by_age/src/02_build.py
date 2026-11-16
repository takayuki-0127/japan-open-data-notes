"""02_build.py : 労働力調査の理由別の表と有効求人倍率を、分析用の CSV にする（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
REASONS = ["都合のよい時間", "家計の補助・学費", "家事・育児等と両立", "通勤時間が短い", "専門的な技能", "正規の仕事がない", "その他"]
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]
SEX_COL = {"男女計": 6, "男": 29, "女": 52}


def norm(s):
    if pd.isna(s):
        return ""
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def parse(path, version):
    eng = "xlrd" if path.suffix == ".xls" else None
    v = pd.read_excel(path, header=None, engine=eng)
    rows = []
    age = None
    for i in range(8, 43):  # 実数の行（7区分 × 5年）
        a = norm(v.iat[i, 3])
        if a:
            age = "年齢計" if a == "総数" else a.replace("~", "〜")
        y = int(re.match(r"(\d{4})", norm(v.iat[i, 5])).group(1)) if re.match(r"\d{4}", norm(v.iat[i, 5])) else None
        if y is None:
            y = prev + 1
        prev = y
        for sex, c in SEX_COL.items():
            rec = {"version": version, "year": y, "sex": sex, "age": age, "total": float(v.iat[i, c])}
            for k, rname in enumerate(REASONS):
                rec[rname] = float(v.iat[i, c + 1 + k])
            rows.append(rec)
    df = pd.DataFrame(rows)
    assert set(df.age) == set(["年齢計"] + AGES), set(df.age)
    assert df.groupby(["sex", "age"]).size().eq(5).all()
    return df


def header_check(path):
    """理由の並び（7列）と男女の区分が想定どおりかを確かめる。"""
    eng = "xlrd" if path.suffix == ".xls" else None
    v = pd.read_excel(path, header=None, engine=eng)
    keys = ["都合のよい時間", "家計の補助", "家事・育児", "通勤時間", "専門的な技能", "正規の職員・従業員の仕事がない", "その他"]
    for sex, c in SEX_COL.items():
        hdr = " ".join(norm(x) for x in v.iloc[0:8, c:c + 8].astype(str).values.ravel())
        for k, key in enumerate(keys):
            lab = " ".join(norm(v.iat[r, c + 1 + k]) for r in range(0, 8))
            assert key in lab, (path.name, sex, key, lab)
        assert norm(v.iat[8, c - 5]) == sex, (path.name, sex, norm(v.iat[8, c - 5]))
        del hdr


def build_reason():
    parts = []
    for stem, ver in [("lfs_reason_2013_2017", 2017), ("lfs_reason_2018_2022", 2022), ("lfs_reason_2021_2025", 2025)]:
        p = next(RAW.glob(stem + ".xls*"))
        header_check(p)
        parts.append(parse(p, ver))
    allv = pd.concat(parts, ignore_index=True)
    allv.to_csv(OUT / "reason_all_versions.csv", index=False, float_format="%.0f")
    # 年ごとに新しい版を使う
    use = allv.sort_values("version").drop_duplicates(["year", "sex", "age"], keep="last")
    use = use.sort_values(["sex", "age", "year"]).drop(columns="version")
    use.to_csv(OUT / "reason.csv", index=False, float_format="%.0f")
    return use


def build_jr():
    p = next(RAW.glob("jobs_to_applicants_ratio_longterm.xls*"))
    v = pd.read_excel(p, header=None, sheet_name=0)
    assert norm(v.iat[3, 18]) == "年平均" and norm(v.iat[2, 18]) == "実数"
    rows = []
    for i in range(5, len(v)):
        m = re.match(r"(\d{4})年", norm(v.iat[i, 0]))
        if m and pd.notna(v.iat[i, 18]):
            rows.append({"year": int(m.group(1)), "jobs_ratio": float(v.iat[i, 18])})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "jobs_ratio_annual.csv", index=False)
    return df


if __name__ == "__main__":
    r = build_reason()
    j = build_jr()
    print(r.year.min(), r.year.max(), len(r), j.tail(3).to_dict("records"))
