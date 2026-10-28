"""F28 と同じデータ（国税庁 法人番号公表サイト 全件データ 2026-09-30 更新）を使う。
data/raw/houjin_new_2015_2026.csv.gz は F28 の 01_取得.py で作ったもの
（2015-11-01 以降に指定された法人の 種別・都道府県・市区町村コード・指定日・閉鎖日・閉鎖事由 だけ）。
ここではファイルがあるかを確かめるだけ。"""
from common import RAW
p = RAW / "houjin_new_2015_2026.csv.gz"
assert p.exists(), "F28 の data/raw/houjin_new_2015_2026.csv.gz を data/raw/ に置いてください"
print("ok", p.stat().st_size)
