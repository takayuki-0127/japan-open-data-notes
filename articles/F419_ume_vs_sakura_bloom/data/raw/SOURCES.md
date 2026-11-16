# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| 001_ume_kaika.csv | 気象庁「生物季節観測」累年値 うめの開花（地点別、1953〜2025年） | https://www.data.jma.go.jp/sakura/data/ruinenchi/001.csv | 7ebf1033dc99 |
| 004_sakura_kaika.csv | 同 さくらの開花（地点別、1953〜2025年） | https://www.data.jma.go.jp/sakura/data/ruinenchi/004.csv | 53b51c305f86 |
| mon_jpn.csv | 気象庁「日本の月平均気温偏差」（都市化の影響が少ない15地点の平均、1898年以降） | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/mon_jpn.csv | 5652abad27b9 |
| ame_master_20260324.csv | 気象庁 アメダス観測所一覧（地点の緯度を引くために使用。ame_master.zip の中身） | https://www.jma.go.jp/jma/kishou/know/amedas/ame_master.zip | 0adceeeb4c2e |

- 表の見方（rm の意味、前年12月の値の扱い）：気象庁「生物季節観測 表の見方」https://www.data.jma.go.jp/sakura/data/pdf/mikata.pdf
- CSV は Shift_JIS（cp932）。
