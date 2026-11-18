"""data/raw の元ファイルから、分析に使う CSV を作る（オフライン）。"""
import csv, io, pathlib, re
import numpy as np
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
# 季調・月次シートの列（0始まり）。見出しの文字で確かめる
COLS = {"core": 9, "mfg": 10, "nonmfg_core": 13, "sales_exship": 20, "backlog_exship": 22}


def read_orders(sheet):
    wb = openpyxl.load_workbook(RAW / "juchu_chouki1_2608.xlsx", read_only=True, data_only=True)
    rows = list(wb[sheet].iter_rows(values_only=True))
    h1, h2 = rows[3], rows[4]
    assert "民" in str(h1[7]) and "船舶・電力" in str(h2[9]) and "製" in str(h1[10]) and "船舶・電力" in str(h2[13])
    assert "販売額" in str(h1[19]) and "受注残高" in str(h1[21])
    out, year = [], None
    for r in rows[9:]:
        if isinstance(r[1], int) or (isinstance(r[1], str) and r[1].strip().isdigit()):
            year = int(r[1])  # 2011年以降は年が文字で入っている
        if year is not None and r[2] is not None and isinstance(r[3], (int, float)):
            rec = {"year": year, "per": str(r[2])}
            for k, j in COLS.items():
                rec[k] = float(r[j]) if isinstance(r[j], (int, float)) else np.nan
            out.append(rec)
    return pd.DataFrame(out)


def read_qe(name, col_label):
    rows = list(csv.reader(io.open(RAW / name, encoding="cp932")))
    head = rows[2]
    j = head.index(col_label)
    out, year = [], None
    for r in rows:
        m = re.match(r"\s*(?:(\d{4})/)?\s*(\d+)-\s*(\d+)\.", r[0] or "")
        if not m:
            continue
        if m.group(1):
            year = int(m.group(1))
        q = (int(m.group(2)) - 1) // 3 + 1
        v = (r[j] or "").replace(",", "").strip()
        out.append({"year": year, "q": q, "value": float(v) if v else np.nan})
        if len(out) > 1 and out[-1]["year"] == out[-2]["year"] and out[-1]["q"] <= out[-2]["q"]:
            out.pop(); break  # 2つめの表（前期比など）に入ったら止める
    return pd.DataFrame(out)


def main():
    mo = read_orders("季調・月次")
    mo["month"] = mo["per"].astype(int)
    mo["ym"] = mo["year"] * 100 + mo["month"]
    mo[["ym", "year", "month", "core", "mfg", "nonmfg_core", "sales_exship", "backlog_exship"]].to_csv(D / "orders_monthly_sa.csv", index=False)
    qo = read_orders("季調・四半期")
    qo["q"] = qo["per"].map({"1-3": 1, "4-6": 2, "7-9": 3, "10-12": 4})
    qo = qo.dropna(subset=["q"])
    qo["q"] = qo["q"].astype(int)
    qo[["year", "q", "core", "mfg", "nonmfg_core", "sales_exship", "backlog_exship"]].to_csv(D / "orders_quarterly_sa.csv", index=False)
    lab = "民間企業設備"
    n = read_qe("qe_nominal_sa_2631.csv", lab).rename(columns={"value": "capex_nominal"})
    r = read_qe("qe_real_sa_2631.csv", lab).rename(columns={"value": "capex_real"})
    d = read_qe("qe_deflator_sa_2631.csv", lab).rename(columns={"value": "capex_deflator"})
    qe = n.merge(r, on=["year", "q"]).merge(d, on=["year", "q"])
    qe.to_csv(D / "capex_quarterly_sa.csv", index=False)
    print(len(mo), len(qo), len(qe), qe.tail(2).to_dict("records"), qo.tail(2).to_dict("records"))


if __name__ == "__main__":
    main()
