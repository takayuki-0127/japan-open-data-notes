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

SUFFIX = ["A100", "A110", "A140", "A150", "A170", "A300", "A311", "A330", "A331", "A332", "A318", "A400", "A900", "L900"]
# 資金循環統計（db=FF）の家計（部門430）。FFAS＝ストック（期末残高）、FFAF＝フロー（期中の取引）。単位は億円
CODES = [f"FOF_{k}430{s}" for k in ["FFAS", "FFAF"] for s in SUFFIX]
REQUESTS = {"boj_fof_household.csv": [("FF", CODES[i:i + 10], "199701") for i in range(0, len(CODES), 10)]}


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
                    rows.append((s["SERIES_CODE"], s["NAME_OF_TIME_SERIES_J"], s.get("UNIT_J", ""), d, v))
        pos = j.get("NEXTPOSITION")
        time.sleep(1)
        if not pos:
            return rows


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for fname, reqs in REQUESTS.items():
        rows = [r for db, codes, start in reqs for r in get(db, codes, start)]
        pd.DataFrame(rows, columns=["series_code", "name", "unit", "date", "value"]).to_csv(RAW / fname, index=False, encoding="utf-8-sig")
        print(fname, len(rows))
