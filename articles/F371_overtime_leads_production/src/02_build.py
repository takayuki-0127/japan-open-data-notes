"""02_build.py : data/raw の元データから分析用の表を作る。
- data/monthly.csv : 年月、製造業の所定外労働時間指数（5人以上・30人以上）、総実労働時間指数・常用雇用指数（5人以上）、鉱工業生産指数
- data/cycle_dates.csv : 景気基準日付（山・谷）
"""
import html
import pathlib
import re
import unicodedata

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"


def n(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def maikin():
    v = pd.read_excel(RAW / "maikin_sa_index.xlsx", header=None)
    cur = [""] * 5
    cols = {}
    for c in range(1, v.shape[1]):
        for r in range(1, 6):
            x = v.iat[r, c]
            if isinstance(x, str):
                cur[r - 1] = n(x.split("\n")[0])
        cols[c] = tuple(cur)
    want = {
        "ot_mfg5": ("所定外労働時間", "就業形態計(Total)", "5人以上", "製造業", "季調済指数"),
        "ot_mfg30": ("所定外労働時間", "就業形態計(Total)", "30人以上", "製造業", "季調済指数"),
        "hours_mfg5": ("総実労働時間", "就業形態計(Total)", "5人以上", "製造業", "季調済指数"),
        "ot_all5": ("所定外労働時間", "就業形態計(Total)", "5人以上", "調査産業計", "季調済指数"),
        "emp_mfg5": ("常用雇用", "就業形態計(Total)", "5人以上", "製造業", "季調済指数"),
    }
    out = {}
    for k, key in want.items():
        hit = [c for c, h in cols.items() if h == key]
        assert len(hit) == 1, (k, hit)
        out[k] = hit[0]
    rows = []
    for r in range(7, v.shape[0]):
        ym = v.iat[r, 0]
        if not re.fullmatch(r"\d{6}", n(ym)):
            continue
        rec = {"ym": n(ym)}
        for k, c in out.items():
            x = pd.to_numeric(v.iat[r, c], errors="coerce")
            rec[k] = None if pd.isna(x) else float(x)
        rows.append(rec)
    d = pd.DataFrame(rows).dropna(subset=["ot_mfg5"])
    return d


def ci():
    v = pd.read_excel(RAW / "ci_coincident_series.xlsx", sheet_name=0, header=None)
    head = " ".join(n(x) for x in v.iloc[:5, 3] if isinstance(x, str))
    assert "生産指数" in head and "鉱工業" in head, head
    rows = []
    for r in range(5, v.shape[0]):
        y, m, x = v.iat[r, 1], v.iat[r, 2], pd.to_numeric(v.iat[r, 3], errors="coerce")
        if pd.isna(y) or pd.isna(m) or pd.isna(x):
            continue
        rows.append({"ym": "%04d%02d" % (int(y), int(m)), "iip": float(x)})
    return pd.DataFrame(rows)


def cycle():
    t = (RAW / "esri_hiduke.html").read_bytes().decode("utf-8", "ignore")
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t)
    rows = []
    for m in re.finditer(r"第(\d+)循環 (.*?)(?=第\d+循環|このページの先頭へ)", t):
        no = int(m.group(1))
        dates = re.findall(r"(\d{4})年(\d{1,2})月 \(", m.group(2))
        kinds = ["谷", "山", "谷"] if len(dates) == 3 else ["山", "谷"]
        for (y, mo), k in zip(dates, kinds):
            rows.append({"cycle": no, "kind": k, "ym": "%04d%02d" % (int(y), int(mo))})
    d = pd.DataFrame(rows).drop_duplicates(subset=["kind", "ym"]).sort_values("ym")
    return d


def main():
    m = maikin()
    c = ci()
    d = m.merge(c, on="ym", how="inner").sort_values("ym").reset_index(drop=True)
    d.to_csv(BASE / "data" / "monthly.csv", index=False, float_format="%.1f")
    cy = cycle()
    cy.to_csv(BASE / "data" / "cycle_dates.csv", index=False)
    print(d.head(), d.tail(), len(d))
    print(cy.tail(12))


if __name__ == "__main__":
    main()
