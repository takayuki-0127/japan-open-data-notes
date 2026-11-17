"""data/raw から、メタンの分野別（2版）と、水稲の作付面積・牛の頭数の表を作る。ネットにはつながない。
出力：data/ch4_long.csv（版・分野・年度・百万トン CO2 換算）、data/activity.csv（年・作付面積・頭数）"""
import pathlib, re
import numpy as np
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ROWS = {5: "fuel_combustion", 6: "fugitive", 9: "ippu", 12: "agriculture", 13: "enteric", 14: "manure", 15: "rice",
        16: "field_burning", 17: "waste", 18: "landfill", 19: "composting", 20: "incineration", 21: "wastewater", 22: "waste_energy", 23: "total"}
rows = []
for ver, fn in [(2026, "L5-7gas_2026_gioweb_ver1.0.xlsx"), (2025, "L5-7gas_2025_gioweb_1.0.xlsx")]:
    wb = openpyxl.load_workbook(RAW / fn, read_only=True, data_only=True)
    grid = [list(r) for r in wb["6.CH4"].iter_rows(min_row=1, max_row=24, values_only=True)]
    years = {j: int(v) for j, v in enumerate(grid[3]) if isinstance(v, (int, float)) and 1989 < v < 2100}
    for rn, key in ROWS.items():
        for j, y in years.items():
            v = grid[rn - 1][j]
            rows.append({"version": ver, "sector": key, "fy": y, "mt": round((float(v) if isinstance(v, (int, float)) else 0.0) / 1000, 6)})
ch4 = pd.DataFrame(rows).sort_values(["version", "sector", "fy"]).reset_index(drop=True)
# 点検：農業の内訳の合計＝農業
for ver in (2025, 2026):
    w = ch4[ch4.version == ver].pivot(index="fy", columns="sector", values="mt")
    assert (w[["enteric", "manure", "rice", "field_burning"]].sum(axis=1) - w.agriculture).abs().max() < 0.001
ch4.to_csv(ROOT / "data" / "ch4_long.csv", index=False)


def year_of(s):
    m = re.search(r"\((\d{4})\)", str(s))
    return int(m.group(1)) if m else None


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


# 水稲 作付面積（子実用）
r = pd.read_excel(RAW / "rice_suito_zenkoku.xls", header=None, dtype=str)
rice = [(year_of(a), num(b)) for a, b in zip(r[0], r[1]) if year_of(a)]
rice = pd.DataFrame(rice, columns=["year", "rice_area_ha"]).drop_duplicates("year", keep="last")


def cattle(fn, col, name):
    x = pd.read_excel(RAW / fn, header=None, dtype=str)
    out = []
    for a, v in zip(x[0], x[col]):
        y = year_of(a)
        if y:
            tag = "old" if "旧" in str(a) else ("new" if "新" in str(a) else "")
            out.append({"year": y, "tag": tag, name: num(v)})
    return pd.DataFrame(out)


d = cattle("dairy_cattle_zenkoku.xls", 2, "dairy_head")   # 飼養頭数（めす）合計
b = cattle("beef_cattle_zenkoku.xls", 3, "beef_head")      # 総頭数
cat = d.merge(b, on=["year", "tag"], how="outer").sort_values(["year", "tag"])
# 2019年は（旧）（新）の2行。本線は（新）を使い、頑健性用に（旧）も残す
cat_new = cat[cat.tag != "old"].drop(columns="tag").rename(columns={"dairy_head": "dairy_head", "beef_head": "beef_head"})
cat_old19 = cat[cat.tag == "old"][["year", "dairy_head", "beef_head"]].rename(columns={"dairy_head": "dairy_head_old2019", "beef_head": "beef_head_old2019"})
act = rice.merge(cat_new, on="year", how="outer").merge(cat_old19, on="year", how="left").sort_values("year")
act = act[act.year >= 1960].reset_index(drop=True)
act["cattle_head"] = act.dairy_head + act.beef_head
act.to_csv(ROOT / "data" / "activity.csv", index=False)
print(ch4.groupby("version").fy.agg(["min", "max"])); print(act.tail(8).to_string())
