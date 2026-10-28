"""F85 取得：e-Stat の産業連関表（F38 と同じ表）を取る。
python src/01_取得.py → data/raw/io_tables.json

- 令和2年（2020年）産業連関表 取引基本表（生産者価格評価、統合中分類108部門）statInfId=000040187026
- 同 雇用表（統合中分類）statInfId=000040187066
- 同 部門分類コード表 statInfId=000040186856
- 平成27年（2015年）産業連関表 取引基本表（生産者価格評価、統合中分類107部門）statInfId=000031839447
記事の作成時は新しく取得せず、F38（articles/F38_input_output_tourism/data/raw/f38_io.json）と同じものを使った。
"""
import json, io, urllib.request
import pandas as pd
from common import RAW

URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"

if __name__ == "__main__":
    out = {}
    for i in ["000040187026", "000040187066", "000040186856", "000031839447"]:
        b = urllib.request.urlopen(URL.format(i), timeout=120).read()
        xl = pd.read_excel(io.BytesIO(b), sheet_name=None, header=None)
        out[i] = {k: v.where(v.notna(), None).values.tolist() for k, v in xl.items()}
    json.dump(out, open(RAW / "io_tables.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
    print("ok")
