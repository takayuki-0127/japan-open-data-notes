# 元データの出典（取得日と URL）

取得日：2026-11-18（src/01_fetch.py で取得）

## 農林水産省「漁業・養殖業生産統計」（e-Stat）

各年の表は、一覧のページの節（海面養殖業の部）と表の題（「のり類」を含む都道府県別の表）の文字で選んだ。選んだ表の題と ID は maff/manifest.json にある。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| maff/long_yoshoku_national.xlsx | 長期累年 養殖魚種別収獲量累年統計 全国（1956〜2024年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040416372&fileKind=0 | 5886ef403ac2 |
| maff/nori_2004.xls | 2004年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000001158789&fileKind=0 | 31de4f79de34 |
| maff/nori_2005.xls | 2005年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000001213404&fileKind=0 | f164c1a7e8c5 |
| maff/nori_2006.xls | 2006年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000002047575&fileKind=0 | 7909e65a9ef2 |
| maff/nori_2007.xls | 2007年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000007556777&fileKind=0 | 3b0a9c490ce0 |
| maff/nori_2008.xls | 2008年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000008598243&fileKind=0 | 45bf7c8d8d78 |
| maff/nori_2009.xls | 2009年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000010783350&fileKind=0 | c40c2929db2a |
| maff/nori_2010.xls | 2010年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000012841999&fileKind=0 | 992e2453b259 |
| maff/nori_2011.xls | 2011年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000018104519&fileKind=0 | 38e36c3e0930 |
| maff/nori_2012.xls | 2012年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000023609731&fileKind=0 | 065cb9710aea |
| maff/nori_2013.xls | 2013年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000028393825&fileKind=0 | 49c51662692c |
| maff/nori_2014.xls | 2014年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031352905&fileKind=0 | 6424521ceb4b |
| maff/nori_2015.xls | 2015年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031515388&fileKind=0 | ec79cb119ba7 |
| maff/nori_2016.xls | 2016年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031655469&fileKind=0 | f7587f3d8029 |
| maff/nori_2017.xls | 2017年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031791475&fileKind=0 | 1ccf7482f8ab |
| maff/nori_2018.xls | 2018年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031896050&fileKind=0 | 239812851e17 |
| maff/nori_2019.xls | 2019年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032044846&fileKind=0 | 1fc69a69680c |
| maff/nori_2020.xlsx | 2020年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032166245&fileKind=0 | b4f0f0b53f68 |
| maff/nori_2021.xlsx | 2021年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040024230&fileKind=0 | 019dcb3c5e48 |
| maff/nori_2022.xlsx | 2022年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040146665&fileKind=0 | cc008339f86b |
| maff/nori_2023.xlsx | 2023年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040260897&fileKind=0 | 8d4fc7979c82 |
| maff/nori_2024.xlsx | 2024年 海面養殖業 都道府県別 のり類収獲量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040416349&fileKind=0 | 98b83983e668 |

- 統計表の一覧（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00500216&tstat=000001015174

## 気象庁

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| jma/areaC_SST.txt | 海域平均海面水温の平年差（東シナ海北部、年・季節） | https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/cfig/data/areaC_SST.txt | 045659ff3875 |
| jma/areaN_SST.txt | 海域平均海面水温の平年差（四国・東海沖、年・季節） | https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/cfig/data/areaN_SST.txt | 6a35edf2e13e |
| jma/areaM_SST.txt | 海域平均海面水温の平年差（関東の南、年・季節） | https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/cfig/data/areaM_SST.txt | 0ad5c2c8f533 |
| jma/areaK_SST.txt | 海域平均海面水温の平年差（三陸沖、年・季節） | https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/cfig/data/areaK_SST.txt | eb926cca12e6 |
| jma/areaall_SST.txt | 海域平均海面水温の平年差（全海域平均、年・季節） | https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/cfig/data/areaall_SST.txt | d1d784c388a8 |
| jma/station_47813.html | 佐賀 日平均気温の月平均値（全年） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=85&block_no=47813&year=2024&month=&day=&view= | 74364e0fa47c |
| jma/station_47891.html | 高松 日平均気温の月平均値（全年） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=72&block_no=47891&year=2024&month=&day=&view= | 74bfd2790de5 |
| jma/station_47636.html | 名古屋 日平均気温の月平均値（全年） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=51&block_no=47636&year=2024&month=&day=&view= | 518cb8752eb4 |
| jma/station_47682.html | 千葉 日平均気温の月平均値（全年） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=45&block_no=47682&year=2024&month=&day=&view= | a6b57abd5146 |
| jma/station_47590.html | 仙台 日平均気温の月平均値（全年） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=34&block_no=47590&year=2024&month=&day=&view= | c185778e0f9f |

- 海面水温の長期変化傾向（日本近海）のデータ：https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/japan_warm_data.html
- 過去の気象データ検索：https://www.data.jma.go.jp/stats/etrn/index.php

出典：農林水産省「漁業・養殖業生産統計」、気象庁「海面水温の長期変化傾向（日本近海）」「過去の気象データ検索」。政府標準利用規約（第2.0版）・気象庁ホームページの利用規約に従い、出典を示して加工して使う。
