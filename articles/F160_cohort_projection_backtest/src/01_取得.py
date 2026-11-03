"""F160 の元データ。

1. 社人研「日本の地域別将来推計人口（平成25年3月推計）」の市区町村編（結果・仮定値）
   https://www.ipss.go.jp/pp-shicyoson/j/shicyoson13/3kekka/Municipalities.asp
   https://www.ipss.go.jp/pp-shicyoson/j/shicyoson13/4shihyo/Municipalities.asp
   都道府県ごとの Excel（福島県はなし）を、ブラウザ上で SheetJS で読み、シートごとの表を
   1つの JSON（data/raw/f160_ipss13_muni.json.gz）にまとめた。
   下の関数は同じことを Python で行う（ipss.go.jp に接続できる環境で）。
2. 2018・2023年推計と令和7年国勢調査（不詳補完値）は、F45 で整形した CSV
   （../F45_population_projection/data/）をそのまま使う。
"""
import gzip
import json
import io
import urllib.request
import pandas as pd
from common import RAW

BASE = "https://www.ipss.go.jp/pp-shicyoson/j/shicyoson13/"


def fetch():
    out = {"kekka": {}, "shihyo": {}}
    for k, d in (("kekka", "3kekka"), ("shihyo", "4shihyo")):
        for i in range(1, 48):
            if i == 7:
                continue
            for ext in ("xls", "xlsx"):
                url = f"{BASE}{d}/Municipalities/{i:02d}.{ext}"
                try:
                    b = urllib.request.urlopen(url).read()
                except Exception:  # noqa: BLE001
                    continue
                for sn, df in pd.read_excel(io.BytesIO(b), sheet_name=None, header=None).items():
                    out[k][sn] = df.astype(object).where(df.notna(), None).values.tolist()
                break
    with gzip.open(RAW / "f160_ipss13_muni.json.gz", "wt", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)


if __name__ == "__main__":
    if (RAW / "f160_ipss13_muni.json.gz").exists():
        print("あり: f160_ipss13_muni.json.gz")
    else:
        fetch()
