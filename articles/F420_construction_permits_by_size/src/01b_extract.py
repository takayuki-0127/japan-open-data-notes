"""01b 抜き出し（run_all.sh からは呼ばない。結果の CSV は data/raw に同梱済み）。
PDF を pdftotext -layout で文字にし、表－１・表－３・表－５を CSV にする。
- 年は各年3月末。和暦を西暦にする（昭和33年＝1958、平成元年＝1989、令和元年＝2019）。
- 抜き出し後に、表－５の階層の合計＝総数、表－１と表－５の総数の一致を確かめる。
"""
import pathlib, re, subprocess, unicodedata
import pandas as pd

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
PDF = RAW / "mlit_kyoka_2025_03.pdf"
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def num(s):
    return int(s.replace(",", ""))


def main():
    txt = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True).stdout
    txt = unicodedata.normalize("NFKC", txt)
    lines = txt.splitlines()
    # 表－１
    i0 = next(i for i, l in enumerate(lines) if "表-1" in l and "推移" in l)
    era, rows = None, []
    for l in lines[i0 + 1:]:
        m = re.match(r"^\s*(昭和|平成|令和)?\s*(元|\d+)年\s+([\d,]+)\s+(?:-|[-\d.]+%)\s+([\d,]+)\s+(?:-|[-\d.]+%)\s+([\d,]+)", l)
        if m:
            if m.group(1):
                era = m.group(1)
            y = ERA[era] + (1 if m.group(2) == "元" else int(m.group(2)))
            rows.append((y, num(m.group(3)), num(m.group(4)), num(m.group(5))))
        elif rows and "(注1)" in l:
            break
    t1 = pd.DataFrame(rows, columns=["year", "total", "minister", "governor"])
    assert (t1.minister + t1.governor == t1.total).all()
    assert t1.year.is_monotonic_increasing and t1.year.diff().dropna().eq(1).all()
    t1.to_csv(RAW / "table1_total.csv", index=False)
    # 表－５（9階層、1993〜2025年）
    i5 = next(i for i, l in enumerate(lines) if "表-5" in l and "資本金階層別" in l)
    cols = ["total", "individual", "lt2m", "2m_5m", "5m_10m", "10m_50m", "50m_100m", "100m_1b", "ge1b"]
    era, rows = "平成", []
    for l in lines[i5 + 1:]:
        m = re.match(r"^\s*(令和)?(\d+)年\s+(.*)$", l)
        if m and "%" in l:
            if m.group(1):
                era = "令和"
            vals = re.findall(r"([\d,]+)\s+([\d.]+)%", m.group(3))
            if len(vals) != 9:
                continue
            y = ERA[era] + int(m.group(2))
            rows.append([y] + [num(v[0]) for v in vals])
        if "200万円以上" in l and rows and rows[-1][0] == 2025:
            break
    t5 = pd.DataFrame(rows, columns=["year"] + cols)
    assert (t5[cols[1:]].sum(axis=1) == t5.total).all(), "階層の合計が総数と合わない"
    chk = t5.merge(t1, on="year", suffixes=("", "_t1"))
    assert (chk.total == chk.total_t1).all() and len(chk) == len(t5)
    t5.to_csv(RAW / "table5_capital.csv", index=False)
    # 表－３（業種別、2000年と2011〜2025年）
    i3 = next(i for i, l in enumerate(lines) if "表-3" in l and "業種別" in l)
    years = [2000] + list(range(2011, 2026))
    rows = []
    for l in lines[i3 + 1:]:
        if "(注1)" in l:
            break
        m = re.match(r"^\s*([^\d\s][^\d]*?)\s{2,}((?:(?:[\d,]+|-)\s+){15}(?:[\d,]+|-))", l)
        if m:
            name = re.sub(r"\s+", "", m.group(1))
            v = [None if x == "-" else num(x) for x in m.group(2).split()]
            rows.append([name] + v)
    t3 = pd.DataFrame(rows, columns=["type"] + [str(y) for y in years])
    t3[[str(y) for y in years]] = t3[[str(y) for y in years]].astype("Int64")
    tot = t3[t3.type == "合計"].iloc[0]
    body = t3[t3.type != "合計"]
    assert len(body) == 29, len(body)
    for y in years:
        assert body[str(y)].fillna(0).sum() == tot[str(y)], y
    t3.to_csv(RAW / "table3_by_type.csv", index=False)
    print(len(t1), len(t5), len(t3))


if __name__ == "__main__":
    main()
