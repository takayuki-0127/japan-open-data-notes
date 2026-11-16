"""02 整形：調査年×年齢の主世帯数・持ち家・借家（全国）を縦長の CSV にする（オフライン）。
出力：data/tenure_by_age.csv（year, age, ordinary, main, owned, rented）。2023年は普通世帯の列なし。"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def age_key(s):
    s = re.sub(r"^\d+_", "", str(s)).strip()
    m = re.match(r"(\d+)～(\d+)歳", s)
    if m: return f"{m.group(1)}-{m.group(2)}"
    if s.startswith("25歳未満"): return "<25"
    m = re.match(r"(\d+)歳以上", s)
    if m: return f"{m.group(1)}+"
    if s.startswith("総数"): return "total"
    return None

def ts():
    R = [list(r) for r in openpyxl.load_workbook(str(RAW / "jutaku_ts_t21-1_1968_2018_000031959639.xlsx"), read_only=True).worksheets[0].iter_rows(values_only=True)]
    out, year = [], None
    for r in R[19:]:
        lab = str(r[1]).strip() if r[1] else ""
        if re.match(r"^(昭和|平成)", lab) and r[2]:
            year = int(float(r[2])); continue
        if year is None or num(r[4]) is None:
            continue
        a = age_key(lab)
        if a:
            out.append((year, a, num(r[4]), num(r[5]), num(r[6]), num(r[7])))
    return out

def y2023():
    out = []
    for r in openpyxl.load_workbook(str(RAW / "jutaku_2023_t44-1_000040209922.xlsx"), read_only=True).worksheets[0].iter_rows(min_row=10, values_only=True):
        if r[0] == "00000_全国" and r[1] == "0_総数" and r[2] == "0_総数":
            a = age_key(r[3]) if not str(r[3]).startswith("99") else "unknown"
            if a:
                out.append((2023, a, None, num(r[4]), num(r[5]), num(r[6])))
    return out

def main():
    D = pd.DataFrame(ts() + y2023(), columns=["year", "age", "ordinary", "main", "owned", "rented"])
    assert not D.duplicated(["year", "age"]).any()
    D = D.sort_values(["year", "age"]).reset_index(drop=True)
    D.to_csv(ROOT / "data" / "tenure_by_age.csv", index=False)
    print(D.groupby("year").age.apply(lambda s: ",".join(s)).to_string())

if __name__ == "__main__":
    main()
