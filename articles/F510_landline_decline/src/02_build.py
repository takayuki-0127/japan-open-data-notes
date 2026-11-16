"""data/raw の表から、月末×系列の長い表（data/series.csv、単位：万）を作る。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def period(lab):
    """「平成13年度末」→ 2002-03、「令和7年12月末」→ 2025-12。合わなければ None。"""
    m = re.fullmatch(r"(昭和|平成|令和)(元|\d+)年(度末|(\d+)月末)", norm(lab))
    if not m:
        return None
    y = ERA[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2)))
    if m.group(3) == "度末":
        return f"{y + 1}-03"
    return f"{y}-{int(m.group(4)):02d}"


def num(v):
    s = norm(v)
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def take(df, cols):
    rows = []
    for i in range(len(df)):
        p = period(df.iloc[i, 1])
        if p is None:
            continue
        for name, j in cols.items():
            v = num(df.iloc[i, j])
            if v is not None:
                rows.append((p, name, v))
    return rows


def main():
    rows = []
    d = pd.read_excel(RAW / "gt010205.xls", header=None)
    rows += take(d, {"fixed_total": 2, "fixed_tel": 4, "fixed_isdn": 6, "ntt_total": 8, "ntt_tel": 10, "ntt_isdn": 12})
    d = pd.read_excel(RAW / "gt010206.xls", header=None)
    rows += take(d, {"ip_total": 2, "ip_050": 4, "ip_0abj": 6})
    d = pd.read_excel(RAW / "gt01020101.xls", header=None)
    m = take(d, {"mobile_phs_n": 9, "mobile_phs_pen": 10})
    rows += [(p, "mobile_phs" if k == "mobile_phs_n" else "mobile_phs_pen_pct",
              round(v / 1e4, 4) if k == "mobile_phs_n" else round(v * 100, 3)) for p, k, v in m]
    s = pd.DataFrame(rows, columns=["date", "series", "value"])
    assert not s.duplicated(["date", "series"]).any()
    s = s.sort_values(["series", "date"]).reset_index(drop=True)
    s.to_csv(ROOT / "data" / "series.csv", index=False)

    # 白書のCSV（2016〜2025年、年末。2025年は12月末）
    w = pd.read_csv(RAW / "wp_r08_f00126.csv", header=None, encoding="utf-8-sig", dtype=str)
    out = []
    for _, r in w.iterrows():
        lab = norm(r[0])
        m = re.match(r"^(\d{4})(\.12)?", lab)
        if m and not lab.startswith("@") and (lab.isdigit() or ".12" in lab):
            out.append({"year": int(m.group(1)), "fixed_wp": num(r[1]), "mobile_wp": num(r[2]),
                        "ip_0abj_wp": num(r[3]), "ip_050_wp": num(r[4])})
    pd.DataFrame(out).drop_duplicates("year", keep="last").to_csv(ROOT / "data" / "whitepaper.csv", index=False)


if __name__ == "__main__":
    main()
