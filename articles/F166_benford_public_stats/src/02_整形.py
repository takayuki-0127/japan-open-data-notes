"""02 整形：SSDSE-A を「市区町村×項目」の数値表と、項目の一覧に分ける。

出力
- data/muni_2026.csv, data/muni_2021.csv : 行＝市区町村（地域コードのみ）、列＝項目コード
- data/items_2026.csv, data/items_2021.csv : 項目コード・項目名・年度
市区町村名は分析に使わないので出力しない（地域コードだけ残す）。
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"

for year in ("2026", "2021"):
    raw = pd.read_csv(RAW / f"SSDSE-A-{year}.csv", encoding="cp932", header=None, dtype=str)
    codes = raw.iloc[0].tolist()
    years = raw.iloc[1].tolist()
    names = raw.iloc[2].tolist()
    body = raw.iloc[3:].reset_index(drop=True)
    items = pd.DataFrame({"code": codes[3:], "name": names[3:], "year": years[3:]})
    num = body.iloc[:, 3:].apply(lambda s: pd.to_numeric(s.str.replace(",", ""), errors="coerce"))
    num.columns = codes[3:]
    num.insert(0, "area_code", body.iloc[:, 0].values)
    num.to_csv(BASE / "data" / f"muni_{year}.csv", index=False)
    items.to_csv(BASE / "data" / f"items_{year}.csv", index=False)
    print(year, num.shape, "項目", len(items))
