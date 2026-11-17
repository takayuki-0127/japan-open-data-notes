"""data/raw から分析に使う表を data/ に作る（オフライン）。"""
import pathlib, re
import numpy as np
import pandas as pd
import openpyxl
import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"
ITEMS = ["total", "clothes", "mens", "womens", "other_clothes", "accessories", "food", "others",
         "furniture", "appliances", "household", "other_goods", "restaurant"]


def num(x):
    if x is None or x == "":
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def dept_monthly():
    wb = openpyxl.load_workbook(RAW / "meti_dept_super_timeseries.xlsx", read_only=True, data_only=True)
    ws = wb["百貨店　販売額　月次"]
    rec = []
    for r in ws.iter_rows(min_row=11, values_only=True):
        code = r[0]
        if code is None or not str(code).strip().isdigit():
            continue
        c = str(code).strip()
        rec.append([int(c[:4]), int(c[6:8])] + [num(v) for v in r[2:15]])
    df = pd.DataFrame(rec, columns=["year", "month"] + ITEMS).dropna(subset=["total"])
    # リンク係数（注2）：百貨店の欄を読み、記録する
    rows = [list(r) for r in wb["注2"].iter_rows(values_only=True)]
    links = []
    for r in rows:
        if r[2] is not None and isinstance(r[2], (int, float)) and r[15] is not None and str(r[15]).isdigit():
            ym = str(r[15])
            links.append({"link_month": f"{ym[:4]}-{ym[6:8]}", "dept_total": num(r[7]), "dept_clothes": num(r[8]),
                          "dept_food": num(r[9]), "dept_others": num(r[10])})
    pd.DataFrame(links).to_csv(OUT / "dept_link_coefficients.csv", index=False)
    return df.sort_values(["year", "month"]).reset_index(drop=True)


def jnto():
    wb = openpyxl.load_workbook(RAW / "jnto_visitors_2003_2026.xlsx", read_only=True, data_only=True)
    rows = []
    for sh in wb.sheetnames:
        y = int(sh)
        hdr = None
        got = {}
        for r in wb[sh].iter_rows(values_only=True):
            if "1月" in r[:3]:
                hdr = r
            elif hdr is not None and r[0] in ("総数", "中国") and r[0] not in got:
                got[r[0]] = r
        for j, h in enumerate(hdr):
            if isinstance(h, str) and h.endswith("月") and h[:-1].isdigit():
                tv = got["総数"][j] if "総数" in got else None
                cv = got["中国"][j] if "中国" in got else None
                if isinstance(tv, (int, float)):
                    rows.append({"year": y, "month": int(h[:-1]), "visitors": int(tv),
                                 "visitors_china": int(cv) if isinstance(cv, (int, float)) else np.nan})
    return pd.DataFrame(rows).sort_values(["year", "month"]).reset_index(drop=True)


def kanko():
    out = []
    for y in [2019, 2023, 2024, 2025]:
        b = xlrd.open_workbook(RAW / f"kanko_{y}_annual.xls")
        rec = {"year": y}
        s = b.sheet_by_name("参考2")
        for i in range(s.nrows):
            r = s.row_values(i)
            if r[2] == "買物代":
                rec["shopping_per_person_yen"] = num(r[4]); break
        s = b.sheet_by_name("表5-1")
        for i in range(s.nrows):
            r = s.row_values(i)
            lab = str(r[1])
            if lab.startswith("消費税免税手続きをした回") and "taxfree_rate_pct" not in rec:
                rec["taxfree_rate_pct"] = num(r[5])
            if lab.startswith("手続きをした人の免税物品") and "taxfree_per_buyer_yen" not in rec:
                rec["taxfree_per_buyer_yen"] = num(r[5])
        s = b.sheet_by_name("表1-1")
        for i in range(s.nrows):
            r = s.row_values(i)
            if r[2] == "百貨店・デパート":
                rec["dept_use_rate_pct"] = num(r[5]); break
        out.append(rec)
    return pd.DataFrame(out)


PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]


def pref_annual():
    rec = []
    b = xlrd.open_workbook(RAW / "meti_pref_2019.xls")
    for sh in b.sheets():
        r10 = sh.row_values(10)
        for c, v in enumerate(r10):
            m = re.match(r"[（(](\d+)[)）](.+)", str(v))
            if not m or re.search("[A-Za-z]", str(v)):
                continue
            code = int(m.group(1))
            in_dept, mode = False, ""
            for i in range(sh.nrows):
                r = sh.row_values(i)
                lab = str(r[c - 5]).replace("\u3000", "").replace(" ", "")
                if lab:
                    in_dept = lab.startswith("百貨店")
                if str(r[c - 3]).strip():
                    mode = str(r[c - 3]).strip()
                ys = str(r[c - 4]).strip().replace(".0", "")
                if in_dept and mode == "年" and ys in ("2017", "2018", "2019") and str(r[c - 2]).strip() == "":
                    rec.append({"pref_code": code, "pref": PREFS[code - 1], "year": int(ys), "dept_sales": num(r[c + 1]), "raw": str(r[c + 1])})
                    if ys == "2019":
                        break
    wb = openpyxl.load_workbook(RAW / "meti_pref_2025.xlsx", read_only=True, data_only=True)
    for r in list(wb.worksheets[0].iter_rows(values_only=True))[6:]:
        if r[4] == "百貨店" and r[2] == "C.Y.":
            rec.append({"pref_code": int(r[6]), "pref": r[7], "year": int(r[3]), "dept_sales": num(r[10]), "raw": str(r[10])})
    df = pd.DataFrame(rec).sort_values(["pref_code", "year"]).reset_index(drop=True)
    return df


def cpi():
    # レビュー（2026-11-18）で、年度平均の表（cpi_item_annual.csv）から暦年の年平均の表に替えた
    c = pd.read_csv(RAW / "cpi_annual_middle_class.csv", encoding="cp932", header=None, dtype=str)
    assert str(c.iloc[0, 1]).strip() == "総合"
    c = c.iloc[6:, :2]
    c.columns = ["year", "cpi_all"]
    c = c[c["year"].str.strip().str.isdigit()].astype({"year": int, "cpi_all": float})
    c["cpi_all"] = c["cpi_all"] / c.loc[c["year"] == 2025, "cpi_all"].iloc[0] * 100
    return c


def main():
    d = dept_monthly(); d.to_csv(OUT / "dept_monthly.csv", index=False, float_format="%.1f")
    v = jnto(); v.to_csv(OUT / "visitors_monthly.csv", index=False)
    k = kanko(); k.to_csv(OUT / "inbound_shopping.csv", index=False, float_format="%.4f")
    p = pref_annual(); p.to_csv(OUT / "dept_pref_annual.csv", index=False, float_format="%.1f")
    c = cpi(); c.to_csv(OUT / "cpi_annual.csv", index=False, float_format="%.4f")
    print(d.shape, d.year.min(), d.year.max(), v.shape, v.year.max(), v.month.iloc[-1])
    print(k.to_string())
    print(p.groupby("year").size(), p[p.dept_sales.isna()].groupby("year").size())


if __name__ == "__main__":
    main()
