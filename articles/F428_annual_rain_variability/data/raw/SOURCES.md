# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得。地点のページは F331 と同じ日に同じ手順で取得したもの）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| an_jpn_r_list.html | 気象庁「日本の年平均降水量偏差」（国内51地点の平均、1898〜2025年）の一覧ページ | https://www.data.jma.go.jp/cpdinfo/temp/list/an_jpn_r.html | 7c99e511681f |
| annual/47xxx.html.gz | 気象庁「過去の気象データ検索」地点ごとの「年ごとの値 主な要素」（157地点）。HTML を gzip（mtime=0）で圧縮 | https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no=（府県番号）&block_no=47xxx&year=&month=&day=&view= | 157ファイルを連結したものの cc2d47f06005 |
| station_prec.csv | 地点番号と府県番号の対応（府県ごとの地点選択ページから作成） | https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no=NN | be3c5329899f |

- 使った列：年ごとの値の「降水量 合計」。「)」（準正常値）は使い、「]」（資料不足値）・「×」・「///」・空欄は欠測。
