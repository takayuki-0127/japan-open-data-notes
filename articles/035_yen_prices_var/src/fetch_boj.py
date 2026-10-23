"""日本銀行「時系列統計データ検索サイト」の API からデータを取り、data/raw/ に CSV で保存する

使い方：python fetch_boj.py
- API の仕様：日本銀行「API機能利用マニュアル」（https://www.stat-search.boj.or.jp/info/manual_list.html）
- 1回のリクエストで取れる件数に上限があるので、NEXTPOSITION が返ってきたら続きを取る
- サーバーに負担をかけないよう、リクエストの間に1秒あける
"""
import time, json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
import pandas as pd

API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

REQUESTS = {
    "boj_prices_fx.csv": [
        ("PR01", ["PRCG20_2200000000",   # 国内企業物価指数 総平均（2020年=100）
                  "PRCG20_2600000000",   # 輸入物価指数・円ベース 総平均
                  "PRCG20_2500000000",   # 輸入物価指数・契約通貨ベース 総平均
                  "PRCG20_2400000000"],  # 輸出物価指数・円ベース 総平均
         "197001"),
        ("FM08", ["FXERM07"], "197001"),  # ドル・円 スポット 17時時点 月中平均
    ],
    "boj_tankan_di.csv": [
        ("CO", ["TK99F1000601GCQ01000", "TK99F1000601GCQ11000",   # 業況判断DI 大企業・製造業 実績／予測
                "TK99F2000601GCQ01000", "TK99F2000601GCQ11000",   # 大企業・非製造業
                "TK99F1000601GCQ03000", "TK99F1000601GCQ13000",   # 中小企業・製造業
                "TK99F2000601GCQ03000", "TK99F2000601GCQ13000"],  # 中小企業・非製造業
         "196701"),
    ],
}


def get(db, codes, start):
    rows, pos = [], None
    while True:
        q = {"format": "json", "lang": "jp", "db": db, "startDate": start, "code": ",".join(codes)}
        if pos: q["startPosition"] = pos
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
    RAW.mkdir(parents=True, exist_ok=True)
    for fname, reqs in REQUESTS.items():
        rows = [r for db, codes, start in reqs for r in get(db, codes, start)]
        pd.DataFrame(rows, columns=["db", "series_code", "name", "unit", "date", "value"]).to_csv(RAW / fname, index=False, encoding="utf-8-sig")
        print(fname, len(rows))
