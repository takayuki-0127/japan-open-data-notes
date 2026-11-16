"""02 整形：能力開発基本調査の第1表（OFF-JT に支出した企業の割合）と第2表（OFF-JT の費用の平均額）から、
調査年度×区分（総数・企業規模・産業）の表を作る。消費者物価指数（総合）の年度平均もつける。
出力：data/offjt.csv（survey_year, spend_fy, group, unit, share_spend, per_worker, per_firm）, data/cpi_fy.csv
"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
SIZE = {"30~49人": "s30", "50~99人": "s50", "100~299人": "s100", "300~999人": "s300", "1,000人以上": "s1000"}


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"\s+", "", s).replace("～", "~").replace("〜", "~").replace("、", ",")


def rows_of(df, hdr_row):
    """見出しの下の行を（区分, 行番号）で返す。"""
    group, out = "total", []
    for i in range(hdr_row + 1, len(df)):
        lab = norm(df.iloc[i, 0]) if isinstance(df.iloc[i, 0], str) else ""
        if not lab or lab.startswith("注") or lab.startswith("本社規模"):
            continue
        if lab == "総数":
            out.append(("total", "total", i)); continue
        if lab == "産業分類":
            group = "industry"; continue
        if lab == "企業規模":
            group = "size"; continue
        if lab.startswith("正社員率"):
            group = "other"; continue
        if group == "size" and lab in SIZE:
            out.append(("size", SIZE[lab], i))
        elif group == "industry":
            out.append(("industry", lab, i))
    return out


def table(path, kind):
    book = pd.read_excel(path, header=None, sheet_name=None)
    df = next(iter(book.values()))
    key = "労働者一人当たり平均額" if kind == 2 else "支出した"
    hdr_row = next(i for i in range(14) if any(norm(v).startswith(key) for v in df.iloc[i] if isinstance(v, str)))
    hdr = [norm(v) for v in df.iloc[hdr_row]]
    if kind == 2:
        j_pw = hdr.index(next(h for h in hdr if h.startswith("労働者一人当たり平均額")))
        j_pf = hdr.index(next(h for h in hdr if h.startswith("一社当たり平均額")))
        cols = {"per_worker": j_pw, "per_firm": j_pf}
    else:
        j = hdr.index(next(h for h in hdr if h.startswith("支出した")))
        cols = {"share_spend": j}
    rec = []
    for g, u, i in rows_of(df, hdr_row):
        r = dict(group=g, unit=u)
        for k, j in cols.items():
            r[k] = pd.to_numeric(df.iloc[i, j], errors="coerce")
        rec.append(r)
    return pd.DataFrame(rec)


def cpi_fy():
    d = pd.read_csv(RAW / "cpi_zenkoku_special_monthly.csv", encoding="cp932", header=None, low_memory=False)
    j = [k for k in range(d.shape[1]) if str(d.iloc[2, k]).strip() == "0001"][0]
    b = d.iloc[6:, [0, j]].copy(); b.columns = ["ym", "cpi"]
    b = b[b.ym.astype(str).str.fullmatch(r"\d{6}")]
    b["ym"] = b.ym.astype(int); b["cpi"] = pd.to_numeric(b.cpi, errors="coerce")
    b["fy"] = (b.ym // 100) - ((b.ym % 100) <= 3).astype(int)
    c = b.groupby("fy").agg(cpi=("cpi", "mean"), n=("cpi", "size"))
    return c[c.n == 12].cpi


def main():
    out = []
    for y in range(2009, 2026):
        p1 = next(RAW.glob(f"nouryoku_{y}_t1.*")); p2 = next(RAW.glob(f"nouryoku_{y}_t2.*"))
        t = table(p2, 2).merge(table(p1, 1), on=["group", "unit"], how="outer")
        t.insert(0, "survey_year", y); t.insert(1, "spend_fy", y - 1)
        out.append(t)
    d = pd.concat(out, ignore_index=True)
    d.to_csv(D / "offjt.csv", index=False)
    cpi_fy().round(4).to_csv(D / "cpi_fy.csv")
    print(d[d.group != "industry"].pivot_table(index="survey_year", columns="unit", values="per_worker", aggfunc="count").to_string())
    print(d[d.group != "industry"].pivot_table(index="survey_year", columns="unit", values="share_spend", aggfunc="count").to_string())
    print(d[d.group == "industry"].unit.value_counts().to_string())


if __name__ == "__main__":
    main()
