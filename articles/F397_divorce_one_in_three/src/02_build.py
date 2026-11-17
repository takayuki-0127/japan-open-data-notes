"""data/raw の CSV（Shift_JIS）から、離婚件数（年×同居期間）と婚姻件数（年）の表を作る。"""
import csv, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
DUR = ["総数", "5年未満", "0", "1", "2", "3", "4", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35+", "不詳"]


def num(s):
    s = str(s).strip().replace(" ", "")
    return pd.to_numeric(s, errors="coerce")


def main():
    rows, part = [], None
    with open(RAW / "vs2025_t10_5_divorce_duration.csv", encoding="cp932", newline="") as f:
        for r in csv.reader(f):
            if not r:
                continue
            if r[0].startswith("離婚件数"):
                part = "count"; continue
            if r[0].startswith("百分率"):
                part = None; continue
            if part == "count" and r[0].strip().isdigit():
                y = int(r[0])
                for k, d in enumerate(DUR):
                    rows.append(dict(year=y, duration=d, n=num(r[1 + k])))
    div = pd.DataFrame(rows)
    div.to_csv(DATA / "divorce_by_duration.csv", index=False)
    mar = []
    with open(RAW / "vs2025_t9_5_marriage_first_re.csv", encoding="cp932", newline="") as f:
        for r in csv.reader(f):
            if r and r[0].strip().isdigit() and len(r) > 6:
                mar.append(dict(year=int(r[0]), marriages=num(r[1]), first_both=num(r[2]), any_re=num(r[3])))
    pd.DataFrame(mar).drop_duplicates("year").to_csv(DATA / "marriages.csv", index=False)
    print(div.year.nunique(), len(mar))


if __name__ == "__main__":
    main()
