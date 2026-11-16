"""data/raw の3つの表から、年ごとの値の表を作る。ネットにはつながない。単位は千トン（kt）。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def yr(s):
    m = re.search(r"\((\d{4})\)", str(s))
    return int(m.group(1)) if m else None


def num(v):
    s = str(v).replace(",", "").strip()
    if s in ("-", "－"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return np.nan


def label(v, j, r0, r1):
    return " / ".join(str(v.iat[i, j]).replace("\n", "").strip() for i in range(r0, r1) if str(v.iat[i, j]) != "nan")


# 部門別（1000t）
v = pd.read_excel(RAW / "gyogyo_bumon_1979_2024.xlsx", header=None, dtype=str)
cols = {1: "total", 2: "marine_total", 3: "marine_fishing", 4: "distant", 5: "offshore", 6: "coastal", 7: "marine_aquaculture", 8: "inland_total"}
b = [{"year": yr(v.iat[i, 0]), **{k: num(v.iat[i, j]) for j, k in cols.items()}} for i in range(len(v)) if yr(v.iat[i, 0])]
b = pd.DataFrame(b)
# 2003年以降は単位がトン（見出しは1000ｔのまま）。総生産量が5万を超える行はトンとみなし1000で割る
big = b.total > 50000
b.loc[big, list(cols.values())] = b.loc[big, list(cols.values())] / 1000
b.to_csv(ROOT / "data" / "bumon.csv", index=False)

# 種類別（t → kt）
v = pd.read_excel(RAW / "gyogyo_shurui_1956_2024.xlsx", header=None, dtype=str)
want = {"遠洋まぐろはえ縄 / 計": "longline_distant", "近海まぐろはえ縄": "longline_offshore", "沿岸まぐろはえ縄": "longline_coastal",
        "遠洋かつお一本釣": "polepole_distant", "近海かつお一本釣": "polepole_offshore", "沿岸かつお一本釣": "polepole_coastal",
        "遠洋かつお･まぐろまき網": "seine_distant", "近海かつお･まぐろまき網": "seine_offshore", "漁獲量計": "marine_catch_total"}
pos = {}
for j in range(v.shape[1]):
    lab = label(v, j, 4, 9)
    for k, name in want.items():
        if lab == k or lab.endswith(" / " + k) or (k == "漁獲量計" and lab == "漁獲量計"):
            pos.setdefault(name, j)
assert len(pos) == len(want), pos
s = [{"year": yr(v.iat[i, 0]), **{k: num(v.iat[i, j]) / 1000 for k, j in pos.items()}} for i in range(len(v)) if yr(v.iat[i, 0])]
s = pd.DataFrame(s)
# 漁業種類ができる前の年は「-」（0）になっているので、最初に正の値が出る年より前は空欄にする
for c in s.columns[1:]:
    first = s.index[s[c] > 0].min()
    s.loc[s.index < first, c] = np.nan
s.to_csv(ROOT / "data" / "shurui.csv", index=False)

# 魚種別（まぐろ類計・かつお、t → kt）
v = pd.read_excel(RAW / "gyogyo_gyoshu_1956_2024.xlsx", header=None, dtype=str)
pos = {}
for j in range(v.shape[1]):
    parts = [str(v.iat[i, j]).replace("\n", "").strip() for i in range(3, 8) if str(v.iat[i, j]) != "nan"]
    if parts[:2] == ["まぐろ類", "小計"]:
        pos["tuna_total"] = j
    if parts and parts[0] == "かつお":
        pos.setdefault("skipjack", j)
assert len(pos) == 2, pos
g = [{"year": yr(v.iat[i, 0]), **{k: num(v.iat[i, j]) / 1000 for k, j in pos.items()}} for i in range(len(v)) if yr(v.iat[i, 0])]
pd.DataFrame(g).to_csv(ROOT / "data" / "gyoshu.csv", index=False)
print(len(b), int(big.sum()), int(big.idxmax()), len(s), len(g), sorted(pos))
