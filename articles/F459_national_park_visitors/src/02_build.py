"""国立公園の利用者数を取り出す。data/totals.csv（公園の種類別の合計、1951〜2024年）、data/parks.csv（国立公園別、1971〜2024年、万人）。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def num(x):
    if isinstance(x, (int, float)) and not pd.isna(x):
        return float(x)
    return None


# 合計（右側の段に1951〜2024年がそろう。早い年は人、のちの年は千人で書かれているので、大きさで判定して人にそろえる）
w = pd.read_excel(RAW / "naturalpark_02.xlsx", header=None)
recs, era = [], "昭和"
for i in range(4, len(w)):
    if n(w.iloc[i, 10]) in ERA:
        era = n(w.iloc[i, 10])
    y = w.iloc[i, 11]
    s_ = n(y) if isinstance(y, str) else ("" if pd.isna(y) else str(int(y)))
    if not s_:
        continue
    yy = 1 if s_ == "元" else int(s_)
    def people(x):
        x = num(x)
        return None if x is None else (x if x > 5e6 else x * 1000)
    recs.append(dict(year=ERA[era] + yy, np_n=num(w.iloc[i, 13]), np_users=people(w.iloc[i, 14]), qnp_n=num(w.iloc[i, 15]),
                     qnp_users=people(w.iloc[i, 16]), pref_n=num(w.iloc[i, 17]), pref_users=people(w.iloc[i, 18])))
t = pd.DataFrame(recs).sort_values("year")
assert t.year.is_unique and t.year.min() == 1951 and t.year.max() == 2024
t.to_csv(ROOT / "data" / "totals.csv", index=False)

# 国立公園別：横に5つの段（年のまとまり）があり、段ごとに「番号・公園名」の列と並び順がある。2行1組（上が対前年比、下が利用者数（万人））
v = pd.read_excel(RAW / "naturalpark_04.xlsx", header=None)
label_cols = [j for j in range(v.shape[1]) if n(v.iloc[3, j]) == "公園名"]
blocks = []
for k, lc in enumerate(label_cols):
    end = label_cols[k + 1] - 1 if k + 1 < len(label_cols) else v.shape[1]
    blocks.append((lc - 1, lc, lc + 1, end))
rows = []
for nc, lc, c0, c1 in blocks:
    era = None
    yearcols = {}
    for j in range(c0, c1):
        c = v.iloc[2, j]
        s_ = n(c) if isinstance(c, str) else ("" if pd.isna(c) else str(int(c)))
        if not s_ or s_ == "年次":
            continue
        m = re.match(r"^(昭和|平成|令和)?(元|\d+)", s_)
        if s_.startswith("31") and "令和" in s_:
            yearcols[j] = 2019; era = "令和"; continue
        if m.group(1):
            era = m.group(1)
        if era is None:
            era = "昭和" if int(m.group(2)) >= 46 else "平成"
        if era == "昭和" and m.group(2) not in ("元",) and int(m.group(2)) < 20 and not m.group(1):
            era = "平成"
        yearcols[j] = ERA[era] + (1 if m.group(2) == "元" else int(m.group(2)))
    for i in range(4, len(v) - 1):
        no = v.iloc[i, nc]
        if not (isinstance(no, (int, float)) and not pd.isna(no)):
            continue
        name = n(v.iloc[i, lc]) + n(v.iloc[i + 1, lc])
        for j, y in yearcols.items():
            rows.append(dict(block=nc, no=int(no), park=name, year=y, users_10k=num(v.iloc[i + 1, j])))
p = pd.DataFrame(rows)
p.to_csv(ROOT / "data" / "parks.csv", index=False)
print(t.tail(4)); print(p.groupby("block").year.agg(["min", "max"]), p.groupby("year").users_10k.sum().loc[[1971, 1991, 2019, 2024]], t.set_index("year").np_users.loc[[1971, 1991, 2019, 2024]] / 1e4)
