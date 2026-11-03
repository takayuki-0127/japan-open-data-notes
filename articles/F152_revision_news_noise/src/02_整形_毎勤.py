"""毎月勤労統計（全国・事業所規模5人以上・調査産業計・就業形態計）の速報と確報から、
主な項目の前年比を月ごとに取り出す"""
import csv, io, json, re
import pandas as pd
from common import RAW, DATA

d = json.load(open(RAW / "f152_maikin_releases.json", encoding="utf-8"))

# 表ごとに「調査産業計」の行の何列目を使うか（列0が産業名）
COLS = {
    "1": {"給与総額_円": 2, "給与総額": 3, "きまって支給": 5, "所定内給与": 7, "所定外給与": 9, "特別給与": 11},
    "2": {"総実労働時間": 3, "所定内労働時間": 5, "所定外労働時間": 7},
    "3": {"常用雇用": 3},
}


def num(s):
    s = s.replace(",", "").replace("△", "-").replace("▲", "-").strip()
    try:
        return float(s)
    except ValueError:
        return None


def first_total_row(text):
    """5人以上の表の、最初の「調査産業計」の行（数字が入っている行）"""
    for row in csv.reader(io.StringIO(text)):
        if row and re.sub(r"[\s　]", "", row[0]) == "調査産業計" and len(row) > 3 and num(row[2]) is not None:
            return row
    return None


rows = []
for key, w in d.items():
    m = re.fullmatch(r"(\d{4})-(\d{2})([pr])", key)
    y, mo, k = int(m.group(1)), int(m.group(2)), m.group(3)
    rec = {"月": f"{y}-{mo:02d}", "段階": "速報" if k == "p" else "確報", "公表日": w.get("pub", "")}
    for t, cols in COLS.items():
        row = first_total_row(w["tabs"].get(t, ""))
        for name, j in cols.items():
            rec[name] = num(row[j]) if row and j < len(row) else None
    rows.append(rec)
df = pd.DataFrame(rows).sort_values(["月", "段階"])
df.to_csv(DATA / "maikin_p_r.csv", index=False)
wide = df.pivot(index="月", columns="段階")
print(df.shape, df.isna().sum().to_dict())
print(df.tail(4).to_string())
