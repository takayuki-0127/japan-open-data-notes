# SOURCES（元データの取得元）

取得日：2026-11-16（curl で取得。01_fetch.py は同じ URL を取る）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| nino3idx.html | エルニーニョ監視速報 監視指数 NINO.3 の基準値との差（月平均） | https://www.data.jma.go.jp/cpd/db/elnino/index/nino3idx.html | 16c5be70a72f |
| elnino_table.html | 過去のエルニーニョ現象・ラニーニャ現象の発生期間 | https://www.data.jma.go.jp/cpd/db/elnino/learning/faq/elnino_table.html | 31210fc30ee8 |
| ssn_jpn.csv | 日本の季節平均気温偏差（15地点平均） | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/ssn_jpn.csv | 1a374ba7e651 |
| etrn_m_47409.html | 過去の気象データ検索 網走 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=17&block_no=47409&year=&month=&day=&view=a1 | 2429ebbcf7e3 |
| etrn_m_47420.html | 過去の気象データ検索 根室 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=18&block_no=47420&year=&month=&day=&view=a1 | a3b320eea0eb |
| etrn_m_47421.html | 過去の気象データ検索 寿都 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=16&block_no=47421&year=&month=&day=&view=a1 | 8c69c54a28ad |
| etrn_m_47588.html | 過去の気象データ検索 山形 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=35&block_no=47588&year=&month=&day=&view=a1 | 17ac4ef73f1f |
| etrn_m_47592.html | 過去の気象データ検索 石巻 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=34&block_no=47592&year=&month=&day=&view=a1 | 382516a9a67d |
| etrn_m_47606.html | 過去の気象データ検索 伏木 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=55&block_no=47606&year=&month=&day=&view=a1 | 69d258e1a9fd |
| etrn_m_47637.html | 過去の気象データ検索 飯田 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=48&block_no=47637&year=&month=&day=&view=a1 | 6e347a8d295f |
| etrn_m_47648.html | 過去の気象データ検索 銚子 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=45&block_no=47648&year=&month=&day=&view=a1 | ef1da0279efb |
| etrn_m_47742.html | 過去の気象データ検索 境 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=69&block_no=47742&year=&month=&day=&view=a1 | 29b1bf31c81c |
| etrn_m_47755.html | 過去の気象データ検索 浜田 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=68&block_no=47755&year=&month=&day=&view=a1 | 51ea451bbc30 |
| etrn_m_47761.html | 過去の気象データ検索 彦根 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=60&block_no=47761&year=&month=&day=&view=a1 | 11dce2f03792 |
| etrn_m_47830.html | 過去の気象データ検索 宮崎 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=87&block_no=47830&year=&month=&day=&view=a1 | 315c111d116b |
| etrn_m_47890.html | 過去の気象データ検索 多度津 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=72&block_no=47890&year=&month=&day=&view=a1 | 6ec47b203308 |
| etrn_m_47909.html | 過去の気象データ検索 名瀬 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=88&block_no=47909&year=&month=&day=&view=a1 | 8248f3f13266 |
| etrn_m_47918.html | 過去の気象データ検索 石垣島 日平均気温の月平均値 | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=91&block_no=47918&year=&month=&day=&view=a1 | 7975b8ad0cd2 |

出典：気象庁「エルニーニョ監視速報」（監視指数・過去の発生期間）、気象庁「日本の季節平均気温」、気象庁「過去の気象データ検索」。

15地点は、気象庁が日本の平均気温の算出に使う、都市化の影響が比較的小さい地点。
