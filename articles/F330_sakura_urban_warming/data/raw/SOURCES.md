# data/raw の出典

取得日：2026-11-16（`src/01_fetch.py` で取得）

| ファイル | 内容 | URL |
|---|---|---|
| 004.csv | 気象庁「生物季節観測累年値」さくらの開花（地点×年、値は月日 MMDD、0 は観測なし、各年の右の列は rm） | https://www.data.jma.go.jp/sakura/data/ruinenchi/004.csv |
| mon_jpn.csv | 気象庁「日本の月平均気温偏差」（1991〜2020年平均との差、都市化の影響が少ない15地点の平均） | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/mon_jpn.csv |
| temp/47xxx.html | 気象庁「過去の気象データ検索」地点ごとの月平均気温（年ごとの表、観測開始〜2025年） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=（府県番号）&block_no=47xxx&year=&month=&day=&view=p1 |
| station_prec.csv | 地点番号と府県番号の対応（府県ごとの地点選択ページ https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no=NN から作成） | — |

- さくらの rm が6・7の値は、主に北海道東部・奄美・沖縄など、ソメイヨシノ以外（エゾヤマザクラ・ヒカンザクラなど）を観測した地点に付いているため除いた（rm の意味は、既存の分析と同じ扱い。気象庁の説明書と照らしては確かめていない）。
- 月平均気温の「)」（準正常値）は使い、「]」（資料不足値）・「×」・「///」は欠測にした。
- 江差（47428）は府県ごとの地点選択ページで見つからず、気温を取っていない。開花の値はあるが、気温がないため分析の対象から外れている。
