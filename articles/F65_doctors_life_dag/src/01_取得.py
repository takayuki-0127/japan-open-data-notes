"""元データの取得。

この記事では新しい統計は取らず、同じリポジトリの2本の記事が作った表を使う。
- 209（e-Stat「社会・人口統計体系 都道府県データ」の指標、2015年版と2026年版）:
  articles/209_pref_rank_turnover/data/pref_indicators_2015_2026_editions.csv と indicator_names_2026.tsv
- F49（厚生労働省「都道府県別生命表」2000〜2020年）: articles/F49_life_expectancy_decomposition/data/lifetables.csv
  （0歳と65歳の平均余命だけを抜き出して life_expectancy_f49.csv にする）
"""
import urllib.request
import pandas as pd
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

out = RAW / "life_expectancy_f49.csv"
if not out.exists():
    lt = pd.read_csv(BASE + "F49_life_expectancy_decomposition/data/lifetables.csv")
    e = lt[lt.age.isin([0, 65]) & (lt.pref_code > 0)][["year", "pref_code", "pref", "sex", "age", "ex"]]
    e.to_csv(out, index=False); print("作成:", out.name)
else:
    print("あり:", out.name)
