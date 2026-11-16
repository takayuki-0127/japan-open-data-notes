"""02 整形（オフライン）：
- data/pref_period.csv ：2018・2023年 × 全国・都道府県 × 建築の時期 × （総数・持ち家）の住宅数（人が住む住宅）
- data/owned_retrofit.csv：2003〜2018年 全国の持ち家（建築の時期別）と、そのうち耐震工事をした数"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0 if str(x).strip() == "-" else None

def clean(x):
    return re.sub(r"\s", "", str(x)) if x is not None else ""

def period(s):
    s = re.sub(r"^\d+_", "", str(s))
    if s.startswith("総数"): return "total"
    if s.startswith("不詳"): return "unknown"
    m = re.match(r"(\d{4})年以前", s)
    if m: return f"-{m.group(1)}"
    m = re.match(r"(\d{4})", s)
    return m.group(1) if m else None

def pref_tables():
    out = []
    spec = [(2023, "jutaku_2023_t5-1_period_000040209849.xlsx", 10, 1, 2, 3, 4, 5),
            (2018, "jutaku_2018_t6-1_period_000031865677.xlsx", 12, 5, 7, 9, 10, 11)]
    for y, name, minrow, ca, ck, cp, ct, co in spec:
        for r in openpyxl.load_workbook(str(RAW / name), read_only=True).worksheets[0].iter_rows(min_row=minrow, values_only=True):
            m = re.match(r"^(\d{5})_(.+)$", str(r[ca]))
            if not m or not m.group(1).endswith("000") or clean(r[ck]) != "0_総数":
                continue
            code = int(m.group(1)[:2])
            if code > 47:
                continue
            p = period(r[cp])
            if p:
                out.append((y, code, m.group(2), p, num(r[ct]), num(r[co])))
    D = pd.DataFrame(out, columns=["year", "pref", "name", "period", "dwellings", "owned"])
    assert not D.duplicated(["year", "pref", "period"]).any()
    return D.sort_values(["year", "pref", "period"]).reset_index(drop=True)

def retrofit():
    out = []
    wb = openpyxl.load_workbook(str(RAW / "jutaku_ts_t20-1_retrofit_000031959637.xlsx"), read_only=True)
    for ws, y in zip(wb.worksheets, [2003, 2008, 2013, 2018]):
        R = [list(r) for r in ws.iter_rows(values_only=True)]
        i = next(k for k, r in enumerate(R) if clean(r[1]).startswith("持ち家"))
        for r in R[i + 1:]:
            if clean(r[1]).startswith("木"):
                break
            m = re.search(r"(\d{4})", str(r[2]))
            if not m:
                continue
            start = int(m.group(1)); late = "or" in str(r[2]) or "以前" in clean(r[1])
            out.append((y, clean(r[1]), str(r[2]).strip(), start, late, num(r[4]), num(r[5])))
    D = pd.DataFrame(out, columns=["year", "label", "label_en", "start_year", "or_earlier", "owned", "retrofit_5y"])
    D["pre1981"] = D.or_earlier | (D.start_year <= 1971)
    return D

def main():
    P = pref_tables(); P.to_csv(ROOT / "data" / "pref_period.csv", index=False)
    print(P[P.pref == 0].pivot(index="period", columns="year", values="dwellings"))
    Rt = retrofit(); Rt.to_csv(ROOT / "data" / "owned_retrofit.csv", index=False)
    print(Rt[["year", "label_en", "pre1981", "owned", "retrofit_5y"]].to_string())

if __name__ == "__main__":
    main()
