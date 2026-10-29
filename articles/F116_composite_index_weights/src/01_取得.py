"""元データの取得。

新しい統計は取らず、同じリポジトリの記事 209 が e-Stat「社会・人口統計体系 都道府県データ」から作った表を使う
（2015年版と2026年版の指標値、指標名）。data/raw にあれば取り直さない。
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "ssds_pref_indicators.csv": "209_pref_rank_turnover/data/pref_indicators_2015_2026_editions.csv",
    "indicator_names_2026.tsv": "209_pref_rank_turnover/data/indicator_names_2026.tsv",
}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print("あり:", name); continue
    urllib.request.urlretrieve(BASE + path, out); print("取得:", name)
