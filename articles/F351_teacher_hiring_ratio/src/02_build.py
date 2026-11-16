"""data/raw の PDF から表の数字を取り出し、CSV にする（オフライン。pdfplumber を使う）。
- data/long_term.csv：第7表 長期的推移（1979〜2025年度、校種×受験者・採用者・倍率）
- data/new_vs_prior.csv：新規学卒者・既卒者の受験者・採用者（2012〜2025年度、校種）
- data/new_vs_prior_crosscheck.csv：同じ年度の値を、その年度の表と次の年度の表（前年度の欄）で比べたもの
- data/univ_graduates.csv：大学（学部）の卒業者"""
import pathlib, re
import numpy as np
import pandas as pd
import pdfplumber

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MAIN = RAW / "mext_r7_kyoin_saiyo_sankou1_tables1_23.pdf"
TYPES = ["小学校", "中学校", "高等学校", "特別支援学校", "養護教諭", "栄養教諭", "計"]
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def to_num(s):
    s = s.replace(",", "")
    return np.nan if s in ("-", "－") else float(s)


def long_term():
    rows = {}
    era = None
    with pdfplumber.open(MAIN) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    blocks = [t for t in pages if "長期的推移" in t]
    assert len(blocks) == 2, len(blocks)
    for part, t in enumerate(blocks):
        era = None
        for line in t.splitlines():
            m = re.match(r"^\s*(昭和|平成|令和)?\s*(元|\d+)\s+(.*)$", line)
            if not m:
                continue
            if m.group(1):
                era = m.group(1)
            if era is None:
                continue
            n = 1 if m.group(2) == "元" else int(m.group(2))
            year = ERA[era] + n
            toks = m.group(3).split()
            vals = [to_num(x) for x in toks]
            if part == 0 and len(vals) == 12:
                for k, ty in enumerate(["小学校", "中学校", "高等学校", "特別支援学校"]):
                    rows.setdefault(year, {}).update({f"{ty}_受験者": vals[3 * k], f"{ty}_採用者": vals[3 * k + 1], f"{ty}_倍率": vals[3 * k + 2]})
            elif part == 1 and len(vals) == 9:
                for k, ty in enumerate(["養護教諭", "栄養教諭", "計"]):
                    rows.setdefault(year, {}).update({f"{ty}_受験者": vals[3 * k], f"{ty}_採用者": vals[3 * k + 1], f"{ty}_倍率": vals[3 * k + 2]})
    df = pd.DataFrame([dict(year=y, **v) for y, v in sorted(rows.items())])
    out = []
    for _, r in df.iterrows():
        for ty in TYPES:
            out.append(dict(year=int(r.year), type=ty, applicants=r.get(f"{ty}_受験者"), hires=r.get(f"{ty}_採用者"), ratio_published=r.get(f"{ty}_倍率")))
    return pd.DataFrame(out)


def table_new_prior(path):
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            if "新規学卒者・既卒者" in t and "内訳" in t:
                seg = t[t.find("新規学卒者・既卒者"):]
                rows = []
                for line in seg.splitlines():
                    if "%" in line:
                        continue
                    vals = [int(x.strip("()").replace(",", "")) for x in re.findall(r"\(?\d[\d,]*\)?", line)]
                    if len(vals) == 7:
                        rows.append(vals)
                    if len(rows) == 12:
                        return rows
    raise ValueError(path)


def new_prior():
    files = {2025: MAIN}
    for y in [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2022, 2023, 2024]:
        files[y] = RAW / f"mext_kyoin_saiyo_{y}_tables.pdf"
    names = [("受験者", "新卒"), ("受験者", "既卒"), ("受験者", "計"), ("採用者", "新卒"), ("採用者", "既卒"), ("採用者", "計")]
    recs = []
    for fy, p in sorted(files.items()):
        rows = table_new_prior(p)
        for k, (who, kind) in enumerate(names):
            for which, yy in [(0, fy), (1, fy - 1)]:
                for j, ty in enumerate(TYPES):
                    recs.append(dict(file_year=fy, year=yy, who=who, kind=kind, type=ty, value=rows[2 * k + which][j]))
    d = pd.DataFrame(recs)
    own = d[d.year == d.file_year].drop(columns="file_year")
    nxt = d[d.year == d.file_year - 1].drop(columns="file_year")
    chk = own.merge(nxt, on=["year", "who", "kind", "type"], how="outer", suffixes=("_own_file", "_next_file"))
    chk["diff"] = chk.value_next_file - chk.value_own_file
    # 使う値：その年度の表（初めの公表値）。その年度の表がない年度（2012・2021）は次の年度の表の前年度の欄
    use = own.copy()
    miss = nxt[~nxt.set_index(["year", "who", "kind", "type"]).index.isin(own.set_index(["year", "who", "kind", "type"]).index)]
    use = pd.concat([use.assign(source="その年度の表"), miss.assign(source="次の年度の表の前年度の欄")], ignore_index=True)
    return use.sort_values(["type", "who", "kind", "year"]), chk.sort_values(["type", "who", "kind", "year"])


def univ_grad():
    g = pd.read_excel(RAW / "gakkou_kihon_nenji_13_graduates_1948_2025.xlsx", header=None)
    c = [c for c in range(g.shape[1]) if "|".join(str(g.iat[r, c]).strip() for r in range(2, 5)) == "大学|大学|大学"][0]
    out = []
    for i in range(5, len(g)):
        try:
            y = int(float(g.iat[i, 1]))
        except (TypeError, ValueError):
            continue
        if y > 1900:
            try:
                out.append(dict(year=y, univ_grad=float(g.iat[i, c])))
            except (TypeError, ValueError):
                pass
    return pd.DataFrame(out)


def main():
    lt = long_term()
    lt.to_csv(ROOT / "data" / "long_term.csv", index=False)
    use, chk = new_prior()
    use.to_csv(ROOT / "data" / "new_vs_prior.csv", index=False)
    chk.to_csv(ROOT / "data" / "new_vs_prior_crosscheck.csv", index=False)
    univ_grad().to_csv(ROOT / "data" / "univ_graduates.csv", index=False)
    calc = lt.applicants / lt.hires
    print(lt.year.min(), lt.year.max(), lt.year.nunique(), "max |round(A/H,1)-published|", float((calc.round(1) - lt.ratio_published).abs().max()))
    print(use.year.min(), use.year.max(), use.year.nunique(), "crosscheck nonzero", int((chk["diff"].fillna(0) != 0).sum()))


if __name__ == "__main__":
    main()
