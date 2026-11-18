"""02_build.py：新旧の推計方法の表から、学歴計の行（男女計・男・女 × 年齢階級）を、産業・企業規模・年ごとに読み出して1つの CSV にする。
列の位置は決め打ちせず、「区　分」のセルと、企業規模・項目の見出しの文字で探す。産業はシート名の産業の記号（C〜R）で合わせる。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "wage_long.csv"
SIZES = {"企業規模計(10人以上)": "計", "企業規模(10人以上)": "計", "1,000人以上": "1000+", "100～999人": "100-999", "10～99人": "10-99"}
ERA = {"平成": 1988, "令和": 2018}


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s))) if s is not None else ""


def year_of(s):
    s = norm(s).replace("元", "1")
    m = re.match(r"(平成|令和)(\d+)年", s)
    return ERA[m.group(1)] + int(m.group(2)) if m else None


def ind_code(sheet):
    s = norm(sheet)
    if s.startswith("(民+公)"):
        return None
    if s == "産業計":
        return "TOTAL"
    m = re.match(r"([C-R])", s)
    return m.group(1) if m else None


def parse_sheet(df, method, fixed_year=None):
    df = df.reset_index(drop=True)
    h = c0 = None
    for i in range(min(20, len(df))):
        for j in range(df.shape[1]):
            if norm(df.iat[i, j]) == "区分":
                h, c0 = i, j
                break
        if h is not None:
            break
    lc = c0 + 1
    years_row = [year_of(v) for v in df.iloc[h]]
    if any(years_row):
        srow, frow, urow = h + 1, h + 2, h + 3
    else:
        srow, frow, urow = h, h + 1, h + 2
    # 企業規模の列（見出しの文字）
    sn = {norm(k): v for k, v in SIZES.items()}
    size_cols = [(j, sn[norm(v)]) for j, v in enumerate(df.iloc[srow]) if norm(v) in sn]
    blocks = []
    for k, (j, sz) in enumerate(size_cols):
        end = size_cols[k + 1][0] if k + 1 < len(size_cols) else df.shape[1]
        yr = fixed_year
        if yr is None:
            yr = [y for jj, y in enumerate(years_row) if y and jj <= j][-1]
        cols = {}
        for jj in range(j, end):
            f, u = norm(df.iat[frow, jj]), norm(df.iat[urow, jj])
            if f.startswith("きまって"):
                cols["kimatte"] = jj
            if u.startswith("所定内給与"):
                cols["shoteinai"] = jj
            if f.startswith("年間賞与"):
                cols["bonus"] = jj
            if f.startswith("労働者数"):
                cols["workers"] = jj
        assert len(cols) == 4, (method, sz, cols)
        blocks.append((yr, sz, cols))
    rows, sex, in_total = [], None, False
    for i in range(urow + 1, len(df)):
        lab = norm(df.iat[i, lc])
        if not lab:
            continue
        if lab.endswith("学歴計"):
            sex = {"男女計学歴計": "計", "男学歴計": "男", "女学歴計": "女"}[lab]
            in_total, age = True, "計"
        elif in_total and re.search(r"歳", lab):
            age = lab
        else:
            in_total = False
            continue
        for yr, sz, cols in blocks:
            vals = {k: pd.to_numeric(df.iat[i, c], errors="coerce") for k, c in cols.items()}
            rows.append(dict(method=method, year=yr, size=sz, sex=sex, age=age, **vals))
    return rows


def read_book(path, method, fixed_year=None):
    x = pd.ExcelFile(path)
    out = []
    for s in x.sheet_names:
        code = ind_code(s)
        if code is None:
            continue
        df = pd.read_excel(x, s, header=None, dtype=object)
        for r in parse_sheet(df, method, fixed_year):
            r.update(industry=code, industry_name=norm(s).lstrip("CDEFGHIJKLMNOPQR") if code != "TOTAL" else "産業計")
            out.append(r)
    return out


def main():
    rows = []
    for f in ["new_sokyu01_2006_2008.xlsx", "new_sokyu01_2009_2014.xlsx", "new_sokyu01_2015_2019.xlsx"]:
        rows += read_book(RAW / f, "new")
    rows += read_book(RAW / "old_2019_t1.xls", "old", 2019)
    rows += read_book(RAW / "new_2020_t1.xls", "new2020", 2020)
    d = pd.DataFrame(rows)
    d = d[["method", "year", "industry", "industry_name", "size", "sex", "age", "kimatte", "shoteinai", "bonus", "workers"]]
    d = d.sort_values(["method", "year", "industry", "size", "sex", "age"], kind="mergesort").reset_index(drop=True)
    d.to_csv(OUT, index=False)
    # 古い方法の時系列（第3表）：年は「昭和」「平成」「令和」の行と数字の行から作る
    t = pd.read_excel(RAW / "old_timeseries_t3.xls", header=None, dtype=object)
    era, ts = None, []
    hdr = [norm(v) for v in t.iloc[1]]
    ci = {s: hdr.index(s) for s in ["男女計", "男", "女"]}
    for i in range(4, len(t)):
        e, n = norm(t.iat[i, 0]), norm(t.iat[i, 1]).replace("元", "1").replace("年", "")
        if e in ("昭和", "平成", "令和"):
            era = e
        if not n.isdigit() or era is None:
            continue
        y = {"昭和": 1925, "平成": 1988, "令和": 2018}[era] + int(n)
        v = {s: pd.to_numeric(t.iat[i, c], errors="coerce") for s, c in ci.items()}
        if pd.isna(v["男女計"]):
            continue
        ts.append(dict(year=y, **{f"old_{k}": v[k] for k in ci}))
    pd.DataFrame(ts).to_csv(ROOT / "data" / "old_timeseries.csv", index=False)
    print(d.groupby(["method", "year"]).size().to_string())


if __name__ == "__main__":
    main()
