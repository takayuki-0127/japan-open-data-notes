"""データの取得（data/raw/ に取得済みのものを同梱）
1) 死亡数（全国・月別）: F172 の data/births_deaths_monthly.csv をそのまま使う
   （厚生労働省「人口動態統計」確定数 上巻 死亡 第5.4表、e-Stat 統計表ID 000040502537）。
2) 気温: 気象庁「過去の気象データ検索」の月ごとの値（monthly_s3.php）を、47都道府県の
   県庁所在地などの気象台（data/raw/jma_stations.csv）について取得。view=a1/a2/a3 =
   月平均気温／日最高気温の月平均／日最低気温の月平均。
   気象庁のサイトはこの作業環境から直接つながらないため、ブラウザで取得・集計して保存した。
   下の関数は同じ取得を requests で行うもの（つながる環境用）。
3) 日本の月平均気温偏差（15地点平均、1991〜2020年平均との差）: mon_jpn.csv
"""
import time, re
import pandas as pd
from common import RAW

F172 = ("https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/"
        "articles/F172_birth_death_calendar/data/births_deaths_monthly.csv")


def fetch_station(prec_no, block_no, view):
    import requests
    from io import StringIO
    url = ("https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php"
           f"?prec_no={prec_no}&block_no={block_no}&year=&month=&day=&view={view}")
    t = pd.read_html(StringIO(requests.get(url, timeout=60).text), attrs={"class": "data2_s"})[0]
    time.sleep(1)
    return t


if __name__ == "__main__":
    if not (RAW / "deaths_monthly_F172.csv").exists():
        pd.read_csv(F172).to_csv(RAW / "deaths_monthly_F172.csv", index=False)
    print("data/raw の取得済みファイルを使います:", sorted(p.name for p in RAW.glob("*.csv")))
