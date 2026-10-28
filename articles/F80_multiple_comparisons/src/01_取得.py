"""元データの取得。

この記事では新しい統計は取らず、同じリポジトリの記事が作った表を使う。
- 209（e-Stat「社会・人口統計体系 都道府県データ」の指標、2015年版と2026年版）
- F33（都道府県の組の隣接フラグ。境界線を共有していれば adj=1）
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "ssds_pref_indicators.csv": "209_pref_rank_turnover/data/pref_indicators_2015_2026_editions.csv",
    "indicator_names_2026.tsv": "209_pref_rank_turnover/data/indicator_names_2026.tsv",
    "pref_pairs_f33.csv": "F33_migration_gravity/data/pairs.csv",
}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print("あり:", name); continue
    urllib.request.urlretrieve(BASE + path, out); print("取得:", name)
