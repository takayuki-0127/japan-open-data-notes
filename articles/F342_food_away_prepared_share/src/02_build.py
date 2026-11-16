"""data/raw から、年×項目の支出金額の表 data/food_spending.csv を作る（オフライン）。"""
import pathlib, io
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ITEMS = ["世帯人員(人)", "年齢(歳)", "有業者比率", "世帯主の年齢(歳)", "消費支出", "食料", "調理食品", "主食的調理食品", "他の調理食品", "外食", "一般外食", "学校給食"]


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def read_csv_table(fname, series, kind):
    txt = (RAW / fname).read_bytes().decode("cp932")
    d = pd.read_csv(io.StringIO(txt), header=None, dtype=str)
    years = [int(str(v).replace("年", "")) for v in d.iloc[1, 6:].tolist() if str(v).endswith("年")]
    rows = []
    for i in range(3, len(d)):
        name = str(d.iat[i, 5]).strip()
        if name in ITEMS:
            for k, y in enumerate(years):
                rows.append(dict(series=series, kind=kind, year=y, item=name, value=num(d.iat[i, 6 + k])))
    out = pd.DataFrame(rows)
    # 同じ名前の行が2つあるとき（例：食料と食料(財・サービス)は名前が違うので起きない）最初の行を使う
    return out.drop_duplicates(["series", "kind", "year", "item"], keep="first")


def read_longterm():
    x = pd.ExcelFile(RAW / "kakei_nonfarm_items_1963_2007.xls")
    spec = {"120-217": {4: "世帯人員(人)", 7: "消費支出", 8: "食料"}, "300-376": {115: "調理食品", 116: "主食的調理食品", 124: "他の調理食品"},
            "380-479": {60: "外食", 61: "一般外食", 76: "学校給食"}}
    rows = []
    for sh, cols in spec.items():
        d = x.parse(sh, header=None)
        for i in range(12, len(d)):
            y = num(d.iat[i, 1])
            if np.isnan(y):
                continue
            for c, name in cols.items():
                rows.append(dict(series="二人以上（農林漁家を除く）1963-2007", kind="名目", year=int(y), item=name, value=num(d.iat[i, c])))
    return pd.DataFrame(rows)


def main():
    parts = [read_csv_table("kakei_two_plus_items_nominal_2000_2025.csv", "二人以上 2000-", "名目"),
             read_csv_table("kakei_two_plus_items_real_growth_2000_2025.csv", "二人以上 2000-", "実質増減率"),
             read_csv_table("kakei_total_households_items_2000_2025.csv", "総世帯 2000-", "名目"),
             read_csv_table("kakei_single_items_2000_2025.csv", "単身 2000-", "名目"),
             read_longterm()]
    out = pd.concat(parts, ignore_index=True).sort_values(["series", "kind", "item", "year"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "food_spending.csv", index=False)
    print(out.groupby(["series", "kind"]).agg(n=("value", "size"), y0=("year", "min"), y1=("year", "max")))


if __name__ == "__main__":
    main()
