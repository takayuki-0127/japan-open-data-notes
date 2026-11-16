"""data/raw の CSV（Shift_JIS）から、年×区分×相手の国籍の婚姻件数（data/marriage_nationality.csv）を作る。"""
import csv, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
NAT = ["総数", "韓国・朝鮮", "中国", "フィリピン", "タイ", "米国", "英国", "ブラジル", "ペルー", "その他の国"]


def num(s):
    s = str(s).strip().replace(" ", "")
    return pd.to_numeric(s, errors="coerce")  # 「…」は欠測


def main():
    rows = []
    with open(RAW / "vs2025_t9_18_marriage_nationality.csv", encoding="cp932", newline="") as f:
        for r in csv.reader(f):
            y = r[0].strip().replace("　", "") if r else ""
            if not y.isdigit():
                continue
            y = int(y)
            rows.append(dict(year=y, group="総数", nationality="総数", n=num(r[1])))
            rows.append(dict(year=y, group="夫妻とも日本", nationality="総数", n=num(r[2])))
            rows.append(dict(year=y, group="夫妻の一方が外国", nationality="総数", n=num(r[3])))
            for k, nat in enumerate(NAT):
                rows.append(dict(year=y, group="夫日本・妻外国", nationality=nat, n=num(r[4 + k])))
                rows.append(dict(year=y, group="妻日本・夫外国", nationality=nat, n=num(r[14 + k])))
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "marriage_nationality.csv", index=False)
    print(df.year.min(), df.year.max(), df.year.nunique())


if __name__ == "__main__":
    main()
