"""元データの取得。

この記事では新しい統計は取らず、同じリポジトリの3本の記事が作った表をそのまま使う。
- F01（労働力調査 都道府県別モデル推計値・有効求人倍率）: articles/F01_minimum_wage_did/data/panel.csv
- F44（都道府県別合計特殊出生率 1925〜2023年）: articles/F44_structural_breaks/data/tfr_long.csv
- F19（地域保健・健康増進事業報告 市区町村の大腸がん検診 国保 40〜69歳）: articles/F19_small_area_fh/data/screening_long.csv
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "f01_pref_panel.csv": "F01_minimum_wage_did/data/panel.csv",
    "f44_tfr_pref.csv": "F44_structural_breaks/data/tfr_long.csv",
    "f19_screening_muni.csv": "F19_small_area_fh/data/screening_long.csv",
}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print("あり:", name)
        continue
    urllib.request.urlretrieve(BASE + path, out)
    print("取得:", name)
