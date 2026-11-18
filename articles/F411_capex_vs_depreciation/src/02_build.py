"""法人企業統計（四半期別）の時系列 Excel から、使う項目を四半期の縦長 CSV と年度の CSV にする。"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "mof_ssc_quarterly_all.xls"
OUT = ROOT / "data"
SHEETS = {"20": "dep", "60": "capex_sw", "61": "software", "62": "capex_exsw", "14": "tangible_exland", "15": "cip"}
INDS = ["all", "mfg", "nonmfg", "all_incl_fin", "fin"]
SIZES = ["A", "B", "C", "D"]
MON = {"Apr.～Jun.": 1, "Jul.～Sep.": 2, "Oct.～Dec.": 3, "Jan.～Mar.": 4}


def read_sheet(sheet, item):
    d = pd.read_excel(RAW, sheet, header=None)
    rows = []
    for _, r in d.iloc[4:].iterrows():
        lab = str(r[0]).strip()
        if not lab[:4].isdigit():
            continue
        cy, q = int(lab[:4]), MON[lab[5:].strip()]
        fy = cy if q in (1, 2, 3) else cy - 1  # 年度（4〜3月）
        ncol = d.shape[1] - 1
        for j in range(ncol):
            ind, size = INDS[j // 4], SIZES[j % 4]
            v = pd.to_numeric(r[j + 1], errors="coerce")
            if pd.isna(v):
                continue
            rows.append((lab, fy, q, ind, size, item, float(v)))
    return rows


def main():
    rows = []
    for s, item in SHEETS.items():
        rows += read_sheet(s, item)
    q = pd.DataFrame(rows, columns=["label", "fy", "fq", "ind", "size", "item", "oku_yen"])
    q = q.sort_values(["item", "ind", "size", "fy", "fq"]).reset_index(drop=True)
    q.to_csv(OUT / "quarterly_long.csv", index=False)

    flow = q[q["item"].isin(["dep", "capex_sw", "software", "capex_exsw"])]
    g = flow.groupby(["item", "ind", "size", "fy"], sort=True)["oku_yen"].agg(["sum", "count"]).reset_index()
    g = g[g["count"] == 4].drop(columns="count").rename(columns={"sum": "oku_yen"})
    fyw = g.pivot_table(index=["ind", "size", "fy"], columns="item", values="oku_yen").reset_index()
    # 年度末（1-3月期）の残高
    stock = q[q["item"].isin(["tangible_exland", "cip"]) & (q["fq"] == 4)]
    st = stock.pivot_table(index=["ind", "size", "fy"], columns="item", values="oku_yen").reset_index()
    fyw = fyw.merge(st, on=["ind", "size", "fy"], how="left")
    fyw = fyw[fyw["fy"] <= 2025].sort_values(["ind", "size", "fy"]).reset_index(drop=True)
    fyw.to_csv(OUT / "fiscal_year.csv", index=False, float_format="%.2f")
    print(fyw[(fyw["ind"] == "all") & (fyw["size"] == "A")].tail(3))


if __name__ == "__main__":
    main()
