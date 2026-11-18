"""02_build.py：財務省の時系列 Excel から、使う項目だけを縦長の CSV にする。
シートは番号ではなく、左上の項目名（英語）で探す。業種と規模は見出しの行の文字で付ける。"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "mof_ssc_quarterly_all.xls"
OUT = ROOT / "data" / "quarterly_long.csv"

ITEMS = {  # 左上の項目名 → 短い名前
    "sales": "sales",
    "ordinary profits": "ordinary_profit",
    "investment in plant and equipment": "capex",
    "investment in plant and equipment excluding software": "capex_ex_sw",
    "number of employees": "employees",
    "capital stock": "capital",
    "capital stock at the end of previous period": "capital_prev_end",
    "number of corporations": "corporations",
}
IND = {"All Industries(except Finance and Insurance)": "all_ex_fin",
       "Manufacturing": "manufacturing", "Non-Manufacturing": "non_manufacturing"}
MON = {"Apr.": 2, "Jul.": 3, "Oct.": 4, "Jan.": 1}  # 暦の四半期（4〜6月期＝2）


def main():
    x = pd.ExcelFile(RAW)
    rows, found = [], {}
    for s in x.sheet_names:
        d = pd.read_excel(x, s, header=None, dtype=object)
        name = str(d.iloc[0, 0]).strip()
        if name not in ITEMS:
            continue
        found[ITEMS[name]] = s
        ind = d.iloc[2].ffill()
        size = d.iloc[3]
        for i in range(4, len(d)):
            lab = d.iloc[i, 0]
            if not isinstance(lab, str):
                continue
            m = re.match(r"\s*(\d{4})\s+(\w+\.)", lab)
            if not m:
                continue
            y, q = int(m.group(1)), MON[m.group(2)]
            for j in range(1, d.shape[1]):
                if ind[j] not in IND or size[j] not in ("A", "B", "C", "D"):
                    continue
                v = pd.to_numeric(d.iloc[i, j], errors="coerce")
                if pd.isna(v):
                    continue
                rows.append((ITEMS[name], IND[ind[j]], size[j], y, q, float(v)))
    assert len(found) == len(ITEMS), found
    df = pd.DataFrame(rows, columns=["item", "industry", "size", "year", "q", "value"])
    df = df.sort_values(["item", "industry", "size", "year", "q"]).reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print("rows", len(df), "sheets", found)


if __name__ == "__main__":
    main()
