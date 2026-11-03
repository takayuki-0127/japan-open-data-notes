"""F28 と同じ法人番号データ（data/raw/houjin_new_2015_2026.csv.gz）があるか確かめる。

作り方は F28 の src/01_取得.py（国税庁 法人番号公表サイト 全件データ 2026-09-30 更新版から、
2015-11-01 以降に法人番号が指定された法人の 種別・所在地コード・指定日・閉鎖日・閉鎖事由 だけを抜き出す）。
法人名・法人番号・住所は持たない。
"""
from common import RAW
p = RAW / "houjin_new_2015_2026.csv.gz"
assert p.exists(), "F28 の data/raw/houjin_new_2015_2026.csv.gz をここに置いてください"
print(p, p.stat().st_size, "bytes")
