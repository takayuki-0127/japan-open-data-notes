# SOURCES（元データの取得元）

取得日：2026-11-16（curl で取得。01_fetch.py は同じ URL を取る）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| okhotsk_alldata.txt | オホーツク海の半旬ごとの海氷域面積（万km²） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/okhotsk/data/okhotsk_alldata.txt | dde08e76d455 |
| longterm_okhotsk_latest.txt | オホーツク海の最大海氷域面積（万km²） | https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/series_okhotsk/longterm_okhotsk_latest.txt | 0a1ed9acec7e |
| station_wakkanai.txt | 北海道沿岸の海氷に関する初終日（稚内） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/hokkaido/data/statistical/wakkanai.txt | 7b3aa4037702 |
| station_omu.txt | 北海道沿岸の海氷に関する初終日（雄武） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/hokkaido/data/statistical/omu.txt | 15c5de92296d |
| station_monbetsu.txt | 北海道沿岸の海氷に関する初終日（紋別） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/hokkaido/data/statistical/monbetsu.txt | fc45f0f77c29 |
| station_abashiri.txt | 北海道沿岸の海氷に関する初終日（網走） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/hokkaido/data/statistical/abashiri.txt | 38f4aeff908b |
| station_nemuro.txt | 北海道沿岸の海氷に関する初終日（根室） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/hokkaido/data/statistical/nemuro.txt | 99961786f1a1 |
| station_kushiro.txt | 北海道沿岸の海氷に関する初終日（釧路） | https://www.data.jma.go.jp/kaiyou/data/db/seaice/hokkaido/data/statistical/kushiro.txt | 0b978ce3bcb3 |
| etrn_monthly_temp_47409.html | 過去の気象データ検索 網走 日平均気温の月平均値（観測開始からの毎月の値） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=17&block_no=47409&year=&month=&day=&view=a1 | 2429ebbcf7e3 |

出典：気象庁「海洋の健康診断表」（海氷域面積の長期変化傾向、海氷分布図・半旬ごとの値）、気象庁「北海道沿岸の海氷に関する初終日」、気象庁「過去の気象データ検索」。

初終日の観測は2025年で終了（気象庁のページの説明）。流氷終日・海明けは2021年までの値がある。
