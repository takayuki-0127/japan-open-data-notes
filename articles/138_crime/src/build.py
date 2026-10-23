"""元の資料（PDF・CSV）から data/crime_counts.csv を作る。元ファイルは data/raw/ に置く（README 参照）"""
import re
import pandas as pd
from common import RAW, DATA, read_pdf, read_csv, RENAME

ERA = {"H": 1988, "R": 2018}


def year_of(name):
    m = re.search(r"([HR])(\d+)", name)
    return ERA[m.group(1)] + int(m.group(2))


def fix(lab):
    lab = lab.replace("傷害うち)傷害致死", "うち)傷害致死")
    lab = re.sub(r"^.*?(うち\))", r"\1", lab) if "うち)" in lab else lab
    return RENAME.get(lab, lab)


rows = []
for f in sorted(RAW.glob("138_*.k*")):
    y = year_of(f.name)
    if f.suffix == ".k2":
        if y >= 2020:
            continue
        rows += read_pdf(f, y)
    else:
        rows += read_csv(f, y)
d = pd.DataFrame(rows)
d["item"] = d["item"].map(fix)
d["group"] = d["group"].fillna("")
# 前年値から2007年分を足す（2008年分の資料の前年値）
first = d[d.year == d.year.min()].copy()
first["year"] -= 1; first["count"] = first["prev"]
d = pd.concat([first, d])
# 同じ年の値が2つ（PDF の2019年と CSV の前年値）になることはないが、重複行は最初を残す
d = d.drop_duplicates(["year", "table", "group", "item"], keep="last")
d[["year", "table", "group", "item", "count", "prev"]].sort_values(["table", "group", "item", "year"]).to_csv(DATA / "crime_counts.csv", index=False)
print(d.groupby("year").size().to_dict())
# 確認：前年の資料の当年値と、次の年の資料の前年値の差
chk = d.merge(d.assign(year=d.year - 1)[["year", "table", "group", "item", "prev"]].rename(columns={"prev": "next_prev"}), on=["year", "table", "group", "item"])
chk["diff"] = chk["count"] - chk["next_prev"]
print(chk[chk["diff"].abs() > 0][["year", "table", "group", "item", "count", "next_prev"]].head(30).to_string())
