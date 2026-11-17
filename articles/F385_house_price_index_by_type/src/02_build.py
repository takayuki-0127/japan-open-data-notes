"""02 整形：Excel・CSV → data/rppi_monthly.csv、data/transactions_monthly.csv、data/cpi_monthly.csv（オフライン）。"""
import csv, pathlib, re
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
AREAS = ["全国", "北海道地方", "東北地方", "関東地方", "北陸地方", "中部地方", "近畿地方", "中国地方", "四国地方",
         "九州・沖縄地方", "南関東圏", "名古屋圏", "京阪神圏", "東京都", "愛知県", "大阪府"]
TYPES = ["住宅総合", "住宅地", "戸建住宅", "マンション"]


def area_of(sheet):
    for a in AREAS:
        if sheet.startswith(a):
            return a
    return None


def build_index():
    wb = openpyxl.load_workbook(RAW / "rppi_residential_001473668.xlsx", read_only=True, data_only=True)
    out = []
    for sh in wb.sheetnames:
        a = area_of(sh)
        if a is None:
            continue
        kind = "sa" if sh.endswith("季節調整") else "orig"
        for r in wb[sh].iter_rows(min_row=10, values_only=True):
            if not hasattr(r[0], "year"):
                continue
            for k, t in enumerate(TYPES):
                v, n = r[1 + 3 * k], r[3 + 3 * k]
                if isinstance(v, (int, float)):
                    out.append((a, kind, f"{r[0].year}-{r[0].month:02d}", t, round(float(v), 6), n))
    df = pd.DataFrame(out, columns=["area", "series", "month", "type", "index", "n"])
    df["area"] = pd.Categorical(df["area"], AREAS, ordered=True)
    df = df.sort_values(["series", "area", "type", "month"]).reset_index(drop=True)
    df.to_csv(DATA / "rppi_monthly.csv", index=False)
    return df


def build_tx():
    wb = openpyxl.load_workbook(RAW / "transactions_001465569.xlsx", read_only=True, data_only=True)
    out = []
    for sh in wb.sheetnames:
        a = area_of(sh)
        if a is None:
            continue
        for r in wb[sh].iter_rows(min_row=11, values_only=True):
            if not hasattr(r[0], "year"):
                continue
            for col, t in [(1, "戸建住宅"), (15, "マンション")]:
                if isinstance(r[col], (int, float)):
                    out.append((a, f"{r[0].year}-{r[0].month:02d}", t, int(r[col])))
    df = pd.DataFrame(out, columns=["area", "month", "type", "count"])
    df["area"] = pd.Categorical(df["area"], AREAS, ordered=True)
    df = df.sort_values(["area", "type", "month"]).reset_index(drop=True)
    df.to_csv(DATA / "transactions_monthly.csv", index=False)
    return df


def build_cpi():
    rows = list(csv.reader(open(RAW / "cpi_middle_class_index.csv", encoding="cp932")))
    assert rows[0][1] == "総合"
    out = [(f"{r[0][:4]}-{r[0][4:6]}", float(r[1])) for r in rows if re.fullmatch(r"\d{6}", r[0] or "") and r[1]]
    df = pd.DataFrame(out, columns=["month", "cpi"])
    df = df[(df.month >= "2008-01") & (df.month <= "2025-12")]
    df.to_csv(DATA / "cpi_monthly.csv", index=False)
    return df


if __name__ == "__main__":
    a, b, c = build_index(), build_tx(), build_cpi()
    print(len(a), len(b), len(c), a.month.min(), a.month.max(), b.month.max())
