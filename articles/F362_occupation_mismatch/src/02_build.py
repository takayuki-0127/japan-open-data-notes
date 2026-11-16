"""02_build.py : 職業別の求人・求職（年度の月平均）を長い形の CSV にする（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
SHEETS = {0: "新規求人_パート含む", 1: "有効求人_パート含む", 2: "新規求職_パート含む", 3: "有効求職_パート含む",
          8: "有効求人_パート除く", 10: "有効求職_パート除く"}
MAJOR_ROWS = [6, 7, 20, 28, 32, 41, 42, 43, 55, 61, 67]
MAJOR_NAME = ["管理", "専門・技術", "事務", "販売", "サービス", "保安", "農林漁業", "生産工程", "輸送・機械運転", "建設・採掘", "運搬・清掃・包装等"]
NO_SUB = {6, 41, 42}  # 中分類がない大分類（大分類をそのまま中分類として使う）


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def parse(path, era):
    xf = pd.ExcelFile(path)
    rows = []
    for k, key in SHEETS.items():
        sn = xf.sheet_names[k]
        kind = key.split("_")
        assert kind[0] in norm(sn) and ("パート含む" if kind[1] == "パート含む" else "パート除く") in norm(sn), (sn, key)
        v = xf.parse(sn, header=None)
        assert norm(v.iat[5, 0]) == "職業計" and norm(v.iat[72, 0]) == "分類不能の職業"
        fy_cols = {int(m.group(1)): j for j in range(v.shape[1]) if (m := re.match(r"^(\d{4})年度$", norm(v.iat[1, j])))}
        major_of = None
        for i in range(5, 73):
            lab = norm(v.iat[i, 0])
            if i == 5:
                level = "total"
            elif i == 72:
                level = "unclassified"
            elif i in MAJOR_ROWS:
                level = "major"
                major_of = MAJOR_NAME[MAJOR_ROWS.index(i)]
            else:
                level = "sub"
            for fy, j in fy_cols.items():
                rows.append({"era": era, "series": key, "fy": fy, "row": i, "label": lab, "level": level,
                             "major": major_of if level in ("major", "sub") else "", "value": float(v.iat[i, j])})
    df = pd.DataFrame(rows)
    # 大分類の名前の確かめ
    for i, nm in zip(MAJOR_ROWS, MAJOR_NAME):
        lab = df[(df.row == i)].label.iloc[0]
        key = {"管理": "管理", "専門・技術": "専門的・技術的", "事務": "事務", "販売": "販売", "サービス": "サービス", "保安": "保安",
               "農林漁業": "農林漁業", "生産工程": "生産工程", "輸送・機械運転": "輸送・機械運転", "建設・採掘": "建設・採掘",
               "運搬・清掃・包装等": "運搬・清掃・包装"}[nm]
        assert key in lab, (era, i, lab)
    return df


if __name__ == "__main__":
    a = parse(next(RAW.glob("occupation_h23_*.xls*")), "H23分類")
    b = parse(next(RAW.glob("occupation_r4_*.xls*")), "R4分類")
    df = pd.concat([a, b], ignore_index=True)
    # 中分類の合計が大分類に一致するか（有効求人・有効求職、パート含む）
    chk = df[(df.level.isin(["sub"])) & df.series.str.startswith("有効")].groupby(["era", "series", "fy", "major"]).value.sum()
    maj = df[(df.level == "major")].set_index(["era", "series", "fy", "major"]).value
    d = (chk - maj.reindex(chk.index)).abs().max()
    print("sub-major max diff", d)
    df.to_csv(OUT / "occupation_fy.csv", index=False, float_format="%.0f")
    print(df.groupby(["era"]).fy.agg(["min", "max"]))
