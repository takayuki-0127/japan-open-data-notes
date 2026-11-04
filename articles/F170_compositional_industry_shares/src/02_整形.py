"""02 整形：SSDSE-A から、産業別の従業者数（経済センサス、民営、18産業）と、
目的変数・説明変数に使う数個の項目だけを取り出す。

出力
- data/muni_2026.csv / data/muni_2021.csv : 行＝市区町村（地域コードのみ）
  列＝ind01〜ind18（従業者数）、pop（総人口）、tax（地方税）、in_/out（転入・転出）、hab（可住地面積）、
      sec1〜sec3（国勢調査の第1〜3次産業就業者数）
- data/industries.csv : ind01〜ind18 の産業名
市区町村名は使わないので出力しない。都道府県は地域コードの2〜3桁目で集計する。
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
IND = ["C220832", "C220833", "C220835", "C220836", "C220837", "C220838", "C220839", "C220840", "C220841",
       "C220844", "C220845", "C220846", "C220847", "C220848", "C220849", "C220850", "C220851", "C220852"]
OTHER = {"A1101": "pop", "D320101": "tax", "A5101": "in_", "A5102": "out", "B1103": "hab",
         "F2201": "sec1", "F2211": "sec2", "F2221": "sec3"}

for year in ("2026", "2021"):
    raw = pd.read_csv(RAW / f"SSDSE-A-{year}.csv", encoding="cp932", header=None, dtype=str)
    codes, years, names = raw.iloc[0].tolist(), raw.iloc[1].tolist(), raw.iloc[2].tolist()
    body = raw.iloc[3:].reset_index(drop=True)
    num = body.iloc[:, 3:].apply(lambda s: pd.to_numeric(s.str.replace(",", ""), errors="coerce"))
    num.columns = codes[3:]
    out = pd.DataFrame({"area_code": body.iloc[:, 0].values})
    for i, c in enumerate(IND, 1):
        out[f"ind{i:02d}"] = num[c].values
    for c, n in OTHER.items():
        out[n] = num[c].values
    out.to_csv(BASE / "data" / f"muni_{year}.csv", index=False)
    yr = dict(zip(codes, years))
    print(year, out.shape, "欠損", int(out.isna().sum().sum()),
          "年:", {n: yr[c] for c, n in OTHER.items()}, "経済センサス", yr[IND[0]])
    if year == "2026":
        nm = dict(zip(codes, names))
        pd.DataFrame({"code": [f"ind{i:02d}" for i in range(1, 19)],
                      "name": [nm[c].replace("従業者数（民営）（", "")[:-1] for c in IND]}).to_csv(
            BASE / "data" / "industries.csv", index=False)
