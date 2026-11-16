"""02 整形：推移表（年のシート）を縦長に（指標×旅行の種類×目的×年）"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
KIND = {"国内旅行（全体）": "全体", "国内旅行（宿泊旅行）": "宿泊", "国内旅行（日帰り旅行）": "日帰り", "国内旅行": "国内", "海外旅行": "海外"}
PURP = {None: "計", "観光・レクリエーション": "観光", "帰省・知人訪問等": "帰省", "出張・業務": "出張"}


def main():
    ws = openpyxl.load_workbook(str(RAW / "suii_002028738.xlsx"), read_only=True, data_only=True)["年"]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    cols, c3, c4 = {}, None, None
    for j in range(3, len(rows[3])):
        a, b, c = rows[3][j], rows[4][j], rows[5][j]
        if a:
            c3, c4 = a.strip(), None
        if b:
            c4 = b.strip()
        p = re.sub(r"\s+", "", c) if c else None
        cols[j] = (c3, KIND[c4], PURP[p])
    out = []
    for r in rows[6:]:
        if not r[2] or not re.match(r"^\d{4}年$", str(r[2]).strip()):
            continue
        y = int(str(r[2])[:4])
        for j, (ind, kind, purp) in cols.items():
            v = r[j]
            if isinstance(v, (int, float)):
                out.append((y, ind, kind, purp, float(v)))
    d = pd.DataFrame(out, columns=["year", "indicator", "kind", "purpose", "value"])
    d.to_csv(ROOT / "data" / "series.csv", index=False)
    print(d.year.min(), d.year.max(), len(d))
    print(d[(d.year.isin([2010, 2019, 2025])) & (d.purpose == "計")].pivot_table(index=["indicator", "kind"], columns="year", values="value").round(2))


if __name__ == "__main__":
    main()
