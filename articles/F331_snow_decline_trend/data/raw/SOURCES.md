# data/raw の出典

取得日：2026-11-16（`src/01_fetch.py` で取得）

| ファイル | 内容 | URL |
|---|---|---|
| annual/47xxx.html.gz | 気象庁「過去の気象データ検索」地点ごとの「年ごとの値 主な要素」（気象台・測候所など、地点番号 47xxx の157地点）。ページの HTML をそのまま gzip で圧縮 | https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no=（府県番号）&block_no=47xxx&year=&month=&day=&view= |
| station_prec.csv | 地点番号と府県番号の対応（府県ごとの地点選択ページ https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no=NN から作成） | — |
| mon_jpn.csv | 気象庁「日本の月平均気温偏差」（1991〜2020年平均との差、都市化の影響が少ない15地点の平均） | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/mon_jpn.csv |

- 使った列：雪（寒候年）の「降雪の深さ 合計」と「最深積雪」。寒候年は前年8月〜その年7月。
- 「--」（現象なし）は0、「)」（準正常値）はそのまま使い、「]」（資料不足値）・「×」・「///」・空欄は欠測にした。
- 2026寒候年は途中のため使っていない（分析は1962〜2025寒候年）。
