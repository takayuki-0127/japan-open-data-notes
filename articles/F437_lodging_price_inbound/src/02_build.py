"""02 整形：消費者物価指数（全国・東京都区部）の宿泊料と総合、JNTO の訪日外客数を月次の表にする。
出力：data/monthly.csv（ym, lodging_z, all_z, lodging_t, all_t, visitors）
"""
import pathlib
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"


def cpi(path, tag):
    d = pd.read_csv(path, encoding="cp932", header=None, low_memory=False)
    code = d.iloc[2]
    j_lodge = [j for j in range(d.shape[1]) if str(code[j]).strip() == "0139"][0]
    j_all = [j for j in range(d.shape[1]) if str(code[j]).strip() == "0001"][0]
    body = d.iloc[6:, [0, j_lodge, j_all]].copy()
    body.columns = ["ym", f"lodging_{tag}", f"all_{tag}"]
    body = body[body.ym.astype(str).str.fullmatch(r"\d{6}")]
    body["ym"] = body.ym.astype(int)
    for c in body.columns[1:]:
        body[c] = pd.to_numeric(body[c], errors="coerce")
    return body.set_index("ym")


def visitors():
    wb = openpyxl.load_workbook(RAW / "jnto_visitors_2003_2026.xlsx", read_only=True, data_only=True)
    rows = []
    for sh in wb.sheetnames:
        y = int(sh)
        hdr = None
        for r in wb[sh].iter_rows(values_only=True):
            if "1月" in r[:3]:
                hdr = r
            elif hdr is not None and r[0] == "総数":
                for j, h in enumerate(hdr):
                    if isinstance(h, str) and h.endswith("月") and h[:-1].isdigit() and isinstance(r[j], (int, float)):
                        rows.append((y * 100 + int(h[:-1]), int(r[j])))
                break
    return pd.Series(dict(sorted(rows)), name="visitors")


def main():
    m = cpi(RAW / "cpi_zenkoku_item_monthly.csv", "z").join(cpi(RAW / "cpi_kubu_item_monthly.csv", "t"), how="outer").join(visitors(), how="left")
    m.index.name = "ym"
    m.to_csv(D / "monthly.csv")
    print(m.loc[201901:].tail(14).to_string()); print(m.visitors.dropna().index.min(), m.visitors.dropna().index.max())


if __name__ == "__main__":
    main()
