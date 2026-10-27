"""データの取得

- 短期金利（無担保コールレート O/N 物、月平均）：日本銀行「時系列統計データ検索サイト」の API（db=FM02, code=STRACLUCON）
- ドル円・輸入物価（契約通貨ベース）：同じ API（記事035・F39 と同じファイル boj_prices_fx.csv）
- 消費者物価（生鮮食品を除く総合）・完全失業率（季節調整値）：F12 のパイプラインの集計表（f12_mart_extract.csv）
- 鉱工業生産指数（季節調整値）：F13 で取った景気動向指数の個別系列（f13_monthly.csv）
- 長期金利（10年国債）：F18 で取った系列（f18_long_rate.csv）

使い方：python 01_取得.py  （短期金利だけを API から取り直します。ほかのファイルは data/raw にあるものを使います）
日銀の API は、リクエストの間に1秒あけて使います。
"""
import json, time
from urllib.parse import urlencode
from urllib.request import urlopen
import pandas as pd
from common import RAW

API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"


def get(db, codes, start):
    rows, pos = [], None
    while True:
        q = {"format": "json", "lang": "jp", "db": db, "startDate": start, "code": ",".join(codes)}
        if pos:
            q["startPosition"] = pos
        with urlopen(API + "?" + urlencode(q), timeout=60) as r:
            j = json.load(r)
        if j.get("STATUS") != 200:
            raise RuntimeError(j.get("MESSAGE"))
        for s in j["RESULTSET"]:
            for d, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
                if v is not None:
                    rows.append((db, s["SERIES_CODE"], s["NAME_OF_TIME_SERIES_J"], s.get("UNIT_J", ""), d, v))
        pos = j.get("NEXTPOSITION")
        time.sleep(1)
        if not pos:
            return rows


if __name__ == "__main__":
    rows = get("FM02", ["STRACLUCON"], "198001")
    pd.DataFrame(rows, columns=["db", "series_code", "name", "unit", "date", "value"]).to_csv(
        RAW / "f43_boj_callrate.csv", index=False, encoding="utf-8-sig")
    print("call rate rows", len(rows))
