# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| cpi_item_monthly.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| jma/<地点>_<要素>.html.gz | 気象庁「過去の気象データ検索」月ごとの値（年×月の表）。地点：47412 札幌、47629 水戸、47624 前橋、47648 銚子、47610 長野、47636 名古屋、47819 熊本。要素：temp（view=a1 日平均気温の月平均値）、precip（view=p5 降水量の月合計値）、sunshine（view=p4 日照時間の月合計値）。HTML を gzip（mtime=0）で圧縮 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=（府県番号）&block_no=（地点番号）&year=&month=&day=&view=（a1・p5・p4） | 21ファイルを連結したものの ed8cd7bf8c00 |

- 気象庁の値：「)」（準正常値）は使い、「]」（資料不足値）・「×」・「///」・空欄は欠測。
