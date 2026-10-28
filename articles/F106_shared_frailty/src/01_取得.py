"""データの取得。F28（法人は何年続くのか）・F79（閉鎖か合併か）と同じ抽出ファイルを使う。

F28 の 01_取得.py で、国税庁「法人番号公表サイト」全件データ（2026年9月30日更新）から作った
data/raw/houjin_new_2015_2026.csv.gz（2015-11-01 以降に法人番号が指定された法人。
種別・都道府県・市区町村コード・指定日・閉鎖日・閉鎖事由だけで、法人名・法人番号・住所は含まない）
をそのまま data/raw/ に置いている。作り直す場合は F28 の手順で全件 zip から抽出する。
https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F28_corporate_survival
"""
from common import RAW
assert (RAW / "houjin_new_2015_2026.csv.gz").exists(), "F28 の data/raw からコピーしてください"
print("ok")
