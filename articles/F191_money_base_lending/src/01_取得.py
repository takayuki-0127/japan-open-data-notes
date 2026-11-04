"""日本銀行 時系列統計データ検索サイトの API から月次の系列を取得し、data/raw/boj_raw.csv に保存する。
このサービスは、日本銀行時系列統計データ検索サイトの API 機能を使用しています。サービスの内容は日本銀行によって保証されたものではありません。
"""
import requests
from common import RAW, SERIES

rows = ["db,code,date,value"]
for db, codes in SERIES.items():
    url = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=en"
           f"&db={db}&code={','.join(codes)}&startDate=197001")
    t = requests.get(url, timeout=120).text
    for l in t.splitlines():
        s = l.split(",")
        if s[0] in codes:
            rows.append(",".join([db, s[0], s[-2], s[-1]]))
(RAW / "boj_raw.csv").write_text("\n".join(rows) + "\n")
print(len(rows) - 1, "rows")
